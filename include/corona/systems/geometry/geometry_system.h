#pragma once

#include <horizon.h>

#include <corona/events/geometry_system_events.h>
#include <corona/events/scene_system_events.h>
#include <corona/kernel/event/i_event_bus.h>
#include <corona/kernel/event/i_event_stream.h>
#include <corona/kernel/system/system_base.h>
#include <corona/math/frustum.h>
#include <corona/memory/gpu_mem_ledger.h>
#include <corona/spatial/aabb.h>
#include <corona/spatial/bvh.h>

#include <cstdint>
#include <filesystem>
#include <memory>
#include <optional>
#include <utility>
#include <vector>

namespace Corona::Systems {

/**
 * @brief 物体加载状态枚举
 */
enum class ActorLoadState : uint8_t {
    Loaded,     // 已加载，可正常渲染和物理模拟
    Loading,    // 正在异步加载中
    Unloading,  // 正在异步卸载中
    Unloaded    // 已卸载，数据不在内存中
};

/**
 * @brief 单场景的可见性策略
 */
struct SceneVisibilityConfig {
    /// 连续不可见超过该帧数时，触发 ActorEvictRequestedEvent。
    /// 0 表示永不 evict（默认，避免在 LRU 接入前误触）。
    int  invisible_frames_to_evict = 60;  // 连续不可见1秒(60帧)触发淘汰，0=永不
    bool collect_stats             = true;

    bool enable_distance_culling  = true;   // 是否启用距离剔除
    float unload_distance         = 10.0f;  // 超过此距离且不可见时触发淘汰
    float preload_distance        = 25.0f;  // 进入此距离时触发预加载
};

/**
 * @brief 单场景统计信息（供 UI / 日志读取）
 */
struct SceneStats {
    std::size_t actor_total       = 0;
    std::size_t actor_visible     = 0;  // 上一帧所有相机视锥的并集
    std::size_t actor_offline     = 0;  // 已被 LRU 卸载（M3 起）
    std::size_t octree_entries    = 0;
    double      last_rebuild_ms   = 0.0;
    double      last_query_ms     = 0.0;

    //距离卸载统计
    std::size_t actor_loaded      = 0;
    std::size_t actor_loading     = 0;
    std::size_t actor_unloading   = 0;
    std::size_t actor_unloaded    = 0;
};

// ========================================
// 资源内存账本（P0：mesh / texture 的 CPU + GPU 计量）
// ========================================

/**
 * @brief 单个内存池（VRAM 或 RAM）的用量 + 预算视图
 *
 * 只"计量与计算预算"，不触发淘汰。need_free_bytes 供后续淘汰步骤消费。
 */
struct MemoryPoolReport {
    std::size_t mesh_bytes      = 0;  ///< mesh 占用
    std::size_t texture_bytes   = 0;  ///< texture 占用
    std::size_t used_bytes      = 0;  ///< mesh + texture
    std::size_t budget_bytes    = 0;  ///< 预算上限，0 = 不限制
    std::size_t high_bytes      = 0;  ///< 高水位（触发淘汰阈值）
    std::size_t low_bytes       = 0;  ///< 低水位（淘汰目标）
    std::size_t over_bytes      = 0;  ///< max(0, used - high)
    std::size_t need_free_bytes = 0;  ///< used > high ? used - low : 0（降到低水位需释放量）
    bool        pressured       = false;  ///< over_bytes > 0
};

/**
 * @brief mesh/texture 的 CPU(RAM) 与 GPU(VRAM) 内存账本快照
 */
struct MemoryReport {
    MemoryPoolReport vram;  ///< GPU：mesh/texture 缓冲（geometry 自有，精确）
    MemoryPoolReport ram;   ///< CPU：Scene/Image 资源（按 rid 去重，对账存活）
    std::size_t      vram_mesh_peak    = 0;
    std::size_t      vram_texture_peak = 0;
};

// ========================================
// 动态减面 (Mesh Simplification) 相关类型
// ========================================
//
// 网格简化由资源导入管线完成（使用 meshoptimizer 库，参见
// modules/corona_resource 中的 parse_common.h）。
// 导入时已生成多级 LOD 数据（MeshData::lod_levels），
// 本系统负责：
//   1. 将导入时生成的 CPU 端 LOD 数据上传为 GPU 缓冲（upload_lod_from_scene_data）
//   2. 提供线程安全的 LOD 查询接口供渲染线程使用
//   3. 根据屏幕占比自动选择合适的 LOD 级别
//
// 数据流向：
//   导入时 meshoptimizer → MeshData::lod_levels [CPU]
//   → upload_lod_from_scene_data() → LODMeshBuffers [GPU] → 存入 lod_cache
//   → 渲染时查询 get_lod_buffers() → 替换原始缓冲 → 提交 GPU 绘制

/**
 * @brief 单个 LOD 级别的 GPU 缓冲集合
 *
 */
struct LODMeshBuffers {
    Horizon::HardwareBuffer vertex_buffer;    // GPU 顶点缓冲（Vertex Shader 读取）
    Horizon::HardwareBuffer index_buffer;     // GPU 索引缓冲（组装三角形）
    Horizon::HardwareBuffer vertex_storage;   // GPU 顶点 StorageBuffer（Compute Shader 用）
    Horizon::HardwareBuffer index_storage;    // GPU 索引 StorageBuffer（Compute Shader 用）
    float  error            = 0.0f;  // 该级别的几何误差（QEM 计算得出，用于调试）
    float  screen_threshold = 1.0f;  // 屏幕占比阈值：低于此值时切换到此级别
    bool   ready            = false; // GPU 缓冲是否已创建完毕（创建前不能用于渲染）
    std::uint32_t vertex_count = 0;  // 该级别顶点数（调试/诊断用）
    std::uint32_t index_count  = 0;  // 该级别索引数（调试/诊断用）

    // GPU 显存记账令牌（P0）：LOD1..N 各自的顶点/索引缓冲字节。
    // LOD0 复用 mesh_dev 的缓冲（非新分配）→ 该令牌留空计 0，避免重复计量。
    Corona::Memory::GpuMemToken mesh_mem;
};

// LOD（动态减面）现由 GeometrySystem 内部自行决策，无外部配置面：
// - 是否生成：由导入层 LODGenerationOptions 决定（见 corona/resource/types/scene.h）
// - 是否上传 GPU / 选哪一级：每帧在 update() 中自动完成
// 最大级别数等内部参数见 geometry_system.cpp 中的 kMaxLodLevels 常量。

/**
 * @brief 几何系统 (Geometry System)
 *
 * 负责几何数据管理、空间变换、包围盒计算，并承载场景八叉树空间索引服务
 * （原 SceneSystem 职责已并入此处）：
 * - 每帧重建场景八叉树；
 * - 提供线程安全的 AABB / 球 / 视锥 / 碰撞对查询；
 * - 维护 Actor 加载状态机与距离预加载/卸载；
 * - 维护 actor 可见性热度并发出 LRU evict/restore 事件。
 * - 管理运行时 LOD 切换（基于导入时 meshoptimizer 生成的简化数据）。
 *
 * 运行在独立线程，以 60 FPS 更新几何状态。
 *
 * 优先级 85：晚于 transform 写入者，早于 MechanicsSystem(75)，确保物理宽相
 * query_pairs() 在同帧读取到已重建的八叉树。
 */
class GeometrySystem : public Kernel::SystemBase {
   public:
    GeometrySystem();
    ~GeometrySystem() override;

    // ========================================
    // ISystem 接口实现
    // ========================================

    std::string_view get_name() const override {
        return "Geometry";
    }

    int get_priority() const override {
        return 85;  // 高优先级，早于 MechanicsSystem(75)，保证八叉树同帧就绪
    }

    /**
     * @brief 初始化几何系统
     * @param ctx 系统上下文
     * @return 初始化成功返回 true
     */
    bool initialize(Kernel::ISystemContext* ctx) override;

    /**
     * @brief 每帧更新几何
     *
     * 在独立线程中调用，更新几何变换、重建八叉树并维护加载状态。
     */
    void update() override;

    /**
     * @brief 关闭几何系统
     *
     * 清理所有几何资源与异步任务。
     */
    void shutdown() override;

    // ========================================
    // 配置
    // ========================================
    void set_visibility_config(std::uintptr_t scene, SceneVisibilityConfig cfg);

    /// 距离卸载配置接口
    void set_distance_config(std::uintptr_t scene, float unload_dist, float preload_dist, bool enable = true);

    // ========================================
    // 空间查询（线程安全）
    // ========================================
    [[nodiscard]] std::vector<std::uintptr_t> query_aabb(
        std::uintptr_t scene, const Spatial::AABB& box) const;

    [[nodiscard]] std::vector<std::uintptr_t> query_sphere(
        std::uintptr_t scene, const ktm::fvec3& center, float radius) const;

    [[nodiscard]] std::vector<std::uintptr_t> query_frustum(
        std::uintptr_t scene, const Math::Frustum& frustum) const;

    /// 物理宽相用：返回 (handle_a, handle_b)，a < b。
    [[nodiscard]] std::vector<std::pair<std::uintptr_t, std::uintptr_t>> query_pairs(
        std::uintptr_t scene) const;

    /// 便捷：内部从 CameraDevice 构造 frustum 后查询
    [[nodiscard]] std::vector<std::uintptr_t> query_visible_for_camera(
        std::uintptr_t scene, std::uintptr_t camera) const;

    // ========================================
    // LRU 协作（M3 生产化）
    // ========================================
    //
    // ActorEvictRequestedEvent 发布后，GeometrySystem 自动：
    //   1. 创建 ActorStreamingRecord（scene/actor + model_path + transform + handles + flags）
    //   2. 存入 ActorCache（两级 LRU：内存 64MB + 磁盘 256MB）
    //   3. 标记 actor 为 offline，状态置为 Unloaded
    //
    // ActorRestoreRequestedEvent 发布后，GeometrySystem 自动：
    //   1. 从 ActorCache 获取 ActorStreamingRecord（或回退到磁盘 model_path）
    //   2. 调用 ResourceManager::import_async 重新导入
    //   3. 导入完成后重建 GPU 资源，标记为 online
    //
    // 磁盘目录默认：{cwd}/cache/actors/，可通过 set_cache_directory() 修改

    /// 设置 LRU ActorCache 磁盘目录（需在首次 evict 前调用）
    void set_cache_directory(std::filesystem::path dir);

    /// 设置资源内存预算（MB），0 = 不限制。
    /// 当 ResourceManager 估算内存用量超过预算时，GeometrySystem 每帧末尾
    /// 触发 evict_until_under_budget，优先淘汰最久未访问（cold）的资源。
    void set_resource_memory_budget_mb(std::size_t mb);

    /// 设置 GPU 显存（VRAM）预算（MB），0 = 不限制（默认）。
    /// P0 仅用于计算 over/need_free 报告，不触发淘汰。
    void set_vram_budget_mb(std::size_t mb);

    /// mesh/texture 的 CPU(RAM) + GPU(VRAM) 内存账本快照（线程安全）。
    [[nodiscard]] MemoryReport memory_report() const;

    [[nodiscard]] bool is_actor_offline(std::uintptr_t actor) const;
    void               mark_actor_restored(std::uintptr_t actor);

    /// 加载状态查询接口
    [[nodiscard]] ActorLoadState get_actor_load_state(std::uintptr_t actor, std::uintptr_t scene) const;

    // ========================================
    // LOD 工具
    // ========================================
    /// 计算物体包围球在屏幕上的占比（0~1）
    static float compute_screen_ratio(const ktm::fvec3& camera_pos,
                                      float              camera_fov_deg,
                                      const ktm::fvec3& world_center,
                                      float              bounding_radius);

    /// 根据屏幕占比选择 LOD 等级（0 = 原始网格）
    static int select_lod_level(float                     screen_ratio,
                                const std::vector<float>& thresholds);

    // ========================================
    // 动态减面 (Mesh Simplification) API
    // ========================================
    //
    // LOD 由 GeometrySystem 内部自动管理，无对外配置开关：
    //
    //   【自动上传】
    //   模型导入时 meshoptimizer 已生成了 LOD 数据（存在 MeshData::lod_levels）。
    //   引擎在 update() 中每帧调用 upload_lod_from_scene_data() 将其上传 GPU，
    //   无 LOD 数据的 mesh 自动跳过。无需任何外部调用。
    //
    //   【渲染时查询】
    //   渲染线程调用 select_render_buffers()，由 GeometrySystem 内部完成
    //   屏幕占比计算 + LOD 选级 + 降级兜底，直接返回可用的渲染缓冲。

    /// 渲染用的一组 GPU 缓冲（顶点/索引 + 对应 StorageBuffer）
    /// select_render_buffers 的入参（fallback）与返回值均为此类型。
    struct RenderMeshBuffers {
        Horizon::HardwareBuffer vertex;
        Horizon::HardwareBuffer index;
        Horizon::HardwareBuffer vertex_storage;
        Horizon::HardwareBuffer index_storage;
    };

    /// 一站式渲染缓冲选择（渲染线程调用，线程安全）。
    ///
    /// 内部流程：compute_screen_ratio() → 选 LOD 级别 → 降级到已就绪级别，
    /// 命中则返回该级 LOD 缓冲；无 LOD 数据 / 未就绪 / 缓冲无效时，原样返回
    /// fallback。**保证返回值始终可直接用于渲染**，调用方无需判空或降级。
    ///
    /// @param geometry_handle GeometryDevice 句柄
    /// @param mesh_index      子网格索引
    /// @param camera_pos      相机世界坐标
    /// @param camera_fov_deg  相机垂直 FOV（度）
    /// @param world_center    物体包围球世界中心
    /// @param bounding_radius 物体包围球半径
    /// @param fallback        无 LOD 时使用的原始缓冲（通常为 mesh 的 LOD0）
    [[nodiscard]] RenderMeshBuffers select_render_buffers(
        std::uintptr_t          geometry_handle,
        uint32_t                mesh_index,
        const ktm::fvec3&       camera_pos,
        float                   camera_fov_deg,
        const ktm::fvec3&       world_center,
        float                   bounding_radius,
        const RenderMeshBuffers& fallback) const;

    /// 查询指定 LOD 级别的 GPU 缓冲（渲染线程调用，线程安全）
    ///
    /// @param geometry_handle GeometryDevice 句柄
    /// @param mesh_index      子网格索引
    /// @param lod_level       LOD 级别（0=原始精度，1..N=各级简化）
    /// @return 指向 LODMeshBuffers 的指针，或 nullptr 表示该级别不存在
    ///
    /// 降级策略：如果请求的级别尚未就绪（ready=false），自动返回 LOD 0。
    /// 调用者无需处理未就绪的情况。
    [[nodiscard]] const LODMeshBuffers* get_lod_buffers(
        std::uintptr_t geometry_handle,
        uint32_t       mesh_index,
        int            lod_level) const;

    /// 查询某个 mesh 已就绪的 LOD 级别数
    /// @return 0 表示该 mesh 还未上传任何 LOD 数据
    [[nodiscard]] int get_lod_count(std::uintptr_t geometry_handle,
                                    uint32_t       mesh_index) const;

    /// 一站式 LOD 级别选择：给定屏幕占比，返回应使用的 LOD 级别
    ///
    /// 内部流程：
    ///   1. 从 lod_cache 获取该 mesh 的各 LOD 级别阈值
    ///   2. 调用 select_lod_level(screen_ratio, thresholds) 选择级别
    ///   3. 如果选中的级别未就绪，自动降级到最近的已就绪级别
    ///
    /// @param geometry_handle GeometryDevice 句柄
    /// @param mesh_index      子网格索引
    /// @param screen_ratio    物体在屏幕上的占比（0~1），由 compute_screen_ratio() 算得
    /// @return 应使用的 LOD 级别（0=原始，1..N=各级简化）
    [[nodiscard]] int resolve_lod_level(std::uintptr_t geometry_handle,
                                        uint32_t       mesh_index,
                                        float          screen_ratio) const;

    /// 一站式 LOD 缓冲获取：自动选级 + 返回 GPU 缓冲（渲染线程调用，单次加锁）
    ///
    /// 等价于 resolve_lod_level() + get_lod_buffers()，但只获取一次锁。
    /// 渲染热路径上应优先使用此方法。
    ///
    /// @return 指向 LODMeshBuffers 的指针，或 nullptr 表示该 mesh 无 LOD 数据
    [[nodiscard]] const LODMeshBuffers* resolve_lod_buffers(
        std::uintptr_t geometry_handle,
        uint32_t       mesh_index,
        float          screen_ratio) const;

    /// 蒙皮专用：一次性拷出某 mesh 所有 LOD 级别的 (vertex, vertex_storage) 句柄对。
    ///
    /// 供 MechanicsSystem 在物理线程把蒙皮后顶点 write_bytes 回所有 LOD 级别的 GPU
    /// 缓冲。下标 0 = LOD0（= MeshDevice 缓冲），1..N = 各级简化。单次 shared_lock
    /// 拷贝；HardwareBuffer 为引用计数句柄，拷出后即便 Geometry 线程后续 evict 缓存，
    /// 调用方持有的拷贝仍保活底层 buffer。无 LOD 缓存条目时返回空 vector（调用方回退
    /// 到只写 LOD0，即 GeometryDevice.mesh_handles 里的缓冲）。
    ///
    /// @param geometry_handle GeometryDevice 句柄
    /// @param mesh_index      子网格索引
    /// @return 各 LOD 级别的 (vertexBuffer, vertexStorageBuffer) 句柄对，含 LOD0
    [[nodiscard]] std::vector<std::pair<Horizon::HardwareBuffer, Horizon::HardwareBuffer>>
    get_skinning_targets(std::uintptr_t geometry_handle, uint32_t mesh_index) const;

    // ========================================
    // BVH 射线查询（三角形级加速）
    // ========================================
    //
    // 使用场景：拿到 Octree 粗筛的 actor 列表后，对每个 mesh 调用以下方法
    // 获取射线命中的三角形下标。payload = 三角形序号（i/3）。
    //
    // 命中基于三角形 AABB，调用方拿到候选三角形后需自行做精确
    // ray-tri 相交检测（Möller-Trumbore）以确认最终命中。

    /// 穿透查询：返回射线命中的所有三角形下标（AABB 级，无序）
    /// @param geometry_handle GeometryDevice 句柄
    /// @param mesh_index      子网格索引
    /// @param lod_level       LOD 级别（0=原始精度）
    /// @param origin          射线起点（mesh 局部空间）
    /// @param inv_dir         射线方向倒数（1/dir.x, 1/dir.y, 1/dir.z）
    /// @return 命中的三角形下标列表，未命中或无 BVH 时返回空 vector
    [[nodiscard]] std::vector<uint32_t> query_mesh_ray(
        std::uintptr_t   geometry_handle,
        uint32_t         mesh_index,
        int              lod_level,
        const ktm::fvec3& origin,
        const ktm::fvec3& inv_dir) const;

    /// 最近命中查询：返回离射线起点最近的三角形及其距离
    /// @param geometry_handle GeometryDevice 句柄
    /// @param mesh_index      子网格索引
    /// @param lod_level       LOD 级别
    /// @param origin          射线起点（mesh 局部空间）
    /// @param inv_dir         射线方向倒数
    /// @param t_max           最大搜索距离
    /// @return 命中返回 Hit{payload=三角形下标, t=距离}，未命中返回 std::nullopt
    [[nodiscard]] std::optional<Spatial::BVH<uint32_t>::Hit> query_mesh_closest_hit(
        std::uintptr_t   geometry_handle,
        uint32_t         mesh_index,
        int              lod_level,
        const ktm::fvec3& origin,
        const ktm::fvec3& inv_dir,
        float            t_max) const;

    // ========================================
    // 统计
    // ========================================
    [[nodiscard]] SceneStats stats(std::uintptr_t scene) const;

   private:
    void on_load_finished(const Events::ActorLoadFinishedEvent& event);
    void on_unload_finished(const Events::ActorUnloadFinishedEvent& event);
    void on_load_requested(const Events::ActorLoadRequestedEvent& event);
    void on_unload_requested(const Events::ActorUnloadRequestedEvent& event);
    void on_evict_requested(const Events::ActorEvictRequestedEvent& event);
    void on_restore_requested(const Events::ActorRestoreRequestedEvent& event);
    void process_async_tasks();  // 处理完成的异步资源任务

    /// 扫描 PendingImport 的 GeometryDevice，发起异步 import；轮询已完成的 import
    /// 任务，将解析出的 model_id 写入其 ModelResource 槽并转入 PendingBuild。
    /// import 完成后回填引用该 geometry 的 MechanicsDevice 的 AABB（八叉树每帧自愈）。
    /// 这是"导入异步化"的承接点：Python ctor 仅记录 model_path 并标记 PendingImport，
    /// 磁盘 IO / assimp 解析全部移到 GeometrySystem 线程，不阻塞前端（CEF UI 线程）。
    void process_pending_geometry_imports();

    /// 扫描所有 GeometryDevice，为标记 PendingBuild 且 model_id 已就绪者构建 GPU
    /// 资源（mesh_handles），构建后置回 Ready 并失效其 LOD 缓存。
    /// 这是"初始加载异步化"的承接点：Python ctor 仅记录 model_id 并标记 PendingBuild，
    /// 实际 GPU 构建延迟到此处（GeometrySystem 线程）完成，不阻塞前端。
    /// 当前默认无人产出 PendingBuild（所有路径仍同步构建为 Ready），本扫描为空跑。
    void process_pending_geometry_builds();

    /// 卸载完成时释放 actor 关联的 GPU 资源（HardwareBuffer / HardwareImage），
    /// 并清理对应的 LOD 缓存条目。不释放 SharedDataHub 存储槽位本身——
    /// 槽位归 Python API 层 Geometry 对象所有，由其析构函数回收。
    void release_actor_gpu_resources(std::uintptr_t actor);

    /// 重新加载完成时重建 actor 关联的 GPU 资源（HardwareBuffer / HardwareImage），
    /// 从已导入的 Scene 资源中重新创建 mesh_handles 并恢复 model_resource_handle。
    /// 同时清理 LOD 缓存以保证下一帧 update() 重新上传 LOD 数据。
    void rebuild_actor_gpu_resources(std::uintptr_t actor, std::uint64_t rid);

    // ========================================
    // 动态减面内部管线（在 update() 中每帧调用，外部不可见）
    // ========================================
    //
    // 模型导入时 meshoptimizer 已生成 LOD 数据（MeshData::lod_levels），
    // 这里只负责将其上传为 GPU 缓冲。

    /// 遍历所有已加载的 Scene 资源，
    /// 将其 MeshData::lod_levels（导入时 meshoptimizer 生成的LOD数据）上传到 GPU。
    /// 每帧调用但只对新模型生效（已有缓存的跳过）。
    void upload_lod_from_scene_data();

    /// 骨骼动画 CPU 蒙皮（P2）。每帧遍历所有 GeometryDevice，对蒙皮模型
    /// （Scene::skeleton 有值）：推进 anim_time → compute_pose 算 final 骨骼矩阵
    /// → 对每个 mesh 做 CPU 蒙皮（skinned[v] = Σ wᵢ·(finalᵢ·bind[v])）→ 把蒙皮后
    /// 顶点 write_bytes 重传到 MeshDevice 的 vertexBuffer + vertexStorageBuffer。
    /// 蒙皮输出仍是标准 32B Vertex，故 Native 光栅 / material_resolve 着色器零改动。
    /// 蒙皮后顶点同时缓存到 GeometryDevice::skinned_cpu_vertices，供 P3 Vision /
    /// P4 物理作为单一数据源消费。
    void update_skinned_geometry();

    /// 维护 mesh/texture 的 CPU 资源账本（P0）：登记新出现 model_id 的 Scene
    /// (mesh CPU) 与其 Image 纹理 (texture CPU)，按 rid 去重；并对 ResourceManager
    /// 的存活集合做对账，删除已被驱逐的 rid。低频调用（~1Hz）即可，CPU 用量变化缓慢。
    void update_cpu_resource_ledger();

    /// 计算 mesh/texture 的 VRAM/RAM 用量 + 预算视图（线程安全，内部加锁）。
    [[nodiscard]] MemoryReport compute_memory_report() const;

    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace Corona::Systems
