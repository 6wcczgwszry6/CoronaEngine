# R3-min 推进记录

更新时间：2026-07-13

## 1. 当前结论

本轮按“双轨但有硬门槛”推进：

```text
主线 A：Game-ready Scene Runtime 收口
并行 B：SceneWorldSnapshot + 只读 SceneInspectorAgent
```

没有恢复旧 Workflow 用户入口，没有引入可执行下游 Agent，也没有扩展 VLM、Provider 或 UI。

### 本轮 M5 增量：权威 Scene Snapshot 切换

- Runtime 导入的普通 Actor 与 environment Actor 现在携带 `source_scene_version`，并由 C++ Scene Actor 元数据持久化、快照读取和 LAN 同步保留。
- Host 的 `ACTOR_SCENE_SNAPSHOT` JSON 顶层携带 `plan_id / scene_version / snapshot_authority`；没有新增网络消息类型。
- C++ 收到带计划身份的 Snapshot 后产生 `scene_snapshot_received` 只读同步事实。
- 成员 Runtime 可继续接收不同计划的 Actor 事实，但只有权威 Snapshot 可以把 `peer_mirror_plan_id` 从旧计划切换到新计划；迟到旧 Actor 事件不能再把活动世界切回去。
- 聚焦验证：35 项 Python 测试、Python syntax compile、LANChat Scene Sync 静态检查通过。

以下仍为 **[待 F5/实机验证]**：

- C++ Actor 元数据在完整构建、场景保存/重载和真实 LAN 传输后保持 `source_scene_version`。
- Host Snapshot 到达后，成员端活动 Snapshot 只切换一次且版本与 Host 一致。
- 新计划 Actor 先于 Snapshot、旧计划 Actor 迟到、追加批更新三种乱序情况下，成员端均不回退世界版本。

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

## 15. Snapshot 世界指纹与 transform/AABB 对账

本轮继续复核发现，旧一致性审计只检查 `entity_id / actor_id / asset_id / version`，即使 transform 或 world AABB 已发生漂移，仍可能被误判为 `consistent`。这不足以支撑多人世界一致性，也不能作为下游 Agent 的乐观并发依据。

当前改动：

- 一致性审计增加 transform 和 world AABB 对账，分别输出 `transform_mismatches` 与 `world_aabb_mismatches`。
- `SceneWorldSnapshot` 增加排序无关的 `world_fingerprint`，由 plan/version 以及稳定实体身份、资源身份、版本、transform、world AABB 生成。
- Engine 审计生成同口径 `engine_fingerprint`，并输出 `fingerprints_match`。
- `runtime.scene_world_snapshot.get` 顶层返回 fingerprint；找不到计划或版本时返回空值，不伪造。
- `SceneInspectorAgent` 分析结果绑定 `scene_version + world_fingerprint`，同版本内 late-ready 几何事实变化也可触发重新分析。

聚焦自动验证：

```text
身份、版本、transform、AABB 一致 -> consistent + fingerprint match
transform/AABB 缺失或漂移 -> needs_review
Snapshot fingerprint 为稳定 64 位摘要
SceneInspector 输出绑定 fingerprint
Game-ready / Inspector / ActionIntent 27 项通过
Python syntax compile 通过
```

以下仍为 **[待 F5/实机验证]**：

- 房主 Runtime Snapshot 与本机 Engine snapshot 的 fingerprint 一致。
- 成员端 Actor 同步完成后，其 Engine 实体事实与房主权威 Snapshot 对账一致。
- transform 更新、late-ready AABB 和追加批会产生新的 fingerprint，旧分析不会被继续使用。

## 16. C++ LAN 同步事实接入 AgentRuntime

本轮修复了多人同步验证中的假覆盖：Python 已有 `handle_lanchat_sync_event()` 和 Runtime reducer，但真实 Worker 只轮询聊天室消息与房间事件，C++ Actor/资源生命周期从未进入 RuntimeState。

当前改动：

- C++ `NetworkSystem` 新增有界 `LanChatSyncEvent` 队列和 Python pop binding，不修改现有网络包协议。
- `ACTOR_CREATE`、transform、delete、state update 和资源传输完成会产出结构化同步事实。
- 网络收到 Actor 只记录 `actor_create_received`；远端 Actor identity 注册成功后才记录 `actor_imported`，不把网络接收伪装成 Engine 成功。
- Worker 每 tick 在 Runtime drain 前消费同步事实，并展开已有 `actor_json` 中的 plan/batch/entity/asset/version 元数据。
- Runtime 保留 actor/entity 版本、语义角色与同步生命周期，现有 RuntimeGuard/StatePatch 写门保持不变。

聚焦自动验证：

```text
C++ 队列、事件生产点和 Python binding 静态核对
Worker 原生同步事件轮询与 actor_json 元数据展开
actor_create_received != actor_imported
既有 actor create/transform/delete Runtime 回归
Python syntax compile
```

以下仍为 **[待 F5/实机验证]**：

- 新 C++ binding 可在完整引擎中编译、加载并持续出队。
- 真实 LAN 文件传输完成、远端 Actor 创建和 identity 注册按预期产生一次事件。
- 高事件速率下有界队列不会造成关键终态事实丢失。

## 17. 成员端只读 Peer Mirror Snapshot

真实宿主同步的 `plan_id` 在成员本地没有对应 ScenePlan。旧逻辑会以 `no runtime plan` 拒绝这些事实，因此成员端无法形成可供只读下游 Agent 使用的 SceneWorldSnapshot。

当前改动：

- 仅接受 `authority=remote_host` 且包含 actor/asset 身份的未知计划同步事实进入 `peer_mirror`。
- Peer mirror 不创建 ScenePlan、BatchPlan、ToolCallGraph、PlanPatch 或 Provider 请求，也不执行 Engine 写入。
- `runtime.scene_world_snapshot.get` 在没有本地 active/latest plan 时回退只读 peer mirror，并标记 `snapshot_authority=peer_mirror`、`snapshot_stability=peer_mirror`。
- 成员端 Snapshot 继续使用 Registry/Game-ready 规则；缺少真实 AABB、grounding 或同步终态时保持 `needs_review`，不伪造 Game-ready。
- 非宿主权威的未知 plan 同步事实继续被拒绝。

聚焦自动验证：

```text
未知宿主 plan -> peer mirror Snapshot
peer mirror 不创建本地 ScenePlan/执行队列
非宿主未知 plan -> rejected
Snapshot/Game-ready/SceneInspector/同步桥 24 项通过
Python syntax compile
```

以下仍为 **[待 F5/实机验证]**：

- 房主与成员的 `entity_id/asset_id/actor_version/transform/AABB` 和 fingerprint 一致。
- 成员远端 Actor identity 注册及真实 AABB 到达后，Snapshot 从 `needs_review` 正确收敛。
- 房主切换执行计划或追加场景版本时，成员 peer mirror 不回退到迟到旧事实。

## 18. Runtime 同步版本单调性

前端已经按 `actor_guid + actor_version` 拒绝旧 Actor 更新，但 Runtime 同步 reducer 之前仍会直接应用迟到事件中的 transform/AABB。这会造成 Engine 已保留新版本，而成员 SceneWorldSnapshot 被旧事实覆盖。

当前改动：

- 同步事件显式携带 `actor_version/version` 时，Runtime 在创建 StatePatch 前与现有 ActorFact 版本比较。
- 低于当前版本的事件记录为 `sync_event_record_skipped: stale actor version`，不修改 ActorFact、Registry、Snapshot 或 fingerprint。
- 未携带版本的旧协议事件保持兼容，不凭默认版本 1 错误拒绝。
- 同版本事件仍可补齐晚到 AABB/readiness 事实，避免阻断合法的 Engine-ready 收敛。
- Runtime/GM 状态摘要与公开 Snapshot 使用同一目标优先级；成员没有本地 ScenePlan 时可只读显示 peer mirror 实体世界及 authority，不再错误显示“无计划”。

聚焦自动验证：

```text
actor version 4 后收到 version 3 -> rejected
旧 transform/AABB 不覆盖新事实
Snapshot world_fingerprint 保持不变
Snapshot/Game-ready/SceneInspector/同步桥 24 项通过
```

以下仍为 **[待 F5/实机验证]**：

- 真实网络乱序或重放时，成员 Engine 与 Runtime 均拒绝旧版本。
- 同版本的 identity、AABB 和同步终态补齐不会被误判为重复而丢失。
- 房主追加批产生的新 actor/scene version 能在成员端单调收敛。

## 19. 宿主世界 AABB 与成员本机 Engine AABB 分域

多人同步中的 `actor_json` 可以携带宿主测得的 world AABB，但该事实只能证明宿主世界中的几何范围，不能证明成员进程已经在本机 GeometrySystem 中完成模型加载。旧逻辑将两者都记录成 `bounds_source=engine_actual`，可能让成员 peer mirror 在本机 Actor 尚未 materialize 时提前进入 Game-ready。

当前改动：

- `authority=remote_host/remote_peer` 的同步 AABB 分别记录为 `remote_host_actual/remote_peer_actual`。
- 远端 AABB 保留为共享世界事实，但不设置成员本机 `bounds_ready`，也不把本机 Engine 生命周期提升为 `bounds_ready`。
- `actor_imported` 只证明成员本机已注册 Actor identity，状态收敛到 `engine_imported`；它不伪造本机 AABB。
- 只有 `runtime.scene.snapshot` 从成员本机 Engine 读取到真实 AABB 后，才覆盖为 `bounds_source=engine_actual` 并允许进入 Game-ready 判定。
- Engine snapshot 的已知 Actor 投影保留 `model_ref`、Actor/Entity version 和同步身份，防止刷新真实几何时丢失稳定资源身份。
- environment component 使用同一来源边界，远端 room/terrain bounds 不会提前完成成员本机 environment readiness。

聚焦自动验证：

```text
宿主 AABB 到达 -> peer mirror needs_review
成员 actor_imported -> 仍等待本机 engine_actual AABB
成员本机 scene snapshot -> engine_actual + engine_verified + game_ready
迟到旧版本 transform/AABB -> rejected，world fingerprint 不变
Snapshot/Game-ready/SceneInspector/同步桥 24 项通过
ActionIntent 聚焦回归 8 项通过
LANChat Scene Sync 静态检查通过
Python syntax compile 通过
```

历史 `test_agent_runtime_phase1` 大套件本轮运行超过两分钟仍未完成，已显式终止；已执行部分未见失败，但不计为通过，也不作为本轮提交证据。

以下仍为 **[待 F5/实机验证]**：

- 成员接收模型后，`actor_imported` 与本机 GeometrySystem AABB 事件按预期先后到达。
- 宿主 Snapshot 可以先用于只读世界展示，但成员在本机 Actor 未就绪前保持 `needs_review`。
- 成员本机 snapshot 到达后，Registry/Snapshot/fingerprint 自动收敛且不丢失宿主 plan/entity/asset/version 身份。
- environment 和普通 Actor 均遵守同一事实来源边界。

## 20. LAN 同步事实队列背压与终态保护

C++ `LanChatSyncEvent` 队列此前在超过 256 项后直接删除最老事件。多人场景中 transform/state update 可能高频进入队列，这种策略会连带丢失更早的 `actor_create_received`、`actor_imported`、`actor_deleted` 或 `asset_transfer_completed`，导致成员 RuntimeState 永远缺少收敛终态。

当前改动：

- 同一 Actor、同一事件类型的 `actor_transform/actor_updated` 在待消费队列中只保留最新快照。
- transform 与 actor state update 不互相覆盖，避免不同事实集合被错误合并。
- 队列超过软上限时优先移除可合并的 best-effort 事件，不删除关键生命周期终态。
- 仅由关键事实构成的队列允许短时超过软上限，并受 2048 项紧急硬上限保护；触发硬上限会输出明确告警。
- 不修改现有 LAN 网络包格式、Actor 创建协议或 Python binding，只调整 Runtime 同步事实桥的本地背压语义。

聚焦自动验证：

```text
C++ 同步桥事件生产点与背压策略静态核对通过
Snapshot/Game-ready/SceneInspector/ActionIntent/同步桥 32 项通过
LANChat Scene Sync 静态检查通过
```

以下仍为 **[待 F5/实机验证]**：

- 高频拖动多个 Actor 时，同一 Actor 的 transform 事件被有效压缩且最终位置不丢失。
- 文件传输和 transform 高并发期间，Actor create/import/delete 与 asset complete 终态均进入 RuntimeState。
- 队列压力不会造成明显主线程卡顿；若触发硬上限告警，需要进一步拆分关键/快照双队列。

## 21. 五方对账禁止忽略未物化实体

本轮复核 M3 五方对账时发现，一致性审计此前只把带 `actor_id` 的 Runtime 实体纳入 Engine 对账。尚未物化的 environment、substrate 或普通实体会被排除，导致“Runtime 世界仍有 planned 实体，但剩余 Actor 与 Engine 完全一致”时错误返回 `consistent`，世界指纹也可能出现假一致。

当前改动：

- `non_materialized_entity_count` 计入一致性审计问题总数；只要 Snapshot 中存在尚未形成 Engine Actor 的实体，审计至少为 `needs_review`。
- `expected_entity_count` 统一表示 Runtime 世界完整实体数，并单独披露 `materialized_entity_count/non_materialized_entity_count`，避免“expected 与 Engine 数量相等但仍漏实体”的统计歧义。
- Runtime world fingerprint 使用完整下游可见实体集合，不再只对已物化 Actor 求摘要。
- Engine fingerprint 继续只由真实 Engine Actor 生成；两者在未物化实体存在时必须不同。
- Engine Actor 缺失或漂移 `actor_id/asset_id/model_ref/version` 时均输出明确 mismatch；空值不再绕过检查。
- 若 fingerprint 仍出现未被字段级诊断覆盖的差异，审计记录 `unclassified_fingerprint_mismatch_count` 并降级为 `needs_review`，禁止 `consistent + fingerprint mismatch` 的矛盾状态。
- Snapshot 的 `game_ready` 现在受 Engine 一致性审计约束：审计为 `needs_review/blocked` 时，公开 Snapshot 与最终报告统一降级为 `needs_review`，实体级 Registry readiness 保留用于诊断。
- Finalizer 顺序调整为 `registry ready -> consistency audited -> snapshot ready -> report ready`；不会再先发布 Game-ready Snapshot、随后才发现 Engine 漂移。
- provisional Snapshot 同样读取当前 Engine snapshot 进行约束；缺少 Engine snapshot 时不能供可执行下游 Agent 使用。
- immutable Snapshot 重放持久化报告中的一致性结论；旧报告缺少审计或审计未通过时保持保守降级，不因重新读取而恢复成 Game-ready。
- Finalizer 已有的 `runtime_scene_world_consistency_audited` 与最终报告会直接继承该严格判定，不新增旁路状态源。

聚焦自动验证：

```text
完整物化且身份/transform/AABB 一致 -> consistent
身份、版本、transform 或 AABB 漂移 -> needs_review
存在未物化 Runtime 实体 -> needs_review + fingerprint mismatch
Game-ready 聚焦套件 19 项通过
LANChat 世界一致性披露、Inspector 与 Peer Mirror 聚焦回归 7 项通过
Game-ready 聚焦套件 22 项通过
Inspector、Peer Mirror、同步桥和 LANChat 披露聚焦回归 10 项通过
```

以下仍为 **[待 F5/实机验证]**：

- 儿童卧室、森林营地和混合场景最终审计不存在未解释的 `non_materialized_entity_count`。
- Provider 或 Engine 导入失败时，最终报告准确列出未物化实体并保持 `needs_review/partial`。
- 追加批执行期间 Snapshot 的临时未物化实体不会被错误披露为 Game-ready；追加批完成后新版本重新收敛。

## 22. Finalizer 终态事件按场景版本幂等

本轮复核生成后追加批时发现，`scene_entity_registry_ready` 和 `scene_world_snapshot_ready` 此前只按 plan 判断是否已经记录。同一计划第一次完成后再追加实体，即使 `scene_version` 已增加，第二次 Finalizer 也可能跳过新版终态事件，导致成员端和只读下游 Agent 停留在旧世界版本。

当前改动：

- Registry/Snapshot ready 事件改为按 `plan_id + scene_version` 幂等。
- 同一版本因 worker 重试重复进入 Finalizer 时不重复发布。
- 追加批令计划版本增加后，新版本重新发布 Registry 与受 Engine 一致性约束的 Snapshot。
- Registry ready payload 增加 `scene_version`；Snapshot ready 继续携带版本并新增一致性状态。
- 不创建新的 ScenePlan，不改变追加批、RuntimeGuard 或 EngineWriteGate 主链。

聚焦自动验证：

```text
version 1 Finalizer -> registry/snapshot ready 各一次
version 2 Finalizer -> registry/snapshot ready 各新增一次
version 2 重试 -> 不重复发布
Game-ready、Inspector、Peer Mirror、同步桥与 LANChat 披露相关回归 33 项通过
```

以下仍为 **[待 F5/实机验证]**：

- 生成完成后追加一个实体会令 scene version 增加，并在聊天室与成员端出现对应的新 Snapshot。
- 追加批期间旧 immutable Snapshot 保持可读，但不能冒充新版本。
- 新版 Snapshot 与 Engine Actor、Registry、最终报告的实体数量和 fingerprint 一致。

## 23. Engine Snapshot 绑定场景版本

追加批完成后，Runtime 世界已按 `scene_version` 演进，但 Engine snapshot 此前只记录 plan 和时间戳。旧版本快照若晚到，`latest_engine_snapshot()` 可能把它当成当前世界参与 Finalizer 对账，导致新版本无法稳定收敛。完成态与成员 peer mirror 的手动刷新还沿用旧 active-plan 解析，可能写出空 plan 或默认 version 1。

当前改动：

- `runtime.scene.snapshot` ToolCall 显式携带当前 ScenePlan version。
- Engine snapshot fact 增加并校验正整数 `scene_version`；ToolResult、StatePatch 与 RuntimeState 使用同一字段。
- snapshot 选择器优先匹配 `plan_id + scene_version`，不使用显式旧版本或未来版本冒充当前世界。
- 无版本历史快照仅作为兼容 fallback；新链路产生的快照必须版本化。
- `refresh_scene_snapshot()` 目标统一为 `active_execution -> latest_completed -> peer_mirror -> discussion`，并携带对应版本。
- 成员 peer mirror 在本机 Engine snapshot 到达后可从 `needs_review` 收敛；完成态本地计划不再因 active execution 已清空而丢失快照归属。
- 接入时曾发现 Snapshot validator allowlist 漏接新字段；已补齐 schema，并用原 snapshot/Finalizer 测试验证 ToolGraph 不再被安全校验误拒绝。

聚焦自动验证：

```text
version 2 世界 + 晚到 version 1 快照 -> 选择 version 2
只有显式旧版本快照 -> 当前版本视为 snapshot unavailable
Batch ToolCall 携带 ScenePlan version
latest completed plan 刷新保留 plan/version
peer mirror 本机快照按宿主 scene version 收敛
Game-ready、Inspector、Peer Mirror、同步桥与 LANChat 披露 36 项通过
真实 snapshot/Finalizer 聚焦回归 9 项通过
```

以下仍为 **[待 F5/实机验证]**：

- 追加批前后 Engine snapshot 分别携带正确 scene version，晚到旧快照不影响当前报告。
- 房主与成员端本机 snapshot 使用同一宿主 plan/version，但各自保留本机 Engine AABB 来源。
- Engine snapshot 缺失当前版本时 Snapshot 保持 `needs_review`，当前版本到达后自动收敛。

## 24. 下游 Agent gameplay 事实不再使用模板默认值

本轮审查 `scene_entity_registry -> SceneWorldSnapshot -> SceneInspectorAgent` 契约时发现，默认 Actor 导入器会为所有对象统一声明 `inspect/move`、`scene_actor/runtime_generated` 和静态碰撞；环境模板也会仅凭名称或 component type 推导 `walk_on`、`walkable` 和物理配置。这些字段没有来自 EntityIntent 或 Engine 的可信证据，交给后续 Agent 后会被误认为可执行能力。

当前改动：

- 默认 Actor 的 `interaction_capability/gameplay_tags/physics_profile` 改为空。
- 环境组件和未物化 substrate 的上述字段同样保持为空。
- ScenePlan、StatePatch 或 Engine 结果显式提供的可信字段仍原样进入 Registry 和 Snapshot。
- `entity_type/semantic_role/component_type/environment_profile/grounding_status` 继续承担场景语义描述，不用 gameplay 字段重复猜测。
- 不修改资源生成、Engine 导入、AABB、Finalizer 或多人同步主链。

聚焦自动验证：

```text
默认 Actor/环境/substrate -> gameplay 字段为空
显式 Actor gameplay 字段 -> Registry 原样保留
显式环境 gameplay 字段 -> Registry 原样保留
森林营地对象/环境分流回归通过
Python syntax compile 通过
```

以下仍为 **[待 F5/实机验证]**：

- 实机场景 Snapshot 中未知 gameplay 字段保持为空，不影响 Registry/报告完成。
- 后续 SceneInspectorAgent 不会把空能力扩写成可执行动作。
- 未来能力识别必须由独立、可审计的 EntityIntent/CapabilityPatch 写入，而不是恢复名称模板默认值。

## 25. SceneWorldSnapshot API 严格只读

复核公开 Snapshot 接口时发现，`get_scene_world_snapshot()` 虽然不创建 ToolGraph 或 PlanPatch，但统一消息入口和查询方法仍会把每次读取写入世界 OperationLog。结果是只读 Inspector 每分析一次场景都会推进 operation cursor，连续读取同一版本也会产生新的世界历史。

当前改动：

- `runtime.scene_world_snapshot.get` 不再写 `runtime_message_action_routed` 或 snapshot queried 世界事件。
- 其他控制、写入和审计 action 继续完整记录 OperationLog，不放松执行审计。
- 连续读取同一 `plan_id + scene_version` 返回相同 fingerprint 和 operation cursor。
- SceneInspectorAgent 读取 Snapshot 后，RuntimeState、ToolGraph、PlanPatch 和 OperationLog 均不变化。
- Snapshot 仍从已有 RuntimeState、OperationLog、Registry 与 Engine consistency fact 构建，不引入第二事实源。

聚焦自动验证：

```text
连续两次公开 Snapshot 查询 -> OperationLog 数量不变
连续两次公开 Snapshot 查询 -> cursor/fingerprint 稳定
SceneInspectorAgent 分析 -> 零世界写入
Inspector scene version 更新检测回归通过
```

以下仍为 **[待 F5/实机验证]**：

- 下游 Inspector 频繁轮询不会改变聊天室终态事件窗口或成员端 cursor。
- 同一场景版本在房主与成员端读取时各自稳定，宿主发布新版本后再发生可解释变化。

## 26. Native Chat 的房主权威门禁

多人权威复核发现，生成写入路径虽然已有本机角色检查，但每个节点都会收到的 Native Chat Queue 在进入 GM 控制、实体查询、ActionIntent、Coordinator 和方案上下文前没有统一门禁。进程内 MessageDispatchLedger 只能去重同一进程的 Native Queue/Agent Trigger，不能阻止房主和成员两个进程同时解释同一消息并回复。

当前改动：

- Native Chat 在任何 GM、Intent、Coordinator、Provider 或业务回复前检查本机 network session role。
- `client` 只标记该聊天消息已观察并等待房主权威结果，不执行 Agent 路由。
- 生成选项/VLM 环境设置同样移到权威门禁之后，成员端不能凭同步到的聊天修改本机执行选项。
- 成员仍通过独立 Native Sync Event 路径接收 Actor、asset、transform、AABB 和宿主 Snapshot，不影响 peer mirror。
- Agent Trigger 原有非房主门禁继续保留，形成两个消息入口的一致权威边界。

聚焦自动验证：

```text
成员收到房主 GM 消息 -> 不运行 Coordinator/Runtime、不回复
同一成员消息重放 -> 本地观察去重
房主 Runtime status query -> 继续正常处理
Native sync bridge + peer mirror 6 项回归通过
```

以下仍为 **[待 F5/实机验证]**：

- 房主和成员同时在线时，同一聊天只产生一条 ActionIntent 和一条权威回复。
- 成员不调用 LLM/Provider，不创建 PlanPatch/Actor；仅消费宿主同步事实。
- 房主/成员 Snapshot 的 entity/version/fingerprint 最终一致，成员本机 Engine 未 ready 时保持 `needs_review`。

## 27. 墙挂与悬挂支撑不得由名称推断为已验证

Game-ready grounding 复核确认，地面物体只有在 Engine transform 返回 `ground_snapped` 或真实 AABB bottom 已贴地时才会写入 `grounded`。但墙挂和悬挂对象此前只要名称命中 support type，就会默认写成 `not_applicable`；Registry 的 Game-ready 判定接受该状态，因此尚未验证墙面/天花支撑的对象可能被错误计为可用实体。

当前改动：

- 名称分类只决定 `support_type`，不再证明墙挂/悬挂已经安装正确。
- `wall_mounted/ceiling_hung/unknown` 若没有显式 Engine/可信支撑事实，统一保持 `grounding_status=needs_review`。
- 显式返回的 `wall_mounted/suspended` 仍可进入 Registry，并在其他 Engine-ready 条件满足时成为 Game-ready。
- 地面对象原有 AABB bottom snap、Engine transform 和贴地验证路径不变。
- 不把墙挂对象错误执行 floor snap。

聚焦自动验证：

```text
ready floor actor + Engine ground snap -> grounded
ready wall torch + 仅名称 support 分类 -> needs_review
wall actor -> 不调用 floor snap transform
Game-ready 聚焦套件 26 项回归通过
```

以下仍为 **[待 F5/实机验证]**：

- 火把、壁灯、地图、吊灯等对象在真实 Engine 场景中不被拉到地面。
- 未接入墙面/悬挂验证的对象在 Snapshot 中明确列为 needs_review。
- 后续若增加 wall/ceiling support checker，必须以独立 ToolResult/StatePatch 写入可信状态。

## 28. Runtime Evidence 只统计业务 ToolCallGraph

最新旧版 F5 日志显示 5 个业务批次对应 151 个 ToolCallGraph。报告层已经按 `graph_role` 分域，但 LANChat Evidence 只有在执行结果没有携带 graphs 时才从 RuntimeState 过滤；worker drain 返回全量内部图时会绕过过滤，导致日志、节点数和状态列表继续混入 query/state/finalizer 图。

当前改动：

- Evidence 无条件从 RuntimeState 按当前 plan 重建图集合，不信任 drain 返回的全量 graphs。
- 业务图由 `graph_role=business_batch` 或 `BatchPlan.tool_graph_id` 双重识别，兼容早期持久化数据。
- 图状态、active/terminal 和 node 数只统计业务批次图。
- 内部图仅保留独立 `internal_graph_count`，不进入用户可见执行状态列表。
- 日志字段改为 `graphs=business:X,internal:Y,...`，避免把内部编排量误读为业务批次数。

聚焦自动验证：

```text
输入包含全量 Runtime graphs -> Evidence 仅返回业务图
business_graph_count == graph_count
internal_graph_count > 0 且不进入业务节点统计
单图执行回复与报告 graph domain 回归通过
```

以下仍为 **[待 F5/实机验证]**：

- 下一轮 3-5 个业务批次日志中的 business graph 数与 BatchPlan 数一致。
- internal graph 数可增长，但不影响 GM/UI 的业务进度和完成判断。

## 29. F5 Evidence 披露 Game-ready 缺失事实

旧 F5 最终状态为 14 个实体、3 个 Game-ready，但 Evidence 只打印总数，无法现场判断其余实体究竟缺少 Engine AABB、grounding、resource identity、sync 还是 Engine ready。Registry 已经有逐实体和聚合缺失字段，本轮只把这份既有事实接到现有 Evidence。

当前改动：

- Evidence 增加 `readiness_missing_field_counts`，直接读取 scene_entity_registry 聚合。
- LANChat Runtime 日志增加紧凑 `readiness_missing={...}` 字段。
- 不新增 Replay、检查器或第二状态源，不改变 Game-ready 判定。
- 下一次 F5 可直接判断 Engine Snapshot/reconcile 修复后剩余断点。

聚焦自动验证：

```text
Registry 缺失字段聚合 -> Evidence 原样披露
execution reply/evidence 既有字段回归通过
```

以下仍为 **[待 F5/实机验证]**：

- 旧运行的 14/3 是否主要由 `engine_actual_aabb/engine_ready/grounding_status` 缺失造成。
- 当前版本 Finalizer reconcile 后，各缺失项是否降为 0；若不为 0，日志可直接定位责任域。

## 30. 当前权威文档切换为双轨推进与分级门禁

为避免超长历史计划和旧约束文档继续产生执行口径歧义，本轮完成文档治理：

- 新增 `R3稳定门禁与三职能Agent双轨推进计划.md`，作为当前唯一推进优先级来源。
- 新增 `Agent任务约束循环_R3三职能协同版.md`，作为当前 Agent / Codex 执行规约。
- 旧计划和旧约束循环保留历史正文，并增加新文档迁移提示。
- 后续阶段进度继续写入本文件；微小修改只保留在提交记录中。

当前 Gate 仍为 `red / pending_reevaluation`：最近 F5 是旧代码的 `3/14 Game-ready` 结果，最新 Readiness、业务图分域、Finalizer 与 Peer Mirror 修复仍需新一轮 F5 验证。文档切换本身没有改变 Runtime、Engine 或多人同步代码。

## 31. W0.2/W0.3 R3GateReport 与只读自动对账

轨道 A 的首要断点此前只能依赖人工拼接 Runtime、Registry、Snapshot 和日志。本轮完成首个代码闭环：

- 新增稳定 `R3GateReport`、七个固定判定维度及 `R3GateReportValidator`。
- 新增纯聚合接口 `runtime.r3_readiness.evaluate`，统一读取当前 execution/completed plan 的既有 Runtime 事实。
- 七维覆盖 Snapshot、必要环境、实体身份与 readiness、Finalizer、业务批次/图、多人一致性和 Runtime 写入安全。
- `5/14` 判定 Yellow；`8/14` 且全部硬条件满足时判定 Green；环境缺失、Fingerprint 不稳、身份漂移或写入边界缺失判定 Red。
- `gate_report_id` 与 `evaluated_at` 均由输入事实派生；相同 room/plan/version 和相同事实重复查询得到完全相同报告。
- 查询 action 不记录 `runtime_message_action_routed`，不存在的 room 也不会被 `RuntimeState.room()` 隐式创建。
- evaluator 不写 OperationLog、StatePatch、PlanPatch 或 ToolCallGraph，不调用 Provider，不触发 Engine 写入。

聚焦自动验证：

```text
R3 readiness 新增测试 6 项通过
5/14 -> Yellow
8/14 + 全部硬条件 -> Green
环境缺失 / Fingerprint 错误 / duplicate entity_id -> Red
相同事实重复评估 -> 报告和 gate_report_id 完全一致
缺失 room 与已有 room 查询 -> RuntimeState/OperationLog 均零变化
AgentRuntime Game-ready + Phase 1 兼容回归 28 项通过
Python syntax compile 通过
```

当前任务状态：

```text
W0.2 R3GateReport 契约：code_complete
W0.3 只读 Gate evaluator：code_complete
W0.4 初始 Gate 锚点：等待最新可信 F5 事实
```

当前 Gate **仍为 `red / pending_reevaluation`**。以上证据只证明 Python 结构、边界和零副作用成立；旧 F5 的 `3/14 Game-ready` 仍是最新实机基准。Engine、多人一致性和实际 Green 判定均为 **[待 F5/实机验证]**。

## 32. W1.2 计划内 Scene Snapshot 不再认领未知 Actor

复核旧 F5 的 `14 entities / 3 Game-ready` 与当前 Scene Snapshot 调用链后，确认存在一个跨批次身份覆盖断点：每个业务批次开头都会执行 `runtime.scene.snapshot`；当调用没有携带 `known_actors` 时，Snapshot 工具此前会把所有 Engine 观察对象同时写入 `observed_actors` 和权威 `actors`，并补上当前 plan/batch。这样会把既有场景对象错误认领为当前计划实体，也可能把前几批 Actor 的稳定资源身份和原始 batch 归属覆盖为后一批。

当前改动：

- plan/batch scoped Snapshot 在没有 Runtime 稳定身份投影时，只写 `observed_actors` 和 Engine snapshot，不写权威 `actors`。
- 只有通过 actor_id、entity_id、asset_id、model_ref 或唯一名称索引与 `known_actors` 明确匹配的 Engine 对象，才允许把真实 transform/AABB/lifecycle 回写到 Runtime Actor。
- 手动、无 plan/batch 的显式场景刷新继续允许登记 unmanaged native Actor，保留原有检查能力。
- 不修改模型生成、Actor import、RuntimeGuard、EngineWriteGate 或 Finalizer 主链。

聚焦自动验证：

```text
plan-scoped snapshot + no known identity -> 观察到 native Actor，但不认领、不改批次
known Runtime actor + Engine snapshot -> 保留 plan/batch/asset identity，并吸收真实 AABB
Finalizer partial batch recovery -> 继续从唯一匹配的 native snapshot 收敛
AgentRuntime Game-ready 26 项通过
R3 readiness evaluator 6 项通过
Python syntax compile 与 git diff --check 通过
```

当前任务状态：

```text
W1.2 稳定身份和真实几何事实：本断点 code_complete
W0.4 初始 Gate 锚点：仍等待最新可信 F5
```

以下仍为 **[待 F5/实机验证]**：

- 多批次生成时，前序 Actor 的 `entity_id/asset_id/model_ref/batch_id` 不再被后续 Snapshot 覆盖。
- Finalizer 使用 known identity 对齐 Engine Actor 后，`engine_verified` 和 Game-ready 数量能否由旧基准 `3/14` 提升到 Yellow/Green 门槛。
- 未被当前计划拥有的既有场景 Actor 只出现在观察事实中，不进入当前计划 Registry/Snapshot。

## 33. W0.4/W1.2 R3 Gate 输出逐实体 Readiness 责任字段

旧 F5 只记录 `14 entities / 3 Game-ready` 和聚合缺失计数，无法证明剩余 11 个实体分别缺少身份、真实 AABB、Engine ready、贴地还是同步事实。`scene_entity_registry` 已经保存每个实体的 `readiness_missing_fields`，但 `runtime.r3_readiness.evaluate` 此前没有把这份既有事实带入 GateReport。

当前改动：

- `entity_readiness.metrics` 增加稳定排序的 `entity_diagnostics`，逐项披露 `entity_ref/entity_type/semantic_role/game_ready/readiness_missing_fields`。
- 诊断直接读取 `scene_entity_registry`，并合并 Gate 自己验证出的 `entity_id/asset_identity/actor_id/version` 身份缺失，不建立第二状态源。
- 已标记 `game_ready=true` 但缺少稳定身份的实体仍进入诊断并使 Gate 判 Red，不能信任矛盾标记。
- 诊断默认最多 50 项，同时提供 total/truncated 计数，避免大场景报告无限增长。
- 输出按 `entity_ref` 排序并参与确定性 GateReport hash；相同事实重复查询仍得到相同结果。
- 不修改 RuntimeState、OperationLog、Registry、ToolCallGraph 或 Engine，也不改变现有 Game-ready 判定。

聚焦自动验证：

```text
R3 readiness evaluator 7 项通过
5/14 Yellow -> 精确列出 9 个 needs-review 实体及 support_classification
game_ready 标记与 asset identity 矛盾 -> 逐实体诊断并判 Red
AgentRuntime Game-ready 26 项通过
SceneWorld peer mirror 4 项通过
Python syntax compile 与 git diff --check 通过
```

当前任务状态：

```text
W0.4 Gate 逐实体诊断：code_complete
W1.2 Game-ready 实机提升：仍等待最新可信 F5
当前 Gate：red / pending_reevaluation
```

以下仍为 **[待 F5/实机验证]**：

- 下一轮 F5 的 GateReport 能否准确列出全部 needs-review 实体及真实缺失字段。
- Scene Snapshot 身份修复后 Game-ready 是否达到 Yellow（至少 5/14）或 Green（至少 8/14）门槛。
- 若仍未达标，必须按 `entity_diagnostics` 选择数量占比最高的真实责任字段继续修复，不能根据旧日志猜测。

## 34. W3.1/W3.2/W3.6 三职能强类型契约底座

轨道 A 的跨批次 readiness 恢复已有聚焦集成测试证明；在等待最新 F5 重新评估期间，按 Red 能力矩阵推进首个独立轨道 B 交付物。本轮只建立协作契约，不连接 LANChat、真实或 Mock Snapshot、AgentRuntime、ActionProposal 或 Runtime 写入路径。

当前改动：

- 新增独立 `services/agent_collaboration/contracts.py`，不导入 AgentRuntime 内部实现。
- 定义 `GameProjectState`、`ArtifactEnvelope`、`AgentTask` 和六种首批 Artifact payload DTO。
- `ArtifactEnvelope` 构造时规范化并深度冻结 payload，由实际 Validator 产生 `validation_result`；调用方不能传入伪造 hash 或默认“通过”结果。
- `content_hash` 由 Artifact 类型、schema version 和规范化 payload 确定性计算；键顺序不影响 hash，内容变化必然改变 hash。
- 无效 payload 可作为审计事实存在，但状态强制为 `invalid`，不能声称 `validated` 或通过执行资格检查。
- 定义 `NonExecutableArtifactError` 与 `assert_executable()`；`snapshot_source=mock` 在构造时必须同时为 `non_executable=true`，执行资格检查始终拒绝 Mock。
- Mock 仅在契约测试 fixture 中使用，没有注册运行中 Agent 输入，也没有创建 EntityBindingPlan 生产入口。
- 本轮没有建立 ArtifactRegistry、TaskGraph、Coordinator、ProjectGate 或 ActionProposal。

聚焦自动验证：

```text
六种首批 Artifact DTO -> 统一 Validator 通过
相同规范化 payload -> 相同 content_hash
payload 内容变化 -> content_hash 变化
Artifact payload -> 深度不可变，导出副本修改不污染原件
非法 payload -> validation_result.valid=false + status=invalid
伪造 validation_result 构造参数 -> 拒绝
Mock Artifact -> 可审计但 assert_executable 必然拒绝
GameProjectState / AgentTask 基础约束与规范化通过
独立导入 contracts -> 未加载 AgentRuntime/LANChat 模块
契约聚焦测试 8 项通过
Python syntax compile 与 git diff --check 通过
```

当前任务状态：

```text
W3.1 Artifact 与 Project 契约：code_complete
W3.2 Content Hash 与真实 Validator：contract_layer_code_complete
W3.6 Mock/非执行硬隔离：contract_layer_code_complete
W3.3 GameProjectState 存储与版本迁移：ready
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁：

- ArtifactRegistry 的版本索引与 stale 传播（W3.4）。
- AgentTaskGraph 的依赖、失败和重试状态机（W3.5）。
- 运行中的三职能 Agent 和任何 Snapshot 输入（Red 禁止）。
- ActionProposal 构造器对 `assert_executable()` 的二次强制调用（Green-only W5）。
- 所有 Runtime、Engine 与多人效果仍以最新 F5 GateReport 为准，本轮契约代码不改变 Gate 颜色。
