#pragma once

/// @file actor_cache.h
/// @brief ActorCache — 类型化 Actor 快照缓存，封装两级 LRU CacheManager
///
/// ActorSnapshot 包含重建 actor 所需的最小信息集：
/// - model_path（资源文件路径，也是 ResourceManager 的 key）
/// - transform（position / euler_rotation / scale）
/// - follow_camera flag
///
/// 注意：mesh / texture 等重资源由 ResourceManager 自行管理；
///       ActorSnapshot 只存资源路径，不重复序列化几何数据。

#include <corona/resource/cache/lru_cache.h>

#include <cstdint>
#include <filesystem>
#include <functional>
#include <optional>
#include <string>

namespace Corona::Cache {

// ============================================================================
// ActorSnapshot — 重建 actor 所需的最小数据
// ============================================================================

struct ActorSnapshot {
    std::filesystem::path model_path;          // 模型文件路径（ResourceManager key）
    float position[3]        = {0, 0, 0};      // world position
    float euler_rotation[3]  = {0, 0, 0};      // euler angles (radians)
    float scale[3]           = {1, 1, 1};      // world scale
    bool  follow_camera      = false;           // camera-local 渲染模式
    int   profile_count      = 0;               // profile 数量（仅用于验证）

    /// JSON 序列化
    [[nodiscard]] std::string to_json() const;
    [[nodiscard]] static std::optional<ActorSnapshot> from_json(const std::string& json);
};

// ============================================================================
// ActorCache — 类型化 actor 缓存
// ============================================================================

class ActorCache {
public:
    /// @param mem_capacity  内存缓存容量（字节），默认 64 MB
    /// @param disk_capacity 磁盘缓存容量（字节），0 = 仅内存
    /// @param disk_dir      磁盘缓存目录
    ActorCache(size_t mem_capacity, size_t disk_capacity,
               std::filesystem::path disk_dir);

    ~ActorCache() = default;

    ActorCache(const ActorCache&) = delete;
    ActorCache& operator=(const ActorCache&) = delete;

    // ---- 核心 API ----

    /// 存入 actor 快照
    bool put(std::uintptr_t actor_handle, const ActorSnapshot& snapshot);

    /// 获取 actor 快照
    std::optional<ActorSnapshot> get(std::uintptr_t actor_handle);

    /// 移除 actor 缓存项
    void remove(std::uintptr_t actor_handle);

    /// 检查 actor 是否在缓存中
    [[nodiscard]] bool contains(std::uintptr_t actor_handle);

    // ---- 容量查询 ----
    [[nodiscard]] size_t memory_used() const;
    [[nodiscard]] size_t memory_capacity() const;
    [[nodiscard]] size_t disk_used();
    [[nodiscard]] size_t disk_capacity() const;

    // ---- 淘汰回调 ----
    /// 设置淘汰回调：当 actor 快照被从 LRU 中淘汰时调用
    void set_evict_callback(std::function<void(std::uintptr_t, const std::string&)> cb);

private:
    CacheManager cache_;

    [[nodiscard]] static std::string make_key(std::uintptr_t handle);
    [[nodiscard]] static std::uintptr_t parse_key(const std::string& key);
};

}  // namespace Corona::Cache
