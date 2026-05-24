"""
Acoustics Manager - DOP 风格
"""
from __future__ import annotations
from typing import Optional, List, Dict

from CoronaCore.core.components import Acoustics
from CoronaCore.core.components import Geometry
from . import geometry_manager

_acoustics: Dict[str, Acoustics] = {}
_attached_geometry: Dict[str, Geometry] = {}


def get(name: str) -> Optional[Acoustics]:
    return _acoustics.get(name)


def has(name: str) -> bool:
    return name in _acoustics


def list_all() -> List[str]:
    return list(_acoustics.keys())


def count() -> int:
    return len(_acoustics)


def create(name: str, geometry: Geometry) -> Acoustics:
    if name in _acoustics:
        raise ValueError(f"Acoustics '{name}' already exists")
    acou = Acoustics(geometry)
    _acoustics[name] = acou
    _attached_geometry[name] = geometry
    geometry_manager.register_dependency(geometry, 'acoustics', name)
    return acou


def register(name: str, acoustics: Acoustics, geometry: Geometry) -> None:
    if name in _acoustics:
        raise ValueError(f"Acoustics '{name}' already registered")
    _acoustics[name] = acoustics
    _attached_geometry[name] = geometry
    geometry_manager.register_dependency(geometry, 'acoustics', name)


def get_or_create(name: str, geometry: Geometry) -> Acoustics:
    exist = get(name)
    if exist is not None:
        return exist
    return create(name, geometry)


def remove(name: str) -> bool:
    if name not in _acoustics:
        return False
    acou = _acoustics.pop(name)
    geo = _attached_geometry.pop(name, None)
    if isinstance(geo, Geometry):
        geometry_manager.unregister_dependency(geo, 'acoustics', name)
    return True


def clear() -> None:
    for n in list_all():
        remove(n)


def create_batch(configs: Dict[str, Geometry]) -> List[Acoustics]:
    res: List[Acoustics] = []
    for n, g in configs.items():
        res.append(get_or_create(n, g))
    return res


def remove_batch(names: List[str]) -> int:
    c = 0
    for n in names:
        if remove(n):
            c += 1
    return c


def set_all_volume(volume: float) -> None:
    for ac in _acoustics.values():
        try:
            ac.set_volume(volume)
        except Exception:
            pass


def mute_all() -> None:
    set_all_volume(0.0)


def print_state() -> None:
    print(f"[AcousticsManager] Total: {count()}")
    for n, a in _acoustics.items():
        print(f"  - {n}: geo={getattr(a, '_geo', None)}")
