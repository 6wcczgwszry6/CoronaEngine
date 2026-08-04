"""Production-facing, non-executable entry for the three-role demo runner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Literal

from .agent_collaboration.walking_skeleton import (
    DemoScenarioRunner,
    EngineCapabilityPort,
    UnavailableEngineCapabilityPort,
    UserCommandFixture,
    WalkingSkeletonRunResult,
)
from .frontend_adapter import (
    FrontendBusinessProtocolAdapter,
    ProgressEvent,
    UserCommand,
)
from .integration_contracts import BlockedResult, MissingRequirement
from .schema_versions import FRONTEND_INTERACTION_SCHEMA_VERSION


@dataclass(frozen=True)
class CollaborationReadOnlyResult:
    status: Literal["accepted", "blocked", "replayed"]
    command: UserCommand
    run_result: WalkingSkeletonRunResult | None
    progress_events: tuple[ProgressEvent, ...]
    blocked_result: BlockedResult | None
    executable: bool = False

    def __post_init__(self) -> None:
        if self.executable:
            raise ValueError("CollaborationReadOnlyResult cannot be executable")
        if self.status == "accepted":
            if self.run_result is None or not self.progress_events or self.blocked_result is not None:
                raise ValueError("accepted collaboration result is incomplete")
        elif self.status == "blocked":
            if self.run_result is not None or self.progress_events or self.blocked_result is None:
                raise ValueError("blocked collaboration result requires one blocker")
        elif self.status == "replayed":
            if self.run_result is None or self.progress_events or self.blocked_result is not None:
                raise ValueError("replayed collaboration result must reuse the prior run without events")
        else:
            raise ValueError("unsupported collaboration result status")


class CollaborationReadOnlyEntry:
    """Run the formal artifact workflow while every execution path is locked."""

    def __init__(
        self,
        *,
        engine_capabilities: EngineCapabilityPort | None = None,
        clock=None,
        planning_reasoner: object | None = None,
        program_reasoner: object | None = None,
        art_reasoner: object | None = None,
        retry_failed_agents: bool = True,
        stage_observer=None,
    ) -> None:
        self._frontend = FrontendBusinessProtocolAdapter()
        self._runner = DemoScenarioRunner(
            engine_capabilities=engine_capabilities or UnavailableEngineCapabilityPort(),
            clock=clock or (lambda: datetime.now(timezone.utc)),
            planning_reasoner=planning_reasoner,
            program_reasoner=program_reasoner,
            art_reasoner=art_reasoner,
            retry_failed_agents=retry_failed_agents,
            stage_observer=stage_observer,
        )
        self._results: dict[str, tuple[UserCommand, WalkingSkeletonRunResult]] = {}
        self._lock = RLock()

    def run(self, command: UserCommand) -> CollaborationReadOnlyResult:
        if not isinstance(command, UserCommand):
            raise TypeError("CollaborationReadOnlyEntry.run requires UserCommand")
        if command.command_type != "start_project":
            return self._blocked(
                command,
                error_code="collaboration_command_not_readonly_start",
                requirement_id="collaboration.command.start_project",
                summary="Only start_project can enter the read-only collaboration runner.",
                next_action="Use start_project or wait for a later command-specific gate.",
            )
        with self._lock:
            cached = self._results.get(command.command_id)
            if cached is not None:
                previous_command, previous_result = cached
                if previous_command != command:
                    return self._blocked(
                        command,
                        error_code="collaboration_command_content_conflict",
                        requirement_id="collaboration.command_id_content",
                        summary="The command_id was reused with different project content.",
                        next_action="Reuse the original result or submit a new command_id.",
                    )
                return CollaborationReadOnlyResult(
                    status="replayed",
                    command=command,
                    run_result=previous_result,
                    progress_events=(),
                    blocked_result=None,
                )
            dispatch = self._frontend.dispatch(command)
            if dispatch.status == "blocked":
                return CollaborationReadOnlyResult(
                    status="blocked",
                    command=command,
                    run_result=None,
                    progress_events=(),
                    blocked_result=dispatch.blocked_result,
                )
            fixture = self._fixture_from_command(command)
            run_result = self._runner.run(fixture)
            if run_result.demo_result.executable:
                raise RuntimeError("read-only collaboration runner returned an executable result")
            final_event = ProgressEvent(
                schema_version=FRONTEND_INTERACTION_SCHEMA_VERSION,
                event_id=f"event.{command.command_id}.collaboration_result",
                command_id=command.command_id,
                room_id=command.room_id,
                project_id=fixture.project_id,
                task_id=run_result.demo_result.task_graph_id,
                plan_id="",
                scene_version=0,
                event_type="collaboration_result_ready",
                status=run_result.demo_result.status,
                detail={
                    "artifact_count": len(run_result.demo_result.artifact_refs),
                    "preflight_status": run_result.preflight.status,
                    "pending_runtime_verification_count": len(
                        run_result.demo_result.pending_runtime_verifications
                    ),
                    "executable": False,
                },
            )
            events = tuple(dispatch.events) + (final_event,)
            self._results[command.command_id] = (command, run_result)
            return CollaborationReadOnlyResult(
                status="accepted",
                command=command,
                run_result=run_result,
                progress_events=events,
                blocked_result=None,
            )

    @staticmethod
    def _fixture_from_command(command: UserCommand) -> UserCommandFixture:
        payload = command.payload
        return UserCommandFixture(
            schema_version=FRONTEND_INTERACTION_SCHEMA_VERSION,
            command_id=command.command_id,
            room_id=command.room_id,
            project_id=str(payload.get("project_id") or ""),
            scenario_id=str(payload.get("scenario_id") or ""),
            project_goal=str(payload.get("project_goal") or ""),
            requested_by=str(payload.get("requested_by") or "host"),
        )

    @staticmethod
    def _blocked(
        command: UserCommand,
        *,
        error_code: str,
        requirement_id: str,
        summary: str,
        next_action: str,
    ) -> CollaborationReadOnlyResult:
        blocker = BlockedResult(
            node_id="collaboration_readonly_entry",
            status="blocked",
            error_code=error_code,
            summary=summary,
            missing_requirements=(
                MissingRequirement(
                    requirement_id=requirement_id,
                    owner_domain="integration",
                    description=summary,
                ),
            ),
            owner_domain="integration",
            retryable=False,
            next_action=next_action,
            evidence_refs=("adapter:collaboration_readonly_entry",),
        )
        return CollaborationReadOnlyResult(
            status="blocked",
            command=command,
            run_result=None,
            progress_events=(),
            blocked_result=blocker,
        )


__all__ = ["CollaborationReadOnlyEntry", "CollaborationReadOnlyResult"]
