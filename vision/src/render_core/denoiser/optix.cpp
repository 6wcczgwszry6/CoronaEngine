//
// Created by Zero on 2023/5/30.
//
// NOTE: Offline denoise has been disabled.
// This file is kept for potential future re-implementation.

#include "base/denoiser.h"

#if 0  // OptiX offline denoise disabled

namespace vision {

class OptixDenoiser : public Denoiser {
public:
    explicit OptixDenoiser(const DenoiserDesc &desc)
        : Denoiser(desc){
    }
    VS_MAKE_PLUGIN_NAME_FUNC
};

}// namespace vision

VS_MAKE_CLASS_CREATOR(vision::OptixDenoiser)

#endif  // OptiX offline denoise disabled