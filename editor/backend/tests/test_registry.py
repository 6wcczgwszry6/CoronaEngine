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


if __name__ == "__main__":
    unittest.main()
