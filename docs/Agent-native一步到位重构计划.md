# Agent-native 一步到位重构计划：旧 Workflow 主控退场与能力工具化

更新时间：2026-06-29

## 1. 问题本质判断

本项目当前要解决的不是“再补一个更聪明的 Agent”，也不是继续在旧 workflow 上追加更多 if/else，而是要把系统主控权从 workflow 调用栈中释放出来，升级为 Agent-native Runtime 架构。

当前真实链路大致是：

```text
LANChat / 单人输入
-> LANChatAgentWorker / Orchestrator
-> InteractionCoordinator / SeedPlan
-> GenerationScheduler
-> SceneComposer.compose()
-> model_retrieval workflow
-> run_progressive_workflow()
-> SceneSession.progressive_compose()
-> incremental_import / AABB / VLM / final report
-> actor / asset / network sync
```

这个链路已经能跑通一定的生成、导入、审查和多人同步，但它的核心短板是：

```text
控制权仍在旧 workflow 内部
批次状态仍藏在函数调用栈里
用户介入只能被延迟吸收
完成态调整依赖局部补丁
同步状态不是 Runtime 一等状态
最终报告仍可能来自 workflow 内部拼接
```

本次重构目标：

```text
User / LANChat
-> AgentRuntime
-> GM / Planner / Builder / Reviewer Agents
-> ScenePlan / BatchPlan
-> ToolCallGraph
-> RuntimeGuard
-> ToolRegistry
-> Atomic / Mid-grain Tools
-> RuntimeState / OperationLog
-> Engine / Asset / Network
```

核心原则：

```text
AgentRuntime 是唯一主控
ScenePlan / BatchPlan 是计划事实源
ToolCallGraph 是执行事实源
RuntimeState 是状态事实源
OperationLog 是复盘事实源
旧 Workflow 不再主控，只能被拆解为函数级工具能力
```

这不是把旧 workflow 包成 `legacy.scene_compose` 继续跑，也不是让 LLM Agent 自由调用底层函数，而是：

```text
Agent 负责决策
ToolCallGraph 负责编排
RuntimeGuard 负责权限和风险
ToolRegistry 负责执行能力
RuntimeState 负责状态合并
OperationLog 负责可回放
```

本次重构的根本目的，是让后续真正支持实时介入和更自由的人机交互边界。旧 workflow 的状态大量藏在函数调用栈里，用户介入只能延迟吸收；Agent-native Runtime 要把计划、批次、工具调用、资源、actor、审查、同步状态都显式化，让用户介入可以变成可取消、可插队、可替换、可确认的 `ToolCall / PlanPatch / ReviewRequest`。

## 2. 当前核实状态

### 2.1 工程状态

本次审理时的仓库状态：

```text
分支：main
HEAD：c3c808fd Merge pull request #70 from CoronaEngine/add_csm
远端状态：main 落后 origin/main 6 个提交
特殊状态：editor/plugins/AITool/Quasar 仍显示为 ?，需要单独确认子模块或嵌套仓库状态
文档变更：新增本计划文档；已删除旧空文档和被替代的旧后续计划草稿
```

执行本计划前必须先完成：

```text
同步远端 main
确认 Quasar 状态
确认 docs 当前待提交变更
记录现有测试 baseline
```

### 2.2 CodeGraph 绝对优先铁律

本计划继承 `终极计划.md` 中的 CodeGraph 规则。后续凡涉及代码理解、代码定位、代码查看、代码读取、代码写入、影响面判断、调用链判断、测试覆盖判断，必须绝对优先使用 CodeGraph。

执行优先级固定为：

```text
MCP CodeGraph
-> CLI codegraph.cmd
-> 普通文件工具
```

代码修改前必须通过 CodeGraph 明确：

```text
目标符号
调用方
被调用方
blast radius
相关测试
单人链路影响
多人链路影响
```

禁止在未使用 CodeGraph 了解影响面的情况下直接改：

```text
LANChatAgentWorker
InteractionCoordinator
SeedPlan
GenerationScheduler
SceneComposer
run_progressive_workflow
SceneSession
IncrementalImport
VLM review
Actor sync
```

### 2.3 当前代码证据

本次通过 CodeGraph 核实到的关键事实：

#### 2.3.1 `SceneComposer.compose()` 仍是完整生成主控

当前 `SceneComposer.compose()` 仍然串联：

```text
生成文本增强 / memory context
extract_items
element classification summary
zone_tree 分解
room budget
model_retrieval workflow
review queue
run_progressive_workflow 或 _run_original_workflow
final report 字段回填
```

这说明 `SceneComposer` 当前不是单纯工具，而是旧 workflow 的主控节点之一。Agent-native 重构必须把它拆成工具能力，而不是继续让它控制完整流程。

#### 2.3.2 `run_progressive_workflow()` 仍是批次与导入主控

当前 `run_progressive_workflow()` 仍然负责：

```text
生成场景框架
初始化 SceneSession / SceneDiffTracker / EngineWriteGate
按 phase 构建 micro-batch
处理 pending runtime notes
resolve pending resource requests
调用 incremental_import
执行 AABB / room bounds repair
执行 VLM checkpoint
合并 final report / vlm report
返回 operation_log / progress_events / pending_tasks
```

这说明 progressive workflow 已经具备一些目标能力，但状态仍没有上升为统一 RuntimeState。后续不能把 `run_progressive_workflow()` 包成大工具继续主控，必须拆成 `batch / import / review / report` 工具。

#### 2.3.3 `GenerationScheduler` 已有队列能力，但仍是旧业务状态源

当前 `GenerationScheduler` 已有：

```text
QUEUED / PREPARING / COMPOSING / IMPORTING / DONE / FAILED / PAUSED
queue_limit
priority
submit / status / snapshot
event log
async worker
```

这些是可复用能力，但不能继续作为业务主控状态源。目标形态中它应降级为 `ToolCallGraphExecutor` 的执行队列能力，业务状态进入 RuntimeState。

#### 2.3.4 `SeedPlan` 已有计划雏形，但需要升级为 ScenePlan

当前 `SeedPlanStatus` 包含：

```text
draft / clarifying / proposed / confirmed / executing / paused / completed / cancelled
```

当前 SeedPlan 已承担多人确认与计划承接的一部分职责，但 Agent-native 后应升级为 `ScenePlan`：

```text
ScenePlan 是计划事实源
SeedPlan 可作为迁移映射对象
不再作为新架构最终状态对象
```

#### 2.3.5 `SceneSession.OperationLogEntry` 已存在，但作用域不够

当前 `OperationLogEntry` 在 `scene_session.py` 内部，用于记录用户/Agent/系统操作账本条目。它是有价值的雏形，但仍局限于 progressive session。

目标形态中 OperationLog 必须上升为 Runtime 级账本，覆盖：

```text
Agent 决策
ToolCall 创建
Guard 判断
工具执行
StatePatch 合并
VLM 建议
同步广播
失败回退
最终报告
```

#### 2.3.6 VLM 已有 checkpoint policy，但仍嵌在 workflow 中

当前 `VlmCheckpointPolicy` 已支持：

```text
structure_review
high_risk_object_review
final_consistency_review
```

但它由 `run_progressive_workflow()` 调用，不是 Runtime 工具。目标形态应拆为：

```text
review.vlm_structure
review.vlm_high_risk_object
review.vlm_final_consistency
review.generate_adjustment_proposal
```


### 2.4 Python / C++ 边界核实

本项目此前已有相当一部分多人、同步、消息和引擎接口能力下沉到 C++。Agent-native 重构不能只在 Python 层设计 Runtime，否则会出现两套事实源：Python 认为状态已更新，但 C++ LANChat / Network / Actor / Asset 同步事实并未对齐。

当前已核实的 C++ 边界包括：

```text
src/systems/network/network_system.cpp
- lanchat_start_room / join / leave
- lanchat_send_message_ex
- lanchat_send_agent_reply_ex
- lanchat_send_system_message_to_host_ex
- lanchat_register_agent / remove_agent
- peer broadcast / host relay
- metadata_json / correlation_id / target_agent_id / source_user_id
```

其中 `lanchat_send_message_ex()` 当前负责：

```text
构造 message_id
区分 host / user
写入 LanChatState
持久化 LANChat message
广播 CHAT_MESSAGE
触发 agent trigger queue
```

`lanchat_send_agent_reply_ex()` 当前负责：

```text
构造 agent reply message
写入 LanChatState
广播 CHAT_AGENT_REPLY
携带 sender_type / message_kind / target_agent_id / source_user_id / correlation_id / metadata_json
```

这说明 AgentRuntime 不能绕过 C++ LANChat 通道直接维护一套 Python-only 聊天状态。正确边界是：

```text
C++ 负责房间、成员、消息、Agent roster、网络广播、底层同步事实
Python AgentRuntime 负责计划、批次、工具图、审查、报告、业务状态
二者通过明确 Tool / Binding / Event schema 对齐
```

当前 Python 侧也已有 `EngineWriteGate`，其职责是引擎写入口串行化：

```text
import_model
remove_actor
set_transform
set_material
settle
screenshot
```

但 `EngineWriteGate` 只是写入互斥保护，不是 RuntimeState，也不是 C++/Python 接口协议。Agent-native 重构时，应把它升级为 ToolRegistry 下的 engine-write adapter，而不是让各工具自由调用 C++/Python 引擎接口。

## 3. 推荐目标架构

### 3.1 目标架构图

```text
┌────────────────────────────────────────────────────────────────────┐
│                    LANChat / 单人输入 / 多人用户 / Agent            │
│       普通聊天、方案讨论、确认、介入、状态查询、完成后调整           │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                v
┌────────────────────────────────────────────────────────────────────┐
│                         AgentRuntime                              │
│ - 唯一用户入口                                                     │
│ - 管理 plan / batch / tool graph / runtime state / operation log    │
│ - 调度 GM / Planner / Builder / Reviewer                           │
│ - 禁止用户入口直连旧 workflow                                      │
└───────┬──────────────┬──────────────┬──────────────┬────────────────┘
        │              │              │              │
        v              v              v              v
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│ GM Agent     │ │ Planner Agent│ │ Builder Agent│ │ Reviewer Agent    │
│ 总结/仲裁/确认│ │ ScenePlan    │ │ Batch/Tool   │ │ 审查/调整建议      │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘
       │                │                │                  │
       └────────────────┴────────────────┴──────────────────┘
                                │
                                v
┌────────────────────────────────────────────────────────────────────┐
│                         ToolCallGraph                              │
│ 串行 / 并行 / 依赖 / 重试 / 取消 / abandoned late result             │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                v
┌────────────────────────────────────────────────────────────────────┐
│ RuntimeGuard + ToolRegistry                                        │
│ 权限、风险、确认、工具存在性、schema 校验、写操作拦截                │
└──────────────┬───────────────────────────────┬─────────────────────┘
               │                               │
               v                               v
┌──────────────────────────────┐   ┌─────────────────────────────────┐
│ Atomic / Mid-grain Tools      │   │ RuntimeState / OperationLog      │
│ plan/asset/import/layout/VLM  │   │ 状态合并、版本、复盘、报告依据    │
└──────────────┬───────────────┘   └──────────────┬──────────────────┘
               │                                  │
               v                                  v
┌──────────────────────────────┐   ┌─────────────────────────────────┐
│ Engine / Asset / Network      │   │ User-visible Report / Progress   │
│ 真实引擎、资源、actor、同步     │   │ 只读 RuntimeState + OperationLog │
└──────────────────────────────┘   └─────────────────────────────────┘
```

### 3.2 架构不变量

后续所有拆任务、代码实现和验收都必须遵守这些不变量：

```text
1. 用户入口只能进入 AgentRuntime
2. Agent 只能产出结构化对象，不直接执行
3. ToolCallGraph 是唯一执行编排
4. RuntimeGuard 是唯一写权限判断
5. RuntimeState 是唯一状态事实源
6. OperationLog 必须先于用户报告
7. 真实引擎返回优先于 Agent 计划
8. ToolResult 不直接改状态，只能提交 StatePatch
9. 没有 Validator 通过的 Agent 输出不得执行
10. 旧 workflow 主控入口不得重新暴露给普通用户
```

## 4. 核心模块设计

### 4.1 AgentRuntime

新增目录：

```text
editor/plugins/AITool/services/agent_runtime/
```

核心文件：

```text
agent_runtime.py
runtime_state.py
scene_plan.py
batch_plan.py
tool_call.py
tool_call_graph.py
tool_result.py
tool_registry.py
runtime_guard.py
operation_log.py
state_patch.py
validators.py
agent_roles.py
runtime_events.py
runtime_errors.py
```

核心 API：

```python
AgentRuntime.handle_message()
AgentRuntime.confirm_plan()
AgentRuntime.handle_intervention()
AgentRuntime.query_state()
AgentRuntime.apply_adjustment()
AgentRuntime.generate_report()
```

禁止普通入口直接调用：

```text
SceneComposer.compose()
run_progressive_workflow()
GenerationScheduler.submit()
IncrementalImport
FinalAdjustment
ActorSync
```

### 4.2 Agent Roles

#### GM Agent

职责：

```text
总结多人讨论
澄清模糊意图
仲裁多人冲突
提出确认请求
控制暂停 / 继续节奏
```

禁止：

```text
直接生成模型
直接导入场景
直接修改 actor
直接调用旧 workflow
```

#### Planner Agent

职责：

```text
把用户需求和多人讨论转成 ScenePlan
判断 indoor / outdoor / mixed
区分 object / substrate / terrain / boundary / lighting / layout
生成风格、空间、资源、交互约束
```

#### Builder Agent

职责：

```text
把 confirmed ScenePlan 拆成 BatchPlan
规划每批 ToolCallGraph
吸收生成中用户介入
决定失败时重试、跳过或询问用户
```

#### Reviewer Agent

职责：

```text
读取 RuntimeState
检查缺失、浮空、穿模、比例、风格、同步异常
生成 AdjustmentProposal
不直接执行修改
```

### 4.3 ScenePlan

`ScenePlan` 替代 `SeedPlan` 成为计划事实源。`SeedPlan` 可作为迁移期输入或兼容映射，但新链路的状态以 `ScenePlan` 为准。

建议结构：

```python
@dataclass
class ScenePlan:
    plan_id: str
    room_id: str
    source_user_id: str
    owner_agent_id: str | None
    scene_goal: str
    scene_type: Literal["indoor", "outdoor", "mixed", "unknown"]
    design_brief: str
    required_items: list[dict]
    environment_items: list[dict]
    style_constraints: list[str]
    spatial_constraints: dict
    interaction_constraints: dict
    status: Literal["draft", "proposed", "confirmed", "running", "completed", "failed", "obsolete"]
    version: int
```

### 4.4 BatchPlan

`BatchPlan` 替代 progressive workflow phase 成为批次事实源。

```python
@dataclass
class BatchPlan:
    batch_id: str
    plan_id: str
    batch_index: int
    batch_goal: str
    items: list[dict]
    absorbed_interventions: list[dict]
    tool_graph_id: str | None
    status: Literal["pending", "running", "waiting", "completed", "failed", "skipped"]
```

### 4.5 ToolCallGraph

`ToolCallGraph` 替代旧 workflow 成为执行事实源。

```python
@dataclass
class ToolCallGraph:
    graph_id: str
    plan_id: str
    batch_id: str | None
    nodes: dict[str, ToolCall]
    edges: list[tuple[str, str]]
    status: Literal["pending", "running", "completed", "failed", "abandoned"]
```

必须支持：

```text
串行执行
并行执行
依赖等待
失败跳过
失败中断
重试
取消
abandoned late result
```

执行规则：

```text
无依赖节点可并行
依赖失败时按 node policy 决定 skip / retry / abort
用户介入可取消未开始节点
迟到结果若 graph version 已过期，标 abandoned，不写入 RuntimeState
```

### 4.6 ToolCall / ToolResult

```python
@dataclass
class ToolCall:
    tool_call_id: str
    tool_name: str
    input: dict
    source_agent: str
    plan_id: str | None
    batch_id: str | None
    risk_level: Literal["low", "medium", "high"]
    requires_confirmation: bool
    status: Literal["queued", "running", "success", "failed", "rejected", "abandoned"]
```

```python
@dataclass
class ToolResult:
    tool_call_id: str
    success: bool
    result: dict
    error_code: str | None
    error_message: str | None
    state_patch: StatePatch | None
    user_visible_message: str | None
```

硬规则：

```text
无 ToolCall 不执行
无 RuntimeGuard 不写场景
无 ToolResult 不更新状态
无 OperationLog 不算完成
```

### 4.7 StatePatch

ToolResult 不直接改 RuntimeState，只返回 StatePatch。

```python
@dataclass
class StatePatch:
    patch_id: str
    base_version: int
    target: Literal["plan", "batch", "scene", "asset", "actor", "geometry", "review", "sync"]
    operations: list[dict]
    source_tool_call_id: str
```

合并规则：

```text
RuntimeState.apply_patch() 统一合并
patch 必须带 base_version
版本不一致进入 reconcile
真实引擎返回 > Tool 预期 > Agent 计划
失败 ToolCall 不得写 success state
late result 只能写 OperationLog，不能覆盖新状态
```

### 4.8 RuntimeState

RuntimeState 是唯一状态事实源。

```python
@dataclass
class RuntimeState:
    room_id: str
    active_plan_id: str | None
    active_batch_id: str | None
    plans: dict[str, ScenePlan]
    batches: dict[str, BatchPlan]
    tool_calls: dict[str, ToolCall]
    scene_state: dict
    asset_state: dict
    actor_state: dict
    geometry_state: dict
    review_state: dict
    sync_state: dict
    pending_interventions: list[dict]
    operation_log_ids: list[str]
    version: int
```

状态查询、GM 总结、Reviewer 审查、最终报告只能读取 RuntimeState 和 OperationLog。

### 4.9 RuntimeGuard

风险等级：

```text
Low:
状态查询、计划生成、报告生成、AABB 检查、VLM 审查

Medium:
模型导入、普通 actor 移动、贴地、低风险布局调整

High:
删除 actor、替换模型、重生成、修改 system actor、多人广播、覆盖场景
```

确认规则：

```text
完整生成必须确认
多人方案执行必须确认
生成中追加可按配置确认
完成态低风险贴地可自动执行
删除 / 替换 / 重生成必须确认
system actor 默认禁止修改
VLM 建议只生成 proposal
```

禁止普通调整：

```text
__room_box
__room_terrain
_terrain_boundary
__terrain_boundary
sky
terrain
```

### 4.10 Validators

必须新增：

```text
ScenePlanValidator
BatchPlanValidator
ToolCallGraphValidator
ToolCallValidator
AdjustmentProposalValidator
StatePatchValidator
```

校验内容：

```text
必填字段完整
工具名存在于 ToolRegistry
风险等级合法
system actor 修改被禁止
object / substrate / terrain 分类合法
BatchPlan 引用的 item 存在
AdjustmentProposal 只包含允许的低风险 delta
```

Agent 输出不通过 validator 时：

```text
不进入执行
写 OperationLog
向用户返回澄清或失败原因
```

## 5. 旧代码处理分类

旧代码不一刀切删除，按四类处理：

```text
A. 主控类：删除 / 禁用 / 隐藏
B. 可复用函数类：拆成 Tool
C. 状态类：迁移到 RuntimeState
D. 测试 / 文档类：保留为 legacy regression baseline
```

### 5.1 A 类：主控类

包括：

```text
完整 compose 主流程
progressive workflow 主控
旧 scheduler 业务主控
旧 direct final adjustment
旧 direct sync entry
旧用户可触发 slash command
```

处理：

```text
普通用户入口禁用
不允许作为 legacy big tool 保留
不允许继续决定 plan / batch / report / user status
```

### 5.2 B 类：可复用函数类

包括：

```text
对象提取函数
场景类型判断函数
模型生成 provider
资源路径解析函数
导入 API
AABB 计算函数
贴地函数
VLM 调用函数
actor 广播函数
文件同步函数
```

处理：

```text
拆成 ToolRegistry 中的工具
所有调用必须产生 ToolCall / ToolResult / StatePatch / OperationLog
```

### 5.3 C 类：状态类

包括：

```text
workflow phase
pending items
imported actors
failed assets
review result
sync progress
final report fields
```

处理：

```text
迁移到 RuntimeState
旧内部状态只作为 ToolResult 输入，不作为用户可见事实源
```

### 5.4 D 类：测试 / 文档类

处理：

```text
旧测试先标记为 legacy regression
对应 AgentRuntime 测试 + F5 验收都通过后，再删除或归档
不要过早删除旧测试
```

## 6. 工具拆解映射

### 6.1 Plan / parsing tools

```text
scene.classify_type
scene.extract_objects
scene.extract_environment
scene.extract_constraints
scene.create_plan
scene.update_plan
```

### 6.2 Batch tools

```text
batch.create
batch.merge_intervention
batch.prioritize_items
batch.mark_completed
batch.mark_failed
```

### 6.3 Asset tools

```text
asset.route_item
asset.generate_image
asset.retrieve_model
asset.generate_model
asset.resolve_model_path
asset.cache_lookup
asset.cache_store
```

### 6.4 Environment tools

```text
environment.resolve_substrate
terrain.create
terrain.update
boundary.create
boundary.update
room.estimate_bounds
room.create_box
zone.create_indoor
zone.create_outdoor
zone.create_transition
```

### 6.5 Import / actor tools

```text
actor.import_model
actor.create
actor.place
actor.move
actor.rotate
actor.scale
actor.delete_guarded
actor.query
actor.list
```

### 6.6 Geometry tools

```text
geometry.compute_aabb
geometry.check_overlap
geometry.check_room_bounds
geometry.snap_to_ground_selective
geometry.check_walkable_path
geometry.repair_low_risk
```

### 6.7 Review tools

```text
review.aabb
review.vlm_structure
review.vlm_high_risk_object
review.vlm_final_consistency
review.generate_adjustment_proposal
```

### 6.8 Sync tools

```text
sync.actor_snapshot
sync.actor_broadcast
sync.asset_transfer
sync.peer_status
sync.reconcile_remote_state
```

### 6.9 Report tools

```text
report.progress
report.plan_summary
report.batch_summary
report.final
report.failure_reason
```


## 7. Python / C++ 接口统一层设计

Agent-native 重构必须把 Python 和 C++ 的接口边界统一捋清楚。否则 RuntimeState、LANChatState、Engine scene state、Network sync state 会分裂。

### 7.1 事实源分层

推荐事实源划分：

```text
C++ 事实源：
- 房间与 peer 连接状态
- LANChat 原始消息、成员、Agent roster
- message_id / seq / timestamp
- actor 创建、transform、删除的引擎事实
- 资源同步和 peer 传输事实
- 底层网络广播结果

Python AgentRuntime 事实源：
- ScenePlan
- BatchPlan
- ToolCallGraph
- RuntimeState 业务视图
- pending_interventions
- review_state
- OperationLog
- 用户可见报告

共享事实：
- actor_id
- asset_id / model_path / resource hash
- room_id
- plan_id
- batch_id
- tool_call_id
- correlation_id
```

设计原则：

```text
C++ 返回的真实引擎结果优先于 Agent 计划
Python Runtime 不伪造 C++ 成功结果
C++ 消息和同步事件必须能映射到 RuntimeState
RuntimeState 只能通过 C++ result / ToolResult / StatePatch 更新
```

### 7.2 Runtime-C++ Bridge

新增或明确一层桥接模块：

```text
runtime_cpp_bridge.py
```

职责：

```text
封装 C++ binding 调用
统一参数 schema
统一返回 result schema
把 C++ error code 映射成 ToolResult.error_code
把 C++ success result 映射成 StatePatch
把 C++ event/callback 映射成 RuntimeEvent
```

禁止：

```text
业务 Agent 直接调用 CoronaEngine.* binding
业务 Agent 直接调用 NetworkSystem 暴露函数
业务 Agent 直接调用 SceneTools.create_actor
业务 Agent 直接写 LANChat message
```

### 7.3 C++ 接口工具化分类

LANChat tools：

```text
lanchat.send_user_message
lanchat.send_agent_reply
lanchat.send_system_message
lanchat.query_room_state
lanchat.query_history
lanchat.register_agent
lanchat.remove_agent
```

Engine actor tools：

```text
engine.actor.import_model
engine.actor.create
engine.actor.query
engine.actor.list
engine.actor.set_transform
engine.actor.remove_guarded
engine.actor.snapshot
```

Engine geometry tools：

```text
engine.geometry.compute_aabb
engine.geometry.query_bounds
engine.geometry.snap_to_ground
engine.geometry.check_overlap
```

Network sync tools：

```text
network.sync_actor_snapshot
network.broadcast_actor_delta
network.transfer_asset
network.query_peer_sync_state
network.reconcile_peer_state
```

VLM / screenshot tools：

```text
engine.capture_viewport
review.vlm_structure
review.vlm_final_consistency
```

所有这些工具都必须遵守：

```text
ToolCall -> RuntimeGuard -> runtime_cpp_bridge -> C++ binding/API -> ToolResult -> StatePatch -> RuntimeState
```

### 7.4 C++/Python 统一 ID 与 metadata 规范

必须统一这些字段：

```text
room_id
user_id
peer_id
agent_id
message_id
correlation_id
plan_id
batch_id
tool_call_id
actor_id
asset_id
resource_hash
```

LANChat message 的 `metadata_json` 应成为 Runtime 事件桥，而不是塞任意临时字段。建议 metadata 至少支持：

```json
{
  "runtime_event": "plan_created | plan_confirmed | batch_started | tool_started | tool_completed | review_created | sync_partial",
  "plan_id": "...",
  "batch_id": "...",
  "tool_call_id": "...",
  "correlation_id": "...",
  "visibility": "host | room | agent | debug"
}
```

### 7.5 C++ 下沉能力迁移原则

已经迁到 C++ 的能力，不要再搬回 Python。正确处理方式是：

```text
C++ 保持底层事实与执行
Python Runtime 通过工具接口调度
ToolResult 把 C++ 结果变成 StatePatch
OperationLog 记录 Python 决策与 C++ 执行结果
```

如果某个功能当前一半在 Python、一半在 C++，必须在迁移任务中明确：

```text
谁是事实源
谁负责执行
谁负责状态转换
谁负责用户可见报告
失败码从哪里产生
是否需要 F5/实机验证
```

## 8. 失败策略

ToolCallGraph 执行失败必须有明确策略，不能靠异常向外冒泡。

```text
资源生成失败：
  可重试；可降级 retrieve；仍失败则标 asset failed，不创建 actor

导入失败：
  标记 import failed；不创建 actor；不写 actor_state success

AABB 失败：
  写 review warning；不阻塞全部生成；相关 actor 标 geometry_unknown

贴地失败：
  写 adjustment warning；不伪装成功；允许用户后续再次调整

VLM 失败：
  写 review unavailable / failed；不阻塞主链路

同步失败：
  场景生成可完成，但 sync_state 标 partial / failed

高风险 guard 拒绝：
  请求用户确认，或终止该 action

StatePatch 冲突：
  进入 reconcile；真实引擎事实优先；旧 patch 标 stale

late result：
  写 OperationLog；不覆盖 RuntimeState
```

## 9. 实施节奏

### Phase 0：冻结旧入口与调用点扫描

目标：明确旧主控边界。

动作：

```text
同步远端 main
确认 Quasar 状态
隔离或提交现有计划文档
扫描普通入口到 SceneComposer / ProgressiveWorkflow / Scheduler 的调用点
新增 test_no_direct_workflow_entry.py
```

完成标准：

```text
旧主控入口清单明确
用户入口清单明确
baseline 测试结果记录完成
```

可运行切片：

```text
不改执行链，只输出入口扫描报告和 baseline 测试结果
```

### Phase 1：AgentRuntime + RuntimeState + OperationLog + Mock Tool 闭环

目标：先跑通新主控，不接真实引擎。

Mock 可运行切片：

```text
用户：生成一个可爱卧室
-> Planner 产出 ScenePlan
-> 用户确认
-> Builder 产出 BatchPlan
-> ToolCallGraph 调 mock 工具
-> RuntimeState 更新
-> OperationLog 可复盘
-> Report 输出
```

完成标准：

```text
Mock 卧室完整跑通
状态查询读取 RuntimeState
最终报告读取 RuntimeState / OperationLog
```

### Phase 2：ToolRegistry / RuntimeGuard / ToolCallGraph 完整化

目标：执行底座补完整，再拆旧模块。

实现：

```text
ToolRegistry.register()
RuntimeGuard.check()
ToolCallGraphExecutor.run()
RuntimeState.apply_patch()
OperationLog.append()
Validators.validate()
```

可运行切片：

```text
真实 ScenePlan + Mock 资源 + Mock 导入
```

完成标准：

```text
高风险操作被拦截
中风险操作按规则确认
低风险查询自动执行
ToolCallGraph 支持依赖、失败、重试、abandoned late result
```

### Phase 3：拆 SceneComposer 为 plan / asset / placement 工具

目标：SceneComposer 不再主控完整生成。

拆出工具：

```text
scene.classify_type
scene.extract_objects
scene.extract_environment
scene.extract_constraints
asset.route_item
room.estimate_bounds
zone.decompose
placement.prepare_items
```

禁止：

```text
用户入口 -> SceneComposer.compose()
SceneComposer 一次性控制 extract -> model -> import -> review -> report
```

可运行切片：

```text
真实对象提取 + 真实场景类型判断 + Mock 导入
```

完成标准：

```text
SceneComposer 中的能力被 ToolCall 调用
SceneComposer 不再生成最终报告
```

### Phase 4：拆 ProgressiveWorkflow 为 batch / import / review 工具

目标：批次事实源从 workflow phase 迁移到 BatchPlan。

拆出工具：

```text
batch.create
batch.merge_intervention
batch.prioritize_items
actor.import_model
actor.place
geometry.repair_low_risk
review.vlm_checkpoint
report.progress
```

可运行切片：

```text
真实 BatchPlan + Mock 资源 + 真实 import dry path / 轻量导入路径
```

完成标准：

```text
每批由 Builder Agent 生成
每个批次步骤是 ToolCall
用户介入进入 Runtime pending_interventions
```

### Phase 5：拆 Scheduler 为 ToolCallGraph Executor

目标：Scheduler 不再主控业务状态，只提供队列执行能力。

迁移：

```text
GenerationScheduler queue -> ToolCallGraph queue
priority -> ToolCall priority
cancel / pause -> Runtime command
status_change -> Runtime event
backpressure -> AssetState / ToolCall state
```

可运行切片：

```text
真实资源生成 + Mock 同步
```

完成标准：

```text
状态查询不读旧 Scheduler 内部状态
Scheduler 不决定 plan / batch / report
```

### Phase 6：拆 Geometry / VLM / Layout Adjustment

目标：审查与完成态调整全部工具化。

工具：

```text
geometry.compute_aabb
geometry.check_room_bounds
geometry.snap_to_ground_selective
geometry.check_overlap
review.vlm_structure
review.vlm_high_risk_object
review.vlm_final_consistency
review.generate_adjustment_proposal
actor.apply_transform_delta
```

可运行切片：

```text
真实 AABB / 贴地 / layout proposal 跑通
```

完成标准：

```text
浮空检查是 ToolCall
贴地是 ToolCall
完成态调整通过 Reviewer + RuntimeGuard + ToolCall 执行
VLM 只产出 proposal，不直接改场景
```

### Phase 7：拆 Sync

目标：多人同步进入 RuntimeState，不再是导入副作用。

工具：

```text
sync.actor_snapshot
sync.actor_broadcast
sync.asset_transfer
sync.peer_status
sync.reconcile_remote_state
```

SyncState：

```text
actor_created
asset_ready
actor_broadcasted
peer_received_actor
peer_requested_asset
asset_transferred
peer_asset_ready
peer_instantiated_actor
sync_failed
```

可运行切片：

```text
真实同步状态跑通
```

完成标准：

```text
生成成功 != 导入成功 != 同步成功
远端缺资源可查询
重复资源不重复传
```

### Phase 8：隐藏旧主控入口 + 静态扫描 + F5 验收

目标：完成正式切换。

处理：

```text
隐藏旧 slash command
禁用 direct compose 用户入口
禁用 progressive compose 用户入口
禁用 final adjustment direct 入口
禁用 sync direct 入口
```

完成标准：

```text
静态扫描无普通用户路径直连旧 workflow 主控
旧 workflow 只剩函数级工具能力
```

## 10. 测试计划

### 10.1 新增测试

```text
test_agent_runtime_mock_flow.py
test_scene_plan.py
test_batch_plan.py
test_tool_call_graph.py
test_tool_registry.py
test_runtime_guard.py
test_runtime_state.py
test_state_patch_merge.py
test_operation_log.py
test_validators.py
test_no_direct_workflow_entry.py
test_scene_composer_decomposed_tools.py
test_progressive_workflow_decomposed_tools.py
test_scheduler_as_tool_executor.py
test_runtime_intervention.py
test_runtime_adjustment.py
test_runtime_sync_state.py
```

### 10.2 旧测试处理

```text
旧 workflow 测试先标 legacy regression
不要在 AgentRuntime 对应测试和 F5 验收通过前删除旧测试
当新 Runtime 测试覆盖同等能力后，再删除或归档旧测试
```

### 10.3 保留回归

```powershell
python editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/test_lanchat_agent_orchestrator.py
python editor/plugins/AITool/services/test_intent_understanding.py
python editor/plugins/AITool/cai_extensions/agent/test_scene_element_classifier.py
python editor/plugins/AITool/cai_extensions/agent/test_scene_composer_progressive_geometry.py
python editor/plugins/AITool/cai_extensions/agent/test_vlm_review_loop.py
node editor/Frontend/scripts/test-lanchat-roster.mjs
```

## 11. F5 验收场景

### 11.1 单人卧室

目标：

```text
验证 AgentRuntime 主控、ScenePlan、room box、object/substrate 分类、贴地与最终报告
```

脚本：

```text
帮我设计一个可爱的卧室，有床、书桌、衣柜、台灯、地毯、玩偶、书架
确认生成
完成后：调整一下布局
如果浮空：把模型都落地
```

### 11.2 多 Agent 藏宝室

目标：

```text
验证多人/多 Agent 讨论承接、GM 总结、ScenePlan 确认、完成态调整
```

脚本：

```text
@长者 围绕强盗藏宝室主题讨论一下
@商人 评价并改进长者方案
@GM 总结当前方案
按照这个方案生成
确认生成
完成后：调整一下布局，我看模型位置冲突
确认调整
```

### 11.3 室外森林营地

目标：

```text
验证 substrate / terrain 不进入普通模型生成
```

脚本：

```text
做一个森林营地，有天空、树林、草地、小木桌、帐篷
确认生成
```

### 11.4 混合幻想集市

目标：

```text
验证 mixed zone、批次介入、追加对象、最终报告
```

脚本：

```text
做一个室内外结合的夜晚幻想集市，有入口、摊位、灯光、休息区
生成中：再加一个天使雕像
生成中：再加一只小狗
完成后：查看吸收了哪些调整
```

### 11.5 多人同步

目标：

```text
验证 actor sync / asset transfer / peer status 进入 RuntimeState
```

脚本：

```text
房主创建房间
其他用户加入
房主多 Agent 讨论后确认生成
观察其他用户 actor / asset / sync 状态
模拟远端缺资源或断线重连
```

## 12. 完成标准

本次重构完成必须满足：

```text
1. 用户入口全部进入 AgentRuntime
2. ScenePlan 替代 SeedPlan 成为计划事实源
3. BatchPlan 替代 workflow phase 成为批次事实源
4. ToolCallGraph 替代旧 workflow 成为执行事实源
5. RuntimeState 是唯一状态源
6. OperationLog 可回放完整执行路径
7. StatePatch 统一合并状态
8. Agent 输出必须经过 Validator
9. SceneComposer 不再主控完整生成
10. ProgressiveWorkflow 不再主控批次执行
11. Scheduler 不再主控业务状态
12. Geometry / VLM / Layout / Sync 全部工具化
13. 生成中介入进入 Runtime pending_interventions
14. 完成态调整进入 Reviewer + RuntimeGuard + ToolCall
15. 旧 workflow 主控入口被隐藏或删除
16. ALLOW_LEGACY_MAIN_WORKFLOW=0
```

## 13. 风险与反模式

### 13.1 把旧 workflow 包成大工具

反模式：

```text
legacy.scene_compose()
legacy.progressive_compose()
legacy.workflow_orchestrator()
```

问题：

```text
旧 workflow 继续暗中主控
RuntimeState 只能拿结果
用户介入仍不能实时控制中间状态
```

处理：

```text
禁止保留这类大工具
只能保留函数级能力
```

### 13.2 先拆旧链路再补新链路

反模式：

```text
先删除 SceneComposer / ProgressiveWorkflow 主路径
再尝试补 AgentRuntime
```

处理：

```text
每拆一个旧能力，必须已有 ToolCall 替代
每个 Phase 必须有可运行切片
```

### 13.3 Agent 直接写场景

反模式：

```text
Agent 直接调用 import / move / delete / sync
```

处理：

```text
所有写操作必须经过 RuntimeGuard
所有执行必须是 ToolCall
```

### 13.4 RuntimeState 与真实引擎不一致

处理：

```text
真实引擎返回优先于 Agent 计划
ToolResult 必须提供 StatePatch
StatePatch 冲突进入 reconcile
```

### 13.5 过早删除旧测试

处理：

```text
旧测试先标 legacy regression
新 Runtime 测试和 F5 验收覆盖后再删除或归档
```

## 14. Feature Flag 与边界

本次重构接受较大架构变动，但仍需要工程开关防止实机完全不可用：

```text
AGENT_RUNTIME_ENABLED=1
OLD_WORKFLOW_DIRECT_ENTRY_DISABLED=1
ALLOW_LEGACY_FUNCTION_ADAPTER=1
ALLOW_LEGACY_MAIN_WORKFLOW=0
```

含义：

```text
允许复用旧代码里的底层函数
不允许复用旧 workflow 主控
不允许用户入口回旧链路
不允许 legacy compose whole scene
```

本计划不包含：

```text
C++ / CMake / Ninja / CEF 底层构建改造
引入外部 Agent 框架
重做全部前端 UI
VLM 自动强执行修改
产品级权限系统
```

## 15. 最终建议

本次大改应定名为：

```text
Agent-native Runtime 主控重构
```

而不是：

```text
纯 Agent 自由执行
旧 workflow 包装升级
```

最终目标是：

```text
Agent 负责规划与决策
ToolCallGraph 负责编排
RuntimeGuard 负责权限和风险
ToolRegistry 负责能力执行
RuntimeState 负责事实状态
OperationLog 负责可回放
旧 workflow 主控退场，底层能力工具化
```

只有完成这次主控权迁移，后续“实时介入”才不是聊天层的延迟吸收，而是可以在 Runtime 中真正取消、插队、替换、暂停、继续、确认和回放的交互能力。



