from __future__ import annotations

from typing import Any, Iterable, Sequence


def _as_float_list(value: Any, expected: int | None = None) -> list[float] | None:
    try:
        items = [float(x) for x in value]
    except Exception:
        return None
    if expected is not None and len(items) != expected:
        return None
    return items


def _valid_aabb(value: Any) -> list[float] | None:
    aabb = _as_float_list(value, 6)
    if aabb is None:
        return None
    has_extent = False
    for axis in range(3):
        if aabb[axis + 3] < aabb[axis]:
            return None
        if abs(aabb[axis + 3] - aabb[axis]) > 1e-5:
            has_extent = True
    return aabb if has_extent else None


def _actor_local_aabb(actor: Any) -> list[float] | None:
    geom = getattr(actor, "_geometry", None)
    getter = getattr(geom, "get_aabb", None)
    if not callable(getter):
        return None
    try:
        return _valid_aabb(getter())
    except Exception:
        return None


def _actor_vec(actor: Any, getter_name: str, fallback: Sequence[float]) -> list[float]:
    getter = getattr(actor, getter_name, None)
    if callable(getter):
        try:
            value = _as_float_list(getter(), len(fallback))
            if value is not None:
                return value
        except Exception:
            pass
    return [float(x) for x in fallback]


def actor_world_aabb(actor: Any) -> list[float] | None:
    getter = getattr(actor, "get_world_aabb", None)
    if callable(getter):
        try:
            ready = getattr(actor, "bounds_ready", True)
            if ready:
                aabb = _valid_aabb(getter())
                if aabb is not None:
                    return aabb
        except Exception:
            pass
    getter = getattr(actor, "get_aabb", None)
    if callable(getter) and not hasattr(actor, "_geometry"):
        try:
            aabb = _valid_aabb(getter())
            if aabb is not None:
                return aabb
        except Exception:
            pass
    local = _actor_local_aabb(actor)
    if local is None:
        return None
    pos = _actor_vec(actor, "get_position", [0.0, 0.0, 0.0])
    scale = _actor_vec(actor, "get_scale", [1.0, 1.0, 1.0])
    out: list[float] = []
    for axis in range(3):
        a = local[axis] * scale[axis] + pos[axis]
        b = local[axis + 3] * scale[axis] + pos[axis]
        out.append(min(a, b))
    for axis in range(3):
        a = local[axis] * scale[axis] + pos[axis]
        b = local[axis + 3] * scale[axis] + pos[axis]
        out.append(max(a, b))
    return _valid_aabb(out)


def _actor_name(actor: Any) -> str:
    getter = getattr(actor, "get_name", None)
    if callable(getter):
        try:
            return str(getter() or "")
        except Exception:
            pass
    return str(getattr(actor, "name", "") or "")


def _is_infra_name(name: str) -> bool:
    return name.startswith(("__room_", "__interior_", "__terrain_", "__foundation_"))


def _height(aabb: Sequence[float]) -> float:
    return max(0.0, float(aabb[4]) - float(aabb[1]))


def _is_surface_like(name: str, aabb: Sequence[float]) -> bool:
    lname = name.lower()
    if any(k in lname for k in ("rug", "carpet", "floor")):
        return True
    return _height(aabb) <= 0.08


def _overlap_xz(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    return min(float(a[3]), float(b[3])) - max(float(a[0]), float(b[0])), min(float(a[5]), float(b[5])) - max(float(a[2]), float(b[2]))


def _overlap_y(a: Sequence[float], b: Sequence[float]) -> float:
    return min(float(a[4]), float(b[4])) - max(float(a[1]), float(b[1]))


def _translate_aabb(aabb: Sequence[float], dx: float, dz: float) -> list[float]:
    return [float(aabb[0]) + dx, float(aabb[1]), float(aabb[2]) + dz, float(aabb[3]) + dx, float(aabb[4]), float(aabb[5]) + dz]


def _fits_zone(aabb: Sequence[float], zone_aabb: Sequence[float] | None) -> bool:
    if zone_aabb is None:
        return True
    return float(aabb[0]) >= float(zone_aabb[0]) and float(aabb[2]) >= float(zone_aabb[2]) and float(aabb[3]) <= float(zone_aabb[3]) and float(aabb[5]) <= float(zone_aabb[5])


def _clamp_delta_to_zone(aabb: Sequence[float], dx: float, dz: float, zone_aabb: Sequence[float] | None) -> tuple[float, float]:
    if zone_aabb is None:
        return dx, dz
    moved = _translate_aabb(aabb, dx, dz)
    if moved[0] < zone_aabb[0]:
        dx += float(zone_aabb[0]) - float(moved[0])
    if moved[3] > zone_aabb[3]:
        dx -= float(moved[3]) - float(zone_aabb[3])
    moved = _translate_aabb(aabb, dx, dz)
    if moved[2] < zone_aabb[2]:
        dz += float(zone_aabb[2]) - float(moved[2])
    if moved[5] > zone_aabb[5]:
        dz -= float(moved[5]) - float(zone_aabb[5])
    return dx, dz


def _remaining_overlaps(moved: Sequence[float], fixed: Sequence[tuple[str, list[float]]]) -> list[dict[str, Any]]:
    remaining: list[dict[str, Any]] = []
    for other_name, other_aabb in fixed:
        oy = _overlap_y(moved, other_aabb)
        if oy <= 0.0:
            continue
        ox, oz = _overlap_xz(moved, other_aabb)
        if ox > 0.0 and oz > 0.0:
            remaining.append({"actor": other_name, "overlap_x": round(float(ox), 4), "overlap_y": round(float(oy), 4), "overlap_z": round(float(oz), 4)})
    return remaining


def resolve_actor_overlaps(actor: Any, obstacles: Iterable[Any] = (), *, extra_obstacle_aabbs: Iterable[Sequence[float]] = (), zone_aabb: Sequence[float] | None = None, clearance: float = 0.08, max_iterations: int = 16) -> dict[str, Any]:
    name = _actor_name(actor)
    current = actor_world_aabb(actor)
    if current is None:
        return {"changed": False, "reason": "bounds_not_ready", "bounds_ready": False}
    if _is_infra_name(name) or _is_surface_like(name, current):
        return {"changed": False, "reason": "surface_or_infra", "bounds_ready": True}
    fixed: list[tuple[str, list[float]]] = []
    for other in obstacles:
        other_name = _actor_name(other)
        if not other_name or other_name == name or _is_infra_name(other_name):
            continue
        other_aabb = actor_world_aabb(other)
        if other_aabb is None or _is_surface_like(other_name, other_aabb):
            continue
        fixed.append((other_name, other_aabb))
    for idx, aabb in enumerate(extra_obstacle_aabbs):
        valid = _valid_aabb(aabb)
        if valid is not None:
            fixed.append((f"extra_{idx}", valid))
    if not fixed:
        return {"changed": False, "reason": "no_obstacles", "bounds_ready": True}
    total_dx = total_dz = 0.0
    moved = list(current)
    resolved = False
    for _ in range(max(1, int(max_iterations))):
        hit = None
        for other_name, other_aabb in fixed:
            if _overlap_y(moved, other_aabb) <= 0.0:
                continue
            ox, oz = _overlap_xz(moved, other_aabb)
            if ox > 0.0 and oz > 0.0:
                hit = (other_name, other_aabb)
                break
        if hit is None:
            resolved = True
            break
        _, other = hit
        candidates = [(float(other[0]) - float(moved[3]) - clearance, 0.0), (float(other[3]) - float(moved[0]) + clearance, 0.0), (0.0, float(other[2]) - float(moved[5]) - clearance), (0.0, float(other[5]) - float(moved[2]) + clearance)]
        candidates.sort(key=lambda item: abs(item[0]) + abs(item[1]))
        chosen = None
        for dx, dz in candidates:
            cdx, cdz = _clamp_delta_to_zone(moved, dx, dz, zone_aabb)
            candidate_aabb = _translate_aabb(moved, cdx, cdz)
            if _fits_zone(candidate_aabb, zone_aabb):
                chosen = (cdx, cdz)
                break
        if chosen is None:
            chosen = _clamp_delta_to_zone(moved, candidates[0][0], candidates[0][1], zone_aabb)
        total_dx += chosen[0]
        total_dz += chosen[1]
        moved = _translate_aabb(moved, chosen[0], chosen[1])
    remaining = _remaining_overlaps(moved, fixed)
    if abs(total_dx) < 1e-5 and abs(total_dz) < 1e-5:
        return {"changed": False, "reason": "no_delta", "resolved": resolved and not remaining, "remaining_overlap": remaining, "bounds_ready": True}
    pos = _actor_vec(actor, "get_position", [0.0, 0.0, 0.0])
    new_pos = [pos[0] + total_dx, pos[1], pos[2] + total_dz]
    setter = getattr(actor, "set_position", None)
    if callable(setter):
        setter(new_pos)
    return {"changed": True, "position": new_pos, "delta": [total_dx, 0.0, total_dz], "resolved": resolved and not remaining, "remaining_overlap": remaining, "bounds_ready": True}


def compute_ground_snap_position(actor: Any, *, ground_y: float = 0.0, clearance: float = 0.02) -> list[float] | None:
    aabb = actor_world_aabb(actor)
    if aabb is None:
        return None
    pos = _actor_vec(actor, "get_position", [0.0, 0.0, 0.0])
    delta = (float(ground_y) + float(clearance)) - float(aabb[1])
    if abs(delta) < 1e-4:
        return pos
    return [float(pos[0]), float(pos[1]) + delta, float(pos[2])]


def snap_actor_to_ground(actor: Any, *, ground_y: float = 0.0, clearance: float = 0.02) -> list[float] | None:
    corrected = compute_ground_snap_position(actor, ground_y=ground_y, clearance=clearance)
    if corrected is None:
        return None
    setter = getattr(actor, "set_position", None)
    if not callable(setter):
        return None
    setter(corrected)
    return corrected


__all__ = ["actor_world_aabb", "compute_ground_snap_position", "resolve_actor_overlaps", "snap_actor_to_ground"]
