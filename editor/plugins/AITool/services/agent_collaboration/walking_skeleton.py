from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Callable, Mapping, Protocol

from ..integration_contracts import (
    BLOCKED_STATUSES,
    NODE_STATUSES,
    OWNER_DOMAINS,
    PUBLIC_SCHEMA_VERSIONS,
    FRONTEND_INTERACTION_SCHEMA_VERSION,
    SKELETON_CONTRACT_VERSION,
    BlockedResult,
    MissingRequirement,
    PublicDtoManifest,
    PublicEnumManifest,
    SkeletonContractManifest,
    SkeletonNodeStatus,
    SkeletonStatusReport,
    dto_manifest,
    protocol_manifest,
)
from .artifact_bundle import ProjectArtifactBundle, ProjectArtifactBundleReader
from .artifact_registry import ArtifactRegistry
from .contracts import (
    ARTIFACT_LINEAGE_IDS,
    ALLOWED_GAMEPLAY_PRIMITIVES,
    AgentTask,
    ArtDirection,
    GameDesignBrief,
    GameplayEntitySlot,
    GameplayLogicPlan,
    GameplayPrimitiveSpec,
    LevelPlan,
    SceneCompositionPlan,
)
from .project_state import ProjectStateStore
from .task_graph import AgentTaskGraphStore
from .agents import (
    ArtAgent,
    ArtAgentDraft,
    ArtAgentResult,
    ArtRequest,
    PlanningAgent,
    PlanningAgentDraft,
    PlanningAgentResult,
    PlanningRequest,
    ProgramAgent,
    ProgramAgentDraft,
    ProgramAgentResult,
    ProgramRequest,
)


SKELETON_NODE_ORDER = (
    "user_command_fixture",
    "demo_scenario_runner",
    "planning_agent",
    "program_agent",
    "art_agent",
    "artifact_bundle",
    "project_gate_preflight",
    "engine_capability_port",
    "demo_result",
    "progress_event_fixture",
)
SKELETON_EDGES = tuple(zip(SKELETON_NODE_ORDER, SKELETON_NODE_ORDER[1:]))
SKELETON_INTERFACE_NAMES = (
    "UserCommandFixture",
    "DemoScenarioRunnerPort.run",
    "PlanningAgentPort.run",
    "ProgramAgentPort.run",
    "ArtAgentPort.run",
    "ArtifactBundlePort.build",
    "ProjectGatePreflightPort.evaluate",
    "EngineCapabilityPort.get_manifest",
    "DemoResult",
    "ProgressEventFixture",
)


def _required_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _text_tuple(values: object, field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a sequence")
    result = tuple(str(value or "").strip() for value in values)
    if any(not value for value in result):
        raise ValueError(f"{field_name} cannot contain empty values")
    if not allow_empty and not result:
        raise ValueError(f"{field_name} cannot be empty")
    return result


@dataclass(frozen=True)
class UserCommandFixture:
    schema_version: str
    command_id: str
    room_id: str
    project_id: str
    scenario_id: str
    project_goal: str
    requested_by: str

    def __post_init__(self) -> None:
        for field_name in (
            "schema_version",
            "command_id",
            "room_id",
            "project_id",
            "scenario_id",
            "project_goal",
            "requested_by",
        ):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))


@dataclass(frozen=True)
class PreflightCheck:
    check_id: str
    status: str
    summary: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "check_id", _required_text(self.check_id, "check_id"))
        if self.status not in {"passed", "failed"}:
            raise ValueError(f"unsupported preflight status: {self.status}")
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs", allow_empty=False))


@dataclass(frozen=True)
class ProjectGatePreflightResult:
    status: str
    checks: tuple[PreflightCheck, ...]
    blocked_results: tuple[BlockedResult, ...]
    executable: bool = False

    def __post_init__(self) -> None:
        if self.status not in {"completed", "blocked", "pending_runtime_verification"}:
            raise ValueError(f"unsupported preflight result: {self.status}")
        checks = tuple(self.checks)
        if not checks or not all(isinstance(item, PreflightCheck) for item in checks):
            raise ValueError("checks must contain PreflightCheck values")
        object.__setattr__(self, "checks", checks)
        blocked = tuple(self.blocked_results)
        if not all(isinstance(item, BlockedResult) for item in blocked):
            raise ValueError("blocked_results must contain BlockedResult values")
        if self.status in BLOCKED_STATUSES and not blocked:
            raise ValueError("blocked preflight result requires blocked_results")
        object.__setattr__(self, "blocked_results", blocked)
        if self.executable:
            raise ValueError("Walking Skeleton preflight cannot be executable")


@dataclass(frozen=True)
class EngineCapabilityManifest:
    contract_version: str
    bridge_version: str
    snapshot_schema_version: str
    supported_operations: tuple[str, ...]
    supported_gameplay_primitives: tuple[str, ...]


@dataclass(frozen=True)
class DemoResult:
    project_id: str
    task_graph_id: str
    scenario_id: str
    status: str
    executable: bool
    artifact_refs: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    preflight_result: ProjectGatePreflightResult
    pending_runtime_verifications: tuple[BlockedResult, ...]
    blocked_results: tuple[BlockedResult, ...]
    skeleton_report: SkeletonStatusReport

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _required_text(self.project_id, "project_id"))
        object.__setattr__(self, "task_graph_id", _required_text(self.task_graph_id, "task_graph_id"))
        object.__setattr__(self, "scenario_id", _required_text(self.scenario_id, "scenario_id"))
        if self.status not in {"integration_ready", "blocked", "failed"}:
            raise ValueError(f"unsupported demo result status: {self.status}")
        if self.executable:
            raise ValueError("Walking Skeleton DemoResult cannot be executable")
        object.__setattr__(self, "artifact_refs", tuple(sorted(_text_tuple(self.artifact_refs, "artifact_refs", allow_empty=False))))
        blocked = tuple(self.blocked_results)
        if not all(isinstance(item, BlockedResult) for item in blocked):
            raise ValueError("blocked_results must contain BlockedResult values")
        if self.status == "blocked" and not blocked:
            raise ValueError("blocked DemoResult requires blocked_results")
        object.__setattr__(self, "blocked_results", blocked)
        pending = tuple(self.pending_runtime_verifications)
        if not all(isinstance(item, BlockedResult) for item in pending):
            raise ValueError("pending_runtime_verifications must contain BlockedResult values")
        if any(item.status != "pending_runtime_verification" for item in pending):
            raise ValueError("pending_runtime_verifications must contain pending runtime results")
        object.__setattr__(self, "pending_runtime_verifications", pending)
        object.__setattr__(self, "required_capabilities", tuple(sorted(_text_tuple(self.required_capabilities, "required_capabilities", allow_empty=False))))
        if not isinstance(self.preflight_result, ProjectGatePreflightResult):
            raise TypeError("preflight_result must be ProjectGatePreflightResult")
        if not isinstance(self.skeleton_report, SkeletonStatusReport):
            raise TypeError("skeleton_report must be SkeletonStatusReport")


@dataclass(frozen=True)
class ProgressEventFixture:
    schema_version: str
    event_id: str
    command_id: str
    scenario_id: str
    status: str
    blocked_results: tuple[BlockedResult, ...]
    skeleton_report: SkeletonStatusReport


@dataclass(frozen=True)
class WalkingSkeletonRunResult:
    manifest: SkeletonContractManifest
    preflight: ProjectGatePreflightResult
    demo_result: DemoResult
    progress_event: ProgressEventFixture
    bundle: ProjectArtifactBundle
    artifact_payloads: Mapping[str, Mapping[str, object]]


@dataclass(frozen=True)
class CollaborationStageEvent:
    stage: str
    status: str
    artifact_refs: tuple[str, ...] = ()
    error_code: str = ""
    field_path: str = ""
    safe_summary: str = ""


class DemoScenarioRunnerPort(Protocol):
    def run(self, command: UserCommandFixture) -> WalkingSkeletonRunResult: ...


class PlanningAgentPort(Protocol):
    def run(self, request: PlanningRequest) -> PlanningAgentResult: ...


class ArtAgentPort(Protocol):
    def run(self, request: ArtRequest) -> ArtAgentResult: ...


class ProgramAgentPort(Protocol):
    def run(self, request: ProgramRequest) -> ProgramAgentResult: ...


class ArtifactBundlePort(Protocol):
    def build(self, *, project_id: str, graph_id: str) -> ProjectArtifactBundle: ...


class ProjectGatePreflightPort(Protocol):
    def evaluate(self, bundle: ProjectArtifactBundle) -> ProjectGatePreflightResult: ...


class EngineCapabilityPort(Protocol):
    def get_manifest(self) -> EngineCapabilityManifest | BlockedResult: ...


class _PlanningReasoner:
    def generate(self, request, _context) -> PlanningAgentDraft:
        return PlanningAgentDraft(
            game_design_brief=GameDesignBrief(
                project_goal=request.project_goal,
                player_experience=("understand the objective", "complete a short playable loop"),
                core_rules=("collect the key before unlocking the exit",),
                acceptance_criteria=request.acceptance_criteria,
            ),
            level_plan=LevelPlan(
                level_goal="Collect the key, unlock the door, and reach the goal zone.",
                zones=("spawn", "key table", "locked exit", "goal zone"),
                progression=("spawn", "collect key", "unlock door", "enter goal"),
                acceptance_criteria=request.acceptance_criteria,
            ),
        )


class _ArtReasoner:
    def generate(self, _request, context) -> ArtAgentDraft:
        gameplay_artifact = context.gameplay_logic_artifact
        gameplay = gameplay_artifact.payload if gameplay_artifact is not None else {}
        slots = gameplay.get("entity_slots") if isinstance(gameplay, Mapping) else ()
        semantic_roles = tuple(
            str(slot.get("semantic_role") or "").strip()
            for slot in (slots or ())
            if isinstance(slot, Mapping) and str(slot.get("semantic_role") or "").strip()
        )
        entity_requirements = semantic_roles or (
            "player_spawn",
            "collectible_key",
            "locked_door",
            "goal_zone",
        )
        return ArtAgentDraft(
            art_direction=ArtDirection(
                style_keywords=("readable", "low-detail", "warm indoor"),
                palette=("warm white", "wood", "green accent"),
                lighting=("single soft key light",),
                avoid_keywords=("visual clutter", "dark horror"),
            ),
            scene_composition_plan=SceneCompositionPlan(
                scene_type="indoor_room",
                environment_requirements=("room_box", "room_floor"),
                entity_requirements=entity_requirements,
                layout_rules=("keep a clear route from spawn to goal",),
                image_prompts={
                    role: f"low-detail game-ready {role}, isolated object, readable silhouette"
                    for role in entity_requirements
                    if role not in {"player_spawn", "goal_zone"}
                },
            ),
        )


class _ProgramReasoner:
    def generate(self, _request, _context) -> ProgramAgentDraft:
        return ProgramAgentDraft(
            gameplay_logic_plan=GameplayLogicPlan(
                states=("key_available", "key_collected", "door_unlocked", "objective_complete"),
                entity_slots=(
                    GameplayEntitySlot("player", "player_spawn", ("player",)),
                    GameplayEntitySlot("key", "collectible_key", ("collectible",)),
                    GameplayEntitySlot("door", "locked_door", ("lockable",)),
                    GameplayEntitySlot("goal", "goal_zone", ("trigger_zone",)),
                ),
                primitives=(
                    GameplayPrimitiveSpec("collect-key", "on_collect", "key", "player", {"state_key": "key_collected", "set_value": True}),
                    GameplayPrimitiveSpec("unlock-door", "unlock", "key", "door", {"required_state": "key_collected"}),
                    GameplayPrimitiveSpec("enter-goal", "on_enter", "goal", "player", {}),
                    GameplayPrimitiveSpec("complete-objective", "complete_objective", "goal", "player", {"objective_id": "reach_goal"}),
                ),
                triggers=("collect_key", "enter_unlocked_door", "enter_goal_zone"),
                rules=("door requires key_collected", "goal requires door_unlocked"),
                win_conditions=("objective_complete",),
                lose_conditions=("none",),
            )
        )


class ProjectGatePreflight:
    _REQUIRED_ENGINE_OPERATIONS = frozenset(
        {
            "actor_create",
            "scene_snapshot.read",
            "actual_aabb",
            "render_ready",
            "gameplay.apply_manifest",
            "gameplay.preview.start",
        }
    )

    def __init__(self, *, engine_capabilities: EngineCapabilityPort) -> None:
        if not callable(getattr(engine_capabilities, "get_manifest", None)):
            raise TypeError("engine_capabilities must provide get_manifest()")
        self._engine_capabilities = engine_capabilities
        self._last_capability_result: EngineCapabilityManifest | BlockedResult | None = None

    @property
    def last_capability_result(self) -> EngineCapabilityManifest | BlockedResult:
        if self._last_capability_result is None:
            raise RuntimeError("evaluate() must run before reading capability_result")
        return self._last_capability_result

    def evaluate(self, bundle: ProjectArtifactBundle) -> ProjectGatePreflightResult:
        package = bundle.as_dict()
        refs = set(bundle.artifact_refs)
        dependencies = {
            dependency
            for entry in bundle.entries.values()
            for dependency in entry.dependencies
        }
        checks = (
            PreflightCheck(
                "artifact.bundle_complete",
                "passed" if len(bundle.entries) == 5 else "failed",
                "Five Red-stage Artifacts are present.",
                (f"ArtifactBundle:{bundle.content_hash}",),
            ),
            PreflightCheck(
                "artifact.hashes_valid",
                "passed" if bundle.content_hash.startswith("sha256:") and all(
                    entry.content_hash.startswith("sha256:") for entry in bundle.entries.values()
                ) else "failed",
                "Bundle and Artifact hashes use SHA-256 identities.",
                (f"ArtifactBundle:{bundle.content_hash}",),
            ),
            PreflightCheck(
                "artifact.dependencies_internal",
                "passed" if dependencies <= refs else "failed",
                "Artifact dependencies resolve inside the bundle.",
                tuple(sorted(f"Artifact:{ref}" for ref in refs)),
            ),
            PreflightCheck(
                "artifact.non_executable",
                "passed" if bool(package.get("non_executable")) else "failed",
                "Red-stage Artifact bundle remains non-executable.",
                (f"ArtifactBundle:{bundle.content_hash}",),
            ),
        )
        failed = tuple(check for check in checks if check.status == "failed")
        blocked_results: tuple[BlockedResult, ...] = ()
        if failed:
            blocked_results = (
                BlockedResult(
                    node_id="project_gate_preflight",
                    status="blocked",
                    error_code="collaboration.preflight_failed",
                    summary="Artifact preflight failed.",
                    missing_requirements=tuple(
                        MissingRequirement(
                            requirement_id=f"collaboration.{check.check_id}",
                            owner_domain="collaboration",
                            description=check.summary,
                        )
                        for check in failed
                    ),
                    owner_domain="collaboration",
                    retryable=False,
                    next_action="Repair the invalid Artifact task and rerun preflight.",
                    evidence_refs=tuple(ref for check in failed for ref in check.evidence_refs),
                ),
            )
        capability_result = self._engine_capabilities.get_manifest()
        self._last_capability_result = capability_result
        if isinstance(capability_result, BlockedResult):
            if failed:
                return ProjectGatePreflightResult(
                    status="blocked",
                    checks=checks,
                    blocked_results=blocked_results + (capability_result,),
                    executable=False,
                )
            return ProjectGatePreflightResult(
                status="pending_runtime_verification",
                checks=checks,
                blocked_results=(capability_result,),
                executable=False,
            )

        missing_operations = tuple(
            sorted(self._REQUIRED_ENGINE_OPERATIONS - set(capability_result.supported_operations))
        )
        missing_primitives = tuple(
            sorted(ALLOWED_GAMEPLAY_PRIMITIVES - set(capability_result.supported_gameplay_primitives))
        )
        if missing_operations or missing_primitives:
            missing_requirements = tuple(
                MissingRequirement(
                    requirement_id=f"engine.operation.{operation}",
                    owner_domain="engine",
                    description=f"Engine must support operation {operation} for the demo.",
                )
                for operation in missing_operations
            ) + tuple(
                MissingRequirement(
                    requirement_id=f"engine.gameplay_primitive.{primitive}",
                    owner_domain="engine",
                    description=f"Engine must support gameplay primitive {primitive} for the demo.",
                )
                for primitive in missing_primitives
            )
            blocked_results += (
                BlockedResult(
                    node_id="project_gate_preflight",
                    status="blocked",
                    error_code="engine_capability_missing",
                    summary="Engine capability manifest does not satisfy the demo contract.",
                    missing_requirements=missing_requirements,
                    owner_domain="engine",
                    retryable=True,
                    next_action="Implement or advertise every required Engine operation and gameplay primitive.",
                    evidence_refs=("EngineCapabilityManifest",),
                ),
            )
        return ProjectGatePreflightResult(
            status="blocked" if failed or blocked_results else "completed",
            checks=checks,
            blocked_results=blocked_results,
            executable=False,
        )


class UnavailableEngineCapabilityPort:
    def get_manifest(self) -> BlockedResult:
        return BlockedResult(
            node_id="engine_capability_port",
            status="pending_runtime_verification",
            error_code="engine_capability_manifest_unavailable",
            summary="Engine capability manifest is unavailable during the black-box phase.",
            missing_requirements=(
                MissingRequirement(
                    requirement_id="engine.capability_manifest",
                    owner_domain="engine",
                    description="Provide the frozen Engine capability manifest on the integration SHA.",
                ),
            ),
            owner_domain="engine",
            retryable=True,
            next_action="Retry after the Engine team provides the stable integration manifest.",
            evidence_refs=("plan:B0.4:engine_capability_port",),
        )


class RuntimeEngineCapabilityPort:
    """Normalize a read-only Engine manifest without importing Runtime internals.

    A host wires this port with ``make_engine_capability_manifest_reader`` from
    the Runtime adapter layer.  Keeping the callable injected preserves the
    collaboration-to-Runtime dependency boundary established by the skeleton.
    """

    _KNOWN_FAILURE_CODES = frozenset(
        {
            "bridge_not_connected",
            "engine_capability_manifest_unavailable",
            "engine_capability_manifest_read_failed",
            "engine_capability_manifest_invalid",
            "engine_capability_contract_version_incompatible",
            "engine_snapshot_schema_version_incompatible",
        }
    )

    def __init__(
        self,
        *,
        manifest_reader: Callable[[], Mapping[str, object]] | None,
        evidence_ref: str = "adapter:engine_capability_port",
    ) -> None:
        self._manifest_reader = manifest_reader
        self._evidence_ref = _required_text(evidence_ref, "evidence_ref")

    def get_manifest(self) -> EngineCapabilityManifest | BlockedResult:
        if self._manifest_reader is None:
            return self._blocked(
                "bridge_not_connected",
                "No Engine capability reader is connected.",
                "Connect the Runtime read-only capability adapter and retry.",
            )
        try:
            raw_manifest = self._manifest_reader()
        except Exception as exc:  # noqa: BLE001
            error_code = str(getattr(exc, "error_code", "")).strip()
            return self._blocked(
                error_code if error_code in self._KNOWN_FAILURE_CODES else "engine_capability_manifest_read_failed",
                "Engine capability manifest could not be read.",
                "Restore the Engine capability bridge and retry the read-only query.",
            )
        if not isinstance(raw_manifest, Mapping):
            return self._blocked(
                "engine_capability_manifest_invalid",
                "Engine capability manifest response is not a mapping.",
                "Return a structured Engine capability manifest from the bridge.",
            )
        manifest = dict(raw_manifest)
        status = str(manifest.get("status") or "").strip().lower()
        if status in {"error", "failed", "failure", "fail"} or manifest.get("error"):
            native_code = str(manifest.get("error_code") or "").strip()
            return self._blocked(
                native_code if native_code in self._KNOWN_FAILURE_CODES else "engine_capability_manifest_unavailable",
                "Engine reported that its capability manifest is unavailable.",
                "Repair the Engine capability endpoint and retry the read-only query.",
            )
        contract_version = self._text_value(manifest, "contract_version", "capability_contract_version")
        bridge_version = self._text_value(manifest, "bridge_version", "engine_bridge_version")
        snapshot_schema_version = self._text_value(
            manifest,
            "snapshot_schema_version",
            "scene_snapshot_schema_version",
        )
        if not contract_version or not bridge_version or not snapshot_schema_version:
            return self._blocked(
                "engine_capability_manifest_invalid",
                "Engine capability manifest is missing required version fields.",
                "Return contract, bridge, and scene snapshot schema versions from Engine.",
            )
        expected_versions = dict(PUBLIC_SCHEMA_VERSIONS)
        if contract_version != expected_versions["engine_adapter"]:
            return self._blocked(
                "engine_capability_contract_version_incompatible",
                "Engine capability contract version is incompatible with this integration build.",
                "Align the Engine capability contract version before retrying.",
            )
        if snapshot_schema_version != expected_versions["scene_world_snapshot"]:
            return self._blocked(
                "engine_snapshot_schema_version_incompatible",
                "Engine scene snapshot schema version is incompatible with this integration build.",
                "Align the Engine scene snapshot schema version before retrying.",
            )
        operations = self._text_values(manifest, "supported_operations", "operations")
        primitives = self._text_values(manifest, "supported_gameplay_primitives", "gameplay_primitives")
        if operations is None or primitives is None:
            return self._blocked(
                "engine_capability_manifest_invalid",
                "Engine capability manifest has invalid capability lists.",
                "Return string capability lists for operations and gameplay primitives.",
            )
        return EngineCapabilityManifest(
            contract_version=contract_version,
            bridge_version=bridge_version,
            snapshot_schema_version=snapshot_schema_version,
            supported_operations=operations,
            supported_gameplay_primitives=primitives,
        )

    @staticmethod
    def _text_value(manifest: Mapping[str, object], *keys: str) -> str:
        for key in keys:
            value = str(manifest.get(key) or "").strip()
            if value:
                return value
        return ""

    @staticmethod
    def _text_values(manifest: Mapping[str, object], *keys: str) -> tuple[str, ...] | None:
        for key in keys:
            if key not in manifest:
                continue
            value = manifest[key]
            if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, (tuple, list, set, frozenset)):
                return None
            return tuple(sorted({str(item or "").strip() for item in value if str(item or "").strip()}))
        return None

    def _blocked(self, error_code: str, summary: str, next_action: str) -> BlockedResult:
        return BlockedResult(
            node_id="engine_capability_port",
            status="pending_runtime_verification",
            error_code=error_code,
            summary=summary,
            missing_requirements=(
                MissingRequirement(
                    requirement_id="engine.capability_manifest",
                    owner_domain="engine",
                    description="A compatible Engine capability manifest is required for this node.",
                ),
            ),
            owner_domain="engine",
            retryable=True,
            next_action=next_action,
            evidence_refs=(self._evidence_ref,),
        )


def default_user_command_fixture() -> UserCommandFixture:
    return UserCommandFixture(
        schema_version=FRONTEND_INTERACTION_SCHEMA_VERSION,
        command_id="command.walking-skeleton-001",
        room_id="room.walking-skeleton",
        project_id="project.walking-skeleton",
        scenario_id="scenario.key-door-goal",
        project_goal="Create a short single-player key, door, and goal demo.",
        requested_by="host",
    )


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError("clock must return a UTC datetime")
    return value.isoformat().replace("+00:00", "Z")


def build_skeleton_manifest() -> SkeletonContractManifest:
    protocols = (
        protocol_manifest(DemoScenarioRunnerPort),
        protocol_manifest(PlanningAgentPort),
        protocol_manifest(ArtAgentPort),
        protocol_manifest(ProgramAgentPort),
        protocol_manifest(ArtifactBundlePort),
        protocol_manifest(ProjectGatePreflightPort),
        protocol_manifest(EngineCapabilityPort),
    )
    dtos = tuple(
        dto_manifest(dto)
        for dto in (
            UserCommandFixture,
            PlanningRequest,
            PlanningAgentResult,
            ArtRequest,
            ArtAgentResult,
            ProgramRequest,
            ProgramAgentResult,
            GameplayEntitySlot,
            GameplayPrimitiveSpec,
            GameplayLogicPlan,
            ProjectArtifactBundle,
            PreflightCheck,
            ProjectGatePreflightResult,
            EngineCapabilityManifest,
            MissingRequirement,
            BlockedResult,
            SkeletonNodeStatus,
            SkeletonStatusReport,
            DemoResult,
            ProgressEventFixture,
            WalkingSkeletonRunResult,
        )
    ) + (
        PublicDtoManifest(
            "ActionProposal",
            (
                "schema_version",
                "proposal_id",
                "command_id",
                "project_id",
                "room_id",
                "plan_id",
                "scene_version",
                "execution_scope",
                "operation",
                "gate_report_id",
                "gate_profile",
                "binding_artifact_id",
                "binding_artifact_hash",
                "gameplay_manifest",
                "idempotency_key",
                "risk_level",
                "status",
            ),
        ),
        PublicDtoManifest(
            "GameplayManifest",
            (
                "project_id",
                "plan_id",
                "scene_version",
                "entity_bindings",
                "primitives",
                "objective_id",
                "schema_version",
                "content_hash",
            ),
        ),
        PublicDtoManifest(
            "PlanPatch",
            (
                "patch_id",
                "room_id",
                "plan_id",
                "text",
                "patch_type",
                "items",
                "source_user",
                "target_agent",
                "idempotency_key",
                "payload_schema_version",
                "structured_payload",
                "payload_hash",
                "proposal_id",
                "risk_level",
                "status",
                "deferred_reason",
                "created_at",
                "updated_at",
            ),
        ),
    )
    enums = (
        PublicEnumManifest("OwnerDomain", tuple(sorted(OWNER_DOMAINS))),
        PublicEnumManifest("NodeStatus", tuple(sorted(NODE_STATUSES))),
        PublicEnumManifest("BlockedStatus", tuple(sorted(BLOCKED_STATUSES))),
        PublicEnumManifest("PreflightStatus", ("blocked", "completed", "pending_runtime_verification")),
    )
    return SkeletonContractManifest(
        contract_version=SKELETON_CONTRACT_VERSION,
        schema_versions=PUBLIC_SCHEMA_VERSIONS,
        public_protocols=protocols,
        public_dtos=dtos,
        public_enums=enums,
        skeleton_nodes=tuple(zip(SKELETON_NODE_ORDER, SKELETON_INTERFACE_NAMES)),
        skeleton_edges=SKELETON_EDGES,
    )


class DemoScenarioRunner:
    def __init__(
        self,
        *,
        engine_capabilities: EngineCapabilityPort,
        clock,
        planning_reasoner: object | None = None,
        art_reasoner: object | None = None,
        program_reasoner: object | None = None,
        retry_failed_agents: bool = True,
        stage_observer: Callable[[CollaborationStageEvent], None] | None = None,
    ) -> None:
        if not callable(getattr(engine_capabilities, "get_manifest", None)):
            raise TypeError("engine_capabilities must provide get_manifest()")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._engine_capabilities = engine_capabilities
        self._clock = clock
        self._planning_reasoner = planning_reasoner or _PlanningReasoner()
        self._art_reasoner = art_reasoner or _ArtReasoner()
        self._program_reasoner = program_reasoner or _ProgramReasoner()
        self._retry_failed_agents = bool(retry_failed_agents)
        if stage_observer is not None and not callable(stage_observer):
            raise TypeError("stage_observer must be callable")
        self._stage_observer = stage_observer
        self._results: dict[tuple[str, str], tuple[UserCommandFixture, WalkingSkeletonRunResult]] = {}
        self._lock = RLock()

    def run(self, command: UserCommandFixture) -> WalkingSkeletonRunResult:
        if not isinstance(command, UserCommandFixture):
            raise TypeError("run requires UserCommandFixture")
        key = (command.project_id, command.command_id)
        with self._lock:
            previous = self._results.get(key)
            if previous is not None:
                previous_command, previous_result = previous
                if previous_command != command:
                    raise ValueError(f"command_id {command.command_id} was reused with different content")
                return previous_result
            result = self._run_new(command)
            self._results[key] = (command, result)
            return result

    def _run_new(self, command: UserCommandFixture) -> WalkingSkeletonRunResult:

        projects = ProjectStateStore()
        projects.create_project(project_id=command.project_id, room_id=command.room_id, source="walking-skeleton")
        artifacts = ArtifactRegistry(projects)
        graphs = AgentTaskGraphStore(projects, artifacts)
        refs = {
            artifact_type: f"{artifact_id}@1"
            for artifact_type, artifact_id in ARTIFACT_LINEAGE_IDS.items()
        }
        graph_id = f"graph.{command.scenario_id}"
        task_ids = {
            "planning": f"task.{command.scenario_id}.planning",
            "art": f"task.{command.scenario_id}.art",
            "program": f"task.{command.scenario_id}.program",
        }
        tasks = (
            AgentTask(
                task_id=task_ids["planning"],
                assigned_role="planning",
                objective="Produce planning contracts for the demo.",
                input_artifact_refs=(),
                output_types=("GameDesignBrief", "LevelPlan"),
                depends_on=(),
                acceptance_criteria=("planning contracts validate",),
                capability_set=("artifact.write",),
                max_attempts=2,
            ),
            AgentTask(
                task_id=task_ids["program"],
                assigned_role="program",
                objective="Produce non-executable gameplay logic.",
                input_artifact_refs=(refs["GameDesignBrief"], refs["LevelPlan"]),
                output_types=("GameplayLogicPlan",),
                depends_on=(task_ids["planning"],),
                acceptance_criteria=("gameplay logic validates",),
                capability_set=("artifact.read", "artifact.write"),
                max_attempts=2,
            ),
            AgentTask(
                task_id=task_ids["art"],
                assigned_role="art",
                objective="Produce art contracts for the demo from gameplay slots.",
                input_artifact_refs=(
                    refs["GameDesignBrief"],
                    refs["LevelPlan"],
                    refs["GameplayLogicPlan"],
                ),
                output_types=("ArtDirection", "SceneCompositionPlan"),
                depends_on=(task_ids["program"],),
                acceptance_criteria=("art contracts cover every gameplay entity slot",),
                capability_set=("artifact.read", "artifact.write"),
                max_attempts=2,
            ),
        )
        graphs.create_graph(
            graph_id=graph_id,
            project_id=command.project_id,
            tasks=tasks,
            expected_project_version=projects.get(command.project_id).project_version,
            patch_id=f"patch.{command.scenario_id}.graph",
            source="walking-skeleton",
        )

        planning_agent = PlanningAgent(
            project_states=projects,
            artifacts=artifacts,
            task_graphs=graphs,
            reasoner=self._planning_reasoner,
        )
        self._run_stage(
            stage="planning",
            artifact_refs=(refs["GameDesignBrief"], refs["LevelPlan"]),
            remaining_stages=("program", "art", "narration"),
            run_agent=lambda: planning_agent.run(
            PlanningRequest(
                request_id=f"request.{command.scenario_id}.planning",
                project_id=command.project_id,
                graph_id=graph_id,
                task_id=task_ids["planning"],
                project_goal=command.project_goal,
                constraints=("single-player", "non-executable", "no scene writes"),
                acceptance_criteria=("key-door-goal progression is explicit",),
                requested_by=command.requested_by,
            )
            ),
            graphs=graphs,
            graph_id=graph_id,
            task_id=task_ids["planning"],
            retry_failed=self._retry_failed_agents,
        )
        program_agent = ProgramAgent(
            project_states=projects,
            artifacts=artifacts,
            task_graphs=graphs,
            reasoner=self._program_reasoner,
        )
        self._run_stage(
            stage="program",
            artifact_refs=(refs["GameplayLogicPlan"],),
            remaining_stages=("art", "narration"),
            run_agent=lambda: program_agent.run(
            ProgramRequest(
                request_id=f"request.{command.scenario_id}.program",
                project_id=command.project_id,
                graph_id=graph_id,
                task_id=task_ids["program"],
                logic_objective="Define the key, unlock, and goal state progression.",
                constraints=("no scripts", "no scene writes", "non-executable"),
                acceptance_criteria=("states, triggers, rules, and win condition validate",),
                requested_by=command.requested_by,
            )
            ),
            graphs=graphs,
            graph_id=graph_id,
            task_id=task_ids["program"],
            retry_failed=self._retry_failed_agents,
        )
        art_agent = ArtAgent(
            project_states=projects,
            artifacts=artifacts,
            task_graphs=graphs,
            reasoner=self._art_reasoner,
        )
        self._run_stage(
            stage="art",
            artifact_refs=(refs["ArtDirection"], refs["SceneCompositionPlan"]),
            remaining_stages=("narration",),
            run_agent=lambda: art_agent.run(
            ArtRequest(
                request_id=f"request.{command.scenario_id}.art",
                project_id=command.project_id,
                graph_id=graph_id,
                task_id=task_ids["art"],
                art_objective="Define a readable low-detail indoor demo scene.",
                constraints=("no scene writes", "low visual quality is acceptable"),
                acceptance_criteria=("scene requirements cover gameplay slots",),
                requested_by=command.requested_by,
            )
            ),
            graphs=graphs,
            graph_id=graph_id,
            task_id=task_ids["art"],
            retry_failed=self._retry_failed_agents,
        )

        bundle = ProjectArtifactBundleReader(
            project_states=projects,
            artifacts=artifacts,
            task_graphs=graphs,
        ).build(project_id=command.project_id, graph_id=graph_id)
        gate = ProjectGatePreflight(engine_capabilities=self._engine_capabilities)
        preflight = gate.evaluate(bundle)
        capability_result = gate.last_capability_result
        blocked_results = tuple(preflight.blocked_results)

        manifest = build_skeleton_manifest()
        contract_hash = manifest.contract_hash()
        node_statuses = tuple(
            SkeletonNodeStatus(
                node_id=node_id,
                interface_name=interface_name,
                status=(
                    capability_result.status
                    if node_id == "engine_capability_port" and isinstance(capability_result, BlockedResult)
                    else preflight.status
                    if node_id == "project_gate_preflight" and preflight.status != "completed"
                    else "completed"
                ),
                blocker_code=(
                    capability_result.error_code
                    if node_id == "engine_capability_port" and isinstance(capability_result, BlockedResult)
                    else next(
                        (result.error_code for result in preflight.blocked_results if result.node_id == "project_gate_preflight"),
                        "runtime_gate_pending",
                    )
                    if node_id == "project_gate_preflight" and preflight.blocked_results
                    else ""
                ),
                owner_domain=(
                    "frontend"
                    if node_id in {"user_command_fixture", "progress_event_fixture"}
                    else "engine"
                    if node_id == "engine_capability_port"
                    else "integration"
                    if node_id in {"demo_scenario_runner", "demo_result"}
                    else "collaboration"
                ),
                fill_priority=index,
                evidence_refs=(
                    f"Skeleton:{node_id}",
                    *(tuple(capability_result.evidence_refs) if node_id == "engine_capability_port" and isinstance(capability_result, BlockedResult) else ()),
                ),
            )
            for index, (node_id, interface_name) in enumerate(
                zip(SKELETON_NODE_ORDER, SKELETON_INTERFACE_NAMES),
                start=1,
            )
        )
        overall_status = (
            preflight.status
            if preflight.status != "completed"
            else capability_result.status
            if isinstance(capability_result, BlockedResult)
            else "completed"
        )
        report = SkeletonStatusReport(
            contract_version=SKELETON_CONTRACT_VERSION,
            contract_hash=contract_hash,
            nodes=node_statuses,
            overall_status=overall_status,
            generated_at=_utc_text(self._clock()),
        )
        demo_result = DemoResult(
            project_id=command.project_id,
            task_graph_id=graph_id,
            scenario_id=command.scenario_id,
            status="blocked" if overall_status == "blocked" else "integration_ready",
            executable=False,
            artifact_refs=bundle.artifact_refs,
            required_capabilities=tuple(
                sorted(
                    {f"operation:{operation}" for operation in ProjectGatePreflight._REQUIRED_ENGINE_OPERATIONS}
                    | {f"gameplay_primitive:{primitive}" for primitive in ALLOWED_GAMEPLAY_PRIMITIVES}
                )
            ),
            preflight_result=preflight,
            pending_runtime_verifications=tuple(
                result for result in blocked_results if result.status == "pending_runtime_verification"
            ),
            blocked_results=blocked_results,
            skeleton_report=report,
        )
        progress_event = ProgressEventFixture(
            schema_version=FRONTEND_INTERACTION_SCHEMA_VERSION,
            event_id=f"event.{command.command_id}.skeleton",
            command_id=command.command_id,
            scenario_id=command.scenario_id,
            status=overall_status,
            blocked_results=blocked_results,
            skeleton_report=report,
        )
        artifact_payloads = {
            artifact_type: artifacts.current(
                command.project_id,
                ARTIFACT_LINEAGE_IDS[artifact_type],
                require_usable=True,
            ).artifact.payload
            for artifact_type in sorted(ARTIFACT_LINEAGE_IDS)
            if artifact_type in bundle.entries
        }
        return WalkingSkeletonRunResult(
            manifest=manifest,
            preflight=preflight,
            demo_result=demo_result,
            progress_event=progress_event,
            bundle=bundle,
            artifact_payloads=artifact_payloads,
        )

    def _run_stage(
        self,
        *,
        stage: str,
        artifact_refs: tuple[str, ...],
        remaining_stages: tuple[str, ...],
        run_agent: Callable[[], object],
        graphs: AgentTaskGraphStore,
        graph_id: str,
        task_id: str,
        retry_failed: bool,
    ) -> object:
        self._emit_stage(CollaborationStageEvent(
            stage=stage,
            status="in_progress",
        ))
        try:
            result = self._run_with_retry(
                run_agent=run_agent,
                graphs=graphs,
                graph_id=graph_id,
                task_id=task_id,
                retry_failed=retry_failed,
            )
        except Exception as exc:
            self._emit_stage(CollaborationStageEvent(
                stage=stage,
                status="blocked",
                error_code=str(getattr(exc, "error_code", "") or type(exc).__name__),
                field_path=str(getattr(exc, "field_path", "") or ""),
                safe_summary=str(
                    getattr(exc, "safe_summary", "")
                    or f"{type(exc).__name__} blocked the collaboration stage"
                ),
            ))
            for remaining in remaining_stages:
                self._emit_stage(CollaborationStageEvent(
                    stage=remaining,
                    status="not_started",
                ))
            raise
        self._emit_stage(CollaborationStageEvent(
            stage=stage,
            status="completed",
            artifact_refs=artifact_refs,
        ))
        return result

    def _emit_stage(self, event: CollaborationStageEvent) -> None:
        if self._stage_observer is None:
            return
        try:
            self._stage_observer(event)
        except Exception:
            return

    @staticmethod
    def _run_with_retry(
        *,
        run_agent: Callable[[], object],
        graphs: AgentTaskGraphStore,
        graph_id: str,
        task_id: str,
        retry_failed: bool,
    ) -> object:
        while True:
            try:
                return run_agent()
            except Exception:
                if not retry_failed:
                    raise
                record = graphs.get(graph_id).task(task_id)
                if record.status != "failed" or record.attempt_count >= record.task.max_attempts:
                    raise
                graphs.retry_task(graph_id, task_id, source=f"demo-runner:{task_id}:retry")
