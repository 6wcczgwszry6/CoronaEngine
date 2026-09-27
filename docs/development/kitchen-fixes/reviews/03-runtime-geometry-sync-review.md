# 第03项审核：独立 runtime 完整几何同步

日期：2026-09-27；分支 `svgf_magic`；基线 `0a230495d8e59fb3195bf0f1bf46f241bf48498b`。
执行会话：`01a0e050-2cea-7010-baf5-10115ce8afd3`，CODEX_THREAD_ID/CODEX_SESSION_ID 一致。

状态：实现、审核、最终全量验证与推送核对完成。第04项未启动，按用户最新要求不再推进。

## 复现与红色证据

生产 OpticsSystem 导入两个独立 SceneData、独立 GeometryGpuResource 的 PT/SVGF runtime。SharedDataHub 建立真实 actor/profile/geometry/transform 及 external-live 绑定，调用生产 `sync_external_live_vision_transforms` 和 `sync_shared_vision_scene`。后者由原有逐帧共享矩阵消费入口等价提取，红色阶段未改变行为。

`red-test.log`：相同地址、相同数量的顶点原位从 z=0 改为 z=1 后，PT CUDA 射线命中 z=1；SVGF CPU 顶点与 CUDA 命中均为 z=0。断言 `consumer CPU and CUDA must receive in-place vertices` 失败，确认完整几何传播实际缺失。此前夹具编译错误不计为功能红色证据。

所有本机日志/脚本位于 `cmake-build-relwithdebinfo/kitchen-frame-profile/03-runtime-geometry-sync/`。

## 实现与所有权

- VisionSceneResource 发布 CPU 值快照，包含顶点、索引、稳定形状/实例身份、材质与发光描述、实例成员及矩阵；快照不持有 Mesh/SceneData/GPU 对象。geometry_version 独立于变换版本，source_revision 限定来源。
- 每个 runtime 保有独立 SceneData、GPU、framebuffer、积分器和历史。落后的 runtime 先消费再参与任意发布路径；成功安装、上传/构建及提交后才推进 applied_geometry_version。
- 创建/消费快照时初始化比较基线，防止第一次 producer 同步把已发生的编辑当成未变化基线。初始化之后，静止或相机变化不发布快照、不重建 BLAS。
- 替换前先完成 CUDA 并等待该 runtime 的 interop receipts；暂存输入无效时保留旧 GPU 场景，修复同一版本后仍可消费。
- 新增材质从 CPU 描述在消费 runtime 内创建；已存在材质按内容哈希匹配。面积光按稳定实例身份复用，重排更新实例索引、删除清理孤立光源。完整几何重建强制刷新光照依赖，即使总范围相同。
- 保留第01项范围聚合/光照槽位复用和第02项来源描述、相机方向、路径规范化。source reload 新建快照命名空间；idle 释放 GPU 时保留 CPU 快照。

## 只读审核及处理

审核者 `/root/geometry_review` 只读检查，未构建、修改或启动其他代理。四个 Important 已建立独立失败用例（`review-red-final-test.log`）：

1. 新材质仅存在于 producer：消费失败 `geometry material mapping unavailable`。
2. 发光实例重排后 area light 仍指旧实例槽位。
3. 消费失败后 mixed 删除路径反向发布旧几何。
4. 刚消费的新 runtime 首次 producer 前编辑被吞掉，GPU 仍 z=1，期望 z=0.75。

修正后五项测试全部通过（`review-green-test.log`，36.58秒）。新增材质第一次夹具使用未完整准备的新材质类型，进程终止；改为完整准备的 diffuse 类型新实例后得到上面有效失败，不把夹具错误当作生产映射证据。随后新增 principled_bsdf 类型测试，验证新增材质类型也可被独立 runtime 导入并产帧。

进一步的 idle 测试发现：最后一个 runtime 淘汰时清掉逻辑变换，恢复时丢失比几何快照更新的平移。`eviction-red-test.log` 断言恢复 x=0、期望4失败。修正为只退休 SceneData/GPU，保留 CPU 快照和当前逻辑变换；绿色测试确认旧 GPU weak_ptr 过期、重建后 GPU 在 x=4、z=1 命中。单 runtime 渲染入口也检查消费结果，消费失败不继续渲染该版本。

审核者未判断实际 CUDA、全量测试、编辑器验收和性能，因为其任务禁止运行；这些由本执行会话直接验证。未把只读审核替代运行证据。

最终只读复查已检查上述修正、测试源码及本机运行日志：四项Important均已修复，未发现新的Critical/Important。其未重新运行构建或测试；GPU与性能结论仍以本执行会话的实际日志为依据。

## 验证记录

CLion RelWithDebInfo、原 CMake/Ninja/MSVC 工具链，无设置降低。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .agents/skills/clion-cmake-relwithdebinfo/scripts/configure.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .agents/skills/clion-build-corona-engine/scripts/build.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File cmake-build-relwithdebinfo/kitchen-frame-profile/03-runtime-geometry-sync/focused.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File cmake-build-relwithdebinfo/kitchen-frame-profile/03-runtime-geometry-sync/suite.ps1 -TestsOnly
```

首次扩展集成用例通过：`green-staged-test.log`，15.29秒；同地址顶点/索引、网格替换、实例增删重排、隐藏恢复、睡眠跳过中间版本、无效索引导入和同版本重试、来源重载。PT/SVGF 输出均有限，RGB 和 `376.435`，各运行3帧，实际 `actual_runtimes=2`。每次变更各runtime BLAS build计数恰好+1；静止重复同步保持build计数与快照指针/版本不变。

首次全量41/41通过，0失败、0跳过，25.27秒（`suite-initial-driver.log`）；此记录早于四项审核修正，不作为最终通过结论。修正后专项目标7/7通过，48.37秒（`final-focused-test.log`），覆盖 base/fresh/material/topology/lights/stale/eviction。新增 diffuse 输出RGB和366.214、新增principled_bsdf为386.445、删除发光实例后为0。

撤回临时插桩后正式构建通过（`final-engine-build.log`，退出码0）。最终补充的 framebuffer 检查曾误用protected积分器接口而编译失败（`final-fixture-compile-error.log`），已改用公开framebuffer接口，不将此编译错误记为功能红色证据。

最终全量 **47/47通过，0失败、0跳过、无内部SKIP，53.66秒**，40个独立可执行测试目标，`CORONA_RUN_GPU_SMOKE=1`。日志 `final-suite-driver.log`、`acceptance-test-build.log`、`acceptance-ctest.log`、`acceptance-ctest.xml`。新增组/场景中心断言随每次三角形平面修改更新；framebuffer地址在几何消费后保持不变。PT/SVGF各实际完成3帧，RGB和均376.435，`actual_runtimes=2`；两个runtime均在确定性CUDA射线上命中新顶点/索引平面。仅移动相机仍不发布快照、不增加build计数。

## Kitchen 实测

原项目 `D:/work/corona/crn_projects/vision_scene_11`，299个物体；保持原相机、1 spp、最大深度16及SVGF设置。正常帧1536×825，模式/重载过渡中出现1920×1080帧，没有主动降低分辨率。预热20秒，采样25秒。

| 稳态指标 | 结果 |
|---|---:|
| 同步样本 / 已完成GPU帧 | 1021 / 1021 |
| external-live同步均值 / P95 | 4.7721 / 6.5182 ms |
| 逐三角形AABB计算 | 0 |
| AABB几何比较缓存复制 | 0 |
| 几何版本 / 完整加速结构build计数 | 全程1 / 1，无新增 |

这里的时间是external-live同步耗时，不是整帧GPU时间。实际完成帧在 `Pipeline::display()` 返回后记录：PT 2459帧、SVGF 163帧。移动相机及恢复均无三角形计算、缓存复制、快照发布或BLAS重建；物体隐藏/恢复、平移/恢复、旋转缩放/恢复各只重算对应实例一次，几何版本保持1。新SVGF导入并消费快照后build计数为2，其后稳定不增长。

来源重载返回299个actor，日志确认 `source_revision=2` 重新导入；本轮插桩未采到版本2的完成帧，不将此导入日志算作版本2持续产帧证据。双GPU来源重载的数值正确性由自动化测试直接断言。编辑器实际始终 `visible_cameras=1, active_runtimes=1`；不声称完成第04项双视图。

`kitchen.stdout.log` 无引擎ERROR或CUDA_ERROR。API部分响应字段异步滞后，模式结论依据真实pipeline和完成帧。记录见 `runtime.py`、`analyze.py`、`results.json`、`kitchen.actions.json`、`kitchen.steady-window.json` 和stdout/stderr。分析按Windows本地UTC+8匹配时间窗口。

插桩按本轮最新源码备份逐字节恢复，正式源码无 `GEO_*` 测量标记。场景恢复SHA256：`55587b499d8ec3cc7448bbb06ba94bc546aaebe3ff2117f7fd6330278c96f478`。保留这些本地日志，不将大体积产物纳入Git。

## 范围与限制

无效快照测试注入的是上传之前的CPU导入验证失败，不能把它表述为真实CUDA驱动上传故障注入。底层Vision GPU构建接口为 noexcept，设备级失败并无可恢复异常契约；此项需在最终结论中明确。

几何替换前生产代码提交CUDA并等待已记录的interop receipts；本轮editor路径未产生待等待的interop receipt，因此“存在未完成Vulkan提交时替换”的分支只有源码审查，没有实际运行覆盖。独立GPU测试覆盖实际CUDA提交、替换和退休。实例重排/删除有确定性断言，尚无单独的多group重排测试。

CPU快照与材质/光源描述增加CPU内存占用，首次加载和几何变化时复制，idle退休后保留到资源来源重置/clear；各runtime仍拥有独立GPU缓冲。动态medium新增及任意插件参数编辑不在本次几何同步范围。

集成测试实际创建/渲染两个模式，不等同于编辑器两个可见窗口。Horizon截图恢复和第04项整体结论不在本次提前完成。

## 交付

实现提交 `4176fa956d3baeff663e71325fbb745e4c335320` 已推送至 `origin/svgf_magic`；`git ls-remote --heads origin refs/heads/svgf_magic` 返回完全相同SHA。核对后才将执行记录第03项标记完成；交付状态由后续文档提交保存并再次推送核对。

正式构建、全量测试与本项kitchen验证完成。测试、编辑器和构建进程均已退出。按用户最新要求，第03项交付后停止，第04项不启动；截图读回和编辑器双视图仍未实施。
