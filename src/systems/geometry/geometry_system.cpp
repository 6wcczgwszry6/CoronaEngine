#include <corona/events/engine_events.h>
#include <corona/kernel/core/i_logger.h>
#include <corona/kernel/utils/storage.h>
#include <corona/resource/resource.h>
#include <corona/resource/resource_manager.h>
#include <corona/resource/types/scene.h>
#include <corona/shared_data_hub.h>
#include <corona/spatial/octree.h>
#include <corona/systems/geometry/geometry_system.h>
#include <corona/utils/path_utils.h>
#include <ktm/ktm.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <future>
#include <limits>
#include <mutex>
#include <shared_mutex>
#include <span>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>

#include "geometry_internal.h"

#include <corona/systems/geometry/geometry_mesh_builder.h>

namespace Corona::Systems {

using namespace GeometryInternal;

namespace {

template <typename T>
Horizon::HardwareBuffer make_geometry_buffer(const std::vector<T>& data,
                                             Horizon::BufferUsageFlags usage,
                                             std::string name = {}) {
    Horizon::HardwareBufferDesc desc;
    desc.element_count = data.size();
    desc.element_size = static_cast<uint32_t>(sizeof(T));
    desc.usage = usage;
    desc.debug_name = std::move(name);
    return Horizon::HardwareBuffer(desc, std::as_bytes(std::span<const T>(data.data(), data.size())));
}

}  // namespace

// ============================================================================
// 生命周期
// ============================================================================

GeometrySystem::GeometrySystem() : impl_(std::make_unique<Impl>()) {
    set_target_fps(60);
}

GeometrySystem::~GeometrySystem() = default;

bool GeometrySystem::initialize(Kernel::ISystemContext* ctx) {
    impl_->ctx = ctx;
    CFW_LOG_NOTICE("GeometrySystem: Initializing (octree host)");

    if (ctx && ctx->event_bus()) {
        auto id1 = ctx->event_bus()->subscribe<Events::ActorLoadFinishedEvent>(
            [this](const Events::ActorLoadFinishedEvent& e) {
                this->on_load_finished(e);
            });
        auto id2 = ctx->event_bus()->subscribe<Events::ActorUnloadFinishedEvent>(
           [this](const Events::ActorUnloadFinishedEvent& e) {
               this->on_unload_finished(e);
           });
        auto id3 = ctx->event_bus()->subscribe<Events::ActorLoadRequestedEvent>(
            [this](const Events::ActorLoadRequestedEvent& e) {
                this->on_load_requested(e);
            });
        auto id4 = ctx->event_bus()->subscribe<Events::ActorUnloadRequestedEvent>(
            [this](const Events::ActorUnloadRequestedEvent& e) {
                this->on_unload_requested(e);
            });
        // ---- M3 LRU：订阅 evict / restore 事件 ----
        auto id5 = ctx->event_bus()->subscribe<Events::ActorEvictRequestedEvent>(
            [this](const Events::ActorEvictRequestedEvent& e) {
                this->on_evict_requested(e);
            });
        auto id6 = ctx->event_bus()->subscribe<Events::ActorRestoreRequestedEvent>(
            [this](const Events::ActorRestoreRequestedEvent& e) {
                this->on_restore_requested(e);
            });

        impl_->event_subscriptions = {id1, id2, id3, id4, id5, id6};
    }

    return true;
}

void GeometrySystem::update() {
    auto& hub = SharedDataHub::instance();
    auto& scene_storage = hub.scene_storage();
    auto& camera_storage = hub.camera_storage();
    auto& geometry_storage = hub.geometry_storage();
    auto& transform_storage = hub.model_transform_storage();
    std::vector<std::uintptr_t> scene_handles;
    {
        for (auto it = scene_storage.cbegin(); it != scene_storage.cend(); ++it) {
            const SceneDevice& scene_dev = *it;
            scene_handles.push_back(reinterpret_cast<std::uintptr_t>(&scene_dev));
        }
    }

    process_async_tasks();

    // ---- 延迟 GPU 释放（LRU evict 路径） ----
    // on_evict_requested 将 actor 加入 pending_gpu_releases 集合，
    // 延迟到此处（下一帧 update 头部）释放 GPU 资源，避免与
    // OpticsSystem 渲染线程产生 data race。
    if (!impl_->pending_gpu_releases.empty()) {
        std::unordered_set<Impl::Payload> to_release;
        {
            std::unique_lock lock(impl_->mtx);
            to_release.swap(impl_->pending_gpu_releases);
        }
        for (auto actor : to_release) {
            release_actor_gpu_resources(actor);
        }
    }

    // ---- 异步导入（方案 A 承接点）----
    // 扫描 PendingImport 的 GeometryDevice，发起 import_async / 轮询完成，
    // 填 model_id 后转 PendingBuild，并回填 MechanicsDevice AABB。
    // 磁盘 IO / assimp 解析全部在本（引擎）线程之外的 ResourceManager 线程池完成，
    // 不阻塞前端 CEF UI 线程。
    process_pending_geometry_imports();

    // ---- 初始构建（异步加载承接点）----
    // 为标记 PendingBuild 的 GeometryDevice 构建 GPU 资源（mesh_handles）。
    // 放在 LOD 上传之前，使本帧新建的 mesh 同帧即可上传其 LOD 数据。
    process_pending_geometry_builds();

    // ---- 动态减面管线 ----
    // LOD 由 GeometrySystem 内部自动管理，无外部开关：每帧上传导入时生成的 LOD 数据。
    // 已缓存的 mesh 仅做一次 find + model_id 比较，无 LOD 数据的 mesh 自动跳过。
    upload_lod_from_scene_data();

    for (std::uintptr_t scene_handle : scene_handles) {
        const auto scene_begin = std::chrono::steady_clock::now();
        std::vector<std::uintptr_t> actor_handles;
        std::vector<std::uintptr_t> camera_handles;
        {
            auto scene_read = scene_storage.try_acquire_read(scene_handle);
            if ( !scene_read.valid() )  continue;
            actor_handles = scene_read->actor_handles;
            camera_handles = scene_read->camera_handles;
        }

        std::vector<typename Spatial::Octree<Impl::Payload>::Entry> octree_entries;
        std::unordered_set<Impl::Payload> added_actors;
        for (std::uintptr_t actor_handle : actor_handles) {
            if (added_actors.count(actor_handle)) continue;

            auto& actor_storage = hub.actor_storage();
            auto actor_read = actor_storage.acquire_read(actor_handle);
            if ( !actor_read ) continue;
            const ActorDevice& actor_dev = *actor_read;

            for (std::uintptr_t profile_handle : actor_dev.profile_handles) {
                auto& profile_storage = hub.profile_storage();
                auto profile_read = profile_storage.acquire_read(profile_handle);
                if (!profile_read.valid()) continue;

                const ProfileDevice& profile_dev = *profile_read;
                std::uintptr_t mechanics_handle = profile_dev.mechanics_handle;
                if ( !mechanics_handle ) continue;

                auto& mechanics_storage = hub.mechanics_storage();
                auto mechanics_read = mechanics_storage.acquire_read(mechanics_handle);
                if (!mechanics_read.valid()) continue;

                auto geometry_read = geometry_storage.acquire_read(mechanics_read->geometry_handle);
                if (!geometry_read.valid() || geometry_read->transform_handle == 0) continue;

                auto transform_read = transform_storage.acquire_read(geometry_read->transform_handle);
                if (!transform_read.valid()) continue;

                const MechanicsDevice& mechanics_dev = *mechanics_read;
                Spatial::AABB aabb;
                world_aabb_from_local_bounds(*transform_read, mechanics_dev.min_xyz, mechanics_dev.max_xyz, aabb);
                octree_entries.push_back({actor_handle,aabb});
                added_actors.insert(actor_handle);
                break;
            }
        }
        // 批量初始化 Actor 加载状态（单次加锁替代逐 Actor 加锁）
        // 当距离剔除关闭时，actor 视为始终已加载；否则从 Unloaded 开始由距离剔除系统管理
        // 对于初始即为 Loaded 的 actor，需要手动发布 ActorResidencyChangedEvent
        // 因为不经过 load 流程，on_load_finished 不会触发
        std::vector<Events::ActorResidencyChangedEvent> initial_resident;
        {
            std::unique_lock lock(impl_->mtx);
            auto& scene_state = impl_->get_or_create(scene_handle);
            const ActorLoadState initial_state = scene_state.cfg.enable_distance_culling
                                                     ? ActorLoadState::Unloaded
                                                     : ActorLoadState::Loaded;
            for (auto actor_handle : added_actors) {
                auto [it, inserted] = scene_state.actor_load_states.try_emplace(
                    actor_handle, initial_state);
                if (inserted && initial_state == ActorLoadState::Loaded) {
                    initial_resident.push_back(
                        {scene_handle, actor_handle, /*loaded=*/true});
                }
            }
        }
        for (const auto& evt : initial_resident) {
            if (impl_->ctx && impl_->ctx->event_bus())
                impl_->ctx->event_bus()->publish(evt);
        }

        Spatial::AABB root_aabb;
        if (!octree_entries.empty()) {
            root_aabb = octree_entries[0].bounds;
            for (const auto& entry : octree_entries) {
                root_aabb = root_aabb.merged(entry.bounds);
            }
            ktm::fvec3 extent = root_aabb.extent();

            //padding 添加10%的内边距
            float max_extent = std::max({extent[0], extent[1], extent[2]});
            float padding = max_extent * 0.1f;
            root_aabb = root_aabb.expanded(padding);
        }else {
            root_aabb.min = make_fvec3(-1.0f, -1.0f, -1.0f);
            root_aabb.max = make_fvec3(1.0f, 1.0f, 1.0f);
        }

        double rebuild_ms = 0.0;
        {
            const auto rebuild_begin = std::chrono::steady_clock::now();
            std::unique_lock lock(impl_->mtx);
            auto& scene_state = impl_->get_or_create(scene_handle);
            scene_state.tree.rebuild(root_aabb,octree_entries);
            scene_state.actor_to_entry.clear();
            for (const auto& entry : octree_entries) {
                scene_state.actor_to_entry[entry.payload] = entry.bounds;
            }

            // 清理已经从场景中删除的Actor的状态
            std::unordered_set<Impl::Payload> current_actors(actor_handles.begin(),
                                                actor_handles.end());
            auto it = scene_state.actor_load_states.begin();
            while (it != scene_state.actor_load_states.end()) {
                if (!current_actors.count(it->first)) {
                    scene_state.loading_tasks.erase(it->first);
                    scene_state.unloading_tasks.erase(it->first);
                    scene_state.unload_retry_counts.erase(it->first);
                    scene_state.invisible_frames.erase(it->first);
                    it = scene_state.actor_load_states.erase(it);
                }else {
                    ++it;
                }
            }

            rebuild_ms = std::chrono::duration<double, std::milli>(
                             std::chrono::steady_clock::now() - rebuild_begin)
                             .count();
            std::lock_guard stats_lock(scene_state.stats_mutex);
            scene_state.stats.last_rebuild_ms = rebuild_ms;
        }
        // 发布粗筛碰撞候选对：SceneSystem 仅负责空间划分，不依赖物理系统
        {
            auto pairs = query_pairs(scene_handle);
            if (impl_->ctx && impl_->ctx->event_bus()) {
                impl_->ctx->event_bus()->publish(
                    Events::BroadphasePairsEvent{scene_handle, std::move(pairs)});
            }
        }

        std::vector<std::pair<ktm::fvec3,Math::Frustum>> cameras;
        std::unordered_set<Impl::Payload> visible_actors;
        double visible_query_ms_total = 0.0;
        for (std::uintptr_t camera_handle : camera_handles) {
            auto cam_read = camera_storage.try_acquire_read_nowait(camera_handle);
            if ( !cam_read.valid() ) continue;

            // 填充相机位置和视锥
            const CameraDevice& cam_dev = *cam_read;
            Math::Frustum frustum = Math::Frustum::from_camera(cam_dev);
            cameras.emplace_back(cam_dev.position,frustum);

            const auto visible_query_begin = std::chrono::steady_clock::now();
            std::vector<Impl::Payload> visible_for_camera = query_visible_for_camera(scene_handle,camera_handle);
            visible_query_ms_total += std::chrono::duration<double, std::milli>(
                                          std::chrono::steady_clock::now() - visible_query_begin)
                                          .count();
            visible_actors.insert(visible_for_camera.begin(),visible_for_camera.end());
        }

        // ---- M3 LRU 唤醒触发器 ----
        // 遍历可见 actor，检查是否有被 evict 后 offline 的
        std::vector<Events::ActorRestoreRequestedEvent> pending_restores;
        {
            std::shared_lock lock(impl_->mtx);
            auto scene_it = impl_->scenes.find(scene_handle);
            if (scene_it != impl_->scenes.end()) {
                auto& scene_state = scene_it->second;
                for (auto actor : visible_actors) {
                    auto it = impl_->offline_actors.find(actor);
                    if (it == impl_->offline_actors.end() || !it->second) continue;
                    auto state_it = scene_state.actor_load_states.find(actor);
                    if (state_it == scene_state.actor_load_states.end()) continue;
                    if (state_it->second != ActorLoadState::Unloaded) continue;
                    if (scene_state.loading_tasks.count(actor)) continue;
                    if (scene_state.unloading_tasks.count(actor)) continue;
                    pending_restores.push_back({scene_handle, actor});
                }
            }
        }
        for (const auto& evt : pending_restores) {
            if (impl_->ctx && impl_->ctx->event_bus())
                impl_->ctx->event_bus()->publish(evt);
        }

        std::vector<Events::ActorUnloadRequestedEvent> pending_unloads;
        std::vector<Events::ActorLoadRequestedEvent> pending_loads;
        {
            // Phase 1: shared_lock — 收集候选、计算距离、决定转换（只读不写）
            std::shared_lock lock(impl_->mtx);
            auto& scene_state = impl_->get_or_create(scene_handle);
            if (scene_state.cfg.enable_distance_culling && !cameras.empty()) {
                std::unordered_set<Impl::Payload> candidates;

                //仅收集预加载范围内的物体
                for (const auto& [cam_pos, _] : cameras) {
                    std::vector<Impl::Payload> sphere_results;
                    scene_state.tree.query_sphere(cam_pos, scene_state.cfg.preload_distance, sphere_results);
                    for (auto actor : sphere_results) {
                        candidates.insert(actor);
                    }
                }

                //保留所有非Unloaded状态的物体
                for (const auto& [actor,state] : scene_state.actor_load_states) {
                    if (state != ActorLoadState::Unloaded) {
                        candidates.insert(actor);
                    }
                }

                //仅处理候选物体
                for (auto actor : candidates) {
                    auto entry_it = scene_state.actor_to_entry.find(actor);
                    if (entry_it == scene_state.actor_to_entry.end()) continue;

                    const auto& aabb = entry_it->second;
                    auto state_it = scene_state.actor_load_states.find(actor);
                    if (state_it == scene_state.actor_load_states.end()) continue;
                    ActorLoadState state = state_it->second;  // 值拷贝，只读

                    // 计算物体到最近相机的欧氏距离
                    ktm::fvec3 center = aabb.center();
                    float min_distance = std::numeric_limits<float>::max();
                    for (const auto& [cam_pos,_] : cameras) {
                        min_distance = std::min(min_distance,ktm::distance(center,cam_pos));
                    }

                    // 状态机转换（只记录决策，不修改状态 — 由 Phase 2 统一应用）
                    switch (state) {
                        case ActorLoadState::Loaded:
                            if (min_distance > scene_state.cfg.unload_distance &&
                                !visible_actors.count(actor)) {
                                pending_unloads.push_back({scene_handle, actor});
                                }
                            break;

                        case ActorLoadState::Unloaded:
                            if (min_distance < scene_state.cfg.preload_distance) {
                                pending_loads.push_back({scene_handle, actor});
                            }
                            break;

                        default:
                            // 过渡状态不做任何操作，等待资源系统的完成事件
                            break;
                    }
                }
            }
        }
        // Phase 2: unique_lock — 应用状态转换（带 TOCTOU 重校验）
        if (!pending_unloads.empty() || !pending_loads.empty()) {
            std::unique_lock lock(impl_->mtx);
            auto& scene_state = impl_->get_or_create(scene_handle);

            for (auto it = pending_unloads.begin(); it != pending_unloads.end(); ) {
                auto state_it = scene_state.actor_load_states.find(it->actor);
                if (state_it != scene_state.actor_load_states.end() &&
                    state_it->second == ActorLoadState::Loaded) {
                    state_it->second = ActorLoadState::Unloading;
                    CFW_LOG_NOTICE("[SceneSystem] Published unload request for actor {} (distance culling)",
                                  it->actor);
                    ++it;
                    } else {
                        it = pending_unloads.erase(it);  // 状态已被异步事件改变，取消此事件
                    }
            }

            for (auto it = pending_loads.begin(); it != pending_loads.end(); ) {
                auto state_it = scene_state.actor_load_states.find(it->actor);
                if (state_it != scene_state.actor_load_states.end() &&
                    state_it->second == ActorLoadState::Unloaded) {
                    state_it->second = ActorLoadState::Loading;
                    CFW_LOG_NOTICE("[SceneSystem] Published preload request for actor {} (distance culling)",
                                  it->actor);
                    ++it;
                    } else {
                        it = pending_loads.erase(it);
                    }
            }
        }
        for (const auto& evt : pending_unloads) {
            if (impl_->ctx && impl_->ctx->event_bus())
                impl_->ctx->event_bus()->publish(evt);
        }
        for (const auto& evt : pending_loads) {
            if (impl_->ctx && impl_->ctx->event_bus())
                impl_->ctx->event_bus()->publish(evt);
        }

        // 不可见帧计数与淘汰
        std::vector<Events::ActorEvictRequestedEvent> pending_evictions;
        {
            std::unique_lock lock(impl_->mtx);
            Impl::SceneState& scene_state = impl_->get_or_create(scene_handle);
            for (std::uintptr_t actor_handle : actor_handles) {
                auto state_it = scene_state.actor_load_states.find(actor_handle);
                if (state_it == scene_state.actor_load_states.end() ||
                    state_it->second != ActorLoadState::Loaded) {
                    continue;
                }

                if (!scene_state.actor_to_entry.count(actor_handle)) {
                    scene_state.invisible_frames.erase(actor_handle);
                    continue;
                }

                if ( visible_actors.count(actor_handle) ) {
                    scene_state.invisible_frames[actor_handle] = 0;
                } else {
                    uint32_t cnt = ++scene_state.invisible_frames[actor_handle];

                    if ( scene_state.cfg.invisible_frames_to_evict > 0 &&
                        cnt >= static_cast<uint32_t>(scene_state.cfg.invisible_frames_to_evict) ) {
                        pending_evictions.push_back({scene_handle, actor_handle});
                        CFW_LOG_NOTICE("GeometrySystem: Evict requested for actor {} (invisible {} frames)",
                               actor_handle, cnt);
                        scene_state.invisible_frames[actor_handle] = 0;
                    }
                }
            }
        }
        for (const auto& evt : pending_evictions) {
            if (impl_->ctx && impl_->ctx->event_bus())
                impl_->ctx->event_bus()->publish(evt);
        }

        // 统计信息：使用读锁遍历，独立 stats_mutex 写入，减少主锁竞争
        {
            std::shared_lock lock(impl_->mtx);
            auto& scene_state = impl_->get_or_create(scene_handle);

            std::size_t loaded = 0, loading = 0, unloading = 0, unloaded = 0;
            for (const auto& [actor_handle, state] : scene_state.actor_load_states) {
                switch (state) {
                    case ActorLoadState::Loaded:    loaded++; break;
                    case ActorLoadState::Loading:   loading++; break;
                    case ActorLoadState::Unloading: unloading++; break;
                    case ActorLoadState::Unloaded:  unloaded++; break;
                }
            }

            std::lock_guard stats_lock(scene_state.stats_mutex);
            scene_state.stats.actor_total    = actor_handles.size();
            scene_state.stats.actor_visible  = visible_actors.size();
            scene_state.stats.octree_entries = octree_entries.size();
            scene_state.stats.last_query_ms = visible_query_ms_total;
            scene_state.stats.actor_loaded    = loaded;
            scene_state.stats.actor_loading   = loading;
            scene_state.stats.actor_unloading = unloading;
            scene_state.stats.actor_unloaded  = unloaded;
        }
        auto scene_write = scene_storage.try_acquire_write(scene_handle);
        if (scene_write.valid()) {
            SceneDevice& scene_dev_write = *scene_write;
            scene_dev_write.min_world = root_aabb.min;
            scene_dev_write.max_world = root_aabb.max;
            scene_dev_write.center_world = root_aabb.center();
            scene_dev_write.visible_actor_handles.assign(visible_actors.begin(),
                                                         visible_actors.end());
        }
    }

    // ========================================
    // 每帧资源预算检查：超过预算时主动淘汰最久未访问的冷资源
    // ========================================
    if (impl_->resource_memory_budget_mb > 0) {
        auto& rm = Resource::ResourceManager::get_instance();
        auto used = rm.used_memory_bytes();
        auto budget = rm.memory_budget();
        if (budget > 0 && used > budget) {
            CFW_LOG_NOTICE("[GeometrySystem] Resource memory {} MB over budget {} MB, evicting...",
                           used / (1024 * 1024), budget / (1024 * 1024));
            auto result = rm.evict_until_under_budget();
            if (result.success) {
                CFW_LOG_NOTICE("[GeometrySystem] Evicted resource {}, freed {} bytes "
                               "({} MB used after eviction)",
                               result.rid, result.bytes_freed,
                               rm.used_memory_bytes() / (1024 * 1024));
            } else {
                CFW_LOG_WARNING("[GeometrySystem] Eviction stalled: all resources pinned or in use "
                                "({} MB still over {} MB budget)",
                                rm.used_memory_bytes() / (1024 * 1024),
                                budget / (1024 * 1024));
            }
        }
    }
}

void GeometrySystem::shutdown() {
    CFW_LOG_NOTICE("GeometrySystem: Shutting down...");

    // 取消所有事件订阅
    if (impl_->ctx && impl_->ctx->event_bus()) {
        for (Kernel::EventId subscription_id : impl_->event_subscriptions) {
            impl_->ctx->event_bus()->unsubscribe(subscription_id);
        }
    }
    impl_->event_subscriptions.clear();

    std::unique_lock lock(impl_->mtx);
    std::vector<std::future<std::uint64_t>> load_futures;
    std::vector<std::future<bool>> unload_futures;
    for (auto& [scene,state] : impl_->scenes) {
        for (auto& [actor,future] : state.loading_tasks) {
            if (future.valid()) {
                load_futures.push_back(std::move(future));
            }
        }
        for (auto& [actor, future] : state.unloading_tasks) {
            if (future.valid()) {
                unload_futures.push_back(std::move(future));
            }
        }
    }
    lock.unlock();

    for (auto& f : load_futures) {
        if ( f.valid() ) {
            f.wait();
        }
    }
    for (auto& f : unload_futures) {
        if ( f.valid() ) {
            f.wait();
        }
    }
    lock.lock();
    for (auto& [scene,state] : impl_->scenes) {
        state.loading_tasks.clear();
        state.unloading_tasks.clear();
    }

    impl_->scenes.clear();
    impl_->offline_actors.clear();
    impl_->pending_gpu_releases.clear();

    // 等待并清理在途的异步 import 任务，避免 future 析构阻塞或悬挂回调。
    for (auto& [geom_handle, task] : impl_->pending_import_tasks) {
        if (task.future.valid()) task.future.wait();
    }
    impl_->pending_import_tasks.clear();

    // 释放 LRU ActorCache（确保在 shutdown 时清理磁盘/内存）
    impl_->actor_cache.reset();

    // 显式释放共享占位纹理，确保在 GPU device 仍存活时析构 HardwareImage。
    // 占位纹理现由 geometry_mesh_builder 模块持有（进程级单例，唯一所有者）。
    release_geometry_placeholder_texture();
}

// ============================================================================
// 配置
// ============================================================================

void GeometrySystem::set_visibility_config(std::uintptr_t scene, SceneVisibilityConfig cfg) {
    std::unique_lock lock(impl_->mtx);
    impl_->get_or_create(scene).cfg = cfg;
}

void GeometrySystem::set_distance_config(std::uintptr_t scene, float unload_dist,
                                    float preload_dist,bool enable) {
    std::unique_lock lock(impl_->mtx);
    auto& scene_state = impl_->get_or_create(scene);
    scene_state.cfg.enable_distance_culling = enable;
    scene_state.cfg.unload_distance = unload_dist;
    scene_state.cfg.preload_distance = preload_dist;
}

void GeometrySystem::set_cache_directory(std::filesystem::path dir) {
    impl_->actor_cache_dir = std::move(dir);
    // 如果 ActorCache 已创建，下次 evict 时会沿用旧目录；
    // 如果尚未创建，ensure_actor_cache() 将使用新目录。
    CFW_LOG_NOTICE("[GeometrySystem] Cache directory set to {}", impl_->actor_cache_dir.string());
}

void GeometrySystem::set_resource_memory_budget_mb(std::size_t mb) {
    impl_->resource_memory_budget_mb = mb;
    if (mb > 0) {
        Resource::ResourceManager::get_instance().set_memory_budget(mb * 1024 * 1024);
        CFW_LOG_NOTICE("[GeometrySystem] Resource memory budget set to {} MB", mb);
    } else {
        Resource::ResourceManager::get_instance().set_memory_budget(0);
        CFW_LOG_NOTICE("[GeometrySystem] Resource memory budget disabled (unlimited)");
    }
}

// ============================================================================
// 私有事件处理
// ============================================================================

void GeometrySystem::on_load_finished(const Events::ActorLoadFinishedEvent& event) {
    {
        std::unique_lock lock(impl_->mtx);
        auto scene_it = impl_->scenes.find(event.scene);
        if (scene_it != impl_->scenes.end()) {
            auto& state_map = scene_it->second.actor_load_states;
            auto actor_it = state_map.find(event.actor);
            if (actor_it != state_map.end() && actor_it->second == ActorLoadState::Loading) {
                actor_it->second = ActorLoadState::Loaded;
                impl_->offline_actors[event.actor] = false;
                CFW_LOG_NOTICE("GeometrySystem: Actor {} (scene: {}) load finished",
                               event.actor, event.scene);
            }
        }
    }
    // 不再重新发布 ActorLoadFinishedEvent（由 process_async_tasks 发布）。
    // 对外发布统一的驻留变更事件，外部系统只需订阅 ActorResidencyChangedEvent。
    if (impl_->ctx && impl_->ctx->event_bus()) {
        impl_->ctx->event_bus()->publish(Events::ActorResidencyChangedEvent{
            event.scene, event.actor, /*loaded=*/true});
    }
}

void GeometrySystem::on_unload_finished(const Events::ActorUnloadFinishedEvent& event) {
    {
        std::unique_lock lock(impl_->mtx);
        auto scene_it = impl_->scenes.find(event.scene);
        if (scene_it == impl_->scenes.end()) return;

        auto& state_map = scene_it->second.actor_load_states;
        auto actor_it = state_map.find(event.actor);
        if (actor_it != state_map.end() && actor_it->second == ActorLoadState::Unloading) {
            actor_it->second = ActorLoadState::Unloaded;
            impl_->offline_actors[event.actor] = true;
            CFW_LOG_NOTICE("GeometrySystem: Actor {} (scene: {}) unload finished",
                           event.actor, event.scene);
        }
    }
    // 不再重新发布 ActorUnloadFinishedEvent（由 process_async_tasks 发布）。
    // 对外发布统一的驻留变更事件，外部系统只需订阅 ActorResidencyChangedEvent。
    if (impl_->ctx && impl_->ctx->event_bus()) {
        impl_->ctx->event_bus()->publish(Events::ActorResidencyChangedEvent{
            event.scene, event.actor, /*loaded=*/false});
    }
}

// ============================================================================
// GPU 资源释放（unload 时由 process_async_tasks 调用）
// ============================================================================

// ============================================================================
// release_actor_gpu_resources
// 功能：释放指定 actor 占用的全部 GPU 资源（显存中的顶点/索引缓冲和纹理）
// 调用时机：process_async_tasks() 中处理 ActorUnloadFinishedEvent 时
// 注意：只清理 GPU 端资源，不删除 SharedDataHub 中的存储槽位
// ============================================================================
void GeometrySystem::release_actor_gpu_resources(std::uintptr_t actor) {
    // ---- 第 0 步：获取全局数据中心单例 ----
    // SharedDataHub 是所有系统共享的数据仓库，存 Actor/Profile/Geometry 等设备数据
    auto& hub = SharedDataHub::instance();

    // ---- 第 1 步：以只读模式获取 actor 数据 ----
    // try_acquire_read 返回一个 RAII 读锁守卫，离开作用域自动释放
    auto actor_read = hub.actor_storage().try_acquire_read(actor);
    if (!actor_read.valid()) return;  // actor 句柄无效（可能已被销毁），直接返回

    // ---- 第 2 步：用 visited 集合去重 ----
    // 一个 actor 的多个 profile 可能共享同一个 geometry（例如 optics 和 mechanics 引用同一几何体）
    // 用 unordered_set 记录已处理的 geometry，避免重复释放
    std::unordered_set<std::uintptr_t> visited_geometry_handles;

    // ---- 第 3 步：遍历 actor 身上每个 Profile ----
    // Profile 是"配件槽位"——它聚合了 optics/mechanics/geometry/acoustics 的句柄
    for (auto profile_handle : actor_read->profile_handles) {
        auto profile = hub.profile_storage().try_acquire_read(profile_handle);
        if (!profile) continue;  // profile 句柄已失效

        // ---- 第 4 步：从 Profile 的 4 条路径收集 geometry 句柄 ----
        // 路径 A：Profile 自身直接挂载的 geometry_handle
        // 路径 B：Profile → OpticsDevice → geometry_handle（光学设备可能引用几何体）
        // 路径 C：Profile → MechanicsDevice → geometry_handle（力学设备必然引用几何体，最常用）
        // 路径 D：Profile → AcousticsDevice → geometry_handle（声学设备可能引用几何体）
        std::vector<std::uintptr_t> geom_handles;

        // 路径 A：Profile 自身的 geometry 直连
        if (profile->geometry_handle != 0) {
            geom_handles.push_back(profile->geometry_handle);
        }
        // 路径 B：OpticsDevice（视觉渲染设备）→ geometry
        if (profile->optics_handle != 0) {
            if (auto optics = hub.optics_storage().try_acquire_read(profile->optics_handle)) {
                if (optics->geometry_handle != 0) {
                    geom_handles.push_back(optics->geometry_handle);
                }
            }
        }
        // 路径 C：MechanicsDevice（物理/变换设备）→ geometry（最常用的路径）
        if (profile->mechanics_handle != 0) {
            if (auto mech = hub.mechanics_storage().try_acquire_read(profile->mechanics_handle)) {
                if (mech->geometry_handle != 0) {
                    geom_handles.push_back(mech->geometry_handle);
                }
            }
        }
        // 路径 D：AcousticsDevice（声学设备）→ geometry
        if (profile->acoustics_handle != 0) {
            if (auto acoustics = hub.acoustics_storage().try_acquire_read(profile->acoustics_handle)) {
                if (acoustics->geometry_handle != 0) {
                    geom_handles.push_back(acoustics->geometry_handle);
                }
            }
        }

        // ---- 第 5 步：对每个收集到的 geometry 释放 GPU 资源 ----
        for (auto geom_handle : geom_handles) {
            // visited_geometry_handles.insert() 返回 pair<iter, bool>
            // .second == false 表示已存在 → 跳过，避免重复处理
            if (!visited_geometry_handles.insert(geom_handle).second) continue;

            // ---- 第 5.1 步：统计该 geometry 有多少个 mesh（子网格）----
            // 一个 GeometryDevice 可能包含多个 MeshDevice（例如一个模型有多个材质）
            uint32_t mesh_count = 0;
            if (auto geom_read = hub.geometry_storage().try_acquire_read(geom_handle)) {
                mesh_count = static_cast<uint32_t>(geom_read->mesh_handles.size());
            } else {
                continue;  // geometry 句柄已失效
            }

            // ---- 第 5.2 步：清理 LOD 缓存 ----
            // 每个 mesh 可能在 upload_lod_from_scene_data() 中创建了多级 LOD GPU 缓冲
            // make_lod_key(geom_handle, i) 生成唯一键：(geometry_handle << 32) | mesh_index
            {
                std::unique_lock lod_lock(impl_->lod_cache_mutex);  // 独占锁（写操作）
                for (uint32_t i = 0; i < mesh_count; ++i) {
                    impl_->lod_cache.erase(Impl::make_lod_key(geom_handle, i));
                }
            }  // lod_lock 在此析构，自动释放互斥锁

            // ---- 第 5.3 步：销毁 mesh_handles 中的 GPU 缓冲 ----
            // mesh_handles 是 vector<MeshDevice>，每个 MeshDevice 内含：
            //   vertexBuffer / indexBuffer（渲染用）
            //   vertexStorageBuffer / indexStorageBuffer（Compute Shader 用）
            //   textureBuffer（纹理）
            // clear() 触发每个元素的析构 → HardwareBuffer/HardwareImage 析构 → GPU 显存归还
            // 注意：model_resource_handle 保留不删，以便 reload 时能找到模型资源条目
            if (auto geom_write = hub.geometry_storage().try_acquire_write(geom_handle)) {
                geom_write->mesh_handles.clear();
            }  // geom_write 析构时自动释放写锁

            // ---- 第 5.4 步：日志 ----
            CFW_LOG_NOTICE("[GeometrySystem] Released GPU resources for geometry {}, "
                           "{} mesh(es), actor {}",
                           geom_handle,   // geometry 在 SharedDataHub 中的句柄地址
                           mesh_count,    // 释放了多少个 mesh 的 GPU 缓冲
                           actor);        // 所属 actor 句柄
        }
    }
}

// ============================================================================
// rebuild_actor_gpu_resources
// 功能：释放后重新加载 actor 时，重建全部 GPU 资源（顶点/索引缓冲 + 纹理）
// 调用时机：process_async_tasks() 检测到 load 任务完成后，发布事件前
// 参数：
//   actor — actor 句柄（SharedDataHub 中的地址）
//   rid   — 资源 UID（ResourceManager 分配的唯一标识，由 import_async 返回）
// 说明：这个函数是 unload → reload 生命周期中"重建"环节的核心
// ============================================================================
void GeometrySystem::rebuild_actor_gpu_resources(std::uintptr_t actor, std::uint64_t rid) {
    // ---- 第 0 步：获取两个全局单例 ----
    // SharedDataHub：管理所有系统共享的设备数据（actor/profile/geometry 等）
    auto& hub = SharedDataHub::instance();
    // ResourceManager：管理所有资源文件（Scene/Image 等），通过 UID 查找
    auto& resource_manager = Resource::ResourceManager::get_instance();

    // ---- 第 1 步：读取 actor 数据 ----
    auto actor_read = hub.actor_storage().try_acquire_read(actor);
    if (!actor_read.valid()) return;  // actor 句柄无效

    // ---- 第 2 步：去重集合（与 release 函数逻辑相同）----
    // 多个 profile 可能引用同一 geometry，用 set 防止重复重建
    std::unordered_set<std::uintptr_t> visited_geometry_handles;

    // ---- 第 3 步：遍历 actor 的所有 profile ----
    for (auto profile_handle : actor_read->profile_handles) {
        auto profile = hub.profile_storage().try_acquire_read(profile_handle);
        if (!profile) continue;

        // ---- 第 4 步：4 条路径收集 geometry 句柄（同 release 逻辑）----
        // 路径 A：Profile 直连 geometry
        // 路径 B：Profile → OpticsDevice → geometry
        // 路径 C：Profile → MechanicsDevice → geometry（最常用）
        // 路径 D：Profile → AcousticsDevice → geometry
        std::vector<std::uintptr_t> geom_handles;

        // 路径 A：profile 自身的 geometry_handle
        if (profile->geometry_handle != 0) {
            geom_handles.push_back(profile->geometry_handle);
        }
        // 路径 B：光学设备 → geometry
        if (profile->optics_handle != 0) {
            if (auto optics = hub.optics_storage().try_acquire_read(profile->optics_handle)) {
                if (optics->geometry_handle != 0) {
                    geom_handles.push_back(optics->geometry_handle);
                }
            }
        }
        // 路径 C：力学/物理设备 → geometry（渲染对象的主要路径）
        if (profile->mechanics_handle != 0) {
            if (auto mech = hub.mechanics_storage().try_acquire_read(profile->mechanics_handle)) {
                if (mech->geometry_handle != 0) {
                    geom_handles.push_back(mech->geometry_handle);
                }
            }
        }
        // 路径 D：声学设备 → geometry
        if (profile->acoustics_handle != 0) {
            if (auto acoustics = hub.acoustics_storage().try_acquire_read(profile->acoustics_handle)) {
                if (acoustics->geometry_handle != 0) {
                    geom_handles.push_back(acoustics->geometry_handle);
                }
            }
        }

        // ---- 第 5 步：对每个 geometry 重建 GPU 资源 ----
        for (auto geom_handle : geom_handles) {
            // 去重：同一 geometry 只处理一次
            if (!visited_geometry_handles.insert(geom_handle).second) continue;

            // ---- 第 5.1 步：判断是否需要重建 ----
            // model_resource_handle 是 SharedDataHub 中 ModelResource 条目的句柄
            // release() 时保留了它（未置零），通过它找到对应的模型资源条目
            // mesh_handles 在 release() 时已 clear()，所以 empty() == true 表示需要重建
            // 初始加载时 Python API 已填充 mesh_handles，此时不为空 → 无需重建
            std::uintptr_t model_res_handle = 0;  // ModelResource 句柄
            bool needs_rebuild = false;            // 是否需要重建 GPU 缓冲
            {
                auto geom_read = hub.geometry_storage().try_acquire_read(geom_handle);
                if (!geom_read) continue;  // geometry 已失效
                model_res_handle = geom_read->model_resource_handle;
                // 关键判断：mesh_handles 为空 → 被 release() 清理过 → 需要重建
                //          mesh_handles 不为空 → 初始加载已完成 → 无需重建
                needs_rebuild = geom_read->mesh_handles.empty();
            }  // geom_read 析构，释放读锁

            // ---- 第 5.2 步：更新 ModelResource 中的 model_id ----
            // reload 时 import_async 可能分配新的资源 UID，必须更新
            // 无论是否需要 rebuild 都要更新，确保后续 LOD 上传能正确查找到 Scene 数据
            if (model_res_handle != 0) {
                if (auto model_res = hub.model_resource_storage().try_acquire_write(model_res_handle)) {
                    model_res->model_id = rid;  // 写入新的资源 UID
                }
            }

            // ---- 第 5.3 步：如果不需要重建，跳过此 geometry ----
            // 初始加载场景：mesh_handles 已在 Python API 层创建完毕
            if (!needs_rebuild) {
                continue;  // 无需重建，直接处理下一个 geometry
            }

            // ---- 第 5.4 步：从 ResourceManager 获取导入的 Scene 数据 ----
            // rid 是 import_async 完成后返回的资源唯一标识
            // Scene 资源包含完整的模型数据：顶点/索引/材质/纹理/LOD 等
            auto scene_read = resource_manager.acquire_read<Resource::Scene>(rid);
            if (!scene_read.valid()) {
                CFW_LOG_ERROR("[GeometrySystem] Failed to acquire Scene resource for rid={}", rid);
                continue;  // 资源无效，跳过
            }
            auto& scene = *scene_read;  // 解引用读锁守卫，获得 Scene 数据引用

            // ================================================================
            // 阶段 A：创建 MeshDevice 数组（GPU 缓冲 + 纹理）
            // 构建逻辑收敛到 build_mesh_devices_from_scene（单一来源），
            // 与 Python API 层 Geometry 构造函数共用同一份实现。
            // 占位纹理由 builder 模块持有（进程级单例），无需在此创建。
            // ================================================================
            std::vector<MeshDevice> mesh_devices = build_mesh_devices_from_scene(scene);

            // ================================================================
            // 阶段 C：写回 GeometryDevice
            // 将重建好的 mesh_handles 写回 SharedDataHub
            // ================================================================

            // ---- 先清理旧 LOD 缓存 ----
            // mesh_handles 已经重建（新的 GPU 缓冲句柄），旧 LOD 条目指向已销毁的缓冲
            // 必须清除，否则下一帧 upload_lod_from_scene_data() 会检测到 mismatched handles 并重建
            {
                std::unique_lock lod_lock(impl_->lod_cache_mutex);  // 独占锁
                for (uint32_t i = 0; i < static_cast<uint32_t>(mesh_devices.size()); ++i) {
                    impl_->lod_cache.erase(Impl::make_lod_key(geom_handle, i));
                }
            }  // lod_lock 析构

            // ---- 将新 mesh_handles 写入 GeometryDevice ----
            if (auto geom_write = hub.geometry_storage().try_acquire_write(geom_handle)) {
                geom_write->mesh_handles = std::move(mesh_devices);  // move 语义，避免拷贝
            }  // geom_write 析构，释放写锁

            // ---- 日志：记录重建完成 ----
            CFW_LOG_NOTICE("[GeometrySystem] Rebuilt GPU resources for geometry {}, "
                           "{} mesh(es), actor {}, rid={}",
                           geom_handle,                // geometry 句柄
                           scene.data.meshes.size(),   // 重建的 mesh 数量
                           actor,                      // 所属 actor
                           rid);                       // 资源 UID
        }
    }
}

// ============================================================================
// 异步资源任务处理
// ============================================================================

void GeometrySystem::process_async_tasks() {
    auto& hub = SharedDataHub::instance();
    auto& actor_storage = hub.actor_storage();

    struct CompletedLoadTask {
        std::uintptr_t scene_handle;
        std::uintptr_t actor;
        std::uint64_t rid;
    };
    struct CompletedUnloadTask {
        std::uintptr_t scene_handle;
        std::uintptr_t actor;
        bool success;
    };
    struct DeferredLoadTask {
        std::uintptr_t scene_handle;
        std::uintptr_t actor;
        std::future<std::uint64_t> future;
    };
    struct DeferredUnloadTask {
        std::uintptr_t scene_handle;
        std::uintptr_t actor;
        std::future<bool> future;
    };

    std::vector<CompletedLoadTask> completed_loads;
    std::vector<CompletedUnloadTask> completed_unloads;
    std::vector<DeferredLoadTask> deferred_loads;
    std::vector<DeferredUnloadTask> deferred_unloads;
    {
        std::unique_lock lock(impl_->mtx);
        for (auto& [scene_handle, scene_state] : impl_->scenes) {
            auto load_it = scene_state.loading_tasks.begin();
            while (load_it != scene_state.loading_tasks.end()) {
                if (load_it->second.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                    deferred_loads.push_back({scene_handle, load_it->first, std::move(load_it->second)});
                    load_it = scene_state.loading_tasks.erase(load_it);
                } else {
                    ++load_it;
                }
            }

            auto unload_it = scene_state.unloading_tasks.begin();
            while (unload_it != scene_state.unloading_tasks.end()) {
                if (unload_it->second.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                    deferred_unloads.push_back({scene_handle, unload_it->first, std::move(unload_it->second)});
                    unload_it = scene_state.unloading_tasks.erase(unload_it);
                } else {
                    ++unload_it;
                }
            }
        }
    }

    // 无锁阶段调用 future.get()，处理结果
    for (auto& task : deferred_loads) {
        completed_loads.push_back({task.scene_handle, task.actor, task.future.get()});
    }
    for (auto& task : deferred_unloads) {
        completed_unloads.push_back({task.scene_handle, task.actor, task.future.get()});
    }

    for (const auto& task : completed_loads) {
        // 检查加载是否已被 on_unload_requested 取消（状态被改为非 Loading）
        {
            std::shared_lock lock(impl_->mtx);
            auto scene_it = impl_->scenes.find(task.scene_handle);
            if (scene_it != impl_->scenes.end()) {
                auto state_it = scene_it->second.actor_load_states.find(task.actor);
                if (state_it == scene_it->second.actor_load_states.end() ||
                    state_it->second != ActorLoadState::Loading) {
                    CFW_LOG_DEBUG("[SceneSystem] Actor {} load completed but was cancelled — skipping", task.actor);
                    continue;
                }
            }
        }

        if (task.rid != Resource::IResource::INVALID_UID) {
            // 重建 GPU 资源（mesh_handles + 纹理），恢复 model_resource_handle
            // 必须在发布 ActorLoadFinishedEvent 之前完成，
            // 以保证事件订阅者（渲染线程等）能读到有效的 GPU 缓冲
            rebuild_actor_gpu_resources(task.actor, task.rid);

            impl_->ctx->event_bus()->publish(Events::ActorLoadFinishedEvent{task.scene_handle,task.actor});
            CFW_LOG_DEBUG("[SceneSystem] Actor {} loaded (resource: {})", task.actor, task.rid);
        }else {
            CFW_LOG_ERROR("[SceneSystem] Failed to load actor {}", task.actor);
            // 加载失败，回滚到Unloaded状态
            {
                std::unique_lock lock(impl_->mtx);
                auto scene_it = impl_->scenes.find(task.scene_handle);
                if (scene_it != impl_->scenes.end()) {
                    scene_it->second.actor_load_states[task.actor] = ActorLoadState::Unloaded;
                }
            }
            impl_->ctx->event_bus()->publish(Events::ActorUnloadFinishedEvent{task.scene_handle, task.actor});
        }
    }

    std::vector<CompletedUnloadTask> failed_unloads;
    for (const auto& task : completed_unloads) {
        if (task.success) {
            // 释放 actor 关联的 GPU 资源（HardwareBuffer / HardwareImage）
            release_actor_gpu_resources(task.actor);

            {
                std::unique_lock lock(impl_->mtx);
                auto scene_it = impl_->scenes.find(task.scene_handle);
                if (scene_it != impl_->scenes.end()) {
                    scene_it->second.unload_retry_counts.erase(task.actor);
                }
            }
            impl_->ctx->event_bus()->publish(Events::ActorUnloadFinishedEvent{task.scene_handle, task.actor});
            CFW_LOG_DEBUG("[SceneSystem] Actor {} unloaded", task.actor);
        } else {
            // 卸载失败，保存到列表中后续处理重试
            failed_unloads.push_back(task);
        }
    }

    //卸载失败重试
    if (!failed_unloads.empty()) {
        std::vector<Events::ActorUnloadFinishedEvent> deferred_events;
        std::vector<Events::ActorResidencyChangedEvent> deferred_residency;
        {
            std::unique_lock lock(impl_->mtx);
            for (const auto& task : failed_unloads) {
                auto scene_it = impl_->scenes.find(task.scene_handle);
                if (scene_it == impl_->scenes.end()) {
                    continue;
                }
                auto& scene_state = scene_it->second;

                auto state_it = scene_state.actor_load_states.find(task.actor);
                if (state_it == scene_state.actor_load_states.end()) {
                    continue;
                }

                int& retry_count = scene_state.unload_retry_counts[task.actor];
                CFW_LOG_WARNING("[SceneSystem] Actor 0x%lx unload delayed (resource in use), retry %d/10",
                               (unsigned long)task.actor, retry_count + 1);

                if (++retry_count >= 10) {
                    CFW_LOG_ERROR("[SceneSystem] Actor 0x%lx unload failed after 10 retries, resource is permanently in use — reverting to Loaded",
                                 (unsigned long)task.actor);
                    scene_state.unload_retry_counts.erase(task.actor);
                    scene_state.actor_load_states[task.actor] = ActorLoadState::Loaded;
                    deferred_residency.push_back(
                        {task.scene_handle, task.actor, /*loaded=*/true});
                } else {
                    auto actor_read = actor_storage.try_acquire_read(task.actor);
                    if (actor_read.valid()) {
                        if (!actor_read->model_path.empty()) {
                            auto normalized = actor_read->model_path.is_relative()
                                ? std::filesystem::absolute(actor_read->model_path)
                                : actor_read->model_path;
                            std::error_code ec;
                            normalized = std::filesystem::weakly_canonical(normalized, ec);
                            if (ec) normalized = actor_read->model_path;
                            auto rid = Resource::IResource::generate_uid(normalized);
                            scene_state.unloading_tasks[task.actor] =
                                Resource::ResourceManager::get_instance().remove_cache_async(rid);
                        } else {
                            CFW_LOG_WARNING("[SceneSystem] Actor 0x%lx model path empty, mark as unloaded",
                                           (unsigned long)task.actor);
                            scene_state.unload_retry_counts.erase(task.actor);
                            scene_state.actor_load_states[task.actor] = ActorLoadState::Unloaded;
                            deferred_events.push_back({task.scene_handle, task.actor});
                            // on_unload_finished 检查 Unloading 状态，此处已是 Unloaded 不会通过
                            // 所以直接在此 push residency 事件
                            deferred_residency.push_back(
                                {task.scene_handle, task.actor, /*loaded=*/false});
                        }
                    } else {
                        CFW_LOG_WARNING("[SceneSystem] Actor 0x%lx handle invalid, clean up all states",
                                       (unsigned long)task.actor);
                        scene_state.unload_retry_counts.erase(task.actor);
                        scene_state.actor_load_states.erase(task.actor);
                        impl_->offline_actors.erase(task.actor);
                        deferred_residency.push_back(
                            {task.scene_handle, task.actor, /*loaded=*/false});
                    }
                }
            }
        }
        for (const auto& evt : deferred_events) {
            impl_->ctx->event_bus()->publish(evt);
        }
        for (const auto& evt : deferred_residency) {
            impl_->ctx->event_bus()->publish(evt);
        }
    }
}

// ============================================================================
// 资源请求事件处理
// ============================================================================

// 锁顺序: impl_->mtx → Storage 槽位锁 (try_acquire_read)。
// 不要在持有 Storage ReadHandle/WriteHandle 的作用域内获取 impl_->mtx，
// 否则会与 update() 中的 Storage→释放→impl_->mtx 路径形成死锁环。
void GeometrySystem::on_load_requested(const Events::ActorLoadRequestedEvent& e) {
    std::unique_lock lock(impl_->mtx);
    auto scene_it = impl_->scenes.find(e.scene);
    if (scene_it == impl_->scenes.end()) {
        return;
    }

    auto& scene_state = scene_it->second;
    if (scene_state.loading_tasks.count(e.actor) || scene_state.unloading_tasks.count(e.actor)) {
        return;
    }

    auto& actor_storage = SharedDataHub::instance().actor_storage();
    auto actor_read = actor_storage.try_acquire_read(e.actor);
    if (!actor_read.valid() || actor_read->model_path.empty()) {
        CFW_LOG_ERROR("[GeometrySystem] Invalid actor or empty model path: {}", e.actor);
        scene_state.actor_load_states[e.actor] = ActorLoadState::Unloaded;
        lock.unlock();
        impl_->ctx->event_bus()->publish(Events::ActorUnloadFinishedEvent{e.scene,e.actor});
        return;
    }

    CFW_LOG_NOTICE("[GeometrySystem] Start loading actor {} (path: {})",
                  e.actor, Utils::path_to_utf8(actor_read->model_path));
    scene_state.loading_tasks[e.actor] = Resource::ResourceManager::get_instance().import_async(actor_read->model_path);
}

// 锁顺序同 on_load_requested: impl_->mtx → Storage。
void GeometrySystem::on_unload_requested(const Events::ActorUnloadRequestedEvent& e) {
    std::unique_lock lock(impl_->mtx);
    auto scene_it = impl_->scenes.find(e.scene);
    if (scene_it == impl_->scenes.end()) return;

    auto& scene_state = scene_it->second;
    if (scene_state.loading_tasks.count(e.actor) || scene_state.unloading_tasks.count(e.actor)) {
        Events::ActorResidencyChangedEvent deferred;
        bool has_deferred = false;
        if (scene_state.unloading_tasks.count(e.actor)) {
            scene_state.unloading_tasks.erase(e.actor);
            scene_state.unload_retry_counts.erase(e.actor);
            scene_state.actor_load_states[e.actor] = ActorLoadState::Loaded;
            deferred = {e.scene, e.actor, /*loaded=*/true};
            has_deferred = true;
            CFW_LOG_NOTICE("[GeometrySystem] Cancelled pending unload for actor {}", e.actor);
        }
        if (scene_state.loading_tasks.count(e.actor)) {
            // 加载进行中 — 将状态设为 Unloaded，加载完成时 process_async_tasks 检测到非 Loading 状态会跳过
            scene_state.actor_load_states[e.actor] = ActorLoadState::Unloaded;
            deferred = {e.scene, e.actor, /*loaded=*/false};
            has_deferred = true;
            CFW_LOG_NOTICE("[GeometrySystem] Unload requested during load for actor {} — cancelling load", e.actor);
        }
        if (has_deferred) {
            lock.unlock();
            impl_->ctx->event_bus()->publish(deferred);
        }
        return;
    }

    auto& actor_storage = SharedDataHub::instance().actor_storage();
    auto actor_read = actor_storage.try_acquire_read(e.actor);
    if (!actor_read.valid() || actor_read->model_path.empty()) {
        scene_state.actor_load_states[e.actor] = ActorLoadState::Unloaded;
        lock.unlock();
        impl_->ctx->event_bus()->publish(Events::ActorUnloadFinishedEvent{e.scene, e.actor});
        return;
    }

    auto normalized = actor_read->model_path.is_relative()
        ? std::filesystem::absolute(actor_read->model_path)
        : actor_read->model_path;
    std::error_code ec;
    normalized = std::filesystem::weakly_canonical(normalized, ec);
    if (ec) normalized = actor_read->model_path;
    auto rid = Resource::IResource::generate_uid(normalized);

    CFW_LOG_NOTICE("[GeometrySystem] Start unloading actor {} (path: {})",
                  e.actor, Utils::path_to_utf8(actor_read->model_path));
    scene_state.unload_retry_counts[e.actor] = 0;
    scene_state.unloading_tasks[e.actor] = Resource::ResourceManager::get_instance().remove_cache_async(rid);
}

// ============================================================================
// LRU ActorCache：ensure + evict/restore 事件处理
// ============================================================================

void GeometrySystem::Impl::ensure_actor_cache() {
    if (actor_cache) return;
    if (actor_cache_dir.empty()) {
        // 默认目录：可执行文件同级的 cache/actors/
        actor_cache_dir = std::filesystem::current_path() / "cache" / "actors";
    }
    actor_cache = std::make_unique<Corona::Cache::ActorCache>(
        kDefaultMemCacheBytes,
        kDefaultDiskCacheBytes,
        actor_cache_dir);
    CFW_LOG_NOTICE("[GeometrySystem] ActorCache initialized: mem={}MB disk={}MB dir={}",
                   kDefaultMemCacheBytes / (1024 * 1024),
                   kDefaultDiskCacheBytes / (1024 * 1024),
                   actor_cache_dir.string());
}

void GeometrySystem::on_evict_requested(const Events::ActorEvictRequestedEvent& event) {
    impl_->ensure_actor_cache();

    auto& hub = SharedDataHub::instance();
    const auto now = std::chrono::steady_clock::now();

    // ---- 第 1 步：防抖检查（5 秒内不重复快照） ----
    {
        auto it = impl_->last_snapshot_time.find(event.actor);
        if (it != impl_->last_snapshot_time.end()) {
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - it->second);
            if (elapsed.count() < 5) return;
        }
    }

    // ---- 第 2 步：读取 actor 完整状态，构建 ActorStreamingRecord ----
    auto actor_read = hub.actor_storage().try_acquire_read(event.actor);
    if (!actor_read) return;

    Corona::Cache::ActorStreamingRecord rec;

    // 身份
    rec.scene = event.scene;
    rec.actor = event.actor;

    // 核心字段
    rec.model_path    = actor_read->model_path;
    rec.follow_camera = actor_read->follow_camera;
    rec.profile_handles = actor_read->profile_handles;  // 全量拷贝

    // 遍历 profiles 收集 geometry_handles / resource_ids / transform / 运行时标志
    bool transform_captured = false;
    bool optics_captured   = false;
    bool physics_captured  = false;
    for (auto profile_handle : actor_read->profile_handles) {
        auto profile = hub.profile_storage().try_acquire_read(profile_handle);
        if (!profile) continue;

        // 收集 geometry_handle
        if (profile->geometry_handle) {
            rec.geometry_handles.push_back(profile->geometry_handle);

            // 收集 resource_id: geometry → model_resource → model_id
            auto geom = hub.geometry_storage().try_acquire_read(profile->geometry_handle);
            if (geom && geom->model_resource_handle) {
                auto model_res = hub.model_resource_storage().try_acquire_read(geom->model_resource_handle);
                if (model_res && model_res->model_id != 0) {
                    rec.resource_ids.push_back(model_res->model_id);
                }
            }
        }

        // 从首个有效 profile 收集 transform + physics_enabled
        if (!transform_captured && profile->mechanics_handle) {
            auto mech = hub.mechanics_storage().try_acquire_read(profile->mechanics_handle);
            if (mech) {
                if (!physics_captured) {
                    rec.physics_enabled = mech->physics_enabled;
                    physics_captured = true;
                }

                if (mech->geometry_handle) {
                    auto geom = hub.geometry_storage().try_acquire_read(mech->geometry_handle);
                    if (geom && geom->transform_handle) {
                        auto xform = hub.model_transform_storage().try_acquire_read(geom->transform_handle);
                        if (xform) {
                            rec.transform = *xform;  // ModelTransform 值拷贝
                            transform_captured = true;
                        }
                    }
                }
            }
        }

        // 从首个有效 profile 收集 optics_visible（独立于 transform）
        if (!optics_captured && profile->optics_handle) {
            auto optics = hub.optics_storage().try_acquire_read(profile->optics_handle);
            if (optics) {
                rec.optics_visible = optics->visible;
                optics_captured = true;
            }
        }
    }

    // ---- 第 3 步：存入 ActorCache ----
    if (!impl_->actor_cache->put(event.actor, rec)) {
        CFW_LOG_ERROR("[GeometrySystem] Failed to cache actor {} stream record", event.actor);
    }

    // ---- 第 4 步：标记 offline + 延迟 GPU 释放 ----
    // 不在事件处理中直接调用 release_actor_gpu_resources，
    // 避免与 OpticsSystem 渲染线程产生 data race。
    // 改为加入 pending_gpu_releases 集合，在下一帧 update() 头部释放。
    {
        std::unique_lock lock(impl_->mtx);
        impl_->offline_actors[event.actor] = true;
        impl_->pending_gpu_releases.insert(event.actor);
        auto scene_it = impl_->scenes.find(event.scene);
        if (scene_it != impl_->scenes.end()) {
            scene_it->second.actor_load_states[event.actor] = ActorLoadState::Unloaded;
        }
    }

    impl_->last_snapshot_time[event.actor] = now;

    CFW_LOG_NOTICE("[GeometrySystem] Actor {} evicted: cached stream record "
                   "({} profiles, {} geometries, {} resource_ids, path={}, "
                   "physics={}, optics_visible={}, follow_camera={})",
                   event.actor,
                   rec.profile_handles.size(), rec.geometry_handles.size(),
                   rec.resource_ids.size(), rec.model_path.string(),
                   rec.physics_enabled, rec.optics_visible, rec.follow_camera);
}

void GeometrySystem::on_restore_requested(const Events::ActorRestoreRequestedEvent& event) {
    impl_->ensure_actor_cache();

    auto& hub = SharedDataHub::instance();

    // ---- 第 1 步：从 ActorCache 获取流式记录 ----
    auto rec = impl_->actor_cache->get(event.actor);
    std::filesystem::path model_path;

    if (rec) {
        model_path = rec->model_path;
        CFW_LOG_NOTICE("[GeometrySystem] Restoring actor {} from cache: "
                       "path={}, profiles={}, geometries={}, resource_ids={}, "
                       "follow_camera={}, physics_enabled={}, optics_visible={}, priority={}",
                       event.actor, model_path.string(),
                       rec->profile_handles.size(), rec->geometry_handles.size(),
                       rec->resource_ids.size(), rec->follow_camera,
                       rec->physics_enabled, rec->optics_visible, rec->priority);
    } else {
        // 缓存未命中：回退到从 ActorDevice 读取 model_path
        auto actor_read = hub.actor_storage().try_acquire_read(event.actor);
        if (!actor_read) {
            CFW_LOG_ERROR("[GeometrySystem] Restore failed: actor {} not in storage", event.actor);
            return;
        }
        model_path = actor_read->model_path;
        CFW_LOG_NOTICE("[GeometrySystem] Restoring actor {} from disk (cache miss, path={})",
                       event.actor, model_path.string());
    }

    if (model_path.empty()) {
        CFW_LOG_ERROR("[GeometrySystem] Restore failed: actor {} has empty model path", event.actor);
        return;
    }

    // ---- 第 1.5 步：恢复运行时状态到 SharedDataHub ----
    // evict 时存入 ActorStreamingRecord 的 transform / physics_enabled /
    // optics_visible 在 restore 时写回对应的存储槽位，保证 actor 恢复后
    // 渲染/物理看到的是 evict 前的状态而非默认值。
    if (rec) {
        auto actor_read = hub.actor_storage().try_acquire_read(event.actor);
        if (actor_read) {
            for (auto ph : actor_read->profile_handles) {
                auto profile = hub.profile_storage().try_acquire_read(ph);
                if (!profile) continue;

                // 恢复 transform（通过 geometry → transform_handle）
                if (profile->geometry_handle) {
                    auto geom = hub.geometry_storage().try_acquire_read(
                        profile->geometry_handle);
                    if (geom && geom->transform_handle) {
                        auto xform = hub.model_transform_storage().try_acquire_write(
                            geom->transform_handle);
                        if (xform) {
                            *xform = rec->transform;
                        }
                    }
                }

                // 恢复 physics_enabled
                if (profile->mechanics_handle) {
                    auto mech = hub.mechanics_storage().try_acquire_write(
                        profile->mechanics_handle);
                    if (mech) {
                        mech->physics_enabled = rec->physics_enabled;
                    }
                }

                // 恢复 optics_visible
                if (profile->optics_handle) {
                    auto optics = hub.optics_storage().try_acquire_write(
                        profile->optics_handle);
                    if (optics) {
                        optics->visible = rec->optics_visible;
                    }
                }
            }
        }
        CFW_LOG_NOTICE("[GeometrySystem] Restored actor {} state: pos=({:.1f},{:.1f},{:.1f}) "
                       "physics={} optics_visible={}",
                       event.actor,
                       rec->transform.position.x, rec->transform.position.y,
                       rec->transform.position.z,
                       rec->physics_enabled, rec->optics_visible);
    }

    // ---- 第 2 步：检查是否已在加载/卸载中，然后启动异步导入 ----
    {
        std::unique_lock lock(impl_->mtx);
        auto scene_it = impl_->scenes.find(event.scene);
        if (scene_it == impl_->scenes.end()) return;
        auto& scene_state = scene_it->second;

        if (scene_state.loading_tasks.count(event.actor) ||
            scene_state.unloading_tasks.count(event.actor)) {
            CFW_LOG_NOTICE("[GeometrySystem] Restore: actor {} already in transition, skip",
                           event.actor);
            return;
        }

        // 如果该 actor 还在待释放 GPU 队列中，移除（不需要释放了）
        impl_->pending_gpu_releases.erase(event.actor);

        scene_state.actor_load_states[event.actor] = ActorLoadState::Loading;
        scene_state.loading_tasks[event.actor] =
            Resource::ResourceManager::get_instance().import_async(model_path);
    }

    CFW_LOG_NOTICE("[GeometrySystem] Restore started for actor {} ({})", event.actor,
                   model_path.string());
}

// ============================================================================
// 动态减面 (Mesh Simplification) 公共 API
// ============================================================================

GeometrySystem::RenderMeshBuffers GeometrySystem::select_render_buffers(
    std::uintptr_t          geometry_handle,
    uint32_t                mesh_index,
    const ktm::fvec3&       camera_pos,
    float                   camera_fov_deg,
    const ktm::fvec3&       world_center,
    float                   bounding_radius,
    const RenderMeshBuffers& fallback) const {

    // 屏幕占比由 GeometrySystem 内部计算，optics 无需关心
    const float screen_ratio = compute_screen_ratio(
        camera_pos, camera_fov_deg, world_center, bounding_radius);

    // 复用 resolve_lod_buffers 的选级 + 降级逻辑（单次加锁）
    const LODMeshBuffers* lod = resolve_lod_buffers(geometry_handle, mesh_index, screen_ratio);

    // 无 LOD / 未就绪 / 缓冲无效 → 原样返回 fallback，保证始终可渲染
    if (lod == nullptr || !lod->vertex_buffer || !lod->index_buffer) {
        return fallback;
    }

    RenderMeshBuffers out;
    out.vertex         = lod->vertex_buffer;
    out.index          = lod->index_buffer;
    // StorageBuffer 可能缺失：缺失时沿用 fallback 的，避免 compute 路径拿到空句柄
    out.vertex_storage = lod->vertex_storage ? lod->vertex_storage : fallback.vertex_storage;
    out.index_storage  = lod->index_storage  ? lod->index_storage  : fallback.index_storage;
    return out;
}

const LODMeshBuffers* GeometrySystem::get_lod_buffers(
    std::uintptr_t geometry_handle,
    uint32_t       mesh_index,
    int            lod_level) const {

    std::shared_lock lock(impl_->lod_cache_mutex);
    auto key = Impl::make_lod_key(geometry_handle, mesh_index);
    auto it = impl_->lod_cache.find(key);
    if (it == impl_->lod_cache.end()) return nullptr;
    if (lod_level < 0 || static_cast<size_t>(lod_level) >= it->second.levels.size())
        return nullptr;
    auto& level = it->second.levels[lod_level];
    // 降级：如果目标级别未就绪，回退到 LOD 0
    if (!level.ready && lod_level > 0) {
        auto& lod0 = it->second.levels[0];
        return lod0.ready ? &lod0 : nullptr;
    }
    return level.ready ? &level : nullptr;
}

int GeometrySystem::get_lod_count(std::uintptr_t geometry_handle,
                                  uint32_t       mesh_index) const {
    std::shared_lock lock(impl_->lod_cache_mutex);
    auto key = Impl::make_lod_key(geometry_handle, mesh_index);
    auto it = impl_->lod_cache.find(key);
    if (it == impl_->lod_cache.end()) return 0;
    return static_cast<int>(it->second.levels.size());
}

int GeometrySystem::resolve_lod_level(std::uintptr_t geometry_handle,
                                      uint32_t       mesh_index,
                                      float          screen_ratio) const {

    std::shared_lock lock(impl_->lod_cache_mutex);
    auto key = Impl::make_lod_key(geometry_handle, mesh_index);
    auto it = impl_->lod_cache.find(key);
    if (it == impl_->lod_cache.end()) return 0;

    std::vector<float> thresholds;
    for (size_t i = 1; i < it->second.levels.size(); ++i) {
        thresholds.push_back(it->second.levels[i].screen_threshold);
    }

    int selected = select_lod_level(screen_ratio, thresholds);

    // 降级到最近的已就绪级别
    while (selected > 0) {
        if (static_cast<size_t>(selected) < it->second.levels.size()
            && it->second.levels[selected].ready)
            break;
        selected--;
    }
    return selected;
}

const LODMeshBuffers* GeometrySystem::resolve_lod_buffers(
    std::uintptr_t geometry_handle,
    uint32_t       mesh_index,
    float          screen_ratio) const {

    std::shared_lock lock(impl_->lod_cache_mutex);
    auto key = Impl::make_lod_key(geometry_handle, mesh_index);
    auto it = impl_->lod_cache.find(key);
    if (it == impl_->lod_cache.end()) return nullptr;

    // 构建阈值列表（LOD 1..N 的 screen_threshold）
    std::vector<float> thresholds;
    for (size_t i = 1; i < it->second.levels.size(); ++i) {
        thresholds.push_back(it->second.levels[i].screen_threshold);
    }

    int selected = select_lod_level(screen_ratio, thresholds);

    // 降级到最近的已就绪级别
    while (selected > 0) {
        if (static_cast<size_t>(selected) < it->second.levels.size()
            && it->second.levels[selected].ready)
            break;
        selected--;
    }

    // 返回缓冲（与 get_lod_buffers 相同的降级策略）
    if (selected < 0 || static_cast<size_t>(selected) >= it->second.levels.size())
        return nullptr;

    auto& level = it->second.levels[selected];
    if (!level.ready && selected > 0) {
        auto& lod0 = it->second.levels[0];
        return lod0.ready ? &lod0 : nullptr;
    }
    return level.ready ? &level : nullptr;
}

// ============================================================================
// BVH 射线查询
// ============================================================================

std::vector<uint32_t> GeometrySystem::query_mesh_ray(
    std::uintptr_t   geometry_handle,
    uint32_t         mesh_index,
    int              lod_level,
    const ktm::fvec3& origin,
    const ktm::fvec3& inv_dir) const
{
    std::shared_lock lock(impl_->lod_cache_mutex);
    auto key = Impl::make_lod_key(geometry_handle, mesh_index);
    auto it  = impl_->lod_cache.find(key);
    if (it == impl_->lod_cache.end()) return {};
    if (lod_level < 0 || static_cast<size_t>(lod_level) >= it->second.per_level_bvh.size())
        return {};

    std::vector<uint32_t> hits;
    it->second.per_level_bvh[lod_level].query_ray(origin, inv_dir, hits);
    return hits;
}

std::optional<Spatial::BVH<uint32_t>::Hit> GeometrySystem::query_mesh_closest_hit(
    std::uintptr_t   geometry_handle,
    uint32_t         mesh_index,
    int              lod_level,
    const ktm::fvec3& origin,
    const ktm::fvec3& inv_dir,
    float            t_max) const
{
    std::shared_lock lock(impl_->lod_cache_mutex);
    auto key = Impl::make_lod_key(geometry_handle, mesh_index);
    auto it  = impl_->lod_cache.find(key);
    if (it == impl_->lod_cache.end()) return std::nullopt;
    if (lod_level < 0 || static_cast<size_t>(lod_level) >= it->second.per_level_bvh.size())
        return std::nullopt;

    return it->second.per_level_bvh[lod_level].closest_hit(origin, inv_dir, t_max);
}

// ============================================================================
// 动态减面内部管线
// ============================================================================

namespace {

/// 从 CPU 端顶点+索引构建 BVH（payload = 三角形下标）
/// @param vertices 顶点数组
/// @param indices  uint16 索引数组（每 3 个一组构成三角形）
/// @return 构建好的 BVH，无数据时返回空 BVH

[[nodiscard]] Spatial::BVH<uint32_t> build_triangle_bvh(
    const std::vector<Resource::Vertex>&    vertices,
    const std::vector<std::uint16_t>&       indices)
{
    Spatial::BVH<uint32_t> bvh;
    if (indices.size() < 3) return bvh;

    std::vector<Spatial::BVH<uint32_t>::Entry> entries;
    entries.reserve(indices.size() / 3);

    for (size_t i = 0; i + 2 < indices.size(); i += 3) {
        const auto& v0 = vertices[indices[i]];
        const auto& v1 = vertices[indices[i + 1]];
        const auto& v2 = vertices[indices[i + 2]];

        Spatial::AABB aabb;
        aabb.min.x = std::min({v0.position[0], v1.position[0], v2.position[0]});
        aabb.min.y = std::min({v0.position[1], v1.position[1], v2.position[1]});
        aabb.min.z = std::min({v0.position[2], v1.position[2], v2.position[2]});
        aabb.max.x = std::max({v0.position[0], v1.position[0], v2.position[0]});
        aabb.max.y = std::max({v0.position[1], v1.position[1], v2.position[1]});
        aabb.max.z = std::max({v0.position[2], v1.position[2], v2.position[2]});
        entries.push_back({static_cast<uint32_t>(i / 3), aabb});
    }

    bvh.build(entries);
    return bvh;
}

// 收集所有场景所有相机的世界位置（用于流式加载的距离排序）。
[[nodiscard]] std::vector<ktm::fvec3> collect_camera_positions() {
    auto& hub = SharedDataHub::instance();
    auto& camera_storage = hub.camera_storage();
    std::vector<ktm::fvec3> positions;
    for (auto sit = hub.scene_storage().cbegin(); sit != hub.scene_storage().cend(); ++sit) {
        for (std::uintptr_t cam_handle : sit->camera_handles) {
            if (auto cam = camera_storage.try_acquire_read_nowait(cam_handle)) {
                positions.push_back(cam->position);
            }
        }
    }
    return positions;
}

// 点 p 到最近相机的距离平方；无相机时返回 0（不影响排序稳定性）。
[[nodiscard]] float nearest_camera_dist2(const ktm::fvec3& p,
                                         const std::vector<ktm::fvec3>& cameras) {
    if (cameras.empty()) return 0.0f;
    float best = std::numeric_limits<float>::max();
    for (const auto& c : cameras) {
        const float dx = p.x - c.x, dy = p.y - c.y, dz = p.z - c.z;
        best = std::min(best, dx * dx + dy * dy + dz * dz);
    }
    return best;
}

}  // namespace

void GeometrySystem::process_pending_geometry_imports() {
    auto& hub = SharedDataHub::instance();
    auto& resource_manager = Resource::ResourceManager::get_instance();
    auto& geom_storage = hub.geometry_storage();

    // ---- 阶段 1：轮询已完成的 import 任务 ----
    // future 就绪 → 取 model_id → 写入 ModelResource 槽 → 转 PendingBuild。
    // 失败（rid==0）→ 转 Failed，不再重试。
    {
        std::vector<Impl::Payload> done_handles;
        for (auto& [geom_handle, task] : impl_->pending_import_tasks) {
            if (task.future.valid() &&
                task.future.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                done_handles.push_back(geom_handle);
            }
        }
        for (auto geom_handle : done_handles) {
            const std::uint64_t task_epoch = impl_->pending_import_tasks[geom_handle].epoch;
            std::uint64_t rid = impl_->pending_import_tasks[geom_handle].future.get();
            impl_->pending_import_tasks.erase(geom_handle);

            // 第 1 步：更新 geometry 状态 / model_id（geom_write 作用域内完成并尽早释放，
            // 避免与下方 mechanics 槽锁同时持有 → 杜绝跨槽锁序倒置）。
            bool import_ok = false;
            {
                auto geom_write = geom_storage.try_acquire_write(geom_handle);
                if (!geom_write.valid()) continue;  // geometry 已销毁

                // 防 slot 复用 ABA：本槽可能在 import 在途期间被 deallocate→复用为新对象
                // （allocate 时 T{} 把 import_epoch 重置为 0 或新对象有自己的 epoch）。
                // epoch 不符说明这已不是当初发起 import 的那个对象，丢弃本次结果。
                if (geom_write->import_epoch != task_epoch) {
                    CFW_LOG_NOTICE("[GeometrySystem] Stale async import discarded for geometry {} "
                                   "(epoch {} != {}, slot reused)",
                                   geom_handle, task_epoch, geom_write->import_epoch);
                    continue;
                }

                if (rid == Resource::IResource::INVALID_UID || rid == 0) {
                    CFW_LOG_ERROR("[GeometrySystem] Async import failed for geometry {} (path={})",
                                  geom_handle, geom_write->model_path_utf8);
                    geom_write->gpu_build_state = GeometryDevice::GpuBuildState::Failed;
                    geom_write->import_epoch = 0;  // 任务结束
                    continue;
                }

                if (geom_write->model_resource_handle) {
                    if (auto mr = hub.model_resource_storage().try_acquire_write(geom_write->model_resource_handle)) {
                        mr->model_id = rid;
                    }
                }
                geom_write->gpu_build_state = GeometryDevice::GpuBuildState::PendingBuild;
                geom_write->import_epoch = 0;  // import 阶段完成，清零
                import_ok = true;
            }  // geom_write 释放
            if (!import_ok) continue;

            // 第 2 步：回填 MechanicsDevice AABB（geometry 槽锁已释放）。
            // Mechanics 在 Python 同步构造时读到 model_id=0 → AABB 为 0；
            // 这里用 Scene 的 AABB 回填，八叉树下帧重建即自愈。
            // 注意：Storage 迭代器在当前槽持有锁，不能在迭代中对同槽再 acquire_write
            // （会重入死锁）。故先 const 遍历收集句柄，迭代结束后再写。
            if (auto scene = resource_manager.acquire_read<Resource::Scene>(rid)) {
                const auto aabb_min = scene->get_scene_aabb().min;  // std::array<float,3>
                const auto aabb_max = scene->get_scene_aabb().max;
                auto& mech_storage = hub.mechanics_storage();

                std::vector<std::uintptr_t> mech_handles;
                for (auto mit = mech_storage.cbegin(); mit != mech_storage.cend(); ++mit) {
                    if (mit->geometry_handle == geom_handle) {
                        mech_handles.push_back(reinterpret_cast<std::uintptr_t>(&(*mit)));
                    }
                }
                for (std::uintptr_t mh : mech_handles) {
                    if (auto mw = mech_storage.try_acquire_write(mh)) {
                        mw->min_xyz = make_fvec3(aabb_min[0], aabb_min[1], aabb_min[2]);
                        mw->max_xyz = make_fvec3(aabb_max[0], aabb_max[1], aabb_max[2]);
                    }
                }
            }

            CFW_LOG_NOTICE("[GeometrySystem] Async import finished for geometry {} (rid={})",
                           geom_handle, rid);
        }
    }

    // ---- 阶段 2：为新的 PendingImport 发起 import_async（距离排序 + 每帧预算）----
    // 仅对尚无在途任务的 PendingImport geometry 发起，避免重复 import。
    // 近处对象先 import（流式体验），且每帧最多发起 kMaxImportsPerFrame 个，
    // 避免一次性把大量模型全压进 TBB 线程池造成内存/解析突发。
    struct ToImport {
        std::uintptr_t geom_handle;
        std::string    path;
        ktm::fvec3     world_pos;
    };
    std::vector<ToImport> to_import;
    for (auto it = geom_storage.cbegin(); it != geom_storage.cend(); ++it) {
        const GeometryDevice& geom_dev = *it;
        if (geom_dev.gpu_build_state != GeometryDevice::GpuBuildState::PendingImport) continue;
        auto geom_handle = reinterpret_cast<std::uintptr_t>(&geom_dev);
        if (impl_->pending_import_tasks.count(geom_handle)) continue;  // 已在途
        if (geom_dev.model_path_utf8.empty()) continue;

        ktm::fvec3 world_pos = make_fvec3(0.0f, 0.0f, 0.0f);
        if (geom_dev.transform_handle != 0) {
            if (auto tr = hub.model_transform_storage().try_acquire_read(geom_dev.transform_handle)) {
                world_pos = tr->position;
            }
        }
        to_import.push_back({geom_handle, geom_dev.model_path_utf8, world_pos});
    }
    if (to_import.empty()) return;

    // 按到最近相机的距离排序：近处先 import
    const std::vector<ktm::fvec3> cameras = collect_camera_positions();
    if (!cameras.empty()) {
        std::sort(to_import.begin(), to_import.end(),
                  [&](const ToImport& a, const ToImport& b) {
                      return nearest_camera_dist2(a.world_pos, cameras)
                           < nearest_camera_dist2(b.world_pos, cameras);
                  });
    }

    // 每帧发起预算：剩余的下帧继续（仍为 PendingImport，不丢失）
    constexpr size_t kMaxImportsPerFrame = 4;
    size_t launched = 0;
    for (auto& item : to_import) {
        if (launched >= kMaxImportsPerFrame) break;

        // 分配 epoch 并写入 GeometryDevice（防 slot 复用 ABA）。
        // 写锁内再校验仍为 PendingImport 且无 epoch，避免与并发状态变更竞争。
        const std::uint64_t epoch = impl_->next_import_epoch++;
        {
            auto geom_write = geom_storage.try_acquire_write(item.geom_handle);
            if (!geom_write.valid()) continue;  // 已销毁
            if (geom_write->gpu_build_state != GeometryDevice::GpuBuildState::PendingImport ||
                geom_write->import_epoch != 0) {
                continue;  // 状态已变 / 已有在途任务，跳过
            }
            geom_write->import_epoch = epoch;
        }

        impl_->pending_import_tasks[item.geom_handle] =
            Impl::PendingImportTask{epoch,
                                    resource_manager.import_async(Utils::utf8_to_path(item.path))};
        ++launched;
    }
}

void GeometrySystem::process_pending_geometry_builds() {
    auto& hub = SharedDataHub::instance();
    auto& resource_manager = Resource::ResourceManager::get_instance();
    auto& geom_storage = hub.geometry_storage();

    // ---- 阶段 1：只读收集待构建项 ----
    // 收集 gpu_build_state==PendingBuild 且 model_id 已就绪的 geometry。
    // 仅记录 (geom_handle, model_id, world_pos)，不在持有遍历期间做重活。
    struct PendingBuild {
        std::uintptr_t geom_handle;
        std::uint64_t  model_id;
        ktm::fvec3     world_pos;  // 用于按相机距离排序（近处先建）
    };
    std::vector<PendingBuild> pending;
    for (auto it = geom_storage.cbegin(); it != geom_storage.cend(); ++it) {
        const GeometryDevice& geom_dev = *it;
        if (geom_dev.gpu_build_state != GeometryDevice::GpuBuildState::PendingBuild) continue;
        if (!geom_dev.model_resource_handle) continue;

        std::uint64_t model_id = 0;
        if (auto model_res = hub.model_resource_storage().try_acquire_read(geom_dev.model_resource_handle)) {
            model_id = model_res->model_id;
        }
        if (model_id == 0) continue;  // import 尚未完成，下帧再试

        // 读取世界位置（transform 缺失时退化为原点，仍可构建、只是排序权重为 0）
        ktm::fvec3 world_pos = make_fvec3(0.0f, 0.0f, 0.0f);
        if (geom_dev.transform_handle != 0) {
            if (auto tr = hub.model_transform_storage().try_acquire_read(geom_dev.transform_handle)) {
                world_pos = tr->position;
            }
        }

        pending.push_back({reinterpret_cast<std::uintptr_t>(&geom_dev), model_id, world_pos});
    }
    if (pending.empty()) return;

    // ---- 按相机距离排序：近处对象先构建（流式加载体验）----
    const std::vector<ktm::fvec3> cameras = collect_camera_positions();
    if (!cameras.empty()) {
        std::sort(pending.begin(), pending.end(),
                  [&](const PendingBuild& a, const PendingBuild& b) {
                      return nearest_camera_dist2(a.world_pos, cameras)
                           < nearest_camera_dist2(b.world_pos, cameras);
                  });
    }

    // ---- 阶段 2：构建 GPU 资源（不持 storage 锁，仅写回时短暂加锁）----
    // 每帧预算：最多构建 kMaxBuildsPerFrame 个，剩余保持 PendingBuild 下帧继续。
    // 目的：一次性创建大量对象时，把 GPU buffer 创建的帧突刺摊平到多帧，
    // 避免单帧卡顿。预算为内部常量（"由底层自行决定"），无外部开关。
    constexpr size_t kMaxBuildsPerFrame = 4;
    size_t built = 0;
    for (const auto& item : pending) {
        if (built >= kMaxBuildsPerFrame) break;  // 本帧预算用尽，剩余下帧处理

        auto scene_read = resource_manager.acquire_read<Resource::Scene>(item.model_id);
        if (!scene_read.valid()) continue;  // 资源无效，下帧再试

        std::vector<MeshDevice> mesh_devices = build_mesh_devices_from_scene(*scene_read);

        // 先失效旧 LOD 缓存（新 mesh_handles 即将替换，旧条目指向已变更的缓冲）
        {
            std::unique_lock lod_lock(impl_->lod_cache_mutex);
            for (uint32_t i = 0; i < static_cast<uint32_t>(mesh_devices.size()); ++i) {
                impl_->lod_cache.erase(Impl::make_lod_key(item.geom_handle, i));
            }
        }

        // 写回 + TOCTOU 重校验：仅当仍为 PendingBuild 才接管（防止期间被其它路径改写）
        if (auto geom_write = hub.geometry_storage().try_acquire_write(item.geom_handle)) {
            if (geom_write->gpu_build_state == GeometryDevice::GpuBuildState::PendingBuild) {
                geom_write->mesh_handles = std::move(mesh_devices);
                geom_write->gpu_build_state = GeometryDevice::GpuBuildState::Ready;
                ++built;
                CFW_LOG_NOTICE("[GeometrySystem] Built pending GPU resources for geometry {}, {} mesh(es)",
                               item.geom_handle, geom_write->mesh_handles.size());
            }
        }
    }
}

void GeometrySystem::upload_lod_from_scene_data() {
    // LOD 由本系统内部决策，无外部配置开关。
    // 最大 LOD 级别数（含 LOD0 原始精度）为内部常量。
    constexpr int max_lod_levels = 4;

    auto& resource_manager = Resource::ResourceManager::get_instance();
    auto& hub = SharedDataHub::instance();
    auto& geom_storage = hub.geometry_storage();

    for (auto it = geom_storage.cbegin(); it != geom_storage.cend(); ++it) {
        const GeometryDevice& geom_dev = *it;
        auto geom_handle = reinterpret_cast<std::uintptr_t>(&geom_dev);
        if (!geom_dev.model_resource_handle) continue;

        // 通过 ModelResource 解析真正的 ResourceManager UID
        std::uint64_t model_id = 0;
        if (auto model_res = hub.model_resource_storage().try_acquire_read(geom_dev.model_resource_handle)) {
            model_id = model_res->model_id;
        }
        if (model_id == 0) continue;

        for (uint32_t mesh_idx = 0; mesh_idx < static_cast<uint32_t>(geom_dev.mesh_handles.size()); ++mesh_idx) {
            uint64_t lod_key = Impl::make_lod_key(geom_handle, mesh_idx);

            // 已有缓存且模型未变更则跳过（model_id 比较防止 slot 复用）
            {
                std::shared_lock lock(impl_->lod_cache_mutex);
                auto cache_it = impl_->lod_cache.find(lod_key);
                if (cache_it != impl_->lod_cache.end()
                    && cache_it->second.model_id == model_id)
                    continue;
            }

            // 从 ResourceManager 读取 Scene 数据
            auto scene_read = resource_manager.acquire_read<Resource::Scene>(model_id);
            if (!scene_read.valid()) continue;

            auto& scene = *scene_read;
            if (mesh_idx >= scene.data.meshes.size()) continue;

            auto& mesh = scene.data.meshes[mesh_idx];
            if (mesh.lod_levels.empty()) continue;

            // 创建缓存条目
            Impl::LODCacheEntry entry;
            entry.model_id = model_id;
            auto& mesh_dev = geom_dev.mesh_handles[mesh_idx];

            // LOD 0：复用现有的 GPU 缓冲
            LODMeshBuffers lod0;
            lod0.vertex_buffer    = mesh_dev.vertexBuffer;
            lod0.index_buffer     = mesh_dev.indexBuffer;
            lod0.vertex_storage   = mesh_dev.vertexStorageBuffer;
            lod0.index_storage    = mesh_dev.indexStorageBuffer;
            lod0.error            = 0.0f;
            lod0.screen_threshold = 1.0f;
            lod0.ready            = true;
            entry.levels.push_back(std::move(lod0));

            // 为 LOD 0 构建 BVH（三角形级空间索引）
            entry.per_level_bvh.push_back(build_triangle_bvh(mesh.vertices, mesh.indices));

            // LOD 1..N：从导入时 meshoptimizer 生成的数据创建 GPU 缓冲
            for (size_t lod_idx = 0; lod_idx < mesh.lod_levels.size() && lod_idx < static_cast<size_t>(max_lod_levels - 1); ++lod_idx) {
                auto& lod_data = mesh.lod_levels[lod_idx];
                if (lod_data.vertices.empty() || lod_data.indices.empty()) continue;

                LODMeshBuffers lod_buf;
                // LOD 索引保持 uint16（与 LOD0 一致），不转换为 uint32。
                // 之前转为 uint32 导致 GPU 索引缓冲格式与 pipeline 预期不匹配→渲染缺口。
                lod_buf.vertex_buffer    = make_geometry_buffer(lod_data.vertices, Horizon::BufferUsageFlags::TransferDst | Horizon::BufferUsageFlags::Vertex,     "geometry.lod_vertex");
                lod_buf.index_buffer     = make_geometry_buffer(lod_data.indices,  Horizon::BufferUsageFlags::TransferDst | Horizon::BufferUsageFlags::Index,      "geometry.lod_index");
                lod_buf.vertex_storage   = make_geometry_buffer(lod_data.vertices, Horizon::BufferUsageFlags::TransferSrc | Horizon::BufferUsageFlags::TransferDst | Horizon::BufferUsageFlags::Storage, "geometry.lod_vertex_storage");
                lod_buf.index_storage    = make_geometry_buffer(lod_data.indices,  Horizon::BufferUsageFlags::TransferSrc | Horizon::BufferUsageFlags::TransferDst | Horizon::BufferUsageFlags::Storage, "geometry.lod_index_storage");
                lod_buf.error            = lod_data.error;
                // 切换阈值采用按 LOD 序号的固定表，不用 error 反推值（1/(1+error*80)）：
                // 后者在 error 较大时阈值极小，只在物体缩得很小时才切入；且 error==0
                // 时阈值为 0 → 该级永不选中（死级）。固定表保证单调递减、行为可预测：
                //   LOD1 @ screen_ratio<=0.3, LOD2 @ <=0.12, LOD3 @ <=0.04
                // 即物体在屏幕上越小，使用越简化的网格。
                {
                    static constexpr float kFixedThresholds[] = {0.30f, 0.12f, 0.04f};
                    const size_t ti = entry.levels.size() - 1;  // 当前是第 (levels.size()) 级，下标从 LOD1=0 起
                    lod_buf.screen_threshold = (ti < std::size(kFixedThresholds))
                                                   ? kFixedThresholds[ti]
                                                   : 0.02f;
                }
                lod_buf.ready            = true;
                entry.levels.push_back(std::move(lod_buf));

                // 为该 LOD 级别构建 BVH
                entry.per_level_bvh.push_back(build_triangle_bvh(lod_data.vertices, lod_data.indices));
            }

            std::unique_lock lock(impl_->lod_cache_mutex);
            impl_->lod_cache.insert_or_assign(lod_key, std::move(entry));
        }
    }
}

}  // namespace Corona::Systems


