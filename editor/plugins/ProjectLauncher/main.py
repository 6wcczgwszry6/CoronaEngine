import json
import os
import datetime
import logging
from CoronaCore.core.corona_editor import CoronaEditor
from CoronaCore.core.entities.scene import (
    VISION_DOCUMENT_ENCODING,
    VISION_DOCUMENT_VERSION,
    _encode_vision_document,
)
from CoronaPlugin.core.corona_plugin_base import PluginBase
from CoronaCore.utils.file_handler import FileHandler
from plugins.SceneTools.main import _vision_document_for_embedded_storage
from utils.settings import settings_manager
from .utils.project_copy import ProjectCopy
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
        """创建项目目录及初始化文件"""
        name = project_data.get("name")
        base_dir = project_data.get("path")
        mode = project_data.get("mode", "3d")  # 获取前端传来的 mode
        target_full_path = os.path.join(base_dir, name)

        # 调用工具类处理物理复制和配置修改
        ProjectCopy.create_from_template(target_full_path, name, mode)
        settings_manager.set_default_path(base_dir)
        return target_full_path

    @staticmethod
    def create_world_project(world_data: dict) -> dict:
        """AI 世界创建专用：自动命名 + 保存到引擎 data 目录，无需用户指定 name/path。

        与 create_project 的区别：不接收 name/path，全部由后端决定：
        - 保存位置固定为引擎根目录下的 data/（core_path.repo_root/data）
        - 展示名称按"模式 + 递增编号"自动生成（创造世界_1 / 剧情世界_1 ...）
        - 磁盘目录使用 ASCII（creative_world_1 / story_world_1 ...），避免原生侧中文路径问题
        - 把 worldPrompt 写入 project.ini 的 [Project] world_prompt，供引擎/AI 后续读取
        返回 {name, path}，与打开普通项目的返回结构一致。
        """
        import configparser
        from utils.settings import core_path

        mode = world_data.get("mode", "creative")
        prompt = world_data.get("prompt", "") or ""

        # 引擎 data 目录（不存在则创建）
        base_dir = os.path.join(str(core_path.repo_root), "data")
        os.makedirs(base_dir, exist_ok=True)

        # 模式 + 递增编号，防重名。磁盘目录使用 ASCII，避免原生/引擎侧处理中文路径时崩溃；
        # project.ini 和返回 name 仍保留中文展示名。
        label = "剧情世界" if mode == "story" else "创造世界"
        path_prefix = "story_world" if mode == "story" else "creative_world"
        index = 1
        while (
            os.path.exists(os.path.join(base_dir, f"{path_prefix}_{index}"))
            or os.path.exists(os.path.join(base_dir, f"{label}_{index}"))
        ):
            index += 1
        display_name = f"{label}_{index}"
        dir_name = f"{path_prefix}_{index}"
        target_full_path = os.path.join(base_dir, dir_name)

        # 复制模板并初始化 project.ini
        project_ini = ProjectCopy.create_from_template(target_full_path, display_name, mode)

        # 把世界提示词持久化进 project.ini，供引擎/AI 后续读取
        try:
            cfg = configparser.ConfigParser()
            cfg.read(project_ini, encoding='utf-8')
            if 'Project' not in cfg:
                cfg['Project'] = {}
            cfg['Project']['world_prompt'] = prompt
            with open(project_ini, 'w', encoding='utf-8') as f:
                cfg.write(f)
        except Exception as e:
            logger.error(f"Failed to persist world_prompt: {e}")

        return {"name": display_name, "path": os.path.dirname(project_ini)}

    @staticmethod
    def create_multiplayer_project(project_data: dict) -> dict:
        """首页联机入口专用：自动创建一个 ASCII 路径的临时联机项目。"""
        import configparser
        from utils.settings import core_path

        role = project_data.get("role", "guest")
        role = "host" if role == "host" else "guest"
        label = "联机房主" if role == "host" else "联机加入"
        path_prefix = "multiplayer_host" if role == "host" else "multiplayer_guest"

        base_dir = os.path.join(str(core_path.repo_root), "data")
        os.makedirs(base_dir, exist_ok=True)

        index = 1
        while os.path.exists(os.path.join(base_dir, f"{path_prefix}_{index}")):
            index += 1

        display_name = f"{label}_{index}"
        target_full_path = os.path.join(base_dir, f"{path_prefix}_{index}")
        project_ini = ProjectCopy.create_from_template(target_full_path, display_name, "3d")

        try:
            cfg = configparser.ConfigParser()
            cfg.read(project_ini, encoding='utf-8')
            if 'Project' not in cfg:
                cfg['Project'] = {}
            cfg['Project']['multiplayer_role'] = role
            with open(project_ini, 'w', encoding='utf-8') as f:
                cfg.write(f)
        except Exception as e:
            logger.error(f"Failed to persist multiplayer metadata: {e}")

        return {"name": display_name, "path": os.path.dirname(project_ini), "role": role}

    @staticmethod
    def open_project(project_path: str) -> bool:
        """执行打开项目的逻辑（加载资源、初始化环境等）"""
        return ProjectCopy.open_and_update(project_path)

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
        选中 .json 时即时新建一个轻量项目（external_live 模式）承载，返回其目录，
        前端按打开普通项目的流程处理即可；引擎启动后由 MainView 自动加载/导入。
        成功后返回项目信息并更新最近项目列表。
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

        # 2a. Vision 场景：新建轻量项目承载
        if file_path.lower().endswith('.json'):
            return ProjectLauncher._create_project_from_vision(file_path)

        # 2b. Existing .ini save: copy it into runtime data before opening.
        try:
            return ProjectCopy.copy_existing_to_data(file_path)
        except Exception as e:
            logger.error(f"Failed to open project file: {e}")
            return {}

    @staticmethod
    def _create_project_from_vision(json_path: str) -> dict:
        """为一个 Vision 场景 .json 新建轻量项目（纯文件 IO，不依赖引擎）。

        复制项目模板，把 Vision JSON 文档嵌入入口场景的 .scene 文件；
        真正的代理 actor / 相机 / 绑定导入延迟到引擎启动后完成。
        返回 {name, path}，与打开普通项目的返回结构一致。
        """
        try:
            if not CoronaEditor.CoronaEngine.is_vision_available():
                logger.error("Vision backend is not available in this build")
                return {}
            abs_json = os.path.abspath(json_path)
            if not os.path.isfile(abs_json):
                logger.error("Vision scene file not found: %s", abs_json)
                return {}

            base_dir = settings_manager.get_default_path()
            project_name = os.path.splitext(os.path.basename(abs_json))[0]

            # 目标目录重名则加后缀
            target_path = os.path.join(base_dir, project_name)
            counter = 1
            while os.path.exists(target_path):
                target_path = os.path.join(base_dir, f"{project_name}_{counter}")
                counter += 1
            final_name = os.path.basename(target_path)

            # 1. 复制项目模板（写 project.ini，加入最近项目）
            project_ini = ProjectCopy.create_from_template(target_path, final_name, '3d')
            project_dir = os.path.dirname(project_ini)

            # 2. 定位模板入口场景文件
            import configparser
            cfg = configparser.ConfigParser()
            cfg.read(project_ini, encoding='utf-8')
            entrance = cfg.get('Project', 'entrance_scene', fallback='').strip()
            if not entrance:
                logger.error("Template project has no entrance_scene: %s", project_ini)
                return {}
            scene_file = os.path.join(project_dir, *entrance.split('/'))
            if not os.path.isfile(scene_file):
                logger.error("Entrance scene file not found: %s", scene_file)
                return {}

            with open(abs_json, 'r', encoding='utf-8') as f:
                vision_document = _vision_document_for_embedded_storage(json.load(f), abs_json)

            # 3. 往入口 .scene 注入内嵌 Vision JSON 文档（格式同 Scene.save_data）
            scene_cfg = configparser.ConfigParser()
            scene_cfg.read(scene_file, encoding='utf-8')
            if 'vision' in scene_cfg:
                scene_cfg.remove_section('vision')
            scene_cfg['vision_document'] = {
                'encoding': VISION_DOCUMENT_ENCODING,
                'version': VISION_DOCUMENT_VERSION,
                'data': _encode_vision_document(vision_document),
            }
            with open(scene_file, 'w', encoding='utf-8') as f:
                scene_cfg.write(f)

            logger.info("Created lightweight project for Vision scene: %s -> %s", abs_json, project_dir)
            return {"name": final_name, "path": project_dir}
        except Exception as e:
            logger.exception("Failed to create project from Vision scene: %s", e)
            return {}
