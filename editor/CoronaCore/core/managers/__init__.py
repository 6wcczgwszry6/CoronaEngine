"""
Managers - Data-Oriented Programming (DOP) 风格的资源管理器
所有 Manager 对外暴露模块级函数，类包装器仅供内部模块直接引用。
"""

# DOP modules (official public API)
from . import scene_manager
from . import actor_manager
from . import camera_manager
from . import environment_manager
from . import geometry_manager
from . import optics_manager
from . import mechanics_manager
from . import kinematics_manager
from . import acoustics_manager

__all__ = [
    "scene_manager",
    "actor_manager",
    "camera_manager",
    "environment_manager",
    "geometry_manager",
    "optics_manager",
    "mechanics_manager",
    "kinematics_manager",
    "acoustics_manager",
]
