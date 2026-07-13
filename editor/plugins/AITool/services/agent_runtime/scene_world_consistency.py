"""Read-only consistency checks between Runtime world and Engine snapshots."""

from __future__ import annotations

from collections import Counter
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
    version_mismatches: list[dict[str, Any]] = []
    for entity_id in sorted(set(world_by_id) & set(engine_by_id)):
        expected = world_by_id[entity_id]
        actual = engine_by_id[entity_id]
        expected_actor_id = _text(expected.get("actor_id"))
        actual_actor_id = _text(actual.get("actor_id"))
        if expected_actor_id and actual_actor_id and expected_actor_id != actual_actor_id:
            actor_id_mismatches.append({
                "entity_id": entity_id,
                "expected": expected_actor_id,
                "actual": actual_actor_id,
            })
        expected_asset_id = _text(expected.get("asset_id"))
        actual_asset_id = _text(actual.get("asset_id"))
        if expected_asset_id and actual_asset_id and expected_asset_id != actual_asset_id:
            asset_id_mismatches.append({
                "entity_id": entity_id,
                "expected": expected_asset_id,
                "actual": actual_asset_id,
            })
        expected_version = _version(expected)
        actual_version = _version(actual)
        if expected_version and actual_version and expected_version != actual_version:
            version_mismatches.append({
                "entity_id": entity_id,
                "expected": expected_version,
                "actual": actual_version,
            })

    issue_count = sum((
        len(duplicate_world_ids),
        len(duplicate_engine_ids),
        len(missing_world_identity),
        len(unidentified_engine_actors),
        len(missing_in_engine),
        len(unexpected_in_engine),
        len(actor_id_mismatches),
        len(asset_id_mismatches),
        len(version_mismatches),
    ))
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
        "expected_entity_count": len(expected_entities),
        "engine_actor_count": len(engine_actors),
        "matched_entity_count": len(set(world_by_id) & set(engine_by_id)),
        "non_materialized_entity_count": max(0, len(world_entities) - len(expected_entities)),
        "issue_count": issue_count,
        "duplicate_world_entity_ids": duplicate_world_ids,
        "duplicate_engine_entity_ids": duplicate_engine_ids,
        "missing_world_identity_actor_ids": missing_world_identity,
        "unidentified_engine_actor_ids": unidentified_engine_actors,
        "missing_in_engine_entity_ids": missing_in_engine,
        "unexpected_in_engine_entity_ids": unexpected_in_engine,
        "actor_id_mismatches": actor_id_mismatches,
        "asset_id_mismatches": asset_id_mismatches,
        "version_mismatches": version_mismatches,
    }


__all__ = ["audit_scene_world_consistency", "latest_engine_snapshot"]
