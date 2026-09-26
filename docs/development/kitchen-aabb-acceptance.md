# Kitchen AABB 优化验收（2026-09-27）

结论：**静止场景性能目标和现有自动化回归通过；整体验收未通过。** 已在编辑器复现场景总范围不更新、嵌入场景切换 SVGF 加载失败。独立运行时几何传播及图像对照尚缺有效端到端证据。

测试对象为 `ee00024e` 上的未提交 AABB 优化，保留用户现有工作。CLion RelWithDebInfo / MSVC 14.44.35207，RTX 3070 Ti。本轮未修改 AABB 生产实现；只修复测试运行配置和过时的测试夹具。不能将本轮发现直接归因为此次优化引入；未对所有失败项运行优化前二进制对照。

## 1. 构建及全量测试

- 按 `.agents/skills/clion-cmake-relwithdebinfo/scripts/configure.ps1` 重新生成，按 `.agents/skills/clion-build-corona-engine/scripts/build.ps1` 构建正式引擎成功。
- 显式编译 CTest 注册的全部 37 个测试目标；同一 CLion CMake、Ninja、MSVC 环境，未清理或更换构建目录。
- 撤回临时计时代码、重新构建正式引擎及测试后，全量 CTest **37/37 通过、0 失败、0 跳过**，耗时 4.89 秒。
- 设置 `CORONA_RUN_GPU_SMOKE=1`，实际运行 UI 多 surface GPU 冒烟测试，覆盖 1/3/16 surface、突发、resize/minimize/restore、100 次生命周期及 shutdown drain。该测试不是 kitchen 多相机／多渲染运行时几何传播测试。
- `VisionGeometryGpuResourceTests` 包含 AABB 生产 helper 回归及 CUDA 资源集成；检查输出未出现内部 `SKIP`。

本轮修复了两个测试设施问题：

1. 六个 Vision 测试的工作目录从写死 `bin/$<CONFIG>` 改为实际 Vision 插件输出目录。当前 Ninja 单配置构建为 `bin`，不存在原先的 `bin/RelWithDebInfo`。
2. `VisionInteropLifetimeTests` 的假回执仍用 `empty()` 表示空状态，且给“空回执”设置了非零 serial；生产接口在历史提交 `82fe89a7` 已改为 `serial != 0`。改用真实 `Horizon::SubmitReceipt` 和默认空回执后，原来的“所有等待先于释放”断言通过；未修改生产释放逻辑或删除断言。

复跑入口：`cmake-build-relwithdebinfo/kitchen-frame-profile/acceptance-suite.ps1`。`-TestsOnly` 仅编译测试并运行全部 CTest；脚本为本机验收产物，构建目录清理后不保留。

## 2. 静止 kitchen 实测

项目 `D:/work/corona/crn_projects/vision_scene_11`，299 个物体，view1，相机位置 `(1.2110046, 1.8047513, -3.8523903)`、朝向 `(0,0,1)`、FOV 60。实际 framebuffer **1536×825**，1 spp、深度 16；当前 PT 模式启用 SVGF，`zero_copy=false`。预热 20 秒，采样 25 秒。各线程时间不能相加。

| 指标 | 样本数 | 平均 | P95 |
|---|---:|---:|---:|
| CPU 场景同步 | 1,046 | 4.455 ms | 5.326 ms |
| AABB 重算／逐三角形遍历 | 1,046 | 0 次／帧 | 0 |
| 绑定源路径规范化 | 1,046 | 0 次／帧 | 0 |
| 新场景帧间隔 | 1,047 | 23.882 ms | 25.339 ms |
| 渲染调用（含降噪等） | 1,047 | 15.979 ms | 16.762 ms |
| UI 循环间隔 | 1,419 | 17.616 ms | 18.524 ms |
| Display 单次工作 | 2,720 | 0.656 ms | 1.082 ms |

全部静止同步样本 `changed=false`；绑定路径累计计数恒为 598，没有稳态增长。新场景出帧约 **41.87 FPS**，不是显示器实际 present 频率。本轮没有重新采集优化前基线；前次 AABB 优化前约 134.485 ms 的同步数据见原方案第 8 节。

快路径仍逐帧比较网格字节内容，保留快照内存；本轮测得的 4.455 ms 不代表已经消除所有与网格大小相关的 CPU 工作。

## 3. 正确性与编辑器操作

| 验证项 | 本轮结果与证据范围 |
|---|---|
| 初次同步、原始实例矩阵 | 生产 helper 测试通过；真实 kitchen 加载成功，299 个物体 |
| 平移、旋转、非均匀缩放及还原 | helper 与原逐三角形算法、手算坐标比对通过；编辑器普通变换每次只重算 1 个实例、1 帧，随后为 0 |
| 隐藏、恢复、隐藏稳态 | helper 通过；编辑器隐藏／恢复各触发 1 次重算，后续复用 |
| 相机移动与还原 | 两段共 188 帧同步，AABB 重算 0 次、物体 changed 0 次 |
| 顶点原位修改、三角形索引修改、换网格 | helper 检测与精确 AABB 通过；未取得编辑器 GPU 图像／射线结果对照 |
| 实例增删、组替换、逻辑记录损坏、资源 reset | helper 测试通过；不能等同于所有编辑器入口的端到端验证 |
| 正式构建的编辑器场景重载 | `SceneTools.reload_scene` 成功；前后均 299 个物体、1 个相机，camera handle 已重建、姿态与 PT 设置保留；渲染日志确认重新完成 embedded import/loaded，无 ERROR，进程存活 |
| 两个运行时的缓存切换及隐藏恢复 | CPU helper 通过；独立 SceneData 的 GPU 几何传播未通过端到端验收 |
| 场景总范围 | **失败**，见下节 |
| PT → SVGF → PT | **失败**；SVGF 无法加载，返回 PT 后恢复同步 |
| 双相机同时渲染 | **未验证**；创建第二相机及切为 Vision 的 API 成功，但渲染日志仍只有 `visible_cameras=1`，不能据 API 成功判通过 |
| 像素／图像回归 | **阻塞**；截图接口返回失败，生产日志明确指出新 Horizon API 适配尚未完成 |

操作窗口共记录 1,598 个同步样本。将物体移至远处会触发 GeometrySystem 卸载及 `hide_original`，该特殊操作共 300 次 AABB 更新（先更新 1 个，后续缓存失效重算 299 个）；不将它算作“普通变换只更新一次”的证据。

## 4. 未通过项及后续修复边界

### 场景总包围盒没有跟随物体更新

复现：对 `shape_0` 调用 `SceneTools.set_actor_transform`，position 为 `[100,200,300]`。在当帧逐组并集与 `Scene::world_center/world_radius()` 同时取值：

| 数据 | 实际 Scene 值 | 按最新组包围盒计算 |
|---|---|---|
| center | `(0.31935644, 1.6715624, 1.143443)` | `(47.193382, 100.685555, -146.7462)` |
| radius | `10` | `189.32784` |

这是物体随后因距离被卸载前的实际更新帧。静止时原始几何半径约 5.79，Scene 最小半径为 10，静止时两者不同属于正常下限钳制；上表 189.33 的差异不能由该钳制解释。

`sync_external_live_vision_transforms()` 及共享变换应用会更新 instance/group AABB，但未同步 `SceneData::aabb_`。应在实际边界变化后重新聚合场景范围，并核对依赖场景中心／半径的光源、环境与相关 GPU 数据；静止帧不应重新逐三角形扫描。

### 嵌入场景切换 SVGF 失败

`SceneTools.set_vision_render_mode('scene.ini','view1','svgf')` 返回成功，但渲染线程实际报：

```text
Vision scene not found: d:/work/corona/crn_projects/vision_scene_11/scene.ini.embedded
External Vision scene import failed: .../scene.ini.embedded
```

本轮分别出现 250 次；处于 SVGF 的窗口没有正常的场景同步采样。切回 PT 后恢复同步及可见性。应让新模式运行时使用已保存的嵌入场景数据与基目录初始化，不能把逻辑场景键当成磁盘文件路径。

### 独立运行时几何传播和图像证据仍缺失

源码检查：每个共享场景每帧只由一个 runtime 执行 external-live 同步；其他 runtime 的 `upload_shared_scene_transforms_if_needed()` 只消费逻辑实例矩阵。当前几何内容变化处理只重建当前 runtime，未发现将顶点／拓扑数据传到独立 SceneData 的完整路径。这是代码检查发现的风险，不能声称本轮已完成跨 GPU 运行时复现。

修复模式创建后，需要让两个不同 runtime 同时实际渲染，验证原位顶点变形、拓扑变化、形状增删和变换在两边一致。截图路径报 `Screenshot capture temporarily disabled - new Horizon API needed`，因此本轮没有生成可用于像素对照的 kitchen 图像。

## 5. 证据与收尾

本机产物目录：`cmake-build-relwithdebinfo/kitchen-frame-profile/`。

- `acceptance-final-build.log`：撤回插桩后的正式构建。
- `acceptance-ctest.log`、`acceptance-ctest.xml`：最后一次全量 37 项通过记录。
- `acceptance-gpu-interop.log`：开启 GPU 冒烟及旧测试夹具失败的原始记录。
- `acceptance-results.json`：静止统计、逐操作计数、边界诊断与渲染错误。
- `acceptance-runtime.stdout.log`、`.actions.json`、`.steady-window.json`：原始运行数据。
- `acceptance_runtime.py`、`acceptance_analyze.py`：场景操作和统计脚本。
- `acceptance-reload.json`、`acceptance-reload.stdout.log`：撤回插桩后的正式构建重载检查。
- `acceptance-instrumentation.patch`、`acceptance-instrument-backup/`：临时计时诊断及运行前源码备份。

六个插桩文件已按运行前字节恢复，并重新构建正式引擎；测试程序启动的编辑器已退出。`scene.ini` 恢复后的 SHA256 为 `55587b499d8ec3cc7448bbb06ba94bc546aaebe3ff2117f7fd6330278c96f478`。未提交、推送，也未改动上述失败项的生产实现。

## 6. 转入 svgf_magic 提交前复验（2026-09-27）

按用户要求切换至已有 `svgf_magic`，保留 `c2440064` 的相机方向修复；移入路径优化前置提交及同一验收环境的 Horizon 依赖锁更新（锁定 `2d8883bb`），没有合入 main 的其他 mechanics 改动。

在该分支重新执行 CLion configure、正式构建和全部测试：**38/38 通过、0 跳过，4.94 秒**，包含 `VisionCameraDirectionTests`、实际 GPU 冒烟测试和 AABB 回归。证据为同目录 `svgf-commit-configure.log`、`svgf-commit-engine-build.log`、`svgf-commit-test-build.log`、`svgf-commit-ctest.log`／`.xml`。上文 kitchen 性能和运行时操作数据仍属于切换分支前的测量，本次未重新运行整套场景采样。

本次提交现有优化和验收记录；失败项的生产修复尚未实施，具体步骤见 [后续修复计划](../superpowers/plans/2026-09-27-kitchen-acceptance-fixes.md)。
