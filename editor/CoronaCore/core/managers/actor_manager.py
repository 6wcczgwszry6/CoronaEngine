"""
Actor Manager - Data-Oriented Programming (DOP) 风格
数据和操作分离，使用纯函数管理 Actor 资源
"""
from __future__ import annotations
from typing import Optional, List, Dict
from CoronaCore.core.entities.actor import Actor

# ============================================================================
# 数据存储：模块级字典
# ============================================================================
_actors: Dict[str, Actor] = {}


# ============================================================================
# 查询操作：纯函数
# ============================================================================
def get(route: str) -> Optional[Actor]:
    """获取指定名称的 Actor"""
    return _actors.get(route)


def has(route: str) -> bool:
    """检查 Actor 是否存在"""
    return route in _actors


def list_all() -> List[str]:
    """列出所有 Actor 名称"""
    return list(_actors.keys())


def count() -> int:
    """获取 Actor 总数"""
    return len(_actors)


# ============================================================================
# 创建操作：修改数据
# ============================================================================
def create(route: str) -> Actor:
    """创建新的 Actor"""
    if route in _actors:
        raise ValueError(f"Actor '{route}' already exists")
    actor = Actor(route=route)
    _actors[route] = actor
    return actor


def register(route: str, actor: Actor) -> None:
    """注册已存在的 Actor"""
    if route in _actors:
        raise ValueError(f"Actor '{route}' already registered")
    _actors[route] = actor


def get_or_create(route: str) -> Actor:
    """获取或创建 Actor（推荐）"""
    existing = get(route)
    if existing is not None:
        return existing
    return create(route)


# ============================================================================
# 删除操作：修改数据
# ============================================================================
def remove(route: str) -> bool:
    """删除指定名称的 Actor"""
    if route in _actors:
        del _actors[route]
        return True
    return False


def clear() -> None:
    """清空所有 Actor"""
    _actors.clear()


# ============================================================================
# 批量操作
# ============================================================================
def create_batch(actor_configs: List[str]) -> List[Actor]:
    """批量创建 Actor

    Args:
        actor_configs: {name: asset_path} 字典
    """
    results = []
    for route in actor_configs:
        actor = get_or_create(route)
        results.append(actor)
    return results


def remove_batch(routes: List[str]) -> int:
    """批量删除 Actor，返回删除的数量"""
    count = 0
    for route in routes:
        if remove(route):
            count += 1
    return count


def filter_by_path(path_pattern: str) -> List[Actor]:
    """根据路径模式筛选 Actor"""
    return [actor for actor in _actors.values() if path_pattern in actor.path]


# ============================================================================
# 调试与监控
# ============================================================================
def get_all() -> Dict[str, Actor]:
    """获取所有 Actor（用于调试）"""
    return _actors.copy()


def print_state() -> None:
    """打印当前状态（用于调试）"""
    print(f"[ActorManager] Total: {count()}")
    for name in list_all():
        actor = get(name)
        print(f"  - {name}: {actor.path}")


