from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from threading import RLock
from types import MappingProxyType
from typing import Iterable, Mapping

from .artifact_registry import (
    ArtifactNotFoundError,
    ArtifactRef,
    ArtifactRegistry,
)
from .contracts import AgentTask
from .project_state import ProjectStatePatch, ProjectStateStore


GRAPH_STATUSES = frozenset({"pending", "ready", "in_progress", "blocked", "failed", "completed"})


class AgentTaskGraphError(RuntimeError):
    pass


class TaskGraphNotFoundError(AgentTaskGraphError):
    pass


class TaskGraphAlreadyExistsError(AgentTaskGraphError):
    pass


class TaskGraphValidationError(AgentTaskGraphError):
    pass


class TaskTransitionError(AgentTaskGraphError):
    pass


class TaskOutputValidationError(AgentTaskGraphError):
    pass


def _text(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True, order=True)
class TaskBlockReason:
    code: str
    subject: str
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "subject": self.subject, "detail": self.detail}


@dataclass(frozen=True)
class AgentTaskRecord:
    task: AgentTask
    status: str
    attempt_count: int = 0
    output_artifact_refs: tuple[str, ...] = ()
    blocked_reasons: tuple[TaskBlockReason, ...] = ()
    last_error: str = ""

    def __post_init__(self) -> None:
        if self.status not in GRAPH_STATUSES:
            raise ValueError(f"unsupported task record status: {self.status}")
        if int(self.attempt_count) < 0 or int(self.attempt_count) > self.task.max_attempts:
            raise ValueError("attempt_count is outside task retry policy")
        refs = tuple(sorted(set(_text(value) for value in self.output_artifact_refs if _text(value))))
        for ref in refs:
            ArtifactRef.parse(ref)
        normalized_task = (
            self.task
            if self.task.status == self.status
            else replace(self.task, status=self.status)
        )
        object.__setattr__(self, "task", normalized_task)
        object.__setattr__(self, "attempt_count", int(self.attempt_count))
        object.__setattr__(self, "output_artifact_refs", refs)
        object.__setattr__(
            self,
            "blocked_reasons",
            tuple(sorted(set(self.blocked_reasons))),
        )
        object.__setattr__(self, "last_error", _text(self.last_error))

    def as_dict(self) -> dict[str, object]:
        return {
            "task": asdict(self.task),
            "status": self.status,
            "attempt_count": self.attempt_count,
            "output_artifact_refs": list(self.output_artifact_refs),
            "blocked_reasons": [reason.as_dict() for reason in self.blocked_reasons],
            "last_error": self.last_error,
        }


@dataclass(frozen=True)
class AgentTaskGraph:
    graph_id: str
    project_id: str
    version: int
    status: str
    tasks: Mapping[str, AgentTaskRecord]

    def __post_init__(self) -> None:
        if not _text(self.graph_id) or not _text(self.project_id):
            raise ValueError("graph_id and project_id are required")
        if int(self.version) <= 0:
            raise ValueError("graph version must be positive")
        if self.status not in GRAPH_STATUSES:
            raise ValueError(f"unsupported graph status: {self.status}")
        normalized = dict(self.tasks)
        if not normalized or any(task_id != record.task.task_id for task_id, record in normalized.items()):
            raise ValueError("graph tasks must be non-empty and keyed by task_id")
        object.__setattr__(self, "version", int(self.version))
        object.__setattr__(self, "tasks", MappingProxyType(dict(sorted(normalized.items()))))

    def task(self, task_id: str) -> AgentTaskRecord:
        normalized = _text(task_id)
        try:
            return self.tasks[normalized]
        except KeyError as exc:
            raise TaskTransitionError(f"unknown task: {normalized}") from exc

    def as_dict(self) -> dict[str, object]:
        return {
            "graph_id": self.graph_id,
            "project_id": self.project_id,
            "version": self.version,
            "status": self.status,
            "tasks": {
                task_id: record.as_dict()
                for task_id, record in self.tasks.items()
            },
        }


@dataclass(frozen=True)
class TaskGraphTransition:
    transition_id: str
    graph_id: str
    from_version: int
    to_version: int
    action: str
    task_id: str
    affected_tasks: tuple[str, ...]
    source: str

    def as_dict(self) -> dict[str, object]:
        return {
            "transition_id": self.transition_id,
            "graph_id": self.graph_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "action": self.action,
            "task_id": self.task_id,
            "affected_tasks": list(self.affected_tasks),
            "source": self.source,
        }


def _task_fingerprint(tasks: tuple[AgentTask, ...]) -> str:
    canonical = json.dumps(
        [asdict(task) for task in sorted(tasks, key=lambda item: item.task_id)],
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AgentTaskGraphStore:
    """Project-level business task DAG; never executes Runtime tools."""

    def __init__(self, project_states: ProjectStateStore, artifacts: ArtifactRegistry) -> None:
        if not isinstance(project_states, ProjectStateStore):
            raise TypeError("AgentTaskGraphStore requires ProjectStateStore")
        if not isinstance(artifacts, ArtifactRegistry):
            raise TypeError("AgentTaskGraphStore requires ArtifactRegistry")
        self._project_states = project_states
        self._artifacts = artifacts
        self._graphs: dict[str, AgentTaskGraph] = {}
        self._histories: dict[str, list[TaskGraphTransition]] = {}
        self._fingerprints: dict[str, str] = {}
        self._lock = RLock()

    def create_graph(
        self,
        *,
        graph_id: str,
        project_id: str,
        tasks: Iterable[AgentTask],
        expected_project_version: int,
        patch_id: str,
        source: str,
    ) -> AgentTaskGraph:
        normalized_graph_id = _text(graph_id)
        normalized_project_id = _text(project_id)
        normalized_source = _text(source)
        normalized_patch_id = _text(patch_id)
        items = tuple(tasks)
        if not normalized_graph_id or not normalized_project_id or not normalized_source or not normalized_patch_id:
            raise ValueError("graph_id, project_id, source, and patch_id are required")
        if not items or any(not isinstance(task, AgentTask) for task in items):
            raise TypeError("tasks must be a non-empty iterable of AgentTask")
        fingerprint = _task_fingerprint(items)

        with self._lock:
            existing = self._graphs.get(normalized_graph_id)
            if existing is not None:
                if (
                    existing.project_id == normalized_project_id
                    and self._fingerprints[normalized_graph_id] == fingerprint
                ):
                    return existing
                raise TaskGraphAlreadyExistsError(normalized_graph_id)

            self._validate_graph_definition(items)
            project = self._project_states.get(normalized_project_id)
            if project.project_version != int(expected_project_version):
                raise TaskGraphValidationError(
                    f"{normalized_project_id}: expected project version {expected_project_version}, "
                    f"current {project.project_version}"
                )
            if project.active_task_graph_id and project.active_task_graph_id != normalized_graph_id:
                active = self._graphs.get(project.active_task_graph_id)
                if active is None or active.status != "completed":
                    raise TaskGraphValidationError(
                        f"project already has active non-terminal graph {project.active_task_graph_id}"
                    )

            records = {
                task.task_id: AgentTaskRecord(task=task, status="pending")
                for task in items
            }
            records = self._recompute_records(normalized_project_id, records)
            graph = AgentTaskGraph(
                graph_id=normalized_graph_id,
                project_id=normalized_project_id,
                version=1,
                status=self._graph_status(records),
                tasks=records,
            )
            self._project_states.apply_patch(
                ProjectStatePatch(
                    patch_id=normalized_patch_id,
                    project_id=normalized_project_id,
                    expected_project_version=int(expected_project_version),
                    source=normalized_source,
                    changes={"active_task_graph_id": normalized_graph_id},
                )
            )
            self._graphs[normalized_graph_id] = graph
            self._fingerprints[normalized_graph_id] = fingerprint
            self._histories[normalized_graph_id] = [
                TaskGraphTransition(
                    transition_id=f"transition-create-{normalized_graph_id}",
                    graph_id=normalized_graph_id,
                    from_version=0,
                    to_version=1,
                    action="graph_created",
                    task_id="",
                    affected_tasks=tuple(sorted(records)),
                    source=normalized_source,
                )
            ]
            return graph

    def get(self, graph_id: str) -> AgentTaskGraph:
        normalized = _text(graph_id)
        with self._lock:
            graph = self._graphs.get(normalized)
            if graph is None:
                raise TaskGraphNotFoundError(normalized)
            return graph

    def history(self, graph_id: str) -> tuple[TaskGraphTransition, ...]:
        normalized = _text(graph_id)
        with self._lock:
            if normalized not in self._graphs:
                raise TaskGraphNotFoundError(normalized)
            return tuple(self._histories.get(normalized, ()))

    def start_task(self, graph_id: str, task_id: str, *, source: str) -> AgentTaskGraph:
        def mutate(record: AgentTaskRecord, records: dict[str, AgentTaskRecord]) -> AgentTaskRecord:
            resolved = self._resolve_record_status(self.get(graph_id).project_id, record, records)
            if resolved.status != "ready":
                raise TaskTransitionError(f"{task_id}: expected ready, got {resolved.status}")
            return replace(
                resolved,
                status="in_progress",
                attempt_count=resolved.attempt_count + 1,
                blocked_reasons=(),
                last_error="",
            )

        return self._mutate_task(graph_id, task_id, action="task_started", source=source, mutate=mutate)

    def fail_task(self, graph_id: str, task_id: str, *, error: str, source: str) -> AgentTaskGraph:
        normalized_error = _text(error)
        if not normalized_error:
            raise ValueError("error is required")

        def mutate(record: AgentTaskRecord, _records: dict[str, AgentTaskRecord]) -> AgentTaskRecord:
            if record.status != "in_progress":
                raise TaskTransitionError(f"{task_id}: expected in_progress, got {record.status}")
            return replace(record, status="failed", last_error=normalized_error)

        return self._mutate_task(graph_id, task_id, action="task_failed", source=source, mutate=mutate)

    def retry_task(self, graph_id: str, task_id: str, *, source: str) -> AgentTaskGraph:
        def mutate(record: AgentTaskRecord, records: dict[str, AgentTaskRecord]) -> AgentTaskRecord:
            if record.status != "failed":
                raise TaskTransitionError(f"{task_id}: expected failed, got {record.status}")
            if record.attempt_count >= record.task.max_attempts:
                raise TaskTransitionError(f"{task_id}: retry budget exhausted")
            candidate = replace(record, status="pending", blocked_reasons=())
            return self._resolve_record_status(self.get(graph_id).project_id, candidate, records)

        return self._mutate_task(graph_id, task_id, action="task_retried", source=source, mutate=mutate)

    def complete_task(
        self,
        graph_id: str,
        task_id: str,
        *,
        output_artifact_refs: Iterable[str],
        source: str,
    ) -> AgentTaskGraph:
        outputs = tuple(sorted(set(_text(value) for value in output_artifact_refs if _text(value))))
        if not outputs:
            raise TaskOutputValidationError("output_artifact_refs cannot be empty")

        def mutate(record: AgentTaskRecord, records: dict[str, AgentTaskRecord]) -> AgentTaskRecord:
            if record.status != "in_progress":
                raise TaskTransitionError(f"{task_id}: expected in_progress, got {record.status}")
            resolved = self._resolve_record_status(self.get(graph_id).project_id, record, records)
            if resolved.status != "in_progress":
                raise TaskTransitionError(f"{task_id}: inputs changed while task was running")
            produced_types: set[str] = set()
            for value in outputs:
                ref = ArtifactRef.parse(value)
                try:
                    artifact_record = self._artifacts.get(self.get(graph_id).project_id, ref)
                except ArtifactNotFoundError as exc:
                    raise TaskOutputValidationError(f"{task_id}: missing output {ref}") from exc
                if not self._artifacts.is_usable(self.get(graph_id).project_id, ref):
                    raise TaskOutputValidationError(f"{task_id}: output {ref} is not usable")
                artifact = artifact_record.artifact
                if artifact.source_task_id != task_id:
                    raise TaskOutputValidationError(
                        f"{task_id}: output {ref} belongs to task {artifact.source_task_id}"
                    )
                if artifact.artifact_type not in record.task.output_types:
                    raise TaskOutputValidationError(
                        f"{task_id}: output {ref} has undeclared type {artifact.artifact_type}"
                    )
                produced_types.add(artifact.artifact_type)
            missing_types = set(record.task.output_types) - produced_types
            if missing_types:
                raise TaskOutputValidationError(
                    f"{task_id}: missing declared output types {sorted(missing_types)}"
                )
            return replace(
                record,
                status="completed",
                output_artifact_refs=outputs,
                blocked_reasons=(),
                last_error="",
            )

        return self._mutate_task(graph_id, task_id, action="task_completed", source=source, mutate=mutate)

    def rebind_inputs(
        self,
        graph_id: str,
        task_id: str,
        *,
        input_artifact_refs: Iterable[str],
        source: str,
    ) -> AgentTaskGraph:
        inputs = tuple(sorted(set(_text(value) for value in input_artifact_refs if _text(value))))
        for value in inputs:
            ArtifactRef.parse(value)

        def mutate(record: AgentTaskRecord, records: dict[str, AgentTaskRecord]) -> AgentTaskRecord:
            if record.status == "in_progress":
                raise TaskTransitionError(f"{task_id}: cannot rebind an in-progress task")
            revised_task = replace(record.task, input_artifact_refs=inputs, status="pending")
            candidate = AgentTaskRecord(
                task=revised_task,
                status="pending",
                attempt_count=0,
            )
            return self._resolve_record_status(self.get(graph_id).project_id, candidate, records)

        return self._mutate_task(graph_id, task_id, action="task_inputs_rebound", source=source, mutate=mutate)

    def refresh(self, graph_id: str, *, source: str) -> AgentTaskGraph:
        normalized_source = _text(source)
        if not normalized_source:
            raise ValueError("source is required")
        with self._lock:
            graph = self.get(graph_id)
            records = self._recompute_records(graph.project_id, dict(graph.tasks))
            if records == dict(graph.tasks):
                return graph
            return self._commit_graph_change(
                graph,
                records,
                action="graph_refreshed",
                task_id="",
                source=normalized_source,
            )

    def _mutate_task(self, graph_id, task_id, *, action, source, mutate) -> AgentTaskGraph:
        normalized_source = _text(source)
        normalized_task_id = _text(task_id)
        if not normalized_source or not normalized_task_id:
            raise ValueError("source and task_id are required")
        with self._lock:
            graph = self.get(graph_id)
            records = dict(graph.tasks)
            record = graph.task(normalized_task_id)
            records[normalized_task_id] = mutate(record, records)
            records = self._recompute_records(graph.project_id, records)
            return self._commit_graph_change(
                graph,
                records,
                action=action,
                task_id=normalized_task_id,
                source=normalized_source,
            )

    def _commit_graph_change(
        self,
        graph: AgentTaskGraph,
        records: dict[str, AgentTaskRecord],
        *,
        action: str,
        task_id: str,
        source: str,
    ) -> AgentTaskGraph:
        affected = tuple(
            sorted(
                candidate_id
                for candidate_id, record in records.items()
                if graph.tasks.get(candidate_id) != record
            )
        )
        if not affected:
            return graph
        next_graph = AgentTaskGraph(
            graph_id=graph.graph_id,
            project_id=graph.project_id,
            version=graph.version + 1,
            status=self._graph_status(records),
            tasks=records,
        )
        transition = TaskGraphTransition(
            transition_id=f"transition-{graph.graph_id}-{next_graph.version}",
            graph_id=graph.graph_id,
            from_version=graph.version,
            to_version=next_graph.version,
            action=action,
            task_id=task_id,
            affected_tasks=affected,
            source=source,
        )
        self._graphs[graph.graph_id] = next_graph
        self._histories.setdefault(graph.graph_id, []).append(transition)
        return next_graph

    def _recompute_records(
        self,
        project_id: str,
        records: dict[str, AgentTaskRecord],
    ) -> dict[str, AgentTaskRecord]:
        result = dict(records)
        for _ in range(len(result) + 1):
            changed = False
            for task_id in sorted(result):
                record = result[task_id]
                resolved = self._resolve_record_status(project_id, record, result)
                if resolved != record:
                    result[task_id] = resolved
                    changed = True
            if not changed:
                return result
        raise TaskGraphValidationError("task status resolution did not converge")

    def _resolve_record_status(
        self,
        project_id: str,
        record: AgentTaskRecord,
        records: Mapping[str, AgentTaskRecord],
    ) -> AgentTaskRecord:
        if record.status == "failed":
            return record
        dependency_records = [records[dependency] for dependency in record.task.depends_on]
        blocking_dependencies = [
            dependency
            for dependency in dependency_records
            if dependency.status in {"blocked", "failed"}
        ]
        if blocking_dependencies:
            reasons = tuple(
                TaskBlockReason("dependency_not_successful", dependency.task.task_id, dependency.status)
                for dependency in blocking_dependencies
            )
            return replace(record, status="blocked", blocked_reasons=reasons)
        if any(dependency.status != "completed" for dependency in dependency_records):
            if record.status in {"completed", "in_progress"}:
                return replace(
                    record,
                    status="blocked",
                    blocked_reasons=(TaskBlockReason("dependency_regressed", record.task.task_id),),
                )
            return replace(record, status="pending", blocked_reasons=())

        input_reasons: list[TaskBlockReason] = []
        for value in record.task.input_artifact_refs:
            try:
                artifact_record = self._artifacts.get(project_id, value)
            except ArtifactNotFoundError:
                input_reasons.append(TaskBlockReason("input_artifact_missing", value))
                continue
            if not self._artifacts.is_usable(project_id, value):
                input_reasons.append(
                    TaskBlockReason(
                        "input_artifact_not_usable",
                        value,
                        artifact_record.registry_status,
                    )
                )
        if input_reasons:
            return replace(record, status="blocked", blocked_reasons=tuple(input_reasons))

        if record.status in {"completed", "in_progress"}:
            return replace(record, blocked_reasons=())
        return replace(record, status="ready", blocked_reasons=())

    @staticmethod
    def _graph_status(records: Mapping[str, AgentTaskRecord]) -> str:
        statuses = {record.status for record in records.values()}
        if statuses == {"completed"}:
            return "completed"
        if "in_progress" in statuses:
            return "in_progress"
        if "failed" in statuses:
            return "failed"
        if "ready" in statuses:
            return "ready"
        if "blocked" in statuses:
            return "blocked"
        return "pending"

    @staticmethod
    def _validate_graph_definition(tasks: tuple[AgentTask, ...]) -> None:
        task_ids = [task.task_id for task in tasks]
        if len(set(task_ids)) != len(task_ids):
            raise TaskGraphValidationError("task IDs must be unique")
        known = set(task_ids)
        for task in tasks:
            if task.status != "pending":
                raise TaskGraphValidationError(f"{task.task_id}: initial status must be pending")
            for artifact_ref in task.input_artifact_refs:
                try:
                    ArtifactRef.parse(artifact_ref)
                except ValueError as exc:
                    raise TaskGraphValidationError(
                        f"{task.task_id}: invalid input Artifact ref {artifact_ref!r}"
                    ) from exc
            if task.task_id in task.depends_on:
                raise TaskGraphValidationError(f"{task.task_id}: task cannot depend on itself")
            missing = set(task.depends_on) - known
            if missing:
                raise TaskGraphValidationError(
                    f"{task.task_id}: missing dependency tasks {sorted(missing)}"
                )

        indegree = {task.task_id: len(task.depends_on) for task in tasks}
        dependents: dict[str, list[str]] = {task_id: [] for task_id in task_ids}
        for task in tasks:
            for dependency in task.depends_on:
                dependents[dependency].append(task.task_id)
        ready = sorted(task_id for task_id, count in indegree.items() if count == 0)
        visited: list[str] = []
        while ready:
            task_id = ready.pop(0)
            visited.append(task_id)
            for dependent in sorted(dependents[task_id]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)
                    ready.sort()
        if len(visited) != len(tasks):
            raise TaskGraphValidationError("task dependency graph contains a cycle")
