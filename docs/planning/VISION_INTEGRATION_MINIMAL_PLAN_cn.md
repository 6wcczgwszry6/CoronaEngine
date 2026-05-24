# Vision 渲染接入 CoronaEngine 最小改动详细计划

## 1. 文档目标

本文档用于指导将 Vision 渲染模块以最小改动方式接入 CoronaEngine，为其新增一种 **Vision 渲染模式**，使 CoronaEngine 的画面可以直接呈现 Vision 的渲染结果。

**产品目标**：在 CoronaEngine 现有 native 渲染模式的基础上，新增 Vision 渲染模式，用户（或编辑器）可在运行时切换，切换后画面即由 Vision 渲染引擎驱动输出。

核心目标：
- 在不改动 DisplaySystem 协议的前提下，复用现有图像句柄与事件流。
- 通过四类数据适配器完成 Corona CPU 数据到 Vision 数据格式转换（几何、光源、材质、**相机**）。
- 材质统一映射到 Vision 的 principled BSDF 路径。
- 支持 native 与 vision 两种渲染后端切换。
- 首版范围限定为静态几何、环境光、纯色材质。
- 先完成可运行、可切换、可验证版本，再进行性能优化。

---

## 2. 总体设计思路

总体采用 单点接入 + 适配层 + 输出桥接 的方式：

- 单点接入：仅在 OpticsSystem 内实现后端选择与调度。
- 四适配器：
  - 几何适配器：Geometry 数据到 Vision Mesh 和 Instance。
  - 光源适配器：Environment 和 Sun 参数到 Vision Light。
  - 材质适配器：OpticsDevice 参数与材质颜色纹理到 Vision principled BSDF Material。
  - **相机适配器**：从 OpticsSystem 当前视角收集相机位置、朝向、FOV、近远裁面等参数，转换为 Vision Camera。
- 输出桥接层：将 Vision 渲染结果写入现有 ImageStorage 句柄，并继续发布 OpticsFrameReadyEvent。

该方案可以保持 DisplaySystem 无感知，无需修改显示系统架构。

同时增加一条实现边界：

- 尽量不修改 Vision 内部渲染逻辑。
- 所有 Corona 到 Vision 的适配逻辑统一放在 OpticsSystem 目录下。
- 若 Vision 现有公开接口不足，仅允许补最小公开接口，不修改 Vision 的核心渲染算法、材质实现、几何处理主流程与积分器逻辑。

首版切换语义最终确定为：

- 支持运行时切换。
- 切换采用“下一帧生效”的安全热切换策略。
- 切换时允许在 OpticsSystem 线程内执行一次 Vision 资源重建与状态清空。
- 不要求无重建零停顿切换。
- 首版以稳定性优先，不追求切换过程中的完全无缝连续累积。

这意味着首版实现目标不是“两个后端同时常驻、瞬时无损切换”，而是“运行中可切换，并在下一帧以安全方式切入目标后端”。

---

## 2.1 首版确定方案

本项目首版实现方案已经固定，不再保留开放项，具体如下：

1. 接入位置固定
- 所有 Vision 接入逻辑都收敛在 OpticsSystem 下。
- 不新增独立 VisionSystem。
- DisplaySystem 不做协议修改。

2. 数据范围固定
- 只支持静态几何。
- 只支持环境光与太阳光参数。
- 只支持纯色材质。
- 不支持纹理。
- **相机参数**：从 OpticsSystem 当前帧视角数据中读取，支持基础透视相机（位置、朝向、FOV、近远裁面）。

3. 材质模型固定
- Corona 材质统一映射到 Vision principled BSDF。
- 首版仅使用基础颜色与基础 BRDF 标量参数。
- 具体映射关系：`materialColor` → `baseColor`，`roughness` → `roughness`，`metallic` → `metallic`，其余参数使用 Vision 默认值。

4. 切换行为固定
- 支持运行时切换。
- 切换在下一帧生效。
- 切换时清空 Vision 累积与缓存状态。

5. 输出路径固定
- Vision 输出继续写入现有 ImageStorage。
- 继续发布现有 OpticsFrameReadyEvent。
- DisplaySystem 无感知后端差异。
- 输出分辨率跟随当前 viewport 尺寸；若 viewport resize，Vision 输出随之重建。

6. Vision 修改策略固定
- 默认不改 Vision 内部逻辑。
- 如必须修改，仅允许补最小公开接口。
- 不允许将 Corona 适配逻辑写入 vision/ 目录。

7. 同步策略固定
- 首版允许全量重建 Vision 场景数据。
- 暂不做增量同步优化。

8. Vision 帧累积策略固定
- Vision 路径追踪采用逐帧增量累积模式，持续提升画质。
- 场景数据或相机发生变化时，清空已有累积帧，重新开始累积。
- 首版不设累积帧数上限，以稳定性为优先。

9. 坐标系适配固定
- 首版在适配器中统一处理 Corona 与 Vision 之间的坐标系转换（如存在差异）。
- 转换逻辑封装在各适配器内部，不散落到 OpticsSystem 主流程。

10. 错误处理策略固定
- Vision 单帧渲染失败时，输出上一帧结果（若有），并记录错误日志，**不自动 fallback 到 native**。
- 若连续失败超过阈值（首版建议 3 帧），触发告警日志，由用户主动切换回 native。

11. 切换请求传递机制固定
- 使用 `atomic` 标志位传递切换请求，OpticsSystem 在每帧渲染前检查并执行切换。
- 不使用消息队列，保持实现简单。

这就是首版的最终落地方案，后续实现以此为准。

---

## 3. 改动范围与文件清单

### 3.1 必改文件

1. src/systems/optics/optics_system.cpp
- 去除硬禁用 Vision 的逻辑。
- 增加后端分支调度：native 和 vision。
- 抽取公共帧数据收集逻辑。
- 接入 Vision 适配与渲染调用。
- 统一输出到现有 image_handle 和事件发布流程。

2. include/corona/systems/optics/optics_system.h
- 增加后端状态字段。
- 增加 Vision 渲染与输出桥接的私有方法声明。
- 增加适配器调用所需的缓存结构声明。

3. include/corona/systems/script/corona_engine_api.h
- 新增后端切换 API 声明。

4. src/systems/script/python/corona_engine_api.cpp
- 实现后端切换 API。
- 绑定脚本接口，支持编辑器和脚本触发切换。

### 3.2 建议新增文件

5. src/systems/optics/vision/vision_geometry_adapter.h
6. src/systems/optics/vision/vision_geometry_adapter.cpp

7. src/systems/optics/vision/vision_light_adapter.h
8. src/systems/optics/vision/vision_light_adapter.cpp

9. src/systems/optics/vision/vision_material_adapter.h
10. src/systems/optics/vision/vision_material_adapter.cpp

11. src/systems/optics/vision/vision_camera_adapter.h
12. src/systems/optics/vision/vision_camera_adapter.cpp

13. src/systems/optics/vision/vision_output_bridge.h
14. src/systems/optics/vision/vision_output_bridge.cpp

说明：若希望进一步减少文件数量，可先把三适配器与输出桥接实现为 optics_system.cpp 内部静态类，待跑通后再拆分。

目录约束：
- 优先将所有新增适配代码放在 src/systems/optics/vision/ 下。
- 不在 vision/ 目录下新增 Corona 专用适配实现。

### 3.3 可能需要轻量确认的构建文件

13. misc/cmake/corona_options.cmake
14. misc/cmake/corona_compile_config.cmake

仅确认 CORONA_BUILD_VISION 与 CORONA_ENABLE_VISION 宏链路是否按预期生效。

---

## 4. 分阶段实施计划

### 首版范围锁定

为控制改动范围并优先打通最小闭环，首版实现边界明确如下：

- 只支持静态几何，不覆盖动画、蒙皮、运行时网格拓扑变化。
- 只支持环境光参数，不接入点光、聚光、面光等额外灯光类型。
- 材质只支持纯色参数，不接入纹理采样链路。
- 材质目标模型仍统一适配为 Vision principled BSDF，但首版仅使用其纯色相关基础参数。
- 后端切换采用下一帧生效策略，允许安全重建，不要求无缝无重建切换。

以下能力明确延后：

- 法线纹理、金属度纹理、粗糙度纹理、透明度纹理。
- 多灯混合与复杂灯光类型映射。
- 动态网格、骨骼动画、形变几何增量同步。

### 阶段 A：后端切换骨架与输出链路保持

目标：先打通 vision 分支框架，不破坏 native 现有行为。

步骤：
1. 在 OpticsSystem 中增加后端枚举与当前后端状态。
2. 在 update 或 optics_pipeline 中增加分支：
- native 分支继续走现有路径。
- vision 分支调用新函数入口（先可为空实现）。
3. 保留原有 image_handle 写入和 OpticsFrameReadyEvent 发布逻辑，抽成统一函数。
4. 删除或替换硬编码场景路径逻辑，避免固定 json 依赖。
5. 将后端切换请求设计为“挂起状态”，在下一帧渲染开始前统一处理。
6. 处理切换时的 Vision 状态清空与安全重建。

完成标准：
- 工程在 Vision 开关关闭和开启时均可编译。
- native 路径渲染行为不变。
- 后端切换请求可在运行时提交，并在下一帧安全生效。

### 阶段 B：四适配器最小可用实现

目标：完成 CPU 数据到 Vision 数据结构的基础映射。

步骤：
1. 几何适配器
- 输入：Scene Actor Profile Optics Geometry Transform。
- 几何数据源优先使用模型资源中的 CPU mesh 数据，避免仅依赖 GPU buffer 句柄。
- 若 CPU mesh 数据不可用，跳过该物体并记录警告日志，不中断渲染。
- 输出：Vision Mesh 与 ShapeInstance。
- 首版仅处理静态 mesh 与 transform，不处理动画和拓扑变化。
- 适配器内部统一处理坐标系转换（如 Corona 与 Vision 存在差异）。

2. 光源适配器
- 输入：Environment 的 sun_position、sun_color、sun_intensity、sky_intensity。
- 输出：Vision directional 或 environment light。
- 首版仅处理环境光与太阳光相关参数，不支持额外灯光类型。

3. 材质适配器
- 输入：OpticsDevice BRDF 参数、materialColor、纹理句柄信息。
- 输出：Vision principled BSDF Material。
- 映射规则：`materialColor` → `baseColor`，`roughness` → `roughness`，`metallic` → `metallic`，其余参数取 Vision 默认值。
- 首版不接入纹理，材质仅使用纯色与基础 BRDF 标量参数。

4. 相机适配器
- 输入：OpticsSystem 当前帧视角数据（位置、朝向、FOV、近远裁面）。
- 输出：Vision Camera 对象。
- 坐标系转换封装在适配器内部。
- 相机参数每帧更新；相机变化时通知 Vision 清空累积帧。

完成标准：
- 单场景下可生成 Vision 可渲染场景对象（含相机）。
- 参数变化能够正确反映到 Vision 对象（允许首版全量刷新）。

### 阶段 C：Vision 渲染输出桥接

目标：让 DisplaySystem 可以直接显示 Vision 输出。

步骤：
1. 调用 Vision pipeline 执行渲染。
2. 将 Vision 帧缓冲结果拷贝或导入到 Horizon HardwareImage。
3. 写回 SharedDataHub image_storage 对应 image_handle。
4. 使用现有事件类型发布 OpticsFrameReadyEvent。
5. 确认 Vision 输出分辨率与当前 viewport 一致；若不一致，执行尺寸对齐或重建。

首版实现决策：
- 优先采用稳定的结果拷贝或格式转换写回方案。
- 不将”零拷贝共享输出”作为首版前置要求。
- Vision 单帧失败时，输出上一帧结果并记录日志，不自动 fallback。

完成标准：
- 不改 DisplaySystem 的情况下，主窗口可显示 Vision 渲染结果。
- native 与 vision 切换后均能稳定显示。

### 阶段 D：脚本接口与运行时切换

目标：从脚本或编辑器触发后端切换。

步骤：
1. 新增 set_render_backend 接口。
2. 增加 get_render_backend 用于 UI 状态展示（可选但建议）。
3. 切换时触发必要资源重置（例如清累计帧、重建或标记重建 Vision 场景）。

首版实现决策：
- 切换接口提交请求，不直接在外部线程即时改后端状态。
- 真正的后端切换与资源重建只在 OpticsSystem 更新线程内执行。

完成标准：
- 运行中可在 native 和 vision 间切换。
- 切换后首帧有效，无崩溃或黑屏长期停留。

### 阶段 E：增量优化（非首版阻塞）

目标：降低首版全量重建开销。

步骤：
1. 增加 mesh 和 material 缓存键（如 model_id、mesh_idx、material_hash）。
2. 对 transform、environment 参数采用增量更新。
3. 仅在资源变化时重建加速结构。

完成标准：
- 切换后首版功能不回退。
- 大场景帧时延和内存占用可控。

---

## 5. 关键技术约束与决策

1. DisplaySystem 不改协议
- 保持 image_handle 与 OpticsFrameReadyEvent 不变，降低联动风险。

2. 首版优先正确性
- 首版允许全量同步，先确保可渲染与可切换。

补充决策：
- 首版优先可验证与稳定，不优先最优性能。

3. 适配器输入统一
- 适配器不直接访问 UI 或脚本层，仅接收 Optics 收集好的帧数据。
- 相机适配器同样仅从 OpticsSystem 当前帧数据读取，不直接访问编辑器视口。

4. 宏开关策略
- Vision 相关编译代码必须受 CORONA_ENABLE_VISION 保护。

5. Vision 修改红线
- 不在 Vision 内部引入 Corona 数据结构。
- 不修改 Vision 的材质模型内部实现，Corona 侧统一适配到 Vision principled BSDF。
- 不修改 Vision 的积分器、核心渲染流程、几何求交主路径。
- 若确实缺少外部调用入口，仅允许增加最小公开接口，并保持 Vision 对 Corona 无反向依赖。
- **在开始阶段 B 前，需先对 Vision 现有公开接口进行一次盘点**，确认几何、光源、材质、相机、渲染调用、输出读取各环节的接口是否完备，提前识别需要补充的最小公开接口，避免阶段 B/C 返工。

6. 切换线程模型
- 外部系统只能发起切换请求，使用 `atomic` 标志位传递。
- OpticsSystem 在每帧渲染开始前统一检查并执行切换，是唯一允许实际提交后端切换和资源替换的线程。
- 不做跨线程即时抢占式切换。

7. 坐标系适配
- 如 Corona 与 Vision 存在坐标系差异（如 Y-up vs Z-up），统一在各适配器内部处理转换。
- 转换逻辑不散落在 OpticsSystem 主流程中。

8. Vision 帧累积
- Vision 路径追踪采用逐帧增量累积，持续提升画质。
- 场景数据或相机变化时清空累积帧。
- 首版不设帧数上限。

---

## 6. 风险清单与应对

1. 风险：相机参数缺失或无对应接口
- 应对：阶段 A 前盘点 Vision 相机接口，确认 position/direction/fov/near/far 的设置入口；若缺失则补最小公开接口。

2. 风险：Vision 公开接口不完备（各适配器调用入口缺失）
- 应对：**阶段 B 开始前**完成接口盘点，提前记录需补充的接口列表，避免中途返工。

3. 风险：几何 CPU 数据缺失或来源不一致
- 应对：通过 model_resource_handle 回查资源层 Scene 的 mesh 顶点索引；CPU 数据不可用时跳过该物体并记录警告，不中断渲染。

4. 风险：坐标系不一致导致画面错误
- 应对：阶段 B 初期先对比 Corona 与 Vision 坐标系约定，确认是否需要转换，统一封装在适配器内。

5. 风险：Vision 输出格式与 HardwareImage 不匹配
- 应对：增加统一格式转换和尺寸对齐逻辑，首版固定输出格式，viewport resize 时重建 Vision 输出。

6. 风险：切换时资源生命周期冲突
- 应对：切换动作串行化，在 OpticsSystem 线程内执行重建和替换；atomic 标志位保证线程安全。

7. 风险：首版性能波动较大
- 应对：先保证功能，再做缓存和增量策略。

8. 风险：Corona 材质参数与 Vision principled BSDF 语义不完全一致
- 应对：首版只做稳定的一对一主参数映射（materialColor→baseColor / roughness→roughness / metallic→metallic），明确不追求完全视觉一致；差异通过映射表和后续校准迭代处理。

9. 风险：Vision 路径追踪累积帧导致切换后画面短暂噪点
- 应对：切换时主动清空累积帧，告知用户 Vision 模式需若干帧收敛，属预期行为。

10. 风险：环境光首版范围过窄，用户预期包含其他灯光类型
- 应对：文档与实现都明确首版只支持环境光与太阳光，其他灯光延后到下一阶段。

---

## 7. 验收标准

### 功能验收
- native 后端正常渲染。
- vision 后端正常渲染。
- 运行中可从 native 切换到 vision，再切回 native。
- DisplaySystem 无代码改动仍可显示两者输出。
- 静态几何场景可正确显示。
- 环境光参数变化可传递到 Vision。
- 纯色材质可正确映射到 Vision principled BSDF。
- 切换请求在下一帧生效，且切换后首帧输出有效。

### 稳定性验收
- 连续切换 50 次无崩溃。
- 场景加载后连续运行 10 分钟无显存泄漏趋势。
- 切换过程中允许发生一次安全重建，但不允许长期黑屏或卡死。

### 可维护性验收
- 适配器职责边界清晰。
- optics_system.cpp 不再包含硬编码 Vision 场景路径。

---

## 8. 推荐实施顺序（两周样例）

- 第 1 到 2 天：阶段 A
- 第 3 到 5 天：阶段 B
- 第 6 到 7 天：阶段 C
- 第 8 到 9 天：阶段 D
- 第 10 天：联调与回归
- 第 11 到 14 天：阶段 E 与文档补充

---

## 9. 回滚策略

若 Vision 分支出现问题：
- 通过后端开关强制回退 native。
- 保留所有 native 渲染路径与事件发布逻辑。
- Vision 代码受编译宏保护，可一键关闭构建。

---

## 10. 后续扩展建议

- 将适配器抽象为可插拔后端接口，为未来接入更多渲染器预留统一边界。
- 将输出桥接扩展为多输出通道，支持调试视图和离线导出。
- 在编辑器中加入后端切换与状态诊断面板。

---

## 11. 实施结论

本文档对应的首版方案已经完全确定，后续不再保留以下开放讨论项：

- 是否支持动态几何：否。
- 是否支持多类灯光：否。
- 是否支持纹理：否。
- 是否采用无缝零重建热切换：否。
- 是否需要修改 DisplaySystem：否。
- 是否允许把适配逻辑写进 vision/：否。
- 是否自动 fallback 到 native：否，Vision 失败保留上一帧并记录日志。
- 相机是否单独适配：**是**，作为第四个适配器（vision_camera_adapter）。
- 坐标系转换由谁负责：各适配器内部封装，主流程不感知。
- 切换请求传递机制：atomic 标志位，OpticsSystem 每帧前检查执行。
- 帧累积策略：逐帧增量累积，场景或相机变化时清空，首版不设上限。
- 材质映射规则：materialColor→baseColor，roughness→roughness，metallic→metallic，其余取 Vision 默认值。

首版唯一目标是：

- 在尽量不修改 Vision 内部逻辑的前提下，
- 通过 OpticsSystem 下的四个适配器（几何、光源、材质、相机）与输出桥接，
- 让 CoronaEngine 能在运行时切换并以 Vision 渲染模式驱动画面输出。