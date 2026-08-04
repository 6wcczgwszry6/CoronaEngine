"""Project-level validation for the single-player gameplay proposal boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..integration_contracts import (
    BlockedResult,
    InterfaceChangeDecision,
    InterfaceChangeRequest,
    MissingRequirement,
)
from ..schema_versions import SKELETON_CONTRACT_VERSION
from .action_proposal import (
    ActionProposal,
    GameplayEntityBinding,
    GameplayManifest,
)
from .contracts import (
    ArtifactEnvelope,
    GameplayPrimitiveSpec,
    compute_artifact_content_hash,
    validate_artifact_payload,
)


@dataclass(frozen=True)
class ProjectGateResult:
    status: str
    proposal: ActionProposal | None
    blocked_results: tuple[BlockedResult, ...]

    def __post_init__(self) -> None:
        if self.status == "passed":
            if self.proposal is None or self.blocked_results:
                raise ValueError("passed ProjectGateResult requires one proposal and no blockers")
        elif self.status == "blocked":
            if self.proposal is not None or not self.blocked_results:
                raise ValueError("blocked ProjectGateResult requires blockers and no proposal")
        else:
            raise ValueError("unsupported ProjectGateResult status")


@dataclass(frozen=True)
class AssetLineageGateResult:
    status: str
    blocked_results: tuple[BlockedResult, ...]

    def __post_init__(self) -> None:
        if self.status == "passed" and self.blocked_results:
            raise ValueError("passed AssetLineageGateResult cannot contain blockers")
        if self.status == "blocked" and not self.blocked_results:
            raise ValueError("blocked AssetLineageGateResult requires blockers")
        if self.status not in {"passed", "blocked"}:
            raise ValueError("unsupported AssetLineageGateResult status")


class ProjectGateService:
    """Validate Artifacts and Snapshot facts without submitting a Runtime write."""

    def validate_asset_lineage(
        self,
        *,
        required_items: Sequence[str],
        image_resources: Mapping[str, Any],
        model_resources: Mapping[str, Any],
    ) -> AssetLineageGateResult:
        blockers: list[BlockedResult] = []
        for raw_name in required_items:
            name = str(raw_name or "").strip()
            image = image_resources.get(name) if isinstance(image_resources, Mapping) else None
            model = model_resources.get(name) if isinstance(model_resources, Mapping) else None
            image = dict(image) if isinstance(image, Mapping) else {}
            model = dict(model) if isinstance(model, Mapping) else {}
            image_ref = str(image.get("resource_ref") or "").strip()
            image_hash = str(image.get("content_hash") or "").strip()
            image_location = str(image.get("image_url") or image.get("local_path") or "").strip()
            valid_image = (
                str(image.get("status") or "").strip().lower() == "ready"
                and str(image.get("mode") or "").strip().lower() not in {"mock", "mock_reference", "fixture"}
                and image_ref
                and image_location
                and image_hash.startswith("sha256:")
                and str(image.get("prompt_hash") or "").startswith("sha256:")
            )
            valid_model = (
                str(model.get("status") or "").strip().lower() == "ready"
                and str(model.get("generation_mode") or "") == "image_to_3d"
                and str(model.get("source_image_ref") or "") == image_ref
                and str(model.get("source_image_hash") or "") == image_hash
                and bool(str(model.get("model_ref") or "").strip())
                and bool(str(model.get("local_path") or model.get("model_path") or "").strip())
            )
            if valid_image and valid_model:
                continue
            blockers.extend(self._blockers(
                "asset_image_to_model_lineage_invalid",
                f"{name or '<unnamed>'}: image-to-model lineage is incomplete or mismatched.",
                "collaboration.asset_lineage.image_to_model",
                "Regenerate the image and model with matching resource refs and content hashes.",
            ))
        return AssetLineageGateResult(
            "blocked" if blockers else "passed",
            tuple(blockers),
        )

    def validate_single_player_action(
        self,
        *,
        proposal_id: str,
        command_id: str,
        room_id: str,
        project_id: str,
        gameplay_logic_artifact: ArtifactEnvelope,
        entity_binding_artifact: ArtifactEnvelope,
        snapshot: Mapping[str, Any],
        gate_report: Mapping[str, Any],
    ) -> ProjectGateResult:
        blockers: list[BlockedResult] = []
        blockers.extend(self._validate_artifact(
            gameplay_logic_artifact,
            expected_type="GameplayLogicPlan",
            require_executable=False,
        ))
        blockers.extend(self._validate_artifact(
            entity_binding_artifact,
            expected_type="EntityBindingPlan",
            require_executable=True,
        ))
        if blockers:
            return ProjectGateResult("blocked", None, tuple(blockers))
        if gameplay_logic_artifact.artifact_id not in entity_binding_artifact.dependencies:
            return self._blocked(
                "entity_binding_dependency_missing",
                "EntityBindingPlan does not depend on the validated GameplayLogicPlan.",
                "collaboration.entity_binding.gameplay_logic_dependency",
                "Regenerate EntityBindingPlan with the current GameplayLogicPlan dependency.",
            )
        if not isinstance(snapshot, Mapping):
            return self._blocked(
                "scene_snapshot_invalid",
                "SceneWorldSnapshot is not a mapping.",
                "runtime.scene_world_snapshot",
                "Read a structured immutable SceneWorldSnapshot and retry.",
            )
        snapshot_data = dict(snapshot)
        plan_id = str(snapshot_data.get("plan_id") or "").strip()
        try:
            scene_version = int(snapshot_data.get("scene_version") or 0)
        except (TypeError, ValueError):
            scene_version = 0
        if (
            str(snapshot_data.get("world_readiness") or "").strip() != "game_ready"
            or not plan_id
            or scene_version <= 0
            or not str(snapshot_data.get("world_fingerprint") or "").strip()
        ):
            return self._blocked(
                "scene_snapshot_not_game_ready",
                "Entity binding requires an immutable Game-ready SceneWorldSnapshot.",
                "runtime.scene_world_snapshot.game_ready",
                "Resolve Snapshot readiness and identity blockers before binding gameplay.",
            )
        binding_payload = dict(entity_binding_artifact.payload)
        if (
            str(binding_payload.get("snapshot_plan_id") or "").strip() != plan_id
            or int(binding_payload.get("snapshot_version") or 0) != scene_version
            or entity_binding_artifact.base_world_version != scene_version
        ):
            return self._blocked(
                "entity_binding_snapshot_version_mismatch",
                "EntityBindingPlan targets a different Snapshot plan/version.",
                "collaboration.entity_binding.snapshot_identity",
                "Regenerate EntityBindingPlan from the current immutable Snapshot.",
            )
        if not self._gate_matches_snapshot(gate_report, plan_id=plan_id, scene_version=scene_version):
            return self._blocked(
                "single_player_gate_not_green",
                "single_player_demo Gate is not Green for the target Snapshot.",
                "runtime.r3_gate.single_player_demo.green",
                "Run the single-player Gate against this exact Snapshot and resolve all blockers.",
            )

        logic_payload = dict(gameplay_logic_artifact.payload)
        slots = {
            str(slot.get("slot_id") or "").strip(): dict(slot)
            for slot in logic_payload.get("entity_slots") or ()
            if isinstance(slot, Mapping) and str(slot.get("slot_id") or "").strip()
        }
        entities = self._snapshot_entities(snapshot_data)
        normalized_bindings: list[GameplayEntityBinding] = []
        for binding in binding_payload.get("bindings") or ():
            binding_data = dict(binding)
            slot_id = str(binding_data.get("slot_id") or "").strip()
            slot = slots.get(slot_id)
            entity_id = str(binding_data.get("entity_id") or "").strip()
            entity = entities.get(entity_id)
            if slot is None or entity is None:
                return self._blocked(
                    "entity_binding_reference_missing",
                    "EntityBindingPlan references an unknown slot or Snapshot entity.",
                    "collaboration.entity_binding.reference",
                    "Bind every GameplayEntitySlot to an existing Snapshot entity_id.",
                )
            expected_role = str(slot.get("semantic_role") or "").strip()
            required_capabilities = tuple(
                sorted({str(item or "").strip() for item in slot.get("required_capabilities") or () if str(item or "").strip()})
            )
            observed_capabilities = self._entity_capabilities(entity)
            try:
                observed_version = int(entity.get("entity_version") or entity.get("version") or 0)
            except (TypeError, ValueError):
                observed_version = 0
            if (
                entity.get("game_ready") is not True
                or str(entity.get("semantic_role") or "").strip() != expected_role
                or str(binding_data.get("semantic_role") or "").strip() != expected_role
                or str(binding_data.get("asset_id") or "").strip() != str(entity.get("asset_id") or "").strip()
                or int(binding_data.get("entity_version") or 0) != observed_version
                or not set(required_capabilities).issubset(observed_capabilities)
                or tuple(sorted(binding_data.get("required_capabilities") or ())) != required_capabilities
            ):
                return self._blocked(
                    "entity_binding_fact_mismatch",
                    "EntityBindingPlan does not match Game-ready Snapshot facts.",
                    "collaboration.entity_binding.game_ready_fact",
                    "Regenerate bindings from stable entity_id/version/asset/capability facts.",
                )
            normalized_bindings.append(GameplayEntityBinding(
                slot_id=slot_id,
                semantic_role=expected_role,
                entity_id=entity_id,
                entity_version=observed_version,
                asset_id=str(entity.get("asset_id") or ""),
                required_capabilities=required_capabilities,
            ))
        if set(item.slot_id for item in normalized_bindings) != set(slots):
            return self._blocked(
                "entity_binding_slot_coverage_incomplete",
                "EntityBindingPlan does not cover every GameplayEntitySlot exactly once.",
                "collaboration.entity_binding.slot_coverage",
                "Bind every declared gameplay slot before constructing a manifest.",
            )

        primitives = tuple(
            GameplayPrimitiveSpec(
                primitive_id=str(item.get("primitive_id") or ""),
                kind=str(item.get("kind") or ""),
                subject_slot=str(item.get("subject_slot") or ""),
                target_slot=str(item.get("target_slot") or ""),
                parameters=dict(item.get("parameters") or {}),
            )
            for item in logic_payload.get("primitives") or ()
            if isinstance(item, Mapping)
        )
        objective_ids = {
            str(item.parameters.get("objective_id") or "").strip()
            for item in primitives
            if item.kind == "complete_objective" and str(item.parameters.get("objective_id") or "").strip()
        }
        if len(objective_ids) != 1:
            return self._blocked(
                "gameplay_objective_ambiguous",
                "GameplayLogicPlan must define exactly one complete_objective objective_id.",
                "collaboration.gameplay.objective",
                "Define one deterministic completion objective for the vertical slice.",
            )
        try:
            manifest = GameplayManifest(
                project_id=project_id,
                plan_id=plan_id,
                scene_version=scene_version,
                entity_bindings=tuple(normalized_bindings),
                primitives=primitives,
                objective_id=next(iter(objective_ids)),
            )
            proposal = ActionProposal(
                proposal_id=proposal_id,
                command_id=command_id,
                room_id=room_id,
                binding_artifact=entity_binding_artifact,
                gameplay_manifest=manifest,
                gate_report=gate_report,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            return self._blocked(
                "action_proposal_validation_failed",
                f"Gameplay proposal contract validation failed: {type(exc).__name__}.",
                "collaboration.action_proposal.valid",
                "Repair the producing Artifact or Gate evidence and retry validation.",
            )
        return ProjectGateResult("passed", proposal, ())

    @staticmethod
    def _validate_artifact(
        artifact: ArtifactEnvelope,
        *,
        expected_type: str,
        require_executable: bool,
    ) -> tuple[BlockedResult, ...]:
        if not isinstance(artifact, ArtifactEnvelope):
            return ProjectGateService._blockers(
                "artifact_invalid",
                f"{expected_type} is not an ArtifactEnvelope.",
                "collaboration.artifact.envelope",
                "Provide the validated strong-type ArtifactEnvelope.",
            )
        errors: list[str] = []
        if artifact.artifact_type != expected_type:
            errors.append("artifact_type")
        validation = validate_artifact_payload(artifact.artifact_type, artifact.payload)
        if not validation.valid or not artifact.validation_result.valid:
            errors.append("schema")
        if compute_artifact_content_hash(artifact.artifact_type, artifact.payload) != artifact.content_hash:
            errors.append("content_hash")
        if artifact.status != "validated":
            errors.append("status")
        if require_executable and (
            artifact.non_executable
            or artifact.snapshot_source != "runtime"
            or artifact.base_world_version <= 0
        ):
            errors.append("execution_boundary")
        if not errors:
            return ()
        return ProjectGateService._blockers(
            "artifact_validation_failed",
            f"{expected_type} failed checks: {','.join(sorted(errors))}.",
            "collaboration.artifact.validated",
            "Regenerate and validate the Artifact before ProjectGate.",
        )

    @staticmethod
    def _snapshot_entities(snapshot: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for bucket in ("environment_entities", "actor_entities"):
            for entity in snapshot.get(bucket) or ():
                if not isinstance(entity, Mapping):
                    continue
                entity_id = str(entity.get("entity_id") or "").strip()
                if entity_id and entity_id not in result:
                    result[entity_id] = dict(entity)
        return result

    @staticmethod
    def _entity_capabilities(entity: Mapping[str, Any]) -> set[str]:
        values: set[str] = set()
        for field in ("interaction_capability", "interaction_capabilities", "gameplay_tags"):
            raw = entity.get(field) or ()
            if isinstance(raw, str):
                raw = (raw,)
            if isinstance(raw, Sequence):
                values.update(str(item or "").strip() for item in raw if str(item or "").strip())
        return values

    @staticmethod
    def _gate_matches_snapshot(gate_report: Mapping[str, Any], *, plan_id: str, scene_version: int) -> bool:
        if not isinstance(gate_report, Mapping):
            return False
        metrics = gate_report.get("metrics") if isinstance(gate_report.get("metrics"), Mapping) else {}
        unlocks = {str(item or "").strip() for item in gate_report.get("capability_unlocks") or ()}
        return bool(
            str(gate_report.get("overall") or "").strip().lower() == "green"
            and str(metrics.get("gate_profile") or "").strip() == "single_player_demo"
            and str(gate_report.get("plan_id") or "").strip() == plan_id
            and int(gate_report.get("scene_version") or 0) == scene_version
            and "single_player_entity_binding" in unlocks
            and "single_player_local_action" in unlocks
        )

    @staticmethod
    def _blocked(error_code: str, summary: str, requirement_id: str, next_action: str) -> ProjectGateResult:
        return ProjectGateResult(
            "blocked",
            None,
            ProjectGateService._blockers(error_code, summary, requirement_id, next_action),
        )

    @staticmethod
    def _blockers(
        error_code: str,
        summary: str,
        requirement_id: str,
        next_action: str,
    ) -> tuple[BlockedResult, ...]:
        return (
            BlockedResult(
                node_id="project_gate_service",
                status="blocked",
                error_code=error_code,
                summary=summary,
                missing_requirements=(MissingRequirement(
                    requirement_id=requirement_id,
                    owner_domain="collaboration",
                    description=summary,
                ),),
                owner_domain="collaboration",
                retryable=True,
                next_action=next_action,
                evidence_refs=("project_gate:single_player_action",),
            ),
        )


def gameplay_plan_patch_interface_change_request(contract_hash: str) -> InterfaceChangeRequest:
    """Describe the frozen Runtime transport gap without modifying PlanPatch."""

    return InterfaceChangeRequest(
        request_id="request.b6.4-gameplay-plan-patch-payload",
        node_id="project_gate_preflight",
        detected_by_task_id="b6.4",
        current_contract_version=SKELETON_CONTRACT_VERSION,
        current_contract_hash=contract_hash,
        reason_code="structured-gameplay-payload-unavailable",
        required_change=(
            "Add an architecture-approved structured gameplay payload carrier between "
            "ActionProposal and PlanPatch; do not encode GameplayManifest in text/items."
        ),
        affected_interfaces=("ActionProposal", "PlanPatch", "ToolCallGraph"),
        blocked_dependents=("B6.4-runtime-submit", "B7.3"),
        evidence_refs=(
            "editor/plugins/AITool/services/agent_runtime/core.py:PlanPatch",
            "docs/R3黑盒期单人垂直切片推进计划.md:B6.4",
        ),
    )


def gameplay_plan_patch_interface_change_decision(contract_hash: str) -> InterfaceChangeDecision:
    """Record the approved v5 PlanPatch structured-payload interface change."""

    return InterfaceChangeDecision(
        decision="accepted",
        reason=(
            "The user approved a versioned gameplay_manifest_apply PlanPatch payload so "
            "ActionProposal can reach the guarded Runtime write chain without text encoding."
        ),
        changed_interfaces=("ActionProposal", "GameplayManifest", "PlanPatch", "ToolCallGraph"),
        new_contract_version=SKELETON_CONTRACT_VERSION,
        new_contract_hash=contract_hash,
        affected_nodes=("project_gate_preflight", "demo_result"),
        required_revalidation=(
            "B0.4-walking-skeleton",
            "architecture-import-isolation",
            "B6.4-runtime-submit",
        ),
        evidence_refs=(
            "approval:request.b6.4-gameplay-plan-patch-payload",
            "schema_versions:SKELETON_CONTRACT_VERSION",
        ),
    )


__all__ = [
    "ProjectGateResult",
    "ProjectGateService",
    "gameplay_plan_patch_interface_change_decision",
    "gameplay_plan_patch_interface_change_request",
]
