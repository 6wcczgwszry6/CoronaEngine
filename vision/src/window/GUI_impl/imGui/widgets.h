//
// Created by GitHub Copilot on 2026/4/9.
//

#pragma once

#include "gl_helper.h"
#include "window/GUI/window.h"
#include "window/GUI/widgets.h"
#include "imgui_impl_opengl3.h"
#include "imgui_impl_glfw.h"
#include "core/image/image.h"

namespace vision {

class GLTexture {
private:
    GLuint tex_handle_{ocarina::InvalidUI32};
    bool is_float4_{false};
    ocarina::uint2 size_{};
    mutable bool binding_{false};

public:
    explicit GLTexture() noexcept = default;

    void generate() noexcept {
        VISION_CHECK_GL(glGenTextures(1, &tex_handle_));
    }

    [[nodiscard]] bool valid() const noexcept { return tex_handle_ != ocarina::InvalidUI32; }

private:
    void setup_tex_params() noexcept {
        VISION_CHECK_GL(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR));
        VISION_CHECK_GL(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR));
        VISION_CHECK_GL(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE));
        VISION_CHECK_GL(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE));
    }

    void load_impl(const void *pixels, ocarina::uint2 size, bool is_float,
                   GLint internal_fmt, GLenum type) noexcept {
        bind();
        if (ocarina::any(size_ != size) || is_float4_ != is_float) {
            size_ = size;
            is_float4_ = is_float;
            VISION_CHECK_GL(glTexImage2D(GL_TEXTURE_2D, 0, internal_fmt, size.x, size.y, 0, GL_RGBA, type, pixels));
            setup_tex_params();
        } else {
            VISION_CHECK_GL(glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, size_.x, size_.y, GL_RGBA, type, pixels));
        }
        unbind();
    }

public:
    void update(ocarina::uint2 size) noexcept {
        clear();
        size_ = size;
        generate();
        bind();
        VISION_CHECK_GL(glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, size_.x,
                                     size_.y, 0, GL_RGBA, GL_FLOAT, nullptr));
        setup_tex_params();
        unbind();
    }

    GLTexture(GLTexture &&) noexcept = delete;
    GLTexture(const GLTexture &) noexcept = delete;
    GLTexture &operator=(GLTexture &&) noexcept = delete;
    GLTexture &operator=(const GLTexture &) noexcept = delete;

    ~GLTexture() noexcept { clear(); }

    void clear() noexcept {
        if (tex_handle_ != 0) {
            VISION_CHECK_GL(glDeleteTextures(1, &tex_handle_));
            tex_handle_ = 0;
        }
        size_ = ocarina::make_uint2(0);
    }

    [[nodiscard]] GLuint tex_handle() const noexcept { return tex_handle_; }
    [[nodiscard]] auto size() const noexcept { return size_; }
    [[nodiscard]] bool binding() const noexcept { return binding_; }

    void bind() const noexcept {
        VISION_CHECK_GL(glBindTexture(GL_TEXTURE_2D, tex_handle_));
    }

    void unbind() const noexcept {
        VISION_CHECK_GL(glBindTexture(GL_TEXTURE_2D, 0));
    }

    void load(const ocarina::uchar4 *pixels, ocarina::uint2 size) noexcept {
        load_impl(pixels, size, false, GL_RGBA8, GL_UNSIGNED_BYTE);
    }

    void load(const ocarina::float4 *pixels, ocarina::uint2 size) noexcept {
        load_impl(pixels, size, true, GL_RGBA32F, GL_FLOAT);
    }

    void download(ocarina::float4 *pixels) const noexcept {
        bind();
        VISION_CHECK_GL(glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_FLOAT, pixels));
        unbind();
    }

    void upload(const ocarina::float4 *pixels) noexcept {
        bind();
        VISION_CHECK_GL(glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, size_.x, size_.y, GL_RGBA, GL_FLOAT, pixels));
        unbind();
    }
};

class ImGuiWidgets : public Widgets {
private:
    using TextureVec = ocarina::vector<ocarina::UP<GLTexture>>;
    ocarina::map<uint64_t, TextureVec> texture_map_;
    Window *window_{};

private:
    [[nodiscard]] static uint64_t calculate_key(const ocarina::ImageView &image) noexcept;
    [[nodiscard]] GLTexture *obtain_texture(const ocarina::ImageView &image) noexcept;

public:
    explicit ImGuiWidgets(Window *window);

    void push_item_width(int width) noexcept override;
    void pop_item_width() noexcept override;
    void begin_tool_tip() noexcept override;
    void end_tool_tip() noexcept override;
    void begin_disabled() noexcept override;
    void end_disabled() noexcept override;
    bool radio_button(const std::string &label, bool active) noexcept override;
    void image(ocarina::uint tex_handle, ocarina::uint2 size, ocarina::float2 uv0, ocarina::float2 uv1) noexcept override;
    void image(const ocarina::Image &image) noexcept override;
    void image(const ocarina::ImageView &image_view) noexcept override;
    ocarina::uint2 node_size() noexcept override;
    bool push_window(const ocarina::string &label) noexcept override;
    bool push_window(const ocarina::string &label, WindowFlag flag) noexcept override;
    void pop_window() noexcept override;
    bool tree_node(const ocarina::string &label) noexcept override;
    void tree_pop() noexcept override;
    void push_id(char *str) noexcept override;
    void pop_id() noexcept override;
    bool folding_header(const ocarina::string &label) noexcept override;
    bool begin_main_menu_bar() noexcept override;
    void end_main_menu_bar() noexcept override;
    bool begin_menu_bar() noexcept override;
    bool begin_menu(const ocarina::string &label) noexcept override;
    bool menu_item(const ocarina::string &label) noexcept override;
    void end_menu() noexcept override;
    void end_menu_bar() noexcept override;
    void text(const char *format, ...) noexcept override;
    bool input_text(const std::string &label, char *buf, size_t buf_size) noexcept override;
    void text_wrapped(const char *format, ...) noexcept override;
    bool check_box(const ocarina::string &label, bool *val) noexcept override;
    bool slider_float(const ocarina::string &label, float *val, float min, float max) noexcept override;
    bool slider_float2(const ocarina::string &label, ocarina::float2 *val, float min, float max) noexcept override;
    bool slider_float3(const ocarina::string &label, ocarina::float3 *val, float min, float max) noexcept override;
    bool slider_float4(const ocarina::string &label, ocarina::float4 *val, float min, float max) noexcept override;
    bool slider_int(const ocarina::string &label, int *val, int min, int max) noexcept override;
    bool slider_int2(const ocarina::string &label, ocarina::int2 *val, int min, int max) noexcept override;
    bool slider_int3(const ocarina::string &label, ocarina::int3 *val, int min, int max) noexcept override;
    bool slider_int4(const ocarina::string &label, ocarina::int4 *val, int min, int max) noexcept override;
    bool slider_uint(const ocarina::string &label, ocarina::uint *val, ocarina::uint min, ocarina::uint max) noexcept override;
    bool slider_uint2(const ocarina::string &label, ocarina::uint2 *val, ocarina::uint min, ocarina::uint max) noexcept override;
    bool slider_uint3(const ocarina::string &label, ocarina::uint3 *val, ocarina::uint min, ocarina::uint max) noexcept override;
    bool slider_uint4(const ocarina::string &label, ocarina::uint4 *val, ocarina::uint min, ocarina::uint max) noexcept override;
    bool color_edit(const ocarina::string &label, ocarina::float3 *val) noexcept override;
    bool color_edit(const ocarina::string &label, ocarina::float4 *val) noexcept override;
    bool button(const ocarina::string &label, ocarina::uint2 size) noexcept override;
    bool button(const ocarina::string &label) noexcept override;
    void same_line() noexcept override;
    void new_line() noexcept override;
    bool input_int(const ocarina::string &label, int *val) noexcept override;
    bool input_int(const ocarina::string &label, int *val, int step, int step_fast) noexcept override;
    bool input_int2(const ocarina::string &label, ocarina::int2 *val) noexcept override;
    bool input_int3(const ocarina::string &label, ocarina::int3 *val) noexcept override;
    bool input_int4(const ocarina::string &label, ocarina::int4 *val) noexcept override;
    bool input_uint(const ocarina::string &label, ocarina::uint *val) noexcept override;
    bool input_uint(const ocarina::string &label, ocarina::uint *val, ocarina::uint step, ocarina::uint step_fast) noexcept override;
    bool input_uint2(const ocarina::string &label, ocarina::uint2 *val) noexcept override;
    bool input_uint3(const ocarina::string &label, ocarina::uint3 *val) noexcept override;
    bool input_uint4(const ocarina::string &label, ocarina::uint4 *val) noexcept override;
    bool input_float(const ocarina::string &label, float *val) noexcept override;
    bool input_float(const ocarina::string &label, float *val, float step, float step_fast) noexcept override;
    bool input_float2(const ocarina::string &label, ocarina::float2 *val) noexcept override;
    bool input_float3(const ocarina::string &label, ocarina::float3 *val) noexcept override;
    bool input_float4(const ocarina::string &label, ocarina::float4 *val) noexcept override;
    bool drag_int(const ocarina::string &label, int *val, float speed, int min, int max) noexcept override;
    bool drag_int2(const ocarina::string &label, ocarina::int2 *val, float speed, int min, int max) noexcept override;
    bool drag_int3(const ocarina::string &label, ocarina::int3 *val, float speed, int min, int max) noexcept override;
    bool drag_int4(const ocarina::string &label, ocarina::int4 *val, float speed, int min, int max) noexcept override;
    bool drag_uint(const ocarina::string &label, ocarina::uint *val, float speed, ocarina::uint min, ocarina::uint max) noexcept override;
    bool drag_uint2(const ocarina::string &label, ocarina::uint2 *val, float speed, ocarina::uint min, ocarina::uint max) noexcept override;
    bool drag_uint3(const ocarina::string &label, ocarina::uint3 *val, float speed, ocarina::uint min, ocarina::uint max) noexcept override;
    bool drag_uint4(const ocarina::string &label, ocarina::uint4 *val, float speed, ocarina::uint min, ocarina::uint max) noexcept override;
    bool drag_float(const ocarina::string &label, float *val, float speed, float min, float max, const char *fmt) noexcept override;
    bool drag_float2(const ocarina::string &label, ocarina::float2 *val, float speed, float min, float max, const char *fmt) noexcept override;
    bool drag_float3(const ocarina::string &label, ocarina::float3 *val, float speed, float min, float max, const char *fmt) noexcept override;
    bool drag_float4(const ocarina::string &label, ocarina::float4 *val, float speed, float min, float max, const char *fmt) noexcept override;
    bool combo(const std::string &label, int *current_item, const char *const *items, int item_num) noexcept override;
    bool is_item_hovered() noexcept override;
    ocarina::float2 mouse_pos() noexcept override;
};

}// namespace vision