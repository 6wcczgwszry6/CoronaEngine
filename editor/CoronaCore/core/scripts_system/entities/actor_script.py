from ..script_base import ScriptBase
from typing import Dict, Any, Optional, List
from ...entities import Actor


class ActorScript(ScriptBase):
    """
    单位脚本：在actor生成时初始化
    生命周期：Actor创建 -> Actor销毁
    作用范围：单个Actor
    """

    def __init__(self, name: str = "ActorScript", actor: Actor = None):
        super().__init__(name)
        self.actor: Optional[Actor] = actor

    def initialize(self, *args, **kwargs):
        """
        初始化单位脚本
        Args:
            actor: 关联的Actor对象
            unit_data: 单位数据（可选）
        """
        pass

    def update(self, delta_time: float):
        """单位更新"""
        pass
