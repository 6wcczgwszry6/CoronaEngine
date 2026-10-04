//
// Created by GitHub Copilot on 2026/4/9.
//

#pragma once

#include "window/GUI/window.h"
#include "widgets.h"

namespace vision {

class GLFWContext;

class GLWindow : public Window {
private:
    bool ui_backend_enabled_{true};
    ocarina::shared_ptr<GLFWContext> context_;
    GLFWwindow *handle_{nullptr};
    GLFWmonitor *monitor_{nullptr};
    int monitor_index = 0;
    bool isFullscreen = false;
    int windowedX{}, windowedY{}, windowedWidth{}, windowedHeight{};
    std::chrono::steady_clock::time_point lastF11Toggle;
    mutable ocarina::unique_ptr<GLTexture> texture_;

private:
    void _begin_frame() noexcept override;
    void _end_frame() noexcept override;

public:
    GLWindow(const char *name, ocarina::uint2 initial_size, bool resizable = false, bool enable_ui = true) noexcept;
    void init(const char *name, ocarina::uint2 initial_size, bool resizable) noexcept override;
    void init_widgets() noexcept override;
    GLWindow(GLWindow &&) noexcept = delete;
    GLWindow(const GLWindow &) noexcept = delete;
    GLWindow &operator=(GLWindow &&) noexcept = delete;
    GLWindow &operator=(const GLWindow &) noexcept = delete;
    ~GLWindow() noexcept override;
    [[nodiscard]] ocarina::uint2 size() const noexcept override;
    [[nodiscard]] bool should_close() const noexcept override;
    [[nodiscard]] bool has_active_ui_backend() const noexcept {
        return ui_backend_enabled_ && ui_enabled();
    }
    [[nodiscard]] auto handle() const noexcept { return handle_; }
    void full_screen() noexcept override;
    void swap_monitor() noexcept override;
    void download_background(ocarina::float4 *data) const noexcept override;
    [[nodiscard]] ocarina::uint shared_texture_handle() const noexcept override { return texture_->tex_handle(); }
    void set_background(const ocarina::uchar4 *pixels, ocarina::uint2 size) noexcept override;
    void set_background(const ocarina::float4 *pixels, ocarina::uint2 size) noexcept override;
    void set_background(const ocarina::Buffer<ocarina::float4> &buffer, ocarina::uint2 size) noexcept override;
    void make_current() noexcept override;
    void set_should_close() noexcept override;
    void set_size(ocarina::uint2 size) noexcept override;
    void show_window() noexcept override;
    void hide_window() noexcept override;
};

}// namespace vision