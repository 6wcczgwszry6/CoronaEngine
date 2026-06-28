#pragma once

#include <corona/spatial/bvh.h>
#include <corona/spatial/octree.h>
#include <corona/systems/geometry/actor_cache.h>
#include <corona/systems/geometry/geometry_system.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <future>
#include <memory>
#include <mutex>
#include <optional>
#include <shared_mutex>
#include <unordered_map>
#include <vector>

#include <ktm/ktm.h>

namespace Corona::Systems::GeometryInternal {

[[nodiscard]] inline ktm::fvec3 make_fvec3(float x, float y, float z) {
    ktm::fvec3 value;
    value[0] = x;
    value[1] = y;
    value[2] = z;
    return value;
}

[[nodiscard]] inline ktm::fvec4 make_fvec4(float x, float y, float z, float w) {
    ktm::fvec4 value;
    value[0] = x;
    value[1] = y;
    value[2] = z;
    value[3] = w;
    return value;
}

[[nodiscard]] inline ktm::fvec3 transform_local_point_to_world(const Corona::ModelTransform& transform,
                                                        const ktm::fvec3& local_point) {
    const ktm::fmat4x4 matrix = transform.compute_matrix();
    const ktm::fvec4 local_h = make_fvec4(local_point[0], local_point[1], local_point[2], 1.0f);
    const ktm::fvec4 world_h = matrix * local_h;
    return make_fvec3(world_h[0], world_h[1], world_h[2]);
}

inline void world_aabb_from_local_bounds(const Corona::ModelTransform& transform,
                                         const ktm::fvec3& local_min,
                                         const ktm::fvec3& local_max,
                                         Spatial::AABB& out_world_aabb) {
    const ktm::fvec3 corners[8] = {
        make_fvec3(local_min[0], local_min[1], local_min[2]),
        make_fvec3(local_max[0], local_min[1], local_min[2]),
        make_fvec3(local_min[0], local_max[1], local_min[2]),
        make_fvec3(local_max[0], local_max[1], local_min[2]),
        make_fvec3(local_min[0], local_min[1], local_max[2]),
        make_fvec3(local_max[0], local_min[1], local_max[2]),
        make_fvec3(local_min[0], local_max[1], local_max[2]),
        make_fvec3(local_max[0], local_max[1], local_max[2]),
    };

    const ktm::fvec3 first_corner = transform_local_point_to_world(transform, corners[0]);
    out_world_aabb.min = first_corner;
    out_world_aabb.max = first_corner;

    for (int i = 1; i < 8; ++i) {
        const ktm::fvec3 world_corner = transform_local_point_to_world(transform, corners[i]);
        out_world_aabb.min[0] = std::min(out_world_aabb.min[0], world_corner[0]);
        out_world_aabb.min[1] = std::min(out_world_aabb.min[1], world_corner[1]);
        out_world_aabb.min[2] = std::min(out_world_aabb.min[2], world_corner[2]);
        out_world_aabb.max[0] = std::max(out_world_aabb.max[0], world_corner[0]);
        out_world_aabb.max[1] = std::max(out_world_aabb.max[1], world_corner[1]);
        out_world_aabb.max[2] = std::max(out_world_aabb.max[2], world_corner[2]);
    }
}


}  // namespace Corona::Systems::GeometryInternal

namespace Corona::Systems {

struct GeometrySystem::Impl {
    using Payload = std::uintptr_t;
    using OctreeEntry = Spatial::Octree<Payload>::Entry;

    struct SceneState {
        Spatial::Octree<Payload>                            tree;
        std::unordered_map<Payload,Spatial::AABB> actor_to_entry; //Actor到AABB映射
        std::unordered_map<Payload, std::uint32_t>          invisible_frames;
        SceneVisibilityConfig                               cfg;
        SceneStats                                          stats;
        mutable std::mutex                                  stats_mutex;
        std::unordered_map<Payload,ActorLoadState>          actor_load_states;

        std::unordered_map<Payload,std::future<std::uint64_t>> loading_tasks;
        std::unordered_map<Payload,std::future<bool>>       unloading_tasks;
        std::unordered_map<Payload,int>                     unload_retry_counts; //卸载重试次数
    };

    mutable std::shared_mutex                               mtx;
    std::unordered_map<std::uintptr_t /*scene*/, SceneState> scenes;
    std::unordered_map<Payload, bool>                       offline_actors;
    std::vector<Kernel::EventId>                            event_subscriptions;
    Kernel::ISystemContext*                                 ctx = nullptr;

    // ========================================
    // 动态减面（LOD）相关状态
    // ========================================
    struct LODCacheEntry {
        std::vector<LODMeshBuffers> levels;
        std::uint64_t model_id = 0;  // 用于检测模型变更（比地址指针可靠，不受 slot 复用影响）

        // 每个 LOD 级别一个 BVH（下标与 levels 一一对应）
        // payload = 三角形下标（i/3），用于射线→三角形加速查询
        std::vector<Spatial::BVH<uint32_t>> per_level_bvh;
    };

    mutable std::shared_mutex          lod_cache_mutex;
    std::unordered_map<uint64_t, LODCacheEntry> lod_cache;

    // ========================================
    // LRU ActorCache（M3 生产化）
    // ========================================
    // 两级 LRU 缓存（内存 + 磁盘），存储被 evict 的 actor 快照
    // 默认：64MB 内存 + 256MB 磁盘，目录可配置
    static constexpr size_t kDefaultMemCacheBytes  = 64 * 1024 * 1024;
    static constexpr size_t kDefaultDiskCacheBytes = 256 * 1024 * 1024;

    std::unique_ptr<Corona::Cache::ActorCache> actor_cache;
    std::filesystem::path                       actor_cache_dir;

    /// 初始化 ActorCache（延迟到首次 evict/restore 时）
    void ensure_actor_cache();

    /// actor_handle → 最后一次快照时间（用于防抖）
    std::unordered_map<Payload, std::chrono::steady_clock::time_point> last_snapshot_time;

    /// evict 后待释放 GPU 的 actor 集合（延迟到下一帧 update() 头部处理，
    /// 避免与 OpticsSystem 渲染线程产生 data race）
    std::unordered_set<Payload> pending_gpu_releases;

    /// 初始加载异步 import 任务：geometry_handle → (epoch, import future)。
    /// GeometrySystem 扫描 PendingImport 的 GeometryDevice，发起 import_async
    /// 并在此追踪；future 就绪后比对 epoch（防 slot 复用 ABA）、填 model_id、转 PendingBuild。
    struct PendingImportTask {
        std::uint64_t              epoch = 0;  // 与 GeometryDevice::import_epoch 比对
        std::future<std::uint64_t> future;
    };
    std::unordered_map<Payload, PendingImportTask> pending_import_tasks;

    /// import 任务 epoch 分配器（进程级单调递增，0 保留为"无任务"）。
    std::uint64_t next_import_epoch = 1;

    /// 骨骼动画上一帧时间戳（用于 update_skinned_geometry 计算 dt）。
    /// 未初始化时（首帧）取 dt=0。
    std::optional<std::chrono::steady_clock::time_point> last_skin_update_time;

    // ========================================
    // 资源内存预算（MB），0 = 不限制（默认）
    // ========================================
    std::size_t resource_memory_budget_mb = 512;  // 默认 512MB，0 表示不限制

    [[nodiscard]] static uint64_t make_lod_key(std::uintptr_t geometry_handle,
                                               uint32_t       mesh_index) {
        return (static_cast<uint64_t>(geometry_handle) << 32) | mesh_index;
    }

    SceneState& get_or_create(std::uintptr_t scene) {
        auto [it, inserted] = scenes.try_emplace(scene);
        return it->second;
    }
};

}  // namespace Corona::Systems

