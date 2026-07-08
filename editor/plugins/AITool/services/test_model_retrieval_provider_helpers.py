from __future__ import annotations

import sys
import types
import unittest
import importlib.util
from pathlib import Path


_AITOOL_ROOT = Path(__file__).resolve().parents[1]
if str(_AITOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(_AITOOL_ROOT))

_HELPERS_PATH = (
    _AITOOL_ROOT
    / "cai_extensions"
    / "flows"
    / "model_retrieval_workflow"
    / "helpers.py"
)
_SPEC = importlib.util.spec_from_file_location("model_retrieval_workflow_helpers_under_test", _HELPERS_PATH)
assert _SPEC is not None and _SPEC.loader is not None
helpers = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(helpers)


class ModelRetrievalProviderHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_get_ai_config = helpers.get_ai_config
        self._orig_get_tool = helpers.get_tool

    def tearDown(self) -> None:
        helpers.get_ai_config = self._orig_get_ai_config
        helpers.get_tool = self._orig_get_tool

    def test_dashscope_embedding_search_and_store_are_disabled_for_formal_validation(self) -> None:
        self.assertFalse(helpers.object_embedding_tools_enabled())
        self.assertIsNone(helpers.get_search_tool())
        self.assertIsNone(helpers.get_store_tool())

    def test_get_3d_generate_tool_accepts_dict_hunyuan_settings(self) -> None:
        sentinel_tool = object()
        helpers.get_ai_config = lambda: types.SimpleNamespace(
            hunyuan3d={"enable": True, "api_keys": ["test-key"]},
        )
        helpers.get_tool = lambda name: sentinel_tool if name == "hunyuan_generate_3d" else None

        self.assertIs(helpers.get_3d_generate_tool(), sentinel_tool)

    def test_get_3d_generate_tool_rejects_disabled_dict_hunyuan_settings(self) -> None:
        helpers.get_ai_config = lambda: types.SimpleNamespace(
            hunyuan3d={"enable": False, "api_keys": ["test-key"]},
        )
        helpers.get_tool = lambda name: object()

        self.assertIsNone(helpers.get_3d_generate_tool())


if __name__ == "__main__":
    unittest.main()
