#include <corona/systems/optics/vision_scene_resource.h>

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string_view>
#include <unordered_map>

namespace {

using Corona::Systems::Vision::VisionOwnershipAuditEntry;
using Corona::Systems::Vision::VisionPipelineSource;
using Corona::Systems::Vision::VisionResourceOwnership;
using Corona::Systems::Vision::VisionSceneResource;
using Corona::Systems::Vision::VisionSceneResourceKey;
using Corona::Systems::Vision::VisionSceneResourceKeyHash;
using Corona::Systems::Vision::kVisionPhase4OwnershipAudit;

[[noreturn]] void fail(std::string_view message) {
    std::cerr << "FAIL: " << message << '\n';
    std::exit(1);
}

void expect(bool condition, std::string_view message) {
    if (!condition) {
        fail(message);
    }
}

bool audit_contains(std::string_view name, VisionResourceOwnership ownership) {
    return std::any_of(std::begin(kVisionPhase4OwnershipAudit),
                       std::end(kVisionPhase4OwnershipAudit),
                       [&](const VisionOwnershipAuditEntry& entry) {
                           return entry.name == name &&
                                  entry.target_ownership == ownership;
                       });
}

void ownership_audit_covers_phase4_required_dependencies() {
    expect(audit_contains("Pipeline::scene_",
                          VisionResourceOwnership::SharedLogicalScene),
           "Phase 4 audit should cover Pipeline::scene_ as shared logical scene");
    expect(audit_contains("Scene::geometry_",
                          VisionResourceOwnership::SharedSceneGpu),
           "Phase 4 audit should cover Scene::geometry_ as shared scene GPU");
    expect(audit_contains("Geometry::rp_",
                          VisionResourceOwnership::LegacyPipelineOwned),
           "Phase 4 audit should cover Geometry::rp_ legacy pipeline dependency");
    expect(audit_contains("FrameBuffer and denoiser state",
                          VisionResourceOwnership::PerPipelineRenderState),
           "Phase 4 audit should keep framebuffer and denoiser per pipeline");
    expect(audit_contains("Global::pipeline() and Global::bindless_array() users",
                          VisionResourceOwnership::LegacyPipelineOwned),
           "Phase 4 audit should cover Global pipeline/bindless callers");
}

void scene_resource_key_is_mode_independent() {
    const VisionSceneResourceKey external_file{"d:/scene/vision_scene.json",
                                               VisionPipelineSource::ExternalFile};
    const VisionSceneResourceKey external_live{"d:/scene/vision_scene.json",
                                               VisionPipelineSource::ExternalLive};

    std::unordered_map<VisionSceneResourceKey,
                       int,
                       VisionSceneResourceKeyHash>
        resources;
    resources.emplace(external_file, 1);
    resources[external_file] = 2;
    resources.emplace(external_live, 3);

    expect(resources.size() == 2,
           "shared scene resources should be keyed by scene identity/source, not render mode");
    expect(resources[external_file] == 2,
           "same scene resource key should reuse the existing resource slot");
}

void transform_state_lives_on_scene_resource() {
    VisionSceneResource resource;
    resource.key = VisionSceneResourceKey{"d:/scene/vision_scene.json",
                                          VisionPipelineSource::ExternalLive};
    expect(resource.is_external_live(),
           "external_live source should be visible from scene resource");

    resource.external_live_transform_signatures.emplace(42u, 100u);
    resource.mark_transforms_changed();

    expect(resource.logical_transform_version == 1u,
           "scene resource transform version should increment on shared transform update");
    expect(resource.external_live_transform_signatures.at(42u) == 100u,
           "external_live transform signature cache should live on scene resource");
}

void ownership_names_are_stable() {
    expect(Corona::Systems::Vision::vision_resource_ownership_name(
               VisionResourceOwnership::SharedLogicalScene) == "shared_logical_scene",
           "shared logical scene ownership name should be stable");
    expect(Corona::Systems::Vision::vision_resource_ownership_name(
               VisionResourceOwnership::SharedSceneGpu) == "shared_scene_gpu",
           "shared scene GPU ownership name should be stable");
    expect(Corona::Systems::Vision::vision_resource_ownership_name(
               VisionResourceOwnership::PerPipelineRenderState) ==
               "per_pipeline_render_state",
           "per-pipeline ownership name should be stable");
}

}  // namespace

int main() {
    ownership_audit_covers_phase4_required_dependencies();
    scene_resource_key_is_mode_independent();
    transform_state_lives_on_scene_resource();
    ownership_names_are_stable();
    return 0;
}
