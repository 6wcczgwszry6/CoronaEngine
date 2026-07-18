import os
import datetime
import logging
from CoronaPlugin.core.corona_plugin_base import PluginBase
from CoronaCore.utils.file_handler import FileHandler
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
    def browse_folder(default_path) -> str:
        """弹出文件夹选择对话框"""
        # 假设 FileHandler 有选择目录的方法，若没有可调用底层 QFileDialog
        path = FileHandler.open_directory(caption="选择项目保存位置",default_dir=default_path)
        return path if path else ""

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

    @staticmethod
    def open_project_file() -> dict:
        """
        弹出文件选择框，可选 project.ini 项目，或 Vision 场景 .json。
        Python 侧只负责文件对话框。返回的 path 交给 C++ ProjectLauncher.open_project
        处理 .ini 复制、目录打开或 Vision .json 导入。
        """
        # 1. 弹出对话框：项目 .ini 或 Vision 场景 .json
        _, file_path = FileHandler.open_file(
            caption="打开项目或 Vision 场景",
            file_types="项目或 Vision 场景 (*.ini *.json)",
            default_dir=settings_manager.get_default_path(),
            read_content=False
        )

        if not file_path or not os.path.exists(file_path):
            return {}

        abs_path = os.path.abspath(file_path)
        return {"name": os.path.splitext(os.path.basename(abs_path))[0], "path": abs_path}
