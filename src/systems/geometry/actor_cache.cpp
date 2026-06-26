/// @file actor_cache.cpp
/// @brief ActorCache 实现 + ActorSnapshot JSON 序列化

#include <corona/systems/geometry/actor_cache.h>

#include <corona/kernel/core/i_logger.h>

#include <nlohmann/json.hpp>

#include <sstream>

namespace Corona::Cache {

// ============================================================================
// ActorSnapshot JSON 序列化
// ============================================================================

std::string ActorSnapshot::to_json() const {
    nlohmann::json j;
    j["model_path"]     = model_path.string();
    j["pos_x"]          = position[0];
    j["pos_y"]          = position[1];
    j["pos_z"]          = position[2];
    j["rot_x"]          = euler_rotation[0];
    j["rot_y"]          = euler_rotation[1];
    j["rot_z"]          = euler_rotation[2];
    j["scl_x"]          = scale[0];
    j["scl_y"]          = scale[1];
    j["scl_z"]          = scale[2];
    j["follow_camera"]  = follow_camera;
    j["profile_count"]  = profile_count;
    return j.dump();
}

std::optional<ActorSnapshot> ActorSnapshot::from_json(const std::string& json) {
    try {
        nlohmann::json j = nlohmann::json::parse(json);
        ActorSnapshot snap;
        snap.model_path       = j.value("model_path", "");
        snap.position[0]      = j.value("pos_x", 0.0f);
        snap.position[1]      = j.value("pos_y", 0.0f);
        snap.position[2]      = j.value("pos_z", 0.0f);
        snap.euler_rotation[0] = j.value("rot_x", 0.0f);
        snap.euler_rotation[1] = j.value("rot_y", 0.0f);
        snap.euler_rotation[2] = j.value("rot_z", 0.0f);
        snap.scale[0]         = j.value("scl_x", 1.0f);
        snap.scale[1]         = j.value("scl_y", 1.0f);
        snap.scale[2]         = j.value("scl_z", 1.0f);
        snap.follow_camera    = j.value("follow_camera", false);
        snap.profile_count    = j.value("profile_count", 0);
        return snap;
    } catch (const nlohmann::json::exception& e) {
        CFW_LOG_ERROR("[ActorCache] Failed to parse ActorSnapshot JSON: {}", e.what());
        return std::nullopt;
    }
}

// ============================================================================
// ActorCache
// ============================================================================

ActorCache::ActorCache(size_t mem_capacity, size_t disk_capacity,
                       std::filesystem::path disk_dir)
    : cache_(mem_capacity, disk_capacity, std::move(disk_dir)) {}

std::string ActorCache::make_key(std::uintptr_t handle) {
    // 将指针地址格式化为 16 进制字符串
    std::ostringstream oss;
    oss << "actor_0x" << std::hex << handle;
    return oss.str();
}

std::uintptr_t ActorCache::parse_key(const std::string& key) {
    // 反向解析 make_key 产生的 key
    // 格式: "actor_0x<hex>"
    auto pos = key.find("0x");
    if (pos == std::string::npos) return 0;
    try {
        return static_cast<std::uintptr_t>(std::stoull(key.substr(pos + 2), nullptr, 16));
    } catch (...) {
        return 0;
    }
}

bool ActorCache::put(std::uintptr_t actor_handle, const ActorSnapshot& snapshot) {
    std::string key = make_key(actor_handle);
    std::string json = snapshot.to_json();
    CFW_LOG_NOTICE("[ActorCache] Storing actor 0x{:x} ({} bytes)", actor_handle, json.size());
    return cache_.put(key, json.data(), json.size());
}

std::optional<ActorSnapshot> ActorCache::get(std::uintptr_t actor_handle) {
    std::string key = make_key(actor_handle);
    auto item = cache_.get(key);
    if (!item) return std::nullopt;

    std::string json(item->data.data(), item->data.size());
    auto snap = ActorSnapshot::from_json(json);
    if (snap) {
        CFW_LOG_NOTICE("[ActorCache] Cache hit for actor 0x{:x}", actor_handle);
    }
    return snap;
}

void ActorCache::remove(std::uintptr_t actor_handle) {
    cache_.erase(make_key(actor_handle));
}

bool ActorCache::contains(std::uintptr_t actor_handle) {
    return cache_.contains(make_key(actor_handle));
}

size_t ActorCache::memory_used() const {
    return cache_.memory_used();
}

size_t ActorCache::memory_capacity() const {
    return cache_.memory_capacity();
}

size_t ActorCache::disk_used() {
    return cache_.disk_used();
}

size_t ActorCache::disk_capacity() const {
    return cache_.disk_capacity();
}

void ActorCache::set_evict_callback(std::function<void(std::uintptr_t, const std::string&)> cb) {
    cache_.set_evict_callback(
        [cb = std::move(cb)](const std::string& key, const std::vector<char>& data) {
            auto handle = parse_key(key);
            if (handle != 0 && cb) {
                std::string json(data.data(), data.size());
                cb(handle, json);
            }
        });
}

}  // namespace Corona::Cache