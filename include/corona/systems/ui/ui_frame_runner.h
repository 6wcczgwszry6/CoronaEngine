#pragma once

// Phase 6 of the ImGui-removal plan: the ImGui-free main-window frame loop. It replaces
// UI::UiFrameRunner (imgui/imgui_ui.cpp), which drove the frame via ImGui NewFrame/Render
// plus a transparent dockspace. This runner instead:
//   1. pumps SDL events (quit/resize/focus/text + windowID routing), feeding the input
//      router (mouse/wheel) and BrowserInputHandler (keyboard/text/IME);
//   2. computes fixed-rect panel placement via compute_panel_layout();
//   3. for camera_view panels, binds the surface + layout to CameraViewportManager using the
//      computed rect and the main window's native HWND;
//   4. forwards mouse input to the hit panel's CEF browser via the MouseUtils *_ex overloads;
//   5. builds a QuadDraw list (one quad per visible panel texture) and renders it through
//      VulkanBackend::render_quads(), then present_frame().
//
// Phase 6 is main-window only: panels are laid out inside the single main window; there is
// no detach/secondary-window handling (that is Phase 7). Multi-viewport is gone.

#include <SDL3/SDL.h>

#include <corona/systems/ui/panel_layout.h>
#include <corona/systems/ui/sdl_input_router.h>

#include "cef/browser_ui.h"
#include "sdl/sdl_utils.h"

namespace Corona::Systems {
class VulkanBackend;
}

namespace Corona::Systems::UI {

// Lifecycle: create the SDL window + Vulkan backend (replaces initialize_sdl_imgui), and
// tear them down (replaces shutdown_sdl_imgui). No ImGui context is created.
bool initialize_sdl_ui(SDL_Window*& window, std::unique_ptr<VulkanBackend>& vulkan_backend);
void shutdown_sdl_ui(SDL_Window*& window, std::unique_ptr<VulkanBackend>& vulkan_backend);

// Per-frame context, mirroring the old UiFrameContext minus the ImGuiIO pointer.
struct UiFrameContext {
    SDL_Window* window = nullptr;
    VulkanBackend* vulkan_backend = nullptr;
    int* active_tab_id = nullptr;
    bool* running = nullptr;
    bool* window_size_changed = nullptr;
};

class UiFrameRunner {
   public:
    UiFrameRunner() = default;

    void run_frame(UiFrameContext& context);

   private:
    // Forward queued keyboard/text/IME events to the active tab's browser (unchanged logic).
    void dispatch_keyboard_to_active_tab(int active_tab_id);

    // Build hit targets from the computed layout, forward mouse to the hit panel's browser.
    void route_mouse_to_panels(const std::vector<PanelPlacement>& placements,
                               int& active_tab_id);

    int url_input_active_tab_ = -1;

    SdlInputRouter input_router_{};
    BrowserInputHandler input_handler_{};
    SDLEventHandler event_handler_{};
};

}  // namespace Corona::Systems::UI
