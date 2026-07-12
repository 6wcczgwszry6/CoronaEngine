#pragma once

#include <condition_variable>
#include <cstddef>
#include <future>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "corona/systems/ui/ui_surface_lifecycle.h"

namespace Corona::Systems::Detail {

/**
 * Owner-independent lifetime fence for copied EventBus callbacks.
 *
 * A callback must acquire Access before dereferencing the owner. close()
 * rejects callbacks that have not entered and wait_for_quiescence() waits only
 * for callbacks that already hold Access. Rejected callbacks deposit their
 * acknowledgements in the shared state, which remains alive with copied
 * handlers and publishes results only after Display resource destruction.
 */
template <typename Owner>
class OwnerCallbackGate {
   public:
    using Result = UI::DisplaySurfaceResult;
    using Ticket = UI::SurfaceCompletionTicket;

   private:
    struct SharedState {
        std::mutex mutex;
        std::condition_variable quiescent;
        Owner* owner = nullptr;
        std::size_t active_callbacks = 0;
        bool open = true;
        bool resources_destroyed = false;
        Result::Status closed_status = Result::Status::Cancelled;
        std::string closed_message;
        std::vector<Ticket> registrations;
        std::vector<Ticket> first_presents;
        std::vector<Ticket> removals;
        std::vector<std::shared_ptr<std::promise<void>>> removal_promises;
    };

   public:
    class Access {
       public:
        Access() = default;
        Access(const Access&) = delete;
        Access& operator=(const Access&) = delete;

        Access(Access&& other) noexcept
            : state_(std::exchange(other.state_, {})),
              owner_(std::exchange(other.owner_, nullptr)) {}

        Access& operator=(Access&& other) noexcept {
            if (this != &other) {
                release();
                state_ = std::exchange(other.state_, {});
                owner_ = std::exchange(other.owner_, nullptr);
            }
            return *this;
        }

        ~Access() {
            release();
        }

        [[nodiscard]] explicit operator bool() const noexcept {
            return owner_ != nullptr;
        }

        [[nodiscard]] Owner& owner() const noexcept {
            return *owner_;
        }

       private:
        friend class OwnerCallbackGate;

        Access(std::shared_ptr<SharedState> state, Owner* owner)
            : state_(std::move(state)), owner_(owner) {}

        void release() noexcept {
            if (!state_) {
                return;
            }

            auto state = std::exchange(state_, {});
            owner_ = nullptr;
            bool became_quiescent = false;
            {
                std::lock_guard lock(state->mutex);
                if (state->active_callbacks > 0) {
                    --state->active_callbacks;
                    became_quiescent = state->active_callbacks == 0;
                }
            }
            if (became_quiescent) {
                state->quiescent.notify_all();
            }
        }

        std::shared_ptr<SharedState> state_;
        Owner* owner_ = nullptr;
    };

    explicit OwnerCallbackGate(Owner& owner)
        : state_(std::make_shared<SharedState>()) {
        state_->owner = &owner;
    }

    [[nodiscard]] Access try_acquire() const {
        std::lock_guard lock(state_->mutex);
        if (!state_->open || state_->owner == nullptr) {
            return {};
        }
        ++state_->active_callbacks;
        return Access{state_, state_->owner};
    }

    void close() {
        std::lock_guard lock(state_->mutex);
        state_->open = false;
        state_->owner = nullptr;
    }

    void wait_for_quiescence() const {
        std::unique_lock lock(state_->mutex);
        state_->quiescent.wait(
            lock, [this]() { return state_->active_callbacks == 0; });
    }

    void defer_registration(const std::optional<Ticket>& ticket) const {
        defer_forward(ticket, state_->registrations);
    }

    void defer_first_present(const std::optional<Ticket>& ticket) const {
        defer_forward(ticket, state_->first_presents);
    }

    void defer_removal(
        const std::optional<Ticket>& ticket,
        const std::shared_ptr<std::promise<void>>& done) const {
        bool complete_now = false;
        {
            std::lock_guard lock(state_->mutex);
            complete_now = state_->resources_destroyed;
            if (!complete_now) {
                if (ticket) {
                    state_->removals.push_back(*ticket);
                }
                if (done) {
                    state_->removal_promises.push_back(done);
                }
            }
        }
        if (complete_now) {
            if (ticket) {
                ticket->succeed();
            }
            fulfill(done);
        }
    }

    void complete_deferred_after_resources_destroyed(
        Result::Status forward_status,
        std::string message) {
        std::vector<Ticket> registrations;
        std::vector<Ticket> first_presents;
        std::vector<Ticket> removals;
        std::vector<std::shared_ptr<std::promise<void>>> promises;
        std::string completion_message;
        {
            std::lock_guard lock(state_->mutex);
            if (state_->resources_destroyed) {
                return;
            }
            state_->resources_destroyed = true;
            state_->closed_status = forward_status;
            state_->closed_message = std::move(message);
            completion_message = state_->closed_message;
            registrations.swap(state_->registrations);
            first_presents.swap(state_->first_presents);
            removals.swap(state_->removals);
            promises.swap(state_->removal_promises);
        }

        for (const auto& ticket : registrations) {
            ticket.try_complete(forward_status, completion_message);
        }
        for (const auto& ticket : first_presents) {
            ticket.try_complete(forward_status, completion_message);
        }
        for (const auto& ticket : removals) {
            ticket.succeed();
        }
        for (const auto& promise : promises) {
            fulfill(promise);
        }
    }

   private:
    void defer_forward(const std::optional<Ticket>& ticket,
                       std::vector<Ticket>& pending) const {
        if (!ticket) {
            return;
        }

        bool complete_now = false;
        Result::Status status = Result::Status::Cancelled;
        std::string message;
        {
            std::lock_guard lock(state_->mutex);
            complete_now = state_->resources_destroyed;
            if (complete_now) {
                status = state_->closed_status;
                message = state_->closed_message;
            } else {
                pending.push_back(*ticket);
            }
        }
        if (complete_now) {
            ticket->try_complete(status, std::move(message));
        }
    }

    static void fulfill(const std::shared_ptr<std::promise<void>>& promise) {
        if (!promise) {
            return;
        }
        try {
            promise->set_value();
        } catch (const std::future_error&) {
            // Legacy duplicate removals may share a completed promise.
        }
    }

    std::shared_ptr<SharedState> state_;
};

}  // namespace Corona::Systems::Detail
