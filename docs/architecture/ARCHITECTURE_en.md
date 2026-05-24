# Project Architecture Guide

This document provides a high-level overview of the CoronaEngine's architecture, focusing on its core components, system design, and data flow.

## 1. Core Philosophy

CoronaEngine is designed as a modular, multi-threaded, and data-oriented game engine. Its architecture is heavily influenced by the following principles:

- **Modularity**: Functionality is encapsulated within independent "Systems" (e.g., Display, Acoustics, Mechanics).
- **Data-Oriented Design**: Logic and data are separated. Systems operate on data, and communication is often achieved through events.
- **Multi-threading**: Each system runs on its own dedicated thread to maximize performance and prevent bottlenecks.

## 2. Key Components

### `Engine` Class (`include/corona/engine.h`)
The `Engine` class is the central orchestrator of the entire application. It is responsible for:
- **Lifecycle Management**: Manages the main `initialize()`, `run()`, and `shutdown()` sequence.
- **System Registration**: Discovers and registers all available systems.
- **Main Loop**: Drives the main application loop, ticking at a fixed rate (120 FPS) and managing frame timing.
- **Service Access**: Provides access to core kernel services.

### `Kernel::KernelContext` (from CoronaFramework)
The engine is built upon the `CoronaFramework`, which provides a foundational `KernelContext`. This singleton object acts as a central service hub, offering:
- **`SystemManager`**: Manages the lifecycle (initialization, execution, shutdown) of all registered systems.
- **`Logger`**: A centralized logging service.
- **`EventBus` / `EventStream`**: Mechanisms for synchronous and asynchronous inter-system communication.

### Systems (`src/systems/`)
Systems are the building blocks of the engine's functionality. Each system:
- Inherits from `Kernel::SystemBase`.
- Implements specific logic (e.g., rendering, physics, audio).
- Runs in its own thread.
- Is assigned a priority that determines its initialization order.

## 3. System Architecture and Lifecycle

### Priority-Based Initialization
Systems are initialized in a specific order based on their priority, ensuring that dependencies are met. The current priority order is:
1.  `DisplaySystem` (100)
2.  `OpticsSystem` (90)
3.  `GeometrySystem` (85)
4.  `AnimationSystem` (80)
5.  `MechanicsSystem` (75)
6.  `AcousticsSystem` (70)

This is managed automatically by the `SystemManager`. A system defines its priority by overriding the `get_priority()` method.

### Multi-threaded Execution
- When `Engine::run()` is called, the `SystemManager` starts a dedicated thread for each registered system.
- Each system's `update()` method is then called repeatedly within its own thread.
- The engine's main loop is responsible for high-level orchestration and frame rate control, but the core work happens in parallel within the systems.

### Lifecycle Hooks
Each system implements the following methods from `SystemBase`:
- `initialize(ISystemContext* ctx)`: Called once at startup. Used for resource allocation and setup.
- `update()`: The main workhorse method, called every frame within the system's thread.
- `shutdown()`: Called once upon application exit. Used for cleanup.

## 4. Communication and Data Flow

### Event Bus
Systems are designed to be decoupled and communicate primarily through an event-driven mechanism.
- The `KernelContext` provides a global `EventBus` and `EventStream`.
- Systems can publish events (e.g., `EntityCreated`, `CollisionDetected`) without needing to know which other systems are listening.
- Other systems can subscribe to specific event types to react accordingly.
- Event definitions are strongly-typed structs located in `include/corona/events/`.

## 5. Directory Structure

- `include/corona/`: Public headers for the engine's core components.
- `src/engine.cpp`: Implementation of the `Engine` class.
- `include/corona/systems/`: Public headers for all systems.
- `src/systems/src/<module>/`: Private implementation for each system module.
- `examples/`: Contains example applications demonstrating how to use the engine.
- `misc/cmake/`: Home to the modular CMake helper scripts that drive the build process.
