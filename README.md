# CoronaEngine

CoronaEngine 是一个以 CMake、Conan 2 和 C++20 构建的 Windows x64 引擎工程。它在同一构建图中集成锁定版本的 [Horizon](.workspace/Horizon)，并可选构建 CEF 编辑器、示例、资源系统和 CUDA 驱动的 Vision 功能。

本文档面向首次在本仓库构建的开发者。所有命令均在仓库根目录执行。

## 构建模型

~~~text
uv / Python
    └─ tools/dev.py
        ├─ 校验或准备 .workspace/Horizon
        ├─ Conan install（一个依赖图、一个 MSVC profile）
        ├─ 生成 Conan toolchain 与开发环境
        └─ CMake configure / build
             └─ add_subdirectory(.workspace/Horizon)
~~~

- Conan 是第三方库版本、二进制变体和 CMake package target 的唯一所有者；CMake 只查找并链接 Conan 生成的 target。
- Horizon 是锁定提交的源码子项目，不是由 Conan 安装的 Horizon 包。父工程和 Horizon 共用一次 Conan 解析结果、profile 与 generators 目录。
- 构建目录按配置隔离：<code>build/conan/debug</code>、<code>build/conan/release</code>、<code>build/conan/relwithdebinfo</code> 和 <code>build/conan/minsizerel</code>。不要把不同配置的生成文件混用。

## 环境要求

当前工作流仅支持 **Windows x64**。

| 工具 | 要求 |
| --- | --- |
| Git | 克隆源码及管理锁定的 Horizon 工作区 |
| [uv](https://docs.astral.sh/uv/) | 管理 Python 环境和 Conan；无需单独安装 Python 或 Conan |
| CMake | 3.29 或更高版本 |
| Ninja | 必须在 PATH 中；工程使用 Ninja Multi-Config |
| Visual Studio 或 Build Tools | 安装“使用 C++ 的桌面开发”、MSVC x64/x86 工具集与 Windows SDK |
| CUDA Toolkit | 仅 Vision / Ocarina / Vision Hotfix 需要；安装后应存在 CUDA_PATH |

先在新的 PowerShell 中确认基础工具可用：

~~~powershell
git --version
uv --version
cmake --version
ninja --version
~~~

首次进入仓库后同步开发环境：

~~~powershell
uv sync --frozen
~~~

项目要求 Python 3.11 及以上；如果本机没有合适版本，uv 会按自身配置处理 Python 安装。首次同步、Conan 安装或编译依赖耗时较长属于正常情况。

### VS Code / CMake Tools

使用 VS Code 的 CMake Tools 时，在设置中将 <code>CMake: Use VS Developer Environment</code> 设为 <code>always</code>，或加入用户设置：

~~~json
"cmake.useVsDeveloperEnvironment": "always"
~~~

否则 CMake Tools 单独启动的进程可能没有 MSVC 和 Windows SDK 环境，常见表现为 <code>fatal error C1083</code> 或找不到 <code>stddef.h</code> 等标准头文件。

## 快速开始

~~~powershell
# 查看分支、Horizon 锁定提交、Conan 与 CMake preset
uv run --frozen python tools/dev.py status

# 完整准备并构建默认引擎示例（Debug）
uv run --frozen python tools/dev.py build corona_engine --configuration Debug
~~~

<code>build</code> 会依次准备 Horizon、运行 Conan、配置 CMake，再构建指定 target。默认的 <code>corona_engine</code> 是 <code>examples/engine</code> 中的可执行示例；构建后请从 CMake 报告的 target 输出目录运行它，以保留生成的运行时文件。

已成功配置过同一配置目录后，可使用较快的增量构建：

~~~powershell
# 只构建已配置的指定 target
uv run --frozen python tools/dev.py build-fast corona_engine --configuration Debug

# 构建该配置中的全部默认 target
uv run --frozen python tools/dev.py build-fast all --configuration Debug
~~~

配置名称必须使用 <code>Debug</code>、<code>Release</code>、<code>RelWithDebInfo</code> 或 <code>MinSizeRel</code>。脚本参数使用此大小写；对应的 CMake preset 名称为小写。

## 日常命令

| 命令 | 用途 |
| --- | --- |
| <code>uv run --frozen python tools/dev.py install --configuration Debug</code> | 只准备 Horizon 并运行 Conan install |
| <code>uv run --frozen python tools/dev.py configure --configuration Debug</code> | Conan install 后执行 CMake configure |
| <code>uv run --frozen python tools/dev.py build &lt;target&gt; --configuration Debug</code> | 完整安装、配置、构建流程 |
| <code>uv run --frozen python tools/dev.py build-fast &lt;target&gt; --configuration Debug</code> | 只构建现有 CMake cache；不会自动配置 |
| <code>uv run --frozen python tools/dev.py rebuild &lt;target&gt; --configuration Debug</code> | 删除该配置的构建目录后重新构建 |
| <code>uv run --frozen python tools/dev.py update --configuration Debug</code> | 在 Horizon 工作区干净时更新锁定源码和 Conan 解析结果 |
| <code>uv run --frozen python tools/dev.py clean</code> | 删除本仓库的 build、install、out、dist；执行前确认不需要其中产物 |

构建测试 target 时，名称中包含 <code>test</code> 的 target 会让脚本启用 Conan 的 <code>with_tests</code> 选项。例如：

~~~powershell
uv run --frozen python tools/dev.py build corona_resource_tests --configuration Debug
ctest --test-dir build/conan/debug -C Debug --output-on-failure
~~~

工作流脚本自身的快速回归测试不需要原生构建：

~~~powershell
uv run --frozen python -m unittest tools/test_workflow.py
~~~

## 通过 CMake preset 构建

脚本是推荐入口。若使用 CMake Tools，选择与所需配置对应的 <code>debug</code>、<code>release</code>、<code>relwithdebinfo</code> 或 <code>minsizerel</code> configure preset，再执行 Configure 和 Build。根 CMakeLists.txt 会调用开发 bootstrap，生成并加载对应配置的 Conan toolchain。

不要把 [.workspace/Horizon/README.md](.workspace/Horizon/README.md) 中的独立 Horizon preset 或工具命令直接套用于父工程：它们用于单独构建 Horizon，目录结构和 target family 与 CoronaEngine 不同。父工程只应使用根目录的 preset 和 tools/dev.py。

## 功能与依赖注意事项

### Horizon 工作区

<code>.workspace/horizon.lock.json</code> 固定 Horizon 的仓库地址、分支和具体提交。开发脚本会：

1. 在 <code>.workspace/Horizon</code> 不存在时克隆并检出锁定提交；
2. 校验远程地址和当前 HEAD 必须与锁文件一致；
3. 不会为了匹配锁文件而覆盖 Horizon 的本地修改。

因此，不要手动切换该目录的分支或提交后再运行父工程构建。需要升级 Horizon 时使用 <code>tools/dev.py update</code>；若 Horizon 工作区有未提交修改，更新会被拒绝。提交锁文件变更前，应先确认 CoronaEngine 的 Conan 图仍能统一所有包的版本、ABI、MSVC runtime 和 CUDA 选项。

父工程固定启用 Horizon tools，关闭其 examples、tests 和 benchmarks；Horizon 的 Ocarina 与 Vision Hotfix 随 <code>CORONA_BUILD_VISION</code> 开关启用。不要在 CoronaEngine 的构建流程中对 <code>.workspace/Horizon</code> 再运行一次 <code>conan install</code>，否则会产生不一致的依赖图和 generators 目录。

### 第三方库

新增或升级依赖时遵循以下边界：

- CoronaEngine 自己使用的包：在根 [conanfile.py](conanfile.py) 声明版本和 option，在 CMake 中查找并链接导出的 target。
- Horizon 新增的、且会被 CoronaEngine 当前启用功能使用的包：除了 Horizon 自己的 conanfile.py 外，也要在根 conanfile.py 声明。因为集成构建只解析父工程的 Conan 图。
- 仅由当前被关闭的 Horizon target family 使用的包，不应无条件带入父工程依赖图。
- target 名称不兼容时，在 [misc/cmake/corona_third_party.cmake](misc/cmake/corona_third_party.cmake) 添加兼容别名或明确的 target 校验；只有 Horizon 使用时，通常应由 Horizon 的 CMake 模块完成查找。
- 不要在 CMake 中重新引入 FetchContent、ExternalProject、file(DOWNLOAD) 或另一套包管理器来下载同一第三方库。

根 Conan recipe 的主要 feature option 包括 <code>with_editor</code>、<code>with_examples</code>、<code>with_tests</code>、<code>with_vision</code>、<code>with_oidn</code> 与 <code>with_cef</code>。它们会生成相应的 CMake cache 变量。当前 tools/dev.py 会从 target 名称推断 tests、Vision 与 OIDN；需要新增独立 feature 时，应同步调整 Conan option、脚本映射和 Horizon 子项目开关，而不是只手改 CMake cache。

### CUDA 与 Vision

<code>CORONA_BUILD_VISION</code> 默认根据 <code>CUDA_PATH</code> 或 CMake 的 CUDA Toolkit 检测结果启用。显式开启 Vision 但未检测到 CUDA 时，CMake 会警告并关闭 Vision，避免在深层 Vision/Horizon 子目录失败。

若需要 Ocarina 或 Vision Hotfix，请先确认：

~~~powershell
echo $env:CUDA_PATH
~~~

能输出有效 CUDA Toolkit 目录，再配置和构建。CUDA、Conan 的 Vision option 与 Horizon 的 Ocarina option 必须保持一致。

### 运行时文件

构建成功不代表可以只复制一个 .exe 到其他目录运行。示例 target 的构建后步骤会部署所需内容，包括：

- 嵌入式 Python 运行时和相关 DLL；
- TBB、Assimp 等运行时库；
- FFmpeg 的带 ABI 版本 DLL；
- 启用 CEF 时的 libcef、子进程、资源包和 locales；
- 启用编辑器时的 CabbageEditor 前端及资源；
- 需要时的 Horizon/Helicon 运行时依赖和项目 assets。

请从 target 输出目录运行，或使用正式安装/打包流程。移动程序时必须连同构建后部署的内容一起移动。

## 常见问题

### CMake 找不到标准头文件

确认 VS / Build Tools 安装了 C++ 工作负载和 Windows SDK。若在 VS Code 中发生，设置 <code>cmake.useVsDeveloperEnvironment</code> 为 <code>always</code>，重启 VS Code 后重新 Configure。

### 找不到 Conan toolchain 或 dev_build_environment.cmake

不要手工删除 generators 目录的一部分。重新运行：

~~~powershell
uv run --frozen python tools/dev.py configure --configuration Debug
~~~

若 cache 指向其他源码目录或配置目录，使用 <code>rebuild</code> 重新创建该配置的构建目录。

### Horizon 锁定提交不匹配或工作区有修改

先检查：

~~~powershell
uv run --frozen python tools/dev.py status
git -C .workspace/Horizon status --short
~~~

保留、提交或自行处理本地 Horizon 改动，再决定是否执行 <code>tools/dev.py update</code>。不要通过删除锁文件或强制重置工作区来绕过检查。

### 首次构建很慢

首次需要下载或构建 Conan 二进制包，并生成 shader、CEF/编辑器和运行时文件。后续在相同配置目录下优先使用 <code>build-fast</code>。

## 相关入口

- 根构建入口：[CMakeLists.txt](CMakeLists.txt)
- 开发工作流：[tools/dev.py](tools/dev.py)
- Conan 依赖和 feature option：[conanfile.py](conanfile.py)
- Horizon 锁文件：[.workspace/horizon.lock.json](.workspace/horizon.lock.json)
- Horizon 独立构建指南：[.workspace/Horizon/README.md](.workspace/Horizon/README.md)
