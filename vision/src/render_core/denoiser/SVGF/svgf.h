#pragma once

#include "math/basic_types.h"
#include "dsl/dsl.h"
#include "base/denoiser.h"
#include "atrous.h"
#include "modulator.h"
#include "variance_estimator.h"
#include "prefilter.h"
#include "utils.h"
#include "base/using.h"

namespace vision::svgf {
class SVGF : public Denoiser, public GBufferCallback, public enable_shared_from_this<SVGF> {
public:
    RegistrableBuffer<SVGFDataDual> svgf_data;

private:
    HotfixSlot<SP<AtrousFilter>> atrous_{};
    HotfixSlot<SP<Modulator>> modulator_{};
    HotfixSlot<SP<VarianceEstimator>> variance_estimator_{};
    HotfixSlot<SP<Prefilter>> prefilter_{};

private:
    struct Params {
        float sigma_rt_{4.0f};
        float sigma_normal_{128.f};
        float sigma_depth_{1.0f};
        bool spatial_filter_{true};
        bool switch_{true};

        Params() = default;
        explicit Params(const DenoiserDesc &desc)
            : sigma_rt_(desc["sigma_rt"].as_float(4.0f)),
              sigma_normal_(desc["sigma_normal"].as_float(128.f)),
              sigma_depth_(desc["sigma_depth"].as_float(1.0f)),
              spatial_filter_(desc["spatial_filter"].as_bool(true)),
        //
        switch_(false) {}
    };
    Params params_;

public:
    SVGF() = default;
    explicit SVGF(const DenoiserDesc &desc)
        : Denoiser(desc),
          svgf_data(pipeline()->bindless_array()),
          params_(desc) {}

    void initialize_(const vision::NodeDesc &node_desc) noexcept override;
    void compute_GBuffer(const vision::RayState &rs, const vision::Interaction &it) noexcept override;

    VS_HOTFIX_MAKE_RESTORE(Denoiser, svgf_data,
                           atrous_, modulator_, variance_estimator_, prefilter_, params_)
    VS_MAKE_PLUGIN_NAME_FUNC

#define VS_MAKE_MEMBER_GETTER(member, modifier)                                             \
    [[nodiscard]] const auto modifier member() const noexcept { return params_.member##_; } \
    [[nodiscard]] auto modifier member() noexcept { return params_.member##_; }

    VS_MAKE_MEMBER_GETTER(sigma_rt, )
    VS_MAKE_MEMBER_GETTER(sigma_normal, )
    VS_MAKE_MEMBER_GETTER(sigma_depth, )
    VS_MAKE_MEMBER_GETTER(spatial_filter, )

#undef VS_MAKE_MEMBER_GETTER

    [[nodiscard]] AtrousFilter *atrous() noexcept { return atrous_.get(); }
    [[nodiscard]] const AtrousFilter *atrous() const noexcept { return atrous_.get(); }

    void prepare_buffers();
    void render_sub_UI(Widgets *widgets) noexcept override;
    [[nodiscard]] BufferView<SVGFDataDual> svgf_buffer() const noexcept;
    void prepare() noexcept override;
    void compile() noexcept override;
    void update_resolution(uint2 resolution) noexcept override;
    [[nodiscard]] CommandBatch dispatch(vision::RealTimeDenoiseInput &input) noexcept override;
    void set_enabled(bool enabled) noexcept override;
    [[nodiscard]] bool enabled() noexcept override;
};

}// namespace vision::svgf
