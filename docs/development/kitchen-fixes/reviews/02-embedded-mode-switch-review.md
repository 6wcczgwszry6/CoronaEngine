# 第 02 项审核：嵌入场景 PT/SVGF 模式切换

日期：2026-09-27；分支 `svgf_magic`；基线 `5c608cbf72976f8bc63415566244f0785cec221f`。
执行会话：`01a0e033-f659-7232-bed2-1a8e5837df26`（由 CODEX_THREAD_ID 与 CODEX_SESSION_ID 一致核实；list_threads 未列出本会话）。

状态：已完成。实现、只读审核、正式构建、40项全量测试和 kitchen 验证通过；实现提交已推送并核对远端 SHA。第03、04项仍未实施。

## 原因与失败证据

- 旧实现将 JSON/base_dir 放在单个 runtime，`ensure_external_vision_runtime` 创建 SVGF 时只调用文件导入器。逻辑身份 `.embedded` 因此被当作文件。
- 新增 `VisionEmbeddedModeSwitchTests` 直接调用生产 OpticsSystem 加载入口，使用内存 JSON、临时 OBJ、真实 CUDA 设备。旧实现中 PT 完成 GPU 初始化，第二模式失败：`second mode must import the in-memory source, not the identity as a file`，同时记录 `Vision scene not found: .../memory-only.embedded`。未创建该文件。证据 `red-test.log`。
- 审核新增 GPU 生命周期断言在初版修复下失败：`retiring the last runtime must release scene GPU resources`，证据 `retirement-red-test.log`。共享 SceneData 间接保留了 GeometryGpuResource。
- 审核新增 `scene.mediums=1` 无效 JSON 后，进程以 `0xc0000409` 退出，证据 `mediums-red-test.log`；此前校验未拦截此对象边界，JSON 异常穿过 Vision 的 noexcept 描述解析。

本机脚本、日志位于 `cmake-build-relwithdebinfo/kitchen-frame-profile/02-embedded-mode-switch/`。
夹具修正：最初没有光源的小场景触发零长度 light sampler 内核数组，加入有效材质和点光源后才取得上述有效红色用例；首次真实 OpticsSystem 链接需要完整 corona::engine 依赖。改变 CWD 时，Vision CUDA 编译器本身仍需要当前目录包含 cuda headers，测试改用另一已部署的运行目录；这是编译器环境前提，模型来源仍固定在原始绝对 base_dir。以上环境失败不计作功能失败证据。

## 实现范围与执行裁决

- `VisionSceneResource` 持有显式 `VisionSceneSourceDesc`（File/Embedded、file_path、scene_json、绝对 base_dir）与 `source_revision`。reset_loaded_scene 清理加载缓存，不删除来源或回退版本。
- 两类来源统一经过生产 `load_vision_runtime_source`：新 JSON/强制重载先独立导入候选，成功后排空旧 runtime、发布新来源和版本；失败保留旧来源、版本和 pipeline。
- runtime 记录实际消费的来源版本；已有 runtime 的逐帧路径只比较版本，不复制 JSON、不访问文件系统。embedded 删除/隐藏策略读取共享描述，删除原 runtime 的两份来源字符串。
- 最后 runtime 释放后，共享 map 保留来源，释放 loaded SceneData/GPU。完整 shutdown 清空 map。
- Ruling：既有方案中“先校验并发布描述”细化为“完整导入候选成功后发布”，避免部分导入把新版本伪装为成功；代价是重载期间短暂同时保有两份 GPU 场景，优先保证回滚和生命周期。
- Ruling：按用户要求复用当前 local 工作区与已批准方案，不创建 worktree 或第 03/04 执行会话。最终 push 已明确授权，无需再次询问。

## 审核

只读审核者 `/root/embedded_source_review` 未修改文件或运行构建。初审提出 GPU 资源滞留、mediums 无效输入、隐藏恢复及真正 idle eviction 证据缺口。前两项已补红色用例并修正。二次只读复核无剩余已确认 Critical/Important 代码问题；要求补齐实际验收证据并撤回插桩。隐藏恢复新增实际 GPU 输出验证，kitchen 自动同步和真正 idle eviction 已取得下述证据。

最终只读证据复核结论：Ready to merge: Yes，无 Critical/Important；确认未夸大单视图、GPU像素与kitchen帧日志的不同证据边界。提交/push当时仍待执行。

## 验证记录

按仓库 CLion RelWithDebInfo 技能，使用同一 CLion CMake/Ninja/MSVC 14.44.35207；无并行引擎/测试构建，未更换 build 目录或调低渲染设置。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .agents/skills/clion-cmake-relwithdebinfo/scripts/configure.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .agents/skills/clion-build-corona-engine/scripts/build.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File cmake-build-relwithdebinfo/kitchen-frame-profile/02-embedded-mode-switch/suite.ps1 -TestsOnly
```

configure 成功见 `red-configure.log`；撤回所有临时插桩后的正式引擎构建成功见 `final-engine-build.log`，可执行文件存在。测试驱动复用前项脚本，按可执行文件去重，编译 **39个目标、40个已注册CTest**。测试环境 PATH 含 build/bin 和 examples/engine，`CORONA_RUN_GPU_SMOKE=1`；执行 `ctest --test-dir cmake-build-relwithdebinfo -V --output-on-failure --timeout 180 --output-junit .../acceptance-ctest.xml`。

最终 **40/40通过，0失败、0跳过，11.33秒**，完整 verbose 日志无内部 `SKIP`。证据 `final-suite-driver.log`、`acceptance-test-build.log`、`acceptance-ctest.log`/`.xml`。受来源头文件影响的既有 GPU、pipeline key 和 scene resource 测试翻译单元已强制重新编译，避免沿用旧二进制。UiMultiSurfaceSmoke 实际执行1/3/16 surface、burst、resize/minimize/restore、100次生命周期和shutdown drain。第01项范围GPU测试、相机方向回归均通过。

新增 CUDA 测试直接调用生产 OpticsSystem 私有入口（仅 friend 测试访问，不新增测试专用生产方法），不是复制导入算法。JSON不落盘；相对 OBJ/TGA资源在来源绝对基目录加载，初始相对base_dir在接收时固定，改变CWD后创建第二模式仍成功。覆盖：独立 PT/SVGF framebuffer、PT→SVGF→PT、隐藏模式新建和恢复、同key新JSON分辨率16→24、同JSON强制重载后实际模型顶点范围变化、非法JSON/mediums类型/缺失模型和贴图不发布版本、全部runtime退休后GPU弱引用到期及从同版本来源重建、显式File来源两模式导入。CPU回归证明reset不清来源、后缀不决定来源种类。

测试实际运行积分器并下载最终GPU图像，所有像素有限。示例RGB和：PT `135.036`；隐藏SVGF `0`；恢复SVGF `132.678`；PT返回 `132.892`；失败重载后PT `135.388`；新JSON `151.308`；资源重载和重建 `216.679`。这些是本次输出摘要，测试断言可见/隐藏与有限性，不把随机采样图的不同帧强行要求逐像素一致。

隐藏小场景的变换操作调用既有生产 `sync_external_live_group` helper；自动 runtime 选择、共享变换消费和真正idle eviction另由下述kitchen入口验证，明确区分证据层级。

## kitchen 真实渲染证据

项目 `D:/work/corona/crn_projects/vision_scene_11`，299 个物体，view1，相机保持 `(1.2110046,1.8047513,-3.8523903)`、朝向 `(0,0,1)`。保持原采样/深度配置（1 spp、深度16）；正常完成帧为 **1536×825**，未降低分辨率或关闭 SVGF。

临时 `EMBEDDED_FRAME` 在真实 `Pipeline::display()` 返回后记录；该调用包含积分器渲染和 CUDA 同步提交。整个过程 **4,449 个完成帧**。以下按每个操作时间窗口剔除最初2秒统计，帧号因历史失效可重置，不等同于进程累计帧数。

| 操作 | 实际模式/来源版本 | 完成样本数 | 证据 |
|---|---|---:|---|
| 初始打开 | PT / 1 | 959 | 帧1–959 |
| PT→SVGF | SVGF / 1 | 560 | 帧1–560，新 pipeline，降噪启用 |
| SVGF→PT | PT / 1 | 549 | 帧84–632，复用 PT |
| 隐藏 shape_0 | PT / 1 | 129 | 组范围为零 |
| 隐藏状态切换 | SVGF / 1 | 346 | 帧1–346，范围仍为零 |
| 恢复 shape_0 | SVGF / 1 | 341 | 原始范围精确恢复 |
| 场景重载 | PT / 2 | 449 | 新 pipeline，帧1–449 |
| 重载后继续运行 | PT / 2 | 758 | 帧535–1292 |

原始/恢复范围均为 lower `(-2.476724,1.384368,1.037007)`、upper `(-2.474544,1.391896,1.218802)`。`08:31:25.671` 真正触发 `evict_idle_vision_runtimes` 淘汰 SVGF；`08:31:45.910` 从共享内存来源重新导入同一版本，随后持续完成隐藏状态帧。分配器复用了地址，因此不能仅凭指针值判断重建，证据以 teardown/eviction/import 日志和帧号重置共同确认。

实际诊断始终为 **visible_cameras=1、active_runtimes=1**（当前参与渲染的数量）。不声称完成双视图。重载相机初始化期间出现一帧旧版本1、1920×1080、零范围的过渡帧；未把它计入新来源版本2的成功证据。之后版本2正常产帧。

`kitchen.stdout.log` 无引擎 ERROR、CUDA_ERROR 或 `.embedded` 文件查找失败；CEF stderr 有 WebGL `ReadPixels` GPU stall 性能消息，不将它隐去，也不将它等同于 Vision 初始化失败。API 响应中的模式字段有异步滞后，本结论依据完成帧与 pipeline 日志。

证据：`runtime.py`、`analyze.py`、`kitchen-driver.log`、`kitchen.stdout.log`、`kitchen.stderr.log`、`kitchen.actions.json`、`kitchen.snapshot.json`、`results.json`。分析按 Windows 本地时间 UTC+8 将日志匹配操作窗口。场景已按原始字节恢复，SHA256 `55587b499d8ec3cc7448bbb06ba94bc546aaebe3ff2117f7fd6330278c96f478`；进程已退出。临时插桩已从正式源码撤回。

## 边界

不实现第 03 项完整跨 runtime 顶点/索引/拓扑传播。GPU 小场景直接从 Vision 最终图像读取像素，不依赖第 04 项 Horizon 截图接口；不将这视作编辑器截图功能已恢复。JSON 前置验证覆盖本项明确测试的结构和缺失资源，不能推定所有插件或任意损坏模型文件都已支持无异常恢复。


## 生命周期结论与交付

来源版本只在完整候选导入成功后递增；旧pipeline释放前等待CUDA及已记录的interop提交，随后清理view/bridge。新模式始终拥有独立render state；末个runtime退出后不再通过共享SceneData保有GPU对象。恢复路径从保留的来源重建加载缓存。来源CPU文档保留到完整clear/shutdown，runtime空闲淘汰不删除来源。

重载暂时同时保有候选与旧pipeline，存在峰值显存增加的代价；本机kitchen实际重载通过。没有扩展所有Vision插件的异常协议，也没有把截图接口的现状当作本项阻碍。

结论：本项实现与验收通过。实现提交 `ad262dbd777526bebedb32e865c1ecee695005bd` 已推送至 `origin/svgf_magic`；`git ls-remote --heads origin refs/heads/svgf_magic` 返回完全相同 SHA。核对后才将执行记录第02项标记完成。交付状态以本次后续文档提交保存，并再次推送核对；下一项由主协调会话派发。
