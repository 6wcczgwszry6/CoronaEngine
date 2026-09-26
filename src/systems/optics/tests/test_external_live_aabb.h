#pragma once

#include "../vision/vision_external_live_aabb.h"
#include "math/transform.h"
#include <cmath>
#include <cstdlib>
#include <iostream>

inline void external_live_aabb_regressions() {
    using namespace Corona::Systems::Vision;
    using namespace vision;
    auto check = [](bool ok, const char* message) {
        if (!ok) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); }
    };
    auto mesh = std::make_shared<Mesh>(
        vector<Vertex>{Vertex{make_float3(-1, 0, 0), make_float3(0, 0, 1), make_float2(0)},
                       Vertex{make_float3(2, 0, 0), make_float3(0, 0, 1), make_float2(0)},
                       Vertex{make_float3(0, 3, 1), make_float3(0, 0, 1), make_float2(0)}},
        vector<Triangle>{Triangle{0, 1, 2}});
    ShapeInstance initial(mesh);
    initial.set_o2w(translation<H>(make_float3(4, 0, 0)));
    auto group = std::make_shared<ShapeGroup>(std::move(initial));
    VisionSceneResource resource;
    ExternalLiveAabbCache cache;
    resource.upsert_external_live_shape({.actor_handle = 42, .shape_index = 0});
    auto sync = [&](size_t normal, size_t target, float4x4 matrix, bool hidden = false) {
        return sync_external_live_group(resource, cache, 42, 0, group, normal, target, matrix, hidden, true);
    };
    auto identity = make_float4x4(1.f);
    auto first = sync(10, 10, identity);
    check(first.aabb_updates > 0, "first sync must establish complete bounds and metadata");
    auto exact = [&] {
        Box3f expected;
        group->for_each([&](SP<ShapeInstance> instance, uint) {
            const auto box = instance->compute_aabb();
            check(aabb_equal(instance->aabb, box), "instance bounds differ from exact triangle algorithm");
            expected.extend(box);
        });
        check(aabb_equal(group->aabb, expected), "group bounds differ from union of exact instance bounds");
    };
    exact();
    check(group->aabb.lower[0] == 3.f && group->aabb.upper[0] == 6.f && group->aabb.upper[1] == 3.f,
          "imported triangle bounds must match hand-computed coordinates");
    check(sync(10, 10, identity).aabb_updates == 0, "stationary actor must reuse AABB");
    check(group->instance(0).o2w()[3][0] == 4.f, "initial imported instance matrix must survive proxy sync");
    auto moved = translation<H>(make_float3(2, -3, 4)) * scale<H>(make_float3(2, .5f, 3));
    moved[0][0] = 0; moved[0][1] = 2; moved[1][0] = -.5f; moved[1][1] = 0;
    check(sync(11, 11, moved).changed, "move/rotation/nonuniform scale must publish change");
    exact();
    check(group->aabb.lower[0] == .5f && group->aabb.lower[1] == -5.f && group->aabb.lower[2] == 4.f &&
          group->aabb.upper[0] == 2.f && group->aabb.upper[1] == 1.f && group->aabb.upper[2] == 7.f,
          "rotated and scaled bounds must match hand-computed coordinates");
    check(sync(11, 11, moved).aabb_updates == 0, "changed actor must become cacheable again");
    auto hidden = scale<H>(make_float3(0));
    check(sync(11, 99, hidden, true).changed, "hide must update GPU transform state");
    exact();
    check(sync(11, 99, hidden, true).aabb_updates == 0, "hidden stationary actor must reuse AABB");
    check(sync(10, 10, identity).changed, "restore must publish change");
    exact();
    check(group->instance(0).o2w()[3][0] == 4.f, "restore must recover original matrix");

    ExternalLiveAabbCache second_cache;
    ShapeInstance second_initial(mesh);
    second_initial.set_o2w(translation<H>(make_float3(4, 0, 0)));
    auto second_group = std::make_shared<ShapeGroup>(std::move(second_initial));
    sync_external_live_group(resource, second_cache, 42, 0, second_group, 10, 10, identity, false, true);
    check(sync(10, 10, identity).aabb_updates == 0,
          "another runtime must not evict the first runtime's bounds cache");
    check(sync_external_live_group(resource, second_cache, 42, 0, second_group, 10, 10, identity, false, true).aabb_updates == 0,
          "switching coordinator runtime must reuse each runtime's own geometry");
    sync(10, 99, hidden, true);
    sync_external_live_group(resource, second_cache, 42, 0, second_group, 10, 99, hidden, true, true);
    sync(10, 10, identity);
    sync_external_live_group(resource, second_cache, 42, 0, second_group, 10, 10, identity, false, true);
    check(group->instance(0).o2w()[3][0] == 4.f && second_group->instance(0).o2w()[3][0] == 4.f,
          "hide/switch/restore must preserve original matrices in both runtimes");

    // Retain the writable reference across multiple syncs: counts and addresses stay unchanged.
    auto& vertices = mesh->vertices();
    check(sync(10, 10, identity).aabb_updates == 0, "read-only access must not invalidate bounds");
    vertices[2] = Vertex{make_float3(0, 7, 1), make_float3(0, 0, 1), make_float2(0)};
    auto deformed = sync(10, 10, identity);
    check(deformed.geometry_changed && deformed.changed && deformed.aabb_updates == 1,
          "in-place vertex edit must recompute bounds and request geometry rebuild");
    exact();
    mesh->triangles()[0] = Triangle{0, 1, 1};
    check(sync(10, 10, identity).geometry_changed, "triangle edits must invalidate geometry");
    exact();
    auto replacement = std::make_shared<Mesh>(mesh->vertices(), vector<Triangle>{Triangle{0, 1, 2}});
    group->instance(0).set_mesh(replacement);
    check(sync(10, 10, identity).geometry_changed, "mesh replacement must rebuild GPU geometry");
    exact();
    ShapeInstance added(replacement);
    added.set_o2w(translation<H>(make_float3(-5, 1, 0)));
    group->add_instance(std::move(added));
    check(sync(10, 10, identity).geometry_changed, "instance addition must rebuild geometry");
    exact();
    check(resource.logical_instance_count() == 2, "new instance metadata must be published");
    check(sync(10, 10, identity).aabb_updates == 0, "added instance must settle into reuse");

    ShapeInstance remaining(replacement);
    remaining.set_o2w(identity);
    group = std::make_shared<ShapeGroup>(std::move(remaining));
    check(sync(10, 10, identity).geometry_changed, "group replacement/removal must rebuild geometry");
    check(resource.logical_instance_count() == 1, "removed instances must leave no stale logical records");
    exact();
    resource.logical_instances.clear();
    check(sync(10, 10, identity).aabb_updates > 0, "missing logical cache must be repaired");
    exact();
    resource.reset_loaded_scene();
    check(sync(10, 10, identity).aabb_updates > 0, "scene reload must invalidate bounds cache");
    exact();
    check(sync(10, 10, identity).aabb_updates == 0, "camera-only changes require no world-bound update");
    std::cout << "ExternalLiveAabb regressions passed\n";
}
