# Agent 任务约束循环：R3 与三职能协同版

更新时间：2026-07-14
状态：当前权威执行规约
适用范围：所有参与 CoronaEngine R3 Runtime 与三职能 Agent 协作层建设的 AI / Agent / Codex

> 当前推进目标和红黄绿标准以 `R3稳定门禁与三职能Agent双轨推进计划.md` 为准。
> 本文只规定每轮任务如何选择、实施、验证和停手，不重复维护项目计划。

---

## 1. 每轮闭环

每轮任务必须按以下顺序执行：

```text
目标锚定
-> 读取当前 GateReport
-> CodeGraph 核实事实与影响面
-> 选择轨道和一个验收断点
-> 风险判定
-> 最小实现
-> 分级验证
-> 诚实回写
```

禁止跳过事实核实直接修改核心链路，也禁止用扩测试、扩报告代替真实断点修复。

---

## 2. 任务开始模板

开始实施前只需明确以下内容：

```text
工作块 / 任务编号：W?.?
任务目标：
所属轨道：A / B
当前 Gate：red / yellow / green / unavailable
当前任务状态：ready / in_progress / blocked
前置依赖及其状态：
推进维度或交付物：
涉及主链：
风险等级：low / medium / high
不做范围：
最小完成证据：
```

每轮只能选择一个主要 Gate 维度或一个轨道 B 交付物。发现相邻问题时记录，不顺手扩成大重构。

任务定义、依赖和完成标准以权威计划的 `W0-W6` 为准。执行者不得自行新建平行编号体系。

---

## 3. 任务选择算法

每轮开始时按确定顺序选题：

1. 读取最新 `R3GateReport`。
2. 读取 `R3-min推进记录.md` 中最近的任务状态和可选下一项。
3. 找出前置依赖已满足、Gate 允许且状态为 `ready` 的最早任务编号。
4. Red 状态存在 Runtime 硬阻断时，优先选择对应的 W1/W2，不以轨道 B 工作回避底座问题。
5. 若正在等待用户执行 F5，可选择一个独立的 W3/W4 任务；相关 Runtime 任务只能标记 `code_complete`，不能标记 `verified`。
6. Yellow 状态优先提升 readiness/一致性；W4 只能只读真实 Snapshot，不得创建 EntityBindingPlan。
7. 只有 `W2.6=Green` 且 W4 完成，才能选择 W5。
8. 默认一轮只选择一个任务编号；不可分割的前置修复必须在回写中明确列出。

遇到多个同级任务时，依次比较：

```text
是否解除 Red 硬阻断
-> 是否被更多后续任务依赖
-> 是否已有明确失败证据
-> 修改面是否更小且可验证
-> 任务编号顺序
```

不得因为某个任务容易、测试多或输出显眼，就绕过依赖选择它。

---

## 4. 事实核实规则

查代码优先级：

```text
CodeGraph MCP / CLI
-> 精确文件搜索
-> 目标文件阅读
-> 必要的最小测试或日志核对
```

必须核实：

- 当前分支、工作区和用户未提交改动。
- 目标符号、调用方、被调用方和 blast radius。
- 是否已有等价实现、Validator 或历史修复。
- 事实源属于 Runtime、Engine、Sync 还是协作层。
- 修改是否跨 Python / C++ 边界。
- 当前 GateReport 的失败维度是否真的由该代码负责。

禁止凭聊天记忆、旧日志或旧计划章节直接修改当前代码。

---

## 5. Gate 驱动的执行边界

### Red

允许：

- 修复 Runtime、Engine fact、Finalizer、Snapshot 和多人身份一致性。
- 轨道 B 的 contracts、ProjectState、ArtifactRegistry、TaskGraph 和纯单元测试。
- 三职能 Agent 生成不依赖 Snapshot 的非执行型 Artifact。

禁止：

- 运行中的 Agent 接入真实或 Mock Snapshot。
- EntityBindingPlan、CollaborationCoordinator、ProjectGate、ActionProposal。
- 任何上层 Agent 场景写入。

### Yellow

在 Red 允许项基础上，可开放：

- 三职能 Agent 只读真实 Snapshot。
- 策划、美术 Artifact 和 GameplayLogicPlan。
- Readiness 与缺失事实分析。

仍禁止 EntityBindingPlan 和上层 Runtime 写入。

### Green

允许在 ProjectGate 通过后：

- EntityBindingPlan。
- CollaborationCoordinator。
- ActionProposal -> PlanPatch -> ToolCallGraph。

任何 Green 权限都不能绕过 RuntimeGuard、EngineWriteGate、ToolResult 和 StatePatch。

---

## 6. 架构硬约束

1. Agent 不直接写 Engine。
2. Agent 不直接修改 RuntimeState。
3. ToolCallGraph 是唯一执行编排。
4. RuntimeGuard 是唯一场景写权限判断。
5. ToolResult 只能提交 StatePatch。
6. Runtime 报告只能读取 RuntimeState、OperationLog 和真实 Engine 事实。
7. 三职能 Agent 只能读取 SceneWorldSnapshot，不读取 Engine 对象或聊天历史。
8. ProjectGate 不替代 RuntimeGuard，Runtime 门禁不校验 Artifact。
9. Mock Artifact 必须在 ActionProposal 构造阶段被硬拒绝。
10. 旧 SceneComposer / ProgressiveWorkflow 不得恢复为用户入口。

违反任一项时停止实施，重新设计方案，不通过补测试掩盖架构越界。

---

## 7. 风险判定

### Low

```text
文档、强类型契约、纯 Validator、只读 DTO、无副作用查询、测试 fixture
```

验证：相关单元测试；Python 变更增加 syntax compile。

### Medium

```text
ArtifactRegistry、TaskGraph、Runtime 只读门禁、Snapshot schema、Registry 聚合、StatePatch schema
```

验证：模块测试 + 一项跨模块契约测试；触及 RuntimeState 时增加现有 Runtime 聚焦回归。

### High

```text
RuntimeGuard、ToolCallGraph executor、EngineWriteGate、C++ binding、LANChat 权威端、多人同步、Finalizer、生产入口
```

实施前必须写明回滚点；验证包含聚焦测试和对应 F5，未 F5 一律标记 `[待 F5/实机验证]`。

---

## 8. 最小实现原则

- 每次提交只关闭一个可验证断点。
- 默认每轮只推进一个任务编号；同一工作块内也不得批量标记完成。
- 优先复用现有 Snapshot、Consistency Audit、Registry 和 Evidence，不建立第二事实源。
- 先建立替代闭环，再隐藏或拆除旧路径。
- 轨道 B 模块不得导入 LANChat Worker 或 AgentRuntime 内部实现。
- Mock fixture 与真实 Snapshot 使用同一 Schema Validator，但 Mock 不具备执行资格。
- 不为森林营地、卧室或单句测试写特例。
- 不因边角失败扩展 Replay、VLM、UI 或 Provider。

---

## 9. 测试预算

### 文档与纯契约

- 检查路径、引用和 schema 示例一致性。
- Python 契约运行 syntax compile 和直接单元测试。
- 不运行 F5，不运行总门禁。

### ArtifactRegistry / TaskGraph

- 模块单元测试。
- 一项跨模块测试，验证版本更新导致依赖 Artifact 进入 stale。
- 不运行与 Runtime 无关的历史测试。

### Runtime 只读 / Gate

- 聚焦 Runtime 测试。
- 必须验证调用前后 RuntimeState version、OperationLog cursor、ToolGraph 和 PlanPatch 数量不变。
- 必须验证红黄绿边界和确定性。

### Engine / Sync / 写链路

- 本轮直接相关测试。
- 必要 syntax compile。
- 对应 F5 / 多人实机验证。

### 总门禁

`verify_ultimate_plan.py` 只在以下时机运行：

```text
里程碑收口
触及入口 / RuntimeGuard / ToolCallGraph / RuntimeState / StatePatch / OperationLog
提交前需要证明主链未回归
F5 前
```

同一轮默认最多运行一次；只有失败修复后才允许重跑。总门禁运行期间不得修改文件。

---

## 10. 停手与重新诊断条件

出现任一情况必须停止当前实现：

- 同一技术假设连续失败两次。
- 发现 RuntimeGuard 绕过或 ToolResult 直接改状态。
- Snapshot Fingerprint 或 entity_id 出现无法解释的漂移。
- 当前文件存在用户未提交改动，且无法无冲突地保留。
- 真实 Engine 结果与 RuntimeState 相互矛盾。
- 通过测试需要恢复旧 Workflow 主控或写场景特例。
- 任务已经越出当前 Gate 允许能力。
- 当前任务前置依赖并未真正达到 `verified`，却需要依赖其实机结论。

停手后只输出：已验证事实、失败假设、责任域和下一步最小诊断，不继续试探性堆补丁。

---

## 11. 完成、状态与回写

任务结束只需回写：

```text
工作块 / 任务编号：
任务状态：code_complete / verified / blocked
完成断点：
修改范围：
验证证据：
Gate 变化：无 / red->yellow / yellow->green / 降级
未验证项：
风险遗留：
下一批可选任务 ID：
```

代码事实以测试、RuntimeState、OperationLog 和 F5 证据为准。计划变化写入权威计划；阶段进度写入 `R3-min推进记录.md`；微小修改只保留在提交记录中，不向权威计划追加长篇 Progress Update。

状态规则：

- 自动测试通过但要求 F5 的任务，只能标记 `code_complete`。
- F5 证据包完整并达到任务标准，才可标记 `verified`。
- `blocked` 必须写明唯一直接阻断、已验证事实和解除条件。
- Gate 未变化时写“无”，不得为了展示进度强行升级。
- 下一批任务只能从依赖已满足的任务中选择，不能写笼统的“继续优化”。

`R3-min推进记录.md` 每次只追加一条紧凑记录：

```text
时间 / commit：
任务 ID / 状态：
Gate before / after：
证据：
待 F5/阻断：
下一批可选任务：
```

---

## 12. AI 交接与上下文压缩

当任务跨会话、交给另一个 AI 或上下文即将压缩时，交接内容只保留：

```text
当前权威文档路径
当前 GateReport 路径/版本
当前任务 ID 和状态
已修改但未提交文件
已运行测试及结果
尚未运行的 F5/实机验证
唯一直接阻断
下一批可选任务 ID
```

禁止用长篇聊天回顾代替任务状态。新执行者必须重新核实当前分支、工作区和目标符号，不得把交接摘要当作最新代码事实。

---

## 13. 一句话约束

```text
大胆并行纯契约，严格隔离真实执行；每轮只推进一个可验证断点，用最小必要测试证明，不用测试数量代替场景事实。
```
