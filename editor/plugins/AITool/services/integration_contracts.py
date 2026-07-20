from __future__ import annotations

from dataclasses import MISSING, asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import inspect
import json
import re
from typing import Any, Literal, Protocol, get_type_hints

from .schema_versions import (
    COLLABORATION_SCHEMA_VERSION,
    ENGINE_ADAPTER_CONTRACT_VERSION,
    FRONTEND_INTERACTION_SCHEMA_VERSION,
    PLAN_PATCH_PAYLOAD_SCHEMA_VERSION,
    R3_GATE_SCHEMA_VERSION,
    SCENE_WORLD_SNAPSHOT_SCHEMA_VERSION,
    SKELETON_CONTRACT_VERSION,
)


OWNER_DOMAINS = frozenset({"ai_runtime", "engine", "frontend", "collaboration", "integration"})
BLOCKED_STATUSES = frozenset({"unavailable", "blocked", "pending_runtime_verification"})
NODE_STATUSES = frozenset({"ready", "completed", *BLOCKED_STATUSES, "stale"})
REPORT_STATUSES = frozenset({"completed", *BLOCKED_STATUSES})
INTERFACE_CHANGE_DECISIONS = frozenset({"accepted", "rejected", "no_contract_change"})
MACHINE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
CONTRACT_HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
PUBLIC_SCHEMA_VERSIONS = (
    ("collaboration", COLLABORATION_SCHEMA_VERSION),
    ("engine_adapter", ENGINE_ADAPTER_CONTRACT_VERSION),
    ("frontend_interaction", FRONTEND_INTERACTION_SCHEMA_VERSION),
    ("plan_patch_payload", PLAN_PATCH_PAYLOAD_SCHEMA_VERSION),
    ("r3_gate", R3_GATE_SCHEMA_VERSION),
    ("scene_world_snapshot", SCENE_WORLD_SNAPSHOT_SCHEMA_VERSION),
    ("skeleton", SKELETON_CONTRACT_VERSION),
)


def _required_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _machine_id(value: object, field_name: str) -> str:
    text = _required_text(value, field_name)
    if not MACHINE_ID_PATTERN.fullmatch(text):
        raise ValueError(f"{field_name} must be a stable machine identifier")
    return text


def _owner_domain(value: object, field_name: str = "owner_domain") -> str:
    owner = _required_text(value, field_name)
    if owner not in OWNER_DOMAINS:
        raise ValueError(f"{field_name} is unsupported: {owner}")
    return owner


def _text_tuple(values: object, field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, (tuple, list, set, frozenset)):
        raise TypeError(f"{field_name} must be a sequence of strings")
    normalized = tuple(str(value or "").strip() for value in values)
    if any(not value for value in normalized):
        raise ValueError(f"{field_name} cannot contain empty values")
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


def _contract_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalized_type_name(annotation: object) -> str:
    if annotation is inspect.Signature.empty:
        return "Any"
    if isinstance(annotation, str):
        return annotation
    return str(annotation).replace("typing.", "").replace("<class '", "").replace("'>", "")


def _normalized_default(value: object) -> str:
    if value is inspect.Signature.empty or value is MISSING:
        return ""
    if value is None or isinstance(value, (str, bool, int, float)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return repr(value)


@dataclass(frozen=True)
class MissingRequirement:
    requirement_id: str
    owner_domain: str
    description: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "requirement_id", _machine_id(self.requirement_id, "requirement_id"))
        object.__setattr__(self, "owner_domain", _owner_domain(self.owner_domain))
        object.__setattr__(self, "description", _required_text(self.description, "description"))


@dataclass(frozen=True)
class DemoReadinessRequirement:
    requirement_id: str
    semantic_role: str
    required_capabilities: tuple[str, ...]
    min_count: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "requirement_id", _machine_id(self.requirement_id, "requirement_id"))
        object.__setattr__(self, "semantic_role", _required_text(self.semantic_role, "semantic_role"))
        capabilities = tuple(
            sorted(set(_text_tuple(self.required_capabilities, "required_capabilities")))
        )
        object.__setattr__(self, "required_capabilities", capabilities)
        if int(self.min_count) <= 0:
            raise ValueError("min_count must be positive")
        object.__setattr__(self, "min_count", int(self.min_count))

    def as_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "semantic_role": self.semantic_role,
            "required_capabilities": list(self.required_capabilities),
            "min_count": self.min_count,
        }


@dataclass(frozen=True)
class BlockedResult:
    node_id: str
    status: Literal["unavailable", "blocked", "pending_runtime_verification"]
    error_code: str
    summary: str
    missing_requirements: tuple[MissingRequirement, ...]
    owner_domain: str
    retryable: bool
    next_action: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _machine_id(self.node_id, "node_id"))
        if self.status not in BLOCKED_STATUSES:
            raise ValueError(f"unsupported blocked status: {self.status}")
        object.__setattr__(self, "error_code", _machine_id(self.error_code, "error_code"))
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        requirements = tuple(self.missing_requirements)
        if not requirements or not all(isinstance(item, MissingRequirement) for item in requirements):
            raise ValueError("missing_requirements must contain MissingRequirement values")
        object.__setattr__(self, "missing_requirements", requirements)
        object.__setattr__(self, "owner_domain", _owner_domain(self.owner_domain))
        object.__setattr__(self, "retryable", bool(self.retryable))
        object.__setattr__(self, "next_action", _required_text(self.next_action, "next_action"))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs"))


@dataclass(frozen=True)
class SkeletonNodeStatus:
    node_id: str
    interface_name: str
    status: str
    blocker_code: str
    owner_domain: str
    fill_priority: int
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _machine_id(self.node_id, "node_id"))
        object.__setattr__(self, "interface_name", _required_text(self.interface_name, "interface_name"))
        if self.status not in NODE_STATUSES:
            raise ValueError(f"unsupported node status: {self.status}")
        blocker = str(self.blocker_code or "").strip()
        if self.status in BLOCKED_STATUSES or self.status == "stale":
            blocker = _machine_id(blocker, "blocker_code")
        object.__setattr__(self, "blocker_code", blocker)
        object.__setattr__(self, "owner_domain", _owner_domain(self.owner_domain))
        if int(self.fill_priority) <= 0:
            raise ValueError("fill_priority must be positive")
        object.__setattr__(self, "fill_priority", int(self.fill_priority))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs"))


@dataclass(frozen=True)
class PublicProtocolManifest:
    name: str
    methods: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "protocol.name"))
        object.__setattr__(self, "methods", _text_tuple(self.methods, "protocol.methods", allow_empty=False))


@dataclass(frozen=True)
class PublicDtoManifest:
    name: str
    fields: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "dto.name"))
        object.__setattr__(self, "fields", _text_tuple(self.fields, "dto.fields", allow_empty=False))


@dataclass(frozen=True)
class PublicEnumManifest:
    name: str
    values: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "enum.name"))
        object.__setattr__(self, "values", _text_tuple(self.values, "enum.values", allow_empty=False))


@dataclass(frozen=True)
class SkeletonContractManifest:
    contract_version: str
    schema_versions: tuple[tuple[str, str], ...]
    public_protocols: tuple[PublicProtocolManifest, ...]
    public_dtos: tuple[PublicDtoManifest, ...]
    public_enums: tuple[PublicEnumManifest, ...]
    skeleton_nodes: tuple[tuple[str, str], ...]
    skeleton_edges: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_version", _required_text(self.contract_version, "contract_version"))
        object.__setattr__(self, "schema_versions", tuple(sorted(self.schema_versions)))
        object.__setattr__(self, "public_protocols", tuple(sorted(self.public_protocols, key=lambda item: item.name)))
        object.__setattr__(self, "public_dtos", tuple(sorted(self.public_dtos, key=lambda item: item.name)))
        object.__setattr__(self, "public_enums", tuple(sorted(self.public_enums, key=lambda item: item.name)))
        nodes = tuple((str(node_id), str(interface_name)) for node_id, interface_name in self.skeleton_nodes)
        if not nodes or len({node_id for node_id, _ in nodes}) != len(nodes):
            raise ValueError("skeleton_nodes must contain unique nodes")
        for node_id, interface_name in nodes:
            _machine_id(node_id, "skeleton node_id")
            _required_text(interface_name, "skeleton interface_name")
        object.__setattr__(self, "skeleton_nodes", nodes)
        edges = tuple((str(source), str(target)) for source, target in self.skeleton_edges)
        node_ids = {node_id for node_id, _ in nodes}
        if any(source not in node_ids or target not in node_ids for source, target in edges):
            raise ValueError("skeleton_edges must reference declared nodes")
        object.__setattr__(self, "skeleton_edges", edges)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def contract_hash(self) -> str:
        return _contract_hash(self.as_dict())


@dataclass(frozen=True)
class SkeletonStatusReport:
    contract_version: str
    contract_hash: str
    nodes: tuple[SkeletonNodeStatus, ...]
    overall_status: str
    generated_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_version", _required_text(self.contract_version, "contract_version"))
        contract_hash = _required_text(self.contract_hash, "contract_hash")
        if not CONTRACT_HASH_PATTERN.fullmatch(contract_hash):
            raise ValueError("contract_hash must be sha256:<64 lowercase hex>")
        object.__setattr__(self, "contract_hash", contract_hash)
        nodes = tuple(sorted(self.nodes, key=lambda item: (item.fill_priority, item.node_id)))
        if not nodes or not all(isinstance(item, SkeletonNodeStatus) for item in nodes):
            raise ValueError("nodes must contain SkeletonNodeStatus values")
        if len({item.node_id for item in nodes}) != len(nodes):
            raise ValueError("nodes must have unique node_id values")
        object.__setattr__(self, "nodes", nodes)
        if self.overall_status not in REPORT_STATUSES:
            raise ValueError(f"unsupported report status: {self.overall_status}")
        generated_at = _required_text(self.generated_at, "generated_at")
        parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
            raise ValueError("generated_at must be ISO-8601 UTC")
        object.__setattr__(self, "generated_at", generated_at)


@dataclass(frozen=True)
class InterfaceChangeRequest:
    request_id: str
    node_id: str
    detected_by_task_id: str
    current_contract_version: str
    current_contract_hash: str
    reason_code: str
    required_change: str
    affected_interfaces: tuple[str, ...]
    blocked_dependents: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _machine_id(self.request_id, "request_id"))
        object.__setattr__(self, "node_id", _machine_id(self.node_id, "node_id"))
        object.__setattr__(self, "detected_by_task_id", _machine_id(self.detected_by_task_id, "detected_by_task_id"))
        object.__setattr__(self, "current_contract_version", _required_text(self.current_contract_version, "current_contract_version"))
        if not CONTRACT_HASH_PATTERN.fullmatch(str(self.current_contract_hash or "")):
            raise ValueError("current_contract_hash is invalid")
        object.__setattr__(self, "reason_code", _machine_id(self.reason_code, "reason_code"))
        object.__setattr__(self, "required_change", _required_text(self.required_change, "required_change"))
        object.__setattr__(self, "affected_interfaces", _text_tuple(self.affected_interfaces, "affected_interfaces", allow_empty=False))
        object.__setattr__(self, "blocked_dependents", _text_tuple(self.blocked_dependents, "blocked_dependents"))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs", allow_empty=False))


@dataclass(frozen=True)
class InterfaceChangeDecision:
    decision: Literal["accepted", "rejected", "no_contract_change"]
    reason: str
    changed_interfaces: tuple[str, ...]
    new_contract_version: str
    new_contract_hash: str
    affected_nodes: tuple[str, ...]
    required_revalidation: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.decision not in INTERFACE_CHANGE_DECISIONS:
            raise ValueError(f"unsupported interface change decision: {self.decision}")
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        object.__setattr__(self, "changed_interfaces", _text_tuple(self.changed_interfaces, "changed_interfaces"))
        object.__setattr__(self, "new_contract_version", _required_text(self.new_contract_version, "new_contract_version"))
        if not CONTRACT_HASH_PATTERN.fullmatch(str(self.new_contract_hash or "")):
            raise ValueError("new_contract_hash is invalid")
        object.__setattr__(self, "affected_nodes", _text_tuple(self.affected_nodes, "affected_nodes"))
        object.__setattr__(self, "required_revalidation", _text_tuple(self.required_revalidation, "required_revalidation"))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs", allow_empty=False))
        if self.decision == "accepted" and (not self.changed_interfaces or not self.required_revalidation):
            raise ValueError("accepted interface changes require changed interfaces and revalidation")


def protocol_manifest(protocol_type: type[Protocol]) -> PublicProtocolManifest:
    methods: list[str] = []
    for name, value in protocol_type.__dict__.items():
        if name.startswith("_") or not callable(value):
            continue
        signature = inspect.signature(value)
        hints = get_type_hints(value)
        parameters: list[str] = []
        for parameter in signature.parameters.values():
            annotation = hints.get(parameter.name, parameter.annotation)
            rendered = f"{parameter.name}:{_normalized_type_name(annotation)}"
            default = _normalized_default(parameter.default)
            if default:
                rendered += f"={default}"
            parameters.append(rendered)
        return_type = _normalized_type_name(hints.get("return", signature.return_annotation))
        methods.append(f"{name}({','.join(parameters)})->{return_type}")
    return PublicProtocolManifest(protocol_type.__name__, tuple(methods))


def dto_manifest(dto_type: type) -> PublicDtoManifest:
    if not is_dataclass(dto_type):
        raise TypeError("dto_manifest requires a dataclass type")
    hints = get_type_hints(dto_type)
    rendered_fields: list[str] = []
    for field in fields(dto_type):
        rendered = f"{field.name}:{_normalized_type_name(hints.get(field.name, field.type))}"
        if field.default is not MISSING:
            rendered += f"={_normalized_default(field.default)}"
        elif field.default_factory is not MISSING:  # type: ignore[comparison-overlap]
            rendered += "=<factory>"
        rendered_fields.append(rendered)
    return PublicDtoManifest(dto_type.__name__, tuple(rendered_fields))


def default_skeleton_contract_version() -> str:
    return SKELETON_CONTRACT_VERSION
