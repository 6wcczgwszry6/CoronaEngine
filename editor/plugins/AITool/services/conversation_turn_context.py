from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, replace
from typing import Callable, Literal


ConversationPhase = Literal[
    "discussion",
    "drafting",
    "proposal_ready",
    "frozen",
    "generating",
    "completed",
    "blocked",
]


@dataclass(frozen=True)
class ConversationTurnContext:
    room_id: str
    phase: ConversationPhase = "discussion"
    accumulated_goal: str = ""
    goal_history: tuple[str, ...] = ()
    latest_instruction: str = ""
    target_agent_id: str = ""
    target_agent_name: str = ""
    active_agent_plan_id: str = ""
    artifact_ref: str = ""
    proposal_version: int = 0
    proposal_hash: str = ""
    artifact_refs: tuple[str, ...] = ()
    source_message_ids: tuple[str, ...] = ()
    updated_at: float = 0.0


class ConversationTurnContextStore:
    """Deterministic room context for short follow-up instructions."""

    _MENTION = re.compile(r"^\s*@[^\s]+\s*")
    _INSTRUCTION_ONLY = re.compile(
        r"^(?:请(?:你)?|麻烦|帮我|给我)?(?:先|再|现在)?"
        r"(?:给出|提供|制定|整理|展开|说明|说说|讨论|确认|开始|继续|执行|生成)"
        r"(?:一个|一下|当前|这个)?(?:方案|计划|设计|内容|生成)?(?:吧|呢|一下)?[。！？!?]*$"
    )
    _REPLACE_GOAL_MARKERS = ("改成", "换成", "切换为", "不要之前", "新目标")
    _REFINE_GOAL_MARKERS = ("按照", "基于", "继续", "在此基础", "来设计", "调整为")
    _SCENE_TARGET_TERMS = (
        "卧室",
        "房间",
        "客厅",
        "厨房",
        "营地",
        "森林",
        "室内",
        "户外",
        "乐园",
        "集市",
        "藏宝室",
        "关卡",
        "场景",
    )

    def __init__(self, *, clock: Callable[[], float] = time.time, max_rooms: int = 256) -> None:
        self._clock = clock
        self._max_rooms = max(16, int(max_rooms))
        self._lock = threading.RLock()
        self._contexts: dict[str, ConversationTurnContext] = {}

    @classmethod
    def normalized_instruction(cls, text: str) -> str:
        return cls._MENTION.sub("", str(text or "").strip()).strip()

    @classmethod
    def is_instruction_only(cls, text: str) -> bool:
        normalized = cls.normalized_instruction(text)
        return bool(normalized and cls._INSTRUCTION_ONLY.fullmatch(normalized))

    def record_turn(
        self,
        *,
        room_id: str,
        message_id: str,
        text: str,
        target_agent_id: str = "",
        target_agent_name: str = "",
        intent: str = "discussion",
    ) -> ConversationTurnContext:
        room_key = str(room_id or "default")
        message_key = str(message_id or "").strip()
        instruction = self.normalized_instruction(text)
        with self._lock:
            current = self._contexts.get(room_key) or ConversationTurnContext(room_id=room_key)
            if message_key and message_key in current.source_message_ids:
                return current
            accumulated_goal = current.accumulated_goal
            goal_history = list(current.goal_history)
            if instruction and not self.is_instruction_only(instruction):
                if (
                    not accumulated_goal
                    or any(marker in instruction for marker in self._REPLACE_GOAL_MARKERS)
                    or any(term in instruction for term in self._SCENE_TARGET_TERMS)
                ):
                    accumulated_goal = instruction
                elif any(marker in instruction for marker in self._REFINE_GOAL_MARKERS):
                    accumulated_goal = f"{accumulated_goal}；{instruction}"
                else:
                    accumulated_goal = instruction
                if instruction not in goal_history:
                    goal_history.append(instruction)
            source_ids = list(current.source_message_ids)
            if message_key:
                source_ids.append(message_key)
            updated = replace(
                current,
                phase=self._phase_for_intent(current.phase, intent),
                accumulated_goal=accumulated_goal,
                goal_history=tuple(goal_history[-16:]),
                latest_instruction=instruction,
                target_agent_id=str(target_agent_id or current.target_agent_id).strip(),
                target_agent_name=str(target_agent_name or current.target_agent_name).strip(),
                source_message_ids=tuple(source_ids[-64:]),
                updated_at=float(self._clock()),
            )
            self._contexts[room_key] = updated
            self._trim()
            return updated

    def effective_planning_text(self, room_id: str, latest_instruction: str) -> str:
        instruction = self.normalized_instruction(latest_instruction)
        with self._lock:
            current = self._contexts.get(str(room_id or "default"))
            if current and self.is_instruction_only(instruction) and current.accumulated_goal:
                return current.accumulated_goal
        return instruction

    def bind_plan(
        self,
        *,
        room_id: str,
        target_agent_id: str,
        target_agent_name: str,
        agent_plan_id: str,
        artifact_ref: str,
        proposal_version: int = 1,
        proposal_hash: str = "",
        artifact_refs: tuple[str, ...] = (),
    ) -> ConversationTurnContext:
        if not str(agent_plan_id or "").strip() or not str(artifact_ref or "").strip():
            raise ValueError("agent_plan_id and artifact_ref are required")
        room_key = str(room_id or "default")
        with self._lock:
            current = self._contexts.get(room_key) or ConversationTurnContext(room_id=room_key)
            updated = replace(
                current,
                target_agent_id=str(target_agent_id or current.target_agent_id).strip(),
                target_agent_name=str(target_agent_name or current.target_agent_name).strip(),
                active_agent_plan_id=str(agent_plan_id).strip(),
                artifact_ref=str(artifact_ref).strip(),
                proposal_version=max(1, int(proposal_version or 1)),
                proposal_hash=str(proposal_hash or "").strip(),
                artifact_refs=tuple(str(value).strip() for value in artifact_refs if str(value).strip()),
                phase="proposal_ready",
                updated_at=float(self._clock()),
            )
            self._contexts[room_key] = updated
            self._trim()
            return updated

    def get(self, room_id: str) -> ConversationTurnContext:
        with self._lock:
            return self._contexts.get(str(room_id or "default")) or ConversationTurnContext(
                room_id=str(room_id or "default")
            )

    def transition(
        self,
        room_id: str,
        phase: ConversationPhase,
    ) -> ConversationTurnContext:
        if phase not in {
            "discussion",
            "drafting",
            "proposal_ready",
            "frozen",
            "generating",
            "completed",
            "blocked",
        }:
            raise ValueError(f"unsupported conversation phase: {phase}")
        room_key = str(room_id or "default")
        with self._lock:
            current = self._contexts.get(room_key) or ConversationTurnContext(room_id=room_key)
            updated = replace(current, phase=phase, updated_at=float(self._clock()))
            self._contexts[room_key] = updated
            self._trim()
            return updated

    def invalidate_plan(self, room_id: str) -> ConversationTurnContext:
        room_key = str(room_id or "default")
        with self._lock:
            current = self._contexts.get(room_key) or ConversationTurnContext(room_id=room_key)
            updated = replace(
                current,
                active_agent_plan_id="",
                artifact_ref="",
                proposal_version=0,
                proposal_hash="",
                artifact_refs=(),
                phase="blocked",
                updated_at=float(self._clock()),
            )
            self._contexts[room_key] = updated
            self._trim()
            return updated

    @staticmethod
    def _phase_for_intent(current: ConversationPhase, intent: str) -> ConversationPhase:
        normalized = str(intent or "discussion").strip().lower()
        if normalized in {"plan_drafting", "plan_revision"}:
            return "drafting"
        if normalized == "discussion" and current in {"discussion", "drafting"}:
            return "discussion"
        return current

    def _trim(self) -> None:
        if len(self._contexts) <= self._max_rooms:
            return
        oldest = sorted(self._contexts, key=lambda key: self._contexts[key].updated_at)
        for key in oldest[: len(self._contexts) - self._max_rooms]:
            self._contexts.pop(key, None)


__all__ = ["ConversationPhase", "ConversationTurnContext", "ConversationTurnContextStore"]
