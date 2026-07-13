# R3-min 推进记录

更新时间：2026-07-13

## 1. 当前结论

本轮按“双轨但有硬门槛”推进：

```text
主线 A：Game-ready Scene Runtime 收口
并行 B：SceneWorldSnapshot + 只读 SceneInspectorAgent
```

没有恢复旧 Workflow 用户入口，没有引入可执行下游 Agent，也没有扩展 VLM、Provider 或 UI。

## 2. 里程碑状态

| 里程碑 | 状态 | 本轮结果 |
|---|---|---|
| M0 基线冻结 | 已完成 | 建立 `13740c16` R3-min 基线；同步 `origin/main`；Quasar provider 基线对齐；本地配置继续隔离 |
| M1 Snapshot API | 自动验证通过 | 新增只读 `runtime.scene_world_snapshot.get`；支持 plan/version 选择；零 ToolGraph、PlanPatch、Provider 和 Engine 写入 |
| M2 Readiness 收口 | 自动验证通过，待 F5 | batch terminal 后对 partial 实体执行 readiness reconcile；actual AABB、support、sync 均进入 Game-ready 判定 |
| M3 单机三场景 | 待 F5/实机验证 | 儿童卧室、森林营地、室内外混合场景尚需真实 Engine 五方对账 |
| M4 SceneInspectorAgent | 自动验证通过 | 只读取 Snapshot，输出结构化 SceneAnalysis；无 LLM、Provider、PlanPatch 或 Engine 写入 |
| M5 多人权威与一致性 | 部分完成，待 F5 | 客户端 Runtime write 被权威门禁阻断；双入口消息去重已有测试；真实广播和多端 Snapshot 一致性待实机 |

## 3. 新增只读接口

```text
runtime.scene_world_snapshot.get
```

请求：

```python
{
    "room_id": str,
    "plan_id": str | None,
    "min_version": int | None,
}
```

响应核心字段：

```python
{
    "found": bool,
    "plan_id": str,
    "scene_version": int,
    "world_readiness": "game_ready | needs_review | blocked",
    "snapshot": dict,
    "operation_cursor": str,
    "snapshot_stability": "immutable | provisional",
}
```

终态优先读取 Finalizer 已持久化报告中的不可变 Snapshot；执行中返回 `provisional`，供只读观察使用，不允许作为可执行下游 Agent 的写入依据。

## 4. Readiness 口径

实体进入 Game-ready 必须具备：

```text
stable entity_id
actor_id
asset_id / model_ref
actual transform
engine_actual world AABB
明确 support / grounding
已知 sync_status
engine_verified
```

支撑语义已区分：

```text
room_floor / terrain -> grounded
room_box / room_shell -> enclosure
wall entity -> wall_mounted
hanging entity -> suspended / ceiling_hung
sky 等无支撑组件 -> not_applicable
```

`estimated` AABB、未知 grounding 或未知 sync 不计入 Game-ready，并在 `readiness_missing_fields` 中列出原因。

## 5. 下游 Agent 边界

当前仅提供 `SceneInspectorAgent`：

```text
SceneInspectorAgent
-> runtime.scene_world_snapshot.get
-> SceneAnalysis
```

它不读取聊天历史或 Engine 内部对象，不调用 Provider，不创建 PlanPatch，不执行 add/move/delete。只有实体明确声明 `interaction_capability` 时，才进入 `interaction_candidates`；未知能力保持为空。

完整 R3 前禁止接入可执行下游 Agent。后续写入必须统一经过：

```text
ActionProposal
-> Validator
-> PlanPatch
-> business ToolCallGraph
-> RuntimeGuard
-> EngineWriteGate
-> StatePatch
-> SceneWorldSnapshot version +1
```

## 6. 自动验证

已通过：

```text
34 项 Runtime / ActionIntent / Snapshot / Inspector / ModelImport 聚焦测试
LANChat Runtime Guard 回归
Python syntax compile
```

额外修复：远端统一 `RemoteTaskRunner` 恢复瞬时查询断连重试，保持“任务只提交一次，poll 可重试”，避免重复提交混元任务。

## 7. 下一轮 F5

### 儿童卧室

- 对账 room_box、room_floor、家具和追加实体。
- 核验 Engine、RuntimeState、OperationLog、Registry、Snapshot、final report 的 ID、数量和版本。

### 森林营地

- 草地、天空、森林进入 environment/substrate。
- 帐篷、小木桌进入 actor/model。
- 不生成 room_box。

### 室内外混合

- terrain、room shell、floor、transition zone 身份独立。
- Snapshot 能分别查询环境和普通实体。

### 多人

- 非房主端不调用 Provider。
- Actor、PlanPatch、回复各出现一次。
- 房主与成员 `entity_id + version` 一致。
- 同步失败时 Snapshot 明确标记 `partial`。

以上真实 Engine、渲染、碰撞、同步和多端一致性均标记为 **[待 F5/实机验证]**。

## 8. Entity Version 闭环

本轮补齐了 `scene_entity_registry -> SceneWorldSnapshot -> SceneInspectorAgent` 的实体版本语义：

- 每个 actor、environment、substrate 实体均输出正整数 `version` 和 `version_source`。
- C++/Engine 返回 `actor_version` 时优先采用真实版本；没有真实版本时回退到当前 `ScenePlan.version`。
- Actor 导入时独立生成稳定 Runtime `entity_id`，不再默认把 native actor handle 当作实体身份。
- Registry 同时保留 `actor_id`、`source_plan_id`、`source_batch_id`，便于定位实体来源。
- `SceneInspectorAgent` 输出实体版本，Snapshot 版本变化后必须重新分析。

自动验证已覆盖 native actor handle 变化但稳定请求身份不变、Engine 版本优先和 ScenePlan 版本兜底。

房主端与成员端是否能稳定按 `entity_id + version` 去重仍标记为 **[待 F5/实机验证]**。

## 9. M5 多人 Scene Sync 代码闭环

本轮补齐了 LANChat 多人场景同步中原先只打印占位日志的前端断点：

- 房主端通过 `scene.listActorTree` 获取真实 Actor 快照，并继续使用现有 NetworkSystem 广播。
- 成员端在模型文件传输完成后，通过 `sceneTools.createActor` 创建 Actor；重复消息使用 `actor_guid` 和版本账本幂等处理。
- Actor state/transform 更新复用同一 native create/update 接口，设置 `skip_if_exists/update_if_exists`，不重复创建实体。
- 旧版本更新不得覆盖成员端已应用的新版本。
- `__room_box`、`__room_terrain`、`__terrain_boundary` 等 AI 场景框架实体进入同步允许列表，不再因 `__` 前缀被前端过滤。
- 接收端写入期间设置 `_suppress_network_broadcast` 并暂停 dirty sync，避免回环广播。
- Python 发布侧按 `scene + actor_guid` 对 Actor create 做全生命周期去重；Actor 版本变化只走 state/transform 更新，不再次广播 create。

自动验证已覆盖：

```text
LANChat Scene Sync 静态协议检查
Actor create 跨事务去重
Actor version 变化不重复发布 create
Python syntax compile
```

仍需明确区分：以上说明前端与 Python 同步接口已经接通，不代表多人实机已通过。以下继续标记为 **[待 F5/实机验证]**：

- 房主和成员实际出现相同的 environment/actor 集合。
- 真实 transform 更新能在两端保持一致且无乱序回退。
- 模型文件传输完成后 Actor 只创建一次，且 UI 不发生明显卡顿。
- `scene_entity_registry` 与两端 Engine Actor 的 `entity_id/version` 一致。
- 当前 C++ 文件传输主要按项目相对路径复用；跨路径按稳定 `asset_id` 去重仍需后续协议收口，不能在本轮宣称完成。

## 10. Runtime 实体身份贯通 C++ Actor

本轮补齐了 `SceneWorldSnapshot` 与 Engine Actor 快照之间的身份断点：

- 普通模型和 environment 导入在进入 `RuntimeGuard -> EngineWriteGate` 前生成并携带稳定 `actor_guid`、`entity_id`、`asset_id/model_ref`、`source_plan_id/source_batch_id` 和初始版本。
- C++ `NativeEditorActor` 保存上述 Runtime 元数据，并通过现有 Scene actors INI 持久化；场景重载后不应退化为仅有 native handle 的匿名 Actor。
- `actor_to_json()` 将 Runtime 身份和 `actor_version/version` 原样返回，现有 LANChat actor snapshot 无需扩展网络包即可携带同一实体身份。
- 原生 transform 写入成功后递增 `actor_version`，成员端可继续按 `actor_guid + version` 拒绝过期更新。
- environment 事实将 C++ `actor_version` 归一为 Runtime `entity_version`，继续满足现有 Environment schema。

聚焦自动验证覆盖：

```text
普通模型导入保留 Runtime 身份
environment 导入保留 Runtime 身份
C++ Actor snapshot 输出身份和版本
C++ Scene actors 持久化/重载身份字段
transform 更新递增 actor_version
Python syntax compile
```

以下仍为 **[待 F5/实机验证]**：

- native 场景保存并重载后 `entity_id/asset_id/version` 在面板快照中保持不变。
- 房主与成员收到相同 `entity_id + actor_version`，且旧 transform 不覆盖新版本。
- Registry、SceneWorldSnapshot 与两端 Engine Actor 的身份、数量和版本一致。
- 跨路径模型资源按稳定 `asset_id` 去重传输。

本轮尝试运行一次 `verify_ultimate_plan.py` 总门禁，但当前进程持续约 54 分钟仍未退出；同一工作站还存在更早启动且长期未退出的旧门禁进程。为避免继续占用验证资源，本轮门禁被显式终止，不能计为通过。聚焦测试与 syntax compile 已通过；总门禁悬挂原因需单独排查，不与 Runtime 身份闭环混为一项。

## 11. M5 资源传输按稳定 asset_id 去重

本轮在不修改 `ACTOR_CREATE / FILE_REQUEST / FILE_CHUNK` 网络包格式的前提下，补齐了接收端资源传输去重：

- 接收端从现有 `actor_json` 结构化读取稳定 `asset_id`；缺失或无效时保持原有按路径传输行为。
- 同一 `asset_id` 正在传输时，后续 Actor 加入同一个传输组，不重复发送文件请求；每个 Actor 仍保留自己的 `actor_guid`、transform 和 Runtime 元数据。
- 同一 `asset_id` 已完成接收且本地文件仍存在时，后续 Actor 直接复用已接收模型路径，不再次传输模型和依赖文件。
- 超时、Actor 删除、停止会话和项目根目录切换时清理相应索引，避免旧传输组或跨项目缓存污染。
- 传输结束后才逐个释放等待 Actor 到现有 `pollPendingActorCreate -> sceneTools.createActor` 链路，没有新增绕过 EngineWriteGate 的写入口。

聚焦自动验证覆盖：

```text
asset_id 从 actor_json 读取而非扩展线协议
同资产传输组和已接收缓存存在
Runtime Actor 身份快照回归
LANChat Scene Sync 静态协议回归
```

完整 `NativeSceneToolsRpcTests` 本轮共运行 149 项，148 项通过；唯一失败是远端 `engine.cpp` 已启用 mesh simplification，而旧断言仍要求关闭。该失败与本轮网络资源去重无关，未在本提交中顺手修改。

以下仍为 **[待 F5/实机验证]**：

- 两个 Actor 同时引用同一资产时只发生一次真实模型/依赖文件传输，并各自只创建一次。
- 相同 `asset_id` 但来源路径不同的 Actor 能复用已接收文件，且材质依赖仍正确加载。
- 传输中删除一个等待 Actor 不影响同组其他 Actor；删除最后一个 Actor 后传输组可安全回收。
- 房主与成员的 `entity_id + asset_id + actor_version`、SceneWorldSnapshot 和 Engine Actor 数量一致。
- 大模型 LAN 传输期间 UI 卡顿、带宽占用和同步时序满足验收要求。

## 12. Engine Snapshot 身份保留与世界一致性审计

本轮继续修复了 `C++ Actor snapshot -> Python Runtime` 接口断点：C++ 已返回 Runtime 身份，但旧快照适配器只保留 Actor 名称、transform 和 AABB，丢失了 `entity_id/asset_id/model_ref/actor_version`，因此无法可靠完成 Engine、Registry 与 SceneWorldSnapshot 对账。

当前改动：

- Engine snapshot 归一化保留 `entity_id`、`asset_id`、`model_ref`、`entity_type`、`semantic_role`、`plan_id/batch_id` 和 Actor/Entity version。
- 真实 Engine AABB 到达时记录 `bounds_source=engine_actual`、`engine_lifecycle_status=bounds_ready` 和本地 `engine_imported`；不伪造多人 `synced`。
- 新增只读接口 `runtime.scene_world_consistency.audit`，只消费 `SceneWorldSnapshot + engine_scene_snapshots`。
- 审计按稳定 `entity_id` 对账，不根据名称或路径猜测身份；输出缺失、额外、无 Runtime 身份、重复 ID、actor/asset/version 漂移。
- 审计被注册为 READ_ONLY，不创建 ScenePlan、PlanPatch、BatchPlan、ToolCallGraph 或 Engine 写入。
- Finalizer 在 `scene_world_snapshot_ready` 之后、`report_ready` 之前记录 `runtime_scene_world_consistency_audited`；最终报告持久化同一份审计结果，F5 不再需要从零散日志人工拼接五方一致性。

聚焦自动验证：

```text
Engine snapshot 身份和实际 AABB 保留
Runtime/Engine 身份完全一致 -> consistent
缺少身份、asset/version 漂移 -> needs_review
Snapshot/ActionIntent/Inspector/RuntimeGuard 聚焦回归 29 项通过
LANChat Scene Sync 静态检查通过
Python syntax compile 通过
```

一次包含完整 `test_lanchat_runtime_guard` 的大套件因大量历史长等待用例运行约 8 分钟仍未结束，被显式终止；没有观察到失败。本轮按约束文档改跑直接相关的 29 项聚焦测试，不将被终止的大套件计为通过。

以下仍为 **[待 F5/实机验证]**：

- 儿童卧室、森林营地、混合场景的审计结果达到 `consistent`，或准确列出真实漂移实体。
- Finalizer 后抓取的 Engine snapshot 与不可变 SceneWorldSnapshot 使用同一 plan/version。
- 房主与成员分别审计时 `entity_id/asset_id/version` 和实体数量一致。
- 多人传输失败时审计和 Snapshot 正确体现 `partial/needs_review`，不虚报 Game-ready。

## 13. LANChat 世界一致性审计披露

本轮补齐了 Runtime 审计到用户可见报告的最后一段只读链路。此前 `scene_world_consistency_audit` 已由 Finalizer 写入报告，但 LANChat 的 Runtime Report 和状态查询没有消费该字段，导致用户无法判断 Engine、RuntimeState 与 SceneWorldSnapshot 是否一致。

当前改动：

- Runtime Report 新增 `world consistency` 摘要。
- Runtime 状态查询新增“场景事实对账”摘要。
- 只披露 `consistent / needs_review / blocked`、匹配数量、Engine 实体数量和问题总数。
- 不披露 `entity_id`、`actor_id`、模型路径或具体漂移列表；详细证据仍保留在 Runtime 报告和 OperationLog 中供调试。
- Engine 快照尚未到达时明确显示“等待 Engine 场景快照”，不把 blocked 误报为失败或完成。

聚焦自动验证：

```text
consistent / needs_review / blocked 三态格式化
Runtime Report 与 Runtime 状态查询均可见审计摘要
内部 entity_id 不进入聊天室文本
Python syntax compile 通过
```

以下仍为 **[待 F5/实机验证]**：

- Finalizer 完成后聊天室最终报告显示“对账通过”，且数量与 Scene 面板一致。
- Engine Actor 晚到时状态从“等待快照”更新为“对账通过”或准确的“需要复核”。
- 多人房主与成员看到的对账状态不矛盾；成员端没有完整 Runtime 事实时不得伪造一致。

## 14. 同步异常阻断 Game-ready

本轮复核发现，Registry 旧逻辑只要求 `sync_status` 非空，因此 `partial / failed / needs_attention` 也可能被计入 Game-ready，进而让下游 Agent 读取到“流程完成但多人事实并不完整”的世界。

当前改动：

- 单机已知状态 `engine_created / engine_imported / runtime_state` 和真实多人状态 `synced / synchronized` 继续允许参与 Game-ready 判定。
- `partial / failed / needs_attention / timeout / abandoned / cancelled / deleted` 明确阻断 Game-ready。
- 异常同步实体增加 `readiness_missing_fields=[sync_status_ready]`，Snapshot 可定位到具体实体，而不是只给房间级模糊失败。
- `SceneWorldSnapshot.world_readiness` 自动降为 `needs_review`；不把同步不完整世界提供给后续可执行 Agent。

聚焦自动验证：

```text
partial sync_status -> game_ready_entity_count=0
Snapshot world_readiness=needs_review
缺失事实包含 sync_status_ready
Game-ready / ActionIntent / SceneInspector 27 项通过
Python syntax compile 通过
```

以下仍为 **[待 F5/实机验证]**：

- 真实 LAN 传输失败或成员离线时，对应实体的 `sync_status` 能被 Runtime 记录为 partial/failed。
- 传输恢复后 readiness reconcile 能将实体恢复为可用状态并生成新 scene version。
- 房主与成员的 Snapshot 对同一实体给出一致版本与同步状态。
