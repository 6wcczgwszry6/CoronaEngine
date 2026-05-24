//
// Created by Zero on 2025/1/1.
//

#include "base/scattering/material.h"
#include "base/shader_graph/shader_node.h"
#include "base/mgr/scene.h"
#include "base/mgr/pipeline.h"

namespace vision {

/**
 Example material JSON:
 {
     "type" : "add",
     "name" : "MatAdd",
     "param" : {
         "mat0" : {
             "type" : "diffuse",
             "name" : "MatAddBase",
             "param" : {
                 "color" : { "channels" : "xyz", "node" : { "type" : "number", "param" : { "value" : [0.5, 0.5, 0.5] } } },
                 "sigma" : { "channels" : "x", "node" : { "type" : "number", "param" : { "value" : 0.3 } } }
             },
             "node_tab" : {}
         },
         "mat1" : {
             "type" : "emission",
             "name" : "MatAddEmit",
             "param" : {
                 "color" : { "channels" : "xyz", "node" : { "type" : "number", "param" : { "value" : [0.5, 0.5, 0.5] } } },
                 "strength" : { "channels" : "x", "node" : { "type" : "number", "param" : { "value" : 0.5 } } }
             },
             "node_tab" : {}
         }
     },
     "node_tab" : {}
 }
 */
class AddMaterial final : public Material {
private:
    SP<Material> mat0_{};
    SP<Material> mat1_{};

protected:
    VS_MAKE_MATERIAL_EVALUATOR(LobeSet)

public:
    AddMaterial() = default;
    explicit AddMaterial(const MaterialDesc &desc)
        : Material(desc),
          mat0_(Node::create_shared<Material>(*desc.mat0)),
          mat1_(Node::create_shared<Material>(*desc.mat1)) {}

    void initialize_slots(const vision::Material::Desc &desc) noexcept override {
        ensure_graph_ready();
        mat0_->initialize_attached(shared_graph(), *desc.mat0);
        mat1_->initialize_attached(shared_graph(), *desc.mat1);
    }
    VS_MAKE_PLUGIN_NAME_FUNC
    OC_ENCODABLE_FUNC(Material, *mat0_, *mat1_)
    VS_MAKE_GUI_STATUS_FUNC(Material, mat0_, mat1_)
    void render_sub_UI(Widgets *widgets) noexcept override {
        Material::render_sub_UI(widgets);
        widgets->use_tree(ocarina::format("mat0 {}", mat0_->impl_type()), [&] {
            mat0_->render_sub_UI(widgets);
        });
        widgets->use_tree(ocarina::format("mat1 {}", mat1_->impl_type()), [&] {
            mat1_->render_sub_UI(widgets);
        });
    }
    void prepare() noexcept override {
        Material::prepare();
        mat0_->prepare();
        mat1_->prepare();
    }
    [[nodiscard]] uint64_t compute_topology_hash() const noexcept override {
        return hash64(mat0_->topology_hash(), mat1_->topology_hash());
    }
    [[nodiscard]] UP<Lobe> create_lobe_set(const Interaction &it, const SampledWavelengths &swl) const noexcept override {
        return LobeSet::create_add(mat0_->create_lobe_set(it, swl),
                                   mat1_->create_lobe_set(it, swl));
    }
};

}// namespace vision

VS_MAKE_CLASS_CREATOR_HOTFIX(vision, AddMaterial)