import importlib.util
import threading
import unittest
from pathlib import Path


QUASAR_ROOT = Path(__file__).resolve().parents[1] / "Quasar"


def load_warmup_module():
    module_path = QUASAR_ROOT / "ai_tools" / "warmup.py"
    spec = importlib.util.spec_from_file_location("quasar_warmup_contract", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class QuasarLifecycleContractTests(unittest.TestCase):
    def test_warmup_accepts_pre_requested_stop_token(self):
        warmup = load_warmup_module()
        stop_token = threading.Event()
        stop_token.set()

        self.assertFalse(warmup.warmup_all(stop_token=stop_token))


if __name__ == "__main__":
    unittest.main()
