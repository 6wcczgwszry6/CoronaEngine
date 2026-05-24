//
// Created by Z on 2025/03/21.
//

#pragma once

#include "UI/GUI.h"

namespace vision {
class Pipeline;

class PipelineUI {
private:
    Pipeline *pipeline_{};
    bool show_fps_{true};
    bool show_scene_data_{true};
    bool show_framebuffer_data_{true};
    bool show_detail_{true};
    bool show_stats_{true};
    bool show_hotfix_{true};
    bool show_output_{false};

    /// node for show detail
    mutable GUIRenderable *cur_node_{nullptr};

public:
    explicit PipelineUI(Pipeline *pipeline) noexcept : pipeline_(pipeline) {}
    bool render(Widgets *widgets) noexcept;
    bool render_perf_panel(Widgets *widgets) noexcept;
    void render_detail(Widgets *widgets) noexcept;
    void render_stats(Widgets *widgets) noexcept;
    void render_hotfix(Widgets *widgets) noexcept;
    void render_output(Widgets *widgets) noexcept;
    void filp_show_fps() noexcept { show_fps_ = !show_fps_; }
    void set_cur_node(GUIRenderable *node) const noexcept { cur_node_ = node; }
    [[nodiscard]] GUIRenderable *cur_node() const noexcept { return cur_node_; }
};

}// namespace vision
