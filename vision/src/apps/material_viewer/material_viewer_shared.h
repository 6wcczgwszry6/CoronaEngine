#pragma once

#include "math/util.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <vector>

namespace vision {

inline constexpr ocarina::uint2 kWindowSize = ocarina::make_uint2(1680u, 980u);
inline constexpr ocarina::uint kSidebarWidth = 320u;
inline constexpr ocarina::uint kPanelGap = 12u;
inline constexpr ocarina::uint kOuterMargin = 12u;
inline constexpr ocarina::uint kDefaultPreviewResolution = 160u;
inline constexpr float kPi = 3.14159265358979323846f;
inline constexpr float kTwoPi = 6.28318530717958647692f;
inline constexpr float kRadPerDegree = kPi / 180.f;

enum class MaterialKind : int {
    Diffuse = 0,
    Mirror,
    Glass,
    Metal,
    Metallic,
    Plastic,
    Substrate,
    Principled,
    Count
};

enum class QuantityMode : int {
    F = 0,
    FCos = 1
};

enum class ScaleMode : int {
    Shared = 0,
    Independent = 1
};

enum class DisplayMode : int {
    TwoD = 0,
    ThreeD = 1
};

enum class RenderBackend : int {
    CPU = 0,
    GL = 1
};

struct MaterialPreset {
    const char *label;
    const char *summary;
    const char *json;
};

inline constexpr std::array<MaterialPreset, static_cast<size_t>(MaterialKind::Count)> kMaterialPresets = {{
    {
        "diffuse",
        "Diffuse | Reflection | Broad lobe",
        R"json(
{
    "type": "diffuse",
    "name": "MatDiffuse",
    "param": {
        "color": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "sigma": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}}
    },
    "node_tab": {}
}
)json"
    },
    {
        "mirror",
        "Specular/Glossy | Reflection",
        R"json(
{
    "type": "mirror",
    "name": "MatMirror",
    "param": {
        "color": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "roughness": {"channels": "x", "node": {"type": "number", "param": {"value": 0.14}}},
        "anisotropic": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "remapping_roughness": false
    },
    "node_tab": {}
}
)json"
    },
    {
        "glass",
        "Glossy | Reflection + Transmission",
        R"json(
{
    "type": "glass",
    "name": "MatGlass",
    "param": {
        "color": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "ior": {"channels": "x", "node": {"type": "number", "param": {"value": 1.5}}},
        "roughness": {"channels": "x", "node": {"type": "number", "param": {"value": 0.14}}},
        "anisotropic": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "remapping_roughness": false
    },
    "node_tab": {}
}
)json"
    },
    {
        "metal",
        "Glossy conductor | Reflection",
        R"json(
{
    "type": "metal",
    "name": "MatMetal",
    "param": {
        "material_name": "Cu",
        "roughness": {"channels": "x", "node": {"type": "number", "param": {"value": 0.14}}},
        "anisotropic": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "remapping_roughness": false
    },
    "node_tab": {}
}
)json"
    },
    {
        "metallic",
        "Metallic BRDF | Reflection",
        R"json(
{
    "type": "metallic",
    "name": "MatMetallic",
    "param": {
        "color": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "edge_tint": {"channels": "xyz", "node": {"type": "number", "param": {"value": [0.9, 0.85, 0.8]}}},
        "roughness": {"channels": "x", "node": {"type": "number", "param": {"value": 0.14}}},
        "anisotropic": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "remapping_roughness": false
    },
    "node_tab": {}
}
)json"
    },
    {
        "plastic",
        "Diffuse + glossy coat | Reflection",
        R"json(
{
    "type": "plastic",
    "name": "MatPlastic",
    "param": {
        "color": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "ior": {"channels": "x", "node": {"type": "number", "param": {"value": 1.5}}},
        "roughness": {"channels": "x", "node": {"type": "number", "param": {"value": 0.12}}},
        "anisotropic": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "sigma_a": {"channels": "xyz", "node": {"type": "number", "param": {"value": [0.0, 0.0, 0.0]}}},
        "thickness": {"channels": "x", "node": {"type": "number", "param": {"value": 1.0}}},
        "remapping_roughness": true
    },
    "node_tab": {}
}
)json"
    },
    {
        "substrate",
        "Diffuse + specular substrate | Reflection",
        R"json(
{
    "type": "substrate",
    "name": "MatSubstrate",
    "param": {
        "color": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "spec": {"channels": "xyz", "node": {"type": "number", "param": {"value": [0.05, 0.05, 0.05]}}},
        "roughness": {"channels": "x", "node": {"type": "number", "param": {"value": 0.5}}},
        "anisotropic": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "remapping_roughness": false
    },
    "node_tab": {}
}
)json"
    },
    {
        "principled_bsdf",
        "Principled mix | Diffuse/specular/coat/transmission toggles",
        R"json(
{
    "type": "principled_bsdf",
    "name": "MatPrincipledBSDF",
    "param": {
        "color": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "metallic": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "ior": {"channels": "x", "node": {"type": "number", "param": {"value": 1.5}}},
        "roughness": {"channels": "x", "node": {"type": "number", "param": {"value": 0.3}}},
        "spec_tint": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "anisotropic": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "opacity": {"channels": "x", "node": {"type": "number", "param": {"value": 1.0}}},
        "sheen_weight": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "sheen_roughness": {"channels": "x", "node": {"type": "number", "param": {"value": 0.5}}},
        "sheen_tint": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "coat_weight": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "coat_roughness": {"channels": "x", "node": {"type": "number", "param": {"value": 0.2}}},
        "coat_ior": {"channels": "x", "node": {"type": "number", "param": {"value": 1.5}}},
        "coat_tint": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "subsurface_weight": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}},
        "subsurface_radius": {"channels": "xyz", "node": {"type": "number", "param": {"value": [1.0, 1.0, 1.0]}}},
        "subsurface_scale": {"channels": "x", "node": {"type": "number", "param": {"value": 0.2}}},
        "transmission_weight": {"channels": "x", "node": {"type": "number", "param": {"value": 0.0}}}
    },
    "node_tab": {}
}
)json"
    }
}};

inline constexpr std::array<const char *, 2> kQuantityModeNames = {"f", "f*cos(theta_i)"};
inline constexpr std::array<const char *, 2> kScaleModeNames = {"shared", "independent"};
inline constexpr std::array<const char *, 3> kPreviewResolutionNames = {"128", "160", "224"};
inline constexpr std::array<ocarina::uint, 3> kPreviewResolutions = {128u, 160u, 224u};
inline constexpr std::array<const char *, 6> kPresetSampleNames = {"64", "256", "1k", "4k", "16k", "custom"};
inline constexpr std::array<ocarina::uint, 6> kPreviewPresetSamples = {1u, 4u, 16u, 64u, 256u, 0u};
inline constexpr std::array<ocarina::uint, 6> kIntegralPresetSamples = {64u, 256u, 1024u, 4096u, 16384u, 0u};

struct PlotRect {
    ocarina::uint x{};
    ocarina::uint y{};
    ocarina::uint width{};
    ocarina::uint height{};
};

struct PlotColumns {
    ocarina::uint plot_x0{};
    ocarina::uint plot_width{};
    ocarina::uint column_width{};
    ocarina::uint left_x{};
    ocarina::uint right_x{};
};

[[nodiscard]] inline PlotColumns compute_plot_columns(ocarina::uint2 image_size) noexcept {
    PlotColumns layout;
    layout.plot_x0 = kSidebarWidth + kOuterMargin;
    layout.plot_width = image_size.x > layout.plot_x0 + kOuterMargin ? image_size.x - layout.plot_x0 - kOuterMargin : 1u;
    layout.column_width = layout.plot_width > kPanelGap ? (layout.plot_width - kPanelGap) / 2u : 1u;
    layout.left_x = layout.plot_x0;
    layout.right_x = layout.plot_x0 + layout.column_width + kPanelGap;
    return layout;
}

[[nodiscard]] inline PlotRect make_full_height_plot_rect(ocarina::uint x, ocarina::uint width, ocarina::uint2 image_size) noexcept {
    return PlotRect{x, kOuterMargin, width, image_size.y > 2u * kOuterMargin ? image_size.y - 2u * kOuterMargin : 1u};
}

struct ViewerProjector {
    ocarina::float2 center{};
    float base_scale{};
    float view_distance{};
};

inline constexpr float kViewer3DCenterYRatio = 0.55f;
inline constexpr float kViewer3DBaseScaleFactor = 0.78f;
inline constexpr float kViewer3DViewDistance = 2.6f;
inline constexpr float kViewer3DMinPerspectiveDistance = 0.25f;
inline constexpr float kViewer3DNearPlane = 0.1f;
inline constexpr float kViewer3DFarPlane = 8.f;

[[nodiscard]] inline ocarina::float3 material_viewer_direction_from_disk(ocarina::float2 disk, float sign) noexcept {
    float radius2 = ocarina::dot(disk, disk);
    if (radius2 > 1.f) {
        return ocarina::make_float3(0.f, sign, 0.f);
    }
    float y = std::sqrt(std::max(0.f, 1.f - radius2));
    return ocarina::normalize(ocarina::make_float3(disk.x, sign * y, disk.y));
}

[[nodiscard]] inline ocarina::float3 material_viewer_direction_from_angles(float yaw_deg, float pitch_deg) noexcept {
    float yaw = yaw_deg * kRadPerDegree;
    float pitch = pitch_deg * kRadPerDegree;
    float cp = std::cos(pitch);
    float sp = std::sin(pitch);
    float sy = std::sin(yaw);
    float cy = std::cos(yaw);
    return ocarina::normalize(ocarina::make_float3(cp * sy, sp, cp * cy));
}

[[nodiscard]] inline ocarina::float3 material_viewer_rotate_point(ocarina::float3 point, float yaw_deg, float pitch_deg) noexcept {
    float yaw = yaw_deg * kRadPerDegree;
    float pitch = pitch_deg * kRadPerDegree;
    float cy = std::cos(yaw);
    float sy = std::sin(yaw);
    float cp = std::cos(pitch);
    float sp = std::sin(pitch);
    ocarina::float3 yaw_rotated = ocarina::make_float3(cy * point.x + sy * point.z,
                                                       point.y,
                                                       -sy * point.x + cy * point.z);
    return ocarina::make_float3(yaw_rotated.x,
                                cp * yaw_rotated.y - sp * yaw_rotated.z,
                                sp * yaw_rotated.y + cp * yaw_rotated.z);
}

[[nodiscard]] inline ViewerProjector make_material_viewer_projector(const PlotRect &rect, float zoom) noexcept {
    ViewerProjector projector;
    projector.center = ocarina::make_float2(static_cast<float>(rect.x) + static_cast<float>(rect.width) * 0.5f,
                                            static_cast<float>(rect.y) + static_cast<float>(rect.height) * kViewer3DCenterYRatio);
    projector.base_scale = static_cast<float>(std::min(rect.width, rect.height)) *
                           kViewer3DBaseScaleFactor * std::max(0.2f, zoom);
    projector.view_distance = kViewer3DViewDistance;
    return projector;
}

[[nodiscard]] inline float material_viewer_camera_depth(const ViewerProjector &projector, float rotated_z) noexcept {
    return projector.view_distance - rotated_z;
}

[[nodiscard]] inline float material_viewer_perspective(const ViewerProjector &projector, float rotated_z) noexcept {
    return projector.base_scale / std::max(kViewer3DMinPerspectiveDistance,
                                           material_viewer_camera_depth(projector, rotated_z));
}

[[nodiscard]] inline ocarina::float2 material_viewer_project_screen(const ViewerProjector &projector, ocarina::float3 rotated_point) noexcept {
    float perspective = material_viewer_perspective(projector, rotated_point.z);
    return ocarina::make_float2(projector.center.x + rotated_point.x * perspective,
                                projector.center.y - rotated_point.y * perspective);
}

[[nodiscard]] inline bool material_viewer_is_visible(const ViewerProjector &projector, ocarina::float3 rotated_point) noexcept {
    return material_viewer_camera_depth(projector, rotated_point.z) > kViewer3DNearPlane;
}

[[nodiscard]] inline float material_viewer_ndc_depth(const ViewerProjector &projector, ocarina::float3 rotated_point) noexcept {
    float cam_depth = material_viewer_camera_depth(projector, rotated_point.z);
    return std::clamp((cam_depth - kViewer3DNearPlane) / (kViewer3DFarPlane - kViewer3DNearPlane) * 2.f - 1.f,
                      -0.98f,
                      0.98f);
}

[[nodiscard]] inline ocarina::float2 material_viewer_screen_to_ndc(ocarina::uint2 window_size, ocarina::float2 screen) noexcept {
    float width = std::max(1.f, static_cast<float>(window_size.x));
    float height = std::max(1.f, static_cast<float>(window_size.y));
    return ocarina::make_float2(screen.x / width * 2.f - 1.f,
                                1.f - screen.y / height * 2.f);
}

struct ViewerState {
    int current_material{0};
    int quantity_mode{static_cast<int>(QuantityMode::FCos)};
    int scale_mode{static_cast<int>(ScaleMode::Shared)};
    int display_mode{static_cast<int>(DisplayMode::ThreeD)};
    int render_backend{static_cast<int>(RenderBackend::GL)};
    int preview_resolution{1};
    int preview_sample_preset{2};
    int integral_sample_preset{3};
    ocarina::uint preview_sample_custom{16u};
    ocarina::uint integral_sample_custom{4096u};
    float yaw_deg{0.f};
    float pitch_deg{35.f};
    float lobe_view_yaw_deg{-35.f};
    float lobe_view_pitch_deg{25.f};
    float lobe_view_zoom{1.15f};
    float lobe_height_scale{1.f};
    float slice_plane_height{0.f};
    float last_cursor_x{0.f};
    float last_cursor_y{0.f};
    bool show_slice_plane{true};
    bool camera_dragging{false};
    bool slice_plane_dragging{false};
    bool log_scale{true};
    bool integral_dirty{true};
    bool preview_dirty{true};
    bool background_dirty{true};
    bool integral_ready{false};
    bool material_data_dirty{false};
    bool material_reset_requested{false};
    bool keep_running{true};
};

struct PreviewData {
    ocarina::uint resolution{kDefaultPreviewResolution};
    std::vector<float> reflection{};
    std::vector<float> transmission{};
    float reflection_max{1.f};
    float transmission_max{1.f};
};

struct IntegralData {
    ocarina::float3 reflection{ocarina::make_float3(0.f)};
    ocarina::float3 transmission{ocarina::make_float3(0.f)};
    bool ready{false};
};

}// namespace vision