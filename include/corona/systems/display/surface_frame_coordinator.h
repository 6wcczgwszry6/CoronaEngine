#pragma once

#include <cstdint>
#include <functional>
#include <optional>
#include <type_traits>
#include <utility>

#include "corona/systems/display/surface_frame_gate.h"

namespace Corona::Systems::Detail {

/** Production frame-use and retirement ordering shared by Display and tests. */
class SurfaceFrameCoordinator {
   public:
    using Snapshot = SurfaceFrameGate::Snapshot;
    using Retirement = SurfaceFrameGate::Retirement;

    template <typename Images>
    class FrameAccess {
       public:
        FrameAccess(const FrameAccess&) = delete;
        FrameAccess& operator=(const FrameAccess&) = delete;
        FrameAccess(FrameAccess&&) noexcept = default;
        FrameAccess& operator=(FrameAccess&&) = delete;

        [[nodiscard]] explicit operator bool() const noexcept {
            return static_cast<bool>(lease_);
        }

        [[nodiscard]] Images& images() noexcept {
            return images_;
        }

        [[nodiscard]] const Images& images() const noexcept {
            return images_;
        }

       private:
        friend class SurfaceFrameCoordinator;

        FrameAccess(SurfaceFrameGate::Lease lease, Images images)
            : lease_(std::move(lease)), images_(std::move(images)) {}

        // Declaration order is intentional: member destruction is reversed,
        // so all acquired image handles die before the generation lease.
        SurfaceFrameGate::Lease lease_;
        Images images_;
    };

    [[nodiscard]] bool activate(std::uint64_t surface_id) {
        return gate_.activate(surface_id);
    }

    [[nodiscard]] Snapshot capture(std::uint64_t surface_id) const {
        return gate_.capture(surface_id);
    }

    template <typename AcquireImages>
    [[nodiscard]] auto begin_frame(const Snapshot& snapshot,
                                   AcquireImages&& acquire_images) const {
        return begin_frame(snapshot, []() {}, std::forward<AcquireImages>(acquire_images));
    }

    template <typename BeforeAcquire, typename AcquireImages>
    [[nodiscard]] auto begin_frame(const Snapshot& snapshot,
                                   BeforeAcquire&& before_acquire,
                                   AcquireImages&& acquire_images) const {
        using AcquisitionResult = std::invoke_result_t<AcquireImages>;
        static_assert(!std::is_void_v<AcquisitionResult>,
                      "frame acquisition must return an owned image bundle");
        static_assert(!std::is_reference_v<AcquisitionResult>,
                      "frame acquisition must return its image bundle by value");
        using Images = std::remove_cvref_t<AcquisitionResult>;
        static_assert(
            std::is_nothrow_move_constructible_v<Images>,
            "the owned image bundle must be nothrow move constructible");
        using Result = std::optional<FrameAccess<Images>>;

        std::invoke(std::forward<BeforeAcquire>(before_acquire));
        auto lease = gate_.try_acquire(snapshot);
        if (!lease) {
            return Result{};
        }

        // The bundle local is declared after the lease. If acquisition throws,
        // its already-acquired handles unwind before the lease can release.
        auto images = std::invoke(std::forward<AcquireImages>(acquire_images));
        FrameAccess<Images> access{std::move(lease), std::move(images)};
        return Result{std::move(access)};
    }

    [[nodiscard]] Retirement retire(std::uint64_t surface_id) {
        return gate_.retire(surface_id);
    }

    template <typename EraseDisplayer,
              typename EraseComposite,
              typename CompleteAcknowledgement>
    void teardown(std::uint64_t surface_id,
                  const Retirement& retirement,
                  EraseDisplayer&& erase_displayer,
                  EraseComposite&& erase_composite,
                  CompleteAcknowledgement&& complete_acknowledgement) {
        teardown(surface_id, retirement, []() {}, std::forward<EraseDisplayer>(erase_displayer), std::forward<EraseComposite>(erase_composite), std::forward<CompleteAcknowledgement>(complete_acknowledgement));
    }

    template <typename WaitEntered,
              typename EraseDisplayer,
              typename EraseComposite,
              typename CompleteAcknowledgement>
    void teardown(std::uint64_t surface_id,
                  const Retirement& retirement,
                  WaitEntered&& wait_entered,
                  EraseDisplayer&& erase_displayer,
                  EraseComposite&& erase_composite,
                  CompleteAcknowledgement&& complete_acknowledgement) {
        retirement.wait(std::forward<WaitEntered>(wait_entered));
        std::invoke(std::forward<EraseDisplayer>(erase_displayer));
        std::invoke(std::forward<EraseComposite>(erase_composite));
        gate_.forget(surface_id);
        std::invoke(
            std::forward<CompleteAcknowledgement>(complete_acknowledgement));
    }

    void forget(std::uint64_t surface_id) {
        gate_.forget(surface_id);
    }

   private:
    SurfaceFrameGate gate_;
};

}  // namespace Corona::Systems::Detail
