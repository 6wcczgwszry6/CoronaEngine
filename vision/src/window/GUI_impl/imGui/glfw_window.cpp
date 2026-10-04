//
// Created by GitHub Copilot on 2026/4/9.
//

#include "glfw_window.h"
#include "ImGuizmo.h"
#include "core/util/logging.h"

#ifdef _WIN32
#define GLFW_EXPOSE_NATIVE_WIN32
#include "GLFW/glfw3native.h"
#endif

namespace vision {

namespace {

[[nodiscard]] bool should_capture_mouse_input(const GLWindow *window) noexcept {
    return window->has_active_ui_backend() && ImGui::GetIO().WantCaptureMouse;
}

[[nodiscard]] bool should_capture_keyboard_input(const GLWindow *window) noexcept {
    return window->has_active_ui_backend() && ImGui::GetIO().WantCaptureKeyboard;
}

void blit_background_texture(GLuint tex_handle, ocarina::uint2 tex_size, int display_w, int display_h) noexcept {
    GLuint read_fbo = 0;
    VISION_CHECK_GL(glGenFramebuffers(1, &read_fbo));
    VISION_CHECK_GL(glBindFramebuffer(GL_READ_FRAMEBUFFER, read_fbo));
    VISION_CHECK_GL(glFramebufferTexture2D(GL_READ_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex_handle, 0));
    VISION_CHECK_GL(glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0));
    VISION_CHECK_GL(glBlitFramebuffer(0, 0, static_cast<GLint>(tex_size.x), static_cast<GLint>(tex_size.y),
                                      0, display_h, display_w, 0,
                                      GL_COLOR_BUFFER_BIT, GL_LINEAR));
    VISION_CHECK_GL(glBindFramebuffer(GL_READ_FRAMEBUFFER, 0));
    VISION_CHECK_GL(glDeleteFramebuffers(1, &read_fbo));
}

}// namespace

class GLFWContext {
public:
    GLFWContext() noexcept {
        glfwSetErrorCallback([](int error, const char *message) noexcept {
            OC_WARNING_FORMAT("GLFW error (code = {}): {}", error, message);
        });
        if (!glfwInit()) { OC_ERROR("Failed to initialize GLFW."); }
    }
    ~GLFWContext() noexcept { glfwTerminate(); }
    GLFWContext(GLFWContext &&) noexcept = delete;
    GLFWContext(const GLFWContext &) noexcept = delete;
    GLFWContext &operator=(GLFWContext &&) noexcept = delete;
    GLFWContext &operator=(const GLFWContext &) noexcept = delete;

    [[nodiscard]] static auto retain() noexcept {
        static std::weak_ptr<GLFWContext> instance;
        if (auto p = instance.lock()) { return p; }
        auto p = ocarina::make_shared<GLFWContext>();
        instance = p;
        return p;
    }
};

void GLWindow::init_widgets() noexcept {
    if (!ui_backend_enabled_) {
        widgets_.reset();
        return;
    }
    widgets_ = ocarina::make_unique<ImGuiWidgets>(this);
}

void GLWindow::init(const char *name, ocarina::uint2 initial_size, bool resizable) noexcept {
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 1);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
    glfwWindowHint(GLFW_RESIZABLE, resizable);

    monitor_ = glfwGetPrimaryMonitor();
    const GLFWvidmode *mode = glfwGetVideoMode(monitor_);
    if (ocarina::is_zero(initial_size)) {
        initial_size.x = static_cast<ocarina::uint>(mode->width);
        initial_size.y = static_cast<ocarina::uint>(mode->height);
    }
    handle_ = glfwCreateWindow(static_cast<int>(initial_size.x), static_cast<int>(initial_size.y), name, nullptr, nullptr);
    if (handle_ == nullptr) {
        const char *error = nullptr;
        glfwGetError(&error);
        OC_ERROR_FORMAT("Failed to create GLFW window: {}.", error);
    }
#ifdef _WIN32
    window_handle_ = reinterpret_cast<uint64_t>(glfwGetWin32Window(handle_));
#endif
    glfwMakeContextCurrent(handle_);
    glfwSwapInterval(0);

    if (!gladLoadGL()) { OC_ERROR("Failed to initialize GLAD."); }

    init_widgets();
    if (ui_backend_enabled_) {
        IMGUI_CHECKVERSION();
        ImGuizmo::SetImGuiContext(ImGui::CreateContext());
        ImGui::StyleColorsDark();
        ImGui_ImplGlfw_InitForOpenGL(handle_, true);
        ImGui_ImplOpenGL3_Init("#version 330");
    }
    ocarina::uint2 res = size();
    texture_ = ocarina::make_unique<GLTexture>();
    texture_->update(res);
    glfwSetWindowUserPointer(handle_, this);
    glfwSetMouseButtonCallback(handle_, [](GLFWwindow *window, int button, int action, int mods) noexcept {
        auto self = static_cast<GLWindow *>(glfwGetWindowUserPointer(window));
        if (should_capture_mouse_input(self)) {
            ImGui_ImplGlfw_MouseButtonCallback(window, button, action, mods);
        } else {
            double x = 0.0;
            double y = 0.0;
            glfwGetCursorPos(self->handle(), &x, &y);
            if (auto &&cb = self->mouse_button_callback_) {
                cb(button, action, ocarina::make_float2(static_cast<float>(x), static_cast<float>(y)));
            }
        }
    });
    glfwSetCursorPosCallback(handle_, [](GLFWwindow *window, double x, double y) noexcept {
        auto self = static_cast<GLWindow *>(glfwGetWindowUserPointer(window));
        if (auto &&cb = self->cursor_position_callback_) {
            cb(ocarina::make_float2(static_cast<float>(x), static_cast<float>(y)));
        }
    });
    glfwSetWindowSizeCallback(handle_, [](GLFWwindow *window, int width, int height) noexcept {
        auto self = static_cast<GLWindow *>(glfwGetWindowUserPointer(window));
        ocarina::uint2 res = ocarina::make_uint2(width, height);
        if (width * height > 0) {
            self->texture_->update(res);
        }
        if (auto &&cb = self->window_size_callback_) {
            cb(res);
        }
    });
    glfwSetKeyCallback(handle_, [](GLFWwindow *window, int key, int scancode, int action, int mods) noexcept {
        auto self = static_cast<GLWindow *>(glfwGetWindowUserPointer(window));
        if (self->has_active_ui_backend()) {
            ImGui_ImplGlfw_KeyCallback(window, key, scancode, action, mods);
        }
        if (!should_capture_keyboard_input(self)) {
            if (auto &&cb = self->key_callback_) { cb(key, action); }
        }
    });
    glfwSetScrollCallback(handle_, [](GLFWwindow *window, double dx, double dy) noexcept {
        auto self = static_cast<GLWindow *>(glfwGetWindowUserPointer(window));
        if (should_capture_mouse_input(self)) {
            ImGui_ImplGlfw_ScrollCallback(window, dx, dy);
        } else {
            if (auto &&cb = self->scroll_callback_) {
                cb(ocarina::make_float2(static_cast<float>(dx), static_cast<float>(dy)));
            }
        }
    });
    glfwSetCharCallback(handle_, [](GLFWwindow *window, unsigned int c) noexcept {
        auto self = static_cast<GLWindow *>(glfwGetWindowUserPointer(window));
        if (self->has_active_ui_backend()) {
            ImGui_ImplGlfw_CharCallback(window, c);
        }
    });
}

GLWindow::GLWindow(const char *name, ocarina::uint2 initial_size, bool resizable, bool enable_ui) noexcept
        : Window(resizable),
            ui_backend_enabled_{enable_ui},
      context_{GLFWContext::retain()} {
    init(name, initial_size, resizable);
    glfwGetWindowPos(handle_, &windowedX, &windowedY);
    glfwGetWindowSize(handle_, &windowedWidth, &windowedHeight);
    lastF11Toggle = std::chrono::steady_clock::now();
}

GLWindow::~GLWindow() noexcept {
    glfwMakeContextCurrent(handle_);
    texture_.reset();
    widgets_.reset();
    if (ui_backend_enabled_) {
        ImGui_ImplOpenGL3_Shutdown();
        ImGui_ImplGlfw_Shutdown();
        ImGui::DestroyContext();
    }
    glfwDestroyWindow(handle_);
}

ocarina::uint2 GLWindow::size() const noexcept {
    int width = 0;
    int height = 0;
    glfwGetWindowSize(handle_, &width, &height);
    return ocarina::make_uint2(static_cast<ocarina::uint>(width), static_cast<ocarina::uint>(height));
}

bool GLWindow::should_close() const noexcept {
    return glfwWindowShouldClose(handle_);
}

void GLWindow::full_screen() noexcept {
    auto now = std::chrono::steady_clock::now();
    if (now - lastF11Toggle > std::chrono::milliseconds(100)) {
        lastF11Toggle = now;
        if (isFullscreen) {
            glfwSetWindowMonitor(handle_, nullptr, windowedX, windowedY, windowedWidth, windowedHeight, 0);
        } else {
            const GLFWvidmode *mode = glfwGetVideoMode(monitor_);
            glfwGetWindowPos(handle_, &windowedX, &windowedY);
            glfwGetWindowSize(handle_, &windowedWidth, &windowedHeight);
            glfwSetWindowMonitor(handle_, monitor_, 0, 0, mode->width, mode->height, mode->refreshRate);
        }
        isFullscreen = !isFullscreen;
    }
}

void GLWindow::swap_monitor() noexcept {
    if (isFullscreen) {
        int count;
        GLFWmonitor **monitors = glfwGetMonitors(&count);
        monitor_index = (monitor_index + 1) % count;
        monitor_ = monitors[monitor_index];
        const GLFWvidmode *mode = glfwGetVideoMode(monitor_);
        glfwSetWindowMonitor(handle_, monitor_, 0, 0, mode->width, mode->height, mode->refreshRate);
    }
}

void GLWindow::download_background(ocarina::float4 *data) const noexcept {
    texture_->download(data);
}

void GLWindow::set_background(const ocarina::uchar4 *pixels, ocarina::uint2 size) noexcept {
    if (texture_ == nullptr) {
        texture_ = ocarina::make_unique<GLTexture>();
    }
    texture_->load(pixels, size);
}

void GLWindow::set_background(const ocarina::float4 *pixels, ocarina::uint2 size) noexcept {
    if (texture_ == nullptr) {
        texture_ = ocarina::make_unique<GLTexture>();
        texture_->update(size);
    }
    texture_->upload(pixels);
}

void GLWindow::set_background(const ocarina::Buffer<ocarina::float4> &buffer, ocarina::uint2 size) noexcept {
    if (texture_ == nullptr) {
        texture_ = ocarina::make_unique<GLTexture>();
        texture_->update(size);
    }
    texture_->bind();
}

void GLWindow::make_current() noexcept {
    glfwMakeContextCurrent(handle_);
}

void GLWindow::set_should_close() noexcept {
    glfwSetWindowShouldClose(handle_, true);
}

void GLWindow::_begin_frame() noexcept {
    if (!should_close()) {
        glfwMakeContextCurrent(handle_);
        glfwPollEvents();
        if (has_active_ui_backend()) {
            ImGui_ImplOpenGL3_NewFrame();
            ImGui_ImplGlfw_NewFrame();
            ImGui::NewFrame();
            ImGuizmo::BeginFrame();
        }
        Window::_begin_frame();
    }
}

void GLWindow::_end_frame() noexcept {
    if (!should_close()) {
        Window::_end_frame();
        int display_w = 0;
        int display_h = 0;
        glfwGetFramebufferSize(handle_, &display_w, &display_h);
        glViewport(0, 0, display_w, display_h);
        glClearColor(clear_color_.x, clear_color_.y, clear_color_.z, clear_color_.w);
        glClear(GL_COLOR_BUFFER_BIT);
        if (background_visible_ && texture_ != nullptr) {
            if (has_active_ui_backend()) {
                ImVec2 background_size{static_cast<float>(texture_->size().x), static_cast<float>(texture_->size().y)};
                ImGui::GetBackgroundDrawList()->AddImage(
                    reinterpret_cast<ImTextureID>(static_cast<uint64_t>(texture_->tex_handle())), {}, background_size);
            } else {
                blit_background_texture(texture_->tex_handle(), texture_->size(), display_w, display_h);
            }
        }
        if (auto &&cb = render_callback_) {
            cb();
            glDisable(GL_DEPTH_TEST);
            glDisable(GL_CULL_FACE);
            glDisable(GL_SCISSOR_TEST);
            glBindVertexArray(0u);
            glUseProgram(0u);
        }
        if (has_active_ui_backend()) {
            ImGui::Render();
            ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        }
        glfwSwapBuffers(handle_);
    }
}

void GLWindow::set_size(ocarina::uint2 size) noexcept {
    if (resizable_) {
        glfwSetWindowSize(handle_, static_cast<int>(size.x), static_cast<int>(size.y));
    } else {
        OC_WARNING("Ignoring resize on non-resizable window.");
    }
}

void GLWindow::show_window() noexcept {}
void GLWindow::hide_window() noexcept {}

}// namespace vision