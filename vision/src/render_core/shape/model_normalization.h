#pragma once

#include <span>
#include <vector>

#include "math/geometry.h"

namespace vision {

struct ModelNormalizationResult {
    ocarina::float3 center{};
    float scale_factor{1.0f};
    bool valid{false};
};

[[nodiscard]] ModelNormalizationResult normalize_model_vertices_to_unit_bounds(
    std::span<std::vector<ocarina::Vertex>*> meshes,
    bool enabled);

}  // namespace vision
