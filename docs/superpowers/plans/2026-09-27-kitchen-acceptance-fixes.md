# Kitchen 验收问题修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复场景范围和嵌入场景模式切换，补齐独立运行时几何同步及可观察的图像验收，同时保留静止帧 AABB／路径解析零次的效果。

**Architecture:** 场景资源持有与渲染模式无关的来源数据和几何变更版本；每个 runtime 保留独立 GPU 与降噪状态，按版本消费场景变化。包围盒只在实际变化后聚合已有组 AABB；模式切换从正确的场景来源初始化。

**Tech Stack:** C++20、Vision、Horizon、CUDA/Vulkan、CTest；沿用 CLion RelWithDebInfo/MSVC 构建配置。

**Spec:** [Kitchen AABB 验收报告](../../development/kitchen-aabb-acceptance.md)、[原优化方案](../../development/kitchen-scene-sync-optimization.md)。

状态：任务1、2已交付，见[第01项审核](../../development/kitchen-fixes/reviews/01-world-bounds-review.md)、[第02项审核](../../development/kitchen-fixes/reviews/02-embedded-mode-switch-review.md)。任务3实现、正式构建和47项测试通过，已推送并核对远端SHA，见[第03项审核](../../development/kitchen-fixes/reviews/03-runtime-geometry-sync-review.md)。按用户最新要求在任务3完成后停止，任务4不启动。

各问题的独立方案、依赖顺序和验收出口已整理至 [解决方案总览](../../development/kitchen-fixes/README.md)：[场景总范围](../../development/kitchen-fixes/01-world-bounds.md)、[嵌入场景模式切换](../../development/kitchen-fixes/02-embedded-mode-switch.md)、[跨运行时几何](../../development/kitchen-fixes/03-runtime-geometry-sync.md)、[截图与双视图](../../development/kitchen-fixes/04-capture-and-multiview.md)。本文件保留执行任务清单，独立方案补充数据流和边界规则；实施时一起阅读。

## 全局约束

- 保留 `svgf_magic` 原有相机方向修复，以及路径规范化、AABB 复用。
- 不用降低分辨率、采样数、深度或关闭降噪取得性能通过。
- 静止 kitchen 和仅移动相机时，物体逐三角形 AABB 重算与绑定路径解析均为 0 次／帧。
- CPU 数值、GPU 结果、实际活跃相机／runtime 均须有证据；API 返回成功不能替代渲染成功。
- 生产改动分任务提交，当前已有失败不应通过删除断言、跳过 GPU 测试或制造 `.embedded` 文件绕过。

## 重点回归风险

1. 物体向外移动和重新移回都要更新总范围，不能只 `extend` 导致永久膨胀。
2. 隐藏、删除最后一个物体、资源重载应处理空范围及最小半径，不能产生 NaN。
3. 新模式 runtime、休眠后重新使用的 runtime 必须消费最新来源／几何，不能反向覆盖新数据。
4. 顶点和索引原位修改即使地址、数量和变换未变，也必须传播；仅增加版本号却不复制内容不算修复。
5. GPU 尚在使用旧资源时不能销毁；截图必须等对应提交完成，检查格式、尺寸和颜色空间。

## 任务 1：更新 Scene 总范围及依赖数据（最高优先级）

**文件：**
- 修改 `vision/src/base/mgr/scene.h`、`scene.cpp`：总范围聚合。
- 修改 `vision/src/base/mgr/pipeline.h`、`pipeline.cpp`、`src/systems/optics/optics_system.cpp`：更新顺序与 GPU 刷新。
- 核对 `vision/src/render_core/light/environments/directional.cpp`：`prepare()` 缓存了中心和半径，不能只修 CPU getter。
- 测试 `tests/systems/optics/test_external_live_aabb.h`、`test_vision_geometry_gpu_resource.cpp`。

**拟定接口：** `bool Scene::recompute_world_bounds() noexcept`，只对当前有效 group AABB 求并集、返回是否改变；不调用 instance 的逐三角形算法。`void Pipeline::refresh_world_bounds_dependents() noexcept` 更新依赖范围的光源编码数据及采样分布，使用该 pipeline 的 stream/bindless；清除受影响的累积历史。

- [x] 添加失败测试：已加载的 Scene 中移动组后，`world_center()` 等于最新组并集中心，`world_radius()` 等于 `max(并集半径,min_radius)`；移回、隐藏／恢复、删除、空场景、非均匀缩放分别断言。
- [x] 运行测试确认旧实现保留初始 Scene 范围而失败；另测方向光 CPU 编码值及上传后的结果，防止 CPU 修好但 GPU 仍旧。
- [x] 实现聚合；在 external-live、共享变换应用、几何替换／增删的批次结束后执行一次。仅在几何或边界实际变化时刷新依赖，静止路径直接复用。
- [x] 重跑测试及 kitchen `[100,200,300]` 位移复现；在 GeometrySystem 距离卸载前的更新帧取值。验收时从最新组范围计算期望值，不硬编码会受场景和坐标系影响的 189.32784。
- [x] 构建、测试通过后单独提交范围修复。

## 任务 2：模式切换保留嵌入场景来源（最高优先级）

**文件：** `include/corona/systems/optics/vision_scene_resource.h`、`src/systems/optics/optics_system.cpp`；测试 `test_vision_scene_resource.cpp`、`test_vision_render_mode_config.cpp`、`test_vision_geometry_gpu_resource.cpp`。

**拟定数据：** 在 `VisionSceneResource` 增加显式来源描述 `VisionSceneSourceDesc`：来源种类 File/Embedded、文件路径或 `scene_json`、绝对 `base_dir`、单调递增 `source_revision`。规范化的资源 key 仍是身份，不承担内容或加载方式。沿用现有 `import_vision_scene_from_data()` 与 `import_vision_scene_from_file()`。

- [x] 添加失败测试：资源只提供内存 JSON，不创建任何 `.embedded` 磁盘文件；先建 PT，再建 SVGF，应均得到非空 pipeline、相同场景身份、正确相对纹理／模型路径。
- [x] 明确重载语义：新来源描述先校验并完成候选导入，成功后再发布；重置加载缓存不意外清除已发布来源。runtime 清理／淘汰不能带走共享来源。
- [x] `load_vision_scene_from_json` 接收来源时保存到共享资源；`ensure_external_vision_runtime()` 按显式来源种类选择导入器，不从文件名后缀猜测。`reset_pipeline()` 后恢复 runtime 所需的 embedded 标记，保留现有增删行为。
- [x] 补测 PT→SVGF→PT、隐藏后切模式再恢复、修改来源后重载、同 key 新版本、空 JSON 和导入失败；失败不得发布“已加载”版本。
- [x] 在 kitchen 实际渲染中确认 SVGF pipeline 存在且持续产帧，日志无文件查找错误。记录实际相机／runtime 数量，而不是只检查相机 mode 字段。
- [x] 构建、测试通过后单独提交来源修复。

## 任务 3：独立 runtime 消费完整几何变更

生产路径红色集成测试已确认第二runtime的CPU顶点和CUDA命中滞后，现通过CPU快照发布/消费修复。各runtime继续拥有独立SceneData、Geometry GPU资源及渲染状态。

**文件：** `vision_scene_resource.h`、`optics_system.cpp`、`vision_external_live_aabb.h`、`vision_geometry_snapshot.h`及Vision材质/光源/几何生命周期协作；测试 `test_vision_runtime_geometry_sync.cpp`。

**拟定机制：** `VisionSceneResource` 持有不含 GPU 句柄的最新几何快照及 `geometry_version`；每个 runtime 保存 `applied_geometry_version`，与已有 transform version 分离。快照包括网格顶点／索引、稳定形状身份、实例成员和材质映射；只在变更时发布，不逐帧复制。消费方不能将自己的旧网格重新发布为最新内容。

- [x] 创建两个独立 SceneData 和独立 GPU 几何资源的实际 PT/SVGF runtime。修改一个场景的顶点／索引，验证另一 runtime 的 CPU 顶点、AABB、GPU 射线命中结果也更新；确认当前版本的具体失败。
- [x] 将新几何快照发布与版本递增作为一次操作；渲染前先消费几何版本，再应用实例变换、聚合范围、上传 GPU。仅变换变化走现有 TLAS 更新，网格／拓扑变化才重建相应缓冲与 BLAS/TLAS。
- [x] 等旧 GPU 提交完成再替换资源，上传成功后才记录消费版本。保留另一 runtime 的 framebuffer 和 denoiser 所有权，但使受影响历史失效。CUDA替换/退休实测通过；待完成interop receipt分支仍仅源码审查。
- [x] 覆盖原位编辑、网格替换、实例增删／重排、隐藏恢复、休眠 runtime、重载和上传前CPU导入失败；同一次变更每个 runtime 只消费一次。集成测试直接调用生产同步入口，不复制同步算法到测试中。设备级上传故障恢复未测试。
- [x] 构建、GPU 集成测试和双 runtime 实际渲染通过后单独提交。实现 `4176fa956d3baeff663e71325fbb745e4c335320` 已推送并核对远端SHA。

## 任务 4：恢复可验证的截图及双视图验收

**文件：** `src/systems/optics/optics_system.cpp` 的截图处理、`src/systems/ui/cef/cef_editor_native_api_handlers.cpp` 相机入口、`tests/systems/optics/test_vision_geometry_gpu_resource.cpp`；复用 `tests/integration/ui_multisurface_smoke.cpp` 的像素验证经验。

**边界：** `HardwareExecutor::wait(const SubmitReceipt&)` 可用于等待提交；当前截图的旧 `copy_to_buffer` 已移除。采用 Horizon 现有公开读回接口；若缺失，应在 Horizon 增加并测试公开 image→host readback 能力、单独提交和更新依赖锁，不能在 Engine 偷用 Vulkan 私有句柄或假定旧 API 存在。

- [ ] 添加固定小图案 GPU 读回测试：颜色／尺寸／格式正确、等待对应提交、关闭窗口或 resize 后请求能完成或明确失败，不能悬挂 promise。
- [ ] 恢复截图请求实际执行和保存，移除当前无条件返回失败分支；保留相机输出模式与视口状态，验证 Vision 最终合成图而不只是 UI 背景。
- [ ] 通过真实视口显示路径打开两个相机，确认 `visible_cameras=2`；使用不同模式时确认 `active_runtimes=2`。现有创建 camera 的 API 设置 offscreen、surface=0，单凭该 API 无法证明两个可见窗口已参与渲染。
- [ ] 固定相机、分辨率和采样设置，用确定性几何／射线结果校验同步；有随机噪声的 PT 图采用固定种子或预先约定误差阈值，不要求不受控噪声逐像素相等。
- [ ] 重新执行验收报告中的全部项目；静止预热 20 秒、采样 25 秒，保存均值、P95、样本数、GPU 结果与日志。全部满足后才将总体状态改为完成并提交。

## 验证命令与执行顺序

先执行任务 1、2，再完成任务 3、4 的集成验收。任务 4 的读回设施可在任务 3 的 GPU 结果校验需要时先完成。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .agents/skills/clion-cmake-relwithdebinfo/scripts/configure.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .agents/skills/clion-build-corona-engine/scripts/build.ps1
```

配置变化才重新 configure。测试目标使用同一 CLion/MSVC 环境编译；CTest 工作目录使用实际插件目录，PATH 包含构建的 `bin` 和 `examples/engine`，并设置 `CORONA_RUN_GPU_SMOKE=1`。运行全量 `ctest --test-dir cmake-build-relwithdebinfo --output-on-failure --timeout 180`；成功条件为 0 失败、0 跳过，CUDA 集成输出无内部 SKIP。目标分支有额外相机方向测试，不把历史 37 项写死为预期数量。

第01、02项已交付；任务3已完成失败复现、GPU双runtime和kitchen回归，交付状态见执行记录。任务4继续沿用其截图与实际双视图验收边界。
