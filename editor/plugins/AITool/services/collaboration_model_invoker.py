"""Application-level deadlines for collaboration model calls."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any, Callable


class CollaborationInvocationTimeout(TimeoutError):
    error_code = "collaboration_stage_timeout"


class CollaborationInvocationSaturated(RuntimeError):
    error_code = "collaboration_invoker_saturated"


@dataclass
class _InvocationState:
    room_id: str
    attempt_id: str
    stage_token: str
    done: threading.Event
    value: Any = None
    error: BaseException | None = None
    timed_out: bool = False


class CollaborationModelInvoker:
    """Run synchronous model calls behind a bounded application deadline."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.RLock()
        self._active_by_room: dict[str, _InvocationState] = {}

    def invoke(
        self,
        *,
        room_id: str,
        attempt_id: str,
        stage_token: str,
        deadline_s: float,
        call: Callable[[], Any],
        on_late_result: Callable[[_InvocationState], None] | None = None,
    ) -> Any:
        room = str(room_id or "default")
        timeout = float(deadline_s)
        if timeout <= 0:
            raise CollaborationInvocationTimeout("collaboration model deadline already expired")
        if not callable(call):
            raise TypeError("call must be callable")

        state = _InvocationState(
            room_id=room,
            attempt_id=str(attempt_id or ""),
            stage_token=str(stage_token or ""),
            done=threading.Event(),
        )
        with self._lock:
            active = self._active_by_room.get(room)
            if active is not None and not active.done.is_set():
                raise CollaborationInvocationSaturated(
                    f"collaboration model invocation is still active for room {room}"
                )
            self._active_by_room[room] = state

        def run() -> None:
            try:
                state.value = call()
            except BaseException as exc:  # noqa: BLE001
                state.error = exc
            finally:
                state.done.set()
                late = False
                with self._lock:
                    late = state.timed_out
                    if self._active_by_room.get(room) is state:
                        self._active_by_room.pop(room, None)
                if late and callable(on_late_result):
                    on_late_result(state)

        threading.Thread(
            target=run,
            name=f"collaboration-model-{state.stage_token or 'call'}",
            daemon=True,
        ).start()
        started_at = self._clock()
        if not state.done.wait(timeout):
            with self._lock:
                if not state.done.is_set():
                    state.timed_out = True
            if state.done.is_set():
                return self._completed_value(state)
            elapsed = max(0.0, self._clock() - started_at)
            raise CollaborationInvocationTimeout(
                f"collaboration model exceeded {timeout:.3f}s deadline after {elapsed:.3f}s"
            )
        return self._completed_value(state)

    def active(self, room_id: str) -> bool:
        with self._lock:
            state = self._active_by_room.get(str(room_id or "default"))
            return bool(state is not None and not state.done.is_set())

    @staticmethod
    def _completed_value(state: _InvocationState) -> Any:
        if state.error is not None:
            raise state.error
        return state.value


__all__ = [
    "CollaborationInvocationSaturated",
    "CollaborationInvocationTimeout",
    "CollaborationModelInvoker",
]
