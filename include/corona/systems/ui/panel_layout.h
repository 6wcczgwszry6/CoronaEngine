#pragma once

// Phase 3 of the ImGui-removal plan: a pure fixed-zone layout function that replaces
// BrowserRenderer::setup_window_transform. Given a window work area and the panels to
// place, it returns one rectangle per panel using the exact same math as the current
// ImGui path (margins, width ratios, per-docking_pos placement). One panel per zone —
// no tab grouping.
//
// This file is purely additive in Phase 3 — nothing references it yet. It is wired into
// the frame loop in Phase 6. It is intentionally SDL-free so it can be unit-tested; the
// caller builds WorkArea from SDL client-pixel size (origin 0,0 for the window's own UI
// render target).

#include <string>
#include <vector>

namespace Corona::Systems::UI {

// Window work area in render-target pixels (origin is the window client top-left).
struct WorkArea {
    float x = 0.0f;
    float y = 0.0f;
    float width = 0.0f;
    float height = 0.0f;
};

// Rect in render-target pixels.
struct LayoutRect {
    float x = 0.0f;
    float y = 0.0f;
    float w = 0.0f;
    float h = 0.0f;
};

// One panel to place. Mirrors the BrowserTab fields read by setup_window_transform.
struct PanelLayoutInput {
    int tab_id = -1;
    std::string docking_pos;  // "main","left_top","left_bottom","right_top","right_bottom","bottom_left","bottom_right","center"
    int dock_width = 0;
    int dock_height = 0;
    bool camera_view = false;
    // floating: an in-main-window draggable rectangle positioned by initial_x/y (like a
    // camera viewport) rather than a fixed docking_pos anchor. Set for popped-out panels so
    // they can be dragged around the main window. camera_view implies floating placement too.
    bool floating = false;
    int initial_x = 0;  // explicit position for camera_view / floating panels
    int initial_y = 0;
};

// Computed placement for one panel.
struct PanelPlacement {
    int tab_id = -1;
    LayoutRect rect;
    bool is_main = false;
};

// Build a WorkArea covering the whole client area of a window of the given pixel size.
[[nodiscard]] WorkArea make_client_work_area(int client_width_px, int client_height_px);

// Compute a fixed-zone rectangle for each input panel (independent per panel; one zone
// per panel). docking_pos == "main" fills the entire work area. camera_view panels keep
// their explicit initial rect.
[[nodiscard]] std::vector<PanelPlacement> compute_panel_layout(
    const WorkArea& work, const std::vector<PanelLayoutInput>& panels);

}  // namespace Corona::Systems::UI
