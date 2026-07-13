#pragma once

#include <corona/math/frustum.h>
#include <corona/spatial/aabb.h>
#include <ktm/ktm.h>

#include <algorithm>
#include <array>
#include <cmath>

namespace Corona::Systems::OpticsDetail {

struct ShadowCascadeView {
    ktm::fmat4x4 light_view_proj{ktm::fmat4x4::from_eye()};
    Math::Frustum frustum{};
    float orthographic_width = 0.0f;
    float orthographic_height = 0.0f;
    float world_units_per_texel = 0.0f;
};

[[nodiscard]] inline ShadowCascadeView make_shadow_cascade_view(
    const ktm::fmat4x4& light_view_proj,
    float orthographic_width,
    float orthographic_height,
    float shadow_map_size) noexcept {
    ShadowCascadeView result;
    result.light_view_proj = light_view_proj;
    result.frustum = Math::Frustum::from_view_proj(light_view_proj);
    result.orthographic_width = orthographic_width;
    result.orthographic_height = orthographic_height;
    const float extent = std::max(orthographic_width, orthographic_height);
    result.world_units_per_texel = (extent > 0.0f && shadow_map_size > 0.0f)
        ? extent / shadow_map_size : 0.0f;
    return result;
}

[[nodiscard]] inline bool shadow_caster_visible(
    const Math::Frustum& frustum, const Spatial::AABB& world_bounds,
    bool bounds_valid = true) noexcept {
    if (!bounds_valid || !std::isfinite(world_bounds.min.x) ||
        !std::isfinite(world_bounds.min.y) || !std::isfinite(world_bounds.min.z) ||
        !std::isfinite(world_bounds.max.x) || !std::isfinite(world_bounds.max.y) ||
        !std::isfinite(world_bounds.max.z) ||
        world_bounds.min.x > world_bounds.max.x ||
        world_bounds.min.y > world_bounds.max.y ||
        world_bounds.min.z > world_bounds.max.z) {
        return true;
    }
    return frustum.intersects(world_bounds);
}

[[nodiscard]] inline int select_shadow_lod_level(
    const std::array<float, 8>& geometric_errors,
    int level_count, float max_abs_scale, float world_units_per_texel,
    int fallback_level) noexcept {
    if (level_count <= 0 || world_units_per_texel <= 0.0f ||
        !std::isfinite(world_units_per_texel)) return fallback_level;
    const float scale = std::max(std::abs(max_abs_scale), 1.0e-6f);
    int result = std::max(0, std::min(fallback_level, level_count - 1));
    for (int level = 0; level < level_count; ++level) {
        const float error = geometric_errors[static_cast<size_t>(level)] * scale;
        if (std::isfinite(error) && error <= world_units_per_texel) result = level;
    }
    return result;
}

}  // namespace Corona::Systems::OpticsDetail
