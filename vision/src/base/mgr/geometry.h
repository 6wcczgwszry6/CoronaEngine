//
// Created by Z on 2025/12/13.
//

#pragma once

#include "rhi/common.h"
#include "base/shape.h"
#include "base/color/spectrum.h"
#include "base/scattering/interaction.h"
#include "base/sampler.h"
#include "base/using.h"

namespace vision {

class Scene;
class Pipeline;
class ShapeInstance;

class GeometryData {
private:
    RegistrableManaged<InstanceData> instances_;
    RegistrableManaged<MeshHandle> mesh_handles_;

    // mesh registry (merged from MeshRegistry)
    std::map<uint64_t, SP<Mesh>> mesh_map_;
    vector<Mesh *> meshes_;

public:
    explicit GeometryData(BindlessArray &bindless) noexcept;
    void add_instance(InstanceData instance) noexcept;
    void add_mesh_handle(MeshHandle handle) noexcept;
    void reset_gpu_buffers(Device &device) noexcept;
    void clear_host() noexcept;
    void clear_all() noexcept;
    OC_MAKE_MEMBER_GETTER(instances, &)
    OC_MAKE_MEMBER_GETTER(mesh_handles, &)

    // mesh registry methods
    [[nodiscard]] SP<Mesh> register_mesh(Mesh mesh) noexcept;
    [[nodiscard]] SP<Mesh> register_mesh(SP<Mesh> mesh) noexcept;
    [[nodiscard]] SP<const Mesh> get_mesh(uint64_t hash) const noexcept;
    [[nodiscard]] SP<Mesh> get_mesh(uint64_t hash) noexcept;
    [[nodiscard]] bool contain_mesh(uint64_t hash) noexcept;
    bool remove_mesh(uint64_t hash) noexcept;
    [[nodiscard]] CommandBatch upload_meshes() noexcept;
    void for_each_mesh(const std::function<void(Mesh *, uint)> &func) noexcept;
    void for_each_mesh(const std::function<void(const Mesh *, uint)> &func) const noexcept;
    void tidy_up_meshes() noexcept;
    void clear_meshes() noexcept;
};

class Geometry {
private:
    ocarina::Accel accel_;
    UP<GeometryData> data_;
    vector<uint> accel_mesh_ids_;
    Pipeline *rp_{};

public:
    Geometry();
    void init(Pipeline *rp);

    [[nodiscard]] GeometryData *data() noexcept { return data_.get(); }
    [[nodiscard]] const GeometryData *data() const noexcept { return data_.get(); }
    OC_MAKE_MEMBER_GETTER(accel, &)

    void update_instances(const vector<SP<ShapeInstance>> &instances);
    void reset_device_buffer();
    void build_accel();
    void update_accel();
    void upload() const;
    void clear() noexcept;

    // DSL methods
    [[nodiscard]] TriangleHitVar trace_closest(const RayVar &ray) const noexcept;
    [[nodiscard]] Bool trace_occlusion(const RayVar &ray) const noexcept;
    [[nodiscard]] Bool occluded(const Interaction &it, const Float3 &pos, RayState *rs = nullptr) const noexcept;
    template<typename ...Args>
    [[nodiscard]] auto visibility(Args &&...args) const noexcept {
        Bool occ = occluded(OC_FORWARD(args)...);
        return cast<int>(!occ);
    }
    [[nodiscard]] SampledSpectrum Tr(Scene &scene, TSampler &sampler, const SampledWavelengths &swl, const RayState &ray_state) const noexcept;
    [[nodiscard]] LightEvalContext compute_light_eval_context(const Uint &inst_id,
                                                              const Uint &prim_id,
                                                              const Float2 &bary) const noexcept;
    [[nodiscard]] TriangleVar get_triangle(const Uint &buffer_index, const Uint &index) const noexcept;
    [[nodiscard]] array<Var<Vertex>, 3> get_vertices(const Uint &buffer_index,
                                                     const Var<Triangle> &tri) const noexcept;
    [[nodiscard]] Interaction compute_surface_interaction(const TriangleHitVar &hit, bool is_complete) const noexcept;
    [[nodiscard]] Interaction compute_surface_interaction(const TriangleHitVar &hit, const Float3 &view_pos) const noexcept {
        auto ret = compute_surface_interaction(hit, true);
        ret.update_wo(view_pos);
        return ret;
    }
    [[nodiscard]] Interaction compute_surface_interaction(const TriangleHitVar &hit, RayVar &ray, bool is_complete = true) const noexcept {
        auto ret = compute_surface_interaction(hit, is_complete);
        ret.wo = normalize(-ray->direction());
        ray.dir_max.w = length(ret.pos - ray->origin()) / length(ray->direction());
        return ret;
    }
    [[nodiscard]] Bool is_emissive(const Uint &inst_id) const noexcept {
        return data_->instances().read(inst_id).light_id != InvalidUI32;
    }
};

}// namespace vision
