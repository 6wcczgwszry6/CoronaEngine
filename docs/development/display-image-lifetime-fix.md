# Display 图像生命周期修复

日期：2026-09-29。对应 [原始交接文档](display-stale-image-handle-handoff.md)。

## 根因与复现

在保留已有 PT 模式切换改动的工作区中，为分配、缓存、回收、呈现添加临时日志后复现：

- surface `0x30080a` 发布图像 `1926686868032`，最后使用帧为 147。
- Optics 在帧 388 回收该图像，间隔 **241 帧**。
- 约 13 毫秒后，Display 对同一句柄 `acquire_write()`，抛出 `Attempt to acquire write handle for unoccupied object ID` 并退出。

SurfaceFrameCoordinator 保护窗口销毁，但窗口仍存在时，Optics 的空闲图像回收未进入这个协议。Display 缓存及其局部快照只有数字句柄，不能保证对应分配仍存活。Storage 还会复用数字句柄，所以单纯改用 `try_acquire_write()` 无法排除误读另一张图像。

## 修改

- 新增 `PublishedImage`：每次分配建立独立、可复制的生命周期标记，复用 SurfaceFrameCoordinator 的 lease/retirement 实现。
- Optics 和 UI 发布事件携带该标记；Display 缓存与快照保留它，先取得图像 lease 再访问 Storage，并持有到 consumed receipt 回写结束。外层窗口 lease 的顺序不变。
- 生产者先 retire，阻止所有旧快照继续访问；等已进入的访问结束，再等待 GPU 生产/消费完成、清空 ImageDevice、释放 Storage 条目。新分配重置旧图像和 receipt。
- 退役的 Optics 层按缺失层处理，清除本次合成中的旧尺寸和 viewport，使用透明图像，允许 UI 独立呈现。
- 空闲阈值仍为 240；未改变 zero-copy 策略。临时日志探针已移除。

## 验证

新增 `PublishedImageTests` 覆盖：240 帧内最后一帧可访问，退役后的缓存/快照拒绝访问，数字地址复用不串图，退役等待最后写回，UI 与窗口生命周期独立，以及第二张图获取异常时释放全部图像/窗口 lease。

相关 CTest 项全部通过（4/4）：`PublishedImageTests`、`UiSurfaceRemovalRaceTests`、`UiSurfaceLifecycleTests`、`VisionRenderModeConfigTests`。新增文件通过 clang-format 检查，`git diff --check` 通过；独立并发安全审查未发现阻塞问题。

移除临时探针后，`corona_engine` 及上述相关测试目标的 RelWithDebInfo 完整构建成功。最终构建和测试日志分别保存在 `.superpowers/sdd/2026-09-27-kitchen-acceptance-fixes/display-final-build.log` 与 `display-clean-regression-tests.log`。测试引擎均已关闭，运行目录的 `CoronaEditor.ini` 已恢复。

实际 kitchen 场景使用 1536×825 的相机窗口，另保留主窗口：

| 运行 | 回收边界 | 修复后呈现证据 |
|---|---|---|
| 强制关闭 zero-copy | 72 → 313 | 活跃视图持续呈现到帧 1305；实时→渐进→实时切换、相机关闭与重新打开均执行；旧主窗口 UI 帧持续到 19424 |
| 默认路径（未强制关闭 zero-copy） | 162 → 403 | 活跃视图持续呈现到帧 1306；退役旧窗口按 UI-only 呈现，UI 帧持续到 17337 |

关闭后重新打开相机时，确实复用了旧主窗口释放的数字图像句柄 `1508492060608`；旧主窗口仍保持 UI-only。两次修复后运行均没有 Display 更新异常或 device lost，并记录了正常 `Engine shutdown complete`。相同的日志验收脚本在修复前失败、修复后通过。

## 限制与本地证据

- Windows 原生画面捕获两次报 `SetIsBorderRequired failed: 不支持此接口 (0x80004002)`，因此未完成 GPU 合成画面的视觉验收。呈现日志证明提交代码路径持续运行，不是显示器扫描输出的硬件证明。
- 默认路径没有强制禁用 zero-copy，但退出时 `bridges=0, interop_submissions=0`；不能据此宣称已验证成功导入外部显存的实际 zero-copy 分支。
- 最早一次修复前尝试发生 Vulkan device lost，另存为 `before.stdout.log`；用于根因证明的是第二次独立复现 `before2.stdout.log`。
- 未做长时间资源压力测试。已有的实时／渐进 PT 模式改动已单独提交为 `429a1019`；本修复与其分开提交，历史 stash 保持不变。

本地证据目录：`.superpowers/sdd/2026-09-29-display-image-lifetime/`，包含 `before2.stdout.log`、`after.stdout.log`、`default.stdout.log`、对应 `.summary.json`、启动/驱动/验收脚本，以及修改前的 `optics.before.cpp`。这些是本地忽略文件，不随 Git 克隆传递。
