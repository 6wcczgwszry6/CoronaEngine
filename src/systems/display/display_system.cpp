#include <corona/events/display_system_events.h>
#include <corona/events/engine_events.h>
#include <corona/kernel/core/i_logger.h>
#include <corona/kernel/event/i_event_bus.h>
#include <corona/kernel/event/i_event_stream.h>
#include <corona/shared_data_hub.h>
#include <corona/systems/display/display_system.h>

#include <algorithm>
#include <array>
#include <exception>
#include <ranges>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace {
struct PixelExtent {
    uint32_t width = 0;
    uint32_t height = 0;

    [[nodiscard]] explicit operator bool() const noexcept {
        return width != 0 && height != 0;
    }
};

[[nodiscard]] PixelExtent hardware_image_extent(const Corona::Horizon::HardwareImage& image) {
    if (!image) {
        return {};
    }
    const auto extent = image.extent();
    return {extent.width, extent.height};
}

[[nodiscard]] PixelExtent max_extent(PixelExtent lhs, PixelExtent rhs) {
    return {std::max(lhs.width, rhs.width), std::max(lhs.height, rhs.height)};
}

[[nodiscard]] PixelExtent surface_client_extent(void* surface) {
#ifdef _WIN32
    if (surface == nullptr) {
        return {};
    }

    RECT rect{};
    if (!GetClientRect(reinterpret_cast<HWND>(surface), &rect)) {
        return {};
    }

    const auto width = rect.right - rect.left;
    const auto height = rect.bottom - rect.top;
    if (width <= 0 || height <= 0) {
        return {};
    }
    return {static_cast<uint32_t>(width), static_cast<uint32_t>(height)};
#else
    (void)surface;
    return {};
#endif
}

[[nodiscard]] bool is_vulkan_device_lost_message(std::string_view message) {
    return message.find("VK_ERROR_DEVICE_LOST") != std::string_view::npos ||
           message.find("VkResult=-4") != std::string_view::npos ||
           message.find("Vulkan device is lost") != std::string_view::npos ||
           message.find("Queue acquire skipped because the Vulkan device is lost") != std::string_view::npos ||
           message.find("vkGetSemaphoreCounterValue returned UINT64_MAX") != std::string_view::npos;
}
}  // namespace

namespace Corona::Systems {
bool DisplaySystem::initialize(Kernel::ISystemContext* ctx) {
    shutting_down_.store(false, std::memory_order_release);
    shutdown_resources_destroyed_.store(false, std::memory_order_release);
    auto* event_bus = ctx->event_bus();
    if (event_bus == nullptr) {
        CFW_LOG_WARNING("DisplaySystem: No event bus available");
        return true;
    }

    surface_changed_sub_id_ = event_bus->subscribe<Events::DisplaySurfaceChangedEvent>(
        [this](const Events::DisplaySurfaceChangedEvent& event) {
            if (event.surface == nullptr) {
                if (event.registration_ticket) {
                    event.registration_ticket->fail(
                        "Display surface registration failed: surface is null");
                }
                return;
            }

            const auto surface_id = reinterpret_cast<uint64_t>(event.surface);
            std::shared_ptr<Detail::SurfaceLifecycleAcks> acknowledgements;
            std::string rejection;
            bool cancelled = false;
            {
                std::lock_guard<std::mutex> lock(frame_mutex_);
                if (shutting_down_.load(std::memory_order_acquire)) {
                    rejection =
                        "Display surface registration cancelled: Display is shutting down";
                    cancelled = true;
                } else if (device_lost_.load(std::memory_order_acquire)) {
                    rejection =
                        "Display surface registration failed: Vulkan device is lost";
                } else if (!surface_frame_gate_.activate(surface_id)) {
                    rejection =
                        "Display surface registration cancelled: removal is pending";
                    cancelled = true;
                } else {
                    const bool begins_new_lifetime =
                        removed_surfaces_.erase(surface_id) != 0;
                    auto& stored = surface_acknowledgements_[surface_id];
                    if (begins_new_lifetime || !stored) {
                        stored =
                            std::make_shared<Detail::SurfaceLifecycleAcks>();
                    }
                    acknowledgements = stored;
                    surfaces_[surface_id] = event.surface;
                    pending_surfaces_.push_back(event.surface);
                }
            }

            if (acknowledgements) {
                acknowledgements->add_registration(event.registration_ticket);
            } else if (event.registration_ticket) {
                if (cancelled) {
                    event.registration_ticket->cancel(std::move(rejection));
                } else {
                    event.registration_ticket->fail(std::move(rejection));
                }
            }
        });

    // Published synchronously on the MAIN thread when an ImGui secondary viewport window
    // is being destroyed. We only buffer the request (+ promise) here and return; the
    // actual GPU-idle + displayer teardown happens in update() on the Display thread,
    // which then fulfills the promise. The publisher (main thread) blocks on that promise
    // so the OS window is not destroyed until our swapchain is gone. Must NOT block here:
    // this handler runs on the main thread, and blocking while holding frame_mutex_ would
    // deadlock against update()'s own frame_mutex_ acquisition.
    surface_removed_sub_id_ = event_bus->subscribe<Events::DisplaySurfaceRemovedEvent>(
        [this](const Events::DisplaySurfaceRemovedEvent& event) {
            if (event.surface == nullptr) {
                Detail::SurfaceLifecycleAcks acknowledgements;
                acknowledgements.removal_requested(event.removal_ticket, event.done);
                acknowledgements.removal_succeeded();
                return;
            }

            const auto surface_id = reinterpret_cast<uint64_t>(event.surface);
            auto retirement = surface_frame_gate_.retire(surface_id);
            std::shared_ptr<Detail::SurfaceLifecycleAcks> acknowledgements;
            bool resources_already_destroyed = false;
            {
                std::lock_guard<std::mutex> lock(frame_mutex_);
                resources_already_destroyed =
                    shutdown_resources_destroyed_.load(
                        std::memory_order_acquire);
                if (!resources_already_destroyed) {
                    auto& stored = surface_acknowledgements_[surface_id];
                    if (!stored) {
                        stored =
                            std::make_shared<Detail::SurfaceLifecycleAcks>();
                    }
                    acknowledgements = stored;
                    removed_surfaces_.insert(surface_id);
                    surfaces_.erase(surface_id);
                    surface_states_.erase(surface_id);
                    pending_surfaces_.erase(
                        std::remove_if(pending_surfaces_.begin(),
                                       pending_surfaces_.end(),
                                       [surface_id](void* s) {
                                           return reinterpret_cast<uint64_t>(s) ==
                                                  surface_id;
                                       }),
                        pending_surfaces_.end());
                    pending_removals_.push_back(
                        {event.surface,
                         std::move(retirement),
                         acknowledgements});
                }
            }

            if (resources_already_destroyed) {
                Detail::SurfaceLifecycleAcks completed;
                completed.removal_requested(event.removal_ticket, event.done);
                surface_frame_gate_.forget(surface_id);
                completed.removal_succeeded();
                return;
            }
            acknowledgements->removal_requested(event.removal_ticket, event.done);
        });

    optics_frame_sub_id_ = event_bus->subscribe<Events::OpticsFrameReadyEvent>(
        [this](const Events::OpticsFrameReadyEvent& event) {
            if (event.surface == nullptr ||
                event.image_handle == 0) {
                return;
            }

            const auto surface_id = reinterpret_cast<uint64_t>(event.surface);
            std::lock_guard<std::mutex> lock(frame_mutex_);
            if (shutting_down_.load(std::memory_order_acquire) ||
                removed_surfaces_.contains(surface_id)) {
                return;
            }
            auto& layer = surface_states_[surface_id].optics;
            if (event.frame_index >= layer.frame_index) {
                layer.image_handle = event.image_handle;
                layer.frame_index = event.frame_index;
                layer.width = event.width;
                layer.height = event.height;
                layer.viewport_x = event.viewport_x;
                layer.viewport_y = event.viewport_y;
                layer.viewport_width = event.viewport_width;
                layer.viewport_height = event.viewport_height;
            }
        });

    ui_frame_sub_id_ = event_bus->subscribe<Events::UIFrameReadyEvent>(
        [this](const Events::UIFrameReadyEvent& event) {
            if (event.surface == nullptr) {
                if (event.first_present_ticket) {
                    event.first_present_ticket->fail(
                        "Display first present failed: surface is null");
                }
                return;
            }

            const auto surface_id = reinterpret_cast<uint64_t>(event.surface);
            std::shared_ptr<Detail::SurfaceLifecycleAcks> acknowledgements;
            bool removed = false;
            bool device_lost = false;
            bool shutting_down = false;
            Detail::SurfaceLifecycleAcks::FirstPresentBoundary
                first_present_boundary = 0;
            {
                std::lock_guard<std::mutex> lock(frame_mutex_);
                removed = removed_surfaces_.contains(surface_id);
                shutting_down =
                    shutting_down_.load(std::memory_order_acquire);
                if (!removed && !shutting_down) {
                    auto& stored = surface_acknowledgements_[surface_id];
                    if (!stored) {
                        stored =
                            std::make_shared<Detail::SurfaceLifecycleAcks>();
                    }
                    acknowledgements = stored;
                    first_present_boundary =
                        acknowledgements->add_first_present(
                            event.first_present_ticket);
                    device_lost = device_lost_.load(std::memory_order_acquire);
                    if (!device_lost && event.image_handle != 0) {
                        auto& layer = surface_states_[surface_id].ui;
                        if (event.frame_index >= layer.frame_index) {
                            layer.image_handle = event.image_handle;
                            layer.frame_index = event.frame_index;
                            layer.width = event.width;
                            layer.height = event.height;
                            layer.first_present_boundary =
                                first_present_boundary;
                        }
                    }
                }
            }

            if (removed) {
                if (event.first_present_ticket) {
                    event.first_present_ticket->cancel(
                        "Display first present cancelled: surface is removed");
                }
                return;
            }

            if (shutting_down) {
                if (event.first_present_ticket) {
                    event.first_present_ticket->cancel(
                        "Display first present cancelled: Display is shutting down");
                }
                return;
            }

            if (device_lost) {
                acknowledgements->fail_forward(
                    "Display first present failed: Vulkan device is lost");
            }
        });

    const auto initialization_failed =
        [this, event_bus](std::string message) {
            shutting_down_.store(true, std::memory_order_release);
            if (surface_changed_sub_id_ != 0) {
                event_bus->unsubscribe(surface_changed_sub_id_);
                surface_changed_sub_id_ = 0;
            }
            if (surface_removed_sub_id_ != 0) {
                event_bus->unsubscribe(surface_removed_sub_id_);
                surface_removed_sub_id_ = 0;
            }
            if (optics_frame_sub_id_ != 0) {
                event_bus->unsubscribe(optics_frame_sub_id_);
                optics_frame_sub_id_ = 0;
            }
            if (ui_frame_sub_id_ != 0) {
                event_bus->unsubscribe(ui_frame_sub_id_);
                ui_frame_sub_id_ = 0;
            }

            std::vector<std::pair<
                std::uint64_t,
                std::shared_ptr<Detail::SurfaceLifecycleAcks>>>
                acknowledgements;
            {
                std::lock_guard lock(frame_mutex_);
                acknowledgements.reserve(surface_acknowledgements_.size());
                for (const auto& [surface_id, pending_acknowledgements] :
                     surface_acknowledgements_) {
                    acknowledgements.emplace_back(
                        surface_id, pending_acknowledgements);
                }
                pending_surfaces_.clear();
                pending_removals_.clear();
                surface_states_.clear();
                surfaces_.clear();
                removed_surfaces_.clear();
                surface_acknowledgements_.clear();
            }

            for (const auto& [surface_id, pending_acknowledgements] : acknowledgements) {
                (void)pending_acknowledgements;
                auto retirement = surface_frame_gate_.retire(surface_id);
                retirement.wait();
                surface_frame_gate_.forget(surface_id);
            }
            transparent_storage_ = Horizon::HardwareImage();

            std::vector<PendingRemoval> late_removals;
            {
                std::lock_guard lock(frame_mutex_);
                late_removals.swap(pending_removals_);
                for (const auto& [surface_id, pending_acknowledgements] :
                     surface_acknowledgements_) {
                    acknowledgements.emplace_back(
                        surface_id, pending_acknowledgements);
                }
                pending_surfaces_.clear();
                surface_states_.clear();
                surfaces_.clear();
                removed_surfaces_.clear();
                surface_acknowledgements_.clear();
                shutdown_resources_destroyed_.store(
                    true, std::memory_order_release);
            }
            for (auto& removal : late_removals) {
                const auto surface_id =
                    reinterpret_cast<std::uint64_t>(removal.surface);
                removal.retirement.wait();
                surface_frame_gate_.forget(surface_id);
                if (removal.acknowledgements) {
                    acknowledgements.emplace_back(
                        surface_id, removal.acknowledgements);
                }
            }
            for (const auto& [surface_id, pending_acknowledgements] :
                 acknowledgements) {
                (void)surface_id;
                if (pending_acknowledgements) {
                    pending_acknowledgements->fail_forward(message);
                    pending_acknowledgements->removal_succeeded();
                }
            }
            CFW_LOG_ERROR("DisplaySystem: {}", message);
            return false;
        };

    // Create 1x1 transparent fallback images for single-layer compositing.
    // Porter-Duff Source Over with a transparent layer is an identity operation.
    try {
        auto transparent_storage_desc = Horizon::HardwareImageDesc::texture_2d(
            1,
            1,
            Horizon::Format::RGBA16_FLOAT,
            Horizon::ImageUsageFlags::Storage |
                Horizon::ImageUsageFlags::TransferDst,
            "display.transparent_storage");
        transparent_storage_desc.cpu_access = Horizon::CpuAccessMode::Write;
        transparent_storage_ = Horizon::HardwareImage(transparent_storage_desc);

        if (!transparent_storage_) {
            return initialization_failed(
                "initialization failed: transparent fallback image was not created");
        }

        const std::array<std::uint16_t, 4> zero_rgba16f = {0, 0, 0, 0};
        (void)transparent_storage_.write(
            std::span<const std::uint16_t>(zero_rgba16f));
    } catch (const std::exception& error) {
        return initialization_failed(
            std::string("initialization failed while creating fallback image: ") +
            error.what());
    } catch (...) {
        return initialization_failed(
            "initialization failed while creating fallback image: unknown exception");
    }

    return true;
}

void DisplaySystem::update() {
    // Snapshot shared state and process pending displayer creation under lock,
    // then release before GPU work. displayers_ is only modified here, so
    // iterating it after the lock is safe.
    std::unordered_map<uint64_t, SurfaceState> states_snapshot;
    std::unordered_map<uint64_t, void*> surfaces_snapshot;
    std::unordered_map<uint64_t, Detail::SurfaceFrameGate::Snapshot>
        frame_gate_snapshot;
    std::unordered_map<uint64_t, std::shared_ptr<Detail::SurfaceLifecycleAcks>>
        acknowledgements_snapshot;
    std::vector<PendingRemoval> removals;
    {
        std::lock_guard<std::mutex> lock(frame_mutex_);

        // Drain teardown requests first. Drop any matching state and any not-yet-created
        // surface so the creation loop below does not resurrect a surface being removed.
        removals.swap(pending_removals_);
        if (!removals.empty()) {
            for (const auto& r : removals) {
                const auto surface_id = reinterpret_cast<uint64_t>(r.surface);
                removed_surfaces_.insert(surface_id);
                surfaces_.erase(surface_id);
                surface_states_.erase(surface_id);
            }
            pending_surfaces_.erase(
                std::remove_if(pending_surfaces_.begin(), pending_surfaces_.end(),
                               [&](void* s) {
                                   const auto sid = reinterpret_cast<uint64_t>(s);
                                   for (const auto& r : removals) {
                                       if (reinterpret_cast<uint64_t>(r.surface) == sid) {
                                           return true;
                                       }
                                   }
                                   return false;
                               }),
                pending_surfaces_.end());
        }

        for (auto* surface : pending_surfaces_) {
            const auto surface_id = reinterpret_cast<uint64_t>(surface);
            const auto acknowledgements_it =
                surface_acknowledgements_.find(surface_id);
            const auto acknowledgements =
                acknowledgements_it != surface_acknowledgements_.end()
                    ? acknowledgements_it->second
                    : nullptr;

            if (removed_surfaces_.contains(surface_id)) {
                if (acknowledgements) {
                    acknowledgements->cancel_forward(
                        "Display surface registration cancelled: surface is removed");
                }
                continue;
            }
            if (device_lost_.load(std::memory_order_acquire)) {
                if (acknowledgements) {
                    acknowledgements->registration_failed(
                        "Display surface registration failed: Vulkan device is lost");
                }
                continue;
            }

            surfaces_[surface_id] = surface;
            try {
                auto displayer_it = displayers_.find(surface_id);
                if (displayer_it == displayers_.end()) {
                    displayer_it =
                        displayers_.try_emplace(surface_id, surface).first;
                }
                if (!displayer_it->second) {
                    displayers_.erase(displayer_it);
                    throw std::runtime_error(
                        "constructor returned an invalid displayer");
                }
                if (acknowledgements) {
                    acknowledgements->registration_succeeded();
                }
            } catch (const std::exception& error) {
                removed_surfaces_.insert(surface_id);
                surfaces_.erase(surface_id);
                surface_states_.erase(surface_id);
                (void)surface_frame_gate_.retire(surface_id);
                if (acknowledgements) {
                    acknowledgements->registration_failed(
                        std::string("HardwareDisplayer construction failed: ") +
                        error.what());
                }
                CFW_LOG_ERROR(
                    "DisplaySystem: HardwareDisplayer construction failed "
                    "(surface={}): {}",
                    surface,
                    error.what());
            } catch (...) {
                removed_surfaces_.insert(surface_id);
                surfaces_.erase(surface_id);
                surface_states_.erase(surface_id);
                (void)surface_frame_gate_.retire(surface_id);
                if (acknowledgements) {
                    acknowledgements->registration_failed(
                        "HardwareDisplayer construction failed: unknown exception");
                }
                CFW_LOG_ERROR(
                    "DisplaySystem: HardwareDisplayer construction failed with "
                    "unknown exception (surface={})",
                    surface);
            }
        }
        pending_surfaces_.clear();
        states_snapshot = surface_states_;
        surfaces_snapshot = surfaces_;
        acknowledgements_snapshot = surface_acknowledgements_;
        for (const auto& [surface_id, state] : states_snapshot) {
            (void)state;
            frame_gate_snapshot.emplace(
                surface_id, surface_frame_gate_.capture(surface_id));
        }
    }

    // Destroy displayers OUTSIDE the lock (displayers_ is touched only on this thread).
    // ~HardwareDisplayer → cleanUpDisplayManager() runs vkDeviceWaitIdle before destroying
    // the swapchain + VkSurfaceKHR, so no present is in flight and the surface is gone
    // before the main thread destroys the OS window. Fulfilling the promise unblocks the
    // main thread (the publisher of DisplaySurfaceRemovedEvent) to proceed with that.
    for (auto& r : removals) {
        const auto surface_id = reinterpret_cast<uint64_t>(r.surface);
        r.retirement.wait();
        displayers_.erase(surface_id);
        composite_resources_.erase(surface_id);
        surface_frame_gate_.forget(surface_id);
        if (r.acknowledgements) {
            r.acknowledgements->removal_succeeded();
        }
    }

    if (device_lost_.load(std::memory_order_acquire)) {
        return;
    }

    for (auto& [surface_id, displayer] : displayers_) {
        auto it = states_snapshot.find(surface_id);
        if (it == states_snapshot.end()) {
            continue;
        }

        const auto gate_it = frame_gate_snapshot.find(surface_id);
        if (gate_it == frame_gate_snapshot.end()) {
            continue;
        }
        auto frame_lease = surface_frame_gate_.try_acquire(gate_it->second);
        if (!frame_lease) {
            continue;
        }

        std::shared_ptr<Detail::SurfaceLifecycleAcks> acknowledgements;
        if (const auto acknowledgements_it =
                acknowledgements_snapshot.find(surface_id);
            acknowledgements_it != acknowledgements_snapshot.end()) {
            acknowledgements = acknowledgements_it->second;
        }

        auto& state = it->second;
        const bool has_optics = state.optics.image_handle != 0;
        const bool has_ui = state.ui.image_handle != 0;

        if (!has_optics && !has_ui) {
            continue;
        }

        // Acquire write handles for available layers
        SharedDataHub::ImageStorage::WriteHandle optics_frame;
        SharedDataHub::ImageStorage::WriteHandle ui_frame;
        if (has_optics) {
            optics_frame = SharedDataHub::instance().image_storage().acquire_write(state.optics.image_handle);
        }
        if (has_ui) {
            ui_frame = SharedDataHub::instance().image_storage().acquire_write(state.ui.image_handle);
        }

        // Resolve images: use producer image if available, transparent fallback otherwise.
        Horizon::HardwareImage* optics_img_ptr = nullptr;
        const Horizon::SubmitReceipt* optics_receipt_ptr = nullptr;
        if (has_optics && optics_frame) {
            optics_img_ptr = &optics_frame->image;
            optics_receipt_ptr = &optics_frame->submit_receipt;
        }

        Horizon::HardwareImage* ui_img_ptr = nullptr;
        const Horizon::SubmitReceipt* ui_receipt_ptr = nullptr;
        if (has_ui && ui_frame) {
            ui_img_ptr = &ui_frame->image;
            ui_receipt_ptr = &ui_frame->submit_receipt;
        }

        void* surface = nullptr;
        if (auto surface_it = surfaces_snapshot.find(surface_id);
            surface_it != surfaces_snapshot.end()) {
            surface = surface_it->second;
        }

        bool use_optics_layer = optics_img_ptr && *optics_img_ptr;
        bool use_ui_layer = ui_img_ptr && *ui_img_ptr;
        if (use_optics_layer && optics_receipt_ptr != nullptr && optics_receipt_ptr->empty()) {
            if (state.optics.frame_index <= 1 || state.optics.frame_index % 120 == 0) {
                CFW_LOG_WARNING(
                    "DisplaySystem: skipping optics layer with empty submit receipt "
                    "(surface={}, image_handle={}, frame={}, extent={}x{})",
                    surface,
                    state.optics.image_handle,
                    state.optics.frame_index,
                    state.optics.width,
                    state.optics.height);
            }
            use_optics_layer = false;
            optics_receipt_ptr = nullptr;
        }
        if (use_ui_layer && ui_receipt_ptr != nullptr && ui_receipt_ptr->empty()) {
            if (state.ui.frame_index <= 1 || state.ui.frame_index % 120 == 0) {
                CFW_LOG_WARNING(
                    "DisplaySystem: skipping UI layer with empty submit receipt "
                    "(surface={}, image_handle={}, frame={}, extent={}x{})",
                    surface,
                    state.ui.image_handle,
                    state.ui.frame_index,
                    state.ui.width,
                    state.ui.height);
            }
            use_ui_layer = false;
            ui_receipt_ptr = nullptr;
        }

        Horizon::HardwareImage& bg_image = use_optics_layer ? *optics_img_ptr : transparent_storage_;
        Horizon::HardwareImage& fg_image = use_ui_layer ? *ui_img_ptr : transparent_storage_;

        if (!bg_image || !fg_image) {
            continue;
        }

        auto& composite_resources = composite_resources_[surface_id];
        bool composed = false;
        try {
            composed = compose_and_present(
                displayer,
                surface,
                state,
                composite_resources,
                bg_image,
                use_optics_layer ? optics_receipt_ptr : nullptr,
                fg_image,
                use_ui_layer ? ui_receipt_ptr : nullptr);
        } catch (const std::exception& error) {
            if (is_vulkan_device_lost_message(error.what())) {
                const std::string failure_message =
                    std::string("Display first present failed: Vulkan device lost: ") +
                    error.what();
                if (!device_lost_.exchange(true, std::memory_order_acq_rel)) {
                    std::vector<std::shared_ptr<
                        Detail::SurfaceLifecycleAcks>>
                        live_acknowledgements;
                    {
                        std::lock_guard lock(frame_mutex_);
                        live_acknowledgements.reserve(
                            surface_acknowledgements_.size());
                        for (const auto& [id, pending_acknowledgements] :
                             surface_acknowledgements_) {
                            (void)id;
                            if (pending_acknowledgements) {
                                live_acknowledgements.push_back(
                                    pending_acknowledgements);
                            }
                        }
                    }
                    for (const auto& pending_acknowledgements :
                         live_acknowledgements) {
                        if (pending_acknowledgements) {
                            pending_acknowledgements->fail_forward(
                                failure_message);
                        }
                    }
                    CFW_LOG_CRITICAL(
                        "DisplaySystem: Vulkan device lost during compose/present; "
                        "disabling further display submits and requesting engine shutdown "
                        "(surface={}, optics_handle={}, optics_frame={}, optics_receipt_empty={}, "
                        "ui_handle={}, ui_frame={}, ui_receipt_empty={}, output={}x{}, error={})",
                        surface,
                        state.optics.image_handle,
                        state.optics.frame_index,
                        optics_receipt_ptr == nullptr || optics_receipt_ptr->empty(),
                        state.ui.image_handle,
                        state.ui.frame_index,
                        ui_receipt_ptr == nullptr || ui_receipt_ptr->empty(),
                        composite_resources.width,
                        composite_resources.height,
                        error.what());
                    if (auto* stream = context()->event_stream()) {
                        stream->get_stream<Events::EngineShutdownEvent>()->publish(Events::EngineShutdownEvent{});
                    }
                }
                continue;
            }
            if (acknowledgements) {
                acknowledgements->present_failed(
                    std::string("Display compose/present failed: ") +
                    error.what());
            }
            CFW_LOG_ERROR(
                "DisplaySystem: compose/present failed "
                "(surface={}, optics_handle={}, optics_frame={}, optics_receipt_empty={}, "
                "ui_handle={}, ui_frame={}, ui_receipt_empty={}, output={}x{}): {}",
                surface,
                state.optics.image_handle,
                state.optics.frame_index,
                optics_receipt_ptr == nullptr || optics_receipt_ptr->empty(),
                state.ui.image_handle,
                state.ui.frame_index,
                ui_receipt_ptr == nullptr || ui_receipt_ptr->empty(),
                composite_resources.width,
                composite_resources.height,
                error.what());
            continue;
        } catch (...) {
            if (acknowledgements) {
                acknowledgements->present_failed(
                    "Display compose/present failed: unknown exception");
            }
            CFW_LOG_ERROR(
                "DisplaySystem: compose/present failed with unknown exception "
                "(surface={}, optics_handle={}, ui_handle={})",
                surface,
                state.optics.image_handle,
                state.ui.image_handle);
            continue;
        }
        if (acknowledgements) {
            acknowledgements->present_completed(
                composed && use_ui_layer, state.ui.first_present_boundary);
        }
        if (!composed) {
            continue;
        }

        // Write back the consumed signal so producers know when to safely reuse their image.
        const Horizon::SubmitReceipt consumed_receipt = composite_resources.executor.last_receipt();
        if (use_optics_layer && optics_frame) {
            optics_frame->consumed_receipt = consumed_receipt;
        }
        if (use_ui_layer && ui_frame) {
            ui_frame->consumed_receipt = consumed_receipt;
        }
    }
}

bool DisplaySystem::ensure_composite_resources(CompositeResources& resources,
                                               uint32_t width,
                                               uint32_t height) {
    if (!composite_pipeline_ready_) {
        if (!composite_pipeline_) {
            composite_pipeline_.emplace(composite_comp_glsl, ktm::uvec3(8, 8, 1));
        }
        composite_pipeline_ready_ = composite_pipeline_->getComputePipelineID() != 0;
        if (!composite_pipeline_ready_) {
            CFW_LOG_ERROR("DisplaySystem: Failed to create typed composite pipeline");
            return false;
        }
    }

    if (resources.width != width || resources.height != height || !resources.output) {
        resources.executor.wait_idle(resources.executor.last_receipt());
        resources.output = Horizon::HardwareImage(Horizon::HardwareImageDesc::texture_2d(
            width,
            height,
            Horizon::Format::RGBA16_FLOAT,
            Horizon::ImageUsageFlags::Storage | Horizon::ImageUsageFlags::ColorAttachment |
                Horizon::ImageUsageFlags::Sampled | Horizon::ImageUsageFlags::TransferSrc |
                Horizon::ImageUsageFlags::TransferDst,
            "display.composite_output"));
        if (!resources.output) {
            CFW_LOG_ERROR("DisplaySystem: Failed to create composite output ({}x{})", width, height);
            return false;
        }
        resources.width = width;
        resources.height = height;
    }

    return true;
}

bool DisplaySystem::compose_and_present(Horizon::HardwareDisplayer& displayer,
                                        void* surface,
                                        SurfaceState& state,
                                        CompositeResources& resources,
                                        Horizon::HardwareImage& optics_image,
                                        const Horizon::SubmitReceipt* optics_receipt,
                                        Horizon::HardwareImage& ui_image,
                                        const Horizon::SubmitReceipt* ui_receipt) {
    const PixelExtent optics_extent = hardware_image_extent(optics_image);
    const PixelExtent ui_extent = hardware_image_extent(ui_image);

    const PixelExtent state_optics_extent{state.optics.width, state.optics.height};
    const PixelExtent state_ui_extent{state.ui.width, state.ui.height};
    PixelExtent output_extent = surface_client_extent(surface);
    if (!output_extent) {
        output_extent = max_extent(optics_extent, ui_extent);
    }
    if (!output_extent) {
        output_extent = max_extent(state_optics_extent, state_ui_extent);
    }
    if (!output_extent) {
        return false;
    }

    const PixelExtent bg_extent = optics_extent ? optics_extent : state_optics_extent;
    const PixelExtent fg_extent = ui_extent ? ui_extent : state_ui_extent;
    const uint32_t output_width = output_extent.width;
    const uint32_t output_height = output_extent.height;

    if (!ensure_composite_resources(resources, output_width, output_height)) {
        return false;
    }

    auto& composite_pipeline = *composite_pipeline_;
    const uint32_t bg_descriptor = optics_image.storeStorageDescriptor();
    const uint32_t fg_descriptor = ui_image.storeStorageDescriptor();
    const uint32_t output_descriptor = resources.output.storeStorageDescriptor();
    composite_pipeline.pushConsts.bgImage = bg_descriptor;
    composite_pipeline.pushConsts.fgImage = fg_descriptor;
    composite_pipeline.pushConsts.outputImage = output_descriptor;
    composite_pipeline.pushConsts.outputWidth = output_width;
    composite_pipeline.pushConsts.outputHeight = output_height;
    composite_pipeline.pushConsts.bgWidth = std::max(bg_extent.width, 1u);
    composite_pipeline.pushConsts.bgHeight = std::max(bg_extent.height, 1u);
    composite_pipeline.pushConsts.fgWidth = std::max(fg_extent.width, 1u);
    composite_pipeline.pushConsts.fgHeight = std::max(fg_extent.height, 1u);
    composite_pipeline.pushConsts.bgViewportX = state.optics.viewport_x;
    composite_pipeline.pushConsts.bgViewportY = state.optics.viewport_y;
    composite_pipeline.pushConsts.bgViewportWidth =
        state.optics.viewport_width != 0 ? state.optics.viewport_width : output_width;
    composite_pipeline.pushConsts.bgViewportHeight =
        state.optics.viewport_height != 0 ? state.optics.viewport_height : output_height;
    composite_pipeline.pushConsts.fgOpaque =
        (state.ui.image_handle != 0 && state.optics.image_handle == 0) ? 1u : 0u;
    composite_pipeline.bind_storage_image(0, optics_image);
    composite_pipeline.bind_storage_image(1, ui_image);
    composite_pipeline.bind_storage_image(2, resources.output);

    const uint32_t dispatch_x = (output_width + 7u) / 8u;
    const uint32_t dispatch_y = (output_height + 7u) / 8u;
    {
        std::ostringstream label;
        label << "Display/composite"
              << " surface=" << surface
              << " bg_desc=" << bg_descriptor
              << " fg_desc=" << fg_descriptor
              << " output_desc=" << output_descriptor
              << " bg_image=" << optics_image.get_image_id()
              << " fg_image=" << ui_image.get_image_id()
              << " output_image=" << resources.output.get_image_id()
              << " bg_extent=" << bg_extent.width << "x" << bg_extent.height
              << " fg_extent=" << fg_extent.width << "x" << fg_extent.height
              << " output_extent=" << output_width << "x" << output_height
              << " optics_frame=" << state.optics.frame_index
              << " optics_receipt_empty="
              << (optics_receipt == nullptr || optics_receipt->empty())
              << " ui_frame=" << state.ui.frame_index
              << " ui_receipt_empty="
              << (ui_receipt == nullptr || ui_receipt->empty());
        composite_pipeline.set_debug_label(label.str());
    }

    // GPU sync: wait for each producer's rendering to finish before reading their images
    if (optics_receipt != nullptr && !optics_receipt->empty()) {
        resources.executor.wait(*optics_receipt);
    }
    if (ui_receipt != nullptr && !ui_receipt->empty()) {
        resources.executor.wait(*ui_receipt);
    }

    (void)(resources.executor.stream()
           << composite_pipeline(dispatch_x, dispatch_y, 1)
           << Horizon::present(displayer, resources.output)
           << Horizon::commit());
    return true;
}

void DisplaySystem::shutdown() {
    shutting_down_.store(true, std::memory_order_release);

    if (auto* system_context = context(); system_context != nullptr) {
        auto* event_bus = system_context->event_bus();
        if (event_bus != nullptr) {
            if (surface_changed_sub_id_ != 0) {
                event_bus->unsubscribe(surface_changed_sub_id_);
            }
            if (surface_removed_sub_id_ != 0) {
                event_bus->unsubscribe(surface_removed_sub_id_);
            }
            if (optics_frame_sub_id_ != 0) {
                event_bus->unsubscribe(optics_frame_sub_id_);
            }
            if (ui_frame_sub_id_ != 0) {
                event_bus->unsubscribe(ui_frame_sub_id_);
            }
        }
    }
    surface_changed_sub_id_ = 0;
    surface_removed_sub_id_ = 0;
    optics_frame_sub_id_ = 0;
    ui_frame_sub_id_ = 0;

    std::unordered_set<std::uint64_t> surface_ids;
    std::vector<std::shared_ptr<Detail::SurfaceLifecycleAcks>> acknowledgements;
    {
        std::lock_guard<std::mutex> lock(frame_mutex_);
        acknowledgements.reserve(surface_acknowledgements_.size() +
                                 pending_removals_.size());
        for (const auto& [surface_id, pending_acknowledgements] :
             surface_acknowledgements_) {
            surface_ids.insert(surface_id);
            if (pending_acknowledgements) {
                acknowledgements.push_back(pending_acknowledgements);
            }
        }
        for (const auto& removal : pending_removals_) {
            surface_ids.insert(
                reinterpret_cast<std::uint64_t>(removal.surface));
            if (removal.acknowledgements) {
                acknowledgements.push_back(removal.acknowledgements);
            }
        }
        for (const auto& [surface_id, surface] : surfaces_) {
            (void)surface;
            surface_ids.insert(surface_id);
        }

        pending_surfaces_.clear();
        pending_removals_.clear();
        surface_states_.clear();
        surfaces_.clear();
        removed_surfaces_.clear();
        surface_acknowledgements_.clear();
    }

    for (const auto& [surface_id, displayer] : displayers_) {
        (void)displayer;
        surface_ids.insert(surface_id);
    }
    for (const auto& [surface_id, resources] : composite_resources_) {
        (void)resources;
        surface_ids.insert(surface_id);
    }

    std::vector<std::pair<std::uint64_t,
                          Detail::SurfaceFrameGate::Retirement>>
        retirements;
    retirements.reserve(surface_ids.size());
    for (const auto surface_id : surface_ids) {
        retirements.emplace_back(surface_id,
                                 surface_frame_gate_.retire(surface_id));
    }

    for (const auto& pending_acknowledgements : acknowledgements) {
        pending_acknowledgements->cancel_forward(
            "Display shutdown before surface lifecycle completed");
    }
    for (const auto& [surface_id, retirement] : retirements) {
        (void)surface_id;
        retirement.wait();
    }

    composite_pipeline_ready_ = false;
    device_lost_.store(false, std::memory_order_release);
    displayers_.clear();
    composite_resources_.clear();
    composite_pipeline_.reset();
    transparent_storage_ = Horizon::HardwareImage();

    for (const auto& [surface_id, retirement] : retirements) {
        (void)retirement;
        surface_frame_gate_.forget(surface_id);
    }

    // EventBus publish copies handlers before calling them, so unsubscribe does
    // not wait for a callback already in flight. Collect removals that entered
    // after the first snapshot, then close the late-callback window under the
    // same mutex those handlers use.
    std::vector<PendingRemoval> late_removals;
    {
        std::lock_guard<std::mutex> lock(frame_mutex_);
        late_removals.swap(pending_removals_);
        for (const auto& [surface_id, pending_acknowledgements] :
             surface_acknowledgements_) {
            (void)surface_id;
            if (pending_acknowledgements) {
                acknowledgements.push_back(pending_acknowledgements);
            }
        }
        pending_surfaces_.clear();
        surface_states_.clear();
        surfaces_.clear();
        removed_surfaces_.clear();
        surface_acknowledgements_.clear();
        shutdown_resources_destroyed_.store(true, std::memory_order_release);
    }

    for (auto& removal : late_removals) {
        const auto surface_id =
            reinterpret_cast<std::uint64_t>(removal.surface);
        removal.retirement.wait();
        surface_frame_gate_.forget(surface_id);
        if (removal.acknowledgements) {
            acknowledgements.push_back(removal.acknowledgements);
        }
    }

    // Only now are both per-surface displayer/swapchain and composite resources
    // gone, so new removal tickets and every legacy promise may be completed.
    for (const auto& pending_acknowledgements : acknowledgements) {
        pending_acknowledgements->removal_succeeded();
    }
}

}  // namespace Corona::Systems
