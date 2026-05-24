//
// Created by Zero on 26/11/2022.
//

#include "base/illumination/light.h"
#include "base/mgr/pipeline.h"

namespace vision {

/**
 Example light JSON:
 {
     "type" : "spot",
     "param" : {
         "angle" : 20,
         "falloff" : 2,
         "ratio" : 1,
         "color" : {
             "channels" : "xyz",
             "node" : {
                 "type" : "number",
                 "param" : {
                     "value" : [1, 1, 1]
                 }
             }
         },
         "o2w" : {
             "type" : "look_at",
             "param" : {
                 "position" : [0.5, 1.9, 0],
                 "up" : [0, 1, 0],
                 "target_pos" : [0.7, 0.9, 0]
             }
         },
         "scale" : 3,
         "strength" : {
             "channels" : "x",
             "node" : {
                 "type" : "number",
                 "param" : {
                     "value" : 3
                 }
             }
         }
     }
 }
 */
class SpotLight final : public IPointLight {
private:
    EncodedData<float4x4> o2w_;
    EncodedData<float> angle_;
    // falloff angle range
    EncodedData<float> falloff_;
    EncodedData<float> ratio_;

private:
    [[nodiscard]] static float ratio_to_ui_anisotropic(float ratio) noexcept {
        // Map the stored ellipse aspect ratio back to a symmetric UI control.
        // ratio = 1 means a circular cone, while positive/negative UI values
        // stretch one axis or the other like material anisotropy controls.
        ratio = ocarina::max(ratio, 1e-4f);
        if (ratio >= 1.f) {
            return 1.f / std::sqrt(ratio) - 1.f;
        }
        return 1.f - std::sqrt(ratio);
    }

    [[nodiscard]] static float ui_anisotropic_to_ratio(float anisotropic) noexcept {
        anisotropic = ocarina::clamp(anisotropic, -.95f, .95f);
        if (anisotropic >= 0.f) {
            float scale = 1.f - anisotropic;
            return scale * scale;
        }
        float scale = 1.f + anisotropic;
        return 1.f / (scale * scale);
    }

    [[nodiscard]] bool use_projected_color() const noexcept {
        // Elliptic spot mode is needed when the cone is not circular or when
        // color varies over uv, because both cases require 2D projection.
        return ocarina::abs(ratio_.hv() - 1.f) > 1e-4f || !color_->is_uniform();
    }

    [[nodiscard]] Float falloff(Float cos_theta) const noexcept {
        Float falloff_start = max(0.f, *angle_ - *falloff_);
        Float cos_angle = cos(*angle_);
        Float cos_falloff_start = cos(falloff_start);
        cos_theta = clamp(cos_theta, cos_angle, cos_falloff_start);
        Float factor = (cos_theta - cos_angle) / (cos_falloff_start - cos_angle);
        Float ret = Pow<4>(factor);
        return ret;
    }

    [[nodiscard]] Float elliptic_falloff(Float radial) const noexcept {
        // radial is the distance in normalized ellipse space:
        // radial = 1 sits on the outer ellipse boundary, and the inner radius
        // is computed from the same angle/falloff pair as the circular spot.
        Float outer_radius = 1.f;
        Float inner_angle = max(0.f, *angle_ - *falloff_);
        Float inner_radius = tan(inner_angle) / tan(*angle_);
        if (falloff_.hv() <= 1e-4f) {
            return select(radial <= outer_radius, 1.f, 0.f);
        }
        radial = clamp(radial, inner_radius, outer_radius);
        Float factor = (outer_radius - radial) / (outer_radius - inner_radius);
        return Pow<4>(factor);
    }

public:
    SpotLight() = default;
    explicit SpotLight(const LightDesc &desc)
        : IPointLight(desc),
          o2w_(IPointLight::resolve_o2w(desc)),
          angle_(radians(ocarina::clamp(desc["angle"].as_float(45.f), 1.f, 89.f))),
          falloff_(radians(ocarina::clamp(desc["falloff"].as_float(10.f), 0.f, angle_.hv()))),
          ratio_(ocarina::max(desc["ratio"].as_float(1.f), 1e-4f)) {}
    OC_ENCODABLE_FUNC(IPointLight, o2w_, angle_, falloff_, ratio_)
    VS_HOTFIX_MAKE_RESTORE(IPointLight, o2w_, angle_, falloff_, ratio_)
    VS_MAKE_PLUGIN_NAME_FUNC
    void render_sub_UI(Widgets *widgets) noexcept override {
        IPointLight::render_sub_UI(widgets);
        changed_ |= widgets->slider_float("angle", &angle_.hv(), radians(1.f), radians(89.f));
        changed_ |= widgets->slider_float("fall off", &falloff_.hv(), 0.001, angle_.hv());
        float anisotropic = ratio_to_ui_anisotropic(ratio_.hv());
        if (widgets->slider_float("anisotropic", &anisotropic, -.95f, .95f)) {
            ratio_.hv() = ui_anisotropic_to_ratio(anisotropic);
            changed_ = true;
        }
    }
    [[nodiscard]] float3 power() const noexcept override {
        return 2 * Pi * average() * (1 - .5f * (angle_.hv() * 2 + falloff_.hv()));
    }
    [[nodiscard]] Float3 position() const noexcept override { return o2w_position(*o2w_); }
    [[nodiscard]] float3 &host_position() noexcept override {
        return host_o2w_position(o2w_.hv());
    }
    [[nodiscard]] Float3 direction(const LightSampleContext &p_ref) const noexcept override {
        return o2w_direction(*o2w_);
    }
    [[nodiscard]] SampledSpectrum Le(const LightSampleContext &p_ref,
                                     const LightEvalContext &p_light,
                                     const SampledWavelengths &swl) const noexcept override {
        Float3 w_un = p_ref.pos - position();
        Float d2 = length_squared(w_un);
        if (!use_projected_color()) {
            Float3 w = normalize(w_un);
            SampledSpectrum value = color_.eval_illumination_spectrum(p_light.uv, swl).sample * scale();
            return value / d2 * falloff(dot(direction(p_ref), w));
        }

        // Transform the shading point into the light's local frame where the
        // spot always points along +Z. This turns ellipse testing into a local
        // 2D problem on the z=1 projection plane.
        Float3 local_p = transform_point(inverse(*o2w_), p_ref.pos);
        Bool valid = local_p.z > 0.f;

        // Perspective-project the point onto the canonical spotlight plane.
        Float2 projected = local_p.xy() / local_p.z;

        // ratio stretches the x-axis relative to y, so the circular cone test
        // becomes an ellipse test after normalizing by (tan_x, tan_y).
        Float tan_y = tan(*angle_);
        Float tan_x = *ratio_ * tan_y;
        Float2 normalized = projected / make_float2(tan_x, tan_y);

        // radial is the ellipse-space radius. radial <= 1 means the point is
        // inside the outer cone, and the same normalized coordinates also map
        // directly to a [0, 1] uv domain for textured/projected color.
        Float radial = length(normalized);
        Float2 uv = normalized * 0.5f + 0.5f;
        valid = valid && radial <= 1.f;
        SampledSpectrum value = color_.eval_illumination_spectrum(uv, swl).sample * scale();
        return select(valid, 1.f, 0.f) * value / d2 * elliptic_falloff(radial);
    }
};
}// namespace vision

VS_MAKE_CLASS_CREATOR_HOTFIX(vision, SpotLight)