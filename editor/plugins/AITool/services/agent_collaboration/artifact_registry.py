from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from threading import RLock
from typing import Iterable

from .contracts import ArtifactEnvelope, GameProjectState
from .project_state import ProjectStatePatch, ProjectStateStore


REGISTRY_STATUSES = frozenset({"current", "stale", "superseded"})


class ArtifactRegistryError(RuntimeError):
    pass


class ArtifactNotFoundError(ArtifactRegistryError):
    pass


class ArtifactVersionConflictError(ArtifactRegistryError):
    pass


class ArtifactRegistrationConflictError(ArtifactRegistryError):
    pass


class ArtifactDependencyError(ArtifactRegistryError):
    pass


class ArtifactNotUsableError(ArtifactRegistryError):
    pass


class InvalidArtifactError(ArtifactRegistryError):
    pass


def _text(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True, order=True)
class ArtifactRef:
    artifact_id: str
    version: int

    def __post_init__(self) -> None:
        normalized_id = _text(self.artifact_id)
        if not normalized_id or "@" in normalized_id:
            raise ValueError("artifact_id must be non-empty and cannot contain '@'")
        if int(self.version) <= 0:
            raise ValueError("artifact version must be positive")
        object.__setattr__(self, "artifact_id", normalized_id)
        object.__setattr__(self, "version", int(self.version))

    def __str__(self) -> str:
        return f"{self.artifact_id}@{self.version}"

    @classmethod
    def parse(cls, value: str | ArtifactRef) -> ArtifactRef:
        if isinstance(value, cls):
            return value
        text = _text(value)
        artifact_id, separator, raw_version = text.rpartition("@")
        if not separator:
            raise ValueError(f"artifact reference must include an explicit version: {text!r}")
        try:
            version = int(raw_version)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid artifact reference version: {text!r}") from exc
        return cls(artifact_id=artifact_id, version=version)


@dataclass(frozen=True)
class StaleReason:
    code: str
    dependency_ref: ArtifactRef
    replacement_ref: ArtifactRef | None = None

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "dependency_ref": str(self.dependency_ref),
            "replacement_ref": str(self.replacement_ref) if self.replacement_ref else "",
        }


@dataclass(frozen=True)
class ArtifactRecord:
    project_id: str
    ref: ArtifactRef
    artifact: ArtifactEnvelope
    registry_status: str = "current"
    stale_reasons: tuple[StaleReason, ...] = ()
    superseded_by: ArtifactRef | None = None

    def __post_init__(self) -> None:
        if not _text(self.project_id):
            raise ValueError("project_id is required")
        if self.registry_status not in REGISTRY_STATUSES:
            raise ValueError(f"unsupported registry_status: {self.registry_status}")
        if self.ref.artifact_id != self.artifact.artifact_id or self.ref.version != self.artifact.version:
            raise ValueError("record ref must match ArtifactEnvelope identity")

    @property
    def usable(self) -> bool:
        return (
            self.registry_status == "current"
            and self.artifact.status == "validated"
            and self.artifact.validation_result.valid
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "artifact_ref": str(self.ref),
            "registry_status": self.registry_status,
            "stale_reasons": [reason.as_dict() for reason in self.stale_reasons],
            "superseded_by": str(self.superseded_by) if self.superseded_by else "",
            "usable": self.usable,
            "artifact": self.artifact.as_dict(),
        }


def _artifact_fingerprint(artifact: ArtifactEnvelope) -> str:
    canonical = json.dumps(
        artifact.as_dict(),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ArtifactRegistry:
    """Versioned Artifact facts, isolated from RuntimeState and Engine state."""

    def __init__(self, project_states: ProjectStateStore) -> None:
        if not isinstance(project_states, ProjectStateStore):
            raise TypeError("ArtifactRegistry requires a ProjectStateStore")
        self._project_states = project_states
        self._records: dict[tuple[str, ArtifactRef], ArtifactRecord] = {}
        self._current: dict[tuple[str, str], ArtifactRef] = {}
        self._reverse_dependencies: dict[tuple[str, ArtifactRef], set[ArtifactRef]] = {}
        self._fingerprints: dict[tuple[str, ArtifactRef], str] = {}
        self._lock = RLock()

    def get(self, project_id: str, ref: str | ArtifactRef) -> ArtifactRecord:
        project = _text(project_id)
        parsed = ArtifactRef.parse(ref)
        with self._lock:
            record = self._records.get((project, parsed))
            if record is None:
                raise ArtifactNotFoundError(f"{project}:{parsed}")
            return record

    def current(
        self,
        project_id: str,
        artifact_id: str,
        *,
        require_usable: bool = True,
    ) -> ArtifactRecord:
        project = _text(project_id)
        normalized_id = _text(artifact_id)
        with self._lock:
            ref = self._current.get((project, normalized_id))
            if ref is None:
                raise ArtifactNotFoundError(f"{project}:{normalized_id}")
            record = self._records[(project, ref)]
            if require_usable and not record.usable:
                raise ArtifactNotUsableError(
                    f"{project}:{ref} is {record.registry_status}/{record.artifact.status}"
                )
            return record

    def list_versions(self, project_id: str, artifact_id: str) -> tuple[ArtifactRecord, ...]:
        project = _text(project_id)
        normalized_id = _text(artifact_id)
        with self._lock:
            records = [
                record
                for (record_project, ref), record in self._records.items()
                if record_project == project and ref.artifact_id == normalized_id
            ]
            return tuple(sorted(records, key=lambda record: record.ref.version))

    def list_current(
        self,
        project_id: str,
        *,
        include_stale: bool = True,
    ) -> tuple[ArtifactRecord, ...]:
        project = _text(project_id)
        with self._lock:
            records = [
                self._records[(project, ref)]
                for (record_project, _artifact_id), ref in self._current.items()
                if record_project == project
            ]
            if not include_stale:
                records = [record for record in records if record.usable]
            return tuple(sorted(records, key=lambda record: (record.ref.artifact_id, record.ref.version)))

    def dependents(self, project_id: str, ref: str | ArtifactRef) -> tuple[ArtifactRef, ...]:
        project = _text(project_id)
        parsed = ArtifactRef.parse(ref)
        with self._lock:
            return tuple(sorted(self._reverse_dependencies.get((project, parsed), set())))

    def register(
        self,
        *,
        project_id: str,
        artifact: ArtifactEnvelope,
        expected_project_version: int,
        patch_id: str,
        source: str,
    ) -> ArtifactRecord:
        return self.register_many(
            project_id=project_id,
            artifacts=(artifact,),
            expected_project_version=expected_project_version,
            patch_id=patch_id,
            source=source,
        )[0]

    def register_many(
        self,
        *,
        project_id: str,
        artifacts: Iterable[ArtifactEnvelope],
        expected_project_version: int,
        patch_id: str,
        source: str,
    ) -> tuple[ArtifactRecord, ...]:
        project = _text(project_id)
        normalized_patch_id = _text(patch_id)
        normalized_source = _text(source)
        items = tuple(artifacts)
        if not project or not normalized_patch_id or not normalized_source:
            raise ValueError("project_id, patch_id, and source are required")
        if not items:
            raise ValueError("artifacts must not be empty")
        if any(not isinstance(item, ArtifactEnvelope) for item in items):
            raise TypeError("artifacts must contain only ArtifactEnvelope values")

        with self._lock:
            project_state = self._project_states.get(project)
            input_refs = tuple(ArtifactRef(item.artifact_id, item.version) for item in items)
            if len(set(input_refs)) != len(input_refs):
                raise ArtifactRegistrationConflictError("registration batch contains duplicate Artifact refs")

            existing = [self._records.get((project, ref)) for ref in input_refs]
            if any(record is not None for record in existing):
                if not all(record is not None for record in existing):
                    raise ArtifactRegistrationConflictError("partial registration replay is not allowed")
                for artifact, ref, record in zip(items, input_refs, existing):
                    assert record is not None
                    if self._fingerprints[(project, ref)] != _artifact_fingerprint(artifact):
                        raise ArtifactRegistrationConflictError(f"{project}:{ref} content changed")
                return tuple(record for record in existing if record is not None)

            if project_state.project_version != int(expected_project_version):
                raise ArtifactVersionConflictError(
                    f"{project}: expected project version {expected_project_version}, "
                    f"current {project_state.project_version}"
                )

            self._validate_new_artifacts(
                project=project,
                project_state=project_state,
                artifacts=items,
                refs=input_refs,
            )
            ordered = self._topological_registration_order(project, items, input_refs)

            records = dict(self._records)
            current = dict(self._current)
            reverse = {key: set(value) for key, value in self._reverse_dependencies.items()}
            fingerprints = dict(self._fingerprints)

            for artifact, ref in ordered:
                old_ref = current.get((project, ref.artifact_id))
                if old_ref is not None:
                    old_record = records[(project, old_ref)]
                    records[(project, old_ref)] = replace(
                        old_record,
                        registry_status="superseded",
                        superseded_by=ref,
                    )
                    self._propagate_stale(
                        project=project,
                        dependency_ref=old_ref,
                        replacement_ref=ref,
                        records=records,
                        current=current,
                        reverse=reverse,
                    )

                record = ArtifactRecord(
                    project_id=project,
                    ref=ref,
                    artifact=artifact,
                )
                records[(project, ref)] = record
                fingerprints[(project, ref)] = _artifact_fingerprint(artifact)
                current[(project, ref.artifact_id)] = ref
                for dependency in artifact.dependencies:
                    dependency_ref = ArtifactRef.parse(dependency)
                    reverse.setdefault((project, dependency_ref), set()).add(ref)

            project_refs = tuple(
                sorted(
                    str(ref)
                    for (record_project, _artifact_id), ref in current.items()
                    if record_project == project
                )
            )
            current_records = [records[(project, ArtifactRef.parse(ref))] for ref in project_refs]
            validation_status = (
                "stale"
                if any(record.registry_status == "stale" for record in current_records)
                else "pending"
            )
            updated_project = self._project_states.apply_patch(
                ProjectStatePatch(
                    patch_id=normalized_patch_id,
                    project_id=project,
                    expected_project_version=int(expected_project_version),
                    source=normalized_source,
                    changes={
                        "artifact_refs": project_refs,
                        "validation_status": validation_status,
                    },
                )
            )
            if not isinstance(updated_project, GameProjectState):
                raise RuntimeError("ProjectStateStore returned an invalid state")

            self._records = records
            self._current = current
            self._reverse_dependencies = reverse
            self._fingerprints = fingerprints
            return tuple(self._records[(project, ref)] for ref in input_refs)

    def _validate_new_artifacts(
        self,
        *,
        project: str,
        project_state: GameProjectState,
        artifacts: tuple[ArtifactEnvelope, ...],
        refs: tuple[ArtifactRef, ...],
    ) -> None:
        planned = set(refs)
        planned_ids: set[str] = set()
        for artifact, ref in zip(artifacts, refs):
            if artifact.artifact_id in planned_ids:
                raise ArtifactRegistrationConflictError(
                    "one registration batch cannot publish multiple versions of the same Artifact"
                )
            planned_ids.add(artifact.artifact_id)
            if not artifact.validation_result.valid or artifact.status == "invalid":
                raise InvalidArtifactError(f"{ref}: validation failed")
            if artifact.status not in {"draft", "validated"}:
                raise InvalidArtifactError(f"{ref}: cannot register status {artifact.status}")
            if artifact.base_project_version != project_state.project_version:
                raise ArtifactVersionConflictError(
                    f"{ref}: base_project_version {artifact.base_project_version} does not match "
                    f"project version {project_state.project_version}"
                )

            old_ref = self._current.get((project, ref.artifact_id))
            if old_ref is None:
                if ref.version != 1:
                    raise ArtifactVersionConflictError(f"{ref}: first version must be 1")
            else:
                old_record = self._records[(project, old_ref)]
                if ref.version != old_ref.version + 1:
                    raise ArtifactVersionConflictError(
                        f"{ref}: expected next version {old_ref.version + 1}"
                    )
                if artifact.artifact_type != old_record.artifact.artifact_type:
                    raise ArtifactRegistrationConflictError(f"{ref}: artifact_type changed")
                if artifact.producer_role != old_record.artifact.producer_role:
                    raise ArtifactRegistrationConflictError(f"{ref}: producer_role changed")

            for dependency in artifact.dependencies:
                dependency_ref = ArtifactRef.parse(dependency)
                if dependency_ref in planned:
                    continue
                dependency_record = self._records.get((project, dependency_ref))
                if dependency_record is None:
                    raise ArtifactDependencyError(f"{ref}: missing dependency {dependency_ref}")
                if self._current.get((project, dependency_ref.artifact_id)) != dependency_ref:
                    raise ArtifactDependencyError(f"{ref}: dependency {dependency_ref} is not current")
                if not dependency_record.usable:
                    raise ArtifactDependencyError(f"{ref}: dependency {dependency_ref} is not usable")

    def _topological_registration_order(
        self,
        project: str,
        artifacts: tuple[ArtifactEnvelope, ...],
        refs: tuple[ArtifactRef, ...],
    ) -> tuple[tuple[ArtifactEnvelope, ArtifactRef], ...]:
        pending = {ref: artifact for artifact, ref in zip(artifacts, refs)}
        ordered: list[tuple[ArtifactEnvelope, ArtifactRef]] = []
        available = {
            ref
            for (record_project, _artifact_id), ref in self._current.items()
            if record_project == project and self._records[(project, ref)].usable
        }
        while pending:
            progressed = False
            for ref in sorted(pending):
                artifact = pending[ref]
                dependencies = {ArtifactRef.parse(value) for value in artifact.dependencies}
                if dependencies.issubset(available):
                    ordered.append((artifact, ref))
                    if artifact.status == "validated" and artifact.validation_result.valid:
                        available.add(ref)
                    del pending[ref]
                    progressed = True
                    break
            if not progressed:
                unresolved = ", ".join(str(ref) for ref in sorted(pending))
                raise ArtifactDependencyError(f"cyclic or unresolved batch dependencies: {unresolved}")
        return tuple(ordered)

    @staticmethod
    def _propagate_stale(
        *,
        project: str,
        dependency_ref: ArtifactRef,
        replacement_ref: ArtifactRef,
        records: dict[tuple[str, ArtifactRef], ArtifactRecord],
        current: dict[tuple[str, str], ArtifactRef],
        reverse: dict[tuple[str, ArtifactRef], set[ArtifactRef]],
    ) -> None:
        queue: list[tuple[ArtifactRef, ArtifactRef, str, ArtifactRef | None]] = [
            (dependent, dependency_ref, "dependency_superseded", replacement_ref)
            for dependent in sorted(reverse.get((project, dependency_ref), set()))
        ]
        visited: set[tuple[ArtifactRef, ArtifactRef]] = set()
        while queue:
            dependent_ref, cause_ref, code, reason_replacement = queue.pop(0)
            edge = (dependent_ref, cause_ref)
            if edge in visited:
                continue
            visited.add(edge)
            record = records.get((project, dependent_ref))
            if record is None:
                continue
            if current.get((project, dependent_ref.artifact_id)) != dependent_ref:
                continue
            reason = StaleReason(
                code=code,
                dependency_ref=cause_ref,
                replacement_ref=reason_replacement,
            )
            reasons = tuple(
                sorted(
                    set(record.stale_reasons + (reason,)),
                    key=lambda item: (item.code, str(item.dependency_ref), str(item.replacement_ref or "")),
                )
            )
            records[(project, dependent_ref)] = replace(
                record,
                registry_status="stale",
                stale_reasons=reasons,
            )
            for child in sorted(reverse.get((project, dependent_ref), set())):
                queue.append((child, dependent_ref, "dependency_stale", None))
