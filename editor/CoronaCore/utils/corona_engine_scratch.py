# -*- coding: utf-8 -*-
"""
CoronaEngine Scratch 兼容层。

Blockly 生成的代码仍然按旧方式导入本模块：
    from CoronaCore.utils import corona_engine_scratch as CoronaEngine

运行时状态不再是模块级单例，而是绑定到当前脚本线程的
ScratchRuntimeContext。这样项目预览可以同时运行项目全局脚本和多个
Actor 脚本，而不会互相覆盖目标 Actor、变量或输入处理器。
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import json as _json
import logging
import os as _os
from pathlib import Path as _Path
import random as _random
import threading as _threading
import time as _time
from typing import Callable, Optional

_logger = logging.getLogger(__name__)

_engine_lock = _threading.Lock()
_context_lock = _threading.RLock()
_tls = _threading.local()
_run_count = 0


@dataclass
class ScratchRuntimeContext:
    context_id: str
    target_type: str = "actor"  # actor | project | internal
    scene_name: str = ""
    actor_name: str = ""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rot_x: float = 0.0
    rot_y: float = 0.0
    rot_z: float = 0.0
    size_val: float = 100.0
    cartoon_index: int = 0
    visible: bool = True
    variables: dict = field(default_factory=dict)
    last_touch_object: str = ""
    deleted_objects: set = field(default_factory=set)
    object_tags: dict = field(default_factory=dict)
    virtual_objects: dict = field(default_factory=dict)
    game_state: str = ""
    gravity_enabled: bool = False
    gravity_strength: float = 9.8
    last_physics_time: float = 0.0
    countdown_end_time: float = 0.0
    last_loop_yield_time: float = 0.0

    target_scene_name: Optional[str] = None
    target_actor_name: Optional[str] = None
    target_scene: object = None
    target_actor: object = None

    geometry: object = None
    optics: object = None
    kinematics: object = None
    mechanics: object = None
    actor: object = None
    scene: object = None
    initialized: bool = False
    external_target: bool = False

    stop_requested: bool = False
    key_state: dict = field(default_factory=dict)
    mouse_pressed: bool = False
    mouse_x: float = 0.0
    mouse_y: float = 0.0
    mouse_delta_x: float = 0.0
    mouse_delta_y: float = 0.0
    mouse_viewport_x: float = 0.0
    mouse_viewport_y: float = 0.0
    mouse_viewport_width: float = 0.0
    mouse_viewport_height: float = 0.0
    last_mouse_pick_object: str = ""
    key_handler: Optional[Callable] = None
    mouse_handler: Optional[Callable] = None
    broadcast_handlers: dict = field(default_factory=dict)
    clone_start_handler: Optional[Callable] = None
    current_clone_name: str = ""
    visible_variables: set = field(default_factory=set)
    visible_lists: set = field(default_factory=set)
    list_values: dict = field(default_factory=dict)
    mouse_locked: bool = False
    alpha: float = 1.0
    binding_error: str = ""
    current_node_id: str = ""
    current_node_name: str = ""
    waiting_edge_id: str = ""
    waiting_edge_name: str = ""
    countdown_started_at: float = 0.0
    countdown_duration: float = 0.0
    touch_state: dict = field(default_factory=dict)
    crossing_state: dict = field(default_factory=dict)
    last_collision_axis_value: str = ""
    last_collision_normal_value: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    last_collision_target_name: str = ""
    previous_actor_positions: dict = field(default_factory=dict)
    tag_velocity_times: dict = field(default_factory=dict)
    checkpoints: dict = field(default_factory=dict)
    cooldowns: dict = field(default_factory=dict)
    initial_tag_transforms: dict = field(default_factory=dict)


_default_context = ScratchRuntimeContext("default", target_type="internal")
_contexts: dict[str, ScratchRuntimeContext] = {"default": _default_context}
_completed_state_snapshots: dict[str, dict] = {}
_scene_virtual_objects: dict[str, dict[str, object]] = {}
_scene_deleted_objects: dict[str, set[str]] = {}
_scene_object_tags: dict[str, dict[str, str]] = {}
_scene_shared_variables: dict[str, dict[str, object]] = {}
_scene_shared_lists: dict[str, dict[str, list]] = {}
_scene_shared_declarations: dict[str, dict[str, tuple]] = {}
_scene_logical_collision_enabled: dict[str, dict[str, bool]] = {}
_clone_threads: dict[str, list[_threading.Thread]] = {}
_handler_threads: dict[str, list[_threading.Thread]] = {}


def _current_context() -> ScratchRuntimeContext:
    ctx = getattr(_tls, "ctx", None)
    return ctx if ctx is not None else _default_context


def create_context(
    context_id: str | None = None,
    target_type: str = "actor",
    scene_name: str = "",
    actor_name: str = "",
) -> ScratchRuntimeContext:
    if not context_id:
        context_id = f"scratch-{_threading.get_ident()}-{int(_time.time() * 1000)}"
    ctx = ScratchRuntimeContext(
        context_id=context_id,
        target_type="actor" if (target_type or "actor") == "model" else (target_type or "actor"),
        scene_name=scene_name or "",
        actor_name=actor_name or "",
    )
    if ctx.target_type == "project":
        ctx.initialized = True
    elif ctx.scene_name and ctx.actor_name:
        ctx.target_scene_name = ctx.scene_name
        ctx.target_actor_name = ctx.actor_name
        ctx.external_target = True
    with _context_lock:
        _contexts[ctx.context_id] = ctx
        _completed_state_snapshots.pop(ctx.context_id, None)
    return ctx


def bind_context(ctx: ScratchRuntimeContext):
    _tls.ctx = ctx
    with _context_lock:
        _contexts[ctx.context_id] = ctx
    return ctx


def release_context(ctx: ScratchRuntimeContext | None = None):
    if ctx is None:
        ctx = getattr(_tls, "ctx", None)
    if ctx is not None and ctx.context_id != "default":
        if ctx.game_state or ctx.variables.get('game_state'):
            with _context_lock:
                _completed_state_snapshots[ctx.context_id] = runtime_state_snapshot(ctx)
        ctx.key_handler = None
        ctx.mouse_handler = None
        ctx.broadcast_handlers.clear()
        ctx.clone_start_handler = None
        globals().get('_velocity_cache', {}).pop(ctx.context_id, None)
        globals().get('_raycast_cache', {}).pop(ctx.context_id, None)
        globals().get('_native_velocity_contexts', set()).discard(ctx.context_id)
        globals().get('_native_gravity_contexts', set()).discard(ctx.context_id)
        ctx.virtual_objects.clear()
        ctx.deleted_objects.clear()
        ctx.object_tags.clear()
        ctx.visible_variables.clear()
        ctx.visible_lists.clear()
        ctx.list_values.clear()
        ctx.touch_state.clear()
        ctx.crossing_state.clear()
        ctx.last_collision_axis_value = ""
        ctx.last_collision_normal_value = [0.0, 0.0, 0.0]
        ctx.last_collision_target_name = ""
        ctx.previous_actor_positions.clear()
        ctx.tag_velocity_times.clear()
        ctx.last_mouse_pick_object = ""
        ctx.checkpoints.clear()
        ctx.cooldowns.clear()
        ctx.initial_tag_transforms.clear()
        with _context_lock:
            _contexts.pop(ctx.context_id, None)
            _clone_threads[ctx.context_id] = [
                thread for thread in _clone_threads.get(ctx.context_id, []) if thread.is_alive()
            ]
            if not _clone_threads.get(ctx.context_id):
                _clone_threads.pop(ctx.context_id, None)
            _handler_threads[ctx.context_id] = [
                thread for thread in _handler_threads.get(ctx.context_id, []) if thread.is_alive()
            ]
            if not _handler_threads.get(ctx.context_id):
                _handler_threads.pop(ctx.context_id, None)
    if getattr(_tls, "ctx", None) is ctx:
        _tls.ctx = None


@contextmanager
def using_context(ctx: ScratchRuntimeContext):
    previous = getattr(_tls, "ctx", None)
    _tls.ctx = ctx
    try:
        yield ctx
    finally:
        _tls.ctx = previous


def _live_contexts() -> list[ScratchRuntimeContext]:
    with _context_lock:
        return [ctx for ctx in _contexts.values() if ctx.context_id != "default"]


def register_key_handler(handler):
    ctx = _current_context()
    ctx.key_handler = handler
    _logger.debug("[ScratchWrapper] key handler registered: %s", getattr(handler, "__name__", None))


def unregister_key_handler():
    _current_context().key_handler = None


def register_mouse_handler(handler):
    _current_context().mouse_handler = handler


def unregister_mouse_handler():
    _current_context().mouse_handler = None


def register_broadcast_handler(message, handler):
    if not callable(handler):
        return False
    key = str(message or "")
    ctx = _current_context()
    ctx.broadcast_handlers.setdefault(key, []).append(handler)
    return True


def unregister_broadcast_handlers():
    _current_context().broadcast_handlers.clear()


def register_clone_start_handler(handler):
    if not callable(handler):
        return False
    _current_context().clone_start_handler = handler
    return True


def has_runtime_handlers(ctx=None):
    ctx = ctx or _current_context()
    return bool(
        ctx.key_handler is not None
        or ctx.mouse_handler is not None
        or ctx.clone_start_handler is not None
        or any(ctx.broadcast_handlers.values())
    )


def handle_key_event(key, mods=None, display_key=None):
    if display_key is None:
        display_key = key
    keys_to_set = {key, display_key}
    if len(display_key) == 1:
        keys_to_set.add(display_key.lower())
        keys_to_set.add(display_key.upper())
    for ctx in _live_contexts() or [_default_context]:
        for item in keys_to_set:
            ctx.key_state[item] = True
        if ctx.key_handler is None or ctx.stop_requested:
            continue
        try:
            with using_context(ctx):
                ctx.key_handler(key, mods or [])
        except SystemExit:
            ctx.stop_requested = True
        except Exception as exc:
            _logger.warning("[ScratchWrapper] key handler error: %s", exc)


def handle_key_release(key, display_key=None):
    for ctx in _live_contexts() or [_default_context]:
        ctx.key_state[key] = False
        if display_key:
            ctx.key_state[display_key] = False
            if len(display_key) == 1:
                ctx.key_state[display_key.lower()] = False
                ctx.key_state[display_key.upper()] = False


def handle_mouse_event(event_type, button, x, y, viewport_x=None, viewport_y=None, viewport_width=None, viewport_height=None):
    for ctx in _live_contexts() or [_default_context]:
        if event_type in ("click", "mousedown"):
            ctx.mouse_pressed = True
        elif event_type == "mouseup":
            ctx.mouse_pressed = False
        next_x = float(x)
        next_y = float(y)
        ctx.mouse_delta_x = next_x - ctx.mouse_x
        ctx.mouse_delta_y = next_y - ctx.mouse_y
        ctx.mouse_x = next_x
        ctx.mouse_y = next_y
        ctx.mouse_viewport_x = float(next_x if viewport_x is None else viewport_x)
        ctx.mouse_viewport_y = float(next_y if viewport_y is None else viewport_y)
        ctx.mouse_viewport_width = max(0.0, float(viewport_width or 0.0))
        ctx.mouse_viewport_height = max(0.0, float(viewport_height or 0.0))
        if ctx.mouse_handler is None or ctx.stop_requested:
            continue
        try:
            with using_context(ctx):
                ctx.mouse_handler(event_type, button, x, y)
        except SystemExit:
            ctx.stop_requested = True
        except Exception as exc:
            _logger.warning("[ScratchWrapper] mouse handler error: %s", exc)


def set_target(scene_name: str, actor_name: str):
    ctx = _current_context()
    ctx.target_type = "actor"
    ctx.scene_name = scene_name or ""
    ctx.actor_name = actor_name or ""
    ctx.target_scene_name = scene_name
    ctx.target_actor_name = actor_name
    ctx.external_target = True
    ctx.initialized = False
    _logger.debug("[ScratchWrapper] set_target: scene=%s actor=%s", scene_name, actor_name)


def set_project_global():
    ctx = _current_context()
    ctx.target_type = "project"
    ctx.external_target = False
    ctx.initialized = True


def _actor_only(api_name: str) -> bool:
    ctx = _current_context()
    if ctx.target_type == "project":
        _logger.warning("[ScratchWrapper] %s ignored in project-global script", api_name)
        return True
    return False


def _target_token(value):
    text = str(value or "").strip().replace("\\", "/")
    return text.casefold()


def _target_variants(value):
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return set()
    path = _Path(text)
    values = {text, path.name, path.stem}
    return {_target_token(item) for item in values if item}


def _scene_matches(key, scene, requested):
    requested_values = _target_variants(requested)
    if not requested_values:
        return False
    candidates = {key, getattr(scene, "route", ""), getattr(scene, "name", "")}
    return any(_target_variants(candidate) & requested_values for candidate in candidates if candidate)


def _actor_matches(actor, requested):
    requested_values = _target_variants(requested)
    if not requested_values:
        return False
    candidates = {
        getattr(actor, "name", ""),
        getattr(actor, "route", ""),
        getattr(actor, "path", ""),
        getattr(actor, "actor_guid", ""),
        str(getattr(actor, "handle", "") or ""),
    }
    return any(_target_variants(candidate) & requested_values for candidate in candidates if candidate)



def _native_payload(value):
    if isinstance(value, str):
        try:
            value = _json.loads(value)
        except Exception:
            return None
    if not isinstance(value, dict):
        return None
    if value.get("success") is False or value.get("status") == "error":
        return None
    data = value.get("data") if isinstance(value.get("data"), dict) else value
    return data


def _native_payload_or_raise(value, action):
    """Validate a native editor result without discarding its error message."""
    raw = value
    if isinstance(raw, str):
        try:
            raw = _json.loads(raw)
        except Exception as exc:
            raise RuntimeError(f"{action} returned invalid data: {raw}") from exc
    if not isinstance(raw, dict):
        raise RuntimeError(f"{action} returned no valid result")
    if raw.get("success") is False or raw.get("status") == "error":
        message = raw.get("message") or raw.get("error") or "native interface failed"
        raise RuntimeError(f"{action} failed: {message}")
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    return data


def _native_actor_matches(data, requested):
    requested_values = _target_variants(requested)
    if not requested_values or not isinstance(data, dict):
        return False
    candidates = {
        data.get("name", ""), data.get("route", ""), data.get("path", ""),
        data.get("actor_guid", ""), str(data.get("handle", "") or ""),
    }
    return any(_target_variants(value) & requested_values for value in candidates if value)


def _native_scene_matches(data, requested):
    requested_values = _target_variants(requested)
    if not requested_values or not isinstance(data, dict):
        return False
    candidates = {
        data.get("scene", ""), data.get("scene_name", ""), data.get("name", ""),
        data.get("id", ""), data.get("scene_id", ""), data.get("route", ""),
    }
    return any(_target_variants(value) & requested_values for value in candidates if value)


def _native_scene_snapshot(scene_name):
    errors = []
    try:
        from CoronaCore.core.corona_editor import CoronaEditor
        engine = CoronaEditor.CoronaEngine
        getter = getattr(engine, "get_editor_scene_snapshot", None) if engine is not None else None
        if callable(getter):
            payload = _native_payload(getter(scene_name or ""))
            if payload is not None:
                return payload, errors
    except Exception as exc:
        errors.append(str(exc))
    try:
        from CoronaCore.core.editor_api import CoronaEditorApi
        payload = _native_payload(CoronaEditorApi.scene_datas.get_scene(scene_name or ""))
        if payload is not None:
            if "scene" not in payload:
                payload["scene"] = payload.get("scene_id") or payload.get("id") or scene_name
            if "scene_name" not in payload:
                payload["scene_name"] = payload.get("name") or ""
            return payload, errors
    except Exception as exc:
        errors.append(str(exc))
    return None, errors


class _NativeEditorActorProxy:
    def __init__(self, scene, data):
        self.scene = scene
        self.scene_route = scene.route
        self._data = dict(data or {})
        self.name = str(self._data.get("name") or self._data.get("route") or "")
        self.route = str(self._data.get("route") or self._data.get("path") or self.name)
        self.path = self.route
        self.actor_guid = str(self._data.get("actor_guid") or "")
        self.handle = self._data.get("handle")
        self.actor_type = str(self._data.get("actor_type") or self._data.get("type") or "model")
        geometry = self._data.get("geometry") if isinstance(self._data.get("geometry"), dict) else {}
        self._position = list(geometry.get("position") or [0.0, 0.0, 0.0])[:3]
        self._rotation = list(geometry.get("rotation") or [0.0, 0.0, 0.0])[:3]
        self._scale = list(geometry.get("scale") or [1.0, 1.0, 1.0])[:3]
        while len(self._position) < 3: self._position.append(0.0)
        while len(self._rotation) < 3: self._rotation.append(0.0)
        while len(self._scale) < 3: self._scale.append(1.0)
        self._visible = bool(self._data.get("visible", True))
        self._aabb = self._data.get("world_aabb") or self._data.get("aabb")
        mechanics = self._data.get("mechanics") if isinstance(self._data.get("mechanics"), dict) else {}
        self._mass = float(mechanics.get("mass", 1.0) or 1.0)
        self._restitution = float(mechanics.get("restitution", 0.8) or 0.0)
        self._damping = float(mechanics.get("damping", 0.99) or 0.0)
        self._physics_enabled = bool(mechanics.get("physics_enabled", False))
        self._geometry = self
        self._kinematics = self
        self._optics = self
        self._mechanics = self
        self._last_runtime_transform_time = 0.0

    def _pace_runtime_transform(self, minimum_interval=1.0 / 60.0):
        """Throttle native runtime transforms and yield to stop requests."""
        ctx = _current_context()
        deadline = self._last_runtime_transform_time + max(0.0, float(minimum_interval))
        while True:
            if ctx.stop_requested:
                raise SystemExit(0)
            remaining = deadline - _time.monotonic()
            if remaining <= 0:
                break
            _time.sleep(min(0.005, remaining))
        self._last_runtime_transform_time = _time.monotonic()

    def _set_transform(self, key, value):
        values = [float(value[0]), float(value[1]), float(value[2])]
        self._pace_runtime_transform()
        from CoronaCore.core.corona_editor import CoronaEditor
        engine = CoronaEditor.CoronaEngine
        setter = getattr(engine, "set_editor_actor_transform", None) if engine is not None else None
        if not callable(setter):
            raise RuntimeError("native set_editor_actor_transform is unavailable")
        # Runtime scripts update the native actor in memory without persisting every frame.
        # Snapshot restore keeps the default persist=True behavior.
        payload = _native_payload(setter(
            self.scene_route,
            self.name,
            _json.dumps({key: values, "persist": False}),
        ))
        if payload is None:
            raise RuntimeError(f"native transform update failed: {self.scene_route}/{self.name}")
        setattr(self, "_" + key, values)
        actor_data = payload.get("actor") if isinstance(payload.get("actor"), dict) else None
        if actor_data:
            self._data.update(actor_data)
            self._aabb = actor_data.get("world_aabb") or actor_data.get("aabb") or self._aabb
        return True

    def _operation(self, operation, values):
        try:
            from CoronaCore.core.editor_api import CoronaEditorApi
            CoronaEditorApi.scene_datas.actor_operation(self.scene_route, self.name, operation, list(values))
            return True
        except Exception as exc:
            raise RuntimeError(f"native actor operation {operation} failed: {exc}") from exc

    def to_dict(self): return dict(self._data)
    def get_position(self): return list(self._position)
    def set_position(self, value, *_): return self._set_transform("position", value)
    def get_rotation(self): return list(self._rotation)
    def set_rotation(self, value, *_): return self._set_transform("rotation", value)
    def get_scale(self): return list(self._scale)
    def set_scale(self, value, *_): return self._set_transform("scale", value)
    def get_visible(self): return self._visible
    def set_visible(self, value):
        result = self._operation("SetVisible", [bool(value)])
        self._visible = bool(value)
        return result
    def get_aabb(self):
        try:
            from CoronaCore.core.corona_editor import CoronaEditor
            getter = getattr(CoronaEditor.CoronaEngine, "get_editor_actor_bounds", None)
            payload = _native_payload(getter(self.scene_route, self.name)) if callable(getter) else None
            if payload and payload.get("aabb"):
                self._aabb = payload["aabb"]
        except Exception:
            pass
        return self._aabb
    def set_mass(self, value): self._mass = float(value); return self._operation("SetMass", [self._mass])
    def get_mass(self): return self._mass
    def set_restitution(self, value): self._restitution = float(value); return self._operation("SetRestitution", [self._restitution])
    def get_restitution(self): return self._restitution
    def set_damping(self, value): self._damping = float(value); return self._operation("SetDamping", [self._damping])
    def get_damping(self): return self._damping
    def set_physics_enabled(self, value): self._physics_enabled = bool(value); return self._operation("SetPhysicsEnabled", [self._physics_enabled])
    def get_physics_enabled(self): return self._physics_enabled
    def set_collision_enabled(self, value): return self._operation("SetCollision", [bool(value)])
    def set_linear_lock(self, x, y, z): return self._operation("SetLinearLock", [bool(x), bool(y), bool(z)])
    def set_angular_lock(self, x, y, z): return self._operation("SetAngularLock", [bool(x), bool(y), bool(z)])


class _NativeEditorSceneProxy:
    def __init__(self, route, name, actor_payloads):
        self.route = str(route or "")
        self.name = str(name or self.route)
        self._actors = [_NativeEditorActorProxy(self, item) for item in actor_payloads if isinstance(item, dict)]

    def get_actors(self): return list(self._actors)
    def find_actor(self, name):
        matches = [actor for actor in self._actors if _actor_matches(actor, name) or actor.actor_guid == str(name) or str(actor.handle) == str(name)]
        return matches[0] if len(matches) == 1 else None
    def find_actor_by_route(self, route): return self.find_actor(route)
    def refresh(self):
        payload, _errors = _native_scene_snapshot(self.route)
        if payload is None:
            return False
        actor_payloads = payload.get("actors") if isinstance(payload.get("actors"), list) else []
        self.name = str(payload.get("scene_name") or payload.get("name") or self.name)
        self._actors = [_NativeEditorActorProxy(self, item) for item in actor_payloads if isinstance(item, dict)]
        return True


def resolve_runtime_target(target_type="actor", scene_name="", actor_name=""):
    normalized_type = "actor" if str(target_type or "actor").lower() == "model" else str(target_type or "actor").lower()
    base_diag = {
        "requested_scene": scene_name or "", "requested_actor": actor_name or "",
        "python_scenes": [], "native_scene": "", "actor_candidates": [], "binding_mode": "",
    }
    if normalized_type == "project":
        return {"status": "ok", "target_type": "project", "scene_name": "", "actor_name": "", **base_diag}
    if normalized_type != "actor":
        return {"status": "error", "message": f"\u4e0d\u652f\u6301\u7684\u8fd0\u884c\u76ee\u6807\u7c7b\u578b: {target_type}", **base_diag}
    if not actor_name:
        return {"status": "error", "message": "\u8fd0\u884c\u8282\u70b9\u56fe\u524d\u5fc5\u987b\u9009\u62e9\u4e00\u4e2a\u7269\u4f53", **base_diag}

    scenes = {}
    try:
        from CoronaCore.core.managers import scene_manager
        scenes = scene_manager.get_all() or {}
    except Exception as exc:
        base_diag["python_scene_error"] = str(exc)
    base_diag["python_scenes"] = [str(getattr(scene, "route", key) or key) for key, scene in scenes.items()]
    selected_scene = None
    selected_key = ""
    try:
        from CoronaCore.core.managers import scene_manager
        selected_scene = scene_manager.get(scene_name) if scene_name else None
        selected_key = scene_name if selected_scene is not None else ""
    except Exception:
        pass
    if selected_scene is None and scene_name:
        matched_scenes = [(key, scene) for key, scene in scenes.items() if _scene_matches(key, scene, scene_name)]
        if len(matched_scenes) == 1:
            selected_key, selected_scene = matched_scenes[0]
        elif len(matched_scenes) > 1:
            names = [str(getattr(scene, "route", key) or key) for key, scene in matched_scenes]
            return {"status": "error", "message": f"\u573a\u666f\u6807\u8bc6\u300c{scene_name}\u300d\u5339\u914d\u5230\u591a\u4e2a Python \u573a\u666f: {', '.join(names)}", **base_diag}

    def actors_in(scene):
        try: return list(scene.get_actors())
        except Exception: return list(getattr(scene, "_actors", []) or [])

    if selected_scene is not None:
        matches = [candidate for candidate in actors_in(selected_scene) if _actor_matches(candidate, actor_name)]
        if len(matches) > 1:
            base_diag["actor_candidates"] = [str(getattr(item, "name", actor_name)) for item in matches]
            return {"status": "error", "message": f"\u573a\u666f\u300c{scene_name}\u300d\u4e2d\u5b58\u5728\u591a\u4e2a\u5339\u914d\u7269\u4f53\u300c{actor_name}\u300d", **base_diag}
        actor = matches[0] if matches else None
        if actor is None and hasattr(selected_scene, "find_actor"): actor = selected_scene.find_actor(actor_name)
        if actor is None and hasattr(selected_scene, "find_actor_by_route"): actor = selected_scene.find_actor_by_route(actor_name)
        if actor is not None:
            route = str(getattr(selected_scene, "route", selected_key or scene_name) or selected_key or scene_name)
            return {"status": "ok", "target_type": "actor", "scene_name": route,
                    "actor_name": str(getattr(actor, "name", actor_name) or actor_name),
                    "scene": selected_scene, "actor": actor, **base_diag, "binding_mode": "python_scene"}

    cross_matches = []
    for key, scene in scenes.items():
        for actor in actors_in(scene):
            if _actor_matches(actor, actor_name): cross_matches.append((key, scene, actor))
    if len(cross_matches) == 1:
        key, scene, actor = cross_matches[0]
        return {"status": "ok", "target_type": "actor", "scene_name": str(getattr(scene, "route", key) or key),
                "actor_name": str(getattr(actor, "name", actor_name) or actor_name),
                "scene": scene, "actor": actor, **base_diag, "binding_mode": "python_scene"}
    if len(cross_matches) > 1:
        base_diag["actor_candidates"] = [f"{getattr(scene, 'name', key)}/{getattr(actor, 'name', actor_name)}" for key, scene, actor in cross_matches]
        return {"status": "error", "message": f"\u7269\u4f53\u300c{actor_name}\u300d\u5728\u591a\u4e2a Python \u573a\u666f\u4e2d\u5b58\u5728\uff0c\u8bf7\u6307\u5b9a\u51c6\u786e\u573a\u666f", **base_diag}

    native_payload, native_errors = _native_scene_snapshot(scene_name)
    if native_payload is not None:
        native_route = str(native_payload.get("scene") or native_payload.get("scene_id") or native_payload.get("id") or scene_name or "")
        native_name = str(native_payload.get("scene_name") or native_payload.get("name") or native_route)
        base_diag["native_scene"] = native_route or native_name
        actor_payloads = native_payload.get("actors") if isinstance(native_payload.get("actors"), list) else []
        matches = [item for item in actor_payloads if _native_actor_matches(item, actor_name)]
        base_diag["actor_candidates"] = [str(item.get("name") or item.get("route") or "") for item in matches]
        if scene_name and not _native_scene_matches(native_payload, scene_name):
            return {"status": "error", "message": f"\u539f\u751f\u573a\u666f\u8fd4\u56de\u300c{native_route or native_name}\u300d\uff0c\u4e0e\u8bf7\u6c42\u573a\u666f\u300c{scene_name}\u300d\u4e0d\u4e00\u81f4", **base_diag}
        if len(matches) == 1:
            scene_proxy = _NativeEditorSceneProxy(native_route, native_name, actor_payloads)
            actor_proxy = scene_proxy.find_actor(matches[0].get("actor_guid") or matches[0].get("handle") or matches[0].get("name"))
            return {"status": "ok", "target_type": "actor", "scene_name": native_route,
                    "actor_name": actor_proxy.name, "scene": scene_proxy, "actor": actor_proxy,
                    **base_diag, "binding_mode": "native_editor"}
        if len(matches) > 1:
            return {"status": "error", "message": f"\u539f\u751f\u573a\u666f\u300c{native_name}\u300d\u4e2d\u5b58\u5728\u591a\u4e2a\u5339\u914d\u7269\u4f53\u300c{actor_name}\u300d", **base_diag}
        return {"status": "error", "message": f"\u539f\u751f\u573a\u666f\u300c{native_name}\u300d\u4e2d\u672a\u627e\u5230\u7269\u4f53\u300c{actor_name}\u300d", **base_diag}

    if native_errors:
        base_diag["native_errors"] = native_errors
    if selected_scene is None:
        return {"status": "error", "message": f"\u672a\u627e\u5230\u573a\u666f\u300c{scene_name}\u300d\uff0c\u4e5f\u672a\u5728 Python \u6216\u539f\u751f\u7f16\u8f91\u573a\u666f\u4e2d\u627e\u5230\u7269\u4f53\u300c{actor_name}\u300d", **base_diag}
    return {"status": "error", "message": f"\u573a\u666f\u300c{scene_name}\u300d\u4e2d\u672a\u627e\u5230\u7269\u4f53\u300c{actor_name}\u300d", **base_diag}


def capture_runtime_scene_state(scene_name="", scene=None, binding_mode=""):
    """Capture the current scene for single node-graph execution restoration."""
    scene = scene or _runtime_scene()
    if binding_mode == "native_editor" or isinstance(scene, _NativeEditorSceneProxy):
        route = str(getattr(scene, "route", "") or scene_name or "")
        payload, errors = _native_scene_snapshot(route)
        if payload is None:
            raise RuntimeError("\u65e0\u6cd5\u8bfb\u53d6\u539f\u751f\u573a\u666f\u5feb\u7167" + (f": {'; '.join(errors)}" if errors else ""))
        return {"binding_mode": "native_editor", "scene_name": route, "payload": payload}

    if scene is None:
        raise RuntimeError(f"\u672a\u627e\u5230\u53ef\u6062\u590d\u7684 Python \u573a\u666f\u300c{scene_name}\u300d")
    actors = []
    for actor in _iter_scene_actors(scene):
        actors.append({
            "name": _object_name(actor),
            "route": str(getattr(actor, "route", "") or ""),
            "actor_type": str(getattr(actor, "actor_type", "model") or "model"),
            "geometry": {
                "position": list(getattr(actor, "get_position", lambda: [0, 0, 0])()),
                "rotation": list(getattr(actor, "get_rotation", lambda: [0, 0, 0])()),
                "scale": list(getattr(actor, "get_scale", lambda: [1, 1, 1])()),
            },
            "visible": getattr(actor, "get_visible", lambda: True)(),
            "collision": getattr(actor, "get_collision_enabled", lambda: True)(),
            "mechanics": {
                "mass": getattr(actor, "get_mass", lambda: 1.0)(),
                "restitution": getattr(actor, "get_restitution", lambda: 0.0)(),
                "damping": getattr(actor, "get_damping", lambda: 0.0)(),
                "physics_enabled": getattr(actor, "get_physics_enabled", lambda: False)(),
            },
        })
    return {
        "binding_mode": "python_scene",
        "scene_name": str(getattr(scene, "route", "") or scene_name or ""),
        "scene": scene,
        "payload": {"actors": actors},
    }


def _snapshot_actor_key(data):
    guid = str((data or {}).get("actor_guid") or "").strip()
    if guid:
        return "guid:" + guid.casefold()
    return "name:" + _target_token((data or {}).get("name") or (data or {}).get("route") or "")


def _native_restore_operation(scene_route, actor_name, operation, values):
    from CoronaCore.core.editor_api import CoronaEditorApi
    action = f"Restore actor {actor_name} operation {operation}"
    return _native_payload_or_raise(
        CoronaEditorApi.scene_datas.actor_operation(
            scene_route, actor_name, operation, list(values)
        ),
        action,
    )


def _restore_native_actor_state(scene_route, actor_data):
    from CoronaCore.core.corona_editor import CoronaEditor
    actor_name = str(actor_data.get("name") or actor_data.get("route") or "")
    if not actor_name:
        raise RuntimeError("Scene snapshot actor is missing a name")
    engine = CoronaEditor.CoronaEngine
    geometry = actor_data.get("geometry") if isinstance(actor_data.get("geometry"), dict) else {}
    mechanics = actor_data.get("mechanics") if isinstance(actor_data.get("mechanics"), dict) else {}
    setter = getattr(engine, "set_editor_actor_transform", None) if engine is not None else None
    if not callable(setter):
        raise RuntimeError("native set_editor_actor_transform is unavailable")

    # Pause physics before restoring transforms so simulation cannot race restoration.
    if mechanics:
        _native_restore_operation(scene_route, actor_name, "SetPhysicsEnabled", [False])

    transform = {
        key: list(geometry[key])
        for key in ("position", "rotation", "scale")
        if isinstance(geometry.get(key), (list, tuple))
    }
    if transform:
        _native_payload_or_raise(
            setter(scene_route, actor_name, _json.dumps(transform, ensure_ascii=False)),
            f"Restore actor {actor_name} transform",
        )

    _native_restore_operation(
        scene_route, actor_name, "SetVisible", [bool(actor_data.get("visible", True))]
    )
    _native_restore_operation(
        scene_route, actor_name, "SetCollision", [bool(actor_data.get("collision", True))]
    )
    if "mass" in mechanics:
        _native_restore_operation(scene_route, actor_name, "SetMass", [mechanics.get("mass")])
    if "restitution" in mechanics:
        _native_restore_operation(
            scene_route, actor_name, "SetRestitution", [mechanics.get("restitution")]
        )
    if "damping" in mechanics:
        _native_restore_operation(scene_route, actor_name, "SetDamping", [mechanics.get("damping")])
    linear = mechanics.get("linear_lock")
    if isinstance(linear, (list, tuple)) and len(linear) >= 3:
        _native_restore_operation(
            scene_route,
            actor_name,
            "SetLinearLock",
            [bool(linear[0]), bool(linear[1]), bool(linear[2])],
        )
    angular = mechanics.get("angular_lock")
    if isinstance(angular, (list, tuple)) and len(angular) >= 3:
        _native_restore_operation(
            scene_route,
            actor_name,
            "SetAngularLock",
            [bool(angular[0]), bool(angular[1]), bool(angular[2])],
        )
    if "physics_enabled" in mechanics:
        _native_restore_operation(
            scene_route,
            actor_name,
            "SetPhysicsEnabled",
            [bool(mechanics.get("physics_enabled"))],
        )


def _snapshot_actor_match(actors, expected):
    expected_key = _snapshot_actor_key(expected)
    expected_guid = str((expected or {}).get("actor_guid") or "").strip().casefold()
    expected_name = str((expected or {}).get("name") or "").strip().casefold()
    expected_route = str((expected or {}).get("route") or (expected or {}).get("path") or "").strip().replace("\\", "/").casefold()
    for actor in actors:
        if _snapshot_actor_key(actor) == expected_key:
            return actor
    if expected_guid:
        for actor in actors:
            if str(actor.get("actor_guid") or "").strip().casefold() == expected_guid:
                return actor
    if expected_name:
        matches = [actor for actor in actors if str(actor.get("name") or "").strip().casefold() == expected_name]
        if len(matches) == 1:
            return matches[0]
    if expected_route and not expected_guid and not expected_name:
        matches = [
            actor for actor in actors
            if str(actor.get("route") or actor.get("path") or "").strip().replace("\\", "/").casefold() == expected_route
        ]
        if len(matches) == 1:
            return matches[0]
    return None


def _values_close(expected, actual, tolerance=1.0e-3):
    try:
        return abs(float(expected) - float(actual)) <= tolerance
    except (TypeError, ValueError):
        return expected == actual


def _native_actor_state_mismatches(expected, actual):
    mismatches = []
    expected_geometry = expected.get("geometry") if isinstance(expected.get("geometry"), dict) else {}
    actual_geometry = actual.get("geometry") if isinstance(actual.get("geometry"), dict) else {}
    for key in ("position", "rotation", "scale"):
        expected_value = expected_geometry.get(key)
        actual_value = actual_geometry.get(key)
        if not isinstance(expected_value, (list, tuple)):
            continue
        if not isinstance(actual_value, (list, tuple)) or len(actual_value) < len(expected_value):
            mismatches.append(key)
            continue
        if any(not _values_close(left, right) for left, right in zip(expected_value, actual_value)):
            mismatches.append(key)
    for key in ("visible", "collision"):
        if key in expected and bool(expected.get(key)) != bool(actual.get(key)):
            mismatches.append(key)

    expected_mechanics = expected.get("mechanics") if isinstance(expected.get("mechanics"), dict) else {}
    actual_mechanics = actual.get("mechanics") if isinstance(actual.get("mechanics"), dict) else {}
    for key in ("mass", "restitution", "damping"):
        if key in expected_mechanics and not _values_close(
            expected_mechanics.get(key), actual_mechanics.get(key)
        ):
            mismatches.append("mechanics." + key)
    if "physics_enabled" in expected_mechanics and bool(expected_mechanics.get("physics_enabled")) != bool(actual_mechanics.get("physics_enabled")):
        mismatches.append("mechanics.physics_enabled")
    for key in ("linear_lock", "angular_lock"):
        expected_value = expected_mechanics.get(key)
        actual_value = actual_mechanics.get(key)
        if isinstance(expected_value, (list, tuple)):
            if not isinstance(actual_value, (list, tuple)) or tuple(bool(v) for v in expected_value[:3]) != tuple(bool(v) for v in actual_value[:3]):
                mismatches.append("mechanics." + key)
    return mismatches


def _verify_native_scene_restored(scene_route, original):
    payload, errors = _native_scene_snapshot(scene_route)
    if payload is None:
        return ["Unable to read the restored native scene" + (f": {'; '.join(errors)}" if errors else "")]
    current = [item for item in payload.get("actors", []) if isinstance(item, dict)]
    failures = []
    matched_ids = set()
    for expected in original:
        actual = _snapshot_actor_match(current, expected)
        actor_name = str(expected.get("name") or expected.get("route") or "(unnamed)")
        if actual is None:
            failures.append(f"Missing actor {actor_name}")
            continue
        matched_ids.add(id(actual))
        mismatches = _native_actor_state_mismatches(expected, actual)
        if mismatches:
            failures.append(f"Actor {actor_name} fields not restored: {', '.join(mismatches)}")
    extras = [
        str(actor.get("name") or actor.get("route") or "(unnamed)")
        for actor in current
        if id(actor) not in matched_ids
    ]
    if extras:
        failures.append("Runtime-created actors still exist: " + ", ".join(extras))
    return failures



def _clear_scene_runtime_state(scene_name):
    requested = _target_variants(scene_name)
    with _context_lock:
        cache_maps = (_scene_virtual_objects, _scene_deleted_objects, _scene_object_tags)
        for cache in cache_maps:
            for key in list(cache):
                if key == "__default__" and not requested:
                    cache.pop(key, None)
                elif _target_variants(key) & requested:
                    cache.pop(key, None)
        for ctx in list(_contexts.values()):
            if _target_variants(ctx.scene_name) & _target_variants(scene_name):
                ctx.virtual_objects.clear()
                ctx.deleted_objects.clear()
                ctx.object_tags.clear()
                globals().get('_velocity_cache', {}).pop(ctx.context_id, None)
                globals().get('_raycast_cache', {}).pop(ctx.context_id, None)


def restore_runtime_scene_state(snapshot):
    if not isinstance(snapshot, dict):
        raise RuntimeError("\u65e0\u6548\u7684\u573a\u666f\u6062\u590d\u5feb\u7167")
    mode = snapshot.get("binding_mode")
    scene_route = str(snapshot.get("scene_name") or "")
    payload = snapshot.get("payload") if isinstance(snapshot.get("payload"), dict) else {}
    original = [item for item in payload.get("actors", []) if isinstance(item, dict)]

    if mode == "native_editor":
        from CoronaCore.core.corona_editor import CoronaEditor
        engine = CoronaEditor.CoronaEngine
        remover = getattr(engine, "remove_editor_actor", None) if engine is not None else None
        creator = getattr(engine, "create_editor_actor", None) if engine is not None else None

        verification_failures = []
        for attempt in range(3):
            current_payload, errors = _native_scene_snapshot(scene_route)
            if current_payload is None:
                raise RuntimeError(
                    "Unable to read the current native scene while stopping"
                    + (f": {'; '.join(errors)}" if errors else "")
                )
            current = [
                item for item in current_payload.get("actors", []) if isinstance(item, dict)
            ]

            # Remove runtime-created actors. Prefer GUID; use name/route only as fallback.
            runtime_created = [
                item for item in current
                if not any(_snapshot_actor_match([item], expected) is not None for expected in original)
            ]
            if runtime_created and not callable(remover):
                names = ", ".join(str(item.get("name") or item.get("route") or "") for item in runtime_created)
                raise RuntimeError(f"Native remove actor API is unavailable; cannot remove: {names}")
            for item in runtime_created:
                actor_name = str(item.get("name") or item.get("route") or "")
                _native_payload_or_raise(
                    remover(scene_route, actor_name),
                    f"Remove runtime-created actor {actor_name}",
                )

            refreshed, errors = _native_scene_snapshot(scene_route)
            if refreshed is None:
                raise RuntimeError(
                    "Unable to refresh the native scene after removing runtime actors"
                    + (f": {'; '.join(errors)}" if errors else "")
                )
            current = [item for item in refreshed.get("actors", []) if isinstance(item, dict)]

            # Recreate original actors deleted during runtime.
            missing_originals = [item for item in original if _snapshot_actor_match(current, item) is None]
            if missing_originals and not callable(creator):
                names = ", ".join(str(item.get("name") or item.get("route") or "") for item in missing_originals)
                raise RuntimeError(f"Native create actor API is unavailable; cannot recreate: {names}")
            for item in missing_originals:
                route = str(item.get("route") or item.get("path") or item.get("model") or "")
                actor_type = str(item.get("actor_type") or "model")
                actor_name = str(item.get("name") or _Path(route).stem or "actor")
                actor_data = dict(item)
                actor_data.update(actor_name=actor_name, name=actor_name, skip_if_exists=False)
                _native_payload_or_raise(
                    creator(
                        scene_route,
                        route,
                        actor_type,
                        _json.dumps(actor_data, ensure_ascii=False),
                    ),
                    f"Recreate original actor {actor_name}",
                )

            refreshed, errors = _native_scene_snapshot(scene_route)
            if refreshed is None:
                raise RuntimeError(
                    "Unable to refresh the native scene after recreating actors"
                    + (f": {'; '.join(errors)}" if errors else "")
                )
            current = [item for item in refreshed.get("actors", []) if isinstance(item, dict)]
            for item in original:
                actor_name = str(item.get("name") or item.get("route") or "")
                if _snapshot_actor_match(current, item) is None:
                    raise RuntimeError(f"Actor {actor_name} is still missing after recreation")
                _restore_native_actor_state(scene_route, item)

            # Native writes and render/physics synchronization may cross a short frame.
            # Re-read and verify; retry twice and never report restored on mismatch.
            _time.sleep(0.02 * (attempt + 1))
            verification_failures = _verify_native_scene_restored(scene_route, original)
            if not verification_failures:
                break
            _logger.warning(
                "[ScratchWrapper] native scene restore verification failed (attempt %d/3): %s",
                attempt + 1,
                "; ".join(verification_failures),
            )

        if verification_failures:
            raise RuntimeError("Scene restore verification failed: " + "; ".join(verification_failures))

        _clear_scene_runtime_state(scene_route)
        try:
            CoronaEditor.emit_editor_event("scene-tree-changed", [scene_route])
            if CoronaEditor._selected_scene == scene_route and CoronaEditor._selected_actor:
                CoronaEditor.emit_editor_event(
                    "actor-change", ["actor", scene_route, CoronaEditor._selected_actor]
                )
        except Exception:
            _logger.debug("[ScratchWrapper] failed to notify restored native scene", exc_info=True)
        return True

    scene = snapshot.get("scene")
    if scene is None:
        raise RuntimeError("Python \u573a\u666f\u6062\u590d\u5feb\u7167\u5df2\u5931\u6548")
    original_names = {_target_token(item.get("name")): item for item in original}
    for actor in list(_iter_scene_actors(scene)):
        name = _object_name(actor)
        if _target_token(name) not in original_names:
            remover = getattr(scene, "remove_actor", None)
            if callable(remover):
                remover(name)
    for name_key, item in original_names.items():
        actor = scene.find_actor(item.get("name")) if hasattr(scene, "find_actor") else None
        if actor is None:
            created = _try_native_spawn(scene, item.get("route"), item.get("name"), item.get("geometry", {}).get("position", [0, 0, 0]))
            actor = created
        if actor is None:
            raise RuntimeError(f"\u65e0\u6cd5\u5728 Python \u573a\u666f\u4e2d\u91cd\u5efa\u7269\u4f53\u300c{item.get('name')}\u300d")
        geometry = item.get("geometry") or {}
        for method_name, key in (("set_position", "position"), ("set_rotation", "rotation"), ("set_scale", "scale")):
            method = getattr(actor, method_name, None)
            if callable(method) and key in geometry:
                method(geometry[key])
        if hasattr(actor, "set_visible"):
            actor.set_visible(item.get("visible", True))
    _clear_scene_runtime_state(scene_route)
    return True


def _init_engine():
    ctx = _current_context()
    if ctx.initialized:
        if ctx.binding_error:
            raise RuntimeError(ctx.binding_error)
        return
    ctx.initialized = True
    if ctx.target_type == "project":
        return
    if ctx.external_target:
        _init_external_target(ctx)
        if ctx.binding_error:
            raise RuntimeError(ctx.binding_error)
    else:
        _init_internal_actor(ctx)


def _init_external_target(ctx: ScratchRuntimeContext):
    try:
        resolved = resolve_runtime_target(ctx.target_type, ctx.target_scene_name, ctx.target_actor_name)
        if resolved.get("status") != "ok":
            ctx.binding_error = str(resolved.get("message") or "\u65e0\u6cd5\u7ed1\u5b9a\u8fd0\u884c\u76ee\u6807")
            return

        ctx.target_type = resolved["target_type"]
        ctx.scene_name = resolved["scene_name"]
        ctx.actor_name = resolved["actor_name"]
        ctx.target_scene_name = resolved["scene_name"]
        ctx.target_actor_name = resolved["actor_name"]
        ctx.target_scene = resolved.get("scene")
        ctx.target_actor = resolved.get("actor")
        ctx.binding_error = ""
        ctx.actor = ctx.target_actor
        ctx.scene = ctx.target_scene
        ctx.geometry = getattr(ctx.target_actor, "_geometry", None)
        ctx.optics = getattr(ctx.target_actor, "_optics", None)
        ctx.kinematics = getattr(ctx.target_actor, "_kinematics", None)
        ctx.mechanics = getattr(ctx.target_actor, "_mechanics", None)

        try:
            pos = ctx.target_actor.get_position()
            ctx.x, ctx.y, ctx.z = float(pos[0]), float(pos[1]), float(pos[2])
        except Exception:
            pass
        try:
            rot = ctx.target_actor.get_rotation()
            ctx.rot_x, ctx.rot_y, ctx.rot_z = float(rot[0]), float(rot[1]), float(rot[2])
        except Exception:
            pass
        try:
            scale = ctx.target_actor.get_scale()
            ctx.size_val = float(scale[0]) * 100.0
        except Exception:
            pass
    except Exception as exc:
        ctx.binding_error = f"\u7ed1\u5b9a\u7269\u4f53\u5931\u8d25: {exc}"
        _logger.exception("[ScratchWrapper] bind actor failed: %s", exc)


def _init_internal_actor(ctx: ScratchRuntimeContext):
    ctx.geometry = None
    ctx.optics = None
    ctx.kinematics = None
    ctx.mechanics = None
    ctx.actor = None
    ctx.scene = None


def _sync_position():
    ctx = _current_context()
    check_stop()
    failures = []
    attempted = False
    with _engine_lock:
        if ctx.geometry is not None and hasattr(ctx.geometry, "set_position"):
            attempted = True
            try:
                ctx.geometry.set_position([ctx.x, ctx.y, ctx.z])
                return True
            except Exception as exc:
                failures.append(f"geometry.set_position: {exc}")
        if ctx.actor is not None and hasattr(ctx.actor, "set_position"):
            attempted = True
            try:
                ctx.actor.set_position([ctx.x, ctx.y, ctx.z])
                return True
            except Exception as exc:
                failures.append(f"actor.set_position: {exc}")
    if ctx.external_target:
        detail = "; ".join(failures) if failures else "target exposes no set_position interface"
        raise RuntimeError(f"Failed to move bound Actor '{ctx.actor_name}': {detail}")
    return not attempted


def _sync_scale():
    ctx = _current_context()
    check_stop()
    scale = ctx.size_val / 100.0
    failures = []
    attempted = False
    with _engine_lock:
        if ctx.geometry is not None and hasattr(ctx.geometry, "set_scale"):
            attempted = True
            try:
                ctx.geometry.set_scale([scale, scale, scale])
                return True
            except Exception as exc:
                failures.append(f"geometry.set_scale: {exc}")
        if ctx.actor is not None and hasattr(ctx.actor, "set_scale"):
            attempted = True
            try:
                ctx.actor.set_scale([scale, scale, scale])
                return True
            except Exception as exc:
                failures.append(f"actor.set_scale: {exc}")
    if ctx.external_target:
        detail = "; ".join(failures) if failures else "target exposes no set_scale interface"
        raise RuntimeError(f"Failed to scale bound Actor '{ctx.actor_name}': {detail}")
    return not attempted


def _apply_rotation():
    ctx = _current_context()
    check_stop()
    rot = [ctx.rot_x, ctx.rot_y, ctx.rot_z]
    mech_was_enabled = False
    failures = []
    attempted = False
    success = False
    with _engine_lock:
        if ctx.mechanics is not None and hasattr(ctx.mechanics, "set_physics_enabled"):
            try:
                mech_was_enabled = ctx.mechanics.get_physics_enabled()
                if mech_was_enabled:
                    ctx.mechanics.set_physics_enabled(False)
            except Exception:
                pass
        for target, method in (
            (ctx.kinematics, "set_rotation"),
            (ctx.geometry, "set_rotation"),
            (ctx.actor, "set_rotation"),
        ):
            if target is not None and hasattr(target, method):
                attempted = True
                try:
                    getattr(target, method)(rot)
                    success = True
                    break
                except Exception as exc:
                    failures.append(f"{type(target).__name__}.{method}: {exc}")
        if mech_was_enabled and ctx.mechanics is not None:
            try:
                ctx.mechanics.set_physics_enabled(True)
            except Exception:
                pass
    if success:
        return True
    if ctx.external_target:
        detail = "; ".join(failures) if failures else "target exposes no set_rotation interface"
        raise RuntimeError(f"Failed to rotate bound Actor '{ctx.actor_name}': {detail}")
    return not attempted


# Engine / motion
def move(steps):
    if _actor_only("move"):
        return
    _init_engine()
    ctx = _current_context()
    ctx.x += float(steps)
    _sync_position()


def rotateX(angle):
    if _actor_only("rotateX"):
        return
    _init_engine()
    ctx = _current_context()
    ctx.rot_x += float(angle)
    if ctx.kinematics is not None and hasattr(ctx.kinematics, "rotate_x"):
        try:
            ctx.kinematics.rotate_x(float(angle))
        except Exception:
            pass
    _apply_rotation()


def rotateY(angle):
    if _actor_only("rotateY"):
        return
    _init_engine()
    ctx = _current_context()
    ctx.rot_y += float(angle)
    if ctx.kinematics is not None and hasattr(ctx.kinematics, "rotate_y"):
        try:
            ctx.kinematics.rotate_y(float(angle))
        except Exception:
            pass
    _apply_rotation()


def rotateZ(angle):
    if _actor_only("rotateZ"):
        return
    _init_engine()
    ctx = _current_context()
    ctx.rot_z += float(angle)
    if ctx.kinematics is not None and hasattr(ctx.kinematics, "rotate_z"):
        try:
            ctx.kinematics.rotate_z(float(angle))
        except Exception:
            pass
    _apply_rotation()


def face(direction):
    if _actor_only("face"):
        return
    _init_engine()
    _current_context().rot_y = float(direction)
    _apply_rotation()


def rotationX():
    _init_engine()
    return _current_context().rot_x


def rotationY():
    _init_engine()
    return _current_context().rot_y


def rotationZ():
    _init_engine()
    return _current_context().rot_z


def moveto(position):
    if _actor_only("moveto"):
        return
    _init_engine()
    ctx = _current_context()
    if position == "random_position":
        ctx.x = _random.uniform(-10, 10)
        ctx.y = _random.uniform(-5, 5)
        ctx.z = _random.uniform(-10, 10)
    elif position == "sight_position":
        ctx.x, ctx.y, ctx.z = 0.0, 0.0, 0.0
    else:
        _logger.warning("[ScratchWrapper] unknown moveto position: %s", position)
        return
    _sync_position()


def movetoXYZ(position):
    if _actor_only("movetoXYZ"):
        return False
    _init_engine()
    try:
        values = position
        if isinstance(position, str):
            values = [item.strip() for item in position.split(',')]
        if len(values) < 3:
            return False
        ctx = _current_context()
        ctx.x, ctx.y, ctx.z = (float(values[0]), float(values[1]), float(values[2]))
        _sync_position()
        return True
    except (TypeError, ValueError):
        _logger.warning("[ScratchWrapper] invalid movetoXYZ position: %r", position)
        return False


def movetoXYZtime(t, x1, x2, x3):
    if _actor_only("movetoXYZtime"):
        return
    _init_engine()
    ctx = _current_context()
    ctx.x, ctx.y, ctx.z = float(x1), float(x2), float(x3)
    _sync_position()


def Xset(x):
    if _actor_only("Xset"):
        return
    _init_engine()
    _current_context().x = float(x)
    _sync_position()


def Yset(y):
    if _actor_only("Yset"):
        return
    _init_engine()
    _current_context().y = float(y)
    _sync_position()


def Zset(z):
    if _actor_only("Zset"):
        return
    _init_engine()
    _current_context().z = float(z)
    _sync_position()


def Xadd(dx):
    if _actor_only("Xadd"):
        return
    _init_engine()
    _current_context().x += float(dx)
    _sync_position()


def Yadd(dy):
    if _actor_only("Yadd"):
        return
    _init_engine()
    _current_context().y += float(dy)
    _sync_position()


def Zadd(dz):
    if _actor_only("Zadd"):
        return
    _init_engine()
    _current_context().z += float(dz)
    _sync_position()


def X():
    _init_engine()
    return _current_context().x


def Y():
    _init_engine()
    return _current_context().y


def Z():
    _init_engine()
    return _current_context().z


# ── Camera / FPS controls ──

def lock_mouse():
    """Lock the preview mouse when native support exists; always retain runtime state."""
    ctx = _current_context()
    ctx.mouse_locked = True
    try:
        import corona_engine as _ce
        method = getattr(_ce, 'set_mouse_locked', None)
        if callable(method):
            result = method(True)
            return result is not False
    except Exception as exc:
        _logger.warning("[ScratchWrapper] native lock_mouse failed; using runtime state: %s", exc)
    return False


def unlock_mouse():
    """Unlock the preview mouse when native support exists; always retain runtime state."""
    ctx = _current_context()
    ctx.mouse_locked = False
    try:
        import corona_engine as _ce
        method = getattr(_ce, 'set_mouse_locked', None)
        if callable(method):
            result = method(False)
            return result is not False
    except Exception as exc:
        _logger.warning("[ScratchWrapper] native unlock_mouse failed; using runtime state: %s", exc)
    return False


def mouse_dx():
    """获取本帧鼠标 X 位移量"""
    try:
        import corona_engine as _ce
        if hasattr(_ce, 'get_mouse_delta'):
            dx, _dy = _ce.get_mouse_delta()
            return float(dx)
    except Exception:
        pass
    return float(_current_context().mouse_delta_x)


def mouse_dy():
    """获取本帧鼠标 Y 位移量"""
    try:
        import corona_engine as _ce
        if hasattr(_ce, 'get_mouse_delta'):
            _dx, dy = _ce.get_mouse_delta()
            return float(dy)
    except Exception:
        pass
    return float(_current_context().mouse_delta_y)


def set_fov(fov_degrees):
    """设置当前场景 active camera 的视野角度。"""
    value = _safe_float(fov_degrees, 45.0)
    camera, scene = _active_camera_with_scene()
    if camera is not None:
        try:
            if hasattr(camera, 'set_fov'):
                camera.set_fov(value)
                return True
            if hasattr(camera, 'set'):
                camera.set(
                    _camera_vec(camera, 'get_position', [0.0, 0.0, 0.0]),
                    _camera_vec(camera, 'get_forward', [0.0, 0.0, 1.0]),
                    _camera_vec(camera, 'get_world_up', [0.0, 1.0, 0.0]),
                    value,
                )
                return True
            if scene is not None and hasattr(scene, 'set_camera'):
                return bool(scene.set_camera(
                    _camera_vec(camera, 'get_position', [0.0, 0.0, 0.0]),
                    _camera_vec(camera, 'get_forward', [0.0, 0.0, 1.0]),
                    _camera_vec(camera, 'get_world_up', [0.0, 1.0, 0.0]),
                    value,
                ))
        except Exception as exc:
            _logger.warning("[ScratchWrapper] set_fov camera call failed: %s", exc)
    return False



def _active_camera_with_scene():
    scene = _runtime_scene()
    if scene is None or not hasattr(scene, 'get_active_camera'):
        return None, scene
    try:
        return scene.get_active_camera(), scene
    except Exception as exc:
        _logger.debug("[ScratchWrapper] active camera unavailable: %s", exc)
        return None, scene


def _camera_vec(camera, method_name, fallback):
    if camera is None or not hasattr(camera, method_name):
        return list(fallback)
    try:
        value = getattr(camera, method_name)()
        return [float(value[0]), float(value[1]), float(value[2])]
    except Exception:
        return list(fallback)


def _camera_fov(camera, fallback=45.0):
    if camera is None or not hasattr(camera, 'get_fov'):
        return float(fallback)
    try:
        return float(camera.get_fov())
    except Exception:
        return float(fallback)


def camera_follow_object(name, ox, oy, oz):
    """Move active camera to object position plus offset; call once per update."""
    actor = _resolve_actor(name)
    if actor is None:
        return False
    target_pos = _actor_position(actor)
    if target_pos is None:
        return False
    camera, scene = _active_camera_with_scene()
    if camera is None:
        return False
    new_pos = [
        float(target_pos[0]) + float(ox),
        float(target_pos[1]) + float(oy),
        float(target_pos[2]) + float(oz),
    ]
    forward = _camera_vec(camera, 'get_forward', [0.0, 0.0, 1.0])
    up = _camera_vec(camera, 'get_world_up', [0.0, 1.0, 0.0])
    fov = _camera_fov(camera)
    try:
        if scene is not None and hasattr(scene, 'set_camera'):
            result = scene.set_camera(new_pos, forward, up, fov)
            return result is not False
    except Exception as exc:
        _logger.debug("[ScratchWrapper] scene.set_camera failed: %s", exc)
    try:
        if hasattr(camera, 'set'):
            result = camera.set(new_pos, forward, up, fov)
            return result is not False
        if hasattr(camera, 'set_position'):
            result = camera.set_position(new_pos)
            return result is not False
    except Exception as exc:
        _logger.debug("[ScratchWrapper] camera_follow_object failed: %s", exc)
    return False


def camera_raycast(max_dist):
    """Raycast from active camera position along its forward vector."""
    camera, _scene = _active_camera_with_scene()
    if camera is None:
        cache = _get_raycast_cache()
        cache['hit'] = False
        cache['distance'] = float(max_dist)
        cache['object'] = ''
        cache['point'] = (0.0, 0.0, 0.0)
        return False
    origin = _camera_vec(camera, 'get_position', [0.0, 0.0, 0.0])
    direction = _camera_vec(camera, 'get_forward', [0.0, 0.0, 1.0])
    return raycast_hit(origin, direction, float(max_dist))


def camera_raycast_object():
    return raycast_hit_object()


# ── Physics extension (velocity / impulse) ──

_velocity_cache = {}  # context_id → [vx, vy, vz]
_native_velocity_contexts = set()
_native_gravity_contexts = set()


def set_velocity(vx, vy, vz):
    """设置当前 Actor 的线速度；无原生接口时由 wait/check 循环推进。"""
    if _actor_only("set_velocity"):
        return False
    _init_engine()
    ctx = _current_context()
    vel = [float(vx), float(vy), float(vz)]
    _velocity_cache[ctx.context_id] = list(vel)
    for target in (ctx.mechanics, ctx.actor):
        method = getattr(target, 'set_velocity', None) if target is not None else None
        if callable(method):
            try:
                method(vel)
                _native_velocity_contexts.add(ctx.context_id)
                return True
            except TypeError:
                try:
                    method(*vel)
                    _native_velocity_contexts.add(ctx.context_id)
                    return True
                except Exception:
                    pass
            except Exception:
                pass
    _native_velocity_contexts.discard(ctx.context_id)
    return True


def apply_impulse(ix, iy, iz):
    """施加瞬时冲量；无原生物理时累加到运行时速度。"""
    if _actor_only("apply_impulse"):
        return False
    _init_engine()
    ctx = _current_context()
    imp = [float(ix), float(iy), float(iz)]
    for target in (ctx.mechanics, ctx.actor):
        method = getattr(target, 'apply_impulse', None) if target is not None else None
        if callable(method):
            try:
                method(imp)
                _native_velocity_contexts.add(ctx.context_id)
                return True
            except TypeError:
                try:
                    method(*imp)
                    _native_velocity_contexts.add(ctx.context_id)
                    return True
                except Exception:
                    pass
            except Exception:
                pass
    vel = _velocity_list(ctx)
    _velocity_cache[ctx.context_id] = [vel[i] + imp[i] for i in range(3)]
    _native_velocity_contexts.discard(ctx.context_id)
    return True

def _velocity_list(ctx=None):
    ctx = ctx or _current_context()
    for target in (ctx.mechanics, ctx.actor):
        getter = getattr(target, 'get_velocity', None) if target is not None else None
        if callable(getter):
            try:
                native = getter()
                if isinstance(native, (list, tuple)) and len(native) >= 3:
                    vel = [_safe_float(native[0]), _safe_float(native[1]), _safe_float(native[2])]
                    _velocity_cache[ctx.context_id] = vel
                    return vel
            except Exception:
                pass
    vel = _velocity_cache.get(ctx.context_id)
    if not isinstance(vel, (list, tuple)) or len(vel) < 3:
        vel = [0.0, 0.0, 0.0]
    return [_safe_float(vel[0]), _safe_float(vel[1]), _safe_float(vel[2])]

def get_velocity(axis='X'):
    """Get the cached current velocity component."""
    cache = _velocity_list()
    mapping = {'X': 0, 'Y': 1, 'Z': 2}
    return float(cache[mapping.get(str(axis or 'X').upper(), 0)])


def _tick_runtime_physics(dt):
    ctx = _current_context()
    if ctx.target_type == "project":
        return
    dt = max(0.0, _safe_float(dt)) * game_speed()
    if dt <= 0:
        return
    vel = _velocity_list(ctx)
    if ctx.gravity_enabled and ctx.context_id not in _native_gravity_contexts:
        vel[1] -= _safe_float(ctx.gravity_strength, 9.8) * dt
    if ctx.context_id in _native_velocity_contexts:
        return
    if ctx.gravity_enabled or any(abs(v) > 1e-9 for v in vel):
        _velocity_cache[ctx.context_id] = vel
        ctx.x += vel[0] * dt
        ctx.y += vel[1] * dt
        ctx.z += vel[2] * dt
        _sync_position()


def set_gravity(enabled, strength=9.8):
    ctx = _current_context()
    ctx.gravity_enabled = str(enabled).strip().lower() not in ('0', 'false', 'off', 'no', 'none', '')
    ctx.gravity_strength = _safe_float(strength, 9.8)
    _init_engine()
    native_applied = False
    for target in (ctx.mechanics, ctx.actor):
        if target is None:
            continue
        for method_name in ('set_gravity_enabled', 'enable_gravity'):
            method = getattr(target, method_name, None)
            if callable(method):
                try:
                    method(ctx.gravity_enabled)
                    native_applied = True
                except Exception as exc:
                    _logger.debug("[ScratchWrapper] %s failed: %s", method_name, exc)
        method = getattr(target, 'set_gravity', None)
        if callable(method):
            try:
                method(ctx.gravity_enabled, ctx.gravity_strength)
                native_applied = True
            except TypeError:
                try:
                    method(ctx.gravity_strength if ctx.gravity_enabled else 0.0)
                    native_applied = True
                except Exception as exc:
                    _logger.debug("[ScratchWrapper] set_gravity fallback failed: %s", exc)
            except Exception as exc:
                _logger.debug("[ScratchWrapper] set_gravity failed: %s", exc)
    if native_applied:
        _native_gravity_contexts.add(ctx.context_id)
    else:
        _native_gravity_contexts.discard(ctx.context_id)
    return True

def jump(power):
    power = _safe_float(power)
    ctx = _current_context()
    # Native impulse is preferred. Fallback apply_impulse updates the velocity cache.
    if ctx.context_id in _native_velocity_contexts:
        return apply_impulse(0.0, power, 0.0)
    vel = _velocity_list(ctx)
    vel[1] = max(0.0, vel[1]) + power
    return set_velocity(vel[0], vel[1], vel[2])

def bounce_axis(axis, factor=1.0):
    ctx = _current_context()
    axis = str(axis or 'X').upper()
    mapping = {'X': 0, 'Y': 1, 'Z': 2}
    idx = mapping.get(axis, 0)
    vel = _velocity_list(ctx)
    vel[idx] = -vel[idx] * _safe_float(factor, 1.0)
    set_velocity(vel[0], vel[1], vel[2])


def set_game_speed(value):
    _current_context().variables['game_speed'] = _safe_float(value, 1.0)


def game_speed():
    return _safe_float(_current_context().variables.get('game_speed', 1.0), 1.0)


# Appearance
def cartoonSet(index):
    if _actor_only("cartoonSet"):
        return
    _init_engine()
    ctx = _current_context()
    ctx.cartoon_index = int(index)
    if ctx.kinematics is not None:
        try:
            ctx.kinematics.set_animation(ctx.cartoon_index)
        except Exception:
            pass


def nextCartoon():
    if _actor_only("nextCartoon"):
        return
    _init_engine()
    ctx = _current_context()
    ctx.cartoon_index += 1
    if ctx.kinematics is not None:
        try:
            ctx.kinematics.set_animation(ctx.cartoon_index)
        except Exception:
            pass


def playCartoon():
    if _actor_only("playCartoon"):
        return
    _init_engine()
    ctx = _current_context()
    if ctx.kinematics is not None:
        try:
            ctx.kinematics.play_animation()
        except Exception:
            pass


def stopCartoon():
    if _actor_only("stopCartoon"):
        return
    _init_engine()
    ctx = _current_context()
    if ctx.kinematics is not None:
        try:
            ctx.kinematics.stop_animation()
        except Exception:
            pass


def resetCartoon():
    if _actor_only("resetCartoon"):
        return
    _init_engine()
    ctx = _current_context()
    ctx.cartoon_index = 0
    if ctx.kinematics is not None:
        try:
            ctx.kinematics.set_animation(0)
        except Exception:
            pass


def sizeAdd(ds):
    if _actor_only("sizeAdd"):
        return
    _init_engine()
    _current_context().size_val += float(ds)
    _sync_scale()


def sizeSet(sz):
    if _actor_only("sizeSet"):
        return
    _init_engine()
    _current_context().size_val = float(sz)
    _sync_scale()


def show(v=None):
    if _actor_only("show"):
        return
    _init_engine()
    ctx = _current_context()
    ctx.visible = True
    for target in (ctx.optics, ctx.actor):
        if target is not None and hasattr(target, "set_visible"):
            try:
                target.set_visible(True)
                return
            except Exception:
                pass


def hide(v=None):
    if _actor_only("hide"):
        return
    _init_engine()
    ctx = _current_context()
    ctx.visible = False
    for target in (ctx.optics, ctx.actor):
        if target is not None and hasattr(target, "set_visible"):
            try:
                target.set_visible(False)
                return
            except Exception:
                pass


def cartoon():
    _init_engine()
    return _current_context().cartoon_index


def size():
    _init_engine()
    return _current_context().size_val


def set_color(r, g, b):
    """设置物体漫反射颜色（Disney Principled BRDF diffuse）"""
    if _actor_only("set_color"):
        return
    _init_engine()
    ctx = _current_context()
    color = [float(r), float(g), float(b)]
    for target in (ctx.optics, ctx.actor):
        if target is not None and hasattr(target, 'set_diffuse'):
            try:
                target.set_diffuse(color)
                return
            except Exception:
                pass
    _logger.debug("[ScratchWrapper] set_color: no optics target available")


def set_alpha(alpha):
    if _actor_only("set_alpha"):
        return False
    _init_engine()
    ctx = _current_context()
    value = max(0.0, min(1.0, _safe_float(alpha, 1.0)))
    ctx.alpha = value
    for target in (ctx.optics, ctx.actor):
        if target is None:
            continue
        for method_name in ('set_alpha', 'set_opacity'):
            method = getattr(target, method_name, None)
            if callable(method):
                try:
                    method(value)
                    return True
                except Exception:
                    pass
    return False



# Detect
def update_key_state(key, pressed):
    _current_context().key_state[key] = bool(pressed)


def update_mouse_state(pressed, x, y):
    ctx = _current_context()
    ctx.mouse_pressed = bool(pressed)
    ctx.mouse_x = float(x)
    ctx.mouse_y = float(y)


def _norm_name(name) -> str:
    return str(name or "").strip().lower()


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


class _VirtualActor:
    """Small Python-side actor used when the native engine has no spawn/delete API."""

    def __init__(self, name, position=None, tag="", template=""):
        self.name = str(name or "")
        self.actor_name = self.name
        self.template = str(template or "")
        self.tag = str(tag or "")
        self.visible = True
        pos = position or [0.0, 0.0, 0.0]
        self._position = [
            _safe_float(pos[0] if len(pos) > 0 else 0.0),
            _safe_float(pos[1] if len(pos) > 1 else 0.0),
            _safe_float(pos[2] if len(pos) > 2 else 0.0),
        ]

    def get_name(self):
        return self.name

    def get_position(self):
        return list(self._position)

    def set_position(self, *args):
        pos = args[0] if len(args) == 1 and isinstance(args[0], (list, tuple)) else args
        if len(pos) >= 3:
            self._position = [_safe_float(pos[0]), _safe_float(pos[1]), _safe_float(pos[2])]

    def set_visible(self, value):
        self.visible = bool(value)

    def get_aabb(self):
        x, y, z = self._position
        return (x - 0.5, y - 0.5, z - 0.5, x + 0.5, y + 0.5, z + 0.5)


def _object_name(actor) -> str:
    if actor is None:
        return ""
    for attr in ('name', 'actor_name', 'route'):
        value = getattr(actor, attr, None)
        if value:
            return str(value)
    getter = getattr(actor, 'get_name', None)
    if callable(getter):
        try:
            return str(getter() or "")
        except Exception:
            pass
    return ""


def _runtime_scene():
    _init_engine()
    ctx = _current_context()
    if ctx.scene is not None:
        return ctx.scene
    try:
        from CoronaCore.core.managers import scene_manager
        if ctx.scene_name:
            scene = scene_manager.get(ctx.scene_name)
            if scene is not None:
                return scene
        names = scene_manager.list_all()
        if names:
            return scene_manager.get(names[0])
    except Exception:
        pass
    return None


def _runtime_scene_key(ctx=None):
    ctx = ctx or _current_context()
    scene = getattr(ctx, 'scene', None) or getattr(ctx, 'target_scene', None)
    return str(getattr(scene, 'route', '') or ctx.scene_name or '__default__')


def _shared_virtual_objects(ctx=None):
    key = _runtime_scene_key(ctx)
    with _context_lock:
        return _scene_virtual_objects.setdefault(key, {})


def _shared_deleted_objects(ctx=None):
    key = _runtime_scene_key(ctx)
    with _context_lock:
        return _scene_deleted_objects.setdefault(key, set())


def _shared_object_tags(ctx=None):
    key = _runtime_scene_key(ctx)
    with _context_lock:
        return _scene_object_tags.setdefault(key, {})


def _shared_variables(ctx=None):
    key = _runtime_scene_key(ctx)
    with _context_lock:
        return _scene_shared_variables.setdefault(key, {})


def _shared_lists(ctx=None):
    key = _runtime_scene_key(ctx)
    with _context_lock:
        return _scene_shared_lists.setdefault(key, {})


def _shared_declarations(ctx=None):
    key = _runtime_scene_key(ctx)
    with _context_lock:
        return _scene_shared_declarations.setdefault(key, {})


def _iter_scene_actors(scene=None):
    if scene is None:
        scene = _runtime_scene()
    if scene is None:
        return []
    for method_name in ('get_actors', 'get_all_actors'):
        method = getattr(scene, method_name, None)
        if callable(method):
            try:
                actors = method()
                return list(actors or [])
            except Exception:
                pass
    return list(getattr(scene, '_actors', []) or [])


def _iter_known_actors():
    ctx = _current_context()
    result = []
    scene = _runtime_scene()
    result.extend(_iter_scene_actors(scene))
    try:
        if ctx.actor is not None:
            result.append(ctx.actor)
    except Exception:
        pass
    result.extend(getattr(ctx, 'virtual_objects', {}).values())
    result.extend(_shared_virtual_objects(ctx).values())
    if not result:
        try:
            from CoronaCore.core.managers import scene_manager
            for item in scene_manager.get_all().values():
                result.extend(_iter_scene_actors(item))
        except Exception:
            pass
    deduped = []
    seen = set()
    for actor in result:
        if actor is None:
            continue
        key = _norm_name(_object_name(actor)) or str(id(actor))
        if key in seen or _is_actor_deleted(actor):
            continue
        seen.add(key)
        deduped.append(actor)
    return deduped


def _deleted_names(ctx=None):
    ctx = ctx or _current_context()
    names = {_norm_name(item) for item in getattr(ctx, 'deleted_objects', set())}
    names.update(_shared_deleted_objects(ctx))
    return names


def _is_actor_deleted(actor=None, name=None) -> bool:
    ctx = _current_context()
    names = _deleted_names(ctx)
    for candidate in (name, _object_name(actor)):
        if candidate and _norm_name(candidate) in names:
            return True
    return False


def _mark_deleted(actor=None, name=None):
    ctx = _current_context()
    for candidate in (name, _object_name(actor)):
        norm = _norm_name(candidate)
        if norm:
            ctx.deleted_objects.add(norm)
            _shared_deleted_objects(ctx).add(norm)
            _shared_virtual_objects(ctx).pop(norm, None)


def _resolve_actor(name):
    target = str(name or "").strip()
    if not target:
        return None
    _init_engine()
    ctx = _current_context()
    virtual = (
        getattr(ctx, 'virtual_objects', {}).get(_norm_name(target))
        or _shared_virtual_objects(ctx).get(_norm_name(target))
    )
    if virtual is not None:
        return None if _is_actor_deleted(virtual, target) else virtual
    current_name = ctx.actor_name or _object_name(ctx.actor)
    if ctx.actor is not None and _norm_name(current_name) == _norm_name(target):
        return None if _is_actor_deleted(ctx.actor, target) else ctx.actor
    scene = _runtime_scene()
    if scene is not None and hasattr(scene, 'find_actor'):
        try:
            actor = scene.find_actor(target)
            if actor is None and isinstance(scene, _NativeEditorSceneProxy) and scene.refresh():
                actor = scene.find_actor(target)
            if actor is not None:
                return None if _is_actor_deleted(actor, target) else actor
        except Exception:
            pass
    try:
        from CoronaCore.core.managers import scene_manager
        actor = scene_manager.find_actor(target)
        if actor is not None:
            return None if _is_actor_deleted(actor, target) else actor
    except Exception:
        pass
    for actor in _iter_known_actors():
        if _norm_name(_object_name(actor)) == _norm_name(target):
            return None if _is_actor_deleted(actor, target) else actor
    return None


def _current_actor():
    _init_engine()
    ctx = _current_context()
    if ctx.actor is None or _is_actor_deleted(ctx.actor, ctx.actor_name):
        return None
    return ctx.actor


def _aabb_tuple(raw):
    if raw is None:
        return None
    try:
        if isinstance(raw, dict):
            if 'min' in raw and 'max' in raw:
                mn, mx = raw['min'], raw['max']
                return tuple(float(v) for v in (mn[0], mn[1], mn[2], mx[0], mx[1], mx[2]))
            keys = ('min_x', 'min_y', 'min_z', 'max_x', 'max_y', 'max_z')
            if all(k in raw for k in keys):
                return tuple(float(raw[k]) for k in keys)
        if len(raw) >= 6:
            return tuple(float(raw[i]) for i in range(6))
    except Exception:
        return None
    return None


def _actor_aabb(actor):
    if actor is None or not hasattr(actor, 'get_aabb'):
        return None
    try:
        return _aabb_tuple(actor.get_aabb())
    except Exception:
        return None


def _actor_identity(actor):
    if actor is None:
        return ""
    for value in (getattr(actor, 'actor_guid', None), getattr(actor, 'handle', None), _object_name(actor)):
        if value not in (None, ""):
            return _norm_name(str(value))
    return str(id(actor))


def _set_actor_position(actor, pos):
    if actor is None:
        return False
    pos = [_safe_float(pos[0]), _safe_float(pos[1]), _safe_float(pos[2])]
    previous = _actor_position(actor)
    if previous is not None:
        _current_context().previous_actor_positions[_actor_identity(actor)] = list(previous)
    try:
        if hasattr(actor, 'set_position'):
            actor.set_position(pos)
            return True
        geom = getattr(actor, '_geometry', None)
        if geom is not None and hasattr(geom, 'set_position'):
            geom.set_position(pos)
            return True
    except Exception as exc:
        _logger.debug("[ScratchWrapper] set actor position failed: %s", exc)
    return False


def _actor_position(actor):
    if actor is None:
        return None
    for target in (actor, getattr(actor, '_geometry', None)):
        if target is not None and hasattr(target, 'get_position'):
            try:
                pos = target.get_position()
                return [float(pos[0]), float(pos[1]), float(pos[2])]
            except Exception:
                pass
    aabb = _actor_aabb(actor)
    if aabb is not None:
        return [
            (aabb[0] + aabb[3]) * 0.5,
            (aabb[1] + aabb[4]) * 0.5,
            (aabb[2] + aabb[5]) * 0.5,
        ]
    return None


def _aabb_overlap(a, b):
    return not (
        a[3] < b[0] or a[0] > b[3] or
        a[4] < b[1] or a[1] > b[4] or
        a[5] < b[2] or a[2] > b[5]
    )


def _position_distance(a, b):
    pa = _actor_position(a)
    pb = _actor_position(b)
    if pa is None or pb is None:
        return None
    import math as _math
    return _math.sqrt(
        (pa[0] - pb[0]) ** 2 +
        (pa[1] - pb[1]) ** 2 +
        (pa[2] - pb[2]) ** 2
    )


def _logical_collision_store(ctx=None):
    key = _runtime_scene_key(ctx)
    with _context_lock:
        return _scene_logical_collision_enabled.setdefault(key, {})


def _actor_logical_collision_enabled(actor) -> bool:
    if actor is None:
        return False
    return bool(_logical_collision_store().get(_actor_identity(actor), True))


def object_logical_collision_enabled(name=''):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    return _actor_logical_collision_enabled(actor)


def set_object_logical_collision(name, enabled=True):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    if actor is None:
        return False
    _logical_collision_store()[_actor_identity(actor)] = bool(enabled)
    return True


def set_object_native_physics(name, enabled=True):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    if actor is None:
        return False
    setter = getattr(actor, 'set_physics_enabled', None)
    if not callable(setter):
        setter = getattr(getattr(actor, '_mechanics', None), 'set_physics_enabled', None)
    if not callable(setter):
        raise RuntimeError(f'对象「{_object_name(actor)}」不支持原生物理开关')
    setter(bool(enabled))
    return True


def _segment_intersects_aabb(start, end, bounds):
    t_min, t_max = 0.0, 1.0
    for axis in range(3):
        delta = end[axis] - start[axis]
        if abs(delta) < 1e-9:
            if start[axis] < bounds[axis] or start[axis] > bounds[axis + 3]:
                return False
            continue
        inv = 1.0 / delta
        near = (bounds[axis] - start[axis]) * inv
        far = (bounds[axis + 3] - start[axis]) * inv
        if near > far:
            near, far = far, near
        t_min, t_max = max(t_min, near), min(t_max, far)
        if t_min > t_max:
            return False
    return True


def _swept_actor_touch(source, target, source_aabb, target_aabb):
    previous = _current_context().previous_actor_positions.get(_actor_identity(source))
    current = _actor_position(source)
    if previous is None or current is None or source_aabb is None or target_aabb is None:
        return False
    half = [(source_aabb[i + 3] - source_aabb[i]) * 0.5 for i in range(3)]
    expanded = tuple(target_aabb[i] - half[i] for i in range(3)) + tuple(target_aabb[i + 3] + half[i] for i in range(3))
    return _segment_intersects_aabb(previous, current, expanded)


def _actors_touch(a, b) -> bool:
    if a is None or b is None or a is b or _is_actor_deleted(a) or _is_actor_deleted(b):
        return False
    if not _actor_logical_collision_enabled(a) or not _actor_logical_collision_enabled(b):
        return False
    aabb_a = _actor_aabb(a)
    aabb_b = _actor_aabb(b)
    if aabb_a is not None and aabb_b is not None:
        return _aabb_overlap(aabb_a, aabb_b) or _swept_actor_touch(a, b, aabb_a, aabb_b)
    dist = _position_distance(a, b)
    return bool(dist is not None and dist <= 1.0)


def _record_touch(actor):
    name = _object_name(actor)
    if name:
        _current_context().last_touch_object = name


def _actor_matches_tag(actor, tag) -> bool:
    tag_norm = _norm_name(tag)
    if not tag_norm or actor is None or _is_actor_deleted(actor):
        return False
    ctx = _current_context()
    name = _object_name(actor)
    shared_tags = _shared_object_tags(ctx)
    explicit = (ctx.object_tags.get(name) or ctx.object_tags.get(_norm_name(name))
                or shared_tags.get(name) or shared_tags.get(_norm_name(name))
                or getattr(actor, 'tag', None))
    if explicit is not None:
        return _norm_name(explicit) == tag_norm
    # Fallback tag match: object-name prefix, e.g. coin_01 matches coin.
    return _norm_name(name).startswith(tag_norm)


def touch(target):
    source = _current_actor()
    actor = _resolve_actor(target)
    hit = _actors_touch(source, actor)
    if hit:
        _record_touch(actor)
    return hit


def touch_any():
    """Return whether the current actor overlaps any other known actor."""
    source = _current_actor()
    if source is None:
        return False
    source_name = _norm_name(_object_name(source))
    for actor in _iter_known_actors():
        if actor is source:
            continue
        if source_name and _norm_name(_object_name(actor)) == source_name:
            continue
        if _actors_touch(source, actor):
            _record_touch(actor)
            return True
    return False


def touch_tag(tag):
    source = _current_actor()
    if source is None:
        return False
    for actor in _iter_known_actors():
        if actor is source or not _actor_matches_tag(actor, tag):
            continue
        if _actors_touch(source, actor):
            _record_touch(actor)
            return True
    return False


def last_touch_object():
    return _current_context().last_touch_object or ""


def distance(target):
    source = _current_actor()
    actor = _resolve_actor(target)
    dist = _position_distance(source, actor)
    return float(dist) if dist is not None else 0.0


# Object blocks backend

def object_hide(name):
    actor = _resolve_actor(name)
    if actor is None:
        return False
    try:
        if hasattr(actor, 'set_visible'):
            actor.set_visible(False)
            return True
    except Exception as exc:
        _logger.debug("[ScratchWrapper] object_hide failed: %s", exc)
    return False


def object_show(name):
    actor = _resolve_actor(name)
    if actor is None:
        return False
    try:
        if hasattr(actor, 'set_visible'):
            actor.set_visible(True)
            return True
    except Exception as exc:
        _logger.debug("[ScratchWrapper] object_show failed: %s", exc)
    return False


def object_delete(name):
    actor = _resolve_actor(name)
    actor_name = _object_name(actor) if actor is not None else str(name or '').strip()
    if not actor_name:
        return False
    native_deleted = False
    scene = _runtime_scene()
    try:
        from CoronaCore.core.corona_editor import CoronaEditor
        remove_actor = getattr(CoronaEditor.CoronaEngine, 'remove_editor_actor', None)
        if callable(remove_actor) and scene is not None:
            raw = remove_actor(getattr(scene, 'route', ''), actor_name)
            result = _json.loads(raw) if isinstance(raw, str) else raw
            native_deleted = not isinstance(result, dict) or result.get('status') in ('success', 'ok')
            if not native_deleted:
                _logger.warning("[ScratchWrapper] native delete rejected %s: %r", actor_name, result)
    except Exception as exc:
        _logger.warning("[ScratchWrapper] native delete failed for %s: %s", actor_name, exc)

    _mark_deleted(actor, actor_name)
    if actor is not None:
        try:
            if hasattr(actor, 'set_visible'):
                actor.set_visible(False)
        except Exception:
            pass
    if scene is not None and native_deleted and hasattr(scene, '_notify_scene_tree_changed'):
        try:
            scene._notify_scene_tree_changed()
        except Exception:
            pass
    return bool(native_deleted or actor is not None)


def object_delete_last_touched():
    name = last_touch_object()
    return object_delete(name) if name else False


def object_set_position(name, x, y, z):
    actor = _resolve_actor(name)
    if actor is None:
        return False
    pos = [_safe_float(x), _safe_float(y), _safe_float(z)]
    moved = _set_actor_position(actor, pos)
    ctx = _current_context()
    if actor is ctx.actor:
        ctx.x, ctx.y, ctx.z = pos
    return moved


def _object_axis(name, axis):
    actor = _resolve_actor(name)
    pos = _actor_position(actor)
    if pos is None:
        return 0.0
    return float(pos[axis])


def object_x(name):
    return _object_axis(name, 0)


def object_y(name):
    return _object_axis(name, 1)


def object_z(name):
    return _object_axis(name, 2)


def object_exists(name):
    target = str(name or "").strip()
    if not target or _norm_name(target) in _deleted_names():
        return False
    return _resolve_actor(target) is not None


def object_set_tag(name, tag):
    ctx = _current_context()
    actor = _resolve_actor(name)
    actor_name = _object_name(actor) if actor is not None else str(name or "").strip()
    if not actor_name:
        return
    ctx.object_tags[actor_name] = str(tag or "")
    ctx.object_tags[_norm_name(actor_name)] = str(tag or "")
    shared_tags = _shared_object_tags(ctx)
    shared_tags[actor_name] = str(tag or "")
    shared_tags[_norm_name(actor_name)] = str(tag or "")


def object_count_tag(tag):
    return sum(1 for actor in _iter_known_actors() if _actor_matches_tag(actor, tag))


def _unique_object_name(base):
    ctx = _current_context()
    base = str(base or 'object').strip() or 'object'
    if not object_exists(base) and _norm_name(base) not in getattr(ctx, 'virtual_objects', {}):
        return base
    index = 1
    while True:
        candidate = f"{base}_{index:02d}"
        if not object_exists(candidate) and _norm_name(candidate) not in getattr(ctx, 'virtual_objects', {}):
            return candidate
        index += 1


def _try_native_spawn(scene, template, name, pos, template_actor=None):
    if scene is None:
        return None
    template_actor = template_actor or _resolve_actor(template)

    # First use any explicit Python scene factory exposed by the runtime.
    method_names = ('spawn_actor', 'create_actor', 'clone_actor', 'instantiate_actor', 'spawn', 'create', 'clone')
    for method_name in method_names:
        method = getattr(scene, method_name, None)
        if not callable(method):
            continue
        for args in ((template, name, pos), (template, name), (template_actor, name, pos), (template_actor, name)):
            if args[0] is None:
                continue
            try:
                actor = method(*args)
            except TypeError:
                continue
            except Exception as exc:
                _logger.debug("[ScratchWrapper] native spawn %s failed: %s", method_name, exc)
                continue
            if actor is not None:
                _set_actor_position(actor, pos)
                return actor

    # The editor already exposes native actor creation even though Scene has no create_actor method.
    try:
        from CoronaCore.core.corona_editor import CoronaEditor
        create_actor = getattr(CoronaEditor.CoronaEngine, 'create_editor_actor', None)
        if not callable(create_actor):
            return None
        route = getattr(template_actor, 'route', '') or str(template or '')
        actor_type = getattr(template_actor, 'actor_type', 'model') or 'model'
        if not route:
            return None
        actor_data = {
            'actor_name': name,
            'name': name,
            'actor_guid': '',
            'position': list(pos),
            'geometry': {'position': list(pos)},
            'skip_if_exists': False,
        }
        if template_actor is not None:
            try:
                source = template_actor.to_dict()
                geometry = dict(source.get('geometry') or {})
                geometry['position'] = list(pos)
                actor_data['geometry'] = geometry
                for key in ('collision', 'visible', 'mechanics'):
                    if key in source:
                        actor_data[key] = source[key]
            except Exception:
                pass
        raw = create_actor(
            getattr(scene, 'route', ''), route, actor_type,
            _json.dumps(actor_data, ensure_ascii=False),
        )
        result = _json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(result, dict) and result.get("status") == "error":
            _logger.warning("[ScratchWrapper] native spawn rejected %s: %r", name, result)
            return None
        if hasattr(scene, '_notify_scene_tree_changed'):
            scene._notify_scene_tree_changed()
        result_actor = result.get("actor") if isinstance(result, dict) and isinstance(result.get("actor"), dict) else None
        if isinstance(scene, _NativeEditorSceneProxy):
            scene.refresh()
        resolved = scene.find_actor(name) if hasattr(scene, 'find_actor') else None
        if resolved is not None:
            return resolved
        if isinstance(scene, _NativeEditorSceneProxy):
            # Native creation succeeded even if the refreshed tree has not propagated yet.
            source = template_actor.to_dict() if template_actor is not None and hasattr(template_actor, "to_dict") else {}
            proxy_data = dict(source)
            # A clone must never inherit the template's native identity.  The
            # create result may provide the new GUID/handle; otherwise leave
            # them empty until the next native scene refresh supplies them.
            proxy_data.pop("actor_guid", None)
            proxy_data.pop("handle", None)
            if result_actor:
                proxy_data.update(result_actor)
            proxy_data.update(name=name, actor_name=name, route=route, actor_type=actor_type)
            geometry = dict(proxy_data.get("geometry") or {})
            geometry["position"] = list(pos)
            proxy_data["geometry"] = geometry
            proxy = _NativeEditorActorProxy(scene, proxy_data)
            if not any(_object_name(item).casefold() == name.casefold() for item in scene.get_actors()):
                scene._actors.append(proxy)
            return proxy
        # Python scene fallback keeps generated objects usable when native scene sync is unavailable.
        proxy = _VirtualActor(name, pos, template=route)
        setattr(proxy, 'native_created', True)
        return proxy
    except Exception as exc:
        _logger.warning("[ScratchWrapper] create_editor_actor failed for %s: %s", name, exc)
        return None


def object_spawn(template, name, x, y, z):
    ctx = _current_context()
    template = str(template or '').strip() or 'object'
    name = str(name or '').strip() or _unique_object_name(template)
    pos = [_safe_float(x), _safe_float(y), _safe_float(z)]
    ctx.deleted_objects.discard(_norm_name(name))
    _shared_deleted_objects(ctx).discard(_norm_name(name))
    actor = _try_native_spawn(_runtime_scene(), template, name, pos)
    if actor is not None:
        actor_name = _object_name(actor) or name
        if isinstance(actor, _VirtualActor):
            ctx.virtual_objects[_norm_name(actor_name)] = actor
            _shared_virtual_objects(ctx)[_norm_name(actor_name)] = actor
        return actor_name
    if isinstance(_runtime_scene(), _NativeEditorSceneProxy):
        _logger.error("[ScratchWrapper] native object spawn failed: scene=%s template=%s name=%s",
                      _runtime_scene_key(ctx), template, name)
        return ""
    virtual = _VirtualActor(name, pos, template=template)
    ctx.virtual_objects[_norm_name(name)] = virtual
    _shared_virtual_objects(ctx)[_norm_name(name)] = virtual
    return name


def object_spawn_tag(template, tag, count, x, y, z, dx, dy, dz):
    count = max(0, _safe_int(count, 0))
    tag = str(tag or '').strip() or 'object'
    created = 0
    for index in range(count):
        name = _unique_object_name(f"{tag}_{index + 1:02d}")
        object_spawn(template, name,
                     _safe_float(x) + _safe_float(dx) * index,
                     _safe_float(y) + _safe_float(dy) * index,
                     _safe_float(z) + _safe_float(dz) * index)
        object_set_tag(name, tag)
        created += 1
    return created


def object_delete_raycast_hit():
    name = raycast_hit_object()
    return object_delete(name) if name else False


def object_move_tag(tag, dx, dy, dz):
    moved = 0
    offset = [_safe_float(dx), _safe_float(dy), _safe_float(dz)]
    for actor in list(_iter_known_actors()):
        if not _actor_matches_tag(actor, tag):
            continue
        pos = _actor_position(actor)
        if pos is None:
            continue
        new_pos = [pos[0] + offset[0], pos[1] + offset[1], pos[2] + offset[2]]
        if _set_actor_position(actor, new_pos):
            ctx = _current_context()
            if actor is ctx.actor:
                ctx.x, ctx.y, ctx.z = new_pos
            moved += 1
    return moved


def raycast_hit_tag(tag):
    name = raycast_hit_object()
    if not name:
        return False
    actor = _resolve_actor(name)
    if actor is not None:
        return _actor_matches_tag(actor, tag)
    tag_norm = _norm_name(tag)
    return bool(tag_norm and _norm_name(name).startswith(tag_norm))


def _object_passed_axis(name, threshold, axis):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    pos = _actor_position(actor)
    if pos is None:
        return False
    return float(pos[axis]) >= _safe_float(threshold)


def object_passed_x(name, x):
    return _object_passed_axis(name, x, 0)


def object_passed_z(name, z):
    return _object_passed_axis(name, z, 2)


def ground_below(distance):
    actor = _current_actor()
    pos = _actor_position(actor) if actor is not None else [_current_context().x, _current_context().y, _current_context().z]
    if pos is None:
        return False
    # A negative value is accepted as the same detection length in the downward direction.
    dist = abs(_safe_float(distance, 1.0))
    cache = _get_raycast_cache().copy()
    try:
        hit = raycast_hit(pos, [0.0, -1.0, 0.0], dist)
        hit_name = raycast_hit_object()
        self_name = _object_name(actor)
        if hit and hit_name and _norm_name(hit_name) != _norm_name(self_name):
            return True
    finally:
        _get_raycast_cache().update(cache)
    return pos[1] <= dist


# UI / demo state backend

def set_score(value):
    ctx = _current_context()
    ctx.variables['score'] = _safe_float(value)
    _logger.info("[ScratchWrapper] score = %s", ctx.variables['score'])


def add_score(delta):
    ctx = _current_context()
    ctx.variables['score'] = _safe_float(ctx.variables.get('score', 0.0)) + _safe_float(delta)
    _logger.info("[ScratchWrapper] score = %s", ctx.variables['score'])


def set_lives(value):
    ctx = _current_context()
    ctx.variables['lives'] = _safe_float(value)
    _logger.info("[ScratchWrapper] lives = %s", ctx.variables['lives'])


def add_lives(delta):
    ctx = _current_context()
    ctx.variables['lives'] = _safe_float(ctx.variables.get('lives', 0.0)) + _safe_float(delta)
    _logger.info("[ScratchWrapper] lives = %s", ctx.variables['lives'])


def lives():
    return _safe_float(_current_context().variables.get('lives', 0.0))


def set_countdown(seconds):
    ctx = _current_context()
    duration = max(0.0, _safe_float(seconds))
    ctx.countdown_started_at = _time.monotonic()
    ctx.countdown_duration = duration
    ctx.countdown_end_time = ctx.countdown_started_at + duration


def countdown_left():
    end_time = _safe_float(_current_context().countdown_end_time, 0.0)
    if end_time <= 0:
        return 0.0
    return max(0.0, end_time - _time.monotonic())


def countdown_finished():
    end_time = _safe_float(_current_context().countdown_end_time, 0.0)
    return bool(end_time > 0 and countdown_left() <= 0.0)


def node_graph_enter(node_id, node_name=""):
    ctx = _current_context()
    ctx.current_node_id = str(node_id or "")
    ctx.current_node_name = str(node_name or "")
    ctx.waiting_edge_id = ""
    ctx.waiting_edge_name = ""
    return True


def node_graph_waiting(edge_id="", edge_name=""):
    ctx = _current_context()
    ctx.waiting_edge_id = str(edge_id or "")
    ctx.waiting_edge_name = str(edge_name or "")
    return True


def runtime_context_snapshot(context_id):
    with _context_lock:
        ctx = _contexts.get(str(context_id or ""))
        completed = _completed_state_snapshots.get(str(context_id or ""))
    if ctx is not None:
        return runtime_state_snapshot(ctx)
    return dict(completed) if completed else None


def runtime_state_snapshot(ctx=None):
    ctx = ctx or _current_context()
    end_time = _safe_float(ctx.countdown_end_time, 0.0)
    countdown = max(0.0, end_time - _time.monotonic()) if end_time > 0 else 0.0
    variables = {}
    for marker in sorted(ctx.visible_variables):
        if marker.startswith('SCENE:'):
            name = marker[6:]
            variables[name] = _shared_variables(ctx).get(name, 0.0)
        else:
            variables[marker] = ctx.variables.get(marker, 0.0)
    lists = {}
    for marker in sorted(ctx.visible_lists):
        if marker.startswith('SCENE:'):
            name = marker[6:]
            lists[name] = _shared_lists(ctx).get(name, [])
        else:
            lists[marker] = ctx.list_values.get(marker, [])
    return {
        'context_id': ctx.context_id,
        'target_type': ctx.target_type,
        'scene_name': ctx.scene_name,
        'actor_name': ctx.actor_name,
        'score': _safe_float(ctx.variables.get('score', 0.0)),
        'lives': _safe_float(ctx.variables.get('lives', 0.0)),
        'countdown': countdown,
        'countdown_active': end_time > 0,
        'game_state': ctx.variables.get('game_state', ctx.game_state or ''),
        'variables': variables,
        'lists': lists,
        'mouse_locked': bool(ctx.mouse_locked),
        'binding_error': ctx.binding_error,
        'current_node_id': ctx.current_node_id,
        'current_node_name': ctx.current_node_name,
        'waiting_edge_id': ctx.waiting_edge_id,
        'waiting_edge_name': ctx.waiting_edge_name,
    }


def runtime_state_snapshots():
    live = {ctx.context_id: runtime_state_snapshot(ctx) for ctx in _live_contexts()}
    with _context_lock:
        completed = dict(_completed_state_snapshots)
    completed.update(live)
    return list(completed.values())


def clear_runtime_state_snapshots():
    with _context_lock:
        _completed_state_snapshots.clear()
        _scene_virtual_objects.clear()
        _scene_deleted_objects.clear()
        _scene_object_tags.clear()
        _scene_shared_variables.clear()
        _scene_shared_lists.clear()
        _scene_shared_declarations.clear()
        _scene_logical_collision_enabled.clear()


def game_win():
    ctx = _current_context()
    ctx.game_state = 'win'
    ctx.variables['game_state'] = 'win'
    _logger.info("[ScratchWrapper] game win; score=%s", ctx.variables.get('score', 0.0))
    ctx.stop_requested = True
    raise SystemExit(0)


def game_over():
    ctx = _current_context()
    ctx.game_state = 'over'
    ctx.variables['game_state'] = 'over'
    _logger.info("[ScratchWrapper] game over; score=%s", ctx.variables.get('score', 0.0))
    ctx.stop_requested = True
    raise SystemExit(0)


def ask(question):
    _logger.info("[ScratchWrapper] ask: %s", question)
    try:
        return input(question)
    except (EOFError, OSError):
        return ""


def keyboard(key):
    return _current_context().key_state.get(key, False)


def keyboard0(key):
    return not _current_context().key_state.get(key, False)


def mouse1():
    return _current_context().mouse_pressed


def mouse0():
    return not _current_context().mouse_pressed


def attribute(name):
    _init_engine()
    ctx = _current_context()
    values = {
        "X": ctx.x,
        "Y": ctx.y,
        "Z": ctx.z,
        "SIZE": ctx.size_val,
        "DIRECTION": ctx.rot_y,
        "ROTX": ctx.rot_x,
        "ROTY": ctx.rot_y,
        "ROTZ": ctx.rot_z,
        "NAME": ctx.actor_name or ctx.context_id,
        "ID": ctx.context_id,
    }
    return values.get(name, 0.0)


# ── Raycast (射击命中检测) ──

_raycast_cache = {}  # context_id → {hit, distance, object, point}


def _get_raycast_cache():
    """获取当前上下文的射线检测结果缓存"""
    ctx_id = _current_context().context_id
    if ctx_id not in _raycast_cache:
        _raycast_cache[ctx_id] = {
            'hit': False, 'distance': 0.0, 'object': '', 'point': (0.0, 0.0, 0.0)
        }
    return _raycast_cache[ctx_id]


def raycast_hit(origin, direction, max_dist=100.0):
    """执行射线检测，返回是否命中。结果缓存供 raycast_distance 等查询。"""
    cache = _get_raycast_cache()
    try:
        import corona_engine as _ce
        if hasattr(_ce, 'ray_cast'):
            result = _ce.ray_cast(origin, direction, float(max_dist))
            cache['hit'] = bool(result.hit)
            if result.hit:
                cache['distance'] = float(result.distance)
                cache['object'] = str(getattr(result, 'handle', ''))
                cache['point'] = (
                    float(result.point[0]) if result.point else 0.0,
                    float(result.point[1]) if result.point else 0.0,
                    float(result.point[2]) if result.point else 0.0,
                )
            else:
                cache['distance'] = float(max_dist)
                cache['object'] = ''
                cache['point'] = (0.0, 0.0, 0.0)
            return cache['hit']
    except Exception as exc:
        _logger.debug("[ScratchWrapper] raycast engine fallback: %s", exc)

    # Fallback: manually test all known actors, including Python virtual objects.
    cache['hit'] = False
    cache['distance'] = float(max_dist)
    cache['object'] = ''
    cache['point'] = (0.0, 0.0, 0.0)
    try:
        actors = _iter_known_actors()
        origin_vec = [float(origin[0]), float(origin[1]), float(origin[2])]
        dir_vec = [float(direction[0]), float(direction[1]), float(direction[2])]
        import math as _math
        mag = _math.sqrt(dir_vec[0]**2 + dir_vec[1]**2 + dir_vec[2]**2)
        if mag > 0:
            dir_vec = [d / mag for d in dir_vec]
        closest = float(max_dist)
        for actor in actors:
            if _is_actor_deleted(actor):
                continue
            aabb = _actor_aabb(actor)
            if aabb is None:
                continue
            if actor is _current_context().actor and all(aabb[i] <= origin_vec[i] <= aabb[i + 3] for i in range(3)):
                continue
            t = _ray_aabb_intersect(origin_vec, dir_vec, aabb)
            if t is not None and 0 < t < closest:
                closest = t
                cache['hit'] = True
                cache['distance'] = closest
                cache['object'] = _object_name(actor)
                cache['point'] = (
                    origin_vec[0] + dir_vec[0] * closest,
                    origin_vec[1] + dir_vec[1] * closest,
                    origin_vec[2] + dir_vec[2] * closest,
                )
    except Exception as exc:
        _logger.debug("[ScratchWrapper] raycast fallback failed: %s", exc)
    return cache['hit']


def _ray_aabb_intersect(origin, direction, aabb):
    """射线-AABB 相交检测（slab 方法），返回 t 或 None"""
    t_min = float('-inf')
    t_max = float('inf')
    for i in range(3):
        if abs(direction[i]) < 1e-10:
            if origin[i] < aabb[i] or origin[i] > aabb[i + 3]:
                return None
        else:
            t1 = (aabb[i] - origin[i]) / direction[i]
            t2 = (aabb[i + 3] - origin[i]) / direction[i]
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)
    if t_min > t_max or t_max < 0:
        return None
    return t_min if t_min >= 0 else t_max


def raycast_distance():
    """获取最近一次射线检测的命中距离"""
    return _get_raycast_cache()['distance']


def raycast_hit_object():
    """获取最近一次射线检测命中的物体标识"""
    return _get_raycast_cache()['object']


def raycast_hit_point_x():
    """获取命中点 X 坐标"""
    return float(_get_raycast_cache()['point'][0])


def raycast_hit_point_y():
    """获取命中点 Y 坐标"""
    return float(_get_raycast_cache()['point'][1])


def raycast_hit_point_z():
    """获取命中点 Z 坐标"""
    return float(_get_raycast_cache()['point'][2])


# Control
def _tick_runtime_physics_auto():
    if getattr(_tls, 'physics_ticking', False):
        return
    ctx = _current_context()
    now = _time.monotonic()
    if ctx.last_physics_time <= 0:
        ctx.last_physics_time = now
        return
    dt = min(0.1, max(0.0, now - ctx.last_physics_time))
    ctx.last_physics_time = now
    if dt > 0:
        _tls.physics_ticking = True
        try:
            _tick_runtime_physics(dt)
        finally:
            _tls.physics_ticking = False


def check_stop():
    if _current_context().stop_requested:
        raise SystemExit(0)
    _tick_runtime_physics_auto()


def loop_yield(frame_seconds=1.0 / 60.0):
    """Pace tight runtime loops so native calls and stop requests stay responsive."""
    ctx = _current_context()
    check_stop()
    interval = max(0.0, _safe_float(frame_seconds, 1.0 / 60.0))
    now = _time.monotonic()
    if ctx.last_loop_yield_time > 0.0 and interval > 0.0:
        remaining = ctx.last_loop_yield_time + interval - now
        while remaining > 0.0:
            if ctx.stop_requested:
                raise SystemExit(0)
            _time.sleep(min(0.005, remaining))
            remaining = ctx.last_loop_yield_time + interval - _time.monotonic()
    else:
        _time.sleep(0)
    ctx.last_loop_yield_time = _time.monotonic()
    check_stop()


def wait(seconds):
    remaining = max(0.0, _safe_float(seconds))
    while remaining > 0:
        check_stop()
        step = min(0.1, remaining)
        _time.sleep(step)
        remaining -= step
    check_stop()


def stop(option):
    ctx = _current_context()
    normalized = str(option or 'CURRENT_SCRIPT').upper()
    if normalized in ('ALL_SCRIPTS', 'ALL'):
        request_stop_all()
    elif normalized == 'OTHER_SCRIPTS_OF_ACTOR':
        with _context_lock:
            peers = list(_contexts.values())
        for peer in peers:
            if peer is ctx or peer.context_id == 'default':
                continue
            if peer.scene_name == ctx.scene_name and peer.actor_name == ctx.actor_name:
                peer.stop_requested = True
        return True
    elif normalized in ('CURRENT_SCRIPT', 'CURRENT'):
        # The editor's stop action restores the pre-run scene snapshot. Mark this
        # exit explicitly so the backend can coordinate all related threads and
        # run the same stop-and-restore flow instead of merely ending this context.
        ctx.game_state = 'stop_restore'
        ctx.variables['game_state'] = 'stop_restore'
    ctx.stop_requested = True
    raise SystemExit(0)


def restart_level():
    ctx = _current_context()
    ctx.game_state = 'restart'
    ctx.variables['game_state'] = 'restart'
    ctx.stop_requested = True
    raise SystemExit(0)


def _run_bound_handler(ctx, handler, label):
    try:
        with using_context(ctx):
            handler()
    except SystemExit:
        pass
    except Exception:
        _logger.exception("[ScratchWrapper] %s handler failed in %s", label, ctx.context_id)


def _run_tracked_handler(ctx, handler, label):
    try:
        _run_bound_handler(ctx, handler, label)
    finally:
        current = _threading.current_thread()
        with _context_lock:
            threads = _handler_threads.get(ctx.context_id, [])
            alive = [thread for thread in threads if thread is not current and thread.is_alive()]
            if alive:
                _handler_threads[ctx.context_id] = alive
            else:
                _handler_threads.pop(ctx.context_id, None)


def active_child_threads(context_ids=None):
    """Return live broadcast/clone child threads for coordinated shutdown."""
    wanted = {str(value) for value in (context_ids or []) if str(value)}

    def belongs_to_requested_context(context_id):
        if not wanted:
            return True
        # Clone contexts use ``<parent>:clone:<name>`` as their context id. A
        # broadcast handler started by a clone is therefore tracked under the
        # clone id rather than the preview target id. Include those descendants
        # so an already-completed clone cannot keep modifying the restored scene.
        return any(
            context_id == parent_id or context_id.startswith(parent_id + ":clone:")
            for parent_id in wanted
        )

    found = []
    with _context_lock:
        for mapping in (_clone_threads, _handler_threads):
            for context_id, threads in list(mapping.items()):
                alive = [thread for thread in threads if thread and thread.is_alive()]
                if alive:
                    mapping[context_id] = alive
                    if belongs_to_requested_context(context_id):
                        found.extend(alive)
                else:
                    mapping.pop(context_id, None)
    return list(dict.fromkeys(found))


def cloneStart():
    """Compatibility marker. Generated code registers a clone handler directly."""
    return bool(_current_context().current_clone_name)


def _run_clone_context(child, handler, parent_context_id):
    try:
        _run_bound_handler(child, handler, 'clone')
    finally:
        release_context(child)
        current = _threading.current_thread()
        with _context_lock:
            threads = _clone_threads.get(parent_context_id, [])
            _clone_threads[parent_context_id] = [thread for thread in threads if thread is not current]
            if not _clone_threads[parent_context_id]:
                _clone_threads.pop(parent_context_id, None)


def clone(name):
    parent = _current_context()
    template = str(name or "").strip() or str(parent.actor_name or "").strip()
    if not template:
        raise RuntimeError("\u514b\u9686\u5931\u8d25\uff1a\u8bf7\u8f93\u5165\u6a21\u677f\u7269\u4f53\u540d\u79f0")

    scene = _runtime_scene()
    native_scene = isinstance(scene, _NativeEditorSceneProxy)
    template_actor = _resolve_actor(template)
    if native_scene:
        scene.refresh()
        candidates = [actor for actor in scene.get_actors() if _actor_matches(actor, template)]
        if len(candidates) > 1:
            names = ", ".join(_object_name(actor) for actor in candidates)
            raise RuntimeError(
                f"\u514b\u9686\u5931\u8d25\uff1a\u6a21\u677f\u300c{template}\u300d\u5339\u914d\u5230\u591a\u4e2a\u7269\u4f53\uff1a{names}"
            )
        template_actor = candidates[0] if candidates else None
        if template_actor is None:
            scene_name = getattr(scene, "route", "") or parent.scene_name or "(\u672a\u77e5\u573a\u666f)"
            raise RuntimeError(
                f"\u514b\u9686\u5931\u8d25\uff1a\u573a\u666f\u300c{scene_name}\u300d\u4e2d\u672a\u627e\u5230\u6a21\u677f\u7269\u4f53\u300c{template}\u300d"
            )

    pos = _actor_position(template_actor) if template_actor is not None else None
    pos = pos or [parent.x, parent.y, parent.z]
    template_name = _object_name(template_actor) if template_actor is not None else template
    template_name = template_name or template
    clone_name = _unique_object_name(f"{template_name}_clone")

    if native_scene:
        source = template_actor.to_dict() if hasattr(template_actor, "to_dict") else {}
        template_route = str(
            source.get("route") or source.get("path") or source.get("model") or ""
        ).strip()
        if not template_route:
            raise RuntimeError(
                f"\u514b\u9686\u5931\u8d25\uff1a\u5df2\u627e\u5230\u300c{template_name}\u300d\uff0c\u4f46\u8d44\u6e90\u8def\u5f84\u4e3a\u7a7a"
            )
        created_actor = _try_native_spawn(
            scene, template_route, clone_name, pos, template_actor=template_actor
        )
        if created_actor is None or isinstance(created_actor, _VirtualActor):
            raise RuntimeError(
                f"\u514b\u9686\u5931\u8d25\uff1a\u5df2\u627e\u5230\u300c{template_name}\u300d\uff0c\u4f46\u539f\u751f\u5bf9\u8c61\u521b\u5efa\u5931\u8d25\uff0c\u8d44\u6e90\u8def\u5f84\u4e3a\u300c{template_route}\u300d"
            )
        created_name = _object_name(created_actor) or clone_name
    else:
        template_route = str(
            getattr(template_actor, "route", "") or getattr(template_actor, "path", "") or template
        ).strip()
        created_name = object_spawn(template_route, clone_name, pos[0], pos[1], pos[2])

    handler = parent.clone_start_handler
    if callable(handler):
        child = create_context(
            context_id=f"{parent.context_id}:clone:{created_name}",
            target_type="actor",
            scene_name=parent.scene_name,
            actor_name=created_name,
        )
        child.current_clone_name = created_name
        if native_scene:
            scene.refresh()
        actor = scene.find_actor(created_name) if hasattr(scene, "find_actor") else _resolve_actor(created_name)
        if actor is None and _object_name(created_actor).casefold() == created_name.casefold():
            actor = created_actor
        if actor is not None:
            child.actor = actor
            child.target_actor = actor
            child.scene = scene or _runtime_scene()
            child.target_scene = child.scene
            child.initialized = True
        thread = _threading.Thread(
            target=_run_clone_context,
            args=(child, handler, parent.context_id),
            daemon=True,
            name=f"scratch-clone-{created_name}",
        )
        with _context_lock:
            _clone_threads.setdefault(parent.context_id, []).append(thread)
        thread.start()
    return created_name


def deleteClone():
    ctx = _current_context()
    if not ctx.current_clone_name:
        return False
    deleted = object_delete(ctx.current_clone_name)
    ctx.stop_requested = True
    raise SystemExit(0)


def _project_scene_routes():
    try:
        from CoronaCore.utils.proejct_utils import get_project_scenes
        from utils.settings import settings_manager
        root = settings_manager.active_project_path
        if root:
            routes = get_project_scenes(str(_Path(root) / 'project.ini'))
            if routes:
                return routes
    except Exception:
        pass
    try:
        from CoronaCore.core.managers import scene_manager
        return list(scene_manager.list_all())
    except Exception:
        return []


def _resolve_scene_route(name):
    target = str(name or '').strip().replace('\\', '/')
    if not target:
        return ''
    target_stem = _Path(target).stem.lower()
    for route in _project_scene_routes():
        normalized = str(route).replace('\\', '/')
        if normalized.lower() == target.lower() or _Path(normalized).stem.lower() == target_stem:
            return route
    return target


def setScene(name):
    route = _resolve_scene_route(name)
    if not route:
        return False
    try:
        from CoronaCore.core.managers import scene_manager
        ctx = _current_context()
        current = _runtime_scene()
        if current is not None and getattr(current, 'route', '') != route:
            if hasattr(current, 'set_enabled'):
                current.set_enabled(False)
        scene = scene_manager.get_or_create(route)
        if scene is None:
            return False
        if hasattr(scene, 'set_enabled'):
            scene.set_enabled(True)
        ctx.scene_name = getattr(scene, 'route', route)
        ctx.target_scene_name = ctx.scene_name
        ctx.scene = scene
        ctx.target_scene = scene
        ctx.actor = None
        ctx.target_actor = None
        ctx.initialized = ctx.target_type == 'project'
        return True
    except Exception as exc:
        _logger.warning("[ScratchWrapper] setScene failed for %s: %s", route, exc)
        return False


def nextScene():
    routes = _project_scene_routes()
    if not routes:
        return False
    current = getattr(_runtime_scene(), 'route', '') or _current_context().scene_name
    try:
        index = routes.index(current)
    except ValueError:
        index = -1
    return setScene(routes[(index + 1) % len(routes)])


# Event
def gameStart():
    _current_context().variables['game_started'] = True
    return True


def RB(message):
    """Compatibility query for hand-written scripts."""
    return str(message or '') in _current_context().broadcast_handlers


def _broadcast(message, wait_for_handlers):
    key = str(message or '')
    calls = []
    for ctx in _live_contexts():
        for handler in list(ctx.broadcast_handlers.get(key, [])):
            thread = _threading.Thread(
                target=_run_tracked_handler,
                args=(ctx, handler, f"broadcast:{key}"),
                daemon=True,
                name=f"scratch-broadcast-{ctx.context_id}",
            )
            with _context_lock:
                _handler_threads.setdefault(ctx.context_id, []).append(thread)
            calls.append(thread)
            thread.start()
    if wait_for_handlers:
        for thread in calls:
            thread.join()
    return len(calls)


def broadcast(message):
    return _broadcast(message, False)


def broadcastWait(message):
    return _broadcast(message, True)


# Math / variables / lists
def random(a, b):
    return _random.uniform(float(a), float(b))


def var_add(name, value, scope='OBJECT'):
    return data_add(scope, name, value)


def var_set(name, value, scope='OBJECT'):
    return data_set(scope, name, value)


def var_show(name, scope='OBJECT'):
    key = str(name or '')
    marker = f'SCENE:{key}' if _normalize_data_scope(scope) == 'SCENE' else key
    _current_context().visible_variables.add(marker)
    return True


def var_hide(name, scope='OBJECT'):
    key = str(name or '')
    marker = f'SCENE:{key}' if _normalize_data_scope(scope) == 'SCENE' else key
    _current_context().visible_variables.discard(marker)
    return True


def list_show(name, value=None, scope='OBJECT'):
    ctx, key = _current_context(), str(name or '')
    marker = f'SCENE:{key}' if _normalize_data_scope(scope) == 'SCENE' else key
    ctx.visible_lists.add(marker)
    if value is not None:
        data_list_define(scope, key, value)
    return True


def list_hide(name, scope='OBJECT'):
    key = str(name or '')
    marker = f'SCENE:{key}' if _normalize_data_scope(scope) == 'SCENE' else key
    _current_context().visible_lists.discard(marker)
    return True


# Scoped data used by node graphs and concurrent scene scripts.

def _normalize_data_scope(scope):
    value = str(scope or 'OBJECT').strip().upper()
    return 'SCENE' if value in ('SCENE', 'CURRENT_SCENE') else 'OBJECT'


def _data_store(scope, ctx=None):
    ctx = ctx or _current_context()
    return _shared_variables(ctx) if _normalize_data_scope(scope) == 'SCENE' else ctx.variables


def _list_store(scope, ctx=None):
    ctx = ctx or _current_context()
    return _shared_lists(ctx) if _normalize_data_scope(scope) == 'SCENE' else ctx.list_values


def _copy_runtime_value(value):
    if isinstance(value, (dict, list, tuple, set)):
        try:
            return _json.loads(_json.dumps(value, ensure_ascii=False))
        except Exception:
            return dict(value) if isinstance(value, dict) else list(value)
    return value


def data_define(scope, name, value):
    key = str(name or '').strip()
    if not key:
        return False
    normalized = _normalize_data_scope(scope)
    with _context_lock:
        store = _data_store(normalized)
        if normalized == 'SCENE':
            declarations = _shared_declarations()
            signature = ('value', type(value).__name__, repr(value))
            previous = declarations.get(key)
            if previous is not None and previous != signature:
                raise RuntimeError(f'scene variable {key!r} has conflicting declarations')
            declarations.setdefault(key, signature)
        store.setdefault(key, _copy_runtime_value(value))
    return True


def data_get(scope, name, default=None):
    with _context_lock:
        return _data_store(scope).get(str(name or '').strip(), default)


def data_set(scope, name, value):
    key = str(name or '').strip()
    if not key:
        return False
    with _context_lock:
        _data_store(scope)[key] = _copy_runtime_value(value)
    return True


def data_add(scope, name, delta):
    key = str(name or '').strip()
    if not key:
        return 0.0
    with _context_lock:
        store = _data_store(scope)
        store[key] = _safe_float(store.get(key, 0.0)) + _safe_float(delta)
        return store[key]


def data_exists(scope, name):
    with _context_lock:
        return str(name or '').strip() in _data_store(scope)


def _as_runtime_list(values):
    if values is None:
        return []
    if isinstance(values, list):
        return list(values)
    if isinstance(values, tuple):
        return list(values)
    if isinstance(values, str):
        return [values]
    try:
        return list(values)
    except TypeError:
        return [values]


def data_list_define(scope, name, values):
    key = str(name or '').strip()
    if not key:
        return False
    normalized = _normalize_data_scope(scope)
    value = _as_runtime_list(values)
    with _context_lock:
        store = _list_store(normalized)
        if normalized == 'SCENE':
            declarations = _shared_declarations()
            signature = ('list', type(value).__name__, repr(value))
            previous = declarations.get(key)
            if previous is not None and previous != signature:
                raise RuntimeError(f'scene list {key!r} has conflicting declarations')
            declarations.setdefault(key, signature)
        store.setdefault(key, value)
    return True


def data_list_add(scope, name, value):
    with _context_lock:
        values = _list_store(scope).setdefault(str(name or '').strip(), [])
        values.append(value)
        return len(values)


def data_list_insert(scope, name, index, value):
    with _context_lock:
        values = _list_store(scope).setdefault(str(name or '').strip(), [])
        idx = max(0, min(len(values), _safe_int(index, 1) - 1))
        values.insert(idx, value)
        return len(values)


def data_list_remove_index(scope, name, index):
    with _context_lock:
        values = _list_store(scope).setdefault(str(name or '').strip(), [])
        idx = _safe_int(index, 1) - 1
        if 0 <= idx < len(values):
            return values.pop(idx)
    return None


def data_list_remove_value(scope, name, value):
    with _context_lock:
        values = _list_store(scope).setdefault(str(name or '').strip(), [])
        try:
            values.remove(value)
            return True
        except ValueError:
            return False


def data_list_clear(scope, name):
    with _context_lock:
        _list_store(scope)[str(name or '').strip()] = []
    return True


def data_list_item(scope, name, index):
    with _context_lock:
        values = _list_store(scope).get(str(name or '').strip(), [])
        idx = _safe_int(index, 1) - 1
        return values[idx] if 0 <= idx < len(values) else None


def data_list_length(scope, name):
    with _context_lock:
        return len(_list_store(scope).get(str(name or '').strip(), []))


def data_list_contains(scope, name, value):
    with _context_lock:
        return value in _list_store(scope).get(str(name or '').strip(), [])


# One-shot collision, checkpoint, lane and demo helpers.

def _collision_normal(source, target):
    a, b = _actor_aabb(source), _actor_aabb(target)
    source_pos = _actor_position(source) or [0.0, 0.0, 0.0]
    target_pos = _actor_position(target) or [0.0, 0.0, 0.0]
    if a is not None and b is not None:
        overlaps = [min(a[i + 3], b[i + 3]) - max(a[i], b[i]) for i in range(3)]
        axis_index = min(range(3), key=lambda i: overlaps[i])
    else:
        delta = [abs(source_pos[i] - target_pos[i]) for i in range(3)]
        velocity = [abs(v) for v in _velocity_list()]
        axis_index = max(range(3), key=lambda i: velocity[i]) if any(velocity) else max(range(3), key=lambda i: delta[i])
    normal = [0.0, 0.0, 0.0]
    normal[axis_index] = -1.0 if source_pos[axis_index] < target_pos[axis_index] else 1.0
    return ('XYZ'[axis_index], normal)


def _remember_collision(source, target):
    axis, normal = _collision_normal(source, target)
    ctx = _current_context()
    ctx.last_collision_axis_value = axis
    ctx.last_collision_normal_value = normal
    ctx.last_collision_target_name = _object_name(target)


def touch_started(name, trigger_id):
    source, target = _current_actor(), _resolve_actor(name)
    current = {_actor_identity(target)} if _actors_touch(source, target) else set()
    key = f'object:{trigger_id}'
    previous = set(_current_context().touch_state.get(key, set()) or set())
    _current_context().touch_state[key] = current
    entered = current - previous
    if entered:
        _record_touch(target)
        _remember_collision(source, target)
    return bool(entered)


def touch_tag_started(tag, trigger_id):
    source = _current_actor()
    touched = []
    if source is not None:
        touched = [actor for actor in _iter_known_actors()
                   if actor is not source and _actor_matches_tag(actor, tag) and _actors_touch(source, actor)]
    current = {_actor_identity(actor) for actor in touched}
    key = f'tag:{trigger_id}'
    previous = set(_current_context().touch_state.get(key, set()) or set())
    _current_context().touch_state[key] = current
    entered = current - previous
    if entered:
        target = next((actor for actor in touched if _actor_identity(actor) in entered), touched[0])
        _record_touch(target)
        _remember_collision(source, target)
    return bool(entered)


def crossed_axis_once(name, axis, threshold, direction, trigger_id):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    pos = _actor_position(actor)
    if pos is None:
        return False
    axis_name = str(axis or 'X').upper()
    index = {'X': 0, 'Y': 1, 'Z': 2}.get(axis_name, 0)
    current, limit = pos[index], _safe_float(threshold)
    key = f'{trigger_id}:{_object_name(actor)}:{axis_name}'
    previous = _current_context().crossing_state.get(key)
    _current_context().crossing_state[key] = current
    if previous is None:
        return False
    mode = str(direction or 'GREATER').upper()
    crossed_negative = previous >= limit and current < limit
    crossed_positive = previous <= limit and current > limit
    if mode in ('ANY', 'BOTH', 'EITHER', '*'):
        return bool(crossed_negative or crossed_positive)
    if mode in ('LESS', 'LT', 'BELOW', 'NEGATIVE', '-'):
        return bool(crossed_negative)
    return bool(crossed_positive)


def outside_axis(name, axis, minimum, maximum):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    pos = _actor_position(actor)
    if pos is None:
        return False
    index = {'X': 0, 'Y': 1, 'Z': 2}.get(str(axis or 'X').upper(), 0)
    lo, hi = sorted((_safe_float(minimum), _safe_float(maximum)))
    return pos[index] < lo or pos[index] > hi


def inside_axis(name, axis, minimum, maximum):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    pos = _actor_position(actor)
    if pos is None:
        return False
    index = {'X': 0, 'Y': 1, 'Z': 2}.get(str(axis or 'X').upper(), 0)
    lo, hi = sorted((_safe_float(minimum), _safe_float(maximum)))
    return lo <= pos[index] <= hi


def inside_box(name, cx, cy, cz, sx, sy, sz):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    pos = _actor_position(actor)
    if pos is None:
        return False
    center = [_safe_float(cx), _safe_float(cy), _safe_float(cz)]
    half = [abs(_safe_float(sx)) * 0.5, abs(_safe_float(sy)) * 0.5, abs(_safe_float(sz)) * 0.5]
    return all(center[i] - half[i] <= pos[i] <= center[i] + half[i] for i in range(3))


def last_collision_axis():
    return _current_context().last_collision_axis_value or ''


def last_collision_normal(axis):
    index = {'X': 0, 'Y': 1, 'Z': 2}.get(str(axis or 'X').upper(), 0)
    return _safe_float(_current_context().last_collision_normal_value[index])


def bounce_last_collision(factor=1.0):
    ctx = _current_context()
    normal = list(ctx.last_collision_normal_value or [0.0, 0.0, 0.0])
    if not any(abs(v) > 1e-9 for v in normal):
        return False
    velocity = _velocity_list()
    dot = sum(velocity[i] * normal[i] for i in range(3))
    coefficient = max(0.0, _safe_float(factor, 1.0))
    reflected = [velocity[i] - (1.0 + coefficient) * dot * normal[i] for i in range(3)]
    source, target = _current_actor(), _resolve_actor(ctx.last_collision_target_name)
    source_box, target_box = _actor_aabb(source), _actor_aabb(target)
    if source_box is not None and target_box is not None:
        penetrations = [min(source_box[i + 3], target_box[i + 3]) - max(source_box[i], target_box[i]) for i in range(3)]
        axis = next((i for i, value in enumerate(normal) if abs(value) > 0.5), None)
        if axis is not None and penetrations[axis] >= 0:
            position = _actor_position(source)
            if position is not None:
                position[axis] += normal[axis] * (penetrations[axis] + 1e-3)
                _set_actor_position(source, position)
    return set_velocity(*reflected)


def stop_motion():
    return set_velocity(0.0, 0.0, 0.0)


def set_velocity_axis(axis, value):
    velocity = _velocity_list()
    index = {'X': 0, 'Y': 1, 'Z': 2}.get(str(axis or 'X').upper(), 0)
    velocity[index] = _safe_float(value)
    return set_velocity(*velocity)


def _actor_vector(actor, getter_name, fallback):
    getter = getattr(actor, getter_name, None) if actor is not None else None
    if callable(getter):
        try:
            value = list(getter())[:3]
            while len(value) < 3:
                value.append(fallback[len(value)])
            return [_safe_float(value[i], fallback[i]) for i in range(3)]
        except Exception:
            pass
    return list(fallback)


def _set_actor_vector(actor, setter_name, value):
    setter = getattr(actor, setter_name, None) if actor is not None else None
    if not callable(setter):
        return False
    try:
        setter(list(value))
        return True
    except TypeError:
        try:
            setter(*value)
            return True
        except Exception:
            return False
    except Exception:
        return False


def object_clamp_axis(name, axis, minimum, maximum):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    pos = _actor_position(actor)
    if actor is None or pos is None:
        return False
    index = {'X': 0, 'Y': 1, 'Z': 2}.get(str(axis or 'X').upper(), 0)
    lo, hi = sorted((_safe_float(minimum), _safe_float(maximum)))
    pos[index] = min(hi, max(lo, pos[index]))
    return _set_actor_position(actor, pos)


def object_save_checkpoint(name, checkpoint, save_velocity=True):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    if actor is None:
        return False
    key = f'{_norm_name(_object_name(actor))}:{str(checkpoint or "default")}'
    _current_context().checkpoints[key] = {
        'position': _actor_position(actor) or [0.0, 0.0, 0.0],
        'rotation': _actor_vector(actor, 'get_rotation', [0.0, 0.0, 0.0]),
        'scale': _actor_vector(actor, 'get_scale', [1.0, 1.0, 1.0]),
        'velocity': _velocity_list() if actor is _current_actor() and save_velocity else [0.0, 0.0, 0.0],
    }
    return True


def object_restore_checkpoint(name, checkpoint, clear_velocity=True):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    if actor is None:
        return False
    key = f'{_norm_name(_object_name(actor))}:{str(checkpoint or "default")}'
    state = _current_context().checkpoints.get(key)
    if not state:
        return False
    ok = _set_actor_position(actor, state['position'])
    _set_actor_vector(actor, 'set_rotation', state['rotation'])
    _set_actor_vector(actor, 'set_scale', state['scale'])
    if actor is _current_actor():
        set_velocity(0.0, 0.0, 0.0) if clear_velocity else set_velocity(*state['velocity'])
    return ok


def object_move_to_lane(name, axis, lane, origin, spacing):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    pos = _actor_position(actor)
    if actor is None or pos is None:
        return False
    index = {'X': 0, 'Z': 2}.get(str(axis or 'X').upper(), 0)
    pos[index] = _safe_float(origin) + _safe_int(lane, 0) * _safe_float(spacing, 1.0)
    return _set_actor_position(actor, pos)


def object_move_to_lane_smooth(name, axis, lane, origin, spacing, speed):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    pos = _actor_position(actor)
    if actor is None or pos is None:
        return False
    index = {'X': 0, 'Z': 2}.get(str(axis or 'X').upper(), 0)
    target = _safe_float(origin) + _safe_int(lane, 0) * _safe_float(spacing, 1.0)
    delta = target - pos[index]
    step = max(0.0, abs(_safe_float(speed, 5.0))) * 0.05
    if abs(delta) <= max(step, 1e-6):
        pos[index] = target
        _set_actor_position(actor, pos)
        return True
    pos[index] += step if delta > 0 else -step
    _set_actor_position(actor, pos)
    return False


def set_tag_velocity_axis(tag, axis, value):
    ctx = _current_context()
    key = f'{_norm_name(tag)}:{str(axis or "X").upper()}'
    now = _time.monotonic()
    previous = ctx.tag_velocity_times.get(key, now - 0.05)
    ctx.tag_velocity_times[key] = now
    dt = min(0.1, max(0.0, now - previous))
    index = {'X': 0, 'Y': 1, 'Z': 2}.get(str(axis or 'X').upper(), 0)
    moved = 0
    for actor in _iter_known_actors():
        if not _actor_matches_tag(actor, tag):
            continue
        pos = _actor_position(actor)
        if pos is None:
            continue
        pos[index] += _safe_float(value) * dt
        if _set_actor_position(actor, pos):
            moved += 1
    return moved


def reset_crossed_once(name, trigger_id=''):
    target = _norm_name(str(name or '').strip())
    trigger = str(trigger_id or '')
    ctx = _current_context()
    removed = 0
    for key in list(ctx.crossing_state):
        if target and target not in _norm_name(key):
            continue
        if trigger and not key.startswith(f'{trigger}:'):
            continue
        ctx.crossing_state.pop(key, None)
        removed += 1
    return removed


def object_lane_index(name, axis, origin, spacing):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    pos, step = _actor_position(actor), _safe_float(spacing, 1.0)
    if pos is None or abs(step) < 1e-9:
        return 0
    index = {'X': 0, 'Z': 2}.get(str(axis or 'X').upper(), 0)
    return int(round((pos[index] - _safe_float(origin)) / step))


def object_set_random_position(name, cx, cy, cz, sx, sy, sz):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    if actor is None:
        return False
    center = [_safe_float(cx), _safe_float(cy), _safe_float(cz)]
    size = [abs(_safe_float(sx)), abs(_safe_float(sy)), abs(_safe_float(sz))]
    pos = [_random.uniform(center[i] - size[i] * 0.5, center[i] + size[i] * 0.5) for i in range(3)]
    return _set_actor_position(actor, pos)


def object_spawn_random_box(template, tag, count, cx, cy, cz, sx, sy, sz):
    created = 0
    for index in range(max(0, _safe_int(count))):
        name = _unique_object_name(f'{str(tag or "object")}_{index + 1:02d}')
        center = [_safe_float(cx), _safe_float(cy), _safe_float(cz)]
        size = [abs(_safe_float(sx)), abs(_safe_float(sy)), abs(_safe_float(sz))]
        pos = [_random.uniform(center[i] - size[i] * 0.5, center[i] + size[i] * 0.5) for i in range(3)]
        spawned = object_spawn(template, name, *pos)
        if not spawned:
            raise RuntimeError(f'failed to spawn template {template!r}')
        object_set_tag(spawned, tag)
        created += 1
    return created


def _remember_tag_initial_positions(tag):
    ctx, key = _current_context(), _norm_name(tag)
    states = ctx.initial_tag_transforms.setdefault(key, {})
    for actor in _iter_known_actors():
        if _actor_matches_tag(actor, tag):
            states.setdefault(_norm_name(_object_name(actor)), list(_actor_position(actor) or [0.0, 0.0, 0.0]))
    return states


def object_scatter_tag(tag, cx, cy, cz, sx, sy, sz):
    _remember_tag_initial_positions(tag)
    return sum(1 for actor in _iter_known_actors() if _actor_matches_tag(actor, tag) and object_set_random_position(_object_name(actor), cx, cy, cz, sx, sy, sz))


def object_recycle_tag_axis(tag, axis, direction, boundary, reset_value, random_axis='', random_min=0, random_max=0):
    _remember_tag_initial_positions(tag)
    axis_index = {'X': 0, 'Y': 1, 'Z': 2}.get(str(axis or 'X').upper(), 0)
    random_index = {'X': 0, 'Y': 1, 'Z': 2}.get(str(random_axis or '').upper())
    mode, reset = str(direction or 'LESS').upper(), 0
    for actor in _iter_known_actors():
        if not _actor_matches_tag(actor, tag):
            continue
        pos = _actor_position(actor)
        if pos is None:
            continue
        crossed = pos[axis_index] < _safe_float(boundary) if mode in ('LESS', 'LT', '-') else pos[axis_index] > _safe_float(boundary)
        if not crossed:
            continue
        pos[axis_index] = _safe_float(reset_value)
        if random_index is not None:
            lo, hi = sorted((_safe_float(random_min), _safe_float(random_max)))
            pos[random_index] = _random.uniform(lo, hi)
        if _set_actor_position(actor, pos):
            reset_crossed_once(_object_name(actor))
            reset += 1
    return reset


def object_reset_tag(tag):
    states, restored = _current_context().initial_tag_transforms.get(_norm_name(tag), {}), 0
    for actor in _iter_known_actors():
        pos = states.get(_norm_name(_object_name(actor)))
        if pos is not None and _set_actor_position(actor, pos):
            restored += 1
    return restored


def object_count_active_tag(tag):
    return object_count_tag(tag)


def score():
    return _safe_float(_current_context().variables.get('score', 0.0))


def game_state():
    ctx = _current_context()
    return str(ctx.variables.get('game_state', ctx.game_state or ''))


def countdown_elapsed():
    ctx = _current_context()
    return 0.0 if ctx.countdown_started_at <= 0 else min(ctx.countdown_duration, max(0.0, _time.monotonic() - ctx.countdown_started_at))


def cooldown_ready(name, seconds, consume=True):
    ctx, key, now = _current_context(), str(name or '').strip() or 'default', _time.monotonic()
    ready = now >= _safe_float(ctx.cooldowns.get(key, 0.0))
    if ready and bool(consume):
        ctx.cooldowns[key] = now + max(0.0, _safe_float(seconds))
    return ready


def reset_cooldown(name):
    _current_context().cooldowns.pop(str(name or '').strip() or 'default', None)
    return True


def position_near(name, x, y, z, tolerance=0.1):
    actor = _resolve_actor(name) if str(name or '').strip() else _current_actor()
    position = _actor_position(actor)
    if position is None:
        return False
    target = [_safe_float(x), _safe_float(y), _safe_float(z)]
    tolerance = abs(_safe_float(tolerance, 0.1))
    return sum((position[i] - target[i]) ** 2 for i in range(3)) <= tolerance ** 2


def _mouse_pick_native():
    ctx = _current_context()
    if ctx.mouse_viewport_width <= 0 or ctx.mouse_viewport_height <= 0:
        raise RuntimeError('无法取得视口尺寸，不能执行 3D 鼠标拾取')
    scene_name = str(ctx.scene_name or ctx.target_scene_name or getattr(ctx.scene, 'route', '') or '')
    if not scene_name:
        raise RuntimeError('当前运行上下文没有绑定场景，不能执行鼠标拾取')
    payload = None
    try:
        from CoronaCore.core.editor_api import CoronaEditorApi
        for attempt in range(3):
            result = CoronaEditorApi.scene_tools.pick_actor(
                scene_name, ctx.mouse_viewport_x, ctx.mouse_viewport_y,
                ctx.mouse_viewport_width, ctx.mouse_viewport_height)
            payload = _native_payload(result) or result
            status = str(payload.get('status', '') if isinstance(payload, dict) else '').lower()
            if status != 'pending':
                break
            _time.sleep(0.035 * (attempt + 1))
    except Exception as exc:
        raise RuntimeError(f'原生鼠标拾取失败：{exc}') from exc
    if not isinstance(payload, dict) or str(payload.get('status', '')).lower() != 'success':
        ctx.last_mouse_pick_object = ''
        return ''
    actor_data = payload.get('actor') if isinstance(payload.get('actor'), dict) else {}
    name = str(actor_data.get('name') or actor_data.get('route') or '')
    ctx.last_mouse_pick_object = name
    return name


def mouse_pick_object():
    ctx = _current_context()
    if isinstance(_runtime_scene(), _NativeEditorSceneProxy):
        return _mouse_pick_native()
    hit = raycast_hit_object()
    ctx.last_mouse_pick_object = str(hit or '')
    return ctx.last_mouse_pick_object


def mouse_pick_hit_tag(tag):
    name = mouse_pick_object()
    actor = _resolve_actor(name)
    return bool(actor is not None and _actor_matches_tag(actor, tag))


def object_randomize_mouse_pick(cx, cy, cz, sx, sy, sz):
    name = _current_context().last_mouse_pick_object or mouse_pick_object()
    return bool(name) and object_set_random_position(name, cx, cy, cz, sx, sy, sz)


def object_delete_mouse_pick():
    name = _current_context().last_mouse_pick_object or mouse_pick_object()
    return bool(name) and object_delete(name)


# ── Audio ──

_audio_cache = {}  # name → resource_id (str)


def _ensure_audio(name):
    """Resolve project audio first, then editor bundled audio, returning a resource id."""
    key = str(name or '').strip()
    if key in _audio_cache:
        return _audio_cache[key]
    candidates = []
    raw_path = _Path(key)
    if raw_path.is_file():
        candidates.append(raw_path)
    try:
        from utils.settings import settings_manager
        project_root = settings_manager.active_project_path
    except Exception:
        project_root = None
    roots = []
    if project_root:
        project = _Path(project_root)
        roots.extend((project / 'Resource' / 'audio', project / 'assets' / 'audio', project / 'Audio'))
    roots.append(_Path(__file__).resolve().parents[2] / 'assets' / 'audio')
    suffixes = ('',) if raw_path.suffix else ('.wav', '.mp3', '.ogg')
    for root in roots:
        for suffix in suffixes:
            candidates.append(root / f"{key}{suffix}")
    try:
        import corona_engine as _ce
        for path in candidates:
            if path.is_file():
                media = _ce.import_media(str(path))
                rid = media.resource_id
                _audio_cache[key] = rid
                return rid
        # The engine may already know a resource id/string name.
        _audio_cache[key] = key
        return key
    except Exception as exc:
        _logger.warning("[ScratchWrapper] audio resolve failed for %s: %s", key, exc)
        return None


def play_sound(name):
    """播放音效（单次）"""
    rid = _ensure_audio(name)
    if rid is not None:
        try:
            import corona_engine as _ce
            _ce.play_audio(rid, loop=False)
            return True
        except Exception as exc:
            _logger.warning("[ScratchWrapper] play_sound failed: %s", exc)
    return False


def loop_sound(name):
    """循环播放音效（BGM 用）"""
    rid = _ensure_audio(name)
    if rid is not None:
        try:
            import corona_engine as _ce
            _ce.play_audio(rid, loop=True)
            return True
        except Exception as exc:
            _logger.warning("[ScratchWrapper] loop_sound failed: %s", exc)
    return False


def stop_sound(name):
    """停止指定音效"""
    rid = _audio_cache.get(name)
    if rid is not None:
        try:
            import corona_engine as _ce
            _ce.stop_audio(rid)
            return True
        except Exception as exc:
            _logger.warning("[ScratchWrapper] stop_sound failed: %s", exc)
    return False


def stop_all_sounds():
    """停止当前运行时已加载的全部音效。"""
    stopped = 0
    try:
        import corona_engine as _ce
    except Exception:
        return False
    for rid in list(_audio_cache.values()):
        if rid is not None:
            try:
                _ce.stop_audio(rid)
                stopped += 1
            except Exception:
                pass
    _audio_cache.clear()
    return stopped > 0


# Stop/reset compatibility
def reset_state():
    global _run_count
    ctx = _current_context()
    ctx.key_handler = None
    ctx.mouse_handler = None
    ctx.broadcast_handlers.clear()
    ctx.clone_start_handler = None
    globals().get('_velocity_cache', {}).pop(ctx.context_id, None)
    globals().get('_raycast_cache', {}).pop(ctx.context_id, None)
    globals().get('_native_velocity_contexts', set()).discard(ctx.context_id)
    globals().get('_native_gravity_contexts', set()).discard(ctx.context_id)
    fresh = ScratchRuntimeContext(ctx.context_id, target_type=ctx.target_type)
    fresh.scene_name = ctx.scene_name
    fresh.actor_name = ctx.actor_name
    if fresh.target_type == "actor" and fresh.scene_name and fresh.actor_name:
        fresh.target_scene_name = fresh.scene_name
        fresh.target_actor_name = fresh.actor_name
        fresh.external_target = True
    if fresh.target_type == "project":
        fresh.initialized = True
    _run_count += 1
    bind_context(fresh)


def request_stop(context_id: str | None = None):
    if context_id:
        prefix = f"{context_id}:clone:"
        with _context_lock:
            matches = [
                ctx for key, ctx in _contexts.items()
                if key == context_id or key.startswith(prefix)
            ]
        for ctx in matches:
            ctx.stop_requested = True
        with _context_lock:
            child_threads = list(_clone_threads.get(context_id, [])) + list(
                _handler_threads.get(context_id, [])
            )
        deadline = _time.monotonic() + 0.5
        for thread in child_threads:
            if thread is _threading.current_thread() or not thread.is_alive():
                continue
            thread.join(timeout=max(0.0, deadline - _time.monotonic()))
        active_child_threads({context_id})
        return

    ctx = getattr(_tls, "ctx", None)
    if ctx is not None and ctx.context_id != "default":
        ctx.stop_requested = True
        return

    request_stop_all()


def request_stop_all():
    with _context_lock:
        for ctx in _contexts.values():
            ctx.stop_requested = True


def reset_stop():
    _current_context().stop_requested = False


def is_stop_requested():
    return _current_context().stop_requested


def active_context_count():
    return len(_live_contexts())
