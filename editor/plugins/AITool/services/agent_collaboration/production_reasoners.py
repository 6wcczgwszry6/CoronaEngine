"""Tool-free production reasoners for the three-role collaboration chain."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
import re
from typing import Any, Literal, Mapping, Protocol

from .agents.art_agent import ArtAgentDraft, ArtContext, ArtRequest
from .agents.planning_agent import PlanningAgentDraft, PlanningContext, PlanningRequest
from .agents.program_agent import ProgramAgentDraft, ProgramContext, ProgramRequest
from .contracts import (
    ALLOWED_GAMEPLAY_PRIMITIVES,
    ArtDirection,
    GameDesignBrief,
    GameplayEntitySlot,
    GameplayLogicPlan,
    GameplayPrimitiveSpec,
    LevelPlan,
    SceneCompositionPlan,
    gameplay_logic_contract_manifest,
    validate_artifact_payload,
)


class CollaborationReasoningError(RuntimeError):
    """Raised when a model response cannot become a validated collaboration result."""

    def __init__(
        self,
        safe_summary: str,
        *,
        stage: Literal["planning", "program", "art", "narration"],
        error_code: str,
        field_path: str = "",
        response_hash: str = "",
        diagnostic_refs: tuple[str, ...] = (),
    ) -> None:
        summary = str(safe_summary or "Collaboration reasoning failed.").strip()
        super().__init__(summary)
        self.stage = stage
        self.error_code = str(error_code or "collaboration_reasoning_failed").strip()
        self.field_path = str(field_path or "").strip()
        self.safe_summary = summary
        self.response_hash = str(response_hash or "").strip()
        self.diagnostic_refs = tuple(
            str(item or "").strip()[:160]
            for item in diagnostic_refs
            if str(item or "").strip()
        )[:8]

    def as_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "error_code": self.error_code,
            "field_path": self.field_path,
            "safe_summary": self.safe_summary,
            "response_hash": self.response_hash,
            "diagnostic_refs": list(self.diagnostic_refs),
        }


class CompletionPort(Protocol):
    def __call__(self, purpose: str, system_prompt: str, user_prompt: str) -> str: ...


@dataclass(frozen=True)
class ArtRoleManifestEntry:
    slot_id: str
    semantic_role: str
    required_capabilities: tuple[str, ...]

    def prompt_payload(self) -> dict[str, object]:
        return {
            "slot_id": self.slot_id,
            "semantic_role": self.semantic_role,
            "required_capabilities": list(self.required_capabilities),
        }


_SEMANTIC_ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")


def _response_hash(raw: Any) -> str:
    return "sha256:" + hashlib.sha256(str(raw or "").encode("utf-8")).hexdigest()


def _required_text(
    value: Any,
    field: str,
    *,
    stage: Literal["planning", "program", "art"],
    response_hash: str,
) -> str:
    text = str(value or "").strip()
    if not text:
        raise CollaborationReasoningError(
            f"{field} is required",
            stage=stage,
            error_code="required_field_missing",
            field_path=field,
            response_hash=response_hash,
        )
    return text


def _text_tuple(
    value: Any,
    field: str,
    *,
    stage: Literal["planning", "program", "art"],
    response_hash: str,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, (list, tuple)):
        raise CollaborationReasoningError(
            f"{field} must be a list of strings",
            stage=stage,
            error_code="invalid_field_type",
            field_path=field,
            response_hash=response_hash,
        )
    result = tuple(str(item or "").strip() for item in value)
    if any(not item for item in result) or (not allow_empty and not result):
        raise CollaborationReasoningError(
            f"{field} contains invalid values",
            stage=stage,
            error_code="invalid_field_value",
            field_path=field,
            response_hash=response_hash,
        )
    return result


def _json_object(
    raw: Any,
    *,
    stage: Literal["planning", "program", "art"],
) -> tuple[dict[str, Any], str]:
    text = str(raw or "").strip()
    response_hash = _response_hash(text)
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value, response_hash
    raise CollaborationReasoningError(
        "reasoner did not return a JSON object",
        stage=stage,
        error_code="invalid_json_object",
        response_hash=response_hash,
    )


def _context_payloads(items: tuple[Any, ...]) -> dict[str, Any]:
    return {
        str(item.artifact_type): dict(item.payload)
        for item in items
        if str(getattr(item, "artifact_type", "") or "") and isinstance(item.payload, Mapping)
    }


def _json_prompt(value: Any) -> str:
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _validation_error_code(errors: tuple[str, ...]) -> tuple[str, str]:
    first = str(errors[0] if errors else "artifact_validation_failed")
    field_path = first.split(":", 1)[0]
    if ":unsupported" in first:
        return "unsupported_primitive", field_path
    if ".parameters:" in first:
        return "invalid_parameters", field_path
    if ":unknown" in first:
        return "unknown_slot", field_path
    if ".semantic_role:invalid_identifier" in first:
        return "invalid_semantic_role", field_path
    if ":requires_" in first and ("subject_slot" in first or "target_slot" in first):
        return "capability_mismatch", field_path
    if ":self_slot_reference" in first:
        return "self_slot_reference", field_path
    if ".slot_id:duplicate" in first:
        return "duplicate_slot_id", field_path
    if ".semantic_role:duplicate" in first:
        return "duplicate_semantic_role", field_path
    if ".primitive_id:duplicate" in first:
        return "duplicate_primitive_id", field_path
    if ":duplicate" in first:
        return "duplicate_identity", field_path
    return "artifact_validation_failed", field_path


def _validation_diagnostic_refs(
    artifact_type: str,
    value: Any,
    errors: tuple[str, ...],
) -> tuple[str, ...]:
    """Return bounded structural diagnostics without exposing model prose."""

    refs = [f"artifact:{artifact_type}"]
    refs.extend(f"validation:{item}" for item in errors[:4])
    if artifact_type == "GameplayLogicPlan" and is_dataclass(value):
        for index, primitive in enumerate(getattr(value, "primitives", ())):
            primitive_id = str(getattr(primitive, "primitive_id", "") or "").strip()
            subject = str(getattr(primitive, "subject_slot", "") or "").strip()
            target = str(getattr(primitive, "target_slot", "") or "").strip()
            refs.append(f"primitive[{index}]:{primitive_id}:{subject}->{target}")
    return tuple(refs[:8])


def _assert_artifact_valid(
    artifact_type: str,
    value: Any,
    *,
    stage: Literal["planning", "program", "art"],
    response_hash: str,
) -> None:
    validation = validate_artifact_payload(artifact_type, asdict(value))
    if not validation.valid:
        error_code, field_path = _validation_error_code(validation.errors)
        raise CollaborationReasoningError(
            f"{artifact_type} validation failed: {','.join(validation.errors)}",
            stage=stage,
            error_code=error_code,
            field_path=field_path,
            response_hash=response_hash,
            diagnostic_refs=_validation_diagnostic_refs(artifact_type, value, validation.errors),
        )


class ProductionPlanningReasoner:
    def __init__(self, complete: CompletionPort) -> None:
        if not callable(complete):
            raise TypeError("complete must be callable")
        self._complete = complete

    def generate(self, request: PlanningRequest, context: PlanningContext) -> PlanningAgentDraft:
        system = (
            "你是游戏策划 Agent。只输出一个 JSON 对象，不要输出 Markdown、解释或执行承诺。"
            "JSON 必须包含 game_design_brief 和 level_plan，且所有数组元素都是非空字符串。"
            "方案必须针对用户目标，描述低成本单人可玩闭环。"
        )
        user = _json_prompt({
            "project_goal": request.project_goal,
            "constraints": request.constraints,
            "acceptance_criteria": request.acceptance_criteria,
            "prior_artifacts": _context_payloads(context.prior_artifacts),
            "output_schema": {
                "game_design_brief": {
                    "project_goal": "string",
                    "player_experience": ["string"],
                    "core_rules": ["string"],
                    "acceptance_criteria": ["string"],
                },
                "level_plan": {
                    "level_goal": "string",
                    "zones": ["string"],
                    "progression": ["string"],
                    "acceptance_criteria": ["string"],
                },
            },
        })
        raw = self._complete("planning_artifact_reasoning", system, user)
        payload, response_hash = _json_object(raw, stage="planning")
        brief = payload.get("game_design_brief")
        level = payload.get("level_plan")
        if not isinstance(brief, Mapping) or not isinstance(level, Mapping):
            raise CollaborationReasoningError(
                "planning response is missing typed artifacts",
                stage="planning",
                error_code="typed_artifacts_missing",
                response_hash=response_hash,
            )
        game_design_brief = GameDesignBrief(
                project_goal=_required_text(
                    brief.get("project_goal"),
                    "game_design_brief.project_goal",
                    stage="planning",
                    response_hash=response_hash,
                ),
                player_experience=_text_tuple(
                    brief.get("player_experience"),
                    "game_design_brief.player_experience",
                    stage="planning",
                    response_hash=response_hash,
                ),
                core_rules=_text_tuple(
                    brief.get("core_rules"),
                    "game_design_brief.core_rules",
                    stage="planning",
                    response_hash=response_hash,
                ),
                acceptance_criteria=_text_tuple(
                    brief.get("acceptance_criteria"),
                    "game_design_brief.acceptance_criteria",
                    stage="planning",
                    response_hash=response_hash,
                ),
            )
        level_plan = LevelPlan(
                level_goal=_required_text(
                    level.get("level_goal"),
                    "level_plan.level_goal",
                    stage="planning",
                    response_hash=response_hash,
                ),
                zones=_text_tuple(
                    level.get("zones"),
                    "level_plan.zones",
                    stage="planning",
                    response_hash=response_hash,
                ),
                progression=_text_tuple(
                    level.get("progression"),
                    "level_plan.progression",
                    stage="planning",
                    response_hash=response_hash,
                ),
                acceptance_criteria=_text_tuple(
                    level.get("acceptance_criteria"),
                    "level_plan.acceptance_criteria",
                    stage="planning",
                    response_hash=response_hash,
                ),
            )
        _assert_artifact_valid(
            "GameDesignBrief",
            game_design_brief,
            stage="planning",
            response_hash=response_hash,
        )
        _assert_artifact_valid(
            "LevelPlan",
            level_plan,
            stage="planning",
            response_hash=response_hash,
        )
        return PlanningAgentDraft(
            game_design_brief=game_design_brief,
            level_plan=level_plan,
        )


class _LegacyProductionProgramReasoner:
    def __init__(self, complete: CompletionPort) -> None:
        if not callable(complete):
            raise TypeError("complete must be callable")
        self._complete = complete

    def generate(self, request: ProgramRequest, context: ProgramContext) -> ProgramAgentDraft:
        system = (
            "你是游戏程序设计 Agent。只输出一个 JSON 对象，不要输出脚本、Markdown 或执行承诺。"
            "严格遵守 validator_manifest；不要发明 primitive、参数、capability 或 slot。"
            "每个 primitive 的 subject_slot/target_slot 必须引用 entity_slots 且不得相同。"
            "它们是交互参与者，不是前置依赖边，可以在不同 primitive 中重复引用。"
        )
        validator_manifest = gameplay_logic_contract_manifest()
        user = _json_prompt({
            "logic_objective": request.logic_objective,
            "constraints": request.constraints,
            "acceptance_criteria": request.acceptance_criteria,
            "input_artifacts": _context_payloads(context.input_artifacts),
            "validator_manifest": validator_manifest,
            "output_schema": {
                "gameplay_logic_plan": {
                    "states": ["string"],
                    "entity_slots": [{
                        "slot_id": "string",
                        "semantic_role": "string",
                        "required_capabilities": ["string"],
                    }],
                    "primitives": [{
                        "primitive_id": "string",
                        "kind": "allowed primitive",
                        "subject_slot": "slot_id",
                        "target_slot": "slot_id",
                        "parameters": {},
                    }],
                    "win_conditions": ["string"],
                    "lose_conditions": ["string"],
                    "triggers": ["string"],
                    "rules": ["string"],
                },
            },
            "valid_minimal_example": {
                "gameplay_logic_plan": {
                    "states": ["key_available", "key_collected", "door_unlocked", "complete"],
                    "entity_slots": [
                        {
                            "slot_id": "player",
                            "semantic_role": "player_spawn",
                            "required_capabilities": ["player"],
                        },
                        {
                            "slot_id": "key",
                            "semantic_role": "collectible_key",
                            "required_capabilities": ["collectible"],
                        },
                        {
                            "slot_id": "door",
                            "semantic_role": "locked_door",
                            "required_capabilities": ["lockable"],
                        },
                        {
                            "slot_id": "goal",
                            "semantic_role": "goal_zone",
                            "required_capabilities": ["trigger_zone"],
                        },
                    ],
                    "primitives": [
                        {
                            "primitive_id": "collect_key",
                            "kind": "on_collect",
                            "subject_slot": "key",
                            "target_slot": "player",
                            "parameters": {"state_key": "has_key", "set_value": True},
                        },
                        {
                            "primitive_id": "unlock_door",
                            "kind": "unlock",
                            "subject_slot": "key",
                            "target_slot": "door",
                            "parameters": {"required_state": "has_key", "required_value": True},
                        },
                        {
                            "primitive_id": "enter_goal",
                            "kind": "on_enter",
                            "subject_slot": "goal",
                            "target_slot": "player",
                            "parameters": {},
                        },
                        {
                            "primitive_id": "complete_goal",
                            "kind": "complete_objective",
                            "subject_slot": "goal",
                            "target_slot": "player",
                            "parameters": {"objective_id": "reach_goal"},
                        },
                    ],
                    "win_conditions": ["reach_goal completed"],
                    "lose_conditions": ["none"],
                    "triggers": ["collect_key", "enter_goal"],
                    "rules": ["door requires collected key"],
                },
            },
        })
        raw = self._complete("program_artifact_reasoning", system, user)
        payload, response_hash = _json_object(raw, stage="program")
        logic = payload.get("gameplay_logic_plan")
        if not isinstance(logic, Mapping):
            raise CollaborationReasoningError(
                "program response is missing GameplayLogicPlan",
                stage="program",
                error_code="typed_artifacts_missing",
                field_path="gameplay_logic_plan",
                response_hash=response_hash,
            )
        raw_slots = logic.get("entity_slots")
        raw_primitives = logic.get("primitives")
        if not isinstance(raw_slots, list) or not raw_slots:
            raise CollaborationReasoningError(
                "gameplay_logic_plan.entity_slots is required",
                stage="program",
                error_code="required_field_missing",
                field_path="gameplay_logic_plan.entity_slots",
                response_hash=response_hash,
            )
        if not isinstance(raw_primitives, list) or not raw_primitives:
            raise CollaborationReasoningError(
                "gameplay_logic_plan.primitives is required",
                stage="program",
                error_code="required_field_missing",
                field_path="gameplay_logic_plan.primitives",
                response_hash=response_hash,
            )
        slots = tuple(
            GameplayEntitySlot(
                slot_id=_required_text(
                    item.get("slot_id"),
                    f"entity_slots[{index}].slot_id",
                    stage="program",
                    response_hash=response_hash,
                ),
                semantic_role=_required_text(
                    item.get("semantic_role"),
                    f"entity_slots[{index}].semantic_role",
                    stage="program",
                    response_hash=response_hash,
                ),
                required_capabilities=_text_tuple(
                    item.get("required_capabilities"),
                    f"entity_slots[{index}].required_capabilities",
                    stage="program",
                    response_hash=response_hash,
                ),
            )
            for index, item in enumerate(raw_slots)
            if isinstance(item, Mapping)
        )
        if len(slots) != len(raw_slots):
            raise CollaborationReasoningError(
                "entity_slots must contain objects",
                stage="program",
                error_code="invalid_field_type",
                field_path="gameplay_logic_plan.entity_slots",
                response_hash=response_hash,
            )
        slot_ids = {slot.slot_id for slot in slots}
        primitives: list[GameplayPrimitiveSpec] = []
        for index, item in enumerate(raw_primitives):
            if not isinstance(item, Mapping):
                raise CollaborationReasoningError(
                    "primitives must contain objects",
                    stage="program",
                    error_code="invalid_field_type",
                    field_path=f"gameplay_logic_plan.primitives[{index}]",
                    response_hash=response_hash,
                )
            kind = _required_text(
                item.get("kind"),
                f"primitives[{index}].kind",
                stage="program",
                response_hash=response_hash,
            )
            subject = _required_text(
                item.get("subject_slot"),
                f"primitives[{index}].subject_slot",
                stage="program",
                response_hash=response_hash,
            )
            target = _required_text(
                item.get("target_slot"),
                f"primitives[{index}].target_slot",
                stage="program",
                response_hash=response_hash,
            )
            if kind not in ALLOWED_GAMEPLAY_PRIMITIVES:
                raise CollaborationReasoningError(
                    f"unsupported gameplay primitive: {kind}",
                    stage="program",
                    error_code="unsupported_primitive",
                    field_path=f"gameplay_logic_plan.primitives[{index}].kind",
                    response_hash=response_hash,
                )
            if subject not in slot_ids or target not in slot_ids:
                raise CollaborationReasoningError(
                    "gameplay primitive references an unknown slot",
                    stage="program",
                    error_code="unknown_slot",
                    field_path=f"gameplay_logic_plan.primitives[{index}]",
                    response_hash=response_hash,
                )
            parameters = item.get("parameters")
            if not isinstance(parameters, Mapping):
                raise CollaborationReasoningError(
                    f"primitives[{index}].parameters must be an object",
                    stage="program",
                    error_code="invalid_parameters",
                    field_path=f"gameplay_logic_plan.primitives[{index}].parameters",
                    response_hash=response_hash,
                )
            primitives.append(GameplayPrimitiveSpec(
                primitive_id=_required_text(
                    item.get("primitive_id"),
                    f"primitives[{index}].primitive_id",
                    stage="program",
                    response_hash=response_hash,
                ),
                kind=kind,
                subject_slot=subject,
                target_slot=target,
                parameters=dict(parameters),
            ))
        gameplay_logic_plan = GameplayLogicPlan(
                states=_text_tuple(
                    logic.get("states"),
                    "gameplay_logic_plan.states",
                    stage="program",
                    response_hash=response_hash,
                ),
                entity_slots=slots,
                primitives=tuple(primitives),
                win_conditions=_text_tuple(
                    logic.get("win_conditions"),
                    "gameplay_logic_plan.win_conditions",
                    stage="program",
                    response_hash=response_hash,
                ),
                lose_conditions=_text_tuple(
                    logic.get("lose_conditions"),
                    "gameplay_logic_plan.lose_conditions",
                    stage="program",
                    response_hash=response_hash,
                    allow_empty=True,
                ),
                triggers=_text_tuple(
                    logic.get("triggers", []),
                    "gameplay_logic_plan.triggers",
                    stage="program",
                    response_hash=response_hash,
                    allow_empty=True,
                ),
                rules=_text_tuple(
                    logic.get("rules", []),
                    "gameplay_logic_plan.rules",
                    stage="program",
                    response_hash=response_hash,
                    allow_empty=True,
                ),
            )
        _assert_artifact_valid(
            "GameplayLogicPlan",
            gameplay_logic_plan,
            stage="program",
            response_hash=response_hash,
        )
        return ProgramAgentDraft(gameplay_logic_plan=gameplay_logic_plan)


class ProductionProgramReasoner(_LegacyProductionProgramReasoner):
    """Use a semantic-role keyed model schema, then assemble the public slot list."""

    _SYSTEM_PROMPT = (
        "You are the gameplay program-design Agent. Return exactly one JSON object, with no "
        "Markdown, scripts, explanations, or execution promises. Follow validator_manifest exactly. "
        "gameplay_logic_plan.entity_roles must be an object keyed by canonical semantic_role. Each "
        "semantic_role key and each slot_id must be globally unique. Primitive subject_slot and "
        "target_slot must reference declared slot_id values and must differ. They identify interaction "
        "participants, so they may be reused across primitives and do not form a dependency graph. "
        "Do not invent primitives, parameters, capabilities, or undeclared slots."
    )

    def generate(self, request: ProgramRequest, context: ProgramContext) -> ProgramAgentDraft:
        original_complete = self._complete

        def complete(purpose: str, _system_prompt: str, user_prompt: str) -> str:
            prompt = json.loads(user_prompt)
            schema = prompt["output_schema"]["gameplay_logic_plan"]
            schema.pop("entity_slots", None)
            schema["entity_roles"] = {
                "canonical_semantic_role": {
                    "slot_id": "unique string",
                    "required_capabilities": ["string"],
                },
            }
            example_logic = prompt["valid_minimal_example"]["gameplay_logic_plan"]
            example_slots = list(example_logic.pop("entity_slots", ()))
            example_logic["entity_roles"] = {
                str(item["semantic_role"]): {
                    "slot_id": str(item["slot_id"]),
                    "required_capabilities": list(item["required_capabilities"]),
                }
                for item in example_slots
            }
            raw = original_complete(purpose, self._SYSTEM_PROMPT, _json_prompt(prompt))
            payload, response_hash = _json_object(raw, stage="program")
            logic = payload.get("gameplay_logic_plan")
            if not isinstance(logic, Mapping):
                return str(raw or "")
            raw_roles = logic.get("entity_roles")
            if not isinstance(raw_roles, Mapping) or not raw_roles:
                raise CollaborationReasoningError(
                    "gameplay_logic_plan.entity_roles is required",
                    stage="program",
                    error_code="required_field_missing",
                    field_path="gameplay_logic_plan.entity_roles",
                    response_hash=response_hash,
                )
            slots: list[dict[str, object]] = []
            semantic_roles: set[str] = set()
            slot_ids: set[str] = set()
            for index, (raw_role, item) in enumerate(raw_roles.items()):
                field_path = f"gameplay_logic_plan.entity_roles[{index}]"
                if not isinstance(item, Mapping):
                    raise CollaborationReasoningError(
                        "entity_roles values must be objects",
                        stage="program",
                        error_code="invalid_field_type",
                        field_path=field_path,
                        response_hash=response_hash,
                    )
                semantic_role = str(raw_role or "").strip().lower()
                if not _SEMANTIC_ROLE_PATTERN.fullmatch(semantic_role):
                    raise CollaborationReasoningError(
                        "semantic_role must be a canonical identifier",
                        stage="program",
                        error_code="invalid_semantic_role",
                        field_path=f"{field_path}.semantic_role",
                        response_hash=response_hash,
                    )
                if semantic_role in semantic_roles:
                    raise CollaborationReasoningError(
                        "semantic_role values must be unique after normalization",
                        stage="program",
                        error_code="duplicate_semantic_role",
                        field_path=f"{field_path}.semantic_role",
                        response_hash=response_hash,
                    )
                slot_id = _required_text(
                    item.get("slot_id"),
                    f"{field_path}.slot_id",
                    stage="program",
                    response_hash=response_hash,
                )
                if slot_id in slot_ids:
                    raise CollaborationReasoningError(
                        "slot_id values must be unique",
                        stage="program",
                        error_code="duplicate_slot_id",
                        field_path=f"{field_path}.slot_id",
                        response_hash=response_hash,
                    )
                capabilities = _text_tuple(
                    item.get("required_capabilities"),
                    f"{field_path}.required_capabilities",
                    stage="program",
                    response_hash=response_hash,
                )
                semantic_roles.add(semantic_role)
                slot_ids.add(slot_id)
                slots.append({
                    "slot_id": slot_id,
                    "semantic_role": semantic_role,
                    "required_capabilities": list(capabilities),
                })
            normalized_payload = dict(payload)
            normalized_logic = dict(logic)
            normalized_logic.pop("entity_roles", None)
            normalized_logic["entity_slots"] = slots
            normalized_payload["gameplay_logic_plan"] = normalized_logic
            return _json_prompt(normalized_payload)

        return _LegacyProductionProgramReasoner(complete).generate(request, context)


class ProductionArtReasoner:
    def __init__(self, complete: CompletionPort) -> None:
        if not callable(complete):
            raise TypeError("complete must be callable")
        self._complete = complete

    def generate(self, request: ArtRequest, context: ArtContext) -> ArtAgentDraft:
        inputs = _context_payloads(context.input_artifacts)
        goal = str(dict(inputs.get("GameDesignBrief") or {}).get("project_goal") or "").strip()
        gameplay = dict(inputs.get("GameplayLogicPlan") or {})
        role_manifest = tuple(
            ArtRoleManifestEntry(
                slot_id=str(item.get("slot_id") or "").strip(),
                semantic_role=str(item.get("semantic_role") or "").strip(),
                required_capabilities=tuple(
                    str(value or "").strip()
                    for value in list(item.get("required_capabilities") or [])
                    if str(value or "").strip()
                ),
            )
            for item in list(gameplay.get("entity_slots") or [])
            if isinstance(item, Mapping)
            and str(item.get("slot_id") or "").strip()
            and str(item.get("semantic_role") or "").strip()
        )
        required_roles = tuple(item.semantic_role for item in role_manifest)
        if not role_manifest:
            raise CollaborationReasoningError(
                "validated gameplay role manifest is unavailable",
                stage="art",
                error_code="art_role_manifest_invalid",
                field_path="gameplay_logic_plan.entity_slots",
            )
        if len(set(required_roles)) != len(required_roles):
            raise CollaborationReasoningError(
                "validated gameplay role manifest contains duplicate semantic roles",
                stage="art",
                error_code="art_role_manifest_invalid",
                field_path="gameplay_logic_plan.entity_slots.semantic_role",
            )
        system = (
            "你是游戏美术 Agent。只输出一个 JSON 对象，不要输出 Markdown 或执行承诺。"
            "美术方向必须明确引用用户目标。semantic_role 是程序 Agent 提供的机器身份，"
            "不得改名、翻译或自行增删；你只负责全局视觉提示和可选的逐角色视觉覆盖。"
        )
        user = _json_prompt({
            "project_goal": goal,
            "art_objective": request.art_objective,
            "constraints": request.constraints,
            "art_role_manifest": [item.prompt_payload() for item in role_manifest],
            "input_artifacts": inputs,
            "output_schema": {
                "art_direction": {
                    "style_keywords": ["string"],
                    "palette": ["string"],
                    "lighting": ["string"],
                    "avoid_keywords": ["string"],
                },
                "scene_composition_plan": {
                    "scene_type": "string",
                    "environment_requirements": ["string"],
                    "layout_rules": ["string"],
                    "global_visual_prompt": "string",
                    "role_visual_overrides": {"semantic_role": "optional visual detail"},
                },
            },
        })
        raw = self._complete("art_artifact_reasoning", system, user)
        payload, response_hash = _json_object(raw, stage="art")
        art = payload.get("art_direction")
        composition = payload.get("scene_composition_plan")
        if not isinstance(art, Mapping) or not isinstance(composition, Mapping):
            raise CollaborationReasoningError(
                "art response is missing typed artifacts",
                stage="art",
                error_code="typed_artifacts_missing",
                response_hash=response_hash,
            )
        global_visual_prompt = str(composition.get("global_visual_prompt") or "").strip()
        if not global_visual_prompt:
            raise CollaborationReasoningError(
                "scene composition is missing a global visual prompt",
                stage="art",
                error_code="art_visual_prompt_missing",
                field_path="scene_composition_plan.global_visual_prompt",
                response_hash=response_hash,
            )
        role_visual_overrides = composition.get("role_visual_overrides", {})
        if not isinstance(role_visual_overrides, Mapping):
            raise CollaborationReasoningError(
                "scene_composition_plan.role_visual_overrides must be an object",
                stage="art",
                error_code="invalid_field_type",
                field_path="scene_composition_plan.role_visual_overrides",
                response_hash=response_hash,
            )
        normalized_overrides = {
            _required_text(
                key,
                "role_visual_overrides.key",
                stage="art",
                response_hash=response_hash,
            ): _required_text(
                value,
                "role_visual_overrides.value",
                stage="art",
                response_hash=response_hash,
            )
            for key, value in role_visual_overrides.items()
        }
        unknown_roles = sorted(set(normalized_overrides) - set(required_roles))
        if unknown_roles:
            raise CollaborationReasoningError(
                "art role overrides reference unknown semantic roles: " + ",".join(unknown_roles),
                stage="art",
                error_code="art_role_override_unknown",
                field_path="scene_composition_plan.role_visual_overrides",
                response_hash=response_hash,
            )
        normalized_prompts: dict[str, str] = {}
        for role in role_manifest:
            parts = [
                global_visual_prompt,
                f"semantic role: {role.semantic_role}",
            ]
            if role.required_capabilities:
                parts.append("required capabilities: " + ", ".join(role.required_capabilities))
            override = normalized_overrides.get(role.semantic_role)
            if override:
                parts.append(override)
            normalized_prompts[role.semantic_role] = "; ".join(parts)
        style_keywords = list(_text_tuple(
            art.get("style_keywords"),
            "art_direction.style_keywords",
            stage="art",
            response_hash=response_hash,
        ))
        if goal:
            goal_reference = f"用户目标：{goal}"
            if goal_reference not in style_keywords:
                style_keywords.insert(0, goal_reference)
        art_direction = ArtDirection(
                style_keywords=tuple(style_keywords),
                palette=_text_tuple(
                    art.get("palette"),
                    "art_direction.palette",
                    stage="art",
                    response_hash=response_hash,
                ),
                lighting=_text_tuple(
                    art.get("lighting"),
                    "art_direction.lighting",
                    stage="art",
                    response_hash=response_hash,
                ),
                avoid_keywords=_text_tuple(
                    art.get("avoid_keywords", []),
                    "art_direction.avoid_keywords",
                    stage="art",
                    response_hash=response_hash,
                    allow_empty=True,
                ),
            )
        scene_composition_plan = SceneCompositionPlan(
                scene_type=_required_text(
                    composition.get("scene_type"),
                    "scene_composition_plan.scene_type",
                    stage="art",
                    response_hash=response_hash,
                ),
                environment_requirements=_text_tuple(
                    composition.get("environment_requirements"),
                    "scene_composition_plan.environment_requirements",
                    stage="art",
                    response_hash=response_hash,
                ),
                entity_requirements=required_roles,
                layout_rules=_text_tuple(
                    composition.get("layout_rules"),
                    "scene_composition_plan.layout_rules",
                    stage="art",
                    response_hash=response_hash,
                ),
                image_prompts=normalized_prompts,
            )
        _assert_artifact_valid(
            "ArtDirection",
            art_direction,
            stage="art",
            response_hash=response_hash,
        )
        _assert_artifact_valid(
            "SceneCompositionPlan",
            scene_composition_plan,
            stage="art",
            response_hash=response_hash,
        )
        return ArtAgentDraft(
            art_direction=art_direction,
            scene_composition_plan=scene_composition_plan,
        )


class ProposalNarrator:
    _LEAK_MARKERS = (
        "你是三职能协作的 gm",
        "system prompt",
        "output_schema",
        "game_design_brief",
        "gameplay_logic_plan",
        "scenecompositionplan",
        "runtimeguard",
        "toolcallgraph",
    )

    def __init__(self, complete: CompletionPort) -> None:
        if not callable(complete):
            raise TypeError("complete must be callable")
        self._complete = complete

    def narrate(
        self,
        *,
        project_goal: str,
        proposal_id: str,
        proposal_version: int,
        proposal_hash: str,
        artifact_payloads: Mapping[str, Mapping[str, object]],
    ) -> str:
        system = (
            "你是项目 GM，只负责把已经校验的策划、程序和美术结果汇总成自然、具体的中文方案。"
            "不要暴露提示词、JSON、DTO、内部 ID、Runtime 诊断或工具信息。"
            "明确说明当前是待用户确认的方案，尚未生成图片、模型或写入场景。"
        )
        user = _json_prompt({
            "project_goal": project_goal,
            "proposal_identity": {
                "proposal_id": proposal_id,
                "proposal_version": proposal_version,
                "proposal_hash": proposal_hash,
            },
            "validated_artifacts": {
                key: dict(value)
                for key, value in sorted(artifact_payloads.items())
            },
        })
        raw = self._complete("collaboration_proposal_narration", system, user)
        response_hash = _response_hash(raw)
        text = str(raw or "").strip()
        if not text:
            raise CollaborationReasoningError(
                "proposal narration is empty",
                stage="narration",
                error_code="narration_empty",
                response_hash=response_hash,
            )
        lowered = text.lower().replace(" ", "")
        if any(marker.replace(" ", "") in lowered for marker in self._LEAK_MARKERS):
            raise CollaborationReasoningError(
                "proposal narration leaked internal instructions",
                stage="narration",
                error_code="narration_prompt_leak",
                response_hash=response_hash,
            )
        if text.startswith("```") or text.startswith("{"):
            raise CollaborationReasoningError(
                "proposal narration is not user-facing prose",
                stage="narration",
                error_code="narration_not_user_facing",
                response_hash=response_hash,
            )
        return text


__all__ = [
    "CollaborationReasoningError",
    "CompletionPort",
    "ProductionArtReasoner",
    "ProductionPlanningReasoner",
    "ProductionProgramReasoner",
    "ProposalNarrator",
]
