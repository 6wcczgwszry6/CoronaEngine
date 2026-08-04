"""Thread-safe project state with explicit, optimistic version transitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from threading import RLock
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .contracts import GameProjectState


PROJECT_STATE_MUTABLE_FIELDS = frozenset(
    {
        "active_task_graph_id",
        "active_scene_plan_id",
        "scene_world_version",
        "artifact_refs",
        "validation_status",
    }
)


class ProjectStateError(RuntimeError):
    """Base class for deterministic project-state failures."""


class ProjectNotFoundError(ProjectStateError):
    pass


class ProjectAlreadyExistsError(ProjectStateError):
    pass


class ProjectVersionConflictError(ProjectStateError):
    pass


class ProjectPatchConflictError(ProjectStateError):
    pass


class InvalidProjectStateTransitionError(ProjectStateError):
    pass


def _text(value: Any) -> str:
    return str(value or "").strip()


def _text_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{field_name} must be a sequence of strings")
    result: list[str] = []
    for item in value:
        text = _text(item)
        if not text:
            raise ValueError(f"{field_name} cannot contain empty values")
        result.append(text)
    return tuple(sorted(set(result)))


def _normalize_changes(changes: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(changes, Mapping):
        raise TypeError("ProjectStatePatch changes must be a mapping")
    unknown = sorted(set(changes) - PROJECT_STATE_MUTABLE_FIELDS)
    if unknown:
        raise ValueError(f"ProjectStatePatch contains immutable or unknown fields: {', '.join(unknown)}")
    normalized: dict[str, Any] = {}
    for key in sorted(changes):
        value = changes[key]
        if key in {"active_task_graph_id", "active_scene_plan_id", "validation_status"}:
            normalized[key] = _text(value)
        elif key == "scene_world_version":
            try:
                normalized[key] = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("scene_world_version must be an integer") from exc
        elif key == "artifact_refs":
            normalized[key] = _text_tuple(value, field_name="artifact_refs")
    return normalized


def _canonical_patch_payload(
    *,
    project_id: str,
    expected_project_version: int,
    source: str,
    changes: Mapping[str, Any],
) -> str:
    payload = {
        "project_id": project_id,
        "expected_project_version": expected_project_version,
        "source": source,
        "changes": {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in sorted(changes.items())
        },
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, init=False)
class ProjectStatePatch:
    patch_id: str
    project_id: str
    expected_project_version: int
    source: str
    changes: Mapping[str, Any]
    fingerprint: str

    def __init__(
        self,
        *,
        patch_id: str,
        project_id: str,
        expected_project_version: int,
        source: str,
        changes: Mapping[str, Any],
    ) -> None:
        normalized_patch_id = _text(patch_id)
        normalized_project_id = _text(project_id)
        normalized_source = _text(source)
        if not normalized_patch_id or not normalized_project_id or not normalized_source:
            raise ValueError("patch_id, project_id, and source are required")
        if int(expected_project_version) <= 0:
            raise ValueError("expected_project_version must be positive")
        normalized_changes = _normalize_changes(changes)
        canonical = _canonical_patch_payload(
            project_id=normalized_project_id,
            expected_project_version=int(expected_project_version),
            source=normalized_source,
            changes=normalized_changes,
        )
        values = {
            "patch_id": normalized_patch_id,
            "project_id": normalized_project_id,
            "expected_project_version": int(expected_project_version),
            "source": normalized_source,
            "changes": MappingProxyType(dict(normalized_changes)),
            "fingerprint": "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        }
        for key, value in values.items():
            object.__setattr__(self, key, value)


@dataclass(frozen=True)
class ProjectStateTransition:
    transition_id: str
    patch_id: str
    project_id: str
    from_version: int
    to_version: int
    source: str
    changed_fields: tuple[str, ...]
    before: GameProjectState | None
    after: GameProjectState

    def as_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "patch_id": self.patch_id,
            "project_id": self.project_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "source": self.source,
            "changed_fields": list(self.changed_fields),
            "before": self.before.as_dict() if self.before else None,
            "after": self.after.as_dict(),
        }


class ProjectStateStore:
    """In-memory project fact store, independent from RuntimeState."""

    def __init__(self) -> None:
        self._states: dict[str, GameProjectState] = {}
        self._history: dict[str, list[ProjectStateTransition]] = {}
        self._patch_results: dict[str, tuple[str, str, GameProjectState]] = {}
        self._lock = RLock()

    def create_project(
        self,
        *,
        project_id: str,
        room_id: str,
        source: str,
    ) -> GameProjectState:
        normalized_project_id = _text(project_id)
        normalized_room_id = _text(room_id)
        normalized_source = _text(source)
        if not normalized_project_id or not normalized_room_id or not normalized_source:
            raise ValueError("project_id, room_id, and source are required")
        with self._lock:
            if normalized_project_id in self._states:
                raise ProjectAlreadyExistsError(normalized_project_id)
            state = GameProjectState(
                project_id=normalized_project_id,
                project_version=1,
                room_id=normalized_room_id,
            )
            transition = ProjectStateTransition(
                transition_id=f"transition-create-{normalized_project_id}",
                patch_id="",
                project_id=normalized_project_id,
                from_version=0,
                to_version=1,
                source=normalized_source,
                changed_fields=("project_created",),
                before=None,
                after=state,
            )
            self._states[normalized_project_id] = state
            self._history[normalized_project_id] = [transition]
            return state

    def get(self, project_id: str) -> GameProjectState:
        normalized_project_id = _text(project_id)
        with self._lock:
            state = self._states.get(normalized_project_id)
            if state is None:
                raise ProjectNotFoundError(normalized_project_id)
            return state

    def history(self, project_id: str) -> tuple[ProjectStateTransition, ...]:
        normalized_project_id = _text(project_id)
        with self._lock:
            if normalized_project_id not in self._states:
                raise ProjectNotFoundError(normalized_project_id)
            return tuple(self._history.get(normalized_project_id) or ())

    def list_projects(self) -> tuple[GameProjectState, ...]:
        with self._lock:
            return tuple(self._states[key] for key in sorted(self._states))

    def apply_patch(self, patch: ProjectStatePatch) -> GameProjectState:
        if not isinstance(patch, ProjectStatePatch):
            raise TypeError("apply_patch requires a ProjectStatePatch")
        with self._lock:
            previous_result = self._patch_results.get(patch.patch_id)
            if previous_result is not None:
                previous_project_id, previous_fingerprint, result = previous_result
                if previous_project_id != patch.project_id or previous_fingerprint != patch.fingerprint:
                    raise ProjectPatchConflictError(patch.patch_id)
                return result

            current = self._states.get(patch.project_id)
            if current is None:
                raise ProjectNotFoundError(patch.project_id)
            if current.project_version != patch.expected_project_version:
                raise ProjectVersionConflictError(
                    f"{patch.project_id}: expected {patch.expected_project_version}, "
                    f"current {current.project_version}"
                )
            changes = dict(patch.changes)
            if "scene_world_version" in changes:
                next_world_version = int(changes["scene_world_version"])
                if next_world_version < current.scene_world_version:
                    raise InvalidProjectStateTransitionError(
                        f"scene_world_version cannot decrease from {current.scene_world_version} "
                        f"to {next_world_version}"
                    )

            effective_changes = {
                key: value
                for key, value in changes.items()
                if getattr(current, key) != value
            }
            if not effective_changes:
                self._patch_results[patch.patch_id] = (
                    patch.project_id,
                    patch.fingerprint,
                    current,
                )
                return current

            next_state = replace(
                current,
                project_version=current.project_version + 1,
                **effective_changes,
            )
            transition = ProjectStateTransition(
                transition_id=f"transition-{patch.patch_id}",
                patch_id=patch.patch_id,
                project_id=patch.project_id,
                from_version=current.project_version,
                to_version=next_state.project_version,
                source=patch.source,
                changed_fields=tuple(sorted(effective_changes)),
                before=current,
                after=next_state,
            )
            self._states[patch.project_id] = next_state
            self._history.setdefault(patch.project_id, []).append(transition)
            self._patch_results[patch.patch_id] = (
                patch.project_id,
                patch.fingerprint,
                next_state,
            )
            return next_state
