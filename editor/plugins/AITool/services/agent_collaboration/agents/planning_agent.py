from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Mapping, Protocol

from ..artifact_registry import ArtifactNotFoundError, ArtifactRef, ArtifactRegistry
from ..contracts import ARTIFACT_LINEAGE_IDS, ArtifactEnvelope, GameDesignBrief, LevelPlan
from ..project_state import ProjectStateStore
from ..task_graph import AgentTaskGraphStore, TaskTransitionError


GAME_DESIGN_BRIEF_ID = ARTIFACT_LINEAGE_IDS["GameDesignBrief"]
LEVEL_PLAN_ID = ARTIFACT_LINEAGE_IDS["LevelPlan"]
PLANNING_OUTPUT_TYPES = frozenset({"GameDesignBrief", "LevelPlan"})


class PlanningAgentError(RuntimeError):
    pass


class PlanningIsolationError(PlanningAgentError):
    pass


class PlanningContextStaleError(PlanningAgentError):
    pass


class PlanningOutputValidationError(PlanningAgentError):
    pass


def _text(value: object) -> str:
    return str(value or "").strip()


def _text_tuple(values, *, field_name: str, allow_empty: bool = True) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise TypeError(f"{field_name} must be a sequence")
    normalized: list[str] = []
    for value in values:
        text = _text(value)
        if not text:
            raise ValueError(f"{field_name} cannot contain empty values")
        if text not in normalized:
            normalized.append(text)
    if not normalized and not allow_empty:
        raise ValueError(f"{field_name} cannot be empty")
    return tuple(normalized)


@dataclass(frozen=True)
class PlanningRequest:
    request_id: str
    project_id: str
    graph_id: str
    task_id: str
    project_goal: str
    constraints: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    requested_by: str

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "project_id",
            "graph_id",
            "task_id",
            "project_goal",
            "requested_by",
        ):
            normalized = _text(getattr(self, field_name))
            if not normalized:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, normalized)
        object.__setattr__(
            self,
            "constraints",
            _text_tuple(self.constraints, field_name="constraints"),
        )
        object.__setattr__(
            self,
            "acceptance_criteria",
            _text_tuple(
                self.acceptance_criteria,
                field_name="acceptance_criteria",
                allow_empty=False,
            ),
        )


@dataclass(frozen=True)
class PlanningArtifactContext:
    artifact_ref: str
    artifact_type: str
    version: int
    content_hash: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class PlanningContext:
    project_id: str
    project_version: int
    prior_artifacts: tuple[PlanningArtifactContext, ...]


@dataclass(frozen=True)
class PlanningAgentDraft:
    game_design_brief: GameDesignBrief
    level_plan: LevelPlan

    def __post_init__(self) -> None:
        if not isinstance(self.game_design_brief, GameDesignBrief):
            raise TypeError("game_design_brief must be GameDesignBrief")
        if not isinstance(self.level_plan, LevelPlan):
            raise TypeError("level_plan must be LevelPlan")


class PlanningReasoner(Protocol):
    def generate(self, request: PlanningRequest, context: PlanningContext) -> PlanningAgentDraft:
        ...


@dataclass(frozen=True)
class PlanningAgentResult:
    request_id: str
    project_id: str
    graph_id: str
    task_id: str
    artifact_refs: tuple[str, ...]
    project_version: int
    graph_version: int


class PlanningAgent:
    """Produces planning Artifacts without reading or mutating scene Runtime facts."""

    def __init__(
        self,
        *,
        project_states: ProjectStateStore,
        artifacts: ArtifactRegistry,
        task_graphs: AgentTaskGraphStore,
        reasoner: PlanningReasoner,
    ) -> None:
        if not isinstance(project_states, ProjectStateStore):
            raise TypeError("PlanningAgent requires ProjectStateStore")
        if not isinstance(artifacts, ArtifactRegistry):
            raise TypeError("PlanningAgent requires ArtifactRegistry")
        if not isinstance(task_graphs, AgentTaskGraphStore):
            raise TypeError("PlanningAgent requires AgentTaskGraphStore")
        if not callable(getattr(reasoner, "generate", None)):
            raise TypeError("reasoner must provide generate(request, context)")
        self._project_states = project_states
        self._artifacts = artifacts
        self._task_graphs = task_graphs
        self._reasoner = reasoner
        self._results: dict[tuple[str, str], tuple[PlanningRequest, PlanningAgentResult]] = {}
        self._lock = RLock()

    def run(self, request: PlanningRequest) -> PlanningAgentResult:
        if not isinstance(request, PlanningRequest):
            raise TypeError("run requires PlanningRequest")
        result_key = (request.project_id, request.request_id)
        with self._lock:
            previous = self._results.get(result_key)
            if previous is not None:
                previous_request, previous_result = previous
                if previous_request != request:
                    raise PlanningAgentError(
                        f"request_id {request.request_id} was reused with different content"
                    )
                return previous_result

            graph = self._task_graphs.refresh(
                request.graph_id,
                source=f"planning-agent:{request.request_id}:preflight",
            )
            if graph.project_id != request.project_id:
                raise PlanningAgentError("task graph belongs to a different project")
            task_record = graph.task(request.task_id)
            task = task_record.task
            if task.assigned_role != "planning":
                raise PlanningAgentError(f"{request.task_id}: task is not assigned to planning")
            if set(task.output_types) != PLANNING_OUTPUT_TYPES:
                raise PlanningAgentError(
                    f"{request.task_id}: planning task must declare GameDesignBrief and LevelPlan"
                )
            if task_record.status != "ready":
                raise TaskTransitionError(
                    f"{request.task_id}: expected ready, got {task_record.status}"
                )

            context = self._build_context(request.project_id, task.input_artifact_refs)
            self._task_graphs.start_task(
                request.graph_id,
                request.task_id,
                source=f"planning-agent:{request.request_id}",
            )
            try:
                draft = self._reasoner.generate(request, context)
                if not isinstance(draft, PlanningAgentDraft):
                    raise PlanningOutputValidationError(
                        "reasoner must return PlanningAgentDraft"
                    )
                current_project = self._project_states.get(request.project_id)
                if current_project.project_version != context.project_version:
                    raise PlanningContextStaleError(
                        f"project changed from version {context.project_version} "
                        f"to {current_project.project_version} while planning"
                    )

                brief_version = self._next_version(request.project_id, GAME_DESIGN_BRIEF_ID)
                level_version = self._next_version(request.project_id, LEVEL_PLAN_ID)
                brief_ref = ArtifactRef(GAME_DESIGN_BRIEF_ID, brief_version)
                level_ref = ArtifactRef(LEVEL_PLAN_ID, level_version)
                output_lineages = {GAME_DESIGN_BRIEF_ID, LEVEL_PLAN_ID}
                external_inputs = tuple(
                    value
                    for value in task.input_artifact_refs
                    if ArtifactRef.parse(value).artifact_id not in output_lineages
                )
                brief = ArtifactEnvelope(
                    artifact_id=GAME_DESIGN_BRIEF_ID,
                    artifact_type="GameDesignBrief",
                    version=brief_version,
                    producer_role="planning",
                    source_task_id=request.task_id,
                    base_project_version=context.project_version,
                    base_world_version=0,
                    dependencies=external_inputs,
                    snapshot_source="none",
                    non_executable=True,
                    status="validated",
                    payload=draft.game_design_brief,
                )
                level = ArtifactEnvelope(
                    artifact_id=LEVEL_PLAN_ID,
                    artifact_type="LevelPlan",
                    version=level_version,
                    producer_role="planning",
                    source_task_id=request.task_id,
                    base_project_version=context.project_version,
                    base_world_version=0,
                    dependencies=(str(brief_ref),),
                    snapshot_source="none",
                    non_executable=True,
                    status="validated",
                    payload=draft.level_plan,
                )
                self._artifacts.register_many(
                    project_id=request.project_id,
                    artifacts=(brief, level),
                    expected_project_version=context.project_version,
                    patch_id=f"planning-artifacts-{request.request_id}",
                    source=f"planning-agent:{request.request_id}",
                )
                graph = self._task_graphs.complete_task(
                    request.graph_id,
                    request.task_id,
                    output_artifact_refs=(str(brief_ref), str(level_ref)),
                    source=f"planning-agent:{request.request_id}",
                )
                project = self._project_states.get(request.project_id)
                result = PlanningAgentResult(
                    request_id=request.request_id,
                    project_id=request.project_id,
                    graph_id=request.graph_id,
                    task_id=request.task_id,
                    artifact_refs=tuple(sorted((str(brief_ref), str(level_ref)))),
                    project_version=project.project_version,
                    graph_version=graph.version,
                )
                self._results[result_key] = (request, result)
                return result
            except Exception as exc:
                try:
                    self._task_graphs.fail_task(
                        request.graph_id,
                        request.task_id,
                        error=f"{type(exc).__name__}: {_text(exc)}",
                        source=f"planning-agent:{request.request_id}",
                    )
                except TaskTransitionError:
                    pass
                raise

    def _build_context(
        self,
        project_id: str,
        input_artifact_refs: tuple[str, ...],
    ) -> PlanningContext:
        project = self._project_states.get(project_id)
        records = {
            str(record.ref): record
            for record in self._artifacts.list_current(project_id, include_stale=False)
            if record.artifact.producer_role == "planning"
        }
        for value in input_artifact_refs:
            try:
                record = self._artifacts.get(project_id, value)
            except ArtifactNotFoundError as exc:
                raise PlanningAgentError(f"missing input Artifact {value}") from exc
            if not record.usable:
                raise PlanningAgentError(f"input Artifact {value} is not usable")
            records[str(record.ref)] = record

        contexts: list[PlanningArtifactContext] = []
        for artifact_ref, record in sorted(records.items()):
            artifact = record.artifact
            if artifact.snapshot_source != "none":
                raise PlanningIsolationError(
                    f"planning Agent cannot consume {artifact.snapshot_source} Artifact {artifact_ref}"
                )
            contexts.append(
                PlanningArtifactContext(
                    artifact_ref=artifact_ref,
                    artifact_type=artifact.artifact_type,
                    version=artifact.version,
                    content_hash=artifact.content_hash,
                    payload=artifact.payload,
                )
            )
        return PlanningContext(
            project_id=project.project_id,
            project_version=project.project_version,
            prior_artifacts=tuple(contexts),
        )

    def _next_version(self, project_id: str, artifact_id: str) -> int:
        try:
            current = self._artifacts.current(
                project_id,
                artifact_id,
                require_usable=False,
            )
        except ArtifactNotFoundError:
            return 1
        return current.ref.version + 1
