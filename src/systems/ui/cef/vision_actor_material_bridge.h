#pragma once

#include <array>
#include <string>
#include <string_view>

#include <nlohmann/json_fwd.hpp>

namespace Corona::Systems::UI {

struct VisionActorMaterialState {
    std::array<float, 3> diffuse{0.8f, 0.8f, 0.8f};
    float metallic{0.0f};
    float roughness{0.5f};
};

[[nodiscard]] std::string bind_vision_actor_material(
    nlohmann::json& scene_data,
    nlohmann::json& shape,
    std::string_view actor_identity,
    const VisionActorMaterialState& state);

[[nodiscard]] bool ensure_native_actor_model_normalization(
    nlohmann::json& shape,
    bool native_origin = false);

}  // namespace Corona::Systems::UI
