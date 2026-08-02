# script_manager.py
import os
from typing import Dict, Optional, Type, Any
import logging
from pathlib import Path
import importlib.util
import sys
from .script_base import ScriptBase
from .entities.actor_script import ActorScript
from .entities.project_script import ProjectScript
from .entities.scene_script import SceneScript
from .entities.camera_locked_object import CameraLockedObject
from ..entities import Scene


class ScriptsManager:
    """
    脚本管理器：负责加载、管理和分发所有脚本
    """

    _instances: list = []  # 所有实例的列表，供外部查找

    def __init__(self):
        self.project_script: Optional[ProjectScript] = None
        self.current_scene_script: Optional[SceneScript] = None
        self.actor_scripts: Dict[str, ActorScript] = {}  # actor_name -> ActorScript
        self.logger = logging.getLogger("ScriptManager")
        self.state = "created"
        self.shutdown_requested = False
        ScriptsManager._instances.append(self)

    def initialize_project(self, project_script_path: str, scene: Scene) -> bool:
        """
        初始化项目脚本系统
        Args:
            project_script_path: project_script.py路径
            scene: 场景对象
        Returns:
            bool: 初始化是否成功
        """
        if self.shutdown_requested or self.state == "stopped":
            return False
        if self.state in ("initializing", "ready", "updating"):
            return self.state == "ready"
        self.state = "initializing"
        try:
            self.logger.info(f"Initializing script system with global script: {project_script_path}")

            if project_script_path and os.path.exists(project_script_path):
                # 动态导入全局脚本模块
                module_name = f"project_script_module_{Path(project_script_path).stem}"
                spec = importlib.util.spec_from_file_location(module_name, project_script_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # 查找模块中的ProjectScript子类
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                                issubclass(attr, ProjectScript) and
                                attr != ProjectScript):
                            # 找到ProjectScript子类，实例化并初始化
                            self.project_script = attr(f"Project_{Path(project_script_path).stem}")
                            self.project_script.initialize()
                            self.project_script.is_initialized = True
                            self.project_script.on_start()
                            self.logger.debug("Global script loaded: %s", self.project_script.name)
                            break

            if scene.script_path:
                scene_script_path = scene.script_path
                if not os.path.isabs(scene_script_path):
                    # scene.route 指向 项目/Scene/场景.scene，脚本在 项目/Scripts/
                    project_dir = os.path.dirname(os.path.dirname(scene.route))
                    scene_script_path = os.path.join(project_dir, scene_script_path)
                if os.path.exists(scene_script_path):
                    # 动态导入场景脚本模块
                    module_name = f"scene_script_module_{Path(scene_script_path).stem}"
                    spec = importlib.util.spec_from_file_location(module_name, scene_script_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # 查找模块中的SceneScript子类
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (isinstance(attr, type) and
                                    issubclass(attr, SceneScript) and
                                    attr != SceneScript):
                                # 找到SceneScript子类，实例化并初始化
                                self.current_scene_script = attr(f"Scene_{scene.name}", scene)
                                self.current_scene_script.initialize()
                                self.current_scene_script.is_initialized = True
                                self.current_scene_script.on_start()
                                self.logger.debug(
                                    "Scene script loaded for %s: %s", scene.name, self.current_scene_script.name)
                                break

            for actor in scene._actors:
                if hasattr(actor, 'script_path') and actor.script_path:
                    actor_script_path = actor.script_path
                    if not os.path.isabs(actor_script_path):
                        project_dir = os.path.dirname(os.path.dirname(scene.route))
                        actor_script_path = os.path.join(project_dir, actor_script_path)
                    if os.path.exists(actor_script_path):
                        # 动态导入Actor脚本模块
                        module_name = f"actor_script_module_{Path(actor_script_path).stem}_{actor.name}"
                        spec = importlib.util.spec_from_file_location(module_name, actor_script_path)
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)

                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if (isinstance(attr, type) and
                                        issubclass(attr, ActorScript) and
                                        attr != ActorScript):
                                    # 找到ActorScript子类，实例化并初始化
                                    actor_script = attr(f"Actor_{actor.name}", actor)
                                    actor_script.initialize()
                                    actor_script.is_initialized = True
                                    actor_script.on_start()
                                    self.actor_scripts[actor.name] = actor_script
                                    # 如果是 CameraLockedObject，关联到 Actor
                                    if isinstance(actor_script, CameraLockedObject):
                                        actor.set_camera_locked_script(actor_script)
                                    self.logger.debug("Actor script loaded for %s: %s", actor.name, actor_script.name)
                                    break

            self.logger.info("Script system initialized successfully")
            self.state = "ready"
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize script system: {e}", exc_info=True)
            self._shutdown_initialized_scripts()
            self.state = "stopped"
            return False

    def update(self, delta_time: float):
        """更新所有脚本"""
        if self.shutdown_requested or self.state not in ("ready", "updating"):
            return False
        self.state = "updating"
        # 更新全局脚本
        if self.project_script and self.project_script.is_initialized:
            try:
                self.project_script.update(delta_time)
                self.project_script.on_update(delta_time)
            except Exception:
                self.logger.exception("Project script update failed")

        # 更新场景脚本
        if self.current_scene_script and self.current_scene_script.is_initialized:
            try:
                self.current_scene_script.update(delta_time)
                self.current_scene_script.on_update(delta_time)
            except Exception:
                self.logger.exception("Scene script update failed")

        # 更新单位脚本
        for script in self.actor_scripts.values():
            if script.is_initialized:
                try:
                    script.update(delta_time)
                    script.on_update(delta_time)
                except Exception:
                    self.logger.exception("Actor script update failed: %s", script.name)

        self.state = "ready"
        return True

    def _shutdown_initialized_scripts(self):
        for script in list(self.actor_scripts.values())[::-1]:
            try:
                script.shutdown()
            except Exception:
                self.logger.exception("Actor script shutdown failed: %s", script.name)
        self.actor_scripts.clear()
        if self.current_scene_script:
            try:
                self.current_scene_script.shutdown()
            except Exception:
                self.logger.exception("Scene script shutdown failed")
            self.current_scene_script = None
        if self.project_script:
            try:
                self.project_script.shutdown()
            except Exception:
                self.logger.exception("Project script shutdown failed")
            self.project_script = None

    def shutdown(self):
        """关闭脚本系统"""
        if self.state == "stopped":
            return True
        self.shutdown_requested = True
        self.state = "stopping"
        self._shutdown_initialized_scripts()
        self.state = "stopped"
        self.logger.debug("Script system shutdown")
        return True
