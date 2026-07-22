from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
import uuid
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeepSeekSettings:
    api_key: str
    base_url: str
    model: str
    source: str


class NodeGraphReviewService:
    """Review a visible project node graph without executing its generated script."""

    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-v4-flash"
    TIMEOUT_SECONDS = 35
    CONTRACT_FILENAME = "CoronaBlocksDocument.internal-ai-contract.xml"
    MAX_TASKS = 32
    MAX_CACHE_ENTRIES = 32

    # Only these fields identify an existing scene actor. TAG, variable names,
    # cooldown names and spawn names are intentionally excluded.
    ACTOR_REFERENCE_FIELDS: dict[str, tuple[str, ...]] = {
        "engine_move": ("OBJECT",),
        "engine_rotateX": ("OBJECT",),
        "engine_rotateY": ("OBJECT",),
        "engine_rotateZ": ("OBJECT",),
        "engine_face": ("OBJECT",),
        "engine_moveto": ("OBJECT",),
        "engine_movetoXYZ": ("OBJECT",),
        "engine_movetoXYZtime": ("OBJECT",),
        "engine_Xset": ("OBJECT",),
        "engine_Yset": ("OBJECT",),
        "engine_Zset": ("OBJECT",),
        "engine_Xadd": ("OBJECT",),
        "engine_Yadd": ("OBJECT",),
        "engine_Zadd": ("OBJECT",),
        "engine_X": ("OBJECT",),
        "engine_Y": ("OBJECT",),
        "engine_Z": ("OBJECT",),
        "engine_rotationX": ("OBJECT",),
        "engine_rotationY": ("OBJECT",),
        "engine_rotationZ": ("OBJECT",),
        "object_set_position": ("NAME",),
        "object_get_x": ("NAME",),
        "object_get_y": ("NAME",),
        "object_get_z": ("NAME",),
        "object_hide": ("NAME",),
        "object_show": ("NAME",),
        "object_delete": ("NAME",),
        "object_exists": ("NAME",),
        "object_set_tag": ("NAME",),
        "object_clamp_axis": ("NAME",),
        "object_set_native_physics": ("NAME",),
        "object_set_logical_collision": ("NAME",),
        "object_logical_collision_enabled": ("NAME",),
        "object_save_checkpoint": ("NAME",),
        "object_restore_checkpoint": ("NAME",),
        "object_reset_crossed_once": ("NAME",),
        "object_move_to_lane": ("NAME",),
        "object_move_to_lane_smooth": ("NAME",),
        "object_lane_index": ("NAME",),
        "object_set_random_position": ("NAME",),
        "object_third_person_move": ("NAME",),
        "object_arcade_jump": ("NAME",),
        "object_first_person_move": ("NAME",),
        "camera_follow_object": ("NAME",),
        "camera_third_person_orbit": ("NAME",),
        "camera_first_person_follow": ("NAME",),
        "combat_melee_attack": ("PLAYER",),
        "combat_enemy_chase_tag": ("PLAYER",),
        "combat_enemy_contact_damage": ("PLAYER",),
        "object_breakout_reset_round": ("BALL", "PADDLE"),
        "object_breakout_paddle_control": ("PADDLE",),
        "object_breakout_step": ("BALL", "PADDLE"),
        "detect_object_exists": ("NAME",),
        "detect_object_not_exists": ("NAME",),
        "detect_inside_axis": ("NAME",),
        "detect_outside_axis": ("NAME",),
        "detect_inside_box": ("NAME",),
        "detect_position_near": ("NAME",),
        "detect_passed_x": ("NAME",),
        "detect_passed_z": ("NAME",),
        "detect_crossed_x_once": ("NAME",),
        "detect_crossed_z_once": ("NAME",),
    }
    ACTOR_PLACEHOLDERS = {
        "", "__manual__", "none", "null", "undefined", "actor", "object",
        "target", "current actor", "current object", "请选择", "请选择对象",
        "选择对象", "未选择", "对象", "物体", "对象名称", "物体名称",
        "当前对象", "当前物体",
    }

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="NodeGraphReview"
        )
        self._lock = threading.RLock()
        self._tasks: dict[str, dict[str, Any]] = {}
        self._result_cache: dict[str, dict[str, Any]] = {}
        self._closed = False

    def start(self, payload: Any) -> dict[str, Any]:
        """Queue a review and return immediately without waiting for DeepSeek."""
        try:
            request = self._normalize_payload(payload)
        except ValueError as exc:
            return self._error("INVALID_REVIEW_DATA", str(exc))

        revision = request["graphRevision"]
        task_id = "node_review_" + uuid.uuid4().hex
        now = time.time()
        with self._lock:
            if self._closed:
                return self._error("AI_REVIEW_STOPPED", "Node graph review service has stopped.")
            cached = self._result_cache.get(revision)
            if cached is not None:
                self._tasks[task_id] = {
                    "taskId": task_id,
                    "graphRevision": revision,
                    "status": "completed",
                    "createdAt": now,
                    "completedAt": now,
                    "result": json.loads(json.dumps(cached, ensure_ascii=False)),
                }
                self._prune_tasks_locked()
                return {
                    "success": True,
                    "status": "completed",
                    "taskId": task_id,
                    "graphRevision": revision,
                }

            self._tasks[task_id] = {
                "taskId": task_id,
                "graphRevision": revision,
                "status": "pending",
                "createdAt": now,
            }
            self._prune_tasks_locked()
            future = self._executor.submit(self.review, request)
            future.add_done_callback(
                lambda completed, current_task_id=task_id, current_revision=revision: self._complete_task(
                    current_task_id, current_revision, completed
                )
            )

        return {
            "success": True,
            "status": "pending",
            "taskId": task_id,
            "graphRevision": revision,
        }

    def status(self, task_id: str) -> dict[str, Any]:
        task_key = str(task_id or "").strip()
        if not task_key:
            return self._error("INVALID_TASK_ID", "Missing node graph review task ID.")
        with self._lock:
            task = self._tasks.get(task_key)
            if task is None:
                return self._error("REVIEW_TASK_NOT_FOUND", "Node graph review task was not found or has expired.")
            response = {
                "success": True,
                "status": task["status"],
                "taskId": task["taskId"],
                "graphRevision": task["graphRevision"],
            }
            if task["status"] == "completed":
                response["result"] = json.loads(
                    json.dumps(task.get("result") or {}, ensure_ascii=False)
                )
            return response

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _complete_task(self, task_id: str, revision: str, future: Any) -> None:
        try:
            result = future.result()
        except Exception as exc:
            logger.exception("Background node graph review failed: %s", type(exc).__name__)
            result = self._error(
                "AI_REVIEW_FAILED", "Node graph review failed and will retry later."
            )
        completed_at = time.time()
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task["status"] = "completed"
            task["completedAt"] = completed_at
            task["result"] = result
            if result.get("success") is True and result.get("status") == "ok":
                self._result_cache[revision] = json.loads(
                    json.dumps(result, ensure_ascii=False)
                )
                while len(self._result_cache) > self.MAX_CACHE_ENTRIES:
                    self._result_cache.pop(next(iter(self._result_cache)))
            self._prune_tasks_locked()

    def _prune_tasks_locked(self) -> None:
        if len(self._tasks) <= self.MAX_TASKS:
            return
        completed = sorted(
            (task for task in self._tasks.values() if task.get("status") == "completed"),
            key=lambda item: float(item.get("completedAt") or item.get("createdAt") or 0),
        )
        for task in completed[: max(0, len(self._tasks) - self.MAX_TASKS)]:
            self._tasks.pop(str(task.get("taskId") or ""), None)

    @classmethod
    def _find_contract_path(cls, start_path: Path | str | None = None) -> Path:
        """Find the repository contract from both source and packaged editor layouts."""
        start = Path(start_path or __file__).resolve()
        search_roots = [start] if start.is_dir() else list(start.parents)
        for root in search_roots:
            candidate = root / "docs" / cls.CONTRACT_FILENAME
            if candidate.is_file():
                return candidate
        # Keep a deterministic path in diagnostics when the checkout is incomplete.
        fallback_root = search_roots[-1] if search_roots else start.parent
        return fallback_root / "docs" / cls.CONTRACT_FILENAME

    def review(self, payload: Any) -> dict[str, Any]:
        try:
            request = self._normalize_payload(payload)
            settings = self._resolve_settings()
            if not settings.api_key:
                return self._error(
                    "AI_NOT_CONFIGURED",
                    "DeepSeek 未配置，节点审查暂不可用。",
                )

            facts = self._collect_local_facts(
                request["workspace"], request.get("projectContext") or {}
            )
            catalog = self._catalog_summary(request["workspace"])
            prompt = self._build_prompt(request, facts, catalog)
            raw_result = self._call_deepseek(settings, prompt)
            result = self._parse_model_result(raw_result)
            self._validate_model_result(result, request)
            result.update(
                {
                    "schemaVersion": 1,
                    "graphRevision": request["graphRevision"],
                    "provider": "deepseek",
                    "model": settings.model,
                }
            )
            logger.info(
                "Node graph review completed [source=%s, model=%s, revision=%s, "
                "nodes=%d, edges=%d, facts=%d, has_problems=%s]",
                settings.source,
                settings.model,
                request["graphRevision"][:12],
                len(request["workspace"]["nodes"]),
                len(request["workspace"]["edges"]),
                len(facts),
                bool(result.get("hasProblems")),
            )
            return {"success": True, "status": "ok", **result}
        except ValueError as exc:
            logger.warning("Node graph review rejected: %s", exc)
            return self._error("INVALID_REVIEW_DATA", str(exc))
        except urllib.error.HTTPError as exc:
            status = int(getattr(exc, "code", 0) or 0)
            logger.warning("Node graph review provider HTTP error [status=%s]", status)
            if status in (401, 403):
                return self._error(
                    "AI_AUTH_FAILED",
                    "DeepSeek 身份验证失败，请检查 ai_setting.py 中的 deepseek 配置。",
                )
            if status == 429:
                return self._error(
                    "AI_RATE_LIMITED", "DeepSeek 请求过于频繁，请稍后再试。"
                )
            return self._error(
                "AI_PROVIDER_ERROR", f"DeepSeek 服务暂时不可用（HTTP {status}）。"
            )
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            logger.warning(
                "Node graph review network error: %s", type(exc).__name__
            )
            return self._error(
                "AI_NETWORK_ERROR",
                "暂时无法连接 DeepSeek，节点审查将在下一轮重试。",
            )
        except Exception as exc:
            logger.exception("Node graph review failed: %s", type(exc).__name__)
            return self._error(
                "AI_REVIEW_FAILED", "节点逻辑审查失败，将在下一轮自动重试。"
            )

    @staticmethod
    def _error(code: str, message: str) -> dict[str, Any]:
        return {
            "success": False,
            "status": "error",
            "error": code,
            "message": message,
        }

    @staticmethod
    def _normalize_payload(payload: Any) -> dict[str, Any]:
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise ValueError("节点审查请求必须是对象")

        workspace = payload.get("workspace")
        if not isinstance(workspace, dict):
            raise ValueError("缺少节点 workspace")
        nodes = workspace.get("nodes")
        edges = workspace.get("edges")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise ValueError("workspace.nodes 和 workspace.edges 必须是数组")

        revision = str(payload.get("graphRevision") or "").strip()
        if not revision:
            raise ValueError("缺少 graphRevision")

        return {
            "schemaVersion": 1,
            "requestId": str(payload.get("requestId") or ""),
            "graphRevision": revision,
            "targetId": "node_graph:project:global",
            "workspace": {
                "version": int(workspace.get("version") or 1),
                "nodes": nodes,
                "edges": edges,
                "globalVariablesWorkspace": workspace.get(
                    "globalVariablesWorkspace"
                )
                or {},
            },
            "projectContext": payload.get("projectContext")
            if isinstance(payload.get("projectContext"), dict)
            else {},
        }

    @classmethod
    def _resolve_settings(cls) -> DeepSeekSettings:
        provider: Any = None
        raw_provider: dict[str, Any] = {}
        try:
            from Quasar.ai_service.entrance import get_ai_entrance

            collector = get_ai_entrance().collector
            providers = getattr(collector.AIConfig, "providers", {}) or {}
            provider = providers.get("deepseek") if hasattr(providers, "get") else None
            if provider is None:
                raw = getattr(collector, "AI_SETTINGS", {})
                candidate = (
                    (raw.get("providers") or {}).get("deepseek")
                    if isinstance(raw, dict)
                    else None
                )
                if isinstance(candidate, dict):
                    raw_provider = candidate
        except Exception as exc:
            logger.debug(
                "DeepSeek editor configuration lookup failed: %s",
                type(exc).__name__,
            )

        def read(name: str) -> str:
            value = getattr(provider, name, "") if provider is not None else ""
            return str(value or raw_provider.get(name, "") or "").strip()

        editor_key = read("api_key")
        editor_model = read("model")
        if editor_key:
            return DeepSeekSettings(
                editor_key,
                read("base_url") or cls.DEFAULT_BASE_URL,
                os.getenv("DEEPSEEK_MODEL", "").strip()
                or editor_model
                or cls.DEFAULT_MODEL,
                "editor-ai-setting",
            )

        return DeepSeekSettings(
            os.getenv("DEEPSEEK_API_KEY", "").strip(),
            os.getenv("DEEPSEEK_BASE_URL", "").strip() or cls.DEFAULT_BASE_URL,
            os.getenv("DEEPSEEK_MODEL", "").strip() or cls.DEFAULT_MODEL,
            "environment",
        )

    @classmethod
    def _call_deepseek(cls, settings: DeepSeekSettings, prompt: str) -> str:
        base = settings.base_url.rstrip("/")
        endpoint = base if base.endswith("/chat/completions") else base + "/chat/completions"
        body = {
            "model": settings.model,
            "temperature": 0.1,
            "max_tokens": 1200,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 CoronaEngine 3D 游戏节点逻辑审查员。只审查给定的可见节点、"
                        "连线、条件和积木，不编造对象或积木。发现问题时合并成一句委婉、"
                        "可执行的中文提示，句式接近‘……有问题，原因是……；这样做就好了。’"
                        "只输出 JSON。"
                    ),
                },
                {"role": "user", "content": prompt},
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
        with urllib.request.urlopen(request, timeout=cls.TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))

        choices = data.get("choices") if isinstance(data, dict) else None
        message = (
            choices[0].get("message")
            if isinstance(choices, list)
            and choices
            and isinstance(choices[0], dict)
            else None
        )
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("DeepSeek 返回了空内容")
        return content.strip()

    @staticmethod
    def _parse_model_result(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        fence = chr(96) * 3
        if cleaned.startswith(fence):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.rstrip().endswith(fence):
                cleaned = cleaned.rstrip()[:-3]
            cleaned = cleaned.strip()

        try:
            value = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            if start < 0:
                raise ValueError("DeepSeek 未返回 JSON")
            value, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        if not isinstance(value, dict):
            raise ValueError("DeepSeek 审查结果必须是 JSON 对象")
        return value

    @staticmethod
    def _validate_model_result(
        result: dict[str, Any], request: dict[str, Any]
    ) -> None:
        if not isinstance(result.get("hasProblems"), bool):
            raise ValueError("DeepSeek 结果缺少 hasProblems")

        summary = result.get("summary", "")
        if result["hasProblems"] and (
            not isinstance(summary, str) or not summary.strip()
        ):
            raise ValueError("DeepSeek 检测到问题但没有给出 summary")
        result["summary"] = summary.strip()[:160] if isinstance(summary, str) else ""

        issues = result.get("issues", [])
        if not isinstance(issues, list):
            raise ValueError("DeepSeek issues 必须是数组")
        if not result["hasProblems"]:
            result["summary"] = ""
            result["issues"] = []
            return

        node_ids = {
            str(node.get("id"))
            for node in request["workspace"]["nodes"]
            if isinstance(node, dict)
        }
        block_ids = {
            str(block.get("id"))
            for block in NodeGraphReviewService._walk_blocks(request["workspace"])
            if block.get("id")
        }
        normalized: list[dict[str, Any]] = []
        for item in issues[:6]:
            if not isinstance(item, dict):
                continue
            node_id = str(item.get("nodeId") or "")
            block_id = str(item.get("blockId") or "")
            if node_id and node_id not in node_ids:
                continue
            if block_id and block_id not in block_ids:
                continue
            try:
                confidence = max(
                    0.0, min(1.0, float(item.get("confidence") or 0.0))
                )
            except (TypeError, ValueError):
                confidence = 0.0
            if confidence < 0.8:
                continue
            code = str(item.get("code") or "logic_issue")[:80]
            title = str(item.get("title") or "\u8282\u70b9\u903b\u8f91\u9700\u8981\u5904\u7406").strip()[:80]
            message = str(item.get("message") or result["summary"]).strip()[:500]
            suggestion = str(item.get("suggestion") or result["summary"]).strip()[:500]
            normalized.append(
                {
                    "issueKey": f"{code}|{node_id}|{block_id}",
                    "severity": str(item.get("severity") or "warning")[:16],
                    "confidence": confidence,
                    "nodeId": node_id,
                    "blockId": block_id,
                    "code": code,
                    "title": title,
                    "message": message,
                    "suggestion": suggestion,
                }
            )
        if result["hasProblems"] and not normalized:
            result["hasProblems"] = False
            result["summary"] = ""
            result["issues"] = []
            return
        result["issues"] = normalized

    @staticmethod
    def _walk_blocks(value: Any) -> Iterable[dict[str, Any]]:
        if isinstance(value, dict):
            if isinstance(value.get("type"), str):
                yield value
            for child in value.values():
                yield from NodeGraphReviewService._walk_blocks(child)
        elif isinstance(value, list):
            for child in value:
                yield from NodeGraphReviewService._walk_blocks(child)

    @classmethod
    def _normalize_actor_name(cls, value: Any) -> str:
        if isinstance(value, dict):
            value = value.get("name") or value.get("value") or value.get("id") or ""
        if value is None:
            return ""
        return str(value).strip()

    @classmethod
    def _is_missing_actor_name(cls, value: Any) -> bool:
        name = cls._normalize_actor_name(value)
        return name.casefold() in {item.casefold() for item in cls.ACTOR_PLACEHOLDERS}

    @classmethod
    def _connected_actor_reference(
        cls, block: dict[str, Any], input_name: str
    ) -> tuple[str, str]:
        """Return (resolved|missing|dynamic|absent, actor_name)."""
        inputs = block.get("inputs") if isinstance(block.get("inputs"), dict) else {}
        connection = inputs.get(input_name)
        if not isinstance(connection, dict):
            return "absent", ""
        child = connection.get("block")
        if not isinstance(child, dict):
            child = connection.get("shadow")
        if not isinstance(child, dict):
            return "missing", ""

        child_type = str(child.get("type") or "")
        fields = child.get("fields") if isinstance(child.get("fields"), dict) else {}
        if child_type == "text":
            name = cls._normalize_actor_name(fields.get("TEXT"))
            return ("missing", "") if cls._is_missing_actor_name(name) else ("resolved", name)
        if child_type == "object_reference":
            selected = cls._normalize_actor_name(fields.get("OBJECT"))
            if selected == "__manual__":
                manual = cls._normalize_actor_name(fields.get("MANUAL"))
                return ("missing", "") if cls._is_missing_actor_name(manual) else ("resolved", manual)
            # Empty OBJECT means the old implicit current actor, which does not
            # exist in the project-global node graph.
            return ("missing", "") if cls._is_missing_actor_name(selected) else ("resolved", selected)

        # Variables, functions and composed text may resolve to an actor at
        # runtime. They are not deterministic enough for a local error fact.
        return "dynamic", ""

    @classmethod
    def _actor_reference(
        cls, block: dict[str, Any], field_name: str
    ) -> tuple[str, str]:
        connected_state, connected_name = cls._connected_actor_reference(block, field_name)
        if connected_state != "absent":
            return connected_state, connected_name

        fields = block.get("fields") if isinstance(block.get("fields"), dict) else {}
        aliases = (field_name, f"{field_name}_TEXT")
        present = False
        for alias in aliases:
            if alias not in fields:
                continue
            present = True
            name = cls._normalize_actor_name(fields.get(alias))
            if not cls._is_missing_actor_name(name):
                return "resolved", name
        configured = field_name in cls.ACTOR_REFERENCE_FIELDS.get(str(block.get("type") or ""), ())
        return ("missing", "") if present or configured else ("absent", "")

    @classmethod
    def _collect_local_facts(
        cls, workspace: dict[str, Any], project_context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """只收集能够确定的结构事实，不用固定玩法模板推断错误。"""
        nodes = [node for node in workspace.get("nodes", []) if isinstance(node, dict)]
        edges = [edge for edge in workspace.get("edges", []) if isinstance(edge, dict)]
        facts: list[dict[str, Any]] = []

        node_id_values = [str(node.get("id") or "").strip() for node in nodes]
        node_ids = {node_id for node_id in node_id_values if node_id}
        if any(not node_id for node_id in node_id_values):
            facts.append({"code": "missing_node_id", "detail": "存在没有 ID 的节点"})
        duplicate_node_ids = sorted(
            node_id for node_id in node_ids if node_id_values.count(node_id) > 1
        )
        if duplicate_node_ids:
            facts.append(
                {
                    "code": "duplicate_node_id",
                    "detail": "节点 ID 重复：" + "、".join(duplicate_node_ids[:6]),
                }
            )

        starts = [node for node in nodes if node.get("nodeType") == "start"]
        if len(starts) != 1:
            facts.append(
                {
                    "code": "start_node_count",
                    "detail": f"开始节点数量为 {len(starts)}，可运行节点图必须恰好有 1 个开始节点",
                }
            )

        edge_id_values = [str(edge.get("id") or "").strip() for edge in edges]
        edge_ids = {edge_id for edge_id in edge_id_values if edge_id}
        if any(not edge_id for edge_id in edge_id_values):
            facts.append({"code": "missing_edge_id", "detail": "存在没有 ID 的连线"})
        duplicate_edge_ids = sorted(
            edge_id for edge_id in edge_ids if edge_id_values.count(edge_id) > 1
        )
        if duplicate_edge_ids:
            facts.append(
                {
                    "code": "duplicate_edge_id",
                    "detail": "连线 ID 重复：" + "、".join(duplicate_edge_ids[:6]),
                }
            )

        catalog = cls._catalog_index()
        all_blocks = list(cls._walk_blocks(workspace))
        block_scopes: list[tuple[str, Any]] = [
            ("全局变量池", workspace.get("globalVariablesWorkspace") or {})
        ]
        block_scopes.extend(
            (f"节点 {str(node.get('id') or '')}", node.get("workspace") or {})
            for node in nodes
        )
        block_scopes.extend(
            (f"连线 {str(edge.get('id') or '')}", edge.get("conditionWorkspace") or {})
            for edge in edges
        )
        for scope_name, scope_workspace in block_scopes:
            scope_blocks = list(cls._walk_blocks(scope_workspace))
            block_id_values = [
                str(block.get("id") or "").strip() for block in scope_blocks
            ]
            if any(not block_id for block_id in block_id_values):
                facts.append(
                    {
                        "code": "missing_block_id",
                        "detail": f"{scope_name}中存在没有 ID 的积木",
                    }
                )
            duplicate_block_ids = sorted(
                {
                    block_id
                    for block_id in block_id_values
                    if block_id and block_id_values.count(block_id) > 1
                }
            )
            if duplicate_block_ids:
                facts.append(
                    {
                        "code": "duplicate_block_id",
                        "detail": f"{scope_name}中的积木 ID 重复："
                        + "、".join(duplicate_block_ids[:6]),
                    }
                )

        if catalog:
            unknown_types = sorted(
                {
                    str(block.get("type") or "").strip()
                    for block in all_blocks
                    if str(block.get("type") or "").strip()
                    and str(block.get("type") or "").strip() not in catalog
                }
            )
            if unknown_types:
                facts.append(
                    {
                        "code": "unknown_block_type",
                        "detail": "存在引擎未登记的积木类型：" + "、".join(unknown_types[:8]),
                    }
                )

        for edge in edges:
            edge_id = str(edge.get("id") or "")
            source_value = edge.get("source") if isinstance(edge.get("source"), dict) else {}
            target_value = edge.get("target") if isinstance(edge.get("target"), dict) else {}
            source = str(source_value.get("nodeId") or "")
            target = str(target_value.get("nodeId") or "")
            if source not in node_ids or target not in node_ids:
                facts.append(
                    {
                        "code": "dangling_edge",
                        "edgeId": edge_id,
                        "detail": "连线端点引用了不存在的节点",
                    }
                )

            condition_workspace = edge.get("conditionWorkspace") or {}
            top_blocks = cls._top_level_blocks(condition_workspace)
            if len(top_blocks) != 1:
                facts.append(
                    {
                        "code": "invalid_visible_condition_count",
                        "edgeId": edge_id,
                        "detail": f"连线条件顶层积木数量为 {len(top_blocks)}，必须恰好为 1",
                    }
                )
                continue
            condition_type = str(top_blocks[0].get("type") or "")
            condition_contract = catalog.get(condition_type) if catalog else None
            if condition_contract and condition_contract.get("outputCheck") != "Boolean":
                facts.append(
                    {
                        "code": "non_boolean_condition",
                        "edgeId": edge_id,
                        "blockId": str(top_blocks[0].get("id") or ""),
                        "detail": f"连线条件积木 {condition_type} 的输出不是 Boolean",
                    }
                )

        actors_value = (project_context or {}).get("actors")
        actor_context_available = isinstance(actors_value, list)
        known_actors = {
            str(actor.get("name") or "").strip()
            for actor in (actors_value or [])
            if isinstance(actor, dict) and str(actor.get("name") or "").strip()
        }

        scoped_blocks: list[tuple[str, dict[str, Any]]] = []
        for node in nodes:
            node_id = str(node.get("id") or "")
            scoped_blocks.extend(
                (node_id, block) for block in cls._walk_blocks(node.get("workspace") or {})
            )
        scoped_blocks.extend(
            ("", block)
            for block in cls._walk_blocks(workspace.get("globalVariablesWorkspace") or {})
        )
        scoped_blocks.extend(
            ("", block)
            for edge in edges
            for block in cls._walk_blocks(edge.get("conditionWorkspace") or {})
        )

        for node_id, block in scoped_blocks:
            block_type = str(block.get("type") or "")
            block_id = str(block.get("id") or "")
            contract = catalog.get(block_type) if catalog else None
            if contract and contract.get("projectUsage") == "actor-context":
                facts.append(
                    {
                        "code": "missing_actor_target",
                        "nodeId": node_id,
                        "blockId": block_id,
                        "blockType": block_type,
                        "detail": f"积木 {block_type} 依赖绑定脚本的当前物体，但项目全局节点没有隐式物体上下文",
                        "suggestion": "改用带对象名称或标签参数的项目级积木，并选择当前场景中的具体物体",
                    }
                )
                continue

            for field_name in cls.ACTOR_REFERENCE_FIELDS.get(block_type, ()):
                state, actor_name = cls._actor_reference(block, field_name)
                if state == "missing":
                    facts.append(
                        {
                            "code": "missing_actor_target",
                            "nodeId": node_id,
                            "blockId": block_id,
                            "blockType": block_type,
                            "field": field_name,
                            "detail": f"积木 {block_type} 的对象参数 {field_name} 没有指定具体物体",
                            "suggestion": "在该对象参数中选择当前场景里的目标物体",
                        }
                    )
                elif state == "resolved" and actor_context_available and actor_name not in known_actors:
                    facts.append(
                        {
                            "code": "actor_target_not_found",
                            "nodeId": node_id,
                            "blockId": block_id,
                            "blockType": block_type,
                            "field": field_name,
                            "actorName": actor_name,
                            "detail": f"积木 {block_type} 指向的对象 {actor_name} 在当前场景中不存在",
                            "suggestion": "改成场景已有对象名称，或先创建同名对象",
                        }
                    )
        return facts

    @staticmethod
    def _top_level_blocks(workspace: Any) -> list[dict[str, Any]]:
        if not isinstance(workspace, dict):
            return []
        blocks_container = workspace.get("blocks")
        if not isinstance(blocks_container, dict):
            return []
        blocks = blocks_container.get("blocks")
        if not isinstance(blocks, list):
            return []
        return [block for block in blocks if isinstance(block, dict)]

    @classmethod
    @lru_cache(maxsize=1)
    def _catalog_index(cls) -> dict[str, dict[str, Any]]:
        try:
            root = ET.parse(cls._find_contract_path()).getroot()
        except Exception as exc:
            logger.warning(
                "Node graph review catalog unavailable: %s", type(exc).__name__
            )
            return {}

        index: dict[str, dict[str, Any]] = {}
        for element in root.findall(".//Block"):
            block_type = str(element.get("type") or "")
            if not block_type:
                continue
            index[block_type] = {
                "type": block_type,
                "category": str(element.get("category") or ""),
                "shape": str(element.get("shape") or ""),
                "outputCheck": str(element.get("outputCheck") or ""),
                "projectUsage": str(element.get("projectUsage") or ""),
                "label": str(element.get("label") or ""),
                "inputs": [
                    {
                        "name": str(item.get("name") or ""),
                        "kind": str(item.get("kind") or ""),
                        "check": str(item.get("check") or ""),
                    }
                    for item in element.findall("Input")
                ],
            }
        return index

    @classmethod
    def _catalog_summary(cls, workspace: dict[str, Any]) -> list[dict[str, Any]]:
        used_types = sorted(
            {
                str(block.get("type") or "")
                for block in cls._walk_blocks(workspace)
                if block.get("type")
            }
        )
        index = cls._catalog_index()
        return [index[block_type] for block_type in used_types if block_type in index]

    @staticmethod
    def _build_prompt(
        request: dict[str, Any],
        facts: list[dict[str, Any]],
        catalog: list[dict[str, Any]],
    ) -> str:
        graph_json = json.dumps(
            request["workspace"], ensure_ascii=False, separators=(",", ":")
        )
        facts_json = json.dumps(facts, ensure_ascii=False, separators=(",", ":"))
        context_json = json.dumps(
            request.get("projectContext") or {},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        catalog_json = json.dumps(
            catalog, ensure_ascii=False, separators=(",", ":")
        )
        return (
            "你只负责判断当前 CoronaEngine 节点图按它已经表达出的逻辑能否正确执行。\n"
            "不要评价游戏是否有趣、丰富、完整或复杂；不要要求增加胜利、失败、分数、生命、"
            "敌人、冷却、界面或任何额外玩法。单节点、简单逻辑、持续运行、没有结束状态都可以"
            "是正确设计。不要参照坦克大战、下到一百层、躲避球或任何固定 Demo 模板，也不要猜测"
            "用户原本想做什么。\n"
            "只有从可见节点、连线、条件、积木和场景上下文中能够直接证明以下情况时，才返回 "
            "hasProblems=true：图结构无效或无法启动；已有连线或条件无效；某条已经表达的流程确定性"
            "地不可达；某个条件依赖的值按可见逻辑永远不可能满足；引用的节点、积木或场景对象不存在；"
            "同一条流程中的状态读写明显矛盾；循环确定性地造成阻塞或失控。项目全局节点没有隐式"
            "‘当前物体’：如果本地事实包含 missing_actor_target 或 actor_target_not_found，必须明确说明"
            "哪个操作没有指向有效物体，并告诉用户在对象参数中选择场景对象，或改用带对象名称/标签参数的"
            "项目级积木。缺少某种玩法功能不是错误，只是可能可以扩展也不是错误；证据不足或无法确定用户"
            "意图时必须返回无问题。\n"
            "如果逻辑正确，严格输出 {\"hasProblems\":false,\"summary\":\"\",\"issues\":[]}。\n"
            "如果逻辑确实错误，严格输出 JSON：{\"hasProblems\":true,\"summary\":\"……有问题，"
            "原因是……；把……改成……就好了。\",\"issues\":[{\"severity\":\"warning\","
            "\"confidence\":0.95,\"nodeId\":\"真实节点ID或空字符串\","
            "\"blockId\":\"真实积木ID或空字符串\",\"code\":\"稳定的英文问题代码\","
            "\"title\":\"简短名称\",\"message\":\"错误原因\","
            "\"suggestion\":\"直接修复方法\"}]}。\n"
            "summary 只写一句简短中文，最多 160 字，把多个确定的问题合并说明；不要列清单，不要介绍"
            "模块，不要输出玩法扩展、优化建议或鼓励语。issues 只记录 summary 所依据的真实问题。\n"
            "本地确定性事实（只作为证据；没有事实不代表一定有错）："
            + facts_json
            + "\n项目上下文："
            + context_json
            + "\n当前实际使用的积木合同摘要："
            + catalog_json
            + "\n节点图："
            + graph_json
        )


_SERVICE = NodeGraphReviewService()


def get_node_graph_review_service() -> NodeGraphReviewService:
    return _SERVICE
