from typing import Any, Dict, List

from ..corona_editor import CoronaEditor

CoronaEngine = CoronaEditor.CoronaEngine


class Environment:
    """
    Environment 包装类：环境设置（太阳方向、地面网格等）

    使用方式：
        env = Environment()
        env.set_sun_direction([1.0, -1.0, 0.0])
        scene.set_environment(env)
    """

    def __init__(self, name: str = "Environment"):
        """
        创建 Environment 对象

        Args:
            name: 环境名称
        """
        if CoronaEngine is None:
            raise RuntimeError("CoronaEngine 未初始化")

        EnvironmentCtor = getattr(CoronaEngine, 'Environment', None)
        if EnvironmentCtor is None:
            raise RuntimeError("CoronaEngine 未提供 Environment 构造器")

        self.engine_obj = EnvironmentCtor()
        self.name = name
        
        # Python 层状态
        self.sun_direction: List[float] = [1.0, 1.0, 1.0]  # 默认太阳方向
        self.floor_grid_enabled: bool = True
        self.gravity: List[float] = [0.0, -9.8, 0.0]
        self.floor_y: float = 0.0
        self.floor_restitution: float = 0.6
        self.fixed_dt: float = 1.0 / 60.0

    def set_sun_direction(self, direction: List[float]):
        """设置太阳/主光源方向"""
        self.sun_direction = list(direction)  # 保存到 Python 层
        try:
            self.engine_obj.set_sun_direction(direction)
        except Exception as e:
            raise RuntimeError(f"Environment.set_sun_direction 失败: {e}") from e
    
    def get_sun_direction(self) -> List[float]:
        """获取太阳方向"""
        return self.sun_direction.copy()

    def set_floor_grid(self, enabled: bool):
        """启用或禁用地面网格"""
        self.floor_grid_enabled = bool(enabled)
        try:
            self.engine_obj.set_floor_grid(self.floor_grid_enabled)
        except Exception as e:
            raise RuntimeError(f"Environment.set_floor_grid 失败: {e}") from e

    def get_floor_grid(self) -> bool:
        """获取地面网格开关状态"""
        return self.floor_grid_enabled

    def set_gravity(self, gravity: List[float]):
        """设置重力向量"""
        self.gravity = list(gravity)
        try:
            self.engine_obj.set_gravity(gravity)
        except Exception as e:
            raise RuntimeError(f"Environment.set_gravity 失败: {e}") from e

    def get_gravity(self) -> List[float]:
        """获取重力向量"""
        return self.gravity.copy()

    def set_floor_y(self, y: float):
        """设置地面高度"""
        self.floor_y = float(y)
        try:
            self.engine_obj.set_floor_y(y)
        except Exception as e:
            raise RuntimeError(f"Environment.set_floor_y 失败: {e}") from e

    def get_floor_y(self) -> float:
        """获取地面高度"""
        return self.floor_y

    def set_floor_restitution(self, restitution: float):
        """设置地面弹性系数"""
        self.floor_restitution = float(restitution)
        try:
            self.engine_obj.set_floor_restitution(restitution)
        except Exception as e:
            raise RuntimeError(f"Environment.set_floor_restitution 失败: {e}") from e

    def get_floor_restitution(self) -> float:
        """获取地面弹性系数"""
        return self.floor_restitution

    def set_fixed_dt(self, dt: float):
        """设置物理固定时间步长"""
        self.fixed_dt = float(dt)
        try:
            self.engine_obj.set_fixed_dt(dt)
        except Exception as e:
            raise RuntimeError(f"Environment.set_fixed_dt 失败: {e}") from e

    def get_fixed_dt(self) -> float:
        """获取物理固定时间步长"""
        return self.fixed_dt

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            'name': self.name,
            'sun_direction': self.sun_direction.copy(),
            'floor_grid_enabled': self.floor_grid_enabled,
            'gravity': self.gravity.copy(),
            'floor_y': self.floor_y,
            'floor_restitution': self.floor_restitution,
            'fixed_dt': self.fixed_dt,
            'engine_obj': self.engine_obj,
        }

    def __repr__(self):
        return f"Environment(name={self.name})"
