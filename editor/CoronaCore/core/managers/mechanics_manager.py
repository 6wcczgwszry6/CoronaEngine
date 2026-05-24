"""
Mechanics Manager - DOP 风格
"""
from __future__ import annotations
from typing import Optional, List, Dict

from CoronaCore.core.components import Mechanics
from CoronaCore.core.components import Geometry
from . import geometry_manager

_mechanics: Dict[str, Mechanics] = {}
_attached_geometry: Dict[str, Geometry] = {}


def get(name: str) -> Optional[Mechanics]:
    return _mechanics.get(name)


def has(name: str) -> bool:
    return name in _mechanics


def list_all() -> List[str]:
    return list(_mechanics.keys())


def count() -> int:
    return len(_mechanics)


def create(name: str, geometry: Geometry) -> Mechanics:
    if name in _mechanics:
        raise ValueError(f"Mechanics '{name}' already exists")
    mech = Mechanics(geometry)
    _mechanics[name] = mech
    _attached_geometry[name] = geometry
    geometry_manager.register_dependency(geometry, 'mechanics', name)
    return mech


def register(name: str, mechanics: Mechanics, geometry: Geometry) -> None:
    if name in _mechanics:
        raise ValueError(f"Mechanics '{name}' already registered")
    _mechanics[name] = mechanics
    _attached_geometry[name] = geometry
    geometry_manager.register_dependency(geometry, 'mechanics', name)


def get_or_create(name: str, geometry: Geometry) -> Mechanics:
    exist = get(name)
    if exist is not None:
        return exist
    return create(name, geometry)


def remove(name: str) -> bool:
    if name not in _mechanics:
        return False
    mech = _mechanics.pop(name)
    geo = _attached_geometry.pop(name, None)
    if isinstance(geo, Geometry):
        geometry_manager.unregister_dependency(geo, 'mechanics', name)
    return True


def clear() -> None:
    for n in list_all():
        remove(n)


def create_batch(configs: Dict[str, Geometry]) -> List[Mechanics]:
    res: List[Mechanics] = []
    for n, g in configs.items():
        res.append(get_or_create(n, g))
    return res


def remove_batch(names: List[str]) -> int:
    c = 0
    for n in names:
        if remove(n):
            c += 1
    return c


def print_state() -> None:
    print(f"[MechanicsManager] Total: {count()}")
    for n, m in _mechanics.items():
        print(f"  - {n}: geo={getattr(m, '_geo', None)}")
