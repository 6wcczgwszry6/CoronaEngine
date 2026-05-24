from ..script_base import ScriptBase
from typing import Dict, Any, Optional, List
from ...entities import Scene


class SceneScript(ScriptBase):
    """
    场景脚本：存放场景数据，在切换场景时初始化
    生命周期：场景加载 -> 场景卸载
    作用范围：当前场景
    """

    def __init__(self, name: str = "SceneScript", scene: Scene = None):
        super().__init__(name)
        self.scene: Optional[Scene] = scene

    def initialize(self, *args, **kwargs):
        """
        初始化场景脚本
        Args:
            scene: 关联的场景对象
            scene_data: 场景数据（可选）
        """
        pass

    def update(self, delta_time: float):
        """场景更新"""
        pass
