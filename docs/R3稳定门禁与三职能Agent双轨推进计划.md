# R3 稳定门禁与三职能 Agent 双轨推进计划

更新时间：2026-07-14
状态：当前权威推进计划
适用范围：Game-ready Scene Runtime 收口，以及策划 / 美术 / 程序三职能 Agent 的第一阶段接入

> 本文档取代 `Agent-native一步到位重构计划_实施计划修改版_后续协调版.md` 的当前执行口径。旧文档继续保留为架构演进和历史实现记录。
> 所有 Agent / Codex 任务同时遵守 `Agent任务约束循环_R3三职能协同版.md`。

---

## 1. 当前目标与起点

项目目标不是单点场景生成，而是：

```text
多人多 Agent 协同
-> 通用地形 / 场景实体生成
-> Game-ready Scene Runtime
-> 策划 / 美术 / 程序 Agent 协作
-> 后续 AI Game Demo
```

当前阶段只推进两件事：

```text
轨道 A：把 SceneWorldSnapshot 收口为可信的 Game-ready 场景事实
轨道 B：建立不依赖真实 Engine 写入的三职能强类型协作契约
```

当前基线：

- 轨道 A 的 W1.3-W1.8 已达到 `code_complete`；最近一轮扩展聚焦套件 49 项通过。
- 最近一次 F5 使用较旧代码，结果为 14 个实体中 3 个 Game-ready。
- 最新 Readiness、业务图分域、Finalizer 和 Peer Mirror 修复尚未重新 F5。
- 当前门禁状态为 `red / pending_reevaluation`，不得据此冻结 Snapshot v1。
- `services/agent_collaboration/` 的强类型契约、ProjectState、ArtifactRegistry、AgentTaskGraph 和三个非执行型职能 Agent 已达到 `code_complete`，但红灯期间没有生产入口，也不得接入真实或 Mock Snapshot。

---

## 2. 架构不变量

现有 AgentRuntime 主链继续作为唯一执行底座：

```text
ScenePlan -> BatchPlan -> ToolCallGraph
-> RuntimeGuard -> EngineWriteGate / RuntimeCppBridge
-> ToolResult -> StatePatch
-> RuntimeState -> OperationLog
-> scene_entity_registry -> SceneWorldSnapshot
```

所有后续实现必须满足：

1. 用户执行入口只能进入 AgentRuntime。
2. Agent 只产出结构化 Artifact 或 Proposal，不直接执行。
3. ToolCallGraph 是唯一工具执行编排。
4. RuntimeGuard 是唯一场景写权限判断。
5. ToolResult 只能通过 StatePatch 更新 RuntimeState。
6. RuntimeState 与 OperationLog 是执行事实源。
7. 真实 Engine 返回优先于计划、估算和 Agent 判断。
8. 三职能 Agent 只能通过 SceneWorldSnapshot 读取场景世界。
9. 旧 SceneComposer / ProgressiveWorkflow 不得恢复为用户主入口。
10. Runtime 层不得承担 Artifact 和项目协作语义校验。

---

## 3. 双轨推进与隔离边界

### 3.1 轨道 A：Game-ready Runtime

负责：

- Environment、Actor、Geometry 的 Engine-ready 事实。
- Readiness reconcile 与 `readiness_missing_fields`。
- Registry、Snapshot、Fingerprint 与 Finalizer。
- 业务 Batch / ToolGraph 对账。
- 房主与成员的实体身份和版本一致性。
- F5 自动证据和红黄绿判定。

### 3.2 轨道 B：三职能协作契约

负责：

- `contracts.py`、GameProjectState、ArtifactRegistry。
- AgentTaskGraph、依赖传播和 Artifact stale 机制。
- 策划、美术、程序 Agent 的非执行型结构化输出。
- 第二阶段 CollaborationCoordinator、ProjectGate 和 ActionProposal。

### 3.3 红灯期间的硬隔离

- 已完成的轨道 B 代码保留，不回滚。
- 只允许继续数据契约、Registry、TaskGraph 和纯单元测试。
- 运行中的 Agent 不得读取真实或 Mock Snapshot。
- Mock Snapshot 只能作为测试 fixture，不得成为 Agent 输入。
- 不注册 LANChat 生产入口，不导入 AgentRuntime 写路径。
- 不创建 EntityBindingPlan、ActionProposal 或 ToolCallGraph。

---

## 4. 两层门禁

### 4.1 Runtime 门禁

新增只读接口：

```text
runtime.r3_readiness.evaluate
```

归属：`services/agent_runtime/`。

职责：

- 只读 RuntimeState、OperationLog、Registry、SceneWorldSnapshot 和 Engine Snapshot。
- 复用现有 Snapshot consistency audit、Fingerprint 和业务图事实。
- 输出 `R3GateReport`。
- 不校验 Artifact，不创建 StatePatch、PlanPatch、ToolGraph 或 OperationLog 事件。
- 同一版本、同一事实输入必须得到确定性相同结果。

最小返回结构：

```text
gate_report_id / room_id / plan_id / scene_version
overall: red | yellow | green
dimensions
metrics
blockers
capability_unlocks
evidence_refs
evaluated_at
```

七个判定维度：

```text
snapshot_integrity
environment_readiness
entity_readiness
finalizer_completeness
business_graph_consistency
multiplayer_consistency
runtime_write_safety
```

### 4.2 Project Gate

`ProjectGateService` 归属第二阶段的 `services/agent_collaboration/`。

它调用 `runtime.r3_readiness.evaluate` 作为一个底座检查项，并另外执行：

- Artifact schema 与真实 Validator。
- 规范化 payload 的 content hash。
- Artifact 版本、依赖和 stale 状态。
- entity_id 是否存在于目标 Snapshot。
- Snapshot 版本是否匹配且实体是否 Game-ready。
- 多人 sync 状态是否满足目标动作。

Runtime 门禁与 Project Gate 不合并；AgentRuntime 不理解策划、美术或程序 Artifact。

---

## 5. 红黄绿判定

### 5.1 Green

必须全部满足：

- 必要环境实体全部 Engine-ready，且具备对应场景语义。
- 终态 Snapshot 为 `immutable`，Runtime / Engine Fingerprint 一致。
- 儿童卧室至少 `8/14` Game-ready；其他场景 Game-ready 比例至少 60%。
- 业务 Batch 与 `business_batch` ToolGraph 数量、归属和终态一致。
- `tool_graph_queue_empty`、`scene_plan_finalized`、`scene_entity_registry_ready`、`runtime_scene_world_consistency_audited`、`scene_world_snapshot_ready`、`report_ready` 完整。
- `latest_completed_plan_id` 与最终 Snapshot plan/version 一致。
- 房主和成员的 `entity_id / asset_id / version` 一致。
- 只读查询前后 RuntimeState version、OperationLog cursor、ToolGraph 和 PlanPatch 数量不变。

### 5.2 Yellow

必须满足：

- 必要环境实体 ready。
- 儿童卧室为 `5-7/14` Game-ready；其他场景比例至少 35% 且低于 60%。
- 房主与成员的 `entity_id` 集合一致，没有身份漂移。
- 成员缺失的 AABB、sync 或其他事实明确进入 `readiness_missing_fields`。
- `asset_id / version` 可以缺失或 partial，但不得与房主事实冲突。
- RuntimeGuard、StatePatch 和只读查询边界没有失效。

### 5.3 Red

任一条件成立即为 Red：

- 必要环境缺失或未 ready。
- Snapshot 缺失、Fingerprint 不稳定或实体身份漂移。
- Game-ready 比例低于 35%。
- RuntimeGuard 被绕过、ToolResult 直接改状态或出现伪造 Engine success。
- 终态报告无法追溯到 RuntimeState、OperationLog 和 Engine 事实。

聚合优先级固定为：`red > yellow > green`。禁止人工用“问题已定位”替代可观测证据。

---

## 6. 能力解锁矩阵

| 能力 | Red | Yellow | Green |
|---|---:|---:|---:|
| 强类型 Artifact / ProjectState / Registry | 允许 | 允许 | 允许 |
| 策划、美术非执行型 Artifact | 允许 | 允许 | 允许 |
| GameplayLogicPlan | 允许 | 允许 | 允许 |
| 读取真实 Snapshot 做只读分析 | 禁止 | 允许 | 允许 |
| EntityBindingPlan | 禁止 | 禁止 | 允许 |
| CollaborationCoordinator 接真实 Snapshot | 禁止 | 禁止 | 允许 |
| ProjectGate / ActionProposal | 禁止 | 禁止 | 允许 |
| Runtime 场景写入 | 仅修复底座 | 禁止上层 Agent 写入 | 通过现有 Runtime 执行 |

Green 通过后冻结 `SceneWorldSnapshot v1`。冻结对象包含 schema、Validator、一个通过 F5 的规范 fixture 和对应 Fingerprint，不只是保存一份聊天报告。

---

## 7. 三职能第一阶段契约

第一阶段目录：

```text
services/agent_collaboration/
  contracts.py
  project_state.py
  artifact_registry.py
  task_graph.py
  agents/
    planning_agent.py
    art_agent.py
    program_agent.py
```

首批 Artifact：

```text
GameDesignBrief
LevelPlan
ArtDirection
SceneCompositionPlan
GameplayLogicPlan
EntityBindingPlan（仅 Green 解锁）
```

`ArtifactEnvelope` 至少包含：

```text
artifact_id / artifact_type / version
producer_role / source_task_id
base_project_version / base_world_version
dependencies / content_hash
snapshot_source / status / validation_result / payload
```

`contracts.py` 必须提供硬检查：

```python
class NonExecutableArtifactError(RuntimeError):
    pass

def assert_executable(artifact: ArtifactEnvelope) -> None:
    if artifact.snapshot_source == "mock":
        raise NonExecutableArtifactError(artifact.artifact_id)
```

第二阶段的 ActionProposal 构造函数必须调用 `assert_executable()`；禁止把检查散落在调用方。

---

## 8. 执行模型：工作块、状态与依赖

后续实施不再以“今天大致做什么”作为唯一导航，而以工作块和任务编号为准。

### 8.1 工作块总览

```text
W0 基线冻结与 R3 门禁底座
├─ W1 轨道 A：Game-ready Runtime 事实收口
│  └─ W2 轨道 A：单机/多人 F5 与 Gate 决策
└─ W3 轨道 B：三职能强类型契约底座
   └─ W4 轨道 B：三职能非执行型协作闭环

W2 = Green 且 W4 完成
-> W5 真实 Snapshot、Coordinator、ProjectGate 与 ActionProposal
-> W6 R3 验收、下游 Agent 承接与版本冻结
```

允许并行：

- `W1` 与 `W3` 可并行。
- 等待人工 F5 时，可继续执行当前 Gate 允许的 `W3/W4` 任务。
- `W4` 只能在 `W3` 的相应依赖完成后推进。

禁止抢跑：

- `W5` 必须同时满足 `W2=Green` 和 `W4` 完成。
- Red 状态下，运行中的职能 Agent 不得读取真实或 Mock Snapshot。
- Yellow 状态下不得创建 EntityBindingPlan 或 ActionProposal。
- 一个任务“代码完成”不等于“F5 已验证”。

### 8.2 任务状态

每个任务只使用以下状态：

```text
pending          尚不满足前置依赖
ready            依赖满足，可开始
in_progress      当前唯一主任务
code_complete    代码和自动测试完成，但仍可能待 F5
verified         所需自动测试/F5 均有证据
blocked          有明确阻断条件，不能继续
deferred         明确移出当前 R3 范围
```

状态更新必须附证据。不得因为文件已创建、测试用例已增加或日志出现预期字符串，就把任务标记为 `verified`。

### 8.3 单任务执行卡

后续 AI 执行任一任务时，必须按以下字段理解任务：

```text
任务编号 / 目标
前置依赖 / Gate 要求
事实输入
实施边界
交付物
完成标准
验证证据
明确不做
```

下面各工作块已经给出这些字段。若代码事实与本文不一致，应先在 `R3-min推进记录.md` 记录偏差，再按当前代码事实修订任务，不得默默改变架构边界。

---

## 9. W0：基线冻结与 R3 门禁底座

### 9.1 工作块目标

建立可重复判断 Red/Yellow/Green 的只读事实聚合器，并给所有后续任务提供稳定基线。W0 不修场景效果，也不接入职能 Agent。

### 9.2 准入与退出

准入：当前 AgentRuntime 主链可被定位，工作区和用户改动已识别。

退出条件：

- 能生成结构化 `R3GateReport`。
- 同一事实输入重复评估结果一致。
- 评估前后 RuntimeState、OperationLog cursor、PlanPatch 和 ToolGraph 数量不变。
- 当前 Gate 和失败维度写入推进记录。

### 9.3 任务分区

#### W0.1 基线与改动隔离

- 前置依赖：无。
- 事实输入：当前分支、远端差异、工作区、子模块状态、最近一次有效 F5 日志。
- 实施：识别功能改动、本地配置、用户未提交文件和子模块差异；建立可回退基线。
- 交付物：基线提交或明确的未提交改动清单；`R3-min推进记录.md` 中的起点记录。
- 完成标准：后续修改不会覆盖 `ai_setting.py`、Quasar 或用户文件；可指出本轮变更的精确文件集合。
- 验证：`git status`、分支/远端差异、必要的 syntax 检查。
- 不做：顺手清理旧代码、重排用户提交、修改本地密钥配置。

#### W0.2 R3GateReport 契约

- 前置依赖：W0.1。
- 事实输入：RuntimeState、OperationLog、Registry、Snapshot、Engine Snapshot 的现有 DTO。
- 实施：定义 GateReport schema、七个判定维度、失败原因和证据引用。
- 交付物：稳定的 `R3GateReport` 数据结构及 Validator。
- 完成标准：报告至少包含环境、身份、readiness、批次/图、Finalizer、Snapshot、多人一致性七个维度。
- 验证：schema/序列化单元测试。
- 不做：Artifact 校验、Runtime 写入、自动修复。

#### W0.3 只读 Gate evaluator

- 前置依赖：W0.2。
- 事实输入：指定 room/plan/version 的结构化事实。
- 实施：实现 `runtime.r3_readiness.evaluate`，聚合事实并给出 Gate。
- 交付物：只读 evaluator、明确的 missing/contradiction 列表。
- 完成标准：`5/14` 可判 Yellow，`8/14` 且其他硬条件满足可判 Green；环境缺失、Fingerprint 不稳或 entity_id 漂移判 Red。
- 验证：边界值、确定性、零副作用测试。
- 不做：写 OperationLog、生成 ToolGraph、触发 Engine 查询以外的副作用。

#### W0.4 初始 Gate 锚点

- 前置依赖：W0.3。
- 事实输入：最新可信运行事实；若仅有旧 F5，必须标注证据版本。
- 实施：生成首份 GateReport，列出每个失败维度对应责任域。
- 交付物：推进记录中的当前 Gate、证据时间、下一批可执行任务 ID。
- 完成标准：AI 能从报告中确定是进入 W1、W3，还是等待 F5，而不靠聊天记忆判断。
- 验证：人工核对报告与日志/Runtime 事实一致。
- 不做：使用尚未 F5 的代码结果冒充实机结论。

---

## 10. W1：轨道 A，Game-ready Runtime 事实收口

### 10.1 工作块目标

让 Engine、RuntimeState、OperationLog、Registry、Snapshot 和报告描述同一个场景实体世界。W1 只修 GateReport 暴露的事实断点。

### 10.2 准入与退出

准入：W0.3 完成，能够按实体和维度定位失败。

退出条件：

- 必要环境实体具有真实 Engine 事实。
- 普通 Actor 的稳定身份、真实 transform/AABB 和支撑状态可解释。
- Finalizer 终态顺序完整。
- 业务 Batch 与业务 ToolGraph 能对账。
- 状态查询严格只读。
- 多人身份差异可被机器检测。

### 10.3 环境事实分区

#### W1.1 必要环境实体闭环

- 前置依赖：W0.3。
- 事实输入：ScenePlan 场景类型、required environment、Engine Snapshot、Registry。
- 实施：统一室内 `room_box/room_floor`、室外 terrain/ground、混合 transition zone 的 required/ready 判定。
- 交付物：环境实体的稳定 entity_id、actor_id、semantic_role、Engine readiness 和 AABB 来源。
- 完成标准：缺少必要环境必判 Red；存在时不再用计划清单或虚拟 AABB冒充 Engine ready。
- 验证：室内/室外/混合聚焦测试，真实表现待 W2 F5。
- 不做：重写 Environment 生成主链、为某个场景名称写特例。

### 10.4 实体身份与几何分区

#### W1.2 稳定身份和真实几何事实

- 前置依赖：W1.1 可并行推进，但最终共同验收。
- 事实输入：ToolResult、StatePatch、C++ Actor snapshot、asset manifest。
- 实施：对齐 entity_id、actor_id、asset_id/model_ref、transform、world AABB、bounds_source、version 和 batch_id。
- 交付物：可由五方对账的 SceneEntity。
- 完成标准：`estimated` 与 `engine_actual` 明确区分；显示名称或路径不能替代稳定 ID。
- 验证：identity/reconcile 单元测试与 snapshot fixture。
- 不做：用默认值补齐未知 interaction/gameplay 能力。

#### W1.3 Grounding 与 support 语义

- 前置依赖：W1.2。
- 事实输入：真实 AABB、transform、semantic role、环境支撑面。
- 实施：统一 `grounded/wall_mounted/suspended/enclosure/not_applicable/needs_review`。
- 交付物：每个实体的 grounding_status 和缺失原因。
- 完成标准：普通地面物体没有支撑事实时不能计入 Game-ready；墙挂/悬挂物不被强制落地。
- 验证：地面、墙挂、悬挂、系统环境对象的聚焦测试；视觉效果待 W2 F5。
- 不做：依赖 VLM 代替几何事实，不做全局物理系统重构。

### 10.5 终态与统计分区

#### W1.4 Finalizer 终态顺序

- 前置依赖：W1.1-W1.3 的事实接口稳定。
- 事实输入：BatchPlan terminal、业务 graph queue、Engine readiness、StatePatch、OperationLog。
- 实施：固定 `registry_ready -> consistency_audit -> snapshot_ready -> report_ready` 的真实终态流程。
- 交付物：可复盘的 Finalizer 事件和 partial/failed 原因。
- 完成标准：任何 required entity 未 terminal 时只能 `report_pending`；报告落盘前不得清除 active execution plan。
- 验证：事件顺序、late-ready、partial 和重复 Finalizer 测试。
- 不做：通过 UI 文案模拟终态。

#### W1.5 业务批次/ToolGraph 对账与只读查询

- 前置依赖：W0.3；可与 W1.4 并行。
- 事实输入：BatchPlan、graph_role、OperationLog、query graph。
- 实施：区分 business_batch、internal_state、query_snapshot、review、finalizer；状态查询不污染业务统计。
- 交付物：`batches_total/terminal`、`business_graphs_total/terminal`、nodes succeeded/failed 的一致摘要。
- 完成标准：不再出现“业务批次少量、ToolGraph 数百个”或 query 导致业务计数增加。
- 验证：图分域、零写入查询、完成后持久化 node_count 测试。
- 不做：删除内部图或牺牲审计能力来让数字好看。

### 10.6 多人事实分区

#### W1.6 权威身份与 Peer Mirror 对账

- 前置依赖：W1.2、W1.5。
- 事实输入：房主/成员 Snapshot、sync operation、entity/version/asset identity。
- 实施：建立 entity_id/version 去重和可观测差异报告。
- 交付物：host/peer identity diff、partial sync missing fields。
- 完成标准：同一实体不会因广播重放产生第二身份；身份漂移判 Red，AABB/sync 缺失但身份一致可判 Yellow。
- 验证：同步聚焦测试，最终结果待 W2.5 多人 F5。
- 不做：重写底层 LAN 传输协议或增加新资源分发系统。

---

## 11. W2：轨道 A，F5 Vertical Slice 与 Gate 决策

### 11.1 工作块目标

用固定场景验证真实 Engine 结果，而不是继续从自动测试推断实机表现。每次 F5 只修对应 Gate 失败维度。

### 11.2 F5 公共证据包

每轮 F5 必须保存：

```text
运行日志路径与代码 commit
room_id / plan_id / scene_version
Engine Actor 摘要
RuntimeState 与 OperationLog cursor
scene_entity_registry
SceneWorldSnapshot fingerprint
final report
R3GateReport
多人测试时的 host/peer diff
```

缺少以上关键事实时，该轮只能算“运行观察”，不能把任务标为 `verified`。

### 11.3 单机场景分区

#### W2.1 儿童卧室 F5

- 前置依赖：W1.1-W1.5 `code_complete`。
- 场景：room_box、room_floor 与约 14 个家具/装饰实体，包含一次只读查询。
- 核验：环境 ready、身份/AABB/grounding、业务批次对账、Finalizer、查询零写入。
- 通过：至少 `5/14` Game-ready 才离开绝对 Red；达到 `8/14` 且硬条件满足可作为 Green 数量门槛。
- 输出：卧室 GateReport 与具体 needs_review entity_id。

#### W2.2 森林营地 F5

- 前置依赖：W2.1 暴露的共性 P0 断点已处理。
- 场景：terrain/ground/sky/forest substrate 与帐篷、小木桌等普通 Actor。
- 核验：环境与普通模型正确分流；不生成 room_box；terrain ready 后才导入/摆放 Actor。
- 通过：必要环境 ready，Game-ready 比例达到 60% 才满足 Green 场景门槛。
- 输出：室外 GateReport 和 substrate routing 证据。

#### W2.3 室内外混合 F5

- 前置依赖：W2.1、W2.2 的环境身份问题已收口。
- 场景：terrain、room shell、floor、transition zone 与普通 Actor。
- 核验：四类环境身份不冲突、不重复导入，Registry/Snapshot 可分别查询。
- 通过：必要环境全部 ready，Game-ready 比例达到 60%，Fingerprint 稳定。
- 输出：混合场景 GateReport。

### 11.4 增量与多人分区

#### W2.4 生成中/生成后追加与只读查询 F5

- 前置依赖：W2.1 至少 Yellow，PlanPatch 主链聚焦测试通过。
- 场景：在原计划中追加一个明确低风险对象，并查询其状态。
- 核验：同一 execution/latest-completed plan、一个 PlanPatch、一个业务 Batch、一个 Actor、scene version +1；查询零写入。
- 通过：不重复环境、不创建新 ScenePlan、不产生重复 Actor，追加后重新 Finalize。
- 输出：追加前后 Snapshot diff 和 OperationLog 证据。

#### W2.5 多人 F5

- 前置依赖：W1.6 `code_complete`，W2.1-W2.4 无 Red 身份问题。
- 场景：房主确认生成、成员观察、一次追加、一次查询。
- 核验：权威端只执行一次；房主/成员 entity_id、asset_id、version 一致；partial 字段明确。
- 通过：无 entity_id 漂移和重复 Actor；必要环境身份一致。
- 输出：host/peer Snapshot diff、多人 GateReport。

### 11.5 Gate 汇总分区

#### W2.6 Gate 汇总与 Snapshot v1 冻结决策

- 前置依赖：W2.1-W2.5 都有证据包。
- 实施：聚合三类场景、追加和多人结果，不用“平均表现”掩盖硬阻断。
- Red：返回具体 W1 任务，不启动 W5。
- Yellow：允许真实 Snapshot 只读分析；继续修 W1/W2。
- Green：冻结版本化、不可变的 `SceneWorldSnapshot v1` 契约和 baseline fingerprint。
- 交付物：门禁决策、未解决列表、W5 解锁记录。
- 完成标准：决策可由同一证据重复计算，且与能力解锁矩阵一致。

---

## 12. W3：轨道 B，三职能强类型契约底座

### 12.1 工作块目标

在不依赖 Runtime/F5 的前提下建立协作数据骨架。W3 在 Red 状态可推进，但不得导入 AgentRuntime 内部实现，也不得为运行中的 Agent提供 Mock Snapshot。

### 12.2 契约分区

#### W3.1 Artifact 与 Project 契约

- 前置依赖：W0.1。
- 实施：建立 `contracts.py`，定义 GameProjectState、ArtifactEnvelope、AgentTask 和六种首批 Artifact schema。
- 交付物：强类型 DTO、schema version、规范化序列化。
- 完成标准：必填字段、producer_role、base_project/world version、dependencies 都可校验。
- 验证：构造、序列化、非法 payload 测试。
- 不做：Agent prompt、Runtime adapter、ActionProposal。

#### W3.2 Content Hash 与真实 Validator

- 前置依赖：W3.1。
- 实施：由规范化 payload 计算 content_hash；validation_result 必须来自 Validator。
- 交付物：确定性 hash 和每种 Artifact 的最小 Validator。
- 完成标准：同内容同 hash；内容变化导致 hash 变化；默认“通过”不可构造。
- 验证：hash 稳定性、schema 错误、伪造 validation_result 测试。

### 12.3 状态与注册分区

#### W3.3 GameProjectState

- 前置依赖：W3.1。
- 实施：维护 project_version、active task graph、scene plan/world version 和 Artifact refs。
- 交付物：独立于 RuntimeState 的项目级状态存储接口。
- 完成标准：项目目标事实与场景执行事实不混写；版本更新有明确来源。
- 验证：状态迁移和并发版本冲突测试。

#### W3.4 ArtifactRegistry 与失效传播

- 前置依赖：W3.2、W3.3。
- 实施：注册、查询、版本化 Artifact；上游变化把依赖旧版本的下游标记 stale。
- 交付物：ArtifactRegistry、依赖索引、stale reason。
- 完成标准：旧版本可审计但不能冒充当前有效版本。
- 验证：至少一项跨模块 stale propagation 测试。

### 12.4 任务编排与隔离分区

#### W3.5 AgentTaskGraph

- 前置依赖：W3.1、W3.4。
- 实施：建立跨 Agent 的 depends_on、acceptance criteria、retry、blocked 和 output refs。
- 交付物：可执行“策划 -> 美术/程序 -> 综合验收”的业务任务图。
- 完成标准：未满足依赖的任务不能 ready；失败只重试责任任务，不重跑整图。
- 验证：依赖顺序、失败/重试、stale input 阻断测试。
- 不做：复用 ToolCallGraph 承载业务协作。

#### W3.6 Mock/非执行硬隔离

- 前置依赖：W3.1。
- 实施：定义 `NonExecutableArtifactError` 和 `assert_executable()`；fixture 标记 source=mock/non_executable。
- 交付物：任何 Mock Artifact 在 ActionProposal 构造边界必然失败的硬约束。
- 完成标准：不能通过调用方漏检绕过；Red 状态运行中 Agent 不消费 Mock Snapshot。
- 验证：直接构造、间接构造和伪造 source 测试。

---

## 13. W4：轨道 B，三职能非执行型协作闭环

### 13.1 工作块目标

证明策划、美术、程序 Agent 能围绕强类型 Artifact 协作，但不连接真实场景写入。Red 状态下三类 Agent 只能消费 ProjectState 和 Artifact；Yellow 才允许只读真实 Snapshot。

### 13.2 策划分区

#### W4.1 PlanningAgent

- 前置依赖：W3.1-W3.5。
- 输入：用户项目目标、已有有效 Artifact，不读取 Engine 或聊天流水账。
- 输出：GameDesignBrief、LevelPlan。
- 完成标准：目标、规则、关卡结构、验收条件可被后续 Artifact 明确引用。
- 验证：schema、依赖、版本更新导致下游 stale。
- 不做：资产生成、Engine 写入、实体绑定。

### 13.3 美术分区

#### W4.2 ArtAgent

- 前置依赖：W4.1 的有效 GameDesignBrief/LevelPlan。
- 输入：已验证策划 Artifact；Yellow 可额外只读 Snapshot。
- 输出：ArtDirection、SceneCompositionPlan。
- 完成标准：场景类型、风格、环境、实体需求和构图约束为结构化字段，不用一段 prompt 代替契约。
- 验证：策划版本变化导致美术 Artifact stale；缺少依赖时拒绝生成。
- 不做：ActionProposal、Provider、SceneTools。

### 13.4 程序分区

#### W4.3 ProgramAgent 非执行输出

- 前置依赖：有效 GameDesignBrief/LevelPlan；可引用 ArtDirection。
- 输入：已验证 Artifact；Red 不读 Snapshot，Yellow 只做世界分析。
- 输出：GameplayLogicPlan。
- 完成标准：触发、状态、规则和胜负/任务逻辑使用稳定 schema；不包含可执行脚本。
- 验证：schema、依赖版本和禁止能力测试。
- 不做：EntityBindingPlan、ScriptBundle、shell、Actor 修改。

### 13.5 协作闭环分区

#### W4.4 Artifact 综合闭环

- 前置依赖：W4.1-W4.3。
- 实施：用 AgentTaskGraph 驱动 Red 阶段五种可产出 Artifact 的生产、校验、返工和 stale 传播；`EntityBindingPlan` 仅保留已定义 schema，待 Green 后由 W5.2 生产。
- 交付物：一个不依赖 Runtime 写入的完整项目方案版本。
- 完成标准：每个 Artifact 都有 producer/task/dependencies/hash/validation，任何上游变更可精确定位需返工任务。
- 验证：端到端纯契约测试，不运行 F5。

#### W4.5 旧 Persona 兼容隔离

- 前置依赖：W4.4，且新职能入口具备最小可用结构化输出。
- 实施：旧长者/小女孩/山贼/商人保留兼容但不作为三职能生产入口；新入口明确策划/美术/程序职责。
- 交付物：入口路由和兼容说明。
- 完成标准：旧 Persona 不会绕过 Collaboration 层生成生产 Artifact 或写 Runtime。
- 验证：路由/权限聚焦测试。
- 不做：删除历史角色代码或大改聊天室 UI。

---

## 14. W5：Green 后真实协作与写入闭环

### 14.1 工作块目标

在可信 Snapshot v1 上，把三职能 Artifact 连接到现有 AgentRuntime。W5 是 Green-only 工作块，任何任务都不能通过 Mock 或 Yellow 豁免。

### 14.2 Snapshot 接入分区

#### W5.1 Snapshot v1 只读适配器

- 前置依赖：W2.6 Green、W3.1-W3.4、W4.4。
- 实施：按 plan_id + scene_version 读取冻结 Snapshot，不暴露 Engine/Runtime 内部对象。
- 交付物：协作层只读 world view 和 fingerprint 校验。
- 完成标准：读取零副作用；版本变化必须显式重新获取。
- 验证：版本选择、过期、fingerprint、零写入测试。

#### W5.2 EntityBindingPlan

- 前置依赖：W5.1、W4.3、W4.4。
- 实施：程序 Agent 只绑定目标 Snapshot 中存在且 Game-ready 的 entity_id。
- 交付物：EntityBindingPlan 与引用验证结果。
- 完成标准：名称、模型路径或聊天文本不能替代 entity_id；Snapshot 更新后旧绑定变 stale。
- 验证：不存在、非 Game-ready、过期和有效绑定测试。

### 14.3 协调与门禁分区

#### W5.3 CollaborationCoordinator

- 前置依赖：W4.4、W5.1。
- 实施：管理三职能任务分解、依赖、返工、房主确认和版本推进。
- 交付物：单一 active project/task graph 协作状态。
- 完成标准：Coordinator 不执行 Engine 工具，不复制 RuntimeState；失败回到责任 AgentTask。
- 验证：三 Agent 顺序、并行依赖、返工和确认测试。

#### W5.4 ProjectGateService

- 前置依赖：W5.2、W5.3。
- 实施：真实校验 Artifact schema/hash/version/dependency、entity_id、Snapshot 版本和 Runtime Gate。
- 交付物：可审计 ProjectGateResult。
- 完成标准：Runtime Gate 只是其中一个检查项；ProjectGate 不替代 RuntimeGuard。
- 验证：每种失败原因及成功路径测试。

### 14.4 写入与版本回流分区

#### W5.5 ActionProposal 到 AgentRuntime

- 前置依赖：W5.4 通过，房主确认，Artifact `assert_executable()` 通过。
- 实施：把批准动作转换为现有 PlanPatch -> business ToolCallGraph -> RuntimeGuard -> EngineWriteGate。
- 交付物：第一条美术低风险 ActionProposal 写入闭环。
- 完成标准：Agent 不直接写 Engine/RuntimeState；失败返回结构化 ToolResult/StatePatch 结果。
- 验证：聚焦集成测试和对应 F5；未 F5 标 `[待 F5/实机验证]`。
- 不做：删除、覆盖环境、脚本执行或高风险自动操作。

#### W5.6 世界版本回流与 Artifact 失效

- 前置依赖：W5.5。
- 实施：写入完成后生成 Snapshot vN+1，触发 EntityBindingPlan 和相关 Artifact 重验。
- 交付物：旧/新 Snapshot diff、stale propagation 和更新后的 ProjectState。
- 完成标准：不能用 vN 的绑定静默操作 vN+1；追加/调整形成可复盘版本链。
- 验证：成功、partial、失败写入后的版本与失效测试。

---

## 15. W6：R3 验收与下游 Agent 承接

### 15.1 工作块目标

证明底座已经能被后续策划、美术、程序 Agent 和 AI Game Demo 安全消费，而不是只完成若干孤立模块。

### 15.2 单机验收分区

#### W6.1 三职能最小业务闭环

- 前置依赖：W5.1-W5.6。
- 场景：策划产出目标，美术形成场景调整，程序形成逻辑与实体绑定，房主确认一次低风险写入。
- 通过：Artifact、TaskGraph、ProjectGate、Runtime、Snapshot 版本链完整；失败可定位责任域。
- 输出：单机验收包和 R3GateReport。

### 15.3 多人验收分区

#### W6.2 多人权威协作闭环

- 前置依赖：W6.1、W2.5 verified。
- 场景：多人讨论、三职能协作、房主确认、成员同步观察。
- 通过：只由权威端创建 ActionProposal/PlanPatch；各端 Snapshot identity/version 一致，无重复 Actor。
- 输出：host/peer diff 和多人验收包。

### 15.4 下游承接分区

#### W6.3 下游 Agent 只读契约验证

- 前置依赖：W6.1。
- 实施：用一个最小只读消费者读取 ProjectState、有效 Artifact 和 SceneWorldSnapshot，输出结构化建议。
- 通过：消费者不读 Engine/聊天历史、不写 Runtime；能识别 stale、needs_review 和版本变化。
- 说明：这是承接证明，不实现战斗/剧情/脚本 Agent。

#### W6.4 R3 版本冻结与完成矩阵

- 前置依赖：W6.1-W6.3；多人能力要求 W6.2。
- 实施：冻结 schema/version、记录已验证平台和 `[待 F5/实机验证]` 项，形成可回退 baseline。
- 交付物：R3 完成矩阵、接口清单、下一阶段 Agent 接入指南。
- 完成标准：每个“完成”声明都能追溯到自动测试或 F5 证据，没有计划字段冒充 Engine 事实。

---

## 16. 七天时间盒映射

任务依赖和 Gate 优先于日期。以下是目标节奏，不是越过门禁的许可：

| 时间 | 轨道 A | 轨道 B | 当日必须留下的证据 |
|---|---|---|---|
| 第 1 天 | W0.1-W0.4 | W3.1-W3.2 | 初始 GateReport、契约测试 |
| 第 2 天 | W1.1-W1.3 | W3.3-W3.4 | 环境/身份聚焦测试、stale 测试 |
| 第 3 天 | W1.4-W1.5 | W3.5-W3.6 | Finalizer/图对账证据、任务图测试 |
| 第 4 天 | W2.1-W2.3 | W4.1 | 三类场景 F5 证据包、策划 Artifact |
| 第 5 天 | W1.6、W2.4-W2.6 | W4.2-W4.4 | 多人/追加证据、Gate 决策、五 Artifact 红灯闭环 |
| 第 6 天 | Red/Yellow：继续 W1/W2；Green：W5.1-W5.4 | W4.5 或 W5 协作接入 | Snapshot v1 或明确阻断项 |
| 第 7 天 | Green：W5.5-W5.6、W6.1 | 协作验收 | 首个真实写入版本链与验收包 |

若第 5 天仍为 Red：

- W3/W4 已完成代码全部保留，不回滚。
- 不启动 W5。
- 下一轮只选择 GateReport 中最高优先级的 W1/W2 断点。

若为 Yellow：

- 允许 W4 Agent 只读真实 Snapshot 做分析。
- 不生成 EntityBindingPlan，不构造 ActionProposal。
- 继续提升 Game-ready 和多人事实一致性。

---

## 17. 分块验证矩阵

| 工作块 | 最小验证 | 何时需要总门禁 | 何时需要 F5 |
|---|---|---|---|
| W0 | schema、确定性、零副作用 | W0 收口时一次 | 不需要 |
| W1 | 对应 Runtime 聚焦测试 | 触及 RuntimeState/Finalizer/Guard 时 | 由 W2 统一验证 |
| W2 | 证据包 + GateReport | 每轮 F5 前必要时一次 | 必须 |
| W3 | 模块单测 + stale 跨模块测试 | W3 收口时可选 | 不需要 |
| W4 | Artifact 端到端纯契约测试 | W4 收口时一次 | 不需要 |
| W5 | ProjectGate/Runtime 集成测试 | 真实写入前一次 | W5.5/W5.6 必须 |
| W6 | 完整验收矩阵 | R3 提交前一次 | 单人/多人必须 |

必须持续覆盖：

- Gate evaluator 完全只读且确定性。
- `5/14 -> Yellow`；`8/14 + 硬条件完整 -> Green`。
- 环境缺失、Fingerprint 不一致、entity_id 漂移 -> Red。
- Partial 同步且身份一致、缺失字段明确 -> Yellow。
- Mock Artifact 不能进入 ActionProposal。
- 业务 Batch 与业务 ToolGraph 对账。
- Snapshot/实体状态查询零场景写入。

每次 F5 只根据 GateReport 的失败维度修复，不扩展无关 VLM、UI、Provider、Replay 或旧 Workflow 清理。

---

## 18. AI 续跑协议

后续 AI 开始工作时必须：

1. 读取最新 `R3GateReport` 和 `R3-min推进记录.md`。
2. 确认当前工作块、最后一个 verified/code_complete 任务及阻断项。
3. 按依赖图选择最早的 `ready` 任务；Red 的 Runtime 硬阻断优先于轨道 B 增量。
4. 若 F5 只能由用户执行，则把相关任务标 `code_complete`，转向一个允许并行的 W3/W4 任务，不得写成 `verified`。
5. 默认一轮只推进一个任务编号；只有不可分割的前置小修可并入同一轮。
6. 结束时记录任务状态、证据、Gate 变化和下一批可选任务 ID。

确定性选题顺序：

```text
存在 Red 架构硬阻断
-> 选择对应 W1/W2 任务

等待人工 F5，且无可继续的 Runtime 代码工作
-> 选择最早 ready 的 W3/W4 任务

Yellow
-> 优先补 W1/W2 缺失事实；允许 W4 只读分析

Green 且 W4 完成
-> 按 W5.1 -> W5.6 顺序推进

W5 完成
-> W6 验收与冻结
```

禁止根据“看起来差不多”跳到 W5，也禁止为了保持忙碌而新增计划外 Agent、测试矩阵或 UI 功能。

---

## 19. 当前不做

- 战斗、剧情、数值、任务、脚本和蓝图执行 Agent。
- ScriptBundle、EngineScriptAdapter 和任意脚本沙箱执行。
- 完整 AI Game Demo。
- 为单一测试场景写死特殊逻辑。
- 把旧 Workflow 包装成 AgentRuntime 大工具。
- 为微小改动运行全量门禁或向本计划追加冗长 Progress Update。
