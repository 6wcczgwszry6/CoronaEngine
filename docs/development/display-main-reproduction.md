# main 分支 Display 旧图像回收问题：实测复现

测试时间：2026-09-29，Asia/Shanghai。

## 结论

在 main 提交 `0301294ff5ee7b46af50628dbf90252161c19de7` 上实际复现了 Display 访问已回收 ImageStorage 句柄的异常。第一次运行使用未修改的 main 源码；第二次只增加 11 行诊断日志，确认回收发生在最后使用之后第 241 个 Optics 更新周期。

第二次运行中，主窗口从第 70 帧一直正常渲染到第 603 帧。打开同一台相机的独立窗口后，新窗口从第 604 帧开始收到图像，主窗口继续使用缓存的第 603 帧。第 844 帧回收主窗口旧图像，约 3.385 毫秒后 Display 访问同一句柄并退出更新循环。之后 Optics 仍输出到第 1140 帧，直到测试主动请求关闭引擎。

两次运行都没有出现 `device lost`，都通过正常退出接口完成关闭。

## 实测环境

| 项目 | 本次配置 |
| --- | --- |
| 分支 | `main`，与测试时 `origin/main` 相同 |
| 工作区 | `C:/Users/Zero/.codex/worktrees/display-main-repro/CoronaEngine` |
| Horizon | 主分支锁定的 `2d8883bb6b03fba438fd17ac70563ffe37b0e7ff` |
| 构建 | Windows x64、MSVC、RelWithDebInfo、完整 `corona_engine` |
| GPU | NVIDIA GeForce RTX 2070 with Max-Q Design，8 GB，驱动 592.82 |
| 场景 | 厨房工程，299 个场景代理对象 |
| 相机 | `view1`，ID `scene.ini#camera0`，Vision / `path_tracing`，深度 16 |
| 输出大小 | 主窗口本次为 1536×832；独立相机窗口为 1536×825 |
| 传输配置 | `CORONA_VISION_DISABLE_ZERO_COPY=0`；未强制关闭默认传输路径，未据此断言实际用了零拷贝 |

另有一台保存于工程中的相机 `acceptance-view2`，始终没有打开；测试中只有主窗口和 `view1` 独立窗口两个显示窗口。

## 复现条件和步骤

必要条件是：一个仍存活的窗口已经让 Display 缓存过场景图像；随后没有相机继续更新这个窗口的渲染目标，而 Display 仍会使用旧缓存；Optics 的更新计数继续前进超过 240 次。

本次可重复操作如下，自动化调用了与界面“打开相机视图”相同的公共编辑器接口：

1. 构建并运行上述 main 版本，不加入本次生命周期修复。
2. 打开测试厨房工程：`E:/work/corona/CoronaEngine/.superpowers/sdd/2026-09-29-main-display-repro/project`。
3. 先保持 `view1` 的独立窗口关闭，让相机在主窗口实际渲染。提供的工程已设置 `camera0.view_open=false`；第二次测试还明确设置了 `[world] type=creative`，使主窗口正常进入编辑界面。
4. 等主窗口至少收到一帧场景图像。本次对照阶段从第 70 帧持续到第 603 帧，没有回收，也没有异常。
5. 在场景相机列表中打开 **同一台 `view1`** 的独立视图，保持主窗口和独立相机窗口同时打开。不要再给主窗口绑定另一台持续渲染的相机。
6. 保持运行。当旧目标距最后一次被 Optics 取用超过 240 个更新周期时，触发异常。镜头可以保持静止，无需反复开关窗口。

本机两次运行从打开独立窗口到异常约为 105 秒和 56 秒。时间受渲染速度与初始化影响，**不是固定等待两秒，也不是程序启动后的第 241 帧**。

如果主窗口从未缓存过场景图像，或仍有相机持续向它输出，则不满足这次复现的条件。仅“同时有两个窗口”并不足以保证触发。

## 直接证据

第二次运行的窗口与图像：

| 目标 | surface | image handle | 帧 |
| --- | --- | --- | --- |
| 主窗口 | `0x60a58` | `2640365284656` | 最后更新 603 |
| 独立相机窗口 | `0xe0a3e` | `2640365284496` | 首次更新 604 |
| 主窗口旧目标回收 | `0x60a58` | `2640365284656` | 当前 844，闲置 241 |

```text
15:43:20.972962286 MainDisplayRepro evict surface=0x60a58 image=2640365284656 last=603 current=844 idle=241
15:43:20.976347277 System 'Display' update threw an exception; requesting engine shutdown: Attempt to acquire write handle for unoccupied object ID: 2640365284656
15:43:20.976362010 DisplaySystem: update loop exited
15:43:32.713711588 MainDisplayRepro produce surface=0xe0a3e image=2640365284496 frame=900
```

日志及验证结果：

- [未修改 main 的运行日志](E:/work/corona/CoronaEngine/.superpowers/sdd/2026-09-29-main-display-repro/baseline.stdout.log)
- [第二次运行的诊断日志](E:/work/corona/CoronaEngine/.superpowers/sdd/2026-09-29-main-display-repro/trace.stdout.log)
- [自动核对的结果](E:/work/corona/CoronaEngine/.superpowers/sdd/2026-09-29-main-display-repro/verified-results.json)
- [临时诊断日志补丁](E:/work/corona/CoronaEngine/.superpowers/sdd/2026-09-29-main-display-repro/diagnostic-logs.patch)
- [第二次运行的初始工程配置](E:/work/corona/CoronaEngine/.superpowers/sdd/2026-09-29-main-display-repro/scene.trace-input.ini)

第一次运行在公共 API 加载工程后，主窗口前端仍停留在启动页；第二次使用明确的 creative 工程配置，确认主窗口路由为 `#/`、相机窗口路由为 `#/CameraView?...`，仍复现同一问题。因此证据同时覆盖原版异常和完整编辑界面的回收链路。这里通过日志确认 Display 停止更新，未通过系统截图作黑屏外观验收。

## 工作区与构建说明

测试在独立 main 工作区进行，原目录的 `svgf_magic` 修复、PT 切换改动和历史 stash 均未动。临时诊断日志已移除；本任务没有把修复提交或合入 main。

首次完整构建发现着色器生成器未处理工作区路径 `display-main-repro` 中的连字符。仅对构建目录中的 24 个生成头文件修正 C++ 符号拼写；脚本核对了嵌入的着色器字节完全相同，未修改 main 或 Horizon 的源码。对应记录在 [构建路径处理结果](E:/work/corona/CoronaEngine/.superpowers/sdd/2026-09-29-main-display-repro/generated-path-workaround.json)。
