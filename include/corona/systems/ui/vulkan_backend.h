#pragma once

// quad_compositor.h is the self-contained base: it owns the GLSL pipeline includes,
// ViewportRenderResources, QuadDraw, and QuadCompositor. Include it (not the reverse) to
// avoid a circular dependency.
#include <corona/systems/ui/quad_compositor.h>

#include <SDL3/SDL.h>

#include <cstdint>
#include <memory>
#include <optional>
#include <span>
#include <vector>

namespace Corona::Systems {

// VulkanBackend (post-ImGui): owns the main window's UI render target and publishes it to
// the DisplaySystem via UIFrameReadyEvent. UI geometry is now built as textured quads by
// the UI frame runner (panel textures + chrome) and rendered through QuadCompositor — there
// is no ImGui draw-data path, font atlas, or multi-viewport renderer callback anymore.
class VulkanBackend {
   public:
    explicit VulkanBackend(SDL_Window* window);
    ~VulkanBackend() = default;

    bool initialize();
    void shutdown();

    // GPU back-pressure: wait for DisplaySystem to finish consuming the previous frame's
    // image before we render new UI content into it.
    void new_frame();

    // Render the given quads into the main render target (via QuadCompositor) and mark the
    // frame ready for present_frame(). Replaces the old render_frame(ImDrawData*).
    void render_quads(std::span<const QuadDraw> quads);

    // Publish the main render target to DisplaySystem (UIFrameReadyEvent).
    void present_frame();

    [[nodiscard]] bool is_rebuild_needed() const noexcept { return rebuild_needed_; }
    void request_rebuild() noexcept { rebuild_needed_ = true; }
    void rebuild(int width, int height);

    // Current main render-target pixel size (0 until first target is created).
    [[nodiscard]] uint32_t width() const noexcept { return main_resources_.width; }
    [[nodiscard]] uint32_t height() const noexcept { return main_resources_.height; }

    // Ensure `resources` holds a render target of the given size, (re)creating it on
    // size change. Shared with the quad compositor.
    static bool ensure_render_target(ViewportRenderResources& resources, uint32_t width, uint32_t height,
                                     Horizon::ImageUsageFlags usage = Horizon::ImageUsageFlags::Sampled);

   private:
    // Lazily create the shared quad pipeline (reuses the imgui.vert/frag GLSL).
    bool ensure_pipeline();

    bool initialized_ = false;
    bool rebuild_needed_ = false;
    bool pipeline_ready_ = false;

    SDL_Window* window_ = nullptr;
    void* surface_ = nullptr;

    // Main window rendering resources + the quad compositor that renders into them.
    ViewportRenderResources main_resources_;
    QuadCompositor compositor_;
    std::optional<Horizon::RasterizerPipeline<imgui_vert_glsl_t, imgui_frag_glsl_t>> pipeline_;

    // Main window presentation (SharedDataHub path)
    uint64_t frame_index_ = 0;
    std::uintptr_t image_handle_ = 0;
};

}  // namespace Corona::Systems
