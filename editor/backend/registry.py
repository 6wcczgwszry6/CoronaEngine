import logging
import threading
from importlib import import_module

from CoronaCore.core.corona_editor import CoronaEditor


_SCRIPT_PACKAGE = __package__ or "backend"
logger = logging.getLogger(__name__)


PYTHON_SCRIPT_SERVICES = {
    "ProjectArchive": ("plugins.ProjectArchive.main", "ProjectArchive"),
    "AITool": ("plugins.AITool.main", "AITool"),
    "ScratchTool": (f"{_SCRIPT_PACKAGE}.blockly.main", "ScratchTool"),
    "MainView": ("plugins.MainView.main", "MainView"),
    "ProjectLauncher": ("plugins.ProjectLauncher.main", "ProjectLauncher"),
    "FileManager": (f"{_SCRIPT_PACKAGE}.file_system.main", "FileManager"),
    "ProjectSettings": (f"{_SCRIPT_PACKAGE}.project_settings.main", "ProjectSettings"),
    "SceneDatas": ("plugins.SceneDatas.main", "SceneDatas"),
    "SceneTools": ("plugins.SceneTools.main", "SceneTools"),
}

CORE_PYTHON_SCRIPT_SERVICES = {"ProjectArchive"}
LAZY_PYTHON_SCRIPT_SERVICES = {"AITool"}


class PythonScriptService:
    def __init__(self, module_name, target):
        self.module_name = module_name
        self._target = target

    def __getattr__(self, name):
        return getattr(self._target, name)


class LazyPythonScriptService:
    def __init__(self, module_name, module_path, class_name):
        self.module_name = module_name
        self._module_path = module_path
        self._class_name = class_name
        self._target = None
        self._load_lock = threading.Lock()

    def _load_target(self):
        if self._target is not None:
            return self._target
        with self._load_lock:
            if self._target is None:
                module = import_module(self._module_path)
                initializer = getattr(module, "initialize_script_service", None)
                if callable(initializer):
                    initializer()
                self._target = getattr(module, self._class_name)
        return self._target

    def __getattr__(self, name):
        return getattr(self._load_target(), name)


def _register_python_script_services(service_names):
    registered = []
    for service_name in service_names:
        if service_name not in PYTHON_SCRIPT_SERVICES:
            continue
        module_path, class_name = PYTHON_SCRIPT_SERVICES[service_name]
        try:
            if service_name in LAZY_PYTHON_SCRIPT_SERVICES:
                service = LazyPythonScriptService(
                    service_name,
                    module_path,
                    class_name,
                )
            else:
                module = import_module(module_path)
                service_class = getattr(module, class_name)
                service = PythonScriptService(service_name, service_class)
            CoronaEditor.register_page(
                service_name,
                service,
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


def register_python_script_services():
    return _register_python_script_services(PYTHON_SCRIPT_SERVICES)


def register_core_python_script_services():
    return _register_python_script_services(
        name
        for name in PYTHON_SCRIPT_SERVICES
        if name in CORE_PYTHON_SCRIPT_SERVICES
    )


def register_remaining_python_script_services():
    return _register_python_script_services(
        name
        for name in PYTHON_SCRIPT_SERVICES
        if name not in CORE_PYTHON_SCRIPT_SERVICES
    )
