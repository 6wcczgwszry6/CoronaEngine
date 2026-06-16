from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from .lanchat_agent_orchestrator import LanChatAgentOrchestrator


class LANChatAgentWorker:
    """Poll C++ LANChat agent triggers and return replies through C++."""

    def __init__(
        self,
        corona_engine: Any = None,
        agent_factory: Callable[[], Any] | None = None,
        sleep_seconds: float = 0.1,
    ) -> None:
        self._corona_engine = corona_engine
        self._agent_factory = agent_factory
        self._sleep_seconds = sleep_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._orchestrator: LanChatAgentOrchestrator | None = None
        self._logger = logging.getLogger(__name__)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        if not self._has_engine_api():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="LANChatAgentWorker",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 1.0) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def process_once(self) -> bool:
        if not self._has_engine_api():
            return False

        try:
            trigger = self._corona_engine.network_pop_lanchat_agent_trigger()
        except Exception as exc:
            self._logger.debug("Failed to poll LANChat agent trigger: %s", exc)
            return False

        if not trigger:
            return False

        try:
            result = self._run_agent(trigger)
        except Exception as exc:
            self._logger.debug("LANChat AI agent failed: %s", exc)
            agent_id = str(trigger.get("agent_id") or "agent")
            agent_name = str(trigger.get("agent_name") or "Agent")
            reply = f"AI agent failed: {exc}"
        else:
            agent_id = result.sender_id
            agent_name = result.sender_name
            reply = result.text

        try:
            self._broadcast_confirmed_action(getattr(result, "action_payload", None))
            return bool(
                self._corona_engine.network_send_agent_reply(
                    agent_id,
                    agent_name,
                    str(reply or ""),
                )
            )
        except Exception as exc:
            self._logger.debug("Failed to send LANChat agent reply: %s", exc)
            return False

    def _run(self) -> None:
        while not self._stop_event.is_set():
            processed = self.process_once()
            if not processed:
                self._stop_event.wait(self._sleep_seconds)

    def _has_engine_api(self) -> bool:
        return (
            self._corona_engine is not None
            and hasattr(self._corona_engine, "network_pop_lanchat_agent_trigger")
            and hasattr(self._corona_engine, "network_send_agent_reply")
        )

    def _get_orchestrator(self) -> LanChatAgentOrchestrator:
        if self._orchestrator is None:
            self._orchestrator = LanChatAgentOrchestrator(
                agent_factory=self._agent_factory or self._default_agent_factory,
            )
        return self._orchestrator

    def _run_agent(self, trigger: dict[str, Any]):
        return self._get_orchestrator().handle_trigger(trigger)

    def _broadcast_confirmed_action(self, payload: dict[str, Any] | None) -> None:
        if not payload or payload.get("status") != "confirmed":
            return
        if not hasattr(self._corona_engine, "network_broadcast_intent"):
            return
        source_user_id = str(payload.get("source_user_id") or "unknown")
        tooltip = str(payload.get("intent_text") or payload.get("proposal_id") or "")
        try:
            self._corona_engine.network_broadcast_intent(
                source_user_id,
                tooltip,
                [0.0, 0.0, 0.0],
                "confirmed_gm_action",
            )
        except Exception as exc:
            self._logger.debug("Failed to broadcast confirmed GM action: %s", exc)

    @staticmethod
    def _messages_from_trigger(trigger: dict[str, Any]) -> list[str]:
        messages: list[str] = []
        history = trigger.get("history") or []
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                sender = str(item.get("from") or item.get("sender_name") or "")
                text = str(item.get("text") or "")
                if text:
                    messages.append(f"{sender}: {text}" if sender else text)

        text = str(trigger.get("text") or "")
        if text and text not in messages:
            messages.append(text)
        return messages

    @staticmethod
    def _default_agent_factory() -> Any:
        from plugins.AITool.cai_extensions.agent.agent_adapter import create_master_agent

        return create_master_agent()
