//
// Created by GitHub Copilot on 2026/4/9.
//

#pragma once

#include "decl.h"
#include "widgets.h"

namespace vision {

class Window {
public:
    using MouseButtonCallback = ocarina::function<void(int /* button */, int /* action */, ocarina::float2 /* (x, y) */)>;
    using CursorPositionCallback = ocarina::function<void(ocarina::float2 /* (x, y) */)>;
    using WindowSizeCallback = ocarina::function<void(ocarina::uint2 /* (width, height) */)>;
    using KeyCallback = ocarina::function<void(int /* key */, int /* action */)>;
    using ScrollCallback = ocarina::function<void(ocarina::float2 /* (dx, dy) */)>;
    using UpdateCallback = ocarina::function<void(double)>;
    using BeginFrame = ocarina::function<void()>;
    using EndFrame = ocarina::function<void()>;
    using RenderCallback = ocarina::function<void()>;

protected:
    MouseButtonCallback mouse_button_callback_;
    CursorPositionCallback cursor_position_callback_;
    WindowSizeCallback window_size_callback_;
    KeyCallback key_callback_;
    ScrollCallback scroll_callback_;
    BeginFrame begin_frame_callback_;
    EndFrame end_frame_callback_;
    RenderCallback render_callback_;
    ocarina::float4 clear_color_{ocarina::make_float4(0, 0, 0, 0)};
    bool background_visible_{true};
    bool ui_enabled_{true};
    bool resizable_{false};
    ocarina::Clock clock_;
    double dt_{};
    ocarina::unique_ptr<Widgets> widgets_{};
    uint64_t window_handle_ = ocarina::InvalidUI64;

protected:
    virtual void _begin_frame() noexcept;
    virtual void _end_frame() noexcept;

public:
    explicit Window(bool resizable = false) noexcept;
    virtual void init(const char *name, ocarina::uint2 initial_size, bool resizable) noexcept = 0;
    virtual void init_widgets() noexcept = 0;
    Window(Window &&) noexcept = delete;
    virtual void full_screen() noexcept = 0;
    virtual void swap_monitor() noexcept = 0;
    Window(const Window &) noexcept = delete;
    Window &operator=(Window &&) noexcept = delete;
    Window &operator=(const Window &) noexcept = delete;
    virtual ~Window() noexcept = default;
    [[nodiscard]] Widgets *widgets() noexcept { return widgets_.get(); }
    [[nodiscard]] const Widgets *widgets() const noexcept { return widgets_.get(); }
    [[nodiscard]] double dt() const noexcept { return dt_; }
    [[nodiscard]] virtual ocarina::uint2 size() const noexcept = 0;
    [[nodiscard]] virtual bool should_close() const noexcept = 0;
    [[nodiscard]] virtual ocarina::uint shared_texture_handle() const noexcept { OC_ASSERT(0); return 0; }
    [[nodiscard]] explicit operator bool() const noexcept { return !should_close(); }
    [[nodiscard]] uint64_t get_window_handle() const noexcept { return window_handle_; }
    virtual Window &set_mouse_callback(MouseButtonCallback cb) noexcept;
    virtual Window &set_cursor_position_callback(CursorPositionCallback cb) noexcept;
    virtual Window &set_window_size_callback(WindowSizeCallback cb) noexcept;
    virtual Window &set_key_callback(KeyCallback cb) noexcept;
    virtual Window &set_scroll_callback(ScrollCallback cb) noexcept;
    virtual Window &set_begin_frame_callback(BeginFrame cb) noexcept;
    virtual Window &set_end_frame_callback(EndFrame cb) noexcept;
    virtual Window &set_render_callback(RenderCallback cb) noexcept;
    virtual Window &set_background_visible(bool visible) noexcept {
        background_visible_ = visible;
        return *this;
    }
    virtual Window &set_ui_enabled(bool enabled) noexcept {
        ui_enabled_ = enabled;
        return *this;
    }
    [[nodiscard]] bool background_visible() const noexcept { return background_visible_; }
    [[nodiscard]] bool ui_enabled() const noexcept { return ui_enabled_; }
    virtual void download_background(ocarina::float4 *data) const noexcept {
        OC_NOT_IMPLEMENT_ERROR(download_background);
    }
    virtual void set_background(const ocarina::uchar4 *pixels, ocarina::uint2 size) noexcept = 0;
    void set_background(const ocarina::uchar4 *pixels) noexcept {
        set_background(pixels, size());
    }
    virtual void set_background(const ocarina::Buffer<ocarina::float4> &buffer, ocarina::uint2 size) noexcept = 0;
    void set_background(const ocarina::Buffer<ocarina::float4> &buffer) noexcept {
        set_background(buffer, size());
    }
    void set_clear_color(ocarina::float4 color) noexcept { clear_color_ = color; }
    virtual void set_background(const ocarina::float4 *pixels, ocarina::uint2 size) noexcept = 0;
    void set_background(const ocarina::float4 *pixels) noexcept {
        set_background(pixels, size());
    }
    virtual void make_current() noexcept {}
    virtual void set_should_close() noexcept = 0;
    virtual void set_size(ocarina::uint2 size) noexcept = 0;
    virtual void run(UpdateCallback &&draw) noexcept;
    virtual void run_one_frame(UpdateCallback &&draw, double dt) noexcept;
    virtual void run_one_frame(UpdateCallback &&draw) noexcept {
        run_one_frame(OC_FORWARD(draw), 0);
    }
    virtual void show_window() noexcept = 0;
    virtual void hide_window() noexcept = 0;

    class WindowLoop {
    public:
        explicit WindowLoop(Window *window) : window_(window) {
            if (window_) {
                window_->_begin_frame();
            }
        }

        ~WindowLoop() {
            if (window_) {
                window_->_end_frame();
            }
        }

    private:
        Window *window_{nullptr};
    };
};

}// namespace vision