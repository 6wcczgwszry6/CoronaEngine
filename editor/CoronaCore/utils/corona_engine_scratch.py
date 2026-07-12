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


_default_context = ScratchRuntimeContext("default", target_type="internal")
_contexts: dict[str, ScratchRuntimeContext] = {"default": _default_context}
_completed_state_snapshots: dict[str, dict] = {}
_scene_virtual_objects: dict[str, dict[str, object]] = {}
_scene_deleted_objects: dict[str, set[str]] = {}
_scene_object_tags: dict[str, dict[str, str]] = {}


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
        target_type=target_type or "actor",
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
        with _context_lock:
            _contexts.pop(ctx.context_id, None)
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


def handle_mouse_event(event_type, button, x, y):
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


def _init_engine():
    ctx = _current_context()
    if ctx.initialized:
        return
    ctx.initialized = True
    if ctx.target_type == "project":
        return
    if ctx.external_target:
        _init_external_target(ctx)
    else:
        _init_internal_actor(ctx)


def _init_external_target(ctx: ScratchRuntimeContext):
    try:
        from CoronaCore.core.managers import scene_manager

        ctx.target_scene = scene_manager.get(ctx.target_scene_name)
        if ctx.target_scene is None:
            _logger.warning("[ScratchWrapper] scene not found, fallback internal: %s", ctx.target_scene_name)
            _init_internal_actor(ctx)
            return

        ctx.target_actor = ctx.target_scene.find_actor(ctx.target_actor_name)
        if ctx.target_actor is None:
            _logger.warning("[ScratchWrapper] actor not found, fallback internal: %s", ctx.target_actor_name)
            _init_internal_actor(ctx)
            return

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
        _logger.exception("[ScratchWrapper] bind actor failed: %s", exc)
        _init_internal_actor(ctx)


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
    with _engine_lock:
        if ctx.geometry is not None:
            try:
                ctx.geometry.set_position([ctx.x, ctx.y, ctx.z])
                return
            except Exception as exc:
                _logger.debug("_sync_position geometry failed: %s", exc)
        if ctx.actor is not None and hasattr(ctx.actor, "set_position"):
            try:
                ctx.actor.set_position([ctx.x, ctx.y, ctx.z])
            except Exception as exc:
                _logger.debug("_sync_position actor failed: %s", exc)


def _sync_scale():
    ctx = _current_context()
    check_stop()
    scale = ctx.size_val / 100.0
    with _engine_lock:
        if ctx.geometry is not None:
            try:
                ctx.geometry.set_scale([scale, scale, scale])
                return
            except Exception as exc:
                _logger.debug("_sync_scale geometry failed: %s", exc)
        if ctx.actor is not None and hasattr(ctx.actor, "set_scale"):
            try:
                ctx.actor.set_scale([scale, scale, scale])
            except Exception as exc:
                _logger.debug("_sync_scale actor failed: %s", exc)


def _apply_rotation():
    ctx = _current_context()
    check_stop()
    rot = [ctx.rot_x, ctx.rot_y, ctx.rot_z]
    mech_was_enabled = False
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
                try:
                    getattr(target, method)(rot)
                except Exception as exc:
                    _logger.debug("_apply_rotation %s failed: %s", method, exc)
        if mech_was_enabled and ctx.mechanics is not None:
            try:
                ctx.mechanics.set_physics_enabled(True)
            except Exception:
                pass


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


def _set_actor_position(actor, pos):
    if actor is None:
        return False
    pos = [_safe_float(pos[0]), _safe_float(pos[1]), _safe_float(pos[2])]
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


def _actors_touch(a, b) -> bool:
    if a is None or b is None or a is b or _is_actor_deleted(a) or _is_actor_deleted(b):
        return False
    aabb_a = _actor_aabb(a)
    aabb_b = _actor_aabb(b)
    if aabb_a is not None and aabb_b is not None:
        return _aabb_overlap(aabb_a, aabb_b)
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


def _try_native_spawn(scene, template, name, pos):
    if scene is None:
        return None
    template_actor = _resolve_actor(template)

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
        if isinstance(result, dict) and result.get('status') not in ('success', 'ok'):
            _logger.warning("[ScratchWrapper] native spawn rejected %s: %r", name, result)
            return None
        if hasattr(scene, '_notify_scene_tree_changed'):
            scene._notify_scene_tree_changed()
        resolved = scene.find_actor(name) if hasattr(scene, 'find_actor') else None
        if resolved is not None:
            return resolved
        # Native object is visible, while this proxy keeps Blockly collision/tag logic usable
        # until the Python scene cache refreshes.
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
    dist = max(0.0, _safe_float(distance, 1.0))
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
    ctx.countdown_end_time = _time.monotonic() + max(0.0, _safe_float(seconds))


def countdown_left():
    end_time = _safe_float(_current_context().countdown_end_time, 0.0)
    if end_time <= 0:
        return 0.0
    return max(0.0, end_time - _time.monotonic())


def countdown_finished():
    end_time = _safe_float(_current_context().countdown_end_time, 0.0)
    return bool(end_time > 0 and countdown_left() <= 0.0)


def runtime_state_snapshot(ctx=None):
    ctx = ctx or _current_context()
    end_time = _safe_float(ctx.countdown_end_time, 0.0)
    countdown = max(0.0, end_time - _time.monotonic()) if end_time > 0 else 0.0
    variables = {
        name: ctx.variables.get(name, 0.0)
        for name in sorted(ctx.visible_variables)
    }
    lists = {
        name: ctx.list_values.get(name, [])
        for name in sorted(ctx.visible_lists)
    }
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


def cloneStart():
    """Compatibility marker. Generated code registers a clone handler directly."""
    return bool(_current_context().current_clone_name)


def _run_clone_context(child, handler):
    try:
        _run_bound_handler(child, handler, 'clone')
    finally:
        release_context(child)


def clone(name):
    parent = _current_context()
    template = str(name or '').strip() or parent.actor_name
    template_actor = _resolve_actor(template)
    pos = _actor_position(template_actor or _current_actor()) or [parent.x, parent.y, parent.z]
    clone_name = _unique_object_name(f"{_object_name(template_actor) or template or 'clone'}_clone")
    created_name = object_spawn(template, clone_name, pos[0], pos[1], pos[2])
    handler = parent.clone_start_handler
    if callable(handler):
        child = create_context(
            context_id=f"{parent.context_id}:clone:{created_name}",
            target_type='actor',
            scene_name=parent.scene_name,
            actor_name=created_name,
        )
        child.current_clone_name = created_name
        actor = _resolve_actor(created_name)
        if actor is not None:
            child.actor = actor
            child.target_actor = actor
            child.scene = _runtime_scene()
            child.target_scene = child.scene
            child.initialized = True
        thread = _threading.Thread(
            target=_run_clone_context,
            args=(child, handler),
            daemon=True,
            name=f"scratch-clone-{created_name}",
        )
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
                target=_run_bound_handler,
                args=(ctx, handler, f"broadcast:{key}"),
                daemon=True,
                name=f"scratch-broadcast-{ctx.context_id}",
            )
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


def var_add(name, value):
    ctx = _current_context()
    ctx.variables[name] = ctx.variables.get(name, 0.0) + float(value)


def var_set(name, value):
    _current_context().variables[name] = float(value)


def var_show(name):
    _current_context().visible_variables.add(str(name or ''))
    return True


def var_hide(name):
    _current_context().visible_variables.discard(str(name or ''))
    return True


def list_show(name, value=None):
    ctx = _current_context()
    key = str(name or '')
    ctx.visible_lists.add(key)
    if value is not None:
        if isinstance(value, list):
            ctx.list_values[key] = value
        else:
            try:
                ctx.list_values[key] = list(value)
            except TypeError:
                ctx.list_values[key] = [value]
    return True


def list_hide(name):
    _current_context().visible_lists.discard(str(name or ''))
    return True


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
        with _context_lock:
            ctx = _contexts.get(context_id)
        if ctx is not None:
            ctx.stop_requested = True
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
