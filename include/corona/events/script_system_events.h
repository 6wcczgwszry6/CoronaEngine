#pragma once

namespace Corona::Events {

/**
 * @brief 脚本系统内部事件（单线程使用 EventBus）
 */
struct ScriptSystemDemoEvent {
    int demo_value;
};

/**
 * @brief 引擎到脚本系统的跨线程事件（使用 EventStream）
 */
struct EngineToScriptDemoEvent {
    float delta_time;
};

/**
 * @brief 脚本系统到引擎的跨线程事件（使用 EventStream）
 */
struct ScriptToEngineDemoEvent {
    float delta_time;
};

/**
 * @brief Python 初始化完成事件：脚本系统发布，UI 系统订阅后显示窗口（使用 EventStream）
 */
struct ScriptFinishStartEvent {
    float delta_time;
};

}  // namespace Corona::Events
