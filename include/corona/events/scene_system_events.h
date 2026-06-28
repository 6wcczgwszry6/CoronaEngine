#pragma once

#include <cstdint>
#include <utility>
#include <vector>

namespace Corona::Events {

/**
 * @brief 场景系统：actor 进入某相机视锥
 */
struct ActorEnteredFrustumEvent {
    std::uintptr_t scene{};
    std::uintptr_t actor{};
    std::uintptr_t camera{};
};

/**
 * @brief 场景系统：actor 离开某相机视锥
 */
struct ActorLeftFrustumEvent {
    std::uintptr_t scene{};
    std::uintptr_t actor{};
    std::uintptr_t camera{};
};

/**
 * @brief 触发 LRU 卸载请求（M3 起接入 ActorCache）
 */
struct ActorEvictRequestedEvent {
    std::uintptr_t scene{};
    std::uintptr_t actor{};
};

/**
 * @brief 触发 LRU 唤醒请求（M3 起接入 ActorCache）
 */
struct ActorRestoreRequestedEvent {
    std::uintptr_t scene{};
    std::uintptr_t actor{};
};

/**
 * @brief 触发 Actor 的距离预加载请求事件
 */
struct ActorLoadRequestedEvent {
    std::uintptr_t scene{};
    std::uintptr_t actor{};
};

/**
 * @brief Actor 资源加载完成，GPU 资源已就绪（由 GeometrySystem 发布）
 *
 * 外部系统（Optics/Mechanics/Vision）应监听此事件以开始消费该 actor。
 * 与 ActorLoadRequestedEvent 配对：request → 异步加载 → finished。
 */
struct ActorLoadFinishedEvent {
    std::uintptr_t scene{};
    std::uintptr_t actor{};
};

/**
 * @brief 触发 Actor 的距离卸载请求事件
 */
struct ActorUnloadRequestedEvent {
    std::uintptr_t scene{};
    std::uintptr_t actor{};
};

/**
 * @brief Actor 资源卸载完成，GPU 资源已释放（由 GeometrySystem 发布）
 *
 * 外部系统应监听此事件以停止消费该 actor。
 * 与 ActorUnloadRequestedEvent 配对：request → 异步卸载 → finished。
 */
struct ActorUnloadFinishedEvent {
    std::uintptr_t scene{};
    std::uintptr_t actor{};
};

/**
 * @brief Actor 驻留状态变更通知（Loaded ↔ Unloaded）
 *
 * 每当 actor 的驻留状态发生确定性的变化时发布：
 * - loaded=true  → 资源已加载，GPU 数据就绪，外部系统可以消费
 * - loaded=false → 资源已卸载，GPU 数据已释放，外部系统应停止消费
 *
 * 外部系统（Optics / Mechanics / Vision）应统一监听此事件，
 * 而不是分别监听 ActorLoadFinishedEvent / ActorUnloadFinishedEvent。
 *
 * 发布方：GeometrySystem（on_load_finished / on_unload_finished）
 */
struct ActorResidencyChangedEvent {
    std::uintptr_t scene{};
    std::uintptr_t actor{};
    bool           loaded{};   // true=已加载(Loaded), false=已卸载(Unloaded)
};

/**
 * @brief 八叉树粗筛碰撞候选对事件（SceneSystem → MechanicsSystem）
 *
 * SceneSystem 在每帧重建八叉树后，通过 collect_pairs() 收集所有
 * AABB 重叠的 actor 对，打包为本事件通过 IEventBus 同步发布。
 * 订阅方（如 MechanicsSystem）被动接收候选对列表，进行窄相检测。
 *
 * 设计意图：
 * - SceneSystem 只负责空间划分与粗筛，不直接依赖任何物理系统
 * - 物理系统通过事件订阅解耦，可独立替换或禁用
 * - 使用 EventBus 同步发布：SceneSystem(priority=88) 早于
 *   MechanicsSystem(priority=75)，同帧内保证数据就绪
 */
struct BroadphasePairsEvent {
    std::uintptr_t scene{};
    std::vector<std::pair<std::uintptr_t, std::uintptr_t>> pairs;
};
}  // namespace Corona::Events
