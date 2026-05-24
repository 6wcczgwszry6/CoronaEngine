# 场景管理 / 视锥剔除 / LRU 持久化 — 需求分析与设计文档

> 文档版本：v0.2
> 关联需求：
> 1. 八叉树挪至场景管理（现位于物理系统）
> 2. 基于 Camera 位置的视锥剔除 / 遮挡剔除
> 3. 接入 LRU，实现剔除后序列化 / 反序列化

---

## 进度跟踪（最新）

| 里程碑 | 状态 | 备注 |
|---|---|---|
| **M1.0 SceneSystem 骨架** | ✅ 已完成 | commit `85b401f`：新增 `SceneSystem`(优先级 88)、`Spatial::AABB/Octree<T>`、`Math::Frustum`、`scene_system_events.h`，并注册到 `Engine`；后续提交已补入 `update()` / 查询接口 / 可见性热度预埋 |
| M1.1 在 `update()` 中遍历 `SharedDataHub::scene_storage()` 重建八叉树 + 写回 `SceneDevice` AABB | ⚠️ 已实现（有缺陷） | commits `4c87c5b` + `df3034e` + `4083e62`：`SceneSystem::update()` 已遍历 `scene_storage`、重建 `Octree` 并写回 `SceneDevice` AABB；但当前直接使用 `MechanicsDevice.min_xyz/max_xyz`，尚未像 `MechanicsSystem` 那样结合 transform 展开世界 AABB |
| M1.2 八叉树查询实现（aabb / sphere / frustum / pairs）| ⚠️ 已实现（有缺陷） | commits `0b38920` + `4f90e4d` + `4083e62`：`query_aabb / query_sphere / query_frustum / query_pairs` 已接入 `Spatial::Octree<T>`；但 `query_aabb/query_sphere/query_if` 递归未处理内部节点 `entries`，大包围盒/跨子节点对象会漏查 |
| M1.3 `MechanicsSystem` 改为消费 `SceneSystem::query_pairs` | ⏳ 待办 | 物理仍在本地临时建树并 `collect_pairs()` |
| M1.4 SceneDevice AABB 数据所有权迁移 | ⏳ 待办 | `SceneSystem` 与 `MechanicsSystem` 目前都会写 `min_world/max_world/center_world`，所有权仍未统一 |
| **M2 视锥剔除接入 OpticsSystem** | 🟡 准备中 | `Math::Frustum` 与 `SceneSystem::query_frustum()` 已存在，但 `OpticsSystem` 仍按 actor 全量遍历，尚未接入查询结果 |
| **M3 内存 LRU + 同步序列化** | 🟡 预埋中 | `ca1ff70` 补了 `ActorLoadState`，`SceneSystem` 已有 `invisible_frames` / `offline_actors` / `ActorEvictRequestedEvent` 预埋；`ActorCache` / 序列化 / restore pipeline 仍未接入 |
| **M4 磁盘 LRU + 异步唤醒** | ⏳ 未开始 | |
| **M5 遮挡剔除（可选）** | ⏳ 未开始 | |

> 2026-05-12 提交核对：`4c87c5b` 对应 M1.1 主体，`0b38920` / `4f90e4d` / `4083e62` 对应 M1.2 主体与修补，`ca1ff70` 属于 M3/M4 的加载状态预埋，`0bf7f89` 仅更新 `.gitignore`，不影响里程碑完成度。

> 已落地文件：
> - [include/corona/spatial/aabb.h](../include/corona/spatial/aabb.h)
> - [include/corona/spatial/octree.h](../include/corona/spatial/octree.h)
> - [include/corona/math/frustum.h](../include/corona/math/frustum.h) + [src/systems/scene/frustum.cpp](../src/systems/scene/frustum.cpp)
> - [include/corona/systems/scene/scene_system.h](../include/corona/systems/scene/scene_system.h) + [src/systems/scene/scene_system.cpp](../src/systems/scene/scene_system.cpp)
> - [include/corona/events/scene_system_events.h](../include/corona/events/scene_system_events.h)
> - [src/engine.cpp](../src/engine.cpp) 中 `register_systems()` 已注册 `SceneSystem`

---

## 0. 现状速览

| 关注点 | 现状 | 文件 |
|---|---|---|
| 八叉树 | 通用 `Spatial::Octree<T>` 已落地并被 `SceneSystem` 使用；`MechanicsSystem` 不再持有 file-local octree 类型，但仍在 `update()` 内临时建树并 `collect_pairs()`，尚未切到 `SceneSystem::query_pairs()` | [include/corona/spatial/octree.h](../include/corona/spatial/octree.h)、[src/systems/scene/scene_system.cpp](../src/systems/scene/scene_system.cpp)、[src/systems/mechanics/mechanics_system.cpp](../src/systems/mechanics/mechanics_system.cpp) |
| 场景管理 | 已有独立 `SceneSystem`，维护 per-scene octree / `SceneStats` / 可见性热度；`SceneDevice` 仍是 POD，且 AABB 当前被 `SceneSystem` 与 `MechanicsSystem` 双写，所有权未统一 | [include/corona/systems/scene/scene_system.h](../include/corona/systems/scene/scene_system.h)、[src/systems/scene/scene_system.cpp](../src/systems/scene/scene_system.cpp)、[include/corona/shared_data_hub.h](include/corona/shared_data_hub.h#L212-L222) |
| Camera | `CameraDevice` 已具备 `position / forward / world_up / fov / aspect / near_plane / far_plane`，并提供 `compute_view_matrix() / compute_projection_matrix() / compute_view_proj_matrix()`（Vulkan NDC） | [include/corona/shared_data_hub.h](include/corona/shared_data_hub.h#L143-L206) |
| 渲染剔除 | `OpticsSystem` 渲染时仍**无任何空间裁剪**，按 actor 列表线性遍历；`SceneSystem` 已能基于 camera 构造 frustum 做查询，但结果尚未接入渲染管线 | [src/systems/optics/optics_system.cpp](../src/systems/optics/optics_system.cpp)、[src/systems/scene/scene_system.cpp](../src/systems/scene/scene_system.cpp) |
| LRU | 正式 `ActorCache` / 磁盘 LRU 仍不存在；但 `SceneSystem` 已预埋 `invisible_frames` / `offline_actors` / `ActorLoadState`，并会发布 `ActorEvictRequestedEvent` | [src/systems/scene/scene_system.cpp](../src/systems/scene/scene_system.cpp)、[include/corona/events/scene_system_events.h](../include/corona/events/scene_system_events.h) |
| 序列化 | 工程依赖 `nlohmann_json`；`coronaresource::scene::desc` 已有 JSON schema（`scene_desc.h / node_desc.h / json_importer.hpp`），但**主工程的 `SceneDevice / ActorDevice` 没有任何序列化适配器** | coronaresource-src/include/corona/scene/desc/ |

**关键结论**：三个需求不是独立特性，**先后顺序紧耦合**——
SceneSystem 是承载八叉树的容器；八叉树的查询能力是视锥剔除的基础；剔除结果（"近期不可见集合"）是 LRU 触发卸载/序列化的输入。
故必须按 ① → ② → ③ 顺序推进。

---

## 1. 需求一：八叉树迁移至「场景管理」

### 1.1 目标
- 把空间分割数据结构从物理系统中**抽离**为通用基础设施；
- 由一个新的 `SceneSystem` 持有并维护，每帧更新一次、所有消费者（物理、渲染、音频、脚本）共享读；
- 物理系统改为**消费者**：通过 `SceneSystem` 提供的查询 API 拿到候选对，不再自己建树。

### 1.2 现状痛点
- 八叉树是 `mechanics_system.cpp` 的 file-local 实现（`struct OctreeEntry/OctreeNode` + 多个 `static` 自由函数），无法在其他 TU 复用；
- 每帧从零建树，建完即弃，不能跨帧增量更新；
- `MechanicsSystem` 同时负责"算 AABB" + "建八叉树" + "解算碰撞"，违反单一职责，加大了渲染剔除复用的成本；
- `SceneDevice.min_world/max_world` 由物理系统写入——**渲染想用场景包围盒得等物理跑完**，跨系统时序不清晰。

### 1.3 拆解任务

| # | 任务 | 产物 | 状态 |
|---|---|---|---|
| 1.1 | 新增 `corona::spatial` 命名空间，把 `OctreeNode/OctreeEntry` + 操作函数移入 `include/corona/spatial/octree.h` + `src/spatial/octree.cpp`。模板化 `Entry` 的 payload 类型（默认 `std::uintptr_t`），保留 `aabb_overlap` 等小工具 | 独立可单测的小库 | ✅ 已落地为头文件模板 `Spatial::Octree<T>`（实现内联，未拆 .cpp） |
| 1.2 | 新增 `SceneSystem`（优先级建议 **88**，介于 Geometry(85) 与 Optics(90) 之间，保证 Optics 拉取剔除结果时八叉树已就绪），目录 `src/systems/scene/`，对外接口见 §1.4 | 新系统，注册到 `Engine::register_systems()` | ✅ 骨架完成、已注册；后续提交已补入 `update()`、查询接口与可见性热度预埋 |
| 1.3 | 把 `mechanics_system.cpp` 中"遍历 actors → 算世界 AABB → 写回 `SceneDevice` → 建树"的代码，整体迁入 `SceneSystem::update()` | `MechanicsSystem` 瘦身 | ⚠️ 部分完成：`SceneSystem::update()` 已开始遍历 scene/actor/profile/mechanics 并建树，但当前直接使用 `MechanicsDevice.min_xyz/max_xyz`；`MechanicsSystem` 中原有“算世界 AABB / 写 Scene / 建树”流程仍保留 |
| 1.4 | `MechanicsSystem` 改为调用 `SceneSystem::query_pairs(scene_handle)` 获取碰撞候选对 | 物理仅做窄相+解算 | ⏳ 待办 |
| 1.5 | 八叉树**内化到 `SceneSystem` 私有状态**（不进 `SharedDataHub`，避免暴露可变指针）；通过 `acquire_read` 风格的快照接口供其它系统访问 | 线程安全 | ⚠️ 部分完成：已用 `Impl` + `std::shared_mutex` 保护查询读路径，但 `update()` 对 `scenes/tree/stats` 的写入未整体持有 write lock，读写隔离尚未闭合 |
| 1.6 | 增加 `SceneSystem` 的脏标记：actor transform 未变化时跳过重建（v0.1 可先全量重建，留 TODO） | 可跨帧增量优化 | ⏳ 待办 |

### 1.4 SceneSystem 对外 API（草案）

```cpp
namespace Corona::Systems {

struct SceneQueryResult {
    std::vector<std::uintptr_t> actor_handles;   // 命中的 actor handle
};

class SceneSystem : public Kernel::SystemBase {
public:
    auto get_name() const -> std::string_view override { return "SceneSystem"; }
    auto get_priority() const -> i16 override { return 88; }

    void initialize(ISystemContext* ctx) override;
    void update() override;       // 重建/刷新八叉树，写 SceneDevice 的 AABB
    void shutdown() override;

    // —— 空间查询（只读，线程安全；返回快照） ——
    SceneQueryResult query_aabb (std::uintptr_t scene, const ktm::fvec3& mn, const ktm::fvec3& mx) const;
    SceneQueryResult query_frustum(std::uintptr_t scene, const Math::Frustum& f)        const;
    SceneQueryResult query_sphere (std::uintptr_t scene, const ktm::fvec3& c, float r) const;

    // —— 碰撞用（给物理系统） ——
    std::vector<std::pair<std::uintptr_t,std::uintptr_t>>
        query_pairs(std::uintptr_t scene) const;
};

} // namespace Corona::Systems
```

### 1.5 兼容性 / 风险

- **数据所有权切换**：`SceneSystem` 已开始写 `SceneDevice.min_world/max_world/center_world`，但 `MechanicsSystem` 仍会覆写同一组字段；M1.4 需要收口到单一写入者，否则场景包围盒语义不稳定。
- **优先级 / 时序**：当前优先级为 `Mechanics=75 / Kinematics=80 / Scene=88 / Optics=90`。若 M1.3 目标是让物理同帧消费 `SceneSystem::query_pairs()`，那么 88 并不满足“Scene 在 Mechanics 之前”；要么调整优先级，要么明确物理读取上一帧快照。
- **读写锁闭环**：查询路径已上 `shared_lock`，但 `SceneSystem::update()` 对 `tree/stats/invisible_frames` 的写入未整体纳入 `unique_lock`；若系统并行查询，该实现仍有 data race 风险。
- **handle → 实体类型**：八叉树现仅存 `uintptr_t`，含义靠调用约定。迁移后建议把"该 handle 是 actor / 是 emitter / 是 light"等元信息附加到 `OctreeEntry` 的 `Payload` 模板参数，避免后续渲染剔除误把不可渲染对象塞进结果。

---

## 2. 需求二：基于 Camera 的视锥剔除（与遮挡剔除）

### 2.1 目标
- `OpticsSystem` 在每帧渲染前，**只**遍历对当前 Camera **可能可见**的 actor，避免无效绘制。
- v0.1 先做**视锥剔除（Frustum Culling）**，达到 90% 收益；遮挡剔除（Occlusion Culling）作为 v0.2 增量。

### 2.2 拆解任务

| # | 任务 | 备注 | 状态 |
|---|---|---|---|
| 2.1 | 新增 `include/corona/math/frustum.h`：从 `view * proj` 矩阵提取 6 个平面（Hartmann & Gribb 法），提供 `intersects(AABB)` 三态结果（Outside / Intersect / Inside） | 纯头文件、可单测 | ✅ 头文件 + `frustum.cpp` 已落地（`Math::Frustum::from_view_proj` / `from_camera` / `intersects(AABB)`） |
| 2.2 | `SceneSystem::query_frustum()` 实现：DFS 八叉树，节点 vs 平面：Outside 剪枝；Inside 全收；Intersect 递归 | 复用 §1.1 的八叉树 | ⚠️ 已实现（有缺陷）：`SceneSystem::query_frustum()` 已接入 `Octree::query_if()`；但当前 `query_if_recursive()` 未遍历内部节点 `entries`，会漏掉跨多个子节点的大包围盒 actor |
| 2.3 | 在 `OpticsSystem` 渲染入口（每个 Camera 一次）调用 `query_frustum`，用结果替换原 actor 全量遍历 | 关键集成点 | ⏳ 待办 |
| 2.4 | 增加调试可视化：UI 开关 `Optics > Show Culling Stats`，输出 `total / visible / culled` 三个数 | 验收必备 | ⏳ 待办（`SceneStats` 已开始写 `actor_total / actor_visible / octree_entries`，但 UI 尚未接线） |
| 2.5 | 多相机场景：每个 active camera 各自做一次剔除；离屏相机（`surface == nullptr`）若禁用则跳过 | 与 `CameraDevice.surface` 配合 | ⏳ 待办 |

### 2.3 视锥构造（落到 Camera 已有字段）

```cpp
Math::Frustum Math::Frustum::from_camera(const CameraDevice& c) {
    auto vp = c.compute_view_proj_matrix();   // Vulkan NDC, Y-down
    return from_view_proj(vp);                // 行抽取 6 平面
}
```
> 注意：项目使用 Vulkan NDC（z∈[0,1], y 翻转）。提取 near 平面时用 `row3` 而不是 `row3+row2`，否则 near 截断会偏。

### 2.4 遮挡剔除（v0.2，仅做方案选型，不在本次实现）

候选方案三选一：
| 方案 | 复杂度 | 适用场景 | 备注 |
|---|---|---|---|
| **CPU Hi-Z / Software Rasterizer**（如 Intel Masked SOC）| 高 | 室内、密集遮挡 | 需额外维护代理网格 |
| **GPU Occlusion Query**（VK_QUERY_TYPE_OCCLUSION）| 中 | 简单场景 | 1 帧延迟、与现 OpticsSystem 调度耦合 |
| **PVS / Portal**（预计算）| 低运行时 / 高离线 | 关卡型 | 需关卡编辑器支持，与本引擎当前形态不匹配 |

**建议**：v0.2 选 GPU Occlusion Query；若发现 actor 数仍偏少（< 1k），可把遮挡剔除推迟到 v0.3。

### 2.5 风险
- 视锥平面提取的列/行序与 ktm 的矩阵布局必须严格一致，建议加单元测试（手算单位立方体可见性 8 个角点对比）；
- skybox / 阴影 caster 必须**绕过**视锥剔除，需在 `ActorDevice` 上加 `bool ignore_frustum_cull{false}` 字段（或独立 tag）。

---

## 3. 需求三：接入 LRU，实现剔除后序列化 / 反序列化

### 3.1 目标
- 把"被视锥剔除掉、连续 N 帧不可见"的 actor，从 GPU/内存中**卸载**，序列化到磁盘；
- 当再次进入视锥时，从磁盘**反序列化**回内存并重建 GPU 资源；
- 用 LRU 作为热度判定与容量上限控制器，避免内存抖动。

### 3.2 现状对接

`coronaresource` 中 `lru_cache_example` 已经把要点（双层 Memory + Disk、淘汰刷盘、key 字符串、value 二进制）做完了，但它有三个问题让它不能直接当生产实现用：

1. 它在 example 目录，未对外导出 target；需提升为 `coronaresource::lru` 公共库（或在主工程内做 fork+裁剪，根据 coronaresource 的更新节奏决定）；
2. 它的 value 是 `std::vector<char>` 裸缓冲，**没有类型化序列化适配**；
3. 它没有"淘汰回调"——主工程需要在 evict 时拿到 key 才能去清 GPU 资源。

### 3.3 拆解任务

| # | 任务 | 备注 | 状态 |
|---|---|---|---|
| 3.1 | 提升 `lru_cache_example` 为 `coronaresource::lru` 公共 target；为 `MemoryCache` / `CacheManager` 增加 `set_evict_callback(std::function<void(const std::string&, CacheItem&&)>)` | 上游改 | ⏳ 待办 |
| 3.2 | 主工程新增 `Corona::Cache::ActorCache`，封装 `CacheManager`，提供类型化 API：`put(handle, ActorSnapshot)` / `get(handle) -> std::optional<ActorSnapshot>` / `evict(handle)` | 适配层 | ⏳ 待办 |
| 3.3 | 定义 `ActorSnapshot`：包含 `ModelTransform`、引用的 `model resource id`（不是 mesh 数据本身——mesh 走 ResourceManager 自己的缓存）、物理参数等"重建 actor 所需的最小集" | 新结构 | ⏳ 待办 |
| 3.4 | 用 `nlohmann::json` 给 `ActorSnapshot` 实现 `to_json/from_json`；二进制路径用 cereal 或自研 BSON-like（v0.1 先 JSON，性能不够再换） | 序列化 | ⏳ 待办 |
| 3.5 | `SceneSystem` 维护 `unordered_map<handle, frames_invisible>`：每帧 `query_frustum` 后，命中清零、未命中累加；超过阈值（例如 300 帧 = 5 秒@60Hz）触发 `ActorCache.put()` 并从场景活跃集合移除 | 热度策略 | ⚙️ 部分完成：`SceneSystem` 已维护 `invisible_frames`，并在阈值达到时发布 `ActorEvictRequestedEvent`；但尚未接入 `ActorCache.put()`，也未把 actor 从场景活跃集合移除 |
| 3.6 | 当 `query_frustum` 命中一个**已卸载**的 handle（需要保留卸载占位 + 包围盒；这部分仍留在八叉树中作为"幽灵节点"）时，调 `ActorCache.get()` 异步反序列化、上传 GPU 资源、重新加入活跃集合 | 唤醒路径 | ⚙️ 预埋接口：`is_actor_offline / mark_actor_restored / get_actor_load_state` 已就位，但尚未形成 restore / 反序列化 / GPU 重建流程 |
| 3.7 | 卸载 / 唤醒事件通过 `EventBus` 广播（`ActorEvictRequestedEvent` / `ActorRestoreRequestedEvent`，资源完成后再由 `ActorLoadCompletedEvent` / `ActorUnloadCompletedEvent` 收口），让 OpticsSystem、MechanicsSystem 等有机会清理/重建自己的本地缓存 | 解耦 | ⚠️ 部分完成：事件类型已定义，且 `SceneSystem` 已开始发布 `ActorEvictRequestedEvent`；但 restore 广播尚未接通，且当前 evict 事件聚合初始化未正确填充 `scene/actor` 两个字段 |

### 3.4 数据流图

```
  ┌────────────┐  query_frustum  ┌────────────┐
  │OpticsSystem├────────────────►│SceneSystem │
  └────────────┘                 │  + Octree  │
                                 │  + heat map│
                                 └─────┬──────┘
                            evict│     │restore
                                 ▼     ▲
                          ┌──────────────────┐
                          │ ActorCache (LRU) │
                          │ Memory ─► Disk   │
                          └──────────────────┘
                                 │
                                 ▼  EventBus
                  ActorEvictRequestedEvent / ActorRestoreRequestedEvent
```

### 3.5 风险与权衡

- **"幽灵节点" vs 重新加入八叉树**：被卸载的 actor 必须保留 AABB 在八叉树里，否则永远无法被视锥命中触发 restore。这就要求 `OctreeEntry::payload` 携带"是否在线"的 flag，渲染端必须忽略离线 entry 但 SceneSystem 内部要保留它。
- **资源 id vs actor 数据**：mesh / texture 这种**重资源**已经在 `ResourceManager` 里，自带缓存和 GUID。`ActorSnapshot` 只存 resource id（路径），不要重复序列化几何数据，否则磁盘膨胀严重。
- **磁盘目录策略**：当前 `lru_cache_example` 把 key 直接当文件名，存在路径注入风险（example 已有 `validate_and_normalize_key_path`）。生产化时强制：`{cache_root}/{scene_uuid}/{actor_handle_hex}.actor.json`，禁用任何 `..` / 绝对路径 / 通配符。
- **唤醒延迟**：磁盘读 + 反序列化 + GPU 上传不能在渲染线程同步做。需走 `Kernel::TaskGraph` 异步，渲染端这一帧使用上一帧的可见集合或 placeholder。这是整个需求的最大工程难点，建议在 v0.1 先做**仅内存层 LRU + 同步重建**验证逻辑，v0.2 再上磁盘 + 异步。

---

## 4. 总体里程碑（建议拆分迭代）

| 里程碑 | 范围 | 验收 |
|---|---|---|
| **M1：八叉树独立** | §1.1 ~ §1.5；MechanicsSystem 改用 SceneSystem 的查询接口；现有所有物理用例不回归 | 物理 demo 全通过；新增 `octree` 的单元测试 |
| **M2：视锥剔除** | §2.1 ~ §2.4；UI 显示剔除统计 | 在 `assets/Kitchen_set_usd` 这种重场景下，可见 actor 数 < 总数 50%，且画面无差异 |
| **M3：内存 LRU + 同步序列化** | §3.1 ~ §3.5（不上磁盘，仅 MemoryCache + JSON 内存往返）| 强制循环 evict / restore 100 次场景一致 |
| **M4：磁盘 LRU + 异步唤醒** | §3.6 ~ §3.7；接 `TaskGraph` | 长时间运行不 OOM；重启进程后 disk cache 命中 |
| **M5（可选）：遮挡剔除** | §2.4 选定方案 | 在 PVS/室内 demo 中再降可见 actor ≥ 30% |

---

## 5. 待用户确认的开放问题

1. **SceneSystem 的优先级**：建议 88（在 Geometry 85 与 Optics 90 之间）。是否接受？
2. **八叉树是否泛型化 payload**？（迁移阻力 vs 后续渲染/音频剔除复用收益）
3. **ActorSnapshot 序列化格式**：v0.1 是否接受 JSON（可读、易调）？还是直接上二进制？
4. **LRU 库归属**：上游 `coronaresource` 提升 example 为 public target（需推动上游 PR），还是主工程内 fork 一份？
5. **遮挡剔除**是否纳入本轮交付（M5），还是单独立项？

---
*以上为需求拆解与设计草案，等用户确认开放问题后即可拆 issue / 排期实现。*
