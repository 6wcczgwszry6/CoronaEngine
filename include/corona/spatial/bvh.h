#pragma once

#include <corona/spatial/aabb.h>
#include <ktm/ktm.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <utility>
#include <vector>

namespace Corona::Spatial {

/**
 * @brief 物体级 BVH（Bounding Volume Hierarchy）加速结构
 *
 * 设计定位：
 *   - Octree 负责 **场景级**："场景中有哪些物体？"（粗粒度剔除）
 *   - BVH   负责 **物体级**："这个物体内部命中了哪些基元？"（细粒度查询）
 *   两者组合使用形成双层加速结构。
 *
 * 构建算法：
 *   自顶向下递归构建，每层选择包围盒最长轴，按基元重心排序后中位数
 *   分割（spatial median split）。时间复杂度 O(n log n)，对退化输入
 *   （同重心、零体积包围盒等）有兜底处理。
 *
 * 查询接口：
 *   - query_ray()   : 射线穿透，返回所有 AABB 被命中的载荷（无序）
 *   - closest_hit() : 射线穿透，返回离射线起点最近的命中载荷（有序遍历 + 剪枝）
 *   - query_aabb()  : 包围盒重叠查询
 *
 * @tparam TPayload 叶节点载荷类型（如三角形索引、碰撞体句柄）。
 *                  要求可拷贝、可移动、可用 operator< 比较（去重用）。
 *
 * 使用示例：
 * @code
 *   BVH<uint32_t> bvh;
 *   std::vector<BVH<uint32_t>::Entry> entries;
 *   for (uint32_t i = 0; i < triangles.size(); ++i) {
 *       entries.push_back({i, compute_AABB(triangles[i])});
 *   }
 *   bvh.build(entries);
 *
 *   // 穿透查询：拿到所有命中的三角面索引
 *   std::vector<uint32_t> hits;
 *   bvh.query_ray(ray_origin, ray_inv_dir, hits);
 *
 *   // 最近命中：直接返回 Hit{payload, t} 或 nullopt
 *   if (auto hit = bvh.closest_hit(origin, inv_dir, 1000.0f)) {
 *       uint32_t tri = hit->payload;   // 最近三角面
 *       float    t   = hit->t;         // 命中距离
 *   }
 * @endcode
 */
template <typename TPayload>
class BVH {
   public:
    // ================================================================
    // 公开类型
    // ================================================================

    /**
     * @brief 输入基元：一对一的载荷与包围盒映射
     *
     * 重心的预计算放在构建内部完成，调用方只需提供 bounds。
     */
    struct Entry {
        TPayload payload;  ///< 基元标识，如三角形下标
        AABB     bounds;   ///< 世界空间 / 局部空间包围盒（构建前必须 valid()）
    };

    /**
     * @brief 构建参数
     */
    struct Config {
        /** 叶节点基元数上限。超过此值且未到 max_depth 则继续分裂。*/
        int max_leaf_primitives = 4;

        /** 树的最大深度，防止无限递归。*/
        int max_depth = 32;
    };

    /**
     * @brief 射线命中结果
     */
    struct Hit {
        TPayload payload;  ///< 命中的载荷
        float    t;        ///< 命中点到射线起点的参数距离（t >= 0）
    };

    /**
     * @brief 统计信息（调试/性能分析用）
     */
    struct Stats {
        std::size_t nodes            = 0;  ///< 节点总数
        std::size_t leaves           = 0;  ///< 叶节点数
        std::size_t total_primitives = 0;  ///< 基元总数（叶节点 entries 之和）
        int         max_depth_used   = 0;  ///< 实际最大深度
    };

    explicit BVH(Config cfg = {}) : cfg_(cfg) {}

    /** 清空整棵树，释放所有内存 */
    void clear() noexcept { root_.reset(); }

    /**
     * @brief 全量重建 BVH
     *
     * 每次调用完全覆盖旧树。典型调用时机：
     *   - 物体几何变更（蒙皮动画、变形）
     *   - 物体变换更新导致包围盒在世界空间发生变化
     *
     * @param entries 基元列表（内部拷贝一份用于排序构建，调用方可随后释放）
     */
    void build(std::span<const Entry> entries) {
        if (entries.empty()) {
            root_.reset();
            return;
        }

        // 拷贝到可变缓冲区，预计算重心供排序
        std::vector<BuildEntry> buffer;
        buffer.reserve(entries.size());
        for (const auto& e : entries) {
            buffer.push_back({e.payload, e.bounds, e.bounds.center()});
        }

        root_ = build_recursive(buffer, 0);
    }

    [[nodiscard]] bool empty() const noexcept { return !root_; }

    [[nodiscard]] const Config& config() const noexcept { return cfg_; }

    // ================================================================
    // 射线查询
    // ================================================================

    /**
     * @brief 返回射线命中的所有载荷（AABB 级，无序）
     *
     * 注意：命中判定基于包围盒而非精确几何。调用方如需精确命中，
     * 拿到载荷后自行做三角形级射线检测。
     *
     * @param origin   射线起点
     * @param inv_dir  射线方向各分量的倒数（1/dir），传此值可避免三次除法
     * @param out      输出：命中的载荷列表（不清空，追加写入）
     */
    void query_ray(const ktm::fvec3& origin,
                   const ktm::fvec3& inv_dir,
                   std::vector<TPayload>& out) const {
        if (!root_) return;
        query_ray_recursive(root_.get(), origin, inv_dir, out);
    }

    /**
     * @brief 返回射线命中的最近载荷（AABB 级，有序遍历 + 剪枝）
     *
     * 遍历策略：每次进入内部节点时，先计算左右子节点的入口距离，
     * 从近到远遍历，并持续用当前最优 t 剪枝——一旦子节点的入口距离
     * 超过已知最优 t 即跳过整棵子树。
     *
     * @param origin   射线起点
     * @param inv_dir  射线方向各分量的倒数
     * @param t_max    最大搜索距离（射线长度），命中的 t 一定 <= t_max
     * @return 命中返回 Hit{payload, t}，未命中返回 std::nullopt
     */
    [[nodiscard]] std::optional<Hit> closest_hit(const ktm::fvec3& origin,
                                                  const ktm::fvec3& inv_dir,
                                                  float              t_max) const {
        if (!root_) return std::nullopt;
        std::optional<Hit> best;
        float best_t = t_max;
        closest_hit_recursive(root_.get(), origin, inv_dir, best, best_t);
        return best;
    }

    // ================================================================
    // 包围盒查询
    // ================================================================

    /**
     * @brief 返回所有包围盒与给定 AABB 重叠的载荷
     *
     * @param box  查询包围盒
     * @param out  输出：命中的载荷列表（不清空，追加写入）
     */
    void query_aabb(const AABB& box, std::vector<TPayload>& out) const {
        if (!root_) return;
        query_aabb_recursive(root_.get(), box, out);
    }

    // ================================================================
    // 调试 / 统计
    // ================================================================

    [[nodiscard]] Stats stats() const noexcept {
        Stats s;
        gather_stats(root_.get(), s, 0);
        return s;
    }

   private:
    // ================================================================
    // 内部节点结构
    // ================================================================
    //
    // BVH 是一棵二叉树：
    //   - 叶节点：entries 非空，left/right 均为空
    //   - 内部节点：left/right 均非空，entries 为空（仅用于包围盒维护）
    //
    //   与 Octree（八叉树）的区别：
    //   - Octree 是八分空间，内部节点可能也存储跨分割面的基元
    //   - BVH 是二分对象，每个基元只出现在一个叶节点中
    //
    struct Node {
        AABB bounds;  ///< 该节点所有基元的紧致包围盒

        std::unique_ptr<Node> left;   ///< 左子树
        std::unique_ptr<Node> right;  ///< 右子树

        std::vector<Entry> entries;  ///< 仅在叶节点有效

        bool is_leaf = true;    ///< 是否为叶节点
        int  axis    = 0;       ///< 分割轴（调试用，0=x, 1=y, 2=z）
    };

    // ================================================================
    // 射线 ↔ AABB 相交检测（Slab 方法）
    // ================================================================
    //
    // 原理：将 AABB 视为三对平行平面的交集，分别计算射线与每对平面
    // 的进出参数 t，取最近进入点和最远离开点。若 tmin <= tmax 且
    // tmax >= 0，则相交。
    //
    // 稳健处理：
    //   - 射线方向分量为 0（平行于某轴）时，用显式区间检查代替除法
    //   - 避免 inf*0=NaN 问题
    //

    /**
     * @brief 单个轴上的 slab 检测
     *
     * 当 dir[axis] == 0 时射线平行于该轴，inv_dir[axis] 为 ±inf。
     * 此时需直接检查原点是否在该轴区间内。
     *
     * 当 inv_dir[axis] == 0（即 dir 无穷大，实际罕见）时走标准 slab，
     * t0/t1 均退化为 0，该轴不收窄 tmin/tmax，等价于"对该轴无约束"。
     *
     * @return true  该轴通过
     * @return false 射线平行且原点在区间外，或进出参数导致 tmin > tmax
     */
    static bool slab_test(float  origin_val,   ///< 射线起点在该轴的坐标
                          float  inv_dir_val,  ///< 射线方向倒数（dir==0 时为 ±inf）
                          float  box_min_val,  ///< 包围盒该轴最小值
                          float  box_max_val,  ///< 包围盒该轴最大值
                          float& tmin,         ///< [in/out] 当前最近进入点
                          float& tmax)         ///< [in/out] 当前最远离开点
    {
        // 情形 1：射线方向分量为 0（或 NaN）—— 平行于该轴
        //         inv_dir = 1/0 = ±inf，用 isinf 精确捕获
        //         NaN 走相同路径：视为平行，区间内通过，区间外淘汰
        if (std::isnan(inv_dir_val) || std::isinf(inv_dir_val)) {
            return origin_val >= box_min_val && origin_val <= box_max_val;
        }

        // 情形 2：标准 slab 检测（dir 分量有限，inv_dir 有限）
        float t0 = (box_min_val - origin_val) * inv_dir_val;
        float t1 = (box_max_val - origin_val) * inv_dir_val;
        if (t0 > t1) {
            std::swap(t0, t1);  // 确保 t0 <= t1（t0 是进入，t1 是离开）
        }
        tmin = (t0 > tmin) ? t0 : tmin;  // 收紧进入点
        tmax = (t1 < tmax) ? t1 : tmax;  // 收紧离开点
        return tmin <= tmax;
    }

    /**
     * @brief 射线与包围盒相交检测（带参数范围）
     *
     * @param origin  射线起点
     * @param inv_dir 射线方向倒数
     * @param box     包围盒
     * @param t_min   允许的最小 t（通常为 0，避免负方向的命中）
     * @param t_max   允许的最大 t（如射线长度）
     * @return true 相交
     */
    static bool ray_aabb_intersect(const ktm::fvec3& origin,
                                   const ktm::fvec3& inv_dir,
                                   const AABB&        box,
                                   float              t_min,
                                   float              t_max) {
        // 依次检测 X / Y / Z 三个轴
        if (!slab_test(origin.x, inv_dir.x, box.min.x, box.max.x, t_min, t_max)) return false;
        if (!slab_test(origin.y, inv_dir.y, box.min.y, box.max.y, t_min, t_max)) return false;
        if (!slab_test(origin.z, inv_dir.z, box.min.z, box.max.z, t_min, t_max)) return false;
        return true;
    }

    /**
     * @brief 计算射线进入包围盒的参数距离
     *
     * 用于 closest_hit 的有序遍历：决定先遍历哪个子节点。
     *
     * @return t_entry：射线进入包围盒处的参数值。
     *         若不相交则返回 +inf。
     */
    static float ray_entry_t(const ktm::fvec3& origin,
                             const ktm::fvec3& inv_dir,
                             const AABB&        box) {
        float tmin = 0.0f;
        float tmax = std::numeric_limits<float>::max();

        // X 轴：平行/NaN 检测（dir.x==0 ⇔ inv_dir.x==±inf）
        if (!std::isnan(inv_dir.x) && !std::isinf(inv_dir.x)) {
            float t0 = (box.min.x - origin.x) * inv_dir.x;
            float t1 = (box.max.x - origin.x) * inv_dir.x;
            if (t0 > t1) std::swap(t0, t1);
            tmin = (t0 > tmin) ? t0 : tmin;
            tmax = (t1 < tmax) ? t1 : tmax;
        } else if (origin.x < box.min.x || origin.x > box.max.x) {
            return std::numeric_limits<float>::max();
        }

        // Y 轴
        if (!std::isnan(inv_dir.y) && !std::isinf(inv_dir.y)) {
            float t0 = (box.min.y - origin.y) * inv_dir.y;
            float t1 = (box.max.y - origin.y) * inv_dir.y;
            if (t0 > t1) std::swap(t0, t1);
            tmin = (t0 > tmin) ? t0 : tmin;
            tmax = (t1 < tmax) ? t1 : tmax;
        } else if (origin.y < box.min.y || origin.y > box.max.y) {
            return std::numeric_limits<float>::max();
        }

        // Z 轴
        if (!std::isnan(inv_dir.z) && !std::isinf(inv_dir.z)) {
            float t0 = (box.min.z - origin.z) * inv_dir.z;
            float t1 = (box.max.z - origin.z) * inv_dir.z;
            if (t0 > t1) std::swap(t0, t1);
            tmin = (t0 > tmin) ? t0 : tmin;
            tmax = (t1 < tmax) ? t1 : tmax;
        } else if (origin.z < box.min.z || origin.z > box.max.z) {
            return std::numeric_limits<float>::max();
        }

        if (tmin > tmax) return std::numeric_limits<float>::max();
        return tmin;  // 进入点的 t
    }

    // ================================================================
    // 构建
    // ================================================================

    /**
     * @brief 递归构建子树
     *
     * 算法步骤（spatial median split）：
     *   1. 计算该组基元的合并包围盒
     *   2. 若满足终止条件（<= leaf_capacity 或 >= max_depth），创建叶节点
     *   3. 否则选择包围盒最长轴作为分割轴
     *   4. 按基元重心沿该轴排序，中位数切分
     *   5. 左右子集递归构建
     *
     * 退化兜底：
     *   - 若包围盒零体积（所有轴退化），直接创建叶节点
     *   - 若所有基元重心相同（排序后首尾相等），无法继续分割，创建叶节点
     *
     * @param entries 可变基元列表（包含预计算的重心）
     * @param depth   当前递归深度
     * @return 构建好的子树根节点
     */
    struct BuildEntry {
        TPayload   payload;
        AABB       bounds;
        ktm::fvec3 centroid;
    };

    std::unique_ptr<Node> build_recursive(std::vector<BuildEntry>& entries, int depth) {
        // ---------- 步骤 1：计算合并包围盒 ----------
        AABB merged = entries[0].bounds;
        for (std::size_t i = 1; i < entries.size(); ++i) {
            merged = merged.merged(entries[i].bounds);
        }

        // ---------- 步骤 2：终止条件 ----------
        // 叶节点条件：基元数 <= 阈值  或  不足两个无法二分  或  深度 >= 上限
        if (static_cast<int>(entries.size()) <= cfg_.max_leaf_primitives
            || entries.size() < 2
            || depth >= cfg_.max_depth) {
            auto node        = std::make_unique<Node>();
            node->bounds     = merged;
            node->is_leaf    = true;
            node->entries.reserve(entries.size());
            for (const auto& be : entries) {
                node->entries.push_back({be.payload, be.bounds});
            }
            return node;
        }

        // ---------- 步骤 3：选择分割轴 ----------
        // 选包围盒跨度最大的轴。若所有轴退化，创建叶节点退出。
        ktm::fvec3 extent = merged.extent();  // 半边长向量
        float ex = extent.x, ey = extent.y, ez = extent.z;

        int split_axis = 0;  // 默认 X
        if (ey > ex && ey > ez) {
            split_axis = 1;  // Y 最大
        } else if (ez > ex && ez > ey) {
            split_axis = 2;  // Z 最大
        }

        // 零体积包围盒兜底（所有轴都退化）
        if (ex <= 0.0f && ey <= 0.0f && ez <= 0.0f) {
            auto node     = std::make_unique<Node>();
            node->bounds  = merged;
            node->is_leaf = true;
            node->entries.reserve(entries.size());
            for (const auto& be : entries) {
                node->entries.push_back({be.payload, be.bounds});
            }
            return node;
        }

        // ---------- 步骤 4：沿分割轴排序 ----------
        // 使用 lambda 提取指定轴的重心分量
        auto centroid_on_axis = [split_axis](const BuildEntry& be) -> float {
            switch (split_axis) {
                case 0:  return be.centroid.x;
                case 1:  return be.centroid.y;
                default: return be.centroid.z;
            }
        };

        std::sort(entries.begin(), entries.end(),
                  [&](const BuildEntry& a, const BuildEntry& b) {
                      return centroid_on_axis(a) < centroid_on_axis(b);
                  });

        // ---------- 步骤 5：退化检测 ----------
        // 如果排序后首尾重心相等，说明所有基元重心在该轴上相同，
        // 无法通过该轴分割。此时扩大检查范围——若所有轴都相同则建叶。
        float first_c = centroid_on_axis(entries.front());
        float last_c  = centroid_on_axis(entries.back());
        if (first_c == last_c) {
            // 尝试换一个轴再排序。这里简单兜底：直接创建叶节点。
            auto node     = std::make_unique<Node>();
            node->bounds  = merged;
            node->is_leaf = true;
            node->entries.reserve(entries.size());
            for (const auto& be : entries) {
                node->entries.push_back({be.payload, be.bounds});
            }
            return node;
        }

        // ---------- 步骤 6：中位数切分 & 递归 ----------
        std::size_t mid = entries.size() / 2;

        // 左子集：[0, mid)
        std::vector<BuildEntry> left_entries(entries.begin(), entries.begin() + mid);
        // 右子集：[mid, end)
        std::vector<BuildEntry> right_entries(entries.begin() + mid, entries.end());

        auto node      = std::make_unique<Node>();
        node->is_leaf  = false;
        node->axis     = split_axis;
        node->left     = build_recursive(left_entries, depth + 1);
        node->right    = build_recursive(right_entries, depth + 1);

        // 内部节点的包围盒 = 左右子节点包围盒的合并
        node->bounds = node->left->bounds.merged(node->right->bounds);

        return node;
    }

    // ================================================================
    // 射线查询（递归）
    // ================================================================

    /**
     * @brief 无序射线查询——递归遍历整棵树
     *
     * 对每个节点先做 ray-AABB 检测，不命中则整棵子树剪枝。
     * 叶节点命中后，所有基元无条件输出（调用方自行精筛）。
     */
    static void query_ray_recursive(const Node*         node,
                                    const ktm::fvec3&   origin,
                                    const ktm::fvec3&   inv_dir,
                                    std::vector<TPayload>& out) {
        if (!node) return;

        // 剪枝：射线不命中该节点包围盒 → 跳过整棵子树
        if (!ray_aabb_intersect(origin, inv_dir, node->bounds, 0.0f,
                                std::numeric_limits<float>::max())) {
            return;
        }

        if (node->is_leaf) {
            // 叶节点：所有基元加入输出
            for (const auto& e : node->entries) {
                if (ray_aabb_intersect(origin, inv_dir, e.bounds, 0.0f,
                                       std::numeric_limits<float>::max())) {
                    out.push_back(e.payload);
                }
            }
            return;
        }

        // 内部节点：递归左右子树（无需排序——query_ray 不关心距离）
        query_ray_recursive(node->left.get(), origin, inv_dir, out);
        query_ray_recursive(node->right.get(), origin, inv_dir, out);
    }

    // ================================================================
    // 最近命中查询（递归——有序遍历 + 剪枝）
    // ================================================================

    /**
     * @brief 最近命中递归
     *
     * 核心优化：先计算左右子节点的入口 t，从近到远遍历。
     * 一旦近端命中，远端子树可能因入口 t > best_t 被整棵剪掉。
     *
     * @param best   [in/out] 当前最优 Hit，未命中状态用 nullopt 表示
     * @param best_t [in/out] 当前最优 t，随遍历推进不断收紧
     */
    static void closest_hit_recursive(const Node*            node,
                                      const ktm::fvec3&      origin,
                                      const ktm::fvec3&      inv_dir,
                                      std::optional<Hit>&    best,
                                      float&                 best_t) {
        if (!node) return;

        // 剪枝：节点包围盒入口距离已超过当前最优 → 跳过
        if (!ray_aabb_intersect(origin, inv_dir, node->bounds, 0.0f, best_t)) {
            return;
        }

        if (node->is_leaf) {
            // 叶节点：逐个检测基元，更新最优
            // ray_entry_t 同时完成相交判定和入口 t 计算，不相交时返回 +inf
            for (const auto& e : node->entries) {
                float t_entry = ray_entry_t(origin, inv_dir, e.bounds);
                if (t_entry < best_t) {
                    best_t = t_entry;
                    best   = Hit{e.payload, t_entry};
                }
            }
            return;
        }

        // 内部节点：计算左右子节点的入口距离，决定遍历顺序
        float t_left  = ray_entry_t(origin, inv_dir, node->left->bounds);
        float t_right = ray_entry_t(origin, inv_dir, node->right->bounds);

        // 从近到远遍历
        if (t_left <= t_right) {
            closest_hit_recursive(node->left.get(),  origin, inv_dir, best, best_t);
            closest_hit_recursive(node->right.get(), origin, inv_dir, best, best_t);
        } else {
            closest_hit_recursive(node->right.get(), origin, inv_dir, best, best_t);
            closest_hit_recursive(node->left.get(),  origin, inv_dir, best, best_t);
        }
    }

    // ================================================================
    // 包围盒查询（递归）
    // ================================================================

    /**
     * @brief 包围盒重叠查询——递归遍历
     *
     * 对每个节点先做 AABB overlaps 测试，不重叠则剪枝。
     */
    static void query_aabb_recursive(const Node*            node,
                                     const AABB&            box,
                                     std::vector<TPayload>& out) {
        if (!node) return;

        // 剪枝：查询盒与节点包围盒不重叠 → 跳过整棵子树
        if (!node->bounds.overlaps(box)) return;

        if (node->is_leaf) {
            for (const auto& e : node->entries) {
                if (e.bounds.overlaps(box)) {
                    out.push_back(e.payload);
                }
            }
            return;
        }

        query_aabb_recursive(node->left.get(), box, out);
        query_aabb_recursive(node->right.get(), box, out);
    }

    // ================================================================
    // 统计信息收集
    // ================================================================

    static void gather_stats(const Node* node, Stats& s, int depth) {
        if (!node) return;
        ++s.nodes;
        s.max_depth_used = std::max(s.max_depth_used, depth);
        if (node->is_leaf) {
            ++s.leaves;
            s.total_primitives += node->entries.size();
        } else {
            gather_stats(node->left.get(), s, depth + 1);
            gather_stats(node->right.get(), s, depth + 1);
        }
    }

    // ================================================================
    // 成员变量
    // ================================================================

    Config                  cfg_;   ///< 构建参数
    std::unique_ptr<Node>   root_;  ///< 根节点（null 表示空树）
};

}  // namespace Corona::Spatial