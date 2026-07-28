"""DeepSeek-powered project node-graph generation for Cabbage Q&A.

The service consumes the trusted CoronaBlocks XML contract and returns a complete JSON
workspace.  It never writes project files and never generates Python; the mounted
NodeGraphWorkspace remains responsible for validation, code generation, atomic apply,
and persistence.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import logging
from pathlib import Path
import re
import socket
import threading
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

from .node_graph_review_service import NodeGraphReviewService

try:
    from editor.backend.blockly.ai_node_graph_contract import (
        load_contract_catalog,
        validate_generated_node_graph,
    )
except ImportError:  # Packaged editor layout places ``backend`` directly on sys.path.
    from backend.blockly.ai_node_graph_contract import (
        load_contract_catalog,
        validate_generated_node_graph,
    )

logger = logging.getLogger(__name__)


class NodeGraphGenerationService:
    """Asynchronous, single-worker node graph CRUD generation service."""

    TARGET_ID = "node_graph:project:global"
    VALID_OPERATIONS = {"create", "extend", "edit", "delete"}
    TIMEOUT_SECONDS = 90
    MAX_TASKS = 16
    MAX_INSTRUCTION_CHARS = 4000
    VALID_RESPONSE_LANGUAGES = {"zh-CN", "en-US"}
    FORBIDDEN_KEYS = {
        "python",
        "sourcecode",
        "generatedcode",
        "xml",
        "filepath",
        "actortarget",
        "scenetarget",
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="NodeGraphGenerate")
        self._tasks: dict[str, dict[str, Any]] = {}
        self._closed = False
        self._contract_cache: tuple[int, str] | None = None

    @staticmethod
    def _error(code: str, message: str) -> dict[str, Any]:
        return {"success": False, "status": "error", "error": code, "message": message}

    @classmethod
    def _normalize_payload(cls, payload: Any) -> dict[str, Any]:
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise ValueError("节点生成请求必须是对象")

        request_id = str(payload.get("requestId") or "").strip()
        project_scope_id = str(payload.get("projectScopeId") or "").strip()
        base_revision = str(payload.get("baseGraphRevision") or "").strip()
        operation = str(payload.get("operation") or "create").strip().lower()
        instruction = str(payload.get("instruction") or "").strip()
        target_id = str(payload.get("targetId") or cls.TARGET_ID).strip()
        workspace = payload.get("workspace")
        project_context = payload.get("projectContext")
        response_language = str(payload.get("responseLanguage") or "").strip()

        if not request_id:
            raise ValueError("缺少 requestId")
        if not project_scope_id:
            raise ValueError("缺少 projectScopeId")
        if not base_revision:
            raise ValueError("缺少 baseGraphRevision")
        if target_id != cls.TARGET_ID:
            raise ValueError(f"targetId 必须为 {cls.TARGET_ID}")
        if operation not in cls.VALID_OPERATIONS:
            raise ValueError("operation 必须为 create、extend、edit 或 delete")
        if not instruction:
            raise ValueError("请输入要生成、制作或编辑的游戏逻辑")
        if not isinstance(workspace, dict):
            raise ValueError("缺少当前节点 workspace")
        if not isinstance(workspace.get("nodes"), list) or not isinstance(workspace.get("edges"), list):
            raise ValueError("workspace.nodes 和 workspace.edges 必须是数组")
        if not isinstance(workspace.get("globalVariablesWorkspace", {}), dict):
            raise ValueError("workspace.globalVariablesWorkspace 必须是对象")
        if not isinstance(project_context, dict):
            project_context = {}
        if response_language not in cls.VALID_RESPONSE_LANGUAGES:
            response_language = "zh-CN" if re.search(r"[\u3400-\u9fff]", instruction) else "en-US"

        return {
            "schemaVersion": 1,
            "requestId": request_id[:160],
            "targetId": cls.TARGET_ID,
            "projectScopeId": project_scope_id[:160],
            "baseGraphRevision": base_revision[:160],
            "operation": operation,
            "instruction": instruction[: cls.MAX_INSTRUCTION_CHARS],
            "responseLanguage": response_language,
            "workspace": json.loads(json.dumps(workspace, ensure_ascii=False)),
            "projectContext": json.loads(json.dumps(project_context, ensure_ascii=False)),
        }

    def _load_contract(self) -> tuple[Path, str]:
        path = NodeGraphReviewService._find_contract_path(__file__)
        if not path.is_file():
            raise ValueError(f"找不到节点积木 AI 合同：{path.name}")
        modified = path.stat().st_mtime_ns
        with self._lock:
            if self._contract_cache and self._contract_cache[0] == modified:
                return path, self._contract_cache[1]
        text = path.read_text(encoding="utf-8")
        if "<CoronaBlocksDocument" not in text or "<Catalog" not in text:
            raise ValueError("节点积木 AI 合同格式不正确")
        with self._lock:
            self._contract_cache = (modified, text)
        return path, text

    @staticmethod
    def _instruction_requirements(instruction: str) -> dict[str, Any]:
        text = str(instruction or "")
        lowered = text.casefold()
        requires_wasd = "wasd" in lowered or bool(
            re.search(r"(?:\u524d\u540e\u5de6\u53f3|\u56db\u65b9\u5411|\u65b9\u5411\u952e)", text)
        )
        requires_space_jump = bool(
            ("space" in lowered or "\u7a7a\u683c" in text)
            and ("jump" in lowered or "\u8df3" in text)
        )
        first_person_requested = bool(
            "first person" in lowered
            or "first-person" in lowered
            or "\u7b2c\u4e00\u4eba\u79f0" in text
        )
        broad_demo_terms = re.compile(
            r"(?:\u5b8c\u6574\u6e38\u620f|\u6574\u4e2a\u6e38\u620f|\u6e38\u620f\u6f14\u793a|demo|deno|"
            r"\u8ba1\u5206|\u751f\u547d|\u80dc\u5229|\u5931\u8d25|\u654c\u4eba|\u6218\u6597|\u5173\u5361|"
            r"score|lives?|victory|defeat|enemy|combat|level)",
            re.IGNORECASE,
        )
        narrow_object_control = bool(
            (requires_wasd or requires_space_jump) and not broad_demo_terms.search(text)
        )
        capabilities = []
        if requires_wasd:
            capabilities.append("wasd-object-movement")
        if requires_space_jump:
            capabilities.append("space-object-jump")
        replacement_match = re.search(
            r"(?:(?:\u5c06|\u628a)\s*)?(.{1,80}?)\s*"
            r"(?:\u4fee\u6539(?:\u6210|\u4e3a)|\u6539(?:\u6210|\u4e3a)|"
            r"\u66ff\u6362(?:\u6210|\u4e3a)|\u6362(?:\u6210|\u4e3a)|"
            r"\u8c03\u6574(?:\u6210|\u4e3a)|\u8bbe\u7f6e(?:\u6210|\u4e3a)|"
            r"\u8bbe(?:\u6210|\u4e3a)|\u53d8(?:\u6210|\u4e3a))\s*"
            r"([^\u3002\uff01\uff1f!?\n]{1,80})",
            text,
            re.IGNORECASE,
        )
        replacement_directive = None
        if replacement_match:
            source = replacement_match.group(1).strip(" \t\uFF0C,\uFF1A:")
            source = re.sub(
                r"^(?:\u8bf7(?:\u4f60)?|\u9ebb\u70e6|\u5e2e\u6211|\u5e2e\u5fd9|\u7ed9\u6211|\u66ff\u6211|\u4e3a\u6211)\s*",
                "",
                source,
            )
            source = re.sub(r"^(?:\u5c06|\u628a)\s*", "", source)
            replacement_directive = {
                "source": source,
                "target": replacement_match.group(2).strip(" \t\uFF0C,\uFF1A:"),
            }
        return {
            "requiredCapabilities": capabilities,
            "narrowObjectControl": narrow_object_control,
            "firstPersonRequested": first_person_requested,
            "replacementDirective": replacement_directive,
        }

    @staticmethod
    def _build_prompt(request: dict[str, Any], contract_text: str) -> str:
        requirements = NodeGraphGenerationService._instruction_requirements(request["instruction"])
        request_payload = {
            "schemaVersion": request["schemaVersion"],
            "requestId": request["requestId"],
            "targetId": request["targetId"],
            "projectScopeId": request["projectScopeId"],
            "baseGraphRevision": request["baseGraphRevision"],
            "operation": request["operation"],
            "instruction": request["instruction"],
            "responseLanguage": request["responseLanguage"],
            "derivedRequirements": requirements,
            "workspace": request["workspace"],
            "projectContext": request["projectContext"],
        }
        scoped_rules = []
        if requirements["narrowObjectControl"]:
            scoped_rules.append(
                "This is a narrow object-control request. Modify only the minimum relevant node logic. "
                "Do not add score, lives, victory, defeat, combat, enemy, or complete-demo state templates."
            )
        if "wasd-object-movement" in requirements["requiredCapabilities"]:
            scoped_rules.append(
                "The final reachable node_while_active DO chain must contain object_third_person_move "
                "(or object_first_person_move only when first-person control is explicitly requested). "
                "Never use object_set_tag_velocity_axis as a substitute for single-object WASD control."
            )
        if "space-object-jump" in requirements["requiredCapabilities"]:
            scoped_rules.append(
                "The same reachable node_while_active DO chain must also contain object_arcade_jump. "
                "Its NAME must exactly equal the movement block NAME."
            )
        scoped_text = "\n".join(f"- {item}" for item in scoped_rules) or "- Follow only the explicit user request."
        operation_rules = {
            "create": (
                "Create the requested logic as a complete valid final workspace. Reuse useful existing logic "
                "when it already satisfies part of the request."
            ),
            "extend": (
                "Extend the current workspace in place. Keep every existing unrelated node, edge, block, "
                "condition, global variable, ID, and canvas position; add or connect only the minimum requested logic."
            ),
            "edit": (
                "Edit the current workspace in place as a targeted transformation. Locate the existing nodes, "
                "blocks, fields, object references, edges, or conditions described by the instruction and change "
                "only those matches. Preserve unrelated logic and preserve existing IDs, node positions, edge "
                "connections, and block order whenever they are not the requested target. Do not clear or rebuild "
                "the graph. For phrases such as modify-to/change-to/replace-with, treat the right-hand value as "
                "the replacement and update the matching existing value rather than generating a second parallel feature."
            ),
            "delete": (
                "Delete only the explicitly requested nodes, blocks, edges, or conditions. Preserve all unrelated "
                "logic and repair only connections made invalid by that deletion."
            ),
        }
        operation_rule = operation_rules[request["operation"]]
        language = request["responseLanguage"]
        return (
            "You are editing CoronaEngine's visible project node graph. Follow the complete trusted XML contract below.\n"
            "Return exactly one JSON object containing the complete final workspace. Never return a patch, Python, XML, "
            "Markdown, file path, or prose outside the JSON. Use only catalog blocks. Preserve unrelated existing logic "
            "for extend/edit/delete. Never invent an actor: object names must exactly match projectContext.actors.\n"
            "The project node graph is already scoped to the current Native Editor scene. An empty graph-level actor "
            "binding is expected and must never trigger a scene-binding workflow. Never ask the user to bind a scene or actor. "
            "For movement, jump, rotation, collision, physics, and other object operations, choose the intended concrete target "
            "from projectContext.actors and serialize its exact name into the supported object field or object input defined by "
            "the XML contract.\n\n"
            "OPERATION MODE:\n"
            + f"- {operation_rule}\n\n"
            + "TASK SCOPING RULES:\n"
            "- Implement only capabilities explicitly requested by the user. Do not expand a small feature into a full game.\n"
            "- XML examples are structural illustrations only and must never be copied as gameplay templates.\n"
            "- Prefer the smallest valid graph change and reuse an existing reachable gameplay node when practical.\n"
            + scoped_text
            + "\n\nBLOCKLY SERIALIZATION GUARDRAILS:\n"
            "- fields contains only real Catalog <Field> names. inputs contains only real Catalog <Input> names. "
            "Never serialize an input socket as a field.\n"
            "- control_if has no BOOL field. Put a Boolean output block under inputs.CONDITION.block. "
            "Example: {\"type\":\"control_if\",\"id\":\"if_1\",\"inputs\":{"
            "\"CONDITION\":{\"block\":{\"type\":\"logic_boolean\",\"id\":\"bool_1\","
            "\"fields\":{\"BOOL\":\"TRUE\"}}},\"DO\":{\"block\":{\"type\":\"engine_rotateZ\","
            "\"id\":\"rotate_1\",\"fields\":{\"ANGLE\":15},\"inputs\":{\"OBJECT\":{\"block\":{"
            "\"type\":\"object_reference\",\"id\":\"object_1\",\"fields\":{\"OBJECT\":\"RealActorName\","
            "\"MANUAL\":\"\"}}}}}}}}.\n"
            "- engine_rotateX/engine_rotateY/engine_rotateZ have only the ANGLE field. Bind the target through "
            "inputs.OBJECT.block using object_reference, and choose an exact actor name from PROJECT_CONTEXT. "
            "Never invent an actor name or leave an object placeholder.\n"
            "- inputs.DO is a statement connection. Put the first action in inputs.DO.block and continue that branch "
            "with next.block. Never put branch actions beside DO or inside fields.\n"
            "- Before returning JSON, check every block against its Catalog entry: every field name, input name, "
            "connection kind, output type, and dropdown value must match exactly.\n"
            + "\n\nLANGUAGE RULES:\n"
            + f"- responseLanguage is {language}. The summary and every newly added or renamed custom node/edge label must use that language.\n"
            "- Do not mix Chinese and English UI labels. Technical block types, field names, IDs, WASD, API names, "
            "and real actor names are identifiers and must not be translated.\n\n"
            "HOST_REQUEST_JSON:\n"
            + json.dumps(request_payload, ensure_ascii=False, separators=(",", ":"))
            + "\n\nFULL_CORONA_BLOCKS_CONTRACT_XML:\n"
            + contract_text
        )

    @classmethod
    def _call_deepseek(cls, settings: Any, prompt: str) -> str:
        base = str(settings.base_url or "").rstrip("/")
        endpoint = base if base.endswith("/chat/completions") else base + "/chat/completions"
        body = {
            "model": settings.model,
            "temperature": 0.05,
            "max_tokens": 12000,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 CoronaEngine 内嵌节点图编辑器。你只输出一个 JSON 对象。"
                        "必须根据完整 XML 合同对 node_graph:project:global 做增删改查，返回完整最终节点图。"
                        "禁止输出 Python、XML、文件路径、JSON Patch、Markdown 或合同外积木。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        http_request = urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + settings.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=cls.TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        choices = data.get("choices") if isinstance(data, dict) else None
        first = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first.get("message"), dict) else {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("DeepSeek 返回了空内容")
        return content.strip()

    @classmethod
    def _contains_forbidden_key(cls, value: Any) -> str:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).replace("_", "").lower()
                if normalized in cls.FORBIDDEN_KEYS:
                    return str(key)
                found = cls._contains_forbidden_key(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = cls._contains_forbidden_key(child)
                if found:
                    return found
        return ""

    @staticmethod
    def _workspace_roots(workspace: Any) -> list[dict[str, Any]]:
        if not isinstance(workspace, dict):
            return []
        container = workspace.get("blocks")
        if not isinstance(container, dict):
            return []
        roots = container.get("blocks")
        return [item for item in roots if isinstance(item, dict)] if isinstance(roots, list) else []

    @classmethod
    def _walk_block(cls, block: Any):
        if not isinstance(block, dict):
            return
        yield block
        inputs = block.get("inputs")
        if isinstance(inputs, dict):
            for connection in inputs.values():
                if not isinstance(connection, dict):
                    continue
                for key in ("block", "shadow"):
                    child = connection.get(key)
                    if isinstance(child, dict):
                        yield from cls._walk_block(child)
        connection = block.get("next")
        if isinstance(connection, dict):
            for key in ("block", "shadow"):
                child = connection.get(key)
                if isinstance(child, dict):
                    yield from cls._walk_block(child)

    @classmethod
    def _workspace_blocks(cls, workspace: Any):
        for root in cls._workspace_roots(workspace):
            yield from cls._walk_block(root)

    @staticmethod
    def _all_graph_workspaces(workspace: Any):
        if not isinstance(workspace, dict):
            return
        nodes = workspace.get("nodes")
        if isinstance(nodes, list):
            for node in nodes:
                if isinstance(node, dict):
                    yield node.get("workspace")
        edges = workspace.get("edges")
        if isinstance(edges, list):
            for edge in edges:
                if isinstance(edge, dict):
                    yield edge.get("conditionWorkspace")
        yield workspace.get("globalVariablesWorkspace")

    @classmethod
    def _normalize_model_block_serialization(
        cls, result: dict[str, Any], contract_path: Path
    ) -> tuple[dict[str, Any], list[str]]:
        """Repair deterministic field/input confusions, then require strict validation."""
        normalized = json.loads(json.dumps(result, ensure_ascii=False))
        workspace = normalized.get("workspace")
        if not isinstance(workspace, dict):
            return normalized, []

        catalog = load_contract_catalog(contract_path)
        block_specs = catalog.get("blocks", {})
        used_ids: set[str] = set()
        for graph_workspace in cls._all_graph_workspaces(workspace):
            for block in cls._workspace_blocks(graph_workspace):
                block_id = str(block.get("id") or "").strip()
                if block_id:
                    used_ids.add(block_id)

        repair_sequence = 0

        def repair_id(prefix: str) -> str:
            nonlocal repair_sequence
            while True:
                repair_sequence += 1
                candidate = f"ai_repair_{prefix}_{repair_sequence}"
                if candidate not in used_ids:
                    used_ids.add(candidate)
                    return candidate

        repairs: list[str] = []

        def normalize_block(block: Any, trail: str) -> None:
            if not isinstance(block, dict):
                return
            block_type = str(block.get("type") or "").strip()
            spec = block_specs.get(block_type)
            fields = block.get("fields")
            inputs = block.get("inputs")
            if not isinstance(fields, dict):
                fields = None
            if inputs is None:
                inputs = {}
                block["inputs"] = inputs
            elif not isinstance(inputs, dict):
                inputs = None

            # BOOL belongs to logic_boolean, never directly to control_if/control_else.
            if (
                block_type in {"control_if", "control_else"}
                and fields is not None
                and "BOOL" in fields
                and inputs is not None
            ):
                bool_value = fields.pop("BOOL")
                if "CONDITION" not in inputs:
                    inputs["CONDITION"] = {
                        "block": {
                            "type": "logic_boolean",
                            "id": repair_id("condition"),
                            "fields": {"BOOL": bool_value},
                        }
                    }
                    repairs.append(f"{trail}: moved BOOL into inputs.CONDITION.logic_boolean")
                else:
                    repairs.append(f"{trail}: removed redundant BOOL field from {block_type}")

            # Generic transforms expose OBJECT as a String value input, not a field.
            if fields is not None and inputs is not None and spec is not None and "OBJECT" in fields:
                object_input = spec.inputs.get("OBJECT")
                object_is_not_field = "OBJECT" not in spec.fields
                object_is_string_input = bool(
                    object_input
                    and object_input.get("kind") == "value"
                    and "String" in tuple(object_input.get("check") or ())
                )
                object_name = fields.get("OBJECT")
                if object_is_not_field and object_is_string_input and isinstance(object_name, str):
                    fields.pop("OBJECT")
                    if "OBJECT" not in inputs and object_name.strip():
                        inputs["OBJECT"] = {
                            "block": {
                                "type": "object_reference",
                                "id": repair_id("object"),
                                "fields": {"OBJECT": object_name.strip(), "MANUAL": ""},
                            }
                        }
                        repairs.append(f"{trail}: moved OBJECT into inputs.OBJECT.object_reference")
                    else:
                        repairs.append(f"{trail}: removed redundant OBJECT field from {block_type}")

            if fields == {}:
                block.pop("fields", None)
            if inputs == {}:
                block.pop("inputs", None)
                inputs = None

            if isinstance(inputs, dict):
                for input_name, connection in inputs.items():
                    if not isinstance(connection, dict):
                        continue
                    for connection_key in ("block", "shadow"):
                        child = connection.get(connection_key)
                        if isinstance(child, dict):
                            normalize_block(child, f"{trail}.inputs.{input_name}.{connection_key}")
            next_connection = block.get("next")
            if isinstance(next_connection, dict):
                child = next_connection.get("block")
                if isinstance(child, dict):
                    normalize_block(child, f"{trail}.next.block")

        for graph_index, graph_workspace in enumerate(cls._all_graph_workspaces(workspace)):
            for root_index, root in enumerate(cls._workspace_roots(graph_workspace)):
                normalize_block(root, f"workspace[{graph_index}].blocks[{root_index}]")
        return normalized, repairs

    @classmethod
    def _graph_block_types(cls, workspace: dict[str, Any]) -> Counter:
        block_types: Counter = Counter()
        nodes = workspace.get("nodes") if isinstance(workspace, dict) else []
        if isinstance(nodes, list):
            for node in nodes:
                if isinstance(node, dict):
                    for block in cls._workspace_blocks(node.get("workspace")):
                        block_type = str(block.get("type") or "").strip()
                        if block_type:
                            block_types[block_type] += 1
        edges = workspace.get("edges") if isinstance(workspace, dict) else []
        if isinstance(edges, list):
            for edge in edges:
                if isinstance(edge, dict):
                    for block in cls._workspace_blocks(edge.get("conditionWorkspace")):
                        block_type = str(block.get("type") or "").strip()
                        if block_type:
                            block_types[block_type] += 1
        for block in cls._workspace_blocks(
            workspace.get("globalVariablesWorkspace") if isinstance(workspace, dict) else None
        ):
            block_type = str(block.get("type") or "").strip()
            if block_type:
                block_types[block_type] += 1
        return block_types

    @staticmethod
    def _actor_names(project_context: dict[str, Any]) -> set[str]:
        actors = project_context.get("actors") if isinstance(project_context, dict) else []
        if not isinstance(actors, list):
            return set()
        return {
            str(actor.get("name") or "").strip()
            for actor in actors
            if isinstance(actor, dict) and str(actor.get("name") or "").strip()
        }

    @staticmethod
    def _contains_chinese(value: Any) -> bool:
        return bool(re.search(r"[\u3400-\u9fff]", str(value or "")))

    @classmethod
    def _validate_actor_references(
        cls, result: dict[str, Any], request: dict[str, Any]
    ) -> None:
        workspace = result.get("workspace") if isinstance(result.get("workspace"), dict) else {}
        project_context = request.get("projectContext")
        actors = project_context.get("actors") if isinstance(project_context, dict) else None
        actor_context_available = isinstance(actors, list)
        known_actors = cls._actor_names(project_context if isinstance(project_context, dict) else {})
        errors: list[str] = []

        for graph_workspace in cls._all_graph_workspaces(workspace):
            for block in cls._workspace_blocks(graph_workspace):
                block_type = str(block.get("type") or "").strip()
                block_id = str(block.get("id") or "").strip() or "<missing-id>"
                for input_name in NodeGraphReviewService.ACTOR_REFERENCE_FIELDS.get(block_type, ()):
                    state, actor_name = NodeGraphReviewService._actor_reference(block, input_name)
                    if state == "missing":
                        errors.append(
                            f"积木 {block_id} ({block_type}) 没有指定对象输入 {input_name}"
                        )
                    elif state == "resolved" and actor_context_available and actor_name not in known_actors:
                        errors.append(
                            f"积木 {block_id} ({block_type}) 引用的对象 {actor_name!r} 不存在于当前场景"
                        )
                    if len(errors) >= 6:
                        break
                if len(errors) >= 6:
                    break
            if len(errors) >= 6:
                break

        if errors:
            raise ValueError("对象引用校验失败：" + "；".join(errors))

    @classmethod
    def _validate_response_language(
        cls, result: dict[str, Any], request: dict[str, Any]
    ) -> None:
        language = request["responseLanguage"]
        summary = str(result.get("summary") or "").strip()
        if language == "zh-CN" and not cls._contains_chinese(summary):
            raise ValueError("中文请求的 summary 必须使用中文")
        if language == "en-US" and cls._contains_chinese(summary):
            raise ValueError("English request summary must use English")

        old_workspace = request.get("workspace") if isinstance(request.get("workspace"), dict) else {}
        new_workspace = result.get("workspace") if isinstance(result.get("workspace"), dict) else {}
        old_nodes = {
            str(node.get("id") or ""): node
            for node in old_workspace.get("nodes", [])
            if isinstance(node, dict) and str(node.get("id") or "")
        }
        for node in new_workspace.get("nodes", []):
            if not isinstance(node, dict) or node.get("nodeType") != "custom":
                continue
            node_id = str(node.get("id") or "")
            label = str(node.get("customName") or node.get("name") or "").strip()
            old = old_nodes.get(node_id)
            old_label = str(old.get("customName") or old.get("name") or "").strip() if old else None
            if old is not None and old_label == label:
                continue
            if language == "zh-CN" and not cls._contains_chinese(label):
                raise ValueError(f"新增或改名的自定义节点必须使用中文：{label or node_id}")
            if language == "en-US" and cls._contains_chinese(label):
                raise ValueError(f"New or renamed custom node must use English: {label or node_id}")

        old_edges = {
            str(edge.get("id") or ""): edge
            for edge in old_workspace.get("edges", [])
            if isinstance(edge, dict) and str(edge.get("id") or "")
        }
        for edge in new_workspace.get("edges", []):
            if not isinstance(edge, dict):
                continue
            edge_id = str(edge.get("id") or "")
            label = str(edge.get("name") or "").strip()
            old = old_edges.get(edge_id)
            old_label = str(old.get("name") or "").strip() if old else None
            if not label or (old is not None and old_label == label):
                continue
            if language == "zh-CN" and not cls._contains_chinese(label):
                raise ValueError(f"新增或改名的连线名称必须使用中文：{label}")
            if language == "en-US" and cls._contains_chinese(label):
                raise ValueError(f"New or renamed edge name must use English: {label}")

    @classmethod
    def _validate_requested_semantics(
        cls, result: dict[str, Any], request: dict[str, Any]
    ) -> None:
        requirements = cls._instruction_requirements(request["instruction"])
        required = set(requirements["requiredCapabilities"])
        if not required:
            return

        workspace = result["workspace"]
        actor_names = cls._actor_names(request.get("projectContext") or {})
        matching_chain = None
        movement_types = {"object_third_person_move"}
        if requirements["firstPersonRequested"]:
            movement_types.add("object_first_person_move")
        for node in workspace.get("nodes", []):
            if not isinstance(node, dict):
                continue
            for root in cls._workspace_roots(node.get("workspace")):
                if root.get("type") != "node_while_active":
                    continue
                do_input = root.get("inputs", {}).get("DO", {}) if isinstance(root.get("inputs"), dict) else {}
                first = do_input.get("block") if isinstance(do_input, dict) else None
                chain = list(cls._walk_block(first)) if isinstance(first, dict) else []
                movements = [block for block in chain if block.get("type") in movement_types]
                jumps = [block for block in chain if block.get("type") == "object_arcade_jump"]
                has_movement = bool(movements)
                has_jump = bool(jumps)
                if (("wasd-object-movement" not in required or has_movement)
                    and ("space-object-jump" not in required or has_jump)):
                    matching_chain = (movements, jumps)
                    break
            if matching_chain:
                break

        if not matching_chain:
            missing = []
            if "wasd-object-movement" in required:
                missing.append("node_while_active 中的 object_third_person_move")
            if "space-object-jump" in required:
                missing.append("同一执行链中的 object_arcade_jump")
            raise ValueError("生成结果没有实现用户要求：缺少" + "和".join(missing))

        movements, jumps = matching_chain
        targets = []
        for block in movements + jumps:
            fields = block.get("fields") if isinstance(block.get("fields"), dict) else {}
            targets.append(str(fields.get("NAME") or "").strip())
        if not targets or any(not target for target in targets):
            raise ValueError("WASD 移动和跳跃积木必须指定一个真实对象")
        if len(set(targets)) != 1:
            raise ValueError("WASD 移动和空格跳跃必须绑定同一个对象")
        if targets[0] not in actor_names:
            raise ValueError(f"控制对象 {targets[0]} 不存在于当前场景")

        if requirements["narrowObjectControl"]:
            before = cls._graph_block_types(request["workspace"])
            after = cls._graph_block_types(workspace)
            prohibited = {"ui_set_score", "ui_add_score", "ui_set_lives", "ui_game_win", "ui_game_over"}
            newly_added = after - before
            bad_types = sorted(
                block_type
                for block_type, count in newly_added.items()
                if count > 0 and (block_type in prohibited or block_type.startswith("combat_"))
            )
            if bad_types:
                raise ValueError("局部对象控制请求不应新增计分、生命、胜负或战斗模板：" + ", ".join(bad_types))
            old_count = len(request["workspace"].get("nodes") or [])
            new_count = len(workspace.get("nodes") or [])
            if new_count - old_count > 2:
                raise ValueError("局部对象控制请求新增了过多节点，请只修改最小必要逻辑")

    @classmethod
    def _validate_operation_scope(
        cls, result: dict[str, Any], request: dict[str, Any]
    ) -> None:
        operation = request.get("operation")
        if operation not in {"extend", "edit"}:
            return
        before = request.get("workspace") if isinstance(request.get("workspace"), dict) else {}
        after = result.get("workspace") if isinstance(result.get("workspace"), dict) else {}

        def ids(workspace: dict[str, Any], key: str) -> set[str]:
            return {
                str(item.get("id") or "").strip()
                for item in (workspace.get(key) or [])
                if isinstance(item, dict) and str(item.get("id") or "").strip()
            }

        missing_nodes = sorted(ids(before, "nodes") - ids(after, "nodes"))
        missing_edges = sorted(ids(before, "edges") - ids(after, "edges"))
        if missing_nodes or missing_edges:
            details = []
            if missing_nodes:
                details.append("nodes=" + ",".join(missing_nodes[:6]))
            if missing_edges:
                details.append("edges=" + ",".join(missing_edges[:6]))
            raise ValueError(
                "Incremental edit removed existing structures without an explicit delete request: "
                + "; ".join(details)
            )
        if operation == "edit" and before == after:
            raise ValueError("The edit request did not change any node logic")

    @classmethod
    def _validate_result(
        cls, result: dict[str, Any], request: dict[str, Any], contract_path: Path
    ) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise ValueError("DeepSeek 必须返回一个 JSON 对象")
        for key in ("requestId", "targetId", "projectScopeId", "baseGraphRevision", "operation"):
            if str(result.get(key) or "") != str(request.get(key) or ""):
                raise ValueError(f"DeepSeek 返回的 {key} 与当前请求不一致")
        if result.get("schemaVersion") != 1 or isinstance(result.get("schemaVersion"), bool):
            raise ValueError("DeepSeek 返回的 schemaVersion 必须为 1")
        summary = str(result.get("summary") or "").strip()
        if not summary:
            raise ValueError("DeepSeek 返回结果缺少 summary")
        forbidden = cls._contains_forbidden_key(result)
        if forbidden:
            raise ValueError(f"DeepSeek 返回了禁止字段：{forbidden}")

        normalized_result, normalization_warnings = cls._normalize_model_block_serialization(
            result, contract_path
        )
        validated = validate_generated_node_graph(normalized_result, catalog_path=contract_path)
        if validated.get("success") is not True:
            errors = validated.get("errors") or []
            detail = "；".join(str(item) for item in errors[:6])
            raise ValueError("生成的节点图未通过积木合同校验" + (f"：{detail}" if detail else ""))
        cls._validate_response_language(normalized_result, request)
        cls._validate_actor_references(normalized_result, request)
        cls._validate_operation_scope(normalized_result, request)
        cls._validate_requested_semantics(normalized_result, request)
        return {
            "schemaVersion": 1,
            "requestId": request["requestId"],
            "targetId": cls.TARGET_ID,
            "projectScopeId": request["projectScopeId"],
            "baseGraphRevision": request["baseGraphRevision"],
            "operation": request["operation"],
            "summary": summary[:600],
            "workspace": normalized_result["workspace"],
            "warnings": normalization_warnings + list(validated.get("warnings") or []),
        }

    def generate(self, payload: Any, cancel_event: threading.Event | None = None) -> dict[str, Any]:
        try:
            request = self._normalize_payload(payload)
            if cancel_event and cancel_event.is_set():
                return self._error("GENERATION_CANCELLED", "已停止本次节点生成。")
            settings = NodeGraphReviewService._resolve_settings()
            if not settings.api_key:
                return self._error("AI_NOT_CONFIGURED", "DeepSeek 未配置，无法生成节点逻辑。")
            contract_path, contract_text = self._load_contract()
            prompt = self._build_prompt(request, contract_text)
            normalized = None
            validation_error = None
            for attempt in range(2):
                current_prompt = prompt
                if validation_error is not None:
                    current_prompt += (
                        "\n\nPREVIOUS_RESULT_REJECTED:\n"
                        + str(validation_error)
                        + "\nReturn a corrected complete JSON result. Do not repeat the rejected structure."
                    )
                raw = self._call_deepseek(settings, current_prompt)
                if cancel_event and cancel_event.is_set():
                    return self._error("GENERATION_CANCELLED", "已停止本次节点生成。")
                try:
                    result = NodeGraphReviewService._parse_model_result(raw)
                    normalized = self._validate_result(result, request, contract_path)
                    break
                except ValueError as exc:
                    validation_error = exc
                    if attempt == 0:
                        logger.info("Retrying rejected node graph generation: %s", exc)
                        continue
                    raise
            if normalized is None:
                raise validation_error or ValueError("DeepSeek 没有返回可应用的节点图")
            logger.info(
                "Node graph generation completed [source=%s, model=%s, operation=%s, revision=%s, nodes=%d, edges=%d]",
                settings.source,
                settings.model,
                request["operation"],
                request["baseGraphRevision"][:12],
                len(normalized["workspace"].get("nodes") or []),
                len(normalized["workspace"].get("edges") or []),
            )
            return {"success": True, "status": "ok", **normalized}
        except ValueError as exc:
            logger.warning("Node graph generation rejected: %s", exc)
            return self._error("INVALID_GENERATION_DATA", str(exc))
        except urllib.error.HTTPError as exc:
            status = int(getattr(exc, "code", 0) or 0)
            logger.warning("Node graph generation provider HTTP error [status=%s]", status)
            if status in (401, 403):
                return self._error("AI_AUTH_FAILED", "DeepSeek 身份验证失败，请检查现有 AI 配置。")
            if status == 429:
                return self._error("AI_RATE_LIMITED", "DeepSeek 请求过于频繁，请稍后再试。")
            return self._error("AI_PROVIDER_ERROR", f"DeepSeek 服务暂时不可用（HTTP {status}）。")
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            logger.warning("Node graph generation network error")
            return self._error("AI_NETWORK_ERROR", "暂时无法连接 DeepSeek，当前节点图没有被修改。")
        except Exception as exc:
            logger.exception("Node graph generation failed: %s", type(exc).__name__)
            return self._error("AI_GENERATION_FAILED", "节点逻辑生成失败，当前节点图没有被修改。")

    def start(self, payload: Any) -> dict[str, Any]:
        try:
            request = self._normalize_payload(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            return self._error("INVALID_GENERATION_REQUEST", str(exc))
        with self._lock:
            if self._closed:
                return self._error("GENERATION_SERVICE_CLOSED", "节点生成服务已经关闭。")
            self._prune_locked()
            task_id = f"node_generate_task_{uuid.uuid4().hex}"
            cancel_event = threading.Event()
            self._tasks[task_id] = {
                "taskId": task_id,
                "requestId": request["requestId"],
                "status": "pending",
                "createdAt": time.time(),
                "updatedAt": time.time(),
                "cancel": cancel_event,
            }
            future = self._executor.submit(self.generate, request, cancel_event)
            future.add_done_callback(lambda completed, current=task_id: self._complete(current, completed))
        return {"success": True, "status": "pending", "taskId": task_id, "requestId": request["requestId"]}

    def _complete(self, task_id: str, future: Any) -> None:
        try:
            result = future.result()
        except Exception:
            logger.exception("Background node graph generation failed")
            result = self._error("AI_GENERATION_FAILED", "节点逻辑生成失败，当前节点图没有被修改。")
        with self._lock:
            state = self._tasks.get(task_id)
            if not state:
                return
            if state["cancel"].is_set():
                state["status"] = "cancelled"
                state["message"] = "已停止本次节点生成。"
            else:
                state["status"] = "completed"
                state["result"] = result
            state["updatedAt"] = time.time()

    def status(self, task_id: str) -> dict[str, Any]:
        key = str(task_id or "").strip()
        if not key:
            return self._error("INVALID_TASK_ID", "缺少节点生成任务 ID。")
        with self._lock:
            state = self._tasks.get(key)
            if not state:
                return self._error("GENERATION_TASK_NOT_FOUND", "节点生成任务不存在或已经过期。")
            response = {
                "success": True,
                "status": state["status"],
                "taskId": state["taskId"],
                "requestId": state["requestId"],
            }
            if state["status"] == "completed":
                response["result"] = json.loads(json.dumps(state.get("result") or {}, ensure_ascii=False))
            if state["status"] == "cancelled":
                response["message"] = str(state.get("message") or "已停止本次节点生成。")
            return response

    def cancel(self, task_id: str) -> dict[str, Any]:
        key = str(task_id or "").strip()
        if not key:
            return self._error("INVALID_TASK_ID", "缺少节点生成任务 ID。")
        with self._lock:
            state = self._tasks.get(key)
            if not state:
                return self._error("GENERATION_TASK_NOT_FOUND", "节点生成任务不存在或已经过期。")
            state["cancel"].set()
            if state["status"] != "completed":
                state["status"] = "cancelled"
                state["message"] = "已停止本次节点生成。"
                state["updatedAt"] = time.time()
        return {"success": True, "status": "cancelled", "taskId": key}

    def _prune_locked(self) -> None:
        if len(self._tasks) < self.MAX_TASKS:
            return
        finished = sorted(
            (
                (task_id, state)
                for task_id, state in self._tasks.items()
                if state.get("status") in {"completed", "cancelled"}
            ),
            key=lambda item: float(item[1].get("updatedAt") or item[1].get("createdAt") or 0),
        )
        while len(self._tasks) >= self.MAX_TASKS and finished:
            task_id, _ = finished.pop(0)
            self._tasks.pop(task_id, None)

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for state in self._tasks.values():
                state["cancel"].set()
        self._executor.shutdown(wait=False, cancel_futures=True)


_service: NodeGraphGenerationService | None = None
_service_lock = threading.Lock()


def get_node_graph_generation_service() -> NodeGraphGenerationService:
    global _service
    with _service_lock:
        if _service is None:
            _service = NodeGraphGenerationService()
        return _service
