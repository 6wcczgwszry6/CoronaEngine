#pragma once

// Phase 5 of the ImGui-removal plan: an ImGui-free input state tracker + hit-tester.
//
// Today input routing reads ImGui IO (io.MousePos, ImGui::IsMouseDown, IsItemHovered,
// GetMouseDragDelta) inside sdl_utils.cpp / browser_ui.cpp. This router reconstructs the
// same state directly from SDL events plus SDL_GetModState(), hit-tests the mouse against
// the fixed panel rectangles produced by compute_panel_layout(), and translates global
// coordinates to panel-local ones for CEF forwarding via the MouseUtils *_ex overloads.
//
// In Phase 5 it is purely additive — nothing calls it yet; it can be exercised in a
// parallel logging mode. The frame loop switches to it in Phase 6. Detach intent (drag-bar
// hit + threshold) is recorded here but only consumed in Phase 7.

#include <SDL3/SDL.h>

#include <cstdint>
#include <vector>

#include "panel_layout.h"

namespace Corona::Systems::UI {

// Mouse button identifiers, independent of SDL/ImGui button numbering.
enum class MouseButton { Left, Right, Middle };

// Snapshot of pointer + modifier state, rebuilt from SDL events (no ImGui IO).
struct InputState {
    float mouse_x = 0.0f;   // global, in render-target pixels
    float mouse_y = 0.0f;
    bool left_down = false;
    bool right_down = false;
    bool middle_down = false;
    bool shift = false;
    bool ctrl = false;
    bool alt = false;
    bool gui = false;   // Win/Cmd
    float wheel = 0.0f;  // accumulated wheel delta since last consume()
};

// A panel rect tagged with the data the router needs to forward input to it.
struct HitTarget {
    int tab_id = -1;
    LayoutRect rect;
    bool is_main = false;
    // Drag-bar regions in panel-local coordinates. Empty ⇒ default top-30px handle
    // (mirrors browser_ui.cpp). Used only for detach intent (Phase 7).
    std::vector<LayoutRect> drag_regions;
};

// Result of hit-testing the current mouse position against the target list.
struct HitResult {
    bool hit = false;
    int tab_id = -1;
    bool is_main = false;
    bool in_drag_region = false;  // mouse is over a drag bar of the hit panel
    float local_x = 0.0f;         // mouse relative to the hit panel's top-left
    float local_y = 0.0f;
};

class SdlInputRouter {
   public:
    SdlInputRouter() = default;

    // Feed one SDL event. Updates the tracked InputState. Mouse-button transitions update
    // click-count (double/triple click) using the same 500ms / 5px thresholds as
    // MouseUtils::MouseStateManager. Returns true if the event was a recognized input
    // event (mouse/wheel); keyboard/text events are left to the existing BrowserInputHandler.
    bool process_event(const SDL_Event& event);

    // Pull modifier state from the OS at frame start (SDL_GetModState), matching how ImGui
    // refreshes io.KeyShift/Ctrl/Alt each NewFrame. Call once per frame before dispatching.
    void refresh_modifiers();

    [[nodiscard]] const InputState& state() const { return state_; }

    // Click count for the most recent left-button press (1, 2, or 3).
    [[nodiscard]] int click_count() const { return click_count_; }

    // Consume the accumulated wheel delta (returns it and resets to 0).
    [[nodiscard]] float consume_wheel();

    // Hit-test the current mouse position against targets, topmost-first. The caller passes
    // targets in draw order (last = topmost); the last containing rect wins.
    [[nodiscard]] HitResult hit_test(const std::vector<HitTarget>& targets) const;

   private:
    InputState state_;

    // Double/triple-click tracking (mirror of MouseStateManager).
    Uint32 last_click_time_ = 0;
    float last_click_x_ = 0.0f;
    float last_click_y_ = 0.0f;
    int click_count_ = 0;

    static constexpr Uint32 kDoubleClickTime = 500;
    static constexpr float kDoubleClickDist = 5.0f;
};

}  // namespace Corona::Systems::UI
