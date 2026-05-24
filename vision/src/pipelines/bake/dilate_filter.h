//
// Created by Zero on 2023/6/14.
//

#pragma once

#include "dsl/dsl.h"
#include "rhi/common.h"
#include "core/util/hash.h"
#include "base/mgr/global.h"
#include "base/using.h"

namespace vision {
class DilateFilter : public Toolkit {
private:
    int padding_{};
    using signature = void(Buffer<uint4>, Buffer<float4>, Buffer<float4>);
    Shader<signature> _shader;

public:
    explicit DilateFilter(int padding = 2);
    void set_padding(int padding) noexcept { padding_ = padding; }
    void compile() noexcept;
    template<typename... Args>
    [[nodiscard]] ocarina::ShaderInvoke operator()(Args &&...args) const noexcept {
        return _shader(OC_FORWARD(args)...);
    }
};

}// namespace vision