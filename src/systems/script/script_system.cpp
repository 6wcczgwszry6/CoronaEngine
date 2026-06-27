#include <corona/events/engine_events.h>
#include <corona/events/script_system_events.h>
#include <corona/kernel/core/i_logger.h>
#include <corona/kernel/event/i_event_bus.h>
#include <corona/kernel/event/i_event_stream.h>
#include <corona/systems/script/camera_follow_controller.h>
#include <corona/systems/script/python_api.h>
#include <corona/systems/script/script_system.h>
#include <nanobind/nanobind.h>

namespace Corona::Systems {

ScriptSystem::ScriptSystem()
    : python_api_(std::make_unique<Script::Python::PythonAPI>()) {
    set_target_fps(60);  // 显示系统高刷新率以提升响应速度
}

ScriptSystem::~ScriptSystem() = default;

bool ScriptSystem::initialize(Kernel::ISystemContext* ctx) {
    CFW_LOG_NOTICE("ScriptSystem: Initializing...");

    // JS→Python 走 CEF query bridge (deal_func_from_js)，ScriptSystem 不再订阅 UI 事件。
    if (ctx->event_bus() == nullptr) {
        CFW_LOG_WARNING("ScriptSystem: No event bus available");
    }

#ifdef CORONA_ENABLE_PYTHON_API
    if (!python_api_->initializeInterpreter()) {
        CFW_LOG_ERROR("ScriptSystem: Python interpreter initialization failed");
        return false;
    }
#endif

    return true;
}

void ScriptSystem::stop() {
    if (python_api_) {
        python_api_->begin_shutdown();
    }
    Kernel::SystemBase::stop();
}

void ScriptSystem::update() {
#ifdef CORONA_ENABLE_PYTHON_API
    CameraFollowController::instance().update(1.0f / 60.0f);
    python_api_->runPythonScript();
#endif
}

void ScriptSystem::shutdown() {
    CFW_LOG_NOTICE("ScriptSystem: Shutting down...");

    // 主动关闭 Python 解释器，避免在析构时阻塞
    python_api_->shutdown();
}

}  // namespace Corona::Systems
