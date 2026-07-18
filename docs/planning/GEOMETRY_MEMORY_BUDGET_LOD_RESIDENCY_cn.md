# 几何系统 — 内存/显存预算 + LOD 分级驻留 改造文档

> 文档版本：v1.0
> 关联需求：
> 1. 超大型场景的流式加载，防止内存(RAM)与显存(VRAM)超过上限
> 2. mesh / texture 的 CPU+GPU 内存记账（最主要的占用项）
> 3. 内存/显存满载时按"逐级 LOD 降级"淘汰，而非整 actor 全淘汰
> 4. 不修改 Horizon（除必须的显存容量查询接口）；逻辑尽量收口在 GeometrySystem
>
> 关联文档：[SCENE_OCTREE_CULLING_LRU_TODO_cn.md](SCENE_OCTREE_CULLING_LRU_TODO_cn.md)（八叉树/剔除/Actor 级 LRU）

---

## 进度跟踪（最新）

| 步骤 | 状态 | 备注 |
|---|---|---|
| **Step 0 记账层**（mesh/texture 的 VRAM+RAM 双轨计量）| ✅ 已实现并编译提交 | GPU 用 RAII 令牌精确计量；CPU 用 rid 账本 + 对账 |
| **Step 0b Horizon 显存容量接口** | ✅ 已实现并编译提交 | `query_device_memory_size()` 汇总 DEVICE_LOCAL 堆大小 |
| **Step 0c 满载淘汰（Actor 级）** | ✅ 已实现并编译提交 | 容量=SDL(RAM)+Horizon(VRAM)，90% 触发、降到 80%，冷优先 |
| **Step 1 resolve 硬化** | ✅ 已实现并编译提交 | `select_render_buffers` 选级+句柄拷贝收进单锁，修悬垂指针 ①、再入 ② |
| **Step 2 主渲染路径统一走常驻路由** | ✅ 已实现，待目视验证 | 新增 `resident_render_buffers`；site 1165/2658/2874 全部经路由 + 空缓冲守卫 |
| **Step 3 按需窗口驻留**（让 LOD 真正省显存）| ⏳ 待办 | 停止上传所有级；只驻留当前需要级 ±1；蒙皮跟随常驻集 |
| **Step 4 VRAM 压力接到 LOD 窗口**（Tier1→2→3）| ⏳ 待办 | 淘汰目标从"整 actor"改为"LOD 级"；释放走延迟队列 |
| **Step 5 CPU 级联解耦** | ⏳ 待办 | GPU 降级绝不清 Scene CPU；仅 RAM 压力才 Tier3→4 |

> 已落地文件（Step 0~2）：
> - [include/corona/memory/gpu_mem_ledger.h](../../include/corona/memory/gpu_mem_ledger.h) — `GpuLedger` 单例 + move-only `GpuMemToken` + `system_ram_bytes()`
> - [include/corona/shared_data_hub.h](../../include/corona/shared_data_hub.h) — `MeshDevice` 加 `mesh_mem`/`tex_mem` 令牌（变 move-only）
> - [include/corona/systems/geometry/geometry_system.h](../../include/corona/systems/geometry/geometry_system.h) — `MemoryReport`/`MemoryPoolReport`、`LODMeshBuffers` 加令牌、`resident_render_buffers`/`memory_report`/`set_vram_budget_mb`
> - [src/systems/geometry/geometry_system.cpp](../../src/systems/geometry/geometry_system.cpp) — CPU 账本 + 对账 + 预算报告 + 满载淘汰 + resolve 硬化 + 常驻路由
> - [src/systems/geometry/geometry_mesh_builder.cpp](../../src/systems/geometry/geometry_mesh_builder.cpp) — mesh/texture GPU 令牌插桩
> - Horizon：`horizon.h` + `hardware_context.cpp` + `hardware/resource_manager.{h,cpp}` 的 `query_device_memory_size()` / `device_local_memory_size()`
> - [src/systems/optics/optics_system.cpp](../../src/systems/optics/optics_system.cpp) — 三个渲染站点改走几何缓冲路由

---

## 0. 现状速览（改造前）

| 关注点 | 现状 | 风险 |
|---|---|---|
| VRAM 追踪 | **完全无** | 超大场景必然显存 OOM 且系统无感知 |
| RAM 预算 | `ResourceManager` 用**文件大小**估算，解码膨胀/内嵌纹理(=0)不计 | 预算严重失真 |
| 加载粒度 | 整 actor / 整模型，二元 Loaded/Unloaded | 无中间档，压力下无渐进降级 |
| LOD | 导入期 meshoptimizer 生成；运行时**上传 LOD0+全部级并常驻** | **不省显存，反占 ~2× 基础显存** |
| LOD 选级 | 仅 site 2658(native)/2874(阴影) 生效 | **主 V-buffer 路径(1165)恒 LOD0**，不接 LOD |
| 淘汰 | 不可见 ≥60 帧 → 整 actor evict + 级联清 Scene CPU | 恢复走磁盘重导，抖动代价灾难性 |

### 关键事实（决定方案）
- **mesh/texture 各有 CPU 副本（ResourceManager 拥有，按 rid 共享）+ GPU 副本（geometry 拥有，每实例独立）**。两侧所有者/生命周期不同 → 必须两套记账：CPU 按 rid 去重、GPU 按实例。
- **当前 LOD 是"增显存"的**：meshoptimizer 每级 ~50% 减面，Σ(LOD1..N) ≈ LOD0，故有 LOD 的 mesh 占 ~2× 基础显存。"逐级淘汰"的真正命题是 **LOD 驻留应按需**（只留当前级附近的小窗口），而非全部级常驻。
- **逐级 LOD 远胜整体淘汰**：整体淘汰恢复=磁盘→解析→CPU→GPU(数十ms+assimp)；逐级恢复=CPU Scene→GPU(一次 buffer 创建，ms 级)。**前提：Scene CPU 数据必须留在 RAM**。
- `ResourceManager` 是**被动资源仓库 + parser 集合**，淘汰全由 geometry 编排，即将并入 geometry 线程 → CPU 记账应放进 geometry，不改 RM 内部估算。

---

## 1. 四级驻留模型（替代二元 Loaded/Unloaded）

```
Tier 1  全精度 GPU      ：需要的 LOD（含 LOD0）在显存
Tier 2  降级 GPU        ：只留低 LOD 在显存，释放高精度级（含 LOD0）   ← VRAM 压力降这里
Tier 3  仅 CPU          ：无任何 GPU 缓冲，Scene 仍在 RAM             ← VRAM 极限降这里
Tier 4  仅磁盘          ：Scene 也从 RAM 踢掉（= 现有 evict + 级联）   ← RAM 压力才降这里
```

- 当前系统是 **Tier1 → Tier4 直接跳**（actor evict 同时清 GPU + 级联清 CPU），恢复永远走磁盘。
- 改造补 Tier2/Tier3 两个中间档。
- **VRAM 压力 与 RAM 压力驱动不同降级方向**：
  - VRAM 压力 → 降细节(Tier1→2) → 无 GPU(Tier2→3)，**完全不动 RAM**，恢复极快。
  - RAM 压力 → 只对已在 Tier3 且最冷的物体 Tier3→4（清 Scene CPU = 最后手段）。

---

## 2. 记账层（Step 0，已完成）

### GPU（精确，RAII 自动增减）
- `GpuLedger` 进程级单例（mesh/texture 原子计数 + 峰值），故意泄漏避免静态析构顺序问题。
- move-only `GpuMemToken{kind, bytes}`：构造 `add`、析构 `sub`、移动转移。挂在：
  - `MeshDevice.mesh_mem`/`tex_mem`（覆盖 4 个几何缓冲 + 纹理）
  - `LODMeshBuffers.mesh_mem`（覆盖 LOD1..N）
- 令牌生命周期 = 真实 `HardwareBuffer` 生命周期（`Storage::deallocate` 不析构槽位，释放都发生在 MeshDevice 析构/clear/槽位复用时）→ **账本与显存不漂移**。
- 释放侧零改动，覆盖 `mesh_handles.clear()` / LOD erase / 槽位复用 / Python `~Geometry` 全部路径。

### CPU（按 rid 去重 + 对账存活）
- `cpu_ledger: rid → {kind, bytes}`，键 = Scene 的 model_id 或 Image 的 texture_id。
- 登记：import/build/restore 拿到 Scene 时算 Σ(顶点+索引+LOD) + 遍历材质纹理算解码字节，按 rid 去重。
- 回收：每秒对 `ResourceManager::list_entries()` 存活集合对账，账本中不在存活集的 rid 删除（= 减计）。基于 liveness，无需 hook 淘汰路径。

### 字节公式（geometry 自算，零 Horizon 查询）
```
CPU mesh (per Scene rid): Σ_meshes(V*32 + I*2) + Σ_lod(v*32 + i*2)
CPU tex  (per Image rid): is_compressed ? compressed.size() : W*H*channels
GPU mesh (per MeshDevice/LOD级): 2*(V*32) + 2*(I*2)   // 顶点/索引各普通+storage 两份
GPU tex  (per MeshDevice): W*H*bpp(format)   // SRGBA8=4 / BC3=1 / BC1=0.5
```

---

## 3. 容量与满载淘汰（Step 0b/0c，已完成）

| 池 | 容量（分母） | 用量（分子） |
|---|---|---|
| VRAM | Horizon `query_device_memory_size()` = Σ DEVICE_LOCAL 堆大小（VMA `vmaGetMemoryProperties`，无需 budget 扩展）| 自统计 `gpu_ledger`（mesh+tex）|
| RAM | `SDL_GetSystemRAM()`（窗口创建时取，存入 `Corona::Memory::system_ram_bytes()`）| 自统计 `cpu_ledger`（mesh+tex）|

- geometry **不链接 SDL**：RAM 总量由 UI system 在窗口创建时取得并写入进程级全局，geometry 读取。
- **水位**：high=90%（触发）、low=80%（目标，批量降到此避免抖动）。
- 触发逻辑在 `compute_memory_report()`：`pressured = used ≥ high*cap`，`need_free = used - low*cap`。
- Actor 级淘汰 `evict_under_memory_pressure()`（每 15 帧评测）：冷优先（不可见帧→距离），按 `estimate_actor_memory()` 估算累加到 `need_free` 即停，发 `ActorEvictRequestedEvent` 复用现有快照+延迟释放+级联通路。
- **注**：此 Actor 级淘汰是 Step 4 落地前的安全网；Step 4 后淘汰目标改为 LOD 级。

---

## 4. 渲染路径解耦（Step 1/2，已完成，待验证）

### 目标不变式
1. **LOD 缓存是几何缓冲常驻状态的唯一事实来源**：`levels[i].ready` 表示该级 GPU 缓冲是否常驻，可为 false（被压力释放但 Scene CPU 还在 → 可快速重传）。
2. `MeshDevice` 仍是 LOD0 物理存放处 + texture + material + identity，但**渲染消费者一律不再直接读 MeshDevice 几何缓冲**，全部经统一 resolve/router。
3. resolve/router 返回当前最佳常驻级的**句柄拷贝**（refcount 跨线程安全）；容忍 LOD0 被释放；全级不常驻 → 返回空 → 调用方跳过该 mesh。
4. **GPU 降级只动 GPU + ready 标志，绝不 touch Scene CPU / 级联 evict**。

### 三个硬问题与解法
- **① 裸指针生命周期竞争**：`resolve_lod_buffers` 返回 `const LODMeshBuffers*`，调用方锁外解引用。逐级淘汰使缓存频繁增删后会悬垂。
  → **解法**：选级 + 句柄拷贝收进**同一 shared_lock**，对外只返回 `RenderMeshBuffers` 值拷贝。热路径弃用返回裸指针的接口。
- **② resolve 再入死锁**：渲染站点已持 geom 槽锁，resolve 内不能再 acquire 同槽（同线程递归 shared_lock → UB）。
  → **解法**：保留 `(geom, mesh, …, fallback)` 签名；fallback = 调用方持锁从 MeshDevice 读出的 LOD0 候选。resolve 只锁 `lod_cache_mutex`，无再入。
- **③ 释放时机 data race**：释放 LOD 级时渲染线程可能持其句柄拷贝。
  → **解法（Step 4）**：复用 `pending_gpu_releases` 延迟到下帧 update 头部释放；refcount 保证本帧已拷副本存活到用完。

### 两个 router 的分工
- `select_render_buffers(geom, mesh, **相机入参**, fallback)`：做屏幕占比**选级**。用于有相机的 site 2658(native)/2874(阴影)。
- `resident_render_buffers(geom, mesh, fallback)`：仅**常驻路由**（无相机），从 LOD0 向高精度扫返回最高精度已就绪级。用于无相机的主 V-buffer/拾取路径 site 1165。

> 关键发现：主 V-buffer 路径 `collect_actor_instances_for_visibility` 只有 `camera_basis`（矩阵，拾取路径传 nullptr），无相机位置/fov/包围半径——这正是它历来不接 LOD 的原因。它需要的是"读当前常驻缓冲"而非"按距离选级"，故用无相机的 `resident_render_buffers` 恰好契合。

### 已改造站点
| 站点 | 改造 |
|---|---|
| site 1165（主 V-buffer/拾取）| descriptors + record 改用 `geo_bufs`（经 `resident_render_buffers`）；texture/material 仍从 `m`；加空缓冲跳过守卫 |
| site 2658（native LOD）| 保留 `select_render_buffers`；新增空缓冲守卫 |
| site 2874（阴影）| 保留 `select_render_buffers`；新增空缓冲守卫 |

**行为零变化保证**：今天 LOD0 恒 ready → router 返回 LOD0 = fallback 同批句柄；无缓存条目(from_image) → 原样返回 fallback。画面应完全一致。

---

## 5. 按需窗口驻留（Step 3，待办）— 让 LOD 真正省显存

- `upload_lod_from_scene_data` 不再上传所有级；按"当前需要级 ±1 窗口"上传，窗口外的级 `ready=false`、不建缓冲。
- 新增 `ensure_lod_resident(geom, mesh, level)`：缺失则从 Scene CPU 即时建缓冲（CPU→GPU，ms 级）。resolve 选中级若非常驻 → 触发 ensure，或本帧降级到已常驻级、下帧补上。
- 蒙皮 `update_skinned_geometry` 跟随常驻集：只对 `ready` 的级 write_bytes，LOD0 非常驻则跳过。
- **收益**：显存从 ~2×base 降到 ~窗口级，最大单点收益。
- **窗口策略待定**：纯按需（最省，拉近有一帧延迟）vs 当前级 ±1（跟手、显存略多）。

---

## 6. VRAM 压力接到 LOD 窗口（Step 4，待办）

- 复用 `evict_under_memory_pressure` 评分（冷+大优先），但**淘汰目标改为 LOD 级**：
  - **Tier1→2**：释放高精度级（含 LOD0），保留一个低级。
  - **Tier2→3**：释放该 mesh 全部几何缓冲 **+ texture**（极远物体不渲染），`mesh_handles` 条目保留为空壳，**Scene CPU 不动**。
- 释放走延迟队列（解③）；账本随句柄析构自动扣减。
- BVH 随级释放（释放级时一并释放其三角形 BVH，避免 RAM 尾巴），或改懒建。

---

## 7. CPU 级联解耦（Step 5，待办）

- `on_evict_requested` 当前无条件级联 `try_evict` 底层 Scene/Image（[geometry_system.cpp 第 ~1543 行](../../src/systems/geometry/geometry_system.cpp)）。
- 改为：
  - **GPU 降级路径绝不级联清 CPU**（保护逐级 LOD 的"快速回源"）。
  - 只有**真正 RAM 压力**（cpu_ledger ≥ 90% SDL 总量）才对"已在 Tier3 且最冷"的物体 Tier3→4（清 Scene CPU = 现有级联）。

---

## 8. 后续路线（本文档之外）

| 步骤 | 内容 | 解决差距 |
|---|---|---|
| Native 剔除接入 | 主/阴影循环消费 `visible_actor_handles`（当前仅 Vision 消费）| draw call 不随视锥收敛 |
| 八叉树增量化 | 每帧全量 rebuild + 全量扫 storage → 持久+脏标记增量 | N=数万时 CPU 爆炸 |
| Cell/Tile 流式 | 加载/淘汰以 cell 为单位 | 加载粒度太粗 |
| per-surface 可见集 | 多相机 union → per-camera | 与多 surface 改造冲突 |
| 纹理 mip streaming | 低 mip 常驻、高 mip 按屏占比 | 纹理整张常驻 |

---

## 9. 约束符合性

| 范围 | 触碰情况 |
|---|---|
| Horizon | 仅新增 `query_device_memory_size()`（显存容量查询，VMA 已有数据）；⚠️ 改动在 `build/_deps/horizon-src`，reconfigure 会被冲掉，需提交 Horizon 仓库 + bump GIT_TAG 持久化 |
| geometry system | 主体（记账/淘汰/路由）|
| shared_data_hub.h（引擎侧，非 Horizon）| `MeshDevice` +2 令牌（move-only） |
| optics_system.cpp | 三个渲染站点改走几何缓冲路由 |
| ui system | 窗口创建时 `SDL_GetSystemRAM()` 写入进程级全局 |
| geometry 不链接 SDL | RAM 总量经全局传入 |

---

## 10. 验证要点

- **归零校验**：加载 N 模型 → 账本增长；全卸载 → VRAM/RAM 账本回 ~0（验 RAII 无泄漏、无重复计数）。
- **压力校验**：临时调小容量（或 `set_*_budget` 覆盖）→ 确认 90% 触发、冷物体淘汰、用量回落到 80%。
- **Step 2 渲染回归**：目视确认主画面/阴影/actor 拾取与改动前完全一致（LOD0 恒常驻 → 应零变化）。
- **Step 3/4**：拉远 → 显存下降且画面降级平滑；拉近 → 快速回源（CPU→GPU，非磁盘重导），无抖动。
