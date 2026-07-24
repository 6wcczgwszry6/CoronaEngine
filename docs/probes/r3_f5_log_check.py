"""Read-only R3 evidence probe for Corona F5 logs.

Usage:
    python docs/probes/r3_f5_log_check.py [path/to/*_corona.log]
        --history path/to/LANChat/history.jsonl
    python docs/probes/r3_f5_log_check.py --profile control-plane --history history.jsonl log
    python docs/probes/r3_f5_log_check.py --profile scene-runtime log
    python docs/probes/r3_f5_log_check.py --json [path/to/*_corona.log]

The probe consumes structured ``R3GateTrace`` and ``LANChatRuntimeEvidence``
lines. It never imports AgentRuntime and never mutates Runtime or Engine state.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_DIR = REPO_ROOT / "build" / "examples" / "engine" / "RelWithDebInfo" / "logs"

R3_DIMENSIONS = (
    "snapshot_integrity",
    "environment_readiness",
    "entity_readiness",
    "finalizer_completeness",
    "business_graph_consistency",
    "multiplayer_consistency",
    "runtime_write_safety",
)
KEY_VALUE_RE = re.compile(r"(?P<key>[a-zA-Z_]+)=(?P<value>[^\s]+)")
BATCH_RE = re.compile(r"batches=total:(\d+),active:(\d+),terminal:(\d+)")
GRAPH_RE = re.compile(r"graphs=business:(\d+),internal:(\d+),active:(\d+),terminal:(\d+)")
DRAIN_RE = re.compile(r"drain=status:([^,\s]+),drained:(\d+)")
RATIO_RE = re.compile(r"^(\d+)/(\d+)$")
THREAD_RE = re.compile(r"\]\[(?P<thread>\d+)\]\[(?:TRACE|DEBUG|INFO|WARNING|ERROR)\]")
PLAN_REF_RE = re.compile(
    r"\b(?:plan|seed)-(?=[A-Za-z0-9_.-]{6,}\b)(?=[A-Za-z0-9_.-]*\d)[A-Za-z0-9_.-]+\b"
)
ARTIFACT_REF_RE = re.compile(
    r"\b(?:artifact[-_:][A-Za-z0-9_.-]+|legacy-plan:[A-Za-z0-9_.-]+)\b",
    re.IGNORECASE,
)
ENTITY_FRAGMENT_RE = re.compile(r"准备生成模型[：:]\s*([^\r\n。；;]+)")
CURRENT_PLAN_RE = re.compile(r"当前方案[：:]\s*(plan-[A-Za-z0-9_.-]+)")
PLAN_OWNER_RE = re.compile(r"\bowner\s+([^,，\r\n]+)", re.IGNORECASE)

FINAL_REPLY_KINDS = frozenset({"agent_reply", "final_reply"})
B7_1_EXPECTED_TURNS = (
    ("@小女孩 围绕迪士尼乐园主题讨论一下", "小女孩", 1, ("agent_visible_reasoning",), False),
    (
        "@小女孩 按照迪士尼风格的卧室来设计呢",
        "小女孩",
        4,
        (
            "planning_artifact_reasoning",
            "program_artifact_reasoning",
            "art_artifact_reasoning",
            "collaboration_proposal_narration",
        ),
        True,
    ),
    ("@GM 确认生成", "GM", 0, (), True),
    (
        "@长者 请你给出一个方案",
        "长者",
        4,
        (
            "planning_artifact_reasoning",
            "program_artifact_reasoning",
            "art_artifact_reasoning",
            "collaboration_proposal_narration",
        ),
        True,
    ),
    ("@长者 确认开始", "长者", 0, (), True),
    ("@小女孩 你好", "小女孩", 1, ("agent_visible_reasoning",), False),
)
B7_1_EXPECTED_REPLY_CONTRACTS = {
    "@小女孩 围绕迪士尼乐园主题讨论一下": "discussion_reply",
    "@小女孩 按照迪士尼风格的卧室来设计呢": "planning_proposal",
    "@GM 确认生成": "runtime_write_blocked",
    "@长者 请你给出一个方案": "planning_proposal",
    "@长者 确认开始": "runtime_write_blocked",
    "@小女孩 你好": "discussion_reply",
}
B7_1_EXPECTED_INTENTS = {
    "@小女孩 围绕迪士尼乐园主题讨论一下": "discussion",
    "@小女孩 按照迪士尼风格的卧室来设计呢": "plan_drafting",
    "@GM 确认生成": "generation_start",
    "@长者 请你给出一个方案": "plan_drafting",
    "@长者 确认开始": "generation_start",
    "@小女孩 你好": "discussion",
}
GREETING_TURN_TEXT = "@小女孩 你好"
GREETING_REPLY_MARKERS = ("你好", "嗨", "在的", "很高兴", "想聊", "可以聊")
CONFIRMATION_SOURCE_TURN = {
    "@GM 确认生成": "@小女孩 按照迪士尼风格的卧室来设计呢",
    "@长者 确认开始": "@长者 请你给出一个方案",
}
CONTROL_PHASES = frozenset(
    {
        "native_queue_pop",
        "received",
        "route_start",
        "planning_gate_handled",
        "trigger_pop",
        "process_start",
        "message_dispatch_deduped",
        "send_agent_reply_ex",
        "agent_trigger_planning_seeded",
        "agent_reply_context_recorded",
    }
)
TEMPLATE_MARKERS = ("方案内容", "建议先做", "你可以回复")
PROMPT_LEAK_MARKERS = (
    "你是三职能协作的 GM",
    "output_schema",
    "game_design_brief",
    "gameplay_logic_plan",
    "SceneCompositionPlan",
    "RuntimeGuard",
    "ToolCallGraph",
)
DIAGNOSTIC_MARKERS = ("【Runtime 状态】", "RuntimeGuard:", "ToolCallGraph：", "Worker drain replay:")


@dataclass(frozen=True)
class Check:
    level: str
    name: str
    detail: str


@dataclass(frozen=True)
class RuntimeEvidence:
    plan_id: str
    batch_total: int
    batch_active: int
    batch_terminal: int
    business_graphs: int
    internal_graphs: int
    graph_active: int
    graph_terminal: int
    drain_status: str
    drained_count: int

    @property
    def terminal(self) -> bool:
        return (
            self.batch_total > 0
            and self.batch_active == 0
            and self.batch_terminal == self.batch_total
            and self.graph_active == 0
            and self.graph_terminal == self.business_graphs
        )


@dataclass(frozen=True)
class TurnEvidence:
    message_id: str
    correlation_id: str
    room_id: str
    text: str
    expected_target_id: str
    expected_target_name: str
    routes: tuple[str, ...]
    processing_owners: tuple[str, ...]
    final_reply_count: int
    actual_reply_senders: tuple[str, ...]
    reply_contracts: tuple[str, ...]
    resolved_intents: tuple[str, ...]
    progress_count: int
    action_status_count: int
    model_call_count: int | None
    model_call_purposes: tuple[str, ...]
    model_call_elapsed_ms: tuple[int, ...]
    model_call_total_elapsed_ms: int
    model_call_observability: str
    plan_refs: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    proposal_ids: tuple[str, ...]
    proposal_versions: tuple[int, ...]
    proposal_hashes: tuple[str, ...]
    artifact_bundle_refs: tuple[str, ...]
    reply_texts: tuple[str, ...]
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class MediaLineageEvidence:
    line_number: int
    phase: str
    plan_id: str
    batch_id: str
    asset_id: str
    image_mode: str
    image_ref: str
    image_hash: str
    image_source: str
    model_mode: str
    source_image_ref: str
    source_image_hash: str
    model_ref: str
    actor_id: str
    actor_source: str
    actor_status: str


@dataclass(frozen=True)
class SessionControlEvidence:
    history_message_count: int
    user_turn_count: int
    message_kind_counts: dict[str, int]
    duplicate_heartbeat_count: int
    duplicate_heartbeat_text: str
    invalid_entity_fragments: tuple[str, ...]
    finalizer_disclosure_sequence: tuple[str, ...]
    finalizer_disclosure_order_violation: bool
    quasar_import_roots: tuple[str, ...]
    explicit_model_purpose_count: int
    explicit_model_summary_count: int
    inferred_model_purpose_count: int
    mojibake_sender_count: int
    diagnostic_dump_count: int
    contradictory_turn_ids: tuple[str, ...]
    plan_owner_mismatches: tuple[str, ...]
    native_defer_mutation_message_ids: tuple[str, ...]
    terminal_disclosure_violation_count: int
    terminal_key_duplicate_count: int


def _latest_log() -> Path:
    candidates = sorted(DEFAULT_LOG_DIR.glob("*_corona.log"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"no *_corona.log found under {DEFAULT_LOG_DIR}")
    return candidates[-1]


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def _read_history(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    messages: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, raw in enumerate(_read_lines(path), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"line {line_number}: expected object")
            continue
        messages.append(value)
    messages.sort(key=lambda item: (int(item.get("seq") or 0), int(item.get("timestamp_ms") or 0)))
    return messages, errors


def _fields(line: str) -> dict[str, str]:
    return {match.group("key"): match.group("value") for match in KEY_VALUE_RE.finditer(line)}


def _metadata(message: dict[str, Any]) -> dict[str, Any]:
    raw = message.get("metadata_json")
    if isinstance(raw, dict):
        return dict(raw)
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return dict(value) if isinstance(value, dict) else {}


def _append_unique(values: list[str], value: str) -> None:
    normalized = str(value or "").strip()
    if normalized and normalized not in values:
        values.append(normalized)


def _thread_id(line: str) -> str:
    match = THREAD_RE.search(line)
    return match.group("thread") if match else ""


def _looks_like_command_fragment(value: str) -> bool:
    text = str(value or "").strip()
    markers = ("请", "确认", "开始", "方案", "讨论", "生成", "完成", "有没有")
    return sum(marker in text for marker in markers) >= 2


def _message_is_linked(message: dict[str, Any], turn: dict[str, Any]) -> bool:
    metadata = _metadata(message)
    reply_to = str(metadata.get("reply_to") or "")
    message_id = str(turn.get("message_id") or "")
    correlation_id = str(turn.get("correlation_id") or "")
    message_correlation = str(message.get("correlation_id") or "")
    return bool(
        (reply_to and reply_to == message_id)
        or (message_correlation and message_correlation in {message_id, correlation_id})
    )


def _is_final_business_reply(message: dict[str, Any], turn: dict[str, Any]) -> bool:
    kind = str(message.get("message_kind") or "").lower()
    if kind in FINAL_REPLY_KINDS:
        return True
    if kind != "gm_proposal" or not _message_is_linked(message, turn):
        return False
    metadata = _metadata(message)
    return bool(
        str(metadata.get("reply_to") or "") == str(turn.get("message_id") or "")
        and str(metadata.get("reply_contract") or "") == "planning_proposal"
    )


def _normalize_turn_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _plan_owners(messages: Iterable[dict[str, Any]]) -> dict[str, str]:
    owners: dict[str, str] = {}
    for message in messages:
        text = str(message.get("text") or "")
        plan_match = CURRENT_PLAN_RE.search(text)
        owner_match = PLAN_OWNER_RE.search(text)
        if plan_match and owner_match:
            owners[plan_match.group(1)] = owner_match.group(1).strip()
    return owners


def _log_control_evidence(lines: Iterable[str]) -> tuple[dict[str, dict[str, list[str]]], dict[str, Any]]:
    by_message: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {
            "routes": [],
            "processing_owners": [],
            "model_call_counts": [],
            "model_call_purposes": [],
            "model_call_elapsed_ms": [],
            "plan_refs": [],
            "artifact_refs": [],
            "native_defer": [],
            "native_mutations": [],
            "control_runtime_mutations": [],
            "late_model_results": [],
        }
    )
    active_message_by_thread: dict[str, str] = {}
    quasar_roots: list[str] = []
    explicit_model_purpose_count = 0
    explicit_model_summary_count = 0
    inferred_model_purpose_count = 0
    terminal_disclosure_violation_count = 0

    for line in lines:
        fields = _fields(line)
        phase = str(fields.get("phase") or "")
        source = str(fields.get("source") or "")
        thread_id = _thread_id(line)
        message_id = str(fields.get("message_id") or "")
        is_history_replay = source == "lanchat_history_snapshot"
        if message_id and not is_history_replay:
            active_message_by_thread[thread_id] = message_id
        elif not message_id and thread_id:
            message_id = active_message_by_thread.get(thread_id, "")

        if "plugins.AITool.Quasar." in line:
            _append_unique(quasar_roots, "plugins.AITool.Quasar")
        if re.search(r"\[Python\]\s+Quasar\.", line):
            _append_unique(quasar_roots, "Quasar")
        if "phase=terminal_order_violation" in line or "runtime_event_disclosure_terminal_violation" in line:
            terminal_disclosure_violation_count += 1

        if not message_id:
            continue
        evidence = by_message[message_id]
        if "[LANChatModelCallSummary]" in line:
            try:
                call_count = max(0, int(fields.get("calls", "0")))
            except (TypeError, ValueError):
                call_count = -1
            if call_count >= 0:
                evidence["model_call_counts"].append(str(call_count))
                explicit_model_summary_count += 1
        if "[LANChatModelCallResult]" in line:
            try:
                elapsed_ms = max(0, int(fields.get("elapsed_ms", "0")))
            except (TypeError, ValueError):
                elapsed_ms = -1
            if elapsed_ms >= 0:
                evidence["model_call_elapsed_ms"].append(str(elapsed_ms))
        if "[LANChatModelCallLateResult]" in line:
            _append_unique(evidence["late_model_results"], str(fields.get("stage_token") or "late"))
        if phase in CONTROL_PHASES:
            route = f"{source}:{phase}" if source else phase
            _append_unique(evidence["routes"], route)
        if "[LANChatDispatchLedger]" in line and phase == "execution_claimed":
            _append_unique(evidence["processing_owners"], str(fields.get("owner") or ""))
        if phase in {"native_observer_deferred", "defer_structured_agent_route"}:
            _append_unique(evidence["native_defer"], phase)
        if source == "lanchat_native_queue" and phase in {
            "authoritative_ingest",
            "route_start",
            "authoritative_only_done",
            "planning_gate_handled",
        }:
            _append_unique(evidence["native_mutations"], phase)
        if phase in {
            "planning_context_recorded",
            "user_context_recorded",
            "agent_reply_context_recorded",
            "agent_trigger_planning_seeded",
        }:
            _append_unique(evidence["control_runtime_mutations"], phase)

        purpose = str(fields.get("purpose") or "")
        if purpose:
            _append_unique(evidence["model_call_purposes"], f"explicit:{purpose}")
            explicit_model_purpose_count += 1
        elif phase == "agent_trigger_planning_seeded":
            intent = str(fields.get("intent") or "unknown")
            _append_unique(evidence["model_call_purposes"], f"inferred:plan_context/{intent}")
            inferred_model_purpose_count += 1
        elif "[MasterAgent] __call__" in line:
            _append_unique(evidence["model_call_purposes"], "inferred:agent_reply")
            inferred_model_purpose_count += 1

        for plan_ref in PLAN_REF_RE.findall(line):
            _append_unique(evidence["plan_refs"], plan_ref)
        for artifact_ref in ARTIFACT_REF_RE.findall(line):
            _append_unique(evidence["artifact_refs"], artifact_ref)

    return dict(by_message), {
        "quasar_import_roots": tuple(quasar_roots),
        "explicit_model_purpose_count": explicit_model_purpose_count,
        "explicit_model_summary_count": explicit_model_summary_count,
        "inferred_model_purpose_count": inferred_model_purpose_count,
        "terminal_disclosure_violation_count": terminal_disclosure_violation_count,
    }


def _control_evidence(
    lines: list[str],
    messages: list[dict[str, Any]],
) -> tuple[list[TurnEvidence], SessionControlEvidence]:
    log_evidence, log_session = _log_control_evidence(lines)
    plan_owners = _plan_owners(messages)
    turns: list[TurnEvidence] = []
    contradictory_turn_ids: list[str] = []
    plan_owner_mismatches: list[str] = []
    native_defer_mutation_message_ids: list[str] = []

    user_turns = [
        message
        for message in messages
        if str(message.get("sender_type") or "").lower() in {"user", "host"}
        and str(message.get("message_kind") or "chat").lower() == "chat"
    ]
    for turn in user_turns:
        message_id = str(turn.get("message_id") or "")
        correlation_id = str(turn.get("correlation_id") or "")
        metadata = _metadata(turn)
        expected_target_id = str(metadata.get("target_agent_id") or turn.get("target_agent_id") or "")
        expected_target_name = str(metadata.get("target_agent_name") or "")
        linked = [message for message in messages if _message_is_linked(message, turn)]
        final_replies = [
            message
            for message in linked
            if _is_final_business_reply(message, turn)
        ]
        progress = [message for message in linked if str(message.get("message_kind") or "").lower() == "progress"]
        action_status = [
            message for message in linked if str(message.get("message_kind") or "").lower() == "action_status"
        ]
        actual_reply_senders = tuple(str(message.get("sender_name") or message.get("sender_id") or "") for message in final_replies)
        reply_contracts: list[str] = []
        resolved_intents: list[str] = []
        evidence = log_evidence.get(message_id, {})
        plan_refs: list[str] = list(evidence.get("plan_refs") or [])
        artifact_refs: list[str] = list(evidence.get("artifact_refs") or [])
        proposal_ids: list[str] = []
        proposal_versions: list[int] = []
        proposal_hashes: list[str] = []
        artifact_bundle_refs: list[str] = []
        reply_texts: list[str] = []
        invalid_fragments: list[str] = []
        for message in linked:
            text = str(message.get("text") or "")
            reply_metadata = _metadata(message)
            if _is_final_business_reply(message, turn):
                reply_texts.append(text)
            _append_unique(reply_contracts, str(reply_metadata.get("reply_contract") or ""))
            _append_unique(resolved_intents, str(reply_metadata.get("resolved_intent") or ""))
            for key in ("proposal_id", "agent_plan_id", "runtime_plan_id"):
                value = str(reply_metadata.get(key) or "")
                if value:
                    _append_unique(plan_refs, value)
            _append_unique(proposal_ids, str(reply_metadata.get("proposal_id") or ""))
            try:
                proposal_version = int(reply_metadata.get("proposal_version") or 0)
            except (TypeError, ValueError):
                proposal_version = 0
            if proposal_version > 0 and proposal_version not in proposal_versions:
                proposal_versions.append(proposal_version)
            _append_unique(proposal_hashes, str(reply_metadata.get("proposal_hash") or ""))
            raw_artifact_refs = reply_metadata.get("artifact_refs")
            if isinstance(raw_artifact_refs, (list, tuple)):
                for artifact_ref in raw_artifact_refs:
                    _append_unique(artifact_bundle_refs, str(artifact_ref or ""))
            _append_unique(artifact_refs, str(reply_metadata.get("artifact_ref") or ""))
            for plan_ref in PLAN_REF_RE.findall(text):
                _append_unique(plan_refs, plan_ref)
            for artifact_ref in ARTIFACT_REF_RE.findall(text):
                _append_unique(artifact_refs, artifact_ref)
            for fragment in ENTITY_FRAGMENT_RE.findall(text):
                if _looks_like_command_fragment(fragment):
                    _append_unique(invalid_fragments, fragment)

        diagnostics: list[str] = []
        if len(final_replies) > 1:
            diagnostics.append("multiple_final_replies")
        if expected_target_name:
            mismatched_senders = []
            for message in final_replies:
                sender = str(message.get("sender_name") or message.get("sender_id") or "")
                metadata = _metadata(message)
                authoritative_gm = bool(
                    sender.upper() == "GM"
                    and str(metadata.get("reply_contract") or "") in {
                        "planning_proposal",
                        "generation_confirmation",
                        "runtime_write_blocked",
                        "collaboration_blocked",
                    }
                )
                if sender != expected_target_name and not authoritative_gm:
                    mismatched_senders.append(sender)
            if mismatched_senders:
                diagnostics.append("reply_target_mismatch")
        processing_owners = tuple(evidence.get("processing_owners") or ())
        if len(processing_owners) > 1:
            diagnostics.append("multiple_processing_owners")
        if not processing_owners:
            diagnostics.append("formal_processing_owner_missing")
        if evidence.get("native_defer") and evidence.get("native_mutations"):
            diagnostics.append("native_defer_after_business_mutation")
            _append_unique(native_defer_mutation_message_ids, message_id)
        control_only_reply = bool(
            set(reply_contracts) & {"discussion_reply", "collaboration_blocked"}
        )
        if control_only_reply and evidence.get("control_runtime_mutations"):
            diagnostics.append("control_plane_runtime_mutation")
        if evidence.get("late_model_results"):
            diagnostics.append("late_model_result_discarded")
        if invalid_fragments:
            diagnostics.append("command_fragment_used_as_entity")
        if len(final_replies) > 1 and all(
            sum(marker in str(reply.get("text") or "") for marker in TEMPLATE_MARKERS) >= 2
            for reply in final_replies
        ):
            diagnostics.append("duplicate_template_reply")

        status_text = "\n".join(str(message.get("text") or "") for message in action_status)
        reply_text = "\n".join(str(message.get("text") or "") for message in final_replies)
        if "已更新当前 Runtime 方案" in status_text and (
            "请先在聊天室形成并确认方案" in reply_text or "方案尚未形成" in reply_text
        ):
            diagnostics.append("runtime_reply_contradiction")
            contradictory_turn_ids.append(message_id)

        if any(marker in str(turn.get("text") or "") for marker in ("确认", "开始", "生成")):
            for plan_ref in plan_refs:
                owner = plan_owners.get(plan_ref, "")
                if owner and expected_target_name and expected_target_name.upper() != "GM" and owner != expected_target_name:
                    mismatch = f"{message_id}:{plan_ref}:{owner}->{expected_target_name}"
                    _append_unique(plan_owner_mismatches, mismatch)
                    diagnostics.append("plan_owner_mismatch")

        model_call_purposes = tuple(evidence.get("model_call_purposes") or ())
        model_call_counts = tuple(evidence.get("model_call_counts") or ())
        model_call_elapsed_ms = tuple(
            int(value)
            for value in tuple(evidence.get("model_call_elapsed_ms") or ())
        )
        model_call_count = int(model_call_counts[-1]) if model_call_counts else None
        if model_call_count is not None or any(value.startswith("explicit:") for value in model_call_purposes):
            model_observability = "explicit"
        elif model_call_purposes:
            model_observability = "inferred"
        else:
            model_observability = "missing"
        turns.append(
            TurnEvidence(
                message_id=message_id,
                correlation_id=correlation_id,
                room_id=str(turn.get("room_id") or ""),
                text=str(turn.get("text") or ""),
                expected_target_id=expected_target_id,
                expected_target_name=expected_target_name,
                routes=tuple(evidence.get("routes") or ()),
                processing_owners=processing_owners,
                final_reply_count=len(final_replies),
                actual_reply_senders=actual_reply_senders,
                reply_contracts=tuple(reply_contracts),
                resolved_intents=tuple(resolved_intents),
                progress_count=len(progress),
                action_status_count=len(action_status),
                model_call_count=model_call_count,
                model_call_purposes=model_call_purposes,
                model_call_elapsed_ms=model_call_elapsed_ms,
                model_call_total_elapsed_ms=sum(model_call_elapsed_ms),
                model_call_observability=model_observability,
                plan_refs=tuple(plan_refs),
                artifact_refs=tuple(artifact_refs),
                proposal_ids=tuple(proposal_ids),
                proposal_versions=tuple(proposal_versions),
                proposal_hashes=tuple(proposal_hashes),
                artifact_bundle_refs=tuple(artifact_bundle_refs),
                reply_texts=tuple(reply_texts),
                diagnostics=tuple(diagnostics),
            )
        )

    status_messages = [
        message
        for message in messages
        if str(message.get("message_kind") or "").lower() in {"action_status", "progress"}
    ]
    heartbeat_counts = Counter(str(message.get("text") or "").strip() for message in status_messages)
    heartbeat_text, heartbeat_count = ("", 0)
    if heartbeat_counts:
        candidate_text, candidate_count = heartbeat_counts.most_common(1)[0]
        if candidate_count > 1:
            heartbeat_text, heartbeat_count = candidate_text, candidate_count

    invalid_entity_fragments: list[str] = []
    for message in messages:
        for fragment in ENTITY_FRAGMENT_RE.findall(str(message.get("text") or "")):
            if _looks_like_command_fragment(fragment):
                _append_unique(invalid_entity_fragments, fragment)

    disclosure_sequence: list[str] = []
    terminal_groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for message in messages:
        text = str(message.get("text") or "")
        sequence = int(message.get("seq") or 0)
        metadata = _metadata(message)
        runtime_event = metadata.get("runtime_event")
        if not isinstance(runtime_event, dict):
            runtime_event = metadata.get("progress_event")
        runtime_event = runtime_event if isinstance(runtime_event, dict) else {}
        payload = runtime_event.get("payload")
        if not isinstance(payload, dict):
            payload = runtime_event.get("detail")
        payload = payload if isinstance(payload, dict) else {}
        event_type = str(runtime_event.get("event_type") or "")
        terminal_key = str(payload.get("terminal_key") or "").strip()
        if not terminal_key:
            plan_id = str(runtime_event.get("plan_id") or payload.get("plan_id") or "").strip()
            scene_version = int(runtime_event.get("scene_version") or payload.get("scene_version") or 0)
            fingerprint = str(payload.get("world_fingerprint") or "").strip()
            terminal_status = str(payload.get("terminal_status") or payload.get("status") or "").strip()
            if plan_id and scene_version and fingerprint and terminal_status:
                terminal_key = f"{plan_id}:{scene_version}:{fingerprint}:{terminal_status}"
        if terminal_key and event_type:
            terminal_groups[terminal_key].append((sequence, event_type))
        if "生成报告已完成" in text or "最终报告已写入" in text:
            disclosure_sequence.append(f"{terminal_key or 'unkeyed'}:report_ready@{sequence}")
            if not terminal_key:
                terminal_groups["unkeyed"].append((sequence, "report_ready"))
        if "场景快照已刷新" in text:
            disclosure_sequence.append(f"{terminal_key or 'unkeyed'}:scene_snapshot_refreshed@{sequence}")
            if not terminal_key:
                terminal_groups["unkeyed"].append((sequence, "scene_snapshot_refreshed"))
    terminal_prerequisites = {
        "scene_snapshot_refreshed",
        "readiness_reconciled",
        "scene_entity_registry_ready",
        "runtime_scene_world_consistency_audited",
        "scene_world_snapshot_ready",
    }
    disclosure_order_violation = False
    terminal_key_duplicate_count = 0
    for rows in terminal_groups.values():
        ordered = sorted(rows)
        event_counts = Counter(event_type for _sequence, event_type in ordered)
        terminal_key_duplicate_count += sum(max(0, count - 1) for count in event_counts.values())
        report_positions = [index for index, row in enumerate(ordered) if row[1] == "report_ready"]
        if report_positions and any(
            event_type in terminal_prerequisites
            for _sequence, event_type in ordered[report_positions[0] + 1:]
        ):
            disclosure_order_violation = True

    mojibake_sender_count = sum("绯荤粺" in str(message.get("sender_name") or "") for message in messages)
    diagnostic_dump_count = sum(
        len(str(message.get("text") or "")) > 1000
        and any(marker in str(message.get("text") or "") for marker in DIAGNOSTIC_MARKERS)
        for message in messages
    )
    session = SessionControlEvidence(
        history_message_count=len(messages),
        user_turn_count=len(user_turns),
        message_kind_counts=dict(Counter(str(message.get("message_kind") or "") for message in messages)),
        duplicate_heartbeat_count=heartbeat_count,
        duplicate_heartbeat_text=heartbeat_text,
        invalid_entity_fragments=tuple(invalid_entity_fragments),
        finalizer_disclosure_sequence=tuple(disclosure_sequence),
        finalizer_disclosure_order_violation=disclosure_order_violation,
        quasar_import_roots=tuple(log_session["quasar_import_roots"]),
        explicit_model_purpose_count=int(log_session["explicit_model_purpose_count"]),
        explicit_model_summary_count=int(log_session["explicit_model_summary_count"]),
        inferred_model_purpose_count=int(log_session["inferred_model_purpose_count"]),
        mojibake_sender_count=mojibake_sender_count,
        diagnostic_dump_count=diagnostic_dump_count,
        contradictory_turn_ids=tuple(contradictory_turn_ids),
        plan_owner_mismatches=tuple(plan_owner_mismatches),
        native_defer_mutation_message_ids=tuple(native_defer_mutation_message_ids),
        terminal_disclosure_violation_count=int(log_session["terminal_disclosure_violation_count"]),
        terminal_key_duplicate_count=terminal_key_duplicate_count,
    )
    return turns, session


def _parse_dimensions(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in str(raw or "").split(","):
        name, separator, status = item.partition(":")
        if separator and name in R3_DIMENSIONS and status in {"red", "yellow", "green"}:
            result[name] = status
    return result


def _parse_ratio(raw: str) -> tuple[int, int]:
    match = RATIO_RE.match(str(raw or ""))
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def _runtime_evidence(line: str) -> RuntimeEvidence | None:
    if "[LANChatRuntimeEvidence]" not in line or "phase=runtime_queue_drain_result" not in line:
        return None
    batches = BATCH_RE.search(line)
    graphs = GRAPH_RE.search(line)
    drain = DRAIN_RE.search(line)
    if not batches or not graphs:
        return None
    fields = _fields(line)
    return RuntimeEvidence(
        plan_id=fields.get("runtime_plan", ""),
        batch_total=int(batches.group(1)),
        batch_active=int(batches.group(2)),
        batch_terminal=int(batches.group(3)),
        business_graphs=int(graphs.group(1)),
        internal_graphs=int(graphs.group(2)),
        graph_active=int(graphs.group(3)),
        graph_terminal=int(graphs.group(4)),
        drain_status=drain.group(1) if drain else "",
        drained_count=int(drain.group(2)) if drain else 0,
    )


def _media_lineage_evidence(lines: Iterable[str]) -> list[MediaLineageEvidence]:
    evidence: list[MediaLineageEvidence] = []
    for line_number, line in enumerate(lines, start=1):
        marker = "[R3MediaLineageTrace]"
        if marker not in line:
            continue
        raw = line.split(marker, 1)[1].strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        evidence.append(MediaLineageEvidence(
            line_number=line_number,
            phase=str(value.get("phase") or ""),
            plan_id=str(value.get("plan_id") or ""),
            batch_id=str(value.get("batch_id") or ""),
            asset_id=str(value.get("asset_id") or ""),
            image_mode=str(value.get("image_mode") or ""),
            image_ref=str(value.get("image_ref") or ""),
            image_hash=str(value.get("image_hash") or ""),
            image_source=str(value.get("image_source") or ""),
            model_mode=str(value.get("model_mode") or ""),
            source_image_ref=str(value.get("source_image_ref") or ""),
            source_image_hash=str(value.get("source_image_hash") or ""),
            model_ref=str(value.get("model_ref") or ""),
            actor_id=str(value.get("actor_id") or ""),
            actor_source=str(value.get("actor_source") or ""),
            actor_status=str(value.get("actor_status") or ""),
        ))
    return evidence


def _image_failure_codes(lines: Iterable[str]) -> tuple[str, ...]:
    known = (
        "image_tool_call_failed",
        "image_resource_timeout",
        "image_resource_resolve_failed",
        "image_content_hash_missing",
        "source_image_lineage_missing",
        "source_image_lineage_mismatch",
    )
    return tuple(
        code
        for code in known
        if any(code in line for line in lines)
    )


def _dimension_checks(fields: dict[str, str]) -> list[Check]:
    dimensions = _parse_dimensions(fields.get("dimensions", ""))
    checks: list[Check] = []
    for name in R3_DIMENSIONS:
        status = dimensions.get(name)
        if not status:
            checks.append(Check("FAIL", name, "dimension missing from latest R3GateTrace"))
        elif status == "green":
            checks.append(Check("PASS", name, "green"))
        elif status == "yellow":
            checks.append(Check("WARN", name, "yellow"))
        else:
            checks.append(Check("FAIL", name, "red"))
    return checks


def _business_graph_check(evidence: list[RuntimeEvidence]) -> Check:
    if not evidence:
        return Check("FAIL", "business-graph-evidence", "no runtime queue-drain evidence")
    latest = evidence[-1]
    if latest.batch_total != latest.business_graphs:
        return Check(
            "FAIL",
            "business-graph-evidence",
            f"business batches={latest.batch_total}, business graphs={latest.business_graphs}",
        )
    if latest.batch_terminal != latest.graph_terminal:
        return Check(
            "FAIL",
            "business-graph-evidence",
            f"terminal batches={latest.batch_terminal}, terminal graphs={latest.graph_terminal}",
        )
    return Check(
        "PASS",
        "business-graph-evidence",
        f"business batches/graphs={latest.batch_total}/{latest.business_graphs}, "
        f"terminal={latest.batch_terminal}/{latest.graph_terminal}",
    )


def _internal_graph_growth_check(evidence: list[RuntimeEvidence], lines: Iterable[str]) -> Check:
    terminal = [item for item in evidence if item.terminal]
    if len(terminal) < 2:
        return Check("WARN", "terminal-internal-graph-growth", "fewer than two terminal drain samples")
    growth = terminal[-1].internal_graphs - terminal[0].internal_graphs
    exhausted = sum("runtime_finalizer_retry_exhausted" in line for line in lines)
    if growth > 25:
        return Check(
            "FAIL",
            "terminal-internal-graph-growth",
            f"internal graphs grew by {growth} after business terminal; retry_exhausted={exhausted}",
        )
    return Check(
        "PASS",
        "terminal-internal-graph-growth",
        f"internal graph growth after terminal={growth}; retry_exhausted={exhausted}",
    )


def _render_check(fields: dict[str, str]) -> Check:
    ready, total = _parse_ratio(fields.get("render", ""))
    observed, observed_total = _parse_ratio(fields.get("render_observed", ""))
    denominator = max(total, observed_total)
    if denominator <= 0:
        return Check("WARN", "render-readiness", "latest R3GateTrace has no render denominator")
    if observed == observed_total and ready == total:
        return Check("PASS", "render-readiness", f"ready={ready}/{total}, observed={observed}/{observed_total}")
    if observed == 0:
        return Check("FAIL", "render-readiness", f"ready={ready}/{total}, observed={observed}/{observed_total}")
    return Check("WARN", "render-readiness", f"ready={ready}/{total}, observed={observed}/{observed_total}")


def _control_checks(turns: list[TurnEvidence], session: SessionControlEvidence) -> list[Check]:
    checks: list[Check] = []
    duplicate_replies = [turn.message_id for turn in turns if turn.final_reply_count > 1]
    checks.append(
        Check(
            "FAIL" if duplicate_replies else "PASS",
            "control-single-final-reply",
            f"multiple final replies: {', '.join(duplicate_replies)}" if duplicate_replies else "one or fewer final replies per user turn",
        )
    )
    control_runtime_mutations = [
        turn.message_id for turn in turns if "control_plane_runtime_mutation" in turn.diagnostics
    ]
    checks.append(
        Check(
            "FAIL" if control_runtime_mutations else "PASS",
            "control-collaboration-runtime-zero-mutation",
            (
                "control-plane turns mutated Runtime: " + ", ".join(control_runtime_mutations)
                if control_runtime_mutations
                else "discussion, collaboration status, and blocked attempts did not mutate Runtime"
            ),
        )
    )
    late_results = [
        turn.message_id for turn in turns if "late_model_result_discarded" in turn.diagnostics
    ]
    checks.append(
        Check(
            "FAIL" if late_results else "PASS",
            "control-collaboration-late-model-result",
            (
                "late model results were discarded: " + ", ".join(late_results)
                if late_results
                else "no late collaboration model result observed"
            ),
        )
    )

    target_mismatches = [turn.message_id for turn in turns if "reply_target_mismatch" in turn.diagnostics]
    checks.append(
        Check(
            "FAIL" if target_mismatches else "PASS",
            "control-target-authority",
            f"reply sender mismatches: {', '.join(target_mismatches)}" if target_mismatches else "reply senders match explicit targets",
        )
    )

    invalid_owners = [turn.message_id for turn in turns if len(turn.processing_owners) != 1]
    checks.append(
        Check(
            "FAIL" if invalid_owners else "PASS",
            "control-single-processing-owner",
            f"invalid formal processing owners: {', '.join(invalid_owners)}" if invalid_owners else "one Ledger execution owner per observed user turn",
        )
    )
    checks.append(
        Check(
            "FAIL" if session.native_defer_mutation_message_ids else "PASS",
            "control-native-defer-zero-mutation",
            (
                "native defer occurred after business mutation: "
                + ", ".join(session.native_defer_mutation_message_ids)
                if session.native_defer_mutation_message_ids
                else "explicit Agent native observers deferred before business mutation"
            ),
        )
    )

    checks.append(
        Check(
            "FAIL" if session.invalid_entity_fragments else "PASS",
            "control-entity-fragment-safety",
            (
                "command fragments used as entities: " + ", ".join(session.invalid_entity_fragments)
                if session.invalid_entity_fragments
                else "no command-like entity fragments observed"
            ),
        )
    )
    checks.append(
        Check(
            "FAIL" if session.plan_owner_mismatches else "PASS",
            "control-plan-owner-consistency",
            (
                "plan owner mismatches: " + ", ".join(session.plan_owner_mismatches)
                if session.plan_owner_mismatches
                else "no confirmation crossed an observed plan owner"
            ),
        )
    )
    checks.append(
        Check(
            "FAIL" if session.duplicate_heartbeat_count > 1 else "PASS",
            "control-heartbeat-deduplication",
            (
                f"same heartbeat occurred {session.duplicate_heartbeat_count} times: {session.duplicate_heartbeat_text}"
                if session.duplicate_heartbeat_count > 1
                else "no repeated heartbeat text"
            ),
        )
    )
    if session.terminal_disclosure_violation_count:
        checks.append(Check(
            "FAIL",
            "control-finalizer-disclosure-order",
            f"runtime terminal disclosure violations={session.terminal_disclosure_violation_count}",
        ))
    elif not session.finalizer_disclosure_sequence:
        checks.append(Check("WARN", "control-finalizer-disclosure-order", "no report/snapshot disclosure evidence"))
    else:
        checks.append(
            Check(
                "FAIL"
                if session.finalizer_disclosure_order_violation or session.terminal_key_duplicate_count
                else "PASS",
                "control-finalizer-disclosure-order",
                (
                    " -> ".join(session.finalizer_disclosure_sequence)
                    + f"; terminal-key duplicates={session.terminal_key_duplicate_count}"
                ),
            )
        )
    if len(session.quasar_import_roots) > 1:
        checks.append(
            Check(
                "FAIL",
                "control-quasar-import-root",
                "multiple roots initialized: " + ", ".join(session.quasar_import_roots),
            )
        )
    elif session.quasar_import_roots:
        checks.append(Check("PASS", "control-quasar-import-root", session.quasar_import_roots[0]))
    else:
        checks.append(Check("WARN", "control-quasar-import-root", "no Quasar import-root evidence"))

    if session.explicit_model_purpose_count or session.explicit_model_summary_count:
        checks.append(
            Check(
                "PASS",
                "control-model-purpose-observability",
                f"explicit purposes={session.explicit_model_purpose_count}, "
                f"summaries={session.explicit_model_summary_count}, "
                f"inferred={session.inferred_model_purpose_count}",
            )
        )
    elif session.inferred_model_purpose_count:
        checks.append(
            Check(
                "WARN",
                "control-model-purpose-observability",
                f"no explicit purpose field; inferred evidence={session.inferred_model_purpose_count}",
            )
        )
    else:
        checks.append(Check("WARN", "control-model-purpose-observability", "no model-call purpose evidence"))

    checks.append(
        Check(
            "FAIL" if session.contradictory_turn_ids else "PASS",
            "control-runtime-reply-consistency",
            (
                "contradictory Runtime/reply turns: " + ", ".join(session.contradictory_turn_ids)
                if session.contradictory_turn_ids
                else "no observed Runtime/reply contradiction"
            ),
        )
    )
    checks.append(
        Check(
            "FAIL" if session.mojibake_sender_count else "PASS",
            "control-user-visible-encoding",
            (
                f"mojibake sender entries={session.mojibake_sender_count}"
                if session.mojibake_sender_count
                else "no known sender-name mojibake"
            ),
        )
    )
    checks.append(
        Check(
            "FAIL" if session.diagnostic_dump_count else "PASS",
            "control-chat-diagnostic-disclosure",
            (
                f"oversized internal diagnostic messages={session.diagnostic_dump_count}"
                if session.diagnostic_dump_count
                else "no oversized internal diagnostic disclosure"
            ),
        )
    )
    return checks


def _b7_1_scenario_checks(turns: list[TurnEvidence]) -> list[Check]:
    by_text: dict[str, list[TurnEvidence]] = defaultdict(list)
    for turn in turns:
        by_text[_normalize_turn_text(turn.text)].append(turn)
    missing: list[str] = []
    duplicates: list[str] = []
    failures: list[str] = []
    observed: dict[str, TurnEvidence] = {}
    for text, expected_target, expected_model_calls, expected_purposes, require_proposal_ref in B7_1_EXPECTED_TURNS:
        matches = by_text.get(_normalize_turn_text(text), [])
        if not matches:
            missing.append(text)
            continue
        if len(matches) > 1:
            duplicates.append(text)
            continue
        turn = matches[0]
        observed[text] = turn
        if turn.expected_target_name != expected_target:
            failures.append(f"{turn.message_id}:target={turn.expected_target_name or 'missing'}")
        if turn.final_reply_count != 1:
            failures.append(f"{turn.message_id}:final_replies={turn.final_reply_count}")
        if len(turn.processing_owners) != 1:
            failures.append(f"{turn.message_id}:owners={len(turn.processing_owners)}")
        if turn.model_call_count is None:
            failures.append(f"{turn.message_id}:model_call_summary=missing")
        elif turn.model_call_count != expected_model_calls:
            failures.append(
                f"{turn.message_id}:model_calls={turn.model_call_count}!={expected_model_calls}"
            )
        explicit_purposes = {
            value.removeprefix("explicit:")
            for value in turn.model_call_purposes
            if value.startswith("explicit:")
        }
        expected_purpose_set = set(expected_purposes)
        if explicit_purposes != expected_purpose_set:
            failures.append(
                f"{turn.message_id}:model_purposes={','.join(sorted(explicit_purposes)) or 'none'}"
                f"!={','.join(sorted(expected_purpose_set)) or 'none'}"
            )
        if expected_model_calls and len(turn.model_call_elapsed_ms) != expected_model_calls:
            failures.append(
                f"{turn.message_id}:model_call_results={len(turn.model_call_elapsed_ms)}"
                f"!={expected_model_calls}"
            )
        stage_overruns = [elapsed for elapsed in turn.model_call_elapsed_ms if elapsed > 90_000]
        if stage_overruns:
            failures.append(
                f"{turn.message_id}:stage_elapsed_ms={','.join(map(str, stage_overruns))}>90000"
            )
        if expected_model_calls == 4 and turn.model_call_total_elapsed_ms > 180_000:
            failures.append(
                f"{turn.message_id}:proposal_elapsed_ms={turn.model_call_total_elapsed_ms}>180000"
            )
        if require_proposal_ref and not (turn.plan_refs or turn.artifact_refs):
            failures.append(f"{turn.message_id}:stable_plan_or_artifact_ref=missing")
        if require_proposal_ref and (
            len(turn.proposal_ids) != 1
            or len(turn.proposal_versions) != 1
            or len(turn.proposal_hashes) != 1
            or not turn.artifact_bundle_refs
        ):
            failures.append(f"{turn.message_id}:versioned_proposal_metadata=incomplete")
        expected_contract = B7_1_EXPECTED_REPLY_CONTRACTS[text]
        if turn.reply_contracts != (expected_contract,):
            failures.append(
                f"{turn.message_id}:reply_contract={','.join(turn.reply_contracts) or 'missing'}"
                f"!={expected_contract}"
            )
        expected_intent = B7_1_EXPECTED_INTENTS[text]
        if turn.resolved_intents != (expected_intent,):
            failures.append(
                f"{turn.message_id}:resolved_intent={','.join(turn.resolved_intents) or 'missing'}"
                f"!={expected_intent}"
            )
        if text == GREETING_TURN_TEXT:
            reply_text = "\n".join(turn.reply_texts)
            if turn.plan_refs or turn.artifact_refs or turn.proposal_ids:
                failures.append(f"{turn.message_id}:greeting_contains_stale_proposal_reference")
            if any(marker in reply_text for marker in TEMPLATE_MARKERS):
                failures.append(f"{turn.message_id}:greeting_uses_proposal_template")
            if not any(marker in reply_text for marker in GREETING_REPLY_MARKERS):
                failures.append(f"{turn.message_id}:greeting_reply_relevance=missing")
        if expected_contract == "planning_proposal":
            reply_text = "\n".join(turn.reply_texts)
            leaked = [marker for marker in PROMPT_LEAK_MARKERS if marker.lower() in reply_text.lower()]
            if leaked:
                failures.append(
                    f"{turn.message_id}:proposal_prompt_leak={','.join(leaked)}"
                )
    for confirmation_text, source_text in CONFIRMATION_SOURCE_TURN.items():
        confirmation = observed.get(confirmation_text)
        source = observed.get(source_text)
        if confirmation is None or source is None:
            continue
        source_identity = (
            source.proposal_ids,
            source.proposal_versions,
            source.proposal_hashes,
            source.artifact_bundle_refs,
        )
        confirmation_identity = (
            confirmation.proposal_ids,
            confirmation.proposal_versions,
            confirmation.proposal_hashes,
            confirmation.artifact_bundle_refs,
        )
        if confirmation_identity != source_identity:
            failures.append(
                f"{confirmation.message_id}:confirmation_identity_mismatch={source.message_id}"
            )
    coverage_level = "FAIL" if missing or duplicates else "PASS"
    coverage_detail = (
        f"missing={missing}; duplicates={duplicates}"
        if missing or duplicates
        else "all five business turns and one greeting probe observed exactly once"
    )
    result_level = "FAIL" if failures else "PASS"
    return [
        Check(coverage_level, "b7.1-fixed-turn-coverage", coverage_detail),
        Check(
            result_level,
            "b7.1-turn-contract",
            "; ".join(failures) if failures else "target/reply/owner/model budget/plan reference checks passed",
        ),
    ]


def run_control_plane(path: Path, history_path: Path) -> tuple[list[Check], dict[str, object]]:
    lines = _read_lines(path)
    messages, history_errors = _read_history(history_path)
    checks: list[Check] = []
    if history_errors:
        checks.append(Check("FAIL", "control-history-parse", "; ".join(history_errors[:5])))
    else:
        checks.append(Check("PASS", "control-history-parse", f"messages={len(messages)}"))
    turns, session = _control_evidence(lines, messages)
    checks.extend(_control_checks(turns, session))
    checks.extend(_b7_1_scenario_checks(turns))
    return checks, {
        "profile": "control-plane",
        "log": str(path),
        "control_plane": {
            "history": str(history_path),
            "turns": [asdict(turn) for turn in turns],
            "session": asdict(session),
        },
    }


def run_scene_runtime(path: Path) -> tuple[list[Check], dict[str, object]]:
    lines = _read_lines(path)
    lineage = _media_lineage_evidence(lines)
    image_failure_codes = _image_failure_codes(lines)
    checks: list[Check] = []
    if not lineage:
        detail = "no R3MediaLineageTrace rows"
        if image_failure_codes:
            detail += "; image failure codes=" + ",".join(image_failure_codes)
        else:
            detail += "; image failure code missing"
        checks.append(Check("FAIL", "b7.2-media-lineage-evidence", detail))
    else:
        checks.append(Check(
            "PASS",
            "b7.2-media-lineage-evidence",
            f"complete lineage rows={len(lineage)}",
        ))

    invalid_images = [
        item.asset_id
        for item in lineage
        if item.image_mode != "text_to_image"
        or not item.image_ref
        or not item.image_hash.startswith("sha256:")
        or item.image_source.lower() in {"mock", "mock_reference", "fixture"}
    ]
    checks.append(Check(
        "FAIL" if not lineage or invalid_images else "PASS",
        "b7.2-real-text-to-image",
        (
            "no media lineage evidence"
            if not lineage
            else f"invalid image lineage: {', '.join(invalid_images)}"
            if invalid_images
            else "all images are real text_to_image resources"
        ),
    ))

    invalid_models = [
        item.asset_id
        for item in lineage
        if item.model_mode != "image_to_3d"
        or not item.model_ref
        or item.source_image_ref != item.image_ref
        or item.source_image_hash != item.image_hash
    ]
    checks.append(Check(
        "FAIL" if not lineage or invalid_models else "PASS",
        "b7.2-strict-image-to-model",
        (
            "no media lineage evidence"
            if not lineage
            else f"invalid model lineage: {', '.join(invalid_models)}"
            if invalid_models
            else "model source refs and hashes match image resources"
        ),
    ))

    invalid_actors = [
        item.asset_id
        for item in lineage
        if item.phase != "actor_import_ready"
        or not item.actor_id
        or not item.actor_source.startswith("engine_")
        or item.actor_status not in {"ready", "engine_ready", "bounds_ready", "render_ready"}
    ]
    checks.append(Check(
        "FAIL" if not lineage or invalid_actors else "PASS",
        "b7.2-engine-actor-import",
        (
            "no media lineage evidence"
            if not lineage
            else f"invalid Actor import evidence: {', '.join(invalid_actors)}"
            if invalid_actors
            else "all lineage rows terminate in Engine Actor facts"
        ),
    ))

    forbidden_fallbacks = [
        marker
        for marker in ("mock_reference", "generation_mode=text_to_3d", '"generation_mode":"text_to_3d"')
        if any(marker in line for line in lines)
    ]
    checks.append(Check(
        "FAIL" if forbidden_fallbacks else "PASS",
        "b7.2-no-media-fallback",
        f"forbidden fallback evidence: {', '.join(forbidden_fallbacks)}" if forbidden_fallbacks else "no mock_reference or text_to_3d fallback observed",
    ))

    runtime_lines = [line for line in lines if "[LANChatRuntimeEvidence]" in line]
    latest_runtime_fields = _fields(runtime_lines[-1]) if runtime_lines else {}
    try:
        engine_imports = int(latest_runtime_fields.get("engine_imports") or 0)
    except (TypeError, ValueError):
        engine_imports = 0
    checks.append(Check(
        "PASS" if engine_imports > 0 else "FAIL",
        "b7.2-runtime-engine-import-count",
        f"engine_imports={engine_imports}" if runtime_lines else "no LANChatRuntimeEvidence row",
    ))
    return checks, {
        "profile": "scene-runtime",
        "log": str(path),
        "media_lineage": [asdict(item) for item in lineage],
        "image_failure_codes": list(image_failure_codes),
        "engine_imports": engine_imports,
    }


def run(path: Path, history_path: Path | None = None) -> tuple[list[Check], dict[str, object]]:
    lines = _read_lines(path)
    gate_lines = [line for line in lines if "[R3GateTrace]" in line]
    evidence = [item for line in lines if (item := _runtime_evidence(line)) is not None]
    if not gate_lines:
        checks = [Check("FAIL", "r3-gate-trace", "no R3GateTrace found")]
        latest_fields: dict[str, str] = {}
        overall = ""
    else:
        latest_fields = _fields(gate_lines[-1])
        overall = latest_fields.get("overall", "")
        overall_level = {"green": "PASS", "yellow": "WARN", "red": "FAIL"}.get(overall, "FAIL")
        checks = [Check(overall_level, "r3-gate-trace", f"overall={overall or 'missing'}")]
        checks.extend(_dimension_checks(latest_fields))
        checks.append(_business_graph_check(evidence))
        checks.append(_internal_graph_growth_check(evidence, lines))
        checks.append(_render_check(latest_fields))
    latest_evidence = asdict(evidence[-1]) if evidence else {}
    metadata: dict[str, object] = {
        "log": str(path),
        "gate_trace_count": len(gate_lines),
        "runtime_evidence_count": len(evidence),
        "plan_id": latest_fields.get("plan", ""),
        "scene_version": int(latest_fields.get("scene_version", "0") or 0),
        "overall": overall,
        "game_ready": latest_fields.get("game_ready", ""),
        "render": latest_fields.get("render", ""),
        "render_observed": latest_fields.get("render_observed", ""),
        "latest_runtime_evidence": latest_evidence,
    }
    if history_path is not None:
        messages, history_errors = _read_history(history_path)
        if history_errors:
            checks.append(
                Check(
                    "FAIL",
                    "control-history-parse",
                    "; ".join(history_errors[:5]),
                )
            )
        else:
            checks.append(Check("PASS", "control-history-parse", f"messages={len(messages)}"))
        turns, session = _control_evidence(lines, messages)
        checks.extend(_control_checks(turns, session))
        metadata["control_plane"] = {
            "history": str(history_path),
            "turns": [asdict(turn) for turn in turns],
            "session": asdict(session),
        }
    return checks, metadata


def summarize(checks: list[Check], *, profile: str = "full-r3") -> str:
    counts = Counter(check.level for check in checks)
    prefix = {
        "control-plane": "B7_1_CONTROL",
        "scene-runtime": "B7_2_SCENE",
    }.get(profile, "R3_F5")
    status = f"{prefix}_BLOCKED" if counts["FAIL"] else f"{prefix}_WARN" if counts["WARN"] else f"{prefix}_READY"
    return f"{status}: PASS={counts['PASS']} WARN={counts['WARN']} FAIL={counts['FAIL']}"


def main(argv: list[str] | None = None) -> int:
    # Windows consoles otherwise render Chinese evidence summaries using the
    # active code page, which makes a failed probe hard to audit or diff.
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)
            if callable(reconfigure):
                reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser()
    parser.add_argument("log", nargs="?", type=Path, help="Path to *_corona.log; defaults to latest")
    parser.add_argument("--history", type=Path, help="Path to the corresponding LANChat JSONL history")
    parser.add_argument(
        "--profile",
        choices=("full-r3", "control-plane", "scene-runtime"),
        default="full-r3",
        help="Run the complete R3 probe or an isolated B7.1/B7.2 gate",
    )
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report")
    args = parser.parse_args(argv)
    path = args.log or _latest_log()
    if not path.exists():
        print(f"[FAIL] log not found: {path}", file=sys.stderr)
        return 2
    if args.history is not None and not args.history.exists():
        print(f"[FAIL] history not found: {args.history}", file=sys.stderr)
        return 2
    if args.profile == "control-plane":
        if args.history is None:
            print("[FAIL] --history is required for --profile control-plane", file=sys.stderr)
            return 2
        checks, metadata = run_control_plane(path, args.history)
    elif args.profile == "scene-runtime":
        checks, metadata = run_scene_runtime(path)
    else:
        checks, metadata = run(path, args.history)
    if args.json:
        print(json.dumps({"metadata": metadata, "checks": [asdict(item) for item in checks], "summary": summarize(checks, profile=args.profile)}, ensure_ascii=False, indent=2))
    else:
        print(f"[INFO] log={path}")
        control_plane = metadata.get("control_plane")
        if isinstance(control_plane, dict):
            print(f"[INFO] history={control_plane.get('history') or ''}")
            for turn in list(control_plane.get("turns") or []):
                print(
                    "[TURN] "
                    f"message_id={turn.get('message_id') or ''} "
                    f"target={turn.get('expected_target_name') or turn.get('expected_target_id') or ''} "
                    f"routes={','.join(turn.get('routes') or []) or 'none'} "
                    f"owners={','.join(turn.get('processing_owners') or []) or 'none'} "
                    f"final_replies={turn.get('final_reply_count') or 0} "
                    f"reply_senders={','.join(turn.get('actual_reply_senders') or []) or 'none'} "
                    f"progress={turn.get('progress_count') or 0} "
                    f"action_status={turn.get('action_status_count') or 0} "
                    f"model_calls={turn.get('model_call_count') if turn.get('model_call_count') is not None else 'missing'} "
                    f"model_purposes={','.join(turn.get('model_call_purposes') or []) or 'missing'} "
                    f"plans={','.join(turn.get('plan_refs') or []) or 'none'} "
                    f"diagnostics={','.join(turn.get('diagnostics') or []) or 'none'}"
                )
        for check in checks:
            print(f"[{check.level}] {check.name}: {check.detail}")
        print(f"[SUMMARY] {summarize(checks, profile=args.profile)}")
    return 1 if any(check.level == "FAIL" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
