#pragma once

#include <array>

#include <nlohmann/json_fwd.hpp>

namespace Corona::Systems::UI {

struct VisionActorTransformState {
    std::array<float, 3> position{0.0f, 0.0f, 0.0f};
    std::array<float, 3> rotation{0.0f, 0.0f, 0.0f};
    std::array<float, 3> scale{1.0f, 1.0f, 1.0f};
    bool valid{false};
    bool lossy{false};
};

[[nodiscard]] VisionActorTransformState decode_vision_actor_transform(
    const nlohmann::json& transform);

[[nodiscard]] nlohmann::json encode_vision_actor_transform(
    const VisionActorTransformState& state);

}  // namespace Corona::Systems::UI
