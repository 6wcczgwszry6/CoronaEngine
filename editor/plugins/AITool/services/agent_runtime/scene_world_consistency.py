"""Read-only consistency checks between Runtime world and Engine snapshots."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from typing import Any, Mapping


def _text(value: Any) -> str:
    return str(value or "").strip()


def _version(row: Mapping[str, Any]) -> int:
    for key in ("entity_version", "actor_version", "version"):
        try:
            value = int(row.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0


def _duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if value and count > 1)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    return value


def _transform(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("transform")
    if not isinstance(raw, Mapping):
        raw = row.get("geometry")
    source = dict(raw) if isinstance(raw, Mapping) else {}
    result: dict[str, Any] = {}
    for key in ("position", "rotation", "scale"):
        value = source.get(key)
        if value is None:
            value = row.get(key)
        if isinstance(value, (list, tuple)):
            result[key] = _canonical_value(value)
    return result


def _world_aabb(row: Mapping[str, Any]) -> Any:
    for key in ("world_aabb", "aabb", "bounds"):
        value = row.get(key)
        if isinstance(value, Mapping):
            minimum = value.get("min")
            maximum = value.get("max")
            if isinstance(minimum, (list, tuple)) and isinstance(maximum, (list, tuple)):
                return {
                    "min": _canonical_value(list(minimum)[:3]),
                    "max": _canonical_value(list(maximum)[:3]),
                }
            return _canonical_value(value)
        if isinstance(value, (list, tuple)):
            values = list(value)
            if len(values) >= 6:
                return {
                    "min": _canonical_value(values[:3]),
                    "max": _canonical_value(values[3:6]),
                }
            if (
                len(values) == 2
                and isinstance(values[0], (list, tuple))
                and isinstance(values[1], (list, tuple))
            ):
                return {
                    "min": _canonical_value(list(values[0])[:3]),
                    "max": _canonical_value(list(values[1])[:3]),
                }
            return _canonical_value(values)
    return None


def scene_world_fingerprint(
    entities: list[Mapping[str, Any]],
    *,
    plan_id: str,
    scene_version: int,
) -> str:
    """Build an order-independent digest from downstream-consumable world facts."""

    facts: list[dict[str, Any]] = []
    for row in entities:
        facts.append({
            "entity_id": _text(row.get("entity_id")),
            "actor_id": _text(row.get("actor_id")),
            "asset_id": _text(row.get("asset_id")),
            "model_ref": _text(row.get("model_ref")),
            "version": _version(row),
            "transform": _transform(row),
            "world_aabb": _world_aabb(row),
        })
    facts.sort(key=lambda item: (item["entity_id"], item["actor_id"], item["asset_id"]))
    payload = {
        "plan_id": _text(plan_id),
        "scene_version": int(scene_version or 0),
        "entities": facts,
    }
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def latest_engine_snapshot(
    snapshots: Mapping[str, Any],
    *,
    plan_id: str,
) -> dict[str, Any]:
    candidates: list[tuple[float, int, dict[str, Any]]] = []
    for index, raw in enumerate(dict(snapshots or {}).values()):
        if not isinstance(raw, Mapping):
            continue
        snapshot = dict(raw)
        snapshot_plan_id = _text(snapshot.get("plan_id"))
        if snapshot_plan_id and snapshot_plan_id != plan_id:
            continue
        try:
            timestamp = float(snapshot.get("timestamp") or 0.0)
        except (TypeError, ValueError):
            timestamp = 0.0
        candidates.append((timestamp, index, snapshot))
    if not candidates:
        return {}
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def audit_scene_world_consistency(
    *,
    world_snapshot: Mapping[str, Any],
    engine_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare stable identities only; never infer identity from names or paths."""

    plan_id = _text(world_snapshot.get("plan_id"))
    scene_version = int(world_snapshot.get("scene_version") or 0)
    world_entities = [
        dict(row)
        for row in (
            list(world_snapshot.get("environment_entities") or [])
            + list(world_snapshot.get("actor_entities") or [])
        )
        if isinstance(row, Mapping)
    ]
    expected_entities = [row for row in world_entities if _text(row.get("actor_id"))]
    engine_actors = [
        dict(row)
        for row in list(engine_snapshot.get("actors") or [])
        if isinstance(row, Mapping)
    ]

    world_ids = [_text(row.get("entity_id")) for row in expected_entities]
    engine_ids = [_text(row.get("entity_id")) for row in engine_actors]
    duplicate_world_ids = _duplicates(world_ids)
    duplicate_engine_ids = _duplicates(engine_ids)
    world_by_id = {entity_id: row for entity_id, row in zip(world_ids, expected_entities) if entity_id}
    engine_by_id = {entity_id: row for entity_id, row in zip(engine_ids, engine_actors) if entity_id}

    missing_world_identity = sorted(
        _text(row.get("actor_id")) for row in expected_entities if not _text(row.get("entity_id"))
    )
    unidentified_engine_actors = sorted(
        _text(row.get("actor_id")) for row in engine_actors if not _text(row.get("entity_id"))
    )
    missing_in_engine = sorted(set(world_by_id) - set(engine_by_id))
    unexpected_in_engine = sorted(set(engine_by_id) - set(world_by_id))

    actor_id_mismatches: list[dict[str, Any]] = []
    asset_id_mismatches: list[dict[str, Any]] = []
    model_ref_mismatches: list[dict[str, Any]] = []
    version_mismatches: list[dict[str, Any]] = []
    transform_mismatches: list[dict[str, Any]] = []
    world_aabb_mismatches: list[dict[str, Any]] = []
    for entity_id in sorted(set(world_by_id) & set(engine_by_id)):
        expected = world_by_id[entity_id]
        actual = engine_by_id[entity_id]
        expected_actor_id = _text(expected.get("actor_id"))
        actual_actor_id = _text(actual.get("actor_id"))
        if expected_actor_id and expected_actor_id != actual_actor_id:
            actor_id_mismatches.append({
                "entity_id": entity_id,
                "expected": expected_actor_id,
                "actual": actual_actor_id,
            })
        expected_asset_id = _text(expected.get("asset_id"))
        actual_asset_id = _text(actual.get("asset_id"))
        if expected_asset_id and expected_asset_id != actual_asset_id:
            asset_id_mismatches.append({
                "entity_id": entity_id,
                "expected": expected_asset_id,
                "actual": actual_asset_id,
            })
        expected_model_ref = _text(expected.get("model_ref"))
        actual_model_ref = _text(actual.get("model_ref"))
        if expected_model_ref and expected_model_ref != actual_model_ref:
            model_ref_mismatches.append({
                "entity_id": entity_id,
                "expected": expected_model_ref,
                "actual": actual_model_ref,
            })
        expected_version = _version(expected)
        actual_version = _version(actual)
        if expected_version and expected_version != actual_version:
            version_mismatches.append({
                "entity_id": entity_id,
                "expected": expected_version,
                "actual": actual_version,
            })
        expected_transform = _transform(expected)
        actual_transform = _transform(actual)
        if expected_transform and expected_transform != actual_transform:
            transform_mismatches.append({
                "entity_id": entity_id,
                "expected": expected_transform,
                "actual": actual_transform,
            })
        expected_aabb = _world_aabb(expected)
        actual_aabb = _world_aabb(actual)
        if expected_aabb is not None and expected_aabb != actual_aabb:
            world_aabb_mismatches.append({
                "entity_id": entity_id,
                "expected": expected_aabb,
                "actual": actual_aabb,
            })

    non_materialized_entity_count = max(0, len(world_entities) - len(expected_entities))
    issue_count = sum((
        len(duplicate_world_ids),
        len(duplicate_engine_ids),
        len(missing_world_identity),
        len(unidentified_engine_actors),
        len(missing_in_engine),
        len(unexpected_in_engine),
        len(actor_id_mismatches),
        len(asset_id_mismatches),
        len(model_ref_mismatches),
        len(version_mismatches),
        len(transform_mismatches),
        len(world_aabb_mismatches),
        non_materialized_entity_count,
    ))
    # The Runtime fingerprint represents the whole downstream-visible world,
    # including entities that have not materialized into Engine actors yet.
    # Otherwise a partial world could compare equal after silently dropping
    # exactly the entities the audit is meant to expose.
    world_fingerprint = scene_world_fingerprint(
        world_entities,
        plan_id=plan_id,
        scene_version=scene_version,
    )
    engine_fingerprint = scene_world_fingerprint(
        engine_actors,
        plan_id=plan_id,
        scene_version=scene_version,
    )
    fingerprints_match = world_fingerprint == engine_fingerprint
    unclassified_fingerprint_mismatch_count = int(
        bool(plan_id and engine_snapshot and not fingerprints_match and issue_count == 0)
    )
    issue_count += unclassified_fingerprint_mismatch_count
    if not plan_id or not engine_snapshot:
        status = "blocked"
    elif issue_count:
        status = "needs_review"
    else:
        status = "consistent"

    return {
        "status": status,
        "plan_id": plan_id,
        "scene_version": scene_version,
        "engine_snapshot_id": _text(engine_snapshot.get("snapshot_id")),
        "expected_entity_count": len(world_entities),
        "materialized_entity_count": len(expected_entities),
        "engine_actor_count": len(engine_actors),
        "matched_entity_count": len(set(world_by_id) & set(engine_by_id)),
        "non_materialized_entity_count": non_materialized_entity_count,
        "issue_count": issue_count,
        "duplicate_world_entity_ids": duplicate_world_ids,
        "duplicate_engine_entity_ids": duplicate_engine_ids,
        "missing_world_identity_actor_ids": missing_world_identity,
        "unidentified_engine_actor_ids": unidentified_engine_actors,
        "missing_in_engine_entity_ids": missing_in_engine,
        "unexpected_in_engine_entity_ids": unexpected_in_engine,
        "actor_id_mismatches": actor_id_mismatches,
        "asset_id_mismatches": asset_id_mismatches,
        "model_ref_mismatches": model_ref_mismatches,
        "version_mismatches": version_mismatches,
        "transform_mismatches": transform_mismatches,
        "world_aabb_mismatches": world_aabb_mismatches,
        "world_fingerprint": world_fingerprint,
        "engine_fingerprint": engine_fingerprint,
        "fingerprints_match": fingerprints_match,
        "unclassified_fingerprint_mismatch_count": unclassified_fingerprint_mismatch_count,
    }


def constrain_scene_world_snapshot_readiness(
    world_snapshot: Mapping[str, Any],
    consistency_audit: Mapping[str, Any],
) -> dict[str, Any]:
    """Prevent downstream readers from treating an inconsistent world as Game-ready."""

    snapshot = dict(world_snapshot or {})
    readiness_summary = dict(snapshot.get("readiness_summary") or {})
    consistency_status = _text(consistency_audit.get("status")) or "blocked"
    consistency_issue_count = int(consistency_audit.get("issue_count") or 0)
    readiness_summary.update({
        "consistency_status": consistency_status,
        "consistency_issue_count": consistency_issue_count,
        "consistency_fingerprints_match": bool(consistency_audit.get("fingerprints_match")),
    })
    snapshot["readiness_summary"] = readiness_summary
    if consistency_status != "consistent" and _text(snapshot.get("world_readiness")) == "game_ready":
        snapshot["world_readiness"] = "needs_review"
    return snapshot


__all__ = [
    "audit_scene_world_consistency",
    "constrain_scene_world_snapshot_readiness",
    "latest_engine_snapshot",
    "scene_world_fingerprint",
]
