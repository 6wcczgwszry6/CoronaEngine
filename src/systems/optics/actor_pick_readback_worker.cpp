#include <corona/systems/optics/actor_pick_readback_worker.h>

#include <utility>

namespace Corona::Systems::OpticsDetail {

ActorPickReadbackWorker::Reservation::Reservation(ActorPickReadbackWorker* owner,
                                                  std::uint64_t id) noexcept
    : owner_(owner), id_(id) {}

ActorPickReadbackWorker::Reservation::Reservation(Reservation&& other) noexcept
    : owner_(std::exchange(other.owner_, nullptr)), id_(std::exchange(other.id_, 0)) {}

ActorPickReadbackWorker::Reservation& ActorPickReadbackWorker::Reservation::operator=(
    Reservation&& other) noexcept {
    if (this != &other) {
        reset();
        owner_ = std::exchange(other.owner_, nullptr);
        id_ = std::exchange(other.id_, 0);
    }
    return *this;
}

ActorPickReadbackWorker::Reservation::~Reservation() {
    reset();
}

void ActorPickReadbackWorker::Reservation::reset() noexcept {
    if (owner_ != nullptr && id_ != 0) {
        owner_->cancel(id_);
    }
    owner_ = nullptr;
    id_ = 0;
}

ActorPickReadbackWorker::ActorPickReadbackWorker(std::size_t capacity)
    : capacity_(capacity) {}

ActorPickReadbackWorker::~ActorPickReadbackWorker() {
    shutdown();
}

void ActorPickReadbackWorker::start() {
    std::lock_guard lock(mutex_);
    if (thread_.joinable()) {
        return;
    }
    stopping_ = false;
    accepting_ = true;
    thread_ = std::thread([this] { run(); });
}

std::optional<ActorPickReadbackWorker::Reservation> ActorPickReadbackWorker::reserve() {
    std::lock_guard lock(mutex_);
    if (!accepting_ || occupied_ >= capacity_) {
        return std::nullopt;
    }

    const std::uint64_t id = next_reservation_id_++;
    reservations_.insert(id);
    ++occupied_;
    return Reservation(this, id);
}

bool ActorPickReadbackWorker::submit(Reservation&& reservation, Work work) {
    if (!work) {
        return false;
    }

    {
        std::lock_guard lock(mutex_);
        if (!accepting_ || reservation.owner_ != this || reservation.id_ == 0 ||
            !reservations_.contains(reservation.id_)) {
            return false;
        }
        work_.push_back(std::move(work));
        reservations_.erase(reservation.id_);
        reservation.owner_ = nullptr;
        reservation.id_ = 0;
    }
    work_available_.notify_one();
    return true;
}

void ActorPickReadbackWorker::shutdown() {
    {
        std::lock_guard lock(mutex_);
        if (!thread_.joinable()) {
            accepting_ = false;
            reservations_.clear();
            occupied_ = 0;
            return;
        }
        accepting_ = false;
        stopping_ = true;
        occupied_ -= reservations_.size();
        reservations_.clear();
    }
    work_available_.notify_all();
    thread_.join();
}

std::size_t ActorPickReadbackWorker::pending_count() const noexcept {
    std::lock_guard lock(mutex_);
    return occupied_;
}

void ActorPickReadbackWorker::cancel(std::uint64_t id) noexcept {
    std::lock_guard lock(mutex_);
    if (reservations_.erase(id) == 1) {
        --occupied_;
    }
}

void ActorPickReadbackWorker::run() {
    for (;;) {
        Work work;
        {
            std::unique_lock lock(mutex_);
            work_available_.wait(lock, [this] { return stopping_ || !work_.empty(); });
            if (work_.empty()) {
                if (stopping_) {
                    return;
                }
                continue;
            }
            work = std::move(work_.front());
            work_.pop_front();
        }

        try {
            work();
        } catch (...) {
            // GPU/readback jobs translate failures into their own completion.
            // Keep this worker alive if a defensive catch is still reached.
        }

        {
            std::lock_guard lock(mutex_);
            --occupied_;
        }
    }
}

}  // namespace Corona::Systems::OpticsDetail
