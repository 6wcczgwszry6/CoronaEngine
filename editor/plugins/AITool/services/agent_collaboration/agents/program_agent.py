from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Mapping, Protocol

from ..artifact_registry import ArtifactNotFoundError, ArtifactRef, ArtifactRegistry
from ..contracts import ARTIFACT_LINEAGE_IDS, ArtifactEnvelope, GameplayLogicPlan
from ..project_state import ProjectStateStore
from ..task_graph import AgentTaskGraphStore, TaskTransitionError


GAMEPLAY_LOGIC_PLAN_ID = ARTIFACT_LINEAGE_IDS["GameplayLogicPlan"]
PROGRAM_OUTPUT_TYPES = frozenset({"GameplayLogicPlan"})
PROGRAM_REQUIRED_INPUT_TYPES = frozenset({"GameDesignBrief", "LevelPlan"})
PROGRAM_OPTIONAL_INPUT_TYPES = frozenset({"ArtDirection"})
PROGRAM_INPUT_PRODUCERS = {
    "GameDesignBrief": "planning",
    "LevelPlan": "planning",
    "ArtDirection": "art",
}
PROGRAM_ALLOWED_CAPABILITIES = frozenset({"artifact.read", "artifact.write"})


class ProgramAgentError(RuntimeError):
    pass


class ProgramIsolationError(ProgramAgentError):
    pass


class ProgramCapabilityError(ProgramAgentError):
    pass


class ProgramContextStaleError(ProgramAgentError):
    pass


class ProgramInputValidationError(ProgramAgentError):
    pass


class ProgramOutputValidationError(ProgramAgentError):
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
class ProgramRequest:
    request_id: str
    project_id: str
    graph_id: str
    task_id: str
    logic_objective: str
    constraints: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    requested_by: str

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "project_id",
            "graph_id",
            "task_id",
            "logic_objective",
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
class ProgramInputArtifactContext:
    artifact_ref: str
    artifact_type: str
    version: int
    content_hash: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class ProgramContext:
    project_id: str
    project_version: int
    input_artifacts: tuple[ProgramInputArtifactContext, ...]


@dataclass(frozen=True)
class ProgramAgentDraft:
    gameplay_logic_plan: GameplayLogicPlan

    def __post_init__(self) -> None:
        if not isinstance(self.gameplay_logic_plan, GameplayLogicPlan):
            raise TypeError("gameplay_logic_plan must be GameplayLogicPlan")


class ProgramReasoner(Protocol):
    def generate(self, request: ProgramRequest, context: ProgramContext) -> ProgramAgentDraft:
        ...


@dataclass(frozen=True)
class ProgramAgentResult:
    request_id: str
    project_id: str
    graph_id: str
    task_id: str
    artifact_refs: tuple[str, ...]
    project_version: int
    graph_version: int


class ProgramAgent:
    """Produces non-executing gameplay logic contracts from explicit Artifact versions."""

    def __init__(
        self,
        *,
        project_states: ProjectStateStore,
        artifacts: ArtifactRegistry,
        task_graphs: AgentTaskGraphStore,
        reasoner: ProgramReasoner,
    ) -> None:
        if not isinstance(project_states, ProjectStateStore):
            raise TypeError("ProgramAgent requires ProjectStateStore")
        if not isinstance(artifacts, ArtifactRegistry):
            raise TypeError("ProgramAgent requires ArtifactRegistry")
        if not isinstance(task_graphs, AgentTaskGraphStore):
            raise TypeError("ProgramAgent requires AgentTaskGraphStore")
        if not callable(getattr(reasoner, "generate", None)):
            raise TypeError("reasoner must provide generate(request, context)")
        self._project_states = project_states
        self._artifacts = artifacts
        self._task_graphs = task_graphs
        self._reasoner = reasoner
        self._results: dict[tuple[str, str], tuple[ProgramRequest, ProgramAgentResult]] = {}
        self._lock = RLock()

    def run(self, request: ProgramRequest) -> ProgramAgentResult:
        if not isinstance(request, ProgramRequest):
            raise TypeError("run requires ProgramRequest")
        result_key = (request.project_id, request.request_id)
        with self._lock:
            previous = self._results.get(result_key)
            if previous is not None:
                previous_request, previous_result = previous
                if previous_request != request:
                    raise ProgramAgentError(
                        f"request_id {request.request_id} was reused with different content"
                    )
                return previous_result

            graph = self._task_graphs.get(request.graph_id)
            if graph.project_id != request.project_id:
                raise ProgramAgentError("task graph belongs to a different project")
            task_record = graph.task(request.task_id)
            task = task_record.task
            if task.assigned_role != "program":
                raise ProgramAgentError(f"{request.task_id}: task is not assigned to program")
            if set(task.output_types) != PROGRAM_OUTPUT_TYPES:
                raise ProgramAgentError(
                    f"{request.task_id}: program task must declare GameplayLogicPlan"
                )
            self._validate_capabilities(task.capability_set)

            context = self._build_context(request.project_id, task.input_artifact_refs)
            if task_record.status != "ready":
                raise TaskTransitionError(
                    f"{request.task_id}: expected ready, got {task_record.status}"
                )

            self._task_graphs.start_task(
                request.graph_id,
                request.task_id,
                source=f"program-agent:{request.request_id}",
            )
            try:
                draft = self._reasoner.generate(request, context)
                if not isinstance(draft, ProgramAgentDraft):
                    raise ProgramOutputValidationError(
                        "reasoner must return ProgramAgentDraft"
                    )
                current_project = self._project_states.get(request.project_id)
                if current_project.project_version != context.project_version:
                    raise ProgramContextStaleError(
                        f"project changed from version {context.project_version} "
                        f"to {current_project.project_version} while producing gameplay logic"
                    )

                logic_version = self._next_version(
                    request.project_id,
                    GAMEPLAY_LOGIC_PLAN_ID,
                )
                logic_ref = ArtifactRef(GAMEPLAY_LOGIC_PLAN_ID, logic_version)
                artifact = ArtifactEnvelope(
                    artifact_id=GAMEPLAY_LOGIC_PLAN_ID,
                    artifact_type="GameplayLogicPlan",
                    version=logic_version,
                    producer_role="program",
                    source_task_id=request.task_id,
                    base_project_version=context.project_version,
                    base_world_version=0,
                    dependencies=tuple(
                        item.artifact_ref for item in context.input_artifacts
                    ),
                    snapshot_source="none",
                    non_executable=True,
                    status="validated",
                    payload=draft.gameplay_logic_plan,
                )
                self._artifacts.register(
                    project_id=request.project_id,
                    artifact=artifact,
                    expected_project_version=context.project_version,
                    patch_id=f"program-artifact-{request.request_id}",
                    source=f"program-agent:{request.request_id}",
                )
                graph = self._task_graphs.complete_task(
                    request.graph_id,
                    request.task_id,
                    output_artifact_refs=(str(logic_ref),),
                    source=f"program-agent:{request.request_id}",
                )
                project = self._project_states.get(request.project_id)
                result = ProgramAgentResult(
                    request_id=request.request_id,
                    project_id=request.project_id,
                    graph_id=request.graph_id,
                    task_id=request.task_id,
                    artifact_refs=(str(logic_ref),),
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
                        source=f"program-agent:{request.request_id}",
                    )
                except TaskTransitionError:
                    pass
                raise

    @staticmethod
    def _validate_capabilities(capability_set: tuple[str, ...]) -> None:
        capabilities = set(capability_set)
        forbidden = capabilities - PROGRAM_ALLOWED_CAPABILITIES
        if forbidden:
            raise ProgramCapabilityError(
                f"program task declares forbidden capabilities {sorted(forbidden)}"
            )
        if "artifact.write" not in capabilities:
            raise ProgramCapabilityError("program task must declare artifact.write")

    def _build_context(
        self,
        project_id: str,
        input_artifact_refs: tuple[str, ...],
    ) -> ProgramContext:
        project = self._project_states.get(project_id)
        records_by_type = {}
        allowed_types = PROGRAM_REQUIRED_INPUT_TYPES | PROGRAM_OPTIONAL_INPUT_TYPES
        for value in input_artifact_refs:
            try:
                record = self._artifacts.get(project_id, value)
            except ArtifactNotFoundError as exc:
                raise ProgramInputValidationError(f"missing input Artifact {value}") from exc
            if not record.usable:
                raise ProgramInputValidationError(f"input Artifact {value} is not usable")
            artifact = record.artifact
            if artifact.artifact_type not in allowed_types:
                raise ProgramInputValidationError(
                    f"program Agent cannot consume {artifact.artifact_type} input {value}"
                )
            expected_producer = PROGRAM_INPUT_PRODUCERS[artifact.artifact_type]
            if artifact.producer_role != expected_producer:
                raise ProgramInputValidationError(
                    f"{value}: expected {expected_producer} producer, "
                    f"got {artifact.producer_role}"
                )
            if artifact.snapshot_source != "none":
                raise ProgramIsolationError(
                    f"program Agent cannot consume {artifact.snapshot_source} Artifact {value} "
                    "while the collaboration Gate is red"
                )
            if not artifact.non_executable:
                raise ProgramIsolationError(f"input {value} must be non_executable")
            if artifact.artifact_type in records_by_type:
                raise ProgramInputValidationError(
                    f"duplicate {artifact.artifact_type} inputs are not allowed"
                )
            records_by_type[artifact.artifact_type] = record

        missing_types = PROGRAM_REQUIRED_INPUT_TYPES - set(records_by_type)
        if missing_types:
            raise ProgramInputValidationError(
                f"program task is missing required planning inputs {sorted(missing_types)}"
            )
        if len(records_by_type) != len(input_artifact_refs):
            raise ProgramInputValidationError(
                "program task inputs must be explicit unique Artifact refs"
            )

        contexts = tuple(
            ProgramInputArtifactContext(
                artifact_ref=str(record.ref),
                artifact_type=record.artifact.artifact_type,
                version=record.artifact.version,
                content_hash=record.artifact.content_hash,
                payload=record.artifact.payload,
            )
            for _artifact_type, record in sorted(records_by_type.items())
        )
        return ProgramContext(
            project_id=project.project_id,
            project_version=project.project_version,
            input_artifacts=contexts,
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
