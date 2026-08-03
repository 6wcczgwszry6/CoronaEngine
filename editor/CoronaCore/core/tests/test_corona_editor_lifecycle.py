import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class CoronaEditorLifecycleTests(unittest.TestCase):
    def _load_editor(self):
        engine = SimpleNamespace()
        corona_engine = ModuleType("CoronaCore.core.corona_engine")
        corona_engine.get_corona_engine = lambda: engine
        settings = ModuleType("utils.settings")
        settings.core_path = SimpleNamespace(frontend_dist="")
        responses = ModuleType("CoronaCore.utils.response_utils")
        responses.create_error_response = lambda message: {"error": message}
        responses.create_success_response = lambda value: {"data": value}
        editor_path = Path(__file__).resolve().parents[1] / "corona_editor.py"
        spec = importlib.util.spec_from_file_location("test_corona_editor_lifecycle_module", editor_path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {
            "CoronaCore.core.corona_engine": corona_engine,
            "utils.settings": settings,
            "CoronaCore.utils.response_utils": responses,
        }):
            spec.loader.exec_module(module)
        return module.CoronaEditor

    def test_shutdown_runtime_stops_services_and_clears_dispatch_state(self):
        editor = self._load_editor()
        calls = []
        scripts = SimpleNamespace(shutdown=lambda: calls.append("scripts"))
        registry = ModuleType("backend.registry")
        registry.shutdown_python_script_services = (
            lambda timeout: calls.append(("services", timeout)) or [{"state": "stopped"}]
        )
        editor.scripts_mgr = scripts
        editor.module_list = {"AITool": object(), "SceneTools": object()}
        editor._runtime_state = "running"
        editor._runtime_initialized = True
        editor._runtime_started = True
        editor.unregister_script_dispatcher = classmethod(lambda cls: calls.append("dispatcher"))
        backend = ModuleType("backend")
        backend.registry = registry

        with patch.dict(sys.modules, {"backend": backend, "backend.registry": registry}):
            result = editor.shutdown_runtime()

        self.assertTrue(result)
        self.assertEqual(calls, [("services", 2.0), "scripts", "dispatcher"])
        self.assertEqual(editor.module_list, {})
        self.assertEqual(editor._runtime_state, "stopped")


if __name__ == "__main__":
    unittest.main()
