"""Versioned contracts for planning, art, and program Agent collaboration.

This module is intentionally independent from AgentRuntime.  It defines
project-level DTOs and validates Artifact payloads, but it cannot read a scene
snapshot, create a ToolCallGraph, or write RuntimeState.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from ..gameplay_contracts import (
    ALLOWED_GAMEPLAY_PRIMITIVES,
    GAMEPLAY_PRIMITIVE_PARAMETER_KEYS,
)
from ..schema_versions import COLLABORATION_SCHEMA_VERSION

PRODUCER_ROLES = frozenset({"planning", "art", "program"})
SEMANTIC_ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
GAMEPLAY_PRIMITIVE_CAPABILITY_REQUIREMENTS = MappingProxyType({
    "on_enter": MappingProxyType({"subject_slot": "trigger_zone"}),
    "on_collect": MappingProxyType({"subject_slot": "collectible"}),
    "unlock": MappingProxyType({"target_slot": "lockable"}),
})
GAMEPLAY_PRIMITIVE_REQUIRED_PARAMETERS = MappingProxyType({
    "set_state": frozenset({"state_key", "value"}),
    "unlock": frozenset({"required_state"}),
    "complete_objective": frozenset({"objective_id"}),
})
ARTIFACT_TYPES = frozenset(
    {
        "GameDesignBrief",
        "LevelPlan",
        "ArtDirection",
        "SceneCompositionPlan",
        "GameplayLogicPlan",
        "EntityBindingPlan",
    }
)
ARTIFACT_LINEAGE_IDS = MappingProxyType(
    {
        "GameDesignBrief": "planning.game-design-brief",
        "LevelPlan": "planning.level-plan",
        "ArtDirection": "art.direction",
        "SceneCompositionPlan": "art.scene-composition",
        "GameplayLogicPlan": "program.gameplay-logic-plan",
        "EntityBindingPlan": "program.entity-binding-plan",
    }
)
ARTIFACT_PRODUCER_ROLES = MappingProxyType(
    {
        "GameDesignBrief": "planning",
        "LevelPlan": "planning",
        "ArtDirection": "art",
        "SceneCompositionPlan": "art",
        "GameplayLogicPlan": "program",
        "EntityBindingPlan": "program",
    }
)
RED_PROJECT_ARTIFACT_TYPES = frozenset(
    {
        "GameDesignBrief",
        "LevelPlan",
        "ArtDirection",
        "SceneCompositionPlan",
        "GameplayLogicPlan",
    }
)
ARTIFACT_STATUSES = frozenset({"draft", "validated", "invalid", "stale", "archived"})
SNAPSHOT_SOURCES = frozenset({"none", "mock", "runtime"})
TASK_STATUSES = frozenset({"pending", "ready", "in_progress", "blocked", "failed", "completed"})
RISK_LEVELS = frozenset({"low", "medium", "high"})
PROJECT_VALIDATION_STATUSES = frozenset({"pending", "valid", "invalid", "stale", "blocked"})


class NonExecutableArtifactError(RuntimeError):
    """Raised when a non-production Artifact reaches an execution boundary."""


def _normalized_json_value(value: Any, *, path: str = "payload") -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key in sorted(value, key=lambda item: str(item)):
            text_key = str(key).strip()
            if not text_key:
                raise ValueError(f"{path} contains an empty key")
            normalized[text_key] = _normalized_json_value(value[key], path=f"{path}.{text_key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            _normalized_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return value
    raise TypeError(f"{path} contains unsupported value type {type(value).__name__}")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _normalized_json_value(value),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def compute_artifact_content_hash(artifact_type: str, payload: Any) -> str:
    normalized_type = _text(artifact_type)
    normalized_payload = _normalized_json_value(payload)
    if normalized_type not in ARTIFACT_TYPES:
        raise ValueError(f"unsupported artifact_type: {normalized_type}")
    if not isinstance(normalized_payload, Mapping):
        raise ValueError("Artifact payload must be a mapping or payload dataclass")
    hash_input = {
        "artifact_type": normalized_type,
        "schema_version": COLLABORATION_SCHEMA_VERSION,
        "payload": normalized_payload,
    }
    return "sha256:" + hashlib.sha256(_canonical_json(hash_input).encode("utf-8")).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _text(value: Any) -> str:
    return str(value or "").strip()


def _text_list(value: Any) -> list[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None
    result = [_text(item) for item in value]
    return result if result and all(result) else None


def _text_tuple(value: Any, *, field_name: str, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{field_name} must be a sequence of strings")
    normalized: list[str] = []
    for item in value:
        text = _text(item)
        if not text:
            raise ValueError(f"{field_name} cannot contain empty values")
        normalized.append(text)
    result = tuple(sorted(set(normalized)))
    if not result and not allow_empty:
        raise ValueError(f"{field_name} cannot be empty")
    return result


@dataclass(frozen=True)
class ValidationResult:
    validator_id: str
    schema_version: str
    valid: bool
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "schema_version": self.schema_version,
            "valid": self.valid,
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class GameDesignBrief:
    project_goal: str
    player_experience: tuple[str, ...]
    core_rules: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]


@dataclass(frozen=True)
class LevelPlan:
    level_goal: str
    zones: tuple[str, ...]
    progression: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]


@dataclass(frozen=True)
class ArtDirection:
    style_keywords: tuple[str, ...]
    palette: tuple[str, ...]
    lighting: tuple[str, ...]
    avoid_keywords: tuple[str, ...]


@dataclass(frozen=True)
class SceneCompositionPlan:
    scene_type: str
    environment_requirements: tuple[str, ...]
    entity_requirements: tuple[str, ...]
    layout_rules: tuple[str, ...]
    image_prompts: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GameplayEntitySlot:
    slot_id: str
    semantic_role: str
    required_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class GameplayPrimitiveSpec:
    primitive_id: str
    kind: str
    subject_slot: str
    target_slot: str
    parameters: Mapping[str, Any]


@dataclass(frozen=True)
class GameplayLogicPlan:
    states: tuple[str, ...]
    entity_slots: tuple[GameplayEntitySlot, ...]
    primitives: tuple[GameplayPrimitiveSpec, ...]
    win_conditions: tuple[str, ...]
    lose_conditions: tuple[str, ...]
    # Legacy narrative fields remain audit-only; primitives carry executable semantics.
    triggers: tuple[str, ...] = ()
    rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class EntityBindingPlan:
    snapshot_plan_id: str
    snapshot_version: int
    bindings: tuple[Mapping[str, Any], ...]


def _required_text(payload: Mapping[str, Any], field: str, errors: list[str]) -> None:
    if not _text(payload.get(field)):
        errors.append(f"{field}:required_text")


def _required_text_list(payload: Mapping[str, Any], field: str, errors: list[str]) -> None:
    if _text_list(payload.get(field)) is None:
        errors.append(f"{field}:required_nonempty_text_list")


def _validate_gameplay_logic_plan(payload: Mapping[str, Any], errors: list[str]) -> None:
    slots = payload.get("entity_slots")
    primitives = payload.get("primitives")
    if not isinstance(slots, list) or not slots:
        errors.append("entity_slots:required_nonempty_list")
        slots = []
    if not isinstance(primitives, list) or not primitives:
        errors.append("primitives:required_nonempty_list")
        primitives = []

    slot_capabilities: dict[str, frozenset[str]] = {}
    semantic_roles: set[str] = set()
    for index, slot in enumerate(slots):
        if not isinstance(slot, Mapping):
            errors.append(f"entity_slots[{index}]:required_mapping")
            continue
        slot_id = _text(slot.get("slot_id"))
        semantic_role = _text(slot.get("semantic_role"))
        capabilities = _text_list(slot.get("required_capabilities"))
        if not slot_id:
            errors.append(f"entity_slots[{index}].slot_id:required_text")
            continue
        if slot_id in slot_capabilities:
            errors.append(f"entity_slots[{index}].slot_id:duplicate")
            continue
        if not semantic_role:
            errors.append(f"entity_slots[{index}].semantic_role:required_text")
        elif not SEMANTIC_ROLE_PATTERN.fullmatch(semantic_role):
            errors.append(f"entity_slots[{index}].semantic_role:invalid_identifier")
        elif semantic_role in semantic_roles:
            errors.append(f"entity_slots[{index}].semantic_role:duplicate")
        else:
            semantic_roles.add(semantic_role)
        if capabilities is None:
            errors.append(f"entity_slots[{index}].required_capabilities:required_nonempty_text_list")
            capabilities = []
        slot_capabilities[slot_id] = frozenset(capabilities)

    primitive_edges: dict[str, set[str]] = {}
    primitive_ids: set[str] = set()
    for index, primitive in enumerate(primitives):
        if not isinstance(primitive, Mapping):
            errors.append(f"primitives[{index}]:required_mapping")
            continue
        primitive_id = _text(primitive.get("primitive_id"))
        kind = _text(primitive.get("kind"))
        subject_slot = _text(primitive.get("subject_slot"))
        target_slot = _text(primitive.get("target_slot"))
        parameters = primitive.get("parameters")
        if not primitive_id:
            errors.append(f"primitives[{index}].primitive_id:required_text")
        elif primitive_id in primitive_ids:
            errors.append(f"primitives[{index}].primitive_id:duplicate")
        else:
            primitive_ids.add(primitive_id)
        if kind not in ALLOWED_GAMEPLAY_PRIMITIVES:
            errors.append(f"primitives[{index}].kind:unsupported")
            continue
        if subject_slot not in slot_capabilities:
            errors.append(f"primitives[{index}].subject_slot:unknown")
        if target_slot not in slot_capabilities:
            errors.append(f"primitives[{index}].target_slot:unknown")
        if subject_slot and target_slot:
            primitive_edges.setdefault(subject_slot, set()).add(target_slot)
        if not isinstance(parameters, Mapping):
            errors.append(f"primitives[{index}].parameters:required_mapping")
            parameters = {}
        allowed_parameters = GAMEPLAY_PRIMITIVE_PARAMETER_KEYS[kind]
        unknown_parameters = sorted(set(parameters) - allowed_parameters)
        if unknown_parameters:
            errors.append(f"primitives[{index}].parameters:unknown:{','.join(map(str, unknown_parameters))}")
        for slot_field, capability in GAMEPLAY_PRIMITIVE_CAPABILITY_REQUIREMENTS.get(kind, {}).items():
            slot_id = subject_slot if slot_field == "subject_slot" else target_slot
            if capability not in slot_capabilities.get(slot_id, frozenset()):
                errors.append(f"primitives[{index}].{slot_field}:requires_{capability}")
        required_parameters = GAMEPLAY_PRIMITIVE_REQUIRED_PARAMETERS.get(kind, frozenset())
        missing_parameters = sorted(
            key
            for key in required_parameters
            if key not in parameters or (key != "value" and not _text(parameters.get(key)))
        )
        if missing_parameters:
            errors.append(
                f"primitives[{index}].parameters:requires_{'_and_'.join(missing_parameters)}"
            )

    visited: set[str] = set()
    active: set[str] = set()

    def has_cycle(slot_id: str) -> bool:
        if slot_id in active:
            return True
        if slot_id in visited:
            return False
        visited.add(slot_id)
        active.add(slot_id)
        cyclic = any(has_cycle(target) for target in primitive_edges.get(slot_id, ()))
        active.remove(slot_id)
        return cyclic

    if any(has_cycle(slot_id) for slot_id in primitive_edges):
        errors.append("primitives:cyclic_slot_reference")


def gameplay_logic_contract_manifest() -> Mapping[str, Any]:
    """Return the prompt-facing view of the authoritative gameplay validator."""

    return MappingProxyType({
        "allowed_primitives": tuple(sorted(ALLOWED_GAMEPLAY_PRIMITIVES)),
        "parameter_keys": MappingProxyType({
            kind: tuple(sorted(keys))
            for kind, keys in GAMEPLAY_PRIMITIVE_PARAMETER_KEYS.items()
        }),
        "required_parameters": MappingProxyType({
            kind: tuple(sorted(keys))
            for kind, keys in GAMEPLAY_PRIMITIVE_REQUIRED_PARAMETERS.items()
        }),
        "capability_requirements": MappingProxyType({
            kind: MappingProxyType(dict(requirements))
            for kind, requirements in GAMEPLAY_PRIMITIVE_CAPABILITY_REQUIREMENTS.items()
        }),
        "identity_rules": (
            "slot_id values must be unique",
            "semantic_role values must be unique canonical identifiers matching ^[a-z][a-z0-9_.-]{2,63}$",
            "primitive_id values must be unique",
            "subject_slot and target_slot must reference declared slot_id values",
            "slot references must not form a cycle",
        ),
    })


def validate_artifact_payload(artifact_type: str, payload: Any) -> ValidationResult:
    normalized_type = _text(artifact_type)
    errors: list[str] = []
    if normalized_type not in ARTIFACT_TYPES:
        errors.append("artifact_type:unsupported")
    try:
        normalized = _normalized_json_value(payload)
    except (TypeError, ValueError) as exc:
        normalized = {}
        errors.append(f"payload:not_canonical_json:{exc}")
    if not isinstance(normalized, Mapping):
        errors.append("payload:required_mapping")
        normalized = {}

    text_fields: dict[str, tuple[str, ...]] = {
        "GameDesignBrief": ("project_goal",),
        "LevelPlan": ("level_goal",),
        "ArtDirection": (),
        "SceneCompositionPlan": ("scene_type",),
        "GameplayLogicPlan": (),
        "EntityBindingPlan": ("snapshot_plan_id",),
    }
    list_fields: dict[str, tuple[str, ...]] = {
        "GameDesignBrief": ("player_experience", "core_rules", "acceptance_criteria"),
        "LevelPlan": ("zones", "progression", "acceptance_criteria"),
        "ArtDirection": ("style_keywords", "palette", "lighting", "avoid_keywords"),
        "SceneCompositionPlan": (
            "environment_requirements",
            "entity_requirements",
            "layout_rules",
        ),
        "GameplayLogicPlan": ("states", "win_conditions", "lose_conditions"),
        "EntityBindingPlan": (),
    }
    for field in text_fields.get(normalized_type, ()):
        _required_text(normalized, field, errors)
    for field in list_fields.get(normalized_type, ()):
        _required_text_list(normalized, field, errors)

    if normalized_type == "GameplayLogicPlan":
        _validate_gameplay_logic_plan(normalized, errors)

    if normalized_type == "EntityBindingPlan":
        try:
            snapshot_version = int(normalized.get("snapshot_version") or 0)
        except (TypeError, ValueError):
            snapshot_version = 0
        if snapshot_version <= 0:
            errors.append("snapshot_version:required_positive_integer")
        bindings = normalized.get("bindings")
        if not isinstance(bindings, list) or not bindings:
            errors.append("bindings:required_nonempty_list")
        else:
            slot_ids: set[str] = set()
            entity_ids: set[str] = set()
            allowed_binding_fields = {
                "slot_id",
                "semantic_role",
                "entity_id",
                "entity_version",
                "asset_id",
                "required_capabilities",
            }
            for index, binding in enumerate(bindings):
                if not isinstance(binding, Mapping):
                    errors.append(f"bindings[{index}]:required_mapping")
                    continue
                unknown_fields = sorted(set(binding) - allowed_binding_fields)
                if unknown_fields:
                    errors.append(
                        f"bindings[{index}]:unknown_fields:{','.join(map(str, unknown_fields))}"
                    )
                slot_id = _text(binding.get("slot_id"))
                entity_id = _text(binding.get("entity_id"))
                if not slot_id:
                    errors.append(f"bindings[{index}].slot_id:required_text")
                elif slot_id in slot_ids:
                    errors.append(f"bindings[{index}].slot_id:duplicate")
                else:
                    slot_ids.add(slot_id)
                if not entity_id:
                    errors.append(f"bindings[{index}].entity_id:required_text")
                elif entity_id in entity_ids:
                    errors.append(f"bindings[{index}].entity_id:duplicate")
                else:
                    entity_ids.add(entity_id)
                if not _text(binding.get("semantic_role")):
                    errors.append(f"bindings[{index}].semantic_role:required_text")
                if not _text(binding.get("asset_id")):
                    errors.append(f"bindings[{index}].asset_id:required_text")
                try:
                    entity_version = int(binding.get("entity_version") or 0)
                except (TypeError, ValueError):
                    entity_version = 0
                if entity_version <= 0:
                    errors.append(f"bindings[{index}].entity_version:required_positive_integer")
                if _text_list(binding.get("required_capabilities")) is None:
                    errors.append(
                        f"bindings[{index}].required_capabilities:required_nonempty_text_list"
                    )

    return ValidationResult(
        validator_id=f"agent_collaboration.{normalized_type or 'unknown'}.v1",
        schema_version=COLLABORATION_SCHEMA_VERSION,
        valid=not errors,
        errors=tuple(sorted(set(errors))),
    )


@dataclass(frozen=True, init=False)
class ArtifactEnvelope:
    artifact_id: str
    artifact_type: str
    version: int
    producer_role: str
    source_task_id: str
    base_project_version: int
    base_world_version: int
    dependencies: tuple[str, ...]
    content_hash: str
    snapshot_source: str
    non_executable: bool
    status: str
    validation_result: ValidationResult
    payload: Mapping[str, Any]
    schema_version: str

    def __init__(
        self,
        *,
        artifact_id: str,
        artifact_type: str,
        version: int,
        producer_role: str,
        source_task_id: str,
        base_project_version: int,
        base_world_version: int,
        dependencies: Sequence[str] = (),
        snapshot_source: str = "none",
        non_executable: bool = True,
        status: str = "draft",
        payload: Any,
    ) -> None:
        normalized_artifact_id = _text(artifact_id)
        normalized_type = _text(artifact_type)
        normalized_role = _text(producer_role).lower()
        normalized_task_id = _text(source_task_id)
        normalized_snapshot_source = _text(snapshot_source).lower() or "none"
        normalized_status = _text(status).lower() or "draft"
        normalized_dependencies = _text_tuple(
            dependencies,
            field_name="dependencies",
        )
        if not normalized_artifact_id:
            raise ValueError("artifact_id is required")
        if normalized_type not in ARTIFACT_TYPES:
            raise ValueError(f"unsupported artifact_type: {normalized_type}")
        if normalized_role not in PRODUCER_ROLES:
            raise ValueError(f"unsupported producer_role: {normalized_role}")
        expected_role = ARTIFACT_PRODUCER_ROLES[normalized_type]
        if normalized_role != expected_role:
            raise ValueError(
                f"{normalized_type} requires producer_role {expected_role}, got {normalized_role}"
            )
        if not normalized_task_id:
            raise ValueError("source_task_id is required")
        if int(version) <= 0:
            raise ValueError("version must be positive")
        if int(base_project_version) < 0 or int(base_world_version) < 0:
            raise ValueError("base versions must be non-negative")
        if normalized_snapshot_source not in SNAPSHOT_SOURCES:
            raise ValueError(f"unsupported snapshot_source: {normalized_snapshot_source}")
        if normalized_status not in ARTIFACT_STATUSES:
            raise ValueError(f"unsupported artifact status: {normalized_status}")
        if normalized_snapshot_source == "mock" and not bool(non_executable):
            raise NonExecutableArtifactError(
                f"{normalized_artifact_id}: mock Artifact must be non_executable"
            )
        if not bool(non_executable) and normalized_snapshot_source != "runtime":
            raise NonExecutableArtifactError(
                f"{normalized_artifact_id}: executable Artifact requires runtime snapshot_source"
            )
        if normalized_snapshot_source == "runtime" and int(base_world_version) <= 0:
            raise NonExecutableArtifactError(
                f"{normalized_artifact_id}: runtime Artifact requires positive base_world_version"
            )

        normalized_payload = _normalized_json_value(payload)
        if not isinstance(normalized_payload, Mapping):
            raise ValueError("Artifact payload must be a mapping or payload dataclass")
        validation = validate_artifact_payload(normalized_type, normalized_payload)
        if not validation.valid:
            normalized_status = "invalid"
        elif normalized_status == "invalid":
            raise ValueError("a valid payload cannot be marked invalid")
        content_hash = compute_artifact_content_hash(normalized_type, normalized_payload)

        values = {
            "artifact_id": normalized_artifact_id,
            "artifact_type": normalized_type,
            "version": int(version),
            "producer_role": normalized_role,
            "source_task_id": normalized_task_id,
            "base_project_version": int(base_project_version),
            "base_world_version": int(base_world_version),
            "dependencies": normalized_dependencies,
            "content_hash": content_hash,
            "snapshot_source": normalized_snapshot_source,
            "non_executable": bool(non_executable),
            "status": normalized_status,
            "validation_result": validation,
            "payload": _freeze(normalized_payload),
            "schema_version": COLLABORATION_SCHEMA_VERSION,
        }
        for key, value in values.items():
            object.__setattr__(self, key, value)

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "version": self.version,
            "producer_role": self.producer_role,
            "source_task_id": self.source_task_id,
            "base_project_version": self.base_project_version,
            "base_world_version": self.base_world_version,
            "dependencies": list(self.dependencies),
            "content_hash": self.content_hash,
            "snapshot_source": self.snapshot_source,
            "non_executable": self.non_executable,
            "status": self.status,
            "validation_result": self.validation_result.as_dict(),
            "payload": _thaw(self.payload),
            "schema_version": self.schema_version,
        }


def assert_executable(artifact: ArtifactEnvelope) -> None:
    if not isinstance(artifact, ArtifactEnvelope):
        raise TypeError("assert_executable requires an ArtifactEnvelope")
    if artifact.snapshot_source == "mock":
        raise NonExecutableArtifactError(f"{artifact.artifact_id}: mock Artifact cannot execute")
    if artifact.non_executable:
        raise NonExecutableArtifactError(f"{artifact.artifact_id}: Artifact is non_executable")
    if artifact.snapshot_source != "runtime":
        raise NonExecutableArtifactError(
            f"{artifact.artifact_id}: executable Artifact requires runtime snapshot_source"
        )
    if artifact.base_world_version <= 0:
        raise NonExecutableArtifactError(
            f"{artifact.artifact_id}: executable Artifact requires positive base_world_version"
        )
    if artifact.status != "validated" or not artifact.validation_result.valid:
        raise NonExecutableArtifactError(f"{artifact.artifact_id}: Artifact is not validated")


@dataclass(frozen=True)
class GameProjectState:
    project_id: str
    project_version: int
    room_id: str
    active_task_graph_id: str = ""
    active_scene_plan_id: str = ""
    scene_world_version: int = 0
    artifact_refs: tuple[str, ...] = ()
    validation_status: str = "pending"

    def __post_init__(self) -> None:
        if not _text(self.project_id) or not _text(self.room_id):
            raise ValueError("project_id and room_id are required")
        if int(self.project_version) <= 0 or int(self.scene_world_version) < 0:
            raise ValueError("project_version must be positive and scene_world_version non-negative")
        validation_status = _text(self.validation_status).lower()
        if validation_status not in PROJECT_VALIDATION_STATUSES:
            raise ValueError(f"unsupported project validation_status: {validation_status}")
        object.__setattr__(
            self,
            "artifact_refs",
            _text_tuple(self.artifact_refs, field_name="artifact_refs"),
        )
        object.__setattr__(self, "validation_status", validation_status)

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_version": self.project_version,
            "room_id": self.room_id,
            "active_task_graph_id": self.active_task_graph_id,
            "active_scene_plan_id": self.active_scene_plan_id,
            "scene_world_version": self.scene_world_version,
            "artifact_refs": list(self.artifact_refs),
            "validation_status": self.validation_status,
        }


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    assigned_role: str
    objective: str
    input_artifact_refs: tuple[str, ...]
    output_types: tuple[str, ...]
    depends_on: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    capability_set: tuple[str, ...]
    risk_level: str = "low"
    status: str = "pending"
    max_attempts: int = 2

    def __post_init__(self) -> None:
        if not _text(self.task_id) or not _text(self.objective):
            raise ValueError("task_id and objective are required")
        role = _text(self.assigned_role).lower()
        if role not in PRODUCER_ROLES:
            raise ValueError(f"unsupported assigned_role: {role}")
        outputs = _text_tuple(
            self.output_types,
            field_name="output_types",
            allow_empty=False,
        )
        if not outputs or any(item not in ARTIFACT_TYPES for item in outputs):
            raise ValueError("output_types must contain supported Artifact types")
        risk = _text(self.risk_level).lower()
        status = _text(self.status).lower()
        if risk not in RISK_LEVELS or status not in TASK_STATUSES:
            raise ValueError("risk_level or task status is invalid")
        if int(self.max_attempts) <= 0:
            raise ValueError("max_attempts must be positive")
        object.__setattr__(self, "assigned_role", role)
        object.__setattr__(self, "output_types", outputs)
        object.__setattr__(self, "risk_level", risk)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "max_attempts", int(self.max_attempts))
        for field_name, allow_empty in (
            ("input_artifact_refs", True),
            ("depends_on", True),
            ("acceptance_criteria", False),
            ("capability_set", True),
        ):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(
                    getattr(self, field_name),
                    field_name=field_name,
                    allow_empty=allow_empty,
                ),
            )
