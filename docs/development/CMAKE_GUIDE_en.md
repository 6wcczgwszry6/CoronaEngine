# CMake Build System Guide

This document provides a comprehensive guide to the CoronaEngine's CMake build system. It covers the build workflow, configuration presets, options, and custom modules that orchestrate the compilation process.

## 1. Build Workflow

The project uses `CMakePresets.json` to simplify the configuration and build process.

### Prerequisites
- CMake 4.0 or higher.
- A compatible C++ compiler (MSVC, Clang, or GCC).
- Ninja (recommended for faster builds).

### Step-by-Step Guide (Windows with MSVC)

1.  **Open a terminal** in the project's root directory.

2.  **Configure the project** using the `ninja-msvc` preset. This generates the build files in the `build/` directory.
    ```powershell
    cmake --preset ninja-msvc
    ```

3.  **Build the project** using a build preset. For example, to build the Debug configuration:
    ```powershell
    cmake --build --preset msvc-debug
    ```
    Other available build presets include `msvc-release`, `msvc-relwithdebinfo`, and `msvc-minsizerel`.

4.  **Run the output**. The executables will be located in `build/<Configuration>/<Preset>/`, for example: `build/Debug/ninja-msvc/`.

## 2. CMake Presets (`CMakePresets.json`)

The `CMakePresets.json` file defines a set of standard configurations for different platforms and toolchains.

### Configure Presets
- `ninja-msvc`: For Windows with Ninja and the MSVC compiler (Recommended on Windows).
- `ninja-clang`: For Windows with Ninja and the Clang compiler.
- `vs2022`: For Windows with the Visual Studio 2022 generator.
- `ninja-linux-gcc`: For Linux with Ninja and GCC.
- `ninja-linux-clang`: For Linux with Ninja and Clang.
- `ninja-macos`: For macOS with Ninja.

### Build Presets
Build presets correspond to each configure preset for different build types (`Debug`, `Release`, `RelWithDebInfo`, `MinSizeRel`). For example:
- `msvc-debug`
- `msvc-release`
- `clang-debug`
- `linux-gcc-release`

## 3. Build Options (`misc/cmake/corona_options.cmake`)

These options allow you to customize the build by enabling or disabling features. You can set them during the configure step with the `-D` flag (e.g., `cmake --preset ninja-msvc -DBUILD_CORONA_EXAMPLES=OFF`).

- `BUILD_CORONA_RUNTIME=ON`: Build the main engine executable.
- `BUILD_CORONA_EXAMPLES=ON`: Build the example programs located in the `examples/` directory.
- `CORONA_CHECK_PY_DEPS=ON`: At configure time, validate that all Python dependencies from `requirements.txt` are installed.
- `CORONA_AUTO_INSTALL_PY_DEPS=ON`: If `CORONA_CHECK_PY_DEPS` is on and dependencies are missing, attempt to install them automatically via pip.

## 4. Custom CMake Modules (`misc/cmake/`)

The build system is modularized into several helper scripts located in `misc/cmake/`.

- `corona_options.cmake`: Defines the main build options (see section above).
- `corona_python.cmake`: Manages the discovery of the embedded Python interpreter and its dependencies.
- `corona_third_party.cmake`: Manages all external third-party libraries using `FetchContent`. This ensures dependencies are downloaded and configured automatically.
- `corona_compile_config.cmake`: Sets project-wide compiler flags, C++ standard, and preprocessor definitions.
- `corona_collect_module.cmake`: Provides the `corona_collect_module()` function, which automatically discovers and adds source and header files from a given module directory, simplifying target definitions.
- `corona_runtime_deps.cmake`: Provides the `corona_runtime_deps()` function, which copies necessary runtime dependencies (like DLLs from third-party libraries) to the target's output directory.
- `corona_editor.cmake`: Contains helpers for packaging editor-specific assets (not currently in active use).

## 5. Dependency Management

### Third-Party Libraries
All external dependencies are managed via `FetchContent` in `misc/cmake/corona_third_party.cmake`. This approach avoids the need for manual installation of libraries. Key dependencies include:
- **Core**: ktm, nlohmann_json, spdlog
- **Windowing & Rendering**: glfw, volk, VulkanMemoryAllocator, glslang, SPIRV-Cross
- **Asset Loading**: assimp, stb

### Internal Dependencies
The engine is built as a static library (`CoronaEngine`). The main runtime executable and examples link against this library. The `add_subdirectory(src)` command in the root `CMakeLists.txt` is responsible for building the core engine module.
