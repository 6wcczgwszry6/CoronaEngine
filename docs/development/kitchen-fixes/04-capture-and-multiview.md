# 04：GPU 截图读回与双视图验收

状态：截图禁用已由日志确认；双视图尚未获得实际同时渲染证据。两者分别验收，不能合并为“API 调用成功”。关联[总览](README.md)。

## 当前情况

截图请求在 OpticsSystem 无条件返回失败，日志为 `Screenshot capture temporarily disabled - new Horizon API needed`。旧 `copy_to_buffer` 已移除，因此当前没有可供 kitchen 图像对照的有效截图。

第二相机创建并切为 Vision 的 API 返回成功，但日志仍为 `visible_cameras=1`。创建入口设置了 offscreen 状态和 surface=0；这只能证明 camera 对象存在，不能证明第二个可见窗口已进入渲染调度。最终根因仍需沿真实窗口／surface 注册路径验证。

## A. 截图解决方案

先核对 Horizon 公开的图像读回能力，使用其提交与完成机制。已知 `HardwareExecutor::wait(const SubmitReceipt&)` 可用于等待提交，但该接口本身不提供像素复制。

若公开 API 已支持读回，直接复用；若缺失，在 Horizon 添加并测试 image→host readback 接口，单独提交再更新 Engine 依赖锁。不要在 Engine 中依赖 Vulkan 后端私有句柄，也不要恢复已经移除的旧接口名称。

请求生命周期：

1. 定位目标相机及其完整最终输出，记录请求对应的尺寸和像素格式。
2. 保证输出生产者已完成，提交图像到 host 可读缓冲的复制及必要同步。
3. 等待该次复制 receipt；需要时完成非一致内存的可见性处理。
4. 根据实际格式、行跨度、方向及颜色空间转换，保存目标图像。
5. 成功保存后完成 promise；错误、窗口关闭、resize、shutdown 时明确结束请求并安全回收资源。

不能默认所有输出都是 RGBA16F；不能把显示编码后的结果再做一次 gamma 转换。初版可同步等待，不引入后台截图队列等无关扩展。正常帧不发起请求时不得分配截图缓冲。

## B. 双视图解决方案

沿编辑器真实打开视口的链路，核对 camera view_open、surface 注册、可见性及 Optics 分组。若创建相机与打开可见视图是不同操作，测试应执行完整流程，而不是把 offscreen camera 强行当作可见窗口。

分别验证：

- 同模式两个相机：`visible_cameras=2`，两份相机输出持续产生；允许共用一个 runtime。
- PT 与 SVGF 两个模式：`visible_cameras=2`、`active_runtimes=2`，两份输出使用各自正确的模式。
- 移动一个相机只改变该视角；变更共享物体后，两边几何、范围和 GPU 结果均更新。
- 关闭或最小化一个视口、再恢复，不导致另一视口丢帧状态、引用释放错误或恢复后的旧几何。

## 修改位置和依赖

| 位置 | 修改／验证责任 |
|---|---|
| `src/systems/optics/optics_system.cpp` | 截图请求处理、帧资源及完成通知 |
| `src/systems/ui/cef/cef_editor_native_api_handlers.cpp` | 相机／可见视口入口，保护原有相机状态 |
| `tests/integration/ui_multisurface_smoke.cpp` | 参考已有 GPU 像素、surface 生命周期验证 |
| `tests/systems/optics/test_vision_geometry_gpu_resource.cpp` | Vision 输出及多 runtime 结果验证 |
| Horizon 公开接口与后端 | 仅当缺少公开读回能力时修改，保持依赖锁与测试版本一致 |

不同模式的双视图验收依赖 [02](02-embedded-mode-switch.md)；共享几何结果验收依赖 [03](03-runtime-geometry-sync.md)。

## 实施与验收

- [ ] 固定小尺寸图案读回：断言尺寸、通道、颜色、行排列和方向；覆盖当前实际使用的浮点与显示输出格式。
- [ ] 验证请求只完成一次，GPU 未完成时不读／释放缓冲，关闭窗口或 resize 后不悬挂。
- [ ] 截取 Vision 最终图，不能以 CEF UI 背景截图冒充场景结果；截图前后相机姿态与输出模式保持一致。
- [ ] 两个相机输出均有帧标识、尺寸和更新记录；不同模式下记录两个实际 runtime。
- [ ] 几何正确性优先使用确定性射线／图案；PT 图像比较固定种子或预先约定误差指标，记录降噪和累积状态，不要求不受控随机噪声逐像素相等。
- [ ] 完成前述检查后，回到 kitchen 全量验收，保存图像、日志、性能采样和参考期望。

不能通过静默跳过读回测试、只检查文件存在、只检查 camera 数量或只检查 mode 字段关闭此问题。
