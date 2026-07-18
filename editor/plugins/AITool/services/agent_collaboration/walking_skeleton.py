from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
    AgentTask,
    ArtDirection,
    GameDesignBrief,
    GameplayLogicPlan,
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
    "art_agent",
    "program_agent",
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
    "ArtAgentPort.run",
    "ProgramAgentPort.run",
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
        if self.status not in {"completed", "blocked"}:
            raise ValueError(f"unsupported preflight result: {self.status}")
        checks = tuple(self.checks)
        if not checks or not all(isinstance(item, PreflightCheck) for item in checks):
            raise ValueError("checks must contain PreflightCheck values")
        object.__setattr__(self, "checks", checks)
        blocked = tuple(self.blocked_results)
        if not all(isinstance(item, BlockedResult) for item in blocked):
            raise ValueError("blocked_results must contain BlockedResult values")
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
    scenario_id: str
    status: str
    executable: bool
    artifact_refs: tuple[str, ...]
    blocked_results: tuple[BlockedResult, ...]
    skeleton_report: SkeletonStatusReport

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _required_text(self.scenario_id, "scenario_id"))
        if self.status not in {"completed", *BLOCKED_STATUSES}:
            raise ValueError(f"unsupported demo result status: {self.status}")
        if self.executable:
            raise ValueError("Walking Skeleton DemoResult cannot be executable")
        object.__setattr__(self, "artifact_refs", tuple(sorted(_text_tuple(self.artifact_refs, "artifact_refs", allow_empty=False))))
        blocked = tuple(self.blocked_results)
        if not all(isinstance(item, BlockedResult) for item in blocked):
            raise ValueError("blocked_results must contain BlockedResult values")
        if self.status in BLOCKED_STATUSES and not blocked:
            raise ValueError("blocked DemoResult requires blocked_results")
        object.__setattr__(self, "blocked_results", blocked)
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
    def generate(self, _request, _context) -> ArtAgentDraft:
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
                entity_requirements=("player_spawn", "collectible_key", "locked_door", "goal_zone"),
                layout_rules=("keep a clear route from spawn to goal",),
            ),
        )


class _ProgramReasoner:
    def generate(self, _request, _context) -> ProgramAgentDraft:
        return ProgramAgentDraft(
            gameplay_logic_plan=GameplayLogicPlan(
                states=("key_available", "key_collected", "door_unlocked", "objective_complete"),
                triggers=("collect_key", "enter_unlocked_door", "enter_goal_zone"),
                rules=("door requires key_collected", "goal requires door_unlocked"),
                win_conditions=("objective_complete",),
                lose_conditions=("none",),
            )
        )


class ProjectGatePreflight:
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
        blocked_results = ()
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
        return ProjectGatePreflightResult(
            status="blocked" if failed else "completed",
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
    )
    enums = (
        PublicEnumManifest("OwnerDomain", tuple(sorted(OWNER_DOMAINS))),
        PublicEnumManifest("NodeStatus", tuple(sorted(NODE_STATUSES))),
        PublicEnumManifest("BlockedStatus", tuple(sorted(BLOCKED_STATUSES))),
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
    def __init__(self, *, engine_capabilities: EngineCapabilityPort, clock) -> None:
        if not callable(getattr(engine_capabilities, "get_manifest", None)):
            raise TypeError("engine_capabilities must provide get_manifest()")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._engine_capabilities = engine_capabilities
        self._clock = clock

    def run(self, command: UserCommandFixture) -> WalkingSkeletonRunResult:
        if not isinstance(command, UserCommandFixture):
            raise TypeError("run requires UserCommandFixture")

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
            ),
            AgentTask(
                task_id=task_ids["art"],
                assigned_role="art",
                objective="Produce art contracts for the demo.",
                input_artifact_refs=(refs["GameDesignBrief"], refs["LevelPlan"]),
                output_types=("ArtDirection", "SceneCompositionPlan"),
                depends_on=(task_ids["planning"],),
                acceptance_criteria=("art contracts validate",),
                capability_set=("artifact.write",),
            ),
            AgentTask(
                task_id=task_ids["program"],
                assigned_role="program",
                objective="Produce non-executable gameplay logic.",
                input_artifact_refs=(refs["GameDesignBrief"], refs["LevelPlan"], refs["ArtDirection"]),
                output_types=("GameplayLogicPlan",),
                depends_on=(task_ids["art"],),
                acceptance_criteria=("gameplay logic validates",),
                capability_set=("artifact.read", "artifact.write"),
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

        PlanningAgent(
            project_states=projects,
            artifacts=artifacts,
            task_graphs=graphs,
            reasoner=_PlanningReasoner(),
        ).run(
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
        )
        ArtAgent(
            project_states=projects,
            artifacts=artifacts,
            task_graphs=graphs,
            reasoner=_ArtReasoner(),
        ).run(
            ArtRequest(
                request_id=f"request.{command.scenario_id}.art",
                project_id=command.project_id,
                graph_id=graph_id,
                task_id=task_ids["art"],
                art_objective="Define a readable low-detail indoor demo scene.",
                constraints=("no scene writes", "low visual quality is acceptable"),
                acceptance_criteria=("scene requirements are structured",),
                requested_by=command.requested_by,
            )
        )
        ProgramAgent(
            project_states=projects,
            artifacts=artifacts,
            task_graphs=graphs,
            reasoner=_ProgramReasoner(),
        ).run(
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
        )

        bundle = ProjectArtifactBundleReader(
            project_states=projects,
            artifacts=artifacts,
            task_graphs=graphs,
        ).build(project_id=command.project_id, graph_id=graph_id)
        preflight = ProjectGatePreflight().evaluate(bundle)
        capability_result = self._engine_capabilities.get_manifest()
        blocked_results = tuple(preflight.blocked_results)
        if isinstance(capability_result, BlockedResult):
            blocked_results += (capability_result,)

        manifest = build_skeleton_manifest()
        contract_hash = manifest.contract_hash()
        node_statuses = tuple(
            SkeletonNodeStatus(
                node_id=node_id,
                interface_name=interface_name,
                status=(
                    capability_result.status
                    if node_id == "engine_capability_port" and isinstance(capability_result, BlockedResult)
                    else "blocked"
                    if node_id == "project_gate_preflight" and preflight.status == "blocked"
                    else "completed"
                ),
                blocker_code=(
                    capability_result.error_code
                    if node_id == "engine_capability_port" and isinstance(capability_result, BlockedResult)
                    else preflight.blocked_results[0].error_code
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
            "blocked"
            if preflight.status == "blocked"
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
            scenario_id=command.scenario_id,
            status=overall_status,
            executable=False,
            artifact_refs=bundle.artifact_refs,
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
        return WalkingSkeletonRunResult(
            manifest=manifest,
            preflight=preflight,
            demo_result=demo_result,
            progress_event=progress_event,
        )
