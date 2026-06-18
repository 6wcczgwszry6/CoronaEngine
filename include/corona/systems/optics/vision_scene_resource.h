#pragma once

#include <corona/systems/optics/vision_pipeline_key.h>

#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>
#include <string_view>
#include <unordered_map>

namespace Corona::Systems::Vision {

enum class VisionResourceOwnership {
    SharedLogicalScene,
    SharedSceneGpu,
    PerPipelineRenderState,
    LegacyPipelineOwned,
};

struct VisionOwnershipAuditEntry {
    std::string_view name;
    VisionResourceOwnership target_ownership;
    std::string_view current_owner;
    std::string_view phase4_action;
};

inline constexpr VisionOwnershipAuditEntry kVisionPhase4OwnershipAudit[] = {
    {"Pipeline::scene_",
     VisionResourceOwnership::SharedLogicalScene,
     "vision::Pipeline",
     "Replace value ownership with a shared scene reference in Phase 4D."},
    {"Scene::geometry_",
     VisionResourceOwnership::SharedSceneGpu,
     "vision::Scene",
     "Move scene-correlated GPU geometry state into shared scene GPU resource in Phase 4C."},
    {"Geometry::rp_",
     VisionResourceOwnership::LegacyPipelineOwned,
     "vision::Geometry",
     "Remove Pipeline* dependency and pass explicit scene GPU/render context in Phase 4C."},
    {"GeometryData mesh buffers",
     VisionResourceOwnership::SharedSceneGpu,
     "vision::GeometryData via pipeline BindlessArray",
     "Share mesh buffers and mesh handle buffers per logical scene, not per render mode."},
    {"Geometry instance buffers",
     VisionResourceOwnership::SharedSceneGpu,
     "vision::GeometryData via pipeline BindlessArray",
     "Update instance buffers and TLAS once per shared logical transform version."},
    {"Accel / BLAS / TLAS",
     VisionResourceOwnership::SharedSceneGpu,
     "vision::Geometry via pipeline Device/Stream",
     "Move acceleration structures under shared scene GPU resource."},
    {"Material and medium registries",
     VisionResourceOwnership::SharedSceneGpu,
     "vision::Scene registries prepared through current pipeline",
     "Keep scene material/medium tables shared when they represent scene data."},
    {"FrameBuffer and denoiser state",
     VisionResourceOwnership::PerPipelineRenderState,
     "vision::Pipeline renderer/framebuffer",
     "Keep per PT/SVGF/SSAT runtime."},
    {"Global::pipeline() and Global::bindless_array() users",
     VisionResourceOwnership::LegacyPipelineOwned,
     "vision::Global / Toolkit helpers",
     "Replace usages that bind scene data to one active pipeline before Phase 5."},
};

struct VisionSceneResourceKey {
    std::string source_path_key;
    VisionPipelineSource source{VisionPipelineSource::EngineBuilt};

    friend bool operator==(const VisionSceneResourceKey& lhs,
                           const VisionSceneResourceKey& rhs) noexcept {
        return lhs.source_path_key == rhs.source_path_key && lhs.source == rhs.source;
    }
};

struct VisionSceneResourceKeyHash {
    [[nodiscard]] std::size_t operator()(
        const VisionSceneResourceKey& key) const noexcept {
        std::size_t seed = std::hash<std::string>{}(key.source_path_key);
        seed ^= std::hash<int>{}(static_cast<int>(key.source)) +
                0x9e3779b97f4a7c15ull + (seed << 6u) + (seed >> 2u);
        return seed;
    }
};

struct VisionSceneResource {
    VisionSceneResourceKey key;
    std::string display_source_path;
    std::string overlay_path;
    std::string overlay_guid;
    std::uint64_t logical_transform_version{0};
    std::unordered_map<std::uintptr_t, std::size_t> external_live_transform_signatures;

    [[nodiscard]] bool is_external_live() const noexcept {
        return key.source == VisionPipelineSource::ExternalLive;
    }

    void mark_transforms_changed() noexcept {
        ++logical_transform_version;
    }
};

[[nodiscard]] inline std::string_view vision_resource_ownership_name(
    VisionResourceOwnership ownership) noexcept {
    switch (ownership) {
        case VisionResourceOwnership::SharedLogicalScene:
            return "shared_logical_scene";
        case VisionResourceOwnership::SharedSceneGpu:
            return "shared_scene_gpu";
        case VisionResourceOwnership::PerPipelineRenderState:
            return "per_pipeline_render_state";
        case VisionResourceOwnership::LegacyPipelineOwned:
            return "legacy_pipeline_owned";
    }
    return "legacy_pipeline_owned";
}

}  // namespace Corona::Systems::Vision
