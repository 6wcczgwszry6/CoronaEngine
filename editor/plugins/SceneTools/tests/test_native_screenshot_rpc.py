import pathlib
import re
import unittest


class NativeSceneToolsRpcTests(unittest.TestCase):
    def test_scene_tools_registers_native_camera_handlers(self):
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        handler_path = repo_root / "src" / "systems" / "ui" / "cef" / "cef_native_rpc_handlers.cpp"
        source = handler_path.read_text(encoding="utf-8")

        match = re.search(
            r"void register_scene_tools_rpc_handlers\(NativeRpcRegistry& registry\).*?"
            r"registry\.register_module\(\"SceneTools\"",
            source,
            re.S,
        )
        self.assertIsNotNone(match)
        scene_tools_handlers = match.group(0)
        for method in (
            "save_screenshot",
            "set_render_backend",
            "get_render_backend",
            "set_vision_render_mode",
            "get_vision_render_mode",
        ):
            with self.subTest(method=method):
                self.assertIn(f'{{"{method}"', scene_tools_handlers)


if __name__ == "__main__":
    unittest.main()
