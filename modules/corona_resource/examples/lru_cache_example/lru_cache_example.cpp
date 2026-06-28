/// @file lru_cache_example.cpp
/// @brief LRU Cache demo 工具函数实现
///
/// 所有缓存操作由生产模块 <corona/resource/cache/lru_cache.h> 提供，
/// 此文件仅包含 demo 所需的测试数据生成工具。

#include "lru_cache_example.h"

#include <random>
#include <string>

[[nodiscard]] std::string generate_deterministic_data(const std::string& key, size_t length) {
    const std::string chars =
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    std::seed_seq seed(key.begin(), key.end());
    std::mt19937 gen(seed);
    std::uniform_int_distribution<> dis(0, static_cast<int>(chars.size()) - 1);

    std::string result;
    result.reserve(length);
    for (size_t i = 0; i < length; ++i) {
        result += chars[dis(gen)];
    }
    return result;
}

[[nodiscard]] std::string generate_random_test_string(size_t length) {
    const std::string chars =
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    thread_local std::mt19937 gen(std::random_device{}());
    std::uniform_int_distribution<> dis(0, static_cast<int>(chars.size()) - 1);

    std::string result;
    result.reserve(length);
    for (size_t i = 0; i < length; ++i) {
        result += chars[dis(gen)];
    }
    return result;
}