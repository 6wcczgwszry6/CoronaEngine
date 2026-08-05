import logging
from CoronaPlugin.core.corona_plugin_base import PluginBase
from utils.settings import settings_manager
logger = logging.getLogger(__name__)


@PluginBase.register_web("ProjectLauncher")
class ProjectLauncher(PluginBase):

    @staticmethod
    def get_default_project_path() -> str:
        # 从配置文件读取
        return settings_manager.get_default_path()

    @staticmethod
    def get_app_version() -> str:
        # 从配置文件读取
        return settings_manager.get_version()

    @staticmethod
    def get_recent_projects() -> list:
        """前端初始化时调用，获取历史记录"""
        return settings_manager.get_recent_projects()

    @staticmethod
    def create_project(project_data: dict) -> str:
        """Native-only; C++ ProjectLauncher handler owns project creation."""
        return ""

    @staticmethod
    def create_world_project(world_data: dict) -> dict:
        """Native-only; C++ ProjectLauncher handler owns world project creation."""
        return {}

    @staticmethod
    def create_multiplayer_project(project_data: dict) -> dict:
        """Native-only; C++ ProjectLauncher handler owns multiplayer project creation."""
        return {}

    @staticmethod
    def open_project(project_path: str) -> bool:
        """Native-only; C++ ProjectLauncher handler owns project opening."""
        return False

    @staticmethod
    def set_project_mode(mode_data: dict) -> bool:
        """设置当前编辑器的工作模式 (2D/3D/Render)"""
        mode = mode_data.get("mode")
        settings = mode_data.get("settings")
        logger.info(f"Switching editor mode to: {mode} with settings: {settings}")
        # 这里可以根据模式调整渲染引擎参数
        return True
