//
// Created by ling.zhu on 2025/6/25.
//

#include "base/import/param_schema.h"
#include "base/scattering/material.h"
#include "base/shader_graph/shader_node.h"
#include "base/mgr/scene.h"
#include "base/mgr/pipeline.h"

namespace vision {

class EmissionLobe : public Lobe {

};

/**
 Example material JSON:
 {
     "type" : "emission",
     "name" : "MatEmission",
     "param" : {
         "color" : {
             "channels" : "xyz",
             "node" : {
                 "type" : "number",
                 "param" : { "value" : [0.5, 0.5, 0.5] }
             }
         },
         "strength" : {
             "channels" : "x",
             "node" : {
                 "type" : "number",
                 "param" : { "value" : 0.5 }
             }
         }
     },
     "node_tab" : {}
 }
 */
class EmissionMaterial : public Material {
private:
#define EMISSION_ALWAYS_SLOTS(X) \
    X(color, make_float3(0.5f), Albedo, , 3u, false)

#define EMISSION_OPTIONAL_SLOTS(X) \
    X(strength, 0.5f, Number, .set_range(0.f, 1.f), 1u, false)

#define EMISSION_DECLARE_SLOT_(name, val, tag, extra, dim, required) VS_MAKE_SLOT(name)
    EMISSION_ALWAYS_SLOTS(EMISSION_DECLARE_SLOT_)
    EMISSION_OPTIONAL_SLOTS(EMISSION_DECLARE_SLOT_)
#undef EMISSION_DECLARE_SLOT_

    [[nodiscard]] static const ParamSchema &param_schema() noexcept {
        static const ParamSchema schema = [] {
            ParamSchema ret;
#define EMISSION_REGISTER_PARAM_(name, val, tag, extra, dim, required) ret.add_slot(#name, tag, dim, required);
            EMISSION_ALWAYS_SLOTS(EMISSION_REGISTER_PARAM_)
            EMISSION_OPTIONAL_SLOTS(EMISSION_REGISTER_PARAM_)
#undef EMISSION_REGISTER_PARAM_
            return ret;
        }();
        return schema;
    }

public:
    EmissionMaterial() = default;
    explicit EmissionMaterial(const MaterialDesc &desc)
        : Material(desc) {}

    void initialize_slots(const vision::Material::Desc &desc) noexcept override {
        Material::initialize_slots(desc);
        const ParamSchema &schema = param_schema();
        validate_params(desc, schema);
#define EMISSION_INIT_ALWAYS_(name, val, tag, extra, dim, required) VS_INIT_SLOT(name, val, tag) extra;
        EMISSION_ALWAYS_SLOTS(EMISSION_INIT_ALWAYS_)
#undef EMISSION_INIT_ALWAYS_
        if (desc.has_attr("strength")) {
#define EMISSION_INIT_OPTIONAL_(name, val, tag, extra, dim, required) VS_INIT_SLOT(name, val, tag) extra;
            EMISSION_OPTIONAL_SLOTS(EMISSION_INIT_OPTIONAL_)
#undef EMISSION_INIT_OPTIONAL_
        }
    }
    VS_MAKE_PLUGIN_NAME_FUNC
};

}// namespace vision