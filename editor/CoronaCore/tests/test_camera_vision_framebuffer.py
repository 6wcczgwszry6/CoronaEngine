import configparser
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from CoronaCore.core.entities import camera as camera_module
from CoronaCore.core.entities import scene as scene_module


class FakeEngineCamera:
    def __init__(self, *args):
        self.vision_framebuffer = "normal"
        self.render_backend = "native"
        self.size = [1920, 1080]
        self.view_state = [0.0, 120.0, 120.0, 960.0, 540.0, 1.0]

    def get_position(self):
        return [0.0, 0.0, -5.0]

    def get_forward(self):
        return [0.0, 0.0, 1.0]

    def get_world_up(self):
        return [0.0, 1.0, 0.0]

    def get_fov(self):
        return 45.0

    def set_size(self, width, height):
        self.size = [int(width), int(height)]

    def get_size(self):
        return list(self.size)

    def set_output_mode(self, mode):
        self.output_mode = mode

    def set_render_backend(self, mode):
        self.render_backend = mode

    def set_view_state(self, open_, x, y, width, height, move_speed):
        self.view_state = [open_, x, y, width, height, move_speed]

    def get_view_state(self):
        return list(self.view_state)

    def set_vision_framebuffer(self, mode):
        self.vision_framebuffer = mode

    def get_vision_framebuffer(self):
        return self.vision_framebuffer

    def get_handle(self):
        return 42


class CameraVisionFramebufferTests(unittest.TestCase):
    def test_camera_defaults_to_normal_vision_framebuffer_and_can_switch_to_lightfield(self):
        fake_engine = SimpleNamespace(
            Camera=FakeEngineCamera,
            is_vision_available=lambda: True,
        )

        with patch.object(camera_module, "CoronaEngine", fake_engine):
            cam = camera_module.Camera(render_backend="vision")

        self.assertEqual(cam.get_vision_framebuffer(), "normal")

        cam.set_vision_framebuffer("lightfield")

        self.assertEqual(cam.get_vision_framebuffer(), "lightfield")
        self.assertEqual(cam.engine_obj.get_vision_framebuffer(), "lightfield")
        self.assertEqual(cam.to_dict()["vision_framebuffer"], "lightfield")

    def test_camera_keeps_local_vision_framebuffer_until_native_state_catches_up(self):
        fake_engine = SimpleNamespace(
            Camera=FakeEngineCamera,
            is_vision_available=lambda: True,
        )

        with patch.object(camera_module, "CoronaEngine", fake_engine):
            cam = camera_module.Camera(render_backend="vision")

        cam.set_vision_framebuffer("lightfield")
        cam.engine_obj.get_vision_framebuffer = lambda: "normal"

        self.assertEqual(cam.get_vision_framebuffer(), "lightfield")
        self.assertEqual(cam.to_dict()["vision_framebuffer"], "lightfield")

    def test_scene_save_persists_camera_vision_framebuffer(self):
        with tempfile.TemporaryDirectory() as tmp:
            scene_path = Path(tmp) / "main.scene"
            camera = SimpleNamespace(
                camera_id="cam-1",
                name="Camera",
                width=960,
                height=540,
                move_speed=1.0,
                view_open=True,
                view_x=120,
                view_y=120,
                view_width=960,
                view_height=540,
                deletable=True,
                refresh_view_state=lambda: None,
                refresh_size=lambda: None,
                get_position=lambda: [0.0, 0.0, -5.0],
                get_forward=lambda: [0.0, 0.0, 1.0],
                get_world_up=lambda: [0.0, 1.0, 0.0],
                get_fov=lambda: 45.0,
                get_output_mode=lambda: "final_color",
                get_render_backend=lambda: "vision",
                get_vision_framebuffer=lambda: "lightfield",
            )
            scene = scene_module.Scene.__new__(scene_module.Scene)
            scene.route = str(scene_path)
            scene.name = "main"
            scene.file_data = configparser.ConfigParser()
            scene._environment = None
            scene._cameras = [camera]
            scene._actors = []
            scene.script_path = ""
            scene.terrain_path = ""
            scene.terrain_type = ""
            scene.vision_source_path = ""
            scene.vision_import_mode = ""
            scene.get_active_camera = lambda: camera

            scene.save_data()

            saved = configparser.ConfigParser()
            saved.read(scene_path, encoding="utf-8")
            self.assertEqual(saved["camera"]["camera0.vision_framebuffer"], "lightfield")


if __name__ == "__main__":
    unittest.main()
