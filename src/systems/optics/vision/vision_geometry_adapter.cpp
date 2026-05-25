#include "vision_geometry_adapter.h"

#ifdef CORONA_ENABLE_VISION

#include <corona/kernel/core/i_logger.h>
#include <corona/shared_data_hub.h>

#include <cstring>
#include <vector>

#include "base/mgr/geometry.h"
#include "base/mgr/scene.h"
#include "base/shape.h"
#include "base/using.h"
#include "math/basic_types.h"
#include "vision/vision_material_adapter.h"

namespace Corona::Systems::Vision {

int build_vision_geometry(::vision::Scene& scene) {
    scene.clear_shapes();

    auto& hub = SharedDataHub::instance();
    auto& actor_storage = hub.actor_storage();
    auto& profile_storage = hub.profile_storage();
    auto& optics_storage = hub.optics_storage();
    auto& geom_storage = hub.geometry_storage();
    auto& transform_storage = hub.model_transform_storage();

    int shape_count = 0;

    for (const auto& scene_dev : hub.scene_storage()) {
        if (!scene_dev.enabled) continue;

        auto group = std::make_shared<::vision::ShapeGroup>();
        bool group_has_instances = false;

        for (auto actor_handle : scene_dev.actor_handles) {
            auto actor = actor_storage.acquire_read(actor_handle);
            if (!actor) continue;

            for (auto profile_handle : actor->profile_handles) {
                auto profile = profile_storage.acquire_read(profile_handle);
                if (!profile || profile->optics_handle == 0 || profile->geometry_handle == 0) continue;

                auto optics = optics_storage.acquire_read(profile->optics_handle);
                if (!optics || !optics->visible) continue;

                auto geom = geom_storage.acquire_read(optics->geometry_handle);
                if (!geom) continue;

                // Build the object-to-world transform
                ::vision::float4x4 o2w = ::vision::make_float4x4(1.f);
                if (auto transform = transform_storage.acquire_read(geom->transform_handle)) {
                    ktm::fmat4x4 corona_mat = transform->compute_matrix();
                    // Both ktm::fmat4x4 and ocarina::float4x4 are column-major 4x4
                    for (int col = 0; col < 4; ++col) {
                        for (int row = 0; row < 4; ++row) {
                            o2w[col][row] = corona_mat[col][row];
                        }
                    }
                }

                for (auto& mesh_dev : geom->mesh_handles) {
                    // Pick the vertex buffer that has data (primary or storage mirror)
                    HardwareBuffer* vbuf = &mesh_dev.vertexBuffer;
                    if (!(*vbuf) || vbuf->getElementCount() == 0) {
                        vbuf = &mesh_dev.vertexStorageBuffer;
                    }
                    if (!(*vbuf) || vbuf->getElementCount() == 0) {
                        CFW_LOG_WARNING("Vision geometry adapter: no vertex data, skipping mesh");
                        continue;
                    }

                    uint64_t vert_bytes = vbuf->getElementCount() * vbuf->getElementSize();
                    constexpr uint64_t kCoronaVertexStride = 32;  // pos(12) + normal(12) + uv(8)
                    uint64_t vert_count = vert_bytes / kCoronaVertexStride;
                    if (vert_count == 0) {
                        CFW_LOG_WARNING("Vision geometry adapter: zero vertices after stride division");
                        continue;
                    }

                    std::vector<uint8_t> vert_data(vert_bytes);
                    if (!vbuf->copyToData(vert_data.data(), vert_bytes)) {
                        CFW_LOG_WARNING("Vision geometry adapter: failed to read vertex data");
                        continue;
                    }

                    // Pick the index buffer that has data
                    HardwareBuffer* ibuf = &mesh_dev.indexBuffer;
                    if (!(*ibuf) || ibuf->getElementCount() == 0) {
                        ibuf = &mesh_dev.indexStorageBuffer;
                    }
                    if (!(*ibuf) || ibuf->getElementCount() == 0) {
                        CFW_LOG_WARNING("Vision geometry adapter: no index data, skipping mesh");
                        continue;
                    }

                    uint64_t idx_bytes = ibuf->getElementCount() * ibuf->getElementSize();
                    uint64_t idx_elem_size = ibuf->getElementSize();
                    if (idx_bytes == 0 || idx_elem_size == 0) {
                        CFW_LOG_WARNING("Vision geometry adapter: empty index buffer, skipping mesh");
                        continue;
                    }

                    std::vector<uint8_t> idx_data(idx_bytes);
                    if (!ibuf->copyToData(idx_data.data(), idx_bytes)) {
                        CFW_LOG_WARNING("Vision geometry adapter: failed to read index data");
                        continue;
                    }

                    // Parse Corona vertices (interleaved: pos3, normal3, uv2) into ocarina::Vertex
                    std::vector<::vision::Vertex> vertices;
                    vertices.reserve(vert_count);
                    for (uint64_t vi = 0; vi < vert_count; ++vi) {
                        const float* fptr = reinterpret_cast<const float*>(
                            vert_data.data() + vi * kCoronaVertexStride);
                        ::vision::Vertex v;
                        v.pos = {fptr[0], fptr[1], fptr[2]};
                        v.n   = {fptr[3], fptr[4], fptr[5]};
                        v.uv  = {fptr[6], fptr[7]};
                        v.uv2 = {0.f, 0.f};
                        vertices.push_back(v);
                    }

                    // Parse indices into ocarina::Triangle
                    uint64_t idx_count = idx_bytes / idx_elem_size;
                    uint64_t tri_count = idx_count / 3;
                    std::vector<::vision::Triangle> triangles;
                    triangles.reserve(tri_count);

                    if (idx_elem_size == 4) {
                        const uint32_t* idx32 = reinterpret_cast<const uint32_t*>(idx_data.data());
                        for (uint64_t ti = 0; ti < tri_count; ++ti) {
                            triangles.emplace_back(
                                static_cast<uint32_t>(idx32[ti * 3]),
                                static_cast<uint32_t>(idx32[ti * 3 + 1]),
                                static_cast<uint32_t>(idx32[ti * 3 + 2]));
                        }
                    } else if (idx_elem_size == 2) {
                        const uint16_t* idx16 = reinterpret_cast<const uint16_t*>(idx_data.data());
                        for (uint64_t ti = 0; ti < tri_count; ++ti) {
                            triangles.emplace_back(
                                static_cast<uint32_t>(idx16[ti * 3]),
                                static_cast<uint32_t>(idx16[ti * 3 + 1]),
                                static_cast<uint32_t>(idx16[ti * 3 + 2]));
                        }
                    } else {
                        CFW_LOG_WARNING("Vision geometry adapter: unsupported index element size {}",
                                        static_cast<int>(idx_elem_size));
                        continue;
                    }

                    // Create Vision Mesh and upload to Vision GPU device
                    auto mesh = std::make_shared<::vision::Mesh>(
                        std::move(vertices), std::move(triangles));
                    mesh->upload_immediately();
                    scene.geometry().data()->register_mesh(mesh);

                    // Create material and ShapeInstance
                    auto material = create_vision_material(*optics, mesh_dev);
                    auto instance = std::make_shared<::vision::ShapeInstance>(mesh);
                    instance->set_o2w(o2w);
                    if (material) {
                        instance->set_material(material);
                        scene.add_material(material);
                    }

                    group->add_instance(*instance);
                    ++shape_count;
                    group_has_instances = true;
                }
            }
        }

        if (group_has_instances) {
            scene.add_shape(group);
        }
    }

    // Finalize: encode material/mesh IDs into instance handles, register with geometry, build BVH
    scene.fill_instances();
    scene.update_geometry_instances();
    scene.geometry().build_accel();
    scene.geometry().upload();

    CFW_LOG_INFO("Vision geometry adapter: added {} ShapeInstances", shape_count);
    return shape_count;
}

}  // namespace Corona::Systems::Vision

#endif  // CORONA_ENABLE_VISION
