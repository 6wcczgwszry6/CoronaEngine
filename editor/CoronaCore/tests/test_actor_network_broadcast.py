import unittest
import contextvars
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from CoronaCore.core import network_sync_policy
from CoronaCore.core.entities import actor as actor_module


class FakeActorEngineObject:
    def __init__(self):
        self.active_profile = None

    def add_profile(self, profile):
        return profile

    def set_active_profile(self, profile):
        self.active_profile = profile

    def get_handle(self):
        return 1234


class FakeGeometry:
    def __init__(self, model_path):
        self.engine_obj = object()
        self.model_path = model_path
        self.position = [0.0, 0.0, 0.0]
        self.rotation = [0.0, 0.0, 0.0]
        self.scale = [1.0, 1.0, 1.0]

    def get_position(self):
        return self.position

    def set_position(self, position):
        self.position = position

    def get_rotation(self):
        return self.rotation

    def set_rotation(self, rotation):
        self.rotation = rotation

    def get_scale(self):
        return self.scale

    def set_scale(self, scale):
        self.scale = scale


class FakeOptics:
    def __init__(self, geometry):
        self.engine_obj = object()

    def get_visible(self):
        return True


class FakeComponent:
    def __init__(self, geometry):
        self.engine_obj = object()
        self.physics_enabled = True

    def set_collision_callback(self, callback):
        self.collision_callback = callback

    def set_on_move_callback(self, callback):
        self.on_move_callback = callback

    def set_physics_enabled(self, enabled):
        self.physics_enabled = enabled

    def get_physics_enabled(self):
        return self.physics_enabled


class ActorNetworkBroadcastTests(unittest.TestCase):
    def setUp(self):
        network_sync_policy.reset_for_tests()

    def tearDown(self):
        network_sync_policy.reset_for_tests()

    def _create_actor_with_events(self, *, route="Resource/cube.obj", name="", parent=None,
                                  actor_data=None, project_path="D:/project/test"):
        events = []
        fake_editor = SimpleNamespace(
            CoronaEngine=SimpleNamespace(
                active_project_path=project_path,
                Actor=FakeActorEngineObject,
                ActorProfile=SimpleNamespace,
            ),
            js_call_func=lambda name, args: events.append((name, args)),
        )
        if parent is None:
            parent = SimpleNamespace(route="Scene/main.scene")

        with patch.object(actor_module, "CoronaEditor", fake_editor), \
             patch.object(actor_module, "CoronaEngine", fake_editor.CoronaEngine), \
             patch.object(actor_module, "Geometry", FakeGeometry), \
             patch.object(actor_module, "Optics", FakeOptics), \
             patch.object(actor_module, "Mechanics", FakeComponent), \
             patch.object(actor_module, "Acoustics", FakeComponent):
            actor = actor_module.Actor(
                name=name,
                route=route,
                actor_type="model",
                parent_scene=parent,
                actor_data=actor_data,
            )
        return actor, events

    def test_actor_create_broadcast_happens_after_handle_is_available(self):
        events = []
        fake_editor = SimpleNamespace(
            CoronaEngine=SimpleNamespace(
                active_project_path="D:/project/test",
                Actor=FakeActorEngineObject,
                ActorProfile=SimpleNamespace,
            ),
            js_call_func=lambda name, args: events.append((name, args)),
        )
        parent = SimpleNamespace(route="Scene/main.scene")

        with patch.object(actor_module, "CoronaEditor", fake_editor), \
             patch.object(actor_module, "CoronaEngine", fake_editor.CoronaEngine), \
             patch.object(actor_module, "Geometry", FakeGeometry), \
             patch.object(actor_module, "Optics", FakeOptics), \
             patch.object(actor_module, "Mechanics", FakeComponent), \
             patch.object(actor_module, "Acoustics", FakeComponent):
            actor_module.Actor(route="Resource/cube.obj",
                               actor_type="model",
                               parent_scene=parent)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "actor-sync-broadcast")
        actor_data = events[0][1][0]
        self.assertEqual(actor_data["handle"], 1234)
        self.assertTrue(actor_data["actor_guid"])
        self.assertEqual(actor_data["scene"], "Scene/main.scene")

    def test_external_model_path_is_copied_into_project_resource_before_broadcast(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_root = root / "Project"
            external_root = root / "External"
            project_root.mkdir()
            external_root.mkdir()
            source_model = external_root / "Ball.obj"
            source_model.write_text("mtllib Ball.mtl\nmesh-data", encoding="utf-8")
            (external_root / "Ball.mtl").write_text(
                "map_Kd textures/Ball.png\n", encoding="utf-8")
            (external_root / "textures").mkdir()
            (external_root / "textures" / "Ball.png").write_bytes(b"png-data")

            events = []
            fake_editor = SimpleNamespace(
                CoronaEngine=SimpleNamespace(
                    active_project_path=str(project_root),
                    Actor=FakeActorEngineObject,
                    ActorProfile=SimpleNamespace,
                ),
                js_call_func=lambda name, args: events.append((name, args)),
            )
            parent = SimpleNamespace(route="Scene/main.scene")
            unsafe_route = "../External/Ball.obj"

            with patch.object(actor_module, "CoronaEditor", fake_editor), \
                 patch.object(actor_module, "CoronaEngine", fake_editor.CoronaEngine), \
                 patch.object(actor_module, "Geometry", FakeGeometry), \
                 patch.object(actor_module, "Optics", FakeOptics), \
                 patch.object(actor_module, "Mechanics", FakeComponent), \
                 patch.object(actor_module, "Acoustics", FakeComponent):
                actor_module.Actor(route=unsafe_route,
                                   actor_type="model",
                                   parent_scene=parent)

            actor_data = events[0][1][0]
            self.assertEqual(actor_data["path"], "Resource/Ball.obj")
            self.assertEqual(actor_data["model"], "Resource/Ball.obj")
            self.assertEqual(actor_data["scene"], "Scene/main.scene")
            self.assertEqual(actor_data["model_dependencies"], [
                "Resource/Ball.mtl",
                "Resource/textures/Ball.png",
            ])
            self.assertTrue((project_root / "Resource" / "Ball.obj").exists())
            self.assertEqual((project_root / "Resource" / "Ball.obj").read_text(encoding="utf-8"),
                             "mtllib Ball.mtl\nmesh-data")
            self.assertTrue((project_root / "Resource" / "Ball.mtl").exists())
            self.assertTrue((project_root / "Resource" / "textures" / "Ball.png").exists())

    def test_remote_actor_disables_local_physics(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "Resource").mkdir()
            (project_root / "Resource" / "cube.obj").write_text("mesh", encoding="utf-8")
            fake_editor = SimpleNamespace(
                CoronaEngine=SimpleNamespace(
                    active_project_path=str(project_root),
                    Actor=FakeActorEngineObject,
                    ActorProfile=SimpleNamespace,
                ),
                js_call_func=lambda name, args: None,
            )
            parent = SimpleNamespace(route="Scene/main.scene")

            with patch.object(actor_module, "CoronaEditor", fake_editor), \
                 patch.object(actor_module, "CoronaEngine", fake_editor.CoronaEngine), \
                 patch.object(actor_module, "Geometry", FakeGeometry), \
                 patch.object(actor_module, "Optics", FakeOptics), \
                 patch.object(actor_module, "Mechanics", FakeComponent), \
                 patch.object(actor_module, "Acoustics", FakeComponent):
                actor = actor_module.Actor(
                    route="Resource/cube.obj",
                    actor_type="model",
                    parent_scene=parent,
                    actor_data={
                        "actor_guid": "actor-remote",
                        "_suppress_network_broadcast": True,
                        "geometry": {
                            "position": [0, 0, 0],
                            "rotation": [0, 0, 0],
                            "scale": [1, 1, 1],
                        },
                    },
                )

            self.assertFalse(actor._mechanics.get_physics_enabled())

    def test_actor_in_internal_temp_scene_does_not_broadcast(self):
        parent = SimpleNamespace(route="__six_view_tmp_abc__")

        _, events = self._create_actor_with_events(parent=parent)

        self.assertEqual(events, [])

    def test_internal_actor_name_does_not_broadcast(self):
        _, events = self._create_actor_with_events(name="__room_box")

        self.assertEqual(events, [])

    def test_suppressed_actor_does_not_broadcast(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "Resource").mkdir()
            (project_root / "Resource" / "cube.obj").write_text("mesh", encoding="utf-8")

            _, events = self._create_actor_with_events(
                project_path=str(project_root),
                actor_data={
                    "actor_guid": "actor-remote",
                    "_suppress_network_broadcast": True,
                    "geometry": {
                        "position": [0, 0, 0],
                        "rotation": [0, 0, 0],
                        "scale": [1, 1, 1],
                    },
                },
            )

        self.assertEqual(events, [])

    def test_deferred_mode_flushes_only_existing_normal_actors(self):
        events = []
        fake_editor = SimpleNamespace(
            CoronaEngine=SimpleNamespace(
                active_project_path="D:/project/test",
                Actor=FakeActorEngineObject,
                ActorProfile=SimpleNamespace,
            ),
            js_call_func=lambda name, args: events.append((name, args)),
        )
        parent = SimpleNamespace(route="Scene/main.scene")

        with patch.object(actor_module, "CoronaEditor", fake_editor), \
             patch.object(actor_module, "CoronaEngine", fake_editor.CoronaEngine), \
             patch.object(actor_module, "Geometry", FakeGeometry), \
             patch.object(actor_module, "Optics", FakeOptics), \
             patch.object(actor_module, "Mechanics", FakeComponent), \
             patch.object(actor_module, "Acoustics", FakeComponent):
            with network_sync_policy.deferred_actor_broadcasts():
                kept = actor_module.Actor(
                    name="chair",
                    route="Resource/chair.obj",
                    actor_type="model",
                    parent_scene=parent,
                )
                actor_module.Actor(
                    name="__wb_floor",
                    route="Resource/floor.obj",
                    actor_type="model",
                    parent_scene=parent,
                )
                removed = actor_module.Actor(
                    name="table",
                    route="Resource/table.obj",
                    actor_type="model",
                    parent_scene=parent,
                )
                removed.parent = None
                self.assertEqual(events, [])

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "actor-sync-broadcast")
        self.assertEqual(events[0][1][0]["actor_guid"], kept.actor_guid)
        self.assertEqual(events[0][1][0]["name"], "chair")

    def test_deferred_mode_discards_events_on_failure(self):
        events = []
        fake_editor = SimpleNamespace(
            CoronaEngine=SimpleNamespace(
                active_project_path="D:/project/test",
                Actor=FakeActorEngineObject,
                ActorProfile=SimpleNamespace,
            ),
            js_call_func=lambda name, args: events.append((name, args)),
        )
        parent = SimpleNamespace(route="Scene/main.scene")

        with patch.object(actor_module, "CoronaEditor", fake_editor), \
             patch.object(actor_module, "CoronaEngine", fake_editor.CoronaEngine), \
             patch.object(actor_module, "Geometry", FakeGeometry), \
             patch.object(actor_module, "Optics", FakeOptics), \
             patch.object(actor_module, "Mechanics", FakeComponent), \
             patch.object(actor_module, "Acoustics", FakeComponent):
            with self.assertRaises(RuntimeError):
                with network_sync_policy.deferred_actor_broadcasts():
                    actor_module.Actor(
                        name="chair",
                        route="Resource/chair.obj",
                        actor_type="model",
                        parent_scene=parent,
                    )
                    raise RuntimeError("cancelled")

        self.assertEqual(events, [])

    def test_deferred_mode_does_not_capture_actor_created_in_separate_context(self):
        events = []

        fake_editor = SimpleNamespace(
            CoronaEngine=SimpleNamespace(
                active_project_path="D:/project/test",
                Actor=FakeActorEngineObject,
                ActorProfile=SimpleNamespace,
            ),
            js_call_func=lambda name, args: events.append((name, args)),
        )
        parent = SimpleNamespace(route="Scene/main.scene")

        with patch.object(actor_module, "CoronaEditor", fake_editor), \
             patch.object(actor_module, "CoronaEngine", fake_editor.CoronaEngine), \
             patch.object(actor_module, "Geometry", FakeGeometry), \
             patch.object(actor_module, "Optics", FakeOptics), \
             patch.object(actor_module, "Mechanics", FakeComponent), \
             patch.object(actor_module, "Acoustics", FakeComponent):
            with network_sync_policy.deferred_actor_broadcasts():
                actor_module.Actor(
                    name="ai_chair",
                    route="Resource/ai_chair.obj",
                    actor_type="model",
                    parent_scene=parent,
                )

                def create_manual_actor():
                    actor_module.Actor(
                        name="manual_table",
                        route="Resource/manual_table.obj",
                        actor_type="model",
                        parent_scene=parent,
                    )

                contextvars.Context().run(create_manual_actor)
                self.assertEqual([e[1][0]["name"] for e in events], ["manual_table"])

        self.assertEqual([e[1][0]["name"] for e in events], ["manual_table", "ai_chair"])

    def test_actor_move_emits_ownership_claim(self):
        events = []
        fake_editor = SimpleNamespace(
            CoronaEngine=SimpleNamespace(
                active_project_path="D:/project/test",
                Actor=FakeActorEngineObject,
                ActorProfile=SimpleNamespace,
            ),
            js_call_func=lambda name, args: events.append((name, args)),
        )
        parent = SimpleNamespace(route="Scene/main.scene", save_data=lambda: None)

        with patch.object(actor_module, "CoronaEditor", fake_editor), \
             patch.object(actor_module, "CoronaEngine", fake_editor.CoronaEngine), \
             patch.object(actor_module, "Geometry", FakeGeometry), \
             patch.object(actor_module, "Optics", FakeOptics), \
             patch.object(actor_module, "Mechanics", FakeComponent), \
             patch.object(actor_module, "Acoustics", FakeComponent):
            actor = actor_module.Actor(route="Resource/cube.obj",
                                       actor_type="model",
                                       parent_scene=parent)
            actor.on_move()

        claims = [args[0] for name, args in events if name == "actor-ownership-claim"]
        self.assertTrue(claims)
        self.assertEqual(claims[-1]["actor_guid"], actor.actor_guid)


if __name__ == "__main__":
    unittest.main()
