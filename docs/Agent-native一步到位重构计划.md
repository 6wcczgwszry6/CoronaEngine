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

### 13.6 2026-07-03 当前落盘增量

本轮已完成的非 native 切片：

```text
1. AgentRuntimeFlags 默认保持 Runtime 主控：
   - AGENT_RUNTIME_ENABLED 默认开启
   - OLD_WORKFLOW_DIRECT_ENTRY_DISABLED 默认开启
   - ALLOW_LEGACY_MAIN_WORKFLOW 默认关闭
   - 真实 provider / engine-write 通道均默认关闭

2. 真实 engine-write provider 必须显式开启：
   - AGENT_RUNTIME_USE_ENGINE_ENVIRONMENT_IMPORT_PROVIDER
   - AGENT_RUNTIME_USE_ENGINE_IMPORT_PROVIDER
   - AGENT_RUNTIME_USE_ENGINE_DELETE_PROVIDER
   - AGENT_RUNTIME_USE_ENGINE_TRANSFORM_PROVIDER

3. LANChat Runtime 工厂已支持显式装配 actor delete provider：
   - flag：AGENT_RUNTIME_USE_ENGINE_DELETE_PROVIDER
   - 工具候选：remove_actor / delete_actor / destroy_actor
   - 写入边界：make_engine_actor_delete_provider + EngineWriteGate.remove_actor
   - 默认仍为 RuntimeState-only，不会自动删除真实引擎 actor

4. engine_write_status 已统一为四通道读侧：
   - environment_import
   - actor_import
   - actor_delete
   - layout_transform
   - LANChat / GM engine_write report 展示同样显示 env-import 与 actor-delete，不再只显示 import / transform

5. verify_ultimate_plan.py 已把关键过渡边界纳入非 native 总门禁：
   - agent_runtime/*
   - lanchat_agent_worker.py
   - lanchat_host_action_executor.py
   - generation_scheduler.py
   - generation_composer_adapter.py
   - engine_write_gate.py
   - scene_composer_progressive.py

6. Review / VLM checkpoint 已补齐 RuntimeState 读侧事实源：
   - RuntimeState room schema 显式包含 custom_vlm_checkpoint_facts
   - runtime.review.vlm_checkpoint 的结果会与 geometry_reviews 一起进入 review_summary
   - status_summary / generate_report 均可看到 VLM checkpoint 的 checkpoint_type、status、reviewed_targets 与 advisory_count
   - VLM advisory 仍只形成 review_advisory_proposals，必须房主确认，不直接修改 actors
   - OperationLog 仅保留 VLM checkpoint 的安全摘要字段，operation_replay / report compact replay 均可回放 checkpoint_count、status_counts、advisory_count
   - runtime.review.vlm_checkpoint 会发出安全用户可见 RuntimeEvent：外观审查完成 / 已跳过 / 等待房主确认，不暴露 provider、prompt、截图路径或 raw payload

7. 资源准备阶段已补齐安全 RuntimeEvent：
   - runtime.asset.image.prepare / runtime.asset.model.prepare 成功后会披露图片资源 / 模型资源准备进度
   - RuntimeEvent payload 只允许 status、requested_count、ready_count、failed_count 等计数字段
   - 不暴露 provider、prompt、metadata、内部 URL、私有路径或 raw payload

8. 场景物体导入成功路径已补齐安全 RuntimeEvent：
   - runtime.actor.import_batch 成功后会披露本批场景物体导入完成 / 部分完成
   - RuntimeEvent payload 只允许 status、requested_count、imported_count、failed_count 等计数字段
   - partial import 会明确显示已导入数量与失败数量，但不暴露 actor_id、model_path、provider、import_results raw 或私有路径

9. 同步事实已具备 RuntimeState / OperationLog / RuntimeEvent 基础闭环：
   - record_sync_event 会通过 runtime.sync_event.record ToolCallGraph 写入 sync_events / sync_state / actors / assets
   - actor create / transform / delete、asset transfer、peer join / leave / room close 均可进入 status_summary / generate_report / operation_replay
   - OperationLog replay 会保留安全 latest_peer_id，便于复盘多人 peer join / leave，不再只知道“发生过 peer 事件”
   - 同步用户事件只披露安全摘要，不暴露 asset_path、message_id、correlation_id、provider、URL 或私有路径

10. 方案提炼 / 元素分类已具备 ToolCallGraph 安全披露：
   - runtime.plan.extract 成功后会披露“方案提炼完成”，只暴露候选物体数量与布局/环境要素数量
   - runtime.elements.classify 成功后会披露“元素分类完成”，只暴露准备生成模型数量与环境/地形/布局要素数量
   - RuntimeEvent payload 仅透传 status、item_count、component_count 等安全计数字段
   - 不暴露 candidate_items/routes/prompt/provider/model_path/raw payload 或私有路径
   - 这一步把“LLM 提炼好的模型/地形信息要让用户知道”的要求落到 AgentRuntime ToolCall 事件层，而不是回到旧 SceneComposer 文案拼接

11. 最终报告写入已具备 ToolCallGraph 安全披露：
   - generate_report 仍先写 OperationLog，再通过 runtime.user_report.persist 写入 RuntimeState
   - runtime.user_report.persist 成功后会发出“最终报告已写入 Runtime 状态”的安全 RuntimeEvent
   - 该事件 payload 仅包含 status，不暴露 report 全文、operation_log_index、provider、prompt、raw payload 或私有路径
   - report_ready 仍作为最终用户报告完成事件，report persist 事件用于证明报告状态已进入 RuntimeState，可被后续查询与复盘读取

12. 批次规划已具备 ToolCallGraph 安全披露：
   - plan_batches 会通过 runtime.batch.plan_record 写入 batch_plans / absorbed intervention 状态
   - runtime.batch.plan_record 成功后会发出“批次规划完成”的安全 RuntimeEvent
   - RuntimeEvent payload 仅透传 status、batch_count 等安全计数字段
   - 不暴露 requested_items、用户原文、provider、prompt、model_path 或 raw batch state
   - 这一步覆盖“只规划批次但尚未排队执行”的阶段，避免批次计划继续藏在函数返回值里

13. 批次执行过程已具备 OperationLog replay 摘要：
   - operation_replay / generate_report compact replay 均包含 batch_execution_summary
   - batch_execution_summary 统计 started_count、completed_count、finalized_count、status_counts 与 latest_batch
   - 摘要来源于已清洗的 OperationLog entries，不暴露 requested_items、tool graph raw、provider、prompt 或私有路径
   - 这一步让 batch started / finalized / completed 不只停留在散落日志事件中，而是形成可验收、可复盘的批次执行视图

14. 工具节点执行过程已具备 OperationLog replay 摘要：
   - operation_replay / generate_report compact replay 均包含 tool_execution_summary
   - tool_execution_summary 统计 started_count、succeeded_count、failed_count、blocked_count、retry_scheduled_count、skipped_count
   - 摘要同时保留 tool_event_counts 与 latest_tool_event，便于定位 ToolCallGraph 内部健康度
   - 摘要来源于已清洗的 OperationLog entries，不暴露 tool args、raw result、provider、prompt、model_path 或私有路径
   - 这一步让 ToolCall 节点级执行不再只能逐条翻日志，而是形成可审计的图执行视图

15. ToolCallGraph 队列生命周期已具备 OperationLog replay 摘要：
   - operation_replay / generate_report compact replay 均包含 tool_graph_queue_summary
   - tool_graph_queue_summary 统计 queued_count、dequeued_count、completed_count、rejected_count、empty_count、blocked_count、missing_graph_count
   - 摘要同时保留 queue_status_counts、queue_event_counts 与 latest_queue_event，便于复盘 Runtime 执行队列是否积压、满队列、被暂停/取消阻断或缺失 graph
   - completed_count 只来自 tool_graph_queue_state_persisted 的 completed 状态，不把通用 tool_graph_completed 误算为队列完成
   - 摘要来源于已清洗的 OperationLog entries，不暴露 graph raw、tool args、provider、prompt、model_path 或私有路径
   - 这一步继续推进 “GenerationScheduler queue -> ToolCallGraph queue” 的读侧替换，让队列健康度进入 Runtime 可验收视图

16. 资源通道 readiness 已具备 OperationLog replay 摘要：
   - operation_replay / generate_report compact replay 均包含 resource_readiness_replay_summary
   - resource_readiness_replay_summary 统计 status_query_count、published_count、publish_failed_count、readiness_event_count 与 status_counts
   - 摘要从 raw OperationLog 聚合，但只输出安全计数和 latest_readiness_event，不暴露具体 provider 名称、provider 函数、诊断 reason、prompt、URL 或私有路径
   - 对外字段刻意使用 resource_readiness 而不是 provider_readiness，避免复盘对象被普通用户理解为内部 provider 细节
   - 这一步让“资源通道是否已预检 / 是否已发布 readiness / 是否产生用户可见资源通道事件”进入 Runtime 可验收视图

17. StatePatch 冲突仲裁已具备 OperationLog replay 摘要：
   - operation_replay / generate_report compact replay 均包含 state_patch_summary
   - state_patch_summary 统计 version_stamped、applied、conflict、invalid、reconcile_rejected、reconcile_missing、reconciled、reconcile_failed
   - 摘要保留 decision_counts 与 latest_reconcile_event，便于复盘 StatePatch conflict 是否已仲裁、仲裁决策是什么、是否成功落盘
   - ToolCallGraph 执行期产生的 StatePatch conflict 会补充 plan_id / batch_id 安全归属，确保按 plan_id 回放时不会丢失后续 reconciled 事件
   - 摘要不暴露 patch_id、source_tool_call_id、tool_call_id 或 StatePatch 原始内容，只输出安全计数和仲裁结果
   - 这一步让“多个 ToolCall 并发写 RuntimeState 后是否冲突 / 是否处理 / 处理结果能否复盘”进入 Runtime 可验收视图

18. 生成中介入入批已具备 OperationLog replay 摘要：
   - operation_replay / generate_report compact replay 均包含 intervention_batch_replay_summary
   - intervention_batch_replay_summary 统计 routed_count、queued_count、persisted_count、persist_failed_count、skipped_count、enqueue_failed_count、absorbed_count
   - 摘要保留 status_counts 与 latest_intervention_batch，便于复盘用户中途新增对象是否被路由、是否被吸收、是否进入下一批 ToolCallGraph 队列
   - 摘要从 OperationLog 聚合，但不暴露 patch_id、用户原文、requested_items 明细、tool graph raw、provider、prompt 或私有路径
   - 这一步让“生成中介入是否真正改变后续批次”进入 Runtime 可验收视图，而不是只依赖聊天室提示或最终报告文案

19. ScenePlan 生命周期已具备 OperationLog replay 摘要：
   - operation_replay / generate_report compact replay 均包含 scene_plan_lifecycle_summary
   - scene_plan_lifecycle_summary 统计 created_count、confirmed_count、state_persisted_count、state_persist_failed_count、status_persisted_count、status_persist_failed_count、extracted_count
   - 摘要保留 status_counts、reason_counts 与 latest_plan_event，便于复盘方案是否创建、是否确认、是否进入执行、是否完成/失败、状态是否先于报告落盘
   - batch scoped 报告中的 scene_plan_lifecycle_summary 使用 plan scope 聚合，避免最终报告只看到批次事件却看不到方案确认链路
   - 摘要不暴露 design_brief、用户原文、tool graph raw、provider、prompt 或私有路径
   - 这一步让“方案名称/方案确认/执行状态是否透明传递”进入 Runtime 可验收视图

20. RuntimeEvent 用户披露已具备 OperationLog replay 摘要：
   - operation_replay / generate_report compact replay 均包含 runtime_event_replay_summary
   - runtime_event_replay_summary 统计 emitted_count、emit_failed_count、event_type_counts 与 latest_runtime_event
   - 摘要用于复盘哪些 Runtime 事件已经安全披露给用户、是否有披露写入失败、事件类型分布是否覆盖方案确认/队列/批次/资源/报告等阶段
   - 摘要只读取 OperationLog 中的 runtime_event_emitted / runtime_event_emit_failed 安全字段，不暴露 RuntimeEvent 标题正文、用户原文、payload raw、provider、prompt 或私有路径
   - 这一步让“信息披露是否真的发生、是否持续覆盖长耗时阶段”进入 Runtime 可验收视图

21. RuntimeGuard 拦截结果已具备 OperationLog replay 摘要：
   - operation_replay / generate_report compact replay 均包含 runtime_guard_replay_summary
   - runtime_guard_replay_summary 统计 blocked_count、high_risk_confirmation_required_count、write_confirmation_required_count、system_actor_write_blocked_count、user_visible_blocked_event_count
   - 摘要保留 reason_counts 与 latest_block，便于复盘写操作被 RuntimeGuard 拦截的原因类别
   - 摘要只输出原因类别和计数，不暴露 tool_name、actor 名称、工具参数、用户原文、provider、prompt 或私有路径
   - 这一步让“RuntimeGuard 是否作为唯一写权限判断生效、是否有用户可见拦截披露”进入 Runtime 可验收视图

22. ToolCallGraph 失败策略已具备 OperationLog replay 摘要：
   - operation_replay / generate_report compact replay 均包含 tool_failure_strategy_summary
   - tool_failure_strategy_summary 统计 retry_scheduled_count、dependency_skipped_count、abandoned_late_result_count、handler_failed_count、invalid_result_count、runtime_facts_missing_count、runtime_facts_rejected_count、invalid_state_patch_count、state_patch_conflict_count、stopped_by_runtime_command_count
   - 摘要保留 strategy_counts 与 latest_strategy_event，便于复盘失败是走重试、依赖跳过、迟到结果丢弃、协议结果无效、Runtime facts 缺失/拒绝、StatePatch 冲突还是运行时暂停/取消
   - 摘要只输出策略类别、计数、batch_id、status / error_code 等安全字段，不暴露 tool_name、tool args、raw result、异常文本、provider、prompt、model_path 或私有路径
   - 这一步让“ToolCallGraph 支持依赖、失败、重试、abandoned late result，并且可被 OperationLog 证明”进入 Runtime 可验收视图

23. Runtime 状态查询已包含 ToolCallGraph 失败策略摘要：
   - status_summary 直接包含 tool_failure_strategy_summary，GM / 用户状态查询无需先触发 operation_replay 或 generate_report 也能看到失败策略健康度
   - 摘要复用 OperationLog scoped entries，只输出安全计数与 latest_strategy_event，不暴露 tool_name、tool args、异常文本、provider、prompt、URL、model_path 或私有路径
   - 这一步让“状态查询读取 RuntimeState / OperationLog，而不是旧 Scheduler 内部状态”继续向 Phase 5 目标靠拢

24. 旧 SceneComposer 主控直达入口已纳入静态门禁：
   - verify_ultimate_plan.py 新增 static direct SceneComposer entry gate，扫描 AITool services / cai_extensions/agent / main.py
   - 普通用户入口不允许新增 SceneComposer(...) / composer.compose(...) 直达旧主控
   - 当前只允许 main.py 的 composer factory、agent_adapter.py 的 legacy guard 入口、generation_composer_adapter.py 的 JobRunner adapter
   - 允许的 legacy compose 文件必须包含 Runtime flag guard：agent_adapter.py 需要 _legacy_main_workflow_allowed / AGENT_RUNTIME_REQUIRED_MESSAGE，generation_composer_adapter.py 需要 can_call_legacy_main_workflow / legacy disabled error
   - 扫描排除 Quasar、测试文件、scene_composer.py 本体，避免误伤底层能力实现与回归测试
   - 这一步把“用户入口只能进入 AgentRuntime / 旧 workflow 主控不得重新暴露为用户入口”变成可重复验证的非 native 门禁

25. 旧 slash workflow 命令暴露策略已纳入静态门禁：
   - verify_ultimate_plan.py 新增 static workflow command exposure gate，解析 workflow_command_policy.py 与 cai_extensions/agent、cai_extensions/flows 下的 WORKFLOW_COMMANDS
   - 废弃主控命令必须留在 DEPRECATED_USER_WORKFLOW_COMMANDS：/scene_agent、/sc_agent、/scene_composition、/scene_composition_v2、/sc_v2、/full_pipeline、/pipeline、/full_pipeline_v2、/fp_v2、/multi_scene、/parallel_generate、/parallel_generate_v2、/pg_v2
   - 内部调试命令必须留在 INTERNAL_DEBUG_WORKFLOW_COMMANDS：/model_retrieval、/terrain_generate、/terrain
   - 门禁确认 workflow function get / has / list_function_ids 仍经过 should_execute_workflow_function 过滤，避免绕过 slash command 直接用 function_id 执行旧主控
   - 这一步允许 legacy flow 模块继续作为 regression baseline 存在，但禁止废弃主控命令重新成为普通用户入口

26. Runtime 报告事实源顺序已纳入静态门禁：
   - verify_ultimate_plan.py 新增 static Runtime report fact-source gate，直接检查 AgentRuntime.generate_report / status_summary 的关键事实源顺序
   - generate_report 必须先构造 operation_replay_summary / classification_summary 等 RuntimeState + OperationLog 摘要，再写 user_report_generated，再持久化 report，最后发出 report_ready 事件
   - status_summary 必须保持只读状态查询语义：可以写 runtime_status_queried 审计事件，但不得写 user_report_generated、不得持久化用户报告、不得发 report_ready
   - 这一步把“OperationLog 必须先于用户报告、状态查询读取 RuntimeState / OperationLog 而不是触发报告副作用”变成可重复验证的非 native 门禁

27. Runtime Validator 契约已纳入静态门禁：
   - verify_ultimate_plan.py 新增 static Runtime validator contract gate，确认 ScenePlanValidator、BatchPlanValidator、PlanPatchValidator、StatePatchValidator、ToolCallValidator、ToolResultValidator、ToolCallGraphValidator、AdjustmentProposalValidator、ReviewAdvisoryProposalValidator、ReportRecordValidator 等关键 schema validator 持续存在
   - ToolCallGraphExecutor.execute 必须先调用 ToolCallGraphValidator.validate，并在执行前经过 RuntimeGuard.authorize，运行时事实注入后必须通过 ToolCallValidator，工具返回必须通过 ToolResultValidator
   - ToolCallGraph 持久化必须经过 ToolCallGraphValidator.safe_graph_fact，避免把 raw args / unsafe graph payload 写入 RuntimeState
   - 用户报告必须通过 runtime.user_report.persist ToolCallGraph 路径持久化，并由 _persist_user_report_tool 调用 ReportRecordValidator.validate(report) 后再提交 StatePatch；门禁按这条真实工具链检查，而不是要求 generate_report 本体直接写 RuntimeState
   - 这一步把“Agent 只能产出结构化对象、没有 Validator 通过的 Agent 输出不得执行、ToolResult 不直接改 RuntimeState”继续固化成可重复验证的非 native 门禁

28. Phase 3 场景提炼能力已开始拆成 Agent-native 工具：
   - AgentRuntime ToolRegistry 新增 scene.extract_objects、scene.classify_type、scene.extract_environment 三个只读 planning 工具
   - scene.extract_objects 只负责从用户文本提炼可生成物体，并写入 plan_extractions；抽象布局词、天空、草地等不会进入候选模型清单
   - scene.classify_type 只负责生成 scene_type / environment_type 事实，写入 custom_scene_facts，用于后续 plan / substrate / room_box 决策
   - scene.extract_environment 只负责把地形、天空、草地、森林等环境 / substrate 项写入 element_routes、classification_summaries、substrate_plans
   - 三个工具均通过 ToolCallGraphExecutor 执行、RuntimeGuard 授权、ToolResult / StatePatch schema 校验，不包装旧 SceneComposer / ProgressiveWorkflow 主控
   - runtime.plan.extract / runtime.elements.classify 继续作为既有图节点保留，保证现有 ToolCallGraph 测试和过渡链路兼容；新 scene.* 工具用于 Phase 3 拆解粒度收敛
   - 新增 test_phase3_scene_extraction_tools_are_registered_without_legacy_main_control 与 test_phase3_scene_extraction_tools_split_objects_and_environment，验证工具注册不含旧主控词、森林营地中的帐篷 / 小木桌进入模型清单，天空 / 草地进入 substrate plan
   - 这一步开始把“SceneComposer 的提取 / 分类职责”拆成可审计 ToolCall，而不是继续让旧主控一次性完成场景理解、资源、导入和报告

29. Phase 3 方案约束提炼已拆成 Agent-native 工具：
   - AgentRuntime ToolRegistry 新增 scene.extract_constraints 只读 planning 工具
   - scene.extract_constraints 从方案文本提炼 mood、style_keywords、avoid_keywords、palette、lighting、scale_rules、placement_rules，并写入 custom_scene_facts
   - “不要太恐怖 / 不恐怖”进入 avoid_keywords=too_horror，不会被写成正向 style_keywords；“更温暖 / 灯光 / 休息区 / 风格统一”分别进入 mood / lighting / placement_rules
   - 工具结果通过 ToolCallGraphExecutor 执行、RuntimeGuard 授权、ToolResult / StatePatch schema 校验；不接真实引擎、不修改 actor、不生成报告
   - 新增 test_phase3_scene_constraints_tool_extracts_negative_and_style_constraints，验证负向约束、风格约束、灯光约束、休息区与风格一致性约束能进入 RuntimeState
   - 这一步把“SceneDesignContract / 长周期场景记忆所需的约束事实”先落到 RuntimeState 的结构化事实层，为后续 Planner / Builder Agent 替换规则提炼留出稳定 ToolCall 合约

30. Phase 3 空间范围与区域拆分已开始工具化：
   - AgentRuntime ToolRegistry 新增 room.estimate_bounds 与 zone.decompose 两个只读 planning 工具
   - room.estimate_bounds 根据场景类型、候选物体数量和大件物体预算生成 room_bounds_estimate 事实；室内写 bounds_type=room_box，室外 / 森林 / 草地 / 天空类写 bounds_type=terrain_area
   - zone.decompose 根据 room / terrain bounds 与场景语义生成 zone_decomposition 事实；藏宝室会拆出 entry、treasure_focus、side_storage、walkable_path，室外集市 / 森林营地会拆出入口、主路、主体区、环境背景等功能区
   - 两个工具均写入 custom_scene_facts，经 ToolCallGraphExecutor、RuntimeGuard、ToolResult / StatePatch schema 校验；不创建 room_box、不导入 terrain、不写真实 actor
   - 新增 test_phase3_room_bounds_and_zone_decompose_tools_create_structural_facts 与 test_phase3_room_bounds_tool_keeps_outdoor_substrate_as_terrain_area，验证藏宝室一定产生 room_box 预算，森林营地保持 terrain_area 而不是误生成 room_box
   - 这一步把“室内 room_box 兜底 / 室外 substrate 派生 / 区域规划”先收敛为 RuntimeState 结构事实，为后续 Builder Agent 和真实 environment import 工具接管旧空间框架逻辑铺路

31. Phase 3 资源路由与摆放输入准备已开始工具化：
   - AgentRuntime ToolRegistry 新增 asset.route_item 与 placement.prepare_items 两个只读工具
   - asset.route_item 从候选项中过滤天空、草地等环境 / substrate 项，只把帐篷、小木桌、藏宝箱等模型物体写入 asset_request_plans
   - placement.prepare_items 复用现有 build_placement_proposals，把模型物体转换为低风险 placement_proposals；它只生成摆放草案，不导入模型、不移动 actor
   - 两个工具均通过 ToolCallGraphExecutor、RuntimeGuard、ToolResult / StatePatch schema 校验；asset.route_item 属于 asset 类工具，placement.prepare_items 属于 geometry 类工具，但都 requires_write=False
   - 新增 test_phase3_asset_and_placement_tools_prepare_only_model_items，验证森林营地中的天空 / 草地不会进入资源请求和摆放草案，帐篷 / 小木桌会进入后续资源与摆放链路
   - 这一步把“对象到资源请求”和“对象到摆放草案”的准备阶段从旧主控中拆出，为后续 asset provider / actor import 工具接管真实执行铺路

32. Phase 3 扩展规划工具图已接入真实 ScenePlan 创建链路：
   - AgentRuntime._extract_scene_plan_fields_via_tool_graph 不再只跑 runtime.plan.extract / runtime.elements.classify，而是在 ScenePlan 创建前统一编排 scene.extract_objects、scene.classify_type、scene.extract_constraints、room.estimate_bounds、zone.decompose、scene.extract_environment、asset.route_item、placement.prepare_items，并保留 runtime.elements.classify 作为过渡兼容分类节点
   - scene.extract_objects 作为根节点写入 plan_extractions；asset.route_item、placement.prepare_items、runtime.elements.classify 通过 consumes_state 从 plan_extractions 读取同一个计划级提炼结果，避免各节点重复猜测候选物体
   - 本轮已验证该 ToolCallGraph 会在 ScenePlan 持久化后、ScenePlan 创建报告前写入 custom_scene_facts、environment_substrate_facts、asset_request_plans、placement_proposals 和 model_item_lists
   - 新增 test_phase3_scene_plan_creation_runs_extended_planning_tool_graph，验证藏宝室计划创建时能生成 scene_type / constraints / bounds / zones 结构事实，asset 与 placement 草案包含藏宝箱，且执行图节点数覆盖 Phase 3 扩展规划工具
   - 同步更新 Runtime / LANChat guard 测试中的 planning graph 判定：这些 requires_write=False 的 scene / asset / placement 准备图属于 Agent-native 规划证据，不属于越权执行图；真正写引擎 actor 的工具仍会被 guard 测试识别

33. 批次执行 ToolCallGraph 的旧提炼根节点已替换为 scene.extract_objects：
   - AgentRuntime._build_mock_graph 不再以 runtime.plan.extract 作为批次执行图的提炼根节点，改为 runtime.scene.snapshot -> scene.extract_objects -> runtime.elements.classify
   - scene.extract_objects 在批次执行图中写 batch 级 plan_extractions，避免覆盖 ScenePlan 创建阶段的 plan 级提炼事实；后续 runtime.elements.classify 仍以 batch.requested_items 为权威批次输入
   - 资源、substrate、environment、image、model、placement、geometry review、actor import、VLM checkpoint 的后续依赖链保持不变，仍通过 ToolCallGraphExecutor、RuntimeGuard、ToolResult / StatePatch schema 校验
   - 更新 test_runtime_graph_plans_assets_and_placements_before_mock_import 与 consumes 相关测试断言，确认 snapshot 先于 scene.extract_objects，后续 asset/image/model/placement/import/review 顺序不回退
   - 这一步继续收缩 runtime.plan.extract 的使用面，让批次执行链路也开始使用 Phase 3 scene.* 工具作为事实提炼入口，为 Phase 4 batch/import/review 工具化铺路

34. Phase 4 批次物体优先级已拆成 batch.prioritize_items ToolCall：
   - AgentRuntime ToolRegistry 新增 batch.prioritize_items 只读 planning 工具，用于将 ScenePlan 的 concrete_object_items 转换为稳定 ordered_items 与 priority rows
   - batch.prioritize_items 写入 custom_batch_facts 的 `{plan_id}:item_priorities`，不创建 BatchPlan、不导入模型、不修改 actor，也不接触真实引擎
   - plan_batches 与 enqueue_planned_batches 在切分 BatchPlan 前先执行 batch.prioritize_items ToolCallGraph；若工具失败则安全回退原始顺序，不阻断主链路
   - 现有 batch_plans 仍由 runtime.batch.plan_record 持久化，但 requested_items 的顺序已来自 RuntimeState 中的 batch priority fact，推进“批次事实源从函数局部变量迁移到 RuntimeState”
   - 新增 / 强化 test_runtime_can_plan_multiple_batches_as_state_facts 与 legacy model provider 顺序测试，验证批次 flattened requested_items 与 custom_batch_facts ordered_items 一致，provider 调用顺序也遵循 batch priority fact
   - 高风险物体如天使雕像 / 动物会被排到核心批次之后、普通支撑物之前，保持 VLM high_risk_object_review 的中间批语义

35. Phase 4 生成中介入合并已拆成 batch.merge_intervention ToolCall：
   - AgentRuntime ToolRegistry 新增 batch.merge_intervention 只读 planning 工具，用于将 pending intervention candidate patches 与 base_items 合并为 merged_items
   - batch.merge_intervention 写入 custom_batch_facts 的 `{plan_id}:merged_interventions`，不创建 BatchPlan、不入队、不导入模型、不修改 actor，也不触碰真实引擎
   - enqueue_pending_intervention_batch 在筛出可吸收 intervention 后，先执行 batch.merge_intervention ToolCallGraph，再使用 RuntimeState merge fact 生成下一批 requested_items；若工具失败则回退旧的 _merge_items 路径
   - merge fact 中不暴露 `patch_id` 字段名，避免用户报告路径泄漏内部补丁结构；内部 batch 仍保留 absorbed_intervention_ids 供回放与原子写入使用
   - 强化 test_enqueue_pending_intervention_batch_adds_next_runtime_batch，验证 pending intervention 追加批包含 batch.merge_intervention graph、custom_batch_facts merge fact、operation_log 事件，并保持原 enqueue 持久化原子性

36. Phase 4 批次终态标记已拆成 batch.mark_completed / batch.mark_failed / batch.mark_cancelled ToolCall：
   - AgentRuntime ToolRegistry 新增 batch.mark_completed、batch.mark_failed 与 batch.mark_cancelled 三个窄写工具，只负责把已有 BatchPlan 的 terminal status 写回 RuntimeState
   - _finalize_batch_after_drained_graph 不再直接修改 completed / failed / cancelled 状态后调用通用 batch plan 持久化；完成、失败或取消图会先执行对应 batch.mark_* ToolCallGraph，再由 StatePatch 更新 batch_plans
   - 本轮只拆取消后的终态写回，不改变 runtime command / pause / cancel 的入口语义，也不触碰 C++ 或真实调度取消逻辑
   - 工具失败会抛出并阻止 batch_execution_completed 用户事件，保持现有“终态状态写入失败不伪装完成”的门禁语义
   - 强化 drain_tool_graph_queue 与 cancelled finalize 测试，验证成功批次产生 batch.mark_completed graph，失败批次产生 batch.mark_failed graph，取消批次产生 batch.mark_cancelled graph，并记录 batch_terminal_status_state_persisted

37. Phase 4 批次创建草案已拆成 batch.create ToolCall：
   - AgentRuntime ToolRegistry 新增 batch.create 只读 planning 工具，用于把 ordered_items、max_items_per_batch 与 absorbed_intervention_ids 转换为 batch draft rows
   - batch.create 只写入 custom_batch_facts 的 `{plan_id}:created_batches`，不直接创建正式 batch_plans、不入队、不导入资源、不修改 actor，也不触碰真实引擎
   - plan_batches 与 enqueue_planned_batches 在最终持久化 batch_plans / tool_graph_queue 前，先执行 batch.create ToolCallGraph，再从 RuntimeState 的 created_batches fact 重建 BatchPlan dataclass 并走 BatchPlanValidator
   - 现有 runtime.batch.plan_record 与 runtime.scene_plan.planned_batches.enqueue 仍负责最终状态写入，因此最终批次状态失败时不会污染内存 mirror 或误吸收 intervention
   - 强化 test_runtime_can_plan_multiple_batches_as_state_facts 与 test_enqueue_planned_batches_only_queues_until_worker_drains，验证 custom_batch_facts created_batches、batch.create graph、后续正式 batch_plans / queue 状态一致

38. Phase 4 导入前 actor import plan 已拆成只读 ToolCall：
   - AgentRuntime ToolRegistry 新增 runtime.actor.plan_import_batch，只生成导入前审计计划，写入 custom_import_facts，不导入 actor、不写引擎、不修改真实场景
   - 批次执行图中 runtime.actor.plan_import_batch 位于 geometry review / environment dependency 之后、runtime.actor.import_batch 之前；真正写引擎的 runtime.actor.import_batch 仍是 import 类 requires_write 工具
   - runtime.actor.import_batch 现在显式消费 actor_import_plan（来自 custom_import_facts 的 batch scope），让“准备导入什么、哪些资源已 ready、摆放草案是什么”在写入前可审计
   - import plan 只保留 actor_name、ready_count、position / rotation / scale、zone_hint 等安全字段，不写 provider、model_path、URL、raw prompt 或私有路径
   - 强化 test_runtime_graph_plans_assets_and_placements_before_mock_import、ToolRegistry manifest 与 graph consumes/dependencies 测试，验证 import plan 顺序、custom_import_facts、manifest 分类和 actor import consume 合约

39. Phase 4 批次审查汇总已拆成 review.summarize_batch ToolCall：
   - AgentRuntime ToolRegistry 新增 runtime.review.summarize_batch，在 VLM checkpoint 与 actor import 之后生成批次级 review summary fact，写入 custom_review_summary_facts
   - 该工具只汇总 geometry review、VLM checkpoint、actor import plan 与 Runtime actors 的安全计数字段，不执行修复、不移动 actor、不写引擎
   - 批次执行图中 runtime.review.summarize_batch 依赖 runtime.review.vlm_checkpoint、runtime.geometry.review 与 runtime.actor.import_batch，继续把 report 前的隐式聚合拆成可审计 ToolCall
   - status_summary / generate_report 的 review_summary 会读取 custom_review_summary_facts，并以 latest_batch_summaries / batch_summary_count 暴露批次审查事实；同一 fact 的 batch_id 与 plan_id:batch_id 双 key 会去重
   - 强化 test_runtime_graph_plans_assets_and_placements_before_mock_import、ToolRegistry manifest 与 graph consumes/dependencies 测试，验证 review summary 顺序、custom_review_summary_facts、manifest 分类和报告读取口径

40. Phase 4 审查调整建议已拆成 review.generate_adjustment_proposal ToolCall：
   - AgentRuntime ToolRegistry 新增 runtime.review.generate_adjustment_proposal，在 review.summarize_batch 之后读取 geometry review、batch review summary 与 VLM advisory proposal
   - 该工具只把安全的 geometry issue 转换成低风险 layout_adjustment_proposals，不执行 actor move、不确认调整、不写真实引擎
   - 批次执行图中 runtime.review.generate_adjustment_proposal 依赖 runtime.review.summarize_batch、runtime.geometry.review 与 runtime.review.vlm_checkpoint，使“审查后是否需要调整”成为可回放 ToolCall，而不是报告阶段临时推断
   - 无可执行低风险 delta 时，该工具返回 not_needed payload，不制造空 proposal；有 floating / out_of_bounds 等低风险问题时生成等待房主确认的 proposal
   - 强化 review.generate_adjustment_proposal manifest、graph consumes/dependencies、direct ToolCallGraph 行为测试，并调整 completed batch 自动 proposal 测试，确认该 proposal 来源于 review ToolCall 而不是完成态用户入口事件

41. Phase 5 Runtime 队列选择已拆成 queue.select_next_graph ToolCall：
   - AgentRuntime ToolRegistry 新增 runtime.queue.select_next_graph，用于在 drain_next_tool_graph 真正出队执行前选择下一条 queued ToolCallGraph
   - 该工具读取 tool_graph_queue，写入 custom_queue_facts，记录 selected_graph_ref、batch_id、queued_count 与 status；不执行目标 graph、不修改 batch、不写引擎
   - drain_next_tool_graph 在正常可执行队列路径中先执行 queue.select_next_graph ToolCallGraph，再按 custom_queue_facts 里的 selected_graph_ref 执行业务 ToolCallGraph
   - paused / cancelled 计划下的队首 graph 仍保留原安全路径，直接进入 _drain_queued_tool_graph 的 blocked 处理，确保图状态持久化失败不会被 queue selection 控制面图吞掉
   - custom_queue_facts 不暴露 graph_id 字段名，避免用户报告或 Runtime fact 泄漏内部执行图标识；测试覆盖 manifest、queue fact 与 paused drain 安全回归

42. Phase 5 Runtime 队列状态写回已拆成 queue.mark_graph_status ToolCall：
   - AgentRuntime ToolRegistry 新增 runtime.queue.mark_graph_status，用于持久化 queued ToolCallGraph 的 running / completed / failed / paused / cancelled 等状态转换
   - _mark_tool_graph_queue_item 保留为内部唯一调用点，但内部改为执行 confirmed 的 runtime-queue-control ToolCallGraph，不再手写 tool_graph_queue StatePatch
   - 该工具读取 tool_graph_queue，写回 tool_graph_queue，保留 started_at / completed_at / updated_at 等队列生命周期字段；不执行目标 graph、不修改 batch、不写引擎
   - 原有 tool_graph_queue_state_persisted / tool_graph_queue_update_failed OperationLog 语义保留；状态写回失败仍会抛错，避免队列图未落盘却继续发完成事件
   - 测试覆盖 manifest consumes/produces 契约、正常 drain 路径中 runtime.queue.mark_graph_status 的 ToolCall 执行，以及 queue state failure 的旧安全语义

43. Phase 5 批次开始状态已拆成 batch.mark_started ToolCall：
   - AgentRuntime ToolRegistry 新增 batch.mark_started，用于把 Runtime BatchPlan 从 planned 切到 executing
   - _mark_batch_started_by_tool_graph 不再先改内存 batch 再走通用 plan_record，而是执行 confirmed 的 batch.mark_started ToolCallGraph，再从 RuntimeState 回读 batch mirror
   - batch.mark_started 只写 batch_plans，不执行目标 graph、不请求资源、不导入 actor、不写真实引擎；batch_execution_started RuntimeEvent 仍在状态落盘成功后发出
   - 状态写入失败会产生 batch_started_status_state_persist_failed 并抛错，不会继续发 batch_started / graph started 这类误导用户的完成信号
   - 测试覆盖 manifest write/user-visible failure 契约，以及 drain 路径中 batch.mark_started ToolCall 的执行

44. Phase 5 直接 ToolCallGraph 入队路径已拆成 queue.enqueue_graph ToolCall：
   - AgentRuntime ToolRegistry 新增 runtime.queue.enqueue_graph，用于把已清洗的 ToolCallGraph fact 与 queue item 原子写入 tool_graphs / tool_graph_queue
   - _enqueue_tool_graph 不再直接 apply_patch 写 tool_graphs + tool_graph_queue，而是执行 confirmed 的 runtime.queue.enqueue_graph ToolCallGraph，再保留原 tool_graph_queue_state_persisted / failed 事件语义
   - 该工具只接收 ToolCallGraphValidator.safe_graph_fact(graph) 和 queue_item，不接收 raw graph / raw args / provider / prompt / model_path；失败时仍抛错并阻止 tool_graph_queued / batch_execution_queued 等业务事件
   - runtime.scene_plan.enqueue 这类“确认方案时原子写 plan + batch + queue”的工具路径暂时保留，用于保障确认入队的原子性；本条覆盖 worker / 内部直接 _enqueue_tool_graph 路径
   - 测试覆盖 manifest write/user-visible failure 契约、直接 _enqueue_tool_graph 路径中 runtime.queue.enqueue_graph 的 ToolCall 执行，以及 enqueue/queue 原子性回归

45. Phase 5 目标执行图状态记录已拆成 queue.record_graph_state ToolCall：
   - AgentRuntime ToolRegistry 新增 runtime.queue.record_graph_state，用于把已清洗的目标 ToolCallGraph fact 写入 tool_graphs
   - _persist_tool_graph_state 不再直接 apply_patch 写 tool_graphs，而是执行 confirmed 的 runtime.queue.record_graph_state ToolCallGraph，再保留原 tool_graph_state_recorded / failed 事件语义
   - 该工具只记录“目标业务图”的状态快照，尤其覆盖 paused / cancelled / blocked drain 路径；ToolCallGraphExecutor 内部用于记录自身执行过程的 _persist_graph 仍保留为执行器内部机制，避免递归工具化
   - 工具参数只接收 ToolCallGraphValidator.safe_graph_fact(graph) 与 target_graph_ref，不接收 raw graph / raw args / provider / prompt / model_path；失败时仍抛错并阻止后续 blocked / completed 用户事件
   - 测试覆盖 manifest write/user-visible failure 契约、paused drain 路径中 runtime.queue.record_graph_state 的 ToolCall 执行，以及 queue state failure 回归

46. Phase 5 外部 RuntimeEvent 写入已拆成 runtime.event.emit ToolCall：
   - AgentRuntime ToolRegistry 新增 runtime.event.emit，用于把已通过 RuntimeEventValidator 清洗的用户可见事件写入 runtime_events
   - AgentRuntime.emit_runtime_event 不再直接 apply_patch 写 runtime_events，而是执行 confirmed 的 runtime.event.emit ToolCallGraph，再保留原 runtime_event_emitted / runtime_event_emit_failed 事件语义
   - runtime.event.emit 被加入生命周期披露抑制列表，避免“发进度事件时又生成进度事件”的递归噪声；ToolCallGraphExecutor 内部 tool_call_started / tool_result_message / blocked / stopped 事件仍保留为执行器内部机制，暂不递归工具化
   - 工具参数只接收 event_row 与 room_id，event_row 必须通过 RuntimeEventValidator.validate_row，不接收 raw payload / provider / prompt / URL / API key / tool args
   - 测试覆盖 manifest write/user-visible failure 契约、RuntimeEvent 安全 payload 持久化、持久化失败显式返回，以及 runtime_events 只读查询不会创建 ScenePlan

47. Phase 8 旧 MasterAgent 整体 compose 直入口已补默认阻断测试：
   - `agent_adapter.MasterAgent._handle_scene_compose()` 已有 AgentRuntime migration guard，默认 `ALLOW_LEGACY_MAIN_WORKFLOW=0` / `OLD_WORKFLOW_DIRECT_ENTRY_DISABLED=1` 时返回 Runtime 主控提示，不再实例化 `SceneComposer` 进入旧主控链路
   - 新增 `test_master_agent_direct_scene_compose_blocks_default_legacy_main_workflow`，把 RoleAgent / MasterAgent 直连 `SceneComposer.compose()` 的默认禁用行为纳入 `test_lanchat_runtime_guard.py`
   - 这一步不改变运行时主链路，只把“普通 Agent 入口不得重新暴露旧 workflow 主控”的不变量固化为测试，防止后续改动把 `_handle_scene_compose` 重新接回旧 compose

48. Phase 8 旧 MasterAgent 显式文件导入直入口已补默认阻断测试：
   - `agent_adapter.MasterAgent.__call__()` 中显式模型文件路径会优先进入 `_handle_direct_import()`；该路径已有 AgentRuntime migration guard，默认不允许绕过 Runtime 直接调用旧 `import_model` 工具写引擎
   - 新增 `test_master_agent_direct_file_import_blocks_default_legacy_main_workflow`，把“文件路径导入也必须先进入 Runtime / 方案确认链路”的约束纳入 `test_lanchat_runtime_guard.py`
   - 这一步不删除直接导入能力，只防止普通 Agent 入口在默认 Runtime 主控模式下绕过 ToolCallGraph / RuntimeGuard 直接写场景

49. Phase 8 直接 engine-write 旧入口已纳入总门禁：
   - `verify_ultimate_plan.py` 新增 static direct engine-write entry gate，扫描 `agent_adapter.py` 中 `_handle_direct_import()` 与 `_handle_edit()` 是否在触达旧 `import_model` / 场景 actor 读取写入链路前经过 AgentRuntime migration guard
   - 该门禁要求 guard 前缀包含 `_legacy_main_workflow_allowed()` 与 `AGENT_RUNTIME_REQUIRED_MESSAGE`，避免后续把显式文件导入、快速编辑或菜包 agentic 工具循环重新暴露为默认用户写入口
   - 这一步把“业务 Agent 不得绕过 ToolCallGraph / RuntimeGuard 直接写场景”的约束从单元测试提升为 `verify_ultimate_plan.py` 总门禁

50. Phase 8 旧 ProgressiveWorkflow 主控直达入口已纳入总门禁：
   - `verify_ultimate_plan.py` 新增 static direct ProgressiveWorkflow entry gate，扫描 services / `cai_extensions/agent` / `main.py` 中的 `run_progressive_workflow` 与 `progressive_compose(` 直连调用
   - 当前只允许旧能力本体 `scene_composer_progressive.py` / `scene_session.py` 和过渡期 legacy `scene_composer.py` 内部调用存在；普通用户入口、LANChat worker、Host executor、AgentRuntime 包不得新增直连 progressive 主控
   - 门禁会跳过 AgentRuntime 内部“禁用旧主控 token”清单这类字符串声明，避免把防回潮规则本身误判为旧入口
   - 这一步把“不能把 `run_progressive_workflow()` 包成新的大工具或重新暴露给普通入口”的约束固化为总门禁，为后续继续拆 batch / import / review 工具留出安全边界

51. RuntimeState.apply_patch 直写边界已纳入总门禁：
   - `verify_ultimate_plan.py` 新增 static RuntimeState apply_patch boundary gate，用 AST 扫描 `agent_runtime/core.py` 中所有 `apply_patch()` 调用
   - 当前只允许 `ToolCallGraphExecutor.execute()` 的 ToolResult StatePatch 合并、执行器生命周期 RuntimeEvent 写入、以及 `_persist_graph()` 内部图状态持久化保留直接写入；这些属于执行器内部机制，暂不递归工具化
   - 任何 AgentRuntime 外层业务方法、入口路由、报告生成、队列控制或旧 workflow adapter 新增直接 `RuntimeState.apply_patch` 都会触发总门禁失败，必须改为 ToolCallGraph + ToolResult / StatePatch 路径
   - 这一步把“ToolResult 不直接改状态，只有 RuntimeState.apply_patch 能合并；业务状态写入必须经工具图”的边界固化为可重复验证的非 native 门禁

52. Phase 5/Report OperationLog replay 汇总已拆成 runtime.report.operation_replay_summary ToolCall：
   - AgentRuntime ToolRegistry 新增 `runtime.report.operation_replay_summary`，在 `generate_report()` 组装用户报告前，把 OperationLog replay summary 写入 `custom_report_facts`
   - `generate_report()` 不再直接调用 `_operation_replay_summary_for_report()` 作为最终报告事实来源，而是先执行单节点 ToolCallGraph，再从 RuntimeState 读取已记录的 report fact
   - 该工具只读取 OperationLog 与 RuntimeState、写入安全的 `custom_report_facts`，不触碰引擎、不修改 actor、不调用旧 workflow，也不暴露 `tool_call_id` / `patch_id` / provider / prompt / path
   - 工具失败会记录 `runtime_report_operation_replay_summary_failed` 并阻断 `user_report_generated` / `report_ready`，避免报告在缺失 RuntimeState report fact 时伪装完成；成功时记录 `runtime_report_operation_replay_summary_recorded`
   - 强化 `test_generate_report_contains_safe_operation_replay_summary`、`test_generate_report_replay_summary_failure_blocks_user_report` 与 ToolRegistry manifest 测试，验证报告 replay summary 已落入 RuntimeState fact 且新工具具备 write/user-visible-failure/produces_state 契约

53. Phase 5/Report ToolRegistry manifest 查询已拆成 runtime.tool_manifest.snapshot ToolCall：
   - AgentRuntime ToolRegistry 新增 `runtime.tool_manifest.snapshot`，在 `tool_manifest()` 返回工具能力清单前，把 ToolRegistry manifest / capability summary 写入 `custom_report_facts`
   - `tool_manifest()` 不再直接从 registry 读完即返回，而是先执行单节点 ToolCallGraph，再从 RuntimeState 的 `tool_manifest:*` fact 读取 summary 与 tools
   - 该工具只记录安全 manifest 快照，不创建 ScenePlan、不入队、不写引擎、不触碰旧 workflow；manifest fact 不包含 handler、provider、prompt、path、URL 或 raw payload
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已扩展检查 `tool_manifest()` 必须走 `runtime.tool_manifest.snapshot`，禁止回退为直接 registry 读取
   - 强化 ToolRegistry manifest 测试，验证 `tool_manifest:all` 已落入 RuntimeState fact 且新工具具备 write/user-visible-failure/produces_state 契约

54. Phase 5/Status Runtime 状态查询已拆成 runtime.status_summary.snapshot ToolCall：
   - AgentRuntime ToolRegistry 新增 `runtime.status_summary.snapshot`，在 `status_summary()` 返回用户/GM 可见状态前，把已清洗 Runtime 状态摘要写入 `custom_report_facts`
   - `status_summary()` 仍保持不创建 ScenePlan、不写用户报告、不发 `report_ready` 的查询语义；但返回值必须先经单节点 ToolCallGraph 落入 RuntimeState fact，再从 fact 读回
   - `status_summary()` 的工具能力摘要不再直接读 `registry.capability_summary()`，而是复用 `runtime.tool_manifest.snapshot` 的安全 summary，并过滤掉内部工具名列表后披露
   - 工具失败会记录 `runtime_status_summary_snapshot_failed` 并阻断状态返回，避免缺失 RuntimeState status fact 时伪装查询成功；成功时记录 `runtime_status_summary_snapshot_recorded`
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已扩展检查 `status_summary()` 必须走 `runtime.status_summary.snapshot`，并禁止直接读取 registry capability summary
   - 强化 status summary / ToolRegistry manifest 测试，验证内部 `runtime-status-summary` 房间中的 `*:runtime_status_summary` fact 已落入 RuntimeState 且新工具具备 write/user-visible-failure/produces_state 契约

55. Phase 5/Status Provider readiness 状态查询已拆成 runtime.resource_status.snapshot ToolCall：
   - AgentRuntime ToolRegistry 新增 `runtime.resource_status.snapshot`，在 `provider_status()` 返回资源通道状态前，把已清洗 provider readiness / engine write / message delivery 摘要写入 `custom_report_facts`
   - `provider_status()` 保留原有 `runtime.provider_readiness.publish` 逻辑，继续把 provider readiness 发布到业务房间 RuntimeState；新增 provider status 快照写入内部 `runtime-provider-status` 房间，避免污染业务房间 `tool_graphs` 和用户可见进度
   - 外部 SeedPlan 找不到 runtime plan 的分支也必须写入 provider status fact，避免“无 runtime plan”状态绕过 RuntimeState 事实源
   - 工具失败会记录 `runtime_provider_status_snapshot_failed` 并阻断状态返回；成功时记录 `runtime_provider_status_snapshot_recorded`
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已扩展检查 `provider_status()` 必须走 `runtime.resource_status.snapshot`
   - 强化 provider status / ToolRegistry manifest 测试，验证正常查询、外部 plan 查询、未知外部 plan 查询均已落入内部 `runtime-provider-status` fact，且不会把 snapshot ToolCallGraph 写入业务房间

56. Phase 5/Replay OperationLog 复盘查询已拆成 runtime.operation_replay.snapshot ToolCall：
   - AgentRuntime ToolRegistry 新增 `runtime.operation_replay.snapshot`，在 `operation_replay()` 返回诊断/复盘结果前，把已清洗 replay 结果写入 `custom_report_facts`
   - `operation_replay()` 保留 `runtime_operation_replay_requested` 与 `runtime_operation_replay_queried` 审计事件，但最终返回值必须先经内部 `runtime-operation-replay` 房间的 RuntimeState fact 读回
   - replay snapshot 不写用户报告、不发 `report_ready`、不污染业务房间 `tool_graphs`，只作为诊断事实源固化
   - 工具失败会记录 `runtime_operation_replay_snapshot_failed` 并阻断 replay 返回；成功时记录 `runtime_operation_replay_snapshot_recorded`
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已扩展检查 `operation_replay()` 必须走 `runtime.operation_replay.snapshot`
   - 强化 operation replay / ToolRegistry manifest 测试，验证 `runtime-operation-replay` 内部 fact 已落入 RuntimeState 且新工具具备 write/user-visible-failure/produces_state 契约

57. Phase 5/GM Runtime 上下文总结已拆成 runtime.gm_summary.snapshot ToolCall：
   - AgentRuntime ToolRegistry 新增 `runtime.gm_summary.snapshot`，在 `gm_summary()` 返回 GM 可见上下文摘要前，把已清洗摘要写入 `custom_report_facts`
   - `gm_summary()` 仍先读取 `status_summary()`，继承 RuntimeState / OperationLog 状态事实源；但最终返回值必须先经内部 `runtime-gm-summary` 房间的 RuntimeState fact 读回
   - GM summary snapshot 不创建 ScenePlan、不写用户报告、不发 `report_ready`、不污染业务房间 `tool_graphs`，只固化 GM/Planner 可用的上下文摘要事实
   - 工具失败会记录 `runtime_gm_summary_snapshot_failed` 并让 `runtime_gm_summary` action 返回 unavailable summary；成功时记录 `runtime_gm_summary_snapshot_recorded` 和 `runtime_gm_summary_exported`
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已扩展检查 `gm_summary()` 必须走 `runtime.gm_summary.snapshot`
   - 强化 GM summary / ToolRegistry manifest 测试，验证 `runtime-gm-summary` 内部 fact 已落入 RuntimeState 且新工具具备 write/user-visible-failure/produces_state 契约

58. Phase 5/UI RuntimeEvent 查询已拆成 runtime.events.snapshot ToolCall：
   - AgentRuntime ToolRegistry 新增 `runtime.events.snapshot`，在 `runtime_events` / `user_visible_events` action 返回用户可见事件列表前，把已清洗事件列表写入 `custom_report_facts`
   - `user_visible_events()` 继续作为内部只读 helper；外部 action 必须先经内部 `runtime-events-snapshot` 房间的 RuntimeState fact 读回，避免 UI 事件披露只存在于函数返回值里
   - Runtime events snapshot 不创建 ScenePlan、不写用户报告、不发 `report_ready`、不污染业务房间 `tool_graphs`；只固化“用户这一刻可见哪些 RuntimeEvent”的安全事实
   - 工具失败会记录 `runtime_events_snapshot_failed`，并让 `runtime_events` action 返回空事件与 `recorded=False`，不返回未落 RuntimeState fact 的事件列表；成功时记录 `runtime_events_snapshot_recorded`
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已扩展检查 `handle_message()` 的 runtime_events action 必须走 `runtime.events.snapshot`
   - 强化 runtime_events action / ToolRegistry manifest 测试，验证 `runtime-events-snapshot` 内部 fact 已落入 RuntimeState，且不泄露 provider、tool_name、URL、prompt、event_id 或内部 tool graph 信息

59. Phase 5/Sync 多人同步状态查询已拆成 runtime.sync_status.snapshot ToolCall：
   - AgentRuntime ToolRegistry 新增 `runtime.sync_status.snapshot`，在 `sync_status` / `runtime_sync_status` / `sync_summary` action 返回多人同步健康度前，把同步状态、同步 replay 摘要、消息投递摘要和最新可见 RuntimeEvent 写入 `custom_report_facts`
   - `sync_status` action 仍从 `status_summary()` 与 `operation_replay()` 读取 RuntimeState / OperationLog 事实源；但最终返回值必须先经内部 `runtime-sync-status` 房间的 RuntimeState fact 读回
   - Sync status snapshot 不创建 ScenePlan、不写用户报告、不发 `report_ready`、不污染业务房间 `tool_graphs`；只固化“多人 actor / asset / peer / delivery 同步状态查询”的安全事实
   - 工具失败会记录 `runtime_sync_status_snapshot_failed` 与 `runtime_sync_status_export_failed`，并让 sync_status action 返回空同步状态，不返回未落 RuntimeState fact 的同步摘要；成功时记录 `runtime_sync_status_snapshot_recorded` 和 `runtime_sync_status_exported`
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已扩展检查 `handle_message()` 的 sync_status action 必须走 `runtime.sync_status.snapshot`
   - 强化 sync_status action / ToolRegistry manifest 测试，验证 `runtime-sync-status` 内部 fact 已落入 RuntimeState，且不泄露 message_id、correlation_id、source_user_id、provider、URL 或 prompt

60. Phase 5/Sync 未映射 external SeedPlan 的状态查询也已收口到 runtime.sync_status.snapshot：
   - `sync_status` action 携带 `external_plan_id` 但找不到对应 Runtime plan 时，不再直接返回“no mapped Runtime plan”，而是先把空同步状态、安全提示和失败原因写入内部 `runtime-sync-status` 房间的 `custom_report_facts`
   - 该分支继续不回退 active plan，避免查询一个失效/旧 SeedPlan 时误读当前活跃计划的 actor / asset / peer 同步状态
   - snapshot 失败时记录 `runtime_sync_status_snapshot_failed` 与 `runtime_sync_status_export_failed`，并返回 RuntimeState 持久化失败提示，不返回未落 fact 的状态
   - 强化 `test_sync_status_action_rejects_unknown_external_plan_without_active_fallback`，验证未知 external plan 的 sync status 结果也来自 `runtime-sync-status` fact，且不会泄露已有计划 actor

61. Phase 5/Scene Snapshot 用户可见状态返回已移除 ToolCallGraph 节点细节：
   - `refresh_scene_snapshot()` 内部仍通过 `runtime.scene.snapshot` ToolCallGraph 读取真实/模拟引擎快照，并把 `engine_scene_snapshots`、`observed_actors`、`actors` 写入 RuntimeState
   - `handle_message(action=scene_snapshot_status)` 不再把内部 `graph.nodes`、tool args 或 tool_name 返回给用户可见 action 结果，只返回 `graph.status`、安全 `snapshot_summary` 与清洗后的 RuntimeEvent
   - 这一步保留内部调试方法的详细 graph 返回，避免影响 Runtime 内部测试和 provider adapter 验证；但聊天室 / action 查询路径不再暴露 ToolCallGraph 节点结构
   - 强化 scene snapshot status 测试，验证成功、失败、异常和 active scene name 分支均不返回 `graph.nodes`，同时 RuntimeState 中的 engine snapshot / observed actor 事实仍正确落盘

62. Phase 6/Layout Adjustment 用户可见 action 返回已移除 ToolCallGraph 节点细节：
   - `propose_layout_adjustment()` 与 `confirm_layout_adjustment()` 内部仍通过 `runtime.layout.adjust_propose` / `runtime.layout.apply` ToolCallGraph 写入 `layout_adjustment_proposals` 与低风险 actor transform 结果
   - `handle_message(action=layout_adjustment/final_adjustment_request/confirm_layout_adjustment)` 不再把内部 `graph.nodes`、tool args 或 tool_name 返回给聊天室 / action 调用方，只返回 `graph.status`、plan、proposal 和安全 message
   - 该切片保持内部 helper 的详细 graph / state 返回，继续服务 Runtime 内部测试、回放和执行器调试；只收窄用户可见入口的泄露面
   - 强化布局建议生成、确认成功、确认失败与异常分支测试，验证 action 返回不包含 `graph.nodes`，且 RuntimeState 中的 proposal / actor facts 仍正确落盘

63. Phase 6/Delete Advisory 用户可见执行返回已移除 ToolCallGraph 节点细节：
   - `execute_confirmed_delete_advisory()` 内部仍通过 `runtime.delete_advisory.apply` ToolCallGraph 执行已确认的低风险/中风险删除建议，并写入 actor deleted / sync lifecycle facts
   - `handle_message(action=execute_confirmed_delete_advisory)` 不再把内部 `graph.nodes`、tool args 或 tool_name 返回给调用方，只返回 `graph.status`、proposal、status summary 和安全 message
   - 保留内部 helper 的详细 graph 返回，继续服务 Runtime 执行器测试、tool_call_succeeded 追踪和回放诊断；普通聊天室 / action 路径只看安全状态摘要
   - 强化 confirmed delete advisory handle_message 测试，验证 action 返回不包含 `graph.nodes`，且 RuntimeState 中 actor 删除事实仍正确落盘

64. Phase 5/UI 未映射 external SeedPlan 的 RuntimeEvent 查询也已收口到 runtime.events.snapshot：
   - `runtime_events` / `user_visible_events` action 携带 `external_plan_id` 但找不到对应 Runtime plan 时，不再直接返回空事件列表，而是先把空事件 feed 写入内部 `runtime-events-snapshot` 房间的 `custom_report_facts`
   - 该分支继续不回退 active plan，避免查询一个失效/旧 SeedPlan 时误读当前活跃计划的 resource / tool / review 事件
   - snapshot 失败时记录 `runtime_events_snapshot_failed` 与失败版 `runtime_events_queried`，并返回 RuntimeState 持久化失败提示，不返回未落 fact 的事件列表
   - 强化 unknown external plan runtime events 测试，验证空事件结果来自 `runtime-events-snapshot` fact，且不会泄露已有计划事件

65. Phase 5/UI 未映射 external SeedPlan 的 OperationReplay 查询也已收口到 runtime.operation_replay.snapshot：
   - `operation_replay` action 携带 `external_plan_id` 但找不到对应 Runtime plan 时，不再直接拼一个未持久化的空 replay 返回，而是先通过 `runtime.operation_replay.snapshot` 写入内部 `runtime-operation-replay` 房间的 `custom_report_facts`
   - 该分支使用不会命中真实日志的 `__missing_runtime_plan__` 哨兵过滤，避免空 `plan_id` 查询误读当前 room 或 active plan 的 OperationLog
   - snapshot 失败时记录 `runtime_operation_replay_failed`，并返回 RuntimeState 持久化失败提示，不返回未落 fact 的复盘结果
   - 强化 missing external operation replay 测试，验证空 replay 来自 `runtime-operation-replay` fact，且不会泄露已有计划的 OperationLog 条目

66. Phase 8 旧 ProgressiveWorkflow 主控直达门禁已从“文件级放行”收紧到“行模式级放行”：
   - `verify_ultimate_plan.py` 的 static direct ProgressiveWorkflow entry gate 仍扫描 services / `cai_extensions/agent` / `main.py` 中的 `run_progressive_workflow` 与 `progressive_compose(` 直连调用
   - 过渡期允许文件不再整体豁免；`scene_composer.py` 只允许既有 `run_progressive_workflow` import / 调用，`scene_composer_progressive.py` 只允许 workflow 定义、内部 `session.progressive_compose(` 调用与 `__all__`，`scene_session.py` 只允许主循环说明和 `def progressive_compose(`
   - 后续如果在 allowed 文件里新增第二条绕过 AgentRuntime / ToolCallGraph 的 ProgressiveWorkflow 入口，非 native 总门禁会直接失败
   - 这一步继续收紧“旧 ProgressiveWorkflow 只能作为过渡内部能力存在，不得重新扩大为用户入口或新的大工具入口”的边界

67. Phase 8 旧 SceneComposer 主控直达门禁也已从“文件级放行”收紧到“行模式级放行”：
   - `verify_ultimate_plan.py` 的 static direct SceneComposer entry gate 仍扫描 services / `cai_extensions/agent` / `main.py` 中的 `SceneComposer(` 与 `composer.compose(` 直连调用
   - 过渡期允许文件不再整体豁免；`main.py` 只允许默认 composer factory，`agent_adapter.py` 只允许 legacy guard 包住的 `SceneComposer` / `compose` 调用，`generation_composer_adapter.py` 只允许 Scheduler 过渡 adapter 调用
   - 原有 Runtime guard token 检查继续保留：`agent_adapter.py` 必须包含 `_legacy_main_workflow_allowed` 与 `AGENT_RUNTIME_REQUIRED_MESSAGE`，`generation_composer_adapter.py` 必须包含 `can_call_legacy_main_workflow` 与 legacy disabled error
   - 后续即使在 allowed 文件里新增新的 `SceneComposer` 或 `compose()` 直达旧主控，也会被非 native 总门禁拦下
   - 这一步继续固化“用户入口只能进入 AgentRuntime，旧 SceneComposer 主控只能作为受控过渡 adapter 存在”的边界

68. Phase 8 旧 SceneComposer 主控直达门禁已进一步收紧为“调用点前缀必须有 Runtime guard”：
   - static direct SceneComposer entry gate 不再只检查 guard token 是否出现在整个文件中，而是对具体 `SceneComposer(` / `composer.compose(` 调用点回溯所在过渡函数前缀
   - `agent_adapter.py::_handle_scene_compose()` 中的 `SceneComposer` 创建与 `compose()` 调用前必须已经出现 `_legacy_main_workflow_allowed` 与 `AGENT_RUNTIME_REQUIRED_MESSAGE`
   - `generation_composer_adapter.py::compose()` 中的 `composer.compose()` 调用前必须已经出现 `can_call_legacy_main_workflow` 与 legacy disabled error
   - 这一步避免“文件顶部有 guard token，但新增调用点绕过 guard”的假安全，继续强化旧主控只能作为受控过渡 adapter 存在

69. Phase 8 旧 ProgressiveWorkflow 主控直达门禁已进一步收紧为“调用点必须位于预期过渡函数内”：
   - static direct ProgressiveWorkflow entry gate 不再只检查 allowed 文件和 allowed 行模式，还会校验关键调用点的函数作用域
   - `scene_composer.py` 中的 `run_progressive_workflow` import / 调用必须位于 `SceneComposer.compose()` 过渡路径内，不允许同文件新增第二个绕过 AgentRuntime 的 progressive 入口
   - `scene_composer_progressive.py` 中的 `session.progressive_compose()` 必须位于 `run_progressive_workflow()` 内，不允许把 `SceneSession.progressive_compose()` 扩散成新的主控入口
   - 这一步保持当前旧链路过渡能力可运行，但把“允许旧 ProgressiveWorkflow 存在”的边界从文件级进一步收紧到函数作用域级

70. Phase 8 旧 ProgressiveWorkflow 内部导入写入口已增加 EngineWriteGate 静态约束：
   - `verify_ultimate_plan.py` 的 ProgressiveWorkflow gate 现在要求 `run_progressive_workflow()` 作用域内必须取得 `get_engine_write_gate()`，并将同一个 `engine_gate` 传入 `incremental_import()`
   - 检查条件收窄到 `incremental_import()` 的参数片段，避免误把 `SceneSession(...)` 初始化里的同名参数当作导入收口证据
   - 这一步不改变现有 progressive 执行行为，只把“旧过渡链路里的真实导入也必须经 EngineWriteGate”固化为非 native 门禁
   - 后续若有人在 progressive 内新增绕过 `EngineWriteGate` 的导入路径，`verify_ultimate_plan.py` 会直接失败

71. Phase 8 旧 GenerationScheduler 直达入口已纳入非 native 静态门禁：
   - CodeGraph 核实当前真实 `GenerationScheduler.submit()` 调用仅位于 `InteractionCoordinator.execute_confirmed_plan()` 和 `InteractionCoordinator.execute_post_generation_add()` 两个旧过渡函数
   - `verify_ultimate_plan.py` 新增 static direct GenerationScheduler entry gate，扫描 services / `cai_extensions/agent` / `main.py` 中的 `GenerationScheduler(` 与 `_scheduler.submit(`
   - 过渡期只允许 `lanchat_agent_worker._get_generation_scheduler()` 在 `can_call_legacy_main_workflow()` guard 后创建 scheduler，并安装 Runtime audit / disclosure hooks
   - 过渡期只允许 `InteractionCoordinator` 的确认生成与完成后追加两个函数提交旧队列；其它服务、Agent、工具或 UI 路径新增直达 submit 会直接失败
   - 这一步继续把 `GenerationScheduler` 降级为受控过渡执行队列能力，避免它重新成为用户入口或业务状态事实源

72. Phase 8 LANChat confirmed host action 执行入口已纳入 Runtime approval 静态门禁：
   - CodeGraph 核实当前生产路径中 `LanChatHostActionExecutor.enqueue_and_process()` 只从 `lanchat_agent_worker._execute_confirmed_action()` 调用
   - `verify_ultimate_plan.py` 新增 static direct host action executor entry gate，扫描 services / `cai_extensions/agent` / `main.py` 中的 `_execute_confirmed_action(` 与 `enqueue_and_process(`
   - `lanchat_agent_worker._broadcast_confirmed_action()` 必须先调用 `_is_confirmed_action_payload_runtime_approved(payload)`，并在未批准时记录 `unapproved_confirmed_action_blocked` 后返回，才能进入 `_execute_confirmed_action(payload)`
   - `enqueue_and_process(payload)` 只能保留在 `_execute_confirmed_action()` 中，且该函数必须通过 `_get_host_action_executor()` 获取受控 executor，并在 finally 中继续触发 disclosure / scheduler 状态披露
   - 这一步把“GM/房主确认后的旧 host action 执行”固定为 Runtime-approved 过渡路径，避免未由 AgentRuntime/Coordinator 准备的 confirmed payload 重新绕回旧执行链

73. Phase 8 LANChat 主动确认生成到旧 Coordinator 执行的过渡入口已纳入 legacy-main guard 静态门禁：
   - CodeGraph 核实 `InteractionCoordinator.execute_confirmed_plan()` 除 coordinator 内部复用外，生产侧还有 `lanchat_agent_worker._start_active_coordinator_generation()` 一个旧过渡调用点
   - `verify_ultimate_plan.py` 的 static direct GenerationScheduler entry gate 已扩展扫描 `ref = coordinator.execute_confirmed_plan(plan.plan_id)`
   - 该调用必须位于 `_start_active_coordinator_generation()` 内，并且必须先检查 `if not self._agent_runtime_flags.can_call_legacy_main_workflow():`
   - legacy main workflow 禁用时，必须返回 `_execute_confirmed_plan_via_agent_runtime(...)`；只有 legacy main workflow 被显式允许时，才能继续进入 `coordinator.execute_confirmed_plan()`
   - 这一步继续压缩“聊天确认生成 -> SeedPlan -> GenerationScheduler”的旧直达窗口，确保默认方向是 AgentRuntime，而旧 Coordinator 执行只作为显式 legacy 过渡路径存在

74. Phase 8 HostActionExecutor 内部执行策略已纳入静态门禁：
   - CodeGraph 核实 `LanChatHostActionExecutor._execute_payload()` 是 confirmed host action 进入结构化 handler 或旧 Agent fallback 的关键分流点
   - `verify_ultimate_plan.py` 新增 static host action executor policy gate，校验 `__init__()` 默认 `allow_legacy_agent_fallback=False`，并保存 `structured_action_handler`
   - `_execute_payload()` 必须先识别 structured SeedPlan payload，再校验 action 是否属于受控集合；结构化入口不可用时直接拒绝，不能落到旧 Agent fallback
   - 只有非结构化 payload 且 `_allow_legacy_agent_fallback` 显式开启时，才允许调用 `_get_agent()` 进入旧 Agent 执行器
   - 受控 structured action 集合固定包含 `start_generation` / `execute_seed_plan` / `post_generation_add`，避免任意 plan-like payload 借结构化身份执行未知动作

75. Phase 8 旧 Quasar workflow 注册层 policy 安装顺序已纳入静态门禁：
   - CodeGraph 核实 `CabbageWorkflowPlugin.register()` 会注册旧 `WORKFLOWS` 与 `WORKFLOW_COMMANDS`，这些模块仍保留作为 legacy regression / internal debug baseline
   - `verify_ultimate_plan.py` 的 static workflow command exposure gate 现在会读取 `cai_extensions/register.py`，并精确截取 `CabbageWorkflowPlugin.register()` 作用域
   - 门禁要求先取得 workflow / workflow_command registry，再先后调用 `install_workflow_command_policy(command_registry)` 与 `install_workflow_function_policy(registry, command_registry)`，之后才允许遍历 `flow_modules`
   - 每个 command 必须先 `record_workflow_function_exposure(...)`，再执行 `should_register_workflow_command(command)`，最后才允许 `command_registry.register(...)`
   - 这一步保证旧 workflow 可以继续作为保守隐藏的 baseline 注册在底层 registry 中，但用户可见命令和 function_id 执行面必须先经过 Corona policy 过滤

76. Phase 8 AgentRuntime feature flag 与 legacy main workflow 默认边界已纳入静态门禁：
   - CodeGraph 核实 `AgentRuntimeFlags` 当前默认 `agent_runtime_enabled=True`、`old_workflow_direct_entry_disabled=True`、`allow_legacy_main_workflow=False`
   - `verify_ultimate_plan.py` 新增 static AgentRuntime flag boundary gate，校验 dataclass 默认值和 `from_env()` 默认值必须继续保持“Runtime 默认启用、旧主 workflow 默认关闭”
   - 门禁要求 `can_call_legacy_main_workflow()` 同时受 `agent_runtime_enabled`、`allow_legacy_main_workflow`、`not old_workflow_direct_entry_disabled` 三个条件约束
   - 门禁要求 `SceneComposerJobRunner.compose()` 必须先检查 `can_call_legacy_main_workflow()`，再允许创建 composer 并调用 `composer.compose()`
   - 门禁要求 `LANChatAgentWorker._get_generation_scheduler()` 必须先检查 `can_call_legacy_main_workflow()`，否则返回 `None`，再允许创建 `GenerationScheduler`
   - 这一步把第 14 节的 feature flag 约束变成非 native 自动验证项，避免后续改动把旧主 workflow 重新作为默认执行路径放出来

77. Phase 8 真实 provider / engine-write 通道默认关闭边界已纳入同一静态门禁：
   - CodeGraph 核实 `LANChatAgentWorker._create_agent_runtime()` 中真实 scene snapshot、image/model resource、environment component、engine import/delete/transform provider 都只在对应 `can_use_*_provider()` 为真时装配
   - `verify_ultimate_plan.py` 的 static AgentRuntime flag boundary gate 已扩展校验所有真实 provider flag 的 dataclass 默认值与 `from_env()` 默认值均为 `False`
   - 门禁要求每个 `can_use_*_provider()` 都必须先经过 `can_call_legacy_function_adapter()`，再读取对应 provider flag，避免单独打开 provider 绕过 Runtime 迁移边界
   - 门禁要求 `_create_agent_runtime()` 中每个真实 provider factory 之前必须先出现对应 `can_use_*_provider()` guard，包括 actor import、actor delete、layout transform 与 environment import
   - 这一步把“真实 C++/资源 provider 必须显式开启，默认保持 mock / RuntimeState-only”的第 14 节约束固化为非 native 自动验证项

78. Phase 5/Report `execute_scene_plan()` 默认返回已移除 ToolCallGraph 节点细节：
   - CodeGraph 核实 `AgentRuntime.execute_scene_plan()` 是 Runtime 内部确认执行闭环入口，历史返回值中仍包含 `graph.nodes` 的完整 ToolCall 明细
   - `execute_scene_plan()` 现在默认只返回 `graph_id`、`status`、`node_count` 等 graph 摘要，不再默认返回 `nodes`
   - 需要内部调试或测试 DAG 依赖时，必须显式传入 `include_debug_graph_nodes=True` 才能拿到 `graph_result["nodes"]`
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已扩展检查该默认安全返回契约，防止后续把 graph node 明细重新放回默认返回
   - Runtime 内部测试同步区分默认安全返回与 debug 返回，继续保留验证工具顺序、依赖和 consumes 契约的能力
   - 这一步继续推进“用户/上层默认只看到 RuntimeState / OperationLog 派生事实，不直接暴露 ToolCallGraph 节点 raw payload”的收口

79. Phase 5/UI `handle_message()` 用户可见返回面已补齐 graph 节点泄露门禁：
   - CodeGraph 核实 `refresh_scene_snapshot()`、`propose_layout_adjustment()` 等内部 helper 仍保留详细 graph 返回，用于 Runtime 内部调试与测试
   - 用户可见 `handle_message()` 分支必须只返回安全 graph 摘要：scene snapshot、layout adjustment、layout confirm、confirmed delete advisory 均只返回 `{"status": ...}`
   - 修复 `pending intervention -> adjustment proposal` 分支：不再把 `propose_layout_adjustment()` 的 raw graph 原样返回给上层，只返回 graph status
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已扩展检查 `handle_message()` 的用户返回面必须使用 `safe_snapshot` 和 graph status 摘要，并禁止 raw graph payload 直返
   - 这一步保留内部 helper 的调试能力，同时继续保证聊天室 / action 层不暴露 ToolCallGraph 节点、tool args 或 raw payload

80. Phase 5/UI Runtime queue/drain/execute 用户可见返回面继续收窄：
   - CodeGraph 核实 `handle_message(worker_drain)` 曾把 `drain_result` 原样返回，`confirm_and_enqueue` 曾把 `queued` 和 `queued["graphs"]` 原样返回，`confirm_and_execute` 曾把 `execution["graphs"]` 原样返回
   - 新增 `_safe_graph_summary_for_user()` / `_safe_graphs_for_user()` / `_safe_queue_result_for_user()` / `_safe_drain_result_for_user()`，统一把 graph、queue、drain 结果收敛为 graph_id / batch_id / status / node_count / drained_count 等摘要
   - `handle_message()` 的 worker drain、介入批次 enqueue、生成 enqueue、直接 execute 分支均不再返回 `nodes`、tool args、consumes 或 raw ToolCallGraph 节点明细
   - `execute_scene_plan()` 默认返回也同步改为 safe queue / safe drain 摘要；内部完整 graph nodes 仍留在 RuntimeState 与显式 debug 参数中，避免丢失诊断能力
   - Runtime 测试已覆盖 confirm-and-execute、confirm-and-enqueue、worker-drain、execute-scene-plan 的用户可见 payload 不含 `nodes`，同时确认 RuntimeState 内部仍保留完整执行图事实
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已扩展禁止 `handle_message()` 重新出现 `"drain": drain_result`、`"queued": queued`、`"graphs": queued["graphs"]`、`"graphs": execution["graphs"]` 等原样透传

81. Phase 6/GM Planner 上下文摘要已从 RuntimeState 生成结构化 digest：
   - CodeGraph 核实 `gm_summary()` 当前通过 `status_summary()` 读取 RuntimeState 中的 `planning_context_events`，再通过 `runtime.gm_summary.snapshot` 持久化 GM-facing 摘要
   - 新增 `_planning_context_digest_for_report()`，从已落 RuntimeState 的安全 `text_preview`、speaker_type、agent_name、owner_agent、source_context_agents 派生上下文 digest
   - `status_summary()` 与最终 `generate_report()` 的 `planning_context_summary` 均包含 `context_digest`，使 GM / Planner 不再只依赖最近三条 context，也不需要回读 raw chat history
   - `gm_summary()` 现在返回 `context_digest`，包含 speaker_type_counts、owner_agent、source_context_agents、agent_contributions、latest_user_points、latest_agent_points
   - Runtime 测试已覆盖房主 + 多 Agent 讨论后，GM summary 能同时保留长者 / 商人的贡献，并确认 snapshot fact 与用户可见摘要一致
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求 `gm_summary()` 保留 `context_digest` / `agent_contributions`，防止 GM 总结退回薄状态摘要

82. Phase 6/Planner 介入摘要已从 RuntimeState 生成结构化 intervention digest：
   - CodeGraph 核实 `status_summary()` / `generate_report()` 已读取 RuntimeState 中的 pending / accepted / deferred interventions，但此前主要暴露数量和 latest 列表，Planner 仍需自行判断哪些能进下一批
   - 新增 `_intervention_digest_for_report()`，从已落 RuntimeState 的 PlanPatch 事实派生 patch_type_counts、next_batch_candidate_items、absorbable / non_absorbable 计数、needs_confirmation 与 deferred_reasons
   - `status_summary()` 与 `generate_report()` 的 `intervention_summary` 均包含 `intervention_digest`，让 GM / Planner 可以直接区分“下一批可吸收新增物体”和“需要确认的修改/删除/高风险介入”
   - Runtime 测试已覆盖新增天使雕像 + 修改入口布局的混合 pending 介入：天使雕像进入 next_batch_candidate_items，修改请求进入 needs_confirmation
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求 status / report 保留 `intervention_digest`，防止介入摘要退回只有计数与最近列表

83. Phase 7/Sync 同步与资源传输健康摘要已进入 Runtime 报告面：
   - CodeGraph 核实 `status_summary()` / `generate_report()` 已分别暴露 `sync_summary`、`asset_transfer_summary`、`sync_replay_summary`、`message_delivery_summary`，但缺少统一健康判定，GM / 验收仍需要人工拼日志
   - 新增 `_sync_health_digest_for_report()`，从 RuntimeState 与 OperationLog 已有同步事实派生 `healthy` / `partial` / `needs_attention` / `no_sync_facts` 状态
   - `sync_health_digest` 汇总 actor sync、asset transfer、transfer progress、message delivery failure，不暴露 message_id、correlation_id、asset_path、provider、URL 等内部字段
   - `status_summary()`、`generate_report()` 和 `sync_status` 动作均返回 `sync_health_digest`，使多人同步/模型传输问题成为 Runtime 一等可验收状态
   - `ReportRecordValidator` 已将 `sync_health_digest` 纳入报告白名单，但仍走安全树校验，避免新增字段绕过报告安全约束
   - Runtime 测试已覆盖 asset transfer failed -> `needs_attention`、asset transfer progress -> `partial`、message delivery failed -> `needs_attention`
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求 status / report 保留 `sync_health_digest`，防止同步健康摘要从报告面退回日志碎片

84. Phase 7/Sync actor create / transform / delete 动作摘要已进入 `sync_health_digest`：
   - CodeGraph 核实 `record_sync_event()` 已把 C++ / LANChat / engine sync 事实镜像到 RuntimeState 的 `actors`、`sync_events`、`sync_state.actor_events`，并维护 `sync_lifecycle_status`
   - 在不改 C++ 与网络广播链路的前提下，`_sync_health_digest_for_report()` 进一步从 `sync_replay_summary.event_type_counts` 和 `sync_summary.latest_actors` 派生 actor action digest
   - 新增字段包括 `actor_create_count`、`actor_transform_count`、`actor_delete_count`、`latest_actor_count`、`latest_active_actor_count`、`latest_deleted_actor_count`
   - 这使多人联机验收可以直接判断“actor 创建有无同步、transform 是否进入 Runtime、delete 是否落到生命周期状态”，而不是只能人工 grep `Broadcast actor create` / `actor_transform` / `actor_deleted`
   - Runtime 测试已覆盖 actor transform + delete 后，status / report 的 `sync_health_digest` 与 replay 计数一致；`sync_status` 查询也会返回 actor create 摘要
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求这些 actor sync 字段保留在 `_sync_health_digest_for_report()` 中

85. Phase 7/Sync peer / room lifecycle 摘要已进入 `sync_health_digest`：
   - CodeGraph 核实 `record_sync_event()` 已把 room close、peer join、peer leave 等 C++/LANChat 同步事实进入 `sync_state.peer_events`、`sync_state.room_status` 和 OperationLog replay
   - `_sync_health_digest_for_report()` 现在从 `sync_replay_summary` 派生 `peer_join_count`、`peer_leave_count`、`room_close_count`、`latest_peer_id`、`latest_peer_event_type`、`latest_room_status`
   - 房间关闭会进入 `needs_attention=["room_closed"]` 并将 digest 状态置为 `needs_attention`；普通 peer join / leave 保持健康生命周期摘要，不误判为失败
   - 这使多人联机验收可以直接判断“房间是否被关闭、peer 是否发生 join/leave、最新 peer 事件是谁”，不再只能人工翻 LANChat / NetworkSystem 日志
   - Runtime 测试已覆盖 room_closed -> `needs_attention`，以及 peer join + leave 后 status / report digest 与 replay 一致
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求这些 peer / room lifecycle 字段保留在 `_sync_health_digest_for_report()` 中

86. Phase 7/GM 同步健康摘要已进入 GM-facing summary：
   - CodeGraph 核实 `gm_summary()` 已通过 `status_summary()` 读取 RuntimeState，而不是直接读取底层 LANChat / Network / Engine 状态
   - `gm_summary()` 现在透传 `sync_health_digest`，让 GM 总结可以同时看到讨论上下文、计划摘要和多人同步健康状态
   - `runtime_gm_summary_exported` 只记录 `sync_health_status` 与 `sync_attention_count`，不暴露 message_id、asset_path、provider、URL 等内部字段
   - Runtime 测试已覆盖 GM summary 在多 Agent 讨论后同时包含 context digest 与 actor sync health digest，并确认 snapshot fact 与用户可见摘要一致
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求 `gm_summary()` 保留 `sync_health_digest` / `sync_health_status`

87. Phase 7/LANChat GM 回复已披露同步健康摘要：
   - CodeGraph 核实 `@GM 总结当前方案` / 状态查询会优先走 `LANChatAgentWorker._agent_runtime_status_reply()`，该路径读取 AgentRuntime `status_summary()`，旧 Coordinator 只作为显式 legacy fallback
   - `_agent_runtime_status_reply()` 现在读取 `sync_health_digest`，并在“多人同步”行中展示健康状态、需关注项数量、actor create/transform/delete 计数、active actor 数与 peer join/leave 计数
   - 新增 `_format_agent_runtime_sync_health_report()`，只输出安全状态与计数；不暴露 peer_id、message_id、asset_path、provider、URL 或私有路径
   - LANChat Runtime guard 测试已覆盖同步中模型同传进度会显示 `partial`、`attention 1` 与 `asset-transfer-in-progress`，同时继续确认内部路径和 peer id 不会出现在 GM 回复中
   - 这一步把第 86 项的 Runtime GM summary 能力接到实际聊天室 GM-facing 文案，便于多人联机时直接判断同步健康而不是人工翻日志

88. Phase 7/GM 总结动作已从普通状态查询中分离：
   - CodeGraph 核实 `LANChatAgentWorker._handle_coordinator_status_query()` 是 `@GM 总结当前方案` 与状态查询进入 Runtime 的关键分流点
   - 新增 `_is_runtime_gm_summary_query()`，将 `总结/汇总/概括/当前方案/现在方案/生成方案` 这类 GM 总结请求路由到 AgentRuntime `runtime_gm_summary`；`进度/到哪/生成到哪里/什么情况` 仍走普通 `status_query`
   - 新增 `_agent_runtime_gm_summary_reply()`，GM 总结回复只展示方案、上下文、Agent 贡献、最近用户要点、介入摘要、模型/地形清单和同步健康，不再把 ToolCallGraph、资源通道、引擎写入等执行面细节塞进总结
   - `AgentRuntime.gm_summary()` 现在带出 `intervention_digest`，使 GM 能总结待处理/已吸收/延后介入，而不需要读取旧 Coordinator 或底层 Scheduler
   - LANChat Runtime guard 测试已覆盖无 ScenePlan 的 room-level 讨论也能由 Runtime GM summary 总结，且不会构造旧 Coordinator；同步健康与介入摘要均在 GM-facing 回复中可见
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求 `gm_summary()` 保留 `intervention_digest`，防止 GM 总结退回只有上下文而看不到用户介入状态

89. Phase 7/GM summary export 已记录安全介入计数：
   - CodeGraph 核实 `AgentRuntime.gm_summary()` 的 `runtime_gm_summary_exported` OperationLog payload 原先只记录 context 与 sync health 计数，缺少介入摘要的可回放证据
   - `runtime_gm_summary_exported` 现在增加 `intervention_pending_count`、`intervention_accepted_count`、`intervention_deferred_count` 三个安全数字段
   - 这些字段只用于复盘 GM 总结是否看见了用户介入状态，不记录用户原文、patch_id、metadata、actor_id、provider、URL 或私有路径
   - 新增 Runtime 测试覆盖有 ScenePlan 的介入场景：GM summary 返回 `intervention_digest`，OperationLog export payload 只包含计数且不泄露“天使雕像”等用户原文
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求这些 intervention export 字段保留在 `gm_summary()` 中

90. Phase 7/GM summary `recorded` 语义已从 context-only 修正为 Runtime availability：
   - CodeGraph 核实 `AgentRuntime.handle_message(action="runtime_gm_summary")` 原先只用 `context_count` 判断 `recorded`，会把“已有 ScenePlan 但暂无讨论上下文”的 GM summary 误标为未记录
   - `recorded` 现在跟随 `gm_summary.available`，只要 RuntimeState 中已有可用 ScenePlan 或讨论上下文，就视为已记录的 GM summary
   - 新增 Runtime 测试用 `StatePatch` 写入无 discussion context 的 ScenePlan，验证 `runtime_gm_summary` 返回 `recorded=True`、`available=True`、`has_scene_plan=True` 且 `context_count=0`
   - 这一步保持 GM summary 的事实源仍为 RuntimeState / OperationLog，不回退旧 Coordinator，也不为了记录状态伪造上下文

91. Phase 7/GM summary replay 摘要已进入 operation replay/report：
   - CodeGraph 核实 `runtime_gm_summary_exported` 已有安全 payload，但 `operation_replay()` / `generate_report()` 的 compact replay 之前没有 GM summary 聚合视图
   - 新增 `_gm_summary_replay_summary()`，从 OperationLog 聚合 exported/failed、available、scene_plan、context、agent contribution、intervention 计数和 sync health 状态分布
   - `operation_replay()` 与 `_operation_replay_summary_for_report()` 均返回 `gm_summary_replay_summary`，使 GM 总结本身可被 Runtime 回放和最终报告复盘
   - 摘要只输出计数和状态，不暴露用户原文、patch_id、metadata、actor_id、provider、URL 或私有路径
   - Runtime 测试已覆盖 GM summary export 后 operation replay 与 final report 都包含该摘要，且不泄露“天使雕像”等用户原文
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求 `_operation_replay_summary_for_report()` 保留 `gm_summary_replay_summary`

92. Phase 6/Layout reflow 后选择性 AABB 贴地已进入 `runtime.layout.apply_delta`：
   - CodeGraph 核实 `_apply_layout_delta_tool()` 原先只执行低风险 move；无真实 engine transform provider 时，RuntimeState 内部不会根据 AABB 修正地面物体浮空
   - `runtime.layout.apply_delta` 现在会在低风险 move 后识别 actor 支撑类型：地面支撑物体执行 AABB bottom snap，墙挂/悬挂/system/unknown 对象跳过
   - 贴地修正基于移动后的 AABB bottom，而不是粗暴 `position.y=0`；同步更新 `position.y` 与 `aabb.min/max.y`，保持 RuntimeState 自洽
   - 新增 Runtime 测试覆盖无 provider 的确认布局调整：`藏宝箱` 被贴地，`火把` 作为 wall-mounted 只移动不落地
   - `verify_ultimate_plan.py` 的 Runtime validator contract gate 已要求 `_apply_layout_delta_tool()` 保留 `_layout_support_type()`、`_shift_actor_aabb()` 与 `_snap_actor_bottom_to_ground_if_supported()`，防止回退成纯 move

93. Phase 4/Batch ToolCall facts 已进入 status/report 安全摘要：
   - CodeGraph 核实 `batch.prioritize_items`、`batch.create`、`batch.merge_intervention` 已把批次排序、批次草案和介入合并结果写入 `custom_batch_facts`
   - 新增 `_batch_tooling_summary_for_plan()`，从 RuntimeState 聚合 created/prioritized/merged/absorbed 计数，让 ToolCall 产物可被状态查询和最终报告复盘
   - `status_summary()` 与 `generate_report()` 均返回 `batch_tooling_summary`；摘要只输出 fact 类型和计数，不暴露 `patch_id`、用户原文、provider、URL 或私有路径
   - Runtime 测试已覆盖普通批次规划和生成中介入追加两条链路，确认 batch tooling summary 与 report/status 一致且不泄露介入 id
   - `verify_ultimate_plan.py` 的 Runtime report / validator gate 已要求 `status_summary()`、`generate_report()` 和 helper 保留该摘要，防止 Phase 4 批次工具事实重新变成不可见内部状态

94. Phase 5/Runtime command 队列影响已进入 operation replay/report：
   - CodeGraph 核实 `apply_runtime_command()` 已通过 RuntimeState 修改 pause/cancel/resume/retry 对 ScenePlan、BatchPlan、ToolCallGraph queue 的影响，且 `drain_next_tool_graph()` 会在 paused/cancelled 状态下阻断执行图出队
   - `_runtime_command_replay_summary()` 现在聚合 `cancelled_batch_total`、`cancelled_graph_total`、`resumed_graph_total`、`retried_graph_total` 与状态迁移计数
   - `operation_replay()` 与 `generate_report()` 的 compact replay 可以证明 Runtime command 不只是聊天室文案，而是真正影响 Runtime queue / graph / batch 状态
   - Runtime 测试已覆盖 pause/resume/cancel 与 retry 两条命令链路，确认 replay/report 能看到取消批次数、取消执行图数和重试执行图数，且不暴露 `command_id`
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求这些 queue-impact 字段保留在 runtime command replay 中，继续推进 `GenerationScheduler queue -> ToolCallGraph queue`

95. Phase 5/ToolGraph queue health 已进入 status/report 安全摘要：
   - CodeGraph 核实 `status_summary()` 与 `generate_report()` 已能看到 RuntimeState 中的 `tool_graphs` / `tool_graph_queue`，但此前缺少专门的 queue/backpressure 聚合视图
   - 新增 `_tool_queue_health_summary_for_plan()`，从 RuntimeState 聚合 `queue_count`、`queued_count`、`running_count`、`blocked_count`、`terminal_count`、`active_count`、`queue_pressure`、queue/graph/node 状态分布
   - `status_summary()` 与 `generate_report()` 均返回 `tool_queue_health_summary`；摘要只输出计数、状态和批次序号，不暴露 `graph_id`、`tool_call_id`、provider、URL 或私有路径
   - Runtime 测试已覆盖批次只入队未 drain 的场景，确认 status/report 能看到 queue pressure 和 queued 计数，且不会泄露 `graph_id`
   - `verify_ultimate_plan.py` 的 Runtime report / validator gate 已要求 status/report 和 helper 保留该摘要，继续推进 `backpressure -> ToolCall state`

96. Phase 6/Review advisory proposal 状态已进入 operation replay：
   - CodeGraph 核实 `review_advisory_proposal_created` 与 `review_advisory_confirmation_recorded` 已写入 OperationLog，但 `_review_advisory_replay_summary()` 之前只能看到 created/confirmed 事件数量，不能判断建议是否仍待房主确认
   - `_review_advisory_replay_summary()` 现在聚合 `proposal_status_counts`、`pending_proposal_count`、`confirmed_proposal_count`、`rejected_proposal_count` 与 `advisory_item_count`
   - 这一步让 VLM / Reviewer 建议的“只生成 proposal、不直接改场景、等待确认”可以被 operation replay 证明，而不是只依赖用户可见文案
   - Runtime 测试已覆盖 review provider 生成建议、确认前 pending、确认后 confirmed 的 replay 变化，且不暴露截图路径、prompt、provider raw 或内部 id
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求这些 review advisory replay 字段保留，继续推进 `VLM 只产出 proposal，不直接改场景`

97. Phase 6/Layout adjustment proposal 状态已进入 operation replay：
   - CodeGraph 核实 `layout_adjustment_requested` 与 `layout_adjustment_confirmed` 已写入 OperationLog，但 `_layout_adjustment_replay_summary()` 之前主要统计执行结果，无法证明完成态布局调整建议是否仍待确认
   - `layout_adjustment_requested` 现在在 OperationLog 安全 payload 中记录 `proposal_id` 与 `delta_count`，不再依赖会被 safe replay 剥离的嵌套 proposal
   - `_layout_adjustment_replay_summary()` 现在聚合 `proposal_status_counts`、`pending_proposal_count`、`confirmed_proposal_count`、`failed_proposal_count` 与 `delta_count`
   - Runtime 测试已覆盖布局建议创建后 pending、确认执行后 confirmed 的 replay 变化，同时继续验证 transform / selective ground snap 计数
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求这些 layout adjustment replay 字段保留，继续推进 `完成态调整通过 Reviewer + RuntimeGuard + ToolCall 执行`

98. Phase 7/Sync asset transfer 生命周期已进入 operation replay/report：
   - CodeGraph 核实 `record_sync_event()` 已把 C++ / LANChat / engine 的 asset transfer 事实写入 RuntimeState `assets`、`sync_events` 与 OperationLog，但此前 `operation_replay()` 只有泛 `sync_summary`，不能单独复盘 started / progress / completed / failed / peer-ready 生命周期
   - 新增 `_asset_transfer_replay_summary()`，从安全 OperationLog entries 与 RuntimeState sync events 聚合 `asset_transfer_started_count`、`asset_transfer_progress_count`、`asset_transfer_completed_count`、`asset_transfer_failed_count`、`peer_asset_ready_count` 与 `transfer_status_counts`
   - `operation_replay()` 与 `_operation_replay_summary_for_report()` 均返回 `asset_transfer_replay_summary`，让多人同传模型卡顿、失败、peer ready 等问题可以从 Runtime replay 直接定位
   - 摘要只输出 asset_id、peer_id、状态、progress、chunk 与 bytes 计数，不暴露 `asset_path`、`message_id`、`correlation_id`、provider、URL 或私有路径
   - Runtime 测试已覆盖 file chunk progress、completed、peer ready、failed 生命周期，并确认 final report 的 replay summary 与 operation replay 一致且无路径泄露
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求这些 asset transfer replay 字段保留，继续推进 `asset/model transfer facts -> RuntimeState / OperationLog / Report`

99. Phase 7/Sync `sync_status` 查询已固化 asset transfer lifecycle 快照：
   - CodeGraph 核实 `sync_status` action 已通过 `runtime.sync_status.snapshot` 把同步状态写入内部 `runtime-sync-status` RuntimeState fact，但此前快照只包含 `sync_status`、`sync_replay`、`sync_health_digest` 与 message delivery
   - `sync_status` action 现在从 `operation_replay()` 读取 `asset_transfer_replay_summary`，并把它纳入返回值和 `runtime.sync_status.snapshot` fact
   - `_record_sync_status_snapshot_tool()` 与 `_sync_status_snapshot_via_tool_graph()` 的安全 payload 现在记录 asset transfer started / progress / completed / failed / peer-ready 计数，便于状态查询证明模型同传生命周期已被 Runtime 读取
   - `peer_asset_ready` 等 peer ready 事件在 Runtime 镜像中进入 completed/ready 状态，不再被误归为 transferring
   - Runtime 测试已覆盖 `sync_status` 查询中 asset transfer lifecycle 快照落盘、OperationLog export / snapshot 计数一致、失败分支不返回未落盘摘要，以及路径/provider 不泄露
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已要求 `handle_message(sync_status)` 与 sync status snapshot 保留 asset transfer lifecycle 字段；这一步仍不改 C++ 网络传输，只推进同步事实读侧 Runtime 化

100. Phase 7/Sync peer lifecycle 与 reconcile 摘要已进入 operation replay/report/sync_status：
   - CodeGraph 核实 peer join / leave / room close 已在 `record_sync_event()` 写入 RuntimeState `sync_state.peer_events` 与 OperationLog，但此前只能从泛 `sync_summary` 读取，缺少面向多人协作复盘的独立 peer/reconcile 摘要
   - 新增 `_peer_sync_replay_summary()`，从安全 OperationLog entries 与 RuntimeState sync events 聚合 `peer_event_count`、`peer_join_count`、`peer_leave_count`、`room_close_count`、`sync_reconcile_count`、`sync_reconcile_failed_count`、`state_reconcile_count`、`state_reconcile_failed_count`
   - `operation_replay()` 与 `_operation_replay_summary_for_report()` 均返回 `peer_sync_replay_summary`，让多人联机中的 peer 生命周期和状态补偿/冲突 reconcile 可以从 Runtime replay 直接定位
   - `sync_status` action 现在把 `peer_sync_replay_summary` 纳入返回值和 `runtime.sync_status.snapshot` fact；`runtime_sync_status_exported` 与 `runtime_sync_status_snapshot_recorded` 也记录 peer/reconcile 计数
   - 摘要只输出 peer_id、event_type、room_status 和计数，不暴露 `message_id`、`correlation_id`、provider、URL、prompt 或私有路径
   - Runtime 测试已覆盖 peer join + leave、sync reconcile completed / failed、state patch reconcile completed / failed，以及 sync_status 快照落盘；`verify_ultimate_plan.py` 已把 peer/reconcile replay 字段加入静态门禁

101. Phase 4/BatchResourcePlan v2 批次资源闭环摘要已进入 status/report：
   - 当前 Runtime 执行图已经具备 `runtime.asset.image.prepare`、`runtime.asset.model.prepare`、`runtime.actor.import_batch`、`runtime.geometry.review`、`runtime.review.vlm_checkpoint` 与 `runtime.review.summarize_batch` 等批次资源节点；此前 `resource_summary` 更偏阶段聚合，无法直接回答“每个 batch 的图片、模型、导入、审查是否闭环”
   - 新增 `_batch_resource_flow_summary_for_plan()`，从 RuntimeState 的 `batch_plans`、`image_resource_plans`、`model_resource_plans`、`custom_import_facts`、`geometry_reviews`、`custom_vlm_checkpoint_facts` 与 `custom_review_summary_facts` 聚合每批 `image/model/import/review` 状态
   - `status_summary()` 与 `generate_report()` 均返回 `batch_resource_flow_summary`，包含 `batch_count`、`completed_count`、`partial_count`、`failed_count`、`waiting_count` 与最近批次的 ready/failure 计数
   - 摘要只输出 batch_id、批次序号、状态与安全计数，不暴露 provider、prompt、URL、模型路径、ToolCallGraph nodes 或内部异常文本
   - Runtime 测试已覆盖完整 mock 批次中 image/model/import/review 全 ready 时的 completed 判定；`verify_ultimate_plan.py` 已把 `batch_resource_flow_summary` 加入 status/report/helper 静态门禁
   - 这一步仍是 RuntimeState 读侧与报告事实源收口，不代表真实 provider 已完成“大分批图片生成 -> 模型生成 -> 导入 -> 审查”的实机执行接管

102. Phase 4/OperationLog 批次资源生命周期已进入 replay/report：
   - CodeGraph 与当前文件核实资源阶段已经通过 `runtime_event_emitted` 记录 `image_resources_ready/failed`、`model_resources_ready/failed`、`actors_imported/import_failed` 与 environment component 事件；此前这些事件没有独立的批次资源生命周期 replay 摘要
   - 新增 `_batch_resource_lifecycle_replay_summary()`，从 OperationLog 聚合 `resource_event_count`、`image_ready_count`、`model_ready_count`、`import_ready_count`、对应 failed 计数、`emit_failed_count`、`batch_event_counts` 与 `latest_resource_event`
   - `operation_replay()` 与 `_operation_replay_summary_for_report()` 均返回 `batch_resource_lifecycle_summary`，让“本批图片、模型、导入阶段是否曾被 Runtime 事件化并落入日志”可以被 replay 和最终报告证明
   - 摘要只读取安全 event_type、batch_id 与 persisted 状态，不暴露 provider、prompt、URL、截图路径、模型路径、ToolCallGraph nodes 或内部异常文本
   - Runtime 测试已覆盖完整 mock 批次的 image/model/import replay 计数，并确认 `generate_report()` 中的 `operation_replay_summary.batch_resource_lifecycle_summary` 与 `operation_replay()` 一致
   - `verify_ultimate_plan.py` 的 Runtime report fact-source gate 已加入 helper、report 和 replay 接入静态门禁；这一步继续落实“OperationLog 必须先于用户报告”的不变量

103. Phase 6/GM Summary 已能读取批次资源闭环 digest：
   - CodeGraph 核实 `gm_summary()` 只通过 `status_summary()` 读取 RuntimeState / OperationLog 派生事实；此前 GM summary 已有讨论上下文、介入摘要和同步健康，但缺少面向“资源批次是否卡住/失败/完成”的安全摘要
   - `gm_summary()` 现在从 `batch_resource_flow_summary` 派生 `resource_flow_digest`，包含 `batch_count`、`completed_count`、`partial_count`、`failed_count`、`waiting_count`、最近批次的 image/model/import ready 计数与 review 状态
   - `runtime_gm_summary_exported` OperationLog payload 追加 `resource_batch_count`、`resource_failed_count`、`resource_waiting_count`，用于复盘 GM 是否看见批次资源健康度
   - 摘要只输出安全计数、batch 状态和最近批次摘要，不暴露 provider、prompt、URL、模型路径、ToolCallGraph nodes 或内部异常文本
   - Runtime 测试已覆盖完整 mock 批次执行后 GM summary 可以看到资源闭环完成状态，且 `verify_ultimate_plan.py` 已把 `resource_flow_digest` 与导出计数字段加入 Runtime GM summary 静态门禁
   - 这一步推进 GM / Planner 从 Runtime 事实源读取生成进度与资源健康度；完整语义仲裁、长期记忆和冲突决策策略仍未完成

104. Phase 6/LANChat GM Runtime 摘要已披露资源批次健康：
   - CodeGraph 核实 `LANChatAgentWorker._agent_runtime_gm_summary_reply()` 是 `@GM 总结当前方案` 走 Runtime summary 后的用户可见回复面；此前 Runtime 内部已有 `resource_flow_digest`，但聊天室回复只展示上下文、介入、模型、地形和多人同步健康
   - 新增 `_format_agent_runtime_resource_flow_report()`，把 `resource_flow_digest` 转成安全文本：批次数、completed/partial/failed/waiting 计数、最近批次 image/model/import ready 计数、review 状态和需关注项
   - `【GM Runtime 摘要】` 现在增加 `资源批次：...` 行，用户/房主可直接看到大分批资源闭环是否完成、等待或失败，而不需要查看内部 report/replay
   - 文案只输出安全计数和状态，不暴露 provider、prompt、URL、模型路径、ToolCallGraph nodes、tool_name 或内部异常文本
   - LANChat Runtime guard 测试已覆盖 Runtime mock 生成完成后 `@GM 总结当前方案` 回复包含资源批次摘要；`verify_ultimate_plan.py` 的 AgentRuntime flag boundary gate 已要求 worker 保留该 formatter 和 GM reply 接入
   - 这一步继续推进 GM / Planner 的 Runtime 事实可见性，但不改变真实 provider、不触碰 C++/Quasar，也不代表真实大分批执行已完成

105. Phase 6/LANChat 普通 Runtime 状态回复已披露资源批次健康：
   - CodeGraph 核实 `LANChatAgentWorker._agent_runtime_status_reply()` 是用户询问“进度 / 到哪了 / 当前状态”时的 Runtime-first 回复面；此前该回复已有资源通道和资源可用性，但缺少按 batch 聚合的资源闭环摘要
   - `_agent_runtime_status_reply()` 现在读取 `batch_resource_flow_summary`，复用 `_format_agent_runtime_resource_flow_report()` 输出 `资源批次：...`
   - 显式 batch 查询会显示当前 batch 的 completed/failed/waiting 等安全状态；全计划状态查询会显示整体批次资源健康，帮助区分“方案状态正常”与“图片/模型/导入批次卡住”
   - 文案只输出安全计数和状态，不暴露 provider、prompt、URL、模型路径、ToolCallGraph nodes、tool_name 或内部异常文本
   - LANChat Runtime guard 测试已覆盖显式 batch 状态回复包含资源批次摘要；`verify_ultimate_plan.py` 的 AgentRuntime flag boundary gate 已要求 status reply 保留 `batch_resource_flow_summary` 和 formatter 接入
   - 这一步继续解决用户体感上的“问状态但看不到资源阶段真实进展”；真实 provider 大分批执行仍待后续 F5 验证

106. Phase 5/LANChat Operation Replay 已披露批次资源生命周期：
   - CodeGraph 核实 `_handle_agent_runtime_operation_replay_query()` 是 `@GM runtime operation replay` 的用户可见诊断面；Runtime replay 内部已有 `batch_resource_lifecycle_summary`，但聊天室回复此前只展示 entry/event/context/review/engine/message/recent
   - 新增 `_format_agent_runtime_batch_resource_lifecycle_report()`，把 image/model/import/environment lifecycle ready/failed 计数和最近资源事件转成安全文本
   - `【Runtime Operation Replay】` 现在增加 `batch_resources: ...` 行，支持按 room/plan/batch 复盘资源阶段是否事件化并落入 OperationLog
   - 文案不暴露 provider、prompt、URL、模型路径、ToolCallGraph nodes、tool_name 或内部异常文本
   - LANChat Runtime guard 测试覆盖带 metadata batch scope 的 replay 查询只显示目标 batch 的资源生命周期；`verify_ultimate_plan.py` 已要求 formatter 和 reply 接入
   - 这一步继续把 F5 日志诊断入口迁入 Runtime OperationLog；真实 provider 大分批执行仍待后续 F5 验证

107. Phase 5/LANChat Operation Replay 已披露 Runtime command 队列影响：
   - CodeGraph 核实 Runtime replay 内部已有 `runtime_command_summary`，可聚合 pause/cancel/resume/retry 等命令的状态迁移、取消批次数、取消 graph 数、恢复 graph 数和重试 graph 数
   - 新增 `_format_agent_runtime_replay_command_report()`，专门适配 replay 的 `latest_command` 与 queue-impact 计数字段，避免复用普通 report/status command formatter 时因结构不同而显示 `none`
   - `【Runtime Operation Replay】` 现在增加 `commands: ...` 行，支持按 room/plan/batch 复盘运行时命令是否真正影响 Runtime queue / batch / graph
   - 文案只输出命令计数、状态迁移和取消/恢复/重试计数，不暴露 command_id、tool_call_id、graph_id、provider、prompt、URL 或内部异常文本
   - LANChat Runtime guard 测试覆盖带 metadata batch scope 的 replay 查询显示目标 batch 的 runtime command 影响；`verify_ultimate_plan.py` 已要求 replay command formatter 和 reply 接入
   - 这一步继续推进“暂停/取消/恢复不是聊天文案，而是 Runtime OperationLog 可复盘事实”的 Phase 5 目标

108. Phase 5/LANChat Operation Replay 已披露 ToolCall 与 ToolGraph queue 摘要：
   - CodeGraph 核实 Runtime replay 内部已有 `tool_execution_summary` 和 `tool_graph_queue_summary`，可聚合 ToolCall started/succeeded/failed/blocked/retry/skipped 与 ToolGraph queued/dequeued/completed/rejected/blocked/missing
   - 新增 `_format_agent_runtime_replay_tool_execution_report()` 与 `_format_agent_runtime_replay_tool_queue_report()`，把工具执行和队列生命周期转成安全计数文本
   - `【Runtime Operation Replay】` 现在增加 `tools: ...` 和 `queue: ...` 行，支持按 room/plan/batch 复盘 ToolCallGraph 是否真的执行、是否被队列阻塞或缺失
   - 文案只输出事件计数、状态和最近安全事件名，不暴露 graph_id、tool_call_id、tool_name、tool args、provider、prompt、URL 或内部异常文本
   - LANChat Runtime guard 测试覆盖带 metadata batch scope 的 replay 查询显示目标 batch 的 tool execution 与 queue 摘要；`verify_ultimate_plan.py` 已要求两个 formatter 和 replay reply 接入
   - 这一步继续落实 `ToolCallGraph 是唯一执行编排` 与 `OperationLog 必须先于用户报告` 两条架构不变量

109. Phase 5/LANChat Operation Replay 已披露 RuntimeState patch 与 RuntimeGuard 摘要：
   - CodeGraph 核实 Runtime replay 内部已有 `state_patch_summary` 和 `runtime_guard_replay_summary`，可聚合 RuntimeState patch version/applied/conflict/invalid/reconcile 事件，以及 RuntimeGuard blocked/high-risk/write-confirm/system-actor 等写权限判断事件
   - 新增 `_format_agent_runtime_replay_state_patch_report()` 与 `_format_agent_runtime_replay_guard_report()`，把状态合并结果和写权限拦截结果转成安全计数文本
   - `【Runtime Operation Replay】` 现在增加 `state_patch: ...` 和 `guard: ...` 行，支持按 room/plan/batch 复盘状态是否真正落盘、写工具是否被 RuntimeGuard 拦截
   - 文案只输出事件计数、状态和安全原因类别，不暴露 patch_id、tool_call_id、actor_id、graph_id、tool args、provider、prompt、URL 或内部异常文本
   - LANChat Runtime guard 测试覆盖带 metadata batch scope 的 replay 查询显示目标 batch 的 state patch 与 guard 摘要；`verify_ultimate_plan.py` 已要求两个 formatter 和 replay reply 接入
   - 这一步继续落实 `RuntimeGuard 是唯一写权限判断`、`RuntimeState 是唯一状态事实源` 和 `OperationLog 必须先于用户报告` 三条架构不变量

110. Phase 5/LANChat Operation Replay 已披露 ScenePlan 生命周期与介入批次摘要：
   - CodeGraph 与当前代码核实 Runtime replay 内部已有 `scene_plan_lifecycle_summary` 和 `intervention_batch_replay_summary`，可聚合 ScenePlan created/confirmed/state/status/extracted 生命周期，以及 pending intervention routed/queued/persisted/skipped/absorbed 批次事件
   - 新增 `_format_agent_runtime_replay_plan_lifecycle_report()` 与 `_format_agent_runtime_replay_intervention_report()`，把方案生命周期和用户/Agent 中途介入批次路由结果转成安全计数文本
   - `【Runtime Operation Replay】` 现在增加 `plan_lifecycle: ...` 和 `interventions: ...` 行，支持按 room/plan/batch 复盘方案是否创建/确认、介入是否进入后续批次或被吸收
   - 文案只输出事件计数、状态和最近安全事件类别，不暴露 plan raw prompt、patch_id、tool_call_id、graph_id、requested item prompt、provider、URL 或内部异常文本
   - LANChat Runtime guard 测试覆盖 active plan replay 可见 plan lifecycle，metadata batch scope replay 可见目标 batch 的 intervention routing/absorption；`verify_ultimate_plan.py` 已要求两个 formatter 和 replay reply 接入
   - 这一步继续推进多人/多 Agent 动态介入从“聊天记录解释”迁移为 Runtime OperationLog 可复盘事实

111. Phase 5/LANChat Operation Replay 已披露 RuntimeEvent 与失败策略摘要：
   - CodeGraph 与当前代码核实 Runtime replay 内部已有 `runtime_event_replay_summary` 和 `tool_failure_strategy_summary`，可聚合用户可见 RuntimeEvent emitted/failed/type counts，以及 ToolCall retry/skipped/abandoned/handler_failed/invalid_result/state_conflict 等失败处理策略
   - 新增 `_format_agent_runtime_replay_runtime_event_report()` 与 `_format_agent_runtime_replay_failure_strategy_report()`，把事件披露和失败策略转成安全计数文本
   - `【Runtime Operation Replay】` 现在增加 `runtime_events: ...` 和 `failure_strategy: ...` 行，支持按 room/plan/batch 复盘用户可见进度事件是否发出、失败是否按 Runtime 策略重试/跳过/丢弃 late result
   - 文案只输出事件计数、类型分布、策略类别和安全状态，不暴露 event payload、tool args、provider、prompt、URL、error raw 或内部异常文本
   - LANChat Runtime guard 测试覆盖目标 batch 的 runtime event 与 retry strategy 摘要；`verify_ultimate_plan.py` 已要求两个 formatter 和 replay reply 接入
   - 这一步继续推进“资源长耗时披露、失败降级、重试/跳过策略”从旧日志诊断迁移为 Runtime OperationLog 可回放事实

112. Phase 5/LANChat Operation Replay 已披露 VLM checkpoint 与布局调整摘要：
   - CodeGraph 与当前代码核实 Runtime replay 内部已有 `vlm_checkpoint_summary` 和 `layout_adjustment_summary`，可聚合 VLM checkpoint/advisory/status/type 与 layout adjustment request/confirm/apply/transform/ground snap/overlap 结果
   - 新增 `_format_agent_runtime_replay_vlm_report()` 与 `_format_agent_runtime_replay_layout_report()`，把外观审查和完成态布局调整闭环转成安全计数文本
   - `【Runtime Operation Replay】` 现在增加 `vlm: ...` 和 `layout: ...` 行，支持按 room/plan/batch 复盘 VLM 是否实际参与、布局调整是否产生 proposal 并执行 transform/贴地/避让
   - 文案只输出事件计数、状态和 checkpoint/proposal 类别，不暴露截图路径、prompt、provider、actor_id、graph_id、tool args、URL 或内部异常文本
   - LANChat Runtime guard 测试覆盖目标 batch 的 VLM checkpoint 与 layout adjustment 摘要；`verify_ultimate_plan.py` 已要求两个 formatter 和 replay reply 接入
   - 这一步继续把“VLM 是否生效”和“调整布局是否闭环”从 F5 体感/日志猜测迁移为 Runtime OperationLog 可回放事实

113. Phase 4/5 LANChat Operation Replay 已披露环境组件与资源可用性摘要：
   - CodeGraph 与当前代码核实 Runtime replay 内部已有 `environment_component_summary` 和 `resource_readiness_replay_summary`，可聚合 environment component ready/failed/import/import_failed，以及 resource readiness status query/publish/event/status counts
   - 新增 `_format_agent_runtime_replay_environment_report()` 与 `_format_agent_runtime_replay_resource_readiness_report()`，把地形/环境组件和资源通道预检结果转成安全计数文本
   - `【Runtime Operation Replay】` 现在增加 `environment: ...` 和 `resource_readiness: ...` 行，支持按 room/plan/batch 复盘地形/边界/环境组件是否进入 RuntimeEvent，以及资源通道 readiness 是否发布
   - RuntimeEvent formatter 已将 `provider_readiness` 等内部事件标签安全改写为 `resource-readiness`，用户回复不暴露 provider、prompt、URL、raw、token、API key 或内部路径
   - LANChat Runtime guard 测试覆盖目标 batch 的 environment component 与 resource readiness 摘要，并继续校验回复不出现 `provider` / `prompt`；`verify_ultimate_plan.py` 已要求两个 formatter 和 replay reply 接入
   - 这一步继续把“开放场景 substrate/terrain 是否派生”和“资源通道是否可用”从 F5 日志判断迁移为 Runtime OperationLog 可回放事实

114. Phase 7/LANChat Operation Replay 已披露多人同步、模型同传与 peer 摘要：
   - CodeGraph 与当前代码核实 Runtime replay 内部已有 `sync_summary`、`asset_transfer_replay_summary`、`peer_sync_replay_summary`，可聚合 actor sync、asset transfer progress/completed/failed、peer join/leave/reconcile 等多人联机场景事实
   - LANChat Operation Replay 查询层新增 `sync: ...`、`asset_transfer: ...`、`peer_sync: ...` 三行安全摘要，并把 replay 查询窗口从 20 条提升到 50 条，避免资源、VLM、布局、同步事件互相挤掉
   - 新增 `_format_agent_runtime_replay_asset_transfer_report()` 与 `_format_agent_runtime_replay_peer_sync_report()`，复用既有 `_format_agent_runtime_sync_replay_report()`，只输出计数、进度、chunk/bytes、完成/失败与 reconcile 状态
   - 文案不暴露 `peer_id`、`asset_id`、文件路径、message_id、provider、prompt、URL、raw payload、token 或 API key；测试中显式注入 secret peer/asset/path 并校验不会出现在回复里
   - LANChat Runtime guard 测试覆盖目标 batch 的 actor transform、asset transfer progress、peer asset ready、peer join 与 sync reconcile 摘要；`verify_ultimate_plan.py` 已要求三个 replay summary、formatter 和回复行接入
   - 这一步继续把“多人联机模型/actor 同步是否卡顿、是否完成、是否重放一致”从 F5 日志经验迁移为 Runtime OperationLog 可回放事实

115. Phase 7/LANChat Runtime Report 已消费同步 replay 摘要：
   - CodeGraph 核实 `[Runtime Report]` 原先只显示 `sync_summary` 和 `asset_transfer_summary` 的当前状态，没有消费 `operation_replay_summary` 中的 `sync_replay_summary`、`asset_transfer_replay_summary`、`peer_sync_replay_summary`
   - `_handle_agent_runtime_report_query()` 现在从 report 的 `operation_replay_summary` 读取三类 replay 摘要，并新增 `sync replay: ...`、`asset transfer replay: ...`、`peer sync replay: ...` 用户可见行
   - 这让 Runtime Report 同时回答“当前同步/同传状态是什么”和“本轮 replay 里实际发生过哪些 actor sync、asset transfer、peer join/reconcile 事件”
   - 文案复用 Operation Replay 的安全 formatter，只输出计数、进度、chunk/bytes、完成/失败和 reconcile 状态，不暴露 peer_id、asset_id、内部路径、message_id、provider、prompt、URL 或 raw payload
   - LANChat Runtime guard 报告测试已注入 peer/asset/path/message secret 并校验 report 不泄露；`verify_ultimate_plan.py` 已把 Runtime Report 的三类 replay 行纳入静态门禁
   - 这一步继续落实 `OperationLog 必须先于用户报告`，并让多人同步诊断不只停留在专用 operation replay 查询里，也进入正式 Runtime Report

116. Phase 7/GM Runtime 摘要已消费同步 replay digest：
   - CodeGraph 核实 `gm_summary()` 原先只消费 `sync_health_digest`，GM 摘要能看到同步健康状态，但不能看到本轮 OperationLog 中 asset transfer / peer join / reconcile 的回放事实
   - `status_summary()` 现在同步保留 `asset_transfer_replay_summary` 与 `peer_sync_replay_summary`，`gm_summary()` 从 `sync_replay_summary`、`asset_transfer_replay_summary`、`peer_sync_replay_summary` 派生 `sync_replay_digest`
   - LANChat GM 摘要新增 `同步复盘：...`，用紧凑格式显示 recorded/failed、actor transform/delete、asset progress/completed/failed、peer-ready、peer join/leave、reconcile 计数
   - 文案只输出 digest 计数，不暴露 peer_id、asset_id、内部路径、message_id、provider、prompt、URL 或 raw payload；测试显式注入 secret peer/asset/path 并校验不会出现在 `@GM 总结当前方案` 回复中
   - `verify_ultimate_plan.py` 已要求 Runtime `gm_summary()` 产出 `sync_replay_digest`，并要求 LANChat GM summary reply 显示 `同步复盘`
   - 这一步让 GM 总结从“只解释当前健康状态”推进为“可基于 OperationLog 解释本轮同步/同传发生过什么”，继续落实 `RuntimeState 是唯一状态事实源` 与 `OperationLog 必须先于用户报告`

117. Phase 7/LANChat Runtime 状态回复已消费同传/peer replay 摘要：
   - CodeGraph 核实 `_agent_runtime_status_reply()` 原先只显示 `sync_replay_summary`，但没有读取 `asset_transfer_replay_summary` 与 `peer_sync_replay_summary`
   - Runtime 普通状态回复现在新增 `同传复盘：...` 与 `Peer 复盘：...`，补齐 asset transfer progress/completed/failed、peer-ready、peer join/leave/reconcile 等批次范围事实
   - 该回复仍保留原有 `多人同步：当前状态；健康；复盘` 与 `模型同传：当前状态`，新增内容用于区分“当前同传状态”和“OperationLog 中实际发生过的同传/peer 事件”
   - 文案复用安全 replay formatter，只输出计数、进度、chunk/bytes 和状态，不暴露 peer_id、asset_id、内部路径、message_id、provider、prompt、URL 或 raw payload
   - LANChat Runtime guard 测试覆盖带 metadata batch scope 的状态查询，并校验同传/peer replay 只显示目标 batch 计数且不泄露 secret；`verify_ultimate_plan.py` 已要求 Runtime status reply 接入两类 replay formatter 和用户可见行
   - 这一步让 `@GM 当前状态`、`@GM runtime report`、`@GM runtime operation replay`、`@GM 总结当前方案` 四类入口都能从 RuntimeState/OperationLog 消费同步回放事实

118. Phase 7/RuntimeEvent 用户可见披露已透传安全事件 metadata：
   - CodeGraph 核实 `_emit_agent_runtime_events_since()` 原先能把 RuntimeEvent 转成聊天室系统消息，但 `_send_agent_runtime_system_event()` 只发送 `phase/room_id`，前端/同步层无法稳定按 event、plan、batch、stage、progress 去去重和对齐
   - 新增 `_safe_runtime_event_metadata()`，只白名单输出 `runtime_event_id`、`runtime_event_type`、`runtime_plan_id`、`runtime_batch_id`、`runtime_stage`、`runtime_progress`，并裁剪 progress 到 0-100
   - RuntimeEvent 发送路径现在以 `line + event` 成对传递，`network_send_system_message_ex()` 的 metadata 与 OperationLog audit payload 均携带同一份安全事件字段
   - 文案和 metadata 不透传 event payload、provider、prompt、asset_path、URL、raw 或 token；测试显式注入 secret provider/prompt/path 并校验可见消息与 replay 均不泄露
   - `verify_ultimate_plan.py` 已要求 RuntimeEvent sender 接收 `runtime_event` 并要求 metadata helper 产出六个安全字段，继续落实 `OperationLog 必须先于用户报告` 和 UI 阶段披露可对齐

119. Phase 7/RuntimeEvent 披露 metadata 已携带 audience / level 语义：
   - CodeGraph 核实 `RuntimeEvent` 本身已有 `audience` 与 `level` 字段，但 LANChat 系统消息 metadata 原先没有传递这两个语义，前端/同步层无法区分 host-only、participants、warning、error 等展示策略
   - `_safe_runtime_event_metadata()` 现在仅在 allowlist 内输出 `runtime_audience` 与 `runtime_level`，非法值不会进入用户可见 metadata
   - OperationLog audit payload 与 replay snapshot schema 同步放行这两个安全字段，保证可见消息、审计、复盘三处语义一致
   - 本步骤不改变 C++ 网络发送行为，也不声称已经完成前端分众显示；它只是把 RuntimeState 的可见性/严重级别事实安全带到 UI metadata 边界
   - LANChat Runtime guard 测试覆盖 `host + warning` 事件 metadata 与 replay payload；`verify_ultimate_plan.py` 已要求 metadata helper 保留 `runtime_audience` / `runtime_level`

120. Phase 7/LANChat 自动 RuntimeEvent 披露已过滤非用户 audience：
   - CodeGraph 核实 `runtime_events` action 支持按 `audience` 查询，但 worker 自动轮询 `_emit_agent_runtime_events_since()` 原先未传 audience，可能把 `agent` / `system` 内部事件也推成普通聊天室系统消息
   - 新增 `_should_auto_disclose_agent_runtime_event()`，自动披露只允许 `host`、`participants`、`all` 三类用户可见 audience；`agent` / `system` 事件仍保留在 RuntimeState / OperationLog，但不自动发到聊天室
   - 被跳过的事件会写入 `runtime_system_event_disclosure_skipped` audit，payload 只携带安全 runtime metadata 和 `reason=audience_not_user_visible`，便于后续 replay 解释“事件存在但未自动披露”
   - 该步骤继续落实信息披露边界：RuntimeEvent 是事实源，LANChat 自动消息只是用户可见投影，内部 Agent/System 事件不得默认污染多人聊天
   - LANChat Runtime guard 测试覆盖 host 事件正常发送、agent 事件跳过、skip audit 可 replay 且不泄露 provider/prompt/path；`verify_ultimate_plan.py` 已把 disclosure guard 与 skip audit 纳入静态门禁

121. Phase 7/LANChat RuntimeEvent 自动披露已避免内部事件挤占用户进度：
   - CodeGraph 核实 `_emit_agent_runtime_events_since()` 原先先调用 `_format_agent_runtime_event_rows(fresh_events)`，而 formatter 只取最后 3 条；如果最后几条都是 `agent` / `system` 内部事件，真正的 host/participants 进度会在过滤前被挤掉
   - 自动披露流程现在先把 `fresh_events` 分成 `disclose_events` 与 skipped 内部事件，再对 `disclose_events` 做最后 3 条格式化发送
   - 这保证内部 Agent/System 事件不会污染聊天室，也不会让用户可见进度因为内部事件密集而饿死；被跳过的内部事件仍写入 `runtime_system_event_disclosure_skipped`
   - LANChat Runtime guard 测试覆盖“1 条 host 进度后跟 4 条 agent 内部事件”的场景，确认 host 进度仍会发送且 4 条内部事件只进入 skip audit
   - `verify_ultimate_plan.py` 已要求 `_emit_agent_runtime_events_since()` 先产生 `disclose_events` 再调用 `_format_agent_runtime_event_rows(disclose_events)`

122. Phase 7/LANChat RuntimeEvent 自动披露查询窗口已扩大，避免查询阶段 starvation：
   - CodeGraph 核实 `_emit_agent_runtime_events_since()` 向 Runtime 查询事件时仍硬编码 `limit=8`；如果 host 进度后跟 8 条以上 `agent/system` 内部事件，host 事件会在查询阶段被截掉，后续过滤再正确也无法披露
   - 新增 `MAX_AGENT_RUNTIME_DISCLOSURE_EVENT_LOOKBACK = 32`，自动披露查询使用该窗口拉取最近事件；实际发送仍由 `_format_agent_runtime_event_rows(disclose_events)` 限制为最后 3 条用户可见事件，避免刷屏
   - LANChat Runtime guard 测试覆盖“1 条 host 进度后跟 12 条 agent 内部事件”的场景，确认 host 进度仍会发送，12 条内部事件只进入 skip audit
   - 这一步继续修复用户体感的“前面不动”：内部 Runtime 事件密集时，不应挤掉真正应该缓解等待焦虑的用户可见进度
   - `verify_ultimate_plan.py` 已要求自动披露路径使用 `MAX_AGENT_RUNTIME_DISCLOSURE_EVENT_LOOKBACK`，防止回退到小窗口硬编码

123. Phase 7/RuntimeEvent 跳过披露 audit 已按 Runtime plan 归档：
   - CodeGraph 核实 `_record_skipped_agent_runtime_event_disclosure()` 通过 `runtime_audit_event` 写 OperationLog，但 Runtime audit 原先只通过 external SeedPlan 解析 `entry.plan_id`；跳过披露事件只有 RuntimeEvent 自带的 `plan_id`，因此按 plan 做 operation replay 时可能看不到“为什么没有披露”
   - `_record_runtime_audit_event()` 现在可传入 `runtime_plan_id`，`AgentRuntime.handle_message(action=runtime_audit_event)` 会在当前 room 的 RuntimeState 中校验该 plan 存在后，把 OperationLog entry 归档到真实 `plan_id`
   - skipped disclosure audit 同时保留 `batch_id`，因此 `operation_replay(room, plan_id, batch_id)` 能解释某批次内部事件被跳过披露的原因
   - LANChat Runtime guard 测试覆盖带 Runtime plan 的 agent-only RuntimeEvent：自动披露不发送消息，但 `operation_replay(plan_id=...)` 能看到 `runtime_system_event_disclosure_skipped`
   - `verify_ultimate_plan.py` 已要求 skip audit 与 runtime audit recorder 保留 `runtime_plan_id` / `batch_id` scope，继续落实 `OperationLog 必须先于用户报告`

124. Phase 7/Operation Replay 已聚合 RuntimeEvent 跳过披露摘要：
   - CodeGraph 核实 `LANChatAgentWorker._format_agent_runtime_replay_runtime_event_report()` 原先只格式化 emitted / failed / latest；即使 `runtime_system_event_disclosure_skipped` 已进入 OperationLog，用户或 GM 查询 replay 时仍需要翻明细才能知道有内部事件被安全跳过
   - `AgentRuntime._runtime_event_replay_summary()` 现在统计 `disclosure_skipped_count`，并记录 `latest_disclosure_skip` 的安全 event_type / audience / reason / batch_id
   - Operation Replay 的 runtime_events 行现在显示 `skipped N` 与最近 skip 类型，继续不暴露 provider、prompt、URL、raw、内部路径或 token
   - LANChat Runtime guard 测试覆盖 plan-scoped skipped audit 的 summary 与 formatter 输出；`verify_ultimate_plan.py` 已要求 Runtime core summary builder 和 worker formatter 同时保留 skipped 聚合字段

125. Phase 7/Runtime Report 与状态查询已消费 RuntimeEvent 跳过披露摘要：
   - CodeGraph 核实 Runtime Report 原先只把 replay summary 压成泛 `entries/events/recent`，普通 Runtime status 则只显示最近用户可见 RuntimeEvent；当内部 `agent/system` 事件被安全跳过时，用户仍难以知道“事件存在但被披露策略过滤”
   - `AgentRuntime.status_summary()` 现在带出 `runtime_event_replay_summary`，`LANChatAgentWorker._agent_runtime_status_reply()` 复用安全 runtime event replay formatter 显示 `skipped N`
   - Runtime Report 的 `_format_agent_runtime_replay_report()` 现在在 replay 摘要里消费 `runtime_event_replay_summary`，当存在跳过披露事件时追加 `runtime-events ... skipped N`
   - LANChat Runtime guard 测试覆盖 Runtime Report 与 batch-scoped status reply 两个入口，确认 skipped disclosure 可见且不泄露 provider、prompt、URL、内部路径或 raw payload；`verify_ultimate_plan.py` 已将 status/report/core 三处 token 纳入门禁

126. Phase 7/GM Runtime 摘要已消费 RuntimeEvent 跳过披露 digest：
   - CodeGraph 核实 `_agent_runtime_gm_summary_reply()` 通过 `AgentRuntime.gm_summary()` 读取 status_summary 派生事实；此前 GM summary 已消费同步和资源 digest，但没有解释 RuntimeEvent 披露策略过滤
   - `AgentRuntime.gm_summary()` 现在从 `runtime_event_replay_summary` 生成 `runtime_event_replay_digest`，只保留 emitted / failed / skipped 计数和最近跳过披露的安全 event_type / audience / reason / batch_id
   - GM 回复新增 `RuntimeEvent replay` 行，复用安全标签裁剪，不透传 provider、prompt、URL、raw、token、API key、截图路径或内部路径
   - LANChat Runtime guard 测试覆盖 GM 总结入口可看到 `skipped 1` 与 `latest-skip agent-internal:agent`，且 secret provider/prompt 不泄露；`verify_ultimate_plan.py` 已要求 core/worker 两侧保留该 digest 与 formatter

127. Phase 5/7 Runtime queue health 已进入 LANChat 状态、报告与 GM 读侧：
   - CodeGraph 核实 `AgentRuntime.status_summary()` 与 `generate_report()` 已返回 `tool_queue_health_summary`，但 LANChat 的 Runtime status、Runtime Report、GM summary 还未统一消费该摘要
   - 新增 `_format_agent_runtime_tool_queue_health_report()`，只输出 `queue_count`、`active_count`、queued/running、blocked、terminal 与 `queue_pressure` 百分比，不暴露 graph id、tool call id、tool name、provider、prompt、URL、内部路径或 raw payload
   - Runtime Report 新增 `runtime queue` 行；状态查询与 GM Runtime 摘要新增 `Runtime queue` 行；`AgentRuntime.gm_summary()` 从 status_summary 派生 `tool_queue_health_digest`
   - LANChat Runtime guard 测试覆盖 report/status/GM 三个入口均能看到 queue pressure；`verify_ultimate_plan.py` 已要求 core/worker 两侧保留 queue health digest、formatter 与读侧消费

128. Phase 5/7 Batch tooling 摘要已进入 LANChat 状态、报告与 GM 读侧：
   - CodeGraph 与当前代码核实 `AgentRuntime.status_summary()` / `generate_report()` 已返回 `batch_tooling_summary`，用于证明批次创建、物体优先级、介入合并等批次规划事实来自 RuntimeState，而不是旧 workflow 黑箱文案
   - `AgentRuntime.gm_summary()` 现在从 `batch_tooling_summary` 派生 `batch_tooling_digest`，保留 fact、created-batches、priorities、merged、absorbed 与 latest fact type 计数
   - 新增 `_format_agent_runtime_batch_tooling_report()`，Runtime Report 新增 `batch tooling` 行，状态查询与 GM 摘要新增 `Batch tooling` 行；输出只包含计数和 fact type，不暴露 batch fact key、tool payload、graph id、provider、prompt、URL、内部路径或 raw payload
   - LANChat Runtime guard 测试覆盖 report/status/GM 三个入口均能看到 `created-batches`；`verify_ultimate_plan.py` 已要求 core/worker 两侧保留 batch tooling digest、formatter 与读侧消费

129. Phase 5/7 StatePatch 与失败策略摘要已进入 LANChat 状态、报告与 GM 读侧：
   - CodeGraph 与当前代码核实 `AgentRuntime.status_summary()` 已返回 `state_patch_summary` 与 `tool_failure_strategy_summary`，Operation Replay 也已有安全 formatter，但普通 status / Runtime Report / GM summary 读侧还未直接消费这些事实
   - `AgentRuntime.gm_summary()` 现在派生 `state_patch_digest` 与 `tool_failure_strategy_digest`，保留 versioned/applied/conflict/invalid/reconciled/reconcile-pending、retry/skipped/abandoned/handler-failed/invalid/state-conflict/stopped 等计数
   - Runtime Report 新增 `state patch` 与 `failure strategy` 行；状态查询与 GM Runtime 摘要新增 `StatePatch` / `Failure strategy` 行；文案复用 Operation Replay 的安全 formatter，不暴露 patch id、source tool call id、tool payload、provider、prompt、URL、内部路径或 raw payload
   - LANChat Runtime guard 测试覆盖 report/status/GM 三个入口均能看到 StatePatch 与 Failure strategy；`verify_ultimate_plan.py` 已要求 core/worker 两侧保留 digest、formatter 与读侧消费

130. Phase 7/GM Runtime 摘要已消费引擎写入与消息送达 digest：
   - CodeGraph 核实 `AgentRuntime.status_summary()` 已返回 `engine_write_summary` 与 `message_delivery_summary`，状态查询和 Runtime Report 已能显示这些事实，但 GM summary 还缺少对应摘要
   - `AgentRuntime.gm_summary()` 现在派生 `engine_write_digest` 与 `message_delivery_digest`，保留 import / transform / env-import / delete 结果计数，以及 requested / succeeded / failed / message kind / channel / latest stage / progress
   - GM Runtime 摘要新增 `Engine write` 与 `Message delivery` 行，复用已有安全 formatter，不暴露 actor id、message id、peer id、asset path、provider、prompt、URL、内部路径或 raw payload
   - LANChat Runtime guard 测试覆盖 GM 摘要可见 Engine write / Message delivery；`verify_ultimate_plan.py` 已要求 core/worker 两侧保留 digest、formatter 与读侧消费

131. Phase 5/7 RuntimeGuard 写权限摘要已进入 LANChat 状态、报告与 GM 读侧：
   - CodeGraph 核实 `runtime_guard_replay_summary` 原本只在 Operation Replay 中稳定存在，普通 Runtime status、Runtime Report 与 GM summary 缺少同一事实源的直接读侧
   - `AgentRuntime.status_summary()` 现在基于同一 Runtime scoped OperationLog entries 返回 `runtime_guard_replay_summary`；`generate_report()` 将 Operation Replay 中的 Guard 摘要提升为顶层报告字段
   - `AgentRuntime.gm_summary()` 现在派生 `runtime_guard_digest`，保留 blocked、high-risk-confirm、write-confirm、system-actor、visible-blocked 与 latest block reason/batch 的安全摘要
   - Runtime Report 新增 `guard` 行，状态查询与 GM Runtime 摘要新增 `RuntimeGuard` 行，复用 `_format_agent_runtime_replay_guard_report()`，不暴露 tool args、raw payload、provider、prompt、URL、内部路径或敏感 actor/message 标识
   - LANChat Runtime guard 测试覆盖 report/status/GM 三个入口均能看到 Guard 摘要；`verify_ultimate_plan.py` 已要求 core/worker 两侧保留 Guard digest、formatter 与读侧消费

132. Phase 2/7 ScenePlan lifecycle 摘要已进入 LANChat 状态、报告与 GM 读侧：
   - CodeGraph 核实 `scene_plan_lifecycle_summary` 原本只在 Operation Replay 中稳定存在，普通 Runtime status、Runtime Report 与 GM summary 不能直接说明计划创建、确认、持久化和提取状态
   - `AgentRuntime.status_summary()` 现在返回 `scene_plan_lifecycle_summary`；当查询限定到某个 batch 时，生命周期仍按 plan 级别聚合，避免批次范围遮蔽计划创建/确认事实
   - `AgentRuntime.generate_report()` 将 Operation Replay 中的 `scene_plan_lifecycle_summary` 提升为顶层报告字段，并同步加入 `ReportRecordValidator` 白名单，保证结构化报告可持久化
   - `AgentRuntime.gm_summary()` 现在派生 `scene_plan_lifecycle_digest`，保留 created、confirmed、state/status persisted/failed、extracted 与 latest plan event 的安全摘要
   - Runtime Report 新增 `plan lifecycle` 行，状态查询与 GM Runtime 摘要新增 `Plan lifecycle` 行，复用 `_format_agent_runtime_replay_plan_lifecycle_report()`，不暴露 raw payload、prompt、provider、URL、内部路径或 tool args
   - LANChat Runtime guard 测试覆盖 report/status/GM 三个入口均能看到 Plan lifecycle 摘要；`verify_ultimate_plan.py` 已要求 core/worker 两侧保留 lifecycle digest、formatter 与读侧消费

133. Phase 6/7 VLM checkpoint 与 review advisory replay 摘要已进入 LANChat 状态、报告与 GM 读侧：
   - CodeGraph 核实 `vlm_checkpoint_summary` 与 `review_advisory_summary` 原本主要存在于 Operation Replay，普通 Runtime status、Runtime Report 与 GM summary 缺少同一事实源的直接摘要
   - `AgentRuntime.status_summary()` 现在返回 `vlm_checkpoint_summary` 与 `review_advisory_replay_summary`；`generate_report()` 将 Operation Replay 中的 VLM checkpoint / review advisory 摘要提升为顶层报告字段，并同步加入 `ReportRecordValidator` 白名单
   - `AgentRuntime.gm_summary()` 现在派生 `vlm_checkpoint_digest` 与 `review_advisory_replay_digest`，保留 checkpoint/proposal/confirmation/advisory item 计数、状态分布与 latest decision 的安全摘要
   - Runtime Report 新增 `vlm replay` 与 `review advisory replay` 行，状态查询与 GM Runtime 摘要新增 `VLM replay` 与 `Review advisory replay` 行，复用安全 formatter，只输出计数、checkpoint 类型、状态和 proposal 状态
   - 该切片只把 VLM / review 事实接入读侧与报告面，不让 VLM 自动修改场景；不暴露截图路径、prompt、provider、URL、raw payload、tool args、actor/message 内部标识
   - LANChat Runtime guard 测试覆盖 report/status/GM 三个入口均能看到 VLM checkpoint 与 review advisory replay；`verify_ultimate_plan.py` 已要求 core/worker 两侧保留 digest、formatter 与读侧消费

134. Phase 2/6/7 SceneDesignContract 长周期场景契约已进入 RuntimeState、报告与 GM 读侧：
   - CodeGraph 核实旧 `SceneDesignContract` 主要由 `InteractionCoordinator` 维护，AgentRuntime 的 `ScenePlan` 持久化链路此前缺少同等的长期风格、地形、边界、避雷词约束事实
   - `AgentRuntime._persist_new_scene_plan()` 与 ScenePlan 状态持久化路径现在会从 `ScenePlan` 派生安全的 `custom_scene_design_contract_facts`，记录 scene_type、environment_type、mood、style_keywords、avoid_keywords、terrain、boundary、scale_rules 与 placement_rules
   - `AgentRuntime.status_summary()` 与 `generate_report()` 现在返回 `scene_design_contract_summary`；`ReportRecordValidator` 白名单同步允许该字段，保证状态查询和最终报告都能读取同一个 RuntimeState 事实源
   - `AgentRuntime.gm_summary()` 现在派生 `scene_design_contract_digest`，供 GM 总结长期场景约束、地形/边界类型和负向约束，不回退旧 Coordinator memory
   - Runtime Report 新增 `scene contract` 行，状态查询新增 `场景契约` 行，GM Runtime 摘要新增 `Scene contract` 行；formatter 只输出安全摘要，不暴露 prompt、provider、URL、raw payload、内部路径或 tool args
   - LANChat Runtime guard 测试覆盖 report/status/GM 三个入口均能看到场景契约摘要；`verify_ultimate_plan.py` 已要求 core/worker 两侧保留 summary、digest、formatter 与读侧消费

135. Phase 6/Planner + GM 语义仲裁摘要已进入 RuntimeState 读侧：
   - CodeGraph 核实 `gm_summary()` 当前先通过 `status_summary()` 读取 RuntimeState 中的 planning context、ScenePlan、intervention、SceneDesignContract，再经 `runtime.gm_summary.snapshot` 持久化 GM-facing 摘要
   - 新增 `semantic_arbitration_summary`，从 RuntimeState 已有事实派生 arbitration_state、execution_readiness、requires_host_confirmation、needs_clarification、owner_agent、contributing_agents、multi_agent_discussion 与 risk_flags
   - Runtime Report 新增 `semantic arbitration` 行，状态查询新增 `语义仲裁` 行，GM Runtime 摘要新增 `Semantic arbitration` 行，帮助 GM / Planner 区分“只有讨论上下文”“方案待房主确认”“已确认或执行中”“完成后可调整”等状态
   - 该切片不调用 LLM、不改变 IntentRouter、不执行工具、不写引擎，只把语义仲裁所需的结构化读侧事实从旧聊天/Coordinator 隐性状态迁移到 RuntimeState / OperationLog 可复盘视图
   - LANChat Runtime guard 测试覆盖 report/status/GM 三个入口均能看到语义仲裁摘要；`verify_ultimate_plan.py` 已要求 core/worker 两侧保留 summary、digest、formatter 与读侧消费
```

验证状态：

```text
python editor/plugins/AITool/services/test_agent_runtime_phase1.py
python editor/plugins/AITool/services/test_lanchat_runtime_guard.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

当前这些检查已通过；`git diff --check` 只有 CRLF warning，无 whitespace error。

仍未完成：

```text
真实 C++ remove_actor / import_environment_component / import_model / set_actor_transform F5 效果
真实多人 actor create / transform / delete 广播
真实 asset/model transfer 接管与限流
旧 ProgressiveWorkflow / SceneComposer 主控完全工具化仍在推进
真实 provider 下的大分批 image/model/import/review 执行闭环仍待 F5 验证
GM / Planner 的完整语义仲裁与长期记忆 Runtime 化
```

## 14. Feature Flag 与边界

本次重构接受较大架构变动，但仍需要工程开关防止实机完全不可用：

```text
AGENT_RUNTIME_ENABLED=1
OLD_WORKFLOW_DIRECT_ENTRY_DISABLED=1
ALLOW_LEGACY_FUNCTION_ADAPTER=1
ALLOW_LEGACY_MAIN_WORKFLOW=0
```

真实 provider / engine-write 通道必须单独显式开启，默认保持 mock / RuntimeState-only：

```text
AGENT_RUNTIME_USE_SCENE_SNAPSHOT_PROVIDER=0
AGENT_RUNTIME_USE_IMAGE_PROVIDER=0
AGENT_RUNTIME_USE_MODEL_PROVIDER=0
AGENT_RUNTIME_USE_LEGACY_MODEL_PROVIDER=0
AGENT_RUNTIME_USE_ENVIRONMENT_PROVIDER=0
AGENT_RUNTIME_USE_ENGINE_ENVIRONMENT_IMPORT_PROVIDER=0
AGENT_RUNTIME_USE_ENGINE_IMPORT_PROVIDER=0
AGENT_RUNTIME_USE_ENGINE_DELETE_PROVIDER=0
AGENT_RUNTIME_USE_ENGINE_TRANSFORM_PROVIDER=0
AGENT_RUNTIME_USE_SCENE_REVIEW_PROVIDER=0
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




## 16. Progress Update 136 - Runtime read-side scene/resource/import summaries

Status: completed in current non-native slice.

Scope:

```text
Phase 5 / Phase 7 read side
RuntimeState -> LANChat status/report/GM summary
No legacy workflow re-entry
No provider / prompt / raw path leakage
```

Evidence:

```text
CodeGraph confirmed AgentRuntime.status_summary() and AgentRuntime.generate_report()
already expose scene_snapshot_summary, resource_summary and import_summary.

This slice wires those RuntimeState facts into:
- LANChat Runtime status reply
- Runtime report query
- GM Runtime summary reply

AgentRuntime.gm_summary() now exports safe digest fields:
- scene_snapshot_digest
- resource_stage_digest
- import_stage_digest
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
test_lanchat_runtime_guard.py: 174 tests passed
test_agent_runtime_phase1.py: 557 tests passed through verify_ultimate_plan.py
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Notes:

```text
This is a read-side closure slice. It does not change ToolCallGraph execution,
provider behavior, engine write behavior, LAN sync protocol, Quasar, C++,
CMake, Ninja, or CEF.
```

## 17. Progress Update 137 - LANChat/C++ sync bridge rejection reason hardening

Status: completed in current non-native slice.

Scope:

```text
Phase 7 / Python-C++ bridge boundary
LANChat/C++ sync callback -> AgentRuntime.handle_message(runtime_sync_event)
No LAN sync protocol change
No C++ change
No engine write change
```

Problem:

```text
The LANChat sync bridge already routes C++/LANChat/engine sync facts through
AgentRuntime.handle_message(action="runtime_sync_event").  However, when Runtime
rejected an event, the bridge returned Runtime's message directly as reason.
That was safe for normal tokens such as "RuntimeState rejected sync patch", but
it left a boundary hole if a lower layer returned provider, prompt, URL, asset
path, raw payload, or API-key-like text.
```

Change:

```text
Added LANChatAgentWorker._safe_lanchat_sync_bridge_reason().
_record_lanchat_sync_event_in_agent_runtime() now returns a stable
"runtime_sync_rejected" token for unsafe rejection text, while preserving short
safe reasons.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
test_lanchat_runtime_guard.py: 175 tests passed
test_agent_runtime_phase1.py: 557 tests passed through verify_ultimate_plan.py
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Notes:

```text
This closes a bridge-safety gap only. It does not change RuntimeState sync event
storage semantics, OperationLog replay, actor/asset transfer behavior, Quasar,
C++, CMake, Ninja, or CEF.
```

## 17. Progress Update 138 - Runtime engine-write status replay disclosure

Status: completed in current non-native slice.

Scope:

```text
Phase 7 / Python-C++ bridge boundary
AgentRuntime.handle_message(action="engine_write_status")
LANChat Runtime Engine Write preflight reply
OperationLog replay summary only
No C++ call behavior change
No engine write behavior change
```

Problem:

```text
Runtime provider preflight already exposed a safe engine-write replay digest,
but the dedicated Runtime Engine Write query only listed adapter readiness.
That made the C++/engine-write boundary harder to inspect from LANChat because
recorded import / transform / environment-import / delete outcomes were only
visible through the broader provider status path.
```

Change:

```text
AgentRuntime engine_write_status now returns engine_write_summary from the same
OperationLog replay fact source used by provider_status.

LANChatAgentWorker._handle_agent_runtime_engine_write_status_query now appends
a safe replay line:

- replay: import N(...), transform N(...), env-import N(...), actor-delete N(...)

The reply keeps provider/prompt/url-like internal fields out of user-visible
text and continues to avoid creating ScenePlan or calling C++ write APIs.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_lanchat_runtime_guard.py: 175 tests passed
test_agent_runtime_phase1.py: 557 tests passed through verify_ultimate_plan.py
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing LF/CRLF warnings
```

Notes:

```text
This is a read-side Runtime/C++ bridge observability slice. It does not change
RuntimeCppBridge invocation, EngineWriteGate, real import/transform/delete
behavior, LAN sync protocol, Quasar, C++, CMake, Ninja, or CEF.
```

## 17. Progress Update 139 - RuntimeCppBridge safety regression coverage

Status: completed in current non-native slice.

Scope:

```text
Phase 7 / Python-C++ bridge boundary
RuntimeCppBridge normalization and sanitization coverage
No real C++ invocation
No EngineWriteGate behavior change
No provider behavior change
```

Problem:

```text
RuntimeCppBridge is the narrow adapter boundary that normalizes C++/engine
binding results before they enter AgentRuntime. CodeGraph showed the bridge had
small blast radius but no direct test coverage, which was risky for the
Agent-native invariant that real engine returns must be trusted only after
schema normalization and user-visible sanitization.
```

Change:

```text
Added regression coverage for RuntimeCppBridge:

- successful binding payloads keep only narrow safe actor/transform fields
- model_path/provider/prompt/url/api_key/raw metadata are stripped
- failed binding envelopes produce stable sanitized errors
- missing EngineWriteGate methods return stable cpp_gate_method_missing

verify_ultimate_plan.py now requires these RuntimeCppBridge boundary tests to
exist, so future refactors cannot silently remove this safety coverage.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_lanchat_runtime_guard.py: 178 tests passed
test_agent_runtime_phase1.py: 557 tests passed through verify_ultimate_plan.py
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing LF/CRLF warnings
```

Notes:

```text
This is a bridge safety coverage slice. It does not change actual C++ binding
calls, EngineWriteGate invocation, import/transform/delete semantics, LAN sync
protocol, Quasar, C++, CMake, Ninja, or CEF.
```

## 17. Progress Update 140 - Runtime tool manifest engine-plane boundary

Status: completed in current non-native slice.

Scope:

```text
Phase 2 / ToolRegistry and RuntimeGuard boundary
Phase 7 / Python-C++ bridge capability visibility
Runtime tool manifest query
No real engine write
No legacy workflow exposure
```

Problem:

```text
AgentRuntime already registered small engine-plane tools, but the LANChat tool
manifest test only checked one scene snapshot tool.  That left the core
Agent-native invariant under-tested: engine writes should be represented as
named ToolCall-sized capabilities, not hidden behind SceneComposer or
ProgressiveWorkflow.
```

Change:

```text
Expanded the Runtime tool manifest preview and regression tests so the engine
boundary is visible as small tools:

- runtime.environment.import_components
- runtime.actor.import_batch
- runtime.layout.apply_delta
- runtime.actor.mark_deleted

The manifest test verifies categories, write flags, high-risk delete marking,
and that handler/provider/api_key/model_path/tool_call_id internals are not
exposed through the user-visible capability list.

verify_ultimate_plan.py now requires the engine-plane tool manifest regression.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_lanchat_runtime_guard.py: 179 tests passed
test_agent_runtime_phase1.py: 557 tests passed through verify_ultimate_plan.py
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing LF/CRLF warnings
```

Notes:

```text
This is a manifest/observability and test-gate slice. It does not change
ToolCallGraph execution, RuntimeGuard authorization, RuntimeCppBridge calls,
EngineWriteGate invocation, LAN sync protocol, Quasar, C++, CMake, Ninja, or CEF.
```

## 17. Progress Update 141 - RuntimeGuard boundary regression gate

Status: completed in current non-native slice.

Scope:

```text
Phase 2 / RuntimeGuard write authorization boundary
Phase 7 / engine-plane write safety
Static verification gate only
No RuntimeGuard behavior change
No engine write behavior change
```

Problem:

```text
RuntimeGuard already had concrete tests for unconfirmed writes, high-risk tools,
definition-level requires_write, and system actor write blocking.  However,
verify_ultimate_plan.py did not explicitly require those critical tests to
remain present.  A future refactor could accidentally remove the guard coverage
while still leaving the broader suite runnable.
```

Change:

```text
verify_ultimate_plan.py now requires the key RuntimeGuard regression tests from
test_agent_runtime_phase1.py:

- unconfirmed high-risk write tools are blocked
- unconfirmed low-risk write tools are blocked
- ToolDefinition.requires_write is honored even if ToolCall omits requires_write
- confirmed system actor writes are blocked by actor id
- nested system actor references are blocked
- room/terrain system aliases match while false sky prefixes do not
- ToolDefinition default high risk still requires confirmation
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_agent_runtime_phase1.py: 557 tests passed through verify_ultimate_plan.py
test_lanchat_runtime_guard.py: 179 tests passed through verify_ultimate_plan.py
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing LF/CRLF warnings
```

Notes:

```text
This is a test-gate hardening slice. It does not change RuntimeGuard
authorization behavior, ToolCallGraph execution, RuntimeCppBridge calls,
EngineWriteGate invocation, LAN sync protocol, Quasar, C++, CMake, Ninja, or CEF.
```

## 17. Progress Update 142 - RuntimeState StatePatch conflict/reconcile regression gate

Status: completed in current non-native slice.

Scope:

```text
Phase 1 / RuntimeState as single factual state source
Phase 2 / ToolCallGraphExecutor state patch boundary
Static verification gate only
No RuntimeState merge behavior change
No ToolCallGraph execution behavior change
```

Problem:

```text
RuntimeState.apply_patch already validates StatePatch schemas, records applied
patch history, and turns stale expected_version writes into safe
state_patch_conflicts facts.  The Phase 1 tests also covered conflict visibility,
reconcile actions, failed conflict persistence, invalid operation schemas, and
RuntimeState-owned control slot protection.  However, verify_ultimate_plan.py did
not explicitly require these tests to remain present.
```

Change:

```text
verify_ultimate_plan.py now requires the key StatePatch conflict/reconcile
regression tests from test_agent_runtime_phase1.py:

- stale expected_version patches do not overwrite RuntimeState
- conflict facts are visible in status and report without leaking patch/tool ids
- reconcile action records a decision without replaying the stale patch
- failed conflict-state persistence does not emit a false success result
- invalid operations schemas are rejected
- RuntimeState-owned control slots cannot be forged through StatePatch
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
test_agent_runtime_phase1.py: 557 tests passed through verify_ultimate_plan.py
test_lanchat_runtime_guard.py: 179 tests passed through verify_ultimate_plan.py
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Notes:

```text
This is a StatePatch audit/test-gate hardening slice. It does not change
RuntimeState.apply_patch merge semantics, OperationLog behavior, ToolCallGraph
execution, RuntimeCppBridge calls, EngineWriteGate invocation, LAN sync protocol,
Quasar, C++, CMake, Ninja, or CEF.
```

## 17. Progress Update 143 - Phase 6 Runtime geometry AABB and overlap tools

Status: completed in current non-native slice.

Scope:

```text
Phase 6 / Geometry review tooling
ToolRegistry + ToolCallGraphExecutor
RuntimeState custom geometry facts
No real engine physics or C++ collision call
No layout transform behavior change
```

Problem:

```text
The plan requires geometry.compute_aabb and geometry.check_overlap to become
ToolCall-sized Runtime capabilities.  Before this slice, Runtime already had
runtime.geometry.review and runtime.layout.apply_delta, but the smaller AABB and
overlap facts were not independently exposed as AgentRuntime tools.  That meant
future Reviewer/Planner work would still have to infer these geometry facts from
larger review or layout paths.
```

Change:

```text
Added two side-effect-free Runtime geometry tools in agent_runtime/tools.py:

- runtime.geometry.compute_aabb
- runtime.geometry.check_overlap

Both tools consume Runtime actor facts, produce safe custom_geometry_facts, and
never write to the engine.  The AABB tool records center, size and bottom_y for
actors with readable AABB data, while explicitly counting skipped actors.  The
overlap tool records AABB overlap issues with actor names, related actors,
severity and overlap ratio.

verify_ultimate_plan.py now requires both tool names and their Phase 6 regression
tests to remain present.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
test_agent_runtime_phase1.py: 559 tests passed
test_lanchat_runtime_guard.py: 179 tests passed through verify_ultimate_plan.py
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Notes:

```text
This is a Geometry fact-tooling slice. It does not replace real C++ collision,
physics settle, model import, actor transform, LAN sync protocol, Quasar, C++,
CMake, Ninja, or CEF. Real engine AABB/physics correctness still requires F5 or
engine-side verification.
```

## 17. Progress Update 144 - Phase 6 geometry facts enter Runtime status/report read side

Status: completed in current non-native slice.

Scope:

```text
Phase 6 / Geometry review read side
RuntimeState custom_geometry_facts
status_summary / generate_report
No engine write
No real physics or C++ collision call
```

Problem:

```text
Progress Update 143 made AABB and overlap checks available as ToolCall-sized
Runtime tools, but their facts still only existed as raw custom_geometry_facts.
That left a read-side gap: status queries and final reports could summarize VLM,
review, layout adjustment and resource flow, but not the new AABB / overlap fact
layer.
```

Change:

```text
AgentRuntime now derives geometry_fact_summary from custom_geometry_facts and
returns it from both status_summary() and generate_report().  The summary reports
fact_count, AABB actor count, skipped AABB count, overlap issue count, status
counts, fact type counts, and compact latest facts.

ReportRecordValidator now allows geometry_fact_summary as a safe top-level
report field while retaining the existing safe-tree redaction rules.

verify_ultimate_plan.py now requires geometry_fact_summary to remain wired into
generate_report(), status_summary(), and the Runtime helper set.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
test_agent_runtime_phase1.py: 559 tests passed
test_lanchat_runtime_guard.py: 179 tests passed through verify_ultimate_plan.py
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Notes:

```text
This is a Runtime read-side integration slice. It does not change geometry tool
execution, layout transform behavior, RuntimeCppBridge calls, EngineWriteGate
invocation, LAN sync protocol, Quasar, C++, CMake, Ninja, or CEF.
```

## 17. Progress Update 145 - Geometry facts exposed through LANChat Runtime replies

Status: completed in current non-native slice.

Scope:

```text
Phase 6 / Geometry review disclosure
RuntimeState geometry_fact_summary -> LANChat status/report/GM summary
No engine write
No real physics or C++ collision call
```

Problem:

```text
Progress Update 144 made geometry_fact_summary available from AgentRuntime
status_summary() and generate_report(), but LANChat user-visible replies still
did not include that summary.  Users asking for Runtime status, Runtime report,
or GM Runtime summary could see VLM/review/layout/resource facts while missing
the AABB / overlap fact layer.
```

Change:

```text
LANChatAgentWorker now formats geometry facts through
_format_agent_runtime_geometry_fact_report() and includes the safe summary in:

- Runtime report replies
- Runtime status replies
- GM Runtime summary replies

AgentRuntime.gm_summary() now exports geometry_fact_digest and records geometry
fact / overlap counts in the runtime_gm_summary_exported OperationLog event.

verify_ultimate_plan.py now requires the formatter and all three LANChat reply
paths to keep geometry fact disclosure wired through RuntimeState.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_lanchat_runtime_guard.py: 179 tests passed
test_agent_runtime_phase1.py: 559 tests passed through verify_ultimate_plan.py
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing LF/CRLF warnings
```

Notes:

```text
This is a LANChat read-side disclosure slice. It does not change geometry tool
execution, layout transform behavior, real AABB/physics calculation,
RuntimeCppBridge calls, EngineWriteGate invocation, LAN sync protocol, Quasar,
C++, CMake, Ninja, or CEF.
```

## 18. Progress Update 146 - Geometry facts enter OperationLog replay

Status: completed in current non-native slice.

Scope:

```text
Phase 6 / Geometry review replay
ToolCallGraphExecutor geometry StatePatch -> OperationLog safe summary
OperationLog replay -> geometry_fact_replay_summary
Runtime report -> geometry_fact_replay_summary
No engine write
No geometry execution behavior change
```

Problem:

```text
Progress Updates 144 and 145 exposed RuntimeState geometry facts through
status_summary(), generate_report(), LANChat Runtime report/status, and GM
summary.  However, OperationLog replay still did not summarize geometry fact
patches, so AABB / overlap review facts were visible in current state but not
fully replay-auditable from the Runtime log.
```

Change:

```text
ToolCallGraphExecutor now records a sanitized geometry_fact_patch_summary when
a StatePatch writes custom_geometry_facts.  The summary contains only safe
counts and categories: fact_count, aabb_actor_count, aabb_skipped_count,
overlap_issue_count, status_counts, fact_type_counts, and latest fact metadata.

AgentRuntime.operation_replay() and the compact report replay summary now expose
geometry_fact_replay_summary.  generate_report() also carries that summary as a
top-level field, so geometry review evidence can be checked from both current
RuntimeState and replay evidence.

verify_ultimate_plan.py now requires the geometry replay helper, direct replay
hook, compact report hook, and report field.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_agent_runtime_phase1.py: 559 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing LF/CRLF warnings
```

Notes:

```text
This is an OperationLog / report replay slice. It does not change geometry tool
execution, layout transform behavior, RuntimeCppBridge calls, EngineWriteGate
invocation, LAN sync protocol, Quasar, C++, CMake, Ninja, or CEF.
```

## 19. Progress Update 147 - Intervention route and merge replay detail

Status: completed in current non-native slice.

Scope:

```text
Phase 4 / Batch intervention replay
Pending intervention route fact -> OperationLog replay totals
Batch merge fact -> OperationLog replay totals
No generation execution behavior change
No scene import behavior change
```

Problem:

```text
AgentRuntime already routed pending interventions through
runtime.intervention.plan_next_batch and merged batch additions through
batch.merge_intervention.  The replay summary proved that routing, persistence,
and queueing happened, but it did not preserve enough aggregate evidence to
audit what the route saw versus what the merge absorbed.

That left the "user intervention changed the next batch" invariant weaker than
the current RuntimeState facts, especially when an interaction contains both
absorbable add requests and non-absorbable modify requests.
```

Change:

```text
_intervention_batch_replay_summary() now includes route and merge aggregates:

- route_absorbable_count
- route_non_absorbable_count
- route_requested_item_count
- merge_event_count
- merged_item_count
- merge_absorbed_count

The phase1 intervention batch regression now asserts these fields against the
actual custom_intervention_route_facts and custom_batch_facts.  This keeps the
replay evidence aligned with RuntimeState, without exposing intervention patch
ids or internal tool graph ids.

verify_ultimate_plan.py now requires these route/merge replay tokens.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_agent_runtime_phase1.py: 559 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing LF/CRLF warnings
```

Notes:

```text
This is an OperationLog replay detail slice. It does not change intervention
routing, batch merge execution, resource generation, scene import,
RuntimeCppBridge calls, EngineWriteGate invocation, LAN sync protocol, Quasar,
C++, CMake, Ninja, or CEF.
```

## 20. Progress Update 148 - LANChat intervention replay exposes route and merge counts

Status: completed in current non-native slice.

Scope:

```text
Phase 4 / User-visible intervention replay
OperationLog intervention route/merge aggregates -> LANChat operation replay reply
No intervention execution change
No batch execution change
```

Problem:

```text
Progress Update 147 made route/merge aggregates available in
intervention_batch_replay_summary, but LANChat operation replay replies still
only displayed routed, queued, persisted, and absorbed totals.  A host asking GM
for Runtime replay could not see how many pending interventions were
absorbable, non-absorbable, route candidates, or actually merged into the next
batch.
```

Change:

```text
LANChatAgentWorker._format_agent_runtime_replay_intervention_report() now
includes route and merge detail when available:

- route <absorbable>/<non_absorbable> items <route_requested_item_count>
- merge <merge_event_count> items <merged_item_count> absorbed <merge_absorbed_count>

The operation replay regression now seeds routed and merged OperationLog events
with safe aggregate payloads and asserts the LANChat reply includes those
counts.  verify_ultimate_plan.py now requires the formatter to keep these
fields wired.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_lanchat_runtime_guard.py: 179 tests passed
test_agent_runtime_phase1.py: 559 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing LF/CRLF warnings
```

Notes:

```text
This is a LANChat read-side disclosure slice. It does not change intervention
routing, batch merge execution, resource generation, scene import,
RuntimeCppBridge calls, EngineWriteGate invocation, LAN sync protocol, Quasar,
C++, CMake, Ninja, or CEF.
```

## 21. Progress Update 149 - LANChat operation replay exposes geometry facts

Status: completed in current non-native slice.

Scope:

```text
Phase 6 / User-visible geometry replay
OperationLog geometry_fact_replay_summary -> LANChat operation replay reply
No geometry execution change
No layout transform change
```

Problem:

```text
Progress Updates 144-146 made geometry facts available in RuntimeState,
Runtime reports, GM summaries, and OperationLog replay.  LANChat operation
replay replies still did not include the geometry replay summary, so a host
asking GM for Runtime replay could see interventions, VLM, layout, sync, and
resource facts while missing the AABB / overlap replay evidence.
```

Change:

```text
LANChatAgentWorker._handle_agent_runtime_operation_replay_query() now reads
geometry_fact_replay_summary and prints a geometry line in the replay reply.

The new _format_agent_runtime_replay_geometry_report() surfaces only safe
aggregates:

- patch count
- total geometry fact count
- AABB actor / skipped counts
- overlap issue count
- status and fact-type counts
- latest geometry event type/status/counts

The operation replay regression now seeds a sanitized geometry
runtime_state_patch_applied payload and asserts the LANChat reply includes the
geometry line.  verify_ultimate_plan.py now requires the operation replay
reply and formatter to keep this disclosure path wired.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_lanchat_runtime_guard.py: 179 tests passed
test_agent_runtime_phase1.py: 559 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing LF/CRLF warnings
```

Notes:

```text
This is a LANChat read-side disclosure slice. It does not change geometry tool
execution, layout transform behavior, RuntimeCppBridge calls, EngineWriteGate
invocation, LAN sync protocol, Quasar, C++, CMake, Ninja, or CEF.
```

## 22. Progress Update 150 - Runtime tool manifest legacy-main boundary gate

Status: completed in current non-native slice.

Scope:

```text
Phase 0 / Phase 2 / Phase 8 boundary hardening
ToolRegistry manifest safety
verify_ultimate_plan.py static gate only
No ToolCall execution change
No RuntimeState behavior change
```

Problem:

```text
AgentRuntime already rejects legacy workflow main-control tools through
ToolDefinition validation and regression tests, but the repeatable
verify_ultimate_plan.py gate did not explicitly require the Runtime tool
manifest boundary tests to remain present, nor did it inspect registered tool
manifest descriptions for accidental legacy main-control exposure.

During Agent-native decomposition, this is a risk because a future tool could
reintroduce SceneComposer / ProgressiveWorkflow as a manifest-visible big tool
without changing the ordinary direct-entry scans.
```

Change:

```text
verify_ultimate_plan.py now parses agent_runtime/tools.py with AST and checks
only actual registry.register(..., description=...) manifest entries for
legacy main-control tokens:

- legacy.scene_compose
- legacy.progressive_compose
- legacy.workflow_orchestrator
- SceneComposer.compose
- ProgressiveWorkflow
- run_progressive_workflow

The gate also requires the existing Phase 1 regression tests to stay present:

- test_tool_definition_rejects_legacy_workflow_main_control_tools
- test_tool_registry_manifest_does_not_expose_legacy_workflow_main_control_tools

The scan intentionally checks registered manifest fields rather than comments
or module-level documentation, so architecture notes can still mention the old
systems while user/tool-facing capability metadata stays clean.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
test_agent_runtime_phase1.py: 559 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Notes:

```text
This is a verifier hardening slice. It does not change ToolRegistry runtime
registration behavior, ToolCallGraph execution, RuntimeGuard authorization,
RuntimeState apply_patch, provider routing, SceneComposer, ProgressiveWorkflow,
GenerationScheduler, RuntimeCppBridge, EngineWriteGate, LAN sync protocol,
Quasar, C++, CMake, Ninja, or CEF.
```

## 23. Progress Update 151 - Queue enqueue item drafts become ToolCall facts

Status: completed in current non-native slice.

Scope:

```text
Phase 5 execution scheduling decomposition
ToolCallGraph queue enqueue planning
RuntimeState custom_queue_facts
No native build
No Quasar changes
No queue persistence behavior change
```

Problem:

```text
AgentRuntime.enqueue_planned_batches() already persisted planned batch queue
state through runtime.scene_plan.planned_batches.enqueue, but the queue item
drafts were still assembled inline in Python immediately before the write.

That left one Phase 5 scheduling decision outside the ToolCallGraph audit
surface: the Runtime could enqueue graph facts safely, but the queue item
draft itself was not yet a planning ToolCall result.
```

Change:

```text
Added runtime.queue.plan_enqueue_items as a read-only PLAN tool:

- required args: room_id, graph_refs
- consumes: tool_graph_queue at room scope
- produces: custom_queue_facts
- emits safe enqueue item drafts under enqueue_item_drafts

AgentRuntime.enqueue_planned_batches() now calls this planning tool before the
existing persistence write. The existing runtime.scene_plan.planned_batches.enqueue
write tool remains the only state commit path for batch_plans, tool_graphs and
tool_graph_queue.

If the planning tool is unavailable, fails, or returns incomplete drafts,
AgentRuntime falls back to the existing queue item shape. This keeps the current
running path stable while moving the normal path toward Agent-native ToolCall
facts.

The custom fact uses target_graph_ref instead of graph_id to avoid leaking
internal execution graph identifiers through user/report-safe payload fields.
The internal queue state still receives graph_id only at the controlled Runtime
write boundary.
```

Tests and gates:

```text
test_agent_runtime_phase1.py now covers:

- direct runtime.queue.plan_enqueue_items execution
- custom_queue_facts enqueue draft persistence
- no direct tool_graph_queue write from the planning tool
- enqueue_planned_batches invoking runtime.queue.plan_enqueue_items
- ToolRegistry manifest metadata for runtime.queue.plan_enqueue_items

verify_ultimate_plan.py now requires:

- runtime.queue.plan_enqueue_items in agent_runtime/tools.py
- AgentRuntime._plan_queue_items_via_tool_graph()
- queue_item_plan_tool_failed fallback logging
- test_queue_enqueue_item_planning_tool_records_safe_drafts_without_persisting_queue
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py ^
  editor/plugins/AITool/services/agent_runtime/core.py ^
  editor/plugins/AITool/services/test_agent_runtime_phase1.py ^
  editor/plugins/AITool/services/verify_ultimate_plan.py

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_agent_runtime_phase1.py: 560 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This slice does not yet make the real provider execution loop fully Agent-native.
The remaining Phase 5/Phase 6 work is still to retire more execution decisions
from SceneComposer / ProgressiveWorkflow and route real image/model/import/review
batch execution through ToolCallGraph nodes with F5 evidence.
```

## 24. Progress Update 152 - Batch execution graph replaces mock graph on main queue paths

Status: completed in current non-native slice.

Scope:

```text
Phase 5 execution graph naming and boundary hardening
AgentRuntime enqueue_scene_plan / enqueue_planned_batches / enqueue_pending_intervention_batch
ToolCallGraph construction path
No provider behavior change
No native build
No Quasar changes
```

Problem:

```text
The AgentRuntime main queue paths were already building a real batch execution
ToolCallGraph containing scene snapshot, extraction, classification, asset,
placement, geometry, import, VLM checkpoint and review nodes.

However the method was still named _build_mock_graph(), and the three main
enqueue paths called that mock-named entry directly. This was dangerous for the
Agent-native rewrite because future tasks could misread the current main graph
as disposable test scaffolding, or keep adding real execution behavior under a
mock boundary.
```

Change:

```text
Added the formal AgentRuntime._build_batch_execution_graph() entry and moved
the main graph construction body there.

Updated the three Runtime queue entry points to call the formal graph builder:

- enqueue_scene_plan
- enqueue_planned_batches
- enqueue_pending_intervention_batch

Kept _build_mock_graph() only as a compatibility wrapper that delegates to
_build_batch_execution_graph(). Regression tests now call the formal graph
builder directly.

verify_ultimate_plan.py now statically checks that the three main queue entry
points use _build_batch_execution_graph() and do not call _build_mock_graph().
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py ^
  editor/plugins/AITool/services/test_agent_runtime_phase1.py ^
  editor/plugins/AITool/services/verify_ultimate_plan.py

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_agent_runtime_phase1.py: 560 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This is a boundary and naming hardening slice. It does not yet remove the
compatibility wrapper, and it does not change the real provider execution loop.
Next Phase 5 work should continue moving real execution scheduling decisions
and provider/result handling into ToolCallGraph facts and RuntimeState evidence.
```

## 25. Progress Update 153 - Legacy mock graph wrapper removed

Status: completed in current non-native slice.

Scope:

```text
Phase 5 execution graph boundary cleanup
AgentRuntime batch execution graph entry
Regression and verifier hardening
No provider behavior change
No native build
No Quasar changes
```

Problem:

```text
Progress Update 152 moved all main queue paths to
AgentRuntime._build_batch_execution_graph(), but kept _build_mock_graph() as a
compatibility wrapper.

After scanning the current repository, the only remaining non-document
reference was that wrapper definition itself. Keeping a mock-named compatibility
entry after the main paths had moved creates a misleading extension point for
future Agent tasks and weakens the invariant that Runtime execution graphs are
formal ToolCallGraph units rather than mock scaffolding.
```

Change:

```text
Removed AgentRuntime._build_mock_graph().

test_agent_runtime_phase1.py now has a structural regression test confirming:

- AgentRuntime exposes _build_batch_execution_graph
- AgentRuntime no longer exposes _build_mock_graph

verify_ultimate_plan.py now fails if:

- AgentRuntime keeps a def _build_mock_graph(...) wrapper
- enqueue_scene_plan / enqueue_planned_batches / enqueue_pending_intervention_batch
  do not call _build_batch_execution_graph
- any of those main queue entry points call _build_mock_graph
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py ^
  editor/plugins/AITool/services/test_agent_runtime_phase1.py ^
  editor/plugins/AITool/services/verify_ultimate_plan.py

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_agent_runtime_phase1.py: 561 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This removes the misleading mock graph entry point, but it does not yet convert
real provider result handling or all remaining execution decisions into
dedicated ToolCallGraph facts. Those remain Phase 5 / Phase 6 work and still
need F5 evidence once connected to real image/model/import/review providers.
```

## 26. Progress Update 154 - Default mock import tool removed from Runtime registry

Status: completed in current non-native slice.

Scope:

```text
Phase 5 import boundary cleanup
AgentRuntime default ToolRegistry registration
runtime.actor.import_batch remains the official import path
No provider behavior change
No native build
No Quasar changes
```

Problem:

```text
AgentRuntime still registered mock.import_actor through the default Runtime
tool registration path. The formal batch execution graph no longer uses this
tool, but keeping it in the default registry left a stale write-capable mock
entry beside runtime.actor.import_batch.

That conflicts with the Agent-native direction: user/runtime execution should
move through structured batch import planning and runtime.actor.import_batch,
not an old single-actor mock import adapter.
```

Change:

```text
Renamed AgentRuntime._register_default_mock_tools() to
_register_default_runtime_tools().

Removed default registration of mock.import_actor.

Removed AgentRuntime._mock_import_actor().

test_agent_runtime_phase1.py now verifies:

- AgentRuntime default manifest does not expose mock.import_actor
- AgentRuntime exposes _register_default_runtime_tools
- AgentRuntime no longer exposes _register_default_mock_tools
- AgentRuntime no longer exposes _mock_import_actor

verify_ultimate_plan.py now fails if core.py reintroduces:

- def _register_default_mock_tools(...)
- def _mock_import_actor(...)
- mock.import_actor in the default Runtime core path

Local unit tests may still register mock.import_actor inside isolated
ToolRegistry instances to exercise generic RuntimeGuard behavior. That is test
scaffolding only, not a default Runtime capability.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py ^
  editor/plugins/AITool/services/test_agent_runtime_phase1.py ^
  editor/plugins/AITool/services/verify_ultimate_plan.py

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_agent_runtime_phase1.py: 561 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This removes the old default mock import capability. The next execution-plane
work is still to continue replacing real provider/result handling decisions
with explicit ToolCallGraph facts and RuntimeState evidence, then validate the
real image/model/import/review loop in F5.
```

## 27. Progress Update 155 - Import batch manifest no longer advertises mock import

Status: completed in current non-native slice.

Scope:

```text
Phase 5 import manifest cleanup
ToolRegistry capability metadata
runtime.actor.import_batch
No handler behavior change
No provider behavior change
No native build
No Quasar changes
```

Problem:

```text
After removing the default mock.import_actor tool, runtime.actor.import_batch
still had a stale manifest description:

"Create a mock actor import result for a whole Runtime batch."

That description was misleading because runtime.actor.import_batch is now the
official batch import tool. It may use a default Runtime provider in tests or a
configured engine import provider in real integration, but it is no longer a
mock tool entry and should not advertise mock semantics.
```

Change:

```text
Changed runtime.actor.import_batch description to:

"Import a whole Runtime batch through the configured actor import provider."

test_agent_runtime_phase1.py now asserts:

- the public manifest for runtime.actor.import_batch does not expose "mock"
- tools.py contains the formal Runtime batch import description
- tools.py no longer contains the stale mock import description

verify_ultimate_plan.py now extends the ToolRegistry manifest AST scan to reject
mock import phrases in registered tool names/descriptions:

- mock.import_actor
- mock actor import
- mock import
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py ^
  editor/plugins/AITool/services/test_agent_runtime_phase1.py ^
  editor/plugins/AITool/services/verify_ultimate_plan.py

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
test_agent_runtime_phase1.py: 561 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This is a manifest/capability metadata cleanup. It does not change import
provider selection, EngineWriteGate behavior, actor import result parsing, or
F5 real provider execution. Those remain part of the larger Phase 5/6 runtime
provider and execution-loop migration.
```

## 28. Progress Update 156 - Empty resource provider results become RuntimeState failed facts

Status: completed in current non-native slice.

Scope:

```text
Phase 5 provider/result handling decomposition
runtime.asset.image.prepare
runtime.asset.model.prepare
RuntimeState image_resource_plans / model_resource_plans
Batch resource flow summary read side
No real provider invocation change
No native build
No Quasar changes
```

Problem:

```text
Previous Phase 5 slices moved batch graph construction and import capability
metadata toward AgentRuntime, but one provider/result edge still stayed too
close to old workflow semantics:

- if an image/model resource provider returned an empty result for requested
  items, the tool failed without writing per-item RuntimeState evidence;
- batch_resource_flow_summary could therefore see the batch as waiting or only
  infer failure from runtime events/OperationLog;
- F5 diagnosis of "resource provider produced nothing" still depended too much
  on logs rather than RuntimeState facts.
```

Change:

```text
runtime.asset.image.prepare and runtime.asset.model.prepare now convert empty
provider results into explicit failed resource entries for each requested item:

- image resources use status=failed and source=image_resource_unavailable
- model resources use status=failed and source=model_resource_unavailable

The tools still produce only their declared RuntimeState keys:

- image_resource_plans
- model_resource_plans

No new side-channel state key was introduced.  The existing
batch_resource_flow_summary now sees failed status counts directly from
RuntimeState and marks the batch resource flow as failed instead of leaving it
ambiguous.

The resource tool manifest descriptions were also corrected from stale
"without calling providers" wording to provider/fallback wording.
```

Tests / gates:

```text
test_agent_runtime_phase1.py now covers:

- empty image provider result records failed image_resource_plans facts
- empty model provider result records failed model_resource_plans facts
- resource events remain user-visible warnings with failed_count
- batch_resource_flow_summary reports the affected batch as failed

verify_ultimate_plan.py now requires:

- _failed_resource_entries helper
- image_resource_unavailable and model_resource_unavailable facts
- the two empty-provider regression tests
- no resource tool manifest phrase claiming providers are never called
```

Validation:

```text
python -B -m unittest ^
  editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_resource_provider_result_records_failed_resource_facts ^
  editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted empty-provider tests: 2 passed
test_agent_runtime_phase1.py: 562 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice makes empty resource provider results factual in RuntimeState, but
it does not yet make the full real provider execution loop Agent-native.
Remaining Phase 5/6 work still includes real image/model/import/review provider
execution through ToolCallGraph nodes, real provider failure/timeout evidence,
EngineWriteGate-backed import results, VLM/geometry review result evidence, and
F5 validation of the complete real-provider loop.
```

## 29. Progress Update 157 - Batch resource flow preserves explicit zero import readiness

Status: completed in current non-native slice.

Scope:

```text
Phase 5 provider/result read-side correctness
RuntimeState batch_resource_flow_summary
model_resource_plans failed status
custom_import_facts ready_count
No import execution behavior change
No native build
No Quasar changes
```

Problem:

```text
Progress Update 156 made empty model provider results factual in
model_resource_plans by recording per-item failed entries.

However, the batch resource flow read side still used an unsafe fallback:

import_ready = ready_count or actor_count

That means an explicit ready_count=0 from the actor import planning fact was
treated as missing and replaced with actor_count.  In reports, a batch whose
model resources were all failed could still appear to have import_ready_count
equal to the number of planned actors.
```

Change:

```text
_batch_resource_flow_summary_for_plan() now distinguishes:

- ready_count key exists with value 0
- ready_count key is absent

Only absent ready_count falls back to actor_count.  Explicit ready_count=0 is
preserved, so failed model resources no longer produce misleading import-ready
evidence.

The empty model provider regression now asserts:

- model_resource_plans records failed entries
- batch_resource_flow_summary status is failed
- model_status_counts is failed
- import_ready_count is 0
- import_failed_count equals the planned actor count
```

Tests / gates:

```text
verify_ultimate_plan.py now statically rejects the old
ready_count-or-actor_count pattern and requires the explicit ready_count key
check in _batch_resource_flow_summary_for_plan().
```

Validation:

```text
python -B -m unittest ^
  editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted model empty-provider test: passed
test_agent_runtime_phase1.py: 562 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This is a RuntimeState/report read-side correctness slice.  It does not yet
replace the real import provider loop, EngineWriteGate-backed actor import
result parsing, or F5 real-provider execution evidence.  Those remain Phase 5/6
work.
```

## 30. Progress Update 158 - Actor import plan status reflects model resource readiness

Status: completed in current non-native slice.

Scope:

```text
Phase 5 import planning facts
runtime.actor.plan_import_batch
RuntimeState custom_import_facts
model_resource_plans failed status
No actor import execution behavior change
No native build
No Quasar changes
```

Problem:

```text
runtime.actor.plan_import_batch already inspected model_resource_plans and
computed per-actor model_ready values, but the import planning fact always used
status=planned.

After empty model provider results became explicit failed resource facts, this
left a mismatch:

- planned_actors could all have model_ready=false
- ready_count could be 0
- the import plan fact still said planned

That weakened RuntimeState as the execution fact source and made downstream
reports less direct than they should be.
```

Change:

```text
runtime.actor.plan_import_batch now derives import plan status from model
resource readiness:

- actor_count > 0 and ready_count == 0 -> status=failed
- 0 < ready_count < actor_count -> status=partial
- all ready, or no actor items -> status=planned

This does not change the actual actor import execution path.  It only makes the
RuntimeState import planning fact truthful before the write tool runs.
```

Tests / gates:

```text
The empty model provider regression now asserts:

- custom_import_facts[batch_id].status == failed
- custom_import_facts[batch_id].ready_count == 0
- custom_import_facts[batch_id].actor_count == planned actor count

verify_ultimate_plan.py now requires the failed and partial import plan status
tokens in the Runtime tool layer.
```

Validation:

```text
python -B -m unittest ^
  editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted model empty-provider test: passed
test_agent_runtime_phase1.py: 562 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice makes import planning facts more truthful, but it does not yet
replace the real EngineWriteGate-backed import provider loop or parse real
engine actor import results into RuntimeState.  Those remain Phase 5/6 work and
still require F5 evidence.
```

## 31. Progress Update 159 - Actor import results are persisted as RuntimeState facts

Status: completed in current non-native slice.

Scope:

```text
Phase 5 import result evidence
runtime.actor.import_batch
RuntimeState custom_import_facts
Batch resource flow result read side
No real engine provider behavior change
No native build
No Quasar changes
```

Problem:

```text
runtime.actor.import_batch previously wrote imported actors to RuntimeState and
returned import_results in ToolResult payload, but the actual import result was
not persisted as a RuntimeState fact.

That meant:

- actor creation state existed;
- import planning facts existed;
- but import result evidence was still tied to the transient ToolResult payload.

This was not aligned with the Agent-native invariant that RuntimeState and
OperationLog must be the replayable evidence source before user reports.
```

Change:

```text
runtime.actor.import_batch now declares both produced state keys:

- actors
- custom_import_facts

On successful or partial import, it writes:

custom_import_facts[f"{batch_id}:actor_import_result"]

with safe fields:

- plan_id
- batch_id
- actor_count
- ready_count
- imported_count
- failed_count
- status: imported / partial / failed
- source: runtime_actor_import_result
- sanitized import_results

_batch_resource_flow_summary_for_plan() now prefers actor_import_result when it
exists, falling back to actor_import_plan only when no result fact has been
written yet.
```

Tests / gates:

```text
test_agent_runtime_phase1.py now asserts the successful batch graph writes an
actor_import_result fact with imported status, imported_count, failed_count=0,
and source=runtime_actor_import_result.

The Runtime tool manifest regression now expects runtime.actor.import_batch to
produce both actors and custom_import_facts.

verify_ultimate_plan.py now requires:

- runtime.actor.import_batch manifest presence
- produces_state=("actors", "custom_import_facts")
- runtime_actor_import_result
- :actor_import_result
```

Validation:

```text
python -B -m unittest ^
  editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_batch_graph_consumes_scene_snapshot_for_placement_and_import ^
  editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_tool_registry_manifest_exposes_safe_capability_metadata

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted batch graph and manifest tests: passed
test_agent_runtime_phase1.py: 562 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice persists Runtime actor import result facts, but it still relies on
the current actor import provider contract.  Real EngineWriteGate-backed import
provider integration, true C++ result normalization, multiplayer actor sync
evidence, and F5 validation remain Phase 5/6 work.
```

### Progress Update 160 - failed actor import results are now RuntimeState facts

Goal:

```text
Close the next Phase 5 evidence gap: when the actor import provider returns a
sanitized failure result but no actors, RuntimeState must still keep the real
import failure as a replayable fact.  The system must not create fake actors,
and reports must derive failed batch status from facts rather than from a lost
ToolResult failure.
```

Change:

```text
runtime.actor.import_batch now treats "provider returned import_results but no
actors" as:

- no actor creation
- a successful recording of the failed real import result
- custom_import_facts[f"{batch_id}:actor_import_result"] with:
  - status: failed
  - actor_count
  - ready_count: 0
  - imported_count: 0
  - failed_count
  - source: runtime_actor_import_result
  - sanitized import_results

The normal success / partial success branch now uses the same
_actor_import_result_fact() helper, keeping imported / partial / failed fact
shape consistent.
```

Tests / gates:

```text
test_actor_import_provider_empty_actor_result_records_failed_import_fact
now covers a provider response with actors={} and failed import_results.  It
asserts:

- RuntimeState actors stay empty
- actor_import_result fact is recorded with status=failed
- import_ready_count is 0
- import_failed_count matches requested objects
- batch_resource_flow_summary marks the batch failed
- report import_summary carries failed_count

test_engine_actor_import_provider_missing_model_resource_fails_runtime_graph
was updated to match the current fact-first runtime contract: the graph may
complete after recording failed import facts, while the batch/report status
still shows failed and no actor is created.

verify_ultimate_plan.py now requires:

- def _actor_import_result_fact(
- actor import failed and result fact recorded
```

Validation:

```text
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py \
  AgentRuntimePhase1Tests.test_actor_import_provider_empty_actor_result_records_failed_import_fact \
  AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider \
  AgentRuntimePhase1Tests.test_engine_actor_import_provider_requires_engine_actor_identity

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py \
  AgentRuntimePhase1Tests.test_engine_actor_import_provider_missing_model_resource_fails_runtime_graph \
  AgentRuntimePhase1Tests.test_actor_import_provider_empty_actor_result_records_failed_import_fact

python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- . ':(exclude)editor/plugins/AITool/Quasar'
```

Result:

```text
targeted actor import failure/partial tests: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 179 tests passed
docs/probes/test_v3_f5_log_check.py: passed
docs/probes/test_v3_f5_quick_gate.py: passed
syntax compile current Agent-native modules: passed
all static Agent-native gates: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
The runtime now records failed real import outcomes as facts, but the graph
status can still be completed when it successfully records a failed engine
write.  This is intentional for the fact-first slice; later Phase 5/6 work
should decide whether ToolCallGraph status should become semantic partial /
failed when downstream fact summaries contain failed actor imports.
```
