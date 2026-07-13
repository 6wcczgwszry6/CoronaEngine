#include "corona/systems/ui/ui_surface_lifecycle.h"

#include <atomic>
#include <utility>

namespace Corona::Systems::UI {
namespace {

std::atomic<std::uint64_t> next_trace_id{1};

constexpr auto kRemovalCancellationMessage = "surface removal requested";

int state_order(UiSurfaceState state) noexcept {
    return static_cast<int>(state);
}

}  // namespace

DisplaySurfaceResult::DisplaySurfaceResult(Status result_status,
                                           std::string result_message)
    : status(result_status), message(std::move(result_message)) {}

struct SurfaceCompletionTicket::SharedState {
    std::mutex mutex;
    std::condition_variable completed;
    std::shared_ptr<const DisplaySurfaceResult> result;
};

SurfaceCompletionTicket::SurfaceCompletionTicket()
    : state_(std::make_shared<SharedState>()) {}

bool SurfaceCompletionTicket::try_complete(DisplaySurfaceResult::Status status,
                                           std::string message) const {
    auto completion =
        std::make_shared<const DisplaySurfaceResult>(status, std::move(message));
    {
        std::lock_guard lock(state_->mutex);
        if (state_->result) {
            return false;
        }
        state_->result = std::move(completion);
    }
    state_->completed.notify_all();
    return true;
}

bool SurfaceCompletionTicket::succeed() const {
    return try_complete(DisplaySurfaceResult::Status::Succeeded);
}

bool SurfaceCompletionTicket::fail(std::string message) const {
    return try_complete(DisplaySurfaceResult::Status::Failed, std::move(message));
}

bool SurfaceCompletionTicket::cancel(std::string message) const {
    return try_complete(DisplaySurfaceResult::Status::Cancelled, std::move(message));
}

bool SurfaceCompletionTicket::is_ready() const {
    std::lock_guard lock(state_->mutex);
    return state_->result != nullptr;
}

std::shared_ptr<const DisplaySurfaceResult> SurfaceCompletionTicket::result() const {
    std::lock_guard lock(state_->mutex);
    return state_->result;
}

bool SurfaceCompletionTicket::wait_until(Deadline deadline) const {
    std::unique_lock lock(state_->mutex);
    return state_->completed.wait_until(
        lock, deadline, [this]() { return state_->result != nullptr; });
}

UiSurfaceLifecycle::UiSurfaceLifecycle()
    : trace_id_(next_trace_id.fetch_add(1, std::memory_order_relaxed)) {}

std::uint64_t UiSurfaceLifecycle::trace_id() const noexcept {
    return trace_id_;
}

UiSurfaceState UiSurfaceLifecycle::state() const {
    std::lock_guard lock(mutex_);
    advance_locked();
    return state_;
}

SurfaceCompletionTicket UiSurfaceLifecycle::registration_ticket() const {
    return registration_ticket_;
}

SurfaceCompletionTicket UiSurfaceLifecycle::first_present_ticket() const {
    return first_present_ticket_;
}

SurfaceCompletionTicket UiSurfaceLifecycle::request_removal() {
    UiSurfaceState previous = UiSurfaceState::Registering;
    bool started_removal = false;
    std::shared_ptr<const DisplaySurfaceResult> terminal;

    {
        std::lock_guard lock(mutex_);
        advance_locked();
        if (is_terminal(state_)) {
            terminal = terminal_result_;
        } else if (state_ != UiSurfaceState::Removing) {
            previous = state_;
            state_ = UiSurfaceState::Removing;
            started_removal = true;
        }
    }

    if (terminal) {
        removal_ticket_.try_complete(terminal->status, terminal->message);
    } else if (started_removal) {
        if (previous == UiSurfaceState::Registering) {
            registration_ticket_.cancel(kRemovalCancellationMessage);
            first_present_ticket_.cancel(kRemovalCancellationMessage);
        } else if (previous == UiSurfaceState::WaitingFirstPresent) {
            first_present_ticket_.cancel(kRemovalCancellationMessage);
        }
        state_changed_.notify_all();
    }

    return removal_ticket_;
}

std::shared_ptr<const DisplaySurfaceResult> UiSurfaceLifecycle::terminal_result() const {
    std::lock_guard lock(mutex_);
    advance_locked();
    return terminal_result_;
}

bool UiSurfaceLifecycle::wait_until(UiSurfaceState desired, Deadline deadline) const {
    return wait_for(desired, deadline);
}

bool UiSurfaceLifecycle::wait_until_terminal(Deadline deadline) const {
    return wait_for(std::nullopt, deadline);
}

bool UiSurfaceLifecycle::is_terminal(UiSurfaceState state) noexcept {
    return state == UiSurfaceState::Retired || state == UiSurfaceState::Failed;
}

void UiSurfaceLifecycle::advance_locked() const {
    for (;;) {
        if (state_ == UiSurfaceState::Registering) {
            const auto registration = registration_ticket_.result();
            if (!registration) {
                return;
            }
            if (registration->status != DisplaySurfaceResult::Status::Succeeded) {
                state_ = UiSurfaceState::Failed;
                terminal_result_ = registration;
                first_present_ticket_.cancel("surface registration did not succeed");
                removal_ticket_.try_complete(registration->status,
                                             registration->message);
                state_changed_.notify_all();
                return;
            }
            state_ = UiSurfaceState::WaitingFirstPresent;
            state_changed_.notify_all();
            continue;
        }

        if (state_ == UiSurfaceState::WaitingFirstPresent) {
            const auto first_present = first_present_ticket_.result();
            if (!first_present) {
                return;
            }
            if (first_present->status != DisplaySurfaceResult::Status::Succeeded) {
                state_ = UiSurfaceState::Failed;
                terminal_result_ = first_present;
                removal_ticket_.try_complete(first_present->status,
                                             first_present->message);
                state_changed_.notify_all();
                return;
            }
            state_ = UiSurfaceState::Active;
            state_changed_.notify_all();
            continue;
        }

        if (state_ == UiSurfaceState::Removing) {
            const auto removal = removal_ticket_.result();
            if (!removal) {
                return;
            }
            terminal_result_ = removal;
            state_ = removal->status == DisplaySurfaceResult::Status::Succeeded
                         ? UiSurfaceState::Retired
                         : UiSurfaceState::Failed;
            state_changed_.notify_all();
        }
        return;
    }
}

bool UiSurfaceLifecycle::wait_for(std::optional<UiSurfaceState> desired,
                                  Deadline deadline) const {
    for (;;) {
        std::optional<SurfaceCompletionTicket> pending;
        {
            std::unique_lock lock(mutex_);
            advance_locked();

            if (desired) {
                if (state_ == *desired) {
                    return true;
                }
                if (is_terminal(state_) || state_order(state_) > state_order(*desired)) {
                    return false;
                }
            } else if (is_terminal(state_)) {
                return true;
            }

            switch (state_) {
                case UiSurfaceState::Registering:
                    pending = registration_ticket_;
                    break;
                case UiSurfaceState::WaitingFirstPresent:
                    pending = first_present_ticket_;
                    break;
                case UiSurfaceState::Removing:
                    pending = removal_ticket_;
                    break;
                case UiSurfaceState::Active:
                    if (!state_changed_.wait_until(lock, deadline, [this]() {
                            return state_ != UiSurfaceState::Active;
                        })) {
                        return false;
                    }
                    continue;
                case UiSurfaceState::Retired:
                case UiSurfaceState::Failed:
                    return !desired;
            }
        }

        if (!pending->wait_until(deadline)) {
            return false;
        }
    }
}

bool drain_ui_surfaces(std::span<UiSurfaceLifecycle* const> surfaces,
                       UiSurfaceLifecycle::Deadline deadline) {
    for (auto* surface : surfaces) {
        if (surface == nullptr) {
            return false;
        }
    }
    for (auto* surface : surfaces) {
        (void)surface->request_removal();
    }
    for (auto* surface : surfaces) {
        if (!surface->wait_until_terminal(deadline)) {
            return false;
        }
        const auto terminal = surface->terminal_result();
        if (surface->state() != UiSurfaceState::Retired || !terminal ||
            terminal->status != DisplaySurfaceResult::Status::Succeeded) {
            return false;
        }
    }
    return true;
}

}  // namespace Corona::Systems::UI
