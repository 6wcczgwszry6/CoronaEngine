"""
Optics Manager - DOP 风格
"""
from __future__ import annotations
from typing import Optional, List, Dict

from CoronaCore.core.components import Optics
from CoronaCore.core.components import Geometry
from . import geometry_manager

# ============================================================================
# 数据存储：模块级字典
# ============================================================================
_optics: Dict[str, Optics] = {}
_attached_geometry: Dict[str, Geometry] = {}


# ============================================================================
# 查询操作：纯函数
# ============================================================================
def get(name: str) -> Optional[Optics]:
    """获取指定名称的 Optics"""
    return _optics.get(name)


def has(name: str) -> bool:
    """检查 Optics 是否存在"""
    return name in _optics


def list_all() -> List[str]:
    """列出所有 Optics 名称"""
    return list(_optics.keys())


def count() -> int:
    """获取 Optics 总数"""
    return len(_optics)


# ============================================================================
# 创建操作：修改数据
# ============================================================================
def create(name: str, geometry: Geometry) -> Optics:
    """创建新的 Optics 组件"""
    if name in _optics:
        raise ValueError(f"Optics '{name}' already exists")
    opt = Optics(geometry)
    _optics[name] = opt
    _attached_geometry[name] = geometry
    geometry_manager.register_dependency(geometry, 'optics', name)
    return opt


def register(name: str, optics: Optics, geometry: Geometry) -> None:
    """注册已存在的 Optics"""
    if name in _optics:
        raise ValueError(f"Optics '{name}' already registered")
    _optics[name] = optics
    _attached_geometry[name] = geometry
    geometry_manager.register_dependency(geometry, 'optics', name)


def get_or_create(name: str, geometry: Geometry) -> Optics:
    """获取或创建 Optics（推荐）"""
    exist = get(name)
    if exist is not None:
        return exist
    return create(name, geometry)


# ============================================================================
# 删除操作：修改数据
# ============================================================================
def remove(name: str) -> bool:
    """删除指定名称的 Optics"""
    if name not in _optics:
        return False
    opt = _optics.pop(name)
    geo = _attached_geometry.pop(name, None)
    if isinstance(geo, Geometry):
        geometry_manager.unregister_dependency(geo, 'optics', name)
    return True


def clear() -> None:
    """清空所有 Optics"""
    for n in list_all():
        remove(n)


# ============================================================================
# 批量操作
# ============================================================================
def create_batch(configs: Dict[str, Geometry]) -> List[Optics]:
    """批量创建 Optics

    Args:
        configs: {name: geometry} 字典
    """
    res: List[Optics] = []
    for n, g in configs.items():
        res.append(get_or_create(n, g))
    return res


def remove_batch(names: List[str]) -> int:
    """批量删除 Optics，返回删除的数量"""
    c = 0
    for n in names:
        if remove(n):
            c += 1
    return c


def print_state() -> None:
    """打印当前状态（用于调试）"""
    print(f"[OpticsManager] Total: {count()}")
    for n, o in _optics.items():
        print(f"  - {n}: geo={getattr(o, '_geo', None)}")
