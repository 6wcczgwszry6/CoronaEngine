# Agent 任务约束循环：R3 与三职能协同版

更新时间：2026-07-18
状态：当前权威执行规约
适用范围：所有参与 CoronaEngine R3 Runtime 与三职能 Agent 协作层建设的 AI / Agent / Codex

> 当前推进目标和红黄绿标准以 `plan/R3稳定门禁与三职能Agent双轨推进计划.md` 为准。
> 已执行任务的历史编号和验收证据以 `R3-min推进记录.md` 为准。
> 子计划不得覆盖完整 R3 的 RuntimeGuard、EngineWriteGate、真实事实和 Mock 不可执行约束。
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
工作块 / 任务编号：W?.? / B?.?
任务目标：
所属轨道：Runtime A / Collaboration B / Black-box Slice
Full R3 Gate：red / yellow / green / unavailable
Single-player Demo Gate：red / yellow / green / unavailable
Integration status：not_ready / code_complete / integration_ready / single_player_verified
当前任务状态：ready / in_progress / blocked
前置依赖及其状态：
推进维度或交付物：
涉及主链：
风险等级：low / medium / high
不做范围：
最小完成证据：
```

每轮只能选择一个主要 Gate 维度或一个轨道 B 交付物。发现相邻问题时记录，不顺手扩成大重构。

任务定义、依赖和完成标准以权威总计划的 `W0-W6` 及当前子计划的 `B0-B7` 为准。`B?.?` 是经权威子计划批准的编号，不属于执行者自行创建的平行体系；禁止再建立第三套编号。

---

## 3. 任务选择算法

每轮开始时按确定顺序选题：

1. 读取最新 `R3GateReport`。
2. 读取 `R3-min推进记录.md` 顶部当前执行锚点及最近 2-3 条任务记录。
3. 找出前置依赖已满足、Gate 允许且状态为 `ready` 的最早任务编号。
4. 当前处于黑盒期时，严格按 `B0.1 干净门禁 -> B0.2 版本登记 -> B0.3 阻断诊断 -> B0.4 Walking Skeleton` 串行推进，再选择 B1-B5 的最早 ready 任务。
5. Full R3 Red 存在 Runtime 权限、身份或事实硬阻断时，不得用子计划绕过；允许继续不依赖实机事实的 B0-B4。
6. 若正在等待稳定 Engine SHA 或用户执行 F5，可选择独立的 B1-B5/W3-W4 任务；相关 Engine 任务只能标记 `code_complete` 或 `integration_ready`，不能标记 `verified`。
7. Full R3 Yellow 状态优先提升 readiness/一致性；完整 R3 的 EntityBindingPlan 继续受总计划约束。
8. `single_player_demo` Gate Green 只允许子计划声明的本地单人 binding/action/preview，不得解锁多人或声明 Full R3 Green。
9. 只有 `W2.6=Green` 且 W4 完成，才能选择完整 R3 的 W5；单人子计划执行按 B5-B7 的独立依赖判断。
10. 默认一轮只选择一个任务编号；不可分割的前置修复必须在回写中明确列出。

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
- schema version 是否来自统一 `services/schema_versions.py`，而不是目标模块私自声明。
- 未实现节点是否返回完整 BlockedResult，且每个缺失要求都是结构化 MissingRequirement，不需要解析自然语言才能确定依赖和责任域。
- 事实源属于 Runtime、Engine、Sync 还是协作层。
- 修改是否跨 Python / C++ 边界。
- 当前 GateReport 的失败维度是否真的由该代码负责。

禁止凭聊天记忆、旧日志或旧计划章节直接修改当前代码。

---

## 5. Gate 驱动的执行边界

### 黑盒期共同规则

允许：

- Walking Skeleton、Adapter Protocol、schema、Test Double、兼容 fixture 和 Demo Runner。
- ProjectGatePreflight 对 Artifact、版本、依赖和 capability 做非执行校验。
- ActionProposal wire shape、Mock/legacy/过期 Snapshot 的拒绝路径测试。

禁止：

- ProjectGatePreflight 跳过 Runtime Gate 或返回可执行成功。
- 使用 Test Double、Mock Snapshot 或 legacy Snapshot 构造成功 ActionProposal。
- 在稳定 SHA 和实机 Gate 证据到达前注册新的生产写入口。

### Red

允许：

- 修复 Runtime、Engine fact、Finalizer、Snapshot 和多人身份一致性。
- 轨道 B 的 contracts、ProjectState、ArtifactRegistry、TaskGraph 和纯单元测试。
- 三职能 Agent 生成不依赖 Snapshot 的非执行型 Artifact。

禁止：

- 运行中的 Agent 接入真实或 Mock Snapshot。
- 完整 ProjectGate、可执行 ActionProposal 和生产 EntityBindingPlan。
- 任何上层 Agent 场景写入。

Red 状态可执行 ProjectGatePreflight，但结果必须为 `pending_runtime_verification` 或 `blocked`。

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

### Single-player Demo Green

只有 `single_player_demo` profile 按动态 GameplayEntitySlot 要求通过时，才允许：

- `single_player_entity_binding`。
- `single_player_local_action`。
- `single_player_preview`。

该状态必须与 Full R3 Gate 分开记录，不得解锁 multiplayer capability。

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
ArtifactRegistry、TaskGraph、Runtime 只读门禁、Snapshot schema、Registry 聚合、StatePatch schema、Engine/Frontend Adapter Protocol、Demo Runner
```

验证：模块测试 + 一项跨模块契约测试；触及 RuntimeState 时增加现有 Runtime 聚焦回归。

### High

```text
RuntimeGuard、ToolCallGraph executor、EngineWriteGate、C++ binding、LANChat 权威端、多人同步、Finalizer、生产入口
```

实施前必须写明回滚点；验证包含聚焦测试和对应 F5，未 F5 一律标记 `[待 F5/实机验证]`。

---

## 8. 最小实现原则

- 先建立可运行的端到端 Walking Skeleton，再沿骨架补充模块细节；不采用逐模块纵深完成后才集成的顺序。
- Walking Skeleton 必须真实连接入口、Artifact、Preflight、capability 结果、DemoResult 和 ProgressEvent。
- 未实现能力必须返回 `unavailable/blocked/pending_runtime_verification`，禁止 `pass`、空字典或固定成功占位。
- 框架先行只覆盖本周垂直切片，不为未来 Agent、多人、战斗或脚本预建空壳。
- BlockedResult 必须具有稳定 error code、结构化 MissingRequirement、owner domain、retryable、next action 和 evidence refs；缺少诊断字段不算完成骨架节点。
- MissingRequirement 必须包含稳定 requirement_id、owner_domain 和 description；填充 AI 只能使用 requirement_id/owner_domain 做依赖选择，不得解析 description 判断路由。
- 每次提交只关闭一个可验证断点。
- 默认每轮只推进一个任务编号；同一工作块内也不得批量标记完成。
- 优先复用现有 Snapshot、Consistency Audit、Registry 和 Evidence，不建立第二事实源。
- 先建立替代闭环，再隐藏或拆除旧路径。
- 轨道 B 模块不得导入 LANChat Worker 或 AgentRuntime 内部实现。
- Mock fixture 与真实 Snapshot 使用同一 Schema Validator，但 Mock 不具备执行资格。
- 不为森林营地、卧室或单句测试写特例。
- 不因边角失败扩展 Replay、VLM、UI 或 Provider。

### 架构 AI 阶段

- 只执行 B0.1-B0.4，完成接口、最小编排、统一诊断、端到端测试、SkeletonContractManifest 和 contract hash。
- 不只创建空接口；现有 Agent、Artifact 和 Registry 必须通过真实最小调用进入骨架。
- 不实现真实 Engine 业务逻辑、玩法执行或生产写入口。
- 完成后输出 SkeletonContractManifest、SkeletonStatusReport 和节点状态表，冻结公共接口、节点 ID 与调用顺序。

### 填充 AI 阶段

- 架构 AI 完成交接后才可开始，两个阶段不得并发修改骨架。
- 每轮从状态表选择优先级最高且依赖满足的 blocked 节点。
- 开始前校验交接 contract hash 并读取该节点 BlockedResult；结束后更新对应节点状态。
- 不得修改冻结的公共接口、schema version、节点 ID 或数据流顺序。
- 发现接口不足时提交 InterfaceChangeRequest，节点标为 `blocked/interface_change_required`，不得建立第二接口或兼容旁路。
- 每个填充节点必须验证正常路径和至少一种失败路径。
- 节点需要 F5 后，只允许继续与该实机事实无依赖的节点；消费该事实的下游保持 blocked。

### 接口变更交接

填充 AI 的 InterfaceChangeRequest 必须包含：

```text
request_id / node_id / detected_by_task_id
current_contract_version / current_contract_hash
reason_code / required_change
affected_interfaces / blocked_dependents / evidence_refs
```

只有架构 AI 可以处理该请求，并输出：

```text
InterfaceChangeDecision
decision: accepted | rejected | no_contract_change
reason / changed_interfaces
new_contract_version / new_contract_hash
affected_nodes / required_revalidation / evidence_refs
```

接受公共接口变更时必须提升 `SKELETON_CONTRACT_VERSION`、重新生成 Manifest/hash、重跑 B0.4，并把旧 hash 下游节点标记 stale。填充 AI 在新交接包形成前不得恢复。

---

## 9. 测试预算

### 文档与纯契约

- 检查路径、引用和 schema 示例一致性。
- Python 契约运行 syntax compile 和直接单元测试。
- 不运行 F5，不运行总门禁。

### B0 干净门禁与 Skeleton

- Track B 81 项与 R3 readiness 21 项必须在同一测试进程中通过，不允许保留已知 `sys.modules` 噪声。
- 版本常量检查必须证明 Python domain 只从 `schema_versions.py` import。
- BlockedResult Validator 必须拒绝缺少 owner、MissingRequirement 或 next action 的阻断结果。
- MissingRequirement Validator 必须拒绝不匹配 `^[a-z][a-z0-9_.-]{2,63}$` 的 requirement_id、未知 owner_domain 和空 description。
- Skeleton 测试必须断言每个节点的 blocker code、owner domain 和 evidence refs。
- contract hash 必须来自规范化 SkeletonContractManifest，不得来自 SkeletonStatusReport 或原始文件字节。
- 公共签名、DTO、枚举、schema version、节点/边变化必须改变 hash；注释、格式化和私有实现变化不得改变 hash。
- 相同 fixture 必须产生相同 SkeletonStatusReport、Manifest 和 contract hash。

### ArtifactRegistry / TaskGraph

- 模块单元测试。
- 一项跨模块测试，验证版本更新导致依赖 Artifact 进入 stale。
- 不运行与 Runtime 无关的历史测试。

### Runtime 只读 / Gate

- 聚焦 Runtime 测试。
- 必须验证调用前后 RuntimeState version、OperationLog cursor、ToolGraph 和 PlanPatch 数量不变。
- 必须验证红黄绿边界和确定性。

### 黑盒 Adapter / Test Double / Runner

- 验证分域 schema version、old/new fixture 归一化和 capability mismatch。
- Test Double 覆盖 normal、late-ready、partial、failed、duplicate 和 version conflict。
- Demo Runner 只允许产出非执行结果；Mock/legacy 必须被硬拒绝。
- 默认不运行 F5，不运行无关 Engine 全量构建。

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
执行角色：架构 AI / 填充 AI
任务状态：code_complete / verified / blocked
里程碑状态：not_ready / integration_ready / single_player_verified / full_r3_verified
完成断点：
修改范围：
验证证据：
Full R3 Gate 变化：无 / red->yellow / yellow->green / 降级
Single-player Demo Gate 变化：无 / red->yellow / yellow->green / 降级
未验证项：
风险遗留：
Skeleton contract version/hash：
当前节点状态：
Interface change request / decision：
下一批可选任务 ID：
```

代码事实以测试、RuntimeState、OperationLog 和 F5 证据为准。计划变化写入权威计划；阶段进度写入 `R3-min推进记录.md`；微小修改只保留在提交记录中，不向权威计划追加长篇 Progress Update。

状态规则：

- 自动测试通过但要求 F5 的任务，只能标记 `code_complete`。
- 契约、Adapter、Test Double、Runner 和迁移清单完成时可标记里程碑 `integration_ready`，但任务不得标记实机 verified。
- 两个独立 Session 的单人 Demo 通过后才能标记 `single_player_verified`。
- `single_player_verified` 不得自动提升为 `full_r3_verified`。
- B0.4 只有在公共接口、节点 ID、SkeletonContractManifest、contract hash 和完整节点状态表落盘后才能标记 code_complete。
- 填充任务若需要改变公共接口，必须提交 InterfaceChangeRequest 并标记 blocked，不得标记 code_complete。
- F5 证据包完整并达到任务标准，才可标记 `verified`。
- `blocked` 必须写明唯一直接阻断、已验证事实和解除条件。
- Gate 未变化时写“无”，不得为了展示进度强行升级。
- 下一批任务只能从依赖已满足的任务中选择，不能写笼统的“继续优化”。

`R3-min推进记录.md` 每次只追加一条紧凑记录：

```text
时间 / commit：
任务 ID / 状态：
执行角色：
里程碑状态：
Full R3 Gate before / after：
Single-player Demo Gate before / after：
证据：
Skeleton 节点 / contract hash：
Interface change request / decision：
待 F5/阻断：
下一批可选任务：
```

---

## 12. AI 交接与上下文压缩

当任务跨会话、交给另一个 AI 或上下文即将压缩时，交接内容只保留：

```text
当前权威文档路径
当前权威子计划路径
当前 Full R3 / Single-player GateReport 路径与版本
当前 AI / Engine / Frontend 基准 SHA
当前 capability manifest version
当前 Skeleton contract version/hash
当前执行角色：架构 AI / 填充 AI
当前 Skeleton 节点、owner 和 BlockedResult
未决 InterfaceChangeRequest 与最新 InterfaceChangeDecision
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
先连通可阻断的端到端骨架，再沿骨架填充细节；大胆并行纯契约，严格隔离真实执行，用最小必要测试证明，不用测试数量代替场景事实。
```
