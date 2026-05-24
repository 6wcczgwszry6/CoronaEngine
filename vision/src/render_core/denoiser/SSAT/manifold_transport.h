//
// Created by Zero on 2025/01/26.
// Manifold Transport Operator Ψ for Light Field
//
// Implements three transport mechanisms on the 5D phase space manifold:
// 1. Ψ_spatial: Intra-slice spatial transport (geometry-agnostic)
// 2. Ψ_ang: Inter-slice angular transport (EPI shear)
// 3. Ψ_temp: Temporal transport (phase-space ray back-projection)
//

#pragma once

#include "math/basic_types.h"
#include "dsl/dsl.h"
#include "base/mgr/global.h"
#include "base/mgr/pipeline.h"
#include "phase_space.h"
#include "utils.h"

namespace vision::ssat {
using namespace ocarina;

// ============================================================================
// Manifold Transport Operator Ψ
// ============================================================================

/// Static DSL functions implementing the Manifold Transport Operator
/// These are designed to be called within GPU kernels
class ManifoldTransport {
public:
    // ========================================================================
    // Ψ_spatial: Intra-Slice Spatial Transport
    // ========================================================================
    
    /// Spatial transport within a fixed angular slice
    /// Ψ_spatial(p, Δx) = (x_p + Δx, u_p)
    /// 
    /// This is geometry-agnostic; discontinuities are handled by feature-based
    /// rejection during integration (weight computation)
    /// 
    /// @param src Source phase-space coordinate
    /// @param delta_x Spatial offset in display plane coordinates
    /// @return Transported phase-space coordinate
    [[nodiscard]] static PhaseSpaceCoordVar spatial_transport(
        const PhaseSpaceCoordVar &src,
        const Float2 &delta_x) noexcept {
        
        PhaseSpaceCoordVar result;
        result.x = src.x + delta_x;
        result.u = src.u;  // Angular coordinate unchanged
        return result;
    }
    
    // ========================================================================
    // Ψ_ang: Inter-Slice Angular Transport (EPI Shear)
    // ========================================================================
    
    /// Compute signed disparity δ(z) = 1/z - 1/z_ref
    /// This captures the characteristic EPI shear structure
    /// 
    /// @param depth Surface depth z
    /// @param z_ref Reference depth (typically D_opt, the focal distance)
    /// @return Signed disparity value
    [[nodiscard]] static Float disparity(const Float &depth, const Float &z_ref) noexcept {
        Float safe_depth = max(depth, 0.001f);
        Float safe_z_ref = max(z_ref, 0.001f);
        return 1.f / safe_depth - 1.f / safe_z_ref;
    }
    
    /// Angular transport across divergent angular slices using EPI shear
    /// Ψ_ang(p, Δu; z) = (x_p + β·Δu·δ(z), u_p + Δu)
    /// 
    /// This formulation captures automultiscopic geometry:
    /// - On-screen content (z = z_ref): δ = 0, no spatial shift
    /// - Off-screen content: shears proportionally to inverse depth deviation
    /// 
    /// @param src Source phase-space coordinate
    /// @param delta_u Angular offset on viewing plane
    /// @param depth Surface depth at the source point
    /// @param z_ref Reference depth (focal plane = ZPP = D_opt)
    /// @param beta Projection scale factor (typically based on geometry)
    /// @return Transported phase-space coordinate
    [[nodiscard]] static PhaseSpaceCoordVar angular_transport(
        const PhaseSpaceCoordVar &src,
        const Float2 &delta_u,
        const Float &depth,
        const Float &z_ref,
        const Float &beta) noexcept {
        
        // Compute disparity-induced spatial shift
        Float disp = disparity(depth, z_ref);
        Float2 spatial_shift = beta * delta_u * disp;
        
        PhaseSpaceCoordVar result;
        result.x = src.x + spatial_shift;
        result.u = src.u + delta_u;
        return result;
    }
    
    /// Combined spatial-angular transport (composition of Ψ_spatial and Ψ_ang)
    /// C_target = Ψ_ang(Ψ_spatial(p, Δx), Δu; z)
    /// 
    /// This is the key operation for unified spatio-angular integration
    /// 
    /// @param src Source phase-space coordinate
    /// @param delta_x Spatial offset
    /// @param delta_u Angular offset
    /// @param depth Surface depth
    /// @param z_ref Reference depth
    /// @param beta Projection scale factor
    /// @return Target phase-space coordinate after combined transport
    [[nodiscard]] static PhaseSpaceCoordVar spatial_angular_transport(
        const PhaseSpaceCoordVar &src,
        const Float2 &delta_x,
        const Float2 &delta_u,
        const Float &depth,
        const Float &z_ref,
        const Float &beta) noexcept {
        
        // First apply spatial transport
        PhaseSpaceCoordVar after_spatial = spatial_transport(src, delta_x);
        // Then apply angular transport
        return angular_transport(after_spatial, delta_u, depth, z_ref, beta);
    }
    
    // ========================================================================
    // Ψ_temp: Temporal Transport (Phase-Space Ray Back-Projection)
    // ========================================================================
    
    /// Temporal transport via phase-space ray back-projection
    /// Given surface intersection P_surf and world-space velocity v_world:
    /// 1. Estimate previous position: P_prev = P_surf - v_world * Δt
    /// 2. Construct historical query ray R_prev along preserved direction -d_p
    /// 3. Intersect R_prev with previous parameterization planes
    /// 
    /// This preserves world-space angular consistency, mitigating aliasing
    /// on non-Lambertian surfaces.
    /// 
    /// @param surface_pos Current surface intersection point in world space
    /// @param world_velocity World-space velocity vector
    /// @param delta_t Time step (typically 1.0 for frame-to-frame)
    /// @param ray_dir Current ray direction (for angular consistency)
    /// @param prev_w2l Previous frame's world-to-local transform
    /// @param geom Light field geometry parameters
    /// @return Historical phase-space coordinate (x', u') on previous frame
    [[nodiscard]] static PhaseSpaceCoordVar temporal_transport(
        const Float3 &surface_pos,
        const Float3 &world_velocity,
        const Float &delta_t,
        const Float3 &ray_dir,
        const Float4x4 &prev_w2l,
        Var<LightFieldGeometry> geom) noexcept {
        
        // 1. Estimate previous surface position
        Float3 prev_surface_pos = surface_pos - world_velocity * delta_t;
        
        // 2. Transform to previous frame's local coordinates
        Float3 prev_local_pos = (prev_w2l * make_float4(prev_surface_pos, 1.f)).xyz();
        
        // 3. Compute where this point projects onto the display plane (Ω)
        // The display plane is at z=0 in local coordinates
        // Project along viewing direction to z=0
        Float z_safe = max(prev_local_pos.z, 0.001f);
        Float scale_to_display = -prev_local_pos.z / max(abs(ray_dir.z), 0.001f);
        
        // For phase-space, we need the focal plane projection
        Float d_f = geom.d_f;
        Float W_f = geom.W_f;
        Float H_f = geom.H_f;
        
        // Project to focal plane (z = d_f)
        Float focal_scale = d_f / z_safe;
        Float focal_x = prev_local_pos.x * focal_scale;
        Float focal_y = prev_local_pos.y * focal_scale;
        
        // Convert focal plane coordinates to normalized display coordinates
        // focal_x ∈ [-W_f/2, W_f/2] → x ∈ [0, res_w)
        Float x_normalized = (focal_x + W_f / 2.f) / W_f;
        Float y_normalized = (H_f / 2.f - focal_y) / H_f;
        
        // 4. Compute angular coordinate on viewing plane (Π)
        // Transform ray direction to local space and find viewing plane intersection
        Float3 local_ray_dir = normalize((prev_w2l * make_float4(ray_dir, 0.f)).xyz());
        
        // Viewing plane is at z = d_f (same as focal plane in our parameterization)
        // Angular coordinate u is the intersection point on this plane
        Float t_viewing = (d_f - prev_local_pos.z) / max(abs(local_ray_dir.z), 0.001f);
        Float3 viewing_intersection = prev_local_pos + local_ray_dir * t_viewing;
        
        // Convert to normalized angular coordinates
        Float u_x = viewing_intersection.x / W_f + 0.5f;
        Float u_y = 0.5f - viewing_intersection.y / H_f;
        
        PhaseSpaceCoordVar result;
        result.x = make_float2(x_normalized, y_normalized);
        result.u = make_float2(u_x, u_y);
        return result;
    }
    
    /// Simplified temporal transport using motion vectors
    /// For cases where explicit world velocity is not available
    /// 
    /// @param src Source phase-space coordinate
    /// @param motion_vec Motion vector in subpixel space (for light field: dx, dy where dx = x*3 + k)
    /// @param res_w Display resolution width in subpixels (for light field: res_w * 3)
    /// @param res_h Display resolution height in subpixels (same as pixels for light field)
    /// @return Historical phase-space coordinate
    [[nodiscard]] static PhaseSpaceCoordVar temporal_transport_motion_vec(
        const PhaseSpaceCoordVar &src,
        const Float2 &motion_vec,
        const Float &res_w,
        const Float &res_h) noexcept {
        
        // Convert motion vector from subpixels to normalized coordinates
        Float2 motion_normalized = make_float2(motion_vec.x / res_w, motion_vec.y / res_h);
        
        PhaseSpaceCoordVar result;
        // Spatial coordinate moves by motion vector
        result.x = src.x - motion_normalized;
        // Angular coordinate is assumed to be preserved (approximation)
        // For accurate angular transport, use the full temporal_transport()
        result.u = src.u;
        return result;
    }
    
    // ========================================================================
    // Utility Functions
    // ========================================================================
    
    /// Compute the projection scale factor β for angular transport
    /// This relates angular offsets on the viewing plane to spatial shifts
    /// on the display plane, accounting for the optical geometry
    /// 
    /// @param geom Light field geometry parameters
    /// @return Projection scale factor β
    [[nodiscard]] static Float compute_beta(Var<LightFieldGeometry> geom) noexcept {
        // β relates the angular baseline to spatial shift
        // For a two-plane parameterization with focal distance d_f:
        // β ≈ W_f (focal plane width) to convert normalized angular to spatial
        return geom.W_f;
    }
    
    /// Check if a phase-space coordinate is within valid bounds
    /// 
    /// @param coord Phase-space coordinate to check
    /// @param res_w Display width in pixels
    /// @param res_h Display height in pixels
    /// @return True if coordinate is valid
    [[nodiscard]] static Bool is_valid_coord(
        const PhaseSpaceCoordVar &coord,
        const Float &res_w,
        const Float &res_h) noexcept {
        
        // Check spatial bounds (normalized to [0, 1])
        Bool spatial_valid = all(coord.x >= 0.f) && 
                             coord.x.x <= 1.f && 
                             coord.x.y <= 1.f;
        
        // Angular bounds are typically more relaxed
        // but we still check for reasonable values
        Bool angular_valid = all(abs(coord.u) < 10.f);
        
        return spatial_valid && angular_valid;
    }
};

}// namespace vision::ssat
