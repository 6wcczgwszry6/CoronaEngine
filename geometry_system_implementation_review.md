# GeometrySystem 四大核心设计目标 — 实现状态分析

> 分析范围：commit `5197c8c2` → `142a9f89` (HEAD)
> 分析时间：2026-07-12

---

## 目标 1：八叉树分块流式加载/预加载/释放

### 已实现

**八叉树空间索引存在且在工作**

每个场景有一个 `Spatial::Octree`，每帧重建，存所有 actor 的 AABB。查询接口使用 `tree.query_sphere(cam_pos, preload_distance, results)` 来查找相机周围范围内的物体。

**预加载机制**

```
每帧 for 每个场景:
  1. 用八叉树 query_sphere 找到 preload_distance 内的所有 actor
  2. 过滤出状态为 Unloaded 的
  3. 按距离排序（近者优先）
  4. 每帧最多发起 4 个加载请求（防止上百个同时加载撑爆线程池）
  5. 异步 import → 完成后回调 on_load_finished
```

**pinned 保护**

ActorDevice 有 `pinned` 标记。pinned 的 actor 不被距离剔除、不被不可见帧淘汰、不被满载淘汰。evict 快照时同步写入 pinned 状态。

**四态加载状态机**

```
Unloaded → Loading → Loaded
                       ↓ (满载淘汰)
                  Unloading → Unloaded
```

加载/卸载进行中不可重复触发，加载中收到卸载请求则取消加载。

**restore 防抖**

on_restore_requested 有 2 秒冷却——刚被 evict 的 actor 不立即 restore，避免 preload/unload 边界反复横跳。

**新加载 actor 保护**

`last_load_finished_time` 记录每个 actor 最近加载完成时间。淘汰逻辑跳过"刚加载完成"的 actor——渲染线程可能还没识别到它可见（有一到两帧延迟）。

**无网格 actor 处理**

空 `model_path` 的 actor（如音频物体）不参与几何加载/距离剔除，避免每帧反复请求加载空路径。

### 没有实现

**不是真正的"分块（block）流式加载"**

当前加载粒度是**单个 actor**，不是**空间块**。真正的分块流式加载（如 UE5 World Partition）会把世界划分为固定大小的网格，每个网格作为一个加载单元整体加载/卸载。当前系统每个 actor 独立判断、独立加载——100 个 actor 在范围内就是 100 个独立决策。

**没有基于八叉树估计的自动卸载**

旧代码有 `PendingUnload` 逻辑（物体超出 `unload_distance` → 按 actor 逐个判断卸载），在 commit `70c7e3be` 中被删除。目前卸载的**唯一触发条件**是 `evict_under_memory_pressure`（显存/内存用到 90%）。对于内存充裕的机器，可能永远不会触发卸载，显存里堆积大量无用数据。

**计划方案：八叉树估计卸载**

不再恢复到旧代码的 per-actor 距离逐一判断，而是利用已有的八叉树做空间块级卸载：

1. **遍历八叉树节点**：从根向叶子遍历，对每个非叶节点，用其 AABB 到相机的最近距离（`distance_point_to_aabb`，现成函数）估算该节点整体是否远离
2. **节点级卸载判定**：若某节点的 AABB 最小距离 > `unload_distance`，则该节点下所有 actor 均视为"远离"——一次性标记卸载，无需逐 actor 计算距离
3. **lod_unload_distance 分级**：不设单一阈值，按 LOD 级别分别设置——LOD0~1 的 unload 距离可以设得很大（精细模型值得保留更久），LOD4+ 的 unload 距离收紧（粗模早卸）
4. **与 preload 对称**：preload 用 `tree.query_sphere(cam_pos, preload_distance)` 加载球内物体，unload 用八叉树遍历找到球外节点卸载，二者在空间结构上对称，逻辑清晰

优势：O(log N) 八叉树遍历替代 O(N) 逐 actor 遍历；节点级批量卸载减少状态变更次数；与现有的八叉树预加载形成闭环。

**没有相机方向感知预加载**

当前预加载是"以相机为球心画一个球"，所有方向同等对待。但实际上相机前方的物体应该优先于背后的物体。

### 评估

```
八叉树空间索引              ████████████████████  完成
预加载（距离触发）          ████████████████████  完成
预加载排序限帧              ████████████████████  完成
pinned 保护                 ████████████████████  完成
四态状态机                  ████████████████████  完成
restore 防抖                ████████████████████  完成
新加载 actor 保护           ████████████████████  完成
无网格 actor 跳过           ████████████████████  完成
────────────────────────────────────────────────────
分块/打包加载               ░░░░░░░░░░░░░░░░░░░░  未实现
八叉树估计卸载              ░░░░░░░░░░░░░░░░░░░░  已设计，待实现
相机方向感知预加载          ░░░░░░░░░░░░░░░░░░░░  未实现
```

**约 72%**

---

## 目标 2：LOD 层级由相机距离（像素映射）决定

### 已实现

这是四个目标里实现最完整的。

**核心公式：屏幕空间误差模型**

```
第 1 步：像素预算 → 角预算
  epsilon = pixel_budget × 2×tan(fov/2) / height_px

第 2 步：模型空间误差 → 世界误差
  world_error[i] = geometric_error[i] × actor_scale

第 3 步：判断某级是否"够好"
  world_error[i] / d ≤ epsilon
  其中 d = 相机到 mesh 包围盒最近点的距离

第 4 步：选"最粗的可接受级别"
  从最粗级向精细方向扫描
```

**用"到包围盒最近点距离"而非"到中心距离"**

`distance_point_to_aabb` 计算相机到 AABB 每个面的越界量。一条 100m 长的火车，相机在车头前 10m：到中心距离=60m（误判"远"），到最近点=10m（正确"近"）。相机进入包围盒时 d=0 → 角误差无限大 → 强制 LOD0，天然正确。

**per-mesh 局部 AABB**

旧方案用整场景 AABB 的外接球半径作为所有 mesh 的 bounding_radius——大场景里的小物体（桌面上的杯子）拿到巨大半径，恒选 LOD0。新方案每个 mesh 缓存自己的局部 AABB，用完整 transform 矩阵映到世界空间，小物体不再被大场景半径误判。

**滞回死区（防抖动）**

```
kLodHysteresis = 15%

当前在 LOD1:
  降级(LOD1→LOD2): ratio < 阈值×(1-0.15) ← 更严格才降
  升级(LOD2→LOD1): ratio > 阈值×(1+0.15) ← 更严格才升
  死区中间 → 维持不变
```

没有死区时，ratio 刚好在阈值附近波动 → 每帧切换 LOD → 画面闪烁。有死区后微小的相机抖动被吸收。

**多相机聚合**

所有相机取最高精度（`min` 级号）= 任一视角的需求都要满足。不能因为顶视图只需要粗网格就让透视相机的玩家看到粗糙模型。

**Swap 平滑切换模型**

```
demand 从 LOD1 → LOD3:
  ① committed_demand=3, swap_in_progress=true, prev_committed=1
  ② 保留 LOD1 供渲染降级（不会黑屏）
  ③ LOD3 异步构建中...
  ④ 构建完成 → 同一帧释放 LOD1 → swap_in_progress=false
  保活窗口: <5 帧（vs 旧方案 90 帧）
```

**异步 LOD 构建（方案 C）**

TBB `task_group` 在 worker 线程构建 GPU 缓冲，几何线程 `process_pending_lod_builds` 轮询回写。`residency_epoch` + `model_id` 双重 ABA 守卫，防止 evict→erase→重载后旧任务误填新条目。

**compute_screen_ratio 修复**

旧代码 `d < 1e-4f` 钳制不够——相机进入包围球后 d→0 导致 ratio→∞，ratio 摆动数百个百分点跨越多个阈值。修复：`d = max(d, bounding_radius)`，贴近时 ratio 饱和在 `1/tan(fov/2)`，恒选 LOD0。

### 评估

```
屏幕空间误差模型          ████████████████████  完成
geometric_error × scale   ████████████████████  完成
到包围盒最近点距离        ████████████████████  完成
角预算 epsilon            ████████████████████  完成
滞回死区 (15%)            ████████████████████  完成
多相机聚合 (min)          ████████████████████  完成
Swap 切换模型             ████████████████████  完成
异步构建 (TBB)            ████████████████████  完成
ABA 守卫                  ████████████████████  完成
per-mesh AABB             ████████████████████  完成
screen_ratio 钳制修复     ████████████████████  完成
```

**约 95%**

---

## 目标 3：基于 LOD 层级的 LRU + 内存不够时的降级

### 已实现

**Actor 级别的三层 LRU 淘汰链**

```
Layer 1: ActorCache（磁盘缓存）
  - DiskCache: LRU 按 last_access 淘汰
  - 增量计数器 used_（O(1) 替代旧的 O(n) calc_directory_size 全目录扫描）
  - put() 三阶段: 持锁索引操作 → 锁外磁盘写 → 持锁结果确认/回滚

Layer 2: ResourceCache（CPU 内存）
  - ResourceEntry{ pinned, estimated_bytes, last_access }
  - pin/unpin/touch/try_evict
  - evict_until_under_budget: 按 last_access 循环淘汰

Layer 3: ResourceManager（统一入口）
  - 透传全部 8 个新方法
```

**满载淘汰安全网**

```
每 15 帧检查:
  水位: high=容量×90%, low=容量×80%
  need_free = used - low

  如果 used ≥ high:
    1. 收集所有 Loaded + 非 pinned + 非加载中的 actor
    2. 按"冷度"排序（距相机远者优先）
    3. 从最冷的开始淘汰（最多 64 个/轮）
    4. 直到 need_free=0 或无可淘汰
```

**GPU 压力绝不清 CPU**

```
gpu_only = !ram.pressured

gpu_only=true:
  → 释放 GPU 缓冲 ✓
  → 保留 Scene CPU 数据 ✓
  → 恢复时从 CPU 快速重建（毫秒级，不需要磁盘重导）

gpu_only=false（RAM 也承压）:
  → 级联 try_evict 释放底层 CPU 资源
```

### 没有实现 —— 核心差距

**LRU 在 Actor 级别运作，不在 LOD 级别运作**

当前的淘汰逻辑：
```
"这个 actor 太远 → 整个 actor 淘汰"
"显存快爆 → 淘汰最远的几个 actor"
```

目标要求的是更细粒度：
```
"VRAM 紧张 → 所有中等距离 actor 的 LOD3 清掉，只保留 LOD1"
"还是紧张 → 远距离 actor 连 LOD1 也别要了"
```

两者的区别：
- **淘汰整个 actor**：释放该 actor 所有数据（GPU+CPU），恢复需要重新 import → 代价大
- **释放单个 LOD 级别**：只释放某 actor 的 LOD3，LOD0/LOD1 还在 → 代价小

**~~缺少~~"把显存预算反馈到 LOD 选级"的闭环** ✅ 已完成 (96cef63d)

```
已实现 (commit 96cef63d):
  compute_pixel_budget_from_pressure(vram_ratio) — 阶梯分段映射
    < 60% → 1.5px（正常，视觉无损）
    < 75% → 3.0px（轻度承压，2×）
    < 85% → 6.0px（中度承压，4×）
    < 92% → 12.0px（重度承压，8×）
    ≥ 92% → 24.0px（极限，16×，几乎总选最粗级）

  reconcile_lod_residency() 每帧:
    ① compute_memory_report() → used/budget 比值
    ② compute_pixel_budget_from_pressure(ratio) → 动态 pixel_budget
    ③ 替代原 constexpr kLodPixelErrorBudget → compute_angular_epsilon
    ④ budget_bytes==0 时回退默认 1.5px

  改动: 4 文件, +32/-3 行。阶梯分段防 LOD 振荡，与 evict_under_memory_pressure(90%)
  形成"软调节(60%) + 硬兜底(90%)"双层机制。
```

**跨 Actor 的 LOD 优先级比较缺失**

假设显存只能再容纳 100MB：

| Actor | 距离 | 需求 LOD | 大小 | 重要性 |
|-------|------|----------|------|--------|
| A | 10m | LOD1 | 5MB | 高（视野中央） |
| B | 50m | LOD2 | 3MB | 中（视野边缘） |
| C | 200m | LOD5 | 1MB | 低 |

优秀策略：优先满足 A 的 LOD1（5MB），再满足 B 的 LOD2（3MB），C 的 LOD5 可以不构建（回退 LOD0）。当前系统：A/B/C 各自独立决策，不知道彼此存在。没有"全局 LOD 优先级队列"。

### 评估

```
Actor 级 LRU (ActorCache)    ████████████████████  完成
ResourceManager pin/touch    ████████████████████  完成
满载淘汰 (90%→80%)          ████████████████████  完成
GPU 压力不清 CPU (gpu_only)  ████████████████████  完成
estimate_actor_memory         ████████████████████  完成
显存预算反馈到 LOD 选级      ████████████████████  完成 (96cef63d)
────────────────────────────────────────────────────
LOD 级别粒度的 LRU           ░░░░░░░░░░░░░░░░░░░░  未实现
跨 Actor 的 LOD 优先级比较   ░░░░░░░░░░░░░░░░░░░░  未实现
每个 Actor 的 LOD 独立预算   ░░░░░░░░░░░░░░░░░░░░  未实现
```

**约 55%**（P0 完成，提升 15%）

---

## 目标 4：尽可能少保存 LOD 层级

### 已实现

这是实现质量最高的目标。

**GPU 端：仅 {LOD0, 需求级 D} 驻留**

`reconcile_lod_residency()` 核心逻辑：
```
for 每个 (geometry, mesh):
  ① 多相机联合算需求级 D（含滞回死区）
  ② 限速反向（方案 D）：committed 直跳目标，不逐级移动
  ③ D 未就绪 → 从 Scene CPU 取数据 → 异步构建
  ④ 释放所有 ≠ D 的已就绪级（含 LOD0，若 D>0）
```

稳态：每 mesh 至多 2 套 GPU 缓冲。
旧方案：每 mesh 全部 N 套（N 可达 9）。

**限速反向（方案 D）**

旧方案 demand 每帧最多移动一级 → 相机拉远时逐级构建+释放每个中间级 → N 次 GPU 上传抖动。新方案直跳目标级 → 只构建目标级 1 次，跳过所有中间级。

**CPU 端：3 层窗口管理**

`reconcile_cpu_residency()` 每 120 帧（2 秒）运行：

```
① 按 model_id 收集所有实例的 committed_demand
② 计算中位数 D_med
③ 窗口 = { lod_levels[0], lod_levels[D_med-1], lod_levels[N-1] }
   - [0]:         最精细简化级，始终保留
   - [D_med-1]:   中位数需求级（大多数实例需要）
   - [N-1]:       最粗级，始终保留
④ acquire_write<Scene> → 窗口外 clear()+shrink_to_fit()
```

用中位数而非平均数：50 棵近树 demand=0，50 棵远树 demand=5。平均数=2.5 → 如果只保留 LOD3，远树需要 LOD5 就得从磁盘重导。中位数更准。

LOD0（MeshData::vertices/indices）永远保留，不在此管理范围。

**Swap 模型：切换期间几乎不额外占用**

```
旧方案: kLodReleaseCooldownFrames=90 → 90 帧内 VRAM 有 2 套简化缓冲
新方案: 新级 ready → 同一帧释放旧级 → <5 帧保活窗口
```

### 可优化但非必须

- CPU 窗口固定 3 层，不随内存压力自适应（可缩到 2 层或 1 层）
- 无模型重要度分级（主角应保留更多 LOD，碎石可只保留 1 层）

### 评估

```
GPU: {LOD0, demand} 驻留    ████████████████████  完成
GPU: Swap 瞬时切换          ████████████████████  完成
GPU: LOD0 可 Tier 2 淘汰    ████████████████████  完成
GPU: 异步构建不阻塞帧       ████████████████████  完成
GPU: 限速反向（跳级）       ████████████████████  完成
GPU: GpuMemToken 记账        ████████████████████  完成
CPU: 3 层窗口管理           ████████████████████  完成
CPU: 中位数需求级           ████████████████████  完成
CPU: clear+shrink_to_fit    ████████████████████  完成
CPU: 120 帧间隔评估         ████████████████████  完成
────────────────────────────────────────────────────
自适应窗口大小              ░░░░░░░░░░░░░░░░░░░░  可优化（非必须）
模型重要度分级              ░░░░░░░░░░░░░░░░░░░░  可优化（非必须）
```

**约 90%**

---

## 总评

```
目标 1: 八叉树流式加载     ██████████████░░░░░░  72%
目标 2: 距离→像素→LOD      ████████████████████  95%
目标 3: LOD 级 LRU + 降级  ████████░░░░░░░░░░░░  40% ← 最大短板
目标 4: 最少 LOD 层级       ██████████████████░░  90%
```

**关键发现**

最大的短板是目标 3——目标 2 和目标 4 实现得很好：系统知道该用什么 LOD（目标 2），也知道稳态下只保留最少数据（目标 4）。但当内存不够时（目标 3），缺少"渐进式降低 LOD 质量"的策略，只能粗暴淘汰整个 actor。在内存紧张的设备上，可能出现"相机转头，背后刚被淘汰的 actor 重新加载"的抖动。

**距离卸载的缺失**（目标 1）导致内存充裕的机器永远不触发卸载。当前只有"满载淘汰"安全网，没有"距离卸载"日常管理。已设计八叉树估计卸载方案，利用现有八叉树做节点级批量卸载判定，替代旧的 per-actor 距离遍历。

**建议实现顺序**

---

### P0 ✅：显存预算反馈到 LOD 选级（已完成 — 96cef63d）

`kLodPixelErrorBudget` 从硬编码变动态值。改动小、效果显著——打通目标 2 和目标 3。

---

### P1：八叉树估计卸载（目标 ① 距离卸载缺口）

遍历八叉树节点做空间块级批量卸载，与现有 `query_sphere` 预加载形成对称闭环，与满载淘汰形成"日常+紧急"双层机制。

**Step 1** — `Octree` 新增 `collect_outside_sphere(center, radius, out)`：收集 AABB 完全在球外的所有 payload。递归剪枝——节点完全在球内则跳过整棵子树；完全在球外则收集整棵子树条目；跨边界则递归子节点并逐条目判断。

**Step 2** — Phase 1 收集卸载候选：在现有 `pending_loads` 收集之后，对每个相机调用 `collect_outside_sphere(cam_pos, unload_distance)`，过滤只保留 `Loaded` 状态（排除 Unloaded/Loading/Unloading/pinned/已有 future 的 actor），按距离远者优先排序，限制 8 个/帧。

**Step 3** — Phase 2 应用卸载：持 `unique_lock` 做 TOCTOU 重校验后调用 `on_unload_requested`，复用已有的 `Unloading → remove_cache_async → Unloaded → release_actor_gpu_resources` 链路。

**Step 4**（可选）— LOD 分级卸载距离：查 actor → geometry → `committed_demand`（取 min = 最精细级），LOD0-1 用 2× 卸载距离，LOD2-3 用 1.5×，LOD4+ 用 1×。精模多保留，粗模早卸。

---

### P2：LOD 级 LRU — per-actor 渐进降级（目标 ③ 核心缺口）

当前 `reconcile_lod_residency` 对所有 actor 无差别保留 `{LOD0, demand}` 两级 GPU 缓冲。需求是：VRAM 紧张时，保留近处/重要 actor 的精细 LOD，把远处/次要 actor 强制退到更粗 LOD 或仅 LOD0，**不淘汰整个 actor**（恢复代价从秒级降到毫秒级）。

**Step 1** — 定义 actor 重要度分数：`score = f(屏幕占比, 到相机距离, pinned, 是否在视野中央)`。初版简化为"到最近相机距离"——近者优先保留精细 LOD。

**Step 2** — 在 `reconcile_lod_residency` 尾部加入全局 LOD 预算分配：

```
① 正常算出每个 geometry 的 demand（现有逻辑，不改）
② 汇总所有 geometry 的 {demand, estimated_gpu_bytes_per_level}
③ 估算全部按 demand 构建 GPU 缓冲的总显存量
④ 若总显存 > 软预算（VRAM 容量 × 75%）：
   a. 按 actor 重要度排序（低→高）
   b. 从最不重要 actor 开始，demand += 1（强制更粗一级）
   c. 重新估算总显存，循环直到 ≤ 预算
   d. 若 demand 已是最粗级仍不够 → demand = -1（标记"仅 LOD0"）
⑤ 若总显存 > 硬预算（85%）：标记最不重要 actor 为待淘汰，触发整体卸载
```

**Step 3** — `GeometryResidency` 新增 `lod_budget_cap` 字段（`-1` = 无限制；`≥0` = 强制不超过此级）。`reconcile_lod_residency` 写入 demand 时应用：`demand = max(demand, lod_budget_cap)`。

**Step 4** — 与现有机制的分层水位：

| 水位 | 机制 | 动作 |
|------|------|------|
| < 60% | — | 正常：全部按视觉需求选 LOD |
| 60-75% | **P0** pixel_budget 放宽 | 全场景 LOD 自然变粗（无差别全局降级） |
| 75-85% | **P2** LOD 级 LRU | 远/次要 actor 强制退到更粗 LOD 或仅 LOD0（有选择局部降级） |
| 85-90% | **P2** 尾部 | 最次要 actor 仅 LOD0 |
| > 90% | 已有 `evict_under_memory_pressure` | 硬淘汰整个 actor |

P1（八叉树卸载）在距离维度独立运作——日常清理远处不相关物体，不参与水位分层。

**Step 5** — 与 P1（八叉树卸载）的协同：

| | 八叉树卸载 (P1) | LOD 级 LRU (P2) |
|---|---|---|
| 粒度 | 整个 actor | 单个 LOD 级别 |
| 触发 | 距离 > unload_distance | VRAM > 75% |
| 效果 | actor 从场景消失 | actor 仍在，用更粗模型 |
| 恢复 | 重新 import（秒级） | 从 CPU Scene 重建 GPU 缓冲（毫秒级） |

两者互补：P1 清远处，P2 压近处。

---

### P3：分块流式加载（目标 ① 分块缺口）

八叉树节点作为加载单元，替代当前 per-actor 独立加载。架构改动较大但能显著改善大量小物体的加载性能。

---

### P4：模型重要度分级（锦上添花）

静态标记（主角/敌人/碎石等），替代 P2 中纯距离驱动的重要度排序，使 LOD 预算分配更精准。