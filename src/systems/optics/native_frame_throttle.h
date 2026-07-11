#pragma once

#include "horizon.h"

#include <cstddef>
#include <deque>
#include <stdexcept>
#include <utility>

namespace Corona::Systems::OpticsDetail {

/** Keeps the native renderer from recording an unbounded queue of stale views. */
class NativeFrameThrottle {
public:
    static constexpr std::size_t kMaxInFlight = 2;

    template <typename WaitForCompletion>
    void make_room(WaitForCompletion&& wait_for_completion) {
        while (in_flight_.size() >= kMaxInFlight) {
            std::forward<WaitForCompletion>(wait_for_completion)(in_flight_.front());
            in_flight_.pop_front();
        }
    }

    void submitted(Corona::Horizon::SubmitReceipt receipt) {
        if (!receipt.empty()) {
            if (in_flight_.size() >= kMaxInFlight) {
                throw std::logic_error("NativeFrameThrottle capacity was not made available before submit");
            }
            in_flight_.push_back(std::move(receipt));
        }
    }

    template <typename WaitForCompletion>
    void drain(WaitForCompletion&& wait_for_completion) {
        while (!in_flight_.empty()) {
            std::forward<WaitForCompletion>(wait_for_completion)(in_flight_.front());
            in_flight_.pop_front();
        }
    }

    [[nodiscard]] std::size_t in_flight_count() const noexcept {
        return in_flight_.size();
    }

private:
    std::deque<Corona::Horizon::SubmitReceipt> in_flight_;
};

}  // namespace Corona::Systems::OpticsDetail
