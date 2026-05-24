# 项目架构指南

本文档高层次地概述了 CoronaEngine 的架构，重点介绍其核心组件、系统设计和数据流。

## 1. 核心设计哲学

CoronaEngine 被设计为一个模块化、多线程、数据驱动的游戏引擎。其架构深受以下原则影响：

- **模块化 (Modularity)**：功能被封装在独立的“系统”（Systems）中（例如，显示、声学、力学系统）。
- **数据驱动设计 (Data-Oriented Design)**：逻辑与数据分离。系统操作数据，通信通常通过事件实现。
- **多线程 (Multi-threading)**：每个系统都在其专用的线程上运行，以最大化性能并防止瓶颈。

## 2. 关键组件

### `Engine` 类 (`include/corona/engine.h`)
`Engine` 类是整个应用程序的中央协调器。它负责：
- **生命周期管理**: 管理主要的 `initialize()`、`run()` 和 `shutdown()` 序列。
- **系统注册**: 发现并注册所有可用的系统。
- **主循环**: 驱动主应用循环，以固定速率（120 FPS）进行心跳并管理帧计时。
- **服务访问**: 提供对核心内核服务的访问。

### `Kernel::KernelContext` (来自 CoronaFramework)
引擎构建于 `CoronaFramework` 之上，后者提供了一个基础的 `KernelContext`。这个单例对象充当中央服务中心，提供：
- **`SystemManager`**: 管理所有已注册系统的生命周期（初始化、执行、关闭）。
- **`Logger`**: 集中式日志服务。
- **`EventBus` / `EventStream`**: 用于同步和异步的系统间通信机制。

### 系统 (`src/systems/`)
系统是引擎功能的构建块。每个系统：
- 继承自 `Kernel::SystemBase`。
- 实现特定的逻辑（例如，渲染、物理、音频）。
- 在自己的线程中运行。
- 被分配一个优先级，该优先级决定了其初始化顺序。

## 3. 系统架构与生命周期

### 基于优先级的初始化
系统根据其优先级按特定顺序进行初始化，以确保满足依赖关系。当前的优先级顺序是：
1.  `DisplaySystem` (100)
2.  `OpticsSystem` (90)
3.  `GeometrySystem` (85)
4.  `AnimationSystem` (80)
5.  `MechanicsSystem` (75)
6.  `AcousticsSystem` (70)

这由 `SystemManager` 自动管理。系统通过重写 `get_priority()` 方法来定义其优先级。

### 多线程执行
- 当 `Engine::run()` 被调用时，`SystemManager` 会为每个注册的系统启动一个专用线程。
- 然后，每个系统的 `update()` 方法会在其自己的线程内被反复调用。
- 引擎的主循环负责高层编排和帧率控制，但核心工作在各个系统内并行进行。

### 生命周期钩子
每个系统都实现了 `SystemBase` 中的以下方法：
- `initialize(ISystemContext* ctx)`: 在启动时调用一次。用于资源分配和设置。
- `update()`: 主要的工作方法，在系统线程内每帧调用。
- `shutdown()`: 在应用程序退出时调用一次。用于清理。

## 4. 通信与数据流

### 事件总线 (Event Bus)
系统被设计为解耦的，主要通过事件驱动机制进行通信。
- `KernelContext` 提供了一个全局的 `EventBus` 和 `EventStream`。
- 系统可以发布事件（例如 `EntityCreated`、`CollisionDetected`），而无需知道哪些其他系统在监听。
- 其他系统可以订阅特定的事件类型以作出相应反应。
- 事件定义是位于 `include/corona/events/` 中的强类型结构体。

## 5. 目录结构

- `include/corona/`: 引擎核心组件的公共头文件。
- `src/engine.cpp`: `Engine` 类的实现。
- `include/corona/systems/`: 所有系统的公共头文件。
- `src/systems/src/<module>/`: 每个系统模块的私有实现。
- `examples/`: 包含演示如何使用引擎的示例应用程序。
- `misc/cmake/`: 存放驱动构建过程的模块化 CMake 辅助脚本。
