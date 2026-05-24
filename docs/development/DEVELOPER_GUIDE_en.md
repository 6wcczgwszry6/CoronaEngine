# Developer Guide

Welcome to the CoronaEngine! This guide is designed to help you get started with the development, from setting up your environment to understanding the core architecture and contributing to the project.

## 1. Getting Started: Setup and Build

Before you can start coding, you need to set up your development environment and build the project.

### Prerequisites
- **Git**: For version control.
- **CMake (4.0+)**: Our build system generator.
- **A C++ Compiler**: MSVC (on Windows), Clang, or GCC.
- **Ninja**: For faster builds (recommended).

### Build Process
The project uses a straightforward, preset-based CMake workflow. For a detailed explanation, please refer to the [CMake Build System Guide](./CMAKE_GUIDE_en.md).

Here is the quick version for Windows with MSVC:

1.  **Clone the repository**:
    ```sh
    git clone <repository-url>
    cd CoronaEngine
    ```

2.  **Configure CMake**:
    This command generates the build files in the `build/` directory.
    ```powershell
    cmake --preset ninja-msvc
    ```

3.  **Build the project**:
    This command compiles the project in Debug mode.
    ```powershell
    cmake --build --preset msvc-debug
    ```

Executables will be available in the `build/` directory which is the cmake target directory.

## 2. Core Architecture

To contribute effectively, it's important to understand the engine's design. The architecture is modular, multi-threaded, and data-oriented. For a deep dive, see the [Project Architecture Guide](./ARCHITECTURE_en.md).

### Key Concepts
- **`Engine` Class**: The central orchestrator that manages the application's lifecycle.
- **`KernelContext`**: A service hub from `CoronaFramework` that provides core services like logging, event management, and system management.
- **Systems**: Independent, thread-safe modules that encapsulate specific functionalities (e.g., `DisplaySystem`, `MechanicsSystem`). Each system runs on its own thread.
- **Event-Driven Communication**: Systems are decoupled and communicate by publishing and subscribing to events via a central event bus.

## 3. Common Workflow: Adding a New System

One of the most common tasks is adding a new system to the engine. Here’s how you do it:

1.  **Create the Header File**:
    Create `include/corona/systems/my_new_system.h`. The class must inherit from `Kernel::SystemBase`.
    ```cpp
    #pragma once
    #include <corona/kernel/system/system_base.h>
    
    namespace Corona::Systems {
      class MyNewSystem : public Kernel::SystemBase {
      public:
        // Override required methods
        auto get_name() const -> std::string_view override { return "MyNewSystem"; }
        auto get_priority() const -> i16 override { return 88; } // Choose a unique priority
    
        void initialize(ISystemContext* ctx) override;
        void update() override;
        void shutdown() override;
      };
    } // namespace Corona::Systems
    ```

2.  **Create the Implementation File**:
    Create `src/systems/src/mynewsystem/my_new_system.cpp` and implement the lifecycle methods.

3.  **Register the System**:
    In `src/engine.cpp`, find the `Engine::register_systems()` method and add your new system.
    ```cpp
    // In Engine::register_systems()
    #include <corona/systems/my_new_system.h> // Add include at the top
    
    // ... inside the method
    sys_mgr->register_system(std::make_shared<Systems::MyNewSystem>());
    logger->info("  - MyNewSystem registered (priority 88)");
    ```

4.  **Rebuild the project**, and the engine will automatically initialize and run your new system on its own thread.

## 4. Code Style and Conventions

We enforce a consistent code style to maintain readability and quality. All code should adhere to the rules defined in our `.clang-format` and `.clang-tidy` files.

- **Formatting**: Based on Google Style (4-space indents, no tabs).
- **Naming**: Uses `CamelCase` for types and `snake_case` for functions and variables.

Before committing any code, please run the formatting script:
```powershell
./code-format.ps1
```

For complete details, please read the [Code Style Guide](./CODE_STYLE_en.md).

Happy coding!
