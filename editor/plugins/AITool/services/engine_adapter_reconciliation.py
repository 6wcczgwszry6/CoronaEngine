"""Strict read-only reconciliation for the current unversioned Engine build."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Literal, Mapping

from .agent_collaboration.walking_skeleton import (
    EngineCapabilityManifest,
    RuntimeEngineCapabilityPort,
)
from .integration_contracts import BlockedResult, MissingRequirement
from .schema_versions import ENGINE_SNAPSHOT_INPUT_CONTRACT_VERSION


_REQUIRED_OBSERVATION_OPERATIONS = frozenset(
    {"scene_snapshot.read", "actual_aabb", "render_ready"}
)


@dataclass(frozen=True)
class CurrentEngineReconciliationResult:
    status: Literal["accepted", "blocked"]
    capability_manifest: EngineCapabilityManifest | None
    input_contract_version: str
    build_fingerprint: str
    schema_fingerprint: str
    plan_id: str
    scene_version: int
    snapshot: Mapping[str, Any] | None
    blocked_result: BlockedResult | None
    executable: bool = False

    def __post_init__(self) -> None:
        if self.executable:
            raise ValueError("Engine reconciliation result cannot be executable")
        if self.status == "accepted":
            if self.capability_manifest is None or self.snapshot is None or self.blocked_result is not None:
                raise ValueError("accepted reconciliation result is incomplete")
            if self.input_contract_version != ENGINE_SNAPSHOT_INPUT_CONTRACT_VERSION:
                raise ValueError("accepted reconciliation result has incompatible input contract")
            if not self.build_fingerprint or not self.schema_fingerprint:
                raise ValueError("accepted reconciliation result requires contract fingerprints")
            if not self.plan_id or self.scene_version <= 0:
                raise ValueError("accepted reconciliation result requires stable plan/version identity")
            object.__setattr__(self, "snapshot", MappingProxyType(dict(self.snapshot)))
        elif self.status == "blocked":
            if self.snapshot is not None or self.blocked_result is None:
                raise ValueError("blocked reconciliation result requires one blocker and no snapshot")
        else:
            raise ValueError("unsupported reconciliation status")


class CurrentEngineAdapterReconciler:
    """Combine capability and strict Snapshot facts without entering Runtime writes."""

    def __init__(
        self,
        *,
        manifest_reader: Callable[[], Mapping[str, object]] | None,
        snapshot_reader: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
        evidence_ref: str = "adapter:current_engine_reconciliation",
    ) -> None:
        self._capabilities = RuntimeEngineCapabilityPort(
            manifest_reader=manifest_reader,
            evidence_ref=f"{evidence_ref}:capabilities",
        )
        self._snapshot_reader = snapshot_reader
        self._evidence_ref = str(evidence_ref or "adapter:current_engine_reconciliation")

    def reconcile(
        self,
        *,
        room_id: str,
        scene_name: str = "",
        scene_route: str = "",
    ) -> CurrentEngineReconciliationResult:
        capability_result = self._capabilities.get_manifest()
        if isinstance(capability_result, BlockedResult):
            return self._blocked(capability_result)
        missing_operations = tuple(
            sorted(_REQUIRED_OBSERVATION_OPERATIONS - set(capability_result.supported_operations))
        )
        if missing_operations:
            return self._blocked(BlockedResult(
                node_id="current_engine_adapter_reconciliation",
                status="blocked",
                error_code="engine_observation_capability_missing",
                summary="Engine capability manifest lacks required read-only observation operations.",
                missing_requirements=tuple(
                    MissingRequirement(
                        requirement_id=f"engine.operation.{operation}",
                        owner_domain="engine",
                        description=f"Engine must advertise {operation} for strict Snapshot reconciliation.",
                    )
                    for operation in missing_operations
                ),
                owner_domain="engine",
                retryable=True,
                next_action="Expose the missing observation operations in the Engine capability manifest.",
                evidence_refs=(f"{self._evidence_ref}:capabilities",),
            ))
        if self._snapshot_reader is None:
            return self._blocked(self._snapshot_blocker(
                "engine_snapshot_reader_unavailable",
                "No strict current-build Snapshot reader is connected.",
                "Connect the current-unversioned-v1 Snapshot reader and retry.",
            ))
        try:
            raw_result = self._snapshot_reader({
                "room_id": str(room_id or "default"),
                "scene_name": str(scene_name or ""),
                "scene_route": str(scene_route or ""),
            })
        except Exception as exc:  # noqa: BLE001
            error_code = str(getattr(exc, "error_code", "") or "").strip()
            return self._blocked(self._snapshot_blocker(
                error_code or "engine_snapshot_reconciliation_failed",
                "Engine Snapshot failed the strict current-build reconciliation contract.",
                "Align the Engine build and Snapshot field contract, then retry the read-only query.",
            ))
        if not isinstance(raw_result, Mapping):
            return self._blocked(self._snapshot_blocker(
                "engine_snapshot_reconciliation_invalid",
                "Strict Snapshot reader returned an invalid result.",
                "Return the current-unversioned-v1 reconciliation envelope.",
            ))
        result = dict(raw_result)
        snapshot = result.get("snapshot")
        plan_id = str(result.get("plan_id") or "").strip()
        try:
            scene_version = int(result.get("scene_version") or 0)
        except (TypeError, ValueError):
            scene_version = 0
        if not isinstance(snapshot, Mapping) or not plan_id or scene_version <= 0:
            return self._blocked(self._snapshot_blocker(
                "engine_snapshot_plan_version_missing",
                "Strict Snapshot lacks one stable plan_id and scene_version.",
                "Preserve source_plan_id and source_scene_version for every native Actor.",
            ))
        return CurrentEngineReconciliationResult(
            status="accepted",
            capability_manifest=capability_result,
            input_contract_version=str(result.get("input_contract_version") or ""),
            build_fingerprint=str(result.get("build_fingerprint") or ""),
            schema_fingerprint=str(result.get("schema_fingerprint") or ""),
            plan_id=plan_id,
            scene_version=scene_version,
            snapshot=snapshot,
            blocked_result=None,
        )

    @staticmethod
    def _blocked(blocker: BlockedResult) -> CurrentEngineReconciliationResult:
        return CurrentEngineReconciliationResult(
            status="blocked",
            capability_manifest=None,
            input_contract_version="",
            build_fingerprint="",
            schema_fingerprint="",
            plan_id="",
            scene_version=0,
            snapshot=None,
            blocked_result=blocker,
        )

    def _snapshot_blocker(self, error_code: str, summary: str, next_action: str) -> BlockedResult:
        return BlockedResult(
            node_id="current_engine_adapter_reconciliation",
            status="blocked",
            error_code=error_code,
            summary=summary,
            missing_requirements=(
                MissingRequirement(
                    requirement_id="engine.snapshot.current_unversioned_v1",
                    owner_domain="engine",
                    description="A strict current-build Snapshot with stable identity and actual facts is required.",
                ),
            ),
            owner_domain="engine",
            retryable=True,
            next_action=next_action,
            evidence_refs=(f"{self._evidence_ref}:snapshot",),
        )


__all__ = ["CurrentEngineAdapterReconciler", "CurrentEngineReconciliationResult"]
