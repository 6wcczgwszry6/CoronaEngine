# Native Optics 相机延迟与积压稳定性设计

## 背景与结论

当前多物体场景每帧最多提交约 1997 万个索引三角形，其中四级联阴影占 80%。GPU 长时间接近满载时，Native Optics 仍持续提交新帧。Horizon 的 `HardwareExecutor::wait(receipt)` 只建立 GPU 依赖，不会阻塞 CPU；命令缓冲和 `FramePlaceBufferPool` 因而随在飞帧数扩张。每个新 FramePlace 槽至少分配五个 storage-buffer descriptor，而 bindless storage-buffer 表只有 4096 项且不回收，持续积压最终会异常退出。

同时，`OpticsSystem::optics_pipeline` 通过 `SceneStorage::ConstIterator` 持有当前场景的共享锁，并把锁跨越实例收集、命令录制和 GPU 提交。Geometry 更新 `visible_actor_handles` 需要同槽位写锁，因此渲染变慢时 Geometry 也被连带阻塞。Camera 的读取句柄同样跨越整帧，虽然它不是本次 Geometry 阻塞的主因。

当前工作区新增的逐 draw/dispatch 调试标签每帧无条件使用 `std::ostringstream` 构造，并触发 Vulkan DebugUtils marker。它们应只在 `CORONA_OPTICS_DIAG_PROFILE=1` 时启用。

## 目标

- Native Optics 在任何 GPU 负载下最多保留 2 个未完成提交。
- 等待只针对 receipt 中的 timeline token，不调用共享队列级 `wait_idle()`。
- 等待最老帧之后再消费最新相机移动，使中间相机状态被合并而不是依次渲染。
- Scene 和 Camera 的 Storage 锁只用于复制快照，不跨越实例收集、录制或提交。
- 普通运行不构造逐 draw/dispatch 标签；诊断模式保留现有标签内容。
- 不改变阴影、SSAO、曝光、分辨率或模型几何，便于单独验证延迟与稳定性修复。

## 备选方案

### A. 精确 timeline 反压与存储快照（采用）

在 Horizon 为 `HardwareExecutor` 增加 receipt 精确完成等待 API。Optics 用一个小型 FIFO 跟踪 Native receipts，在提交第三帧前等待并移除最老帧。该方案直接限制资源高水位，同时只等待必要工作。

### B. Optics 直接调用 `wait_idle(receipt)`

改动最小，但现有实现对 receipt 中每个 token 调用 `Queue::wait_idle()`，会等待共享物理队列上的所有提交，包括比目标 token 更新的无关工作。它可能把秒级积压变成明显停顿，因此不采用。

### C. 仅优化阴影、shader 或降低画质

能提高吞吐量，但只要负载再次超过 GPU 能力，无界提交、FramePlace 扩张和描述符耗尽仍会重现。它属于第二阶段，不替代本设计。

## 架构

### Horizon receipt 完成等待

为 `HardwareExecutor` 增加 `wait_until_complete(const SubmitReceipt&)`。它按 token 的 device/queue capability 使用现有 resolver 定位队列，调用 `Queue::wait_for(token)` 等待该 timeline 值，然后调用 `retire_completed()` 释放对应命令缓冲和 keep-alive。空 token 被忽略；无法解析队列或 device-lost 沿用现有异常策略。

该 API 与 `wait(receipt)` 语义明确区分：`wait` 只把依赖附加到下一次 GPU 提交，`wait_until_complete` 是 CPU 完成等待。

### Native 两帧限制器

新增只负责 FIFO 状态的 `NativeFrameLimiter`：

- 最大在飞数固定为 2；
- 空 receipt 不进入队列；
- `oldest()` 返回需要等待的 receipt；
- 成功等待后 `retire_oldest()`；
- shutdown 逐个排空。

`OpticsSystem::update()` 在应用 pending camera move 前先确保有一个提交空位，避免等待期间捕获旧相机姿态。每个 Native camera 开始录制前再次确保容量，以覆盖多相机场景。commit 成功后才跟踪 receipt。

### Scene/Camera 快照

新增内部模板帮助函数：

- `snapshot_storage(storage)` 在短生命周期迭代器内复制所有对象到 `std::vector<T>`；
- `snapshot_storage_value(storage, handle)` 在短生命周期读句柄内复制单个对象到 `std::optional<T>`。

Native 渲染遍历快照而不是 Storage 句柄。Geometry 可在 CPU 收集、命令录制和 GPU 等待期间更新下一份可见集。

### 调试标签策略

把标签格式化函数移到内部 `optics_debug_labels` 单元，并增加 `enabled` 参数。`enabled=false` 时在创建 `std::ostringstream` 前立即返回空字符串。所有 Native、UI、shadow、actor-pick 和 dispatch 标签均传入 `optics_diag_config().profile`。Horizon 对空标签已经不会发出 DebugUtils marker。

## 测试与验收

自动测试覆盖：

1. Horizon 精确等待 token 1 后只回收第一个 fake-queue submission，token 2 仍在飞，证明没有退化为 queue idle。
2. `NativeFrameLimiter` 永远不允许在未等待时跟踪第三个非空 receipt，FIFO 顺序正确，空 receipt 被忽略。
3. Storage 快照与原对象独立，并在函数返回后可立即取得原槽位写锁。
4. 普通模式 draw/dispatch 标签为空；诊断模式保留现有关键字段。
5. `corona_engine` RelWithDebInfo 增量构建通过。

运行时验收使用正常阴影和 deferred compute：进入同一 43 mesh、约 399 万三角形场景，持续移动相机 30 秒。日志中不得出现 descriptor-array-full、device-lost 或新的异常；在飞 Native receipt 高水位不得超过 2；Geometry 不再因 Optics 持有 Scene 读锁而降到数秒一次。GPU 仍可能因原始几何和 shader 成本保持高占用，这部分由第二阶段优化处理。

## 范围边界

本阶段不实现级联阴影视锥剔除、运行时 LOD、shader finite-check 清理、SSAO 半分辨率、bindless descriptor free-list 或 Python shutdown 修复。这些改动彼此可独立验证，待本阶段数据确认后分批实施。
