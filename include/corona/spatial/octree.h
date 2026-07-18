#pragma once

#include <corona/spatial/aabb.h>

#include <array>
#include <cstddef>
#include <functional>
#include <memory>
#include <span>
#include <utility>
#include <vector>

namespace Corona::Spatial {

/**
 * @brief 八叉树调参
 *
 * 该结构与 mechanics_system.cpp 中 file-local 实现的常量保持兼容，
 * 便于后续把物理系统的实现迁移到 GeometrySystem 时无回归差异。
 */
struct OctreeConfig {
    int   max_depth            = 6;       ///< 最大递归深度
    int   max_objects_per_leaf = 4;       ///< 叶节点容量阈值，超过则尝试分裂
    float root_padding         = 0.01f;   ///< 根盒外扩，防边界物体跨层抖振
};

/**
 * @brief 通用模板化八叉树（递归空间分区）
 *
 * @tparam TPayload 叶节点存储的载荷类型，要求可拷贝/可移动且可比较（用于 dedupe）。
 *
 * 由 GeometrySystem 在 update() 中独占重建（rebuild），其它系统只读查询。
 * 所有查询接口采用递归剪枝，节点 bounds 不相交时跳过整棵子树。
 */
template <typename TPayload>
class Octree {
   public:
    struct Entry {
        TPayload payload;
        AABB     bounds;
    };

    // 八叉树分块 preload — 节点仅作为当帧的 actor 分组容器，不跨帧持久化
    struct NodeInRange {
        AABB                bounds;            // 节点世界 AABB
        float               min_cam_distance;  // 到最近相机的最近点距离（非中心点）
        std::vector<TPayload> actors;          // 该节点子树内满足 predicate 的 actor
    };

    explicit Octree(OctreeConfig cfg = {}) : cfg_(cfg) {}

    void clear() noexcept {
        root_.reset();
    }

    /**
     * @brief 全量重建八叉树
     * @param root      场景根 AABB（已含 padding）
     * @param entries   所有需要插入的载荷
     */
    void rebuild(const AABB& root, std::span<const Entry> entries) {
        root_ = std::make_unique<Node>();
        root_->bounds = root;
        for (const auto& e : entries) {
            insert(root_.get(), e, 0);
        }
    }

    [[nodiscard]] std::size_t size() const noexcept {
        return count_entries(root_.get());
    }

    [[nodiscard]] bool empty() const noexcept {
        return !root_ || count_entries(root_.get()) == 0;
    }

    [[nodiscard]] const OctreeConfig& config() const noexcept { return cfg_; }

    // ============================================================
    // 查询接口（递归 + 剪枝）
    // ============================================================

    void query_aabb(const AABB& box, std::vector<TPayload>& out) const {
        if (!root_) return;
        query_aabb_impl(root_.get(), box, out);
    }

    void query_sphere(const ktm::fvec3& center, float radius,
                      std::vector<TPayload>& out) const {
        if (!root_) return;
        query_sphere_impl(root_.get(), center, radius, out);
    }

    /**
     * @brief 自定义谓词查询（视锥剔除等可基于此封装）
     */
    template <typename Predicate>
    void query_if(Predicate&& pred, std::vector<TPayload>& out) const {
        if (!root_) return;
        query_if_impl(root_.get(), pred, out);
    }

    /**
     * @brief 收集在所有球之外的子树 payload（八叉树估计卸载核心）
     *
     * 节点级判定：若节点 AABB 到**所有**球心的最近距离均 > radius，
     * 则该节点整棵子树一次性批量收集——不逐条目、不逐相机计数。
     * 若节点与任一球相交则递归子节点。
     *
     * 与 query_sphere（单个球内）对称：query_sphere 找到"该加载的"，
     * collect_outside_spheres 找到"所有相机外、该卸载的"。
     *
     * @param centers  多相机位置（通常 1~4 个）
     * @param radius   卸载距离阈值（所有相机共用同一值）
     */
    void collect_outside_spheres(const std::vector<ktm::fvec3>& centers, float radius,
                                 std::vector<TPayload>& out) const {
        if (!root_ || centers.empty()) return;
        collect_outside_spheres_impl(root_.get(), centers, radius, out);
    }

    // ============================================================
    // 八叉树分块 preload — 自适应深度节点收集
    // ============================================================
    // 递归八叉树，收集所有"完全在 preload 范围内"的节点。
    // 节点 AABB 完全在半径内 → 收集该节点（不再递归）；
    // 节点 AABB 部分在内 → 递归子节点；完全在外 → 跳过整棵子树。
    //
    /// @param cam_positions 所有相机世界位置
    /// @param radius        范围半径（= preload_distance）
    /// @param predicate     过滤谓词 bool(TPayload) — 只收集返回 true 的 actor
    /// @param out           输出：范围内节点的信息
    template <typename Predicate>
    void collect_nodes_in_range(
        const std::vector<ktm::fvec3>& cam_positions,
        float radius,
        Predicate&& predicate,
        std::vector<NodeInRange>& out) const {
        if (!root_ || cam_positions.empty()) return;
        const float r2 = radius * radius;
        collect_nodes_in_range_impl(root_.get(), cam_positions, r2, predicate, out);
    }

    /**
     * @brief 收集所有可能碰撞的 payload 对（i<j，已去重）
     */
    void collect_pairs(std::vector<std::pair<TPayload, TPayload>>& out) const {
        if (!root_) return;
        collect_pairs_impl(root_.get(), out);
    }

    struct Stats {
        std::size_t entries        = 0;
        int         nodes          = 0;
        int         leaves         = 0;
        int         max_depth_used = 0;
    };

    [[nodiscard]] Stats stats() const noexcept {
        Stats s;
        gather_stats(root_.get(), s, 0);
        return s;
    }

   private:
    struct Node {
        AABB                                bounds;
        std::vector<Entry>                  entries;   // 叶节点=全部对象；内部节点=跨分割面的对象
        std::array<std::unique_ptr<Node>, 8> children{};
        bool                                is_leaf = true;
    };

    static int octant_index(const ktm::fvec3& center, const ktm::fvec3& point) {
        return (point.x >= center.x ? 1 : 0)
             | (point.y >= center.y ? 2 : 0)
             | (point.z >= center.z ? 4 : 0);
    }

    static AABB child_bounds(const AABB& parent, int octant) {
        ktm::fvec3 c = parent.center();
        AABB child;
        child.min.x = (octant & 1) ? c.x : parent.min.x;
        child.max.x = (octant & 1) ? parent.max.x : c.x;
        child.min.y = (octant & 2) ? c.y : parent.min.y;
        child.max.y = (octant & 2) ? parent.max.y : c.y;
        child.min.z = (octant & 4) ? c.z : parent.min.z;
        child.max.z = (octant & 4) ? parent.max.z : c.z;
        return child;
    }

    int fits_in_one_octant(const AABB& parent, const AABB& box) const {
        ktm::fvec3 c = parent.center();
        int idx_min = octant_index(c, box.min);
        int idx_max = octant_index(c, box.max);
        return (idx_min == idx_max) ? idx_min : -1;
    }

    void subdivide(Node* node, int depth) {
        for (int i = 0; i < 8; ++i) {
            node->children[i] = std::make_unique<Node>();
            node->children[i]->bounds = child_bounds(node->bounds, i);
        }
        node->is_leaf = false;

        std::vector<Entry> old_entries;
        old_entries.swap(node->entries);
        for (const auto& e : old_entries) {
            int idx = fits_in_one_octant(node->bounds, e.bounds);
            if (idx >= 0) {
                node->children[idx]->entries.push_back(e);
            } else {
                node->entries.push_back(e);
            }
        }
        // 递归分裂：检查每个子节点是否需要继续分裂
        for (int i = 0; i < 8; ++i) {
            // 条件1：该子节点的条目数 >= 阈值（超容量了）
            //        static_cast<int> 是把 size_t 转成 int，消除有符号/无符号比较的警告
            // 条件2：深度还没到上限（还能往下分）
            if (static_cast<int>(node->children[i]->entries.size()) >= cfg_.max_objects_per_leaf
                && depth + 1 < cfg_.max_depth) {
                // 对第 i 个子节点继续分裂，深度 +1
                subdivide(node->children[i].get(), depth + 1);
                }
        }
    }

    void insert(Node* node, const Entry& entry, int depth) {
        if (node->is_leaf) {
            if (static_cast<int>(node->entries.size()) < cfg_.max_objects_per_leaf
                || depth >= cfg_.max_depth) {
                node->entries.push_back(entry);
                return;
            }
            subdivide(node,depth);
        }

        int idx = fits_in_one_octant(node->bounds, entry.bounds);
        if (idx >= 0) {
            insert(node->children[idx].get(), entry, depth + 1);
        } else {
            node->entries.push_back(entry);
        }
    }

    static std::size_t count_entries(const Node* node) {
        if (!node) return 0;
        std::size_t n = node->entries.size();
        for (const auto& child : node->children) {
            if (child) n += count_entries(child.get());
        }
        return n;
    }

    // === 递归查询 ===

    static void query_aabb_impl(const Node* node, const AABB& box,
                                std::vector<TPayload>& out) {
        if (!node->bounds.overlaps(box)) return;
        for (const auto& e : node->entries) {
            if (e.bounds.overlaps(box)) out.push_back(e.payload);
        }
        for (const auto& child : node->children) {
            if (child) query_aabb_impl(child.get(), box, out);
        }
    }

    static void query_sphere_impl(const Node* node, const ktm::fvec3& center,
                                  float radius, std::vector<TPayload>& out) {
        float r2 = radius * radius;
        float dx = std::max({node->bounds.min.x - center.x, 0.0f, center.x - node->bounds.max.x});
        float dy = std::max({node->bounds.min.y - center.y, 0.0f, center.y - node->bounds.max.y});
        float dz = std::max({node->bounds.min.z - center.z, 0.0f, center.z - node->bounds.max.z});
        if (dx * dx + dy * dy + dz * dz > r2) return;

        for (const auto& e : node->entries) {
            dx = std::max({e.bounds.min.x - center.x, 0.0f, center.x - e.bounds.max.x});
            dy = std::max({e.bounds.min.y - center.y, 0.0f, center.y - e.bounds.max.y});
            dz = std::max({e.bounds.min.z - center.z, 0.0f, center.z - e.bounds.max.z});
            if (dx * dx + dy * dy + dz * dz <= r2) out.push_back(e.payload);
        }
        for (const auto& child : node->children) {
            if (child) query_sphere_impl(child.get(), center, radius, out);
        }
    }

    template <typename Predicate>
    static void query_if_impl(const Node* node, const Predicate& pred,
                              std::vector<TPayload>& out) {
        if (!pred(node->bounds)) return;
        for (const auto& e : node->entries) {
            if (pred(e.bounds)) out.push_back(e.payload);
        }
        for (const auto& child : node->children) {
            if (child) query_if_impl(child.get(), pred, out);
        }
    }

    /// 点到 AABB 最近点的距离平方。相机在 AABB 内部 → 返回 0。
    /// 复用 collect_outside_spheres_impl 中已有的同等逻辑。
    static float point_aabb_dist_sq(const ktm::fvec3& p, const AABB& box) {
        float dx = std::max({box.min.x - p.x, 0.0f, p.x - box.max.x});
        float dy = std::max({box.min.y - p.y, 0.0f, p.y - box.max.y});
        float dz = std::max({box.min.z - p.z, 0.0f, p.z - box.max.z});
        return dx*dx + dy*dy + dz*dz;
    }

    /// 判定 AABB 是否完全在**任意一台**相机的 preload 球内。
    /// AABB 最远角点 = 逐轴取离相机远的端点，farthest² = Σ max(Δmin², Δmax²)
    static bool aabb_fully_in_any_range(const AABB& box,
                                        const std::vector<ktm::fvec3>& cam_positions,
                                        float radius_sq) {
        for (const auto& cam : cam_positions) {
            float farthest_sq = 0.0f;
            float d;

            d = box.min.x - cam.x;  d *= d;
            { float e = box.max.x - cam.x;  e *= e;  if (e > d) d = e; }
            farthest_sq += d;

            d = box.min.y - cam.y;  d *= d;
            { float e = box.max.y - cam.y;  e *= e;  if (e > d) d = e; }
            farthest_sq += d;

            d = box.min.z - cam.z;  d *= d;
            { float e = box.max.z - cam.z;  e *= e;  if (e > d) d = e; }
            farthest_sq += d;

            if (farthest_sq <= radius_sq) return true;  // 这台相机完全覆盖 AABB → 收集
        }
        return false;  // 没有一台相机完全覆盖 → 需要递归
    }

    /// 收集子树中所有 payload（节点已判定完全在球外时批量使用）
    static void collect_subtree_payloads(const Node* node, std::vector<TPayload>& out) {
        for (const auto& e : node->entries) out.push_back(e.payload);
        for (const auto& child : node->children) {
            if (child) collect_subtree_payloads(child.get(), out);
        }
    }

    /// predicate 过滤版 collect_subtree_payloads
    template <typename Predicate>
    static void collect_subtree_payloads_if(const Node* node, Predicate&& pred,
                                            std::vector<TPayload>& out) {
        for (const auto& e : node->entries) {
            if (pred(e.payload)) out.push_back(e.payload);
        }
        for (const auto& child : node->children) {
            if (child) collect_subtree_payloads_if(child.get(), pred, out);
        }
    }

    /// @see collect_outside_spheres
    static void collect_outside_spheres_impl(const Node* node,
                                             const std::vector<ktm::fvec3>& centers,
                                             float radius, std::vector<TPayload>& out) {
        float r2 = radius * radius;

        // 节点级判定：此节点是否在所有相机球之外？
        bool outside_all = true;
        for (const auto& c : centers) {
            float dx = std::max({node->bounds.min.x - c.x, 0.0f, c.x - node->bounds.max.x});
            float dy = std::max({node->bounds.min.y - c.y, 0.0f, c.y - node->bounds.max.y});
            float dz = std::max({node->bounds.min.z - c.z, 0.0f, c.z - node->bounds.max.z});
            if (dx * dx + dy * dy + dz * dz <= r2) {
                outside_all = false;
                break;  // 在一台相机内 → 不必检查其余
            }
        }

        if (outside_all) {
            // 整棵子树在所有相机外 → 批量收集，不逐条目判断
            collect_subtree_payloads(node, out);
            return;
        }

        // 节点与至少一台相机的球相交 → 逐条目判断 + 递归子节点
        for (const auto& e : node->entries) {
            bool entry_outside = true;
            for (const auto& c : centers) {
                float dx = std::max({e.bounds.min.x - c.x, 0.0f, c.x - e.bounds.max.x});
                float dy = std::max({e.bounds.min.y - c.y, 0.0f, c.y - e.bounds.max.y});
                float dz = std::max({e.bounds.min.z - c.z, 0.0f, c.z - e.bounds.max.z});
                if (dx * dx + dy * dy + dz * dz <= r2) {
                    entry_outside = false;
                    break;
                }
            }
            if (entry_outside) out.push_back(e.payload);
        }

        for (const auto& child : node->children) {
            if (child) collect_outside_spheres_impl(child.get(), centers, radius, out);
        }
    }

    // ============================================================
    // collect_nodes_in_range 递归实现
    // ============================================================
    template <typename Predicate>
    static void collect_nodes_in_range_impl(const Node* node,
                                            const std::vector<ktm::fvec3>& cam_positions,
                                            float radius_sq, Predicate&& pred,
                                            std::vector<NodeInRange>& out) {
        // ① 最近距离剪枝：节点 AABB 到所有相机均 > radius → 整棵子树跳过
        // 用第一台相机的距离作初始值，避免依赖 <limits>
        float min_dist_sq = point_aabb_dist_sq(cam_positions[0], node->bounds);
        for (size_t i = 1; i < cam_positions.size(); ++i) {
            float d_sq = point_aabb_dist_sq(cam_positions[i], node->bounds);
            if (d_sq < min_dist_sq) min_dist_sq = d_sq;
        }
        if (min_dist_sq > radius_sq) return;  // 完全在范围外

        // ② 判定节点是否"完全在范围内"（最远角点也在球内）
        if (aabb_fully_in_any_range(node->bounds, cam_positions, radius_sq)) {
            // 整棵子树在范围内 → 收集满足 predicate 的 actor → 不再递归
            NodeInRange info;
            info.bounds           = node->bounds;
            info.min_cam_distance = std::sqrt(min_dist_sq);
            collect_subtree_payloads_if(node, pred, info.actors);
            if (!info.actors.empty()) out.push_back(std::move(info));
            return;
        }

        // ③ 部分在范围内 → 递归子节点
        if (!node->is_leaf) {
            for (const auto& child : node->children) {
                if (child) collect_nodes_in_range_impl(
                    child.get(), cam_positions, radius_sq, pred, out);
            }
        } else {
            // 叶节点且部分在范围内 → 逐 entry 判断后收集。
            NodeInRange info;
            info.bounds           = node->bounds;
            info.min_cam_distance = std::sqrt(min_dist_sq);
            for (const auto& e : node->entries) {
                if (!pred(e.payload)) continue;
                // 验证 entry 确实在范围内
                float entry_min_sq = point_aabb_dist_sq(cam_positions[0], e.bounds);
                for (size_t i = 1; i < cam_positions.size(); ++i) {
                    float d_sq = point_aabb_dist_sq(cam_positions[i], e.bounds);
                    if (d_sq < entry_min_sq) entry_min_sq = d_sq;
                }
                if (entry_min_sq > radius_sq) continue;  // 超出预加载半径
                info.actors.push_back(e.payload);
            }
            if (!info.actors.empty()) out.push_back(std::move(info));
        }
    }

    static void query_straddle_in_subtree(const Entry& straddle, const Node* subtree,
                                           std::vector<std::pair<TPayload, TPayload>>& out) {
        if (!straddle.bounds.overlaps(subtree->bounds)) return;
        for (const auto& e : subtree->entries) {
            if (straddle.bounds.overlaps(e.bounds)) {
                auto a = straddle.payload;
                auto b = e.payload;
                out.emplace_back(a < b ? a : b, a < b ? b : a);
            }
        }
        if (subtree->is_leaf) return;
        for (const auto& child : subtree->children) {
            if (child) query_straddle_in_subtree(straddle, child.get(), out);
        }
    }

    // ============================================================================
    // compare_subtrees() —— 跨子树碰撞检测
    // ============================================================================
    //检查两棵子树的条目之间是否有 AABB 重叠。
    static void compare_subtrees(const Node* a, const Node* b,
                                  std::vector<std::pair<TPayload, TPayload>>& out) {
        if (!a->bounds.overlaps(b->bounds)) return;

        for (const auto& ea : a->entries) {
            for (const auto& eb : b->entries) {
                if (ea.bounds.overlaps(eb.bounds)) {
                    auto pa = ea.payload;
                    auto pb = eb.payload;
                    out.emplace_back(pa < pb ? pa : pb, pa < pb ? pb : pa);
                }
            }
        }
        // A的跨面条目 vs B的深层子节点
        for (const auto& ea : a->entries) {
            for (const auto& cb : b->children) {
                if (cb) query_straddle_in_subtree(ea, cb.get(), out);
            }
        }
        // B的跨面条目 vs A的深层子节点
        for (const auto& eb : b->entries) {
            for (const auto& ca : a->children) {
                if (ca) query_straddle_in_subtree(eb, ca.get(), out);
            }
        }
        if (a->is_leaf && b->is_leaf) return;

        if (!a->is_leaf && !b->is_leaf) {
            for (const auto& ca : a->children) {
                if (!ca) continue;
                for (const auto& cb : b->children) {
                    if (!cb) continue;
                    compare_subtrees(ca.get(), cb.get(), out);
                }
            }
        }
        else if (!a->is_leaf) {
            for (const auto& ca : a->children) {
                if (ca) compare_subtrees(ca.get(), b, out);
            }
        }
        else {
            for (const auto& cb : b->children) {
                if (cb) compare_subtrees(a, cb.get(), out);
            }
        }
    }


    static void collect_pairs_impl(const Node* node,
                                   std::vector<std::pair<TPayload, TPayload>>& out) {
        if (!node) return;

        if (node->is_leaf) {
            for (std::size_t i = 0; i < node->entries.size(); ++i) {
                for (std::size_t j = i + 1; j < node->entries.size(); ++j) {
                    if (node->entries[i].bounds.overlaps(node->entries[j].bounds)) {
                        auto a = node->entries[i].payload;
                        auto b = node->entries[j].payload;
                        out.emplace_back(a < b ? a : b, a < b ? b : a);
                    }
                }
            }
            return;
        }

        // 跨分割条目间的对
        for (std::size_t i = 0; i < node->entries.size(); ++i) {
            for (std::size_t j = i + 1; j < node->entries.size(); ++j) {
                if (node->entries[i].bounds.overlaps(node->entries[j].bounds)) {
                    auto a = node->entries[i].payload;
                    auto b = node->entries[j].payload;
                    out.emplace_back(a < b ? a : b, a < b ? b : a);
                }
            }
        }

        // 跨分割条目 vs 每个子树的条目
        for (const auto& straddle : node->entries) {
            for (const auto& child : node->children) {
                if (child) {
                    query_straddle_in_subtree(straddle, child.get(), out);
                }
            }
        }

        // 不同子树条目之间的对（边界接触）
        for (int ci = 0; ci < 8; ++ci) {
            if (!node->children[ci]) continue;  // 跳过不存在的子节点
            for (int cj = ci + 1; cj < 8; ++cj) {
                if (!node->children[cj]) continue;  // 跳过不存在的子节点
                // 递归比较两棵子树之间的碰撞对
                compare_subtrees(node->children[ci].get(), node->children[cj].get(), out);
            }
        }

        // 递归子节点
        for (const auto& child : node->children) {
            if (child) collect_pairs_impl(child.get(), out);
        }
    }

    static void gather_stats(const Node* node, Stats& s, int depth) {
        if (!node) return;
        s.entries += node->entries.size();
        ++s.nodes;
        s.max_depth_used = std::max(s.max_depth_used, depth);
        if (node->is_leaf) {
            ++s.leaves;
        } else {
            for (const auto& child : node->children) {
                if (child) gather_stats(child.get(), s, depth + 1);
            }
        }
    }

    OctreeConfig            cfg_;
    std::unique_ptr<Node>   root_;
};

}  // namespace Corona::Spatial