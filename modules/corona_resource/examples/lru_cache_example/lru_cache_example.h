#pragma once

/// @file lru_cache_example.h
/// @brief LRU Cache demo — 调用生产级 Corona::Cache API 的示例工具函数
///
/// 此前该文件包含一套独立的 MemoryCache / DiskCache / CacheManager 实现，
/// 现已移除。所有缓存操作直接使用 <corona/resource/cache/lru_cache.h>。

#include <cstddef>
#include <string>

/// 生成确定性测试数据（相同 key + length → 相同结果，用于写入后验证）
[[nodiscard]] std::string generate_deterministic_data(const std::string& key, size_t length);

/// 生成随机测试数据
[[nodiscard]] std::string generate_random_test_string(size_t length);