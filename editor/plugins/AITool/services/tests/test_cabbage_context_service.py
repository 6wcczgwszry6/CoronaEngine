import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

EDITOR_ROOT = pathlib.Path(__file__).resolve().parents[4]
if str(EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(EDITOR_ROOT))

from plugins.AITool.services.cabbage_context_service import CabbageContextService
from plugins.AITool.services.node_graph_review_service import NodeGraphReviewService


class CabbageContextServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.world = pathlib.Path(self.temp_dir.name) / "story_world_test"
        self.world.mkdir(parents=True)
        (self.world / "project.ini").write_text("[Project]\nname=story_world_test\n", encoding="utf-8")
        self.service = CabbageContextService()
        self.path_patch = mock.patch.object(
            CabbageContextService,
            "_active_project_path",
            return_value=self.world,
        )
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.service.shutdown()
        self.temp_dir.cleanup()

    def active_task_keys(self, context):
        return {task.get("taskKey") for task in context.get("activeTasks", [])}

    def history_task(self, context, task_key):
        return next(
            (task for task in context.get("taskHistory", []) if task.get("taskKey") == task_key),
            None,
        )

    def visible_tutorial_keys(self, context):
        return {
            task.get("taskKey")
            for task in context.get("activeTasks", [])
            if task.get("type") == "tutorial" and task.get("status") in {"active", "pending"}
        }

    def test_new_world_contains_node_interaction_tutorials(self):
        response = self.service.load()
        self.assertTrue(response["success"])
        keys = self.active_task_keys(response["context"])
        self.assertIn("tutorial.move_node", keys)
        self.assertIn("tutorial.connect_nodes", keys)
        self.assertIn("tutorial.drag_block", keys)

    def test_new_world_shows_one_scene_task_and_one_node_task(self):
        context = self.service.load()["context"]
        self.assertEqual(
            {"tutorial.import_model", "tutorial.create_node"},
            self.visible_tutorial_keys(context),
        )
        visible = {
            task.get("track")
            for task in context.get("activeTasks", [])
            if task.get("status") == "active" and task.get("type") == "tutorial"
        }
        self.assertEqual({"scene", "node"}, visible)

    def test_legacy_pending_tutorials_are_migrated_to_two_visible_slots(self):
        context = self.service._default_context(self.world)
        for task in context["activeTasks"]:
            if task.get("type") == "tutorial":
                task["status"] = "pending"
        context_path = self.service._context_path(self.world)
        context_path.parent.mkdir(parents=True, exist_ok=True)
        context_path.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")

        loaded = self.service.load()["context"]
        self.assertEqual(
            {"tutorial.import_model", "tutorial.create_node"},
            self.visible_tutorial_keys(loaded),
        )
        queued = {
            task.get("taskKey")
            for task in loaded.get("activeTasks", [])
            if task.get("type") == "tutorial" and task.get("status") == "queued"
        }
        self.assertIn("tutorial.transform_model", queued)
        self.assertIn("tutorial.move_node", queued)

    def test_completing_a_task_reveals_next_task_in_same_track(self):
        imported = self.service.record_event({
            "type": "model_imported",
            "category": "scene",
            "success": True,
            "worldId": self.world.name,
        })
        self.assertEqual(["tutorial.import_model"], imported["completedTaskKeys"])
        self.assertEqual(
            {"tutorial.transform_model", "tutorial.create_node"},
            self.visible_tutorial_keys(imported["context"]),
        )

        created = self.service.record_event({
            "type": "node_created",
            "category": "node",
            "success": True,
            "details": {"nodeId": "state_2"},
            "worldId": self.world.name,
        })
        self.assertEqual(["tutorial.create_node"], created["completedTaskKeys"])
        self.assertEqual(
            {"tutorial.transform_model", "tutorial.move_node"},
            self.visible_tutorial_keys(created["context"]),
        )

    def test_any_transform_parameter_completes_adjust_object_task(self):
        for event_type in ("transform_position", "transform_rotation", "transform_scale"):
            with self.subTest(event_type=event_type):
                context_path = self.service._context_path(self.world)
                if context_path.exists():
                    context_path.unlink()
                response = self.service.record_event({
                    "type": event_type,
                    "category": "scene",
                    "success": True,
                    "details": {"actorName": "Player"},
                    "worldId": self.world.name,
                })
                self.assertEqual(["tutorial.transform_model"], response["completedTaskKeys"])
                self.assertIsNotNone(self.history_task(response["context"], "tutorial.transform_model"))

    def test_supplementary_tutorial_events_are_recognized(self):
        cases = (
            ("block_parameter_changed", {"blockId": "speed", "fieldName": "VALUE"}, "tutorial.edit_block_parameter"),
            ("block_added", {"workspaceRole": "condition", "interaction": "pick"}, "tutorial.set_transition_condition"),
            ("run_started", {"source": "node_graph"}, "tutorial.run_node_graph"),
            ("run_succeeded", {"source": "node_graph"}, "tutorial.run_node_graph"),
        )
        for event_type, details, task_key in cases:
            with self.subTest(event_type=event_type):
                context_path = self.service._context_path(self.world)
                if context_path.exists():
                    context_path.unlink()
                response = self.service.record_event({
                    "type": event_type,
                    "category": "node" if "block" in event_type else "runtime",
                    "success": True,
                    "details": details,
                    "worldId": self.world.name,
                })
                self.assertIn(task_key, response["completedTaskKeys"])
                self.assertIsNotNone(self.history_task(response["context"], task_key))

    def test_retired_rotate_task_is_removed_from_existing_world(self):
        context = self.service._default_context(self.world)
        context["activeTasks"].append({
            "taskKey": "tutorial.rotate_model",
            "type": "tutorial",
            "track": "scene",
            "status": "active",
            "createdAt": 1,
            "updatedAt": 1,
        })
        context_path = self.service._context_path(self.world)
        context_path.parent.mkdir(parents=True, exist_ok=True)
        context_path.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")

        loaded = self.service.load()["context"]
        self.assertNotIn("tutorial.rotate_model", self.active_task_keys(loaded))

    def test_first_score_update_clamps_and_persists_model_score(self):
        context = self.service.load()["context"]
        settings = type("Settings", (), {"api_key": "configured"})()
        response_text = json.dumps({
            "score": 126,
            "reasonCodes": ["fast_issue_resolution"],
        })
        with mock.patch.object(NodeGraphReviewService, "_resolve_settings", return_value=settings), \
             mock.patch.object(NodeGraphReviewService, "_call_deepseek", return_value=response_text):
            result = self.service._compute_score(self.world, context)

        self.assertTrue(result["success"])
        self.assertEqual(100, result["profile"]["score"])
        persisted = self.service.load()["context"]["profile"]
        self.assertEqual(100, persisted["score"])
        self.assertNotIn("role", persisted)
        self.assertNotIn("fluencyTier", persisted)

    def test_later_score_can_rise_with_recent_performance(self):
        context = self.service.load()["context"]
        context["profile"].update({"score": 20, "updatedAt": 1000})
        self.service._write_locked(self.world, context)
        settings = type("Settings", (), {"api_key": "configured"})()
        with mock.patch.object(NodeGraphReviewService, "_resolve_settings", return_value=settings), \
             mock.patch.object(NodeGraphReviewService, "_call_deepseek", return_value='{"score":100,"reasonCodes":["recent_success"]}'):
            result = self.service._compute_score(self.world, context)

        self.assertEqual(72, result["profile"]["score"])
        history = self.service.load()["context"]["profileHistory"]
        self.assertEqual(20, history[-1]["score"])

    def test_later_score_can_fall_with_recent_failures(self):
        context = self.service.load()["context"]
        context["profile"].update({"score": 80, "updatedAt": 1000})
        self.service._write_locked(self.world, context)
        settings = type("Settings", (), {"api_key": "configured"})()
        with mock.patch.object(NodeGraphReviewService, "_resolve_settings", return_value=settings), \
             mock.patch.object(NodeGraphReviewService, "_call_deepseek", return_value='{"score":20,"reasonCodes":["recent_failures"]}'):
            result = self.service._compute_score(self.world, context)

        self.assertEqual(41, result["profile"]["score"])
        history = self.service.load()["context"]["profileHistory"]
        self.assertEqual(80, history[-1]["score"])

    def test_legacy_profile_is_migrated_to_score_only(self):
        context = self.service._default_context(self.world)
        context["profile"] = {
            "role": "programmer",
            "confidence": 0.9,
            "fluencyScore": 68,
            "fluencyTier": "intermediate",
            "fluencyReasonCodes": ["legacy_reason"],
            "updatedAt": 123,
        }
        context_path = self.service._context_path(self.world)
        context_path.parent.mkdir(parents=True, exist_ok=True)
        context_path.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")

        profile = self.service.load()["context"]["profile"]
        self.assertEqual(68, profile["score"])
        self.assertEqual(["legacy_reason"], profile["reasonCodes"])
        self.assertNotIn("role", profile)
        self.assertNotIn("confidence", profile)
        self.assertNotIn("fluencyTier", profile)

    def test_repeated_issue_and_related_chat_are_remembered(self):
        task = {
            "action": "upsert",
            "worldId": self.world.name,
            "task": {
                "taskKey": "missing_actor_target|start|move",
                "type": "node-issue",
                "code": "missing_actor_target",
                "nodeId": "start",
                "blockId": "move",
                "title": "Missing actor",
            },
        }
        self.service.update_task(task)
        self.service.append_message({
            "worldId": self.world.name,
            "role": "user",
            "content": "How should this actor reference be connected?",
            "taskKey": task["task"]["taskKey"],
        })
        self.service.append_message({
            "worldId": self.world.name,
            "role": "assistant",
            "content": "Connect an object-reference block.",
            "taskKey": task["task"]["taskKey"],
        })
        self.service.update_task({**task, "action": "resolve"})
        self.service.update_task(task)

        memory = self.service.load()["context"]["issueMemory"]["missing_actor_target"]
        self.assertEqual(2, memory["occurrences"])
        self.assertEqual(1, memory["resolvedCount"])
        self.assertEqual(1, memory["chatDiscussionCount"])

    def test_node_move_completes_only_move_tutorial(self):
        response = self.service.record_event({
            "type": "node_moved",
            "category": "node",
            "success": True,
            "details": {"nodeId": "start"},
            "worldId": self.world.name,
        })
        self.assertEqual(["tutorial.move_node"], response["completedTaskKeys"])
        self.assertIsNotNone(self.history_task(response["context"], "tutorial.move_node"))
        self.assertIn("tutorial.connect_nodes", self.active_task_keys(response["context"]))
        self.assertIn("tutorial.drag_block", self.active_task_keys(response["context"]))

    def test_connection_requires_two_different_nodes(self):
        same_node = self.service.record_event({
            "type": "node_connected",
            "category": "node",
            "success": True,
            "details": {"sourceNodeId": "loop", "targetNodeId": "loop"},
            "worldId": self.world.name,
        })
        self.assertEqual([], same_node["completedTaskKeys"])
        self.assertIn("tutorial.connect_nodes", self.active_task_keys(same_node["context"]))

        different_nodes = self.service.record_event({
            "type": "node_connected",
            "category": "node",
            "success": True,
            "details": {"sourceNodeId": "start", "targetNodeId": "play"},
            "worldId": self.world.name,
        })
        self.assertEqual(["tutorial.connect_nodes"], different_nodes["completedTaskKeys"])

    def test_block_tutorial_requires_drag_interaction(self):
        picked = self.service.record_event({
            "type": "block_added",
            "category": "node",
            "success": True,
            "details": {"blockType": "logic_boolean", "interaction": "pick"},
            "worldId": self.world.name,
        })
        self.assertEqual([], picked["completedTaskKeys"])
        self.assertIn("tutorial.drag_block", self.active_task_keys(picked["context"]))

        dragged = self.service.record_event({
            "type": "block_added",
            "category": "node",
            "success": True,
            "details": {"blockType": "logic_boolean", "interaction": "drag"},
            "worldId": self.world.name,
        })
        self.assertEqual(["tutorial.drag_block"], dragged["completedTaskKeys"])

    def test_late_event_from_another_world_is_rejected(self):
        response = self.service.record_event({
            "type": "node_moved",
            "success": True,
            "worldId": "another_world",
        })
        self.assertFalse(response["success"])
        self.assertEqual("INVALID_CONTEXT_EVENT", response["error"])
        self.assertIn("其他世界", response["message"])


if __name__ == "__main__":
    unittest.main()
