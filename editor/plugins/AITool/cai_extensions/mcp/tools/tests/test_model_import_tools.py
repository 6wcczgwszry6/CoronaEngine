from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[7]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
AI_TOOL_ROOT = PROJECT_ROOT / "editor" / "plugins" / "AITool"
if str(AI_TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_TOOL_ROOT))

from editor.plugins.AITool.cai_extensions.mcp.tools.model_import_tools import (
    _actor_identity_from_native_result,
    _pick_model_file,
)


class ModelImportToolsTests(unittest.TestCase):
    def test_pick_model_file_finds_nested_mesh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hunyuan_model"
            nested = root / "mesh" / "export"
            nested.mkdir(parents=True)
            mesh = nested / "base.glb"
            mesh.write_bytes(b"glb")

            self.assertEqual(_pick_model_file(str(root)), str(mesh))

    def test_actor_identity_from_native_result_accepts_supported_fields(self) -> None:
        self.assertEqual(
            _actor_identity_from_native_result({"actor": {"actor_guid": "guid-1"}}),
            "guid-1",
        )
        self.assertEqual(
            _actor_identity_from_native_result({"actor_data": {"native_actor_id": "native-2"}}),
            "native-2",
        )
        self.assertEqual(
            _actor_identity_from_native_result({"entity_id": "entity-3"}),
            "entity-3",
        )

    def test_actor_identity_from_native_result_rejects_missing_identity(self) -> None:
        self.assertEqual(
            _actor_identity_from_native_result({"status": "success", "actor": {"name": "box"}}),
            "",
        )


if __name__ == "__main__":
    unittest.main()
