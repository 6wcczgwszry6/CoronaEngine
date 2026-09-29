# Display 图像句柄异常交接

整理日期：2026-09-29。以下运行证据均来自 2026-09-28，时间为北京时间（UTC+8）。本文用于新会话接手定位和修复；本轮只整理文档，没有修改 Display 实现，也没有重新运行引擎。

## 1. 问题与影响

加载 kitchen、使用 Vision PT 渲染一段时间后，Display 更新线程抛出异常并退出：

```text
System 'Display' update threw an exception; requesting engine shutdown:
Attempt to acquire write handle for unoccupied object ID: <handle>
DisplaySystem: update loop exited
```

**已确认的影响：显示线程停止，Optics 渲染线程仍可能继续产帧，进程不会立即整体退出。** 因此，只观察渲染帧号、FPS 或 Optics 日志会误以为引擎仍正常工作。性能验收必须同时核对 Display 是否仍在呈现新的光学帧。

异常表示申请 ImageStorage 写句柄时，对应条目已不处于占用状态。它本身尚不能证明 GPU 显存已经被错误访问，也不能直接判定是 optics 层还是 UI 层触发。

此问题在新增“实时 PT / 渐进 PT”开关之前已有多次记录，不能归因于该开关。尚未做提交二分，未确定最早引入版本。

## 2. 当前工作区：接手前先保留

| 项目 | 整理时状态 |
|---|---|
| 仓库 | `E:/work/corona/CoronaEngine` |
| 分支 | `svgf_magic` |
| HEAD | `67a9cad903931213c961d03b1c6f6129e64a3b98` |
| Horizon 工作目录 | `E:/work/corona/CoronaEngine/.workspace/Horizon` |
| Horizon HEAD | `2d8883bb6b03fba438fd17ac70563ffe37b0e7ff` |
| 构建目录 | `E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo` |
| 引擎程序 | `E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/examples/engine/corona_engine.exe` |
| 引擎运行状态 | 已关闭 |

工作区有上一任务留下的 **12 个已跟踪文件修改**，实现 PT 实时/渐进切换、UI 入口和相关测试，尚未提交。其中包括 `optics_system.cpp`、`shared_data_hub.h`、`vision/src/base/mgr/pipeline.cpp` 以及前端文件。接手时先检查 `git status` / `git diff`，保留这些改动；不要直接清理工作区或覆盖整个文件。

更早一批用户改动另外保存在 stash 中，与当前 PT 开关改动不同：

```text
stash@{0}: On svgf_magic: Before kitchen PT benchmark at 8378e140 - 2026-09-28
stash commit: 72d86b0c03f1387bdced8925d8a5a4cff5d631df
```

这份 stash 尚未应用或删除。此前性能测量用的临时探针已经撤回，不能假定当前程序仍会生成 `frames.trace.csv`。

## 3. 已有复现证据

| 版本 / 运行 | Display 异常时间 | 报错句柄 | 说明 |
|---|---|---:|---|
| `cc26b69d`，第一次测试 | 16:41:54.931627 | 2539713341376 | 25 秒采样中途失败，整次性能样本排除 |
| `cc26b69d`，第二次测试 | 16:53:09.782976 | 2565884951808 | 25 秒采样结束约 10.08 秒后失败 |
| `67a9cad9`，profile | 19:32:27.112837 | 2021238704704 | 基于干净提交，仅临时插桩；有效采样缩短为 6.43 秒 / 49 个完整且已呈现帧 |
| `67a9cad9` + PT 开关，UI 验收 1 | 20:37:32.230270 | 2859246929584 | Display 退出；之后正常关闭引擎 |
| `67a9cad9` + PT 开关，UI 验收 2 | 20:41:09.125848 | 2949554668176 | 发生在渐进模式运行时完成加载之前 |

第二次 UI 验收的渐进运行时直到 20:41:41 才记录加载完成，故这次 Display 异常并非由已开始运行的渐进累积直接触发。第二次尝试以主视口为主、没有再次创建独立相机窗口，仍然复现；“不开多个窗口”并不是已验证有效的规避办法。

### 最有价值的帧号关联

`cc26b69d` 两次运行的原始 trace 有相同规律：

| 运行 | 持续被呈现的旧主窗口 optics 帧号 | 异常前最后完成的相机处理所用 Optics 帧号 | 差值 |
|---|---:|---:|---:|
| 第一次 | 83 | 324 | 241 |
| 第二次 | 112 | 353 | 241 |

旧窗口 surface 分别为 `4983172`、`2361748`；当时另一个相机 surface 分别为 `4850528`、`1442430`。首次运行最后一条相机呈现记录仍为 323，但相机处理已完成 324，随后 Display 抛错。这些是 Optics 更新/发布使用的帧号，不是 PT 采样累积计数。

异常之后，原始 trace 中分别还有 **2042 / 393 条新的 camera scope**，直接证明 Display 退出后渲染仍继续。

差值 241 与“空闲超过 240 帧后回收”的代码高度吻合。这是强线索，尚不是带有句柄分配、释放和访问调用栈的完整因果证明。

## 4. 初步原因：空闲回收与 Display 缓存寿命不一致

目前最值得优先验证的路径：

1. Optics 向某个 surface 发布一个 `image_handle`。
2. Display 把该数值句柄保存到 `surface_states_[surface].optics`，在后续显示更新中继续使用。
3. 该 surface 不再产生新的 Optics 图像，但窗口或 UI 仍存在，Display 缓存的 optics 层仍然非零。
4. Optics 的全局帧号继续前进；旧 target 空闲超过 240 帧后，其 ImageStorage 条目被回收。
5. Display 再次对缓存句柄调用 `acquire_write()`，遇到未占用条目，异常逃出本次 update，显示线程停止。

### 直接相关代码

以下行号以整理时工作区为准，后续改动可能使其移动。

| 位置 | 已看到的行为 |
|---|---|
| [Display PendingLayer](E:/work/corona/CoronaEngine/include/corona/systems/display/display_system.h:61) | 缓存数值 `image_handle`、帧号和尺寸；该结构没有持有 ImageStorage 访问句柄 |
| [handle_optics_frame](E:/work/corona/CoronaEngine/src/systems/display/display_system.cpp:166) | 接收 `OpticsFrameReadyEvent` 并缓存 optics 图像句柄 |
| [Display 状态快照](E:/work/corona/CoronaEngine/src/systems/display/display_system.cpp:584) | 把 `surface_states_` 复制到局部快照，再进行本帧访问 |
| [Display 图像访问](E:/work/corona/CoronaEngine/src/systems/display/display_system.cpp:649) | 在 `begin_frame()` 回调中分别对 optics / UI 句柄调用 `acquire_write()`；任一访问都可能抛错 |
| [evict_idle_surface_targets](E:/work/corona/CoronaEngine/src/systems/optics/optics_system.cpp:3218) | `(frame_index - last_used_frame) > kSurfaceTargetIdleEvictFrames` 时直接 `image_storage().deallocate(target.image_handle)`，并删除 target |
| [空闲阈值](E:/work/corona/CoronaEngine/include/corona/systems/optics/optics_system.h:306) | `kSurfaceTargetIdleEvictFrames = 240` |
| [surface 移除处理](E:/work/corona/CoronaEngine/src/systems/display/display_system.cpp:138) | 有 surface retirement 与清除缓存逻辑，应对照检查空闲 target 回收是否进入同一协议 |
| [SurfaceFrameCoordinator](E:/work/corona/CoronaEngine/include/corona/systems/display/surface_frame_coordinator.h) | 已存在 surface lease / retirement 协调，修复时需理解并复用现有边界 |
| [系统更新异常处理](E:/work/corona/CoronaEngine/src/kernel/system/system_base.cpp:235) | 捕获异常并退出当前系统更新循环；日志虽然写“requesting engine shutdown”，实际观测不是全进程立即退出 |

**已看到：**空闲 target 回收函数本身没有清除 Display 缓存或向 Display 发送失效通知。

**尚未证明：**报错的每个句柄是否都恰好由这个回收函数释放；当前回收与 `SurfaceFrameCoordinator` 的完整并发时序；是否还有 UI 图像释放、surface 重建或句柄复用路径造成同类异常。不能仅凭异常字符串把问题定性为 GPU use-after-free。

## 5. 复现场景与操作参考

环境为 Windows、MSVC 19.43 / RelWithDebInfo、NVIDIA RTX 2070 Max-Q、驱动 592.82。

场景项目位于：

[vision_scene_1](E:/work/corona/CoronaEngine/.superpowers/sdd/2026-09-27-kitchen-acceptance-fixes/projects/vision_scene_1/scene.ini)

历史测量设置：kitchen 299 个 actor，静止相机，1536×825，1 spp，最大深度 16，`CORONA_VISION_DISABLE_ZERO_COPY=1`。旧提交上的 `path_tracing` 实际会强制运行 SVGF。最近主视口 UI 验收的实际视口为 1536×832，因此不要把全部运行都写成相同分辨率。

建议先沿用已出现问题的操作序列，而不是先追求新的最小场景：

1. 从上述构建目录的 `examples/engine` 启动引擎并打开该 kitchen 项目。
2. 使用 Vision 实时 PT。历史基准中通过独立相机视图渲染，并保留原主窗口；相机 ID 为 `scene.ini#camera0`。
3. 保持相机静止，观察原窗口的 optics 帧号是否停止更新，而其他相机继续推进。
4. 超过旧 target 最后使用帧号至少 241 个 Optics 更新后，检查异常与实际呈现记录。不要只等待固定 25 秒：触发条件很可能是帧数，运行速度和初始化耗时会改变墙钟时间。
5. 保留完整日志、surface / handle / frame 对照和退出状态。测试结束关闭引擎；不要让异常后的后台渲染继续占用 GPU。

这是历史复现流程，尚未整理成稳定、自动判定的最小复现。最近仅以主视口操作也复现过，说明独立相机窗口未被证明是必要条件。

可复用的本地辅助程序：

- [构建辅助脚本](E:/work/corona/CoronaEngine/.superpowers/sdd/2026-09-27-kitchen-acceptance-fixes/build.ps1)：已配置工作区的构建入口之一。
- [CEF API 驱动辅助](E:/work/corona/CoronaEngine/.superpowers/sdd/2026-09-27-kitchen-acceptance-fixes/acceptance_runtime.py)：使用本机 9222 调试端口；历史环境使用 `C:/Users/Zero/miniconda3/envs/coronaengine-dev/python.exe`，默认 Python 缺少 websocket 依赖。
- [cc26 基准驱动](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/kitchen-pt-benchmark-cc26b69d-20260928/benchmark.py)：可参考相机视图创建流程，但依赖当时的临时探针，不应直接当作当前可运行验收脚本。
- [最近 UI 检查脚本](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/pt-mode-acceptance-20260928/check-ui.py)：验证 UI 与相机 API 状态，**没有证明 Display 持续呈现正常画面**。

引擎常规日志位于 `E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/examples/engine/logs/`。Nsight 启动的 profile 运行中 stdout 为空，应使用下节保存的 `engine-internal.log`。

## 6. 原始材料索引

所有链接均为本机现存文件；`cmake-build-relwithdebinfo` 下证据属于本地构建产物，不保证随 Git 克隆传递。新会话若仍使用此工作区可直接读取，清理构建目录前应保留这些证据。

| 材料 | 路径 |
|---|---|
| cc26 第一次异常 | [engine.stdout.log](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/kitchen-pt-benchmark-cc26b69d-20260928/attempt1/engine.stdout.log:5542) |
| cc26 第一次帧记录 | [frames.trace.csv](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/kitchen-pt-benchmark-cc26b69d-20260928/attempt1/frames.trace.csv) |
| cc26 第二次异常 | [engine.stdout.log](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/kitchen-pt-benchmark-cc26b69d-20260928/engine.stdout.log:6330) |
| cc26 第二次帧记录 | [frames.trace.csv](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/kitchen-pt-benchmark-cc26b69d-20260928/frames.trace.csv) |
| cc26 测量说明 | [report.md](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/kitchen-pt-benchmark-cc26b69d-20260928/report.md) |
| 干净 67a9 基线 profile 异常 | [engine-internal.log](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/kitchen-profile-latest-20260928/engine-internal.log:3654) |
| profile 测量说明 | [report.md](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/kitchen-profile-latest-20260928/report.md) |
| 新 PT 开关验收，第一次异常 | [engine.stdout.log](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/pt-mode-acceptance-20260928/engine.stdout.log:6462) |
| 新 PT 开关验收，第二次异常 | [engine2.stdout.log](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/pt-mode-acceptance-20260928/engine2.stdout.log:6387) |
| 新 PT 开关验收说明 | [report.md](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/pt-mode-acceptance-20260928/report.md) |
| 保存的界面截图 | [render-mode-menu.png](E:/work/corona/CoronaEngine/cmake-build-relwithdebinfo/pt-mode-acceptance-20260928/render-mode-menu.png) |

截图保存于 20:41:56，异常发生于 20:41:09。它是 **CEF UI 层截图，不含最终 GPU 合成画面**，不能根据黑色背景宣称出现了渲染黑屏，也不能用它证明异常后画面仍能正常刷新。此前截图在对话内显示不可靠，新会话可直接打开文件。

`frames.trace.csv` 无表头，字段为 `kind,time,ms,handle,frame,width,height,updates,paths`。其中 `camera` 行的 handle 是相机句柄，`present` 行的 handle 是 surface；不要把它们直接当作异常中的 ImageStorage 句柄。`present` 是当时在提交呈现命令之后加入的探针，能证明代码走到呈现提交处，不是显示器扫描输出的硬件证明。

## 7. 新会话的调查重点与验收建议

建议先建立句柄的完整时间线：在分配、发布、空闲回收和 Display 获取处关联记录 `surface`、`image_handle`、optics/UI 层、发布帧、`last_used_frame`、当前 Optics 帧号。确认具体异常句柄的释放位置，再选择修复方案。

重点检查缓存快照与回收之间的并发窗口，以及 surface lease 是否真正覆盖了 image 的存活期。单纯先检查“存在”再获取仍可能有竞态；单纯增大 240 帧阈值只能延后触发。安全获取、缓存失效、引用持有或退休通知都是候选方向，需要按现有生命周期协议评估；本文不指定已经验证过的修复方案。

修复验收至少应覆盖：

- 原复现流程运行超过旧 target 空闲阈值，Display 不退出，活跃视图持续提交新的 optics 帧。
- 仍保留 UI 的旧 surface 停止接收 Optics 图像后，正确处理其最后一帧，避免访问已回收条目。
- 相机窗口打开、关闭、切换、重新激活，以及实时 / 渐进模式切换。
- surface 销毁与快照访问交错时，没有悬空访问、错误帧复用、永久等待或资源持续增长。
- zero-copy 关闭的原复现路径先通过，再验证正常默认路径；无条件关闭 zero-copy 不作为根因修复。
- 单独核对线程存活、呈现帧号和实际画面；不要仅以 Optics FPS 或“无崩溃进程”判定通过。

此前只做过有限调查，没有修复 Display，也没有调试器级别的所有权证明。新会话若进入 Horizon，需先阅读 [Horizon AGENTS.md](E:/work/corona/CoronaEngine/.workspace/Horizon/AGENTS.md)；其默认调查范围有限，不应无关扩展到旧 Ocarina 模块。

## 8. 可复制给新会话的任务

请阅读 `E:/work/corona/CoronaEngine/docs/development/display-stale-image-handle-handoff.md`，定位并修复 kitchen PT 运行时 Display 的 `Attempt to acquire write handle for unoccupied object ID` 异常。先验证空闲 surface target 在第 241 帧回收与 Display 缓存句柄的因果关系，不把推测当成已证实根因。保留工作区已有的 PT 实时/渐进切换改动及历史 stash；添加针对真实生命周期问题的回归验证，确认显示线程和呈现持续正常，测完关闭引擎，并报告修改、验证结果和剩余限制。
