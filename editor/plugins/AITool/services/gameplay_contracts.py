"""Shared, engine-independent validation for the single-player gameplay payload."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .schema_versions import GAMEPLAY_MANIFEST_SCHEMA_VERSION


ALLOWED_GAMEPLAY_PRIMITIVES = frozenset(
    {"on_enter", "on_collect", "set_state", "unlock", "complete_objective"}
)
GAMEPLAY_PRIMITIVE_PARAMETER_KEYS = MappingProxyType(
    {
        "on_enter": frozenset({"state_key", "expected_value", "next_state"}),
        "on_collect": frozenset({"state_key", "set_value"}),
        "set_state": frozenset({"state_key", "value"}),
        "unlock": frozenset({"required_state", "required_value"}),
        "complete_objective": frozenset({"objective_id"}),
    }
)

_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "project_id",
        "plan_id",
        "scene_version",
        "entity_bindings",
        "primitives",
        "objective_id",
        "content_hash",
    }
)
_BINDING_FIELDS = frozenset(
    {"slot_id", "semantic_role", "entity_id", "entity_version", "asset_id", "required_capabilities"}
)
_PRIMITIVE_FIELDS = frozenset(
    {"primitive_id", "kind", "subject_slot", "target_slot", "parameters"}
)


def canonical_payload_hash(value: Mapping[str, Any]) -> str:
    canonical = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("ascii")).hexdigest()


def gameplay_manifest_content_hash(payload: Mapping[str, Any]) -> str:
    body = deepcopy(dict(payload or {}))
    body.pop("content_hash", None)
    return canonical_payload_hash(body)


def gameplay_command_idempotency_key(command_id: object, payload_hash: object) -> str:
    command = _required_text(command_id, "command_id")
    digest = _required_hash(payload_hash, "payload_hash")
    return canonical_payload_hash({"command_id": command, "payload_hash": digest})


def validate_gameplay_manifest_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("gameplay manifest payload must be a mapping")
    normalized = deepcopy(dict(payload))
    unknown = sorted(set(normalized) - _MANIFEST_FIELDS)
    missing = sorted(_MANIFEST_FIELDS - set(normalized))
    if unknown or missing:
        raise ValueError(
            "gameplay manifest fields mismatch: "
            f"missing={','.join(missing) or '-'} unknown={','.join(unknown) or '-'}"
        )
    if normalized.get("schema_version") != GAMEPLAY_MANIFEST_SCHEMA_VERSION:
        raise ValueError("gameplay manifest schema_version is incompatible")
    for field_name in ("project_id", "plan_id", "objective_id"):
        normalized[field_name] = _required_text(normalized.get(field_name), field_name)
    scene_version = normalized.get("scene_version")
    if isinstance(scene_version, bool) or not isinstance(scene_version, int) or scene_version <= 0:
        raise ValueError("gameplay manifest scene_version must be a positive int")

    bindings = normalized.get("entity_bindings")
    if not isinstance(bindings, list) or not bindings:
        raise ValueError("gameplay manifest entity_bindings must be a non-empty list")
    slot_ids: set[str] = set()
    entity_ids: set[str] = set()
    for index, raw_binding in enumerate(bindings):
        binding = _exact_mapping(raw_binding, _BINDING_FIELDS, f"entity_bindings[{index}]")
        slot_id = _required_text(binding.get("slot_id"), f"entity_bindings[{index}].slot_id")
        entity_id = _required_text(binding.get("entity_id"), f"entity_bindings[{index}].entity_id")
        _required_text(binding.get("semantic_role"), f"entity_bindings[{index}].semantic_role")
        _required_text(binding.get("asset_id"), f"entity_bindings[{index}].asset_id")
        entity_version = binding.get("entity_version")
        if isinstance(entity_version, bool) or not isinstance(entity_version, int) or entity_version <= 0:
            raise ValueError(f"entity_bindings[{index}].entity_version must be a positive int")
        _required_text_sequence(
            binding.get("required_capabilities"),
            f"entity_bindings[{index}].required_capabilities",
        )
        if slot_id in slot_ids or entity_id in entity_ids:
            raise ValueError("gameplay manifest bindings contain duplicate slot_id or entity_id")
        slot_ids.add(slot_id)
        entity_ids.add(entity_id)

    primitives = normalized.get("primitives")
    if not isinstance(primitives, list) or not primitives:
        raise ValueError("gameplay manifest primitives must be a non-empty list")
    primitive_ids: set[str] = set()
    completed_objectives: set[str] = set()
    for index, raw_primitive in enumerate(primitives):
        primitive = _exact_mapping(raw_primitive, _PRIMITIVE_FIELDS, f"primitives[{index}]")
        primitive_id = _required_text(primitive.get("primitive_id"), f"primitives[{index}].primitive_id")
        kind = _required_text(primitive.get("kind"), f"primitives[{index}].kind")
        subject_slot = _required_text(primitive.get("subject_slot"), f"primitives[{index}].subject_slot")
        target_slot = _required_text(primitive.get("target_slot"), f"primitives[{index}].target_slot")
        if primitive_id in primitive_ids:
            raise ValueError("gameplay manifest primitives contain duplicate primitive_id")
        if kind not in ALLOWED_GAMEPLAY_PRIMITIVES:
            raise ValueError(f"unsupported gameplay primitive: {kind}")
        if subject_slot not in slot_ids or target_slot not in slot_ids:
            raise ValueError("gameplay primitive references an unknown entity slot")
        parameters = primitive.get("parameters")
        if not isinstance(parameters, Mapping):
            raise TypeError(f"primitives[{index}].parameters must be a mapping")
        unknown_parameters = sorted(set(parameters) - GAMEPLAY_PRIMITIVE_PARAMETER_KEYS[kind])
        if unknown_parameters:
            raise ValueError(
                f"primitive {primitive_id} has unknown parameters: {','.join(map(str, unknown_parameters))}"
            )
        if kind == "set_state" and (
            not str(parameters.get("state_key") or "").strip() or "value" not in parameters
        ):
            raise ValueError("set_state requires state_key and value")
        if kind == "unlock" and not str(parameters.get("required_state") or "").strip():
            raise ValueError("unlock requires required_state")
        if kind == "complete_objective":
            completed_objectives.add(
                _required_text(parameters.get("objective_id"), "complete_objective.objective_id")
            )
        primitive_ids.add(primitive_id)
    if completed_objectives != {normalized["objective_id"]}:
        raise ValueError("complete_objective must match gameplay manifest objective_id")

    payload_hash = _required_hash(normalized.get("content_hash"), "content_hash")
    if gameplay_manifest_content_hash(normalized) != payload_hash:
        raise ValueError("gameplay manifest content_hash mismatch")
    return normalized


def _exact_mapping(value: object, fields: frozenset[str], path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{path} must be a mapping")
    result = dict(value)
    if set(result) != fields:
        raise ValueError(f"{path} fields mismatch")
    return result


def _required_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _required_hash(value: object, field_name: str) -> str:
    text = _required_text(value, field_name)
    if len(text) != 71 or not text.startswith("sha256:"):
        raise ValueError(f"{field_name} must be a sha256 digest")
    if any(ch not in "0123456789abcdef" for ch in text[7:]):
        raise ValueError(f"{field_name} must be a sha256 digest")
    return text


def _required_text_sequence(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a sequence")
    result = tuple(_required_text(item, field_name) for item in value)
    if not result:
        raise ValueError(f"{field_name} cannot be empty")
    return result


__all__ = [
    "ALLOWED_GAMEPLAY_PRIMITIVES",
    "GAMEPLAY_PRIMITIVE_PARAMETER_KEYS",
    "canonical_payload_hash",
    "gameplay_command_idempotency_key",
    "gameplay_manifest_content_hash",
    "validate_gameplay_manifest_payload",
]
