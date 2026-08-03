#include <corona/systems/script/python_runtime_coordinator.h>

#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>

using namespace std::chrono_literals;
using Corona::Script::Python::PythonRuntimeCoordinator;
using Corona::Script::Python::PythonRuntimeRequest;
using Corona::Script::Python::PythonRuntimeRequestKind;
using Corona::Script::Python::PythonRuntimeResponse;
using Corona::Script::Python::PythonRuntimeResponseStatus;
using Corona::Script::Python::PythonRuntimeState;

namespace {
bool require(bool condition, const char* message) {
    if (!condition) std::cerr << message << '\n';
    return condition;
}

PythonRuntimeRequest request(std::string payload = {}) {
    PythonRuntimeRequest value;
    value.kind = PythonRuntimeRequestKind::ServiceCall;
    value.payload_json = std::move(payload);
    return value;
}

PythonRuntimeResponse callback_handler(const PythonRuntimeRequest& value) {
    return PythonRuntimeResponse::success("callback:" + value.payload_json);
}
}  // namespace

int main() {
    {
        PythonRuntimeCoordinator coordinator(2);
        if (!require(coordinator.bind_consumer_thread(),
                     "first thread should bind as the Python consumer")) return 1;
        std::atomic<bool> second_thread_bound{true};
        std::thread other([&] { second_thread_bound.store(coordinator.bind_consumer_thread()); });
        other.join();
        if (!require(!second_thread_bound.load(),
                     "another thread must not replace the Python consumer")) return 1;
    }

    {
        PythonRuntimeCoordinator coordinator(2);
        auto callback = request("payload");
        callback.kind = PythonRuntimeRequestKind::Callback;
        callback.handler = &callback_handler;
        auto ticket = coordinator.submit(std::move(callback));
        auto queued = coordinator.wait_pop(50ms);
        if (!require(queued.has_value(), "callback request should reach the consumer") ||
            !require(queued->handler != nullptr, "callback handler should survive queueing")) return 1;
        auto response = queued->handler(*queued);
        coordinator.complete(queued->request_id, response);
        response = ticket.wait(50ms);
        if (!require(response.status == PythonRuntimeResponseStatus::Success,
                     "callback handler should complete") ||
            !require(response.payload_json == "callback:payload",
                     "callback handler should receive the plain payload")) return 1;
    }

    {
        PythonRuntimeCoordinator coordinator(2);
        std::thread consumer([&] {
            auto item = coordinator.wait_pop(100ms);
            if (item) coordinator.complete(item->request_id, PythonRuntimeResponse::success(item->payload_json));
        });
        auto response = coordinator.submit_and_wait(request("first"), 500ms);
        consumer.join();
        if (!require(response.status == PythonRuntimeResponseStatus::Success, "request should complete") ||
            !require(response.payload_json == "first", "response payload should match")) return 1;
    }

    {
        PythonRuntimeCoordinator coordinator(1);
        auto first = coordinator.submit(request("one"));
        auto second = coordinator.submit(request("two"));
        if (!require(first.accepted, "first request should be accepted") ||
            !require(!second.accepted && second.response.status == PythonRuntimeResponseStatus::QueueFull,
                     "request above capacity should return queue_full")) return 1;
    }

    {
        PythonRuntimeCoordinator coordinator(4);
        auto response = coordinator.submit_and_wait(request("late"), 5ms);
        if (!require(response.status == PythonRuntimeResponseStatus::Timeout, "request should time out") ||
            !require(!coordinator.wait_pop(5ms).has_value(), "timed-out request must be discarded")) return 1;
    }

    {
        PythonRuntimeCoordinator coordinator(8);
        auto ticket = coordinator.submit(request("shutdown"));
        coordinator.begin_quiescing();
        auto response = ticket.wait(50ms);
        if (!require(coordinator.state() == PythonRuntimeState::Quiescing, "state should be quiescing") ||
            !require(response.status == PythonRuntimeResponseStatus::RuntimeStopping,
                     "pending request should complete as runtime_stopping") ||
            !require(!coordinator.submit(request("rejected")).accepted,
                     "new requests must be rejected")) return 1;
    }

    {
        PythonRuntimeCoordinator coordinator(64);
        constexpr int producer_count = 4;
        constexpr int per_producer = 8;
        std::atomic<int> completed{0};
        std::atomic<bool> duplicate_completed{false};
        std::thread consumer([&] {
            while (completed.load() < producer_count * per_producer) {
                auto item = coordinator.wait_pop(100ms);
                if (!item) continue;
                if (coordinator.complete(item->request_id, PythonRuntimeResponse::success(item->payload_json))) {
                    completed.fetch_add(1);
                }
                if (coordinator.complete(item->request_id, PythonRuntimeResponse::success("duplicate"))) {
                    duplicate_completed.store(true);
                }
            }
        });
        std::vector<std::thread> producers;
        std::atomic<int> successful{0};
        for (int producer = 0; producer < producer_count; ++producer) {
            producers.emplace_back([&, producer] {
                for (int index = 0; index < per_producer; ++index) {
                    auto response = coordinator.submit_and_wait(
                        request(std::to_string(producer) + ":" + std::to_string(index)), 1s);
                    if (response.status == PythonRuntimeResponseStatus::Success) successful.fetch_add(1);
                }
            });
        }
        for (auto& producer : producers) producer.join();
        consumer.join();
        if (!require(successful.load() == producer_count * per_producer, "all requests should complete") ||
            !require(!duplicate_completed.load(), "request must only complete once")) return 1;
    }
    return 0;
}
