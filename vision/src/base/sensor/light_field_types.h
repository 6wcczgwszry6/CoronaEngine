//
// Created by Zero on 2025/01/26.
// Common Light Field Types - shared between LightFieldFrameBuffer, SSAT denoiser, etc.
//

#pragma once

#include "math/basic_types.h"
#include "dsl/dsl.h"

namespace vision {
using namespace ocarina;

// ============================================================================
// Light Field Parameter Structures
// ============================================================================

/// Lenticular interlacing parameters (from LightFieldArray.js)
/// Note: Using float for all parameters to ensure compatibility with OC_STRUCT macro
struct LenticularParams {
    float pe{19.1813f};    // Period
    float angle{0.2305f};  // Slant angle in radians
    float offset{14.1171f};// Offset
    float num_views{60.f}; // Number of views
    float res_w{32.f};     // Pixel resolution width
    float res_h{32.f};     // Pixel resolution height
};

/// Light field geometry parameters
struct LightFieldGeometry {
    float d_f{20.f};            // Focal distance (camera array to focal plane) = D_opt = z_ref
    float fov_h_deg{45.f};      // Horizontal FOV (degrees)
    float aspect{1.77f};        // Aspect ratio
    float array_angle_deg{30.f};// Camera array span angle (degrees)
    float W_f{0.f};             // Focal plane width (derived)
    float H_f{0.f};             // Focal plane height (derived)
};

}// namespace vision

// GPU-side struct definitions
// Custom macro expansion that:
// 1. Does NOT use OC_MAKE_PARAM_STRUCT (allows Var<T> copy construction in DSL contexts)
// 2. Does NOT generate OC_MAKE_STRUCT_SOA_VAR/OC_MAKE_STRUCT_SOA_VIEW (avoids invalid TBuffer instantiation)
// This is a hybrid approach to get the best of both OC_STRUCT and OC_PARAM_STRUCT.
// clang-format off
OC_MAKE_STRUCT_REFLECTION(vision::LenticularParams, pe, angle, offset, num_views, res_w, res_h)
OC_MAKE_STRUCT_DESC(vision::LenticularParams, pe, angle, offset, num_views, res_w, res_h)
OC_MAKE_COMPUTABLE_BODY(vision::LenticularParams, pe, angle, offset, num_views, res_w, res_h)
OC_STRUCT_ALIAS(vision, LenticularParams)
OC_MAKE_PROXY(vision::LenticularParams) {};

OC_MAKE_STRUCT_REFLECTION(vision::LightFieldGeometry, d_f, fov_h_deg, aspect, array_angle_deg, W_f, H_f)
OC_MAKE_STRUCT_DESC(vision::LightFieldGeometry, d_f, fov_h_deg, aspect, array_angle_deg, W_f, H_f)
OC_MAKE_COMPUTABLE_BODY(vision::LightFieldGeometry, d_f, fov_h_deg, aspect, array_angle_deg, W_f, H_f)
OC_STRUCT_ALIAS(vision, LightFieldGeometry)
OC_MAKE_PROXY(vision::LightFieldGeometry) {};
// clang-format on

namespace vision {

// ============================================================================
// Light Field FrameBuffer Interface
// ============================================================================

/// Interface for accessing light field parameters from FrameBuffer
/// Implemented by LightFieldFrameBuffer, used by denoisers and integrators
class ILightFieldFrameBuffer {
public:
    virtual ~ILightFieldFrameBuffer() = default;
    
    /// Get lenticular interlacing parameters
    [[nodiscard]] virtual const LenticularParams& lenticular_params() const noexcept = 0;
    
    /// Get light field geometry parameters
    [[nodiscard]] virtual const LightFieldGeometry& geometry_params() const noexcept = 0;
    
    /// Get current local-to-world transform (includes camera transform)
    [[nodiscard]] virtual float4x4 get_current_l2w() const noexcept = 0;
    
    /// Get previous frame's local-to-world transform (for temporal reprojection)
    [[nodiscard]] virtual float4x4 get_prev_l2w() const noexcept = 0;
};

}// namespace vision
