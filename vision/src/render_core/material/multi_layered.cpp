//
// Created by Zero on 2023/8/28.
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
     "type" : "multi_layered",
     "name" : "MatMultiLayered",
     "param" : {
         "thickness_" : {
             "channels" : "x",
             "node" : {
                 "type" : "number",
                 "param" : { "value" : 1.0 }
             }
         },
         "mat0" : {
             "type" : "diffuse",
             "name" : "MatMultiLayeredBottom",
             "param" : {
                 "color" : { "channels" : "xyz", "node" : { "type" : "number", "param" : { "value" : [0.5, 0.5, 0.5] } } },
                 "sigma" : { "channels" : "x", "node" : { "type" : "number", "param" : { "value" : 0.3 } } }
             },
             "node_tab" : {}
         },
         "mat1" : {
             "type" : "diffuse",
             "name" : "MatMultiLayeredTop",
             "param" : {
                 "color" : { "channels" : "xyz", "node" : { "type" : "number", "param" : { "value" : [0.5, 0.5, 0.5] } } },
                 "sigma" : { "channels" : "x", "node" : { "type" : "number", "param" : { "value" : 0.3 } } }
             },
             "node_tab" : {}
         }
     },
     "node_tab" : {}
 }
 */
class MultiLayeredMaterial : public Material {
private:
    static constexpr float float_min = std::numeric_limits<float>::min();

#define MULTI_LAYERED_SLOTS(X) \
    X(thickness_, 1.f, Number, 1u, false)

private:
    EncodedData<float> factor_{float_min};
    [[nodiscard]] static const ParamSchema &param_schema() noexcept {
        static const ParamSchema schema = [] {
            ParamSchema ret;
#define MULTI_LAYERED_REGISTER_PARAM_(name, val, tag, dim, required) ret.add_slot(#name, tag, dim, required);
            MULTI_LAYERED_SLOTS(MULTI_LAYERED_REGISTER_PARAM_)
#undef MULTI_LAYERED_REGISTER_PARAM_
            return ret;
        }();
        return schema;
    }

    ShaderNodeSlot thickness_;
    SP<Material> bottom_{};
    SP<Material> top_{};

public:
    explicit MultiLayeredMaterial(const MaterialDesc &desc)
        : Material(desc),
          thickness_(ShaderNodeSlot::create_slot(desc.slot("thickness_", 1.f, Number))),
          bottom_(Node::create_shared<Material>(*desc.mat0)),
                    top_(Node::create_shared<Material>(*desc.mat1)) {
                validate_params(desc, param_schema());
        }
    void initialize_slots(const vision::Material::Desc &desc) noexcept override {
        ensure_graph_ready();
        thickness_.set(graph().construct_slot(desc, "thickness_", 1.f, Number));
        bottom_->initialize_attached(shared_graph(), *desc.mat0);
        top_->initialize_attached(shared_graph(), *desc.mat1);
    }
    VS_MAKE_PLUGIN_NAME_FUNC
    void prepare() noexcept override {
        Material::prepare();
        bottom_->prepare();
        top_->prepare();
        thickness_->prepare();
    }
};

}// namespace vision