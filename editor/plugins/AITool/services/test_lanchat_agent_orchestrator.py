from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from plugins.AITool.services.lanchat_agent_orchestrator import LanChatAgentOrchestrator  # noqa: E402
from plugins.AITool.services.lanchat_agent_worker import LANChatAgentWorker  # noqa: E402


def _agent_factory():
    def _agent(persona, messages):
        assert messages
        return f"agent-reply persona={persona or 'none'} messages={len(messages)}"

    return _agent


def _trigger(text="@小B 添加一个篝火", agent_name="小B"):
    return {
        "trigger_id": "m1:a1",
        "message_id": "m1",
        "room_id": "r1",
        "sender_id": "user-a",
        "sender_name": "用户A",
        "agent_id": "agent-b",
        "agent_name": agent_name,
        "persona": "山贼",
        "text": text,
        "history": [
            {"message_id": "m0", "from": "用户A", "text": "我们做一个营地"},
            {"message_id": "m1", "from": "用户A", "text": text},
        ],
    }


class FakeEngine:
    def __init__(self, triggers):
        self.triggers = list(triggers)
        self.replies = []
        self.intents = []

    def network_pop_lanchat_agent_trigger(self):
        return self.triggers.pop(0) if self.triggers else None

    def network_send_agent_reply(self, agent_id, agent_name, text):
        self.replies.append((agent_id, agent_name, text))
        return True

    def network_broadcast_intent(self, user_id, tooltip, preview_position, status):
        self.intents.append((user_id, tooltip, preview_position, status))
        return True


def test_regular_role_agent_reply():
    orch = LanChatAgentOrchestrator(agent_factory=_agent_factory)
    result = orch.handle_trigger(_trigger())
    assert result.sender_id == "agent-b"
    assert result.sender_name == "小B"
    assert "agent-reply" in result.text
    assert result.discussion_state.pending_intents
    print("[OK] regular role agent reply goes through orchestrator")


def test_gm_proposal_for_conflict():
    orch = LanChatAgentOrchestrator(agent_factory=_agent_factory)
    result = orch.handle_trigger(_trigger("@GM 用户A要移动桌子，但是用户B不同意", "GM"))
    assert result.sender_id == "gm-system"
    assert result.sender_name == "GM"
    assert result.proposal is True
    assert "GM 提案" in result.text
    assert "房主可回复" in result.text
    assert result.action_payload["source_user_id"] == "user-a"
    assert result.action_payload["intent_text"]
    assert result.action_payload["execution"] == "host_single_writer"
    print("[OK] conflict or GM mention produces GM proposal")


def test_host_confirmation_consumes_pending_proposal():
    orch = LanChatAgentOrchestrator(agent_factory=_agent_factory)
    proposal = orch.handle_trigger(_trigger("@GM 删除桌子", "GM"))
    assert proposal.proposal is True
    confirmed = orch.handle_trigger(_trigger("确认", "GM"))
    assert confirmed.proposal is False
    assert "已确认" in confirmed.text
    assert confirmed.action_payload["status"] == "confirmed"
    assert confirmed.action_payload["source_user_id"] == "user-a"
    print("[OK] host confirmation consumes pending GM proposal")


def test_worker_uses_orchestrator_and_sends_reply():
    engine = FakeEngine([_trigger()])
    worker = LANChatAgentWorker(corona_engine=engine, agent_factory=_agent_factory)
    assert worker.process_once() is True
    assert len(engine.replies) == 1
    assert engine.replies[0][0] == "agent-b"
    assert "agent-reply" in engine.replies[0][2]
    print("[OK] worker polls C++ trigger and replies through C++")


def test_worker_broadcasts_confirmed_gm_action():
    engine = FakeEngine([
        _trigger("@GM 删除桌子", "GM"),
        _trigger("确认", "GM"),
    ])
    worker = LANChatAgentWorker(corona_engine=engine, agent_factory=_agent_factory)
    assert worker.process_once() is True
    assert worker.process_once() is True
    assert len(engine.replies) == 2
    assert engine.intents, "confirmed GM action should be visible to C++ intent channel"
    assert engine.intents[-1][0] == "user-a"
    assert engine.intents[-1][3] == "confirmed_gm_action"
    print("[OK] worker broadcasts confirmed GM action payload")


if __name__ == "__main__":
    test_regular_role_agent_reply()
    test_gm_proposal_for_conflict()
    test_host_confirmation_consumes_pending_proposal()
    test_worker_uses_orchestrator_and_sends_reply()
    test_worker_broadcasts_confirmed_gm_action()
    print("\n=== LANChat agent orchestrator ALL PASS ===")
