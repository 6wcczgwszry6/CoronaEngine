"""World-scoped persistence, guidance tasks, and adaptive assistance scoring."""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from utils.settings import settings_manager

from .node_graph_review_service import NodeGraphReviewService

logger = logging.getLogger(__name__)


class CabbageContextService:
    SCHEMA_VERSION = 1
    CONTEXT_DIR = "CabbageAssistant"
    CONTEXT_FILE = "context.json"
    MAX_RECENT_EVENTS = 200
    MAX_PROFILE_HISTORY = 50
    MAX_ISSUE_MEMORY = 200
    MAX_SCORE_TASKS = 24
    SCORE_MIN_INTERVAL_SECONDS = 300
    ISSUE_PATTERN_FIELDS = (
        "blockType", "workspaceRole", "relationType",
        "missingInput", "objectRequirement", "edgeId",
    )
    CHAT_GUIDANCE_INTENTS = {
        "connect_object_reference", "select_existing_object", "create_node",
        "move_node", "connect_nodes", "drag_block", "edit_block_parameter",
        "set_transition_condition", "run_node_graph", "import_model",
        "transform_model", "adjust_lighting", "adjust_physics",
    }
    IMPORTANT_EVENT_TYPES = {
        "model_imported",
        "actor_created",
        "actor_deleted",
        "transform_position",
        "transform_rotation",
        "transform_scale",
        "lighting_changed",
        "physics_changed",
        "node_edited",
        "node_created",
        "node_moved",
        "node_connected",
        "block_added",
        "block_parameter_changed",
        "node_issue_found",
        "node_issue_fixed",
        "run_started",
        "run_succeeded",
        "run_failed",
        "tutorial_completed",
    }
    METRIC_BY_EVENT = {
        "model_imported": "modelImports",
        "transform_position": "transformEdits",
        "transform_rotation": "transformEdits",
        "transform_scale": "transformEdits",
        "lighting_changed": "lightingEdits",
        "physics_changed": "physicsEdits",
        "node_edited": "nodeEdits",
        "node_created": "nodeEdits",
        "node_connected": "nodeEdits",
        "block_added": "nodeEdits",
        "block_parameter_changed": "nodeEdits",
        "node_issue_found": "nodeErrors",
        "node_issue_fixed": "nodeIssueFixes",
        "run_succeeded": "runSuccesses",
        "run_failed": "runFailures",
    }
    TUTORIAL_TASKS = (
        {
            "taskKey": "tutorial.import_model",
            "type": "tutorial",
            "track": "scene",
            "order": 1,
            "title": "导入一个物体",
            "message": "先把一个模型加入当前世界，后续才能练习摆放和属性调整。",
            "suggestion": "打开场景管理，使用导入或添加模型功能，把一个模型放入场景。",
            "completionCriteria": "成功导入模型，或场景中新建一个模型对象。",
        },
        {
            "taskKey": "tutorial.transform_model",
            "type": "tutorial",
            "track": "scene",
            "order": 2,
            "title": "调整一个物体",
            "message": "修改模型的变换参数，观察它在场景中的位置、朝向或大小变化。",
            "suggestion": "选中一个模型，在对象 Dock 的“变换”区域修改位置、旋转或缩放中的任意参数。",
            "completionCriteria": "成功保存一次位置、旋转或缩放修改。",
        },
        {
            "taskKey": "tutorial.adjust_lighting",
            "type": "tutorial",
            "track": "scene",
            "order": 3,
            "title": "调整场景光照",
            "message": "尝试改变光照状态或方向，观察模型明暗和场景氛围的变化。",
            "suggestion": "在场景管理中切换光照，或调整光照方向后确认效果。",
            "completionCriteria": "成功修改光照启用状态或光照方向。",
        },
        {
            "taskKey": "tutorial.adjust_physics",
            "type": "tutorial",
            "track": "scene",
            "order": 4,
            "title": "调整物理属性",
            "message": "给模型设置物理效果，让它能够参与重力、碰撞或反弹。",
            "suggestion": "选中一个模型，启用物理或修改质量、弹性、阻尼、锁轴中的任意一项。",
            "completionCriteria": "成功修改一次模型物理属性。",
        },
        {
            "taskKey": "tutorial.create_node",
            "type": "tutorial",
            "track": "node",
            "order": 1,
            "title": "创建一个节点",
            "message": "先建立一个新的状态节点，为后续的积木逻辑和流程跳转准备容器。",
            "suggestion": "在节点 Dock 中拖入一个状态节点，并把它放到画布中。",
            "completionCriteria": "成功创建一个新的状态节点。",
        },
        {
            "taskKey": "tutorial.move_node",
            "type": "tutorial",
            "track": "node",
            "order": 2,
            "title": "拖拽一个节点",
            "message": "整理节点位置，让状态流程更容易阅读和连接。",
            "suggestion": "在节点 Dock 的画布中拖动任意节点，并把它放到新的位置。",
            "completionCriteria": "节点位置产生一次有效变化。",
        },
        {
            "taskKey": "tutorial.connect_nodes",
            "type": "tutorial",
            "track": "node",
            "order": 3,
            "title": "连接两个节点",
            "message": "建立两个不同状态之间的跳转路径，让流程能够从一个节点进入另一个节点。",
            "suggestion": "依次点击两个不同节点的端口，创建一条有效连线。",
            "completionCriteria": "两个不同节点之间成功新增一条连线。",
        },
        {
            "taskKey": "tutorial.drag_block",
            "type": "tutorial",
            "track": "node",
            "order": 4,
            "title": "向节点拖入一个积木",
            "message": "把一个积木放进节点工作区，开始为当前状态添加实际行为。",
            "suggestion": "从左侧积木列表拖动一个积木，并放入当前节点的积木区域。",
            "completionCriteria": "通过拖拽方式成功创建一个积木。",
        },
        {
            "taskKey": "tutorial.edit_block_parameter",
            "type": "tutorial",
            "track": "node",
            "order": 5,
            "title": "修改一个积木参数",
            "message": "调整积木字段，让同一个功能使用你需要的按键、数值、对象或条件。",
            "suggestion": "修改任意积木中的下拉项、文本或数值字段。",
            "completionCriteria": "积木的一个字段值发生有效变化。",
        },
        {
            "taskKey": "tutorial.set_transition_condition",
            "type": "tutorial",
            "track": "node",
            "order": 6,
            "title": "设置一个跳转条件",
            "message": "给节点连线添加 Boolean 条件，控制流程在什么情况下进入下一个状态。",
            "suggestion": "选中一条节点连线，在条件工作区放入能够返回 Boolean 的积木。",
            "completionCriteria": "跳转条件工作区成功加入一个条件积木。",
        },
        {
            "taskKey": "tutorial.run_node_graph",
            "type": "tutorial",
            "track": "node",
            "order": 7,
            "title": "运行一次节点逻辑",
            "message": "点击运行当前节点图，开始验证节点、连线和积木的执行效果。",
            "suggestion": "直接点击节点 Dock 中的运行按钮；节点会实时保存，不需要额外执行保存操作。",
            "completionCriteria": "节点逻辑成功发起一次运行。",
        },
    )
    RETIRED_TUTORIAL_TASK_KEYS = {"tutorial.rotate_model"}

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="CabbageProfile")
        self._score_tasks: dict[str, dict[str, Any]] = {}
        self._closed = False

    @staticmethod
    def _error(code: str, message: str) -> dict[str, Any]:
        return {"success": False, "status": "error", "error": code, "message": message}

    @staticmethod
    def _clone(value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False))

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @classmethod
    def _active_project_path(cls) -> Path:
        # settings_manager is the authoritative world resolver. Its property already
        # hydrates from last_project when no world has been activated yet; forcing
        # last_project on every request can overwrite a newer in-memory world switch.
        project_path = settings_manager.active_project_path
        if not project_path:
            raise RuntimeError("当前没有打开世界")
        path = Path(project_path).expanduser().resolve()
        if not (path / "project.ini").is_file():
            raise RuntimeError("当前世界目录无效")
        return path

    @classmethod
    def _context_path(cls, project_path: Path) -> Path:
        return project_path / cls.CONTEXT_DIR / cls.CONTEXT_FILE

    @staticmethod
    def _validate_payload_world(project_path: Path, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        expected = str(payload.get("worldId") or "").strip()
        if expected and expected != project_path.name:
            raise ValueError("请求属于其他世界，已忽略迟到的上下文写入")

    @classmethod
    def _tutorial_templates(cls) -> dict[str, dict[str, Any]]:
        return {str(task["taskKey"]): task for task in cls.TUTORIAL_TASKS}

    @classmethod
    def _ensure_tutorial_slots_locked(cls, context: dict[str, Any], now: int) -> None:
        """Keep one visible scene task and one visible node task; queue the rest."""
        templates = cls._tutorial_templates()
        history_keys = {
            str(task.get("taskKey") or "")
            for task in context.get("taskHistory") or []
            if isinstance(task, dict) and task.get("type") == "tutorial"
        }
        normalized_tasks: list[dict[str, Any]] = []
        for raw in context.get("activeTasks") or []:
            if not isinstance(raw, dict):
                continue
            task_key = str(raw.get("taskKey") or "")
            template = templates.get(task_key)
            if task_key in cls.RETIRED_TUTORIAL_TASK_KEYS:
                continue
            if not template or raw.get("type") != "tutorial":
                normalized_tasks.append(raw)
                continue
            if task_key in history_keys:
                continue
            task = dict(raw)
            task.update({
                "type": "tutorial",
                "track": template["track"],
                "order": template["order"],
                "title": template["title"],
                "message": template["message"],
                "suggestion": template["suggestion"],
                "completionCriteria": template["completionCriteria"],
            })
            normalized_tasks.append(task)
        context["activeTasks"] = normalized_tasks

        existing_keys = {
            str(task.get("taskKey") or "")
            for task in context["activeTasks"]
            if isinstance(task, dict)
        }
        for template in cls.TUTORIAL_TASKS:
            task_key = str(template["taskKey"])
            if task_key in history_keys or task_key in existing_keys:
                continue
            task = dict(template)
            task.update({
                "status": "queued",
                "createdAt": now,
                "updatedAt": now,
                "completedAt": 0,
                "resolvedAt": 0,
            })
            context["activeTasks"].append(task)

        for track in ("scene", "node"):
            track_tasks = sorted(
                (
                    task for task in context["activeTasks"]
                    if isinstance(task, dict)
                    and task.get("type") == "tutorial"
                    and task.get("track") == track
                ),
                key=lambda task: int(task.get("order") or 0),
            )
            if not track_tasks:
                continue
            visible = [task for task in track_tasks if task.get("status") in {"active", "pending"}]
            selected = visible[0] if visible else track_tasks[0]
            for task in track_tasks:
                next_status = "active" if task is selected else "queued"
                if task.get("status") != next_status:
                    task["status"] = next_status
                    task["updatedAt"] = now

    @classmethod
    def _default_context(cls, project_path: Path) -> dict[str, Any]:
        now = cls._now_ms()
        context = {
            "schemaVersion": cls.SCHEMA_VERSION,
            "worldId": project_path.name,
            "projectPathIdentity": os.path.normcase(str(project_path)),
            "profile": {
                "score": 0,
                "source": "deepseek",
                "updatedAt": 0,
                "reasonCodes": [],
                "lastScoredEventCount": 0,
            },
            "profileHistory": [],
            "issueMemory": {},
            "metrics": {
                "modelImports": 0,
                "transformEdits": 0,
                "lightingEdits": 0,
                "physicsEdits": 0,
                "nodeEdits": 0,
                "nodeErrors": 0,
                "nodeIssueFixes": 0,
                "runSuccesses": 0,
                "runFailures": 0,
                "importantEventCount": 0,
                "firstActivityAt": 0,
                "lastActivityAt": 0,
            },
            "tutorialProgress": {
                "positionChanged": False,
                "scaleChanged": False,
            },
            "activeTasks": [],
            "taskHistory": [],
            "chatMessages": [],
            "recentOperationEvents": [],
            "updatedAt": now,
        }
        cls._ensure_tutorial_slots_locked(context, now)
        return context

    @classmethod
    def _normalize_context(cls, value: Any, project_path: Path) -> dict[str, Any]:
        default = cls._default_context(project_path)
        if not isinstance(value, dict):
            return default
        value["schemaVersion"] = cls.SCHEMA_VERSION
        value["worldId"] = project_path.name
        value["projectPathIdentity"] = os.path.normcase(str(project_path))
        raw_profile = value.get("profile") if isinstance(value.get("profile"), dict) else {}
        legacy_score = raw_profile.get("score", raw_profile.get("fluencyScore", 0))
        try:
            normalized_score = max(0, min(int(round(float(legacy_score or 0))), 100))
        except (TypeError, ValueError):
            normalized_score = 0
        value["profile"] = {
            "score": normalized_score,
            "source": str(raw_profile.get("source") or "deepseek")[:40],
            "updatedAt": max(0, int(raw_profile.get("updatedAt") or 0)),
            "reasonCodes": [
                str(item)[:80]
                for item in (raw_profile.get("reasonCodes") or raw_profile.get("fluencyReasonCodes") or [])
                if str(item).strip()
            ][:12],
            "lastScoredEventCount": max(0, int(raw_profile.get("lastScoredEventCount", raw_profile.get("lastClassifiedEventCount", 0)) or 0)),
        }
        for key in ("metrics", "tutorialProgress"):
            merged = dict(default[key])
            if isinstance(value.get(key), dict):
                merged.update(value[key])
            value[key] = merged
        for key in ("profileHistory", "activeTasks", "taskHistory", "chatMessages", "recentOperationEvents"):
            if not isinstance(value.get(key), list):
                value[key] = []
        if not isinstance(value.get("issueMemory"), dict):
            value["issueMemory"] = {}
        now = cls._now_ms()
        cls._ensure_tutorial_slots_locked(value, now)
        value["profileHistory"] = value["profileHistory"][-cls.MAX_PROFILE_HISTORY :]
        value["recentOperationEvents"] = value["recentOperationEvents"][-cls.MAX_RECENT_EVENTS :]
        cls._normalize_issue_memory_locked(value)
        value["updatedAt"] = int(value.get("updatedAt") or now)
        return value

    def _read_locked(self, project_path: Path) -> dict[str, Any]:
        path = self._context_path(project_path)
        if not path.is_file():
            context = self._default_context(project_path)
            self._write_locked(project_path, context)
            return context
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            context = self._normalize_context(value, project_path)
            return context
        except Exception:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            corrupt = path.with_name(f"context.{stamp}.corrupt.json")
            try:
                shutil.copy2(path, corrupt)
            except Exception:
                logger.debug("Failed to back up corrupt Cabbage context", exc_info=True)
            logger.warning("Cabbage context was invalid and has been reset: %s", path)
            context = self._default_context(project_path)
            self._write_locked(project_path, context)
            return context


    @classmethod
    def _normalize_issue_pattern(cls, raw: Any) -> dict[str, str]:
        if not isinstance(raw, dict):
            return {}
        normalized: dict[str, str] = {}
        for field in cls.ISSUE_PATTERN_FIELDS:
            value = str(raw.get(field) or "").strip()[:180]
            if value:
                normalized[field] = value
        return normalized

    @classmethod
    def _normalize_issue_memory_locked(cls, context: dict[str, Any]) -> None:
        raw_memory = context.get("issueMemory")
        normalized: dict[str, dict[str, Any]] = {}
        if isinstance(raw_memory, dict):
            for raw_code, raw_entry in raw_memory.items():
                code = str(raw_code or "").strip()[:180]
                if not code or not isinstance(raw_entry, dict):
                    continue
                normalized[code] = {
                    "occurrences": max(0, int(raw_entry.get("occurrences") or 0)),
                    "resolvedCount": max(0, int(raw_entry.get("resolvedCount") or 0)),
                    "chatDiscussionCount": max(0, int(raw_entry.get("chatDiscussionCount") or 0)),
                    "firstSeenAt": max(0, int(raw_entry.get("firstSeenAt") or 0)),
                    "lastSeenAt": max(0, int(raw_entry.get("lastSeenAt") or 0)),
                    "lastDiscussedAt": max(0, int(raw_entry.get("lastDiscussedAt") or 0)),
                    "pattern": cls._normalize_issue_pattern(raw_entry.get("pattern")),
                }

        if not normalized:
            for task in (context.get("activeTasks") or []) + (context.get("taskHistory") or []):
                if not isinstance(task, dict) or task.get("type") != "node-issue":
                    continue
                code = str(task.get("code") or task.get("issueKey") or task.get("taskKey") or "").strip()[:180]
                if not code:
                    continue
                entry = normalized.setdefault(code, {
                    "occurrences": 0, "resolvedCount": 0, "chatDiscussionCount": 0,
                    "firstSeenAt": 0, "lastSeenAt": 0, "lastDiscussedAt": 0, "pattern": {},
                })
                entry["occurrences"] += 1
                entry["pattern"].update(cls._normalize_issue_pattern(task.get("pattern")))
                seen_at = int(task.get("firstDetectedAt") or task.get("createdAt") or 0)
                entry["firstSeenAt"] = min(filter(None, (entry["firstSeenAt"], seen_at)), default=0)
                entry["lastSeenAt"] = max(entry["lastSeenAt"], seen_at)
                if task.get("status") == "resolved" or int(task.get("resolvedAt") or 0) > 0:
                    entry["resolvedCount"] += 1
            for message in context.get("chatMessages") or []:
                if not isinstance(message, dict) or message.get("role") != "user":
                    continue
                code = str(message.get("issueCode") or "").strip()[:180]
                if not code:
                    continue
                entry = normalized.setdefault(code, {
                    "occurrences": 0, "resolvedCount": 0, "chatDiscussionCount": 0,
                    "firstSeenAt": 0, "lastSeenAt": 0, "lastDiscussedAt": 0, "pattern": {},
                })
                entry["chatDiscussionCount"] += 1
                entry["lastDiscussedAt"] = max(entry["lastDiscussedAt"], int(message.get("createdAt") or 0))

        ordered = sorted(normalized.items(), key=lambda item: max(item[1]["lastSeenAt"], item[1]["lastDiscussedAt"]), reverse=True)
        context["issueMemory"] = dict(ordered[: cls.MAX_ISSUE_MEMORY])

    @classmethod
    def _issue_memory_entry_locked(cls, context: dict[str, Any], code: str) -> dict[str, Any]:
        cls._normalize_issue_memory_locked(context)
        key = str(code or "logic_issue").strip()[:180] or "logic_issue"
        return context["issueMemory"].setdefault(key, {
            "occurrences": 0,
            "resolvedCount": 0,
            "chatDiscussionCount": 0,
            "firstSeenAt": 0,
            "lastSeenAt": 0,
            "lastDiscussedAt": 0,
            "pattern": {},
        })

    def _write_locked(self, project_path: Path, context: dict[str, Any]) -> None:
        path = self._context_path(project_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        context["updatedAt"] = self._now_ms()
        temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temp_path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, path)

    def load(self) -> dict[str, Any]:
        try:
            project_path = self._active_project_path()
            with self._lock:
                context = self._read_locked(project_path)
                self._write_locked(project_path, context)
                return {"success": True, "status": "ok", "context": self._clone(context)}
        except Exception as exc:
            logger.warning("Unable to load Cabbage context: %s", exc)
            return self._error("CONTEXT_LOAD_FAILED", str(exc))

    @classmethod
    def _normalize_event(cls, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("包菜操作事件格式不正确")
        event_type = str(payload.get("type") or "").strip()[:80]
        if not event_type:
            raise ValueError("包菜操作事件缺少 type")
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        safe_details: dict[str, Any] = {}
        for key, raw in details.items():
            name = str(key)[:80]
            if isinstance(raw, (str, int, float, bool)) or raw is None:
                safe_details[name] = raw if not isinstance(raw, str) else raw[:500]
        return {
            "eventId": str(payload.get("eventId") or f"event_{uuid.uuid4().hex}"),
            "type": event_type,
            "category": str(payload.get("category") or "editor")[:80],
            "success": payload.get("success") is not False,
            "timestamp": int(payload.get("timestamp") or cls._now_ms()),
            "details": safe_details,
        }

    @staticmethod
    def _find_task(context: dict[str, Any], task_key: str) -> dict[str, Any] | None:
        return next((task for task in context["activeTasks"] if isinstance(task, dict) and task.get("taskKey") == task_key), None)

    @classmethod
    def _complete_task_locked(cls, context: dict[str, Any], task_key: str, now: int) -> bool:
        task = cls._find_task(context, task_key)
        if not task:
            return False
        context["activeTasks"].remove(task)
        task = dict(task)
        task.update({"status": "completed", "updatedAt": now, "completedAt": now})
        context["taskHistory"].append(task)
        return True

    @classmethod
    def _apply_tutorial_progress(cls, context: dict[str, Any], event: dict[str, Any]) -> list[str]:
        if not event["success"]:
            return []
        event_type = event["type"]
        now = event["timestamp"]
        completed: list[str] = []
        if event_type in {"model_imported", "actor_created"}:
            if cls._complete_task_locked(context, "tutorial.import_model", now):
                completed.append("tutorial.import_model")
        if event_type in {"transform_position", "transform_rotation", "transform_scale"}:
            if cls._complete_task_locked(context, "tutorial.transform_model", now):
                completed.append("tutorial.transform_model")
        if event_type == "lighting_changed":
            if cls._complete_task_locked(context, "tutorial.adjust_lighting", now):
                completed.append("tutorial.adjust_lighting")
        if event_type == "physics_changed":
            if cls._complete_task_locked(context, "tutorial.adjust_physics", now):
                completed.append("tutorial.adjust_physics")
        if event_type == "node_created":
            if cls._complete_task_locked(context, "tutorial.create_node", now):
                completed.append("tutorial.create_node")
        if event_type == "node_moved":
            if cls._complete_task_locked(context, "tutorial.move_node", now):
                completed.append("tutorial.move_node")
        if event_type == "node_connected":
            source_node_id = str((event.get("details") or {}).get("sourceNodeId") or "")
            target_node_id = str((event.get("details") or {}).get("targetNodeId") or "")
            if source_node_id and target_node_id and source_node_id != target_node_id:
                if cls._complete_task_locked(context, "tutorial.connect_nodes", now):
                    completed.append("tutorial.connect_nodes")
        if event_type == "block_added":
            details = event.get("details") or {}
            if details.get("interaction") == "drag":
                if cls._complete_task_locked(context, "tutorial.drag_block", now):
                    completed.append("tutorial.drag_block")
            if details.get("workspaceRole") == "condition":
                if cls._complete_task_locked(context, "tutorial.set_transition_condition", now):
                    completed.append("tutorial.set_transition_condition")
        if event_type == "block_parameter_changed":
            if cls._complete_task_locked(context, "tutorial.edit_block_parameter", now):
                completed.append("tutorial.edit_block_parameter")
        if event_type in {"run_started", "run_succeeded"}:
            if cls._complete_task_locked(context, "tutorial.run_node_graph", now):
                completed.append("tutorial.run_node_graph")
        return completed

    def record_event(self, payload: Any) -> dict[str, Any]:
        try:
            event = self._normalize_event(payload)
            project_path = self._active_project_path()
            self._validate_payload_world(project_path, payload)
            with self._lock:
                context = self._read_locked(project_path)
                context["recentOperationEvents"].append(event)
                context["recentOperationEvents"] = context["recentOperationEvents"][-self.MAX_RECENT_EVENTS :]
                metric = self.METRIC_BY_EVENT.get(event["type"])
                if metric and event["success"]:
                    context["metrics"][metric] = int(context["metrics"].get(metric) or 0) + 1
                if event["type"] in self.IMPORTANT_EVENT_TYPES and event["success"]:
                    context["metrics"]["importantEventCount"] = int(context["metrics"].get("importantEventCount") or 0) + 1
                if not context["metrics"].get("firstActivityAt"):
                    context["metrics"]["firstActivityAt"] = event["timestamp"]
                context["metrics"]["lastActivityAt"] = event["timestamp"]
                completed = self._apply_tutorial_progress(context, event)
                self._ensure_tutorial_slots_locked(context, event["timestamp"])
                for task_key in completed:
                    context["recentOperationEvents"].append({
                        "eventId": f"event_{uuid.uuid4().hex}",
                        "type": "tutorial_completed",
                        "category": "assistant",
                        "success": True,
                        "timestamp": event["timestamp"],
                        "details": {"taskKey": task_key},
                    })
                self._write_locked(project_path, context)
                return {
                    "success": True,
                    "status": "ok",
                    "completedTaskKeys": completed,
                    "context": self._clone(context),
                }
        except ValueError as exc:
            return self._error("INVALID_CONTEXT_EVENT", str(exc))
        except Exception as exc:
            logger.warning("Unable to record Cabbage event: %s", exc)
            return self._error("CONTEXT_WRITE_FAILED", str(exc))

    @classmethod
    def _normalize_task(cls, payload: Any) -> tuple[str, dict[str, Any]]:
        if not isinstance(payload, dict):
            raise ValueError("包菜任务格式不正确")
        action = str(payload.get("action") or "upsert").strip()
        raw = payload.get("task") if isinstance(payload.get("task"), dict) else payload
        task_key = str(raw.get("taskKey") or raw.get("issueKey") or raw.get("code") or "").strip()[:180]
        if not task_key:
            raise ValueError("包菜任务缺少 taskKey")
        now = cls._now_ms()
        task = {
            "taskKey": task_key,
            "issueKey": task_key,
            "type": "tutorial" if raw.get("type") == "tutorial" else "node-issue",
            "track": str(raw.get("track") or "")[:40],
            "order": int(raw.get("order") or 0),
            "status": str(raw.get("status") or ("candidate" if action == "candidate" else "active"))[:40],
            "code": str(raw.get("code") or task_key)[:180],
            "severity": str(raw.get("severity") or "warning")[:40],
            "confidence": float(raw.get("confidence") or 0),
            "nodeId": str(raw.get("nodeId") or "")[:180],
            "blockId": str(raw.get("blockId") or "")[:180],
            "edgeId": str(raw.get("edgeId") or "")[:180],
            "pattern": cls._normalize_issue_pattern(raw.get("pattern")),
            "title": str(raw.get("title") or "节点逻辑需要调整").strip()[:160],
            "message": str(raw.get("message") or "").strip()[:1600],
            "suggestion": str(raw.get("suggestion") or "").strip()[:1600],
            "completionCriteria": str(raw.get("completionCriteria") or "").strip()[:800],
            "graphRevision": str(raw.get("graphRevision") or "")[:180],
            "createdAt": int(raw.get("createdAt") or now),
            "firstDetectedAt": int(raw.get("firstDetectedAt") or raw.get("createdAt") or now),
            "updatedAt": now,
            "completedAt": int(raw.get("completedAt") or 0),
            "resolvedAt": int(raw.get("resolvedAt") or 0),
        }
        return action, task

    @classmethod
    def _append_internal_event_locked(
        cls,
        context: dict[str, Any],
        event_type: str,
        *,
        task_key: str,
        timestamp: int,
    ) -> None:
        event = {
            "eventId": f"event_{uuid.uuid4().hex}",
            "type": event_type,
            "category": "node",
            "success": True,
            "timestamp": timestamp,
            "details": {"taskKey": task_key},
        }
        context["recentOperationEvents"].append(event)
        context["recentOperationEvents"] = context["recentOperationEvents"][-cls.MAX_RECENT_EVENTS :]
        context["metrics"]["importantEventCount"] = int(context["metrics"].get("importantEventCount") or 0) + 1
        if not context["metrics"].get("firstActivityAt"):
            context["metrics"]["firstActivityAt"] = timestamp
        context["metrics"]["lastActivityAt"] = timestamp

    def update_task(self, payload: Any) -> dict[str, Any]:
        try:
            action, incoming = self._normalize_task(payload)
            project_path = self._active_project_path()
            self._validate_payload_world(project_path, payload)
            now = self._now_ms()
            with self._lock:
                context = self._read_locked(project_path)
                existing = self._find_task(context, incoming["taskKey"])
                if action in {"complete", "resolve", "cancel"}:
                    if existing:
                        context["activeTasks"].remove(existing)
                        archived = dict(existing)
                        archived.update(incoming)
                        archived["status"] = {"complete": "completed", "resolve": "resolved", "cancel": "cancelled"}[action]
                        archived["updatedAt"] = now
                        if action == "complete":
                            archived["completedAt"] = now
                        else:
                            archived["resolvedAt"] = now
                        context["taskHistory"].append(archived)
                        if existing.get("type") == "tutorial":
                            self._ensure_tutorial_slots_locked(context, now)
                        if existing.get("type") == "node-issue" and action == "resolve":
                            context["metrics"]["nodeIssueFixes"] = int(context["metrics"].get("nodeIssueFixes") or 0) + 1
                            memory = self._issue_memory_entry_locked(context, str(existing.get("code") or incoming.get("code") or ""))
                            memory["resolvedCount"] = int(memory.get("resolvedCount") or 0) + 1
                            self._append_internal_event_locked(
                                context,
                                "node_issue_fixed",
                                task_key=incoming["taskKey"],
                                timestamp=now,
                            )
                    self._write_locked(project_path, context)
                    return {"success": True, "status": "ok", "context": self._clone(context)}

                if existing:
                    created_at = int(existing.get("createdAt") or incoming["createdAt"])
                    first_detected = int(existing.get("firstDetectedAt") or incoming["firstDetectedAt"])
                    existing.update(incoming)
                    existing["createdAt"] = created_at
                    existing["firstDetectedAt"] = first_detected
                    if incoming["type"] == "node-issue":
                        memory = self._issue_memory_entry_locked(context, incoming.get("code") or incoming["taskKey"])
                        memory["pattern"].update(incoming.get("pattern") or {})
                else:
                    if incoming["type"] == "node-issue":
                        # Update memory before inserting the task. When an older context has
                        # no issueMemory yet, normalization reconstructs it from existing
                        # tasks; inserting first would count this first occurrence twice.
                        context["metrics"]["nodeErrors"] = int(context["metrics"].get("nodeErrors") or 0) + 1
                        memory = self._issue_memory_entry_locked(context, incoming.get("code") or incoming["taskKey"])
                        memory["occurrences"] = int(memory.get("occurrences") or 0) + 1
                        memory["firstSeenAt"] = int(memory.get("firstSeenAt") or now)
                        memory["lastSeenAt"] = now
                        memory["pattern"].update(incoming.get("pattern") or {})
                        self._append_internal_event_locked(
                            context,
                            "node_issue_found",
                            task_key=incoming["taskKey"],
                            timestamp=now,
                        )
                    context["activeTasks"].append(incoming)
                self._write_locked(project_path, context)
                return {"success": True, "status": "ok", "context": self._clone(context)}
        except ValueError as exc:
            return self._error("INVALID_CONTEXT_TASK", str(exc))
        except Exception as exc:
            logger.warning("Unable to update Cabbage task: %s", exc)
            return self._error("CONTEXT_WRITE_FAILED", str(exc))

    def append_message(self, payload: Any) -> dict[str, Any]:
        try:
            if not isinstance(payload, dict):
                raise ValueError("包菜消息格式不正确")
            content = str(payload.get("content") or "").strip()[:12000]
            if not content:
                raise ValueError("包菜消息内容为空")
            message = {
                "id": str(payload.get("id") or f"cabbage_msg_{uuid.uuid4().hex}"),
                "role": "assistant" if payload.get("role") == "assistant" else "user",
                "content": content,
                "createdAt": int(payload.get("createdAt") or self._now_ms()),
                "taskKey": str(payload.get("taskKey") or "").strip()[:180],
                "issueCode": str(payload.get("issueCode") or "").strip()[:180],
                "nodeId": str(payload.get("nodeId") or "").strip()[:180],
                "blockId": str(payload.get("blockId") or "").strip()[:180],
                "needsShowcase": payload.get("needsShowcase") is True,
                "guidanceIntent": str(payload.get("guidanceIntent") or "").strip()[:80],
                "steps": [
                    str(step or "").strip()[:500]
                    for step in (payload.get("steps") if isinstance(payload.get("steps"), list) else [])[:8]
                    if str(step or "").strip()
                ],
            }
            if message["guidanceIntent"] not in self.CHAT_GUIDANCE_INTENTS:
                message["guidanceIntent"] = ""
                message["needsShowcase"] = False
            if not message["guidanceIntent"]:
                message["needsShowcase"] = False
            project_path = self._active_project_path()
            self._validate_payload_world(project_path, payload)
            with self._lock:
                context = self._read_locked(project_path)
                if not message["issueCode"] and message["taskKey"]:
                    related = self._find_task(context, message["taskKey"]) or next(
                        (task for task in reversed(context["taskHistory"])
                         if isinstance(task, dict) and task.get("taskKey") == message["taskKey"]),
                        None,
                    )
                    if related and related.get("type") == "node-issue":
                        message["issueCode"] = str(related.get("code") or "")[:180]
                        message["nodeId"] = message["nodeId"] or str(related.get("nodeId") or "")[:180]
                        message["blockId"] = message["blockId"] or str(related.get("blockId") or "")[:180]
                is_new = not any(item.get("id") == message["id"] for item in context["chatMessages"] if isinstance(item, dict))
                if is_new:
                    context["chatMessages"].append(message)
                    if message["role"] == "user" and message["issueCode"]:
                        memory = self._issue_memory_entry_locked(context, message["issueCode"])
                        memory["chatDiscussionCount"] = int(memory.get("chatDiscussionCount") or 0) + 1
                        memory["lastDiscussedAt"] = message["createdAt"]
                self._write_locked(project_path, context)
                return {
                    "success": True,
                    "status": "ok",
                    "message": message,
                    "context": self._clone(context),
                }
        except ValueError as exc:
            return self._error("INVALID_CONTEXT_MESSAGE", str(exc))
        except Exception as exc:
            logger.warning("Unable to append Cabbage message: %s", exc)
            return self._error("CONTEXT_WRITE_FAILED", str(exc))

    @staticmethod
    def _event_categories(context: dict[str, Any]) -> set[str]:
        categories: set[str] = set()
        metrics = context.get("metrics") or {}
        if metrics.get("modelImports") or metrics.get("transformEdits"):
            categories.add("scene")
        if metrics.get("lightingEdits"):
            categories.add("lighting")
        if metrics.get("physicsEdits"):
            categories.add("physics")
        if metrics.get("nodeEdits") or metrics.get("nodeErrors") or metrics.get("nodeIssueFixes"):
            categories.add("node")
        if metrics.get("runSuccesses") or metrics.get("runFailures"):
            categories.add("runtime")
        return categories

    @classmethod
    def _can_update_score(cls, context: dict[str, Any], force: bool) -> tuple[bool, str]:
        metrics = context.get("metrics") or {}
        event_count = int(metrics.get("importantEventCount") or 0)
        last_count = int((context.get("profile") or {}).get("lastScoredEventCount") or 0)
        last_at = int((context.get("profile") or {}).get("updatedAt") or 0)
        high_value = any(int(metrics.get(key) or 0) > 0 for key in ("nodeEdits", "nodeIssueFixes", "runSuccesses", "runFailures"))
        recent_high_value = any(
            isinstance(event, dict)
            and int(event.get("timestamp") or 0) > last_at
            and event.get("type") in {"node_edited", "node_created", "node_connected", "block_added",
                                      "block_parameter_changed", "node_issue_fixed", "run_succeeded", "run_failed"}
            for event in context.get("recentOperationEvents") or []
        )
        if not force:
            if event_count < 6 and not high_value:
                return False, "insufficient_evidence"
            if len(cls._event_categories(context)) < 2 and not high_value:
                return False, "insufficient_categories"
            if last_at and cls._now_ms() - last_at < cls.SCORE_MIN_INTERVAL_SECONDS * 1000:
                return False, "score_update_cooldown"
            if last_at and event_count <= last_count:
                return False, "no_material_change"
            if last_at and event_count - last_count < 5 and not recent_high_value:
                return False, "no_material_change"
        return True, ""

    @classmethod
    def _score_evidence(cls, context: dict[str, Any]) -> dict[str, Any]:
        task_durations: list[float] = []
        issue_durations: list[float] = []
        completed_tutorials = 0
        for task in context.get("taskHistory") or []:
            if not isinstance(task, dict):
                continue
            created_at = int(task.get("createdAt") or 0)
            if task.get("type") == "tutorial" and int(task.get("completedAt") or 0) > created_at > 0:
                completed_tutorials += 1
                task_durations.append((int(task["completedAt"]) - created_at) / 1000.0)
            if task.get("type") == "node-issue" and int(task.get("resolvedAt") or 0) > 0:
                detected_at = int(task.get("firstDetectedAt") or created_at or 0)
                if detected_at > 0:
                    issue_durations.append((int(task["resolvedAt"]) - detected_at) / 1000.0)
        recent_events = [item for item in (context.get("recentOperationEvents") or []) if isinstance(item, dict)]
        recent_window = recent_events[-60:]
        successful_events = sum(1 for item in recent_window if item.get("success") is not False)
        failed_events = sum(1 for item in recent_window if item.get("success") is False)
        recent_runs = [item for item in recent_window if item.get("type") in {"run_succeeded", "run_failed"}]
        repeated_issue_count = sum(
            1 for entry in (context.get("issueMemory") or {}).values()
            if isinstance(entry, dict) and int(entry.get("occurrences") or 0) >= 2
        )
        metrics = context.get("metrics") or {}
        runs = int(metrics.get("runSuccesses") or 0) + int(metrics.get("runFailures") or 0)
        return {
            "completedTutorials": completed_tutorials,
            "medianTutorialSeconds": round(sorted(task_durations)[len(task_durations) // 2], 1) if task_durations else None,
            "medianIssueFixSeconds": round(sorted(issue_durations)[len(issue_durations) // 2], 1) if issue_durations else None,
            "runSuccessRate": round(int(metrics.get("runSuccesses") or 0) / runs, 3) if runs else None,
            "nodeIssueResolutionRate": round(
                int(metrics.get("nodeIssueFixes") or 0) / max(1, int(metrics.get("nodeErrors") or 0)), 3
            ) if int(metrics.get("nodeErrors") or 0) else None,
            "recentOperationSuccessRate": round(successful_events / max(1, successful_events + failed_events), 3),
            "recentRunSuccessRate": round(
                sum(1 for item in recent_runs if item.get("type") == "run_succeeded") / len(recent_runs), 3
            ) if recent_runs else None,
            "recentFailedOperations": failed_events,
            "repeatedIssueKinds": repeated_issue_count,
            "operationCategoryCount": len(cls._event_categories(context)),
        }

    @classmethod
    def _score_prompt(cls, context: dict[str, Any]) -> str:
        current_profile = context.get("profile") or {}
        evidence = {
            "metrics": context.get("metrics") or {},
            "scoreEvidence": cls._score_evidence(context),
            "tutorialTasks": [
                {
                    "title": task.get("title"),
                    "status": task.get("status"),
                    "completedAt": task.get("completedAt", 0),
                    "createdAt": task.get("createdAt", 0),
                }
                for task in (context.get("activeTasks") or []) + (context.get("taskHistory") or [])
                if isinstance(task, dict) and task.get("type") == "tutorial"
            ],
            "recentEvents": (context.get("recentOperationEvents") or [])[-60:],
            "issueMemory": context.get("issueMemory") or {},
            "profileHistory": (context.get("profileHistory") or [])[-8:],
            "currentScore": current_profile.get("score", 0),
        }
        return (
            "请根据 CoronaEngine 当前世界的操作证据，评估用户当前操作流畅度，给出 0 到 100 的连续分数。"
            "不判断用户是美术还是程序，不输出入门、熟悉或熟练等档位。"
            "分数必须可随后续表现上升或下降：近期任务完成更快、操作成功率提高、节点问题修复更快、运行更稳定时应提分；"
            "重复出现相同错误、运行失败增多、修复变慢或有效操作成功率下降时应降分。"
            "早期表现不能锁死后续分数，优先参考近期证据。"
            "只返回 JSON："
            '{"score":0,"reasonCodes":["short_reason_code"]}'
            "。score 必须是 0 到 100 的数字，reasonCodes 使用简短稳定代码。\n证据："
            + json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
        )

    def start_score_update(self, payload: Any = None) -> dict[str, Any]:
        force = bool(payload.get("force")) if isinstance(payload, dict) else False
        try:
            project_path = self._active_project_path()
            with self._lock:
                context = self._read_locked(project_path)
                allowed, reason = self._can_update_score(context, force)
                if not allowed:
                    return {"success": True, "status": "skipped", "reason": reason, "profile": self._clone(context["profile"])}
                for state in self._score_tasks.values():
                    if state.get("status") == "running" and state.get("projectPath") == str(project_path):
                        return {"success": True, "status": "pending", "taskId": state["taskId"]}
                task_id = f"cabbage_profile_{uuid.uuid4().hex}"
                state = {
                    "taskId": task_id,
                    "status": "running",
                    "projectPath": str(project_path),
                    "createdAt": time.time(),
                    "result": None,
                }
                self._score_tasks[task_id] = state
                future = self._executor.submit(self._compute_score, project_path, self._clone(context))
                future.add_done_callback(lambda done, key=task_id: self._complete_score_update(key, done))
                self._prune_score_tasks_locked()
                return {"success": True, "status": "pending", "taskId": task_id}
        except Exception as exc:
            logger.warning("Unable to start Cabbage assistance score update: %s", exc)
            return self._error("PROFILE_SCORE_FAILED", str(exc))

    def _compute_score(self, project_path: Path, context: dict[str, Any]) -> dict[str, Any]:
        settings = NodeGraphReviewService._resolve_settings()
        if not settings.api_key:
            return self._error("AI_NOT_CONFIGURED", "DeepSeek 未配置，暂时无法更新操作评分。")
        raw = NodeGraphReviewService._call_deepseek(settings, self._score_prompt(context))
        value = NodeGraphReviewService._parse_model_result(raw)
        raw_score = value.get("score", value.get("fluencyScore"))
        try:
            model_score = max(0, min(int(round(float(raw_score))), 100))
        except (TypeError, ValueError):
            raise ValueError("DeepSeek 返回的操作评分无效")
        reason_codes = [str(item)[:80] for item in (value.get("reasonCodes") or []) if str(item).strip()][:12]

        with self._lock:
            latest = self._read_locked(project_path)
            current = latest.get("profile") or {}
            has_previous_score = int(current.get("updatedAt") or 0) > 0
            current_score = max(0, min(int(current.get("score", current.get("fluencyScore", 0)) or 0), 100))
            accepted_score = (
                int(round(current_score * 0.35 + model_score * 0.65))
                if has_previous_score
                else model_score
            )
            now = self._now_ms()
            if has_previous_score:
                latest["profileHistory"].append({
                    "score": current_score,
                    "updatedAt": int(current.get("updatedAt") or 0),
                    "reasonCodes": list(current.get("reasonCodes") or [])[:12],
                })
                latest["profileHistory"] = latest["profileHistory"][-self.MAX_PROFILE_HISTORY :]
            profile = {
                "score": accepted_score,
                "source": "deepseek",
                "updatedAt": now,
                "reasonCodes": reason_codes,
                "lastScoredEventCount": int((latest.get("metrics") or {}).get("importantEventCount") or 0),
            }
            latest["profile"] = profile
            self._write_locked(project_path, latest)
        return {"success": True, "status": "ok", "profile": profile}

    def _complete_score_update(self, task_id: str, future: Any) -> None:
        try:
            result = future.result()
        except Exception as exc:
            logger.warning("Cabbage assistance score update failed: %s", exc)
            result = self._error("PROFILE_SCORE_FAILED", "操作评分更新暂时不可用。")
        with self._lock:
            state = self._score_tasks.get(task_id)
            if state:
                state["status"] = "completed"
                state["result"] = result
                state["completedAt"] = time.time()

    def score_update_status(self, task_id: Any) -> dict[str, Any]:
        key = str(task_id or "")
        with self._lock:
            state = self._score_tasks.get(key)
            if not state:
                return self._error("PROFILE_SCORE_TASK_NOT_FOUND", "没有找到操作评分更新任务。")
            response = {"success": True, "status": state["status"], "taskId": key}
            if state["status"] == "completed":
                response["result"] = self._clone(state.get("result") or {})
            return response

    def _prune_score_tasks_locked(self) -> None:
        if len(self._score_tasks) <= self.MAX_SCORE_TASKS:
            return
        completed = sorted(
            (state for state in self._score_tasks.values() if state.get("status") == "completed"),
            key=lambda item: float(item.get("completedAt") or item.get("createdAt") or 0),
        )
        for state in completed[: max(0, len(self._score_tasks) - self.MAX_SCORE_TASKS)]:
            self._score_tasks.pop(state["taskId"], None)

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)


_service: CabbageContextService | None = None


def get_cabbage_context_service() -> CabbageContextService:
    global _service
    if _service is None:
        _service = CabbageContextService()
    return _service
