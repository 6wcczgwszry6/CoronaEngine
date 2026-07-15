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

// ============================================================================
// 屏幕空间误差选级（统一相机/GI 球形角预算）
// ============================================================================

float GeometrySystem::distance_point_to_aabb(const ktm::fvec3& p,
                                             const ktm::fvec3& aabb_min,
                                             const ktm::fvec3& aabb_max) {
    // 各轴上点到区间 [min,max] 的越界量（盒内为 0），合成欧氏距离。
    const float dx = std::max(std::max(aabb_min[0] - p[0], p[0] - aabb_max[0]), 0.0f);
    const float dy = std::max(std::max(aabb_min[1] - p[1], p[1] - aabb_max[1]), 0.0f);
    const float dz = std::max(std::max(aabb_min[2] - p[2], p[2] - aabb_max[2]), 0.0f);
    return std::sqrt(dx * dx + dy * dy + dz * dz);
}

float GeometrySystem::compute_angular_epsilon(float pixel_budget,
                                              float fov_deg,
                                              float height_px) {
    // epsilon = pixel_budget · (2·tan(fov/2) / height_px)
    //   右因子 = 「距离 1 处 1px 张开的世界尺寸」的倒数关系：world_err/d ≤ epsilon
    //   ⇔ pixel_error = (world_err/d)·(height_px/2)/tan(fov/2) ≤ pixel_budget。
    if (!(height_px > 0.0f)) height_px = 1.0f;
    if (!(pixel_budget > 0.0f)) pixel_budget = 1.0f;
    const float tan_half = std::tan(ktm::radians(fov_deg) * 0.5f);
    const float eps = pixel_budget * (2.0f * tan_half / height_px);
    // 兜底：异常 fov（tan≤0）时给一个极小正数，避免恒选 LOD0 或除零。
    return (eps > 0.0f) ? eps : 1e-6f;
}

float GeometrySystem::compute_pixel_budget_from_pressure(float vram_ratio) {
    // 默认 1.5px：显存充裕，视觉无损。
    // 压力越大预算越宽松 → 更多 mesh 倾向粗 LOD → GPU 缓冲缩小 → 显存自然回落。
    // 阶梯分段而非连续插值：避免相机微动时 pixel_budget 连续波动导致 LOD 跳变。
    if (vram_ratio < 0.60f) return 1.5f;    // 正常：1.5px
    if (vram_ratio < 0.75f) return 3.0f;    // 轻度承压：2×
    if (vram_ratio < 0.85f) return 6.0f;    // 中度承压：4×
    if (vram_ratio < 0.92f) return 12.0f;   // 中度承压：4×
    return 24.0f;                           // 极限：16×，几乎总选最粗级
}

int GeometrySystem::select_lod_by_error(float                     distance_to_aabb,
                                        const std::vector<float>& world_errors,
                                        float                     epsilon) {
    // 选「角误差 world_error/d ≤ epsilon 的最粗一级」。等价比较 world_error ≤ epsilon·d，
    // 免每级除法（d 固定）。d→0（相机贴住/进入 AABB）时 allowed→0 → 仅 level0（误差 0）
    // 通过 → 强制最高精度，天然正确。
    const float allowed = epsilon * std::max(distance_to_aabb, 0.0f);
    // 从最粗级向精细方向找第一个「误差可接受」的级。world_errors 随级号单调递增
    // （越粗误差越大），故第一个 ≤ allowed 的即最粗可接受级。
    for (int i = static_cast<int>(world_errors.size()) - 1; i >= 1; --i) {
        if (world_errors[i] <= allowed) {
            return i;
        }
    }
    return 0;  // 无更粗级可接受 → LOD0
}

}  // namespace Corona::Systems

