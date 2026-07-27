# Agent 任务约束循环

更新时间：2026-06-29

## 1. 文档目标

本文档用于约束后续所有 AI / Agent / Codex 对本项目的拆任务、改代码、写测试、验收和复盘行为。

本项目即将从 `Workflow-driven` 架构切换为 `Agent-native Runtime` 架构。该重构规模较大，不能依赖“Agent 自己判断要做什么”。每个 Agent 任务都必须进入明确的约束循环：

```text
目标锚定
-> 事实核实
-> 任务建模
-> 风险判定
-> 最小可运行切片
-> 实施
-> 验证
-> 状态回写
-> 复盘归档
```

这个循环的目的不是降低 Agent 自主性，而是让 Agent 的自主性被项目目标、Runtime 架构、不变量、接口边界和验收标准约束住。

## 2. 总目标锚定

所有任务必须服务于当前项目目标：

```text
多人、多 Agent、多轮讨论
-> 方案提炼与确认
-> AgentRuntime 主控
-> ScenePlan / BatchPlan
-> ToolCallGraph 执行
-> 用户实时介入
-> Geometry / VLM 审查
-> 多人同步
-> 可解释、可回放、可验收
```

禁止出现以下偏航：

```text
为了技术优雅重写无关模块
为了引入新 Agent 框架扩大范围
为了短期跑通绕过 RuntimeGuard
为了省事继续调用旧 workflow 主控
为了展示效果伪造 RuntimeState
为了让 UI 好看暴露内部 prompt / tool payload
为了修一个问题破坏单人或多人主链路
```

每个任务开始前，Agent 必须明确回答：

```text
这个任务服务哪个项目目标？
它属于 AgentRuntime 重构的哪个阶段？
它改变的是控制面、执行面、状态面、同步面、UI 披露，还是质量审查？
它是否会影响单人、多 Agent、多人成员联机中的哪条链路？
```

## 3. Agent 任务九步循环

### Step 1：目标锚定

任务开始时，先写出目标锚点。

格式：

```text
任务目标：
所属阶段：
关联文档：
涉及主链路：
预期收益：
不做范围：
```

示例：

```text
任务目标：将 SceneComposer 中的对象提取能力拆成 scene.extract_objects Tool
所属阶段：Phase 3：拆 SceneComposer 为 plan / asset / placement 工具
关联文档：Agent-native一步到位重构计划.md
涉及主链路：ScenePlan / ToolCallGraph / ToolRegistry
预期收益：SceneComposer 不再主控完整生成
不做范围：不改模型 provider，不改 C++ import，不改 UI
```

### Step 2：事实核实

所有代码任务必须先核实当前事实，不能凭记忆修改。

强制顺序：

```text
MCP CodeGraph
-> CLI codegraph.cmd
-> 普通文件工具
```

必须核实：

```text
目标文件 / 符号
当前调用方
当前被调用方
blast radius
相关测试
Python / C++ 边界
是否已有历史补丁
是否存在未提交改动
```

禁止：

```text
未查 CodeGraph 直接改 LANChat / Coordinator / Scheduler / SceneComposer / ProgressiveWorkflow / Sync
未确认调用方就删除旧函数
未确认测试覆盖就迁移状态源
未确认 C++ 接口就重写 Python binding 调用
```

### Step 3：任务建模

每个任务必须被归类为以下一种或多种：

```text
control_plane：入口、路由、确认、GM、Planner、Builder、Reviewer
execution_plane：ToolCallGraph、ToolRegistry、ToolAdapter、Scheduler executor
state_plane：RuntimeState、StatePatch、OperationLog、schema version
engine_plane：actor import、transform、AABB、room/terrain、EngineWriteGate
sync_plane：LANChat、actor broadcast、asset transfer、peer state
review_plane：Geometry review、VLM review、AdjustmentProposal
ui_plane：RuntimeEvent、Disclosure、progress、host/participant visibility
test_plane：unit、integration、F5、legacy regression
doc_plane：架构、验收、复盘、接口盘点
```

分类后必须说明：

```text
输入是什么？
输出是什么？
事实源是谁？
写操作是否需要 RuntimeGuard？
结果是否必须写 OperationLog？
是否需要 StatePatch？
是否跨 Python / C++？
```

### Step 4：风险判定

每个任务必须先判定风险等级。

Low Risk：

```text
新增文档
新增 mock 测试
只读查询
新增 Validator
新增 schema 类型
不接真实引擎的 Runtime mock flow
```

Medium Risk：

```text
迁移 Python 内部调用
新增 ToolRegistry 工具
替换部分 SceneComposer 能力
新增 RuntimeState patch
修改 UI 展示状态
低风险 actor transform
```

High Risk：

```text
删除旧 workflow 主控入口
改 LANChat / NetworkSystem C++
改 actor sync / asset transfer
改 import_model / transform / remove
改 GenerationScheduler 队列行为
改多人权限 / host confirmation
修改 system actor
```

High Risk 任务必须额外写：

```text
回滚方式
F5 验收方式
是否需要 C++/实机验证
是否需要先做 mock 切片
是否可能影响已有稳定功能
```

## 4. AgentRuntime 重构专用约束

### 4.1 架构不变量

任何 Agent 任务都不得破坏以下不变量：

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

如果任务需要临时违反某条不变量，必须停止并重新设计，不允许“先这么做以后再改”。

### 4.2 旧代码处理约束

旧代码分四类处理：

```text
A. 主控类：删除 / 禁用 / 隐藏
B. 可复用函数类：拆成 Tool
C. 状态类：迁移到 RuntimeState
D. 测试 / 文档类：保留为 legacy regression baseline
```

Agent 在改旧代码前必须明确：

```text
它属于 A/B/C/D 哪一类？
是否已有 ToolCall 替代？
是否已有 RuntimeState 映射？
是否已有 legacy regression 测试？
是否可以删除，还是只能隐藏？
```

硬规则：

```text
不能把完整 compose / progressive workflow 包成 legacy big tool
不能先删旧主控再补新 Runtime
不能过早删除旧测试
不能把旧 workflow 内部状态继续作为用户可见事实源
```

### 4.3 Python / C++ 接口约束

本项目已有大量能力下沉到 C++。Agent 任务必须先判断接口事实源。

事实源划分：

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
```

跨边界调用必须通过：

```text
ToolCall
-> RuntimeGuard
-> runtime_cpp_bridge
-> C++ binding/API
-> ToolResult
-> StatePatch
-> RuntimeState
```

禁止：

```text
业务 Agent 直接调用 CoronaEngine.* binding
业务 Agent 直接调用 NetworkSystem 暴露函数
业务 Agent 直接调用 SceneTools.create_actor
业务 Agent 直接写 LANChat message
```

## 5. 最小可运行切片约束

每个阶段都必须定义最小可运行切片，不能只提交抽象结构。

### Phase 1 切片

```text
Mock 卧室：
用户需求 -> ScenePlan -> Confirm -> BatchPlan -> Mock ToolCallGraph -> RuntimeState -> OperationLog -> Report
```

不允许接：

```text
SceneComposer
ProgressiveWorkflow
GenerationScheduler
C++ NetworkSystem
真实 import
```

### Phase 2 切片

```text
真实 ScenePlan + Mock 资源 + Mock 导入
```

必须验证：

```text
RuntimeGuard
ToolRegistry
ToolCallGraphExecutor
Validator
StatePatch merge
OperationLog
```

### Phase 3 切片

```text
真实对象提取 + 真实场景类型判断 + Mock 导入
```

必须验证：

```text
SceneComposer 不再主控完整生成
extract / classify / route 变成 ToolCall
```

### Phase 4 切片

```text
真实 BatchPlan + Mock 资源 + 轻量导入路径
```

必须验证：

```text
用户介入进入 pending_interventions
BatchPlan 替代 workflow phase
```

### Phase 5+ 切片

后续每阶段必须至少证明：

```text
旧能力已被 ToolCall 替代
RuntimeState 能查询
OperationLog 能复盘
旧主控入口没有新增依赖
```

## 6. 任务执行模板

后续每个 Agent 任务必须按以下模板输出和执行。

```text
任务编号：
任务标题：
所属阶段：
目标锚点：
当前代码事实：
涉及文件/符号：
旧代码分类：
输入：
输出：
新增/修改接口：
RuntimeState 影响：
OperationLog 事件：
RuntimeGuard 规则：
StatePatch 规则：
Python/C++ 边界：
测试用例：
F5/实机验证：
风险等级：
回滚方式：
完成标准：
```

不允许只有：

```text
“实现 xxx”
“优化 xxx”
“接入 xxx”
```

必须精确到：

```text
改什么
为什么改
在哪改
怎么验证
失败怎么回退
是否影响旧链路
是否需要多人联机验证
```

## 7. 验证循环

每个任务完成后必须经过验证循环。

### 7.1 自动化验证

根据任务类型选择：

```text
AgentRuntime mock flow
ScenePlan / BatchPlan schema test
ToolCallGraph executor test
RuntimeGuard test
StatePatch merge test
OperationLog test
Validator test
no direct workflow entry static test
legacy regression test
frontend runtime event test
C++ protocol test [待 C++/F5 验证]
```

### 7.2 F5 / 实机验证

触及以下内容必须标记或执行 F5：

```text
C++ binding
LANChat room / peer / agent roster
actor import
actor transform
asset transfer
network broadcast
VLM screenshot
CEF UI
多人联机同步
```

未执行 F5 时，结论必须写：

```text
[待 F5/实机验证]
```

### 7.3 复盘验证

每个任务完成后必须能回答：

```text
RuntimeState 是否更新正确？
OperationLog 是否能复盘？
是否有 late result / abandoned？
是否有 StatePatch conflict？
是否有 C++ 返回失败但 Python 误判成功？
是否有 UI 显示和 RuntimeState 不一致？
是否有旧 workflow 主控路径残留？
```

## 8. 状态回写与文档更新

每完成一个任务，必须更新对应记录。

建议位置：

```text
docs/Agent-native一步到位重构计划.md：只更新架构级计划变化
docs/Agent任务约束循环.md：只更新任务执行规约
docs/F5运行复盘记录.md：记录实机日志问题
docs/Codex攻坚修改记录.md：记录阶段性改动摘要
```

状态回写必须包含：

```text
已完成内容
验证结果
未验证内容
[待 F5/实机验证]
风险遗留
下一步任务
```

## 9. Agent 反模式清单

禁止以下行为：

```text
跳过 CodeGraph 直接改核心代码
未定义 RuntimeState 就开始写工具
未定义 ToolResult 就调用 C++ binding
未写 OperationLog 就返回用户报告
让 Agent 直接 import / move / delete actor
把旧 compose 包成一个大工具
先删旧 workflow 再补新 Runtime
把 raw chat history 塞进生成 prompt
状态查询读取旧 scheduler / workflow 内部状态
UI 显示内部 tool payload / prompt / provider raw error
旧测试未迁移就删除
多人同步未验证就声称完成
```

## 10. 最终结论

Agent-native 重构不是让 Agent 更自由地乱调用工具，而是建立一个更严格的任务闭环：

```text
Agent 可以更自由地决策
但必须被 RuntimeState、ToolCallGraph、RuntimeGuard、OperationLog 和 C++/Python 接口协议约束
```

只有坚持这套任务约束循环，后续实时介入、多 Agent 协作、多人同步和开放场景生成才不会在大重构中失控。

本文件是后续所有 Agent 执行任务的操作规约。任何拆任务文档、代码修改计划、实施 PR、F5 验收和复盘，都必须能映射回本文档的约束循环。
