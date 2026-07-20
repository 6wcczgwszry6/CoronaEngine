from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal


RuntimeRoute = Literal["runtime_read", "runtime_write", "planning", "agent_chat"]
RuntimeOperation = Literal[
    "entity_status",
    "add",
    "modify",
    "delete",
    "layout",
    "generation_start",
    "none",
]
RuntimeModality = Literal["factual_query", "command", "request_command", "discussion"]


@dataclass(frozen=True)
class EntityIntent:
    raw_name: str
    canonical_name: str
    quantity: int = 1
    source_span: tuple[int, int] = (0, 0)
    confidence: float = 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "raw_name": self.raw_name,
            "canonical_name": self.canonical_name,
            "quantity": self.quantity,
            "source_span": list(self.source_span),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class RuntimeActionIntent:
    message_id: str
    room_id: str
    route: RuntimeRoute
    operation: RuntimeOperation
    modality: RuntimeModality
    confidence: float
    target_plan_id: str = ""
    entities: list[EntityIntent] = field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    requires_confirmation: bool = False
    clarification: str = ""
    reason: str = ""

    @property
    def is_runtime_owned(self) -> bool:
        return self.route in {"runtime_read", "runtime_write"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "room_id": self.room_id,
            "route": self.route,
            "operation": self.operation,
            "modality": self.modality,
            "confidence": self.confidence,
            "target_plan_id": self.target_plan_id,
            "entities": [item.as_dict() for item in self.entities],
            "risk_level": self.risk_level,
            "requires_confirmation": self.requires_confirmation,
            "clarification": self.clarification,
            "reason": self.reason,
        }


class EntityNameValidator:
    """Reject grammar fragments before they can become resource requests."""

    _INVALID_NAMES = {
        "吗",
        "了吗",
        "已经",
        "是否",
        "有没有",
        "完成了吗",
        "生成了吗",
        "加入了吗",
    }
    _QUESTION_SUFFIX = re.compile(
        r"(?:已经)?(?:加入|添加|生成|导入|完成)?(?:了)?(?:吗|没有|了没|完成了吗)[？?。！!]*$"
    )
    _ACTION_PREFIX = re.compile(
        r"^(?:请|麻烦|帮我|给我)?(?:再|重新)?(?:加入|添加|增加|新增|生成|导入|放入|创建)"
        r"(?:到场景(?:里|中)?)?(?:一个|一只|一座|一张|一件|一组|1个)?\s*"
    )
    _LEADING_QUANTITY = re.compile(r"^(?:一个|一只|一座|一张|一件|一组|1个)\s*")
    _COMMAND_FRAGMENT = re.compile(
        r"^(?:请(?:你)?|麻烦|帮我|给我)?(?:先|再|现在)?"
        r"(?:给出|提供|制定|整理|展开|说明|说说|讨论|确认|开始|继续|执行|生成|完成)"
        r"(?:一个|一下|当前|这个)?(?:方案|计划|设计|内容|场景|生成)?(?:吧|呢|一下)?$"
    )
    _TYPO_ALIASES = {"切比特": "丘比特"}

    @classmethod
    def validate(cls, raw_name: str, *, source_text: str = "") -> tuple[str, str]:
        value = str(raw_name or "").strip(" \t\r\n，,。.!！?？:：'\"")
        value = cls._ACTION_PREFIX.sub("", value)
        value = cls._LEADING_QUANTITY.sub("", value)
        value = cls._QUESTION_SUFFIX.sub("", value).strip(" \t，,。.!！?？")
        if re.search(r"(?:已经|是否|有没有|有没)$", value):
            return "", "实体名称包含未完成的问句片段"
        if cls._COMMAND_FRAGMENT.fullmatch(value):
            return "", "实体名称包含用户指令而不是场景对象"
        if not value or value in cls._INVALID_NAMES:
            return "", "实体名称只包含语法片段"
        for typo, canonical in cls._TYPO_ALIASES.items():
            if typo in value:
                suggested = value.replace(typo, canonical)
                return "", f"名称可能有误，是否指“{suggested}”？"
        if any(fragment == value for fragment in cls._INVALID_NAMES):
            return "", "实体名称无效"
        return value, ""


class RuntimeActionIntentService:
    """Semantic-first runtime router with deterministic write guardrails."""

    _ENTITY_COMPLETION_QUERY = re.compile(
        r"(?P<entity>[^，,。！？?]{1,48}?)(?:(?:是否)?已经|是否|有没有|有没|现在)?"
        r"(?:生成|导入|加载)?(?:完成|做好)(?:了)?(?:吗|没有|了没)?[？?。！!]*$"
    )
    _ENTITY_QUERY = re.compile(
        r"(?P<entity>[^，,。！？?]{1,48}?)(?:(?:是否)?已经|是否|有没有|有没|现在)?"
        r"(?:加入|添加|生成|导入|完成|做好|进入场景)(?:了)?(?:吗|没有|了没|完成了吗)[？?。！!]*$"
    )
    _EXPLICIT_ADD = re.compile(
        r"(?:^|[，,；;。])\s*(?:请|麻烦|帮我|给我)?(?:再|重新)?"
        r"(?:加入|添加|增加|新增|生成|导入|放入|创建)\s*"
        r"(?P<entity>[^，,；;。！？?]{1,64}?)"
        r"(?=(?:再|重新)?(?:加入|添加|增加|新增|生成|导入|放入|创建)|$)"
    )
    _QUESTION_MARKERS = ("吗", "是否", "有没有", "有没", "了没", "为什么", "哪里", "哪步")

    def __init__(self, llm_classifier: Callable[[str], dict[str, Any] | None] | None = None) -> None:
        self._llm_classifier = llm_classifier

    def classify(
        self,
        text: str,
        *,
        message_id: str = "",
        room_id: str = "default",
        target_plan_id: str = "",
        generation_active: bool = False,
        allow_llm: bool = True,
    ) -> RuntimeActionIntent:
        value = re.sub(r"^\s*@GM\s*", "", str(text or "").strip(), flags=re.IGNORECASE)
        query_match = self._ENTITY_COMPLETION_QUERY.search(value) or self._ENTITY_QUERY.search(value)
        if query_match:
            entity = self._entity(query_match.group("entity"), value, query_match.span("entity"))
            entities = [entity] if entity is not None else []
            return RuntimeActionIntent(
                message_id=message_id,
                room_id=room_id,
                route="runtime_read",
                operation="entity_status",
                modality="factual_query",
                confidence=0.99,
                target_plan_id=target_plan_id,
                entities=entities,
                reason="deterministic entity lifecycle query",
            )

        add_matches = list(self._EXPLICIT_ADD.finditer(value))
        if add_matches and not any(marker in value for marker in self._QUESTION_MARKERS):
            entities: list[EntityIntent] = []
            for add_match in add_matches:
                entity, clarification = self._entity_or_clarification(
                    add_match.group("entity"), value, add_match.span("entity")
                )
                if clarification:
                    return RuntimeActionIntent(
                        message_id=message_id,
                        room_id=room_id,
                        route="runtime_read",
                        operation="add",
                        modality="request_command",
                        confidence=0.45,
                        target_plan_id=target_plan_id,
                        requires_confirmation=True,
                        clarification=clarification,
                        reason="entity name requires clarification",
                    )
                if entity and entity.canonical_name not in {item.canonical_name for item in entities}:
                    entities.append(entity)
            return RuntimeActionIntent(
                message_id=message_id,
                room_id=room_id,
                route="runtime_write",
                operation="add",
                modality="command",
                confidence=0.96,
                target_plan_id=target_plan_id,
                entities=entities,
                risk_level="low",
                requires_confirmation=False,
                reason="explicit low-risk add command",
            )

        llm_result = self._classify_via_llm(value) if allow_llm else None
        if llm_result is not None:
            validated = self._from_llm(
                llm_result,
                value,
                message_id=message_id,
                room_id=room_id,
                target_plan_id=target_plan_id,
            )
            if validated is not None:
                return validated

        return RuntimeActionIntent(
            message_id=message_id,
            room_id=room_id,
            route="agent_chat",
            operation="none",
            modality="discussion",
            confidence=0.7,
            target_plan_id=target_plan_id,
            reason="no safe runtime action",
        )

    @classmethod
    def _entity(cls, raw: str, source: str, span: tuple[int, int]) -> EntityIntent | None:
        canonical, error = EntityNameValidator.validate(raw, source_text=source)
        if error:
            return None
        return EntityIntent(str(raw).strip(), canonical, 1, span, 0.98)

    @classmethod
    def _entity_or_clarification(
        cls, raw: str, source: str, span: tuple[int, int]
    ) -> tuple[EntityIntent | None, str]:
        canonical, error = EntityNameValidator.validate(raw, source_text=source)
        if error:
            return None, error
        return EntityIntent(str(raw).strip(), canonical, 1, span, 0.98), ""

    def _classify_via_llm(self, value: str) -> dict[str, Any] | None:
        classifier = self._llm_classifier or self._default_llm_classifier
        try:
            result = classifier(value)
        except Exception:  # noqa: BLE001
            return None
        return dict(result) if isinstance(result, dict) else None

    @staticmethod
    def _default_llm_classifier(value: str) -> dict[str, Any] | None:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from Quasar.ai_models.base_pool.registry import get_chat_model
        except Exception:
            return None
        system = (
            "你是3D场景Runtime的语义控制分类器。只输出JSON。"
            "字段必须包含route, operation, modality, confidence, entities, risk_level, requires_confirmation。"
            "route只能是runtime_read/runtime_write/planning/agent_chat；"
            "operation只能是entity_status/add/modify/delete/layout/generation_start/none；"
            "modality只能是factual_query/command/request_command/discussion。"
            "询问某物体是否已加入、是否完成必须是runtime_read+entity_status，绝不能写场景。"
            "只有语义明确的新增祈使请求才能是runtime_write+add。"
            "entities中的每项包含raw_name和canonical_name，不得包含吗、了吗、已经等语法片段。"
        )
        model = get_chat_model(temperature=0, request_timeout=12.0)
        response = model.invoke([
            SystemMessage(content=system),
            HumanMessage(content=str(value or "")[:800]),
        ])
        raw = response.content if hasattr(response, "content") else str(response)
        text = str(raw or "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
        data = json.loads(text)
        return data if isinstance(data, dict) else None

    def _from_llm(
        self,
        data: dict[str, Any],
        value: str,
        *,
        message_id: str,
        room_id: str,
        target_plan_id: str,
    ) -> RuntimeActionIntent | None:
        route = str(data.get("route") or "")
        operation = str(data.get("operation") or "")
        modality = str(data.get("modality") or "")
        if route not in {"runtime_read", "runtime_write", "planning", "agent_chat"}:
            return None
        if operation not in {"entity_status", "add", "modify", "delete", "layout", "generation_start", "none"}:
            return None
        if modality not in {"factual_query", "command", "request_command", "discussion"}:
            return None
        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        entities: list[EntityIntent] = []
        clarification = ""
        for row in list(data.get("entities") or []):
            if not isinstance(row, dict):
                continue
            raw = str(row.get("raw_name") or row.get("canonical_name") or "")
            entity, error = self._entity_or_clarification(raw, value, (0, 0))
            if error:
                clarification = error
                continue
            if entity and entity.canonical_name not in {item.canonical_name for item in entities}:
                entities.append(entity)
        if route == "runtime_write" and (
            modality == "factual_query" or confidence < 0.85 or not entities or clarification
        ):
            route = "runtime_read"
            if not clarification:
                clarification = "我还不能确定这是查询还是场景修改请求，请明确说明要查询状态，或明确说要新增/修改哪个物体。"
        risk_level = str(data.get("risk_level") or "low").strip().lower()
        if risk_level not in {"low", "medium", "high"}:
            risk_level = "medium"
        requires_confirmation = (
            bool(data.get("requires_confirmation"))
            or bool(clarification)
            or risk_level == "high"
            or operation == "delete"
        )
        return RuntimeActionIntent(
            message_id=message_id,
            room_id=room_id,
            route=route,  # type: ignore[arg-type]
            operation=operation,  # type: ignore[arg-type]
            modality=modality,  # type: ignore[arg-type]
            confidence=confidence,
            target_plan_id=target_plan_id,
            entities=entities,
            risk_level=risk_level,  # type: ignore[arg-type]
            requires_confirmation=requires_confirmation,
            clarification=clarification,
            reason=str(data.get("reason") or "llm semantic classification"),
        )


class MessageDispatchLedger:
    """Process-local atomic ownership for duplicate native/agent message ingress."""

    _TERMINAL = {"replied", "failed_terminal"}

    def __init__(self, max_entries: int = 4096) -> None:
        self._max_entries = max(64, int(max_entries))
        self._lock = threading.RLock()
        self._entries: dict[str, dict[str, Any]] = {}

    @staticmethod
    def key(room_id: str, message_id: str) -> str:
        return f"{str(room_id or 'default')}:{str(message_id or '').strip()}"

    def claim_execution(
        self,
        room_id: str,
        message_id: str,
        *,
        owner: str,
        route: str,
        target_agent_id: str = "",
        target_agent_name: str = "",
    ) -> bool:
        if not str(message_id or "").strip():
            return False
        key = self.key(room_id, message_id)
        with self._lock:
            if key in self._entries:
                return False
            self._entries[key] = {
                "state": "claimed",
                "owner": owner,
                "execution_owner": owner,
                "route": route,
                "target_agent_id": str(target_agent_id or "").strip(),
                "target_agent_name": str(target_agent_name or "").strip(),
                "reply_owner": "",
                "final_reply_sent": False,
                "updated_at": time.time(),
            }
            self._trim()
            return True

    def claim(self, room_id: str, message_id: str, *, owner: str, route: str) -> bool:
        """Compatibility claim for branches continuing an already-owned execution."""

        if not str(message_id or "").strip():
            return False
        key = self.key(room_id, message_id)
        with self._lock:
            current = self._entries.get(key)
            if current is None:
                return self.claim_execution(room_id, message_id, owner=owner, route=route)
            execution_owner = str(current.get("execution_owner") or current.get("owner") or "")
            return execution_owner == owner and str(current.get("state") or "") not in self._TERMINAL

    def claim_reply(
        self,
        room_id: str,
        message_id: str,
        *,
        owner: str,
        agent_id: str = "",
        agent_name: str = "",
        system_reply: bool = False,
    ) -> bool:
        if not str(message_id or "").strip():
            return False
        key = self.key(room_id, message_id)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or bool(entry.get("final_reply_sent")):
                return False
            if str(entry.get("state") or "") == "reply_claimed":
                return False
            expected_id = str(entry.get("target_agent_id") or "").strip()
            expected_name = str(entry.get("target_agent_name") or "").strip()
            actual_id = str(agent_id or "").strip()
            actual_name = str(agent_name or "").strip()
            if not system_reply and (expected_id or expected_name):
                id_matches = bool(expected_id and actual_id and expected_id == actual_id)
                name_matches = bool(expected_name and actual_name and expected_name == actual_name)
                if not id_matches and not name_matches:
                    entry["reply_rejection"] = "target_agent_mismatch"
                    entry["rejected_reply_owner"] = owner
                    entry["updated_at"] = time.time()
                    return False
            entry["state"] = "reply_claimed"
            entry["reply_owner"] = owner
            entry["updated_at"] = time.time()
            return True

    def complete_reply(
        self,
        room_id: str,
        message_id: str,
        *,
        owner: str,
        sent: bool,
        reply: str = "",
    ) -> None:
        if not str(message_id or "").strip():
            return
        key = self.key(room_id, message_id)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or str(entry.get("reply_owner") or "") != owner:
                return
            entry["updated_at"] = time.time()
            if sent:
                entry["state"] = "replied"
                entry["final_reply_sent"] = True
                if reply:
                    entry["reply"] = reply
            else:
                entry["state"] = "reply_failed"
                entry["last_reply_owner"] = owner
                entry["reply_owner"] = ""
            self._trim()

    def transition(self, room_id: str, message_id: str, state: str, *, reply: str = "") -> None:
        if not str(message_id or "").strip():
            return
        key = self.key(room_id, message_id)
        with self._lock:
            entry = self._entries.setdefault(key, {})
            if bool(entry.get("final_reply_sent")) and state != "replied":
                return
            entry["state"] = state
            entry["updated_at"] = time.time()
            if reply:
                entry["reply"] = reply
            self._trim()

    def entry(self, room_id: str, message_id: str) -> dict[str, Any]:
        with self._lock:
            return dict(self._entries.get(self.key(room_id, message_id)) or {})

    def _trim(self) -> None:
        if len(self._entries) <= self._max_entries:
            return
        oldest = sorted(self._entries, key=lambda key: float(self._entries[key].get("updated_at") or 0))
        for key in oldest[: len(self._entries) - self._max_entries]:
            self._entries.pop(key, None)


_SERVICE = RuntimeActionIntentService()


def get_runtime_action_intent_service() -> RuntimeActionIntentService:
    return _SERVICE


__all__ = [
    "EntityIntent",
    "EntityNameValidator",
    "MessageDispatchLedger",
    "RuntimeActionIntent",
    "RuntimeActionIntentService",
    "get_runtime_action_intent_service",
]
