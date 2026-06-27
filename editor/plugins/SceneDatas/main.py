from CoronaCore.core.corona_editor import CoronaEditor
from CoronaCore.utils.file_handler import FileHandler, _FILE_TYPE_CONFIG
from CoronaPlugin.core.corona_plugin_base import PluginBase
import logging

logger = logging.getLogger(__name__)


@PluginBase.register_web("SceneDatas")
class SceneDatas(PluginBase):
    @staticmethod
    def select_model_file(scene_name: str, actor_name: str, file_type: str = "model") -> str:
        config = _FILE_TYPE_CONFIG.get(file_type)
        if not config:
            raise ValueError(f"不支持的文件类型: {file_type}")

        title, filter_str = config

        init_path = CoronaEditor.CoronaEngine.active_project_path if CoronaEditor.CoronaEngine.active_project_path else None
        content, file_path = FileHandler.open_file(title, filter_str, init_path, read_content=False,
                                                   return_relative_path=True)
        logger.info(file_path)
        if not file_path:
            return ""

        return file_path
