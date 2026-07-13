#include "model_normalization.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace vision {

ModelNormalizationResult normalize_model_vertices_to_unit_bounds(
    std::span<std::vector<ocarina::Vertex>*> meshes,
    bool enabled) {
    ModelNormalizationResult result;
    if (!enabled) {
        return result;
    }

    auto minimum = ocarina::make_float3(std::numeric_limits<float>::max());
    auto maximum = ocarina::make_float3(std::numeric_limits<float>::lowest());
    bool has_vertex = false;
    for (const auto* mesh : meshes) {
        if (mesh == nullptr) {
            continue;
        }
        for (const auto& vertex : *mesh) {
            const auto position = vertex.position();
            if (!std::isfinite(position.x) || !std::isfinite(position.y) ||
                !std::isfinite(position.z)) {
                return result;
            }
            minimum = ocarina::min(minimum, position);
            maximum = ocarina::max(maximum, position);
            has_vertex = true;
        }
    }
    if (!has_vertex) {
        return result;
    }

    const auto extent = maximum - minimum;
    const float maximum_extent = std::max({extent.x, extent.y, extent.z});
    if (!std::isfinite(maximum_extent) || maximum_extent <= 1.0e-8f) {
        return result;
    }

    result.center = (minimum + maximum) * 0.5f;
    result.scale_factor = 1.0f / maximum_extent;
    result.valid = true;
    for (auto* mesh : meshes) {
        if (mesh == nullptr) {
            continue;
        }
        for (auto& vertex : *mesh) {
            vertex.set_position((vertex.position() - result.center) * result.scale_factor);
        }
    }
    return result;
}

}  // namespace vision
