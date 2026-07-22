import importlib.util
import io
import json
import pathlib
import sys
import time
import types
import unittest
from unittest import mock

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "node_graph_review_service.py"
SPEC = importlib.util.spec_from_file_location("node_graph_review_service_under_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

NodeGraphReviewService = MODULE.NodeGraphReviewService
DeepSeekSettings = MODULE.DeepSeekSettings


def block(block_type, block_id, fields=None, inputs=None, next_block=None):
    value = {"type": block_type, "id": block_id}
    if fields:
        value["fields"] = fields
    if inputs:
        value["inputs"] = inputs
    if next_block:
        value["next"] = {"block": next_block}
    return value


def graph(nodes=None, edges=None):
    return {
        "version": 1,
        "nodes": nodes or [],
        "edges": edges or [],
        "globalVariablesWorkspace": {},
    }


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class NodeGraphReviewServiceTests(unittest.TestCase):
    def test_contract_path_is_found_from_packaged_editor_layout(self):
        with self.subTest("source checkout"):
            resolved = NodeGraphReviewService._find_contract_path(MODULE_PATH)
            self.assertTrue(resolved.is_file())
            self.assertEqual(NodeGraphReviewService.CONTRACT_FILENAME, resolved.name)

        with self.subTest("packaged CabbageEditor layout"):
            fake_service = (
                MODULE_PATH.parents[4]
                / "build"
                / "examples"
                / "engine"
                / "RelWithDebInfo"
                / "CabbageEditor"
                / "plugins"
                / "AITool"
                / "services"
                / "node_graph_review_service.py"
            )
            resolved = NodeGraphReviewService._find_contract_path(fake_service)
            self.assertTrue(resolved.is_file())
            self.assertEqual(NodeGraphReviewService.CONTRACT_FILENAME, resolved.name)

    def test_parses_fenced_json_with_surrounding_text(self):
        result = NodeGraphReviewService._parse_model_result(
            '```json\n{"hasProblems":true,"summary":"有问题","issues":[]}\n```'
        )
        self.assertTrue(result["hasProblems"])

        result = NodeGraphReviewService._parse_model_result(
            '说明：{"hasProblems":false,"summary":"","issues":[]} trailing'
        )
        self.assertFalse(result["hasProblems"])

    def test_unknown_issue_references_are_filtered(self):
        workspace = graph(
            nodes=[
                {
                    "id": "start",
                    "nodeType": "start",
                    "workspace": {
                        "blocks": {"blocks": [block("node_when_enter", "enter_1")]}
                    },
                }
            ]
        )
        request = {"workspace": workspace}
        result = {
            "hasProblems": True,
            "summary": "有问题",
            "issues": [
                {"nodeId": "missing", "blockId": "", "code": "bad", "confidence": 0.95},
                {"nodeId": "start", "blockId": "enter_1", "code": "good", "confidence": 0.95},
            ],
        }
        NodeGraphReviewService._validate_model_result(result, request)
        self.assertEqual(["good"], [item["code"] for item in result["issues"]])

    def test_deepseek_request_uses_json_mode_and_current_model(self):
        settings = DeepSeekSettings(
            api_key="test-secret",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-v4-flash",
            source="test",
        )
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return _Response(
                {"choices": [{"message": {"content": '{"hasProblems":false,"summary":"","issues":[]}'}}]}
            )

        with mock.patch.object(MODULE.urllib.request, "urlopen", fake_urlopen):
            text = NodeGraphReviewService._call_deepseek(settings, "review")

        self.assertEqual("https://api.deepseek.com/v1/chat/completions", captured["url"])
        self.assertEqual("deepseek-v4-flash", captured["body"]["model"])
        self.assertEqual({"type": "json_object"}, captured["body"]["response_format"])
        self.assertEqual({"type": "disabled"}, captured["body"]["thinking"])
        self.assertNotIn("test-secret", text)

    def test_simple_single_node_is_not_flagged_for_missing_gameplay(self):
        workspace = graph(
            nodes=[
                {
                    "id": "start",
                    "nodeType": "start",
                    "workspace": {
                        "blocks": {"blocks": [block("node_when_enter", "enter")]}
                    },
                }
            ]
        )
        catalog = {"node_when_enter": {"outputCheck": ""}}
        with mock.patch.object(NodeGraphReviewService, "_catalog_index", return_value=catalog):
            facts = NodeGraphReviewService._collect_local_facts(workspace, {})

        self.assertEqual([], facts)

    def test_local_facts_report_only_high_confidence_structure_errors(self):
        workspace = graph(
            nodes=[
                {
                    "id": "start",
                    "nodeType": "start",
                    "workspace": {
                        "blocks": {
                            "blocks": [
                                block("unknown_runtime_block", "duplicate"),
                                block("node_when_enter", "duplicate"),
                            ]
                        }
                    },
                },
                {"id": "start", "nodeType": "start", "workspace": {}},
            ],
            edges=[
                {
                    "id": "bad_edge",
                    "source": {"nodeId": "start"},
                    "target": {"nodeId": "missing"},
                    "conditionWorkspace": {
                        "blocks": {
                            "blocks": [block("math_number", "condition", {"NUM": 1})]
                        }
                    },
                }
            ],
        )
        catalog = {
            "node_when_enter": {"outputCheck": ""},
            "math_number": {"outputCheck": "Number"},
        }
        with mock.patch.object(NodeGraphReviewService, "_catalog_index", return_value=catalog):
            facts = NodeGraphReviewService._collect_local_facts(workspace, {})

        codes = {item["code"] for item in facts}
        self.assertIn("duplicate_node_id", codes)
        self.assertIn("start_node_count", codes)
        self.assertIn("duplicate_block_id", codes)
        self.assertIn("unknown_block_type", codes)
        self.assertIn("dangling_edge", codes)
        self.assertIn("non_boolean_condition", codes)
        self.assertNotIn("missing_outgoing_edge", codes)
        self.assertNotIn("shooting_without_cooldown", codes)
        self.assertNotIn("score_never_increases", codes)

    def test_variable_name_is_not_treated_as_actor_reference(self):
        workspace = graph(
            nodes=[
                {
                    "id": "start",
                    "nodeType": "start",
                    "workspace": {
                        "blocks": {
                            "blocks": [
                                block(
                                    "variable_get",
                                    "variable",
                                    {"NAME": "not_an_actor"},
                                )
                            ]
                        }
                    },
                }
            ]
        )
        catalog = {"variable_get": {"outputCheck": ""}}
        context = {"actors": [{"name": "Player"}]}
        with mock.patch.object(NodeGraphReviewService, "_catalog_index", return_value=catalog):
            facts = NodeGraphReviewService._collect_local_facts(workspace, context)

        self.assertFalse(
            {"missing_actor_target", "actor_target_not_found"}
            & {item["code"] for item in facts}
        )

    def test_actor_context_block_requires_explicit_project_target(self):
        workspace = graph(nodes=[{
            "id": "start",
            "nodeType": "start",
            "workspace": {"blocks": {"blocks": [block("engine_moveto", "move")] }},
        }])
        catalog = {"engine_moveto": {"outputCheck": "", "projectUsage": "actor-context"}}
        with mock.patch.object(NodeGraphReviewService, "_catalog_index", return_value=catalog):
            facts = NodeGraphReviewService._collect_local_facts(
                workspace, {"actors": [{"name": "Player"}]}
            )

        issue = next(item for item in facts if item["code"] == "missing_actor_target")
        self.assertEqual("start", issue["nodeId"])
        self.assertEqual("move", issue["blockId"])
        self.assertEqual("engine_moveto", issue["blockType"])

    def test_empty_explicit_actor_field_is_reported(self):
        workspace = graph(nodes=[{
            "id": "start",
            "nodeType": "start",
            "workspace": {"blocks": {"blocks": [
                block("object_set_position", "move", {"NAME": ""})
            ]}},
        }])
        catalog = {"object_set_position": {"outputCheck": "", "projectUsage": "project-safe"}}
        with mock.patch.object(NodeGraphReviewService, "_catalog_index", return_value=catalog):
            facts = NodeGraphReviewService._collect_local_facts(
                workspace, {"actors": [{"name": "Player"}]}
            )

        self.assertIn("missing_actor_target", {item["code"] for item in facts})

    def test_existing_explicit_actor_is_accepted(self):
        workspace = graph(nodes=[{
            "id": "start",
            "nodeType": "start",
            "workspace": {"blocks": {"blocks": [
                block("object_set_position", "move", {"NAME": "Player"})
            ]}},
        }])
        catalog = {"object_set_position": {"outputCheck": "", "projectUsage": "project-safe"}}
        with mock.patch.object(NodeGraphReviewService, "_catalog_index", return_value=catalog):
            facts = NodeGraphReviewService._collect_local_facts(
                workspace, {"actors": [{"name": "Player"}]}
            )

        self.assertFalse({"missing_actor_target", "actor_target_not_found"} & {item["code"] for item in facts})

    def test_missing_scene_actor_reference_is_reported(self):
        workspace = graph(nodes=[{
            "id": "start",
            "nodeType": "start",
            "workspace": {"blocks": {"blocks": [
                block("object_set_position", "move", {"NAME": "MissingActor"})
            ]}},
        }])
        catalog = {"object_set_position": {"outputCheck": "", "projectUsage": "project-safe"}}
        with mock.patch.object(NodeGraphReviewService, "_catalog_index", return_value=catalog):
            facts = NodeGraphReviewService._collect_local_facts(
                workspace, {"actors": [{"name": "Player"}]}
            )

        issue = next(item for item in facts if item["code"] == "actor_target_not_found")
        self.assertEqual("MissingActor", issue["actorName"])

    def test_connected_object_reference_is_resolved(self):
        reference = block(
            "object_reference",
            "reference",
            {"OBJECT": "Player", "MANUAL": ""},
        )
        workspace = graph(nodes=[{
            "id": "start",
            "nodeType": "start",
            "workspace": {"blocks": {"blocks": [
                block("object_set_position", "move", inputs={"NAME": {"block": reference}})
            ]}},
        }])
        catalog = {
            "object_set_position": {"outputCheck": "", "projectUsage": "project-safe"},
            "object_reference": {"outputCheck": "String", "projectUsage": "project-safe"},
        }
        with mock.patch.object(NodeGraphReviewService, "_catalog_index", return_value=catalog):
            facts = NodeGraphReviewService._collect_local_facts(
                workspace, {"actors": [{"name": "Player"}]}
            )

        self.assertFalse({"missing_actor_target", "actor_target_not_found"} & {item["code"] for item in facts})

    def test_tag_target_is_not_treated_as_actor_name(self):
        workspace = graph(nodes=[{
            "id": "start",
            "nodeType": "start",
            "workspace": {"blocks": {"blocks": [
                block("object_move_tag", "move_tag", {"TAG": "enemy"})
            ]}},
        }])
        catalog = {"object_move_tag": {"outputCheck": "", "projectUsage": "project-safe"}}
        with mock.patch.object(NodeGraphReviewService, "_catalog_index", return_value=catalog):
            facts = NodeGraphReviewService._collect_local_facts(
                workspace, {"actors": [{"name": "Player"}]}
            )

        self.assertFalse({"missing_actor_target", "actor_target_not_found"} & {item["code"] for item in facts})

    def test_prompt_rejects_gameplay_completeness_advice(self):
        prompt = NodeGraphReviewService._build_prompt(
            {"workspace": graph(), "projectContext": {}}, [], []
        )
        self.assertIn("不要评价游戏是否有趣", prompt)
        self.assertIn("缺少某种玩法功能不是错误", prompt)
        self.assertIn("证据不足或无法确定用户意图时必须返回无问题", prompt)
        self.assertIn("missing_actor_target", prompt)
        self.assertIn("actor_target_not_found", prompt)
        self.assertNotIn("胜利/失败条件能否由可见积木实际触发", prompt)

    def test_no_problem_result_clears_model_commentary(self):
        result = {
            "hasProblems": False,
            "summary": "还可以增加更多玩法",
            "issues": [{"code": "optional_feature"}],
        }
        NodeGraphReviewService._validate_model_result(
            result, {"workspace": graph()}
        )
        self.assertEqual("", result["summary"])
        self.assertEqual([], result["issues"])

    def test_problem_summary_is_limited_to_160_characters(self):
        workspace = graph(
            nodes=[
                {
                    "id": "start",
                    "nodeType": "start",
                    "workspace": {
                        "blocks": {"blocks": [block("node_when_enter", "enter")]}
                    },
                }
            ]
        )
        result = {
            "hasProblems": True,
            "summary": "错" * 200,
            "issues": [
                {
                    "nodeId": "start",
                    "blockId": "enter",
                    "code": "certain_problem",
                    "confidence": 0.95,
                }
            ],
        }
        NodeGraphReviewService._validate_model_result(
            result, {"workspace": workspace}
        )
        self.assertEqual(160, len(result["summary"]))
        self.assertEqual(1, len(result["issues"]))

    def test_low_confidence_problem_does_not_create_a_task(self):
        result = {
            "hasProblems": True,
            "summary": "也许可以增加更多玩法",
            "issues": [{"code": "speculative", "confidence": 0.4}],
        }
        NodeGraphReviewService._validate_model_result(
            result, {"workspace": graph()}
        )
        self.assertFalse(result["hasProblems"])
        self.assertEqual("", result["summary"])
        self.assertEqual([], result["issues"])

    def test_review_never_logs_or_returns_api_key(self):
        service = NodeGraphReviewService()
        payload = {
            "graphRevision": "abc123",
            "workspace": graph(),
        }
        settings = DeepSeekSettings(
            "super-secret-key",
            "https://api.deepseek.com",
            "deepseek-v4-flash",
            "test",
        )
        with mock.patch.object(service, "_resolve_settings", return_value=settings), mock.patch.object(
            service,
            "_call_deepseek",
            return_value='{"hasProblems":false,"summary":"","issues":[]}',
        ), self.assertLogs(MODULE.logger, level="INFO") as logs:
            result = service.review(payload)
        combined = "\n".join(logs.output) + json.dumps(result)
        self.assertNotIn("super-secret-key", combined)

    def test_background_start_returns_task_and_completes(self):
        service = NodeGraphReviewService()
        payload = {"graphRevision": "background-revision", "workspace": graph()}
        completed = {
            "success": True,
            "status": "ok",
            "hasProblems": False,
            "summary": "",
            "issues": [],
            "graphRevision": "background-revision",
        }
        try:
            with mock.patch.object(service, "review", return_value=completed):
                started = service.start(payload)
                self.assertTrue(started["success"])
                self.assertEqual("pending", started["status"])
                self.assertTrue(started["taskId"].startswith("node_review_"))

                deadline = time.time() + 2.0
                status = service.status(started["taskId"])
                while status.get("status") != "completed" and time.time() < deadline:
                    time.sleep(0.01)
                    status = service.status(started["taskId"])

                self.assertEqual("completed", status["status"])
                self.assertEqual(completed, status["result"])
        finally:
            service.shutdown()

    def test_background_review_reuses_successful_revision_cache(self):
        service = NodeGraphReviewService()
        payload = {"graphRevision": "cached-revision", "workspace": graph()}
        completed = {
            "success": True,
            "status": "ok",
            "hasProblems": False,
            "summary": "",
            "issues": [],
            "graphRevision": "cached-revision",
        }
        try:
            with mock.patch.object(service, "review", return_value=completed) as review:
                first = service.start(payload)
                deadline = time.time() + 2.0
                first_status = service.status(first["taskId"])
                while first_status.get("status") != "completed" and time.time() < deadline:
                    time.sleep(0.01)
                    first_status = service.status(first["taskId"])
                self.assertEqual("completed", first_status["status"])

                second = service.start(payload)
                self.assertEqual("completed", second["status"])
                second_status = service.status(second["taskId"])
                self.assertEqual("completed", second_status["status"])
                self.assertEqual(completed, second_status["result"])
                self.assertEqual(1, review.call_count)
        finally:
            service.shutdown()

    def test_issue_normalization_builds_task_fields(self):
        workspace = graph(
            nodes=[
                {
                    "id": "play",
                    "nodeType": "custom",
                    "workspace": {
                        "blocks": {"blocks": [block("ui_add_score", "add_score")]}
                    },
                }
            ]
        )
        request = {"workspace": workspace}
        result = {
            "hasProblems": True,
            "summary": "计分逻辑有问题；连接正确的加分积木就好了。",
            "issues": [
                {
                    "severity": "warning",
                    "confidence": 0.9,
                    "nodeId": "play",
                    "blockId": "add_score",
                    "code": "wrong_score_update",
                    "title": "修正计分逻辑",
                    "message": "当前积木没有更新胜利条件读取的分数。",
                    "suggestion": "把命中分支连接到正确的加分积木。",
                }
            ],
        }

        NodeGraphReviewService._validate_model_result(result, request)

        self.assertEqual(1, len(result["issues"]))
        issue = result["issues"][0]
        self.assertEqual("wrong_score_update|play|add_score", issue["issueKey"])
        self.assertEqual("修正计分逻辑", issue["title"])
        self.assertEqual("当前积木没有更新胜利条件读取的分数。", issue["message"])
        self.assertEqual("把命中分支连接到正确的加分积木。", issue["suggestion"])


if __name__ == "__main__":
    unittest.main()
