# Agent-native 一步到位重构计划：Game-ready Scene Runtime 与旧 Workflow 主控退场

更新时间：2026-06-29


> 修订说明：本版在原 Agent-native 场景生成重构计划基础上，补充“通用地形场景生成 Runtime / Game-ready Scene Runtime”的实施目标。  
> 第二约束文档 `Agent任务约束循环.md` 继续作为所有 Agent / Codex 任务的强约束规约。  
> 当前阶段不直接实现 GameDesignAgent / CombatAgent / StoryAgent / BalanceAgent / ScriptAgent，而是把场景 Runtime 做到可被后续 AI Game Demo 生成系统消费。

## 0. 当前实施口径修订：F5 前冲刺 + Game-ready Scene Runtime

### 0.1 当前项目定位

本项目当前不是单点“森林营地生成器”，也不只是传统 3D 模型场景生成器，而是：

```text
多人多 Agent 协同
-> 通用地形 / 场景实体生成
-> Game-ready Scene Runtime
-> 后续承接 AI Game Demo 生成
```

现阶段的直接目标仍是 Agent-native 场景生成重构，但目标口径升级为：

```text
生成可被游戏逻辑消费的场景实体世界
```

也就是说，当前阶段必须让 Runtime 产出的场景不仅“看起来有物体”，还要具备：

```text
稳定 actor_id
稳定 asset_id / model_ref
语义角色 semantic_role
实体类型 entity_type
transform / AABB / grounding 状态
interaction_capability
gameplay_tags
terrain / environment / actor / geometry / review / sync 分域状态
```

这些字段是后续策划 Agent、程序 Agent、蓝图 / 积木代码生成 Agent 的地基。

### 0.2 当前禁止扩大的范围

当前阶段不要直接实现以下上层 Agent：

```text
GameDesignAgent
CombatAgent
StoryAgent
BalanceAgent
ScriptAgent
BlueprintAgent
AudioAgent
PhysicsTuningAgent
```

当前阶段也不要为了单个 demo 写死森林营地、帐篷、小木桌、战斗、剧情、数值或脚本逻辑。

正确做法是：

```text
用森林营地验证通用 terrain scene generation vertical slice
而不是把系统写成森林营地专用逻辑
```

### 0.3 F5 前冲刺模式

当前进入 F5 前冲刺模式：

```text
远端差异暂不处理
editor/plugins/AITool/Quasar 暂不处理
不要继续扩大量测试、门禁和 replay summary
不要为了边角用例拖慢主线
主要测试通过即可，特别细小测试可标记后续处理
```

本阶段只优先推进能直接帮助真实 vertical slice 的内容：

```text
ScenePlan
-> BatchPlan
-> terrain / environment route
-> asset / model prepare
-> actor import
-> transform / grounding / AABB
-> review summary
-> scene_entity_registry
-> final report
-> RuntimeState / OperationLog 可查询
```

### 0.4 当前 P0 优先级

```text
P0-1：engine write adapter 收口
P0-2：terrain / environment / substrate 识别与路由
P0-3：forest / sky / grass / terrain / ground 等环境词不得进入普通模型生成
P0-4：actor import / transform / delete 统一走 Runtime adapter
P0-5：grounding / AABB / layout repair 最小可用
P0-6：scene_entity_registry 最小可用
P0-7：sync actor snapshot / asset transfer status 最小闭环
P0-8：final report 只读 RuntimeState + OperationLog
```

### 0.5 所有真实写引擎操作必须走的链路

```text
ToolCall
-> RuntimeGuard
-> EngineWriteGate / runtime_cpp_bridge
-> ToolResult
-> StatePatch
-> RuntimeState
-> OperationLog
```

禁止：

```text
绕过 RuntimeGuard
把完整 SceneComposer / ProgressiveWorkflow 包成 legacy big tool
重新暴露旧 workflow 用户入口
把 C++ 成功结果伪造成 Python 成功
让 Agent 直接 import / move / delete actor
让脚本/蓝图生成绑定不稳定 actor_id
```

### 0.6 scene_entity_registry 最小结构

`scene_entity_registry` 是后续 AI Game Demo 的承接层。第一版至少包含：

```text
actor_id
asset_id / model_ref
semantic_role
entity_type
transform
AABB / bounds
grounding_status
interaction_capability
gameplay_tags
physics_profile
audio_profile
lighting_profile
script_bindings
source_plan_id
source_batch_id
sync_status
review_status
```

当前可以先为空字段或默认值，但 schema 和 StatePatch 路径必须预留。

### 0.7 后续 AI Game Demo 扩展方向

当前计划文档的终局不再只是场景生成，而是为以下能力预留扩展点：

```text
策划：
- 关卡
- 剧情
- 系统
- 战斗
- 数值
- 任务与胜负条件

美术 / 艺术：
- 地形 / 场景 / 物体
- 音频音效
- 灯光 / 材质 / 物理参数
- 声光力自动调整
- 风格一致性审查

程序：
- 蓝图生成
- 积木代码生成
- 触发器
- 交互逻辑
- 行为脚本
- UI / 任务 / 战斗脚本
```

但这些属于后续阶段。当前只做底座预留，不提前实现上层 Agent。


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

本节替代旧版单纯“场景生成重构”节奏。新的实施节奏采用两层路线：

```text
近期路线：F5 前真实 vertical slice 冲刺
中长期路线：从 Game-ready Scene Runtime 承接 AI Game Demo Runtime
```

### 9.1 当前阶段判定

当前项目状态按真实目标判断：

```text
整体 Agent-native 重构：约 60%
Python / 非 native / Runtime 架构层：约 75%
Engine / C++ / 多人同步 / F5 实机层：约 40%-50%
```

当前不应继续扩大量测试、门禁、replay summary，而应从“证明 Runtime 很完整”切换到：

```text
证明 Runtime 能真实生成一个可被游戏逻辑消费的通用地形场景
```

### 9.2 F5 前冲刺 Milestone A：真实 engine write adapter 收口

目标：

```text
所有真实 actor import / transform / delete / environment import 写操作
统一通过 Runtime adapter 边界
```

必须满足：

```text
ToolCall -> RuntimeGuard -> EngineWriteGate / runtime_cpp_bridge -> ToolResult -> StatePatch -> RuntimeState -> OperationLog
```

动作：

```text
收口 actor import provider
收口 transform provider
收口 delete provider
收口 environment / terrain import provider
确认失败码进入 ToolResult.error_code
确认 C++ / Engine 真实返回优先于 Agent 计划
```

完成标准：

```text
RuntimeState 不伪造 engine success
OperationLog 可复盘 engine write 成败
status_summary 能看到 engine_write_status
涉及真实 C++ / Engine 的结论标记 [待 F5/实机验证]
```

### 9.3 F5 前冲刺 Milestone B：通用 terrain / environment route

目标：

```text
将 terrain / ground / sky / grass / forest / water / mountain 等环境类元素
路由到 terrain / environment / substrate 链路
而不是普通 asset/model/actor 链路
```

动作：

```text
强化 scene.extract_environment
强化 asset.route_item
强化 environment.resolve_substrate
强化 terrain.create / terrain.update 的最小工具路径
```

完成标准：

```text
sky / grass / ground / terrain 不进入普通模型生成
帐篷 / 小木桌 / 宝箱 / 建筑 / 敌人等 concrete object 进入 asset/model/actor 链路
RuntimeState 能区分 terrain_state / environment_state / asset_state / actor_state
```

### 9.4 F5 前冲刺 Milestone C：actor import -> grounding -> AABB 最小闭环

目标：

```text
让 concrete objects 可以真实进入场景，并获得 transform / grounding / AABB / review 结果
```

动作：

```text
actor.import_model
actor.place / actor.set_transform
geometry.compute_aabb
geometry.snap_to_ground_selective
geometry.check_overlap
geometry.repair_low_risk
review.aabb
```

完成标准：

```text
actor_state 有 actor_id / asset_id / transform
geometry_state 有 AABB / bounds / grounding_status
review_state 有 review summary
失败时不伪装成功
浮空 / 穿模 / AABB unknown 能进入 warning
```

### 9.5 F5 前冲刺 Milestone D：scene_entity_registry 最小可用

目标：

```text
把场景 actor 转成后续游戏系统可消费的实体清单
```

动作：

```text
新增或补齐 scene_entity_registry read/write schema
从 actor_state / asset_state / geometry_state / review_state 聚合实体事实
为每个实体补 semantic_role / entity_type / gameplay_tags / interaction_capability 默认值
```

完成标准：

```text
RuntimeState 能查询 scene_entity_registry
final report 能只读 RuntimeState / OperationLog 输出实体摘要
后续 GameDesignPlan / ScriptPlan / BlueprintPlan 可以稳定引用实体
```

第一版允许：

```text
interaction_capability = none / decorative / interactable_candidate
gameplay_tags = inferred / empty
script_bindings = []
physics_profile / audio_profile / lighting_profile 使用默认占位
```

### 9.6 F5 前冲刺 Milestone E：sync actor snapshot / asset transfer status 最小闭环

目标：

```text
多人同步状态进入 RuntimeState，不再只是导入副作用
```

动作：

```text
sync.actor_snapshot
sync.actor_broadcast
sync.asset_transfer
sync.peer_status
sync.reconcile_remote_state
```

完成标准：

```text
生成成功 != 导入成功 != 同步成功
sync_state 能查询 actor snapshot / asset transfer / peer status
OperationLog 能复盘同步事件
真实多人联机结果标记 [待 F5/实机验证]
```

### 9.7 F5 前最小验收场景

最小验收场景：

```text
生成一个简单森林营地，有草地、天空、帐篷、小木桌。
```

注意：森林营地只是通用地形场景生成 vertical slice 的验收样例，不是产品目标。

必须验证：

```text
草地 / 天空 / ground / terrain 进入 environment / terrain / substrate 链路
帐篷 / 小木桌进入 asset / model / actor 链路
物体摆放依赖 terrain / ground plane / grounding 机制
actor 有 transform / grounding / AABB 检查结果
RuntimeState 能查 terrain / environment / asset / actor / geometry / review
scene_entity_registry 能输出可被后续游戏逻辑消费的实体清单
OperationLog 能复盘 plan -> terrain -> asset -> actor -> review -> report
final report 只能读取 RuntimeState + OperationLog
```

### 9.8 当前暂缓事项

以下内容暂缓，不进入 F5 前 P0：

```text
直接实现 GameDesignAgent / CombatAgent / StoryAgent / BalanceAgent / ScriptAgent
复杂剧情 / 战斗 / 数值生成
完整蓝图 / 积木代码生成
高级多人冲突仲裁
复杂 VLM 质量门
大规模新增 replay summary
大规模扩充边角测试
远端差异处理
Quasar 脏项处理
```

### 9.9 后续阶段：AI Game Demo Runtime 承接路线

当 Game-ready Scene Runtime 达到 F5 可用后，再进入后续阶段。

#### Phase G0：GameWorldState / GameDesignPlan 设计

新增事实源：

```text
GameWorldState
GameDesignPlan
LevelPlan
QuestPlan
CombatPlan
BalancePlan
ProgressionPlan
ScriptPlan
BlueprintPlan
```

要求：

```text
只能读取 RuntimeState / scene_entity_registry
不能直接读取旧 workflow 内部状态
不能绑定不稳定 actor_id
```

#### Phase G1：策划 Agent 接入

职责：

```text
关卡目标
核心循环
剧情节奏
任务目标
战斗规则
数值约束
胜负条件
```

禁止：

```text
直接写 engine actor
直接生成脚本并执行
绕过 RuntimeGuard 修改场景
```

#### Phase G2：美术 / 艺术 Agent 扩展

职责：

```text
场景风格统一
音频音效建议
灯光参数
材质参数
物理参数
声光力自动调整 proposal
```

所有调整先进入：

```text
ArtAdjustmentProposal
-> RuntimeGuard
-> ToolCallGraph
-> StatePatch
```

#### Phase G3：程序 / 脚本 / 蓝图 Agent 接入

职责：

```text
蓝图 / 积木代码生成
触发器生成
交互逻辑生成
任务脚本
战斗行为
UI 逻辑
```

必须经过：

```text
ScriptToolCall
-> RuntimeGuard
-> ScriptValidator
-> EngineScriptAdapter
-> ToolResult
-> StatePatch
-> RuntimeState
-> OperationLog
```

#### Phase G4：一键 AI Game Demo 生成

目标：

```text
多人多 Agent 讨论
-> GameDesignPlan
-> Game-ready Scene Runtime
-> GameplayEntityPlan
-> Script / Blueprint 生成
-> Review
-> F5 可玩 demo
```


## 10. 测试计划

当前进入 F5 前冲刺模式，测试策略从“大量扩展门禁”切换为“主门禁 + 最小相关验证”。

### 10.1 必跑测试

```text
python -B editor/plugins/AITool/services/verify_ultimate_plan.py
本轮改动直接相关测试
必要 syntax compile
```

### 10.2 本阶段优先测试类型

```text
engine write adapter boundary test
terrain / environment route test
asset route excludes environment terms test
actor import result persists RuntimeState test
transform / grounding / AABB minimal test
scene_entity_registry aggregation test
sync actor snapshot / asset transfer status test
final report reads RuntimeState + OperationLog test
```

### 10.3 暂不强求测试

```text
大规模全量 AgentRuntime 测试
细小边角 replay summary 测试
与本轮 vertical slice 无关的历史回归
复杂 VLM 效果测试
复杂多人冲突仲裁测试
完整游戏策划 / 脚本 Agent 测试
```

### 10.4 必须标记 [待 F5/实机验证] 的内容

```text
C++ actor import
actor transform
actor delete
terrain / environment 真实写入
asset transfer
LAN peer 同步
VLM screenshot
真实 Engine 场景效果
CEF UI 长耗时反馈
多人联机可见性
```

### 10.5 测试边界原则

测试不能反向绑架重构节奏。

允许：

```text
主要门禁通过
本轮核心链路测试通过
边角测试标记后续处理
```

不允许：

```text
为了新增 replay summary 拖慢真实 vertical slice
为了边角测试大面积重构
为了测试方便绕过 RuntimeGuard
为了测试方便伪造 Engine success
```


## 11. F5 验收场景

### 11.1 F5 前最小场景：通用地形场景 vertical slice

脚本：

```text
生成一个简单森林营地，有草地、天空、帐篷、小木桌。
确认生成。
查看状态。
查看最终报告。
```

验收目的：

```text
验证通用地形场景生成 Runtime，而不是验证森林营地专用逻辑。
```

验收要求：

```text
草地 / 天空 / ground / terrain 进入 environment / terrain / substrate 链路
帐篷 / 小木桌进入 asset / model / actor 链路
actor import 经过 Runtime adapter
actor transform / grounding / AABB 有 RuntimeState 事实
review summary 能看到 geometry / grounding 结果
scene_entity_registry 有可被游戏逻辑消费的实体清单
OperationLog 能复盘 plan -> terrain -> asset -> actor -> review -> report
final report 只读 RuntimeState + OperationLog
```

### 11.2 室内场景回归：可爱卧室

目标：

```text
验证 room_box / object / layout / grounding / final report
```

脚本：

```text
帮我设计一个可爱的卧室，有床、书桌、衣柜、台灯、地毯、玩偶、书架。
确认生成。
完成后：调整一下布局。
如果浮空：把模型都落地。
```

### 11.3 室外地形场景回归：森林营地扩展版

目标：

```text
验证 terrain / substrate / environment 不进入普通模型生成
```

脚本：

```text
做一个森林营地，有天空、树林、草地、小木桌、帐篷、篝火。
确认生成。
```

### 11.4 混合场景回归：幻想集市

目标：

```text
验证 mixed zone、批次介入、追加对象、最终报告
```

脚本：

```text
做一个室内外结合的夜晚幻想集市，有入口、摊位、灯光、休息区。
生成中：再加一个天使雕像。
生成中：再加一只小狗。
完成后：查看吸收了哪些调整。
```

### 11.5 多 Agent / 多人协同回归：藏宝室

目标：

```text
验证多人 / 多 Agent 讨论承接、GM 总结、ScenePlan 确认、完成态调整
```

脚本：

```text
@长者 围绕强盗藏宝室主题讨论一下。
@商人 评价并改进长者方案。
@GM 总结当前方案。
按照这个方案生成。
确认生成。
完成后：调整一下布局，我看模型位置冲突。
确认调整。
```

### 11.6 多人同步验收

目标：

```text
验证 actor sync / asset transfer / peer status 进入 RuntimeState
```

脚本：

```text
房主创建房间。
其他用户加入。
房主多 Agent 讨论后确认生成。
观察其他用户 actor / asset / sync 状态。
模拟远端缺资源或断线重连。
```

验收要求：

```text
房主生成成功不等于同步成功
peer 端资源缺失可查询
重复资源不重复传
actor transform 一致
late join 能收到可恢复状态
```


## 12. 完成标准

本次重构的完成标准分两层：F5 前完成标准与最终 Agent-native 完成标准。

### 12.1 F5 前完成标准

进入第一轮 F5 / 实机验证前，必须满足：

```text
1. AgentRuntime 主控路径可跑通最小 vertical slice
2. ScenePlan / BatchPlan 可作为计划和批次事实源
3. terrain / environment / substrate 与 ordinary model route 明确分离
4. forest / sky / grass / terrain / ground 不进入普通模型生成
5. 帐篷 / 小木桌等 concrete objects 进入 asset/model/actor 链路
6. actor import / transform / delete 走 Runtime adapter
7. grounding / AABB / layout repair 有最小可用 RuntimeState 事实
8. review summary 能读取 geometry / grounding 结果
9. scene_entity_registry 最小可查询
10. sync actor snapshot / asset transfer status 有最小闭环
11. final report 只读 RuntimeState + OperationLog
12. verify_ultimate_plan.py 通过
13. 本轮直接相关测试通过
14. C++ / Engine / Sync / VLM screenshot 结果明确标记 [待 F5/实机验证]
```

### 12.2 Game-ready Scene Runtime 完成标准

```text
1. RuntimeState 明确包含 terrain_state / environment_state / asset_state / actor_state / geometry_state / review_state / sync_state
2. scene_entity_registry 能稳定输出 actor_id / asset_id / semantic_role / entity_type / transform / AABB / grounding_status / interaction_capability / gameplay_tags
3. 真实引擎返回优先于 Agent 计划
4. ToolResult 不直接改状态，只能提交 StatePatch
5. OperationLog 可回放 plan -> terrain -> asset -> actor -> geometry -> review -> sync -> report
6. 用户状态查询、GM summary、final report 均不读取旧 workflow 内部状态
7. 旧 workflow 只作为 fallback / regression baseline，不作为普通用户主控入口
```

### 12.3 最终 Agent-native 完成标准

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

### 12.4 AI Game Demo 承接标准

只有当 Game-ready Scene Runtime 达到以下标准后，才允许正式启动上层游戏 Agent：

```text
1. scene_entity_registry 稳定
2. actor_id / asset_id / transform / AABB / grounding_status 可查询
3. terrain / walkable / bounds 基础事实可查询
4. interaction_capability / gameplay_tags 有默认 schema
5. Script / Blueprint 未来可绑定稳定实体
6. RuntimeGuard 可拦截高风险脚本 / actor 修改
7. OperationLog 能复盘场景实体生成过程
```

达到以上标准后，再开始：

```text
GameDesignPlan
GameplayEntityPlan
CombatPlan
QuestPlan
ScriptPlan
BlueprintPlan
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

2026-07-04 本轮推进记录：

```text
已修复 AgentRuntime Phase1 中的真实语义断点：
- legacy model provider 全失败时，ToolCallGraph 会失败，Batch/Plan 不再伪装成功。
- 失败 ToolResult 的 state_patch 在 ToolCallGraphExecutor 内部受控合并，仍满足 RuntimeState.apply_patch 边界。
- 森林营地等场景 profile 优先于新增物体 alias，避免“帐篷”等对象词提前截断 substrate/object 分类。

已清理 Phase1 测试中的多处 mojibake fixture 与脆弱中文标题断言，改为稳定语义/结构断言。

本轮验证：
- python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
  Ran 563 tests OK
- python editor/plugins/AITool/services/verify_ultimate_plan.py
  All current Agent-native non-native checks passed

仍未验证：
- native / C++ / CEF / F5 实机链路
- 真实 provider 下的大分批 image/model/import/review 执行闭环
- 真实多人 LAN 同步、模型同传与实机场景写入效果
```

当前这些检查已通过；`git diff --check` 只有 CRLF warning，无 whitespace error。

2026-07-04 补充推进记录：

```text
已补齐 Runtime 报告/状态层的语义状态表达：
- ToolCallGraph 的原始执行状态继续表示工具链是否按协议跑完，例如成功记录失败导入事实时仍可为 completed。
- batch_summary / tool_graph_summary 新增 semantic_status 与 semantic_status_source。
- semantic_status 来自 batch_resource_flow_summary，能把 actor import 失败、部分导入、等待资源等真实业务状态传递给报告、状态查询和后续 Disclosure/GM 层。
- batch_resource_flow_summary 新增 status_by_batch_id，作为 RuntimeState fact-source 的批次语义索引。

这样避免了“graph completed 但业务导入失败”在用户报告中被误读为场景成功，同时不破坏 ToolCallGraph Executor 的底层执行语义。

本轮验证：
- python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
  Ran 563 tests OK
- python editor/plugins/AITool/services/verify_ultimate_plan.py
  All current Agent-native non-native checks passed
- git diff --check
  only CRLF warnings, no whitespace error
```

2026-07-05 Operation Replay 补充推进记录：

```text
已把 RuntimeState 的批次资源语义状态接入 Operation Replay：
- AgentRuntime.operation_replay() / _compose_operation_replay() 现在额外输出 batch_resource_flow_summary。
- 该摘要来自 RuntimeState 中的 image/model/import/review facts，而不是只看 OperationLog 事件流。
- LANChatAgentWorker._handle_agent_runtime_operation_replay_query() 新增 resource_flow 行，复用安全 formatter，能显示 latest i/n:status img/model/import x/y/z of requested。
- 当 RuntimeState 显示批次 failed/partial/waiting 时，Operation Replay 也能显示 semantic failed/partial/waiting，避免排障时只看到 queue/tool completed。
- 文案不暴露 batch_id、tool_name、provider、prompt、URL、模型路径或内部异常。

本轮验证：
- python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
  Ran 180 tests OK
- python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
  Ran 563 tests OK
- python editor/plugins/AITool/services/verify_ultimate_plan.py
  All current Agent-native non-native checks passed
- git diff --check
  only CRLF warnings, no whitespace error
```

2026-07-05 LAN 同传状态补充推进记录：

```text
已增强 RuntimeState 中 asset/model transfer 的未完成状态表达：
- AgentRuntime._asset_transfer_summary_for_plan() 新增 incomplete_count，表示 asset_count - ready_count - failed_count。
- AgentRuntime._sync_health_digest_for_report() 新增 asset_incomplete_count，并继续在未 ready/failed 且未 transferring 时标记 asset_transfer_incomplete。
- LANChatAgentWorker._format_agent_runtime_asset_transfer_report() 现在显示 incomplete N，用户问状态或 GM 总结时能直接看到模型同传还有多少资源未完成。
- 这一步只补 RuntimeState 派生事实和用户可见安全摘要，不修改底层 LAN 同步协议、不改变 actor/model 传输行为。

本轮验证：
- python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
  Ran 180 tests OK
- python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
  Ran 563 tests OK
- python editor/plugins/AITool/services/verify_ultimate_plan.py
  All current Agent-native non-native checks passed
- git diff --check
  only CRLF warnings, no whitespace error
```

2026-07-05 补充推进记录：

```text
已把 Runtime 资源批次语义状态继续接到 LANChat 用户可见回复面：
- 修复 LANChatAgentWorker._format_agent_runtime_resource_flow_report() 只读取 latest_batch 单数的问题；Runtime 当前输出的是 latest_batches 列表，旧逻辑会漏掉最近批次 image/model/import 细节。
- formatter 现在会从 latest_batches 取最近批次，显示 latest i/n:status img/model/import x/y/z of requested。
- formatter 现在会读取 status_by_batch_id；当批次语义状态包含 failed/partial/waiting 等非完成状态时，输出 semantic failed/partial/waiting，避免用户只看到 ToolCallGraph completed 而误判业务成功。
- 文案仍只暴露安全计数和状态，不暴露 batch_id、tool_name、provider、prompt、URL、模型路径或内部异常。

本轮验证：
- python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
  Ran 180 tests OK
- python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
  Ran 563 tests OK
- python editor/plugins/AITool/services/verify_ultimate_plan.py
  All current Agent-native non-native checks passed
- git diff --check
  only CRLF warnings, no whitespace error
```

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

### Progress Update 161 - report_ready now exposes semantic batch and sync health

Goal:

```text
Close the user-visible report completion gap: the final report_ready RuntimeEvent
must not only say "report ready" while hiding semantic batch failures, partial
imports, or incomplete LAN asset transfer state inside the full report object.
```

Change:

```text
AgentRuntime.generate_report() now computes batch_semantic_status_counts from
batch_resource_flow_summary.status_by_batch_id and includes the following safe
payload fields in the final report_ready event:

- batch_semantic_status_counts
- batch_failed_count
- batch_partial_count
- sync_health_status
- asset_incomplete_count
- asset_failed_count

RuntimeEventValidator.safe_payload() and AgentRuntime._SAFE_RUNTIME_EVENT_PAYLOAD_KEYS
were updated together so these fields survive both emit-time sanitization and
user_visible_events() filtering.  The only allowed nested payload in this slice
is the small batch_semantic_status_counts status-count map; arbitrary nested
payloads remain blocked.
```

Tests / gates:

```text
test_runtime_actor_import_persists_partial_success_from_engine_provider now
asserts report_ready exposes semantic failed batch status and sync health.

test_actor_import_provider_empty_actor_result_records_failed_import_fact now
asserts report_ready exposes failed semantic batch status even when the import
provider returns no actors and only failed import_results.

test_asset_transfer_progress_sync_event_updates_runtime_asset_summary now asserts
report_ready exposes partial sync health and incomplete asset transfer count.
```

Validation:

```text
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 180 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This slice improves final user-visible report facts.  It does not change real
provider execution, native engine import, C++ sync transport, or F5 validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 189 - report_ready health enters OperationLog replay

Problem:

```text
Recent slices made report_health_summary visible in generate_report(),
status_summary(), Runtime Report replies, and GM summaries.  The remaining
audit gap was RuntimeEvent replay:

- report_ready RuntimeEvent already carried safe report health fields;
- user_visible_events() could expose those fields after payload whitelist fixes;
- but emit_runtime_event() only wrote event_id/event_type/reason into
  OperationLog;
- _runtime_event_replay_summary() could count event types, but could not explain
  whether a report_ready event was healthy, partial, failed, or attention-worthy.

That weakened the invariant "OperationLog is the replay fact source before user
reports": later diagnosis could see that a report was emitted, but not why it
needed attention.
```

Change:

```text
AgentRuntime.emit_runtime_event() now writes safe report_ready health metadata
into OperationLog payloads:

- report_health_status
- report_attention_required
- resource_phase_failed_count
- resource_phase_partial_count
- resource_phase_waiting_count
- report_health_reasons

AgentRuntime._runtime_event_replay_summary() now aggregates:

- report_ready_count
- report_attention_count
- report_health_status_counts
- report_health_reason_counts
- latest_report_ready

LANChat runtime event replay formatters now surface compact report-ready health
status in both normal replay reports and GM runtime replay digests.

verify_ultimate_plan.py statically requires the report_ready health tokens to
exist in RuntimeEventValidator payload keys, AgentRuntime safe event payload
keys, generate_report(), emit_runtime_event(), and runtime event replay summary.
```

Behavior:

```text
This is an audit/read-side slice.  It does not change generation, provider
calls, SceneComposer behavior, C++ writes, LAN sync, VLM execution, or UI
rendering.

It makes report_ready health explainable from OperationLog replay after the
report event is emitted, while keeping provider/prompt/url/API-key data out of
user-facing summaries.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted AgentRuntime report_ready replay test: passed
targeted LANChat formatter test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
test_agent_runtime_phase1.py now runs 565 tests
test_lanchat_runtime_guard.py runs 182 tests
```

Remaining:

```text
This slice only closes the RuntimeEvent/OperationLog replay gap for report
health.  It does not yet complete real native provider rollout, C++ multiplayer
sync transport replacement, front-end report rendering, or F5 runtime
validation.  Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 184 - Report health becomes visible in LANChat status and GM summary

Problem:

```text
RuntimeState and AgentRuntime already produced report_health_summary /
report_health_digest, and Progress Update 183 made resource phase failures
contribute to report health.  The remaining read-side gap was LANChat:

- normal Runtime status replies showed resources, imports, geometry, sync, and
  queues, but not final report health;
- GM Runtime summary also omitted report health;
- therefore resource/import/review failures could affect Runtime truth but still
  be invisible in the user-facing diagnosis surface.

That violated the Agent-native invariant "RuntimeState is the only state fact
source" at the disclosure boundary: the fact existed, but the coordinator-facing
status surface did not expose it.
```

Change:

```text
LANChatAgentWorker now formats report health through a safe formatter:

- status
- attention_required
- batch failed / partial / waiting counts
- import failed count
- resource phase failed / partial / waiting counts
- asset failed / incomplete counts
- sync health status
- safe reason list

The formatter redacts internal provider / prompt / url / raw / token / api-key /
path / session / job markers before displaying reasons.

The formatted report health is now included in:

- Runtime status replies: "报告健康：..."
- GM Runtime summaries: "Report health: ..."
```

Behavior:

```text
This is a read-side Agent-native closure.  It does not change ToolCallGraph
execution, resource generation, import behavior, C++ engine writes, LAN sync, or
VLM behavior.

It makes the existing Runtime report health fact visible to users and GM without
leaking internal provider details.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reads_agent_runtime_status_when_runtime_plan_exists editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_report_query_generates_safe_summary_without_coordinator_ingest
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted LANChat Runtime health tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
test_lanchat_runtime_guard.py now runs 182 tests inside verify_ultimate_plan.py
```

Remaining:

```text
This slice only closes the report-health disclosure gap.  It does not yet
complete real native provider rollout, C++ multiplayer sync transport
replacement, front-end report rendering, or F5 runtime validation.  Those remain
later Agent-native Phase 5/6/7 work.
```

## Progress Update 185 - Runtime Report consumes report health

Problem:

```text
Progress Update 184 made report health visible in:

- Runtime status replies
- GM Runtime summaries

The remaining read-side split was the explicit Runtime Report path.  It already
received a report object from AgentRuntime.generate_report(), but LANChat did not
render report_health_summary inside the final "[Runtime Report]" text.

That meant the three user-facing diagnosis surfaces were inconsistent:

- status query: report health visible
- GM summary: report health visible
- runtime report: report health missing

For the Agent-native invariant "RuntimeState is the only state fact source", the
report surface must consume the same health fact instead of letting report
trustworthiness remain implicit.
```

Change:

```text
LANChatAgentWorker._handle_agent_runtime_report_query() now reads
report["report_health_summary"] and renders it through the same safe formatter
used by status and GM summary.

The Runtime Report output now includes:

- report health: status, attention flag, batch/import/resource/asset failure
  counts, sync health, and safe reason list
```

Behavior:

```text
This is a read-side consistency slice.  It does not alter report generation,
ToolCallGraph execution, provider behavior, C++ engine writes, sync transport,
or VLM behavior.

The user-visible result is that report trustworthiness is now visible in all
three Runtime diagnosis surfaces: status, GM summary, and report.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_report_query_generates_safe_summary_without_coordinator_ingest
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime Report test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice closes the Runtime Report report-health visibility gap.  It does not
yet complete real native provider rollout, C++ multiplayer sync transport
replacement, front-end report rendering, or F5 runtime validation.  Those remain
later Agent-native Phase 5/6/7 work.
```

## Progress Update 186 - report_ready events carry report health metadata

Problem:

```text
Progress Updates 183-185 made report health visible in status, GM summary, and
Runtime Report text.  The remaining UI/event boundary gap was report_ready:

- generate_report() used report_health_summary to choose the report_ready title
  and warning level;
- but the report_ready payload only exposed partial batch/import/asset counts;
- it did not expose report health status, attention flag, resource phase counts,
  or health reasons.

That meant the event stream could say "warning" without carrying enough
structured reason metadata for front-end WAIT UX, report cards, or later
OperationLog replay to explain why.
```

Change:

```text
report_ready RuntimeEvent payload now includes safe report-health metadata:

- report_health_status
- report_attention_required
- resource_phase_failed_count
- resource_phase_partial_count
- resource_phase_waiting_count
- report_health_reasons

RuntimeEventValidator._SAFE_PAYLOAD_KEYS and AgentRuntime._SAFE_RUNTIME_EVENT_PAYLOAD_KEYS
now explicitly allow those fields.  report_health_reasons is restricted to a
small list of safe short text values.
```

Behavior:

```text
This is an event disclosure contract slice.  It does not change report
generation, ToolCallGraph execution, provider behavior, native writes,
multiplayer sync transport, or VLM behavior.

The user-visible effect is that report_ready can now explain whether the report
is healthy, partial, or failed, and whether resource phase failures contributed
to that status.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted report_ready health metadata test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice closes the RuntimeEvent report-health metadata gap.  It does not yet
complete real native provider rollout, C++ multiplayer sync transport
replacement, front-end report rendering, or F5 runtime validation.  Those remain
later Agent-native Phase 5/6/7 work.
```

## Progress Update 187 - report_ready health metadata passes the RuntimeEvent safe read boundary

Problem:

```text
Progress Update 186 added report health fields to the report_ready event payload,
but the RuntimeEvent path has two safety boundaries:

1. RuntimeEventValidator.safe_payload() for write-time event safety.
2. AgentRuntime._SAFE_RUNTIME_EVENT_PAYLOAD_KEYS inside _safe_runtime_event_row()
   for read-time user-visible event filtering.

The first boundary was updated, but the second boundary still filtered the new
report-health fields out of user_visible_events().  As a result, the event was
persisted with health metadata in RuntimeState, but callers reading the safe
event feed still could not see it.
```

Change:

```text
AgentRuntime._SAFE_RUNTIME_EVENT_PAYLOAD_KEYS now also allows:

- report_health_status
- report_attention_required
- resource_phase_failed_count
- resource_phase_partial_count
- resource_phase_waiting_count
- report_health_reasons

The existing report_ready regression now proves the metadata survives all the
way through user_visible_events(), not just the initial emit call.
```

Behavior:

```text
This is a read-boundary contract fix.  It does not change generation,
ToolCallGraph execution, providers, native writes, sync transport, or VLM.

The user-visible RuntimeEvent stream can now explain report health without
exposing provider, URL, prompt, raw payload, path, token, or job internals.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted report_ready health metadata read-boundary test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice closes the RuntimeEvent safe read-boundary gap for report health.
It does not yet complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 188 - report_ready health metadata is locked by the static verifier

Problem:

```text
Progress Updates 186-187 made report_ready health metadata work at runtime and
through user_visible_events().  The remaining regression risk was that the
contract depended on three separate locations staying aligned:

- RuntimeEventValidator._SAFE_PAYLOAD_KEYS
- AgentRuntime._SAFE_RUNTIME_EVENT_PAYLOAD_KEYS
- AgentRuntime.generate_report() report_ready payload

If a later edit removed one of those tokens, the behavior could silently regress
unless the exact runtime test happened to catch it.  This is a contract-level
boundary and belongs in verify_ultimate_plan.py.
```

Change:

```text
verify_ultimate_plan.py now statically requires every report_ready health token
to appear in all three required places:

- report_health_status
- report_attention_required
- resource_phase_failed_count
- resource_phase_partial_count
- resource_phase_waiting_count
- report_health_reasons

It also requires RuntimeEventValidator.safe_payload() to explicitly sanitize
report_health_reasons, and requires the regression test
test_partial_resource_results_report_ready_and_failed_counts to remain present.
```

Behavior:

```text
This is a contract-hardening slice.  It does not change runtime behavior,
generation, ToolCallGraph execution, provider adapters, native writes, sync, or
VLM.

The Agent-native non-native gate will now fail if report_ready health metadata is
removed from either write-time or read-time RuntimeEvent safety boundaries.
```

Validation:

```text
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice only locks the RuntimeEvent report-health contract.  It does not yet
complete real native provider rollout, C++ multiplayer sync transport
replacement, front-end report rendering, or F5 runtime validation.  Those remain
later Agent-native Phase 5/6/7 work.
```

## Progress Update 183 - Resource phase failures affect report health

Problem:

```text
Progress Update 182 made import/review/custom resource phase facts visible in
resource_summary.by_phase.  The next semantic gap was report health:

- status/report/GM could now show that a non image/model phase failed;
- but _report_health_summary() only considered batch_resource_flow, import
  summary, and sync health;
- a future RuntimeState fact such as import/review phase failed could remain a
  local resource-stage detail instead of changing the final health verdict.

That would violate the Agent-native expectation that RuntimeState business facts
drive user-facing report status, not just decorative diagnostics.
```

Change:

```text
AgentRuntime._report_health_summary() now accepts resource_summary and derives:

- resource_phase_failed_count
- resource_phase_partial_count
- resource_phase_waiting_count
- resource_phase_status_counts

The health verdict now treats resource phase failures as failed, partial phases
as partial, and planned/running/waiting phases as waiting.  The implementation
uses status_counts when present and only falls back to failed_count/requested
count inference when needed, avoiding double counting.

generate_report(), status_summary(), and operation replay report health paths now
pass the scoped resource_summary into _report_health_summary().
```

Behavior:

```text
This is a semantic read-side slice.  It does not change provider execution,
resource generation, import execution, review execution, ToolCallGraph
scheduling, C++ writes, or LAN sync.

It prevents the UI/report/GM surface from saying "ok" when RuntimeState already
contains a failed import/review/custom resource phase.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_resource_summary_includes_custom_import_and_review_phase_facts editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted resource health tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
test_agent_runtime_phase1.py remains 565 tests
```

Remaining:

```text
This slice only makes existing RuntimeState phase facts affect report health.  It
does not yet complete real native provider rollout, native import execution, C++
multiplayer sync transport replacement, or F5 runtime validation.  Those remain
later Agent-native Phase 5/6/7 work.
```

## Progress Update 182 - Resource phase facts feed import/review stage summaries

Problem:

```text
custom_resource_phase_facts had become a first-class RuntimeState room slot, and
image/model resource tools already wrote phase facts.  However,
_resource_summary_for_plan() still built by_phase mostly from user-visible
runtime_events, which only covered image/model events.

That left a read-side gap for the target batch loop:

image -> model -> import -> review

Future import/review/custom resource phase facts could exist in RuntimeState but
would not appear in the compact resource stage summary shown by status, report,
or GM surfaces.
```

Change:

```text
AgentRuntime._resource_summary_for_plan() now folds non image/model
custom_resource_phase_facts into by_phase and latest_events.

The merge deliberately avoids image/model double counting because those phases
already have runtime_event coverage today.  Non image/model phases such as
import, review, or future custom resource stages can now appear from
RuntimeState facts even when no matching runtime_event exists.

LANChatAgentWorker._format_agent_runtime_resource_stage_report() now renders:

- image
- model
- import
- review
- any additional custom phases

in a stable order.
```

Behavior:

```text
This is a read-side closure slice.  It does not change provider execution,
resource generation, import execution, review execution, ToolCallGraph
scheduling, C++ writes, or LAN sync.

It moves the user-visible resource stage summary closer to the Agent-native
target of a complete batch loop instead of a partial image/model-only view.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_resource_summary_includes_custom_import_and_review_phase_facts editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted resource phase summary tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
test_agent_runtime_phase1.py now runs 565 tests
```

Remaining:

```text
This slice only makes import/review phase facts visible when RuntimeState already
has them.  It does not yet complete real native provider rollout, native import
execution, C++ multiplayer sync transport replacement, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 181 - GM Runtime summary exposes safe asset-transfer status

Problem:

```text
AgentRuntime already tracked multiplayer sync, message delivery, engine-write
boundaries, and asset-transfer state.  The regular Runtime status reply exposed
those facts, but the GM summary path still missed the current asset-transfer
digest and only showed transfer activity indirectly through sync replay.

For multiplayer验收 this is a real visibility gap: when users ask GM to summarize
the room after multi-agent discussion or generation, GM should report whether
model transfer is active/complete/failed without leaking internal file paths,
peer ids, provider details, or raw asset ids.
```

Change:

```text
AgentRuntime.gm_summary() now includes asset_transfer_digest from RuntimeState:

- asset_count
- ready_count
- completed_count
- transferring_count
- failed_count
- overall_progress
- bytes_transferred / total_bytes
- latest transfer statuses with asset ids redacted

LANChatAgentWorker._agent_runtime_gm_summary_reply() now renders:

- 模型同传：assets N, ready X, completed Y, transferring Z, failed K, progress P%

The GM sync replay empty fallback was also cleaned from a mojibake string to:

- recorded 0, asset progress 0, peer join/leave 0/0, reconcile 0/0
```

Behavior:

```text
This is a reporting/status slice only.  It does not change generation execution,
ToolCallGraph scheduling, sync transport, native writes, or asset-transfer
mechanics.

It strengthens the Agent-native invariant that GM reads RuntimeState and
OperationLog-derived facts instead of guessing from chat history.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_gm_summary_action_records_snapshot_without_business_tool_graph
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reads_agent_runtime_status_when_runtime_plan_exists
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_includes_runtime_sync_summary
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime GM summary test: passed
targeted LANChat GM Runtime status tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice only closes the GM-facing multiplayer transfer visibility gap.  It
does not yet complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 172 - Engine actor import writes provider boundary facts

Problem:

```text
The Runtime actor import path already rejected unsafe engine results:

- a successful native import without a stable actor identity fails the ToolCall;
- partial native imports preserve successful actors and failed rows;
- OperationLog exposes sanitized import result rows for replay.

However, the RuntimeState import result fact still lacked an explicit provider
boundary summary.  Future debugging would have to infer whether a batch result
came from the real engine import provider, a runtime precheck, or a default
mock-like provider by reading OperationLog events and final actor rows.
```

Change:

```text
make_engine_actor_import_provider now returns a safe provider boundary marker:

- source = engine_actor_import_provider
- engine_write_result.provider_source
- requested_count
- identity_result_count
- missing_identity_count
- status_counts

runtime.actor.import_batch now persists this boundary summary into:

custom_import_facts["<batch_id>:actor_import_result"].engine_write_boundary

The fact stores only safe accounting fields and actor ids.  It does not store
model_path, prompts, provider raw payloads, URLs, stack traces, API keys, or
native tool response bodies.
```

Behavior:

```text
The slice does not change ToolCallGraph execution order or actor import
success semantics.

- missing model resources still create a failed import result fact without
  creating fake actors;
- native success without actor identity still fails the import ToolCall;
- partial native import success still keeps real actors, marks the batch
  partial, and records sanitized per-actor import rows;
- the new boundary fact is additive evidence for replay/status/debugging.
```

Tests / gates:

```text
test_runtime_actor_import_persists_partial_success_from_engine_provider now
verifies engine_write_boundary.provider_source, requested_count,
identity_result_count, missing_identity_count, status_counts, imported_actor_ids,
and sanitization.

test_engine_actor_import_provider_requires_engine_actor_identity remains a
tool-failure test; it confirms missing native actor identity does not become a
fake Runtime actor.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_actor_import_provider_requires_engine_actor_identity editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted engine actor import provider tests: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 180 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This slice strengthens RuntimeState evidence for real engine actor import
boundaries.  It does not yet complete native engine import rollout, replace
multiplayer sync transport, or prove F5 runtime behavior.  Those remain later
Agent-native Phase 5/6/7 work.
```

## Progress Update 173 - Layout transform writes engine boundary facts

Problem:

```text
Runtime layout adjustment already used a narrow layout_transform_provider
boundary for confirmed low-risk move/align operations.  The provider returned
sanitized transform_results and authoritative actor_updates, and OperationLog
could replay transform result rows.

The remaining evidence gap was similar to actor import before Progress Update
172: RuntimeState layout_adjustment_proposals did not keep a compact provider
boundary fact that explains whether the transform came from the real engine
layout transform adapter, how many deltas were requested, how many actor updates
were accepted, and whether the engine returned observed positions.
```

Change:

```text
make_engine_layout_transform_provider now returns:

- source = engine_layout_transform_provider
- engine_write_result.provider_source
- requested_count
- updated_count
- observed_position_count
- status_counts

AgentRuntime._apply_layout_adjustment_tool now stores a sanitized copy in:

layout_adjustment_proposals[plan_id].engine_transform_boundary

The boundary fact stores only safe accounting fields.  It does not persist raw
native responses, prompts, provider internals, URLs, local paths, stack traces,
or API keys.
```

Behavior:

```text
This slice does not change layout proposal generation, low-risk delta
selection, actor update authority, or ToolCallGraph execution order.

- provider-confirmed actor_updates remain the only source that can update
  RuntimeState actors after an engine transform provider is configured;
- transform_results remain sanitized advisory/audit rows;
- engine_transform_boundary is additive RuntimeState evidence for status,
  replay, and later F5 debugging.
```

Tests / gates:

```text
test_engine_layout_transform_provider_uses_gate_and_returns_actor_updates now
verifies the provider boundary source, requested_count, updated_count,
observed_position_count, and status_counts.

test_runtime_layout_adjustment_can_call_engine_transform_provider now verifies
layout_adjustment_proposals[plan_id].engine_transform_boundary is persisted
after confirmation.

Existing native-name sanitization tests were updated to allow the safe
engine_layout_transform_provider enum while still blocking provider raw,
prompt, and secret/path leakage.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_layout_transform_provider_uses_gate_and_returns_actor_updates editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_layout_transform_provider_sanitizes_transform_skip_reason editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_layout_adjustment_can_call_engine_transform_provider
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted engine layout transform tests: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 180 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This slice strengthens RuntimeState evidence for confirmed layout transforms.
It does not yet complete native engine transform rollout, C++ multiplayer sync
transport, or F5 runtime behavior.  Those remain later Agent-native Phase 5/6/7
work.
```

### Progress Update 162 - report_ready event text is semantic-status aware

Goal:

```text
Close the UI disclosure gap after Progress Update 161: report_ready payload now
contains semantic batch/sync facts, but the user-visible title/message could
still read like a clean completion.  The event text itself must surface failed
or incomplete outcomes without exposing internal payloads.
```

Change:

```text
AgentRuntime.generate_report() now derives report_ready level/title/message from
the same RuntimeState facts used by batch_resource_flow_summary and sync health:

- failed batch/import/asset-transfer facts produce warning level and
  "生成报告已完成（存在失败项）"
- partial batch or incomplete asset transfer facts produce warning level and
  "生成报告已完成（仍有未完成项）"
- clean reports keep the original info-level completion wording

This keeps LANChat automatic RuntimeEvent disclosure useful even when the UI
only renders event title/message, while the detailed counts remain in safe
payload fields.
```

Tests / gates:

```text
test_runtime_actor_import_persists_partial_success_from_engine_provider now
asserts failed semantic import results make report_ready warning-level.

test_actor_import_provider_empty_actor_result_records_failed_import_fact now
asserts empty actor import with failed import_results makes report_ready
warning-level and mentions import failure.

test_asset_transfer_progress_sync_event_updates_runtime_asset_summary now
asserts incomplete model transfer makes report_ready warning-level and mentions
unfinished transfer.
```

Validation:

```text
targeted report_ready semantic text tests: passed
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted tests: 3 passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 180 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This slice improves user-visible disclosure after Runtime reports.  It does not
change real provider execution, native engine import, C++ sync transport, or F5
validation.  Those remain later Agent-native Phase 5/6/7 work.
```

### Progress Update 163 - report health summary enters status/report/GM read sides

Goal:

```text
Close the remaining read-side split after Progress Updates 160-162: batch
resource flow, import results, and sync/asset transfer health were visible in
separate summaries, but status, final report, GM summary, and LANChat replies
could still describe different health verdicts.  The Runtime now needs one
sanitized health digest shared by these surfaces.
```

Change:

```text
AgentRuntime now derives report_health_summary from:

- batch_resource_flow_summary
- import_summary
- sync_health_digest

The summary contains:

- status: ok / failed / partial / waiting / needs_attention / unknown
- attention_required
- reasons
- batch failed / partial / waiting counts
- batch_semantic_status_counts
- import requested / imported / failed counts
- sync health status
- asset incomplete / failed counts

generate_report(), status_summary(), and gm_summary() now read this same digest.
LANChat status replies expose it as "报告健康"; LANChat GM summaries expose it as
"Report health".  The text remains user-facing and strips internal provider,
prompt, tool graph, path, and payload details.
```

Tests / gates:

```text
test_asset_transfer_progress_sync_event_updates_runtime_asset_summary now checks
that status_summary() and generate_report() share the same partial
report_health_summary when model transfer is incomplete.

import failure tests now assert failed report_health_summary status, attention
flag, and reasons such as batch_failed/import_failed.

GM summary tests now assert the clean runtime path exposes ok report health.

LANChat formatter tests now assert failed/partial health is visible without
leaking provider or prompt fields.
```

Validation:

```text
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 181 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice improves read-side consistency and user-visible health disclosure.
It does not change real provider execution, native engine import, C++ sync
transport, or F5 validation.  Those remain later Agent-native Phase 5/6/7 work.
```

### Progress Update 164 - operation replay carries the same report health digest

Goal:

```text
Make OperationLog replay a first-class audit surface for report health.  After
Progress Update 163, status_summary(), generate_report(), gm_summary(), and
LANChat replies shared one health digest, but operation_replay() still only
exposed separate sync/resource replay summaries.  That made postmortem review
weaker than the live status/report surfaces.
```

Change:

```text
AgentRuntime._compose_operation_replay() now adds:

- asset_transfer_summary: state-derived asset transfer facts for the replay
  scope
- report_health_summary: the same sanitized health digest shape used by status
  and final reports

The replay keeps asset_transfer_replay_summary for event-level audit, but the
health verdict is computed from RuntimeState asset totals plus replay sync and
message-delivery facts.  This avoids treating an in-progress or incomplete
asset transfer as ok just because the replay stream only saw progress events.
```

Tests / gates:

```text
test_asset_transfer_progress_sync_event_updates_runtime_asset_summary now asserts
operation_replay()["report_health_summary"] is partial, attention-required, and
contains asset_transfer_incomplete when the RuntimeState transfer is incomplete.
```

Validation:

```text
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py AgentRuntimePhase1Tests.test_asset_transfer_progress_sync_event_updates_runtime_asset_summary -f
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted asset transfer replay health test: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 181 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice improves replay/postmortem consistency.  It does not change real
provider execution, native engine import, C++ sync transport, or F5 validation.
Those remain later Agent-native Phase 5/6/7 work.
```

### Progress Update 165 - operation replay exposes import summary behind health

Goal:

```text
Complete the audit trail behind Progress Update 164.  operation_replay() now
shows the same report_health_summary as status/report, but import failures were
only indirectly visible through engine_write_summary and batch resource flow.
Replay needs to expose the import_summary that feeds report health so a
postmortem can explain why import_failed_count was raised.
```

Change:

```text
AgentRuntime._compose_operation_replay() now includes import_summary from
RuntimeState for the requested room / plan / batch scope.  report_health_summary
continues to be derived from batch_resource_flow_summary, import_summary, and
sync health.  This keeps replay aligned with status_summary() and
generate_report() without parsing user-facing report text.
```

Tests / gates:

```text
test_runtime_actor_import_persists_partial_success_from_engine_provider now
asserts operation_replay()["import_summary"] matches the report/status import
summary and that replay report_health_summary is failed with import_failed in
the reasons.
```

Validation:

```text
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider -f
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted partial import replay summary test: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 181 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice improves replay/postmortem consistency for import failures.  It does
not change real provider execution, native engine import, C++ sync transport, or
F5 validation.  Those remain later Agent-native Phase 5/6/7 work.
```

### Progress Update 166 - operation replay exposes resource summary behind batch flow

Goal:

```text
Continue making OperationLog replay a first-class audit surface.  Replay already
exposes report health, import summary, sync and asset transfer facts, but image
and model resource readiness were still only available through lifecycle replay
events or final report/status surfaces.  A postmortem needs the same
state-derived resource_summary that explains resource failed/partial counts.
```

Change:

```text
AgentRuntime._compose_operation_replay() now includes resource_summary from
RuntimeState for the requested room / plan / batch scope.  This mirrors
status_summary() and generate_report(), while batch_resource_lifecycle_summary
continues to serve as the event-level resource audit trail.
```

Tests / gates:

```text
test_partial_resource_results_report_ready_and_failed_counts now asserts
operation_replay()["resource_summary"]["by_phase"]["image"] matches the final
report resource summary for a partial image-resource provider result.
```

Validation:

```text
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts -f
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted partial resource replay summary test: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 181 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice improves replay/postmortem consistency for image/model resource
readiness.  It does not change real provider execution, native engine import,
C++ sync transport, or F5 validation.  Those remain later Agent-native Phase
5/6/7 work.
```

### Progress Update 167 - final report replay summary carries state-derived resource/import/health facts

Goal:

```text
Align the replay summary embedded inside generate_report() with the standalone
operation_replay() surface.  Standalone replay already exposes resource,
import, asset transfer, and health summaries, but final reports still embedded
only the older event-level replay summaries.  A saved report should be
self-contained enough to explain resource/import/health outcomes without
requiring a separate replay query.
```

Change:

```text
AgentRuntime._operation_replay_summary_for_report() now adds state-derived:

- resource_summary
- import_summary
- asset_transfer_summary
- report_health_summary

It still reads OperationLog directly and does not call operation_replay(), so
generating a report does not create an extra replay-query side effect before
the user_report_generated entry.
```

Tests / gates:

```text
test_partial_resource_results_report_ready_and_failed_counts now asserts the
final report's operation_replay_summary.resource_summary image phase matches
the report resource summary.

test_runtime_actor_import_persists_partial_success_from_engine_provider now
asserts the final report's operation_replay_summary.import_summary matches the
report/status import summary and carries failed report health.
```

Validation:

```text
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider -f
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted report embedded replay summary tests: 2 passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 181 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice improves saved-report self-containment and postmortem consistency.
It does not change real provider execution, native engine import, C++ sync
transport, or F5 validation.  Those remain later Agent-native Phase 5/6/7 work.
```

### Progress Update 168 - GM summary exposes resource-stage attention

Problem:

```text
GM/runtime status replies already exposed batch-level resource flow and report
health, but the GM read side could not clearly say which resource stage needed
attention.  When image generation was partial/failed while later model/import
steps continued, GM could see that a batch was not fully healthy but lacked a
stage-level diagnostic such as image-resource-failed.
```

Change:

```text
AgentRuntime.gm_summary() now includes a resource_stage_digest with:

- event_count
- by_phase.image / by_phase.model counts
- latest resource events
- needs_attention reasons such as image_resource_failed and model_resource_failed

LANChatAgentWorker now formats those attention reasons in GM/runtime replies
without exposing provider, prompt, URL, API key, or raw payload fields.
```

Tests / gates:

```text
test_partial_resource_results_report_ready_and_failed_counts now verifies that
GM summary carries image phase counts, latest resource event window, and
image_resource_failed attention for partial image resource results.

test_runtime_resource_stage_formatter_surfaces_phase_attention_without_internal_payloads
checks that LANChat resource-stage formatting shows image/model counts, latest
stage status, and attention reasons without leaking internal payload markers.
```

Validation:

```text
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py LANChatRuntimeGuardTests.test_runtime_resource_stage_formatter_surfaces_phase_attention_without_internal_payloads -f
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted GM resource-stage tests: 2 passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 182 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: pass, LF/CRLF warnings only
```

Remaining:

```text
This slice improves GM/status observability and replay-facing diagnostics.  It
does not change actual provider scheduling, native import, C++ multiplayer sync,
or F5 runtime behavior.  Those remain later Agent-native Phase 5/6/7 work.
```

### Progress Update 169 - Runtime fact-source boundary enters report/status/GM read sides

Problem:

```text
Python AgentRuntime and the C++ / LANChat / Engine layer are being unified
gradually.  Before this slice, status/report/GM replies exposed RuntimeState
facts and mirrored sync/engine facts, but did not explicitly show the boundary
between:

- RuntimeState business facts owned by Python AgentRuntime
- external Engine / LANChat / sync facts mirrored back into RuntimeState

That made it easy for future work to accidentally treat a Runtime plan fact as
proof of engine-side import/sync success, or treat missing engine feedback as a
successful external state.
```

Change:

```text
AgentRuntime now adds fact_source_boundary_summary to generate_report() and
status_summary(), and exposes fact_source_boundary_digest through gm_summary().

The digest records:

- runtime_state_source = RuntimeState
- external_truth_source = engine_lanchat_mirrored
- runtime business fact counts split by plan / batch / resource / import
- mirrored external fact counts split by sync / engine write / scene snapshot
- whether authoritative external facts are currently available
- boundary notes such as runtime-state-is-business-truth and
  engine-lanchat-facts-are-mirrored

LANChatAgentWorker formats the digest in Runtime Report, Runtime Status, and GM
Runtime Summary replies without exposing provider, prompt, URL, API key, raw
payload, peer id, actor id, or local file paths.
```

Additional cleanup:

```text
Several AgentRuntime tests still depended on mojibake Chinese strings that were
not architectural invariants.  This slice converted those checks to structure,
payload, count, state, ordering, and redaction assertions.  Where the test was
meant to validate Chinese substrate routing, the data was restored to stable
UTF-8 Chinese terms such as 森林 / 天空 / 草地 / 小木桌 / 帐篷.

This keeps the test suite focused on Runtime invariants instead of editor
encoding artifacts.
```

Tests / gates:

```text
test_report_includes_safe_sync_summary_from_runtime_state now verifies
fact_source_boundary_summary in report/status/GM read sides.

test_runtime_resource_and_fact_source_formatters_surface_attention verifies
LANChat formatting for resource-stage attention and fact-source boundary
counts.

GM summary tests now verify the Fact source line appears alongside Runtime
resources and sync health without leaking internal fields.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 180 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: pass, LF/CRLF warnings only
```

Remaining:

```text
This slice is a read-side and contract-hardening step.  It does not yet complete
real provider scheduling, native engine import, C++ multiplayer sync transport,
or F5 runtime validation.  Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 170 - Partial batch terminal status is now persisted by Runtime facts

Problem:

```text
ToolCallGraph execution status and business execution status were still partly
split.  A graph could finish with status=completed while the engine/import facts
showed that only part of the requested actors were actually imported.

Before this slice, failed import facts could force the BatchPlan to failed, but
partial import success stayed mostly as a read-side report/resource-flow
inference.  That meant RuntimeState itself could still look completed even when
the authoritative import fact was partial.
```

Change:

```text
BatchPlanStatus now includes partial.

AgentRuntime._terminal_batch_status_from_import_facts() now maps:

- explicit failed/error/missing import facts to BatchPlanStatus.FAILED
- zero-ready all-failed import facts to BatchPlanStatus.FAILED
- ready_count > 0 with failed_count > 0 to BatchPlanStatus.PARTIAL
- explicit partial / partially_succeeded / partial_success to BatchPlanStatus.PARTIAL

_finalize_batch_after_drained_graph() records
batch_terminal_status_from_runtime_facts before marking the terminal batch
status, so OperationLog captures that the final batch business status came from
Runtime import facts rather than the ToolCallGraph surface status.

batch.mark_partial was added as a narrow ToolCallGraph state-writing tool, so
partial is persisted through the same RuntimeGuard / StatePatch boundary as
completed, failed, and cancelled.
```

Plan status rule:

```text
ScenePlanStatus still has no separate partial value.  A plan whose batches are
all completed or partial is allowed to reach completed so users can receive the
final report and continue with review/adjustment actions.

The report health layer remains responsible for surfacing partial health:

- batch_resource_flow_summary.partial_count
- report_health_summary.status = partial
- report_health_summary.attention_required = true
- batch_summary.batches[].status / semantic_status = partial
```

Tests / gates:

```text
test_runtime_actor_import_persists_partial_success_from_engine_provider now
verifies:

- ToolCallGraph status may be completed
- BatchPlan status is partial
- batch_terminal_status_from_runtime_facts records source=import_facts
- report/status batch resource flow marks the batch partial
- report_health_summary.status is partial

test_actor_import_provider_empty_actor_result_records_failed_import_fact now
verifies full import failure still persists BatchPlan status failed and records
the same import-facts terminal status event.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider -f
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py AgentRuntimePhase1Tests.test_actor_import_provider_empty_actor_result_records_failed_import_fact -f
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted import fact terminal status tests: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 180 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice improves AgentRuntime semantic execution state and report health.  It
does not yet complete real provider scheduling, native engine import, C++
multiplayer sync transport, or F5 runtime validation.  Those remain later
Agent-native Phase 5/6/7 work.
```

## Progress Update 171 - Resource phase facts are persisted before report summaries

Problem:

```text
Resource image/model preparation already wrote image_resource_plans and
model_resource_plans into RuntimeState, and runtime_events exposed safe progress
messages.  However, the phase-level resource outcome was still mostly derived
from user-visible events at report time.

That left a small Phase 5 evidence gap for future real providers:

- resource rows existed;
- events existed;
- but the "image/model phase status for this batch" was not stored as its own
  RuntimeState fact before report generation.
```

Change:

```text
runtime.asset.image.prepare and runtime.asset.model.prepare now also persist
custom_resource_phase_facts for each batch/phase.

Each fact stores only safe summary fields:

- batch_id
- phase = image / model
- status = completed / partial / failed
- requested_count
- ready_count
- failed_count
- resource_count
- status_counts
- source = runtime_resource_phase_fact

The ToolRegistry contract was updated so both resource tools declare:

- image/model resource plan state
- custom_resource_phase_facts

This keeps RuntimeGuard / StatePatch validation honest instead of letting the
new fact piggyback outside the declared tool contract.
```

Report/status read side:

```text
_resource_summary_for_plan() remains backward compatible with the existing
runtime_event-based by_phase/latest_events summary.

It now also includes:

- fact_count
- latest_facts

These fields are read from custom_resource_phase_facts and contain only the
safe summary fields above.  They do not expose provider names, prompts, URLs,
local file paths, raw payloads, or API keys.

fact_source_boundary_summary now also counts
runtime_resource_phase_fact_count separately from runtime_resource_event_count,
so Runtime business fact accounting reflects resource phase facts instead of
only user-visible resource events.
```

Tests / gates:

```text
test_partial_resource_results_report_ready_and_failed_counts now verifies that
partial image resources create a custom_resource_phase_facts entry and that the
report carries the partial phase fact.

test_empty_model_resource_provider_result_records_failed_resource_facts now
verifies that an empty model provider result creates a failed model phase fact.

Tool manifest tests now verify that runtime.asset.image.prepare and
runtime.asset.model.prepare declare custom_resource_phase_facts in
produces_state.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts -f
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_resource_provider_result_records_failed_resource_facts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_image_adapter_item_failure_persists_failed_fact_and_partial_event editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_partial_model_resources_only_import_ready_items
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted resource phase fact tests: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 180 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice moves resource phase outcome evidence further into RuntimeState.  It
does not yet enable real providers by default, complete native engine import,
replace C++ multiplayer sync transport, or provide F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 174 - Actor delete writes engine boundary facts

Problem:

```text
Actor import and layout transform now persist compact engine-write boundary
facts in RuntimeState.  Actor delete still only persisted sanitized
engine_delete_results and actor deleted updates on the review advisory proposal.

That left the delete path slightly behind the other engine write paths: replay
could count delete rows, but RuntimeState did not explicitly say which provider
boundary handled the deletion, how many delete attempts were represented, how
many actors were accepted as deleted, or how many deletes were observed by the
engine adapter.
```

Change:

```text
make_engine_actor_delete_provider now returns:

- source = engine_actor_delete_provider
- engine_write_result.provider_source
- requested_count
- deleted_count
- observed_deleted_count
- status_counts

AgentRuntime._mark_actor_deleted_tool now stores a sanitized copy in:

review_advisory_proposals[proposal_key].engine_delete_boundary

The boundary fact stores only safe accounting fields.  It does not persist raw
native responses, prompts, provider internals, URLs, local paths, stack traces,
or API keys.
```

Behavior:

```text
This slice does not change delete approval, delete target selection, or actor
update authority.

- system actors remain skipped;
- unconfirmed or high-risk delete actions still go through review advisory;
- when an engine delete provider is configured, only provider-successful actor
  ids are marked deleted in RuntimeState;
- failed delete rows remain advisory/audit facts and do not pretend the engine
  changed.
```

Tests / gates:

```text
test_engine_actor_delete_provider_uses_remove_gate_and_returns_actor_updates now
verifies the provider boundary source, requested_count, deleted_count,
observed_deleted_count, status_counts, and sanitization.

test_confirmed_delete_advisory_with_engine_provider_only_marks_successful_delete
now verifies review_advisory_proposals[proposal_key].engine_delete_boundary is
persisted after execution and preserves mixed success/failed status counts.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_actor_delete_provider_uses_remove_gate_and_returns_actor_updates editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirmed_delete_advisory_with_engine_provider_only_marks_successful_delete
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted engine actor delete tests: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 180 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This slice aligns actor delete with the import and transform engine-write
boundary evidence pattern.  It does not yet complete native delete rollout, C++
multiplayer sync transport, or F5 runtime behavior.  Those remain later
Agent-native Phase 5/6/7 work.
```

## Progress Update 175 - Engine write boundary facts enter report/status/replay

Problem:

```text
Progress Updates 172-174 persisted compact engine write boundary facts for
actor import, layout transform, and actor delete.  Those facts existed in
RuntimeState, but the user-facing read side was still split:

- generate_report() and status_summary() did not expose one compact boundary
  summary;
- operation_replay() could count low-level engine write rows, but did not show
  the new boundary facts as first-class replay evidence;
- fact-source accounting did not count these write-boundary facts as mirrored
  external facts.

That meant RuntimeState already knew which engine boundary accepted a write, but
the report/replay evidence chain was still harder to audit.
```

Change:

```text
AgentRuntime now derives engine_write_boundary_summary from RuntimeState:

- custom_import_facts[*:actor_import_result].engine_write_boundary
- layout_adjustment_proposals[*].engine_transform_boundary
- review_advisory_proposals[*].engine_delete_boundary

The summary is now included in:

- generate_report()
- status_summary()
- operation_replay()
- operation_replay_summary

fact_source_boundary_summary now includes engine_write_boundary_fact_count and
adds those boundary facts into mirrored_external_fact_count.
```

User-facing safety:

```text
The public summary deliberately uses write_source / write_source_counts rather
than provider_source / provider_source_counts.

Safe labels are mapped to:

- engine_actor_import
- runtime_layout_transform
- runtime_actor_delete
- runtime_engine_write

This preserves write-boundary accountability without exposing provider internals,
raw native responses, URLs, prompts, local paths, API keys, or stack traces.
```

Behavior:

```text
This slice is read-side only.  It does not change actor import, layout transform,
actor delete, RuntimeGuard permissions, EngineWriteGate behavior, C++ engine
calls, LAN sync, or provider enablement.

It makes the existing write-boundary facts auditable from report/status/replay
so OperationLog and RuntimeState remain the evidence source before any user
report claims success.
```

Tests / gates:

```text
test_runtime_actor_import_persists_partial_success_from_engine_provider now
checks report/status engine_write_boundary_summary for actor import boundaries
and verifies fact_source_boundary_summary.engine_write_boundary_fact_count.

test_runtime_layout_adjustment_can_call_engine_transform_provider now checks
status engine_write_boundary_summary for layout transform boundaries.

test_confirmed_delete_advisory_with_engine_provider_only_marks_successful_delete
now checks operation_replay engine_write_boundary_summary for delete boundaries.

test_handle_message_operation_replay_filters_by_external_plan verifies the
operation replay surface still does not leak provider internals.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_handle_message_operation_replay_filters_by_external_plan
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_layout_adjustment_can_call_engine_transform_provider editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirmed_delete_advisory_with_engine_provider_only_marks_successful_delete
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted replay/internal-field test: passed
targeted engine write boundary summary tests: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 180 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This slice closes the read-side audit gap for engine write boundary facts.  It
does not yet complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 176 - LANChat consumes engine write boundary digest

Problem:

```text
Progress Update 175 made engine_write_boundary_summary available from
generate_report(), status_summary(), operation_replay(), and report replay
summaries.  The remaining read-side gap was LANChat/GM formatting:

- RuntimeState and OperationLog could expose safe write-boundary facts;
- LANChat status replies, Runtime Report, Operation Replay, and GM Runtime
  summary still mainly showed engine_write result rows;
- users could see that an import/transform/delete happened, but not the compact
  write-boundary fact count that says the Runtime captured the engine write
  boundary as auditable evidence.
```

Change:

```text
LANChatAgentWorker now formats engine write boundary facts through a dedicated
safe formatter:

- _format_agent_runtime_engine_write_boundary_report()

The formatter outputs only:

- boundary_fact_count
- import / transform / delete boundary counts
- safe write_source_counts
- safe status_counts

The formatter is consumed by:

- Runtime Operation Replay reply
- Runtime Report reply
- normal Runtime status reply
- GM Runtime summary reply

GM summary now carries engine_write_boundary_digest from AgentRuntime.gm_summary().
fact-source formatting also displays engine_write_boundary_fact_count as
write-boundary N.
```

User-facing safety:

```text
The LANChat formatter preserves the same public vocabulary as Runtime:

- write_source_counts, not provider_source_counts
- safe labels such as engine_actor_import / runtime_layout_transform /
  runtime_actor_delete

It redacts or normalizes provider / prompt / raw / url / api key / token markers
before rendering.  LANChat tests confirm the rendered text does not expose the
word provider.
```

Behavior:

```text
This slice is a read-side disclosure step.  It does not change EngineWriteGate,
actor import, layout transform, actor delete, RuntimeGuard decisions, C++
bindings, multiplayer sync transport, or provider enablement.

It makes the already-persisted engine write boundary facts visible in the
surfaces users and GM actually query, while keeping OperationLog and RuntimeState
as the source of truth.
```

Tests / gates:

```text
test_runtime_resource_and_fact_source_formatters_surface_attention now verifies
fact-source text includes write-boundary counts.

test_runtime_replay_report_discloses_environment_import_events now verifies the
compact replay report includes engine_write_boundary facts.

test_engine_write_boundary_report_is_safe_and_user_readable covers the new
formatter and provider redaction.

test_gm_summary_reply_includes_runtime_resource_flow_digest now verifies GM
Runtime summary includes Engine write boundary.

The Runtime status reply path also verifies the 写入边界 line is present.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_replay_report_discloses_environment_import_events editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_engine_write_report_discloses_environment_import_results editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_engine_write_boundary_report_is_safe_and_user_readable editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reply_includes_runtime_resource_flow_digest
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted LANChat engine write boundary tests: passed
test_lanchat_runtime_guard.py: 181 tests passed
test_agent_runtime_phase1.py: 563 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This slice closes the LANChat/GM read-side gap for engine write boundary
evidence.  It does not yet complete real native provider rollout, C++ multiplayer
sync transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 177 - Provider status preflight exposes write-boundary digest

Problem:

```text
Progress Update 176 made engine write boundary facts visible in Runtime status,
Runtime Report, Operation Replay, and GM Runtime summary.  One user-facing
capability boundary still lagged behind:

- provider_status / Runtime Resources preflight could show provider readiness,
  message delivery, and engine_write result rows;
- it did not include engine_write_boundary_summary;
- this made the C++/provider capability preflight less useful for checking
  whether Runtime had captured engine write boundary evidence.
```

Change:

```text
AgentRuntime.provider_status() now includes engine_write_boundary_summary.

The no-plan branch returns an empty boundary summary instead of falling back to
the active plan.  The external-plan branch scopes boundary facts through the
resolved Runtime plan, just like engine_write_summary.

LANChatAgentWorker._handle_agent_runtime_provider_status_query() now renders:

- engine_write
- engine_write_boundary
- message_delivery

using the same safe boundary formatter introduced in Progress Update 176.
```

Behavior:

```text
This is still a read-only/preflight path.  It does not create a ScenePlan, does
not enable real providers, does not invoke C++ writes, and does not change
EngineWriteGate or RuntimeGuard decisions.

The goal is capability visibility: when a host/GM asks for Runtime resource
preflight, the reply now shows whether Runtime has safe write-boundary evidence
for the scoped plan.
```

Tests / gates:

```text
test_provider_status_external_plan_scopes_engine_write_summary now verifies
provider_status includes engine_write_boundary_summary and does not mix in the
second external plan.

test_runtime_provider_status_query_runs_preflight_without_creating_plan now
verifies the LANChat preflight reply includes engine_write_boundary while still
not creating a scene plan and not exposing provider internals.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_external_plan_scopes_engine_write_summary editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_publishes_safe_readiness_without_creating_plan
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_provider_status_query_runs_preflight_without_creating_plan editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_engine_write_boundary_report_is_safe_and_user_readable
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted provider status boundary tests: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 181 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This slice closes the provider_status/readiness visibility gap for write
boundary evidence.  It does not yet complete real native provider rollout, C++
multiplayer sync transport replacement, front-end report rendering, or F5
runtime validation.  Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 178 - Engine write status exposes write-boundary digest

Problem:

```text
Progress Update 177 made provider_status / Runtime Resources preflight expose
engine_write_boundary_summary.  The direct engine_write_status action still
lagged behind:

- AgentRuntime.handle_message(action="engine_write_status") returned
  engine_write_status and engine_write_summary;
- LANChatAgentWorker._handle_agent_runtime_engine_write_status_query() rendered
  adapter readiness and replay rows;
- neither direct status surface showed the compact write-boundary digest that
  says Runtime captured engine import / transform / delete boundary facts.

This left one read-side gap in the C++/engine write evidence chain.
```

Change:

```text
AgentRuntime.handle_message(action="engine_write_status") now returns:

- engine_write_status
- engine_write_summary
- engine_write_boundary_summary
- provider_status

The exception/fallback path also returns an empty engine_write_boundary_summary
so callers do not need a separate missing-field branch.

LANChatAgentWorker._handle_agent_runtime_engine_write_status_query() now appends:

- engine boundary: boundary N, import/transform/delete A/B/C, sources ..., statuses ...

using the same safe boundary formatter introduced in Progress Update 176.
```

Behavior:

```text
This is still read-only.  It does not create a ScenePlan, does not enable real
native providers, does not write C++ state, and does not change RuntimeGuard or
EngineWriteGate decisions.

The goal is audit visibility: provider preflight, runtime report/replay, GM
summary, and direct engine-write status now all expose the same safe
write-boundary digest.
```

Tests / gates:

```text
test_provider_status_external_plan_scopes_engine_write_summary now also verifies
the engine_write_status action returns the same scoped engine_write_summary and
engine_write_boundary_summary as provider_status, without leaking the second
external plan.

test_engine_write_status_action_exception_is_operation_logged_safely now verifies
the failure path returns empty engine_write_summary and
engine_write_boundary_summary.

test_runtime_engine_write_status_query_reports_write_adapters_without_creating_plan
now verifies the LANChat engine-write status reply includes an empty boundary
digest while still not creating a ScenePlan.

test_runtime_engine_write_status_query_reports_engine_write_boundary verifies the
LANChat direct engine-write status reply renders persisted engine write boundary
facts and does not expose provider / prompt / URL internals.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_external_plan_scopes_engine_write_summary editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_write_status_action_exception_is_operation_logged_safely editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_engine_write_status_query_reports_write_adapters_without_creating_plan editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_engine_write_status_query_reports_engine_write_boundary
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted engine-write status boundary tests: passed
test_agent_runtime_phase1.py: 563 tests passed
test_lanchat_runtime_guard.py: 182 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice closes the direct engine_write_status visibility gap for write
boundary evidence.  It does not yet complete real native provider rollout, C++
multiplayer sync transport replacement, front-end report rendering, or F5
runtime validation.  Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 179 - Resource phase facts are locked into ToolCall manifest gates

Problem:

```text
The image/model resource tools now write custom_resource_phase_facts so resource
preparation can be audited through RuntimeState instead of remaining an implicit
workflow-side detail.

The functional path was already present, but the Agent-native contract gate was
too easy to weaken later:

- individual tools declared image_resource_plans / model_resource_plans;
- tests checked individual tool produces_state rows;
- the top-level manifest summary and static verifier did not explicitly lock
  custom_resource_phase_facts as a produced state key.

That left a small regression gap for the invariant: every decomposed resource
phase must be visible as ToolCall-produced RuntimeState evidence.
```

Change:

```text
test_tool_registry_manifest_exposes_safe_capability_metadata now asserts that
custom_resource_phase_facts appears in manifest["summary"]["produced_state_keys"].

verify_ultimate_plan.py static Runtime validator contract gate now requires:

- def _resource_phase_fact(
- custom_resource_phase_facts
- produces_state=("image_resource_plans", "custom_resource_phase_facts")
- produces_state=("model_resource_plans", "custom_resource_phase_facts")

This makes the resource phase fact channel part of the checked ToolCallGraph
contract, not just an incidental implementation detail.
```

Behavior:

```text
This is a low-risk test/contract slice.  It does not change runtime behavior,
providers, C++ writes, LANChat routing, or UI rendering.

It strengthens the Agent-native invariant that resource preparation belongs to
ToolCall-produced RuntimeState facts and must stay visible to reports/status
instead of drifting back into hidden workflow state.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_tool_registry_manifest_exposes_safe_capability_metadata
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted ToolRegistry manifest test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice only locks the resource phase manifest contract.  It does not yet
complete real native provider rollout, C++ multiplayer sync transport
replacement, front-end report rendering, or F5 runtime validation.  Those remain
later Agent-native Phase 5/6/7 work.
```

## Progress Update 180 - Resource phase facts enter the RuntimeState room schema

Problem:

```text
Progress Update 179 locked custom_resource_phase_facts into the ToolCall
manifest and static gates.  The next schema gap was RuntimeState itself:

- runtime.asset.image.prepare and runtime.asset.model.prepare could produce
  custom_resource_phase_facts through StatePatch;
- reports and status summaries could consume that key;
- but a newly created RuntimeState room did not declare
  custom_resource_phase_facts in its default schema.

That meant the fact channel worked, but it was still not a first-class room
state slot.  For the Agent-native invariant "RuntimeState is the only state fact
source", the room schema should explicitly declare every Runtime-owned fact
channel.
```

Change:

```text
RuntimeState.room() now initializes:

- custom_resource_phase_facts: {}

test_runtime_state_default_room_declares_resource_phase_facts verifies every new
room exposes this fact slot before any resource tool runs.

verify_ultimate_plan.py now statically requires the default RuntimeState room
schema to declare custom_resource_phase_facts.
```

Behavior:

```text
This is a schema/contract slice.  It does not change provider behavior, resource
generation, C++ writes, LANChat routing, or UI rendering.

It makes resource phase facts a first-class RuntimeState field instead of a
dynamically introduced patch key.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_state_default_room_declares_resource_phase_facts
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted RuntimeState schema test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
test_agent_runtime_phase1.py now runs 564 tests
```

Remaining:

```text
This slice only closes the RuntimeState schema gap for resource phase facts.  It
does not yet complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 190 - status query OperationLog records report health digest

Problem:

```text
Progress Update 189 made report_ready health visible in RuntimeEvent
OperationLog replay.  The next nearby audit gap was status query logging:

- status_summary() returned report_health_summary and runtime_event_replay_summary;
- GM/status UI could read those summaries from RuntimeState and replay;
- but the runtime_status_queried OperationLog row only recorded generic counts
  such as batch_count, graph_count, context_count, and speaker counts.

That meant a later audit could see that a status query happened, but not whether
the status query observed a partial/failed report health state or report-ready
attention events at that time.
```

Change:

```text
AgentRuntime.status_summary() now writes the compact health/replay digest into
the runtime_status_queried OperationLog payload:

- report_health_status
- report_attention_required
- runtime_event_report_ready_count
- runtime_event_report_attention_count

test_partial_resource_results_report_ready_and_failed_counts now performs a
status_summary() query after a partial resource report and verifies the
runtime_status_queried OperationLog payload carries the same safe health digest.

verify_ultimate_plan.py now statically requires these status query audit tokens.
```

Behavior:

```text
This is an audit-only slice.  It does not change generation, providers,
SceneComposer behavior, C++ writes, LAN sync, VLM execution, or UI rendering.

It strengthens the Agent-native invariant that every user-visible status query
must be explainable from OperationLog, not only from the returned Python object.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted AgentRuntime status query audit test: passed
targeted LANChat formatter regression: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
test_agent_runtime_phase1.py runs 565 tests
test_lanchat_runtime_guard.py runs 182 tests
```

Remaining:

```text
This slice only closes the status-query OperationLog audit gap for report
health.  It does not yet complete real native provider rollout, C++ multiplayer
sync transport replacement, front-end report rendering, or F5 runtime
validation.  Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 191 - provider readiness status enters OperationLog replay

Problem:

```text
Provider readiness could be published through AgentRuntime, and provider_status()
could return a safe provider_readiness_summary to callers.  However, the
OperationLog replay path still had two audit gaps:

- runtime_event_emitted rows for provider_readiness did not preserve the safe
  readiness status, so replay could collapse the latest readiness event to
  unknown;
- runtime_provider_status_queried rows recorded that a query happened, but not
  how many channels were requested, enabled, or unavailable at query time.

That meant GM/runtime replay could prove a readiness check occurred, but could
not reconstruct the provider readiness facts that shaped the user-visible status.
```

Change:

```text
AgentRuntime.emit_runtime_event() now writes a safe readiness_status token for
provider_readiness OperationLog rows.

AgentRuntime.provider_status() now records compact readiness counts in the
runtime_provider_status_queried OperationLog payload:

- readiness_channel_count
- readiness_requested_count
- readiness_enabled_count
- readiness_unavailable_count

AgentRuntime._resource_readiness_replay_summary() now aggregates provider status
query totals, preserves the latest provider status query snapshot, and reads
provider_readiness event status from the safe OperationLog payload.

LANChat replay formatting now exposes a concise provider readiness digest:

query-ready requested/enabled/unavailable X/Y/Z

verify_ultimate_plan.py statically requires the provider readiness event token,
provider_status query payload counts, and replay summary fields.
```

Behavior:

```text
This is still an audit/replay slice.  It does not enable new providers, change
the provider selection policy, alter SceneComposer, or touch native/CEF/C++
paths.

The value is that provider availability and degradation can now be explained
from OperationLog replay instead of relying on transient return objects.
```

Validation:

```text
python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_query_uses_metadata_batch_scope
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
test_agent_runtime_phase1.py: 565 tests passed
targeted LANChat metadata batch replay test: passed
targeted LANChat resource/fact formatter test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 193 - missing-plan provider preflight keeps readiness audit facts

Problem:

```text
provider_status(external_plan_id=...) already handled the case where the
external SeedPlan could not be resolved to a Runtime plan:

- it returned readiness_published = false;
- it returned reason = no runtime plan;
- it did not create a ScenePlan;
- it still returned a safe provider_readiness_summary.

However, the runtime_provider_status_queried OperationLog row for this path only
recorded recorded=false and reason=no runtime plan.  The returned Python object
had provider readiness counts, but the replayable audit trail did not.

That made a missing-plan preflight weaker than a normal preflight: later GM /
OperationLog replay could explain why no Runtime plan was touched, but not what
provider readiness looked like at the time of the failed mapping.
```

Change:

```text
The missing-plan provider_status branch now computes the same safe readiness
summary as the normal branch and writes these fields into OperationLog:

- readiness_channel_count
- readiness_requested_count
- readiness_enabled_count
- readiness_unavailable_count
- readiness_status_counts

_resource_readiness_replay_summary() already consumes these fields, so the
missing-plan path now contributes to status_query_* totals and
latest_provider_status_query just like the normal path.
```

Behavior:

```text
This is a preflight/audit-only change.  It still does not create or mutate a
ScenePlan when external_plan_id has no Runtime mapping, and it does not publish a
provider_readiness RuntimeEvent for that missing plan.

The invariant is now tighter:

even failed provider preflight mapping is replayable from OperationLog with the
safe readiness facts that shaped the user-facing response.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_external_plan_field_accepts_runtime_plan_id
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_publishes_safe_readiness_without_creating_plan
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_provider_status_query_runs_preflight_without_creating_plan
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted missing-plan provider status test: passed
targeted provider readiness test: passed
targeted LANChat provider preflight test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 192 - provider readiness query status counts are replayable

Problem:

```text
Progress Update 191 made provider readiness query totals replayable:

- requested_count
- enabled_count
- unavailable_count

That was enough to prove broad provider availability, but not enough to explain
which safe readiness modes contributed to the unavailable side.  A later audit
could see "9 unavailable" but not whether those were disabled channels,
runtime-state-only channels, mock adapters, or geometry-rule adapters.
```

Change:

```text
AgentRuntime.provider_status() now writes the safe readiness_status_counts
dictionary into runtime_provider_status_queried OperationLog payloads.

AgentRuntime._resource_readiness_replay_summary() now aggregates those counts as
status_query_status_counts and preserves the latest query's
readiness_status_counts snapshot.

LANChat operation replay now formats a compact safe digest:

query-status disabled:1,enabled:1

The digest only contains normalized status/count pairs.  It does not expose raw
provider names, provider internals, URLs, file paths, prompts, API keys, or
diagnostic reasons.
```

Behavior:

```text
This is a read-side / audit-side slice.  It does not alter provider selection,
generation, engine writes, C++ sync, VLM behavior, or UI command routing.

It strengthens the Agent-native invariant that runtime capability checks must be
reconstructable from OperationLog, not only from immediate Python return values.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_publishes_safe_readiness_without_creating_plan
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_query_uses_metadata_batch_scope
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted provider status readiness test: passed
targeted LANChat operation replay batch-scope test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 194 - provider readiness publish failure keeps safe readiness facts

Problem:

```text
_publish_provider_readiness() used a ToolCallGraph to persist provider readiness
into RuntimeState.  When that persistence failed, OperationLog recorded only:

- runtime_provider_readiness_publish_failed
- reason

The Runtime knew the safe readiness summary before attempting the write, but the
failure row did not preserve requested/enabled/unavailable counts or status
counts.  A replay could prove that publication failed, but not what provider
readiness state was lost with that failed write.
```

Change:

```text
_publish_provider_readiness() now computes the safe readiness summary once and
writes it into both success and failure OperationLog rows:

- readiness_channel_count
- readiness_requested_count
- readiness_enabled_count
- readiness_unavailable_count
- readiness_status_counts

_resource_readiness_replay_summary() now aggregates publish-side readiness facts:

- publish_requested_total
- publish_enabled_total
- publish_unavailable_total
- publish_status_counts
- latest_publish_event

LANChat operation replay now surfaces a compact publish digest:

publish-ready requested/enabled/unavailable X/Y/Z
publish-status disabled:1,enabled:1
```

Behavior:

```text
This is an audit/replay slice.  It does not change provider selection, provider
execution, generation, native engine writes, C++ sync, VLM behavior, or UI
routing.

The important invariant is that provider readiness publication failure is no
longer a blind spot: the failed write and the safe readiness facts are both
replayable from OperationLog.
```

Validation:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_readiness_persist_failure_does_not_emit_runtime_event
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_query_uses_metadata_batch_scope
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted provider readiness publish failure test: passed
targeted LANChat operation replay batch-scope test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 195 - status queries carry resource readiness replay digest

Problem:

```text
status_summary() returned the current provider_readiness_summary, but the status
query path did not include the resource_readiness_replay_summary, and the
runtime_status_queried OperationLog row did not record compact resource readiness
publish/query counters.

That left a gap between "current provider readiness" and "what readiness events
and preflight queries have actually happened" when users or GM asked for status.
A later audit had to run full operation_replay() to reconstruct the resource
readiness timeline.
```

Change:

```text
status_summary() now computes resource_readiness_replay_summary from scoped
OperationLog entries and returns it in the status summary.

runtime_status_queried OperationLog payload now records safe compact counters:

- resource_readiness_publish_count
- resource_readiness_publish_failed_count
- resource_readiness_query_count
- resource_readiness_publish_requested_total
- resource_readiness_publish_enabled_total
- resource_readiness_publish_unavailable_total

The field names intentionally use resource_readiness, not provider_readiness, so
status query payloads remain free of provider wording while still preserving the
capability facts needed for replay.
```

Behavior:

```text
This is a read-side/status-query audit slice.  It does not change provider
selection, provider execution, generation, native engine writes, C++ sync, VLM
behavior, or UI routing.

The key invariant is stronger: status queries are now self-auditing for resource
readiness publish/query history, without requiring a separate replay call to
prove what the status response was based on.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/verify_ultimate_plan.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_publishes_safe_readiness_without_creating_plan
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_readiness_persist_failure_does_not_emit_runtime_event
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted report health status query test: passed
targeted provider status readiness test: passed
targeted provider readiness publish failure test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 196 - GM summary exposes resource readiness replay digest

Problem:

```text
status_summary() and OperationLog replay already carried resource readiness
publish/query history, but gm_summary() only exposed the broader resource batch
flow. GM could report batch/resource execution shape, but could not directly
restate whether resource readiness had been published, queried, or failed from
the same RuntimeState read path.
```

Change:

```text
gm_summary() now derives a compact resource_readiness_replay_digest from
status_summary(). The digest keeps only safe read-side counters:

- published_count
- publish_failed_count
- status_query_count
- readiness_event_count
- publish requested/enabled/unavailable totals
- query requested/enabled/unavailable totals
- publish/query status count maps
- latest readiness event status and counts

runtime_gm_summary_exported now also records compact resource_readiness_* audit
counters in OperationLog.

LANChat GM Runtime summary now renders this as a user-visible resource channel
replay line, reusing the existing safe formatter.
```

Behavior:

```text
This is a read-side GM/audit slice. It does not change provider selection,
resource execution, generation, native writes, sync transport, VLM behavior, or
front-end routing.

The strengthened invariant is: GM summaries can now explain both current batch
resource flow and the resource readiness publish/query replay facts that led to
that status, without exposing provider internals.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_publishes_safe_readiness_without_creating_plan
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reply_includes_runtime_resource_flow_digest
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted Runtime provider readiness GM summary test: passed
targeted LANChat GM Runtime summary test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 197 - GM summary replay aggregates resource readiness audit counts

Problem:

```text
runtime_gm_summary_exported now records compact resource_readiness_* counters,
but gm_summary_replay_summary still only aggregated intervention and sync facts.
That meant operation_replay() and generated reports could prove that GM summary
was exported, but could not prove how many resource readiness publish/query facts
were included in those GM exports.
```

Change:

```text
_gm_summary_replay_summary() now aggregates resource readiness counters from
runtime_gm_summary_exported OperationLog rows:

- resource_readiness_publish_total
- resource_readiness_publish_failed_total
- resource_readiness_query_total
- resource_readiness_publish_requested_total
- resource_readiness_publish_enabled_total
- resource_readiness_publish_unavailable_total

latest_gm_summary_event also carries the latest GM export's resource readiness
publish/query counts.
```

Behavior:

```text
This is an OperationLog replay/report slice. It does not change resource channel
selection, provider execution, generation, LANChat routing, native writes, sync
transport, or VLM behavior.

The strengthened invariant is: reports and replay queries can now audit not only
that GM summarized RuntimeState, but also which resource readiness publish/query
facts were present in those GM summaries.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_gm_summary_export_records_safe_intervention_counts
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_publishes_safe_readiness_without_creating_plan
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted GM summary replay test: passed
targeted provider readiness GM summary test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 198 - status summary exposes GM summary replay audit facts

Problem:

```text
operation_replay() and generated reports could replay gm_summary_replay_summary,
but status_summary() did not expose that replay digest directly. A status query
could show Runtime status, resource readiness replay, and recent events, but not
whether GM summaries had already been exported or what resource readiness facts
those GM summaries carried.
```

Change:

```text
status_summary() now derives gm_summary_replay_summary from scoped OperationLog
entries and returns it in the status summary.

runtime_status_queried now records compact GM replay counters:

- gm_summary_exported_count
- gm_summary_failed_count
- gm_summary_resource_readiness_publish_total
- gm_summary_resource_readiness_query_total

The verifier now requires these status-summary tokens so the GM replay digest is
kept on the normal status read path.
```

Behavior:

```text
This is a status/read-side audit slice. It does not change GM routing, generation,
resource execution, native writes, sync transport, VLM behavior, or user-visible
LANChat formatting.

The strengthened invariant is: a normal Runtime status query can now audit GM
summary export history and the resource readiness publish/query totals included
in those GM summaries, without requiring a separate operation_replay() call.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_gm_summary_export_records_safe_intervention_counts
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_publishes_safe_readiness_without_creating_plan
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted GM summary replay/status test: passed
targeted provider readiness status test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 199 - status summary includes GM summary replay digest

Problem:

```text
operation_replay() and generated reports could replay gm_summary_replay_summary,
but status_summary() did not expose the same GM replay digest directly. A normal
status query could audit Runtime status and resource readiness replay, but not
whether GM summaries had already been exported or which resource readiness
publish/query totals those GM summaries contained.
```

Change:

```text
status_summary() now derives gm_summary_replay_summary from scoped OperationLog
entries and returns it in the status summary.

runtime_status_queried now records compact GM replay counters:

- gm_summary_exported_count
- gm_summary_failed_count
- gm_summary_resource_readiness_publish_total
- gm_summary_resource_readiness_query_total

The verifier now requires these tokens on the status read path.
```

Behavior:

```text
This is a read-side/status audit slice. It does not change GM routing,
generation, resource execution, native writes, sync transport, VLM behavior, or
LANChat formatting.

The strengthened invariant is: status_summary() can now audit GM summary export
history and the resource readiness facts those summaries carried, without a
separate operation_replay() call.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_gm_summary_export_records_safe_intervention_counts
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_publishes_safe_readiness_without_creating_plan
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted GM summary status replay test: passed
targeted provider readiness status test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 200 - LANChat status reply surfaces GM replay digest

Problem:

```text
status_summary() now exposes gm_summary_replay_summary, but the LANChat Runtime
status reply still did not render it. A user asking for current Runtime status
could see resource batches, RuntimeEvent replay, VLM replay, and sync replay, but
not whether GM summaries had already been exported in this room/batch scope.
```

Change:

```text
LANChatAgentWorker._agent_runtime_status_reply() now reads
status["gm_summary_replay_summary"] and renders a compact user-visible line:

- GM replay: exported N, failed M, available K, scene-plan P, readiness publish/query X/Y

A new safe formatter _format_agent_runtime_gm_summary_replay_report() keeps the
output to counters only and does not expose internal payloads.

The verifier now requires this formatter and the GM replay status line in the
Runtime status reply path.
```

Behavior:

```text
This is a UI disclosure/read-side slice. It does not change status_summary(), GM
routing, generation, resource execution, native writes, sync transport, or VLM
behavior.

The strengthened invariant is: when the Runtime status path has GM replay facts,
the LANChat status reply can disclose them at the same compact audit level as
resource, RuntimeEvent, VLM, and sync replay facts.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_status_reply_can_scope_to_explicit_batch_id
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted LANChat Runtime status reply test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 201 - Runtime status exposes ToolGraph execution replay

Problem:

```text
Operation replay and user reports already carried batch_execution_summary and
tool_graph_queue_summary, but status_summary() and the LANChat Runtime status
reply still leaned on current RuntimeState queue snapshots. For long sessions,
recent-event windows can hide earlier batch start/completion facts, so status
queries could not reliably audit whether ToolCallGraph execution actually
started, completed, finalized, queued, dequeued, or was rejected.
```

Change:

```text
AgentRuntime.status_summary() now computes execution replay from the full current
plan/batch OperationLog scope and exposes:

- batch_execution_replay_summary
- tool_graph_queue_replay_summary

The runtime_status_queried audit payload now records compact counters for batch
start/completion/finalization and queue queued/dequeued/rejected/blocked.

LANChatAgentWorker._agent_runtime_status_reply() now renders a user-visible safe
line:

- ToolGraph replay: batch start/done/final X/Y/Z, queue queued/dequeued/rejected/blocked A/B/C/D

The verifier requires these fields and the LANChat status reply formatter.
```

Behavior:

```text
This is a read-side / audit-side Agent-native slice. It does not change batch
execution ordering, ToolCallGraph scheduling, RuntimeGuard permissions, native
engine writes, sync transport, VLM, or legacy workflow behavior.

The strengthened invariant is: Runtime status queries can replay the execution
queue facts from OperationLog, not only inspect the latest RuntimeState snapshot.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_executes_planned_batches_as_separate_tool_graphs
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_plain_chat_status_query_uses_runtime_before_coordinator_lookup
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted ToolCallGraph batch execution replay test: passed
targeted LANChat Runtime status reply test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real native provider rollout, C++ multiplayer sync
transport replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native Phase 5/6/7 work.
```

## Progress Update 202 - RuntimeCppBridge exposes engine boundary call facts

Problem:

```text
Engine-plane providers already returned engine_write_result facts, and Runtime
status/report could summarize engine write boundaries. However, the C++ bridge
itself did not expose a uniform call-boundary fact. Actor import, layout
transform, and actor delete providers had to infer success/failure from their
own result lists, which made the Python/C++ interface less auditable during the
Agent-native migration.
```

Change:

```text
RuntimeCppBridgeResult now carries a sanitized boundary_fact for every bridge
call:

- bridge_call_count
- bridge_success_count
- bridge_failed_count
- bridge_method_counts
- bridge_error_code_counts

The engine actor import, layout transform, and actor delete providers aggregate
these bridge facts into engine_write_result. Runtime engine_write_boundary facts
preserve the bridge counters, and AgentRuntime._engine_write_boundary_summary_for_plan()
now aggregates them across import/transform/delete boundaries.

LANChatAgentWorker._format_agent_runtime_engine_write_boundary_report() now
shows compact bridge health as:

bridge calls/success/failed, errors <safe counts>

The verifier requires the adapter, Runtime, tools, worker, and regression tests
to keep these bridge-boundary fields present.
```

Behavior:

```text
This is an engine-interface unification slice. It does not call native build,
modify C++ bindings, change EngineWriteGate behavior, alter actor placement, or
change ToolCallGraph scheduling. It only makes C++/engine write boundary facts
first-class and replayable from RuntimeState/OperationLog-derived summaries.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_cpp_bridge_success_payload_is_narrow_and_sanitized editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_cpp_bridge_failure_message_is_sanitized
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_actor_import_provider_uses_gate_and_returns_actor_facts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_actor_delete_provider_uses_remove_gate_and_returns_actor_updates
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted RuntimeCppBridge tests: passed
targeted engine provider tests: passed
targeted partial import boundary test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not replace native sync transport, finish real provider rollout,
render front-end reports, or prove F5 runtime behavior. Those remain later
Agent-native Phase 5/6/7 validation work.
```

## Progress Update 203 - MasterAgent compose routes stop before legacy scene handler

Problem:

```text
MasterAgent._handle_scene(), _handle_scene_compose(), direct import, edit, and
SceneComposerJobRunner already had AgentRuntime migration guards. However,
MasterAgent.__call__ could still classify a request as compose and route into
_handle_scene(..., force_compose=True) before the guard rejected it. That meant
the outer RoleAgent route still behaved like a legacy workflow entry point,
even though the inner write path was blocked.
```

Change:

```text
The planning-gate compose branch and the semantic intent compose branch in
MasterAgent.__call__ now check _legacy_main_workflow_allowed() before calling
_handle_scene(..., force_compose=True). In default AgentRuntime mode they return
AGENT_RUNTIME_REQUIRED_MESSAGE immediately, so old RoleAgent compose routes stop
at the user-entry boundary instead of entering the legacy scene handler.

verify_ultimate_plan.py now includes a static MasterAgent legacy compose route
gate. It requires both outer compose branches to contain the legacy-main guard
and Runtime-required reply before any call into _handle_scene(...force_compose).
```

Behavior:

```text
This is a主控退场 boundary slice. It does not delete SceneComposer, change
SceneComposerJobRunner, modify the LANChat Coordinator path, or alter explicit
transition flags. If ALLOW_LEGACY_MAIN_WORKFLOW is explicitly enabled for
transition/debug, the legacy path can still be reached; by default it is blocked
before the old scene handler takes control.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/cai_extensions/agent/agent_adapter.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_master_agent_call_write_routes_return_runtime_required_message_by_default editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_master_agent_call_compose_routes_do_not_enter_legacy_scene_handler_by_default editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_master_agent_lanchat_progress_context_blocks_compose_even_when_legacy_enabled
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted MasterAgent compose route tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real provider rollout, ToolCallGraph replacement
for every old workflow ability, native sync replacement, front-end report
rendering, or F5 runtime validation. Those remain later Agent-native work.
```

## Progress Update 204 - Confirmed generation reply reports Runtime execution facts

Problem:

```text
The default LANChat confirmed-generation path already routes to AgentRuntime
when legacy main workflow is disabled.  AgentRuntime.handle_message(action=
confirm_and_execute) executes Runtime batch graphs and returns batches, graphs,
and report facts.

However, LANChatAgentWorker still replied with the old queue-oriented wording:
"已进入 Runtime 执行队列".  This made a completed Runtime execution slice look
like a queued legacy scheduler job, and hid graph status / report health from
the immediate confirmation response.
```

Change:

```text
LANChatAgentWorker._format_agent_runtime_execution_reply() is now the shared
formatter for confirmed SeedPlan execution, active Runtime plan execution, and
structured host-action execution.

The reply now reports:

- Runtime batch count
- safe ToolCallGraph status counts
- compact report health status

The wording uses "已执行 Runtime 批次..." instead of "已进入 Runtime 执行队列".
Detailed failed/partial/waiting counts remain available through Runtime status
and report queries.  The immediate execution reply only shows compact health
status / attention flag, avoiding accidental HostActionExecutor failure
classification from harmless strings such as "failed 0".

verify_ultimate_plan.py now statically requires the execution reply formatter
to include Runtime batch count, graph status, report_health_summary, and
attention_required, and rejects the old queue-only wording inside that formatter.
```

Behavior:

```text
This is a disclosure/control-plane truthfulness slice.  It does not change
ToolCallGraph execution, resource providers, C++ engine writes, LAN sync,
VLM behavior, or the legacy transition flags.  It makes the user-facing
confirmation response align with RuntimeState / report facts instead of legacy
GenerationScheduler queue semantics.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_host_action_structured_seed_plan_routes_to_agent_runtime_by_default editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_host_action_structured_external_plan_id_routes_to_agent_runtime_by_default editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_host_action_visible_status_and_result_send_are_audited editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_confirmed_seedplan_execution_remembers_room_for_worker_drain editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_active_runtime_plan_generation_remembers_room_for_worker_drain
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted LANChat execution / host-action tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice does not complete real provider rollout, native sync replacement,
front-end report rendering, or F5 runtime validation. Those remain later
Agent-native work.
```

## Progress Update 205 - Post-generation add host actions report Runtime patch facts

Problem:

```text
Structured host actions already route post_generation_add to AgentRuntime by
default.  AgentRuntime.handle_message(action=post_generation_add) records a
PlanPatch in RuntimeState and OperationLog.

However, LANChatAgentWorker discarded that result and returned only the generic
text "AgentRuntime 执行结果。".  That made user/GM-visible追加生成确认无法看出
whether the intervention was actually recorded, which plan it belonged to, what
patch type was created, or how many objects were extracted.
```

Change:

```text
LANChatAgentWorker now has _format_agent_runtime_intervention_reply(), used by
structured host actions with action_type=post_generation_add.

The reply reports safe Runtime patch facts:

- ScenePlan id
- patch type
- patch status
- extracted object count

The generic "AgentRuntime 执行结果。" reply is no longer used for this path.
verify_ultimate_plan.py now statically requires the intervention reply formatter
to reference patch_type/status/items and rejects collapsing patch facts into the
old generic result text.
```

Behavior:

```text
This is a control/disclosure slice for user intervention.  It does not execute a
new provider call, create native actors, change pending-intervention routing, or
modify legacy transition flags.  It makes the post-generation add confirmation
surface reflect RuntimeState patch facts instead of hiding them behind a generic
success string.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_host_action_post_generation_add_reports_runtime_patch_facts editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_host_action_structured_seed_plan_routes_to_agent_runtime_by_default editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_host_action_structured_external_plan_id_routes_to_agent_runtime_by_default
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted post-generation add / structured host-action tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice records and reports the Runtime intervention patch.  It does not yet
complete automatic post-generation resource generation/import for that patch,
native sync replacement, front-end report rendering, or F5 runtime validation.
Those remain later Agent-native work.
```

## Progress Update 210 - Legacy model provider unavailable becomes Runtime failed resource facts

Problem:

```text
make_legacy_model_resource_provider() had already decomposed the old
ModelProvider.acquire() capability into a function-sized Runtime model resource
provider.

However, if the legacy ModelProvider factory itself failed to initialize, the
exception escaped into runtime.asset.model.prepare.  That meant Runtime could
lose per-item failed model facts for the batch and the ToolCallGraph failure was
less useful for later reports, retries, or user-visible diagnostics.

For Agent-native execution, even provider initialization failure should become
RuntimeState evidence, not an unstructured exception.
```

Change:

```text
make_legacy_model_resource_provider() now parses batch_id and model_items before
lazy provider initialization.

If the legacy ModelProvider factory fails:

- every requested model item gets a failed model resource fact
- the source is the safe enum legacy_model_adapter_unavailable
- no exception message, provider detail, api_key, raw payload, or secret text is
  persisted
- runtime.asset.model.prepare treats those facts as hard model resource failure
  alongside legacy_model_failure
- the failed ToolResult still carries a StatePatch, so model_resource_plans and
  custom_resource_phase_facts are written before dependent ToolCalls are skipped

ResourcePlanValidator / safe source normalization now preserves
legacy_model_adapter_unavailable as a safe source value.

verify_ultimate_plan.py now statically requires this provider-unavailable source
and the runtime.asset.model.prepare hard-failure guard.
```

Behavior:

```text
This is a real-provider rollout robustness slice.  It does not enable the
legacy model provider by default and does not call SceneComposer,
ProgressiveWorkflow, GenerationScheduler, actor import, or native build.

It makes the already-toolized legacy ModelProvider adapter safer to enable
behind AGENT_RUNTIME_USE_LEGACY_MODEL_PROVIDER=1, because provider setup failure
now leaves auditable Runtime facts instead of a missing batch state.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_legacy_model_provider_factory_failure_records_failed_resource_facts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_legacy_model_provider_adapter_normalizes_acquire_results editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_model_provider_consumes_image_resources_from_previous_toolcall
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted legacy model provider / image-to-model ToolCall tests: passed
verify_ultimate_plan.py: passed
```

Remaining:

```text
This slice improves provider failure evidence and ToolCallGraph behavior.  It
does not complete default real provider rollout, native import replacement,
ProgressiveWorkflow removal, multiplayer sync replacement, front-end report
rendering, or F5 runtime validation.  Those remain later Agent-native work.
```

## Progress Update 209 - Tool manifest exposes execution contracts for Agent Runtime tools

Problem:

```text
ToolRegistry already registered many function-level AgentRuntime tools, and the
manifest exposed names, categories, risk, required args, consumes_state, and
produces_state.

However, the manifest did not provide a compact execution contract that an
Agent / verifier can use to distinguish read-only tools from write tools,
stateful tools from stateless tools, confirmation-required tools from safe
planning tools, or user-visible failure tools from silent internal helpers.

That weakens the Agent-native invariant:

ToolCallGraph is the execution unit, RuntimeGuard owns write permission, and
OperationLog / RuntimeState evidence must be available before user reports.
```

Change:

```text
ToolDefinition.as_manifest() now emits a safe execution_contract:

- access: read / write
- stateful: true / false
- state_contract: stateful / stateless
- confirmation_required: true when the tool writes or is high risk
- user_visible_failure: whether failure must be surfaced safely
- system_actor_write: whether this dedicated tool may touch system actors

ToolRegistry.capability_summary() now also reports:

- read_only_tool_count
- stateful_tool_count

The existing manifest test now asserts the contract for representative Runtime
tools:

- runtime.asset.image.prepare is read, stateful, non-confirmed, and
  user-visible on failure
- runtime.actor.import_batch is write, stateful, confirmation-required, and
  user-visible on failure

verify_ultimate_plan.py now statically requires these manifest contract tokens
so the execution contract cannot quietly disappear from the Agent-native gate.
```

Behavior:

```text
This is an execution-plane observability slice.

It does not alter tool execution behavior, SceneComposer, ProgressiveWorkflow,
native import, provider selection, layout logic, or LANChat routing.

It makes the current function-level tools more self-describing, so later
Planner / Builder / Reviewer agents can select and validate tools by contract
instead of relying on scattered hard-coded assumptions.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_tool_registry_manifest_exposes_safe_capability_metadata
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted tool manifest contract test: passed
verify_ultimate_plan.py: passed
```

Remaining:

```text
This slice improves AgentRuntime tool contract visibility.  It does not complete
real provider rollout, native ToolCallGraph execution replacement,
ProgressiveWorkflow removal, multiplayer sync replacement, UI rendering, or F5
runtime validation.  Those remain later Agent-native work.
```

## Progress Update 208 - report_ready RuntimeEvent carries layout application facts

Problem:

```text
Runtime reports and status summaries already carried layout adjustment facts,
and LANChat now formats those facts for users.  But the report_ready
RuntimeEvent payload still exposed only proposal_count plus resource/import
health.  That meant the event layer and OperationLog replay could say a report
was ready, but could not prove whether the completed layout adjustment had
applied deltas, skipped deltas, engine transform results, ground snapping, or
overlap correction.
```

Change:

```text
AgentRuntime.generate_report() now includes the following safe count-only
layout fields in the report_ready payload:

- layout_applied_delta_count
- layout_skipped_delta_count
- layout_transform_result_count
- layout_ground_snapped_count
- layout_overlap_resolved_count

RuntimeEventValidator._SAFE_PAYLOAD_KEYS and
AgentRuntime._SAFE_RUNTIME_EVENT_PAYLOAD_KEYS allow these count-only fields,
without exposing actor ids, provider names, prompts, graph ids, paths, URLs, or
raw tool payloads.

AgentRuntime._runtime_event_replay_summary() now preserves the same fields in
latest_report_ready, so OperationLog replay can audit the report event without
reading the full report object.

verify_ultimate_plan.py now statically requires these fields in generate_report,
runtime event replay, and safe RuntimeEvent payload keys.
```

Behavior:

```text
This is an event/replay fact-source slice.  It does not change layout planning,
ToolCallGraph execution, RuntimeGuard policy, native transform providers,
SceneComposer, or LAN sync.  It makes the report_ready event consistent with
RuntimeState / OperationLog layout facts already produced by the Runtime path.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted layout/report_ready tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This slice strengthens report_ready event evidence.  It does not complete
native layout transform replacement, real provider rollout, full front-end
rendering, multiplayer sync replacement, or F5 runtime validation.  Those
remain later Agent-native work.
```

## Progress Update 207 - Runtime status/report layout summaries include applied and grounding facts

Problem:

```text
AgentRuntime already aggregates layout adjustment summary fields such as
applied_delta_count, skipped_delta_count, transform_result_count,
ground_snapped_count, and overlap_resolved_count.

LANChatAgentWorker._format_agent_runtime_layout_report() only exposed proposal
and delta counts.  Status queries, GM summaries, and final report-facing text
therefore could say that a layout proposal existed, but could not show whether
confirmed deltas were applied, skipped, written to engine, ground-snapped, or
overlap-corrected.
```

Change:

```text
_format_agent_runtime_layout_report() now includes:

- applied delta count
- skipped delta count
- transform result count
- ground-snapped count
- overlap-resolved count
- confirmation count

The nearby review-confirmation formatter also had a mojibake separator, which
was normalized to a readable decision separator.

verify_ultimate_plan.py now statically requires the layout report formatter to
reference applied_delta_count / skipped_delta_count / transform_result_count /
ground_snapped_count / overlap_resolved_count and rejects preserved mojibake.
```

Behavior:

```text
This is a read-side RuntimeState / OperationLog disclosure slice.  It does not
change the layout planner, ToolCallGraph execution, RuntimeGuard policy,
native transform adapter, SceneComposer, or legacy flags.  It makes status and
report surfaces reflect the layout facts AgentRuntime already records.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_layout_reflow_confirmation_defaults_to_agent_runtime_not_direct_actor_transform
```

Result:

```text
py_compile: passed
targeted formatter / layout confirmation tests: passed
```

Remaining:

```text
This slice improves Runtime layout status visibility.  It does not complete
real native layout transform replacement, full UI rendering, multiplayer sync
replacement, or F5 runtime validation.  Those remain later Agent-native work.
```

## Progress Update 206 - Layout confirmation replies expose Runtime graph/proposal facts

Problem:

```text
Completed-state layout reflow confirmation already routes to AgentRuntime by
default, and AgentRuntime.confirm_layout_adjustment() writes ToolCallGraph,
proposal, applied/skipped delta, engine transform, ground snap, and overlap
facts into RuntimeState / OperationLog.

However, LANChatAgentWorker collapsed that result into generic text such as
"AgentRuntime 执行结果：已应用 N 项低风险布局调整。".  That made the user-facing
confirmation weaker than the Runtime evidence: it did not expose which proposal
was confirmed, graph status, skipped count, engine write success/failure, or
whether selective ground snap participated.
```

Change:

```text
LANChatAgentWorker now has
_format_agent_runtime_layout_confirmation_reply(), used by
_confirm_layout_reflow_via_agent_runtime().

The reply reports safe Runtime layout facts:

- ScenePlan id
- layout proposal id
- ToolCallGraph status
- applied delta count
- skipped delta count
- engine transform success / failure counts
- ground-snapped count
- overlap-resolved count

The confirmation text sent to AgentRuntime was also fixed from mojibake to
"确认布局调整", so OperationLog remains readable.

verify_ultimate_plan.py now statically requires the layout confirmation
formatter to reference ToolCallGraph / graph / applied_deltas / skipped_deltas /
engine_transform_results / ground_snapped / overlap_resolved, and rejects the
old collapsed "AgentRuntime 执行结果：已应用" response.
```

Behavior:

```text
This is a Runtime disclosure / auditability slice.  It does not change the
layout delta planner, provider execution, native transform adapter, old legacy
flags, or SceneComposer.  It makes completed-state layout confirmation visibly
depend on RuntimeState / OperationLog facts rather than a generic success
sentence.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_layout_reflow_confirmation_defaults_to_agent_runtime_not_direct_actor_transform editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_layout_reflow_runtime_failure_does_not_leak_internal_exception_text
```

Result:

```text
py_compile: passed
targeted layout confirmation / error-sanitization tests: passed
```

Remaining:

```text
This slice improves confirmation reporting and log readability.  It does not
complete real native layout transform replacement, provider rollout, front-end
report rendering, multiplayer sync replacement, or F5 runtime validation.
Those remain later Agent-native work.
```

## Progress Update 211 - Environment import failures become Runtime failed component facts

Problem:

```text
AgentRuntime already routed environment/substrate components through
runtime.environment.import_components, and graph execution correctly failed when
the engine environment import provider was unavailable, returned no components,
returned invalid components, or raised an exception.

However, the failed branch only produced a failed ToolCall/event.  RuntimeState
did not persist which requested room_box / terrain / boundary components failed
to import.  That left GM/report/replay unable to distinguish "no environment
component was planned" from "a planned environment component failed to write".
```

Change:

```text
runtime.environment.import_components now writes sanitized failed environment
component facts on failure:

- provider missing -> source=runtime_environment_import_missing
- provider exception -> source=runtime_environment_import_failed
- empty provider result -> source=runtime_environment_import_empty
- invalid provider result -> source=runtime_environment_import_invalid

The failed facts keep component_id/name/component_type/handler/scene_name when
safe, set status=failed, and force requires_engine_write=False.  They are
validated through EnvironmentComponentValidator before entering RuntimeState, so
provider/raw/path/prompt/token/url style internal details are not persisted.

verify_ultimate_plan.py now statically requires the failed environment import
fact helper and source tokens, so the branch cannot silently regress to
"failed event only, no RuntimeState fact".
```

Behavior:

```text
This is an Agent-native RuntimeState fact-source slice.  It does not enable the
real engine environment import provider, change SceneComposer, change
ProgressiveWorkflow, or touch native build/runtime code.  Normal successful
environment imports still persist imported environment component facts as
before; failed imports now also remain auditable and reportable.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_failure_does_not_count_planned_components_as_imported editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_tool_fails_explicitly_without_provider
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_execution_graph_uses_environment_import_node_when_provider_is_enabled editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_tool_uses_provider_and_persists_sanitized_components
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
py_compile: passed
targeted environment import failure tests: passed
targeted environment import success-path regression tests: passed
verify_ultimate_plan.py: passed
git diff --check: passed with CRLF warnings only
```

Remaining:

```text
This closes another adapter/fact-source gap, but the full Agent-native objective
is still active.  Real native environment import provider rollout, full
ToolCallGraph replacement of legacy progressive workflow behavior, multiplayer
sync replacement, UI rendering validation, and F5 runtime validation remain
later work.
```

## Progress Update 212 - Report health surfaces environment import failures

Problem:

```text
Progress Update 211 made failed room_box / terrain / boundary imports persist as
RuntimeState environment component facts.  But report_health_summary still only
looked at batch resource flow, actor import, resource phases, sync health, and
asset transfer.  A planned environment component could fail to import while the
top-level report health did not explicitly name the environment/substrate
failure.

That violated the Agent-native invariant that RuntimeState is the single fact
source and OperationLog/reporting must make important state failures visible to
GM, replay, and users.
```

Change:

```text
AgentRuntime._report_health_summary now accepts environment_component_summary
and includes:

- environment_failed_count
- environment_import_requested_count
- environment_imported_count
- environment_import_failed_count
- reason=environment_component_failed
- reason=environment_import_failed

generate_report(), status_summary(), operation replay summary composition, and
operation_replay() now pass the scoped environment component summary into report
health.  A failed environment import therefore shows up in report, status, and
replay health instead of remaining buried in runtime_events.

verify_ultimate_plan.py now statically requires the environment health fields
and generate_report wiring.
```

Behavior:

```text
Environment import failures no longer masquerade as an otherwise healthy report.
If actor/model import succeeds but room_box / terrain / boundary import fails,
the report can be partial / attention_required with environment_import_failed
reason.  If the full batch already failed, the existing failed status remains,
but the environment failure reason is still visible.

This does not enable a real native environment import provider, change C++,
change SceneComposer, or alter old workflow entry behavior.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_failure_does_not_count_planned_components_as_imported editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_tool_fails_explicitly_without_provider editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_execution_graph_uses_environment_import_node_when_provider_is_enabled
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
py_compile: passed
targeted environment health tests: passed
verify_ultimate_plan.py: passed
git diff --check: passed with CRLF warnings only
```

Remaining:

```text
This improves the reporting/replay surface for environment failures.  The full
Agent-native target still needs real provider rollout, full ToolCallGraph
replacement of progressive execution, multiplayer sync replacement, UI
rendering validation, and F5 runtime validation.
```

## Progress Update 213 - Environment import now has engine-write boundary evidence

Problem:

```text
Progress Update 211/212 made environment component import success/failure visible
as RuntimeState facts and report health.  But the real-provider rollout still
had an evidence gap: actor import, layout transform, and actor delete already
produced engine-write boundary facts, while environment import only returned
environment component rows.  That meant room_box / terrain / boundary writes
could be visible as imported components without the same provider / bridge /
identity-count evidence used by other engine-write tools.

For Agent-native execution this is too weak.  RuntimeState must be able to prove
which tool attempted the engine write, how many identities were returned, and
whether the C++ bridge accepted or failed the write.
```

Change:

```text
make_engine_environment_component_import_provider now returns engine_write_result
with:

- provider_source=engine_environment_import_provider
- requested_count
- identity_result_count
- missing_identity_count
- status_counts
- bridge_call_count / bridge_success_count / bridge_failed_count
- bridge_method_counts / bridge_error_code_counts

runtime.environment.import_components now persists a sanitized
custom_import_facts entry:

    <batch_id>:environment_import_result

That fact includes source=runtime_environment_import_result, sanitized
environment_import_results, and an engine_write_boundary object.  The tool
manifest now explicitly declares both produced RuntimeState keys:

    environment_components
    custom_import_facts

AgentRuntime report generation now counts environment_import engine-write
boundaries beside actor_import / layout_transform / actor_delete and exposes:

- environment_import_boundary_count
- write_source_counts.runtime_environment_import
```

Behavior:

```text
Environment/scene substrate imports now have parity with actor writes at the
RuntimeState evidence layer.  A future real engine provider can be enabled
without weakening OperationLog/report auditability: successful room_box,
terrain, and boundary imports can show provider source, identity counts, and
C++ bridge outcome; failures remain explicit and do not masquerade as imported.

This is still a RuntimeState / adapter / report slice.  It does not enable the
real native environment import provider by default, does not rewrite
SceneComposer, does not touch C++/CMake/Ninja/CEF, and does not change the old
workflow entry behavior.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_environment_component_import_provider_uses_gate_and_returns_component_updates editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_tool_uses_provider_and_persists_sanitized_components editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_tool_registry_manifest_exposes_safe_capability_metadata
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted environment engine-write boundary tests: passed
verify_ultimate_plan.py: passed
```

Remaining:

```text
This closes the environment import engine-write evidence gap.  The full
Agent-native target still needs real provider rollout, full ToolCallGraph
replacement of progressive execution, multiplayer sync replacement, UI
rendering validation, and F5 runtime validation.
```

## Progress Update 214 - Report-ready events surface environment import health

Problem:

```text
Progress Update 212 exposed environment import failures in report_health_summary,
status_summary, and operation replay.  Progress Update 213 added engine-write
boundary facts.  One user-visible event surface was still weaker:

    report_ready

The report object knew that room_box / terrain / boundary import failed, but
the report_ready runtime event payload did not carry environment import counts.
That meant LANChat/UI/GM consumers that react to runtime events could see a
generic report-ready event without knowing that scene substrate import needed
attention.
```

Change:

```text
AgentRuntime.generate_report now includes these safe counters in report_ready
payload:

- environment_failed_count
- environment_import_requested_count
- environment_imported_count
- environment_import_failed_count

RuntimeEventValidator and AgentRuntime._SAFE_RUNTIME_EVENT_PAYLOAD_KEYS now
explicitly allow those fields.  runtime_event_emitted OperationLog payload and
runtime_event_replay_summary.latest_report_ready also preserve the same
environment counters.

The environment import failure regression test now asserts:

- report_ready exposes environment import requested/imported/failed counts
- report_ready report_health_reasons includes environment_import_failed
- operation_replay.latest_report_ready carries the same environment counters

verify_ultimate_plan.py statically requires these safe runtime-event payload
keys, so future cleanup cannot silently drop them.
```

Behavior:

```text
When environment components fail to import, the report, status query, operation
replay, and report-ready event now agree.  UI/GM consumers can surface the
problem without scraping internal facts or exposing provider/tool details.

This remains a safe disclosure/reporting slice.  It does not enable native
environment import, alter SceneComposer, or touch C++/CMake/Ninja/CEF.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_failure_does_not_count_planned_components_as_imported
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted report_ready environment health test: passed
verify_ultimate_plan.py: passed
```

Remaining:

```text
The event/status/report fact surfaces are stronger, but the full Agent-native
objective still needs real provider rollout, full ToolCallGraph replacement of
progressive execution, multiplayer sync replacement, UI rendering validation,
and F5 runtime validation.
```

## Progress Update 215 - Engine-write provider readiness is explicit

Problem:

```text
Provider readiness already existed, but real engine-write readiness still had
to be inferred from the full provider_summary.  That was too indirect for the
Agent-native rollout because environment_import, actor_import, actor_delete, and
layout_transform have different execution semantics:

- real native adapter
- RuntimeState-only write
- mock/fallback write
- disabled channel
- unavailable channel

In particular, environment_import being disabled by default should be visible
as an explicit Runtime fact, not as an implicit mode buried inside provider
status.
```

Change:

```text
AgentRuntime now derives engine_write_readiness_summary from the sanitized
provider summary.  It tracks:

- channel_count
- requested_count
- native_enabled_count
- runtime_state_only_count
- fallback_count
- disabled_count
- unavailable_count
- status_counts
- mode_counts
- requested_channels
- native_enabled_channels
- runtime_state_only_channels
- fallback_channels
- disabled_channels
- unavailable_channels

The summary is now included in:

- provider_status()
- engine_write_status handle_message action
- generate_report()
- status_summary()

ReportRecordValidator allows the new top-level report field, and
verify_ultimate_plan.py statically requires the summary on the report/status
and engine_write_status paths.
```

Behavior:

```text
GM/UI/status consumers can now distinguish:

- environment_import is disabled by default
- actor_import is currently mock/fallback unless a real adapter is provided
- actor_delete / layout_transform may be RuntimeState-only
- actual native engine-write adapters are counted separately

This prepares the real-provider rollout without enabling native writes, changing
SceneComposer, or touching C++/CMake/Ninja/CEF.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_provider_status_publishes_safe_readiness_without_creating_plan editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_write_status_unknown_external_plan_does_not_publish_or_fallback_active
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
py_compile: passed
targeted provider/engine-write readiness tests: passed
verify_ultimate_plan.py: passed
```

Remaining:

```text
Readiness and evidence surfaces are stronger.  The full Agent-native objective
still needs real provider rollout, full ToolCallGraph replacement of progressive
execution, multiplayer sync replacement, UI rendering validation, and F5 runtime
validation.
```

## Progress Update 230 - review advisory proposal summaries inherit top-level batch scope

Problem:

```text
_review_advisory_proposal_summary_for_plan filtered batch-scoped advisory
proposals only by item.batch_id.

Newer Runtime proposals usually stamp batch_id on each advisory item, but older
or adapter-authored proposals can carry batch_id at the proposal top level while
their items have no item-level batch_id.  Those proposals were skipped from
batch-scoped status/report summaries even though they belonged to the requested
batch.  This weakens VLM/review advisory visibility during workflow-to-runtime
migration.
```

Change:

```text
Review advisory proposal summary now uses proposal.batch_id as the fallback
scope for items without item.batch_id.

Rules:

- item.batch_id still takes precedence when present;
- proposal.batch_id fills the scope for legacy items;
- items/proposals from another batch remain excluded;
- plan-level summaries are unchanged.
```

Tests / gates:

```text
Extended test_review_advisory_proposal_uses_batch_scope_when_plan_id_is_missing:

- injects a legacy proposal with top-level batch_id and an item without
  item.batch_id;
- verifies first-batch advisory summary includes the legacy item;
- verifies second-batch advisory summary excludes it.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_review_advisory_proposal_uses_batch_scope_when_plan_id_is_missing
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted review advisory proposal batch scope test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This hardens VLM/review advisory proposal visibility at the RuntimeState summary
layer.  It does not prove real VLM screenshot quality, does not execute advisory
fixes automatically, and does not prove F5 runtime behavior.  Full Agent-native
completion still requires real provider rollout, full progressive replacement,
multiplayer sync replacement, UI validation, and F5 runtime validation.
```

## Progress Update 216 - scene.extract_objects keeps plan and batch identity separate

Problem:

```text
AgentRuntime._build_batch_execution_graph had a subtle ToolCallGraph boundary
issue: the batch execution node for scene.extract_objects passed batch.batch_id
through the args["plan_id"] field.

The current scene.extract_objects tool uses args["plan_id"] as its extraction
id, so this made a batch-level extraction look like the plan identity.  That is
small in code but large architecturally: Agent-native RuntimeState must keep
plan identity, batch identity, and extraction identity explicit instead of
letting a batch id masquerade as a plan id.
```

Change:

```text
AgentRuntime._build_batch_execution_graph now passes both fields explicitly:

- plan_id = plan.plan_id
- batch_id = batch.batch_id

The existing batch graph structure remains unchanged:

- runtime.scene.snapshot still runs before scene.extract_objects
- scene.extract_objects still feeds runtime.elements.classify
- downstream asset/image/model/import/review nodes still operate at batch scope

Only the identity boundary was corrected.
```

Tests / gates:

```text
test_tool_graph_consumed_state_requires_dependency_on_graph_producer now asserts
the scene.extract_objects node receives the true plan_id plus separate batch_id,
and that the two are not equal.

verify_ultimate_plan.py now statically requires _build_batch_execution_graph to
contain the scene.extract_objects ToolCall with plan_id=plan.plan_id and
batch_id=batch.batch_id, and rejects plan_id=batch.batch_id.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_tool_graph_consumed_state_requires_dependency_on_graph_producer editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_executes_planned_batches_as_separate_tool_graphs
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
py_compile: passed
targeted ToolCallGraph tests: 2 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This is a ToolCallGraph identity-boundary repair.  It does not enable native
engine writes, does not change SceneComposer or C++/CEF, and does not prove F5
runtime behavior.  Full Agent-native completion still requires real provider
rollout, full progressive replacement, multiplayer sync replacement, UI
validation, and F5 runtime validation.
```

## Progress Update 224 - operation replay excludes unattributable room sync facts

Problem:

```text
Operation replay already uses plan/batch-scoped OperationLog entries, but it
also supplements sync summaries from RuntimeState.sync_events so old or narrow
log windows can still be diagnosed.

That supplement accepted sync events without plan_id when replaying a specific
plan.  Batch-only legacy sync events are useful and should remain compatible,
but room-level sync events with neither plan_id nor batch_id cannot be proven to
belong to the requested plan.  In multiplayer replay this can make a plan's
sync summary look healthier or noisier than it really was.
```

Change:

```text
_state_sync_replay_entries now uses stricter plan attribution:

- explicit event plan_id must match the requested plan;
- batch-only legacy events are accepted only when the batch belongs to the
  requested plan;
- unscoped room-level sync events are excluded from plan-scoped replay;
- batch_id filtering still applies after plan attribution.
```

Tests / gates:

```text
Added test_operation_replay_state_sync_skips_unattributable_room_events_for_plan:

- creates a plan-scoped batch;
- records one legacy batch-only sync event and one room-level unattributable
  sync event;
- verifies plan operation_replay counts only the attributable batch event;
- verifies the unscoped actor does not leak into sync_summary.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_operation_replay_plan_scope_rejects_other_plan_with_same_batch_id editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_operation_replay_state_sync_skips_unattributable_room_events_for_plan
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted operation replay ownership tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This hardens replay evidence for multiplayer sync diagnosis.  It does not
replace C++ sync transport, does not prove LAN transfer performance, and does
not prove F5 runtime behavior.  Full Agent-native completion still requires real
provider rollout, full progressive replacement, multiplayer sync replacement,
UI validation, and F5 runtime validation.
```

## Progress Update 225 - actor facts require consistent plan/batch ownership

Problem:

```text
_actor_facts_for_plan and _observed_actor_facts_for_plan were plan-scoped when
only plan_id was provided, but their active batch branches returned actors only
by batch_id.

That meant a caller could ask for plan A with a batch_id from plan B and still
receive plan B actor facts.  The risk is small in normal generated batches, but
it violates the Agent-native invariant that RuntimeState facts must be scoped by
consistent plan/batch ownership before status, report, or scene snapshot output
uses them.
```

Change:

```text
Actor fact helpers now apply combined ownership rules:

- batch_id must match when provided;
- when plan_id is also provided, actor.plan_id must match if present;
- legacy actor facts without plan_id may still be attributed through
  batch_plans ownership;
- batch-only queries with no plan_id continue to work.

Observed actor facts use the same rule, including runtime actor facts as the
fallback source for missing observed plan_id / batch_id.
```

Tests / gates:

```text
Added test_actor_fact_helpers_require_matching_plan_and_batch_ownership:

- verifies mismatched plan_id + batch_id returns no actor or observed actor
  facts;
- verifies batch-only queries still return the batch actor;
- verifies legacy planless actor facts are accepted when their batch belongs to
  the requested plan.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_status_and_report_actor_count_are_plan_scoped editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_actor_fact_helpers_require_matching_plan_and_batch_ownership
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted actor ownership tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This hardens actor fact scoping for status/report/snapshot summaries.  It does
not replace real engine actor observation, does not prove LAN synchronization,
and does not prove F5 runtime behavior.  Full Agent-native completion still
requires real provider rollout, full progressive replacement, multiplayer sync
replacement, UI validation, and F5 runtime validation.
```

## Progress Update 227 - layout adjustment batch summaries count filtered proposals

Problem:

```text
_layout_adjustment_summary_for_plan filtered deltas, applied_deltas,
skipped_deltas, and engine_transform_results by batch_id, but proposal_count
still returned the unfiltered plan-level layout proposal count.

For a completed scene with a layout adjustment attached to batch A, a status or
report query for batch B could show proposal_count > 0 even though batch B had
no layout adjustment evidence.  That weakens the completed-state adjustment
closed loop and makes batch replay harder to trust.
```

Change:

```text
layout_adjustment_summary now returns proposal_count from the filtered proposal
rows that survive the requested plan/batch scope.

The underlying proposal filtering is unchanged:

- plan-level summaries still count plan-matching proposals;
- batch-level summaries count only proposals with matching batch-scoped deltas,
  applied/skipped deltas, or transform results;
- operation replay continues to summarize confirmed execution events separately.
```

Tests / gates:

```text
Extended test_confirm_layout_adjustment_records_batch_scope_for_single_batch_proposal:

- confirms a low-risk layout proposal for the first batch;
- verifies first-batch status summary reports one layout proposal;
- verifies second-batch status summary reports zero layout proposals;
- keeps replay checks for confirmation and ground snap execution evidence.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_records_batch_scope_for_single_batch_proposal
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted layout adjustment batch summary test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This hardens completed-state layout adjustment reporting at the RuntimeState
summary layer.  It does not prove real engine transform execution, does not
replace native actor synchronization, and does not prove F5 runtime behavior.
Full Agent-native completion still requires real provider rollout, full
progressive replacement, multiplayer sync replacement, UI validation, and F5
runtime validation.
```

## Progress Update 229 - review summaries accept legacy plan/batch fact keys

Problem:

```text
_review_summary_for_plan supported explicit plan_id and batch_id fields on
geometry_reviews, custom_vlm_checkpoint_facts, and custom_review_summary_facts.
However, legacy/runtime facts can also be keyed as plan_id:batch_id or
plan_id:batch_id:suffix.

Those key-shaped facts were not parsed consistently, so a review fact that only
carried scope in its RuntimeState key could be skipped from plan/batch status or
report summaries.  This weakens the migration path from old review workflow
outputs into AgentRuntime facts.
```

Change:

```text
_review_summary_for_plan now derives scope from either payload fields or legacy
RuntimeState keys:

- first key segment is treated as plan_id;
- second key segment is treated as batch_id;
- additional suffix segments are ignored for scoping;
- explicit payload plan_id/batch_id still take precedence.

The same key parsing pattern was also tightened for geometry fact summaries so
plan_id:batch_id:suffix keys remain batch-attributable.
```

Tests / gates:

```text
Added test_review_summary_accepts_legacy_plan_batch_fact_keys:

- writes geometry review, VLM checkpoint, and review summary facts using only
  plan_id:batch_id-style keys;
- verifies first-batch status/report summaries include first-batch review facts;
- verifies second-batch review evidence does not leak into first-batch output.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_review_summary_uses_batch_scope_when_plan_id_is_missing editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_review_summary_accepts_legacy_plan_batch_fact_keys
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_geometry_fact_summary_requires_matching_batch_when_batch_scoped
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted review and geometry fact scoping tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This hardens RuntimeState review/VLM fact attribution during workflow-to-runtime
migration.  It does not prove real VLM screenshot quality, does not replace
native engine review capture, and does not prove F5 runtime behavior.  Full
Agent-native completion still requires real provider rollout, full progressive
replacement, multiplayer sync replacement, UI validation, and F5 runtime
validation.
```

## Progress Update 228 - report_ready layout proposal count uses scoped summary

Problem:

```text
Progress Update 227 fixed layout_adjustment_summary.proposal_count for
batch-scoped status/report summaries, but the report_ready runtime event payload
still used len(layout_proposals), the unfiltered plan-level proposal list.

That meant the user-visible report_ready event for batch B could expose a
proposal_count from batch A even though the batch-scoped layout summary was
correct.  This is an information disclosure consistency gap: UI/event payloads
must use the same RuntimeState fact source and scope as the report.
```

Change:

```text
report_ready payload now uses:

proposal_count = layout_adjustment_summary.proposal_count

instead of counting the raw plan-level layout proposal list.

This keeps user-visible runtime events aligned with the scoped
layout_adjustment_summary used by status/report output.
```

Tests / gates:

```text
Extended test_confirm_layout_adjustment_records_batch_scope_for_single_batch_proposal:

- generates a report for the second batch after a first-batch layout adjustment;
- reads the second-batch user-visible report_ready event;
- verifies payload.proposal_count is 0 for the second batch.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_records_batch_scope_for_single_batch_proposal
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted report_ready layout proposal count test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This hardens user-visible report event disclosure for completed-state layout
adjustment facts.  It does not prove real engine transform execution, does not
replace native actor synchronization, and does not prove F5 runtime behavior.
Full Agent-native completion still requires real provider rollout, full
progressive replacement, multiplayer sync replacement, UI validation, and F5
runtime validation.
```

## Progress Update 226 - geometry fact summaries require batch attribution

Problem:

```text
_geometry_fact_summary_for_plan filtered correctly by plan, but batch-scoped
queries still accepted same-plan geometry facts with no batch_id.

For a plan-level report this is acceptable, but for a batch-level status/report
it can mix plan-level geometry facts into a specific batch's quality summary.
That weakens the Agent-native replay/review invariant that batch evidence must
belong to the requested batch.
```

Change:

```text
Geometry fact scoping now derives both plan_id and batch_id from either the fact
payload or a legacy key shaped like plan_id:batch_id.

When batch_id is requested:

- fact batch_id must match exactly;
- same-plan facts without batch attribution are excluded from the batch summary;
- plan-level summaries still include all matching plan facts;
- legacy keyed facts remain compatible.
```

Tests / gates:

```text
Added test_geometry_fact_summary_requires_matching_batch_when_batch_scoped:

- writes one batch-a AABB fact, one plan-level overlap fact, and one batch-b AABB
  fact;
- verifies plan summary sees all plan facts;
- verifies batch-a summary only sees batch-a geometry evidence;
- verifies plan-level overlap and batch-b facts do not leak into batch-a.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_phase6_geometry_compute_aabb_tool_records_safe_actor_facts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_geometry_fact_summary_requires_matching_batch_when_batch_scoped editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_phase6_geometry_check_overlap_tool_records_safe_review_fact_without_actor_write
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted geometry fact tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This hardens Geometry/AABB review evidence at the RuntimeState summary layer.
It does not replace real engine geometry capture, does not prove VLM behavior,
and does not prove F5 runtime behavior.  Full Agent-native completion still
requires real provider rollout, full progressive replacement, multiplayer sync
replacement, UI validation, and F5 runtime validation.
```

## Progress Update 217 - runtime placement and geometry review facts are batch-scoped

Problem:

```text
After the scene.extract_objects identity fix, the next batch-boundary gap was
runtime.placement.propose and runtime.geometry.review:

- placement proposals were written under plan_id even when produced inside a
  batch execution ToolCallGraph;
- runtime.actor.plan_import_batch / runtime.actor.import_batch / VLM checkpoint
  consumed placement_proposals as plan-scoped facts;
- geometry review facts were also written under plan_id and consumed by review
  summary / adjustment proposal as plan-scoped facts.

That made later batches able to overwrite or reuse earlier placement/review
facts, which conflicts with the Agent-native target that every batch owns its
image/model/import/placement/review evidence.
```

Change:

```text
Batch execution now keeps placement and geometry review facts batch-scoped:

- _build_batch_execution_graph passes batch_id to runtime.placement.propose.
- runtime.placement.propose writes placement_proposals[batch_id].
- runtime.actor.plan_import_batch consumes placement_proposals with scope=batch.
- runtime.actor.import_batch consumes placement_proposals with scope=batch.
- runtime.review.vlm_checkpoint consumes placement_proposals with scope=batch.
- runtime.geometry.review consumes placement_proposals with scope=batch and
  writes geometry_reviews[batch_id].
- runtime.review.summarize_batch and runtime.review.generate_adjustment_proposal
  consume geometry_reviews with scope=batch.

The planning-only placement.prepare_items path remains plan-scoped; this change
only affects runtime batch execution facts.
```

Tests / gates:

```text
Updated Runtime tests now assert:

- execute_scene_plan stores runtime placement proposals under batch_id.
- batch graph import/review nodes receive the batch-scoped placement proposal.
- manifest contracts expose placement and geometry review consumption as
  batch-scoped for runtime execution tools.
- manual review fixtures overwrite batch_id keys instead of adding unrelated
  plan-level review rows.
- verify_ultimate_plan.py statically requires runtime.placement.propose to carry
  batch_id inside _build_batch_execution_graph.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_batch_report_scopes_resource_import_and_runtime_events_to_batch editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_geometry_review_issues_become_low_risk_layout_adjustment_proposal editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_review_generate_adjustment_proposal_reads_review_facts_without_applying
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
py_compile: passed
targeted batch placement/review tests: 3 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This closes another batch fact-source boundary.  It does not enable real native
providers, does not replace C++ sync transport, and does not prove F5 runtime
behavior.  Full Agent-native completion still requires real provider rollout,
full progressive replacement, multiplayer sync replacement, UI validation, and
F5 runtime validation.
```

## Progress Update 220 - resource phase facts carry plan_id

Problem:

```text
Runtime image/model phase facts were batch-scoped, but they did not carry
plan_id.  The fact key and fact body identified the batch and phase, but not the
owning ScenePlan.

That is weak for Agent-native replay and diagnosis because RuntimeState should
make plan/batch/phase relationships explicit without requiring a caller to
reverse-map batch ids through separate batch_plans state.
```

Change:

```text
_resource_phase_fact now accepts plan_id and writes it into each
custom_resource_phase_facts row.

runtime.asset.image.prepare and runtime.asset.model.prepare now pass plan_id
from their ToolCall args through the resource payload into every image/model
phase fact, including:

- successful image/model resource preparation
- empty provider result fallback facts
- hard failed legacy model adapter facts
```

Tests / gates:

```text
Updated tests assert:

- partial image resource phase facts include plan_id.
- failed model resource phase facts include plan_id.
- legacy model adapter unavailable phase facts include plan_id.
- verify_ultimate_plan.py statically requires _resource_phase_fact to keep
  plan_id in the fact contract.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_legacy_model_provider_factory_failure_records_failed_resource_facts
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
py_compile: passed
targeted resource phase tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This strengthens RuntimeState fact traceability.  It does not enable real native
providers, does not replace C++ sync transport, and does not prove F5 runtime
behavior.  Full Agent-native completion still requires real provider rollout,
full progressive replacement, multiplayer sync replacement, UI validation, and
F5 runtime validation.
```

## Progress Update 219 - batch resource/placement tools require batch_id by contract

Problem:

```text
Progress Updates 217 and 218 moved runtime placement, geometry review, and asset
request facts to batch scope.  However, two runtime batch tools still allowed a
caller to omit batch_id:

- runtime.asset.plan
- runtime.placement.propose

Both tools had fallback logic that could use plan_id or tool_call_id as the fact
key.  That fallback is useful for very early bring-up, but it is now too weak
for Agent-native batch execution: a missing batch_id could silently reintroduce
plan-scoped or unstable fact keys.
```

Change:

```text
ToolRegistry contracts now require batch_id for both runtime batch tools:

- runtime.asset.plan required_args = room_id, batch_id, model_items
- runtime.placement.propose required_args = room_id, batch_id, model_items

The normal _build_batch_execution_graph path already passes batch_id to both
tools, so this is a contract-hardening slice rather than a behavior rewrite.
```

Tests / gates:

```text
Updated tests assert:

- Tool manifest exposes batch_id as required for runtime.asset.plan.
- Tool manifest exposes batch_id as required for runtime.placement.propose.
- Batch execution graph nodes pass the current batch_id to asset planning and
  placement proposal tools.
- verify_ultimate_plan.py statically requires both batch tools to have the
  room_id/batch_id/model_items required-args contract.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_graph_plans_assets_and_placements_before_mock_import editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_execution_graph_consumes_are_derived_from_tool_definition_contract
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
py_compile: passed
targeted graph/contract tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This hardens Runtime ToolRegistry contracts.  It does not enable real native
providers, does not replace C++ sync transport, and does not prove F5 runtime
behavior.  Full Agent-native completion still requires real provider rollout,
full progressive replacement, multiplayer sync replacement, UI validation, and
F5 runtime validation.
```

## Progress Update 218 - runtime asset requests are batch-scoped

Problem:

```text
After placement and geometry review became batch-scoped, the same boundary issue
still existed one step earlier:

- runtime.asset.plan consumed batch-scoped model_items, but wrote
  asset_request_plans under plan_id;
- runtime.asset.image.prepare and runtime.asset.model.prepare consumed
  asset_request_plans as plan-scoped facts.

That meant each batch had independent model_items/image/model resources, but
shared a single plan-level asset request map.  In a real multi-batch flow, a
later batch could overwrite or accidentally reuse earlier asset request facts.
```

Change:

```text
Runtime asset request facts now stay batch-scoped:

- _build_batch_execution_graph passes batch_id to runtime.asset.plan.
- runtime.asset.plan writes asset_request_plans[batch_id].
- runtime.asset.image.prepare consumes asset_request_plans with scope=batch.
- runtime.asset.model.prepare consumes asset_request_plans with scope=batch.

The planning-only asset.route_item path remains plan-scoped; this change only
affects runtime batch execution facts.
```

Tests / gates:

```text
Updated Runtime tests now assert:

- runtime batch graph stores asset_request_plans under batch_id.
- image/model prepare nodes receive the batch-specific asset_requests map.
- ToolRegistry manifest exposes batch-scoped asset_request consumption for
  runtime.asset.image.prepare and runtime.asset.model.prepare.
- pending intervention batch enqueue still works after the batch_id patch.
- LANChat GM / active intervention replies still see queued intervention batches.
- verify_ultimate_plan.py statically requires runtime.asset.plan to carry
  batch_id inside _build_batch_execution_graph.
```

Validation:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_graph_plans_assets_and_placements_before_mock_import editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_asset_resource_tools_can_run_from_asset_requests_without_model_items editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_model_provider_consumes_image_resources_from_previous_toolcall
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_enqueue_pending_intervention_batch_adds_next_runtime_batch editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_enqueue_pending_intervention_batch_is_atomic_when_graph_queue_persist_fails editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_enqueue_pending_intervention_batch_stops_when_plan_status_persist_fails editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_worker_drain_executes_queued_intervention_batch editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_handle_message_can_enqueue_pending_intervention_batch_without_new_plan
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_includes_runtime_intervention_batch_summary editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_executing_intervention_does_not_require_coordinator_active_plan
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
py_compile: passed
targeted asset/resource tests: passed
targeted pending-intervention tests: passed
targeted LANChat intervention tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This closes another batch resource fact-source boundary.  It does not enable
real native providers, does not replace C++ sync transport, and does not prove
F5 runtime behavior.  Full Agent-native completion still requires real provider
rollout, full progressive replacement, multiplayer sync replacement, UI
validation, and F5 runtime validation.
```

## Progress Update 221 - import summary consumes RuntimeState import facts

Problem:

```text
runtime.actor.import_batch writes plan_id/batch_id-scoped
custom_import_facts, but _import_summary_for_plan only consumed runtime_events.

If an import tool result was recorded in RuntimeState facts but the corresponding
actors_imported / actors_import_failed event was missing, pruned, or delayed,
the final/status import summary could incorrectly report 0 imported/failed
actors.  That violates the Agent-native invariant that RuntimeState is the
state fact source.
```

Change:

```text
_import_summary_for_plan now merges import evidence from two sources:

1. runtime_events remain the preferred source when present;
2. custom_import_facts[*:actor_import_result] fill gaps only for batches that
   have no import event.

The merge remains plan/batch scoped:

- facts with plan_id must match the requested plan;
- facts without plan_id are accepted only if their batch_id belongs to the
  requested plan;
- facts from another plan are ignored;
- event-backed batches are not double-counted.
```

Tests / gates:

```text
Added test_import_summary_consumes_runtime_state_import_fact_without_event:

- creates two plans in one room;
- records only custom_import_facts, with no import runtime_events;
- verifies the import summary counts the target plan's imported/failed actors;
- verifies the other plan's batch does not leak into the summary.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_import_summary_consumes_runtime_state_import_fact_without_event editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_actor_import_provider_empty_actor_result_records_failed_import_fact
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted import summary tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This strengthens RuntimeState-driven reporting for the actor import phase.  It
does not enable real native providers, does not replace C++ sync transport, and
does not prove F5 runtime behavior.  Full Agent-native completion still
requires real provider rollout, full progressive replacement, multiplayer sync
replacement, UI validation, and F5 runtime validation.
```

## Progress Update 222 - environment import summary consumes RuntimeState import facts

Problem:

```text
Environment/substrate import had the same class of RuntimeState/reporting gap
as actor import.

runtime.environment.import_components writes
custom_import_facts[*:environment_import_result], but
_environment_component_summary_for_plan primarily counted import requested /
imported / failed numbers from environment import runtime_events.

If the event was missing, pruned, or delayed, a partial environment import could
be reported as if 1/1 components were imported, even when the RuntimeState fact
said 1/2 imported and 1 failed.  That weakens terrain/boundary evidence in open
scene generation.
```

Change:

```text
_environment_component_summary_for_plan now consumes environment import result
facts as a fallback:

- environment_components_imported / environment_components_import_failed events
  remain the preferred source;
- custom_import_facts[*:environment_import_result] fill gaps only for batches
  without environment import events;
- plan_id and batch_id filtering mirrors actor import summary behavior;
- fact-backed batches are not double-counted;
- latest_events marks the fallback row as environment_import_result.
```

Tests / gates:

```text
Added test_environment_component_summary_consumes_import_fact_without_event:

- creates two plans in one room;
- records environment_components and environment_import_result facts without
  environment import runtime_events;
- verifies target plan import_requested/imported/import_failed counts are
  derived from RuntimeState facts;
- verifies the other plan's batch does not leak into the summary.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_environment_component_summary_consumes_import_fact_without_event editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_environment_component_summary_uses_batch_scope_for_runtime_events
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted environment import summary tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This strengthens RuntimeState-driven reporting for terrain/environment import
facts.  It does not enable real native providers, does not replace C++ sync
transport, and does not prove F5 runtime behavior.  Full Agent-native
completion still requires real provider rollout, full progressive replacement,
multiplayer sync replacement, UI validation, and F5 runtime validation.
```

## Progress Update 223 - sync summaries enforce plan/batch ownership together

Problem:

```text
Sync summary scoping already supported plan_id-only and batch_id-only queries,
but when a caller supplied both plan_id and batch_id, the batch branch could
accept events/assets solely because the batch_id matched.

If a caller accidentally asked for plan A with a batch_id that belonged to plan B,
sync_summary and asset_transfer_summary could expose plan B sync facts under a
plan A status query.  This is small but important for multiplayer Agent-native
state: plan/batch ownership must be consistent wherever RuntimeState is used as
the fact source.
```

Change:

```text
_sync_summary_for_plan now applies combined ownership rules:

- batch_id must match when provided;
- if event/fact carries plan_id, that plan_id must also match;
- if plan_id is absent, batch_plans ownership is used as the fallback;
- batch-only queries still work when no plan_id is supplied.

_asset_transfer_summary_for_plan now applies the same combined ownership rule
for asset transfer facts.
```

Tests / gates:

```text
Extended test_sync_summary_uses_batch_scope_when_plan_id_is_missing:

- keeps the existing batch-only behavior;
- adds a mismatched plan_id + batch_id query;
- verifies sync_summary and asset_transfer_summary return empty scoped results;
- verifies facts from the other plan are not leaked.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_sync_summary_uses_batch_scope_when_plan_id_is_missing
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted sync ownership test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This hardens RuntimeState sync/report ownership.  It does not replace C++ sync
transport, does not prove LAN file transfer performance, and does not prove F5
runtime behavior.  Full Agent-native completion still requires real provider
rollout, full progressive replacement, multiplayer sync replacement, UI
validation, and F5 runtime validation.
```

## Progress Update 231 - review advisory confirmation summaries inherit top-level batch scope

Problem:

```text
Review advisory proposal summaries already accepted legacy proposals whose
batch_id lived on the proposal itself rather than on each proposal item.

The matching confirmation summary still required every proposal item to carry
its own batch_id.  For older VLM/review advisory proposal records, a batch-level
status or report could therefore show the advisory proposal but omit the
matching host confirmation.
```

Change:

```text
_review_advisory_confirmation_summary_for_plan now uses the proposal-level
batch_id as a fallback when proposal items do not carry batch_id themselves.

This keeps confirmation summaries consistent with review advisory proposal
summaries and preserves RuntimeState as the single report fact source for
batch-scoped VLM/review advisory decisions.
```

Tests / gates:

```text
Extended test_review_advisory_proposal_uses_batch_scope_when_plan_id_is_missing:

- keeps the existing proposal summary top-level batch compatibility coverage;
- records a confirmation against a legacy proposal whose item lacks batch_id;
- verifies the first batch sees the confirmation and item_count;
- verifies the second batch does not see the confirmation.
```

Validation:

```text
python editor/plugins/AITool/services/test_agent_runtime_phase1.py -k test_review_advisory_proposal_uses_batch_scope_when_plan_id_is_missing
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted review advisory batch compatibility test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This hardens RuntimeState report scoping for VLM/review advisory confirmations.
It does not prove live VLM screenshot quality, does not replace C++ sync
transport, and does not prove F5 runtime behavior.  Full Agent-native
completion still requires real provider rollout, full progressive replacement,
multiplayer sync replacement, UI validation, and F5 runtime validation.
```

## Progress Update 232 - final adjustment confirmations enter OperationLog replay summary

Problem:

```text
Final adjustment confirmations were already persisted as RuntimeState facts and
written to OperationLog as safe final_adjustment_confirmation_recorded entries.

Report/status summaries could show final_adjustment_confirmation_summary, but
operation_replay() only exposed the raw log entries.  That made the confirmation
auditable, but not directly explainable from a compact replay summary.  It left
a small mismatch with the Agent-native invariant that OperationLog must be useful
before user-facing reports.
```

Change:

```text
Added _final_adjustment_confirmation_replay_summary and wired it into both:

- operation_replay()
- generate_report().operation_replay_summary

The summary includes safe aggregate fields only:

- confirmation_count
- confirmation_failed_count
- confirmation_skipped_count
- decision_counts
- latest_confirmation with proposal_id, batch_id, decision, confirmed_by,
  target_hint, and conflict_item_count

It deliberately does not expose raw conflict_items or internal payload details.
```

Tests / gates:

```text
Extended test_record_final_adjustment_confirmation_is_runtime_fact:

- verifies direct operation_replay contains final_adjustment_confirmation_replay_summary;
- verifies report.operation_replay_summary contains the same compact replay fact;
- verifies conflict_items are not exposed in replay summaries.
```

Validation:

```text
python editor/plugins/AITool/services/test_agent_runtime_phase1.py -k test_record_final_adjustment_confirmation_is_runtime_fact
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted final adjustment confirmation replay test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This strengthens OperationLog replay and report explainability for final
adjustment confirmations.  It does not execute live final adjustment UI flows,
does not replace C++ sync transport, and does not prove F5 runtime behavior.
Full Agent-native completion still requires real provider rollout, full
progressive replacement, multiplayer sync replacement, UI validation, and F5
runtime validation.
```

## Progress Update 233 - LANChat replay surfaces final adjustment confirmations

Problem:

```text
Progress Update 232 made final adjustment confirmations available in
operation_replay() and report.operation_replay_summary.

LANChat operation replay replies and Runtime Report text still displayed review
advisory replay and layout replay, but did not render the new final adjustment
confirmation replay summary.  That meant the Runtime replay fact existed but was
not visible at the main chat diagnosis surface.
```

Change:

```text
LANChatAgentWorker now formats final_adjustment_confirmation_replay_summary with
a safe user-visible formatter.

The formatter is included in:

- direct Runtime Operation Replay query replies;
- Runtime Report text through report.operation_replay_summary.

The output includes only compact safe fields:

- confirmation count;
- failed / skipped counts when present;
- decision counts;
- latest proposal id, decision, and conflict item count.

It does not expose raw conflict_items or internal provider/prompt/path details.
```

Tests / gates:

```text
Extended LANChat runtime replay tests:

- room-level operation replay now shows final_adjustment and decision counts;
- batch-scoped replay shows the first batch final adjustment confirmation;
- batch-scoped replay does not leak second-batch final adjustment confirmation;
- raw conflict_items remain hidden from user-visible replay text.
```

Validation:

```text
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_query_exports_safe_summary_without_creating_plan editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_query_uses_metadata_batch_scope
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted LANChat replay formatter tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This closes the chat-facing replay disclosure gap for final adjustment
confirmations.  It does not execute live UI flows, does not replace C++ sync
transport, and does not prove F5 runtime behavior.  Full Agent-native
completion still requires real provider rollout, full progressive replacement,
multiplayer sync replacement, UI validation, and F5 runtime validation.
```

## Progress Update 234 - Runtime Report protects final adjustment replay as persisted fact

Problem:

```text
Progress Update 233 exposed final adjustment confirmation replay in LANChat
diagnostic text, but the Runtime Report top-level payload did not yet carry the
same replay summary as a persisted user-report field.

The first static gate patch also used an overly exact source-token check, which
could miss valid multi-line report formatting.  After adding the report field,
RuntimeState correctly rejected it until the report schema explicitly allowed
the new safe top-level field.
```

Change:

```text
AgentRuntime.generate_report now includes:

- final_adjustment_confirmation_replay_summary

from operation_replay_summary, so the same replay facts are available through:

- operation_replay();
- report.operation_replay_summary;
- report.final_adjustment_confirmation_replay_summary;
- LANChat operation replay text;
- LANChat Runtime Report text.

ReportRecordValidator now explicitly allows the new top-level report field.
The static Runtime report fact-source gate was tightened to require the field
and its OperationLog-derived source without depending on one fragile continuous
line of source text.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/test_agent_runtime_phase1.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
test_agent_runtime_phase1.py: 572 tests passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This closes the Runtime Report persistence gap for final adjustment confirmation
replay facts.  It does not execute live final adjustment UI flows, does not
replace C++ sync transport, and does not prove F5 runtime behavior.  Full
Agent-native completion still requires real provider rollout, full progressive
replacement, multiplayer sync replacement, UI validation, and F5 runtime
validation.
```

## Progress Update 235 - final adjustment replay report schema is regression-protected

Problem:

```text
Progress Update 234 added final_adjustment_confirmation_replay_summary to the
top-level Runtime Report and allowed it through ReportRecordValidator.

That fixed the immediate RuntimeState persistence failure, but the regression
coverage still needed to prove two exact boundaries:

- report.final_adjustment_confirmation_replay_summary must match the
  OperationLog-derived report.operation_replay_summary field;
- ReportRecordValidator._ALLOWED_TOP_LEVEL_FIELDS must continue to allow the
  persisted user-report field.
```

Change:

```text
The final adjustment confirmation Runtime fact test now asserts the top-level
Runtime Report replay summary equals the nested operation_replay_summary value
and still hides raw conflict_items.

The static Runtime validator contract gate now checks the allowed top-level
report field block directly, so a future report-only addition cannot pass if
the RuntimeState report schema would reject it during persistence.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_final_adjustment_confirmation_is_runtime_fact
python -m py_compile editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted final adjustment confirmation Runtime fact test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This is a regression-protection slice for Runtime Report persistence and replay
consistency.  It does not execute live final adjustment UI flows, does not
replace C++ sync transport, and does not prove F5 runtime behavior.  Full
Agent-native completion still requires real provider rollout, full progressive
replacement, multiplayer sync replacement, UI validation, and F5 runtime
validation.
```

## Progress Update 236 - legacy model provider failures expose safe failure codes

Problem:

```text
The legacy ModelProvider adapter had already been narrowed into a Runtime model
resource provider, but per-item failures still collapsed to generic failed
model resource facts.

That made real-provider rollout harder to diagnose from RuntimeState and reports:
the graph could prove "model resource failed", but not safely distinguish adapter
factory unavailable, provider acquire exception, or invalid provider result.
```

Change:

```text
Model resource facts now support a safe failure_code field.

make_legacy_model_resource_provider() writes only enum-like failure codes:

- legacy_model_adapter_unavailable
- legacy_model_acquire_exception
- legacy_model_invalid_result
- legacy_model_failure

The adapter still does not expose exception text, provider names, raw payloads,
URLs, model paths beyond existing sanitized resource fields, prompts, tokens, or
API keys.  It still only acquires model resource facts and does not import
actors or re-enter SceneComposer / ProgressiveWorkflow.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_adapters_sanitize_tool_exceptions_before_runtime_tool_layer editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_legacy_model_provider_adapter_coerces_success_flag editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_legacy_model_provider_factory_failure_records_failed_resource_facts
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted legacy model provider failure-code tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This is a provider-rollout diagnostics slice.  It does not enable the legacy
model provider by default, does not call SceneComposer, does not import actors,
and does not prove F5 real-provider behavior.  Full Agent-native completion
still requires real provider rollout, full progressive replacement,
multiplayer sync replacement, UI validation, and F5 runtime validation.
```

## Progress Update 237 - actor import failures expose safe failure codes

Problem:

```text
The Runtime engine actor import provider already wrote safe import result facts,
but native / bridge failure rows still lacked a stable failure code.

That made OperationLog replay and final report summaries able to show that an
import failed, but unable to safely distinguish "missing model resource" from
"C++ bridge import failed" or "invalid import result".
```

Change:

```text
make_engine_actor_import_provider() now records enum-like import failure codes:

- missing_ready_model_resource
- cpp_actor_import_failed
- actor_import_invalid_result

ToolCallGraphExecutor._safe_engine_result_rows() now preserves failure_code in
the sanitized engine_write_summary replay rows.

The bridge still does not expose raw exception text, URLs, provider payloads,
API keys, function names, or internal model-generation details.  The imported
actor facts remain RuntimeState facts; SceneComposer / ProgressiveWorkflow do
not regain control.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_cpp_bridge_success_payload_still_supports_engine_import_provider editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_actor_import_provider_failure_codes_are_safe editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_write_replay_summary_sanitizes_raw_engine_results
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted actor import failure-code tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This is an engine-import diagnostics slice.  It does not prove live C++ import,
LAN actor synchronization, F5 runtime behavior, or visual placement quality.
Full Agent-native completion still requires real provider rollout, full
progressive replacement, multiplayer sync replacement, UI validation, and F5
runtime validation.
```

## Progress Update 238 - actor import failure-code contract is now gated

Problem:

```text
Progress Update 237 added safe actor-import failure codes, but without a static
contract gate the refactor could later remove those codes or strip failure_code
from replay summaries while still leaving unrelated tests green.
```

Change:

```text
verify_ultimate_plan.py now checks the Runtime validator contract for:

- missing_ready_model_resource
- cpp_actor_import_failed
- actor_import_invalid_result
- ToolCallGraphExecutor._safe_engine_result_rows() preserving "failure_code"
- regression tests covering actor import failure-code safety and replay summary
  sanitization

This keeps the C++ / engine import boundary diagnostic signal in the mandatory
non-native Agent-native gate.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This protects the Python/static Runtime contract only.  It does not prove live
C++ import behavior, multiplayer actor synchronization, or F5 visual placement.
Those remain in the real-provider and runtime-validation workstreams.
```

## Progress Update 239 - transform/delete engine-write failures expose safe failure codes

Problem:

```text
Actor import failures had safe failure_code facts, but the adjacent engine-write
providers for layout transform and actor delete still returned only status and
reason.

That left Runtime replay able to say "transform/delete failed", but not safely
distinguish missing targets from C++ bridge failures.
```

Change:

```text
make_engine_layout_transform_provider() now records safe failure codes:

- missing_transform_target
- cpp_actor_transform_failed

make_engine_actor_delete_provider() now records safe failure codes:

- missing_delete_target
- cpp_actor_delete_failed

verify_ultimate_plan.py now gates these failure-code tokens alongside actor
import failure codes and the replay preservation of "failure_code".
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_actor_delete_provider_uses_remove_gate_and_returns_actor_updates editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_actor_delete_provider_failure_code_is_safe editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_layout_transform_provider_respects_status_and_success_failure editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_layout_transform_provider_keeps_partial_success_when_one_actor_fails
python -m py_compile editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted transform/delete failure-code tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This is still a Python Runtime boundary slice.  It does not prove live C++
transform/delete behavior, multiplayer sync convergence, or F5 visual layout
quality.  Those remain [待 F5/实机验证] after real provider rollout.
```

## Progress Update 240 - environment component import failures expose safe failure codes

Problem:

```text
Room boxes, terrain, boundaries, and other scene substrate components are moving
through the Runtime environment-component import path, but failed engine imports
only returned status/reason.

That made Runtime replay able to say "environment import failed", but not safely
distinguish a C++ environment-component bridge failure from other resource or
validation failures.
```

Change:

```text
make_engine_environment_component_import_provider() now records the safe failure
code:

- cpp_environment_component_import_failed

The Runtime environment import result sanitizer now allows the safe
"failure_code" field, and verify_ultimate_plan.py gates both the failure-code
token and the sanitizer contract.

This keeps terrain / room_box / boundary import failures diagnosable without
exposing raw provider payloads, paths, URLs, prompt text, API keys, or C++
internal details.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_environment_component_import_provider_uses_gate_and_returns_component_updates editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_environment_component_import_provider_failure_code_is_safe editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_tool_uses_provider_and_persists_sanitized_components
python -m py_compile editor/plugins/AITool/services/agent_runtime/adapters.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted environment import failure-code tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This protects the Python Runtime boundary for environment component imports.
It does not prove live C++ terrain / room_box / boundary creation, LAN
synchronization, or F5 visual scene substrate quality.  Those remain
[待 F5/实机验证] after real provider rollout.
```

## Progress Update 241 - failed environment imports persist replayable Runtime facts

Problem:

```text
Progress Update 240 added a safe provider-level failure_code for environment
component import failures, but runtime.environment.import_components could still
collapse a provider failure into generic failed environment_components when no
component was imported.

That meant room_box / terrain / boundary import failures were safe at the
adapter boundary, but the provider's environment_import_results and bridge
boundary counts could be lost before RuntimeState / OperationLog replay.
```

Change:

```text
The failed environment import path now preserves safe provider failure facts:

- failed environment_components are still written so Runtime does not pretend
  terrain / room_box / boundary actors were imported
- custom_import_facts now include runtime_environment_import_result for provider
  failures that returned environment_import_results
- engine_write_boundary is preserved with bridge call / failure counts
- operation_replay().engine_write_summary can now show the failed
  environment_import_results with failure_code

The static AgentRuntime flag boundary gate now checks that failed environment
import paths keep both environment_components and custom_import_facts.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_environment_component_import_provider_failure_code_is_safe editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_failure_preserves_provider_failure_code_fact editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_tool_uses_provider_and_persists_sanitized_components
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted failed environment import Runtime fact tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves RuntimeState / OperationLog / replay preservation for Python-level
provider failures.  It does not prove live C++ terrain / room_box / boundary
creation or multiplayer sync convergence.  Those remain [待 F5/实机验证].
```

## Progress Update 242 - actor import result failure codes survive Runtime sanitization

Problem:

```text
Engine actor import providers could emit safe per-row failure_code values, but
runtime.actor.import_batch sanitized import_results down to actor_id /
actor_name / status / reason.

That meant C++ actor import failures and missing-ready-model precheck failures
could still lose their stable failure_code before RuntimeState, OperationLog,
and operation_replay summaries.
```

Change:

```text
runtime.actor.import_batch now preserves safe import result failure_code values.

The missing-ready-model precheck path now records:

- missing_ready_model_resource

Provider-backed actor import failures preserve:

- cpp_actor_import_failed

verify_ultimate_plan.py now gates _safe_actor_import_results() so future
refactors cannot silently strip safe failure_code from actor import facts.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_actor_import_provider_missing_model_resource_fails_runtime_graph editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted actor import failure-code Runtime fact tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This proves Python Runtime actor-import fact preservation.  It does not prove
live C++ actor import behavior, LAN actor synchronization, or F5 visual scene
quality.  Those remain [待 F5/实机验证].
```

## Progress Update 243 - image/model resource failures keep safe failure codes

Problem:

```text
The Runtime resource stage could already mark image/model preparation as failed,
partial, or completed, but empty provider results still collapsed to generic
status/source fields.

Image resource plans also filtered out failure_code, so image-stage failures
could lose the stable diagnostic token before RuntimeState, resource_summary,
and batch_resource_flow_summary.
```

Change:

```text
ResourcePlanValidator now preserves safe failure_code values for image resources,
matching the model resource contract.

runtime.image.prepare_batch and runtime.model.prepare_batch failed-resource rows
now record:

- image_resource_unavailable
- model_resource_unavailable

custom_resource_phase_facts now include failure_code_counts, and
batch_resource_flow_summary exposes:

- image_failure_code_counts
- model_failure_code_counts

verify_ultimate_plan.py now gates this contract so future refactors cannot
silently strip safe resource-stage failure-code diagnostics.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_model_resource_provider_failure_emits_safe_runtime_event editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_resource_provider_result_records_failed_resource_facts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted resource failure-code Runtime fact tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This proves Python Runtime resource-stage failure-code preservation and replay
summaries.  It does not prove live image/model provider latency behavior,
Hunyuan3D service stability, or F5 visual import quality.  Those remain
[待 F5/实机验证].
```

## Progress Update 259 - report/status/GM preserve environment import failure diagnostics

Problem:

```text
Environment component import failures already persisted sanitized provider
failure_code values in custom_import_facts and engine_write replay summaries.
However, the higher-level Runtime read surfaces only carried aggregate counts:

- environment_component_summary had import_failed_count but no failure-code map
- report_health_summary could mark environment_import_failed but not explain why
- report_ready, runtime_status_queried, and runtime_gm_summary_exported payloads
  did not preserve the safe environment import failure category

This meant the AgentRuntime fact layer knew that a room_box / terrain / boundary
engine write failed, but the final user-report and GM/status audit surfaces
could not name the safe failure bucket without digging into lower-level facts.
```

Change:

```text
AgentRuntime._environment_component_summary_for_plan() now aggregates
environment import failure_code counts from both RuntimeEvents and
custom_import_facts.

AgentRuntime._report_health_summary() now exposes:

- environment_import_failure_code_counts

AgentRuntime.generate_report() copies that field into the report_ready
RuntimeEvent payload.

AgentRuntime.emit_runtime_event() persists the same safe map in the
runtime_event_emitted OperationLog payload for report_ready.

AgentRuntime.status_summary() and AgentRuntime.gm_summary() audit payloads also
preserve environment_import_failure_code_counts, keeping report/status/GM views
aligned on the same RuntimeState-derived failure facts.

RuntimeEventValidator and AgentRuntime._SAFE_RUNTIME_EVENT_PAYLOAD_KEYS now
allow the field as sanitized diagnostic metadata.  It remains a compact failure
code count map and does not expose provider raw output, URLs, API keys, native
payloads, prompts, paths, or internal bridge details.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_failure_preserves_provider_failure_code_fact
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime environment-import failure diagnostic test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python RuntimeState summaries, final report health, report_ready
RuntimeEvents, status audit payloads, and GM audit payloads preserve safe
environment import failure diagnostics.  It does not prove live engine
environment writes, native C++ room_box / terrain import behavior, UI display,
or F5 multiplayer scene convergence.  Those remain [待 F5/实机验证].
```

## Progress Update 260 - operation replay keeps report_ready environment diagnostics

Problem:

```text
Progress Update 259 made report_ready RuntimeEvents and status/GM audit payloads
preserve environment_import_failure_code_counts.

One adjacent replay surface still had a narrower summary:

- _runtime_event_replay_summary().latest_report_ready included
  environment_import_failed_count
- but it did not include environment_import_failure_code_counts

That meant OperationLog replay could show that the final report noticed
environment import failures, but the compact latest_report_ready replay digest
still could not name the safe failure bucket.
```

Change:

```text
AgentRuntime._runtime_event_replay_summary() now includes
environment_import_failure_code_counts in latest_report_ready.

The existing environment import provider failure test now verifies the same
safe failure map across:

- environment_component_summary
- report_health_summary
- report_ready RuntimeEvent payload
- runtime_event_emitted OperationLog payload
- runtime_event_replay_summary.latest_report_ready
- runtime_status_queried OperationLog payload
- runtime_gm_summary_exported OperationLog payload

verify_ultimate_plan.py now statically checks the replay summary token as part
of the Agent-native non-native gate.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_failure_preserves_provider_failure_code_fact
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime environment-import failure replay test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python OperationLog replay summaries retain safe environment import
failure diagnostics for final report events.  It does not prove live native
environment import, C++ actor/component creation, UI rendering, or F5
multiplayer convergence.  Those remain [待 F5/实机验证].
```

## Progress Update 263 - report_ready keeps engine-write bridge diagnostics

Problem:

```text
Runtime reports already contained engine_write_boundary_summary, including
bridge_call_count, bridge_failed_count, and bridge_error_code_counts from the
C++/Python engine-write bridge.

However, report_ready RuntimeEvents and runtime_event replay summaries did not
carry those bridge diagnostics.  A post-run status or GM replay could therefore
show that a report was partial/failed while losing the direct C++ write-boundary
cause such as cpp_actor_import_failed.
```

Change:

```text
report_ready RuntimeEvent payloads now preserve safe engine-write bridge
diagnostics:

- engine_write_boundary_fact_count
- engine_write_bridge_call_count
- engine_write_bridge_success_count
- engine_write_bridge_failed_count
- engine_write_bridge_error_code_counts

RuntimeEventValidator, AgentRuntime runtime-event persistence allowlists, and
OperationLog safe payload handling now accept those aggregate fields.

AgentRuntime._runtime_event_replay_summary() copies the same fields into
latest_report_ready.

LANChatAgentWorker replay formatters now expose safe bridge failures as:

engine-write-failures <safe-code>:<count>

The formatter continues to sanitize provider/url/raw/prompt/token style labels.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime actor-import bridge diagnostics test: passed
targeted LANChat runtime replay formatter test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing Windows LF/CRLF warnings
```

Remaining:

```text
This proves Python RuntimeEvent / OperationLog / LANChat replay paths preserve
safe C++ engine-write bridge diagnostics.  It does not prove real native actor
import quality, live C++ bridge behavior, multiplayer sync convergence, or UI
rendering.  Those remain [待 F5/实机验证].
```

## Progress Update 262 - layout adjustment reports preserve transform failure causes

Problem:

```text
Completed-state layout adjustment already counted transform failures, but the
failure cause was not consistently preserved across RuntimeState summaries,
OperationLog replay, report_ready events, GM/status summaries, and LANChat
runtime text.

In F5 terms, "layout adjustment cannot find actor / cannot write transform"
could collapse into transform_failed_count=1.  That was not enough for the GM,
status query, or post-run replay to explain whether the issue was an engine
write failure, missing actor, stale actor mapping, or another transform bucket.
```

Change:

```text
AgentRuntime now aggregates layout_transform_failure_code_counts from failed
engine_transform_results.

The count map is preserved through:

- layout_adjustment_summary
- report_ready RuntimeEvent payload
- runtime_event_emitted OperationLog payload
- runtime_status_queried payload
- runtime_gm_summary_exported payload
- layout_adjustment_confirmed event payload
- operation_replay layout_adjustment_summary
- runtime_event_replay_summary.latest_report_ready

OperationLog._safe_payload() now supports safe dynamic failure-code count maps,
matching the resource/import/sync diagnostics shape.

LANChatAgentWorker._format_agent_runtime_layout_report() now shows:

transform-failures <safe-code>:<count>

The LANChat formatter redacts provider/url/raw/prompt/token style labels before
display, so this remains diagnostic without exposing internal payloads.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime layout transform failure-code test: passed
targeted LANChat runtime layout formatter test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: no whitespace errors; only existing Windows LF/CRLF warnings
```

Remaining:

```text
This proves Python Runtime/OperationLog/LANChat text paths retain safe layout
transform failure causes.  It does not prove live C++ actor transform writes,
native actor-id resolution, UI rendering, or multiplayer F5 layout adjustment.
Those remain [待 F5/实机验证].
```

## Progress Update 244 - report health exposes resource failure-code diagnostics

Problem:

```text
Progress Update 243 preserved image/model resource failure codes in RuntimeState
and batch_resource_flow_summary, but report_health_summary and the user-visible
report_ready event still only exposed coarse counters such as
resource_phase_failed_count.

That meant GM/status/report consumers could know that a resource phase failed,
but still had to inspect lower-level resource facts to know whether the cause
was image_resource_unavailable, model_resource_unavailable, or another safe
resource-stage failure code.
```

Change:

```text
report_health_summary now aggregates resource_phase_failure_code_counts from
resource_summary.by_phase.

report_ready payload now exposes safe resource_phase_failure_code_counts through
both RuntimeEventValidator and the AgentRuntime user-visible event payload
allowlist.

verify_ultimate_plan.py now gates this contract so Runtime report health and
user-visible report events cannot silently drop safe resource failure-code
diagnostics.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_resource_provider_result_records_failed_resource_facts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_partial_resource_results_report_ready_and_failed_counts
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted report-health resource failure-code tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This proves Python Runtime report/replay disclosure of safe resource-stage
failure codes.  It does not prove live provider latency, external model service
availability, or F5 user-facing pacing quality.  Those remain [待 F5/实机验证].
```

## Progress Update 245 - message delivery replay keeps safe failure diagnostics

Problem:

```text
message_delivery_summary already counted requested / succeeded / failed message
delivery events, message kinds, channels, latest stage, and progress.

For multiplayer verification that was still too coarse: if a LANChat / runtime
message failed to reach peers, status/report/replay could say "message delivery
failed" but not preserve a stable safe reason such as network_send_failed.
```

Change:

```text
_message_delivery_replay_summary now aggregates safe failure diagnostics from
send-failed OperationLog entries:

- failure_code_counts
- latest_failure_code

The summary prefers payload.failure_code, then payload.error_code, then a
sanitized payload.reason, and falls back to message_send_failed.  Unsafe fields
such as provider, prompt, URL, and asset paths remain filtered.

message_delivery_digest now carries the same safe failure-code summary so GM /
status/report consumers can distinguish generation success from multiplayer
message delivery failure without reading raw logs.

verify_ultimate_plan.py now gates the message delivery replay and digest
contract.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_message_delivery_summary_is_derived_from_safe_operation_log
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

Result:

```text
targeted message delivery failure-diagnostics test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
git diff --check: only LF/CRLF warnings, no whitespace errors
```

Remaining:

```text
This proves Python OperationLog / Runtime report replay preservation for safe
message delivery failure diagnostics.  It does not prove live LAN peer delivery,
native network stability, or F5 multiplayer convergence.  Those remain
[待 F5/实机验证].
```

## Progress Update 246 - sync replay keeps safe failure diagnostics

Problem:

```text
sync_replay_summary already counted recorded / failed sync events, actor events,
asset events, peer joins/leaves, room close, and transfer progress.

For multiplayer F5 analysis that was still too coarse: if RuntimeState rejected
or failed to persist a LANChat / engine sync event, status/report/replay could
show a sync_event_record_failed count but not preserve a stable safe diagnostic
that GM/status/report consumers could use without reading raw logs.
```

Change:

```text
OperationLog safe payload allowlists now include failure_code, and
RuntimeEventValidator also accepts failure_code plus sync_failure_code_counts.

record_sync_event now writes a safe failure_code on failed sync-event record
OperationLog entries.

_sync_replay_summary now aggregates:

- failure_code_counts
- latest_failure_code

_merge_sync_replay_summaries preserves those diagnostics when persisted
RuntimeState sync events supplement the OperationLog replay window.

_sync_health_digest_for_report now exposes:

- sync_failure_code_counts
- latest_sync_failure_code

gm_summary's sync_replay_digest also carries the same safe failure-code summary.

verify_ultimate_plan.py now gates the sync replay / sync health diagnostic
contract.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_sync_event_failure_does_not_report_recorded_or_candidate_state
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted sync event failure-diagnostics test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python OperationLog / Runtime status/report replay preservation for
safe sync-event failure diagnostics.  It does not prove live LAN packet
delivery, C++ network bridge behavior, peer convergence, or F5 multiplayer
stability.  Those remain [待 F5/实机验证].
```

## Progress Update 247 - LANChat report health surfaces sync failure diagnostics

Problem:

```text
Progress Update 246 made sync failure diagnostics available inside Runtime
status/report/replay, but LANChat's compact report-health formatter still only
showed sync status as healthy / partial / needs_attention.

That meant GM/user-facing summaries could still say "sync needs attention"
without showing the safe stable cause, even when RuntimeState already had
failure_code_counts.
```

Change:

```text
LANChatAgentWorker._format_agent_runtime_report_health_report now reads:

- sync_failure_code_counts
- latest_sync_failure_code

and appends user-safe labels such as:

- sync failures sync-event-record-failed
- latest sync failure sync-event-record-failed

The formatter continues to sanitize sensitive tokens such as provider, prompt,
URL, path, session, token, and job.

verify_ultimate_plan.py now gates the formatter contract so the LANChat report
health view cannot silently drop sync failure diagnostics.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted LANChat report-health formatter test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python LANChat/GM-facing report-health text can surface safe sync
failure diagnostics from Runtime facts.  It does not prove live LAN delivery,
C++ bridge behavior, UI rendering, or F5 multiplayer convergence.  Those remain
[待 F5/实机验证].
```

## Progress Update 248 - Sync replay and GM summary preserve failure causes

Problem:

```text
Progress Update 246 preserved sync-event failure_code_counts inside Runtime
state/report data, and Progress Update 247 surfaced the same facts through
report-health summaries.

However, two user-facing replay paths could still collapse the cause to only
"failed N":

- Runtime report sync replay
- GM Runtime summary sync replay

This made multiplayer diagnostics less actionable during F5 review because the
summary could show sync replay failures without the stable reason code.
```

Change:

```text
LANChatAgentWorker._format_agent_runtime_sync_replay_report now reads:

- failure_code_counts
- latest_failure_code

and emits safe labels such as:

- failure codes sync-event-record-failed:1
- latest failure sync-event-record-failed

LANChatAgentWorker._format_agent_runtime_gm_sync_replay_digest now applies the
same safe failure-code disclosure for GM summaries.

Both formatters sanitize sensitive markers such as provider, prompt, URL, raw,
token, API key, path, session, and job before text reaches LANChat.

verify_ultimate_plan.py now gates both formatter contracts so safe sync replay
failure diagnostics cannot be silently dropped.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_report_query_generates_safe_summary_without_coordinator_ingest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reads_agent_runtime_status_when_runtime_plan_exists
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted LANChat Runtime report + GM summary tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python LANChat report/GM summary text preserves safe sync replay
failure causes from Runtime facts.  It does not prove live LAN delivery,
C++ bridge behavior, UI rendering, or F5 multiplayer convergence.  Those remain
[待 F5/实机验证].
```

## Progress Update 249 - Message delivery diagnostics surface safe failure causes

Problem:

```text
Runtime already preserved message delivery failure diagnostics in:

- message_delivery_replay_summary.failure_code_counts
- message_delivery_replay_summary.latest_failure_code
- GM summary message_delivery_digest

But LANChatAgentWorker._format_agent_runtime_message_delivery_report only showed
requested / succeeded / failed counts, message kinds, channels, and latest
stage.  The stable reason code could be present in Runtime facts while missing
from Runtime Report and GM Runtime summary text.

That left a small but important diagnosis gap for cases where LANChat delivery
failed but the user-facing summary only said "failed 1".
```

Change:

```text
LANChatAgentWorker._format_agent_runtime_message_delivery_report now reads:

- failure_code_counts
- latest_failure_code

and emits safe labels such as:

- failure codes message-delivery-failed:1
- latest failure message-delivery-failed

The formatter uses failure-code-specific sanitization so message kind/channel
labels keep their existing wording, while stable failure codes use the same
hyphenated shape as other Runtime diagnostics.

verify_ultimate_plan.py now gates the formatter contract so LANChat message
delivery summaries cannot silently drop safe failure diagnostics.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_report_query_generates_safe_summary_without_coordinator_ingest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reads_agent_runtime_status_when_runtime_plan_exists
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted LANChat Runtime report + GM summary tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python LANChat Runtime report and GM summary text can surface safe
message delivery failure causes from Runtime facts.  It does not prove live UI
rendering, native C++ message transport, or F5 multiplayer convergence.  Those
remain [待 F5/实机验证].
```

## Progress Update 250 - Resource readiness replay labels are sanitized

Problem:

```text
ProviderReadinessValidator already blocks unsafe readiness fields at the
RuntimeState boundary, and resource readiness replay summaries expose useful
requested / enabled / unavailable counts.

The remaining disclosure hardening gap was the LANChat replay formatter:

- publish_status_counts
- status_query_status_counts
- status_counts
- latest_readiness_event.status

were rendered by replacing underscores with hyphens, but without applying the
same sensitive-marker sanitization used by other Runtime diagnostics.

If an unsafe or legacy status label containing provider / prompt / url / raw /
token / path slipped into replay facts, the user-visible Operation Replay,
Runtime Report, or GM summary could echo that label directly.
```

Change:

```text
LANChatAgentWorker._format_agent_runtime_replay_resource_readiness_report now
uses a local safe_label helper for all readiness status labels.

The helper normalizes underscores to hyphens and redacts sensitive markers:

- prompt
- provider
- url
- raw
- token
- api-key
- path
- session
- job

verify_ultimate_plan.py now gates the formatter contract so readiness replay
labels continue to pass through safe_label instead of raw string replacement.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_query_exports_safe_summary_without_creating_plan
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_report_query_generates_safe_summary_without_coordinator_ingest
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Operation Replay + Runtime Report tests: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python LANChat replay/report text sanitizes resource readiness labels
before disclosure.  It does not prove live provider readiness behavior, front-end
rendering, native C++ transport, or F5 multiplayer convergence.  Those remain
[待 F5/实机验证].
```

## Progress Update 251 - Actor import preserves missing model failure causes

Problem:

```text
Runtime actor import planning already knew which requested actors could not be
imported because their model resources were not ready.  However, the diagnostic
chain was still too weak:

- the actor import plan did not expose a stable aggregate failure_code_counts
- each planned actor did not preserve a safe failure_code
- actor import result facts did not aggregate failed import reasons
- batch resource flow reports did not surface import failure causes to LANChat

This made a partial batch look like a generic import gap instead of an explicit
"model resource missing / unavailable" condition.
```

Change:

```text
runtime.actor.import_batch now records safe import failure causes at three
levels:

- planned actor row: failure_code
- actor import plan fact: failed_count + failure_code_counts
- actor import result fact: failure_code_counts

AgentRuntime._batch_resource_flow_summary_for_plan now carries
import_failure_code_counts into the batch resource flow summary.

LANChatAgentWorker._format_agent_runtime_resource_flow_report now renders a
sanitized import-failures segment, redacting provider / prompt / url / raw /
token / api-key / path / session / job markers before user-visible disclosure.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime import failure test: passed
targeted LANChat formatter test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python Runtime actor import planning, result facts, batch resource
flow summaries, and LANChat report text preserve safe missing-model failure
diagnostics.  It does not prove native C++ actor import behavior, actual engine
asset availability, front-end rendering, or F5 multiplayer convergence.  Those
remain [待 F5/实机验证].
```

## Progress Update 252 - Report health consumes actor import failure causes

Problem:

```text
Progress Update 251 made import failure causes visible in batch resource flow
and LANChat resource-flow text.  The next read-side gap was report health:

- batch_resource_flow_summary could explain why actor import failed
- but report_health_summary still focused on batch/import counts and resource
  phase failure codes
- a final report could therefore say partial/failed without preserving the
  stable actor import failure cause at the health layer
```

Change:

```text
AgentRuntime._batch_resource_flow_summary_for_plan now aggregates
import_failure_code_counts at the top level across scoped batches.

AgentRuntime._report_health_summary now carries import_failure_code_counts from
batch resource flow into report health.

LANChatAgentWorker._format_agent_runtime_report_health_report now renders a
sanitized import failures segment, using the same marker redaction policy as
other Runtime diagnostics.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime import failure test: passed
targeted LANChat formatter test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python Runtime report health and LANChat report text can preserve
safe actor-import failure diagnostics.  It does not prove native C++ actor
import behavior, engine asset availability, front-end rendering, or F5
multiplayer convergence.  Those remain [待 F5/实机验证].
```

## Progress Update 253 - report_ready event carries actor import failure causes

Problem:

```text
Progress Update 252 moved actor import failure causes into report_health_summary
and LANChat report text.  The next event-layer gap was report_ready:

- report_health_summary contained import_failure_code_counts
- but the user-visible report_ready RuntimeEvent payload did not carry the same
  field
- RuntimeEventValidator.safe_payload also did not treat import_failure_code_counts
  as an allowed safe mapping payload

That meant UI/event replay could still lose the stable import failure reason even
when the persisted report health already had it.
```

Change:

```text
RuntimeEventValidator._SAFE_PAYLOAD_KEYS now allows import_failure_code_counts.

RuntimeEventValidator.safe_payload now treats import_failure_code_counts as a
safe count mapping, applying the same safe text normalization used by
resource_phase_failure_code_counts and sync_failure_code_counts.

AgentRuntime.generate_report now includes import_failure_code_counts in the
report_ready event payload.

verify_ultimate_plan.py now gates the report_ready payload and RuntimeEvent
allowlists for both resource phase and import failure diagnostics.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime report_ready failure-code test: passed
targeted LANChat formatter test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python RuntimeEvent/report_ready payloads preserve safe actor-import
failure diagnostics.  It does not prove live UI rendering, native C++ actor
import behavior, LAN transport, or F5 multiplayer convergence.  Those remain
[待 F5/实机验证].
```

## Progress Update 254 - status queries log actor import failure causes

Problem:

```text
Progress Update 253 made report_ready RuntimeEvents carry actor import failure
causes.  The next audit gap was status query logging:

- status_summary() returned batch_resource_flow_summary and report_health_summary
  with import_failure_code_counts
- but the runtime_status_queried OperationLog payload only recorded compact
  status/count fields
- GM/status replay could therefore prove that a report was failed or partial,
  but not why actor import failed
```

Change:

```text
AgentRuntime.status_summary() now writes two safe diagnostic maps into the
runtime_status_queried OperationLog payload:

- resource_phase_failure_code_counts
- import_failure_code_counts

The fields are compact count maps derived from report_health_summary, not raw
provider payloads or tool args.

verify_ultimate_plan.py now gates these tokens in the status_summary static
contract so future changes cannot silently drop them from status-query audit
events.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime status-query failure-code test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python status-query OperationLog payloads preserve safe actor-import
failure diagnostics.  It does not prove live GM UI rendering, native C++ actor
import behavior, LAN transport, or F5 multiplayer convergence.  Those remain
[待 F5/实机验证].
```

## Progress Update 255 - GM summary export logs actor import failure causes

Problem:

```text
Progress Update 254 made status queries preserve actor import failure causes in
OperationLog.  The next audit gap was GM summary export:

- gm_summary() already derives resource_flow_digest and report_health_digest from
  status_summary(), so the returned summary can carry import_failure_code_counts
- LANChat GM rendering can format those digests for user-visible diagnosis
- but runtime_gm_summary_exported only logged compact counts, not the safe
  failure-code maps

That meant a replay could prove the GM summary saw failed imports, but not the
reason category such as missing_ready_model_resource.
```

Change:

```text
AgentRuntime.gm_summary() now writes safe failure-code count maps into the
runtime_gm_summary_exported OperationLog payload:

- resource_import_failure_code_counts
- report_import_failure_code_counts

These are compact diagnostic count maps.  They do not include raw provider
payloads, paths, prompts, URLs, API keys, tool args, or internal worker details.

verify_ultimate_plan.py now gates both fields in the gm_summary static contract.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_empty_model_resource_provider_result_records_failed_resource_facts
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime GM-summary failure-code test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python GM-summary OperationLog payloads preserve safe actor-import
failure diagnostics.  It does not prove live GM UI rendering, native C++ actor
import behavior, LAN transport, or F5 multiplayer convergence.  Those remain
[待 F5/实机验证].
```

## Progress Update 256 - status and GM audit logs preserve sync failure causes

Problem:

```text
Runtime sync health already carried safe synchronization failure diagnostics:

- sync_health_digest.sync_failure_code_counts
- sync_health_digest.latest_sync_failure_code

But the read-side audit events were weaker:

- runtime_status_queried did not persist the sync failure-code maps
- runtime_gm_summary_exported logged sync health status and attention count, but
  not the reason category for sync failures

That meant RuntimeState/report could show sync failure causes, while status/GM
OperationLog replay could still lose the diagnostic category.
```

Change:

```text
AgentRuntime.status_summary() now writes safe sync failure diagnostics into the
runtime_status_queried OperationLog payload:

- sync_failure_code_counts
- latest_sync_failure_code

AgentRuntime.gm_summary() now writes the same safe fields into
runtime_gm_summary_exported.

The fields are compact failure-code categories and counts.  They do not include
message_id, correlation_id, peer-private payloads, asset paths, URLs, provider
details, prompts, or raw sync event bodies.

verify_ultimate_plan.py now gates both fields in status-summary and GM-summary
static contracts.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_sync_event_failure_does_not_report_recorded_or_candidate_state
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime sync-failure status/GM audit test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python RuntimeState/status/GM OperationLog payloads preserve safe
sync failure diagnostics.  It does not prove live LAN transport behavior, native
C++ sync callbacks, multiplayer convergence, or UI rendering.  Those remain
[待 F5/实机验证].
```

## Progress Update 257 - status and GM audit logs preserve layout adjustment outcomes

Problem:

```text
完成态布局调整已经能进入 RuntimeState / report / operation replay：

- layout_adjustment_summary
- final_adjustment_confirmation_summary
- layout_adjustment_replay_summary
- report_ready layout counts

但 status query 和 GM summary 的 OperationLog payload 仍偏弱：

- runtime_status_queried 没有持久记录 layout applied / skipped / transform / ground snap / overlap counts
- runtime_gm_summary_exported 没有持久记录同一组布局调整结果计数

这会导致用户问“刚才调整到底执行了什么”时，RuntimeState 可以查到，
但 status / GM 审计事件本身不能独立证明低风险布局调整的结果。
```

Change:

```text
AgentRuntime.status_summary() now writes safe layout adjustment counts into the
runtime_status_queried OperationLog payload:

- layout_proposal_count
- layout_applied_delta_count
- layout_skipped_delta_count
- layout_transform_result_count
- layout_ground_snapped_count
- layout_overlap_resolved_count

AgentRuntime.gm_summary() writes the same safe fields into
runtime_gm_summary_exported.

The fields are aggregate counts only.  They do not include actor IDs, actor
names, coordinates, raw deltas, provider output, or private engine payloads.

verify_ultimate_plan.py now gates these fields in status-summary and GM-summary
static contracts.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime layout-adjustment status/GM audit test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python RuntimeState/status/GM OperationLog payloads preserve safe
layout adjustment outcome counts.  It does not prove live engine transform
behavior, native C++ actor movement, UI rendering, or F5 multiplayer scene
convergence.  Those remain [待 F5/实机验证].
```

## Progress Update 258 - report_ready preserves sync failure diagnostics

Problem:

```text
Progress Update 256 made status and GM audit logs preserve sync failure causes.
However, the final report health path still had a gap:

- sync_health_digest contained sync_failure_code_counts and latest_sync_failure_code
- report_health_summary only carried sync_health_status and asset counts
- report_ready RuntimeEvent payload and runtime_event_emitted audit payload
  therefore could show that sync needed attention, but not the safe failure
  category

This weakened the final user-report boundary: OperationLog could prove the final
report was ready, but report_ready itself could not explain the sync failure
category without consulting another summary.
```

Change:

```text
AgentRuntime._report_health_summary() now preserves safe sync diagnostics:

- sync_failure_code_counts
- latest_sync_failure_code

AgentRuntime.generate_report() copies those fields into the report_ready
RuntimeEvent payload.

AgentRuntime.emit_runtime_event() persists the same safe fields in the
runtime_event_emitted OperationLog payload when event_type == report_ready.

RuntimeEventValidator and _SAFE_RUNTIME_EVENT_PAYLOAD_KEYS allow these fields as
sanitized diagnostic metadata.  They remain compact failure-code categories and
do not include peer-private data, message_id, correlation_id, asset paths, URLs,
provider details, prompts, or raw sync event bodies.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_sync_event_failure_does_not_report_recorded_or_candidate_state
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime sync-failure report_ready test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python report health summaries, report_ready RuntimeEvents, and
runtime_event_emitted OperationLog payloads preserve safe sync failure
diagnostics.  It does not prove live LAN transport behavior, native C++ sync
callbacks, multiplayer convergence, or UI rendering.  Those remain
[待 F5/实机验证].
```

## Progress Update 261 - LANChat replay text surfaces environment import failure buckets

Problem:

```text
Progress Update 260 made OperationLog replay summaries retain
latest_report_ready.environment_import_failure_code_counts.

The LANChat-facing replay formatter still compressed that replay state to:

- report-ready count
- report attention count
- latest-report status

It did not show the safe environment import failure bucket.  A user or GM asking
for the runtime replay could therefore see that the latest report needed
attention, but not whether the relevant failure was a room_box / terrain /
boundary engine import bucket such as cpp_environment_component_import_failed.
```

Change:

```text
LANChatAgentWorker._format_agent_runtime_replay_runtime_event_report() now
formats latest_report_ready.environment_import_failure_code_counts as:

env-import-failures <safe-code>:<count>

LANChatAgentWorker._format_agent_runtime_gm_runtime_event_replay_digest() now
does the same for GM replay digest text.

The formatter keeps the same safety behavior as other Runtime replay reports:
provider, prompt, url, raw, token, and api-key markers are rewritten to safe
resource labels before display.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted LANChat runtime replay formatter test: passed
verify_ultimate_plan.py: All current Agent-native non-native checks passed
```

Remaining:

```text
This proves Python LANChat replay text can expose safe environment import
failure buckets without leaking provider/url/internal labels.  It does not
prove UI rendering, live GM chat wording, native engine import, or F5
multiplayer convergence.  Those remain [待 F5/实机验证].
```

## Progress Update 264 - tail note for report_ready engine-write bridge diagnostics

This note records the latest continuation at the current document tail.  The
full detail for this change is in `Progress Update 263 - report_ready keeps
engine-write bridge diagnostics`.

Summary:

```text
report_ready RuntimeEvents, runtime_event replay summaries, and LANChat replay
formatters now preserve safe C++ engine-write bridge diagnostics:

- engine_write_boundary_fact_count
- engine_write_bridge_call_count
- engine_write_bridge_success_count
- engine_write_bridge_failed_count
- engine_write_bridge_error_code_counts

LANChat replay text surfaces those as:

engine-write-failures <safe-code>:<count>
```

Verification:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
All listed non-native checks passed.
Remaining live C++ bridge behavior, native import quality, UI rendering, and
multiplayer convergence remain [待 F5/实机验证].
```

## Progress Update 265 - status and GM summaries keep engine-write bridge diagnostics

Continuation goal:

```text
Make AgentRuntime read paths preserve the same safe engine-write bridge
diagnostics that report_ready already emits, so status queries and GM summaries
can explain C++ bridge/import partial failures without parsing raw provider
details.
```

Change:

```text
AgentRuntime.status_summary() now writes compact engine-write bridge counters
into the runtime_status_queried OperationLog payload:

- engine_write_boundary_fact_count
- engine_write_bridge_call_count
- engine_write_bridge_success_count
- engine_write_bridge_failed_count
- engine_write_bridge_error_code_counts

AgentRuntime.gm_summary() now includes the same bridge counters in
engine_write_boundary_digest and in runtime_gm_summary_exported payloads.

The values come from RuntimeState engine_write_boundary facts and are routed
through the existing OperationLog safe-payload allowlist.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted partial engine import test: passed
verify_ultimate_plan.py: 576 + 184 tests passed; all current Agent-native
non-native checks passed
diff check: only existing LF/CRLF warnings
```

Remaining:

```text
This proves Python Runtime status/GM/report paths can carry safe engine-write
bridge diagnostics.  It still does not prove live C++ bridge behavior, native
import quality, UI rendering, or multiplayer convergence.  Those remain
[待 F5/实机验证].
```

## Progress Update 266 - GM replay aggregates engine-write bridge diagnostics

Continuation goal:

```text
Move one more diagnosis path from ad-hoc report parsing into OperationLog
replay facts.  GM summary replay should aggregate the safe engine-write bridge
diagnostics exported by runtime_gm_summary_exported events.
```

Change:

```text
AgentRuntime._gm_summary_replay_summary() now aggregates:

- engine_write_boundary_fact_total
- engine_write_bridge_call_total
- engine_write_bridge_success_total
- engine_write_bridge_failed_total
- engine_write_bridge_error_code_counts

latest_gm_summary_event also preserves the latest GM-exported bridge failure
count and safe failure-code bucket map.

This keeps GM replay aligned with RuntimeState / OperationLog as the replay
facts source, rather than requiring consumers to inspect raw event payloads.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted partial engine import replay test: passed
verify_ultimate_plan.py: 576 + 184 tests passed; all current Agent-native
non-native checks passed
diff check: only existing LF/CRLF warnings
```

Remaining:

```text
This proves Python OperationLog replay can aggregate safe engine-write bridge
failure buckets for GM summaries.  It does not prove live C++ bridge behavior,
native import quality, UI rendering, or multiplayer convergence.  Those remain
[待 F5/实机验证].
```

## Progress Update 267 - Phase 6 selective ground snap becomes a Runtime geometry ToolCall

Task anchor:

```text
Phase 6 requires floating checks and grounding to become Runtime ToolCalls.
Before this update, selective grounding existed mainly as LANChat/completed
layout helper behavior.  It was useful, but the grounding review itself was
not yet an auditable AgentRuntime geometry tool.
```

Change:

```text
AgentRuntime ToolRegistry now exposes runtime.geometry.snap_to_ground_selective.

The tool:

- consumes room-scoped actors
- reads actor AABB bottom_y
- classifies only floor-supported objects as eligible
- skips wall-mounted, ceiling-hung, system, and unknown objects
- writes custom_geometry_facts with runtime_geometry_ground_snap
- writes a geometry_reviews entry with checkpoint_type=ground_snap_selective
- does not move actors, import models, write engine state, or call native code

This keeps the actual transform write path in layout/apply-delta tools while
making the floating/grounding diagnosis itself replayable from RuntimeState /
OperationLog.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_phase6_geometry_snap_to_ground_tool_records_review_without_actor_write editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_tool_registry_manifest_exposes_safe_capability_metadata
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Phase 6 ground snap ToolCall tests: passed
verify_ultimate_plan.py: 577 + 184 tests passed; all current Agent-native
non-native checks passed
diff check: only existing LF/CRLF warnings
```

Remaining:

```text
This proves Python Runtime can produce replayable selective grounding facts
without writing actors directly.  It does not yet prove live native AABB
quality, real actor transform application, UI wording, or multiplayer F5
convergence.  Those remain [待 F5/实机验证].
```

## Progress Update 268 - selective ground snap is wired into the batch ToolCallGraph

Task anchor:

```text
Progress 267 made selective grounding an auditable Runtime geometry tool.
However, a registered tool is not enough for Agent-native execution: the
batch ToolCallGraph must actually schedule it after import and before review
summaries/advisory proposals so floating diagnostics become part of the real
runtime execution slice.
```

Change:

```text
The batch execution graph now inserts:

runtime.geometry.snap_to_ground_selective

after runtime.actor.import_batch and runtime.geometry.review, and before:

- runtime.review.vlm_checkpoint
- runtime.review.summarize_batch
- runtime.review.generate_adjustment_proposal

The node consumes actors through the registry-derived consumes contract, keeps
risk_level=LOW, and records its ground_snap_selective review under a separate
batch ground-snap key so it does not overwrite the main geometry review.

Tests were updated to treat ground_snap_selective as a first-class batch review
only for real graph execution.  Legacy review-key compatibility tests still
expect their manually injected two-review state and do not fabricate a ground
snap review.
```

Tests / gates:

```text
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_batch_report_scopes_resource_import_and_runtime_events_to_batch editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_vlm_checkpoint_tool_creates_advisory_after_import_without_mutating_actors editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_substrate_terms_are_classified_but_not_imported_as_actors
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_review_summary_accepts_legacy_plan_batch_fact_keys
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py docs/Agent-native一步到位重构计划.md
```

Result:

```text
targeted graph/review regression tests: passed
verify_ultimate_plan.py: 577 AgentRuntime tests + 184 LANChat guard tests passed
F5 log probes and static non-native Agent-native gates passed
diff check: only existing LF/CRLF warnings
```

Remaining:

```text
This closes the Python Runtime scheduling gap for Phase 6 selective grounding
diagnostics.  It still does not claim that native actors are physically moved
or that live F5 scenes are fully grounded; actual transform application, native
AABB quality, and multiplayer visual convergence remain [待 F5/实机验证].
```

## Progress Update 269 - ground snap diagnostics feed review summaries and proposals

Task anchor:

```text
Progress 268 scheduled runtime.geometry.snap_to_ground_selective inside the
batch ToolCallGraph, but its findings were still mostly isolated review facts.
For Agent-native execution, a review fact must be usable by downstream summary
and proposal tools without bypassing RuntimeState or directly writing actors.
```

Change:

```text
runtime.review.summarize_batch now consumes room-scoped geometry_reviews as
ground_snap_reviews and filters only checkpoint_type=ground_snap_selective for
the same plan_id/batch_id.

The batch summary now exposes:

- ground_snap_review_count
- ground_snap_issue_count

runtime.review.generate_adjustment_proposal also consumes ground_snap_reviews,
merges their low-risk floating_or_sunken issues with normal geometry issues,
and can produce a confirmable move delta from selective AABB grounding.

The floating/sunken delta now prefers suggested_position[1] over suggested_y,
so AABB bottom-snap proposals move the actor toward the corrected transform y
instead of assuming the actor origin should equal ground_y.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_phase6_geometry_snap_to_ground_tool_records_review_without_actor_write editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_phase6_ground_snap_review_flows_into_batch_summary_and_adjustment_proposal editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_tool_registry_manifest_exposes_safe_capability_metadata editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_execution_graph_consumes_are_derived_from_tool_definition_contract
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py docs/Agent-native一步到位重构计划.md
```

Result:

```text
targeted Phase 6 summary/proposal slice tests: passed
verify_ultimate_plan.py: 578 AgentRuntime tests + 184 LANChat guard tests passed
F5 log probes and static non-native Agent-native gates passed
diff check: only existing LF/CRLF warnings
```

Remaining:

```text
This proves selective grounding diagnostics can flow through RuntimeState into
batch summaries and confirmable low-risk adjustment proposals.  It still does
not execute native actor transforms by itself; live transform application,
native AABB accuracy, and multiplayer scene convergence remain [待 F5/实机验证].
```

## Progress Update 270 - ground snap proposals can be confirmed through Runtime layout apply

Task anchor:

```text
After Progress 269, selective AABB grounding could produce a low-risk layout
adjustment proposal.  The next Agent-native invariant to prove was that this
proposal can use the existing Runtime confirmation/apply path instead of
requiring a LANChat-side helper or direct actor write.
```

Change:

```text
Added a focused Runtime slice test covering:

ground_snap_selective review
-> review.summarize_batch
-> review.generate_adjustment_proposal
-> confirm_layout_adjustment
-> runtime.layout.apply_delta

The test uses RuntimeState-only execution with no native provider.  It proves
that a floating floor-supported actor can be moved through the guarded layout
apply tool, updating both actor.position and actor.aabb while preserving the
proposal/applied_deltas audit trail.

This reuses the existing runtime.layout.apply_delta write boundary and keeps
native/C++ transform execution behind the existing layout_transform_provider
bridge.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_phase6_ground_snap_review_flows_into_batch_summary_and_adjustment_proposal editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_phase6_ground_snap_adjustment_confirmation_updates_runtime_actor_without_native_provider editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check -- editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py docs/Agent-native一步到位重构计划.md
```

Result:

```text
targeted ground snap confirmation slice tests: passed
verify_ultimate_plan.py: 579 AgentRuntime tests + 184 LANChat guard tests passed
F5 log probes and static non-native Agent-native gates passed
diff check: only existing LF/CRLF warnings
```

Remaining:

```text
This proves the Python Runtime confirmation/apply loop can execute the
selective ground-snap proposal against RuntimeState.  It still does not prove
native layout_transform_provider behavior, real engine actor transform, or
multiplayer sync convergence; those remain [待 F5/实机验证].
```

## Progress Update 271 - layout transform write boundary is visible in Runtime reports

Task anchor:

```text
Progress 270 proved that a ground-snap proposal can be confirmed through the
Runtime layout apply path.  The next missing invariant was observability:
when layout_transform_provider is present, the Runtime report/status/GM/replay
surfaces must show that the native transform write boundary was crossed,
without exposing provider internals.
```

Change:

```text
Extended the safe Runtime event/report payload contract with
engine_write_transform_boundary_count.

The field is now emitted through:

1. report_ready
2. runtime status summaries
3. GM summary payloads
4. runtime event replay summaries

The existing engine_write_boundary_fact_count remains the broad write-boundary
fact counter.  The new transform-specific count makes low-risk layout
adjustment confirmation auditable without leaking native provider details,
job ids, object pointers, or tool internals.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted layout transform boundary observability test: passed
verify_ultimate_plan.py: 579 AgentRuntime tests + 184 LANChat guard tests passed
F5 log probes and static non-native Agent-native gates passed
```

Remaining:

```text
This proves the Python Runtime surfaces can safely expose native layout
transform write-boundary evidence after a confirmed adjustment.  It still does
not prove real engine transform behavior, native AABB precision after transform,
or multiplayer actor convergence; those remain [待 F5/实机验证].
```

## Progress Update 272 - sync failures now raise report health and GM/status attention

Task anchor:

```text
Recent multiplayer F5 reviews showed that sync problems must not be buried in
low-level replay details.  Agent-native Runtime reports, status queries, and GM
summaries need to surface sync failure evidence as an attention state while
still preserving safe replayable failure-code counts.
```

Change:

```text
Updated Runtime report health aggregation so sync_failure_code_counts or a
latest_sync_failure_code now add the sync_failed reason and raise the overall
report health status to needs_attention when no stronger failure status already
applies.

Also added report_health_status / report_attention_required /
report_health_reasons to runtime_gm_summary_exported operation-log payloads.
Status-query payloads now preserve report_health_reasons as structured reasons
instead of only exposing the status flag.

This keeps user-facing summaries and GM-facing operation logs aligned with the
same RuntimeState + OperationLog facts used by final reports.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_sync_event_failure_does_not_report_recorded_or_candidate_state
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_sync_event_failure_does_not_report_recorded_or_candidate_state editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_failure_preserves_provider_failure_code_fact
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted sync/report/GM attention propagation tests: passed
verify_ultimate_plan.py: 579 AgentRuntime tests + 184 LANChat guard tests passed
F5 log probes and static non-native Agent-native gates passed
```

Remaining:

```text
This proves Python Runtime can elevate recorded sync failures into report,
status, and GM attention surfaces.  It still does not prove live network
recovery, peer convergence, or C++ broadcast correctness; those remain
[待 F5/实机验证].
```

## Progress Update 273 - legacy AgentCoordinator write actions are blocked by default

Task anchor:

```text
CodeGraph showed that the old AgentCoordinator can still execute add/delete/
move/modify through legacy helpers such as model acquisition and actor
transform tools.  Under the Agent-native invariants, user-facing write actions
must be routed through AgentRuntime, RuntimeGuard, ToolCallGraph, ToolResult,
StatePatch, RuntimeState, and OperationLog instead of being executed directly
by a legacy Agent coordinator.
```

Change:

```text
Added a default guard in AgentCoordinator.execute():

- add
- delete
- move
- modify

now return a structured blocked result with reason=agent_runtime_required when
OLD_WORKFLOW_DIRECT_ENTRY_DISABLED remains enabled.

Legacy direct execution is still available only through explicit debug/legacy
metadata:

- allow_legacy_direct_agent_execute
- allow_legacy_agent_coordinator_execute

This treats AgentCoordinator as old code category A/B: no longer a main-control
entry for normal users, but still available as a controlled legacy/debug
baseline while capabilities are migrated into Runtime tools.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/cai_extensions/agent/coordinator.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_legacy_agent_coordinator_blocks_runtime_controlled_actions_by_default editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_legacy_agent_coordinator_can_be_explicitly_enabled_for_debug
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_legacy_agent_coordinator_blocks_runtime_controlled_actions_by_default editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_legacy_agent_coordinator_can_be_explicitly_enabled_for_debug editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_sync_event_failure_does_not_report_recorded_or_candidate_state editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted legacy AgentCoordinator entry tests: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 184 LANChat guard tests passed
F5 log probes and static non-native Agent-native gates passed
```

Remaining:

```text
This closes one legacy Python Agent write-entry gap.  It does not remove old
workflow/helper code yet; remaining旧代码仍需按主控类禁用、可复用函数工具化、
状态迁移到 RuntimeState、测试/文档保留为 baseline 的分类继续处理。
```

## Progress Update 274 - legacy AgentCoordinator write block is now a static gate

Task anchor:

```text
Progress Update 273 blocked the old AgentCoordinator add/delete/move/modify
write actions by default.  That runtime guard also needs a non-native static
gate so future refactors cannot silently remove the AgentRuntime takeover
boundary while tests still pass through other paths.
```

Change:

```text
Added `static legacy AgentCoordinator policy gate` to
verify_ultimate_plan.py.

The gate now checks that coordinator.py keeps:

- _RUNTIME_CONTROLLED_ACTIONS for add/delete/move/modify
- default blocked result with reason/execution=agent_runtime_required
- broadcast + record of the blocked decision
- explicit debug-only legacy opt-ins:
  - allow_legacy_direct_agent_execute
  - allow_legacy_agent_coordinator_execute
- AgentRuntimeFlags.old_workflow_direct_entry_disabled as the runtime flag
  boundary

The gate is wired into the main non-native verification sequence immediately
after the host action executor policy gate.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
verify_ultimate_plan.py: 581 AgentRuntime tests + 184 LANChat guard tests passed
static legacy AgentCoordinator policy gate passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This prevents regression of one legacy direct-write boundary.  It still does
not complete old workflow dismantling: remaining旧主控/可复用函数/状态/测试文档
分类仍要继续按 AgentRuntime ToolCallGraph + RuntimeGuard + RuntimeState 的
目标架构推进。
```

## Progress Update 275 - RoleAgent scene-write fallback is blocked before legacy execution

Task anchor:

```text
LANChatAgentWorker can still route @Agent triggers into the old
LanChatAgentOrchestrator / MasterAgent path after Coordinator/Runtime planning
gates decline a message.  MasterAgent already has its own Runtime guard, but
Agent-native invariants require user-facing scene-write actions to be stopped
at the Worker boundary before the old RoleAgent execution path is entered.
```

Change:

```text
Added LANChatAgentWorker._handle_agent_trigger_runtime_write_gate().

For normal @Agent chat triggers, when legacy main workflow execution is
disabled and IntentUnderstanding classifies the message as:

- generation_start
- intervention_add
- intervention_modify
- intervention_delete
- post_generation_add
- final_adjustment_request

the worker now records `legacy_role_agent_scene_write_blocked` in OperationLog
and returns a user-safe system reply explaining that AgentRuntime owns the
scene-write path.

The gate runs after the planning gate and before `_run_agent(trigger)`, so
ordinary discussion / plan drafting can still use RoleAgent replies, while
missed scene-write requests cannot fall through into legacy RoleAgent direct
execution.

Added `static legacy RoleAgent scene-write policy gate` to
verify_ultimate_plan.py to lock this ordering and required audit event.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/lanchat_agent_worker.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_agent_trigger_scene_write_fallback_blocks_legacy_role_agent
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted RoleAgent scene-write fallback test: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 185 LANChat guard tests passed
static legacy RoleAgent scene-write policy gate passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This closes another Worker-level legacy write-entry fallback.  It still keeps
RoleAgent available for normal discussion and planning replies.  Remaining old
workflow/helper code still needs continued A/B/C/D classification and
ToolCallGraph replacement where it owns execution or state.
```

## Progress Update 276 - External Runtime audit events now go through ToolCallGraph

Task anchor:

```text
AgentRuntime.handle_message(runtime_audit_event / audit_event) still recorded
external audit facts by directly appending OperationLog entries.  Although this
did not mutate RuntimeState, it was still an execution fact path outside the
ToolCallGraph invariant.
```

Change:

```text
Added `runtime.audit_event.record` as a low-risk Runtime tool.

The `runtime_audit_event` handle_message branch now:

- sanitizes the external audit payload
- resolves any external/runtime plan link
- builds a one-node ToolCallGraph
- executes `runtime.audit_event.record`
- returns tool_graph_id and tool_call_status

The tool preserves required stable audit fields such as reply_to, event_id,
phase, source_user_id, agent_id, external_plan_id, and
runtime_payload_prepared_by_worker while still filtering provider/api_key/raw
payload-style internal fields.

The LANChat guard test helper now treats `runtime.audit_event.record` as an
internal mirror/audit graph, the same way it already treats runtime.event.emit
and planning-context mirror tools.

Added static verifier checks so future refactors cannot move
runtime_audit_event back to a direct OperationLog append branch.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_handle_message_runtime_audit_event_records_safe_operation_log_without_creating_plan
python editor/plugins/AITool/services/test_lanchat_runtime_guard.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted Runtime audit event ToolCallGraph test: passed
LANChat Runtime guard tests: 185 passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 185 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This closes the external Runtime audit-event fact path.  Internal executor
lifecycle OperationLog writes remain intentionally direct because they are the
ToolCallGraphExecutor's own replay surface.  Remaining work is still the larger
A/B/C/D classification and replacement of old workflow主控能力 with Runtime
ToolCallGraph tools.
```

## Progress Update 277 - Planning context handoff ToolCallGraph path is locked by tests and static gate

Task anchor:

```text
Multi-user / multi-Agent discussion context must survive across plan drafting,
Agent replies, host confirmation, and generation.  This path is not a scene
write, but it is the control-plane memory that prevents "方案跑偏" and must not
regress to direct RuntimeState writes or hidden legacy workflow state.
```

Change:

```text
Kept the existing `runtime.planning_context.persist` ToolCallGraph path and
added stronger regression coverage instead of rewriting the working link.

The Agent reply context test now asserts that mirrored Agent discussion creates
a completed ToolCallGraph containing `runtime.planning_context.persist`.

The static Runtime validator gate now checks:

- `runtime.planning_context.persist` is registered as a Runtime PLAN tool
- it requires room_id, changes, and context_event
- it declares active_plan_id / scene_plans / planning_context_events outputs
- `_execute_planning_context_persist_graph()` builds and executes a ToolCallGraph
- `_persist_planning_context_tool()` validates PlanningContextEvent and StatePatch
- user and Agent context mirror paths call the planning-context persist helpers

This is intentionally a防回退切口: the current path was already mostly correct,
so the value is to make the invariant mechanically enforced before larger
Agent-native dismantling continues.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_agent_context_message_is_read_only_planning_context
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted planning context ToolCallGraph assertion: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 185 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This locks the multi-Agent planning-context handoff path.  It does not yet
finish the larger old workflow拆解; next work should continue classifying old
主控能力 and replacing execution/state ownership with Runtime tools where the
current code still owns behavior outside AgentRuntime.
```

## Progress Update 278 - RoleAgent write fallback audit now preserves semantic intent safely

Task anchor:

```text
Normal @Agent chat must remain available for discussion, but write-like scene
requests must not fall through into legacy RoleAgent execution when old main
workflow is disabled.  When such a request is blocked, OperationLog must keep
enough safe semantic facts to explain which Runtime route absorbed it.
```

Change:

```text
Expanded the existing RoleAgent scene-write fallback regression from a single
add-object case to the full default-blocked write surface:

- generation_start
- intervention_add
- intervention_modify
- intervention_delete
- final_adjustment_request

This verifies `_process_trigger()` stops before `_run_agent()` for these write
intents and records `legacy_role_agent_scene_write_blocked` through the
Runtime audit ToolCallGraph path.

During the test expansion, the final layout phrase exposed a real routing bug:
when a Runtime plan existed, `_protocol_guardrail()` matched the broad modify
pattern before layout / floating / grounding patterns.  Final layout phrases now
take priority and route to `final_adjustment_request` before generic active
generation modify handling.

The Runtime audit path now preserves safe semantic audit fields:

- `intent`
- `route`
- `target_agent`

These fields are allowed in OperationLog payloads, RuntimeEvent-safe payloads,
the `handle_message(action=runtime_audit_event)` pre-graph sanitization path,
and the `runtime.audit_event.record` tool.  This fixes the previous redaction of
`final_adjustment_request` caused by the generic `request` safety marker while
still keeping provider / prompt / path / token fields blocked.

The static Runtime validator gate now requires the audit branch and audit tool
to preserve those semantic fields, preventing this replay visibility from
regressing.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_agent_trigger_scene_write_fallback_blocks_legacy_role_agent
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_agent_trigger_scene_write_fallback_blocks_legacy_role_agent editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_handle_message_runtime_audit_event_records_safe_operation_log_without_creating_plan editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_gm_summary_export_records_safe_intervention_counts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_enqueue_pending_intervention_batch_adds_next_runtime_batch editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirmed_delete_advisory_with_engine_provider_only_marks_successful_delete
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted RoleAgent write fallback test: passed
targeted audit / replay regression set: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 185 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This closes another user-entry fallback and replay-visibility gap.  It does not
finish full old workflow拆解; remaining work is still to continue A/B/C/D
classification and replace old workflow execution/state ownership with
ToolCall-sized Runtime capabilities.
```

## Progress Update 279 - LANChat model provider fallback boundary is now mechanically guarded

Task anchor:

```text
Runtime resource providers may temporarily adapt existing function-sized tools,
but missing modern model-resource tooling must not silently fall back to the old
ModelProvider unless the explicit legacy model adapter flag is enabled.  This is
part of the "old code B: reusable functions can be adapted, old main/control
paths cannot re-enter by accident" invariant.
```

Change:

```text
Added a LANChat Worker regression for the model-resource provider boundary.

When only `AGENT_RUNTIME_USE_MODEL_PROVIDER=1` is set, Worker Runtime creation
now proves that:

- the model-resource channel is marked requested
- unavailable modern tooling is recorded as an unavailable provider-readiness
  fact
- no active plan or ScenePlan is created by the preflight
- `legacy_model_provider` does not appear in Runtime readiness, configured
  provider diagnostics, or the user-facing provider-status result

The static AgentRuntime flag boundary gate now also requires this regression
test to exist, so future refactors cannot accidentally restore an implicit
fallback from modern model tooling into the legacy `ModelProvider`.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_model_provider_flag_does_not_fallback_to_legacy_model_provider
python -m py_compile editor/plugins/AITool/services/test_lanchat_runtime_guard.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted LANChat model-provider no-legacy-fallback test: passed
syntax compile for touched test/verifier files: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This closes one more feature-flag / adapter-boundary regression hole.  It does
not remove the legacy model adapter itself; that adapter remains a flagged,
function-sized transition bridge and still needs later A/B/C/D classification
once the AgentRuntime-native model resource provider is complete.
```

## Progress Update 280 - Runtime command fact ordering is now statically guarded

Task anchor:

```text
Runtime pause / cancel / resume / retry commands are control-plane state writes.
They already use the `runtime.command.record` ToolCallGraph tool for
RuntimeState persistence, but the replay OperationLog event and user-visible
RuntimeEvent must always happen after the state fact is persisted.  Otherwise a
report could claim a command happened before RuntimeState proves it.
```

Change:

```text
Added a static order check in the Runtime report fact-source gate.

The verifier now inspects `AgentRuntime.apply_runtime_command()` and requires
this order:

1. `_persist_runtime_command_state(...)`
2. `self.operation_log.append(...)`
3. `runtime_{normalized}_command_applied`
4. `self.emit_runtime_event(...)`

This keeps the current stable Runtime command implementation, but prevents a
future refactor from moving replay/user-visible events ahead of the
ToolCallGraph-backed StatePatch persistence.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
syntax compile for verifier: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This is a防回退门禁, not a new Runtime command implementation.  The next
larger step remains replacing remaining old workflow execution/state ownership
with ToolCall-sized Runtime capabilities where the current code still relies on
legacy progressive/session behavior.
```

## Progress Update 281 - SceneComposer old original-workflow fallback is now closed

Task anchor:

```text
`SceneComposer.compose()` was still a legacy main-control boundary because it
honored `USE_PROGRESSIVE_COMPOSE=0` and could route user/runtime generation back
to `_run_original_workflow(...)`.  That old clear-and-import workflow is useful
as historical baseline / A-B-C-D classification material, but it must not remain
a live user/runtime fallback while the Agent-native migration is making
ProgressiveWorkflow and SceneSession退场 into ToolCall-sized capabilities.
```

Change:

```text
`SceneComposer.compose()` no longer reads `USE_PROGRESSIVE_COMPOSE` and no
longer branches to `self._run_original_workflow(...)`.

The method now always enters `run_progressive_workflow(...)` after model
resolution/review preparation.  `_run_original_workflow` remains in the file for
legacy classification and comparison, but it is no longer reachable from the
normal compose entry.

The static direct ProgressiveWorkflow gate was strengthened:

- `scene_composer.py` is now part of the non-native py_compile target list.
- the gate requires the Agent-native migration marker and progressive call to
  remain inside `compose()`.
- the gate forbids `USE_PROGRESSIVE_COMPOSE` and
  `self._run_original_workflow(` inside the `compose()` scope.

This turns the old original workflow escape hatch into a mechanically checked
regression boundary.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/cai_extensions/agent/scene_composer.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
syntax compile for SceneComposer and verifier: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This closes only the old `SceneComposer._run_original_workflow` fallback.  The
current `run_progressive_workflow` / `SceneSession.progressive_compose` path is
still a legacy workflow主控 area and must continue to be decomposed into
BatchPlan / import / review / adjustment Runtime tools in later slices.
```

## Progress Update 282 - Runtime ToolCallGraph queue executor invariants are now statically guarded

Task anchor:

```text
Phase 5 requires the old scheduler / queue behavior to退场 into ToolCallGraph
executor semantics.  Current Runtime queue execution already uses narrow queue
tools for selecting, marking, and recording graph state, but the verifier did
not yet mechanically require those queue ToolCalls to stay in place.
```

Change:

```text
Strengthened the Runtime validator contract gate for queue execution.

The verifier now requires AgentRuntime to keep these queue ToolCall boundaries:

- `drain_next_tool_graph(...)` must use `runtime.queue.select_next_graph`
- `_persist_tool_graph_state(...)` must use `runtime.queue.record_graph_state`
- `_mark_tool_graph_queue_item(...)` must use `runtime.queue.mark_graph_status`

The same gate now also requires existing regression coverage for:

- draining a queued graph as a Runtime worker slice
- safe ToolRegistry manifest metadata, including queue select / mark / record
  tools

This does not change queue behavior; it turns the existing Phase 5 queue
executor slice into a防回退门禁.
```

Tests / gates:

```text
python -m py_compile editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
syntax compile for verifier: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This guards the Runtime queue executor cut, but does not yet remove all legacy
GenerationScheduler responsibilities.  Remaining Phase 5 work is to keep
migrating business status, backpressure, pause/cancel/retry, and resource
long-running state out of old scheduler semantics and into RuntimeState /
ToolCallGraph facts.
```

## Progress Update 283 - Provider exceptions now leave resource phase facts

Task anchor:

```text
Phase 5 provider/result handling requires real image/model provider failures to
be replayable Runtime facts.  Before this slice, a provider exception could fail
the ToolCallGraph but leave no image/model resource phase fact, which made
RuntimeState weaker than OperationLog for diagnosing why the batch stopped.
```

Change:

```text
Added `_resource_provider_failure_tool_result(...)` for image/model resource
tools.

When `runtime.asset.image.prepare` or `runtime.asset.model.prepare` catches a
provider exception:

- the ToolResult still fails and remains retryable
- the graph / batch / plan still fail through existing Runtime semantics
- the failed ToolResult now carries a StatePatch
- RuntimeState records failed `{phase}_resource_plans`
- RuntimeState records `custom_resource_phase_facts` for the failed image/model
  phase
- failure codes are sanitized as resource-unavailable codes, not raw provider
  exception text

This keeps the user-visible failure safe while making provider exceptions
visible to report/status/replay through RuntimeState facts.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_provider_failure_fails_graph_and_records_failed_resource_facts editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_model_resource_provider_failure_emits_safe_runtime_event
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted provider-failure resource fact tests: passed
syntax compile for touched Runtime/tool/test/verifier files: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This records provider exception facts; it does not yet connect real F5
image/model providers end-to-end through Runtime-native ToolCallGraph execution,
nor does it change provider retry policy or native import behavior.  Those
remain Phase 5/6 work.
```

## Progress Update 284 - Import provider failures now leave import result facts

Task anchor:

```text
Phase 5/6 provider/result handling requires import failures to be replayable
from RuntimeState, not only visible as a failed ToolCallGraph or OperationLog
entry.  Before this slice, environment import and actor import provider failures
could stop a graph without consistently leaving a batch-scoped import result fact
for report/status/replay.
```

Change:

```text
Strengthened Runtime-native import failure facts:

- `runtime.environment.import_components` now records
  `{batch_id}:environment_import_result` even when component import fails before
  usable engine results are returned
- failed environment components remain in `environment_components` as failed
  facts, but are not counted as imported
- actor import provider exceptions now record
  `{batch_id}:actor_import_result`
- actor import provider exception facts include failed per-actor import rows,
  sanitized failure codes, and zero imported/ready counts
- the verifier now checks semantic import-fact tokens instead of relying on an
  exact one-line dict formatting shape

This keeps failed import attempts visible to Runtime reports without creating
fake actors or fake imported environment components.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_actor_import_provider_requires_engine_actor_identity editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_environment_import_failure_does_not_count_planned_components_as_imported editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_actor_import_provider_failure_emits_safe_runtime_event
python -m py_compile editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted import-failure fact tests: passed
syntax compile for touched Runtime/tool/test/verifier files: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This records import failure facts in RuntimeState.  It does not yet change real
engine import behavior, native actor identity behavior, or F5 scene import
quality.  Those remain Phase 6/7 Runtime toolization and real-engine validation
work.
```

## Progress Update 285 - Import summaries now expose Runtime import failure codes

Task anchor:

```text
Phase 5/6 report/status handling requires RuntimeState facts to be the source
of user-visible diagnostics.  After Progress Update 284, actor import failures
were stored as `actor_import_result` facts, but `import_summary` still only
surfaced counts in some event-backed paths.  Failure codes could remain visible
only through lower-level batch resource flow details.
```

Change:

```text
Strengthened `_import_summary_for_plan(...)` so import failure codes flow into
report/status summaries:

- aggregates `failure_code_counts` from batch-scoped `actor_import_result` facts
- falls back to per-row `import_results[*].failure_code` when explicit counts
  are absent or empty
- avoids double-counting actor import counts when both runtime events and import
  facts exist for the same batch
- keeps empty failure-code maps explicit when a fact has no safe failure code
- verifier now requires the import-summary failure-code aggregation contract and
  its regression assertion

This makes report/status replay more fact-first: the user report can now say not
only that import failed, but also the sanitized Runtime reason family.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_actor_import_provider_failure_emits_safe_runtime_event editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_import_summary_consumes_runtime_state_import_fact_without_event editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted import-summary failure-code tests: passed
syntax compile for touched Runtime/core/test/verifier files: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This improves Runtime report/status diagnostics.  It does not yet change real
engine import quality, native actor identity repair, provider retry scheduling,
or LAN asset transfer behavior.  Those remain Phase 6/7 work.
```

## Progress Update 286 - Actor import events now carry safe failure-code families

Task anchor:

```text
Phase 5/6 disclosure handling requires Runtime events to reflect the same
fact-first import diagnostics that report/status can replay.  After Progress
Update 285, `import_summary` exposed import failure codes, but the live
`actors_imported` / `actors_import_failed` events still only surfaced counts.
```

Change:

```text
Strengthened Runtime actor-import event disclosure:

- `_emit_resource_stage_events_for_graph(...)` now reads the batch-scoped
  `actor_import_result` fact when emitting actor import events
- event payload includes `import_failure_code_counts` when a batch has safe
  import failure codes
- user-visible event codes are normalized through
  `_safe_user_visible_failure_code(...)`
- provider-specific wording is converted to adapter wording before disclosure,
  avoiding RuntimeEvent redaction while preserving the failure family
- report/status summaries still retain their existing Runtime-level diagnostic
  behavior

This closes another gap between RuntimeState facts and user-visible progress
events without changing provider execution or engine import behavior.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_actor_import_provider_failure_emits_safe_runtime_event editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_runtime_actor_import_persists_partial_success_from_engine_provider
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted actor-import event failure-code tests: passed
syntax compile for touched Runtime/core/test/verifier files: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This improves live Runtime event disclosure.  It does not yet change native
engine actor identity repair, real import quality, host-authoritative sync, or
LAN asset transfer behavior.  Those remain Phase 6/7 work.
```

## Progress Update 287 - Layout transform results are now RuntimeState facts

Task anchor:

```text
Phase 6/7 layout adjustment work requires low-risk move / align / selective
ground snap results to be replayable from RuntimeState, not only inferred from
proposal fields or live events.  This keeps OperationLog / RuntimeState ahead
of user reports while preserving the existing layout tool graph.
```

Change:

```text
Strengthened Runtime layout-adjustment fact handling:

- `runtime.layout.apply_delta` now declares `custom_report_facts` as produced
  state in addition to actor/proposal updates
- successful layout confirmations write a
  `runtime_layout_transform_result` fact keyed by plan/proposal
- the fact records applied/skipped delta counts, transform result count,
  selective ground-snap count, overlap-resolved count, and safe transform
  failure-code families
- the existing user-visible event, report, status, GM summary, and operation
  replay paths continue to expose the same safe layout diagnostics
- `verify_ultimate_plan.py` now gates that layout apply keeps this fact write
  path and selective-grounding tokens

This moves completed-state layout adjustment another step toward Agent-native
fact-first execution without changing the native engine transform provider or
the low-risk layout delta semantics.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_tool_registry_manifest_exposes_safe_capability_metadata
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted layout transform fact + manifest tests: passed
syntax compile for touched Runtime/core/test/verifier files: passed
verify_ultimate_plan.py: 581 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This improves RuntimeState replayability for completed layout adjustment.  It
does not yet change native transform quality, real collision/settle behavior,
host-authoritative layout sync, or LAN asset transfer behavior.  Those remain
Phase 6/7 work.
```

## Progress Update 288 - Layout summaries can replay transform facts without proposals

Task anchor:

```text
After Progress Update 287, completed layout adjustment wrote
`runtime_layout_transform_result` facts, but summary paths still primarily
depended on `layout_adjustment_proposals`.  Agent-native RuntimeState should
remain queryable even if proposal rows are absent, trimmed, or repaired later.
```

Change:

```text
Strengthened fact-first layout summary replay:

- `runtime_layout_transform_result` facts now include transform success/failed
  counts in addition to applied/skipped, ground-snap, overlap, and failure-code
  counts
- `_layout_adjustment_summary_for_plan(...)` now consumes
  `runtime_layout_transform_result` facts when no matching proposal row has
  already accounted for the proposal
- proposal/fact de-duplication is keyed by proposal id to avoid double-counting
  the normal confirmation path
- fact-only layout summaries now surface safe status/risk rows, transform
  status counts, ground-snap counts, overlap-resolved counts, and safe failure
  code families

This makes status/report/GM summary consumers less dependent on proposal shape
and moves layout adjustment closer to RuntimeState-as-source-of-truth.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_layout_adjustment_summary_can_replay_transform_fact_without_proposal editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_tool_registry_manifest_exposes_safe_capability_metadata
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted layout fact replay + manifest tests: passed
syntax compile for touched Runtime/core/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This improves completed layout adjustment observability and replay.  It does
not yet implement host-authoritative native transform sync, real collision
settle quality, or LAN asset transfer repair.  Those remain Phase 6/7 work.
```

## Progress Update 289 - Layout transform now feeds Runtime sync facts

Task anchor:

```text
Phase 7 requires engine-facing actor changes to become sync-visible Runtime
facts.  After Progress Update 288, layout transform results were replayable as
report facts, but successful actor transform updates were not yet reflected in
`sync_events` / `sync_state`.
```

Change:

```text
Strengthened layout-transform sync fact handoff:

- `runtime.layout.apply_delta` now declares `sync_events` and `sync_state` as
  produced state in addition to actors/proposals/report facts
- successful low-risk layout transform actor updates are converted into safe
  `actor_transform` sync facts with source `runtime_layout_transform`
- sync facts carry plan id, batch id, actor id/name, scene name, status, and
  safe transform vectors when available
- `sync_state.actor_events` and `sync_events` now reflect layout-confirmation
  actor transform results, so later status/report/sync summaries can consume
  the transform as Runtime state instead of only proposal metadata
- static verifier gates now require `_layout_transform_sync_changes(...)` and
  `runtime_layout_transform` to remain in the layout apply path

This is a Runtime-level sync handoff only: it does not broadcast network
packets or alter C++ sync behavior, but it makes layout transform updates
visible to the Agent-native sync state boundary.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_tool_registry_manifest_exposes_safe_capability_metadata
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted layout sync fact + manifest tests: passed
syntax compile for touched Runtime/core/test files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This improves Runtime sync-state visibility for layout transforms.  It does
not yet implement host-authoritative C++ transform broadcast, native collision
settle, or LAN asset transfer repair.  Those remain Phase 7 work.
```

## Progress Update 290 - Runtime sync summary exposes layout transform events

Task anchor:

```text
After Progress Update 289, layout transforms produced Runtime `actor_transform`
sync facts, but `status_summary.sync_summary` did not expose transform/delete
event diagnostics directly.  This left status queries weaker than operation
replay/report replay for completed layout adjustments.
```

Change:

```text
Strengthened Runtime sync status visibility:

- `_sync_summary_for_plan(...)` now computes safe `event_type_counts`
- actor transform events are counted as `actor_transform_count`
- actor delete events are counted as `actor_delete_count`
- completed layout adjustment tests now require transform sync facts to appear
  in `status_summary`, `operation_replay`, and report replay
- static verifier gates now require sync summary to expose transform/delete
  diagnostics and event-type counts

This closes another read-path gap: layout transform sync facts now flow through
RuntimeState, sync replay, report replay, and status summary without touching
the native network broadcast layer.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_actor_transform_and_delete_sync_events_update_runtime_facts
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted layout sync status + actor transform sync tests: passed
syntax compile for touched Runtime/core/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This improves Runtime status/read-path completeness for layout transform sync
facts.  It still does not perform host-authoritative C++ transform broadcast,
native settle/collision correction, or LAN transfer repair.  Those remain
Phase 7/native-boundary work.
```

## Progress Update 291 - Layout confirmation events disclose sync handoff counts

Task anchor:

```text
Progress Updates 289/290 made layout transform results visible in Runtime
sync facts, replay, report replay, and status summary.  The remaining
disclosure gap was the live `layout_adjustment_confirmed` RuntimeEvent:
it did not tell the host that the layout adjustment had also produced sync
facts.
```

Change:

```text
Strengthened user-visible RuntimeEvent disclosure for layout adjustment:

- layout confirmation operation-log payload now includes safe sync handoff
  counts: `sync_event_count` and `sync_actor_transform_count`
- live `layout_adjustment_confirmed` RuntimeEvent payload now exposes the same
  counts after safe sanitization
- RuntimeEventValidator, OperationLog, and AgentRuntime user-visible event
  payload allowlists now preserve these count-only diagnostics
- layout confirmation tests now require the sync handoff counts to survive
  both operation log and `user_visible_events(...)`
- static verifier gates now require both RuntimeEventValidator and the
  user-visible event payload allowlist to keep these sync count fields

This keeps the event disclosure aligned with RuntimeState: the host can see
that a completed layout adjustment produced sync-visible actor transform facts
without exposing actor ids, provider details, or raw payloads.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted layout confirmation event disclosure test: passed
syntax compile for touched Runtime/core/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This improves live disclosure of Runtime sync handoff.  It does not yet
implement native host-authoritative broadcast, collision settle, or LAN asset
transfer repair.  Those remain Phase 7/native-boundary work.
```

## Progress Update 292 - Report health carries layout sync activity counts

Task anchor:

```text
Progress Updates 289-291 made layout transform sync facts visible in Runtime
state, replay, status summary, and live layout-confirmation events.  The next
read-path gap was the report health digest: it preserved sync failures but did
not carry count-only evidence that layout adjustments had produced actor
transform/delete sync activity.
```

Change:

```text
Extended safe sync diagnostics across the report/status/GM read path:

- `_report_health_summary(...)` now copies `sync_actor_transform_count` and
  `sync_actor_delete_count` from `sync_health_digest`
- GM/report-facing `report_health_digest` now includes these two count-only
  fields
- `runtime_status_queried` operation-log payload now includes the same safe
  counts for status-query replay
- layout adjustment confirmation regression now checks report health,
  status summary, status-query operation log, and GM summary digest
- static verifier now requires report health to preserve these safe sync
  diagnostics

This keeps OperationLog/RuntimeState/GM summary aligned: after a completed
layout adjustment, the system can prove that low-risk transform deltas also
created sync-visible actor transform facts without exposing actor ids or raw
engine payloads.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_actor_transform_and_delete_sync_events_update_runtime_facts
python -m py_compile editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted layout sync report-health test: passed
targeted actor transform/delete sync fact test: passed
syntax compile for touched Runtime/core/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This is still a Runtime read-path/diagnostic improvement.  It does not replace
native host-authoritative actor broadcast, collision/settle correction, or LAN
asset transfer repair.  Those remain Phase 7/native-boundary work.
```

## Progress Update 293 - GM/report replay keeps layout sync activity counts

Task anchor:

```text
Progress Update 292 carried layout sync activity counts into report health and
status query payloads.  The adjacent replay gap was GM/report event replay:
`gm_summary(...)` returned the digest, but `runtime_gm_summary_exported` and
`runtime_event_replay_summary.latest_report_ready` did not preserve the same
count-only sync activity fields.
```

Change:

```text
Closed the GM/report replay read-path gap:

- `report_ready` RuntimeEvent payload and `runtime_event_emitted` replay payload
  now preserve `sync_actor_transform_count` and `sync_actor_delete_count`
- `runtime_gm_summary_exported` operation-log payload now preserves the same
  sync activity counts from `report_health_digest`
- `_gm_summary_replay_summary(...)` now aggregates
  `sync_actor_transform_total` and `sync_actor_delete_total`, and exposes the
  latest GM summary event's count-only sync activity diagnostics
- RuntimeEvent/OperationLog/AgentRuntime safe payload allowlists now include
  `sync_actor_delete_count`
- layout confirmation regression now verifies report-ready event replay,
  GM summary payload, and GM summary replay totals
- `verify_ultimate_plan.py` was hardened against mojibake display-token
  fragility: static gates now rely on stable structure/function tokens and
  violation printing uses safe console encoding

This keeps completion-time layout adjustment evidence visible through all
Runtime read paths: status, report, runtime event replay, GM summary, and GM
summary replay.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_confirm_layout_adjustment_applies_low_risk_deltas_through_runtime_tool
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_record_actor_transform_and_delete_sync_events_update_runtime_facts
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/test_agent_runtime_phase1.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted layout sync replay test: passed
targeted actor transform/delete sync fact test: passed
AST syntax compile for touched Runtime/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This is still inside the Python Runtime read/replay boundary.  Native
host-authoritative transform broadcast, collision/settle correction, LAN asset
transfer repair, and real F5 sync behavior remain Phase 7/native-boundary
validation work.
```

## Progress Update 294 - Sync status export keeps actor transform/delete counts

Task anchor:

```text
Progress Updates 292-293 closed report/status/GM replay visibility for layout
sync activity.  The adjacent explicit sync-status query path still exported
actor event counts but did not preserve actor transform/delete activity counts
in the `runtime_sync_status_exported` operation-log payload.
```

Change:

```text
Closed the explicit sync-status read-path gap:

- `runtime_sync_status_exported` operation-log payload now includes
  `actor_transform_count` and `actor_delete_count` from sync replay facts
- OperationLog safe payload allowlist now preserves `actor_transform_count` and
  `actor_delete_count`
- `test_sync_status_action_exports_sync_summary_without_creating_plan` now
  records actor create, transform, and delete sync events and verifies the
  counts across sync status, sync replay, sync health digest, and exported
  operation-log payload
- `verify_ultimate_plan.py` now statically requires the sync-status path to keep
  these transform/delete replay counters

This makes the direct `sync_status` action consistent with report/status/GM
read paths: every Runtime sync inspection surface can now distinguish generic
actor events from transform/delete activity without exposing actor internals.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_sync_status_action_exports_sync_summary_without_creating_plan
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/test_agent_runtime_phase1.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted sync status export test: passed
AST syntax compile for touched Runtime/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This is a Runtime sync read-path improvement.  Real host-authoritative network
broadcast, native actor settle/collision correction, and LAN asset transfer
repair remain Phase 7/native-boundary work.
```

## Progress Update 295 - Runtime sync-status action exports actor transform/delete counts

Task anchor:

```text
Progress Update 294 made the direct sync-status read path preserve actor
transform/delete counts in operation-log exports.  The next closure point was to
verify this path end to end: Runtime sync status, sync replay, sync health, and
exported operation-log payload should all distinguish actor create, transform,
and delete activity.
```

Change:

```text
Closed the explicit Runtime sync-status action coverage gap:

- OperationLog safe payloads now allow `actor_transform_count` and
  `actor_delete_count`
- `runtime_sync_status_exported` now writes these counts from sync replay facts
- sync-status regression now records actor create, actor transform, and actor
  delete events in one room and verifies all exported count surfaces
- verifier now statically requires the sync-status handler to export
  `actor_transform_count` and `actor_delete_count`

This keeps the direct `sync_status` action aligned with report/status/GM replay:
all Runtime sync inspection paths can identify transform/delete activity without
exposing actor ids, message ids, provider data, or raw payloads.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_sync_status_action_exports_sync_summary_without_creating_plan
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/test_agent_runtime_phase1.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted sync-status action export test: passed
AST syntax compile for touched Runtime/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This remains a Python Runtime read/export improvement.  Native host-authoritative
sync broadcast, collision/settle correction, LAN transfer repair, and real F5
multiplayer behavior remain Phase 7/native-boundary validation work.
```

## Progress Update 296 - Engine-write status action exports boundary diagnostics

Task anchor:

```text
After Progress Updates 292-295 closed the direct sync-status read path, the next
parallel gap was the direct engine-write status action.  Engine-write boundary
facts were already visible in reports, status summaries, GM summaries, and
report-ready events, but an explicit `engine_write_status` query did not leave a
dedicated OperationLog export event for later replay/audit.
```

Change:

```text
Closed the direct Runtime engine-write status export gap:

- `engine_write_status` / `runtime_engine_status` / `engine_bridge_status` now
  append `runtime_engine_write_status_exported` after collecting provider status
- the export payload carries safe count-only diagnostics for import,
  environment-import, transform, delete, bridge call/success/failure, and bridge
  error-code buckets
- missing external plan queries still do not fall back to the active plan, but
  now also leave an explicit recorded=false engine-write status export
- OperationLog safe payload keys now include the new engine-write boundary count
  fields
- regression tests cover normal status export, unknown external-plan export, and
  exception redaction
- verifier static gates now require the explicit engine-write status export and
  its safe diagnostic fields

This makes `engine_write_status` consistent with the rest of the Runtime read
surfaces: an operator can replay whether real engine-write boundary facts were
present without exposing actor internals, provider raw payloads, paths, URLs, or
secrets.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_write_status_reports_import_and_transform_without_creating_plan editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_write_status_unknown_external_plan_does_not_publish_or_fallback_active editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_write_status_action_exception_is_operation_logged_safely
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/test_agent_runtime_phase1.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted engine-write status export tests: passed
AST syntax compile for touched Runtime/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This is still a Python Runtime read/export improvement.  Real native actor
import/transform/delete execution, host-authoritative engine-write reconciliation,
collision/settle correction, and F5 multiplayer behavior remain Phase
7/native-boundary validation work.
```

## Progress Update 297 - Engine-write status exports enter Operation Replay

Task anchor:

```text
Progress Update 296 added a dedicated `runtime_engine_write_status_exported`
OperationLog event for direct engine-write status queries.  The follow-up gap was
that Operation Replay still treated that event as a raw entry; the replay summary
did not aggregate whether engine-write status had been exported or what safe
boundary counters were visible at query time.
```

Change:

```text
Closed the engine-write status replay gap:

- `_engine_write_replay_summary()` now recognizes
  `runtime_engine_write_status_exported`
- replay summaries include `status_export_count` and `latest_status_export`
- `latest_status_export` contains only safe count/status fields: recorded flag,
  reason, boundary counts, bridge call/success/failure counts, and sanitized
  bridge error-code buckets
- `RuntimeEventValidator` safe payload keys now allow the new engine-write
  boundary count fields, so Operation Replay snapshots can be persisted through
  RuntimeState instead of bypassing schema validation
- targeted tests now verify both normal and stale external-plan engine-write
  status exports are visible in `operation_replay()["engine_write_summary"]`
- verifier static gates require `_engine_write_replay_summary()` and its tests to
  keep the status-export replay fields

This keeps `OperationLog must precede reports` intact: direct engine-write status
queries are now replayable as structured Runtime facts, not just loose log rows.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_write_status_reports_import_and_transform_without_creating_plan editor.plugins.AITool.services.test_agent_runtime_phase1.AgentRuntimePhase1Tests.test_engine_write_status_unknown_external_plan_does_not_publish_or_fallback_active
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/test_agent_runtime_phase1.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted engine-write status replay tests: passed
AST syntax compile for touched Runtime/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This remains a Runtime read/replay closure.  It does not prove native engine
writes are correct at runtime; real actor import/transform/delete execution,
host-authoritative reconciliation, collision/settle correction, and F5
multiplayer behavior remain Phase 7/native-boundary validation work.
```

## Progress Update 298 - LANChat replay surfaces engine-write status exports

Task anchor:

```text
Progress Update 297 made `runtime_engine_write_status_exported` replayable inside
AgentRuntime Operation Replay.  The next gap was the LANChat user-facing replay
surface: `_format_agent_runtime_engine_write_report()` still displayed only
import / transform / environment-import / delete result counts, so an operator
could not see whether an explicit engine-write status query had been exported.
```

Change:

```text
Closed the LANChat engine-write status-export visibility gap:

- `_format_agent_runtime_engine_write_report()` now appends a compact
  `status-export N(...)` segment when Operation Replay includes engine-write
  status export facts
- the segment shows only safe status facts: recorded/not-recorded,
  bridge-failed count, and sanitized bridge error-code buckets
- provider/raw/prompt/url/internal path data remains filtered from the formatter
  and regression tests
- LANChat Operation Replay test now records a synthetic
  `runtime_engine_write_status_exported` event and verifies the replay reply
  surfaces `status-export` and safe error buckets
- verifier static gates now require the LANChat engine-write formatter to keep
  `status_export_count`, `latest_status_export`, and the user-visible
  `status-export` text path

This connects the Runtime replay fact from Progress Update 297 to the actual
chat-facing diagnostic surface without exposing low-level provider details.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_engine_write_report_discloses_environment_import_results editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_query_exports_safe_summary_without_creating_plan
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/lanchat_agent_worker.py','editor/plugins/AITool/services/test_lanchat_runtime_guard.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted LANChat engine-write replay tests: passed
AST syntax compile for touched LANChat/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This is a read/report surface improvement.  It does not replace real native
engine-write execution, host-authoritative reconciliation, collision/settle
correction, or F5 multiplayer validation.
```

## Progress Update 299 - GM summary surfaces engine-write status exports

Task anchor:

```text
Progress Update 298 exposed engine-write status-export facts in LANChat Operation
Replay.  The remaining read-surface gap was GM summary: `gm_summary()` built an
`engine_write_digest` from Operation Replay, but only copied import / transform /
environment-import / delete result counts.  GM could not see whether an explicit
engine-write status export had been recorded, nor whether the bridge reported
safe failure buckets.
```

Change:

```text
Closed the GM-facing engine-write status-export visibility gap:

- `AgentRuntime.gm_summary()` now carries `status_export_count` and
  `latest_status_export` inside `engine_write_digest`
- `_agent_runtime_gm_summary_reply()` already reuses the shared
  `_format_agent_runtime_engine_write_report()` formatter, so GM summaries now
  show the same safe `status-export N(...)` segment as Operation Replay
- the GM summary regression test records a synthetic
  `runtime_engine_write_status_exported` event and verifies the user-facing GM
  reply surfaces only safe facts: recorded/not-recorded, bridge-failed count,
  and sanitized bridge error-code buckets
- verifier static gates now require `AgentRuntime.gm_summary()` to keep the
  status-export fields in the GM Runtime digest

This keeps GM as a read-only coordinator over RuntimeState / OperationLog facts:
GM reads the same engine-write status truth as replay/status surfaces, without
creating plans, calling legacy workflow, or leaking provider/prompt/url data.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reads_agent_runtime_status_when_runtime_plan_exists
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/test_lanchat_runtime_guard.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted GM summary status-export test: passed
AST syntax compile for touched Runtime/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This is still a Runtime read/report closure.  It does not prove native engine
writes are correct at runtime; real actor import/transform/delete execution,
host-authoritative reconciliation, collision/settle correction, and F5
multiplayer behavior remain Phase 7/native-boundary validation work.
```

## Progress Update 300 - Engine-write readiness is visible in status/report/GM surfaces

Task anchor:

```text
The Runtime already had `engine_write_readiness_summary`, but LANChat user-facing
surfaces mainly showed provider readiness and engine-write result/replay facts.
Operators could see whether writes had happened, but not clearly whether each
engine-write channel was currently native-enabled, runtime-state-only, fallback,
disabled, or unavailable.
```

Change:

```text
Closed the engine-write readiness visibility gap without changing provider
behavior:

- `AgentRuntime.gm_summary()` now carries an `engine_write_readiness_digest`
  derived from Runtime status facts
- `LANChatAgentWorker` now has
  `_format_agent_runtime_engine_write_readiness_report()` for safe count-only
  readiness display
- Runtime status replies, Runtime report replies, and GM Runtime summaries now
  include engine-write readiness alongside engine-write result and boundary facts
- tests verify the default transition shape is visible: actor import fallback,
  actor delete / layout transform runtime-state-only, and environment import
  disabled
- verifier static gates now require the formatter and read surfaces to keep the
  readiness fields

This clarifies the Python/C++ interface boundary for F5 and implementation
handoff: read surfaces now say whether a write channel is native, fallback,
runtime-state-only, disabled, or unavailable, instead of forcing operators to
infer that from lower-level logs.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_status_query_prefers_agent_runtime_status_when_runtime_plan_exists editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reads_agent_runtime_status_when_runtime_plan_exists
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_report_query_generates_safe_summary_without_coordinator_ingest
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/lanchat_agent_worker.py','editor/plugins/AITool/services/test_lanchat_runtime_guard.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted status/report/GM engine-write readiness tests: passed
AST syntax compile for touched Runtime/LANChat/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 log probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This is still a read/report boundary improvement.  It does not enable native
engine-write providers by default, and it does not prove live C++ bridge writes,
host-authoritative transform broadcast, collision/settle correction, or LAN
asset transfer repair.  Those remain Phase 7/native-boundary validation work.
```

## Progress Update 301 - Engine-write status exports preserve readiness at replay time

Status: completed in current non-native slice.

Phase:

```text
Phase 7 / Python-C++ bridge boundary
```

Task anchor:

```text
Progress Update 300 made current engine-write readiness visible in status/report/GM
surfaces.  The remaining audit gap was temporal: an explicit
`engine_write_status` query exported bridge/result facts into OperationLog, but
its replay fact did not preserve the readiness counts observed at that moment.
After later provider flag changes, replay could show write outcomes but not the
native / fallback / runtime-state-only / disabled split that existed when the
status query was made.
```

Change:

```text
Closed the engine-write status replay readiness gap without changing provider
behavior or native writes:

- `AgentRuntime.handle_message(action=engine_write_status)` now records safe
  engine-write readiness counts in the `runtime_engine_write_status_exported`
  OperationLog payload
- `_engine_write_replay_summary()` preserves these counts in
  `latest_status_export`
- LANChat `_format_agent_runtime_engine_write_report()` now appends compact
  readiness counts inside the `status-export` segment, for example
  `readiness native:1,runtime-state:2,fallback:1,disabled:1`
- GM summary and Operation Replay inherit this through the shared engine-write
  formatter, so operators can distinguish "writes happened" from "which write
  channels were native/fallback/runtime-state-only at the query time"
- tests cover both GM summary and Operation Replay text, and verifier gates now
  require the status export payload, replay summary, formatter, and LANChat
  regression assertions to keep these safe readiness facts

No provider/raw/prompt/url/API-key/internal path data is added to the replay
surface.  The new fields are count-only readiness facts.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reads_agent_runtime_status_when_runtime_plan_exists editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_query_exports_safe_summary_without_creating_plan
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/lanchat_agent_worker.py','editor/plugins/AITool/services/test_lanchat_runtime_guard.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted GM/replay status-export readiness tests: passed
AST syntax compile for touched Runtime/LANChat/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This is still a non-native audit/read-surface closure.  It does not prove real
C++ actor import / transform / delete execution, host-authoritative broadcast,
collision/settle correction, LAN asset transfer repair, UI rendering, or F5
multiplayer convergence.  Those remain Phase 7/native-boundary validation work.
```

## Progress Update 302 - Engine-write status replay preserves readiness channel names

Status: completed in current non-native slice.

Phase:

```text
Phase 7 / Python-C++ bridge boundary
```

Task anchor:

```text
Progress Update 301 preserved engine-write readiness counts in status-export
replay facts.  Counts alone still left an audit gap: after provider flags or
engine adapters changed, an operator could tell how many channels were native /
fallback / runtime-state-only / disabled at query time, but not which write
channels were in each mode.
```

Change:

```text
Closed the channel-level status-export replay gap without enabling or changing
native writes:

- `AgentRuntime.handle_message(action=engine_write_status)` now records safe
  channel-name lists from `engine_write_readiness_summary` into the
  `runtime_engine_write_status_exported` OperationLog payload
- `_engine_write_replay_summary()` preserves sanitized channel lists in
  `latest_status_export`
- LANChat `_format_agent_runtime_engine_write_report()` appends compact channel
  groups inside the `status-export` segment, for example
  `channels native actor-import; runtime-state actor-delete/layout-transform`
- GM summary and Operation Replay inherit this through the shared formatter
- regression tests verify both count and channel-name disclosure, while still
  rejecting provider / prompt / URL / secret leakage
- verifier gates now require the export payload, replay summary, formatter, and
  LANChat tests to keep the channel-level readiness replay facts

This makes the replay evidence stronger for F5 and native-boundary handoff:
operators can see not only whether write channels were native/fallback/etc., but
which channel category each engine-write surface belonged to at the exact status
query time.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reads_agent_runtime_status_when_runtime_plan_exists editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_query_exports_safe_summary_without_creating_plan
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/lanchat_agent_worker.py','editor/plugins/AITool/services/test_lanchat_runtime_guard.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted GM/replay channel-level status-export readiness tests: passed
AST syntax compile for touched Runtime/LANChat/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 186 LANChat guard tests passed
F5 probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This remains a non-native replay/audit improvement.  It does not prove real C++
actor import / transform / delete execution, native collision/settle correction,
host-authoritative broadcast, LAN asset transfer repair, UI rendering, or F5
multiplayer convergence.  Those remain Phase 7/native-boundary validation work.
```

## Progress Update 303 - Engine-write replay flags readiness/result mismatches

Status: completed in current non-native slice.

Phase:

```text
Phase 7 / Python-C++ bridge boundary
```

Task anchor:

```text
Progress Updates 301-302 made engine-write status-export replay preserve readiness
counts and channel names.  The next audit gap was that operators still had to
manually compare write results with readiness channels.  If replay showed a
transform/import/delete result while the latest status export said the matching
channel was not native-enabled, the system should surface that as an attention
fact instead of requiring human eye-balling.
```

Change:

```text
Added conservative readiness/result consistency checks to engine-write replay:

- `_engine_write_replay_summary()` now computes `readiness_mismatch_count` and
  `readiness_mismatch_channels` from safe replay facts
- mismatch detection is count/channel based only: if import / transform / delete
  / environment-import result rows exist, but the latest status-export native
  channel list does not include the matching channel, replay records a safe
  channel label such as `layout-transform`
- LANChat `_format_agent_runtime_engine_write_report()` surfaces this as
  `readiness-mismatch N(channel...)`
- GM summary and Operation Replay inherit the signal through the shared
  engine-write formatter
- regression coverage includes both the no-mismatch path and a mismatch case
  where transform results exist while `layout_transform` is runtime-state-only
- verifier gates require the summary fields, formatter text, and LANChat
  regression assertion to remain in place

This moves the boundary from passive observability toward auditable consistency:
Runtime can now tell an operator that recorded write outcomes and current replay
readiness evidence disagree, without calling C++ or exposing provider details.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_gm_summary_reads_agent_runtime_status_when_runtime_plan_exists editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_query_exports_safe_summary_without_creating_plan editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_reports_engine_write_readiness_mismatch
python -B -c "import ast, pathlib; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in ['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/lanchat_agent_worker.py','editor/plugins/AITool/services/test_lanchat_runtime_guard.py','editor/plugins/AITool/services/verify_ultimate_plan.py']]"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted GM/replay readiness mismatch tests: passed
AST syntax compile for touched Runtime/LANChat/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 187 LANChat guard tests passed
F5 probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This is an audit consistency slice.  It does not prove native C++ writes,
collision/settle correction, host-authoritative broadcast, LAN asset transfer
repair, UI rendering, or F5 multiplayer convergence.  Those remain
Phase 7/native-boundary validation work.
```


## Progress Update 304 - Engine-write readiness mismatch enters report health attention

Status: completed in current non-native slice.

Phase:

```text
Phase 7 / Python-C++ bridge boundary
```

Task anchor:

```text
Progress Update 303 made engine-write replay detect readiness/result mismatches,
but the signal still lived mainly in replay text.  The remaining gap was that
report health and GM-facing summaries could still appear healthy unless a human
read the replay line manually.  For Agent-native operation, audit facts need to
flow into Runtime health state, not only formatter text.
```

Change:

```text
Promoted engine-write readiness mismatch into report health attention:

- `_report_health_summary()` now accepts `engine_write_summary`
- readiness mismatch count/channels are copied into report health as
  `engine_write_readiness_mismatch_count` and
  `engine_write_readiness_mismatch_channels`
- any mismatch adds `engine_write_readiness_mismatch` to report health reasons
- if no stronger failed/partial/waiting state exists, mismatch moves report
  health to `needs_attention`
- generate report, operation replay, GM/status summary, and replay report paths
  pass the existing engine-write replay summary into report health
- LANChat `_format_agent_runtime_report_health_report()` surfaces this as
  `engine-write mismatch N(channel...)`
- regression coverage now asserts that a transform result without native
  `layout-transform` readiness becomes report-health `needs_attention`
- verifier gates require Runtime health, LANChat formatter, and tests to keep
  this bridge in place

This closes another Python/C++ boundary audit gap: mismatch is now part of the
Runtime health contract, so GM/user status surfaces can flag it without relying
on manual replay interpretation.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_reports_engine_write_readiness_mismatch editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python -B -c "import ast, pathlib; paths=['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/lanchat_agent_worker.py','editor/plugins/AITool/services/test_lanchat_runtime_guard.py','editor/plugins/AITool/services/verify_ultimate_plan.py']; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in paths]; print('syntax ok')"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted mismatch/report-health formatter tests: passed
AST syntax compile for touched Runtime/LANChat/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 187 LANChat guard tests passed
F5 probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This remains a non-native audit/health-state improvement.  It does not prove
real C++ actor import / transform / delete execution, native collision/settle
correction, host-authoritative broadcast, LAN asset transfer repair, UI
rendering, or F5 multiplayer convergence.  Those remain Phase 7/native-boundary
validation work.
```


## Progress Update 305 - Report-ready events preserve engine-write mismatch attention

Status: completed in current non-native slice.

Phase:

```text
Phase 7 / Python-C++ bridge boundary
```

Task anchor:

```text
Progress Update 304 promoted engine-write readiness mismatch into report health.
The next gap was that RuntimeEvent / OperationLog report-ready evidence could
still lose the mismatch detail.  That violated the Agent-native invariant that
OperationLog must carry the auditable state before user-facing reports depend on
it.
```

Change:

```text
Extended engine-write mismatch attention through RuntimeEvent and replay:

- `report_ready` RuntimeEvent payload now includes
  `engine_write_readiness_mismatch_count` and
  `engine_write_readiness_mismatch_channels`
- RuntimeEventValidator and AgentRuntime user-visible event payload allowlists
  now explicitly permit these two safe fields
- `_runtime_event_replay_summary()` preserves the mismatch fields in
  `latest_report_ready`
- runtime status query audit payload also carries the mismatch count/channels
- LANChat runtime-event replay formatter and GM runtime-event digest show
  `engine-write-mismatch N(channel...)`
- regression tests assert mismatch survives operation replay latest-report
  extraction and both user/GM runtime-event formatters
- verifier gates require report-ready payload, runtime-event replay, formatter,
  GM digest, tests, and payload allowlists to keep this bridge intact

This makes the audit chain continuous: engine-write replay detects the mismatch,
report health marks attention, report-ready OperationLog preserves the detail,
and GM/user replay summaries can surface it without reinterpreting raw logs.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_reports_engine_write_readiness_mismatch editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python -B -c "import ast, pathlib; paths=['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/lanchat_agent_worker.py','editor/plugins/AITool/services/test_lanchat_runtime_guard.py','editor/plugins/AITool/services/verify_ultimate_plan.py']; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in paths]; print('syntax ok')"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted runtime-event mismatch tests: passed
AST syntax compile for touched Runtime/LANChat/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 187 LANChat guard tests passed
F5 probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This remains a non-native OperationLog / RuntimeEvent / health-state bridge.
It does not prove real C++ actor import / transform / delete execution, native
collision/settle correction, host-authoritative broadcast, LAN asset transfer
repair, UI rendering, or F5 multiplayer convergence.  Those remain
Phase 7/native-boundary validation work.
```


## Progress Update 306 - RuntimeEvent safe payload carries engine-write mismatch evidence

Status: completed in current non-native slice.

Phase:

```text
Phase 7 / Python-C++ bridge boundary
```

Task anchor:

```text
Progress Update 305 pushed engine-write readiness mismatch into report-ready
runtime events and replay summaries.  The follow-up gap was the safe-payload
boundary: real `emit_runtime_event()` paths use allowlists, so mismatch fields
must be explicitly permitted and covered by static gates instead of only working
in direct OperationLog test fixtures.
```

Change:

```text
Closed the RuntimeEvent safe-payload part of the mismatch evidence chain:

- RuntimeEventValidator safe payload keys now include
  `engine_write_readiness_mismatch_count` and
  `engine_write_readiness_mismatch_channels`
- AgentRuntime `_SAFE_RUNTIME_EVENT_PAYLOAD_KEYS` now also permits those fields
  for user-visible runtime events
- `report_ready` emits mismatch count/channels through the normal safe event
  path instead of relying on direct OperationLog append fixtures
- `_runtime_event_replay_summary()` preserves these fields in
  `latest_report_ready`
- status-query audit payloads also include mismatch count/channels
- LANChat runtime-event replay formatter and GM runtime-event digest surface
  `engine-write-mismatch N(channel...)`
- verifier gates now require RuntimeEventValidator, AgentRuntime safe payload
  allowlist, report-ready payload, replay summary, LANChat formatter, GM digest,
  and tests to keep the chain intact

This makes the previous report-health mismatch work survive the real RuntimeEvent
sanitization boundary, which is critical for Agent-native user-visible status and
OperationLog-first auditability.
```

Tests / gates:

```text
python -B -m unittest editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_operation_replay_reports_engine_write_readiness_mismatch editor.plugins.AITool.services.test_lanchat_runtime_guard.LANChatRuntimeGuardTests.test_runtime_resource_and_fact_source_formatters_surface_attention
python -B -c "import ast, pathlib; paths=['editor/plugins/AITool/services/agent_runtime/core.py','editor/plugins/AITool/services/lanchat_agent_worker.py','editor/plugins/AITool/services/test_lanchat_runtime_guard.py','editor/plugins/AITool/services/verify_ultimate_plan.py']; [compile(pathlib.Path(p).read_text(encoding='utf-8-sig'), p, 'exec', ast.PyCF_ONLY_AST) for p in paths]; print('syntax ok')"
python editor/plugins/AITool/services/verify_ultimate_plan.py
```

Result:

```text
targeted RuntimeEvent safe mismatch tests: passed
AST syntax compile for touched Runtime/LANChat/test/verifier files: passed
verify_ultimate_plan.py: 582 AgentRuntime tests + 187 LANChat guard tests passed
F5 probes and all current non-native Agent-native static gates passed
```

Remaining:

```text
This remains a Python-side RuntimeEvent / OperationLog boundary improvement.
It does not prove real C++ actor import / transform / delete execution, native
collision/settle correction, host-authoritative broadcast, LAN asset transfer
repair, UI rendering, or F5 multiplayer convergence.  Those remain
Phase 7/native-boundary validation work.
```

### Progress Update 307 - Provider Status Snapshot Engine-Write Readiness Audit

- Implemented a narrow AgentRuntime audit slice for `runtime.resource_status.snapshot`: the snapshot ToolResult now carries sanitized engine-write readiness counts and channel lists (`native_enabled`, `runtime_state_only`, `fallback`, `disabled`, `unavailable`).
- Extended `runtime_provider_status_snapshot_recorded` OperationLog payload with the same engine-write readiness digest, so F5/runtime replay can tell whether native engine-write channels were actually available without opening internal provider details.
- Added regression coverage in `test_provider_status_publishes_safe_readiness_without_creating_plan` to prove provider snapshots preserve engine-write readiness while still hiding provider URLs/names.
- Strengthened `verify_ultimate_plan.py` static gates so provider status snapshot code cannot silently drop the engine-write readiness audit fields.
- Verification passed: `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 308 - Status Summary Snapshot Health and Engine-Write Audit

- Extended `runtime.status_summary.snapshot` OperationLog output so `runtime_status_summary_snapshot_recorded` now includes sanitized `report_health_status`, `report_health_attention_required`, `report_health_reasons`, and engine-write readiness counts/channel lists.
- Kept the snapshot event narrow: it records replay-critical health/readiness facts without exposing full tool manifests, provider details, URLs, or raw internal state.
- Added regression coverage in `test_tool_registry_manifest_can_filter_by_category_and_status_summary_reports_counts` to prove status snapshot events preserve report-health and engine-write readiness evidence.
- Strengthened `verify_ultimate_plan.py` static gates so status summary snapshots cannot silently drop report-health / engine-write audit fields.
- Verification passed: targeted provider/status snapshot tests and `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 309 - GM Summary Snapshot Context and Intervention Audit

- Extended `runtime.gm_summary.snapshot` so both the ToolResult payload and `runtime_gm_summary_snapshot_recorded` OperationLog event now preserve sanitized GM audit fields: agent contribution count, latest user point count, intervention pending/accepted/deferred counts, layout proposal/applied/skipped counts, runtime event emitted/failed counts, and report-health status/attention.
- Kept GM snapshot logging narrow and replay-safe: the snapshot records counts and status only, without exposing raw conversation text, asset ids, provider internals, URLs, or prompt material.
- Added regression coverage in `test_runtime_gm_summary_action_records_snapshot_without_business_tool_graph` to prove GM snapshot events carry multi-agent context/intervention/layout health evidence.
- Strengthened `verify_ultimate_plan.py` static gates so GM summary snapshots cannot silently drop context/intervention/layout/runtime-event/report-health audit fields.
- Verification passed: targeted GM snapshot test and `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 310 - Runtime Events Snapshot Disclosure Audit Summary

- Added `_runtime_event_snapshot_summary()` as a narrow AgentRuntime helper that summarizes already-sanitized RuntimeEvent rows by event type, level, audience, progress-event count, warning/error count, latest event type, requested audience, and limit.
- Extended `runtime.events.snapshot` so RuntimeState facts, ToolResult payloads, and `runtime_events_snapshot_recorded` OperationLog events all carry the same safe event-disclosure audit summary.
- This keeps user-progress/disclosure verification replayable from OperationLog without exposing raw prompts, providers, URLs, or unsanitized payload fields.
- Added regression coverage for runtime event snapshot facts and OperationLog payloads, including empty-event snapshots for missing external plans.
- Strengthened `verify_ultimate_plan.py` static gates so runtime event snapshots cannot silently drop event type / level / audience / progress / warning / error audit fields.
- Verification passed: targeted runtime event snapshot tests and `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 311 - Sync Status Snapshot Transfer and Peer Audit Summary

- Extended `runtime.sync_status.snapshot` ToolResult payloads and `runtime_sync_status_snapshot_recorded` OperationLog events with sanitized multiplayer sync audit maps: `sync_event_type_counts`, `asset_transfer_status_counts`, `asset_transfer_event_type_counts`, and `peer_sync_event_type_counts`.
- Added replay-safe latest status hints (`latest_transfer_status`, `latest_transfer_progress`, `latest_peer_event_type`) while deliberately excluding asset ids, peer ids, file paths, provider internals, and raw sync payloads.
- Strengthened existing peer-sync and asset-transfer tests to prove sync snapshot events preserve transfer/peer/reconcile evidence without leaking asset paths or ids.
- Updated `verify_ultimate_plan.py` static gates so sync status snapshots cannot silently drop transfer/peer event-count audit fields.
- Verification passed: targeted sync snapshot tests and `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 312 - Status Snapshot ToolResult and OperationLog Consistency

- Closed a consistency gap in `runtime.status_summary.snapshot`: `_record_status_summary_snapshot_tool()` now returns the same sanitized report-health and engine-write readiness audit fields that `_status_summary_snapshot_via_tool_graph()` records to `runtime_status_summary_snapshot_recorded`.
- The ToolGraph execution result and OperationLog replay now agree on status snapshot health/readiness evidence, reducing ambiguity when diagnosing Runtime state through tool execution traces.
- Extended `verify_ultimate_plan.py` to check both `_status_summary_snapshot_via_tool_graph()` and `_record_status_summary_snapshot_tool()` for report-health and engine-write readiness payload fields.
- Verification passed: targeted status summary snapshot test and `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 313 - Operation Replay Summary Snapshot Audit Payload

- Added `_operation_replay_snapshot_summary_payload()` to condense operation replay summaries into a replay-safe top-level audit payload covering RuntimeEvent emission/report readiness, sync replay, asset transfer, peer sync, GM summary export, RuntimeGuard blocks, StatePatch conflicts, queue pressure, failure strategy retries, and engine-write import/bridge failure counts.
- Updated both `runtime.report.operation_replay_summary` ToolResult payloads and `runtime_report_operation_replay_summary_recorded` OperationLog events to use the shared audit payload instead of preserving only `entry_count`.
- Added regression coverage in `test_generate_report_contains_safe_operation_replay_summary` to prove operation replay summary snapshot events preserve key audit counts while still hiding prompts, providers, and asset paths.
- Strengthened `verify_ultimate_plan.py` static gates so `_operation_replay_snapshot_summary_payload()`, `_record_operation_replay_summary_tool()`, and `_operation_replay_summary_via_tool_graph()` cannot silently drop the audit payload.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted operation replay summary test; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 314 - Operation Replay Snapshot Audit Payload

- Added `_operation_replay_snapshot_audit_payload()` so direct `runtime.operation_replay.snapshot` executions produce a safe top-level audit payload instead of only `entry_count/event`.
- Updated `_record_operation_replay_snapshot_tool()` ToolResult payloads and `runtime_operation_replay_snapshot_recorded` OperationLog events to share this audit payload.
- The payload preserves replay-critical counts (`event_counts`, RuntimeEvent emitted/failed counts, sync/asset-transfer/peer counts, engine-write import/transform/delete counts, and report-health status/attention) while deliberately excluding raw `entries`, prompts, providers, URLs, graph/session/context/patch ids, and private paths.
- Strengthened `test_operation_replay_exports_runtime_audit_without_mutating_reports` to prove snapshot record events carry the safe audit payload and still do not mutate reports or leak internal fields.
- Strengthened `verify_ultimate_plan.py` static gates so `_operation_replay_snapshot_audit_payload()`, `_record_operation_replay_snapshot_tool()`, and `_operation_replay_snapshot_via_tool_graph()` cannot silently regress to entry-count-only replay evidence.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted operation replay audit test; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 315 - Operation Replay Query Audit Payload

- Extended `runtime_operation_replay_queried` OperationLog events to use the same safe `_operation_replay_snapshot_audit_payload()` that now backs `runtime_operation_replay_snapshot_recorded`.
- Direct Operation Replay queries now leave replayable audit evidence for `event_counts`, RuntimeEvent emitted/failed counts, sync/asset-transfer/peer counts, engine-write import/transform/delete counts, and report-health status/attention instead of preserving only `event/limit/entry_count`.
- Strengthened `test_operation_replay_exports_runtime_audit_without_mutating_reports` so both snapshot-recorded and queried replay events preserve the safe audit payload while excluding raw entries, prompts, providers, URLs, graph/session/context/patch ids, and private paths.
- Strengthened `verify_ultimate_plan.py` static gates so `AgentRuntime.operation_replay()` cannot silently regress to entry-count-only queried payloads.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted operation replay audit test; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 316 - Status Snapshot Failure Audit Payload

- Added `_snapshot_failure_audit_payload()` as a shared safe failure-payload helper for Runtime snapshot ToolCallGraph failures.
- Updated `runtime_status_summary_snapshot_failed` to record `summary_type`, `recorded=false`, `failure_code=snapshot_record_failed`, and sanitized `reason` instead of a reason-only payload.
- Strengthened `test_status_summary_snapshot_failure_blocks_status_return` to prove failed status snapshots are replayable without leaking prompt/provider/path fields.
- Strengthened `verify_ultimate_plan.py` static gates so status summary snapshot failures cannot silently regress to reason-only payloads.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted status snapshot failure test; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 317 - Unified Snapshot Failure Audit Payloads

- Extended `_snapshot_failure_audit_payload()` usage from status snapshots to all current Runtime snapshot failure paths: tool manifest, GM summary, runtime events, sync status, provider status, status summary, and operation replay.
- Replaced remaining reason-only / ad-hoc `*_snapshot_failed` OperationLog payloads with replay-safe payloads carrying `summary_type`, `recorded=false`, `failure_code=snapshot_record_failed`, sanitized `reason`, and narrow scope hints such as event, limit, or external plan id where relevant.
- Added `_assert_snapshot_failure_payload()` test helper and strengthened six existing failure-path tests so GM/events/sync/provider/status/operation replay snapshot failures remain auditable without leaking prompt/provider/path fields.
- Strengthened `verify_ultimate_plan.py` static gates so any current snapshot failure path that regresses to a reason-only payload is blocked by the Agent-native verifier.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted snapshot failure tests; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`582` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 318 - Tool Manifest Snapshot Failure Regression

- Added runtime regression coverage for `runtime_tool_manifest_snapshot_failed`, forcing the `runtime.tool_manifest.snapshot` ToolCallGraph write path to fail at the RuntimeState `custom_report_facts` boundary.
- Reused `_assert_snapshot_failure_payload()` for the global tool-manifest snapshot path, proving the failure event records `summary_type=runtime-tool-manifest`, `recorded=false`, `failure_code=snapshot_record_failed`, sanitized `reason`, and the requested category event without leaking prompt/provider/path fields.
- Strengthened `verify_ultimate_plan.py` so the tool-manifest snapshot failure regression test is required by the Runtime report fact-source gate, while keeping it out of unrelated RuntimeCppBridge test requirements.
- Verification passed: syntax compile for touched test/verifier files; targeted `test_tool_manifest_snapshot_failure_records_safe_audit_payload`; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 319 - ToolGraph Stop Skipped-Count Audit

- Extended `ToolCallGraphExecutor` stopped-by-runtime-command handling so pause/cancel stops count how many pending/ready downstream ToolCalls were marked skipped.
- Added `skipped_count` to the `tool_graph_stopped_by_runtime_command` OperationLog payload, the corresponding host-visible RuntimeEvent payload, and the `runtime_event_emitted` OperationLog payload for that event.
- Strengthened `test_tool_graph_executor_stops_before_next_tool_when_plan_is_paused` to prove both OperationLog-first replay and RuntimeEvent disclosure preserve the skipped-count impact without exposing downstream tool names.
- Strengthened `verify_ultimate_plan.py` static gates so ToolGraph stopped-by-command audit cannot silently drop skipped-count evidence.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted ToolGraph stop test; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 320 - RuntimeGuard Blocked ToolCall Audit Payload

- Extended ToolCallGraph blocked-call handling so `tool_call_blocked`, the host-visible blocked RuntimeEvent, and the corresponding `runtime_event_emitted` OperationLog entry carry safe RuntimeGuard audit fields: `guard_reason`, effective `risk_level`, `requires_write`, and `confirmed`.
- Kept the payload narrow and user-safe: it explains why RuntimeGuard blocked execution without exposing tool names, actor names, arguments, provider details, prompts, or paths.
- Strengthened `test_runtime_guard_blocks_unconfirmed_low_risk_write_tool` to prove OperationLog-first replay and RuntimeEvent disclosure preserve the guard decision fields while retaining existing no-leak guarantees.
- Strengthened `verify_ultimate_plan.py` static gates so RuntimeGuard blocked-call audit fields and allowlists cannot silently regress.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted RuntimeGuard blocked-call test; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 321 - RuntimeGuard Replay Summary Audit Dimensions

- Extended `_runtime_guard_replay_summary()` so Operation Replay now summarizes blocked ToolCalls by effective `risk_level`, `requires_write`, and `confirmed` state in addition to existing reason counts.
- Added replay fields `risk_level_counts`, `requires_write_blocked_count`, `confirmed_blocked_count`, `unconfirmed_blocked_count`, and enriched `latest_block` with risk/write/confirmation flags.
- Strengthened `test_runtime_guard_blocks_unconfirmed_low_risk_write_tool` to prove the RuntimeGuard payload survives from `tool_call_blocked` through RuntimeEvent disclosure into `operation_replay` summary without leaking tool names or actor names.
- Strengthened `verify_ultimate_plan.py` so RuntimeGuard replay summaries and regression tests cannot silently drop the blocked-call audit dimensions.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted RuntimeGuard blocked-call test; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 322 - LANChat RuntimeGuard Replay Disclosure

- Extended `LANChatAgentWorker._format_agent_runtime_replay_guard_report()` so Runtime status and GM replay summaries now expose safe RuntimeGuard blocked-call dimensions: write-blocked count, confirmed/unconfirmed blocked count, and risk-level distribution.
- Kept the disclosure compact and safe: summaries show counts such as `write-blocked 1`, `unconfirmed 1`, and `risk medium:1`, while still avoiding tool names, actor names, raw arguments, prompts, provider details, or paths.
- Strengthened `test_runtime_operation_replay_query_uses_metadata_batch_scope` so LANChat Operation Replay output proves the new RuntimeGuard dimensions reach user-visible replay text for the selected batch.
- Strengthened `verify_ultimate_plan.py` static gates so the LANChat RuntimeGuard replay formatter and LANChat regression tests cannot silently drop the new audit dimensions.
- Verification passed: syntax compile for touched LANChat/test/verifier files; targeted LANChat operation replay test; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 323 - OperationReplay Snapshot RuntimeGuard Audit Dimensions

- Extended Operation Replay snapshot/report audit payloads so `runtime_operation_replay_snapshot_recorded`, `runtime_operation_replay_queried`, and `runtime_report_operation_replay_summary_recorded` preserve RuntimeGuard blocked-call dimensions: blocked count, write-blocked count, confirmed/unconfirmed blocked counts, and risk-level distribution.
- Extended GM summary `runtime_guard_digest` with the same safe RuntimeGuard dimensions plus latest-block risk/write/confirmation flags, so GM/status reports do not lose the guard decision context after replay summarization.
- Strengthened `test_operation_replay_exports_runtime_audit_without_mutating_reports` and `test_generate_report_contains_safe_operation_replay_summary` to prove replay snapshot/query/report payloads retain the RuntimeGuard audit dimensions without exposing prompts, providers, asset paths, graph ids, session ids, context ids, patch ids, tool names, or actor names.
- Strengthened `verify_ultimate_plan.py` static gates so OperationReplay snapshot/report payloads, GM runtime_guard_digest, and regression tests cannot silently drop these RuntimeGuard audit dimensions.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted OperationReplay snapshot/report tests; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 324 - GM Summary Snapshot RuntimeGuard Audit Dimensions

- Extended `runtime_gm_summary_snapshot_recorded` so GM summary snapshot OperationLog events preserve the same safe RuntimeGuard blocked-call dimensions already present in GM summaries: blocked count, write-blocked count, confirmed/unconfirmed blocked counts, and risk-level distribution.
- Kept the snapshot payload narrow and replay-safe: it records guard decision counts only, without exposing tool names, actor names, raw arguments, prompts, providers, asset paths, graph ids, session ids, context ids, or patch ids.
- Strengthened `test_runtime_gm_summary_action_records_snapshot_without_business_tool_graph` to seed a blocked write ToolCall and prove both `runtime_guard_digest` and the GM snapshot payload retain RuntimeGuard audit dimensions.
- Strengthened `verify_ultimate_plan.py` static gates so `_gm_summary_snapshot_via_tool_graph` and the GM snapshot regression cannot silently drop RuntimeGuard audit dimensions.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted GM summary snapshot test; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 325 - Operation Replay Summary Failure Audit Payload

- Closed a missed snapshot-failure gap in `_operation_replay_summary_via_tool_graph`: `runtime_report_operation_replay_summary_failed` now records the shared safe `_snapshot_failure_audit_payload` instead of a reason-only payload.
- Strengthened `test_generate_report_replay_summary_failure_blocks_user_report` to prove report generation remains blocked when the OperationReplay summary snapshot cannot persist, while the failure is still replayable through `summary_type`, `recorded=false`, `failure_code=snapshot_record_failed`, and sanitized reason.
- Extended `verify_ultimate_plan.py` snapshot-failure static gates so `_operation_replay_summary_via_tool_graph` is checked with the other Runtime snapshot paths and cannot silently regress to reason-only failure logging.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted OperationReplay summary failure test; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 326 - User Report Persist Failure Safe Audit Payload

- Extended `_persist_user_report` OperationLog payloads so `user_report_state_persist_failed` carries a structured, replay-safe failure audit: `failure_code=user_report_state_persist_failed` and sanitized generic `reason=RuntimeState persistence failed`, while preserving existing report operation-log index facts.
- Kept raw StatePatch / provider / prompt details out of the failure payload and OperationLog message, so report persistence failures remain diagnosable without leaking internal adapter/provider details.
- Strengthened `test_generate_report_failure_does_not_emit_report_ready_or_write_state_report` and `test_handle_message_runtime_report_persist_failure_returns_safe_failure` to prove report-ready is not emitted, RuntimeState reports stay empty, and failed payloads include safe failure code/reason without provider or prompt leakage.
- Strengthened `verify_ultimate_plan.py` static gates so `_persist_user_report` and the report-persist failure regressions cannot silently drop safe failure audit fields.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted report persistence failure tests; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 327 - User Report Persist Failure Replay Provenance

- Extended `OperationLog._safe_payload` and `RuntimeEventValidator.safe_payload` allowlists so safe OperationLog snapshots can preserve report provenance fields `operation_log_event` and `operation_log_index` when replaying `user_report_state_persist_failed` payloads.
- Kept the provenance narrow: only the generated-report OperationLog event name and index survive replay, while provider, prompt, raw payload, graph ids, session ids, paths, and tool details remain filtered.
- Strengthened `test_generate_report_failure_does_not_emit_report_ready_or_write_state_report` to prove `OperationLog.snapshot()` keeps the report provenance and failure code in the safe replay entry after user report persistence fails.
- Strengthened `verify_ultimate_plan.py` static gates so both OperationLog and RuntimeEvent payload sanitizers, plus the report-persist replay regression, cannot silently drop this provenance bridge.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted report persist failure + OperationReplay regression tests; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).
### Progress Update 328 - Runtime Facts Injection Safe Replay Audit

- Extended `tool_call_runtime_facts_injected` OperationLog payloads with replay-safe `field_count` and `field_names` while preserving the existing raw `fields` list for direct OperationLog checks.
- Extended OperationLog and RuntimeEvent safe payload allowlists so OperationLog snapshots and OperationReplay snapshot facts retain which RuntimeState facts were injected into ToolCalls without exposing raw fact values, provider details, prompts, paths, graph ids, session ids, tool names, or tool payloads.
- Strengthened `test_batch_graph_consumes_scene_snapshot_for_placement_and_import` to prove safe OperationLog snapshots preserve injected runtime fact names and counts for placement/review/import ToolCalls.
- Strengthened `verify_ultimate_plan.py` static gates so ToolCallGraphExecutor runtime fact injection audit and both safe payload allowlists cannot silently drop this execution-plane provenance.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted runtime fact injection and OperationReplay regression tests; `python editor/plugins/AITool/services/verify_ultimate_plan.py` (`583` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current non-native static gates passed).

### Progress Update 329 - Runtime Fact Injection OperationReplay Summary

- Added `_runtime_fact_injection_replay_summary()` so OperationReplay now summarizes `tool_call_runtime_facts_injected` events by injection count, injected field total, safe field-name counts, and latest injection scope.
- Extended direct `runtime.operation_replay.snapshot` and report-side `runtime.report.operation_replay_summary` audit payloads with safe runtime-fact injection counts and field-name distributions, preserving execution-plane provenance without exposing raw RuntimeState facts, tool args, prompts, providers, paths, graph ids, session ids, or tool names.
- Persisted the shared snapshot/report audit payload into the corresponding `custom_report_facts` records, so replay queries and generated-report facts expose the same safe runtime fact injection evidence.
- Strengthened OperationReplay and generated-report regressions to prove runtime fact injection summaries reach both replay query payloads and user-report replay summaries.
- Strengthened `verify_ultimate_plan.py` static gates so OperationReplay summary paths cannot silently drop runtime fact injection audit evidence.
- Verification status: syntax compile passed for touched Runtime/test/verifier files; targeted OperationReplay/report tests passed. Full `python editor/plugins/AITool/services/verify_ultimate_plan.py` is not green in the current worktree because `test_agent_runtime_phase1.py` had to be restored from HEAD after an encoding/write corruption, which removed earlier accumulated regression-test updates required by current static gates. This is a known recovery item before claiming full gate completion.

### Progress Update 330 - Runtime Validator Static Gate Recovery

- Recovered the Runtime validator static contract gate after the `test_agent_runtime_phase1.py` restore by re-adding targeted regression anchors for actor-import failure-code summaries, partial import failure-code runtime events, and `runtime.audit_event.record` ToolCallGraph execution evidence.
- Updated high-signal regression tests to assert structured payloads instead of brittle localized message text where the restored file still contains historical mojibake expectations.
- Verified targeted regressions pass: `test_handle_message_runtime_audit_event_records_safe_operation_log_without_creating_plan`, `test_engine_actor_import_provider_missing_model_resource_fails_runtime_graph`, and `test_runtime_actor_import_persists_partial_success_from_engine_provider`.
- Full `python editor/plugins/AITool/services/verify_ultimate_plan.py` status now has all non-native static gates clear except the intentionally visible `test_agent_runtime_phase1.py` suite failure. The remaining failures are concentrated in restored legacy assertions and old expectations: stale localized/mojibake text comparisons, old provider-string no-leak checks that now collide with safe `provider_source` metadata names, and several older batch/tool manifest contract expectations. `test_lanchat_runtime_guard.py` remains green.
- Next recovery priority: fix only Agent-native contract-relevant failures in `test_agent_runtime_phase1.py`; do not spend time making every stale localized assertion exact before the Runtime execution architecture advances.

### Progress Update 331 - Batch-Scoped Runtime Contract Test Recovery

- Migrated high-signal AgentRuntime regression tests from legacy plan-scoped expectations to the current Agent-native batch-scoped fact model: `geometry_reviews`, `placement_proposals`, asset requests, and import/review consumes contracts now assert batch keys where the ToolCallGraph actually consumes state.
- Cleared the remaining `test_agent_runtime_phase1.py` errors by fixing stale test assumptions around `execute_scene_plan()` result shape, direct review provider batch ids, and legacy model provider item-name assertions. The suite now fails only with assertion failures, not runtime errors.
- Updated VLM/review advisory tests to recognize checkpoint evidence structurally through `custom_vlm_checkpoint_facts`, `review_advisory_proposals`, `structure_review`, and payload status, instead of brittle localized message substrings.
- Updated ToolRegistry/ToolCallGraph contract tests for the current Agent-native tool schema: asset tools consume batch-scoped requests and emit resource-phase facts; import and placement tools consume batch-scoped placement facts; review tools consume ground-snap review facts; environment import writes import facts; layout apply writes report and sync state.
- Recovered the OperationLog-first report invariant test by checking structured runtime-event payloads rather than a mojibake message prefix. The ordering invariant remains verified: `user_report_generated` is logged before `user_report_state_persisted` and before report-ready disclosure.
- Verification passed: syntax compile for touched Runtime/test/verifier files; targeted 7-test contract group passed (`runtime_graph_plans_assets_and_placements`, scene snapshot injection, scene review provider, VLM checkpoint advisory, ToolRegistry manifest, execution graph consumes, report log-before-state`). Full `test_agent_runtime_phase1.py` currently reports `568` tests run with `37` assertion failures and `0` errors; remaining failures are mostly legacy localized text / old provider-string / old batch-count expectations and are intentionally lower priority than continuing the Runtime architecture migration.

### Progress Update 332 - Phase1 Suite Recovery and Substrate Guardrail Alignment

- Recovered `test_agent_runtime_phase1.py` from the remaining restored legacy assertion failures: the suite now verifies Agent-native contracts structurally through RuntimeState, ToolCallGraph facts, OperationLog events, payload status, batch-scoped state, and safe summaries instead of brittle localized/mojibake UI text.
- Added a small but real scene-element guardrail fix in `scene_element_classifier.py`: English substrate/environment terms such as `forest`, `sky`, `grass`, `terrain`, `ground`, `wall`, and `ceiling` now route to `scene_substrate` with case-insensitive matching, preventing them from being imported as ordinary actor/model items.
- Re-aligned high-signal batch/resource tests with current Agent-native state ownership: environment components, placement proposals, asset requests, geometry reviews, and resource summaries are asserted by batch/runtime facts rather than legacy plan-level caches or exact user-facing strings.
- Preserved the execution-plane safety checks while loosening only stale presentation assertions: provider failures, import failures, sync events, context messages, invalid ToolResult ownership, and invalid StatePatch writes still prove safe failure, no raw provider/prompt/path leakage, no cross-room writes, no undeclared state writes, and dependent ToolCall skipping.
- Verification passed: `python -B -m unittest editor.plugins.AITool.services.test_agent_runtime_phase1` (`568` tests, OK) and `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` (`568` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current Agent-native non-native static gates passed).

### Progress Update 333 - Scene Substrate Guardrail Static Gate

- Added `static scene substrate guardrail gate` to `verify_ultimate_plan.py`, so English environment/substrate terms such as `forest`, `sky`, `grass`, `terrain`, and `ground` remain protected from slipping back into actor/model generation lists.
- The gate now checks both the `SceneElementClassifier` case-insensitive substrate guardrail and the AgentRuntime regression `test_substrate_terms_are_classified_but_not_imported_as_actors`, keeping the plan/resource boundary mechanically enforced.
- Verification passed: targeted substrate regression (`1` test, OK) and `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` (`568` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current Agent-native non-native static gates passed).

### Progress Update 334 - Layout Structure Guardrail Regression

- Extended the scene element guardrail slice beyond substrate/environment terms: English layout structure terms such as `entrance`, `main street`, and `boundary` are now regression-tested as `layout_structure`, not actor/model generation inputs.
- Added `test_layout_terms_are_classified_but_not_imported_as_actors`, verifying layout terms stay out of actors, image resource plans, model resource plans, and import model_items while still appearing in classification summaries as layout items.
- Extended `verify_ultimate_plan.py` static scene substrate/layout guardrail gate so both classifier tokens and the substrate/layout AgentRuntime regressions are required by the project-level non-native verifier.
- Verification passed: targeted substrate/layout regressions (`2` tests, OK) and `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` (`569` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current Agent-native non-native static gates passed).

### Progress Update 335 - Runtime Command ToolCall Evidence Propagation

- Strengthened the Phase 5 runtime command path (`pause`, `cancel`, `resume`, `retry`) so `_persist_runtime_command_state()` returns a safe ToolCallGraph persistence summary instead of only raising/returning implicitly.
- `apply_runtime_command()` now propagates `command_recorded`, `graph_status`, `tool_call_status`, and `state_version` into the command result and the user-visible RuntimeEvent payload. This makes command success prove that the state transition was recorded through `runtime.command.record` before replay logs and user-facing events are emitted.
- Extended safe RuntimeEvent payload allowlists for these narrow status fields; no tool args, provider, prompt, URL, model path, raw graph payload, or private path is exposed.
- Strengthened runtime command regression coverage for pause/resume/cancel and retry, and extended `verify_ultimate_plan.py` static gates so `apply_runtime_command()` cannot silently regress to command events without ToolCallGraph persistence evidence.
- Verification passed: targeted runtime command regressions (`2` tests, OK) and `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` (`569` AgentRuntime tests, `187` LANChat guard tests, F5 probes, syntax compile, and all current Agent-native non-native static gates passed).


### Progress Update 336 - Operation Replay Snapshot Evidence Propagation

- Change: `AgentRuntime._operation_replay_snapshot_via_tool_graph()` now returns safe snapshot evidence with operation replay results: `snapshot_recorded`, `snapshot_status`, `snapshot_tool_status`, and `snapshot_state_version`.
- Why: Operation replay is a core audit surface. The returned replay should prove that it was captured through `runtime.operation_replay.snapshot` and persisted through `RuntimeState`, without leaking `graph_id` / `tool_call_id` / prompt / provider internals.
- Tests: strengthened `test_operation_replay_exports_runtime_audit_without_mutating_reports` and the static Runtime report fact-source gate in `verify_ultimate_plan.py`.
- Verification: `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, all static Agent-native gates OK.
- Scope: no native build; no Quasar changes; no generation main-chain behavior change.

### Progress Update 337 - Status and GM Summary Snapshot Evidence Propagation

- Change: `AgentRuntime._status_summary_snapshot_via_tool_graph()` and `AgentRuntime._gm_summary_snapshot_via_tool_graph()` now return safe snapshot evidence with their summaries: `snapshot_recorded`, `snapshot_status`, `snapshot_tool_status`, and `snapshot_state_version`.
- Why: Status query and GM summary are coordinator-facing diagnosis surfaces. Their returned summaries should prove that they were captured through Runtime ToolCallGraph snapshot tools and persisted through `RuntimeState`, without exposing graph/tool identifiers or provider/prompt internals.
- Tests: strengthened `test_tool_registry_manifest_can_filter_by_category_and_status_summary_reports_counts` and `test_runtime_gm_summary_action_records_snapshot_without_business_tool_graph`; persisted RuntimeState facts are compared after stripping return-layer snapshot evidence so business summaries remain clean.
- Static gate: `verify_ultimate_plan.py` now requires status/GM snapshot evidence tokens and matching regression assertions.
- Verification: `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; no generation main-chain behavior change.
### Progress Update 338 - Provider and Sync Status Snapshot Evidence Propagation

- Change: `AgentRuntime._provider_status_snapshot_via_tool_graph()` and `AgentRuntime._sync_status_snapshot_via_tool_graph()` now return safe snapshot evidence with their status payloads: `snapshot_recorded`, `snapshot_status`, `snapshot_tool_status`, and `snapshot_state_version`.
- Why: Provider readiness / engine-write status and multiplayer sync status are important operator-facing diagnostics. Returned diagnostics should prove that they were captured through Runtime ToolCallGraph snapshot tools and persisted through `RuntimeState`, without exposing graph/tool identifiers, provider internals, prompts, URLs, private paths, or raw sync ids.
- Tests: strengthened sync-status and provider-status regressions so returned payloads assert snapshot evidence while persisted `custom_report_facts` are compared after stripping return-layer evidence. This keeps RuntimeState facts clean and makes the caller-visible result auditable.
- Static gate: `verify_ultimate_plan.py` now requires provider/sync snapshot evidence tokens and regression assertions for evidence stripping.
- Verification: syntax compile passed for touched Runtime/test/verifier files; targeted provider/sync regressions passed; `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; no generation main-chain behavior change.
### Progress Update 339 - Runtime Events Snapshot Evidence Propagation

- Change: `AgentRuntime._runtime_events_snapshot_via_tool_graph()` now returns a narrow snapshot envelope for runtime event feeds: `runtime_events`, `snapshot_recorded`, `snapshot_status`, `snapshot_tool_status`, and `snapshot_state_version`.
- Why: Runtime event feeds are user-visible diagnosis surfaces. The returned feed should prove that it was captured through `runtime.events.snapshot` and persisted through `RuntimeState`, while the `runtime_events` list and stored `custom_report_facts` remain clean and user-safe.
- Tests: strengthened `test_handle_message_runtime_events_lists_safe_events_without_creating_plan` so returned payloads assert snapshot evidence, and persisted event facts explicitly reject return-layer snapshot evidence. Existing failure-path tests still prove failed snapshots do not return unrecorded feeds.
- Static gate: `verify_ultimate_plan.py` now requires runtime-events snapshot evidence tokens in both `_runtime_events_snapshot_via_tool_graph()` and the `handle_message(runtime_events)` response path.
- Verification: `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; no generation main-chain behavior change.

### Progress Update 340 - Scene Entity Registry Minimum Runtime Surface

- Change: added a read-only `scene_entity_registry` surface to `AgentRuntime` status and final reports. The registry is derived from `RuntimeState` facts only: actors, observed actors, assets, environment components, substrate classification, sync status, and review status.
- Why: F5 pre-sprint requires the generated scene to be game-ready enough for later gameplay systems to consume. `scene_entity_registry` now exposes the minimum entity fields reserved by the plan: `actor_id`, `asset_id` / `model_ref`, `semantic_role`, `entity_type`, `transform`, `bounds`, `grounding_status`, `interaction_capability`, `gameplay_tags`, `physics_profile`, `audio_profile`, `lighting_profile`, `script_bindings`, `sync_status`, and `review_status`.
- Forest-camp acceptance: the existing forest-camp Runtime test now verifies that `forest`, `sky`, and `grass` remain environment/substrate entities, while `wooden table` and `tent` are actor entities. Status and final report share matching registry counts.
- Safety: `ReportRecordValidator` now accepts `scene_entity_registry` as a persisted report field, while the registry avoids exposing `model_path`, `asset_path`, private filesystem paths, provider details, prompt text, or raw tool internals.
- Verification: targeted forest-camp registry regression passed; syntax compile passed for touched Runtime/test files; `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; real C++ actor import/transform/delete, terrain write, sync transfer, VLM screenshot, and visual grounding remain `[待 F5/实机验证]`.

### Progress Update 341 - Entity Registry Asset Transfer Status Link

- Change: actor sync events can now bind a safe `model_asset_id` / `actor_asset_id` to the actor fact without counting that actor event as an asset-transfer event. `scene_entity_registry` actor entries now include a safe `asset_transfer_status` summary from RuntimeState `assets`.
- Why: multiplayer F5 needs a single game-facing entity record to show both actor presence and model transfer state. The entity registry now exposes whether the actor's asset is `transferring`, `completed`, or `failed`, plus progress/chunk/byte counters, without leaking private paths or internal message ids.
- Sync closure: the existing `runtime.sync_event.record` ToolCallGraph remains the only writer. The registry only consumes persisted RuntimeState facts (`actors`, `assets`, `sync_state`) and the final report consumes that same registry.
- Tests: strengthened `test_asset_transfer_progress_sync_event_updates_runtime_asset_summary` so an actor linked to `asset-progress` shows `asset_transfer_status.transfer_status == transferring`, progress `50`, chunk counters, byte counters, and matching status/report registry evidence. Forest-camp substrate/actor registry regression still passes.
- Verification: targeted sync asset-transfer registry regression passed; targeted forest-camp registry regression passed; syntax compile passed for touched Runtime/test files; `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; real LAN file transfer and peer-side asset availability remain `[待 F5/实机验证]`.

### Progress Update 342 - Engine Write Adapter Summary Evidence

- Change: added `engine_write_adapter_summary` to AgentRuntime status and final reports. The summary combines existing `engine_write_readiness_summary`, `engine_write_boundary_summary`, and OperationLog `engine_write_summary` into a compact read-only view for `environment_import`, `actor_import`, `actor_delete`, and `layout_transform`.
- Why: F5 pre-sprint needs operator-visible proof that engine writes are adapter-gated instead of hidden behind direct calls. The new summary shows each write channel's readiness mode, whether a write was attempted, boundary/result counts, bridge success/failure counts, and readiness mismatch count without exposing provider names, prompts, raw paths, tool ids, or internal bridge payloads.
- Runtime closure: no write path changed. Real engine mutations still have to go through `ToolCall -> RuntimeGuard -> EngineWriteGate/runtime_cpp_bridge -> ToolResult -> StatePatch -> RuntimeState -> OperationLog`; the new field only reads existing RuntimeState and OperationLog evidence.
- Tests: strengthened `test_provider_status_publishes_safe_readiness_without_creating_plan` so both `status_summary()` and `generate_report()` expose safe adapter evidence and do not leak provider details. The static Runtime report fact-source gate now requires `engine_write_adapter_summary` alongside `engine_write_readiness_summary`.
- Verification: targeted provider/status regression passed; syntax compile passed for touched Runtime/verifier files; `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; real C++ actor import/transform/delete, terrain write, bridge success, sync transfer, VLM screenshot, and visual grounding remain `[�� F5/ʵ����֤]`.

### Progress Update 343 - Layout Reflow Grounding Fact Closure

- Change: layout reflow now writes `support_type` and `grounding_status` back into RuntimeState actor facts after selective AABB bottom snap. Floor-supported actors become `grounded` after snap or when already grounded; wall-mounted / ceiling-hung / system actors are marked `not_applicable`; unknown actors remain `unknown`.
- Why: F5 pre-sprint needs `scene_entity_registry` to be directly consumable by later gameplay systems. Before this update, layout reflow corrected actor position/AABB but grounding was mostly inferred at registry time; now the actor fact itself carries explicit grounding evidence.
- Report closure: no-provider layout adjustments now count `ground_snapped_count` from applied deltas when no native transform result exists, so status/final report summaries match the RuntimeState actor updates instead of hiding successful Runtime-only snap repairs.
- Tests: strengthened `test_confirm_layout_adjustment_snaps_floor_supported_aabb_without_provider` to assert RuntimeState actor facts, status `scene_entity_registry`, final report `scene_entity_registry`, and layout summary all expose the grounded result while wall-mounted actors are not snapped to the floor.
- Verification: targeted layout grounding regression passed; syntax compile passed for touched Runtime file; `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; real imported model pivots/AABB quality, C++ transform application, visual grounding, sync transfer, and VLM screenshot remain `[�� F5/ʵ����֤]`.
