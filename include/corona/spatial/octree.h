// ============================================================================
// octree.h 八叉树空间分区数据结构
// ============================================================================
// 八叉树是一种用于三维空间管理的数据结构。它把一个大空间递归地切成 8 个小格子
// 每个小格子又叫"子节点"。需要查找"某个范围内的物体"时，就可以跳过那些完全不相交的格子，
// 大幅减少需要检查的物体数量。
// ============================================================================
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
@brief 八叉树调参 
该结构与 mechanics_system.cpp 中 file-local 实现的常量保持兼容，
便于后续把物理系统的实现迁移到 SceneSystem 时无回归差异。
*/
// ============================================================================
// OctreeConfig八叉树参数配置
// ============================================================================
struct OctreeConfig {
    // 最大递归深度 = 6 —— 八叉树最多往下分 6 层,物体太密集，无限制地分裂下去会消耗大量内存，
    int   max_depth            = 6;
  
    int   max_objects_per_leaf = 4;
    // 根盒外扩 = 0.01 —— 根节点（整个八叉树的最外层盒子）稍微扩大一点点
    float root_padding         = 0.01f;
};

// ============================================================================
// Octree模板类
// ============================================================================


template <typename TPayload>
class Octree {
   public:  

    // =========================================================================
    // Entry —— 八叉树中存储的每一个"条目"
    // =========================================================================
    // 每个 Entry 包含两个信息：
    //   1. payload —— 实际要存储的数据（比如物体指针、实体ID等）
    //   2. bounds  —— 这个物体的"地盘"（AABB包围盒），用于空间计算
    struct Entry {
        TPayload payload;  // 载荷
        AABB     bounds;   // 包围盒
    };

    explicit Octree(OctreeConfig cfg = {}) : cfg_(cfg) {}


    void clear() noexcept {
        root_.reset();
    }

    // =========================================================================
    // rebuild() —— 全量重建八叉树
    // =========================================================================
    // 每次调用都会把旧的树丢掉，从零构建一棵新树。
    // 构建过程：
    //   1. 创建根节点（root_），设置它的 bounds 为整个场景范围
    //   2. 逐个调用 insert() 把每个 Entry 插入到树的合适位置
    //           ↓
    //   遇到叶节点满员 → 分裂（切成8块） → 物体下沉到对应的子格子里
    //           ↓
    //   跨分割面的物体留在当前节点（因为无法塞进任何一个子格子）
    void rebuild(const AABB& root, std::span<const Entry> entries) {
        //创建根节点：std::make_unique<Node>() 相当于 new Node，但返回智能指针
        root_ = std::make_unique<Node>();
        // 设置整个树的为场景总包围盒
        root_->bounds = root;
        // 遍历所有要插入的条目，逐个插入到树中
        //   const auto& e 是范围 for 循环：依次取出 entries 中的每个元素，用只读引用访问
        for (const auto& e : entries) {
            //从根节点开始插入，当前深度为 0（第 0 层）
            insert(root_.get(), e, 0);
           
        }
    }

   
    [[nodiscard]] std::size_t size() const noexcept {
        // 递归遍历整棵树，统计所有节点的 entries 数量之和
        return count_entries(root_.get());
    }

  
    [[nodiscard]] bool empty() const noexcept {
        // 条件：根节点为空（从未构建过），或者整棵树的条目总数为 0
       //如果 root_ 内部的指针是 nullptr，
        // 那肯定是空树。
        return !root_ || count_entries(root_.get()) == 0;
    }

    
    [[nodiscard]] const OctreeConfig& config() const noexcept { return cfg_; }

    // ============================================================================
    // 查询接口（递归 + 剪枝）
    // ============================================================================

    // 功能：找出所有与给定 AABB（轴对齐包围盒）相交的物体
   
    void query_aabb(const AABB& box, std::vector<TPayload>& out) const {
        // 如果树还没构建过（root_ 为空），直接返回
        if (!root_) return;
        // 从根节点开始递归查询
        query_aabb_impl(root_.get(), box, out);
    }

    // =========================================================================
    // query_sphere() —— 球体查询
    // =========================================================================
    //   center —— 球心位置（三维向量 fvec3，包含 x, y, z 三个分量）
    //   radius —— 球体半径（单位与场景坐标系一致）
    //   out    —— 输出参数，查询结果追加到这里
    void query_sphere(const ktm::fvec3& center, float radius,
                      std::vector<TPayload>& out) const {
        if (!root_) return;
        // 从根节点开始递归，用球体与 AABB 的距离判断是否相交
        query_sphere_impl(root_.get(), center, radius, out);
    }

 
    template <typename Predicate>
    void query_if(Predicate&& pred, std::vector<TPayload>& out) const {
        if (!root_) return;
        // Predicate&& 是"转发引用"（也叫万能引用），既能接受左值也能接受右值
        query_if_impl(root_.get(), pred, out);
    }

    // =========================================================================
    // collect_pairs() —— 收集所有可能碰撞的 payload 对
    // =========================================================================
    // 功能：找出树中所有 AABB 两两重叠的物体对，用 (较小, 较大) 排序保证每对只出现一次。
    //
    //
    // "i < j, 去重" 的含义：如果物体 A 和物体 B 的包围盒相交，结果中只会出现 (A, B)，
    // 不会出现 (B, A)。用 payload 的比较（operator<）来决定谁放前面。
    void collect_pairs(std::vector<std::pair<TPayload, TPayload>>& out) const {
        if (!root_) return;
        // 核心函数：从根节点开始，递归收集所有碰撞对
        collect_pairs_impl(root_.get(), out);
    }


    // Stats —— 统计信息（调试用）
    struct Stats {
        std::size_t entries        = 0;  // 树中一共存了多少条目
        int         nodes          = 0;  // 树中一共有多少个节点（包括内部节点和叶节点）
        int         leaves         = 0;  // 树中一共有多少个叶节点（没有子节点的节点）
        int         max_depth_used = 0;  // 实际使用的最大深度（可能小于 max_depth 配置）
    };

    // stats() —— 获取树的统计信息
    // 用途：调试时查看八叉树的"健康状况"，比如是否某些分支过深、是否有太多跨层条目等。
    [[nodiscard]] Stats stats() const noexcept {
        Stats s;  // 创建一个 Stats 结构体，初始值都是 0
        // 从根节点开始递归收集统计信息，初始深度为 0
        gather_stats(root_.get(), s, 0);
        return s;
    }

   private: 

    // Node —— 八叉树中的一个"节点"（树的内部节点或叶子节点）

    
    struct Node {
        AABB                                bounds;   // 这个节点管辖的空间范围（一个长方体）
        std::vector<Entry>                  entries;  // 存储在该节点的条目列表
        std::array<std::unique_ptr<Node>, 8> children{}; // 8 个子节点的指针数组
                                                         // {} 表示初始化为 nullptr（空指针）
        bool                                is_leaf = true; // 是否为叶节点（默认一开始就是叶子）
    };

    // =========================================================================
    // octant_index() —— 计算某个点在中心点的哪个"八分区"
    // =========================================================================
    // 思路：给定父节点的中心点 center，判断 point 在中心的哪个方向。
    // 用 3 个二进制位（bit）表示 3 个轴的"大于等于":
    //   bit 0（值为 1）→ X 轴：point.x >= center.x ? 1 : 0
    //   bit 1（值为 2）→ Y 轴：point.y >= center.y ? 2 : 0
    //   bit 2（值为 4）→ Z 轴：point.z >= center.z ? 4 : 0
   
   
    static int octant_index(const ktm::fvec3& center, const ktm::fvec3& point) {
    
        return (point.x >= center.x ? 1 : 0)   // X 轴的 bit（位置 0，值为 1）
             | (point.y >= center.y ? 2 : 0)   // Y 轴的 bit（位置 1，值为 2）
             | (point.z >= center.z ? 4 : 0);  // Z 轴的 bit（位置 2，值为 4）
    }

    // =========================================================================
    // child_bounds() —— 根据 octant 编码计算子节点的 AABB
    // =========================================================================
    // 功能：给定父节点的 bounds 和 octant 编号（0~7），算出对应子节点的空间范围。
    //
    // 原理：把父盒沿中心点切成两个"半区"，每个轴根据对应 bit 取上/下半区：
    //   - octant 的 bit 0（值为1）为 1 → X 轴取右半区（c.x ~ parent.max.x）
    //   - octant 的 bit 0（值为1）为 0 → X 轴取左半区（parent.min.x ~ c.x）
    //   - octant 的 bit 1（值为2）为 1 → Y 轴取上半区（c.y ~ parent.max.y）
    //   - octant 的 bit 1（值为2）为 0 → Y 轴取下半区（parent.min.y ~ c.y）
    //   - octant 的 bit 2（值为4）为 1 → Z 轴取上半区（c.z ~ parent.max.z）
    //   - octant 的 bit 2（值为4）为 0 → Z 轴取下半区（parent.min.z ~ c.z）
    static AABB child_bounds(const AABB& parent, int octant) {
        // 先计算父盒的中心点
        ktm::fvec3 c = parent.center();
        AABB child;  // 创建子节点包围盒

        // X 轴：octant & 1 是按位与运算，用来检测 bit 0 是否为 1
        //    如果是 1 → 取右半区（中心到右边界）；如果是 0 → 取左半区（左边界到中心）
        child.min.x = (octant & 1) ? c.x : parent.min.x;   // 左边界
        child.max.x = (octant & 1) ? parent.max.x : c.x;   // 右边界

        // Y 轴：octant & 2 检测 bit 1
        child.min.y = (octant & 2) ? c.y : parent.min.y;   // 下边界
        child.max.y = (octant & 2) ? parent.max.y : c.y;   // 上边界

        // ④ Z 轴：octant & 4 检测 bit 2
        child.min.z = (octant & 4) ? c.z : parent.min.z;   // 后边界
        child.max.z = (octant & 4) ? parent.max.z : c.z;   // 前边界

        return child;
    }

    // fits_in_one_octant() —— 判断一个 AABB 是否完全落入某个子八分区

    int fits_in_one_octant(const AABB& parent, const AABB& box) const {
        ktm::fvec3 c = parent.center();           // 父盒中心点
        int idx_min = octant_index(c, box.min);   // 盒子最小角（左下后）落在哪个八分区
        int idx_max = octant_index(c, box.max);   // 盒子最大角（右上前）落在哪个八分区
        // 如果最小角和最大角在同一个分区 → 整个盒子都在那个分区里 → 可以安全下沉到子节点
        // 否则返回 -1，表示"这个盒子跨分割面了，不能往下塞，留在当前节点"
        return (idx_min == idx_max) ? idx_min : -1;
    }

    // subdivide() —— 分裂：把当前节点切成 8 个子节点，并重新分配条目
   
    // 触发条件：叶节点的条目数超过了 cfg_.max_objects_per_leaf（默认 4 个）。

    void subdivide(Node* node, int depth) {
        // 创建 8 个子节点
        for (int i = 0; i < 8; ++i) {
            // 用 std::make_unique 创建新节点（智能指针管理，自动释放内存）
            node->children[i] = std::make_unique<Node>();
            // 根据父节点的 bounds 和 octant 编号 i，计算这个子节点的空间范围
            node->children[i]->bounds = child_bounds(node->bounds, i);
        }
        // 标记当前节点不再是叶节点（已经分裂了）
        node->is_leaf = false;


        std::vector<Entry> old_entries;
        old_entries.swap(node->entries);
        // 遍历旧条目，尝试下沉
        for (const auto& e : old_entries) {
            // 判断这个条目的包围盒能塞进哪个子分区
            int idx = fits_in_one_octant(node->bounds, e.bounds);
            if (idx >= 0) {
                // idx >= 0 → 完全落入第 idx 个子分区 → 下沉（塞进对应子节点的 entries 列表）
                node->children[idx]->entries.push_back(e);
            } else {
                // idx == -1 → 跨分割面 → 留在当前节点（因为放哪个子节点都不完整）
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

    // =========================================================================
    // insert() —— 将一个条目插入到八叉树的合适位置（递归函数）
    // =========================================================================
    //   node  —— 当前节点指针
    //   entry —— 要插入的条目（只读引用）
    //   depth —— 当前递归深度（用来和 max_depth 比较，防止无限递归）
 
    void insert(Node* node, const Entry& entry, int depth) {
        if (node->is_leaf) {
       
            // 条件判断：是否可以直接插入（不分裂）
            // 条目数 < 阈值（还没满）→ 直接放，条件成立
            //  深度 >= 上限（不能再分了）→ 强行放，条件成立
            if (static_cast<int>(node->entries.size()) < cfg_.max_objects_per_leaf
                || depth >= cfg_.max_depth) {
                node->entries.push_back(entry);  // 直接追加到当前节点的条目列表里
                return;  // 插入完毕，返回
            }
            // 不满足上面的条件 → 需要分裂（因为满了且还能继续分）
            subdivide(node, depth);
            // 分裂后当前节点变成了内部节点，接下来往下走 "非叶节点" 的逻辑
        }

        // 检查这个 entry 是否能塞进某一个子节点
        int idx = fits_in_one_octant(node->bounds, entry.bounds);
        if (idx >= 0) {
            // idx >= 0 → 能完全落入第 idx 个子分区 → 向子节点递归插入
            insert(node->children[idx].get(), entry, depth + 1);
            // depth + 1：每往下一层，深度计数器加 1
        } else {
            // idx == -1 → 跨分割面 → 留在当前内部节点（这是八叉树的妥协设计）
            node->entries.push_back(entry);
        }
    }

    // =========================================================================
    // count_entries() —— 递归统计一个节点及其所有子节点中的条目总数
    // =========================================================================
    static std::size_t count_entries(const Node* node) {
        if (!node) return 0;  // 空指针检查：如果节点不存在，条目数自然是 0
        std::size_t n = node->entries.size();  // 当前节点保存的条目数
        // 遍历 8 个子节点，递归累加每个子节点的条目数
        for (const auto& child : node->children) {
            if (child) n += count_entries(child.get());  // 如果子节点存在，递归
        }
        return n;
    }

    // ============================================================================
    // 以下是递归查询函数（所有这些函数都遵循"剪枝优先"原则）
    // ============================================================================

    // ============================================================================
    // query_aabb_impl() —— AABB 查询的递归实现
    // ============================================================================
    // 剪枝策略：
    //   第一步：如果当前节点的整个 bounds 与查询 box 不相交 → 直接返回（整棵子树跳过）
    //   第二步：遍历当前节点的所有条目，检查是否与 box 相交，相交就加入结果
    //   第三步：递归遍历所有子节点（子节点会再做第一步的剪枝判断）
    //
    // 为什么先检查节点再检查条目？因为节点级别的剪枝更"划算"——如果整个节点的
    // 范围都不相交，那么它下面几百个条目也不可能相交，一次判断就能省掉大量检查。
    static void query_aabb_impl(const Node* node, const AABB& box,
                                std::vector<TPayload>& out) {
        // ① 节点级剪枝：节点的包围盒与查询盒子不相交 → 跳过整棵子树
        //    overlaps() 返回 true 表示两个 AABB 有交集（哪怕只碰一个边也算）
        if (!node->bounds.overlaps(box)) return;
        // ② 条目级检查：遍历当前节点的所有条目
        for (const auto& e : node->entries) {
            // 如果条目的包围盒与查询盒子有交集 → 把 payload 加入结果列表
            if (e.bounds.overlaps(box)) out.push_back(e.payload);
        }
        // ③ 递归子节点：对每个存在的子节点执行同样的查询逻辑
        for (const auto& child : node->children) {
            if (child) query_aabb_impl(child.get(), box, out);
        }
    }

    // ============================================================================
    // query_sphere_impl() —— 球体查询的递归实现
    // ============================================================================
    // 核心数学问题：如何判断一个 AABB 与一个球体是否相交？
    //
    // 方法：求 AABB 上离球心最近的那个点，如果这个点与球心的距离 <= 半径，则相交。
    //
    // AABB 上离球心最近的点 = 把球心的每个坐标轴分量 "Clamp"（夹紧）到 AABB 的范围内：
    //   - 如果球心.X 在 AABB 的 min.X 和 max.X 之间 → 最近点在 X 轴上就是球心本身，距离为 0
    //   - 如果球心.X < min.X → 最近点在 X 轴上是 min.X，距离 = min.X - 球心.X
    //   - 如果球心.X > max.X → 最近点在 X 轴上是 max.X，距离 = 球心.X - max.X
    //
    // 然后三个轴的距离平方相加，与半径²比较即可（避免开平方根运算，更快）。
    static void query_sphere_impl(const Node* node, const ktm::fvec3& center,
                                  float radius, std::vector<TPayload>& out) {
        float r2 = radius * radius;  // 半径的平方，后面比较距离时用（省去开根号）

        // ① 节点级剪枝：计算节点 AABB 到球心的最近距离²
        //    std::max({A, B, C}) 是 C++11 的三参数 max，取三者的最大值
        //
        //    以 X 轴为例说明三个参数的含义：
        //      node->bounds.min.x - center.x          → 球心在 AABB 左边时的距离
        //      0.0f                                   → 球心在 AABB 内部时的距离（X轴分量为0）
        //      center.x - node->bounds.max.x          → 球心在 AABB 右边时的距离
        //    取三者最大值 = clamp 效果：如果球心在 AABB 内，max 会取 0
        float dx = std::max({node->bounds.min.x - center.x, 0.0f, center.x - node->bounds.max.x});
        float dy = std::max({node->bounds.min.y - center.y, 0.0f, center.y - node->bounds.max.y});
        float dz = std::max({node->bounds.min.z - center.z, 0.0f, center.z - node->bounds.max.z});
        // 如果最近距离的平方 > 半径的平方，说明 AABB 整个在球体外，整棵子树都可以跳过
        if (dx * dx + dy * dy + dz * dz > r2) return;

        // ② 条目级检查：对每个条目做同样的 AABB vs 球体相交判断
        for (const auto& e : node->entries) {
            dx = std::max({e.bounds.min.x - center.x, 0.0f, center.x - e.bounds.max.x});
            dy = std::max({e.bounds.min.y - center.y, 0.0f, center.y - e.bounds.max.y});
            dz = std::max({e.bounds.min.z - center.z, 0.0f, center.z - e.bounds.max.z});
            // 距离² <= 半径² → 相交 → 加入结果
            if (dx * dx + dy * dy + dz * dz <= r2) out.push_back(e.payload);
        }
        // ③ 递归子节点
        for (const auto& child : node->children) {
            if (child) query_sphere_impl(child.get(), center, radius, out);
        }
    }

    // ============================================================================
    // query_if_impl() —— 自定义谓词查询的递归实现
    // ============================================================================
    // 这是最通用的查询方式：由调用者提供一个判断函数 pred。
    //
    // 剪枝方式与前两个不同：
    //   - AABB/球体查询用固定的几何公式判断是否跳过节点
    //   - 谓词查询由外部定义的 pred 函数决定：pred(node->bounds) 返回 false → 跳过
    //
    // 注意：template <typename Predicate> 在函数前面，表示 Predicate 是函数模板参数。
    //       编译器会在编译时为每个不同的 pred 类型生成专门的版本（零虚函数开销）。
    template <typename Predicate>
    static void query_if_impl(const Node* node, const Predicate& pred,
                              std::vector<TPayload>& out) {
        // ① 节点级剪枝：用谓词判断 — 如果 pred 说"这个节点的范围不满足条件"，整棵子树跳过
        if (!pred(node->bounds)) return;
        // ② 条目级检查：对每个条目用谓词判断
        for (const auto& e : node->entries) {
            if (pred(e.bounds)) out.push_back(e.payload);
        }
        // ③ 递归子节点
        for (const auto& child : node->children) {
            if (child) query_if_impl(child.get(), pred, out);
        }
    }

    // ============================================================================
    // query_straddle_in_subtree() —— 跨层级碰撞检测
    // ============================================================================
    // 功能：检查一个"跨分割面"的条目（straddle），与某个子树中的所有条目是否有 AABB 重叠。
    //
    // 使用场景：collect_pairs_impl 的第③类碰撞
    //   某个物体太大，跨了当前节点的分割面（所以存在当前节点的 entries 中）。
    //   但它可能与子节点里的小物体碰撞——所以需要把"跨分割面物体"与"子树中的所有物体"
    //   做一次碰撞检测。
    //
    // 参数：
    //   straddle —— 跨分割面的那个条目
    //   subtree  —— 子树的根节点
    //   out      —— 输出碰撞对
    static void query_straddle_in_subtree(const Entry& straddle, const Node* subtree,
                                           std::vector<std::pair<TPayload, TPayload>>& out) {
        // ① 节点级剪枝：如果跨层条目与整个子树的 bounds 都不相交，整棵子树都不可能有碰撞
        if (!straddle.bounds.overlaps(subtree->bounds)) return;
        // ② 检查跨层条目与子树中每个条目的 AABB 是否相交
        for (const auto& e : subtree->entries) {
            if (straddle.bounds.overlaps(e.bounds)) {
                // 找到一对碰撞！用 payload 的大小比较来排序——保证结果集合中每一对
                // 只出现一次，且顺序一致（小在前，大在后）。
                auto a = straddle.payload;
                auto b = e.payload;
                // emplace_back：直接在 vector 末尾"原地构造"一个 pair，比 push_back 少一次拷贝
                // (a < b ? a : b) 取较小的作为 first，(a < b ? b : a) 取较大的作为 second
                out.emplace_back(a < b ? a : b, a < b ? b : a);
            }
        }
        // ③ 如果子树已经是叶节点 → 不需要再深入（叶节点没有子节点）
        if (subtree->is_leaf) return;
        // ④ 递归深入子树的每个子节点（继续用 AABB 剪枝）
        for (const auto& child : subtree->children) {
            if (child) query_straddle_in_subtree(straddle, child.get(), out);
        }
    }

    // ============================================================================
    // compare_subtrees() —— 跨子树碰撞检测
    // ============================================================================
    //检查两棵子树的条目之间是否有 AABB 重叠。
    //
    // 使用场景：collect_pairs_impl 的第④类碰撞 
    //   两个不同的子分区之间可能有碰撞（比如左边格子里的物体和右边格子里的物体碰到）
    //
    // 剪枝策略：先检查两棵子树根节点的 AABB 是否相交 —
    //   如果不相交，那这两棵子树里的所有物体都不可能有碰撞，直接跳过。
    static void compare_subtrees(const Node* a, const Node* b,
                                  std::vector<std::pair<TPayload, TPayload>>& out) {
        // ① 节点级剪枝：两棵子树的根节点 AABB 不相交 → 不可能有任何碰撞对，直接跳过
        if (!a->bounds.overlaps(b->bounds)) return;
        // ② 两两比较两个节点的所有条目
        //    注意：这里的两层嵌套循环是"笛卡尔积"——A的每个条目 与 B的每个条目 检查一次
        for (const auto& ea : a->entries) {
            for (const auto& eb : b->entries) {
                if (ea.bounds.overlaps(eb.bounds)) {
                    auto pa = ea.payload;
                    auto pb = eb.payload;
                    // 有序存储：小的在前，大的在后，保证去重
                    out.emplace_back(pa < pb ? pa : pb, pa < pb ? pb : pa);
                }
            }
        }
        // ③ 如果两个节点都是叶子 → 没有子节点可以继续比较，结束
        if (a->is_leaf && b->is_leaf) return;

        // ④ 根据两棵子树的结构，选择不同的递归策略
       
        // 情况1：两边都不是叶子 → 递归比较各自子节点的所有组合
        //        （A的8个子节点 × B的8个子节点 = 最多64种组合）
        if (!a->is_leaf && !b->is_leaf) {
            for (const auto& ca : a->children) {
                if (!ca) continue;  // 跳过不存在的子节点（理论上8个都存在，但安全检查）
                for (const auto& cb : b->children) {
                    if (!cb) continue;  // 同上
                    // 递归：比较A的第ca个子树 与 B的第cb个子树
                    compare_subtrees(ca.get(), cb.get(), out);
                }
            }
        }
        // 情况2：只有 a 不是叶子（b 是叶子）→ 把 a 的每个子节点与 b 比较
        else if (!a->is_leaf) {
            for (const auto& ca : a->children) {
                if (ca) compare_subtrees(ca.get(), b, out);
            }
        }
        // 情况3：只有 b 不是叶子（a 是叶子）→ 把 b 的每个子节点与 a 比较
        else {
            for (const auto& cb : b->children) {
                if (cb) compare_subtrees(a, cb.get(), out);
            }
        }
    }

    // ============================================================================
    // collect_pairs_impl() —— 碰撞对收集的核心递归实现
    // ============================================================================
    
    static void collect_pairs_impl(const Node* node,
                                   std::vector<std::pair<TPayload, TPayload>>& out) {
        // 空节点检查
        if (!node) return;

        // ===== 情况①：叶节点内的碰撞 =====
        if (node->is_leaf) {
            // 两两比较叶节点中所有条目（标准的"组合数"循环：i从0开始，j从i+1开始，
            // 保证每对只检查一次，不会出现 (A,B) 和 (B,A) 的重复）
            for (std::size_t i = 0; i < node->entries.size(); ++i) {
                for (std::size_t j = i + 1; j < node->entries.size(); ++j) {
                    // 检查两个条目的 AABB 是否相交
                    if (node->entries[i].bounds.overlaps(node->entries[j].bounds)) {
                        auto a = node->entries[i].payload;
                        auto b = node->entries[j].payload;
                        // 有序存储：(较小的payload, 较大的payload)
                        out.emplace_back(a < b ? a : b, a < b ? b : a);
                    }
                }
            }
            // 叶节点没有子节点，处理完返回
            return;
        }

        for (std::size_t i = 0; i < node->entries.size(); ++i) {
            for (std::size_t j = i + 1; j < node->entries.size(); ++j) {
                if (node->entries[i].bounds.overlaps(node->entries[j].bounds)) {
                    auto a = node->entries[i].payload;
                    auto b = node->entries[j].payload;
                    out.emplace_back(a < b ? a : b, a < b ? b : a);
                }
            }
        }

      
        for (const auto& straddle : node->entries) {
            for (const auto& child : node->children) {
                if (child) {
                    // 把这个跨分割面的条目与整棵子树做碰撞检测（递归 + AABB剪枝）
                    query_straddle_in_subtree(straddle, child.get(), out);
                }
            }
        }

        // ===== 情况④：跨子树碰撞 =====
        // "不同子节点"之间的两两比较
        // ci 从 0 到 6，cj 从 ci+1 到 7 —— 保证每对子树只比较一次
        for (int ci = 0; ci < 8; ++ci) {
            if (!node->children[ci]) continue;  // 跳过不存在的子节点
            for (int cj = ci + 1; cj < 8; ++cj) {
                if (!node->children[cj]) continue;  // 跳过不存在的子节点
                // 递归比较两棵子树之间的碰撞对
                compare_subtrees(node->children[ci].get(), node->children[cj].get(), out);
            }
        }

    
        for (const auto& child : node->children) {
            if (child) collect_pairs_impl(child.get(), out);
        }
    }


    static void gather_stats(const Node* node, Stats& s, int depth) {
        if (!node) return;                    // 空节点 → 什么都不统计
        s.entries += node->entries.size();    // 累加当前节点的条目数
        ++s.nodes;                            // 节点数 +1
        // 更新最大深度：取已有最大深度和当前深度的较大值
        s.max_depth_used = std::max(s.max_depth_used, depth);
        if (node->is_leaf) {
            ++s.leaves;  // 如果是叶节点，叶节点计数 +1
        } else {
            // 如果是内部节点，递归遍历所有子节点
            for (const auto& child : node->children) {
                if (child) gather_stats(child.get(), s, depth + 1);
            }
        }
    }

 
    OctreeConfig            cfg_;
    //
    std::unique_ptr<Node>   root_;
};


}  // namespace Corona::Spatial