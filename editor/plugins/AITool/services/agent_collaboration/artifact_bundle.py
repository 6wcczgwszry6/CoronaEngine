from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from typing import Mapping

from .artifact_registry import (
    ArtifactNotFoundError,
    ArtifactNotUsableError,
    ArtifactRegistry,
)
from .contracts import ARTIFACT_LINEAGE_IDS, RED_PROJECT_ARTIFACT_TYPES
from .project_state import ProjectStateStore
from .task_graph import AgentTaskGraphStore


RED_PROJECT_ARTIFACT_PRODUCERS = MappingProxyType(
    {
        "GameDesignBrief": "planning",
        "LevelPlan": "planning",
        "ArtDirection": "art",
        "SceneCompositionPlan": "art",
        "GameplayLogicPlan": "program",
    }
)


class ProjectArtifactBundleError(RuntimeError):
    pass


class ProjectArtifactBundleIncompleteError(ProjectArtifactBundleError):
    pass


class ProjectArtifactBundleValidationError(ProjectArtifactBundleError):
    pass


def _text(value: object) -> str:
    return str(value or "").strip()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


@dataclass(frozen=True)
class ProjectArtifactBundleEntry:
    artifact_ref: str
    artifact_type: str
    producer_role: str
    source_task_id: str
    content_hash: str
    dependencies: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact_ref": self.artifact_ref,
            "artifact_type": self.artifact_type,
            "producer_role": self.producer_role,
            "source_task_id": self.source_task_id,
            "content_hash": self.content_hash,
            "dependencies": list(self.dependencies),
        }


@dataclass(frozen=True)
class ProjectArtifactBundle:
    project_id: str
    project_version: int
    graph_id: str
    artifact_refs: tuple[str, ...]
    entries: Mapping[str, ProjectArtifactBundleEntry]
    content_hash: str

    def __post_init__(self) -> None:
        if not _text(self.project_id) or not _text(self.graph_id):
            raise ValueError("project_id and graph_id are required")
        if int(self.project_version) <= 0:
            raise ValueError("project_version must be positive")
        if set(self.entries) != RED_PROJECT_ARTIFACT_TYPES:
            raise ValueError("entries must contain the five Red-stage Artifact types")
        if tuple(sorted(self.artifact_refs)) != self.artifact_refs:
            raise ValueError("artifact_refs must be sorted")
        if set(self.artifact_refs) != {
            entry.artifact_ref for entry in self.entries.values()
        }:
            raise ValueError("artifact_refs must match bundle entries")
        if not _text(self.content_hash).startswith("sha256:"):
            raise ValueError("content_hash must be a sha256 digest")
        object.__setattr__(
            self,
            "entries",
            MappingProxyType(dict(sorted(self.entries.items()))),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "project_version": self.project_version,
            "graph_id": self.graph_id,
            "artifact_refs": list(self.artifact_refs),
            "entries": {
                artifact_type: entry.as_dict()
                for artifact_type, entry in self.entries.items()
            },
            "content_hash": self.content_hash,
            "non_executable": True,
        }


class ProjectArtifactBundleReader:
    """Builds a read-only five-Artifact project package from collaboration facts."""

    def __init__(
        self,
        *,
        project_states: ProjectStateStore,
        artifacts: ArtifactRegistry,
        task_graphs: AgentTaskGraphStore,
    ) -> None:
        if not isinstance(project_states, ProjectStateStore):
            raise TypeError("ProjectArtifactBundleReader requires ProjectStateStore")
        if not isinstance(artifacts, ArtifactRegistry):
            raise TypeError("ProjectArtifactBundleReader requires ArtifactRegistry")
        if not isinstance(task_graphs, AgentTaskGraphStore):
            raise TypeError("ProjectArtifactBundleReader requires AgentTaskGraphStore")
        self._project_states = project_states
        self._artifacts = artifacts
        self._task_graphs = task_graphs

    def build(self, *, project_id: str, graph_id: str) -> ProjectArtifactBundle:
        normalized_project_id = _text(project_id)
        normalized_graph_id = _text(graph_id)
        if not normalized_project_id or not normalized_graph_id:
            raise ValueError("project_id and graph_id are required")

        project = self._project_states.get(normalized_project_id)
        graph = self._task_graphs.get(normalized_graph_id)
        if graph.project_id != normalized_project_id:
            raise ProjectArtifactBundleValidationError(
                "task graph belongs to a different project"
            )
        if graph.status != "completed":
            raise ProjectArtifactBundleIncompleteError(
                f"task graph {normalized_graph_id} is {graph.status}, not completed"
            )
        if project.active_task_graph_id != normalized_graph_id:
            raise ProjectArtifactBundleValidationError(
                f"project active graph is {project.active_task_graph_id or '<none>'}"
            )

        output_owners: dict[str, str] = {}
        for task_id, task_record in graph.tasks.items():
            if task_record.status != "completed":
                raise ProjectArtifactBundleIncompleteError(
                    f"task {task_id} is {task_record.status}"
                )
            for artifact_ref in task_record.output_artifact_refs:
                if artifact_ref in output_owners:
                    raise ProjectArtifactBundleValidationError(
                        f"Artifact {artifact_ref} is claimed by multiple tasks"
                    )
                output_owners[artifact_ref] = task_id

        project_refs = set(project.artifact_refs)
        entries: dict[str, ProjectArtifactBundleEntry] = {}
        for artifact_type in sorted(RED_PROJECT_ARTIFACT_TYPES):
            artifact_id = ARTIFACT_LINEAGE_IDS[artifact_type]
            try:
                record = self._artifacts.current(
                    normalized_project_id,
                    artifact_id,
                    require_usable=True,
                )
            except (ArtifactNotFoundError, ArtifactNotUsableError) as exc:
                raise ProjectArtifactBundleIncompleteError(
                    f"missing usable current {artifact_type} Artifact"
                ) from exc
            artifact = record.artifact
            artifact_ref = str(record.ref)
            expected_producer = RED_PROJECT_ARTIFACT_PRODUCERS[artifact_type]
            if artifact.artifact_type != artifact_type:
                raise ProjectArtifactBundleValidationError(
                    f"{artifact_ref}: expected type {artifact_type}, "
                    f"got {artifact.artifact_type}"
                )
            if artifact.producer_role != expected_producer:
                raise ProjectArtifactBundleValidationError(
                    f"{artifact_ref}: expected producer {expected_producer}, "
                    f"got {artifact.producer_role}"
                )
            if artifact.snapshot_source != "none" or not artifact.non_executable:
                raise ProjectArtifactBundleValidationError(
                    f"{artifact_ref}: Red-stage Artifact isolation is invalid"
                )
            if artifact_ref not in project_refs:
                raise ProjectArtifactBundleValidationError(
                    f"{artifact_ref}: missing from ProjectState artifact_refs"
                )
            owner_task_id = output_owners.get(artifact_ref)
            if owner_task_id != artifact.source_task_id:
                raise ProjectArtifactBundleValidationError(
                    f"{artifact_ref}: graph owner {owner_task_id or '<none>'} does not "
                    f"match source task {artifact.source_task_id}"
                )
            entries[artifact_type] = ProjectArtifactBundleEntry(
                artifact_ref=artifact_ref,
                artifact_type=artifact_type,
                producer_role=artifact.producer_role,
                source_task_id=artifact.source_task_id,
                content_hash=artifact.content_hash,
                dependencies=artifact.dependencies,
            )

        artifact_refs = tuple(sorted(entry.artifact_ref for entry in entries.values()))
        package_ref_set = set(artifact_refs)
        for entry in entries.values():
            for dependency in entry.dependencies:
                if dependency not in package_ref_set:
                    raise ProjectArtifactBundleValidationError(
                        f"{entry.artifact_ref}: dependency {dependency} is outside the bundle"
                    )

        graph_outputs = set(output_owners)
        if graph_outputs != package_ref_set:
            missing = sorted(package_ref_set - graph_outputs)
            extra = sorted(graph_outputs - package_ref_set)
            raise ProjectArtifactBundleValidationError(
                f"graph outputs do not match bundle; missing={missing}, extra={extra}"
            )

        hash_payload = {
            "project_id": project.project_id,
            "project_version": project.project_version,
            "graph_id": graph.graph_id,
            "entries": {
                artifact_type: entry.as_dict()
                for artifact_type, entry in sorted(entries.items())
            },
        }
        content_hash = "sha256:" + hashlib.sha256(
            _canonical_json(hash_payload).encode("utf-8")
        ).hexdigest()
        return ProjectArtifactBundle(
            project_id=project.project_id,
            project_version=project.project_version,
            graph_id=graph.graph_id,
            artifact_refs=artifact_refs,
            entries=entries,
            content_hash=content_hash,
        )
