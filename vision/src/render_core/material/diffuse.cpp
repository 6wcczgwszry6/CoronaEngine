//
// Created by Zero on 09/09/2022.
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
     "type" : "diffuse",
     "name" : "MatDiffuse",
     "param" : {
         "color" : {
             "channels" : "xyz",
             "node" : {
                 "type" : "number",
                 "param" : { "value" : [0.5, 0.5, 0.5] }
             }
         },
         "sigma" : {
             "channels" : "x",
             "node" : {
                 "type" : "number",
                 "param" : { "value" : 0.3 }
             }
         }
     },
     "node_tab" : {}
 }
 */
class DiffuseMaterial final : public Material {
private:
#define DIFFUSE_SLOTS(X)                                          \
    X(color, make_float3(0.5f), Albedo, , 3u, false)              \
    X(sigma, 0.3f, Number, .set_range(0.f, 1.f), 1u, false)

#define DIFFUSE_DECLARE_SLOT_(name, val, tag, extra, dim, required) VS_MAKE_SLOT(name)
    DIFFUSE_SLOTS(DIFFUSE_DECLARE_SLOT_)
#undef DIFFUSE_DECLARE_SLOT_

    [[nodiscard]] static const ParamSchema &param_schema() noexcept {
        static const ParamSchema schema = [] {
            ParamSchema ret;
#define DIFFUSE_REGISTER_PARAM_(name, val, tag, extra, dim, required) ret.add_slot(#name, tag, dim, required);
            DIFFUSE_SLOTS(DIFFUSE_REGISTER_PARAM_)
#undef DIFFUSE_REGISTER_PARAM_
            return ret;
        }();
        return schema;
    }

protected:
    VS_MAKE_MATERIAL_EVALUATOR(DiffuseLobe)

public:
    [[nodiscard]] UP<Lobe> create_lobe_set(const Interaction &it,
                                           const SampledWavelengths &swl) const noexcept override {
        auto shading_frame = compute_shading_frame(it, swl);
        SampledSpectrum kr = color_.eval_albedo_spectrum(it, swl).sample;
        if (sigma_) {
            Float sigma = sigma_.evaluate(it, swl)->as_scalar();
            return make_unique<DiffuseLobe>(kr, sigma, swl, shading_frame);
        }
        return make_unique<DiffuseLobe>(kr, swl, shading_frame);
    }
    [[nodiscard]] bool enable_delta() const noexcept override { return false; }
    bool render_UI(Widgets *widgets) noexcept override {
        Material::render_UI(widgets);
        return true;
    }
    DiffuseMaterial() = default;
    explicit DiffuseMaterial(const MaterialDesc &desc)
        : Material(desc) {}

    void initialize_slots(const vision::Material::Desc &desc) noexcept override {
        Material::initialize_slots(desc);
        const ParamSchema &schema = param_schema();
        validate_params(desc, schema);
    #define DIFFUSE_INIT_SLOT_(name, val, tag, extra, dim, required) VS_INIT_SLOT(name, val, tag) extra;
        DIFFUSE_SLOTS(DIFFUSE_INIT_SLOT_)
    #undef DIFFUSE_INIT_SLOT_
    }
    VS_MAKE_PLUGIN_NAME_FUNC
};
}// namespace vision

VS_MAKE_CLASS_CREATOR_HOTFIX(vision, DiffuseMaterial)