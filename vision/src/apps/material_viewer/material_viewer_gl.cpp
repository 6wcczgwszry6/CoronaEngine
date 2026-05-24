#include "material_viewer_gl.h"

#include "math/warp.h"

#include <glad/glad.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <vector>

using namespace vision;
using namespace ocarina;

namespace {

struct MeshVertex {
    float x{};
    float y{};
    float z{};
    float r{};
    float g{};
    float b{};
    float a{1.f};
};

struct MeshData {
    std::vector<MeshVertex> vertices{};
    std::vector<uint32_t> indices{};
    PlotRect rect{};
    GLenum primitive{GL_TRIANGLES};
};

struct OrbitCamera {
    float3 eye{};
    float3 right{};
    float3 up{};
    float3 forward{};
    float2 center{};
    float focal{};
    float near_plane{};
    float far_plane{};
};

float tone_value_gl(float value, float scale, bool log_scale) {
    float normalized = scale > 0.f ? value / scale : 0.f;
    normalized = std::max(0.f, normalized);
    if (!log_scale) {
        return std::clamp(normalized, 0.f, 1.f);
    }
    return std::log1p(normalized * 16.f) / std::log1p(16.f);
}

float lobe_height_value_gl(float value, bool log_scale, float height_scale) {
    float positive = std::max(0.f, value) * std::max(0.01f, height_scale);
    if (!log_scale) {
        return std::min(positive, 4.f);
    }
    return std::min(std::log1p(positive * 12.f) / std::log1p(12.f), 4.f);
}

OrbitCamera make_orbit_camera(const PlotRect &rect, float yaw_deg, float pitch_deg, float zoom) {
    OrbitCamera camera;
    const ViewerProjector projector = make_material_viewer_projector(rect, zoom);
    camera.eye = make_float3(0.f, 0.f, projector.view_distance);
    camera.forward = normalize(-camera.eye);
    float3 world_up = make_float3(0.f, 1.f, 0.f);
    if (std::abs(dot(camera.forward, world_up)) > 0.98f) {
        world_up = make_float3(0.f, 0.f, 1.f);
    }
    camera.right = normalize(cross(camera.forward, world_up));
    camera.up = normalize(cross(camera.right, camera.forward));
    camera.center = projector.center;
    camera.focal = projector.base_scale;
    camera.near_plane = kViewer3DNearPlane;
    camera.far_plane = kViewer3DFarPlane;
    return camera;
}

bool project_world_point(const float3 &point, const OrbitCamera &camera, uint2 window_size, float2 *ndc, float *depth) {
    float3 relative = point - camera.eye;
    float cam_x = dot(relative, camera.right);
    float cam_y = dot(relative, camera.up);
    float cam_z = dot(relative, camera.forward);
    if (cam_z <= camera.near_plane) {
        return false;
    }
    float perspective = camera.focal / cam_z;
    float2 screen = make_float2(camera.center.x + cam_x * perspective,
                                camera.center.y - cam_y * perspective);
    *ndc = material_viewer_screen_to_ndc(window_size, screen);
    *depth = std::clamp((cam_z - camera.near_plane) / (camera.far_plane - camera.near_plane) * 2.f - 1.f, -0.98f, 0.98f);
    return true;
}

MeshData build_lobe_mesh(const std::vector<float> &grid,
                         uint resolution,
                         const PlotRect &rect,
                         uint2 window_size,
                         float scale,
                         bool log_scale,
                         float sign,
                         float height_scale,
                         float yaw_deg,
                         float pitch_deg,
                         float zoom,
                         float3 base_color) {
    MeshData mesh;
    mesh.rect = rect;
    if (grid.empty() || resolution < 2u || rect.width < 8u || rect.height < 8u) {
        return mesh;
    }

    const OrbitCamera camera = make_orbit_camera(rect, yaw_deg, pitch_deg, zoom);
    const float3 light_dir = normalize(make_float3(-0.45f, 0.82f, 0.35f));

    std::vector<int> vertex_ids(static_cast<size_t>(resolution) * resolution, -1);
    mesh.vertices.reserve(static_cast<size_t>(resolution) * resolution);
    mesh.indices.reserve(static_cast<size_t>(resolution - 1u) * (resolution - 1u) * 6u);

    for (uint gy = 0; gy < resolution; ++gy) {
        for (uint gx = 0; gx < resolution; ++gx) {
            float2 uv = make_float2((static_cast<float>(gx) + 0.5f) / static_cast<float>(resolution),
                                    (static_cast<float>(gy) + 0.5f) / static_cast<float>(resolution));
            float2 disk = square_to_disk<EPort::H>(uv);

            float3 direction = material_viewer_direction_from_disk(disk, sign);
            float value = grid[static_cast<size_t>(gy) * resolution + gx];
            float radial = lobe_height_value_gl(value, log_scale, height_scale);
            float3 point = material_viewer_rotate_point(direction * radial, yaw_deg, pitch_deg);
            float2 ndc{};
            float depth = 0.f;
            if (!project_world_point(point, camera, window_size, &ndc, &depth)) {
                continue;
            }
            float3 rotated_normal = material_viewer_rotate_point(direction, yaw_deg, pitch_deg);
            float shade = std::clamp(0.25f + 0.75f * dot(normalize(rotated_normal), light_dir), 0.f, 1.f);
            float3 color = base_color * (0.25f + 0.75f * shade);

            vertex_ids[static_cast<size_t>(gy) * resolution + gx] = static_cast<int>(mesh.vertices.size());
            mesh.vertices.emplace_back(MeshVertex{ndc.x, ndc.y, depth, color.x, color.y, color.z, 1.f});
        }
    }

    auto append_triangle = [&](int a, int b, int c) {
        if (a < 0 || b < 0 || c < 0) {
            return;
        }
        mesh.indices.emplace_back(static_cast<uint32_t>(a));
        mesh.indices.emplace_back(static_cast<uint32_t>(b));
        mesh.indices.emplace_back(static_cast<uint32_t>(c));
    };

    for (uint gy = 0; gy + 1u < resolution; ++gy) {
        for (uint gx = 0; gx + 1u < resolution; ++gx) {
            int v00 = vertex_ids[static_cast<size_t>(gy) * resolution + gx];
            int v10 = vertex_ids[static_cast<size_t>(gy) * resolution + (gx + 1u)];
            int v01 = vertex_ids[static_cast<size_t>(gy + 1u) * resolution + gx];
            int v11 = vertex_ids[static_cast<size_t>(gy + 1u) * resolution + (gx + 1u)];
            append_triangle(v00, v10, v11);
            append_triangle(v00, v11, v01);
        }
    }
    return mesh;
}

MeshData build_slice_plane_mesh(const PlotRect &rect,
                                uint2 window_size,
                                float yaw_deg,
                                float pitch_deg,
                                float zoom,
                                float slice_plane_height,
                                float alpha) {
    MeshData mesh;
    mesh.rect = rect;
    if (rect.width < 8u || rect.height < 8u) {
        return mesh;
    }

    constexpr uint kSegments = 48u;
    const OrbitCamera camera = make_orbit_camera(rect, yaw_deg, pitch_deg, zoom);
    const float y = std::clamp(slice_plane_height, -0.98f, 0.98f);
    const float radius = std::sqrt(std::max(0.f, 1.f - y * y));
    const float3 plane_color = make_float3(0.54f, 0.68f, 0.98f);

    float2 center_ndc{};
    float center_depth = 0.f;
    if (!project_world_point(make_float3(0.f, y, 0.f), camera, window_size, &center_ndc, &center_depth)) {
        return mesh;
    }
    mesh.vertices.emplace_back(MeshVertex{center_ndc.x, center_ndc.y, center_depth, plane_color.x, plane_color.y, plane_color.z, alpha});

    for (uint i = 0; i <= kSegments; ++i) {
        float theta = static_cast<float>(i) / static_cast<float>(kSegments) * kTwoPi;
        float3 point = material_viewer_rotate_point(make_float3(std::cos(theta) * radius, y, std::sin(theta) * radius), yaw_deg, pitch_deg);
        float2 ndc{};
        float depth = 0.f;
        if (!project_world_point(point, camera, window_size, &ndc, &depth)) {
            continue;
        }
        mesh.vertices.emplace_back(MeshVertex{ndc.x, ndc.y, depth, plane_color.x, plane_color.y, plane_color.z, alpha});
    }

    for (uint i = 1u; i + 1u < mesh.vertices.size(); ++i) {
        mesh.indices.emplace_back(0u);
        mesh.indices.emplace_back(i);
        mesh.indices.emplace_back(i + 1u);
    }
    return mesh;
}

MeshData build_slice_plane_wire_mesh(const PlotRect &rect,
                                     uint2 window_size,
                                     float yaw_deg,
                                     float pitch_deg,
                                     float zoom,
                                     float slice_plane_height) {
    MeshData mesh;
    mesh.rect = rect;
    mesh.primitive = GL_LINES;
    if (rect.width < 8u || rect.height < 8u) {
        return mesh;
    }

    constexpr uint kSegments = 64u;
    const OrbitCamera camera = make_orbit_camera(rect, yaw_deg, pitch_deg, zoom);
    const float y = std::clamp(slice_plane_height, -0.98f, 0.98f);
    const float radius = std::sqrt(std::max(0.f, 1.f - y * y));
    const float3 ring_color = make_float3(0.74f, 0.84f, 1.0f);
    const float3 x_axis_color = make_float3(0.90f, 0.42f, 0.38f);
    const float3 z_axis_color = make_float3(0.37f, 0.60f, 0.96f);

    auto append_line = [&](float3 a, float3 b, float3 color) {
        float2 a_ndc{};
        float2 b_ndc{};
        float a_depth = 0.f;
        float b_depth = 0.f;
        if (!project_world_point(a, camera, window_size, &a_ndc, &a_depth) ||
            !project_world_point(b, camera, window_size, &b_ndc, &b_depth)) {
            return;
        }
        uint32_t base = static_cast<uint32_t>(mesh.vertices.size());
        mesh.vertices.emplace_back(MeshVertex{a_ndc.x, a_ndc.y, a_depth, color.x, color.y, color.z, 1.f});
        mesh.vertices.emplace_back(MeshVertex{b_ndc.x, b_ndc.y, b_depth, color.x, color.y, color.z, 1.f});
        mesh.indices.emplace_back(base);
        mesh.indices.emplace_back(base + 1u);
    };

    for (uint i = 0; i < kSegments; ++i) {
        float theta0 = static_cast<float>(i) / static_cast<float>(kSegments) * kTwoPi;
        float theta1 = static_cast<float>(i + 1u) / static_cast<float>(kSegments) * kTwoPi;
        float3 p0 = material_viewer_rotate_point(make_float3(std::cos(theta0) * radius, y, std::sin(theta0) * radius), yaw_deg, pitch_deg);
        float3 p1 = material_viewer_rotate_point(make_float3(std::cos(theta1) * radius, y, std::sin(theta1) * radius), yaw_deg, pitch_deg);
        append_line(p0, p1, ring_color);
    }

    append_line(material_viewer_rotate_point(make_float3(-radius, y, 0.f), yaw_deg, pitch_deg),
                material_viewer_rotate_point(make_float3(radius, y, 0.f), yaw_deg, pitch_deg),
                x_axis_color);
    append_line(material_viewer_rotate_point(make_float3(0.f, y, -radius), yaw_deg, pitch_deg),
                material_viewer_rotate_point(make_float3(0.f, y, radius), yaw_deg, pitch_deg),
                z_axis_color);
    return mesh;
}

MeshData build_direction_guides_mesh(const PlotRect &rect,
                                     uint2 window_size,
                                     float camera_yaw_deg,
                                     float camera_pitch_deg,
                                     float zoom,
                                     float sign,
                                     float wo_yaw_deg,
                                     float wo_pitch_deg) {
    MeshData mesh;
    mesh.rect = rect;
    mesh.primitive = GL_LINES;
    if (rect.width < 8u || rect.height < 8u) {
        return mesh;
    }

    const OrbitCamera camera = make_orbit_camera(rect, camera_yaw_deg, camera_pitch_deg, zoom);
    const float3 normal_dir = material_viewer_rotate_point(make_float3(0.f, sign, 0.f), camera_yaw_deg, camera_pitch_deg);
    const float3 wo_dir = material_viewer_rotate_point(material_viewer_direction_from_angles(wo_yaw_deg, wo_pitch_deg), camera_yaw_deg, camera_pitch_deg);
    const float3 normal_color = make_float3(94.f / 255.f, 214.f / 255.f, 118.f / 255.f);
    const float3 view_color = make_float3(250.f / 255.f, 132.f / 255.f, 108.f / 255.f);

    auto append_line = [&](float3 a, float3 b, float3 color) {
        float2 a_ndc{};
        float2 b_ndc{};
        float a_depth = 0.f;
        float b_depth = 0.f;
        if (!project_world_point(a, camera, window_size, &a_ndc, &a_depth) ||
            !project_world_point(b, camera, window_size, &b_ndc, &b_depth)) {
            return;
        }
        uint32_t base = static_cast<uint32_t>(mesh.vertices.size());
        mesh.vertices.emplace_back(MeshVertex{a_ndc.x, a_ndc.y, a_depth, color.x, color.y, color.z, 1.f});
        mesh.vertices.emplace_back(MeshVertex{b_ndc.x, b_ndc.y, b_depth, color.x, color.y, color.z, 1.f});
        mesh.indices.emplace_back(base);
        mesh.indices.emplace_back(base + 1u);
    };

    auto append_arrow = [&](float3 direction, float length, float3 color) {
        float3 dir = normalize(direction);
        float3 end = dir * length;
        append_line(make_float3(0.f), end, color);

        float3 side = normalize(cross(dir, make_float3(0.f, 0.f, 1.f)));
        if (!std::isfinite(side.x) || !std::isfinite(side.y) || !std::isfinite(side.z) || length_squared(side) < 1e-6f) {
            side = make_float3(1.f, 0.f, 0.f);
        }
        float3 back = end - dir * (length * 0.18f);
        float3 wing = side * (length * 0.08f);
        append_line(back + wing, end, color);
        append_line(back - wing, end, color);
    };

    append_arrow(normal_dir, 1.0f, normal_color);
    append_arrow(wo_dir, 0.95f, view_color);
    return mesh;
}

GLuint compile_shader(GLenum type, const char *source) {
    GLuint shader = glCreateShader(type);
    if (shader == 0u) {
        OC_WARNING("Failed to create OpenGL shader object for vision-material-viewer.");
        return 0u;
    }
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);
    GLint compiled = GL_FALSE;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &compiled);
    if (compiled != GL_TRUE) {
        GLint log_length = 0;
        glGetShaderiv(shader, GL_INFO_LOG_LENGTH, &log_length);
        std::vector<char> log(static_cast<size_t>(std::max(1, log_length)), '\0');
        glGetShaderInfoLog(shader, log_length, nullptr, log.data());
        OC_WARNING_FORMAT("Failed to compile OpenGL shader: {}", log.data());
        glDeleteShader(shader);
        return 0u;
    }
    return shader;
}

GLuint link_program() {
    static constexpr const char *kVertexShader = R"glsl(
        #version 330 core
        layout(location = 0) in vec3 in_position;
        layout(location = 1) in vec4 in_color;
        out vec4 v_color;
        void main() {
            gl_Position = vec4(in_position, 1.0);
            v_color = in_color;
        }
    )glsl";
    static constexpr const char *kFragmentShader = R"glsl(
        #version 330 core
        in vec4 v_color;
        out vec4 out_color;
        void main() {
            out_color = v_color;
        }
    )glsl";

    GLuint vs = compile_shader(GL_VERTEX_SHADER, kVertexShader);
    GLuint fs = compile_shader(GL_FRAGMENT_SHADER, kFragmentShader);
    if (vs == 0u || fs == 0u) {
        if (vs != 0u) {
            glDeleteShader(vs);
        }
        if (fs != 0u) {
            glDeleteShader(fs);
        }
        return 0u;
    }
    GLuint program = glCreateProgram();
    if (program == 0u) {
        OC_WARNING("Failed to create OpenGL program for vision-material-viewer.");
        glDeleteShader(vs);
        glDeleteShader(fs);
        return 0u;
    }
    glAttachShader(program, vs);
    glAttachShader(program, fs);
    glLinkProgram(program);
    glDeleteShader(vs);
    glDeleteShader(fs);

    GLint linked = GL_FALSE;
    glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (linked != GL_TRUE) {
        GLint log_length = 0;
        glGetProgramiv(program, GL_INFO_LOG_LENGTH, &log_length);
        std::vector<char> log(static_cast<size_t>(std::max(1, log_length)), '\0');
        glGetProgramInfoLog(program, log_length, nullptr, log.data());
        OC_WARNING_FORMAT("Failed to link OpenGL program: {}", log.data());
        glDeleteProgram(program);
        return 0u;
    }
    return program;
}

void clear_panel(const PlotRect &rect, uint2 window_size, float3 color) {
    glEnable(GL_SCISSOR_TEST);
    glScissor(static_cast<GLint>(rect.x),
              static_cast<GLint>(window_size.y - (rect.y + rect.height)),
              static_cast<GLsizei>(rect.width),
              static_cast<GLsizei>(rect.height));
    glClearColor(color.x, color.y, color.z, 1.f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glDisable(GL_SCISSOR_TEST);
}

}// namespace

namespace vision {

struct MaterialViewerGLRenderer::Impl {
    bool glad_ready_{false};
    bool init_failed_{false};
    bool init_logged_{false};
    bool mesh_logged_{false};
    GLuint program_{0u};
    GLuint vao_{0u};
    GLuint vbo_{0u};
    GLuint ebo_{0u};
    uint2 window_size_{};
    MeshData reflection_plane_{};
    MeshData reflection_plane_wire_{};
    MeshData transmission_plane_{};
    MeshData transmission_plane_wire_{};
    MeshData reflection_guides_{};
    MeshData transmission_guides_{};
    MeshData reflection_{};
    MeshData transmission_{};

    void ensure_initialized() noexcept {
        if (init_failed_) {
            return;
        }
        if (!glad_ready_) {
            if (!gladLoadGL()) {
                OC_WARNING("vision-material-viewer failed to initialize GLAD in application module; 3D view will be skipped.");
                init_failed_ = true;
                return;
            }
            glad_ready_ = true;
            OC_INFO("vision-material-viewer GL renderer initialized GLAD in application module.");
        }
        if (program_ != 0u) {
            return;
        }
        program_ = link_program();
        if (program_ == 0u) {
            OC_WARNING("vision-material-viewer GL program initialization failed; 3D view will be skipped.");
            init_failed_ = true;
            return;
        }
        OC_INFO("vision-material-viewer GL program linked.");
        glGenVertexArrays(1, &vao_);
        glGenBuffers(1, &vbo_);
        glGenBuffers(1, &ebo_);
        glBindVertexArray(vao_);
        glBindBuffer(GL_ARRAY_BUFFER, vbo_);
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo_);
        glEnableVertexAttribArray(0u);
        glVertexAttribPointer(0u, 3, GL_FLOAT, GL_FALSE, sizeof(MeshVertex), reinterpret_cast<void *>(offsetof(MeshVertex, x)));
        glEnableVertexAttribArray(1u);
        glVertexAttribPointer(1u, 4, GL_FLOAT, GL_FALSE, sizeof(MeshVertex), reinterpret_cast<void *>(offsetof(MeshVertex, r)));
        glBindVertexArray(0u);
    }

    void destroy() noexcept {
        if (ebo_ != 0u) {
            glDeleteBuffers(1, &ebo_);
            ebo_ = 0u;
        }
        if (vbo_ != 0u) {
            glDeleteBuffers(1, &vbo_);
            vbo_ = 0u;
        }
        if (vao_ != 0u) {
            glDeleteVertexArrays(1, &vao_);
            vao_ = 0u;
        }
        if (program_ != 0u) {
            glDeleteProgram(program_);
            program_ = 0u;
        }
        glad_ready_ = false;
        init_failed_ = false;
        init_logged_ = false;
        mesh_logged_ = false;
    }

    void draw_mesh(const MeshData &mesh, bool transparent, bool depth_test = true) noexcept {
        if (mesh.vertices.empty() || mesh.indices.empty()) {
            return;
        }

        if (transparent) {
            glEnable(GL_BLEND);
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
            glDepthMask(GL_FALSE);
        } else {
            glDisable(GL_BLEND);
            glDepthMask(GL_TRUE);
        }
        if (depth_test) {
            glEnable(GL_DEPTH_TEST);
            glDepthFunc(GL_LEQUAL);
        } else {
            glDisable(GL_DEPTH_TEST);
        }
        glDisable(GL_CULL_FACE);
        glUseProgram(program_);
        glBindVertexArray(vao_);
        glBindBuffer(GL_ARRAY_BUFFER, vbo_);
        glBufferData(GL_ARRAY_BUFFER,
                     static_cast<GLsizeiptr>(mesh.vertices.size() * sizeof(MeshVertex)),
                     mesh.vertices.data(),
                     GL_DYNAMIC_DRAW);
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo_);
        glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                     static_cast<GLsizeiptr>(mesh.indices.size() * sizeof(uint32_t)),
                     mesh.indices.data(),
                     GL_DYNAMIC_DRAW);
        glDrawElements(mesh.primitive, static_cast<GLsizei>(mesh.indices.size()), GL_UNSIGNED_INT, nullptr);
        if (transparent) {
            glDisable(GL_BLEND);
            glDepthMask(GL_TRUE);
        }
    }

    void draw_panel(const MeshData &plane, const MeshData &plane_wire, const MeshData &guides, const MeshData &surface, bool clear_background = true) noexcept {
        if (surface.rect.width == 0u || surface.rect.height == 0u) {
            return;
        }
        if (clear_background) {
            clear_panel(surface.rect, window_size_, make_float3(0.055f, 0.071f, 0.094f));
        }
        draw_mesh(plane, true);
        draw_mesh(surface, false);
        draw_mesh(plane_wire, false, false);
        draw_mesh(guides, false, false);
    }
};

MaterialViewerGLRenderer::MaterialViewerGLRenderer()
    : impl_(std::make_unique<Impl>()) {}

MaterialViewerGLRenderer::~MaterialViewerGLRenderer() {
    shutdown();
}

void MaterialViewerGLRenderer::initialize() noexcept {
    impl_->ensure_initialized();
}

bool MaterialViewerGLRenderer::is_available() const noexcept {
    return impl_ && impl_->glad_ready_ && impl_->program_ != 0u && !impl_->init_failed_;
}

void MaterialViewerGLRenderer::shutdown() noexcept {
    if (impl_) {
        impl_->destroy();
    }
}

void MaterialViewerGLRenderer::update_meshes(const PreviewData &preview,
                                             const ViewerState &state,
                                             uint2 window_size) noexcept {
    impl_->window_size_ = window_size;
    if (state.display_mode != static_cast<int>(DisplayMode::ThreeD)) {
        impl_->reflection_plane_ = {};
        impl_->reflection_plane_wire_ = {};
        impl_->transmission_plane_ = {};
        impl_->transmission_plane_wire_ = {};
        impl_->reflection_guides_ = {};
        impl_->transmission_guides_ = {};
        impl_->reflection_ = {};
        impl_->transmission_ = {};
        impl_->mesh_logged_ = false;
        return;
    }

    const PlotColumns columns = compute_plot_columns(window_size);
    const PlotRect combined_rect = make_full_height_plot_rect(columns.plot_x0, columns.plot_width, window_size);
    const PlotRect left_rect = combined_rect;
    const PlotRect right_rect = combined_rect;
    const float shared_scale = std::max(preview.reflection_max, preview.transmission_max);
    const float left_scale = state.scale_mode == static_cast<int>(ScaleMode::Shared) ? shared_scale : preview.reflection_max;
    const float right_scale = state.scale_mode == static_cast<int>(ScaleMode::Shared) ? shared_scale : preview.transmission_max;

    if (state.show_slice_plane) {
        impl_->reflection_plane_ = build_slice_plane_mesh(left_rect,
                                                          window_size,
                                                          state.lobe_view_yaw_deg,
                                                          state.lobe_view_pitch_deg,
                                                          state.lobe_view_zoom,
                                                          state.slice_plane_height,
                                                          0.22f);
        impl_->reflection_plane_wire_ = build_slice_plane_wire_mesh(left_rect,
                                                                    window_size,
                                                                    state.lobe_view_yaw_deg,
                                                                    state.lobe_view_pitch_deg,
                                                                    state.lobe_view_zoom,
                                                                    state.slice_plane_height);
        impl_->transmission_plane_ = build_slice_plane_mesh(right_rect,
                                                            window_size,
                                                            state.lobe_view_yaw_deg,
                                                            state.lobe_view_pitch_deg,
                                                            state.lobe_view_zoom,
                                                            state.slice_plane_height,
                                                            0.22f);
        impl_->transmission_plane_wire_ = build_slice_plane_wire_mesh(right_rect,
                                                                      window_size,
                                                                      state.lobe_view_yaw_deg,
                                                                      state.lobe_view_pitch_deg,
                                                                      state.lobe_view_zoom,
                                                                      state.slice_plane_height);
        impl_->transmission_plane_ = {};
        impl_->transmission_plane_wire_ = {};
    } else {
        impl_->reflection_plane_ = {};
        impl_->reflection_plane_wire_ = {};
        impl_->transmission_plane_ = {};
        impl_->transmission_plane_wire_ = {};
    }

    impl_->reflection_guides_ = build_direction_guides_mesh(left_rect,
                                                            window_size,
                                                            state.lobe_view_yaw_deg,
                                                            state.lobe_view_pitch_deg,
                                                            state.lobe_view_zoom,
                                                            1.f,
                                                            state.yaw_deg,
                                                            state.pitch_deg);
    impl_->transmission_guides_ = build_direction_guides_mesh(right_rect,
                                                              window_size,
                                                              state.lobe_view_yaw_deg,
                                                              state.lobe_view_pitch_deg,
                                                              state.lobe_view_zoom,
                                                              -1.f,
                                                              state.yaw_deg,
                                                              state.pitch_deg);

    impl_->reflection_ = build_lobe_mesh(preview.reflection,
                                         preview.resolution,
                                         left_rect,
                                         window_size,
                                         left_scale,
                                         state.log_scale,
                                         1.f,
                                         state.lobe_height_scale,
                                         state.lobe_view_yaw_deg,
                                         state.lobe_view_pitch_deg,
                                         state.lobe_view_zoom,
                                         make_float3(228.f / 255.f, 191.f / 255.f, 78.f / 255.f));
    impl_->transmission_ = build_lobe_mesh(preview.transmission,
                                           preview.resolution,
                                           right_rect,
                                           window_size,
                                           right_scale,
                                           state.log_scale,
                                           -1.f,
                                           state.lobe_height_scale,
                                           state.lobe_view_yaw_deg,
                                           state.lobe_view_pitch_deg,
                                           state.lobe_view_zoom,
                                           make_float3(92.f / 255.f, 204.f / 255.f, 188.f / 255.f));
    if (!impl_->mesh_logged_) {
        impl_->mesh_logged_ = true;
        OC_INFO_FORMAT("vision-material-viewer 3D meshes ready: reflection vtx={}, transmission vtx={}",
                       impl_->reflection_.vertices.size(),
                       impl_->transmission_.vertices.size());
    }
}

void MaterialViewerGLRenderer::render() noexcept {
    impl_->ensure_initialized();
    if (!impl_->glad_ready_ || impl_->program_ == 0u) {
        return;
    }
    if (impl_->reflection_.rect.width == 0u && impl_->transmission_.rect.width == 0u) {
        return;
    }
    if (!impl_->init_logged_) {
        impl_->init_logged_ = true;
        OC_INFO("vision-material-viewer entering GL 3D draw.");
    }
    bool cleared = false;
    if (impl_->reflection_.rect.width != 0u && impl_->reflection_.rect.height != 0u) {
        impl_->draw_panel(impl_->reflection_plane_, impl_->reflection_plane_wire_, impl_->reflection_guides_, impl_->reflection_, !cleared);
        cleared = true;
    }
    if (impl_->transmission_.rect.width != 0u && impl_->transmission_.rect.height != 0u) {
        impl_->draw_panel(impl_->transmission_plane_, impl_->transmission_plane_wire_, impl_->transmission_guides_, impl_->transmission_, !cleared);
    }
}

}// namespace vision