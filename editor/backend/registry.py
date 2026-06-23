from importlib import import_module

from CoronaCore.core.corona_editor import CoronaEditor


_BACKEND_PACKAGE = __package__ or "backend"


PYTHON_BACKEND_SERVICES = {
    "AITool": ("plugins.AITool.main", "AITool"),
    "ScratchTool": (f"{_BACKEND_PACKAGE}.blockly.main", "ScratchTool"),
    "MainView": ("plugins.MainView.main", "MainView"),
    "ProjectLauncher": ("plugins.ProjectLauncher.main", "ProjectLauncher"),
    "FileManager": (f"{_BACKEND_PACKAGE}.file_system.main", "FileManager"),
    "ProjectSettings": (f"{_BACKEND_PACKAGE}.project_settings.main", "ProjectSettings"),
    "SceneDatas": ("plugins.SceneDatas.main", "SceneDatas"),
    "SceneTools": ("plugins.SceneTools.main", "SceneTools"),
}


class PythonBackendService:
    def __init__(self, module_name, target):
        self.module_name = module_name
        self._target = target

    def __getattr__(self, name):
        return getattr(self._target, name)


def register_python_backends():
    registered = []
    for service_name, (module_path, class_name) in PYTHON_BACKEND_SERVICES.items():
        module = import_module(module_path)
        service_class = getattr(module, class_name)
        CoronaEditor.register_page(
            service_name,
            PythonBackendService(service_name, service_class),
        )
        registered.append(service_name)
    return registered
