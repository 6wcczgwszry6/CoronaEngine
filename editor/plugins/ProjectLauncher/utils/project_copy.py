import os
import shutil
import configparser
import datetime
import logging

from CoronaCore.utils.proejct_utils import (
    create_project_from_template,
    normalize_project_runtime_paths,
    update_project_config,
)
from utils.settings import core_path, settings_manager

logger = logging.getLogger(__name__)


def _safe_project_dir_name(name, fallback):
    raw_name = (name or fallback or "project").strip()
    safe_name = "".join("_" if c in '<>:"/\\|?*' else c for c in raw_name)
    safe_name = safe_name.strip(" .")
    return safe_name or "project"


class ProjectCopy:
    @staticmethod
    def create_from_template(target_path, project_name, mode):
        """从 Launcher 目录下的 project 复制并初始化新项目"""
        try:

            project_ini = create_project_from_template(target_path, project_name, mode)
            normalize_project_runtime_paths(os.path.dirname(project_ini))
            # 记录到全局历史
            settings_manager.add_recent_project(os.path.dirname(project_ini))

            return project_ini
        except Exception as e:
            logger.error(f"ProjectCopy Error: {e}")
            raise e

    @staticmethod
    def copy_existing_to_data(project_ini_path):
        """Copy an existing project save into the runtime data directory."""
        source_ini = os.path.abspath(project_ini_path)
        if not os.path.isfile(source_ini):
            raise FileNotFoundError(f"project.ini not found: {source_ini}")

        source_dir = os.path.dirname(source_ini)
        project_name = os.path.basename(source_dir)

        config = configparser.ConfigParser()
        config.read(source_ini, encoding='utf-8')
        if 'Project' in config:
            project_name = config['Project'].get('name', project_name)

        data_dir = os.path.join(str(core_path.repo_root), "data")
        os.makedirs(data_dir, exist_ok=True)

        base_name = _safe_project_dir_name(project_name, os.path.basename(source_dir))
        target_path = os.path.join(data_dir, base_name)
        counter = 1
        while os.path.exists(target_path):
            target_path = os.path.join(data_dir, f"{base_name}_{counter}")
            counter += 1

        shutil.copytree(source_dir, target_path)
        normalize_project_runtime_paths(target_path)

        target_ini = os.path.join(target_path, "project.ini")
        target_config = configparser.ConfigParser()
        target_config.read(target_ini, encoding='utf-8')
        if 'Project' not in target_config:
            target_config['Project'] = {}
        final_name = os.path.basename(target_path)
        target_config['Project']['name'] = final_name
        with open(target_ini, 'w', encoding='utf-8') as f:
            target_config.write(f)

        logger.info("Copied existing project save: %s -> %s", source_dir, target_path)
        return {"name": final_name, "path": target_path}

    @staticmethod
    def open_and_update(project_path):
        """执行打开逻辑，更新最后访问时间"""
        if not os.path.exists(project_path):
            return False

        try:
            normalize_project_runtime_paths(project_path)
            project_ini = os.path.join(project_path, "project.ini")
            update_project_config(project_ini, update_only_time=True)
            settings_manager.set_active_project(project_path)
            return True
        except Exception as e:
            logger.error(f"Open Update Error: {e}")
            return False


