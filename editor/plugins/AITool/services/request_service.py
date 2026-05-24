import asyncio
import json
import uuid


class AIRequestService:
    def __init__(self):
        self.states: dict[str, dict] = {}

    def prepare_legacy_message(self, ai_message: str) -> tuple[str, str | None, str | None]:
        try:
            msg_data = json.loads(ai_message)
        except Exception:
            return ai_message, None, None

        if not isinstance(msg_data, dict):
            return ai_message, None, None

        metadata = msg_data.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            msg_data["metadata"] = metadata

        request_id = metadata.get("request_id") or msg_data.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            request_id = self.create_request_id()
            metadata["request_id"] = request_id
        else:
            metadata.setdefault("request_id", request_id)

        session_id = msg_data.get("session_id")
        return json.dumps(msg_data, ensure_ascii=False), request_id, session_id if isinstance(session_id, str) else None

    def normalize_chat_request(self, request: dict) -> tuple[dict | None, str | None, str | None, dict | None]:
        request_id = request.get("request_id")
        payload = request.get("payload")
        if payload is None:
            payload = request
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            return None, request_id if isinstance(request_id, str) else None, None, {
                "success": False,
                "request_id": request_id,
                "error": "INVALID_PAYLOAD",
            }

        request_id = request_id or payload.get("request_id")
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            payload["metadata"] = metadata
        if not isinstance(request_id, str) or not request_id:
            request_id = self.create_request_id()
        metadata.setdefault("request_id", request_id)

        session_id = request.get("session_id") or payload.get("session_id")
        session_id = session_id if isinstance(session_id, str) else None
        self.mark_accepted(request_id, session_id)
        return payload, request_id, session_id, None

    def mark_accepted(self, request_id: str, session_id: str | None):
        self.states[request_id] = {
            "request_id": request_id,
            "session_id": session_id,
            "status": "accepted",
            "task": None,
        }

    def get_status(self, request_id) -> dict:
        if not isinstance(request_id, str):
            return {"request_id": request_id, "status": "not_found"}
        state = self.states.get(request_id)
        if not isinstance(state, dict):
            return {"request_id": request_id, "status": "not_found"}
        return {
            "request_id": request_id,
            "session_id": state.get("session_id"),
            "status": state.get("status", "unknown"),
            "error": state.get("error"),
        }

    def cancel(self, request_id, loop) -> dict:
        if not isinstance(request_id, str):
            return {"success": False, "request_id": request_id, "status": "not_running"}
        state = self.states.get(request_id)
        if not isinstance(state, dict):
            return {"success": False, "request_id": request_id, "status": "not_running"}
        task = state.get("task")
        if isinstance(task, asyncio.Task) and not task.done():
            loop.call_soon_threadsafe(task.cancel)
            state["status"] = "cancelling"
            return {"success": True, "request_id": request_id, "status": "cancelling"}
        return {"success": False, "request_id": request_id, "status": "not_running"}

    def attach_task(self, request_id: str | None, task: asyncio.Task):
        if not request_id:
            return
        state = self.states.setdefault(request_id, {"request_id": request_id})
        state["task"] = task
        state["status"] = "running"

        def finish(done_task: asyncio.Task):
            current = self.states.get(request_id)
            if not current:
                return
            if done_task.cancelled():
                current["status"] = "cancelled"
            elif done_task.exception() is not None:
                current["status"] = "error"
                current["error"] = str(done_task.exception())
            else:
                current["status"] = "done"

        task.add_done_callback(finish)

    @staticmethod
    def create_request_id() -> str:
        return f"req_{uuid.uuid4().hex}"
