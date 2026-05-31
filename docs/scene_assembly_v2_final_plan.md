# 场景组装最终方案：关系驱动 + 几何求解 + VLM 优先修正

> 2026-06-01 | 基于 20+ 轮测试 + C 老师架构评审

---

## 核心原则

```
1. 不依赖引擎 AABB — trimesh 读文件 bbox
2. 不依赖 LLM 坐标 — LLM 输出语义关系, 代码算坐标
3. 不依赖 VLM 一定输出坐标 — corrections 优先, rule fallback
4. 不依赖物理沉降解决布局 — 保留为兜底处理引擎误差
5. 所有空间关系最终落到代码规则
```

---

## 一、总链路

```
Prompt
  ↓
collect_models (模型收集)
  ↓
Asset Metadata Builder (trimesh 读 bbox → metadata.json)
  ↓
Role & Relation Parser (LLM 输出语义关系)
  ↓
Tier1: Boundary-Anchor Placement (大件靠墙/居中)
  ↓
Tier2: Relation Solver Placement (从属在锚点附近)
  ↓
Tier3: Decoration Rule Placement (装饰绑定规则)
  ↓
Deterministic Polish (Relative Scale + Bottom Align)
  ↓
Engine Import
  ↓
VLM Review
  ├─ Corrections → apply (优先)
  ├─ Rule Correction → apply (fallback)
  └─ Physics Settlement → apply (最后兜底)
  ↓
Output
```

---

## 二、模块规格

### 1. Asset Metadata Builder (P0)

```python
def build_asset_metadata(model_path: str) -> dict:
    """trimesh 读 glb/obj, 返回 bbox + 推荐 placement_type"""
    import trimesh
    mesh = trimesh.load(model_path, force='mesh')
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    
    bmin = mesh.bounds[0]
    bmax = mesh.bounds[1]
    size = bmax - bmin
    
    return {
        "bbox_min": bmin.tolist(),
        "bbox_max": bmax.tolist(),
        "size": size.tolist(),
        "height": float(size[1]),
        "origin_y_offset": float(-bmin[1]),  # 原点→底部偏移
        "placement_type": _infer_placement_type(bmin, bmax),
    }

def _infer_placement_type(name: str, bmin, bmax) -> str:
    """从模型名+类别优先, bbox 兜底。
    
    Hunyuan3D 尺度异常会反向污染纯 bbox 分类,
    台灯 0.96m 高会被误判为 large_anchor。
    """
    h = bmax[1] - bmin[1]
    w = bmax[0] - bmin[0]
    d = bmax[2] - bmin[2]
    
    # 1) 模型名/类别优先
    name_kw = name.lower()
    if any(k in name_kw for k in ["地毯", "rug", "carpet"]):     return "floor_surface"
    if any(k in name_kw for k in ["台灯", "table_lamp"]):         return "on_surface"
    if any(k in name_kw for k in ["落地灯", "floor_lamp"]):       return "near_anchor"
    if any(k in name_kw for k in ["挂画", "窗帘", "painting"]):    return "against_wall"
    if any(k in name_kw for k in ["摆件", "花瓶", "靠垫"]):        return "on_surface"
    if any(k in name_kw for k in ["绿植", "盆栽", "plant"]):      return "near_wall"
    
    # 2) bbox 兜底
    if h < 0.03 and max(w, d) > 0.5:  return "floor_surface"
    if h < 0.3 and w < 0.5:            return "on_surface"
    if h > 0.8 and w < 0.5:            return "near_anchor"
    if h < 0.05 and w > 0.5:           return "against_wall"
    return "large_anchor"
```

### 2. Relative Scale Normalizer (P1)

```
规则:
  table_lamp:    height = support_height × 0.6
  floor_lamp:    height = anchor_height × 1.5
  rug:           width = group_width × 1.25, depth = group_depth × 1.25
  nightstand:    height = bed_height × 0.6
  decoration:    height = support_height × 0.3
  tv_stand:      若 height < 0.3m → scale_y 放大至 0.45-0.6m
                 仅当模型名含"悬空/壁挂"时才 wall_mount
                 否则按 large_anchor 落地处理
  
有 bbox → 反推 scale: target_height / raw_height
无 bbox → DEFAULT_SCALES 表 fallback
异常值 → clamp [0.1, 3.0]
```

### 3. Constraint Solver (P0)

```python
RELATIONS = {
    "on_surface":       (obj, tgt) → tgt.center_xz + tgt.top_y,
    "near_anchor":      (obj, anchor, side, dist) → anchor.side(side) + dist,
    "against_wall":     (obj, wall, offset) → wall.pos + offset,
    "in_front":         (obj, anchor, dist) → anchor.front(dist),
    "center_under_group": (obj, group) → group.center_xz + y=0.01,
    "between":          (obj, a, b) → midpoint(a, b),
}
```

### 4. Correction Pipeline (P1)

```python
def apply_corrections(review_result, scene):
    # 1) VLM corrections 优先 — 但必须经过 solver 校验
    corrections = review_result.get("corrections", [])
    for c in corrections:
        if not validate_object_id(c["object_id"]):   continue
        if not validate_bbox_bounds(c, scene):        continue
        if not validate_relation_invariant(c, scene): continue
        # 例: table_lamp 不能被移到地上, rug 不能被移到桌面高度
        execute_correction(c)
    
    # 2) Rule-based fallback
    for pa in review_result.get("problem_actors", []):
        rule = RULE_MAP.get(pa["issue"])
        if rule:
            rule(pa["actor"], pa.get("target"), scene)
    
    # 3) Physics last resort
    apply_physics_settlement(scene)
```

---

## 三、Tier 职责调整

| Tier | 旧职责 | 新职责 |
|------|--------|--------|
| Tier1 | o3-mini 输出坐标 | LLM 输出边界关系 (against_wall/center_in_zone) |
| Tier2 | gpt-5.5 输出锚点JSON | LLM 输出语义关系 (near_anchor/on_surface/in_front) |
| Tier3 | gpt-5.5 输出坐标 | LLM 输出绑定规则 (center_under_group/near_wall) |

---

## 四、保留 & 新增 & 删除

### 保留
- 三层 DAG + condition routing
- VLM 审查 (GPT-5.5, 8角度)
- Corrections 优先执行
- 物理沉降 (兜底)
- 挂墙修正 (融入 solver)
- _check_overlap (碰撞检测)
- _validate_positions (边界校验)

### 新增
- Asset Metadata Builder (trimesh → bbox)
- Relative Scale Normalizer (ratio-based)
- Constraint Solver (6 relations)
- Rule Correction Fallback (issue→action map)

### 删除
- place_object_near 工具 (已替换为 _calculate_semantic_position)
- _DEFAULT_SCALES 表 (替换为 Relative Scale Normalizer, 保留为 fallback)
- o3-mini 输出坐标 (改为输出关系)

---

## 五、实施路线

### Week 1: 基础闭环

| 天 | 任务 | 验收 |
|----|------|------|
| Day 1 | Asset Metadata Builder + 缓存 | 3个模型 bbox 正确 |
| Day 2 | Constraint Solver 6关系 | 单元测试通过 |
| Day 3 | Tier1 prompt → relation | LLM 输出合法关系 |
| Day 4 | Relative Scale Normalizer | 台灯/地毯/落地灯 scale 合理 |
| Day 5 | 全链路联调, 跑3次 | 坐标由 solver 产出 |

### Week 2: 修正闭环

| 天 | 任务 | 验收 |
|----|------|------|
| Day 1 | Rule Correction Fallback | issue→action 映射正确 |
| Day 2 | Tier3 绑定规则 | 地毯不再随机放 |
| Day 3 | 全链路联调, 跑5次 | corrections + rule 都触发 |
| Day 4 | 日志+统计 | 评分趋势、retry 次数 |
| Day 5 | Code Review + 清理 | 移除废弃代码 |

---

## 六、验收标准

```
□ 不调用 get_world_aabb()
□ Tier1/Tier2/Tier3 LLM 不输出坐标
□ 台灯 scale 反推自真实 bbox
□ 地毯位于沙发茶几组下方
□ 落地灯在 anchor 侧 0.3m
□ VLM corrections 优先执行
□ Rule correction fallback 触发日志可见
□ 重复 retry 0 个副本
□ 平均评分 ≥ 75
□ relation satisfaction ≥ 90% (语义关系被正确求解)
□ scale anomaly ≤ 1 / scene (异常 scale 数量)
□ floating / severe penetration = 0 (悬空/严重穿模)
```
