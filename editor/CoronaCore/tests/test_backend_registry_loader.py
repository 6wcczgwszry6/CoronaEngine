import sys
import tempfile
import types
import unittest
from pathlib import Path

EDITOR_ROOT = Path(__file__).resolve().parents[2]
if str(EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(EDITOR_ROOT))

from CoronaCore.core.corona_editor import CoronaEditor
from CoronaPlugin.core.corona_plugin_base import PluginBase
from CoronaPlugin.utils import load_utils
from backend.registry import PythonBackendService


class BackendRegistryLoaderTests(unittest.TestCase):
    def test_reimport_uses_explicit_backend_registry_without_plugin_scan(self):
        calls = []
        fake_registry = types.ModuleType("backend.registry")
        def register_python_backends():
            calls.append("registered")
            return ["FakeBackend"]

        fake_registry.register_python_backends = register_python_backends
        previous_registry = sys.modules.get("backend.registry")
        sys.modules["backend.registry"] = fake_registry

        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir)
            marker_path = plugins_dir / "legacy_plugin_imported.txt"
            legacy_dir = plugins_dir / "LegacyPagePlugin"
            legacy_dir.mkdir()
            (legacy_dir / "main.py").write_text(
                f"from pathlib import Path\nPath({str(marker_path)!r}).write_text('imported')\n",
                encoding="utf-8",
            )
            try:
                load_utils.reimport()
            finally:
                if previous_registry is None:
                    sys.modules.pop("backend.registry", None)
                else:
                    sys.modules["backend.registry"] = previous_registry

        self.assertEqual(calls, ["registered"])
        self.assertFalse(marker_path.exists())

    def test_register_web_only_marks_module_name_without_rpc_registration(self):
        previous_modules = dict(CoronaEditor.module_list)
        CoronaEditor.module_list = {}

        try:
            decorated = PluginBase.register_web("LegacyPage")(
                type("LegacyPageBackend", (PluginBase,), {})
            )
        finally:
            modules_after = dict(CoronaEditor.module_list)
            CoronaEditor.module_list = previous_modules

        self.assertEqual(decorated.module_name, "LegacyPage")
        self.assertEqual(modules_after, {})

    def test_python_backend_service_delegates_to_target_without_page_class_registration(self):
        class LegacyPageBackend:
            @staticmethod
            def ping(value):
                return {"pong": value}

        service = PythonBackendService("ProjectPersistence", LegacyPageBackend)

        self.assertEqual(service.module_name, "ProjectPersistence")
        self.assertEqual(service.ping("ok"), {"pong": "ok"})
        self.assertNotIsInstance(service, type)


if __name__ == "__main__":
    unittest.main()
