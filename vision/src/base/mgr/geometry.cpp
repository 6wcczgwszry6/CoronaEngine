//
// Created by Z on 2025/12/13.
//

#include "geometry.h"
#include "math/transform.h"
#include "scene.h"
#include "base/scattering/medium.h"
#include "pipeline.h"

namespace vision {
using namespace ocarina;

namespace {

vector<uint> collect_instance_mesh_ids(const GeometryData &data) {
    vector<uint> mesh_ids;
    const auto &instances = data.instances().host_buffer();
    mesh_ids.reserve(instances.size());
    for (const auto &inst : instances) {
        mesh_ids.push_back(inst.mesh_id);
    }
    return mesh_ids;
}

bool can_update_tlas(const GeometryData &data, const vector<uint> &accel_mesh_ids, const Accel &accel) {
    const auto &instances = data.instances().host_buffer();
    if (instances.empty()) {
        return false;
    }
    if (accel.mesh_num() != instances.size() || accel_mesh_ids.size() != instances.size()) {
        return false;
    }
    for (uint i = 0; i < instances.size(); ++i) {
        if (instances[i].mesh_id != accel_mesh_ids[i]) {
            return false;
        }
    }
    return true;
}

void update_accel_transforms(const GeometryData &data, Accel &accel) {
    const auto &instances = data.instances().host_buffer();
    for (uint i = 0; i < instances.size(); ++i) {
        accel.set_transform(i, instances[i].o2w());
    }
}

void rebuild_accel(GeometryData &data, Pipeline &pipeline, Accel &accel) {
    accel.clear();
    if (data.instances().empty()) {
        return;
    }

    Stream &stream = pipeline.stream();
    for (const auto &inst : data.instances()) {
        uint mesh_id = inst.mesh_id;
        const auto &mesh_handle = data.mesh_handles()[mesh_id];
        BufferView<Vertex> vert_buffer = pipeline.bindless_array().buffer_view<Vertex>(mesh_handle.vertex_buffer);
        BufferView<Triangle> tri_buffer = pipeline.bindless_array().buffer_view<Triangle>(mesh_handle.triangle_buffer);
        ocarina::RHIMesh mesh = pipeline.device().create_mesh(vert_buffer, tri_buffer);
        stream << mesh.build_bvh();
        accel.add_instance(ocarina::move(mesh), inst.o2w());
    }

    OC_INFO_FORMAT("vertex num is {}, triangle num is {}", accel.vertex_num(), accel.triangle_num());
    stream << accel.build_bvh();
    stream << synchronize();
    stream << commit();
}

}// namespace

GeometryData::GeometryData(BindlessArray &bindless) noexcept
    : instances_(bindless), mesh_handles_(bindless) {}

void GeometryData::add_instance(InstanceData instance) noexcept {
    instances_.push_back(std::move(instance));
}

void GeometryData::add_mesh_handle(MeshHandle handle) noexcept {
    mesh_handles_.push_back(handle);
}

void GeometryData::reset_gpu_buffers(Device &device) noexcept {
    instances_.reset_device_buffer_immediately(device, "Geometry::instances_");
    mesh_handles_.reset_device_buffer_immediately(device, "Geometry::mesh_handles_");
    instances_.register_self();
    mesh_handles_.register_self();
}

void GeometryData::clear_host() noexcept {
    instances_.host_buffer().clear();
    mesh_handles_.host_buffer().clear();
}

void GeometryData::clear_all() noexcept {
    instances_.clear_all();
    mesh_handles_.clear_all();
}

// mesh registry methods

bool GeometryData::contain_mesh(uint64_t hash) noexcept {
    auto iter = mesh_map_.find(hash);
    return iter != mesh_map_.cend();
}

SP<Mesh> GeometryData::register_mesh(SP<Mesh> mesh) noexcept {
    uint64_t hash = mesh->hash();
    if (!contain_mesh(hash)) {
        mesh_map_.insert(make_pair(hash, mesh));
        meshes_.push_back(mesh.get());
    }
    return get_mesh(hash);
}

SP<Mesh> GeometryData::register_mesh(Mesh mesh) noexcept {
    uint64_t hash = mesh.hash();
    if (!contain_mesh(hash)) {
        return register_mesh(make_shared<Mesh>(ocarina::move(mesh)));
    }
    return get_mesh(hash);
}

SP<const Mesh> GeometryData::get_mesh(uint64_t hash) const noexcept {
    if (auto iter = mesh_map_.find(hash);
        iter != mesh_map_.cend()) {
        return mesh_map_.at(hash);
    }
    return nullptr;
}

SP<Mesh> GeometryData::get_mesh(uint64_t hash) noexcept {
    if (auto iter = mesh_map_.find(hash);
        iter != mesh_map_.cend()) {
        return mesh_map_.at(hash);
    }
    return nullptr;
}

bool GeometryData::remove_mesh(uint64_t hash) noexcept {
    for (auto iter = meshes_.cbegin();
         iter != meshes_.cend(); ++iter) {
        Mesh *mesh = *iter;
        if (mesh->hash() == hash) {
            meshes_.erase(iter);
            break;
        }
    }
    if (auto iter = mesh_map_.find(hash); iter != mesh_map_.cend()) {
        mesh_map_.erase(iter);
        return true;
    }
    return false;
}

CommandBatch GeometryData::upload_meshes() noexcept {
    CommandBatch ret;
    for_each_mesh([&](Mesh *mesh, uint i) {
        ret << mesh->upload();
    });
    return ret;
}

void GeometryData::for_each_mesh(const std::function<void(Mesh *, uint)> &func) noexcept {
    for (uint i = 0; i < meshes_.size(); ++i) {
        func(meshes_[i], i);
    }
}

void GeometryData::for_each_mesh(const std::function<void(const Mesh *, uint)> &func) const noexcept {
    for (uint i = 0; i < meshes_.size(); ++i) {
        func(meshes_[i], i);
    }
}

void GeometryData::tidy_up_meshes() noexcept {
    for_each_mesh([&](Mesh *mesh, uint i) {
        mesh->set_index(i);
    });
}

void GeometryData::clear_meshes() noexcept {
    mesh_map_.clear();
    meshes_.clear();
}

Geometry::Geometry() = default;

void Geometry::init(Pipeline *rp) {
    rp_ = rp;
    data_ = make_unique<GeometryData>(rp_->bindless_array());
    accel_ = rp_->device().create_accel(FAST_UPDATE);
}

void Geometry::update_instances(const vector<SP<ShapeInstance>> &instances) {
    data_->clear_host();

    data_->for_each_mesh([&](const Mesh *mesh, uint i) {
        MeshHandle mesh_handle{.vertex_buffer = mesh->vertex_buffer().index().hv(),
                               .triangle_buffer = mesh->triangle_buffer().index().hv()};
        data_->add_mesh_handle(mesh_handle);
    });

    std::for_each(instances.begin(), instances.end(), [&](SP<const ShapeInstance> instance) {
        data_->add_instance(instance->handle());
    });
}

void Geometry::update_accel() {
    TIMER(update_accel);
    vector<uint> current_mesh_ids = collect_instance_mesh_ids(*data_);
    if (data_->instances().empty()) {
        accel_.clear();
        accel_mesh_ids_.clear();
        return;
    }
    if (!can_update_tlas(*data_, accel_mesh_ids_, accel_)) {
        rebuild_accel(*data_, *rp_, accel_);
        accel_mesh_ids_ = ocarina::move(current_mesh_ids);
        return;
    }

    update_accel_transforms(*data_, accel_);
    Stream &stream = rp_->stream();
    stream << accel_.update_bvh();
    stream << synchronize();
    stream << commit();
    accel_mesh_ids_ = ocarina::move(current_mesh_ids);
}

void Geometry::build_accel() {
    TIMER(build_accel);
    rebuild_accel(*data_, *rp_, accel_);
    accel_mesh_ids_ = collect_instance_mesh_ids(*data_);
}

void Geometry::reset_device_buffer() {
    data_->reset_gpu_buffers(rp_->device());
}

void Geometry::upload() const {
    Stream &stream = rp_->stream();
    stream << data_->upload_meshes()
           << data_->mesh_handles().upload()
           << data_->instances().upload()
           << synchronize();
    stream << commit();
}

void Geometry::clear() noexcept {
    data_->clear_all();
    accel_.clear();
    accel_mesh_ids_.clear();
}

Interaction Geometry::compute_surface_interaction(const TriangleHitVar &hit, bool is_complete) const noexcept {
    Interaction it{Global::instance().pipeline()->scene().process_mediums()};
    it.prim_id = hit.prim_id;
    Var inst = data_->instances().read(hit.inst_id);
    it.inst_id = hit.inst_id;
    Var mesh = data_->mesh_handles().read(inst.mesh_id);
    auto o2w = Transform(inst->o2w());
    Var tri = get_triangle(mesh.triangle_buffer, hit.prim_id);
    auto [v0, v1, v2] = get_vertices(mesh.vertex_buffer, tri);
    it.lightmap_id = inst.lightmap_id;
    it.set_light(inst.light_id);
    it.set_material(inst.mat_id);
    it.set_medium(inst.inside_medium, inst.outside_medium);
    
    outline("Geometry::compute_surface_interaction", [&] {
        comment("compute pos");
        Var p0 = o2w.apply_point(v0->position());
        Var p1 = o2w.apply_point(v1->position());
        Var p2 = o2w.apply_point(v2->position());
        Float3 pos = hit->triangle_lerp(p0, p1, p2);
        it.pos = pos;
        it.lightmap_uv = hit->triangle_lerp(v0->lightmap_uv(), v1->lightmap_uv(), v2->lightmap_uv());

        Frame<Float3> frame;

        comment("compute geometry uvn");
        Float3 dp02 = p0 - p2;
        Float3 dp12 = p1 - p2;
        Float3 ng_un = cross(dp02, dp12);
        it.prim_area = 0.5f * length(ng_un);
        Float2 duv02 = v0->tex_coord() - v2->tex_coord();
        Float2 duv12 = v1->tex_coord() - v2->tex_coord();
        Float det = duv02[0] * duv12[1] - duv02[1] * duv12[0];
        Bool degenerate_uv = abs(det) < float(1e-8);
        if (is_complete) {
            Float3 dp_du, dp_dv;
            $if(!degenerate_uv) {
                Float inv_det = 1 / det;
                dp_du = normalize((duv12[1] * dp02 - duv02[1] * dp12) * inv_det);
                dp_dv = normalize((-duv12[0] * dp02 + duv02[0] * dp12) * inv_det);
            }
            $else {
                dp_du = normalize(p1 - p0);
                dp_dv = normalize(p2 - p0);
            };
            frame.set(dp_du, dp_dv, normalize(ng_un));
        } else {
            frame.set(dp02, dp12, normalize(ng_un));
        }

        if (is_complete) {
            comment("compute shading uvn");
            Float3 dn_du, dn_dv;
            Float3 normal = hit->triangle_lerp(v0->normal(), v1->normal(), v2->normal());
            it.shading.set_frame(frame);
            it.ng_local = normal;
            $if(!is_zero(normal)) {
                Float3 ns = normalize(o2w.apply_normal(normal));
                it.shading.update(ns);
            };

            Float3 dn1 = v0->normal() - v2->normal();
            Float3 dn2 = v1->normal() - v2->normal();
            Float3 dn = cross(v2->normal() - v0->normal(),
                              v1->normal() - v0->normal());

            $if(degenerate_uv) {
                $if(length_squared(dn)) {
                    dn_du = make_float3(0.f);
                    dn_dv = make_float3(0.f);
                }
                $else {
                    coordinate_system(dn, dn_du, dn_dv);
                };
            }
            $else {
                Float inv_det = 1 / det;
                dn_du = (duv12[1] * dn1 - duv02[1] * dn2) * inv_det;
                dn_dv = (-duv12[0] * dn1 + duv02[0] * dn2) * inv_det;
            };
            it.shading.dn_du = dn_du;
            it.shading.dn_dv = dn_dv;
        }
        Float2 uv = hit->triangle_lerp(v0->tex_coord(), v1->tex_coord(), v2->tex_coord());
        it.uv = uv;
        it.ng = frame.z;
    });
    return it;
}

TriangleHitVar Geometry::trace_closest(const RayVar &ray) const noexcept {
    return accel_.trace_closest(ray);
}

Bool Geometry::trace_occlusion(const RayVar &ray) const noexcept {
    return accel_.trace_occlusion(ray);
}

Bool Geometry::occluded(const Interaction &it, const Float3 &pos, RayState *rs) const noexcept {
    RayVar shadow_ray;
    if (rs) {
        *rs = it.spawn_ray_state_to(pos);
        shadow_ray = rs->ray;
    } else {
        shadow_ray = it.spawn_ray_to(pos);
    }
    return trace_occlusion(shadow_ray);
}

SampledSpectrum Geometry::Tr(Scene &scene, TSampler &sampler, const SampledWavelengths &swl,
                             const RayState &ray_state) const noexcept {
    SampledSpectrum ret{swl.dimension(), 1.f};
    if (scene.process_mediums()) {
        $if(ray_state.in_medium()) {
            scene.mediums().dispatch(ray_state.medium, [&](const Medium *medium) {
                ret = medium->Tr(ray_state.ray, swl, sampler);
            });
        };
    }
    return ret;
}

TriangleVar Geometry::get_triangle(const Uint &buffer_index, const Uint &index) const noexcept {
    return rp_->bindless_array().buffer_var<Triangle>(buffer_index).read(index);
}

array<Var<Vertex>, 3> Geometry::get_vertices(const Uint &buffer_index,
                                             const Var<Triangle> &tri) const noexcept {
    BindlessArrayBuffer<Vertex> buffer = rp_->bindless_array().buffer_var<Vertex>(buffer_index);
    return {buffer.read(tri.i),
            buffer.read(tri.j),
            buffer.read(tri.k)};
}

LightEvalContext Geometry::compute_light_eval_context(const Uint &inst_id,
                                                      const Uint &prim_id,
                                                      const Float2 &bary) const noexcept {
    TriangleHitVar hit;
    hit.inst_id = inst_id;
    hit.prim_id = prim_id;
    hit.bary = bary;
    Interaction it = compute_surface_interaction(hit, false);
    LightEvalContext ret(it);
    return ret;
}

}// namespace vision