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
        self._state = "cold"
        self._initialization_error = None
        self._state_lock = threading.Lock()
        self._initialization_finished = threading.Event()

    @property
    def state(self):
        with self._state_lock:
            return self._state

    def start_background_load(self):
        with self._state_lock:
            if self._state != "cold":
                return
            self._state = "initializing"
            worker = threading.Thread(
                target=self._load_target,
                name=f"{self.module_name}Initializer",
                daemon=True,
            )
        worker.start()

    def wait_for_initialization(self, timeout=None):
        self.start_background_load()
        return self._initialization_finished.wait(timeout)

    def _load_target(self):
        try:
            module = import_module(self._module_path)
            initializer = getattr(module, "initialize_script_service", None)
            if callable(initializer):
                initializer()
            target = getattr(module, self._class_name)
            with self._state_lock:
                self._target = target
                self._state = "ready"
            logger.info(
                "Python script service %s initialized in background",
                self.module_name,
            )
        except Exception as error:
            with self._state_lock:
                self._initialization_error = error
                self._state = "degraded"
            logger.exception(
                "Failed to initialize Python script service %s from %s.%s",
                self.module_name,
                self._module_path,
                self._class_name,
            )
        finally:
            self._initialization_finished.set()

    def _unavailable_result(self, state, error):
        if state == "degraded":
            return {
                "success": False,
                "status": "degraded",
                "message": (
                    f"{self.module_name} initialization failed: {error}"
                ),
            }
        return {
            "success": False,
            "status": "initializing",
            "message": f"{self.module_name} is initializing",
        }

    def __getattr__(self, name):
        def invoke(*args, **kwargs):
            self.start_background_load()
            with self._state_lock:
                target = self._target
                state = self._state
                error = self._initialization_error
            if target is not None:
                return getattr(target, name)(*args, **kwargs)
            return self._unavailable_result(state, error)

        return invoke


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
            if isinstance(service, LazyPythonScriptService):
                service.start_background_load()
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
