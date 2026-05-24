//
// Created by Zero on 2023/6/1.
//

#pragma once

#include "base/denoiser.h"
#include "base/sensor/tonemapper.h"
#include "base/using.h"

namespace vision {
class Pipeline;
class Postprocessor {
private:
    using signature = void(Buffer<float4>, Buffer<float4>, bool);

private:
    Pipeline *rp_{};
    TToneMapper tone_mapper_{};
    ocarina::Shader<signature> tone_mapping_shader_;

public:
    explicit Postprocessor(Pipeline *rp);
    void set_tone_mapper(const TToneMapper & tone_mapper) noexcept {
        if (tone_mapper_ && tone_mapper->topology_hash() == tone_mapper_->topology_hash()) {
            return;
        }
        tone_mapper_ = tone_mapper;
        compile_tone_mapping();
    }
    void compile_tone_mapping() noexcept;
    void tone_mapping(BufferView<float4> input,
                      BufferView<float4> output,
                      bool gamma = false) noexcept;
};
}// namespace vision
