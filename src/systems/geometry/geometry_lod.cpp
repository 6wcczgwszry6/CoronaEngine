#include <corona/systems/geometry/geometry_system.h>

#include <cmath>
#include <vector>

#include <ktm/ktm.h>

namespace Corona::Systems {

// ============================================================================
// LOD 工具
// ============================================================================

float GeometrySystem::compute_screen_ratio(const ktm::fvec3& camera_pos,
                                        float              camera_fov_deg,
                                        const ktm::fvec3& world_center,
                                        float              bounding_radius) {
    float d = ktm::distance(camera_pos, world_center);
    if (d < 1e-4f) d = 1e-4f;
    return bounding_radius / (d * std::tan(ktm::radians(camera_fov_deg) * 0.5f));
}

int GeometrySystem::select_lod_level(float                     screen_ratio,
                                   const std::vector<float>& thresholds) {
    for (int i = static_cast<int>(thresholds.size()) - 1; i >= 0; --i) {
        if (screen_ratio <= thresholds[i]) {
            return i + 1;
        }
    }
    return 0;
}

}  // namespace Corona::Systems

