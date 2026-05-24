"""
脚本工具模块：为各种脚本提供便捷的工具函数
供 ProjectScript, SceneScript, ActorScript 内部使用
"""

from typing import Optional, List, Dict, Any, Union
from ..entities import Scene, Actor
from .scripts_manager import ScriptsManager
from .entities.project_script import ProjectScript
from .entities.scene_script import SceneScript
from .entities.actor_script import ActorScript
import logging


class ScriptsTool:
    """
    脚本工具类，提供静态方法供各种脚本调用
    所有方法都是类方法，可以直接调用
    """

    _script_manager: Optional[ScriptsManager] = None
    _logger = logging.getLogger("ScriptsTool")

    @classmethod
    def initialize(cls, script_manager: ScriptsManager):
        """初始化工具类，设置脚本管理器引用"""
        cls._script_manager = script_manager
        cls._logger.info("ScriptsTool initialized")

    # ==================== 脚本获取相关 ====================

    @classmethod
    def get_project_script(cls) -> Optional[ProjectScript]:
        """
        获取项目全局脚本

        Returns:
            ProjectScript 实例，如果不存在则返回 None
        """
        if cls._script_manager:
            return cls._script_manager.project_script
        cls._logger.warning("ScriptManager not initialized")
        return None

    @classmethod
    def get_scene_script(cls, scene_name: Optional[str] = None) -> Optional[SceneScript]:
        """
        获取场景脚本

        Args:
            scene_name: 场景名称，如果为 None 则返回当前场景脚本

        Returns:
            SceneScript 实例，如果不存在则返回 None
        """
        if not cls._script_manager:
            cls._logger.warning("ScriptManager not initialized")
            return None

        if scene_name is None:
            # 返回当前场景脚本
            return cls._script_manager.current_scene_script
        else:
            # 根据名称查找场景脚本
            # 注意：如果需要多场景支持，可以在 ScriptManager 中添加场景脚本字典
            current = cls._script_manager.current_scene_script
            if current and current.scene and current.scene.name == scene_name:
                return current
            return None

    @classmethod
    def get_actor_script(cls, actor_name: str) -> Optional[ActorScript]:
        """
        获取指定 Actor 的脚本

        Args:
            actor_name: Actor 名称

        Returns:
            ActorScript 实例，如果不存在则返回 None
        """
        if cls._script_manager:
            return cls._script_manager.actor_scripts.get(actor_name)
        cls._logger.warning("ScriptManager not initialized")
        return None

    @classmethod
    def get_all_actor_scripts(cls) -> Dict[str, ActorScript]:
        """
        获取所有 Actor 脚本

        Returns:
            Actor 名称到脚本的字典
        """
        if cls._script_manager:
            return cls._script_manager.actor_scripts.copy()
        cls._logger.warning("ScriptManager not initialized")
        return {}

    # ==================== Actor 对象获取 ====================

    @classmethod
    def get_actor(cls, actor_name: str, scene: Optional[Scene] = None) -> Optional[Actor]:
        """
        获取场景中的 Actor 对象

        Args:
            actor_name: Actor 名称
            scene: 场景对象，如果为 None 则从当前场景获取

        Returns:
            Actor 对象，如果不存在则返回 None
        """
        target_scene = cls._get_target_scene(scene)
        if not target_scene:
            return None

        return target_scene.get_actor(actor_name)

    @classmethod
    def get_actors_by_type(cls, actor_type: str, scene: Optional[Scene] = None) -> List[Actor]:
        """
        获取场景中指定类型的所有 Actor

        Args:
            actor_type: Actor 类型
            scene: 场景对象，如果为 None 则从当前场景获取

        Returns:
            Actor 对象列表
        """
        target_scene = cls._get_target_scene(scene)
        if not target_scene:
            return []

        result = []
        for actor in target_scene.get_actors():
            if getattr(actor, 'actor_type', '') == actor_type:
                result.append(actor)
        return result

    @classmethod
    def get_actors_by_name_pattern(cls, pattern: str, scene: Optional[Scene] = None) -> List[Actor]:
        """
        根据名称模式获取 Actor（支持模糊匹配）

        Args:
            pattern: 名称模式，如 "player*", "enemy_001"
            scene: 场景对象，如果为 None 则从当前场景获取

        Returns:
            Actor 对象列表
        """
        target_scene = cls._get_target_scene(scene)
        if not target_scene:
            return []

        result = []
        import fnmatch
        for actor in target_scene.get_actors():
            if fnmatch.fnmatch(actor.name.lower(), pattern.lower()):
                result.append(actor)
        return result

    @classmethod
    def get_all_actors(cls, scene: Optional[Scene] = None) -> List[Actor]:
        """
        获取场景中的所有 Actor

        Args:
            scene: 场景对象，如果为 None 则从当前场景获取

        Returns:
            Actor 对象列表
        """
        target_scene = cls._get_target_scene(scene)
        if not target_scene:
            return []

        return target_scene.get_actors()

    @classmethod
    def find_actor_by_position(cls, position: List[float], radius: float = 1.0,
                               scene: Optional[Scene] = None) -> List[Actor]:
        """
        根据位置查找 Actor

        Args:
            position: 目标位置 [x, y, z]
            radius: 查找半径
            scene: 场景对象，如果为 None 则从当前场景获取

        Returns:
            在指定半径内的 Actor 列表
        """
        target_scene = cls._get_target_scene(scene)
        if not target_scene:
            return []

        result = []
        import math
        for actor in target_scene.get_actors():
            try:
                actor_pos = actor.get_position()
                distance = math.sqrt(
                    (actor_pos[0] - position[0]) ** 2 +
                    (actor_pos[1] - position[1]) ** 2 +
                    (actor_pos[2] - position[2]) ** 2
                )
                if distance <= radius:
                    result.append(actor)
            except Exception as e:
                cls._logger.error(f"Error calculating distance for {actor.name}: {e}")

        return result

    # ==================== 场景相关 ====================

    @classmethod
    def get_current_scene(cls) -> Optional[Scene]:
        """
        获取当前场景

        Returns:
            当前 Scene 对象
        """
        if cls._script_manager and cls._script_manager.current_scene_script:
            return cls._script_manager.current_scene_script.scene
        return None

    # ==================== 辅助方法 ====================

    @classmethod
    def _get_target_scene(cls, scene: Optional[Scene] = None) -> Optional[Scene]:
        """
        获取目标场景（内部辅助方法）

        Args:
            scene: 指定的场景，如果为 None 则返回当前场景

        Returns:
            Scene 对象
        """
        if scene:
            return scene

        return cls.get_current_scene()

    @classmethod
    def broadcast_event(cls, event_name: str, data: Any = None,
                        target: str = "all") -> None:
        """
        广播事件到脚本

        Args:
            event_name: 事件名称
            data: 事件数据
            target: 目标类型：'all', 'project', 'scene', 'actors'
        """
        if not cls._script_manager:
            cls._logger.warning("ScriptManager not initialized")
            return

        cls._logger.info(f"Broadcasting event: {event_name} to {target}")

        if target in ["all", "project"] and cls._script_manager.project_script:
            cls._script_manager.project_script.on_event(event_name, data)

        if target in ["all", "scene"] and cls._script_manager.current_scene_script:
            cls._script_manager.current_scene_script.on_event(event_name, data)

        if target in ["all", "actors"]:
            for script in cls._script_manager.actor_scripts.values():
                script.on_event(event_name, data)

    @classmethod
    def log(cls, message: str, level: str = "info"):
        """
        日志记录

        Args:
            message: 日志消息
            level: 日志级别：'debug', 'info', 'warning', 'error'
        """
        log_func = getattr(cls._logger, level.lower(), cls._logger.info)
        log_func(message)


# 为了方便使用，创建单例实例
scripts_tool = ScriptsTool()


# 为了方便脚本导入，提供快捷函数
def get_project_script() -> Optional[ProjectScript]:
    """快捷函数：获取项目脚本"""
    return ScriptsTool.get_project_script()


def get_scene_script(scene_name: Optional[str] = None) -> Optional[SceneScript]:
    """快捷函数：获取场景脚本"""
    return ScriptsTool.get_scene_script(scene_name)


def get_actor_script(actor_name: str) -> Optional[ActorScript]:
    """快捷函数：获取 Actor 脚本"""
    return ScriptsTool.get_actor_script(actor_name)


def get_actor(actor_name: str, scene: Optional[Scene] = None) -> Optional[Actor]:
    """快捷函数：获取 Actor 对象"""
    return ScriptsTool.get_actor(actor_name, scene)


def get_all_actors(scene: Optional[Scene] = None) -> List[Actor]:
    """快捷函数：获取所有 Actor"""
    return ScriptsTool.get_all_actors(scene)


def find_actors_by_type(actor_type: str, scene: Optional[Scene] = None) -> List[Actor]:
    """快捷函数：根据类型查找 Actor"""
    return ScriptsTool.get_actors_by_type(actor_type, scene)


def broadcast_event(event_name: str, data: Any = None, target: str = "all"):
    """快捷函数：广播事件"""
    ScriptsTool.broadcast_event(event_name, data, target)
