# Conan 开发脚本使用说明

本文说明 `tools/` 目录下两个 PowerShell 辅助脚本的用途和用法：

- `tools/dev.ps1`：日常开发入口，用于安装依赖、配置 CMake、构建目标、清理项目本地生成物。
- `tools/conan-cache.ps1`：本地 Conan 缓存维护工具，用于查看、更新、删除或清空全局 Conan cache。

建议在仓库根目录下用 PowerShell 运行这些脚本。脚本默认假设 `git`、`conan`、`cmake` 已经在 `PATH` 中，并使用 `conan/profiles/` 下的 Windows MSVC profile。

## `tools/dev.ps1`

`dev.ps1` 封装了 CoronaEngine 常用的 Conan + CMake 工作流。它会导出仓库内的 Conan 本地 recipe，把依赖图安装到 `build/conan`，导入 Conan 生成的构建环境，然后通过 CMake 配置或构建目标。

基本形式：

```powershell
.\tools\dev.ps1 <command> [target] [-Configuration Debug|Release|RelWithDebInfo|MinSizeRel]
```

默认值：

- 命令：`status`
- 目标：`corona_engine`
- 配置：`Debug`
- 构建目录：`build/conan`
- CMake configure preset：`conan-default`

### 命令

| 命令 | 行为 | 适用场景 |
| --- | --- | --- |
| `status` | 输出 `git status --short --branch`、`conan --version`、`cmake --list-presets`。 | 快速检查环境和工作区状态。 |
| `install` | 导出本地 recipe，并用所选 MSVC profile 执行 `conan install .`。 | 只刷新依赖，不重新配置 CMake。 |
| `configure` | 执行 `install`，导入 `build/conan/generators/conanbuild.bat`，然后运行 `cmake --preset conan-default`。 | 生成或刷新 CMake 构建树。 |
| `build` | 执行 `install`、`configure`，然后在 `build/conan` 中构建指定目标。 | 依赖或 CMake 配置可能变化后的常规构建路径。 |
| `build-fast` | 只导入现有 Conan 构建环境并构建目标，不执行 install/configure。 | 依赖和 CMake cache 已经有效时的快速重编译。 |
| `rebuild` | 删除 `build/` 和 `install/`，再执行 `install`、`configure`、`build`。 | 处理陈旧 CMake cache、生成器变化、构建树损坏等问题。 |
| `update` | 清理可更新的本地包缓存，执行带 `--update` 的 Conan install，然后重新配置 CMake。 | 拉取依赖的新修订版本，但不立即构建。 |
| `clean` | 直接删除仓库内被 Git ignore 的本地构建、缓存、生成物。 | 将项目本地状态重置到接近干净 checkout 的状态。 |

常用示例：

```powershell
.\tools\dev.ps1 status
.\tools\dev.ps1 install
.\tools\dev.ps1 configure
.\tools\dev.ps1 build
.\tools\dev.ps1 build CoronaEngine
.\tools\dev.ps1 build corona_engine -Configuration Release
.\tools\dev.ps1 build-fast corona_engine
.\tools\dev.ps1 rebuild corona_engine
.\tools\dev.ps1 update
.\tools\dev.ps1 clean
```

### `clean` 的清理范围

`clean` 会在仓库根目录执行：

```powershell
git clean -fdX
```

这表示只删除 Git ignore 规则覆盖的本地文件和目录，不删除已跟踪文件，也不删除未被 ignore 的未跟踪源码或工作文件。它通常会清理：

- `build/`、`build-*`、`install/`、`out/`、`dist/`
- `cmake-build-*`
- `CMakeUserPresets.json`、`CMakeCache.txt`、`CMakeFiles/`
- `.vs/`、`.cache/`、`.pytest_cache/`
- `.codegraph/` 中未跟踪的本地索引内容
- 日志、临时文件、Python cache、工具运行缓存

`clean` 不清理全局 Conan cache。需要清空全局 Conan cache 时，使用：

```powershell
.\tools\conan-cache.ps1 clear
```

### Target 与 Configuration

`-Configuration` 同时决定 Conan profile 和 CMake 构建配置：

| Configuration | Conan profile |
| --- | --- |
| `Debug` | `conan/profiles/windows-msvc-debug` |
| `Release` | `conan/profiles/windows-msvc-release` |
| `RelWithDebInfo` | `conan/profiles/windows-msvc-relwithdebinfo` |
| `MinSizeRel` | `conan/profiles/windows-msvc-minsizerel` |

命令后的第一个位置参数是 CMake target：

```powershell
.\tools\dev.ps1 build corona_engine -Configuration RelWithDebInfo
```

脚本会把剩余参数作为 target 数组接收，但真正传给 CMake build 的是 `Target[0]`。完整 target 数组只用于在 Conan install 前推导需要打开的 Conan options。

### 根据 Target 自动推导的 Conan Options

CoronaEngine 会根据 target 名称自动开启部分根包选项：

| target 名称包含 | 自动添加的 Conan option |
| --- | --- |
| `test` | `-o &:with_tests=True` |
| `vision` 或 `oidn` | `-o &:with_vision=True` |
| `oidn` | `-o &:with_oidn=True` |

例如，target 名称中包含 `vision` 时，脚本会在 install 阶段先启用 Vision 相关依赖路径，再进入 CMake configure。

### 本地 Recipes

每次 Conan install 前，脚本都会导出以下本地 recipes：

- `conan/recipes/ktm`
- `conan/recipes/pfr`
- `conan/recipes/slang`
- `conan/recipes/vulkan-memory-allocator`
- `conan/recipes/astc-encoder`
- `conan/recipes/cef-binary`
- `conan/recipes/ffmpeg`
- `conan/recipes/horizon`

`horizon/0.5.0` 会通过 CoronaEngine 仓库内的 bootstrap recipe 导出。开发者电脑上不需要存在 sibling Horizon checkout；当本地 Conan cache 中没有 Horizon 包时，Conan 会根据该 recipe 从 Horizon Git 远端拉取源码并构建包。

```powershell
$env:HORIZON_CONAN_GIT_REF = "conan-migration"
$env:HORIZON_CONAN_GIT_URL = "https://github.com/CoronaEngine/Horizon.git"
```

以上两个环境变量都是可选项。默认 Git URL 是 `https://github.com/CoronaEngine/Horizon.git`，默认 ref 是 `conan-migration`。

如果当前 Conan 全局状态中注册了 `horizon/0.5.0` editable，`dev.ps1` 和 `conan-cache.ps1 update` 会直接失败并提示先运行 `conan editable remove horizon/0.5.0`，避免构建意外指向本地源码 checkout。

### 构建树安全检查

`build-fast` 会检查 `build/conan/CMakeCache.txt` 是否存在，并确认该 cache 属于当前仓库。如果 cache 指向其他源码目录或其他 cache 目录，脚本会要求改用 `rebuild`。

`rebuild` 只会删除 `build/` 和 `install/`。删除前脚本会解析绝对路径，并拒绝删除仓库根目录之外的路径。

### Python Shim

脚本启动时会创建 `build/conan/tool-shims` 并将其加入 `PATH` 前部。如果系统中没有 `python` 命令，但存在 `python3.14` 或 `python3`，脚本会写入一个很小的 `python.cmd` shim。这样可以兼容某些 Conan recipe 或工具对 `python` 命令名的依赖。

`clean` 命令不会创建这个 shim。

## `tools/conan-cache.ps1`

`conan-cache.ps1` 用于直接维护本地 Conan cache。它不会配置或构建 CMake。它操作的是当前用户账号的全局 Conan cache，因此删除和清空操作需要谨慎。

基本形式：

```powershell
.\tools\conan-cache.ps1 <list|update|remove|clear> [package-or-reference] [options]
```

默认值：

- 命令：`list`
- 配置：`Debug`
- 不传 package/reference 时的匹配模式：`*`

### 常用示例

```powershell
.\tools\conan-cache.ps1 list
.\tools\conan-cache.ps1 list slang
.\tools\conan-cache.ps1 list slang -Version 2026.10
.\tools\conan-cache.ps1 list -Reference slang/2026.10
.\tools\conan-cache.ps1 list slang -Version 2026.10 -PackageId "*"

.\tools\conan-cache.ps1 update
.\tools\conan-cache.ps1 update slang
.\tools\conan-cache.ps1 update slang -Version 2026.10
.\tools\conan-cache.ps1 update -Reference slang/2026.10

.\tools\conan-cache.ps1 remove slang/2026.10 -DryRun
.\tools\conan-cache.ps1 remove slang/2026.10
.\tools\conan-cache.ps1 remove slang -Version 2026.10 -Force

.\tools\conan-cache.ps1 clear -DryRun
.\tools\conan-cache.ps1 clear
```

### Reference 与匹配规则

脚本会根据输入构造 Conan cache 匹配模式：

| 输入 | 生成的匹配模式 |
| --- | --- |
| 不传 package，也不传 `-Reference` | `*` |
| `slang` | `slang/*` |
| `slang -Version 2026.10` | `slang/2026.10` |
| `slang -Version 2026.10 -User user -Channel channel` | `slang/2026.10@user/channel` |
| `slang -Version 2026.10 -PackageId "*"` | `slang/2026.10:*` |
| `-Reference slang/2026.10` | `slang/2026.10` |

如果位置参数本身已经包含 `/`、`@`、`*`、`#` 或 `:`，脚本会把它视为 reference-like pattern，并直接使用。

输入限制：

- 位置参数 package 和 `-Reference` 不能同时使用。
- `-Reference` 不能和 `-Version`、`-User`、`-Channel` 同时使用。
- `-User` 和 `-Channel` 必须成对提供。
- `-PackageId` 必须搭配 package 或 `-Reference`。
- `-PackageId` 和 `-PackageQuery` 只支持 `list` 和 `remove`，不支持 `update`。
- `clear` 不接受 package/reference 过滤参数；需要过滤删除时使用 `remove`。

### `list`

`list` 执行：

```powershell
conan list <pattern> --cache
```

如果提供了 `-PackageQuery`，脚本会继续传递为 `--package-query`。

### `update`

`update` 会先导出与 `dev.ps1` 相同的本地 recipes，然后执行带 `--update` 的 Conan install。

如果输入可以解析为一个具体 reference，脚本会直接安装该 reference：

```powershell
conan install --requires <reference> ...
```

如果输入为空、包含通配符、包含 revision，或包含 package id，脚本会改为更新 CoronaEngine 的完整依赖图：

```powershell
conan install . ...
```

如果可以从输入中推导出包名，脚本会传递 `--update <name>`；否则传递普通的 `--update`。

### `remove`

`remove` 会先列出匹配的 cache 条目，然后执行：

```powershell
conan remove <pattern> --confirm
```

安全行为：

- 不带 `-Force` 或 `-DryRun` 时，脚本会要求输入 `YES`。
- `-DryRun` 会追加 Conan 的 `--dry-run`，不会真正删除条目。
- `-Force` 会跳过确认并删除匹配项。

当 pattern 中包含 `*`，或你不确定会匹配多少条目时，建议先使用 `-DryRun`。

### `clear`

`clear` 是一键清空全局 Conan cache 的显式命令。它不需要确认，也不接受 package/reference 过滤参数。

预览清空效果：

```powershell
.\tools\conan-cache.ps1 clear -DryRun
```

直接清空：

```powershell
.\tools\conan-cache.ps1 clear
```

它实际执行的是：

```powershell
conan remove "*" --confirm
```

这会影响当前用户账号的全局 Conan cache，不只影响当前仓库。清空后，下次 install/build 会重新下载或重新构建依赖。

### 应该使用哪个脚本

| 需求 | 推荐命令 |
| --- | --- |
| 常规依赖安装 | `.\tools\dev.ps1 install` |
| 常规配置 | `.\tools\dev.ps1 configure` |
| 常规构建 | `.\tools\dev.ps1 build <target>` |
| 快速本地重编译 | `.\tools\dev.ps1 build-fast <target>` |
| 清理构建树后重建 | `.\tools\dev.ps1 rebuild <target>` |
| 重置项目本地构建/缓存生成物 | `.\tools\dev.ps1 clean` |
| 更新完整依赖图并重新配置 | `.\tools\dev.ps1 update` |
| 查看本地 Conan cache | `.\tools\conan-cache.ps1 list ...` |
| 更新某个包或 reference | `.\tools\conan-cache.ps1 update ...` |
| 删除陈旧 cache 条目 | `.\tools\conan-cache.ps1 remove ...` |
| 清空全局 Conan cache | `.\tools\conan-cache.ps1 clear` |
