from __future__ import annotations

import json
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from editor.plugins.AITool.services.node_graph_generation_service import NodeGraphGenerationService


def minimal_workspace():
    return {
        "version": 1,
        "nodes": [
            {
                "id": "start",
                "macroType": "state",
                "nodeType": "start",
                "name": "Start",
                "customName": "Initialize",
                "x": 80,
                "y": 120,
                "workspace": {},
            }
        ],
        "edges": [],
        "globalVariablesWorkspace": {},
    }


def control_workspace(
    actor="ball",
    *,
    movement_type="object_third_person_move",
    jump_actor=None,
    include_jump=True,
    include_score=False,
    custom_name="\u7403\u4f53\u63a7\u5236",
    edge_name="\u8fdb\u5165\u63a7\u5236",
):
    movement_fields = {
        "NAME": actor,
        "SPEED": 0.18,
        "OBSTACLE_TAG": "obstacle",
        "MIN_X": -12,
        "MAX_X": 12,
        "MIN_Z": -12,
        "MAX_Z": 12,
    }
    movement = {
        "type": movement_type,
        "id": "move-ball",
        "fields": movement_fields,
    }
    tail = movement
    if include_jump:
        jump = {
            "type": "object_arcade_jump",
            "id": "jump-ball",
            "fields": {
                "NAME": actor if jump_actor is None else jump_actor,
                "POWER": 0.28,
                "GRAVITY": 0.025,
                "GROUND_Y": 0.8,
            },
        }
        tail["next"] = {"block": jump}
        tail = jump
    if include_score:
        tail["next"] = {
            "block": {
                "type": "ui_set_score",
                "id": "unrequested-score",
                "fields": {"VALUE": 0},
            }
        }
    control = {
        "id": "control",
        "macroType": "state",
        "nodeType": "custom",
        "name": custom_name,
        "customName": custom_name,
        "x": 480,
        "y": 120,
        "workspace": {
            "blocks": {
                "languageVersion": 0,
                "blocks": [
                    {
                        "type": "node_while_active",
                        "id": "control-active",
                        "x": 24,
                        "y": 24,
                        "inputs": {"DO": {"block": movement}},
                    }
                ],
            }
        },
    }
    edge = {
        "id": "start-control",
        "source": {"nodeId": "start", "side": "right", "index": 0},
        "target": {"nodeId": "control", "side": "left", "index": 0},
        "name": edge_name,
        "conditionWorkspace": {
            "blocks": {
                "languageVersion": 0,
                "blocks": [
                    {
                        "type": "logic_boolean",
                        "id": "always-control",
                        "fields": {"BOOL": "TRUE"},
                        "x": 24,
                        "y": 24,
                    }
                ],
            }
        },
    }
    return {
        "version": 1,
        "nodes": [minimal_workspace()["nodes"][0], control],
        "edges": [edge],
        "globalVariablesWorkspace": {},
    }


def tag_velocity_workspace():
    workspace = control_workspace(include_jump=False)
    root = workspace["nodes"][1]["workspace"]["blocks"]["blocks"][0]
    root["inputs"]["DO"]["block"] = {
        "type": "object_set_tag_velocity_axis",
        "id": "wrong-tag-velocity",
        "fields": {"TAG_TEXT": "ball", "AXIS": "X", "VALUE_NUMBER": 0.1},
    }
    return workspace


def legacy_field_input_workspace(actor="bunny2"):
    start = minimal_workspace()["nodes"][0]
    start["workspace"] = {
        "blocks": {
            "languageVersion": 0,
            "blocks": [
                {
                    "type": "node_while_active",
                    "id": "active-root",
                    "x": 24,
                    "y": 24,
                    "inputs": {
                        "DO": {
                            "block": {
                                "type": "control_if",
                                "id": "legacy-if",
                                "fields": {"BOOL": "TRUE"},
                                "inputs": {
                                    "DO": {
                                        "block": {
                                            "type": "engine_rotateZ",
                                            "id": "legacy-rotate",
                                            "fields": {"ANGLE": 15, "OBJECT": actor},
                                        }
                                    }
                                },
                            }
                        }
                    },
                }
            ],
        }
    }
    return {
        "version": 1,
        "nodes": [start],
        "edges": [],
        "globalVariablesWorkspace": {},
    }


def request_payload(**overrides):
    value = {
        "schemaVersion": 1,
        "requestId": "request-1",
        "targetId": "node_graph:project:global",
        "projectScopeId": "world-scope-1",
        "baseGraphRevision": "revision-1",
        "operation": "create",
        "instruction": "Please create a dodgeball demo",
        "workspace": minimal_workspace(),
        "projectContext": {
            "sceneName": "default",
            "actors": [{"name": "Player", "type": "model", "tags": ["player"]}],
        },
    }
    value.update(overrides)
    return value


def generated_result(request=None, **overrides):
    request = request or request_payload()
    value = {
        "schemaVersion": 1,
        "requestId": request["requestId"],
        "targetId": request["targetId"],
        "projectScopeId": request["projectScopeId"],
        "baseGraphRevision": request["baseGraphRevision"],
        "operation": request["operation"],
        "summary": "Generated the dodgeball node graph.",
        "workspace": minimal_workspace(),
    }
    value.update(overrides)
    return value


class NodeGraphGenerationServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = NodeGraphGenerationService()

    def tearDown(self):
        self.service.shutdown()

    def test_prompt_contains_complete_contract_workspace_and_actor_context(self):
        request = self.service._normalize_payload(request_payload())
        _path, contract = self.service._load_contract()
        prompt = self.service._build_prompt(request, contract)
        self.assertIn(contract, prompt)
        self.assertIn('"baseGraphRevision":"revision-1"', prompt)
        self.assertIn('"nodes":[{"id":"start"', prompt)
        self.assertIn('"name":"Player"', prompt)
        self.assertIn("FULL_CORONA_BLOCKS_CONTRACT_XML", prompt)
        self.assertIn("control_if has no BOOL field", prompt)
        self.assertIn("inputs.OBJECT.block using object_reference", prompt)
        self.assertIn("choose an exact actor name from PROJECT_CONTEXT", prompt)
        self.assertNotIn("{...}", prompt)


    def test_chinese_instruction_sets_chinese_response_language(self):
        request = self.service._normalize_payload(
            request_payload(instruction="\u5e2e\u6211\u7ed9\u7403\u52a0\u4e0a WASD \u548c\u7a7a\u683c\u8df3\u8dc3", responseLanguage="")
        )
        self.assertEqual("zh-CN", request["responseLanguage"])

    def test_prompt_scopes_wasd_jump_to_minimal_real_object_control(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="extend",
                instruction="\u5e2e\u6211\u7ed9\u5f53\u524d\u573a\u666f\u4e2d\u7684\u7403\u52a0\u4e00\u4e2a WASD \u548c\u7a7a\u683c\u8df3\u8dc3",
                responseLanguage="zh-CN",
            )
        )
        _path, contract = self.service._load_contract()
        prompt = self.service._build_prompt(request, contract)
        self.assertIn("object_third_person_move", prompt)
        self.assertIn("object_arcade_jump", prompt)
        self.assertIn("object_set_tag_velocity_axis", prompt)
        self.assertIn("Do not expand a small feature into a full game", prompt)
        self.assertIn('"responseLanguage":"zh-CN"', prompt)

    def test_chinese_request_rejects_english_summary_and_labels(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="extend",
                instruction="\u7ed9\u7403\u52a0 WASD \u548c\u7a7a\u683c\u8df3\u8dc3",
                responseLanguage="zh-CN",
            )
        )
        contract_path, _contract = self.service._load_contract()
        result = generated_result(
            request,
            summary="Added ball controls.",
            workspace=control_workspace(custom_name="Play", edge_name="Start Play"),
        )
        with self.assertRaisesRegex(ValueError, "summary"):
            self.service._validate_result(result, request, contract_path)

    def test_tag_velocity_template_cannot_satisfy_wasd_and_jump(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="extend",
                instruction="\u7ed9\u7403\u52a0 WASD \u548c\u7a7a\u683c\u8df3\u8dc3",
                responseLanguage="zh-CN",
            )
        )
        contract_path, _contract = self.service._load_contract()
        result = generated_result(
            request,
            summary="\u5df2\u6dfb\u52a0\u7403\u4f53\u63a7\u5236\u3002",
            workspace=tag_velocity_workspace(),
        )
        with self.assertRaisesRegex(ValueError, "object_third_person_move"):
            self.service._validate_result(result, request, contract_path)

    def test_wasd_and_jump_chain_for_same_real_actor_is_accepted(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="extend",
                instruction="\u7ed9\u7403\u52a0 WASD \u548c\u7a7a\u683c\u8df3\u8dc3",
                responseLanguage="zh-CN",
                projectContext={"actors": [{"name": "ball", "type": "model", "tags": []}]},
            )
        )
        contract_path, _contract = self.service._load_contract()
        normalized = self.service._validate_result(
            generated_result(
                request,
                summary="\u5df2\u4e3a\u7403\u6dfb\u52a0 WASD \u79fb\u52a8\u548c\u7a7a\u683c\u8df3\u8dc3\u3002",
                workspace=control_workspace(),
            ),
            request,
            contract_path,
        )
        self.assertEqual(2, len(normalized["workspace"]["nodes"]))

    def test_movement_and_jump_must_target_the_same_actor(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="extend",
                instruction="\u7ed9\u7403\u52a0 WASD \u548c\u7a7a\u683c\u8df3\u8dc3",
                responseLanguage="zh-CN",
                projectContext={
                    "actors": [
                        {"name": "ball", "type": "model", "tags": []},
                        {"name": "other", "type": "model", "tags": []},
                    ]
                },
            )
        )
        contract_path, _contract = self.service._load_contract()
        result = generated_result(
            request,
            summary="\u5df2\u6dfb\u52a0\u79fb\u52a8\u548c\u8df3\u8dc3\u3002",
            workspace=control_workspace(jump_actor="other"),
        )
        with self.assertRaisesRegex(ValueError, "\u540c\u4e00\u4e2a\u5bf9\u8c61"):
            self.service._validate_result(result, request, contract_path)

    def test_control_target_must_exist_in_scene_context(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="extend",
                instruction="\u7ed9\u7403\u52a0 WASD \u548c\u7a7a\u683c\u8df3\u8dc3",
                responseLanguage="zh-CN",
                projectContext={"actors": [{"name": "Player", "type": "model", "tags": []}]},
            )
        )
        contract_path, _contract = self.service._load_contract()
        result = generated_result(
            request,
            summary="\u5df2\u6dfb\u52a0\u7403\u4f53\u63a7\u5236\u3002",
            workspace=control_workspace(actor="ball"),
        )
        with self.assertRaisesRegex(ValueError, "\u4e0d\u5b58\u5728\u4e8e\u5f53\u524d\u573a\u666f"):
            self.service._validate_result(result, request, contract_path)

    def test_narrow_control_request_rejects_unrequested_score_logic(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="extend",
                instruction="\u7ed9\u7403\u52a0 WASD \u548c\u7a7a\u683c\u8df3\u8dc3",
                responseLanguage="zh-CN",
                projectContext={"actors": [{"name": "ball", "type": "model", "tags": []}]},
            )
        )
        contract_path, _contract = self.service._load_contract()
        result = generated_result(
            request,
            summary="\u5df2\u6dfb\u52a0\u7403\u4f53\u63a7\u5236\u3002",
            workspace=control_workspace(include_score=True),
        )
        with self.assertRaisesRegex(ValueError, "ui_set_score"):
            self.service._validate_result(result, request, contract_path)

    def test_legacy_bool_and_object_fields_are_safely_normalized(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="extend",
                instruction="\u7ed9\u5154\u5b50\u6dfb\u52a0\u65cb\u8f6c\u529f\u80fd",
                responseLanguage="zh-CN",
                projectContext={"actors": [{"name": "bunny2", "type": "model", "tags": []}]},
            )
        )
        contract_path, _contract = self.service._load_contract()
        normalized = self.service._validate_result(
            generated_result(
                request,
                summary="\u5df2\u4e3a\u5154\u5b50\u6dfb\u52a0\u65cb\u8f6c\u529f\u80fd\u3002",
                workspace=legacy_field_input_workspace(),
            ),
            request,
            contract_path,
        )
        root = normalized["workspace"]["nodes"][0]["workspace"]["blocks"]["blocks"][0]
        control_if = root["inputs"]["DO"]["block"]
        rotate = control_if["inputs"]["DO"]["block"]
        self.assertNotIn("BOOL", control_if.get("fields", {}))
        self.assertEqual(
            "logic_boolean", control_if["inputs"]["CONDITION"]["block"]["type"]
        )
        self.assertNotIn("OBJECT", rotate.get("fields", {}))
        self.assertEqual(
            "bunny2", rotate["inputs"]["OBJECT"]["block"]["fields"]["OBJECT"]
        )
        self.assertTrue(any("moved BOOL" in item for item in normalized["warnings"]))
        self.assertTrue(any("moved OBJECT" in item for item in normalized["warnings"]))

    def test_object_reference_must_exist_in_current_scene(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="extend",
                instruction="\u7ed9\u5154\u5b50\u6dfb\u52a0\u65cb\u8f6c\u529f\u80fd",
                responseLanguage="zh-CN",
                projectContext={"actors": [{"name": "bunny2", "type": "model", "tags": []}]},
            )
        )
        contract_path, _contract = self.service._load_contract()
        result = generated_result(
            request,
            summary="\u5df2\u6dfb\u52a0\u65cb\u8f6c\u529f\u80fd\u3002",
            workspace=legacy_field_input_workspace(actor="missing-rabbit"),
        )
        with self.assertRaisesRegex(ValueError, "\u4e0d\u5b58\u5728\u4e8e\u5f53\u524d\u573a\u666f"):
            self.service._validate_result(result, request, contract_path)

    def test_unknown_fields_are_still_rejected_after_safe_normalization(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="extend",
                instruction="\u7ed9\u5154\u5b50\u6dfb\u52a0\u65cb\u8f6c\u529f\u80fd",
                responseLanguage="zh-CN",
                projectContext={"actors": [{"name": "bunny2", "type": "model", "tags": []}]},
            )
        )
        contract_path, _contract = self.service._load_contract()
        workspace = legacy_field_input_workspace()
        rotate = workspace["nodes"][0]["workspace"]["blocks"]["blocks"][0]["inputs"]["DO"]["block"]["inputs"]["DO"]["block"]
        rotate["fields"]["BROKEN"] = 1
        result = generated_result(
            request,
            summary="\u5df2\u6dfb\u52a0\u65cb\u8f6c\u529f\u80fd\u3002",
            workspace=workspace,
        )
        with self.assertRaisesRegex(ValueError, "unknown field BROKEN"):
            self.service._validate_result(result, request, contract_path)

    def test_replacement_instruction_extracts_source_and_target(self):
        requirements = self.service._instruction_requirements(
            "\u8bf7\u5c06\u79fb\u52a8\u79ef\u6728\u7684\u5bf9\u8c61\u6539\u4e3a bunny2\uff0c"
        )
        self.assertEqual(
            {"source": "\u79fb\u52a8\u79ef\u6728\u7684\u5bf9\u8c61", "target": "bunny2"},
            requirements["replacementDirective"],
        )

    def test_edit_prompt_requires_in_place_change(self):
        request = self.service._normalize_payload(
            request_payload(
                operation="edit",
                instruction="\u5c06\u79fb\u52a8\u79ef\u6728\u7684\u5bf9\u8c61\u6539\u4e3a bunny2",
                responseLanguage="zh-CN",
            )
        )
        _path, contract = self.service._load_contract()
        prompt = self.service._build_prompt(request, contract)
        self.assertIn("Edit the current workspace in place", prompt)
        self.assertIn("Do not clear or rebuild the graph", prompt)
        self.assertIn('"target":"bunny2"', prompt)

    def test_edit_cannot_remove_existing_node_or_edge(self):
        before = control_workspace(actor="bunny1", include_jump=False)
        request = self.service._normalize_payload(
            request_payload(
                operation="edit",
                instruction="\u5c06\u79fb\u52a8\u79ef\u6728\u7684\u5bf9\u8c61\u6539\u4e3a bunny2",
                responseLanguage="zh-CN",
                workspace=before,
            )
        )
        without_node = {**before, "nodes": before["nodes"][:1]}
        with self.assertRaisesRegex(ValueError, "removed existing structures"):
            self.service._validate_operation_scope({"workspace": without_node}, request)
        without_edge = {**before, "edges": []}
        with self.assertRaisesRegex(ValueError, "removed existing structures"):
            self.service._validate_operation_scope({"workspace": without_edge}, request)

    def test_edit_must_change_existing_logic(self):
        before = control_workspace(actor="bunny1", include_jump=False)
        request = self.service._normalize_payload(
            request_payload(
                operation="edit",
                instruction="\u5c06\u79fb\u52a8\u79ef\u6728\u7684\u5bf9\u8c61\u6539\u4e3a bunny2",
                responseLanguage="zh-CN",
                workspace=before,
            )
        )
        with self.assertRaisesRegex(ValueError, "did not change any node logic"):
            self.service._validate_operation_scope({"workspace": before}, request)

    def test_edit_can_replace_only_an_existing_object_reference(self):
        before = control_workspace(actor="bunny1", include_jump=False)
        after = control_workspace(actor="bunny2", include_jump=False)
        request = self.service._normalize_payload(
            request_payload(
                operation="edit",
                instruction="\u5c06\u79fb\u52a8\u79ef\u6728\u7684\u5bf9\u8c61\u6539\u4e3a bunny2",
                responseLanguage="zh-CN",
                workspace=before,
                projectContext={
                    "actors": [
                        {"name": "bunny1", "type": "model", "tags": []},
                        {"name": "bunny2", "type": "model", "tags": []},
                    ]
                },
            )
        )
        contract_path, _contract = self.service._load_contract()
        normalized = self.service._validate_result(
            generated_result(
                request,
                summary="\u5df2\u5c06\u79fb\u52a8\u79ef\u6728\u7684\u5bf9\u8c61\u6539\u4e3a bunny2\u3002",
                workspace=after,
            ),
            request,
            contract_path,
        )
        self.assertEqual(
            "bunny2",
            normalized["workspace"]["nodes"][1]["workspace"]["blocks"]["blocks"][0]
            ["inputs"]["DO"]["block"]["fields"]["NAME"],
        )
        self.assertEqual(
            [node["id"] for node in before["nodes"]],
            [node["id"] for node in normalized["workspace"]["nodes"]],
        )
        self.assertEqual(
            [edge["id"] for edge in before["edges"]],
            [edge["id"] for edge in normalized["workspace"]["edges"]],
        )

    def test_wrong_request_identity_is_rejected(self):
        request = self.service._normalize_payload(request_payload())
        contract_path, _contract = self.service._load_contract()
        result = generated_result(request, baseGraphRevision="stale-revision")
        with self.assertRaisesRegex(ValueError, "baseGraphRevision"):
            self.service._validate_result(result, request, contract_path)

    def test_valid_complete_workspace_passes_contract_validation(self):
        request = self.service._normalize_payload(request_payload())
        contract_path, _contract = self.service._load_contract()
        normalized = self.service._validate_result(generated_result(request), request, contract_path)
        self.assertEqual("node_graph:project:global", normalized["targetId"])
        self.assertEqual("revision-1", normalized["baseGraphRevision"])
        self.assertEqual(1, len(normalized["workspace"]["nodes"]))

    def test_forbidden_python_or_xml_fields_are_rejected(self):
        request = self.service._normalize_payload(request_payload())
        contract_path, _contract = self.service._load_contract()
        for forbidden in ("python", "generatedCode", "xml"):
            with self.subTest(forbidden=forbidden):
                result = generated_result(request)
                result[forbidden] = "not allowed"
                with self.assertRaisesRegex(ValueError, forbidden):
                    self.service._validate_result(result, request, contract_path)


    def test_rejected_semantic_result_is_retried_once(self):
        payload = request_payload(
            operation="extend",
            instruction="\u7ed9\u7403\u52a0 WASD \u548c\u7a7a\u683c\u8df3\u8dc3",
            responseLanguage="zh-CN",
            projectContext={"actors": [{"name": "ball", "type": "model", "tags": []}]},
        )
        invalid = generated_result(
            payload,
            summary="\u5df2\u6dfb\u52a0\u7403\u4f53\u63a7\u5236\u3002",
            workspace=tag_velocity_workspace(),
        )
        valid = generated_result(
            payload,
            summary="\u5df2\u4e3a\u7403\u6dfb\u52a0 WASD \u79fb\u52a8\u548c\u7a7a\u683c\u8df3\u8dc3\u3002",
            workspace=control_workspace(),
        )
        settings = SimpleNamespace(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-test",
            source="unit-test",
        )
        responses = [
            json.dumps(invalid, ensure_ascii=False),
            json.dumps(valid, ensure_ascii=False),
        ]
        with mock.patch.object(
            NodeGraphGenerationService, "_call_deepseek", side_effect=responses
        ) as provider, mock.patch(
            "editor.plugins.AITool.services.node_graph_generation_service.NodeGraphReviewService._resolve_settings",
            return_value=settings,
        ):
            result = self.service.generate(payload)
        self.assertTrue(result["success"])
        self.assertEqual(2, provider.call_count)

    def test_async_task_reaches_completed_without_real_provider_call(self):
        request = request_payload()
        settings = SimpleNamespace(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-test",
            source="unit-test",
        )
        response = json.dumps(generated_result(request), ensure_ascii=False)
        with mock.patch.object(NodeGraphGenerationService, "_call_deepseek", return_value=response), mock.patch(
            "editor.plugins.AITool.services.node_graph_generation_service.NodeGraphReviewService._resolve_settings",
            return_value=settings,
        ):
            started = self.service.start(request)
            self.assertTrue(started["success"])
            deadline = time.time() + 3
            status = self.service.status(started["taskId"])
            while status.get("status") == "pending" and time.time() < deadline:
                time.sleep(0.01)
                status = self.service.status(started["taskId"])
        self.assertEqual("completed", status["status"])
        self.assertTrue(status["result"]["success"])
        self.assertEqual("ok", status["result"]["status"])

    def test_cancelled_task_stays_cancelled(self):
        def wait_for_cancel(_payload, cancel_event):
            cancel_event.wait(1)
            return {"success": False, "status": "error", "error": "GENERATION_CANCELLED"}

        with mock.patch.object(self.service, "generate", side_effect=wait_for_cancel):
            started = self.service.start(request_payload())
            cancelled = self.service.cancel(started["taskId"])
            self.assertTrue(cancelled["success"])
            deadline = time.time() + 2
            status = self.service.status(started["taskId"])
            while status.get("status") == "pending" and time.time() < deadline:
                time.sleep(0.01)
                status = self.service.status(started["taskId"])
        self.assertEqual("cancelled", status["status"])


if __name__ == "__main__":
    unittest.main()
