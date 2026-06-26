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
#include <unordered_map>
#include <vector>

#include "panel_layout.h"

namespace Corona::Systems::UI {

// Mouse button identifiers, independent of SDL/ImGui button numbering.
enum class MouseButton { Left, Right, Middle };

// A button press/release transition recorded during event processing. The frame loop
// drains these each frame and forwards them to the hit panel's CEF browser. `click_count`
// is meaningful for left-button presses (double/triple click); 1 otherwise.
struct ButtonEvent {
    MouseButton button = MouseButton::Left;
    bool pressed = false;   // true = down, false = up
    float mouse_x = 0.0f;   // global position at the time of the transition
    float mouse_y = 0.0f;
    int click_count = 1;
};

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

    // Feed one SDL event. SDL mouse coordinates are WINDOW-LOCAL and every mouse/wheel event
    // carries a windowID, so state is tracked per window: the event updates the bucket for its
    // own window. Mouse-button transitions update that window's click-count (double/triple
    // click) using the same 500ms / 5px thresholds as the old MouseStateManager. Returns true
    // if the event was a recognized mouse/wheel event; keyboard/text events are left to
    // BrowserInputHandler.
    bool process_event(const SDL_Event& event);

    // Pull modifier state from the OS at frame start (SDL_GetModState). Modifiers are global
    // in SDL (keyboard state is not per-window), so they are stored once and merged into every
    // window's reported state. Call once per frame before dispatching.
    void refresh_modifiers();

    // Per-window pointer/modifier snapshot. Returns a zeroed state for an unknown window.
    [[nodiscard]] InputState state(SDL_WindowID window_id) const;

    // Consume a window's accumulated wheel delta (returns it and resets to 0).
    [[nodiscard]] float consume_wheel(SDL_WindowID window_id);

    // Hit-test a window's current mouse position against targets, topmost-first (the last
    // containing rect in draw order wins).
    [[nodiscard]] HitResult hit_test(SDL_WindowID window_id,
                                     const std::vector<HitTarget>& targets) const;

    // Drain a window's button press/release transitions recorded since the last call.
    [[nodiscard]] std::vector<ButtonEvent> drain_button_events(SDL_WindowID window_id);

   private:
    // Per-window pointer + click state. Modifiers live in the shared block below and are
    // merged in on query, since SDL keyboard modifier state is global.
    struct PerWindowInput {
        float mouse_x = 0.0f;
        float mouse_y = 0.0f;
        bool left_down = false;
        bool right_down = false;
        bool middle_down = false;
        float wheel = 0.0f;
        std::vector<ButtonEvent> button_events;

        Uint32 last_click_time = 0;
        float last_click_x = 0.0f;
        float last_click_y = 0.0f;
        int click_count = 0;
    };

    PerWindowInput& bucket(SDL_WindowID window_id);

    std::unordered_map<SDL_WindowID, PerWindowInput> windows_;

    // Global modifier state (SDL_GetModState), merged into every window's reported state.
    bool shift_ = false;
    bool ctrl_ = false;
    bool alt_ = false;
    bool gui_ = false;

    static constexpr Uint32 kDoubleClickTime = 500;
    static constexpr float kDoubleClickDist = 5.0f;
};

}  // namespace Corona::Systems::UI
