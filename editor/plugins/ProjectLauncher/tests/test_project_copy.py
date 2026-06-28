import configparser
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

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


if __name__ == "__main__":
    unittest.main()
