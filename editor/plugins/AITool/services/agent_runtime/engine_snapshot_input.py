"""Strict contract for the current unversioned native scene snapshot DTO."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from ..schema_versions import ENGINE_SNAPSHOT_INPUT_CONTRACT_VERSION


CURRENT_UNVERSIONED_V1_ENGINE_BUILD_FINGERPRINT = "3d849a9a+patch-0c651bd4"

_TOP_LEVEL_FIELDS = frozenset(
    {
        "status",
        "scene",
        "scene_name",
        "actor_count",
        "actors",
        "active_camera_id",
        "active_camera_name",
        "camera",
        "cameras",
        "scene_aabb",
        "bounds_ready",
    }
)
_ACTOR_REQUIRED_FIELDS = frozenset(
    {
        "name",
        "actor_guid",
        "handle",
        "path",
        "route",
        "scene",
        "type",
        "model",
        "model_dependencies",
        "actor_type",
        "entity_id",
        "asset_id",
        "model_ref",
        "entity_type",
        "semantic_role",
        "source_plan_id",
        "source_batch_id",
        "source_scene_version",
        "actor_version",
        "version",
        "collision",
        "visible",
        "script",
        "follow_camera",
        "render_space",
        "geometry",
        "local_aabb",
        "world_aabb",
        "aabb",
        "bounds_ready",
        "render_status_observed",
        "render_ready",
        "render_failed",
        "gpu_build_state",
        "mesh_count",
        "renderable_mesh_count",
        "invalid_mesh_count",
        "size",
        "camera_lock",
    }
)
_ACTOR_OPTIONAL_FIELDS = frozenset(
    {"audio_resource_id", "mechanics", "optics", "material"}
)
_GEOMETRY_FIELDS = frozenset({"position", "rotation", "scale"})
_MECHANICS_FIELDS = frozenset(
    {"mass", "restitution", "damping", "physics_enabled", "linear_lock", "angular_lock"}
)
_OPTICS_REQUIRED_FIELDS = frozenset(
    {"diffuse", "metallic", "roughness", "specular", "shininess"}
)
_OPTICS_OPTIONAL_FIELDS = frozenset({"emission"})
_MATERIAL_FIELDS = frozenset({"texture"})
_CAMERA_LOCK_FIELDS = frozenset({"lock_to_camera", "position_offset", "rotation_offset"})
_CAMERA_FIELDS = frozenset(
    {
        "id",
        "camera_id",
        "name",
        "handle",
        "position",
        "forward",
        "world_up",
        "fov",
        "width",
        "height",
        "output_mode",
        "render_backend",
        "vision_render_mode",
        "vision_spp",
        "vision_max_depth",
        "vision_denoise",
        "shadow_cascade_debug",
        "ssao_enabled",
        "move_speed",
        "view_open",
        "view_x",
        "view_y",
        "view_width",
        "view_height",
        "deletable",
    }
)


class EngineSnapshotInputContractError(ValueError):
    """Fail-closed error raised before permissive Runtime normalization."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = str(error_code)


def current_unversioned_v1_schema_fingerprint() -> str:
    manifest = {
        "contract_version": ENGINE_SNAPSHOT_INPUT_CONTRACT_VERSION,
        "top_level_fields": sorted(_TOP_LEVEL_FIELDS),
        "actor_required_fields": sorted(_ACTOR_REQUIRED_FIELDS),
        "actor_optional_fields": sorted(_ACTOR_OPTIONAL_FIELDS),
        "geometry_fields": sorted(_GEOMETRY_FIELDS),
        "mechanics_fields": sorted(_MECHANICS_FIELDS),
        "optics_required_fields": sorted(_OPTICS_REQUIRED_FIELDS),
        "optics_optional_fields": sorted(_OPTICS_OPTIONAL_FIELDS),
        "material_fields": sorted(_MATERIAL_FIELDS),
        "camera_lock_fields": sorted(_CAMERA_LOCK_FIELDS),
        "camera_fields": sorted(_CAMERA_FIELDS),
    }
    canonical = json.dumps(manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('ascii')).hexdigest()}"


def validate_current_unversioned_v1_snapshot(
    raw_snapshot: Mapping[str, Any],
    *,
    build_fingerprint: str,
) -> dict[str, Any]:
    """Validate one exact current-build native snapshot without version guessing."""

    if str(build_fingerprint or "").strip() != CURRENT_UNVERSIONED_V1_ENGINE_BUILD_FINGERPRINT:
        raise EngineSnapshotInputContractError(
            "engine_snapshot_build_fingerprint_mismatch",
            "Engine build fingerprint does not match current-unversioned-v1.",
        )
    if not isinstance(raw_snapshot, Mapping):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_input_not_mapping",
            "Engine scene snapshot must be a mapping.",
        )
    snapshot = deepcopy(dict(raw_snapshot))
    _require_exact_fields(snapshot, _TOP_LEVEL_FIELDS, "engine_snapshot_field_set_mismatch", "snapshot")
    if str(snapshot.get("status") or "").strip().lower() != "success":
        raise EngineSnapshotInputContractError(
            "engine_snapshot_status_not_success",
            "Current snapshot fixture only accepts successful native snapshots.",
        )
    if not _required_text(snapshot.get("scene")) or not _required_text(snapshot.get("scene_name")):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_identity_missing",
            "Native snapshot requires scene and scene_name identity.",
        )
    actors = snapshot.get("actors")
    if not isinstance(actors, list):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actor_list_invalid",
            "Native snapshot actors must be a list.",
        )
    if not isinstance(snapshot.get("actor_count"), int) or snapshot["actor_count"] != len(actors):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actor_count_mismatch",
            "Native snapshot actor_count must equal the actors list length.",
        )
    if snapshot.get("bounds_ready") is not True:
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actual_fact_missing",
            "Native snapshot requires an actual scene AABB.",
        )
    _require_aabb(snapshot.get("scene_aabb"), "scene_aabb")
    for index, actor in enumerate(actors):
        _validate_actor(actor, index=index)
    _validate_cameras(snapshot)
    return snapshot


def _validate_actor(value: Any, *, index: int) -> None:
    if not isinstance(value, Mapping):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actor_invalid",
            f"Native snapshot actor {index} must be a mapping.",
        )
    actor = dict(value)
    actor_fields = frozenset(actor)
    missing = sorted(_ACTOR_REQUIRED_FIELDS - actor_fields)
    unknown = sorted(actor_fields - _ACTOR_REQUIRED_FIELDS - _ACTOR_OPTIONAL_FIELDS)
    if missing or unknown:
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actor_field_set_mismatch",
            f"Native snapshot actor {index} field set mismatch: missing={missing}, unknown={unknown}.",
        )
    for field in (
        "name",
        "actor_guid",
        "entity_id",
        "asset_id",
        "model_ref",
        "entity_type",
        "semantic_role",
        "source_plan_id",
        "source_batch_id",
    ):
        if not _required_text(actor.get(field)):
            raise EngineSnapshotInputContractError(
                "engine_snapshot_actor_identity_missing",
                f"Native snapshot actor {index} requires stable {field}.",
            )
    for field in ("source_scene_version", "actor_version", "version"):
        if not isinstance(actor.get(field), int) or int(actor[field]) <= 0:
            raise EngineSnapshotInputContractError(
                "engine_snapshot_actor_version_invalid",
                f"Native snapshot actor {index} requires positive {field}.",
            )
    if int(actor["actor_version"]) != int(actor["version"]):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actor_version_mismatch",
            f"Native snapshot actor {index} actor_version/version mismatch.",
        )
    _require_exact_mapping(actor.get("geometry"), _GEOMETRY_FIELDS, "geometry", index)
    geometry = dict(actor["geometry"])
    for field in _GEOMETRY_FIELDS:
        _require_vector3(geometry.get(field), f"actor[{index}].geometry.{field}")
    if actor.get("bounds_ready") is not True:
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actual_fact_missing",
            f"Native snapshot actor {index} is missing actual bounds readiness.",
        )
    world_aabb = _require_aabb(actor.get("world_aabb"), f"actor[{index}].world_aabb")
    if actor.get("aabb") != world_aabb:
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actor_aabb_mismatch",
            f"Native snapshot actor {index} aabb must equal world_aabb.",
        )
    local_aabb = actor.get("local_aabb")
    if local_aabb is not None:
        _require_aabb(local_aabb, f"actor[{index}].local_aabb")
    if not isinstance(actor.get("render_status_observed"), bool):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_render_fact_missing",
            f"Native snapshot actor {index} requires render_status_observed.",
        )
    for field in ("render_ready", "render_failed", "visible", "follow_camera"):
        if not isinstance(actor.get(field), bool):
            raise EngineSnapshotInputContractError(
                "engine_snapshot_actor_value_invalid",
                f"Native snapshot actor {index} requires boolean {field}.",
            )
    for field in ("mesh_count", "renderable_mesh_count", "invalid_mesh_count"):
        if not isinstance(actor.get(field), int) or int(actor[field]) < 0:
            raise EngineSnapshotInputContractError(
                "engine_snapshot_actor_value_invalid",
                f"Native snapshot actor {index} requires non-negative {field}.",
            )
    _require_vector3(actor.get("size"), f"actor[{index}].size")
    _require_exact_mapping(actor.get("camera_lock"), _CAMERA_LOCK_FIELDS, "camera_lock", index)
    camera_lock = dict(actor["camera_lock"])
    if not isinstance(camera_lock.get("lock_to_camera"), bool):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actor_value_invalid",
            f"Native snapshot actor {index} camera_lock requires lock_to_camera.",
        )
    _require_vector3(camera_lock.get("position_offset"), f"actor[{index}].camera_lock.position_offset")
    _require_vector3(camera_lock.get("rotation_offset"), f"actor[{index}].camera_lock.rotation_offset")
    if "mechanics" in actor:
        _require_exact_mapping(actor["mechanics"], _MECHANICS_FIELDS, "mechanics", index)
    if "optics" in actor:
        optics = actor["optics"]
        if not isinstance(optics, Mapping):
            raise EngineSnapshotInputContractError(
                "engine_snapshot_actor_nested_field_invalid",
                f"Native snapshot actor {index} optics must be a mapping.",
            )
        optics_fields = frozenset(optics)
        if _OPTICS_REQUIRED_FIELDS - optics_fields or optics_fields - _OPTICS_REQUIRED_FIELDS - _OPTICS_OPTIONAL_FIELDS:
            raise EngineSnapshotInputContractError(
                "engine_snapshot_actor_nested_field_set_mismatch",
                f"Native snapshot actor {index} optics field set mismatch.",
            )
    if "material" in actor:
        _require_exact_mapping(actor["material"], _MATERIAL_FIELDS, "material", index)


def _validate_cameras(snapshot: Mapping[str, Any]) -> None:
    cameras = snapshot.get("cameras")
    if not isinstance(cameras, list):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_camera_list_invalid",
            "Native snapshot cameras must be a list.",
        )
    for index, camera in enumerate(cameras):
        _require_exact_mapping(camera, _CAMERA_FIELDS, "camera", index)
    active_camera = snapshot.get("camera")
    if active_camera is None:
        if cameras or _required_text(snapshot.get("active_camera_id")) or _required_text(snapshot.get("active_camera_name")):
            raise EngineSnapshotInputContractError(
                "engine_snapshot_active_camera_mismatch",
                "Native snapshot active camera identity is inconsistent.",
            )
        return
    _require_exact_mapping(active_camera, _CAMERA_FIELDS, "active_camera", 0)
    active = dict(active_camera)
    if str(active.get("camera_id") or "") != str(snapshot.get("active_camera_id") or ""):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_active_camera_mismatch",
            "Native snapshot active_camera_id does not match camera payload.",
        )
    if str(active.get("name") or "") != str(snapshot.get("active_camera_name") or ""):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_active_camera_mismatch",
            "Native snapshot active_camera_name does not match camera payload.",
        )


def _require_exact_fields(
    value: Mapping[str, Any],
    expected: frozenset[str],
    error_code: str,
    label: str,
) -> None:
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise EngineSnapshotInputContractError(
            error_code,
            f"{label} field set mismatch: missing={missing}, unknown={unknown}.",
        )


def _require_exact_mapping(
    value: Any,
    expected: frozenset[str],
    label: str,
    index: int,
) -> None:
    if not isinstance(value, Mapping):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actor_nested_field_invalid",
            f"Native snapshot actor {index} {label} must be a mapping.",
        )
    _require_exact_fields(
        dict(value),
        expected,
        "engine_snapshot_actor_nested_field_set_mismatch",
        f"actor[{index}].{label}",
    )


def _require_aabb(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 6 or not all(_is_number(item) for item in value):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actual_fact_missing",
            f"{label} must be an actual six-value Engine AABB.",
        )
    return list(value)


def _require_vector3(value: Any, label: str) -> None:
    if not isinstance(value, list) or len(value) != 3 or not all(_is_number(item) for item in value):
        raise EngineSnapshotInputContractError(
            "engine_snapshot_actor_value_invalid",
            f"{label} must be a three-value numeric vector.",
        )


def _required_text(value: Any) -> str:
    return str(value or "").strip()


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


__all__ = [
    "CURRENT_UNVERSIONED_V1_ENGINE_BUILD_FINGERPRINT",
    "EngineSnapshotInputContractError",
    "current_unversioned_v1_schema_fingerprint",
    "validate_current_unversioned_v1_snapshot",
]
