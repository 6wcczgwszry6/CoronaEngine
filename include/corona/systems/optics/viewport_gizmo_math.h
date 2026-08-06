#pragma once

#include <ktm/ktm.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <optional>
#include <span>

namespace Corona {

enum class ViewportGizmoAxis : std::uint8_t {
    None,
    X,
    Y,
    Z,
};

struct ViewportGizmoWarpCalibration {
    float lenticular_pitch{19.1849f};
    float slant_angle_radians{0.2333f};
    float phase_offset{10.0f};
    float green_subpixel_offset{1.0f / 3.0f};
    float parallax_scale{19.1849f};
};

}  // namespace Corona

namespace Corona::Systems::OpticsDetail {

struct ViewportGizmoAxisLayout {
    ktm::fvec2 tip{};
    ktm::fvec2 direction{};
};

struct ViewportGizmoLayout {
    bool visible{false};
    ktm::fvec2 origin{};
    float clip_w{0.0f};
    std::array<ViewportGizmoAxisLayout, 3> axes{};
};

struct ViewportGizmoSpriteMetadata {
    ktm::fvec2 anchor{};
    ktm::fvec2 tip{};
};

inline constexpr std::array<ViewportGizmoSpriteMetadata, 3>
    kViewportGizmoSpriteMetadata{{
        {{363.7f, 500.2f}, {968.0f, 773.0f}},
        // axis_y.png now contains the former Z (green) sprite.
        {{808.3f, 511.1f}, {266.0f, 780.0f}},
        // axis_z.png now contains the former Y (blue) sprite.
        {{622.5f, 752.8f}, {622.0f, 224.0f}},
    }};

struct ViewportGizmoSpriteMask {
    std::span<const std::uint8_t> alpha{};
    std::uint32_t width{};
    std::uint32_t height{};
    ktm::fvec2 anchor{};
    ktm::fvec2 tip{};
};

namespace Detail {

[[nodiscard]] inline ktm::fvec4 transform_clip(const ktm::fmat4x4& matrix,
                                               const ktm::fvec3& point) {
    return {
        matrix[0][0] * point.x + matrix[1][0] * point.y +
            matrix[2][0] * point.z + matrix[3][0],
        matrix[0][1] * point.x + matrix[1][1] * point.y +
            matrix[2][1] * point.z + matrix[3][1],
        matrix[0][2] * point.x + matrix[1][2] * point.y +
            matrix[2][2] * point.z + matrix[3][2],
        matrix[0][3] * point.x + matrix[1][3] * point.y +
            matrix[2][3] * point.z + matrix[3][3],
    };
}

[[nodiscard]] inline std::optional<ktm::fvec2> project_pixel(
    const ktm::fmat4x4& view_projection,
    const ktm::fvec3& point,
    std::uint32_t width,
    std::uint32_t height,
    float* clip_w = nullptr,
    float* ndc_z = nullptr) {
    const auto clip = transform_clip(view_projection, point);
    if (clip_w) *clip_w = clip.w;
    if (!std::isfinite(clip.w) || std::abs(clip.w) < 1.0e-6f) {
        return std::nullopt;
    }
    const float x = clip.x / clip.w;
    const float y = clip.y / clip.w;
    const float z = clip.z / clip.w;
    if (ndc_z) *ndc_z = z;
    if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z)) {
        return std::nullopt;
    }
    return ktm::fvec2{
        (x * 0.5f + 0.5f) * static_cast<float>(width),
        (y * 0.5f + 0.5f) * static_cast<float>(height),
    };
}

[[nodiscard]] inline float point_segment_distance(ktm::fvec2 point,
                                                  ktm::fvec2 start,
                                                  ktm::fvec2 end) {
    const auto segment = end - start;
    const float length_sq = ktm::dot(segment, segment);
    if (length_sq <= 1.0e-6f) {
        return ktm::length(point - start);
    }
    const float t = std::clamp(ktm::dot(point - start, segment) / length_sq, 0.0f, 1.0f);
    return ktm::length(point - (start + segment * t));
}

}  // namespace Detail

[[nodiscard]] inline ViewportGizmoLayout make_viewport_gizmo_layout(
    const ktm::fmat4x4& view_projection,
    const ktm::fvec3& origin,
    std::uint32_t width,
    std::uint32_t height,
    float axis_length_pixels = 128.0f) {
    ViewportGizmoLayout layout;
    if (width == 0 || height == 0 || axis_length_pixels <= 0.0f) {
        return layout;
    }

    float clip_w = 0.0f;
    float ndc_z = 0.0f;
    const auto projected_origin =
        Detail::project_pixel(view_projection, origin, width, height, &clip_w, &ndc_z);
    if (!projected_origin || clip_w <= 0.0f || ndc_z < 0.0f || ndc_z > 1.0f) {
        return layout;
    }

    constexpr std::array<ktm::fvec3, 3> world_axes{{
        {1.0f, 0.0f, 0.0f},
        {0.0f, 1.0f, 0.0f},
        {0.0f, 0.0f, 1.0f},
    }};
    constexpr std::array<ktm::fvec2, 3> fallback_directions{{
        {1.0f, 0.0f},
        {0.0f, -1.0f},
        {-0.70710678f, 0.70710678f},
    }};

    layout.visible = true;
    layout.origin = *projected_origin;
    layout.clip_w = clip_w;
    for (std::size_t i = 0; i < world_axes.size(); ++i) {
        const auto projected_tip =
            Detail::project_pixel(view_projection, origin + world_axes[i], width, height);
        auto direction = projected_tip ? (*projected_tip - layout.origin) : fallback_directions[i];
        const float direction_length = ktm::length(direction);
        direction = direction_length > 1.0e-3f
                        ? direction / direction_length
                        : fallback_directions[i];
        layout.axes[i].direction = direction;
        layout.axes[i].tip = layout.origin + direction * axis_length_pixels;
    }
    return layout;
}

[[nodiscard]] inline ViewportGizmoAxis hit_test_viewport_gizmo(
    const ViewportGizmoLayout& layout,
    ktm::fvec2 point,
    float padding_pixels = 8.0f) {
    if (!layout.visible) {
        return ViewportGizmoAxis::None;
    }

    float nearest = padding_pixels + 6.0f;
    ViewportGizmoAxis result = ViewportGizmoAxis::None;
    constexpr std::array<ViewportGizmoAxis, 3> axes{
        ViewportGizmoAxis::X, ViewportGizmoAxis::Y, ViewportGizmoAxis::Z};
    for (std::size_t i = 0; i < axes.size(); ++i) {
        const float distance =
            Detail::point_segment_distance(point, layout.origin, layout.axes[i].tip);
        if (distance <= nearest) {
            nearest = distance;
            result = axes[i];
        }
    }
    return result;
}

[[nodiscard]] inline ViewportGizmoAxis hit_test_viewport_gizmo_alpha(
    const ViewportGizmoLayout& layout,
    ktm::fvec2 point,
    const std::array<ViewportGizmoSpriteMask, 3>& masks,
    float padding_pixels = 8.0f,
    float axis_length_pixels = 128.0f) {
    if (!layout.visible || axis_length_pixels <= 0.0f) {
        return ViewportGizmoAxis::None;
    }

    constexpr std::array<ViewportGizmoAxis, 3> axes{
        ViewportGizmoAxis::X, ViewportGizmoAxis::Y, ViewportGizmoAxis::Z};
    for (std::size_t i = 0; i < axes.size(); ++i) {
        const auto& mask = masks[i];
        if (mask.width == 0 || mask.height == 0 ||
            mask.alpha.size() < static_cast<std::size_t>(mask.width) * mask.height) {
            continue;
        }
        const auto source_axis = mask.tip - mask.anchor;
        const float source_length = ktm::length(source_axis);
        if (source_length <= 1.0e-4f) {
            continue;
        }
        const auto source_direction = source_axis / source_length;
        const ktm::fvec2 source_perpendicular{
            -source_direction.y, source_direction.x};
        const auto screen_direction = layout.axes[i].direction;
        const ktm::fvec2 screen_perpendicular{
            -screen_direction.y, screen_direction.x};
        const float scale = axis_length_pixels / source_length;
        const auto screen_relative = point - layout.origin;
        const auto source_pixel =
            mask.anchor +
            source_direction *
                (ktm::dot(screen_relative, screen_direction) / scale) +
            source_perpendicular *
                (ktm::dot(screen_relative, screen_perpendicular) / scale);
        const int radius =
            static_cast<int>(std::ceil(std::max(padding_pixels, 0.0f) / scale));
        const int center_x = static_cast<int>(std::floor(source_pixel.x + 0.5f));
        const int center_y = static_cast<int>(std::floor(source_pixel.y + 0.5f));
        for (int y = center_y - radius; y <= center_y + radius; ++y) {
            if (y < 0 || y >= static_cast<int>(mask.height)) continue;
            for (int x = center_x - radius; x <= center_x + radius; ++x) {
                if (x < 0 || x >= static_cast<int>(mask.width)) continue;
                const float dx = static_cast<float>(x - center_x) * scale;
                const float dy = static_cast<float>(y - center_y) * scale;
                if (dx * dx + dy * dy >
                    padding_pixels * padding_pixels + 0.25f) {
                    continue;
                }
                if (mask.alpha[static_cast<std::size_t>(y) * mask.width + x] > 2u) {
                    return axes[i];
                }
            }
        }
    }
    return ViewportGizmoAxis::None;
}

[[nodiscard]] inline ktm::fvec2 viewport_ui_prewarp_point(
    ktm::fvec2 displayed,
    const ViewportGizmoWarpCalibration& calibration) {
    const float pitch = std::max(std::abs(calibration.lenticular_pitch), 1.0e-5f);
    const float slant = std::tan(calibration.slant_angle_radians);
    const float phase =
        (displayed.x + calibration.green_subpixel_offset - slant * displayed.y) / pitch +
        calibration.phase_offset;
    const float gamma = 2.0f * (phase - std::floor(phase)) - 1.0f;
    displayed.x += gamma * calibration.parallax_scale;
    return displayed;
}

[[nodiscard]] inline std::optional<float> closest_axis_parameter(
    const ktm::fvec3& ray_origin,
    const ktm::fvec3& ray_direction,
    const ktm::fvec3& axis_origin,
    const ktm::fvec3& axis_direction) {
    const auto u = ktm::normalize(ray_direction);
    const auto v = ktm::normalize(axis_direction);
    const auto w = ray_origin - axis_origin;
    const float a = ktm::dot(u, u);
    const float b = ktm::dot(u, v);
    const float c = ktm::dot(v, v);
    const float d = ktm::dot(u, w);
    const float e = ktm::dot(v, w);
    const float denominator = a * c - b * b;
    if (!std::isfinite(denominator) || std::abs(denominator) < 1.0e-3f) {
        return std::nullopt;
    }
    const float parameter = (a * e - b * d) / denominator;
    return std::isfinite(parameter) ? std::optional<float>(parameter) : std::nullopt;
}

}  // namespace Corona::Systems::OpticsDetail
