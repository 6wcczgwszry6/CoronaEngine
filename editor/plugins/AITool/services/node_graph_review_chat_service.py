"""Focused DeepSeek conversation for unresolved node-graph review tasks."""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

from .node_graph_review_service import NodeGraphReviewService

logger = logging.getLogger(__name__)


class NodeGraphReviewChatService:
    TIMEOUT_SECONDS = 45
    MAX_MESSAGES = 24
    MAX_TASKS = 20
    MAX_GRAPH_CHARS = 18000
    MAX_ACTIVE_TASKS = 40

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tasks: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _error(code: str, message: str) -> dict[str, Any]:
        return {"success": False, "status": "error", "error": code, "message": message}

    @classmethod
    def _normalize_payload(cls, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("包菜答疑请求格式不正确")
        messages = []
        for item in (payload.get("messages") or [])[-cls.MAX_MESSAGES :]:
            if not isinstance(item, dict):
                continue
            role = "assistant" if item.get("role") == "assistant" else "user"
            content = str(item.get("content") or "").strip()[:4000]
            if content:
                messages.append({"role": role, "content": content})
        if not messages or messages[-1]["role"] != "user":
            raise ValueError("请输入需要继续询问的问题")

        tasks = []
        for task in (payload.get("tasks") or [])[: cls.MAX_TASKS]:
            if not isinstance(task, dict):
                continue
            tasks.append({
                "issueKey": str(task.get("issueKey") or "")[:160],
                "title": str(task.get("title") or "")[:160],
                "message": str(task.get("message") or "")[:800],
                "suggestion": str(task.get("suggestion") or "")[:800],
                "nodeId": str(task.get("nodeId") or "")[:160],
                "blockId": str(task.get("blockId") or "")[:160],
            })

        graph_excerpt = payload.get("graphExcerpt") if isinstance(payload.get("graphExcerpt"), dict) else {}
        graph_text = json.dumps(graph_excerpt, ensure_ascii=False, separators=(",", ":"))
        if len(graph_text) > cls.MAX_GRAPH_CHARS:
            graph_text = graph_text[: cls.MAX_GRAPH_CHARS] + "…"

        return {
            "requestId": str(payload.get("requestId") or f"node_chat_{uuid.uuid4().hex}"),
            "projectScopeId": str(payload.get("projectScopeId") or "")[:160],
            "graphRevision": str(payload.get("graphRevision") or "")[:160],
            "selectedTaskKey": str(payload.get("selectedTaskKey") or "")[:160],
            "tasks": tasks,
            "graphText": graph_text,
            "messages": messages,
        }

    @staticmethod
    def _build_messages(request: dict[str, Any]) -> list[dict[str, str]]:
        selected = next(
            (task for task in request["tasks"] if task["issueKey"] == request["selectedTaskKey"]),
            None,
        )
        context = {
            "projectScopeId": request["projectScopeId"],
            "graphRevision": request["graphRevision"],
            "selectedTask": selected,
            "unresolvedTasks": request["tasks"],
            "graphExcerpt": request["graphText"],
        }
        return [
            {
                "role": "system",
                "content": (
                    "你是 CoronaEngine 的包菜节点答疑助手。只根据提供的未解决任务和可见节点片段回答。"
                    "优先解释问题为什么发生、应该把哪个积木接到哪里、如何验证已经修好。"
                    "不要编造项目中不存在的对象、节点、积木或接口；上下文不足时明确说明需要用户补充什么。"
                    "使用简洁、友好的中文，不输出 JSON，不写 Python 脚本。"
                ),
            },
            {
                "role": "system",
                "content": "当前节点上下文：" + json.dumps(context, ensure_ascii=False),
            },
            *request["messages"],
        ]

    @classmethod
    def _build_http_request(cls, request: dict[str, Any], settings: Any, *, stream: bool) -> urllib.request.Request:
        base = settings.base_url.rstrip("/")
        endpoint = base if base.endswith("/chat/completions") else base + "/chat/completions"
        body = {
            "model": settings.model,
            "temperature": 0.25,
            "max_tokens": 1400,
            "thinking": {"type": "disabled"},
            "stream": stream,
            "messages": cls._build_messages(request),
        }
        return urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + settings.api_key,
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if stream else "application/json",
            },
            method="POST",
        )

    @staticmethod
    def _extract_message(data: Any) -> str:
        choices = data.get("choices") if isinstance(data, dict) else None
        first = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first.get("message"), dict) else {}
        content = message.get("content")
        return content.strip() if isinstance(content, str) else ""

    @staticmethod
    def _extract_delta(data: Any) -> str:
        choices = data.get("choices") if isinstance(data, dict) else None
        first = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        delta = first.get("delta") if isinstance(first.get("delta"), dict) else {}
        content = delta.get("content")
        if isinstance(content, str):
            return content
        return NodeGraphReviewChatService._extract_message(data)

    def _append_content(self, task_id: str, text: str) -> None:
        if not text:
            return
        with self._lock:
            state = self._tasks.get(task_id)
            if not state or state["cancel"].is_set():
                return
            state["content"] += text
            state["updatedAt"] = time.time()

    def _finish_task(self, task_id: str, status: str, *, error: str = "", message: str = "") -> None:
        with self._lock:
            state = self._tasks.get(task_id)
            if not state:
                return
            state["status"] = status
            state["error"] = error
            state["message"] = message
            state["updatedAt"] = time.time()

    def _run_stream(self, task_id: str, request: dict[str, Any], settings: Any) -> None:
        try:
            http_request = self._build_http_request(request, settings, stream=True)
            with urllib.request.urlopen(http_request, timeout=self.TIMEOUT_SECONDS) as response:
                content_type = str(response.headers.get("Content-Type") or "").lower()
                if "text/event-stream" not in content_type:
                    data = json.loads(response.read().decode("utf-8"))
                    content = self._extract_message(data)
                    if not content:
                        raise ValueError("DeepSeek 返回了空内容")
                    self._append_content(task_id, content)
                else:
                    for raw_line in response:
                        with self._lock:
                            state = self._tasks.get(task_id)
                            cancelled = not state or state["cancel"].is_set()
                        if cancelled:
                            self._finish_task(task_id, "cancelled", message="已停止等待本次回答。")
                            return
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line or line.startswith(":") or not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        self._append_content(task_id, self._extract_delta(chunk))

            with self._lock:
                state = self._tasks.get(task_id)
                if not state:
                    return
                if state["cancel"].is_set():
                    state["status"] = "cancelled"
                    state["message"] = "已停止等待本次回答。"
                elif not str(state.get("content") or "").strip():
                    state["status"] = "error"
                    state["error"] = "AI_EMPTY_RESPONSE"
                    state["message"] = "DeepSeek 没有返回可显示的内容。"
                else:
                    state["status"] = "completed"
                state["updatedAt"] = time.time()
        except urllib.error.HTTPError as exc:
            code = f"HTTP_{exc.code}"
            message = "DeepSeek 请求失败，请稍后再试。"
            if exc.code == 401:
                message = "DeepSeek API Key 无效或已过期。"
            elif exc.code == 429:
                message = "DeepSeek 请求过于频繁，请稍后再试。"
            self._finish_task(task_id, "error", error=code, message=message)
        except urllib.error.URLError:
            self._finish_task(task_id, "error", error="NETWORK_ERROR", message="无法连接 DeepSeek，请检查网络和配置。")
        except Exception as exc:
            logger.debug("Node graph review chat stream failed: %s", exc)
            self._finish_task(task_id, "error", error="AI_RESPONSE_ERROR", message="DeepSeek 返回内容无法读取，请稍后再试。")

    def _prune_locked(self) -> None:
        if len(self._tasks) < self.MAX_ACTIVE_TASKS:
            return
        completed = sorted(
            (
                (task_id, state)
                for task_id, state in self._tasks.items()
                if state.get("status") in {"completed", "cancelled", "error"}
            ),
            key=lambda item: float(item[1].get("updatedAt") or 0),
        )
        while len(self._tasks) >= self.MAX_ACTIVE_TASKS and completed:
            task_id, _ = completed.pop(0)
            self._tasks.pop(task_id, None)

    def start(self, payload: Any) -> dict[str, Any]:
        try:
            request = self._normalize_payload(payload)
            settings = NodeGraphReviewService._resolve_settings()
            if not settings.api_key:
                return self._error("AI_NOT_CONFIGURED", "DeepSeek 未配置，包菜答疑暂不可用。")

            task_id = f"node_chat_task_{uuid.uuid4().hex}"
            now = time.time()
            state = {
                "taskId": task_id,
                "requestId": request["requestId"],
                "status": "running",
                "content": "",
                "error": "",
                "message": "",
                "cancel": threading.Event(),
                "createdAt": now,
                "updatedAt": now,
            }
            with self._lock:
                self._prune_locked()
                self._tasks[task_id] = state
            thread = threading.Thread(
                target=self._run_stream,
                args=(task_id, request, settings),
                name=f"NodeGraphChat-{task_id[-8:]}",
                daemon=True,
            )
            state["thread"] = thread
            thread.start()
            return {
                "success": True,
                "status": "accepted",
                "taskId": task_id,
                "requestId": request["requestId"],
            }
        except ValueError as exc:
            return self._error("INVALID_PAYLOAD", str(exc))
        except Exception as exc:
            logger.debug("Node graph review chat start failed: %s", exc)
            return self._error("AI_CHAT_FAILED", "包菜答疑暂时不可用，请稍后再试。")

    def status(self, task_id: Any) -> dict[str, Any]:
        task_key = str(task_id or "")
        with self._lock:
            state = self._tasks.get(task_key)
            if not state:
                return self._error("TASK_NOT_FOUND", "没有找到这次包菜答疑请求。")
            return {
                "success": True,
                "status": state["status"],
                "taskId": task_key,
                "requestId": state["requestId"],
                "content": str(state.get("content") or ""),
                "error": str(state.get("error") or ""),
                "message": str(state.get("message") or ""),
            }

    def cancel(self, task_id: Any) -> dict[str, Any]:
        task_key = str(task_id or "")
        with self._lock:
            state = self._tasks.get(task_key)
            if not state:
                return self._error("TASK_NOT_FOUND", "没有找到这次包菜答疑请求。")
            if state["status"] in {"completed", "cancelled", "error"}:
                return {"success": True, "status": state["status"], "taskId": task_key}
            state["cancel"].set()
            state["status"] = "cancelling"
            state["updatedAt"] = time.time()
            return {"success": True, "status": "cancelling", "taskId": task_key}

    def chat(self, payload: Any) -> dict[str, Any]:
        """Backward-compatible one-shot response for callers that have not adopted polling."""
        started = self.start(payload)
        if started.get("success") is not True:
            return started
        task_id = started["taskId"]
        deadline = time.monotonic() + self.TIMEOUT_SECONDS + 5
        while time.monotonic() < deadline:
            result = self.status(task_id)
            if result.get("status") == "completed":
                return {"success": True, "status": "ok", "message": result.get("content", "")}
            if result.get("status") in {"cancelled", "error"}:
                return self._error(result.get("error") or "AI_CHAT_FAILED", result.get("message") or "包菜答疑失败。")
            time.sleep(0.1)
        self.cancel(task_id)
        return self._error("AI_TIMEOUT", "DeepSeek 响应超时，请稍后再试。")

    def shutdown(self) -> None:
        with self._lock:
            for state in self._tasks.values():
                state["cancel"].set()


_service: NodeGraphReviewChatService | None = None


def get_node_graph_review_chat_service() -> NodeGraphReviewChatService:
    global _service
    if _service is None:
        _service = NodeGraphReviewChatService()
    return _service
