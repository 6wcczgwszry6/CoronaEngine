# R3-min 推进记录

更新时间：2026-07-23

## E8 当前执行覆盖（优先于下方历史锚点）

```text
当前工作块：B7.1 E8 Program 原语语义与伪循环收敛
当前任务：E8.1 GameplayLogicPlan 交互参与者契约
任务状态：code_complete / pending_focused_verification
当前执行角色：架构 AI
Full R3 Gate：red / pending_reevaluation
B7.1：blocked / collaboration_program_contract_failed
B7.2：blocked_by_B7.1
Collaboration schema：1.3（不升级）
Skeleton：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd（不变）
最新只读证据：2026-07-22_23-46-45，二轮会话；B7_1_CONTROL_BLOCKED / PASS=15 WARN=1 FAIL=2
下一任务：E8 聚焦测试；随后使用全新独立 Session 执行完整六轮 B7.1
```

## 0. 当前执行锚点

```text
完整 R3 权威计划：docs/plan/R3稳定门禁与三职能Agent双轨推进计划.md
历史子计划：已被权威计划取代并清理
执行约束：docs/Agent任务约束循环_R3三职能协同版.md

当前分支：agent-native
当前 AI 基准 HEAD：3d849a9a
当前 origin/main：6721de43
Engine 当前实机参考：HEAD 3d849a9a + working-tree patch fingerprint 0c651bd4（非稳定跨版本 SHA）
Engine 候选集成 SHA：待 Engine 组冻结
Frontend 候选集成 SHA：待 Frontend 组冻结

当前工作块：B7.1 三职能契约与控制面收敛
当前任务：B7.1 六消息独立 Session F5
任务状态：E6.0-E6.5 code_complete / pending_independent_f5 [待F5/实机验证]
里程碑状态：B7.1 blocked / collaboration_program_contract_failed；B7.2 blocked_by_B7.1
当前执行角色：实机验证

Skeleton contract version：r3-skeleton-week1-v6（Planning -> Program -> Art 依赖与 Program 接口变更后冻结）
Skeleton contract hash：sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd
当前 Skeleton 节点：demo_result（B4.2 已填充）
当前节点 owner：integration
待 F5 Skeleton 节点数：1
待 F5 Adapter 项：2（Engine capability、Frontend 业务协议）
未决 InterfaceChangeRequest：1（request.b2.2-engine-dto-version）
最新 InterfaceChangeDecision：accepted / request.b6.4-gameplay-plan-patch-payload

Full R3 Gate：red / pending_reevaluation
Single-player Demo Gate：evaluator_available / not_evaluated

最新自动证据：E6 Track B 123 passed；E6 聚焦组合 59 passed；辅助控制面 26 passed；受影响 Runtime Guard 15 passed；Python syntax compile passed
已知门禁噪声：无；3 项 sys.modules 顺序污染误报已改为目标模块 AST import 检查
最新总门禁：E5 收口后 `verify_ultimate_plan.py` 运行一次，在 900 秒上限超时；输出 134 个连续通过点，未出现断言失败，门禁未完整结束
最新实机边界：2026-07-21 04:20 F5 已完成 Discussion 与 Planning；Program 调用耗时 260770ms 后因 duplicate semantic_role 阻断，Art/Narrator/Proposal/Runtime 均未进入
最新实机日志：build/examples/engine/RelWithDebInfo/logs/2026-07-21_04-20-32_corona.log
最新 LANChat history：build/examples/engine/RelWithDebInfo/Saved/LANChat/history/single-default__session__1784578872125__1.jsonl
最新控制面探针：B7_1_CONTROL_BLOCKED / PASS=13 WARN=1 FAIL=4（E6 Probe 口径）
最新 Scene Runtime 探针：B7_2_SCENE_BLOCKED / PASS=1 WARN=0 FAIL=5
最新记录章节：106
下一 ready 任务：使用全新 Session 原样执行 B7.1 六消息验收
```

维护规则：

- 1-66 节作为历史审计保留，不回写旧结论。
- 从第 67 节起使用紧凑任务记录，不再追加长篇 Progress Update。
- 后续 AI 默认只读取本锚点、最近 2-3 条记录和当前任务引用的历史章节。
- 每次任务结束更新本锚点；只有工作块收口时增加阶段总结。
- 第 1-81 节保留为黑盒阶段审计；其中 `verified` 表示自动契约验证，不等于生产接入或 Engine 实机验证。
- 第 82 节起同时记录 `contract_status` 与 `production_integration_status`，不得互相替代。

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

- 新增 `docs/plan/R3稳定门禁与三职能Agent双轨推进计划.md`，作为当前唯一推进优先级来源。
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

## 35. W3.3 GameProjectState 存储与版本迁移

在强类型契约稳定后，本轮建立独立项目事实存储。该状态层只维护三职能协作的项目版本、任务图引用、场景计划/世界版本和 Artifact 引用；它不复用 Runtime `StatePatch`，也不读取或修改 RuntimeState。

当前改动：

- 新增线程安全 `ProjectStateStore`，以不可变 `GameProjectState` 作为当前项目事实。
- 新增不可变 `ProjectStatePatch`；每个 Patch 必须携带 `patch_id/project_id/expected_project_version/source/changes`。
- 采用 compare-and-swap：期望版本与当前版本不一致时明确抛出 `ProjectVersionConflictError`，不静默覆盖其他 Agent 更新。
- `patch_id` 重放返回原结果且不重复增加版本/历史；相同 ID 携带不同内容时抛出 `ProjectPatchConflictError`。
- `scene_world_version` 只能单调递增，回退版本明确拒绝。
- `project_id/room_id/project_version` 等身份字段不能由 Patch 修改；只允许更新计划中列出的五个项目字段。
- 无实际变化的 Patch 不虚构新 project version 或迁移记录。
- 每个真实迁移记录 source、from/to version、changed fields 和不可变 before/after，用于后续 ArtifactRegistry 审计。
- Store 与 contracts 独立导入时均不会加载 AgentRuntime/LANChat 模块。

聚焦自动验证：

```text
创建项目 + 显式 source 更新 -> project_version 1 -> 2
stale expected version -> 冲突且状态/历史零变化
相同 patch 重放 -> 幂等；同 ID 异内容 -> 拒绝
scene_world_version 回退 -> 拒绝
no-op patch -> 不增加版本
两个并发写者使用同一 expected version -> 仅一个成功
多项目状态隔离 + 身份字段不可修改
协作契约与 ProjectState 聚焦测试 15 项通过
Python syntax compile、导入隔离与 git diff --check 通过
```

当前任务状态：

```text
W3.3 GameProjectState 存储与版本迁移：code_complete
W3.4 ArtifactRegistry 与失效传播：ready
W3.5 AgentTaskGraph：等待 W3.4
当前 Gate：red / pending_reevaluation
```

以下仍未实现：

- ProjectState 的跨进程持久化和多人广播；第一阶段只提供协作层内存事实接口。
- ArtifactRegistry 注册/查询、版本索引和 stale 传播。
- 真实 Snapshot、RuntimeState、LANChat 或三职能生产 Agent 接入。
- 本轮不改变轨道 A Gate，所有 Engine/Sync 效果仍为 **[待 F5/实机验证]**。

## 36. W3.4 ArtifactRegistry 与失效传播

在 Gate 仍为 Red、等待下一轮 F5 重新评估期间，完成独立轨道 B 的 Artifact 版本事实层。本轮没有接入 RuntimeState、SceneWorldSnapshot、LANChat、ActionProposal 或 Engine 写入路径。

当前改动：

- 新增 `services/agent_collaboration/artifact_registry.py`，以不可变 `ArtifactEnvelope` 为内容事实，以独立 `ArtifactRecord` 保存 `current/stale/superseded` 生命周期，避免修改已计算 hash 的 Artifact。
- 引入显式 `artifact_id@version` 引用；依赖、项目当前引用和审计查询均绑定具体版本，旧版本不能冒充当前有效版本。
- 支持单项与批量原子注册；同一个 Agent 一次产出的多个 Artifact 可以共享同一个 `base_project_version`，批内依赖按拓扑顺序解析，ProjectState 只增加一次版本。
- 注册操作通过 `ProjectStatePatch` 的 expected-version CAS 更新 `artifact_refs`；版本冲突、缺失依赖、非法跳版本或无效 Artifact 均不会写入 Registry 或 ProjectState。
- 同一 Artifact ref 和相同内容可幂等重放；相同 ref 携带不同内容明确拒绝，避免静默覆盖审计事实。
- 上游新版本发布后，直接依赖旧版本的当前 Artifact 标记 `dependency_superseded`，更下游 Artifact 递归标记 `dependency_stale`；每条 stale reason 保留明确依赖 ref，直接替代版本与传递失效不混淆。
- 下游按新依赖发布新版本后，当前版本恢复可用；旧 stale/superseded 版本仍可按 ref 查询和审计。
- ProjectState 在存在当前 stale Artifact 时写为 `validation_status=stale`；当前头部全部恢复后回到 `pending`，不在 ProjectGate 建立前伪称项目已通过验证。

聚焦自动验证：

```text
contracts + ProjectState + ArtifactRegistry：23 tests passed
批量原子注册 + 批内拓扑依赖：passed
直接/传递 stale propagation：passed
旧版本审计 + current usable guard：passed
幂等重放 + 同 ref 异内容拒绝：passed
项目版本、Artifact 版本、依赖与 invalid guard：passed
轨道 B Runtime/LANChat import isolation：passed
Python syntax compile：passed
git diff --check：无 whitespace error（仅现有 CRLF 提示）
```

当前任务状态：

```text
W3.3 GameProjectState 存储与版本迁移：code_complete
W3.4 ArtifactRegistry 与失效传播：code_complete
W3.5 AgentTaskGraph：ready
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁：

- AgentTaskGraph 的依赖、失败、重试、blocked 和 output refs 状态机（W3.5）。
- ArtifactRegistry 的跨进程持久化和多人传播；W3 第一阶段只提供协作层内存事实接口。
- 运行中的三职能 Agent、真实或 Mock Snapshot 输入、Coordinator、ProjectGate 和 ActionProposal。
- 本轮不改变轨道 A Gate；所有 Engine/Sync 效果仍为 **[待 F5/实机验证]**。

## 41. W4.4 五 Artifact 红灯阶段综合闭环

在 PlanningAgent、ArtAgent 和 ProgramAgent 的非执行型输出完成后，补齐 Red Gate 下的单业务任务图综合闭环。该闭环只聚合项目契约事实，不接入 Runtime、Snapshot、LANChat 或场景写入。

当前改动：

- 在 `contracts.py` 统一声明 Artifact 稳定 lineage，并明确 Red 阶段五类可产出 Artifact：`GameDesignBrief`、`LevelPlan`、`ArtDirection`、`SceneCompositionPlan`、`GameplayLogicPlan`。
- 三个职能 Agent 统一引用中心 lineage 映射，消除各模块重复字符串定义。
- 新增只读 `ProjectArtifactBundleReader`，从当前 `ProjectState + ArtifactRegistry + AgentTaskGraph` 构建不可执行的五 Artifact 项目方案包。
- 方案包校验当前任务图必须 completed、属于当前项目且仍是 active graph；每项 Artifact 必须是当前可用版本，并与 producer role、source task、项目引用和图输出一致。
- 方案包使用规范化 payload 计算确定性 SHA-256 content hash；相同项目事实重复读取产生相同结果，读取过程不修改 ProjectState、Registry 或 TaskGraph。
- 单一业务 DAG 按 `planning -> art -> program` 依赖顺序产出五类 Artifact；Program 只消费显式版本化策划输入与 ArtDirection。
- 策划 v2 发布后，旧美术与程序 Artifact 精确进入 stale；重新执行下游任务后形成完整 v2 方案包，旧版本进入 superseded。
- 美术任务失败时只重试失败节点；策划任务不重放，程序任务保持 blocked，待美术重试成功后继续。
- `EntityBindingPlan` 继续保持 schema-only，不进入 Red 阶段方案包；真实/Mock Snapshot、ProjectGate、ActionProposal 和 Runtime 写入仍未解锁。

聚焦自动验证：

```text
五 Artifact 单业务 DAG 与确定性方案包：passed
planning -> art -> program 依赖解锁：passed
策划 v2 触发下游 stale 并重建 v2：passed
失败美术任务定点重试且不重放策划：passed
方案包读取零状态副作用：passed
五类 Artifact 均保持 non_executable：passed
EntityBindingPlan 未提前生产：passed
Runtime/LANChat/Snapshot/SceneTools/ActionProposal/ToolCallGraph 静态隔离：passed
Python syntax compile：passed
agent_collaboration 聚焦回归：76 tests passed
```

当前任务状态：

```text
W4.1 PlanningAgent：code_complete
W4.2 ArtAgent：code_complete
W4.3 ProgramAgent：code_complete
W4.4 五 Artifact 红灯阶段综合闭环：code_complete
EntityBindingPlan：schema_only / Green 后 W5.2 解锁
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁：

- 三个 Reasoner 的生产模型适配与 CollaborationCoordinator 生产入口。
- 真实/Mock Snapshot 输入、EntityBindingPlan、ProjectGate、ActionProposal 和 Runtime 写入。
- 轨道 A 新一轮 F5 Gate 复评；所有 Engine/Sync 效果仍为 **[待 F5/实机验证]**。

## 37. W3.5 AgentTaskGraph 业务任务状态机

在 W3.4 的版本化 ArtifactRegistry 基础上，完成独立于 ToolCallGraph 和 AgentRuntime 的跨职能业务任务图。本轮只管理“哪个职能在什么依赖满足后产出哪类 Artifact”，不执行 Provider、Engine 或场景写入。

当前改动：

- 新增 `services/agent_collaboration/task_graph.py`，定义不可变 `AgentTaskGraph`、`AgentTaskRecord`、`TaskBlockReason` 和 `TaskGraphTransition`。
- `AgentTask` 增加显式 `max_attempts`；Record 的权威状态会同步到嵌套 Task，避免序列化后同时出现 `pending` 和 `in_progress` 两个事实。
- 建图时验证 task_id 唯一、depends_on 完整、输入 Artifact ref 显式带版本、依赖图无环；图定义和 project identity 共同参与幂等/冲突判断。
- 项目同一时刻只允许一个非 terminal active task graph；创建成功后通过 ProjectState CAS 写入 `active_task_graph_id`。
- 上游任务未完成时，下游保持 `pending`；上游完成且输入 Artifact 当前可用时才进入 `ready`。
- 上游失败/blocked、输入缺失或 stale 时，下游进入 `blocked` 并保留结构化原因，不会凭任务文本猜测继续执行。
- 单个任务支持 `ready -> in_progress -> completed/failed -> retry`；失败只重开责任任务，已完成上游不重跑，重试预算耗尽后明确拒绝。
- 任务完成前必须核验 output ref 存在、当前可用、`source_task_id` 匹配责任任务且覆盖声明的 output types；不能用其他 Agent 的 Artifact 冒充本任务结果。
- Artifact 更新后 `refresh()` 精确阻断依赖旧版本的已完成任务及其下游；`rebind_inputs()` 显式绑定新版本并清空旧输出后才重新 ready。
- 两个并发执行者竞争同一 ready task 时只有一个能进入 `in_progress`；状态迁移均有 graph version 和 transition history。
- 模块不导入 ToolCallGraph、RuntimeState、SceneWorldSnapshot、LANChat 或 Engine 接口。

聚焦自动验证：

```text
contracts + ProjectState + ArtifactRegistry + AgentTaskGraph：34 tests passed
三职能依赖顺序与完整 completed 闭环：passed
任务级失败/重试与预算耗尽：passed
stale input 精确阻断 + 版本 rebind：passed
output source/type/current version 门禁：passed
循环/未知依赖/跨项目 graph ID 冲突：passed
并发 ready task 原子认领：passed
迁移历史和 no-op refresh：passed
轨道 B Runtime/LANChat import isolation：passed
Python syntax compile：passed
```

当前任务状态：

```text
W3.1-W3.6 三职能强类型契约底座：code_complete
W4.1 策划 Agent 非执行型 Artifact 输出：ready
W4.2/W4.3 美术与程序 Agent：等待 W4.1
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁：

- W4 三职能 Agent 的结构化 Artifact 生产与纯契约协作闭环。
- 运行中的 Agent 不得读取真实或 Mock Snapshot；Red 状态下 W4.1 只能消费 ProjectState 和有效 Artifact。
- Coordinator、ProjectGate、ActionProposal、EntityBindingPlan 真实绑定和 Runtime 写入仍由 Green Gate 阻断。
- TaskGraph/Registry 的跨进程持久化与多人传播不属于 W3 第一阶段。
- 本轮不改变轨道 A Gate；所有 Engine/Sync 效果仍为 **[待 F5/实机验证]**。

## 38. W4.1 PlanningAgent 非执行型策划 Artifact 输出

在 W3 强类型契约、Registry 和 TaskGraph 完成后，实现第一个职能 Agent。该 Agent 通过可注入 `PlanningReasoner` 获取推理结果，但自身只处理项目级强类型输入和 Artifact，不注册 LANChat，不读取聊天流水、RuntimeState、Engine 或任何真实/Mock Snapshot。

当前改动：

- 新增 `services/agent_collaboration/agents/planning_agent.py` 和独立 agents 导出入口。
- 定义 `PlanningRequest`、`PlanningContext`、`PlanningArtifactContext`、`PlanningAgentDraft`、`PlanningAgentResult` 与 `PlanningReasoner` Protocol。
- PlanningRequest 只包含明确项目目标、约束、验收条件、project/graph/task identity 和请求来源，不接受聊天历史或场景对象。
- PlanningContext 只包含 ProjectState 的项目版本和当前有效 planning Artifact；不携带 `scene_world_version`，避免 Red 状态下策划契约间接绑定 Runtime 世界事实。
- PlanningAgent 要求责任任务属于 planning 且声明 `GameDesignBrief + LevelPlan` 两种输出；任务非 ready 时拒绝推理。
- Reasoner 必须返回强类型 `PlanningAgentDraft`；输出再经过现有 Artifact schema Validator，不能用一段 prompt 文本冒充契约。
- 输出使用稳定 lineage `planning.game-design-brief` 和 `planning.level-plan`，自动计算下一版本；LevelPlan 显式依赖同批 GameDesignBrief。
- 两种 Artifact 通过 ArtifactRegistry 原子注册并由 AgentTaskGraph 校验 source_task、类型和当前可用性后，策划任务才进入 completed。
- 推理期间 ProjectState 版本变化会抛出 `PlanningContextStaleError`，任务记录失败且不登记过期输出。
- 同 project/request ID 的完全相同请求幂等返回；相同 ID 携带不同内容明确拒绝。
- 当前 planning Artifact 若来自 `mock` 或 `runtime` snapshot source，Agent 在调用 Reasoner 前以 `PlanningIsolationError` 拒绝，避免测试 fixture 或世界绑定 Artifact 被静默洗入策划链。
- 策划版本更新后，Registry 会使依赖旧 LevelPlan 的美术 Artifact 精确 stale，为 W4.2 返工提供事实依据。
- 本轮 reasoner 通过依赖注入测试，没有注册生产 LLM/LANChat 入口，也没有 ActionProposal 或 Runtime 写入能力。

聚焦自动验证：

```text
contracts + ProjectState + ArtifactRegistry + TaskGraph + PlanningAgent：42 tests passed
GameDesignBrief + LevelPlan 原子产出与 TaskGraph completed：passed
schema invalid / reasoner 非结构化输出失败：passed
项目版本并发变化拒绝过期输出：passed
Mock/Runtime source 在 Reasoner 前隔离：passed
请求幂等与同 ID 异内容冲突：passed
策划 v2 触发下游美术 Artifact stale：passed
非执行 Artifact assert_executable 拒绝：passed
Runtime/LANChat/Snapshot 静态与 import isolation：passed
Python syntax compile：passed
```

当前任务状态：

```text
W3.1-W3.6 三职能强类型契约底座：code_complete
W4.1 PlanningAgent：code_complete（可注入 reasoner，无生产入口）
W4.2 ArtAgent：ready
W4.3 ProgramAgent 非执行输出：ready
W4.4 Artifact 综合闭环：等待 W4.2/W4.3
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁：

- W4.2 ArtAgent 的 `ArtDirection + SceneCompositionPlan` 强类型输出。
- W4.3 ProgramAgent 的 `GameplayLogicPlan` 非脚本输出。
- W4.4 六 Artifact 端到端任务图、版本返工和综合验收。
- PlanningReasoner 的生产模型适配和 CollaborationCoordinator 入口；Red 状态下继续不注册 LANChat。
- 真实/Mock Snapshot 输入、EntityBindingPlan、ProjectGate、ActionProposal 和 Runtime 写入仍由 Gate 阻断。
- 本轮不改变轨道 A Gate；所有 Engine/Sync 效果仍为 **[待 F5/实机验证]**。

## 39. W4.2 ArtAgent 非执行型美术 Artifact 输出

在 W4.1 策划 Artifact 闭环基础上，实现第二个职能 Agent。该 Agent 只消费任务显式绑定的当前有效 `GameDesignBrief@version + LevelPlan@version`，通过可注入 `ArtReasoner` 形成强类型美术契约，不读取 RuntimeState、Engine、聊天历史或任何真实/Mock Snapshot。

当前改动：

- 新增 `services/agent_collaboration/agents/art_agent.py`，并从独立 agents 包导出。
- 定义 `ArtRequest`、`ArtContext`、`ArtInputArtifactContext`、`ArtAgentDraft`、`ArtAgentResult` 与 `ArtReasoner` Protocol。
- ArtRequest 只包含 project/graph/task identity、明确美术目标、约束、验收条件和请求来源，不接受聊天流水或场景对象。
- ArtAgent 要求责任任务属于 `art` 且精确声明 `ArtDirection + SceneCompositionPlan` 两种输出。
- 输入必须显式包含且仅包含一个当前有效、由 planning 角色产生的 GameDesignBrief 和 LevelPlan；缺失、重复、非当前或其他类型在 Reasoner 前拒绝。
- Red Gate 下，任何 `snapshot_source=mock/runtime` 的策划输入均以 `ArtIsolationError` 拒绝；输入同时必须保持 `non_executable=true`。
- Reasoner 必须返回强类型 `ArtAgentDraft`；风格、调色板、灯光、避用项、场景类型、环境需求、实体需求和布局规则继续经过 Artifact schema Validator。
- 输出使用稳定 lineage `art.direction` 与 `art.scene-composition` 并自动计算下一版本。
- ArtDirection 显式依赖两个策划版本；SceneCompositionPlan 同时依赖两个策划版本和同批 ArtDirection，二者通过 ArtifactRegistry 原子注册。
- AgentTaskGraph 在 source_task、声明类型和当前可用性检查通过后才将美术任务置为 completed。
- 推理期间 ProjectState 版本变化会抛出 `ArtContextStaleError`，任务记录失败且不登记过期产物。
- 同 project/request ID 的相同请求幂等返回；相同 ID 携带不同内容明确拒绝。
- 策划 v2 发布后，依赖 v1 的 ArtDirection/SceneCompositionPlan 精确 stale；重新绑定 v2 后可发布美术 Artifact v2。
- 本轮 reasoner 仅依赖注入测试，没有注册生产 LLM/LANChat 入口，也没有 Provider、SceneTools、ActionProposal 或 Runtime 写入能力。

聚焦自动验证：

```text
ArtAgent 专项：13 tests passed
contracts + ProjectState + ArtifactRegistry + TaskGraph + PlanningAgent + ArtAgent：55 tests passed
GameDesignBrief/LevelPlan -> ArtDirection/SceneCompositionPlan 跨 Agent 闭环：passed
缺失/stale/重复/非策划输入在 Reasoner 前拒绝：passed
schema invalid / reasoner 非结构化输出失败且零 Artifact 发布：passed
项目版本并发变化拒绝过期输出：passed
Mock/Runtime source 在 Reasoner 前隔离：passed
请求幂等与同 ID 异内容冲突：passed
策划 v2 精确 stale 美术 v1，并允许美术 v2 重建：passed
非执行 Artifact assert_executable 拒绝：passed
Runtime/LANChat/Snapshot/SceneTools/ActionProposal 静态隔离：passed
Python syntax compile：passed
```

当前任务状态：

```text
W3.1-W3.6 三职能强类型契约底座：code_complete
W4.1 PlanningAgent：code_complete（可注入 reasoner，无生产入口）
W4.2 ArtAgent：code_complete（可注入 reasoner，无生产入口）
W4.3 ProgramAgent 非执行输出：ready
W4.4 Artifact 综合闭环：等待 W4.3
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁：

- W4.3 ProgramAgent 的 `GameplayLogicPlan` 非脚本输出。
- W4.4 六 Artifact 端到端任务图、版本返工和综合验收。
- PlanningReasoner/ArtReasoner 的生产模型适配和 CollaborationCoordinator 入口；Red 状态下继续不注册 LANChat。
- 真实/Mock Snapshot 输入、EntityBindingPlan、ProjectGate、ActionProposal 和 Runtime 写入仍由 Gate 阻断。
- 本轮不改变轨道 A Gate；所有 Engine/Sync 效果仍为 **[待 F5/实机验证]**。

## 40. W4.3 ProgramAgent 非执行型 GameplayLogicPlan 输出

在 W4.1/W4.2 强类型策划与美术契约基础上，实现第三个职能 Agent。该 Agent 是规则设计器而非代码执行器，只消费任务显式绑定的当前有效 Artifact，并产出非执行 `GameplayLogicPlan`；不读取 RuntimeState、Engine、聊天历史或任何真实/Mock Snapshot。

当前改动：

- 新增 `services/agent_collaboration/agents/program_agent.py`，并从独立 agents 包导出。
- 定义 `ProgramRequest`、`ProgramContext`、`ProgramInputArtifactContext`、`ProgramAgentDraft`、`ProgramAgentResult` 与 `ProgramReasoner` Protocol。
- ProgramRequest 只包含 project/graph/task identity、明确逻辑目标、约束、验收条件和请求来源，不接受脚本、聊天流水或场景对象。
- ProgramAgent 要求责任任务属于 `program` 且只声明 `GameplayLogicPlan` 输出。
- 必需输入为当前有效且由 planning 角色产生的 GameDesignBrief 与 LevelPlan；可选输入仅允许当前有效且由 art 角色产生的 ArtDirection。
- SceneCompositionPlan、重复类型、错误 producer、缺失或 stale Artifact 在 Reasoner 前拒绝。
- Red Gate 下，任何 `snapshot_source=mock/runtime` 输入均以 `ProgramIsolationError` 拒绝；输入必须保持 `non_executable=true`。
- Program 任务能力集只允许 `artifact.read/artifact.write` 且必须声明 `artifact.write`；shell、Engine、脚本执行或 Actor 修改能力在 Reasoner 前拒绝。
- Reasoner 必须返回强类型 `ProgramAgentDraft`；states、triggers、rules、win_conditions 和 lose_conditions 继续经过 Artifact schema Validator。
- 输出使用稳定 lineage `program.gameplay-logic-plan` 并自动计算下一版本；依赖精确记录所有显式输入版本。
- ArtifactRegistry 登记成功且 AgentTaskGraph 校验 source_task、声明类型和当前可用性后，程序任务才进入 completed。
- 推理期间 ProjectState 版本变化会抛出 `ProgramContextStaleError`，任务记录失败且不登记过期产物。
- 同 project/request ID 的相同请求幂等返回；相同 ID 携带不同内容明确拒绝。
- 策划版本更新会精确 stale GameplayLogicPlan；当程序逻辑显式引用 ArtDirection 时，美术版本更新同样精确触发 stale，并可重建 v2。
- 本轮 reasoner 仅依赖注入测试，没有注册生产 LLM/LANChat 入口，也没有 EntityBindingPlan、ScriptBundle、ActionProposal 或 Runtime 写入能力。

聚焦自动验证：

```text
ProgramAgent 专项：17 tests passed
contracts + ProjectState + ArtifactRegistry + TaskGraph + 三职能 Agents：72 tests passed
GameDesignBrief/LevelPlan -> GameplayLogicPlan：passed
可选 ArtDirection 显式依赖：passed
缺失/stale/错误类型/错误 producer 输入在 Reasoner 前拒绝：passed
禁止 capability 和缺少 artifact.write：passed
schema invalid / reasoner 非结构化输出失败且零 Artifact 发布：passed
项目版本并发变化拒绝过期输出：passed
Mock/Runtime source 在 Reasoner 前隔离：passed
请求幂等与同 ID 异内容冲突：passed
策划/美术版本更新精确 stale 程序产物并允许 v2 重建：passed
非执行 Artifact assert_executable 拒绝：passed
Runtime/LANChat/Snapshot/SceneTools/ActionProposal/EntityBinding 静态隔离：passed
Python syntax compile：passed
```

当前任务状态：

```text
W3.1-W3.6 三职能强类型契约底座：code_complete
W4.1 PlanningAgent：code_complete（可注入 reasoner，无生产入口）
W4.2 ArtAgent：code_complete（可注入 reasoner，无生产入口）
W4.3 ProgramAgent：code_complete（可注入 reasoner，无生产入口）
W4.4 五 Artifact 红灯阶段综合闭环：ready
EntityBindingPlan：schema_only / Green 后 W5.2 解锁
当前 Gate：red / pending_reevaluation
```

以下仍未实现或未解锁：

- W4.4 五 Artifact 端到端业务任务图、版本返工和综合验收。
- 三个 Reasoner 的生产模型适配和 CollaborationCoordinator 入口；Red 状态下继续不注册 LANChat。
- 真实/Mock Snapshot 输入、EntityBindingPlan、ProjectGate、ActionProposal 和 Runtime 写入仍由 Gate 阻断。
- 本轮不改变轨道 A Gate；所有 Engine/Sync 效果仍为 **[待 F5/实机验证]**。

## 42. W1.3 Late-ready Actor 选择性 Grounding Reconcile

旧 F5 的 `3/14 Game-ready` 证据中，部分普通 Actor 已被 Engine 接受，但真实 AABB 晚于首次导入结果到达。现有 late-ready reconcile 会补齐 `bounds_ready / bounds_source=engine_actual`，却保留导入早期的 `grounding_status=needs_review`，导致已经实际贴地的地面实体仍无法进入 Game-ready。

本轮改动：

- 在 `_reconcile_partial_engine_readiness()` 完成原生 Scene Snapshot 后，仅检查本轮待 reconcile 批次中的 Actor。
- 仅当 `support_type=floor_supported`、AABB 为 `engine_actual`、`bounds_ready=true` 且 AABB 底面与地面高度误差不超过 `0.05m` 时，将 grounding 事实提升为 `grounded`。
- 墙挂、吊挂、系统对象、未知支撑类型和真实浮空对象保持原状态，不移动 Actor，不伪造接地。
- Grounding 更新通过 `runtime.engine_readiness.reconcile -> ToolResult -> StatePatch -> RuntimeState` 写回；该工具显式声明 `actors` 写集合，继续受 RuntimeGuard 约束。
- OperationLog 增加 `grounding_reconciled_count`，用于下一轮 F5 对账。

聚焦自动验证：

```text
Late-ready floor-supported Actor -> grounded -> Game-ready：passed
wall_mounted / 实际浮空 Actor 不被误判 grounded：passed
跨历史批次 native actor_id / AABB reconcile：passed
Game-ready + R3 Readiness 聚焦套件：33 tests passed
Python syntax compile：passed
```

当前 Gate：

```text
red / pending_reevaluation
旧基准：3/14 Game-ready
代码断点：late actual AABB 后 grounding 不更新，已修复
实机效果：待新一轮儿童卧室 F5 重新运行 runtime.r3_readiness.evaluate
```

本轮不能证明已经达到 `8/14`。下一步固定使用儿童卧室场景重新 F5，核对 `grounding_reconciled_count`、逐实体 `readiness_missing_fields`、Registry、Snapshot 与 R3GateReport；所有 Engine 效果仍为 **[待 F5/实机验证]**。

## 43. W1.4 Finalizer 同版本终态证据闭环

现有 Finalizer 已产生 Registry、Consistency Audit、Snapshot 和 Report 事件，但 R3 Gate 原先只检查事件名称是否在同一计划历史中出现以及最后位置是否有序，没有验证这些事件属于同一个 `scene_version`。这允许旧 Registry、新 Snapshot 和另一版本 Report 被错误拼接成绿色证据。

本轮改动：

- Finalizer 的 `finalizer_started`、`tool_graph_queue_empty` 和 `scene_plan_finalized` 统一写入当前 `scene_version`。
- `report_ready/report_pending` 的用户可见 RuntimeEvent 同步携带最终 `SceneWorldSnapshot.scene_version`。
- Registry、Consistency Audit 和 Snapshot 原有版本事实保留，七个终态节点现在可以按同一版本对账。
- `runtime.r3_readiness.evaluate` 的 `finalizer_completeness` 不再跨版本拼事件，而是以最新 versioned `report_ready` 为目标，查找同版本的完整有序链：

```text
finalizer_started
-> tool_graph_queue_empty
-> scene_plan_finalized
-> scene_entity_registry_ready
-> runtime_scene_world_consistency_audited
-> scene_world_snapshot_ready
-> report_ready
```

- 缺少版本证据返回 `finalizer_scene_version_missing`；事件存在但版本不同返回 `finalizer_scene_version_mismatch`；同版本但顺序错误返回 `finalizer_event_order_invalid`。
- 旧 F5 证据不会因事件名称齐全而自动变绿，必须由新代码重新实机产生同版本闭环。

聚焦自动验证：

```text
R3 Finalizer 混合 scene_version 拒绝：passed
Registry -> Snapshot -> Report 同版本有序闭环：passed
同 scene_version 终态事件幂等：passed
final report 写入失败后下一 drain 重试：passed
report_pending 不冒充 terminal report：passed
Finalizer/R3 专项：12 tests passed
Game-ready + R3 Readiness 套件：34 tests passed
Python syntax compile：passed
```

当前 Gate：

```text
red / pending_reevaluation
finalizer_completeness 代码约束：已收口
旧 F5 终态版本证据：不足，保持 red
新 F5 同版本终态链：待实机验证
```

下一步按优先级进入 `business_graph_consistency`，检查一个业务 Batch 是否严格对应一个 terminal `business_batch` ToolGraph；所有 Engine/Sync/终态实机效果仍为 **[待 F5/实机验证]**。

## 44. W1.5 Business Batch 与 Principal ToolGraph 一对一收口

旧 F5 曾出现少量业务批次对应大量 ToolCallGraph 的矛盾统计。代码核查确认，`enqueue_planned_batches()` 原先采用整组判断：只有全部未完成批次都已有 `queued/running` 图时才整体复用；只要一个批次缺图，就会为全部未完成批次重新创建业务图。这会重复提交仍在执行的批次，也会把已完成业务图、但仍等待 Engine late-ready 的 `partial` 批次重新跑一遍资源链路。

本轮改动：

- `BatchPlan.tool_graph_id` 现在被视为该批次稳定的 principal business graph 身份。
- `enqueue_planned_batches()` 改为逐批解析：已有合法 principal graph 的批次一律复用，仅为没有主图的待执行批次创建新图。
- `partial BatchPlan + completed business graph` 被识别为 Engine readiness 收尾状态，不重新执行图片、模型、导入链路。
- 显式失败重试继续复用现有 `graph_id`，由既有 `retry_generation` 增加 `generation`，OperationLog 保留尝试历史。
- 主图事实缺失、plan/batch/role 身份不一致、active graph 缺 queue fact 或 graph/queue 状态冲突时明确失败并记录诊断事件，不再静默生成第二张业务图。
- 混合状态下记录 `planned_batches_enqueue_partial_reuse`，可对账复用图数和新建图数。
- 返回结果按 BatchPlan 顺序列出每个批次的 principal graph，避免只返回新建图造成调用方统计失真。

聚焦自动验证：

```text
混合“已有主图 + 缺图”仅补一个 principal graph：passed
partial batch + completed graph 不重跑资源链路：passed
悬空 principal graph 引用明确失败且不创建第二图：passed
原子入队、介入吸收回滚与失败重试 generation：passed
业务图域报告与 R3 Gate 回归：14 tests passed
Game-ready + R3 Readiness 套件：34 tests passed
Python syntax compile：passed
```

当前 Gate：

```text
red / pending_reevaluation
business_graph_consistency 代码约束：已收口
旧 F5 的 5 批/151 图证据：不满足，保持 red
新 F5 的 BatchPlan/principal graph 一对一事实：待实机验证
```

下一步按优先级进入 `snapshot_integrity`，核实同一 `plan_id + scene_version` 的 Snapshot 是否不可变、Fingerprint 是否稳定，以及 Registry/Snapshot/Report 是否引用同一版本；所有 Engine/Sync 实机效果仍为 **[待 F5/实机验证]**。

## 45. W1.6 SceneWorldSnapshot 同版本不可变收口

代码核查确认，终态 `SceneWorldSnapshot` 过去只嵌在 Report 中，没有独立的版本化事实集合；查询接口会把任意终态 Report 中的同版本 Snapshot 标为 immutable，却没有校验 Fingerprint，也无法阻止同一 `plan_id + scene_version` 被后续不同内容覆盖。原世界指纹只覆盖 Engine 可观测的身份、Transform 和 AABB，未覆盖下游 Agent 实际消费的语义、接地、交互、玩法和同步事实。

本轮改动：

- RuntimeState 新增 `scene_world_snapshots`，以 `plan_id@v<scene_version>` 保存终态不可变 Snapshot。
- 终态 Report 与 Snapshot 原子写入；相同内容幂等复用，不同内容返回 `scene_world_snapshot_version_conflict`，禁止覆盖。
- `SceneWorldSnapshotRecordValidator` 校验计划、版本、authority、实体 ID 唯一性、Readiness 摘要和 SHA-256 Fingerprint。
- Registry 增加 `scene_version`，Report 持久化时强制 Registry、Snapshot、Consistency Audit 和 PlanSummary 使用同一版本。
- `scene_world_fingerprint()` 扩展为下游 Agent 世界契约指纹；另设 `scene_materialization_fingerprint()` 专门用于 Runtime 与 Engine 可观测事实对账，避免混淆两种职责。
- Snapshot 与 Report 使用深拷贝；调用方修改返回对象不能反向污染 RuntimeState。
- 查询优先读取专用冻结 Snapshot；旧 Report 内 Snapshot 仅标记为 `legacy_report`，校验失败时返回明确 integrity failure，不再冒充 immutable。
- Finalizer 的 Registry、Snapshot 与 Report 事件补充同版本 `world_fingerprint`，便于 F5 对账。

聚焦自动验证：

```text
Fingerprint 顺序稳定且覆盖 Agent 语义契约：passed
同版本终态 Snapshot 幂等复用与深拷贝隔离：passed
同版本不同内容覆盖拒绝：passed
旧 Report Snapshot 降级为 legacy_report：passed
Game-ready + R3 Readiness 套件：37 tests passed
Finalizer/Report 持久化关键回归：passed
Python syntax compile：passed
```

当前 Gate：

```text
red / pending_reevaluation
snapshot_integrity 代码约束：已收口
旧 F5 Snapshot 证据：不满足新不可变契约，保持 red
新 F5 Registry/Snapshot/Report/Fingerprint 同版本事实：待实机验证
```

下一步按轨道 A 优先级进入 `environment_readiness`，核实室内 `room_box/room_floor`、室外 terrain 和混合 transition zone 是否以真实 Engine-ready 环境实体进入 Registry 与 Snapshot；所有 Engine/Sync 实机效果仍为 **[待 F5/实机验证]**。

## 46. W1.7 Environment Readiness 契约与稳定身份收口

代码核查确认，Environment 链路存在三个会直接阻断 R3 Gate 的事实断点：配置了外部环境 fact provider 后，Runtime 会完全采用其返回值，导致 SceneDesignContract 要求的 `room_box/room_floor/terrain/transition_zone` 可能被吞掉；Registry 先根据 `requires_engine_write=False` 把环境实体标为 `not_applicable`，覆盖了 floor、terrain、room shell 的真实支撑语义；环境 Actor GUID 依赖当前业务 `batch_id`，provider 重建或跨批次补录时可能产生新身份。

本轮改动：

- `runtime.environment.create_components` 在外部 provider 成功后仍统一应用 SceneDesignContract 的 framework fallback；室内稳定补齐 `room_box + room_floor`，室外补齐 terrain，混合场景补齐 terrain、room shell、floor 与 transition zone。
- 显式 substrate 请求仍保持严格失败语义：外部 provider 未解析任何请求项时继续失败，不用默认组件掩盖真实 provider 断点。
- Registry 的环境支撑语义改为 component type 优先：`room_floor/terrain/ground/transition_zone -> grounded`，`room_box/room_shell -> enclosure`；只有其他无几何写入需求的环境事实才使用 `not_applicable`。
- 环境 Actor GUID 改为 plan-level 稳定身份，不再纳入业务批次；`source_batch_id` 仍记录本次物化来源，便于 OperationLog 对账。
- provider 内缓存继续避免同一进程重复导入；即使 provider 重建导致缓存丢失，同一 `plan_id + component_id + asset_id` 仍解析到相同 `actor_guid/entity_id`。

聚焦自动验证：

```text
外部 provider 不得吞掉 indoor/mixed 必需 framework components：passed
环境导入缺失/部分失败阻断普通 Actor：passed
floor/room shell/transition zone 支撑语义与 Game-ready 判定：passed
provider 重建及跨业务批次环境身份稳定：passed
Environment 聚焦回归：7 tests passed
Game-ready + R3 Readiness 套件：37 tests passed
git diff --check：clean（仅既有 CRLF 提示）
```

当前 Gate：

```text
red / pending_reevaluation
environment_readiness 代码约束：已收口
旧 F5 环境实体证据：不足，保持 red
新 F5 的真实 room_box/room_floor/terrain/transition zone、Engine-ready 与 Snapshot 事实：待实机验证
```

下一步进入 `multiplayer_consistency` 前，先按固定儿童卧室、森林营地和混合场景执行新一轮 F5，核对 Environment Actor、RuntimeState、Registry、Snapshot 与 Report 五方身份和 readiness；所有 Engine/Sync 实机效果仍为 **[待 F5/实机验证]**。

## 47. W1.8 Multiplayer Snapshot Identity ACK 闭环

本轮推进 Gate 维度：`multiplayer_consistency`。

此前同步状态只能证明“发生过同步事件”，不能证明房主端与成员端实际持有相同的实体身份和版本；同时，安全事件过滤会丢弃实体指纹、实体数量和漂移计数，使 R3 Gate 可能基于弱证据误判。

本轮完成：

- 房主 Snapshot 增加确定性实体身份指纹，输入仅包含 `entity_id / actor_id / asset_id / actor_version / source_plan_id / source_scene_version`。
- 成员应用 Snapshot 后发送 `peer_ack`，回传房主/成员指纹、预期/已应用/partial 数量、身份漂移和版本漂移计数。
- 成员在模型晚到并完成 Actor 创建后刷新 ACK；房主轮询期周期性重算 Snapshot，并用 hash 去重避免重复广播。
- C++ NetworkSystem 将 `peer_ack` 转为 `scene_snapshot_peer_ack`，且不再把 ACK 放回前端 Snapshot 队列，避免形成应用循环。
- Runtime 同步事件白名单保留上述安全证据；R3 Gate 只接受明确 ACK 或 peer mirror 证据，普通 `peer_connected/syncing` 事件不再被当作身份一致性证明。
- peer mirror Registry 与房主 Snapshot 使用同一 `scene_version`，避免镜像构建阶段制造假版本漂移。

验证证据：

```text
Python compile：passed
multiplayer / native sync / R3 readiness 聚焦测试：20 tests passed
Game-ready + multiplayer + native sync + R3 readiness 扩展聚焦测试：49 tests passed
RoomPanel <script setup> JavaScript 语法解析：passed
git diff --check：clean（仅既有 CRLF 提示）
Frontend ESLint：未执行，当前工作区未安装 @eslint/js
Native C++ build：未执行
F5 多人实机：未执行
```

当前 Gate：

```text
red / pending_reevaluation
multiplayer_consistency 代码证据链：已补齐
真实房主/成员 Snapshot ACK、实体落地后的指纹一致性、无重复 Actor/无 ACK 循环：待 F5 验证
```

所有真实 Engine、网络传输与多人一致性效果仍为 **[待 F5/实机验证]**。下一轮应先执行固定多人 F5，对账房主/成员的 `entity_id / asset_id / version / identity_fingerprint`，再根据新 GateReport 决定是否从红灯切换为黄灯或绿灯。

## 48. R3 Gate 聊天室只读诊断入口

代码核查确认，`runtime.r3_readiness.evaluate` 已经具备七维聚合、确定性输出和零副作用测试，但此前只存在于 AgentRuntime 内部接口与测试中。下一轮 F5 若仍依赖人工拼接 RuntimeState、Registry、Snapshot 和日志，既容易漏项，也无法稳定复现红黄绿判定。

本轮完成：

- 新增窄口径 GM 查询：`@GM R3门禁`、`@GM R3 Gate`、`@GM R3 readiness`。
- 查询直接调用 `runtime.r3_readiness.evaluate`，不经过 LLM、Coordinator 写链、PlanPatch、ToolCallGraph 或 Provider。
- 聊天室返回总体 Gate、scene version、Game-ready 数量以及七个维度的红黄绿状态。
- 阻塞项只展示前三项并给出剩余计数；能力解锁项读取 GateReport，不根据聊天历史猜测。
- 新增安全日志 `[R3GateTrace]`，仅记录 room/plan/version、维度状态、Game-ready 计数、阻塞数量和 report ID，不记录实体明细、Provider 或内部 URL。
- 普通 Agent 或不明确的“检查门禁”不会命中该入口，避免扩大控制词规则面。

聚焦验证：

```text
Python syntax compile：passed
GM R3 Gate 零副作用与 Coordinator 绕过：passed
AgentRuntime R3 Readiness 回归：passed
聚焦套件：9 tests passed
Native C++ build：未执行
F5 实机 Gate 输出：未执行
```

当前 Gate：

```text
red / pending_reevaluation
R3GateReport 聊天室证据入口：code_complete
旧 F5 基线：3/14 Game-ready，不满足新 Gate 契约
新一轮儿童卧室、森林营地、混合场景和多人 F5：待执行
```

下一轮 F5 在每个场景 Finalizer 后发送 `@GM R3门禁`，保存聊天室输出和对应 `[R3GateTrace]`；只有新代码产生的 GateReport 可以决定红灯是否升级。所有真实 Engine、多人同步和 Game-ready 效果仍为 **[待 F5/实机验证]**。

## 49. W1.3 Completed Batch 接地事实补录

继续核查 `entity_readiness` 时确认，已有的 late-ready 修复只会选择 `partial` 批次，或仍缺少 `engine_actual` AABB 的 `completed` 批次。如果一个批次已经完成、Actor 已持有真实 AABB，但导入早期留下的 `grounding_status=needs_review` 尚未更新，Finalizer 会因为“bounds 已齐”而跳过整个批次。这样实际底面已经与地面接触的普通地面物体仍无法进入 Game-ready。

本轮改动：

- `batch_needs_reconcile()` 除 bounds 缺失外，也检查是否存在“可由真实 AABB 直接证明已贴地”的 floor-supported Actor。
- 仅当 `bounds_ready=true`、`bounds_source=engine_actual`、支撑类型为 `floor_supported`，且 AABB bottom 与地面误差不超过 `0.05m` 时重新纳入 reconcile。
- 仍通过 `runtime.scene.snapshot -> runtime.engine_readiness.reconcile -> ToolResult -> StatePatch -> RuntimeState` 写回，不直接修改 RuntimeState。
- 墙挂、吊挂、未知支撑类型和真实浮空对象不会因为本次修改被提升为 grounded。
- 已经具有合法 grounding 的实体不会重复进入该分支，避免无意义的持续 reconcile。

聚焦验证：

```text
completed batch + engine_actual AABB + 实际贴地 + needs_review -> grounded：passed
partial batch late-ready -> grounded -> Game-ready：passed
wall_mounted / 真实浮空 Actor 不被误判：passed
Game-ready + R3 Readiness 聚焦套件：37 tests passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示）
F5 实机：未执行
```

当前 Gate：

```text
red / pending_reevaluation
entity_readiness completed-batch grounding 断点：code_complete
旧 F5 基线：3/14 Game-ready
新 F5 中 grounding_reconciled_count 与 Game-ready 提升：待验证
```

本轮没有移动 Actor，也没有放宽 `engine_actual`、Engine verification、稳定资源身份或 sync 事实要求。下一轮儿童卧室 F5 仍需通过 `@GM R3门禁` 和逐实体 `readiness_missing_fields` 证明是否达到 `8/14`；所有 Engine 接地与 Game-ready 效果仍为 **[待 F5/实机验证]**。

## 50. W1.4 Finalizer `report_ready` 同版本持久化闭环

继续核查 `finalizer_completeness` 时确认，终态报告会先写入 RuntimeState，再尝试写入 `report_ready` RuntimeEvent；Finalizer 过去只检查报告是否存在，即使事件 StatePatch 失败，也会设置 `latest_completed_plan_id` 并清空 `active_execution_plan_id`。此外，`RuntimeEventValidator` 的安全字段白名单会剥离 `scene_version`，导致正常写入的 `report_ready` 也无法成为 R3 Gate 所要求的同版本终态证据。

本轮改动：

- RuntimeEvent 安全 payload 明确保留数值型 `scene_version`，仍继续剔除 Provider、URL、路径、密钥和内部工具字段。
- Finalizer 在清理执行计划前，必须从 RuntimeState 找到当前 `plan_id + scene_version` 的 `report_ready` 事件。
- 报告已存在但终态事件缺失时，基于已持久化报告重发最小终态事件，不重复执行 Engine 写入。
- 事件仍无法持久化时，计划恢复为 `executing`，保留 `active_execution_plan_id`，发布 `report_pending` 并等待下一次零 drain 重试。
- 恢复成功后记录 `scene_plan_report_ready_event_recovered`，随后才设置 latest completed 并清理 active execution。

聚焦验证：

```text
report 持久化失败后零 drain 重试：passed
report_ready StatePatch 持续失败时不清理 execution plan：passed
恢复后同版本 report_ready 写入并完成 Finalizer：passed
RuntimeEvent 安全过滤回归：passed
Finalizer 顺序 + R3 Readiness：9 tests passed
Finalizer/RuntimeEvent 聚焦回归：4 tests passed
Python syntax compile：passed
F5 实机：未执行
```

当前 Gate：

```text
red / pending_reevaluation
finalizer_completeness 同版本事件闭环：code_complete
旧 F5 终态事件缺少新 scene_version 证据，不可用于升级 Gate
新 F5 的 finalizer_started -> report_ready 同版本序列：待验证
```

下一轮按轨道 A 优先级进入 `business_graph_consistency`，核对业务 Batch 与 `business_batch` ToolGraph 的数量、归属、节点终态和查询零污染；所有 Engine、多人同步和真实 Finalizer 效果仍为 **[待 F5/实机验证]**。

## 51. W1.5 R3 Gate 业务图角色、归属与节点终态收紧

复核既有 principal business graph 一对一闭环时确认，执行层已经能够拒绝悬空 principal graph 和错误 graph identity，但 `runtime.r3_readiness.evaluate` 的只读判定仍存在两处宽松口径：被 Batch 引用的 `internal_state/query_snapshot` 图也会被计入业务图；已经标记 terminal 的图不会检查节点是否仍停留在 `planned/ready/running`。这会让错误图角色、错误归属或未真正收尾的节点被误判为 `business_graph_consistency=green`。

本轮改动：

- `business_graph_consistency` 只把 `graph_role=business_batch` 的图计入业务图数量，query、review、finalizer 和 internal 图不再污染业务统计。
- 每个 Batch 的 `tool_graph_id` 必须解析到真实图，且图的 `plan_id / batch_id / graph_role` 必须与 Batch 一致。
- 独立的 orphan `business_batch` 图明确列为 contradiction，不通过减少审计事实来让数量看起来一致。
- terminal business graph 必须保留非空节点事实；节点必须处于 `succeeded / failed / blocked / skipped` 之一，`planned / ready / running` 会被判定为 active contradiction。
- GateReport 增加业务节点总数以及 succeeded、failed、blocked、skipped、active 状态计数，F5 不再需要人工从完整 ToolGraph 日志拼接节点状态。
- `blocked / incomplete` 图按执行器现有失败终态语义识别为 terminal；本轮不改变图执行器和失败策略。

聚焦验证：

```text
R3 Readiness Gate（含角色、归属、orphan、节点终态、query 零污染）：11 tests passed
Game-ready / 报告图分域回归：29 tests passed
principal graph 缺图补建、partial 复用、悬空引用拒绝：passed
Python syntax compile：passed
F5 实机：未执行
```

当前 Gate：

```text
red / pending_reevaluation
business_graph_consistency 严格事实判定：code_complete
旧 F5 的业务图统计不满足新角色/节点终态证据口径，不可用于升级 Gate
新 F5 的 Batch/principal graph/terminal node 对账：待验证
```

下一步按轨道 A 顺序复核 `snapshot_integrity`，重点确认同一 `plan_id + scene_version` 的 Registry、Snapshot、Consistency Audit 与 Report 是否引用同一 Fingerprint；所有真实 Engine、多人同步和终态效果仍为 **[待 F5/实机验证]**。

## 52. W1.6 Engine Snapshot 同计划同版本身份闭环

复核 `snapshot_integrity` 时确认，冻结的 `SceneWorldSnapshot` 已具备不可变记录和世界 Fingerprint，但 Engine 对账仍存在一个同版本漏洞：`latest_engine_snapshot()` 在目标版本不存在时允许回退到 `scene_version=0` 的 legacy Engine Snapshot；随后 consistency audit 又使用世界 Snapshot 的 `plan_id + scene_version` 替该旧 Engine Snapshot 计算 materialization fingerprint。这样旧版或跨计划 Engine 事实在 Actor 内容恰好相同时，可能冒充当前版本的一致性证据。

本轮改动：

- consistency audit 独立读取并保留世界与 Engine 两侧各自的 `plan_id + scene_version`，不再使用世界版本替 Engine 版本计算 Fingerprint。
- Engine Snapshot 缺少 plan/version、plan 不一致或 scene version 不一致时，明确写入 `snapshot_identity_issues` 并返回 `needs_review`。
- audit 输出 `engine_plan_id / engine_scene_version / plan_id_matches / scene_version_matches`，供 Finalizer、报告和 R3 Gate 统一消费。
- `snapshot_integrity` 维度增加 Engine plan/version 匹配指标和明确 contradiction；Actor 内容完全相同也不能掩盖版本漂移。
- 保留 `latest_engine_snapshot()` 的 legacy 读取能力用于旧状态诊断，但 legacy 事实不再具备证明当前版本一致性的资格。
- 本轮没有修改冻结 Snapshot 写入、Engine 查询、RuntimeState 或 final report 主链。

聚焦验证：

```text
当前版本 Runtime/Engine Snapshot 一致：passed
scene_version=0 legacy Engine Snapshot 不得证明 v3 世界：passed
跨 plan Engine Snapshot 不得证明当前世界：passed
R3 Gate 对跨版本 Engine Snapshot 判 red：passed
Game-ready + Snapshot + R3 Readiness：42 tests passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示）
F5 实机：未执行
```

当前 Gate：

```text
red / pending_reevaluation
snapshot_integrity Engine plan/version 身份约束：code_complete
旧 F5 的 legacy/缺版本 Engine Snapshot 证据不可用于升级 Gate
新 F5 的 Registry/Snapshot/Engine Audit/Report 同版本 Fingerprint：待验证
```

下一步按轨道 A 顺序复核 `environment_readiness`，重点确认必要环境实体的 stable entity identity、真实 Engine AABB、support semantics 与 Snapshot 版本是否同时满足 Gate；所有真实 Engine、多人同步和环境渲染效果仍为 **[待 F5/实机验证]**。

## 53. W1.7 Environment Readiness 硬事实重算与 Actor 身份收口

复核既有 Environment framework、稳定 GUID 和支撑语义修复后确认，生成与 Registry 链路已经能够表达 `room_box / room_floor / terrain / transition_zone`，但 R3 Gate 与 Engine readiness reconcile 仍有两个可信性缺口：`environment_readiness` 只读取 Snapshot 中已经计算好的 `game_ready` 布尔值，没有独立核验必要环境实体的 Engine Actor 身份、真实 AABB 和 component-specific support；Engine readiness polling 在 `actor_id` 未命中时仍按显示名称匹配，可能把同名旧 Actor 的几何事实写到当前环境实体。

本轮改动：

- `environment_readiness` 不再仅相信 `game_ready=True`，而是从 `SceneWorldSnapshot.environment_entities` 重新核验 `entity_id / actor_id / asset_id / model_ref / version / transform / world_aabb / bounds_source / Engine verification / support / sync`。
- 必要环境实体只有 `bounds_source=engine_actual`、`engine_write_verification_status=engine_verified` 且无 `readiness_missing_fields` 时才计入 ready。
- 支撑语义按组件类型独立检查：`room_box -> enclosure`，`room_floor / terrain / transition_zone -> grounded`，sky 类为 `not_applicable`。
- GateReport 增加逐环境实体 `component_diagnostics`，可直接定位 `room_floor:engine_actual_aabb`、`room_box:grounding_status` 等阻断项，不再人工拼接 Registry 与 Snapshot。
- 对 `room_shell / indoor_enclosure / walkable_floor / ground / transition` 做通用 canonical alias 归一，不为单一测试场景写特例。
- Engine readiness reconcile 删除名称匹配兜底，只接受稳定 `actor_id`；同名但 actor_id 不同的旧 Actor 不得让当前环境实体晋升为 Engine-ready。

聚焦验证：

```text
环境 game_ready 布尔值与 Engine AABB/support 事实冲突时 Gate 判 red：passed
room_shell 等 canonical alias 仍能匹配契约组件：passed
同名但 actor_id 不同的 Engine Actor 不得提供 readiness：passed
既有真实环境导入与支撑语义回归：passed
Game-ready + R3 Readiness + Environment adapter：46 tests passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示）
F5 实机：未执行
```

当前 Gate：

```text
red / pending_reevaluation
environment_readiness 硬事实与稳定 Actor 身份判定：code_complete
旧 F5 的 3/14 Game-ready 与 legacy 环境证据不可用于升级 Gate
新 F5 的 room_box/room_floor/terrain/transition_zone 真实 Engine Actor、AABB 与 support：待验证
```

下一步进入 W2 固定场景 F5 Vertical Slice，先执行儿童卧室，使用 `runtime.r3_readiness.evaluate` 自动核对 Engine Actor、RuntimeState、OperationLog、Registry、Snapshot 与 final report；若仍为 red，只修 GateReport 指向的首个真实环境或实体 readiness 断点。所有真实 Engine、多人同步与渲染效果仍为 **[待 F5/实机验证]**。

## 54. W1.8 普通实体 Readiness 硬事实重算

W2 F5 前置核查发现，Registry 已经会依据 Engine verification、真实 AABB、稳定资源身份、支撑和同步状态计算 `game_ready`，但 `runtime.r3_readiness.evaluate` 的 `entity_readiness` 仍直接累计该布尔值。若 Registry 行出现 `game_ready=true` 与 `bounds_source=estimated`、Engine 未验证、支撑未知或同步 partial 等公开字段相互矛盾，Gate 仍可能把该实体计入卧室 `8/14` 门槛，导致自动对账失去独立校验价值。

本轮改动：

- `entity_readiness` 从 Registry 的公开、Engine-backed 字段重新核验 `entity_id / actor_id / asset_id / model_ref / version / entity_type / semantic_role / transform / world_aabb / bounds_source / Engine verification / grounding / sync`。
- Gate 不会自行把实体提升为 Game-ready；只有 Registry 已声明 ready 且重算无缺失时才计入核验数量。
- “声明 ready 但缺少硬事实”进入 `game_ready_without_hard_facts` contradiction，并在逐实体诊断中列出具体字段。
- 非 ready 实体仍必须由 Registry 提供 `readiness_missing_fields`；Gate 重算结果不能替 Registry 掩盖缺失原因。
- GateReport 同时输出 `declared_game_ready_entity_count` 与核验后的 `game_ready_entity_count`；顶层聊天室摘要读取核验值，不再出现维度为 `7/14`、摘要仍显示 `8/14` 的双口径。
- `readiness_missing_field_counts` 改为由本次硬事实核验结果确定性计算，不再直接转抄 Registry 聚合值。

聚焦验证：

```text
Game-ready + R3 Readiness：45 tests passed
GM R3 Gate 只读查询回归：1 test passed
普通家具 game_ready=true + estimated AABB -> 不计入 Game-ready、Gate 判 red：passed
声明计数 8、核验计数 7 的顶层/维度口径一致：passed
Python syntax compile：passed
F5 实机：未执行
```

F5 证据边界：

```text
最新现有日志：2026-07-14_04-51-51_corona.log
本轮 Gate 修复提交时间：2026-07-14 08:24-08:47 之后
结论：现有日志早于当前代码，不得用于升级 Gate
verify_ultimate_plan.py：旧 phase1 长超时路径运行约 1 小时 50 分钟后终止，不作为通过证据
```

当前 Gate 保持：

```text
red / pending_reevaluation
entity_readiness 硬事实独立核验：code_complete
旧基线：3/14 Game-ready
当前代码的儿童卧室 GateReport：待新 F5
```

下一步严格进入 W2.1 儿童卧室 F5。必须保存运行日志与代码 commit、room/plan/version、Engine Actor 摘要、OperationLog cursor、Registry、Snapshot fingerprint、final report 和 `@GM R3门禁` 输出；若仍为 red，只处理 GateReport 指向的第一个实机事实断点。所有真实 Engine、渲染、接地和多人效果仍为 **[待 F5/实机验证]**。

## 55. W2.1 儿童卧室 F5：Snapshot 终态版本断点

有效 VSCode F5 日志：

```text
build/examples/engine/RelWithDebInfo/logs/2026-07-14_13-28-28_corona.log
Runtime plan: plan-2bde99becad5
Scene version: 4
```

本轮实机证据：

```text
业务批次：3/3 terminal
业务 ToolGraph：3/3 terminal
ToolCall：54/54 succeeded，0 failed
Runtime entities：9（environment 2 + actor 7）
核验 Game-ready：6/14（实际场景 6/9）
Engine bridge：13/13 success，0 failed
Environment readiness：green
Finalizer completeness：green
Business graph consistency：green
Runtime write safety：green
Entity readiness：yellow
Snapshot integrity：red
Overall Gate：red
```

结论：当前代码已把环境、执行图、Finalizer 与写权限边界跑通，Game-ready 从旧基线 `3/14` 提升到 `6/14`；但最终 Registry/SceneWorldSnapshot 仍可能与批次早期 Engine Snapshot 对账。原 Finalizer 在 readiness reconcile 后直接选择已有快照，没有按终态 `plan_id + scene_version` 重新采集 Engine 事实，因此最终 v4 世界可能与旧批次快照发生 identity/fingerprint 冲突。

本轮小修：

- Finalizer 仅在计划进入 terminal 时，按显式 `plan_id + scene_version` 刷新一次 Engine Snapshot。
- 刷新发生在 Registry、SceneWorldSnapshot 和 consistency audit 之前，不修改 Provider、C++ 导入或业务 ToolGraph。
- 执行仍处于 partial/96% 时不反复刷新，避免继续膨胀 internal graph。
- R3 trace 增加前三个 `blocker_codes`，下一次 F5 可直接定位 Snapshot、实体或多人维度的具体缺失事实。
- 增加 Finalizer 必须以终态计划身份刷新快照的回归断言。

聚焦验证：

```text
Game-ready tests：30 passed
R3 Readiness tests：15 passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示）
```

本次日志还暴露一个后续控制面断点：同一条 `@GM R3门禁` 先被 Native Queue 处理，随后又被 Agent Task 处理，产生两条回复和两个 report id；第二条路径末尾还出现一次零事实 RuntimeEvidence。该问题不影响本轮 Snapshot 修复的代码边界，列入 W2.1 下一断点。

当前 Gate：

```text
red / snapshot_fix_pending_f5
四个基础维度已由本次 F5 证明为 green
entity_readiness：yellow，6/14
finalizer terminal-version Engine Snapshot refresh：code_complete
Snapshot fingerprint 一致性：待下一次 F5 验证
GM R3 查询双入口幂等：待修复
```

下一次 F5 优先复用同类卧室场景并执行 `@GM R3门禁`。必须核对 `blocker_codes`、Snapshot plan/version/fingerprint、Registry 计数和重复回复；Snapshot 转为 yellow/green 后，再处理 GM 查询双入口幂等与剩余 3 个 `grounding_status` 缺失。所有本轮 Engine Snapshot 一致性改进仍标记 **[待 F5/实机验证]**。

## 56. W2.1 GM R3 查询双入口原子收口

`2026-07-14_13-28-28_corona.log` 同时记录了：

```text
Native Queue 对 @GM R3门禁 执行一次 runtime.r3_readiness.evaluate 并回复
随后 Agent Trigger 对同一 message_id 再执行一次并回复
两次 R3GateReport 使用相同 plan/version/facts，但产生两条用户消息
第二条路径完成后还输出一次零事实 RuntimeEvidence
```

代码链复核确认：Native Queue 的 structured GM route 会同步调用 `_process_trigger()`，但该分支此前没有先写入 `MessageDispatchLedger`；R3 Gate 查询又不属于已有的确认、拒绝、暂停协议，因而不会进入 `_gm_control_message_ids` 去重集合。Agent Trigger 随后看到消息未被认领，便完整执行第二次。

本轮改动：

- structured GM route 在调用 `_process_trigger()` 前，以 `room_id + message_id` 原子认领消息。
- Native Queue 为权威 owner，route 记录为 `gm_control`；处理成功后状态写为 `replied`。
- Agent Trigger 入口继续使用既有 Ledger 终态检查，命中同一消息时直接返回，不调用 Runtime、不回复第二次。
- 该收口覆盖 R3 Gate、GM 总结和其他 structured GM 只读控制，不改变确定性确认/拒绝协议，也不扩大到普通 RoleAgent 消息。

聚焦验证：

```text
Game-ready/消息幂等：31 tests passed
structured GM target 优先路由：passed
裸 GM 确认双队列去重：passed
Python syntax compile：passed
```

当前结论：

```text
GM R3 查询双入口幂等：code_complete
单次 Runtime evaluate + 单条权威回复：自动测试通过
Native Queue / Agent Trigger 实机单回复：[待 F5/实机验证]
Snapshot terminal refresh：[待 F5/实机验证]
```

下一次 F5 的同一条 `@GM R3门禁` 应只出现一个 `R3GateTrace` 和一条回复；若仍重复，直接根据 `message_dispatch_deduped`、owner、route 和 blocker_codes 定位，不再扩展新的去重集合。

## 57. W2.1 Entity Readiness：支撑语义统一

`2026-07-14_13-28-28_corona.log` 的终态事实为：

```text
Runtime entities：9（environment 2 + actor 7）
Game-ready：6/14
readiness_missing：grounding_status x3
Engine bridge：13/13 success
```

结合本次保留的 7 张混元输入图和 Actor 导入顺序，普通对象依次属于：衣柜、书桌、床、地毯、台灯、玩偶、书架。旧代码在 Runtime import、geometry review 和 layout reflow 三处各维护一份名称规则，前四类可识别为 `floor_supported`，台灯、玩偶和书架落为 `unknown`；因此 13 次 Engine 写入可解释为 `2 environment + 7 actor create + 4 ground transform`，与 3 个 grounding 缺失完全对应。

本轮改动：

- 新增共享 `support_semantics.classify_support_type()`，统一 import、ground review 和 layout reflow。
- 补齐台灯/落地灯、玩偶/玩具、书架/书柜等通用地面支撑语义。
- 保持严格优先级：吊灯/悬挂物先判 `ceiling_hung`，壁灯/墙饰先判 `wall_mounted`，不会因包含“灯”而统一落地。
- 显式 `support_type` 优先于名称推断，允许上游结构化语义覆盖规则 fallback。
- 分类结果只决定 support domain；只有 Engine actual AABB 证明 bottom 接触地面，或 Engine ground transform 返回成功，才能写入 `grounding_status=grounded`。
- `estimated` AABB、浮空 AABB、挂墙/悬挂和 unknown 对象不得伪造 grounded。

聚焦验证：

```text
Support semantics + Game-ready：36 passed
AgentRuntime phase1：2 passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示）
```

日志还存在 4 次 `GeometrySystem: invalid mesh slot skipped`。这证明当前 `engine_accepted/load_finished` 尚不能完整代表 render-ready；该问题先作为下一 Gate 事实断点记录，不在本轮 support/grounding 修改中顺带改 C++。

当前 Gate 保持：

```text
red / pending_reevaluation
entity support semantic closure：code_complete
台灯、玩偶、书架 ground transform + actual AABB：[待 F5/实机验证]
预期 Game-ready：若三者 Engine 事实成立，可由 6/14 提升至 9/14
invalid mesh render readiness：待独立诊断
```

## 58. W2.1 Entity Readiness：真实可渲染几何门禁

用户提供的 VSCode F5 日志仍为：

```text
build/examples/engine/RelWithDebInfo/logs/2026-07-14_13-28-28_corona.log
日志结束时间：2026-07-14 14:05:18
```

该日志早于以下修复提交：

```text
d9dc806f 2026-07-14 14:15:22 terminal Engine Snapshot refresh
6173c9a9 2026-07-14 14:18:55 structured GM query dedupe
1695c56b 2026-07-14 14:28:39 unified entity support semantics
```

因此它是修复前基线，不能用于验证 Snapshot 终态刷新、GM 单回复或支撑语义修复。日志中仍有以下有效问题证据：

```text
GeometrySystem load finished：存在
GeometrySystem invalid mesh slot skipped：4 次
OpticsSystem skipped invalid mesh draw：存在
render_status_observed/render_ready：未进入 Runtime 事实
RuntimeEvidence：Game-ready 6/14，grounding_status 缺失 3 个
R3GateTrace：2 次，Snapshot integrity red
```

其中无效 mesh slot 的 vertex/index/storage buffer 均为 false，但旧 `get_editor_actor_geometry_status_from_python()` 只检查 `gpu_build_state == Ready` 和 `mesh_count > 0`。这会把“Actor 已加载但当前没有有效可绘制 mesh slot”错误计为 Engine-ready，进而污染 Registry、SceneWorldSnapshot 和 R3GateReport。

本轮改动：

- 在 C++ `Geometry` API 增加只读 `GeometryRenderStatus`，通过 `GeometrySystem::query_mesh_slots()` 统计可绘制和无效 mesh slot。
- CEF Actor Snapshot 输出 `render_status_observed`、`render_ready`、`render_failed`、`gpu_build_state`、`mesh_count`、`renderable_mesh_count` 和 `invalid_mesh_count`。
- Runtime actor/environment import 与 late-ready reconcile 保留上述真实 Engine 字段。
- `engine_verified` 和 `game_ready` 现在同时要求 actual AABB 与真实 render-ready；无效 slot 不再被伪装为 Game-ready。
- R3 readiness 对未观测和不可渲染实体分别输出 `render_readiness_unobserved`、`render_not_ready`。
- 不修改资源生成、LOD 切换、渲染或 Engine 写入链路；本轮只补真实事实观测与门禁。

聚焦验证：

```text
Game-ready + R3 readiness + support semantics：52 tests passed
Python syntax compile：passed
RelWithDebInfo corona_engine 增量构建：passed
新增回归：actual AABB 存在但 mesh slot 无效时不得 Game-ready
```

当前 Gate 保持：

```text
red / pending_reevaluation
真实 render readiness bridge：code_complete
Snapshot terminal refresh：code_complete
GM structured query dedupe：code_complete
support semantics closure：code_complete
上述四项真实 Engine/UI 效果：[待 F5/实机验证]
```

下一次 F5 必须使用包含本节改动的新构建，并核对：

```text
Actor Snapshot 中出现 render_status_observed/render_ready/invalid_mesh_count
无效 mesh slot 对应实体进入 needs_review，而不是 Game-ready
台灯、玩偶、书架不再缺 grounding_status（以实际 AABB/ground transform 为准）
同一条 @GM R3门禁 只有一个 R3GateTrace 和一条回复
Snapshot plan/version/fingerprint 与终态 Registry 一致
```

## 59. W2.1 R3GateReport：Render Readiness 自动对账

在真实 render readiness bridge 落地后，R3 聚合器虽然已经能逐实体识别 `render_readiness_unobserved` 和 `render_not_ready`，但顶层 Gate 摘要此前只披露 Game-ready 总数。若下一次 F5 仍有无效 mesh，仍需要人工展开 Registry 才能区分“未观测”“不可渲染”和“支撑状态缺失”。

本轮改动：

- `entity_readiness.metrics` 增加渲染观测数、渲染就绪数、失败数、无效 mesh 实体数和无效 slot 总数。
- `R3GateReport.metrics` 提升同一组聚合指标，并提升 `readiness_missing_field_counts`，供后续 runtime doctor 与 ProjectGate 只读复用。
- GM R3 门禁回复同时显示基准 Game-ready 分母和当前实际实体渲染分母，避免把“14 个基准目标”和“9 个已存在实体”混为同一统计口径。
- `R3GateTrace` 直接记录 render、render_observed、invalid_mesh 和 entity_missing 摘要，下一轮日志可以自动对账，不再人工关联 GeometrySystem warning。
- 普通 `needs_review` 仍按既有阈值进入 yellow/red；渲染诊断指标不会被错误写成身份矛盾，也不会改变 RuntimeState。

预期用户可见摘要：

```text
场景版本：vN；Game-ready：6/14
渲染就绪：7/9（已观测 9/9；无效 Mesh 实体 2，slot 3）
实体待检查：grounding_status x3；render_not_ready x2
```

聚焦验证：

```text
Game-ready + R3 readiness + support semantics + GM 只读披露：55 tests passed
R3 查询零 Runtime 写入：passed
渲染聚合口径与无效 mesh 统计：passed
```

当前 Gate 不变：

```text
red / pending_reevaluation
R3 render readiness 自动对账：code_complete
真实 Engine 字段与用户摘要：[待 F5/实机验证]
```

## 60. W1.4 Finalizer Completeness：自动收尾退避与熔断

最新 F5 日志：

```text
build/examples/engine/RelWithDebInfo/logs/2026-07-14_18-47-10_corona.log
```

该轮三个业务图均失败后，自动 worker 继续对空队列执行 Finalizer；内部图数量从 85 增长到 352，最终报告与 `report_ready` 未形成可信终态。上一断点已修复 Environment render-ready 字段在 C++ 安全桥、Adapter 和 Validator 之间的契约丢失，本节只收敛 Finalizer 的自动重试放大。

本轮改动：

- `final_report_persist_pending` 与 `report_ready_event_persist_pending` 保留自动恢复语义，但采用 1/2/4/8 秒指数退避，最长不超过 30 秒。
- 同一计划连续 4 次收尾持久化失败后，暂停该房间的自动 drain，记录 `runtime_finalizer_retry_exhausted`；不伪造 `report_ready`，不把失败计划声明为完成。
- 若同一 ScenePlan 后续出现新的 queued/running ToolGraph，自动解除收尾暂停，避免阻断真实追加批。
- 正常一次失败后恢复、零 drain 晚到 `report_ready`、正常终态清理房间的既有语义保持不变。

聚焦验证：

```text
Finalizer backoff/circuit-breaker Worker tests: 3 passed
Transient report persistence retry: passed
Missing report_ready recovery retry: passed
Python syntax compile: passed
git diff --check: clean（仅既有 CRLF 提示）
```

当前 Gate：

```text
red / pending_reevaluation
Environment render-ready 字段闭环：code_complete
Finalizer 自动重试退避与熔断：code_complete
真实业务图完成、Registry/Snapshot/report_ready 终态：[待 F5/实机验证]
```

下一次 F5 重点核对：三个业务图应不再在 Environment 状态写入节点失败；正常成功时必须出现完整 Finalizer 终态事件。若报告持久化仍失败，内部图不得继续无界增长，并应出现一次 `runtime_finalizer_retry_exhausted` 审计事实。

## 61. W2.2 R3 F5 日志自动对账探针

新增只读工具 `docs/probes/r3_f5_log_check.py`，直接消费 `R3GateTrace` 与
`LANChatRuntimeEvidence`，不导入 AgentRuntime，不修改 RuntimeState、OperationLog 或 Engine。

自动输出：

- 七个 R3 Gate 维度的最新 red/yellow/green 状态。
- 业务 BatchPlan 与 business ToolGraph 数量、终态对账。
- 业务终态后 internal graph 增长量与 Finalizer 熔断证据。
- Game-ready、render-ready 与 render observation 摘要。

旧基线回放：

```text
2026-07-14_18-47-10_corona.log
R3_F5_BLOCKED: PASS=2 WARN=2 FAIL=7
business batches/graphs=3/3
terminal internal graph growth=267
render ready/observed=0/2
```

聚焦验证：

```text
R3 log probe unit tests: 3 passed
Python syntax compile: passed
old F5 baseline replay: correctly blocked
```

当前 Gate 不变：`red / pending_reevaluation`。新代码的 Engine、Registry、Snapshot
和 Finalizer 效果仍为 `[待 F5/实机验证]`。

## 62. W1.4/W1.2 最新 F5：Render 二层投影断链与 Finalizer 空转

实机日志：

```text
build/examples/engine/RelWithDebInfo/logs/2026-07-14_21-18-25_corona.log
```

自动对账结果：

```text
R3_F5_BLOCKED: PASS=2 WARN=2 FAIL=7
business batches/graphs=3/3
business nodes=54 succeeded=54 failed=0
Game-ready=0/14
render ready/observed=0/8
terminal internal graph growth=3822 (99 -> 3921)
runtime_finalizer_retry_exhausted=0
```

本轮确认业务 ToolGraph、混元资源生成和 C++ Actor 导入均已执行；日志中 `room_box`、
`room_floor` 与普通模型均出现 GeometrySystem load/GPU resource ready 证据。红灯来自两个
收尾断点，而不是业务批次失败：

1. C++ Snapshot 与 `adapters.py` 已携带 render readiness，但
   `agent_runtime/tools.py::_normalize_snapshot_actors()` 再次丢弃
   `render_status_observed/render_ready/mesh_count` 等字段，导致 Registry 仍为 0/8 observed。
2. 三个业务图完成后，BatchPlan 处于 `engine_readiness_pending`；Worker 熔断只识别报告
   持久化 pending，未识别 Engine readiness pending，因此每次空 drain 都重复创建约 10 个
   internal graph，并持续发送重复的部分完成状态。

本轮修复：

- Runtime scene snapshot 投影保留完整 render readiness 字段。
- Engine import readiness 只通过稳定 `actor_id` 或 `entity_id` 对账；禁止按名称、模型路径或
  资产相似度猜测 Actor 归属。
- `engine_readiness_pending` 纳入 Finalizer 1/2/4/8 秒有界退避与四次熔断，避免内部图和
  用户状态消息无限增长；不伪造 `report_ready`。
- 历史 finalizer fixture 补齐新的 render-ready 强约束，并保留同名不同 Actor 不得误绑定测试。

聚焦验证：

```text
Game-ready + R3 readiness suites: 50 passed
snapshot render projection / stable entity matching / no same-name claim / finalizer backoff: 4 passed
late-ready finalizer recovery and historical batch identity reconciliation: passed
Python syntax compile: passed
```

当前 Gate 继续保持：

```text
red / pending_reevaluation
render readiness 二层投影修复：code_complete
engine_readiness_pending 有界退避：code_complete
真实 render observed/Game-ready/Finalizer terminal： [待 F5/实机验证]
```

下一次 F5 必须核对：`render_observed > 0`、`internal graph` 在业务终态后不再无界增长、
必要环境实体进入 ready，并出现 Registry/Snapshot/report_ready 的可信终态事件。

## 63. W1.2 F5 前置核验：Native `created` 与 Engine-ready 事实脱节

在 `f56dae61` 的 Render Snapshot 投影和 Finalizer 有界重试修复后，F5 provider 聚焦回归仍
报告一个 `actor_import` readiness mismatch。测试事实显示普通 Actor 已同时具备：

```text
stable actor_id
engine_actual AABB
engine_lifecycle_status=bounds_ready
render_status_observed=true
render_ready=true
```

但 C++ 导入返回的同步生命周期仍为 `created`。Registry 的 Engine write 判定此前只接受
`engine_created/engine_imported/...`，因此将这类已经被原生 Snapshot 独立证明就绪的 Actor
保留为 `engine_write_verification_status=unknown`。这会导致上一节字段投影修好后，普通模型
仍无法进入 Game-ready。

本轮修复严格限定为：只有 actual bounds、render observation、render-ready 和 ready lifecycle
四项同时成立时，`sync_status=created` 才可计为 `engine_verified`。单独的 handle 或 created
返回仍不代表 Engine ready，也不能进入 Game-ready。

同时更新 F5 provider fixture，使其显式模拟 native render readiness，不再用旧的
handle/AABB-only 事实冒充完整 Engine 终态。

聚焦验证：

```text
Game-ready + R3 readiness + F5 provider bridge + Finalizer backoff：52 passed
Python syntax compile：passed
旧 F5 日志探针：R3_F5_BLOCKED PASS=2 WARN=2 FAIL=7（符合修复前基线）
```

当前 Gate 仍为：

```text
red / pending_reevaluation
native created + actual render-ready reconcile：code_complete
真实普通 Actor Game-ready 与 Finalizer 终态：[待 F5/实机验证]
```

下一次 F5 除上一节检查项外，还必须确认普通 Actor 的
`engine_write_verification_status=engine_verified`，不能只看到 Environment ready。

## 64. 2026-07-15 开发中断审计

7 月 15 日的开发没有沿用一个可比较的 F5 基线完成收口。对日志、Git 历史和原推进记录
重新核对后，当前以以下事实替代原先损坏的 64-83 节：

```text
最后一个强实机基线：2026-07-14_23-38-14_corona.log
结果：3/3 业务批次、54/54 节点、9 个实际实体 Game-ready、R3 9/14

中断日志：2026-07-15_01-15-38_corona.log
结果：3/3 业务图失败、没有混元请求、仅 room_box/room_floor、R3 0/14
直接原因：Quasar 与 plugins.AITool.Quasar 配置命名空间重复
```

该次失败后继续开发了 Provider 命名空间、Finalizer、Engine observation、Environment
reconcile、多人 fingerprint 和轨道 B 契约，但没有先完成同脚本、同场景、同门禁的 F5
复验。完整门禁后续出现 `11 failures / 21 errors` 时，开发仍继续推进，最终大量改动被合并
进单个提交 `7d441c9e`。这造成三个工程问题：

- 运行时修复、协作层契约和文档同时进入一个提交，失去有效 bisect 粒度。
- 推进记录的 UTF-8 内容被错误改写，大量汉字变成 `?`，审计信息不再可信。
- 文档中的“代码完成”多于实机证据，7 月 15 日之后的完成声明不能视为 F5 通过。

因此 Gate 回退为：

```text
red / pending_reevaluation
Track B 契约代码：保留，但不解锁真实 Snapshot/ActionProposal
Track A Runtime：以新的最小 F5 重新建立可信基线
```

## 65. 2026-07-17 同事实机日志暴露的问题

日志 `2026-07-17_01-12-26_corona.log` 证明混元请求、环境 OBJ 和 Native Actor 创建仍可运行，
但该轮不是与 7 月 14 日相同脚本的受控对照，并暴露以下阻断：

1. 角色方案回复尚未完成时，用户发送“确定生成”；系统把确认文本重新交给 Agent/GM，
   生成了以“确定生成”为设计目标的新 proposal。
2. 同一讨论先后出现多个 Runtime plan ID，角色回复没有稳定补充到最初 discussion plan。
3. Runtime Evidence 在最终报告不存在时只读取 `report`，把已有实体、操作和 Engine import
   打印为 0。
4. Runtime 的语义 `scene_name` 被传入 Native scene route。Native reader 在场景入口路由和
   语义名称之间反复 reload，持续销毁并重建 Geometry；日志出现 8656 次 async import、
   3693 次 upload queued 和 1864 次 published。
5. 日志记录了完整混元签名 URL，存在凭据和资源地址泄露风险。
6. 本轮没有 `R3GateTrace`、`snapshot_ready` 和 `report_ready`，不能宣称闭环完成。

## 66. 2026-07-17 当前修复批次

本批次只修上述控制面和可观测性断点，不改混元生成、RuntimeGuard、EngineWriteGate 或
场景导入主协议：

- Native scene route 只接受当前场景别名或真实存在的 `.scene` 文件；只读 Snapshot 不再
  使用 Runtime 语义场景名选择 C++ 场景。
- Runtime Evidence 在无最终报告时合并 `query_state.summary` 的实时事实。
- 同房间角色方案回复仍在执行时，“确认生成/确定生成”在 LLM 和 GM proposal 前被阻断。
- 角色回复优先复用 `active_discussion_plan_id` 对应的 external plan，不再按新 correlation
  创建平行 discussion plan。
- 混元完成日志仅保留 task/request/status/resource count/error code，不再输出签名 URL。

验证边界：

```text
Python 聚焦测试：28 个用例通过（Runtime/控制面 16 + 模型导入 12）
Python syntax compile：passed
C++ cef_editor_native_api_handlers.cpp RelWithDebInfo object compile：passed
完整 corona_ui_system 目标：依赖重编译超过本轮 5 分钟预算，未完成链接
Geometry 不再重载、Snapshot/Report 终态： [待 F5/实机验证]
```

下一次 F5 先使用最小场景：

```text
room_box + room_floor + 1 个普通模型
```

只核对一次 Actor 创建、稳定 actor_id/model_ref、actual AABB、非零 Runtime Evidence、
`snapshot_ready/report_ready`。该最小闭环通过后，再恢复儿童卧室三批与多人 F5。

## 67. 2026-07-18 黑盒期单人垂直切片子计划启动

```text
时间 / commit：2026-07-18 / working tree（未形成新提交）
任务 ID / 状态：B0 文档准备 / code_complete
里程碑状态：not_ready
Full R3 Gate before / after：red -> red（无实机新证据）
Single-player Demo Gate before / after：unavailable -> unavailable
```

完成断点：

- 当时新增黑盒期单人垂直切片子计划，建立 B0-B7 一周执行链；该子计划后被权威计划取代并清理。
- 计划采用端到端 Walking Skeleton 优先策略，不按模块逐个纵深开发。
- 更新 Agent 约束循环，支持 B 编号、黑盒 Preflight、双 Gate、integration status 和单人能力解锁。
- 明确继续使用本文件作为唯一推进记录，不创建第二份并行进度事实源。

验证证据：

```text
Track B 聚焦测试：81 passed
R3 readiness 聚焦测试：21 passed
组合运行：102 tests / 3 failures
失败原因：隔离测试依赖被其他测试污染的 sys.modules，待 B0.2 修复
文档 UTF-8 / diff check：passed
```

待 F5 / 阻断：

```text
最新 Native scene route、Runtime Evidence 和 Finalizer 修复：[待 F5/实机验证]
Engine 稳定 24 小时 SHA：未提供
Frontend 稳定候选接口：未提供
Single-player Demo Gate：尚未实现和评估
```

下一批可选任务：

```text
B0.1 基准 SHA、改动清单与干净合并门禁
B0.2 集中 schema version（B0.1 完成后）
B0.3 BlockedResult 与节点清单（B0.2 完成后）
```

## 68. 2026-07-18 Walking Skeleton 与双层 AI 串行规则收口

```text
时间 / commit：2026-07-18 / working tree（未形成新提交）
任务 ID / 状态：B0 计划修订 / code_complete
执行角色：架构 AI
里程碑状态：not_ready
Full R3 Gate before / after：red -> red（无实机新证据）
Single-player Demo Gate before / after：unavailable -> unavailable
Skeleton contract version/hash：r3-skeleton-week1-v1 / unavailable
```

完成断点：

- B0 顺序调整为 `B0.1 干净门禁 -> B0.2 集中版本 -> B0.3 统一阻断诊断 -> B0.4 Walking Skeleton`。
- B0.1 吸收 3 项 `sys.modules` 隔离测试误报修复，已知噪声不得进入骨架阶段。
- 规划 `services/schema_versions.py` 作为 Python domain version 的唯一登记点。
- 规划统一 BlockedResult、SkeletonNodeStatus 和 SkeletonStatusReport，所有阻断必须说明缺失条件、责任域和下一动作。
- 执行方式固定为架构 AI 与填充 AI 串行交接；填充 AI 不得修改冻结接口。
- 需要 F5 的节点只能阻断依赖它的下游；允许继续无实机依赖的独立节点。

验证证据：

```text
计划、约束循环与推进记录三方口径已对齐
当前代码基线仍为：Track B 81 passed；R3 readiness 21 passed
组合门禁 3 项误报尚未修复，属于 B0.1 实施任务
本节只记录计划修订，不新增代码完成声明
```

待 F5 / 阻断：

```text
Skeleton 尚未实现，contract hash 与节点状态表不可用
Engine / Frontend 稳定集成 SHA 尚未冻结
最新 Runtime / Native 修复仍为 [待 F5/实机验证]
```

下一批可选任务：

```text
B0.1 基准 SHA、Adapter 影响表与干净合并门禁
B0.2 集中 schema version（仅在 B0.1 完成后）
B0.3 BlockedResult 与节点清单（仅在 B0.2 完成后）
```

## 69. 2026-07-18 结构化依赖、契约 Hash 与接口变更交接收口

```text
时间 / commit：2026-07-18 / working tree（未形成新提交）
任务 ID / 状态：B0 诊断与交接契约修订 / code_complete
执行角色：架构 AI
里程碑状态：not_ready
Full R3 Gate before / after：red -> red（无实机新证据）
Single-player Demo Gate before / after：unavailable -> unavailable
Skeleton contract version/hash：r3-skeleton-week1-v1 / unavailable
Interface change request / decision：none / none
```

完成断点：

- `missing_requirements` 改为结构化 `MissingRequirement(requirement_id, owner_domain, description)`，填充 AI 不再解析自然语言判断依赖。
- Skeleton hash 明确基于规范化 `SkeletonContractManifest`，覆盖公共 Protocol、DTO、枚举、schema version、节点 ID 和边顺序。
- `SkeletonStatusReport` 只引用 hash，不参与 hash 计算；注释、格式化和私有实现变化不应改变 hash。
- 新增 InterfaceChangeRequest / InterfaceChangeDecision 交接协议。
- 填充 AI 发现接口不足时必须停止并提交请求；只有架构 AI 可以决定接口是否变化。
- 接受公共接口变更后必须升版本、重算 hash、重跑 B0.4，并将旧 hash 下游节点标记 stale。

验证证据：

```text
三份权威文档的 MissingRequirement、Manifest/hash 和接口变更口径已统一
本节仅修改计划和执行规约，不新增代码完成声明
```

待 F5 / 阻断：

```text
MissingRequirement、SkeletonContractManifest 和 InterfaceChange DTO 尚未实现
Skeleton contract hash 仍不可用
当前无 InterfaceChangeRequest，因为填充阶段尚未开始
```

下一批可选任务：

```text
B0.1 基准 SHA、Adapter 影响表与干净合并门禁
B0.2 集中 schema version（B0.1 完成后）
B0.3 结构化诊断与接口交接 DTO（B0.2 完成后）
```

## 70. 2026-07-18 B0.1 基准与干净门禁完成

```text
时间 / commit：2026-07-18 / agent-native@7d441c9e（working tree）
任务 ID / 状态：B0.1 / verified
执行角色：架构 AI
里程碑状态：not_ready
Full R3 Gate before / after：red -> red（无实机新证据）
Single-player Demo Gate before / after：unavailable -> unavailable
Skeleton contract version/hash：r3-skeleton-week1-v1（计划值） / unavailable
Interface change request / decision：none / none
```

基准：

```text
repo HEAD：7d441c9e82d20ab99e8e6e5153564810fd11b656
origin/main：bfa66766565bba7648b9197c34f8d7cd10136a42
AITool tree：76cf9fa8734b4f79bc0fdf84b34caf67b1b22966
Engine src tree：0af0cd76946047d3b6432cad9e21d007e7f4d6e2
Frontend tree：77f52e9c4daecf6bb0425f54039eb665ee024758
Quasar HEAD：3ab27ef3b18b22d33539d3b1dee66a9d39f14433
```

工作区边界：

- 保留既有 Runtime、LANChat、C++ Native route、Quasar 安全日志和文档修改，不做回退。
- Quasar 既有修改：`client_hunyuan3d.py`、`model_tools.py`。
- 本任务新增 `_test_import_guard.py`，只用于测试目标模块自身的 AST import。
- 三项隔离测试不再读取全局 `sys.modules`，仍严格禁止协作层静态 import Runtime/LANChat。

验证证据：

```text
单命令门禁：102 passed
Track B：81
R3 readiness：21
结果：Ran 102 tests in 0.281s / OK
```

Gate 与 F5：

```text
Full R3 Gate 保持 red / pending_reevaluation
B0.1 不涉及 Engine 行为，无新增 F5 要求
历史 Native / Snapshot / Finalizer 修复仍为 [待 F5/实机验证]
```

准入检查：

```text
B0.1 verified
B0.2 ready
B0.3/B0.4 继续受前置依赖阻断
```

下一批可选任务：

```text
B0.2 集中 schema version 登记
```

## 71. 2026-07-18 B0.2 集中 schema version 登记完成

```text
时间 / commit：2026-07-18 / agent-native@7d441c9e（working tree）
任务 ID / 状态：B0.2 / verified
执行角色：架构 AI
里程碑状态：not_ready
Full R3 Gate before / after：red -> red（无实机新证据）
Single-player Demo Gate before / after：unavailable -> unavailable
Skeleton contract version/hash：r3-skeleton-week1-v1 / unavailable
Interface change request / decision：none / none
```

完成断点：

- 新增零依赖 `services/schema_versions.py`，集中登记六个 domain version。
- `agent_collaboration/contracts.py` 不再声明本地版本，改为 import `COLLABORATION_SCHEMA_VERSION=1.1`。
- 保留 `contracts.COLLABORATION_SCHEMA_VERSION` 兼容读取，不增加第二事实源。
- 新增集中性测试：注册表零 import、生产源码无重复版本字面量、协作契约使用集中版本。

验证证据：

```text
Python compileall：passed
单命令门禁：105 passed
schema version：3
Track B：81
R3 readiness：21
结果：Ran 105 tests in 2.932s / OK
```

Gate 与 F5：

```text
Full R3 Gate 保持 red / pending_reevaluation
B0.2 只修改 Python 契约版本，不需要 F5
Snapshot/Gate/Engine/Frontend 版本目前仅集中登记，未冒充对应 DTO 已完成迁移
```

准入检查：

```text
B0.1 verified
B0.2 verified
B0.3 ready
B0.4 继续受 B0.3 阻断
```

下一批可选任务：

```text
B0.3 统一阻断诊断、Manifest/hash 与接口变更交接契约
```

## 72. 2026-07-18 B0.3 统一阻断诊断与接口交接契约完成

```text
时间 / commit：2026-07-18 / agent-native@7d441c9e（working tree）
任务 ID / 状态：B0.3 / verified
执行角色：架构 AI
里程碑状态：not_ready
Full R3 Gate before / after：red -> red（无实机新证据）
Single-player Demo Gate before / after：unavailable -> unavailable
Skeleton contract version/hash：r3-skeleton-week1-v1 / unavailable（待 B0.4 Manifest）
Interface change request / decision：none / none
```

完成断点：

- 新增中立 `services/integration_contracts.py`，只依赖 stdlib 与 `schema_versions.py`。
- 实现结构化 MissingRequirement、BlockedResult、SkeletonNodeStatus 和 SkeletonStatusReport。
- 实现规范化 Public Protocol/DTO/Enum Manifest 与 SkeletonContractManifest SHA-256。
- hash 输入不含 generated_at、注释、格式化和私有实现。
- 实现 InterfaceChangeRequest / InterfaceChangeDecision 与 accepted revalidation 强约束。
- requirement ID、owner domain、节点状态、优先级、UTC 时间和 contract hash 均有 Validator。

验证证据：

```text
Python compileall：passed
单命令门禁：114 passed
integration contracts：9
schema version：3
Track B：81
R3 readiness：21
结果：Ran 114 tests in 2.656s / OK
```

关键自动验证：

```text
非法 requirement_id/owner/description：rejected
BlockedResult 无结构化依赖或 next_action：rejected
非法 node status/priority：rejected
相同 Manifest：相同 hash
公共签名变化：hash 变化
私有 Protocol 方法变化：hash 不变
generated_at 变化：contract hash 不变
accepted interface change 无 revalidation：rejected
```

Gate 与 F5：

```text
Full R3 Gate 保持 red / pending_reevaluation
B0.3 为纯契约，不需要 F5
当前无 InterfaceChangeRequest，填充阶段尚未开始
```

准入检查：

```text
B0.1-B0.3 verified
B0.4 ready
```

下一批可选任务：

```text
B0.4 Walking Skeleton
```

## 73. 2026-07-18 B0.4 Walking Skeleton 完成并冻结

```text
时间 / commit：2026-07-18 / agent-native@7d441c9e（working tree）
任务 ID / 状态：B0.4 / verified
执行角色：架构 AI -> 填充 AI
里程碑状态：not_ready
Full R3 Gate before / after：red -> red（无实机新证据）
Single-player Demo Gate before / after：unavailable -> unavailable
Skeleton contract version：r3-skeleton-week1-v1
Skeleton contract hash：sha256:fd65eaf4f7067f011ed812d8eb57a79d0b78504ea9e394bd6927c90c73b48148
Interface change request / decision：none / none
```

完成断点：

- 新增纯协作层 `agent_collaboration/walking_skeleton.py`，没有 AgentRuntime、Frontend 或 C++ import。
- 固定十节点和九条有序边，复用真实 PlanningAgent、ArtAgent、ProgramAgent 和五 Artifact bundle。
- ProjectGatePreflight 真实检查 bundle 完整性、SHA-256 identity、内部依赖和 non-executable 状态。
- Engine capability 通过注入端口返回结构化 `pending_runtime_verification`，没有 Engine 写入或假成功。
- DemoResult 明确 `executable=False`，ProgressEventFixture 携带相同阻断事实和 SkeletonStatusReport。
- 规范化 ContractManifest 覆盖 6 个 schema version、7 个 Protocol、18 个 DTO、3 个枚举、10 个节点和 9 条边。
- 相同 fixture 与固定 UTC clock 产生相同 Manifest、报告和 contract hash。

节点状态表：

| 节点名 | 接口签名 | 当前状态 | 阻断码 | 责任域 | 填充优先级 | 证据 |
|---|---|---|---|---|---:|---|
| `user_command_fixture` | `UserCommandFixture` | completed | - | frontend | 1 | `Skeleton:user_command_fixture` |
| `demo_scenario_runner` | `DemoScenarioRunnerPort.run` | completed | - | integration | 2 | `Skeleton:demo_scenario_runner` |
| `planning_agent` | `PlanningAgentPort.run` | completed | - | collaboration | 3 | `Skeleton:planning_agent` |
| `art_agent` | `ArtAgentPort.run` | completed | - | collaboration | 4 | `Skeleton:art_agent` |
| `program_agent` | `ProgramAgentPort.run` | completed | - | collaboration | 5 | `Skeleton:program_agent` |
| `artifact_bundle` | `ArtifactBundlePort.build` | completed | - | collaboration | 6 | `Skeleton:artifact_bundle` |
| `project_gate_preflight` | `ProjectGatePreflightPort.evaluate` | completed | - | collaboration | 7 | `Skeleton:project_gate_preflight` |
| `engine_capability_port` | `EngineCapabilityPort.get_manifest` | pending_runtime_verification | `bridge_not_connected` | engine | 8 | `Skeleton:engine_capability_port`, `adapter:engine_capability_port`, `[待F5/实机验证]` |
| `demo_result` | `DemoResult` | completed | - | integration | 9 | `Skeleton:demo_result` |
| `progress_event_fixture` | `ProgressEventFixture` | completed | - | frontend | 10 | `Skeleton:progress_event_fixture` |

阻断事实：

```text
node_id：engine_capability_port
status：pending_runtime_verification
error_code：engine_capability_manifest_unavailable
MissingRequirement：engine.capability_manifest
owner_domain：engine
retryable：true
next_action：等待 Engine 组提供稳定集成 manifest 后重试
```

验证证据：

```text
Python compileall：passed
单命令门禁：121 passed
Walking Skeleton：6
integration contracts：10
schema version：3
Track B：81
R3 readiness：21
结果：Ran 121 tests in 3.159s / OK

Artifact 数量：5
BlockedResult 数量：1
overall：pending_runtime_verification
contract hash：sha256:fd65eaf4f7067f011ed812d8eb57a79d0b78504ea9e394bd6927c90c73b48148
```

硬边界证据：

```text
零 ActionProposal / EntityBindingPlan / PlanPatch / ToolCallGraph
零 RuntimeCppBridge / EngineWriteGate
Mock Artifact 在 assert_executable() 边界被拒绝
协作层静态 import 未出现 AgentRuntime / LANChat / Frontend / C++
```

Gate 与 F5：

```text
Full R3 Gate 保持 red / pending_reevaluation
Single-player Demo Gate 尚未评估
engine_capability_port：[待 F5/实机验证]
其他 B0 Skeleton 节点不需要 F5
```

架构 AI 交接包：

```text
contract version：r3-skeleton-week1-v1
contract hash：sha256:fd65eaf4f7067f011ed812d8eb57a79d0b78504ea9e394bd6927c90c73b48148
未决 InterfaceChangeRequest：0
当前填充节点：engine_capability_port
当前 owner：engine
```

下一批可选任务：

```text
B1.1 Engine capability / snapshot 端口
```

## 74. 2026-07-18 B1.1 Engine capability / snapshot 端口填充完成

```text
时间 / commit：2026-07-18 / agent-native@7d441c9e（working tree）
任务 ID / 节点：B1.1 / engine_capability_port
执行角色：填充 AI
接口变化：否
节点状态 before -> after：pending_runtime_verification -> pending_runtime_verification
阻断码 before -> after：engine_capability_manifest_unavailable -> bridge_not_connected（按真实读取结果细分）
Skeleton contract version/hash：r3-skeleton-week1-v1 / sha256:fd65eaf4f7067f011ed812d8eb57a79d0b78504ea9e394bd6927c90c73b48148
Interface change request / decision：none / none
```

完成断点：

- `agent_runtime.adapters.make_engine_capability_manifest_reader()` 通过注入的 native/tool 只读查询实际读取 manifest；不经过 `RuntimeCppBridge` 或任何 Engine 写入。
- 连接断开、工具读取失败、native manifest 不可用和非结构化响应均转换为受限、可审计的失败语义，未伪造 Engine 成功。
- `RuntimeEngineCapabilityPort` 保持协作层不 import Runtime 的依赖边界；它接收注入 reader，归一化 current/legacy manifest 字段，并返回既有 `EngineCapabilityManifest` 或完整 `BlockedResult`。
- 不兼容 Engine capability contract、SceneWorldSnapshot schema、缺失 version 字段或非法 capability list 均 fail closed。
- 未修改 Protocol、DTO、节点 ID、节点边或已完成的九个节点；`DemoResult.executable` 仍为 false。

验证证据：

```text
capability 正常路径（legacy 字段归一化）: passed
Engine bridge 断开 -> bridge_not_connected BlockedResult: passed
snapshot schema 不兼容 -> engine_snapshot_schema_version_incompatible: passed
冻结 contract hash 不变: passed
骨架端到端及九个既有节点回归: passed
Python syntax compile: passed
git diff --check: clean（仅既有 CRLF 提示）

单命令门禁：125 passed
B1.1 capability port：4
Walking Skeleton：6
integration contracts：10
schema version：3
Track B：81
R3 readiness：21
结果：Ran 125 tests in 3.681s / OK
```

Gate 与 F5：

```text
Full R3 Gate：red / pending_reevaluation（不变）
engine_capability_port：[待F5/实机验证]
当前基准未提供可调用的稳定 Engine capability manifest；该端口只能如实返回阻断，不得标 verified。
待 F5 节点数量：1（不变）
```

下一 ready 任务：

```text
B1.2 Frontend 业务协议
```

## 75. 2026-07-18 B1.2 Frontend 业务协议填充完成

```text
时间 / commit：2026-07-18 / agent-native@7d441c9e（working tree）
任务 ID：B1.2
涉及模块：services/frontend_adapter.py、services/test_frontend_adapter.py
执行角色：填充 AI
接口变化：否
状态 before -> after：unavailable -> code_complete
Skeleton contract version/hash：r3-skeleton-week1-v1 / sha256:fd65eaf4f7067f011ed812d8eb57a79d0b78504ea9e394bd6927c90c73b48148
Interface change request / decision：none / none
```

完成断点：

- 新增独立 `FrontendBusinessProtocolAdapter`，仅依赖 stdlib、`schema_versions.py` 和 `integration_contracts.py`，不导入 CEF、Runtime、LANChat、C++ 或 Engine 写路径。
- `UserCommand` 固定使用集中 `FRONTEND_INTERACTION_SCHEMA_VERSION`，支持 `start_project / confirm_action / query_status / start_preview` 四类命令；`ProgressEvent` 保留 project/task/plan/scene version 等业务字段。
- 每个合法命令使用稳定 `command_id` 派生确定性 `event_id`；相同 command ID 重放返回 `duplicate_command_id` 且零新事件，外来相同 event ID 返回 `duplicate_event_id`。
- schema 不兼容、未知命令和非法字段返回结构完整、可审计的 `BlockedResult`，不把失败折叠为通用错误。
- 复用 bridge.js 既有 C++ method/event manifest 与 callback transport 的未来接入点；本轮没有重建或修改 CEF Bridge。bridge.js 没有统一业务 event ID，因此真实接入必须传递本 Adapter 所要求的 event_id，不能用 callback token 代替。
- 零 ActionProposal / EntityBindingPlan / PlanPatch / ToolCallGraph；AI 页面未获得 `sceneTools.createActor` 或其他 Engine 写权限。

验证证据：

```text
合法 UserCommand -> 确定性 ProgressEvent：passed
unknown command_type -> unknown_command_type：passed
schema version 不兼容 -> frontend_schema_version_incompatible：passed
相同 command_id 重放 -> 零第二业务事件：passed
相同 event_id 重放 -> duplicate_event_id：passed
Adapter 无 Runtime/LANChat/Frontend/C++ import：passed
Walking Skeleton 端到端和冻结 hash 回归：passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示）

单命令门禁：131 passed
Frontend adapter：6
B1.1 capability port：4
Walking Skeleton：6
integration contracts：10
schema version：3
Track B：81
R3 readiness：21
结果：Ran 131 tests in 3.155s / OK
```

Gate 与 F5：

```text
Full R3 Gate：red / pending_reevaluation（不变）
Frontend 业务协议：code_complete，[待F5/实机验证]
待 F5 Adapter 项：1 -> 2
真实 bridge.js / CEF 事件联调尚未执行；不得将 fixture 结果视为 UI 或 Engine 实机结论。
```

下一 ready 任务：

```text
B2.1 Engine Test Double 生命周期模拟
```

## 76. 2026-07-18 B2.1 Engine Test Double 生命周期模拟完成

```text
时间 / commit：2026-07-18 / agent-native@7d441c9e（working tree）
任务 ID：B2.1
涉及模块：services/test_support/engine_test_double.py、services/test_engine_test_double.py
执行角色：填充 AI
接口变化：否
状态 before -> after：unavailable -> code_complete
Skeleton contract version/hash：r3-skeleton-week1-v1 / sha256:fd65eaf4f7067f011ed812d8eb57a79d0b78504ea9e394bd6927c90c73b48148
Interface change request / decision：none / none
```

完成断点：

- 新增仅测试支持命名空间 `services/test_support/engine_test_double.py`；没有注册生产 Provider，也没有被任何生产模块导入。
- `EngineTestDouble.get_manifest()` 复用 `RuntimeEngineCapabilityPort` 的既有结果契约：成功返回 `EngineCapabilityManifest`，失败返回结构完整的 `BlockedResult`；未改动 B1.1 生产实现。
- 生命周期可确定性驱动：create accepted -> geometry ready -> actual AABB/grounding/support -> render ready -> scene version +1；late-ready、partial、create timeout/reject 均可由显式参数控制。
- 相同 request_id 重放复用同一 Actor identity；expected scene version 不匹配返回 `engine_snapshot_version_conflict`；缺 primitive 返回 `engine_capability_primitive_missing`。
- 所有可读 snapshot 强制 `snapshot_source=mock`，调用方不能覆盖。mock Artifact 继续由现有 `assert_executable()` 拒绝，未建立第二套执行边界。
- 本轮未创建 ActionProposal、EntityBindingPlan、PlanPatch、ToolCallGraph 或任何 Engine 写路径。

验证证据：

```text
normal 生命周期（actual AABB、grounding/support、render ready、version +1）：passed
late-ready 延迟周期：passed
partial 身份一致但缺 AABB/sync：passed
failure create timeout -> engine_create_timeout：passed
duplicate request_id -> 单一稳定 Actor：passed
snapshot expected version 冲突 -> engine_snapshot_version_conflict：passed
capability missing -> engine_capability_primitive_missing：passed
所有场景 snapshot_source=mock 且不可覆盖：passed
mock Artifact -> assert_executable -> NonExecutableArtifactError：passed
生产模块零 test_support import：passed
Walking Skeleton hash 回归：passed
Python syntax compile：passed
git diff --check：clean（仅既有 CRLF 提示）

单命令门禁：142 passed
Engine Test Double：11
Frontend adapter：6
B1.1 capability port：4
Walking Skeleton：6
integration contracts：10
schema version：3
Track B：81
R3 readiness：21
结果：Ran 142 tests in 6.096s / OK
```

Gate 与 F5：

```text
Full R3 Gate：red / pending_reevaluation（不变）
Engine Test Double：code_complete，仅测试 fixture，不构成实机证据
待 F5 Skeleton 节点数：1（不变）
待 F5 Adapter 项：2（不变）
```

下一 ready 任务：

```text
B2.2 Adapter 双版本兼容
```

## 77. 2026-07-18 B2.2 Adapter 双版本兼容阻断：缺少输入 DTO 版本标记

```text
时间 / commit：2026-07-18 / agent-native@7d441c9e（working tree）
任务 ID：B2.2
执行角色：填充 AI
接口变化：未执行；请求架构 AI 决策
状态 before -> after：ready -> interface_change_required
Skeleton contract version/hash：r3-skeleton-week1-v1 / sha256:fd65eaf4f7067f011ed812d8eb57a79d0b78504ea9e394bd6927c90c73b48148
```

事实核验：

- 当前 C++ `get_editor_scene_snapshot_from_python()` 只返回 status/scene/actors/scene_aabb/bounds_ready；没有 `dto_version`、`snapshot_dto_version`、`native_snapshot_version` 或等价输入 DTO 版本标记。
- 当前 `actor_to_json()` 已知真实字段包含 `actor_guid`、`entity_id`、`geometry.position/rotation/scale`、`world_aabb`、`source_scene_version`、`actor_version/version` 和 render readiness；这些可作为当前 native DTO 事实，不能反推出旧 DTO 版本。
- `RuntimeEngineCapabilityPort` 只传递 capability manifest 的 `snapshot_schema_version`，它描述目标 SceneWorldSnapshot schema，不是输入 C++ DTO version；`make_scene_snapshot_provider()` 也没有接收或传递输入 DTO version。
- 因此若现在通过 `actor_id/actor_guid`、顶层/geometry transform 或 `aabb/world_aabb` 的字段存在性猜测新旧版本，会违反 B2.2 的显式版本规则，并可能把未知缺字段伪造成兼容成功。

InterfaceChangeRequest：

```text
request_id：request.b2.2-engine-dto-version
node_id：engine_capability_port
reason_code：engine_dto_version_marker_missing
required_change：由 Engine C++ snapshot envelope 提供稳定 input_dto_version；能力 manifest 或 snapshot reader 必须把该值传入 Adapter。值需与目标 SceneWorldSnapshot schema version 分离。
affected_interfaces：get_editor_scene_snapshot_from_python、get_scene_snapshot MCP tool、make_scene_snapshot_provider、Engine capability/snapshot integration contract
blocked_dependents：B2.2 dual-version normalization、B6 Engine Adapter integration
evidence_refs：src/systems/ui/cef/cef_editor_native_api_handlers.cpp:get_editor_scene_snapshot_from_python、actor_to_json；editor/plugins/AITool/services/agent_runtime/adapters.py:make_scene_snapshot_provider
```

验证证据：

```text
冻结 Skeleton contract hash：一致
C++ / Adapter 对 dto_version、snapshot_dto_version、actor_snapshot_version、native_snapshot_version 的源码扫描：无匹配
当前 native actor 字段读取：已核实
未创建旧/新 DTO fixture，未实现字段猜测归一化，未修改 RuntimeEngineCapabilityPort 或 SceneWorldSnapshot schema
Full R3 Gate：red / pending_reevaluation（不变）
待 F5 Skeleton 节点数：1（不变）
待 F5 Adapter 项：2（不变）
```

本轮没有把[文档假设]误写为真实 Engine 差异。待架构 AI 接受或拒绝该请求后，再决定是否升级契约并恢复 B2.2；真实 Engine DTO 归一化仍为 **[待F5/实机验证]**。

## 78. 2026-07-19 B3.1 强类型 slot 与 primitive 完成

```text
时间 / commit：2026-07-19 / agent-native@3d849a9a，origin/main@6721de43
任务 ID：B3.1
执行角色：架构 AI + 填充 AI
接口变化：接受；GameplayLogicPlan 1.1 加入强类型 slot/primitive
状态 before -> after：ready -> verified
Skeleton contract version/hash：r3-skeleton-week1-v2 / sha256:754042409f4adda073e696fea0b65eb6d7466885e36bb8de155ddff9434fc7ef
```

事实核验：

- 权威计划第 4.2-4.3 节已定义 GameplayLogicPlan 1.1，是本次公开契约演进的架构依据。
- 新增 `GameplayEntitySlot(slot_id/semantic_role/required_capabilities)` 与 `GameplayPrimitiveSpec(primitive_id/kind/subject_slot/target_slot/parameters)`；GameplayLogicPlan 现有 `entity_slots/primitives`。
- `triggers/rules` 保留为历史审计的非执行叙述字段；结构化 primitive 是后续 Gate/Manifest 的唯一玩法语义来源。
- Manifest 现在显式包含三个 Gameplay DTO；旧 v1 hash 的下游节点需要在 B3.2/B4 前使用 v2 重新验证。

InterfaceChangeDecision：

```text
request_id：request.b3.1-gameplay-logic-plan-v1-1
decision：accepted
changed_interfaces：GameplayLogicPlan、GameplayEntitySlot、GameplayPrimitiveSpec、SkeletonContractManifest.public_dtos
new_contract_version/hash：r3-skeleton-week1-v2 / sha256:754042409f4adda073e696fea0b65eb6d7466885e36bb8de155ddff9434fc7ef
affected_nodes：program_agent、artifact_bundle、project_gate_preflight、demo_scenario_runner
required_revalidation：B0.4 skeleton、ProgramAgent、ArtifactRegistry、TaskGraph、five-Artifact workflow
evidence_refs：docs/R3-min推进记录.md:B6.4；editor/plugins/AITool/services/agent_collaboration/contracts.py；editor/plugins/AITool/services/agent_collaboration/walking_skeleton.py
```

验证证据：

```text
GameplayLogicPlan 白名单完整链：on_collect/set_state/unlock/on_enter/complete_objective 通过
非法参数、非 lockable 解锁目标、循环 slot 引用：被 validator 拒绝
python -m unittest（contracts/program-agent/artifact-registry/task-graph/five-workflow/walking-skeleton）：61 passed
build_skeleton_manifest().contract_hash()：sha256:754042409f4adda073e696fea0b65eb6d7466885e36bb8de155ddff9434fc7ef
未修改 Runtime、Engine、Frontend、CMakeLists.txt 或任何执行写路径；本任务不需要 F5
Full R3 Gate：red / pending_reevaluation（不变）
```

`CMakeLists.txt` 的 MSVC/Ninja showIncludes 修复为独立未提交工作，已识别并保持不触碰；合并 `origin/main` 带入的历史 docs 删除不构成 B3.1 代码事实，文档恢复策略另行决策。下一项为 B3.2：对现有 ArtifactRegistry 的依赖失效机制补充 GameplayLogicPlan 1.0 -> 1.1 的显式审计/拒绝规则。

## 79. 2026-07-19 B3.2 GameplayLogicPlan 版本与 stale 传播完成

```text
时间 / commit：2026-07-19 / agent-native@3d849a9a，origin/main@6721de43
任务 ID：B3.2
执行角色：填充 AI
接口变化：无；复用 ArtifactRegistry 的已存在依赖版本图
状态 before -> after：ready -> verified
Skeleton contract version/hash：r3-skeleton-week1-v2 / sha256:754042409f4adda073e696fea0b65eb6d7466885e36bb8de155ddff9434fc7ef
```

完成断点：

- 旧 GameplayLogicPlan 1.0 字符串 payload 保留原始 payload 用于审计，但缺少 `entity_slots/primitives` 时 validation 为 invalid，不能注册为新的 Artifact、不能跨越执行边界。
- GameplayLogicPlan 1.1 版本更新时，ArtifactRegistry 的通用 `dependency_superseded -> dependency_stale` 传播会将依赖旧 logic ref 的 EntityBindingPlan 标为 stale；它不再可作为后续绑定/执行输入。
- 没有通过名称、路径或 Snapshot 字段猜测绑定，也没有创建 EntityBindingPlan 的生产写入路径。

验证证据：

```text
legacy gameplay audit/reject test：passed
GameplayLogicPlan revision -> EntityBindingPlan stale test：passed
python -m unittest（contracts/artifact-registry/program-agent/task-graph/five-workflow/walking-skeleton）：63 passed
Full R3 Gate：red / pending_reevaluation（不变）
待 F5：无新增；本任务为纯协作层版本事实
```

下一 ready 任务：B4.1 ProjectGatePreflight。B2.2 `request.b2.2-engine-dto-version` 继续等待 Engine/架构侧显式 DTO 版本决策。

## 80. 2026-07-19 B4.1 ProjectGatePreflight 完成

```text
时间 / commit：2026-07-19 / agent-native@3d849a9a，origin/main@6721de43
任务 ID：B4.1
执行角色：架构 AI + 填充 AI
接口变化：接受 PreflightStatus 枚举扩展；evaluate(bundle) 节点签名不变
状态 before -> after：ready -> verified
Skeleton contract version/hash：r3-skeleton-week1-v3 / sha256:015cf2e5a38c68530c1d7a897bbda67745d46fa7993edb5514f2b9e87b7cc0c0
```

完成断点：

- ProjectGatePreflight 真实检查五 Artifact bundle/hash/internal dependencies/non-executable 边界。
- 通过 B1.1 的只读 EngineCapabilityPort 查询 capability manifest，不 import Runtime internals、不写 Engine。
- Runtime Gate/manifest 不可用时返回 `pending_runtime_verification` 且 `executable=false`；已获得 manifest 但缺 required operation 或 gameplay primitive 时返回 `blocked/engine_capability_missing`。
- 默认 Runner 继续零 ActionProposal、PlanPatch、ToolCallGraph、Provider 和 Engine 写入。

验证证据：

```text
unavailable manifest -> pending_runtime_verification：passed
full required manifest -> completed：passed
declared but incomplete manifest -> engine_capability_missing：passed
python -m unittest（contracts/artifact-registry/program-agent/task-graph/five-workflow/walking-skeleton/engine-capability-port）：69 passed
本任务为黑盒只读验证；真实 Engine capability manifest 仍 [待F5/实机验证]
```

下一 ready 任务：B4.2 无 UI Demo Runner。B2.2 `request.b2.2-engine-dto-version` 继续等待 Engine/架构侧显式 DTO 版本决策。

## 81. 2026-07-19 B4.2 无 UI Demo Runner 完成

```text
时间 / commit：2026-07-19 / agent-native@3d849a9a，origin/main@6721de43
任务 ID：B4.2
执行角色：架构 AI + 填充 AI
接口变化：接受 DemoResult 扩展（project/task graph/preflight/required capabilities/pending runtime verifications）
状态 before -> after：ready -> verified
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
```

完成断点：

- Runner 通过正式 ProjectState、ArtifactRegistry、AgentTaskGraph、三个职能 Agent 和 ProjectGatePreflight，确定性生成五 Artifact bundle；无 UI、无 Provider、无场景写入。
- DemoResult 公开 `project_id/task_graph_id/artifact_refs/required_capabilities/preflight_result/pending_runtime_verifications`；`executable` 固定为 false。
- 同一 `project_id + command_id` 重放返回同一结果；同 ID 内容变化拒绝，避免二次生成。
- 任务图 `max_attempts=2`；短暂 Agent 异常会调用既有 retry_task，成功重试后继续，不重放已完成上游。
- Capability unavailable 保持 integration_ready + 明确 pending runtime verification；缺已声明能力则 blocked。该状态不是 Engine-ready、Game-ready 或 F5 Green。

验证证据：

```text
正常 five-Artifact bundle：passed
transient ArtAgent failure -> TaskGraph retry -> success：passed
Artifact stale propagation：由 B3.2 目标测试覆盖
capability unavailable/full/missing：passed
identical command replay / changed command ID reuse rejection：passed
python -m unittest（contracts/artifact-registry/program-agent/task-graph/five-workflow/walking-skeleton/engine-capability-port）：71 passed
本任务不写 Engine；所有 Runtime/Engine 事实继续 [待F5/实机验证]
```

下一状态：B5.1 依赖 B2（含 B2.2 Adapter 双版本兼容），目前只剩 `request.b2.2-engine-dto-version` 的外部 Engine/架构决策。连续推进在此暂停。

## 82. 2026-07-20 最新 F5 校准与黑盒成果收敛决策

```text
时间 / 证据：2026-07-20 / 2026-07-19_15-51-42_corona.log + 对应 LANChat history
任务 ID / 状态：B5.0 前置决策 / ready
执行角色：架构 AI
contract_status：B0-B4 verified（保留）
production_integration_status：not_ready
Full R3 Gate：red / pending_reevaluation
Single-player Demo Gate：unavailable / blocked_by_runtime_control_plane
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
公共 Skeleton 接口变化：无
```

### 实机正向事实

```text
business BatchPlan：3/3 completed
business ToolGraph：3/3 completed
Tool nodes：54/54 succeeded
Runtime 最终摘要：11 entities / 11 reported game-ready / 11 engine-verified
Engine scene：4 environment + 7 model actors
Engine bridge：18/18 success，0 bridge error
```

上述事实证明 ScenePlan -> BatchPlan -> business ToolGraph -> Engine import 主链已明显打通，但 `11 reported game-ready` 仍不是 R3 Green。Registry/Snapshot/Report 的终态可信度、消息控制面和语义边界尚未同时通过。

### P0 问题

| 问题 | 实机证据 | 影响 |
|---|---|---|
| 同一消息重复执行与回复 | `@长者 请你给出一个方案` 先由“小女孩”回复，再由“长者”回复 | route、target 和 reply authority 未原子收口 |
| 固定模板替代真实回答 | 方案回复来自 `lanchat_scene_runtime` 固定角色开场和固定四段结构 | DMX 调用成本没有转化为问题对应回答 |
| 上下文丢失 | “请你给出一个方案”没有继承“迪士尼风格卧室” | 方案目标被短指令覆盖 |
| 语法片段成为实体 | 回复出现“准备生成模型：请你给出一个方案” | 初始 ScenePlan 未统一经过 EntityNameValidator |
| 方案身份混淆 | “长者确认开始”执行已有 `plan-d37bebb0578d`，未验证目标 Agent 方案引用 | 不同 Agent 的计划可能互相覆盖或误执行 |
| 系统口径矛盾 | Runtime 先报告方案已更新和 7 个模型，Agent/GM 又报告方案尚未形成 | 用户无法判断真实状态 |
| Quasar 双路径初始化 | 同一进程出现 `Quasar.*` 与 `plugins.AITool.Quasar.*` 两套入口和路径 | Provider、模型目录、PoolRegistry 可能分裂 |

### P1 问题

| 问题 | 实机证据 | 影响 |
|---|---|---|
| 重复 heartbeat | 47 条 history 中 25 条 action_status，同一句资源准备消息重复 20 次 | 聊天刷屏、终态事件被淹没 |
| 内部诊断倾倒 | 一条方案更新包含 Runtime/Replay/Provider/Guard 数十行指标 | 用户回复不可读且暴露内部实现 |
| 用户可见乱码 | 系统名称持久化为“绯荤粺”，部分状态字段同样乱码 | 前端体验和自动文本判断不稳定 |
| Scene Contract 漂移 | 明确卧室目标仍为 `mixed/mixed`，并导入 terrain/transition_zone | 场景语义和环境分流不可信 |
| 终态披露顺序异常 | history 先显示 report_ready，随后才显示 scene_snapshot_refreshed | 用户无法确认报告是否基于最新 Engine 事实 |
| 中间 Readiness 不连续 | 前两批导入完成时仍为 entities=0，最终一次跳为 11/11 | GM 进度、上层 Agent 和多人状态无法消费连续事实 |
| 材质/纹理降级 | 多次 default white 与 embedded texture fallback | Demo 视觉质量不稳定 |

### 黑盒成果保留与生产缺口

| 工作块 | contract_status | production_integration_status | 决策 |
|---|---|---|---|
| B0 Walking Skeleton | verified | disconnected | 保留 v4，不重新实现 |
| B1.1 Engine capability port | code_complete | pending_runtime_verification | 在 B6.2 接真实 manifest/fixture |
| B1.2 Frontend Adapter | code_complete | bypassed_by_current_runtime | 在 B6.1/B5.4 接真实入口与进度事件 |
| B2.1 Engine Test Double | verified | insufficient_for_message_flow | B5.0 增加真实 history replay，不扩大通用 Mock |
| B2.2 Adapter version | pending | blocks cross-SHA only | 拆为 B2.2a/B2.2b |
| B3 GameplayLogicPlan 1.1 | verified | no real Snapshot binding | 保留，等待 B6.3/B6.4 |
| B4 Preflight/Runner | verified | not production entry | B6.1 只读接入 |

### B2.2 拆分决策

```text
B2.2a current-unversioned-v1 strict fixture：ready
  - 以本轮真实字段集合、必填身份字段和 build fingerprint 精确匹配
  - 当前 SHA 可用于只读 Adapter/Gate 对账
  - 未知变化 fail closed

B2.2b Engine explicit input_dto_version：deferred_to_B7
  - 等待 capability manifest
  - 只阻断跨 SHA 迁移和最终集成
```

原 `request.b2.2-engine-dto-version` 保持未决，但不再阻断 B5 或 B6.3 的纯逻辑开发。

### 新执行队列

```text
B5.0 F5 fixture 与自动诊断
-> B5.1 单消息单执行单回复
-> B5.2 语义上下文 / 方案身份 / 实体校验
-> B5.3 零模型上下文记录
-> B5.4 进度 / Finalizer / 双初始化

并行：
B2.2a 严格当前版本 fixture
-> B6.3 single_player_demo Gate evaluator

汇合：
B5 完成 + B6.1/B6.2/B6.3
-> B7.1 控制面 F5
-> B7.2 Runtime 最小 F5
-> B6.4 EntityBindingPlan / GameplayManifest 边界
-> B7.3 两个独立 Session 完整 Demo
```

### 当前任务与边界

```text
当前唯一主线任务：B5.0 F5 证据基线
可并行纯逻辑任务：B2.2a 或 B6.3（不得修改 lanchat_agent_worker.py）
旧 persona：兼容入口，不再扩建项目规划或 Engine 执行能力
Engine/Frontend/材质/Readiness 效果：[待F5/实机验证]
```

B5.0 完成标准：任意 AI 只读取推进记录顶部、本节和新推进计划，即可明确当前 Gate、黑盒已完成项、F5 推翻的假设、唯一主线任务、可并行任务、F5 阻断项以及 B2.2 不再全局阻断的原因。

## 83. 2026-07-20 B5.0 F5 证据基线完成

```text
任务 ID / 状态：B5.0 / verified
执行角色：架构 AI
contract_status：联合探针与回归 fixture verified
production_integration_status：unchanged / not_ready
Full R3 Gate：red / pending_reevaluation
Single-player Demo Gate：unavailable / blocked_by_runtime_control_plane
公共 Runtime / LANChat / Frontend / Engine 代码变化：无
```

完成断点：

- 扩展 `docs/probes/r3_f5_log_check.py`，新增 `--history`，可联合分析 Corona 日志与 LANChat JSONL history。
- 保持原 Runtime Gate/Batch/ToolGraph/Render 检查兼容；未提供 history 时行为不变。
- 新增逐消息控制面证据：目标 Agent、route、processing owner、final reply、progress/action status、模型调用 purpose 证据、plan/artifact ref 和诊断码。
- 新增会话级检查：重复 heartbeat、命令片段实体、方案 owner 串线、Finalizer 披露顺序、Quasar import root、模型 purpose 可观测性、Runtime/回复矛盾、乱码和内部诊断倾倒。
- 将本轮关键证据缩减为只读 fixture：
  - `docs/probes/fixtures/2026-07-19_b5_control_plane_corona.log`
  - `docs/probes/fixtures/2026-07-19_b5_control_plane_history.jsonl`

聚焦验证：

```text
python -m unittest docs.probes.test_r3_f5_log_check
结果：4 passed

真实证据：2026-07-19_15-51-42_corona.log + 对应 47 条 LANChat history
结果：R3_F5_BLOCKED，PASS=1 / WARN=1 / FAIL=12
```

真实 F5 自动复现结果：

```text
用户消息：5 条
@长者“请你给出一个方案”：final reply 2 条，sender=[小女孩, 长者]
重复处理 owner：首轮小女孩消息与 @长者方案消息均出现 native_queue + agent_trigger
错误实体片段：请你给出一个方案
方案身份串线：plan-d37bebb0578d owner 小女孩 -> 确认目标 长者
重复 heartbeat：同一文本 20 次
Finalizer 披露：report_ready@42 -> report_ready@43 -> scene_snapshot_refreshed@46
Quasar root：plugins.AITool.Quasar + Quasar
用户可见乱码 sender：37 条
内部诊断倾倒：1 条
模型调用 purpose：5 条推断证据，0 条显式 purpose 字段
R3GateTrace：日志中缺失
```

结论：B5.0 已把本轮实机问题转换为稳定、机器可读的回归证据，但没有修改或验证生产控制面。下一唯一主线任务为 **B5.1 单消息单执行单回复**；B2.2a/B6.3 仍可在不修改 `lanchat_agent_worker.py` 的前提下并行。B5.1 完成并通过聚焦并发/重放测试前不运行下一轮 F5。

## 84. 2026-07-20 B5.1 单消息单执行单回复代码收口

```text
任务 ID / 状态：B5.1 / code_complete [待F5/实机验证]
执行角色：填充 AI
里程碑状态：not_ready
Full R3 Gate before / after：red / pending_reevaluation -> 无变化
Single-player Demo Gate before / after：unavailable / blocked_by_runtime_control_plane -> 无变化
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
公共 Skeleton 接口变化：无
```

完成断点：

- `MessageDispatchLedger` 新增严格 `claim_execution`、原子 `claim_reply/complete_reply`，第一次认领冻结 execution owner、route 和显式目标 Agent。
- 同一 owner 的重复 execution claim 也会被拒绝；旧分支只能在已拥有执行权时继续使用兼容 `claim`，不能取得第二份执行权。
- `_send_final_reply()` 内部强制取得 final reply claim；错误非系统 Agent、并发第二回复和成功后的重放均被拒绝。
- 回复发送失败只释放 reply claim，允许重试回复，不允许重新执行 Agent。
- 缺失 `message_id` 时优先使用 `correlation_id`，两者都缺失时使用 room/sender/timestamp/target/text 的规范化 hash 形成稳定 dispatch identity。
- Native Queue 收到显式非 GM `@Agent` 消息时不再进入旧 pending planning gate 或 active Runtime plan update，统一交给 Agent Trigger；GM 控制继续保持 Native 权威 owner。
- `_process_trigger` 在任何 Agent 推理前取得 execution claim；Native 内部已认领的 GM handoff 通过显式 `_dispatch_owner` 继续，不开放外部重放旁路。

验证证据：

```text
execution strict claim / target freeze / failed reply retry：passed
Native-first explicit Agent deferral：passed
Agent Trigger 真并发与 replay：1 execution / 1 final reply，passed
错误 Agent reply -> 正确 Agent reply -> duplicate：passed
无 message_id correlation identity：passed
GM Native ownership 与 R3 query 兼容：passed
python -m unittest 聚焦入口/并发：22 passed
Probe + ActionIntent + Native sync + Game-ready 回归：57 passed
Python syntax compile：passed
```

未验证与边界：

- 真实 C++ Native Queue 与 Agent Trigger 的线程时序仍为 `[待F5/实机验证]`，在 B7.1 固定五轮对话中验收。
- 完整 `test_lanchat_runtime_guard` 单文件包含既有 Quasar 慢启动路径，本轮组合运行在 240 秒超时前未出现断言失败；按测试预算未扩大为无关全量修复。
- 本任务没有修改 RuntimeGuard、EngineWriteGate、ToolCallGraph、Frontend 或 C++。

下一唯一主线任务：**B5.2 语义上下文、方案身份和实体名称安全**。并行候选仍为 B2.2a/B6.3；任何涉及真实双入口时序的结论继续等待 B7.1。

## 85. 2026-07-20 B5.2 语义上下文、方案身份和实体名称安全代码收口

```text
任务 ID / 状态：B5.2 / code_complete [待F5/实机验证]
执行角色：填充 AI
里程碑状态：not_ready
Full R3 Gate before / after：red / pending_reevaluation -> 无变化
Single-player Demo Gate before / after：unavailable / blocked_by_runtime_control_plane -> 无变化
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
公共 Skeleton 接口变化：无
```

完成断点：

- 新增房间级强类型 `ConversationTurnContext/Store`，保存活动场景目标、目标历史、最新指令、目标 Agent、活动方案引用和来源消息 ID。
- Native/Trigger 对同一 message 的上下文记录幂等；“请给出方案”等短指令继承当前活动目标，不再覆盖“迪士尼风格卧室”。
- 新的明确场景目标替换活动目标，旧目标仅保留在 history；从乐园/混合切到卧室时不会继续把旧场景类别拼入活动目标。
- 兼容 planning confirmation 暴露稳定 `agent_plan_id` 与 `artifact_ref=legacy-plan:<agent_plan_id>`，并通过回复 metadata 和确认 compose text 继续传递。
- 确认首先按 `target_plan_id/target_agent` 查找；显式目标 Agent 没有待确认方案时返回澄清，不再回退执行房间中另一 Agent 的 pending/active plan。
- `EntityNameValidator` 增加通用命令片段判断；初始 ScenePlan 与 `scene.extract_objects` 候选统一过滤用户指令，拒绝原因保留在 ToolResult payload，不扩张 RuntimeState schema。
- 旧小女孩/长者/商人仅作为兼容回复入口，本任务没有把它们接入三职能 Artifact 或新增 Engine 执行权限。

验证证据：

```text
Disney 乐园讨论 -> Disney 卧室目标 -> @长者短方案指令：活动目标保持卧室，passed
新场景目标替换旧类型 / 同 message 幂等：passed
稳定 agent_plan_id/artifact_ref 生成、metadata 传递和 context binding：passed
@长者确认不得执行小女孩 pending plan：passed
无上文的空泛方案指令返回澄清：covered by deterministic branch
“请你给出一个方案” EntityNameValidator 拒绝：passed
scene.extract_objects 不产生命令片段实体且正常对象仍保留：passed
语义/方案/实体聚焦：21 passed
Probe + Context + ActionIntent + Native sync + Game-ready 回归：61 passed
Python syntax compile：passed
Skeleton Manifest hash 重算：e60094df...（不变）
```

未验证与边界：

- 真实五轮 LANChat history 是否持续携带方案 metadata、卧室 Scene Contract 是否不再为 mixed，均为 `[待F5/实机验证]`，在 B7.1/B7.2 核对。
- 本任务没有实现正式三职能 EntityBindingPlan，也没有放开 ActionProposal。

下一唯一主线任务：**B5.3 上下文记录零模型调用与调用预算**。

## 86. 2026-07-20 B5.3 上下文记录零模型调用与调用预算代码收口

```text
任务 ID / 状态：B5.3 / code_complete [待F5/实机验证]
执行角色：填充 AI
里程碑状态：not_ready
Full R3 Gate before / after：red / pending_reevaluation -> 无变化
Single-player Demo Gate before / after：unavailable / blocked_by_runtime_control_plane -> 无变化
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
公共 Skeleton 接口变化：无
```

完成断点：

- AgentRuntime 注册精确纯记录动作 `runtime.plan_context.record` 与 `runtime.agent_reply_context.record`；两个动作只写 RuntimeState/OperationLog，不创建 ScenePlan、PlanPatch、RuntimeEvent ToolGraph 或业务 ToolGraph。
- LANChat 的 SeedPlan 镜像、用户讨论、Agent 回复和 planning reply 全部改走精确纯记录动作；普通回复不再自动提升为 Runtime ScenePlan，也不再覆盖已冻结方案 brief。
- 只有已经存在 RuntimeState 映射的 plan reference 才能附着到具体 ScenePlan；未映射的 SeedPlan/聊天引用只记录为 room context，禁止借 Coordinator fallback 猜测绑定。
- 直接场景请求在未产出稳定 `agent_plan_id/artifact_ref` 时 fail closed：保留需求上下文，但明确提示尚未冻结为可执行 Runtime 方案，不能直接确认写入。
- 场景提取新增 `plan_id + plan_version + content_hash` 幂等键；同版本同内容重放返回已有提取事实，零新增提取 ToolGraph。
- 新增 `ModelCallLedger`，为每消息记录 `message_id/correlation_id/purpose/provider/model/plan_version/dedupe_result`；显式 Agent 用户可见推理预算为 1，第二次调用硬阻断。
- 每条 final reply 产出一次 `model_call_summary`；确定性 GM/查询/上下文记录自然得到 0 次调用摘要，发送重试不会重复生成摘要。

验证证据：

```text
精确 context action：ToolGraph/PlanPatch/ScenePlan version 均不变，passed
精确 context state 写入失败：fail closed、零 ToolGraph，passed
相同 plan version + content hash 提取重放：零新增 ToolGraph，passed
确定性回复模型调用摘要：0 calls，passed
显式 Agent 推理调用预算：1 call；第二次 budget_exhausted，passed
SeedPlan/user/Agent reply 生产镜像：room context only；已有 Runtime plan 可精确附着，passed
直接生成请求未冻结方案：禁止形成可确认 Runtime draft，passed
B5.3 聚焦上下文/调用预算回归：23 passed
Context + ActionIntent + Game-ready + Native sync 回归：59 passed
Walking Skeleton：10 passed
Python syntax compile：passed
Skeleton Manifest hash 重算：e60094df...（不变）
```

未验证与边界：

- 真实 F5 中每条消息是否只出现一个 `LANChatModelCallSummary`、确定性查询是否稳定为 0、显式 Agent 讨论是否最多 1 次，均为 `[待F5/实机验证]`，在 B7.1 核对。
- `test_agent_runtime_phase1` 全文件包含既有长时运行路径；本轮 240 秒门限前未出现断言失败，按测试预算未扩成无关慢测试治理。
- 本任务没有放开 ActionProposal、EntityBindingPlan、Provider 场景生成或 Engine 写入；Full R3/Single-player Gate 均未改变。

下一唯一主线任务：**B5.4 进度、Finalizer、报告和启动路径收口**。

## 87. 2026-07-20 B5.4 进度、Finalizer、报告和启动路径代码收口

```text
任务 ID / 状态：B5.4 / code_complete [待F5/实机验证]
执行角色：填充 AI
里程碑状态：not_ready
Full R3 Gate before / after：red / pending_reevaluation -> 无变化
Single-player Demo Gate before / after：unavailable / blocked_by_runtime_control_plane -> 无变化
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
公共 Skeleton 接口变化：无
```

完成断点：

- 同一 `room_id + plan_id` 的生成进度使用稳定 event ID；只有阶段、进度或错误级别变化才发布，文本变化和相同 heartbeat 不再追加消息。
- 生成进度与系统状态的用户可见 sender 统一为“系统”；旧乱码名称仅保留为历史输入识别，不再用于生产发送。
- Runtime AI 配置使用 canonical `Quasar` 根；同一进程首次加载后，其余 Worker 只记录 `config_load_deduped`，正常路径不再加载 plugin-qualified Hunyuan loader。
- `generate_report()` 对终态计划增加同版本证据门禁：`scene_entity_registry_ready`、`runtime_scene_world_consistency_audited`、`scene_world_snapshot_ready` 任一缺失时只发布 `report_pending`。
- Finalizer 在同版本 Registry、Consistency、Snapshot 证据齐全后发布或恢复 `report_ready`；最终事件显式包含实体数、Game-ready、needs-review、缺失字段计数、scene version 和 world fingerprint。
- 未修改 RuntimeGuard、EngineWriteGate、ToolCallGraph 执行边界、Skeleton DTO 或 C++。

验证证据：

```text
Game-ready / Snapshot / Finalizer：39 passed
Quasar canonical/once、稳定 progress event、heartbeat、late finalizer：8 passed
Native sync + Walking Skeleton：15 passed
F5 probe：4 passed
actor import failure 阶段报告回归：1 passed
Python syntax compile：passed
Skeleton Manifest hash：sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1（不变）
```

总门禁事实：

- 首轮 `verify_ultimate_plan.py` 在 900 秒上限超时，并定位到一个旧断言仍要求未经过 Finalizer 的失败批次直接发布 `report_ready`。
- 该断言已按新终态顺序改为 `report_pending`，对应单测通过。
- 修复后第二轮总门禁运行 1800 秒，仍停留在既有 `test_agent_runtime_phase1.py` 长时路径；输出未出现新的失败，但全门禁没有在时限内结束，因此不得记为总门禁通过。
- 按测试预算不继续第三次重跑，不把慢测试治理扩入 B5.4。

未验证与边界：

- 真实 LANChat 是否原位更新同一进度事件、同进程是否只有一次 Quasar 服务初始化、用户披露是否严格按 Snapshot/Registry/Consistency/Report 顺序，均为 `[待F5/实机验证]`，在 B7.1/B7.2 验收。
- B5.1-B5.4 均已达到代码完成，但控制面 P0 只有 B7.1 固定五轮实机通过后才能标记 verified。
- 历史阻断 `request.b2.2-engine-dto-version` 保留：B2.2a ready，B2.2b deferred_to_B7。

下一唯一主线任务：**B2.2a current-unversioned-v1 严格 fixture**。

## 88. 2026-07-20 B2.2a current-unversioned-v1 严格 fixture 完成

```text
任务 ID / 状态：B2.2a / code_complete
执行角色：填充 AI
contract_status：current-unversioned-v1 strict fixture verified
production_integration_status：pending B6.2 [待F5/实机验证]
Full R3 Gate before / after：red / pending_reevaluation -> 无变化
Single-player Demo Gate before / after：unavailable / blocked_by_runtime_control_plane -> 无变化
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
公共 Skeleton 接口变化：无
```

完成断点：

- 在 `schema_versions.py` 集中登记 `ENGINE_SNAPSHOT_INPUT_CONTRACT_VERSION=current-unversioned-v1`，未在 Adapter 模块重复声明版本字符串。
- 新增严格 native Snapshot 输入契约，冻结当前 C++ `get_editor_scene_snapshot_from_python()` 顶层字段、`actor_to_json()` 必填/条件字段、Camera/Geometry/AABB 嵌套字段和 schema fingerprint。
- 当前 Engine build fingerprint 冻结为 `3d849a9a+patch-0c651bd4`；不匹配 build 直接返回 `engine_snapshot_build_fingerprint_mismatch`。
- 成功输入必须具有稳定 `actor_guid/entity_id/asset_id/model_ref/source_plan_id/source_batch_id`、正版本、actual world AABB 和显式 render observation；缺失事实不通过别名或默认值猜测。
- 未知顶层字段、未知 Actor 字段、AABB 缺失、actor/version 不一致和稳定身份缺失均 fail closed。
- 严格验证通过后才复用现有 `_normalize_scene_snapshot_result()`；未改变生产 Snapshot Provider 的宽兼容入口，本契约将在 B6.2 接入当前 SHA 的只读对账路径。

验证证据：

```text
strict current fixture：5 passed
Capability port + strict fixture + collaboration contracts：22 passed
既有 Snapshot Provider 归一化/scene context/route/count：4 passed
Python syntax compile：passed
Schema fingerprint：确定性 sha256
Skeleton Manifest hash：sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1（不变）
```

未验证与边界：

- 本任务没有声称 Engine 已提供显式 `input_dto_version`；`request.b2.2-engine-dto-version` 与 B2.2b 继续保留并推迟到 B7 跨 SHA 集成。
- build fingerprint 由当前集成配置注入，真实 bridge 尚未把该值随 Snapshot 传递；B6.2 只能对当前冻结 SHA 做严格只读对账。
- current-unversioned-v1 不代表通用旧/新 DTO 兼容，也不允许字段存在性猜版本。

下一唯一主线任务：**B6.3 single_player_demo Gate profile**。

## 89. 2026-07-20 B6.3 single_player_demo Gate profile 完成

```text
任务 ID / 状态：B6.3 / verified（纯 evaluator）
执行角色：填充 AI
production_integration_status：not_connected，等待 B6.1/B6.2
Full R3 Gate before / after：red / pending_reevaluation -> 无变化
Single-player Demo Gate before / after：unavailable / blocked_by_runtime_control_plane -> evaluator_available / not_evaluated
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
公共 Skeleton 接口变化：无
```

完成断点：

- 新增中立强类型 `DemoReadinessRequirement(requirement_id/semantic_role/required_capabilities/min_count)`；Runtime 与协作层均可引用，Runtime 不读取 GameplayLogicPlan。
- 协作层从任意 `GameplayEntitySlot` 动态派生 requirements；Gate 实现中不存在 `player_spawn/collectible_key/locked_door/goal_zone` 场景硬编码。
- `evaluate_r3_gate()` 新增 `profile=full_r3|single_player_demo`；默认 `full_r3` 的七维状态和 capability unlock 语义保持不变。
- 单人 entity readiness 只匹配具有稳定身份、已验证 Game-ready 且满足 capability 的实体，并要求不同 slot 使用不同 entity_id。
- GateReport metrics 记录 requirements fingerprint、逐 requirement 匹配 entity IDs 和诊断；相同事实产生确定性结果。
- 单人 multiplayer 维度要求 `project_mode=single_player`、peer count 为 0 且无身份/版本漂移。
- Single-player Green 只解锁 `single_player_entity_binding/single_player_local_action/single_player_preview`，不解锁多人或完整 R3 capability。
- `runtime.r3_readiness.evaluate` 接受结构化 profile/requirements/project_mode，调用前后 RuntimeState、OperationLog、ToolGraph 和 PlanPatch 保持不变。

验证证据：

```text
R3 readiness + single-player profile：27 passed
Integration contracts + collaboration contracts + ProgramAgent + Gate：67 passed
动态 role/capability、缺能力、实体不可复用、Full R3 不变、零副作用：passed
Gate 源码禁用四个场景特定 role 字符串：无匹配
Python syntax compile：passed
Skeleton Manifest hash：sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1（不变）
```

未验证与边界：

- 本任务只证明 evaluator；没有读取真实 Snapshot、没有构造 EntityBindingPlan/ActionProposal，也没有改变 Full R3 Gate。
- 当前单人 Gate 尚未对生产 Runtime 世界执行，实际状态为 `evaluator_available / not_evaluated`。
- requirements 必须由后续 ProjectGate/协作入口从已验证 GameplayLogicPlan 派生，禁止聊天文本或显示名称直接构造绑定。

下一唯一主线任务：**B6.1 真实 UserCommand -> DemoRunner 只读接入**。

## 90. 2026-07-20 B6.1 真实 UserCommand -> DemoRunner 只读接入完成

```text
任务 ID / 状态：B6.1 / code_complete [待F5/实机验证]
执行角色：填充 AI
contract_status：只读协作入口与生产兼容 LANChat 路由已验证
production_integration_status：LANChat/Frontend 实际收发待 B7.1 F5
Full R3 Gate before / after：red / pending_reevaluation -> 无变化
Single-player Demo Gate before / after：evaluator_available / not_evaluated -> 无变化
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
公共 Skeleton 接口变化：无
```

完成断点：

- 新增生产兼容、非执行型 `CollaborationReadOnlyEntry`：正式链路为 `UserCommand -> FrontendBusinessProtocolAdapter -> UserCommandFixture -> DemoScenarioRunner -> Artifact bundle / Preflight / DemoResult -> ProgressEvent`。
- 入口仅接受 `start_project`；返回结果永久 `executable=False`，不构造 ActionProposal、EntityBindingPlan、PlanPatch、ToolCallGraph，也不写 Engine。
- `command_id` 相同且内容相同的重放直接复用缓存结果，零新增 Agent 运行和进度事件；相同 ID 不同内容 fail closed。
- LANChat 只显式识别结构化 `command_type=start_project` 与 `/start_project <goal>`，普通聊天不会被协作入口认领。
- 结构化命令使用稳定 command/project/scenario ID，产生两条 `action_status`：项目请求受理与 Artifact/Preflight 结果就绪。
- 命令只产生一条 final reply；同一 `message_id` 重放由 MessageDispatchLedger 拦截，不重复执行、不重复回复。
- 缺少项目目标时只返回澄清，零 Artifact、零进度事件、零 Runtime/Engine 写入。
- 协作只读入口本身不 import AgentRuntime、LANChat、Frontend 组件或 C++ 实现；LANChat 仅作为兼容命令接入层。

验证证据：

```text
CollaborationReadOnlyEntry：5 passed
LANChat start_project 生产兼容路由：4 passed
Walking Skeleton：10 passed
Frontend Adapter：6 passed
B5.1 消息执行/最终回复去重回归：3 passed
组合门禁：28 passed
Python syntax compile：passed
Skeleton Manifest hash：sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1（不变）
```

未验证与边界：

- 真实 Frontend 是否发送结构化 `start_project`、C++ LANChat 是否保持 metadata/payload、两条 `action_status` 是否原位正确展示，均为 `[待F5/实机验证]`，在 B7.1 验收。
- 本任务没有读取真实或 Mock Snapshot；测试 fixture 只进入非执行型 Artifact 链，没有冒充 Runtime 世界事实。
- Full R3 Gate 保持 Red；Single-player Demo Gate 仍只是 evaluator available，未对生产 Snapshot 执行。

下一唯一主线任务：**B6.2 current Engine Adapter 严格对账**。

## 91. 2026-07-20 B6.2 current Engine Adapter 严格对账完成

```text
任务 ID / 状态：B6.2 / code_complete [待F5/实机验证]
执行角色：填充 AI
contract_status：current-unversioned-v1 strict reconciliation verified
production_integration_status：当前 SHA integration_ready；真实 C++ reader/capability 输出待 B7.2 F5
Full R3 Gate before / after：red / pending_reevaluation -> 无变化
Single-player Demo Gate before / after：evaluator_available / not_evaluated -> evaluator_available / awaiting_current_engine_f5
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
公共 Skeleton 接口变化：无
```

完成断点：

- 新增 `make_current_unversioned_v1_scene_snapshot_reader()`：当前 build 的 native Snapshot 必须先经过严格字段/build/actual fact 校验，再进入既有 Runtime 归一化。
- 新增 `CurrentEngineAdapterReconciler`，只读组合 Engine capability manifest 与严格 Snapshot；输出 capability、input/schema/build fingerprint、稳定 `plan_id + scene_version` 和归一化 Snapshot。
- 对账要求 Engine 明确支持 `scene_snapshot.read`、`actual_aabb`、`render_ready`；缺任一项时在读取 Snapshot 前 fail closed。
- 当前 Snapshot 的所有 Actor 必须共享一个 `source_plan_id` 和一个 `source_scene_version`；actor/entity identity 不得重复。
- unknown field、build mismatch、缺 actual AABB/render observation、plan/version drift 和 identity drift 均返回结构化 `BlockedResult`，不使用默认值或别名猜测事实。
- 语义 scene name 与 native scene route 分离；严格 reader 只把显式 `scene_route` 传给 C++，避免只读对账触发场景反复 reload。
- 对账结果永久 `executable=False`；未新增 EngineWriteGate、RuntimeCppBridge 或任何公共写方法。

验证证据：

```text
Current Engine reconciliation + strict fixture：9 passed
Capability port + R3/single-player Gate + Walking Skeleton + Snapshot identity/render 回归：52 passed
未知字段/build、缺 capability、plan/version/entity drift：全部 fail closed
Python syntax compile：passed
Skeleton Manifest hash：sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1（不变）
```

未验证与边界：

- 当前 Engine 仍未提供显式 `input_dto_version`；B2.2b 继续推迟到跨 SHA 集成，不把 current-unversioned-v1 宣称为通用契约。
- 真实 capability manifest 是否包含三项 observation operation、native Snapshot 是否精确匹配冻结字段/build fingerprint，均为 `[待F5/实机验证]`。
- 本任务没有把严格对账结果写入 RuntimeState，也没有执行 Single-player Demo Gate；真实 Gate 仍保持 Red。

下一唯一主线任务：**B7.1 控制面 F5 证据包**。

## 92. 2026-07-20 B7.1 控制面 F5 证据包完成

```text
任务 ID / 状态：B7.1-evidence / verified（自动探针）
实机任务状态：B7.1 / ready_for_f5 [待F5/实机验证]
执行角色：填充 AI
Full R3 Gate：red / pending_reevaluation
Single-player Demo Gate：evaluator_available / awaiting_current_engine_f5
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
```

完成断点：

- `r3_f5_log_check.py` 新增独立 `--profile control-plane`，B7.1 不再被 Scene Runtime/R3 Gate 结果混淆。
- 固定检查计划中的五轮原始对话，缺失、重复或临时改写任一轮均 fail closed。
- 每轮要求恰好一个 processing owner、一条 final reply、正确目标 Agent 和显式 `LANChatModelCallSummary`。
- 模型预算固定为：讨论/方案消息最多 1 次；确认消息 0 次。
- 确认消息必须能观察到稳定 plan/artifact 引用；同时复用重复回复、目标权威、heartbeat、实体片段、Quasar 根、编码和诊断披露检查。
- 新增 `docs/probes/B7.1控制面F5验收包.md`，冻结执行前提、五轮输入、唯一命令、通过口径和推进记录回写字段。

验证证据：

```text
B7.1 probe 单元测试：6 passed
历史 2026-07-19 fixture：可自动判定固定轮次缺失及既有控制面失败
显式 0-call LANChatModelCallSummary：可被识别为 explicit
Python syntax compile：passed
```

当前硬边界：

- 代码侧已到真实 F5 边界；在取得新 log/history 前不得标记 B7.1 verified，也不得进入 B7.2。
- 下一次 F5 只执行控制面五轮，不同时扩大到最小 Scene Runtime 或完整玩法 Demo。
- 若摘要不是 `B7_1_CONTROL_READY`，只修对应 control check，不修改 B6.4 或玩法执行链。

下一动作：按 `docs/probes/B7.1控制面F5验收包.md` 执行 F5，并提供本次 `_corona.log` 与 LANChat `history.jsonl`。

## 93. 2026-07-20 B6.4 契约层完成与 Runtime 传输接口变更请求

```text
任务 ID / 状态：B6.4-contracts / code_complete
Runtime submit 状态：interface_change_required
执行角色：填充 AI
Full R3 Gate：red / pending_reevaluation
Single-player Demo Gate：evaluator_available / awaiting_current_engine_f5
Skeleton contract version/hash：r3-skeleton-week1-v4 / sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1
InterfaceChangeRequest：request.b6.4-gameplay-plan-patch-payload
```

完成断点：

- 新增 `GameplayEntityBinding`、`GameplayManifest` 和 `ActionProposal` 强类型契约；版本常量集中登记在 `schema_versions.py`。
- `GameplayManifest` 只接受 `on_enter/on_collect/set_state/unlock/complete_objective`，拒绝未知 primitive、未知参数、未绑定 slot、重复 entity 和不一致 objective。
- `EntityBindingPlan` 的 binding 行现在强制包含 `slot_id/entity_id/entity_version/asset_id/semantic_role/required_capabilities`，并拒绝未知字段、重复 slot 和重复 entity。
- `ActionProposal` 构造阶段实际调用 `assert_executable()`；Mock、non-executable、非 runtime Snapshot、stale world version、Red Gate 和错误 execution scope 均无法构造。
- 新增 `ProjectGateService`：真实检查 Artifact schema/content hash/status/dependency、Snapshot plan/version/fingerprint/Game-ready、实体 ID/version/asset/role/capability 和 single-player Gate unlock。
- 合法纯契约输入可确定性形成 `GameplayManifest` 与 `ActionProposal(operation=gameplay.apply_manifest, execution_scope=single_player_local)`；该结果只表示提交资格，不表示 Runtime 或 Engine 已执行。
- 协作层新模块不 import AgentRuntime、LANChat、RuntimeGuard、EngineWriteGate 或 RuntimeCppBridge；没有新增生产写入口。

验证证据：

```text
B6.4 ProjectGate/ActionProposal 正常与失败路径：6 passed
Contracts/ArtifactRegistry/ProgramAgent/Five Artifact/Skeleton 回归：61 passed
Mock 构造 ActionProposal：硬拒绝
Red/stale/needs-review/未知 primitive：结构化 blocked 或 invalid
Python syntax compile：passed
Skeleton Manifest hash：sha256:e60094df4323164cf2461f670e9a0bfafd18ba6cfbf3c67762ea3c09304fc7a1（不变）
```

接口阻断：

- 现有 `PlanPatch` 仅有文本和字符串 `items`，没有承载结构化 `GameplayManifest` 的字段或批准的 payload reference。
- 将 Manifest 编码进 `text/items` 会破坏强类型契约、审计能力和 RuntimeGuard 边界，禁止采用。
- 已生成 `request.b6.4-gameplay-plan-patch-payload`，要求架构 AI 决定结构化 gameplay payload 如何从 ActionProposal 进入 PlanPatch/ToolCallGraph。
- 在该请求决策前，不得注册 `gameplay.apply_manifest` 生产 ToolDefinition，也不得声称 B6.4 Runtime submit code_complete。

保留阻断：

- `request.b2.2-engine-dto-version` 继续存在，未被覆盖或清除。
- B7.1 控制面 F5 证据包已经 ready；B7.2/B7.3 证据包尚未落盘，因为本轮触发冻结接口硬停止条件。

下一动作：架构 AI 审批、拒绝或改写 `request.b6.4-gameplay-plan-patch-payload`；决策前停止后续运行时接线。

## 94. 2026-07-20 B6.4 PlanPatch v5 接口变更与 Runtime 提交链完成

```text
任务 ID / 状态：B6.4-runtime-submit / code_complete [待F5/实机验证]
执行角色：架构 AI
InterfaceChangeDecision：accepted / request.b6.4-gameplay-plan-patch-payload
contract_status：versioned PlanPatch + guarded Runtime submit verified
production_integration_status：provider_not_injected / blocked_by_B7.2
Full R3 Gate before / after：red / pending_reevaluation -> 无变化
Single-player Demo Gate before / after：evaluator_available / awaiting_current_engine_f5 -> 无变化
Skeleton contract version/hash：r3-skeleton-week1-v5 / sha256:ba41ac25b17559369fb79778fbaa061adf74d543c9f8262dd6dd8f34de2b98c8
```

完成断点：

- 接受并记录 `request.b6.4-gameplay-plan-patch-payload`；Skeleton 从 v4 升至 v5，Manifest 明确登记 `ActionProposal`、`GameplayManifest` 和完整 `PlanPatch` 公共字段。
- `PlanPatch` 新增 `patch_type=gameplay_manifest_apply`、`payload_schema_version`、`structured_payload`、`payload_hash`、`proposal_id`，旧文本型 Patch 缺少这些字段时仍可读取、恢复和回放。
- `structured_payload` 由 Runtime 独立执行严格 schema、白名单 primitive、未知字段、entity slot、objective 和 canonical SHA-256 校验；不能只信任协作层 Validator。
- `ActionProposal` 的幂等身份统一为 `command_id + payload_hash`；同一已提交请求重放时零新增 PlanPatch、业务 ToolGraph 和 Engine manifest apply。
- 新代码路径为 `ActionProposal -> versioned PlanPatch -> business_action ToolCallGraph -> RuntimeGuard -> gameplay.apply_manifest -> EngineWriteGate/RuntimeCppBridge -> StatePatch receipt`。
- `make_engine_gameplay_manifest_provider()` 在 EngineWriteGate 前检查 capability manifest；缺少 `gameplay.apply_manifest`、缺少任一白名单 primitive 或缺少 Engine tool 时 fail closed。
- 默认 AgentRuntime 在没有真实 gameplay provider 时不注册 `gameplay.apply_manifest`，提交返回 blocked，且零 PlanPatch、零 ToolGraph、零 Engine 写入；因此未越过 B7.2 激活门槛。
- 成功 receipt 只记录稳定 proposal/hash/idempotency/status 事实，不把原始 Engine payload 或任意脚本写入 RuntimeState。

接口变更重验：

```text
旧 v4/hash 消费者：stale / revalidation_required
B0.4 Walking Skeleton + public Manifest/hash：passed
协作层 Runtime/Frontend/C++ import isolation：passed
legacy PlanPatch compatibility：passed
normal gameplay PlanPatch + canonical hash：passed
hash tamper / unknown primitive：blocked
RuntimeGuard + EngineWriteGate spy：passed
same command_id + payload_hash replay：zero duplicate business graph/apply
missing provider / unadvertised capability：fail closed
聚焦回归：82 tests passed
Python syntax compile：passed
```

未验证与边界：

- 真实 Engine capability manifest 是否广告 `gameplay.apply_manifest` 和五项 primitive、C++ gameplay tool 是否返回稳定 receipt，均为 **[待 F5/实机验证]**。
- 当前未把 provider 注入 LANChat/F5 生产 Runtime；B7.2 最小 Scene Runtime F5 和 Single-player Gate Green 前不得激活。
- `request.b2.2-engine-dto-version` 继续保留，未被本次 PlanPatch 变更覆盖。
- B7.3 仍需两个独立 Session，并在 Session A 内验证相同 command/hash 重放零重复。

下一动作：执行 B7.1 控制面 F5；不依赖实机结果的并行任务为准备 B7.2 Scene Runtime 和 B6.4 gameplay write receipt 验收包。

## 95. 2026-07-20 单人垂直切片 F5 边界证据包收口

```text
任务 ID / 状态：B7-evidence-packages / verified（文档与代码位置核对）
执行角色：架构 AI
contract_status：M1/M2/M5 non-F5 work exhausted
production_integration_status：awaiting staged F5
Full R3 Gate：red / pending_reevaluation
Single-player Demo Gate：evaluator_available / not_evaluated
Skeleton contract version/hash：r3-skeleton-week1-v5 / sha256:ba41ac25b17559369fb79778fbaa061adf74d543c9f8262dd6dd8f34de2b98c8
```

新增证据包：

- `docs/probes/B7.2最小SceneRuntime_F5验收包.md`：固定 `room_box + room_floor + 1 actor`，核对身份、actual AABB、render observation、Registry/Snapshot/Finalizer 和终态顺序。
- `docs/probes/B6.4Gameplay写入回执_F5验收包.md`：核对 capability manifest、versioned PlanPatch、RuntimeGuard、EngineWriteGate、receipt 与同 command/hash 零重复。
- `docs/probes/B7.3单人垂直切片双Session_F5验收包.md`：两个独立 Session 各完成 40-50 秒流程，并在 Session A 内执行一次同 command/hash 重放。

当前任务审计：

```text
B5.1-B5.4：code_complete [待F5]
B2.2a：code_complete
B6.3：verified（纯 evaluator）
B6.1-B6.2：code_complete [待F5]
B6.4 contract/runtime submit：code_complete [待F5]
B7.1/B7.2/B6.4 receipt/B7.3：证据包 ready，等待分阶段 F5
```

未解决 blocked：

- `request.b2.2-engine-dto-version`：等待 Engine 显式 input DTO version，仅阻断跨 SHA 最终集成。
- B7.1：等待控制面五轮 F5。
- B7.2：等待最小 Scene Runtime F5。
- B6.4 production activation：等待 B7.2 通过、single-player Gate Green 和真实 gameplay capability/tool。
- B7.3：等待前述门槛通过后执行两个独立 Session。

边界结论：

- 当前没有剩余可独立推进的非 F5 代码任务；继续修改将依赖尚未观察到的真实 Engine/Frontend 事实。
- 单人切片已达到“代码层 integration-ready，只差分阶段 F5 与真实 Engine gameplay receipt”的状态，但尚未达到实机 verified。
- 原连续目标中的 `fd65...` 基准已被用户批准的 B6.4 公共接口变更替代；当前权威 hash 为 v5 `ba41...`，旧 v4 消费者已标 stale 并完成重验。

下一动作：严格先执行 `docs/probes/B7.1控制面F5验收包.md`；通过后依次执行 B7.2、B6.4 write receipt、B7.3，不合并为一次长跑。

## 96. 2026-07-20 B7.1 固定五轮控制面 F5 失败校准

```text
任务 ID / 状态：B7.1-F0 / verified（失败证据已固化）
执行角色：架构 AI
B7.1：blocked / control_plane_f5_failed
B7.2：blocked_by_B7.1
Full R3 Gate：red / pending_reevaluation
Skeleton contract version/hash：r3-skeleton-week1-v5 / sha256:ba41ac25b17559369fb79778fbaa061adf74d543c9f8262dd6dd8f34de2b98c8
```

实机证据：

```text
log：build/examples/engine/RelWithDebInfo/logs/2026-07-20_12-54-21_corona.log
history：build/examples/engine/RelWithDebInfo/Saved/LANChat/history/single-default__session__1784523561529__1.jsonl
probe：B7_1_CONTROL_BLOCKED / PASS=10 WARN=0 FAIL=5
失败检查：
  control-target-authority
  control-single-processing-owner
  control-finalizer-disclosure-order
  control-quasar-import-root
  b7.1-turn-contract
```

五轮诊断摘要：

| 轮次 | 路由/owner 事实 | final reply | 模型调用 | 方案引用与结果 |
|---|---|---|---|---|
| `@小女孩 围绕迪士尼乐园主题讨论一下` | Native Queue 先更新 `seed-91cc7143f47c`，Agent Trigger 再处理回复 | 1，小女孩 | 0 | 回复引用无关 `plan-6099e4ac` |
| `@小女孩 按照迪士尼风格的卧室来设计呢` | Native Queue 与 Agent Trigger 均参与业务处理 | 1，固定 Runtime 警告 | 1 | 模型结果未形成可确认方案，缺稳定 artifact ref |
| `@GM 确认生成` | Native GM 路由被去重 | 0，仅 action status | 0，但缺显式 summary | 返回“当前没有可确认事项” |
| `@长者 请你给出一个方案` | Native Queue 仍触碰 SeedPlan，Agent Trigger 产出方案 | 1，长者 | 0 | 方案为 `plan-b42d336d` |
| `@长者 确认开始` | 实际进入 Runtime 生成 | 1，但 sender 为系统 | 0 | 执行文本引用 `plan-b42d336d`，Runtime 新建 `plan-21b28a665a24` |

终态与启动问题：

- 用户可见顺序出现 `report_ready -> 后续内部调用 -> scene_snapshot_refreshed`，同版本终态披露不可信。
- 同进程同时初始化 `Quasar` 与 `plugins.AITool.Quasar`，AI 配置、媒体注册表和路径单例存在分裂风险。
- 底层执行仍有正向证据：3/3 业务 Batch、3/3 业务 ToolGraph、54/54 业务节点、Engine bridge 16/16、9 个 reported Game-ready；因控制面与终态失败，不作为 B7.2 或 R3 Green 证据。

下一唯一主线：`B7.1-F1 入口单一认领`。修复顺序固定为 F1 消息 owner -> F2 方案身份/确认事务 -> F3 回复契约 -> F4 终态披露 -> F5 Quasar 单根 -> F6 probe/组合门禁；在新的五轮 F5 输出 `B7_1_CONTROL_READY` 前不得进入 B7.2。

## 97. 2026-07-20 B7.1 控制面失败修复代码收口

```text
任务 ID / 状态：B7.1-F1..F6 / code_complete [待F5/实机验证]
执行角色：架构 AI
B7.1：repair_code_complete / ready_for_f5
B7.2：blocked_by_B7.1
Full R3 Gate：red / pending_reevaluation
Skeleton contract version/hash：r3-skeleton-week1-v5 / sha256:ba41ac25b17559369fb79778fbaa061adf74d543c9f8262dd6dd8f34de2b98c8（不变）
```

完成断点：

- 显式非 GM Agent 的 Native Queue 副本在 ConversationTurnContext、Coordinator、SeedPlan、Runtime 和生成配置修改前退出；正式执行 owner 由 `MessageDispatchLedger.claim_execution()` 记录。
- GM Native 路径在业务副作用前 claim；同消息 Agent Trigger 重放只命中 dedupe，零重复 final reply、零重复 Runtime enqueue。
- 方案外部身份统一为 `proposal_id == agent_plan_id`、`artifact_ref=legacy-plan:<proposal_id>`；Runtime `external_plan_links[artifact_ref]` 显式指向内部 `runtime_plan_id`。
- 普通讨论不创建 Runtime ScenePlan；`plan_drafting` 即使 UI metadata 为 `draft_action=chat`，仍产出正式规划方案并绑定稳定 artifact。
- 确认改为 `pending -> confirming -> confirmed/pending` 事务；Runtime enqueue 失败时方案恢复 pending，不会被提前消费。
- GM 唯一方案确认由 GM final reply；显式 Agent 确认由目标 Agent final reply。回复 metadata 增加 `proposal_id/agent_plan_id/artifact_ref/runtime_plan_id/reply_contract/resolved_intent`。
- RuntimeEvent 披露改为每房间 event-id 游标和串行锁；重叠 watcher 不重复发送，终态事件不再截断为最后三条。
- `scene_snapshot_refreshed` 携带 `plan_id + scene_version`；同版本 `report_ready` 后若观察到终态前置事件，记录 `runtime_event_disclosure_terminal_violation` 并阻止错误披露。
- Editor warmup 与 Worker 生产路径统一使用 canonical `Quasar`；删除 plugin-qualified fallback 和双命名空间同步，canonical 不可用时 fail closed。
- 控制面 probe 改为读取 Ledger 正式 owner，新增 `control-native-defer-zero-mutation`，并校验 `reply_contract + resolved_intent`；旧 2026-07-20 实机证据仍稳定输出 blocked，typed 五轮 fixture 输出 ready。

验证证据：

```text
B7.1 控制面/方案/终态/Quasar/probe 聚焦组合：26 passed
RuntimeActionIntent：11 passed
Native GM owner + Agent Trigger replay：1 passed
合计聚焦证据：38 passed
Python syntax compile：passed
旧 2026-07-20 log/history 更新后 probe：B7_1_CONTROL_BLOCKED / PASS=10 WARN=0 FAIL=6
固定五轮 typed fixture：B7_1_CONTROL_READY / WARN=0 FAIL=0
verify_ultimate_plan.py：运行一次，900 秒超时；仅输出连续通过点，无断言失败，未完整结束
```

未验证与边界：

- C++ Native Queue 与 Agent Trigger 的真实线程时序、Frontend metadata 保留、同进程 Quasar 单根初始化和 Finalizer 用户披露顺序仍为 **[待F5/实机验证]**。
- 旧日志不会因代码修复变为通过证据；必须使用全新独立 Session 重跑固定五轮。
- B7.2、Gameplay write receipt 和 B7.3 继续阻断，不因自动测试通过提前解锁。

下一动作：严格按 `docs/probes/B7.1控制面F5验收包.md` 使用全新 Session 原样执行五轮对话；只有真实 log/history 的 probe 输出 `B7_1_CONTROL_READY` 且 WARN/FAIL 均为 0，才将 B7.1 标记 verified 并进入 B7.2。

## 98. 2026-07-20 C1-C5 真实讨论、三职能协作与严格媒体链代码收口

```text
任务 ID / 状态：C1-C5 / code_complete [待F5/实机验证]
执行角色：架构 AI
B7.1：blocked / ready_for_retest
B7.2：code_complete / blocked_by_B7.1
Full R3 Gate：red / pending_reevaluation
Skeleton contract version/hash：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd
```

完成断点：

- `ConversationPhase` 已建立；讨论/问候不再创建 Proposal 或 Runtime ScenePlan，方案请求进入正式三职能 Coordinator。
- 生产依赖固定为 `Planning -> Program logic -> Art`，五个强类型 Artifact 由 GM 单一汇总回复；旧 persona 只保留兼容 sender。
- 方案和确认统一携带 `proposal_id/proposal_version/proposal_hash/artifact_refs`；修订递增版本，确认事务只消费当前匹配 hash 的 pending proposal。
- Skeleton 因 Program 公共接口和节点依赖变化升至 v6；旧 v5 下游视为 stale，v6 Walking Skeleton 已重验。
- F5 默认启用真实 image provider 和 strict image-to-model；缺图、Mock 图、hash 不符或 `text_to_3d` 降级均 fail closed。
- Runtime 新增只读 `R3MediaLineageTrace`，逐实体披露图片 ref/hash、模型 source image ref/hash 和 Engine Actor 事实，供 B7.2 自动探针核验。
- Finalizer 增加同世界锁与 `plan_id + scene_version + fingerprint` 短路；重复 watcher/后续聊天不得增加终态事件或 internal graph。
- B7.1 probe 升级为五个业务回合加一个问候探针；B7.2 新增独立 `scene-runtime` profile。

验证证据：

```text
C1-C5 + B7.1/B7.2 probe 聚焦组合：55 passed
B7.1 六消息 typed fixture：B7_1_CONTROL_READY / WARN=0 / FAIL=0
B7.2 严格媒体 fixture：B7_2_SCENE_READY / WARN=0 / FAIL=0
旧 18:30 F5 控制面：B7_1_CONTROL_BLOCKED / PASS=12 / WARN=0 / FAIL=4
旧 18:30 F5 Scene Runtime：B7_2_SCENE_BLOCKED / PASS=2 / WARN=0 / FAIL=4（无 R3MediaLineageTrace）
```

未验证与边界：

- 真实 Reasoner 是否针对讨论/问候作答、Frontend 是否完整保留版本化 metadata，仍为 `[待F5/实机验证]`。
- 真实图片 Provider 是否返回可用图片路径、模型 Provider 是否执行 `image_to_3d`、Actor 是否携带匹配血缘，仍为 `[待F5/实机验证]`。
- B7.1 未通过前不得用 B7.2 自动测试解锁 Gameplay provider、EntityBindingPlan 或 B7.3。

下一动作：按 `docs/probes/B7.1控制面F5验收包.md` 在全新 Session 严格执行六条固定消息；通过后立即按 `docs/probes/B7.2最小SceneRuntime_F5验收包.md` 执行最小真实媒体链 F5。

## 99. 2026-07-20 D1-D5 方案权威、真实三职能与媒体链修复收口

```text
任务 ID / 状态：D1-D5 / code_complete [待F5/实机验证]
执行角色：架构 AI
B7.1：blocked / control_plane_contract_failed
B7.2：blocked_by_B7.1
Full R3 Gate：red / pending_reevaluation
Skeleton contract version/hash：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd（不变）
```

完成断点：

- 生产方案链改为四次独立、无工具模型调用：`planning_artifact_reasoning -> program_artifact_reasoning -> art_artifact_reasoning -> collaboration_proposal_narration`；强类型或 hash 校验失败立即停止，不创建可确认 pending proposal。
- `gm_proposal` 使用唯一 `proposal_id + proposal_version + proposal_hash`，并携带 `reply_to/origin_message_id/origin_correlation_id/reply_contract`；Runtime 外部执行键改为 `proposal_id@version:hash`，不再按稳定 legacy artifact ref 复用旧计划。
- 无语义变化的修订不升版本；有效修订使用同一 proposal ID、递增版本、版本化 Artifact refs 和 supersedes 关系。
- 讨论/问候改走直接聊天模型，只读取当前消息、目标 Agent 和累计项目目标；不注入 Runtime 报告、旧 plan ID 或失败诊断。
- `generate_image` 的 `llm_content[].part[].content_url=fileid://...` 已接入 MediaRegistry resolver；图片 hash 只接受实际字节或 Provider 权威 hash，并输出明确失败码。
- 模型和 Actor 导入前均校验 `generation_mode=image_to_3d` 及 source image ref/hash；缺图、超时、解析失败、缺 hash 或血缘不一致均 fail closed。
- Finalizer 增加 `plan_id + scene_version + snapshot_fingerprint + terminal_status` 终态键；已持久化失败/完成终态不会因后续问候、讨论或查询再次生成 Finalizer 图。
- 同一 proposal 的可见进度使用稳定 event ID 原位更新，策划、程序、美术和 GM 阶段使用不同文案；B7 probe 支持合法 `gm_proposal`、连续空白规范化、四类 purpose、提示词泄露、终态键重复和图片失败码检查。

验证证据：

```text
D1-D5 + Runtime/Probe 聚焦组合：63 passed
Track B 协作层：108 passed
入口/上下文/媒体/Probe：35 passed
关键确认事务与终态披露：8 passed
受影响 Runtime Phase1 媒体用例：3 passed
Python syntax compile：passed
Skeleton v6 hash：保持 6144cabd...e1cd
```

未验证与边界：

- `test_agent_runtime_phase1` 全模块在 180 秒预算内超时，仅运行到 31 个通过点，未完整结束；本轮只将受影响媒体用例单独闭环，不声明全量门禁通过。
- 真实模型是否稳定返回四个 schema、Frontend 是否按稳定 event ID 原位更新、MediaRegistry 是否能在 F5 中解析真实 fileid、Hunyuan 是否接受解析后的图片输入，均为 `[待F5/实机验证]`。
- 旧 22:18 日志仍是失败证据，不因代码修复改写为通过；B7.1/B7.2/Full R3 状态保持 blocked/red。

下一动作：使用全新独立 Session 原样执行 B7.1 六条消息。只有 probe 输出 `B7_1_CONTROL_READY / WARN=0 / FAIL=0`，才进入 B7.2 最小真实媒体链 F5。

## 100. 2026-07-21 E0-E4 三职能契约与控制面修复收口

```text
任务 ID / 状态：B7.1-E0..E4 / code_complete [待F5/实机验证]
执行角色：架构 AI
B7.1：blocked / collaboration_program_contract_failed
B7.2：blocked_by_B7.1
Full R3 Gate：red / pending_reevaluation
Skeleton contract version/hash：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd（不变）
```

完成断点：

- `CollaborationReasoningError` 现在携带 `stage/error_code/field_path/safe_summary/response_hash`；生产日志不再只记录异常类型，也不记录原始提示词或模型原文。
- Gameplay primitive 参数、capability、必填参数和无环规则提取为 Validator/Prompt 共用 Manifest；Program Reasoner 使用通过真实 Validator 的 `key -> door -> goal` 示例。
- 稳定错误码覆盖非法 JSON、缺字段、未知 slot、非白名单 primitive、capability 不匹配、非法参数、重复 ID 和循环引用。
- 协作模型选择保持可插拔，默认 `deepseek/deepseek-v4-pro`；Planning/Program/Art 使用 `json_object`，讨论与 GM Narrator 使用文本模式，结构化模式不可用时 fail closed。
- Walking Skeleton 增加内部 stage observer；策划/程序/美术完成后实时更新同一 ProgressEvent，失败阶段标 blocked，后续阶段标 not_started；公共 Protocol/hash 未改变。
- Coordinator 保存 `CollaborationAttemptReport`；状态查询最多六行展示四阶段状态，不再倾倒 Runtime 内部诊断。
- `@GM 让@小女孩 给我一个方案` 进入正式 Coordinator；完全相同的成功请求复用当前 Proposal，零额外模型调用、零版本增长。
- Narrator 失败时标记 narration blocked，并撤销候选 Proposal；不会留下用户不可见但可被确认的 pending 方案。

验证证据：

```text
E0-E4 生产 Reasoner/Coordinator/LANChat/模型策略聚焦：38 passed
Track B 协作层：116 passed
协作入口/只读入口/模型预算/意图组合：30 passed
B7.1/B7.2 probe 单元测试：10 passed
Python syntax compile：passed
旧 2026-07-21 01:10 log/history：B7_1_CONTROL_BLOCKED / PASS=11 WARN=1 FAIL=4（历史证据保持不变）
六轮只读回归 fixture：docs/probes/fixtures/2026-07-21_b7_1_three_role_conversation.json
```

未验证与边界：

- `deepseek-v4-pro` 是否接受 `response_format=json_object`、是否连续返回四份可校验结果，仍为 `[待F5/实机验证]`。
- Frontend 是否按稳定 event ID 原位更新四阶段进度、真实日志是否包含四类 purpose 和版本化 Proposal metadata，仍为 `[待F5/实机验证]`。
- 本轮没有进入图片、模型、Actor、GameplayManifest 或 Engine 写链；B7.2 继续由 B7.1 阻断。

下一动作：使用全新独立 Session 执行 B7.1 六消息验收；必须观察 `provider=deepseek model=deepseek-v4-pro`、四类 purpose、单 final reply、稳定 Proposal identity 和零 Runtime 诊断倾倒，探针达到 READY 后再进入 B7.2。

## 101. 2026-07-21 E5.0 最新 F5 校准与修复入口

```text
任务 ID / 状态：B7.1-E5.0 / verified（失败证据已固化）
执行角色：架构 AI
B7.1：blocked / collaboration_art_contract_failed
B7.2：blocked_by_B7.1
Full R3 Gate：red / pending_reevaluation
Skeleton contract version/hash：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd（不变）
```

实机证据：

```text
日志：build/examples/engine/RelWithDebInfo/logs/2026-07-21_02-54-38_corona.log
discussion：deepseek/deepseek-v4-pro，1 次 agent_visible_reasoning，成功
planning：completed
program：completed
art：blocked / gameplay_roles_missing / scene_composition_plan.entity_requirements
narration：not_started
proposal/runtime/media/actor：未进入
```

校准结论：

- E0-E4 的自动契约验证结论保留；本轮 F5 证明程序契约已跨过，但美术模型没有稳定复述程序权威 semantic roles。
- 单消息认领和单 final reply 在本轮三条消息中未观察到重复；DeepSeek 未回退 GPT，也没有连接错误。
- Program 调用持续约 211 秒，暴露默认 SDK 重试使 90 秒配置没有形成单阶段硬预算；方案状态查询同时被 Coordinator 长锁阻塞。
- Red 期间继续禁止 ActionProposal、EntityBindingPlan、ToolGraph、真实或 Mock Snapshot 输入和 Engine 写入。

下一唯一任务：`E5.1 semantic_role 权威传递与美术 Artifact 组装`。

## 102. 2026-07-21 E5.1 semantic_role 权威传递完成

```text
任务 ID / 状态：B7.1-E5.1 / code_complete
B7.1：blocked / collaboration_art_contract_failed
Skeleton contract version/hash：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd（不变）
```

- GameplayLogicPlan Validator 新增 semantic_role 唯一性检查。
- Art Reasoner 从已验证 slot 构建有序角色 Manifest；最终 `entity_requirements` 和逐角色 `image_prompts` 由系统权威组装。
- 美术模型只产出 ArtDirection、场景环境/布局、全局视觉提示和可选角色视觉覆盖；未知角色和缺失全局提示 fail closed。
- 聚焦验证：Production Reasoners + LANChat Collaboration Proposal，20 passed。

下一唯一任务：`E5.2 非阻塞 Coordinator 与实时 AttemptReport`。

## 103. 2026-07-21 E5.2 非阻塞 Coordinator 完成

```text
任务 ID / 状态：B7.1-E5.2 / code_complete
Collaboration schema version：1.2
Skeleton contract version/hash：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd（不变）
```

- `create_proposal()` 只在状态预留和最终提交阶段持锁，三职能模型调用在锁外运行。
- AttemptReport 从 Planning `in_progress` 开始，Stage Observer 实时推进 completed/in_progress/blocked/not_started。
- 同项目已有 inflight 尝试时返回 `collaboration_in_progress`，不启动第二条模型链。
- 状态查询可在模型任务阻塞期间立即读取；聚焦并发测试验证读取耗时低于 0.2 秒。
- Coordinator/LANChat/schema 聚焦验证：15 passed。

下一唯一任务：`E5.3 DeepSeek 零重试、90 秒预算与调用审计`。

## 104. 2026-07-21 E5.3 DeepSeek 调用预算收口

```text
任务 ID / 状态：B7.1-E5.3 / code_complete
协作阶段预算：90 秒 / max_retries=0
```

- `CollaborationModelSelection` 增加 `max_retries`，默认协作策略固定为 0。
- Quasar chat model 构造支持调用方覆盖重试次数；非协作调用继续保留默认 2 次重试。
- LANChat 模型调用日志增加 output_mode、timeout、max_retries、elapsed_ms、result 和 error_code。
- Timeout 映射为 `collaboration_stage_timeout`，同一职能只产生一次 Provider 调用。
- 模型策略/LANChat/Coordinator 聚焦验证：20 passed。

下一唯一任务：`E5.4 GM 回复、ProgressEvent 与 B7.1 Probe 对齐`。

## 105. 2026-07-21 E5.4-E5.5 控制面代码收口

```text
任务 ID / 状态：B7.1-E5.4..E5.5 / code_complete [待F5/实机验证]
B7.1：blocked / repair_code_complete / pending_independent_f5
B7.2：blocked_by_B7.1
Full R3 Gate：red / pending_reevaluation
Collaboration schema version：1.2
Skeleton contract version/hash：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd（不变）
```

完成断点：

- 讨论和问候继续由显式 persona 回复；正式方案、协作状态、协作失败与 Red Gate 确认阻断统一由 GM 回复。
- Stage Observer 现在披露 planning/program/art/narration 的 in_progress、completed 和 blocked；not_started 只保留在 AttemptReport，避免覆盖用户可见根因。
- Full R3 Red 时，结构化方案确认只核对 ID/version/hash/artifact refs，返回 `runtime_write_blocked` 并保留 pending proposal；旧非协作 Runtime 路由不受此开关影响。
- B7.1 Probe 要求每个方案四类 purpose、四条 ModelCallResult、单阶段不超过 90 秒、方案累计不超过 180 秒；确认固定零模型调用。
- F5 执行默认仍不启用 `AGENT_RUNTIME_ENABLE_COLLABORATION_WRITE`；B7.2 和 Single-player Gate Green 前不得打开。

验证证据：

```text
E5 Track B 协作层：134 passed
控制面/模型预算/意图/Probe：47 passed
受影响 Runtime Guard：5 passed
E5 重点组合：56 passed
Python syntax compile：passed
verify_ultimate_plan.py：运行一次，900 秒超时；134 个连续通过点，无断言失败，未完整结束
```

未验证与边界：

- `deepseek-v4-pro` 是否在真实网络下连续完成四阶段且单阶段低于 90 秒，仍为 `[待F5/实机验证]`。
- Frontend 是否对同一 event ID 原位更新四阶段进度、状态查询是否在实机线程中低于 1 秒，仍为 `[待F5/实机验证]`。
- B7.1 未通过前不进入图片、模型、Actor、Finalizer、GameplayManifest 或 B7.2 修改。

下一唯一任务：按 `docs/probes/B7.1控制面F5验收包.md` 使用全新 Session 原样执行六条消息；只有 `B7_1_CONTROL_READY / WARN=0 / FAIL=0` 才进入 B7.2。

## 106. 2026-07-21 E6 程序契约、硬超时与协作状态收敛

```text
任务 ID / 状态：B7.1-E6.0..E6.5 / code_complete [待F5/实机验证]
B7.1：blocked / collaboration_program_contract_failed / pending_independent_f5
B7.2：blocked_by_B7.1
Full R3 Gate：red / pending_reevaluation
Skeleton contract version/hash：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd（不变）
```

完成断点：

- 已固化 `2026-07-21_04-20-32` log/history。更新后的 Probe 可稳定重现重复 semantic role、260770ms 阶段超时、旧 Runtime 诊断倾倒、固定六轮不完整和控制面对 Runtime 的上下文污染。
- Program 生产 Reasoner 改用 `entity_roles` 映射作为模型输出；semantic role 经过规范化格式和唯一性校验，系统再组装公共 `GameplayLogicPlan.entity_slots`。重复 slot、role 和 primitive 分别产生稳定错误码。
- 新增 `CollaborationModelInvoker`：协作调用具有应用级 deadline、attempt/stage token、迟到结果丢弃和同房间饱和保护。完整 Proposal 共享 180 秒预算；Provider 仍固定 `max_retries=0`。
- 有 active/recent AttemptReport 时，通用 GM 状态查询优先返回最多六行的三职能状态；显式 Runtime/Engine 查询保持原有只读路径。
- 首次方案失败固定为 `plan_drafting + collaboration_blocked`。讨论、协作状态和失败回复不再写 AgentRuntime reply context、模型摘要或内部 ToolGraph。
- Probe 新增单阶段 90 秒、Proposal 180 秒、迟到模型结果和控制面 Runtime 零修改检查。

验证证据：

```text
Python syntax compile：passed
E6 Program/Invoker/ModelPolicy/LANChat/Probe 聚焦组合：59 passed
Track B 显式协作模块：123 passed
Collaboration ReadOnly/Context/Intent/Budget/Probe：26 passed
受影响 Runtime Guard 状态查询与旧 Runtime fallback：13 passed
受影响 Runtime Guard 直接场景兼容隔离：2 passed
旧 04:20 log/history（E6 Probe）：B7_1_CONTROL_BLOCKED / PASS=13 WARN=1 FAIL=4
```

未验证与边界：

- `deepseek-v4-pro` 是否在真实网络下连续完成 Planning/Program/Art/Narration，且每阶段低于 90 秒、总耗时低于 180 秒，仍为 `[待F5/实机验证]`。
- 迟到 Provider 请求是否会在真实 SDK 连接中及时退出只能由新日志确认；即使底层连接继续存活，其结果已不能提交 Artifact 或 Proposal。
- 全量 `test_lanchat_runtime_guard.py` 本轮运行到 300 秒上限时未完成；其中旧 Runtime fallback 测试会主动加载可选 Quasar 工具。与 E6 直接相关的 15 项已单独通过，不把全量超时记为通过。
- 本轮没有进入图片、模型、Actor、Finalizer、GameplayManifest 或 Engine 写链；B7.2 继续由 B7.1 阻断。

下一唯一任务：使用全新独立 Session 原样执行 B7.1 固定六条消息；另以辅助状态查询验证 AttemptReport 回复低于 1 秒。只有 `B7_1_CONTROL_READY / WARN=0 / FAIL=0` 才进入 B7.2。
# E7 执行覆盖（2026-07-22）

\`\`\`text
当前工作块：B7.1 E7 控制面修复
当前任务：全新独立 Session 原样执行 B7.1 六条消息
任务状态：code_complete / pending_f5
当前执行角色：实机验证
Full R3 Gate：red / pending_reevaluation
B7.1：blocked / collaboration_art_contract_failed（旧失败证据）；E7 修复待新的 F5 证实
B7.2：blocked_by_B7.1
Collaboration schema：1.3
Frontend interaction schema：r3-interaction-week1-v2
Skeleton：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd（不变）
\`\`\`

## 107. 2026-07-22 B7.1 E7 美术契约与控制面修复

- 只读失败证据已固化：\`docs/probes/fixtures/r3_f5/2026-07-22_19-37-55_corona.log.txt\` 与 \`2026-07-22_19-37-55_history.jsonl\`；原始 probe 结果为 \`B7_1_CONTROL_BLOCKED / PASS=14 / WARN=1 / FAIL=3\`。
- F5 正向事实：Discussion、Planning、Program 和 Art 均调用 \`deepseek/deepseek-v4-pro\`；Art 模型返回成功，但 \`avoid_keywords=[]\` 被本地 Artifact Validator 误判为非法，Narrator/Proposal/Runtime 未启动。
- E7 已修复：\`avoid_keywords\` 现在必须是字符串列表但可为空；\`style_keywords/palette/lighting\` 仍为非空列表。受影响旧 Artifact/Proposal 由协作 schema \`1.3\` 失效，不迁移失败尝试。
- E7 已修复：状态查询只接受明确查询短语；“给出/设计/做一个方案”优先进入 Collaboration Coordinator。成功 Proposal 的“再给一个方案”在后续请求中形成版本化修订；失败 Attempt 则重走 \`plan_drafting\`。
- E7 已修复：普通 \`@GM 确认生成\` 在旧 \`LANChatAgentOrchestrator\` 之前由 Coordinator 处理；无 Proposal 返回一条 \`collaboration_blocked\` final reply，有 Proposal 时核对 version/hash/artifact refs，Red 下保持 pending 且零 Runtime 写入。
- E7 已修复：\`ProgressEvent\` 携带 origin message/correlation；同一稳定 event ID 继续作为前端原位更新键。控制面 reply/model summary 保持在 RuntimeState 之外。
- 未扩展：本轮没有修改图片、模型、Actor、Finalizer、GameplayManifest 或 Engine 写链；Quasar capability warnings 记录为后续 B7.2a 输入，不构成本轮绕过条件。

验证证据：

\`\`\`text
E7 contracts/reasoners/intent/frontend/LANChat 聚焦组合：52 passed
新 F5 前状态：B7.1 blocked / pending_independent_f5
\`\`\`

下一唯一任务：使用全新独立 Session 原样执行 B7.1 固定六条消息，并运行 \`docs/probes/r3_f5_log_check.py --profile control-plane\`。只有 \`B7_1_CONTROL_READY / WARN=0 / FAIL=0\` 才将 B7.1 标记 verified。

## 108. 2026-07-23 B7.1 E8 Program 原语语义与伪循环收敛

```text
任务 ID / 状态：B7.1-E8.0..E8.4 / code_complete / pending_focused_verification
contract_status：GameplayLogicPlan participant semantics updated
production_integration_status：pending_independent_f5
B7.1：blocked / collaboration_program_contract_failed
B7.2：blocked_by_B7.1
Full R3 Gate：red / pending_reevaluation
Collaboration schema：1.3（不变）
Skeleton：r3-skeleton-week1-v6 / sha256:6144cabd279c57c8e843c585156e775f213d2575f1c61152100a426f5729e1cd（不变）
```

- 固化只读失败证据：`docs/probes/fixtures/r3_f5/2026-07-22_23-46-45_corona.log.txt` 与 `2026-07-22_23-46-45_history.jsonl`。该会话只有两条用户消息；Probe 为 `B7_1_CONTROL_BLOCKED / PASS=15 WARN=1 FAIL=2`，两项 FAIL 包含固定六轮缺失，不能作为完整 B7.1 的失败结论。
- 实机事实：Discussion 真实调用 `deepseek/deepseek-v4-pro` 并完成；Planning 10172ms 完成；Program 78831ms 返回后遭旧 `cyclic_reference` 拒绝；Art/Narration/Proposal/Runtime 未启动，Red 期间保持零 Runtime 业务写入。
- 修复：移除将全部 primitive participant 关系当作依赖 DAG 的 DFS；新增 `self_slot_reference`；继续校验 slot、primitive ID、semantic role、capability、参数白名单及必填参数。不同 primitive 可以复用 subject/target。
- Prompt/Manifest/Reasoner 统一为参与者语义；错误对象与日志保留 stage、error code、field path、response hash 和受限 diagnostic refs，不保存模型原文或提示词。
- 聚焦验证：Contracts、Production Reasoners 与 LANChat Collaboration Proposal 共 42 项通过；Python syntax compile 与 `git diff --check` 通过。全量 `test_lanchat_runtime_guard.py` 仍有 4 项旧 Runtime 路由期望失败，未作为 E8 通过证据，留待控制面后续单独收口。
- 验证边界：E8 聚焦测试通过后，使用全新独立 Session 完整运行 B7.1 六条消息；未得到 `B7_1_CONTROL_READY / WARN=0 / FAIL=0` 前，不进入 B7.2、媒体、Actor、Finalizer、GameplayManifest 或 Engine 写链。
