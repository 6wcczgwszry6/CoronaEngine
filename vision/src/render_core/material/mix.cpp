//
// Created by Zero on 2023/5/5.
//

#include "base/import/param_schema.h"
#include "base/scattering/material.h"
#include "base/shader_graph/shader_node.h"
#include "base/mgr/scene.h"
#include "base/mgr/pipeline.h"

namespace vision {

/**
 Example material JSON:
 {
     "type" : "mix",
     "name" : "MatMix",
     "param" : {
         "frac" : {
             "channels" : "x",
             "node" : {
                 "type" : "number",
                 "param" : { "value" : 0.5 }
             }
         },
         "mat0" : {
             "type" : "diffuse",
             "name" : "MatMixBase",
             "param" : {
                 "color" : { "channels" : "xyz", "node" : { "type" : "number", "param" : { "value" : [0.5, 0.5, 0.5] } } },
                 "sigma" : { "channels" : "x", "node" : { "type" : "number", "param" : { "value" : 0.3 } } }
             },
             "node_tab" : {}
         },
         "mat1" : {
             "type" : "glass",
             "name" : "MatMixCoat",
             "param" : {
                 "material_name" : "BK7",
                 "roughness" : { "channels" : "x", "node" : { "type" : "number", "param" : { "value" : 0.5 } } }
             },
             "node_tab" : {}
         }
     },
     "node_tab" : {}
 }
 */
class MixMaterial final : public Material {
private:
#define MIX_SLOTS(X) \
    X(frac, 0.5f, Number, , 1u, false)

#define MIX_DECLARE_SLOT_(name, val, tag, extra, dim, required) VS_MAKE_SLOT(name)
    MIX_SLOTS(MIX_DECLARE_SLOT_)
#undef MIX_DECLARE_SLOT_

    [[nodiscard]] static const ParamSchema &param_schema() noexcept {
        static const ParamSchema schema = [] {
            ParamSchema ret;
#define MIX_REGISTER_PARAM_(name, val, tag, extra, dim, required) ret.add_slot(#name, tag, dim, required);
            MIX_SLOTS(MIX_REGISTER_PARAM_)
#undef MIX_REGISTER_PARAM_
            return ret;
        }();
        return schema;
    }

    HotfixSlot<SP<Material>> mat0_{};
    HotfixSlot<SP<Material>> mat1_{};

protected:
    VS_MAKE_MATERIAL_EVALUATOR(LobeSet)

public:
    MixMaterial() = default;
    explicit MixMaterial(const MaterialDesc &desc)
        : Material(desc),
          mat0_(Node::create_shared<Material>(*desc.mat0)),
          mat1_(Node::create_shared<Material>(*desc.mat1)) {
    }

    void initialize_slots(const vision::Material::Desc &desc) noexcept override {
        ensure_graph_ready();
        mat0_->initialize_attached(shared_graph(), *desc.mat0);
        mat1_->initialize_attached(shared_graph(), *desc.mat1);
        const ParamSchema &schema = param_schema();
        validate_params(desc, schema);
    #define MIX_INIT_SLOT_(name, val, tag, extra, dim, required) VS_INIT_SLOT(name, val, tag) extra;
        MIX_SLOTS(MIX_INIT_SLOT_)
    #undef MIX_INIT_SLOT_
    }

    VS_MAKE_PLUGIN_NAME_FUNC
    VS_HOTFIX_MAKE_RESTORE(Material, frac_, mat0_, mat1_)
    VS_MAKE_GUI_STATUS_FUNC(Material, frac_, mat0_, mat1_)
    OC_ENCODABLE_FUNC(Material, *mat0_, *mat1_)

    [[nodiscard]] uint64_t compute_topology_hash() const noexcept override {
        return hash64(mat0_->topology_hash(), mat1_->topology_hash(), frac_.topology_hash());
    }
    void render_sub_UI(Widgets *widgets) noexcept override {
        Material::render_sub_UI(widgets);
        widgets->use_tree(ocarina::format("mat0 {}", mat0_->impl_type()), [&] {
            mat0_->render_sub_UI(widgets);
        });
        widgets->use_tree(ocarina::format("mat1 {}", mat1_->impl_type()), [&] {
            mat1_->render_sub_UI(widgets);
        });
    }
    [[nodiscard]] uint64_t compute_hash() const noexcept override {
        return hash64(mat0_->hash(), mat1_->hash(), frac_.hash());
    }

    void prepare() noexcept override {
        Material::prepare();
        frac_->prepare();
        mat0_->prepare();
        mat1_->prepare();
    }

    [[nodiscard]] UP<Lobe> create_lobe_set(const Interaction &it, const SampledWavelengths &swl) const noexcept override {
        Float frac = frac_.evaluate(it, swl).array[0];
        auto ret = LobeSet::create_mix(frac, mat0_->create_lobe_set(it, swl),
                                       mat1_->create_lobe_set(it, swl));
        return ret;
    }
};

}// namespace vision

VS_MAKE_CLASS_CREATOR_HOTFIX(vision, MixMaterial)