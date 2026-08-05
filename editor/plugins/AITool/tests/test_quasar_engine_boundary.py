import re
import unittest
from pathlib import Path


QUASAR_ROOT = Path(__file__).resolve().parents[1] / "Quasar"


class QuasarEngineBoundaryTests(unittest.TestCase):
    def test_quasar_production_code_has_no_engine_imports(self):
        forbidden = re.compile(
            r"(?:from|import)\s+(?:Backend(?:\.|\s)|plugins\.AITool|services(?:\.|\s))"
        )
        violations = []
        for path in QUASAR_ROOT.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if forbidden.search(text):
                violations.append(str(path.relative_to(QUASAR_ROOT)))
        self.assertEqual([], violations)

    def test_quasar_model_tools_uses_injected_scheduler_protocol(self):
        path = QUASAR_ROOT / "ai_modules" / "three_d_generate" / "tools" / "model_tools.py"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("generation_provider_adapter", text)

    def test_default_paths_do_not_invent_engine_layout(self):
        import importlib.util
        import sys

        path = QUASAR_ROOT / "ai_config" / "paths_config.py"
        spec = importlib.util.spec_from_file_location("quasar_paths_boundary", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        paths = module.get_default_paths()
        self.assertIsNone(paths.backend_root)
        self.assertIsNone(paths.frontend_dist)
        self.assertIsNone(paths.script_dir)

    def test_local_storage_accepts_explicit_storage_root(self):
        path = QUASAR_ROOT / "ai_media_resource" / "adapter_local.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn("storage_root", text)
        self.assertNotIn("Backend.local_storage", text)


if __name__ == "__main__":
    unittest.main()
