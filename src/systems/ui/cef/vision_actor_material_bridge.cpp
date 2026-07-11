#include "vision_actor_material_bridge.h"

#include <algorithm>
#include <cmath>

#include <nlohmann/json.hpp>

namespace Corona::Systems::UI {
namespace {

float finite_clamp(float value, float fallback, float low, float high) {
    return std::clamp(std::isfinite(value) ? value : fallback, low, high);
}

nlohmann::json make_material(std::string_view name,
                             const VisionActorMaterialState& state) {
    const nlohmann::json color = nlohmann::json::array({
        finite_clamp(state.diffuse[0], 0.8f, 0.0f, 1.0f),
        finite_clamp(state.diffuse[1], 0.8f, 0.0f, 1.0f),
        finite_clamp(state.diffuse[2], 0.8f, 0.0f, 1.0f),
    });
    return {
        {"type", "principled_bsdf"},
        {"name", std::string(name)},
        {"param",
         {
             {"color", color},
             {"metallic", finite_clamp(state.metallic, 0.0f, 0.0f, 1.0f)},
             {"roughness", finite_clamp(state.roughness, 0.5f, 0.0001f, 1.0f)},
         }},
    };
}

}  // namespace

std::string bind_vision_actor_material(nlohmann::json& scene_data,
                                       nlohmann::json& shape,
                                       std::string_view actor_identity,
                                       const VisionActorMaterialState& state) {
    const std::string identity = actor_identity.empty() ? "unnamed" : std::string(actor_identity);
    const std::string material_name = "corona_actor_material_" + identity;
    auto material = make_material(material_name, state);

    auto& materials = scene_data["materials"];
    if (!materials.is_array()) {
        materials = nlohmann::json::array();
    }
    const auto existing = std::find_if(materials.begin(), materials.end(), [&](const auto& item) {
        return item.is_object() && item.value("name", std::string{}) == material_name;
    });
    if (existing == materials.end()) {
        materials.push_back(std::move(material));
    } else {
        *existing = std::move(material);
    }

    auto& params = shape["param"];
    if (!params.is_object()) {
        params = nlohmann::json::object();
    }
    params["material"] = material_name;
    return material_name;
}

}  // namespace Corona::Systems::UI
