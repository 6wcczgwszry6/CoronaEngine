from __future__ import annotations

import os
from types import MethodType
from typing import Any, Literal


DEPRECATED_USER_WORKFLOW_COMMANDS = frozenset({
    "/scene_agent",
    "/sc_agent",
    "/scene_composition",
    "/scene_composition_v2",
    "/sc_v2",
    "/full_pipeline",
    "/pipeline",
    "/full_pipeline_v2",
    "/fp_v2",
    "/multi_scene",
    "/parallel_generate",
    "/parallel_generate_v2",
    "/pg_v2",
})

INTERNAL_DEBUG_WORKFLOW_COMMANDS = frozenset({
    "/model_retrieval",
    "/terrain_generate",
    "/terrain",
})

DEPRECATED_WORKFLOW_COMMAND_MESSAGE = (
    "该旧工作流入口已废弃。请在聊天室中先讨论并确认生成方案，"
    "再通过统一的 AI 场景生成链路执行。"
)

WorkflowCommandExposure = Literal["public", "internal", "deprecated", "invalid"]
WorkflowFunctionExposure = WorkflowCommandExposure


def normalize_workflow_command(command: str) -> str:
    value = str(command or "").strip().lower()
    if value and not value.startswith("/"):
        value = f"/{value}"
    return value


def is_deprecated_user_workflow_command(command: str) -> bool:
    return normalize_workflow_command(command) in DEPRECATED_USER_WORKFLOW_COMMANDS


def is_internal_debug_workflow_command(command: str) -> bool:
    return normalize_workflow_command(command) in INTERNAL_DEBUG_WORKFLOW_COMMANDS


def classify_workflow_command_exposure(command: str) -> WorkflowCommandExposure:
    normalized = normalize_workflow_command(command)
    if not normalized:
        return "invalid"
    if normalized in DEPRECATED_USER_WORKFLOW_COMMANDS:
        return "deprecated"
    if normalized in INTERNAL_DEBUG_WORKFLOW_COMMANDS:
        return "internal"
    return "public"


def should_register_workflow_command(command: str) -> bool:
    exposure = classify_workflow_command_exposure(command)
    if exposure == "invalid":
        return False
    if exposure == "deprecated":
        return False
    if exposure == "internal":
        return os.getenv("CORONA_ENABLE_INTERNAL_WORKFLOW_COMMANDS", "").strip() == "1"
    return True


def record_workflow_function_exposure(command_registry: Any, command: str, function_id: Any) -> None:
    """Remember the command-derived exposure for a workflow function_id.

    Slash command filtering alone is not enough because Quasar also supports
    explicit function_id execution.  We keep the mapping on the command registry
    instance so the workflow registry can later filter get/has/list calls without
    changing Quasar source.
    """

    if command_registry is None:
        return
    try:
        fid = int(function_id)
    except (TypeError, ValueError):
        return
    exposure = classify_workflow_command_exposure(command)
    if exposure == "invalid":
        return
    _workflow_function_exposure_set(command_registry, exposure).add(fid)


def classify_workflow_function_exposure(function_id: Any, command_registry: Any) -> WorkflowFunctionExposure:
    try:
        fid = int(function_id)
    except (TypeError, ValueError):
        return "invalid"

    # Deprecated main-control ids are terminal: a later public alias must not
    # accidentally resurrect an old workflow-driven entrypoint.
    if fid in _workflow_function_exposure_set(command_registry, "deprecated"):
        return "deprecated"
    # Internal debug ids can be made public intentionally by a future safe alias.
    if fid in _workflow_function_exposure_set(command_registry, "public"):
        return "public"
    if fid in _workflow_function_exposure_set(command_registry, "internal"):
        return "internal"
    return "public"


def should_execute_workflow_function(function_id: Any, command_registry: Any) -> bool:
    exposure = classify_workflow_function_exposure(function_id, command_registry)
    if exposure == "invalid":
        return False
    if exposure == "deprecated":
        return False
    if exposure == "internal":
        return os.getenv("CORONA_ENABLE_INTERNAL_WORKFLOW_COMMANDS", "").strip() == "1"
    return True


def install_workflow_command_policy(command_registry: Any) -> bool:
    """Patch a Quasar WorkflowCommandRegistry instance with Corona exposure policy.

    The Quasar registry can dynamically discover WORKFLOW_COMMANDS after our
    plugin registration path has already filtered them.  This adapter keeps the
    policy attached to the registry instance without editing Quasar itself.
    """

    if command_registry is None:
        return False
    _ensure_workflow_function_exposure_sets(command_registry)
    if getattr(command_registry, "_corona_workflow_command_policy_installed", False):
        _purge_hidden_workflow_commands(command_registry)
        return True

    original_register = getattr(command_registry, "register", None)
    original_resolve = getattr(command_registry, "resolve", None)
    original_list_commands = getattr(command_registry, "list_commands", None)
    original_discover = getattr(command_registry, "discover", None)

    if callable(original_register):
        setattr(command_registry, "_corona_original_register", original_register)

        def register_with_policy(self, command: str, function_id: int, *, overwrite: bool = False) -> None:
            record_workflow_function_exposure(self, command, function_id)
            if not should_register_workflow_command(command):
                return None
            return original_register(command, function_id, overwrite=overwrite)

        command_registry.register = MethodType(register_with_policy, command_registry)

    if callable(original_resolve):
        setattr(command_registry, "_corona_original_resolve", original_resolve)

        def resolve_with_policy(self, command: str) -> Any:
            if not should_register_workflow_command(command):
                return None
            return original_resolve(command)

        command_registry.resolve = MethodType(resolve_with_policy, command_registry)

    if callable(original_list_commands):
        setattr(command_registry, "_corona_original_list_commands", original_list_commands)

        def list_commands_with_policy(self) -> dict[str, int]:
            commands = original_list_commands()
            if not isinstance(commands, dict):
                return {}
            return {
                command: function_id
                for command, function_id in commands.items()
                if should_register_workflow_command(command)
            }

        command_registry.list_commands = MethodType(list_commands_with_policy, command_registry)

    if callable(original_discover):
        setattr(command_registry, "_corona_original_discover", original_discover)

        def discover_with_policy(self, *args: Any, **kwargs: Any) -> Any:
            result = original_discover(*args, **kwargs)
            _purge_hidden_workflow_commands(self)
            return result

        command_registry.discover = MethodType(discover_with_policy, command_registry)

    setattr(command_registry, "_corona_workflow_command_policy_installed", True)
    _purge_hidden_workflow_commands(command_registry)
    return True


def install_workflow_function_policy(workflow_registry: Any, command_registry: Any) -> bool:
    """Patch a Quasar WorkflowRegistry so hidden workflow ids are not executable."""

    if workflow_registry is None or command_registry is None:
        return False
    install_workflow_command_policy(command_registry)
    if getattr(workflow_registry, "_corona_workflow_function_policy_installed", False):
        return True

    original_get = getattr(workflow_registry, "get", None)
    original_has = getattr(workflow_registry, "has", None)
    original_list_function_ids = getattr(workflow_registry, "list_function_ids", None)
    original_discover = getattr(workflow_registry, "discover", None)

    if callable(original_get):
        setattr(workflow_registry, "_corona_original_get", original_get)

        def get_with_policy(self, function_id: int) -> Any:
            if not should_execute_workflow_function(function_id, command_registry):
                return None
            return original_get(function_id)

        workflow_registry.get = MethodType(get_with_policy, workflow_registry)

    if callable(original_has):
        setattr(workflow_registry, "_corona_original_has", original_has)

        def has_with_policy(self, function_id: int) -> bool:
            if not should_execute_workflow_function(function_id, command_registry):
                return False
            return bool(original_has(function_id))

        workflow_registry.has = MethodType(has_with_policy, workflow_registry)

    if callable(original_list_function_ids):
        setattr(workflow_registry, "_corona_original_list_function_ids", original_list_function_ids)

        def list_function_ids_with_policy(self) -> list[int]:
            function_ids = original_list_function_ids()
            return [
                function_id
                for function_id in function_ids
                if should_execute_workflow_function(function_id, command_registry)
            ]

        workflow_registry.list_function_ids = MethodType(list_function_ids_with_policy, workflow_registry)

    if callable(original_discover):
        setattr(workflow_registry, "_corona_original_discover", original_discover)

        def discover_with_policy(self, *args: Any, **kwargs: Any) -> Any:
            return original_discover(*args, **kwargs)

        workflow_registry.discover = MethodType(discover_with_policy, workflow_registry)

    setattr(workflow_registry, "_corona_workflow_function_policy_installed", True)
    return True


def _purge_hidden_workflow_commands(command_registry: Any) -> None:
    commands = getattr(command_registry, "_commands", None)
    if not isinstance(commands, dict):
        return
    for command in list(commands.keys()):
        if not should_register_workflow_command(str(command)):
            commands.pop(command, None)


def _ensure_workflow_function_exposure_sets(command_registry: Any) -> None:
    for exposure in ("public", "internal", "deprecated"):
        attr = f"_corona_{exposure}_workflow_function_ids"
        if not isinstance(getattr(command_registry, attr, None), set):
            setattr(command_registry, attr, set())


def _workflow_function_exposure_set(command_registry: Any, exposure: str) -> set[int]:
    _ensure_workflow_function_exposure_sets(command_registry)
    attr = f"_corona_{exposure}_workflow_function_ids"
    value = getattr(command_registry, attr)
    if isinstance(value, set):
        return value
    replacement: set[int] = set()
    setattr(command_registry, attr, replacement)
    return replacement


__all__ = [
    "DEPRECATED_USER_WORKFLOW_COMMANDS",
    "INTERNAL_DEBUG_WORKFLOW_COMMANDS",
    "DEPRECATED_WORKFLOW_COMMAND_MESSAGE",
    "WorkflowCommandExposure",
    "WorkflowFunctionExposure",
    "classify_workflow_function_exposure",
    "classify_workflow_command_exposure",
    "install_workflow_command_policy",
    "install_workflow_function_policy",
    "is_deprecated_user_workflow_command",
    "is_internal_debug_workflow_command",
    "normalize_workflow_command",
    "record_workflow_function_exposure",
    "should_execute_workflow_function",
    "should_register_workflow_command",
]
