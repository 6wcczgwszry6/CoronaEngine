"""World-scoped persistence, guidance tasks, and adaptive assistance scoring."""

from __future__ import annotations

import configparser
import json
import logging
import os
import socket
import shutil
import threading
import time
import urllib.error
import urllib.request
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
    MAX_GOAL_PLAN_TASKS = 24
    GOAL_VISIBLE_TASKS = 2
    GOAL_PLAN_TIMEOUT_SECONDS = 45
    SCORE_MIN_INTERVAL_SECONDS = 300
    GOAL_COMPLETION_SIGNALS = {
        "model_imported",
        "object_transformed",
        "lighting_adjusted",
        "physics_adjusted",
        "node_created",
        "node_moved",
        "nodes_connected",
        "block_added",
        "block_parameter_changed",
        "transition_condition_set",
        "node_graph_run",
        "run_succeeded",
    }
    GOAL_NODE_SIGNALS = {
        "node_created",
        "node_moved",
        "nodes_connected",
        "block_added",
        "block_parameter_changed",
        "transition_condition_set",
        "node_graph_run",
        "run_succeeded",
    }
    GOAL_SCENE_SIGNALS = {
        "model_imported",
        "object_transformed",
        "lighting_adjusted",
        "physics_adjusted",
    }
    GOAL_PHASES = {"node-logic", "scene-polish"}
    MIN_GOAL_NODE_TASKS = 5
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
        "goal_task_completed",
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
        "node_moved": "nodeEdits",
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
            "titleEn": "Import an Object",
            "message": "先把一个模型加入当前世界，后续才能练习摆放和属性调整。",
            "messageEn": "Add a model to the current world first so you can practice placement and property adjustments.",
            "suggestion": "打开场景管理，使用导入或添加模型功能，把一个模型放入场景。",
            "suggestionEn": "Open Scene Manager and use Import or Add Model to place a model in the scene.",
            "completionCriteria": "成功导入模型，或场景中新建一个模型对象。",
            "completionCriteriaEn": "A model is imported successfully or a new model object appears in the scene.",
        },
        {
            "taskKey": "tutorial.transform_model",
            "type": "tutorial",
            "track": "scene",
            "order": 2,
            "title": "调整一个物体",
            "titleEn": "Adjust an Object",
            "message": "修改模型的变换参数，观察它在场景中的位置、朝向或大小变化。",
            "messageEn": "Edit a model transform and observe changes to its position, orientation, or size.",
            "suggestion": "选中一个模型，在对象 Dock 的“变换”区域修改位置、旋转或缩放中的任意参数。",
            "suggestionEn": "Select a model and change any Position, Rotation, or Scale value in the Transform section of the Object dock.",
            "completionCriteria": "成功保存一次位置、旋转或缩放修改。",
            "completionCriteriaEn": "A position, rotation, or scale change is saved successfully.",
        },
        {
            "taskKey": "tutorial.adjust_lighting",
            "type": "tutorial",
            "track": "scene",
            "order": 3,
            "title": "调整场景光照",
            "titleEn": "Adjust Scene Lighting",
            "message": "尝试改变光照状态或方向，观察模型明暗和场景氛围的变化。",
            "messageEn": "Change the lighting state or direction and observe the model shading and scene atmosphere.",
            "suggestion": "在场景管理中切换光照，或调整光照方向后确认效果。",
            "suggestionEn": "Toggle lighting in Scene Manager or adjust its direction, then confirm the result.",
            "completionCriteria": "成功修改光照启用状态或光照方向。",
            "completionCriteriaEn": "The lighting enabled state or direction is changed successfully.",
        },
        {
            "taskKey": "tutorial.adjust_physics",
            "type": "tutorial",
            "track": "scene",
            "order": 4,
            "title": "调整物理属性",
            "titleEn": "Adjust Physics Properties",
            "message": "给模型设置物理效果，让它能够参与重力、碰撞或反弹。",
            "messageEn": "Configure physics so the model can respond to gravity, collisions, or bouncing.",
            "suggestion": "选中一个模型，启用物理或修改质量、弹性、阻尼、锁轴中的任意一项。",
            "suggestionEn": "Select a model, then enable physics or change mass, restitution, damping, or an axis lock.",
            "completionCriteria": "成功修改一次模型物理属性。",
            "completionCriteriaEn": "A model physics property is changed successfully.",
        },
        {
            "taskKey": "tutorial.create_node",
            "type": "tutorial",
            "track": "node",
            "order": 1,
            "title": "创建一个节点",
            "titleEn": "Create a Node",
            "message": "先建立一个新的状态节点，为后续的积木逻辑和流程跳转准备容器。",
            "messageEn": "Create a new state node as a container for later block logic and flow transitions.",
            "suggestion": "在节点 Dock 中拖入一个状态节点，并把它放到画布中。",
            "suggestionEn": "Drag a state node from the Nodes dock onto the canvas.",
            "completionCriteria": "成功创建一个新的状态节点。",
            "completionCriteriaEn": "A new state node is created successfully.",
        },
        {
            "taskKey": "tutorial.move_node",
            "type": "tutorial",
            "track": "node",
            "order": 2,
            "title": "拖拽一个节点",
            "titleEn": "Move a Node",
            "message": "整理节点位置，让状态流程更容易阅读和连接。",
            "messageEn": "Rearrange a node so the state flow is easier to read and connect.",
            "suggestion": "在节点 Dock 的画布中拖动任意节点，并把它放到新的位置。",
            "suggestionEn": "Drag any node on the Nodes dock canvas and place it at a new position.",
            "completionCriteria": "节点位置产生一次有效变化。",
            "completionCriteriaEn": "A node position changes successfully.",
        },
        {
            "taskKey": "tutorial.connect_nodes",
            "type": "tutorial",
            "track": "node",
            "order": 3,
            "title": "连接两个节点",
            "titleEn": "Connect Two Nodes",
            "message": "建立两个不同状态之间的跳转路径，让流程能够从一个节点进入另一个节点。",
            "messageEn": "Create a transition path between two states so the flow can move from one node to another.",
            "suggestion": "依次点击两个不同节点的端口，创建一条有效连线。",
            "suggestionEn": "Connect the ports of two different nodes to create a valid edge.",
            "completionCriteria": "两个不同节点之间成功新增一条连线。",
            "completionCriteriaEn": "A new connection is created successfully between two different nodes.",
        },
        {
            "taskKey": "tutorial.drag_block",
            "type": "tutorial",
            "track": "node",
            "order": 4,
            "title": "向节点拖入一个积木",
            "titleEn": "Drag a Block into a Node",
            "message": "把一个积木放进节点工作区，开始为当前状态添加实际行为。",
            "messageEn": "Place a block in the node workspace to add behavior to the current state.",
            "suggestion": "从左侧积木列表拖动一个积木，并放入当前节点的积木区域。",
            "suggestionEn": "Drag a block from the left toolbox into the current node block area.",
            "completionCriteria": "通过拖拽方式成功创建一个积木。",
            "completionCriteriaEn": "A block is created successfully by dragging it into the workspace.",
        },
        {
            "taskKey": "tutorial.edit_block_parameter",
            "type": "tutorial",
            "track": "node",
            "order": 5,
            "title": "修改一个积木参数",
            "titleEn": "Edit a Block Parameter",
            "message": "调整积木字段，让同一个功能使用你需要的按键、数值、对象或条件。",
            "messageEn": "Edit a block field to use the key, value, object, or condition you need.",
            "suggestion": "修改任意积木中的下拉项、文本或数值字段。",
            "suggestionEn": "Change a dropdown, text, or numeric field in any block.",
            "completionCriteria": "积木的一个字段值发生有效变化。",
            "completionCriteriaEn": "A block field value changes successfully.",
        },
        {
            "taskKey": "tutorial.set_transition_condition",
            "type": "tutorial",
            "track": "node",
            "order": 6,
            "title": "设置一个跳转条件",
            "titleEn": "Set a Transition Condition",
            "message": "给节点连线添加 Boolean 条件，控制流程在什么情况下进入下一个状态。",
            "messageEn": "Add a Boolean condition to a node connection to control when the flow enters the next state.",
            "suggestion": "选中一条节点连线，在条件工作区放入能够返回 Boolean 的积木。",
            "suggestionEn": "Select a node connection and place a Boolean-returning block in the condition workspace.",
            "completionCriteria": "跳转条件工作区成功加入一个条件积木。",
            "completionCriteriaEn": "A condition block is added successfully to the transition condition workspace.",
        },
        {
            "taskKey": "tutorial.run_node_graph",
            "type": "tutorial",
            "track": "node",
            "order": 7,
            "title": "运行一次节点逻辑",
            "titleEn": "Run the Node Logic",
            "message": "点击运行当前节点图，开始验证节点、连线和积木的执行效果。",
            "messageEn": "Run the current node graph to verify how its nodes, connections, and blocks execute.",
            "suggestion": "直接点击节点 Dock 中的运行按钮；节点会实时保存，不需要额外执行保存操作。",
            "suggestionEn": "Click Run in the Nodes dock. The graph saves automatically, so no separate save action is required.",
            "completionCriteria": "节点逻辑成功发起一次运行。",
            "completionCriteriaEn": "The node logic starts running successfully.",
        },
    )
    RETIRED_TUTORIAL_TASK_KEYS = {"tutorial.rotate_model"}

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="CabbageAssistant")
        self._score_tasks: dict[str, dict[str, Any]] = {}
        self._goal_plan_tasks: dict[str, dict[str, Any]] = {}
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
    def _project_goal_metadata(project_path: Path) -> tuple[str, str]:
        project_file = project_path / "project.ini"
        if not project_file.is_file():
            return "", "story"
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(project_file, encoding="utf-8-sig")
            section = parser["Project"] if parser.has_section("Project") else parser.defaults()
            prompt = str(section.get("world_prompt") or section.get("prompt") or "").strip()[:4000]
            mode = str(section.get("mode") or "story").strip().lower()
        except Exception:
            logger.debug("Unable to read world prompt from project.ini: %s", project_file, exc_info=True)
            return "", "story"
        if mode not in {"story", "creative"}:
            mode = "story"
        return prompt, mode

    @staticmethod
    def _needs_project_goal_plan(context: dict[str, Any], prompt: str, mode: str) -> bool:
        if not prompt:
            return False
        goal = context.get("worldGoal") if isinstance(context.get("worldGoal"), dict) else {}
        same_goal = (
            str(goal.get("prompt") or "").strip() == prompt
            and str(goal.get("mode") or "story").strip().lower() == mode
            and goal.get("source") == "ai"
        )
        if not same_goal:
            return True
        has_goal_plan = any(
            isinstance(task, dict) and task.get("type") == "goal"
            for task in [*(context.get("activeTasks") or []), *(context.get("taskHistory") or [])]
        )
        return goal.get("status") == "ready" and not has_goal_plan

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

    @staticmethod
    def _custom_goal_enabled(context: dict[str, Any]) -> bool:
        goal = context.get("worldGoal") if isinstance(context.get("worldGoal"), dict) else {}
        if (not str(goal.get("prompt") or "").strip()
                or goal.get("source") != "ai"
                or goal.get("status") != "ready"):
            return False
        return any(
            isinstance(task, dict) and task.get("type") == "goal"
            for task in [*(context.get("activeTasks") or []), *(context.get("taskHistory") or [])]
        )

    @classmethod
    def _ensure_goal_slots_locked(cls, context: dict[str, Any], now: int) -> None:
        history_keys = {
            str(task.get("taskKey") or "")
            for task in context.get("taskHistory") or []
            if isinstance(task, dict) and task.get("type") == "goal"
        }
        normalized: list[dict[str, Any]] = []
        for raw in context.get("activeTasks") or []:
            if not isinstance(raw, dict):
                continue
            if raw.get("type") != "goal":
                normalized.append(raw)
                continue
            task_key = str(raw.get("taskKey") or "")
            if not task_key or task_key in history_keys:
                continue
            task = dict(raw)
            task["status"] = str(task.get("status") or "queued")
            normalized.append(task)
        context["activeTasks"] = normalized

        goal_tasks = sorted(
            (task for task in normalized if task.get("type") == "goal"),
            key=lambda task: int(task.get("order") or 0),
        )
        visible = [task for task in goal_tasks if task.get("status") in {"active", "pending"}]
        selected_keys = {str(task.get("taskKey") or "") for task in visible[: cls.GOAL_VISIBLE_TASKS]}
        if len(selected_keys) < cls.GOAL_VISIBLE_TASKS:
            for task in goal_tasks:
                key = str(task.get("taskKey") or "")
                if key in selected_keys:
                    continue
                selected_keys.add(key)
                if len(selected_keys) >= cls.GOAL_VISIBLE_TASKS:
                    break
        for task in goal_tasks:
            next_status = "active" if str(task.get("taskKey") or "") in selected_keys else "queued"
            if task.get("status") != next_status:
                task["status"] = next_status
                task["updatedAt"] = now

    @classmethod
    def _ensure_task_slots_locked(cls, context: dict[str, Any], now: int) -> None:
        if cls._custom_goal_enabled(context):
            context["activeTasks"] = [
                task for task in context.get("activeTasks") or []
                if not isinstance(task, dict) or task.get("type") != "tutorial"
            ]
            cls._ensure_goal_slots_locked(context, now)
            return
        context["activeTasks"] = [
            task for task in context.get("activeTasks") or []
            if not isinstance(task, dict) or task.get("type") != "goal"
        ]
        cls._ensure_tutorial_slots_locked(context, now)

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
                "titleEn": template["titleEn"],
                "message": template["message"],
                "messageEn": template["messageEn"],
                "suggestion": template["suggestion"],
                "suggestionEn": template["suggestionEn"],
                "completionCriteria": template["completionCriteria"],
                "completionCriteriaEn": template["completionCriteriaEn"],
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
            "worldGoal": {
                "prompt": "",
                "mode": "story",
                "source": "default",
                "status": "ready",
                "generatedAt": 0,
                "generationError": "",
                "generationId": "",
            },
            "goalTaskPlan": {
                "schemaVersion": 2,
                "generatedAt": 0,
                "taskCount": 0,
                "nodeTaskCount": 0,
                "sceneTaskCount": 0,
                "logicBlueprint": {},
            },
            "goalSignalCounts": {},
            "activeTasks": [],
            "taskHistory": [],
            "chatMessages": [],
            "recentOperationEvents": [],
            "updatedAt": now,
        }
        cls._ensure_task_slots_locked(context, now)
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
        for key in ("metrics", "tutorialProgress", "worldGoal", "goalTaskPlan"):
            merged = dict(default[key])
            if isinstance(value.get(key), dict):
                merged.update(value[key])
            value[key] = merged
        if not isinstance(value.get("goalSignalCounts"), dict):
            value["goalSignalCounts"] = {}
        value["goalSignalCounts"] = {
            str(key)[:80]: max(0, int(count or 0))
            for key, count in value["goalSignalCounts"].items()
            if str(key) in cls.GOAL_COMPLETION_SIGNALS
        }
        for key in ("profileHistory", "activeTasks", "taskHistory", "chatMessages", "recentOperationEvents"):
            if not isinstance(value.get(key), list):
                value[key] = []
        if not isinstance(value.get("issueMemory"), dict):
            value["issueMemory"] = {}
        now = cls._now_ms()
        cls._ensure_task_slots_locked(value, now)
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

    def load(self, payload: Any = None) -> dict[str, Any]:
        try:
            project_path = self._active_project_path()
            self._validate_payload_world(project_path, payload)
            project_prompt, project_mode = self._project_goal_metadata(project_path)
            with self._lock:
                context = self._read_locked(project_path)
                should_start_goal_plan = self._needs_project_goal_plan(
                    context, project_prompt, project_mode,
                )
                self._write_locked(project_path, context)

            goal_plan = None
            if should_start_goal_plan:
                # The creation page can disappear immediately after opening the world.
                # Recover from its missed/raced request by treating project.ini as the
                # durable source of the original world description.
                goal_plan = self.start_goal_plan({
                    "worldId": project_path.name,
                    "prompt": project_prompt,
                    "mode": project_mode,
                })
                with self._lock:
                    context = self._read_locked(project_path)

            response = {"success": True, "status": "ok", "context": self._clone(context)}
            if goal_plan is not None:
                response["goalPlan"] = self._clone(goal_plan)
            return response
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

    @classmethod
    def _goal_signals_for_event(cls, event: dict[str, Any]) -> set[str]:
        if not event.get("success"):
            return set()
        event_type = str(event.get("type") or "")
        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        signals: set[str] = set()
        if event_type in {"model_imported", "actor_created"}:
            signals.add("model_imported")
        if event_type in {"transform_position", "transform_rotation", "transform_scale"}:
            signals.add("object_transformed")
        if event_type == "lighting_changed":
            signals.add("lighting_adjusted")
        if event_type == "physics_changed":
            signals.add("physics_adjusted")
        if event_type == "node_created":
            signals.add("node_created")
        if event_type == "node_moved":
            signals.add("node_moved")
        if event_type == "node_connected":
            source = str(details.get("sourceNodeId") or "")
            target = str(details.get("targetNodeId") or "")
            if source and target and source != target:
                signals.add("nodes_connected")
        if event_type == "block_added":
            signals.add("block_added")
            if details.get("workspaceRole") == "condition":
                signals.add("transition_condition_set")
        if event_type == "block_parameter_changed":
            signals.add("block_parameter_changed")
        if event_type in {"run_started", "run_succeeded"}:
            signals.add("node_graph_run")
        if event_type == "run_succeeded":
            signals.add("run_succeeded")
        return signals

    @classmethod
    def _apply_goal_progress(cls, context: dict[str, Any], event: dict[str, Any]) -> list[str]:
        signals = cls._goal_signals_for_event(event)
        if not signals:
            return []
        counts = context.setdefault("goalSignalCounts", {})
        for signal in signals:
            counts[signal] = int(counts.get(signal) or 0) + 1

        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        block_type = str(details.get("blockType") or "").strip()
        now = int(event.get("timestamp") or cls._now_ms())
        completed: list[str] = []
        for task in list(context.get("activeTasks") or []):
            if not isinstance(task, dict) or task.get("type") != "goal":
                continue
            if task.get("status") not in {"active", "pending"}:
                continue
            signal = str(task.get("completionSignal") or "")
            if signal not in signals:
                continue

            required_block_types = {
                str(item).strip()
                for item in task.get("requiredBlockTypes") or []
                if str(item).strip()
            }
            if required_block_types:
                if not block_type or block_type not in required_block_types:
                    continue
                observed = {
                    str(item).strip()
                    for item in task.get("observedBlockTypes") or []
                    if str(item).strip()
                }
                observed.add(block_type)
                task["observedBlockTypes"] = sorted(observed)
                task["updatedAt"] = now
                if not required_block_types.issubset(observed):
                    continue
            else:
                required = max(1, int(task.get("requiredCount") or 1))
                if int(counts.get(signal) or 0) < required:
                    continue

            task_key = str(task.get("taskKey") or "")
            if task_key and cls._complete_task_locked(context, task_key, now):
                completed.append(task_key)
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
                completed.extend(self._apply_goal_progress(context, event))
                self._ensure_task_slots_locked(context, event["timestamp"])
                for task_key in completed:
                    completed_task = next(
                        (
                            task for task in reversed(context["taskHistory"])
                            if isinstance(task, dict) and task.get("taskKey") == task_key
                        ),
                        {},
                    )
                    completed_type = str(completed_task.get("type") or "")
                    completion_event_type = (
                        "goal_task_completed" if completed_type == "goal" else "tutorial_completed"
                    )
                    context["recentOperationEvents"].append({
                        "eventId": f"event_{uuid.uuid4().hex}",
                        "type": completion_event_type,
                        "category": "assistant",
                        "success": True,
                        "timestamp": event["timestamp"],
                        "details": {"taskKey": task_key, "taskType": completed_type},
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
        raw_type = str(raw.get("type") or "node-issue")
        task_type = raw_type if raw_type in {"tutorial", "goal", "node-issue"} else "node-issue"

        def english_field(name: str, source_name: str, fallback: str = "") -> str:
            english = str(raw.get(name) or "").strip()
            source = str(raw.get(source_name) or "").strip()
            if not english:
                return fallback
            if english == source and any("\u3400" <= char <= "\u9fff" for char in english):
                return fallback
            return english
        task = {
            "taskKey": task_key,
            "issueKey": task_key,
            "type": task_type,
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
            "titleEn": english_field(
                "titleEn",
                "title",
                "Node Logic Needs Adjustment" if not raw.get("title") and task_type == "node-issue" else "",
            )[:160],
            "message": str(raw.get("message") or "").strip()[:1600],
            "messageEn": english_field("messageEn", "message")[:1600],
            "suggestion": str(raw.get("suggestion") or "").strip()[:1600],
            "suggestionEn": english_field("suggestionEn", "suggestion")[:1600],
            "completionCriteria": str(raw.get("completionCriteria") or "").strip()[:800],
            "completionCriteriaEn": english_field("completionCriteriaEn", "completionCriteria")[:800],
            "completionSignal": str(raw.get("completionSignal") or "").strip()[:80],
            "requiredCount": max(1, int(raw.get("requiredCount") or 1)),
            "phase": str(raw.get("phase") or "").strip()[:40],
            "effectId": str(raw.get("effectId") or "").strip()[:120],
            "requiredBlockTypes": [
                str(item).strip()[:180]
                for item in (raw.get("requiredBlockTypes") or [])
                if str(item).strip()
            ][:20],
            "observedBlockTypes": [
                str(item).strip()[:180]
                for item in (raw.get("observedBlockTypes") or [])
                if str(item).strip()
            ][:20],
            "guidanceIntent": str(raw.get("guidanceIntent") or "").strip()[:80],
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
                        if existing.get("type") in {"tutorial", "goal"}:
                            self._ensure_task_slots_locked(context, now)
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

    @classmethod
    def _goal_block_catalog(cls) -> list[dict[str, str]]:
        catalog = NodeGraphReviewService._catalog_index()
        return [
            {
                "type": str(item.get("type") or ""),
                "category": str(item.get("category") or ""),
                "label": str(item.get("label") or ""),
                "shape": str(item.get("shape") or ""),
                "outputCheck": str(item.get("outputCheck") or ""),
                "projectUsage": str(item.get("projectUsage") or ""),
            }
            for item in catalog.values()
            if item.get("type") and item.get("projectUsage") == "project-safe"
        ]

    @classmethod
    def _goal_plan_prompt(cls, world_prompt: str, mode: str) -> str:
        capabilities = {
            "model_imported": "导入一个模型或在场景中新建模型对象",
            "object_transformed": "修改一个对象的位置、旋转或缩放",
            "lighting_adjusted": "修改场景光照开关或光照方向",
            "physics_adjusted": "修改一个对象的物理、碰撞、质量、弹性或阻尼",
            "node_created": "创建一个节点",
            "node_moved": "拖动一个节点",
            "nodes_connected": "连接两个不同节点",
            "block_added": "向节点内加入指定类型的积木",
            "block_parameter_changed": "修改指定类型积木的参数",
            "transition_condition_set": "为节点连线设置一个 Boolean 条件",
            "node_graph_run": "发起一次节点逻辑运行",
            "run_succeeded": "节点逻辑成功运行",
        }
        schema = {
            "logicBlueprint": {
                "worldSummary": "",
                "coreLoop": "",
                "requiredActors": [],
                "nodeEffects": [
                    {
                        "effectId": "effect_01",
                        "title": "",
                        "description": "",
                        "trigger": "",
                        "outcome": "",
                        "recommendedBlockTypes": [],
                        "verification": "",
                    }
                ],
                "flow": [],
            },
            "tasks": [
                {
                    "phase": "node-logic",
                    "effectId": "effect_01",
                    "title": "",
                    "titleEn": "",
                    "message": "",
                    "messageEn": "",
                    "suggestion": "",
                    "suggestionEn": "",
                    "completionCriteria": "",
                    "completionCriteriaEn": "",
                    "completionSignal": "block_added",
                    "requiredBlockTypes": [],
                }
            ],
        }
        request_context = {
            "mode": mode,
            "description": world_prompt,
        }
        return (
            "你是 CoronaEngine 3D 游戏编辑器的世界搭建任务规划器。"
            "用户的 description 可以是任意语言、任意题材、任意详细程度的自然语言，必须把它作为本次规划唯一的世界语义来源。"
            "只分析 description 中实际出现或能够直接推导出的场景、对象、体验、交互和目标，形成 logicBlueprint。"
            "如果描述偏抽象、偏氛围或没有明确玩法，就把其中的视觉与体验目标拆成当前引擎能够验证的场景任务和最小交互任务；"
            "不得擅自加入 description 未包含且不能直接推导出的具体角色、道具、机关、运动方式、交互、战斗、胜负条件或其他固定玩法。"
            "不得使用固定题材模板或按关键词套用预制任务，也不得照抄返回结构模板中的 effect_01。"
            "logicBlueprint 只是理解世界目标的内部分析，不是节点图、不是积木 JSON，也不能直接修改当前节点区。"
            "最终产物只能是一套与当前 description 强相关的个性化搭建任务，由任务一步一步引导用户亲自完成世界。"
            "生成 6 到 10 个循序渐进的任务。目标是先让当前世界所需的节点玩法逻辑成立，再完成必要的场景内容和表现，而不是替用户生成一套节点积木。"
            "至少 5 个任务必须是 phase=node-logic，并且所有 node-logic 任务必须排在 scene-polish 前。"
            "每个任务只能对应一个可由 completionSignal 验证的操作目标；不要把光照和物理、导入和变换等不同完成信号合并在同一个任务中。"
            "每个任务的 title、message、suggestion、completionCriteria 必须使用简体中文，"
            "并同时提供语义一致、自然简洁的英文 titleEn、messageEn、suggestionEn、completionCriteriaEn。"
            "如果一个玩法效果需要多个积木，可以在同一个积木任务的 requiredBlockTypes 中列出，但标题、说明和完成条件必须与该单一任务目标一致。"
            "节点任务必须围绕当前 description 真正需要的效果组织；能力目录中的输入、移动、碰撞等只代表可选能力，不是必须加入世界的内容。"
            "禁止使用‘随便创建节点’‘任意拖入积木’这类脱离世界目标的通用教程。"
            "最后一个 node-logic 任务必须使用 run_succeeded，确认前面的玩法节点能够成功运行。"
            "scene-polish 只能放在节点逻辑验证之后，用于当前 description 确实需要的模型、变换、光照或物理准备。"
            "requiredActors 可以填写角色、普通物体、场景区域或系统，但只能来自当前 description 的需求。"
            "nodeEffects.recommendedBlockTypes 与 tasks.requiredBlockTypes 只能从下方 XML 积木目录选择，必须使用精确 type，不能编造。"
            "completionSignal 为 block_added 或 block_parameter_changed 时必须给出 requiredBlockTypes；其他完成信号不要填写该数组。"
            "每个任务只使用一个 completionSignal。不要输出 Python、脚本、XML 或 Markdown，只输出合法 JSON。\n"
            "返回结构模板（仅表示字段结构，空数组必须按当前 description 补全，示例标识不能照抄）："
            + json.dumps(schema, ensure_ascii=False, separators=(",", ":")) + "\n"
            "本次用户输入数据："
            + json.dumps(request_context, ensure_ascii=False, separators=(",", ":")) + "\n"
            "可用完成信号：" + json.dumps(capabilities, ensure_ascii=False, separators=(",", ":")) + "\n"
            "可用的项目级积木目录：" + json.dumps(cls._goal_block_catalog(), ensure_ascii=False, separators=(",", ":"))
        )

    @classmethod
    def _call_deepseek_for_goal_plan(cls, world_prompt: str, mode: str) -> dict[str, Any]:
        settings = NodeGraphReviewService._resolve_settings()
        if not settings.api_key:
            raise ValueError("DeepSeek API Key 未配置，无法生成世界任务")
        base = settings.base_url.rstrip("/")
        endpoint = base if base.endswith("/chat/completions") else base + "/chat/completions"
        body = {
            "model": settings.model,
            "temperature": 0.25,
            "max_tokens": 3600,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "messages": [
                {
                    "role": "system",
                    "content": "你只负责为 CoronaEngine 生成结构化的个性化世界搭建任务，绝不生成或修改节点图、积木工作区和脚本，必须返回合法 JSON。",
                },
                {"role": "user", "content": cls._goal_plan_prompt(world_prompt, mode)},
            ],
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + settings.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=cls.GOAL_PLAN_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        choices = payload.get("choices") if isinstance(payload, dict) else None
        message = choices[0].get("message") if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("DeepSeek 没有返回世界任务")
        return NodeGraphReviewService._parse_model_result(content)

    @classmethod
    def _normalize_block_type_list(cls, raw: Any, *, field_name: str) -> list[str]:
        if raw in (None, ""):
            return []
        if not isinstance(raw, list):
            raise ValueError(f"DeepSeek 世界任务中的 {field_name} 必须是数组")
        catalog = NodeGraphReviewService._catalog_index()
        normalized: list[str] = []
        for item in raw:
            block_type = str(item or "").strip()[:180]
            if not block_type or block_type in normalized:
                continue
            block = catalog.get(block_type)
            if not block or block.get("projectUsage") != "project-safe":
                raise ValueError(f"DeepSeek 返回了不存在或不适用于项目节点图的积木：{block_type}")
            normalized.append(block_type)
        return normalized[:20]

    @classmethod
    def _normalize_logic_blueprint(cls, result: dict[str, Any]) -> dict[str, Any]:
        raw = result.get("logicBlueprint") if isinstance(result, dict) else None
        if not isinstance(raw, dict):
            raise ValueError("DeepSeek 世界任务结果缺少 logicBlueprint")
        world_summary = str(raw.get("worldSummary") or "").strip()[:800]
        core_loop = str(raw.get("coreLoop") or "").strip()[:1200]
        if not world_summary or not core_loop:
            raise ValueError("DeepSeek 世界玩法蓝图缺少世界概述或核心循环")

        actors = [
            str(item).strip()[:160]
            for item in (raw.get("requiredActors") or [])
            if str(item).strip()
        ][:30]
        flow = [
            str(item).strip()[:240]
            for item in (raw.get("flow") or [])
            if str(item).strip()
        ][:20]
        if not actors or len(flow) < 3:
            raise ValueError("DeepSeek 世界玩法蓝图缺少角色清单或节点流程")

        raw_effects = raw.get("nodeEffects")
        if not isinstance(raw_effects, list):
            raise ValueError("DeepSeek 世界玩法蓝图缺少 nodeEffects")
        effects: list[dict[str, Any]] = []
        effect_ids: set[str] = set()
        for item in raw_effects[:16]:
            if not isinstance(item, dict):
                continue
            effect_id = str(item.get("effectId") or "").strip()[:120]
            title = str(item.get("title") or "").strip()[:200]
            description = str(item.get("description") or "").strip()[:1200]
            verification = str(item.get("verification") or "").strip()[:800]
            if not effect_id or effect_id in effect_ids or not title or not description or not verification:
                raise ValueError("DeepSeek 世界玩法蓝图中的节点效果字段不完整或 effectId 重复")
            recommended = cls._normalize_block_type_list(
                item.get("recommendedBlockTypes"), field_name="recommendedBlockTypes",
            )
            if not recommended:
                raise ValueError(f"节点效果 {effect_id} 没有对应的现有积木")
            effect_ids.add(effect_id)
            effects.append({
                "effectId": effect_id,
                "title": title,
                "description": description,
                "trigger": str(item.get("trigger") or "").strip()[:800],
                "outcome": str(item.get("outcome") or "").strip()[:800],
                "recommendedBlockTypes": recommended,
                "verification": verification,
            })
        if len(effects) < 2:
            raise ValueError("DeepSeek 世界玩法蓝图中的节点效果数量不足")
        return {
            "worldSummary": world_summary,
            "coreLoop": core_loop,
            "requiredActors": actors,
            "nodeEffects": effects,
            "flow": flow,
        }

    @classmethod
    def _normalize_goal_plan_tasks(
        cls,
        result: dict[str, Any],
        context: dict[str, Any],
        now: int,
    ) -> list[dict[str, Any]]:
        blueprint = cls._normalize_logic_blueprint(result)
        effect_ids = {str(item.get("effectId") or "") for item in blueprint["nodeEffects"]}
        raw_tasks = result.get("tasks") if isinstance(result, dict) else None
        if not isinstance(raw_tasks, list):
            raise ValueError("DeepSeek 世界任务结果缺少 tasks 数组")
        raw_tasks = raw_tasks[:10]
        if len(raw_tasks) < 6:
            raise ValueError("DeepSeek 生成的世界任务数量不足")
        guidance_by_signal = {
            "model_imported": "import_model",
            "object_transformed": "transform_model",
            "lighting_adjusted": "adjust_lighting",
            "physics_adjusted": "adjust_physics",
            "node_created": "create_node",
            "node_moved": "move_node",
            "nodes_connected": "connect_nodes",
            "block_added": "drag_block",
            "block_parameter_changed": "edit_block_parameter",
            "transition_condition_set": "set_transition_condition",
            "node_graph_run": "run_node_graph",
            "run_succeeded": "run_node_graph",
        }
        baseline = {
            signal: max(0, int(count or 0))
            for signal, count in (context.get("goalSignalCounts") or {}).items()
            if signal in cls.GOAL_COMPLETION_SIGNALS
        }
        occurrences: dict[str, int] = {}
        tasks: list[dict[str, Any]] = []
        node_task_count = 0
        seen_scene_phase = False
        for index, raw in enumerate(raw_tasks, start=1):
            if not isinstance(raw, dict):
                continue
            phase = str(raw.get("phase") or "").strip()
            if phase not in cls.GOAL_PHASES:
                raise ValueError(f"DeepSeek 返回了不支持的任务阶段：{phase or '(空)'}")
            if phase == "scene-polish":
                seen_scene_phase = True
            elif seen_scene_phase:
                raise ValueError("节点玩法任务必须全部排在场景美化任务之前")

            signal = str(raw.get("completionSignal") or "").strip()
            if signal not in cls.GOAL_COMPLETION_SIGNALS:
                raise ValueError(f"DeepSeek 返回了不支持的完成信号：{signal or '(空)'}")
            if phase == "node-logic" and signal not in cls.GOAL_NODE_SIGNALS:
                raise ValueError("节点玩法任务使用了场景编辑完成信号")
            if phase == "scene-polish" and signal not in cls.GOAL_SCENE_SIGNALS:
                raise ValueError("场景美化任务使用了节点完成信号")

            effect_id = str(raw.get("effectId") or "").strip()[:120]
            if phase == "node-logic":
                node_task_count += 1
                if not effect_id or effect_id not in effect_ids:
                    raise ValueError("节点玩法任务没有关联 logicBlueprint 中的 effectId")
            else:
                effect_id = ""

            required_block_types = cls._normalize_block_type_list(
                raw.get("requiredBlockTypes"), field_name="requiredBlockTypes",
            )
            if signal in {"block_added", "block_parameter_changed"} and not required_block_types:
                raise ValueError("积木任务必须给出 requiredBlockTypes")
            if signal not in {"block_added", "block_parameter_changed"} and required_block_types:
                raise ValueError("非积木任务不应设置 requiredBlockTypes")

            title = str(raw.get("title") or "").strip()[:160]
            message = str(raw.get("message") or "").strip()[:1600]
            suggestion = str(raw.get("suggestion") or "").strip()[:1600]
            criteria = str(raw.get("completionCriteria") or "").strip()[:800]
            title_en = str(raw.get("titleEn") or title).strip()[:160]
            message_en = str(raw.get("messageEn") or message).strip()[:1600]
            suggestion_en = str(raw.get("suggestionEn") or suggestion).strip()[:1600]
            criteria_en = str(raw.get("completionCriteriaEn") or criteria).strip()[:800]
            if not title or not message or not suggestion or not criteria:
                raise ValueError("DeepSeek 生成的世界任务字段不完整")
            occurrences[signal] = occurrences.get(signal, 0) + 1
            tasks.append({
                "taskKey": f"goal.ai.{index:02d}",
                "issueKey": f"goal.ai.{index:02d}",
                "type": "goal",
                "track": "world-goal",
                "phase": phase,
                "effectId": effect_id,
                "order": index,
                "status": "queued",
                "code": "world_goal_step",
                "severity": "info",
                "confidence": 1.0,
                "title": title,
                "titleEn": title_en,
                "message": message,
                "messageEn": message_en,
                "suggestion": suggestion,
                "suggestionEn": suggestion_en,
                "completionCriteria": criteria,
                "completionCriteriaEn": criteria_en,
                "completionSignal": signal,
                "requiredCount": baseline.get(signal, 0) + occurrences[signal],
                "requiredBlockTypes": required_block_types,
                "observedBlockTypes": [],
                "guidanceIntent": guidance_by_signal[signal],
                "createdAt": now,
                "firstDetectedAt": now,
                "updatedAt": now,
                "completedAt": 0,
                "resolvedAt": 0,
            })
        if len(tasks) < 6:
            raise ValueError("DeepSeek 生成的有效世界任务数量不足")
        if node_task_count < cls.MIN_GOAL_NODE_TASKS:
            raise ValueError("世界任务必须优先包含足够的节点玩法实现步骤")
        node_tasks = [task for task in tasks if task.get("phase") == "node-logic"]
        if not node_tasks or node_tasks[-1].get("completionSignal") != "run_succeeded":
            raise ValueError("最后一个节点玩法任务必须验证节点逻辑成功运行")
        return tasks

    def start_goal_plan(self, payload: Any = None) -> dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        prompt = str(payload.get("prompt") or "").strip()[:4000]
        mode = str(payload.get("mode") or "story").strip().lower()
        if mode not in {"story", "creative"}:
            mode = "story"
        try:
            project_path = self._active_project_path()
            self._validate_payload_world(project_path, payload)
            now = self._now_ms()
            with self._lock:
                context = self._read_locked(project_path)
                if not prompt:
                    context["worldGoal"] = {
                        "prompt": "",
                        "mode": mode,
                        "source": "default",
                        "status": "ready",
                        "generatedAt": 0,
                        "generationError": "",
                        "generationId": "",
                    }
                    context["goalTaskPlan"] = {
                        "schemaVersion": 2,
                        "generatedAt": 0,
                        "taskCount": 0,
                        "nodeTaskCount": 0,
                        "sceneTaskCount": 0,
                        "logicBlueprint": {},
                    }
                    context["activeTasks"] = [
                        task for task in context.get("activeTasks") or []
                        if not isinstance(task, dict) or task.get("type") != "goal"
                    ]
                    self._ensure_task_slots_locked(context, now)
                    self._write_locked(project_path, context)
                    return {"success": True, "status": "completed", "context": self._clone(context)}

                goal = context.get("worldGoal") if isinstance(context.get("worldGoal"), dict) else {}
                goal_plan_tasks = [
                    task for task in [*(context.get("activeTasks") or []), *(context.get("taskHistory") or [])]
                    if isinstance(task, dict) and task.get("type") == "goal"
                ]
                has_goal_plan = any(
                    all(str(task.get(field) or "").strip() for field in (
                        "titleEn", "messageEn", "suggestionEn", "completionCriteriaEn",
                    ))
                    for task in goal_plan_tasks
                )
                if (goal.get("status") == "ready"
                        and str(goal.get("prompt") or "") == prompt
                        and str(goal.get("mode") or "story") == mode
                        and has_goal_plan):
                    return {"success": True, "status": "completed", "context": self._clone(context)}
                current_generation_id = str(goal.get("generationId") or "")
                current_state = self._goal_plan_tasks.get(current_generation_id)
                if (goal.get("status") == "generating"
                        and goal.get("source") == "ai"
                        and str(goal.get("prompt") or "") == prompt
                        and str(goal.get("mode") or "story") == mode
                        and current_state
                        and current_state.get("status") == "running"
                        and current_state.get("projectPath") == str(project_path)):
                    return {"success": True, "status": "pending", "taskId": current_generation_id}

                task_id = f"cabbage_goal_plan_{uuid.uuid4().hex}"
                context["worldGoal"] = {
                    "prompt": prompt,
                    "mode": mode,
                    "source": "ai",
                    "status": "generating",
                    "generatedAt": 0,
                    "generationError": "",
                    "generationId": task_id,
                }
                context["goalTaskPlan"] = {
                    "schemaVersion": 2,
                    "generatedAt": 0,
                    "taskCount": 0,
                    "nodeTaskCount": 0,
                    "sceneTaskCount": 0,
                    "logicBlueprint": {},
                }
                context["activeTasks"] = [
                    task for task in context.get("activeTasks") or []
                    if not isinstance(task, dict) or task.get("type") != "goal"
                ]
                # Keep the deterministic tutorials visible while DeepSeek is planning.
                # The successful result replaces them atomically; a timeout, crash or
                # invalid AI response therefore never leaves the task board empty.
                self._ensure_task_slots_locked(context, now)
                self._write_locked(project_path, context)
                self._goal_plan_tasks[task_id] = {
                    "taskId": task_id,
                    "status": "running",
                    "projectPath": str(project_path),
                    "prompt": prompt,
                    "mode": mode,
                    "createdAt": time.time(),
                    "result": None,
                }
                self._prune_goal_plan_tasks_locked()
                future = self._executor.submit(self._generate_goal_plan, project_path, prompt, mode, task_id)
                future.add_done_callback(lambda completed, current_task_id=task_id: self._complete_goal_plan(current_task_id, completed))
                return {"success": True, "status": "pending", "taskId": task_id}
        except Exception as exc:
            logger.warning("Unable to start Cabbage world task generation: %s", type(exc).__name__)
            return self._error("GOAL_PLAN_START_FAILED", str(exc))

    def _generate_goal_plan(
        self, project_path: Path, prompt: str, mode: str, generation_id: str,
    ) -> dict[str, Any]:
        try:
            result = self._call_deepseek_for_goal_plan(prompt, mode)
            now = self._now_ms()
            with self._lock:
                context = self._read_locked(project_path)
                current_goal = context.get("worldGoal") if isinstance(context.get("worldGoal"), dict) else {}
                if (str(current_goal.get("prompt") or "") != prompt
                        or str(current_goal.get("mode") or "story") != mode
                        or current_goal.get("source") != "ai"
                        or str(current_goal.get("generationId") or "") != generation_id):
                    return self._error("GOAL_PLAN_STALE", "世界目标已经变化，已忽略迟到的任务结果。")
                logic_blueprint = self._normalize_logic_blueprint(result)
                tasks = self._normalize_goal_plan_tasks(result, context, now)
                context["activeTasks"] = [
                    task for task in context.get("activeTasks") or []
                    if not isinstance(task, dict) or task.get("type") not in {"tutorial", "goal"}
                ] + tasks
                context["worldGoal"] = {
                    "prompt": prompt,
                    "mode": mode,
                    "source": "ai",
                    "status": "ready",
                    "generatedAt": now,
                    "generationError": "",
                    "generationId": generation_id,
                }
                context["goalTaskPlan"] = {
                    "schemaVersion": 2,
                    "generatedAt": now,
                    "taskCount": len(tasks),
                    "nodeTaskCount": sum(1 for task in tasks if task.get("phase") == "node-logic"),
                    "sceneTaskCount": sum(1 for task in tasks if task.get("phase") == "scene-polish"),
                    "logicBlueprint": logic_blueprint,
                }
                self._ensure_task_slots_locked(context, now)
                self._write_locked(project_path, context)
                return {"success": True, "status": "ok", "context": self._clone(context)}
        except urllib.error.HTTPError as exc:
            status = int(getattr(exc, "code", 0) or 0)
            message = "DeepSeek API Key 无效或无权限。" if status in {401, 403} else f"DeepSeek 请求失败（HTTP {status}）。"
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            message = "无法连接 DeepSeek，请稍后重试。"
        except Exception as exc:
            logger.warning("Cabbage world task generation failed: %s", type(exc).__name__)
            message = str(exc) or "世界任务生成失败。"
        failure_context = None
        with self._lock:
            context = self._read_locked(project_path)
            goal = context.get("worldGoal") if isinstance(context.get("worldGoal"), dict) else {}
            if (str(goal.get("prompt") or "") == prompt
                    and str(goal.get("mode") or "story") == mode
                    and goal.get("source") == "ai"
                    and str(goal.get("generationId") or "") == generation_id):
                goal.update({"status": "error", "generationError": message, "generatedAt": 0})
                context["worldGoal"] = goal
                self._ensure_task_slots_locked(context, self._now_ms())
                self._write_locked(project_path, context)
                failure_context = self._clone(context)
        failure = self._error("GOAL_PLAN_GENERATION_FAILED", message)
        if failure_context is not None:
            failure["context"] = failure_context
        return failure

    def _complete_goal_plan(self, task_id: str, future: Any) -> None:
        try:
            result = future.result()
        except Exception as exc:
            logger.warning("Cabbage world task generation callback failed: %s", type(exc).__name__)
            result = self._error("GOAL_PLAN_GENERATION_FAILED", "世界任务生成失败。")
        with self._lock:
            state = self._goal_plan_tasks.get(task_id)
            if state:
                state["status"] = "completed"
                state["result"] = result
                state["completedAt"] = time.time()

    def goal_plan_status(self, task_id: Any) -> dict[str, Any]:
        key = str(task_id or "")
        with self._lock:
            state = self._goal_plan_tasks.get(key)
            if not state:
                return self._error("GOAL_PLAN_TASK_NOT_FOUND", "没有找到这次世界任务生成请求。")
            response = {"success": True, "status": state["status"], "taskId": key}
            if state["status"] == "completed":
                response["result"] = self._clone(state.get("result") or {})
            return response

    def _prune_goal_plan_tasks_locked(self) -> None:
        if len(self._goal_plan_tasks) <= self.MAX_GOAL_PLAN_TASKS:
            return
        completed = sorted(
            (state for state in self._goal_plan_tasks.values() if state.get("status") == "completed"),
            key=lambda item: float(item.get("completedAt") or item.get("createdAt") or 0),
        )
        for state in completed[: max(0, len(self._goal_plan_tasks) - self.MAX_GOAL_PLAN_TASKS)]:
            self._goal_plan_tasks.pop(state["taskId"], None)

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
