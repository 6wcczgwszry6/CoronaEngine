# CMake 构建系统指南

本文档全面介绍了 CoronaEngine 的 CMake 构建系统，涵盖了构建流程、配置预设、选项以及用于编排编译过程的自定义模块。

## 1. 构建流程

项目使用 `CMakePresets.json` 来简化配置和构建过程。

### 先决条件
- CMake 4.0 或更高版本。
- 兼容的 C++ 编译器（MSVC、Clang 或 GCC）。
- Ninja（推荐，可加速构建）。

### 分步指南 (Windows + MSVC)

1.  在项目根目录中**打开一个终端**。

2.  使用 `ninja-msvc` 预设**配置项目**。这将在 `build/` 目录中生成构建文件。
    ```powershell
    cmake --preset ninja-msvc
    ```

3.  使用构建预设**编译项目**。例如，要构建 Debug 配置：
    ```powershell
    cmake --build --preset msvc-debug
    ```
    其他可用的构建预设包括 `msvc-release`、`msvc-relwithdebinfo` 和 `msvc-minsizerel`。

4.  **运行程序**。可执行文件将位于 `build/<Configuration>/<Preset>/` 目录下，例如：`build/Debug/ninja-msvc/`。

## 2. CMake 预设 (`CMakePresets.json`)

`CMakePresets.json` 文件为不同的平台和工具链定义了一套标准配置。

### 配置预设 (Configure Presets)
- `ninja-msvc`: 适用于 Windows，使用 Ninja 和 MSVC 编译器（Windows 平台推荐）。
- `ninja-clang`: 适用于 Windows，使用 Ninja 和 Clang 编译器。
- `vs2022`: 适用于 Windows，使用 Visual Studio 2022 生成器。
- `ninja-linux-gcc`: 适用于 Linux，使用 Ninja 和 GCC。
- `ninja-linux-clang`: 适用于 Linux，使用 Ninja 和 Clang。
- `ninja-macos`: 适用于 macOS，使用 Ninja。

### 构建预设 (Build Presets)
构建预设对应于每种配置预设的不同构建类型（`Debug`、`Release`、`RelWithDebInfo`、`MinSizeRel`）。例如：
- `msvc-debug`
- `msvc-release`
- `clang-debug`
- `linux-gcc-release`

## 3. 构建选项 (`misc/cmake/corona_options.cmake`)

这些选项允许您通过启用或禁用某些功能来定制构建。您可以在配置阶段使用 `-D` 标志来设置它们（例如：`cmake --preset ninja-msvc -DBUILD_CORONA_EXAMPLES=OFF`）。

- `BUILD_CORONA_RUNTIME=ON`: 构建主引擎可执行文件。
- `BUILD_CORONA_EXAMPLES=ON`: 构建 `examples/` 目录中的示例程序。
- `CORONA_CHECK_PY_DEPS=ON`: 在配置时，验证 `requirements.txt` 中的所有 Python 依赖项是否已安装。
- `CORONA_AUTO_INSTALL_PY_DEPS=ON`: 如果 `CORONA_CHECK_PY_DEPS` 开启且存在缺失的依赖项，则尝试通过 pip 自动安装它们。

## 4. 自定义 CMake 模块 (`misc/cmake/`)

构建系统被模块化为位于 `misc/cmake/` 中的几个辅助脚本。

- `corona_options.cmake`: 定义了主要的构建选项（见上一节）。
- `corona_python.cmake`: 管理嵌入式 Python 解释器及其依赖项的发现。
- `corona_third_party.cmake`: 使用 `FetchContent` 管理所有外部第三方库（如 spdlog、glfw）。这确保了依赖项能够被自动下载和配置。
- `corona_compile_config.cmake`: 设置项目范围的编译器标志、C++ 标准和预处理器定义。
- `corona_collect_module.cmake`: 提供 `corona_collect_module()` 函数，该函数可自动发现并添加给定模块目录中的源文件和头文件，从而简化了目标定义。
- `corona_runtime_deps.cmake`: 提供 `corona_runtime_deps()` 函数，该函数负责将必要的运行时依赖项（如第三方库的 DLL）复制到目标输出目录。
- `corona_editor.cmake`: 包含用于打包编辑器特定资源的辅助函数（目前未积极使用）。

## 5. 依赖管理

### 第三方库
所有外部依赖都通过 `misc/cmake/corona_third_party.cmake` 中的 `FetchContent` 进行管理。这种方法避免了手动安装库的需要。关键依赖项包括：
- **核心**: ktm, nlohmann_json, spdlog
- **窗口与渲染**: glfw, volk, VulkanMemoryAllocator, glslang, SPIRV-Cross
- **资产加载**: assimp, stb

### 内部依赖
引擎本身被构建为一个静态库（`CoronaEngine`）。主运行时可执行文件和示例程序都链接到此库。根目录 `CMakeLists.txt` 中的 `add_subdirectory(src)` 命令负责构建核心引擎模块。
