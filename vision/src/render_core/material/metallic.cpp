//
// Created by ling.zhu on 2025/3/15.
//

#include "base/import/param_schema.h"
#include "base/scattering/material.h"
#include "base/shader_graph/shader_node.h"
#include "base/mgr/scene.h"
#include "math/warp.h"

namespace vision {

/**
 Example material JSON:
 {
     "type" : "metallic",
     "name" : "MatMetallic",
     "param" : {
         "color" : {
             "channels" : "xyz",
             "node" : {
                 "type" : "number",
                 "param" : { "value" : [1.0, 1.0, 1.0] }
             }
         },
         "edge_tint" : {
             "channels" : "xyz",
             "node" : {
                 "type" : "number",
                 "param" : { "value" : [1.0, 1.0, 1.0] }
             }
         },
         "roughness" : {
             "channels" : "x",
             "node" : {
                 "type" : "number",
                 "param" : { "value" : 0.5 }
             }
         },
         "anisotropic" : {
             "channels" : "x",
             "node" : {
                 "type" : "number",
                 "param" : { "value" : 0.0 }
             }
         },
         "remapping_roughness" : true
     },
     "node_tab" : {}
 }
 */
class MetallicMaterial final : public Material {
private:
#define METALLIC_SLOTS(X)                                           \
    X(color, make_float3(1.f), Albedo, , 3u, false)                 \
    X(edge_tint, make_float3(1.f), Albedo, , 3u, false)             \
    X(roughness, 0.5f, Number, .set_range(0.0001f, 1.f), 1u, false) \
    X(anisotropic, 0.f, Number, .set_range(-1, 1), 1u, false)

#define METALLIC_DECLARE_SLOT_(name, val, tag, extra, dim, required) VS_MAKE_SLOT(name)
    METALLIC_SLOTS(METALLIC_DECLARE_SLOT_)
#undef METALLIC_DECLARE_SLOT_

    [[nodiscard]] static const ParamSchema &param_schema() noexcept {
        static const ParamSchema schema = [] {
            ParamSchema ret;
#define METALLIC_REGISTER_PARAM_(name, val, tag, extra, dim, required) ret.add_slot(#name, tag, dim, required);
            METALLIC_SLOTS(METALLIC_REGISTER_PARAM_)
#undef METALLIC_REGISTER_PARAM_
            ret.add_plain("remapping_roughness", ParamType::Bool);
            return ret;
        }();
        return schema;
    }
    bool remapping_roughness_{true};
    float alpha_threshold_{0.022};

protected:
    VS_MAKE_MATERIAL_EVALUATOR(MicrofacetLobe)
public:
    MetallicMaterial() = default;
    explicit MetallicMaterial(const MaterialDesc &desc)
        : Material(desc) {}

    void initialize_slots(const vision::Material::Desc &desc) noexcept override {
        Material::initialize_slots(desc);
        const ParamSchema &schema = param_schema();
        validate_params(desc, schema);
#define METALLIC_INIT_SLOT_(name, val, tag, extra, dim, required) VS_INIT_SLOT(name, val, tag) extra;
        METALLIC_SLOTS(METALLIC_INIT_SLOT_)
#undef METALLIC_INIT_SLOT_
    }

    void prepare() noexcept override {
        MetallicLobe::prepare();
    }

    VS_MAKE_PLUGIN_NAME_FUNC
    VS_HOTFIX_MAKE_RESTORE(Material, remapping_roughness_, alpha_threshold_)
    [[nodiscard]] UP<Lobe> create_lobe_set(const Interaction &it, const SampledWavelengths &swl) const noexcept override {
        auto shading_frame = compute_shading_frame(it, swl);
        SampledSpectrum color = color_.eval_albedo_spectrum(it, swl).sample;
        SampledSpectrum edge_tint = edge_tint_.eval_albedo_spectrum(it, swl).sample;
        Float roughness = ocarina::clamp(roughness_.evaluate(it, swl)->as_scalar(), 0.01f, 1.f);
        Float anisotropic = ocarina::clamp(anisotropic_.evaluate(it, swl)->as_scalar(), -0.9f, 0.9f);

        roughness = remapping_roughness_ ? roughness_to_alpha(roughness) : roughness;
        Float2 alpha = calculate_alpha<D>(roughness, anisotropic);
        Float alpha_min = min(alpha.x, alpha.y);
        Uint flag = select(alpha_min < alpha_threshold_, SurfaceData::NearSpec, SurfaceData::Glossy);
        auto microfacet = make_shared<GGXMicrofacet>(alpha.x, alpha.y);

        SP<FresnelF82Tint> fresnel_f82 = make_shared<FresnelF82Tint>(color, swl);
        fresnel_f82->init_from_F82(edge_tint);

        UP<MicrofacetReflection> metal_refl = make_unique<MicrofacetReflection>(color, swl, microfacet);
        return make_unique<MetallicLobe>(fresnel_f82, std::move(metal_refl), flag, shading_frame);
    }
};
}// namespace vision

VS_MAKE_CLASS_CREATOR_HOTFIX(vision, MetallicMaterial)