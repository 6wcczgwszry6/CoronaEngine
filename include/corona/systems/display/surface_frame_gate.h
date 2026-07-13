#pragma once

#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <utility>

namespace Corona::Systems::Detail {

/**
 * Coordinates frame snapshots with asynchronous surface retirement.
 *
 * retire() only invalidates the current generation. It never waits, so it is
 * safe to call from the synchronous EventBus handler. Display later waits on
 * the returned Retirement before destroying resources and acknowledging the
 * removal. A Lease keeps that acknowledgement pending while a frame is using
 * a snapshot that won the race immediately before retirement.
 */
class SurfaceFrameGate {
   private:
    struct Entry {
        std::mutex mutex;
        std::condition_variable quiescent;
        std::uint64_t generation = 0;
        std::size_t active_leases = 0;
        bool active = false;
        bool retired = false;
    };

   public:
    class Snapshot {
       public:
        Snapshot() = default;

       private:
        friend class SurfaceFrameGate;

        Snapshot(std::shared_ptr<Entry> entry, std::uint64_t generation)
            : entry_(std::move(entry)), generation_(generation) {}

        std::shared_ptr<Entry> entry_;
        std::uint64_t generation_ = 0;
    };

    class Lease {
       public:
        Lease() = default;
        Lease(const Lease&) = delete;
        Lease& operator=(const Lease&) = delete;

        Lease(Lease&& other) noexcept
            : entry_(std::exchange(other.entry_, {})) {}

        Lease& operator=(Lease&& other) noexcept {
            if (this != &other) {
                release();
                entry_ = std::exchange(other.entry_, {});
            }
            return *this;
        }

        ~Lease() {
            release();
        }

        [[nodiscard]] explicit operator bool() const noexcept {
            return entry_ != nullptr;
        }

       private:
        friend class SurfaceFrameGate;

        explicit Lease(std::shared_ptr<Entry> entry)
            : entry_(std::move(entry)) {}

        void release() noexcept {
            if (!entry_) {
                return;
            }

            auto entry = std::exchange(entry_, {});
            bool became_quiescent = false;
            {
                std::lock_guard lock(entry->mutex);
                if (entry->active_leases > 0) {
                    --entry->active_leases;
                    became_quiescent = entry->active_leases == 0;
                }
            }
            if (became_quiescent) {
                entry->quiescent.notify_all();
            }
        }

        std::shared_ptr<Entry> entry_;
    };

    class Retirement {
       public:
        Retirement() = default;

        void wait() const {
            wait([]() {});
        }

        template <typename WaitEntered>
        void wait(WaitEntered&& wait_entered) const {
            if (!entry_) {
                return;
            }
            std::unique_lock lock(entry_->mutex);
            if (entry_->active_leases != 0) {
                // The hook runs with the entry locked immediately before the
                // condition-variable wait. Tests can therefore prove teardown
                // has reached the real quiescence barrier without sleeping.
                std::invoke(std::forward<WaitEntered>(wait_entered));
            }
            entry_->quiescent.wait(
                lock, [this]() { return entry_->active_leases == 0; });
        }

       private:
        friend class SurfaceFrameGate;

        explicit Retirement(std::shared_ptr<Entry> entry)
            : entry_(std::move(entry)) {}

        std::shared_ptr<Entry> entry_;
    };

    /** Activates a new surface or accepts a duplicate registration. */
    [[nodiscard]] bool activate(std::uint64_t surface_id) {
        std::lock_guard registry_lock(registry_mutex_);
        auto it = entries_.find(surface_id);
        if (it == entries_.end()) {
            it = entries_
                     .emplace(surface_id, std::make_shared<Entry>())
                     .first;
        }

        auto& entry = it->second;
        std::lock_guard entry_lock(entry->mutex);
        if (entry->retired) {
            return false;
        }
        if (!entry->active) {
            ++entry->generation;
            entry->active = true;
        }
        return true;
    }

    /** Captures the generation represented by Display's copied frame state. */
    [[nodiscard]] Snapshot capture(std::uint64_t surface_id) const {
        std::shared_ptr<Entry> entry;
        {
            std::lock_guard registry_lock(registry_mutex_);
            const auto it = entries_.find(surface_id);
            if (it == entries_.end()) {
                return {};
            }
            entry = it->second;
        }

        std::lock_guard entry_lock(entry->mutex);
        if (!entry->active) {
            return {};
        }
        const auto generation = entry->generation;
        return Snapshot{std::move(entry), generation};
    }

    /** Acquires frame use only if the captured generation remains active. */
    [[nodiscard]] Lease try_acquire(const Snapshot& snapshot) const {
        if (!snapshot.entry_) {
            return {};
        }

        std::lock_guard entry_lock(snapshot.entry_->mutex);
        if (!snapshot.entry_->active ||
            snapshot.entry_->generation != snapshot.generation_) {
            return {};
        }
        ++snapshot.entry_->active_leases;
        return Lease{snapshot.entry_};
    }

    /** Invalidates snapshots immediately and returns a non-waiting teardown token. */
    [[nodiscard]] Retirement retire(std::uint64_t surface_id) {
        std::lock_guard registry_lock(registry_mutex_);
        auto it = entries_.find(surface_id);
        if (it == entries_.end()) {
            it = entries_
                     .emplace(surface_id, std::make_shared<Entry>())
                     .first;
        }

        auto& entry = it->second;
        {
            std::lock_guard entry_lock(entry->mutex);
            if (entry->active) {
                entry->active = false;
                ++entry->generation;
            }
            entry->retired = true;
        }
        return Retirement{entry};
    }

    /** Removes a quiescent retired entry after its resources are destroyed. */
    void forget(std::uint64_t surface_id) {
        std::lock_guard registry_lock(registry_mutex_);
        const auto it = entries_.find(surface_id);
        if (it == entries_.end()) {
            return;
        }

        const auto entry = it->second;
        std::lock_guard entry_lock(entry->mutex);
        if (entry->retired && entry->active_leases == 0) {
            entries_.erase(it);
        }
    }

   private:
    mutable std::mutex registry_mutex_;
    std::unordered_map<std::uint64_t, std::shared_ptr<Entry>> entries_;
};

}  // namespace Corona::Systems::Detail
