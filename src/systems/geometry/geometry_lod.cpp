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
    // 关键修复：用"到包围球表面"的距离下界钳制，消除贴近时的高增益失稳。
    // 原公式 ratio = r/(d·tan) 在相机进入包围球（d ≤ r，巨物贴脸时必然发生）时
    // 进入 1/d 高增益区，d→0 时 ratio→∞：相机每帧正常移动即让 ratio 摆动数百个
    // 百分点，跨越多个 LOD 阈值 → 级别快速跳变 + 面闪烁。
    // 把 d 钳到 bounding_radius 后，贴近时 ratio 饱和在 1/tan(fov/2)（≈1.73@60°），
    // 远超最大阈值 0.95 → 恒选最高精度 LOD0，不再抖动。
    d = std::max(d, bounding_radius);
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

