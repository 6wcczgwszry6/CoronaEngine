#pragma once

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <memory>
#include <mutex>
#include <optional>
#include <span>
#include <string>

namespace Corona::Systems::UI {

/** Immutable acknowledgement published by a display-surface operation. */
struct DisplaySurfaceResult {
    enum class Status {
        Succeeded,
        Failed,
        Cancelled,
    };

    explicit DisplaySurfaceResult(Status result_status, std::string result_message = {});

    const Status status;
    const std::string message;

    friend bool operator==(const DisplaySurfaceResult&,
                           const DisplaySurfaceResult&) = default;
};

/**
 * Copyable handle to one shared completion.
 *
 * Copies may cross threads in events. The first try_complete() call wins and
 * fixes the immutable result for every copy; later completions return false.
 */
class SurfaceCompletionTicket {
   public:
    using Clock = std::chrono::steady_clock;
    using Deadline = Clock::time_point;

    SurfaceCompletionTicket();
    SurfaceCompletionTicket(const SurfaceCompletionTicket&) = default;
    SurfaceCompletionTicket& operator=(const SurfaceCompletionTicket&) = default;

    bool try_complete(DisplaySurfaceResult::Status status,
                      std::string message = {}) const;
    bool succeed() const;
    bool fail(std::string message) const;
    bool cancel(std::string message = {}) const;

    [[nodiscard]] bool is_ready() const;
    [[nodiscard]] std::shared_ptr<const DisplaySurfaceResult> result() const;
    [[nodiscard]] bool wait_until(Deadline deadline) const;

   private:
    struct SharedState;
    std::shared_ptr<SharedState> state_;
};

enum class UiSurfaceState : std::uint8_t {
    Registering,
    WaitingFirstPresent,
    Active,
    Removing,
    Retired,
    Failed,
};

/**
 * Thread-safe protocol coordinator for exactly one UI surface.
 *
 * Construction starts registration. Copy the registration and first-present
 * tickets into their events, and use the ticket returned by request_removal()
 * for the removal event. Querying or waiting folds completed acknowledgements
 * into monotonic lifecycle transitions. This class owns no native surface,
 * SDL, Vulkan, Display, or browser object.
 */
class UiSurfaceLifecycle {
   public:
    using Clock = SurfaceCompletionTicket::Clock;
    using Deadline = SurfaceCompletionTicket::Deadline;

    UiSurfaceLifecycle();
    UiSurfaceLifecycle(const UiSurfaceLifecycle&) = delete;
    UiSurfaceLifecycle& operator=(const UiSurfaceLifecycle&) = delete;

    [[nodiscard]] std::uint64_t trace_id() const noexcept;
    [[nodiscard]] UiSurfaceState state() const;
    [[nodiscard]] SurfaceCompletionTicket registration_ticket() const;
    [[nodiscard]] SurfaceCompletionTicket first_present_ticket() const;
    [[nodiscard]] SurfaceCompletionTicket request_removal();
    [[nodiscard]] std::shared_ptr<const DisplaySurfaceResult> terminal_result() const;

    /** Waits for an exact state, returning false on timeout or if it is passed. */
    [[nodiscard]] bool wait_until(UiSurfaceState desired, Deadline deadline) const;
    /** Waits until either Retired or Failed without discarding timed-out work. */
    [[nodiscard]] bool wait_until_terminal(Deadline deadline) const;

   private:
    [[nodiscard]] static bool is_terminal(UiSurfaceState state) noexcept;
    void advance_locked() const;
    [[nodiscard]] bool wait_for(std::optional<UiSurfaceState> desired,
                                Deadline deadline) const;

    const std::uint64_t trace_id_;
    mutable std::mutex mutex_;
    mutable std::condition_variable state_changed_;
    mutable UiSurfaceState state_ = UiSurfaceState::Registering;
    SurfaceCompletionTicket registration_ticket_;
    SurfaceCompletionTicket first_present_ticket_;
    SurfaceCompletionTicket removal_ticket_;
    mutable std::shared_ptr<const DisplaySurfaceResult> terminal_result_;
};

/** Requests removal for every nonterminal surface and waits on one deadline. */
[[nodiscard]] bool drain_ui_surfaces(
    std::span<UiSurfaceLifecycle* const> surfaces,
    UiSurfaceLifecycle::Deadline deadline);

}  // namespace Corona::Systems::UI
