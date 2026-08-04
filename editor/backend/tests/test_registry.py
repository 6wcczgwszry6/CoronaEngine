import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class PythonScriptServiceRegistryTests(unittest.TestCase):
    def _load_registry(self):
        corona_editor_module = ModuleType("CoronaCore.core.corona_editor")
        corona_editor_module.CoronaEditor = SimpleNamespace(register_page=lambda *_: None)
        registry_path = Path(__file__).resolve().parents[1] / "registry.py"
        spec = importlib.util.spec_from_file_location(
            "test_python_script_service_registry",
            registry_path,
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict(
            sys.modules,
            {"CoronaCore.core.corona_editor": corona_editor_module},
        ):
            spec.loader.exec_module(module)
        return module

    def test_project_archive_service_is_registered_for_native_project_opening(self):
        registry = self._load_registry()

        self.assertIn("ProjectArchive", registry.PYTHON_SCRIPT_SERVICES)
        self.assertEqual(
            registry.PYTHON_SCRIPT_SERVICES["ProjectArchive"],
            ("plugins.ProjectArchive.main", "ProjectArchive"),
        )
        self.assertEqual(
            next(iter(registry.PYTHON_SCRIPT_SERVICES)),
            "ProjectArchive",
        )

    def test_later_services_register_when_an_earlier_import_fails(self):
        registry = self._load_registry()
        registry.PYTHON_SCRIPT_SERVICES = {
            "BrokenService": ("services.broken", "BrokenService"),
            "ProjectLauncher": ("services.project_launcher", "ProjectLauncher"),
        }
        project_launcher = object()
        registered_pages = []

        def import_service(module_path):
            if module_path == "services.broken":
                raise RuntimeError("broken dependency")
            return SimpleNamespace(ProjectLauncher=project_launcher)

        registry.CoronaEditor.register_page = (
            lambda service_name, service: registered_pages.append(
                (service_name, service),
            )
        )

        with patch.object(registry, "import_module", side_effect=import_service):
            with self.assertLogs(registry.logger, level="ERROR") as logs:
                registered = registry.register_python_script_services()

        self.assertEqual(registered, ["ProjectLauncher"])
        self.assertEqual(
            [(name, service._target) for name, service in registered_pages],
            [("ProjectLauncher", project_launcher)],
        )
        self.assertIn("BrokenService", "\n".join(logs.output))
        self.assertIn("services.broken", "\n".join(logs.output))

    def test_aitool_is_registered_without_import_until_first_use(self):
        registry = self._load_registry()
        registry.PYTHON_SCRIPT_SERVICES = {
            "ProjectArchive": ("services.archive", "ProjectArchive"),
            "AITool": ("services.ai", "AITool"),
        }
        registry.LAZY_PYTHON_SCRIPT_SERVICES = {"AITool"}
        imported = []
        initialized = []
        registered_pages = {}
        archive_service = SimpleNamespace(parse=lambda payload: payload)
        ai_service = SimpleNamespace(submit_request=lambda payload: {"ok": payload})

        def import_service(module_path):
            imported.append(module_path)
            if module_path == "services.archive":
                return SimpleNamespace(ProjectArchive=archive_service)
            return SimpleNamespace(
                AITool=ai_service,
                initialize_script_service=lambda: initialized.append("AITool"),
            )

        registry.CoronaEditor.register_page = (
            lambda service_name, service: registered_pages.__setitem__(
                service_name,
                service,
            )
        )

        with patch.object(registry, "import_module", side_effect=import_service):
            registered = registry.register_python_script_services()
            self.assertEqual(imported, ["services.archive"])
            self.assertEqual(initialized, [])
            self.assertEqual(
                registered_pages["AITool"].submit_request("hello"),
                {"ok": "hello"},
            )
            self.assertEqual(imported, ["services.archive", "services.ai"])
            self.assertEqual(initialized, ["AITool"])

        self.assertEqual(registered, ["ProjectArchive", "AITool"])


if __name__ == "__main__":
    unittest.main()
