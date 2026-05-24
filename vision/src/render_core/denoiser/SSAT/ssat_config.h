//
// Created by Zero on 2025/01/26.
// SSAT (Sparse Spatial-Angular-Temporal) Light Field Denoiser Configuration
//

#pragma once

namespace vision::ssat {

/// Configuration constants for the SSAT light field denoiser
/// Based on the paper's methodology for 5D phase-space sparse signal reconstruction
struct SSATConfig {
    
    /// Phase 1: Disparity-Guided Adaptive Sampling
    struct Sampling {
        /// Default baseline fill rate ρ_base (analogous to stochastic checkerboard)
        static constexpr float kDefaultRhoBase = 0.5f;
        /// Minimum shear magnitude threshold
        static constexpr float kMinShearMagnitude = 0.01f;
        /// Maximum shear magnitude for clamping
        static constexpr float kMaxShearMagnitude = 10.0f;
        /// Default sensitivity coefficient α for shear-to-probability mapping
        static constexpr float kDefaultAlpha = 1.0f;
        /// Transfer function W scaling factor
        static constexpr float kShearTransferScale = 0.5f;
    };
    
    /// Phase 2: Unified Spatio-Angular Integration
    struct SpatialAngular {
        /// Minimum variance for numerical stability
        static constexpr float kMinVariance = 0.0001f;
        /// Depth weight scale factor for w_geo
        static constexpr float kDepthWeightScale = 1.0f;
        /// Maximum spatial filter radius
        static constexpr int kMaxSpatialRadius = 5;
        /// Default spatial filter radius
        static constexpr int kDefaultSpatialRadius = 3;
        /// Maximum angular samples per direction
        static constexpr int kMaxAngularSamples = 9;
        /// Default angular samples
        static constexpr int kDefaultAngularSamples = 5;
        /// Default luminance sigma for edge-stopping
        static constexpr float kDefaultSigmaLum = 3.0f;
        /// Default normal sigma for edge-stopping
        static constexpr float kDefaultSigmaNormal = 192.0f;
        /// Default depth-angular sigma for w_geo
        static constexpr float kDefaultSigmaDepthAngular = 1.0f;
        /// Beta coefficient for angular baseline penalty in w_geo
        static constexpr float kBetaAngular = 1.0f;
        /// B-spline 1D kernel weights for à-trous filtering
        static constexpr float kBSpline1D[3] = {0.375f, 0.25f, 0.0625f};
    };
    
    /// Phase 3: 5D Temporal Accumulation
    struct Temporal {
        /// Minimum blending factor α (lower = more history, 0.02 → ~50 effective frames)
        static constexpr float kMinAlpha = 0.02f;
        /// Maximum history length for EMA
        static constexpr float kMaxHistory = 128.f;
        /// Fast history for disocclusion
        static constexpr float kFastHistory = 4.f;
        /// Angular bandwidth ω_angular for strict history rejection
        static constexpr float kAngularBandwidth = 0.1f;
        /// Depth consistency threshold (relative)
        static constexpr float kDepthThreshold = 0.1f;
        /// Normal consistency threshold (dot product minimum)
        static constexpr float kNormalThreshold = 0.95f;
        /// Normal exponent for consistency check (unused with dot threshold)
        static constexpr float kNormalExp = 1.0f;
        /// Motion scale divisor for adaptive history
        static constexpr float kMotionScaleDivisor = 16.0f;
    };
    
    /// Sparse Gathering Operator Υ parameters
    struct Gather {
        /// Default spatial bandwidth σ_x
        static constexpr float kDefaultSigmaX = 2.0f;
        /// Default angular bandwidth σ_u
        static constexpr float kDefaultSigmaU = 0.5f;
        /// Epsilon for numerical stability in normalization
        static constexpr float kEpsilon = 1e-6f;
        /// Maximum neighbor search radius
        static constexpr int kMaxNeighborRadius = 2;
    };
    
    /// Ghosting and artifact rejection
    struct Ghosting {
        /// Color difference threshold for history rejection
        static constexpr float kColorDiffThreshold = 0.5f;
        /// Bright history ratio threshold
        static constexpr float kBrightHistoryRatio = 50.0f;
        /// Minimum luminance for bright history detection
        static constexpr float kBrightHistoryMinLum = 5.0f;
        /// Fast motion threshold in pixels
        static constexpr float kFastMotionThreshold = 8.0f;
    };
    
    /// Firefly suppression
    struct Firefly {
        /// Sigma multiplier for consistent history
        static constexpr float kSigmaMultiplierMin = 10.0f;
        static constexpr float kSigmaMultiplierMax = 20.0f;
        /// Minimum sigma for clamping
        static constexpr float kMinSigma = 0.5f;
        /// Mean multiplier for maximum luminance
        static constexpr float kMeanMultiplier = 100.0f;
        /// Clamp ratio for soft clamping
        static constexpr float kClampRatio = 0.95f;
    };
};

}// namespace vision::ssat
