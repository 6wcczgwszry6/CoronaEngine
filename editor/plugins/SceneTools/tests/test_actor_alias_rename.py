import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from plugins.SceneTools import main as scene_tools_main


class FakeActor:
    def __init__(self, name):
        self.name = name
        self.route = f"models/{name}.obj"
        self.actor_type = "model"
        self.actor_guid = f"guid-{name}"

    def to_dict(self):
        return {
            "name": self.name,
            "path": self.route,
            "type": self.actor_type,
            "actor_guid": self.actor_guid,
        }


class FakeScene:
    def __init__(self, actors):
        self.route = "Demo.scene"
        self._actors = actors
        self.saved = False
        self.notified = False

    def get_actors(self):
        return self._actors

    def find_actor(self, name):
        return next((actor for actor in self._actors if actor.name == name), None)

    def save_data(self):
        self.saved = True

    def _notify_scene_tree_changed(self):
        self.notified = True


class FakeSceneManager:
    def __init__(self, scene):
        self.scene = scene

    def get(self, scene_name):
        return self.scene if scene_name == self.scene.route else None


class ActorAliasRenameTests(unittest.TestCase):
    def test_rename_actor_updates_alias_and_refreshes_scene_tree(self):
        actor = FakeActor("chair")
        scene = FakeScene([actor])

        with patch.object(scene_tools_main, "scene_manager", FakeSceneManager(scene)):
            result = scene_tools_main.SceneTools.rename_actor("Demo.scene", "chair", "Display Chair")

        self.assertEqual(result["status"], "success")
        self.assertEqual(actor.name, "Display Chair")
        self.assertTrue(scene.saved)
        self.assertTrue(scene.notified)
        self.assertEqual(result["actor"]["name"], "Display Chair")
        self.assertEqual(result["old_name"], "chair")
        self.assertEqual(result["new_name"], "Display Chair")

    def test_rename_actor_rejects_duplicate_aliases(self):
        scene = FakeScene([FakeActor("chair"), FakeActor("table")])

        with patch.object(scene_tools_main, "scene_manager", FakeSceneManager(scene)):
            result = scene_tools_main.SceneTools.rename_actor("Demo.scene", "chair", "table")

        self.assertEqual(result["status"], "error")
        self.assertIn("already exists", result["message"])
        self.assertFalse(scene.saved)
        self.assertFalse(scene.notified)


if __name__ == "__main__":
    unittest.main()
