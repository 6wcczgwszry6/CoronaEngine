"""
Environment Manager - Data-Oriented Programming (DOP) 风格
数据和操作分离，使用纯函数管理 Environment 资源
"""
from __future__ import annotations
from typing import Optional, List, Dict
from CoronaCore.core.entities.environment import Environment

# ============================================================================
# 数据存储：模块级字典
# ============================================================================
_environments: Dict[str, Environment] = {}


# ============================================================================
# 查询操作：纯函数
# ============================================================================
def get(name: str) -> Optional[Environment]:
    """获取指定名称的 Environment"""
    return _environments.get(name)


def has(name: str) -> bool:
    """检查 Environment 是否存在"""
    return name in _environments


def list_all() -> List[str]:
    """列出所有 Environment 名称"""
    return list(_environments.keys())


def count() -> int:
    """获取 Environment 总数"""
    return len(_environments)


# ============================================================================
# 创建操作：修改数据
# ============================================================================
def create(name: str) -> Environment:
    """创建新的 Environment"""
    if name in _environments:
        raise ValueError(f"Environment '{name}' already exists")
    env = Environment()
    _environments[name] = env
    return env


def register(name: str, environment: Environment) -> None:
    """注册已存在的 Environment"""
    if name in _environments:
        raise ValueError(f"Environment '{name}' already registered")
    _environments[name] = environment


def get_or_create(name: str) -> Environment:
    """获取或创建 Environment（推荐）"""
    existing = get(name)
    if existing is not None:
        return existing
    return create(name)


# ============================================================================
# 删除操作：修改数据
# ============================================================================
def remove(name: str) -> bool:
    """删除指定名称的 Environment"""
    if name in _environments:
        del _environments[name]
        return True
    return False


def clear() -> None:
    """清空所有 Environment"""
    _environments.clear()


# ============================================================================
# 批量操作
# ============================================================================
def create_batch(env_names: List[str]) -> List[Environment]:
    """批量创建 Environment"""
    results = []
    for name in env_names:
        env = get_or_create(name)
        results.append(env)
    return results


def remove_batch(names: List[str]) -> int:
    """批量删除 Environment，返回删除的数量"""
    count_deleted = 0
    for name in names:
        if remove(name):
            count_deleted += 1
    return count_deleted


def set_all_sun_direction(direction: List[float]) -> None:
    """设置所有 Environment 的太阳方向"""
    for env in _environments.values():
        env.set_sun_direction(direction)


# ============================================================================
# 调试与监控
# ============================================================================
def get_all() -> Dict[str, Environment]:
    """获取所有 Environment（用于调试）"""
    return _environments.copy()


def print_state() -> None:
    """打印当前状态（用于调试）"""
    print(f"[EnvironmentManager] Total: {count()}")
    for name in list_all():
        env = get(name)
        print(f"  - {name}: {env}")
