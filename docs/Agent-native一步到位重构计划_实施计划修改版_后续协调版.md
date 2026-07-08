# Agent-native 涓€姝ュ埌浣嶉噸鏋勮鍒掞細Game-ready Scene Runtime 涓庢棫 Workflow 涓绘帶閫€鍦?

鏇存柊鏃堕棿锛?026-06-29


> 淇璇存槑锛氭湰鐗堝湪鍘?Agent-native 鍦烘櫙鐢熸垚閲嶆瀯璁″垝鍩虹涓婏紝琛ュ厖鈥滈€氱敤鍦板舰鍦烘櫙鐢熸垚 Runtime / Game-ready Scene Runtime鈥濈殑瀹炴柦鐩爣銆?
> 绗簩绾︽潫鏂囨。 `Agent浠诲姟绾︽潫寰幆.md` 缁х画浣滀负鎵€鏈?Agent / Codex 浠诲姟鐨勫己绾︽潫瑙勭害銆?
> 褰撳墠闃舵涓嶇洿鎺ュ疄鐜?GameDesignAgent / CombatAgent / StoryAgent / BalanceAgent / ScriptAgent锛岃€屾槸鎶婂満鏅?Runtime 鍋氬埌鍙鍚庣画 AI Game Demo 鐢熸垚绯荤粺娑堣垂銆?

## 0. 褰撳墠瀹炴柦鍙ｅ緞淇锛欶5 鍓嶅啿鍒?+ Game-ready Scene Runtime

### 0.1 褰撳墠椤圭洰瀹氫綅

鏈」鐩綋鍓嶄笉鏄崟鐐光€滄．鏋楄惀鍦扮敓鎴愬櫒鈥濓紝涔熶笉鍙槸浼犵粺 3D 妯″瀷鍦烘櫙鐢熸垚鍣紝鑰屾槸锛?

```text
澶氫汉澶?Agent 鍗忓悓
-> 閫氱敤鍦板舰 / 鍦烘櫙瀹炰綋鐢熸垚
-> Game-ready Scene Runtime
-> 鍚庣画鎵挎帴 AI Game Demo 鐢熸垚
```

鐜伴樁娈电殑鐩存帴鐩爣浠嶆槸 Agent-native 鍦烘櫙鐢熸垚閲嶆瀯锛屼絾鐩爣鍙ｅ緞鍗囩骇涓猴細

```text
鐢熸垚鍙娓告垙閫昏緫娑堣垂鐨勫満鏅疄浣撲笘鐣?
```

涔熷氨鏄锛屽綋鍓嶉樁娈靛繀椤昏 Runtime 浜у嚭鐨勫満鏅笉浠呪€滅湅璧锋潵鏈夌墿浣撯€濓紝杩樿鍏峰锛?

```text
绋冲畾 actor_id
绋冲畾 asset_id / model_ref
璇箟瑙掕壊 semantic_role
瀹炰綋绫诲瀷 entity_type
transform / AABB / grounding 鐘舵€?
interaction_capability
gameplay_tags
terrain / environment / actor / geometry / review / sync 鍒嗗煙鐘舵€?
```

杩欎簺瀛楁鏄悗缁瓥鍒?Agent銆佺▼搴?Agent銆佽摑鍥?/ 绉湪浠ｇ爜鐢熸垚 Agent 鐨勫湴鍩恒€?

### 0.2 褰撳墠绂佹鎵╁ぇ鐨勮寖鍥?

褰撳墠闃舵涓嶈鐩存帴瀹炵幇浠ヤ笅涓婂眰 Agent锛?

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

褰撳墠闃舵涔熶笉瑕佷负浜嗗崟涓?demo 鍐欐妫灄钀ュ湴銆佸笎绡枫€佸皬鏈ㄦ銆佹垬鏂椼€佸墽鎯呫€佹暟鍊兼垨鑴氭湰閫昏緫銆?

姝ｇ‘鍋氭硶鏄細

```text
鐢ㄦ．鏋楄惀鍦伴獙璇侀€氱敤 terrain scene generation vertical slice
鑰屼笉鏄妸绯荤粺鍐欐垚妫灄钀ュ湴涓撶敤閫昏緫
```

### 0.3 F5 鍓嶅啿鍒烘ā寮?

褰撳墠杩涘叆 F5 鍓嶅啿鍒烘ā寮忥細

```text
杩滅宸紓鏆備笉澶勭悊
editor/plugins/AITool/Quasar 鏆備笉澶勭悊
涓嶈缁х画鎵╁ぇ閲忔祴璇曘€侀棬绂佸拰 replay summary
涓嶈涓轰簡杈硅鐢ㄤ緥鎷栨參涓荤嚎
涓昏娴嬭瘯閫氳繃鍗冲彲锛岀壒鍒粏灏忔祴璇曞彲鏍囪鍚庣画澶勭悊
```

鏈樁娈靛彧浼樺厛鎺ㄨ繘鑳界洿鎺ュ府鍔╃湡瀹?vertical slice 鐨勫唴瀹癸細

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
-> RuntimeState / OperationLog 鍙煡璇?
```

### 0.4 褰撳墠 P0 浼樺厛绾?

```text
P0-1锛歟ngine write adapter 鏀跺彛
P0-2锛歵errain / environment / substrate 璇嗗埆涓庤矾鐢?
P0-3锛歠orest / sky / grass / terrain / ground 绛夌幆澧冭瘝涓嶅緱杩涘叆鏅€氭ā鍨嬬敓鎴?
P0-4锛歛ctor import / transform / delete 缁熶竴璧?Runtime adapter
P0-5锛歡rounding / AABB / layout repair 鏈€灏忓彲鐢?
P0-6锛歴cene_entity_registry 鏈€灏忓彲鐢?
P0-7锛歴ync actor snapshot / asset transfer status 鏈€灏忛棴鐜?
P0-8锛歠inal report 鍙 RuntimeState + OperationLog
```

### 0.5 鎵€鏈夌湡瀹炲啓寮曟搸鎿嶄綔蹇呴』璧扮殑閾捐矾

```text
ToolCall
-> RuntimeGuard
-> EngineWriteGate / runtime_cpp_bridge
-> ToolResult
-> StatePatch
-> RuntimeState
-> OperationLog
```

绂佹锛?

```text
缁曡繃 RuntimeGuard
鎶婂畬鏁?SceneComposer / ProgressiveWorkflow 鍖呮垚 legacy big tool
閲嶆柊鏆撮湶鏃?workflow 鐢ㄦ埛鍏ュ彛
鎶?C++ 鎴愬姛缁撴灉浼€犳垚 Python 鎴愬姛
璁?Agent 鐩存帴 import / move / delete actor
璁╄剼鏈?钃濆浘鐢熸垚缁戝畾涓嶇ǔ瀹?actor_id
```

### 0.6 scene_entity_registry 鏈€灏忕粨鏋?

`scene_entity_registry` 鏄悗缁?AI Game Demo 鐨勬壙鎺ュ眰銆傜涓€鐗堣嚦灏戝寘鍚細

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

褰撳墠鍙互鍏堜负绌哄瓧娈垫垨榛樿鍊硷紝浣?schema 鍜?StatePatch 璺緞蹇呴』棰勭暀銆?

### 0.7 鍚庣画 AI Game Demo 鎵╁睍鏂瑰悜

褰撳墠璁″垝鏂囨。鐨勭粓灞€涓嶅啀鍙槸鍦烘櫙鐢熸垚锛岃€屾槸涓轰互涓嬭兘鍔涢鐣欐墿灞曠偣锛?

```text
绛栧垝锛?
- 鍏冲崱
- 鍓ф儏
- 绯荤粺
- 鎴樻枟
- 鏁板€?
- 浠诲姟涓庤儨璐熸潯浠?

缇庢湳 / 鑹烘湳锛?
- 鍦板舰 / 鍦烘櫙 / 鐗╀綋
- 闊抽闊虫晥
- 鐏厜 / 鏉愯川 / 鐗╃悊鍙傛暟
- 澹板厜鍔涜嚜鍔ㄨ皟鏁?
- 椋庢牸涓€鑷存€у鏌?

绋嬪簭锛?
- 钃濆浘鐢熸垚
- 绉湪浠ｇ爜鐢熸垚
- 瑙﹀彂鍣?
- 浜や簰閫昏緫
- 琛屼负鑴氭湰
- UI / 浠诲姟 / 鎴樻枟鑴氭湰
```

浣嗚繖浜涘睘浜庡悗缁樁娈点€傚綋鍓嶅彧鍋氬簳搴ч鐣欙紝涓嶆彁鍓嶅疄鐜颁笂灞?Agent銆?


## 1. 闂鏈川鍒ゆ柇

鏈」鐩綋鍓嶈瑙ｅ喅鐨勪笉鏄€滃啀琛ヤ竴涓洿鑱槑鐨?Agent鈥濓紝涔熶笉鏄户缁湪鏃?workflow 涓婅拷鍔犳洿澶?if/else锛岃€屾槸瑕佹妸绯荤粺涓绘帶鏉冧粠 workflow 璋冪敤鏍堜腑閲婃斁鍑烘潵锛屽崌绾т负 Agent-native Runtime 鏋舵瀯銆?

褰撳墠鐪熷疄閾捐矾澶ц嚧鏄細

```text
LANChat / 鍗曚汉杈撳叆
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

杩欎釜閾捐矾宸茬粡鑳借窇閫氫竴瀹氱殑鐢熸垚銆佸鍏ャ€佸鏌ュ拰澶氫汉鍚屾锛屼絾瀹冪殑鏍稿績鐭澘鏄細

```text
鎺у埗鏉冧粛鍦ㄦ棫 workflow 鍐呴儴
鎵规鐘舵€佷粛钘忓湪鍑芥暟璋冪敤鏍堥噷
鐢ㄦ埛浠嬪叆鍙兘琚欢杩熷惛鏀?
瀹屾垚鎬佽皟鏁翠緷璧栧眬閮ㄨˉ涓?
鍚屾鐘舵€佷笉鏄?Runtime 涓€绛夌姸鎬?
鏈€缁堟姤鍛婁粛鍙兘鏉ヨ嚜 workflow 鍐呴儴鎷兼帴
```

鏈閲嶆瀯鐩爣锛?

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

鏍稿績鍘熷垯锛?

```text
AgentRuntime 鏄敮涓€涓绘帶
ScenePlan / BatchPlan 鏄鍒掍簨瀹炴簮
ToolCallGraph 鏄墽琛屼簨瀹炴簮
RuntimeState 鏄姸鎬佷簨瀹炴簮
OperationLog 鏄鐩樹簨瀹炴簮
鏃?Workflow 涓嶅啀涓绘帶锛屽彧鑳借鎷嗚В涓哄嚱鏁扮骇宸ュ叿鑳藉姏
```

杩欎笉鏄妸鏃?workflow 鍖呮垚 `legacy.scene_compose` 缁х画璺戯紝涔熶笉鏄 LLM Agent 鑷敱璋冪敤搴曞眰鍑芥暟锛岃€屾槸锛?

```text
Agent 璐熻矗鍐崇瓥
ToolCallGraph 璐熻矗缂栨帓
RuntimeGuard 璐熻矗鏉冮檺鍜岄闄?
ToolRegistry 璐熻矗鎵ц鑳藉姏
RuntimeState 璐熻矗鐘舵€佸悎骞?
OperationLog 璐熻矗鍙洖鏀?
```

鏈閲嶆瀯鐨勬牴鏈洰鐨勶紝鏄鍚庣画鐪熸鏀寔瀹炴椂浠嬪叆鍜屾洿鑷敱鐨勪汉鏈轰氦浜掕竟鐣屻€傛棫 workflow 鐨勭姸鎬佸ぇ閲忚棌鍦ㄥ嚱鏁拌皟鐢ㄦ爤閲岋紝鐢ㄦ埛浠嬪叆鍙兘寤惰繜鍚告敹锛汚gent-native Runtime 瑕佹妸璁″垝銆佹壒娆°€佸伐鍏疯皟鐢ㄣ€佽祫婧愩€乤ctor銆佸鏌ャ€佸悓姝ョ姸鎬侀兘鏄惧紡鍖栵紝璁╃敤鎴蜂粙鍏ュ彲浠ュ彉鎴愬彲鍙栨秷銆佸彲鎻掗槦銆佸彲鏇挎崲銆佸彲纭鐨?`ToolCall / PlanPatch / ReviewRequest`銆?

## 2. 褰撳墠鏍稿疄鐘舵€?

### 2.1 宸ョ▼鐘舵€?

鏈瀹＄悊鏃剁殑浠撳簱鐘舵€侊細

```text
鍒嗘敮锛歮ain
HEAD锛歝3c808fd Merge pull request #70 from CoronaEngine/add_csm
杩滅鐘舵€侊細main 钀藉悗 origin/main 6 涓彁浜?
鐗规畩鐘舵€侊細editor/plugins/AITool/Quasar 浠嶆樉绀轰负 ?锛岄渶瑕佸崟鐙‘璁ゅ瓙妯″潡鎴栧祵濂椾粨搴撶姸鎬?
鏂囨。鍙樻洿锛氭柊澧炴湰璁″垝鏂囨。锛涘凡鍒犻櫎鏃х┖鏂囨。鍜岃鏇夸唬鐨勬棫鍚庣画璁″垝鑽夌
```

鎵ц鏈鍒掑墠蹇呴』鍏堝畬鎴愶細

```text
鍚屾杩滅 main
纭 Quasar 鐘舵€?
纭 docs 褰撳墠寰呮彁浜ゅ彉鏇?
璁板綍鐜版湁娴嬭瘯 baseline
```

### 2.2 CodeGraph 缁濆浼樺厛閾佸緥

鏈鍒掔户鎵?`缁堟瀬璁″垝.md` 涓殑 CodeGraph 瑙勫垯銆傚悗缁嚒娑夊強浠ｇ爜鐞嗚В銆佷唬鐮佸畾浣嶃€佷唬鐮佹煡鐪嬨€佷唬鐮佽鍙栥€佷唬鐮佸啓鍏ャ€佸奖鍝嶉潰鍒ゆ柇銆佽皟鐢ㄩ摼鍒ゆ柇銆佹祴璇曡鐩栧垽鏂紝蹇呴』缁濆浼樺厛浣跨敤 CodeGraph銆?

鎵ц浼樺厛绾у浐瀹氫负锛?

```text
MCP CodeGraph
-> CLI codegraph.cmd
-> 鏅€氭枃浠跺伐鍏?
```

浠ｇ爜淇敼鍓嶅繀椤婚€氳繃 CodeGraph 鏄庣‘锛?

```text
鐩爣绗﹀彿
璋冪敤鏂?
琚皟鐢ㄦ柟
blast radius
鐩稿叧娴嬭瘯
鍗曚汉閾捐矾褰卞搷
澶氫汉閾捐矾褰卞搷
```

绂佹鍦ㄦ湭浣跨敤 CodeGraph 浜嗚В褰卞搷闈㈢殑鎯呭喌涓嬬洿鎺ユ敼锛?

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

### 2.3 褰撳墠浠ｇ爜璇佹嵁

鏈閫氳繃 CodeGraph 鏍稿疄鍒扮殑鍏抽敭浜嬪疄锛?

#### 2.3.1 `SceneComposer.compose()` 浠嶆槸瀹屾暣鐢熸垚涓绘帶

褰撳墠 `SceneComposer.compose()` 浠嶇劧涓茶仈锛?

```text
鐢熸垚鏂囨湰澧炲己 / memory context
extract_items
element classification summary
zone_tree 鍒嗚В
room budget
model_retrieval workflow
review queue
run_progressive_workflow 鎴?_run_original_workflow
final report 瀛楁鍥炲～
```

杩欒鏄?`SceneComposer` 褰撳墠涓嶆槸鍗曠函宸ュ叿锛岃€屾槸鏃?workflow 鐨勪富鎺ц妭鐐逛箣涓€銆侫gent-native 閲嶆瀯蹇呴』鎶婂畠鎷嗘垚宸ュ叿鑳藉姏锛岃€屼笉鏄户缁瀹冩帶鍒跺畬鏁存祦绋嬨€?

#### 2.3.2 `run_progressive_workflow()` 浠嶆槸鎵规涓庡鍏ヤ富鎺?

褰撳墠 `run_progressive_workflow()` 浠嶇劧璐熻矗锛?

```text
鐢熸垚鍦烘櫙妗嗘灦
鍒濆鍖?SceneSession / SceneDiffTracker / EngineWriteGate
鎸?phase 鏋勫缓 micro-batch
澶勭悊 pending runtime notes
resolve pending resource requests
璋冪敤 incremental_import
鎵ц AABB / room bounds repair
鎵ц VLM checkpoint
鍚堝苟 final report / vlm report
杩斿洖 operation_log / progress_events / pending_tasks
```

杩欒鏄?progressive workflow 宸茬粡鍏峰涓€浜涚洰鏍囪兘鍔涳紝浣嗙姸鎬佷粛娌℃湁涓婂崌涓虹粺涓€ RuntimeState銆傚悗缁笉鑳芥妸 `run_progressive_workflow()` 鍖呮垚澶у伐鍏风户缁富鎺э紝蹇呴』鎷嗘垚 `batch / import / review / report` 宸ュ叿銆?

#### 2.3.3 `GenerationScheduler` 宸叉湁闃熷垪鑳藉姏锛屼絾浠嶆槸鏃т笟鍔＄姸鎬佹簮

褰撳墠 `GenerationScheduler` 宸叉湁锛?

```text
QUEUED / PREPARING / COMPOSING / IMPORTING / DONE / FAILED / PAUSED
queue_limit
priority
submit / status / snapshot
event log
async worker
```

杩欎簺鏄彲澶嶇敤鑳藉姏锛屼絾涓嶈兘缁х画浣滀负涓氬姟涓绘帶鐘舵€佹簮銆傜洰鏍囧舰鎬佷腑瀹冨簲闄嶇骇涓?`ToolCallGraphExecutor` 鐨勬墽琛岄槦鍒楄兘鍔涳紝涓氬姟鐘舵€佽繘鍏?RuntimeState銆?

#### 2.3.4 `SeedPlan` 宸叉湁璁″垝闆忓舰锛屼絾闇€瑕佸崌绾т负 ScenePlan

褰撳墠 `SeedPlanStatus` 鍖呭惈锛?

```text
draft / clarifying / proposed / confirmed / executing / paused / completed / cancelled
```

褰撳墠 SeedPlan 宸叉壙鎷呭浜虹‘璁や笌璁″垝鎵挎帴鐨勪竴閮ㄥ垎鑱岃矗锛屼絾 Agent-native 鍚庡簲鍗囩骇涓?`ScenePlan`锛?

```text
ScenePlan 鏄鍒掍簨瀹炴簮
SeedPlan 鍙綔涓鸿縼绉绘槧灏勫璞?
涓嶅啀浣滀负鏂版灦鏋勬渶缁堢姸鎬佸璞?
```

#### 2.3.5 `SceneSession.OperationLogEntry` 宸插瓨鍦紝浣嗕綔鐢ㄥ煙涓嶅

褰撳墠 `OperationLogEntry` 鍦?`scene_session.py` 鍐呴儴锛岀敤浜庤褰曠敤鎴?Agent/绯荤粺鎿嶄綔璐︽湰鏉＄洰銆傚畠鏄湁浠峰€肩殑闆忓舰锛屼絾浠嶅眬闄愪簬 progressive session銆?

鐩爣褰㈡€佷腑 OperationLog 蹇呴』涓婂崌涓?Runtime 绾ц处鏈紝瑕嗙洊锛?

```text
Agent 鍐崇瓥
ToolCall 鍒涘缓
Guard 鍒ゆ柇
宸ュ叿鎵ц
StatePatch 鍚堝苟
VLM 寤鸿
鍚屾骞挎挱
澶辫触鍥為€€
鏈€缁堟姤鍛?
```

#### 2.3.6 VLM 宸叉湁 checkpoint policy锛屼絾浠嶅祵鍦?workflow 涓?

褰撳墠 `VlmCheckpointPolicy` 宸叉敮鎸侊細

```text
structure_review
high_risk_object_review
final_consistency_review
```

浣嗗畠鐢?`run_progressive_workflow()` 璋冪敤锛屼笉鏄?Runtime 宸ュ叿銆傜洰鏍囧舰鎬佸簲鎷嗕负锛?

```text
review.vlm_structure
review.vlm_high_risk_object
review.vlm_final_consistency
review.generate_adjustment_proposal
```


### 2.4 Python / C++ 杈圭晫鏍稿疄

鏈」鐩鍓嶅凡鏈夌浉褰撲竴閮ㄥ垎澶氫汉銆佸悓姝ャ€佹秷鎭拰寮曟搸鎺ュ彛鑳藉姏涓嬫矇鍒?C++銆侫gent-native 閲嶆瀯涓嶈兘鍙湪 Python 灞傝璁?Runtime锛屽惁鍒欎細鍑虹幇涓ゅ浜嬪疄婧愶細Python 璁や负鐘舵€佸凡鏇存柊锛屼絾 C++ LANChat / Network / Actor / Asset 鍚屾浜嬪疄骞舵湭瀵归綈銆?

褰撳墠宸叉牳瀹炵殑 C++ 杈圭晫鍖呮嫭锛?

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

鍏朵腑 `lanchat_send_message_ex()` 褰撳墠璐熻矗锛?

```text
鏋勯€?message_id
鍖哄垎 host / user
鍐欏叆 LanChatState
鎸佷箙鍖?LANChat message
骞挎挱 CHAT_MESSAGE
瑙﹀彂 agent trigger queue
```

`lanchat_send_agent_reply_ex()` 褰撳墠璐熻矗锛?

```text
鏋勯€?agent reply message
鍐欏叆 LanChatState
骞挎挱 CHAT_AGENT_REPLY
鎼哄甫 sender_type / message_kind / target_agent_id / source_user_id / correlation_id / metadata_json
```

杩欒鏄?AgentRuntime 涓嶈兘缁曡繃 C++ LANChat 閫氶亾鐩存帴缁存姢涓€濂?Python-only 鑱婂ぉ鐘舵€併€傛纭竟鐣屾槸锛?

```text
C++ 璐熻矗鎴块棿銆佹垚鍛樸€佹秷鎭€丄gent roster銆佺綉缁滃箍鎾€佸簳灞傚悓姝ヤ簨瀹?
Python AgentRuntime 璐熻矗璁″垝銆佹壒娆°€佸伐鍏峰浘銆佸鏌ャ€佹姤鍛娿€佷笟鍔＄姸鎬?
浜岃€呴€氳繃鏄庣‘ Tool / Binding / Event schema 瀵归綈
```

褰撳墠 Python 渚т篃宸叉湁 `EngineWriteGate`锛屽叾鑱岃矗鏄紩鎿庡啓鍏ュ彛涓茶鍖栵細

```text
import_model
remove_actor
set_transform
set_material
settle
screenshot
```

浣?`EngineWriteGate` 鍙槸鍐欏叆浜掓枼淇濇姢锛屼笉鏄?RuntimeState锛屼篃涓嶆槸 C++/Python 鎺ュ彛鍗忚銆侫gent-native 閲嶆瀯鏃讹紝搴旀妸瀹冨崌绾т负 ToolRegistry 涓嬬殑 engine-write adapter锛岃€屼笉鏄鍚勫伐鍏疯嚜鐢辫皟鐢?C++/Python 寮曟搸鎺ュ彛銆?

## 3. 鎺ㄨ崘鐩爣鏋舵瀯

### 3.1 鐩爣鏋舵瀯鍥?

```text
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?                   LANChat / 鍗曚汉杈撳叆 / 澶氫汉鐢ㄦ埛 / Agent            鈹?
鈹?      鏅€氳亰澶┿€佹柟妗堣璁恒€佺‘璁ゃ€佷粙鍏ャ€佺姸鎬佹煡璇€佸畬鎴愬悗璋冩暣           鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                                鈹?
                                v
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?                        AgentRuntime                              鈹?
鈹?- 鍞竴鐢ㄦ埛鍏ュ彛                                                     鈹?
鈹?- 绠＄悊 plan / batch / tool graph / runtime state / operation log    鈹?
鈹?- 璋冨害 GM / Planner / Builder / Reviewer                           鈹?
鈹?- 绂佹鐢ㄦ埛鍏ュ彛鐩磋繛鏃?workflow                                      鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
        鈹?             鈹?             鈹?             鈹?
        v              v              v              v
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?GM Agent     鈹?鈹?Planner Agent鈹?鈹?Builder Agent鈹?鈹?Reviewer Agent    鈹?
鈹?鎬荤粨/浠茶/纭鈹?鈹?ScenePlan    鈹?鈹?Batch/Tool   鈹?鈹?瀹℃煡/璋冩暣寤鸿      鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
       鈹?               鈹?               鈹?                 鈹?
       鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                                鈹?
                                v
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?                        ToolCallGraph                              鈹?
鈹?涓茶 / 骞惰 / 渚濊禆 / 閲嶈瘯 / 鍙栨秷 / abandoned late result             鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                                鈹?
                                v
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?RuntimeGuard + ToolRegistry                                        鈹?
鈹?鏉冮檺銆侀闄┿€佺‘璁ゃ€佸伐鍏峰瓨鍦ㄦ€с€乻chema 鏍￠獙銆佸啓鎿嶄綔鎷︽埅                鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
               鈹?                              鈹?
               v                               v
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?  鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?Atomic / Mid-grain Tools      鈹?  鈹?RuntimeState / OperationLog      鈹?
鈹?plan/asset/import/layout/VLM  鈹?  鈹?鐘舵€佸悎骞躲€佺増鏈€佸鐩樸€佹姤鍛婁緷鎹?   鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?  鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
               鈹?                                 鈹?
               v                                  v
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?  鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?Engine / Asset / Network      鈹?  鈹?User-visible Report / Progress   鈹?
鈹?鐪熷疄寮曟搸銆佽祫婧愩€乤ctor銆佸悓姝?    鈹?  鈹?鍙 RuntimeState + OperationLog 鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?  鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
```

### 3.2 鏋舵瀯涓嶅彉閲?

鍚庣画鎵€鏈夋媶浠诲姟銆佷唬鐮佸疄鐜板拰楠屾敹閮藉繀椤婚伒瀹堣繖浜涗笉鍙橀噺锛?

```text
1. 鐢ㄦ埛鍏ュ彛鍙兘杩涘叆 AgentRuntime
2. Agent 鍙兘浜у嚭缁撴瀯鍖栧璞★紝涓嶇洿鎺ユ墽琛?
3. ToolCallGraph 鏄敮涓€鎵ц缂栨帓
4. RuntimeGuard 鏄敮涓€鍐欐潈闄愬垽鏂?
5. RuntimeState 鏄敮涓€鐘舵€佷簨瀹炴簮
6. OperationLog 蹇呴』鍏堜簬鐢ㄦ埛鎶ュ憡
7. 鐪熷疄寮曟搸杩斿洖浼樺厛浜?Agent 璁″垝
8. ToolResult 涓嶇洿鎺ユ敼鐘舵€侊紝鍙兘鎻愪氦 StatePatch
9. 娌℃湁 Validator 閫氳繃鐨?Agent 杈撳嚭涓嶅緱鎵ц
10. 鏃?workflow 涓绘帶鍏ュ彛涓嶅緱閲嶆柊鏆撮湶缁欐櫘閫氱敤鎴?
```

## 4. 鏍稿績妯″潡璁捐

### 4.1 AgentRuntime

鏂板鐩綍锛?

```text
editor/plugins/AITool/services/agent_runtime/
```

鏍稿績鏂囦欢锛?

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

鏍稿績 API锛?

```python
AgentRuntime.handle_message()
AgentRuntime.confirm_plan()
AgentRuntime.handle_intervention()
AgentRuntime.query_state()
AgentRuntime.apply_adjustment()
AgentRuntime.generate_report()
```

绂佹鏅€氬叆鍙ｇ洿鎺ヨ皟鐢細

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

鑱岃矗锛?

```text
鎬荤粨澶氫汉璁ㄨ
婢勬竻妯＄硦鎰忓浘
浠茶澶氫汉鍐茬獊
鎻愬嚭纭璇锋眰
鎺у埗鏆傚仠 / 缁х画鑺傚
```

绂佹锛?

```text
鐩存帴鐢熸垚妯″瀷
鐩存帴瀵煎叆鍦烘櫙
鐩存帴淇敼 actor
鐩存帴璋冪敤鏃?workflow
```

#### Planner Agent

鑱岃矗锛?

```text
鎶婄敤鎴烽渶姹傚拰澶氫汉璁ㄨ杞垚 ScenePlan
鍒ゆ柇 indoor / outdoor / mixed
鍖哄垎 object / substrate / terrain / boundary / lighting / layout
鐢熸垚椋庢牸銆佺┖闂淬€佽祫婧愩€佷氦浜掔害鏉?
```

#### Builder Agent

鑱岃矗锛?

```text
鎶?confirmed ScenePlan 鎷嗘垚 BatchPlan
瑙勫垝姣忔壒 ToolCallGraph
鍚告敹鐢熸垚涓敤鎴蜂粙鍏?
鍐冲畾澶辫触鏃堕噸璇曘€佽烦杩囨垨璇㈤棶鐢ㄦ埛
```

#### Reviewer Agent

鑱岃矗锛?

```text
璇诲彇 RuntimeState
妫€鏌ョ己澶便€佹诞绌恒€佺┛妯°€佹瘮渚嬨€侀鏍笺€佸悓姝ュ紓甯?
鐢熸垚 AdjustmentProposal
涓嶇洿鎺ユ墽琛屼慨鏀?
```

### 4.3 ScenePlan

`ScenePlan` 鏇夸唬 `SeedPlan` 鎴愪负璁″垝浜嬪疄婧愩€俙SeedPlan` 鍙綔涓鸿縼绉绘湡杈撳叆鎴栧吋瀹规槧灏勶紝浣嗘柊閾捐矾鐨勭姸鎬佷互 `ScenePlan` 涓哄噯銆?

寤鸿缁撴瀯锛?

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

`BatchPlan` 鏇夸唬 progressive workflow phase 鎴愪负鎵规浜嬪疄婧愩€?

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

`ToolCallGraph` 鏇夸唬鏃?workflow 鎴愪负鎵ц浜嬪疄婧愩€?

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

蹇呴』鏀寔锛?

```text
涓茶鎵ц
骞惰鎵ц
渚濊禆绛夊緟
澶辫触璺宠繃
澶辫触涓柇
閲嶈瘯
鍙栨秷
abandoned late result
```

鎵ц瑙勫垯锛?

```text
鏃犱緷璧栬妭鐐瑰彲骞惰
渚濊禆澶辫触鏃舵寜 node policy 鍐冲畾 skip / retry / abort
鐢ㄦ埛浠嬪叆鍙彇娑堟湭寮€濮嬭妭鐐?
杩熷埌缁撴灉鑻?graph version 宸茶繃鏈燂紝鏍?abandoned锛屼笉鍐欏叆 RuntimeState
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

纭鍒欙細

```text
鏃?ToolCall 涓嶆墽琛?
鏃?RuntimeGuard 涓嶅啓鍦烘櫙
鏃?ToolResult 涓嶆洿鏂扮姸鎬?
鏃?OperationLog 涓嶇畻瀹屾垚
```

### 4.7 StatePatch

ToolResult 涓嶇洿鎺ユ敼 RuntimeState锛屽彧杩斿洖 StatePatch銆?

```python
@dataclass
class StatePatch:
    patch_id: str
    base_version: int
    target: Literal["plan", "batch", "scene", "asset", "actor", "geometry", "review", "sync"]
    operations: list[dict]
    source_tool_call_id: str
```

鍚堝苟瑙勫垯锛?

```text
RuntimeState.apply_patch() 缁熶竴鍚堝苟
patch 蹇呴』甯?base_version
鐗堟湰涓嶄竴鑷磋繘鍏?reconcile
鐪熷疄寮曟搸杩斿洖 > Tool 棰勬湡 > Agent 璁″垝
澶辫触 ToolCall 涓嶅緱鍐?success state
late result 鍙兘鍐?OperationLog锛屼笉鑳借鐩栨柊鐘舵€?
```

### 4.8 RuntimeState

RuntimeState 鏄敮涓€鐘舵€佷簨瀹炴簮銆?

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

鐘舵€佹煡璇€丟M 鎬荤粨銆丷eviewer 瀹℃煡銆佹渶缁堟姤鍛婂彧鑳借鍙?RuntimeState 鍜?OperationLog銆?

### 4.9 RuntimeGuard

椋庨櫓绛夌骇锛?

```text
Low:
鐘舵€佹煡璇€佽鍒掔敓鎴愩€佹姤鍛婄敓鎴愩€丄ABB 妫€鏌ャ€乂LM 瀹℃煡

Medium:
妯″瀷瀵煎叆銆佹櫘閫?actor 绉诲姩銆佽创鍦般€佷綆椋庨櫓甯冨眬璋冩暣

High:
鍒犻櫎 actor銆佹浛鎹㈡ā鍨嬨€侀噸鐢熸垚銆佷慨鏀?system actor銆佸浜哄箍鎾€佽鐩栧満鏅?
```

纭瑙勫垯锛?

```text
瀹屾暣鐢熸垚蹇呴』纭
澶氫汉鏂规鎵ц蹇呴』纭
鐢熸垚涓拷鍔犲彲鎸夐厤缃‘璁?
瀹屾垚鎬佷綆椋庨櫓璐村湴鍙嚜鍔ㄦ墽琛?
鍒犻櫎 / 鏇挎崲 / 閲嶇敓鎴愬繀椤荤‘璁?
system actor 榛樿绂佹淇敼
VLM 寤鸿鍙敓鎴?proposal
```

绂佹鏅€氳皟鏁达細

```text
__room_box
__room_terrain
_terrain_boundary
__terrain_boundary
sky
terrain
```

### 4.10 Validators

蹇呴』鏂板锛?

```text
ScenePlanValidator
BatchPlanValidator
ToolCallGraphValidator
ToolCallValidator
AdjustmentProposalValidator
StatePatchValidator
```

鏍￠獙鍐呭锛?

```text
蹇呭～瀛楁瀹屾暣
宸ュ叿鍚嶅瓨鍦ㄤ簬 ToolRegistry
椋庨櫓绛夌骇鍚堟硶
system actor 淇敼琚姝?
object / substrate / terrain 鍒嗙被鍚堟硶
BatchPlan 寮曠敤鐨?item 瀛樺湪
AdjustmentProposal 鍙寘鍚厑璁哥殑浣庨闄?delta
```

Agent 杈撳嚭涓嶉€氳繃 validator 鏃讹細

```text
涓嶈繘鍏ユ墽琛?
鍐?OperationLog
鍚戠敤鎴疯繑鍥炴緞娓呮垨澶辫触鍘熷洜
```

## 5. 鏃т唬鐮佸鐞嗗垎绫?

鏃т唬鐮佷笉涓€鍒€鍒囧垹闄わ紝鎸夊洓绫诲鐞嗭細

```text
A. 涓绘帶绫伙細鍒犻櫎 / 绂佺敤 / 闅愯棌
B. 鍙鐢ㄥ嚱鏁扮被锛氭媶鎴?Tool
C. 鐘舵€佺被锛氳縼绉诲埌 RuntimeState
D. 娴嬭瘯 / 鏂囨。绫伙細淇濈暀涓?legacy regression baseline
```

### 5.1 A 绫伙細涓绘帶绫?

鍖呮嫭锛?

```text
瀹屾暣 compose 涓绘祦绋?
progressive workflow 涓绘帶
鏃?scheduler 涓氬姟涓绘帶
鏃?direct final adjustment
鏃?direct sync entry
鏃х敤鎴峰彲瑙﹀彂 slash command
```

澶勭悊锛?

```text
鏅€氱敤鎴峰叆鍙ｇ鐢?
涓嶅厑璁镐綔涓?legacy big tool 淇濈暀
涓嶅厑璁哥户缁喅瀹?plan / batch / report / user status
```

### 5.2 B 绫伙細鍙鐢ㄥ嚱鏁扮被

鍖呮嫭锛?

```text
瀵硅薄鎻愬彇鍑芥暟
鍦烘櫙绫诲瀷鍒ゆ柇鍑芥暟
妯″瀷鐢熸垚 provider
璧勬簮璺緞瑙ｆ瀽鍑芥暟
瀵煎叆 API
AABB 璁＄畻鍑芥暟
璐村湴鍑芥暟
VLM 璋冪敤鍑芥暟
actor 骞挎挱鍑芥暟
鏂囦欢鍚屾鍑芥暟
```

澶勭悊锛?

```text
鎷嗘垚 ToolRegistry 涓殑宸ュ叿
鎵€鏈夎皟鐢ㄥ繀椤讳骇鐢?ToolCall / ToolResult / StatePatch / OperationLog
```

### 5.3 C 绫伙細鐘舵€佺被

鍖呮嫭锛?

```text
workflow phase
pending items
imported actors
failed assets
review result
sync progress
final report fields
```

澶勭悊锛?

```text
杩佺Щ鍒?RuntimeState
鏃у唴閮ㄧ姸鎬佸彧浣滀负 ToolResult 杈撳叆锛屼笉浣滀负鐢ㄦ埛鍙浜嬪疄婧?
```

### 5.4 D 绫伙細娴嬭瘯 / 鏂囨。绫?

澶勭悊锛?

```text
鏃ф祴璇曞厛鏍囪涓?legacy regression
瀵瑰簲 AgentRuntime 娴嬭瘯 + F5 楠屾敹閮介€氳繃鍚庯紝鍐嶅垹闄ゆ垨褰掓。
涓嶈杩囨棭鍒犻櫎鏃ф祴璇?
```

## 6. 宸ュ叿鎷嗚В鏄犲皠

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


## 7. Python / C++ 鎺ュ彛缁熶竴灞傝璁?

Agent-native 閲嶆瀯蹇呴』鎶?Python 鍜?C++ 鐨勬帴鍙ｈ竟鐣岀粺涓€鎹嬫竻妤氥€傚惁鍒?RuntimeState銆丩ANChatState銆丒ngine scene state銆丯etwork sync state 浼氬垎瑁傘€?

### 7.1 浜嬪疄婧愬垎灞?

鎺ㄨ崘浜嬪疄婧愬垝鍒嗭細

```text
C++ 浜嬪疄婧愶細
- 鎴块棿涓?peer 杩炴帴鐘舵€?
- LANChat 鍘熷娑堟伅銆佹垚鍛樸€丄gent roster
- message_id / seq / timestamp
- actor 鍒涘缓銆乼ransform銆佸垹闄ょ殑寮曟搸浜嬪疄
- 璧勬簮鍚屾鍜?peer 浼犺緭浜嬪疄
- 搴曞眰缃戠粶骞挎挱缁撴灉

Python AgentRuntime 浜嬪疄婧愶細
- ScenePlan
- BatchPlan
- ToolCallGraph
- RuntimeState 涓氬姟瑙嗗浘
- pending_interventions
- review_state
- OperationLog
- 鐢ㄦ埛鍙鎶ュ憡

鍏变韩浜嬪疄锛?
- actor_id
- asset_id / model_path / resource hash
- room_id
- plan_id
- batch_id
- tool_call_id
- correlation_id
```

璁捐鍘熷垯锛?

```text
C++ 杩斿洖鐨勭湡瀹炲紩鎿庣粨鏋滀紭鍏堜簬 Agent 璁″垝
Python Runtime 涓嶄吉閫?C++ 鎴愬姛缁撴灉
C++ 娑堟伅鍜屽悓姝ヤ簨浠跺繀椤昏兘鏄犲皠鍒?RuntimeState
RuntimeState 鍙兘閫氳繃 C++ result / ToolResult / StatePatch 鏇存柊
```

### 7.2 Runtime-C++ Bridge

鏂板鎴栨槑纭竴灞傛ˉ鎺ユā鍧楋細

```text
runtime_cpp_bridge.py
```

鑱岃矗锛?

```text
灏佽 C++ binding 璋冪敤
缁熶竴鍙傛暟 schema
缁熶竴杩斿洖 result schema
鎶?C++ error code 鏄犲皠鎴?ToolResult.error_code
鎶?C++ success result 鏄犲皠鎴?StatePatch
鎶?C++ event/callback 鏄犲皠鎴?RuntimeEvent
```

绂佹锛?

```text
涓氬姟 Agent 鐩存帴璋冪敤 CoronaEngine.* binding
涓氬姟 Agent 鐩存帴璋冪敤 NetworkSystem 鏆撮湶鍑芥暟
涓氬姟 Agent 鐩存帴璋冪敤 SceneTools.create_actor
涓氬姟 Agent 鐩存帴鍐?LANChat message
```

### 7.3 C++ 鎺ュ彛宸ュ叿鍖栧垎绫?

LANChat tools锛?

```text
lanchat.send_user_message
lanchat.send_agent_reply
lanchat.send_system_message
lanchat.query_room_state
lanchat.query_history
lanchat.register_agent
lanchat.remove_agent
```

Engine actor tools锛?

```text
engine.actor.import_model
engine.actor.create
engine.actor.query
engine.actor.list
engine.actor.set_transform
engine.actor.remove_guarded
engine.actor.snapshot
```

Engine geometry tools锛?

```text
engine.geometry.compute_aabb
engine.geometry.query_bounds
engine.geometry.snap_to_ground
engine.geometry.check_overlap
```

Network sync tools锛?

```text
network.sync_actor_snapshot
network.broadcast_actor_delta
network.transfer_asset
network.query_peer_sync_state
network.reconcile_peer_state
```

VLM / screenshot tools锛?

```text
engine.capture_viewport
review.vlm_structure
review.vlm_final_consistency
```

鎵€鏈夎繖浜涘伐鍏烽兘蹇呴』閬靛畧锛?

```text
ToolCall -> RuntimeGuard -> runtime_cpp_bridge -> C++ binding/API -> ToolResult -> StatePatch -> RuntimeState
```

### 7.4 C++/Python 缁熶竴 ID 涓?metadata 瑙勮寖

蹇呴』缁熶竴杩欎簺瀛楁锛?

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

LANChat message 鐨?`metadata_json` 搴旀垚涓?Runtime 浜嬩欢妗ワ紝鑰屼笉鏄浠绘剰涓存椂瀛楁銆傚缓璁?metadata 鑷冲皯鏀寔锛?

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

### 7.5 C++ 涓嬫矇鑳藉姏杩佺Щ鍘熷垯

宸茬粡杩佸埌 C++ 鐨勮兘鍔涳紝涓嶈鍐嶆惉鍥?Python銆傛纭鐞嗘柟寮忔槸锛?

```text
C++ 淇濇寔搴曞眰浜嬪疄涓庢墽琛?
Python Runtime 閫氳繃宸ュ叿鎺ュ彛璋冨害
ToolResult 鎶?C++ 缁撴灉鍙樻垚 StatePatch
OperationLog 璁板綍 Python 鍐崇瓥涓?C++ 鎵ц缁撴灉
```

濡傛灉鏌愪釜鍔熻兘褰撳墠涓€鍗婂湪 Python銆佷竴鍗婂湪 C++锛屽繀椤诲湪杩佺Щ浠诲姟涓槑纭細

```text
璋佹槸浜嬪疄婧?
璋佽礋璐ｆ墽琛?
璋佽礋璐ｇ姸鎬佽浆鎹?
璋佽礋璐ｇ敤鎴峰彲瑙佹姤鍛?
澶辫触鐮佷粠鍝噷浜х敓
鏄惁闇€瑕?F5/瀹炴満楠岃瘉
```

## 8. 澶辫触绛栫暐

ToolCallGraph 鎵ц澶辫触蹇呴』鏈夋槑纭瓥鐣ワ紝涓嶈兘闈犲紓甯稿悜澶栧啋娉°€?

```text
璧勬簮鐢熸垚澶辫触锛?
  鍙噸璇曪紱鍙檷绾?retrieve锛涗粛澶辫触鍒欐爣 asset failed锛屼笉鍒涘缓 actor

瀵煎叆澶辫触锛?
  鏍囪 import failed锛涗笉鍒涘缓 actor锛涗笉鍐?actor_state success

AABB 澶辫触锛?
  鍐?review warning锛涗笉闃诲鍏ㄩ儴鐢熸垚锛涚浉鍏?actor 鏍?geometry_unknown

璐村湴澶辫触锛?
  鍐?adjustment warning锛涗笉浼鎴愬姛锛涘厑璁哥敤鎴峰悗缁啀娆¤皟鏁?

VLM 澶辫触锛?
  鍐?review unavailable / failed锛涗笉闃诲涓婚摼璺?

鍚屾澶辫触锛?
  鍦烘櫙鐢熸垚鍙畬鎴愶紝浣?sync_state 鏍?partial / failed

楂橀闄?guard 鎷掔粷锛?
  璇锋眰鐢ㄦ埛纭锛屾垨缁堟璇?action

StatePatch 鍐茬獊锛?
  杩涘叆 reconcile锛涚湡瀹炲紩鎿庝簨瀹炰紭鍏堬紱鏃?patch 鏍?stale

late result锛?
  鍐?OperationLog锛涗笉瑕嗙洊 RuntimeState
```


## 9. 瀹炴柦鑺傚

鏈妭鏇夸唬鏃х増鍗曠函鈥滃満鏅敓鎴愰噸鏋勨€濊妭濂忋€傛柊鐨勫疄鏂借妭濂忛噰鐢ㄤ袱灞傝矾绾匡細

```text
杩戞湡璺嚎锛欶5 鍓嶇湡瀹?vertical slice 鍐插埡
涓暱鏈熻矾绾匡細浠?Game-ready Scene Runtime 鎵挎帴 AI Game Demo Runtime
```

### 9.1 褰撳墠闃舵鍒ゅ畾

褰撳墠椤圭洰鐘舵€佹寜鐪熷疄鐩爣鍒ゆ柇锛?

```text
鏁翠綋 Agent-native 閲嶆瀯锛氱害 60%
Python / 闈?native / Runtime 鏋舵瀯灞傦細绾?75%
Engine / C++ / 澶氫汉鍚屾 / F5 瀹炴満灞傦細绾?40%-50%
```

褰撳墠涓嶅簲缁х画鎵╁ぇ閲忔祴璇曘€侀棬绂併€乺eplay summary锛岃€屽簲浠庘€滆瘉鏄?Runtime 寰堝畬鏁粹€濆垏鎹㈠埌锛?

```text
璇佹槑 Runtime 鑳界湡瀹炵敓鎴愪竴涓彲琚父鎴忛€昏緫娑堣垂鐨勯€氱敤鍦板舰鍦烘櫙
```

### 9.2 F5 鍓嶅啿鍒?Milestone A锛氱湡瀹?engine write adapter 鏀跺彛

鐩爣锛?

```text
鎵€鏈夌湡瀹?actor import / transform / delete / environment import 鍐欐搷浣?
缁熶竴閫氳繃 Runtime adapter 杈圭晫
```

蹇呴』婊¤冻锛?

```text
ToolCall -> RuntimeGuard -> EngineWriteGate / runtime_cpp_bridge -> ToolResult -> StatePatch -> RuntimeState -> OperationLog
```

鍔ㄤ綔锛?

```text
鏀跺彛 actor import provider
鏀跺彛 transform provider
鏀跺彛 delete provider
鏀跺彛 environment / terrain import provider
纭澶辫触鐮佽繘鍏?ToolResult.error_code
纭 C++ / Engine 鐪熷疄杩斿洖浼樺厛浜?Agent 璁″垝
```

瀹屾垚鏍囧噯锛?

```text
RuntimeState 涓嶄吉閫?engine success
OperationLog 鍙鐩?engine write 鎴愯触
status_summary 鑳界湅鍒?engine_write_status
娑夊強鐪熷疄 C++ / Engine 鐨勭粨璁烘爣璁?[寰?F5/瀹炴満楠岃瘉]
```

### 9.3 F5 鍓嶅啿鍒?Milestone B锛氶€氱敤 terrain / environment route

鐩爣锛?

```text
灏?terrain / ground / sky / grass / forest / water / mountain 绛夌幆澧冪被鍏冪礌
璺敱鍒?terrain / environment / substrate 閾捐矾
鑰屼笉鏄櫘閫?asset/model/actor 閾捐矾
```

鍔ㄤ綔锛?

```text
寮哄寲 scene.extract_environment
寮哄寲 asset.route_item
寮哄寲 environment.resolve_substrate
寮哄寲 terrain.create / terrain.update 鐨勬渶灏忓伐鍏疯矾寰?
```

瀹屾垚鏍囧噯锛?

```text
sky / grass / ground / terrain 涓嶈繘鍏ユ櫘閫氭ā鍨嬬敓鎴?
甯愮 / 灏忔湪妗?/ 瀹濈 / 寤虹瓚 / 鏁屼汉绛?concrete object 杩涘叆 asset/model/actor 閾捐矾
RuntimeState 鑳藉尯鍒?terrain_state / environment_state / asset_state / actor_state
```

### 9.4 F5 鍓嶅啿鍒?Milestone C锛歛ctor import -> grounding -> AABB 鏈€灏忛棴鐜?

鐩爣锛?

```text
璁?concrete objects 鍙互鐪熷疄杩涘叆鍦烘櫙锛屽苟鑾峰緱 transform / grounding / AABB / review 缁撴灉
```

鍔ㄤ綔锛?

```text
actor.import_model
actor.place / actor.set_transform
geometry.compute_aabb
geometry.snap_to_ground_selective
geometry.check_overlap
geometry.repair_low_risk
review.aabb
```

瀹屾垚鏍囧噯锛?

```text
actor_state 鏈?actor_id / asset_id / transform
geometry_state 鏈?AABB / bounds / grounding_status
review_state 鏈?review summary
澶辫触鏃朵笉浼鎴愬姛
娴┖ / 绌挎ā / AABB unknown 鑳借繘鍏?warning
```

### 9.5 F5 鍓嶅啿鍒?Milestone D锛歴cene_entity_registry 鏈€灏忓彲鐢?

鐩爣锛?

```text
鎶婂満鏅?actor 杞垚鍚庣画娓告垙绯荤粺鍙秷璐圭殑瀹炰綋娓呭崟
```

鍔ㄤ綔锛?

```text
鏂板鎴栬ˉ榻?scene_entity_registry read/write schema
浠?actor_state / asset_state / geometry_state / review_state 鑱氬悎瀹炰綋浜嬪疄
涓烘瘡涓疄浣撹ˉ semantic_role / entity_type / gameplay_tags / interaction_capability 榛樿鍊?
```

瀹屾垚鏍囧噯锛?

```text
RuntimeState 鑳芥煡璇?scene_entity_registry
final report 鑳藉彧璇?RuntimeState / OperationLog 杈撳嚭瀹炰綋鎽樿
鍚庣画 GameDesignPlan / ScriptPlan / BlueprintPlan 鍙互绋冲畾寮曠敤瀹炰綋
```

绗竴鐗堝厑璁革細

```text
interaction_capability = none / decorative / interactable_candidate
gameplay_tags = inferred / empty
script_bindings = []
physics_profile / audio_profile / lighting_profile 浣跨敤榛樿鍗犱綅
```

### 9.6 F5 鍓嶅啿鍒?Milestone E锛歴ync actor snapshot / asset transfer status 鏈€灏忛棴鐜?

鐩爣锛?

```text
澶氫汉鍚屾鐘舵€佽繘鍏?RuntimeState锛屼笉鍐嶅彧鏄鍏ュ壇浣滅敤
```

鍔ㄤ綔锛?

```text
sync.actor_snapshot
sync.actor_broadcast
sync.asset_transfer
sync.peer_status
sync.reconcile_remote_state
```

瀹屾垚鏍囧噯锛?

```text
鐢熸垚鎴愬姛 != 瀵煎叆鎴愬姛 != 鍚屾鎴愬姛
sync_state 鑳芥煡璇?actor snapshot / asset transfer / peer status
OperationLog 鑳藉鐩樺悓姝ヤ簨浠?
鐪熷疄澶氫汉鑱旀満缁撴灉鏍囪 [寰?F5/瀹炴満楠岃瘉]
```

### 9.7 F5 鍓嶆渶灏忛獙鏀跺満鏅?

鏈€灏忛獙鏀跺満鏅細

```text
鐢熸垚涓€涓畝鍗曟．鏋楄惀鍦帮紝鏈夎崏鍦般€佸ぉ绌恒€佸笎绡枫€佸皬鏈ㄦ銆?
```

娉ㄦ剰锛氭．鏋楄惀鍦板彧鏄€氱敤鍦板舰鍦烘櫙鐢熸垚 vertical slice 鐨勯獙鏀舵牱渚嬶紝涓嶆槸浜у搧鐩爣銆?

蹇呴』楠岃瘉锛?

```text
鑽夊湴 / 澶╃┖ / ground / terrain 杩涘叆 environment / terrain / substrate 閾捐矾
甯愮 / 灏忔湪妗岃繘鍏?asset / model / actor 閾捐矾
鐗╀綋鎽嗘斁渚濊禆 terrain / ground plane / grounding 鏈哄埗
actor 鏈?transform / grounding / AABB 妫€鏌ョ粨鏋?
RuntimeState 鑳芥煡 terrain / environment / asset / actor / geometry / review
scene_entity_registry 鑳借緭鍑哄彲琚悗缁父鎴忛€昏緫娑堣垂鐨勫疄浣撴竻鍗?
OperationLog 鑳藉鐩?plan -> terrain -> asset -> actor -> review -> report
final report 鍙兘璇诲彇 RuntimeState + OperationLog
```

### 9.8 褰撳墠鏆傜紦浜嬮」

浠ヤ笅鍐呭鏆傜紦锛屼笉杩涘叆 F5 鍓?P0锛?

```text
鐩存帴瀹炵幇 GameDesignAgent / CombatAgent / StoryAgent / BalanceAgent / ScriptAgent
澶嶆潅鍓ф儏 / 鎴樻枟 / 鏁板€肩敓鎴?
瀹屾暣钃濆浘 / 绉湪浠ｇ爜鐢熸垚
楂樼骇澶氫汉鍐茬獊浠茶
澶嶆潅 VLM 璐ㄩ噺闂?
澶ц妯℃柊澧?replay summary
澶ц妯℃墿鍏呰竟瑙掓祴璇?
杩滅宸紓澶勭悊
Quasar 鑴忛」澶勭悊
```

### 9.9 鍚庣画闃舵锛欰I Game Demo Runtime 鎵挎帴璺嚎

褰?Game-ready Scene Runtime 杈惧埌 F5 鍙敤鍚庯紝鍐嶈繘鍏ュ悗缁樁娈点€?

#### Phase G0锛欸ameWorldState / GameDesignPlan 璁捐

鏂板浜嬪疄婧愶細

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

瑕佹眰锛?

```text
鍙兘璇诲彇 RuntimeState / scene_entity_registry
涓嶈兘鐩存帴璇诲彇鏃?workflow 鍐呴儴鐘舵€?
涓嶈兘缁戝畾涓嶇ǔ瀹?actor_id
```

#### Phase G1锛氱瓥鍒?Agent 鎺ュ叆

鑱岃矗锛?

```text
鍏冲崱鐩爣
鏍稿績寰幆
鍓ф儏鑺傚
浠诲姟鐩爣
鎴樻枟瑙勫垯
鏁板€肩害鏉?
鑳滆礋鏉′欢
```

绂佹锛?

```text
鐩存帴鍐?engine actor
鐩存帴鐢熸垚鑴氭湰骞舵墽琛?
缁曡繃 RuntimeGuard 淇敼鍦烘櫙
```

#### Phase G2锛氱編鏈?/ 鑹烘湳 Agent 鎵╁睍

鑱岃矗锛?

```text
鍦烘櫙椋庢牸缁熶竴
闊抽闊虫晥寤鸿
鐏厜鍙傛暟
鏉愯川鍙傛暟
鐗╃悊鍙傛暟
澹板厜鍔涜嚜鍔ㄨ皟鏁?proposal
```

鎵€鏈夎皟鏁村厛杩涘叆锛?

```text
ArtAdjustmentProposal
-> RuntimeGuard
-> ToolCallGraph
-> StatePatch
```

#### Phase G3锛氱▼搴?/ 鑴氭湰 / 钃濆浘 Agent 鎺ュ叆

鑱岃矗锛?

```text
钃濆浘 / 绉湪浠ｇ爜鐢熸垚
瑙﹀彂鍣ㄧ敓鎴?
浜や簰閫昏緫鐢熸垚
浠诲姟鑴氭湰
鎴樻枟琛屼负
UI 閫昏緫
```

蹇呴』缁忚繃锛?

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

#### Phase G4锛氫竴閿?AI Game Demo 鐢熸垚

鐩爣锛?

```text
澶氫汉澶?Agent 璁ㄨ
-> GameDesignPlan
-> Game-ready Scene Runtime
-> GameplayEntityPlan
-> Script / Blueprint 鐢熸垚
-> Review
-> F5 鍙帺 demo
```


## 10. 娴嬭瘯璁″垝

褰撳墠杩涘叆 F5 鍓嶅啿鍒烘ā寮忥紝娴嬭瘯绛栫暐浠庘€滃ぇ閲忔墿灞曢棬绂佲€濆垏鎹负鈥滀富闂ㄧ + 鏈€灏忕浉鍏抽獙璇佲€濄€?

### 10.1 蹇呰窇娴嬭瘯

```text
python -B editor/plugins/AITool/services/verify_ultimate_plan.py
鏈疆鏀瑰姩鐩存帴鐩稿叧娴嬭瘯
蹇呰 syntax compile
```

### 10.2 鏈樁娈典紭鍏堟祴璇曠被鍨?

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

### 10.3 鏆備笉寮烘眰娴嬭瘯

```text
澶ц妯″叏閲?AgentRuntime 娴嬭瘯
缁嗗皬杈硅 replay summary 娴嬭瘯
涓庢湰杞?vertical slice 鏃犲叧鐨勫巻鍙插洖褰?
澶嶆潅 VLM 鏁堟灉娴嬭瘯
澶嶆潅澶氫汉鍐茬獊浠茶娴嬭瘯
瀹屾暣娓告垙绛栧垝 / 鑴氭湰 Agent 娴嬭瘯
```

### 10.4 蹇呴』鏍囪 [寰?F5/瀹炴満楠岃瘉] 鐨勫唴瀹?

```text
C++ actor import
actor transform
actor delete
terrain / environment 鐪熷疄鍐欏叆
asset transfer
LAN peer 鍚屾
VLM screenshot
鐪熷疄 Engine 鍦烘櫙鏁堟灉
CEF UI 闀胯€楁椂鍙嶉
澶氫汉鑱旀満鍙鎬?
```

### 10.5 娴嬭瘯杈圭晫鍘熷垯

娴嬭瘯涓嶈兘鍙嶅悜缁戞灦閲嶆瀯鑺傚銆?

鍏佽锛?

```text
涓昏闂ㄧ閫氳繃
鏈疆鏍稿績閾捐矾娴嬭瘯閫氳繃
杈硅娴嬭瘯鏍囪鍚庣画澶勭悊
```

涓嶅厑璁革細

```text
涓轰簡鏂板 replay summary 鎷栨參鐪熷疄 vertical slice
涓轰簡杈硅娴嬭瘯澶ч潰绉噸鏋?
涓轰簡娴嬭瘯鏂逛究缁曡繃 RuntimeGuard
涓轰簡娴嬭瘯鏂逛究浼€?Engine success
```


## 11. F5 楠屾敹鍦烘櫙

### 11.1 F5 鍓嶆渶灏忓満鏅細閫氱敤鍦板舰鍦烘櫙 vertical slice

鑴氭湰锛?

```text
鐢熸垚涓€涓畝鍗曟．鏋楄惀鍦帮紝鏈夎崏鍦般€佸笎绡枫€佸皬鏈ㄦ銆?
纭鐢熸垚銆?
鏌ョ湅鐘舵€併€?
鏌ョ湅鏈€缁堟姤鍛娿€?
```

楠屾敹鐩殑锛?

```text
楠岃瘉閫氱敤鍦板舰鍦烘櫙鐢熸垚 Runtime锛岃€屼笉鏄獙璇佹．鏋楄惀鍦颁笓鐢ㄩ€昏緫銆?
```

楠屾敹瑕佹眰锛?

```text
鑽夊湴  / ground / terrain 杩涘叆 environment / terrain / substrate 閾捐矾
甯愮 / 灏忔湪妗岃繘鍏?asset / model / actor 閾捐矾
actor import 缁忚繃 Runtime adapter
actor transform / grounding / AABB 鏈?RuntimeState 浜嬪疄
review summary 鑳界湅鍒?geometry / grounding 缁撴灉
scene_entity_registry 鏈夊彲琚父鎴忛€昏緫娑堣垂鐨勫疄浣撴竻鍗?
OperationLog 鑳藉鐩?plan -> terrain -> asset -> actor -> review -> report
final report 鍙 RuntimeState + OperationLog
```

### 11.2 瀹ゅ唴鍦烘櫙鍥炲綊锛氬彲鐖卞崸瀹?

鐩爣锛?

```text
楠岃瘉 room_box / object / layout / grounding / final report
```

鑴氭湰锛?

```text
甯垜璁捐涓€涓彲鐖辩殑鍗у锛屾湁搴娿€佷功妗屻€佽。鏌溿€佸彴鐏€佸湴姣€佺帺鍋躲€佷功鏋躲€?
纭鐢熸垚銆?
瀹屾垚鍚庯細璋冩暣涓€涓嬪竷灞€銆?
濡傛灉娴┖锛氭妸妯″瀷閮借惤鍦般€?
```

### 11.3 瀹ゅ鍦板舰鍦烘櫙鍥炲綊锛氭．鏋楄惀鍦版墿灞曠増

鐩爣锛?

```text
楠岃瘉 terrain / substrate / environment 涓嶈繘鍏ユ櫘閫氭ā鍨嬬敓鎴?
```

鑴氭湰锛?

```text
鍋氫竴涓．鏋楄惀鍦帮紝鏈夊ぉ绌恒€佹爲鏋椼€佽崏鍦般€佸皬鏈ㄦ銆佸笎绡枫€佺瘽鐏€?
纭鐢熸垚銆?
```

### 11.4 娣峰悎鍦烘櫙鍥炲綊锛氬够鎯抽泦甯?

鐩爣锛?

```text
楠岃瘉 mixed zone銆佹壒娆′粙鍏ャ€佽拷鍔犲璞°€佹渶缁堟姤鍛?
```

鑴氭湰锛?

```text
鍋氫竴涓鍐呭缁撳悎鐨勫鏅氬够鎯抽泦甯傦紝鏈夊叆鍙ｃ€佹憡浣嶃€佺伅鍏夈€佷紤鎭尯銆?
鐢熸垚涓細鍐嶅姞涓€涓ぉ浣块洉鍍忋€?
鐢熸垚涓細鍐嶅姞涓€鍙皬鐙椼€?
瀹屾垚鍚庯細鏌ョ湅鍚告敹浜嗗摢浜涜皟鏁淬€?
```

### 11.5 澶?Agent / 澶氫汉鍗忓悓鍥炲綊锛氳棌瀹濆

鐩爣锛?

```text
楠岃瘉澶氫汉 / 澶?Agent 璁ㄨ鎵挎帴銆丟M 鎬荤粨銆丼cenePlan 纭銆佸畬鎴愭€佽皟鏁?
```

鑴氭湰锛?

```text
@闀胯€?鍥寸粫寮虹洍钘忓疂瀹や富棰樿璁轰竴涓嬨€?
@鍟嗕汉 璇勪环骞舵敼杩涢暱鑰呮柟妗堛€?
@GM 鎬荤粨褰撳墠鏂规銆?
鎸夌収杩欎釜鏂规鐢熸垚銆?
纭鐢熸垚銆?
瀹屾垚鍚庯細璋冩暣涓€涓嬪竷灞€锛屾垜鐪嬫ā鍨嬩綅缃啿绐併€?
纭璋冩暣銆?
```

### 11.6 澶氫汉鍚屾楠屾敹

鐩爣锛?

```text
楠岃瘉 actor sync / asset transfer / peer status 杩涘叆 RuntimeState
```

鑴氭湰锛?

```text
鎴夸富鍒涘缓鎴块棿銆?
鍏朵粬鐢ㄦ埛鍔犲叆銆?
鎴夸富澶?Agent 璁ㄨ鍚庣‘璁ょ敓鎴愩€?
瑙傚療鍏朵粬鐢ㄦ埛 actor / asset / sync 鐘舵€併€?
妯℃嫙杩滅缂鸿祫婧愭垨鏂嚎閲嶈繛銆?
```

楠屾敹瑕佹眰锛?

```text
鎴夸富鐢熸垚鎴愬姛涓嶇瓑浜庡悓姝ユ垚鍔?
peer 绔祫婧愮己澶卞彲鏌ヨ
閲嶅璧勬簮涓嶉噸澶嶄紶
actor transform 涓€鑷?
late join 鑳芥敹鍒板彲鎭㈠鐘舵€?
```


## 12. 瀹屾垚鏍囧噯

鏈閲嶆瀯鐨勫畬鎴愭爣鍑嗗垎涓ゅ眰锛欶5 鍓嶅畬鎴愭爣鍑嗕笌鏈€缁?Agent-native 瀹屾垚鏍囧噯銆?

### 12.1 F5 鍓嶅畬鎴愭爣鍑?

杩涘叆绗竴杞?F5 / 瀹炴満楠岃瘉鍓嶏紝蹇呴』婊¤冻锛?

```text
1. AgentRuntime 涓绘帶璺緞鍙窇閫氭渶灏?vertical slice
2. ScenePlan / BatchPlan 鍙綔涓鸿鍒掑拰鎵规浜嬪疄婧?
3. terrain / environment / substrate 涓?ordinary model route 鏄庣‘鍒嗙
4. forest / sky / grass / terrain / ground 涓嶈繘鍏ユ櫘閫氭ā鍨嬬敓鎴?
5. 甯愮 / 灏忔湪妗岀瓑 concrete objects 杩涘叆 asset/model/actor 閾捐矾
6. actor import / transform / delete 璧?Runtime adapter
7. grounding / AABB / layout repair 鏈夋渶灏忓彲鐢?RuntimeState 浜嬪疄
8. review summary 鑳借鍙?geometry / grounding 缁撴灉
9. scene_entity_registry 鏈€灏忓彲鏌ヨ
10. sync actor snapshot / asset transfer status 鏈夋渶灏忛棴鐜?
11. final report 鍙 RuntimeState + OperationLog
12. verify_ultimate_plan.py 閫氳繃
13. 鏈疆鐩存帴鐩稿叧娴嬭瘯閫氳繃
14. C++ / Engine / Sync / VLM screenshot 缁撴灉鏄庣‘鏍囪 [寰?F5/瀹炴満楠岃瘉]
```

### 12.2 Game-ready Scene Runtime 瀹屾垚鏍囧噯

```text
1. RuntimeState 鏄庣‘鍖呭惈 terrain_state / environment_state / asset_state / actor_state / geometry_state / review_state / sync_state
2. scene_entity_registry 鑳界ǔ瀹氳緭鍑?actor_id / asset_id / semantic_role / entity_type / transform / AABB / grounding_status / interaction_capability / gameplay_tags
3. 鐪熷疄寮曟搸杩斿洖浼樺厛浜?Agent 璁″垝
4. ToolResult 涓嶇洿鎺ユ敼鐘舵€侊紝鍙兘鎻愪氦 StatePatch
5. OperationLog 鍙洖鏀?plan -> terrain -> asset -> actor -> geometry -> review -> sync -> report
6. 鐢ㄦ埛鐘舵€佹煡璇€丟M summary銆乫inal report 鍧囦笉璇诲彇鏃?workflow 鍐呴儴鐘舵€?
7. 鏃?workflow 鍙綔涓?fallback / regression baseline锛屼笉浣滀负鏅€氱敤鎴蜂富鎺у叆鍙?
```

### 12.3 鏈€缁?Agent-native 瀹屾垚鏍囧噯

```text
1. 鐢ㄦ埛鍏ュ彛鍏ㄩ儴杩涘叆 AgentRuntime
2. ScenePlan 鏇夸唬 SeedPlan 鎴愪负璁″垝浜嬪疄婧?
3. BatchPlan 鏇夸唬 workflow phase 鎴愪负鎵规浜嬪疄婧?
4. ToolCallGraph 鏇夸唬鏃?workflow 鎴愪负鎵ц浜嬪疄婧?
5. RuntimeState 鏄敮涓€鐘舵€佹簮
6. OperationLog 鍙洖鏀惧畬鏁存墽琛岃矾寰?
7. StatePatch 缁熶竴鍚堝苟鐘舵€?
8. Agent 杈撳嚭蹇呴』缁忚繃 Validator
9. SceneComposer 涓嶅啀涓绘帶瀹屾暣鐢熸垚
10. ProgressiveWorkflow 涓嶅啀涓绘帶鎵规鎵ц
11. Scheduler 涓嶅啀涓绘帶涓氬姟鐘舵€?
12. Geometry / VLM / Layout / Sync 鍏ㄩ儴宸ュ叿鍖?
13. 鐢熸垚涓粙鍏ヨ繘鍏?Runtime pending_interventions
14. 瀹屾垚鎬佽皟鏁磋繘鍏?Reviewer + RuntimeGuard + ToolCall
15. 鏃?workflow 涓绘帶鍏ュ彛琚殣钘忔垨鍒犻櫎
16. ALLOW_LEGACY_MAIN_WORKFLOW=0
```

### 12.4 AI Game Demo 鎵挎帴鏍囧噯

鍙湁褰?Game-ready Scene Runtime 杈惧埌浠ヤ笅鏍囧噯鍚庯紝鎵嶅厑璁告寮忓惎鍔ㄤ笂灞傛父鎴?Agent锛?

```text
1. scene_entity_registry 绋冲畾
2. actor_id / asset_id / transform / AABB / grounding_status 鍙煡璇?
3. terrain / walkable / bounds 鍩虹浜嬪疄鍙煡璇?
4. interaction_capability / gameplay_tags 鏈夐粯璁?schema
5. Script / Blueprint 鏈潵鍙粦瀹氱ǔ瀹氬疄浣?
6. RuntimeGuard 鍙嫤鎴珮椋庨櫓鑴氭湰 / actor 淇敼
7. OperationLog 鑳藉鐩樺満鏅疄浣撶敓鎴愯繃绋?
```

杈惧埌浠ヤ笂鏍囧噯鍚庯紝鍐嶅紑濮嬶細

```text
GameDesignPlan
GameplayEntityPlan
CombatPlan
QuestPlan
ScriptPlan
BlueprintPlan
```

## 13. 椋庨櫓涓庡弽妯″紡

### 13.1 鎶婃棫 workflow 鍖呮垚澶у伐鍏?

鍙嶆ā寮忥細

```text
legacy.scene_compose()
legacy.progressive_compose()
legacy.workflow_orchestrator()
```

闂锛?

```text
鏃?workflow 缁х画鏆椾腑涓绘帶
RuntimeState 鍙兘鎷跨粨鏋?
鐢ㄦ埛浠嬪叆浠嶄笉鑳藉疄鏃舵帶鍒朵腑闂寸姸鎬?
```

澶勭悊锛?

```text
绂佹淇濈暀杩欑被澶у伐鍏?
鍙兘淇濈暀鍑芥暟绾ц兘鍔?
```

### 13.2 鍏堟媶鏃ч摼璺啀琛ユ柊閾捐矾

鍙嶆ā寮忥細

```text
鍏堝垹闄?SceneComposer / ProgressiveWorkflow 涓昏矾寰?
鍐嶅皾璇曡ˉ AgentRuntime
```

澶勭悊锛?

```text
姣忔媶涓€涓棫鑳藉姏锛屽繀椤诲凡鏈?ToolCall 鏇夸唬
姣忎釜 Phase 蹇呴』鏈夊彲杩愯鍒囩墖
```

### 13.3 Agent 鐩存帴鍐欏満鏅?

鍙嶆ā寮忥細

```text
Agent 鐩存帴璋冪敤 import / move / delete / sync
```

澶勭悊锛?

```text
鎵€鏈夊啓鎿嶄綔蹇呴』缁忚繃 RuntimeGuard
鎵€鏈夋墽琛屽繀椤绘槸 ToolCall
```

### 13.4 RuntimeState 涓庣湡瀹炲紩鎿庝笉涓€鑷?

澶勭悊锛?

```text
鐪熷疄寮曟搸杩斿洖浼樺厛浜?Agent 璁″垝
ToolResult 蹇呴』鎻愪緵 StatePatch
StatePatch 鍐茬獊杩涘叆 reconcile
```

### 13.5 杩囨棭鍒犻櫎鏃ф祴璇?

澶勭悊锛?

```text
鏃ф祴璇曞厛鏍?legacy regression
鏂?Runtime 娴嬭瘯鍜?F5 楠屾敹瑕嗙洊鍚庡啀鍒犻櫎鎴栧綊妗?
```

### 13.6 2026-07-03 褰撳墠钀界洏澧為噺

鏈疆宸插畬鎴愮殑闈?native 鍒囩墖锛?

```text
1. AgentRuntimeFlags 榛樿淇濇寔 Runtime 涓绘帶锛?
   - AGENT_RUNTIME_ENABLED 榛樿寮€鍚?
   - OLD_WORKFLOW_DIRECT_ENTRY_DISABLED 榛樿寮€鍚?
   - ALLOW_LEGACY_MAIN_WORKFLOW 榛樿鍏抽棴
   - 鐪熷疄 provider / engine-write 閫氶亾鍧囬粯璁ゅ叧闂?

2. 鐪熷疄 engine-write provider 蹇呴』鏄惧紡寮€鍚細
   - AGENT_RUNTIME_USE_ENGINE_ENVIRONMENT_IMPORT_PROVIDER
   - AGENT_RUNTIME_USE_ENGINE_IMPORT_PROVIDER
   - AGENT_RUNTIME_USE_ENGINE_DELETE_PROVIDER
   - AGENT_RUNTIME_USE_ENGINE_TRANSFORM_PROVIDER

3. LANChat Runtime 宸ュ巶宸叉敮鎸佹樉寮忚閰?actor delete provider锛?
   - flag锛欰GENT_RUNTIME_USE_ENGINE_DELETE_PROVIDER
   - 宸ュ叿鍊欓€夛細remove_actor / delete_actor / destroy_actor
   - 鍐欏叆杈圭晫锛歮ake_engine_actor_delete_provider + EngineWriteGate.remove_actor
   - 榛樿浠嶄负 RuntimeState-only锛屼笉浼氳嚜鍔ㄥ垹闄ょ湡瀹炲紩鎿?actor

4. engine_write_status 宸茬粺涓€涓哄洓閫氶亾璇讳晶锛?
   - environment_import
   - actor_import
   - actor_delete
   - layout_transform
   - LANChat / GM engine_write report 灞曠ず鍚屾牱鏄剧ず env-import 涓?actor-delete锛屼笉鍐嶅彧鏄剧ず import / transform

5. verify_ultimate_plan.py 宸叉妸鍏抽敭杩囨浮杈圭晫绾冲叆闈?native 鎬婚棬绂侊細
   - agent_runtime/*
   - lanchat_agent_worker.py
   - lanchat_host_action_executor.py
   - generation_scheduler.py
   - generation_composer_adapter.py
   - engine_write_gate.py
   - scene_composer_progressive.py

6. Review / VLM checkpoint 宸茶ˉ榻?RuntimeState 璇讳晶浜嬪疄婧愶細
   - RuntimeState room schema 鏄惧紡鍖呭惈 custom_vlm_checkpoint_facts
   - runtime.review.vlm_checkpoint 鐨勭粨鏋滀細涓?geometry_reviews 涓€璧疯繘鍏?review_summary
   - status_summary / generate_report 鍧囧彲鐪嬪埌 VLM checkpoint 鐨?checkpoint_type銆乻tatus銆乺eviewed_targets 涓?advisory_count
   - VLM advisory 浠嶅彧褰㈡垚 review_advisory_proposals锛屽繀椤绘埧涓荤‘璁わ紝涓嶇洿鎺ヤ慨鏀?actors
   - OperationLog 浠呬繚鐣?VLM checkpoint 鐨勫畨鍏ㄦ憳瑕佸瓧娈碉紝operation_replay / report compact replay 鍧囧彲鍥炴斁 checkpoint_count銆乻tatus_counts銆乤dvisory_count
   - runtime.review.vlm_checkpoint 浼氬彂鍑哄畨鍏ㄧ敤鎴峰彲瑙?RuntimeEvent锛氬瑙傚鏌ュ畬鎴?/ 宸茶烦杩?/ 绛夊緟鎴夸富纭锛屼笉鏆撮湶 provider銆乸rompt銆佹埅鍥捐矾寰勬垨 raw payload

7. 璧勬簮鍑嗗闃舵宸茶ˉ榻愬畨鍏?RuntimeEvent锛?
   - runtime.asset.image.prepare / runtime.asset.model.prepare 鎴愬姛鍚庝細鎶湶鍥剧墖璧勬簮 / 妯″瀷璧勬簮鍑嗗杩涘害
   - RuntimeEvent payload 鍙厑璁?status銆乺equested_count銆乺eady_count銆乫ailed_count 绛夎鏁板瓧娈?
   - 涓嶆毚闇?provider銆乸rompt銆乵etadata銆佸唴閮?URL銆佺鏈夎矾寰勬垨 raw payload

8. 鍦烘櫙鐗╀綋瀵煎叆鎴愬姛璺緞宸茶ˉ榻愬畨鍏?RuntimeEvent锛?
   - runtime.actor.import_batch 鎴愬姛鍚庝細鎶湶鏈壒鍦烘櫙鐗╀綋瀵煎叆瀹屾垚 / 閮ㄥ垎瀹屾垚
   - RuntimeEvent payload 鍙厑璁?status銆乺equested_count銆乮mported_count銆乫ailed_count 绛夎鏁板瓧娈?
   - partial import 浼氭槑纭樉绀哄凡瀵煎叆鏁伴噺涓庡け璐ユ暟閲忥紝浣嗕笉鏆撮湶 actor_id銆乵odel_path銆乸rovider銆乮mport_results raw 鎴栫鏈夎矾寰?

9. 鍚屾浜嬪疄宸插叿澶?RuntimeState / OperationLog / RuntimeEvent 鍩虹闂幆锛?
   - record_sync_event 浼氶€氳繃 runtime.sync_event.record ToolCallGraph 鍐欏叆 sync_events / sync_state / actors / assets
   - actor create / transform / delete銆乤sset transfer銆乸eer join / leave / room close 鍧囧彲杩涘叆 status_summary / generate_report / operation_replay
   - OperationLog replay 浼氫繚鐣欏畨鍏?latest_peer_id锛屼究浜庡鐩樺浜?peer join / leave锛屼笉鍐嶅彧鐭ラ亾鈥滃彂鐢熻繃 peer 浜嬩欢鈥?
   - 鍚屾鐢ㄦ埛浜嬩欢鍙姭闇插畨鍏ㄦ憳瑕侊紝涓嶆毚闇?asset_path銆乵essage_id銆乧orrelation_id銆乸rovider銆乁RL 鎴栫鏈夎矾寰?

10. 鏂规鎻愮偧 / 鍏冪礌鍒嗙被宸插叿澶?ToolCallGraph 瀹夊叏鎶湶锛?
   - runtime.plan.extract 鎴愬姛鍚庝細鎶湶鈥滄柟妗堟彁鐐煎畬鎴愨€濓紝鍙毚闇插€欓€夌墿浣撴暟閲忎笌甯冨眬/鐜瑕佺礌鏁伴噺
   - runtime.elements.classify 鎴愬姛鍚庝細鎶湶鈥滃厓绱犲垎绫诲畬鎴愨€濓紝鍙毚闇插噯澶囩敓鎴愭ā鍨嬫暟閲忎笌鐜/鍦板舰/甯冨眬瑕佺礌鏁伴噺
   - RuntimeEvent payload 浠呴€忎紶 status銆乮tem_count銆乧omponent_count 绛夊畨鍏ㄨ鏁板瓧娈?
   - 涓嶆毚闇?candidate_items/routes/prompt/provider/model_path/raw payload 鎴栫鏈夎矾寰?
   - 杩欎竴姝ユ妸鈥淟LM 鎻愮偧濂界殑妯″瀷/鍦板舰淇℃伅瑕佽鐢ㄦ埛鐭ラ亾鈥濈殑瑕佹眰钀藉埌 AgentRuntime ToolCall 浜嬩欢灞傦紝鑰屼笉鏄洖鍒版棫 SceneComposer 鏂囨鎷兼帴

11. 鏈€缁堟姤鍛婂啓鍏ュ凡鍏峰 ToolCallGraph 瀹夊叏鎶湶锛?
   - generate_report 浠嶅厛鍐?OperationLog锛屽啀閫氳繃 runtime.user_report.persist 鍐欏叆 RuntimeState
   - runtime.user_report.persist 鎴愬姛鍚庝細鍙戝嚭鈥滄渶缁堟姤鍛婂凡鍐欏叆 Runtime 鐘舵€佲€濈殑瀹夊叏 RuntimeEvent
   - 璇ヤ簨浠?payload 浠呭寘鍚?status锛屼笉鏆撮湶 report 鍏ㄦ枃銆乷peration_log_index銆乸rovider銆乸rompt銆乺aw payload 鎴栫鏈夎矾寰?
   - report_ready 浠嶄綔涓烘渶缁堢敤鎴锋姤鍛婂畬鎴愪簨浠讹紝report persist 浜嬩欢鐢ㄤ簬璇佹槑鎶ュ憡鐘舵€佸凡杩涘叆 RuntimeState锛屽彲琚悗缁煡璇笌澶嶇洏璇诲彇

12. 鎵规瑙勫垝宸插叿澶?ToolCallGraph 瀹夊叏鎶湶锛?
   - plan_batches 浼氶€氳繃 runtime.batch.plan_record 鍐欏叆 batch_plans / absorbed intervention 鐘舵€?
   - runtime.batch.plan_record 鎴愬姛鍚庝細鍙戝嚭鈥滄壒娆¤鍒掑畬鎴愨€濈殑瀹夊叏 RuntimeEvent
   - RuntimeEvent payload 浠呴€忎紶 status銆乥atch_count 绛夊畨鍏ㄨ鏁板瓧娈?
   - 涓嶆毚闇?requested_items銆佺敤鎴峰師鏂囥€乸rovider銆乸rompt銆乵odel_path 鎴?raw batch state
   - 杩欎竴姝ヨ鐩栤€滃彧瑙勫垝鎵规浣嗗皻鏈帓闃熸墽琛屸€濈殑闃舵锛岄伩鍏嶆壒娆¤鍒掔户缁棌鍦ㄥ嚱鏁拌繑鍥炲€奸噷

13. 鎵规鎵ц杩囩▼宸插叿澶?OperationLog replay 鎽樿锛?
   - operation_replay / generate_report compact replay 鍧囧寘鍚?batch_execution_summary
   - batch_execution_summary 缁熻 started_count銆乧ompleted_count銆乫inalized_count銆乻tatus_counts 涓?latest_batch
   - 鎽樿鏉ユ簮浜庡凡娓呮礂鐨?OperationLog entries锛屼笉鏆撮湶 requested_items銆乼ool graph raw銆乸rovider銆乸rompt 鎴栫鏈夎矾寰?
   - 杩欎竴姝ヨ batch started / finalized / completed 涓嶅彧鍋滅暀鍦ㄦ暎钀芥棩蹇椾簨浠朵腑锛岃€屾槸褰㈡垚鍙獙鏀躲€佸彲澶嶇洏鐨勬壒娆℃墽琛岃鍥?

14. 宸ュ叿鑺傜偣鎵ц杩囩▼宸插叿澶?OperationLog replay 鎽樿锛?
   - operation_replay / generate_report compact replay 鍧囧寘鍚?tool_execution_summary
   - tool_execution_summary 缁熻 started_count銆乻ucceeded_count銆乫ailed_count銆乥locked_count銆乺etry_scheduled_count銆乻kipped_count
   - 鎽樿鍚屾椂淇濈暀 tool_event_counts 涓?latest_tool_event锛屼究浜庡畾浣?ToolCallGraph 鍐呴儴鍋ュ悍搴?
   - 鎽樿鏉ユ簮浜庡凡娓呮礂鐨?OperationLog entries锛屼笉鏆撮湶 tool args銆乺aw result銆乸rovider銆乸rompt銆乵odel_path 鎴栫鏈夎矾寰?
   - 杩欎竴姝ヨ ToolCall 鑺傜偣绾ф墽琛屼笉鍐嶅彧鑳介€愭潯缈绘棩蹇楋紝鑰屾槸褰㈡垚鍙璁＄殑鍥炬墽琛岃鍥?

15. ToolCallGraph 闃熷垪鐢熷懡鍛ㄦ湡宸插叿澶?OperationLog replay 鎽樿锛?
   - operation_replay / generate_report compact replay 鍧囧寘鍚?tool_graph_queue_summary
   - tool_graph_queue_summary 缁熻 queued_count銆乨equeued_count銆乧ompleted_count銆乺ejected_count銆乪mpty_count銆乥locked_count銆乵issing_graph_count
   - 鎽樿鍚屾椂淇濈暀 queue_status_counts銆乹ueue_event_counts 涓?latest_queue_event锛屼究浜庡鐩?Runtime 鎵ц闃熷垪鏄惁绉帇銆佹弧闃熷垪銆佽鏆傚仠/鍙栨秷闃绘柇鎴栫己澶?graph
   - completed_count 鍙潵鑷?tool_graph_queue_state_persisted 鐨?completed 鐘舵€侊紝涓嶆妸閫氱敤 tool_graph_completed 璇畻涓洪槦鍒楀畬鎴?
   - 鎽樿鏉ユ簮浜庡凡娓呮礂鐨?OperationLog entries锛屼笉鏆撮湶 graph raw銆乼ool args銆乸rovider銆乸rompt銆乵odel_path 鎴栫鏈夎矾寰?
   - 杩欎竴姝ョ户缁帹杩?鈥淕enerationScheduler queue -> ToolCallGraph queue鈥?鐨勮渚ф浛鎹紝璁╅槦鍒楀仴搴峰害杩涘叆 Runtime 鍙獙鏀惰鍥?

16. 璧勬簮閫氶亾 readiness 宸插叿澶?OperationLog replay 鎽樿锛?
   - operation_replay / generate_report compact replay 鍧囧寘鍚?resource_readiness_replay_summary
   - resource_readiness_replay_summary 缁熻 status_query_count銆乸ublished_count銆乸ublish_failed_count銆乺eadiness_event_count 涓?status_counts
   - 鎽樿浠?raw OperationLog 鑱氬悎锛屼絾鍙緭鍑哄畨鍏ㄨ鏁板拰 latest_readiness_event锛屼笉鏆撮湶鍏蜂綋 provider 鍚嶇О銆乸rovider 鍑芥暟銆佽瘖鏂?reason銆乸rompt銆乁RL 鎴栫鏈夎矾寰?
   - 瀵瑰瀛楁鍒绘剰浣跨敤 resource_readiness 鑰屼笉鏄?provider_readiness锛岄伩鍏嶅鐩樺璞¤鏅€氱敤鎴风悊瑙ｄ负鍐呴儴 provider 缁嗚妭
   - 杩欎竴姝ヨ鈥滆祫婧愰€氶亾鏄惁宸查妫€ / 鏄惁宸插彂甯?readiness / 鏄惁浜х敓鐢ㄦ埛鍙璧勬簮閫氶亾浜嬩欢鈥濊繘鍏?Runtime 鍙獙鏀惰鍥?

17. StatePatch 鍐茬獊浠茶宸插叿澶?OperationLog replay 鎽樿锛?
   - operation_replay / generate_report compact replay 鍧囧寘鍚?state_patch_summary
   - state_patch_summary 缁熻 version_stamped銆乤pplied銆乧onflict銆乮nvalid銆乺econcile_rejected銆乺econcile_missing銆乺econciled銆乺econcile_failed
   - 鎽樿淇濈暀 decision_counts 涓?latest_reconcile_event锛屼究浜庡鐩?StatePatch conflict 鏄惁宸蹭徊瑁併€佷徊瑁佸喅绛栨槸浠€涔堛€佹槸鍚︽垚鍔熻惤鐩?
   - ToolCallGraph 鎵ц鏈熶骇鐢熺殑 StatePatch conflict 浼氳ˉ鍏?plan_id / batch_id 瀹夊叏褰掑睘锛岀‘淇濇寜 plan_id 鍥炴斁鏃朵笉浼氫涪澶卞悗缁?reconciled 浜嬩欢
   - 鎽樿涓嶆毚闇?patch_id銆乻ource_tool_call_id銆乼ool_call_id 鎴?StatePatch 鍘熷鍐呭锛屽彧杈撳嚭瀹夊叏璁℃暟鍜屼徊瑁佺粨鏋?
   - 杩欎竴姝ヨ鈥滃涓?ToolCall 骞跺彂鍐?RuntimeState 鍚庢槸鍚﹀啿绐?/ 鏄惁澶勭悊 / 澶勭悊缁撴灉鑳藉惁澶嶇洏鈥濊繘鍏?Runtime 鍙獙鏀惰鍥?

18. 鐢熸垚涓粙鍏ュ叆鎵瑰凡鍏峰 OperationLog replay 鎽樿锛?
   - operation_replay / generate_report compact replay 鍧囧寘鍚?intervention_batch_replay_summary
   - intervention_batch_replay_summary 缁熻 routed_count銆乹ueued_count銆乸ersisted_count銆乸ersist_failed_count銆乻kipped_count銆乪nqueue_failed_count銆乤bsorbed_count
   - 鎽樿淇濈暀 status_counts 涓?latest_intervention_batch锛屼究浜庡鐩樼敤鎴蜂腑閫旀柊澧炲璞℃槸鍚﹁璺敱銆佹槸鍚﹁鍚告敹銆佹槸鍚﹁繘鍏ヤ笅涓€鎵?ToolCallGraph 闃熷垪
   - 鎽樿浠?OperationLog 鑱氬悎锛屼絾涓嶆毚闇?patch_id銆佺敤鎴峰師鏂囥€乺equested_items 鏄庣粏銆乼ool graph raw銆乸rovider銆乸rompt 鎴栫鏈夎矾寰?
   - 杩欎竴姝ヨ鈥滅敓鎴愪腑浠嬪叆鏄惁鐪熸鏀瑰彉鍚庣画鎵规鈥濊繘鍏?Runtime 鍙獙鏀惰鍥撅紝鑰屼笉鏄彧渚濊禆鑱婂ぉ瀹ゆ彁绀烘垨鏈€缁堟姤鍛婃枃妗?

19. ScenePlan 鐢熷懡鍛ㄦ湡宸插叿澶?OperationLog replay 鎽樿锛?
   - operation_replay / generate_report compact replay 鍧囧寘鍚?scene_plan_lifecycle_summary
   - scene_plan_lifecycle_summary 缁熻 created_count銆乧onfirmed_count銆乻tate_persisted_count銆乻tate_persist_failed_count銆乻tatus_persisted_count銆乻tatus_persist_failed_count銆乪xtracted_count
   - 鎽樿淇濈暀 status_counts銆乺eason_counts 涓?latest_plan_event锛屼究浜庡鐩樻柟妗堟槸鍚﹀垱寤恒€佹槸鍚︾‘璁ゃ€佹槸鍚﹁繘鍏ユ墽琛屻€佹槸鍚﹀畬鎴?澶辫触銆佺姸鎬佹槸鍚﹀厛浜庢姤鍛婅惤鐩?
   - batch scoped 鎶ュ憡涓殑 scene_plan_lifecycle_summary 浣跨敤 plan scope 鑱氬悎锛岄伩鍏嶆渶缁堟姤鍛婂彧鐪嬪埌鎵规浜嬩欢鍗寸湅涓嶅埌鏂规纭閾捐矾
   - 鎽樿涓嶆毚闇?design_brief銆佺敤鎴峰師鏂囥€乼ool graph raw銆乸rovider銆乸rompt 鎴栫鏈夎矾寰?
   - 杩欎竴姝ヨ鈥滄柟妗堝悕绉?鏂规纭/鎵ц鐘舵€佹槸鍚﹂€忔槑浼犻€掆€濊繘鍏?Runtime 鍙獙鏀惰鍥?

20. RuntimeEvent 鐢ㄦ埛鎶湶宸插叿澶?OperationLog replay 鎽樿锛?
   - operation_replay / generate_report compact replay 鍧囧寘鍚?runtime_event_replay_summary
   - runtime_event_replay_summary 缁熻 emitted_count銆乪mit_failed_count銆乪vent_type_counts 涓?latest_runtime_event
   - 鎽樿鐢ㄤ簬澶嶇洏鍝簺 Runtime 浜嬩欢宸茬粡瀹夊叏鎶湶缁欑敤鎴枫€佹槸鍚︽湁鎶湶鍐欏叆澶辫触銆佷簨浠剁被鍨嬪垎甯冩槸鍚﹁鐩栨柟妗堢‘璁?闃熷垪/鎵规/璧勬簮/鎶ュ憡绛夐樁娈?
   - 鎽樿鍙鍙?OperationLog 涓殑 runtime_event_emitted / runtime_event_emit_failed 瀹夊叏瀛楁锛屼笉鏆撮湶 RuntimeEvent 鏍囬姝ｆ枃銆佺敤鎴峰師鏂囥€乸ayload raw銆乸rovider銆乸rompt 鎴栫鏈夎矾寰?
   - 杩欎竴姝ヨ鈥滀俊鎭姭闇叉槸鍚︾湡鐨勫彂鐢熴€佹槸鍚︽寔缁鐩栭暱鑰楁椂闃舵鈥濊繘鍏?Runtime 鍙獙鏀惰鍥?

21. RuntimeGuard 鎷︽埅缁撴灉宸插叿澶?OperationLog replay 鎽樿锛?
   - operation_replay / generate_report compact replay 鍧囧寘鍚?runtime_guard_replay_summary
   - runtime_guard_replay_summary 缁熻 blocked_count銆乭igh_risk_confirmation_required_count銆亀rite_confirmation_required_count銆乻ystem_actor_write_blocked_count銆乽ser_visible_blocked_event_count
   - 鎽樿淇濈暀 reason_counts 涓?latest_block锛屼究浜庡鐩樺啓鎿嶄綔琚?RuntimeGuard 鎷︽埅鐨勫師鍥犵被鍒?
   - 鎽樿鍙緭鍑哄師鍥犵被鍒拰璁℃暟锛屼笉鏆撮湶 tool_name銆乤ctor 鍚嶇О銆佸伐鍏峰弬鏁般€佺敤鎴峰師鏂囥€乸rovider銆乸rompt 鎴栫鏈夎矾寰?
   - 杩欎竴姝ヨ鈥淩untimeGuard 鏄惁浣滀负鍞竴鍐欐潈闄愬垽鏂敓鏁堛€佹槸鍚︽湁鐢ㄦ埛鍙鎷︽埅鎶湶鈥濊繘鍏?Runtime 鍙獙鏀惰鍥?

22. ToolCallGraph 澶辫触绛栫暐宸插叿澶?OperationLog replay 鎽樿锛?
   - operation_replay / generate_report compact replay 鍧囧寘鍚?tool_failure_strategy_summary
   - tool_failure_strategy_summary 缁熻 retry_scheduled_count銆乨ependency_skipped_count銆乤bandoned_late_result_count銆乭andler_failed_count銆乮nvalid_result_count銆乺untime_facts_missing_count銆乺untime_facts_rejected_count銆乮nvalid_state_patch_count銆乻tate_patch_conflict_count銆乻topped_by_runtime_command_count
   - 鎽樿淇濈暀 strategy_counts 涓?latest_strategy_event锛屼究浜庡鐩樺け璐ユ槸璧伴噸璇曘€佷緷璧栬烦杩囥€佽繜鍒扮粨鏋滀涪寮冦€佸崗璁粨鏋滄棤鏁堛€丷untime facts 缂哄け/鎷掔粷銆丼tatePatch 鍐茬獊杩樻槸杩愯鏃舵殏鍋?鍙栨秷
   - 鎽樿鍙緭鍑虹瓥鐣ョ被鍒€佽鏁般€乥atch_id銆乻tatus / error_code 绛夊畨鍏ㄥ瓧娈碉紝涓嶆毚闇?tool_name銆乼ool args銆乺aw result銆佸紓甯告枃鏈€乸rovider銆乸rompt銆乵odel_path 鎴栫鏈夎矾寰?
   - 杩欎竴姝ヨ鈥淭oolCallGraph 鏀寔渚濊禆銆佸け璐ャ€侀噸璇曘€乤bandoned late result锛屽苟涓斿彲琚?OperationLog 璇佹槑鈥濊繘鍏?Runtime 鍙獙鏀惰鍥?

23. Runtime 鐘舵€佹煡璇㈠凡鍖呭惈 ToolCallGraph 澶辫触绛栫暐鎽樿锛?
   - status_summary 鐩存帴鍖呭惈 tool_failure_strategy_summary锛孏M / 鐢ㄦ埛鐘舵€佹煡璇㈡棤闇€鍏堣Е鍙?operation_replay 鎴?generate_report 涔熻兘鐪嬪埌澶辫触绛栫暐鍋ュ悍搴?
   - 鎽樿澶嶇敤 OperationLog scoped entries锛屽彧杈撳嚭瀹夊叏璁℃暟涓?latest_strategy_event锛屼笉鏆撮湶 tool_name銆乼ool args銆佸紓甯告枃鏈€乸rovider銆乸rompt銆乁RL銆乵odel_path 鎴栫鏈夎矾寰?
   - 杩欎竴姝ヨ鈥滅姸鎬佹煡璇㈣鍙?RuntimeState / OperationLog锛岃€屼笉鏄棫 Scheduler 鍐呴儴鐘舵€佲€濈户缁悜 Phase 5 鐩爣闈犳嫝

24. 鏃?SceneComposer 涓绘帶鐩磋揪鍏ュ彛宸茬撼鍏ラ潤鎬侀棬绂侊細
   - verify_ultimate_plan.py 鏂板 static direct SceneComposer entry gate锛屾壂鎻?AITool services / cai_extensions/agent / main.py
   - 鏅€氱敤鎴峰叆鍙ｄ笉鍏佽鏂板 SceneComposer(...) / composer.compose(...) 鐩磋揪鏃т富鎺?
   - 褰撳墠鍙厑璁?main.py 鐨?composer factory銆乤gent_adapter.py 鐨?legacy guard 鍏ュ彛銆乬eneration_composer_adapter.py 鐨?JobRunner adapter
   - 鍏佽鐨?legacy compose 鏂囦欢蹇呴』鍖呭惈 Runtime flag guard锛歛gent_adapter.py 闇€瑕?_legacy_main_workflow_allowed / AGENT_RUNTIME_REQUIRED_MESSAGE锛実eneration_composer_adapter.py 闇€瑕?can_call_legacy_main_workflow / legacy disabled error
   - 鎵弿鎺掗櫎 Quasar銆佹祴璇曟枃浠躲€乻cene_composer.py 鏈綋锛岄伩鍏嶈浼ゅ簳灞傝兘鍔涘疄鐜颁笌鍥炲綊娴嬭瘯
   - 杩欎竴姝ユ妸鈥滅敤鎴峰叆鍙ｅ彧鑳借繘鍏?AgentRuntime / 鏃?workflow 涓绘帶涓嶅緱閲嶆柊鏆撮湶涓虹敤鎴峰叆鍙ｂ€濆彉鎴愬彲閲嶅楠岃瘉鐨勯潪 native 闂ㄧ

25. 鏃?slash workflow 鍛戒护鏆撮湶绛栫暐宸茬撼鍏ラ潤鎬侀棬绂侊細
   - verify_ultimate_plan.py 鏂板 static workflow command exposure gate锛岃В鏋?workflow_command_policy.py 涓?cai_extensions/agent銆乧ai_extensions/flows 涓嬬殑 WORKFLOW_COMMANDS
   - 搴熷純涓绘帶鍛戒护蹇呴』鐣欏湪 DEPRECATED_USER_WORKFLOW_COMMANDS锛?scene_agent銆?sc_agent銆?scene_composition銆?scene_composition_v2銆?sc_v2銆?full_pipeline銆?pipeline銆?full_pipeline_v2銆?fp_v2銆?multi_scene銆?parallel_generate銆?parallel_generate_v2銆?pg_v2
   - 鍐呴儴璋冭瘯鍛戒护蹇呴』鐣欏湪 INTERNAL_DEBUG_WORKFLOW_COMMANDS锛?model_retrieval銆?terrain_generate銆?terrain
   - 闂ㄧ纭 workflow function get / has / list_function_ids 浠嶇粡杩?should_execute_workflow_function 杩囨护锛岄伩鍏嶇粫杩?slash command 鐩存帴鐢?function_id 鎵ц鏃т富鎺?
   - 杩欎竴姝ュ厑璁?legacy flow 妯″潡缁х画浣滀负 regression baseline 瀛樺湪锛屼絾绂佹搴熷純涓绘帶鍛戒护閲嶆柊鎴愪负鏅€氱敤鎴峰叆鍙?

26. Runtime 鎶ュ憡浜嬪疄婧愰『搴忓凡绾冲叆闈欐€侀棬绂侊細
   - verify_ultimate_plan.py 鏂板 static Runtime report fact-source gate锛岀洿鎺ユ鏌?AgentRuntime.generate_report / status_summary 鐨勫叧閿簨瀹炴簮椤哄簭
   - generate_report 蹇呴』鍏堟瀯閫?operation_replay_summary / classification_summary 绛?RuntimeState + OperationLog 鎽樿锛屽啀鍐?user_report_generated锛屽啀鎸佷箙鍖?report锛屾渶鍚庡彂鍑?report_ready 浜嬩欢
   - status_summary 蹇呴』淇濇寔鍙鐘舵€佹煡璇㈣涔夛細鍙互鍐?runtime_status_queried 瀹¤浜嬩欢锛屼絾涓嶅緱鍐?user_report_generated銆佷笉寰楁寔涔呭寲鐢ㄦ埛鎶ュ憡銆佷笉寰楀彂 report_ready
   - 杩欎竴姝ユ妸鈥淥perationLog 蹇呴』鍏堜簬鐢ㄦ埛鎶ュ憡銆佺姸鎬佹煡璇㈣鍙?RuntimeState / OperationLog 鑰屼笉鏄Е鍙戞姤鍛婂壇浣滅敤鈥濆彉鎴愬彲閲嶅楠岃瘉鐨勯潪 native 闂ㄧ

27. Runtime Validator 濂戠害宸茬撼鍏ラ潤鎬侀棬绂侊細
   - verify_ultimate_plan.py 鏂板 static Runtime validator contract gate锛岀‘璁?ScenePlanValidator銆丅atchPlanValidator銆丳lanPatchValidator銆丼tatePatchValidator銆乀oolCallValidator銆乀oolResultValidator銆乀oolCallGraphValidator銆丄djustmentProposalValidator銆丷eviewAdvisoryProposalValidator銆丷eportRecordValidator 绛夊叧閿?schema validator 鎸佺画瀛樺湪
   - ToolCallGraphExecutor.execute 蹇呴』鍏堣皟鐢?ToolCallGraphValidator.validate锛屽苟鍦ㄦ墽琛屽墠缁忚繃 RuntimeGuard.authorize锛岃繍琛屾椂浜嬪疄娉ㄥ叆鍚庡繀椤婚€氳繃 ToolCallValidator锛屽伐鍏疯繑鍥炲繀椤婚€氳繃 ToolResultValidator
   - ToolCallGraph 鎸佷箙鍖栧繀椤荤粡杩?ToolCallGraphValidator.safe_graph_fact锛岄伩鍏嶆妸 raw args / unsafe graph payload 鍐欏叆 RuntimeState
   - 鐢ㄦ埛鎶ュ憡蹇呴』閫氳繃 runtime.user_report.persist ToolCallGraph 璺緞鎸佷箙鍖栵紝骞剁敱 _persist_user_report_tool 璋冪敤 ReportRecordValidator.validate(report) 鍚庡啀鎻愪氦 StatePatch锛涢棬绂佹寜杩欐潯鐪熷疄宸ュ叿閾炬鏌ワ紝鑰屼笉鏄姹?generate_report 鏈綋鐩存帴鍐?RuntimeState
   - 杩欎竴姝ユ妸鈥淎gent 鍙兘浜у嚭缁撴瀯鍖栧璞°€佹病鏈?Validator 閫氳繃鐨?Agent 杈撳嚭涓嶅緱鎵ц銆乀oolResult 涓嶇洿鎺ユ敼 RuntimeState鈥濈户缁浐鍖栨垚鍙噸澶嶉獙璇佺殑闈?native 闂ㄧ

28. Phase 3 鍦烘櫙鎻愮偧鑳藉姏宸插紑濮嬫媶鎴?Agent-native 宸ュ叿锛?
   - AgentRuntime ToolRegistry 鏂板 scene.extract_objects銆乻cene.classify_type銆乻cene.extract_environment 涓変釜鍙 planning 宸ュ叿
   - scene.extract_objects 鍙礋璐ｄ粠鐢ㄦ埛鏂囨湰鎻愮偧鍙敓鎴愮墿浣擄紝骞跺啓鍏?plan_extractions锛涙娊璞″竷灞€璇嶃€佸ぉ绌恒€佽崏鍦扮瓑涓嶄細杩涘叆鍊欓€夋ā鍨嬫竻鍗?
   - scene.classify_type 鍙礋璐ｇ敓鎴?scene_type / environment_type 浜嬪疄锛屽啓鍏?custom_scene_facts锛岀敤浜庡悗缁?plan / substrate / room_box 鍐崇瓥
   - scene.extract_environment 鍙礋璐ｆ妸鍦板舰銆佸ぉ绌恒€佽崏鍦般€佹．鏋楃瓑鐜 / substrate 椤瑰啓鍏?element_routes銆乧lassification_summaries銆乻ubstrate_plans
   - 涓変釜宸ュ叿鍧囬€氳繃 ToolCallGraphExecutor 鎵ц銆丷untimeGuard 鎺堟潈銆乀oolResult / StatePatch schema 鏍￠獙锛屼笉鍖呰鏃?SceneComposer / ProgressiveWorkflow 涓绘帶
   - runtime.plan.extract / runtime.elements.classify 缁х画浣滀负鏃㈡湁鍥捐妭鐐逛繚鐣欙紝淇濊瘉鐜版湁 ToolCallGraph 娴嬭瘯鍜岃繃娓￠摼璺吋瀹癸紱鏂?scene.* 宸ュ叿鐢ㄤ簬 Phase 3 鎷嗚В绮掑害鏀舵暃
   - 鏂板 test_phase3_scene_extraction_tools_are_registered_without_legacy_main_control 涓?test_phase3_scene_extraction_tools_split_objects_and_environment锛岄獙璇佸伐鍏锋敞鍐屼笉鍚棫涓绘帶璇嶃€佹．鏋楄惀鍦颁腑鐨勫笎绡?/ 灏忔湪妗岃繘鍏ユā鍨嬫竻鍗曪紝澶╃┖ / 鑽夊湴杩涘叆 substrate plan
   - 杩欎竴姝ュ紑濮嬫妸鈥淪ceneComposer 鐨勬彁鍙?/ 鍒嗙被鑱岃矗鈥濇媶鎴愬彲瀹¤ ToolCall锛岃€屼笉鏄户缁鏃т富鎺т竴娆℃€у畬鎴愬満鏅悊瑙ｃ€佽祫婧愩€佸鍏ュ拰鎶ュ憡

29. Phase 3 鏂规绾︽潫鎻愮偧宸叉媶鎴?Agent-native 宸ュ叿锛?
   - AgentRuntime ToolRegistry 鏂板 scene.extract_constraints 鍙 planning 宸ュ叿
   - scene.extract_constraints 浠庢柟妗堟枃鏈彁鐐?mood銆乻tyle_keywords銆乤void_keywords銆乸alette銆乴ighting銆乻cale_rules銆乸lacement_rules锛屽苟鍐欏叆 custom_scene_facts
   - 鈥滀笉瑕佸お鎭愭€?/ 涓嶆亹鎬栤€濊繘鍏?avoid_keywords=too_horror锛屼笉浼氳鍐欐垚姝ｅ悜 style_keywords锛涒€滄洿娓╂殩 / 鐏厜 / 浼戞伅鍖?/ 椋庢牸缁熶竴鈥濆垎鍒繘鍏?mood / lighting / placement_rules
   - 宸ュ叿缁撴灉閫氳繃 ToolCallGraphExecutor 鎵ц銆丷untimeGuard 鎺堟潈銆乀oolResult / StatePatch schema 鏍￠獙锛涗笉鎺ョ湡瀹炲紩鎿庛€佷笉淇敼 actor銆佷笉鐢熸垚鎶ュ憡
   - 鏂板 test_phase3_scene_constraints_tool_extracts_negative_and_style_constraints锛岄獙璇佽礋鍚戠害鏉熴€侀鏍肩害鏉熴€佺伅鍏夌害鏉熴€佷紤鎭尯涓庨鏍间竴鑷存€х害鏉熻兘杩涘叆 RuntimeState
   - 杩欎竴姝ユ妸鈥淪ceneDesignContract / 闀垮懆鏈熷満鏅蹇嗘墍闇€鐨勭害鏉熶簨瀹炩€濆厛钀藉埌 RuntimeState 鐨勭粨鏋勫寲浜嬪疄灞傦紝涓哄悗缁?Planner / Builder Agent 鏇挎崲瑙勫垯鎻愮偧鐣欏嚭绋冲畾 ToolCall 鍚堢害

30. Phase 3 绌洪棿鑼冨洿涓庡尯鍩熸媶鍒嗗凡寮€濮嬪伐鍏峰寲锛?
   - AgentRuntime ToolRegistry 鏂板 room.estimate_bounds 涓?zone.decompose 涓や釜鍙 planning 宸ュ叿
   - room.estimate_bounds 鏍规嵁鍦烘櫙绫诲瀷銆佸€欓€夌墿浣撴暟閲忓拰澶т欢鐗╀綋棰勭畻鐢熸垚 room_bounds_estimate 浜嬪疄锛涘鍐呭啓 bounds_type=room_box锛屽澶?/ 妫灄 / 鑽夊湴 / 澶╃┖绫诲啓 bounds_type=terrain_area
   - zone.decompose 鏍规嵁 room / terrain bounds 涓庡満鏅涔夌敓鎴?zone_decomposition 浜嬪疄锛涜棌瀹濆浼氭媶鍑?entry銆乼reasure_focus銆乻ide_storage銆亀alkable_path锛屽澶栭泦甯?/ 妫灄钀ュ湴浼氭媶鍑哄叆鍙ｃ€佷富璺€佷富浣撳尯銆佺幆澧冭儗鏅瓑鍔熻兘鍖?
   - 涓や釜宸ュ叿鍧囧啓鍏?custom_scene_facts锛岀粡 ToolCallGraphExecutor銆丷untimeGuard銆乀oolResult / StatePatch schema 鏍￠獙锛涗笉鍒涘缓 room_box銆佷笉瀵煎叆 terrain銆佷笉鍐欑湡瀹?actor
   - 鏂板 test_phase3_room_bounds_and_zone_decompose_tools_create_structural_facts 涓?test_phase3_room_bounds_tool_keeps_outdoor_substrate_as_terrain_area锛岄獙璇佽棌瀹濆涓€瀹氫骇鐢?room_box 棰勭畻锛屾．鏋楄惀鍦颁繚鎸?terrain_area 鑰屼笉鏄鐢熸垚 room_box
   - 杩欎竴姝ユ妸鈥滃鍐?room_box 鍏滃簳 / 瀹ゅ substrate 娲剧敓 / 鍖哄煙瑙勫垝鈥濆厛鏀舵暃涓?RuntimeState 缁撴瀯浜嬪疄锛屼负鍚庣画 Builder Agent 鍜岀湡瀹?environment import 宸ュ叿鎺ョ鏃х┖闂存鏋堕€昏緫閾鸿矾

31. Phase 3 璧勬簮璺敱涓庢憜鏀捐緭鍏ュ噯澶囧凡寮€濮嬪伐鍏峰寲锛?
   - AgentRuntime ToolRegistry 鏂板 asset.route_item 涓?placement.prepare_items 涓や釜鍙宸ュ叿
   - asset.route_item 浠庡€欓€夐」涓繃婊ゅぉ绌恒€佽崏鍦扮瓑鐜 / substrate 椤癸紝鍙妸甯愮銆佸皬鏈ㄦ銆佽棌瀹濈绛夋ā鍨嬬墿浣撳啓鍏?asset_request_plans
   - placement.prepare_items 澶嶇敤鐜版湁 build_placement_proposals锛屾妸妯″瀷鐗╀綋杞崲涓轰綆椋庨櫓 placement_proposals锛涘畠鍙敓鎴愭憜鏀捐崏妗堬紝涓嶅鍏ユā鍨嬨€佷笉绉诲姩 actor
   - 涓や釜宸ュ叿鍧囬€氳繃 ToolCallGraphExecutor銆丷untimeGuard銆乀oolResult / StatePatch schema 鏍￠獙锛沘sset.route_item 灞炰簬 asset 绫诲伐鍏凤紝placement.prepare_items 灞炰簬 geometry 绫诲伐鍏凤紝浣嗛兘 requires_write=False
   - 鏂板 test_phase3_asset_and_placement_tools_prepare_only_model_items锛岄獙璇佹．鏋楄惀鍦颁腑鐨勫ぉ绌?/ 鑽夊湴涓嶄細杩涘叆璧勬簮璇锋眰鍜屾憜鏀捐崏妗堬紝甯愮 / 灏忔湪妗屼細杩涘叆鍚庣画璧勬簮涓庢憜鏀鹃摼璺?
   - 杩欎竴姝ユ妸鈥滃璞″埌璧勬簮璇锋眰鈥濆拰鈥滃璞″埌鎽嗘斁鑽夋鈥濈殑鍑嗗闃舵浠庢棫涓绘帶涓媶鍑猴紝涓哄悗缁?asset provider / actor import 宸ュ叿鎺ョ鐪熷疄鎵ц閾鸿矾

32. Phase 3 鎵╁睍瑙勫垝宸ュ叿鍥惧凡鎺ュ叆鐪熷疄 ScenePlan 鍒涘缓閾捐矾锛?
   - AgentRuntime._extract_scene_plan_fields_via_tool_graph 涓嶅啀鍙窇 runtime.plan.extract / runtime.elements.classify锛岃€屾槸鍦?ScenePlan 鍒涘缓鍓嶇粺涓€缂栨帓 scene.extract_objects銆乻cene.classify_type銆乻cene.extract_constraints銆乺oom.estimate_bounds銆亃one.decompose銆乻cene.extract_environment銆乤sset.route_item銆乸lacement.prepare_items锛屽苟淇濈暀 runtime.elements.classify 浣滀负杩囨浮鍏煎鍒嗙被鑺傜偣
   - scene.extract_objects 浣滀负鏍硅妭鐐瑰啓鍏?plan_extractions锛沘sset.route_item銆乸lacement.prepare_items銆乺untime.elements.classify 閫氳繃 consumes_state 浠?plan_extractions 璇诲彇鍚屼竴涓鍒掔骇鎻愮偧缁撴灉锛岄伩鍏嶅悇鑺傜偣閲嶅鐚滄祴鍊欓€夌墿浣?
   - 鏈疆宸查獙璇佽 ToolCallGraph 浼氬湪 ScenePlan 鎸佷箙鍖栧悗銆丼cenePlan 鍒涘缓鎶ュ憡鍓嶅啓鍏?custom_scene_facts銆乪nvironment_substrate_facts銆乤sset_request_plans銆乸lacement_proposals 鍜?model_item_lists
   - 鏂板 test_phase3_scene_plan_creation_runs_extended_planning_tool_graph锛岄獙璇佽棌瀹濆璁″垝鍒涘缓鏃惰兘鐢熸垚 scene_type / constraints / bounds / zones 缁撴瀯浜嬪疄锛宎sset 涓?placement 鑽夋鍖呭惈钘忓疂绠憋紝涓旀墽琛屽浘鑺傜偣鏁拌鐩?Phase 3 鎵╁睍瑙勫垝宸ュ叿
   - 鍚屾鏇存柊 Runtime / LANChat guard 娴嬭瘯涓殑 planning graph 鍒ゅ畾锛氳繖浜?requires_write=False 鐨?scene / asset / placement 鍑嗗鍥惧睘浜?Agent-native 瑙勫垝璇佹嵁锛屼笉灞炰簬瓒婃潈鎵ц鍥撅紱鐪熸鍐欏紩鎿?actor 鐨勫伐鍏蜂粛浼氳 guard 娴嬭瘯璇嗗埆

33. 鎵规鎵ц ToolCallGraph 鐨勬棫鎻愮偧鏍硅妭鐐瑰凡鏇挎崲涓?scene.extract_objects锛?
   - AgentRuntime._build_mock_graph 涓嶅啀浠?runtime.plan.extract 浣滀负鎵规鎵ц鍥剧殑鎻愮偧鏍硅妭鐐癸紝鏀逛负 runtime.scene.snapshot -> scene.extract_objects -> runtime.elements.classify
   - scene.extract_objects 鍦ㄦ壒娆℃墽琛屽浘涓啓 batch 绾?plan_extractions锛岄伩鍏嶈鐩?ScenePlan 鍒涘缓闃舵鐨?plan 绾ф彁鐐间簨瀹烇紱鍚庣画 runtime.elements.classify 浠嶄互 batch.requested_items 涓烘潈濞佹壒娆¤緭鍏?
   - 璧勬簮銆乻ubstrate銆乪nvironment銆乮mage銆乵odel銆乸lacement銆乬eometry review銆乤ctor import銆乂LM checkpoint 鐨勫悗缁緷璧栭摼淇濇寔涓嶅彉锛屼粛閫氳繃 ToolCallGraphExecutor銆丷untimeGuard銆乀oolResult / StatePatch schema 鏍￠獙
   - 鏇存柊 test_runtime_graph_plans_assets_and_placements_before_mock_import 涓?consumes 鐩稿叧娴嬭瘯鏂█锛岀‘璁?snapshot 鍏堜簬 scene.extract_objects锛屽悗缁?asset/image/model/placement/import/review 椤哄簭涓嶅洖閫€
   - 杩欎竴姝ョ户缁敹缂?runtime.plan.extract 鐨勪娇鐢ㄩ潰锛岃鎵规鎵ц閾捐矾涔熷紑濮嬩娇鐢?Phase 3 scene.* 宸ュ叿浣滀负浜嬪疄鎻愮偧鍏ュ彛锛屼负 Phase 4 batch/import/review 宸ュ叿鍖栭摵璺?

34. Phase 4 鎵规鐗╀綋浼樺厛绾у凡鎷嗘垚 batch.prioritize_items ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 batch.prioritize_items 鍙 planning 宸ュ叿锛岀敤浜庡皢 ScenePlan 鐨?concrete_object_items 杞崲涓虹ǔ瀹?ordered_items 涓?priority rows
   - batch.prioritize_items 鍐欏叆 custom_batch_facts 鐨?`{plan_id}:item_priorities`锛屼笉鍒涘缓 BatchPlan銆佷笉瀵煎叆妯″瀷銆佷笉淇敼 actor锛屼篃涓嶆帴瑙︾湡瀹炲紩鎿?
   - plan_batches 涓?enqueue_planned_batches 鍦ㄥ垏鍒?BatchPlan 鍓嶅厛鎵ц batch.prioritize_items ToolCallGraph锛涜嫢宸ュ叿澶辫触鍒欏畨鍏ㄥ洖閫€鍘熷椤哄簭锛屼笉闃绘柇涓婚摼璺?
   - 鐜版湁 batch_plans 浠嶇敱 runtime.batch.plan_record 鎸佷箙鍖栵紝浣?requested_items 鐨勯『搴忓凡鏉ヨ嚜 RuntimeState 涓殑 batch priority fact锛屾帹杩涒€滄壒娆′簨瀹炴簮浠庡嚱鏁板眬閮ㄥ彉閲忚縼绉诲埌 RuntimeState鈥?
   - 鏂板 / 寮哄寲 test_runtime_can_plan_multiple_batches_as_state_facts 涓?legacy model provider 椤哄簭娴嬭瘯锛岄獙璇佹壒娆?flattened requested_items 涓?custom_batch_facts ordered_items 涓€鑷达紝provider 璋冪敤椤哄簭涔熼伒寰?batch priority fact
   - 楂橀闄╃墿浣撳澶╀娇闆曞儚 / 鍔ㄧ墿浼氳鎺掑埌鏍稿績鎵规涔嬪悗銆佹櫘閫氭敮鎾戠墿涔嬪墠锛屼繚鎸?VLM high_risk_object_review 鐨勪腑闂存壒璇箟

35. Phase 4 鐢熸垚涓粙鍏ュ悎骞跺凡鎷嗘垚 batch.merge_intervention ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 batch.merge_intervention 鍙 planning 宸ュ叿锛岀敤浜庡皢 pending intervention candidate patches 涓?base_items 鍚堝苟涓?merged_items
   - batch.merge_intervention 鍐欏叆 custom_batch_facts 鐨?`{plan_id}:merged_interventions`锛屼笉鍒涘缓 BatchPlan銆佷笉鍏ラ槦銆佷笉瀵煎叆妯″瀷銆佷笉淇敼 actor锛屼篃涓嶈Е纰扮湡瀹炲紩鎿?
   - enqueue_pending_intervention_batch 鍦ㄧ瓫鍑哄彲鍚告敹 intervention 鍚庯紝鍏堟墽琛?batch.merge_intervention ToolCallGraph锛屽啀浣跨敤 RuntimeState merge fact 鐢熸垚涓嬩竴鎵?requested_items锛涜嫢宸ュ叿澶辫触鍒欏洖閫€鏃х殑 _merge_items 璺緞
   - merge fact 涓笉鏆撮湶 `patch_id` 瀛楁鍚嶏紝閬垮厤鐢ㄦ埛鎶ュ憡璺緞娉勬紡鍐呴儴琛ヤ竵缁撴瀯锛涘唴閮?batch 浠嶄繚鐣?absorbed_intervention_ids 渚涘洖鏀句笌鍘熷瓙鍐欏叆浣跨敤
   - 寮哄寲 test_enqueue_pending_intervention_batch_adds_next_runtime_batch锛岄獙璇?pending intervention 杩藉姞鎵瑰寘鍚?batch.merge_intervention graph銆乧ustom_batch_facts merge fact銆乷peration_log 浜嬩欢锛屽苟淇濇寔鍘?enqueue 鎸佷箙鍖栧師瀛愭€?

36. Phase 4 鎵规缁堟€佹爣璁板凡鎷嗘垚 batch.mark_completed / batch.mark_failed / batch.mark_cancelled ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 batch.mark_completed銆乥atch.mark_failed 涓?batch.mark_cancelled 涓変釜绐勫啓宸ュ叿锛屽彧璐熻矗鎶婂凡鏈?BatchPlan 鐨?terminal status 鍐欏洖 RuntimeState
   - _finalize_batch_after_drained_graph 涓嶅啀鐩存帴淇敼 completed / failed / cancelled 鐘舵€佸悗璋冪敤閫氱敤 batch plan 鎸佷箙鍖栵紱瀹屾垚銆佸け璐ユ垨鍙栨秷鍥句細鍏堟墽琛屽搴?batch.mark_* ToolCallGraph锛屽啀鐢?StatePatch 鏇存柊 batch_plans
   - 鏈疆鍙媶鍙栨秷鍚庣殑缁堟€佸啓鍥烇紝涓嶆敼鍙?runtime command / pause / cancel 鐨勫叆鍙ｈ涔夛紝涔熶笉瑙︾ C++ 鎴栫湡瀹炶皟搴﹀彇娑堥€昏緫
   - 宸ュ叿澶辫触浼氭姏鍑哄苟闃绘 batch_execution_completed 鐢ㄦ埛浜嬩欢锛屼繚鎸佺幇鏈夆€滅粓鎬佺姸鎬佸啓鍏ュけ璐ヤ笉浼瀹屾垚鈥濈殑闂ㄧ璇箟
   - 寮哄寲 drain_tool_graph_queue 涓?cancelled finalize 娴嬭瘯锛岄獙璇佹垚鍔熸壒娆′骇鐢?batch.mark_completed graph锛屽け璐ユ壒娆′骇鐢?batch.mark_failed graph锛屽彇娑堟壒娆′骇鐢?batch.mark_cancelled graph锛屽苟璁板綍 batch_terminal_status_state_persisted

37. Phase 4 鎵规鍒涘缓鑽夋宸叉媶鎴?batch.create ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 batch.create 鍙 planning 宸ュ叿锛岀敤浜庢妸 ordered_items銆乵ax_items_per_batch 涓?absorbed_intervention_ids 杞崲涓?batch draft rows
   - batch.create 鍙啓鍏?custom_batch_facts 鐨?`{plan_id}:created_batches`锛屼笉鐩存帴鍒涘缓姝ｅ紡 batch_plans銆佷笉鍏ラ槦銆佷笉瀵煎叆璧勬簮銆佷笉淇敼 actor锛屼篃涓嶈Е纰扮湡瀹炲紩鎿?
   - plan_batches 涓?enqueue_planned_batches 鍦ㄦ渶缁堟寔涔呭寲 batch_plans / tool_graph_queue 鍓嶏紝鍏堟墽琛?batch.create ToolCallGraph锛屽啀浠?RuntimeState 鐨?created_batches fact 閲嶅缓 BatchPlan dataclass 骞惰蛋 BatchPlanValidator
   - 鐜版湁 runtime.batch.plan_record 涓?runtime.scene_plan.planned_batches.enqueue 浠嶈礋璐ｆ渶缁堢姸鎬佸啓鍏ワ紝鍥犳鏈€缁堟壒娆＄姸鎬佸け璐ユ椂涓嶄細姹℃煋鍐呭瓨 mirror 鎴栬鍚告敹 intervention
   - 寮哄寲 test_runtime_can_plan_multiple_batches_as_state_facts 涓?test_enqueue_planned_batches_only_queues_until_worker_drains锛岄獙璇?custom_batch_facts created_batches銆乥atch.create graph銆佸悗缁寮?batch_plans / queue 鐘舵€佷竴鑷?

38. Phase 4 瀵煎叆鍓?actor import plan 宸叉媶鎴愬彧璇?ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 runtime.actor.plan_import_batch锛屽彧鐢熸垚瀵煎叆鍓嶅璁¤鍒掞紝鍐欏叆 custom_import_facts锛屼笉瀵煎叆 actor銆佷笉鍐欏紩鎿庛€佷笉淇敼鐪熷疄鍦烘櫙
   - 鎵规鎵ц鍥句腑 runtime.actor.plan_import_batch 浣嶄簬 geometry review / environment dependency 涔嬪悗銆乺untime.actor.import_batch 涔嬪墠锛涚湡姝ｅ啓寮曟搸鐨?runtime.actor.import_batch 浠嶆槸 import 绫?requires_write 宸ュ叿
   - runtime.actor.import_batch 鐜板湪鏄惧紡娑堣垂 actor_import_plan锛堟潵鑷?custom_import_facts 鐨?batch scope锛夛紝璁┾€滃噯澶囧鍏ヤ粈涔堛€佸摢浜涜祫婧愬凡 ready銆佹憜鏀捐崏妗堟槸浠€涔堚€濆湪鍐欏叆鍓嶅彲瀹¤
   - import plan 鍙繚鐣?actor_name銆乺eady_count銆乸osition / rotation / scale銆亃one_hint 绛夊畨鍏ㄥ瓧娈碉紝涓嶅啓 provider銆乵odel_path銆乁RL銆乺aw prompt 鎴栫鏈夎矾寰?
   - 寮哄寲 test_runtime_graph_plans_assets_and_placements_before_mock_import銆乀oolRegistry manifest 涓?graph consumes/dependencies 娴嬭瘯锛岄獙璇?import plan 椤哄簭銆乧ustom_import_facts銆乵anifest 鍒嗙被鍜?actor import consume 鍚堢害

39. Phase 4 鎵规瀹℃煡姹囨€诲凡鎷嗘垚 review.summarize_batch ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 runtime.review.summarize_batch锛屽湪 VLM checkpoint 涓?actor import 涔嬪悗鐢熸垚鎵规绾?review summary fact锛屽啓鍏?custom_review_summary_facts
   - 璇ュ伐鍏峰彧姹囨€?geometry review銆乂LM checkpoint銆乤ctor import plan 涓?Runtime actors 鐨勫畨鍏ㄨ鏁板瓧娈碉紝涓嶆墽琛屼慨澶嶃€佷笉绉诲姩 actor銆佷笉鍐欏紩鎿?
   - 鎵规鎵ц鍥句腑 runtime.review.summarize_batch 渚濊禆 runtime.review.vlm_checkpoint銆乺untime.geometry.review 涓?runtime.actor.import_batch锛岀户缁妸 report 鍓嶇殑闅愬紡鑱氬悎鎷嗘垚鍙璁?ToolCall
   - status_summary / generate_report 鐨?review_summary 浼氳鍙?custom_review_summary_facts锛屽苟浠?latest_batch_summaries / batch_summary_count 鏆撮湶鎵规瀹℃煡浜嬪疄锛涘悓涓€ fact 鐨?batch_id 涓?plan_id:batch_id 鍙?key 浼氬幓閲?
   - 寮哄寲 test_runtime_graph_plans_assets_and_placements_before_mock_import銆乀oolRegistry manifest 涓?graph consumes/dependencies 娴嬭瘯锛岄獙璇?review summary 椤哄簭銆乧ustom_review_summary_facts銆乵anifest 鍒嗙被鍜屾姤鍛婅鍙栧彛寰?

40. Phase 4 瀹℃煡璋冩暣寤鸿宸叉媶鎴?review.generate_adjustment_proposal ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 runtime.review.generate_adjustment_proposal锛屽湪 review.summarize_batch 涔嬪悗璇诲彇 geometry review銆乥atch review summary 涓?VLM advisory proposal
   - 璇ュ伐鍏峰彧鎶婂畨鍏ㄧ殑 geometry issue 杞崲鎴愪綆椋庨櫓 layout_adjustment_proposals锛屼笉鎵ц actor move銆佷笉纭璋冩暣銆佷笉鍐欑湡瀹炲紩鎿?
   - 鎵规鎵ц鍥句腑 runtime.review.generate_adjustment_proposal 渚濊禆 runtime.review.summarize_batch銆乺untime.geometry.review 涓?runtime.review.vlm_checkpoint锛屼娇鈥滃鏌ュ悗鏄惁闇€瑕佽皟鏁粹€濇垚涓哄彲鍥炴斁 ToolCall锛岃€屼笉鏄姤鍛婇樁娈典复鏃舵帹鏂?
   - 鏃犲彲鎵ц浣庨闄?delta 鏃讹紝璇ュ伐鍏疯繑鍥?not_needed payload锛屼笉鍒堕€犵┖ proposal锛涙湁 floating / out_of_bounds 绛変綆椋庨櫓闂鏃剁敓鎴愮瓑寰呮埧涓荤‘璁ょ殑 proposal
   - 寮哄寲 review.generate_adjustment_proposal manifest銆乬raph consumes/dependencies銆乨irect ToolCallGraph 琛屼负娴嬭瘯锛屽苟璋冩暣 completed batch 鑷姩 proposal 娴嬭瘯锛岀‘璁よ proposal 鏉ユ簮浜?review ToolCall 鑰屼笉鏄畬鎴愭€佺敤鎴峰叆鍙ｄ簨浠?

41. Phase 5 Runtime 闃熷垪閫夋嫨宸叉媶鎴?queue.select_next_graph ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 runtime.queue.select_next_graph锛岀敤浜庡湪 drain_next_tool_graph 鐪熸鍑洪槦鎵ц鍓嶉€夋嫨涓嬩竴鏉?queued ToolCallGraph
   - 璇ュ伐鍏疯鍙?tool_graph_queue锛屽啓鍏?custom_queue_facts锛岃褰?selected_graph_ref銆乥atch_id銆乹ueued_count 涓?status锛涗笉鎵ц鐩爣 graph銆佷笉淇敼 batch銆佷笉鍐欏紩鎿?
   - drain_next_tool_graph 鍦ㄦ甯稿彲鎵ц闃熷垪璺緞涓厛鎵ц queue.select_next_graph ToolCallGraph锛屽啀鎸?custom_queue_facts 閲岀殑 selected_graph_ref 鎵ц涓氬姟 ToolCallGraph
   - paused / cancelled 璁″垝涓嬬殑闃熼 graph 浠嶄繚鐣欏師瀹夊叏璺緞锛岀洿鎺ヨ繘鍏?_drain_queued_tool_graph 鐨?blocked 澶勭悊锛岀‘淇濆浘鐘舵€佹寔涔呭寲澶辫触涓嶄細琚?queue selection 鎺у埗闈㈠浘鍚炴帀
   - custom_queue_facts 涓嶆毚闇?graph_id 瀛楁鍚嶏紝閬垮厤鐢ㄦ埛鎶ュ憡鎴?Runtime fact 娉勬紡鍐呴儴鎵ц鍥炬爣璇嗭紱娴嬭瘯瑕嗙洊 manifest銆乹ueue fact 涓?paused drain 瀹夊叏鍥炲綊

42. Phase 5 Runtime 闃熷垪鐘舵€佸啓鍥炲凡鎷嗘垚 queue.mark_graph_status ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 runtime.queue.mark_graph_status锛岀敤浜庢寔涔呭寲 queued ToolCallGraph 鐨?running / completed / failed / paused / cancelled 绛夌姸鎬佽浆鎹?
   - _mark_tool_graph_queue_item 淇濈暀涓哄唴閮ㄥ敮涓€璋冪敤鐐癸紝浣嗗唴閮ㄦ敼涓烘墽琛?confirmed 鐨?runtime-queue-control ToolCallGraph锛屼笉鍐嶆墜鍐?tool_graph_queue StatePatch
   - 璇ュ伐鍏疯鍙?tool_graph_queue锛屽啓鍥?tool_graph_queue锛屼繚鐣?started_at / completed_at / updated_at 绛夐槦鍒楃敓鍛藉懆鏈熷瓧娈碉紱涓嶆墽琛岀洰鏍?graph銆佷笉淇敼 batch銆佷笉鍐欏紩鎿?
   - 鍘熸湁 tool_graph_queue_state_persisted / tool_graph_queue_update_failed OperationLog 璇箟淇濈暀锛涚姸鎬佸啓鍥炲け璐ヤ粛浼氭姏閿欙紝閬垮厤闃熷垪鍥炬湭钀界洏鍗寸户缁彂瀹屾垚浜嬩欢
   - 娴嬭瘯瑕嗙洊 manifest consumes/produces 濂戠害銆佹甯?drain 璺緞涓?runtime.queue.mark_graph_status 鐨?ToolCall 鎵ц锛屼互鍙?queue state failure 鐨勬棫瀹夊叏璇箟

43. Phase 5 鎵规寮€濮嬬姸鎬佸凡鎷嗘垚 batch.mark_started ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 batch.mark_started锛岀敤浜庢妸 Runtime BatchPlan 浠?planned 鍒囧埌 executing
   - _mark_batch_started_by_tool_graph 涓嶅啀鍏堟敼鍐呭瓨 batch 鍐嶈蛋閫氱敤 plan_record锛岃€屾槸鎵ц confirmed 鐨?batch.mark_started ToolCallGraph锛屽啀浠?RuntimeState 鍥炶 batch mirror
   - batch.mark_started 鍙啓 batch_plans锛屼笉鎵ц鐩爣 graph銆佷笉璇锋眰璧勬簮銆佷笉瀵煎叆 actor銆佷笉鍐欑湡瀹炲紩鎿庯紱batch_execution_started RuntimeEvent 浠嶅湪鐘舵€佽惤鐩樻垚鍔熷悗鍙戝嚭
   - 鐘舵€佸啓鍏ュけ璐ヤ細浜х敓 batch_started_status_state_persist_failed 骞舵姏閿欙紝涓嶄細缁х画鍙?batch_started / graph started 杩欑被璇鐢ㄦ埛鐨勫畬鎴愪俊鍙?
   - 娴嬭瘯瑕嗙洊 manifest write/user-visible failure 濂戠害锛屼互鍙?drain 璺緞涓?batch.mark_started ToolCall 鐨勬墽琛?

44. Phase 5 鐩存帴 ToolCallGraph 鍏ラ槦璺緞宸叉媶鎴?queue.enqueue_graph ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 runtime.queue.enqueue_graph锛岀敤浜庢妸宸叉竻娲楃殑 ToolCallGraph fact 涓?queue item 鍘熷瓙鍐欏叆 tool_graphs / tool_graph_queue
   - _enqueue_tool_graph 涓嶅啀鐩存帴 apply_patch 鍐?tool_graphs + tool_graph_queue锛岃€屾槸鎵ц confirmed 鐨?runtime.queue.enqueue_graph ToolCallGraph锛屽啀淇濈暀鍘?tool_graph_queue_state_persisted / failed 浜嬩欢璇箟
   - 璇ュ伐鍏峰彧鎺ユ敹 ToolCallGraphValidator.safe_graph_fact(graph) 鍜?queue_item锛屼笉鎺ユ敹 raw graph / raw args / provider / prompt / model_path锛涘け璐ユ椂浠嶆姏閿欏苟闃绘 tool_graph_queued / batch_execution_queued 绛変笟鍔′簨浠?
   - runtime.scene_plan.enqueue 杩欑被鈥滅‘璁ゆ柟妗堟椂鍘熷瓙鍐?plan + batch + queue鈥濈殑宸ュ叿璺緞鏆傛椂淇濈暀锛岀敤浜庝繚闅滅‘璁ゅ叆闃熺殑鍘熷瓙鎬э紱鏈潯瑕嗙洊 worker / 鍐呴儴鐩存帴 _enqueue_tool_graph 璺緞
   - 娴嬭瘯瑕嗙洊 manifest write/user-visible failure 濂戠害銆佺洿鎺?_enqueue_tool_graph 璺緞涓?runtime.queue.enqueue_graph 鐨?ToolCall 鎵ц锛屼互鍙?enqueue/queue 鍘熷瓙鎬у洖褰?

45. Phase 5 鐩爣鎵ц鍥剧姸鎬佽褰曞凡鎷嗘垚 queue.record_graph_state ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 runtime.queue.record_graph_state锛岀敤浜庢妸宸叉竻娲楃殑鐩爣 ToolCallGraph fact 鍐欏叆 tool_graphs
   - _persist_tool_graph_state 涓嶅啀鐩存帴 apply_patch 鍐?tool_graphs锛岃€屾槸鎵ц confirmed 鐨?runtime.queue.record_graph_state ToolCallGraph锛屽啀淇濈暀鍘?tool_graph_state_recorded / failed 浜嬩欢璇箟
   - 璇ュ伐鍏峰彧璁板綍鈥滅洰鏍囦笟鍔″浘鈥濈殑鐘舵€佸揩鐓э紝灏ゅ叾瑕嗙洊 paused / cancelled / blocked drain 璺緞锛汿oolCallGraphExecutor 鍐呴儴鐢ㄤ簬璁板綍鑷韩鎵ц杩囩▼鐨?_persist_graph 浠嶄繚鐣欎负鎵ц鍣ㄥ唴閮ㄦ満鍒讹紝閬垮厤閫掑綊宸ュ叿鍖?
   - 宸ュ叿鍙傛暟鍙帴鏀?ToolCallGraphValidator.safe_graph_fact(graph) 涓?target_graph_ref锛屼笉鎺ユ敹 raw graph / raw args / provider / prompt / model_path锛涘け璐ユ椂浠嶆姏閿欏苟闃绘鍚庣画 blocked / completed 鐢ㄦ埛浜嬩欢
   - 娴嬭瘯瑕嗙洊 manifest write/user-visible failure 濂戠害銆乸aused drain 璺緞涓?runtime.queue.record_graph_state 鐨?ToolCall 鎵ц锛屼互鍙?queue state failure 鍥炲綊

46. Phase 5 澶栭儴 RuntimeEvent 鍐欏叆宸叉媶鎴?runtime.event.emit ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 runtime.event.emit锛岀敤浜庢妸宸查€氳繃 RuntimeEventValidator 娓呮礂鐨勭敤鎴峰彲瑙佷簨浠跺啓鍏?runtime_events
   - AgentRuntime.emit_runtime_event 涓嶅啀鐩存帴 apply_patch 鍐?runtime_events锛岃€屾槸鎵ц confirmed 鐨?runtime.event.emit ToolCallGraph锛屽啀淇濈暀鍘?runtime_event_emitted / runtime_event_emit_failed 浜嬩欢璇箟
   - runtime.event.emit 琚姞鍏ョ敓鍛藉懆鏈熸姭闇叉姂鍒跺垪琛紝閬垮厤鈥滃彂杩涘害浜嬩欢鏃跺張鐢熸垚杩涘害浜嬩欢鈥濈殑閫掑綊鍣０锛汿oolCallGraphExecutor 鍐呴儴 tool_call_started / tool_result_message / blocked / stopped 浜嬩欢浠嶄繚鐣欎负鎵ц鍣ㄥ唴閮ㄦ満鍒讹紝鏆備笉閫掑綊宸ュ叿鍖?
   - 宸ュ叿鍙傛暟鍙帴鏀?event_row 涓?room_id锛宔vent_row 蹇呴』閫氳繃 RuntimeEventValidator.validate_row锛屼笉鎺ユ敹 raw payload / provider / prompt / URL / API key / tool args
   - 娴嬭瘯瑕嗙洊 manifest write/user-visible failure 濂戠害銆丷untimeEvent 瀹夊叏 payload 鎸佷箙鍖栥€佹寔涔呭寲澶辫触鏄惧紡杩斿洖锛屼互鍙?runtime_events 鍙鏌ヨ涓嶄細鍒涘缓 ScenePlan

47. Phase 8 鏃?MasterAgent 鏁翠綋 compose 鐩村叆鍙ｅ凡琛ラ粯璁ら樆鏂祴璇曪細
   - `agent_adapter.MasterAgent._handle_scene_compose()` 宸叉湁 AgentRuntime migration guard锛岄粯璁?`ALLOW_LEGACY_MAIN_WORKFLOW=0` / `OLD_WORKFLOW_DIRECT_ENTRY_DISABLED=1` 鏃惰繑鍥?Runtime 涓绘帶鎻愮ず锛屼笉鍐嶅疄渚嬪寲 `SceneComposer` 杩涘叆鏃т富鎺ч摼璺?
   - 鏂板 `test_master_agent_direct_scene_compose_blocks_default_legacy_main_workflow`锛屾妸 RoleAgent / MasterAgent 鐩磋繛 `SceneComposer.compose()` 鐨勯粯璁ょ鐢ㄨ涓虹撼鍏?`test_lanchat_runtime_guard.py`
   - 杩欎竴姝ヤ笉鏀瑰彉杩愯鏃朵富閾捐矾锛屽彧鎶娾€滄櫘閫?Agent 鍏ュ彛涓嶅緱閲嶆柊鏆撮湶鏃?workflow 涓绘帶鈥濈殑涓嶅彉閲忓浐鍖栦负娴嬭瘯锛岄槻姝㈠悗缁敼鍔ㄦ妸 `_handle_scene_compose` 閲嶆柊鎺ュ洖鏃?compose

48. Phase 8 鏃?MasterAgent 鏄惧紡鏂囦欢瀵煎叆鐩村叆鍙ｅ凡琛ラ粯璁ら樆鏂祴璇曪細
   - `agent_adapter.MasterAgent.__call__()` 涓樉寮忔ā鍨嬫枃浠惰矾寰勪細浼樺厛杩涘叆 `_handle_direct_import()`锛涜璺緞宸叉湁 AgentRuntime migration guard锛岄粯璁や笉鍏佽缁曡繃 Runtime 鐩存帴璋冪敤鏃?`import_model` 宸ュ叿鍐欏紩鎿?
   - 鏂板 `test_master_agent_direct_file_import_blocks_default_legacy_main_workflow`锛屾妸鈥滄枃浠惰矾寰勫鍏ヤ篃蹇呴』鍏堣繘鍏?Runtime / 鏂规纭閾捐矾鈥濈殑绾︽潫绾冲叆 `test_lanchat_runtime_guard.py`
   - 杩欎竴姝ヤ笉鍒犻櫎鐩存帴瀵煎叆鑳藉姏锛屽彧闃叉鏅€?Agent 鍏ュ彛鍦ㄩ粯璁?Runtime 涓绘帶妯″紡涓嬬粫杩?ToolCallGraph / RuntimeGuard 鐩存帴鍐欏満鏅?

49. Phase 8 鐩存帴 engine-write 鏃у叆鍙ｅ凡绾冲叆鎬婚棬绂侊細
   - `verify_ultimate_plan.py` 鏂板 static direct engine-write entry gate锛屾壂鎻?`agent_adapter.py` 涓?`_handle_direct_import()` 涓?`_handle_edit()` 鏄惁鍦ㄨЕ杈炬棫 `import_model` / 鍦烘櫙 actor 璇诲彇鍐欏叆閾捐矾鍓嶇粡杩?AgentRuntime migration guard
   - 璇ラ棬绂佽姹?guard 鍓嶇紑鍖呭惈 `_legacy_main_workflow_allowed()` 涓?`AGENT_RUNTIME_REQUIRED_MESSAGE`锛岄伩鍏嶅悗缁妸鏄惧紡鏂囦欢瀵煎叆銆佸揩閫熺紪杈戞垨鑿滃寘 agentic 宸ュ叿寰幆閲嶆柊鏆撮湶涓洪粯璁ょ敤鎴峰啓鍏ュ彛
   - 杩欎竴姝ユ妸鈥滀笟鍔?Agent 涓嶅緱缁曡繃 ToolCallGraph / RuntimeGuard 鐩存帴鍐欏満鏅€濈殑绾︽潫浠庡崟鍏冩祴璇曟彁鍗囦负 `verify_ultimate_plan.py` 鎬婚棬绂?

50. Phase 8 鏃?ProgressiveWorkflow 涓绘帶鐩磋揪鍏ュ彛宸茬撼鍏ユ€婚棬绂侊細
   - `verify_ultimate_plan.py` 鏂板 static direct ProgressiveWorkflow entry gate锛屾壂鎻?services / `cai_extensions/agent` / `main.py` 涓殑 `run_progressive_workflow` 涓?`progressive_compose(` 鐩磋繛璋冪敤
   - 褰撳墠鍙厑璁告棫鑳藉姏鏈綋 `scene_composer_progressive.py` / `scene_session.py` 鍜岃繃娓℃湡 legacy `scene_composer.py` 鍐呴儴璋冪敤瀛樺湪锛涙櫘閫氱敤鎴峰叆鍙ｃ€丩ANChat worker銆丠ost executor銆丄gentRuntime 鍖呬笉寰楁柊澧炵洿杩?progressive 涓绘帶
   - 闂ㄧ浼氳烦杩?AgentRuntime 鍐呴儴鈥滅鐢ㄦ棫涓绘帶 token鈥濇竻鍗曡繖绫诲瓧绗︿覆澹版槑锛岄伩鍏嶆妸闃插洖娼鍒欐湰韬鍒や负鏃у叆鍙?
   - 杩欎竴姝ユ妸鈥滀笉鑳芥妸 `run_progressive_workflow()` 鍖呮垚鏂扮殑澶у伐鍏锋垨閲嶆柊鏆撮湶缁欐櫘閫氬叆鍙ｂ€濈殑绾︽潫鍥哄寲涓烘€婚棬绂侊紝涓哄悗缁户缁媶 batch / import / review 宸ュ叿鐣欏嚭瀹夊叏杈圭晫

51. RuntimeState.apply_patch 鐩村啓杈圭晫宸茬撼鍏ユ€婚棬绂侊細
   - `verify_ultimate_plan.py` 鏂板 static RuntimeState apply_patch boundary gate锛岀敤 AST 鎵弿 `agent_runtime/core.py` 涓墍鏈?`apply_patch()` 璋冪敤
   - 褰撳墠鍙厑璁?`ToolCallGraphExecutor.execute()` 鐨?ToolResult StatePatch 鍚堝苟銆佹墽琛屽櫒鐢熷懡鍛ㄦ湡 RuntimeEvent 鍐欏叆銆佷互鍙?`_persist_graph()` 鍐呴儴鍥剧姸鎬佹寔涔呭寲淇濈暀鐩存帴鍐欏叆锛涜繖浜涘睘浜庢墽琛屽櫒鍐呴儴鏈哄埗锛屾殏涓嶉€掑綊宸ュ叿鍖?
   - 浠讳綍 AgentRuntime 澶栧眰涓氬姟鏂规硶銆佸叆鍙ｈ矾鐢便€佹姤鍛婄敓鎴愩€侀槦鍒楁帶鍒舵垨鏃?workflow adapter 鏂板鐩存帴 `RuntimeState.apply_patch` 閮戒細瑙﹀彂鎬婚棬绂佸け璐ワ紝蹇呴』鏀逛负 ToolCallGraph + ToolResult / StatePatch 璺緞
   - 杩欎竴姝ユ妸鈥淭oolResult 涓嶇洿鎺ユ敼鐘舵€侊紝鍙湁 RuntimeState.apply_patch 鑳藉悎骞讹紱涓氬姟鐘舵€佸啓鍏ュ繀椤荤粡宸ュ叿鍥锯€濈殑杈圭晫鍥哄寲涓哄彲閲嶅楠岃瘉鐨勯潪 native 闂ㄧ

52. Phase 5/Report OperationLog replay 姹囨€诲凡鎷嗘垚 runtime.report.operation_replay_summary ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 `runtime.report.operation_replay_summary`锛屽湪 `generate_report()` 缁勮鐢ㄦ埛鎶ュ憡鍓嶏紝鎶?OperationLog replay summary 鍐欏叆 `custom_report_facts`
   - `generate_report()` 涓嶅啀鐩存帴璋冪敤 `_operation_replay_summary_for_report()` 浣滀负鏈€缁堟姤鍛婁簨瀹炴潵婧愶紝鑰屾槸鍏堟墽琛屽崟鑺傜偣 ToolCallGraph锛屽啀浠?RuntimeState 璇诲彇宸茶褰曠殑 report fact
   - 璇ュ伐鍏峰彧璇诲彇 OperationLog 涓?RuntimeState銆佸啓鍏ュ畨鍏ㄧ殑 `custom_report_facts`锛屼笉瑙︾寮曟搸銆佷笉淇敼 actor銆佷笉璋冪敤鏃?workflow锛屼篃涓嶆毚闇?`tool_call_id` / `patch_id` / provider / prompt / path
   - 宸ュ叿澶辫触浼氳褰?`runtime_report_operation_replay_summary_failed` 骞堕樆鏂?`user_report_generated` / `report_ready`锛岄伩鍏嶆姤鍛婂湪缂哄け RuntimeState report fact 鏃朵吉瑁呭畬鎴愶紱鎴愬姛鏃惰褰?`runtime_report_operation_replay_summary_recorded`
   - 寮哄寲 `test_generate_report_contains_safe_operation_replay_summary`銆乣test_generate_report_replay_summary_failure_blocks_user_report` 涓?ToolRegistry manifest 娴嬭瘯锛岄獙璇佹姤鍛?replay summary 宸茶惤鍏?RuntimeState fact 涓旀柊宸ュ叿鍏峰 write/user-visible-failure/produces_state 濂戠害

53. Phase 5/Report ToolRegistry manifest 鏌ヨ宸叉媶鎴?runtime.tool_manifest.snapshot ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 `runtime.tool_manifest.snapshot`锛屽湪 `tool_manifest()` 杩斿洖宸ュ叿鑳藉姏娓呭崟鍓嶏紝鎶?ToolRegistry manifest / capability summary 鍐欏叆 `custom_report_facts`
   - `tool_manifest()` 涓嶅啀鐩存帴浠?registry 璇诲畬鍗宠繑鍥烇紝鑰屾槸鍏堟墽琛屽崟鑺傜偣 ToolCallGraph锛屽啀浠?RuntimeState 鐨?`tool_manifest:*` fact 璇诲彇 summary 涓?tools
   - 璇ュ伐鍏峰彧璁板綍瀹夊叏 manifest 蹇収锛屼笉鍒涘缓 ScenePlan銆佷笉鍏ラ槦銆佷笉鍐欏紩鎿庛€佷笉瑙︾鏃?workflow锛沵anifest fact 涓嶅寘鍚?handler銆乸rovider銆乸rompt銆乸ath銆乁RL 鎴?raw payload
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸叉墿灞曟鏌?`tool_manifest()` 蹇呴』璧?`runtime.tool_manifest.snapshot`锛岀姝㈠洖閫€涓虹洿鎺?registry 璇诲彇
   - 寮哄寲 ToolRegistry manifest 娴嬭瘯锛岄獙璇?`tool_manifest:all` 宸茶惤鍏?RuntimeState fact 涓旀柊宸ュ叿鍏峰 write/user-visible-failure/produces_state 濂戠害

54. Phase 5/Status Runtime 鐘舵€佹煡璇㈠凡鎷嗘垚 runtime.status_summary.snapshot ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 `runtime.status_summary.snapshot`锛屽湪 `status_summary()` 杩斿洖鐢ㄦ埛/GM 鍙鐘舵€佸墠锛屾妸宸叉竻娲?Runtime 鐘舵€佹憳瑕佸啓鍏?`custom_report_facts`
   - `status_summary()` 浠嶄繚鎸佷笉鍒涘缓 ScenePlan銆佷笉鍐欑敤鎴锋姤鍛娿€佷笉鍙?`report_ready` 鐨勬煡璇㈣涔夛紱浣嗚繑鍥炲€煎繀椤诲厛缁忓崟鑺傜偣 ToolCallGraph 钀藉叆 RuntimeState fact锛屽啀浠?fact 璇诲洖
   - `status_summary()` 鐨勫伐鍏疯兘鍔涙憳瑕佷笉鍐嶇洿鎺ヨ `registry.capability_summary()`锛岃€屾槸澶嶇敤 `runtime.tool_manifest.snapshot` 鐨勫畨鍏?summary锛屽苟杩囨护鎺夊唴閮ㄥ伐鍏峰悕鍒楄〃鍚庢姭闇?
   - 宸ュ叿澶辫触浼氳褰?`runtime_status_summary_snapshot_failed` 骞堕樆鏂姸鎬佽繑鍥烇紝閬垮厤缂哄け RuntimeState status fact 鏃朵吉瑁呮煡璇㈡垚鍔燂紱鎴愬姛鏃惰褰?`runtime_status_summary_snapshot_recorded`
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸叉墿灞曟鏌?`status_summary()` 蹇呴』璧?`runtime.status_summary.snapshot`锛屽苟绂佹鐩存帴璇诲彇 registry capability summary
   - 寮哄寲 status summary / ToolRegistry manifest 娴嬭瘯锛岄獙璇佸唴閮?`runtime-status-summary` 鎴块棿涓殑 `*:runtime_status_summary` fact 宸茶惤鍏?RuntimeState 涓旀柊宸ュ叿鍏峰 write/user-visible-failure/produces_state 濂戠害

55. Phase 5/Status Provider readiness 鐘舵€佹煡璇㈠凡鎷嗘垚 runtime.resource_status.snapshot ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 `runtime.resource_status.snapshot`锛屽湪 `provider_status()` 杩斿洖璧勬簮閫氶亾鐘舵€佸墠锛屾妸宸叉竻娲?provider readiness / engine write / message delivery 鎽樿鍐欏叆 `custom_report_facts`
   - `provider_status()` 淇濈暀鍘熸湁 `runtime.provider_readiness.publish` 閫昏緫锛岀户缁妸 provider readiness 鍙戝竷鍒颁笟鍔℃埧闂?RuntimeState锛涙柊澧?provider status 蹇収鍐欏叆鍐呴儴 `runtime-provider-status` 鎴块棿锛岄伩鍏嶆薄鏌撲笟鍔℃埧闂?`tool_graphs` 鍜岀敤鎴峰彲瑙佽繘搴?
   - 澶栭儴 SeedPlan 鎵句笉鍒?runtime plan 鐨勫垎鏀篃蹇呴』鍐欏叆 provider status fact锛岄伩鍏嶁€滄棤 runtime plan鈥濈姸鎬佺粫杩?RuntimeState 浜嬪疄婧?
   - 宸ュ叿澶辫触浼氳褰?`runtime_provider_status_snapshot_failed` 骞堕樆鏂姸鎬佽繑鍥烇紱鎴愬姛鏃惰褰?`runtime_provider_status_snapshot_recorded`
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸叉墿灞曟鏌?`provider_status()` 蹇呴』璧?`runtime.resource_status.snapshot`
   - 寮哄寲 provider status / ToolRegistry manifest 娴嬭瘯锛岄獙璇佹甯告煡璇€佸閮?plan 鏌ヨ銆佹湭鐭ュ閮?plan 鏌ヨ鍧囧凡钀藉叆鍐呴儴 `runtime-provider-status` fact锛屼笖涓嶄細鎶?snapshot ToolCallGraph 鍐欏叆涓氬姟鎴块棿

56. Phase 5/Replay OperationLog 澶嶇洏鏌ヨ宸叉媶鎴?runtime.operation_replay.snapshot ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 `runtime.operation_replay.snapshot`锛屽湪 `operation_replay()` 杩斿洖璇婃柇/澶嶇洏缁撴灉鍓嶏紝鎶婂凡娓呮礂 replay 缁撴灉鍐欏叆 `custom_report_facts`
   - `operation_replay()` 淇濈暀 `runtime_operation_replay_requested` 涓?`runtime_operation_replay_queried` 瀹¤浜嬩欢锛屼絾鏈€缁堣繑鍥炲€煎繀椤诲厛缁忓唴閮?`runtime-operation-replay` 鎴块棿鐨?RuntimeState fact 璇诲洖
   - replay snapshot 涓嶅啓鐢ㄦ埛鎶ュ憡銆佷笉鍙?`report_ready`銆佷笉姹℃煋涓氬姟鎴块棿 `tool_graphs`锛屽彧浣滀负璇婃柇浜嬪疄婧愬浐鍖?
   - 宸ュ叿澶辫触浼氳褰?`runtime_operation_replay_snapshot_failed` 骞堕樆鏂?replay 杩斿洖锛涙垚鍔熸椂璁板綍 `runtime_operation_replay_snapshot_recorded`
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸叉墿灞曟鏌?`operation_replay()` 蹇呴』璧?`runtime.operation_replay.snapshot`
   - 寮哄寲 operation replay / ToolRegistry manifest 娴嬭瘯锛岄獙璇?`runtime-operation-replay` 鍐呴儴 fact 宸茶惤鍏?RuntimeState 涓旀柊宸ュ叿鍏峰 write/user-visible-failure/produces_state 濂戠害

57. Phase 5/GM Runtime 涓婁笅鏂囨€荤粨宸叉媶鎴?runtime.gm_summary.snapshot ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 `runtime.gm_summary.snapshot`锛屽湪 `gm_summary()` 杩斿洖 GM 鍙涓婁笅鏂囨憳瑕佸墠锛屾妸宸叉竻娲楁憳瑕佸啓鍏?`custom_report_facts`
   - `gm_summary()` 浠嶅厛璇诲彇 `status_summary()`锛岀户鎵?RuntimeState / OperationLog 鐘舵€佷簨瀹炴簮锛涗絾鏈€缁堣繑鍥炲€煎繀椤诲厛缁忓唴閮?`runtime-gm-summary` 鎴块棿鐨?RuntimeState fact 璇诲洖
   - GM summary snapshot 涓嶅垱寤?ScenePlan銆佷笉鍐欑敤鎴锋姤鍛娿€佷笉鍙?`report_ready`銆佷笉姹℃煋涓氬姟鎴块棿 `tool_graphs`锛屽彧鍥哄寲 GM/Planner 鍙敤鐨勪笂涓嬫枃鎽樿浜嬪疄
   - 宸ュ叿澶辫触浼氳褰?`runtime_gm_summary_snapshot_failed` 骞惰 `runtime_gm_summary` action 杩斿洖 unavailable summary锛涙垚鍔熸椂璁板綍 `runtime_gm_summary_snapshot_recorded` 鍜?`runtime_gm_summary_exported`
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸叉墿灞曟鏌?`gm_summary()` 蹇呴』璧?`runtime.gm_summary.snapshot`
   - 寮哄寲 GM summary / ToolRegistry manifest 娴嬭瘯锛岄獙璇?`runtime-gm-summary` 鍐呴儴 fact 宸茶惤鍏?RuntimeState 涓旀柊宸ュ叿鍏峰 write/user-visible-failure/produces_state 濂戠害

58. Phase 5/UI RuntimeEvent 鏌ヨ宸叉媶鎴?runtime.events.snapshot ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 `runtime.events.snapshot`锛屽湪 `runtime_events` / `user_visible_events` action 杩斿洖鐢ㄦ埛鍙浜嬩欢鍒楄〃鍓嶏紝鎶婂凡娓呮礂浜嬩欢鍒楄〃鍐欏叆 `custom_report_facts`
   - `user_visible_events()` 缁х画浣滀负鍐呴儴鍙 helper锛涘閮?action 蹇呴』鍏堢粡鍐呴儴 `runtime-events-snapshot` 鎴块棿鐨?RuntimeState fact 璇诲洖锛岄伩鍏?UI 浜嬩欢鎶湶鍙瓨鍦ㄤ簬鍑芥暟杩斿洖鍊奸噷
   - Runtime events snapshot 涓嶅垱寤?ScenePlan銆佷笉鍐欑敤鎴锋姤鍛娿€佷笉鍙?`report_ready`銆佷笉姹℃煋涓氬姟鎴块棿 `tool_graphs`锛涘彧鍥哄寲鈥滅敤鎴疯繖涓€鍒诲彲瑙佸摢浜?RuntimeEvent鈥濈殑瀹夊叏浜嬪疄
   - 宸ュ叿澶辫触浼氳褰?`runtime_events_snapshot_failed`锛屽苟璁?`runtime_events` action 杩斿洖绌轰簨浠朵笌 `recorded=False`锛屼笉杩斿洖鏈惤 RuntimeState fact 鐨勪簨浠跺垪琛紱鎴愬姛鏃惰褰?`runtime_events_snapshot_recorded`
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸叉墿灞曟鏌?`handle_message()` 鐨?runtime_events action 蹇呴』璧?`runtime.events.snapshot`
   - 寮哄寲 runtime_events action / ToolRegistry manifest 娴嬭瘯锛岄獙璇?`runtime-events-snapshot` 鍐呴儴 fact 宸茶惤鍏?RuntimeState锛屼笖涓嶆硠闇?provider銆乼ool_name銆乁RL銆乸rompt銆乪vent_id 鎴栧唴閮?tool graph 淇℃伅

59. Phase 5/Sync 澶氫汉鍚屾鐘舵€佹煡璇㈠凡鎷嗘垚 runtime.sync_status.snapshot ToolCall锛?
   - AgentRuntime ToolRegistry 鏂板 `runtime.sync_status.snapshot`锛屽湪 `sync_status` / `runtime_sync_status` / `sync_summary` action 杩斿洖澶氫汉鍚屾鍋ュ悍搴﹀墠锛屾妸鍚屾鐘舵€併€佸悓姝?replay 鎽樿銆佹秷鎭姇閫掓憳瑕佸拰鏈€鏂板彲瑙?RuntimeEvent 鍐欏叆 `custom_report_facts`
   - `sync_status` action 浠嶄粠 `status_summary()` 涓?`operation_replay()` 璇诲彇 RuntimeState / OperationLog 浜嬪疄婧愶紱浣嗘渶缁堣繑鍥炲€煎繀椤诲厛缁忓唴閮?`runtime-sync-status` 鎴块棿鐨?RuntimeState fact 璇诲洖
   - Sync status snapshot 涓嶅垱寤?ScenePlan銆佷笉鍐欑敤鎴锋姤鍛娿€佷笉鍙?`report_ready`銆佷笉姹℃煋涓氬姟鎴块棿 `tool_graphs`锛涘彧鍥哄寲鈥滃浜?actor / asset / peer / delivery 鍚屾鐘舵€佹煡璇⑩€濈殑瀹夊叏浜嬪疄
   - 宸ュ叿澶辫触浼氳褰?`runtime_sync_status_snapshot_failed` 涓?`runtime_sync_status_export_failed`锛屽苟璁?sync_status action 杩斿洖绌哄悓姝ョ姸鎬侊紝涓嶈繑鍥炴湭钀?RuntimeState fact 鐨勫悓姝ユ憳瑕侊紱鎴愬姛鏃惰褰?`runtime_sync_status_snapshot_recorded` 鍜?`runtime_sync_status_exported`
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸叉墿灞曟鏌?`handle_message()` 鐨?sync_status action 蹇呴』璧?`runtime.sync_status.snapshot`
   - 寮哄寲 sync_status action / ToolRegistry manifest 娴嬭瘯锛岄獙璇?`runtime-sync-status` 鍐呴儴 fact 宸茶惤鍏?RuntimeState锛屼笖涓嶆硠闇?message_id銆乧orrelation_id銆乻ource_user_id銆乸rovider銆乁RL 鎴?prompt

60. Phase 5/Sync 鏈槧灏?external SeedPlan 鐨勭姸鎬佹煡璇篃宸叉敹鍙ｅ埌 runtime.sync_status.snapshot锛?
   - `sync_status` action 鎼哄甫 `external_plan_id` 浣嗘壘涓嶅埌瀵瑰簲 Runtime plan 鏃讹紝涓嶅啀鐩存帴杩斿洖鈥渘o mapped Runtime plan鈥濓紝鑰屾槸鍏堟妸绌哄悓姝ョ姸鎬併€佸畨鍏ㄦ彁绀哄拰澶辫触鍘熷洜鍐欏叆鍐呴儴 `runtime-sync-status` 鎴块棿鐨?`custom_report_facts`
   - 璇ュ垎鏀户缁笉鍥為€€ active plan锛岄伩鍏嶆煡璇竴涓け鏁?鏃?SeedPlan 鏃惰璇诲綋鍓嶆椿璺冭鍒掔殑 actor / asset / peer 鍚屾鐘舵€?
   - snapshot 澶辫触鏃惰褰?`runtime_sync_status_snapshot_failed` 涓?`runtime_sync_status_export_failed`锛屽苟杩斿洖 RuntimeState 鎸佷箙鍖栧け璐ユ彁绀猴紝涓嶈繑鍥炴湭钀?fact 鐨勭姸鎬?
   - 寮哄寲 `test_sync_status_action_rejects_unknown_external_plan_without_active_fallback`锛岄獙璇佹湭鐭?external plan 鐨?sync status 缁撴灉涔熸潵鑷?`runtime-sync-status` fact锛屼笖涓嶄細娉勯湶宸叉湁璁″垝 actor

61. Phase 5/Scene Snapshot 鐢ㄦ埛鍙鐘舵€佽繑鍥炲凡绉婚櫎 ToolCallGraph 鑺傜偣缁嗚妭锛?
   - `refresh_scene_snapshot()` 鍐呴儴浠嶉€氳繃 `runtime.scene.snapshot` ToolCallGraph 璇诲彇鐪熷疄/妯℃嫙寮曟搸蹇収锛屽苟鎶?`engine_scene_snapshots`銆乣observed_actors`銆乣actors` 鍐欏叆 RuntimeState
   - `handle_message(action=scene_snapshot_status)` 涓嶅啀鎶婂唴閮?`graph.nodes`銆乼ool args 鎴?tool_name 杩斿洖缁欑敤鎴峰彲瑙?action 缁撴灉锛屽彧杩斿洖 `graph.status`銆佸畨鍏?`snapshot_summary` 涓庢竻娲楀悗鐨?RuntimeEvent
   - 杩欎竴姝ヤ繚鐣欏唴閮ㄨ皟璇曟柟娉曠殑璇︾粏 graph 杩斿洖锛岄伩鍏嶅奖鍝?Runtime 鍐呴儴娴嬭瘯鍜?provider adapter 楠岃瘉锛涗絾鑱婂ぉ瀹?/ action 鏌ヨ璺緞涓嶅啀鏆撮湶 ToolCallGraph 鑺傜偣缁撴瀯
   - 寮哄寲 scene snapshot status 娴嬭瘯锛岄獙璇佹垚鍔熴€佸け璐ャ€佸紓甯稿拰 active scene name 鍒嗘敮鍧囦笉杩斿洖 `graph.nodes`锛屽悓鏃?RuntimeState 涓殑 engine snapshot / observed actor 浜嬪疄浠嶆纭惤鐩?

62. Phase 6/Layout Adjustment 鐢ㄦ埛鍙 action 杩斿洖宸茬Щ闄?ToolCallGraph 鑺傜偣缁嗚妭锛?
   - `propose_layout_adjustment()` 涓?`confirm_layout_adjustment()` 鍐呴儴浠嶉€氳繃 `runtime.layout.adjust_propose` / `runtime.layout.apply` ToolCallGraph 鍐欏叆 `layout_adjustment_proposals` 涓庝綆椋庨櫓 actor transform 缁撴灉
   - `handle_message(action=layout_adjustment/final_adjustment_request/confirm_layout_adjustment)` 涓嶅啀鎶婂唴閮?`graph.nodes`銆乼ool args 鎴?tool_name 杩斿洖缁欒亰澶╁ / action 璋冪敤鏂癸紝鍙繑鍥?`graph.status`銆乸lan銆乸roposal 鍜屽畨鍏?message
   - 璇ュ垏鐗囦繚鎸佸唴閮?helper 鐨勮缁?graph / state 杩斿洖锛岀户缁湇鍔?Runtime 鍐呴儴娴嬭瘯銆佸洖鏀惧拰鎵ц鍣ㄨ皟璇曪紱鍙敹绐勭敤鎴峰彲瑙佸叆鍙ｇ殑娉勯湶闈?
   - 寮哄寲甯冨眬寤鸿鐢熸垚銆佺‘璁ゆ垚鍔熴€佺‘璁ゅけ璐ヤ笌寮傚父鍒嗘敮娴嬭瘯锛岄獙璇?action 杩斿洖涓嶅寘鍚?`graph.nodes`锛屼笖 RuntimeState 涓殑 proposal / actor facts 浠嶆纭惤鐩?

63. Phase 6/Delete Advisory 鐢ㄦ埛鍙鎵ц杩斿洖宸茬Щ闄?ToolCallGraph 鑺傜偣缁嗚妭锛?
   - `execute_confirmed_delete_advisory()` 鍐呴儴浠嶉€氳繃 `runtime.delete_advisory.apply` ToolCallGraph 鎵ц宸茬‘璁ょ殑浣庨闄?涓闄╁垹闄ゅ缓璁紝骞跺啓鍏?actor deleted / sync lifecycle facts
   - `handle_message(action=execute_confirmed_delete_advisory)` 涓嶅啀鎶婂唴閮?`graph.nodes`銆乼ool args 鎴?tool_name 杩斿洖缁欒皟鐢ㄦ柟锛屽彧杩斿洖 `graph.status`銆乸roposal銆乻tatus summary 鍜屽畨鍏?message
   - 淇濈暀鍐呴儴 helper 鐨勮缁?graph 杩斿洖锛岀户缁湇鍔?Runtime 鎵ц鍣ㄦ祴璇曘€乼ool_call_succeeded 杩借釜鍜屽洖鏀捐瘖鏂紱鏅€氳亰澶╁ / action 璺緞鍙湅瀹夊叏鐘舵€佹憳瑕?
   - 寮哄寲 confirmed delete advisory handle_message 娴嬭瘯锛岄獙璇?action 杩斿洖涓嶅寘鍚?`graph.nodes`锛屼笖 RuntimeState 涓?actor 鍒犻櫎浜嬪疄浠嶆纭惤鐩?

64. Phase 5/UI 鏈槧灏?external SeedPlan 鐨?RuntimeEvent 鏌ヨ涔熷凡鏀跺彛鍒?runtime.events.snapshot锛?
   - `runtime_events` / `user_visible_events` action 鎼哄甫 `external_plan_id` 浣嗘壘涓嶅埌瀵瑰簲 Runtime plan 鏃讹紝涓嶅啀鐩存帴杩斿洖绌轰簨浠跺垪琛紝鑰屾槸鍏堟妸绌轰簨浠?feed 鍐欏叆鍐呴儴 `runtime-events-snapshot` 鎴块棿鐨?`custom_report_facts`
   - 璇ュ垎鏀户缁笉鍥為€€ active plan锛岄伩鍏嶆煡璇竴涓け鏁?鏃?SeedPlan 鏃惰璇诲綋鍓嶆椿璺冭鍒掔殑 resource / tool / review 浜嬩欢
   - snapshot 澶辫触鏃惰褰?`runtime_events_snapshot_failed` 涓庡け璐ョ増 `runtime_events_queried`锛屽苟杩斿洖 RuntimeState 鎸佷箙鍖栧け璐ユ彁绀猴紝涓嶈繑鍥炴湭钀?fact 鐨勪簨浠跺垪琛?
   - 寮哄寲 unknown external plan runtime events 娴嬭瘯锛岄獙璇佺┖浜嬩欢缁撴灉鏉ヨ嚜 `runtime-events-snapshot` fact锛屼笖涓嶄細娉勯湶宸叉湁璁″垝浜嬩欢

65. Phase 5/UI 鏈槧灏?external SeedPlan 鐨?OperationReplay 鏌ヨ涔熷凡鏀跺彛鍒?runtime.operation_replay.snapshot锛?
   - `operation_replay` action 鎼哄甫 `external_plan_id` 浣嗘壘涓嶅埌瀵瑰簲 Runtime plan 鏃讹紝涓嶅啀鐩存帴鎷间竴涓湭鎸佷箙鍖栫殑绌?replay 杩斿洖锛岃€屾槸鍏堥€氳繃 `runtime.operation_replay.snapshot` 鍐欏叆鍐呴儴 `runtime-operation-replay` 鎴块棿鐨?`custom_report_facts`
   - 璇ュ垎鏀娇鐢ㄤ笉浼氬懡涓湡瀹炴棩蹇楃殑 `__missing_runtime_plan__` 鍝ㄥ叺杩囨护锛岄伩鍏嶇┖ `plan_id` 鏌ヨ璇褰撳墠 room 鎴?active plan 鐨?OperationLog
   - snapshot 澶辫触鏃惰褰?`runtime_operation_replay_failed`锛屽苟杩斿洖 RuntimeState 鎸佷箙鍖栧け璐ユ彁绀猴紝涓嶈繑鍥炴湭钀?fact 鐨勫鐩樼粨鏋?
   - 寮哄寲 missing external operation replay 娴嬭瘯锛岄獙璇佺┖ replay 鏉ヨ嚜 `runtime-operation-replay` fact锛屼笖涓嶄細娉勯湶宸叉湁璁″垝鐨?OperationLog 鏉＄洰

66. Phase 8 鏃?ProgressiveWorkflow 涓绘帶鐩磋揪闂ㄧ宸蹭粠鈥滄枃浠剁骇鏀捐鈥濇敹绱у埌鈥滆妯″紡绾ф斁琛屸€濓細
   - `verify_ultimate_plan.py` 鐨?static direct ProgressiveWorkflow entry gate 浠嶆壂鎻?services / `cai_extensions/agent` / `main.py` 涓殑 `run_progressive_workflow` 涓?`progressive_compose(` 鐩磋繛璋冪敤
   - 杩囨浮鏈熷厑璁告枃浠朵笉鍐嶆暣浣撹眮鍏嶏紱`scene_composer.py` 鍙厑璁告棦鏈?`run_progressive_workflow` import / 璋冪敤锛宍scene_composer_progressive.py` 鍙厑璁?workflow 瀹氫箟銆佸唴閮?`session.progressive_compose(` 璋冪敤涓?`__all__`锛宍scene_session.py` 鍙厑璁镐富寰幆璇存槑鍜?`def progressive_compose(`
   - 鍚庣画濡傛灉鍦?allowed 鏂囦欢閲屾柊澧炵浜屾潯缁曡繃 AgentRuntime / ToolCallGraph 鐨?ProgressiveWorkflow 鍏ュ彛锛岄潪 native 鎬婚棬绂佷細鐩存帴澶辫触
   - 杩欎竴姝ョ户缁敹绱р€滄棫 ProgressiveWorkflow 鍙兘浣滀负杩囨浮鍐呴儴鑳藉姏瀛樺湪锛屼笉寰楅噸鏂版墿澶т负鐢ㄦ埛鍏ュ彛鎴栨柊鐨勫ぇ宸ュ叿鍏ュ彛鈥濈殑杈圭晫

67. Phase 8 鏃?SceneComposer 涓绘帶鐩磋揪闂ㄧ涔熷凡浠庘€滄枃浠剁骇鏀捐鈥濇敹绱у埌鈥滆妯″紡绾ф斁琛屸€濓細
   - `verify_ultimate_plan.py` 鐨?static direct SceneComposer entry gate 浠嶆壂鎻?services / `cai_extensions/agent` / `main.py` 涓殑 `SceneComposer(` 涓?`composer.compose(` 鐩磋繛璋冪敤
   - 杩囨浮鏈熷厑璁告枃浠朵笉鍐嶆暣浣撹眮鍏嶏紱`main.py` 鍙厑璁搁粯璁?composer factory锛宍agent_adapter.py` 鍙厑璁?legacy guard 鍖呬綇鐨?`SceneComposer` / `compose` 璋冪敤锛宍generation_composer_adapter.py` 鍙厑璁?Scheduler 杩囨浮 adapter 璋冪敤
   - 鍘熸湁 Runtime guard token 妫€鏌ョ户缁繚鐣欙細`agent_adapter.py` 蹇呴』鍖呭惈 `_legacy_main_workflow_allowed` 涓?`AGENT_RUNTIME_REQUIRED_MESSAGE`锛宍generation_composer_adapter.py` 蹇呴』鍖呭惈 `can_call_legacy_main_workflow` 涓?legacy disabled error
   - 鍚庣画鍗充娇鍦?allowed 鏂囦欢閲屾柊澧炴柊鐨?`SceneComposer` 鎴?`compose()` 鐩磋揪鏃т富鎺э紝涔熶細琚潪 native 鎬婚棬绂佹嫤涓?
   - 杩欎竴姝ョ户缁浐鍖栤€滅敤鎴峰叆鍙ｅ彧鑳借繘鍏?AgentRuntime锛屾棫 SceneComposer 涓绘帶鍙兘浣滀负鍙楁帶杩囨浮 adapter 瀛樺湪鈥濈殑杈圭晫

68. Phase 8 鏃?SceneComposer 涓绘帶鐩磋揪闂ㄧ宸茶繘涓€姝ユ敹绱т负鈥滆皟鐢ㄧ偣鍓嶇紑蹇呴』鏈?Runtime guard鈥濓細
   - static direct SceneComposer entry gate 涓嶅啀鍙鏌?guard token 鏄惁鍑虹幇鍦ㄦ暣涓枃浠朵腑锛岃€屾槸瀵瑰叿浣?`SceneComposer(` / `composer.compose(` 璋冪敤鐐瑰洖婧墍鍦ㄨ繃娓″嚱鏁板墠缂€
   - `agent_adapter.py::_handle_scene_compose()` 涓殑 `SceneComposer` 鍒涘缓涓?`compose()` 璋冪敤鍓嶅繀椤诲凡缁忓嚭鐜?`_legacy_main_workflow_allowed` 涓?`AGENT_RUNTIME_REQUIRED_MESSAGE`
   - `generation_composer_adapter.py::compose()` 涓殑 `composer.compose()` 璋冪敤鍓嶅繀椤诲凡缁忓嚭鐜?`can_call_legacy_main_workflow` 涓?legacy disabled error
   - 杩欎竴姝ラ伩鍏嶁€滄枃浠堕《閮ㄦ湁 guard token锛屼絾鏂板璋冪敤鐐圭粫杩?guard鈥濈殑鍋囧畨鍏紝缁х画寮哄寲鏃т富鎺у彧鑳戒綔涓哄彈鎺ц繃娓?adapter 瀛樺湪

69. Phase 8 鏃?ProgressiveWorkflow 涓绘帶鐩磋揪闂ㄧ宸茶繘涓€姝ユ敹绱т负鈥滆皟鐢ㄧ偣蹇呴』浣嶄簬棰勬湡杩囨浮鍑芥暟鍐呪€濓細
   - static direct ProgressiveWorkflow entry gate 涓嶅啀鍙鏌?allowed 鏂囦欢鍜?allowed 琛屾ā寮忥紝杩樹細鏍￠獙鍏抽敭璋冪敤鐐圭殑鍑芥暟浣滅敤鍩?
   - `scene_composer.py` 涓殑 `run_progressive_workflow` import / 璋冪敤蹇呴』浣嶄簬 `SceneComposer.compose()` 杩囨浮璺緞鍐咃紝涓嶅厑璁稿悓鏂囦欢鏂板绗簩涓粫杩?AgentRuntime 鐨?progressive 鍏ュ彛
   - `scene_composer_progressive.py` 涓殑 `session.progressive_compose()` 蹇呴』浣嶄簬 `run_progressive_workflow()` 鍐咃紝涓嶅厑璁告妸 `SceneSession.progressive_compose()` 鎵╂暎鎴愭柊鐨勪富鎺у叆鍙?
   - 杩欎竴姝ヤ繚鎸佸綋鍓嶆棫閾捐矾杩囨浮鑳藉姏鍙繍琛岋紝浣嗘妸鈥滃厑璁告棫 ProgressiveWorkflow 瀛樺湪鈥濈殑杈圭晫浠庢枃浠剁骇杩涗竴姝ユ敹绱у埌鍑芥暟浣滅敤鍩熺骇

70. Phase 8 鏃?ProgressiveWorkflow 鍐呴儴瀵煎叆鍐欏叆鍙ｅ凡澧炲姞 EngineWriteGate 闈欐€佺害鏉燂細
   - `verify_ultimate_plan.py` 鐨?ProgressiveWorkflow gate 鐜板湪瑕佹眰 `run_progressive_workflow()` 浣滅敤鍩熷唴蹇呴』鍙栧緱 `get_engine_write_gate()`锛屽苟灏嗗悓涓€涓?`engine_gate` 浼犲叆 `incremental_import()`
   - 妫€鏌ユ潯浠舵敹绐勫埌 `incremental_import()` 鐨勫弬鏁扮墖娈碉紝閬垮厤璇妸 `SceneSession(...)` 鍒濆鍖栭噷鐨勫悓鍚嶅弬鏁板綋浣滃鍏ユ敹鍙ｈ瘉鎹?
   - 杩欎竴姝ヤ笉鏀瑰彉鐜版湁 progressive 鎵ц琛屼负锛屽彧鎶娾€滄棫杩囨浮閾捐矾閲岀殑鐪熷疄瀵煎叆涔熷繀椤荤粡 EngineWriteGate鈥濆浐鍖栦负闈?native 闂ㄧ
   - 鍚庣画鑻ユ湁浜哄湪 progressive 鍐呮柊澧炵粫杩?`EngineWriteGate` 鐨勫鍏ヨ矾寰勶紝`verify_ultimate_plan.py` 浼氱洿鎺ュけ璐?

71. Phase 8 鏃?GenerationScheduler 鐩磋揪鍏ュ彛宸茬撼鍏ラ潪 native 闈欐€侀棬绂侊細
   - CodeGraph 鏍稿疄褰撳墠鐪熷疄 `GenerationScheduler.submit()` 璋冪敤浠呬綅浜?`InteractionCoordinator.execute_confirmed_plan()` 鍜?`InteractionCoordinator.execute_post_generation_add()` 涓や釜鏃ц繃娓″嚱鏁?
   - `verify_ultimate_plan.py` 鏂板 static direct GenerationScheduler entry gate锛屾壂鎻?services / `cai_extensions/agent` / `main.py` 涓殑 `GenerationScheduler(` 涓?`_scheduler.submit(`
   - 杩囨浮鏈熷彧鍏佽 `lanchat_agent_worker._get_generation_scheduler()` 鍦?`can_call_legacy_main_workflow()` guard 鍚庡垱寤?scheduler锛屽苟瀹夎 Runtime audit / disclosure hooks
   - 杩囨浮鏈熷彧鍏佽 `InteractionCoordinator` 鐨勭‘璁ょ敓鎴愪笌瀹屾垚鍚庤拷鍔犱袱涓嚱鏁版彁浜ゆ棫闃熷垪锛涘叾瀹冩湇鍔°€丄gent銆佸伐鍏锋垨 UI 璺緞鏂板鐩磋揪 submit 浼氱洿鎺ュけ璐?
   - 杩欎竴姝ョ户缁妸 `GenerationScheduler` 闄嶇骇涓哄彈鎺ц繃娓℃墽琛岄槦鍒楄兘鍔涳紝閬垮厤瀹冮噸鏂版垚涓虹敤鎴峰叆鍙ｆ垨涓氬姟鐘舵€佷簨瀹炴簮

72. Phase 8 LANChat confirmed host action 鎵ц鍏ュ彛宸茬撼鍏?Runtime approval 闈欐€侀棬绂侊細
   - CodeGraph 鏍稿疄褰撳墠鐢熶骇璺緞涓?`LanChatHostActionExecutor.enqueue_and_process()` 鍙粠 `lanchat_agent_worker._execute_confirmed_action()` 璋冪敤
   - `verify_ultimate_plan.py` 鏂板 static direct host action executor entry gate锛屾壂鎻?services / `cai_extensions/agent` / `main.py` 涓殑 `_execute_confirmed_action(` 涓?`enqueue_and_process(`
   - `lanchat_agent_worker._broadcast_confirmed_action()` 蹇呴』鍏堣皟鐢?`_is_confirmed_action_payload_runtime_approved(payload)`锛屽苟鍦ㄦ湭鎵瑰噯鏃惰褰?`unapproved_confirmed_action_blocked` 鍚庤繑鍥烇紝鎵嶈兘杩涘叆 `_execute_confirmed_action(payload)`
   - `enqueue_and_process(payload)` 鍙兘淇濈暀鍦?`_execute_confirmed_action()` 涓紝涓旇鍑芥暟蹇呴』閫氳繃 `_get_host_action_executor()` 鑾峰彇鍙楁帶 executor锛屽苟鍦?finally 涓户缁Е鍙?disclosure / scheduler 鐘舵€佹姭闇?
   - 杩欎竴姝ユ妸鈥淕M/鎴夸富纭鍚庣殑鏃?host action 鎵ц鈥濆浐瀹氫负 Runtime-approved 杩囨浮璺緞锛岄伩鍏嶆湭鐢?AgentRuntime/Coordinator 鍑嗗鐨?confirmed payload 閲嶆柊缁曞洖鏃ф墽琛岄摼

73. Phase 8 LANChat 涓诲姩纭鐢熸垚鍒版棫 Coordinator 鎵ц鐨勮繃娓″叆鍙ｅ凡绾冲叆 legacy-main guard 闈欐€侀棬绂侊細
   - CodeGraph 鏍稿疄 `InteractionCoordinator.execute_confirmed_plan()` 闄?coordinator 鍐呴儴澶嶇敤澶栵紝鐢熶骇渚ц繕鏈?`lanchat_agent_worker._start_active_coordinator_generation()` 涓€涓棫杩囨浮璋冪敤鐐?
   - `verify_ultimate_plan.py` 鐨?static direct GenerationScheduler entry gate 宸叉墿灞曟壂鎻?`ref = coordinator.execute_confirmed_plan(plan.plan_id)`
   - 璇ヨ皟鐢ㄥ繀椤讳綅浜?`_start_active_coordinator_generation()` 鍐咃紝骞朵笖蹇呴』鍏堟鏌?`if not self._agent_runtime_flags.can_call_legacy_main_workflow():`
   - legacy main workflow 绂佺敤鏃讹紝蹇呴』杩斿洖 `_execute_confirmed_plan_via_agent_runtime(...)`锛涘彧鏈?legacy main workflow 琚樉寮忓厑璁告椂锛屾墠鑳界户缁繘鍏?`coordinator.execute_confirmed_plan()`
   - 杩欎竴姝ョ户缁帇缂┾€滆亰澶╃‘璁ょ敓鎴?-> SeedPlan -> GenerationScheduler鈥濈殑鏃х洿杈剧獥鍙ｏ紝纭繚榛樿鏂瑰悜鏄?AgentRuntime锛岃€屾棫 Coordinator 鎵ц鍙綔涓烘樉寮?legacy 杩囨浮璺緞瀛樺湪

74. Phase 8 HostActionExecutor 鍐呴儴鎵ц绛栫暐宸茬撼鍏ラ潤鎬侀棬绂侊細
   - CodeGraph 鏍稿疄 `LanChatHostActionExecutor._execute_payload()` 鏄?confirmed host action 杩涘叆缁撴瀯鍖?handler 鎴栨棫 Agent fallback 鐨勫叧閿垎娴佺偣
   - `verify_ultimate_plan.py` 鏂板 static host action executor policy gate锛屾牎楠?`__init__()` 榛樿 `allow_legacy_agent_fallback=False`锛屽苟淇濆瓨 `structured_action_handler`
   - `_execute_payload()` 蹇呴』鍏堣瘑鍒?structured SeedPlan payload锛屽啀鏍￠獙 action 鏄惁灞炰簬鍙楁帶闆嗗悎锛涚粨鏋勫寲鍏ュ彛涓嶅彲鐢ㄦ椂鐩存帴鎷掔粷锛屼笉鑳借惤鍒版棫 Agent fallback
   - 鍙湁闈炵粨鏋勫寲 payload 涓?`_allow_legacy_agent_fallback` 鏄惧紡寮€鍚椂锛屾墠鍏佽璋冪敤 `_get_agent()` 杩涘叆鏃?Agent 鎵ц鍣?
   - 鍙楁帶 structured action 闆嗗悎鍥哄畾鍖呭惈 `start_generation` / `execute_seed_plan` / `post_generation_add`锛岄伩鍏嶄换鎰?plan-like payload 鍊熺粨鏋勫寲韬唤鎵ц鏈煡鍔ㄤ綔

75. Phase 8 鏃?Quasar workflow 娉ㄥ唽灞?policy 瀹夎椤哄簭宸茬撼鍏ラ潤鎬侀棬绂侊細
   - CodeGraph 鏍稿疄 `CabbageWorkflowPlugin.register()` 浼氭敞鍐屾棫 `WORKFLOWS` 涓?`WORKFLOW_COMMANDS`锛岃繖浜涙ā鍧椾粛淇濈暀浣滀负 legacy regression / internal debug baseline
   - `verify_ultimate_plan.py` 鐨?static workflow command exposure gate 鐜板湪浼氳鍙?`cai_extensions/register.py`锛屽苟绮剧‘鎴彇 `CabbageWorkflowPlugin.register()` 浣滅敤鍩?
   - 闂ㄧ瑕佹眰鍏堝彇寰?workflow / workflow_command registry锛屽啀鍏堝悗璋冪敤 `install_workflow_command_policy(command_registry)` 涓?`install_workflow_function_policy(registry, command_registry)`锛屼箣鍚庢墠鍏佽閬嶅巻 `flow_modules`
   - 姣忎釜 command 蹇呴』鍏?`record_workflow_function_exposure(...)`锛屽啀鎵ц `should_register_workflow_command(command)`锛屾渶鍚庢墠鍏佽 `command_registry.register(...)`
   - 杩欎竴姝ヤ繚璇佹棫 workflow 鍙互缁х画浣滀负淇濆畧闅愯棌鐨?baseline 娉ㄥ唽鍦ㄥ簳灞?registry 涓紝浣嗙敤鎴峰彲瑙佸懡浠ゅ拰 function_id 鎵ц闈㈠繀椤诲厛缁忚繃 Corona policy 杩囨护

76. Phase 8 AgentRuntime feature flag 涓?legacy main workflow 榛樿杈圭晫宸茬撼鍏ラ潤鎬侀棬绂侊細
   - CodeGraph 鏍稿疄 `AgentRuntimeFlags` 褰撳墠榛樿 `agent_runtime_enabled=True`銆乣old_workflow_direct_entry_disabled=True`銆乣allow_legacy_main_workflow=False`
   - `verify_ultimate_plan.py` 鏂板 static AgentRuntime flag boundary gate锛屾牎楠?dataclass 榛樿鍊煎拰 `from_env()` 榛樿鍊煎繀椤荤户缁繚鎸佲€淩untime 榛樿鍚敤銆佹棫涓?workflow 榛樿鍏抽棴鈥?
   - 闂ㄧ瑕佹眰 `can_call_legacy_main_workflow()` 鍚屾椂鍙?`agent_runtime_enabled`銆乣allow_legacy_main_workflow`銆乣not old_workflow_direct_entry_disabled` 涓変釜鏉′欢绾︽潫
   - 闂ㄧ瑕佹眰 `SceneComposerJobRunner.compose()` 蹇呴』鍏堟鏌?`can_call_legacy_main_workflow()`锛屽啀鍏佽鍒涘缓 composer 骞惰皟鐢?`composer.compose()`
   - 闂ㄧ瑕佹眰 `LANChatAgentWorker._get_generation_scheduler()` 蹇呴』鍏堟鏌?`can_call_legacy_main_workflow()`锛屽惁鍒欒繑鍥?`None`锛屽啀鍏佽鍒涘缓 `GenerationScheduler`
   - 杩欎竴姝ユ妸绗?14 鑺傜殑 feature flag 绾︽潫鍙樻垚闈?native 鑷姩楠岃瘉椤癸紝閬垮厤鍚庣画鏀瑰姩鎶婃棫涓?workflow 閲嶆柊浣滀负榛樿鎵ц璺緞鏀惧嚭鏉?

77. Phase 8 鐪熷疄 provider / engine-write 閫氶亾榛樿鍏抽棴杈圭晫宸茬撼鍏ュ悓涓€闈欐€侀棬绂侊細
   - CodeGraph 鏍稿疄 `LANChatAgentWorker._create_agent_runtime()` 涓湡瀹?scene snapshot銆乮mage/model resource銆乪nvironment component銆乪ngine import/delete/transform provider 閮藉彧鍦ㄥ搴?`can_use_*_provider()` 涓虹湡鏃惰閰?
   - `verify_ultimate_plan.py` 鐨?static AgentRuntime flag boundary gate 宸叉墿灞曟牎楠屾墍鏈夌湡瀹?provider flag 鐨?dataclass 榛樿鍊间笌 `from_env()` 榛樿鍊煎潎涓?`False`
   - 闂ㄧ瑕佹眰姣忎釜 `can_use_*_provider()` 閮藉繀椤诲厛缁忚繃 `can_call_legacy_function_adapter()`锛屽啀璇诲彇瀵瑰簲 provider flag锛岄伩鍏嶅崟鐙墦寮€ provider 缁曡繃 Runtime 杩佺Щ杈圭晫
   - 闂ㄧ瑕佹眰 `_create_agent_runtime()` 涓瘡涓湡瀹?provider factory 涔嬪墠蹇呴』鍏堝嚭鐜板搴?`can_use_*_provider()` guard锛屽寘鎷?actor import銆乤ctor delete銆乴ayout transform 涓?environment import
   - 杩欎竴姝ユ妸鈥滅湡瀹?C++/璧勬簮 provider 蹇呴』鏄惧紡寮€鍚紝榛樿淇濇寔 mock / RuntimeState-only鈥濈殑绗?14 鑺傜害鏉熷浐鍖栦负闈?native 鑷姩楠岃瘉椤?

78. Phase 5/Report `execute_scene_plan()` 榛樿杩斿洖宸茬Щ闄?ToolCallGraph 鑺傜偣缁嗚妭锛?
   - CodeGraph 鏍稿疄 `AgentRuntime.execute_scene_plan()` 鏄?Runtime 鍐呴儴纭鎵ц闂幆鍏ュ彛锛屽巻鍙茶繑鍥炲€间腑浠嶅寘鍚?`graph.nodes` 鐨勫畬鏁?ToolCall 鏄庣粏
   - `execute_scene_plan()` 鐜板湪榛樿鍙繑鍥?`graph_id`銆乣status`銆乣node_count` 绛?graph 鎽樿锛屼笉鍐嶉粯璁よ繑鍥?`nodes`
   - 闇€瑕佸唴閮ㄨ皟璇曟垨娴嬭瘯 DAG 渚濊禆鏃讹紝蹇呴』鏄惧紡浼犲叆 `include_debug_graph_nodes=True` 鎵嶈兘鎷垮埌 `graph_result["nodes"]`
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸叉墿灞曟鏌ヨ榛樿瀹夊叏杩斿洖濂戠害锛岄槻姝㈠悗缁妸 graph node 鏄庣粏閲嶆柊鏀惧洖榛樿杩斿洖
   - Runtime 鍐呴儴娴嬭瘯鍚屾鍖哄垎榛樿瀹夊叏杩斿洖涓?debug 杩斿洖锛岀户缁繚鐣欓獙璇佸伐鍏烽『搴忋€佷緷璧栧拰 consumes 濂戠害鐨勮兘鍔?
   - 杩欎竴姝ョ户缁帹杩涒€滅敤鎴?涓婂眰榛樿鍙湅鍒?RuntimeState / OperationLog 娲剧敓浜嬪疄锛屼笉鐩存帴鏆撮湶 ToolCallGraph 鑺傜偣 raw payload鈥濈殑鏀跺彛

79. Phase 5/UI `handle_message()` 鐢ㄦ埛鍙杩斿洖闈㈠凡琛ラ綈 graph 鑺傜偣娉勯湶闂ㄧ锛?
   - CodeGraph 鏍稿疄 `refresh_scene_snapshot()`銆乣propose_layout_adjustment()` 绛夊唴閮?helper 浠嶄繚鐣欒缁?graph 杩斿洖锛岀敤浜?Runtime 鍐呴儴璋冭瘯涓庢祴璇?
   - 鐢ㄦ埛鍙 `handle_message()` 鍒嗘敮蹇呴』鍙繑鍥炲畨鍏?graph 鎽樿锛歴cene snapshot銆乴ayout adjustment銆乴ayout confirm銆乧onfirmed delete advisory 鍧囧彧杩斿洖 `{"status": ...}`
   - 淇 `pending intervention -> adjustment proposal` 鍒嗘敮锛氫笉鍐嶆妸 `propose_layout_adjustment()` 鐨?raw graph 鍘熸牱杩斿洖缁欎笂灞傦紝鍙繑鍥?graph status
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸叉墿灞曟鏌?`handle_message()` 鐨勭敤鎴疯繑鍥為潰蹇呴』浣跨敤 `safe_snapshot` 鍜?graph status 鎽樿锛屽苟绂佹 raw graph payload 鐩磋繑
   - 杩欎竴姝ヤ繚鐣欏唴閮?helper 鐨勮皟璇曡兘鍔涳紝鍚屾椂缁х画淇濊瘉鑱婂ぉ瀹?/ action 灞備笉鏆撮湶 ToolCallGraph 鑺傜偣銆乼ool args 鎴?raw payload

80. Phase 5/UI Runtime queue/drain/execute 鐢ㄦ埛鍙杩斿洖闈㈢户缁敹绐勶細
   - CodeGraph 鏍稿疄 `handle_message(worker_drain)` 鏇炬妸 `drain_result` 鍘熸牱杩斿洖锛宍confirm_and_enqueue` 鏇炬妸 `queued` 鍜?`queued["graphs"]` 鍘熸牱杩斿洖锛宍confirm_and_execute` 鏇炬妸 `execution["graphs"]` 鍘熸牱杩斿洖
   - 鏂板 `_safe_graph_summary_for_user()` / `_safe_graphs_for_user()` / `_safe_queue_result_for_user()` / `_safe_drain_result_for_user()`锛岀粺涓€鎶?graph銆乹ueue銆乨rain 缁撴灉鏀舵暃涓?graph_id / batch_id / status / node_count / drained_count 绛夋憳瑕?
   - `handle_message()` 鐨?worker drain銆佷粙鍏ユ壒娆?enqueue銆佺敓鎴?enqueue銆佺洿鎺?execute 鍒嗘敮鍧囦笉鍐嶈繑鍥?`nodes`銆乼ool args銆乧onsumes 鎴?raw ToolCallGraph 鑺傜偣鏄庣粏
   - `execute_scene_plan()` 榛樿杩斿洖涔熷悓姝ユ敼涓?safe queue / safe drain 鎽樿锛涘唴閮ㄥ畬鏁?graph nodes 浠嶇暀鍦?RuntimeState 涓庢樉寮?debug 鍙傛暟涓紝閬垮厤涓㈠け璇婃柇鑳藉姏
   - Runtime 娴嬭瘯宸茶鐩?confirm-and-execute銆乧onfirm-and-enqueue銆亀orker-drain銆乪xecute-scene-plan 鐨勭敤鎴峰彲瑙?payload 涓嶅惈 `nodes`锛屽悓鏃剁‘璁?RuntimeState 鍐呴儴浠嶄繚鐣欏畬鏁存墽琛屽浘浜嬪疄
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸叉墿灞曠姝?`handle_message()` 閲嶆柊鍑虹幇 `"drain": drain_result`銆乣"queued": queued`銆乣"graphs": queued["graphs"]`銆乣"graphs": execution["graphs"]` 绛夊師鏍烽€忎紶

81. Phase 6/GM Planner 涓婁笅鏂囨憳瑕佸凡浠?RuntimeState 鐢熸垚缁撴瀯鍖?digest锛?
   - CodeGraph 鏍稿疄 `gm_summary()` 褰撳墠閫氳繃 `status_summary()` 璇诲彇 RuntimeState 涓殑 `planning_context_events`锛屽啀閫氳繃 `runtime.gm_summary.snapshot` 鎸佷箙鍖?GM-facing 鎽樿
   - 鏂板 `_planning_context_digest_for_report()`锛屼粠宸茶惤 RuntimeState 鐨勫畨鍏?`text_preview`銆乻peaker_type銆乤gent_name銆乷wner_agent銆乻ource_context_agents 娲剧敓涓婁笅鏂?digest
   - `status_summary()` 涓庢渶缁?`generate_report()` 鐨?`planning_context_summary` 鍧囧寘鍚?`context_digest`锛屼娇 GM / Planner 涓嶅啀鍙緷璧栨渶杩戜笁鏉?context锛屼篃涓嶉渶瑕佸洖璇?raw chat history
   - `gm_summary()` 鐜板湪杩斿洖 `context_digest`锛屽寘鍚?speaker_type_counts銆乷wner_agent銆乻ource_context_agents銆乤gent_contributions銆乴atest_user_points銆乴atest_agent_points
   - Runtime 娴嬭瘯宸茶鐩栨埧涓?+ 澶?Agent 璁ㄨ鍚庯紝GM summary 鑳藉悓鏃朵繚鐣欓暱鑰?/ 鍟嗕汉鐨勮础鐚紝骞剁‘璁?snapshot fact 涓庣敤鎴峰彲瑙佹憳瑕佷竴鑷?
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹?`gm_summary()` 淇濈暀 `context_digest` / `agent_contributions`锛岄槻姝?GM 鎬荤粨閫€鍥炶杽鐘舵€佹憳瑕?

82. Phase 6/Planner 浠嬪叆鎽樿宸蹭粠 RuntimeState 鐢熸垚缁撴瀯鍖?intervention digest锛?
   - CodeGraph 鏍稿疄 `status_summary()` / `generate_report()` 宸茶鍙?RuntimeState 涓殑 pending / accepted / deferred interventions锛屼絾姝ゅ墠涓昏鏆撮湶鏁伴噺鍜?latest 鍒楄〃锛孭lanner 浠嶉渶鑷鍒ゆ柇鍝簺鑳借繘涓嬩竴鎵?
   - 鏂板 `_intervention_digest_for_report()`锛屼粠宸茶惤 RuntimeState 鐨?PlanPatch 浜嬪疄娲剧敓 patch_type_counts銆乶ext_batch_candidate_items銆乤bsorbable / non_absorbable 璁℃暟銆乶eeds_confirmation 涓?deferred_reasons
   - `status_summary()` 涓?`generate_report()` 鐨?`intervention_summary` 鍧囧寘鍚?`intervention_digest`锛岃 GM / Planner 鍙互鐩存帴鍖哄垎鈥滀笅涓€鎵瑰彲鍚告敹鏂板鐗╀綋鈥濆拰鈥滈渶瑕佺‘璁ょ殑淇敼/鍒犻櫎/楂橀闄╀粙鍏モ€?
   - Runtime 娴嬭瘯宸茶鐩栨柊澧炲ぉ浣块洉鍍?+ 淇敼鍏ュ彛甯冨眬鐨勬贩鍚?pending 浠嬪叆锛氬ぉ浣块洉鍍忚繘鍏?next_batch_candidate_items锛屼慨鏀硅姹傝繘鍏?needs_confirmation
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹?status / report 淇濈暀 `intervention_digest`锛岄槻姝粙鍏ユ憳瑕侀€€鍥炲彧鏈夎鏁颁笌鏈€杩戝垪琛?

83. Phase 7/Sync 鍚屾涓庤祫婧愪紶杈撳仴搴锋憳瑕佸凡杩涘叆 Runtime 鎶ュ憡闈細
   - CodeGraph 鏍稿疄 `status_summary()` / `generate_report()` 宸插垎鍒毚闇?`sync_summary`銆乣asset_transfer_summary`銆乣sync_replay_summary`銆乣message_delivery_summary`锛屼絾缂哄皯缁熶竴鍋ュ悍鍒ゅ畾锛孏M / 楠屾敹浠嶉渶瑕佷汉宸ユ嫾鏃ュ織
   - 鏂板 `_sync_health_digest_for_report()`锛屼粠 RuntimeState 涓?OperationLog 宸叉湁鍚屾浜嬪疄娲剧敓 `healthy` / `partial` / `needs_attention` / `no_sync_facts` 鐘舵€?
   - `sync_health_digest` 姹囨€?actor sync銆乤sset transfer銆乼ransfer progress銆乵essage delivery failure锛屼笉鏆撮湶 message_id銆乧orrelation_id銆乤sset_path銆乸rovider銆乁RL 绛夊唴閮ㄥ瓧娈?
   - `status_summary()`銆乣generate_report()` 鍜?`sync_status` 鍔ㄤ綔鍧囪繑鍥?`sync_health_digest`锛屼娇澶氫汉鍚屾/妯″瀷浼犺緭闂鎴愪负 Runtime 涓€绛夊彲楠屾敹鐘舵€?
   - `ReportRecordValidator` 宸插皢 `sync_health_digest` 绾冲叆鎶ュ憡鐧藉悕鍗曪紝浣嗕粛璧板畨鍏ㄦ爲鏍￠獙锛岄伩鍏嶆柊澧炲瓧娈电粫杩囨姤鍛婂畨鍏ㄧ害鏉?
   - Runtime 娴嬭瘯宸茶鐩?asset transfer failed -> `needs_attention`銆乤sset transfer progress -> `partial`銆乵essage delivery failed -> `needs_attention`
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹?status / report 淇濈暀 `sync_health_digest`锛岄槻姝㈠悓姝ュ仴搴锋憳瑕佷粠鎶ュ憡闈㈤€€鍥炴棩蹇楃鐗?

84. Phase 7/Sync actor create / transform / delete 鍔ㄤ綔鎽樿宸茶繘鍏?`sync_health_digest`锛?
   - CodeGraph 鏍稿疄 `record_sync_event()` 宸叉妸 C++ / LANChat / engine sync 浜嬪疄闀滃儚鍒?RuntimeState 鐨?`actors`銆乣sync_events`銆乣sync_state.actor_events`锛屽苟缁存姢 `sync_lifecycle_status`
   - 鍦ㄤ笉鏀?C++ 涓庣綉缁滃箍鎾摼璺殑鍓嶆彁涓嬶紝`_sync_health_digest_for_report()` 杩涗竴姝ヤ粠 `sync_replay_summary.event_type_counts` 鍜?`sync_summary.latest_actors` 娲剧敓 actor action digest
   - 鏂板瀛楁鍖呮嫭 `actor_create_count`銆乣actor_transform_count`銆乣actor_delete_count`銆乣latest_actor_count`銆乣latest_active_actor_count`銆乣latest_deleted_actor_count`
   - 杩欎娇澶氫汉鑱旀満楠屾敹鍙互鐩存帴鍒ゆ柇鈥渁ctor 鍒涘缓鏈夋棤鍚屾銆乼ransform 鏄惁杩涘叆 Runtime銆乨elete 鏄惁钀藉埌鐢熷懡鍛ㄦ湡鐘舵€佲€濓紝鑰屼笉鏄彧鑳戒汉宸?grep `Broadcast actor create` / `actor_transform` / `actor_deleted`
   - Runtime 娴嬭瘯宸茶鐩?actor transform + delete 鍚庯紝status / report 鐨?`sync_health_digest` 涓?replay 璁℃暟涓€鑷达紱`sync_status` 鏌ヨ涔熶細杩斿洖 actor create 鎽樿
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹傝繖浜?actor sync 瀛楁淇濈暀鍦?`_sync_health_digest_for_report()` 涓?

85. Phase 7/Sync peer / room lifecycle 鎽樿宸茶繘鍏?`sync_health_digest`锛?
   - CodeGraph 鏍稿疄 `record_sync_event()` 宸叉妸 room close銆乸eer join銆乸eer leave 绛?C++/LANChat 鍚屾浜嬪疄杩涘叆 `sync_state.peer_events`銆乣sync_state.room_status` 鍜?OperationLog replay
   - `_sync_health_digest_for_report()` 鐜板湪浠?`sync_replay_summary` 娲剧敓 `peer_join_count`銆乣peer_leave_count`銆乣room_close_count`銆乣latest_peer_id`銆乣latest_peer_event_type`銆乣latest_room_status`
   - 鎴块棿鍏抽棴浼氳繘鍏?`needs_attention=["room_closed"]` 骞跺皢 digest 鐘舵€佺疆涓?`needs_attention`锛涙櫘閫?peer join / leave 淇濇寔鍋ュ悍鐢熷懡鍛ㄦ湡鎽樿锛屼笉璇垽涓哄け璐?
   - 杩欎娇澶氫汉鑱旀満楠屾敹鍙互鐩存帴鍒ゆ柇鈥滄埧闂存槸鍚﹁鍏抽棴銆乸eer 鏄惁鍙戠敓 join/leave銆佹渶鏂?peer 浜嬩欢鏄皝鈥濓紝涓嶅啀鍙兘浜哄伐缈?LANChat / NetworkSystem 鏃ュ織
   - Runtime 娴嬭瘯宸茶鐩?room_closed -> `needs_attention`锛屼互鍙?peer join + leave 鍚?status / report digest 涓?replay 涓€鑷?
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹傝繖浜?peer / room lifecycle 瀛楁淇濈暀鍦?`_sync_health_digest_for_report()` 涓?

86. Phase 7/GM 鍚屾鍋ュ悍鎽樿宸茶繘鍏?GM-facing summary锛?
   - CodeGraph 鏍稿疄 `gm_summary()` 宸查€氳繃 `status_summary()` 璇诲彇 RuntimeState锛岃€屼笉鏄洿鎺ヨ鍙栧簳灞?LANChat / Network / Engine 鐘舵€?
   - `gm_summary()` 鐜板湪閫忎紶 `sync_health_digest`锛岃 GM 鎬荤粨鍙互鍚屾椂鐪嬪埌璁ㄨ涓婁笅鏂囥€佽鍒掓憳瑕佸拰澶氫汉鍚屾鍋ュ悍鐘舵€?
   - `runtime_gm_summary_exported` 鍙褰?`sync_health_status` 涓?`sync_attention_count`锛屼笉鏆撮湶 message_id銆乤sset_path銆乸rovider銆乁RL 绛夊唴閮ㄥ瓧娈?
   - Runtime 娴嬭瘯宸茶鐩?GM summary 鍦ㄥ Agent 璁ㄨ鍚庡悓鏃跺寘鍚?context digest 涓?actor sync health digest锛屽苟纭 snapshot fact 涓庣敤鎴峰彲瑙佹憳瑕佷竴鑷?
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹?`gm_summary()` 淇濈暀 `sync_health_digest` / `sync_health_status`

87. Phase 7/LANChat GM 鍥炲宸叉姭闇插悓姝ュ仴搴锋憳瑕侊細
   - CodeGraph 鏍稿疄 `@GM 鎬荤粨褰撳墠鏂规` / 鐘舵€佹煡璇細浼樺厛璧?`LANChatAgentWorker._agent_runtime_status_reply()`锛岃璺緞璇诲彇 AgentRuntime `status_summary()`锛屾棫 Coordinator 鍙綔涓烘樉寮?legacy fallback
   - `_agent_runtime_status_reply()` 鐜板湪璇诲彇 `sync_health_digest`锛屽苟鍦ㄢ€滃浜哄悓姝モ€濊涓睍绀哄仴搴风姸鎬併€侀渶鍏虫敞椤规暟閲忋€乤ctor create/transform/delete 璁℃暟銆乤ctive actor 鏁颁笌 peer join/leave 璁℃暟
   - 鏂板 `_format_agent_runtime_sync_health_report()`锛屽彧杈撳嚭瀹夊叏鐘舵€佷笌璁℃暟锛涗笉鏆撮湶 peer_id銆乵essage_id銆乤sset_path銆乸rovider銆乁RL 鎴栫鏈夎矾寰?
   - LANChat Runtime guard 娴嬭瘯宸茶鐩栧悓姝ヤ腑妯″瀷鍚屼紶杩涘害浼氭樉绀?`partial`銆乣attention 1` 涓?`asset-transfer-in-progress`锛屽悓鏃剁户缁‘璁ゅ唴閮ㄨ矾寰勫拰 peer id 涓嶄細鍑虹幇鍦?GM 鍥炲涓?
   - 杩欎竴姝ユ妸绗?86 椤圭殑 Runtime GM summary 鑳藉姏鎺ュ埌瀹為檯鑱婂ぉ瀹?GM-facing 鏂囨锛屼究浜庡浜鸿仈鏈烘椂鐩存帴鍒ゆ柇鍚屾鍋ュ悍鑰屼笉鏄汉宸ョ炕鏃ュ織

88. Phase 7/GM 鎬荤粨鍔ㄤ綔宸蹭粠鏅€氱姸鎬佹煡璇腑鍒嗙锛?
   - CodeGraph 鏍稿疄 `LANChatAgentWorker._handle_coordinator_status_query()` 鏄?`@GM 鎬荤粨褰撳墠鏂规` 涓庣姸鎬佹煡璇㈣繘鍏?Runtime 鐨勫叧閿垎娴佺偣
   - 鏂板 `_is_runtime_gm_summary_query()`锛屽皢 `鎬荤粨/姹囨€?姒傛嫭/褰撳墠鏂规/鐜板湪鏂规/鐢熸垚鏂规` 杩欑被 GM 鎬荤粨璇锋眰璺敱鍒?AgentRuntime `runtime_gm_summary`锛沗杩涘害/鍒板摢/鐢熸垚鍒板摢閲?浠€涔堟儏鍐礰 浠嶈蛋鏅€?`status_query`
   - 鏂板 `_agent_runtime_gm_summary_reply()`锛孏M 鎬荤粨鍥炲鍙睍绀烘柟妗堛€佷笂涓嬫枃銆丄gent 璐＄尞銆佹渶杩戠敤鎴疯鐐广€佷粙鍏ユ憳瑕併€佹ā鍨?鍦板舰娓呭崟鍜屽悓姝ュ仴搴凤紝涓嶅啀鎶?ToolCallGraph銆佽祫婧愰€氶亾銆佸紩鎿庡啓鍏ョ瓑鎵ц闈㈢粏鑺傚杩涙€荤粨
   - `AgentRuntime.gm_summary()` 鐜板湪甯﹀嚭 `intervention_digest`锛屼娇 GM 鑳芥€荤粨寰呭鐞?宸插惛鏀?寤跺悗浠嬪叆锛岃€屼笉闇€瑕佽鍙栨棫 Coordinator 鎴栧簳灞?Scheduler
   - LANChat Runtime guard 娴嬭瘯宸茶鐩栨棤 ScenePlan 鐨?room-level 璁ㄨ涔熻兘鐢?Runtime GM summary 鎬荤粨锛屼笖涓嶄細鏋勯€犳棫 Coordinator锛涘悓姝ュ仴搴蜂笌浠嬪叆鎽樿鍧囧湪 GM-facing 鍥炲涓彲瑙?
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹?`gm_summary()` 淇濈暀 `intervention_digest`锛岄槻姝?GM 鎬荤粨閫€鍥炲彧鏈変笂涓嬫枃鑰岀湅涓嶅埌鐢ㄦ埛浠嬪叆鐘舵€?

89. Phase 7/GM summary export 宸茶褰曞畨鍏ㄤ粙鍏ヨ鏁帮細
   - CodeGraph 鏍稿疄 `AgentRuntime.gm_summary()` 鐨?`runtime_gm_summary_exported` OperationLog payload 鍘熷厛鍙褰?context 涓?sync health 璁℃暟锛岀己灏戜粙鍏ユ憳瑕佺殑鍙洖鏀捐瘉鎹?
   - `runtime_gm_summary_exported` 鐜板湪澧炲姞 `intervention_pending_count`銆乣intervention_accepted_count`銆乣intervention_deferred_count` 涓変釜瀹夊叏鏁板瓧娈?
   - 杩欎簺瀛楁鍙敤浜庡鐩?GM 鎬荤粨鏄惁鐪嬭浜嗙敤鎴蜂粙鍏ョ姸鎬侊紝涓嶈褰曠敤鎴峰師鏂囥€乸atch_id銆乵etadata銆乤ctor_id銆乸rovider銆乁RL 鎴栫鏈夎矾寰?
   - 鏂板 Runtime 娴嬭瘯瑕嗙洊鏈?ScenePlan 鐨勪粙鍏ュ満鏅細GM summary 杩斿洖 `intervention_digest`锛孫perationLog export payload 鍙寘鍚鏁颁笖涓嶆硠闇测€滃ぉ浣块洉鍍忊€濈瓑鐢ㄦ埛鍘熸枃
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹傝繖浜?intervention export 瀛楁淇濈暀鍦?`gm_summary()` 涓?

90. Phase 7/GM summary `recorded` 璇箟宸蹭粠 context-only 淇涓?Runtime availability锛?
   - CodeGraph 鏍稿疄 `AgentRuntime.handle_message(action="runtime_gm_summary")` 鍘熷厛鍙敤 `context_count` 鍒ゆ柇 `recorded`锛屼細鎶娾€滃凡鏈?ScenePlan 浣嗘殏鏃犺璁轰笂涓嬫枃鈥濈殑 GM summary 璇爣涓烘湭璁板綍
   - `recorded` 鐜板湪璺熼殢 `gm_summary.available`锛屽彧瑕?RuntimeState 涓凡鏈夊彲鐢?ScenePlan 鎴栬璁轰笂涓嬫枃锛屽氨瑙嗕负宸茶褰曠殑 GM summary
   - 鏂板 Runtime 娴嬭瘯鐢?`StatePatch` 鍐欏叆鏃?discussion context 鐨?ScenePlan锛岄獙璇?`runtime_gm_summary` 杩斿洖 `recorded=True`銆乣available=True`銆乣has_scene_plan=True` 涓?`context_count=0`
   - 杩欎竴姝ヤ繚鎸?GM summary 鐨勪簨瀹炴簮浠嶄负 RuntimeState / OperationLog锛屼笉鍥為€€鏃?Coordinator锛屼篃涓嶄负浜嗚褰曠姸鎬佷吉閫犱笂涓嬫枃

91. Phase 7/GM summary replay 鎽樿宸茶繘鍏?operation replay/report锛?
   - CodeGraph 鏍稿疄 `runtime_gm_summary_exported` 宸叉湁瀹夊叏 payload锛屼絾 `operation_replay()` / `generate_report()` 鐨?compact replay 涔嬪墠娌℃湁 GM summary 鑱氬悎瑙嗗浘
   - 鏂板 `_gm_summary_replay_summary()`锛屼粠 OperationLog 鑱氬悎 exported/failed銆乤vailable銆乻cene_plan銆乧ontext銆乤gent contribution銆乮ntervention 璁℃暟鍜?sync health 鐘舵€佸垎甯?
   - `operation_replay()` 涓?`_operation_replay_summary_for_report()` 鍧囪繑鍥?`gm_summary_replay_summary`锛屼娇 GM 鎬荤粨鏈韩鍙 Runtime 鍥炴斁鍜屾渶缁堟姤鍛婂鐩?
   - 鎽樿鍙緭鍑鸿鏁板拰鐘舵€侊紝涓嶆毚闇茬敤鎴峰師鏂囥€乸atch_id銆乵etadata銆乤ctor_id銆乸rovider銆乁RL 鎴栫鏈夎矾寰?
   - Runtime 娴嬭瘯宸茶鐩?GM summary export 鍚?operation replay 涓?final report 閮藉寘鍚鎽樿锛屼笖涓嶆硠闇测€滃ぉ浣块洉鍍忊€濈瓑鐢ㄦ埛鍘熸枃
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹?`_operation_replay_summary_for_report()` 淇濈暀 `gm_summary_replay_summary`

92. Phase 6/Layout reflow 鍚庨€夋嫨鎬?AABB 璐村湴宸茶繘鍏?`runtime.layout.apply_delta`锛?
   - CodeGraph 鏍稿疄 `_apply_layout_delta_tool()` 鍘熷厛鍙墽琛屼綆椋庨櫓 move锛涙棤鐪熷疄 engine transform provider 鏃讹紝RuntimeState 鍐呴儴涓嶄細鏍规嵁 AABB 淇鍦伴潰鐗╀綋娴┖
   - `runtime.layout.apply_delta` 鐜板湪浼氬湪浣庨闄?move 鍚庤瘑鍒?actor 鏀拺绫诲瀷锛氬湴闈㈡敮鎾戠墿浣撴墽琛?AABB bottom snap锛屽鎸?鎮寕/system/unknown 瀵硅薄璺宠繃
   - 璐村湴淇鍩轰簬绉诲姩鍚庣殑 AABB bottom锛岃€屼笉鏄矖鏆?`position.y=0`锛涘悓姝ユ洿鏂?`position.y` 涓?`aabb.min/max.y`锛屼繚鎸?RuntimeState 鑷唇
   - 鏂板 Runtime 娴嬭瘯瑕嗙洊鏃?provider 鐨勭‘璁ゅ竷灞€璋冩暣锛歚钘忓疂绠盽 琚创鍦帮紝`鐏妸` 浣滀负 wall-mounted 鍙Щ鍔ㄤ笉钀藉湴
   - `verify_ultimate_plan.py` 鐨?Runtime validator contract gate 宸茶姹?`_apply_layout_delta_tool()` 淇濈暀 `_layout_support_type()`銆乣_shift_actor_aabb()` 涓?`_snap_actor_bottom_to_ground_if_supported()`锛岄槻姝㈠洖閫€鎴愮函 move

93. Phase 4/Batch ToolCall facts 宸茶繘鍏?status/report 瀹夊叏鎽樿锛?
   - CodeGraph 鏍稿疄 `batch.prioritize_items`銆乣batch.create`銆乣batch.merge_intervention` 宸叉妸鎵规鎺掑簭銆佹壒娆¤崏妗堝拰浠嬪叆鍚堝苟缁撴灉鍐欏叆 `custom_batch_facts`
   - 鏂板 `_batch_tooling_summary_for_plan()`锛屼粠 RuntimeState 鑱氬悎 created/prioritized/merged/absorbed 璁℃暟锛岃 ToolCall 浜х墿鍙鐘舵€佹煡璇㈠拰鏈€缁堟姤鍛婂鐩?
   - `status_summary()` 涓?`generate_report()` 鍧囪繑鍥?`batch_tooling_summary`锛涙憳瑕佸彧杈撳嚭 fact 绫诲瀷鍜岃鏁帮紝涓嶆毚闇?`patch_id`銆佺敤鎴峰師鏂囥€乸rovider銆乁RL 鎴栫鏈夎矾寰?
   - Runtime 娴嬭瘯宸茶鐩栨櫘閫氭壒娆¤鍒掑拰鐢熸垚涓粙鍏ヨ拷鍔犱袱鏉￠摼璺紝纭 batch tooling summary 涓?report/status 涓€鑷翠笖涓嶆硠闇蹭粙鍏?id
   - `verify_ultimate_plan.py` 鐨?Runtime report / validator gate 宸茶姹?`status_summary()`銆乣generate_report()` 鍜?helper 淇濈暀璇ユ憳瑕侊紝闃叉 Phase 4 鎵规宸ュ叿浜嬪疄閲嶆柊鍙樻垚涓嶅彲瑙佸唴閮ㄧ姸鎬?

94. Phase 5/Runtime command 闃熷垪褰卞搷宸茶繘鍏?operation replay/report锛?
   - CodeGraph 鏍稿疄 `apply_runtime_command()` 宸查€氳繃 RuntimeState 淇敼 pause/cancel/resume/retry 瀵?ScenePlan銆丅atchPlan銆乀oolCallGraph queue 鐨勫奖鍝嶏紝涓?`drain_next_tool_graph()` 浼氬湪 paused/cancelled 鐘舵€佷笅闃绘柇鎵ц鍥惧嚭闃?
   - `_runtime_command_replay_summary()` 鐜板湪鑱氬悎 `cancelled_batch_total`銆乣cancelled_graph_total`銆乣resumed_graph_total`銆乣retried_graph_total` 涓庣姸鎬佽縼绉昏鏁?
   - `operation_replay()` 涓?`generate_report()` 鐨?compact replay 鍙互璇佹槑 Runtime command 涓嶅彧鏄亰澶╁鏂囨锛岃€屾槸鐪熸褰卞搷 Runtime queue / graph / batch 鐘舵€?
   - Runtime 娴嬭瘯宸茶鐩?pause/resume/cancel 涓?retry 涓ゆ潯鍛戒护閾捐矾锛岀‘璁?replay/report 鑳界湅鍒板彇娑堟壒娆℃暟銆佸彇娑堟墽琛屽浘鏁板拰閲嶈瘯鎵ц鍥炬暟锛屼笖涓嶆毚闇?`command_id`
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹傝繖浜?queue-impact 瀛楁淇濈暀鍦?runtime command replay 涓紝缁х画鎺ㄨ繘 `GenerationScheduler queue -> ToolCallGraph queue`

95. Phase 5/ToolGraph queue health 宸茶繘鍏?status/report 瀹夊叏鎽樿锛?
   - CodeGraph 鏍稿疄 `status_summary()` 涓?`generate_report()` 宸茶兘鐪嬪埌 RuntimeState 涓殑 `tool_graphs` / `tool_graph_queue`锛屼絾姝ゅ墠缂哄皯涓撻棬鐨?queue/backpressure 鑱氬悎瑙嗗浘
   - 鏂板 `_tool_queue_health_summary_for_plan()`锛屼粠 RuntimeState 鑱氬悎 `queue_count`銆乣queued_count`銆乣running_count`銆乣blocked_count`銆乣terminal_count`銆乣active_count`銆乣queue_pressure`銆乹ueue/graph/node 鐘舵€佸垎甯?
   - `status_summary()` 涓?`generate_report()` 鍧囪繑鍥?`tool_queue_health_summary`锛涙憳瑕佸彧杈撳嚭璁℃暟銆佺姸鎬佸拰鎵规搴忓彿锛屼笉鏆撮湶 `graph_id`銆乣tool_call_id`銆乸rovider銆乁RL 鎴栫鏈夎矾寰?
   - Runtime 娴嬭瘯宸茶鐩栨壒娆″彧鍏ラ槦鏈?drain 鐨勫満鏅紝纭 status/report 鑳界湅鍒?queue pressure 鍜?queued 璁℃暟锛屼笖涓嶄細娉勯湶 `graph_id`
   - `verify_ultimate_plan.py` 鐨?Runtime report / validator gate 宸茶姹?status/report 鍜?helper 淇濈暀璇ユ憳瑕侊紝缁х画鎺ㄨ繘 `backpressure -> ToolCall state`

96. Phase 6/Review advisory proposal 鐘舵€佸凡杩涘叆 operation replay锛?
   - CodeGraph 鏍稿疄 `review_advisory_proposal_created` 涓?`review_advisory_confirmation_recorded` 宸插啓鍏?OperationLog锛屼絾 `_review_advisory_replay_summary()` 涔嬪墠鍙兘鐪嬪埌 created/confirmed 浜嬩欢鏁伴噺锛屼笉鑳藉垽鏂缓璁槸鍚︿粛寰呮埧涓荤‘璁?
   - `_review_advisory_replay_summary()` 鐜板湪鑱氬悎 `proposal_status_counts`銆乣pending_proposal_count`銆乣confirmed_proposal_count`銆乣rejected_proposal_count` 涓?`advisory_item_count`
   - 杩欎竴姝ヨ VLM / Reviewer 寤鸿鐨勨€滃彧鐢熸垚 proposal銆佷笉鐩存帴鏀瑰満鏅€佺瓑寰呯‘璁も€濆彲浠ヨ operation replay 璇佹槑锛岃€屼笉鏄彧渚濊禆鐢ㄦ埛鍙鏂囨
   - Runtime 娴嬭瘯宸茶鐩?review provider 鐢熸垚寤鸿銆佺‘璁ゅ墠 pending銆佺‘璁ゅ悗 confirmed 鐨?replay 鍙樺寲锛屼笖涓嶆毚闇叉埅鍥捐矾寰勩€乸rompt銆乸rovider raw 鎴栧唴閮?id
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹傝繖浜?review advisory replay 瀛楁淇濈暀锛岀户缁帹杩?`VLM 鍙骇鍑?proposal锛屼笉鐩存帴鏀瑰満鏅痐

97. Phase 6/Layout adjustment proposal 鐘舵€佸凡杩涘叆 operation replay锛?
   - CodeGraph 鏍稿疄 `layout_adjustment_requested` 涓?`layout_adjustment_confirmed` 宸插啓鍏?OperationLog锛屼絾 `_layout_adjustment_replay_summary()` 涔嬪墠涓昏缁熻鎵ц缁撴灉锛屾棤娉曡瘉鏄庡畬鎴愭€佸竷灞€璋冩暣寤鸿鏄惁浠嶅緟纭
   - `layout_adjustment_requested` 鐜板湪鍦?OperationLog 瀹夊叏 payload 涓褰?`proposal_id` 涓?`delta_count`锛屼笉鍐嶄緷璧栦細琚?safe replay 鍓ョ鐨勫祵濂?proposal
   - `_layout_adjustment_replay_summary()` 鐜板湪鑱氬悎 `proposal_status_counts`銆乣pending_proposal_count`銆乣confirmed_proposal_count`銆乣failed_proposal_count` 涓?`delta_count`
   - Runtime 娴嬭瘯宸茶鐩栧竷灞€寤鸿鍒涘缓鍚?pending銆佺‘璁ゆ墽琛屽悗 confirmed 鐨?replay 鍙樺寲锛屽悓鏃剁户缁獙璇?transform / selective ground snap 璁℃暟
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹傝繖浜?layout adjustment replay 瀛楁淇濈暀锛岀户缁帹杩?`瀹屾垚鎬佽皟鏁撮€氳繃 Reviewer + RuntimeGuard + ToolCall 鎵ц`

98. Phase 7/Sync asset transfer 鐢熷懡鍛ㄦ湡宸茶繘鍏?operation replay/report锛?
   - CodeGraph 鏍稿疄 `record_sync_event()` 宸叉妸 C++ / LANChat / engine 鐨?asset transfer 浜嬪疄鍐欏叆 RuntimeState `assets`銆乣sync_events` 涓?OperationLog锛屼絾姝ゅ墠 `operation_replay()` 鍙湁娉?`sync_summary`锛屼笉鑳藉崟鐙鐩?started / progress / completed / failed / peer-ready 鐢熷懡鍛ㄦ湡
   - 鏂板 `_asset_transfer_replay_summary()`锛屼粠瀹夊叏 OperationLog entries 涓?RuntimeState sync events 鑱氬悎 `asset_transfer_started_count`銆乣asset_transfer_progress_count`銆乣asset_transfer_completed_count`銆乣asset_transfer_failed_count`銆乣peer_asset_ready_count` 涓?`transfer_status_counts`
   - `operation_replay()` 涓?`_operation_replay_summary_for_report()` 鍧囪繑鍥?`asset_transfer_replay_summary`锛岃澶氫汉鍚屼紶妯″瀷鍗￠】銆佸け璐ャ€乸eer ready 绛夐棶棰樺彲浠ヤ粠 Runtime replay 鐩存帴瀹氫綅
   - 鎽樿鍙緭鍑?asset_id銆乸eer_id銆佺姸鎬併€乸rogress銆乧hunk 涓?bytes 璁℃暟锛屼笉鏆撮湶 `asset_path`銆乣message_id`銆乣correlation_id`銆乸rovider銆乁RL 鎴栫鏈夎矾寰?
   - Runtime 娴嬭瘯宸茶鐩?file chunk progress銆乧ompleted銆乸eer ready銆乫ailed 鐢熷懡鍛ㄦ湡锛屽苟纭 final report 鐨?replay summary 涓?operation replay 涓€鑷翠笖鏃犺矾寰勬硠闇?
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹傝繖浜?asset transfer replay 瀛楁淇濈暀锛岀户缁帹杩?`asset/model transfer facts -> RuntimeState / OperationLog / Report`

99. Phase 7/Sync `sync_status` 鏌ヨ宸插浐鍖?asset transfer lifecycle 蹇収锛?
   - CodeGraph 鏍稿疄 `sync_status` action 宸查€氳繃 `runtime.sync_status.snapshot` 鎶婂悓姝ョ姸鎬佸啓鍏ュ唴閮?`runtime-sync-status` RuntimeState fact锛屼絾姝ゅ墠蹇収鍙寘鍚?`sync_status`銆乣sync_replay`銆乣sync_health_digest` 涓?message delivery
   - `sync_status` action 鐜板湪浠?`operation_replay()` 璇诲彇 `asset_transfer_replay_summary`锛屽苟鎶婂畠绾冲叆杩斿洖鍊煎拰 `runtime.sync_status.snapshot` fact
   - `_record_sync_status_snapshot_tool()` 涓?`_sync_status_snapshot_via_tool_graph()` 鐨勫畨鍏?payload 鐜板湪璁板綍 asset transfer started / progress / completed / failed / peer-ready 璁℃暟锛屼究浜庣姸鎬佹煡璇㈣瘉鏄庢ā鍨嬪悓浼犵敓鍛藉懆鏈熷凡琚?Runtime 璇诲彇
   - `peer_asset_ready` 绛?peer ready 浜嬩欢鍦?Runtime 闀滃儚涓繘鍏?completed/ready 鐘舵€侊紝涓嶅啀琚褰掍负 transferring
   - Runtime 娴嬭瘯宸茶鐩?`sync_status` 鏌ヨ涓?asset transfer lifecycle 蹇収钀界洏銆丱perationLog export / snapshot 璁℃暟涓€鑷淬€佸け璐ュ垎鏀笉杩斿洖鏈惤鐩樻憳瑕侊紝浠ュ強璺緞/provider 涓嶆硠闇?
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸茶姹?`handle_message(sync_status)` 涓?sync status snapshot 淇濈暀 asset transfer lifecycle 瀛楁锛涜繖涓€姝ヤ粛涓嶆敼 C++ 缃戠粶浼犺緭锛屽彧鎺ㄨ繘鍚屾浜嬪疄璇讳晶 Runtime 鍖?

100. Phase 7/Sync peer lifecycle 涓?reconcile 鎽樿宸茶繘鍏?operation replay/report/sync_status锛?
   - CodeGraph 鏍稿疄 peer join / leave / room close 宸插湪 `record_sync_event()` 鍐欏叆 RuntimeState `sync_state.peer_events` 涓?OperationLog锛屼絾姝ゅ墠鍙兘浠庢硾 `sync_summary` 璇诲彇锛岀己灏戦潰鍚戝浜哄崗浣滃鐩樼殑鐙珛 peer/reconcile 鎽樿
   - 鏂板 `_peer_sync_replay_summary()`锛屼粠瀹夊叏 OperationLog entries 涓?RuntimeState sync events 鑱氬悎 `peer_event_count`銆乣peer_join_count`銆乣peer_leave_count`銆乣room_close_count`銆乣sync_reconcile_count`銆乣sync_reconcile_failed_count`銆乣state_reconcile_count`銆乣state_reconcile_failed_count`
   - `operation_replay()` 涓?`_operation_replay_summary_for_report()` 鍧囪繑鍥?`peer_sync_replay_summary`锛岃澶氫汉鑱旀満涓殑 peer 鐢熷懡鍛ㄦ湡鍜岀姸鎬佽ˉ鍋?鍐茬獊 reconcile 鍙互浠?Runtime replay 鐩存帴瀹氫綅
   - `sync_status` action 鐜板湪鎶?`peer_sync_replay_summary` 绾冲叆杩斿洖鍊煎拰 `runtime.sync_status.snapshot` fact锛沗runtime_sync_status_exported` 涓?`runtime_sync_status_snapshot_recorded` 涔熻褰?peer/reconcile 璁℃暟
   - 鎽樿鍙緭鍑?peer_id銆乪vent_type銆乺oom_status 鍜岃鏁帮紝涓嶆毚闇?`message_id`銆乣correlation_id`銆乸rovider銆乁RL銆乸rompt 鎴栫鏈夎矾寰?
   - Runtime 娴嬭瘯宸茶鐩?peer join + leave銆乻ync reconcile completed / failed銆乻tate patch reconcile completed / failed锛屼互鍙?sync_status 蹇収钀界洏锛沗verify_ultimate_plan.py` 宸叉妸 peer/reconcile replay 瀛楁鍔犲叆闈欐€侀棬绂?

101. Phase 4/BatchResourcePlan v2 鎵规璧勬簮闂幆鎽樿宸茶繘鍏?status/report锛?
   - 褰撳墠 Runtime 鎵ц鍥惧凡缁忓叿澶?`runtime.asset.image.prepare`銆乣runtime.asset.model.prepare`銆乣runtime.actor.import_batch`銆乣runtime.geometry.review`銆乣runtime.review.vlm_checkpoint` 涓?`runtime.review.summarize_batch` 绛夋壒娆¤祫婧愯妭鐐癸紱姝ゅ墠 `resource_summary` 鏇村亸闃舵鑱氬悎锛屾棤娉曠洿鎺ュ洖绛斺€滄瘡涓?batch 鐨勫浘鐗囥€佹ā鍨嬨€佸鍏ャ€佸鏌ユ槸鍚﹂棴鐜€?
   - 鏂板 `_batch_resource_flow_summary_for_plan()`锛屼粠 RuntimeState 鐨?`batch_plans`銆乣image_resource_plans`銆乣model_resource_plans`銆乣custom_import_facts`銆乣geometry_reviews`銆乣custom_vlm_checkpoint_facts` 涓?`custom_review_summary_facts` 鑱氬悎姣忔壒 `image/model/import/review` 鐘舵€?
   - `status_summary()` 涓?`generate_report()` 鍧囪繑鍥?`batch_resource_flow_summary`锛屽寘鍚?`batch_count`銆乣completed_count`銆乣partial_count`銆乣failed_count`銆乣waiting_count` 涓庢渶杩戞壒娆＄殑 ready/failure 璁℃暟
   - 鎽樿鍙緭鍑?batch_id銆佹壒娆″簭鍙枫€佺姸鎬佷笌瀹夊叏璁℃暟锛屼笉鏆撮湶 provider銆乸rompt銆乁RL銆佹ā鍨嬭矾寰勩€乀oolCallGraph nodes 鎴栧唴閮ㄥ紓甯告枃鏈?
   - Runtime 娴嬭瘯宸茶鐩栧畬鏁?mock 鎵规涓?image/model/import/review 鍏?ready 鏃剁殑 completed 鍒ゅ畾锛沗verify_ultimate_plan.py` 宸叉妸 `batch_resource_flow_summary` 鍔犲叆 status/report/helper 闈欐€侀棬绂?
   - 杩欎竴姝ヤ粛鏄?RuntimeState 璇讳晶涓庢姤鍛婁簨瀹炴簮鏀跺彛锛屼笉浠ｈ〃鐪熷疄 provider 宸插畬鎴愨€滃ぇ鍒嗘壒鍥剧墖鐢熸垚 -> 妯″瀷鐢熸垚 -> 瀵煎叆 -> 瀹℃煡鈥濈殑瀹炴満鎵ц鎺ョ

102. Phase 4/OperationLog 鎵规璧勬簮鐢熷懡鍛ㄦ湡宸茶繘鍏?replay/report锛?
   - CodeGraph 涓庡綋鍓嶆枃浠舵牳瀹炶祫婧愰樁娈靛凡缁忛€氳繃 `runtime_event_emitted` 璁板綍 `image_resources_ready/failed`銆乣model_resources_ready/failed`銆乣actors_imported/import_failed` 涓?environment component 浜嬩欢锛涙鍓嶈繖浜涗簨浠舵病鏈夌嫭绔嬬殑鎵规璧勬簮鐢熷懡鍛ㄦ湡 replay 鎽樿
   - 鏂板 `_batch_resource_lifecycle_replay_summary()`锛屼粠 OperationLog 鑱氬悎 `resource_event_count`銆乣image_ready_count`銆乣model_ready_count`銆乣import_ready_count`銆佸搴?failed 璁℃暟銆乣emit_failed_count`銆乣batch_event_counts` 涓?`latest_resource_event`
   - `operation_replay()` 涓?`_operation_replay_summary_for_report()` 鍧囪繑鍥?`batch_resource_lifecycle_summary`锛岃鈥滄湰鎵瑰浘鐗囥€佹ā鍨嬨€佸鍏ラ樁娈垫槸鍚︽浘琚?Runtime 浜嬩欢鍖栧苟钀藉叆鏃ュ織鈥濆彲浠ヨ replay 鍜屾渶缁堟姤鍛婅瘉鏄?
   - 鎽樿鍙鍙栧畨鍏?event_type銆乥atch_id 涓?persisted 鐘舵€侊紝涓嶆毚闇?provider銆乸rompt銆乁RL銆佹埅鍥捐矾寰勩€佹ā鍨嬭矾寰勩€乀oolCallGraph nodes 鎴栧唴閮ㄥ紓甯告枃鏈?
   - Runtime 娴嬭瘯宸茶鐩栧畬鏁?mock 鎵规鐨?image/model/import replay 璁℃暟锛屽苟纭 `generate_report()` 涓殑 `operation_replay_summary.batch_resource_lifecycle_summary` 涓?`operation_replay()` 涓€鑷?
   - `verify_ultimate_plan.py` 鐨?Runtime report fact-source gate 宸插姞鍏?helper銆乺eport 鍜?replay 鎺ュ叆闈欐€侀棬绂侊紱杩欎竴姝ョ户缁惤瀹炩€淥perationLog 蹇呴』鍏堜簬鐢ㄦ埛鎶ュ憡鈥濈殑涓嶅彉閲?

103. Phase 6/GM Summary 宸茶兘璇诲彇鎵规璧勬簮闂幆 digest锛?
   - CodeGraph 鏍稿疄 `gm_summary()` 鍙€氳繃 `status_summary()` 璇诲彇 RuntimeState / OperationLog 娲剧敓浜嬪疄锛涙鍓?GM summary 宸叉湁璁ㄨ涓婁笅鏂囥€佷粙鍏ユ憳瑕佸拰鍚屾鍋ュ悍锛屼絾缂哄皯闈㈠悜鈥滆祫婧愭壒娆℃槸鍚﹀崱浣?澶辫触/瀹屾垚鈥濈殑瀹夊叏鎽樿
   - `gm_summary()` 鐜板湪浠?`batch_resource_flow_summary` 娲剧敓 `resource_flow_digest`锛屽寘鍚?`batch_count`銆乣completed_count`銆乣partial_count`銆乣failed_count`銆乣waiting_count`銆佹渶杩戞壒娆＄殑 image/model/import ready 璁℃暟涓?review 鐘舵€?
   - `runtime_gm_summary_exported` OperationLog payload 杩藉姞 `resource_batch_count`銆乣resource_failed_count`銆乣resource_waiting_count`锛岀敤浜庡鐩?GM 鏄惁鐪嬭鎵规璧勬簮鍋ュ悍搴?
   - 鎽樿鍙緭鍑哄畨鍏ㄨ鏁般€乥atch 鐘舵€佸拰鏈€杩戞壒娆℃憳瑕侊紝涓嶆毚闇?provider銆乸rompt銆乁RL銆佹ā鍨嬭矾寰勩€乀oolCallGraph nodes 鎴栧唴閮ㄥ紓甯告枃鏈?
   - Runtime 娴嬭瘯宸茶鐩栧畬鏁?mock 鎵规鎵ц鍚?GM summary 鍙互鐪嬪埌璧勬簮闂幆瀹屾垚鐘舵€侊紝涓?`verify_ultimate_plan.py` 宸叉妸 `resource_flow_digest` 涓庡鍑鸿鏁板瓧娈靛姞鍏?Runtime GM summary 闈欐€侀棬绂?
   - 杩欎竴姝ユ帹杩?GM / Planner 浠?Runtime 浜嬪疄婧愯鍙栫敓鎴愯繘搴︿笌璧勬簮鍋ュ悍搴︼紱瀹屾暣璇箟浠茶銆侀暱鏈熻蹇嗗拰鍐茬獊鍐崇瓥绛栫暐浠嶆湭瀹屾垚

104. Phase 6/LANChat GM Runtime 鎽樿宸叉姭闇茶祫婧愭壒娆″仴搴凤細
   - CodeGraph 鏍稿疄 `LANChatAgentWorker._agent_runtime_gm_summary_reply()` 鏄?`@GM 鎬荤粨褰撳墠鏂规` 璧?Runtime summary 鍚庣殑鐢ㄦ埛鍙鍥炲闈紱姝ゅ墠 Runtime 鍐呴儴宸叉湁 `resource_flow_digest`锛屼絾鑱婂ぉ瀹ゅ洖澶嶅彧灞曠ず涓婁笅鏂囥€佷粙鍏ャ€佹ā鍨嬨€佸湴褰㈠拰澶氫汉鍚屾鍋ュ悍
   - 鏂板 `_format_agent_runtime_resource_flow_report()`锛屾妸 `resource_flow_digest` 杞垚瀹夊叏鏂囨湰锛氭壒娆℃暟銆乧ompleted/partial/failed/waiting 璁℃暟銆佹渶杩戞壒娆?image/model/import ready 璁℃暟銆乺eview 鐘舵€佸拰闇€鍏虫敞椤?
   - `銆怗M Runtime 鎽樿銆慲 鐜板湪澧炲姞 `璧勬簮鎵规锛?..` 琛岋紝鐢ㄦ埛/鎴夸富鍙洿鎺ョ湅鍒板ぇ鍒嗘壒璧勬簮闂幆鏄惁瀹屾垚銆佺瓑寰呮垨澶辫触锛岃€屼笉闇€瑕佹煡鐪嬪唴閮?report/replay
   - 鏂囨鍙緭鍑哄畨鍏ㄨ鏁板拰鐘舵€侊紝涓嶆毚闇?provider銆乸rompt銆乁RL銆佹ā鍨嬭矾寰勩€乀oolCallGraph nodes銆乼ool_name 鎴栧唴閮ㄥ紓甯告枃鏈?
   - LANChat Runtime guard 娴嬭瘯宸茶鐩?Runtime mock 鐢熸垚瀹屾垚鍚?`@GM 鎬荤粨褰撳墠鏂规` 鍥炲鍖呭惈璧勬簮鎵规鎽樿锛沗verify_ultimate_plan.py` 鐨?AgentRuntime flag boundary gate 宸茶姹?worker 淇濈暀璇?formatter 鍜?GM reply 鎺ュ叆
   - 杩欎竴姝ョ户缁帹杩?GM / Planner 鐨?Runtime 浜嬪疄鍙鎬э紝浣嗕笉鏀瑰彉鐪熷疄 provider銆佷笉瑙︾ C++/Quasar锛屼篃涓嶄唬琛ㄧ湡瀹炲ぇ鍒嗘壒鎵ц宸插畬鎴?

105. Phase 6/LANChat 鏅€?Runtime 鐘舵€佸洖澶嶅凡鎶湶璧勬簮鎵规鍋ュ悍锛?
   - CodeGraph 鏍稿疄 `LANChatAgentWorker._agent_runtime_status_reply()` 鏄敤鎴疯闂€滆繘搴?/ 鍒板摢浜?/ 褰撳墠鐘舵€佲€濇椂鐨?Runtime-first 鍥炲闈紱姝ゅ墠璇ュ洖澶嶅凡鏈夎祫婧愰€氶亾鍜岃祫婧愬彲鐢ㄦ€э紝浣嗙己灏戞寜 batch 鑱氬悎鐨勮祫婧愰棴鐜憳瑕?
   - `_agent_runtime_status_reply()` 鐜板湪璇诲彇 `batch_resource_flow_summary`锛屽鐢?`_format_agent_runtime_resource_flow_report()` 杈撳嚭 `璧勬簮鎵规锛?..`
   - 鏄惧紡 batch 鏌ヨ浼氭樉绀哄綋鍓?batch 鐨?completed/failed/waiting 绛夊畨鍏ㄧ姸鎬侊紱鍏ㄨ鍒掔姸鎬佹煡璇細鏄剧ず鏁翠綋鎵规璧勬簮鍋ュ悍锛屽府鍔╁尯鍒嗏€滄柟妗堢姸鎬佹甯糕€濅笌鈥滃浘鐗?妯″瀷/瀵煎叆鎵规鍗′綇鈥?
   - 鏂囨鍙緭鍑哄畨鍏ㄨ鏁板拰鐘舵€侊紝涓嶆毚闇?provider銆乸rompt銆乁RL銆佹ā鍨嬭矾寰勩€乀oolCallGraph nodes銆乼ool_name 鎴栧唴閮ㄥ紓甯告枃鏈?
   - LANChat Runtime guard 娴嬭瘯宸茶鐩栨樉寮?batch 鐘舵€佸洖澶嶅寘鍚祫婧愭壒娆℃憳瑕侊紱`verify_ultimate_plan.py` 鐨?AgentRuntime flag boundary gate 宸茶姹?status reply 淇濈暀 `batch_resource_flow_summary` 鍜?formatter 鎺ュ叆
   - 杩欎竴姝ョ户缁В鍐崇敤鎴蜂綋鎰熶笂鐨勨€滈棶鐘舵€佷絾鐪嬩笉鍒拌祫婧愰樁娈电湡瀹炶繘灞曗€濓紱鐪熷疄 provider 澶у垎鎵规墽琛屼粛寰呭悗缁?F5 楠岃瘉

106. Phase 5/LANChat Operation Replay 宸叉姭闇叉壒娆¤祫婧愮敓鍛藉懆鏈燂細
   - CodeGraph 鏍稿疄 `_handle_agent_runtime_operation_replay_query()` 鏄?`@GM runtime operation replay` 鐨勭敤鎴峰彲瑙佽瘖鏂潰锛汻untime replay 鍐呴儴宸叉湁 `batch_resource_lifecycle_summary`锛屼絾鑱婂ぉ瀹ゅ洖澶嶆鍓嶅彧灞曠ず entry/event/context/review/engine/message/recent
   - 鏂板 `_format_agent_runtime_batch_resource_lifecycle_report()`锛屾妸 image/model/import/environment lifecycle ready/failed 璁℃暟鍜屾渶杩戣祫婧愪簨浠惰浆鎴愬畨鍏ㄦ枃鏈?
   - `銆怰untime Operation Replay銆慲 鐜板湪澧炲姞 `batch_resources: ...` 琛岋紝鏀寔鎸?room/plan/batch 澶嶇洏璧勬簮闃舵鏄惁浜嬩欢鍖栧苟钀藉叆 OperationLog
   - 鏂囨涓嶆毚闇?provider銆乸rompt銆乁RL銆佹ā鍨嬭矾寰勩€乀oolCallGraph nodes銆乼ool_name 鎴栧唴閮ㄥ紓甯告枃鏈?
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊甯?metadata batch scope 鐨?replay 鏌ヨ鍙樉绀虹洰鏍?batch 鐨勮祫婧愮敓鍛藉懆鏈燂紱`verify_ultimate_plan.py` 宸茶姹?formatter 鍜?reply 鎺ュ叆
   - 杩欎竴姝ョ户缁妸 F5 鏃ュ織璇婃柇鍏ュ彛杩佸叆 Runtime OperationLog锛涚湡瀹?provider 澶у垎鎵规墽琛屼粛寰呭悗缁?F5 楠岃瘉

107. Phase 5/LANChat Operation Replay 宸叉姭闇?Runtime command 闃熷垪褰卞搷锛?
   - CodeGraph 鏍稿疄 Runtime replay 鍐呴儴宸叉湁 `runtime_command_summary`锛屽彲鑱氬悎 pause/cancel/resume/retry 绛夊懡浠ょ殑鐘舵€佽縼绉汇€佸彇娑堟壒娆℃暟銆佸彇娑?graph 鏁般€佹仮澶?graph 鏁板拰閲嶈瘯 graph 鏁?
   - 鏂板 `_format_agent_runtime_replay_command_report()`锛屼笓闂ㄩ€傞厤 replay 鐨?`latest_command` 涓?queue-impact 璁℃暟瀛楁锛岄伩鍏嶅鐢ㄦ櫘閫?report/status command formatter 鏃跺洜缁撴瀯涓嶅悓鑰屾樉绀?`none`
   - `銆怰untime Operation Replay銆慲 鐜板湪澧炲姞 `commands: ...` 琛岋紝鏀寔鎸?room/plan/batch 澶嶇洏杩愯鏃跺懡浠ゆ槸鍚︾湡姝ｅ奖鍝?Runtime queue / batch / graph
   - 鏂囨鍙緭鍑哄懡浠よ鏁般€佺姸鎬佽縼绉诲拰鍙栨秷/鎭㈠/閲嶈瘯璁℃暟锛屼笉鏆撮湶 command_id銆乼ool_call_id銆乬raph_id銆乸rovider銆乸rompt銆乁RL 鎴栧唴閮ㄥ紓甯告枃鏈?
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊甯?metadata batch scope 鐨?replay 鏌ヨ鏄剧ず鐩爣 batch 鐨?runtime command 褰卞搷锛沗verify_ultimate_plan.py` 宸茶姹?replay command formatter 鍜?reply 鎺ュ叆
   - 杩欎竴姝ョ户缁帹杩涒€滄殏鍋?鍙栨秷/鎭㈠涓嶆槸鑱婂ぉ鏂囨锛岃€屾槸 Runtime OperationLog 鍙鐩樹簨瀹炩€濈殑 Phase 5 鐩爣

108. Phase 5/LANChat Operation Replay 宸叉姭闇?ToolCall 涓?ToolGraph queue 鎽樿锛?
   - CodeGraph 鏍稿疄 Runtime replay 鍐呴儴宸叉湁 `tool_execution_summary` 鍜?`tool_graph_queue_summary`锛屽彲鑱氬悎 ToolCall started/succeeded/failed/blocked/retry/skipped 涓?ToolGraph queued/dequeued/completed/rejected/blocked/missing
   - 鏂板 `_format_agent_runtime_replay_tool_execution_report()` 涓?`_format_agent_runtime_replay_tool_queue_report()`锛屾妸宸ュ叿鎵ц鍜岄槦鍒楃敓鍛藉懆鏈熻浆鎴愬畨鍏ㄨ鏁版枃鏈?
   - `銆怰untime Operation Replay銆慲 鐜板湪澧炲姞 `tools: ...` 鍜?`queue: ...` 琛岋紝鏀寔鎸?room/plan/batch 澶嶇洏 ToolCallGraph 鏄惁鐪熺殑鎵ц銆佹槸鍚﹁闃熷垪闃诲鎴栫己澶?
   - 鏂囨鍙緭鍑轰簨浠惰鏁般€佺姸鎬佸拰鏈€杩戝畨鍏ㄤ簨浠跺悕锛屼笉鏆撮湶 graph_id銆乼ool_call_id銆乼ool_name銆乼ool args銆乸rovider銆乸rompt銆乁RL 鎴栧唴閮ㄥ紓甯告枃鏈?
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊甯?metadata batch scope 鐨?replay 鏌ヨ鏄剧ず鐩爣 batch 鐨?tool execution 涓?queue 鎽樿锛沗verify_ultimate_plan.py` 宸茶姹備袱涓?formatter 鍜?replay reply 鎺ュ叆
   - 杩欎竴姝ョ户缁惤瀹?`ToolCallGraph 鏄敮涓€鎵ц缂栨帓` 涓?`OperationLog 蹇呴』鍏堜簬鐢ㄦ埛鎶ュ憡` 涓ゆ潯鏋舵瀯涓嶅彉閲?

109. Phase 5/LANChat Operation Replay 宸叉姭闇?RuntimeState patch 涓?RuntimeGuard 鎽樿锛?
   - CodeGraph 鏍稿疄 Runtime replay 鍐呴儴宸叉湁 `state_patch_summary` 鍜?`runtime_guard_replay_summary`锛屽彲鑱氬悎 RuntimeState patch version/applied/conflict/invalid/reconcile 浜嬩欢锛屼互鍙?RuntimeGuard blocked/high-risk/write-confirm/system-actor 绛夊啓鏉冮檺鍒ゆ柇浜嬩欢
   - 鏂板 `_format_agent_runtime_replay_state_patch_report()` 涓?`_format_agent_runtime_replay_guard_report()`锛屾妸鐘舵€佸悎骞剁粨鏋滃拰鍐欐潈闄愭嫤鎴粨鏋滆浆鎴愬畨鍏ㄨ鏁版枃鏈?
   - `銆怰untime Operation Replay銆慲 鐜板湪澧炲姞 `state_patch: ...` 鍜?`guard: ...` 琛岋紝鏀寔鎸?room/plan/batch 澶嶇洏鐘舵€佹槸鍚︾湡姝ｈ惤鐩樸€佸啓宸ュ叿鏄惁琚?RuntimeGuard 鎷︽埅
   - 鏂囨鍙緭鍑轰簨浠惰鏁般€佺姸鎬佸拰瀹夊叏鍘熷洜绫诲埆锛屼笉鏆撮湶 patch_id銆乼ool_call_id銆乤ctor_id銆乬raph_id銆乼ool args銆乸rovider銆乸rompt銆乁RL 鎴栧唴閮ㄥ紓甯告枃鏈?
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊甯?metadata batch scope 鐨?replay 鏌ヨ鏄剧ず鐩爣 batch 鐨?state patch 涓?guard 鎽樿锛沗verify_ultimate_plan.py` 宸茶姹備袱涓?formatter 鍜?replay reply 鎺ュ叆
   - 杩欎竴姝ョ户缁惤瀹?`RuntimeGuard 鏄敮涓€鍐欐潈闄愬垽鏂璥銆乣RuntimeState 鏄敮涓€鐘舵€佷簨瀹炴簮` 鍜?`OperationLog 蹇呴』鍏堜簬鐢ㄦ埛鎶ュ憡` 涓夋潯鏋舵瀯涓嶅彉閲?

110. Phase 5/LANChat Operation Replay 宸叉姭闇?ScenePlan 鐢熷懡鍛ㄦ湡涓庝粙鍏ユ壒娆℃憳瑕侊細
   - CodeGraph 涓庡綋鍓嶄唬鐮佹牳瀹?Runtime replay 鍐呴儴宸叉湁 `scene_plan_lifecycle_summary` 鍜?`intervention_batch_replay_summary`锛屽彲鑱氬悎 ScenePlan created/confirmed/state/status/extracted 鐢熷懡鍛ㄦ湡锛屼互鍙?pending intervention routed/queued/persisted/skipped/absorbed 鎵规浜嬩欢
   - 鏂板 `_format_agent_runtime_replay_plan_lifecycle_report()` 涓?`_format_agent_runtime_replay_intervention_report()`锛屾妸鏂规鐢熷懡鍛ㄦ湡鍜岀敤鎴?Agent 涓€斾粙鍏ユ壒娆¤矾鐢辩粨鏋滆浆鎴愬畨鍏ㄨ鏁版枃鏈?
   - `銆怰untime Operation Replay銆慲 鐜板湪澧炲姞 `plan_lifecycle: ...` 鍜?`interventions: ...` 琛岋紝鏀寔鎸?room/plan/batch 澶嶇洏鏂规鏄惁鍒涘缓/纭銆佷粙鍏ユ槸鍚﹁繘鍏ュ悗缁壒娆℃垨琚惛鏀?
   - 鏂囨鍙緭鍑轰簨浠惰鏁般€佺姸鎬佸拰鏈€杩戝畨鍏ㄤ簨浠剁被鍒紝涓嶆毚闇?plan raw prompt銆乸atch_id銆乼ool_call_id銆乬raph_id銆乺equested item prompt銆乸rovider銆乁RL 鎴栧唴閮ㄥ紓甯告枃鏈?
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 active plan replay 鍙 plan lifecycle锛宮etadata batch scope replay 鍙鐩爣 batch 鐨?intervention routing/absorption锛沗verify_ultimate_plan.py` 宸茶姹備袱涓?formatter 鍜?replay reply 鎺ュ叆
   - 杩欎竴姝ョ户缁帹杩涘浜?澶?Agent 鍔ㄦ€佷粙鍏ヤ粠鈥滆亰澶╄褰曡В閲娾€濊縼绉讳负 Runtime OperationLog 鍙鐩樹簨瀹?

111. Phase 5/LANChat Operation Replay 宸叉姭闇?RuntimeEvent 涓庡け璐ョ瓥鐣ユ憳瑕侊細
   - CodeGraph 涓庡綋鍓嶄唬鐮佹牳瀹?Runtime replay 鍐呴儴宸叉湁 `runtime_event_replay_summary` 鍜?`tool_failure_strategy_summary`锛屽彲鑱氬悎鐢ㄦ埛鍙 RuntimeEvent emitted/failed/type counts锛屼互鍙?ToolCall retry/skipped/abandoned/handler_failed/invalid_result/state_conflict 绛夊け璐ュ鐞嗙瓥鐣?
   - 鏂板 `_format_agent_runtime_replay_runtime_event_report()` 涓?`_format_agent_runtime_replay_failure_strategy_report()`锛屾妸浜嬩欢鎶湶鍜屽け璐ョ瓥鐣ヨ浆鎴愬畨鍏ㄨ鏁版枃鏈?
   - `銆怰untime Operation Replay銆慲 鐜板湪澧炲姞 `runtime_events: ...` 鍜?`failure_strategy: ...` 琛岋紝鏀寔鎸?room/plan/batch 澶嶇洏鐢ㄦ埛鍙杩涘害浜嬩欢鏄惁鍙戝嚭銆佸け璐ユ槸鍚︽寜 Runtime 绛栫暐閲嶈瘯/璺宠繃/涓㈠純 late result
   - 鏂囨鍙緭鍑轰簨浠惰鏁般€佺被鍨嬪垎甯冦€佺瓥鐣ョ被鍒拰瀹夊叏鐘舵€侊紝涓嶆毚闇?event payload銆乼ool args銆乸rovider銆乸rompt銆乁RL銆乪rror raw 鎴栧唴閮ㄥ紓甯告枃鏈?
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊鐩爣 batch 鐨?runtime event 涓?retry strategy 鎽樿锛沗verify_ultimate_plan.py` 宸茶姹備袱涓?formatter 鍜?replay reply 鎺ュ叆
   - 杩欎竴姝ョ户缁帹杩涒€滆祫婧愰暱鑰楁椂鎶湶銆佸け璐ラ檷绾с€侀噸璇?璺宠繃绛栫暐鈥濅粠鏃ф棩蹇楄瘖鏂縼绉讳负 Runtime OperationLog 鍙洖鏀句簨瀹?

112. Phase 5/LANChat Operation Replay 宸叉姭闇?VLM checkpoint 涓庡竷灞€璋冩暣鎽樿锛?
   - CodeGraph 涓庡綋鍓嶄唬鐮佹牳瀹?Runtime replay 鍐呴儴宸叉湁 `vlm_checkpoint_summary` 鍜?`layout_adjustment_summary`锛屽彲鑱氬悎 VLM checkpoint/advisory/status/type 涓?layout adjustment request/confirm/apply/transform/ground snap/overlap 缁撴灉
   - 鏂板 `_format_agent_runtime_replay_vlm_report()` 涓?`_format_agent_runtime_replay_layout_report()`锛屾妸澶栬瀹℃煡鍜屽畬鎴愭€佸竷灞€璋冩暣闂幆杞垚瀹夊叏璁℃暟鏂囨湰
   - `銆怰untime Operation Replay銆慲 鐜板湪澧炲姞 `vlm: ...` 鍜?`layout: ...` 琛岋紝鏀寔鎸?room/plan/batch 澶嶇洏 VLM 鏄惁瀹為檯鍙備笌銆佸竷灞€璋冩暣鏄惁浜х敓 proposal 骞舵墽琛?transform/璐村湴/閬胯
   - 鏂囨鍙緭鍑轰簨浠惰鏁般€佺姸鎬佸拰 checkpoint/proposal 绫诲埆锛屼笉鏆撮湶鎴浘璺緞銆乸rompt銆乸rovider銆乤ctor_id銆乬raph_id銆乼ool args銆乁RL 鎴栧唴閮ㄥ紓甯告枃鏈?
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊鐩爣 batch 鐨?VLM checkpoint 涓?layout adjustment 鎽樿锛沗verify_ultimate_plan.py` 宸茶姹備袱涓?formatter 鍜?replay reply 鎺ュ叆
   - 杩欎竴姝ョ户缁妸鈥淰LM 鏄惁鐢熸晥鈥濆拰鈥滆皟鏁村竷灞€鏄惁闂幆鈥濅粠 F5 浣撴劅/鏃ュ織鐚滄祴杩佺Щ涓?Runtime OperationLog 鍙洖鏀句簨瀹?

113. Phase 4/5 LANChat Operation Replay 宸叉姭闇茬幆澧冪粍浠朵笌璧勬簮鍙敤鎬ф憳瑕侊細
   - CodeGraph 涓庡綋鍓嶄唬鐮佹牳瀹?Runtime replay 鍐呴儴宸叉湁 `environment_component_summary` 鍜?`resource_readiness_replay_summary`锛屽彲鑱氬悎 environment component ready/failed/import/import_failed锛屼互鍙?resource readiness status query/publish/event/status counts
   - 鏂板 `_format_agent_runtime_replay_environment_report()` 涓?`_format_agent_runtime_replay_resource_readiness_report()`锛屾妸鍦板舰/鐜缁勪欢鍜岃祫婧愰€氶亾棰勬缁撴灉杞垚瀹夊叏璁℃暟鏂囨湰
   - `銆怰untime Operation Replay銆慲 鐜板湪澧炲姞 `environment: ...` 鍜?`resource_readiness: ...` 琛岋紝鏀寔鎸?room/plan/batch 澶嶇洏鍦板舰/杈圭晫/鐜缁勪欢鏄惁杩涘叆 RuntimeEvent锛屼互鍙婅祫婧愰€氶亾 readiness 鏄惁鍙戝竷
   - RuntimeEvent formatter 宸插皢 `provider_readiness` 绛夊唴閮ㄤ簨浠舵爣绛惧畨鍏ㄦ敼鍐欎负 `resource-readiness`锛岀敤鎴峰洖澶嶄笉鏆撮湶 provider銆乸rompt銆乁RL銆乺aw銆乼oken銆丄PI key 鎴栧唴閮ㄨ矾寰?
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊鐩爣 batch 鐨?environment component 涓?resource readiness 鎽樿锛屽苟缁х画鏍￠獙鍥炲涓嶅嚭鐜?`provider` / `prompt`锛沗verify_ultimate_plan.py` 宸茶姹備袱涓?formatter 鍜?replay reply 鎺ュ叆
   - 杩欎竴姝ョ户缁妸鈥滃紑鏀惧満鏅?substrate/terrain 鏄惁娲剧敓鈥濆拰鈥滆祫婧愰€氶亾鏄惁鍙敤鈥濅粠 F5 鏃ュ織鍒ゆ柇杩佺Щ涓?Runtime OperationLog 鍙洖鏀句簨瀹?

114. Phase 7/LANChat Operation Replay 宸叉姭闇插浜哄悓姝ャ€佹ā鍨嬪悓浼犱笌 peer 鎽樿锛?
   - CodeGraph 涓庡綋鍓嶄唬鐮佹牳瀹?Runtime replay 鍐呴儴宸叉湁 `sync_summary`銆乣asset_transfer_replay_summary`銆乣peer_sync_replay_summary`锛屽彲鑱氬悎 actor sync銆乤sset transfer progress/completed/failed銆乸eer join/leave/reconcile 绛夊浜鸿仈鏈哄満鏅簨瀹?
   - LANChat Operation Replay 鏌ヨ灞傛柊澧?`sync: ...`銆乣asset_transfer: ...`銆乣peer_sync: ...` 涓夎瀹夊叏鎽樿锛屽苟鎶?replay 鏌ヨ绐楀彛浠?20 鏉℃彁鍗囧埌 50 鏉★紝閬垮厤璧勬簮銆乂LM銆佸竷灞€銆佸悓姝ヤ簨浠朵簰鐩告尋鎺?
   - 鏂板 `_format_agent_runtime_replay_asset_transfer_report()` 涓?`_format_agent_runtime_replay_peer_sync_report()`锛屽鐢ㄦ棦鏈?`_format_agent_runtime_sync_replay_report()`锛屽彧杈撳嚭璁℃暟銆佽繘搴︺€乧hunk/bytes銆佸畬鎴?澶辫触涓?reconcile 鐘舵€?
   - 鏂囨涓嶆毚闇?`peer_id`銆乣asset_id`銆佹枃浠惰矾寰勩€乵essage_id銆乸rovider銆乸rompt銆乁RL銆乺aw payload銆乼oken 鎴?API key锛涙祴璇曚腑鏄惧紡娉ㄥ叆 secret peer/asset/path 骞舵牎楠屼笉浼氬嚭鐜板湪鍥炲閲?
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊鐩爣 batch 鐨?actor transform銆乤sset transfer progress銆乸eer asset ready銆乸eer join 涓?sync reconcile 鎽樿锛沗verify_ultimate_plan.py` 宸茶姹備笁涓?replay summary銆乫ormatter 鍜屽洖澶嶈鎺ュ叆
   - 杩欎竴姝ョ户缁妸鈥滃浜鸿仈鏈烘ā鍨?actor 鍚屾鏄惁鍗￠】銆佹槸鍚﹀畬鎴愩€佹槸鍚﹂噸鏀句竴鑷粹€濅粠 F5 鏃ュ織缁忛獙杩佺Щ涓?Runtime OperationLog 鍙洖鏀句簨瀹?

115. Phase 7/LANChat Runtime Report 宸叉秷璐瑰悓姝?replay 鎽樿锛?
   - CodeGraph 鏍稿疄 `[Runtime Report]` 鍘熷厛鍙樉绀?`sync_summary` 鍜?`asset_transfer_summary` 鐨勫綋鍓嶇姸鎬侊紝娌℃湁娑堣垂 `operation_replay_summary` 涓殑 `sync_replay_summary`銆乣asset_transfer_replay_summary`銆乣peer_sync_replay_summary`
   - `_handle_agent_runtime_report_query()` 鐜板湪浠?report 鐨?`operation_replay_summary` 璇诲彇涓夌被 replay 鎽樿锛屽苟鏂板 `sync replay: ...`銆乣asset transfer replay: ...`銆乣peer sync replay: ...` 鐢ㄦ埛鍙琛?
   - 杩欒 Runtime Report 鍚屾椂鍥炵瓟鈥滃綋鍓嶅悓姝?鍚屼紶鐘舵€佹槸浠€涔堚€濆拰鈥滄湰杞?replay 閲屽疄闄呭彂鐢熻繃鍝簺 actor sync銆乤sset transfer銆乸eer join/reconcile 浜嬩欢鈥?
   - 鏂囨澶嶇敤 Operation Replay 鐨勫畨鍏?formatter锛屽彧杈撳嚭璁℃暟銆佽繘搴︺€乧hunk/bytes銆佸畬鎴?澶辫触鍜?reconcile 鐘舵€侊紝涓嶆毚闇?peer_id銆乤sset_id銆佸唴閮ㄨ矾寰勩€乵essage_id銆乸rovider銆乸rompt銆乁RL 鎴?raw payload
   - LANChat Runtime guard 鎶ュ憡娴嬭瘯宸叉敞鍏?peer/asset/path/message secret 骞舵牎楠?report 涓嶆硠闇诧紱`verify_ultimate_plan.py` 宸叉妸 Runtime Report 鐨勪笁绫?replay 琛岀撼鍏ラ潤鎬侀棬绂?
   - 杩欎竴姝ョ户缁惤瀹?`OperationLog 蹇呴』鍏堜簬鐢ㄦ埛鎶ュ憡`锛屽苟璁╁浜哄悓姝ヨ瘖鏂笉鍙仠鐣欏湪涓撶敤 operation replay 鏌ヨ閲岋紝涔熻繘鍏ユ寮?Runtime Report

116. Phase 7/GM Runtime 鎽樿宸叉秷璐瑰悓姝?replay digest锛?
   - CodeGraph 鏍稿疄 `gm_summary()` 鍘熷厛鍙秷璐?`sync_health_digest`锛孏M 鎽樿鑳界湅鍒板悓姝ュ仴搴风姸鎬侊紝浣嗕笉鑳界湅鍒版湰杞?OperationLog 涓?asset transfer / peer join / reconcile 鐨勫洖鏀句簨瀹?
   - `status_summary()` 鐜板湪鍚屾淇濈暀 `asset_transfer_replay_summary` 涓?`peer_sync_replay_summary`锛宍gm_summary()` 浠?`sync_replay_summary`銆乣asset_transfer_replay_summary`銆乣peer_sync_replay_summary` 娲剧敓 `sync_replay_digest`
   - LANChat GM 鎽樿鏂板 `鍚屾澶嶇洏锛?..`锛岀敤绱у噾鏍煎紡鏄剧ず recorded/failed銆乤ctor transform/delete銆乤sset progress/completed/failed銆乸eer-ready銆乸eer join/leave銆乺econcile 璁℃暟
   - 鏂囨鍙緭鍑?digest 璁℃暟锛屼笉鏆撮湶 peer_id銆乤sset_id銆佸唴閮ㄨ矾寰勩€乵essage_id銆乸rovider銆乸rompt銆乁RL 鎴?raw payload锛涙祴璇曟樉寮忔敞鍏?secret peer/asset/path 骞舵牎楠屼笉浼氬嚭鐜板湪 `@GM 鎬荤粨褰撳墠鏂规` 鍥炲涓?
   - `verify_ultimate_plan.py` 宸茶姹?Runtime `gm_summary()` 浜у嚭 `sync_replay_digest`锛屽苟瑕佹眰 LANChat GM summary reply 鏄剧ず `鍚屾澶嶇洏`
   - 杩欎竴姝ヨ GM 鎬荤粨浠庘€滃彧瑙ｉ噴褰撳墠鍋ュ悍鐘舵€佲€濇帹杩涗负鈥滃彲鍩轰簬 OperationLog 瑙ｉ噴鏈疆鍚屾/鍚屼紶鍙戠敓杩囦粈涔堚€濓紝缁х画钀藉疄 `RuntimeState 鏄敮涓€鐘舵€佷簨瀹炴簮` 涓?`OperationLog 蹇呴』鍏堜簬鐢ㄦ埛鎶ュ憡`

117. Phase 7/LANChat Runtime 鐘舵€佸洖澶嶅凡娑堣垂鍚屼紶/peer replay 鎽樿锛?
   - CodeGraph 鏍稿疄 `_agent_runtime_status_reply()` 鍘熷厛鍙樉绀?`sync_replay_summary`锛屼絾娌℃湁璇诲彇 `asset_transfer_replay_summary` 涓?`peer_sync_replay_summary`
   - Runtime 鏅€氱姸鎬佸洖澶嶇幇鍦ㄦ柊澧?`鍚屼紶澶嶇洏锛?..` 涓?`Peer 澶嶇洏锛?..`锛岃ˉ榻?asset transfer progress/completed/failed銆乸eer-ready銆乸eer join/leave/reconcile 绛夋壒娆¤寖鍥翠簨瀹?
   - 璇ュ洖澶嶄粛淇濈暀鍘熸湁 `澶氫汉鍚屾锛氬綋鍓嶇姸鎬侊紱鍋ュ悍锛涘鐩榒 涓?`妯″瀷鍚屼紶锛氬綋鍓嶇姸鎬乣锛屾柊澧炲唴瀹圭敤浜庡尯鍒嗏€滃綋鍓嶅悓浼犵姸鎬佲€濆拰鈥淥perationLog 涓疄闄呭彂鐢熻繃鐨勫悓浼?peer 浜嬩欢鈥?
   - 鏂囨澶嶇敤瀹夊叏 replay formatter锛屽彧杈撳嚭璁℃暟銆佽繘搴︺€乧hunk/bytes 鍜岀姸鎬侊紝涓嶆毚闇?peer_id銆乤sset_id銆佸唴閮ㄨ矾寰勩€乵essage_id銆乸rovider銆乸rompt銆乁RL 鎴?raw payload
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊甯?metadata batch scope 鐨勭姸鎬佹煡璇紝骞舵牎楠屽悓浼?peer replay 鍙樉绀虹洰鏍?batch 璁℃暟涓斾笉娉勯湶 secret锛沗verify_ultimate_plan.py` 宸茶姹?Runtime status reply 鎺ュ叆涓ょ被 replay formatter 鍜岀敤鎴峰彲瑙佽
   - 杩欎竴姝ヨ `@GM 褰撳墠鐘舵€乣銆乣@GM runtime report`銆乣@GM runtime operation replay`銆乣@GM 鎬荤粨褰撳墠鏂规` 鍥涚被鍏ュ彛閮借兘浠?RuntimeState/OperationLog 娑堣垂鍚屾鍥炴斁浜嬪疄

118. Phase 7/RuntimeEvent 鐢ㄦ埛鍙鎶湶宸查€忎紶瀹夊叏浜嬩欢 metadata锛?
   - CodeGraph 鏍稿疄 `_emit_agent_runtime_events_since()` 鍘熷厛鑳芥妸 RuntimeEvent 杞垚鑱婂ぉ瀹ょ郴缁熸秷鎭紝浣?`_send_agent_runtime_system_event()` 鍙彂閫?`phase/room_id`锛屽墠绔?鍚屾灞傛棤娉曠ǔ瀹氭寜 event銆乸lan銆乥atch銆乻tage銆乸rogress 鍘诲幓閲嶅拰瀵归綈
   - 鏂板 `_safe_runtime_event_metadata()`锛屽彧鐧藉悕鍗曡緭鍑?`runtime_event_id`銆乣runtime_event_type`銆乣runtime_plan_id`銆乣runtime_batch_id`銆乣runtime_stage`銆乣runtime_progress`锛屽苟瑁佸壀 progress 鍒?0-100
   - RuntimeEvent 鍙戦€佽矾寰勭幇鍦ㄤ互 `line + event` 鎴愬浼犻€掞紝`network_send_system_message_ex()` 鐨?metadata 涓?OperationLog audit payload 鍧囨惡甯﹀悓涓€浠藉畨鍏ㄤ簨浠跺瓧娈?
   - 鏂囨鍜?metadata 涓嶉€忎紶 event payload銆乸rovider銆乸rompt銆乤sset_path銆乁RL銆乺aw 鎴?token锛涙祴璇曟樉寮忔敞鍏?secret provider/prompt/path 骞舵牎楠屽彲瑙佹秷鎭笌 replay 鍧囦笉娉勯湶
   - `verify_ultimate_plan.py` 宸茶姹?RuntimeEvent sender 鎺ユ敹 `runtime_event` 骞惰姹?metadata helper 浜у嚭鍏釜瀹夊叏瀛楁锛岀户缁惤瀹?`OperationLog 蹇呴』鍏堜簬鐢ㄦ埛鎶ュ憡` 鍜?UI 闃舵鎶湶鍙榻?

119. Phase 7/RuntimeEvent 鎶湶 metadata 宸叉惡甯?audience / level 璇箟锛?
   - CodeGraph 鏍稿疄 `RuntimeEvent` 鏈韩宸叉湁 `audience` 涓?`level` 瀛楁锛屼絾 LANChat 绯荤粺娑堟伅 metadata 鍘熷厛娌℃湁浼犻€掕繖涓や釜璇箟锛屽墠绔?鍚屾灞傛棤娉曞尯鍒?host-only銆乸articipants銆亀arning銆乪rror 绛夊睍绀虹瓥鐣?
   - `_safe_runtime_event_metadata()` 鐜板湪浠呭湪 allowlist 鍐呰緭鍑?`runtime_audience` 涓?`runtime_level`锛岄潪娉曞€间笉浼氳繘鍏ョ敤鎴峰彲瑙?metadata
   - OperationLog audit payload 涓?replay snapshot schema 鍚屾鏀捐杩欎袱涓畨鍏ㄥ瓧娈碉紝淇濊瘉鍙娑堟伅銆佸璁°€佸鐩樹笁澶勮涔変竴鑷?
   - 鏈楠や笉鏀瑰彉 C++ 缃戠粶鍙戦€佽涓猴紝涔熶笉澹扮О宸茬粡瀹屾垚鍓嶇鍒嗕紬鏄剧ず锛涘畠鍙槸鎶?RuntimeState 鐨勫彲瑙佹€?涓ラ噸绾у埆浜嬪疄瀹夊叏甯﹀埌 UI metadata 杈圭晫
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 `host + warning` 浜嬩欢 metadata 涓?replay payload锛沗verify_ultimate_plan.py` 宸茶姹?metadata helper 淇濈暀 `runtime_audience` / `runtime_level`

120. Phase 7/LANChat 鑷姩 RuntimeEvent 鎶湶宸茶繃婊ら潪鐢ㄦ埛 audience锛?
   - CodeGraph 鏍稿疄 `runtime_events` action 鏀寔鎸?`audience` 鏌ヨ锛屼絾 worker 鑷姩杞 `_emit_agent_runtime_events_since()` 鍘熷厛鏈紶 audience锛屽彲鑳芥妸 `agent` / `system` 鍐呴儴浜嬩欢涔熸帹鎴愭櫘閫氳亰澶╁绯荤粺娑堟伅
   - 鏂板 `_should_auto_disclose_agent_runtime_event()`锛岃嚜鍔ㄦ姭闇插彧鍏佽 `host`銆乣participants`銆乣all` 涓夌被鐢ㄦ埛鍙 audience锛沗agent` / `system` 浜嬩欢浠嶄繚鐣欏湪 RuntimeState / OperationLog锛屼絾涓嶈嚜鍔ㄥ彂鍒拌亰澶╁
   - 琚烦杩囩殑浜嬩欢浼氬啓鍏?`runtime_system_event_disclosure_skipped` audit锛宲ayload 鍙惡甯﹀畨鍏?runtime metadata 鍜?`reason=audience_not_user_visible`锛屼究浜庡悗缁?replay 瑙ｉ噴鈥滀簨浠跺瓨鍦ㄤ絾鏈嚜鍔ㄦ姭闇测€?
   - 璇ユ楠ょ户缁惤瀹炰俊鎭姭闇茶竟鐣岋細RuntimeEvent 鏄簨瀹炴簮锛孡ANChat 鑷姩娑堟伅鍙槸鐢ㄦ埛鍙鎶曞奖锛屽唴閮?Agent/System 浜嬩欢涓嶅緱榛樿姹℃煋澶氫汉鑱婂ぉ
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 host 浜嬩欢姝ｅ父鍙戦€併€乤gent 浜嬩欢璺宠繃銆乻kip audit 鍙?replay 涓斾笉娉勯湶 provider/prompt/path锛沗verify_ultimate_plan.py` 宸叉妸 disclosure guard 涓?skip audit 绾冲叆闈欐€侀棬绂?

121. Phase 7/LANChat RuntimeEvent 鑷姩鎶湶宸查伩鍏嶅唴閮ㄤ簨浠舵尋鍗犵敤鎴疯繘搴︼細
   - CodeGraph 鏍稿疄 `_emit_agent_runtime_events_since()` 鍘熷厛鍏堣皟鐢?`_format_agent_runtime_event_rows(fresh_events)`锛岃€?formatter 鍙彇鏈€鍚?3 鏉★紱濡傛灉鏈€鍚庡嚑鏉￠兘鏄?`agent` / `system` 鍐呴儴浜嬩欢锛岀湡姝ｇ殑 host/participants 杩涘害浼氬湪杩囨护鍓嶈鎸ゆ帀
   - 鑷姩鎶湶娴佺▼鐜板湪鍏堟妸 `fresh_events` 鍒嗘垚 `disclose_events` 涓?skipped 鍐呴儴浜嬩欢锛屽啀瀵?`disclose_events` 鍋氭渶鍚?3 鏉℃牸寮忓寲鍙戦€?
   - 杩欎繚璇佸唴閮?Agent/System 浜嬩欢涓嶄細姹℃煋鑱婂ぉ瀹わ紝涔熶笉浼氳鐢ㄦ埛鍙杩涘害鍥犱负鍐呴儴浜嬩欢瀵嗛泦鑰岄タ姝伙紱琚烦杩囩殑鍐呴儴浜嬩欢浠嶅啓鍏?`runtime_system_event_disclosure_skipped`
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊鈥? 鏉?host 杩涘害鍚庤窡 4 鏉?agent 鍐呴儴浜嬩欢鈥濈殑鍦烘櫙锛岀‘璁?host 杩涘害浠嶄細鍙戦€佷笖 4 鏉″唴閮ㄤ簨浠跺彧杩涘叆 skip audit
   - `verify_ultimate_plan.py` 宸茶姹?`_emit_agent_runtime_events_since()` 鍏堜骇鐢?`disclose_events` 鍐嶈皟鐢?`_format_agent_runtime_event_rows(disclose_events)`

122. Phase 7/LANChat RuntimeEvent 鑷姩鎶湶鏌ヨ绐楀彛宸叉墿澶э紝閬垮厤鏌ヨ闃舵 starvation锛?
   - CodeGraph 鏍稿疄 `_emit_agent_runtime_events_since()` 鍚?Runtime 鏌ヨ浜嬩欢鏃朵粛纭紪鐮?`limit=8`锛涘鏋?host 杩涘害鍚庤窡 8 鏉′互涓?`agent/system` 鍐呴儴浜嬩欢锛宧ost 浜嬩欢浼氬湪鏌ヨ闃舵琚埅鎺夛紝鍚庣画杩囨护鍐嶆纭篃鏃犳硶鎶湶
   - 鏂板 `MAX_AGENT_RUNTIME_DISCLOSURE_EVENT_LOOKBACK = 32`锛岃嚜鍔ㄦ姭闇叉煡璇娇鐢ㄨ绐楀彛鎷夊彇鏈€杩戜簨浠讹紱瀹為檯鍙戦€佷粛鐢?`_format_agent_runtime_event_rows(disclose_events)` 闄愬埗涓烘渶鍚?3 鏉＄敤鎴峰彲瑙佷簨浠讹紝閬垮厤鍒峰睆
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊鈥? 鏉?host 杩涘害鍚庤窡 12 鏉?agent 鍐呴儴浜嬩欢鈥濈殑鍦烘櫙锛岀‘璁?host 杩涘害浠嶄細鍙戦€侊紝12 鏉″唴閮ㄤ簨浠跺彧杩涘叆 skip audit
   - 杩欎竴姝ョ户缁慨澶嶇敤鎴蜂綋鎰熺殑鈥滃墠闈笉鍔ㄢ€濓細鍐呴儴 Runtime 浜嬩欢瀵嗛泦鏃讹紝涓嶅簲鎸ゆ帀鐪熸搴旇缂撹В绛夊緟鐒﹁檻鐨勭敤鎴峰彲瑙佽繘搴?
   - `verify_ultimate_plan.py` 宸茶姹傝嚜鍔ㄦ姭闇茶矾寰勪娇鐢?`MAX_AGENT_RUNTIME_DISCLOSURE_EVENT_LOOKBACK`锛岄槻姝㈠洖閫€鍒板皬绐楀彛纭紪鐮?

123. Phase 7/RuntimeEvent 璺宠繃鎶湶 audit 宸叉寜 Runtime plan 褰掓。锛?
   - CodeGraph 鏍稿疄 `_record_skipped_agent_runtime_event_disclosure()` 閫氳繃 `runtime_audit_event` 鍐?OperationLog锛屼絾 Runtime audit 鍘熷厛鍙€氳繃 external SeedPlan 瑙ｆ瀽 `entry.plan_id`锛涜烦杩囨姭闇蹭簨浠跺彧鏈?RuntimeEvent 鑷甫鐨?`plan_id`锛屽洜姝ゆ寜 plan 鍋?operation replay 鏃跺彲鑳界湅涓嶅埌鈥滀负浠€涔堟病鏈夋姭闇测€?
   - `_record_runtime_audit_event()` 鐜板湪鍙紶鍏?`runtime_plan_id`锛宍AgentRuntime.handle_message(action=runtime_audit_event)` 浼氬湪褰撳墠 room 鐨?RuntimeState 涓牎楠岃 plan 瀛樺湪鍚庯紝鎶?OperationLog entry 褰掓。鍒扮湡瀹?`plan_id`
   - skipped disclosure audit 鍚屾椂淇濈暀 `batch_id`锛屽洜姝?`operation_replay(room, plan_id, batch_id)` 鑳借В閲婃煇鎵规鍐呴儴浜嬩欢琚烦杩囨姭闇茬殑鍘熷洜
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊甯?Runtime plan 鐨?agent-only RuntimeEvent锛氳嚜鍔ㄦ姭闇蹭笉鍙戦€佹秷鎭紝浣?`operation_replay(plan_id=...)` 鑳界湅鍒?`runtime_system_event_disclosure_skipped`
   - `verify_ultimate_plan.py` 宸茶姹?skip audit 涓?runtime audit recorder 淇濈暀 `runtime_plan_id` / `batch_id` scope锛岀户缁惤瀹?`OperationLog 蹇呴』鍏堜簬鐢ㄦ埛鎶ュ憡`

124. Phase 7/Operation Replay 宸茶仛鍚?RuntimeEvent 璺宠繃鎶湶鎽樿锛?
   - CodeGraph 鏍稿疄 `LANChatAgentWorker._format_agent_runtime_replay_runtime_event_report()` 鍘熷厛鍙牸寮忓寲 emitted / failed / latest锛涘嵆浣?`runtime_system_event_disclosure_skipped` 宸茶繘鍏?OperationLog锛岀敤鎴锋垨 GM 鏌ヨ replay 鏃朵粛闇€瑕佺炕鏄庣粏鎵嶈兘鐭ラ亾鏈夊唴閮ㄤ簨浠惰瀹夊叏璺宠繃
   - `AgentRuntime._runtime_event_replay_summary()` 鐜板湪缁熻 `disclosure_skipped_count`锛屽苟璁板綍 `latest_disclosure_skip` 鐨勫畨鍏?event_type / audience / reason / batch_id
   - Operation Replay 鐨?runtime_events 琛岀幇鍦ㄦ樉绀?`skipped N` 涓庢渶杩?skip 绫诲瀷锛岀户缁笉鏆撮湶 provider銆乸rompt銆乁RL銆乺aw銆佸唴閮ㄨ矾寰勬垨 token
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 plan-scoped skipped audit 鐨?summary 涓?formatter 杈撳嚭锛沗verify_ultimate_plan.py` 宸茶姹?Runtime core summary builder 鍜?worker formatter 鍚屾椂淇濈暀 skipped 鑱氬悎瀛楁

125. Phase 7/Runtime Report 涓庣姸鎬佹煡璇㈠凡娑堣垂 RuntimeEvent 璺宠繃鎶湶鎽樿锛?
   - CodeGraph 鏍稿疄 Runtime Report 鍘熷厛鍙妸 replay summary 鍘嬫垚娉?`entries/events/recent`锛屾櫘閫?Runtime status 鍒欏彧鏄剧ず鏈€杩戠敤鎴峰彲瑙?RuntimeEvent锛涘綋鍐呴儴 `agent/system` 浜嬩欢琚畨鍏ㄨ烦杩囨椂锛岀敤鎴蜂粛闅句互鐭ラ亾鈥滀簨浠跺瓨鍦ㄤ絾琚姭闇茬瓥鐣ヨ繃婊も€?
   - `AgentRuntime.status_summary()` 鐜板湪甯﹀嚭 `runtime_event_replay_summary`锛宍LANChatAgentWorker._agent_runtime_status_reply()` 澶嶇敤瀹夊叏 runtime event replay formatter 鏄剧ず `skipped N`
   - Runtime Report 鐨?`_format_agent_runtime_replay_report()` 鐜板湪鍦?replay 鎽樿閲屾秷璐?`runtime_event_replay_summary`锛屽綋瀛樺湪璺宠繃鎶湶浜嬩欢鏃惰拷鍔?`runtime-events ... skipped N`
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 Runtime Report 涓?batch-scoped status reply 涓や釜鍏ュ彛锛岀‘璁?skipped disclosure 鍙涓斾笉娉勯湶 provider銆乸rompt銆乁RL銆佸唴閮ㄨ矾寰勬垨 raw payload锛沗verify_ultimate_plan.py` 宸插皢 status/report/core 涓夊 token 绾冲叆闂ㄧ

126. Phase 7/GM Runtime 鎽樿宸叉秷璐?RuntimeEvent 璺宠繃鎶湶 digest锛?
   - CodeGraph 鏍稿疄 `_agent_runtime_gm_summary_reply()` 閫氳繃 `AgentRuntime.gm_summary()` 璇诲彇 status_summary 娲剧敓浜嬪疄锛涙鍓?GM summary 宸叉秷璐瑰悓姝ュ拰璧勬簮 digest锛屼絾娌℃湁瑙ｉ噴 RuntimeEvent 鎶湶绛栫暐杩囨护
   - `AgentRuntime.gm_summary()` 鐜板湪浠?`runtime_event_replay_summary` 鐢熸垚 `runtime_event_replay_digest`锛屽彧淇濈暀 emitted / failed / skipped 璁℃暟鍜屾渶杩戣烦杩囨姭闇茬殑瀹夊叏 event_type / audience / reason / batch_id
   - GM 鍥炲鏂板 `RuntimeEvent replay` 琛岋紝澶嶇敤瀹夊叏鏍囩瑁佸壀锛屼笉閫忎紶 provider銆乸rompt銆乁RL銆乺aw銆乼oken銆丄PI key銆佹埅鍥捐矾寰勬垨鍐呴儴璺緞
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 GM 鎬荤粨鍏ュ彛鍙湅鍒?`skipped 1` 涓?`latest-skip agent-internal:agent`锛屼笖 secret provider/prompt 涓嶆硠闇诧紱`verify_ultimate_plan.py` 宸茶姹?core/worker 涓や晶淇濈暀璇?digest 涓?formatter

127. Phase 5/7 Runtime queue health 宸茶繘鍏?LANChat 鐘舵€併€佹姤鍛婁笌 GM 璇讳晶锛?
   - CodeGraph 鏍稿疄 `AgentRuntime.status_summary()` 涓?`generate_report()` 宸茶繑鍥?`tool_queue_health_summary`锛屼絾 LANChat 鐨?Runtime status銆丷untime Report銆丟M summary 杩樻湭缁熶竴娑堣垂璇ユ憳瑕?
   - 鏂板 `_format_agent_runtime_tool_queue_health_report()`锛屽彧杈撳嚭 `queue_count`銆乣active_count`銆乹ueued/running銆乥locked銆乼erminal 涓?`queue_pressure` 鐧惧垎姣旓紝涓嶆毚闇?graph id銆乼ool call id銆乼ool name銆乸rovider銆乸rompt銆乁RL銆佸唴閮ㄨ矾寰勬垨 raw payload
   - Runtime Report 鏂板 `runtime queue` 琛岋紱鐘舵€佹煡璇笌 GM Runtime 鎽樿鏂板 `Runtime queue` 琛岋紱`AgentRuntime.gm_summary()` 浠?status_summary 娲剧敓 `tool_queue_health_digest`
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 report/status/GM 涓変釜鍏ュ彛鍧囪兘鐪嬪埌 queue pressure锛沗verify_ultimate_plan.py` 宸茶姹?core/worker 涓や晶淇濈暀 queue health digest銆乫ormatter 涓庤渚ф秷璐?

128. Phase 5/7 Batch tooling 鎽樿宸茶繘鍏?LANChat 鐘舵€併€佹姤鍛婁笌 GM 璇讳晶锛?
   - CodeGraph 涓庡綋鍓嶄唬鐮佹牳瀹?`AgentRuntime.status_summary()` / `generate_report()` 宸茶繑鍥?`batch_tooling_summary`锛岀敤浜庤瘉鏄庢壒娆″垱寤恒€佺墿浣撲紭鍏堢骇銆佷粙鍏ュ悎骞剁瓑鎵规瑙勫垝浜嬪疄鏉ヨ嚜 RuntimeState锛岃€屼笉鏄棫 workflow 榛戠鏂囨
   - `AgentRuntime.gm_summary()` 鐜板湪浠?`batch_tooling_summary` 娲剧敓 `batch_tooling_digest`锛屼繚鐣?fact銆乧reated-batches銆乸riorities銆乵erged銆乤bsorbed 涓?latest fact type 璁℃暟
   - 鏂板 `_format_agent_runtime_batch_tooling_report()`锛孯untime Report 鏂板 `batch tooling` 琛岋紝鐘舵€佹煡璇笌 GM 鎽樿鏂板 `Batch tooling` 琛岋紱杈撳嚭鍙寘鍚鏁板拰 fact type锛屼笉鏆撮湶 batch fact key銆乼ool payload銆乬raph id銆乸rovider銆乸rompt銆乁RL銆佸唴閮ㄨ矾寰勬垨 raw payload
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 report/status/GM 涓変釜鍏ュ彛鍧囪兘鐪嬪埌 `created-batches`锛沗verify_ultimate_plan.py` 宸茶姹?core/worker 涓や晶淇濈暀 batch tooling digest銆乫ormatter 涓庤渚ф秷璐?

129. Phase 5/7 StatePatch 涓庡け璐ョ瓥鐣ユ憳瑕佸凡杩涘叆 LANChat 鐘舵€併€佹姤鍛婁笌 GM 璇讳晶锛?
   - CodeGraph 涓庡綋鍓嶄唬鐮佹牳瀹?`AgentRuntime.status_summary()` 宸茶繑鍥?`state_patch_summary` 涓?`tool_failure_strategy_summary`锛孫peration Replay 涔熷凡鏈夊畨鍏?formatter锛屼絾鏅€?status / Runtime Report / GM summary 璇讳晶杩樻湭鐩存帴娑堣垂杩欎簺浜嬪疄
   - `AgentRuntime.gm_summary()` 鐜板湪娲剧敓 `state_patch_digest` 涓?`tool_failure_strategy_digest`锛屼繚鐣?versioned/applied/conflict/invalid/reconciled/reconcile-pending銆乺etry/skipped/abandoned/handler-failed/invalid/state-conflict/stopped 绛夎鏁?
   - Runtime Report 鏂板 `state patch` 涓?`failure strategy` 琛岋紱鐘舵€佹煡璇笌 GM Runtime 鎽樿鏂板 `StatePatch` / `Failure strategy` 琛岋紱鏂囨澶嶇敤 Operation Replay 鐨勫畨鍏?formatter锛屼笉鏆撮湶 patch id銆乻ource tool call id銆乼ool payload銆乸rovider銆乸rompt銆乁RL銆佸唴閮ㄨ矾寰勬垨 raw payload
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 report/status/GM 涓変釜鍏ュ彛鍧囪兘鐪嬪埌 StatePatch 涓?Failure strategy锛沗verify_ultimate_plan.py` 宸茶姹?core/worker 涓や晶淇濈暀 digest銆乫ormatter 涓庤渚ф秷璐?

130. Phase 7/GM Runtime 鎽樿宸叉秷璐瑰紩鎿庡啓鍏ヤ笌娑堟伅閫佽揪 digest锛?
   - CodeGraph 鏍稿疄 `AgentRuntime.status_summary()` 宸茶繑鍥?`engine_write_summary` 涓?`message_delivery_summary`锛岀姸鎬佹煡璇㈠拰 Runtime Report 宸茶兘鏄剧ず杩欎簺浜嬪疄锛屼絾 GM summary 杩樼己灏戝搴旀憳瑕?
   - `AgentRuntime.gm_summary()` 鐜板湪娲剧敓 `engine_write_digest` 涓?`message_delivery_digest`锛屼繚鐣?import / transform / env-import / delete 缁撴灉璁℃暟锛屼互鍙?requested / succeeded / failed / message kind / channel / latest stage / progress
   - GM Runtime 鎽樿鏂板 `Engine write` 涓?`Message delivery` 琛岋紝澶嶇敤宸叉湁瀹夊叏 formatter锛屼笉鏆撮湶 actor id銆乵essage id銆乸eer id銆乤sset path銆乸rovider銆乸rompt銆乁RL銆佸唴閮ㄨ矾寰勬垨 raw payload
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 GM 鎽樿鍙 Engine write / Message delivery锛沗verify_ultimate_plan.py` 宸茶姹?core/worker 涓や晶淇濈暀 digest銆乫ormatter 涓庤渚ф秷璐?

131. Phase 5/7 RuntimeGuard 鍐欐潈闄愭憳瑕佸凡杩涘叆 LANChat 鐘舵€併€佹姤鍛婁笌 GM 璇讳晶锛?
   - CodeGraph 鏍稿疄 `runtime_guard_replay_summary` 鍘熸湰鍙湪 Operation Replay 涓ǔ瀹氬瓨鍦紝鏅€?Runtime status銆丷untime Report 涓?GM summary 缂哄皯鍚屼竴浜嬪疄婧愮殑鐩存帴璇讳晶
   - `AgentRuntime.status_summary()` 鐜板湪鍩轰簬鍚屼竴 Runtime scoped OperationLog entries 杩斿洖 `runtime_guard_replay_summary`锛沗generate_report()` 灏?Operation Replay 涓殑 Guard 鎽樿鎻愬崌涓洪《灞傛姤鍛婂瓧娈?
   - `AgentRuntime.gm_summary()` 鐜板湪娲剧敓 `runtime_guard_digest`锛屼繚鐣?blocked銆乭igh-risk-confirm銆亀rite-confirm銆乻ystem-actor銆乿isible-blocked 涓?latest block reason/batch 鐨勫畨鍏ㄦ憳瑕?
   - Runtime Report 鏂板 `guard` 琛岋紝鐘舵€佹煡璇笌 GM Runtime 鎽樿鏂板 `RuntimeGuard` 琛岋紝澶嶇敤 `_format_agent_runtime_replay_guard_report()`锛屼笉鏆撮湶 tool args銆乺aw payload銆乸rovider銆乸rompt銆乁RL銆佸唴閮ㄨ矾寰勬垨鏁忔劅 actor/message 鏍囪瘑
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 report/status/GM 涓変釜鍏ュ彛鍧囪兘鐪嬪埌 Guard 鎽樿锛沗verify_ultimate_plan.py` 宸茶姹?core/worker 涓や晶淇濈暀 Guard digest銆乫ormatter 涓庤渚ф秷璐?

132. Phase 2/7 ScenePlan lifecycle 鎽樿宸茶繘鍏?LANChat 鐘舵€併€佹姤鍛婁笌 GM 璇讳晶锛?
   - CodeGraph 鏍稿疄 `scene_plan_lifecycle_summary` 鍘熸湰鍙湪 Operation Replay 涓ǔ瀹氬瓨鍦紝鏅€?Runtime status銆丷untime Report 涓?GM summary 涓嶈兘鐩存帴璇存槑璁″垝鍒涘缓銆佺‘璁ゃ€佹寔涔呭寲鍜屾彁鍙栫姸鎬?
   - `AgentRuntime.status_summary()` 鐜板湪杩斿洖 `scene_plan_lifecycle_summary`锛涘綋鏌ヨ闄愬畾鍒版煇涓?batch 鏃讹紝鐢熷懡鍛ㄦ湡浠嶆寜 plan 绾у埆鑱氬悎锛岄伩鍏嶆壒娆¤寖鍥撮伄钄借鍒掑垱寤?纭浜嬪疄
   - `AgentRuntime.generate_report()` 灏?Operation Replay 涓殑 `scene_plan_lifecycle_summary` 鎻愬崌涓洪《灞傛姤鍛婂瓧娈碉紝骞跺悓姝ュ姞鍏?`ReportRecordValidator` 鐧藉悕鍗曪紝淇濊瘉缁撴瀯鍖栨姤鍛婂彲鎸佷箙鍖?
   - `AgentRuntime.gm_summary()` 鐜板湪娲剧敓 `scene_plan_lifecycle_digest`锛屼繚鐣?created銆乧onfirmed銆乻tate/status persisted/failed銆乪xtracted 涓?latest plan event 鐨勫畨鍏ㄦ憳瑕?
   - Runtime Report 鏂板 `plan lifecycle` 琛岋紝鐘舵€佹煡璇笌 GM Runtime 鎽樿鏂板 `Plan lifecycle` 琛岋紝澶嶇敤 `_format_agent_runtime_replay_plan_lifecycle_report()`锛屼笉鏆撮湶 raw payload銆乸rompt銆乸rovider銆乁RL銆佸唴閮ㄨ矾寰勬垨 tool args
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 report/status/GM 涓変釜鍏ュ彛鍧囪兘鐪嬪埌 Plan lifecycle 鎽樿锛沗verify_ultimate_plan.py` 宸茶姹?core/worker 涓や晶淇濈暀 lifecycle digest銆乫ormatter 涓庤渚ф秷璐?

133. Phase 6/7 VLM checkpoint 涓?review advisory replay 鎽樿宸茶繘鍏?LANChat 鐘舵€併€佹姤鍛婁笌 GM 璇讳晶锛?
   - CodeGraph 鏍稿疄 `vlm_checkpoint_summary` 涓?`review_advisory_summary` 鍘熸湰涓昏瀛樺湪浜?Operation Replay锛屾櫘閫?Runtime status銆丷untime Report 涓?GM summary 缂哄皯鍚屼竴浜嬪疄婧愮殑鐩存帴鎽樿
   - `AgentRuntime.status_summary()` 鐜板湪杩斿洖 `vlm_checkpoint_summary` 涓?`review_advisory_replay_summary`锛沗generate_report()` 灏?Operation Replay 涓殑 VLM checkpoint / review advisory 鎽樿鎻愬崌涓洪《灞傛姤鍛婂瓧娈碉紝骞跺悓姝ュ姞鍏?`ReportRecordValidator` 鐧藉悕鍗?
   - `AgentRuntime.gm_summary()` 鐜板湪娲剧敓 `vlm_checkpoint_digest` 涓?`review_advisory_replay_digest`锛屼繚鐣?checkpoint/proposal/confirmation/advisory item 璁℃暟銆佺姸鎬佸垎甯冧笌 latest decision 鐨勫畨鍏ㄦ憳瑕?
   - Runtime Report 鏂板 `vlm replay` 涓?`review advisory replay` 琛岋紝鐘舵€佹煡璇笌 GM Runtime 鎽樿鏂板 `VLM replay` 涓?`Review advisory replay` 琛岋紝澶嶇敤瀹夊叏 formatter锛屽彧杈撳嚭璁℃暟銆乧heckpoint 绫诲瀷銆佺姸鎬佸拰 proposal 鐘舵€?
   - 璇ュ垏鐗囧彧鎶?VLM / review 浜嬪疄鎺ュ叆璇讳晶涓庢姤鍛婇潰锛屼笉璁?VLM 鑷姩淇敼鍦烘櫙锛涗笉鏆撮湶鎴浘璺緞銆乸rompt銆乸rovider銆乁RL銆乺aw payload銆乼ool args銆乤ctor/message 鍐呴儴鏍囪瘑
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 report/status/GM 涓変釜鍏ュ彛鍧囪兘鐪嬪埌 VLM checkpoint 涓?review advisory replay锛沗verify_ultimate_plan.py` 宸茶姹?core/worker 涓や晶淇濈暀 digest銆乫ormatter 涓庤渚ф秷璐?

134. Phase 2/6/7 SceneDesignContract 闀垮懆鏈熷満鏅绾﹀凡杩涘叆 RuntimeState銆佹姤鍛婁笌 GM 璇讳晶锛?
   - CodeGraph 鏍稿疄鏃?`SceneDesignContract` 涓昏鐢?`InteractionCoordinator` 缁存姢锛孉gentRuntime 鐨?`ScenePlan` 鎸佷箙鍖栭摼璺鍓嶇己灏戝悓绛夌殑闀挎湡椋庢牸銆佸湴褰€佽竟鐣屻€侀伩闆疯瘝绾︽潫浜嬪疄
   - `AgentRuntime._persist_new_scene_plan()` 涓?ScenePlan 鐘舵€佹寔涔呭寲璺緞鐜板湪浼氫粠 `ScenePlan` 娲剧敓瀹夊叏鐨?`custom_scene_design_contract_facts`锛岃褰?scene_type銆乪nvironment_type銆乵ood銆乻tyle_keywords銆乤void_keywords銆乼errain銆乥oundary銆乻cale_rules 涓?placement_rules
   - `AgentRuntime.status_summary()` 涓?`generate_report()` 鐜板湪杩斿洖 `scene_design_contract_summary`锛沗ReportRecordValidator` 鐧藉悕鍗曞悓姝ュ厑璁歌瀛楁锛屼繚璇佺姸鎬佹煡璇㈠拰鏈€缁堟姤鍛婇兘鑳借鍙栧悓涓€涓?RuntimeState 浜嬪疄婧?
   - `AgentRuntime.gm_summary()` 鐜板湪娲剧敓 `scene_design_contract_digest`锛屼緵 GM 鎬荤粨闀挎湡鍦烘櫙绾︽潫銆佸湴褰?杈圭晫绫诲瀷鍜岃礋鍚戠害鏉燂紝涓嶅洖閫€鏃?Coordinator memory
   - Runtime Report 鏂板 `scene contract` 琛岋紝鐘舵€佹煡璇㈡柊澧?`鍦烘櫙濂戠害` 琛岋紝GM Runtime 鎽樿鏂板 `Scene contract` 琛岋紱formatter 鍙緭鍑哄畨鍏ㄦ憳瑕侊紝涓嶆毚闇?prompt銆乸rovider銆乁RL銆乺aw payload銆佸唴閮ㄨ矾寰勬垨 tool args
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 report/status/GM 涓変釜鍏ュ彛鍧囪兘鐪嬪埌鍦烘櫙濂戠害鎽樿锛沗verify_ultimate_plan.py` 宸茶姹?core/worker 涓や晶淇濈暀 summary銆乨igest銆乫ormatter 涓庤渚ф秷璐?

135. Phase 6/Planner + GM 璇箟浠茶鎽樿宸茶繘鍏?RuntimeState 璇讳晶锛?
   - CodeGraph 鏍稿疄 `gm_summary()` 褰撳墠鍏堥€氳繃 `status_summary()` 璇诲彇 RuntimeState 涓殑 planning context銆丼cenePlan銆乮ntervention銆丼ceneDesignContract锛屽啀缁?`runtime.gm_summary.snapshot` 鎸佷箙鍖?GM-facing 鎽樿
   - 鏂板 `semantic_arbitration_summary`锛屼粠 RuntimeState 宸叉湁浜嬪疄娲剧敓 arbitration_state銆乪xecution_readiness銆乺equires_host_confirmation銆乶eeds_clarification銆乷wner_agent銆乧ontributing_agents銆乵ulti_agent_discussion 涓?risk_flags
   - Runtime Report 鏂板 `semantic arbitration` 琛岋紝鐘舵€佹煡璇㈡柊澧?`璇箟浠茶` 琛岋紝GM Runtime 鎽樿鏂板 `Semantic arbitration` 琛岋紝甯姪 GM / Planner 鍖哄垎鈥滃彧鏈夎璁轰笂涓嬫枃鈥濃€滄柟妗堝緟鎴夸富纭鈥濃€滃凡纭鎴栨墽琛屼腑鈥濃€滃畬鎴愬悗鍙皟鏁粹€濈瓑鐘舵€?
   - 璇ュ垏鐗囦笉璋冪敤 LLM銆佷笉鏀瑰彉 IntentRouter銆佷笉鎵ц宸ュ叿銆佷笉鍐欏紩鎿庯紝鍙妸璇箟浠茶鎵€闇€鐨勭粨鏋勫寲璇讳晶浜嬪疄浠庢棫鑱婂ぉ/Coordinator 闅愭€х姸鎬佽縼绉诲埌 RuntimeState / OperationLog 鍙鐩樿鍥?
   - LANChat Runtime guard 娴嬭瘯瑕嗙洊 report/status/GM 涓変釜鍏ュ彛鍧囪兘鐪嬪埌璇箟浠茶鎽樿锛沗verify_ultimate_plan.py` 宸茶姹?core/worker 涓や晶淇濈暀 summary銆乨igest銆乫ormatter 涓庤渚ф秷璐?
```

楠岃瘉鐘舵€侊細

```text
python editor/plugins/AITool/services/test_agent_runtime_phase1.py
python editor/plugins/AITool/services/test_lanchat_runtime_guard.py
python editor/plugins/AITool/services/verify_ultimate_plan.py
git diff --check
```

2026-07-04 鏈疆鎺ㄨ繘璁板綍锛?

```text
宸蹭慨澶?AgentRuntime Phase1 涓殑鐪熷疄璇箟鏂偣锛?
- legacy model provider 鍏ㄥけ璐ユ椂锛孴oolCallGraph 浼氬け璐ワ紝Batch/Plan 涓嶅啀浼鎴愬姛銆?
- 澶辫触 ToolResult 鐨?state_patch 鍦?ToolCallGraphExecutor 鍐呴儴鍙楁帶鍚堝苟锛屼粛婊¤冻 RuntimeState.apply_patch 杈圭晫銆?
- 妫灄钀ュ湴绛夊満鏅?profile 浼樺厛浜庢柊澧炵墿浣?alias锛岄伩鍏嶁€滃笎绡封€濈瓑瀵硅薄璇嶆彁鍓嶆埅鏂?substrate/object 鍒嗙被銆?

宸叉竻鐞?Phase1 娴嬭瘯涓殑澶氬 mojibake fixture 涓庤剢寮变腑鏂囨爣棰樻柇瑷€锛屾敼涓虹ǔ瀹氳涔?缁撴瀯鏂█銆?

鏈疆楠岃瘉锛?
- python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
  Ran 563 tests OK
- python editor/plugins/AITool/services/verify_ultimate_plan.py
  All current Agent-native non-native checks passed

浠嶆湭楠岃瘉锛?
- native / C++ / CEF / F5 瀹炴満閾捐矾
- 鐪熷疄 provider 涓嬬殑澶у垎鎵?image/model/import/review 鎵ц闂幆
- 鐪熷疄澶氫汉 LAN 鍚屾銆佹ā鍨嬪悓浼犱笌瀹炴満鍦烘櫙鍐欏叆鏁堟灉
```

褰撳墠杩欎簺妫€鏌ュ凡閫氳繃锛沗git diff --check` 鍙湁 CRLF warning锛屾棤 whitespace error銆?

2026-07-04 琛ュ厖鎺ㄨ繘璁板綍锛?

```text
宸茶ˉ榻?Runtime 鎶ュ憡/鐘舵€佸眰鐨勮涔夌姸鎬佽〃杈撅細
- ToolCallGraph 鐨勫師濮嬫墽琛岀姸鎬佺户缁〃绀哄伐鍏烽摼鏄惁鎸夊崗璁窇瀹岋紝渚嬪鎴愬姛璁板綍澶辫触瀵煎叆浜嬪疄鏃朵粛鍙负 completed銆?
- batch_summary / tool_graph_summary 鏂板 semantic_status 涓?semantic_status_source銆?
- semantic_status 鏉ヨ嚜 batch_resource_flow_summary锛岃兘鎶?actor import 澶辫触銆侀儴鍒嗗鍏ャ€佺瓑寰呰祫婧愮瓑鐪熷疄涓氬姟鐘舵€佷紶閫掔粰鎶ュ憡銆佺姸鎬佹煡璇㈠拰鍚庣画 Disclosure/GM 灞傘€?
- batch_resource_flow_summary 鏂板 status_by_batch_id锛屼綔涓?RuntimeState fact-source 鐨勬壒娆¤涔夌储寮曘€?

杩欐牱閬垮厤浜嗏€済raph completed 浣嗕笟鍔″鍏ュけ璐モ€濆湪鐢ㄦ埛鎶ュ憡涓璇涓哄満鏅垚鍔燂紝鍚屾椂涓嶇牬鍧?ToolCallGraph Executor 鐨勫簳灞傛墽琛岃涔夈€?

鏈疆楠岃瘉锛?
- python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
  Ran 563 tests OK
- python editor/plugins/AITool/services/verify_ultimate_plan.py
  All current Agent-native non-native checks passed
- git diff --check
  only CRLF warnings, no whitespace error
```

2026-07-05 Operation Replay 琛ュ厖鎺ㄨ繘璁板綍锛?

```text
宸叉妸 RuntimeState 鐨勬壒娆¤祫婧愯涔夌姸鎬佹帴鍏?Operation Replay锛?
- AgentRuntime.operation_replay() / _compose_operation_replay() 鐜板湪棰濆杈撳嚭 batch_resource_flow_summary銆?
- 璇ユ憳瑕佹潵鑷?RuntimeState 涓殑 image/model/import/review facts锛岃€屼笉鏄彧鐪?OperationLog 浜嬩欢娴併€?
- LANChatAgentWorker._handle_agent_runtime_operation_replay_query() 鏂板 resource_flow 琛岋紝澶嶇敤瀹夊叏 formatter锛岃兘鏄剧ず latest i/n:status img/model/import x/y/z of requested銆?
- 褰?RuntimeState 鏄剧ず鎵规 failed/partial/waiting 鏃讹紝Operation Replay 涔熻兘鏄剧ず semantic failed/partial/waiting锛岄伩鍏嶆帓闅滄椂鍙湅鍒?queue/tool completed銆?
- 鏂囨涓嶆毚闇?batch_id銆乼ool_name銆乸rovider銆乸rompt銆乁RL銆佹ā鍨嬭矾寰勬垨鍐呴儴寮傚父銆?

鏈疆楠岃瘉锛?
- python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
  Ran 180 tests OK
- python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
  Ran 563 tests OK
- python editor/plugins/AITool/services/verify_ultimate_plan.py
  All current Agent-native non-native checks passed
- git diff --check
  only CRLF warnings, no whitespace error
```

2026-07-05 LAN 鍚屼紶鐘舵€佽ˉ鍏呮帹杩涜褰曪細

```text
宸插寮?RuntimeState 涓?asset/model transfer 鐨勬湭瀹屾垚鐘舵€佽〃杈撅細
- AgentRuntime._asset_transfer_summary_for_plan() 鏂板 incomplete_count锛岃〃绀?asset_count - ready_count - failed_count銆?
- AgentRuntime._sync_health_digest_for_report() 鏂板 asset_incomplete_count锛屽苟缁х画鍦ㄦ湭 ready/failed 涓旀湭 transferring 鏃舵爣璁?asset_transfer_incomplete銆?
- LANChatAgentWorker._format_agent_runtime_asset_transfer_report() 鐜板湪鏄剧ず incomplete N锛岀敤鎴烽棶鐘舵€佹垨 GM 鎬荤粨鏃惰兘鐩存帴鐪嬪埌妯″瀷鍚屼紶杩樻湁澶氬皯璧勬簮鏈畬鎴愩€?
- 杩欎竴姝ュ彧琛?RuntimeState 娲剧敓浜嬪疄鍜岀敤鎴峰彲瑙佸畨鍏ㄦ憳瑕侊紝涓嶄慨鏀瑰簳灞?LAN 鍚屾鍗忚銆佷笉鏀瑰彉 actor/model 浼犺緭琛屼负銆?

鏈疆楠岃瘉锛?
- python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
  Ran 180 tests OK
- python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
  Ran 563 tests OK
- python editor/plugins/AITool/services/verify_ultimate_plan.py
  All current Agent-native non-native checks passed
- git diff --check
  only CRLF warnings, no whitespace error
```

2026-07-05 琛ュ厖鎺ㄨ繘璁板綍锛?

```text
宸叉妸 Runtime 璧勬簮鎵规璇箟鐘舵€佺户缁帴鍒?LANChat 鐢ㄦ埛鍙鍥炲闈細
- 淇 LANChatAgentWorker._format_agent_runtime_resource_flow_report() 鍙鍙?latest_batch 鍗曟暟鐨勯棶棰橈紱Runtime 褰撳墠杈撳嚭鐨勬槸 latest_batches 鍒楄〃锛屾棫閫昏緫浼氭紡鎺夋渶杩戞壒娆?image/model/import 缁嗚妭銆?
- formatter 鐜板湪浼氫粠 latest_batches 鍙栨渶杩戞壒娆★紝鏄剧ず latest i/n:status img/model/import x/y/z of requested銆?
- formatter 鐜板湪浼氳鍙?status_by_batch_id锛涘綋鎵规璇箟鐘舵€佸寘鍚?failed/partial/waiting 绛夐潪瀹屾垚鐘舵€佹椂锛岃緭鍑?semantic failed/partial/waiting锛岄伩鍏嶇敤鎴峰彧鐪嬪埌 ToolCallGraph completed 鑰岃鍒や笟鍔℃垚鍔熴€?
- 鏂囨浠嶅彧鏆撮湶瀹夊叏璁℃暟鍜岀姸鎬侊紝涓嶆毚闇?batch_id銆乼ool_name銆乸rovider銆乸rompt銆乁RL銆佹ā鍨嬭矾寰勬垨鍐呴儴寮傚父銆?

鏈疆楠岃瘉锛?
- python -B editor/plugins/AITool/services/test_lanchat_runtime_guard.py -f
  Ran 180 tests OK
- python -B editor/plugins/AITool/services/test_agent_runtime_phase1.py -f
  Ran 563 tests OK
- python editor/plugins/AITool/services/verify_ultimate_plan.py
  All current Agent-native non-native checks passed
- git diff --check
  only CRLF warnings, no whitespace error
```

浠嶆湭瀹屾垚锛?

```text
鐪熷疄 C++ remove_actor / import_environment_component / import_model / set_actor_transform F5 鏁堟灉
鐪熷疄澶氫汉 actor create / transform / delete 骞挎挱
鐪熷疄 asset/model transfer 鎺ョ涓庨檺娴?
鏃?ProgressiveWorkflow / SceneComposer 涓绘帶瀹屽叏宸ュ叿鍖栦粛鍦ㄦ帹杩?
鐪熷疄 provider 涓嬬殑澶у垎鎵?image/model/import/review 鎵ц闂幆浠嶅緟 F5 楠岃瘉
GM / Planner 鐨勫畬鏁磋涔変徊瑁佷笌闀挎湡璁板繂 Runtime 鍖?
```

## 14. Feature Flag 涓庤竟鐣?

鏈閲嶆瀯鎺ュ彈杈冨ぇ鏋舵瀯鍙樺姩锛屼絾浠嶉渶瑕佸伐绋嬪紑鍏抽槻姝㈠疄鏈哄畬鍏ㄤ笉鍙敤锛?

```text
AGENT_RUNTIME_ENABLED=1
OLD_WORKFLOW_DIRECT_ENTRY_DISABLED=1
ALLOW_LEGACY_FUNCTION_ADAPTER=1
ALLOW_LEGACY_MAIN_WORKFLOW=0
```

鐪熷疄 provider / engine-write 閫氶亾蹇呴』鍗曠嫭鏄惧紡寮€鍚紝榛樿淇濇寔 mock / RuntimeState-only锛?

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

鍚箟锛?

```text
鍏佽澶嶇敤鏃т唬鐮侀噷鐨勫簳灞傚嚱鏁?
涓嶅厑璁稿鐢ㄦ棫 workflow 涓绘帶
涓嶅厑璁哥敤鎴峰叆鍙ｅ洖鏃ч摼璺?
涓嶅厑璁?legacy compose whole scene
```

鏈鍒掍笉鍖呭惈锛?

```text
C++ / CMake / Ninja / CEF 搴曞眰鏋勫缓鏀归€?
寮曞叆澶栭儴 Agent 妗嗘灦
閲嶅仛鍏ㄩ儴鍓嶇 UI
VLM 鑷姩寮烘墽琛屼慨鏀?
浜у搧绾ф潈闄愮郴缁?
```

## 15. 鏈€缁堝缓璁?

鏈澶ф敼搴斿畾鍚嶄负锛?

```text
Agent-native Runtime 涓绘帶閲嶆瀯
```

鑰屼笉鏄細

```text
绾?Agent 鑷敱鎵ц
鏃?workflow 鍖呰鍗囩骇
```

鏈€缁堢洰鏍囨槸锛?

```text
Agent 璐熻矗瑙勫垝涓庡喅绛?
ToolCallGraph 璐熻矗缂栨帓
RuntimeGuard 璐熻矗鏉冮檺鍜岄闄?
ToolRegistry 璐熻矗鑳藉姏鎵ц
RuntimeState 璐熻矗浜嬪疄鐘舵€?
OperationLog 璐熻矗鍙洖鏀?
鏃?workflow 涓绘帶閫€鍦猴紝搴曞眰鑳藉姏宸ュ叿鍖?
```

鍙湁瀹屾垚杩欐涓绘帶鏉冭縼绉伙紝鍚庣画鈥滃疄鏃朵粙鍏モ€濇墠涓嶆槸鑱婂ぉ灞傜殑寤惰繜鍚告敹锛岃€屾槸鍙互鍦?Runtime 涓湡姝ｅ彇娑堛€佹彃闃熴€佹浛鎹€佹殏鍋溿€佺户缁€佺‘璁ゅ拰鍥炴斁鐨勪氦浜掕兘鍔涖€?




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

- Runtime status replies: "鎶ュ憡鍋ュ悍锛?.."
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

For multiplayer楠屾敹 this is a real visibility gap: when users ask GM to summarize
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

- 妯″瀷鍚屼紶锛歛ssets N, ready X, completed Y, transferring Z, failed K, progress P%

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
  "鐢熸垚鎶ュ憡宸插畬鎴愶紙瀛樺湪澶辫触椤癸級"
- partial batch or incomplete asset transfer facts produce warning level and
  "鐢熸垚鎶ュ憡宸插畬鎴愶紙浠嶆湁鏈畬鎴愰」锛?
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
LANChat status replies expose it as "鎶ュ憡鍋ュ悍"; LANChat GM summaries expose it as
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
UTF-8 Chinese terms such as 妫灄 / 澶╃┖ / 鑽夊湴 / 灏忔湪妗?/ 甯愮.

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

The Runtime status reply path also verifies the 鍐欏叆杈圭晫 line is present.
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
This is a涓绘帶閫€鍦?boundary slice. It does not delete SceneComposer, change
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
"宸茶繘鍏?Runtime 鎵ц闃熷垪".  This made a completed Runtime execution slice look
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

The wording uses "宸叉墽琛?Runtime 鎵规..." instead of "宸茶繘鍏?Runtime 鎵ц闃熷垪".
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
text "AgentRuntime 鎵ц缁撴灉銆?.  That made user/GM-visible杩藉姞鐢熸垚纭鏃犳硶鐪嬪嚭
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

The generic "AgentRuntime 鎵ц缁撴灉銆? reply is no longer used for this path.
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
"AgentRuntime 鎵ц缁撴灉锛氬凡搴旂敤 N 椤逛綆椋庨櫓甯冨眬璋冩暣銆?.  That made the user-facing
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
"纭甯冨眬璋冩暣", so OperationLog remains readable.

verify_ultimate_plan.py now statically requires the layout confirmation
formatter to reference ToolCallGraph / graph / applied_deltas / skipped_deltas /
engine_transform_results / ground_snapped / overlap_resolved, and rejects the
old collapsed "AgentRuntime 鎵ц缁撴灉锛氬凡搴旂敤" response.
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
quality.  Those remain [寰?F5/瀹炴満楠岃瘉] after real provider rollout.
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
[寰?F5/瀹炴満楠岃瘉] after real provider rollout.
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
creation or multiplayer sync convergence.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
quality.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
or F5 multiplayer scene convergence.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
multiplayer convergence.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
rendering.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
Those remain [寰?F5/瀹炴満楠岃瘉].
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
availability, or F5 user-facing pacing quality.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
stability.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
remain [寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
remain [寰?F5/瀹炴満楠岃瘉].
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
multiplayer convergence.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
```

## Progress Update 257 - status and GM audit logs preserve layout adjustment outcomes

Problem:

```text
瀹屾垚鎬佸竷灞€璋冩暣宸茬粡鑳借繘鍏?RuntimeState / report / operation replay锛?

- layout_adjustment_summary
- final_adjustment_confirmation_summary
- layout_adjustment_replay_summary
- report_ready layout counts

浣?status query 鍜?GM summary 鐨?OperationLog payload 浠嶅亸寮憋細

- runtime_status_queried 娌℃湁鎸佷箙璁板綍 layout applied / skipped / transform / ground snap / overlap counts
- runtime_gm_summary_exported 娌℃湁鎸佷箙璁板綍鍚屼竴缁勫竷灞€璋冩暣缁撴灉璁℃暟

杩欎細瀵艰嚧鐢ㄦ埛闂€滃垰鎵嶈皟鏁村埌搴曟墽琛屼簡浠€涔堚€濇椂锛孯untimeState 鍙互鏌ュ埌锛?
浣?status / GM 瀹¤浜嬩欢鏈韩涓嶈兘鐙珛璇佹槑浣庨闄╁竷灞€璋冩暣鐨勭粨鏋溿€?
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
convergence.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
multiplayer convergence.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
multiplayer convergence remain [寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
convergence.  Those remain [寰?F5/瀹炴満楠岃瘉].
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
git diff --check -- editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py docs/Agent-native涓€姝ュ埌浣嶉噸鏋勮鍒?md
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
AABB quality, and multiplayer visual convergence remain [寰?F5/瀹炴満楠岃瘉].
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
git diff --check -- editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py docs/Agent-native涓€姝ュ埌浣嶉噸鏋勮鍒?md
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
native AABB accuracy, and multiplayer scene convergence remain [寰?F5/瀹炴満楠岃瘉].
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
git diff --check -- editor/plugins/AITool/services/agent_runtime/core.py editor/plugins/AITool/services/agent_runtime/tools.py editor/plugins/AITool/services/test_agent_runtime_phase1.py editor/plugins/AITool/services/verify_ultimate_plan.py docs/Agent-native涓€姝ュ埌浣嶉噸鏋勮鍒?md
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
multiplayer sync convergence; those remain [寰?F5/瀹炴満楠岃瘉].
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
or multiplayer actor convergence; those remain [寰?F5/瀹炴満楠岃瘉].
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
[寰?F5/瀹炴満楠岃瘉].
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
workflow/helper code yet; remaining鏃т唬鐮佷粛闇€鎸変富鎺х被绂佺敤銆佸彲澶嶇敤鍑芥暟宸ュ叿鍖栥€?
鐘舵€佽縼绉诲埌 RuntimeState銆佹祴璇?鏂囨。淇濈暀涓?baseline 鐨勫垎绫荤户缁鐞嗐€?
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
not complete old workflow dismantling: remaining鏃т富鎺?鍙鐢ㄥ嚱鏁?鐘舵€?娴嬭瘯鏂囨。
鍒嗙被浠嶈缁х画鎸?AgentRuntime ToolCallGraph + RuntimeGuard + RuntimeState 鐨?
鐩爣鏋舵瀯鎺ㄨ繘銆?
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
A/B/C/D classification and replacement of old workflow涓绘帶鑳藉姏 with Runtime
ToolCallGraph tools.
```

## Progress Update 277 - Planning context handoff ToolCallGraph path is locked by tests and static gate

Task anchor:

```text
Multi-user / multi-Agent discussion context must survive across plan drafting,
Agent replies, host confirmation, and generation.  This path is not a scene
write, but it is the control-plane memory that prevents "鏂规璺戝亸" and must not
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

This is intentionally a闃插洖閫€鍒囧彛: the current path was already mostly correct,
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
finish the larger old workflow鎷嗚В; next work should continue classifying old
涓绘帶鑳藉姏 and replacing execution/state ownership with Runtime tools where the
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
finish full old workflow鎷嗚В; remaining work is still to continue A/B/C/D
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
This is a闃插洖閫€闂ㄧ, not a new Runtime command implementation.  The next
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
ProgressiveWorkflow and SceneSession閫€鍦?into ToolCall-sized capabilities.
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
still a legacy workflow涓绘帶 area and must continue to be decomposed into
BatchPlan / import / review / adjustment Runtime tools in later slices.
```

## Progress Update 282 - Runtime ToolCallGraph queue executor invariants are now statically guarded

Task anchor:

```text
Phase 5 requires the old scheduler / queue behavior to閫€鍦?into ToolCallGraph
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
executor slice into a闃插洖閫€闂ㄧ.
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
- Scope: no native build; no Quasar changes; real C++ actor import/transform/delete, terrain write, sync transfer, VLM screenshot, and visual grounding remain `[寰?F5/瀹炴満楠岃瘉]`.

### Progress Update 341 - Entity Registry Asset Transfer Status Link

- Change: actor sync events can now bind a safe `model_asset_id` / `actor_asset_id` to the actor fact without counting that actor event as an asset-transfer event. `scene_entity_registry` actor entries now include a safe `asset_transfer_status` summary from RuntimeState `assets`.
- Why: multiplayer F5 needs a single game-facing entity record to show both actor presence and model transfer state. The entity registry now exposes whether the actor's asset is `transferring`, `completed`, or `failed`, plus progress/chunk/byte counters, without leaking private paths or internal message ids.
- Sync closure: the existing `runtime.sync_event.record` ToolCallGraph remains the only writer. The registry only consumes persisted RuntimeState facts (`actors`, `assets`, `sync_state`) and the final report consumes that same registry.
- Tests: strengthened `test_asset_transfer_progress_sync_event_updates_runtime_asset_summary` so an actor linked to `asset-progress` shows `asset_transfer_status.transfer_status == transferring`, progress `50`, chunk counters, byte counters, and matching status/report registry evidence. Forest-camp substrate/actor registry regression still passes.
- Verification: targeted sync asset-transfer registry regression passed; targeted forest-camp registry regression passed; syntax compile passed for touched Runtime/test files; `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; real LAN file transfer and peer-side asset availability remain `[寰?F5/瀹炴満楠岃瘉]`.

### Progress Update 342 - Engine Write Adapter Summary Evidence

- Change: added `engine_write_adapter_summary` to AgentRuntime status and final reports. The summary combines existing `engine_write_readiness_summary`, `engine_write_boundary_summary`, and OperationLog `engine_write_summary` into a compact read-only view for `environment_import`, `actor_import`, `actor_delete`, and `layout_transform`.
- Why: F5 pre-sprint needs operator-visible proof that engine writes are adapter-gated instead of hidden behind direct calls. The new summary shows each write channel's readiness mode, whether a write was attempted, boundary/result counts, bridge success/failure counts, and readiness mismatch count without exposing provider names, prompts, raw paths, tool ids, or internal bridge payloads.
- Runtime closure: no write path changed. Real engine mutations still have to go through `ToolCall -> RuntimeGuard -> EngineWriteGate/runtime_cpp_bridge -> ToolResult -> StatePatch -> RuntimeState -> OperationLog`; the new field only reads existing RuntimeState and OperationLog evidence.
- Tests: strengthened `test_provider_status_publishes_safe_readiness_without_creating_plan` so both `status_summary()` and `generate_report()` expose safe adapter evidence and do not leak provider details. The static Runtime report fact-source gate now requires `engine_write_adapter_summary` alongside `engine_write_readiness_summary`.
- Verification: targeted provider/status regression passed; syntax compile passed for touched Runtime/verifier files; `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; real C++ actor import/transform/delete, terrain write, bridge success, sync transfer, VLM screenshot, and visual grounding remain `[锟斤拷 F5/实锟斤拷锟斤拷证]`.

### Progress Update 343 - Layout Reflow Grounding Fact Closure

- Change: layout reflow now writes `support_type` and `grounding_status` back into RuntimeState actor facts after selective AABB bottom snap. Floor-supported actors become `grounded` after snap or when already grounded; wall-mounted / ceiling-hung / system actors are marked `not_applicable`; unknown actors remain `unknown`.
- Why: F5 pre-sprint needs `scene_entity_registry` to be directly consumable by later gameplay systems. Before this update, layout reflow corrected actor position/AABB but grounding was mostly inferred at registry time; now the actor fact itself carries explicit grounding evidence.
- Report closure: no-provider layout adjustments now count `ground_snapped_count` from applied deltas when no native transform result exists, so status/final report summaries match the RuntimeState actor updates instead of hiding successful Runtime-only snap repairs.
- Tests: strengthened `test_confirm_layout_adjustment_snaps_floor_supported_aabb_without_provider` to assert RuntimeState actor facts, status `scene_entity_registry`, final report `scene_entity_registry`, and layout summary all expose the grounded result while wall-mounted actors are not snapped to the floor.
- Verification: targeted layout grounding regression passed; syntax compile passed for touched Runtime file; `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; real imported model pivots/AABB quality, C++ transform application, visual grounding, sync transfer, and VLM screenshot remain `[锟斤拷 F5/实锟斤拷锟斤拷证]`.

### Progress Update 344 - Generic Outdoor Nature Terrain Profile

- Change: added a generic `outdoor_nature` terrain/boundary profile to `TerrainComponentResolver` for outdoor nature/camp substrate prompts such as forest, woods, camp, grass, sky, ground, terrain, hill, river, lake, and their Chinese equivalents. This avoids falling back to `neutral_ground` / `contextual_boundary` for the F5 forest-camp acceptance prompt.
- Guardrail: kept existing specific profiles ahead of the generic fallback. Fantasy night market still resolves to `fantasy_night_market`, grassland/yurt prompts still resolve to `grassland_yurt`, and indoor room prompts still resolve to `indoor_room` even when the text mentions floor/ground.
- Why: F5 pre-sprint minimum acceptance requires grass/sky/ground/terrain/forest to stay in environment/terrain/substrate while tent and wooden table remain asset/model/actor entities. The existing classifier guardrail already protected the model list; this update closes the terrain resolver side so the environment profile is also meaningful.
- Tests: added `test_terrain_component_resolver.py` covering outdoor nature/camp substrate, profile-priority regressions, and indoor priority. Existing AgentRuntime substrate regression still proves environment terms do not enter normal actor/model generation.
- Verification: direct terrain resolver tests passed; targeted AgentRuntime substrate regression passed; syntax compile passed for touched resolver/test files; `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; real terrain actor creation, visual terrain material, C++ environment import, sync transfer, and F5 forest-camp visual result remain `[Pending F5/native verification]`.
### Progress Update 345 - Forest Camp OperationLog Replay Closure

- Change: strengthened the existing forest-camp AgentRuntime regression to prove the F5 minimum scene can be replayed from OperationLog/report evidence across plan, environment, image/model resource, actor import, geometry/review, and final report stages.
- Why: the RuntimeState and scene_entity_registry already showed forest/sky/grass as substrate/environment entities and wooden table/tent as actor entities. This update ties the same minimum acceptance path to OperationLog-derived summaries and user-visible runtime event ordering.
- Evidence: the regression now asserts scene plan lifecycle counts, environment readiness replay, image/model resource replay, actor import replay, geometry fact replay, VLM checkpoint replay, batch completion, report generation, and ordered user-facing runtime events from environment ready to report ready.
- Tests: targeted `test_substrate_terms_are_classified_but_not_imported_as_actors` passed.
- Scope: no production Runtime code change; no native build; no Quasar changes; real engine terrain import, actor import, visual grounding, LAN sync, and VLM screenshot remain `[Pending F5/native verification]`.

### Progress Update 346 - Transform/Delete Adapter Summary Closure

- Change: `engine_write_adapter_summary` now merges layout adjustment transform results into the `layout_transform` channel, so status and final reports show transform result counts/statuses even when those results are produced by the layout adjustment Runtime tool rather than the generic engine-write replay bucket.
- Why: F5 operator-facing reports must prove actor import/transform/delete writes are adapter-gated. Delete results were already visible through engine-write replay; layout transform results were visible in `layout_adjustment_summary` but not in the adapter channel summary.
- Tests: strengthened the confirmed delete advisory provider regression so final reports expose actor delete result counts/statuses in `engine_write_adapter_summary`. Strengthened the layout adjustment confirmation regression so both status and final report expose layout transform result counts/statuses in `engine_write_adapter_summary`.
- Verification: targeted delete-advisory and layout-transform regressions passed; syntax compile passed for touched Runtime/test files; `python -B editor/plugins/AITool/services/verify_ultimate_plan.py` passed: AgentRuntime 569 tests OK, LANChat guard 187 tests OK, V3 F5 probes OK, syntax compile OK, and all current Agent-native non-native static gates OK.
- Scope: no native build; no Quasar changes; real C++ actor delete/transform calls and visual engine effects remain `[Pending F5/native verification]`.


---

## 14. 2026-07-08 鍚庣画鎵ц淇锛歊2.5 / F5 鍓?Game-ready Scene Runtime 鏈€鐭敾鍧氳矾寰?

> **鏈珷鑺傛槸褰撳墠鏈€鏂版墽琛屽彛寰勩€?*
> 鑻ユ湰绔犺妭涓庡墠鏂囦腑杈冮暱鏈熴€佽緝瀹屾暣鐨?Phase 璁″垝瀛樺湪浼樺厛绾у啿绐侊紝鍦ㄧ涓€杞?F5 / 瀹炴満楠岃瘉閫氳繃鍓嶏紝浼樺厛閬靛畧鏈珷鑺傘€?
> 鏈珷鑺備笉鏄帹缈诲師璁″垝锛岃€屾槸鎶婂悗缁墽琛岃寖鍥村帇缂╁埌鈥滆兘鎵挎帴 AI Game Demo 鐨勫満鏅?Runtime 鏈€灏忓彲杩愯鍒囩墖鈥濄€?

---

### 14.1 鏈€鏂扮幇瀹炲垽鏂?

褰撳墠绯荤粺宸茬粡涓嶆槸鍗曚竴鏃?`SceneComposer` 涓婚摼璺紝浣嗕篃杩樹笉鏄畬鍏ㄥ共鍑€鐨?Agent-native銆傜湡瀹炵姸鎬佹槸锛?

```text
AgentRuntime 涓绘帶姝ｅ湪鎺ョ
鏃?workflow / RoleAgent / Coordinator / LANChat planning gate 浠嶈淇濇姢鎬т繚鐣?
鍏ュ彛銆佺姸鎬併€佺‘璁ゃ€佹墽琛屻€佹姤鍛婁粛瀛樺湪鏂版棫璺緞绔炰簤
```

鍥犳锛屽綋鍓嶆渶瀹规槗鍑洪棶棰樼殑涓嶆槸鈥滅己灏戞洿澶?Agent 鑳藉姏鈥濓紝鑰屾槸锛?

```text
鍏ュ彛 ownership 涓嶆竻
鐘舵€?ownership 涓嶆竻
鎵ц ownership 涓嶆竻
鎶ュ憡 ownership 涓嶆竻
```

鍚庣画閲嶆瀯鐨勬牳蹇冧笉鍐嶆槸缁х画鎵╁睍鍔熻兘锛岃€屾槸璁?AgentRuntime 鐪熸鎷ユ湁锛?

```text
鐢熸垚鎰忓浘鍏ュ彛
鏂规浜嬪疄婧?
纭濂戠害
ToolCallGraph 鎵ц鏉?
RuntimeState 鐘舵€佷簨瀹?
OperationLog 鍥炴斁浜嬪疄
final report 鎶ュ憡浜嬪疄
```

---

### 14.2 褰撳墠闃舵閲嶆柊鍛藉悕

褰撳墠闃舵缁熶竴鍛藉悕涓猴細

```text
R2.5 / F5 鍓?Game-ready Scene Runtime 鏈€灏忔敾鍧?
```

闃舵鐩爣锛?

```text
璁?AgentRuntime 鐪熷疄璺戦€氾細

鐢ㄦ埛纭鐢熸垚
-> ScenePlan
-> BatchPlan
-> ToolCallGraph
-> terrain / environment route
-> asset / model route
-> actor.import/create
-> transform / grounding / AABB
-> review
-> scene_entity_registry
-> RuntimeState
-> OperationLog
-> final report
```

褰撳墠闃舵涓嶆槸锛?

```text
瀹屾暣 AI Game Demo
瀹屾暣 Game-ready Scene Runtime
瀹屾暣娓告垙绛栧垝绯荤粺
瀹屾暣鑴氭湰 / 钃濆浘鐢熸垚绯荤粺
```

褰撳墠闃舵鍙仛锛?

```text
AI Game Demo 鐨勫満鏅?Runtime 鎵挎帴灞?
```

涔熷氨鏄細

```text
鐢熸垚涓€涓悗缁父鎴忛€昏緫鍙互娑堣垂銆佹煡璇€佸紩鐢ㄣ€佸洖鏀剧殑鍦烘櫙瀹炰綋涓栫晫銆?
```

---

### 14.3 鏈樁娈垫槑纭笉鍋?

鍦?R2.5 / F5 鍓嶏紝绂佹鐩存帴瀹炵幇锛?

```text
GameDesignAgent
CombatAgent
StoryAgent
BalanceAgent
ScriptAgent
BlueprintAgent
AudioAgent
PhysicsTuningAgent
瀹屾暣 Gameplay Runtime
瀹屾暣 Script Runtime
瀹屾暣 Blueprint Runtime
```

绂佹涓轰簡楠屾敹鏍蜂緥鍐欐锛?

```text
妫灄钀ュ湴
鑽夊湴
澶╃┖
甯愮
灏忔湪妗?
鎴樻枟
鍓ф儏
鏁板€?
浠诲姟
鑴氭湰
钃濆浘
```

姝ｇ‘鏂瑰紡鏄細

```text
鐢ㄢ€滄．鏋楄惀鍦扳€濋獙璇侀€氱敤 outdoor terrain scene generation vertical slice锛?
鑰屼笉鏄妸绯荤粺鍐欐垚妫灄钀ュ湴涓撶敤鐢熸垚鍣ㄣ€?
```

---

### 14.4 褰撳墠鏈€鐭敾鍧氫富绾?

鍚庣画 Codex / AI 鎵ц蹇呴』浼樺厛娌跨潃杩欐潯鏈€鐭矾寰勬帹杩涳細

```text
淇?AgentRuntime queue drain failed 鐨勭湡瀹炴牴鍥?
  鈫?
纭鐢熸垚鍚庤嚦灏戜骇鐢?1 涓?ScenePlan / BatchPlan
  鈫?
BatchPlan 鑷冲皯浜х敓 1 涓?ToolCallGraph
  鈫?
ToolCallGraph 鑷冲皯鎵ц涓€涓渶灏?actor.import/create 宸ュ叿
  鈫?
ToolResult 蹇呴』鎻愪氦 StatePatch
  鈫?
StatePatch 蹇呴』鍐欏叆 RuntimeState
  鈫?
OperationLog 蹇呴』鑳藉鐩?plan -> terrain -> asset -> actor -> review -> report
  鈫?
scene_entity_registry 蹇呴』鑳借緭鍑哄疄浣撴竻鍗?
  鈫?
final report 鍙兘璇诲彇 RuntimeState + OperationLog
```

褰撳墠涓嶈鎶婁富绾挎墿灞曞埌锛?

```text
杩滅宸紓澶勭悊
Quasar 鑴忛」澶勭悊
澶ц妯?replay summary
澶ц妯￠棬绂?
瀹屾暣娴嬭瘯鐭╅樀
瀹屾暣 VLM 璐ㄩ噺闂幆
澶嶆潅澶氫汉鍐茬獊浠茶
涓婂眰娓告垙 Agent
```

---

### 14.5 P0 鎵ц浠诲姟閲嶆帓

#### P0-0锛氫慨澶?AgentRuntime queue drain failed 鐨勭湡瀹炴牴鍥?

鐩爣锛?

```text
queue drain failed 蹇呴』鏈夋槑纭師鍥犮€佹槑纭姸鎬併€佹槑纭?OperationLog 璁板綍銆?
```

蹇呴』瀹氫綅澶辫触灞炰簬鍝竴绫伙細

```text
graph missing
node failed
guard rejected
tool missing
invalid ToolResult
invalid StatePatch
apply_patch conflict
provider unavailable
exception
cancelled / paused / blocked
```

瀹屾垚鏍囧噯锛?

```text
1. 涓嶅啀鍑虹幇鏃犲師鍥?queue drain failed銆?
2. failed / blocked / cancelled graph 蹇呴』杩涘叆 terminal 鐘舵€併€?
3. graph 涓嶅緱姘镐箙 queued / running銆?
4. drain 澶辫触蹇呴』杩涘叆 OperationLog銆?
5. final report / status_summary 鑳借鍒板畨鍏ㄦ憳瑕併€?
6. failed 涓嶈兘琚绠楁垚 completed銆?
```

绂佹锛?

```text
鍚炲紓甯?
浼 completed
鐢?replay summary 鎺╃洊 queue drain 闂
涓轰簡淇?queue 閲嶅啓鏁翠釜 Runtime 闃熷垪绯荤粺
```

---

#### P0-1锛氱‘璁ょ敓鎴愬繀椤讳骇鐢?ScenePlan + BatchPlan

鐩爣锛?

```text
鐢ㄦ埛纭鐢熸垚鍚庯紝RuntimeState 涓繀椤昏嚦灏戝嚭鐜帮細
1 涓?ScenePlan
1 涓?BatchPlan
```

鏈€灏忛獙鏀讹細

```text
active_plan_id 涓嶄负绌?
active_batch_id 鎴?batch_plans 涓嶄负绌?
BatchPlan 缁戝畾 plan_id
BatchPlan.items 鑷冲皯鍖呭惈鏈疆闇€姹備腑鍙墽琛岀殑鍦烘櫙椤?
environment items 鍜?actor items 涓嶆贩鍦ㄥ悓涓€璺?
```

娉ㄦ剰锛?

```text
BatchPlan 涓嶆槸鑱婂ぉ鎽樿銆?
BatchPlan 涓嶆槸 Coordinator SeedPlan銆?
BatchPlan 蹇呴』鏄?RuntimeState 閲岀殑璁″垝浜嬪疄銆?
```

---

#### P0-2锛欱atchPlan 蹇呴』浜х敓 ToolCallGraph

鐩爣锛?

```text
姣忎釜鍙墽琛?BatchPlan 鑷冲皯鐢熸垚涓€涓?ToolCallGraph銆?
```

鏈€灏?graph 寤鸿锛?

```text
runtime.scene.snapshot
-> scene.extract_objects
-> scene.extract_environment
-> asset.route_item
-> environment.resolve_substrate
-> runtime.actor.plan_import_batch
-> runtime.actor.import_batch / actor.import_model
-> geometry.compute_aabb
-> review.summarize_batch
-> report.final
```

瀹屾垚鏍囧噯锛?

```text
1. RuntimeState 鎴?OperationLog 鍙煡璇?graph_id銆?
2. graph 缁戝畾 plan_id / batch_id銆?
3. graph 鑷冲皯瑕嗙洊 environment / asset / actor / review / report 绫昏妭鐐广€?
4. graph 鍙互杩涘叆 queue銆?
5. drain 鍚庣姸鎬佷笉鑳芥案杩?queued銆?
```

---

#### P0-3锛歵errain / environment / substrate 璺敱蹇呴』鍏堜簬鏅€?asset/model

鐩爣锛?

```text
鑽夊湴 / 澶╃┖ / ground / terrain / sky / forest floor 绛夌幆澧冮」
蹇呴』杩涘叆 environment / terrain / substrate 閾捐矾锛?
涓嶅緱杩涘叆鏅€?asset / model / actor 閾捐矾銆?
```

鍩虹鍒嗙被锛?

```text
鑽夊湴 -> terrain/substrate
澶╃┖ -> environment/skybox
ground -> terrain/substrate
terrain -> terrain
妫灄鑳屾櫙 / 鏍戞灄鐜 -> environment
鏍戞湪涓綋 / 鍙憜鏀炬湪妗?-> asset/model/actor
甯愮 -> asset/model/actor
灏忔湪妗?-> asset/model/actor
```

瀹屾垚鏍囧噯锛?

```text
1. environment_state / terrain_state 鑳借褰曡崏鍦般€佸ぉ绌恒€佸湴褰㈢被浜嬪疄銆?
2. asset_state / actor_state 涓嶅寘鍚ぉ绌恒€佽崏鍦扮瓑鐜椤圭殑鏅€氭ā鍨嬪鍏ョ粨鏋溿€?
3. 璺敱閫昏緫鏄€氱敤璇嶇被 / entity_type 瑙勫垯锛屼笉鏄．鏋楄惀鍦颁笓鐢?if銆?
```

---

#### P0-4锛氭渶灏?actor.import/create 宸ュ叿闂幆

鐩爣锛?

```text
ToolCallGraph 鑷冲皯鑳芥墽琛屼竴涓?actor.import/create 绫诲伐鍏枫€?
```

鍞竴鍏佽鐨勭湡瀹炲啓閾捐矾锛?

```text
ToolCall
-> RuntimeGuard
-> EngineWriteGate / runtime_cpp_bridge
-> C++ Engine
-> ToolResult
-> StatePatch
-> RuntimeState
-> OperationLog
```

濡傛灉鐪熷疄 C++ bridge 鏈帴閫氾紝鍏佽锛?

```text
engine_write_status = runtime_state_only
engine_write_status = engine_unavailable
engine_write_status = engine_call_failed
engine_write_status = pending_f5
```

绂佹锛?

```text
engine_write_status = success
```

闄ら潪鐪熷疄 C++ / Engine 杩斿洖浜?actor_id / component_id / transform result 绛夋垚鍔熺粨鏋溿€?

瀹屾垚鏍囧噯锛?

```text
1. actor.import/create 宸ュ叿琚?ToolCallGraph 璋冪敤銆?
2. RuntimeGuard 鏈夋巿鏉冩垨鎷掔粷璁板綍銆?
3. ToolResult 鏈夋槑纭?success / failed / unavailable / pending_f5銆?
4. ToolResult 鍙彁浜?StatePatch锛屼笉鐩存帴鏀?RuntimeState銆?
5. StatePatch 鍐欏叆 actor_state銆?
6. OperationLog 鑳界湅鍒?actor import 灏濊瘯鍜岀粨鏋溿€?
```

---

#### P0-5锛歛ctor transform / grounding / AABB 鏈€灏忎簨瀹?

鐩爣锛?

```text
姣忎釜 actor 鑷冲皯鏈?transform銆乬rounding_status銆丄ABB/bounds 鐨勬渶灏忎簨瀹炪€?
```

鍏佽鐘舵€侊細

```text
resolved
estimated
unknown
failed
pending_f5
```

瀹屾垚鏍囧噯锛?

```text
1. 甯愮鏈?transform銆?
2. 灏忔湪妗屾湁 transform銆?
3. actor 鏈?grounding_status銆?
4. actor 鏈?AABB / bounds銆?
5. geometry_state 鑳芥煡鍒?actor 瀵瑰簲缁撴灉銆?
6. review_state 鑳界湅鍒?geometry / grounding review 鎽樿銆?
```

濡傛灉 AABB 鏉ヨ嚜浼扮畻鑰屼笉鏄湡瀹炲紩鎿庯細

```text
aabb_status = estimated
review_status = warning / pending_f5
```

绂佹鎶婁及绠楃粨鏋滀吉瑁呮垚鐪熷疄 Engine AABB銆?

---

#### P0-6锛歴cene_entity_registry 鏈€灏忓彲鐢?

鐩爣锛?

```text
鎶?RuntimeState 涓殑 terrain / environment / asset / actor / geometry / review / sync
鑱氬悎鎴愬悗缁父鎴忛€昏緫鍙秷璐圭殑瀹炰綋娓呭崟銆?
```

鏈€浣庡瓧娈碉細

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

褰撳墠榛樿鍊艰鍒欙細

```text
interaction_capability = none / decorative / interactable_candidate
gameplay_tags = []
script_bindings = []
physics_profile = default
audio_profile = default
lighting_profile = default
sync_status = pending / local_only / synced / failed / unknown
review_status = pending / passed / warning / failed / unavailable
```

瀹屾垚鏍囧噯锛?

```text
1. scene_entity_registry 鑳借緭鍑鸿崏鍦?/ 澶╃┖ / 甯愮 / 灏忔湪妗岀浉鍏充簨瀹炪€?
2. actor 绫诲疄浣撴湁 actor_id 鎴?pending_actor_id銆?
3. environment 绫诲疄浣撲笉浼鎴?actor銆?
4. final report 鍙互璇诲彇 entity registry 鎽樿銆?
5. 鍚庣画 GameDesignPlan / ScriptPlan 鍙互绋冲畾寮曠敤杩欎簺瀛楁銆?
```

---

#### P0-7锛歠inal report 鍙 RuntimeState + OperationLog

鐩爣锛?

```text
final report 涓嶅啀鎷?SceneComposer summary锛?
涓嶈 GenerationScheduler 鍐呴儴鐘舵€侊紝
涓嶈 Coordinator 鐚滄祴鐘舵€侊紝
涓嶈 RoleAgent chat memory銆?
```

final report 蹇呴』璇存槑锛?

```text
plan 鏄惁鍒涘缓
batch 鏄惁鍒涘缓
ToolCallGraph 鏄惁鎵ц
terrain/environment 鏄惁杩涘叆瀵瑰簲閾捐矾
asset/model/actor 鏄惁杩涘叆瀵瑰簲閾捐矾
actor import 鏄?success / failed / runtime_state_only / unavailable / pending_f5
transform / AABB / grounding 鏄?resolved / estimated / unknown / failed / pending_f5
scene_entity_registry 杈撳嚭浜嗗灏戝疄浣?
sync / VLM / real engine 鏁堟灉鍝簺鏄?[寰?F5/瀹炴満楠岃瘉]
```

绂佹妯＄硦缁撹锛?

```text
鐢熸垚鎴愬姛
鍦烘櫙宸插畬鎴?
鍏ㄩ儴瀵煎叆鎴愬姛
```

闄ら潪鐪熷疄 Engine / RuntimeState / OperationLog 涓夎€呬竴鑷存敮鎸佽缁撹銆?

鎺ㄨ崘鎶ュ憡璇箟锛?

```text
Runtime planning completed.
RuntimeState entity facts recorded.
Engine write pending F5 verification.
```

鎴栵細

```text
Engine actor import succeeded.
RuntimeState and OperationLog recorded engine result.
```

---

#### P0-8锛氬叆鍙ｄ笌 Legacy 闈欐€佸皝閿佸彧鍋氬繀瑕佹敹鍙?

褰撳墠涓嶈繘琛屽ぇ瑙勬ā鍏ュ彛閲嶆瀯锛屼絾蹇呴』纭繚锛?

```text
鐢熸垚绫昏姹備笉寰楁紡鍒?RoleAgent 鏃?compose
RoleAgent / MasterAgent 涓嶅緱杩斿洖 start_generation action
SceneComposer / ProgressiveWorkflow 涓嶅緱閲嶆柊鏆撮湶鏅€氱敤鎴峰叆鍙?
鏃?workflow 涓嶅緱琚寘瑁呮垚 legacy big tool
鐘舵€佹煡璇笉寰楄鍙栨棫 workflow summary
```

RoleAgent / MasterAgent 褰撳墠瀹氫綅锛?

```text
talk-only
瑙ｉ噴鏂规
鎻愪緵寤鸿
鏅€氳亰澶?
鎶婄敓鎴愮被鎰忓浘杞氦 Runtime planning
```

Coordinator 褰撳墠瀹氫綅锛?

```text
compatibility adapter
鍙互淇濈暀纭浣撻獙
涓嶅緱鎴愪负鏈€缁堟柟妗堜簨瀹炴簮
SeedPlan 蹇呴』鏄犲皠鍒?ScenePlan
```

---

### 14.6 鎴愬姛璇箟蹇呴』鎷嗗垎

鍚庣画鎵€鏈夌姸鎬併€佹姤鍛娿€佹祴璇曡緭鍑洪兘涓嶅緱鍐嶄娇鐢ㄥ崟涓€鈥滅敓鎴愭垚鍔熲€濄€?

蹇呴』鎷嗘垚锛?

```text
plan_success
batch_success
tool_graph_success
resource_success
engine_write_success
runtime_state_success
operation_log_success
sync_success
review_success
report_success
```

鏈粡杩?F5 / 瀹炴満楠岃瘉鏃讹紝蹇呴』鏍囪锛?

```text
[寰?F5/瀹炴満楠岃瘉]
```

灏ゅ叾浠ヤ笅鍐呭蹇呴』鏍囪锛?

```text
C++ actor import
actor transform
actor delete
terrain / environment 鐪熷疄鍐欏叆
asset transfer
LAN peer sync
VLM screenshot
鐪熷疄 Engine 鍦烘櫙鏁堟灉
CEF UI 闀胯€楁椂鍙嶉
澶氫汉鑱旀満鍙鎬?
```

---

### 14.7 F5 鍓嶆渶灏忛獙鏀跺満鏅?

鍥哄畾绗竴杞?F5 楠屾敹璇彞锛?

```text
鐢熸垚涓€涓畝鍗曟．鏋楄惀鍦帮紝鏈夎崏鍦般€佸ぉ绌恒€佸笎绡枫€佸皬鏈ㄦ銆?
纭鐢熸垚銆?
鏌ョ湅鐘舵€併€?
鏌ョ湅鏈€缁堟姤鍛娿€?
鏌ョ湅 operation replay銆?
```

楠屾敹鐩殑锛?

```text
楠岃瘉閫氱敤 outdoor terrain scene Runtime锛?
涓嶆槸楠岃瘉妫灄钀ュ湴涓撶敤閫昏緫銆?
```

蹇呴』婊¤冻锛?

```text
鑽夊湴 / 澶╃┖ / ground / terrain 杩涘叆 environment / terrain / substrate 閾捐矾
甯愮 / 灏忔湪妗岃繘鍏?asset / model / actor 閾捐矾
actor import/create 缁忚繃 RuntimeGuard
actor 鏈?transform / grounding / AABB
RuntimeState 鑳芥煡 terrain / environment / asset / actor / geometry / review
scene_entity_registry 鑳借緭鍑哄疄浣撴竻鍗?
OperationLog 鑳藉鐩?plan -> terrain -> asset -> actor -> review -> report
final report 鍙 RuntimeState + OperationLog
```

---

### 14.8 娴嬭瘯绛栫暐鏀剁缉

褰撳墠鍙窇锛?

```text
python -B editor/plugins/AITool/services/verify_ultimate_plan.py
鏈疆鐩存帴鐩稿叧娴嬭瘯
蹇呰 syntax compile
```

鍙互鍚庣疆锛?

```text
闈?P0 杈硅娴嬭瘯
澶ц妯?replay summary 娴嬭瘯
涓庢湰杞?vertical slice 鏃犲叧鐨勫巻鍙插洖褰?
澶嶆潅 VLM 鏁堟灉娴嬭瘯
澶嶆潅澶氫汉鍐茬獊浠茶娴嬭瘯
瀹屾暣娓告垙绛栧垝 / 鑴氭湰 Agent 娴嬭瘯
```

涓嶅彲鍚庣疆锛?

```text
verify_ultimate_plan.py 澶辫触
璇硶缂栬瘧澶辫触
RuntimeGuard 缁曡繃
ToolResult 鐩存帴鍐?RuntimeState
StatePatch 涓嶇粡 Validator
final report 璇诲彇鏃?workflow
SceneComposer / ProgressiveWorkflow 鏅€氬叆鍙ｅ娲?
queue drain 鏃犲師鍥犲け璐?
engine success 浼€?
```

---

### 14.9 涓?AI Game Demo 鐨勬壙鎺ラ棬妲?

褰撳墠闃舵瀹屾垚鍚庯紝椤圭洰鎵挎帴 AI Game Demo 鐨勯棬妲涙寜浠ヤ笅椤哄簭鍒ゆ柇锛?

```text
R2.5锛?
F5 鍓嶆渶灏?vertical slice銆?
璇佹槑 Runtime 鑳芥妸鍦烘櫙瀹炰綋浜嬪疄鍐欏叆 RuntimeState / OperationLog銆?
涓嶈兘姝ｅ紡鎺ユ父鎴?Agent銆?

R3-min锛?
Game-ready Scene Runtime 鏈€灏忓彲鐢ㄣ€?
scene_entity_registry 绋冲畾锛宎ctor/entity facts 鍙鍚庣画閫昏緫娑堣垂銆?
鍙互寮€濮嬭璁?G0 schema锛屼絾涓嶆帴鍙墽琛屾父鎴?Agent銆?

瀹屾暣 R3锛?
Game-ready Scene Runtime 瀹屾垚銆?
RuntimeState / scene_entity_registry / OperationLog / Engine write / sync / review 浜嬪疄绋冲畾銆?
鍙互杩涘叆 G1锛欸ameDesignAgent / StoryAgent / CombatAgent / BalanceAgent 杈撳嚭缁撴瀯鍖栬鍒掋€?

G2锛?
Gameplay ToolCallGraph銆?
鍙互鎶?GameDesignPlan / QuestPlan / CombatPlan / BalancePlan 杞垚 gameplay state facts銆?

G3锛?
ScriptAgent / BlueprintAgent銆?
蹇呴』缁忚繃 ScriptValidator / RuntimeGuard / EngineScriptAdapter / ToolResult / StatePatch銆?

G4锛?
涓€閿?AI Game Demo銆?
鐢ㄦ埛杈撳叆涓€涓父鎴忕洰鏍囷紝绯荤粺鐢熸垚鍙帺鐨?demo銆?
```

鍏抽敭杈圭晫锛?

```text
R3 涔嬪墠锛氫笉瑕佹寮忓仛娓告垙 Agent 涓婚摼璺€?
R3-min 涔嬪悗锛氬彲浠ュ仛 GameWorldState / GameDesignPlan schema銆?
瀹屾暣 R3 涔嬪悗锛氬彲浠ユ帴绛栧垝 / 鍓ф儏 / 鎴樻枟 / 鏁板€?Agent锛屼絾鍙緭鍑?Plan銆?
G3 涔嬪悗锛氭墠鎺?ScriptAgent / BlueprintAgent銆?
```

---

### 14.10 缁?AI / Codex 鐨勬渶鏂版墽琛屽彛寰?

鍚庣画缁?AI / Codex 鐨勪换鍔℃彁绀哄缓璁粺涓€浣跨敤浠ヤ笅鍙ｅ緞锛?

```text
浣犲繀椤婚伒瀹堬細
E:\corona\CoronaEngine\docs\Agent浠诲姟绾︽潫寰幆.md

浣犲繀椤绘寜浠ヤ笅璁″垝缁х画鎺ㄨ繘锛?
E:\corona\CoronaEngine\docs\Agent-native涓€姝ュ埌浣嶉噸鏋勮鍒抇瀹炴柦璁″垝淇敼鐗?md

褰撳墠鏈€鏂拌鐩栫珷鑺傦細
绗?14 绔狅細2026-07-08 鍚庣画鎵ц淇锛歊2.5 / F5 鍓?Game-ready Scene Runtime 鏈€鐭敾鍧氳矾寰勩€?

褰撳墠闃舵锛?
R2.5 / F5 鍓?Game-ready Scene Runtime 鏈€灏忔敾鍧氥€?

褰撳墠鐩爣锛?
涓嶆槸瀹炵幇瀹屾暣 AI Game Demo銆?
涓嶆槸瀹炵幇 GameDesignAgent / CombatAgent / StoryAgent / BalanceAgent / ScriptAgent / BlueprintAgent銆?
鏈樁娈靛彧鎶婂満鏅?Runtime 鍋氬埌鍚庣画娓告垙閫昏緫鍙秷璐广€?

鏈€鐭矾寰勶細
1. 淇 AgentRuntime queue drain failed 鐨勭湡瀹炴牴鍥犮€?
2. 纭鐢熸垚鍚庤嚦灏戜骇鐢?1 涓?ScenePlan 鍜?1 涓?BatchPlan銆?
3. BatchPlan 鑷冲皯浜х敓 1 涓?ToolCallGraph銆?
4. ToolCallGraph 鑷冲皯鎵ц terrain/environment route 涓?actor.import/create 鏈€灏忓伐鍏枫€?
5. 鎵€鏈夌湡瀹炲啓鍏ュ繀椤昏蛋 ToolCall -> RuntimeGuard -> EngineWriteGate / runtime_cpp_bridge -> ToolResult -> StatePatch -> RuntimeState -> OperationLog銆?
6. scene_entity_registry 蹇呴』杈撳嚭鍚庣画娓告垙閫昏緫鍙秷璐圭殑瀹炰綋娓呭崟銆?
7. final report 鍙兘璇诲彇 RuntimeState + OperationLog銆?
8. C++ actor import / transform / delete銆乼errain 鐪熷疄鍐欏叆銆乻ync銆乤sset transfer銆乂LM screenshot銆佺湡瀹?Engine 鏁堟灉缁熶竴鏍囪 [寰?F5/瀹炴満楠岃瘉]銆?

绂佹锛?
- 缁曡繃 RuntimeGuard锛?
- 鎶?SceneComposer / ProgressiveWorkflow 鍖呮垚 legacy big tool锛?
- 閲嶆柊鏆撮湶鏃?workflow 鐢ㄦ埛鍏ュ彛锛?
- 涓烘．鏋楄惀鍦般€佸笎绡枫€佸皬鏈ㄦ銆佽崏鍦般€佸ぉ绌哄啓姝讳笓鐢ㄩ€昏緫锛?
- 褰撳墠闃舵瀹炵幇涓婂眰娓告垙 Agent锛?
- 浼€?Engine success锛?
- 涓洪潪 P0 杈硅娴嬭瘯澶ч潰绉噸鏋勶紱
- 鎵╁ぇ閲?replay summary / 闂ㄧ / 娴嬭瘯鐭╅樀銆?
```

---

### 14.11 鏈珷鑺傚畬鎴愬悗锛屼笅涓€姝ュ簲璇ヨ繘鍏ョ殑浠诲姟闃熷垪

鎺ㄨ崘鍚庣画浠诲姟闃熷垪椤哄簭锛?

```text
Task R2.5-01锛?
瀹氫綅骞朵慨澶?AgentRuntime queue drain failed 鐪熷疄鏍瑰洜銆?

Task R2.5-02锛?
纭鐢熸垚鍚庡己鍒惰惤 ScenePlan / BatchPlan锛屽苟鍐?RuntimeState + OperationLog銆?

Task R2.5-03锛?
BatchPlan 鐢熸垚 ToolCallGraph锛岃嚦灏戝寘鍚?scene.extract_objects / terrain route / actor import / review / report銆?

Task R2.5-04锛?
terrain / environment / substrate 璺敱涓?asset/model/actor 璺敱褰诲簳鍒嗙銆?

Task R2.5-05锛?
鏈€灏?actor.import/create 闂幆锛屼弗鏍兼墽琛?RuntimeGuard -> EngineWriteGate -> ToolResult -> StatePatch銆?

Task R2.5-06锛?
actor transform / grounding / AABB 鏈€灏忎簨瀹炲啓鍏?geometry_state / review_state銆?

Task R2.5-07锛?
scene_entity_registry 鑱氬悎 terrain / environment / asset / actor / geometry / review / sync銆?

Task R2.5-08锛?
final report 鏀逛负鍙 RuntimeState + OperationLog锛屽苟鍖哄垎 runtime_state_only / pending_f5 / engine_success銆?

Task R2.5-09锛?
浣跨敤鍥哄畾 F5 鏈€灏忓満鏅仛瀹炴満楠岃瘉锛屽苟鎶婃湭楠岃瘉椤规爣璁?[寰?F5/瀹炴満楠岃瘉]銆?

Task R2.5-10锛?
F5 閫氳繃鍚庯紝鍐嶅喅瀹氭槸鍚﹁繘鍏?R3-min / GameWorldState schema銆?
```

---

### 14.12 鏈珷鎬荤粨

褰撳墠閲嶆瀯鍚庣画鐨勬牳蹇冨垽鏂槸锛?

```text
涓嶈缁х画琛ヨ嚜鐒惰瑷€鍒嗙被銆?
涓嶈缁х画鎵╀笂灞?Agent銆?
涓嶈缁х画鍫?replay summary銆?
涓嶈缁х画璁╂棫 workflow 鍙備笌浜嬪疄婧愩€?

鍏堣 AgentRuntime 鑳藉彲淇″湴浜х敓锛?
ScenePlan
BatchPlan
ToolCallGraph
RuntimeState
OperationLog
scene_entity_registry
final report
```

涓€鍙ヨ瘽鐩爣锛?

```text
鍏堣 Runtime 鍙俊鍦颁骇鐢熲€滄父鎴忓彲娑堣垂鐨勫満鏅疄浣撲笘鐣屸€濓紝鍐嶈娓告垙 Agent 娑堣垂杩欎釜涓栫晫銆?
```
