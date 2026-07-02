import configparser
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from CoronaCore.core.entities.scene import _encode_vision_document
from plugins.ProjectLauncher import main as project_launcher
from plugins.ProjectLauncher.utils import project_copy


class ProjectCopyTests(unittest.TestCase):
    def test_copy_existing_to_data_creates_new_runtime_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_dir = temp_root / "source_save"
            source_scene_dir = source_dir / "Scene"
            source_scene_dir.mkdir(parents=True)
            (source_scene_dir / "default.scene").write_text("[base]\nname = default\n", encoding="utf-8")
            source_ini = source_dir / "project.ini"
            source_ini.write_text(
                "\n".join([
                    "[Project]",
                    "name = sample_save",
                    "mode = 3d",
                    "entrance_scene = Scene/default.scene",
                    "scenes = Scene/default.scene",
                    "active_scene = Scene/default.scene",
                    "",
                ]),
                encoding="utf-8",
            )

            original_core_path = project_copy.core_path
            project_copy.core_path = SimpleNamespace(repo_root=temp_root / "runtime")
            try:
                first = project_copy.ProjectCopy.copy_existing_to_data(str(source_ini))
                second = project_copy.ProjectCopy.copy_existing_to_data(str(source_ini))
            finally:
                project_copy.core_path = original_core_path

            first_path = Path(first["path"])
            second_path = Path(second["path"])

            self.assertEqual(first["name"], "sample_save")
            self.assertEqual(second["name"], "sample_save_1")
            self.assertTrue((first_path / "project.ini").is_file())
            self.assertTrue((first_path / "Scene" / "default.scene").is_file())
            self.assertTrue((second_path / "project.ini").is_file())
            self.assertEqual(first_path.parent, temp_root / "runtime" / "data")
            self.assertEqual(second_path.parent, temp_root / "runtime" / "data")

            source_cfg = configparser.ConfigParser()
            source_cfg.read(source_ini, encoding="utf-8")
            self.assertEqual(source_cfg.get("Project", "name"), "sample_save")

            copied_cfg = configparser.ConfigParser()
            copied_cfg.read(second_path / "project.ini", encoding="utf-8")
            self.assertEqual(copied_cfg.get("Project", "name"), "sample_save_1")

    def test_create_project_from_vision_writes_native_compatible_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_project = temp_root / "template"
            template_scene_dir = template_project / "Scene"
            template_scene_dir.mkdir(parents=True)
            (template_scene_dir / "default.scene").write_text("[base]\nname = default\n", encoding="utf-8")
            (template_project / "project.ini").write_text(
                "\n".join([
                    "[Project]",
                    "name = template",
                    "mode = 3d",
                    "entrance_scene = Scene/default.scene",
                    "",
                ]),
                encoding="utf-8",
            )
            source_json = temp_root / "vision_scene.json"
            source_json.write_text(json.dumps({"shapes": []}), encoding="utf-8")

            def fake_create_from_template(target_path, project_name, mode):
                target = Path(target_path)
                project_copy.shutil.copytree(template_project, target)
                return str(target / "project.ini")

            original_default_path = project_launcher.settings_manager.get_default_path
            original_create = project_launcher.ProjectCopy.create_from_template
            original_is_vision_available = project_launcher.CoronaEditor.CoronaEngine.is_vision_available
            project_launcher.settings_manager.get_default_path = lambda: str(temp_root / "projects")
            project_launcher.ProjectCopy.create_from_template = staticmethod(fake_create_from_template)
            project_launcher.CoronaEditor.CoronaEngine.is_vision_available = staticmethod(lambda: True)
            try:
                result = project_launcher.ProjectLauncher._create_project_from_vision(str(source_json))
            finally:
                project_launcher.settings_manager.get_default_path = original_default_path
                project_launcher.ProjectCopy.create_from_template = original_create
                project_launcher.CoronaEditor.CoronaEngine.is_vision_available = original_is_vision_available

            scene_file = Path(result["path"]) / "Scene" / "default.scene"
            scene_cfg = configparser.ConfigParser()
            scene_cfg.read(scene_file, encoding="utf-8")

            self.assertTrue(scene_cfg.has_section("vision_document"))
            self.assertEqual(scene_cfg.get("vision", "source_path"), str(source_json.resolve()))
            self.assertEqual(scene_cfg.get("vision", "import_mode"), "external_live")
            self.assertEqual(scene_cfg.get("camera", "camera0.render_backend"), "vision")

    def test_open_and_update_migrates_embedded_vision_document_for_native_startup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "embedded_only"
            scene_dir = project_dir / "Scene"
            scene_dir.mkdir(parents=True)
            (project_dir / "project.ini").write_text(
                "\n".join([
                    "[Project]",
                    "name = embedded_only",
                    "entrance_scene = Scene/default.scene",
                    "",
                ]),
                encoding="utf-8",
            )
            scene_file = scene_dir / "default.scene"
            scene_file.write_text(
                "\n".join([
                    "[base]",
                    "name = default",
                    "",
                    "[vision_document]",
                    "encoding = zlib_base64_json",
                    "version = 1",
                    f"data = {_encode_vision_document({'shapes': []})}",
                    "",
                ]),
                encoding="utf-8",
            )

            original_normalize = project_copy.normalize_project_runtime_paths
            original_update = project_copy.update_project_config
            original_settings = project_copy.settings_manager
            project_copy.normalize_project_runtime_paths = lambda path: None
            project_copy.update_project_config = lambda ini_path, update_only_time=True: None
            project_copy.settings_manager = SimpleNamespace(set_active_project=lambda path: True)
            try:
                self.assertTrue(project_copy.ProjectCopy.open_and_update(str(project_dir)))
            finally:
                project_copy.normalize_project_runtime_paths = original_normalize
                project_copy.update_project_config = original_update
                project_copy.settings_manager = original_settings

            scene_cfg = configparser.ConfigParser()
            scene_cfg.read(scene_file, encoding="utf-8")
            migrated_source = scene_cfg.get("vision", "source_path")

            self.assertEqual(scene_cfg.get("vision", "import_mode"), "external_live")
            self.assertEqual(scene_cfg.get("camera", "camera0.render_backend"), "vision")
            self.assertTrue((project_dir / migrated_source).is_file())


if __name__ == "__main__":
    unittest.main()
