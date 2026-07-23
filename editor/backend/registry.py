import logging
from importlib import import_module

from CoronaCore.core.corona_editor import CoronaEditor


_SCRIPT_PACKAGE = __package__ or "backend"
logger = logging.getLogger(__name__)


PYTHON_SCRIPT_SERVICES = {
    "AITool": ("plugins.AITool.main", "AITool"),
    "ScratchTool": (f"{_SCRIPT_PACKAGE}.blockly.main", "ScratchTool"),
    "MainView": ("plugins.MainView.main", "MainView"),
    "ProjectLauncher": ("plugins.ProjectLauncher.main", "ProjectLauncher"),
    "FileManager": (f"{_SCRIPT_PACKAGE}.file_system.main", "FileManager"),
    "ProjectSettings": (f"{_SCRIPT_PACKAGE}.project_settings.main", "ProjectSettings"),
    "SceneDatas": ("plugins.SceneDatas.main", "SceneDatas"),
    "SceneTools": ("plugins.SceneTools.main", "SceneTools"),
}


class PythonScriptService:
    def __init__(self, module_name, target):
        self.module_name = module_name
        self._target = target

    def __getattr__(self, name):
        return getattr(self._target, name)


def register_python_script_services():
    registered = []
    for service_name, (module_path, class_name) in PYTHON_SCRIPT_SERVICES.items():
        try:
            module = import_module(module_path)
            service_class = getattr(module, class_name)
            CoronaEditor.register_page(
                service_name,
                PythonScriptService(service_name, service_class),
            )
            registered.append(service_name)
        except Exception:
            logger.exception(
                "Failed to register Python script service %s from %s.%s",
                service_name,
                module_path,
                class_name,
            )
    return registered
