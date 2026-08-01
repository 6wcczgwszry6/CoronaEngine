#pragma once

#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <optional>
#include <thread>
#include <unordered_set>

namespace Corona::Systems::OpticsDetail {

class ActorPickReadbackWorker {
public:
    class Reservation {
    public:
        Reservation() = default;
        Reservation(const Reservation&) = delete;
        Reservation& operator=(const Reservation&) = delete;
        Reservation(Reservation&& other) noexcept;
        Reservation& operator=(Reservation&& other) noexcept;
        ~Reservation();

    private:
        friend class ActorPickReadbackWorker;
        Reservation(ActorPickReadbackWorker* owner, std::uint64_t id) noexcept;
        void reset() noexcept;

        ActorPickReadbackWorker* owner_{nullptr};
        std::uint64_t id_{0};
    };

    using Work = std::function<void()>;

    explicit ActorPickReadbackWorker(std::size_t capacity = 64);
    ActorPickReadbackWorker(const ActorPickReadbackWorker&) = delete;
    ActorPickReadbackWorker& operator=(const ActorPickReadbackWorker&) = delete;
    ~ActorPickReadbackWorker();

    void start();
    [[nodiscard]] std::optional<Reservation> reserve();
    [[nodiscard]] bool submit(Reservation&& reservation, Work work);
    void shutdown();

    [[nodiscard]] std::size_t pending_count() const noexcept;

private:
    void cancel(std::uint64_t id) noexcept;
    void run();

    const std::size_t capacity_;
    mutable std::mutex mutex_;
    std::condition_variable work_available_;
    std::deque<Work> work_;
    std::unordered_set<std::uint64_t> reservations_;
    std::thread thread_;
    std::uint64_t next_reservation_id_{1};
    std::size_t occupied_{0};
    bool accepting_{false};
    bool stopping_{false};
};

}  // namespace Corona::Systems::OpticsDetail
