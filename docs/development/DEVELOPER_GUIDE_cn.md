# 开发者指南

欢迎来到 CoronaEngine！本指南旨在帮助您开始进行开发，从设置环境到理解核心架构，再到为项目做出贡献。

## 1. 入门：设置与构建

在开始编码之前，您需要设置开发环境并构建项目。

### 先决条件
- **Git**: 用于版本控制。
- **CMake (4.0+)**: 我们的构建系统生成器。
- **C++ 编译器**: MSVC (在 Windows 上)、Clang 或 GCC。
- **Ninja**: 用于加速构建（推荐）。

### 构建流程
项目使用基于预设的、简单直接的 CMake 工作流。有关详细说明，请参阅 [CMake 构建系统指南](./CMAKE_GUIDE_cn.md)。

以下是适用于 Windows 和 MSVC 的快速版本：

1.  **克隆仓库**:
    ```sh
    git clone <repository-url>
    cd CoronaEngine
    ```

2.  **配置 CMake**:
    此命令会在 `build/` 目录中生成构建文件。
    ```powershell
    cmake --preset ninja-msvc
    ```

3.  **构建项目**:
    此命令以 Debug 模式编译项目。
    ```powershell
    cmake --build --preset msvc-debug
    ```

可执行文件将位于 `build/` 对应的cmake目标目录中。

## 2. 核心架构

为了有效地做出贡献，理解引擎的设计至关重要。该架构是模块化、多线程和数据驱动的。要深入了解，请参阅 [项目架构指南](./ARCHITECTURE_cn.md)。

### 关键概念
- **`Engine` 类**: 管理应用程序生命周期的中央协调器。
- **`KernelContext`**: 来自 `CoronaFramework` 的服务中心，提供日志、事件管理和系统管理等核心服务。
- **系统 (Systems)**: 独立的、线程安全的模块，封装了特定的功能（例如 `DisplaySystem`、`MechanicsSystem`）。每个系统都在自己的线程上运行。
- **事件驱动通信**: 系统是解耦的，通过中央事件总线发布和订阅事件来进行通信。

## 3. 常见工作流：添加一个新系统

最常见的任务之一是向引擎添加一个新系统。操作方法如下：

1.  **创建头文件**:
    创建 `include/corona/systems/my_new_system.h`。该类必须继承自 `Kernel::SystemBase`。
    ```cpp
    #pragma once
    #include <corona/kernel/system/system_base.h>
    
    namespace Corona::Systems {
      class MyNewSystem : public Kernel::SystemBase {
      public:
        // 重写必要的方法
        auto get_name() const -> std::string_view override { return "MyNewSystem"; }
        auto get_priority() const -> i16 override { return 88; } // 选择一个唯一的优先级
    
        void initialize(ISystemContext* ctx) override;
        void update() override;
        void shutdown() override;
      };
    } // namespace Corona::Systems
    ```

2.  **创建实现文件**:
    创建 `src/systems/src/mynewsystem/my_new_system.cpp` 并实现生命周期方法。

3.  **注册系统**:
    在 `src/engine.cpp` 中，找到 `Engine::register_systems()` 方法并添加您的新系统。
    ```cpp
    // 在 Engine::register_systems() 中
    #include <corona/systems/my_new_system.h> // 在文件顶部添加 include
    
    // ... 在方法内部
    sys_mgr->register_system(std::make_shared<Systems::MyNewSystem>());
    logger->info("  - MyNewSystem registered (priority 88)");
    ```

4.  **重新构建项目**，引擎将自动在其自己的线程上初始化并运行您的新系统。

## 4. 代码风格与约定

我们强制执行一致的代码风格以保持可读性和质量。所有代码都应遵守 `.clang-format` 和 `.clang-tidy` 文件中定义的规则。

- **格式化**: 基于 Google 风格（4空格缩进，无制表符）。
- **命名**: 类型使用 `CamelCase`，函数和变量使用 `snake_case`。

在提交任何代码之前，请运行格式化脚本：
```powershell
./code-format.ps1
```

有关完整详情，请阅读 [代码风格指南](./CODE_STYLE_cn.md)。

编码愉快！
