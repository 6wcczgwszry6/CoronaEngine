#include <corona/systems/ui/panel_layout.h>

#include <algorithm>

namespace Corona::Systems::UI {

namespace {

// Verbatim port of BrowserRenderer's clamp_float: returns min when the range is inverted
// (which happens for some docking_pos height clamps on short work areas).
float clamp_float(float value, float min_value, float max_value) {
    if (max_value < min_value) {
        return min_value;
    }
    return std::clamp(value, min_value, max_value);
}

// Port of the non-camera branch of BrowserRenderer::setup_window_transform, operating in
// window-local work-area coordinates instead of ImGui global viewport coordinates.
LayoutRect compute_docked_rect(const WorkArea& work, const PanelLayoutInput& panel) {
    constexpr float panel_margin = 24.0f;
    constexpr float scene_bar_offset = 64.0f;
    constexpr float right_stack_gap = 16.0f;

    const float work_x = work.x;
    const float work_y = work.y;
    const float work_w = work.width;
    const float work_h = work.height;

    auto target_w = static_cast<float>(panel.dock_width);
    auto target_h = static_cast<float>(panel.dock_height);

    const std::string& pos = panel.docking_pos;
    const bool left_panel = pos == "left_bottom";
    const bool right_panel = pos == "right_top" || pos == "right_bottom";

    const float min_w = left_panel ? 300.0f : 320.0f;
    const float width_ratio = left_panel ? 0.22f : (right_panel ? 0.27f : 0.42f);
    const float max_w = std::max(min_w, work_w * width_ratio);
    target_w = clamp_float(target_w, min_w, max_w);

    const float usable_h =
        std::max(260.0f, work_h - scene_bar_offset - panel_margin - right_stack_gap);
    if (pos == "right_top") {
        target_h = clamp_float(target_h, 320.0f, usable_h * 0.54f);
    } else if (pos == "right_bottom") {
        target_h = clamp_float(target_h, 300.0f, usable_h * 0.46f);
    } else if (pos == "left_bottom") {
        target_h = clamp_float(target_h, 300.0f, std::max(300.0f, usable_h * 0.48f));
    } else {
        target_h = clamp_float(target_h, 320.0f, usable_h);
    }

    float final_x = work_x;
    float final_y = work_y;

    if (pos == "left_top") {
        final_x = work_x + panel_margin;
        final_y = work_y + scene_bar_offset;
    } else if (pos == "left_bottom") {
        final_x = work_x + panel_margin;
        final_y = work_y + work_h - target_h - panel_margin;
    } else if (pos == "right_top") {
        final_x = work_x + work_w - target_w - panel_margin;
        final_y = work_y + scene_bar_offset;
    } else if (pos == "right_bottom") {
        final_x = work_x + work_w - target_w - panel_margin;
        final_y = work_y + work_h - target_h - panel_margin;
    } else if (pos == "bottom_left") {
        final_x = work_x + 300.0f;
        final_y = work_y + work_h - target_h;
    } else if (pos == "bottom_right") {
        final_x = work_x + work_w - target_w - 300.0f;
        final_y = work_y + work_h - target_h;
    } else if (pos == "center") {
        final_x = work_x + (work_w - target_w) * 0.5f;
        final_y = work_y + (work_h - target_h) * 0.5f;
    } else {
        final_x = work_x + work_w - target_w - panel_margin;
        final_y = work_y + scene_bar_offset + right_stack_gap;
    }

    return LayoutRect{final_x, final_y, target_w, target_h};
}

}  // namespace

WorkArea make_client_work_area(int client_width_px, int client_height_px) {
    WorkArea work;
    work.x = 0.0f;
    work.y = 0.0f;
    work.width = static_cast<float>(std::max(0, client_width_px));
    work.height = static_cast<float>(std::max(0, client_height_px));
    return work;
}

std::vector<PanelPlacement> compute_panel_layout(const WorkArea& work,
                                                 const std::vector<PanelLayoutInput>& panels) {
    std::vector<PanelPlacement> placements;
    placements.reserve(panels.size());

    for (const PanelLayoutInput& panel : panels) {
        PanelPlacement placement;
        placement.tab_id = panel.tab_id;

        if (panel.docking_pos == "main") {
            placement.is_main = true;
            placement.rect = LayoutRect{work.x, work.y, work.width, work.height};
        } else if (panel.camera_view || panel.floating) {
            // Camera viewports and floating (popped-out) panels use an explicit rect from
            // initial_x/y + dock_width/height; the input/drag layer owns subsequent moves.
            placement.rect = LayoutRect{
                static_cast<float>(panel.initial_x),
                static_cast<float>(panel.initial_y),
                static_cast<float>(panel.dock_width),
                static_cast<float>(panel.dock_height)};
        } else {
            placement.rect = compute_docked_rect(work, panel);
        }

        placements.push_back(placement);
    }

    return placements;
}

}  // namespace Corona::Systems::UI
