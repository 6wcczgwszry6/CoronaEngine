"""
Kinematics Manager - DOP 风格
"""
from __future__ import annotations
from typing import Optional, List, Dict

from CoronaCore.core.components import Kinematics
from CoronaCore.core.components import Geometry
from . import geometry_manager

_kinematics: Dict[str, Kinematics] = {}
_attached_geometry: Dict[str, Geometry] = {}


def get(name: str) -> Optional[Kinematics]:
    return _kinematics.get(name)


def has(name: str) -> bool:
    return name in _kinematics


def list_all() -> List[str]:
    return list(_kinematics.keys())


def count() -> int:
    return len(_kinematics)


def create(name: str, geometry: Geometry) -> Kinematics:
    if name in _kinematics:
        raise ValueError(f"Kinematics '{name}' already exists")
    kine = Kinematics(geometry)
    _kinematics[name] = kine
    _attached_geometry[name] = geometry
    geometry_manager.register_dependency(geometry, 'kinematics', name)
    return kine


def register(name: str, kinematics: Kinematics, geometry: Geometry) -> None:
    if name in _kinematics:
        raise ValueError(f"Kinematics '{name}' already registered")
    _kinematics[name] = kinematics
    _attached_geometry[name] = geometry
    geometry_manager.register_dependency(geometry, 'kinematics', name)


def get_or_create(name: str, geometry: Geometry) -> Kinematics:
    exist = get(name)
    if exist is not None:
        return exist
    return create(name, geometry)


def remove(name: str) -> bool:
    if name not in _kinematics:
        return False
    kine = _kinematics.pop(name)
    geo = _attached_geometry.pop(name, None)
    if isinstance(geo, Geometry):
        geometry_manager.unregister_dependency(geo, 'kinematics', name)
    return True


def clear() -> None:
    for n in list_all():
        remove(n)


def create_batch(configs: Dict[str, Geometry]) -> List[Kinematics]:
    res: List[Kinematics] = []
    for n, g in configs.items():
        res.append(get_or_create(n, g))
    return res


def remove_batch(names: List[str]) -> int:
    c = 0
    for n in names:
        if remove(n):
            c += 1
    return c


def play_all(speed: float = 1.0) -> None:
    for kine in _kinematics.values():
        try:
            kine.play_animation(speed)
        except Exception:
            pass


def stop_all() -> None:
    for kine in _kinematics.values():
        try:
            kine.stop_animation()
        except Exception:
            pass


def print_state() -> None:
    print(f"[KinematicsManager] Total: {count()}")
    for n, k in _kinematics.items():
        print(f"  - {n}: geo={getattr(k, '_geo', None)}")
