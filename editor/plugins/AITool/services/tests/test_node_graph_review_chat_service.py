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
        request = NodeGraphReviewChatService._normalize_payload(self.payload({
            "score": 50,
            "updatedAt": 1,
        }))
        prompt = NodeGraphReviewChatService._build_messages(request)[0]["content"]
        self.assertIn("干净的中文纯文本", prompt)
        self.assertIn("不要使用 Markdown 标题", prompt)
        self.assertIn("只使用‘1. 2. 3.’编号", prompt)


if __name__ == "__main__":
    unittest.main()
