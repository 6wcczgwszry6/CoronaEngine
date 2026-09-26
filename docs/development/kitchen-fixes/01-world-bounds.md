# 01：场景总包围盒与光照数据同步

状态：已复现，待修复。关联[总览](README.md)、[原始验收证据](../kitchen-aabb-acceptance.md)。

## 问题与原因

将 kitchen 的 `shape_0` 移至 `[100,200,300]` 后，在物体因距离被卸载前，最新组包围盒的并集半径约为 189.32784，`Scene::world_radius()` 却仍为 10，中心也未改变。静止时几何半径小于最小半径 10 属于正常钳制，但不能解释此次差异。

当前同步更新了实例、组 AABB，没有刷新 `SceneData::aabb_`。此外，方向光在 `prepare()` 中缓存场景中心和半径，仅修复 CPU getter 会留下旧光照数据。

## 解决方案

新增 `bool Scene::recompute_world_bounds() noexcept`（拟定接口），从有效组 AABB 重新求并集，替换旧场景范围并报告是否变化。它只读取已有组包围盒，不遍历三角形。不能只向旧场景范围 `extend`，否则物体移回或删除后范围不会缩小。

以一次场景变更批次为单位执行以下顺序：

1. 完成实例变换、几何成员、实例／组 AABB 更新。
2. 对当前 SceneData 的组范围聚合一次。
3. 范围改变时更新依赖它的光源编码数据、相关采样分布和 GPU 上传。
4. 使受影响的渲染累积／降噪历史失效，然后渲染新帧。

拟定 `Pipeline::refresh_world_bounds_dependents()` 封装第 3 步，必须使用该 pipeline 的 GPU 上下文。实施前逐项核对范围消费者，不能假定调用一次方向光 `prepare()` 就完成所有上传。

静止帧直接跳过聚合与上传。只有变换／成员／几何变化触发范围更新，不为相机移动增加物体 AABB 工作。多个独立 SceneData 分别维护范围。

## 修改位置

| 文件 | 职责 |
|---|---|
| `vision/src/base/mgr/scene.h`、`scene.cpp` | 聚合并保存场景范围，保留最小半径规则 |
| `vision/src/base/mgr/pipeline.h`、`pipeline.cpp` | 刷新范围相关 GPU 数据及历史 |
| `src/systems/optics/optics_system.cpp` | external-live、共享变换应用、增删／重建批次的调用顺序 |
| `vision/src/render_core/light/environments/directional.cpp` | 核对中心／半径缓存及更新路径 |
| `src/systems/optics/tests/test_external_live_aabb.h`、`test_vision_geometry_gpu_resource.cpp` | CPU 与 GPU 回归 |

## 边界规则

- 无有效组时保持内部空 AABB 语义；对外中心返回有限值（建议原点），半径使用现有最小半径下限，避免对无效区间求中心产生 NaN。
- 隐藏物体是否贡献范围沿用现有可见性语义，测试中明确其预期；不要顺带改变隐藏表示方式。
- 同一变更批次先完成全部组更新，再聚合，避免中间状态进入光照。
- 不把 kitchen 的 189.32784 写成通用断言，期望值应从测试几何独立计算。

## 实施与验收

- [ ] 先写移动后范围变化的失败测试，确认旧实现失败。
- [ ] 覆盖向外移动、移回、旋转、非均匀缩放、隐藏恢复、删除最后一组、重载；对比中心、半径及最小半径规则。
- [ ] 检查方向光编码数据及 GPU 消费结果，排除“CPU 正确、GPU 仍旧”。
- [ ] 复跑 kitchen 远距离移动，在卸载前的更新帧比较实际值和参考并集。
- [ ] 静止及相机移动时，三角形 AABB 调用为 0；仅变更时增加一次场景聚合。

失败时不记录“GPU 数据已更新”版本，修复与其回归测试独立提交。恢复旧实现只能作为排查手段，不能保留“范围错误但性能通过”的验收状态。
