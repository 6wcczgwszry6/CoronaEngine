#include "../native_frame_throttle.h"

#include <cassert>
#include <vector>

namespace {

Corona::Horizon::SubmitReceipt receipt(std::uint64_t serial) {
    Corona::Horizon::SubmitReceipt value;
    value.serial = serial;
    value.tokens.push_back({});
    return value;
}

}  // namespace

int main() {
    static_assert(requires(Corona::Horizon::HardwareExecutor& executor,
                           const Corona::Horizon::SubmitReceipt& value) {
        executor.wait_for_completion(value);
    });

    Corona::Systems::OpticsDetail::NativeFrameThrottle throttle;
    std::vector<std::uint64_t> waited;
    const auto wait = [&waited](const Corona::Horizon::SubmitReceipt& value) {
        waited.push_back(value.serial);
    };

    throttle.submitted(receipt(1));
    throttle.submitted(receipt(2));
    assert(throttle.in_flight_count() == 2);

    bool rejected_third_receipt = false;
    try {
        throttle.submitted(receipt(3));
    } catch (const std::logic_error&) {
        rejected_third_receipt = true;
    }
    assert(rejected_third_receipt);

    throttle.make_room(wait);
    assert(waited == std::vector<std::uint64_t>{1});
    assert(throttle.in_flight_count() == 1);

    throttle.submitted(receipt(3));
    throttle.make_room(wait);
    assert(waited == (std::vector<std::uint64_t>{1, 2}));
    assert(throttle.in_flight_count() == 1);

    throttle.drain(wait);
    assert(waited == (std::vector<std::uint64_t>{1, 2, 3}));
    assert(throttle.in_flight_count() == 0);
    return 0;
}
