//
// Created by Zero on 2025/01/26.
// 5D Phase Space Coordinate System for Light Field
//
// Based on the two-plane parameterization L: Ω × Π → R³
// where Ω is the Display Plane and Π is the Viewing Plane
//

#pragma once

#include "math/basic_types.h"
#include "dsl/dsl.h"
#include "base/sensor/light_field_types.h"

namespace vision::ssat {

// Use common light field types from base
using vision::LenticularParams;
using vision::LightFieldGeometry;

// ============================================================================
// Phase Space Coordinate Structure
// ============================================================================

/// 4D Phase-Space coordinate (x, u) representing a point in Ω × Π
/// x ∈ Ω: Position on the Display Plane (sub-pixel location)
/// u ∈ Π: Angular coordinate on the Viewing Plane
/// 
/// The full 5D phase space includes time T, handled separately in temporal transport
struct PhaseSpaceCoord {
    float2 x{};  // Display Plane coordinate (spatial)
    float2 u{};  // Viewing Plane coordinate (angular)
};

}// namespace vision::ssat

// GPU-side structure definition with DSL operations
OC_STRUCT(vision::ssat, PhaseSpaceCoord, x, u) {
    /// Get spatial coordinate x ∈ Ω
    [[nodiscard]] Float2 spatial() const noexcept { return x; }
    /// Get angular coordinate u ∈ Π  
    [[nodiscard]] Float2 angular() const noexcept { return u; }
    
    /// Set spatial coordinate
    void set_spatial(const Float2 &val) noexcept { x = val; }
    /// Set angular coordinate
    void set_angular(const Float2 &val) noexcept { u = val; }
    
    /// Create a new coordinate with offset spatial position
    [[nodiscard]] Var<vision::ssat::PhaseSpaceCoord> offset_spatial(const Float2 &delta) const noexcept {
        Var<vision::ssat::PhaseSpaceCoord> result;
        result.x = x + delta;
        result.u = u;
        return result;
    }
    
    /// Create a new coordinate with offset angular position
    [[nodiscard]] Var<vision::ssat::PhaseSpaceCoord> offset_angular(const Float2 &delta) const noexcept {
        Var<vision::ssat::PhaseSpaceCoord> result;
        result.x = x;
        result.u = u + delta;
        return result;
    }
    
    /// Compute squared distance to another coordinate in phase space
    /// Uses separable metric: d² = ||x - x'||² / σ_x² + ||u - u'||² / σ_u²
    [[nodiscard]] Float phase_distance_sq(const Var<vision::ssat::PhaseSpaceCoord> &other,
                                          const Float &sigma_x, const Float &sigma_u) const noexcept {
        Float2 dx = x - other.x;
        Float2 du = u - other.u;
        Float spatial_dist_sq = dot(dx, dx) / (sigma_x * sigma_x);
        Float angular_dist_sq = dot(du, du) / (sigma_u * sigma_u);
        return spatial_dist_sq + angular_dist_sq;
    }
    
    /// Compute the separable anisotropic kernel weight κ(C, Q)
    /// κ = exp(-||x - x'||² / σ_x²) · exp(-||u - u'||² / σ_u²)
    [[nodiscard]] Float kernel_weight(const Var<vision::ssat::PhaseSpaceCoord> &other,
                                      const Float &sigma_x, const Float &sigma_u) const noexcept {
        Float2 dx = x - other.x;
        Float2 du = u - other.u;
        Float w_spatial = exp(-dot(dx, dx) / (sigma_x * sigma_x));
        Float w_angular = exp(-dot(du, du) / (sigma_u * sigma_u));
        return w_spatial * w_angular;
    }
};

namespace vision::ssat {
using namespace ocarina;

using PhaseSpaceCoordVar = Var<PhaseSpaceCoord>;

// ============================================================================
// Phase Space Coordinate Factory Functions
// ============================================================================

/// Create a phase space coordinate from spatial and angular components
[[nodiscard]] inline PhaseSpaceCoordVar make_phase_coord(const Float2 &spatial, const Float2 &angular) noexcept {
    PhaseSpaceCoordVar coord;
    coord.x = spatial;
    coord.u = angular;
    return coord;
}

/// Create a zero-initialized phase space coordinate
[[nodiscard]] inline PhaseSpaceCoordVar make_phase_coord_zero() noexcept {
    PhaseSpaceCoordVar coord;
    coord.x = make_float2(0.f);
    coord.u = make_float2(0.f);
    return coord;
}

}// namespace vision::ssat
