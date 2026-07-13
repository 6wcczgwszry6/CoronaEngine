"""Deterministic, read-only R3 readiness gate aggregation.

The evaluator in this module consumes already-materialized Runtime facts.  It
does not know about collaboration Artifacts and must never mutate RuntimeState,
OperationLog, ToolCallGraph, or the Engine.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from .scene_world_consistency import scene_world_fingerprint


R3_DIMENSION_NAMES = (
    "snapshot_integrity",
    "environment_readiness",
    "entity_readiness",
    "finalizer_completeness",
    "business_graph_consistency",
    "multiplayer_consistency",
    "runtime_write_safety",
)
R3_GATE_STATES = frozenset({"red", "yellow", "green"})


def _stable_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _stable_rows(value: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    return [dict(item) for item in list(value or []) if isinstance(item, Mapping)]


def _unique_text(values: Sequence[Any]) -> list[str]:
    return sorted({str(value or "").strip() for value in values if str(value or "").strip()})


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class R3GateDimension:
    name: str
    status: str
    summary: str
    metrics: Mapping[str, Any]
    missing: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "metrics": dict(self.metrics),
            "missing": list(self.missing),
            "contradictions": list(self.contradictions),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class R3GateReport:
    gate_report_id: str
    room_id: str
    plan_id: str
    scene_version: int
    overall: str
    dimensions: Mapping[str, R3GateDimension]
    metrics: Mapping[str, Any]
    blockers: tuple[str, ...]
    capability_unlocks: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    evaluated_at: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_report_id": self.gate_report_id,
            "room_id": self.room_id,
            "plan_id": self.plan_id,
            "scene_version": self.scene_version,
            "overall": self.overall,
            "dimensions": {
                name: self.dimensions[name].as_dict()
                for name in R3_DIMENSION_NAMES
            },
            "metrics": dict(self.metrics),
            "blockers": list(self.blockers),
            "capability_unlocks": list(self.capability_unlocks),
            "evidence_refs": list(self.evidence_refs),
            "evaluated_at": self.evaluated_at,
        }


class R3GateReportValidator:
    """Validate the stable public R3 gate contract."""

    @staticmethod
    def validate(report: R3GateReport | Mapping[str, Any]) -> None:
        data = report.as_dict() if isinstance(report, R3GateReport) else dict(report or {})
        required = {
            "gate_report_id",
            "room_id",
            "plan_id",
            "scene_version",
            "overall",
            "dimensions",
            "metrics",
            "blockers",
            "capability_unlocks",
            "evidence_refs",
            "evaluated_at",
        }
        if set(data) != required:
            raise ValueError("R3GateReport fields do not match the public schema")
        if str(data.get("overall") or "") not in R3_GATE_STATES:
            raise ValueError("R3GateReport overall must be red, yellow, or green")
        if not str(data.get("gate_report_id") or "").startswith("r3gate-"):
            raise ValueError("R3GateReport gate_report_id is invalid")
        if not str(data.get("room_id") or "").strip():
            raise ValueError("R3GateReport room_id is required")
        if _safe_int(data.get("scene_version"), -1) < 0:
            raise ValueError("R3GateReport scene_version must be non-negative")
        dimensions = data.get("dimensions")
        if not isinstance(dimensions, Mapping) or set(dimensions.keys()) != set(R3_DIMENSION_NAMES):
            raise ValueError("R3GateReport must contain the seven ordered R3 dimensions")
        for name in R3_DIMENSION_NAMES:
            row = dimensions.get(name)
            if not isinstance(row, Mapping):
                raise ValueError(f"R3 dimension {name} must be a mapping")
            if str(row.get("name") or "") != name:
                raise ValueError(f"R3 dimension {name} has a mismatched name")
            if str(row.get("status") or "") not in R3_GATE_STATES:
                raise ValueError(f"R3 dimension {name} has an invalid status")
            for list_field in ("missing", "contradictions", "evidence_refs"):
                if not isinstance(row.get(list_field), list):
                    raise ValueError(f"R3 dimension {name}.{list_field} must be a list")
            if not isinstance(row.get("metrics"), Mapping):
                raise ValueError(f"R3 dimension {name}.metrics must be a mapping")
        for list_field in ("blockers", "capability_unlocks", "evidence_refs"):
            if not isinstance(data.get(list_field), list):
                raise ValueError(f"R3GateReport {list_field} must be a list")


def _dimension(
    name: str,
    status: str,
    summary: str,
    *,
    metrics: Mapping[str, Any],
    missing: Sequence[Any] = (),
    contradictions: Sequence[Any] = (),
    evidence_refs: Sequence[Any] = (),
) -> R3GateDimension:
    return R3GateDimension(
        name=name,
        status=status,
        summary=summary,
        metrics=dict(metrics),
        missing=tuple(_unique_text(list(missing))),
        contradictions=tuple(_unique_text(list(contradictions))),
        evidence_refs=tuple(_unique_text(list(evidence_refs))),
    )


def _snapshot_dimension(
    snapshot_result: Mapping[str, Any],
    consistency_audit: Mapping[str, Any],
) -> R3GateDimension:
    result = _stable_mapping(snapshot_result)
    snapshot = _stable_mapping(result.get("snapshot"))
    entities = _stable_rows(snapshot.get("environment_entities")) + _stable_rows(
        snapshot.get("actor_entities")
    )
    plan_id = str(snapshot.get("plan_id") or result.get("plan_id") or "")
    scene_version = max(0, _safe_int(snapshot.get("scene_version") or result.get("scene_version")))
    fingerprint = str(snapshot.get("world_fingerprint") or result.get("world_fingerprint") or "")
    computed_fingerprint = (
        scene_world_fingerprint(entities, plan_id=plan_id, scene_version=scene_version)
        if plan_id and scene_version > 0
        else ""
    )
    stability = str(result.get("snapshot_stability") or "")
    authority = str(result.get("snapshot_authority") or snapshot.get("snapshot_authority") or "")
    audit = _stable_mapping(consistency_audit)
    engine_available = bool(audit.get("engine_snapshot_available"))
    audit_consistent = bool(audit.get("fingerprints_match")) and str(audit.get("status") or "") == "consistent"
    missing: list[str] = []
    contradictions: list[str] = []
    if not result.get("found"):
        missing.append("scene_world_snapshot")
    if not fingerprint:
        missing.append("world_fingerprint")
    if fingerprint and computed_fingerprint and fingerprint != computed_fingerprint:
        contradictions.append("world_fingerprint_mismatch")
    if authority == "local_runtime" and stability != "immutable":
        contradictions.append("snapshot_not_immutable")
    if authority == "peer_mirror" and stability != "peer_mirror":
        contradictions.append("peer_snapshot_stability_mismatch")
    if engine_available and not audit_consistent:
        contradictions.append("engine_snapshot_fingerprint_mismatch")
    if not missing and not contradictions and engine_available and audit_consistent and stability == "immutable":
        status = "green"
        summary = "Immutable Runtime and Engine snapshots have matching fingerprints."
    elif missing or contradictions:
        status = "red"
        summary = "Snapshot identity is missing, provisional, or contradictory."
    else:
        status = "yellow"
        summary = "Snapshot is deterministic, but authoritative Engine comparison is incomplete."
    return _dimension(
        "snapshot_integrity",
        status,
        summary,
        metrics={
            "found": bool(result.get("found")),
            "scene_version": scene_version,
            "snapshot_stability": stability,
            "snapshot_authority": authority,
            "entity_count": len(entities),
            "fingerprint_matches_payload": bool(fingerprint and fingerprint == computed_fingerprint),
            "engine_snapshot_available": engine_available,
            "engine_fingerprints_match": bool(audit.get("fingerprints_match")),
        },
        missing=missing,
        contradictions=contradictions,
        evidence_refs=[f"SceneWorldSnapshot:{plan_id}@v{scene_version}"],
    )


def _environment_dimension(
    snapshot_result: Mapping[str, Any],
    required_environment_components: Sequence[Any],
) -> R3GateDimension:
    snapshot = _stable_mapping(_stable_mapping(snapshot_result).get("snapshot"))
    entities = _stable_rows(snapshot.get("environment_entities"))
    required = _unique_text(list(required_environment_components))
    by_type: dict[str, list[dict[str, Any]]] = {}
    for entity in entities:
        component_type = str(
            entity.get("component_type")
            or entity.get("environment_component_type")
            or entity.get("semantic_role")
            or ""
        ).strip()
        if component_type:
            by_type.setdefault(component_type, []).append(entity)
    missing = [item for item in required if item not in by_type]
    not_ready = [
        item
        for item in required
        if item in by_type and not any(bool(row.get("game_ready")) for row in by_type[item])
    ]
    if not required:
        status = "red"
        missing.append("required_environment_components")
        summary = "The plan does not define its required environment components."
    elif missing or not_ready:
        status = "red"
        summary = "One or more required environment components are missing or not Engine-ready."
    else:
        status = "green"
        summary = "All required environment components are present and Game-ready."
    return _dimension(
        "environment_readiness",
        status,
        summary,
        metrics={
            "required_count": len(required),
            "present_count": sum(1 for item in required if item in by_type),
            "ready_count": sum(
                1 for item in required if any(bool(row.get("game_ready")) for row in by_type.get(item, []))
            ),
            "environment_entity_count": len(entities),
            "required_components": required,
        },
        missing=missing,
        contradictions=[f"environment_not_ready:{item}" for item in not_ready],
        evidence_refs=["SceneWorldSnapshot.environment_entities"],
    )


def _entity_dimension(
    registry: Mapping[str, Any],
    *,
    benchmark_profile: str,
    expected_entity_count: int,
) -> R3GateDimension:
    data = _stable_mapping(registry)
    entities = _stable_rows(data.get("entities"))
    entity_count = len(entities)
    game_ready_count = sum(1 for entity in entities if bool(entity.get("game_ready")))
    denominator = max(entity_count, max(0, expected_entity_count))
    ratio = round(game_ready_count / float(denominator), 4) if denominator else 0.0
    ids = [str(entity.get("entity_id") or "").strip() for entity in entities]
    duplicate_ids = sorted({entity_id for entity_id in ids if entity_id and ids.count(entity_id) > 1})
    missing: list[str] = []
    contradictions: list[str] = []
    partial_without_reasons = 0
    for index, entity in enumerate(entities):
        entity_ref = str(entity.get("entity_id") or f"entity[{index}]")
        if not str(entity.get("entity_id") or "").strip():
            missing.append(f"{entity_ref}:entity_id")
        if not str(entity.get("asset_id") or entity.get("model_ref") or "").strip():
            missing.append(f"{entity_ref}:asset_identity")
        if str(entity.get("entity_type") or "") not in {"environment", "substrate"} and not str(
            entity.get("actor_id") or ""
        ).strip():
            missing.append(f"{entity_ref}:actor_id")
        if _safe_int(entity.get("version"), 0) <= 0:
            missing.append(f"{entity_ref}:version")
        if not bool(entity.get("game_ready")) and not list(entity.get("readiness_missing_fields") or []):
            partial_without_reasons += 1
    contradictions.extend(f"duplicate_entity_id:{entity_id}" for entity_id in duplicate_ids)
    if partial_without_reasons:
        contradictions.append("needs_review_entities_without_missing_fields")
    profile = str(benchmark_profile or "generic").strip().lower()
    if profile == "bedroom_14":
        if game_ready_count >= 8:
            threshold_status = "green"
        elif game_ready_count >= 5:
            threshold_status = "yellow"
        else:
            threshold_status = "red"
    elif ratio >= 0.60:
        threshold_status = "green"
    elif ratio >= 0.35:
        threshold_status = "yellow"
    else:
        threshold_status = "red"
    status = "red" if missing or contradictions else threshold_status
    summary = (
        "Entity identities are contradictory or incomplete."
        if missing or contradictions
        else f"{game_ready_count}/{denominator} expected entities are Game-ready."
    )
    return _dimension(
        "entity_readiness",
        status,
        summary,
        metrics={
            "benchmark_profile": profile,
            "entity_count": entity_count,
            "expected_entity_count": denominator,
            "game_ready_entity_count": game_ready_count,
            "needs_review_entity_count": max(0, entity_count - game_ready_count),
            "game_ready_ratio": ratio,
            "identity_complete_count": max(0, entity_count - len({item.split(":", 1)[0] for item in missing})),
            "partial_without_missing_fields_count": partial_without_reasons,
            "readiness_missing_field_counts": dict(data.get("readiness_missing_field_counts") or {}),
        },
        missing=missing,
        contradictions=contradictions,
        evidence_refs=["scene_entity_registry"],
    )


def _finalizer_dimension(
    operation_entries: Sequence[Mapping[str, Any]],
    runtime_events: Sequence[Mapping[str, Any]],
) -> R3GateDimension:
    required = (
        "finalizer_started",
        "tool_graph_queue_empty",
        "scene_plan_finalized",
        "scene_entity_registry_ready",
        "runtime_scene_world_consistency_audited",
        "scene_world_snapshot_ready",
        "report_ready",
    )
    timeline: list[tuple[float, int, str]] = []
    ordinal = 0
    for entry in _stable_rows(operation_entries):
        event = str(entry.get("event") or "")
        if event in required:
            timeline.append((float(entry.get("timestamp") or 0.0), ordinal, event))
            ordinal += 1
    for entry in _stable_rows(runtime_events):
        event = str(entry.get("event_type") or entry.get("event") or "")
        if event == "report_ready":
            timeline.append((float(entry.get("timestamp") or 0.0), ordinal, event))
            ordinal += 1
    timeline.sort(key=lambda item: (item[0], item[1]))
    last_positions: dict[str, int] = {}
    for index, (_, _, event) in enumerate(timeline):
        last_positions[event] = index
    missing = [event for event in required if event not in last_positions]
    ordered = not missing and [last_positions[event] for event in required] == sorted(
        last_positions[event] for event in required
    )
    contradictions = [] if ordered or missing else ["finalizer_event_order_invalid"]
    status = "green" if not missing and ordered else "red"
    return _dimension(
        "finalizer_completeness",
        status,
        "Finalizer terminal events are complete and ordered."
        if status == "green"
        else "Finalizer terminal evidence is incomplete or out of order.",
        metrics={
            "required_event_count": len(required),
            "observed_event_count": len(last_positions),
            "ordered": ordered,
            "observed_events": [event for _, _, event in timeline],
        },
        missing=missing,
        contradictions=contradictions,
        evidence_refs=["OperationLog.finalizer", "RuntimeState.runtime_events.report_ready"],
    )


def _business_graph_dimension(
    batches: Sequence[Mapping[str, Any]],
    graphs: Sequence[Mapping[str, Any]],
) -> R3GateDimension:
    batch_rows = _stable_rows(batches)
    graph_rows = _stable_rows(graphs)
    referenced_ids = {
        str(batch.get("tool_graph_id") or "").strip()
        for batch in batch_rows
        if str(batch.get("tool_graph_id") or "").strip()
    }
    business_graphs = [
        graph
        for graph in graph_rows
        if str(graph.get("graph_role") or "") == "business_batch"
        or str(graph.get("graph_id") or "") in referenced_ids
    ]
    graph_by_id = {
        str(graph.get("graph_id") or ""): graph
        for graph in business_graphs
        if str(graph.get("graph_id") or "")
    }
    missing: list[str] = []
    contradictions: list[str] = []
    terminal_batch_statuses = {"completed", "failed", "cancelled", "abandoned", "partial"}
    terminal_graph_statuses = {"completed", "failed", "cancelled", "abandoned", "skipped"}
    for batch in batch_rows:
        batch_id = str(batch.get("batch_id") or "")
        graph_id = str(batch.get("tool_graph_id") or "").strip()
        if not graph_id:
            missing.append(f"{batch_id}:tool_graph_id")
            continue
        graph = graph_by_id.get(graph_id)
        if graph is None:
            missing.append(f"{batch_id}:business_graph")
            continue
        if str(graph.get("batch_id") or "") != batch_id:
            contradictions.append(f"{batch_id}:graph_batch_mismatch")
        if str(batch.get("status") or "") not in terminal_batch_statuses:
            contradictions.append(f"{batch_id}:batch_not_terminal")
        if str(graph.get("status") or "") not in terminal_graph_statuses:
            contradictions.append(f"{batch_id}:graph_not_terminal")
    orphan_graphs = [
        str(graph.get("graph_id") or "")
        for graph in business_graphs
        if str(graph.get("graph_id") or "") not in referenced_ids
    ]
    contradictions.extend(f"orphan_business_graph:{graph_id}" for graph_id in orphan_graphs if graph_id)
    if not batch_rows:
        missing.append("business_batches")
    status = "green" if not missing and not contradictions and len(batch_rows) == len(business_graphs) else "red"
    if len(batch_rows) != len(business_graphs):
        contradictions.append("business_batch_graph_count_mismatch")
        status = "red"
    return _dimension(
        "business_graph_consistency",
        status,
        "Every business batch has exactly one terminal business ToolCallGraph."
        if status == "green"
        else "Business BatchPlan and ToolCallGraph facts do not reconcile.",
        metrics={
            "business_batch_count": len(batch_rows),
            "business_graph_count": len(business_graphs),
            "terminal_batch_count": sum(
                1 for batch in batch_rows if str(batch.get("status") or "") in terminal_batch_statuses
            ),
            "terminal_graph_count": sum(
                1 for graph in business_graphs if str(graph.get("status") or "") in terminal_graph_statuses
            ),
        },
        missing=missing,
        contradictions=contradictions,
        evidence_refs=["RuntimeState.batch_plans", "RuntimeState.tool_graphs:business_batch"],
    )


def _multiplayer_dimension(multiplayer_evidence: Mapping[str, Any]) -> R3GateDimension:
    evidence = _stable_mapping(multiplayer_evidence)
    applicable = bool(evidence.get("applicable"))
    drift_count = _safe_int(evidence.get("identity_drift_count")) + _safe_int(
        evidence.get("version_drift_count")
    )
    partial_count = _safe_int(evidence.get("partial_entity_count"))
    verified_count = _safe_int(evidence.get("verified_entity_count"))
    entity_count = _safe_int(evidence.get("entity_count"))
    missing_fields_explicit = bool(evidence.get("missing_fields_explicit", True))
    contradictions: list[str] = []
    missing: list[str] = []
    if drift_count:
        contradictions.append("multiplayer_entity_or_version_drift")
    if partial_count and not missing_fields_explicit:
        contradictions.append("partial_peer_entities_without_missing_fields")
    if not applicable:
        status = "yellow"
        missing.append("host_peer_consistency_evidence")
        summary = "No authoritative host/peer comparison is available yet."
    elif contradictions:
        status = "red"
        summary = "Host and peer entity identity facts are contradictory."
    elif entity_count > 0 and verified_count >= entity_count and partial_count == 0:
        status = "green"
        summary = "Host and peer entity identities and versions are consistent."
    else:
        status = "yellow"
        summary = "Peer identities are stable, but some synchronized facts remain partial."
    return _dimension(
        "multiplayer_consistency",
        status,
        summary,
        metrics={
            "applicable": applicable,
            "peer_count": _safe_int(evidence.get("peer_count")),
            "entity_count": entity_count,
            "verified_entity_count": verified_count,
            "partial_entity_count": partial_count,
            "identity_drift_count": _safe_int(evidence.get("identity_drift_count")),
            "version_drift_count": _safe_int(evidence.get("version_drift_count")),
            "missing_fields_explicit": missing_fields_explicit,
        },
        missing=missing,
        contradictions=contradictions,
        evidence_refs=["RuntimeState.sync_state", "RuntimeState.sync_events"],
    )


def _write_safety_dimension(
    registry: Mapping[str, Any],
    engine_write_summary: Mapping[str, Any],
    operation_entries: Sequence[Mapping[str, Any]],
) -> R3GateDimension:
    registry_data = _stable_mapping(registry)
    summary = _stable_mapping(engine_write_summary)
    materialized_count = _safe_int(registry_data.get("engine_write_verified_count"))
    boundary_count = _safe_int(summary.get("boundary_fact_count"))
    bypass_events = [
        str(entry.get("event") or "")
        for entry in _stable_rows(operation_entries)
        if str(entry.get("event") or "") in {
            "runtime_guard_bypassed",
            "engine_write_gate_bypassed",
            "direct_engine_write_detected",
        }
    ]
    runtime_state_only_count = sum(
        1
        for entity in _stable_rows(registry_data.get("entities"))
        if str(entity.get("engine_write_verification_status") or "") in {
            "runtime_state_only",
            "pending_f5",
        }
    )
    missing: list[str] = []
    contradictions: list[str] = []
    if bypass_events:
        contradictions.extend(bypass_events)
    if materialized_count > 0 and boundary_count <= 0:
        contradictions.append("engine_write_boundary_missing")
    if runtime_state_only_count:
        contradictions.append("runtime_state_only_engine_write_claim")
    if contradictions:
        status = "red"
        text = "Engine materialization includes an unsafe or unverifiable write path."
    elif materialized_count <= 0:
        status = "yellow"
        missing.append("verified_engine_write")
        text = "No verified Engine write is available for this plan yet."
    else:
        status = "green"
        text = "Verified Engine writes are covered by Runtime write-boundary facts."
    return _dimension(
        "runtime_write_safety",
        status,
        text,
        metrics={
            "engine_verified_entity_count": materialized_count,
            "boundary_fact_count": boundary_count,
            "bridge_call_count": _safe_int(summary.get("bridge_call_count")),
            "bridge_success_count": _safe_int(summary.get("bridge_success_count")),
            "bridge_failed_count": _safe_int(summary.get("bridge_failed_count")),
            "runtime_state_only_count": runtime_state_only_count,
        },
        missing=missing,
        contradictions=contradictions,
        evidence_refs=["RuntimeGuard", "EngineWriteGate", "RuntimeState.engine_write_boundary"],
    )


def evaluate_r3_gate(
    *,
    room_id: str,
    plan_id: str,
    scene_version: int,
    snapshot_result: Mapping[str, Any],
    consistency_audit: Mapping[str, Any],
    scene_entity_registry: Mapping[str, Any],
    required_environment_components: Sequence[Any],
    batch_plans: Sequence[Mapping[str, Any]],
    tool_graphs: Sequence[Mapping[str, Any]],
    operation_entries: Sequence[Mapping[str, Any]],
    runtime_events: Sequence[Mapping[str, Any]],
    engine_write_summary: Mapping[str, Any],
    multiplayer_evidence: Mapping[str, Any],
    state_version: int,
    benchmark_profile: str = "generic",
    expected_entity_count: int = 0,
    evaluated_at: float = 0.0,
) -> R3GateReport:
    """Build one deterministic R3GateReport from immutable fact snapshots."""

    dimensions = {
        "snapshot_integrity": _snapshot_dimension(snapshot_result, consistency_audit),
        "environment_readiness": _environment_dimension(
            snapshot_result, required_environment_components
        ),
        "entity_readiness": _entity_dimension(
            scene_entity_registry,
            benchmark_profile=benchmark_profile,
            expected_entity_count=max(0, int(expected_entity_count or 0)),
        ),
        "finalizer_completeness": _finalizer_dimension(operation_entries, runtime_events),
        "business_graph_consistency": _business_graph_dimension(batch_plans, tool_graphs),
        "multiplayer_consistency": _multiplayer_dimension(multiplayer_evidence),
        "runtime_write_safety": _write_safety_dimension(
            scene_entity_registry, engine_write_summary, operation_entries
        ),
    }
    statuses = [dimensions[name].status for name in R3_DIMENSION_NAMES]
    overall = "red" if "red" in statuses else "green" if all(status == "green" for status in statuses) else "yellow"
    blockers = _unique_text(
        [
            f"{name}:{item}"
            for name in R3_DIMENSION_NAMES
            for item in (*dimensions[name].missing, *dimensions[name].contradictions)
        ]
    )
    if overall == "red":
        capability_unlocks = ("runtime_repair", "artifact_contract_development")
    elif overall == "yellow":
        capability_unlocks = (
            "runtime_repair",
            "artifact_contract_development",
            "planning_artifacts",
            "art_artifacts",
            "gameplay_logic_plan",
            "readonly_snapshot_analysis",
        )
    else:
        capability_unlocks = (
            "snapshot_v1_freeze",
            "entity_binding_plan",
            "collaboration_coordinator",
            "project_gate",
            "action_proposal",
        )
    evidence_refs = _unique_text(
        [
            f"RuntimeState@v{max(0, int(state_version))}",
            f"OperationLog@op:{len(list(operation_entries or []))}",
            f"SceneWorldSnapshot:{plan_id}@v{max(0, int(scene_version))}",
            *[
                ref
                for name in R3_DIMENSION_NAMES
                for ref in dimensions[name].evidence_refs
            ],
        ]
    )
    registry = _stable_mapping(scene_entity_registry)
    report_body = {
        "room_id": str(room_id),
        "plan_id": str(plan_id),
        "scene_version": max(0, int(scene_version)),
        "overall": overall,
        "dimensions": {name: dimensions[name].as_dict() for name in R3_DIMENSION_NAMES},
        "metrics": {
            "state_version": max(0, int(state_version)),
            "entity_count": _safe_int(registry.get("entity_count")),
            "game_ready_entity_count": _safe_int(registry.get("game_ready_entity_count")),
            "dimension_status_counts": {
                status: statuses.count(status) for status in ("red", "yellow", "green")
            },
        },
        "blockers": blockers,
        "capability_unlocks": list(capability_unlocks),
        "evidence_refs": evidence_refs,
        "evaluated_at": float(evaluated_at or 0.0),
    }
    gate_report_id = "r3gate-" + hashlib.sha256(_canonical_json(report_body).encode("utf-8")).hexdigest()[:16]
    report = R3GateReport(
        gate_report_id=gate_report_id,
        room_id=str(room_id),
        plan_id=str(plan_id),
        scene_version=max(0, int(scene_version)),
        overall=overall,
        dimensions=dimensions,
        metrics=report_body["metrics"],
        blockers=tuple(blockers),
        capability_unlocks=tuple(capability_unlocks),
        evidence_refs=tuple(evidence_refs),
        evaluated_at=float(evaluated_at or 0.0),
    )
    R3GateReportValidator.validate(report)
    return report


__all__ = [
    "R3_DIMENSION_NAMES",
    "R3GateDimension",
    "R3GateReport",
    "R3GateReportValidator",
    "evaluate_r3_gate",
]
