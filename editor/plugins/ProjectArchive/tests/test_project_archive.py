import tempfile
import unittest
from pathlib import Path

from plugins.ProjectArchive.main import ProjectArchive


class ProjectArchiveServiceTests(unittest.TestCase):
    def test_parse_returns_invalid_archive_with_structured_diagnostic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scene = Path(temp_dir)
            (scene / "scene.ini").write_text(
                "[format]\ntype = corona_scene_folder\nversion = 99\n[scene]\nname = Future\n",
                encoding="utf-8",
            )

            result = ProjectArchive.parse({"path": str(scene)})

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "invalid_archive")
            self.assertEqual(result["diagnostics"][0]["code"], "UNSUPPORTED_ARCHIVE_VERSION")

    def test_parse_requires_user_decision_when_snapshot_has_recoverable_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scene = Path(temp_dir)
            (scene / "scene.ini").write_text(
                "\n".join(
                    [
                        "[format]",
                        "type = corona_scene_folder",
                        "version = 1",
                        "[scene]",
                        "name = Missing",
                        "[actors]",
                        "missing.actor_guid = missing-guid",
                        "missing.route = assets/missing.fbx",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = ProjectArchive.parse({"path": str(scene), "load_policy": "prompt"})

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "decision_required")
            self.assertEqual(result["snapshot"]["schema_version"], 1)

            degraded = ProjectArchive.parse(
                {"path": str(scene), "load_policy": "degraded"}
            )
            self.assertEqual(degraded["status"], "ready_degraded")


if __name__ == "__main__":
    unittest.main()
