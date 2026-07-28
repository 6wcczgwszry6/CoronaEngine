import json
import pathlib
import sys
import tempfile
import time
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


    def test_node_issue_persists_edge_pattern_without_double_counting_active_upsert(self):
        payload = {
            "action": "upsert",
            "worldId": self.world.name,
            "task": {
                "taskKey": "invalid_edge_endpoint|start||edge_1",
                "type": "node-issue",
                "code": "invalid_edge_endpoint",
                "nodeId": "start",
                "edgeId": "edge_1",
                "pattern": {
                    "relationType": "transition",
                    "edgeId": "edge_1",
                },
                "title": "repair edge",
            },
        }
        first = self.service.update_task(payload)
        second = self.service.update_task(payload)
        task = next(item for item in second["context"]["activeTasks"] if item["taskKey"] == payload["task"]["taskKey"])
        memory = second["context"]["issueMemory"]["invalid_edge_endpoint"]
        self.assertEqual("edge_1", task["edgeId"])
        self.assertEqual("transition", task["pattern"]["relationType"])
        self.assertEqual("edge_1", task["pattern"]["edgeId"])
        self.assertEqual(1, memory["occurrences"])
        self.assertEqual(1, first["context"]["issueMemory"]["invalid_edge_endpoint"]["occurrences"])

    def test_assistant_showcase_metadata_is_persisted_and_invalid_intent_is_rejected(self):
        valid = self.service.append_message({
            "worldId": self.world.name,
            "role": "assistant",
            "content": "Follow these steps.",
            "needsShowcase": True,
            "guidanceIntent": "connect_object_reference",
            "steps": ["Open Node Dock", "repair edge"],
        })
        self.assertTrue(valid["message"]["needsShowcase"])
        self.assertEqual("connect_object_reference", valid["message"]["guidanceIntent"])
        self.assertEqual(["Open Node Dock", "repair edge"], valid["message"]["steps"])

        invalid = self.service.append_message({
            "worldId": self.world.name,
            "role": "assistant",
            "content": "Reject unknown guidance.",
            "needsShowcase": True,
            "guidanceIntent": "querySelector:anything",
            "steps": ["Unknown action"],
        })
        self.assertFalse(invalid["message"]["needsShowcase"])
        self.assertEqual("", invalid["message"]["guidanceIntent"])


    @staticmethod
    def goal_plan_payload():
        effects = [
            {
                "effectId": "player_move_jump",
                "title": "player movement and jump",
                "description": "the player moves with WASD and jumps between platforms",
                "trigger": "keyboard input",
                "outcome": "the player changes position and can leave the ground",
                "recommendedBlockTypes": ["object_third_person_move", "object_arcade_jump"],
                "verification": "the player can move and jump after running the graph",
            },
            {
                "effectId": "rabbit_behavior",
                "title": "rabbit behavior",
                "description": "the rabbit changes its position inside the play area",
                "trigger": "gameplay update",
                "outcome": "the rabbit appears to roam",
                "recommendedBlockTypes": ["object_set_random_position"],
                "verification": "the rabbit changes position in the allowed area",
            },
            {
                "effectId": "mechanism_collision",
                "title": "mechanism collision",
                "description": "the mechanism participates in logical collision",
                "trigger": "player contact",
                "outcome": "the mechanism can be used by collision gameplay",
                "recommendedBlockTypes": ["object_set_logical_collision"],
                "verification": "the node graph runs with collision behavior enabled",
            },
        ]
        task_specs = [
            ("player_move_jump", "node_created", []),
            ("player_move_jump", "block_added", ["object_third_person_move"]),
            ("player_move_jump", "block_added", ["object_arcade_jump"]),
            ("rabbit_behavior", "block_added", ["object_set_random_position"]),
            ("mechanism_collision", "block_added", ["object_set_logical_collision"]),
            ("mechanism_collision", "run_succeeded", []),
        ]
        return {
            "logicBlueprint": {
                "worldSummary": "an ink-style fantasy exploration world",
                "coreLoop": "move and jump across platforms, observe the rabbit, and avoid mechanisms",
                "requiredActors": ["player", "rabbit", "mechanism", "platform"],
                "nodeEffects": effects,
                "flow": ["initialize", "move and jump", "rabbit behavior", "collision", "run verification"],
            },
            "tasks": [
                {
                    "phase": "node-logic",
                    "effectId": effect_id,
                    "title": f"goal step {index}",
                    "message": f"build gameplay effect {effect_id}",
                    "suggestion": f"finish the {effect_id} node logic",
                    "completionCriteria": f"signal {signal} is observed for the requested effect",
                    "completionSignal": signal,
                    "requiredBlockTypes": block_types,
                }
                for index, (effect_id, signal, block_types) in enumerate(task_specs, start=1)
            ],
        }

    def test_empty_world_prompt_keeps_default_tutorial_tasks(self):
        response = self.service.start_goal_plan({"prompt": "", "mode": "story"})
        self.assertTrue(response["success"])
        self.assertEqual("completed", response["status"])
        context = response["context"]
        self.assertEqual("default", context["worldGoal"]["source"])
        self.assertTrue(any(task.get("type") == "tutorial" for task in context["activeTasks"]))
        self.assertFalse(any(task.get("type") == "goal" for task in context["activeTasks"]))

    def test_goal_plan_prompt_only_requests_personalized_guidance_tasks(self):
        prompt = self.service._goal_plan_prompt(
            "水墨风的仙侠秘境，有兔子、机关和可以跳跃的平台", "story",
        )
        self.assertIn("个性化搭建任务", prompt)
        self.assertIn("不能直接修改当前节点区", prompt)
        self.assertIn("不是替用户生成一套节点积木", prompt)
        self.assertIn("一步一步引导用户亲自完成世界", prompt)

    def test_goal_plan_rejects_unknown_completion_signal(self):
        context = self.service._default_context(self.world)
        payload = self.goal_plan_payload()
        payload["tasks"][0]["completionSignal"] = "write_python_script"
        with self.assertRaises(ValueError):
            self.service._normalize_goal_plan_tasks(payload, context, self.service._now_ms())


    def test_goal_plan_rejects_unknown_block_type(self):
        context = self.service._default_context(self.world)
        payload = self.goal_plan_payload()
        payload["tasks"][1]["requiredBlockTypes"] = ["invented_collision_block"]
        with self.assertRaises(ValueError):
            self.service._normalize_goal_plan_tasks(payload, context, self.service._now_ms())

    def test_goal_plan_requires_node_tasks_before_scene_polish(self):
        context = self.service._default_context(self.world)
        payload = self.goal_plan_payload()
        payload["tasks"][1].update({
            "phase": "scene-polish",
            "effectId": "",
            "completionSignal": "object_transformed",
            "requiredBlockTypes": [],
        })
        with self.assertRaises(ValueError):
            self.service._normalize_goal_plan_tasks(payload, context, self.service._now_ms())

    def test_goal_block_task_ignores_unrelated_block_type(self):
        context = self.service._default_context(self.world)
        context["worldGoal"] = {
            "prompt": "ink fantasy world with a rabbit and mechanisms",
            "mode": "story",
            "source": "ai",
            "status": "ready",
            "generatedAt": self.service._now_ms(),
            "generationError": "",
        }
        context["activeTasks"] = self.service._normalize_goal_plan_tasks(
            self.goal_plan_payload(), context, self.service._now_ms(),
        )
        self.service._ensure_task_slots_locked(context, self.service._now_ms())
        self.service._write_locked(self.world, context)

        unrelated = self.service.record_event({
            "type": "block_added",
            "category": "node",
            "success": True,
            "details": {"blockType": "logic_boolean", "interaction": "drag"},
            "worldId": self.world.name,
        })
        self.assertEqual([], unrelated["completedTaskKeys"])
        move_task = next(
            task for task in unrelated["context"]["activeTasks"]
            if task.get("taskKey") == "goal.ai.02"
        )
        self.assertEqual([], move_task["observedBlockTypes"])

        matched = self.service.record_event({
            "type": "block_added",
            "category": "node",
            "success": True,
            "details": {"blockType": "object_third_person_move", "interaction": "drag"},
            "worldId": self.world.name,
        })
        self.assertEqual(["goal.ai.02"], matched["completedTaskKeys"])
        archived = self.history_task(matched["context"], "goal.ai.02")
        self.assertEqual(["object_third_person_move"], archived["observedBlockTypes"])

    def test_ai_goal_plan_replaces_tutorials_and_shows_two_tasks(self):
        with mock.patch.object(
            CabbageContextService,
            "_call_deepseek_for_goal_plan",
            return_value=self.goal_plan_payload(),
        ):
            started = self.service.start_goal_plan({
                "prompt": "a puzzle world across floating islands",
                "mode": "story",
            })
            self.assertTrue(started["success"])
            self.assertEqual("pending", started["status"])
            deadline = time.monotonic() + 3
            result = None
            while time.monotonic() < deadline:
                status = self.service.goal_plan_status(started["taskId"])
                if status.get("status") == "completed":
                    result = status.get("result")
                    break
                time.sleep(0.02)

        self.assertIsNotNone(result)
        self.assertTrue(result["success"])
        context = result["context"]
        self.assertEqual("ai", context["worldGoal"]["source"])
        self.assertEqual(2, context["goalTaskPlan"]["schemaVersion"])
        self.assertEqual(6, context["goalTaskPlan"]["taskCount"])
        self.assertEqual(6, context["goalTaskPlan"]["nodeTaskCount"])
        self.assertEqual(0, context["goalTaskPlan"]["sceneTaskCount"])
        self.assertEqual(
            "an ink-style fantasy exploration world",
            context["goalTaskPlan"]["logicBlueprint"]["worldSummary"],
        )
        self.assertFalse(any(task.get("type") == "tutorial" for task in context["activeTasks"]))
        visible = [
            task for task in context["activeTasks"]
            if task.get("type") == "goal" and task.get("status") == "active"
        ]
        queued = [
            task for task in context["activeTasks"]
            if task.get("type") == "goal" and task.get("status") == "queued"
        ]
        self.assertEqual(2, len(visible))
        self.assertEqual(4, len(queued))

    def test_completing_goal_task_reveals_next_ai_task(self):
        context = self.service._default_context(self.world)
        context["worldGoal"] = {
            "prompt": "a puzzle world across floating islands",
            "mode": "story",
            "source": "ai",
            "status": "ready",
            "generatedAt": self.service._now_ms(),
            "generationError": "",
        }
        context["activeTasks"] = self.service._normalize_goal_plan_tasks(
            self.goal_plan_payload(), context, self.service._now_ms(),
        )
        self.service._ensure_task_slots_locked(context, self.service._now_ms())
        self.service._write_locked(self.world, context)

        response = self.service.record_event({
            "type": "node_created",
            "category": "node",
            "success": True,
            "details": {"nodeId": "start"},
            "worldId": self.world.name,
        })
        self.assertEqual(["goal.ai.01"], response["completedTaskKeys"])
        self.assertIsNotNone(self.history_task(response["context"], "goal.ai.01"))
        visible_keys = {
            task.get("taskKey")
            for task in response["context"]["activeTasks"]
            if task.get("type") == "goal" and task.get("status") == "active"
        }
        self.assertEqual({"goal.ai.02", "goal.ai.03"}, visible_keys)


if __name__ == "__main__":
    unittest.main()
