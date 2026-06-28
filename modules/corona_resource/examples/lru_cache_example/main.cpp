/// @file main.cpp
/// @brief LRU Cache Demo — 演示两级缓存（内存 + 磁盘）的生产 API 使用
///
/// 所有缓存类来自 <corona/resource/cache/lru_cache.h>：
///   Corona::Cache::CacheManager  — 两级缓存管理器
///   Corona::Cache::MemoryCache   — 纯内存 LRU
///   Corona::Cache::DiskCache     — 磁盘 LRU
///
/// 此前此处包含独立实现的 CacheRecord / MemoryCache / DiskCache / CacheManager，
/// 现已全部替换为生产 API 调用。

#include <atomic>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <random>
#include <thread>
#include <vector>

#include <corona/resource/cache/lru_cache.h>

#include "lru_cache_example.h"

using namespace Corona::Cache;

// ============================================================================
// 多线程写入测试
// ============================================================================
void thread_write_worker(CacheManager& cache, int thread_id, int num_items,
                         size_t data_size, std::atomic<int>& success_count,
                         std::atomic<int>& fail_count) {
    for (int i = 0; i < num_items; ++i) {
        std::string key =
            "thread_" + std::to_string(thread_id) + "_item_" + std::to_string(i);
        std::string data = generate_deterministic_data(key, data_size);

        bool success = cache.put(key, data.data(), data.size());
        if (success) {
            success_count++;
        } else {
            fail_count++;
            std::cerr << "Thread " << thread_id << " failed to put item: " << key
                      << std::endl;
        }
    }
}

// ============================================================================
// 多线程读取测试（验证数据完整性）
// ============================================================================
void thread_read_worker(CacheManager& cache, int thread_id, int num_items,
                        std::atomic<int>& hit_count, std::atomic<int>& miss_count,
                        std::atomic<int>& corrupt_count) {
    for (int i = 0; i < num_items; ++i) {
        std::string key =
            "thread_" + std::to_string(thread_id) + "_item_" + std::to_string(i);
        auto item_opt = cache.get(key);

        if (item_opt) {
            std::string read_data(item_opt->data.begin(), item_opt->data.end());
            std::string expected_data =
                generate_deterministic_data(key, item_opt->data_size);

            if (read_data == expected_data) {
                hit_count++;
            } else {
                corrupt_count++;
                std::cerr << "Thread " << thread_id << " data corrupted for: " << key
                          << std::endl;
            }
        } else {
            miss_count++;
        }
    }
}

// ============================================================================
// 磁盘缓存淘汰测试
// ============================================================================
void test_disk_eviction(CacheManager& cache) {
    std::cout << "\n=== Testing Disk Cache Eviction ===" << std::endl;

    const size_t data_size = 1024 * 512;  // 512KB per item
    const int num_items = 25;  // 25 * 512KB = 12.5MB > 10MB disk capacity

    for (int i = 0; i < num_items; ++i) {
        std::string key = "disk_evict_item_" + std::to_string(i);
        std::string data = generate_random_test_string(data_size);

        bool success = cache.put(key, data.data(), data.size());
        std::cout << "Put disk item " << i << ": " << (success ? "OK" : "FAILED")
                  << "  cache_used_memory:" << cache.memory_used() / 1024
                  << "KB    disk_used_memory:" << cache.disk_used() / 1024 << "KB"
                  << std::endl;
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }

    // 验证最早写入的 key 是否被淘汰
    std::string oldest_key = "disk_evict_item_0";
    auto item_opt = cache.get(oldest_key);
    if (!item_opt) {
        std::cout << "Oldest disk item (" << oldest_key
                  << ") evicted as expected" << std::endl;
    } else {
        std::cout << "ERROR: Oldest disk item (" << oldest_key
                  << ") still exists!" << std::endl;
    }

    // 验证最新写入的 key 是否存在
    std::string newest_key = "disk_evict_item_" + std::to_string(num_items - 1);
    item_opt = cache.get(newest_key);
    if (item_opt) {
        std::cout << "Newest disk item (" << newest_key
                  << ") exists as expected" << std::endl;
    } else {
        std::cout << "ERROR: Newest disk item (" << newest_key
                  << ") missing!" << std::endl;
    }
}

// ============================================================================
// 磁盘持久化测试
// ============================================================================
void test_persistence(const std::string& cache_dir) {
    std::cout << "\n=== Testing Disk Persistence ===" << std::endl;

    constexpr size_t memory_capacity = 1024 * 1024;
    constexpr size_t disk_capacity = 10 * 1024 * 1024;
    CacheManager new_cache(memory_capacity, disk_capacity, cache_dir);

    std::string test_key = "disk_evict_item_20";
    auto item_opt = new_cache.get(test_key);
    if (item_opt) {
        std::cout << "Persistent data (" << test_key
                  << ") loaded from disk successfully" << std::endl;
    } else {
        std::cout << "ERROR: Persistent data (" << test_key
                  << ") not found on disk!" << std::endl;
    }
}

// ============================================================================
// Pin / Unpin 测试（生产 API 新增功能）
// ============================================================================
void test_pin_unpin(CacheManager& cache) {
    std::cout << "\n=== Testing Pin / Unpin ===" << std::endl;

    // 存入一个固定项
    const std::string pinned_key = "pinned_item";
    std::string data = generate_random_test_string(512 * 1024);  // 512KB
    cache.put(pinned_key, data.data(), data.size());

    // Pin it
    bool pinned = cache.pin(pinned_key);
    std::cout << "Pin '" << pinned_key << "': " << (pinned ? "OK" : "FAILED")
              << std::endl;

    // 填满内存试图触发淘汰
    bool pinned_survived = true;
    for (int i = 0; i < 10; ++i) {
        std::string key = "filler_" + std::to_string(i);
        std::string fill = generate_random_test_string(200 * 1024);  // 200KB each
        cache.put(key, fill.data(), fill.size());
    }

    // 检查 pinned item 是否还在
    auto pinned_item = cache.get(pinned_key);
    if (pinned_item) {
        std::cout << "Pinned item survived eviction pressure: OK" << std::endl;
    } else {
        std::cout << "ERROR: Pinned item was evicted!" << std::endl;
        pinned_survived = false;
    }

    // Unpin
    cache.unpin(pinned_key);
    std::cout << "Unpin '" << pinned_key << "': OK" << std::endl;
}

// ============================================================================
// Touch 测试（生产 API 新增功能）
// ============================================================================
void test_touch(CacheManager& cache) {
    std::cout << "\n=== Testing Touch ===" << std::endl;

    std::string key = "touch_test_item";
    std::string data = generate_random_test_string(100 * 1024);
    cache.put(key, data.data(), data.size());

    // touch 比 get 更轻量 — 只更新访问时间，不返回数据
    bool touched = cache.touch(key);
    std::cout << "Touch '" << key << "': " << (touched ? "OK" : "FAILED")
              << std::endl;

    // 验证数据仍在
    auto item = cache.get(key);
    if (item) {
        std::cout << "Data accessible after touch: OK (" << item->data_size
                  << " bytes)" << std::endl;
    } else {
        std::cout << "ERROR: Data lost after touch!" << std::endl;
    }
}

// ============================================================================
// 淘汰回调测试（生产 API 新增功能）
// ============================================================================
void test_evict_callback() {
    std::cout << "\n=== Testing Evict Callback ===" << std::endl;

    // 仅内存缓存（无磁盘），触发回调
    CacheManager mem_only_cache(256 * 1024, 0, "");  // 256KB memory, no disk

    std::atomic<int> evict_count{0};
    mem_only_cache.set_evict_callback(
        [&](const std::string& key, const std::vector<char>& data) {
            evict_count++;
            std::cout << "  Evict callback: key=" << key
                      << ", size=" << data.size() << " bytes" << std::endl;
        });

    // 填入超过容量的数据
    for (int i = 0; i < 5; ++i) {
        std::string key = "evict_cb_test_" + std::to_string(i);
        std::string data = generate_random_test_string(100 * 1024);  // 100KB each
        mem_only_cache.put(key, data.data(), data.size());
    }

    std::cout << "Evict callback invoked " << evict_count << " times" << std::endl;
    if (evict_count > 0) {
        std::cout << "Evict callback working: OK" << std::endl;
    } else {
        std::cout << "WARNING: No eviction occurred (all items fit in memory)"
                  << std::endl;
    }
}

// ============================================================================
// 主函数
// ============================================================================
int main() {
    constexpr size_t memory_capacity = 1024 * 1024;       // 1MB 内存缓存
    constexpr size_t disk_capacity = 10 * 1024 * 1024;    // 10MB 磁盘缓存
    const std::string cache_dir = "./cache_dir";

    // ---- 使用生产级 CacheManager ----
    CacheManager cache_manager(memory_capacity, disk_capacity, cache_dir);

    // ========== 多线程并发测试 ==========
    std::cout << "\n=== Multi-thread Concurrent Test ===" << std::endl;
    const int num_threads = 4;
    const int items_per_thread = 50;
    const size_t data_size_per_item = 1024;  // 1KB

    std::atomic<int> write_success_count(0);
    std::atomic<int> write_fail_count(0);
    std::atomic<int> read_hit_count(0);
    std::atomic<int> read_miss_count(0);
    std::atomic<int> read_corrupt_count(0);

    // 启动写入线程
    std::vector<std::thread> write_threads;
    auto start_time = std::chrono::high_resolution_clock::now();

    for (int i = 0; i < num_threads; ++i) {
        write_threads.emplace_back(thread_write_worker, std::ref(cache_manager),
                                   i, items_per_thread, data_size_per_item,
                                   std::ref(write_success_count),
                                   std::ref(write_fail_count));
    }
    for (auto& t : write_threads) { t.join(); }

    // 启动读取线程
    std::vector<std::thread> read_threads;
    for (int i = 0; i < num_threads; ++i) {
        read_threads.emplace_back(thread_read_worker, std::ref(cache_manager),
                                  i, items_per_thread,
                                  std::ref(read_hit_count),
                                  std::ref(read_miss_count),
                                  std::ref(read_corrupt_count));
    }
    for (auto& t : read_threads) { t.join(); }

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time);

    std::cout << "Total write attempts: " << num_threads * items_per_thread
              << std::endl;
    std::cout << "Write successes: " << write_success_count << std::endl;
    std::cout << "Write failures: " << write_fail_count << std::endl;
    std::cout << "Read hits: " << read_hit_count << std::endl;
    std::cout << "Read misses: " << read_miss_count << std::endl;
    std::cout << "Read corruptions: " << read_corrupt_count << std::endl;
    std::cout << "Total time: " << duration.count() << " ms" << std::endl;

    // ========== 磁盘缓存淘汰测试 ==========
    test_disk_eviction(cache_manager);

    // ========== 磁盘持久化测试 ==========
    test_persistence(cache_dir);

    // ========== 生产 API 新功能测试 ==========
    test_pin_unpin(cache_manager);
    test_touch(cache_manager);
    test_evict_callback();

    std::cout << "\n=== All demos completed ===" << std::endl;

    // 清理测试缓存目录
    std::error_code ec;
    std::filesystem::remove_all(cache_dir, ec);

    return 0;
}