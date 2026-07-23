"""Stable, non-executable frontend business protocol for the black-box phase.

This module deliberately sits beside Runtime and collaboration.  It maps a
frontend-shaped command into a deterministic progress event, but does not
import CEF, Engine, SceneTools, or any Runtime write surface.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Any, Literal, Mapping

from .integration_contracts import BlockedResult, MissingRequirement
from .schema_versions import FRONTEND_INTERACTION_SCHEMA_VERSION


COMMAND_TYPES = frozenset({"start_project", "confirm_action", "query_status", "start_preview"})
COMMAND_EVENT_TYPES = {
    "start_project": "project_start_requested",
    "confirm_action": "action_confirmed",
    "query_status": "status_requested",
    "start_preview": "preview_start_requested",
}
_STABLE_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")


def _stable_id(value: object, field_name: str, *, required: bool = True) -> str:
    text = str(value or "").strip()
    if not text and not required:
        return ""
    if not _STABLE_ID.fullmatch(text):
        raise ValueError(f"{field_name} must be a stable identifier")
    return text


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class UserCommand:
    schema_version: str
    command_id: str
    room_id: str
    command_type: Literal["start_project", "confirm_action", "query_status", "start_preview"]
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.schema_version != FRONTEND_INTERACTION_SCHEMA_VERSION:
            raise ValueError("UserCommand schema_version is incompatible")
        object.__setattr__(self, "command_id", _stable_id(self.command_id, "command_id"))
        object.__setattr__(self, "room_id", _stable_id(self.room_id, "room_id"))
        command_type = str(self.command_type or "").strip()
        if command_type not in COMMAND_TYPES:
            raise ValueError("UserCommand command_type is unsupported")
        object.__setattr__(self, "command_type", command_type)
        object.__setattr__(self, "payload", _mapping(self.payload, "payload"))


@dataclass(frozen=True)
class ProgressEvent:
    schema_version: str
    event_id: str
    command_id: str
    room_id: str
    project_id: str
    task_id: str
    plan_id: str
    scene_version: int
    event_type: str
    status: str
    detail: Mapping[str, Any] | None
    origin_message_id: str = ""
    origin_correlation_id: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != FRONTEND_INTERACTION_SCHEMA_VERSION:
            raise ValueError("ProgressEvent schema_version is incompatible")
        for field_name in ("event_id", "command_id", "room_id"):
            object.__setattr__(self, field_name, _stable_id(getattr(self, field_name), field_name))
        for field_name in ("project_id", "task_id", "plan_id"):
            object.__setattr__(
                self,
                field_name,
                _stable_id(getattr(self, field_name), field_name, required=False),
            )
        if isinstance(self.scene_version, bool) or not isinstance(self.scene_version, int) or self.scene_version < 0:
            raise ValueError("scene_version must be a non-negative integer")
        object.__setattr__(self, "event_type", _stable_id(self.event_type, "event_type"))
        status = str(self.status or "").strip()
        if not status:
            raise ValueError("status is required")
        object.__setattr__(self, "status", status)
        for field_name in ("origin_message_id", "origin_correlation_id"):
            value = str(getattr(self, field_name) or "").strip()
            if len(value) > 256:
                raise ValueError(f"{field_name} is too long")
            object.__setattr__(self, field_name, value)
        if self.detail is not None:
            object.__setattr__(self, "detail", _mapping(self.detail, "detail"))


@dataclass(frozen=True)
class FrontendDispatchResult:
    status: Literal["accepted", "blocked"]
    events: tuple[ProgressEvent, ...]
    blocked_result: BlockedResult | None = None

    def __post_init__(self) -> None:
        events = tuple(self.events)
        if not all(isinstance(event, ProgressEvent) for event in events):
            raise TypeError("events must contain ProgressEvent values")
        object.__setattr__(self, "events", events)
        if self.status == "accepted":
            if not events or self.blocked_result is not None:
                raise ValueError("accepted result requires events and no blocker")
        elif self.status == "blocked":
            if events or not isinstance(self.blocked_result, BlockedResult):
                raise ValueError("blocked result requires one BlockedResult and no events")
        else:
            raise ValueError("unsupported dispatch status")


class FrontendBusinessProtocolAdapter:
    """Map command fixtures to progress events with process-local replay protection."""

    def __init__(self) -> None:
        self._seen_command_ids: set[str] = set()
        self._seen_event_ids: set[str] = set()

    def dispatch(self, raw_command: UserCommand | Mapping[str, Any]) -> FrontendDispatchResult:
        command = self._parse_command(raw_command)
        if isinstance(command, BlockedResult):
            return FrontendDispatchResult(status="blocked", events=(), blocked_result=command)
        if command.command_id in self._seen_command_ids:
            return FrontendDispatchResult(
                status="blocked",
                events=(),
                blocked_result=self._blocked(
                    error_code="duplicate_command_id",
                    summary="Frontend command replay was rejected.",
                    requirement_id="frontend.command_id_unique",
                    next_action="Use the original command result or submit a new command_id.",
                ),
            )
        event = self._event_from_command(command)
        self._seen_command_ids.add(command.command_id)
        self._seen_event_ids.add(event.event_id)
        return FrontendDispatchResult(status="accepted", events=(event,))

    def forward_event(self, raw_event: ProgressEvent | Mapping[str, Any]) -> ProgressEvent | BlockedResult:
        event = self._parse_event(raw_event)
        if isinstance(event, BlockedResult):
            return event
        if event.event_id in self._seen_event_ids:
            return self._blocked(
                error_code="duplicate_event_id",
                summary="Frontend progress event replay was rejected.",
                requirement_id="frontend.event_id_unique",
                next_action="Ignore the replayed event_id and wait for a new event.",
            )
        self._seen_event_ids.add(event.event_id)
        return event

    def _parse_command(self, raw_command: UserCommand | Mapping[str, Any]) -> UserCommand | BlockedResult:
        if isinstance(raw_command, UserCommand):
            return raw_command
        if not isinstance(raw_command, Mapping):
            return self._blocked(
                error_code="invalid_user_command",
                summary="Frontend command is not a mapping.",
                requirement_id="frontend.command_mapping",
                next_action="Send a structured UserCommand payload.",
            )
        schema_version = str(raw_command.get("schema_version") or "")
        if schema_version != FRONTEND_INTERACTION_SCHEMA_VERSION:
            return self._blocked(
                error_code="frontend_schema_version_incompatible",
                summary="Frontend command schema version is incompatible.",
                requirement_id="frontend.schema_version",
                next_action="Upgrade the frontend command schema and retry.",
            )
        command_type = str(raw_command.get("command_type") or "").strip()
        if command_type not in COMMAND_TYPES:
            return self._blocked(
                error_code="unknown_command_type",
                summary="Frontend command type is not supported.",
                requirement_id="frontend.command_type",
                next_action="Use start_project, confirm_action, query_status, or start_preview.",
            )
        try:
            return UserCommand(
                schema_version=schema_version,
                command_id=raw_command.get("command_id", ""),
                room_id=raw_command.get("room_id", ""),
                command_type=command_type,
                payload=raw_command.get("payload", {}),
            )
        except (TypeError, ValueError):
            return self._blocked(
                error_code="invalid_user_command",
                summary="Frontend command fields are invalid.",
                requirement_id="frontend.command_fields",
                next_action="Provide stable command_id, room_id, and mapping payload fields.",
            )

    def _parse_event(self, raw_event: ProgressEvent | Mapping[str, Any]) -> ProgressEvent | BlockedResult:
        if isinstance(raw_event, ProgressEvent):
            return raw_event
        if not isinstance(raw_event, Mapping):
            return self._blocked(
                error_code="invalid_progress_event",
                summary="Frontend progress event is not a mapping.",
                requirement_id="frontend.event_mapping",
                next_action="Send a structured ProgressEvent payload.",
            )
        schema_version = str(raw_event.get("schema_version") or "")
        if schema_version != FRONTEND_INTERACTION_SCHEMA_VERSION:
            return self._blocked(
                error_code="frontend_schema_version_incompatible",
                summary="Frontend progress event schema version is incompatible.",
                requirement_id="frontend.schema_version",
                next_action="Upgrade the frontend event schema and retry.",
            )
        try:
            return ProgressEvent(
                schema_version=schema_version,
                event_id=raw_event.get("event_id", ""),
                command_id=raw_event.get("command_id", ""),
                room_id=raw_event.get("room_id", ""),
                project_id=raw_event.get("project_id", ""),
                task_id=raw_event.get("task_id", ""),
                plan_id=raw_event.get("plan_id", ""),
                scene_version=raw_event.get("scene_version", 0),
                event_type=raw_event.get("event_type", ""),
                status=raw_event.get("status", ""),
                detail=raw_event.get("detail"),
                origin_message_id=raw_event.get("origin_message_id", ""),
                origin_correlation_id=raw_event.get("origin_correlation_id", ""),
            )
        except (TypeError, ValueError):
            return self._blocked(
                error_code="invalid_progress_event",
                summary="Frontend progress event fields are invalid.",
                requirement_id="frontend.event_fields",
                next_action="Provide stable event and command identifiers with a valid detail mapping.",
            )

    @staticmethod
    def _event_from_command(command: UserCommand) -> ProgressEvent:
        payload = command.payload
        event_type = COMMAND_EVENT_TYPES[command.command_type]
        return ProgressEvent(
            schema_version=FRONTEND_INTERACTION_SCHEMA_VERSION,
            event_id=f"event.{command.command_id}.{event_type}",
            command_id=command.command_id,
            room_id=command.room_id,
            project_id=str(payload.get("project_id") or "").strip(),
            task_id=str(payload.get("task_id") or "").strip(),
            plan_id=str(payload.get("plan_id") or "").strip(),
            scene_version=int(payload.get("scene_version") or 0),
            event_type=event_type,
            status="accepted",
            detail={"command_type": command.command_type},
            origin_message_id=str(payload.get("origin_message_id") or "").strip(),
            origin_correlation_id=str(payload.get("origin_correlation_id") or "").strip(),
        )

    @staticmethod
    def _blocked(
        *,
        error_code: str,
        summary: str,
        requirement_id: str,
        next_action: str,
    ) -> BlockedResult:
        return BlockedResult(
            node_id="frontend_business_protocol",
            status="blocked",
            error_code=error_code,
            summary=summary,
            missing_requirements=(
                MissingRequirement(
                    requirement_id=requirement_id,
                    owner_domain="frontend",
                    description=summary,
                ),
            ),
            owner_domain="frontend",
            retryable=False,
            next_action=next_action,
            evidence_refs=("adapter:frontend_business_protocol",),
        )


__all__ = [
    "COMMAND_TYPES",
    "FrontendBusinessProtocolAdapter",
    "FrontendDispatchResult",
    "ProgressEvent",
    "UserCommand",
]
