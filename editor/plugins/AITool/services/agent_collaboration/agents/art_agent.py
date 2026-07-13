from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Mapping, Protocol

from ..artifact_registry import ArtifactNotFoundError, ArtifactRef, ArtifactRegistry
from ..contracts import ArtDirection, ArtifactEnvelope, SceneCompositionPlan
from ..project_state import ProjectStateStore
from ..task_graph import AgentTaskGraphStore, TaskTransitionError


ART_DIRECTION_ID = "art.direction"
SCENE_COMPOSITION_PLAN_ID = "art.scene-composition"
ART_OUTPUT_TYPES = frozenset({"ArtDirection", "SceneCompositionPlan"})
ART_INPUT_TYPES = frozenset({"GameDesignBrief", "LevelPlan"})


class ArtAgentError(RuntimeError):
    pass


class ArtIsolationError(ArtAgentError):
    pass


class ArtContextStaleError(ArtAgentError):
    pass


class ArtInputValidationError(ArtAgentError):
    pass


class ArtOutputValidationError(ArtAgentError):
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
class ArtRequest:
    request_id: str
    project_id: str
    graph_id: str
    task_id: str
    art_objective: str
    constraints: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    requested_by: str

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "project_id",
            "graph_id",
            "task_id",
            "art_objective",
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
class ArtInputArtifactContext:
    artifact_ref: str
    artifact_type: str
    version: int
    content_hash: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class ArtContext:
    project_id: str
    project_version: int
    planning_artifacts: tuple[ArtInputArtifactContext, ...]


@dataclass(frozen=True)
class ArtAgentDraft:
    art_direction: ArtDirection
    scene_composition_plan: SceneCompositionPlan

    def __post_init__(self) -> None:
        if not isinstance(self.art_direction, ArtDirection):
            raise TypeError("art_direction must be ArtDirection")
        if not isinstance(self.scene_composition_plan, SceneCompositionPlan):
            raise TypeError("scene_composition_plan must be SceneCompositionPlan")


class ArtReasoner(Protocol):
    def generate(self, request: ArtRequest, context: ArtContext) -> ArtAgentDraft:
        ...


@dataclass(frozen=True)
class ArtAgentResult:
    request_id: str
    project_id: str
    graph_id: str
    task_id: str
    artifact_refs: tuple[str, ...]
    project_version: int
    graph_version: int


class ArtAgent:
    """Produces non-executing art contracts from explicit planning Artifact versions."""

    def __init__(
        self,
        *,
        project_states: ProjectStateStore,
        artifacts: ArtifactRegistry,
        task_graphs: AgentTaskGraphStore,
        reasoner: ArtReasoner,
    ) -> None:
        if not isinstance(project_states, ProjectStateStore):
            raise TypeError("ArtAgent requires ProjectStateStore")
        if not isinstance(artifacts, ArtifactRegistry):
            raise TypeError("ArtAgent requires ArtifactRegistry")
        if not isinstance(task_graphs, AgentTaskGraphStore):
            raise TypeError("ArtAgent requires AgentTaskGraphStore")
        if not callable(getattr(reasoner, "generate", None)):
            raise TypeError("reasoner must provide generate(request, context)")
        self._project_states = project_states
        self._artifacts = artifacts
        self._task_graphs = task_graphs
        self._reasoner = reasoner
        self._results: dict[tuple[str, str], tuple[ArtRequest, ArtAgentResult]] = {}
        self._lock = RLock()

    def run(self, request: ArtRequest) -> ArtAgentResult:
        if not isinstance(request, ArtRequest):
            raise TypeError("run requires ArtRequest")
        result_key = (request.project_id, request.request_id)
        with self._lock:
            previous = self._results.get(result_key)
            if previous is not None:
                previous_request, previous_result = previous
                if previous_request != request:
                    raise ArtAgentError(
                        f"request_id {request.request_id} was reused with different content"
                    )
                return previous_result

            graph = self._task_graphs.get(request.graph_id)
            if graph.project_id != request.project_id:
                raise ArtAgentError("task graph belongs to a different project")
            task_record = graph.task(request.task_id)
            task = task_record.task
            if task.assigned_role != "art":
                raise ArtAgentError(f"{request.task_id}: task is not assigned to art")
            if set(task.output_types) != ART_OUTPUT_TYPES:
                raise ArtAgentError(
                    f"{request.task_id}: art task must declare ArtDirection "
                    "and SceneCompositionPlan"
                )

            context = self._build_context(request.project_id, task.input_artifact_refs)
            if task_record.status != "ready":
                raise TaskTransitionError(
                    f"{request.task_id}: expected ready, got {task_record.status}"
                )

            self._task_graphs.start_task(
                request.graph_id,
                request.task_id,
                source=f"art-agent:{request.request_id}",
            )
            try:
                draft = self._reasoner.generate(request, context)
                if not isinstance(draft, ArtAgentDraft):
                    raise ArtOutputValidationError("reasoner must return ArtAgentDraft")
                current_project = self._project_states.get(request.project_id)
                if current_project.project_version != context.project_version:
                    raise ArtContextStaleError(
                        f"project changed from version {context.project_version} "
                        f"to {current_project.project_version} while producing art contracts"
                    )

                direction_version = self._next_version(request.project_id, ART_DIRECTION_ID)
                composition_version = self._next_version(
                    request.project_id,
                    SCENE_COMPOSITION_PLAN_ID,
                )
                direction_ref = ArtifactRef(ART_DIRECTION_ID, direction_version)
                composition_ref = ArtifactRef(
                    SCENE_COMPOSITION_PLAN_ID,
                    composition_version,
                )
                planning_refs = tuple(
                    item.artifact_ref for item in context.planning_artifacts
                )
                direction = ArtifactEnvelope(
                    artifact_id=ART_DIRECTION_ID,
                    artifact_type="ArtDirection",
                    version=direction_version,
                    producer_role="art",
                    source_task_id=request.task_id,
                    base_project_version=context.project_version,
                    base_world_version=0,
                    dependencies=planning_refs,
                    snapshot_source="none",
                    non_executable=True,
                    status="validated",
                    payload=draft.art_direction,
                )
                composition = ArtifactEnvelope(
                    artifact_id=SCENE_COMPOSITION_PLAN_ID,
                    artifact_type="SceneCompositionPlan",
                    version=composition_version,
                    producer_role="art",
                    source_task_id=request.task_id,
                    base_project_version=context.project_version,
                    base_world_version=0,
                    dependencies=(*planning_refs, str(direction_ref)),
                    snapshot_source="none",
                    non_executable=True,
                    status="validated",
                    payload=draft.scene_composition_plan,
                )
                self._artifacts.register_many(
                    project_id=request.project_id,
                    artifacts=(direction, composition),
                    expected_project_version=context.project_version,
                    patch_id=f"art-artifacts-{request.request_id}",
                    source=f"art-agent:{request.request_id}",
                )
                graph = self._task_graphs.complete_task(
                    request.graph_id,
                    request.task_id,
                    output_artifact_refs=(str(direction_ref), str(composition_ref)),
                    source=f"art-agent:{request.request_id}",
                )
                project = self._project_states.get(request.project_id)
                result = ArtAgentResult(
                    request_id=request.request_id,
                    project_id=request.project_id,
                    graph_id=request.graph_id,
                    task_id=request.task_id,
                    artifact_refs=tuple(sorted((str(direction_ref), str(composition_ref)))),
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
                        source=f"art-agent:{request.request_id}",
                    )
                except TaskTransitionError:
                    pass
                raise

    def _build_context(
        self,
        project_id: str,
        input_artifact_refs: tuple[str, ...],
    ) -> ArtContext:
        project = self._project_states.get(project_id)
        records_by_type = {}
        for value in input_artifact_refs:
            try:
                record = self._artifacts.get(project_id, value)
            except ArtifactNotFoundError as exc:
                raise ArtInputValidationError(f"missing input Artifact {value}") from exc
            if not record.usable:
                raise ArtInputValidationError(f"input Artifact {value} is not usable")
            artifact = record.artifact
            if artifact.artifact_type not in ART_INPUT_TYPES:
                raise ArtInputValidationError(
                    f"art Agent cannot consume {artifact.artifact_type} input {value}"
                )
            if artifact.producer_role != "planning":
                raise ArtInputValidationError(
                    f"{value}: expected planning producer, got {artifact.producer_role}"
                )
            if artifact.snapshot_source != "none":
                raise ArtIsolationError(
                    f"art Agent cannot consume {artifact.snapshot_source} Artifact {value} "
                    "while the collaboration Gate is red"
                )
            if not artifact.non_executable:
                raise ArtIsolationError(f"planning input {value} must be non_executable")
            if artifact.artifact_type in records_by_type:
                raise ArtInputValidationError(
                    f"duplicate {artifact.artifact_type} inputs are not allowed"
                )
            records_by_type[artifact.artifact_type] = record

        missing_types = ART_INPUT_TYPES - set(records_by_type)
        if missing_types:
            raise ArtInputValidationError(
                f"art task is missing required planning inputs {sorted(missing_types)}"
            )
        if len(records_by_type) != len(input_artifact_refs):
            raise ArtInputValidationError("art task inputs must be explicit unique Artifact refs")

        contexts = tuple(
            ArtInputArtifactContext(
                artifact_ref=str(record.ref),
                artifact_type=record.artifact.artifact_type,
                version=record.artifact.version,
                content_hash=record.artifact.content_hash,
                payload=record.artifact.payload,
            )
            for _artifact_type, record in sorted(records_by_type.items())
        )
        return ArtContext(
            project_id=project.project_id,
            project_version=project.project_version,
            planning_artifacts=contexts,
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
