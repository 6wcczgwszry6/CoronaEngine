#pragma once

#include <corona/events/mechanics_system_events.h>
#include <corona/events/scene_system_events.h>
#include <corona/kernel/event/i_event_bus.h>
#include <corona/kernel/event/i_event_stream.h>
#include <corona/kernel/system/system_base.h>

#include <memory>

namespace Corona::Systems {

// 前向声明，避免每帧通过 ISystemContext::get_system() 获取
class GeometrySystem;

/**
 * @brief 力学系统 (Mechanics System)
 *
 * 负责物理模拟、刚体动力学、碰撞检测和响应。
 * 运行在独立线程，以 60 FPS 更新物理状态。
 */
class MechanicsSystem : public Kernel::SystemBase {
   public:
    MechanicsSystem();

    ~MechanicsSystem() override;

    // ========================================
    // ISystem 接口实现
    // ========================================

    std::string_view get_name() const override {
        return "Mechanics";
    }

    int get_priority() const override {
        return 75;  // 中高优先级，在几何系统之后
    }

    /**
     * @brief 初始化力学系统
     * @param ctx 系统上下文
     * @return 初始化成功返回 true
     */
    bool initialize(Kernel::ISystemContext* ctx) override;

    /**
     * @brief 每帧更新物理
     *
     * 在独立线程中调用，执行物理模拟
     */
    void update() override;

    /**
     * @brief 关闭力学系统
     *
     * 清理所有物理资源
     */
    void stop() override;

    void shutdown() override;

   private:
    // 力学系统私有成员
    void update_physics();

    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace Corona::Systems
