# Codex 攻坚修改记录

> 维护规则：每次关键接线、语义修正、测试结果都记录到本文档，便于后续 AI 接手时快速判断当前状态。

## 执行计划（置顶）

### 总目标

本轮不是做“一句话一次性 AI 生成场景”，而是实现：

> 用户、AI 助手、Role Agent、GM/静默监听 Agent 共同维护同一个 SceneState，并在生成过程中持续磋商、介入、修正和确认。

UbiComp 叙事重点：

- 人机交互：用户可在生成过程中持续介入，而不是等待最终结果。
- 开放场景生成：任意需求拆成 `AssetPool + Zone/Anchor + SceneLayout`，不依赖固定模板。
- 通用混合环境：地形外皮由主建筑/场景语义驱动，建筑尺度决定平台和地形范围，避免只服务草原蒙古包特例。
- 协作治理：多人不同时乱写引擎，由 GM 整理意图、房主确认、host 单写者执行。
- 可靠性：放弃物理主路径，用 `AABB + VLM` 分层保证穿模、摆放和语义一致性。

### 全局原则

```text
SceneState 是唯一事实源
Prompt 只是 SceneState 的投影
生成可以并行
规划可以异步
引擎写入必须串行
用户介入不是打断流程，而是更新 SceneState
GM 不是替用户拍板，而是整理冲突、提出方案、请求确认
```

AI 执行铁律：

- 不允许 LLM/VLM/Role Agent 直接操作引擎。
- 所有引擎写入必须经过 `EngineWriteGate`，多人阶段经过 host single-writer。
- 不维护历史 prompt 作为状态；布局、审查、重排时从 SceneState 懒重建 prompt。
- 不把 `touched_by_user=True` 解释成永久锁死，必须结合 `intervention_round` 和 AABB 合理性。

### Day 1：单人优先

1. 元数据与写入收口
   - 复用 `SceneLayout/LayoutInstance`。
   - 保留 `intervention_round`、`protection_level`、`lock_level`。
   - `SceneSession` 持有 `current_round/pending_tasks/intervention_queue/operation_log/silent_gm_state`。
   - `EngineWriteGate` 收口 import/remove/transform/material/screenshot/settle。

2. 渐进生成与用户介入
   - 渐进路径默认启用，旧路径仅作为 `USE_PROGRESSIVE_COMPOSE=0` 回退。
   - 新增/使用 incremental import，只 add，不 clear。
   - phase 顺序：`GROUND -> SHELL -> INTERIOR -> BOUNDARY -> OBJECTS -> DECORATION`。
   - 每个 phase 末采样 viewport，scene-diff 捕获用户 move/add/delete。
   - Agent 导入后必须更新 diff baseline，避免误判为用户新增。

3. 保护策略
   - 最近 1-2 轮用户明确操作为 `HARD`，FinalReview 和 Agent 不自动覆盖。
   - 较早且合理的用户操作为 `SOFT`，尽量保留，冲突时请求确认。
   - 较早且不合理的用户操作为 `NONE`，可进入重排候选，但必须报告。
   - Agent 与用户冲突时 Agent 让位。

4. AABB + VLM
   - AABB 是内回路，检查 overlap、block doorway、out of zone、floating、hard user moved。
   - VLM 是外回路，只产 advisory，不阻塞主链路。
   - VLM 截图必须 timeout，失败 skip。

5. 通用混合环境地形/建筑链路
   - `ZoneTree` 的 terrain zone 必须携带或推导 `TerrainProfile`。
   - `TerrainProfile` 包括 `type/material/scatter/style_tags`，由主建筑/场景语义驱动。
   - 主建筑 shell/box 的 footprint 决定 terrain 中心平台和地形范围。
   - terrain 材质和散布层不得写死草地；蒙古包、木屋、帐篷、沙漠建筑、山寨营地等都走同一套 profile 映射。
   - F5 验收重点：主建筑不埋入/悬空于地形，门洞 clearance 不被物体挡住。

6. Role Agent
   - 内置长者、小女孩、山贼、学者、商人。
   - 支持用户自定义 persona。
   - 本阶段只影响聊天风格和轻量偏好，不进入深层 decompose。
   - Role Agent 只输出 proposal，不直接写引擎。

### Day 2：多人推进

1. LANChat host single-writer
   - guest 操作/指令发给 host。
   - host 通过 `EngineWriteGate` 执行。
   - 执行后广播 SceneDelta/Actor sync。

2. GM/静默监听
   - 基于 `SummaryService.monitor()` 输出 `DiscussionState`。
   - 结构化字段包括 pending intents、conflicts、constraints、required confirmations。
   - GM 负责语义冲突和顺序建议，不负责底层 race。

3. 权限与确认
   - 小操作自动执行。
   - 中/大操作 GM 提案 + 房主确认。
   - 投票只作为咨询展示，不作为 demo 主裁决路径。
   - guest 请求由 host 执行，但必须保留真实 `source_user_id`。

4. 多人冲突
   - 同一 actor 操作冲突：Actor version / lock 后续补齐。
   - 用户 vs Agent：用户优先，Agent replan。
   - 语义冲突：GM 提案并广播，房主确认。

### 当前成功标准

今天必须达到：

- 单人渐进生成默认可走。
- 用户中途介入能进入 SceneState 和 OperationLog。
- 最近用户操作不会被后续 batch 静默覆盖。
- AABB 能防主要穿模/挡门/越界。
- 地形能根据主建筑/场景语义生成对应 profile、材质和散布层，并为主建筑保留平台。
- VLM 可接入且不会卡死主链路。
- Role Agent 可列出模板并注册自定义 persona。
- 静默监听能总结 pending/conflict/confirmation。

明天必须达到：

- LANChat 内模型和操作能同传。
- host 是唯一引擎写入者。
- GM 能识别语义冲突并提案。
- 房主能确认关键操作。
- 多人 provenance 不丢。

### 禁止项

```text
不要恢复物理 settlement 作为主路径
不要让 VLM 阻塞主链路
不要做完整 CRDT
不要做复杂投票裁决
不要让 Role Agent 直接写引擎
不要让 prompt 成为事实源
不要静默覆盖用户物体
不要对每次用户小编辑都调用 LLM/VLM
不要在渐进导入里复用清场式 import_to_engine_node
不要对根目录 E:\corona 建 CodeGraph 全仓索引
```

## 当前推进汇报

- 已完成单人主链路关键接线：渐进路径默认开启、incremental import 接入、scene-diff baseline 修复、OperationLog 落账、FinalReview 三分桶。
- 已完成可靠性底座：AABB 内回路测试通过，VLM 外回路 timeout/skip 测试通过。
- 已完成 Role Agent 最小可用入口：模板列表、自定义 role 注册、persona 注入聊天 system prompt。
- 已完成多人/GM 最小底座：`SummaryService.monitor()` 输出结构化讨论状态，`ChatServer` 能广播 pending intents / confirmation，`GMArbiter` 已接入 @agent 请求的轻量冲突提案路径。
- 已完成通用混合环境增强：`TerrainProfile` 支持主建筑/场景语义驱动的地形类型、材质、散布层；离线测试覆盖蒙古包/木屋/沙漠等 profile 映射。
- 尚未完成 F5 引擎实机验收、前端房主确认 UI、Actor version/lock、SceneDelta 标准化广播。

## 下一步推进

1. F5 验收单人渐进生成
   - 验证真实 `import_model` envelope 是否被 `parse_import_result` 正确解析。
   - 验证第二批导入不清第一批。
   - 验证用户中途移动后不会被后续 batch 误覆盖。
   - 验证地形 profile 材质/散布层是否在引擎中正确显示。
   - 验证 shell/box 主建筑与 terrain 平台贴合，不悬空、不埋地、不穿模。

2. 补多人 host single-writer 的 SceneDelta
   - 定义最小事件：`ActorAdded/ActorMoved/ActorDeleted/GMProposal/HostConfirmationRequired`。
   - host 执行后广播结果，guest 只接受 confirmed delta。

3. 补房主确认闭环
   - 当前 GM 是“广播提案 + 默认确认”。
   - 下一步要让房主能确认/拒绝/修改顺序。

4. 补 Actor version/lock
   - 每个 actor 维护 `version/owner_user_id/last_touched_by/lock_owner/lock_expire_at`。
   - 后到操作 version 不匹配时进入冲突提示。

5. 继续维护本文档
   - 每轮关键接线、验收结果、风险和下一步都追加到下方日期记录。

## 2026-06-16

### 目标

- 落地“磋商式开放场景生成与多人/多 Agent 协作”方案的两天冲刺主链路。
- 优先保证单人渐进生成、用户介入保护、AABB/VLM 分层审查、Role Agent 注入。
- 继续推进 LANChat 侧 GM/静默监听与 host single-writer 的多人简化闭环。

### 当前接手事实

- `SceneLayout/LayoutInstance` 已有 `intervention_round` 与近因加权 `protection_level`。
- 已存在初版 `SceneSession`、`SceneDiffTracker`、`EngineWriteGate`、`incremental_import`、`consistency_check`、`vlm_review_loop`、`role_registry`、`gm_arbiter`。
- `SceneComposer.compose()` 已有 `USE_PROGRESSIVE_COMPOSE` 环境变量开关，但默认仍走旧的一次性路径。
- 需要优先修复渐进路径接线问题，避免“看似实现、实际跑不通”。

### 修改记录

- 初始化本文档，后续关键修改持续追加。
- 修复渐进导入接线：
  - `incremental_import` 兼容 `model_path/local_path`，避免模型检索产物无法导入。
  - `scene_composer_progressive` 修正 `helpers` 相对导入，并使用 `parse_import_result` 解析工具 envelope。
  - `SceneSession` 在每批 Agent 导入后调用 `SceneDiffTracker.baseline_add`，避免系统导入被误判为用户新增。
- 补齐运行时账本与写入白名单：
  - `SceneSession` 新增 `OperationLogEntry`、`operation_log`、`pending_tasks`、`silent_gm_state`。
  - 用户介入 drain 时记录 MOVE/ADD/SCALE/ROTATE/COLOR/DELETE 操作账本。
  - `EngineWriteGate` 增加 import/remove/transform/material/settle 语义化入口，降低后续工具绕过 gate 的概率。
- 将 `SceneComposer.compose()` 的渐进式路径默认开启；`USE_PROGRESSIVE_COMPOSE=0` 可显式回退旧路径。
- 调整 `PHASE_ORDER` 为 `GROUND -> SHELL -> INTERIOR -> BOUNDARY -> OBJECTS -> DECORATION`，确保装饰件后置。
- 改造 LANChat 静默监听：
  - `SummaryService` 新增 `DiscussionState` 与 `monitor()`，在保留 `compress()` 兼容的同时输出 pending/conflict/confirmation。
  - `ChatServer._maybe_compress()` 优先使用 monitor 结果，并在聊天室中提示待执行场景意图与房主确认项。
- 接入 GMArbiter 最小实际路径：
  - `ChatServer._dispatch_mentions()` 对 @agent/隐式场景请求做轻量 intent/target 抽取并入 GM 队列。
  - 检测到同物体语义冲突时广播 GM 提案；当前无前端确认 UI，demo 路径使用“广播提案 + 默认确认”。
- 暴露 Role Agent 模板入口：
  - `LANChat.list_role_templates()` 返回内置/自定义 role 模板。
  - `LANChat.register_custom_role()` 注册用户自定义 persona，并返回可用于 `add_agent(persona=key)` 的 role key。

### 自测记录

- 通过：`python editor/plugins/AITool/cai_extensions/data_model/test_protection_tiers.py`
- 通过：`python editor/plugins/AITool/cai_extensions/agent/test_scene_diff.py`
- 通过：`python editor/plugins/AITool/cai_extensions/flows/scene_composition_workflow/test_incremental_import.py`
- 通过：`python editor/plugins/AITool/cai_extensions/agent/test_scene_session.py`
- `python -m py_compile ...` 因 Windows 拒绝写入 `__pycache__` 失败，改用无写入 `ast.parse` 检查；第二轮通过 7 个关键文件。
- GM 最小路径接入后复跑以上 4 个离线测试，全部通过。
- Role 模板入口接入后，`LANChat/main.py` 与 `role_registry.py` 的 `ast.parse` 通过，并复跑 `test_scene_session.py` 通过。
- 通过：`python editor/plugins/AITool/cai_extensions/agent/test_consistency_check.py`
- 通过：`python editor/plugins/AITool/cai_extensions/agent/test_vlm_review_loop.py`
- 最后一轮无写入语法检查通过 12 个关键文件，包括 `SceneSession`、渐进工作流、AABB/VLM、Role、LANChat GM 相关文件。
### 2026-06-16 追加：混合环境地形-建筑装配与穿模硬约束

- 针对通用方案链路新增重点判断：草原蒙古包只是代表 case，本质是 `terrain zone + main shell/box building + indoor/outdoor objects + connector clearance` 的混合环境装配问题。
- 修改 `scene_composer_progressive.reasonable_provider()`：
  - 从 `ZoneTree` 派生 `zone_aabb`，并按 `LayoutInstance.zone_id` 分组做 out-of-zone 检查，避免室外篝火/围栏被室内 zone 误判。
  - 从 `ZoneTree.connectors` 派生 door/passage clearance AABB，接入 `run_furniture_checks(..., door_aabbs=...)`，用于运行时防挡门。
  - 保留全局 overlap/floating 检查，作为防穿模主力。
- 增强 `_distribute_assets_to_phases()`：
  - 室内家具/地毯/桌椅/床默认写入 indoor zone，并把 shell zone 作为 `anchor_ref`。
  - 篝火/木柴/马/围栏等默认写入 outdoor terrain zone。
  - 装饰后置，并优先挂 indoor/shell anchor。
- 新增几何辅助函数：
  - `_infer_primary_zone_ids()`
  - `_collect_zone_aabbs()`
  - `_collect_door_clearance_aabbs()`
  - `_filter_aabbs_by_zone()`
- 新增离线测试 `test_scene_composer_progressive_geometry.py`，覆盖：
  - mixed environment zone 推断；
  - 资产分流写入 `zone_id/anchor_ref`；
  - door clearance AABB 派生；
  - AABB zone 检查按实例 zone 分组。
- 验证结果：
  - `python editor/plugins/AITool/cai_extensions/agent/test_scene_composer_progressive_geometry.py` 通过。
  - `python editor/plugins/AITool/cai_extensions/agent/test_consistency_check.py` 通过。
  - `python editor/plugins/AITool/cai_extensions/agent/test_scene_session.py` 通过。
  - `python editor/plugins/AITool/cai_extensions/flows/scene_composition_workflow/test_incremental_import.py` 通过。
  - `ast.parse` 检查 `scene_composer_progressive.py` 与新测试通过。

风险/下一步：

- 当前地形仍按 flat/platform AABB 处理，尚未对 rolling/noise terrain 做高度采样；F5 前需要确认真实地形 actor 是否能提供可用 bounding box。
- 建筑 shell 与 terrain 的贴地/基座检查还需要进一步接入 infra 层：`check_shell_on_platform()` 已有，但 progressive runtime 尚未把 shell actor AABB 与 terrain/platform y 绑定。
- 下一步优先做 F5 验收：确认真实 `get_bounding_box()`、actor name、shell placement、door clearance 在引擎里是否一致。

### 2026-06-16 追加：地形跟随主建筑风格生成

> **【Claude 校对追加 2026-06-16】本段为历史记录，已被后续「M2 去特殊化 / 半开放 ZoneAspect 注册表」段修正**：`_infer_terrain_style()` 的关键词地形推导已删除，当前代码不再从 shell/name 关键词推导草地/沙地/雪地；地形风格改由 LLM decompose 输出的 `ground_profile` aspect 驱动，缺失时返回中性 `flat/neutral/none`。下文保留原始记录仅供溯源。

- 更新置顶执行计划：新增“通用混合环境地形/建筑链路”，把 `TerrainProfile` 作为 terrain zone 的语义外皮，要求跟随主建筑/场景风格。
- 扩展 `TerrainProfile`：
  - 新增 `material`、`scatter`、`style_tags`。
  - 继续保留 `type/amplitude/frequency/seed` 作为确定性高度场参数。
- 更新 `ZoneTree` 分解 prompt：
  - 要求 terrain zone 输出 `terrain_profile`。
  - 明确示例：蒙古包/游牧/草原、森林木屋、雪地帐篷、沙漠建筑、山寨/营地/岩地。
- 新增本地兜底推导：
  - `_terrain_profile_from_spec()`
  - `_infer_terrain_style()`
  - 即使 LLM 没有输出 `terrain_profile`，也会从 `shell_asset/name` 推导草地、沙地、雪地、林地、岩地等。
- 地形生成接入 profile-driven material/scatter：
  - `_generate_terrain()` 不再写死 `grass.mtl`，改为根据 `profile.material` 写 terrain MTL。
  - 散布层根据 `profile.scatter` 输出草/花、灌木、岩石、雪斑等不同颜色倾向的 billboard 材质。
- 新增离线测试 `test_terrain_style_profile.py`，覆盖：
  - 蒙古包/游牧语义 -> rolling grass flowers。
  - 森林木屋语义 -> noise dirt shrubs。
  - 沙漠语义 -> dunes sand shrubs。
  - LLM 显式 terrain_profile 优先于本地推导。
  - terrain OBJ/MTL 使用 profile-driven material。
- 验证结果：
  - `python editor/plugins/AITool/cai_extensions/agent/test_terrain_style_profile.py` 通过。
  - `python editor/plugins/AITool/cai_extensions/agent/test_scene_composer_progressive_geometry.py` 通过。
  - `ast.parse` 检查 `scene_composer.py`、`zone_tree.py`、`test_terrain_style_profile.py` 通过。

风险/下一步：

- 目前 scatter 几何仍复用 billboard 草簇结构，只通过材质区分灌木/岩石/雪斑；F5 可接受，但后续如有时间应补不同 scatter mesh。
- 真实引擎材质加载是否读取同目录 `mtllib terrain_style.mtl` 仍需 F5 验证。

### 2026-06-16 追加：LANChat C++ Network 合并后的 Agent/GM 重接

- 接受远端架构：LANChat 房间、消息、成员、agent roster、trigger、lock、intent 由 C++ `NetworkSystem` 作为唯一事实源。
- 不恢复旧 Python `chat_server.py / summary_service.py`。
- 新增 AITool 侧 Python 语义层：
  - `services/lanchat_summary_service.py`
  - `services/lanchat_agent_orchestrator.py`
- `LANChatAgentWorker` 从直接调用 role agent 改为调用 `LanChatAgentOrchestrator`：
  - 更新静默监听摘要；
  - 普通请求走 role agent；
  - GM/冲突/大操作请求生成 GM proposal；
  - 房主回复“确认/拒绝/按方案A”消费 pending proposal。
- C++ Python binding 新增最小桥接：
  - `network_lanchat_history_snapshot(limit)`
  - `network_lanchat_agents_snapshot()`
  - `network_send_system_message(sender_id, sender_name, text)`
- `editor/plugins/LANChat/server/gm_arbiter.py` 改为历史兼容 no-op，不再尝试集成已删除的 Python chat server。
- 验证结果：
  - `python editor/plugins/AITool/services/test_lanchat_agent_orchestrator.py` 通过。
  - Python AST 检查 `lanchat_agent_worker.py`、`lanchat_agent_orchestrator.py`、`lanchat_summary_service.py`、`test_lanchat_agent_orchestrator.py` 通过。

风险/下一步：

- C++ binding 尚需完整 C++ 编译验证。
- 前端房主确认当前仍是“聊天室文字确认”v1，后续再补按钮 UI。
- GM proposal 当前只回写聊天消息，尚未真正串到场景工具执行队列；下一步要接 host single-writer 的场景 command。

### 2026-06-16 追加：boundary 从开关升级为参数化边界能力

- 修正 boundary 半通用问题：
  - 之前已做到“无 `boundary` aspect 不生成围栏”，但生成器内部仍只会木栏。
  - 现在 `boundary.params.kind/material/height/style` 都进入 manifest 与 decompose prompt。
- 生成器改造：
  - `_build_fence_obj()` 继续作为环形边界纯函数，但新增 `kind` 和 `height` 参数。
  - 当前支持 `fence`、`wall`、`hedge` 三类基础几何分流。
  - 新增 `_boundary_mtl_text(kind, material)`，支持 `wood/stone/greenery/neutral` 等材质倾向。
  - `_generate_fence()` 改为读取 `boundary` aspect 参数；无 aspect 不调用，有 aspect 才按参数生成 `__terrain_boundary`。
- 测试补充：
  - `test_boundary_params_drive_kind_material_and_height()` 验证 `wall/stone/1.8` 和 `hedge/greenery/0.8` 参数真正影响 OBJ/MTL。
- 自测结果：
  - 通过：`python editor/plugins/AITool/cai_extensions/agent/test_terrain_style_profile.py`
  - 通过：`python editor/plugins/AITool/cai_extensions/agent/test_scene_composer_progressive_geometry.py`
  - 通过：`ast.parse` 检查 3 个关键文件。
  - 通过：`git diff --check`，仅剩 Windows LF/CRLF 提示。

### 2026-06-16 追加：style_context 支撑开放场景动态参数选择

- 将“根据开放式场景主建筑和地形风格动态确定类型/材质/需求”收口到规划层：
  - `Zone` 新增 `style_context: Dict`。
  - decompose prompt 新增 `style_context` schema：`main_building`、`terrain_mood`、`material_palette`、`functional_intent`。
  - prompt 明确要求 LLM/GM 根据用户需求、主建筑、地形气质、时代/文化/功能意图填写 `ground_profile / ground_cover / boundary / entrance / interior_surface` 的 params。
  - 代码不按 `main_building/terrain_mood` 写 if，只保存上下文并执行 aspect params。
- 运行时接线：
  - `_build_zone_tree()` 将 LLM 输出的 `style_context` 存入 `zone.style_context`。
  - `_shell_generation_hint()` 透传 `material_palette` 和 `terrain_mood` 到 shell 模型生成 prompt，增强主建筑与环境风格一致性。
  - 入口样式仍只来自 `entrance` aspect；无 aspect 不猜毡帘/拱门/木门。
- 测试补充：
  - `test_style_context_is_preserved_without_code_inference()` 覆盖火山口观测站场景：
    - `style_context` 被保存；
    - 未声明 `boundary/ground_cover` 时不生成；
    - `lava_flow` 进入 `unsupported`；
    - shell prompt 透传 metal/concrete/volcanic research site；
    - 不出现毡布/布帘类全局默认。
- 自测结果：
  - 通过：`python editor/plugins/AITool/cai_extensions/agent/test_terrain_style_profile.py`
  - 通过：`python editor/plugins/AITool/cai_extensions/agent/test_scene_composer_progressive_geometry.py`
  - 通过：`ast.parse` 检查 3 个关键文件。
  - 通过：`git diff --check`，仅剩 Windows LF/CRLF 提示。

### 2026-06-16 追加：M2 去特殊化 / 半开放 ZoneAspect 注册表

- 按终审放行条件修正上一轮“关键词推导地形”的方向错误：
  - `zone_tree.py` 新增 `ZoneAspect{capability, params}`、`CAPABILITY_MANIFEST`、`GENERATOR_MANIFEST`。
  - manifest 当前覆盖 6 项：`ground_profile`、`ground_cover`、`boundary`、`interior_surface`、`entrance`、`shell_dressing`。
  - `unsupported` 不进入 manifest；未知 capability 统一归入 `ZoneAspect(capability="unsupported")`，记录 requested/reason/params，不崩。
- 删除场景关键词式地形兜底：
  - 移除 `_infer_terrain_style()` 的关键词 if-elif 路线。
  - `_terrain_profile_from_spec()` 只兼容显式 legacy `terrain_profile`；缺失时返回 `flat/neutral/none`。
  - `TerrainProfile` 默认从 `grass/grass` 改为 `neutral/none`，避免 legacy adapter 误生成草覆盖。
- 四个写死点已接入 aspect/manifest：
  - `ground_profile`：terrain 的 type/amplitude/frequency/material/extent_factor 由 aspect params 驱动；`building_extent * 6.0` 改为 `extent_factor`，默认 6.0。
  - `entrance`：删除全局 `_SHELL_ENTRANCE_HINT`，入口提示只来自 `entrance` aspect；无 aspect 时不再默认给蒙古包/帐篷毡帘、拱门等场景身份提示。
  - `interior_surface`：`_generate_interior_floor()` 不再硬编码 `floor_mat="carpet"`；默认 neutral，显式 aspect 可给 stone/wood/carpet。保留 shell footprint 派生和 `INSCRIBE=0.96`，不动几何贴合链路。
  - `ground_cover/boundary`：`ground_cover` 和 `boundary` 都是 opt-in；无 aspect 不调用散布层和 `_generate_fence()`。gate 放在调用边界，生成器本体只保留几何能力。
- 保持 `PHASE_ORDER = ["GROUND", "SHELL", "INTERIOR", "BOUNDARY", "OBJECTS", "DECORATION"]` 不变，未引入装饰提前的回归。
- 测试更新：
  - 替换旧 `test_terrain_style_profile.py`，删除“蒙古包/木屋/沙漠关键词命中 profile”的错误断言。
  - 新增覆盖：manifest shape、PHASE_ORDER 不变、unknown capability -> unsupported、显式 aspect 覆盖 legacy、火山口观测站中性默认、ground_cover/boundary opt-in、entrance/interior_surface aspect 驱动。
- 自测结果：
  - 通过：`python editor/plugins/AITool/cai_extensions/agent/test_terrain_style_profile.py`
  - 通过：`python editor/plugins/AITool/cai_extensions/agent/test_scene_composer_progressive_geometry.py`
  - 通过：`python editor/plugins/AITool/cai_extensions/agent/test_consistency_check.py`
  - 通过：`python editor/plugins/AITool/cai_extensions/agent/test_scene_session.py`
  - 通过：`python editor/plugins/AITool/cai_extensions/flows/scene_composition_workflow/test_incremental_import.py`
  - 通过：`ast.parse` 检查 4 个关键文件。
  - 通过：`git diff --check`，仅剩 Windows LF/CRLF 提示，无 whitespace error。
- 合并门仍然是 F5 实机，不以离线全绿替代（**【Claude 校对追加 2026-06-16】三场景→四场景**，第 4 场景专门验 M2-2 的 ZoneVolumeAnchor/PlatformAnchor，前三场景全有 shell 只走 ShellAnchor 验不到）：
  - 草原蒙古包：看 rolling 起伏、草/花覆盖、围栏、入口、地板贴边和主体建筑贴地。
  - 欧式教堂：看无草、无栅栏、非毡帘、石板/中性地面。
  - 火山口观测站：看不崩、unsupported 正确记录、没有 fallback 草地。
- **纯室外营地/集市/广场（有围栏无可进入建筑）**：LLM 输出 boundary aspect + 无 shell → 边界/地表能落地；这是唯一触发 M2-2 纯室外分支的场景。

### 2026-06-16 追加：M2-2 resolve_zone_anchor 接入当前硬编码生成路径

- 实现 `resolve_zone_anchor(composer, zone, capability)`，三态顺序为：
  - `ShellAnchor`：优先使用 `_shell_aabb` 的真实 shell footprint，保持草原蒙古包等已有 shell 场景路径不回归。
  - `PlatformAnchor`：无 shell footprint 但存在 terrain platform 时，使用 `_platform_radius` 作为边界/地表参照。
  - `ZoneVolumeAnchor`：纯室外无 shell、无 platform 时，使用 zone volume 生成边界参照，解决营地/集市/广场这类无可进入建筑场景无法生成 boundary 的断点。
- `_generate_fence()` 已从直接读取 `_shell_aabb` 改为读取 resolved anchor；无有效 anchor 时才跳过。
- `_run_original_workflow()` 的 boundary 调用点已接入 `resolve_zone_anchor()`，即 M2-2 落在当前 `framework -> shell -> interior_floor -> boundary` 硬编码路径上，不依赖已降级的未来 `dispatch_aspects`。
- 离线测试补充：
  - `test_resolve_zone_anchor_preserves_shell_path()`：验证 shell 场景继续使用真实 footprint。
  - `test_resolve_zone_anchor_supports_platform_and_pure_outdoor_volume()`：验证 platform 与纯室外 zone volume 均可作为 boundary anchor。
- F5 合并门保持四场景：草原蒙古包、欧式教堂、火山口观测站、纯室外营地/集市/广场。第四场景专门验 M2-2 的 Platform/ZoneVolume 分支。

### 2026-06-16 追加：M2-2 hardening / boundary anchor 风险收口

- 修正 ShellAnchor center 风险：
  - `resolve_zone_anchor()` 的 ShellAnchor 不再使用 `zone.volume.center` 作为 boundary 落点。
  - 当前 `_place_shells()` 固定将 shell actor 放在世界原点，因此 ShellAnchor 默认 center 为 `[0, 0, 0]`；未来如支持多建筑 offset，可由 `_shell_aabb` 增加 center 字段承接。
  - 新增测试覆盖 shell zone volume center 非原点时，ShellAnchor center 仍不偏移，避免草原蒙古包围栏被 terrain/zone center 带偏。
- 修正 ZoneVolumeAnchor 半径策略：
  - `resolve_zone_anchor()` 新增 `params` 输入。
  - 纯室外 boundary 优先读取 `boundary.params.radius`；无显式 radius 时使用 `min(width, depth) / 2 - margin`，默认 `margin=1.0m`，并保留最小半径保护。
  - 删除测试中 `ring_radius == 7.0` 的裸常数断言，改为验证默认贴近 zone 内缘和显式 radius 覆盖。
- 收窄 M2-2 真实迁移范围：
  - 本轮 anchor 迁移只覆盖 `boundary/_generate_fence`。
  - `_generate_interior_floor()` 仍只服务 shell zone，继续从 shell footprint 派生；这不是本轮 anchor 迁移对象。
  - ground_cover 散布层仍在 `_generate_terrain()` 内按 terrain volume/platform 计算，未走 `resolve_zone_anchor()`。
- F5 必查新增：
  - 草原蒙古包：围栏必须仍套住蒙古包中心，不能因 zone/terrain center 产生平移。
  - 纯室外营地/集市/广场：围栏相对营地物体位置必须合理，不切穿主体物体，也不能只是在空地中央生成一圈。

### 2026-06-16 追加：M2-3 shape-aware fit Tier 1 / interior floor shape

- `interior_surface.params` 增加 `floor_shape`，并加入 `GENERATOR_MANIFEST["interior_surface"].effective_params`。
- decompose prompt 明确：
  - 圆形/帐篷类内皮可输出 `floor_shape=disc`。
  - 矩形/教堂/房间类内皮可输出 `floor_shape=quad`。
  - 代码不按场景关键词判断，只执行 aspect params。
- 新增 `_select_interior_floor_shape(width, depth, surface_params)`：
  - 显式 `floor_shape=disc|quad` 优先。
  - 无显式 shape 时，只用宽深比做几何兜底：明显长条矩形走 `quad`，接近方形保持 `disc`，以保护蒙古包零回归。
- `_generate_interior_floor()` 改为按 `floor_shape` 选择 `_build_disc_obj()` 或 `_build_floor_obj()`；保留 shell footprint 派生和 `INSCRIBE=0.96`，不改贴合缩放链路。
- 离线测试补充：
  - manifest 记录 `floor_shape`。
  - 显式 `quad/disc` 生效。
  - 宽深比兜底只处理明显长条，近方形默认 disc。
- F5 必查：
  - 草原蒙古包：仍为圆/椭圆地面且贴边。
  - 欧式教堂：需要 decompose 输出 `interior_surface.floor_shape=quad`，F5 看方形/矩形地面是否贴合。
  - 本轮仍是 Tier 1；不规则 footprint / convex hull / 多边形地面留深水项。

### 2026-06-16 追加：M2-4 降级说明与 M2-F5 准备

- M2-4 `dispatch_aspects` phase 分桶派发明确降级为深水项，不阻塞 M2-F5：
  - 当前 `framework -> shell -> interior_floor -> boundary` 硬编码路径已覆盖草原蒙古包、欧式教堂、火山口观测站、纯室外营地四个 F5 场景的必要生成顺序。
  - 后续如果增加新的 capability generator，再做 `dispatch_aspects`，并必须按 `PHASE_ORDER` 分桶派发，不能按 LLM 输出的 aspects 数组顺序执行。
  - `unsupported` 只进入 backlog/report，不进入执行派发。
- 补齐 boundary 参数声明：
  - `GENERATOR_MANIFEST["boundary"].effective_params` 新增 `radius/margin`。
  - decompose prompt 的 `boundary.params` schema 新增 `radius/margin`。
  - 纯室外场景中，LLM/GM 可显式给 `radius` 控制围栏范围；未给时由 `zone size - margin` 推导。
- 当前 M2 离线侧剩余工作：
  - 代码路径已到 M2-F5 门口；不继续堆叠未 F5 验证的生成能力。
  - 下一步应进行四场景 F5，重点核查 decompose JSON 与实机场景一致性。

### 2026-06-16 追加：M2-F5 decompose JSON 快照

- `SceneComposer.decompose_zone_tree()` 在成功构建 `ZoneTree` 后，会自动保存一份 F5 用 JSON 快照。
- 快照位置：
  - 系统临时目录下的 `corona_m2_f5_decompose/<scene_name>_<timestamp>.json`。
  - `compose()` 返回结果新增 `zone_decompose_snapshot`，便于从 F5 结果/日志中直接定位。
- 快照内容：
  - `prompt`：原始用户请求。
  - `raw_zones`：LLM 原始 decompose 输出。
  - `normalized_zones`：经过 `normalize_zone_aspects()` 后的 zone/aspects/volume/style_context。
- 用途：
  - 草原蒙古包：核查 boundary 是否来自 aspect，围栏中心 F5 是否套住 shell。
  - 欧式教堂：核查 `interior_surface.floor_shape=quad` 是否真实输出。
  - 纯室外营地：核查 `boundary.radius/margin` 与 `zone.size` 是否能解释围栏位置。

### 2026-06-16 追加：M2-F5 snapshot 字段检查脚本

- 新增只读脚本 `docs/probes/m2_f5_snapshot_check.py`。
- 用法：
  - `python docs/probes/m2_f5_snapshot_check.py <zone_decompose_snapshot> <scene_kind>`
  - `scene_kind` 可取 `grass_yurt / church / observatory / outdoor_market / auto`。
- 作用：
  - 自动打印 snapshot 内 zone/aspect 概览。
  - 草原蒙古包：检查 rolling grass、ground_cover、boundary、disc floor。
  - 欧式教堂：检查无 ground_cover、无 boundary、`floor_material=stone`、`floor_shape=quad`、无毡帘偏置。
  - 火山口观测站：检查非 grass fallback、unsupported 记录。
  - 纯室外集市：检查无 shell、boundary 存在、radius/margin 是否显式。
- 该脚本只读 snapshot，不触引擎、不改仓库状态；用于 F5 后快速判定 decompose JSON 是否过门。

### 2026-06-16 追加：M-Demo 单人渐进链路可观测性

- `run_progressive_workflow()` 现在把 `SceneSession` 的 phase 进度通过 `progress_events` 返回给上层，而不是只写日志。
- 渐进结果新增：
  - `final_report_text`：`FinalReviewReport.to_user_text()` 的用户可读文案，便于 F5/聊天侧直接展示；
  - `operation_log` / `operation_count`：用户介入、视口 diff、AI 工具介入在 phase 边界落账后的可序列化记录；
  - `round`：当前渐进生成轮次。
- 目的：
  - F5 时可以区分“生成阶段未执行”“用户介入未捕获”“FinalReview 未产出文案”“视觉摆放失败”四类问题；
  - 不改变 M2 生成策略、不新增场景特化逻辑，只补 demo 验收和排障所需的观测出口。
- 离线测试补充：
  - `test_scene_session.py` 新增进度 sink + FinalReview 文案可观测断言。

### 2026-06-16 追加：多人 GM proposal 到 confirmed intent 的最小接线

- `AgentOrchestrationResult` 新增 `action_payload`，保持原有 `text/sender/proposal` 行为兼容。
- GM 提案时结构化保存：
  - `proposal_id`
  - `source_user_id`
  - `target_agent_id`
  - `intent_text`
  - `pending`
  - `conflicts`
  - `requires_host_confirm`
  - `execution=host_single_writer`
- 房主文字确认后：
  - `action_payload.status` 从 `pending_host_confirmation` 变为 `confirmed`；
  - 保留真实 `source_user_id`，不把 guest 请求伪装成房主请求。
- `LANChatAgentWorker` 在 C++ binding 提供 `network_broadcast_intent()` 时，广播 `confirmed_gm_action`，让 C++ NetworkSystem/前端能够看到“已确认、待 host 单写执行”的意图。
- 边界：
  - 本轮仍不直接调用场景工具，不绕过 EngineWriteGate；
  - 还没有完成 `confirmed_gm_action -> EngineWriteGate -> SceneDelta` 的最终执行队列。
- 离线测试补充：
  - `test_lanchat_agent_orchestrator.py` 覆盖 GM proposal payload、房主确认 payload、worker 广播 confirmed GM action。

### 2026-06-16 追加：M-Demo 单人结果回传到聊天侧

- `_handle_scene_compose()` 现在会把 `SceneComposer.compose()` 的新增观测字段展示给用户：
  - `progressive/phases_run`：显示渐进阶段；
  - `progress_events`：显示最近阶段进度；
  - `operation_count`：显示本轮捕获到的用户介入数量；
  - `final_report_text`：显示 FinalReview 用户可读检查结果；
  - `zone_decompose_snapshot`：显示 M2-F5 decompose JSON 快照路径。
- 目的：
  - 单人 M-Demo F5 时，聊天侧可以直接看到渐进主循环、介入捕获、FinalReview 和 decompose snapshot 是否接上；
  - 不需要用户翻日志判断链路是否运行。
- 边界：
  - 本轮只补展示和排障信息，不改变生成、布局或引擎写入策略。

### 2026-06-16 追加：M-Demo VLM 外回路接入渐进结果

- `run_progressive_workflow()` 现在在渐进导入完成后调用 `vlm_review_loop.review_models_async()`。
- 接入方式：
  - 使用已有 `model_reviewer._capture_single_model()` 作为截图函数；
  - 使用已有 `model_reviewer._vlm_review_model()` 作为 VLM 审查函数；
  - 截图经 `EngineWriteGate.screenshot()` 收口；
  - 默认最多审查前 4 个导入 actor，可用 `PROGRESSIVE_VLM_MAX_TARGETS` 调整。
- 返回字段新增：
  - `vlm_review`
  - `vlm_review_text`
  - `vlm_review_skipped`
  - `vlm_review_timed_out`
- 聊天侧展示：
  - `_handle_scene_compose()` 会展示 VLM 外审文案；
  - 若截图/VLM 跳过或超时，会显示跳过数和超时数。
- 边界：
  - VLM 仍是外回路 advisory，不阻塞主生成链路；
  - VLM 不直接修改场景，不覆盖用户物体；
  - 工具缺失、截图失败、VLM 异常均 skip，不影响 M-Demo 主链路。

### 2026-06-16 追加：M-Demo 阶段披露 / 进度条数据

- `SceneSession.progressive_compose()` 新增 `progress_timeline`。
- 每个实际执行 phase 会产生两条结构化进度：
  - `status=start`：阶段开始，包含 `phase / percent / message`；
  - `status=done`：阶段完成，包含 `phase / percent / asset_count / imported_count / message`。
- 百分比按本次实际执行的 phase 数计算，单阶段为 `0 -> 100`，多阶段按阶段边界递增。
- `run_progressive_workflow()` 将 `progress_timeline` 返回给上层。
- `_handle_scene_compose()` 在聊天侧展示当前阶段百分比，同时保留完整 timeline 供前端渲染进度条/阶段列表。
- 目的：
  - 生成过程中分阶段披露状态，降低用户等待焦虑；
  - F5 时可确认渐进生成不是黑盒等待，而是能看到 `GROUND/SHELL/INTERIOR/BOUNDARY/OBJECTS/DECORATION` 等阶段推进。

### 2026-06-16 追加：LANChat 添加 Agent 快速模板入口

- `RoomPanel.vue` 的“添加 AI 助手”弹窗新增快速模板按钮：
  - 长者
  - 小女孩
  - 山贼
  - 学者
  - 商人
- 点击模板会自动填充：
  - `agentForm.name = 模板名`
  - `agentForm.persona = 模板名`
- 添加仍复用已有 `lanchat.addAgent({ name, persona })`，不新增 C++/Python binding。
- 后端 `RoleRegistry.resolve(persona)` 已支持按模板名解析，因此 persona 传“长者/小女孩/山贼”等即可命中内置模板。
- 自定义角色仍保留原 textarea：用户可直接输入自定义 persona 文本作为临时自定义人格。
- 验证：
  - 轻量静态检查确认 `roleTemplates/selectRoleTemplate` 已存在；
  - `npm` 被 PowerShell 执行策略拦截，改用 `npm.cmd` 后发现当前前端依赖环境缺少可执行 `eslint`，因此未跑完整 lint。
