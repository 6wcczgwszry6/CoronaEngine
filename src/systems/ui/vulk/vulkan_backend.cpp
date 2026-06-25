#include <corona/events/display_system_events.h>
#include <corona/kernel/core/i_logger.h>
#include <corona/kernel/core/kernel_context.h>
#include <corona/kernel/event/i_event_bus.h>
#include <corona/shared_data_hub.h>
#include <corona/systems/script/corona_engine_api.h>
#include <corona/systems/ui/vulkan_backend.h>

#include <algorithm>
#include <cstdint>
#include <span>
#include <vector>

namespace {

[[nodiscard]] Corona::Horizon::RasterizerPipelineDesc make_ui_pipeline_desc() {
    Corona::Horizon::RasterizerPipelineDesc desc;
    desc.debug_name = "corona.ui_quad";
    desc.rasterizer.cull_mode = Corona::Horizon::CullMode::None;
    desc.depth_stencil.depth_test_enabled = false;
    desc.depth_stencil.depth_write_enabled = false;
    desc.depth_stencil.stencil_test_enabled = false;
    return desc;
}

constexpr auto kUiRenderTargetUsage =
    Corona::Horizon::ImageUsageFlags::Sampled | Corona::Horizon::ImageUsageFlags::Storage;

struct PixelExtent {
    uint32_t width = 0;
    uint32_t height = 0;

    [[nodiscard]] explicit operator bool() const noexcept {
        return width != 0 && height != 0;
    }
};

[[nodiscard]] PixelExtent window_pixel_extent(SDL_Window* window) {
    if (window == nullptr) {
        return {};
    }

    int width = 0;
    int height = 0;
    if (SDL_GetWindowSizeInPixels(window, &width, &height) && width > 0 && height > 0) {
        return {static_cast<uint32_t>(width), static_cast<uint32_t>(height)};
    }

    width = 0;
    height = 0;
    if (SDL_GetWindowSize(window, &width, &height) && width > 0 && height > 0) {
        return {static_cast<uint32_t>(width), static_cast<uint32_t>(height)};
    }

    return {};
}

std::uintptr_t select_main_camera_handle(const Corona::SceneDevice& scene) {
    if (scene.active_camera_handle != 0 &&
        std::find(scene.camera_handles.begin(),
                  scene.camera_handles.end(),
                  scene.active_camera_handle) != scene.camera_handles.end()) {
        return scene.active_camera_handle;
    }
    return scene.camera_handles.empty() ? 0 : scene.camera_handles.front();
}

void sync_default_surface_camera_size(void* surface, uint32_t width, uint32_t height) {
    if (surface == nullptr || width == 0 || height == 0) {
        return;
    }

    auto& hub = Corona::SharedDataHub::instance();
    for (const auto& scene : hub.scene_storage()) {
        if (!scene.enabled) {
            continue;
        }
        const auto camera_handle = select_main_camera_handle(scene);
        if (camera_handle == 0) {
            continue;
        }
        if (auto camera = hub.camera_storage().try_acquire_write(camera_handle)) {
            if (!camera->follows_default_surface) {
                continue;
            }
            if (camera->surface != nullptr && camera->surface != surface) {
                continue;
            }
            camera->surface = surface;
            camera->width = width;
            camera->height = height;
            camera->aspect = static_cast<float>(width) / static_cast<float>(height);
        }
    }
}

}  // namespace

namespace Corona::Systems {

VulkanBackend::VulkanBackend(SDL_Window* window)
    : window_(window) {
}

bool VulkanBackend::initialize() {
    if (initialized_) {
        return true;
    }

    if (window_ == nullptr) {
        CFW_LOG_ERROR("VulkanBackend: initialize failed, window is null");
        return false;
    }

    void* native_handle = nullptr;
#if defined(_WIN32)
    native_handle = SDL_GetPointerProperty(
        SDL_GetWindowProperties(window_),
        SDL_PROP_WINDOW_WIN32_HWND_POINTER,
        nullptr);
#elif defined(__APPLE__)
    native_handle = SDL_GetPointerProperty(
        SDL_GetWindowProperties(window_),
        SDL_PROP_WINDOW_COCOA_WINDOW_POINTER,
        nullptr);
#endif

    if (native_handle == nullptr) {
        CFW_LOG_ERROR("VulkanBackend: failed to get native window handle from SDL");
        return false;
    }

    surface_ = native_handle;
    Corona::API::set_default_surface(surface_);
    if (auto* event_bus = Kernel::KernelContext::instance().event_bus()) {
        event_bus->publish<Events::DisplaySurfaceChangedEvent>({surface_});
    }

    const PixelExtent initial_extent = window_pixel_extent(window_);
    if (initial_extent) {
        if (!ensure_render_target(main_resources_, initial_extent.width, initial_extent.height,
                                  kUiRenderTargetUsage)) {
            CFW_LOG_ERROR("VulkanBackend: failed to create initial render target");
            return false;
        }
    } else {
        rebuild_needed_ = true;
    }

    image_handle_ = SharedDataHub::instance().image_storage().allocate();
    if (auto image_device = SharedDataHub::instance().image_storage().acquire_write(image_handle_)) {
        // Keep storage entry alive; per-frame values are updated in present_frame().
    } else {
        CFW_LOG_ERROR("VulkanBackend: failed to acquire shared image storage handle");
        SharedDataHub::instance().image_storage().deallocate(image_handle_);
        image_handle_ = 0;
        return false;
    }

    initialized_ = true;
    CFW_LOG_INFO("VulkanBackend: initialized");
    return true;
}

void VulkanBackend::shutdown() {
    if (!initialized_) {
        return;
    }

    main_resources_.frame_ready = false;
    rebuild_needed_ = false;
    pipeline_ready_ = false;

    main_resources_.render_target = Horizon::HardwareImage();
    pipeline_.reset();

    main_resources_.vertex_buffer = Horizon::HardwareBuffer();
    main_resources_.index_buffer = Horizon::HardwareBuffer();
    main_resources_.vertex_buffer_capacity = 0;
    main_resources_.index_buffer_capacity = 0;

    main_resources_.width = 0;
    main_resources_.height = 0;

    surface_ = nullptr;
    frame_index_ = 0;

    if (image_handle_ != 0) {
        SharedDataHub::instance().image_storage().deallocate(image_handle_);
        image_handle_ = 0;
    }

    initialized_ = false;
    CFW_LOG_INFO("VulkanBackend: shutdown");
}

void VulkanBackend::new_frame() {
    if (!initialized_) {
        return;
    }

    // GPU sync: wait for Display to finish consuming our image
    // before we clear and render new UI content into it.
    if (image_handle_ != 0) {
        if (auto image_device = SharedDataHub::instance().image_storage().acquire_write(image_handle_)) {
            main_resources_.executor.wait(image_device->consumed_receipt);
        }
    }
}

bool VulkanBackend::ensure_pipeline() {
    if (pipeline_ready_) {
        return true;
    }

    pipeline_.emplace(imgui_vert_glsl, imgui_frag_glsl, make_ui_pipeline_desc());
    pipeline_ready_ = pipeline_->getRasterizerPipelineID() != 0;

    if (pipeline_ready_) {
        CFW_LOG_INFO("VulkanBackend: ui quad pipeline created, pipeline_id={}",
                     pipeline_->getRasterizerPipelineID());
    } else {
        CFW_LOG_ERROR("VulkanBackend: ui quad pipeline creation returned invalid pipeline id");
    }

    return pipeline_ready_;
}

void VulkanBackend::render_quads(std::span<const QuadDraw> quads) {
    if (!initialized_) {
        return;
    }

    if (!ensure_pipeline()) {
        return;
    }

    PixelExtent target_extent{main_resources_.width, main_resources_.height};
    if (!target_extent) {
        target_extent = window_pixel_extent(window_);
    }
    if (!target_extent) {
        return;
    }

    if (compositor_.composite(quads,
                              main_resources_,
                              *pipeline_,
                              target_extent.width,
                              target_extent.height,
                              kUiRenderTargetUsage)) {
        main_resources_.frame_ready = true;
    }
}

void VulkanBackend::present_frame() {
    if (!initialized_ || !main_resources_.frame_ready || !main_resources_.render_target ||
        surface_ == nullptr || image_handle_ == 0) {
        return;
    }

    if (auto image_device = SharedDataHub::instance().image_storage().acquire_write(image_handle_)) {
        image_device->image = main_resources_.render_target;
        image_device->submit_receipt = main_resources_.executor.last_receipt();
    } else {
        return;
    }

    sync_default_surface_camera_size(surface_, main_resources_.width, main_resources_.height);

    if (auto* event_bus = Kernel::KernelContext::instance().event_bus()) {
        ++frame_index_;
        event_bus->publish<Events::UIFrameReadyEvent>({surface_,
                                                       image_handle_,
                                                       frame_index_,
                                                       main_resources_.width,
                                                       main_resources_.height});
    }

    main_resources_.frame_ready = false;
}

void VulkanBackend::rebuild(int width, int height) {
    if (!initialized_) {
        return;
    }

    if (width <= 0 || height <= 0) {
        return;
    }

    PixelExtent target_extent = window_pixel_extent(window_);
    if (!target_extent) {
        target_extent = {static_cast<uint32_t>(width), static_cast<uint32_t>(height)};
    }

    const auto target_width = target_extent.width;
    const auto target_height = target_extent.height;
    const bool size_changed = !main_resources_.render_target ||
                              main_resources_.width != target_width ||
                              main_resources_.height != target_height;
    if (size_changed) {
        if (image_handle_ != 0) {
            if (auto image_device = SharedDataHub::instance().image_storage().acquire_write(image_handle_)) {
                main_resources_.executor.wait_idle(image_device->consumed_receipt);
            }
        }
        main_resources_.executor.wait_idle(main_resources_.executor.last_receipt());
    }

    if (!ensure_render_target(main_resources_, target_width, target_height, kUiRenderTargetUsage)) {
        rebuild_needed_ = true;
        return;
    }

    sync_default_surface_camera_size(surface_, target_width, target_height);
    rebuild_needed_ = false;
}

bool VulkanBackend::ensure_render_target(ViewportRenderResources& resources, uint32_t width, uint32_t height,
                                         Horizon::ImageUsageFlags usage) {
    if (width == 0 || height == 0) {
        return false;
    }

    if (resources.render_target && resources.width == width && resources.height == height) {
        return true;
    }

    // SRGBA8_UNORM does not support VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT on many GPUs.
    // When the render target is used as a storage image, use a storage-capable format
    // (RGBA16_FLOAT) to avoid VK_ERROR_FORMAT_NOT_SUPPORTED.
    const Horizon::ImageUsageFlags target_usage = usage | Horizon::ImageUsageFlags::ColorAttachment;
    const Horizon::Format target_format =
        Horizon::has_flag(target_usage, Horizon::ImageUsageFlags::Storage) ? Horizon::Format::RGBA16_FLOAT : Horizon::Format::SRGBA8_UNORM;

    Horizon::HardwareImage new_target(Horizon::HardwareImageDesc::texture_2d(
        width,
        height,
        target_format,
        target_usage,
        "ui.render_target"));
    if (!new_target) {
        CFW_LOG_ERROR("VulkanBackend: create render target failed ({}x{})", width, height);
        return false;
    }
    new_target.set_clear_color(0.0f, 0.0f, 0.0f, 0.0f);
    resources.render_target = std::move(new_target);
    resources.width = width;
    resources.height = height;
    resources.frame_ready = false;

    return true;
}

}  // namespace Corona::Systems
