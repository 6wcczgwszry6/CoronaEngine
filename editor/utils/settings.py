import os
import configparser
import logging
import shutil
import json
import datetime
from CoronaCore.core.corona_editor import CoronaEditor
from CoronaCore.utils import settings

logger = logging.getLogger(__name__)


class CoronaSettings:
    """
    管理 CoronaEditor.ini 配置文件
    支持版本号、最近项目列表、默认路径等配置项
    """

    def __init__(self, config_path=None):
        self.project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if config_path is None:
            # 默认存放在执行文件同级目录，或者用户文档目录
            self.config_path = os.path.join(os.getcwd(), "CoronaEditor.ini")
        else:
            self.config_path = config_path

        self.config = configparser.ConfigParser()
        self.active_project_path = None  # 当前项目路径
        self.active_project_config = None  # 当前项目的 project.ini 内容
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """
        确保配置文件存在。
        如果指定路径不存在，则尝试从项目根目录复制模板 ini 文件。
        """
        if not os.path.exists(self.config_path):
            # 这里的 template_path 指向你项目源码中的那个 CoronaEditor.ini
            template_path = os.path.join(self.project_path, "CoronaEditor.ini")

            if os.path.exists(template_path):
                try:
                    shutil.copy2(template_path, self.config_path)
                    logger.info(f"Config initialized from template: {template_path}")
                except Exception as e:
                    logger.error(f"Failed to copy template config: {e}")

            self.load()
        else:
            self.load()

    def load(self):
        """从磁盘加载配置"""
        try:
            self.config.read(self.config_path, encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    def save(self):
        """保存配置到磁盘"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    # --- 具体的 Getter / Setter ---

    def get_version(self) -> str:
        return self.config.get('General', 'version', fallback='1.0.0')

    def set_version(self, version: str):
        self.config.set('General', 'version', version)
        self.save()

    def get_recent_projects(self) -> list:
        """读取最近项目路径列表，并解析 project.ini 获取名称"""
        raw = self.config.get('History', 'recent_projects', fallback='[]')

        try:
            path_list = json.loads(raw)
        except:
            return []

        refined_projects = []
        remove_list = []
        for raw_path in path_list:
            # 拼接项目内部 project.ini 的完整路径
            ini_path = os.path.join(raw_path, "project.ini")

            # 默认名称设为文件夹名，防止 ini 不存在或读取失败
            project_name = os.path.basename(raw_path)

            if os.path.exists(ini_path):
                try:
                    # 创建临时的配置解析器读取项目信息
                    proj_cfg = configparser.ConfigParser()
                    proj_cfg.read(ini_path, encoding='utf-8')
                    project_name = proj_cfg.get('Project', 'name', fallback=project_name)
                except Exception as e:
                    logger.warning(f"Failed to read project info at {ini_path}: {e}")
                refined_projects.append({
                    "name": project_name,
                    "path": raw_path,
                    "if_exists": True
                })
            else:
                refined_projects.append({
                    "name": project_name,
                    "path": raw_path,
                    "if_exists": False
                })
        return refined_projects

    def add_recent_project(self, project_path: str):
        """添加项目到最近列表，保持最大数量限制（例如10个）"""
        projects = json.loads(self.config.get('History', 'recent_projects', fallback='[]'))

        # 如果已存在则先移除，保证新加入的在最前面
        if project_path in projects:
            projects.remove(project_path)

        projects.insert(0, project_path)

        # 限制数量为 10
        projects = projects[:10]

        self.config.set('History', 'recent_projects', json.dumps(projects, ensure_ascii=False))
        self.save()

    def get_default_path(self) -> str:
        path = self.config.get('General', 'default_path', fallback='')
        return path

    def set_default_path(self, path: str):
        self.config.set('General', 'default_path', path)
        self.save()

    def set_active_project(self, project_path: str):
        """设置当前激活的项目，并加载其配置"""
        if not os.path.exists(project_path):
            logger.error(f"Project path does not exist: {project_path}")
            return False

        ini_path = os.path.join(project_path, "project.ini")
        if not os.path.exists(ini_path):
            logger.error(f"project.ini not found in {project_path}")
            return False

        try:
            # 1. 加载项目配置
            proj_cfg = configparser.ConfigParser()
            proj_cfg.read(ini_path, encoding='utf-8')

            self.active_project_path = project_path
            CoronaEditor.CoronaEngine.active_project_path = project_path
            self.active_project_config = proj_cfg

            # 2. 更新全局配置中的“最后一次打开的项目”
            self.config.set('General', 'last_project', project_path)

            # 3. 顺便添加到最近项目列表
            self.add_recent_project(project_path)
            self.save()

            logger.info(f"Active project set to: {project_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load project config: {e}")
            return False

    def get_active_project_info(self) -> dict:
        """获取当前项目的所有配置信息"""
        if not self.active_project_config:
            return {}

        info = {}
        for section in self.active_project_config.sections():
            info[section] = dict(self.active_project_config.items(section))
        return info

    def save_active_project_info(self) -> bool:
        """
        保存当前激活项目的配置信息
        :param settings: 要保存的配置字典，包含 name, mode, entrance_scene, core_version 等字段
        :return: 是否保存成功
        """
        if not self.active_project_path:
            logger.error("未激活任何项目，无法保存配置")
            return False

        self.active_project_config.set('Project', 'last_opened', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # 写回文件
        ini_path = os.path.join(self.active_project_path, "project.ini")
        try:
            with open(ini_path, 'w', encoding='utf-8') as f:
                self.active_project_config.write(f)
            logger.info(f"项目配置保存成功: {ini_path}")
            return True
        except Exception as e:
            logger.error(f"保存项目配置文件失败: {e}")
            return False

# 全局单例
settings_manager = CoronaSettings()