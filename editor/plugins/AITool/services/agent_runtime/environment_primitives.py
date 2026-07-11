"""Small deterministic geometry builders for AgentRuntime environment actors.

These helpers only materialize primitive assets.  They do not plan scenes,
write RuntimeState, or call the engine, so the ToolCallGraph remains the sole
execution coordinator.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class EnvironmentPrimitive:
    model_path: str
    position: list[float]
    scale: list[float]
    semantic_role: str


def build_environment_primitive(
    *,
    component_type: str,
    component_id: str,
    scale: Sequence[float] | None = None,
) -> EnvironmentPrimitive:
    """Build a visible room primitive in a stable temporary asset cache."""

    normalized = str(component_type or "").strip().lower()
    if normalized not in {
        "room_box",
        "room_floor",
        "terrain",
        "ground",
        "boundary",
        "terrain_boundary",
        "sky",
        "skybox",
    }:
        raise ValueError(f"unsupported environment primitive: {component_type}")

    dimensions = _dimensions(normalized, scale)
    cache_key = hashlib.sha256(
        json.dumps(
            {
                "component_type": normalized,
                "component_id": str(component_id or ""),
                "dimensions": dimensions,
                "geometry_version": 1,
            },
            ensure_ascii=True,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:20]
    asset_dir = Path(tempfile.gettempdir()) / "corona_agent_runtime_environment" / cache_key
    asset_dir.mkdir(parents=True, exist_ok=True)
    obj_path = asset_dir / f"{normalized}.obj"
    mtl_path = asset_dir / f"{normalized}.mtl"

    if normalized == "room_box":
        obj_text = _room_shell_obj(mtl_path.name)
        mtl_text = _room_shell_mtl()
        position = [0.0, dimensions[1] / 2.0, 0.0]
        semantic_role = "indoor_enclosure"
    elif normalized in {"room_floor", "terrain", "ground"}:
        obj_text = _floor_slab_obj(mtl_path.name)
        mtl_text = _terrain_mtl() if normalized in {"terrain", "ground"} else _floor_mtl()
        position = [0.0, dimensions[1] / 2.0, 0.0]
        semantic_role = "walkable_floor" if normalized == "room_floor" else "walkable_terrain"
    elif normalized in {"boundary", "terrain_boundary"}:
        obj_text = _boundary_obj(mtl_path.name)
        mtl_text = _boundary_mtl()
        position = [0.0, dimensions[1] / 2.0, 0.0]
        semantic_role = "scene_boundary"
    else:
        obj_text = _sky_shell_obj(mtl_path.name)
        mtl_text = _sky_mtl()
        position = [0.0, dimensions[1] / 2.0, 0.0]
        semantic_role = "sky_context"

    _write_if_changed(obj_path, obj_text)
    _write_if_changed(mtl_path, mtl_text)
    return EnvironmentPrimitive(
        model_path=str(obj_path),
        position=position,
        scale=dimensions,
        semantic_role=semantic_role,
    )


def _dimensions(component_type: str, scale: Sequence[float] | None) -> list[float]:
    defaults_by_type = {
        "room_box": [6.0, 3.0, 6.0],
        "room_floor": [6.0, 0.05, 6.0],
        "terrain": [12.0, 0.05, 12.0],
        "ground": [12.0, 0.05, 12.0],
        "boundary": [12.0, 0.8, 12.0],
        "terrain_boundary": [12.0, 0.8, 12.0],
        "sky": [24.0, 12.0, 24.0],
        "skybox": [24.0, 12.0, 24.0],
    }
    defaults = defaults_by_type[component_type]
    values = list(scale or defaults)
    if len(values) < 3:
        values = defaults
    horizontal_ceiling = 32.0 if component_type in {"sky", "skybox"} else 16.0
    width = min(horizontal_ceiling, max(1.0, float(values[0])))
    if component_type in {"room_box", "sky", "skybox"}:
        height_floor, height_ceiling = 2.2, 20.0
    elif component_type in {"boundary", "terrain_boundary"}:
        height_floor, height_ceiling = 0.2, 2.0
    else:
        height_floor, height_ceiling = 0.02, 0.2
    height = min(height_ceiling, max(height_floor, float(values[1])))
    depth = min(horizontal_ceiling, max(1.0, float(values[2])))
    return [round(width, 4), round(height, 4), round(depth, 4)]


def _write_if_changed(path: Path, content: str) -> None:
    if path.is_file():
        try:
            if path.read_text(encoding="utf-8") == content:
                return
        except OSError:
            pass
    path.write_text(content, encoding="utf-8", newline="\n")


def _room_shell_obj(mtl_name: str) -> str:
    # Open-front shell: back, left, right, and ceiling.  The floor is a
    # separate actor so it can carry walkable semantics and collision later.
    return f"""mtllib {mtl_name}
v -0.5 -0.5 -0.5
v  0.5 -0.5 -0.5
v  0.5  0.5 -0.5
v -0.5  0.5 -0.5
v -0.5 -0.5  0.5
v  0.5 -0.5  0.5
v  0.5  0.5  0.5
v -0.5  0.5  0.5
vn  0.0  0.0  1.0
vn  1.0  0.0  0.0
vn -1.0  0.0  0.0
vn  0.0 -1.0  0.0
usemtl wall
f 1//1 2//1 3//1 4//1
f 1//2 4//2 8//2 5//2
f 2//3 6//3 7//3 3//3
usemtl ceiling
f 4//4 3//4 7//4 8//4
"""


def _floor_slab_obj(mtl_name: str) -> str:
    # A thin closed slab gives the engine a non-zero Y extent and stable AABB.
    return f"""mtllib {mtl_name}
v -0.5 -0.5 -0.5
v  0.5 -0.5 -0.5
v  0.5 -0.5  0.5
v -0.5 -0.5  0.5
v -0.5  0.5 -0.5
v  0.5  0.5 -0.5
v  0.5  0.5  0.5
v -0.5  0.5  0.5
vn 0.0 -1.0 0.0
vn 0.0 1.0 0.0
vn 0.0 0.0 -1.0
vn 0.0 0.0 1.0
vn -1.0 0.0 0.0
vn 1.0 0.0 0.0
usemtl floor
f 1//1 4//1 3//1 2//1
f 5//2 6//2 7//2 8//2
f 1//3 2//3 6//3 5//3
f 4//4 8//4 7//4 3//4
f 1//5 5//5 8//5 4//5
f 2//6 3//6 7//6 6//6
"""


def _boundary_obj(mtl_name: str) -> str:
    return f"""mtllib {mtl_name}
v -0.5 -0.5 -0.5
v  0.5 -0.5 -0.5
v  0.5  0.5 -0.5
v -0.5  0.5 -0.5
v -0.5 -0.5  0.5
v  0.5 -0.5  0.5
v  0.5  0.5  0.5
v -0.5  0.5  0.5
vn 0.0 0.0 1.0
vn 1.0 0.0 0.0
vn -1.0 0.0 0.0
vn 0.0 0.0 -1.0
usemtl boundary
f 1//1 2//1 3//1 4//1
f 1//2 4//2 8//2 5//2
f 2//3 6//3 7//3 3//3
f 5//4 8//4 7//4 6//4
"""


def _sky_shell_obj(mtl_name: str) -> str:
    return _room_shell_obj(mtl_name) + """usemtl sky
f 5//1 8//1 7//1 6//1
"""


def _room_shell_mtl() -> str:
    return """newmtl wall
Ka 0.18 0.18 0.20
Kd 0.72 0.74 0.78
Ks 0.08 0.08 0.08
Ns 12.0
newmtl ceiling
Ka 0.20 0.20 0.21
Kd 0.82 0.82 0.84
Ks 0.05 0.05 0.05
Ns 8.0
"""


def _floor_mtl() -> str:
    return """newmtl floor
Ka 0.16 0.14 0.12
Kd 0.58 0.48 0.38
Ks 0.06 0.06 0.06
Ns 10.0
"""


def _terrain_mtl() -> str:
    return """newmtl floor
Ka 0.10 0.16 0.08
Kd 0.34 0.52 0.28
Ks 0.03 0.03 0.03
Ns 6.0
"""


def _boundary_mtl() -> str:
    return """newmtl boundary
Ka 0.12 0.10 0.08
Kd 0.42 0.32 0.22
Ks 0.04 0.04 0.04
Ns 8.0
"""


def _sky_mtl() -> str:
    return """newmtl wall
Ka 0.30 0.42 0.62
Kd 0.48 0.64 0.88
Ks 0.00 0.00 0.00
Ns 1.0
newmtl ceiling
Ka 0.34 0.46 0.68
Kd 0.52 0.68 0.92
Ks 0.00 0.00 0.00
Ns 1.0
newmtl sky
Ka 0.30 0.42 0.62
Kd 0.48 0.64 0.88
Ks 0.00 0.00 0.00
Ns 1.0
"""
