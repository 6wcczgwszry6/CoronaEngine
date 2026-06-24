#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <iphlpapi.h>
#pragma comment(lib, "iphlpapi.lib")
#endif

#include "browser_manager.h"
#include "cef_client.h"
#include "cef_native_rpc.h"

#include <corona/events/acoustics_system_events.h>
#include <corona/kernel/core/kernel_context.h>
#include <corona/systems/network/network_system.h>

#include <algorithm>
#include <cctype>
#include <cstring>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace Corona::Systems::UI {

namespace {

std::shared_ptr<Corona::Systems::NetworkSystem> get_network_system() {
    auto sys_mgr = Corona::Kernel::KernelContext::instance().system_manager();
    if (!sys_mgr) {
        return nullptr;
    }
    return std::dynamic_pointer_cast<Corona::Systems::NetworkSystem>(
        sys_mgr->get_system("Network"));
}

Corona::Systems::NetworkSystem::SessionRole parse_network_session_role(
    const nlohmann::json& value) {
    if (!value.is_string()) {
        return Corona::Systems::NetworkSystem::SessionRole::Host;
    }
    const auto role = value.get<std::string>();
    if (role == "client") {
        return Corona::Systems::NetworkSystem::SessionRole::Client;
    }
    if (role == "none") {
        return Corona::Systems::NetworkSystem::SessionRole::None;
    }
    return Corona::Systems::NetworkSystem::SessionRole::Host;
}

std::string to_lower_ascii(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

bool looks_like_wlan_adapter(const std::string& adapter_name) {
    const std::string name = to_lower_ascii(adapter_name);
    return name.find("wlan") != std::string::npos ||
           name.find("wi-fi") != std::string::npos ||
           name.find("wifi") != std::string::npos ||
           name.find("wireless") != std::string::npos ||
           name.find("无线") != std::string::npos;
}

bool is_usable_ipv4(const std::string& ip) {
    return !ip.empty() && ip.rfind("127.", 0) != 0 && ip != "0.0.0.0";
}

std::string detect_hostname_ipv4() {
    char host_name[256] = {};
    if (gethostname(host_name, sizeof(host_name)) != 0) {
        return "127.0.0.1";
    }

    addrinfo hints{};
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_DGRAM;
    addrinfo* result = nullptr;
    if (getaddrinfo(host_name, nullptr, &hints, &result) != 0) {
        return "127.0.0.1";
    }

    std::string fallback = "127.0.0.1";
    for (addrinfo* it = result; it; it = it->ai_next) {
        auto* addr = reinterpret_cast<sockaddr_in*>(it->ai_addr);
        char ip[INET_ADDRSTRLEN] = {};
        if (!inet_ntop(AF_INET, &addr->sin_addr, ip, sizeof(ip))) {
            continue;
        }
        std::string candidate(ip);
        if (is_usable_ipv4(candidate)) {
            fallback = candidate;
            break;
        }
    }
    freeaddrinfo(result);
    return fallback;
}

#ifdef _WIN32
std::string wide_to_utf8(const wchar_t* value) {
    if (!value || !*value) {
        return {};
    }
    const int size = WideCharToMultiByte(CP_UTF8, 0, value, -1, nullptr, 0, nullptr, nullptr);
    if (size <= 1) {
        return {};
    }
    std::string result(static_cast<size_t>(size - 1), '\0');
    WideCharToMultiByte(CP_UTF8, 0, value, -1, result.data(), size, nullptr, nullptr);
    return result;
}

std::string ipv4_from_sockaddr(const sockaddr* address) {
    if (!address || address->sa_family != AF_INET) {
        return {};
    }
    const auto* addr = reinterpret_cast<const sockaddr_in*>(address);
    char ip[INET_ADDRSTRLEN] = {};
    if (!inet_ntop(AF_INET, &addr->sin_addr, ip, sizeof(ip))) {
        return {};
    }
    return std::string(ip);
}

bool adapter_has_ipv4_gateway(const IP_ADAPTER_ADDRESSES* adapter) {
    for (auto* gateway = adapter ? adapter->FirstGatewayAddress : nullptr; gateway; gateway = gateway->Next) {
        if (gateway->Address.lpSockaddr &&
            gateway->Address.lpSockaddr->sa_family == AF_INET) {
            return true;
        }
    }
    return false;
}
#endif

std::string detect_wlan_ipv4() {
#ifdef _WIN32
    WSADATA wsa{};
    const bool started = WSAStartup(MAKEWORD(2, 2), &wsa) == 0;
    std::string wlan_with_gateway;
    std::string wlan_fallback;
    std::string gateway_fallback;
    std::string any_fallback;

    ULONG buffer_size = 15000;
    std::vector<unsigned char> buffer(buffer_size);
    ULONG flags = GAA_FLAG_SKIP_ANYCAST |
                  GAA_FLAG_SKIP_MULTICAST |
                  GAA_FLAG_SKIP_DNS_SERVER |
                  GAA_FLAG_INCLUDE_GATEWAYS;
    ULONG result = GetAdaptersAddresses(
        AF_INET, flags, nullptr,
        reinterpret_cast<IP_ADAPTER_ADDRESSES*>(buffer.data()),
        &buffer_size);
    if (result == ERROR_BUFFER_OVERFLOW) {
        buffer.resize(buffer_size);
        result = GetAdaptersAddresses(
            AF_INET, flags, nullptr,
            reinterpret_cast<IP_ADAPTER_ADDRESSES*>(buffer.data()),
            &buffer_size);
    }

    if (result == NO_ERROR) {
        auto* adapters = reinterpret_cast<IP_ADAPTER_ADDRESSES*>(buffer.data());
        for (auto* adapter = adapters; adapter; adapter = adapter->Next) {
            if (adapter->OperStatus != IfOperStatusUp ||
                adapter->IfType == IF_TYPE_SOFTWARE_LOOPBACK) {
                continue;
            }

            std::string adapter_name = wide_to_utf8(adapter->FriendlyName);
            if (adapter->AdapterName) {
                adapter_name += " ";
                adapter_name += adapter->AdapterName;
            }
            const bool is_wlan = looks_like_wlan_adapter(adapter_name);
            const bool has_gateway = adapter_has_ipv4_gateway(adapter);

            for (auto* unicast = adapter->FirstUnicastAddress; unicast; unicast = unicast->Next) {
                const std::string ip = ipv4_from_sockaddr(unicast->Address.lpSockaddr);
                if (!is_usable_ipv4(ip)) {
                    continue;
                }
                if (is_wlan && has_gateway && wlan_with_gateway.empty()) {
                    wlan_with_gateway = ip;
                }
                if (is_wlan && wlan_fallback.empty()) {
                    wlan_fallback = ip;
                }
                if (has_gateway && gateway_fallback.empty()) {
                    gateway_fallback = ip;
                }
                if (any_fallback.empty()) {
                    any_fallback = ip;
                }
            }
        }
    }

    std::string selected = !wlan_with_gateway.empty() ? wlan_with_gateway :
                           !wlan_fallback.empty() ? wlan_fallback :
                           !gateway_fallback.empty() ? gateway_fallback :
                           !any_fallback.empty() ? any_fallback :
                           detect_hostname_ipv4();
    if (started) {
        WSACleanup();
    }
    return selected;
#else
    return detect_hostname_ipv4();
#endif
}

nlohmann::json build_network_session_info(
    const std::shared_ptr<Corona::Systems::NetworkSystem>& sys) {
    nlohmann::json payload;
    payload["ok"] = true;
    payload["active"] =
        sys->session_state() == Corona::Systems::NetworkSystem::SessionState::Active;
    payload["role"] = std::string(sys->session_role_name());
    payload["peer_count"] = static_cast<int>(sys->peer_count());
    payload["host_address"] = sys->host_address();
    payload["host_port"] = sys->host_port();
    payload["listen_port"] = sys->session_port();
    payload["local_ip"] = detect_wlan_ipv4();
    return payload;
}

void emit_lanchat_event_json(const std::string& event_json) {
    if (event_json.empty()) {
        return;
    }
    std::string js = "if(window.__coronaEmit)window.__coronaEmit(" +
                     nlohmann::json("lanchat-event").dump() + "," +
                     event_json + ",{\"_fromCross\":1})";
    for (auto& [tab_id, tab] : BrowserManager::instance().get_tabs()) {
        if (tab && !tab->minimized && tab->client && tab->client->GetBrowser()) {
            tab->client->GetBrowser()->GetMainFrame()->ExecuteJavaScript(js, "", 0);
        }
    }
}

nlohmann::json build_lanchat_members(
    const std::vector<Corona::Network::LanChatMember>& members) {
    nlohmann::json result = nlohmann::json::array();
    for (const auto& member : members) {
        result.push_back(member.nickname);
    }
    return result;
}

nlohmann::json build_lanchat_member_details(
    const std::vector<Corona::Network::LanChatMember>& members) {
    nlohmann::json result = nlohmann::json::array();
    for (const auto& member : members) {
        result.push_back({
            {"member_id", member.member_id},
            {"nickname", member.nickname},
            {"status", member.status},
        });
    }
    return result;
}

nlohmann::json build_lanchat_history(
    const std::vector<Corona::Network::LanChatMessage>& history) {
    nlohmann::json result = nlohmann::json::array();
    for (const auto& message : history) {
        result.push_back({
            {"message_id", message.message_id},
            {"sender_id", message.sender_id},
            {"room_id", message.room_id},
            {"seq", message.seq},
            {"from", message.sender_name},
            {"text", message.text},
            {"ts", message.timestamp_ms / 1000},
            {"sender_type", message.sender_type},
            {"message_kind", message.message_kind},
            {"target_agent_id", message.target_agent_id},
            {"source_user_id", message.source_user_id},
            {"correlation_id", message.correlation_id},
            {"metadata_json", message.metadata_json},
        });
    }
    return result;
}

nlohmann::json build_lanchat_history_rooms(
    const std::vector<Corona::Network::LanChatHistoryRoomSummary>& rooms) {
    nlohmann::json result = nlohmann::json::array();
    for (const auto& room : rooms) {
        const std::string load_id = room.session_id.empty() ? room.room_id : room.session_id;
        result.push_back({
            {"room_id", load_id},
            {"session_id", load_id},
            {"display_room_id", room.room_id},
            {"message_count", room.message_count},
            {"last_timestamp_ms", room.last_timestamp_ms},
            {"last_ts", room.last_timestamp_ms / 1000},
            {"last_sender_name", room.last_sender_name},
            {"last_text", room.last_text},
        });
    }
    return result;
}

nlohmann::json build_lanchat_agents(
    const std::vector<Corona::Network::LanChatAgent>& agents) {
    nlohmann::json result = nlohmann::json::array();
    for (const auto& agent : agents) {
        result.push_back({
            {"agent_id", agent.agent_id},
            {"name", agent.name},
            {"persona", agent.persona},
            {"owner", agent.owner_id},
        });
    }
    return result;
}

std::string make_agent_id(const std::string& owner, const std::string& name) {
    static uint64_t counter = 0;
    std::ostringstream out;
    out << "agent-" << std::hash<std::string>{}(owner + ":" + name) << "-" << ++counter;
    return out.str();
}

void read_transform_from_actor_json(const nlohmann::json& actor, float transform[9]) {
    if (!actor.contains("geometry")) {
        return;
    }
    const auto& geo = actor["geometry"];
    if (geo.contains("position") && geo["position"].is_array() && geo["position"].size() >= 3) {
        transform[0] = geo["position"][0].get<float>();
        transform[1] = geo["position"][1].get<float>();
        transform[2] = geo["position"][2].get<float>();
    }
    if (geo.contains("rotation") && geo["rotation"].is_array() && geo["rotation"].size() >= 3) {
        transform[3] = geo["rotation"][0].get<float>();
        transform[4] = geo["rotation"][1].get<float>();
        transform[5] = geo["rotation"][2].get<float>();
    }
    if (geo.contains("scale") && geo["scale"].is_array() && geo["scale"].size() >= 3) {
        transform[6] = geo["scale"][0].get<float>();
        transform[7] = geo["scale"][1].get<float>();
        transform[8] = geo["scale"][2].get<float>();
    }
}

NativeResult dispatch_method(const std::string& module,
                             const NativeMethodTable& methods,
                             const NativeRequest& request,
                             const NativeContext& context) {
    const auto it = methods.find(request.function);
    if (it == methods.end()) {
        return native_failure("Unknown " + module + " function: " + request.function);
    }
    try {
        return it->second(request, context);
    } catch (const std::exception& e) {
        return native_failure(e.what(), 2);
    } catch (...) {
        return native_failure(module + " native handler error", 2);
    }
}

std::shared_ptr<Corona::Systems::NetworkSystem> require_network_system() {
    return get_network_system();
}

}  // namespace

void register_scene_tools_rpc_handlers(NativeRpcRegistry& registry) {
    static const NativeMethodTable methods = {
        {"play_audio", [](const NativeRequest& request, const NativeContext&) {
            auto* event_bus = Corona::Kernel::KernelContext::instance().event_bus();
            if (!event_bus) {
                return native_failure("event_bus unavailable", 2);
            }
            const uint64_t rid = arg_uint64(request.args, 0);
            if (rid == 0) {
                return native_failure("invalid resource_id", 2);
            }
            const bool loop = arg_bool(request.args, 1, false);
            event_bus->publish<::Corona::Events::PlayAudioEvent>({rid, loop});

            nlohmann::json payload;
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"stop_audio", [](const NativeRequest& request, const NativeContext&) {
            auto* event_bus = Corona::Kernel::KernelContext::instance().event_bus();
            if (!event_bus) {
                return native_failure("event_bus unavailable", 2);
            }
            const uint64_t rid = arg_uint64(request.args, 0);
            if (rid == 0) {
                return native_failure("invalid resource_id", 2);
            }
            event_bus->publish<::Corona::Events::StopAudioEvent>({rid});

            nlohmann::json payload;
            payload["ok"] = true;
            return native_success(payload);
        }},
    };

    registry.register_module("SceneTools", [](const NativeRequest& request,
                                              const NativeContext& context) {
        const auto it = methods.find(request.function);
        if (it == methods.end()) {
            return native_unhandled();
        }
        try {
            return it->second(request, context);
        } catch (const std::exception& e) {
            return native_failure(e.what(), 2);
        } catch (...) {
            return native_failure("SceneTools native handler error", 2);
        }
    });
}

void register_network_rpc_handlers(NativeRpcRegistry& registry) {
    static const NativeMethodTable methods = {
        {"start_session", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const std::string name = arg_string(request.args, 0);
            const uint64_t project_id = arg_uint64(request.args, 1);
            const uint16_t port = arg_uint16(request.args, 2, 27960);
            const auto role = request.args.size() > 3
                ? parse_network_session_role(request.args[3])
                : Corona::Systems::NetworkSystem::SessionRole::Host;

            const bool ok = sys->start_session(name, project_id, port, role);
            auto payload = build_network_session_info(sys);
            payload["ok"] = ok;
            return native_success(payload);
        }},
        {"stop_session", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->stop_session();
            return native_success({{"ok", true}});
        }},
        {"get_peer_count", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success(build_network_session_info(sys));
        }},
        {"get_session_info", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success(build_network_session_info(sys));
        }},
        {"connect_to_peer", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const std::string ip = arg_string(request.args, 0);
            const uint16_t port = arg_uint16(request.args, 1, 27960);
            const std::string peer_name = arg_string(request.args, 2);
            const bool ok = sys->connect_to_peer(ip, port, peer_name);
            auto payload = build_network_session_info(sys);
            payload["ok"] = ok;
            return native_success(payload);
        }},
        {"set_project_root", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const std::string root = arg_string(request.args, 0);
            if (!root.empty()) {
                sys->set_project_root(root);
            }
            return native_success({{"ok", true}});
        }},
        {"poll_pending_actor_create", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string actor_guid, scene_name, model_path, actor_json;
            Corona::Network::ActorCreatePacked packed;
            if (sys->pop_pending_actor_create(actor_guid, scene_name, model_path,
                                               &packed, sizeof(packed), &actor_json)) {
                payload["has_pending"] = true;
                payload["actor_guid"] = actor_guid;
                payload["scene_name"] = scene_name;
                payload["model_path"] = model_path;
                nlohmann::json actor_data = nlohmann::json::object();
                if (!actor_json.empty()) {
                    try {
                        actor_data = nlohmann::json::parse(actor_json);
                        if (!actor_data.is_object()) {
                            actor_data = nlohmann::json::object();
                        }
                    } catch (const nlohmann::json::parse_error&) {
                        actor_data = nlohmann::json::object();
                    }
                }
                actor_data["geometry"]["position"] = {
                    packed.transform[0], packed.transform[1], packed.transform[2]
                };
                actor_data["geometry"]["rotation"] = {
                    packed.transform[3], packed.transform[4], packed.transform[5]
                };
                actor_data["geometry"]["scale"] = {
                    packed.transform[6], packed.transform[7], packed.transform[8]
                };
                payload["actor_data"] = actor_data;
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"poll_pending_actor_transform", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string actor_guid, scene_name, source_user_id, correlation_id;
            float transform[9] = {0,0,0, 0,0,0, 1,1,1};
            if (sys->pop_pending_actor_transform_update(
                    actor_guid, scene_name, transform, 9,
                    source_user_id, correlation_id)) {
                payload["has_pending"] = true;
                payload["actor_guid"] = actor_guid;
                payload["scene_name"] = scene_name;
                payload["source_user_id"] = source_user_id;
                payload["correlation_id"] = correlation_id;
                payload["geometry"]["position"] = {transform[0], transform[1], transform[2]};
                payload["geometry"]["rotation"] = {transform[3], transform[4], transform[5]};
                payload["geometry"]["scale"] = {transform[6], transform[7], transform[8]};
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"poll_pending_actor_delete", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string actor_guid, scene_name, actor_name;
            if (sys->pop_pending_actor_delete(actor_guid, scene_name, actor_name)) {
                payload["has_pending"] = true;
                payload["actor_guid"] = actor_guid;
                payload["scene_name"] = scene_name;
                payload["actor_name"] = actor_name;
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"poll_pending_actor_scene_snapshot_request", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string scene_name;
            if (sys->pop_pending_actor_scene_snapshot_request(scene_name)) {
                payload["has_pending"] = true;
                payload["scene_name"] = scene_name;
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"poll_pending_actor_scene_snapshot", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string scene_name, snapshot_json;
            if (sys->pop_pending_actor_scene_snapshot(scene_name, snapshot_json)) {
                payload["has_pending"] = true;
                payload["scene_name"] = scene_name;
                payload["snapshot_json"] = snapshot_json;
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"poll_pending_actor_state_update", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string actor_guid, scene_name, actor_json;
            if (sys->pop_pending_actor_state_update(actor_guid, scene_name, actor_json)) {
                payload["has_pending"] = true;
                payload["actor_guid"] = actor_guid;
                payload["scene_name"] = scene_name;
                payload["actor_json"] = actor_json;
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"set_sync_paused", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->set_sync_paused(arg_bool(request.args, 0, false));
            return native_success({{"ok", true}});
        }},
        {"register_actor_identity", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const std::string actor_guid = arg_string(request.args, 0);
            const std::uintptr_t actor_handle = arg_uintptr(request.args, 1);
            const bool locally_owned = arg_bool(request.args, 2, true);
            const bool ok = sys->register_actor_identity(actor_guid, actor_handle, locally_owned);
            return native_success({{"ok", ok}});
        }},
        {"claim_actor_ownership", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const bool ok = sys->claim_actor_ownership(arg_string(request.args, 0));
            return native_success({{"ok", ok}});
        }},
        {"broadcast_actor_transform", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const std::string actor_guid = arg_string(request.args, 0);
            const std::string scene_name = arg_string(request.args, 1);
            float transform[9] = {0,0,0, 0,0,0, 1,1,1};
            std::string source_user_id;
            std::string correlation_id;
            const auto actor_data = arg_object(request.args, 2);
            if (!actor_data.empty()) {
                read_transform_from_actor_json(actor_data, transform);
                source_user_id = actor_data.value("source_user_id", "");
                correlation_id = actor_data.value("correlation_id", "");
            }
            sys->broadcast_actor_transform_update(
                actor_guid, scene_name, transform, source_user_id, correlation_id);
            return native_success({{"ok", true}});
        }},
        {"broadcast_actor_delete", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->broadcast_actor_delete(
                arg_string(request.args, 0),
                arg_string(request.args, 1),
                arg_string(request.args, 2));
            return native_success({{"ok", true}});
        }},
        {"request_actor_scene_snapshot", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->request_actor_scene_snapshot(arg_string(request.args, 0));
            return native_success({{"ok", true}});
        }},
        {"broadcast_actor_scene_snapshot", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            std::string snapshot_json;
            if (request.args.size() > 1) {
                snapshot_json = request.args[1].is_string()
                    ? request.args[1].get<std::string>()
                    : request.args[1].dump();
            }
            sys->broadcast_actor_scene_snapshot(arg_string(request.args, 0), snapshot_json);
            return native_success({{"ok", true}});
        }},
        {"broadcast_actor_state_update", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            std::string actor_json;
            if (request.args.size() > 2) {
                actor_json = request.args[2].is_string()
                    ? request.args[2].get<std::string>()
                    : request.args[2].dump();
            }
            sys->broadcast_actor_state_update(
                arg_string(request.args, 0),
                arg_string(request.args, 1),
                actor_json);
            return native_success({{"ok", true}});
        }},
        {"broadcast_actor_create", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            std::string actor_guid = arg_string(request.args, 0);
            const std::string scene_name = arg_string(request.args, 1);
            const std::string model_path = arg_string(request.args, 2);
            float transform[9] = {0,0,0, 0,0,0, 1,1,1};
            std::vector<std::string> dependency_paths;
            std::string actor_json;
            const auto actor_data = arg_object(request.args, 3);
            if (!actor_data.empty()) {
                actor_json = actor_data.dump();
                if (actor_guid.empty() &&
                    actor_data.contains("actor_guid") &&
                    actor_data["actor_guid"].is_string()) {
                    actor_guid = actor_data["actor_guid"].get<std::string>();
                }
                if (actor_data.contains("model_dependencies") &&
                    actor_data["model_dependencies"].is_array()) {
                    for (const auto& dep : actor_data["model_dependencies"]) {
                        if (dep.is_string()) {
                            dependency_paths.push_back(dep.get<std::string>());
                        }
                    }
                }
                read_transform_from_actor_json(actor_data, transform);
            }
            if (actor_guid.empty()) {
                actor_guid = scene_name + ":" + model_path;
            }

            Corona::Network::ActorCreatePacked opt;
            std::memset(&opt, 0, sizeof(opt));
            opt.visible = true;
            opt.bEnableLighting = true;
            opt.metallic = 0.0f;
            opt.roughness = 0.5f;
            opt.specular = 0.5f;
            opt.specularTint = 0.0f;
            opt.sheen = 0.0f;
            opt.sheenTint = 0.5f;
            opt.clearcoat = 0.0f;
            opt.clearcoatGloss = 1.0f;
            opt.ambient[0] = 0.2f; opt.ambient[1] = 0.2f; opt.ambient[2] = 0.2f;
            opt.diffuse[0] = 0.8f; opt.diffuse[1] = 0.8f; opt.diffuse[2] = 0.8f;
            opt.specular_color[0] = 1.0f; opt.specular_color[1] = 1.0f; opt.specular_color[2] = 1.0f;
            opt.shininess = 32.0f;

            sys->broadcast_actor_create(actor_guid, scene_name, model_path,
                                        dependency_paths, transform,
                                        &opt, sizeof(opt), actor_json);
            return native_success({{"ok", true}});
        }},
    };

    registry.register_module("Network", [](const NativeRequest& request,
                                           const NativeContext& context) {
        return dispatch_method("Network", methods, request, context);
    });
}

void register_lanchat_rpc_handlers(NativeRpcRegistry& registry) {
    static const NativeMethodTable methods = {
        {"start_room", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->set_lanchat_event_callback(emit_lanchat_event_json);
            const auto payload_arg = arg_object(request.args, 0);
            const std::string room = payload_arg.value("room", "");
            const uint16_t port = payload_arg.value("port", 27960);
            const std::string nickname = payload_arg.value("nickname", "房主");
            const bool restore_history = payload_arg.value("restore_history", false);
            const std::string history_room = payload_arg.value("history_room", room);
            const std::string host_nickname = nickname.empty() ? "房主" : nickname;
            const bool ok = sys->lanchat_start_room(room, host_nickname, port);
            bool restored_history = false;
            if (ok && restore_history) {
                restored_history = sys->lanchat_restore_history_room(history_room);
            }
            const uint16_t actual_port = sys->session_port() != 0 ? sys->session_port() : port;
            nlohmann::json data;
            data["ok"] = ok;
            data["you"] = host_nickname;
            data["ip"] = detect_wlan_ipv4();
            data["port"] = actual_port;
            data["room"] = room;
            data["peer_id"] = sys->local_peer_id();
            data["members"] = build_lanchat_members(sys->lanchat_members());
            data["member_details"] = build_lanchat_member_details(sys->lanchat_members());
            data["history"] = build_lanchat_history(sys->lanchat_history());
            data["agents"] = build_lanchat_agents(sys->lanchat_agents());
            data["restored_history"] = restored_history;
            return native_success(data);
        }},
        {"start_local_room", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->set_lanchat_event_callback(emit_lanchat_event_json);
            const auto payload_arg = arg_object(request.args, 0);
            const std::string room = payload_arg.value("room", "");
            const std::string nickname = payload_arg.value("nickname", "房主");
            const bool restore_history = payload_arg.value("restore_history", false);
            const std::string history_room = payload_arg.value("history_room", room);
            const std::string host_nickname = nickname.empty() ? "房主" : nickname;
            const bool ok = sys->lanchat_start_local_room(room, host_nickname);
            bool restored_history = false;
            if (ok && restore_history) {
                restored_history = sys->lanchat_restore_history_room(history_room);
            }
            nlohmann::json data;
            data["ok"] = ok;
            data["you"] = host_nickname;
            data["ip"] = "";
            data["port"] = 0;
            data["room"] = room;
            data["mode"] = "single";
            data["peer_id"] = "local-single-player";
            data["members"] = build_lanchat_members(sys->lanchat_members());
            data["member_details"] = build_lanchat_member_details(sys->lanchat_members());
            data["history"] = build_lanchat_history(sys->lanchat_history());
            data["agents"] = build_lanchat_agents(sys->lanchat_agents());
            data["restored_history"] = restored_history;
            return native_success(data);
        }},
        {"stop_room", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->lanchat_leave_room();
            sys->stop_session();
            return native_success({{"ok", true}});
        }},
        {"stop_local_room", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->lanchat_stop_local_room();
            return native_success({{"ok", true}});
        }},
        {"get_history", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success({
                {"ok", true},
                {"history", build_lanchat_history(sys->lanchat_history())},
            });
        }},
        {"list_history_rooms", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success({
                {"ok", true},
                {"rooms", build_lanchat_history_rooms(sys->lanchat_history_rooms())},
            });
        }},
        {"load_history_room", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const auto payload_arg = arg_object(request.args, 0);
            const std::string room = payload_arg.value("room", "");
            nlohmann::json data;
            data["ok"] = !room.empty();
            data["room"] = room;
            data["history"] = room.empty()
                ? nlohmann::json::array()
                : build_lanchat_history(sys->lanchat_load_history_room(room));
            data["agents"] = room.empty()
                ? nlohmann::json::array()
                : build_lanchat_agents(sys->lanchat_load_history_agents(room));
            if (room.empty()) {
                data["error"] = "ROOM_REQUIRED";
            }
            return native_success(data);
        }},
        {"join_room", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->set_lanchat_event_callback(emit_lanchat_event_json);
            const auto payload_arg = arg_object(request.args, 0);
            const std::string ip = payload_arg.value("ip", "");
            const uint16_t port = payload_arg.value("port", 27960);
            const std::string room = payload_arg.value("room", "");
            const std::string nickname = payload_arg.value("nickname", "Guest");
            const bool ok = sys->lanchat_join_room(ip, port, room, nickname);
            nlohmann::json data;
            data["ok"] = ok;
            data["you"] = nickname;
            data["peer_id"] = sys->local_peer_id();
            data["port"] = sys->host_port() != 0 ? sys->host_port() : port;
            data["members"] = build_lanchat_members(sys->lanchat_members());
            data["member_details"] = build_lanchat_member_details(sys->lanchat_members());
            data["history"] = build_lanchat_history(sys->lanchat_history());
            data["agents"] = build_lanchat_agents(sys->lanchat_agents());
            if (!ok) {
                data["error"] = "JOIN_FAILED";
            }
            return native_success(data);
        }},
        {"leave_room", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->lanchat_leave_room();
            return native_success({{"ok", true}});
        }},
        {"send_message", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const auto payload_arg = arg_object(request.args, 0);
            const std::string text = payload_arg.value("text", "");
            const std::string message_kind = payload_arg.value("message_kind", "chat");
            const std::string target_agent_id = payload_arg.value("target_agent_id", "");
            const std::string source_user_id = payload_arg.value("source_user_id", "");
            const std::string correlation_id = payload_arg.value("correlation_id", "");
            std::string metadata_json;
            if (payload_arg.contains("metadata_json")) {
                metadata_json = payload_arg.value("metadata_json", "");
            } else if (payload_arg.contains("metadata")) {
                metadata_json = payload_arg["metadata"].dump();
            }
            const auto result = sys->lanchat_send_message_ex(
                text, message_kind, target_agent_id, source_user_id,
                correlation_id, metadata_json);
            nlohmann::json data;
            data["ok"] = result.accepted;
            if (result.accepted) {
                data["message_id"] = result.message.message_id;
                data["seq"] = result.message.seq;
            } else {
                data["error"] = result.error.empty() ? "SEND_FAILED" : result.error;
            }
            return native_success(data);
        }},
        {"add_agent", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const auto payload_arg = arg_object(request.args, 0);
            const std::string name = payload_arg.value("name", "Agent");
            const std::string persona = payload_arg.value("persona", "");
            const std::string peer_id = sys->local_peer_id().empty()
                ? "local-single-player"
                : sys->local_peer_id();
            const std::string agent_id = make_agent_id(peer_id, name);
            const auto result = sys->lanchat_register_agent(agent_id, name, persona);
            nlohmann::json data;
            data["ok"] = result.ok;
            data["agent_id"] = agent_id;
            data["name"] = name;
            if (!result.ok) {
                data["error"] = result.error;
            }
            return native_success(data);
        }},
        {"remove_agent", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const auto payload_arg = arg_object(request.args, 0);
            const auto result = sys->lanchat_remove_agent(payload_arg.value("agent_id", ""));
            nlohmann::json data;
            data["ok"] = result.ok;
            if (!result.ok) {
                data["error"] = result.error;
            }
            return native_success(data);
        }},
        {"list_agents", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success({
                {"ok", true},
                {"agents", build_lanchat_agents(sys->lanchat_agents())},
            });
        }},
        {"get_local_ip", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success({
                {"ok", true},
                {"ip", detect_wlan_ipv4()},
                {"port", sys->session_port() != 0 ? sys->session_port() : 27960},
            });
        }},
    };

    registry.register_module("LANChat", [](const NativeRequest& request,
                                           const NativeContext& context) {
        return dispatch_method("LANChat", methods, request, context);
    });
}

}  // namespace Corona::Systems::UI
