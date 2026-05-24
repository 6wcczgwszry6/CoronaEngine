import os
import shutil
import configparser
import datetime
import logging

from CoronaCore.utils.proejct_utils import update_project_config,create_project_from_template
from utils.settings import settings_manager

logger = logging.getLogger(__name__)


class ProjectCopy:
    @staticmethod
    def create_from_template(target_path, project_name, mode):
        """从 Launcher 目录下的 project 复制并初始化新项目"""
        try:

            project_ini = create_project_from_template(target_path, project_name, mode)
            # 记录到全局历史
            settings_manager.add_recent_project(os.path.dirname(project_ini))

            return project_ini
        except Exception as e:
            logger.error(f"ProjectCopy Error: {e}")
            raise e

    @staticmethod
    def open_and_update(project_path):
        """执行打开逻辑，更新最后访问时间"""
        if not os.path.exists(project_path):
            return False

        try:
            project_ini = os.path.join(project_path, "project.ini")
            update_project_config(project_ini, update_only_time=True)
            settings_manager.set_active_project(project_path)
            return True
        except Exception as e:
            logger.error(f"Open Update Error: {e}")
            return False


