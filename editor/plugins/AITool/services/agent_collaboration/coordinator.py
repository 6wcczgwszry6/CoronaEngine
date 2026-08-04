"""Production-facing coordination of planning, program, and art Artifacts."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from threading import RLock
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal, Mapping

from ..frontend_adapter import ProgressEvent, UserCommand
from ..schema_versions import FRONTEND_INTERACTION_SCHEMA_VERSION
from .walking_skeleton import WalkingSkeletonRunResult

if TYPE_CHECKING:
    from ..collaboration_readonly_entry import CollaborationReadOnlyEntry


@dataclass(frozen=True)
class CollaborationProposal:
    project_id: str
    room_id: str
    proposal_id: str
    proposal_version: int
    proposal_hash: str
    artifact_ref: str
    artifact_refs: tuple[str, ...]
    artifact_payloads: Mapping[str, Mapping[str, object]]
    summary: str
    request_hash: str
    supersedes: tuple[str, ...] = ()
    status: Literal["proposal_ready", "frozen"] = "proposal_ready"

    def __post_init__(self) -> None:
        if not self.proposal_id or self.proposal_version <= 0:
            raise ValueError("proposal identity is required")
        if not self.proposal_hash.startswith("sha256:"):
            raise ValueError("proposal_hash must be a sha256 digest")
        if not self.request_hash.startswith("sha256:"):
            raise ValueError("request_hash must be a sha256 digest")
        if self.artifact_ref != f"legacy-plan:{self.proposal_id}":
            raise ValueError("artifact_ref must preserve the compatibility proposal identity")
        object.__setattr__(self, "artifact_refs", tuple(sorted(self.artifact_refs)))
        object.__setattr__(self, "supersedes", tuple(sorted(set(self.supersedes))))
        object.__setattr__(
            self,
            "artifact_payloads",
            MappingProxyType({key: MappingProxyType(dict(value)) for key, value in self.artifact_payloads.items()}),
        )


@dataclass(frozen=True)
class CollaborationProposalResult:
    proposal: CollaborationProposal
    run_result: WalkingSkeletonRunResult
    progress_events: tuple[ProgressEvent, ...]
    replayed: bool = False
    revision_status: Literal["created", "revised", "unchanged"] = "created"


@dataclass(frozen=True)
class CollaborationStageStatus:
    stage: Literal["planning", "program", "art", "narration"]
    status: Literal["completed", "blocked", "not_started", "in_progress"]
    artifact_refs: tuple[str, ...] = ()
    error_code: str = ""
    field_path: str = ""
    safe_summary: str = ""


@dataclass(frozen=True)
class CollaborationAttemptReport:
    attempt_id: str
    command_id: str
    project_id: str
    room_id: str
    overall_status: Literal["completed", "blocked", "in_progress"]
    stages: tuple[CollaborationStageStatus, ...]
    retryable: bool

    def stage(self, name: str) -> CollaborationStageStatus | None:
        return next((item for item in self.stages if item.stage == name), None)


class CollaborationInProgressError(RuntimeError):
    def __init__(self, attempt_id: str) -> None:
        super().__init__("collaboration proposal generation is already in progress")
        self.stage = "planning"
        self.error_code = "collaboration_in_progress"
        self.field_path = ""
        self.safe_summary = "A collaboration proposal is already being generated for this project."
        self.attempt_id = str(attempt_id or "")


@dataclass(frozen=True)
class _CollaborationInFlight:
    command_id: str
    request_hash: str
    attempt_id: str


class CollaborationCoordinator:
    """Owns proposal versions while all scene execution remains outside this layer."""

    def __init__(self, *, readonly_entry: "CollaborationReadOnlyEntry | None" = None) -> None:
        if readonly_entry is None:
            from ..collaboration_readonly_entry import CollaborationReadOnlyEntry

            readonly_entry = CollaborationReadOnlyEntry()
        self._entry = readonly_entry
        self._by_project: dict[str, CollaborationProposal] = {}
        self._history_by_project: dict[str, tuple[CollaborationProposal, ...]] = {}
        self._by_command: dict[str, CollaborationProposalResult] = {}
        self._latest_result_by_project: dict[str, CollaborationProposalResult] = {}
        self._attempt_by_project: dict[str, CollaborationAttemptReport] = {}
        self._inflight_by_project: dict[str, _CollaborationInFlight] = {}
        self._lock = RLock()

    def create_proposal(
        self,
        command: UserCommand,
        *,
        readonly_entry: "CollaborationReadOnlyEntry | None" = None,
    ) -> CollaborationProposalResult:
        if command.command_type != "start_project":
            raise ValueError("CollaborationCoordinator requires start_project")
        project_id = str(command.payload.get("project_id") or "").strip()
        if not project_id:
            raise ValueError("project_id is required")
        request_hash = self.request_hash(str(command.payload.get("project_goal") or ""))
        with self._lock:
            previous = self._by_command.get(command.command_id)
            if previous is not None:
                return replace(previous, replayed=True, progress_events=())
            current = self._by_project.get(project_id)
            latest_result = self._latest_result_by_project.get(project_id)
            if (
                current is not None
                and latest_result is not None
                and current.request_hash == request_hash
            ):
                unchanged = replace(
                    latest_result,
                    replayed=True,
                    progress_events=(),
                    revision_status="unchanged",
                )
                self._by_command[command.command_id] = unchanged
                return unchanged
            inflight = self._inflight_by_project.get(project_id)
            if inflight is not None:
                raise CollaborationInProgressError(inflight.attempt_id)
            attempt_id = f"attempt.{command.command_id}"
            inflight = _CollaborationInFlight(
                command_id=command.command_id,
                request_hash=request_hash,
                attempt_id=attempt_id,
            )
            self._inflight_by_project[project_id] = inflight
            self._attempt_by_project[project_id] = self._started_attempt(command)

        try:
            entry_result = (readonly_entry or self._entry).run(command)
        except Exception as exc:
            with self._lock:
                active = self._inflight_by_project.get(project_id)
                if active == inflight:
                    self._attempt_by_project[project_id] = self._failed_attempt(command, exc)
                    self._inflight_by_project.pop(project_id, None)
            raise

        with self._lock:
            active = self._inflight_by_project.get(project_id)
            if active != inflight:
                raise RuntimeError("collaboration attempt ownership changed before commit")
            try:
                current = self._by_project.get(project_id)
                if entry_result.run_result is None:
                    blocker = entry_result.blocked_result
                    self._attempt_by_project[project_id] = self._blocked_entry_attempt(
                        command,
                        error_code=str(getattr(blocker, "error_code", "collaboration_blocked")),
                        summary=str(getattr(blocker, "summary", "Collaboration entry was blocked.")),
                    )
                    raise RuntimeError(str(getattr(blocker, "error_code", "collaboration_blocked")))
                run_result = entry_result.run_result
                proposal_id = current.proposal_id if current is not None else self._proposal_id(command.room_id, project_id)
                if current is not None and current.proposal_hash == run_result.bundle.content_hash:
                    unchanged = CollaborationProposalResult(
                        proposal=current,
                        run_result=run_result,
                        progress_events=(),
                        replayed=True,
                        revision_status="unchanged",
                    )
                    self._by_command[command.command_id] = unchanged
                    self._attempt_by_project[project_id] = self._successful_artifact_attempt(command)
                    return unchanged
                version = (current.proposal_version + 1) if current is not None else 1
                proposal = CollaborationProposal(
                    project_id=project_id,
                    room_id=command.room_id,
                    proposal_id=proposal_id,
                    proposal_version=version,
                    proposal_hash=run_result.bundle.content_hash,
                    artifact_ref=f"legacy-plan:{proposal_id}",
                    artifact_refs=self._versioned_artifact_refs(
                        run_result.bundle.artifact_refs,
                        version=version,
                    ),
                    artifact_payloads=run_result.artifact_payloads,
                    summary=self._summary(run_result),
                    request_hash=request_hash,
                    supersedes=(self._execution_ref(current),) if current is not None else (),
                )
                result = CollaborationProposalResult(
                    proposal=proposal,
                    run_result=run_result,
                    progress_events=(),
                    replayed=False,
                    revision_status="revised" if current is not None else "created",
                )
                self._by_project[project_id] = proposal
                self._history_by_project[project_id] = (
                    *self._history_by_project.get(project_id, ()),
                    proposal,
                )
                self._by_command[command.command_id] = result
                self._latest_result_by_project[project_id] = result
                self._attempt_by_project[project_id] = self._successful_artifact_attempt(command)
                return result
            finally:
                self._inflight_by_project.pop(project_id, None)

    def freeze(
        self,
        *,
        project_id: str,
        proposal_id: str,
        proposal_version: int,
        proposal_hash: str,
    ) -> CollaborationProposal:
        with self._lock:
            current = self._by_project.get(project_id)
            if current is None:
                raise ValueError("proposal does not exist")
            if (
                current.proposal_id != proposal_id
                or current.proposal_version != int(proposal_version)
                or current.proposal_hash != proposal_hash
            ):
                raise ValueError("proposal identity is stale")
            frozen = replace(current, status="frozen")
            self._by_project[project_id] = frozen
            return frozen

    def current(self, project_id: str) -> CollaborationProposal | None:
        with self._lock:
            return self._by_project.get(str(project_id or "").strip())

    def history(self, project_id: str) -> tuple[CollaborationProposal, ...]:
        with self._lock:
            return self._history_by_project.get(str(project_id or "").strip(), ())

    def last_attempt(self, project_id: str) -> CollaborationAttemptReport | None:
        with self._lock:
            return self._attempt_by_project.get(str(project_id or "").strip())

    def observe_stage(self, project_id: str, event: object) -> CollaborationAttemptReport | None:
        stage = str(getattr(event, "stage", "") or "").strip()
        status = str(getattr(event, "status", "") or "").strip()
        order = ("planning", "program", "art", "narration")
        if stage not in order or status not in {"completed", "blocked", "not_started", "in_progress"}:
            return None
        project = str(project_id or "").strip()
        with self._lock:
            report = self._attempt_by_project.get(project)
            if report is None:
                return None
            stages = list(report.stages)
            index = order.index(stage)
            stages[index] = CollaborationStageStatus(
                stage=stage,  # type: ignore[arg-type]
                status=status,  # type: ignore[arg-type]
                artifact_refs=tuple(getattr(event, "artifact_refs", ()) or ()),
                error_code=str(getattr(event, "error_code", "") or ""),
                field_path=str(getattr(event, "field_path", "") or ""),
                safe_summary=str(getattr(event, "safe_summary", "") or ""),
            )
            if status == "completed" and stage in {"planning", "program"}:
                next_index = index + 1
                next_stage = stages[next_index]
                if next_stage.status == "not_started":
                    stages[next_index] = replace(next_stage, status="in_progress")
            overall_status = (
                "blocked"
                if status == "blocked" or report.overall_status == "blocked"
                else "in_progress"
            )
            updated = replace(
                report,
                stages=tuple(stages),
                overall_status=overall_status,
                retryable=overall_status == "blocked",
            )
            self._attempt_by_project[project] = updated
            return updated

    def matches_current_request(self, project_id: str, project_goal: str) -> bool:
        with self._lock:
            current = self._by_project.get(str(project_id or "").strip())
            return bool(current is not None and current.request_hash == self.request_hash(project_goal))

    def mark_narration(
        self,
        *,
        project_id: str,
        status: Literal["in_progress", "completed", "blocked"],
        error: Exception | None = None,
    ) -> CollaborationAttemptReport | None:
        with self._lock:
            report = self._attempt_by_project.get(str(project_id or "").strip())
            if report is None:
                return None
            stages = [item for item in report.stages if item.stage != "narration"]
            stages.append(CollaborationStageStatus(
                stage="narration",
                status=status,
                error_code=str(getattr(error, "error_code", "") or ""),
                field_path=str(getattr(error, "field_path", "") or ""),
                safe_summary=str(getattr(error, "safe_summary", "") or ""),
            ))
            updated = replace(
                report,
                overall_status=(
                    "completed"
                    if status == "completed"
                    else "blocked"
                    if status == "blocked"
                    else "in_progress"
                ),
                stages=tuple(stages),
                retryable=status == "blocked",
            )
            self._attempt_by_project[project_id] = updated
            return updated

    def discard_proposal(
        self,
        *,
        project_id: str,
        proposal_id: str,
        proposal_version: int,
        proposal_hash: str,
    ) -> None:
        with self._lock:
            project = str(project_id or "").strip()
            current = self._by_project.get(project)
            if current is None or (
                current.proposal_id != proposal_id
                or current.proposal_version != int(proposal_version)
                or current.proposal_hash != proposal_hash
            ):
                return
            history = tuple(
                item
                for item in self._history_by_project.get(project, ())
                if not (
                    item.proposal_id == proposal_id
                    and item.proposal_version == int(proposal_version)
                    and item.proposal_hash == proposal_hash
                )
            )
            self._history_by_project[project] = history
            if history:
                self._by_project[project] = history[-1]
                prior = next(
                    (
                        result
                        for result in reversed(tuple(self._by_command.values()))
                        if result.proposal == history[-1]
                    ),
                    None,
                )
                if prior is not None:
                    self._latest_result_by_project[project] = prior
            else:
                self._by_project.pop(project, None)
                self._latest_result_by_project.pop(project, None)

    @staticmethod
    def request_hash(project_goal: str) -> str:
        normalized = " ".join(str(project_goal or "").split())
        return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _started_attempt(command: UserCommand) -> CollaborationAttemptReport:
        return CollaborationAttemptReport(
            attempt_id=f"attempt.{command.command_id}",
            command_id=command.command_id,
            project_id=str(command.payload.get("project_id") or ""),
            room_id=command.room_id,
            overall_status="in_progress",
            stages=(
                CollaborationStageStatus("planning", "in_progress"),
                CollaborationStageStatus("program", "not_started"),
                CollaborationStageStatus("art", "not_started"),
                CollaborationStageStatus("narration", "not_started"),
            ),
            retryable=False,
        )

    @staticmethod
    def _successful_artifact_attempt(command: UserCommand) -> CollaborationAttemptReport:
        return CollaborationAttemptReport(
            attempt_id=f"attempt.{command.command_id}",
            command_id=command.command_id,
            project_id=str(command.payload.get("project_id") or ""),
            room_id=command.room_id,
            overall_status="in_progress",
            stages=(
                CollaborationStageStatus("planning", "completed", ("GameDesignBrief", "LevelPlan")),
                CollaborationStageStatus("program", "completed", ("GameplayLogicPlan",)),
                CollaborationStageStatus("art", "completed", ("ArtDirection", "SceneCompositionPlan")),
                CollaborationStageStatus("narration", "not_started"),
            ),
            retryable=False,
        )

    @staticmethod
    def _failed_attempt(command: UserCommand, error: Exception) -> CollaborationAttemptReport:
        stage = str(getattr(error, "stage", "planning") or "planning")
        if stage not in {"planning", "program", "art", "narration"}:
            stage = "planning"
        order = ("planning", "program", "art", "narration")
        failed_index = order.index(stage)
        artifact_refs = {
            "planning": ("GameDesignBrief", "LevelPlan"),
            "program": ("GameplayLogicPlan",),
            "art": ("ArtDirection", "SceneCompositionPlan"),
            "narration": (),
        }
        stages = tuple(
            CollaborationStageStatus(
                stage=item,
                status="completed" if index < failed_index else "blocked" if index == failed_index else "not_started",
                artifact_refs=artifact_refs[item] if index < failed_index else (),
                error_code=str(getattr(error, "error_code", "") or "") if index == failed_index else "",
                field_path=str(getattr(error, "field_path", "") or "") if index == failed_index else "",
                safe_summary=str(
                    getattr(error, "safe_summary", "")
                    or f"{type(error).__name__} blocked the collaboration stage"
                ) if index == failed_index else "",
            )
            for index, item in enumerate(order)
        )
        return CollaborationAttemptReport(
            attempt_id=f"attempt.{command.command_id}",
            command_id=command.command_id,
            project_id=str(command.payload.get("project_id") or ""),
            room_id=command.room_id,
            overall_status="blocked",
            stages=stages,
            retryable=True,
        )

    @staticmethod
    def _blocked_entry_attempt(
        command: UserCommand,
        *,
        error_code: str,
        summary: str,
    ) -> CollaborationAttemptReport:
        error = RuntimeError(summary)
        error.stage = "planning"  # type: ignore[attr-defined]
        error.error_code = error_code  # type: ignore[attr-defined]
        error.safe_summary = summary  # type: ignore[attr-defined]
        return CollaborationCoordinator._failed_attempt(command, error)

    @staticmethod
    def _versioned_artifact_refs(
        artifact_refs: tuple[str, ...],
        *,
        version: int,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                f"{str(artifact_ref or '').rsplit('@', 1)[0]}@{version}"
                for artifact_ref in artifact_refs
            )
        )

    @staticmethod
    def _execution_ref(proposal: CollaborationProposal) -> str:
        digest = proposal.proposal_hash.removeprefix("sha256:")
        return f"{proposal.proposal_id}@{proposal.proposal_version}:{digest}"

    @staticmethod
    def _proposal_id(room_id: str, project_id: str) -> str:
        digest = hashlib.sha256(f"{room_id}|{project_id}".encode("utf-8")).hexdigest()[:16]
        return f"proposal-{digest}"

    @staticmethod
    def _summary(run_result: WalkingSkeletonRunResult) -> str:
        payloads = run_result.artifact_payloads
        brief = payloads.get("GameDesignBrief", {})
        logic = payloads.get("GameplayLogicPlan", {})
        art = payloads.get("ArtDirection", {})
        composition = payloads.get("SceneCompositionPlan", {})
        roles = [
            str(item.get("semantic_role") or "").strip()
            for item in logic.get("entity_slots", ())
            if isinstance(item, Mapping) and str(item.get("semantic_role") or "").strip()
        ]
        return (
            f"项目目标：{brief.get('project_goal', '')}\n"
            f"策划/程序实体槽位：{'、'.join(roles)}\n"
            f"美术风格：{'、'.join(str(value) for value in art.get('style_keywords', ()))}\n"
            f"场景构成：{'、'.join(str(value) for value in composition.get('entity_requirements', ()))}"
        ).strip()

    @staticmethod
    def _role_progress_events(
        command: UserCommand,
        proposal: CollaborationProposal,
    ) -> tuple[ProgressEvent, ...]:
        specs = (
            ("planning_artifacts_ready", "planning", "策划方案已完成。"),
            ("program_logic_ready", "program", "程序逻辑与必需实体槽位已完成。"),
            ("art_composition_ready", "art", "美术构图与图片提示词已完成。"),
            ("collaboration_proposal_ready", "gm", "GM 已完成方案汇总。"),
        )
        return tuple(
            ProgressEvent(
                schema_version=FRONTEND_INTERACTION_SCHEMA_VERSION,
                event_id=f"event.{proposal.proposal_id}.progress",
                command_id=command.command_id,
                room_id=command.room_id,
                project_id=proposal.project_id,
                task_id=f"task.{proposal.proposal_id}.{owner_role}",
                plan_id=proposal.proposal_id,
                scene_version=proposal.proposal_version,
                event_type=event_type,
                status="completed",
                detail={
                    "owner_role": owner_role,
                    "proposal_hash": proposal.proposal_hash,
                    "artifact_ref": proposal.artifact_ref,
                    "proposal_version": proposal.proposal_version,
                    "stage_text": stage_text,
                },
            )
            for event_type, owner_role, stage_text in specs
        )


__all__ = [
    "CollaborationAttemptReport",
    "CollaborationCoordinator",
    "CollaborationInProgressError",
    "CollaborationProposal",
    "CollaborationProposalResult",
    "CollaborationStageStatus",
]
