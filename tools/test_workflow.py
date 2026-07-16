from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from horizon_workspace import load_lock
from workflow import _cmake_bracket, build_dir, configuration_slug, safe_remove


class WorkflowTests(unittest.TestCase):
    def test_configuration_paths_are_per_configuration(self) -> None:
        root = Path("C:/repo")
        self.assertEqual(configuration_slug("RelWithDebInfo"), "relwithdebinfo")
        self.assertEqual(build_dir(root, "Debug"), root / "build" / "conan" / "debug")

    def test_unknown_configuration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            configuration_slug("Profile")

    def test_cmake_bracket_handles_embedded_delimiter(self) -> None:
        self.assertEqual(_cmake_bracket("a]]b"), "[=[a]]b]=]")

    def test_safe_remove_refuses_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            with self.assertRaises(RuntimeError):
                safe_remove(root, root.parent)

    def test_horizon_lock_requires_full_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock_file = Path(directory) / "horizon.lock.json"
            lock_file.write_text(json.dumps({
                "schema_version": 1,
                "url": "https://github.com/CoronaEngine/Horizon.git",
                "ref": "conan-migration",
                "commit": "a" * 40,
            }), encoding="utf-8")
            self.assertEqual(load_lock(lock_file).commit, "a" * 40)
            lock_file.write_text("{}", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                load_lock(lock_file)


if __name__ == "__main__":
    unittest.main()
