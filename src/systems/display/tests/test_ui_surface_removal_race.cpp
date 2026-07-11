#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstdlib>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <string_view>
#include <thread>
#include <type_traits>
#include <utility>

#include "corona/systems/display/surface_frame_gate.h"
#include "corona/systems/display/surface_lifecycle_acks.h"
#include "corona/systems/ui/ui_surface_lifecycle.h"

namespace {

using namespace std::chrono_literals;
using Corona::Systems::Detail::SurfaceFrameGate;
using Corona::Systems::Detail::SurfaceLifecycleAcks;
using Corona::Systems::UI::DisplaySurfaceResult;
using Corona::Systems::UI::SurfaceCompletionTicket;

[[noreturn]] void fail(std::string_view message) {
    std::cerr << "FAIL: " << message << '\n';
    std::exit(1);
}

void expect(bool condition, std::string_view message) {
    if (!condition) {
        fail(message);
    }
}

void expect_result(const SurfaceCompletionTicket& ticket,
                   DisplaySurfaceResult::Status status,
                   std::string_view message,
                   std::string_view failure_message) {
    const auto result = ticket.result();
    expect(result != nullptr, failure_message);
    expect(result->status == status, failure_message);
    expect(result->message == message, failure_message);
}

void acknowledgements_follow_registration_and_real_present_boundaries() {
    SurfaceLifecycleAcks acknowledgements;
    SurfaceCompletionTicket registration;
    SurfaceCompletionTicket first_present;
    acknowledgements.add_registration(registration);
    const auto first_present_boundary =
        acknowledgements.add_first_present(first_present);

    expect(!registration.is_ready(),
           "registration must remain pending before displayer construction");
    expect(!first_present.is_ready(),
           "first present must remain pending before compose/present");

    acknowledgements.registration_succeeded();
    expect_result(registration,
                  DisplaySurfaceResult::Status::Succeeded,
                  {},
                  "successful construction should acknowledge registration");
    expect(!first_present.is_ready(),
           "registration must not acknowledge the first present");

    acknowledgements.present_completed(false, first_present_boundary);
    expect(!first_present.is_ready(),
           "a skipped compose/present must leave first present pending");

    acknowledgements.present_completed(true, first_present_boundary);
    expect_result(first_present,
                  DisplaySurfaceResult::Status::Succeeded,
                  {},
                  "a real compose/present should acknowledge first present");
}

void first_present_only_completes_tickets_in_the_presented_snapshot() {
    SurfaceLifecycleAcks acknowledgements;
    SurfaceCompletionTicket captured_ticket;
    SurfaceCompletionTicket late_ticket;

    const auto captured_boundary =
        acknowledgements.add_first_present(captured_ticket);
    const auto late_boundary = acknowledgements.add_first_present(late_ticket);

    acknowledgements.present_completed(true, captured_boundary);
    expect(captured_ticket.is_ready(),
           "the ticket captured with a presented UI frame should complete");
    expect(!late_ticket.is_ready(),
           "a ticket added after the frame snapshot must remain pending");

    acknowledgements.present_completed(true, late_boundary);
    expect(late_ticket.is_ready(),
           "the late ticket should complete with a later UI snapshot");
}

void registration_and_present_failures_complete_forward_tickets() {
    SurfaceLifecycleAcks construction_failure;
    SurfaceCompletionTicket registration;
    SurfaceCompletionTicket first_present;
    construction_failure.add_registration(registration);
    (void)construction_failure.add_first_present(first_present);
    construction_failure.registration_failed(
        "HardwareDisplayer construction failed: test exception");

    expect_result(registration,
                  DisplaySurfaceResult::Status::Failed,
                  "HardwareDisplayer construction failed: test exception",
                  "construction failure should fail registration");
    expect_result(first_present,
                  DisplaySurfaceResult::Status::Failed,
                  "HardwareDisplayer construction failed: test exception",
                  "construction failure must not strand first present");

    SurfaceLifecycleAcks present_failure;
    SurfaceCompletionTicket failed_present;
    present_failure.registration_succeeded();
    (void)present_failure.add_first_present(failed_present);
    present_failure.present_failed("compose/present failed: test exception");
    expect_result(failed_present,
                  DisplaySurfaceResult::Status::Failed,
                  "compose/present failed: test exception",
                  "present exception should fail first present");
}

void device_loss_outcome_completes_tickets_attached_after_the_transition() {
    SurfaceLifecycleAcks acknowledgements;
    acknowledgements.fail_forward(
        "Display first present failed: Vulkan device lost");

    SurfaceCompletionTicket late_registration;
    SurfaceCompletionTicket late_first_present;
    acknowledgements.add_registration(late_registration);
    (void)acknowledgements.add_first_present(late_first_present);

    expect_result(late_registration,
                  DisplaySurfaceResult::Status::Failed,
                  "Display first present failed: Vulkan device lost",
                  "a registration attached after device loss must fail");
    expect_result(late_first_present,
                  DisplaySurfaceResult::Status::Failed,
                  "Display first present failed: Vulkan device lost",
                  "a first present attached after device loss must fail");
}

void removal_cancels_forward_work_and_waits_for_the_safe_point() {
    SurfaceLifecycleAcks acknowledgements;
    SurfaceCompletionTicket registration;
    SurfaceCompletionTicket first_present;
    SurfaceCompletionTicket removal;
    auto done = std::make_shared<std::promise<void>>();
    auto done_future = done->get_future();

    acknowledgements.add_registration(registration);
    acknowledgements.registration_succeeded();
    (void)acknowledgements.add_first_present(first_present);
    acknowledgements.removal_requested(removal, done);

    expect_result(first_present,
                  DisplaySurfaceResult::Status::Cancelled,
                  "surface removal requested",
                  "early removal should cancel first present");
    expect(!removal.is_ready(),
           "removal must remain pending before resource destruction");
    expect(done_future.wait_for(0ms) == std::future_status::timeout,
           "legacy done must remain pending before resource destruction");

    acknowledgements.removal_succeeded();
    expect_result(removal,
                  DisplaySurfaceResult::Status::Succeeded,
                  {},
                  "safe teardown should acknowledge removal");
    expect(done_future.wait_for(0ms) == std::future_status::ready,
           "legacy done should complete at the removal safe point");
}

void duplicate_and_late_removals_complete_idempotently() {
    SurfaceLifecycleAcks acknowledgements;
    SurfaceCompletionTicket first_removal;
    SurfaceCompletionTicket duplicate_removal;
    auto first_done = std::make_shared<std::promise<void>>();
    auto duplicate_done = std::make_shared<std::promise<void>>();
    auto first_future = first_done->get_future();
    auto duplicate_future = duplicate_done->get_future();

    acknowledgements.removal_requested(first_removal, first_done);
    acknowledgements.removal_requested(duplicate_removal, duplicate_done);
    acknowledgements.removal_succeeded();
    acknowledgements.removal_succeeded();

    expect_result(first_removal,
                  DisplaySurfaceResult::Status::Succeeded,
                  {},
                  "first removal should succeed once");
    expect_result(duplicate_removal,
                  DisplaySurfaceResult::Status::Succeeded,
                  {},
                  "duplicate removal should share the safe completion");
    expect(first_future.wait_for(0ms) == std::future_status::ready &&
               duplicate_future.wait_for(0ms) == std::future_status::ready,
           "all distinct legacy promises should complete once");

    SurfaceCompletionTicket late_removal;
    auto late_done = std::make_shared<std::promise<void>>();
    auto late_future = late_done->get_future();
    acknowledgements.removal_requested(late_removal, late_done);
    expect_result(late_removal,
                  DisplaySurfaceResult::Status::Succeeded,
                  {},
                  "already-closed surface removal should complete immediately");
    expect(late_future.wait_for(0ms) == std::future_status::ready,
           "already-closed legacy promise should complete immediately");
}

void shutdown_cancels_impossible_forward_work_without_certifying_removal_early() {
    SurfaceLifecycleAcks acknowledgements;
    SurfaceCompletionTicket registration;
    SurfaceCompletionTicket first_present;
    SurfaceCompletionTicket removal;
    auto done = std::make_shared<std::promise<void>>();
    auto done_future = done->get_future();

    acknowledgements.add_registration(registration);
    (void)acknowledgements.add_first_present(first_present);
    acknowledgements.removal_requested(removal, done);
    acknowledgements.cancel_forward("display shutdown before surface became ready");

    expect(registration.is_ready() && first_present.is_ready(),
           "shutdown should leave no forward ticket pending");
    expect(!removal.is_ready() &&
               done_future.wait_for(0ms) == std::future_status::timeout,
           "shutdown must not certify removal before resources are destroyed");

    acknowledgements.removal_succeeded();
    expect(removal.is_ready() &&
               done_future.wait_for(0ms) == std::future_status::ready,
           "shutdown should acknowledge removal after resource destruction");
}

void removal_invalidates_a_snapshot_captured_before_retirement() {
    constexpr std::uint64_t surface_id = 0x1234;
    SurfaceFrameGate gate;
    expect(gate.activate(surface_id), "a new surface should activate its frame gate");

    std::mutex mutex;
    std::condition_variable state_changed;
    bool snapshot_captured = false;
    bool resume_display = false;
    std::atomic<int> retired_image_accesses{0};

    std::thread display_frame([&]() {
        const auto snapshot = gate.capture(surface_id);
        {
            std::lock_guard lock(mutex);
            snapshot_captured = true;
        }
        state_changed.notify_all();

        {
            std::unique_lock lock(mutex);
            state_changed.wait(lock, [&]() { return resume_display; });
        }

        auto lease = gate.try_acquire(snapshot);
        if (lease) {
            retired_image_accesses.fetch_add(1, std::memory_order_relaxed);
        }
    });

    {
        std::unique_lock lock(mutex);
        state_changed.wait(lock, [&]() { return snapshot_captured; });
    }

    auto retirement = gate.retire(surface_id);
    retirement.wait();

    {
        std::lock_guard lock(mutex);
        resume_display = true;
    }
    state_changed.notify_all();
    display_frame.join();

    expect(retired_image_accesses.load(std::memory_order_relaxed) == 0,
           "a retired generation must invalidate an already-captured snapshot");
}

void removal_acknowledgement_waits_for_an_acquired_frame_lease() {
    constexpr std::uint64_t surface_id = 0x5678;
    SurfaceFrameGate gate;
    expect(gate.activate(surface_id), "a new surface should activate its frame gate");

    auto lease = gate.try_acquire(gate.capture(surface_id));
    expect(static_cast<bool>(lease), "an active snapshot should acquire a frame lease");

    using Lease = decltype(lease);
    static_assert(std::is_move_constructible_v<Lease>);
    static_assert(std::is_move_assignable_v<Lease>);
    static_assert(!std::is_copy_constructible_v<Lease>);
    static_assert(!std::is_copy_assignable_v<Lease>);

    auto moved_lease = std::move(lease);
    expect(!lease, "moving a lease should empty the source");
    expect(static_cast<bool>(moved_lease), "moving a lease should retain ownership");

    auto retirement = gate.retire(surface_id);
    SurfaceCompletionTicket removal_ack;
    std::mutex mutex;
    std::condition_variable waiter_started;
    bool waiting_for_quiescence = false;

    std::thread display_teardown([&]() mutable {
        {
            std::lock_guard lock(mutex);
            waiting_for_quiescence = true;
        }
        waiter_started.notify_one();
        retirement.wait();
        removal_ack.succeed();
    });

    {
        std::unique_lock lock(mutex);
        waiter_started.wait(lock, [&]() { return waiting_for_quiescence; });
    }
    expect(!removal_ack.is_ready(),
           "removal acknowledgement must remain pending while a frame lease is active");

    moved_lease = {};
    display_teardown.join();

    const auto result = removal_ack.result();
    expect(result != nullptr &&
               result->status == DisplaySurfaceResult::Status::Succeeded,
           "removal should acknowledge after the final frame lease is released");
}

}  // namespace

int main() {
    acknowledgements_follow_registration_and_real_present_boundaries();
    first_present_only_completes_tickets_in_the_presented_snapshot();
    registration_and_present_failures_complete_forward_tickets();
    device_loss_outcome_completes_tickets_attached_after_the_transition();
    removal_cancels_forward_work_and_waits_for_the_safe_point();
    duplicate_and_late_removals_complete_idempotently();
    shutdown_cancels_impossible_forward_work_without_certifying_removal_early();
    removal_invalidates_a_snapshot_captured_before_retirement();
    removal_acknowledgement_waits_for_an_acquired_frame_lease();
    std::cout << "UI surface removal race tests passed\n";
    return 0;
}
