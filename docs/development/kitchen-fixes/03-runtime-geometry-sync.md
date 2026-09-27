# 03：独立渲染运行时的完整几何同步

状态：已取得跨 GPU runtime 的失败复现并修复；正式构建、47项测试及本项kitchen验证通过，交付以[执行记录](execution-tracker.md)为准。证据与限制见[第03项审核](reviews/03-runtime-geometry-sync-review.md)。关联[总览](README.md)、[模式创建方案](02-embedded-mode-switch.md)。

## 当前缺口

修复前，同一个共享场景每帧只由一个 runtime 执行 external-live 同步。其他 runtime 经 `upload_shared_scene_transforms_if_needed()` 只消费逻辑实例矩阵；生产路径测试确认顶点原位从z=0修改到z=1后，第二runtime的CPU和CUDA命中仍为z=0。

不能仅增加版本号，因为另一 runtime 仍可能保留旧顶点。也不直接共享整个 `SceneData`：其中包含 Geometry、材质等与当前 GPU 所有权设计相关的对象，扩大共享范围会引入额外生命周期问题。

## 解决方案

由 `VisionSceneResource` 发布不含 GPU 句柄的最新 CPU 几何快照和 `geometry_version`。快照包含实际顶点、三角形索引、稳定形状身份、实例成员及材质/光源CPU描述。消费runtime本地创建新增材质，面积光随实例重排重绑定、删除时清理。仅在初始化或确认几何内容／成员发生变化时复制并发布，静止帧不重复复制。

每个 runtime 保存 `applied_geometry_version`，与现有 transform version 分开。在渲染线程当前同步阶段发布快照与版本，消费方先取得匹配版本的完整快照，再更新自己的 SceneData 和 GPU 资源。无需为当前任务增加通用跨线程事件框架。

| 变化 | 必要处理 |
|---|---|
| 仅实例变换／可见性 | 应用矩阵，更新实例和场景范围，上传实例数据及 TLAS |
| 顶点、索引、网格或实例成员变化 | 应用完整几何内容，更新网格注册和范围，重建必要缓冲、BLAS/TLAS |
| runtime 休眠后恢复 | 渲染前消费最新版本，不要求回放已被覆盖的所有中间版本 |
| 来源重载 | 淘汰旧来源的快照／消费状态；新来源版本与几何版本一起校验 |

初版可以沿用当前 runtime 的完整几何重建，先保证正确性，不把局部 BLAS 优化混入本轮。

## 数据流和所有权

1. 生产同步入口检测到几何内容变化，更新权威 CPU 状态。
2. 完整快照与新版本一次发布；不发布仅有版本、没有内容的半成品。
3. 每个 runtime 渲染前，若落后于发布版本，等待其旧资源关联的 GPU 提交完成。
4. 替换 CPU 几何并注册网格，应用当前变换，刷新实例／组／场景 AABB。
5. 重建 GPU 缓冲及加速结构，更新相关光照数据和历史。
6. 只有上述步骤成功后记录消费版本；消费过程不得把自己的旧几何反向发布成新版本。

不把运行时指针或数组位置作为跨快照的持久形状身份。复用已有 shape GUID／identity 与逻辑实例映射，处理重排和删除，防止误保留已移除实例。

## 修改位置

- `include/corona/systems/optics/vision_scene_resource.h`：快照所有权及版本。
- `src/systems/optics/optics_system.cpp`：发布入口、每个 runtime 的消费顺序与 GPU 生命周期。
- `src/systems/optics/vision/vision_external_live_aabb.h`：几何变化信号和缓存失效协作。
- `src/systems/optics/vision/vision_geometry_snapshot.h`：CPU快照与本地暂存导入。
- `src/systems/optics/tests/test_vision_runtime_geometry_sync.cpp`：实际双 runtime 集成测试。
- Vision的Shape、Scene、Geometry、Pipeline、Material、Light：稳定身份、build计数、几何重建光照刷新、CPU描述保留与面积光成员映射。

## 实施与验收

- [x] 先创建独立 SceneData、独立 GPU 几何资源的两个 runtime；在第一份几何中原位修改顶点，确认当前第二份的 CPU／GPU 结果滞后。
- [x] 使用确定性射线，断言两边命中位置／距离与新几何一致；不能只比较 GPU 资源地址或版本数。
- [x] 覆盖地址和数量不变的顶点／索引编辑、网格替换、实例增删重排、隐藏恢复、休眠恢复和场景重载。
- [x] 验证一次几何变化每个 runtime 只消费一次，单纯相机移动不重建 BLAS，不复制快照。
- [x] 注入上传前CPU导入失败，确保消费版本没有提前推进、旧GPU仍可用、同版本可重试；不声称设备级上传故障注入通过。待完成interop receipt替换分支未实测，见审核限制。
- [x] 在两个不同模式真实产帧时复验；实际 runtime 数量为 2。

若首次失败测试发现几何已经通过另一条有效路径共享，应收缩方案到实际缺口，不重复建设快照机制。是否完成以生产同步路径上的数值与 GPU 证据为准。
