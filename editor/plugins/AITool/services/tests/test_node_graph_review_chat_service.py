import pathlib
import sys
import unittest

EDITOR_ROOT = pathlib.Path(__file__).resolve().parents[4]
if str(EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(EDITOR_ROOT))

from plugins.AITool.services.node_graph_review_chat_service import NodeGraphReviewChatService


class NodeGraphReviewChatServiceTests(unittest.TestCase):
    def payload(self, profile):
        return {
            "messages": [{"role": "user", "content": "这个节点问题该怎么改？"}],
            "tasks": [],
            "graphExcerpt": {},
            "assistanceProfile": profile,
        }

    def test_normalizes_and_clamps_assistance_score(self):
        high = NodeGraphReviewChatService._normalize_payload(self.payload({
            "score": 125,
            "updatedAt": 1,
        }))
        low = NodeGraphReviewChatService._normalize_payload(self.payload({
            "score": -20,
            "updatedAt": 1,
        }))
        self.assertEqual({"score": 100, "updatedAt": 1}, high["assistanceProfile"])
        self.assertEqual({"score": 0, "updatedAt": 1}, low["assistanceProfile"])

    def test_high_score_chat_is_concise_and_professional(self):
        request = NodeGraphReviewChatService._normalize_payload(self.payload({
            "score": 85,
            "updatedAt": 1,
        }))
        prompt = NodeGraphReviewChatService._build_messages(request)[0]["content"]
        self.assertIn("回答简洁、专业", prompt)
        self.assertIn("状态机、控制流、数据流", prompt)
        self.assertIn("实时计算机图形学", prompt)
        self.assertIn("仅在直接相关时补充", prompt)

    def test_low_score_chat_is_calm_and_actionable(self):
        request = NodeGraphReviewChatService._normalize_payload(self.payload({
            "score": 25,
            "updatedAt": 1,
        }))
        prompt = NodeGraphReviewChatService._build_messages(request)[0]["content"]
        self.assertIn("平和、通俗", prompt)
        self.assertIn("减少术语", prompt)
        self.assertIn("点击、拖拽、连接或修改", prompt)
        self.assertIn("验证方法", prompt)

    def test_unscored_chat_uses_neutral_guidance_without_labels(self):
        request = NodeGraphReviewChatService._normalize_payload(self.payload({
            "score": 90,
            "updatedAt": 0,
        }))
        prompt = NodeGraphReviewChatService._build_messages(request)[0]["content"]
        self.assertIn("尚无稳定操作评分", prompt)
        self.assertIn("不要给用户贴美术、程序、入门、熟悉或熟练标签", prompt)

    def test_chat_requests_clean_plain_text_without_markdown_decoration(self):
        payload = self.payload({"score": 50, "updatedAt": 1})
        payload["messages"] = [{"role": "user", "content": "Please review the current issue."}]
        request = NodeGraphReviewChatService._normalize_payload(payload)
        prompt = NodeGraphReviewChatService._build_messages(request)[0]["content"]
        self.assertIn("干净的中文纯文本", prompt)
        self.assertIn("不要使用 Markdown 标题", prompt)
        self.assertIn("只使用‘1. 2. 3.’编号", prompt)


    def test_detail_request_for_object_reference_returns_safe_showcase(self):
        payload = self.payload({"score": 50, "updatedAt": 1})
        payload["messages"] = [{"role": "user", "content": "\u4e0d\u7406\u89e3\u600e\u4e48\u7ed9\u79fb\u52a8\u79ef\u6728\u6307\u5b9a\u5bf9\u8c61"}]
        request = NodeGraphReviewChatService._normalize_payload(payload)
        metadata = NodeGraphReviewChatService._guidance_metadata(request)
        self.assertTrue(request["detailGuidanceRequested"])
        self.assertTrue(metadata["needsShowcase"])
        self.assertEqual("connect_object_reference", metadata["guidanceIntent"])
        self.assertGreaterEqual(len(metadata["steps"]), 3)

    def test_selected_tutorial_task_maps_to_whitelisted_guidance(self):
        payload = self.payload({"score": 50, "updatedAt": 1})
        payload.update({
            "detailGuidanceRequested": True,
            "selectedTaskKey": "tutorial.adjust_physics",
            "tasks": [{
                "taskKey": "tutorial.adjust_physics",
                "type": "tutorial",
                "title": "adjust physics",
            }],
        })
        request = NodeGraphReviewChatService._normalize_payload(payload)
        metadata = NodeGraphReviewChatService._guidance_metadata(request)
        self.assertEqual("adjust_physics", metadata["guidanceIntent"])
        self.assertTrue(metadata["needsShowcase"])

    def test_explicit_physics_request_overrides_selected_transform_task(self):
        payload = self.payload({"score": 50, "updatedAt": 1})
        payload.update({
            "detailGuidanceRequested": True,
            "selectedTaskKey": "tutorial.transform_model",
            "tasks": [{
                "taskKey": "tutorial.transform_model",
                "type": "tutorial",
                "title": "adjust transform",
            }],
            "messages": [{"role": "user", "content": "\u5c55\u793a\u8c03\u6574\u7269\u4f53\u7269\u7406\u6027\u8d28"}],
        })
        request = NodeGraphReviewChatService._normalize_payload(payload)
        metadata = NodeGraphReviewChatService._guidance_metadata(request)
        self.assertEqual("adjust_physics", metadata["guidanceIntent"])
        self.assertTrue(metadata["needsShowcase"])
        self.assertTrue(any("\u7269\u7406" in step for step in metadata["steps"]))

    def test_unknown_detail_question_keeps_steps_without_showcase(self):
        payload = self.payload({"score": 50, "updatedAt": 1})
        payload["messages"] = [{"role": "user", "content": "\u6211\u4e0d\u7406\u89e3\u8fd9\u4e2a\u62bd\u8c61\u6982\u5ff5"}]
        request = NodeGraphReviewChatService._normalize_payload(payload)
        metadata = NodeGraphReviewChatService._guidance_metadata(request)
        self.assertFalse(metadata["needsShowcase"])
        self.assertEqual("", metadata["guidanceIntent"])
        self.assertGreaterEqual(len(metadata["steps"]), 3)

    def test_normal_question_does_not_add_steps_or_showcase(self):
        payload = self.payload({"score": 50, "updatedAt": 1})
        payload["messages"] = [{"role": "user", "content": "Please review the current issue."}]
        request = NodeGraphReviewChatService._normalize_payload(payload)
        metadata = NodeGraphReviewChatService._guidance_metadata(request)
        self.assertFalse(metadata["needsShowcase"])
        self.assertEqual([], metadata["steps"])


    def test_project_context_keeps_real_scene_actors(self):
        payload = self.payload({"score": 50, "updatedAt": 1})
        payload["projectContext"] = {
            "sceneName": "Scene/default.scene",
            "actorContextAvailable": True,
            "actors": [
                {
                    "name": "modern chair 11 obj",
                    "type": "model",
                    "tags": ["prop"],
                    "aliases": ["chair", "modern chair 11 obj"],
                    "ignored": "not forwarded",
                },
                {"name": "modern chair 11 obj", "type": "duplicate"},
            ],
            "ignored": {"project": "data"},
        }
        request = NodeGraphReviewChatService._normalize_payload(payload)
        self.assertEqual("Scene/default.scene", request["projectContext"]["sceneName"])
        self.assertTrue(request["projectContext"]["actorContextAvailable"])
        self.assertEqual(1, len(request["projectContext"]["actors"]))
        self.assertEqual("modern chair 11 obj", request["projectContext"]["actors"][0]["name"])
        self.assertNotIn("ignored", request["projectContext"]["actors"][0])

    def test_project_graph_prompt_forbids_fake_binding_workflow(self):
        payload = self.payload({"score": 50, "updatedAt": 1})
        payload["projectContext"] = {
            "sceneName": "Scene/default.scene",
            "actorContextAvailable": True,
            "actors": [{"name": "modern chair 11 obj", "type": "model"}],
        }
        request = NodeGraphReviewChatService._normalize_payload(payload)
        messages = NodeGraphReviewChatService._build_messages(request)
        prompt = messages[0]["content"]
        context = messages[1]["content"]
        self.assertIn("node_graph:project:global", prompt)
        self.assertIn("actorName", prompt)
        self.assertIn("projectContext.actors", prompt)
        self.assertIn("modern chair 11 obj", context)
        self.assertIn("Scene/default.scene", context)


if __name__ == "__main__":
    unittest.main()
