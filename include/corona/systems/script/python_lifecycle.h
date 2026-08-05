#pragma once

#include <atomic>

namespace Corona::Script::Python {

enum class PythonLifecycleState {
    Created,
    InterpreterInitializing,
    InterpreterReady,
    BackendInitializing,
    Running,
    StopRequested,
    Stopping,
    Stopped,
    Failed,
};

class PythonLifecycle {
   public:
    PythonLifecycleState state() const noexcept {
        return state_.load(std::memory_order_acquire);
    }

    bool transition(PythonLifecycleState next) noexcept {
        auto current = state();
        if (!is_valid_transition(current, next)) {
            return false;
        }
        return state_.compare_exchange_strong(current, next,
                                              std::memory_order_acq_rel,
                                              std::memory_order_acquire);
    }

    bool request_stop() noexcept {
        auto current = state();
        for (;;) {
            if (current == PythonLifecycleState::StopRequested ||
                current == PythonLifecycleState::Stopping) {
                return true;
            }
            if (current == PythonLifecycleState::Stopped ||
                current == PythonLifecycleState::Failed) {
                return false;
            }
            if (state_.compare_exchange_weak(current, PythonLifecycleState::StopRequested,
                                              std::memory_order_acq_rel,
                                              std::memory_order_acquire)) {
                return true;
            }
        }
    }

   private:
    static bool is_valid_transition(PythonLifecycleState from,
                                    PythonLifecycleState to) noexcept {
        if (to == PythonLifecycleState::Failed) {
            return from != PythonLifecycleState::Stopped;
        }
        switch (from) {
            case PythonLifecycleState::Created:
                return to == PythonLifecycleState::InterpreterInitializing;
            case PythonLifecycleState::InterpreterInitializing:
                return to == PythonLifecycleState::InterpreterReady;
            case PythonLifecycleState::InterpreterReady:
                return to == PythonLifecycleState::BackendInitializing;
            case PythonLifecycleState::BackendInitializing:
                return to == PythonLifecycleState::Running;
            case PythonLifecycleState::Running:
                return to == PythonLifecycleState::StopRequested;
            case PythonLifecycleState::StopRequested:
                return to == PythonLifecycleState::Stopping;
            case PythonLifecycleState::Stopping:
                return to == PythonLifecycleState::Stopped;
            case PythonLifecycleState::Stopped:
            case PythonLifecycleState::Failed:
                return false;
        }
        return false;
    }

    std::atomic<PythonLifecycleState> state_{PythonLifecycleState::Created};
};

}  // namespace Corona::Script::Python
