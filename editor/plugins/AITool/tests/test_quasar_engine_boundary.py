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


if __name__ == "__main__":
    unittest.main()
