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
    MAX_PROJECT_ACTORS = 80
    MAX_ACTOR_ALIASES = 12
    MAX_ACTOR_TAGS = 12
    DETAIL_GUIDANCE_TERMS = (
        "不理解", "看不懂", "不会", "怎么做", "怎么连接", "放在哪里", "怎么放",
        "为什么还是不行", "展示", "演示", "给我看看", "一步一步", "具体步骤",
        "怎么改", "show me", "don't understand", "how do i",
    )
    GUIDANCE_INTENTS = {
        "connect_object_reference", "select_existing_object", "create_node",
        "move_node", "connect_nodes", "drag_block", "edit_block_parameter",
        "set_transition_condition", "run_node_graph", "import_model",
        "transform_model", "adjust_lighting", "adjust_physics",
    }
    GUIDANCE_BY_TASK = {
        "tutorial.import_model": (
            "import_model",
            ["打开场景管理 Dock", "找到导入模型入口并选择模型文件", "确认场景树中出现新的模型对象"],
        ),
        "tutorial.transform_model": (
            "transform_model",
            ["先在场景中选中一个模型", "打开对象 Dock 并展开变换", "修改位置、旋转或缩放中的任意一个参数"],
        ),
        "tutorial.adjust_lighting": (
            "adjust_lighting",
            ["打开场景管理 Dock", "找到场景光照设置", "切换光照或修改光照方向的任意轴"],
        ),
        "tutorial.adjust_physics": (
            "adjust_physics",
            ["选择一个模型并打开对象 Dock", "展开物理区域", "启用物理或修改质量、弹性、阻尼和锁轴"],
        ),
        "tutorial.create_node": (
            "create_node",
            ["打开节点 Dock", "从左侧节点工具区选择节点", "将节点拖入中间画布"],
        ),
        "tutorial.move_node": (
            "move_node",
            ["打开节点 Dock 并找到已有节点", "按住节点标题区域", "把节点拖到新的位置后松开"],
        ),
        "tutorial.connect_nodes": (
            "connect_nodes",
            ["找到两个需要连接的节点", "从前一个节点的输出端口开始拖动", "拖到后一个节点的输入端口后松开"],
        ),
        "tutorial.drag_block": (
            "drag_block",
            ["先选中一个节点", "从左侧微观积木工具箱选择积木", "把积木拖入节点内部编辑区"],
        ),
        "tutorial.edit_block_parameter": (
            "edit_block_parameter",
            ["选中包含目标积木的节点", "找到需要修改的下拉项、数值或文本字段", "修改字段并等待节点图自动保存"],
        ),
        "tutorial.set_transition_condition": (
            "set_transition_condition",
            ["选中需要设置条件的节点连线", "在条件编辑区放入返回 Boolean 的积木", "确保条件区只有一个完整的返回表达式"],
        ),
        "tutorial.run_node_graph": (
            "run_node_graph",
            ["确认开始节点已经连接到后续节点", "找到节点 Dock 顶部的运行按钮", "点击运行并观察逻辑是否正常执行"],
        ),
    }
    GUIDANCE_BY_ISSUE = {
        "missing_actor_target": (
            "connect_object_reference",
            ["打开节点 Dock 并选中包含操作积木的节点", "找到操作积木的对象输入口", "连接“对象[]”积木并选择场景中的目标物体", "运行节点逻辑确认目标物体能够响应"],
        ),
        "actor_target_not_found": (
            "select_existing_object",
            ["打开节点 Dock 并找到对象引用积木", "展开对象选择项", "改为当前场景中真实存在的物体"],
        ),
        "start_node_count": (
            "create_node",
            ["打开节点 Dock 并查看整个节点图", "只保留一个开始节点", "将开始节点连接到第一个需要执行的节点"],
        ),
        "invalid_edge_endpoint": (
            "connect_nodes",
            ["定位到无效的节点连线", "删除或断开这条连线", "从有效输出端口重新连接到有效输入端口"],
        ),
        "invalid_visible_condition_count": (
            "set_transition_condition",
            ["选中对应节点连线", "打开连线条件编辑区", "只保留一个完整的 Boolean 返回表达式"],
        ),
        "non_boolean_condition": (
            "set_transition_condition",
            ["选中对应节点连线", "检查条件区最外层返回值", "改为比较、逻辑或其他返回 Boolean 的积木"],
        ),
        "unknown_block_type": (
            "drag_block",
            ["定位到当前不支持的积木", "移除这个积木", "从左侧工具箱换成当前引擎提供的积木"],
        ),
        "missing_required_input": (
            "drag_block",
            ["定位到缺少输入的积木", "找到未连接的关键输入口", "连接类型匹配的积木并补齐必要参数"],
        ),
    }

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
            task_key = str(task.get("taskKey") or task.get("issueKey") or "")[:160]
            task_type = str(task.get("type") or "")
            if task_type not in {"tutorial", "goal", "node-issue"}:
                task_type = "node-issue"
            tasks.append({
                "taskKey": task_key,
                "issueKey": task_key,
                "type": task_type,
                "title": str(task.get("title") or "")[:160],
                "message": str(task.get("message") or "")[:800],
                "suggestion": str(task.get("suggestion") or "")[:800],
                "completionCriteria": str(task.get("completionCriteria") or "")[:600],
                "completionSignal": str(task.get("completionSignal") or "")[:80],
                "guidanceIntent": str(task.get("guidanceIntent") or "")[:80],
                "nodeId": str(task.get("nodeId") or "")[:160],
                "blockId": str(task.get("blockId") or "")[:160],
                "edgeId": str(task.get("edgeId") or "")[:160],
                "code": str(task.get("code") or "")[:80],
            })

        graph_excerpt = payload.get("graphExcerpt") if isinstance(payload.get("graphExcerpt"), dict) else {}
        graph_text = json.dumps(graph_excerpt, ensure_ascii=False, separators=(",", ":"))
        if len(graph_text) > cls.MAX_GRAPH_CHARS:
            graph_text = graph_text[: cls.MAX_GRAPH_CHARS] + "…"

        raw_project_context = payload.get("projectContext")
        raw_project_context = raw_project_context if isinstance(raw_project_context, dict) else {}
        actors = []
        seen_actor_names = set()
        for item in (raw_project_context.get("actors") or [])[: cls.MAX_PROJECT_ACTORS]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()[:240]
            name_key = name.casefold()
            if not name or name_key in seen_actor_names:
                continue
            seen_actor_names.add(name_key)
            aliases = []
            for alias in (item.get("aliases") or [])[: cls.MAX_ACTOR_ALIASES]:
                value = str(alias or "").strip()[:240]
                if value and value.casefold() != name_key and value not in aliases:
                    aliases.append(value)
            tags = []
            for tag in (item.get("tags") or [])[: cls.MAX_ACTOR_TAGS]:
                value = str(tag or "").strip()[:120]
                if value and value not in tags:
                    tags.append(value)
            actors.append({
                "name": name,
                "type": str(item.get("type") or "actor").strip()[:120] or "actor",
                "tags": tags,
                "aliases": aliases,
            })
        project_context = {
            "sceneName": str(raw_project_context.get("sceneName") or "").strip()[:320],
            "actorContextAvailable": raw_project_context.get("actorContextAvailable") is True,
            "actors": actors,
        }

        raw_profile = payload.get("assistanceProfile")
        raw_profile = raw_profile if isinstance(raw_profile, dict) else {}
        try:
            score = max(0, min(int(round(float(raw_profile.get("score", raw_profile.get("fluencyScore", 0)) or 0))), 100))
        except (TypeError, ValueError):
            score = 0
        last_user_text = messages[-1]["content"].casefold()
        selected_task_key = str(payload.get("selectedTaskKey") or "")[:160]
        same_task_user_messages = sum(1 for item in messages if item["role"] == "user")
        detail_requested = payload.get("detailGuidanceRequested") is True or any(
            term.casefold() in last_user_text for term in cls.DETAIL_GUIDANCE_TERMS
        ) or bool(selected_task_key and same_task_user_messages >= 2)
        return {
            "requestId": str(payload.get("requestId") or f"node_chat_{uuid.uuid4().hex}"),
            "worldId": str(payload.get("worldId") or "")[:160],
            "projectScopeId": str(payload.get("projectScopeId") or "")[:160],
            "graphRevision": str(payload.get("graphRevision") or "")[:160],
            "assistanceProfile": {
                "score": score,
                "updatedAt": max(0, int(raw_profile.get("updatedAt") or 0)),
            },
            "selectedTaskKey": selected_task_key,
            "detailGuidanceRequested": detail_requested,
            "tasks": tasks,
            "graphText": graph_text,
            "projectContext": project_context,
            "messages": messages,
        }

    @classmethod
    def _guidance_metadata(cls, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("detailGuidanceRequested") is not True:
            return {"needsShowcase": False, "guidanceIntent": "", "steps": []}

        selected = next(
            (task for task in request.get("tasks") or []
             if task.get("taskKey") == request.get("selectedTaskKey")),
            None,
        )
        resolved = None
        last_text = str((request.get("messages") or [{}])[-1].get("content") or "").casefold()

        # The latest explicit request takes precedence over the task that happens to be
        # selected. This keeps a physics showcase from falling back to transform fields.
        keyword_guidance = (
            (("物理", "碰撞", "质量", "弹性", "阻尼", "锁轴", "重力", "刚体"), (), cls.GUIDANCE_BY_TASK["tutorial.adjust_physics"]),
            (("对象", "物体", "目标"), ("连接", "指定", "选择", "移动", "输入"), cls.GUIDANCE_BY_ISSUE["missing_actor_target"]),
            (("导入", "模型"), (), cls.GUIDANCE_BY_TASK["tutorial.import_model"]),
            (("光照", "灯光"), (), cls.GUIDANCE_BY_TASK["tutorial.adjust_lighting"]),
            (("位置", "旋转", "缩放", "变换", "移动物体"), (), cls.GUIDANCE_BY_TASK["tutorial.transform_model"]),
            (("跳转条件", "布尔", "boolean"), (), cls.GUIDANCE_BY_TASK["tutorial.set_transition_condition"]),
            (("连线", "连接节点", "端口"), (), cls.GUIDANCE_BY_TASK["tutorial.connect_nodes"]),
            (("拖入积木", "拖拽积木", "积木放"), (), cls.GUIDANCE_BY_TASK["tutorial.drag_block"]),
            (("参数", "字段", "数值"), (), cls.GUIDANCE_BY_TASK["tutorial.edit_block_parameter"]),
            (("运行节点", "节点运行"), (), cls.GUIDANCE_BY_TASK["tutorial.run_node_graph"]),
            (("创建节点", "新增节点"), (), cls.GUIDANCE_BY_TASK["tutorial.create_node"]),
            (("拖动节点", "移动节点"), (), cls.GUIDANCE_BY_TASK["tutorial.move_node"]),
        )
        for primary, secondary, candidate in keyword_guidance:
            if any(word.casefold() in last_text for word in primary) and (
                not secondary or any(word.casefold() in last_text for word in secondary)
            ):
                resolved = candidate
                break

        if not resolved and selected:
            if selected.get("type") == "goal":
                selected_intent = str(selected.get("guidanceIntent") or "")
                resolved = next(
                    (candidate for candidate in cls.GUIDANCE_BY_TASK.values() if candidate[0] == selected_intent),
                    None,
                )
            if not resolved:
                resolved = cls.GUIDANCE_BY_TASK.get(str(selected.get("taskKey") or ""))
            if not resolved:
                resolved = cls.GUIDANCE_BY_ISSUE.get(str(selected.get("code") or ""))

        if not resolved:
            return {
                "needsShowcase": False,
                "guidanceIntent": "",
                "steps": [
                    "先确认当前要完成的目标和出现问题的位置",
                    "检查对应对象、节点、积木或连线是否已经选中并正确连接",
                    "完成修改后重新运行或等待下一次节点审查确认结果",
                ],
            }

        intent, steps = resolved
        intent = intent if intent in cls.GUIDANCE_INTENTS else ""
        normalized_steps = [str(step).strip()[:500] for step in steps if str(step).strip()][:8]
        return {
            "needsShowcase": bool(intent and normalized_steps),
            "guidanceIntent": intent,
            "steps": normalized_steps,
        }

    @staticmethod
    def _build_messages(request: dict[str, Any]) -> list[dict[str, str]]:
        selected = next(
            (task for task in request["tasks"] if task["taskKey"] == request["selectedTaskKey"]),
            None,
        )
        context = {
            "worldId": request["worldId"],
            "projectScopeId": request["projectScopeId"],
            "graphRevision": request["graphRevision"],
            "selectedTask": selected,
            "activeTasks": request["tasks"],
            "graphExcerpt": request["graphText"],
            "projectContext": request["projectContext"],
        }
        profile = request.get("assistanceProfile") or {}
        score = max(0, min(int(profile.get("score") or 0), 100))
        has_score = int(profile.get("updatedAt") or 0) > 0
        if not has_score:
            score_instruction = (
                "尚无稳定操作评分，请使用平和、清楚、适中详细度的回答。"
            )
        elif score >= 75:
            score_instruction = (
                "用户操作评分较高，请回答简洁、专业，给用户保留自主排查空间。"
                "仅在直接相关时补充状态机、控制流、数据流、Boolean 求值、对象引用、"
                "实时计算机图形学、变换或物理知识，不要展开无关教学。"
            )
        elif score <= 45:
            score_instruction = (
                "用户当前需要更具体的引导。请使用平和、通俗的语言，减少术语，"
                "说清需要点击、拖拽、连接或修改的位置，并给出验证方法。"
            )
        else:
            score_instruction = (
                "请保持适中详细度，先给关键修改方向，再补充必要的操作步骤，"
                "仅解释与当前问题直接相关的术语。"
            )
        detail_instruction = (
            "用户明确表示不理解或连续追问。请把解决方法整理成清楚的编号步骤，"
            "说明操作位置、连接顺序和完成后的验证方法。不要声称已经替用户修改。"
            if request.get("detailGuidanceRequested") is True else ""
        )
        return [
            {
                "role": "system",
                "content": (
                    "你是 CoronaEngine 的包菜答疑助手。请围绕当前世界、待处理任务和节点图回答。"
                    "对基础引导任务和世界制作任务，说明如何在引擎内完成；对节点问题，说明原因、修改位置和验证方法。"
                    "不得编造不存在的节点、积木、对象或 API。信息不足时应使用条件式建议。"
                    "node_graph:project:global 是当前 Native Editor 场景的项目级节点图，默认已经作用于当前场景。"
                    "项目节点图的 actorName 为空表示它不固定绑定单个物体，不表示场景没有绑定。"
                    "不得要求用户选择原生场景、绑定模式、确认绑定或点击应用。"
                    "projectContext.actors 是场景管理中已经导入的可用物体；涉及移动、跳跃、旋转、碰撞等对象操作时，"
                    "必须优先使用其中的精确对象名，并说明在对应积木的对象参数中选择该物体。"
                    "如果 actorContextAvailable 为 false，只能说明暂时无法读取对象列表，不能编造场景绑定面板。"
                    "不要向用户显示内部评分，不要给用户贴美术、程序、入门、熟悉或熟练标签。"
                    "不要输出 JSON，不要为用户生成或覆盖 Python 脚本。"

                    "请使用干净的中文纯文本回答，不要使用 Markdown 标题、星号加粗、反引号、"
                    "代码围栏或横线分隔符。需要分步骤时只使用‘1. 2. 3.’编号，"
                    "每一步保持一到两句，不要堆叠装饰符号。"
                    + score_instruction
                    + detail_instruction
                ),
            },
            {
                "role": "system",
                "content": "当前结构化上下文：" + json.dumps(context, ensure_ascii=False),
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
                    state.update(self._guidance_metadata(request))
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
                "needsShowcase": False,
                "guidanceIntent": "",
                "steps": [],
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
                "needsShowcase": state.get("needsShowcase") is True,
                "guidanceIntent": str(state.get("guidanceIntent") or ""),
                "steps": [str(step) for step in (state.get("steps") or [])[:8]],
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
                return {
                    "success": True,
                    "status": "ok",
                    "message": result.get("content", ""),
                    "needsShowcase": result.get("needsShowcase") is True,
                    "guidanceIntent": str(result.get("guidanceIntent") or ""),
                    "steps": list(result.get("steps") or []),
                }
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
