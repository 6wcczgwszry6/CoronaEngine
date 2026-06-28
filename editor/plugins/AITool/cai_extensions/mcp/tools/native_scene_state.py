from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

CORONA_ENGINE_OVERRIDE: Any | None = None


def _get_corona_engine() -> Any:
    if CORONA_ENGINE_OVERRIDE is not None:
        return CORONA_ENGINE_OVERRIDE
    from CoronaCore.core.corona_editor import CoronaEditor

    return CoronaEditor.CoronaEngine


def _parse_native_json(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        data = json.loads(raw or "{}")
    elif isinstance(raw, dict):
        data = raw
    else:
        raise RuntimeError(f"Native API returned unsupported value: {raw!r}")
    if not isinstance(data, dict):
        raise RuntimeError(f"Native API returned non-object JSON: {data!r}")
    if data.get("status") == "error":
        raise RuntimeError(str(data.get("message") or data.get("error") or "native scene API failed"))
    return data


def _vec3(value: Any, fallback: Sequence[float]) -> list[float]:
    try:
        out = [float(v) for v in value]
    except Exception:
        out = [float(v) for v in fallback]
    while len(out) < 3:
        out.append(float(fallback[len(out)] if len(out) < len(fallback) else 0.0))
    return out[:3]


def _aabb_ready(aabb: Any) -> bool:
    if not isinstance(aabb, (list, tuple)) or len(aabb) < 6:
        return False
    try:
        values = [float(v) for v in aabb[:6]]
    except Exception:
        return False
    has_extent = False
    for axis in range(3):
        min_v = values[axis]
        max_v = values[axis + 3]
        if max_v < min_v:
            return False
        if abs(max_v - min_v) > 1e-5:
            has_extent = True
    return has_extent


def get_native_scene_snapshot(
    scene_name: str = "",
    *,
    wait_for_bounds: bool = False,
    actor_name: str | None = None,
    timeout_s: float = 1.0,
    interval_s: float = 0.05,
) -> dict[str, Any]:
    engine = _get_corona_engine()
    getter = getattr(engine, "get_editor_scene_snapshot", None)
    if not callable(getter):
        raise RuntimeError("Current engine is missing get_editor_scene_snapshot native API")

    deadline = time.monotonic() + max(0.0, float(timeout_s))
    last: dict[str, Any] | None = None
    while True:
        last = _parse_native_json(getter(scene_name or ""))
        if not wait_for_bounds:
            return last
        actors = last.get("actors") if isinstance(last.get("actors"), list) else []
        if actor_name:
            target = find_actor_data(actors, actor_name)
            if target is not None and actor_bounds_ready(target):
                return last
        elif actors and all(actor_bounds_ready(actor) for actor in actors):
            return last
        if time.monotonic() >= deadline:
            return last
        time.sleep(max(0.01, float(interval_s)))


def actor_bounds_ready(actor: dict[str, Any]) -> bool:
    return bool(actor.get("bounds_ready")) and _aabb_ready(actor.get("world_aabb"))


def find_actor_data(actors: Iterable[dict[str, Any]], actor_name: str) -> dict[str, Any] | None:
    wanted = str(actor_name or "")
    wanted_lower = wanted.lower()
    shell_wanted = f"__shell_{wanted}" if not wanted.startswith("__shell_") else wanted
    for actor in actors:
        names = {
            str(actor.get("name") or ""),
            str(actor.get("actor_guid") or ""),
            str(actor.get("handle") or ""),
        }
        if wanted in names or shell_wanted in names:
            return actor
        if wanted_lower and any(name.lower() == wanted_lower for name in names if name):
            return actor
    return None


def native_scene_actors(scene_name: str = "", *, wait_for_bounds: bool = False) -> list[dict[str, Any]]:
    snapshot = get_native_scene_snapshot(scene_name, wait_for_bounds=wait_for_bounds)
    actors = snapshot.get("actors")
    return list(actors) if isinstance(actors, list) else []


@dataclass
class NativeActorView:
    data: dict[str, Any]
    scene_name: str = ""

    @property
    def name(self) -> str:
        return str(self.data.get("name") or "")

    @property
    def actor_type(self) -> str:
        return str(self.data.get("actor_type") or self.data.get("type") or "unknown")

    @property
    def model_path(self) -> str:
        return str(self.data.get("route") or self.data.get("path") or self.data.get("model") or "")

    @property
    def bounds_ready(self) -> bool:
        return actor_bounds_ready(self.data)

    def refresh(self) -> None:
        updated = find_native_actor(self.scene_name, self.name)
        if updated is not None:
            self.data = updated.data

    def get_name(self) -> str:
        return self.name

    def get_position(self) -> list[float]:
        return _vec3((self.data.get("geometry") or {}).get("position"), [0.0, 0.0, 0.0])

    def get_rotation(self) -> list[float]:
        return _vec3((self.data.get("geometry") or {}).get("rotation"), [0.0, 0.0, 0.0])

    def get_scale(self) -> list[float]:
        return _vec3((self.data.get("geometry") or {}).get("scale"), [1.0, 1.0, 1.0])

    def set_position(self, value: Sequence[float]) -> None:
        result = set_native_actor_transform(self.scene_name, self.name, position=list(value))
        actor = result.get("actor") if isinstance(result.get("actor"), dict) else None
        if actor:
            self.data = actor

    def set_rotation(self, value: Sequence[float]) -> None:
        result = set_native_actor_transform(self.scene_name, self.name, rotation=list(value))
        actor = result.get("actor") if isinstance(result.get("actor"), dict) else None
        if actor:
            self.data = actor

    def set_scale(self, value: Sequence[float]) -> None:
        result = set_native_actor_transform(self.scene_name, self.name, scale=list(value))
        actor = result.get("actor") if isinstance(result.get("actor"), dict) else None
        if actor:
            self.data = actor

    def get_world_aabb(self) -> list[float]:
        if not self.bounds_ready:
            raise RuntimeError(f"Native bounds are not ready for actor {self.name!r}")
        return [float(v) for v in self.data.get("world_aabb", [])[:6]]

    def get_aabb(self) -> list[float]:
        return self.get_world_aabb() if self.bounds_ready else []

    def get_bounding_box(self) -> list[float]:
        return self.get_aabb()


def native_actor_views(scene_name: str = "", *, wait_for_bounds: bool = False) -> list[NativeActorView]:
    snapshot = get_native_scene_snapshot(scene_name, wait_for_bounds=wait_for_bounds)
    scene = str(snapshot.get("scene") or scene_name or "")
    actors = snapshot.get("actors") if isinstance(snapshot.get("actors"), list) else []
    return [NativeActorView(dict(actor), scene) for actor in actors if isinstance(actor, dict)]


def find_native_actor(
    scene_name: str,
    actor_name: str,
    *,
    wait_for_bounds: bool = False,
    timeout_s: float = 1.0,
    interval_s: float = 0.05,
) -> NativeActorView | None:
    snapshot = get_native_scene_snapshot(
        scene_name,
        wait_for_bounds=wait_for_bounds,
        actor_name=actor_name if wait_for_bounds else None,
        timeout_s=timeout_s,
        interval_s=interval_s,
    )
    actors = snapshot.get("actors") if isinstance(snapshot.get("actors"), list) else []
    actor = find_actor_data([a for a in actors if isinstance(a, dict)], actor_name)
    if actor is None:
        return None
    return NativeActorView(dict(actor), str(snapshot.get("scene") or scene_name or ""))


def set_native_actor_transform(
    scene_name: str,
    actor_name: str,
    *,
    position: Sequence[float] | None = None,
    rotation: Sequence[float] | None = None,
    scale: Sequence[float] | None = None,
) -> dict[str, Any]:
    transform: dict[str, Any] = {"geometry": {}}
    if position is not None:
        transform["geometry"]["position"] = [float(v) for v in position[:3]]
    if rotation is not None:
        transform["geometry"]["rotation"] = [float(v) for v in rotation[:3]]
    if scale is not None:
        transform["geometry"]["scale"] = [float(v) for v in scale[:3]]
    if not transform["geometry"]:
        raise ValueError("position, rotation, or scale is required")

    engine = _get_corona_engine()
    setter = getattr(engine, "set_editor_actor_transform", None)
    if not callable(setter):
        raise RuntimeError("Current engine is missing set_editor_actor_transform native API")
    result = _parse_native_json(setter(scene_name or "", actor_name, json.dumps(transform, ensure_ascii=False)))
    _emit_scene_tree_changed(str(result.get("scene") or scene_name or ""))
    return result


def _emit_scene_tree_changed(scene_name: str) -> None:
    try:
        from CoronaCore.core.corona_editor import CoronaEditor

        CoronaEditor.emit_editor_event("scene-tree-changed", [scene_name])
    except Exception:
        pass


def wait_for_actor_bounds(
    scene_name: str,
    actor_name: str,
    *,
    timeout_s: float = 1.0,
    interval_s: float = 0.05,
) -> NativeActorView | None:
    return find_native_actor(
        scene_name,
        actor_name,
        wait_for_bounds=True,
        timeout_s=timeout_s,
        interval_s=interval_s,
    ) if timeout_s >= 0 else find_native_actor(scene_name, actor_name)


__all__ = [
    "NativeActorView",
    "actor_bounds_ready",
    "find_native_actor",
    "get_native_scene_snapshot",
    "native_actor_views",
    "native_scene_actors",
    "set_native_actor_transform",
    "wait_for_actor_bounds",
]
