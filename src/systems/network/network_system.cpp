#include <corona/events/network_system_events.h>
#include <corona/kernel/core/i_logger.h>
#include <corona/kernel/event/i_event_bus.h>
#include <corona/kernel/event/i_event_stream.h>
#include <corona/systems/network/network_system.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <unordered_map>

namespace Corona::Systems {

// ============================================================================
// Impl
// ============================================================================

struct NetworkSystem::Impl {
    Kernel::ISystemContext* ctx = nullptr;

    // Subsystems
    Network::Discovery discovery;
    Network::PeerManager peer_manager;
    Network::SyncEngine sync_engine;

    // State
    SessionState session_state{SessionState::Idle};
    std::string instance_name;
    uint64_t project_id = 0;
    uint16_t port = Network::kDefaultPort;

    // Timing for sync ticks
    using Clock = std::chrono::steady_clock;
    Clock::time_point last_sync_time;
    Clock::time_point last_discovery_poll;

    // Event subscription IDs
    std::vector<Kernel::EventId> event_subscriptions;

    // File transfer state
    struct IncomingTransfer {
        std::string model_path;
        std::string sender_peer_id;  // isolate chunks from multi-sender
        uint32_t total_size = 0;
        uint32_t chunk_count = 0;
        std::vector<bool> received_chunks;
        std::vector<uint8_t> buffer;
        Clock::time_point last_chunk_time;
        bool complete = false;
    };
    // key = sender_peer_id + "/" + model_path (first responder wins)
    std::unordered_map<std::string, IncomingTransfer> incoming_transfers;

    // Outgoing transfer: for each model_path, cache the file data
    // so we don't re-read on every FILE_REQUEST
    struct CachedFileData {
        std::vector<uint8_t> data;
        Clock::time_point load_time;
    };
    std::unordered_map<std::string, CachedFileData> outgoing_cache;

    // Project root for file write destination
    std::string project_root;

    // Sync pause (suppress poll_and_sync during incoming actor creation)
    bool sync_paused = false;

    // Deferred actions to execute in update() (avoid GIL in network thread)
    struct PendingAction {
        std::string scene_name;
        std::string model_path;
        Network::ActorCreatePacked actor_packed;
    };
    std::vector<PendingAction> pending_actor_creates;

    // Pending file transfers: model_path → actor data from the original
    // ACTOR_CREATE that triggered the transfer.  When the file arrives,
    // we reconstruct the PendingAction without requiring a re-send.
    struct PendingFileTransfer {
        std::string scene_name;
        Network::ActorCreatePacked actor_packed;
    };
    std::unordered_map<std::string, PendingFileTransfer> pending_file_transfers;
};

// ============================================================================
// Lifecycle
// ============================================================================

NetworkSystem::NetworkSystem() : impl_(std::make_unique<Impl>()) {
    set_target_fps(60);
}

NetworkSystem::~NetworkSystem() = default;

bool NetworkSystem::initialize(Kernel::ISystemContext* ctx) {
    impl_->ctx = ctx;
    CFW_LOG_NOTICE("NetworkSystem: Initializing (ENet LAN collaborative editing)");

    // Wire up SyncEngine → PeerManager outbound path
    impl_->sync_engine.set_on_outgoing([this](const std::vector<uint8_t>& packet) {
        impl_->peer_manager.broadcast(
            Network::kChannelReliable,
            packet.data(), packet.size(),
            true);
    });

    // Wire up PeerManager → SyncEngine inbound path
    impl_->peer_manager.set_on_data_received(
        [this](const std::string& peer_id, const uint8_t* data, size_t len) {
            // Route: SYNC_DIRTY/SYNC_FULL/HEARTBEAT → sync engine
            //         ACTOR_CREATE/FILE_REQUEST/FILE_CHUNK → custom handler
            if (len >= 1) {
                using Network::MessageType;
                auto mt = static_cast<MessageType>(data[0]);
                if (mt == MessageType::SYNC_DIRTY || mt == MessageType::SYNC_FULL ||
                    mt == MessageType::HEARTBEAT) {
                    on_data_received(peer_id, data, len);
                } else {
                    on_custom_message(peer_id, data, len);
                }
            }
        });

    // Wire up PeerManager connect/disconnect → events
    impl_->peer_manager.set_on_peer_connected(
        [this](const Network::PeerManager::PeerInfo& info) {
            on_peer_connected(info);
        });

    impl_->peer_manager.set_on_peer_disconnected(
        [this](const Network::PeerManager::PeerInfo& info) {
            on_peer_disconnected(info);
        });

    // Wire up Discovery → PeerManager connect path
    impl_->discovery.set_on_peer_discovered(
        [this](const std::string& ip, const std::string& name, uint64_t proj_id) {
            on_peer_discovered(ip, name, proj_id);
        });

    return true;
}

void NetworkSystem::update() {
    if (impl_->session_state != SessionState::Active) return;

    auto now = Impl::Clock::now();

    // Poll ENet events every tick
    impl_->peer_manager.poll();

    // Poll Discovery broadcasts
    if (now - impl_->last_discovery_poll >=
        std::chrono::milliseconds(Network::kDiscoveryIntervalMs)) {
        impl_->discovery.poll();
        impl_->last_discovery_poll = now;
    }

    // Sync engine tick (~60 Hz) — paused during remote actor creation
    // to ensure both peers build identical storage layouts (seq_id alignment).
    if (!impl_->sync_paused && now - impl_->last_sync_time >=
        std::chrono::milliseconds(Network::kSyncIntervalMs)) {
        impl_->sync_engine.poll_and_sync();
        impl_->last_sync_time = now;
    }
}

void NetworkSystem::shutdown() {
    CFW_LOG_NOTICE("NetworkSystem: Shutting down...");
    stop_session();

    // Unsubscribe events
    if (impl_->ctx && impl_->ctx->event_bus()) {
        for (auto id : impl_->event_subscriptions) {
            impl_->ctx->event_bus()->unsubscribe(id);
        }
    }
    impl_->event_subscriptions.clear();
}

// ============================================================================
// Public API
// ============================================================================

bool NetworkSystem::start_session(const std::string& instance_name,
                                  uint64_t project_id, uint16_t port) {
    if (impl_->session_state == SessionState::Active) {
        CFW_LOG_WARNING("NetworkSystem: Session already active");
        return true;
    }

    impl_->session_state = SessionState::Starting;
    impl_->instance_name = instance_name;
    impl_->project_id = project_id;
    impl_->port = port;

    CFW_LOG_INFO("NetworkSystem: Starting session '{}' on port {} (project={:x})",
                 instance_name, port, project_id);

    // 1. PeerManager
    if (!impl_->peer_manager.start(port, instance_name)) {
        impl_->session_state = SessionState::Error;
        CFW_LOG_ERROR("NetworkSystem: Failed to start PeerManager");
        return false;
    }

    // 2. SyncEngine
    impl_->sync_engine.initialize(impl_->peer_manager.local_peer_id());

    // 3. Discovery (use port + 1 to avoid bind conflict with ENet)
    // If Discovery fails (port already in use by another instance), retry
    // with port+2, port+3 (same-machine multi-instance).
    uint16_t disc_port = port + Network::kDiscoveryPortOffset;
    bool disc_ok = impl_->discovery.start(disc_port, instance_name, project_id);
    for (int retry = 1; !disc_ok && retry <= 2; ++retry) {
        disc_port = port + Network::kDiscoveryPortOffset + static_cast<uint16_t>(retry);
        CFW_LOG_WARNING("NetworkSystem: Discovery port {} in use, retrying on {}",
                         port + Network::kDiscoveryPortOffset, disc_port);
        disc_ok = impl_->discovery.start(disc_port, instance_name, project_id);
    }
    if (!disc_ok) {
        impl_->peer_manager.stop();
        impl_->session_state = SessionState::Error;
        CFW_LOG_ERROR("NetworkSystem: Failed to start Discovery on any port");
        return false;
    }

    impl_->session_state = SessionState::Active;
    impl_->last_sync_time = Impl::Clock::now();
    impl_->last_discovery_poll = Impl::Clock::now();

    // Publish event
    if (impl_->ctx && impl_->ctx->event_bus()) {
        Events::NetworkHostStartedEvent ev{port};
        impl_->ctx->event_bus()->publish(ev);
    }

    CFW_LOG_INFO("NetworkSystem: Session active — listening on port {}", port);
    return true;
}

void NetworkSystem::stop_session() {
    if (impl_->session_state != SessionState::Active &&
        impl_->session_state != SessionState::Error) return;

    // Stop ENet host FIRST (it relies on WinSock, which discovery owns the
    // WSAStartup/WSACleanup for). Tearing down discovery first would call
    // WSACleanup() while ENet sockets are still open, hanging enet_host_destroy.
    impl_->peer_manager.stop();
    impl_->sync_engine.shutdown();
    impl_->discovery.stop();

    impl_->session_state = SessionState::Idle;

    // Publish event
    if (impl_->ctx && impl_->ctx->event_bus()) {
        Events::NetworkHostStoppedEvent ev;
        impl_->ctx->event_bus()->publish(ev);
    }

    CFW_LOG_INFO("NetworkSystem: Session stopped");
}

NetworkSystem::SessionState NetworkSystem::session_state() const {
    return impl_->session_state;
}

size_t NetworkSystem::peer_count() const {
    return impl_->peer_manager.peer_count();
}

bool NetworkSystem::connect_to_peer(const std::string& ip, uint16_t port,
                                    const std::string& peer_name) {
    if (impl_->session_state != SessionState::Active) {
        CFW_LOG_WARNING("NetworkSystem: Cannot connect — session not active");
        return false;
    }
    impl_->peer_manager.connect_to_peer(ip, port, peer_name, /*force=*/true);
    return true;
}

void NetworkSystem::broadcast_actor_create(const std::string& scene_name,
                                           const std::string& model_path,
                                           const float* transform,
                                           const void* optics_packed, size_t optics_size) {
    if (impl_->session_state != SessionState::Active) return;
    if (impl_->peer_manager.peer_count() == 0) {
        CFW_LOG_DEBUG("NetworkSystem: No peers — skipping actor create broadcast");
        return;
    }
    auto pkt = Network::build_actor_create(scene_name, model_path, transform,
                                           optics_packed, optics_size);
    impl_->peer_manager.broadcast(Network::kChannelReliable, pkt.data(), pkt.size(), true);
    CFW_LOG_INFO("NetworkSystem: Broadcast actor create — scene='{}' model='{}'",
                 scene_name, model_path);
}

bool NetworkSystem::has_pending_transfers() const {
    return !impl_->pending_actor_creates.empty();
}

void NetworkSystem::set_sync_paused(bool paused) {
    impl_->sync_paused = paused;
}

bool NetworkSystem::pop_pending_actor_create(std::string& scene_name,
                                              std::string& model_path,
                                              void* actor_packed_out, size_t packed_size) {
    if (impl_->pending_actor_creates.empty()) return false;
    auto& pa = impl_->pending_actor_creates.front();
    scene_name = pa.scene_name;
    model_path = pa.model_path;
    if (actor_packed_out && packed_size <= sizeof(Network::ActorCreatePacked)) {
        std::memcpy(actor_packed_out, &pa.actor_packed, packed_size);
    }
    impl_->pending_actor_creates.erase(impl_->pending_actor_creates.begin());
    return true;
}

void NetworkSystem::set_project_root(const std::string& project_root) {
    impl_->project_root = project_root;
}

// ============================================================================
// Callbacks
// ============================================================================

void NetworkSystem::on_peer_discovered(const std::string& ip,
                                       const std::string& name,
                                       uint64_t /*project_id*/) {
    impl_->peer_manager.connect_to_peer(ip, impl_->port, name);
}

void NetworkSystem::on_peer_connected(const Network::PeerManager::PeerInfo& info) {
    CFW_LOG_INFO("NetworkSystem: Peer connected — {} ({})", info.id, info.name);

    if (impl_->ctx && impl_->ctx->event_bus()) {
        Events::PeerConnectedEvent ev{info.id, info.name};
        impl_->ctx->event_bus()->publish(ev);
    }
}

void NetworkSystem::on_peer_disconnected(const Network::PeerManager::PeerInfo& info) {
    CFW_LOG_INFO("NetworkSystem: Peer disconnected — {} ({})", info.id, info.name);

    if (impl_->ctx && impl_->ctx->event_bus()) {
        Events::PeerDisconnectedEvent ev{info.id};
        impl_->ctx->event_bus()->publish(ev);
    }
}

void NetworkSystem::on_data_received(const std::string& peer_id,
                                     const uint8_t* data, size_t len) {
    impl_->sync_engine.handle_incoming(peer_id, data, len);

    if (impl_->ctx && impl_->ctx->event_bus()) {
        Events::RemoteSyncReceivedEvent ev{peer_id};
        impl_->ctx->event_bus()->publish(ev);
    }
}

void NetworkSystem::on_custom_message(const std::string& sender_peer_id,
                                        const uint8_t* data, size_t len) {
    if (len < 1) return;
    using Network::MessageType;
    auto mt = static_cast<MessageType>(data[0]);

    if (mt == MessageType::ACTOR_CREATE) {
        Network::BufferReader r(data + 1, len - 1);
        uint16_t sn_len = r.read_u16();
        std::string scene_name = r.read_string(sn_len);
        uint16_t mp_len = r.read_u16();
        std::string model_path = r.read_string(mp_len);

        if (r.has_remaining(36 + sizeof(Network::ActorCreatePacked))) {
            const float* transform = reinterpret_cast<const float*>(r.data + r.pos);
            r.pos += 36;
            const auto* opt_packed = reinterpret_cast<const Network::ActorCreatePacked*>(r.data + r.pos);

            CFW_LOG_INFO("NetworkSystem: Received ACTOR_CREATE from {} — scene='{}' model='{}'",
                         sender_peer_id, scene_name, model_path);

            // Check if local file exists
            namespace fs = std::filesystem;
            fs::path full_path = fs::path(impl_->project_root) / model_path;
            if (fs::exists(full_path) && fs::is_regular_file(full_path)) {
                // File exists — queue actor creation
                Impl::PendingAction pa;
                pa.scene_name = scene_name;
                pa.model_path = model_path;
                pa.actor_packed = *opt_packed;
                impl_->pending_actor_creates.push_back(pa);
            } else {
                // File missing — save actor data and request file from peers
                impl_->pending_file_transfers[model_path] = {
                    scene_name, *opt_packed
                };
                auto pkt = Network::build_file_request(model_path);
                impl_->peer_manager.broadcast(Network::kChannelReliable,
                                              pkt.data(), pkt.size(), true);
            }
        }
    } else if (mt == MessageType::FILE_REQUEST) {
        handle_file_request(sender_peer_id, data, len);
    } else if (mt == MessageType::FILE_CHUNK) {
        handle_file_chunk(sender_peer_id, data, len);
    }
}

void NetworkSystem::handle_file_request(const std::string& sender_peer_id,
                                        const uint8_t* data, size_t len) {
    if (len < 3) return;
    Network::BufferReader r(data + 1, len - 1);
    uint16_t mp_len = r.read_u16();
    if (!r.has_remaining(mp_len)) return;
    std::string model_path = r.read_string(mp_len);

    namespace fs = std::filesystem;
    fs::path full_path = fs::path(impl_->project_root) / model_path;

    auto& cache = impl_->outgoing_cache[model_path];
    if (cache.data.empty()) {
        std::ifstream file(full_path, std::ios::binary | std::ios::ate);
        if (!file.is_open()) {
            CFW_LOG_ERROR("NetworkSystem: Cannot open file '{}' for FILE_REQUEST", full_path.string());
            impl_->outgoing_cache.erase(model_path);
            return;
        }
        cache.data.resize(static_cast<size_t>(file.tellg()));
        file.seekg(0);
        file.read(reinterpret_cast<char*>(cache.data.data()), cache.data.size());
        cache.load_time = Impl::Clock::now();
    }

    if (cache.data.empty()) return;

    constexpr uint32_t kChunkSize = 512 * 1024; // 512KB
    uint32_t total_size = static_cast<uint32_t>(cache.data.size());
    uint32_t chunk_count = (total_size + kChunkSize - 1) / kChunkSize;

    // Find sender's peer
    const auto* peer_info = impl_->peer_manager.find_peer(sender_peer_id);
    if (!peer_info || !peer_info->peer) {
        CFW_LOG_ERROR("NetworkSystem: Cannot find peer {} for FILE_CHUNK send", sender_peer_id);
        return;
    }

    for (uint32_t i = 0; i < chunk_count; ++i) {
        uint32_t offset = i * kChunkSize;
        uint32_t chunk_len = std::min(kChunkSize, total_size - offset);

        auto pkt = Network::build_file_chunk(
            model_path, total_size, i, chunk_count,
            cache.data.data() + offset, chunk_len);

        impl_->peer_manager.send_to(peer_info->peer, Network::kChannelReliable,
                                    pkt.data(), pkt.size(), true);
    }
}

void NetworkSystem::handle_file_chunk(const std::string& sender_peer_id,
                                      const uint8_t* data, size_t len) {
    if (len < 1 + 2) return;
    Network::BufferReader r(data + 1, len - 1);

    uint16_t mp_len = r.read_u16();
    if (!r.has_remaining(mp_len)) return;
    std::string model_path = r.read_string(mp_len);

    if (!r.has_remaining(4 + 4 + 4 + 4)) return;
    uint32_t total_size = r.read_u32();
    uint32_t chunk_index = r.read_u32();
    uint32_t chunk_count = r.read_u32();
    uint32_t chunk_data_len = r.read_u32();

    if (!r.has_remaining(chunk_data_len)) return;
    const uint8_t* chunk_data = r.data + r.pos;

    // Get or create transfer state — isolate by sender+path to prevent
    // chunk interleaving when multiple peers respond to one FILE_REQUEST.
    std::string tx_key = sender_peer_id + "/" + model_path;
    auto& tx = impl_->incoming_transfers[tx_key];
    if (tx.model_path.empty()) {
        tx.model_path = model_path;
        tx.sender_peer_id = sender_peer_id;
        tx.total_size = total_size;
        tx.chunk_count = chunk_count;
        tx.received_chunks.resize(chunk_count, false);
        tx.buffer.resize(total_size);
        tx.last_chunk_time = Impl::Clock::now();
    }

    // Write chunk into buffer
    uint32_t offset = chunk_index * 512 * 1024;
    if (offset + chunk_data_len <= total_size) {
        std::memcpy(tx.buffer.data() + offset, chunk_data, chunk_data_len);
        tx.received_chunks[chunk_index] = true;
        tx.last_chunk_time = Impl::Clock::now();
    }

    // Check if all chunks received
    bool all_received = true;
    for (bool rcvd : tx.received_chunks) {
        if (!rcvd) { all_received = false; break; }
    }

    if (!all_received) {
        return;
    }

    // All chunks received — write to disk
    namespace fs = std::filesystem;
    fs::path dest = fs::path(impl_->project_root) / model_path;
    std::error_code ec;
    fs::create_directories(dest.parent_path(), ec);

    std::ofstream out(dest, std::ios::binary);
    if (out.is_open()) {
        out.write(reinterpret_cast<const char*>(tx.buffer.data()), total_size);
        out.close();
    } else {
        CFW_LOG_ERROR("NetworkSystem: Failed to write file '{}'", dest.string());
        impl_->incoming_transfers.erase(model_path);
        return;
    }

    impl_->incoming_transfers.erase(tx_key);

    // If this transfer was triggered by an ACTOR_CREATE, push the
    // saved actor data as a PendingAction so the frontend creates the
    // actor.  No need to re-request ACTOR_CREATE from the original
    // sender — we already have everything.
    auto ft_it = impl_->pending_file_transfers.find(model_path);
    if (ft_it != impl_->pending_file_transfers.end()) {
        Impl::PendingAction pa;
        pa.scene_name = ft_it->second.scene_name;
        pa.model_path = model_path;
        pa.actor_packed = ft_it->second.actor_packed;
        impl_->pending_actor_creates.push_back(pa);
        impl_->pending_file_transfers.erase(ft_it);
    }
}

}  // namespace Corona::Systems
