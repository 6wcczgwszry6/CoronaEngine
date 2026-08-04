"""Shared support-domain semantics for Runtime scene entities.

This classifier only chooses which surface should support an entity. It never
claims that the relationship has been verified; grounding remains an Engine
transform/AABB fact established by import or readiness reconciliation.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


VALID_SUPPORT_TYPES = frozenset({
    "floor_supported",
    "wall_mounted",
    "ceiling_hung",
    "system",
    "unknown",
})

_SYSTEM_PREFIXES = ("__", "_terrain", "terrain", "sky")
_SYSTEM_EXACT_NAMES = frozenset({"ground", "room_box", "room_floor", "room_terrain"})
_SYSTEM_TOKENS = ("地形", "天空", "边界")

_CEILING_TOKENS = (
    "吊灯", "吊旗", "吊笼", "悬挂", "铁链", "天花",
    "ceiling", "chandelier", "hanging", "suspended", "chain", "pendant light",
)

_WALL_TOKENS = (
    "火把", "壁灯", "墙灯", "墙饰", "地图", "旗帜", "窗", "门", "招牌", "武器架",
    "torch", "sconce", "wall lamp", "wall light", "wall_light", "wall-mounted",
    "wall mounted", "map", "flag", "banner", "window", "door", "sign", "weapon rack",
)

_FLOOR_TOKENS = (
    "书桌", "台灯", "落地灯", "衣柜", "书架", "地毯", "藏宝箱", "长椅", "花盆",
    "桌", "椅", "箱", "金币", "木桶", "酒桶", "麻袋", "床", "柜", "雕像",
    "动物", "小狗", "玩偶", "玩具", "帐篷", "篝火", "摊位", "沙发", "植物",
    "table lamp", "desk lamp", "floor lamp", "bookshelf", "bookcase", "wardrobe",
    "cabinet", "table", "desk", "chair", "box", "chest", "coin", "barrel", "sack",
    "bag", "bed", "rug", "carpet", "statue", "animal", "dog", "doll", "toy",
    "bench", "sofa", "tent", "campfire", "stall", "planter", "plant",
)


def classify_support_type(
    values: Any | Iterable[Any],
    *,
    explicit: Any = "",
) -> str:
    """Return a support domain without asserting that support is verified."""

    explicit_value = str(explicit or "").strip().lower()
    if explicit_value in VALID_SUPPORT_TYPES and explicit_value != "unknown":
        return explicit_value

    if isinstance(values, (str, bytes)) or values is None:
        candidates = (values,)
    else:
        try:
            candidates = tuple(values)
        except TypeError:
            candidates = (values,)
    text = " ".join(str(value or "").strip() for value in candidates).strip().lower()
    if not text:
        return "unknown"
    if (
        text.startswith(_SYSTEM_PREFIXES)
        or text in _SYSTEM_EXACT_NAMES
        or any(token in text for token in _SYSTEM_TOKENS)
    ):
        return "system"
    # Mounted-light semantics must win over generic furniture/prop terms.
    if any(token in text for token in _CEILING_TOKENS):
        return "ceiling_hung"
    if any(token in text for token in _WALL_TOKENS):
        return "wall_mounted"
    if any(token in text for token in _FLOOR_TOKENS):
        return "floor_supported"
    return "unknown"
