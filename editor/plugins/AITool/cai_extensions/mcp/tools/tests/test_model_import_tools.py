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

from editor.plugins.AITool.cai_extensions.mcp.tools.model_import_tools import _pick_model_file


class ModelImportToolsTests(unittest.TestCase):
    def test_pick_model_file_finds_nested_mesh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hunyuan_model"
            nested = root / "mesh" / "export"
            nested.mkdir(parents=True)
            mesh = nested / "base.glb"
            mesh.write_bytes(b"glb")

            self.assertEqual(_pick_model_file(str(root)), str(mesh))


if __name__ == "__main__":
    unittest.main()
