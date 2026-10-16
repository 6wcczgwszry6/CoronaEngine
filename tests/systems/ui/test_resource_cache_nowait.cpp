#include <corona/resource/resource.h>
#include <corona/resource/resource_cache.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <shared_mutex>
#include <thread>

namespace {

void require(bool condition, const char* message) {
    if (condition) return;
    std::fprintf(stderr, "FAILED: %s\n", message);
    std::fflush(stderr);
    std::exit(1);
}

}  // namespace

// The editor UI thread paints the editor and dispatches its input, so any read it
// performs must be bounded.  A loader holds a resource entry's lock across the
// whole import (seconds for a large model), and a blocking read there is what froze
// the editor permanently.  This pins the best-effort contract: a busy entry yields
// no handle immediately instead of waiting.
int main() {
    using Corona::Resource::LoadState;
    using Corona::Resource::ResourceCache;
    using Corona::Resource::TResourceID;

    ResourceCache cache;
    const TResourceID rid = 4242;
    auto [entry, created] = cache.get_or_create_entry(rid);
    require(static_cast<bool>(entry), "entry must be created");
    entry->state = LoadState::Ready;

    std::thread loader([&entry] {
        std::unique_lock<std::shared_mutex> lock(entry->mutex);
        std::this_thread::sleep_for(std::chrono::milliseconds(400));
    });
    std::this_thread::sleep_for(std::chrono::milliseconds(60));

    const auto started = std::chrono::steady_clock::now();
    auto handle = cache.try_acquire_read_nowait(rid);
    const auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                                std::chrono::steady_clock::now() - started)
                                .count();
    loader.join();

    require(elapsed_ms < 100, "best-effort read waited for a busy entry");
    require(!handle.valid(), "a busy entry must not hand out a handle");

    require(!cache.try_acquire_read_nowait(rid + 1).valid(),
            "an unknown resource must not hand out a handle");
    return 0;
}
