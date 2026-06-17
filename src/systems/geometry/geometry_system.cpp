#include <corona/events/engine_events.h>
#include <corona/kernel/core/i_logger.h>
#include <corona/shared_data_hub.h>
#include <corona/kernel/utils/storage.h>
#include <corona/spatial/octree.h>
#include <corona/systems/geometry/geometry_system.h>
#include <corona/utils/path_utils.h>
#include <ktm/ktm.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <mutex>
#include <shared_mutex>
#include <unordered_map>
#include <unordered_set>
#include <filesystem>
#include <future>

#include <corona/resource/resource.h>
#include <corona/resource/resource_manager.h>
#include <corona/resource/types/scene.h>

#include "geometry_internal.h"

namespace Corona::Systems {

using namespace GeometryInternal;

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
        auto id1 = ctx->event_bus()->subscribe<Events::ActorLoadCompletedEvent>(
            [this](const Events::ActorLoadCompletedEvent& e) {
                this->on_load_completed(e);
            });
        auto id2 = ctx->event_bus()->subscribe<Events::ActorUnloadCompletedEvent>(
           [this](const Events::ActorUnloadCompletedEvent& e) {
               this->on_unload_completed(e);
           });
        auto id3 = ctx->event_bus()->subscribe<Events::ActorLoadRequestedEvent>(
            [this](const Events::ActorLoadRequestedEvent& e) {
                this->on_load_requested(e);
            });
        auto id4 = ctx->event_bus()->subscribe<Events::ActorUnloadRequestedEvent>(
            [this](const Events::ActorUnloadRequestedEvent& e) {
                this->on_unload_requested(e);
            });

        impl_->event_subscriptions = {id1,id2,id3,id4};
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

    // ---- 动态减面管线 ----
    if (impl_->simplification_cfg.enabled) {
        upload_lod_from_scene_data();
    }

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
        {
            std::unique_lock lock(impl_->mtx);
            auto& scene_state = impl_->get_or_create(scene_handle);
            const ActorLoadState initial_state = scene_state.cfg.enable_distance_culling
                                                     ? ActorLoadState::Unloaded
                                                     : ActorLoadState::Loaded;
            for (auto actor_handle : added_actors) {
                scene_state.actor_load_states.try_emplace(actor_handle, initial_state);
            }
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

// ============================================================================
// 私有事件处理
// ============================================================================

void GeometrySystem::on_load_completed(const Events::ActorLoadCompletedEvent& event) {
    ActorLoadState old_state = ActorLoadState::Unloaded;
    {
        std::unique_lock lock(impl_->mtx);
        auto scene_it = impl_->scenes.find(event.scene);
        if (scene_it != impl_->scenes.end()) {
            auto& state_map = scene_it->second.actor_load_states;
            auto actor_it = state_map.find(event.actor);
            if (actor_it != state_map.end() && actor_it->second == ActorLoadState::Loading) {
                old_state = actor_it->second;
                actor_it->second = ActorLoadState::Loaded;
                impl_->offline_actors[event.actor] = false;
            }
        }
    } // 释放锁后发布事件
    if (old_state == ActorLoadState::Loading) {
        CFW_LOG_NOTICE("GeometrySystem: Actor {} (scene: {}) load completed", event.actor, event.scene);
        impl_->ctx->event_bus()->publish(event);
    }
}

void GeometrySystem::on_unload_completed(const Events::ActorUnloadCompletedEvent& event) {
    ActorLoadState old_state = ActorLoadState::Loaded;
    {
        std::unique_lock lock(impl_->mtx);
        auto scene_it = impl_->scenes.find(event.scene);
        if (scene_it == impl_->scenes.end()) return;

        auto& state_map = scene_it->second.actor_load_states;
        auto actor_it = state_map.find(event.actor);
        if (actor_it != state_map.end() && actor_it->second == ActorLoadState::Unloading) {
            old_state = actor_it->second;
            actor_it->second = ActorLoadState::Unloaded;
            impl_->offline_actors[event.actor] = false;
        }
    }
    if (old_state == ActorLoadState::Unloading) {
        CFW_LOG_NOTICE("GeometrySystem: Actor {} (scene: {}) unload completed", event.actor, event.scene);
        impl_->ctx->event_bus()->publish(event);
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
        if (task.rid != Resource::IResource::INVALID_UID) {
            impl_->ctx->event_bus()->publish(Events::ActorLoadCompletedEvent{task.scene_handle,task.actor});
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
            impl_->ctx->event_bus()->publish(Events::ActorUnloadCompletedEvent{task.scene_handle, task.actor});
        }
    }

    std::vector<CompletedUnloadTask> failed_unloads;
    for (const auto& task : completed_unloads) {
        if (task.success) {
            {
                std::unique_lock lock(impl_->mtx);
                auto scene_it = impl_->scenes.find(task.scene_handle);
                if (scene_it != impl_->scenes.end()) {
                    scene_it->second.unload_retry_counts.erase(task.actor);
                }
            }
            impl_->ctx->event_bus()->publish(Events::ActorUnloadCompletedEvent{task.scene_handle, task.actor});
            CFW_LOG_DEBUG("[SceneSystem] Actor {} unloaded", task.actor);
        } else {
            // 卸载失败，保存到列表中后续处理重试
            failed_unloads.push_back(task);
        }
    }

    //卸载失败重试
    if (!failed_unloads.empty()) {
        std::vector<Events::ActorUnloadCompletedEvent> deferred_events;
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
                    CFW_LOG_ERROR("[SceneSystem] Actor 0x%lx unload failed after 10 retries, resource is permanently in use",
                                 (unsigned long)task.actor);
                    scene_state.unload_retry_counts.erase(task.actor);
                    // 不强制设为Loaded，保留Unloading状态，由业务层处理
                    // 同时不发布任何事件，避免状态混乱
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
                        }
                    } else {
                        CFW_LOG_WARNING("[SceneSystem] Actor 0x%lx handle invalid, clean up all states",
                                       (unsigned long)task.actor);
                        scene_state.unload_retry_counts.erase(task.actor);
                        scene_state.actor_load_states.erase(task.actor);
                        impl_->offline_actors.erase(task.actor);
                    }
                }
            }
        }
        for (const auto& evt : deferred_events) {
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
        impl_->ctx->event_bus()->publish(Events::ActorUnloadCompletedEvent{e.scene,e.actor});
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
        if (scene_state.unloading_tasks.count(e.actor)) {
            scene_state.unloading_tasks.erase(e.actor);
            scene_state.unload_retry_counts.erase(e.actor);
            scene_state.actor_load_states[e.actor] = ActorLoadState::Loaded;
            CFW_LOG_NOTICE("[GeometrySystem] Cancelled pending unload for actor {}", e.actor);
        }

        return;
    }

    auto& actor_storage = SharedDataHub::instance().actor_storage();
    auto actor_read = actor_storage.try_acquire_read(e.actor);
    if (!actor_read.valid() || actor_read->model_path.empty()) {
        scene_state.actor_load_states[e.actor] = ActorLoadState::Unloaded;
        lock.unlock();
        impl_->ctx->event_bus()->publish(Events::ActorUnloadCompletedEvent{e.scene, e.actor});
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
// 动态减面 (Mesh Simplification) 公共 API
// ============================================================================

void GeometrySystem::set_simplification_config(const MeshSimplificationConfig& cfg) {
    impl_->simplification_cfg = cfg;
}

const MeshSimplificationConfig& GeometrySystem::get_simplification_config() const {
    return impl_->simplification_cfg;
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
// 动态减面内部管线
// ============================================================================

void GeometrySystem::upload_lod_from_scene_data() {
    if (!impl_->simplification_cfg.auto_on_load) return;

    auto& resource_manager = Resource::ResourceManager::get_instance();
    auto& geom_storage = SharedDataHub::instance().geometry_storage();

    for (auto it = geom_storage.cbegin(); it != geom_storage.cend(); ++it) {
        const GeometryDevice& geom_dev = *it;
        auto geom_handle = reinterpret_cast<std::uintptr_t>(&geom_dev);
        if (!geom_dev.model_resource_handle) continue;

        for (uint32_t mesh_idx = 0; mesh_idx < static_cast<uint32_t>(geom_dev.mesh_handles.size()); ++mesh_idx) {
            uint64_t lod_key = Impl::make_lod_key(geom_handle, mesh_idx);

            // 已有缓存且模型未变更则跳过（model_resource_handle 比较防止 slot 复用）
            {
                std::shared_lock lock(impl_->lod_cache_mutex);
                auto cache_it = impl_->lod_cache.find(lod_key);
                if (cache_it != impl_->lod_cache.end()
                    && cache_it->second.model_resource_handle == geom_dev.model_resource_handle)
                    continue;
            }

            // 从 ResourceManager 读取 Scene 数据
            auto scene_read = resource_manager.acquire_read<Resource::Scene>(geom_dev.model_resource_handle);
            if (!scene_read.valid()) continue;

            auto& scene = *scene_read;
            if (mesh_idx >= scene.data.meshes.size()) continue;

            auto& mesh = scene.data.meshes[mesh_idx];
            if (mesh.lod_levels.empty()) continue;

            // 创建缓存条目
            Impl::LODCacheEntry entry;
            entry.model_resource_handle = geom_dev.model_resource_handle;
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

            // LOD 1..N：从导入时 meshoptimizer 生成的数据创建 GPU 缓冲
            for (size_t lod_idx = 0; lod_idx < mesh.lod_levels.size() && lod_idx < static_cast<size_t>(impl_->simplification_cfg.max_lod_levels - 1); ++lod_idx) {
                auto& lod_data = mesh.lod_levels[lod_idx];
                if (lod_data.vertices.empty() || lod_data.indices.empty()) continue;

                LODMeshBuffers lod_buf;
                // 转换为 uint32 索引（meshopt 输出 uint16，GPU 需要 uint32）
                std::vector<uint32_t> indices32;
                indices32.reserve(lod_data.indices.size());
                for (auto idx : lod_data.indices) indices32.push_back(static_cast<uint32_t>(idx));

                lod_buf.vertex_buffer    = HardwareBuffer(lod_data.vertices, BufferUsage::VertexBuffer);
                lod_buf.index_buffer     = HardwareBuffer(indices32,        BufferUsage::IndexBuffer);
                lod_buf.vertex_storage   = HardwareBuffer(lod_data.vertices, BufferUsage::StorageBuffer);
                lod_buf.index_storage    = HardwareBuffer(indices32,        BufferUsage::StorageBuffer);
                lod_buf.error            = lod_data.error;
                lod_buf.screen_threshold = lod_data.screen_threshold;
                lod_buf.ready            = true;
                entry.levels.push_back(std::move(lod_buf));
            }

            std::unique_lock lock(impl_->lod_cache_mutex);
            impl_->lod_cache.insert_or_assign(lod_key, std::move(entry));
        }
    }
}

}  // namespace Corona::Systems


