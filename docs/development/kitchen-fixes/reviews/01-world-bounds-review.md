# 第 01 项审核：场景总包围盒与光照同步

日期：2026-09-27；分支：`svgf_magic`；基线：`cc26b69d`。仅处理第 01 项，不关闭第 02–04 项。执行会话环境 ID：`01a0e00d-5f21-7040-980e-8ecfc858591b`。

状态：已完成。实现、只读复核、正式引擎构建、39 项自动化测试和 kitchen 验证通过；实现提交已推送并完成远端 SHA 核对。

## 问题与失败证据

- 原实现只更新实例和组 AABB，`SceneData::aabb_` 保留导入时范围。新增 CPU 测试在旧行为（新增接口暂为空操作）下失败：`scene center must follow current group bounds`。日志：`red-forced-test.log`。
- 真实 CUDA 探针先正确读出半径 `1.41421`、功率采样概率 `0.333333`；将三角形放大 20 倍并调用生产 `Pipeline::update_geometry()` 后，仍读出上述旧值，而期望为 `28.2843 / 0.995025`。日志：`gpu-red-final-test.log`。这是设备计算结果，不是 API success。
- 审核补充的槽位回归在初版修复下失败：`bounds refresh must reuse light-sampling bindless slots`（`slots-red-test.log`），证明反复重新创建采样表会不断追加 bindless 槽位。
- 首次只改测试头文件时，本机构建没有重编译测试翻译单元，旧二进制通过不计作证据。之后强制重编译测试源码，并按 CLion 重新 configure，强制重编译受影响 Vision/Optics 源文件；上述失败及最终通过均来自重新编译的程序。

本机原始日志和脚本统一位于 `cmake-build-relwithdebinfo/kitchen-frame-profile/01-world-bounds/`，不会把旧验收日志作为本轮证据。

## 实际变更和接口

1. `Scene::recompute_world_bounds()` 从当前非空组 AABB 重建并集，替换原范围并返回变化标志；不访问三角形。空场景对外返回原点及现有最小半径。
2. `Pipeline::prepare_geometry/update_geometry` 在几何提交后调用 `refresh_world_bounds_dependents()`。每个 Pipeline 比较自己上次消费的场景球体，避免 add/remove 已更新 CPU 范围时漏刷光照，也避免静止帧工作。
3. external-live 与 engine-native mixed 均先完成成员和所有组变换，再统一重建或更新 GPU；external-live 同时合并网格内容更新，取消同一批次先重建、再 refit 的重复提交。共享变换更新通过同一 Pipeline 入口刷新。
4. `Scene::remove_shape(index, defer_world_bounds=false)` 保留默认立即更新语义；引擎批量删除入口显式传入 true，在 Pipeline 提交时只聚合一次。
5. 功率、面积光、球面环境采样器保留已有 warper 对象，复用槽位并重新构建/上传内容。
6. 新增 `VisionWorldBoundsGpuTests`，与既有 GeometryGpuResource 测试共用可执行文件、使用独立进程参数 `--world-bounds-gpu`。现有 CTest 数由 38 增为 39，编译目标仍为 38 个。独立进程使编译内核使用的 Vision 进程级 printer/debugger 资源有持续有效的 CUDA device；不删除旧测试或把初始化错误记为 SKIP。

保留相机方向修复、加载时路径规范化、AABB 缓存及原渲染设置。隐藏仍沿用退化变换：组在原点的退化范围参与并集，没有另改可见性表示。

## 正确性与 GPU 生命周期审核

范围消费者检查：方向光 `prepare()` 缓存中心/半径，`sample_wi` 等使用设备半径，`power()` 依赖半径平方；球面环境 `power()` 读取 Scene 范围，功率 light sampler 据此生成概率表。

变化时先排空该 Pipeline 的 stream，再在其 scene GPU context 内准备所有视图的光照表；全部 prepare 完成后发布 scene/pipeline bindless，随后编译每个视图并使累积历史失效，最后记录消费球体并恢复调用前视图。不能仅修改 CPU getter，或在 EInstance 模式仅上传数据，因为编译代码可能捕获常量与槽位。静止路径没有新聚合、上传或编译。

只读审核者 `/root/world_bounds_review` 未修改源码、运行构建或实施其他项。初审两项 Important 已修正：

- 逐视图 prepare→compile 会使早先视图捕获后来被替换的面积光表：改为所有视图先 prepare、再全部 compile。
- 反复创建 warper 导致槽位增长：改为复用对象，并加入增长/缩小循环的槽位断言。

初审 Minor（批量删除重复聚合）已通过延迟聚合参数修正。提交前审核另发现 engine-native mixed 同批增删与已有物体移动仍会提交两次：已将成员提交移到所有变换更新之后，并在完成后返回，保留材质、bindless、版本标记及历史失效处理。最终只读复核结论：无剩余 Critical/Important。环境光在多视图测试中覆盖资源生命周期与槽位稳定性，未把它描述为完整环境采样/PDF 验证。

## 自动化覆盖和命令

CPU 覆盖移动、旋转、非均匀缩放、隐藏恢复、原位顶点/索引变更、组替换、资源重载、范围扩大/缩小、删除最后组、空/无效组、最小半径和未变化返回值。参考值来自逐三角形精确计算和手算坐标。

CUDA 覆盖：

- 生产 geometry update 后的方向光设备采样距离及功率 PMF；半径从 `sqrt(2)` 到 `sqrt(800)` 再缩小。
- 方向光 CPU 编码和 GPU buffer 下载的中心、半径；隐藏、删空、重新添加后的有限值。
- 两个视图、EInstance、面积光及球面环境，8 次范围交替变化；每个视图方向光常量和面积光三角形 PMF 正确，bindless 槽位数量保持不变。
- `isolated-gpu-test.log`：两项定向测试 2/2 通过，无内部 SKIP。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .agents/skills/clion-cmake-relwithdebinfo/scripts/configure.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .agents/skills/clion-build-corona-engine/scripts/build.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File cmake-build-relwithdebinfo/kitchen-frame-profile/01-world-bounds/suite.ps1 -TestsOnly
```

最后一个脚本使用同一 CLion CMake/Ninja/MSVC 14.44.35207，显式编译注册测试对应的全部目标，将 build/bin 和 examples/engine 加入 PATH，设置 `CORONA_RUN_GPU_SMOKE=1`，执行 `ctest --test-dir cmake-build-relwithdebinfo -V --output-on-failure --timeout 180` 并保存 JUnit。

最终 native 批次顺序修正后正式构建成功（`final-native-engine-build.log`）；全量 **39/39 通过，0 失败、0 跳过，5.39 秒**（`acceptance-ctest.log` / `.xml`、`final-native-suite-driver.log`）。完整 verbose 输出无内部 SKIP；`UiMultiSurfaceSmoke` 实际执行 1/3/16 surface、burst、resize/minimize/restore、100 次生命周期和 shutdown drain。VisionCameraDirectionTests 也通过。

## kitchen 实际场景验证

项目 `D:/work/corona/crn_projects/vision_scene_11`，299 个物体，view1；相机位置 `(1.2110046,1.8047513,-3.8523903)`，朝向 `(0,0,1)`。实际采样 framebuffer 为 **1536×825**，保持原 PT/SVGF 配置、1 spp、深度 16，不通过降低设置换取结果。临时计数插桩只用于采样，采样后按备份字节恢复。

预热 20 秒、采样 25 秒：1,012 个同步样本，均值 **5.219 ms**，P95 **7.145 ms**；`changed=false` 全部成立，实例 AABB 重算 **0**、逐三角形 AABB 调用 **0**、Scene 聚合 **0**。这是本轮同步时间，不将它与不同条件的历史数据当作严格性能对照。

相机移动/还原两个窗口共 **191 帧**：实例 AABB、逐三角形调用、场景聚合均 **0**。普通平移、旋转/非均匀缩放、隐藏/恢复，每个操作窗口各为 1 次实例 AABB、1 次逐三角形调用、1 次聚合。

`shape_0` 移动到 `[100,200,300]`、距离卸载前的新同步帧：

| 数据 | Scene 实际值 | 最新组并集参考值 |
|---|---|---|
| 中心 | `(47.193382,100.685555,-146.7462)` | 相同 |
| 半径 | `189.32784` | `189.32784` |
| 后续恢复中心 | `(0.31935644,1.6715624,1.143443)` | 相同 |
| 后续恢复半径 | `10` | `max(5.791922,10)` |

本轮 9 条变更范围记录全部与参考并集一致，包括重载过渡中的空范围。远距离操作后确有卸载/缓存重建：跨远移和恢复窗口记录了大量 AABB 重算，不能把这一特例表述为普通变换仅一次。日志无引擎 ERROR/CUDA_ERROR。

证据：`kitchen.stdout.log`、`kitchen.stderr.log`、`kitchen.actions.json`、`kitchen.steady-window.json`、`results.json`、`runtime.py`、`analyze.py`。首次立即打开视图的 API 曾返回 `Unable to replace scene.ini`；不将该返回当作成功，随后场景确实渲染并产生上述同步样本，所有变换/隐藏/相机/重载操作响应均成功。

场景文件已恢复，SHA256：`55587b499d8ec3cc7448bbb06ba94bc546aaebe3ff2117f7fd6330278c96f478`。正式二进制的独立重载复验通过（`acceptance-reload.json`、`final-reload.stdout.log`）：前后各 299 个物体、相机句柄重建、姿态保留、进程存活；日志两次确认 loaded embedded Vision runtime，0 引擎 ERROR，0 插桩标记。启动后稍候再打开视图成功，未重现首次采样启动时的保存竞态。

## 证据边界及交付结论

本项 GPU 正确性由独立确定性 CUDA 消费测试证明。未使用截图接口，也未宣称完成 kitchen 的双可见相机、PT→SVGF 模式切换或独立 runtime 几何传播；这些仍属于第 02–04 项。两视图 probe 验证光照资源同步，不等同于编辑器双窗口验收。

kitchen 实测覆盖 external-live 路径。最后的 engine-native mixed 提交顺序调整由只读代码复核、正式构建及全量回归覆盖，未另行执行编辑器中同批增删与移动的专项操作；此调整未改动已采样的 external-live 路径。

变更范围发生变化时，完整光照准备和内核重编译可能产生交互停顿；静止/仅相机移动不会触发。本项优先保证现有编码/采样表生命周期正确，未加入新的异步重编译机制。

本项验证结论：通过。实现与验证提交 `6e716217dd21d38053c4c4938f17340303c3ebef` 已推送至 `origin/svgf_magic`，随后 `git ls-remote origin refs/heads/svgf_magic` 返回完全相同 SHA；核对后才将 execution-tracker.md 第 01 项标记为已完成。本次文档交付记录作为后续独立提交保存。未自动启动下一项。
