# R3-min 推进记录

更新时间�?026-07-13

## 1. 当前结论

本轮按“双轨但有硬门槛”推进：

```text
主线 A：Game-ready Scene Runtime 收口
并行 B：SceneWorldSnapshot + 只读 SceneInspectorAgent
```

没有恢复�?Workflow 用户入口，没有引入可执行下游 Agent，也没有扩展 VLM、Provider �?UI�?
### 本轮 M5 增量：权�?Scene Snapshot 切换

- Runtime 导入的普�?Actor �?environment Actor 现在携带 `source_scene_version`，并�?C++ Scene Actor 元数据持久化、快照读取和 LAN 同步保留�?- Host �?`ACTOR_SCENE_SNAPSHOT` JSON 顶层携带 `plan_id / scene_version / snapshot_authority`；没有新增网络消息类型�?- C++ 收到带计划身份的 Snapshot 后产�?`scene_snapshot_received` 只读同步事实�?- 成员 Runtime 可继续接收不同计划的 Actor 事实，但只有权威 Snapshot 可以�?`peer_mirror_plan_id` 从旧计划切换到新计划；迟到旧 Actor 事件不能再把活动世界切回去�?- 聚焦验证�?5 �?Python 测试、Python syntax compile、LANChat Scene Sync 静态检查通过�?
以下仍为 **[�?F5/实机验证]**�?
- C++ Actor 元数据在完整构建、场景保�?重载和真�?LAN 传输后保�?`source_scene_version`�?- Host Snapshot 到达后，成员端活�?Snapshot 只切换一次且版本�?Host 一致�?- 新计�?Actor 先于 Snapshot、旧计划 Actor 迟到、追加批更新三种乱序情况下，成员端均不回退世界版本�?
## 2. 里程碑状�?
| 里程�?| 状�?| 本轮结果 |
|---|---|---|
| M0 基线冻结 | 已完�?| 建立 `13740c16` R3-min 基线；同�?`origin/main`；Quasar provider 基线对齐；本地配置继续隔�?|
| M1 Snapshot API | 自动验证通过 | 新增只读 `runtime.scene_world_snapshot.get`；支�?plan/version 选择；零 ToolGraph、PlanPatch、Provider �?Engine 写入 |
| M2 Readiness 收口 | 自动验证通过，待 F5 | batch terminal 后对 partial 实体执行 readiness reconcile；actual AABB、support、sync 均进�?Game-ready 判定 |
| M3 单机三场�?| �?F5/实机验证 | 儿童卧室、森林营地、室内外混合场景尚需真实 Engine 五方对账 |
| M4 SceneInspectorAgent | 自动验证通过 | 只读�?Snapshot，输出结构化 SceneAnalysis；无 LLM、Provider、PlanPatch �?Engine 写入 |
| M5 多人权威与一致�?| 部分完成，待 F5 | 客户�?Runtime write 被权威门禁阻断；双入口消息去重已有测试；真实广播和多�?Snapshot 一致性待实机 |

## 3. 新增只读接口

```text
runtime.scene_world_snapshot.get
```

请求�?
```python
{
    "room_id": str,
    "plan_id": str | None,
    "min_version": int | None,
}
```

响应核心字段�?
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

终态优先读�?Finalizer 已持久化报告中的不可�?Snapshot；执行中返回 `provisional`，供只读观察使用，不允许作为可执行下�?Agent 的写入依据�?
## 4. Readiness 口径

实体进入 Game-ready 必须具备�?
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

`estimated` AABB、未�?grounding 或未�?sync 不计�?Game-ready，并�?`readiness_missing_fields` 中列出原因�?
## 5. 下游 Agent 边界

当前仅提�?`SceneInspectorAgent`�?
```text
SceneInspectorAgent
-> runtime.scene_world_snapshot.get
-> SceneAnalysis
```

它不读取聊天历史�?Engine 内部对象，不调用 Provider，不创建 PlanPatch，不执行 add/move/delete。只有实体明确声�?`interaction_capability` 时，才进�?`interaction_candidates`；未知能力保持为空�?
完整 R3 前禁止接入可执行下游 Agent。后续写入必须统一经过�?
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

已通过�?
```text
34 �?Runtime / ActionIntent / Snapshot / Inspector / ModelImport 聚焦测试
LANChat Runtime Guard 回归
Python syntax compile
```

额外修复：远端统一 `RemoteTaskRunner` 恢复瞬时查询断连重试，保持“任务只提交一次，poll 可重试”，避免重复提交混元任务�?
## 7. 下一�?F5

### 儿童卧室

- 对账 room_box、room_floor、家具和追加实体�?- 核验 Engine、RuntimeState、OperationLog、Registry、Snapshot、final report �?ID、数量和版本�?
### 森林营地

- 草地、天空、森林进�?environment/substrate�?- 帐篷、小木桌进入 actor/model�?- 不生�?room_box�?
### 室内外混�?
- terrain、room shell、floor、transition zone 身份独立�?- Snapshot 能分别查询环境和普通实体�?
### 多人

- 非房主端不调�?Provider�?- Actor、PlanPatch、回复各出现一次�?- 房主与成�?`entity_id + version` 一致�?- 同步失败�?Snapshot 明确标记 `partial`�?
以上真实 Engine、渲染、碰撞、同步和多端一致性均标记�?**[�?F5/实机验证]**�?
## 8. Entity Version 闭环

本轮补齐�?`scene_entity_registry -> SceneWorldSnapshot -> SceneInspectorAgent` 的实体版本语义：

- 每个 actor、environment、substrate 实体均输出正整数 `version` �?`version_source`�?- C++/Engine 返回 `actor_version` 时优先采用真实版本；没有真实版本时回退到当�?`ScenePlan.version`�?- Actor 导入时独立生成稳�?Runtime `entity_id`，不再默认把 native actor handle 当作实体身份�?- Registry 同时保留 `actor_id`、`source_plan_id`、`source_batch_id`，便于定位实体来源�?- `SceneInspectorAgent` 输出实体版本，Snapshot 版本变化后必须重新分析�?
自动验证已覆�?native actor handle 变化但稳定请求身份不变、Engine 版本优先�?ScenePlan 版本兜底�?
房主端与成员端是否能稳定�?`entity_id + version` 去重仍标记为 **[�?F5/实机验证]**�?
## 9. M5 多人 Scene Sync 代码闭环

本轮补齐�?LANChat 多人场景同步中原先只打印占位日志的前端断点：

- 房主端通过 `scene.listActorTree` 获取真实 Actor 快照，并继续使用现有 NetworkSystem 广播�?- 成员端在模型文件传输完成后，通过 `sceneTools.createActor` 创建 Actor；重复消息使�?`actor_guid` 和版本账本幂等处理�?- Actor state/transform 更新复用同一 native create/update 接口，设�?`skip_if_exists/update_if_exists`，不重复创建实体�?- 旧版本更新不得覆盖成员端已应用的新版本�?- `__room_box`、`__room_terrain`、`__terrain_boundary` �?AI 场景框架实体进入同步允许列表，不再因 `__` 前缀被前端过滤�?- 接收端写入期间设�?`_suppress_network_broadcast` 并暂�?dirty sync，避免回环广播�?- Python 发布侧按 `scene + actor_guid` �?Actor create 做全生命周期去重；Actor 版本变化只走 state/transform 更新，不再次广播 create�?
自动验证已覆盖：

```text
LANChat Scene Sync 静态协议检�?Actor create 跨事务去�?Actor version 变化不重复发�?create
Python syntax compile
```

仍需明确区分：以上说明前端与 Python 同步接口已经接通，不代表多人实机已通过。以下继续标记为 **[�?F5/实机验证]**�?
- 房主和成员实际出现相同的 environment/actor 集合�?- 真实 transform 更新能在两端保持一致且无乱序回退�?- 模型文件传输完成�?Actor 只创建一次，�?UI 不发生明显卡顿�?- `scene_entity_registry` 与两�?Engine Actor �?`entity_id/version` 一致�?- 当前 C++ 文件传输主要按项目相对路径复用；跨路径按稳定 `asset_id` 去重仍需后续协议收口，不能在本轮宣称完成�?
## 10. Runtime 实体身份贯�?C++ Actor

本轮补齐�?`SceneWorldSnapshot` �?Engine Actor 快照之间的身份断点：

- 普通模型和 environment 导入在进�?`RuntimeGuard -> EngineWriteGate` 前生成并携带稳定 `actor_guid`、`entity_id`、`asset_id/model_ref`、`source_plan_id/source_batch_id` 和初始版本�?- C++ `NativeEditorActor` 保存上述 Runtime 元数据，并通过现有 Scene actors INI 持久化；场景重载后不应退化为仅有 native handle 的匿�?Actor�?- `actor_to_json()` �?Runtime 身份�?`actor_version/version` 原样返回，现�?LANChat actor snapshot 无需扩展网络包即可携带同一实体身份�?- 原生 transform 写入成功后递增 `actor_version`，成员端可继续按 `actor_guid + version` 拒绝过期更新�?- environment 事实�?C++ `actor_version` 归一�?Runtime `entity_version`，继续满足现�?Environment schema�?
聚焦自动验证覆盖�?
```text
普通模型导入保�?Runtime 身份
environment 导入保留 Runtime 身份
C++ Actor snapshot 输出身份和版�?C++ Scene actors 持久�?重载身份字段
transform 更新递增 actor_version
Python syntax compile
```

以下仍为 **[�?F5/实机验证]**�?
- native 场景保存并重载后 `entity_id/asset_id/version` 在面板快照中保持不变�?- 房主与成员收到相�?`entity_id + actor_version`，且�?transform 不覆盖新版本�?- Registry、SceneWorldSnapshot 与两�?Engine Actor 的身份、数量和版本一致�?- 跨路径模型资源按稳定 `asset_id` 去重传输�?
本轮尝试运行一�?`verify_ultimate_plan.py` 总门禁，但当前进程持续约 54 分钟仍未退出；同一工作站还存在更早启动且长期未退出的旧门禁进程。为避免继续占用验证资源，本轮门禁被显式终止，不能计为通过。聚焦测试与 syntax compile 已通过；总门禁悬挂原因需单独排查，不�?Runtime 身份闭环混为一项�?
## 11. M5 资源传输按稳�?asset_id 去重

本轮在不修改 `ACTOR_CREATE / FILE_REQUEST / FILE_CHUNK` 网络包格式的前提下，补齐了接收端资源传输去重�?
- 接收端从现有 `actor_json` 结构化读取稳�?`asset_id`；缺失或无效时保持原有按路径传输行为�?- 同一 `asset_id` 正在传输时，后续 Actor 加入同一个传输组，不重复发送文件请求；每个 Actor 仍保留自己的 `actor_guid`、transform �?Runtime 元数据�?- 同一 `asset_id` 已完成接收且本地文件仍存在时，后�?Actor 直接复用已接收模型路径，不再次传输模型和依赖文件�?- 超时、Actor 删除、停止会话和项目根目录切换时清理相应索引，避免旧传输组或跨项目缓存污染�?- 传输结束后才逐个释放等待 Actor 到现�?`pollPendingActorCreate -> sceneTools.createActor` 链路，没有新增绕�?EngineWriteGate 的写入口�?
聚焦自动验证覆盖�?
```text
asset_id �?actor_json 读取而非扩展线协�?同资产传输组和已接收缓存存在
Runtime Actor 身份快照回归
LANChat Scene Sync 静态协议回�?```

完整 `NativeSceneToolsRpcTests` 本轮共运�?149 项，148 项通过；唯一失败是远�?`engine.cpp` 已启�?mesh simplification，而旧断言仍要求关闭。该失败与本轮网络资源去重无关，未在本提交中顺手修改�?
以下仍为 **[�?F5/实机验证]**�?
- 两个 Actor 同时引用同一资产时只发生一次真实模�?依赖文件传输，并各自只创建一次�?- 相同 `asset_id` 但来源路径不同的 Actor 能复用已接收文件，且材质依赖仍正确加载�?- 传输中删除一个等�?Actor 不影响同组其�?Actor；删除最后一�?Actor 后传输组可安全回收�?- 房主与成员的 `entity_id + asset_id + actor_version`、SceneWorldSnapshot �?Engine Actor 数量一致�?- 大模�?LAN 传输期间 UI 卡顿、带宽占用和同步时序满足验收要求�?
## 12. Engine Snapshot 身份保留与世界一致性审�?
本轮继续修复�?`C++ Actor snapshot -> Python Runtime` 接口断点：C++ 已返�?Runtime 身份，但旧快照适配器只保留 Actor 名称、transform �?AABB，丢失了 `entity_id/asset_id/model_ref/actor_version`，因此无法可靠完�?Engine、Registry �?SceneWorldSnapshot 对账�?
当前改动�?
- Engine snapshot 归一化保�?`entity_id`、`asset_id`、`model_ref`、`entity_type`、`semantic_role`、`plan_id/batch_id` �?Actor/Entity version�?- 真实 Engine AABB 到达时记�?`bounds_source=engine_actual`、`engine_lifecycle_status=bounds_ready` 和本�?`engine_imported`；不伪造多�?`synced`�?- 新增只读接口 `runtime.scene_world_consistency.audit`，只消费 `SceneWorldSnapshot + engine_scene_snapshots`�?- 审计按稳�?`entity_id` 对账，不根据名称或路径猜测身份；输出缺失、额外、无 Runtime 身份、重�?ID、actor/asset/version 漂移�?- 审计被注册为 READ_ONLY，不创建 ScenePlan、PlanPatch、BatchPlan、ToolCallGraph �?Engine 写入�?- Finalizer �?`scene_world_snapshot_ready` 之后、`report_ready` 之前记录 `runtime_scene_world_consistency_audited`；最终报告持久化同一份审计结果，F5 不再需要从零散日志人工拼接五方一致性�?
聚焦自动验证�?
```text
Engine snapshot 身份和实�?AABB 保留
Runtime/Engine 身份完全一�?-> consistent
缺少身份、asset/version 漂移 -> needs_review
Snapshot/ActionIntent/Inspector/RuntimeGuard 聚焦回归 29 项通过
LANChat Scene Sync 静态检查通过
Python syntax compile 通过
```

一次包含完�?`test_lanchat_runtime_guard` 的大套件因大量历史长等待用例运行�?8 分钟仍未结束，被显式终止；没有观察到失败。本轮按约束文档改跑直接相关�?29 项聚焦测试，不将被终止的大套件计为通过�?
以下仍为 **[�?F5/实机验证]**�?
- 儿童卧室、森林营地、混合场景的审计结果达到 `consistent`，或准确列出真实漂移实体�?- Finalizer 后抓取的 Engine snapshot 与不可变 SceneWorldSnapshot 使用同一 plan/version�?- 房主与成员分别审计时 `entity_id/asset_id/version` 和实体数量一致�?- 多人传输失败时审计和 Snapshot 正确体现 `partial/needs_review`，不虚报 Game-ready�?
## 13. LANChat 世界一致性审计披�?
本轮补齐�?Runtime 审计到用户可见报告的最后一段只读链路。此�?`scene_world_consistency_audit` 已由 Finalizer 写入报告，但 LANChat �?Runtime Report 和状态查询没有消费该字段，导致用户无法判�?Engine、RuntimeState �?SceneWorldSnapshot 是否一致�?
当前改动�?
- Runtime Report 新增 `world consistency` 摘要�?- Runtime 状态查询新增“场景事实对账”摘要�?- 只披�?`consistent / needs_review / blocked`、匹配数量、Engine 实体数量和问题总数�?- 不披�?`entity_id`、`actor_id`、模型路径或具体漂移列表；详细证据仍保留�?Runtime 报告�?OperationLog 中供调试�?- Engine 快照尚未到达时明确显示“等�?Engine 场景快照”，不把 blocked 误报为失败或完成�?
聚焦自动验证�?
```text
consistent / needs_review / blocked 三态格式化
Runtime Report �?Runtime 状态查询均可见审计摘要
内部 entity_id 不进入聊天室文本
Python syntax compile 通过
```

以下仍为 **[�?F5/实机验证]**�?
- Finalizer 完成后聊天室最终报告显示“对账通过”，且数量与 Scene 面板一致�?- Engine Actor 晚到时状态从“等待快照”更新为“对账通过”或准确的“需要复核”�?- 多人房主与成员看到的对账状态不矛盾；成员端没有完整 Runtime 事实时不得伪造一致�?
## 14. 同步异常阻断 Game-ready

本轮复核发现，Registry 旧逻辑只要�?`sync_status` 非空，因�?`partial / failed / needs_attention` 也可能被计入 Game-ready，进而让下游 Agent 读取到“流程完成但多人事实并不完整”的世界�?
当前改动�?
- 单机已知状�?`engine_created / engine_imported / runtime_state` 和真实多人状�?`synced / synchronized` 继续允许参与 Game-ready 判定�?- `partial / failed / needs_attention / timeout / abandoned / cancelled / deleted` 明确阻断 Game-ready�?- 异常同步实体增加 `readiness_missing_fields=[sync_status_ready]`，Snapshot 可定位到具体实体，而不是只给房间级模糊失败�?- `SceneWorldSnapshot.world_readiness` 自动降为 `needs_review`；不把同步不完整世界提供给后续可执行 Agent�?
聚焦自动验证�?
```text
partial sync_status -> game_ready_entity_count=0
Snapshot world_readiness=needs_review
缺失事实包含 sync_status_ready
Game-ready / ActionIntent / SceneInspector 27 项通过
Python syntax compile 通过
```

以下仍为 **[�?F5/实机验证]**�?
- 真实 LAN 传输失败或成员离线时，对应实体的 `sync_status` 能被 Runtime 记录�?partial/failed�?- 传输恢复�?readiness reconcile 能将实体恢复为可用状态并生成�?scene version�?- 房主与成员的 Snapshot 对同一实体给出一致版本与同步状态�?
## 15. Snapshot 世界指纹�?transform/AABB 对账

本轮继续复核发现，旧一致性审计只检�?`entity_id / actor_id / asset_id / version`，即�?transform �?world AABB 已发生漂移，仍可能被误判�?`consistent`。这不足以支撑多人世界一致性，也不能作为下�?Agent 的乐观并发依据�?
当前改动�?
- 一致性审计增�?transform �?world AABB 对账，分别输�?`transform_mismatches` �?`world_aabb_mismatches`�?- `SceneWorldSnapshot` 增加排序无关�?`world_fingerprint`，由 plan/version 以及稳定实体身份、资源身份、版本、transform、world AABB 生成�?- Engine 审计生成同口�?`engine_fingerprint`，并输出 `fingerprints_match`�?- `runtime.scene_world_snapshot.get` 顶层返回 fingerprint；找不到计划或版本时返回空值，不伪造�?- `SceneInspectorAgent` 分析结果绑定 `scene_version + world_fingerprint`，同版本�?late-ready 几何事实变化也可触发重新分析�?
聚焦自动验证�?
```text
身份、版本、transform、AABB 一�?-> consistent + fingerprint match
transform/AABB 缺失或漂�?-> needs_review
Snapshot fingerprint 为稳�?64 位摘�?SceneInspector 输出绑定 fingerprint
Game-ready / Inspector / ActionIntent 27 项通过
Python syntax compile 通过
```

以下仍为 **[�?F5/实机验证]**�?
- 房主 Runtime Snapshot 与本�?Engine snapshot �?fingerprint 一致�?- 成员�?Actor 同步完成后，�?Engine 实体事实与房主权�?Snapshot 对账一致�?- transform 更新、late-ready AABB 和追加批会产生新�?fingerprint，旧分析不会被继续使用�?
## 16. C++ LAN 同步事实接入 AgentRuntime

本轮修复了多人同步验证中的假覆盖：Python 已有 `handle_lanchat_sync_event()` �?Runtime reducer，但真实 Worker 只轮询聊天室消息与房间事件，C++ Actor/资源生命周期从未进入 RuntimeState�?
当前改动�?
- C++ `NetworkSystem` 新增有界 `LanChatSyncEvent` 队列�?Python pop binding，不修改现有网络包协议�?- `ACTOR_CREATE`、transform、delete、state update 和资源传输完成会产出结构化同步事实�?- 网络收到 Actor 只记�?`actor_create_received`；远�?Actor identity 注册成功后才记录 `actor_imported`，不把网络接收伪装成 Engine 成功�?- Worker �?tick �?Runtime drain 前消费同步事实，并展开已有 `actor_json` 中的 plan/batch/entity/asset/version 元数据�?- Runtime 保留 actor/entity 版本、语义角色与同步生命周期，现�?RuntimeGuard/StatePatch 写门保持不变�?
聚焦自动验证�?
```text
C++ 队列、事件生产点�?Python binding 静态核�?Worker 原生同步事件轮询�?actor_json 元数据展开
actor_create_received != actor_imported
既有 actor create/transform/delete Runtime 回归
Python syntax compile
```

以下仍为 **[�?F5/实机验证]**�?
- �?C++ binding 可在完整引擎中编译、加载并持续出队�?- 真实 LAN 文件传输完成、远�?Actor 创建�?identity 注册按预期产生一次事件�?- 高事件速率下有界队列不会造成关键终态事实丢失�?
## 17. 成员端只�?Peer Mirror Snapshot

真实宿主同步�?`plan_id` 在成员本地没有对�?ScenePlan。旧逻辑会以 `no runtime plan` 拒绝这些事实，因此成员端无法形成可供只读下游 Agent 使用�?SceneWorldSnapshot�?
当前改动�?
- 仅接�?`authority=remote_host` 且包�?actor/asset 身份的未知计划同步事实进�?`peer_mirror`�?- Peer mirror 不创�?ScenePlan、BatchPlan、ToolCallGraph、PlanPatch �?Provider 请求，也不执�?Engine 写入�?- `runtime.scene_world_snapshot.get` 在没有本�?active/latest plan 时回退只读 peer mirror，并标记 `snapshot_authority=peer_mirror`、`snapshot_stability=peer_mirror`�?- 成员�?Snapshot 继续使用 Registry/Game-ready 规则；缺少真�?AABB、grounding 或同步终态时保持 `needs_review`，不伪�?Game-ready�?- 非宿主权威的未知 plan 同步事实继续被拒绝�?
聚焦自动验证�?
```text
未知宿主 plan -> peer mirror Snapshot
peer mirror 不创建本�?ScenePlan/执行队列
非宿主未�?plan -> rejected
Snapshot/Game-ready/SceneInspector/同步�?24 项通过
Python syntax compile
```

以下仍为 **[�?F5/实机验证]**�?
- 房主与成员的 `entity_id/asset_id/actor_version/transform/AABB` �?fingerprint 一致�?- 成员远端 Actor identity 注册及真�?AABB 到达后，Snapshot �?`needs_review` 正确收敛�?- 房主切换执行计划或追加场景版本时，成�?peer mirror 不回退到迟到旧事实�?
## 18. Runtime 同步版本单调�?
前端已经�?`actor_guid + actor_version` 拒绝�?Actor 更新，但 Runtime 同步 reducer 之前仍会直接应用迟到事件中的 transform/AABB。这会造成 Engine 已保留新版本，而成�?SceneWorldSnapshot 被旧事实覆盖�?
当前改动�?
- 同步事件显式携带 `actor_version/version` 时，Runtime 在创�?StatePatch 前与现有 ActorFact 版本比较�?- 低于当前版本的事件记录为 `sync_event_record_skipped: stale actor version`，不修改 ActorFact、Registry、Snapshot �?fingerprint�?- 未携带版本的旧协议事件保持兼容，不凭默认版本 1 错误拒绝�?- 同版本事件仍可补齐晚�?AABB/readiness 事实，避免阻断合法的 Engine-ready 收敛�?- Runtime/GM 状态摘要与公开 Snapshot 使用同一目标优先级；成员没有本地 ScenePlan 时可只读显示 peer mirror 实体世界�?authority，不再错误显示“无计划”�?
聚焦自动验证�?
```text
actor version 4 后收�?version 3 -> rejected
�?transform/AABB 不覆盖新事实
Snapshot world_fingerprint 保持不变
Snapshot/Game-ready/SceneInspector/同步�?24 项通过
```

以下仍为 **[�?F5/实机验证]**�?
- 真实网络乱序或重放时，成�?Engine �?Runtime 均拒绝旧版本�?- 同版本的 identity、AABB 和同步终态补齐不会被误判为重复而丢失�?- 房主追加批产生的�?actor/scene version 能在成员端单调收敛�?
## 19. 宿主世界 AABB 与成员本�?Engine AABB 分域

多人同步中的 `actor_json` 可以携带宿主测得�?world AABB，但该事实只能证明宿主世界中的几何范围，不能证明成员进程已经在本�?GeometrySystem 中完成模型加载。旧逻辑将两者都记录�?`bounds_source=engine_actual`，可能让成员 peer mirror 在本�?Actor 尚未 materialize 时提前进�?Game-ready�?
当前改动�?
- `authority=remote_host/remote_peer` 的同�?AABB 分别记录�?`remote_host_actual/remote_peer_actual`�?- 远端 AABB 保留为共享世界事实，但不设置成员本机 `bounds_ready`，也不把本机 Engine 生命周期提升�?`bounds_ready`�?- `actor_imported` 只证明成员本机已注册 Actor identity，状态收敛到 `engine_imported`；它不伪造本�?AABB�?- 只有 `runtime.scene.snapshot` 从成员本�?Engine 读取到真�?AABB 后，才覆盖为 `bounds_source=engine_actual` 并允许进�?Game-ready 判定�?- Engine snapshot 的已�?Actor 投影保留 `model_ref`、Actor/Entity version 和同步身份，防止刷新真实几何时丢失稳定资源身份�?- environment component 使用同一来源边界，远�?room/terrain bounds 不会提前完成成员本机 environment readiness�?
聚焦自动验证�?
```text
宿主 AABB 到达 -> peer mirror needs_review
成员 actor_imported -> 仍等待本�?engine_actual AABB
成员本机 scene snapshot -> engine_actual + engine_verified + game_ready
迟到旧版�?transform/AABB -> rejected，world fingerprint 不变
Snapshot/Game-ready/SceneInspector/同步�?24 项通过
ActionIntent 聚焦回归 8 项通过
LANChat Scene Sync 静态检查通过
Python syntax compile 通过
```

历史 `test_agent_runtime_phase1` 大套件本轮运行超过两分钟仍未完成，已显式终止；已执行部分未见失败，但不计为通过，也不作为本轮提交证据�?
以下仍为 **[�?F5/实机验证]**�?
- 成员接收模型后，`actor_imported` 与本�?GeometrySystem AABB 事件按预期先后到达�?- 宿主 Snapshot 可以先用于只读世界展示，但成员在本机 Actor 未就绪前保持 `needs_review`�?- 成员本机 snapshot 到达后，Registry/Snapshot/fingerprint 自动收敛且不丢失宿主 plan/entity/asset/version 身份�?- environment 和普�?Actor 均遵守同一事实来源边界�?
## 20. LAN 同步事实队列背压与终态保�?
C++ `LanChatSyncEvent` 队列此前在超�?256 项后直接删除最老事件。多人场景中 transform/state update 可能高频进入队列，这种策略会连带丢失更早�?`actor_create_received`、`actor_imported`、`actor_deleted` �?`asset_transfer_completed`，导致成�?RuntimeState 永远缺少收敛终态�?
当前改动�?
- 同一 Actor、同一事件类型�?`actor_transform/actor_updated` 在待消费队列中只保留最新快照�?- transform �?actor state update 不互相覆盖，避免不同事实集合被错误合并�?- 队列超过软上限时优先移除可合并的 best-effort 事件，不删除关键生命周期终态�?- 仅由关键事实构成的队列允许短时超过软上限，并�?2048 项紧急硬上限保护；触发硬上限会输出明确告警�?- 不修改现�?LAN 网络包格式、Actor 创建协议�?Python binding，只调整 Runtime 同步事实桥的本地背压语义�?
聚焦自动验证�?
```text
C++ 同步桥事件生产点与背压策略静态核对通过
Snapshot/Game-ready/SceneInspector/ActionIntent/同步�?32 项通过
LANChat Scene Sync 静态检查通过
```

以下仍为 **[�?F5/实机验证]**�?
- 高频拖动多个 Actor 时，同一 Actor �?transform 事件被有效压缩且最终位置不丢失�?- 文件传输�?transform 高并发期间，Actor create/import/delete �?asset complete 终态均进入 RuntimeState�?- 队列压力不会造成明显主线程卡顿；若触发硬上限告警，需要进一步拆分关�?快照双队列�?
## 21. 五方对账禁止忽略未物化实�?
本轮复核 M3 五方对账时发现，一致性审计此前只把带 `actor_id` �?Runtime 实体纳入 Engine 对账。尚未物化的 environment、substrate 或普通实体会被排除，导致“Runtime 世界仍有 planned 实体，但剩余 Actor �?Engine 完全一致”时错误返回 `consistent`，世界指纹也可能出现假一致�?
当前改动�?
- `non_materialized_entity_count` 计入一致性审计问题总数；只�?Snapshot 中存在尚未形�?Engine Actor 的实体，审计至少�?`needs_review`�?- `expected_entity_count` 统一表示 Runtime 世界完整实体数，并单独披�?`materialized_entity_count/non_materialized_entity_count`，避免“expected �?Engine 数量相等但仍漏实体”的统计歧义�?- Runtime world fingerprint 使用完整下游可见实体集合，不再只对已物化 Actor 求摘要�?- Engine fingerprint 继续只由真实 Engine Actor 生成；两者在未物化实体存在时必须不同�?- Engine Actor 缺失或漂�?`actor_id/asset_id/model_ref/version` 时均输出明确 mismatch；空值不再绕过检查�?- �?fingerprint 仍出现未被字段级诊断覆盖的差异，审计记录 `unclassified_fingerprint_mismatch_count` 并降级为 `needs_review`，禁�?`consistent + fingerprint mismatch` 的矛盾状态�?- Snapshot �?`game_ready` 现在�?Engine 一致性审计约束：审计�?`needs_review/blocked` 时，公开 Snapshot 与最终报告统一降级�?`needs_review`，实体级 Registry readiness 保留用于诊断�?- Finalizer 顺序调整�?`registry ready -> consistency audited -> snapshot ready -> report ready`；不会再先发�?Game-ready Snapshot、随后才发现 Engine 漂移�?- provisional Snapshot 同样读取当前 Engine snapshot 进行约束；缺�?Engine snapshot 时不能供可执行下�?Agent 使用�?- immutable Snapshot 重放持久化报告中的一致性结论；旧报告缺少审计或审计未通过时保持保守降级，不因重新读取而恢复成 Game-ready�?- Finalizer 已有�?`runtime_scene_world_consistency_audited` 与最终报告会直接继承该严格判定，不新增旁路状态源�?
聚焦自动验证�?
```text
完整物化且身�?transform/AABB 一�?-> consistent
身份、版本、transform �?AABB 漂移 -> needs_review
存在未物�?Runtime 实体 -> needs_review + fingerprint mismatch
Game-ready 聚焦套件 19 项通过
LANChat 世界一致性披露、Inspector �?Peer Mirror 聚焦回归 7 项通过
Game-ready 聚焦套件 22 项通过
Inspector、Peer Mirror、同步桥�?LANChat 披露聚焦回归 10 项通过
```

以下仍为 **[�?F5/实机验证]**�?
- 儿童卧室、森林营地和混合场景最终审计不存在未解释的 `non_materialized_entity_count`�?- Provider �?Engine 导入失败时，最终报告准确列出未物化实体并保�?`needs_review/partial`�?- 追加批执行期�?Snapshot 的临时未物化实体不会被错误披露为 Game-ready；追加批完成后新版本重新收敛�?
## 22. Finalizer 终态事件按场景版本幂等

本轮复核生成后追加批时发现，`scene_entity_registry_ready` �?`scene_world_snapshot_ready` 此前只按 plan 判断是否已经记录。同一计划第一次完成后再追加实体，即使 `scene_version` 已增加，第二�?Finalizer 也可能跳过新版终态事件，导致成员端和只读下游 Agent 停留在旧世界版本�?
当前改动�?
- Registry/Snapshot ready 事件改为�?`plan_id + scene_version` 幂等�?- 同一版本�?worker 重试重复进入 Finalizer 时不重复发布�?- 追加批令计划版本增加后，新版本重新发�?Registry 与受 Engine 一致性约束的 Snapshot�?- Registry ready payload 增加 `scene_version`；Snapshot ready 继续携带版本并新增一致性状态�?- 不创建新�?ScenePlan，不改变追加批、RuntimeGuard �?EngineWriteGate 主链�?
聚焦自动验证�?
```text
version 1 Finalizer -> registry/snapshot ready 各一�?version 2 Finalizer -> registry/snapshot ready 各新增一�?version 2 重试 -> 不重复发�?Game-ready、Inspector、Peer Mirror、同步桥�?LANChat 披露相关回归 33 项通过
```

以下仍为 **[�?F5/实机验证]**�?
- 生成完成后追加一个实体会�?scene version 增加，并在聊天室与成员端出现对应的新 Snapshot�?- 追加批期间旧 immutable Snapshot 保持可读，但不能冒充新版本�?- 新版 Snapshot �?Engine Actor、Registry、最终报告的实体数量�?fingerprint 一致�?
## 23. Engine Snapshot 绑定场景版本

追加批完成后，Runtime 世界已按 `scene_version` 演进，但 Engine snapshot 此前只记�?plan 和时间戳。旧版本快照若晚到，`latest_engine_snapshot()` 可能把它当成当前世界参与 Finalizer 对账，导致新版本无法稳定收敛。完成态与成员 peer mirror 的手动刷新还沿用�?active-plan 解析，可能写出空 plan 或默�?version 1�?
当前改动�?
- `runtime.scene.snapshot` ToolCall 显式携带当前 ScenePlan version�?- Engine snapshot fact 增加并校验正整数 `scene_version`；ToolResult、StatePatch �?RuntimeState 使用同一字段�?- snapshot 选择器优先匹�?`plan_id + scene_version`，不使用显式旧版本或未来版本冒充当前世界�?- 无版本历史快照仅作为兼容 fallback；新链路产生的快照必须版本化�?- `refresh_scene_snapshot()` 目标统一�?`active_execution -> latest_completed -> peer_mirror -> discussion`，并携带对应版本�?- 成员 peer mirror 在本�?Engine snapshot 到达后可�?`needs_review` 收敛；完成态本地计划不再因 active execution 已清空而丢失快照归属�?- 接入时曾发现 Snapshot validator allowlist 漏接新字段；已补�?schema，并用原 snapshot/Finalizer 测试验证 ToolGraph 不再被安全校验误拒绝�?
聚焦自动验证�?
```text
version 2 世界 + 晚到 version 1 快照 -> 选择 version 2
只有显式旧版本快�?-> 当前版本视为 snapshot unavailable
Batch ToolCall 携带 ScenePlan version
latest completed plan 刷新保留 plan/version
peer mirror 本机快照按宿�?scene version 收敛
Game-ready、Inspector、Peer Mirror、同步桥�?LANChat 披露 36 项通过
真实 snapshot/Finalizer 聚焦回归 9 项通过
```

以下仍为 **[�?F5/实机验证]**�?
- 追加批前�?Engine snapshot 分别携带正确 scene version，晚到旧快照不影响当前报告�?- 房主与成员端本机 snapshot 使用同一宿主 plan/version，但各自保留本机 Engine AABB 来源�?- Engine snapshot 缺失当前版本�?Snapshot 保持 `needs_review`，当前版本到达后自动收敛�?
## 24. 下游 Agent gameplay 事实不再使用模板默认�?
本轮审查 `scene_entity_registry -> SceneWorldSnapshot -> SceneInspectorAgent` 契约时发现，默认 Actor 导入器会为所有对象统一声明 `inspect/move`、`scene_actor/runtime_generated` 和静态碰撞；环境模板也会仅凭名称�?component type 推导 `walk_on`、`walkable` 和物理配置。这些字段没有来�?EntityIntent �?Engine 的可信证据，交给后续 Agent 后会被误认为可执行能力�?
当前改动�?
- 默认 Actor �?`interaction_capability/gameplay_tags/physics_profile` 改为空�?- 环境组件和未物化 substrate 的上述字段同样保持为空�?- ScenePlan、StatePatch �?Engine 结果显式提供的可信字段仍原样进入 Registry �?Snapshot�?- `entity_type/semantic_role/component_type/environment_profile/grounding_status` 继续承担场景语义描述，不�?gameplay 字段重复猜测�?- 不修改资源生成、Engine 导入、AABB、Finalizer 或多人同步主链�?
聚焦自动验证�?
```text
默认 Actor/环境/substrate -> gameplay 字段为空
显式 Actor gameplay 字段 -> Registry 原样保留
显式环境 gameplay 字段 -> Registry 原样保留
森林营地对象/环境分流回归通过
Python syntax compile 通过
```

以下仍为 **[�?F5/实机验证]**�?
- 实机场景 Snapshot 中未�?gameplay 字段保持为空，不影响 Registry/报告完成�?- 后续 SceneInspectorAgent 不会把空能力扩写成可执行动作�?- 未来能力识别必须由独立、可审计�?EntityIntent/CapabilityPatch 写入，而不是恢复名称模板默认值�?
## 25. SceneWorldSnapshot API 严格只读

复核公开 Snapshot 接口时发现，`get_scene_world_snapshot()` 虽然不创�?ToolGraph �?PlanPatch，但统一消息入口和查询方法仍会把每次读取写入世界 OperationLog。结果是只读 Inspector 每分析一次场景都会推�?operation cursor，连续读取同一版本也会产生新的世界历史�?
当前改动�?
- `runtime.scene_world_snapshot.get` 不再�?`runtime_message_action_routed` �?snapshot queried 世界事件�?- 其他控制、写入和审计 action 继续完整记录 OperationLog，不放松执行审计�?- 连续读取同一 `plan_id + scene_version` 返回相同 fingerprint �?operation cursor�?- SceneInspectorAgent 读取 Snapshot 后，RuntimeState、ToolGraph、PlanPatch �?OperationLog 均不变化�?- Snapshot 仍从已有 RuntimeState、OperationLog、Registry �?Engine consistency fact 构建，不引入第二事实源�?
聚焦自动验证�?
```text
连续两次公开 Snapshot 查询 -> OperationLog 数量不变
连续两次公开 Snapshot 查询 -> cursor/fingerprint 稳定
SceneInspectorAgent 分析 -> 零世界写�?Inspector scene version 更新检测回归通过
```

以下仍为 **[�?F5/实机验证]**�?
- 下游 Inspector 频繁轮询不会改变聊天室终态事件窗口或成员�?cursor�?- 同一场景版本在房主与成员端读取时各自稳定，宿主发布新版本后再发生可解释变化�?
## 26. Native Chat 的房主权威门�?
多人权威复核发现，生成写入路径虽然已有本机角色检查，但每个节点都会收到的 Native Chat Queue 在进�?GM 控制、实体查询、ActionIntent、Coordinator 和方案上下文前没有统一门禁。进程内 MessageDispatchLedger 只能去重同一进程�?Native Queue/Agent Trigger，不能阻止房主和成员两个进程同时解释同一消息并回复�?
当前改动�?
- Native Chat 在任�?GM、Intent、Coordinator、Provider 或业务回复前检查本�?network session role�?- `client` 只标记该聊天消息已观察并等待房主权威结果，不执行 Agent 路由�?- 生成选项/VLM 环境设置同样移到权威门禁之后，成员端不能凭同步到的聊天修改本机执行选项�?- 成员仍通过独立 Native Sync Event 路径接收 Actor、asset、transform、AABB 和宿�?Snapshot，不影响 peer mirror�?- Agent Trigger 原有非房主门禁继续保留，形成两个消息入口的一致权威边界�?
聚焦自动验证�?
```text
成员收到房主 GM 消息 -> 不运�?Coordinator/Runtime、不回复
同一成员消息重放 -> 本地观察去重
房主 Runtime status query -> 继续正常处理
Native sync bridge + peer mirror 6 项回归通过
```

以下仍为 **[�?F5/实机验证]**�?
- 房主和成员同时在线时，同一聊天只产生一�?ActionIntent 和一条权威回复�?- 成员不调�?LLM/Provider，不创建 PlanPatch/Actor；仅消费宿主同步事实�?- 房主/成员 Snapshot �?entity/version/fingerprint 最终一致，成员本机 Engine �?ready 时保�?`needs_review`�?
## 27. 墙挂与悬挂支撑不得由名称推断为已验证

Game-ready grounding 复核确认，地面物体只有在 Engine transform 返回 `ground_snapped` 或真�?AABB bottom 已贴地时才会写入 `grounded`。但墙挂和悬挂对象此前只要名称命�?support type，就会默认写�?`not_applicable`；Registry �?Game-ready 判定接受该状态，因此尚未验证墙面/天花支撑的对象可能被错误计为可用实体�?
当前改动�?
- 名称分类只决�?`support_type`，不再证明墙�?悬挂已经安装正确�?- `wall_mounted/ceiling_hung/unknown` 若没有显�?Engine/可信支撑事实，统一保持 `grounding_status=needs_review`�?- 显式返回�?`wall_mounted/suspended` 仍可进入 Registry，并在其�?Engine-ready 条件满足时成�?Game-ready�?- 地面对象原有 AABB bottom snap、Engine transform 和贴地验证路径不变�?- 不把墙挂对象错误执行 floor snap�?
聚焦自动验证�?
```text
ready floor actor + Engine ground snap -> grounded
ready wall torch + 仅名�?support 分类 -> needs_review
wall actor -> 不调�?floor snap transform
Game-ready 聚焦套件 26 项回归通过
```

以下仍为 **[�?F5/实机验证]**�?
- 火把、壁灯、地图、吊灯等对象在真�?Engine 场景中不被拉到地面�?- 未接入墙�?悬挂验证的对象在 Snapshot 中明确列�?needs_review�?- 后续若增�?wall/ceiling support checker，必须以独立 ToolResult/StatePatch 写入可信状态�?
## 28. Runtime Evidence 只统计业�?ToolCallGraph

最新旧�?F5 日志显示 5 个业务批次对�?151 �?ToolCallGraph。报告层已经�?`graph_role` 分域，但 LANChat Evidence 只有在执行结果没有携�?graphs 时才�?RuntimeState 过滤；worker drain 返回全量内部图时会绕过过滤，导致日志、节点数和状态列表继续混�?query/state/finalizer 图�?
当前改动�?
- Evidence 无条件从 RuntimeState 按当�?plan 重建图集合，不信�?drain 返回的全�?graphs�?- 业务图由 `graph_role=business_batch` �?`BatchPlan.tool_graph_id` 双重识别，兼容早期持久化数据�?- 图状态、active/terminal �?node 数只统计业务批次图�?- 内部图仅保留独立 `internal_graph_count`，不进入用户可见执行状态列表�?- 日志字段改为 `graphs=business:X,internal:Y,...`，避免把内部编排量误读为业务批次数�?
聚焦自动验证�?
```text
输入包含全量 Runtime graphs -> Evidence 仅返回业务图
business_graph_count == graph_count
internal_graph_count > 0 且不进入业务节点统计
单图执行回复与报�?graph domain 回归通过
```

以下仍为 **[�?F5/实机验证]**�?
- 下一�?3-5 个业务批次日志中�?business graph 数与 BatchPlan 数一致�?- internal graph 数可增长，但不影�?GM/UI 的业务进度和完成判断�?
## 29. F5 Evidence 披露 Game-ready 缺失事实

�?F5 最终状态为 14 个实体�? �?Game-ready，但 Evidence 只打印总数，无法现场判断其余实体究竟缺�?Engine AABB、grounding、resource identity、sync 还是 Engine ready。Registry 已经有逐实体和聚合缺失字段，本轮只把这份既有事实接到现�?Evidence�?
当前改动�?
- Evidence 增加 `readiness_missing_field_counts`，直接读�?scene_entity_registry 聚合�?- LANChat Runtime 日志增加紧凑 `readiness_missing={...}` 字段�?- 不新�?Replay、检查器或第二状态源，不改变 Game-ready 判定�?- 下一�?F5 可直接判�?Engine Snapshot/reconcile 修复后剩余断点�?
聚焦自动验证�?
```text
Registry 缺失字段聚合 -> Evidence 原样披露
execution reply/evidence 既有字段回归通过
```

以下仍为 **[�?F5/实机验证]**�?
- 旧运行的 14/3 是否主要�?`engine_actual_aabb/engine_ready/grounding_status` 缺失造成�?- 当前版本 Finalizer reconcile 后，各缺失项是否降为 0；若不为 0，日志可直接定位责任域�?
## 30. 当前权威文档切换为双轨推进与分级门禁

为避免超长历史计划和旧约束文档继续产生执行口径歧义，本轮完成文档治理�?
- 新增 `R3稳定门禁与三职能Agent双轨推进计划.md`，作为当前唯一推进优先级来源�?- 新增 `Agent任务约束循环_R3三职能协同版.md`，作为当�?Agent / Codex 执行规约�?- 旧计划和旧约束循环保留历史正文，并增加新文档迁移提示�?- 后续阶段进度继续写入本文件；微小修改只保留在提交记录中�?
当前 Gate 仍为 `red / pending_reevaluation`：最�?F5 是旧代码�?`3/14 Game-ready` 结果，最�?Readiness、业务图分域、Finalizer �?Peer Mirror 修复仍需新一�?F5 验证。文档切换本身没有改�?Runtime、Engine 或多人同步代码�?
## 31. W0.2/W0.3 R3GateReport 与只读自动对�?
轨道 A 的首要断点此前只能依赖人工拼�?Runtime、Registry、Snapshot 和日志。本轮完成首个代码闭环：

- 新增稳定 `R3GateReport`、七个固定判定维度及 `R3GateReportValidator`�?- 新增纯聚合接�?`runtime.r3_readiness.evaluate`，统一读取当前 execution/completed plan 的既�?Runtime 事实�?- 七维覆盖 Snapshot、必要环境、实体身份与 readiness、Finalizer、业务批�?图、多人一致性和 Runtime 写入安全�?- `5/14` 判定 Yellow；`8/14` 且全部硬条件满足时判�?Green；环境缺失、Fingerprint 不稳、身份漂移或写入边界缺失判定 Red�?- `gate_report_id` �?`evaluated_at` 均由输入事实派生；相�?room/plan/version 和相同事实重复查询得到完全相同报告�?- 查询 action 不记�?`runtime_message_action_routed`，不存在�?room 也不会被 `RuntimeState.room()` 隐式创建�?- evaluator 不写 OperationLog、StatePatch、PlanPatch �?ToolCallGraph，不调用 Provider，不触发 Engine 写入�?
聚焦自动验证�?
```text
R3 readiness 新增测试 6 项通过
5/14 -> Yellow
8/14 + 全部硬条�?-> Green
环境缺失 / Fingerprint 错误 / duplicate entity_id -> Red
相同事实重复评估 -> 报告�?gate_report_id 完全一�?缺失 room 与已�?room 查询 -> RuntimeState/OperationLog 均零变化
AgentRuntime Game-ready + Phase 1 兼容回归 28 项通过
Python syntax compile 通过
```

当前任务状态：

```text
W0.2 R3GateReport 契约：code_complete
W0.3 只读 Gate evaluator：code_complete
W0.4 初始 Gate 锚点：等待最新可�?F5 事实
```

当前 Gate **仍为 `red / pending_reevaluation`**。以上证据只证明 Python 结构、边界和零副作用成立；旧 F5 �?`3/14 Game-ready` 仍是最新实机基准。Engine、多人一致性和实际 Green 判定均为 **[�?F5/实机验证]**�?
## 32. W1.2 计划�?Scene Snapshot 不再认领未知 Actor

复核�?F5 �?`14 entities / 3 Game-ready` 与当�?Scene Snapshot 调用链后，确认存在一个跨批次身份覆盖断点：每个业务批次开头都会执�?`runtime.scene.snapshot`；当调用没有携带 `known_actors` 时，Snapshot 工具此前会把所�?Engine 观察对象同时写入 `observed_actors` 和权�?`actors`，并补上当前 plan/batch。这样会把既有场景对象错误认领为当前计划实体，也可能把前几批 Actor 的稳定资源身份和原始 batch 归属覆盖为后一批�?
当前改动�?
- plan/batch scoped Snapshot 在没�?Runtime 稳定身份投影时，只写 `observed_actors` �?Engine snapshot，不写权�?`actors`�?- 只有通过 actor_id、entity_id、asset_id、model_ref 或唯一名称索引�?`known_actors` 明确匹配�?Engine 对象，才允许把真�?transform/AABB/lifecycle 回写�?Runtime Actor�?- 手动、无 plan/batch 的显式场景刷新继续允许登�?unmanaged native Actor，保留原有检查能力�?- 不修改模型生成、Actor import、RuntimeGuard、EngineWriteGate �?Finalizer 主链�?
聚焦自动验证�?
```text
plan-scoped snapshot + no known identity -> 观察�?native Actor，但不认领、不改批�?known Runtime actor + Engine snapshot -> 保留 plan/batch/asset identity，并吸收真实 AABB
Finalizer partial batch recovery -> 继续从唯一匹配�?native snapshot 收敛
AgentRuntime Game-ready 26 项通过
R3 readiness evaluator 6 项通过
Python syntax compile �?git diff --check 通过
```

当前任务状态：

```text
W1.2 稳定身份和真实几何事实：本断�?code_complete
W0.4 初始 Gate 锚点：仍等待最新可�?F5
```

以下仍为 **[�?F5/实机验证]**�?
- 多批次生成时，前�?Actor �?`entity_id/asset_id/model_ref/batch_id` 不再被后�?Snapshot 覆盖�?- Finalizer 使用 known identity 对齐 Engine Actor 后，`engine_verified` �?Game-ready 数量能否由旧基准 `3/14` 提升�?Yellow/Green 门槛�?- 未被当前计划拥有的既有场�?Actor 只出现在观察事实中，不进入当前计�?Registry/Snapshot�?
## 33. W0.4/W1.2 R3 Gate 输出逐实�?Readiness 责任字段

�?F5 只记�?`14 entities / 3 Game-ready` 和聚合缺失计数，无法证明剩余 11 个实体分别缺少身份、真�?AABB、Engine ready、贴地还是同步事实。`scene_entity_registry` 已经保存每个实体�?`readiness_missing_fields`，但 `runtime.r3_readiness.evaluate` 此前没有把这份既有事实带�?GateReport�?
当前改动�?
- `entity_readiness.metrics` 增加稳定排序�?`entity_diagnostics`，逐项披露 `entity_ref/entity_type/semantic_role/game_ready/readiness_missing_fields`�?- 诊断直接读取 `scene_entity_registry`，并合并 Gate 自己验证出的 `entity_id/asset_identity/actor_id/version` 身份缺失，不建立第二状态源�?- 已标�?`game_ready=true` 但缺少稳定身份的实体仍进入诊断并�?Gate �?Red，不能信任矛盾标记�?- 诊断默认最�?50 项，同时提供 total/truncated 计数，避免大场景报告无限增长�?- 输出�?`entity_ref` 排序并参与确定�?GateReport hash；相同事实重复查询仍得到相同结果�?- 不修�?RuntimeState、OperationLog、Registry、ToolCallGraph �?Engine，也不改变现�?Game-ready 判定�?
聚焦自动验证�?
```text
R3 readiness evaluator 7 项通过
5/14 Yellow -> 精确列出 9 �?needs-review 实体�?support_classification
game_ready 标记�?asset identity 矛盾 -> 逐实体诊断并�?Red
AgentRuntime Game-ready 26 项通过
SceneWorld peer mirror 4 项通过
Python syntax compile �?git diff --check 通过
```

当前任务状态：

```text
W0.4 Gate 逐实体诊断：code_complete
W1.2 Game-ready 实机提升：仍等待最新可�?F5
当前 Gate：red / pending_reevaluation
```

以下仍为 **[�?F5/实机验证]**�?
- 下一�?F5 �?GateReport 能否准确列出全部 needs-review 实体及真实缺失字段�?- Scene Snapshot 身份修复�?Game-ready 是否达到 Yellow（至�?5/14）或 Green（至�?8/14）门槛�?- 若仍未达标，必须�?`entity_diagnostics` 选择数量占比最高的真实责任字段继续修复，不能根据旧日志猜测�?
## 34. W3.1/W3.2/W3.6 三职能强类型契约底座

轨道 A 的跨批次 readiness 恢复已有聚焦集成测试证明；在等待最�?F5 重新评估期间，按 Red 能力矩阵推进首个独立轨道 B 交付物。本轮只建立协作契约，不连接 LANChat、真实或 Mock Snapshot、AgentRuntime、ActionProposal �?Runtime 写入路径�?
当前改动�?
- 新增独立 `services/agent_collaboration/contracts.py`，不导入 AgentRuntime 内部实现�?- 定义 `GameProjectState`、`ArtifactEnvelope`、`AgentTask` 和六种首�?Artifact payload DTO�?- `ArtifactEnvelope` 构造时规范化并深度冻结 payload，由实际 Validator 产生 `validation_result`；调用方不能传入伪�?hash 或默认“通过”结果�?- `content_hash` �?Artifact 类型、schema version 和规范化 payload 确定性计算；键顺序不影响 hash，内容变化必然改�?hash�?- 无效 payload 可作为审计事实存在，但状态强制为 `invalid`，不能声�?`validated` 或通过执行资格检查�?- 定义 `NonExecutableArtifactError` �?`assert_executable()`；`snapshot_source=mock` 在构造时必须同时�?`non_executable=true`，执行资格检查始终拒�?Mock�?- Mock 仅在契约测试 fixture 中使用，没有注册运行�?Agent 输入，也没有创建 EntityBindingPlan 生产入口�?- 本轮没有建立 ArtifactRegistry、TaskGraph、Coordinator、ProjectGate �?ActionProposal�?
聚焦自动验证�?
```text
六种首批 Artifact DTO -> 统一 Validator 通过
相同规范�?payload -> 相同 content_hash
payload 内容变化 -> content_hash 变化
Artifact payload -> 深度不可变，导出副本修改不污染原�?非法 payload -> validation_result.valid=false + status=invalid
伪�?validation_result 构造参�?-> 拒绝
Mock Artifact -> 可审计但 assert_executable 必然拒绝
GameProjectState / AgentTask 基础约束与规范化通过
独立导入 contracts -> 未加�?AgentRuntime/LANChat 模块
契约聚焦测试 8 项通过
Python syntax compile �?git diff --check 通过
```

当前任务状态：

```text
W3.1 Artifact �?Project 契约：code_complete
W3.2 Content Hash 与真�?Validator：contract_layer_code_complete
W3.6 Mock/非执行硬隔离：contract_layer_code_complete
W3.3 GameProjectState 存储与版本迁移：ready
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁�?
- ArtifactRegistry 的版本索引与 stale 传播（W3.4）�?- AgentTaskGraph 的依赖、失败和重试状态机（W3.5）�?- 运行中的三职�?Agent 和任�?Snapshot 输入（Red 禁止）�?- ActionProposal 构造器�?`assert_executable()` 的二次强制调用（Green-only W5）�?- 所�?Runtime、Engine 与多人效果仍以最�?F5 GateReport 为准，本轮契约代码不改变 Gate 颜色�?
## 35. W3.3 GameProjectState 存储与版本迁�?
在强类型契约稳定后，本轮建立独立项目事实存储。该状态层只维护三职能协作的项目版本、任务图引用、场景计�?世界版本�?Artifact 引用；它不复�?Runtime `StatePatch`，也不读取或修改 RuntimeState�?
当前改动�?
- 新增线程安全 `ProjectStateStore`，以不可�?`GameProjectState` 作为当前项目事实�?- 新增不可�?`ProjectStatePatch`；每�?Patch 必须携带 `patch_id/project_id/expected_project_version/source/changes`�?- 采用 compare-and-swap：期望版本与当前版本不一致时明确抛出 `ProjectVersionConflictError`，不静默覆盖其他 Agent 更新�?- `patch_id` 重放返回原结果且不重复增加版�?历史；相�?ID 携带不同内容时抛�?`ProjectPatchConflictError`�?- `scene_world_version` 只能单调递增，回退版本明确拒绝�?- `project_id/room_id/project_version` 等身份字段不能由 Patch 修改；只允许更新计划中列出的五个项目字段�?- 无实际变化的 Patch 不虚构新 project version 或迁移记录�?- 每个真实迁移记录 source、from/to version、changed fields 和不可变 before/after，用于后�?ArtifactRegistry 审计�?- Store �?contracts 独立导入时均不会加载 AgentRuntime/LANChat 模块�?
聚焦自动验证�?
```text
创建项目 + 显式 source 更新 -> project_version 1 -> 2
stale expected version -> 冲突且状�?历史零变�?相同 patch 重放 -> 幂等；同 ID 异内�?-> 拒绝
scene_world_version 回退 -> 拒绝
no-op patch -> 不增加版�?两个并发写者使用同一 expected version -> 仅一个成�?多项目状态隔�?+ 身份字段不可修改
协作契约�?ProjectState 聚焦测试 15 项通过
Python syntax compile、导入隔离与 git diff --check 通过
```

当前任务状态：

```text
W3.3 GameProjectState 存储与版本迁移：code_complete
W3.4 ArtifactRegistry 与失效传播：ready
W3.5 AgentTaskGraph：等�?W3.4
当前 Gate：red / pending_reevaluation
```

以下仍未实现�?
- ProjectState 的跨进程持久化和多人广播；第一阶段只提供协作层内存事实接口�?- ArtifactRegistry 注册/查询、版本索引和 stale 传播�?- 真实 Snapshot、RuntimeState、LANChat 或三职能生产 Agent 接入�?- 本轮不改变轨�?A Gate，所�?Engine/Sync 效果仍为 **[�?F5/实机验证]**�?
## 36. W3.4 ArtifactRegistry 与失效传�?
�?Gate 仍为 Red、等待下一�?F5 重新评估期间，完成独立轨�?B �?Artifact 版本事实层。本轮没有接�?RuntimeState、SceneWorldSnapshot、LANChat、ActionProposal �?Engine 写入路径�?
当前改动�?
- 新增 `services/agent_collaboration/artifact_registry.py`，以不可�?`ArtifactEnvelope` 为内容事实，以独�?`ArtifactRecord` 保存 `current/stale/superseded` 生命周期，避免修改已计算 hash �?Artifact�?- 引入显式 `artifact_id@version` 引用；依赖、项目当前引用和审计查询均绑定具体版本，旧版本不能冒充当前有效版本�?- 支持单项与批量原子注册；同一�?Agent 一次产出的多个 Artifact 可以共享同一�?`base_project_version`，批内依赖按拓扑顺序解析，ProjectState 只增加一次版本�?- 注册操作通过 `ProjectStatePatch` �?expected-version CAS 更新 `artifact_refs`；版本冲突、缺失依赖、非法跳版本或无�?Artifact 均不会写�?Registry �?ProjectState�?- 同一 Artifact ref 和相同内容可幂等重放；相�?ref 携带不同内容明确拒绝，避免静默覆盖审计事实�?- 上游新版本发布后，直接依赖旧版本的当�?Artifact 标记 `dependency_superseded`，更下游 Artifact 递归标记 `dependency_stale`；每�?stale reason 保留明确依赖 ref，直接替代版本与传递失效不混淆�?- 下游按新依赖发布新版本后，当前版本恢复可用；�?stale/superseded 版本仍可�?ref 查询和审计�?- ProjectState 在存在当�?stale Artifact 时写�?`validation_status=stale`；当前头部全部恢复后回到 `pending`，不�?ProjectGate 建立前伪称项目已通过验证�?
聚焦自动验证�?
```text
contracts + ProjectState + ArtifactRegistry�?3 tests passed
批量原子注册 + 批内拓扑依赖：passed
直接/传�?stale propagation：passed
旧版本审�?+ current usable guard：passed
幂等重放 + �?ref 异内容拒绝：passed
项目版本、Artifact 版本、依赖与 invalid guard：passed
轨道 B Runtime/LANChat import isolation：passed
Python syntax compile：passed
git diff --check：无 whitespace error（仅现有 CRLF 提示�?```

当前任务状态：

```text
W3.3 GameProjectState 存储与版本迁移：code_complete
W3.4 ArtifactRegistry 与失效传播：code_complete
W3.5 AgentTaskGraph：ready
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁�?
- AgentTaskGraph 的依赖、失败、重试、blocked �?output refs 状态机（W3.5）�?- ArtifactRegistry 的跨进程持久化和多人传播；W3 第一阶段只提供协作层内存事实接口�?- 运行中的三职�?Agent、真实或 Mock Snapshot 输入、Coordinator、ProjectGate �?ActionProposal�?- 本轮不改变轨�?A Gate；所�?Engine/Sync 效果仍为 **[�?F5/实机验证]**�?
## 41. W4.4 �?Artifact 红灯阶段综合闭环

�?PlanningAgent、ArtAgent �?ProgramAgent 的非执行型输出完成后，补�?Red Gate 下的单业务任务图综合闭环。该闭环只聚合项目契约事实，不接�?Runtime、Snapshot、LANChat 或场景写入�?
当前改动�?
- �?`contracts.py` 统一声明 Artifact 稳定 lineage，并明确 Red 阶段五类可产�?Artifact：`GameDesignBrief`、`LevelPlan`、`ArtDirection`、`SceneCompositionPlan`、`GameplayLogicPlan`�?- 三个职能 Agent 统一引用中心 lineage 映射，消除各模块重复字符串定义�?- 新增只读 `ProjectArtifactBundleReader`，从当前 `ProjectState + ArtifactRegistry + AgentTaskGraph` 构建不可执行的五 Artifact 项目方案包�?- 方案包校验当前任务图必须 completed、属于当前项目且仍是 active graph；每�?Artifact 必须是当前可用版本，并与 producer role、source task、项目引用和图输出一致�?- 方案包使用规范化 payload 计算确定�?SHA-256 content hash；相同项目事实重复读取产生相同结果，读取过程不修�?ProjectState、Registry �?TaskGraph�?- 单一业务 DAG �?`planning -> art -> program` 依赖顺序产出五类 Artifact；Program 只消费显式版本化策划输入�?ArtDirection�?- 策划 v2 发布后，旧美术与程序 Artifact 精确进入 stale；重新执行下游任务后形成完整 v2 方案包，旧版本进�?superseded�?- 美术任务失败时只重试失败节点；策划任务不重放，程序任务保�?blocked，待美术重试成功后继续�?- `EntityBindingPlan` 继续保持 schema-only，不进入 Red 阶段方案包；真实/Mock Snapshot、ProjectGate、ActionProposal �?Runtime 写入仍未解锁�?
聚焦自动验证�?
```text
�?Artifact 单业�?DAG 与确定性方案包：passed
planning -> art -> program 依赖解锁：passed
策划 v2 触发下游 stale 并重�?v2：passed
失败美术任务定点重试且不重放策划：passed
方案包读取零状态副作用：passed
五类 Artifact 均保�?non_executable：passed
EntityBindingPlan 未提前生产：passed
Runtime/LANChat/Snapshot/SceneTools/ActionProposal/ToolCallGraph 静态隔离：passed
Python syntax compile：passed
agent_collaboration 聚焦回归�?6 tests passed
```

当前任务状态：

```text
W4.1 PlanningAgent：code_complete
W4.2 ArtAgent：code_complete
W4.3 ProgramAgent：code_complete
W4.4 �?Artifact 红灯阶段综合闭环：code_complete
EntityBindingPlan：schema_only / Green �?W5.2 解锁
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁�?
- 三个 Reasoner 的生产模型适配�?CollaborationCoordinator 生产入口�?- 真实/Mock Snapshot 输入、EntityBindingPlan、ProjectGate、ActionProposal �?Runtime 写入�?- 轨道 A 新一�?F5 Gate 复评；所�?Engine/Sync 效果仍为 **[�?F5/实机验证]**�?
## 37. W3.5 AgentTaskGraph 业务任务状态机

�?W3.4 的版本化 ArtifactRegistry 基础上，完成独立�?ToolCallGraph �?AgentRuntime 的跨职能业务任务图。本轮只管理“哪个职能在什么依赖满足后产出哪类 Artifact”，不执�?Provider、Engine 或场景写入�?
当前改动�?
- 新增 `services/agent_collaboration/task_graph.py`，定义不可变 `AgentTaskGraph`、`AgentTaskRecord`、`TaskBlockReason` �?`TaskGraphTransition`�?- `AgentTask` 增加显式 `max_attempts`；Record 的权威状态会同步到嵌�?Task，避免序列化后同时出�?`pending` �?`in_progress` 两个事实�?- 建图时验�?task_id 唯一、depends_on 完整、输�?Artifact ref 显式带版本、依赖图无环；图定义�?project identity 共同参与幂等/冲突判断�?- 项目同一时刻只允许一个非 terminal active task graph；创建成功后通过 ProjectState CAS 写入 `active_task_graph_id`�?- 上游任务未完成时，下游保�?`pending`；上游完成且输入 Artifact 当前可用时才进入 `ready`�?- 上游失败/blocked、输入缺失或 stale 时，下游进入 `blocked` 并保留结构化原因，不会凭任务文本猜测继续执行�?- 单个任务支持 `ready -> in_progress -> completed/failed -> retry`；失败只重开责任任务，已完成上游不重跑，重试预算耗尽后明确拒绝�?- 任务完成前必须核�?output ref 存在、当前可用、`source_task_id` 匹配责任任务且覆盖声明的 output types；不能用其他 Agent �?Artifact 冒充本任务结果�?- Artifact 更新�?`refresh()` 精确阻断依赖旧版本的已完成任务及其下游；`rebind_inputs()` 显式绑定新版本并清空旧输出后才重�?ready�?- 两个并发执行者竞争同一 ready task 时只有一个能进入 `in_progress`；状态迁移均�?graph version �?transition history�?- 模块不导�?ToolCallGraph、RuntimeState、SceneWorldSnapshot、LANChat �?Engine 接口�?
聚焦自动验证�?
```text
contracts + ProjectState + ArtifactRegistry + AgentTaskGraph�?4 tests passed
三职能依赖顺序与完整 completed 闭环：passed
任务级失�?重试与预算耗尽：passed
stale input 精确阻断 + 版本 rebind：passed
output source/type/current version 门禁：passed
循环/未知依赖/跨项�?graph ID 冲突：passed
并发 ready task 原子认领：passed
迁移历史�?no-op refresh：passed
轨道 B Runtime/LANChat import isolation：passed
Python syntax compile：passed
```

当前任务状态：

```text
W3.1-W3.6 三职能强类型契约底座：code_complete
W4.1 策划 Agent 非执行型 Artifact 输出：ready
W4.2/W4.3 美术与程�?Agent：等�?W4.1
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁�?
- W4 三职�?Agent 的结构化 Artifact 生产与纯契约协作闭环�?- 运行中的 Agent 不得读取真实�?Mock Snapshot；Red 状态下 W4.1 只能消费 ProjectState 和有�?Artifact�?- Coordinator、ProjectGate、ActionProposal、EntityBindingPlan 真实绑定�?Runtime 写入仍由 Green Gate 阻断�?- TaskGraph/Registry 的跨进程持久化与多人传播不属�?W3 第一阶段�?- 本轮不改变轨�?A Gate；所�?Engine/Sync 效果仍为 **[�?F5/实机验证]**�?
## 38. W4.1 PlanningAgent 非执行型策划 Artifact 输出

�?W3 强类型契约、Registry �?TaskGraph 完成后，实现第一个职�?Agent。该 Agent 通过可注�?`PlanningReasoner` 获取推理结果，但自身只处理项目级强类型输入和 Artifact，不注册 LANChat，不读取聊天流水、RuntimeState、Engine 或任何真�?Mock Snapshot�?
当前改动�?
- 新增 `services/agent_collaboration/agents/planning_agent.py` 和独�?agents 导出入口�?- 定义 `PlanningRequest`、`PlanningContext`、`PlanningArtifactContext`、`PlanningAgentDraft`、`PlanningAgentResult` �?`PlanningReasoner` Protocol�?- PlanningRequest 只包含明确项目目标、约束、验收条件、project/graph/task identity 和请求来源，不接受聊天历史或场景对象�?- PlanningContext 只包�?ProjectState 的项目版本和当前有效 planning Artifact；不携带 `scene_world_version`，避�?Red 状态下策划契约间接绑定 Runtime 世界事实�?- PlanningAgent 要求责任任务属于 planning 且声�?`GameDesignBrief + LevelPlan` 两种输出；任务非 ready 时拒绝推理�?- Reasoner 必须返回强类�?`PlanningAgentDraft`；输出再经过现有 Artifact schema Validator，不能用一�?prompt 文本冒充契约�?- 输出使用稳定 lineage `planning.game-design-brief` �?`planning.level-plan`，自动计算下一版本；LevelPlan 显式依赖同批 GameDesignBrief�?- 两种 Artifact 通过 ArtifactRegistry 原子注册并由 AgentTaskGraph 校验 source_task、类型和当前可用性后，策划任务才进入 completed�?- 推理期间 ProjectState 版本变化会抛�?`PlanningContextStaleError`，任务记录失败且不登记过期输出�?- �?project/request ID 的完全相同请求幂等返回；相同 ID 携带不同内容明确拒绝�?- 当前 planning Artifact 若来�?`mock` �?`runtime` snapshot source，Agent 在调�?Reasoner 前以 `PlanningIsolationError` 拒绝，避免测�?fixture 或世界绑�?Artifact 被静默洗入策划链�?- 策划版本更新后，Registry 会使依赖�?LevelPlan 的美�?Artifact 精确 stale，为 W4.2 返工提供事实依据�?- 本轮 reasoner 通过依赖注入测试，没有注册生�?LLM/LANChat 入口，也没有 ActionProposal �?Runtime 写入能力�?
聚焦自动验证�?
```text
contracts + ProjectState + ArtifactRegistry + TaskGraph + PlanningAgent�?2 tests passed
GameDesignBrief + LevelPlan 原子产出�?TaskGraph completed：passed
schema invalid / reasoner 非结构化输出失败：passed
项目版本并发变化拒绝过期输出：passed
Mock/Runtime source �?Reasoner 前隔离：passed
请求幂等与同 ID 异内容冲突：passed
策划 v2 触发下游美术 Artifact stale：passed
非执�?Artifact assert_executable 拒绝：passed
Runtime/LANChat/Snapshot 静态与 import isolation：passed
Python syntax compile：passed
```

当前任务状态：

```text
W3.1-W3.6 三职能强类型契约底座：code_complete
W4.1 PlanningAgent：code_complete（可注入 reasoner，无生产入口�?W4.2 ArtAgent：ready
W4.3 ProgramAgent 非执行输出：ready
W4.4 Artifact 综合闭环：等�?W4.2/W4.3
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁�?
- W4.2 ArtAgent �?`ArtDirection + SceneCompositionPlan` 强类型输出�?- W4.3 ProgramAgent �?`GameplayLogicPlan` 非脚本输出�?- W4.4 �?Artifact 端到端任务图、版本返工和综合验收�?- PlanningReasoner 的生产模型适配�?CollaborationCoordinator 入口；Red 状态下继续不注�?LANChat�?- 真实/Mock Snapshot 输入、EntityBindingPlan、ProjectGate、ActionProposal �?Runtime 写入仍由 Gate 阻断�?- 本轮不改变轨�?A Gate；所�?Engine/Sync 效果仍为 **[�?F5/实机验证]**�?
## 39. W4.2 ArtAgent 非执行型美术 Artifact 输出

�?W4.1 策划 Artifact 闭环基础上，实现第二个职�?Agent。该 Agent 只消费任务显式绑定的当前有效 `GameDesignBrief@version + LevelPlan@version`，通过可注�?`ArtReasoner` 形成强类型美术契约，不读�?RuntimeState、Engine、聊天历史或任何真实/Mock Snapshot�?
当前改动�?
- 新增 `services/agent_collaboration/agents/art_agent.py`，并从独�?agents 包导出�?- 定义 `ArtRequest`、`ArtContext`、`ArtInputArtifactContext`、`ArtAgentDraft`、`ArtAgentResult` �?`ArtReasoner` Protocol�?- ArtRequest 只包�?project/graph/task identity、明确美术目标、约束、验收条件和请求来源，不接受聊天流水或场景对象�?- ArtAgent 要求责任任务属于 `art` 且精确声�?`ArtDirection + SceneCompositionPlan` 两种输出�?- 输入必须显式包含且仅包含一个当前有效、由 planning 角色产生�?GameDesignBrief �?LevelPlan；缺失、重复、非当前或其他类型在 Reasoner 前拒绝�?- Red Gate 下，任何 `snapshot_source=mock/runtime` 的策划输入均�?`ArtIsolationError` 拒绝；输入同时必须保�?`non_executable=true`�?- Reasoner 必须返回强类�?`ArtAgentDraft`；风格、调色板、灯光、避用项、场景类型、环境需求、实体需求和布局规则继续经过 Artifact schema Validator�?- 输出使用稳定 lineage `art.direction` �?`art.scene-composition` 并自动计算下一版本�?- ArtDirection 显式依赖两个策划版本；SceneCompositionPlan 同时依赖两个策划版本和同�?ArtDirection，二者通过 ArtifactRegistry 原子注册�?- AgentTaskGraph �?source_task、声明类型和当前可用性检查通过后才将美术任务置�?completed�?- 推理期间 ProjectState 版本变化会抛�?`ArtContextStaleError`，任务记录失败且不登记过期产物�?- �?project/request ID 的相同请求幂等返回；相同 ID 携带不同内容明确拒绝�?- 策划 v2 发布后，依赖 v1 �?ArtDirection/SceneCompositionPlan 精确 stale；重新绑�?v2 后可发布美术 Artifact v2�?- 本轮 reasoner 仅依赖注入测试，没有注册生产 LLM/LANChat 入口，也没有 Provider、SceneTools、ActionProposal �?Runtime 写入能力�?
聚焦自动验证�?
```text
ArtAgent 专项�?3 tests passed
contracts + ProjectState + ArtifactRegistry + TaskGraph + PlanningAgent + ArtAgent�?5 tests passed
GameDesignBrief/LevelPlan -> ArtDirection/SceneCompositionPlan �?Agent 闭环：passed
缺失/stale/重复/非策划输入在 Reasoner 前拒绝：passed
schema invalid / reasoner 非结构化输出失败且零 Artifact 发布：passed
项目版本并发变化拒绝过期输出：passed
Mock/Runtime source �?Reasoner 前隔离：passed
请求幂等与同 ID 异内容冲突：passed
策划 v2 精确 stale 美术 v1，并允许美术 v2 重建：passed
非执�?Artifact assert_executable 拒绝：passed
Runtime/LANChat/Snapshot/SceneTools/ActionProposal 静态隔离：passed
Python syntax compile：passed
```

当前任务状态：

```text
W3.1-W3.6 三职能强类型契约底座：code_complete
W4.1 PlanningAgent：code_complete（可注入 reasoner，无生产入口�?W4.2 ArtAgent：code_complete（可注入 reasoner，无生产入口�?W4.3 ProgramAgent 非执行输出：ready
W4.4 Artifact 综合闭环：等�?W4.3
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁�?
- W4.3 ProgramAgent �?`GameplayLogicPlan` 非脚本输出�?- W4.4 �?Artifact 端到端任务图、版本返工和综合验收�?- PlanningReasoner/ArtReasoner 的生产模型适配�?CollaborationCoordinator 入口；Red 状态下继续不注�?LANChat�?- 真实/Mock Snapshot 输入、EntityBindingPlan、ProjectGate、ActionProposal �?Runtime 写入仍由 Gate 阻断�?- 本轮不改变轨�?A Gate；所�?Engine/Sync 效果仍为 **[�?F5/实机验证]**�?
## 40. W4.3 ProgramAgent 非执行型 GameplayLogicPlan 输出

�?W4.1/W4.2 强类型策划与美术契约基础上，实现第三个职�?Agent。该 Agent 是规则设计器而非代码执行器，只消费任务显式绑定的当前有效 Artifact，并产出非执�?`GameplayLogicPlan`；不读取 RuntimeState、Engine、聊天历史或任何真实/Mock Snapshot�?
当前改动�?
- 新增 `services/agent_collaboration/agents/program_agent.py`，并从独�?agents 包导出�?- 定义 `ProgramRequest`、`ProgramContext`、`ProgramInputArtifactContext`、`ProgramAgentDraft`、`ProgramAgentResult` �?`ProgramReasoner` Protocol�?- ProgramRequest 只包�?project/graph/task identity、明确逻辑目标、约束、验收条件和请求来源，不接受脚本、聊天流水或场景对象�?- ProgramAgent 要求责任任务属于 `program` 且只声明 `GameplayLogicPlan` 输出�?- 必需输入为当前有效且�?planning 角色产生�?GameDesignBrief �?LevelPlan；可选输入仅允许当前有效且由 art 角色产生�?ArtDirection�?- SceneCompositionPlan、重复类型、错�?producer、缺失或 stale Artifact �?Reasoner 前拒绝�?- Red Gate 下，任何 `snapshot_source=mock/runtime` 输入均以 `ProgramIsolationError` 拒绝；输入必须保�?`non_executable=true`�?- Program 任务能力集只允许 `artifact.read/artifact.write` 且必须声�?`artifact.write`；shell、Engine、脚本执行或 Actor 修改能力�?Reasoner 前拒绝�?- Reasoner 必须返回强类�?`ProgramAgentDraft`；states、triggers、rules、win_conditions �?lose_conditions 继续经过 Artifact schema Validator�?- 输出使用稳定 lineage `program.gameplay-logic-plan` 并自动计算下一版本；依赖精确记录所有显式输入版本�?- ArtifactRegistry 登记成功�?AgentTaskGraph 校验 source_task、声明类型和当前可用性后，程序任务才进入 completed�?- 推理期间 ProjectState 版本变化会抛�?`ProgramContextStaleError`，任务记录失败且不登记过期产物�?- �?project/request ID 的相同请求幂等返回；相同 ID 携带不同内容明确拒绝�?- 策划版本更新会精�?stale GameplayLogicPlan；当程序逻辑显式引用 ArtDirection 时，美术版本更新同样精确触发 stale，并可重�?v2�?- 本轮 reasoner 仅依赖注入测试，没有注册生产 LLM/LANChat 入口，也没有 EntityBindingPlan、ScriptBundle、ActionProposal �?Runtime 写入能力�?
聚焦自动验证�?
```text
ProgramAgent 专项�?7 tests passed
contracts + ProjectState + ArtifactRegistry + TaskGraph + 三职�?Agents�?2 tests passed
GameDesignBrief/LevelPlan -> GameplayLogicPlan：passed
可�?ArtDirection 显式依赖：passed
缺失/stale/错误类型/错误 producer 输入�?Reasoner 前拒绝：passed
禁止 capability 和缺�?artifact.write：passed
schema invalid / reasoner 非结构化输出失败且零 Artifact 发布：passed
项目版本并发变化拒绝过期输出：passed
Mock/Runtime source �?Reasoner 前隔离：passed
请求幂等与同 ID 异内容冲突：passed
策划/美术版本更新精确 stale 程序产物并允�?v2 重建：passed
非执�?Artifact assert_executable 拒绝：passed
Runtime/LANChat/Snapshot/SceneTools/ActionProposal/EntityBinding 静态隔离：passed
Python syntax compile：passed
```

当前任务状态：

```text
W3.1-W3.6 三职能强类型契约底座：code_complete
W4.1 PlanningAgent：code_complete（可注入 reasoner，无生产入口�?W4.2 ArtAgent：code_complete（可注入 reasoner，无生产入口�?W4.3 ProgramAgent：code_complete（可注入 reasoner，无生产入口�?W4.4 �?Artifact 红灯阶段综合闭环：ready
EntityBindingPlan：schema_only / Green �?W5.2 解锁
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁�?
- W4.4 �?Artifact 端到端业务任务图、版本返工和综合验收�?- 三个 Reasoner 的生产模型适配�?CollaborationCoordinator 入口；Red 状态下继续不注�?LANChat�?- 真实/Mock Snapshot 输入、EntityBindingPlan、ProjectGate、ActionProposal �?Runtime 写入仍由 Gate 阻断�?- 本轮不改变轨�?A Gate；所�?Engine/Sync 效果仍为 **[�?F5/实机验证]**�?
## 42. W1.3 Late-ready Actor 选择�?Grounding Reconcile

�?F5 �?`3/14 Game-ready` 证据中，部分普�?Actor 已被 Engine 接受，但真实 AABB 晚于首次导入结果到达。现�?late-ready reconcile 会补�?`bounds_ready / bounds_source=engine_actual`，却保留导入早期�?`grounding_status=needs_review`，导致已经实际贴地的地面实体仍无法进�?Game-ready�?
本轮改动�?
- �?`_reconcile_partial_engine_readiness()` 完成原生 Scene Snapshot 后，仅检查本轮待 reconcile 批次中的 Actor�?- 仅当 `support_type=floor_supported`、AABB �?`engine_actual`、`bounds_ready=true` �?AABB 底面与地面高度误差不超过 `0.05m` 时，�?grounding 事实提升�?`grounded`�?- 墙挂、吊挂、系统对象、未知支撑类型和真实浮空对象保持原状态，不移�?Actor，不伪造接地�?- Grounding 更新通过 `runtime.engine_readiness.reconcile -> ToolResult -> StatePatch -> RuntimeState` 写回；该工具显式声明 `actors` 写集合，继续�?RuntimeGuard 约束�?- OperationLog 增加 `grounding_reconciled_count`，用于下一�?F5 对账�?
聚焦自动验证�?
```text
Late-ready floor-supported Actor -> grounded -> Game-ready：passed
wall_mounted / 实际浮空 Actor 不被误判 grounded：passed
跨历史批�?native actor_id / AABB reconcile：passed
Game-ready + R3 Readiness 聚焦套件�?3 tests passed
Python syntax compile：passed
```

当前 Gate�?
```text
red / pending_reevaluation
旧基准：3/14 Game-ready
代码断点：late actual AABB �?grounding 不更新，已修�?实机效果：待新一轮儿童卧�?F5 重新运行 runtime.r3_readiness.evaluate
```

本轮不能证明已经达到 `8/14`。下一步固定使用儿童卧室场景重�?F5，核�?`grounding_reconciled_count`、逐实�?`readiness_missing_fields`、Registry、Snapshot �?R3GateReport；所�?Engine 效果仍为 **[�?F5/实机验证]**�?
## 43. W1.4 Finalizer 同版本终态证据闭�?
现有 Finalizer 已产�?Registry、Consistency Audit、Snapshot �?Report 事件，但 R3 Gate 原先只检查事件名称是否在同一计划历史中出现以及最后位置是否有序，没有验证这些事件属于同一�?`scene_version`。这允许�?Registry、新 Snapshot 和另一版本 Report 被错误拼接成绿色证据�?
本轮改动�?
- Finalizer �?`finalizer_started`、`tool_graph_queue_empty` �?`scene_plan_finalized` 统一写入当前 `scene_version`�?- `report_ready/report_pending` 的用户可�?RuntimeEvent 同步携带最�?`SceneWorldSnapshot.scene_version`�?- Registry、Consistency Audit �?Snapshot 原有版本事实保留，七个终态节点现在可以按同一版本对账�?- `runtime.r3_readiness.evaluate` �?`finalizer_completeness` 不再跨版本拼事件，而是以最�?versioned `report_ready` 为目标，查找同版本的完整有序链：

```text
finalizer_started
-> tool_graph_queue_empty
-> scene_plan_finalized
-> scene_entity_registry_ready
-> runtime_scene_world_consistency_audited
-> scene_world_snapshot_ready
-> report_ready
```

- 缺少版本证据返回 `finalizer_scene_version_missing`；事件存在但版本不同返回 `finalizer_scene_version_mismatch`；同版本但顺序错误返�?`finalizer_event_order_invalid`�?- �?F5 证据不会因事件名称齐全而自动变绿，必须由新代码重新实机产生同版本闭环�?
聚焦自动验证�?
```text
R3 Finalizer 混合 scene_version 拒绝：passed
Registry -> Snapshot -> Report 同版本有序闭环：passed
�?scene_version 终态事件幂等：passed
final report 写入失败后下一 drain 重试：passed
report_pending 不冒�?terminal report：passed
Finalizer/R3 专项�?2 tests passed
Game-ready + R3 Readiness 套件�?4 tests passed
Python syntax compile：passed
```

当前 Gate�?
```text
red / pending_reevaluation
finalizer_completeness 代码约束：已收口
�?F5 终态版本证据：不足，保�?red
�?F5 同版本终态链：待实机验证
```

下一步按优先级进�?`business_graph_consistency`，检查一个业�?Batch 是否严格对应一�?terminal `business_batch` ToolGraph；所�?Engine/Sync/终态实机效果仍�?**[�?F5/实机验证]**�?
## 44. W1.5 Business Batch �?Principal ToolGraph 一对一收口

�?F5 曾出现少量业务批次对应大�?ToolCallGraph 的矛盾统计。代码核查确认，`enqueue_planned_batches()` 原先采用整组判断：只有全部未完成批次都已�?`queued/running` 图时才整体复用；只要一个批次缺图，就会为全部未完成批次重新创建业务图。这会重复提交仍在执行的批次，也会把已完成业务图、但仍等�?Engine late-ready �?`partial` 批次重新跑一遍资源链路�?
本轮改动�?
- `BatchPlan.tool_graph_id` 现在被视为该批次稳定�?principal business graph 身份�?- `enqueue_planned_batches()` 改为逐批解析：已有合�?principal graph 的批次一律复用，仅为没有主图的待执行批次创建新图�?- `partial BatchPlan + completed business graph` 被识别为 Engine readiness 收尾状态，不重新执行图片、模型、导入链路�?- 显式失败重试继续复用现有 `graph_id`，由既有 `retry_generation` 增加 `generation`，OperationLog 保留尝试历史�?- 主图事实缺失、plan/batch/role 身份不一致、active graph �?queue fact �?graph/queue 状态冲突时明确失败并记录诊断事件，不再静默生成第二张业务图�?- 混合状态下记录 `planned_batches_enqueue_partial_reuse`，可对账复用图数和新建图数�?- 返回结果�?BatchPlan 顺序列出每个批次�?principal graph，避免只返回新建图造成调用方统计失真�?
聚焦自动验证�?
```text
混合“已有主�?+ 缺图”仅补一�?principal graph：passed
partial batch + completed graph 不重跑资源链路：passed
悬空 principal graph 引用明确失败且不创建第二图：passed
原子入队、介入吸收回滚与失败重试 generation：passed
业务图域报告�?R3 Gate 回归�?4 tests passed
Game-ready + R3 Readiness 套件�?4 tests passed
Python syntax compile：passed
```

当前 Gate�?
```text
red / pending_reevaluation
business_graph_consistency 代码约束：已收口
�?F5 �?5 �?151 图证据：不满足，保持 red
�?F5 �?BatchPlan/principal graph 一对一事实：待实机验证
```

下一步按优先级进�?`snapshot_integrity`，核实同一 `plan_id + scene_version` �?Snapshot 是否不可变、Fingerprint 是否稳定，以�?Registry/Snapshot/Report 是否引用同一版本；所�?Engine/Sync 实机效果仍为 **[�?F5/实机验证]**�?
## 45. W1.6 SceneWorldSnapshot 同版本不可变收口

代码核查确认，终�?`SceneWorldSnapshot` 过去只嵌�?Report 中，没有独立的版本化事实集合；查询接口会把任意终�?Report 中的同版�?Snapshot 标为 immutable，却没有校验 Fingerprint，也无法阻止同一 `plan_id + scene_version` 被后续不同内容覆盖。原世界指纹只覆�?Engine 可观测的身份、Transform �?AABB，未覆盖下游 Agent 实际消费的语义、接地、交互、玩法和同步事实�?
本轮改动�?
- RuntimeState 新增 `scene_world_snapshots`，以 `plan_id@v<scene_version>` 保存终态不可变 Snapshot�?- 终�?Report �?Snapshot 原子写入；相同内容幂等复用，不同内容返回 `scene_world_snapshot_version_conflict`，禁止覆盖�?- `SceneWorldSnapshotRecordValidator` 校验计划、版本、authority、实�?ID 唯一性、Readiness 摘要�?SHA-256 Fingerprint�?- Registry 增加 `scene_version`，Report 持久化时强制 Registry、Snapshot、Consistency Audit �?PlanSummary 使用同一版本�?- `scene_world_fingerprint()` 扩展为下�?Agent 世界契约指纹；另�?`scene_materialization_fingerprint()` 专门用于 Runtime �?Engine 可观测事实对账，避免混淆两种职责�?- Snapshot �?Report 使用深拷贝；调用方修改返回对象不能反向污�?RuntimeState�?- 查询优先读取专用冻结 Snapshot；旧 Report �?Snapshot 仅标记为 `legacy_report`，校验失败时返回明确 integrity failure，不再冒�?immutable�?- Finalizer �?Registry、Snapshot �?Report 事件补充同版�?`world_fingerprint`，便�?F5 对账�?
聚焦自动验证�?
```text
Fingerprint 顺序稳定且覆�?Agent 语义契约：passed
同版本终�?Snapshot 幂等复用与深拷贝隔离：passed
同版本不同内容覆盖拒绝：passed
�?Report Snapshot 降级�?legacy_report：passed
Game-ready + R3 Readiness 套件�?7 tests passed
Finalizer/Report 持久化关键回归：passed
Python syntax compile：passed
```

当前 Gate�?
```text
red / pending_reevaluation
snapshot_integrity 代码约束：已收口
�?F5 Snapshot 证据：不满足新不可变契约，保�?red
�?F5 Registry/Snapshot/Report/Fingerprint 同版本事实：待实机验�?```

下一步按轨道 A 优先级进�?`environment_readiness`，核实室�?`room_box/room_floor`、室�?terrain 和混�?transition zone 是否以真�?Engine-ready 环境实体进入 Registry �?Snapshot；所�?Engine/Sync 实机效果仍为 **[�?F5/实机验证]**�?
## 46. W1.7 Environment Readiness 契约与稳定身份收�?
代码核查确认，Environment 链路存在三个会直接阻�?R3 Gate 的事实断点：配置了外部环�?fact provider 后，Runtime 会完全采用其返回值，导致 SceneDesignContract 要求�?`room_box/room_floor/terrain/transition_zone` 可能被吞掉；Registry 先根�?`requires_engine_write=False` 把环境实体标�?`not_applicable`，覆盖了 floor、terrain、room shell 的真实支撑语义；环境 Actor GUID 依赖当前业务 `batch_id`，provider 重建或跨批次补录时可能产生新身份�?
本轮改动�?
- `runtime.environment.create_components` 在外�?provider 成功后仍统一应用 SceneDesignContract �?framework fallback；室内稳定补�?`room_box + room_floor`，室外补�?terrain，混合场景补�?terrain、room shell、floor �?transition zone�?- 显式 substrate 请求仍保持严格失败语义：外部 provider 未解析任何请求项时继续失败，不用默认组件掩盖真实 provider 断点�?- Registry 的环境支撑语义改�?component type 优先：`room_floor/terrain/ground/transition_zone -> grounded`，`room_box/room_shell -> enclosure`；只有其他无几何写入需求的环境事实才使�?`not_applicable`�?- 环境 Actor GUID 改为 plan-level 稳定身份，不再纳入业务批次；`source_batch_id` 仍记录本次物化来源，便于 OperationLog 对账�?- provider 内缓存继续避免同一进程重复导入；即�?provider 重建导致缓存丢失，同一 `plan_id + component_id + asset_id` 仍解析到相同 `actor_guid/entity_id`�?
聚焦自动验证�?
```text
外部 provider 不得吞掉 indoor/mixed 必需 framework components：passed
环境导入缺失/部分失败阻断普�?Actor：passed
floor/room shell/transition zone 支撑语义�?Game-ready 判定：passed
provider 重建及跨业务批次环境身份稳定：passed
Environment 聚焦回归�? tests passed
Game-ready + R3 Readiness 套件�?7 tests passed
git diff --check：clean（仅既有 CRLF 提示�?```

当前 Gate�?
```text
red / pending_reevaluation
environment_readiness 代码约束：已收口
�?F5 环境实体证据：不足，保持 red
�?F5 的真�?room_box/room_floor/terrain/transition zone、Engine-ready �?Snapshot 事实：待实机验证
```

下一步进�?`multiplayer_consistency` 前，先按固定儿童卧室、森林营地和混合场景执行新一�?F5，核�?Environment Actor、RuntimeState、Registry、Snapshot �?Report 五方身份�?readiness；所�?Engine/Sync 实机效果仍为 **[�?F5/实机验证]**�?
## 47. W1.8 Multiplayer Snapshot Identity ACK 闭环

本轮推进 Gate 维度：`multiplayer_consistency`�?
此前同步状态只能证明“发生过同步事件”，不能证明房主端与成员端实际持有相同的实体身份和版本；同时，安全事件过滤会丢弃实体指纹、实体数量和漂移计数，使 R3 Gate 可能基于弱证据误判�?
本轮完成�?
- 房主 Snapshot 增加确定性实体身份指纹，输入仅包�?`entity_id / actor_id / asset_id / actor_version / source_plan_id / source_scene_version`�?- 成员应用 Snapshot 后发�?`peer_ack`，回传房�?成员指纹、预�?已应�?partial 数量、身份漂移和版本漂移计数�?- 成员在模型晚到并完成 Actor 创建后刷�?ACK；房主轮询期周期性重�?Snapshot，并�?hash 去重避免重复广播�?- C++ NetworkSystem �?`peer_ack` 转为 `scene_snapshot_peer_ack`，且不再�?ACK 放回前端 Snapshot 队列，避免形成应用循环�?- Runtime 同步事件白名单保留上述安全证据；R3 Gate 只接受明�?ACK �?peer mirror 证据，普�?`peer_connected/syncing` 事件不再被当作身份一致性证明�?- peer mirror Registry 与房�?Snapshot 使用同一 `scene_version`，避免镜像构建阶段制造假版本漂移�?
验证证据�?
```text
Python compile：passed
multiplayer / native sync / R3 readiness 聚焦测试�?0 tests passed
Game-ready + multiplayer + native sync + R3 readiness 扩展聚焦测试�?9 tests passed
RoomPanel <script setup> JavaScript 语法解析：passed
git diff --check：clean（仅既有 CRLF 提示�?Frontend ESLint：未执行，当前工作区未安�?@eslint/js
Native C++ build：未执行
F5 多人实机：未执行
```

当前 Gate�?
```text
red / pending_reevaluation
multiplayer_consistency 代码证据链：已补�?真实房主/成员 Snapshot ACK、实体落地后的指纹一致性、无重复 Actor/�?ACK 循环：待 F5 验证
```

所有真�?Engine、网络传输与多人一致性效果仍�?**[�?F5/实机验证]**。下一轮应先执行固定多�?F5，对账房�?成员�?`entity_id / asset_id / version / identity_fingerprint`，再根据�?GateReport 决定是否从红灯切换为黄灯或绿灯�?
## 48. R3 Gate 聊天室只读诊断入�?
代码核查确认，`runtime.r3_readiness.evaluate` 已经具备七维聚合、确定性输出和零副作用测试，但此前只存在于 AgentRuntime 内部接口与测试中。下一�?F5 若仍依赖人工拼接 RuntimeState、Registry、Snapshot 和日志，既容易漏项，也无法稳定复现红黄绿判定�?
本轮完成�?
- 新增窄口�?GM 查询：`@GM R3门禁`、`@GM R3 Gate`、`@GM R3 readiness`�?- 查询直接调用 `runtime.r3_readiness.evaluate`，不经过 LLM、Coordinator 写链、PlanPatch、ToolCallGraph �?Provider�?- 聊天室返回总体 Gate、scene version、Game-ready 数量以及七个维度的红黄绿状态�?- 阻塞项只展示前三项并给出剩余计数；能力解锁项读取 GateReport，不根据聊天历史猜测�?- 新增安全日志 `[R3GateTrace]`，仅记录 room/plan/version、维度状态、Game-ready 计数、阻塞数量和 report ID，不记录实体明细、Provider 或内�?URL�?- 普�?Agent 或不明确的“检查门禁”不会命中该入口，避免扩大控制词规则面�?
聚焦验证�?
```text
Python syntax compile：passed
GM R3 Gate 零副作用�?Coordinator 绕过：passed
AgentRuntime R3 Readiness 回归：passed
聚焦套件�? tests passed
Native C++ build：未执行
F5 实机 Gate 输出：未执行
```

当前 Gate�?
```text
red / pending_reevaluation
R3GateReport 聊天室证据入口：code_complete
�?F5 基线�?/14 Game-ready，不满足�?Gate 契约
新一轮儿童卧室、森林营地、混合场景和多人 F5：待执行
```

下一�?F5 在每个场�?Finalizer 后发�?`@GM R3门禁`，保存聊天室输出和对�?`[R3GateTrace]`；只有新代码产生�?GateReport 可以决定红灯是否升级。所有真�?Engine、多人同步和 Game-ready 效果仍为 **[�?F5/实机验证]**�?
## 49. W1.3 Completed Batch 接地事实补录

继续核查 `entity_readiness` 时确认，已有�?late-ready 修复只会选择 `partial` 批次，或仍缺�?`engine_actual` AABB �?`completed` 批次。如果一个批次已经完成、Actor 已持有真�?AABB，但导入早期留下�?`grounding_status=needs_review` 尚未更新，Finalizer 会因为“bounds 已齐”而跳过整个批次。这样实际底面已经与地面接触的普通地面物体仍无法进入 Game-ready�?
本轮改动�?
- `batch_needs_reconcile()` �?bounds 缺失外，也检查是否存在“可由真�?AABB 直接证明已贴地”的 floor-supported Actor�?- 仅当 `bounds_ready=true`、`bounds_source=engine_actual`、支撑类型为 `floor_supported`，且 AABB bottom 与地面误差不超过 `0.05m` 时重新纳�?reconcile�?- 仍通过 `runtime.scene.snapshot -> runtime.engine_readiness.reconcile -> ToolResult -> StatePatch -> RuntimeState` 写回，不直接修改 RuntimeState�?- 墙挂、吊挂、未知支撑类型和真实浮空对象不会因为本次修改被提升为 grounded�?- 已经具有合法 grounding 的实体不会重复进入该分支，避免无意义的持�?reconcile�?
聚焦验证�?
```text
completed batch + engine_actual AABB + 实际贴地 + needs_review -> grounded：passed
partial batch late-ready -> grounded -> Game-ready：passed
wall_mounted / 真实浮空 Actor 不被误判：passed
Game-ready + R3 Readiness 聚焦套件�?7 tests passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示�?F5 实机：未执行
```

当前 Gate�?
```text
red / pending_reevaluation
entity_readiness completed-batch grounding 断点：code_complete
�?F5 基线�?/14 Game-ready
�?F5 �?grounding_reconciled_count �?Game-ready 提升：待验证
```

本轮没有移动 Actor，也没有放宽 `engine_actual`、Engine verification、稳定资源身份或 sync 事实要求。下一轮儿童卧�?F5 仍需通过 `@GM R3门禁` 和逐实�?`readiness_missing_fields` 证明是否达到 `8/14`；所�?Engine 接地�?Game-ready 效果仍为 **[�?F5/实机验证]**�?
## 50. W1.4 Finalizer `report_ready` 同版本持久化闭环

继续核查 `finalizer_completeness` 时确认，终态报告会先写�?RuntimeState，再尝试写入 `report_ready` RuntimeEvent；Finalizer 过去只检查报告是否存在，即使事件 StatePatch 失败，也会设�?`latest_completed_plan_id` 并清�?`active_execution_plan_id`。此外，`RuntimeEventValidator` 的安全字段白名单会剥�?`scene_version`，导致正常写入的 `report_ready` 也无法成�?R3 Gate 所要求的同版本终态证据�?
本轮改动�?
- RuntimeEvent 安全 payload 明确保留数值型 `scene_version`，仍继续剔除 Provider、URL、路径、密钥和内部工具字段�?- Finalizer 在清理执行计划前，必须从 RuntimeState 找到当前 `plan_id + scene_version` �?`report_ready` 事件�?- 报告已存在但终态事件缺失时，基于已持久化报告重发最小终态事件，不重复执�?Engine 写入�?- 事件仍无法持久化时，计划恢复�?`executing`，保�?`active_execution_plan_id`，发�?`report_pending` 并等待下一次零 drain 重试�?- 恢复成功后记�?`scene_plan_report_ready_event_recovered`，随后才设置 latest completed 并清�?active execution�?
聚焦验证�?
```text
report 持久化失败后�?drain 重试：passed
report_ready StatePatch 持续失败时不清理 execution plan：passed
恢复后同版本 report_ready 写入并完�?Finalizer：passed
RuntimeEvent 安全过滤回归：passed
Finalizer 顺序 + R3 Readiness�? tests passed
Finalizer/RuntimeEvent 聚焦回归�? tests passed
Python syntax compile：passed
F5 实机：未执行
```

当前 Gate�?
```text
red / pending_reevaluation
finalizer_completeness 同版本事件闭环：code_complete
�?F5 终态事件缺少新 scene_version 证据，不可用于升�?Gate
�?F5 �?finalizer_started -> report_ready 同版本序列：待验�?```

下一轮按轨道 A 优先级进�?`business_graph_consistency`，核对业�?Batch �?`business_batch` ToolGraph 的数量、归属、节点终态和查询零污染；所�?Engine、多人同步和真实 Finalizer 效果仍为 **[�?F5/实机验证]**�?
## 51. W1.5 R3 Gate 业务图角色、归属与节点终态收�?
复核既有 principal business graph 一对一闭环时确认，执行层已经能够拒绝悬�?principal graph 和错�?graph identity，但 `runtime.r3_readiness.evaluate` 的只读判定仍存在两处宽松口径：被 Batch 引用�?`internal_state/query_snapshot` 图也会被计入业务图；已经标记 terminal 的图不会检查节点是否仍停留�?`planned/ready/running`。这会让错误图角色、错误归属或未真正收尾的节点被误判为 `business_graph_consistency=green`�?
本轮改动�?
- `business_graph_consistency` 只把 `graph_role=business_batch` 的图计入业务图数量，query、review、finalizer �?internal 图不再污染业务统计�?- 每个 Batch �?`tool_graph_id` 必须解析到真实图，且图的 `plan_id / batch_id / graph_role` 必须�?Batch 一致�?- 独立�?orphan `business_batch` 图明确列�?contradiction，不通过减少审计事实来让数量看起来一致�?- terminal business graph 必须保留非空节点事实；节点必须处�?`succeeded / failed / blocked / skipped` 之一，`planned / ready / running` 会被判定�?active contradiction�?- GateReport 增加业务节点总数以及 succeeded、failed、blocked、skipped、active 状态计数，F5 不再需要人工从完整 ToolGraph 日志拼接节点状态�?- `blocked / incomplete` 图按执行器现有失败终态语义识别为 terminal；本轮不改变图执行器和失败策略�?
聚焦验证�?
```text
R3 Readiness Gate（含角色、归属、orphan、节点终态、query 零污染）�?1 tests passed
Game-ready / 报告图分域回归：29 tests passed
principal graph 缺图补建、partial 复用、悬空引用拒绝：passed
Python syntax compile：passed
F5 实机：未执行
```

当前 Gate�?
```text
red / pending_reevaluation
business_graph_consistency 严格事实判定：code_complete
�?F5 的业务图统计不满足新角色/节点终态证据口径，不可用于升级 Gate
�?F5 �?Batch/principal graph/terminal node 对账：待验证
```

下一步按轨道 A 顺序复核 `snapshot_integrity`，重点确认同一 `plan_id + scene_version` �?Registry、Snapshot、Consistency Audit �?Report 是否引用同一 Fingerprint；所有真�?Engine、多人同步和终态效果仍�?**[�?F5/实机验证]**�?
## 52. W1.6 Engine Snapshot 同计划同版本身份闭环

复核 `snapshot_integrity` 时确认，冻结�?`SceneWorldSnapshot` 已具备不可变记录和世�?Fingerprint，但 Engine 对账仍存在一个同版本漏洞：`latest_engine_snapshot()` 在目标版本不存在时允许回退�?`scene_version=0` �?legacy Engine Snapshot；随�?consistency audit 又使用世�?Snapshot �?`plan_id + scene_version` 替该�?Engine Snapshot 计算 materialization fingerprint。这样旧版或跨计�?Engine 事实�?Actor 内容恰好相同时，可能冒充当前版本的一致性证据�?
本轮改动�?
- consistency audit 独立读取并保留世界与 Engine 两侧各自�?`plan_id + scene_version`，不再使用世界版本替 Engine 版本计算 Fingerprint�?- Engine Snapshot 缺少 plan/version、plan 不一致或 scene version 不一致时，明确写�?`snapshot_identity_issues` 并返�?`needs_review`�?- audit 输出 `engine_plan_id / engine_scene_version / plan_id_matches / scene_version_matches`，供 Finalizer、报告和 R3 Gate 统一消费�?- `snapshot_integrity` 维度增加 Engine plan/version 匹配指标和明�?contradiction；Actor 内容完全相同也不能掩盖版本漂移�?- 保留 `latest_engine_snapshot()` �?legacy 读取能力用于旧状态诊断，�?legacy 事实不再具备证明当前版本一致性的资格�?- 本轮没有修改冻结 Snapshot 写入、Engine 查询、RuntimeState �?final report 主链�?
聚焦验证�?
```text
当前版本 Runtime/Engine Snapshot 一致：passed
scene_version=0 legacy Engine Snapshot 不得证明 v3 世界：passed
�?plan Engine Snapshot 不得证明当前世界：passed
R3 Gate 对跨版本 Engine Snapshot �?red：passed
Game-ready + Snapshot + R3 Readiness�?2 tests passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示�?F5 实机：未执行
```

当前 Gate�?
```text
red / pending_reevaluation
snapshot_integrity Engine plan/version 身份约束：code_complete
�?F5 �?legacy/缺版�?Engine Snapshot 证据不可用于升级 Gate
�?F5 �?Registry/Snapshot/Engine Audit/Report 同版�?Fingerprint：待验证
```

下一步按轨道 A 顺序复核 `environment_readiness`，重点确认必要环境实体的 stable entity identity、真�?Engine AABB、support semantics �?Snapshot 版本是否同时满足 Gate；所有真�?Engine、多人同步和环境渲染效果仍为 **[�?F5/实机验证]**�?
## 53. W1.7 Environment Readiness 硬事实重算与 Actor 身份收口

复核既有 Environment framework、稳�?GUID 和支撑语义修复后确认，生成与 Registry 链路已经能够表达 `room_box / room_floor / terrain / transition_zone`，但 R3 Gate �?Engine readiness reconcile 仍有两个可信性缺口：`environment_readiness` 只读�?Snapshot 中已经计算好�?`game_ready` 布尔值，没有独立核验必要环境实体�?Engine Actor 身份、真�?AABB �?component-specific support；Engine readiness polling �?`actor_id` 未命中时仍按显示名称匹配，可能把同名�?Actor 的几何事实写到当前环境实体�?
本轮改动�?
- `environment_readiness` 不再仅相�?`game_ready=True`，而是�?`SceneWorldSnapshot.environment_entities` 重新核验 `entity_id / actor_id / asset_id / model_ref / version / transform / world_aabb / bounds_source / Engine verification / support / sync`�?- 必要环境实体只有 `bounds_source=engine_actual`、`engine_write_verification_status=engine_verified` 且无 `readiness_missing_fields` 时才计入 ready�?- 支撑语义按组件类型独立检查：`room_box -> enclosure`，`room_floor / terrain / transition_zone -> grounded`，sky 类为 `not_applicable`�?- GateReport 增加逐环境实�?`component_diagnostics`，可直接定位 `room_floor:engine_actual_aabb`、`room_box:grounding_status` 等阻断项，不再人工拼�?Registry �?Snapshot�?- �?`room_shell / indoor_enclosure / walkable_floor / ground / transition` 做通用 canonical alias 归一，不为单一测试场景写特例�?- Engine readiness reconcile 删除名称匹配兜底，只接受稳定 `actor_id`；同名但 actor_id 不同的旧 Actor 不得让当前环境实体晋升为 Engine-ready�?
聚焦验证�?
```text
环境 game_ready 布尔值与 Engine AABB/support 事实冲突�?Gate �?red：passed
room_shell �?canonical alias 仍能匹配契约组件：passed
同名�?actor_id 不同�?Engine Actor 不得提供 readiness：passed
既有真实环境导入与支撑语义回归：passed
Game-ready + R3 Readiness + Environment adapter�?6 tests passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示�?F5 实机：未执行
```

当前 Gate�?
```text
red / pending_reevaluation
environment_readiness 硬事实与稳定 Actor 身份判定：code_complete
�?F5 �?3/14 Game-ready �?legacy 环境证据不可用于升级 Gate
�?F5 �?room_box/room_floor/terrain/transition_zone 真实 Engine Actor、AABB �?support：待验证
```

下一步进�?W2 固定场景 F5 Vertical Slice，先执行儿童卧室，使�?`runtime.r3_readiness.evaluate` 自动核对 Engine Actor、RuntimeState、OperationLog、Registry、Snapshot �?final report；若仍为 red，只�?GateReport 指向的首个真实环境或实体 readiness 断点。所有真�?Engine、多人同步与渲染效果仍为 **[�?F5/实机验证]**�?
## 54. W1.8 普通实�?Readiness 硬事实重�?
W2 F5 前置核查发现，Registry 已经会依�?Engine verification、真�?AABB、稳定资源身份、支撑和同步状态计�?`game_ready`，但 `runtime.r3_readiness.evaluate` �?`entity_readiness` 仍直接累计该布尔值。若 Registry 行出�?`game_ready=true` �?`bounds_source=estimated`、Engine 未验证、支撑未知或同步 partial 等公开字段相互矛盾，Gate 仍可能把该实体计入卧�?`8/14` 门槛，导致自动对账失去独立校验价值�?
本轮改动�?
- `entity_readiness` �?Registry 的公开、Engine-backed 字段重新核验 `entity_id / actor_id / asset_id / model_ref / version / entity_type / semantic_role / transform / world_aabb / bounds_source / Engine verification / grounding / sync`�?- Gate 不会自行把实体提升为 Game-ready；只�?Registry 已声�?ready 且重算无缺失时才计入核验数量�?- “声�?ready 但缺少硬事实”进�?`game_ready_without_hard_facts` contradiction，并在逐实体诊断中列出具体字段�?- �?ready 实体仍必须由 Registry 提供 `readiness_missing_fields`；Gate 重算结果不能�?Registry 掩盖缺失原因�?- GateReport 同时输出 `declared_game_ready_entity_count` 与核验后�?`game_ready_entity_count`；顶层聊天室摘要读取核验值，不再出现维度�?`7/14`、摘要仍显示 `8/14` 的双口径�?- `readiness_missing_field_counts` 改为由本次硬事实核验结果确定性计算，不再直接转抄 Registry 聚合值�?
聚焦验证�?
```text
Game-ready + R3 Readiness�?5 tests passed
GM R3 Gate 只读查询回归�? test passed
普通家�?game_ready=true + estimated AABB -> 不计�?Game-ready、Gate �?red：passed
声明计数 8、核验计�?7 的顶�?维度口径一致：passed
Python syntax compile：passed
F5 实机：未执行
```

F5 证据边界�?
```text
最新现有日志：2026-07-14_04-51-51_corona.log
本轮 Gate 修复提交时间�?026-07-14 08:24-08:47 之后
结论：现有日志早于当前代码，不得用于升级 Gate
verify_ultimate_plan.py：旧 phase1 长超时路径运行约 1 小时 50 分钟后终止，不作为通过证据
```

当前 Gate 保持�?
```text
red / pending_reevaluation
entity_readiness 硬事实独立核验：code_complete
旧基线：3/14 Game-ready
当前代码的儿童卧�?GateReport：待�?F5
```

下一步严格进�?W2.1 儿童卧室 F5。必须保存运行日志与代码 commit、room/plan/version、Engine Actor 摘要、OperationLog cursor、Registry、Snapshot fingerprint、final report �?`@GM R3门禁` 输出；若仍为 red，只处理 GateReport 指向的第一个实机事实断点。所有真�?Engine、渲染、接地和多人效果仍为 **[�?F5/实机验证]**�?
## 55. W2.1 儿童卧室 F5：Snapshot 终态版本断�?
有效 VSCode F5 日志�?
```text
build/examples/engine/RelWithDebInfo/logs/2026-07-14_13-28-28_corona.log
Runtime plan: plan-2bde99becad5
Scene version: 4
```

本轮实机证据�?
```text
业务批次�?/3 terminal
业务 ToolGraph�?/3 terminal
ToolCall�?4/54 succeeded�? failed
Runtime entities�?（environment 2 + actor 7�?核验 Game-ready�?/14（实际场�?6/9�?Engine bridge�?3/13 success�? failed
Environment readiness：green
Finalizer completeness：green
Business graph consistency：green
Runtime write safety：green
Entity readiness：yellow
Snapshot integrity：red
Overall Gate：red
```

结论：当前代码已把环境、执行图、Finalizer 与写权限边界跑通，Game-ready 从旧基线 `3/14` 提升�?`6/14`；但最�?Registry/SceneWorldSnapshot 仍可能与批次早期 Engine Snapshot 对账。原 Finalizer �?readiness reconcile 后直接选择已有快照，没有按终�?`plan_id + scene_version` 重新采集 Engine 事实，因此最�?v4 世界可能与旧批次快照发生 identity/fingerprint 冲突�?
本轮小修�?
- Finalizer 仅在计划进入 terminal 时，按显�?`plan_id + scene_version` 刷新一�?Engine Snapshot�?- 刷新发生�?Registry、SceneWorldSnapshot �?consistency audit 之前，不修改 Provider、C++ 导入或业�?ToolGraph�?- 执行仍处�?partial/96% 时不反复刷新，避免继续膨胀 internal graph�?- R3 trace 增加前三�?`blocker_codes`，下一�?F5 可直接定�?Snapshot、实体或多人维度的具体缺失事实�?- 增加 Finalizer 必须以终态计划身份刷新快照的回归断言�?
聚焦验证�?
```text
Game-ready tests�?0 passed
R3 Readiness tests�?5 passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示�?```

本次日志还暴露一个后续控制面断点：同一�?`@GM R3门禁` 先被 Native Queue 处理，随后又�?Agent Task 处理，产生两条回复和两个 report id；第二条路径末尾还出现一次零事实 RuntimeEvidence。该问题不影响本�?Snapshot 修复的代码边界，列入 W2.1 下一断点�?
当前 Gate�?
```text
red / snapshot_fix_pending_f5
四个基础维度已由本次 F5 证明�?green
entity_readiness：yellow�?/14
finalizer terminal-version Engine Snapshot refresh：code_complete
Snapshot fingerprint 一致性：待下一�?F5 验证
GM R3 查询双入口幂等：待修�?```

下一�?F5 优先复用同类卧室场景并执�?`@GM R3门禁`。必须核�?`blocker_codes`、Snapshot plan/version/fingerprint、Registry 计数和重复回复；Snapshot 转为 yellow/green 后，再处�?GM 查询双入口幂等与剩余 3 �?`grounding_status` 缺失。所有本�?Engine Snapshot 一致性改进仍标记 **[�?F5/实机验证]**�?
## 56. W2.1 GM R3 查询双入口原子收�?
`2026-07-14_13-28-28_corona.log` 同时记录了：

```text
Native Queue �?@GM R3门禁 执行一�?runtime.r3_readiness.evaluate 并回�?随后 Agent Trigger 对同一 message_id 再执行一次并回复
两次 R3GateReport 使用相同 plan/version/facts，但产生两条用户消息
第二条路径完成后还输出一次零事实 RuntimeEvidence
```

代码链复核确认：Native Queue �?structured GM route 会同步调�?`_process_trigger()`，但该分支此前没有先写入 `MessageDispatchLedger`；R3 Gate 查询又不属于已有的确认、拒绝、暂停协议，因而不会进�?`_gm_control_message_ids` 去重集合。Agent Trigger 随后看到消息未被认领，便完整执行第二次�?
本轮改动�?
- structured GM route 在调�?`_process_trigger()` 前，�?`room_id + message_id` 原子认领消息�?- Native Queue 为权�?owner，route 记录�?`gm_control`；处理成功后状态写�?`replied`�?- Agent Trigger 入口继续使用既有 Ledger 终态检查，命中同一消息时直接返回，不调�?Runtime、不回复第二次�?- 该收口覆�?R3 Gate、GM 总结和其�?structured GM 只读控制，不改变确定性确�?拒绝协议，也不扩大到普�?RoleAgent 消息�?
聚焦验证�?
```text
Game-ready/消息幂等�?1 tests passed
structured GM target 优先路由：passed
�?GM 确认双队列去重：passed
Python syntax compile：passed
```

当前结论�?
```text
GM R3 查询双入口幂等：code_complete
单次 Runtime evaluate + 单条权威回复：自动测试通过
Native Queue / Agent Trigger 实机单回复：[�?F5/实机验证]
Snapshot terminal refresh：[�?F5/实机验证]
```

下一�?F5 的同一�?`@GM R3门禁` 应只出现一�?`R3GateTrace` 和一条回复；若仍重复，直接根�?`message_dispatch_deduped`、owner、route �?blocker_codes 定位，不再扩展新的去重集合�?
## 57. W2.1 Entity Readiness：支撑语义统一

`2026-07-14_13-28-28_corona.log` 的终态事实为�?
```text
Runtime entities�?（environment 2 + actor 7�?Game-ready�?/14
readiness_missing：grounding_status x3
Engine bridge�?3/13 success
```

结合本次保留�?7 张混元输入图�?Actor 导入顺序，普通对象依次属于：衣柜、书桌、床、地毯、台灯、玩偶、书架。旧代码�?Runtime import、geometry review �?layout reflow 三处各维护一份名称规则，前四类可识别�?`floor_supported`，台灯、玩偶和书架落为 `unknown`；因�?13 �?Engine 写入可解释为 `2 environment + 7 actor create + 4 ground transform`，与 3 �?grounding 缺失完全对应�?
本轮改动�?
- 新增共享 `support_semantics.classify_support_type()`，统一 import、ground review �?layout reflow�?- 补齐台灯/落地灯、玩�?玩具、书�?书柜等通用地面支撑语义�?- 保持严格优先级：吊灯/悬挂物先�?`ceiling_hung`，壁�?墙饰先判 `wall_mounted`，不会因包含“灯”而统一落地�?- 显式 `support_type` 优先于名称推断，允许上游结构化语义覆盖规�?fallback�?- 分类结果只决�?support domain；只�?Engine actual AABB 证明 bottom 接触地面，或 Engine ground transform 返回成功，才能写�?`grounding_status=grounded`�?- `estimated` AABB、浮�?AABB、挂�?悬挂�?unknown 对象不得伪�?grounded�?
聚焦验证�?
```text
Support semantics + Game-ready�?6 passed
AgentRuntime phase1�? passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示�?```

日志还存�?4 �?`GeometrySystem: invalid mesh slot skipped`。这证明当前 `engine_accepted/load_finished` 尚不能完整代�?render-ready；该问题先作为下一 Gate 事实断点记录，不在本�?support/grounding 修改中顺带改 C++�?
当前 Gate 保持�?
```text
red / pending_reevaluation
entity support semantic closure：code_complete
台灯、玩偶、书�?ground transform + actual AABB：[�?F5/实机验证]
预期 Game-ready：若三�?Engine 事实成立，可�?6/14 提升�?9/14
invalid mesh render readiness：待独立诊断
```

## 58. W2.1 Entity Readiness：真实可渲染几何门禁

用户提供�?VSCode F5 日志仍为�?
```text
build/examples/engine/RelWithDebInfo/logs/2026-07-14_13-28-28_corona.log
日志结束时间�?026-07-14 14:05:18
```

该日志早于以下修复提交：

```text
d9dc806f 2026-07-14 14:15:22 terminal Engine Snapshot refresh
6173c9a9 2026-07-14 14:18:55 structured GM query dedupe
1695c56b 2026-07-14 14:28:39 unified entity support semantics
```

因此它是修复前基线，不能用于验证 Snapshot 终态刷新、GM 单回复或支撑语义修复。日志中仍有以下有效问题证据�?
```text
GeometrySystem load finished：存�?GeometrySystem invalid mesh slot skipped�? �?OpticsSystem skipped invalid mesh draw：存�?render_status_observed/render_ready：未进入 Runtime 事实
RuntimeEvidence：Game-ready 6/14，grounding_status 缺失 3 �?R3GateTrace�? 次，Snapshot integrity red
```

其中无效 mesh slot �?vertex/index/storage buffer 均为 false，但�?`get_editor_actor_geometry_status_from_python()` 只检�?`gpu_build_state == Ready` �?`mesh_count > 0`。这会把“Actor 已加载但当前没有有效可绘�?mesh slot”错误计�?Engine-ready，进而污�?Registry、SceneWorldSnapshot �?R3GateReport�?
本轮改动�?
- �?C++ `Geometry` API 增加只读 `GeometryRenderStatus`，通过 `GeometrySystem::query_mesh_slots()` 统计可绘制和无效 mesh slot�?- CEF Actor Snapshot 输出 `render_status_observed`、`render_ready`、`render_failed`、`gpu_build_state`、`mesh_count`、`renderable_mesh_count` �?`invalid_mesh_count`�?- Runtime actor/environment import �?late-ready reconcile 保留上述真实 Engine 字段�?- `engine_verified` �?`game_ready` 现在同时要求 actual AABB 与真�?render-ready；无�?slot 不再被伪装为 Game-ready�?- R3 readiness 对未观测和不可渲染实体分别输�?`render_readiness_unobserved`、`render_not_ready`�?- 不修改资源生成、LOD 切换、渲染或 Engine 写入链路；本轮只补真实事实观测与门禁�?
聚焦验证�?
```text
Game-ready + R3 readiness + support semantics�?2 tests passed
Python syntax compile：passed
RelWithDebInfo corona_engine 增量构建：passed
新增回归：actual AABB 存在�?mesh slot 无效时不�?Game-ready
```

当前 Gate 保持�?
```text
red / pending_reevaluation
真实 render readiness bridge：code_complete
Snapshot terminal refresh：code_complete
GM structured query dedupe：code_complete
support semantics closure：code_complete
上述四项真实 Engine/UI 效果：[�?F5/实机验证]
```

下一�?F5 必须使用包含本节改动的新构建，并核对�?
```text
Actor Snapshot 中出�?render_status_observed/render_ready/invalid_mesh_count
无效 mesh slot 对应实体进入 needs_review，而不�?Game-ready
台灯、玩偶、书架不再缺 grounding_status（以实际 AABB/ground transform 为准�?同一�?@GM R3门禁 只有一�?R3GateTrace 和一条回�?Snapshot plan/version/fingerprint 与终�?Registry 一�?```

## 59. W2.1 R3GateReport：Render Readiness 自动对账

在真�?render readiness bridge 落地后，R3 聚合器虽然已经能逐实体识�?`render_readiness_unobserved` �?`render_not_ready`，但顶层 Gate 摘要此前只披�?Game-ready 总数。若下一�?F5 仍有无效 mesh，仍需要人工展开 Registry 才能区分“未观测”“不可渲染”和“支撑状态缺失”�?
本轮改动�?
- `entity_readiness.metrics` 增加渲染观测数、渲染就绪数、失败数、无�?mesh 实体数和无效 slot 总数�?- `R3GateReport.metrics` 提升同一组聚合指标，并提�?`readiness_missing_field_counts`，供后续 runtime doctor �?ProjectGate 只读复用�?- GM R3 门禁回复同时显示基准 Game-ready 分母和当前实际实体渲染分母，避免把�?4 个基准目标”和�? 个已存在实体”混为同一统计口径�?- `R3GateTrace` 直接记录 render、render_observed、invalid_mesh �?entity_missing 摘要，下一轮日志可以自动对账，不再人工关联 GeometrySystem warning�?- 普�?`needs_review` 仍按既有阈值进�?yellow/red；渲染诊断指标不会被错误写成身份矛盾，也不会改变 RuntimeState�?
预期用户可见摘要�?
```text
场景版本：vN；Game-ready�?/14
渲染就绪�?/9（已观测 9/9；无�?Mesh 实体 2，slot 3�?实体待检查：grounding_status x3；render_not_ready x2
```

聚焦验证�?
```text
Game-ready + R3 readiness + support semantics + GM 只读披露�?5 tests passed
R3 查询�?Runtime 写入：passed
渲染聚合口径与无�?mesh 统计：passed
```

当前 Gate 不变�?
```text
red / pending_reevaluation
R3 render readiness 自动对账：code_complete
真实 Engine 字段与用户摘要：[�?F5/实机验证]
```

## 60. W1.4 Finalizer Completeness：自动收尾退避与熔断

最�?F5 日志�?
```text
build/examples/engine/RelWithDebInfo/logs/2026-07-14_18-47-10_corona.log
```

该轮三个业务图均失败后，自动 worker 继续对空队列执行 Finalizer；内部图数量�?85 增长�?352，最终报告与 `report_ready` 未形成可信终态。上一断点已修�?Environment render-ready 字段�?C++ 安全桥、Adapter �?Validator 之间的契约丢失，本节只收�?Finalizer 的自动重试放大�?
本轮改动�?
- `final_report_persist_pending` �?`report_ready_event_persist_pending` 保留自动恢复语义，但采用 1/2/4/8 秒指数退避，最长不超过 30 秒�?- 同一计划连续 4 次收尾持久化失败后，暂停该房间的自动 drain，记�?`runtime_finalizer_retry_exhausted`；不伪�?`report_ready`，不把失败计划声明为完成�?- 若同一 ScenePlan 后续出现新的 queued/running ToolGraph，自动解除收尾暂停，避免阻断真实追加批�?- 正常一次失败后恢复、零 drain 晚到 `report_ready`、正常终态清理房间的既有语义保持不变�?
聚焦验证�?
```text
Finalizer backoff/circuit-breaker Worker tests: 3 passed
Transient report persistence retry: passed
Missing report_ready recovery retry: passed
Python syntax compile: passed
git diff --check: clean（仅既有 CRLF 提示�?```

当前 Gate�?
```text
red / pending_reevaluation
Environment render-ready 字段闭环：code_complete
Finalizer 自动重试退避与熔断：code_complete
真实业务图完成、Registry/Snapshot/report_ready 终态：[�?F5/实机验证]
```

下一�?F5 重点核对：三个业务图应不再在 Environment 状态写入节点失败；正常成功时必须出现完�?Finalizer 终态事件。若报告持久化仍失败，内部图不得继续无界增长，并应出现一�?`runtime_finalizer_retry_exhausted` 审计事实�?
## 61. W2.2 R3 F5 日志自动对账探针

新增只读工具 `docs/probes/r3_f5_log_check.py`，直接消�?`R3GateTrace` �?`LANChatRuntimeEvidence`，不导入 AgentRuntime，不修改 RuntimeState、OperationLog �?Engine�?
自动输出�?
- 七个 R3 Gate 维度的最�?red/yellow/green 状态�?- 业务 BatchPlan �?business ToolGraph 数量、终态对账�?- 业务终态后 internal graph 增长量与 Finalizer 熔断证据�?- Game-ready、render-ready �?render observation 摘要�?
旧基线回放：

```text
2026-07-14_18-47-10_corona.log
R3_F5_BLOCKED: PASS=2 WARN=2 FAIL=7
business batches/graphs=3/3
terminal internal graph growth=267
render ready/observed=0/2
```

聚焦验证�?
```text
R3 log probe unit tests: 3 passed
Python syntax compile: passed
old F5 baseline replay: correctly blocked
```

当前 Gate 不变：`red / pending_reevaluation`。新代码�?Engine、Registry、Snapshot
�?Finalizer 效果仍为 `[�?F5/实机验证]`�?
## 62. W1.4/W1.2 最�?F5：Render 二层投影断链�?Finalizer 空转

实机日志�?
```text
build/examples/engine/RelWithDebInfo/logs/2026-07-14_21-18-25_corona.log
```

自动对账结果�?
```text
R3_F5_BLOCKED: PASS=2 WARN=2 FAIL=7
business batches/graphs=3/3
business nodes=54 succeeded=54 failed=0
Game-ready=0/14
render ready/observed=0/8
terminal internal graph growth=3822 (99 -> 3921)
runtime_finalizer_retry_exhausted=0
```

本轮确认业务 ToolGraph、混元资源生成和 C++ Actor 导入均已执行；日志中 `room_box`�?`room_floor` 与普通模型均出现 GeometrySystem load/GPU resource ready 证据。红灯来自两�?收尾断点，而不是业务批次失败：

1. C++ Snapshot �?`adapters.py` 已携�?render readiness，但
   `agent_runtime/tools.py::_normalize_snapshot_actors()` 再次丢弃
   `render_status_observed/render_ready/mesh_count` 等字段，导致 Registry 仍为 0/8 observed�?2. 三个业务图完成后，BatchPlan 处于 `engine_readiness_pending`；Worker 熔断只识别报�?   持久�?pending，未识别 Engine readiness pending，因此每次空 drain 都重复创建约 10 �?   internal graph，并持续发送重复的部分完成状态�?
本轮修复�?
- Runtime scene snapshot 投影保留完整 render readiness 字段�?- Engine import readiness 只通过稳定 `actor_id` �?`entity_id` 对账；禁止按名称、模型路径或
  资产相似度猜�?Actor 归属�?- `engine_readiness_pending` 纳入 Finalizer 1/2/4/8 秒有界退避与四次熔断，避免内部图�?  用户状态消息无限增长；不伪�?`report_ready`�?- 历史 finalizer fixture 补齐新的 render-ready 强约束，并保留同名不�?Actor 不得误绑定测试�?
聚焦验证�?
```text
Game-ready + R3 readiness suites: 50 passed
snapshot render projection / stable entity matching / no same-name claim / finalizer backoff: 4 passed
late-ready finalizer recovery and historical batch identity reconciliation: passed
Python syntax compile: passed
```

当前 Gate 继续保持�?
```text
red / pending_reevaluation
render readiness 二层投影修复：code_complete
engine_readiness_pending 有界退避：code_complete
真实 render observed/Game-ready/Finalizer terminal�?[�?F5/实机验证]
```

下一�?F5 必须核对：`render_observed > 0`、`internal graph` 在业务终态后不再无界增长�?必要环境实体进入 ready，并出现 Registry/Snapshot/report_ready 的可信终态事件�?
## 63. W1.2 F5 前置核验：Native `created` �?Engine-ready 事实脱节

�?`f56dae61` �?Render Snapshot 投影�?Finalizer 有界重试修复后，F5 provider 聚焦回归�?报告一�?`actor_import` readiness mismatch。测试事实显示普�?Actor 已同时具备：

```text
stable actor_id
engine_actual AABB
engine_lifecycle_status=bounds_ready
render_status_observed=true
render_ready=true
```

�?C++ 导入返回的同步生命周期仍�?`created`。Registry �?Engine write 判定此前只接�?`engine_created/engine_imported/...`，因此将这类已经被原�?Snapshot 独立证明就绪�?Actor
保留�?`engine_write_verification_status=unknown`。这会导致上一节字段投影修好后，普通模�?仍无法进�?Game-ready�?
本轮修复严格限定为：只有 actual bounds、render observation、render-ready �?ready lifecycle
四项同时成立时，`sync_status=created` 才可计为 `engine_verified`。单独的 handle �?created
返回仍不代表 Engine ready，也不能进入 Game-ready�?
同时更新 F5 provider fixture，使其显式模�?native render readiness，不再用旧的
handle/AABB-only 事实冒充完整 Engine 终态�?
聚焦验证�?
```text
Game-ready + R3 readiness + F5 provider bridge + Finalizer backoff�?2 passed
Python syntax compile：passed
�?F5 日志探针：R3_F5_BLOCKED PASS=2 WARN=2 FAIL=7（符合修复前基线�?```

当前 Gate 仍为�?
```text
red / pending_reevaluation
native created + actual render-ready reconcile：code_complete
真实普�?Actor Game-ready �?Finalizer 终态：[�?F5/实机验证]
```

下一�?F5 除上一节检查项外，还必须确认普�?Actor �?`engine_write_verification_status=engine_verified`，不能只看到 Environment ready�?
## 64. W1.2 新一�?F5�? 个实体全部就绪，环境支撑语义阻断门禁

实机日志�?
```text
build/examples/engine/RelWithDebInfo/logs/2026-07-14_23-38-14_corona.log
```

本轮自动对账结果�?
```text
R3_F5_BLOCKED: PASS=8 WARN=1 FAIL=2
business batches/graphs=3/3, terminal=3/3
business nodes=54, succeeded=54, failed=0
Runtime entities=9, Game-ready actual=9/9
R3 benchmark Game-ready=9/14 (entity_readiness=green)
render ready/observed=9/9
internal graphs=79, terminal 后增�?0
engine_bridge=16/16/0
environment entities=2
```

与上一轮相比，Render Snapshot 投影、Native `created` readiness reconcile �?Finalizer
有界重试均已在真�?F5 生效�? 个业务批次全部完成，9 个实际实体全部达�?Game-ready�?终态后�?internal graph 数量稳定�?79，没有再次出�?3921 个内部图的无界增长�?
R3 门禁仍为红色的唯一单机事实断点�?`environment_readiness`�?
```text
environment_not_ready:room_box
room_box:grounding_status
```

日志同时证明 `room_box.obj` 已真实导入、GeometrySystem load finished、AABB 与渲染状态均�?就绪。因此这不是 Environment 导入失败，而是 Registry 组装时优先采用了通用 AABB 推断出的
`grounded`，覆盖了房间壳应有的 `enclosure` 语义�?
本轮修复�?
- Environment 支撑语义�?`component_type` 为权威事实源�?- `room_box/room_shell/indoor_enclosure` 强制归一�?`enclosure`�?- `room_floor/terrain/transition_zone` 强制归一�?`grounded`�?- `sky/skybox` 强制归一�?`not_applicable`�?- 普通未�?Environment 组件才保留显�?grounding 值�?- 增加反向回归：即�?room box 被上游误写为 `grounded`、room floor 被误写为
  `enclosure`，Registry 仍输出正确的领域语义�?
聚焦验证�?
```text
Game-ready + R3 readiness suites: 50 passed
Python syntax compile: passed
git diff --check: passed
```

当前 Gate�?
```text
red / latest_f5_environment_semantic_mismatch
environment grounding semantic normalization: code_complete
修复后单�?R3 Gate 预期：yellow（仅 multiplayer_consistency 待证据）
真实 room_box=enclosure 与单机黄灯：[�?F5/实机验证]
多人 entity_id/asset_id/version 一致性：[�?F5/实机验证]
```

独立观察项：LOD 切换后仍偶发 `invalid mesh slot skipped`，但本次 R3 查询时记录为
`invalid_mesh=0`。该问题列入渲染稳定性后续验证，不与本轮 Environment 语义修复混改�?
## 65. 2026-07-15 收口：Provider 命名空间与业务图失败证据

`2026-07-15_01-15-38_corona.log` 暴露了两个独立断点：

```text
混元3D 已禁�?(enable=False)
3/3 business graphs failed
business_graph_consistency 被错误判�?green
失败�?Finalizer 继续产生内部轮询�?```

根因不是 `ai_setting.py` 未启用混元，而是同一 Quasar 包同时以 `Quasar` �?`plugins.AITool.Quasar` 两个模块名加载。配置注册和工具发现分别读取了不同的
`ConfigCollector`，导致工具侧看不到正式设置�?
本轮修复�?
- Runtime 创建前同时加载两�?Hunyuan config loader�?- 以顶�?`Quasar` 配置为权威，将设置、loader 归一结果和配置来源同步到兼容命名空间�?- 增加不含密钥�?Provider 诊断日志�?- 保留 `drain_tool_graph_queue()` 的安�?`finalized_plans` 摘要，使 Worker 能识�?  `final_report_persist_pending` 并启用有界退避；不再因字段清洗丢�?Finalizer 状态�?- 失败计划只有在失败报告持久化并产�?`report_ready` 后才正常清理；报告写入持续失败时
  最多自动重�?4 次并暂停轮询，避免内部图无界增长，也避免提前遗失可信失败报告�?- R3 `business_graph_consistency` 不再把“结构一一对应但执行全部失败”判�?green�?  failed/blocked 业务图、批次和节点均进入明�?contradiction 与成功计数�?
本地聚焦证据�?
```text
Quasar runtime/plugin hunyuan enable: True / True
Runtime direct tool probe: hunyuan_generate_3d found
Provider/finalizer/R3 focused tests: 22 passed
agent_collaboration red-gate suites: 78 passed
```

当前状态：

```text
Hunyuan provider namespace convergence: code_complete
failed-plan report + bounded finalizer polling: code_complete
business_graph_consistency failed-outcome audit: code_complete
真实混元任务提交�?Actor materialization: [�?F5/实机验证]
失败计划一次性终报与轮询停止: [�?F5/实机验证]
room_box=enclosure / room_floor=grounded: [�?F5/实机验证]
```

轨道 B 红灯允许范围已经具备 contracts、ProjectState、ArtifactRegistry、AgentTaskGraph
及三个非执行型职�?Agent。当前门禁仍�?`red / pending_reevaluation`，因此不接入真实�?Mock Snapshot，不建立生产 Coordinator、ProjectGate �?ActionProposal�?
### 65.1 Snapshot 身份完整性收�?
成功物化日志 `2026-07-14_23-38-14_corona.log` 已证明：

```text
snapshot_integrity=green
game_ready=9/14
render_ready/render_observed=9/9
```

因此 `2026-07-15_01-15-38_corona.log` 中的 Snapshot 红灯�?Provider、Environment �?Finalizer 失败后的连带结果，不是独立的 Snapshot 构建断链�?
本轮补齐一个面向三职能 Agent 的身份不变量：不可变 Snapshot 中每个实体都必须具有
非空且唯一的稳�?`entity_id`。指纹即使与 payload 一致，也不能封存无法被下游 Agent
可靠引用的匿名实体�?
聚焦验证�?
```text
Snapshot/Game-ready/R3 suites: 53 passed
Python syntax compile: passed
git diff --check: passed
```

当前边界�?
```text
Snapshot fingerprint + immutable read path: code_complete
stable entity_id hard validation: code_complete
最�?Provider/Finalizer 修复后的 snapshot_integrity: [�?F5/实机验证]
多人 host/peer Snapshot identity consistency: [待多�?F5/实机验证]
```

## 66. Multiplayer consistency：Peer Ack 计划与版本锁�?
现有网络链路已经发送：

```text
plan_id
scene_version
host_identity_fingerprint
peer_identity_fingerprint
entity_count / applied_entity_count
identity_drift_count / version_drift_count
status
```

�?Runtime 证据聚合此前存在三个缺口�?
- `scene_version` 在安全持久化时被转成字符串，而不是稳定整数事实�?- Peer ack 未与当前 Registry �?`scene_version` 强制比对，旧版本 ack 可能污染新版本门禁�?- 只要任意一个成�?ack 成功就可能达�?green，没有要求所有已知活跃成员完成确认�?
本轮修复�?
- `scene_version` 纳入 SyncEvent 强类型整数白名单�?- R3 只消费精确匹配当�?`plan_id` �?peer ack�?- ack 版本必须等于当前 Registry 版本；旧版本计入 `version_drift` 并判 red�?- ack 只有在状态为 `peer_confirmed/host_peer_verified/synced` 时才能贡�?verified 实体�?- 聚合已知活跃 peer �?acknowledged peer，存在未确认成员时保�?yellow，并明确输出
  `peer_snapshot_ack` 缺失项�?- Peer mirror 侧只�?AABB、没有实�?render readiness 时继续保�?`needs_review`，不再用旧测�?  假定其已�?Engine verified�?
聚焦验证�?
```text
Peer mirror + R3 readiness + native sync + Game-ready suites: 67 passed
Python syntax compile: passed
git diff --check: passed
```

当前边界�?
```text
plan/version/status exact peer ack validation: code_complete
all-known-peers acknowledgement gate: code_complete
scene_version safe integer persistence: code_complete
房主与全部成�?entity_id/asset_id/version 一�? [待多�?F5/实机验证]
多人 Snapshot fingerprint �?scene_version 实际 ack: [待多�?F5/实机验证]
```

## 67. 轨道 B 契约硬隔离：Artifact 执行资格

CodeGraph 与静态依赖核验确认：`agent_collaboration` 当前不反向导�?AgentRuntime、LANChat�?ToolCallGraph、PlanPatch �?RuntimeState，三个职�?Agent 只产生非执行�?Artifact�?
本轮发现的契约绕过点�?
```text
snapshot_source=none
non_executable=false
status=validated
```

此前该组合能够通过 `assert_executable()`，即没有绑定真实 Snapshot �?Artifact 可能在未来写�?入口建立后跨过执行边界�?
本轮修复�?
- 可执�?Artifact 在构造时必须声明 `snapshot_source=runtime`�?- 可执�?Artifact 必须绑定正数 `base_world_version`�?- `assert_executable()` 在未来执行边界再次复核同一组事实，形成构造层与执行层双重保护�?- `mock` Artifact 继续强制 `non_executable=true`�?- 红灯下现�?Planning/Art/Program Agent 仍只产生 `snapshot_source=none` 的非执行 Artifact�?
聚焦验证�?
```text
All agent_collaboration focused tests: 79 passed
Python syntax compile: passed
git diff --check: passed
```

当前边界�?
```text
contracts content hash + real validator: code_complete
none/mock Artifact execution denial: code_complete
runtime Artifact world-version requirement: code_complete
真实 Snapshot 接入、Coordinator、ProjectGate、ActionProposal: 绿灯前禁�?```

## 68. 轨道 B 项目版本闭环：ProjectState �?ArtifactRegistry

CodeGraph 核验确认 Registry 已具备批量副本校验、ProjectState compare-and-swap、注册回放幂等�?上游替换后的直接与传�?stale 传播，失败校验不会留下半注册记录�?
本轮补齐世界版本断点�?
- 所�?`snapshot_source=runtime` Artifact 在构造时必须具有正数 `base_world_version`�?- Registry 注册 Runtime Artifact 时，`base_world_version` 必须等于 ProjectState 当前
  `scene_world_version`，过期或未来版本均拒绝注册�?- Runtime Artifact 注册成功后，如果项目世界版本继续前进，旧 Artifact 保留审计历史，但
  `current(require_usable=True)` �?`list_current(include_stale=False)` 均不再返回它�?- Mock/Runtime 输入隔离测试先建立一致的世界版本，再验证职能 Agent 自身拒绝 Snapshot 输入�?  不通过构造错误掩�?Agent 隔离断言�?
聚焦验证�?
```text
All agent_collaboration focused tests: 81 passed
Python syntax compile: passed
git diff --check: passed
```

当前边界�?
```text
ProjectState CAS + monotonic world version: code_complete
Artifact batch atomicity + dependency stale propagation: code_complete
Runtime Artifact registration world-version lock: code_complete
World-version advance invalidates Artifact usability: code_complete
真实 Snapshot 版本写入 ProjectState: 绿灯后由 Coordinator 接入
```

## 69. 轨道 B 任务依赖收口：AgentTaskGraph 消费项目世界版本

CodeGraph 核验发现，`AgentTaskGraphStore` 此前直接读取 `ArtifactRecord.usable`，只能判�?Artifact 自身状态，不能反映 ProjectState �?`scene_world_version` 已经前进。因此，一个绑定旧 Runtime Snapshot 版本�?Artifact �?Registry 层已经过期后，仍可能被任务状态机当作可用输入�?
本轮修复�?
- `ArtifactRegistry.is_usable(project_id, ref)` 成为项目感知的唯一可用性查询，同时校验 Artifact 记录与当前项目世界版本�?- `AgentTaskGraphStore` 的输入依赖解析和任务完成检查统一调用该接口，不再绕过 ProjectState�?- `start_task()` 在增�?`attempt_count` 之前重新计算任务状态；输入已过期时直接阻断，不消耗一次虚假尝试�?- 已完成的上游生产任务保留为历史审计事实；依赖其旧版本输出的下游任务被精确阻断，不回滚历史任务状态�?
聚焦验证�?
```text
AgentTaskGraph focused tests: 12 passed
All agent_collaboration focused tests: 82 passed
Python syntax compile: passed
git diff --check: passed (line-ending warnings only)
```

当前边界�?
```text
Task input project/world-version revalidation: code_complete
Stale runtime Artifact start blocking without attempt consumption: code_complete
Three-role Agent structured output and downstream stale regeneration: next block
Real Snapshot/Coordinator/ProjectGate/ActionProposal integration: forbidden before green gate
```

## 70. 轨道 B 职能 Agent 预检：消除人�?TaskGraph refresh 依赖

三个职能 Agent 此前�?`run()` 入口直接读取已存储的 TaskGraph。上�?Artifact 刚被新版本替换时，Registry 已经将旧依赖标记�?stale，但 TaskGraph 可能仍暂时保�?`ready`；测试与调用方需要手工调�?`refresh()` 才能恢复一致�?
本轮修复�?
- Planning/Art/Program Agent 在校验任务和构建上下文前，统一执行 TaskGraph preflight refresh�?- Art/Program stale-input 测试删除人工 `refresh()`，直接验证生产入口会把任务收口为 `blocked`，且 Reasoner 不被调用�?- `start_task()` 的二次重算仍保留，覆�?preflight 后、真正开始任务前的竞态窗口�?- 三个 Agent 仍只产出 `snapshot_source=none` �?`non_executable=true` 的强类型 Artifact�?
聚焦验证�?
```text
Planning/Art/Program/Five-Artifact workflow tests: 42 passed
All agent_collaboration focused tests: 82 passed
Python syntax compile: passed
Static isolation scan: no AgentRuntime/RuntimeState/SceneWorldSnapshot/PlanPatch/ToolCallGraph/LANChat imports
```

当前边界�?
```text
Red-gate contracts/project state/registry/task graph/three-role outputs: code_complete
Three-role production entry or real/mock Snapshot consumption: forbidden
EntityBindingPlan/Coordinator/ProjectGate/ActionProposal: green-gate only
F5 requirement: none for this pure collaboration-contract block
```

## 71. 轨道 A 收尾身份修正：失败计划不再冒�?latest completed

Finalizer 允许成功与失败计划都产生终态报告，但此前在 `report_ready` 后无条件写入 `latest_completed_plan_id`。这会把 Provider/Batch 失败的计划暴露为“最近成功场景”，导致后续追加实体、状态查询或下游世界绑定选错目标�?
本轮修复�?
- `report_ready` 继续表示终态报告已持久化，不再隐含场景成功�?- 只有 `ScenePlanStatus.COMPLETED` 才写�?`latest_completed_plan_id` 并记�?`latest_completed_plan_set`�?- `ScenePlanStatus.FAILED` 仍清�?`active_execution_plan_id`，但保留原有成功场景指针，不将失败世界变成追加目标�?- 报告事件写入失败�?6% 重试、全批次等待�?late Engine-ready 收口语义保持不变�?
聚焦验证�?
```text
Failed-plan terminal report identity regression: 1 passed
Finalizer report-event retry + all-batch wait: 2 passed
Late Engine bounds readiness finalization: 1 passed
Game-ready finalizer/registry/snapshot suite: 36 passed
R3 readiness evaluator suite: 18 passed
Python syntax compile: passed
git diff --check: passed (line-ending warnings only)
```

当前边界�?
```text
Failed report vs successful scene identity separation: code_complete
Finalizer retry/order semantics: focused tests passed
Real report_ready/latest_completed behavior: [�?F5/实机验证]
Engine late-ready timing and persisted terminal event order: [�?F5/实机验证]
```

## 72. 轨道 A 业务图对账复核：内部图不污染批次事实

�?`business_graph_consistency` 的当前实现和测试覆盖进行了代码事实复核。当前判定以 BatchPlan �?`tool_graph_id` �?ToolCallGraph �?`graph_role=business_batch` 为唯一业务映射，并独立拒绝角色错配、plan/batch 错配、孤儿业务图、活跃节点和失败节点�?
复核结论�?
```text
query_snapshot/internal_state/review/finalizer graphs excluded from business counts
every BatchPlan requires one referenced business_batch graph
business graph plan_id/batch_id/terminal node facts validated
orphan and duplicate-reference shapes rejected by count/reference reconciliation
R3 readiness evaluator tests: 18 passed
Code change required: no
```

当前边界�?
```text
business_graph_consistency deterministic evaluator: code_complete
real three-batch BatchPlan/ToolGraph count and terminal nodes: [�?F5/实机验证]
user-visible batch count excluding internal graphs: [�?F5/实机验证]
```

## 73. 轨道 A 实体就绪修正：Engine Snapshot 覆盖�?Runtime 估计事实

Registry 此前合并 Runtime Actor �?`observed_actors` 时，只在 Runtime 字段为空时才填入 Engine Snapshot 值。因�?Runtime 中已存在�?`estimated` AABB、旧 transform、`render_ready=false` 或旧 actor version 会压住更新的 Engine 观测，导致已经真实导入的实体长期停留�?`needs_review`�?
本轮修复�?
- 仅当 Snapshot 明确给出 `bounds_ready + bounds_source=engine_actual + actual AABB` 时，覆盖位置、旋转、缩放、AABB、bounds lifecycle �?Engine 版本�?- 仅当 `render_status_observed=true` 时，覆盖 render-ready、GPU build �?mesh 计数�?- `asset_id/model_ref/semantic_role/sync_status` �?Runtime 稳定身份与协同事实不�?Engine 观测随意覆盖�?- 原有 `needs_review/unknown` grounding 不再阻止推理；只�?floor-supported 实体�?`engine_actual` AABB 底部接触地面时才提升�?`grounded`�?- 墙挂、悬挂和环境支撑语义继续优先使用明确值，不被通用 AABB 落地逻辑误伤�?
聚焦验证�?
```text
Game-ready registry/snapshot suite: 37 passed
Late Engine bounds reconcile/finalize: 1 passed
R3 readiness evaluator suite: 18 passed
Python syntax compile: passed
```

当前边界�?
```text
authoritative Engine geometry/render merge: code_complete
selective actual-AABB grounding promotion: code_complete
real bedroom Game-ready ratio >= 8/14: [�?F5/实机验证]
real actor transform/AABB/render facts in RuntimeState and Registry: [�?F5/实机验证]
```

## 74. 轨道 A 环境就绪修正：Environment component 吸收对应 Engine Actor 事实

`room_box/room_floor/terrain/transition_zone` �?Engine 中以真实 model Actor 存在，但 Registry 此前构建环境实体时只读取 environment component 记录。即使对�?Actor 已经�?Snapshot 中拥有实�?AABB �?render-ready，component 仍可能保�?`estimated/render_unobserved`，使必需环境永久无法通过 R3 Gate�?
本轮修复�?
- �?Engine 权威合并抽为 Registry 内部统一 helper，普�?Actor �?environment component 共用同一套可证明覆盖规则�?- environment component 通过 `actor_id` 合并 Runtime Actor �?`observed_actors` 中的 actual bounds、transform、render readiness、mesh 计数�?Engine version�?- 环境身份、component type、semantic role、asset/model ref �?support semantics 仍由 environment domain 保持，不被普�?Actor 观测改写�?- `room_floor/terrain/transition_zone` 继续�?`grounded`，`room_box` �?`enclosure`，sky �?`not_applicable`�?
聚焦验证�?
```text
Game-ready registry/snapshot suite: 38 passed
Indoor/outdoor/mixed environment focused paths: 5 passed
R3 readiness evaluator suite: 18 passed
Python syntax compile: passed
git diff --check: passed (line-ending warnings only)
```

当前边界�?
```text
environment component -> Engine actor observation reconciliation: code_complete
indoor required room_box/room_floor planning and shared bounds: focused tests passed
mixed terrain/room framework/transition requirements: focused tests passed
real room_box/room_floor/terrain render and Engine-ready state: [�?F5/实机验证]
environment_readiness Gate green on real scenes: [�?F5/实机验证]
```

## 75. 下一个统一 F5 验证�?
当前不再通过增加模拟成功来推�?Gate 颜色。下一�?F5 使用一个儿童卧室主流程，在终态报告后执行 `runtime.r3_readiness.evaluate`，一次收集以下证据：

```text
1. entity_readiness
   - actual Game-ready count and per-entity readiness_missing_fields
   - Engine actual transform/AABB/render/version overrides estimated Runtime facts

2. environment_readiness
   - room_box and room_floor exist as environment entities
   - matching actor_id carries engine_actual AABB and render-ready facts

3. finalizer_completeness
   - finalizer_started -> scene_entity_registry_ready
   - runtime_scene_world_consistency_audited -> scene_world_snapshot_ready
   - report_ready -> latest_completed_plan_set -> active_execution_plan_cleared

4. business_graph_consistency
   - business BatchPlan count equals business_batch ToolGraph count
   - internal/query/review/finalizer graphs excluded from user batch count

5. snapshot_integrity/runtime_write_safety
   - same plan/version fingerprint is stable
   - engine actor identity and Registry identity reconcile
   - no runtime_state_only fact is promoted to Engine success
```

该次 F5 的门禁判定：

```text
green candidate: required environment ready and bedroom >= 8/14 Game-ready
yellow candidate: required environment ready and bedroom 5-7/14, with explicit missing fields
red: required environment missing, identity/fingerprint drift, unsafe write, or < 5/14
```

未获得该实机证据前：

```text
current gate remains red / pending_reevaluation
Coordinator/ProjectGate/ActionProposal/EntityBindingPlan remain locked
track B completed contract code remains preserved and non-executable
```

## 76. 轨道 A 多人一致性修正：Peer Ack 必须匹配 Runtime 真实身份世界

此前房主端只验证成员上报�?`host_identity_fingerprint` �?`peer_identity_fingerprint` 彼此相等，并核对实体数量和场景版本；它没有再验证
�?host 指纹是否等于房主 Runtime Registry 中的真实实体身份集合。两个一致但错误
的指纹因此可能被误判为多人一致，尤其会掩�?`room_floor/room_box` 等环境实体漏传�?
本轮修复�?
- Runtime 使用�?LANChat 前端相同�?`scene-id-v1` 规范化和 UTF-16 hash 算法�?  �?`actor_id/entity_id/asset_id/actor_version/plan_id/scene_version` 构造预期身份指纹�?- `scene_snapshot_peer_ack` 除了 host/peer 指纹互等，还必须匹配 Runtime Registry
  的预期指纹；不匹配时 verified 归零并计�?identity drift�?- 环境实体和普�?Actor 使用同一身份集合，不再只验证普通模型数量�?- 保留现有 scene version、entity count、partial fields 和全部在�?peer ack 约束�?
聚焦验证�?
```text
SceneWorld peer mirror/ack suite: 9 passed
LANChat native sync bridge + R3 readiness: 23 passed
Vue/Node and Python mixed identity fingerprint: exact match
```

当前边界�?
```text
host Registry identity -> peer ack exact comparison: code_complete
environment + actor mixed identity coverage: focused tests passed
real host/member entity_id/asset_id/version equality: [�?F5/实机验证]
real duplicate broadcast / asset transfer behavior: [�?F5/实机验证]
```

## 77. 轨道 B W4.5 收口：旧 Persona 与三职能生产者身份隔�?
CodeGraph 核验确认，旧 `MasterAgent/RoleRegistry` 仍负责长者、小女孩、山贼、商人等
兼容聊天人格；`agent_collaboration` 当前没有�?LANChat Worker、Orchestrator 或旧
Agent Adapter 导入，也没有注册生产入口。该边界符合 Red Gate 约束，不需要删除旧角色
或改动聊天室 UI�?
本轮发现契约层仍有一个身份口子：`ArtifactEnvelope` 只验�?producer role 属于允许集合�?没有验证 Artifact 类型与职能的一一对应，并提前允许 `coordinator` 充当生产者。这样旧入口
或未来协调器只要填写一个允许角色字符串，就可能构造不属于自己的强类型 Artifact�?
本轮修复�?
- 首批六种 Artifact 建立唯一 producer 映射：策划生�?`GameDesignBrief/LevelPlan`�?  美术生产 `ArtDirection/SceneCompositionPlan`，程序生�?  `GameplayLogicPlan/EntityBindingPlan`�?- `ArtifactEnvelope` 构造时执行映射校验；错误生产者不能进�?Registry，更不能等待下游
  Agent �?ProjectGate 才发现�?- Red 阶段 producer 集合仅保�?`planning/art/program`；Coordinator 只管理任务和版本�?  不冒�?Artifact 生产者�?- �?Persona 名称�?coordinator 作为 producer 均被契约拒绝；旧角色仍可作为聊天兼容层存在�?
聚焦验证�?
```text
All agent_collaboration focused tests: 83 passed
Wrong-role Artifact rejected at construction before Registry/reasoner: passed
CodeGraph/static dependency audit: no LANChat/legacy Agent -> agent_collaboration production import
```

当前边界�?
```text
W3 contracts/project state/registry/task graph: code_complete
W4 planning/art/program/five-Artifact loop: code_complete
W4.5 legacy persona producer isolation: code_complete
LANChat production entry / real or Mock Snapshot consumption: forbidden while Red
W5 Coordinator/ProjectGate/ActionProposal/EntityBinding production: Green-only
```

至此 Red Gate 下允许的 W3/W4 代码工作已收口。下一步必须由统一 F5 证据包重新评�?W2.1-W2.6；未达到 Yellow/Green 前不再扩展协作生产入口�?
## 78. F5 前总门禁复核与 Environment grounding schema 对齐

本轮按里程碑策略运行 `verify_ultimate_plan.py`。首个完�?Runtime 测试段共执行
656 项，结果�?`11 failures / 21 errors`。后续旧工具段出现外�?LLM/可选工具长时间
等待；在首段证据已经完整、后续等待不再增�?R3 诊断价值后，终止了本次总门禁进程�?因此当前仍不是可声明通过�?F5 基线�?
首段中确认了一个属�?`environment_readiness` 的真实接口断点：Environment import
已经按组件语义产�?`grounding_status`，其�?`room_box= enclosure`�?`room_floor/terrain=grounded`、`sky=not_applicable`，但
`EnvironmentComponentValidator` 的允许字段仍停留在旧版本。StatePatch 因此会以
`unsupported field: grounding_status` 被拒绝，直接影响室内环境事实进入 RuntimeState�?
本轮最小修复：

- Environment component schema 正式接纳 `grounding_status`�?- 校验器只接受 Runtime/R3 规范状态：`grounded`、`enclosure`、`not_applicable`�?  `wall_mounted`、`suspended`、`ceiling_hung`、`needs_review`、`unknown`�?- 任意自由文本仍会被拒绝，避免通过放宽 schema 引入伪造的 Game-ready 事实�?- Provider、EngineWriteGate、RuntimeGuard 和主执行链均未改动�?
聚焦验证�?
```text
Environment import regression tests: 3 passed
Environment component filtered regression: passed
AgentRuntime Game-ready suite: 38 passed
R3 readiness suite: 18 passed
Python syntax compile: passed
```

总门禁中的剩余问题按独立 Gate 维度继续处理，不与本�?Environment 修复混改�?
```text
finalizer/report:
  no-plan report snapshot validation, batch report version conflict,
  partial report persistence semantics

intervention/control:
  non-add intervention deferred record missing

sync/operation evidence:
  external plan atomic event and plan-scoped sync summary assertions

legacy optional tools:
  optional Quasar scene breakdown/settings/video/placement loading failures
  and external-service timeout-heavy tests
```

当前边界�?
```text
Environment grounding fact schema/write alignment: code_complete
Environment StatePatch focused regression: passed
real room_box/room_floor render and Engine-ready facts: [�?F5/实机验证]
full verify_ultimate_plan gate: failed, remaining clusters tracked separately
current R3 gate: red / pending_reevaluation
```

## 79. 轨道 A Finalizer/report 收口：诊断报告不得伪造或覆盖世界快照

总门禁首段的报告失败并非 `SceneWorldSnapshot` 校验过严，而是 `generate_report()`
仍沿用旧 `active_plan_id` 目标，并对无 ScenePlan、批次级诊断报告一律构造计划级不可�?Snapshot。由此产生两类错误：

```text
no-plan diagnostics -> empty plan_id / synthetic scene_version -> snapshot validation failure
batch-scoped report -> partial entity set written to the same plan/version -> snapshot version conflict
```

本轮修复�?
- 默认报告目标统一�?`active_execution -> latest_completed -> active_discussion` 解析�?  显式 `plan_id` 仍保持其诊断过滤语义�?- 没有真实 ScenePlan 时，报告只提供房间级健康度、同步、Provider �?OperationLog 摘要�?  `scene_world_snapshot=None`，world readiness �?`blocked`，只发布 `report_pending`�?- �?`batch_id` 的报告定义为批次诊断视图：保留该批资源、导入、审查、介入摘要，
  但不生成、不冻结、不覆盖计划�?SceneWorldSnapshot�?- 只有�?`batch_id` 的计划级终态报告才能冻结不可变 Snapshot 并发�?`report_ready`�?- 新讨论计划存在时，默认报告仍绑定 `latest_completed_plan_id`，不回退到讨论计划�?- 未放�?`SceneWorldSnapshotRecordValidator`，稳�?plan/version/entity identity 契约保持不变�?
聚焦验证�?
```text
no-plan health/provider/sync/GM report regressions: 7 passed
batch-scoped complex report regression: passed
report target priority regression: passed
Game-ready suite: 38 passed
Finalizer terminal ordering/idempotency regressions: 6 passed
Python syntax compile: passed
```

当前边界�?
```text
no-plan diagnostic report contract: code_complete
batch report vs immutable world snapshot boundary: code_complete
execution/completed/discussion report target priority: code_complete
Finalizer event order and retry semantics: focused tests passed
real Registry -> Snapshot -> report_ready terminal sequence: [�?F5/实机验证]
real completed-world report target after multiplayer discussion: [�?F5/实机验证]
current R3 gate: red / pending_reevaluation
```

## 80. 轨道 A business_graph_consistency 复核：principal graph 契约已具�?
�?Finalizer/report 收口后，对业�?BatchPlan �?ToolCallGraph 的当前实现做了独立复核�?当前事实源已经满足计划文档要求：

- 每个 BatchPlan 持有唯一 principal `tool_graph_id`�?- principal graph 必须同时匹配 plan ID、batch ID �?`graph_role=business_batch`�?- 已完成批次若缺少 principal graph，或引用不存�?身份不匹配的图，排队阶段直接拒绝�?  不会静默创建第二张图掩盖事实�?- R3 Gate 要求批次、业务图和全部节点均处于成功终态；failed/blocked/active 节点会使
  该维度保�?Red�?- internal_state、query、review、finalizer 等内部图不计入用户业务批次数�?- 用户报告�?`business_batch_count` �?internal graph 统计已分域�?
本轮未修改该链路代码，避免在聚焦测试已经证明契约正确时引入无依据改动�?
聚焦验证�?
```text
R3 business graph positive/negative cases: 4 passed
principal graph reuse and dangling-reference rejection: 2 passed
business graph role persistence and report domain split: 2 passed
```

当前边界�?
```text
BatchPlan -> principal business ToolGraph identity contract: code_complete
internal/query graph exclusion: code_complete
terminal node and failed graph rejection: focused tests passed
real F5 business BatchPlan count == business ToolGraph count: [�?F5/实机验证]
real finalizer zero-drain after all business graphs terminal: [�?F5/实机验证]
current R3 gate: red / pending_reevaluation
```

## 81. Track A snapshot_integrity: Registry-to-Snapshot identity closure

The R3 snapshot gate previously checked two useful but incomplete facts:

```text
persisted Snapshot payload -> persisted world_fingerprint
persisted Snapshot -> Engine snapshot consistency audit
```

It did not compare the current same-version `scene_entity_registry` with the
persisted immutable Snapshot. A Registry fact could therefore drift after the
Snapshot was frozen while the Snapshot remained internally self-consistent.

This iteration adds a third required comparison:

```text
current Registry plan_id/scene_version/entities
-> deterministic Registry fingerprint
-> immutable Snapshot world_fingerprint
```

The `snapshot_integrity` dimension is now red when Registry plan identity,
scene version, or world facts do not match the frozen Snapshot. Gate metrics
expose all three comparisons. `script_bindings` are also canonically sorted so
equivalent binding sets do not produce order-only fingerprint drift.

Focused verification:

```text
R3 readiness suite: 20 passed
AgentRuntime Game-ready/Snapshot suite: 38 passed
SceneWorld peer mirror suite: 9 passed
Python syntax compile: passed
```

Current boundary:

```text
Snapshot payload self-integrity: code_complete
Registry plan/version/fingerprint comparison: code_complete
set-like script binding fingerprint stability: focused tests passed
real Runtime Registry -> immutable Snapshot identity: [pending F5/on-device validation]
real Engine snapshot -> Runtime fingerprint consistency: [pending F5/on-device validation]
current R3 gate: red / pending_reevaluation
```

## 82. Track A multiplayer_consistency: reject peer extra applied entities

The multiplayer evidence path already requires exact plan/version peer ack and
all known active peers to acknowledge before R3 can become green. One remaining
edge case was that a peer ack with `applied_entity_count` greater than the host
Registry entity count was clamped to the host count and could therefore look
fully verified.

This iteration treats that case as identity drift:

```text
peer applied_entity_count > host registry entity count
-> identity_drift_count += 1
-> verified_entity_count = 0 for that peer ack
-> multiplayer_consistency remains red through R3 Gate
```

Peers that apply fewer entities are still handled as partial sync rather than
identity drift, preserving the existing yellow path for incomplete but
non-contradictory synchronization.

Focused verification:

```text
SceneWorld peer mirror suite: 10 passed
R3 readiness suite: 20 passed
Python syntax compile: passed
```

Current boundary:

```text
peer extra applied entity rejection: code_complete
all-known-peers acknowledgement gate: focused tests passed
plan/version/status exact peer ack validation: focused tests passed
real host/member entity_id/asset_id/version consistency: [pending F5/on-device validation]
real multiplayer Snapshot fingerprint ack: [pending F5/on-device validation]
current R3 gate: red / pending_reevaluation
```

## 83. Track A environment_readiness: all required component instances must be ready

The environment gate already recomputes required component readiness from
downstream-visible facts instead of trusting `game_ready` alone. One remaining
edge case was duplicate required environment instances:

```text
room_floor instance A: ready
room_floor instance B: not ready / estimated AABB
```

Previously, the component type could still count as ready because at least one
instance was ready. For a Game-ready world this is too permissive: duplicate or
stale environment actors can still affect scene queries, sync, and downstream
Agent binding.

This iteration changes required component readiness to require every instance
of that required type to be ready:

```text
required component type present
+ all instances pass environment readiness recomputation
-> component ready

any required component instance missing engine_actual AABB, render readiness,
grounding semantics, sync status, or game_ready
-> environment_not_ready:<component_type>
```

Focused verification:

```text
R3 readiness suite: 21 passed
AgentRuntime Game-ready/Snapshot suite: 38 passed
Python syntax compile: passed
```

Current boundary:

```text
all-instance required environment readiness: code_complete
duplicate partial room_floor rejection: focused tests passed
real duplicate/stale environment actor absence: [pending F5/on-device validation]
real room_box/room_floor/terrain readiness after import: [pending F5/on-device validation]
current R3 gate: red / pending_reevaluation
```
