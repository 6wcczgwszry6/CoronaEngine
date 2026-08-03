#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>

namespace Corona::Script::Python {

enum class PythonRuntimeRequestKind {
    ServiceCall,
    Callback,
    LifecycleControl,
};

enum class PythonRuntimeResponseStatus {
    Success,
    Error,
    Timeout,
    QueueFull,
    RuntimeStopping,
};

enum class PythonRuntimeState {
    Accepting,
    Quiescing,
    Draining,
    PythonStopping,
    Stopped,
};

struct PythonRuntimeRequest {
    std::uint64_t request_id = 0;
    PythonRuntimeRequestKind kind = PythonRuntimeRequestKind::ServiceCall;
    std::string source;
    std::string module;
    std::string function;
    std::string payload_json;
};

struct PythonRuntimeResponse {
    PythonRuntimeResponseStatus status = PythonRuntimeResponseStatus::Error;
    std::string payload_json;
    std::string error;

    static PythonRuntimeResponse success(std::string payload = {});
    static PythonRuntimeResponse failure(std::string message);
    static PythonRuntimeResponse timeout();
    static PythonRuntimeResponse queue_full();
    static PythonRuntimeResponse runtime_stopping();
};

namespace Detail {
struct PythonRuntimeTicketState;
}

class PythonRuntimeTicket {
   public:
    bool accepted = false;
    std::uint64_t request_id = 0;
    PythonRuntimeResponse response;

    PythonRuntimeResponse wait(std::chrono::milliseconds timeout) const;

   private:
    friend class PythonRuntimeCoordinator;
    std::shared_ptr<Detail::PythonRuntimeTicketState> state_;
};

class PythonRuntimeCoordinator {
   public:
    explicit PythonRuntimeCoordinator(std::size_t capacity = 256);

    PythonRuntimeTicket submit(PythonRuntimeRequest request);
    PythonRuntimeResponse submit_and_wait(PythonRuntimeRequest request,
                                          std::chrono::milliseconds timeout);
    std::optional<PythonRuntimeRequest> wait_pop(std::chrono::milliseconds timeout);
    bool complete(std::uint64_t request_id, PythonRuntimeResponse response);

    void begin_quiescing();
    void begin_draining();
    void begin_python_stopping();
    void stop();

    PythonRuntimeState state() const noexcept;
    std::size_t pending_count() const;

   private:
    bool cancel(std::uint64_t request_id, PythonRuntimeResponse response);
    void transition_and_cancel(PythonRuntimeState next);

    const std::size_t capacity_;
    std::atomic<std::uint64_t> next_request_id_{1};
    std::atomic<PythonRuntimeState> state_{PythonRuntimeState::Accepting};
    mutable std::mutex mutex_;
    std::condition_variable queue_cv_;
    std::deque<PythonRuntimeRequest> queue_;
    std::unordered_map<std::uint64_t, std::shared_ptr<Detail::PythonRuntimeTicketState>> pending_;
};

PythonRuntimeCoordinator* active_python_runtime_coordinator() noexcept;
void install_active_python_runtime_coordinator(PythonRuntimeCoordinator* coordinator) noexcept;

}  // namespace Corona::Script::Python
