"""
Geometry Manager - Data-Oriented Programming (DOP) 风格
数据和操作分离，使用纯函数管理 Geometry 资源
"""
from __future__ import annotations
from typing import Optional, List, Dict, Tuple

from CoronaCore.core.components import Geometry
from . import optics_manager, mechanics_manager, kinematics_manager, acoustics_manager

# ============================================================================
# 数据存储：模块级字典 + 依赖登记
# ============================================================================
_geometries: Dict[str, Geometry] = {}
# 依赖登记：以 geometry 对象 id 为 key，记录依赖的组件 (kind, name)
_dependencies: Dict[int, List[Tuple[str, str]]] = {}


def _key(geo: Geometry) -> int:
    return id(geo)


def register_dependency(geometry: Geometry, kind: str, name: str) -> None:
    deps = _dependencies.setdefault(_key(geometry), [])
    entry = (kind, name)
    if entry not in deps:
        deps.append(entry)


def unregister_dependency(geometry: Geometry, kind: str, name: str) -> None:
    deps = _dependencies.get(_key(geometry))
    if not deps:
        return
    try:
        deps.remove((kind, name))
    except ValueError:
        pass
    if not deps:
        _dependencies.pop(_key(geometry), None)


# ============================================================================
# 查询操作：纯函数
# ============================================================================
def get(name: str) -> Optional[Geometry]:
    return _geometries.get(name)


def has(name: str) -> bool:
    return name in _geometries


def list_all() -> List[str]:
    return list(_geometries.keys())


def count() -> int:
    return len(_geometries)


def get_all() -> Dict[str, Geometry]:
    return _geometries.copy()


# ============================================================================
# 创建/注册：修改数据
# ============================================================================
def create(name: str, model_path: str) -> Geometry:
    if name in _geometries:
        raise ValueError(f"Geometry '{name}' already exists")
    geo = Geometry(model_path, name=name)
    _geometries[name] = geo
    return geo


def register(name: str, geometry: Geometry) -> None:
    if name in _geometries:
        raise ValueError(f"Geometry '{name}' already registered")
    _geometries[name] = geometry


def get_or_create(name: str, model_path: str) -> Geometry:
    existing = get(name)
    if existing is not None:
        return existing
    return create(name, model_path)


# ============================================================================
# 删除/清理：支持对象级与名称级；包含级联
# ============================================================================
def _cascade_remove_for(geo: Geometry) -> None:
    # 读取依赖，并逐类移除
    deps = list(_dependencies.get(_key(geo), []) or [])
    for kind, comp_name in deps:
        if kind == 'optics':
            optics_manager.remove(comp_name)
        elif kind == 'mechanics':
            mechanics_manager.remove(comp_name)
        elif kind == 'kinematics':
            kinematics_manager.remove(comp_name)
        elif kind == 'acoustics':
            acoustics_manager.remove(comp_name)
    # 清空依赖登记
    _dependencies.pop(_key(geo), None)


def remove(name: str) -> bool:
    if name not in _geometries:
        return False
    geo = _geometries.pop(name)
    _cascade_remove_for(geo)
    return True


def remove_by_object(geometry: Geometry) -> bool:
    # 允许通过对象直接移除（便于外部释放时调用）
    to_delete = None
    for n, g in _geometries.items():
        if g is geometry:
            to_delete = n
            break
    if to_delete is None:
        # 名称字典中未注册，仍尝试清理依赖登记
        _cascade_remove_for(geometry)
        return False
    return remove(to_delete)


def clear() -> None:
    # 清理全部，同时级联相关组件
    for name in list_all():
        remove(name)


# ============================================================================
# 批量与调试
# ============================================================================
def create_batch(geometry_configs: Dict[str, str]) -> List[Geometry]:
    results: List[Geometry] = []
    for name, path in geometry_configs.items():
        results.append(get_or_create(name, path))
    return results


def remove_batch(names: List[str]) -> int:
    cnt = 0
    for n in names:
        if remove(n):
            cnt += 1
    return cnt


def print_state() -> None:
    print(f"[GeometryManager] Total: {count()} | deps={len(_dependencies)}")
    for name, geo in _geometries.items():
        print(f"  - {name}: pos={geo.get_position()} deps={_dependencies.get(_key(geo), [])}")
