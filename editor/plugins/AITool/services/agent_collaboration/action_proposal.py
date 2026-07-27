"""Single-player gameplay contracts that remain upstream of Runtime execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from ..gameplay_contracts import (
    canonical_payload_hash,
    gameplay_command_idempotency_key,
)
from ..schema_versions import (
    ACTION_PROPOSAL_SCHEMA_VERSION,
    GAMEPLAY_MANIFEST_SCHEMA_VERSION,
)
from .contracts import (
    ALLOWED_GAMEPLAY_PRIMITIVES,
    GAMEPLAY_PRIMITIVE_PARAMETER_KEYS,
    ArtifactEnvelope,
    GameplayPrimitiveSpec,
    assert_executable,
    compute_artifact_content_hash,
)


SINGLE_PLAYER_EXECUTION_SCOPE = "single_player_local"
GAMEPLAY_APPLY_OPERATION = "gameplay.apply_manifest"


def _required_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _text_tuple(value: Sequence[object], field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a sequence")
    result = tuple(sorted({str(item or "").strip() for item in value if str(item or "").strip()}))
    if not result:
        raise ValueError(f"{field_name} cannot be empty")
    return result


@dataclass(frozen=True)
class GameplayEntityBinding:
    slot_id: str
    semantic_role: str
    entity_id: str
    entity_version: int
    asset_id: str
    required_capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in ("slot_id", "semantic_role", "entity_id", "asset_id"):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        if isinstance(self.entity_version, bool) or int(self.entity_version) <= 0:
            raise ValueError("entity_version must be positive")
        object.__setattr__(self, "entity_version", int(self.entity_version))
        object.__setattr__(
            self,
            "required_capabilities",
            _text_tuple(self.required_capabilities, "required_capabilities"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "semantic_role": self.semantic_role,
            "entity_id": self.entity_id,
            "entity_version": self.entity_version,
            "asset_id": self.asset_id,
            "required_capabilities": list(self.required_capabilities),
        }


@dataclass(frozen=True)
class GameplayManifest:
    project_id: str
    plan_id: str
    scene_version: int
    entity_bindings: tuple[GameplayEntityBinding, ...]
    primitives: tuple[GameplayPrimitiveSpec, ...]
    objective_id: str
    schema_version: str = GAMEPLAY_MANIFEST_SCHEMA_VERSION
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != GAMEPLAY_MANIFEST_SCHEMA_VERSION:
            raise ValueError("GameplayManifest schema_version is incompatible")
        for field_name in ("project_id", "plan_id", "objective_id"):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        if isinstance(self.scene_version, bool) or int(self.scene_version) <= 0:
            raise ValueError("scene_version must be positive")
        object.__setattr__(self, "scene_version", int(self.scene_version))
        bindings = tuple(self.entity_bindings)
        if not bindings or not all(isinstance(item, GameplayEntityBinding) for item in bindings):
            raise ValueError("entity_bindings must contain GameplayEntityBinding values")
        if len({item.slot_id for item in bindings}) != len(bindings):
            raise ValueError("entity_bindings contain duplicate slot_id")
        if len({item.entity_id for item in bindings}) != len(bindings):
            raise ValueError("entity_bindings cannot reuse one entity_id")
        object.__setattr__(self, "entity_bindings", bindings)

        slot_ids = {item.slot_id for item in bindings}
        primitives = tuple(self.primitives)
        if not primitives or not all(isinstance(item, GameplayPrimitiveSpec) for item in primitives):
            raise ValueError("primitives must contain GameplayPrimitiveSpec values")
        primitive_ids: set[str] = set()
        objective_ids: set[str] = set()
        normalized_primitives: list[GameplayPrimitiveSpec] = []
        for primitive in primitives:
            primitive_id = _required_text(primitive.primitive_id, "primitive_id")
            if primitive_id in primitive_ids:
                raise ValueError("primitives contain duplicate primitive_id")
            primitive_ids.add(primitive_id)
            kind = _required_text(primitive.kind, "primitive.kind")
            if kind not in ALLOWED_GAMEPLAY_PRIMITIVES:
                raise ValueError(f"unsupported gameplay primitive: {kind}")
            subject_slot = _required_text(primitive.subject_slot, "primitive.subject_slot")
            target_slot = _required_text(primitive.target_slot, "primitive.target_slot")
            if subject_slot not in slot_ids or target_slot not in slot_ids:
                raise ValueError("primitive references an unbound entity slot")
            if not isinstance(primitive.parameters, Mapping):
                raise TypeError("primitive.parameters must be a mapping")
            parameters = dict(primitive.parameters)
            unknown = sorted(set(parameters) - GAMEPLAY_PRIMITIVE_PARAMETER_KEYS[kind])
            if unknown:
                raise ValueError(f"primitive {primitive_id} has unknown parameters: {','.join(unknown)}")
            if kind == "set_state" and (
                not str(parameters.get("state_key") or "").strip() or "value" not in parameters
            ):
                raise ValueError("set_state requires state_key and value")
            if kind == "unlock" and not str(parameters.get("required_state") or "").strip():
                raise ValueError("unlock requires required_state")
            if kind == "complete_objective":
                objective = _required_text(parameters.get("objective_id"), "objective_id")
                objective_ids.add(objective)
            normalized_primitives.append(GameplayPrimitiveSpec(
                primitive_id=primitive_id,
                kind=kind,
                subject_slot=subject_slot,
                target_slot=target_slot,
                parameters=MappingProxyType(parameters),
            ))
        if objective_ids != {self.objective_id}:
            raise ValueError("complete_objective primitives must match GameplayManifest objective_id")
        object.__setattr__(self, "primitives", tuple(normalized_primitives))
        object.__setattr__(self, "content_hash", canonical_payload_hash(self._hash_payload()))

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "plan_id": self.plan_id,
            "scene_version": self.scene_version,
            "entity_bindings": [item.as_dict() for item in self.entity_bindings],
            "primitives": [
                {
                    "primitive_id": item.primitive_id,
                    "kind": item.kind,
                    "subject_slot": item.subject_slot,
                    "target_slot": item.target_slot,
                    "parameters": dict(item.parameters),
                }
                for item in self.primitives
            ],
            "objective_id": self.objective_id,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._hash_payload(), "content_hash": self.content_hash}


@dataclass(frozen=True, init=False)
class ActionProposal:
    schema_version: str
    proposal_id: str
    command_id: str
    project_id: str
    room_id: str
    plan_id: str
    scene_version: int
    execution_scope: str
    operation: str
    gate_report_id: str
    gate_profile: str
    binding_artifact_id: str
    binding_artifact_hash: str
    gameplay_manifest: GameplayManifest
    idempotency_key: str
    risk_level: str
    status: str

    def __init__(
        self,
        *,
        proposal_id: str,
        command_id: str,
        room_id: str,
        binding_artifact: ArtifactEnvelope,
        gameplay_manifest: GameplayManifest,
        gate_report: Mapping[str, Any],
        execution_scope: str = SINGLE_PLAYER_EXECUTION_SCOPE,
    ) -> None:
        assert_executable(binding_artifact)
        if binding_artifact.artifact_type != "EntityBindingPlan":
            raise ValueError("ActionProposal requires an EntityBindingPlan Artifact")
        if compute_artifact_content_hash(binding_artifact.artifact_type, binding_artifact.payload) != binding_artifact.content_hash:
            raise ValueError("EntityBindingPlan content_hash mismatch")
        if not isinstance(gameplay_manifest, GameplayManifest):
            raise TypeError("gameplay_manifest must be GameplayManifest")
        if not isinstance(gate_report, Mapping):
            raise TypeError("gate_report must be a mapping")
        gate = dict(gate_report)
        metrics = gate.get("metrics") if isinstance(gate.get("metrics"), Mapping) else {}
        gate_profile = str(metrics.get("gate_profile") or "").strip()
        unlocks = {str(item or "").strip() for item in gate.get("capability_unlocks") or ()}
        if str(gate.get("overall") or "").strip().lower() != "green":
            raise ValueError("ActionProposal requires a Green gate report")
        if gate_profile != "single_player_demo":
            raise ValueError("ActionProposal requires single_player_demo gate profile")
        if "single_player_local_action" not in unlocks:
            raise ValueError("ActionProposal requires single_player_local_action capability")
        normalized_scope = _required_text(execution_scope, "execution_scope")
        if normalized_scope != SINGLE_PLAYER_EXECUTION_SCOPE:
            raise ValueError("ActionProposal execution_scope must be single_player_local")
        gate_plan_id = _required_text(gate.get("plan_id"), "gate_report.plan_id")
        gate_scene_version = int(gate.get("scene_version") or 0)
        if gate_plan_id != gameplay_manifest.plan_id or gate_scene_version != gameplay_manifest.scene_version:
            raise ValueError("ActionProposal gate and GameplayManifest world identity mismatch")
        payload_plan_id = str(binding_artifact.payload.get("snapshot_plan_id") or "").strip()
        payload_scene_version = int(binding_artifact.payload.get("snapshot_version") or 0)
        if payload_plan_id != gameplay_manifest.plan_id or payload_scene_version != gameplay_manifest.scene_version:
            raise ValueError("EntityBindingPlan and GameplayManifest world identity mismatch")
        if binding_artifact.base_world_version != gameplay_manifest.scene_version:
            raise ValueError("EntityBindingPlan base_world_version is stale")

        values = {
            "schema_version": ACTION_PROPOSAL_SCHEMA_VERSION,
            "proposal_id": _required_text(proposal_id, "proposal_id"),
            "command_id": _required_text(command_id, "command_id"),
            "project_id": gameplay_manifest.project_id,
            "room_id": _required_text(room_id, "room_id"),
            "plan_id": gameplay_manifest.plan_id,
            "scene_version": gameplay_manifest.scene_version,
            "execution_scope": normalized_scope,
            "operation": GAMEPLAY_APPLY_OPERATION,
            "gate_report_id": _required_text(gate.get("gate_report_id"), "gate_report_id"),
            "gate_profile": gate_profile,
            "binding_artifact_id": binding_artifact.artifact_id,
            "binding_artifact_hash": binding_artifact.content_hash,
            "gameplay_manifest": gameplay_manifest,
            "idempotency_key": gameplay_command_idempotency_key(
                command_id,
                gameplay_manifest.content_hash,
            ),
            "risk_level": "low",
            "status": "validated",
        }
        for key, value in values.items():
            object.__setattr__(self, key, value)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "proposal_id": self.proposal_id,
            "command_id": self.command_id,
            "project_id": self.project_id,
            "room_id": self.room_id,
            "plan_id": self.plan_id,
            "scene_version": self.scene_version,
            "execution_scope": self.execution_scope,
            "operation": self.operation,
            "gate_report_id": self.gate_report_id,
            "gate_profile": self.gate_profile,
            "binding_artifact_id": self.binding_artifact_id,
            "binding_artifact_hash": self.binding_artifact_hash,
            "gameplay_manifest": self.gameplay_manifest.as_dict(),
            "idempotency_key": self.idempotency_key,
            "risk_level": self.risk_level,
            "status": self.status,
        }


__all__ = [
    "ActionProposal",
    "GAMEPLAY_APPLY_OPERATION",
    "GameplayEntityBinding",
    "GameplayManifest",
    "SINGLE_PLAYER_EXECUTION_SCOPE",
]
