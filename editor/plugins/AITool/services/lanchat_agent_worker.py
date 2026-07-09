from __future__ import annotations

import logging
import json
import os
import re
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable

from .interaction_coordinator import ChatMessage, InteractionCoordinator
from .seed_plan import SeedPlanStatus
from .lanchat_agent_orchestrator import LanChatAgentOrchestrator
from .lanchat_host_action_executor import LanChatHostActionExecutor
from .agent_runtime import AgentRuntime, AgentRuntimeFlags
from .intent_understanding import get_intent_understanding_service


MAX_COORDINATOR_SYNC_MESSAGES_PER_TICK = 4
MAX_ROOM_EVENTS_PER_TICK = 4
MAX_AGENT_RUNTIME_DRAIN_ROOMS_PER_TICK = 1
MAX_AGENT_RUNTIME_GRAPHS_PER_TICK = 1
MAX_AGENT_RUNTIME_DISCLOSURE_EVENT_LOOKBACK = 32
MAX_COORDINATOR_SEEN_MESSAGE_IDS = 2048
MAX_ACTIVE_ROOM_IDS = 256
_SENSITIVE_WORKER_PAYLOAD_KEYS = {
    "prompt",
    "raw_prompt",
    "provider",
    "model_provider",
    "runtime_context",
    "scheduler_updates",
    "vlm_raw",
    "hidden_debug_ref",
    "debug",
    "job_id",
    "session_id",
    "token",
    "api_key",
}
_SENSITIVE_WORKER_TEXT_MARKERS = tuple(sorted(_SENSITIVE_WORKER_PAYLOAD_KEYS))


def _trace_preview(value: Any, limit: int = 80) -> str:
    text = str(value or "").replace("\r", "\\r").replace("\n", "\\n")
    if len(text) > limit:
        return f"{text[:limit]}..."
    return text


class LANChatAgentWorker:
    """Poll C++ LANChat agent triggers and return replies through C++."""

    def __init__(
        self,
        corona_engine: Any = None,
        agent_factory: Callable[[], Any] | None = None,
        host_action_executor: Any = None,
        interaction_coordinator: InteractionCoordinator | None = None,
        generation_scheduler: Any = None,
        composer_factory: Callable[[], Any] | None = None,
        agent_runtime_flags: AgentRuntimeFlags | None = None,
        agent_runtime: AgentRuntime | None = None,
        sleep_seconds: float = 0.1,
        async_agent_execution: bool | None = None,
    ) -> None:
        self._corona_engine = corona_engine
        self._agent_factory = agent_factory
        self._host_action_executor = host_action_executor
        self._interaction_coordinator = interaction_coordinator
        self._generation_scheduler = generation_scheduler
        self._composer_factory = composer_factory
        self._logger = logging.getLogger(__name__)
        self._agent_runtime_flags = agent_runtime_flags or AgentRuntimeFlags.from_env()
        self._agent_runtime = agent_runtime or self._create_agent_runtime()
        self._owns_generation_scheduler = generation_scheduler is None and interaction_coordinator is None
        self._sleep_seconds = sleep_seconds
        self._async_agent_execution = (
            os.getenv("LANCHAT_AGENT_ASYNC", "1") == "1"
            if async_agent_execution is None
            else bool(async_agent_execution)
        )
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._orchestrator: LanChatAgentOrchestrator | None = None
        self._agent_call_lock = threading.RLock()
        self._coordinator_seen_message_ids: set[str] = set()
        self._coordinator_seen_message_order: deque[str] = deque()
        self._active_room_ids: set[str] = set()
        self._active_room_order: deque[str] = deque()
        self._progress_disclosure_lock = threading.RLock()
        self._progress_disclosure_last_by_room: dict[str, tuple[str, float]] = {}
        if self._generation_scheduler is not None:
            self._install_generation_scheduler_hooks(self._generation_scheduler)

    def _get_runtime_tool(self, name: str) -> Any:
        """Resolve a Quasar tool without importing legacy workflow packages."""

        tool_name = str(name or "").strip()
        if not tool_name:
            return None
        self._ensure_runtime_quasar_import_path()
        try:
            from plugins.AITool.Quasar.ai_config.ai_config import get_ai_config, reload_ai_config
            from plugins.AITool.Quasar.ai_tools.load_tools import load_tools
            from plugins.AITool.Quasar.ai_tools.registry import get_tool_registry
        except Exception as exc:  # noqa: BLE001
            try:
                from Quasar.ai_config.ai_config import get_ai_config, reload_ai_config
                from Quasar.ai_tools.load_tools import load_tools
                from Quasar.ai_tools.registry import get_tool_registry
            except Exception:
                self._logger.debug(
                    "AgentRuntime tool registry unavailable for %s: %s",
                    tool_name,
                    type(exc).__name__,
                )
                return None

        self._ensure_runtime_ai_config_loaded()
        config = getattr(self, "_runtime_ai_config_override", None)
        if config is None:
            try:
                config = get_ai_config()
            except Exception:  # noqa: BLE001
                config = None
        registry = get_tool_registry()
        self._ensure_runtime_engine_tool_loaders(registry)
        tool = registry.get(tool_name)
        if tool is not None:
            return tool
        tool = self._load_runtime_tool_direct(registry, config, tool_name)
        if tool is not None:
            return tool
        try:
            load_tools(config)
        except Exception as exc:  # noqa: BLE001
            try:
                config = reload_ai_config()
                load_tools(config)
            except Exception:  # noqa: BLE001
                pass
            self._logger.debug(
                "AgentRuntime tool load failed for %s: %s",
                tool_name,
                type(exc).__name__,
            )
        tool = registry.get(tool_name)
        if tool is not None:
            return tool
        try:
            registry.discover(config, force=True)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug(
                "AgentRuntime tool discovery failed for %s: %s",
                tool_name,
                type(exc).__name__,
            )
        return registry.get(tool_name)

    @staticmethod
    def _ensure_runtime_quasar_import_path() -> None:
        aitool_root = Path(__file__).resolve().parents[1]
        root_text = str(aitool_root)
        if root_text not in sys.path:
            sys.path.insert(0, root_text)

    def _load_runtime_tool_direct(self, registry: Any, config: Any, tool_name: str) -> Any:
        """Directly register narrow Runtime tools without loading all workflows."""

        try:
            if tool_name in {"import_model", "import_environment_component", "remove_model"}:
                from plugins.AITool.cai_extensions.mcp.tools.model_import_tools import load_model_import_tools

                for tool in load_model_import_tools():
                    if not registry.get(getattr(tool, "name", "")):
                        registry.register(tool, overwrite=False)
                return registry.get(tool_name)
            if tool_name == "get_scene_snapshot":
                from plugins.AITool.cai_extensions.mcp.tools.scene_snapshot import load_scene_snapshot_tools

                for tool in load_scene_snapshot_tools():
                    if not registry.get(getattr(tool, "name", "")):
                        registry.register(tool, overwrite=False)
                return registry.get(tool_name)
            if tool_name == "scene_rationality_review":
                from plugins.AITool.cai_extensions.mcp.tools.scene_review_tools import load_scene_review_tools

                for tool in load_scene_review_tools():
                    if not registry.get(getattr(tool, "name", "")):
                        registry.register(tool, overwrite=False)
                return registry.get(tool_name)
            if tool_name == "set_actor_transform":
                from plugins.AITool.cai_extensions.mcp.tools.set_actor_transform import load_set_actor_transform_tools

                for tool in load_set_actor_transform_tools():
                    if not registry.get(getattr(tool, "name", "")):
                        registry.register(tool, overwrite=False)
                return registry.get(tool_name)
            if tool_name == "hunyuan_generate_3d":
                try:
                    from plugins.AITool.Quasar.ai_modules.three_d_generate.tools.model_tools import load_hunyuan3d_tools
                except Exception:
                    from Quasar.ai_modules.three_d_generate.tools.model_tools import load_hunyuan3d_tools

                for tool in load_hunyuan3d_tools(config):
                    if not registry.get(getattr(tool, "name", "")):
                        registry.register(tool, overwrite=False)
                return registry.get(tool_name)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug(
                "AgentRuntime direct tool load failed for %s: %s",
                tool_name,
                type(exc).__name__,
            )
        return None

    def _ensure_runtime_ai_config_loaded(self) -> None:
        """Load narrow AI config modules needed by Runtime providers."""

        if getattr(self, "_runtime_ai_config_loaded", False):
            return
        try:
            from plugins.AITool.Quasar.ai_modules.three_d_generate.tools import loader as _hunyuan_loader  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            try:
                from Quasar.ai_modules.three_d_generate.tools import loader as _hunyuan_loader  # noqa: F401
            except Exception:
                self._logger.debug(
                    "AgentRuntime Hunyuan config loader unavailable: %s",
                    type(exc).__name__,
                )
        try:
            from plugins.AITool import utils as _aitool_utils  # noqa: F401
            from plugins.AITool.utils import ai_setting as _ai_setting  # noqa: F401
            self._mirror_plugin_ai_settings_to_runtime_namespace()
        except Exception as exc:  # noqa: BLE001
            self._logger.debug(
                "AgentRuntime local AI setting module unavailable: %s",
                type(exc).__name__,
            )
        self._runtime_ai_config_loaded = True

    def _mirror_plugin_ai_settings_to_runtime_namespace(self) -> None:
        """Bridge plugin-qualified Quasar settings into the Runtime Quasar namespace."""

        try:
            from plugins.AITool.Quasar.ai_service.entrance import ai_entrance as plugin_entrance
            from Quasar.ai_service.entrance import ai_entrance as runtime_entrance
        except Exception as exc:  # noqa: BLE001
            self._logger.debug(
                "AgentRuntime AI setting namespace bridge unavailable: %s",
                type(exc).__name__,
            )
            return
        plugin_settings = plugin_entrance.collector.AI_SETTINGS
        if not isinstance(plugin_settings, dict) or not plugin_settings:
            return
        runtime_collector = runtime_entrance.collector
        try:
            runtime_collector._ai_settings.update(plugin_settings)
            for key, value in plugin_settings.items():
                loader = runtime_collector._ai_load.get(key)
                if loader is not None:
                    setattr(runtime_collector._ai_config, key, loader(value))
            self._runtime_ai_config_override = runtime_collector.AIConfig
        except Exception as exc:  # noqa: BLE001
            self._logger.debug(
                "AgentRuntime AI setting namespace bridge failed: %s",
                type(exc).__name__,
            )

    def _ensure_runtime_engine_tool_loaders(self, registry: Any) -> None:
        """Ensure host engine tools are visible before Runtime provider lookup."""

        try:
            loaders = list(getattr(registry, "_loaders", []) or [])
            existing_sources = {str(getattr(spec, "source", "") or "") for spec in loaders}
            required_sources = {
                "cai_extensions.mcp.model_import",
                "cai_extensions.mcp.scene_review",
                "cai_extensions.mcp.scene_snapshot",
                "cai_extensions.mcp.set_actor_transform",
            }
            if required_sources.issubset(existing_sources):
                return
            try:
                from Quasar.ai_tools.load_tools import register_extra_builtin_registrar
            except Exception:
                from plugins.AITool.Quasar.ai_tools.load_tools import register_extra_builtin_registrar
            from plugins.AITool.cai_extensions.engine_tools import register_engine_loaders

            register_extra_builtin_registrar(register_engine_loaders)
            register_engine_loaders(registry)
            setattr(registry, "_discovered", False)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug(
                "AgentRuntime engine tool loader registration unavailable: %s",
                type(exc).__name__,
            )

    def _create_agent_runtime(self) -> AgentRuntime:
        """Create the Runtime control plane with optional narrow legacy adapters.

        The adapters are explicitly feature-flagged and function-sized.  They do
        not re-enable SceneComposer / ProgressiveWorkflow as a main workflow.
        """

        kwargs: dict[str, Any] = {}
        provider_diagnostics: dict[str, dict[str, Any]] = {}

        def note_provider(key: str, *, requested: bool, status: str, reason: str = "") -> None:
            provider_diagnostics[key] = {
                "requested": bool(requested),
                "status": str(status or ""),
                "reason": str(reason or ""),
            }

        if (
            self._corona_engine is not None
            and self._agent_runtime_flags.can_use_scene_snapshot_provider()
        ):
            try:
                from .agent_runtime import make_scene_snapshot_provider

                snapshot_tool = self._get_runtime_tool("get_scene_snapshot")
                if snapshot_tool is not None:
                    kwargs["scene_snapshot_provider"] = make_scene_snapshot_provider(
                        snapshot_tool=snapshot_tool,
                    )
                    note_provider("scene_snapshot", requested=True, status="enabled")
                else:
                    note_provider("scene_snapshot", requested=True, status="unavailable", reason="missing_tool:get_scene_snapshot")
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).debug("AgentRuntime scene snapshot provider disabled: %s", type(exc).__name__)
                note_provider("scene_snapshot", requested=True, status="unavailable", reason="adapter_load_failed")
        elif self._agent_runtime_flags.can_use_scene_snapshot_provider():
            note_provider("scene_snapshot", requested=True, status="unavailable", reason="missing_engine")
        if self._agent_runtime_flags.can_use_image_resource_provider():
            try:
                from .agent_runtime import make_image_resource_provider

                image_tool = self._get_runtime_tool("generate_image")
                if image_tool is not None:
                    kwargs["image_resource_provider"] = make_image_resource_provider(
                        image_tool=image_tool,
                    )
                    note_provider("image_resource", requested=True, status="enabled")
                else:
                    note_provider("image_resource", requested=True, status="unavailable", reason="missing_tool:generate_image")
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).debug("AgentRuntime image provider disabled: %s", type(exc).__name__)
                note_provider("image_resource", requested=True, status="unavailable", reason="adapter_load_failed")
        if self._agent_runtime_flags.can_use_scene_review_provider():
            try:
                from .agent_runtime import make_scene_review_provider

                review_tool = self._get_runtime_tool("scene_rationality_review")
                if review_tool is not None:
                    review_provider = make_scene_review_provider(
                        review_tool=review_tool,
                    )
                    kwargs["review_provider"] = review_provider
                    kwargs["vlm_review_provider"] = review_provider
                    note_provider("review", requested=True, status="enabled")
                    note_provider("vlm_review", requested=True, status="enabled")
                else:
                    note_provider("review", requested=True, status="unavailable", reason="missing_tool:scene_rationality_review")
                    note_provider("vlm_review", requested=True, status="unavailable", reason="missing_tool:scene_rationality_review")
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).debug("AgentRuntime scene review provider disabled: %s", type(exc).__name__)
                note_provider("review", requested=True, status="unavailable", reason="adapter_load_failed")
                note_provider("vlm_review", requested=True, status="unavailable", reason="adapter_load_failed")
        if self._agent_runtime_flags.can_use_environment_component_provider():
            note_provider(
                "environment_component",
                requested=True,
                status="unavailable",
                reason="not_initialized",
            )
            try:
                from .agent_runtime import make_environment_component_provider

                environment_tool = None
                environment_tool_name = ""
                for candidate in (
                    "create_environment_component",
                    "create_terrain_component",
                    "create_scene_substrate",
                ):
                    environment_tool = self._get_runtime_tool(candidate)
                    if environment_tool is not None:
                        environment_tool_name = candidate
                        break
                if environment_tool is not None:
                    kwargs["environment_component_provider"] = make_environment_component_provider(
                        environment_tool=environment_tool,
                    )
                    note_provider("environment_component", requested=True, status="enabled", reason=environment_tool_name)
                else:
                    note_provider(
                        "environment_component",
                        requested=True,
                        status="unavailable",
                        reason="missing_tool:create_environment_component",
                    )
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).debug("AgentRuntime environment component provider disabled: %s", type(exc).__name__)
                note_provider("environment_component", requested=True, status="unavailable", reason="adapter_load_failed")
        use_engine_environment_import_provider = (
            self._corona_engine is not None
            and self._agent_runtime_flags.can_use_engine_environment_import_provider()
        )
        if use_engine_environment_import_provider:
            try:
                from .agent_runtime import make_engine_environment_component_import_provider
                from plugins.AITool.cai_extensions.agent.engine_write_gate import get_engine_write_gate

                environment_import_tool = None
                environment_import_tool_name = ""
                for candidate in (
                    "import_environment_component",
                    "create_environment_actor",
                    "create_environment_component",
                    "create_terrain_component",
                    "create_scene_substrate",
                ):
                    environment_import_tool = self._get_runtime_tool(candidate)
                    if environment_import_tool is not None:
                        environment_import_tool_name = candidate
                        break
                if environment_import_tool is not None:
                    kwargs["environment_import_provider"] = make_engine_environment_component_import_provider(
                        environment_import_tool=environment_import_tool,
                        engine_gate=get_engine_write_gate(),
                    )
                    note_provider("environment_import", requested=True, status="enabled", reason=environment_import_tool_name)
                else:
                    note_provider(
                        "environment_import",
                        requested=True,
                        status="unavailable",
                        reason="missing_tool:import_environment_component",
                    )
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).debug("AgentRuntime environment import provider disabled: %s", type(exc).__name__)
                note_provider("environment_import", requested=True, status="unavailable", reason="adapter_load_failed")
        elif self._agent_runtime_flags.can_use_engine_environment_import_provider():
            note_provider("environment_import", requested=True, status="unavailable", reason="missing_engine")
        model_resource_provider_enabled = False
        if self._agent_runtime_flags.can_use_model_resource_provider():
            try:
                from .agent_runtime import make_model_resource_provider

                model_tool = self._get_runtime_tool("hunyuan_generate_3d")
                if model_tool is not None:
                    kwargs["model_resource_provider"] = make_model_resource_provider(
                        model_tool=model_tool,
                    )
                    model_resource_provider_enabled = True
                    note_provider("model_resource", requested=True, status="enabled")
                else:
                    note_provider("model_resource", requested=True, status="unavailable", reason="missing_tool:hunyuan_generate_3d")
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).debug("AgentRuntime model provider disabled: %s", type(exc).__name__)
                note_provider("model_resource", requested=True, status="unavailable", reason="adapter_load_failed")
        if self._agent_runtime_flags.can_use_legacy_model_resource_provider():
            try:
                from .agent_runtime import make_legacy_model_resource_provider

                if "model_resource_provider" not in kwargs:
                    kwargs["model_resource_provider"] = make_legacy_model_resource_provider()
                    model_resource_provider_enabled = True
                    note_provider("model_resource", requested=True, status="enabled", reason="legacy_model_provider")
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).debug("AgentRuntime legacy model provider disabled: %s", type(exc).__name__)
                note_provider("model_resource", requested=True, status="unavailable", reason="adapter_load_failed")
        use_engine_actor_import_provider = (
            self._corona_engine is not None
            and model_resource_provider_enabled
            and (
                self._agent_runtime_flags.agent_runtime_enabled
                or self._agent_runtime_flags.can_use_engine_actor_import_provider()
            )
        )
        if use_engine_actor_import_provider:
            try:
                from .agent_runtime import make_engine_actor_import_provider
                from plugins.AITool.cai_extensions.agent.engine_write_gate import get_engine_write_gate

                import_tool = self._get_runtime_tool("import_model")
                if import_tool is not None:
                    kwargs["actor_import_provider"] = make_engine_actor_import_provider(
                        import_tool=import_tool,
                        engine_gate=get_engine_write_gate(),
                    )
                    note_provider("actor_import", requested=True, status="enabled", reason="import_model")
                else:
                    note_provider("actor_import", requested=True, status="unavailable", reason="missing_tool:import_model")
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).debug("AgentRuntime engine import provider disabled: %s", type(exc).__name__)
                note_provider("actor_import", requested=True, status="unavailable", reason="adapter_load_failed")
        elif self._agent_runtime_flags.can_use_engine_actor_import_provider():
            reason = "missing_engine"
            if self._corona_engine is not None and not model_resource_provider_enabled:
                reason = "missing_model_resource_provider"
            note_provider("actor_import", requested=True, status="unavailable", reason=reason)
        if (
            self._corona_engine is not None
            and self._agent_runtime_flags.can_use_engine_actor_delete_provider()
        ):
            try:
                from .agent_runtime import make_engine_actor_delete_provider
                from plugins.AITool.cai_extensions.agent.engine_write_gate import get_engine_write_gate

                delete_tool = None
                delete_tool_name = ""
                for candidate in (
                    "remove_actor",
                    "delete_actor",
                    "destroy_actor",
                ):
                    delete_tool = self._get_runtime_tool(candidate)
                    if delete_tool is not None:
                        delete_tool_name = candidate
                        break
                if delete_tool is not None:
                    kwargs["actor_delete_provider"] = make_engine_actor_delete_provider(
                        delete_tool=delete_tool,
                        engine_gate=get_engine_write_gate(),
                    )
                    note_provider("actor_delete", requested=True, status="enabled", reason=delete_tool_name)
                else:
                    note_provider("actor_delete", requested=True, status="unavailable", reason="missing_tool:remove_actor")
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).debug("AgentRuntime engine delete provider disabled: %s", type(exc).__name__)
                note_provider("actor_delete", requested=True, status="unavailable", reason="adapter_load_failed")
        elif self._agent_runtime_flags.can_use_engine_actor_delete_provider():
            note_provider("actor_delete", requested=True, status="unavailable", reason="missing_engine")
        if (
            self._corona_engine is not None
            and self._agent_runtime_flags.can_use_engine_layout_transform_provider()
        ):
            try:
                from .agent_runtime import make_engine_layout_transform_provider
                from plugins.AITool.cai_extensions.agent.engine_write_gate import get_engine_write_gate

                transform_tool = self._get_runtime_tool("set_actor_transform")
                if transform_tool is not None:
                    kwargs["layout_transform_provider"] = make_engine_layout_transform_provider(
                        transform_tool=transform_tool,
                        engine_gate=get_engine_write_gate(),
                    )
                    note_provider("layout_transform", requested=True, status="enabled")
                else:
                    note_provider("layout_transform", requested=True, status="unavailable", reason="missing_tool:set_actor_transform")
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).debug("AgentRuntime engine transform provider disabled: %s", type(exc).__name__)
                note_provider("layout_transform", requested=True, status="unavailable", reason="adapter_load_failed")
        elif self._agent_runtime_flags.can_use_engine_layout_transform_provider():
            note_provider("layout_transform", requested=True, status="unavailable", reason="missing_engine")
        if provider_diagnostics:
            kwargs["provider_diagnostics"] = provider_diagnostics
        return AgentRuntime(**kwargs)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        if not self._has_engine_api():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="LANChatAgentWorker",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 1.0) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        if self._generation_scheduler is not None:
            self._clear_generation_scheduler_hooks(self._generation_scheduler)
        if self._owns_generation_scheduler and self._generation_scheduler is not None:
            shutdown = getattr(self._generation_scheduler, "shutdown", None)
            if callable(shutdown):
                shutdown()

    def generation_scheduler_snapshot(self) -> dict[str, Any]:
        if not self._agent_runtime_flags.can_call_legacy_main_workflow():
            return {"available": False, "reason": "legacy generation scheduler is disabled"}
        scheduler = self._generation_scheduler
        if scheduler is None:
            return {"available": False, "reason": "generation scheduler has not been initialized"}
        snapshot = getattr(scheduler, "public_snapshot", None)
        if not callable(snapshot):
            snapshot = getattr(scheduler, "snapshot", None)
        if not callable(snapshot):
            return {"available": False, "reason": "generation scheduler does not expose snapshot"}
        data = snapshot()
        if isinstance(data, dict):
            return {"available": True, **data}
        return {"available": False, "reason": "generation scheduler snapshot returned non-dict"}

    def generation_scheduler_session_snapshot(self, session_id: str) -> dict[str, Any]:
        if not self._agent_runtime_flags.can_call_legacy_main_workflow():
            return {"available": False, "reason": "legacy generation scheduler is disabled"}
        scheduler = self._generation_scheduler
        if scheduler is None:
            return {"available": False, "reason": "generation scheduler has not been initialized"}
        session_snapshot = getattr(scheduler, "public_session_snapshot", None)
        if not callable(session_snapshot):
            session_snapshot = getattr(scheduler, "session_snapshot", None)
        if not callable(session_snapshot):
            return {"available": False, "reason": "generation scheduler does not expose session_snapshot"}
        data = session_snapshot(session_id)
        if isinstance(data, dict):
            return {"available": True, **data}
        return {"available": False, "reason": "generation scheduler session_snapshot returned non-dict"}

    def cancel_generation_session(self, session_id: str, *, abandon_remote: bool = False) -> dict[str, Any]:
        if not self._agent_runtime_flags.can_call_legacy_main_workflow():
            return {"available": False, "reason": "legacy generation scheduler is disabled"}
        scheduler = self._generation_scheduler
        if scheduler is None:
            return {"available": False, "reason": "generation scheduler has not been initialized"}
        cancel_session = getattr(scheduler, "cancel_session", None)
        if not callable(cancel_session):
            return {"available": False, "reason": "generation scheduler does not expose cancel_session"}
        result = cancel_session(session_id, abandon_remote=abandon_remote)
        if isinstance(result, dict):
            return {"available": True, **result}
        return {"available": False, "reason": "generation scheduler cancel_session returned non-dict"}

    def handle_lanchat_room_event(self, event: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(event, dict):
            return {"handled": False, "reason": "event is not a dict"}
        event_type = str(event.get("event") or event.get("type") or "").strip().lower()
        room_id = str(event.get("room_id") or event.get("room") or "").strip()
        if room_id:
            self._remember_room_id(room_id)
        if event_type not in {"room_closed", "leave_room", "left", "stop_room", "stopped", "closed"}:
            if room_id:
                self._record_lanchat_sync_event_in_agent_runtime(event, room_id=room_id)
            return {"handled": False, "reason": "event does not close a room"}
        target_rooms = [room_id] if room_id else sorted(self._active_room_ids)
        if not target_rooms:
            return {"handled": True, "cancelled": [], "reason": "no active room id known"}
        cancelled = []
        runtime_sync = []
        runtime_cancel = []
        for target_room in target_rooms:
            runtime_sync.append(self._record_lanchat_sync_event_in_agent_runtime(event, room_id=target_room))
            runtime_cancel.append(self._cancel_agent_runtime_room_plan(event, room_id=target_room))
            cancelled.append(self.cancel_generation_session(target_room, abandon_remote=True))
            self._forget_room_id(target_room)
        return {"handled": True, "cancelled": cancelled, "runtime_sync": runtime_sync, "runtime_cancel": runtime_cancel}

    def handle_lanchat_sync_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Mirror a LANChat / C++ sync event into AgentRuntime without owning sync.

        This is the narrow bridge for future actor / asset transfer callbacks.
        It intentionally does not broadcast, import, transform, or cancel
        anything; C++ remains the source of network truth.
        """

        if not isinstance(event, dict):
            return {"handled": False, "reason": "event is not a dict"}
        room_id = str(event.get("room_id") or event.get("room") or "").strip()
        if not room_id:
            return {"handled": False, "reason": "missing room id"}
        self._remember_room_id(room_id)
        result = self._record_lanchat_sync_event_in_agent_runtime(event, room_id=room_id)
        return {"handled": bool(result.get("recorded")), "runtime_sync": result}

    def _record_lanchat_sync_event_in_agent_runtime(
        self,
        event: dict[str, Any],
        *,
        room_id: str,
    ) -> dict[str, Any]:
        runtime = self._agent_runtime
        if runtime is None:
            return {"recorded": False, "reason": "agent runtime unavailable"}
        try:
            result = runtime.handle_message(
                room_id=str(room_id or event.get("room_id") or event.get("room") or "default"),
                text=str(event.get("event") or event.get("type") or "sync event"),
                action="runtime_sync_event",
                sync_event=dict(event),
            )
            recorded = bool(result.get("recorded"))
            return {
                "recorded": recorded,
                "reason": "" if recorded else self._safe_lanchat_sync_bridge_reason(result.get("message")),
                "event": dict(result.get("sync_event") or {}),
                "sync_state": dict(result.get("sync_status") or {}),
            }
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("AgentRuntime sync event mirror failed: %s", type(exc).__name__)
            return {"recorded": False, "reason": "internal_exception", "error_type": type(exc).__name__}

    @staticmethod
    def _safe_lanchat_sync_bridge_reason(message: Any) -> str:
        text = str(message or "").strip()
        if not text:
            return "runtime_sync_rejected"
        lowered = text.lower()
        unsafe_tokens = (
            "provider",
            "prompt",
            "api_key",
            "token=",
            "secret",
            "raw",
            "payload",
            "traceback",
            "http://",
            "https://",
            ".glb",
            ".obj",
            ".json",
            ":/",
            ":\\",
        )
        if any(token in lowered for token in unsafe_tokens):
            return "runtime_sync_rejected"
        safe = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff ]+", " ", text)
        safe = re.sub(r"\s+", " ", safe).strip()
        return safe[:120] or "runtime_sync_rejected"

    def _cancel_agent_runtime_room_plan(
        self,
        event: dict[str, Any],
        *,
        room_id: str,
    ) -> dict[str, Any]:
        runtime = self._agent_runtime
        if runtime is None:
            return {"recorded": False, "reason": "agent runtime unavailable"}
        event_type = str(event.get("event") or event.get("type") or "room_closed").strip()
        try:
            result = runtime.handle_message(
                room_id=str(room_id or event.get("room_id") or event.get("room") or "default"),
                text=f"room lifecycle event: {event_type}",
                sender_id="",
                sender_name="",
                action="cancel_generation",
            )
            command = result.get("command", {}) if isinstance(result, dict) else {}
            command = command if isinstance(command, dict) else {}
            return {
                "recorded": bool(result.get("recorded") or command.get("applied")),
                "reason": "" if bool(result.get("recorded") or command.get("applied")) else str(command.get("reason") or result.get("message") or ""),
                "command": str(command.get("command") or "cancel"),
                "plan_id": str(command.get("plan_id") or ""),
                "new_status": str(command.get("new_status") or ""),
                "cancelled_batches": int(command.get("cancelled_batches") or 0),
                "cancelled_graphs": int(command.get("cancelled_graphs") or 0),
            }
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("AgentRuntime room lifecycle cancel failed: %s", type(exc).__name__)
            return {
                "recorded": False,
                "reason": "internal_exception",
                "error_type": type(exc).__name__,
                "command": "cancel",
            }

    def sync_chat_message_to_coordinator(
        self,
        message: dict[str, Any],
        *,
        source: str = "lanchat_direct",
        emit_disclosure: bool = True,
    ) -> bool:
        """Sync one ordinary LANChat user/host message into InteractionCoordinator.

        This is the Python bridge point for non-@Agent chat messages. It does
        not run role agents or execute generation; Coordinator decides whether
        the message updates a SeedPlan draft or becomes a batch intervention.
        """
        if not isinstance(message, dict):
            return False
        self._apply_generation_options_from_message(message)
        message_kind = str(message.get("message_kind") or "chat").lower()
        sender_type = str(message.get("sender_type") or "user").lower()
        dedupe_key = self._coordinator_sync_dedupe_key(message, source=source)
        if not dedupe_key:
            self._logger.info(
                "[LANChatSyncTrace] phase=skip_no_dedupe source=%s message_id=%s room=%s sender=%s/%s text=%s",
                source,
                message.get("message_id") or "",
                message.get("room_id") or "",
                message.get("sender_type") or "",
                message.get("sender_id") or message.get("from") or "",
                _trace_preview(message.get("text")),
            )
            return False
        if dedupe_key in self._coordinator_seen_message_ids:
            self._logger.info(
                "[LANChatSyncTrace] phase=dedupe_skip source=%s dedupe=%s message_id=%s room=%s sender=%s/%s text=%s",
                source,
                dedupe_key,
                message.get("message_id") or "",
                message.get("room_id") or "",
                message.get("sender_type") or "",
                message.get("sender_id") or message.get("from") or "",
                _trace_preview(message.get("text")),
            )
            return False
        self._logger.info(
            "[LANChatSyncTrace] phase=received source=%s dedupe=%s message_id=%s correlation=%s room=%s kind=%s sender=%s/%s/%s target=%s/%s text=%s",
            source,
            dedupe_key,
            message.get("message_id") or "",
            message.get("correlation_id") or "",
            message.get("room_id") or "",
            message_kind,
            sender_type,
            message.get("sender_id") or message.get("from") or "",
            message.get("sender_name") or "",
            message.get("target_agent_id") or message.get("agent_id") or "",
            message.get("target_agent_name") or message.get("agent_name") or "",
            _trace_preview(message.get("text")),
        )
        if message_kind != "chat" or sender_type not in {"user", "host"}:
            self._logger.info(
                "[LANChatSyncTrace] phase=skip_non_chat source=%s dedupe=%s kind=%s sender_type=%s",
                source,
                dedupe_key,
                message_kind,
                sender_type,
            )
            self._remember_coordinator_seen_message_id(dedupe_key)
            return False
        text = str(message.get("text") or "").strip()
        if not text:
            self._logger.info(
                "[LANChatSyncTrace] phase=skip_empty_text source=%s dedupe=%s message_id=%s",
                source,
                dedupe_key,
                message.get("message_id") or "",
            )
            self._remember_coordinator_seen_message_id(dedupe_key)
            return False
        room_id = str(message.get("room_id") or "default")
        self._remember_room_id(room_id)
        if self._is_generation_start_text(text):
            runtime_generation_reply = self._execute_active_runtime_plan_generation(
                message,
                room_id=room_id,
                host_id=str(message.get("sender_id") or message.get("from") or ""),
            )
            if runtime_generation_reply is not None:
                self._send_coordinator_sync_system_reply(message, runtime_generation_reply)
                self._log_scene_route(
                    room_id=room_id,
                    sender=str(message.get("sender_name") or message.get("sender_id") or ""),
                    target_agent=str(message.get("target_agent_name") or message.get("agent_name") or ""),
                    room_state="runtime",
                    intent="generation_start",
                    action="confirm_and_execute",
                    reason=f"runtime_first source={source}",
                )
                self._remember_coordinator_seen_message_id(dedupe_key)
                return True
        if self._is_runtime_status_query_text(text):
            runtime_external_plan_id = self._active_runtime_external_plan_id(room_id)
            if runtime_external_plan_id:
                runtime_batch_id = self._runtime_batch_id_from_message(message)
                runtime_status_reply = self._agent_runtime_status_reply(
                    room_id=room_id,
                    external_plan_id=runtime_external_plan_id,
                    batch_id=runtime_batch_id,
                )
                if runtime_status_reply:
                    self._send_coordinator_sync_system_reply(message, runtime_status_reply)
                    self._log_scene_route(
                        room_id=room_id,
                        sender=str(message.get("sender_name") or message.get("sender_id") or ""),
                        target_agent=str(message.get("target_agent_name") or message.get("agent_name") or ""),
                        room_state="runtime",
                        intent="status_query",
                        action="runtime_status",
                        reason=f"runtime_first source={source}",
                    )
                    self._remember_coordinator_seen_message_id(dedupe_key)
                    return True
        runtime_plan_update_reply = self._handle_active_runtime_plan_context_update(message, text)
        if runtime_plan_update_reply:
            self._send_coordinator_sync_system_reply(message, runtime_plan_update_reply)
            self._log_scene_route(
                room_id=room_id,
                sender=str(message.get("sender_name") or message.get("sender_id") or ""),
                target_agent=str(message.get("target_agent_name") or message.get("agent_name") or ""),
                room_state="runtime",
                intent="plan_update",
                action="plan_supplement",
                reason=f"runtime_active_plan_context source={source}",
            )
            self._remember_coordinator_seen_message_id(dedupe_key)
            return True
        try:
            coordinator = self._get_interaction_coordinator()
            disclosure_start = len(coordinator.disclosure_events)
            metadata = self._coordinator_sync_metadata(message, source=source)
            metadata = self._normalize_coordinator_target_metadata(message, text, metadata)
            active = coordinator.active_plan_for_room(room_id)
            self._logger.info(
                "[LANChatSyncTrace] phase=route_start source=%s dedupe=%s room=%s active=%s plan=%s draft_action=%s target_scope=%s target_agent=%s/%s metadata_keys=%s",
                source,
                dedupe_key,
                room_id,
                str(active.status.value if active is not None else "none"),
                str(getattr(active, "plan_id", "") or ""),
                metadata.get("draft_action") or "",
                metadata.get("target_scope") or "",
                metadata.get("target_agent_id") or "",
                metadata.get("target_agent_name") or "",
                ",".join(sorted(str(key) for key in metadata.keys())),
            )
            authoritative_synced = False
            if self._should_sync_metadata_scene_message_to_seed_plan(coordinator, room_id, text, metadata):
                sender_is_host = self._message_sender_is_host(message, sender_type=sender_type)
                self._logger.info(
                    "[LANChatSyncTrace] phase=authoritative_ingest source=%s dedupe=%s room=%s sender=%s host=%s text=%s",
                    source,
                    dedupe_key,
                    room_id,
                    message.get("sender_id") or message.get("from") or "",
                    sender_is_host,
                    _trace_preview(text),
                )
                coordinator.ingest_message(ChatMessage(
                    room_id=room_id,
                    sender_id=str(message.get("sender_id") or message.get("from") or ""),
                    sender_name=str(message.get("sender_name") or message.get("from") or ""),
                    text=text,
                    is_host=sender_is_host,
                    agent_id=str(metadata.get("target_agent_id") or ""),
                    agent_name=str(metadata.get("target_agent_name") or ""),
                    metadata=metadata,
                ))
                authoritative_synced = True
                active = coordinator.active_plan_for_room(room_id)
            structured_handled = self._handle_structured_chat_route(message, text, metadata)
            if structured_handled:
                self._logger.info(
                    "[LANChatSyncTrace] phase=structured_handled source=%s dedupe=%s room=%s action=%s authoritative=%s active=%s plan=%s",
                    source,
                    dedupe_key,
                    room_id,
                    structured_handled,
                    authoritative_synced,
                    str(active.status.value if active is not None else "none"),
                    str(getattr(active, "plan_id", "") or ""),
                )
                self._log_scene_route(
                    room_id=room_id,
                    sender=str(message.get("sender_name") or message.get("sender_id") or ""),
                    target_agent=str(
                        metadata.get("target_agent_name")
                        or metadata.get("target_agent_id")
                        or message.get("target_agent_name")
                        or message.get("agent_name")
                        or ""
                    ),
                    room_state=str(active.status.value if active is not None else "structured"),
                    intent=str(metadata.get("draft_action") or "structured"),
                    action=structured_handled,
                    reason="metadata route",
                )
                return True
            if (
                source == "lanchat_history_snapshot"
                and active is not None
                and active.status == SeedPlanStatus.COMPLETED
                and not coordinator._is_status_query(text)
                and coordinator._intent_type(text) != "add"
                and not coordinator._is_post_generation_adjustment(text)
            ):
                return False
            planning_gate_handled = ""
            if source != "lanchat_history_snapshot":
                planning_gate_handled = self._handle_plain_chat_planning_gate(message, text)
            if planning_gate_handled in {"reply", "compose"}:
                self._logger.info(
                    "[LANChatSyncTrace] phase=planning_gate_handled source=%s dedupe=%s room=%s action=%s authoritative=%s",
                    source,
                    dedupe_key,
                    room_id,
                    planning_gate_handled,
                    authoritative_synced,
                )
                self._log_scene_route(
                    room_id=room_id,
                    sender=str(message.get("sender_name") or message.get("sender_id") or ""),
                    target_agent=str(message.get("target_agent_name") or message.get("agent_name") or ""),
                    room_state="planning",
                    intent="planning_gate",
                    action=planning_gate_handled,
                    reason="pending planning message",
                )
                return True
            if self._is_generation_start_text(text):
                if active is None:
                    generation_reply = self._execute_active_runtime_plan_generation(
                        message,
                        room_id=room_id,
                        host_id=str(message.get("sender_id") or message.get("from") or ""),
                    )
                else:
                    generation_reply = self._start_active_coordinator_generation(
                        coordinator,
                        room_id=room_id,
                        host_id=str(message.get("sender_id") or message.get("from") or ""),
                    )
                if generation_reply is not None:
                    self._send_coordinator_sync_system_reply(message, generation_reply)
                    self._log_scene_route(
                        room_id=room_id,
                        sender=str(message.get("sender_name") or message.get("sender_id") or ""),
                        target_agent=str(message.get("target_agent_name") or message.get("agent_name") or ""),
                        room_state=str(coordinator.active_plan_for_room(room_id).status.value if coordinator.active_plan_for_room(room_id) is not None else "none"),
                        intent="generation_start",
                        action="confirm_and_execute",
                        reason=f"source={source}",
                    )
                    return True
            if authoritative_synced:
                self._mirror_planning_context_in_agent_runtime(
                    room_id=room_id,
                    text=text,
                    trigger=message,
                    plan=active,
                    metadata=metadata,
                )
                self._logger.info(
                    "[LANChatSyncTrace] phase=authoritative_only_done source=%s dedupe=%s room=%s plan=%s",
                    source,
                    dedupe_key,
                    room_id,
                    str(getattr(active, "plan_id", "") or ""),
                )
                if emit_disclosure:
                    self._emit_new_disclosure_events(coordinator, disclosure_start)
                return True
            if not planning_gate_handled and not self._should_sync_chat_to_coordinator(coordinator, room_id, text, source=source):
                self._mirror_user_context_in_agent_runtime(
                    room_id=room_id,
                    text=text,
                    trigger=message,
                    plan=active,
                    metadata=metadata,
                )
                self._logger.info(
                    "[LANChatSyncTrace] phase=skip_not_scene_write source=%s dedupe=%s room=%s active=%s text=%s",
                    source,
                    dedupe_key,
                    room_id,
                    str(active.status.value if active is not None else "none"),
                    _trace_preview(text),
                )
                self._log_scene_route(
                    room_id=room_id,
                    sender=str(message.get("sender_name") or message.get("sender_id") or ""),
                    target_agent=str(message.get("target_agent_name") or message.get("agent_name") or ""),
                    room_state=str(active.status.value if active is not None else "none"),
                    intent="chat",
                    action="skip_coordinator",
                    reason="not scene-write intent",
                )
                return False
            event = coordinator.ingest_message(ChatMessage(
                room_id=room_id,
                sender_id=str(message.get("sender_id") or message.get("from") or ""),
                sender_name=str(message.get("sender_name") or message.get("from") or ""),
                text=text,
                is_host=self._message_sender_is_host(message, sender_type=sender_type),
                agent_id=str(metadata.get("target_agent_id") or ""),
                agent_name=str(metadata.get("target_agent_name") or ""),
                metadata=metadata,
            ))
            event_type = str(getattr(event, "event_type", "") or "")
            runtime_adjustment_recorded = False
            if event_type in {"layout_reflow_proposal_created", "layout_reflow_confirmed", "layout_reflow_rejected", "layout_reflow_confirmation_failed"}:
                reply = str(getattr(event, "message", "") or "")
                if event_type == "layout_reflow_confirmed":
                    payload = getattr(event, "payload", {}) or {}
                    if self._agent_runtime_flags.can_call_legacy_main_workflow():
                        executed = self._execute_layout_reflow_confirmation(payload)
                    else:
                        self._record_completed_adjustment_in_agent_runtime(
                            room_id=room_id,
                            text=text,
                            trigger=message,
                            plan=active,
                            event=event,
                        )
                        runtime_adjustment_recorded = True
                        executed = self._confirm_layout_reflow_via_agent_runtime(
                            room_id=room_id,
                            plan=active,
                            payload=payload,
                        )
                    if executed:
                        reply = f"{reply}\n{executed}" if reply else executed
                if reply:
                    self._send_coordinator_sync_system_reply(message, reply)
            updated = coordinator.active_plan_for_room(room_id)
            if event_type not in {
                "intervention_routed",
                "post_generation_add_routed",
                "final_adjustment_routed",
                "layout_reflow_proposal_created",
                "layout_reflow_confirmed",
                "layout_reflow_rejected",
                "layout_reflow_confirmation_failed",
                "status_query",
            }:
                self._mirror_planning_context_in_agent_runtime(
                    room_id=room_id,
                    text=text,
                    trigger=message,
                    plan=updated or active,
                    metadata=metadata,
                )
            if event_type in {
                "intervention_routed",
                "post_generation_add_routed",
                "final_adjustment_routed",
                "layout_reflow_proposal_created",
                "layout_reflow_confirmed",
            }:
                if not runtime_adjustment_recorded:
                    self._record_completed_adjustment_in_agent_runtime(
                        room_id=room_id,
                        text=text,
                        trigger=message,
                        plan=updated or active,
                        event=event,
                    )
            self._logger.info(
                "[LANChatSyncTrace] phase=coordinator_ingested source=%s dedupe=%s room=%s before=%s after=%s plan=%s design_len=%s",
                source,
                dedupe_key,
                room_id,
                str(active.status.value if active is not None else "none"),
                str(updated.status.value if updated is not None else "none"),
                str(getattr(updated, "plan_id", "") or ""),
                len(str(getattr(updated, "design_brief", "") or "")) if updated is not None else 0,
            )
            self._log_scene_route(
                room_id=room_id,
                sender=str(message.get("sender_name") or message.get("sender_id") or ""),
                target_agent=str(message.get("target_agent_name") or message.get("agent_name") or ""),
                room_state=str(active.status.value if active is not None else "draft"),
                intent="scene_write",
                action="coordinator_ingest",
                reason=f"source={source}",
            )
            if emit_disclosure:
                self._emit_new_disclosure_events(coordinator, disclosure_start)
            return True
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to sync LANChat chat message to Coordinator: %s", type(exc).__name__)
            return False
        finally:
            self._remember_coordinator_seen_message_id(dedupe_key)

    def _mirror_planning_context_in_agent_runtime(
        self,
        *,
        room_id: str,
        text: str,
        trigger: dict[str, Any],
        plan: Any,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        if plan is None or self._agent_runtime is None:
            return {"mirrored": False, "reason": "missing plan or runtime"}
        status = getattr(plan, "status", None)
        if status in {SeedPlanStatus.EXECUTING, SeedPlanStatus.COMPLETED, SeedPlanStatus.PAUSED}:
            return {"mirrored": False, "reason": f"plan status is {getattr(status, 'value', status)}"}
        external_plan_id = str(getattr(plan, "plan_id", "") or metadata.get("target_plan_id") or "").strip()
        if not external_plan_id:
            return {"mirrored": False, "reason": "missing external plan id"}
        design_text = (
            str(getattr(plan, "design_brief", "") or "").strip()
            or str(getattr(plan, "intent_summary", "") or "").strip()
            or str(text or "").strip()
        )
        if not design_text:
            return {"mirrored": False, "reason": "missing design text"}
        owner_agent = (
            str(getattr(plan, "owner_agent_name", "") or "").strip()
            or str(getattr(plan, "owner_agent", "") or "").strip()
            or str(metadata.get("target_agent_name") or metadata.get("target_agent_id") or "").strip()
        )
        source_agents = list(getattr(plan, "source_context_agents", []) or [])
        source_context_agent = str(metadata.get("source_context_agent") or "").strip()
        if source_context_agent and source_context_agent not in source_agents:
            source_agents.append(source_context_agent)
        try:
            runtime_result = self._agent_runtime.handle_message(
                room_id=str(room_id or trigger.get("room_id") or "default"),
                external_plan_id=external_plan_id,
                text=design_text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                owner_agent=owner_agent,
                source_context_agents=source_agents,
                action="plan",
                reply_to=str(trigger.get("message_id") or ""),
            )
            runtime_plan = dict(runtime_result.get("plan") or {})
            runtime_plan_id = str(runtime_plan.get("plan_id") or "")
            self._logger.info(
                "[LANChatRuntimeTrace] phase=planning_context_mirrored room=%s external_plan=%s runtime_plan=%s status=%s text=%s",
                room_id,
                external_plan_id,
                runtime_plan_id,
                getattr(status, "value", status),
                _trace_preview(design_text),
            )
            return {"mirrored": bool(runtime_plan_id), "runtime_plan_id": runtime_plan_id}
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime planning context mirror failed: %s", type(exc).__name__)
            return {"mirrored": False, "reason": "internal_exception", "error_type": type(exc).__name__}

    def _mirror_agent_reply_context_in_agent_runtime(
        self,
        *,
        room_id: str,
        text: str,
        trigger: dict[str, Any],
        agent_id: str,
        agent_name: str,
    ) -> dict[str, Any]:
        runtime = self._agent_runtime
        if runtime is None:
            return {"recorded": False, "reason": "agent runtime unavailable"}
        room = str(room_id or trigger.get("room_id") or "default")
        reply_text = str(text or "").strip()
        if not reply_text:
            return {"recorded": False, "reason": "empty text"}
        external_plan_id = str(
            trigger.get("target_plan_id")
            or trigger.get("plan_id")
            or trigger.get("seed_plan_id")
            or ""
        ).strip()
        if not external_plan_id:
            external_plan_id = self._active_runtime_external_plan_id(room)
        if not external_plan_id and self._agent_runtime_flags.can_call_legacy_main_workflow():
            try:
                coordinator = self._get_interaction_coordinator()
                active = coordinator.active_plan_for_room(room)
                external_plan_id = str(getattr(active, "plan_id", "") or "").strip()
            except Exception:  # noqa: BLE001
                external_plan_id = ""
        try:
            should_promote = self._should_promote_agent_reply_to_runtime_plan(trigger, reply_text)
            if should_promote and not external_plan_id:
                handled = runtime.handle_message(
                    room_id=room,
                    external_plan_id="",
                    text=reply_text,
                    sender_id=str(agent_id or ""),
                    sender_name=str(agent_name or ""),
                    owner_agent=str(agent_name or ""),
                    reply_to=str(trigger.get("message_id") or ""),
                    action="plan",
                )
                plan = dict(handled.get("plan", {}) or {}) if isinstance(handled, dict) else {}
                runtime_plan_id = str(plan.get("plan_id") or "")
                recorded = bool(runtime_plan_id)
                if recorded:
                    self._logger.info(
                        "[LANChatRuntimeTrace] phase=agent_reply_plan_promoted room=%s runtime_plan=%s agent=%s/%s reply_to=%s text=%s",
                        room,
                        runtime_plan_id,
                        agent_id,
                        agent_name,
                        trigger.get("message_id") or "",
                        _trace_preview(reply_text),
                    )
                return {
                    "recorded": recorded,
                    "runtime_plan_id": runtime_plan_id,
                    "context_id": "",
                    "updated_plan_brief": recorded,
                }
            handled = runtime.handle_message(
                room_id=room,
                external_plan_id=external_plan_id,
                text=reply_text,
                sender_id=str(agent_id or ""),
                sender_name=str(agent_name or ""),
                owner_agent=str(agent_name or ""),
                reply_to=str(trigger.get("message_id") or ""),
                action="agent_reply" if should_promote else "agent_context",
            )
            result = dict(handled.get("context", {}) or {}) if isinstance(handled, dict) else {}
            if result.get("recorded"):
                self._logger.info(
                    "[LANChatRuntimeTrace] phase=agent_reply_context_recorded room=%s external_plan=%s runtime_plan=%s agent=%s/%s reply_to=%s text=%s",
                    room,
                    external_plan_id,
                    result.get("runtime_plan_id") or "",
                    agent_id,
                    agent_name,
                    trigger.get("message_id") or "",
                    _trace_preview(reply_text),
                )
            return result
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime agent reply context mirror failed: %s", type(exc).__name__)
            return {"recorded": False, "reason": "internal_exception", "error_type": type(exc).__name__}

    def _record_gm_proposal_send_in_agent_runtime(
        self,
        *,
        phase: str,
        room_id: str,
        proposal_id: str,
        external_plan_id: str,
        agent_id: str,
        agent_name: str,
        message: str,
        sent: bool | None = None,
    ) -> dict[str, Any]:
        room = str(room_id or "default")
        external_plan = str(external_plan_id or "").strip()
        payload: dict[str, Any] = {
            "proposal_id": str(proposal_id or ""),
            "external_plan_id": external_plan,
            "agent_id": str(agent_id or ""),
            "agent_name": str(agent_name or ""),
            "message_kind": "gm_proposal",
        }
        if sent is not None:
            payload["sent"] = bool(sent)
        return self._record_runtime_audit_event(
            event=phase,
            room_id=room,
            external_plan_id=external_plan,
            message=str(message or ""),
            payload=payload,
        )

    def _record_agent_reply_send_in_agent_runtime(
        self,
        *,
        phase: str,
        room_id: str,
        trigger: dict[str, Any],
        agent_id: str,
        agent_name: str,
        message: str,
        message_kind: str,
        sent: bool | None = None,
    ) -> dict[str, Any]:
        room = str(room_id or trigger.get("room_id") or "default")
        external_plan_id = str(
            trigger.get("target_plan_id")
            or trigger.get("plan_id")
            or trigger.get("seed_plan_id")
            or ""
        ).strip()
        if not external_plan_id:
            external_plan_id = self._active_runtime_external_plan_id(room)
        payload: dict[str, Any] = {
            "external_plan_id": external_plan_id,
            "agent_id": str(agent_id or ""),
            "agent_name": str(agent_name or ""),
            "message_kind": str(message_kind or "agent_reply"),
            "reply_to": str(trigger.get("message_id") or ""),
        }
        if sent is not None:
            payload["sent"] = bool(sent)
        return self._record_runtime_audit_event(
            event=phase,
            room_id=room,
            external_plan_id=external_plan_id,
            message=str(message or ""),
            payload=payload,
        )

    def _record_runtime_audit_event(
        self,
        *,
        event: str,
        room_id: str,
        message: str = "",
        payload: dict[str, Any] | None = None,
        external_plan_id: str = "",
        runtime_plan_id: str = "",
        batch_id: str = "",
    ) -> dict[str, Any]:
        runtime = self._agent_runtime
        if runtime is None:
            return {"recorded": False, "reason": "agent runtime unavailable"}
        try:
            result = runtime.handle_message(
                room_id=str(room_id or "default"),
                text=str(message or ""),
                action="runtime_audit_event",
                external_plan_id=str(external_plan_id or ""),
                sync_event={
                    "event": str(event or ""),
                    "message": str(message or ""),
                    "batch_id": str(batch_id or ""),
                    "payload": {
                        **dict(payload or {}),
                        "runtime_plan_id": str(runtime_plan_id or ""),
                    },
                },
            )
            return {
                "recorded": bool(result.get("recorded")),
                "event": str(result.get("event") or ""),
                "runtime_plan_id": str(result.get("runtime_plan_id") or ""),
            }
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime audit event record failed: %s", type(exc).__name__)
            return {"recorded": False, "reason": "internal_exception", "error_type": type(exc).__name__}

    def _should_promote_agent_reply_to_runtime_plan(self, trigger: dict[str, Any], reply_text: str) -> bool:
        user_text = str((trigger or {}).get("text") or "").strip()
        if user_text:
            try:
                from .intent_understanding import IntentUnderstandingService

                decision = IntentUnderstandingService().classify(
                    user_text,
                    allow_llm=False,
                    generation_active=False,
                )
                if decision.intent in {"plan_drafting", "plan_revision"}:
                    return True
                if decision.intent in {"status_query", "discussion"}:
                    return False
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("AgentRuntime reply promotion intent skipped: %s", type(exc).__name__)
        reply = str(reply_text or "").strip()
        if not reply:
            return False
        plan_markers = (
            "方案内容", "方案展开", "布局", "核心物件", "物品清单",
            "风格定位", "空间布局", "建议先做", "设计方案",
            "鏂规鍐呭", "鏂规灞曞紑", "甯冨眬", "鏍稿績鐗╀欢", "鐗╁搧娓呭崟",
            "椋庢牸瀹氫綅", "绌洪棿甯冨眬", "寤鸿鍏堝仛", "璁捐鏂规",
        )
        return any(marker in reply for marker in plan_markers)

    def _mirror_user_context_in_agent_runtime(
        self,
        *,
        room_id: str,
        text: str,
        trigger: dict[str, Any],
        plan: Any,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        runtime = self._agent_runtime
        if runtime is None:
            return {"recorded": False, "reason": "agent runtime unavailable"}
        user_text = str(text or "").strip()
        if not user_text:
            return {"recorded": False, "reason": "empty text"}
        external_plan_id = str(
            metadata.get("target_plan_id")
            or metadata.get("plan_id")
            or getattr(plan, "plan_id", "")
            or ""
        ).strip()
        try:
            handled = runtime.handle_message(
                room_id=str(room_id or trigger.get("room_id") or "default"),
                external_plan_id=external_plan_id,
                text=user_text,
                action="user_discussion",
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                reply_to=str(trigger.get("message_id") or ""),
            )
            result = dict(handled.get("context", {}) or {})
            if result.get("recorded"):
                self._logger.info(
                    "[LANChatRuntimeTrace] phase=user_context_recorded room=%s external_plan=%s runtime_plan=%s sender=%s reply_to=%s text=%s",
                    room_id,
                    external_plan_id,
                    result.get("runtime_plan_id") or "",
                    trigger.get("sender_name") or trigger.get("sender_id") or trigger.get("from") or "",
                    trigger.get("message_id") or "",
                    _trace_preview(user_text),
                )
            return result
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime user context mirror failed: %s", type(exc).__name__)
            return {"recorded": False, "reason": "internal_exception", "error_type": type(exc).__name__}

    def _should_sync_metadata_scene_message_to_seed_plan(
        self,
        coordinator: InteractionCoordinator,
        room_id: str,
        text: str,
        metadata: dict[str, Any],
    ) -> bool:
        if not metadata:
            return False
        draft_action = str(metadata.get("draft_action") or "").strip().lower()
        target_scope = str(metadata.get("target_scope") or "").strip().lower()
        if draft_action in {"supplement", "generate"} or target_scope == "plan":
            return True
        if draft_action != "chat":
            return False
        active = coordinator.active_plan_for_room(room_id)
        if active is not None and active.status in {SeedPlanStatus.CONFIRMED, SeedPlanStatus.EXECUTING, SeedPlanStatus.PAUSED}:
            return False
        return self._looks_like_seedplan_design_message(text)

    @staticmethod
    def _looks_like_seedplan_design_message(text: str) -> bool:
        raw = str(text or "").strip()
        if not raw:
            return False
        opinion_patterns = ("怎么看", "你觉得", "大家觉得", "对于", "评价", "看法")
        strong_update_words = ("采用", "按", "确认", "补充", "新增", "调整", "修改", "生成", "开始")
        if any(word in raw for word in opinion_patterns) and not any(word in raw for word in strong_update_words):
            return False
        scene_words = (
            "方案", "场景", "主题", "设计", "布局", "风格", "物品", "清单",
            "集市", "鬼市", "卧室", "客厅", "房间", "展厅", "商业空间",
            "草原", "电竞房", "庭院", "街区", "摊位",
        )
        action_words = (
            "围绕", "讨论", "设计", "优化", "简化", "采用", "生成", "做",
            "帮我", "补充", "调整", "新增", "改成", "还是", "整理",
        )
        return any(word in raw for word in scene_words) and any(word in raw for word in action_words)

    def _handle_structured_chat_route(
        self,
        message: dict[str, Any],
        text: str,
        metadata: dict[str, Any],
    ) -> str:
        metadata = self._normalize_coordinator_target_metadata(message, text, metadata)
        draft_action = str(metadata.get("draft_action") or "").strip().lower()
        target_scope = str(metadata.get("target_scope") or "").strip().lower()
        target_agent_id = str(metadata.get("target_agent_id") or "").strip()
        target_agent_name = str(metadata.get("target_agent_name") or "").strip()
        target_plan_id = str(metadata.get("target_plan_id") or "").strip()
        source = str(metadata.get("source") or "").strip()
        if not any((draft_action, target_scope, target_agent_id, target_agent_name, target_plan_id)):
            return ""
        if not self._can_execute_agent_locally():
            self._logger.info(
                "[LANChatAgentTrace] phase=blocked_non_host_agent route=structured_chat role=%s message_id=%s room=%s action=%s target_scope=%s target_agent=%s/%s text=%s",
                self._network_session_role_name(),
                message.get("message_id") or "",
                message.get("room_id") or "",
                draft_action,
                target_scope,
                target_agent_id,
                target_agent_name,
                _trace_preview(text),
            )
            return "blocked_non_host_agent"
        if draft_action == "chat" and self._structured_chat_should_defer_to_runtime_route(text):
            return ""
        if draft_action == "chat" and target_scope == "group":
            group_agents = self._structured_group_agents(metadata)
            if not group_agents:
                return ""
            for agent_id, agent_name in group_agents:
                trigger = self._structured_trigger(message, metadata, agent_id=agent_id, agent_name=agent_name)
                self._process_trigger(trigger)
            return "group_chat"
        if draft_action == "chat" and (target_agent_id or target_agent_name or target_scope == "agent"):
            if source == "lanchat_native_queue":
                self._logger.info(
                    "[LANChatAgentTrace] phase=defer_structured_agent_route source=%s message_id=%s room=%s target_agent=%s/%s text=%s",
                    source,
                    message.get("message_id") or "",
                    message.get("room_id") or "",
                    target_agent_id,
                    target_agent_name,
                    _trace_preview(text),
                )
                return "agent_chat"
            agent_id = target_agent_id or target_agent_name or "agent"
            agent_name = target_agent_name or target_agent_id or "Agent"
            trigger = self._structured_trigger(message, metadata, agent_id=agent_id, agent_name=agent_name)
            self._process_trigger(trigger)
            return "agent_chat"
        if draft_action in {"plan", "supplement", "generate"} or target_scope == "plan" or target_plan_id:
            return self._handle_structured_planning_gate(message, text, metadata)
        if draft_action == "gm_control" or target_scope == "gm":
            trigger = self._structured_trigger(
                message,
                metadata,
                agent_id=target_agent_id or "gm",
                agent_name=target_agent_name or "GM",
            )
            self._process_trigger(trigger)
            return "gm_control"
        return ""

    def _structured_chat_should_defer_to_runtime_route(self, text: str) -> bool:
        if self._is_generation_start_text(text):
            return True
        try:
            from .intent_understanding import IntentUnderstandingService

            decision = IntentUnderstandingService().classify(
                str(text or ""),
                allow_llm=False,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Structured chat intent deferral skipped: %s", type(exc).__name__)
            return False
        return decision.intent in {
            "plan_drafting",
            "plan_revision",
            "generation_start",
            "intervention_add",
            "intervention_modify",
            "intervention_delete",
            "post_generation_add",
            "final_adjustment_request",
        }

    def _handle_structured_planning_gate(
        self,
        message: dict[str, Any],
        text: str,
        metadata: dict[str, Any],
    ) -> str:
        try:
            from .lanchat_scene_runtime import get_lanchat_scene_runtime
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to import LANChat scene runtime for metadata planning route: %s", type(exc).__name__)
            return ""
        draft_action = str(metadata.get("draft_action") or "").strip().lower()
        target = (
            str(metadata.get("target_plan_id") or "").strip()
            or str(metadata.get("target_agent_name") or "").strip()
            or str(metadata.get("target_agent_id") or "").strip()
        )
        try:
            runtime = get_lanchat_scene_runtime()
            if draft_action == "plan":
                agent_name = (
                    str(metadata.get("target_agent_name") or "").strip()
                    or str(metadata.get("target_agent_id") or "").strip()
                    or "璁捐鍔╂墜"
                )
                action, payload = runtime.handle_planning_gate(agent_name, text)
                if action == "pass":
                    return ""
            elif target:
                action, payload, agent_name = runtime.handle_targeted_planning_message(
                    target,
                    text,
                    draft_action=draft_action,
                    source_context_agent=str(metadata.get("source_context_agent") or ""),
                )
            else:
                agent_name = str(metadata.get("target_agent_name") or metadata.get("target_agent_id") or "").strip()
                action, payload = runtime.handle_planning_gate(agent_name or "璁捐鍔╂墜", text)
                if action == "pass":
                    return ""
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to handle metadata planning route: %s", type(exc).__name__)
            return ""
        if action not in {"reply", "compose"} or not agent_name:
            return ""
        trigger = self._structured_trigger(
            message,
            metadata,
            agent_id=str(metadata.get("target_agent_id") or agent_name),
            agent_name=str(agent_name),
        )
        if action == "reply":
            self._send_final_reply(str(trigger.get("agent_id") or agent_name), str(agent_name), str(payload or ""), trigger)
            return "planning_reply"
        if self._execute_runtime_planning_compose(trigger, str(payload or text), str(agent_name)):
            return "planning_compose"
        if not self._agent_runtime_flags.can_call_legacy_main_workflow():
            self._send_final_reply(
                "gm-system",
                "绯荤粺",
                "AgentRuntime 暂不可用，旧生成链路已关闭，已阻止直接生成。",
                trigger,
            )
            return "planning_compose_blocked"
        trigger["text"] = str(payload or text)
        self._process_trigger(trigger)
        return "planning_compose"

    def _structured_trigger(
        self,
        message: dict[str, Any],
        metadata: dict[str, Any],
        *,
        agent_id: str,
        agent_name: str,
    ) -> dict[str, Any]:
        trigger = dict(message)
        trigger["agent_id"] = str(agent_id or "agent")
        trigger["agent_name"] = str(agent_name or "Agent")
        trigger["target_agent_id"] = str(agent_id or "")
        trigger["target_agent_name"] = str(agent_name or "")
        trigger["metadata"] = dict(metadata or {})
        trigger["metadata_json"] = json.dumps(trigger["metadata"], ensure_ascii=False)
        return trigger

    @staticmethod
    def _structured_group_agents(metadata: dict[str, Any]) -> list[tuple[str, str]]:
        names_raw = metadata.get("target_agent_names")
        ids_raw = metadata.get("target_agent_ids")
        names = names_raw if isinstance(names_raw, list) else []
        ids = ids_raw if isinstance(ids_raw, list) else []
        out: list[tuple[str, str]] = []
        for index, raw_name in enumerate(names):
            name = str(raw_name or "").strip()
            if not name:
                continue
            agent_id = str(ids[index] if index < len(ids) else name).strip() or name
            out.append((agent_id, name))
        return out

    def _handle_plain_chat_planning_gate(self, message: dict[str, Any], text: str) -> str:
        if not self._can_execute_agent_locally():
            self._logger.info(
                "[LANChatAgentTrace] phase=blocked_non_host_agent route=plain_planning_gate role=%s message_id=%s room=%s text=%s",
                self._network_session_role_name(),
                message.get("message_id") or "",
                message.get("room_id") or "",
                _trace_preview(text),
            )
            return ""
        try:
            from .lanchat_scene_runtime import get_lanchat_scene_runtime
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to import LANChat scene runtime for plain planning gate: %s", type(exc).__name__)
            return ""
        try:
            action, payload, agent_name = get_lanchat_scene_runtime().handle_pending_planning_message(text)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to handle plain chat planning gate: %s", type(exc).__name__)
            return ""
        if action not in {"reply", "compose"} or not agent_name:
            return ""
        trigger = dict(message)
        trigger.setdefault("agent_id", str(agent_name))
        trigger.setdefault("agent_name", str(agent_name))
        trigger.setdefault("target_agent_id", str(agent_name))
        trigger.setdefault("target_agent_name", str(agent_name))
        self._seed_agent_trigger_planning_context_in_runtime(trigger)
        if action == "reply":
            self._mirror_runtime_planning_reply_context(trigger, str(payload or ""), str(agent_name))
            self._send_final_reply(str(agent_name), str(agent_name), str(payload or ""), trigger)
            return "reply"
        if self._execute_runtime_planning_compose(trigger, str(payload or text), str(agent_name)):
            return "compose"
        if not self._agent_runtime_flags.can_call_legacy_main_workflow():
            self._send_final_reply(
                "gm-system",
                "绯荤粺",
                "AgentRuntime 暂不可用，旧生成链路已关闭，已阻止直接生成。",
                trigger,
            )
            return "compose_blocked"
        trigger["text"] = str(payload or text)
        self._process_trigger(trigger)
        return "compose"

    def _handle_agent_trigger_planning_gate(self, trigger: dict[str, Any]) -> bool:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return False
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return False
        is_gm_target = (
            str(trigger.get("agent_id") or trigger.get("target_agent_id") or "").strip().lower() == "gm"
            or str(trigger.get("agent_name") or "").strip().lower() in {"gm", "主持人", "裁判", "game master"}
        )
        if is_gm_target:
            return False
        try:
            from .lanchat_scene_runtime import get_lanchat_scene_runtime
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to import LANChat scene runtime for agent planning gate: %s", type(exc).__name__)
            return False

        metadata = self._metadata_from_trigger(trigger)
        draft_action = str(metadata.get("draft_action") or "").strip().lower()
        targets = [
            str(metadata.get("target_plan_id") or "").strip(),
            str(metadata.get("target_agent_name") or "").strip(),
            str(metadata.get("target_agent_id") or "").strip(),
            str(trigger.get("target_agent_name") or "").strip(),
            str(trigger.get("agent_name") or "").strip(),
            str(trigger.get("target_agent_id") or "").strip(),
            str(trigger.get("agent_id") or "").strip(),
        ]
        try:
            runtime = get_lanchat_scene_runtime()
            for target in targets:
                if not target:
                    continue
                action, payload, agent_name = runtime.handle_targeted_planning_message(
                    target,
                    text,
                    draft_action=draft_action,
                    source_context_agent=str(metadata.get("source_context_agent") or ""),
                )
                if action in {"reply", "compose"} and agent_name:
                    return self._send_runtime_planning_action(trigger, action, payload, agent_name)
            action, payload, agent_name = runtime.handle_pending_planning_message(text)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to handle agent planning gate: %s", type(exc).__name__)
            return False
        if action in {"reply", "compose"} and agent_name:
            return self._send_runtime_planning_action(trigger, action, payload, agent_name)
        return False

    def _mirror_runtime_planning_reply_context(
        self,
        trigger: dict[str, Any],
        payload: str,
        agent_name: str,
    ) -> dict[str, Any]:
        if not self._agent_runtime_flags.agent_runtime_enabled:
            return {"recorded": False, "reason": "agent runtime disabled"}
        text = str(payload or "").strip()
        if not text:
            return {"recorded": False, "reason": "empty payload"}
        room_id = str((trigger or {}).get("room_id") or "default")
        external_plan_id = self._runtime_planning_external_id(trigger or {}, agent_name)
        metadata = self._metadata_from_trigger(trigger or {})
        source_context_agent = str(metadata.get("source_context_agent") or "").strip()
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                external_plan_id=external_plan_id,
                text=text,
                sender_id=str((trigger or {}).get("agent_id") or (trigger or {}).get("target_agent_id") or agent_name),
                sender_name=str(agent_name or (trigger or {}).get("agent_name") or ""),
                owner_agent=str(agent_name or (trigger or {}).get("agent_name") or ""),
                source_context_agents=[source_context_agent] if source_context_agent else [],
                action="plan_supplement",
                reply_to=str((trigger or {}).get("message_id") or ""),
            )
            return {"recorded": True, "runtime": result}
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime planning reply mirror failed: %s", type(exc).__name__)
            return {"recorded": False, "reason": "internal_exception", "error_type": type(exc).__name__}

    def _seed_agent_trigger_planning_context_in_runtime(self, trigger: dict[str, Any]) -> dict[str, Any]:
        if not self._agent_runtime_flags.agent_runtime_enabled:
            return {"recorded": False, "reason": "agent runtime disabled"}
        text = str(trigger.get("text") or "").strip()
        if not text:
            return {"recorded": False, "reason": "empty text"}
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return {"recorded": False, "reason": "non-chat message"}
        is_gm_target = (
            str(trigger.get("agent_id") or trigger.get("target_agent_id") or "").strip().lower() == "gm"
            or str(trigger.get("agent_name") or "").strip().lower() in {"gm", "主持人", "裁判", "game master"}
        )
        if is_gm_target:
            return {"recorded": False, "reason": "gm target"}
        try:
            from .intent_understanding import IntentUnderstandingService

            decision = IntentUnderstandingService().classify(text, allow_llm=False, generation_active=False)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime planning seed intent skipped: %s", type(exc).__name__)
            return {"recorded": False, "reason": "intent unavailable"}
        if decision.intent not in {"plan_drafting", "plan_revision"}:
            return {"recorded": False, "reason": f"intent:{decision.intent}"}
        room_id = str(trigger.get("room_id") or "default")
        agent_name = str(trigger.get("agent_name") or trigger.get("target_agent_name") or decision.target_agent or "")
        external_plan_id = self._runtime_planning_external_id(trigger, agent_name)
        metadata = self._metadata_from_trigger(trigger)
        source_context_agent = (
            str(metadata.get("source_context_agent") or "").strip()
            or self._source_context_agent_from_text(text)
        )
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                external_plan_id=external_plan_id,
                text=text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                owner_agent=agent_name,
                source_context_agents=[source_context_agent] if source_context_agent else [],
                action="plan",
                reply_to=str(trigger.get("message_id") or ""),
            )
            action = "plan_context"
            self._logger.info(
                "[LANChatRuntimeTrace] phase=agent_trigger_planning_seeded room=%s external_plan=%s action=%s intent=%s text=%s",
                room_id,
                external_plan_id,
                action,
                decision.intent,
                _trace_preview(text),
            )
            return {"recorded": True, "action": action, "runtime": result}
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime planning seed failed: %s", type(exc).__name__)
            return {"recorded": False, "reason": "internal_exception", "error_type": type(exc).__name__}

    def _handle_agent_trigger_runtime_write_gate(
        self,
        trigger: dict[str, Any],
        *,
        planning_seed: dict[str, Any] | None = None,
    ) -> bool:
        if self._agent_runtime_flags.can_call_legacy_main_workflow():
            return False
        text = str(trigger.get("text") or "").strip()
        if not text:
            return False
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return False
        is_gm_target = (
            str(trigger.get("agent_id") or trigger.get("target_agent_id") or "").strip().lower() == "gm"
            or str(trigger.get("agent_name") or "").strip().lower() in {"gm", "主持人", "裁判", "game master"}
        )
        if is_gm_target:
            return False
        room_id = str(trigger.get("room_id") or "default")
        try:
            decision = get_intent_understanding_service().classify(
                text,
                allow_llm=False,
                generation_active=bool(self._active_runtime_external_plan_id(room_id)),
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime write-gate intent skipped: %s", type(exc).__name__)
            return False
        runtime_draft_recorded = isinstance(planning_seed, dict) and bool(planning_seed.get("recorded"))
        if decision.intent not in {
            "generation_start",
            "intervention_add",
            "intervention_modify",
            "intervention_delete",
            "post_generation_add",
            "final_adjustment_request",
        } and not (decision.intent == "plan_drafting" and runtime_draft_recorded):
            return False
        self._record_runtime_audit_event(
            event="legacy_role_agent_scene_write_blocked",
            room_id=room_id,
            message=text,
            payload={
                "intent": decision.intent,
                "route": decision.route,
                "target_agent": str(trigger.get("agent_name") or trigger.get("target_agent_name") or ""),
                "reason": "agent_runtime_required",
            },
            external_plan_id=self._active_runtime_external_plan_id(room_id),
        )
        if (
            decision.intent in {"generation_start", "plan_drafting"}
            and runtime_draft_recorded
        ):
            runtime_result = planning_seed.get("runtime")
            runtime_result = runtime_result if isinstance(runtime_result, dict) else {}
            runtime_plan = runtime_result.get("plan")
            runtime_plan = runtime_plan if isinstance(runtime_plan, dict) else {}
            runtime_plan_id = str(runtime_plan.get("plan_id") or "").strip()
            plan_ref = f" {runtime_plan_id}" if runtime_plan_id else ""
            reply = (
                f"AgentRuntime 方案草案{plan_ref}已记录，尚未执行生成。"
                "请房主回复“确认生成”，确认后会通过 Runtime 生成队列执行。"
            )
            return bool(self._send_final_reply("gm-system", "GM", reply, trigger))
        reply = (
            "这是生成/场景写入类请求。当前已由 AgentRuntime 接管，"
            "旧 RoleAgent 直接执行链路已关闭；请通过确认方案、生成队列或完成态调整链路执行。"
        )
        return bool(self._send_final_reply("gm-system", "系统", reply, trigger))

    def _send_runtime_planning_action(
        self,
        trigger: dict[str, Any],
        action: str,
        payload: str | None,
        agent_name: str,
    ) -> bool:
        agent_id = str(trigger.get("agent_id") or trigger.get("target_agent_id") or agent_name)
        visible_name = str(agent_name or trigger.get("agent_name") or "璁捐鍔╂墜")
        if action == "reply":
            self._mirror_runtime_planning_reply_context(trigger, str(payload or ""), visible_name)
            return bool(self._send_final_reply(agent_id, visible_name, str(payload or ""), trigger))
        if action == "compose":
            if self._execute_runtime_planning_compose(trigger, str(payload or ""), visible_name):
                return True
            if not self._agent_runtime_flags.can_call_legacy_main_workflow():
                return bool(self._send_final_reply(
                    "gm-system",
                    "绯荤粺",
                    "AgentRuntime 暂不可用，旧生成链路已关闭，已阻止直接生成。",
                    trigger,
                ))
            return False
        return False

    def _execute_runtime_planning_compose(
        self,
        trigger: dict[str, Any],
        compose_text: str,
        agent_name: str,
    ) -> bool:
        text = str(compose_text or "").strip()
        if not text:
            return False
        room_id = str(trigger.get("room_id") or "default")
        host_id = str(trigger.get("sender_id") or trigger.get("from") or "host")
        self._remember_room_id(room_id)
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=host_id,
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or "host"),
                owner_agent=str(agent_name or trigger.get("agent_name") or ""),
                action="confirm_and_execute",
                external_plan_id=self._runtime_planning_external_id(trigger, agent_name),
                scene_name=self._runtime_scene_name_from_trigger(trigger),
            )
            reply = self._format_agent_runtime_execution_reply(result)
            self._logger.info(
                "[LANChatGenerationTrace] phase=runtime_planning_compose_executed room=%s external_plan=%s agent=%s text=%s",
                room_id,
                self._runtime_planning_external_id(trigger, agent_name),
                agent_name,
                _trace_preview(text),
            )
            return bool(self._send_final_reply("gm-system", "绯荤粺", reply, trigger))
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime planning compose failed, falling back to Coordinator: %s", type(exc).__name__)
            if not self._agent_runtime_flags.can_call_legacy_main_workflow():
                self._logger.warning(
                    "[LANChatGenerationTrace] phase=runtime_planning_compose_failed_legacy_blocked room=%s external_plan=%s",
                    room_id,
                    self._runtime_planning_external_id(trigger, agent_name),
                )
                return False
        try:
            coordinator = self._get_interaction_coordinator()
            room_id = str(trigger.get("room_id") or "default")
            host_id = str(trigger.get("sender_id") or trigger.get("from") or "host")
            self._remember_room_id(room_id)
            coordinator.create_or_update_seed_plan(ChatMessage(
                room_id=room_id,
                sender_id=host_id,
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or "鎴夸富"),
                text=text,
                is_host=True,
                agent_id=str(trigger.get("agent_id") or trigger.get("target_agent_id") or agent_name or ""),
                agent_name=str(agent_name or trigger.get("agent_name") or ""),
                metadata=self._coordinator_sync_metadata(trigger, source="lanchat_runtime_planning_gate"),
            ))
            reply = self._start_active_coordinator_generation(
                coordinator,
                room_id=room_id,
                host_id=host_id,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to execute runtime planning compose: %s", type(exc).__name__)
            return False
        if reply is None:
            return False
        return bool(self._send_final_reply("gm-system", "绯荤粺", reply, trigger))

    @staticmethod
    def _runtime_planning_external_id(trigger: dict[str, Any], agent_name: str) -> str:
        for value in (
            trigger.get("target_plan_id"),
            trigger.get("proposal_id"),
            trigger.get("correlation_id"),
            trigger.get("message_id"),
        ):
            text = str(value or "").strip()
            if text:
                return f"planning:{text}"
        room_id = str(trigger.get("room_id") or "default").strip() or "default"
        agent = str(agent_name or trigger.get("agent_name") or trigger.get("agent_id") or "agent").strip() or "agent"
        return f"planning:{room_id}:{agent}"

    def _active_runtime_external_plan_id(self, room_id: str) -> str:
        room = str(room_id or "default")
        try:
            result = self._agent_runtime.handle_message(
                room_id=room,
                text="",
                action="runtime_status",
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime active external plan lookup skipped: %s", type(exc).__name__)
            result = {}
        status = result.get("status", {}) if isinstance(result, dict) else {}
        if isinstance(status, dict):
            active_runtime_plan_id = str(status.get("active_plan_id") or status.get("plan_id") or "")
            if active_runtime_plan_id:
                return active_runtime_plan_id
        if not self._agent_runtime_flags.can_call_legacy_main_workflow():
            return ""
        try:
            coordinator = self._get_interaction_coordinator()
            active = coordinator.active_plan_for_room(room)
            return str(getattr(active, "plan_id", "") or "")
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _runtime_scene_name_from_trigger(trigger: dict[str, Any]) -> str:
        metadata = LANChatAgentWorker._metadata_from_trigger(trigger)
        for value in (
            metadata.get("scene_name"),
            metadata.get("scene_path"),
            trigger.get("scene_name"),
            trigger.get("scene_path"),
        ):
            text = str(value or "").strip()
            if text:
                return text
        return ""

    @staticmethod
    def _agent_runtime_graphs_from_result(result: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(result, dict):
            return []
        graphs = result.get("graphs")
        if isinstance(graphs, list):
            normalized = [dict(graph) for graph in graphs if isinstance(graph, dict)]
            if normalized:
                return normalized
        graph = result.get("graph")
        if isinstance(graph, dict) and graph:
            return [dict(graph)]
        queued = result.get("queued")
        if isinstance(queued, dict):
            queued_graphs = queued.get("graphs")
            if isinstance(queued_graphs, list):
                normalized = [dict(graph) for graph in queued_graphs if isinstance(graph, dict)]
                if normalized:
                    return normalized
            queued_graph = queued.get("graph")
            if isinstance(queued_graph, dict) and queued_graph:
                return [dict(queued_graph)]
        return []

    @staticmethod
    def _agent_runtime_batches_from_result(result: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(result, dict):
            return []
        batches = result.get("batches")
        if isinstance(batches, list):
            normalized = [dict(batch) for batch in batches if isinstance(batch, dict)]
            if normalized:
                return normalized
        batch = result.get("batch")
        if isinstance(batch, dict) and batch:
            return [dict(batch)]
        queued = result.get("queued")
        if isinstance(queued, dict):
            queued_batches = queued.get("batches")
            if isinstance(queued_batches, list):
                normalized = [dict(batch) for batch in queued_batches if isinstance(batch, dict)]
                if normalized:
                    return normalized
            queued_batch = queued.get("batch")
            if isinstance(queued_batch, dict) and queued_batch:
                return [dict(queued_batch)]
        return []

    @staticmethod
    def _format_agent_runtime_execution_reply(result: dict[str, Any]) -> str:
        if not isinstance(result, dict):
            return "【AgentRuntime 执行结果】Runtime 未返回执行结果。"
        runtime_plan = result.get("plan", {}) if isinstance(result, dict) else {}
        runtime_plan_id = str(runtime_plan.get("plan_id") or "")
        batches = LANChatAgentWorker._agent_runtime_batches_from_result(result)
        graphs = LANChatAgentWorker._agent_runtime_graphs_from_result(result)
        graph_statuses = [str(graph.get("status") or "") for graph in graphs if isinstance(graph, dict)]
        status_counts: dict[str, int] = {}
        for status in graph_statuses:
            key = status or "unknown"
            status_counts[key] = status_counts.get(key, 0) + 1
        graph_status_text = ", ".join(
            f"{key}:{value}"
            for key, value in sorted(status_counts.items())
        ) or "none"
        report = result.get("report") if isinstance(result.get("report"), dict) else {}
        health = report.get("report_health_summary") if isinstance(report.get("report_health_summary"), dict) else {}
        health_status = str(health.get("status") or "unknown").strip().replace("_", "-") if health else "unknown"
        attention = bool(health.get("attention_required")) if health else False
        health_text = f"{health_status}，需关注" if attention else health_status
        evidence = LANChatAgentWorker._agent_runtime_evidence_summary(result)
        registry_text = (
            f"实体注册：{int(evidence.get('entity_count') or 0)} 个"
            f"（actor {int(evidence.get('actor_count') or 0)}，"
            f"terrain {int(evidence.get('terrain_count') or 0)}，"
            f"skybox {int(evidence.get('skybox_count') or 0)}）"
        )
        classification_text = (
            f"Classification：model/substrate "
            f"{int(evidence.get('model_items') or 0)}/"
            f"{int(evidence.get('substrate_items') or 0)}"
        )
        flow_text = (
            f"Flow：{str(evidence.get('flow_status') or 'unknown')} "
            f"{str(evidence.get('flow_steps') or 'none')}"
        )
        tool_state_text = (
            f"Tool/State：tools ok/fail/block "
            f"{int(evidence.get('tool_execution_succeeded_count') or 0)}/"
            f"{int(evidence.get('tool_execution_failed_count') or 0)}/"
            f"{int(evidence.get('tool_execution_blocked_count') or 0)}，"
            f"patch applied/conflict/invalid "
            f"{int(evidence.get('state_patch_applied_count') or 0)}/"
            f"{int(evidence.get('state_patch_conflict_count') or 0)}/"
            f"{int(evidence.get('state_patch_invalid_count') or 0)}，"
            f"OperationLog {int(evidence.get('operation_total_count') or evidence.get('operation_count') or 0)}"
        )
        guard_text = (
            f"Guard：block/write/system "
            f"{int(evidence.get('runtime_guard_blocked_count') or 0)}/"
            f"{int(evidence.get('runtime_guard_requires_write_blocked_count') or 0)}/"
            f"{int(evidence.get('runtime_guard_system_actor_write_blocked_count') or 0)}，"
            f"confirm high/write "
            f"{int(evidence.get('runtime_guard_high_risk_confirmation_required_count') or 0)}/"
            f"{int(evidence.get('runtime_guard_write_confirmation_required_count') or 0)}"
        )
        queue_text = (
            f"Queue：total/queued/running/active/block "
            f"{int(evidence.get('tool_queue_count') or 0)}/"
            f"{int(evidence.get('tool_queue_queued_count') or 0)}/"
            f"{int(evidence.get('tool_queue_running_count') or 0)}/"
            f"{int(evidence.get('tool_queue_active_count') or 0)}/"
            f"{int(evidence.get('tool_queue_blocked_count') or 0)}，"
            f"pressure {int(float(evidence.get('tool_queue_pressure') or 0.0) * 100)}%"
        )
        batch_tooling_text = (
            f"BatchTooling：facts/created/prioritized/merged/absorbed "
            f"{int(evidence.get('batch_tooling_fact_count') or 0)}/"
            f"{int(evidence.get('batch_tooling_created_batch_count') or 0)}/"
            f"{int(evidence.get('batch_tooling_prioritized_item_count') or 0)}/"
            f"{int(evidence.get('batch_tooling_merged_intervention_item_count') or 0)}/"
            f"{int(evidence.get('batch_tooling_absorbed_intervention_count') or 0)}"
        )
        report_source_text = (
            f"ReportSource：state {str(evidence.get('runtime_state_source') or 'unknown')}，"
            f"operation {int(evidence.get('operation_count') or 0)}/"
            f"{int(evidence.get('operation_total_count') or 0)}"
        )
        bridge_calls = int(evidence.get("engine_write_bridge_call_count") or 0)
        bridge_success = int(evidence.get("engine_write_bridge_success_count") or 0)
        bridge_failed = int(evidence.get("engine_write_bridge_failed_count") or 0)
        status_counts = evidence.get("engine_write_status_counts")
        runtime_state_only = 0
        if isinstance(status_counts, dict):
            runtime_state_only = int(status_counts.get("runtime_state_only") or 0)
        if bridge_calls > 0:
            engine_text = (
                f"Engine写入：bridge {bridge_success}/{bridge_calls} 成功"
                + (f"，失败 {bridge_failed}" if bridge_failed else "")
            )
        elif runtime_state_only > 0:
            engine_text = (
                f"Engine写入：RuntimeState-only {runtime_state_only} 项，"
                "真实引擎写入待 F5/实机验证"
            )
        else:
            engine_text = "Engine写入：未发现 bridge 写入证据，待 F5/实机验证"
        if any(status == "failed" for status in graph_statuses):
            return (
                f"【AgentRuntime 执行结果】ScenePlan {runtime_plan_id} 执行未完成，"
                f"批次 {len(batches)} 个，执行图 {graph_status_text}，报告健康：{health_text}。"
                f"{registry_text}；{classification_text}；{flow_text}；{tool_state_text}；{guard_text}；{queue_text}；"
                f"{batch_tooling_text}；{report_source_text}；{engine_text}。"
            )
        return (
            f"【AgentRuntime 执行结果】ScenePlan {runtime_plan_id} 已执行 Runtime 批次 {len(batches)} 个，"
            f"执行图 {graph_status_text}，报告健康：{health_text}。"
            f"{registry_text}；{classification_text}；{flow_text}；{tool_state_text}；{guard_text}；{queue_text}；"
            f"{batch_tooling_text}；{report_source_text}；{engine_text}。"
        )

    @staticmethod
    def _agent_runtime_evidence_summary(result: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(result, dict):
            return {}
        report = result.get("report") if isinstance(result.get("report"), dict) else {}
        registry = report.get("scene_entity_registry") if isinstance(report.get("scene_entity_registry"), dict) else {}
        flow = report.get("runtime_scene_flow_summary") if isinstance(report.get("runtime_scene_flow_summary"), dict) else {}
        classification = report.get("classification_summary") if isinstance(report.get("classification_summary"), dict) else {}
        state_patch = report.get("state_patch_summary") if isinstance(report.get("state_patch_summary"), dict) else {}
        tool_execution = report.get("tool_execution_digest") if isinstance(report.get("tool_execution_digest"), dict) else {}
        import_summary = (
            report.get("import_summary")
            if isinstance(report.get("import_summary"), dict)
            else {}
        )
        report_health = (
            report.get("report_health_summary")
            if isinstance(report.get("report_health_summary"), dict)
            else {}
        )
        tool_queue_health = (
            report.get("tool_queue_health_summary")
            if isinstance(report.get("tool_queue_health_summary"), dict)
            else {}
        )
        batch_tooling = (
            report.get("batch_tooling_summary")
            if isinstance(report.get("batch_tooling_summary"), dict)
            else {}
        )
        fact_source = (
            report.get("fact_source_boundary_summary")
            if isinstance(report.get("fact_source_boundary_summary"), dict)
            else {}
        )
        engine_write_boundary = (
            report.get("engine_write_boundary_summary")
            if isinstance(report.get("engine_write_boundary_summary"), dict)
            else {}
        )
        replay = (
            report.get("operation_replay_summary")
            if isinstance(report.get("operation_replay_summary"), dict)
            else {}
        )
        guard_summary = (
            report.get("runtime_guard_replay_summary")
            if isinstance(report.get("runtime_guard_replay_summary"), dict)
            else replay.get("runtime_guard_replay_summary")
            if isinstance(replay.get("runtime_guard_replay_summary"), dict)
            else {}
        )
        resource_summary = dict(replay.get("resource_summary") or {})
        resource_by_phase = dict(resource_summary.get("by_phase") or {})
        image_resource = dict(resource_by_phase.get("image") or {})
        model_resource = dict(resource_by_phase.get("model") or {})
        geometry_summary = dict(replay.get("geometry_fact_replay_summary") or {})
        vlm_summary = dict(replay.get("vlm_checkpoint_summary") or {})
        sync_summary = dict(replay.get("sync_replay_summary") or {})
        asset_transfer_summary = dict(replay.get("asset_transfer_replay_summary") or {})
        batch_execution_summary = dict(replay.get("batch_execution_summary") or {})
        graphs = LANChatAgentWorker._agent_runtime_graphs_from_result(result)
        graph_statuses = [str(graph.get("status") or "") for graph in graphs if isinstance(graph, dict)]
        entity_type_counts = dict(registry.get("entity_type_counts") or {})
        steps = []
        for step in flow.get("steps") or []:
            if isinstance(step, dict):
                text = str(step.get("step") or "").strip()
                if text:
                    steps.append(text)
            elif str(step or "").strip():
                steps.append(str(step).strip())
        return {
            "batch_count": len(LANChatAgentWorker._agent_runtime_batches_from_result(result)),
            "graph_count": len(graphs),
            "graph_statuses": ",".join(graph_statuses),
            "flow_steps": ">".join(steps),
            "flow_status": str(flow.get("status") or ""),
            "entity_count": int(registry.get("entity_count") or 0),
            "actor_count": int(registry.get("actor_count") or entity_type_counts.get("actor") or 0),
            "terrain_count": int(registry.get("terrain_count") or entity_type_counts.get("terrain") or 0),
            "skybox_count": int(registry.get("skybox_count") or entity_type_counts.get("skybox") or 0),
            "model_items": len(classification.get("model_items") or []),
            "substrate_items": len(classification.get("substrate_items") or []),
            "operation_count": int(report.get("operation_count") or 0),
            "operation_total_count": int(report.get("operation_total_count") or 0),
            "state_patch_applied_count": int(state_patch.get("applied") or 0),
            "state_patch_conflict_count": int(state_patch.get("conflict") or 0),
            "state_patch_invalid_count": int(state_patch.get("invalid") or 0),
            "tool_execution_succeeded_count": int(tool_execution.get("succeeded_count") or 0),
            "tool_execution_failed_count": int(tool_execution.get("failed_count") or 0),
            "tool_execution_blocked_count": int(tool_execution.get("blocked_count") or 0),
            "runtime_guard_blocked_count": int(guard_summary.get("blocked_count") or 0),
            "runtime_guard_high_risk_confirmation_required_count": int(
                guard_summary.get("high_risk_confirmation_required_count") or 0
            ),
            "runtime_guard_write_confirmation_required_count": int(
                guard_summary.get("write_confirmation_required_count") or 0
            ),
            "runtime_guard_system_actor_write_blocked_count": int(
                guard_summary.get("system_actor_write_blocked_count") or 0
            ),
            "runtime_guard_requires_write_blocked_count": int(
                guard_summary.get("requires_write_blocked_count") or 0
            ),
            "runtime_guard_confirmed_blocked_count": int(guard_summary.get("confirmed_blocked_count") or 0),
            "runtime_guard_unconfirmed_blocked_count": int(guard_summary.get("unconfirmed_blocked_count") or 0),
            "tool_queue_count": int(tool_queue_health.get("queue_count") or 0),
            "tool_queue_queued_count": int(tool_queue_health.get("queued_count") or 0),
            "tool_queue_running_count": int(tool_queue_health.get("running_count") or 0),
            "tool_queue_blocked_count": int(tool_queue_health.get("blocked_count") or 0),
            "tool_queue_terminal_count": int(tool_queue_health.get("terminal_count") or 0),
            "tool_queue_active_count": int(tool_queue_health.get("active_count") or 0),
            "tool_queue_pressure": float(tool_queue_health.get("queue_pressure") or 0.0),
            "batch_tooling_fact_count": int(batch_tooling.get("fact_count") or 0),
            "batch_tooling_created_batch_fact_count": int(batch_tooling.get("created_batch_fact_count") or 0),
            "batch_tooling_created_batch_count": int(batch_tooling.get("created_batch_count") or 0),
            "batch_tooling_prioritized_item_count": int(batch_tooling.get("prioritized_item_count") or 0),
            "batch_tooling_merged_intervention_fact_count": int(batch_tooling.get("merged_intervention_fact_count") or 0),
            "batch_tooling_merged_intervention_item_count": int(batch_tooling.get("merged_intervention_item_count") or 0),
            "batch_tooling_absorbed_intervention_count": int(batch_tooling.get("absorbed_intervention_count") or 0),
            "runtime_state_source": str(fact_source.get("runtime_state_source") or ""),
            "engine_write_boundary_count": int(engine_write_boundary.get("boundary_fact_count") or 0),
            "engine_write_import_boundary_count": int(engine_write_boundary.get("import_boundary_count") or 0),
            "engine_write_bridge_call_count": int(engine_write_boundary.get("bridge_call_count") or 0),
            "engine_write_bridge_success_count": int(engine_write_boundary.get("bridge_success_count") or 0),
            "engine_write_bridge_failed_count": int(engine_write_boundary.get("bridge_failed_count") or 0),
            "engine_write_bridge_error_code_counts": dict(engine_write_boundary.get("bridge_error_code_counts") or {}),
            "engine_write_status_counts": dict(engine_write_boundary.get("status_counts") or {}),
            "engine_write_source_counts": dict(engine_write_boundary.get("write_source_counts") or {}),
            "import_failure_code_counts": dict(
                import_summary.get("import_failure_code_counts")
                or report_health.get("import_failure_code_counts")
                or {}
            ),
            "environment_import_failure_code_counts": dict(
                import_summary.get("environment_import_failure_code_counts")
                or report_health.get("environment_import_failure_code_counts")
                or {}
            ),
            "resource_image_requested_count": int(image_resource.get("requested_count") or 0),
            "resource_image_failed_count": int(image_resource.get("failed_count") or 0),
            "resource_model_requested_count": int(model_resource.get("requested_count") or 0),
            "resource_model_failed_count": int(model_resource.get("failed_count") or 0),
            "geometry_fact_count": int(geometry_summary.get("fact_count") or 0),
            "geometry_aabb_actor_count": int(geometry_summary.get("aabb_actor_count") or 0),
            "geometry_overlap_issue_count": int(geometry_summary.get("overlap_issue_count") or 0),
            "vlm_checkpoint_count": int(vlm_summary.get("checkpoint_count") or 0),
            "vlm_advisory_count": int(vlm_summary.get("advisory_count") or 0),
            "sync_recorded_count": int(sync_summary.get("recorded_count") or 0),
            "sync_failed_count": int(sync_summary.get("failed_count") or 0),
            "asset_transfer_progress_count": int(asset_transfer_summary.get("asset_transfer_progress_count") or 0),
            "asset_transfer_failed_count": int(asset_transfer_summary.get("asset_transfer_failed_count") or 0),
            "batch_execution_completed_count": int(batch_execution_summary.get("completed_count") or 0),
        }

    def _log_agent_runtime_evidence(
        self,
        *,
        phase: str,
        room_id: str,
        runtime_plan_id: str,
        result: dict[str, Any],
    ) -> None:
        summary = self._agent_runtime_evidence_summary(result)
        if not summary:
            return
        self._logger.info(
            "[LANChatRuntimeEvidence] phase=%s room=%s runtime_plan=%s batches=%s graphs=%s graph_statuses=%s "
            "flow=%s flow_status=%s entities=%s actors=%s terrain=%s skybox=%s model_items=%s substrate_items=%s "
            "operations=%s operation_total=%s state_source=%s engine_boundary=%s engine_imports=%s "
            "guard=block:%s,write:%s,system:%s,confirm_high:%s,confirm_write:%s "
            "queue=total:%s,queued:%s,running:%s,active:%s,block:%s,pressure:%s "
            "batch_tooling=facts:%s,created:%s,prioritized:%s,merged:%s,absorbed:%s "
            "engine_bridge=%s/%s/%s engine_statuses=%s engine_sources=%s "
            "import_failures=%s env_import_failures=%s bridge_errors=%s "
            "resources=image:%s/%s,model:%s/%s geometry=facts:%s,aabb:%s,overlap:%s "
            "vlm=checkpoints:%s,advisories:%s sync=recorded:%s,failed:%s "
            "asset_transfer=progress:%s,failed:%s batch_completed=%s",
            phase,
            room_id or "default",
            runtime_plan_id or "",
            summary.get("batch_count", 0),
            summary.get("graph_count", 0),
            summary.get("graph_statuses", ""),
            summary.get("flow_steps", ""),
            summary.get("flow_status", ""),
            summary.get("entity_count", 0),
            summary.get("actor_count", 0),
            summary.get("terrain_count", 0),
            summary.get("skybox_count", 0),
            summary.get("model_items", 0),
            summary.get("substrate_items", 0),
            summary.get("operation_count", 0),
            summary.get("operation_total_count", 0),
            summary.get("runtime_state_source", ""),
            summary.get("engine_write_boundary_count", 0),
            summary.get("engine_write_import_boundary_count", 0),
            summary.get("runtime_guard_blocked_count", 0),
            summary.get("runtime_guard_requires_write_blocked_count", 0),
            summary.get("runtime_guard_system_actor_write_blocked_count", 0),
            summary.get("runtime_guard_high_risk_confirmation_required_count", 0),
            summary.get("runtime_guard_write_confirmation_required_count", 0),
            summary.get("tool_queue_count", 0),
            summary.get("tool_queue_queued_count", 0),
            summary.get("tool_queue_running_count", 0),
            summary.get("tool_queue_active_count", 0),
            summary.get("tool_queue_blocked_count", 0),
            summary.get("tool_queue_pressure", 0.0),
            summary.get("batch_tooling_fact_count", 0),
            summary.get("batch_tooling_created_batch_count", 0),
            summary.get("batch_tooling_prioritized_item_count", 0),
            summary.get("batch_tooling_merged_intervention_item_count", 0),
            summary.get("batch_tooling_absorbed_intervention_count", 0),
            summary.get("engine_write_bridge_call_count", 0),
            summary.get("engine_write_bridge_success_count", 0),
            summary.get("engine_write_bridge_failed_count", 0),
            summary.get("engine_write_status_counts", {}),
            summary.get("engine_write_source_counts", {}),
            summary.get("import_failure_code_counts", {}),
            summary.get("environment_import_failure_code_counts", {}),
            summary.get("engine_write_bridge_error_code_counts", {}),
            summary.get("resource_image_requested_count", 0),
            summary.get("resource_image_failed_count", 0),
            summary.get("resource_model_requested_count", 0),
            summary.get("resource_model_failed_count", 0),
            summary.get("geometry_fact_count", 0),
            summary.get("geometry_aabb_actor_count", 0),
            summary.get("geometry_overlap_issue_count", 0),
            summary.get("vlm_checkpoint_count", 0),
            summary.get("vlm_advisory_count", 0),
            summary.get("sync_recorded_count", 0),
            summary.get("sync_failed_count", 0),
            summary.get("asset_transfer_progress_count", 0),
            summary.get("asset_transfer_failed_count", 0),
            summary.get("batch_execution_completed_count", 0),
        )

    @staticmethod
    def _format_agent_runtime_intervention_reply(result: dict[str, Any]) -> str:
        if not isinstance(result, dict):
            return "【AgentRuntime 介入结果】Runtime 未返回介入结果。"
        plan = result.get("plan") if isinstance(result.get("plan"), dict) else {}
        patch = result.get("patch") if isinstance(result.get("patch"), dict) else {}
        runtime_plan_id = str(plan.get("plan_id") or patch.get("plan_id") or "")
        if not patch:
            message = str(result.get("message") or "AgentRuntime 未记录介入。")
            return f"【AgentRuntime 介入结果】{message}"
        patch_type = str(patch.get("patch_type") or result.get("action") or "intervention").strip().replace("_", "-")
        status = str(
            patch.get("status")
            or ("recorded" if result.get("recorded") else "not-recorded")
        ).strip().replace("_", "-")
        raw_items = patch.get("items") if isinstance(patch.get("items"), list) else []
        item_count = len([item for item in raw_items if str(item or "").strip()])
        return (
            f"【AgentRuntime 介入结果】ScenePlan {runtime_plan_id} 已记录 {patch_type}，"
            f"状态 {status}，对象 {item_count} 个。"
        )

    @staticmethod
    def _format_agent_runtime_layout_confirmation_reply(result: dict[str, Any]) -> str:
        if not isinstance(result, dict):
            return "【AgentRuntime 布局结果】Runtime 未返回布局确认结果。"
        graph = result.get("graph") if isinstance(result.get("graph"), dict) else {}
        proposal = result.get("proposal") if isinstance(result.get("proposal"), dict) else {}
        if not proposal:
            reason = str(result.get("reason") or "未找到布局调整建议").strip()
            return f"【AgentRuntime 布局结果】{reason}。"
        plan_id = str(proposal.get("plan_id") or graph.get("plan_id") or "").strip()
        proposal_id = str(proposal.get("proposal_id") or proposal.get("id") or "").strip()
        graph_status = str(graph.get("status") or "unknown").strip().replace("_", "-")
        applied = proposal.get("applied_deltas") if isinstance(proposal.get("applied_deltas"), list) else []
        skipped = proposal.get("skipped_deltas") if isinstance(proposal.get("skipped_deltas"), list) else []
        transform_results = (
            proposal.get("engine_transform_results")
            if isinstance(proposal.get("engine_transform_results"), list)
            else []
        )
        transform_success = 0
        transform_failed = 0
        ground_snapped = 0
        overlap_resolved = 0
        for item in transform_results:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "").strip().lower()
            if status in {"success", "succeeded", "applied", "ok"}:
                transform_success += 1
            elif status in {"failed", "failure", "error", "rejected"}:
                transform_failed += 1
            if bool(item.get("ground_snapped")):
                ground_snapped += 1
            if bool(item.get("overlap_resolved")):
                overlap_resolved += 1
        prefix = f"ScenePlan {plan_id} " if plan_id else ""
        proposal_part = f"建议 {proposal_id} " if proposal_id else ""
        return (
            f"【AgentRuntime 布局结果】{prefix}{proposal_part}已通过 ToolCallGraph 确认，"
            f"graph {graph_status}，应用 {len(applied)} 项，跳过 {len(skipped)} 项，"
            f"引擎写入成功 {transform_success} 项、失败 {transform_failed} 项，"
            f"贴地 {ground_snapped} 项，重叠修正 {overlap_resolved} 项。"
        )

    def _log_scene_route(
        self,
        *,
        room_id: str,
        sender: str,
        target_agent: str,
        room_state: str,
        intent: str,
        action: str,
        reason: str,
    ) -> None:
        self._logger.info(
            "[LANChatIntentRoute] room=%s sender=%s target=%s state=%s intent=%s action=%s reason=%s",
            room_id or "default",
            sender or "",
            target_agent or "",
            room_state or "",
            intent or "",
            action or "",
            reason or "",
        )

    def _should_sync_chat_to_coordinator(
        self,
        coordinator: InteractionCoordinator,
        room_id: str,
        text: str,
        *,
        source: str,
    ) -> bool:
        active = coordinator.active_plan_for_room(room_id)
        if active is not None and active.status in {
            SeedPlanStatus.CONFIRMED,
            SeedPlanStatus.EXECUTING,
            SeedPlanStatus.PAUSED,
        }:
            return True
        if active is not None and coordinator._is_status_query(text):
            return True
        if active is not None and active.status == SeedPlanStatus.COMPLETED:
            return (
                coordinator._intent_type(text) == "add"
                or coordinator._is_post_generation_adjustment(text)
            )
        try:
            from plugins.AITool.cai_extensions.agent.agent_adapter import classify_intent
        except Exception:  # noqa: BLE001
            try:
                from cai_extensions.agent.agent_adapter import classify_intent  # type: ignore
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Failed to import scene intent classifier for %s: %s", source, type(exc).__name__)
                return False
        try:
            intent = classify_intent(text)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to classify LANChat chat message for Coordinator sync: %s", type(exc).__name__)
            return False
        return intent in {"compose", "edit"}

    @staticmethod
    def _message_sender_is_host(message: dict[str, Any], *, sender_type: str = "") -> bool:
        if bool((message or {}).get("is_host")):
            return True
        normalized_sender_type = str(sender_type or (message or {}).get("sender_type") or "").strip().lower()
        if normalized_sender_type == "host":
            return True
        room_id = str((message or {}).get("room_id") or "").strip()
        sender_id = str((message or {}).get("sender_id") or (message or {}).get("from") or "").strip()
        sender_name = str((message or {}).get("sender_name") or "").strip()
        # The single-player LANChat bridge may emit sender_type=user with no is_host flag.
        # Treat the local single-player owner as host without relaxing multiplayer rooms.
        if room_id in {"single-default", "single", "default"} and (
            sender_id == "local-single-player" or sender_name == "房主"
        ):
            return True
        return False

    def process_once(self) -> bool:
        if not self._has_engine_api():
            return False

        processed_room_event = self._process_room_events(
            max_events=MAX_ROOM_EVENTS_PER_TICK,
        )
        processed_coordinator_sync = self._process_coordinator_sync_messages(
            max_messages=MAX_COORDINATOR_SYNC_MESSAGES_PER_TICK,
        )
        processed_runtime_drain = self._drain_agent_runtime_queue_once(
            max_rooms=MAX_AGENT_RUNTIME_DRAIN_ROOMS_PER_TICK,
            max_graphs_per_room=MAX_AGENT_RUNTIME_GRAPHS_PER_TICK,
        )

        try:
            trigger = self._corona_engine.network_pop_lanchat_agent_trigger()
        except Exception as exc:
            self._logger.debug("Failed to poll LANChat agent trigger: %s", type(exc).__name__)
            return processed_room_event or processed_coordinator_sync or processed_runtime_drain

        if not trigger:
            return processed_room_event or processed_coordinator_sync or processed_runtime_drain

        self._logger.info(
            "[LANChatAgentTrace] phase=trigger_pop message_id=%s correlation=%s room=%s sender=%s/%s target=%s/%s kind=%s text=%s",
            trigger.get("message_id") or "",
            trigger.get("correlation_id") or "",
            trigger.get("room_id") or "",
            trigger.get("sender_type") or "",
            trigger.get("sender_id") or trigger.get("from") or "",
            trigger.get("target_agent_id") or trigger.get("agent_id") or "",
            trigger.get("target_agent_name") or trigger.get("agent_name") or "",
            trigger.get("message_kind") or "",
            _trace_preview(trigger.get("text")),
        )
        self._sync_trigger_history_to_coordinator(trigger)

        if self._async_agent_execution:
            threading.Thread(
                target=self._process_trigger,
                args=(trigger,),
                name="LANChatAgentTask",
                daemon=True,
            ).start()
            return True

        return self._process_trigger(trigger)

    def _drain_agent_runtime_queue_once(
        self,
        *,
        max_rooms: int = MAX_AGENT_RUNTIME_DRAIN_ROOMS_PER_TICK,
        max_graphs_per_room: int = MAX_AGENT_RUNTIME_GRAPHS_PER_TICK,
    ) -> bool:
        if not self._agent_runtime_flags.agent_runtime_enabled:
            return False
        room_snapshot = list(self._active_room_order)
        if not room_snapshot:
            return False
        room_limit = max(1, int(max_rooms or 1))
        graph_limit = max(1, int(max_graphs_per_room or 1))
        for room_id in room_snapshot[:room_limit]:
            before_timestamp = self._latest_agent_runtime_event_timestamp(str(room_id))
            try:
                runtime_result = self._agent_runtime.handle_message(
                    room_id=str(room_id),
                    text="runtime worker drain",
                    action="worker_drain",
                    max_graphs=graph_limit,
                )
                result = dict(runtime_result.get("drain") or {})
            except Exception as exc:  # noqa: BLE001
                self._logger.warning(
                    "AgentRuntime queue drain failed for room %s: error_type=%s",
                    room_id,
                    type(exc).__name__,
                )
                self._record_runtime_audit_event(
                    event="runtime_worker_drain_exception",
                    room_id=str(room_id),
                    message="AgentRuntime worker drain raised an exception.",
                    payload={
                        "error_type": type(exc).__name__,
                        "phase": "agent_runtime_worker_drain",
                    },
                )
                continue
            drained_count = int(result.get("drained_count") or 0)
            if drained_count <= 0:
                if str(result.get("status") or "").strip().lower() == "failed":
                    reason = str(result.get("reason") or "").strip()
                    self._logger.warning(
                        "[LANChatRuntimeDrain] room=%s failed reason=%s",
                        room_id,
                        _trace_preview(reason, limit=120),
                    )
                    self._record_runtime_audit_event(
                        event="runtime_worker_drain_failed",
                        room_id=str(room_id),
                        message="AgentRuntime worker drain returned failed status.",
                        payload={
                            "reason": reason[:240],
                            "status": str(result.get("status") or ""),
                            "phase": "agent_runtime_worker_drain",
                            "drained_count": drained_count,
                        },
                    )
                continue
            self._remember_room_id(str(room_id))
            self._logger.info(
                "[LANChatRuntimeDrain] room=%s drained=%s graphs=%s",
                room_id,
                drained_count,
                _trace_preview(result.get("graphs"), limit=160),
            )
            self._emit_agent_runtime_events_since(
                str(room_id),
                after_timestamp=before_timestamp,
            )
            return True
        return False

    def _latest_agent_runtime_event_timestamp(self, room_id: str) -> float:
        try:
            result = self._agent_runtime.handle_message(
                room_id=str(room_id),
                text="",
                action="runtime_events",
                sync_event={"limit": 1},
            )
            events = result.get("runtime_events", []) if isinstance(result, dict) else []
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime latest event lookup skipped for room %s: %s", room_id, type(exc).__name__)
            return 0.0
        if not events:
            return 0.0
        try:
            return float(events[-1].get("timestamp") or 0)
        except (TypeError, ValueError):
            return 0.0

    def _emit_agent_runtime_events_since(self, room_id: str, *, after_timestamp: float) -> int:
        try:
            result = self._agent_runtime.handle_message(
                room_id=str(room_id),
                text="",
                action="runtime_events",
                sync_event={
                    "limit": MAX_AGENT_RUNTIME_DISCLOSURE_EVENT_LOOKBACK,
                    "after_timestamp": float(after_timestamp or 0),
                },
            )
            events = result.get("runtime_events", []) if isinstance(result, dict) else []
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime event disclosure skipped for room %s: %s", room_id, type(exc).__name__)
            return 0
        fresh_events: list[dict[str, Any]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            try:
                event_timestamp = float(event.get("timestamp") or 0)
            except (TypeError, ValueError):
                event_timestamp = 0.0
            if event_timestamp > float(after_timestamp or 0):
                fresh_events.append(event)
        disclose_events: list[dict[str, Any]] = []
        for event in fresh_events:
            if self._should_auto_disclose_agent_runtime_event(event):
                disclose_events.append(event)
            else:
                self._record_skipped_agent_runtime_event_disclosure(room_id, event)
        rows = self._format_agent_runtime_event_rows(disclose_events)
        sent = 0
        for line, event in rows:
            if self._send_agent_runtime_system_event(room_id, line, runtime_event=event):
                sent += 1
        return sent

    @staticmethod
    def _should_auto_disclose_agent_runtime_event(event: dict[str, Any]) -> bool:
        audience = str((event or {}).get("audience") or "host").strip()
        return audience in {"host", "participants", "all"}

    def _record_skipped_agent_runtime_event_disclosure(self, room_id: str, event: dict[str, Any]) -> None:
        runtime_event_metadata = self._safe_runtime_event_metadata(event)
        runtime_event_metadata["reason"] = "audience_not_user_visible"
        self._record_runtime_audit_event(
            event="runtime_system_event_disclosure_skipped",
            room_id=str(room_id or ""),
            message=str(event.get("event_type") or "runtime_event"),
            payload=runtime_event_metadata,
            runtime_plan_id=str(event.get("plan_id") or runtime_event_metadata.get("runtime_plan_id") or ""),
            batch_id=str(event.get("batch_id") or ""),
        )

    def _safe_runtime_event_metadata(self, runtime_event: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(runtime_event, dict):
            return {}
        metadata: dict[str, Any] = {}
        for source_key, target_key, limit in (
            ("event_id", "runtime_event_id", 80),
            ("event_type", "runtime_event_type", 64),
            ("plan_id", "runtime_plan_id", 80),
            ("batch_id", "runtime_batch_id", 80),
        ):
            raw = str(runtime_event.get(source_key) or "").strip()
            if raw:
                metadata[target_key] = self._safe_control_text(raw)[:limit]
        stage = str(runtime_event.get("stage") or runtime_event.get("phase") or "").strip()
        if stage:
            metadata["runtime_stage"] = self._safe_control_text(stage)[:48]
        audience = str(runtime_event.get("audience") or "").strip()
        if audience in {"host", "participants", "all", "agent", "system"}:
            metadata["runtime_audience"] = audience
        level = str(runtime_event.get("level") or "").strip()
        if level in {"info", "success", "warning", "error"}:
            metadata["runtime_level"] = level
        progress = runtime_event.get("progress")
        if isinstance(progress, (int, float)):
            metadata["runtime_progress"] = max(0, min(100, int(progress)))
        return metadata

    def _send_agent_runtime_system_event(
        self,
        room_id: str,
        text: str,
        runtime_event: dict[str, Any] | None = None,
    ) -> bool:
        safe_text = self._safe_control_text(text)
        room = str(room_id or "")
        metadata = {
            "phase": "agent_runtime",
            "room_id": room,
        }
        runtime_event_metadata = self._safe_runtime_event_metadata(runtime_event)
        metadata.update(runtime_event_metadata)
        self._record_runtime_system_event_send_in_agent_runtime(
            phase="runtime_system_event_send_requested",
            room_id=room,
            message=safe_text,
            message_kind="runtime_status",
            runtime_event_metadata=runtime_event_metadata,
        )
        if self._corona_engine is None:
            self._record_runtime_system_event_send_in_agent_runtime(
                phase="runtime_system_event_send_failed",
                room_id=room,
                message=safe_text,
                message_kind="runtime_status",
                sent=False,
                runtime_event_metadata=runtime_event_metadata,
            )
            return False
        try:
            if hasattr(self._corona_engine, "network_send_system_message_ex"):
                sent = bool(self._corona_engine.network_send_system_message_ex(
                    "system",
                    "绯荤粺",
                    safe_text,
                    "runtime_status",
                    "",
                    json.dumps(metadata, ensure_ascii=False),
                ))
                self._record_runtime_system_event_send_in_agent_runtime(
                    phase="runtime_system_event_send_succeeded" if sent else "runtime_system_event_send_failed",
                    room_id=room,
                    message=safe_text,
                    message_kind="runtime_status",
                    sent=sent,
                    runtime_event_metadata=runtime_event_metadata,
                )
                return sent
            if hasattr(self._corona_engine, "network_send_system_message"):
                sent = bool(self._corona_engine.network_send_system_message("system", "绯荤粺", safe_text))
                self._record_runtime_system_event_send_in_agent_runtime(
                    phase="runtime_system_event_send_succeeded" if sent else "runtime_system_event_send_failed",
                    room_id=room,
                    message=safe_text,
                    message_kind="runtime_status",
                    sent=sent,
                    runtime_event_metadata=runtime_event_metadata,
                )
                return sent
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to send AgentRuntime system event: %s", type(exc).__name__)
            self._record_runtime_system_event_send_in_agent_runtime(
                phase="runtime_system_event_send_failed",
                room_id=room,
                message=safe_text,
                message_kind="runtime_status",
                sent=False,
                runtime_event_metadata=runtime_event_metadata,
            )
            return False
        self._record_runtime_system_event_send_in_agent_runtime(
            phase="runtime_system_event_send_failed",
            room_id=room,
            message=safe_text,
            message_kind="runtime_status",
            sent=False,
            runtime_event_metadata=runtime_event_metadata,
        )
        return False

    def _record_runtime_system_event_send_in_agent_runtime(
        self,
        *,
        phase: str,
        room_id: str,
        message: str,
        message_kind: str,
        sent: bool | None = None,
        runtime_event_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "message_kind": str(message_kind or "runtime_status"),
            "phase": "agent_runtime",
        }
        payload.update(dict(runtime_event_metadata or {}))
        if sent is not None:
            payload["sent"] = bool(sent)
        room = str(room_id or "")
        external_plan_id = self._active_runtime_external_plan_id(room)
        return self._record_runtime_audit_event(
            event=phase,
            room_id=room,
            message=str(message or ""),
            payload=payload,
            external_plan_id=external_plan_id,
        )

    def _process_room_events(self, *, max_events: int) -> bool:
        if not hasattr(self._corona_engine, "network_pop_lanchat_room_event"):
            return False
        processed = False
        limit = max(1, int(max_events or 1))
        for _ in range(limit):
            try:
                event = self._corona_engine.network_pop_lanchat_room_event()
            except Exception as exc:
                self._logger.debug("Failed to poll LANChat room event: %s", type(exc).__name__)
                break
            if not event:
                break
            processed = True
            try:
                self.handle_lanchat_room_event(dict(event))
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Failed to handle LANChat room event: %s", type(exc).__name__)
        return processed

    def _process_coordinator_sync_messages(self, *, max_messages: int) -> bool:
        if not hasattr(self._corona_engine, "network_pop_lanchat_coordinator_sync_message"):
            return False
        processed = False
        limit = max(1, int(max_messages or 1))
        for _ in range(limit):
            try:
                message = self._corona_engine.network_pop_lanchat_coordinator_sync_message()
            except Exception as exc:
                self._logger.debug("Failed to poll LANChat Coordinator sync message: %s", type(exc).__name__)
                break
            if not message:
                break
            processed = True
            self._logger.info(
                "[LANChatSyncTrace] phase=native_queue_pop message_id=%s correlation=%s room=%s sender=%s/%s target=%s/%s text=%s",
                message.get("message_id") or "",
                message.get("correlation_id") or "",
                message.get("room_id") or "",
                message.get("sender_type") or "",
                message.get("sender_id") or message.get("from") or "",
                message.get("target_agent_id") or message.get("agent_id") or "",
                message.get("target_agent_name") or message.get("agent_name") or "",
                _trace_preview(message.get("text")),
            )
            self.sync_chat_message_to_coordinator(
                dict(message),
                source="lanchat_native_queue",
                emit_disclosure=True,
            )
        return processed

    def _process_trigger(self, trigger: dict[str, Any]) -> bool:
        self._apply_generation_options_from_message(trigger)
        agent_id = str(trigger.get("agent_id") or "agent")
        agent_name = str(trigger.get("agent_name") or "Agent")
        action_payload = None
        if not self._can_execute_agent_locally():
            self._logger.info(
                "[LANChatAgentTrace] phase=blocked_non_host_agent route=process_trigger role=%s message_id=%s correlation=%s room=%s agent=%s/%s sender=%s/%s kind=%s text=%s",
                self._network_session_role_name(),
                trigger.get("message_id") or "",
                self._correlation_id(trigger),
                trigger.get("room_id") or "",
                agent_id,
                agent_name,
                trigger.get("sender_type") or "",
                trigger.get("sender_id") or trigger.get("from") or "",
                trigger.get("message_kind") or "",
                _trace_preview(trigger.get("text")),
            )
            return False
        self._logger.info(
            "[LANChatAgentTrace] phase=process_start message_id=%s correlation=%s room=%s agent=%s/%s sender=%s/%s kind=%s text=%s",
            trigger.get("message_id") or "",
            self._correlation_id(trigger),
            trigger.get("room_id") or "",
            agent_id,
            agent_name,
            trigger.get("sender_type") or "",
            trigger.get("sender_id") or trigger.get("from") or "",
            trigger.get("message_kind") or "",
            _trace_preview(trigger.get("text")),
        )

        def _send_progress(message: str) -> None:
            text = str(message or "").strip()
            if not text:
                return
            try:
                if hasattr(self._corona_engine, "network_send_agent_reply_ex"):
                    self._corona_engine.network_send_agent_reply_ex(
                        agent_id,
                        agent_name,
                        text,
                        "progress",
                        agent_id,
                        self._correlation_id(trigger),
                        json.dumps({"phase": "progress"}, ensure_ascii=False),
                    )
                else:
                    self._corona_engine.network_send_agent_reply(
                        agent_id,
                        agent_name,
                        text,
                    )
            except Exception as exc:
                self._logger.debug("Failed to send LANChat progress reply: %s", type(exc).__name__)

        control_reply = self._handle_coordinator_gm_control(trigger)
        if control_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", control_reply, trigger))
        clarification_reply = self._handle_coordinator_gm_clarification(trigger)
        if clarification_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", clarification_reply, trigger))
        runtime_command_reply = self._handle_agent_runtime_command(trigger)
        if runtime_command_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_command_reply, trigger))
        runtime_worker_drain_reply = self._handle_agent_runtime_worker_drain_query(trigger)
        if runtime_worker_drain_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_worker_drain_reply, trigger))
        runtime_provider_reply = self._handle_agent_runtime_provider_status_query(trigger)
        if runtime_provider_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_provider_reply, trigger))
        runtime_engine_write_reply = self._handle_agent_runtime_engine_write_status_query(trigger)
        if runtime_engine_write_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_engine_write_reply, trigger))
        runtime_snapshot_reply = self._handle_agent_runtime_scene_snapshot_query(trigger)
        if runtime_snapshot_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_snapshot_reply, trigger))
        runtime_tools_reply = self._handle_agent_runtime_tool_manifest_query(trigger)
        if runtime_tools_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_tools_reply, trigger))
        runtime_replay_reply = self._handle_agent_runtime_operation_replay_query(trigger)
        if runtime_replay_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_replay_reply, trigger))
        runtime_report_reply = self._handle_agent_runtime_report_query(trigger)
        if runtime_report_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_report_reply, trigger))
        runtime_sync_reply = self._handle_agent_runtime_sync_status_query(trigger)
        if runtime_sync_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_sync_reply, trigger))
        runtime_gm_summary_reply = self._handle_agent_runtime_gm_summary_query(trigger)
        if runtime_gm_summary_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_gm_summary_reply, trigger))
        status_reply = self._handle_coordinator_status_query(trigger)
        if status_reply is not None:
            return bool(self._send_final_reply(agent_id, agent_name, status_reply, trigger))
        runtime_enqueue_reply = self._handle_agent_runtime_enqueue_generation_query(trigger)
        if runtime_enqueue_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", runtime_enqueue_reply, trigger))
        generation_start_reply = self._handle_coordinator_generation_start(trigger)
        if generation_start_reply is not None:
            return bool(self._send_final_reply("gm-system", "GM", generation_start_reply, trigger))
        completed_intervention_reply = self._handle_coordinator_completed_intervention(trigger)
        if completed_intervention_reply is not None:
            return bool(self._send_final_reply(agent_id, agent_name, completed_intervention_reply, trigger))
        executing_intervention_reply = self._handle_coordinator_executing_intervention(trigger)
        if executing_intervention_reply is not None:
            return bool(self._send_final_reply(agent_id, agent_name, executing_intervention_reply, trigger))
        planning_seed = self._seed_agent_trigger_planning_context_in_runtime(trigger)
        if self._handle_agent_trigger_planning_gate(trigger):
            return True
        if self._handle_agent_trigger_runtime_write_gate(trigger, planning_seed=planning_seed):
            return True

        try:
            from .agent_progress_context import agent_progress_sink
            from .lanchat_scene_runtime import get_lanchat_scene_runtime

            is_gm_target = (
                str(trigger.get("agent_id") or trigger.get("target_agent_id") or "").strip().lower() == "gm"
                or str(trigger.get("agent_name") or "").strip().lower() in {"gm", "主持人", "裁判", "game master"}
            )
            if (
                self._agent_runtime_flags.can_call_legacy_main_workflow()
                and not is_gm_target
                and str(trigger.get("message_kind") or "chat").strip().lower() in {"", "chat"}
            ):
                scene_runtime = get_lanchat_scene_runtime()
                note_text = str(trigger.get("text") or "")
                note_kind = ""
                try:
                    if scene_runtime.active_snapshot().get("active"):
                        note_kind = scene_runtime.classify_scene_note(note_text)
                except Exception as exc:  # noqa: BLE001
                    self._logger.debug("LANChat busy note classification skipped: %s", type(exc).__name__)
                    note_kind = ""
                if note_kind and note_kind != "chat":
                    self._record_active_runtime_busy_intervention(trigger, note_kind=note_kind)
                quick_reply = scene_runtime.record_busy_message(
                    agent_name=agent_name,
                    text=note_text,
                    source_user_id=str(trigger.get("sender_id") or ""),
                )
                if quick_reply:
                    return bool(self._send_final_reply(agent_id, agent_name, quick_reply, trigger))

            if self._async_agent_execution and self._should_send_fast_ack(trigger):
                _send_progress("已收到，我正在整理你的请求。")

            with agent_progress_sink(_send_progress):
                with self._agent_call_lock:
                    result = self._run_agent(trigger)
        except Exception as exc:
            self._logger.debug("LANChat AI agent failed: %s", type(exc).__name__)
            reply = "AI agent failed: 内部异常已记录，请稍后重试。"
        else:
            agent_id = result.sender_id
            agent_name = result.sender_name
            reply = result.text
            action_payload = getattr(result, "action_payload", None)
            action_payload = self._prepare_confirmed_action_payload(action_payload, trigger)
            action_payload = self._filter_confirmed_action_payload_for_runtime(action_payload)

        try:
            self._broadcast_confirmed_action(action_payload)
            self._logger.info(
                "[LANChatAgentTrace] phase=process_reply message_id=%s correlation=%s room=%s agent=%s/%s reply_len=%s action=%s status=%s",
                trigger.get("message_id") or "",
                self._correlation_id(trigger),
                trigger.get("room_id") or "",
                agent_id,
                agent_name,
                len(str(reply or "")),
                str((action_payload or {}).get("action_type") or ""),
                str((action_payload or {}).get("status") or ""),
            )
            return bool(
                self._send_final_reply(agent_id, agent_name, str(reply or ""), trigger, action_payload)
            )
        except Exception as exc:
            self._logger.debug("Failed to send LANChat agent reply: %s", type(exc).__name__)
            return False

    def _run(self) -> None:
        while not self._stop_event.is_set():
            processed = self.process_once()
            if not processed:
                self._stop_event.wait(self._sleep_seconds)

    def _send_final_reply(
        self,
        agent_id: str,
        agent_name: str,
        text: str,
        trigger: dict[str, Any],
        action_payload: dict[str, Any] | None = None,
    ) -> bool:
        if action_payload and (
            action_payload.get("status") in {"pending_host_confirmation", "pending"}
            or action_payload.get("requires_host_confirm")
        ):
            proposal_id = str(action_payload.get("proposal_id") or self._correlation_id(trigger))
            metadata = self._sanitize_control_payload(action_payload)
            metadata.setdefault("requires_host_confirm", True)
            if hasattr(self._corona_engine, "network_send_system_message_ex"):
                self._logger.info(
                    "[LANChatReplyTrace] phase=send_system_message_ex message_id=%s correlation=%s proposal=%s agent=%s/%s text_len=%s action=%s status=%s text=%s",
                    trigger.get("message_id") or "",
                    self._correlation_id(trigger),
                    proposal_id,
                    agent_id,
                    agent_name,
                    len(str(text or "")),
                    str((action_payload or {}).get("action_type") or ""),
                    str((action_payload or {}).get("status") or ""),
                    _trace_preview(text),
                )
                safe_text = self._safe_control_text(text)
                target_plan_id = str(
                    metadata.get("target_plan_id")
                    or metadata.get("plan_id")
                    or trigger.get("target_plan_id")
                    or ""
                )
                room_id = str(trigger.get("room_id") or "default")
                self._record_gm_proposal_send_in_agent_runtime(
                    phase="gm_proposal_send_requested",
                    room_id=room_id,
                    proposal_id=proposal_id,
                    external_plan_id=target_plan_id,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    message=safe_text,
                )
                sent = bool(self._corona_engine.network_send_system_message_ex(
                    agent_id,
                    agent_name,
                    safe_text,
                    "gm_proposal",
                    proposal_id,
                    json.dumps(metadata, ensure_ascii=False),
                ))
                self._record_gm_proposal_send_in_agent_runtime(
                    phase="gm_proposal_send_succeeded" if sent else "gm_proposal_send_failed",
                    room_id=room_id,
                    proposal_id=proposal_id,
                    external_plan_id=target_plan_id,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    message=safe_text,
                    sent=sent,
                )
                if sent:
                    self._mirror_agent_reply_context_in_agent_runtime(
                        room_id=room_id,
                        text=safe_text,
                        trigger={**dict(trigger or {}), "target_plan_id": target_plan_id},
                        agent_id=agent_id,
                        agent_name=agent_name,
                    )
                return sent
        if hasattr(self._corona_engine, "network_send_agent_reply_ex"):
            self._logger.info(
                "[LANChatReplyTrace] phase=send_agent_reply_ex message_id=%s correlation=%s reply_to=%s agent=%s/%s text_len=%s text=%s",
                trigger.get("message_id") or "",
                self._correlation_id(trigger),
                trigger.get("message_id") or "",
                agent_id,
                agent_name,
                len(str(text or "")),
                _trace_preview(text),
            )
            room_id = str(trigger.get("room_id") or "default")
            self._record_agent_reply_send_in_agent_runtime(
                phase="agent_reply_send_requested",
                room_id=room_id,
                trigger=trigger,
                agent_id=agent_id,
                agent_name=agent_name,
                message=text,
                message_kind="agent_reply",
            )
            sent = bool(self._corona_engine.network_send_agent_reply_ex(
                agent_id,
                agent_name,
                text,
                "agent_reply",
                agent_id,
                self._correlation_id(trigger),
                json.dumps({"reply_to": str(trigger.get("message_id") or "")}, ensure_ascii=False),
            ))
            self._record_agent_reply_send_in_agent_runtime(
                phase="agent_reply_send_succeeded" if sent else "agent_reply_send_failed",
                room_id=room_id,
                trigger=trigger,
                agent_id=agent_id,
                agent_name=agent_name,
                message=text,
                message_kind="agent_reply",
                sent=sent,
            )
            if sent:
                self._mirror_agent_reply_context_in_agent_runtime(
                    room_id=room_id,
                    text=text,
                    trigger=trigger,
                    agent_id=agent_id,
                    agent_name=agent_name,
                )
            return sent
        self._logger.info(
            "[LANChatReplyTrace] phase=send_agent_reply message_id=%s correlation=%s agent=%s/%s text_len=%s text=%s",
            trigger.get("message_id") or "",
            self._correlation_id(trigger),
            agent_id,
            agent_name,
            len(str(text or "")),
            _trace_preview(text),
        )
        room_id = str(trigger.get("room_id") or "default")
        self._record_agent_reply_send_in_agent_runtime(
            phase="agent_reply_send_requested",
            room_id=room_id,
            trigger=trigger,
            agent_id=agent_id,
            agent_name=agent_name,
            message=text,
            message_kind="agent_reply",
        )
        sent = bool(self._corona_engine.network_send_agent_reply(agent_id, agent_name, text))
        self._record_agent_reply_send_in_agent_runtime(
            phase="agent_reply_send_succeeded" if sent else "agent_reply_send_failed",
            room_id=room_id,
            trigger=trigger,
            agent_id=agent_id,
            agent_name=agent_name,
            message=text,
            message_kind="agent_reply",
            sent=sent,
        )
        if sent:
            self._mirror_agent_reply_context_in_agent_runtime(
                room_id=room_id,
                text=text,
                trigger=trigger,
                agent_id=agent_id,
                agent_name=agent_name,
            )
        return sent

    def _remember_room_id(self, room_id: str) -> None:
        room = str(room_id or "").strip()
        if not room:
            return
        if room in self._active_room_ids:
            try:
                self._active_room_order.remove(room)
            except ValueError:
                pass
        self._active_room_ids.add(room)
        self._active_room_order.append(room)
        while len(self._active_room_order) > MAX_ACTIVE_ROOM_IDS:
            oldest = self._active_room_order.popleft()
            self._active_room_ids.discard(oldest)

    def _forget_room_id(self, room_id: str) -> None:
        room = str(room_id or "").strip()
        if not room:
            return
        self._active_room_ids.discard(room)
        try:
            self._active_room_order.remove(room)
        except ValueError:
            pass

    def _remember_coordinator_seen_message_id(self, key: str) -> None:
        normalized = str(key or "").strip()
        if not normalized or normalized in self._coordinator_seen_message_ids:
            return
        self._coordinator_seen_message_ids.add(normalized)
        self._coordinator_seen_message_order.append(normalized)
        while len(self._coordinator_seen_message_order) > MAX_COORDINATOR_SEEN_MESSAGE_IDS:
            oldest = self._coordinator_seen_message_order.popleft()
            self._coordinator_seen_message_ids.discard(oldest)

    def _has_engine_api(self) -> bool:
        return (
            self._corona_engine is not None
            and hasattr(self._corona_engine, "network_pop_lanchat_agent_trigger")
            and hasattr(self._corona_engine, "network_send_agent_reply")
        )

    def _network_session_role_name(self) -> str:
        if self._corona_engine is None:
            return "none"
        session_role_name = getattr(self._corona_engine, "network_session_role_name", None)
        if not callable(session_role_name):
            return "none"
        try:
            return str(session_role_name() or "none").strip().lower()
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("LANChat network role check skipped: %s", type(exc).__name__)
            return "none"

    def _can_execute_agent_locally(self) -> bool:
        return self._network_session_role_name() != "client"

    def _can_execute_generation_locally(self) -> bool:
        return self._can_execute_agent_locally()

    def _get_orchestrator(self) -> LanChatAgentOrchestrator:
        if self._orchestrator is None:
            self._orchestrator = LanChatAgentOrchestrator(
                agent_factory=self._agent_factory or self._default_agent_factory,
            )
        return self._orchestrator

    def _run_agent(self, trigger: dict[str, Any]):
        return self._get_orchestrator().handle_trigger(trigger)

    def _handle_coordinator_gm_control(self, trigger: dict[str, Any]) -> str | None:
        action = self._gm_pace_action_from_trigger(trigger)
        if not action:
            return None
        if self._trusted_host_control(trigger) is False:
            return "内部执行异常已记录，当前 Runtime 执行未完成。"
        room_id = str(trigger.get("room_id") or "default")
        self._remember_room_id(room_id)
        try:
            coordinator = self._get_interaction_coordinator()
            disclosure_start = len(coordinator.disclosure_events)
            event = coordinator.control_pace(
                room_id,
                action,
                actor_id=str(trigger.get("sender_id") or trigger.get("agent_id") or "gm"),
                note=str(trigger.get("text") or ""),
            )
            emitted = self._emit_new_disclosure_events(coordinator, disclosure_start)
            self._start_coordinator_disclosure_watch(coordinator, disclosure_start + emitted)
            self._set_runtime_mode_for_pace(action, trigger=trigger)
            self._emit_generation_scheduler_disclosure()
            return f"【GM】{event.message}"
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Coordinator GM pace control skipped: %s", type(exc).__name__)
            return None

    def _handle_coordinator_gm_clarification(self, trigger: dict[str, Any]) -> str | None:
        question = self._gm_clarification_question_from_trigger(trigger)
        if not question:
            return None
        if self._trusted_host_control(trigger) is False:
            return "内部执行异常已记录，当前 Runtime 执行未完成。"
        room_id = str(trigger.get("room_id") or "default")
        self._remember_room_id(room_id)
        try:
            coordinator = self._get_interaction_coordinator()
            disclosure_start = len(coordinator.disclosure_events)
            event = coordinator.request_clarification(
                room_id,
                question,
                requested_by=str(trigger.get("sender_id") or trigger.get("agent_id") or "gm"),
            )
            emitted = self._emit_new_disclosure_events(coordinator, disclosure_start)
            self._start_coordinator_disclosure_watch(coordinator, disclosure_start + emitted)
            return f"【GM】{event.message} {question}"
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Coordinator GM clarification skipped: %s", type(exc).__name__)
            return None

    def _handle_coordinator_status_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        room_id = str(trigger.get("room_id") or "default")
        runtime_gm_summary_query = self._is_runtime_gm_summary_query(trigger)
        if runtime_gm_summary_query:
            runtime_external_plan_id = self._active_runtime_external_plan_id(room_id)
            self._remember_room_id(room_id)
            runtime_reply = self._agent_runtime_gm_summary_reply(
                room_id=room_id,
                external_plan_id=runtime_external_plan_id,
                batch_id=self._runtime_batch_id_from_message(trigger),
            )
            if runtime_reply:
                return runtime_reply
            if not self._agent_runtime_flags.can_call_legacy_main_workflow():
                self._logger.info(
                    "[LANChatGenerationTrace] phase=gm_summary_runtime_unavailable_legacy_blocked room=%s",
                    room_id,
                )
                return "Runtime 状态暂不可用，旧状态源默认已关闭。"
        runtime_summary_query = self._is_runtime_status_summary_query(trigger) or self._is_runtime_status_query_text(text)
        if runtime_summary_query:
            runtime_external_plan_id = self._active_runtime_external_plan_id(room_id)
            self._remember_room_id(room_id)
            runtime_reply = self._agent_runtime_status_reply(
                room_id=room_id,
                external_plan_id=runtime_external_plan_id,
                batch_id=self._runtime_batch_id_from_message(trigger),
            )
            if runtime_reply:
                return runtime_reply
            if not self._agent_runtime_flags.can_call_legacy_main_workflow():
                self._logger.info(
                    "[LANChatGenerationTrace] phase=status_query_runtime_unavailable_legacy_blocked room=%s",
                    room_id,
                )
                return "Runtime 状态暂不可用，旧状态源默认已关闭。"
        try:
            coordinator = self._get_interaction_coordinator()
            is_status_query = getattr(coordinator, "_is_status_query", None)
            coordinator_status_query = bool(callable(is_status_query) and is_status_query(text))
            if not coordinator_status_query and not runtime_summary_query:
                return None
            self._remember_room_id(room_id)
            runtime_reply = self._agent_runtime_status_reply(
                room_id=room_id,
                external_plan_id=self._active_runtime_external_plan_id(room_id),
                batch_id=self._runtime_batch_id_from_message(trigger),
            )
            if runtime_reply:
                return runtime_reply
            if not self._agent_runtime_flags.can_call_legacy_main_workflow():
                self._logger.info(
                    "[LANChatGenerationTrace] phase=status_query_legacy_coordinator_blocked room=%s runtime_query=%s",
                    room_id,
                    runtime_summary_query,
                )
                return "Runtime 状态暂不可用，旧状态源默认已关闭。"
            if not coordinator_status_query:
                return None
            event = coordinator.ingest_message(ChatMessage(
                room_id=room_id,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                text=text,
                is_host=self._message_sender_is_host(
                    trigger,
                    sender_type=str(trigger.get("sender_type") or ""),
                ),
                metadata=self._coordinator_sync_metadata(trigger, source="lanchat_agent_trigger"),
            ))
            if getattr(event, "event_type", "") != "status_query":
                return None
            return str(getattr(event, "message", "") or "当前状态暂不可用，请稍后再试。")
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Coordinator status query skipped: %s", type(exc).__name__)
            return None

    def _handle_agent_runtime_gm_summary_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text or not self._is_gm_summary_query(trigger, text):
            return None
        runtime = self._agent_runtime
        if runtime is None:
            return None
        room_id = str(trigger.get("room_id") or "default")
        self._remember_room_id(room_id)
        try:
            result = runtime.handle_message(
                room_id=room_id,
                text="gm_summary",
                action="runtime_gm_summary",
                external_plan_id=self._active_runtime_external_plan_id(room_id),
                sync_event={"limit": 8},
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime GM summary skipped: %s", type(exc).__name__)
            return None
        summary = result.get("gm_summary", {}) if isinstance(result, dict) else {}
        if not isinstance(summary, dict) or not summary.get("available"):
            return None
        context_count = int(summary.get("context_count") or 0)
        if context_count <= 0:
            return None
        plan = summary.get("current_plan", {}) if isinstance(summary.get("current_plan"), dict) else {}
        latest_context = summary.get("latest_context") if isinstance(summary.get("latest_context"), list) else []
        context_lines: list[str] = []
        for item in latest_context[-3:]:
            if not isinstance(item, dict):
                continue
            speaker = (
                str(item.get("agent_name") or "").strip()
                or str(item.get("owner_agent") or "").strip()
                or str(item.get("speaker_type") or "").strip()
                or "成员"
            )
            preview = str(item.get("text_preview") or "").strip()
            if not preview:
                continue
            if len(preview) > 72:
                preview = preview[:72] + "..."
            context_lines.append(f"{speaker}: {preview}")
        speaker_counts = (
            summary.get("speaker_type_counts")
            if isinstance(summary.get("speaker_type_counts"), dict)
            else {}
        )
        user_count = int(speaker_counts.get("user") or 0)
        agent_count = int(speaker_counts.get("agent") or 0)
        brief = str(plan.get("design_brief_preview") or "").strip()
        if len(brief) > 120:
            brief = brief[:120] + "..."
        model_items = [str(item) for item in (summary.get("candidate_model_items") or []) if str(item).strip()]
        substrate_items = [str(item) for item in (summary.get("substrate_items") or []) if str(item).strip()]
        model_text = "、".join(model_items[:8]) if model_items else "暂无明确模型清单"
        if len(model_items) > 8:
            model_text += f" 等 {len(model_items)} 项"
        substrate_text = "、".join(substrate_items[:6]) if substrate_items else "暂无"
        if len(substrate_items) > 6:
            substrate_text += f" 等 {len(substrate_items)} 项"
        current_plan = (
            str(summary.get("plan_id") or "").strip()
            if summary.get("has_scene_plan") and str(summary.get("plan_id") or "").strip()
            else "尚未形成 ScenePlan"
        )
        reply_lines = [
            "【GM Runtime 总结】",
            f"- 当前方案：{current_plan}",
            f"- 已记录讨论：{context_count} 条（用户 {user_count} / Agent {agent_count}）",
        ]
        if brief:
            reply_lines.append(f"- 当前共识：{brief}")
        if context_lines:
            reply_lines.append("- 最近上下文：" + "；".join(context_lines))
        reply_lines.extend([
            f"- 候选模型：{model_text}",
            f"- 环境/地形：{substrate_text}",
        ])
        return "\n".join(reply_lines)

    @staticmethod
    def _is_gm_summary_query(trigger: dict[str, Any], text: str) -> bool:
        agent_id = str(trigger.get("agent_id") or trigger.get("target_agent_id") or "").strip().lower()
        agent_name = str(trigger.get("agent_name") or trigger.get("target_agent_name") or "").strip().lower()
        if agent_id != "gm" and agent_name not in {"gm", "主持人", "裁判", "game master"}:
            return False
        value = str(text or "").strip()
        if not value:
            return False
        summary_words = ("总结", "整理", "归纳", "当前方案", "当前共识", "复盘")
        return any(word in value for word in summary_words)

    def _handle_agent_runtime_command(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        command = self._runtime_command_from_text(text)
        if not command:
            return None
        room_id = str(trigger.get("room_id") or "default")
        external_plan_id = self._active_runtime_external_plan_id(room_id)
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                action=f"{command}_generation",
                external_plan_id=external_plan_id,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime command skipped: %s", type(exc).__name__)
            return None
        command_result = result.get("command", {}) if isinstance(result, dict) else {}
        if not isinstance(command_result, dict) or not command_result.get("applied"):
            return None
        status = str(command_result.get("new_status") or "")
        message = str(command_result.get("message") or "")
        plan_id = str(command_result.get("plan_id") or "")
        self._logger.info(
            "[LANChatRuntimeTrace] phase=runtime_command_applied room=%s plan=%s command=%s status=%s text=%s",
            room_id,
            plan_id,
            command,
            status,
            _trace_preview(text),
        )
        label = {"pause": "暂停", "cancel": "取消", "resume": "恢复"}.get(command, command)
        return f"【Runtime {label}】{message}"

    def _handle_agent_runtime_worker_drain_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if not self._is_runtime_worker_drain_query(text):
            return None
        room_id = str(trigger.get("room_id") or "default")
        external_plan_id = self._active_runtime_external_plan_id(room_id)
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                action="worker_drain",
                external_plan_id=external_plan_id,
                max_graphs=self._runtime_worker_drain_limit_from_text(text),
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime worker drain skipped: %s", type(exc).__name__)
            return None
        drain = result.get("drain", {}) if isinstance(result, dict) else {}
        if not isinstance(drain, dict):
            return None
        drained_count = int(drain.get("drained_count") or 0)
        graphs = drain.get("graphs", [])
        completed = sum(
            1
            for graph in graphs
            if isinstance(graph, dict) and str(graph.get("status") or "") == "completed"
        )
        status = result.get("status", {}) if isinstance(result, dict) else {}
        queue_counts = {}
        if isinstance(status, dict):
            queue_counts = dict((status.get("tool_graph_summary") or {}).get("queue_status_counts") or {})
        lines = [
            "[Runtime Worker]",
            f"drained graphs: {drained_count}",
        ]
        if completed:
            lines.append(f"completed: {completed}")
        if queue_counts:
            rendered_counts = ", ".join(f"{key}:{value}" for key, value in sorted(queue_counts.items()))
            lines.append(f"queue: {rendered_counts}")
        if drained_count == 0:
            lines.append(str(result.get("message") or "No queued Runtime graph is ready."))
        return "\n".join(lines)

    @staticmethod
    def _runtime_command_from_text(text: str) -> str:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return ""
        if any(word in normalized for word in ("取消生成", "取消任务", "停止生成", "终止生成", "不要生成", "cancel generation", "cancel task")):
            return "cancel"
        if any(word in normalized for word in ("暂停生成", "暂停一下", "先暂停", "暂停任务", "pause generation", "pause task")):
            return "pause"
        if any(word in normalized for word in ("继续生成", "恢复生成", "继续执行", "恢复执行", "resume generation", "resume task")):
            return "resume"
        return ""

    @staticmethod
    def _is_runtime_worker_drain_query(text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return False
        runtime_markers = ("runtime", "agentruntime", "agent runtime", "worker", "drain", "闃熷垪", "鎵ц闃熷垪")
        drain_markers = ("worker drain", "drain queue", "runtime drain", "drain", "执行队列", "推进队列", "跑队列", "消费队列")
        return any(marker in normalized for marker in runtime_markers) and any(
            marker in normalized for marker in drain_markers
        )

    @staticmethod
    def _runtime_worker_drain_limit_from_text(text: str) -> int:
        normalized = str(text or "").strip().lower()
        if any(token in normalized for token in ("鍏ㄩ儴", "鍏ㄩ噺", "鍓╀綑", "all", "rest")):
            return 1000
        return 1

    def _handle_agent_runtime_provider_status_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if not self._is_runtime_provider_status_query(text):
            return None
        room_id = str(trigger.get("room_id") or "default")
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                action="provider_status",
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime provider status skipped: %s", type(exc).__name__)
            return None
        status = result.get("provider_status", {}) if isinstance(result, dict) else {}
        provider_summary = status.get("provider_summary", {}) if isinstance(status, dict) else {}
        provider_readiness = status.get("provider_readiness_summary", {}) if isinstance(status, dict) and isinstance(status.get("provider_readiness_summary"), dict) else {}
        message_delivery = status.get("message_delivery_summary", {}) if isinstance(status, dict) and isinstance(status.get("message_delivery_summary"), dict) else {}
        engine_write = status.get("engine_write_summary", {}) if isinstance(status, dict) and isinstance(status.get("engine_write_summary"), dict) else {}
        engine_write_boundary = (
            status.get("engine_write_boundary_summary", {})
            if isinstance(status, dict) and isinstance(status.get("engine_write_boundary_summary"), dict)
            else {}
        )
        if not isinstance(provider_summary, dict):
            return None
        lines: list[str] = []
        for key in ("scene_snapshot", "image_resource", "model_resource", "actor_import", "environment_component", "environment_import", "review", "layout_transform"):
            item = provider_summary.get(key, {})
            if not isinstance(item, dict):
                continue
            mode = str(item.get("mode") or "unknown").replace("provider", "adapter")
            status_text = str(item.get("status") or ("enabled" if mode == "adapter" else "fallback")).replace("provider", "adapter")
            reason = str(item.get("reason") or "").replace("provider", "adapter")
            requested = "requested" if item.get("requested") else "default"
            label = key.replace("_", "-")
            line = f"- {label}: {mode} / {status_text} / {requested}"
            if reason:
                line += f" / {reason}"
            lines.append(line)
        if not lines:
            return None
        readiness_text = self._format_agent_runtime_resource_readiness_report(provider_readiness)
        delivery_text = self._format_agent_runtime_message_delivery_report(message_delivery)
        engine_write_text = self._format_agent_runtime_engine_write_report(engine_write)
        engine_write_boundary_text = self._format_agent_runtime_engine_write_boundary_report(engine_write_boundary)
        return (
            "【Runtime Resources 预检】\n"
            + "\n".join(lines)
            + f"\n- readiness: {readiness_text}"
            + f"\n- engine_write: {engine_write_text}"
            + f"\n- engine_write_boundary: {engine_write_boundary_text}"
            + f"\n- message_delivery: {delivery_text}"
        )

    def _handle_agent_runtime_enqueue_generation_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if not self._is_runtime_enqueue_generation_query(text):
            return None
        if not self._can_execute_generation_locally():
            return None
        room_id = str(trigger.get("room_id") or "default")
        host_id = str(trigger.get("sender_id") or trigger.get("from") or "")
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=host_id,
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                action="confirm_and_enqueue",
                scene_name=self._runtime_scene_name_from_trigger(trigger),
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "[LANChatGenerationTrace] phase=agent_runtime_enqueue_failed room=%s exc_type=%s",
                room_id,
                type(exc).__name__,
            )
            return "内部执行异常已记录，当前 Runtime 执行未完成。"
        runtime_plan = result.get("plan", {}) if isinstance(result, dict) else {}
        runtime_plan_id = str(runtime_plan.get("plan_id") or "")
        graphs = result.get("graphs", []) if isinstance(result, dict) else []
        queued_count = sum(1 for graph in graphs if isinstance(graph, dict) and str(graph.get("status") or "") == "queued")
        if runtime_plan_id and bool(result.get("recorded")):
            self._logger.info(
                "[LANChatGenerationTrace] phase=agent_runtime_enqueue_result room=%s runtime_plan=%s queued_graphs=%s",
                room_id,
                runtime_plan_id,
                queued_count,
            )
            return (
                f"[AgentRuntime Enqueue] ScenePlan {runtime_plan_id} queued "
                f"{queued_count} ToolCallGraph(s). Use Runtime worker drain to execute."
            )
        if not self._agent_runtime_flags.can_call_legacy_main_workflow():
            return "AgentRuntime enqueue failed: no active Runtime ScenePlan."
        try:
            coordinator = self._get_interaction_coordinator()
            plan = coordinator.active_plan_for_room(room_id)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime legacy enqueue skipped: %s", type(exc).__name__)
            return None
        if plan is None:
            return None
        try:
            if getattr(plan, "status", None) != SeedPlanStatus.CONFIRMED:
                confirmed = coordinator.confirm_seed_plan(str(getattr(plan, "plan_id", "") or ""), host_id)
                if not getattr(confirmed, "ok", False):
                    return str(getattr(confirmed, "message", "") or "Runtime enqueue failed: plan is not confirmed.")
                plan = coordinator.active_plan_for_room(room_id) or plan
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=str(
                    getattr(plan, "design_brief", "")
                    or getattr(plan, "intent_summary", "")
                    or getattr(plan, "title", "")
                    or text
                ),
                sender_id=host_id,
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                owner_agent=str(getattr(plan, "owner_agent_name", "") or getattr(plan, "owner_agent_id", "") or ""),
                source_context_agents=list(getattr(plan, "source_context_agents", []) or []),
                action="confirm_and_enqueue",
                external_plan_id=str(getattr(plan, "plan_id", "") or ""),
                scene_name=self._runtime_scene_name_from_plan(plan),
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "[LANChatGenerationTrace] phase=agent_runtime_enqueue_failed room=%s plan=%s exc_type=%s",
                room_id,
                getattr(plan, "plan_id", ""),
                type(exc).__name__,
            )
            return "内部执行异常已记录，当前 Runtime 执行未完成。"
        runtime_plan = result.get("plan", {}) if isinstance(result, dict) else {}
        runtime_plan_id = str(runtime_plan.get("plan_id") or "")
        graphs = result.get("graphs", []) if isinstance(result, dict) else []
        queued_count = sum(1 for graph in graphs if isinstance(graph, dict) and str(graph.get("status") or "") == "queued")
        self._logger.info(
            "[LANChatGenerationTrace] phase=agent_runtime_enqueue_result room=%s external_plan=%s runtime_plan=%s queued_graphs=%s",
            room_id,
            getattr(plan, "plan_id", ""),
            runtime_plan_id,
            queued_count,
        )
        return (
            f"[AgentRuntime Enqueue] ScenePlan {runtime_plan_id} queued "
            f"{queued_count} ToolCallGraph(s). Use Runtime worker drain to execute."
        )

    @staticmethod
    def _is_runtime_provider_status_query(text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return False
        provider_markers = (
            "provider",
            "adapter",
            "runtime preflight",
            "runtime provider",
            "provider status",
            "真实provider",
            "真实 provider",
            "适配器",
            "预检",
            "通道",
            "真实通道",
            "接上",
        )
        runtime_markers = ("runtime", "agentruntime", "agent runtime")
        return any(marker in normalized for marker in provider_markers) and any(
            marker in normalized for marker in runtime_markers
        )

    @staticmethod
    def _is_runtime_enqueue_generation_query(text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return False
        runtime_markers = ("runtime", "agentruntime", "agent runtime")
        enqueue_markers = (
            "confirm_and_enqueue",
            "enqueue generation",
            "runtime enqueue",
            "鍏ラ槦",
            "运行时",
            "纭鍏ラ槦",
            "鎺掑叆闃熷垪",
        )
        generation_markers = ("generate", "generation", "鐢熸垚", "鎵ц", "start")
        return any(marker in normalized for marker in runtime_markers) and any(
            marker in normalized for marker in enqueue_markers
        ) and any(marker in normalized for marker in generation_markers)

    def _handle_agent_runtime_engine_write_status_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if not self._is_runtime_engine_write_status_query(text):
            return None
        room_id = str(trigger.get("room_id") or "default")
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                action="engine_write_status",
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime engine write status skipped: %s", type(exc).__name__)
            return None
        status = result.get("engine_write_status", {}) if isinstance(result, dict) else {}
        summary = result.get("engine_write_summary", {}) if isinstance(result, dict) else {}
        boundary_summary = (
            result.get("engine_write_boundary_summary", {}) if isinstance(result, dict) else {}
        )
        if not isinstance(summary, dict):
            summary = {}
        if not isinstance(boundary_summary, dict):
            boundary_summary = {}
        if not isinstance(status, dict):
            return None
        lines: list[str] = []
        for key in ("environment_import", "actor_import", "actor_delete", "layout_transform"):
            item = status.get(key, {}) if isinstance(status.get(key), dict) else {}
            mode = str(item.get("mode") or "unknown").replace("provider", "adapter")
            status_text = str(item.get("status") or ("enabled" if mode == "adapter" else "fallback")).replace("provider", "adapter")
            reason = str(item.get("reason") or "").replace("provider", "adapter")
            requested = "requested" if item.get("requested") else "default"
            line = f"- {key}: {mode} / {status_text} / {requested}"
            if reason:
                line += f" / {reason}"
            lines.append(line)
        lines.append(f"- replay: {self._format_agent_runtime_engine_write_report(summary)}")
        lines.append(
            f"- engine boundary: {self._format_agent_runtime_engine_write_boundary_report(boundary_summary)}"
        )
        return "【Runtime Engine Write 预检】\n" + "\n".join(lines)

    @staticmethod
    def _is_runtime_engine_write_status_query(text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return False
        engine_markers = (
            "engine write",
            "engine bridge",
            "runtime engine",
            "actor import",
            "layout transform",
            "import provider",
            "transform provider",
            "寮曟搸鍐欏叆",
            "鐪熷疄瀵煎叆",
            "鐪熷疄鍐欏叆",
            "瀵煎叆閫氶亾",
            "鍙樻崲閫氶亾",
            "鍐欏叆閫氶亾",
        )
        runtime_markers = ("runtime", "engine", "provider", "adapter", "寮曟搸", "瀵煎叆", "鍐欏叆", "閫氶亾")
        return any(marker in normalized for marker in engine_markers) and any(
            marker in normalized for marker in runtime_markers
        )

    def _handle_agent_runtime_scene_snapshot_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if not self._is_runtime_scene_snapshot_query(text):
            return None
        room_id = str(trigger.get("room_id") or "default")
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                action="scene_snapshot_status",
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime scene snapshot status skipped: %s", type(exc).__name__)
            return None
        snapshot = result.get("snapshot", {}) if isinstance(result, dict) else {}
        if not isinstance(snapshot, dict):
            return None
        graph = snapshot.get("graph", {}) if isinstance(snapshot.get("graph"), dict) else {}
        summary = snapshot.get("snapshot_summary", {}) if isinstance(snapshot.get("snapshot_summary"), dict) else {}
        actor_count = int(summary.get("observed_actor_count") or summary.get("actor_count") or 0)
        source = str(summary.get("source") or "runtime_state")
        graph_status = str(graph.get("status") or "unknown")
        return (
            "【Runtime Scene Snapshot】\n"
            f"- graph: {graph_status}\n"
            f"- actor_count: {actor_count}\n"
            f"- source: {source}"
        )

    @staticmethod
    def _is_runtime_scene_snapshot_query(text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return False
        snapshot_markers = (
            "scene snapshot",
            "runtime scene snapshot",
            "snapshot status",
            "refresh scene snapshot",
            "鍦烘櫙蹇収",
            "鍒锋柊鍦烘櫙蹇収",
            "褰撳墠鍦烘櫙蹇収",
            "寮曟搸蹇収",
            "actor蹇収",
            "actor 蹇収",
        )
        runtime_markers = ("runtime", "agentruntime", "agent runtime", "鍦烘櫙蹇収", "寮曟搸蹇収", "actor蹇収", "actor 蹇収")
        return any(marker in normalized for marker in snapshot_markers) and any(
            marker in normalized for marker in runtime_markers
        )

    def _handle_agent_runtime_tool_manifest_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if not self._is_runtime_tool_manifest_query(text):
            return None
        room_id = str(trigger.get("room_id") or "default")
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                action="tool_manifest",
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime tool manifest query skipped: %s", type(exc).__name__)
            return None
        manifest = result.get("tool_manifest", {}) if isinstance(result, dict) else {}
        summary = manifest.get("summary", {}) if isinstance(manifest, dict) else {}
        tools = manifest.get("tools", []) if isinstance(manifest, dict) else []
        if not isinstance(summary, dict) or not isinstance(tools, list):
            return None
        categories = summary.get("category_counts", {}) if isinstance(summary.get("category_counts"), dict) else {}
        category_text = ", ".join(
            f"{key}:{value}"
            for key, value in sorted(categories.items())
            if str(key)
        ) or "none"
        preview_names: list[str] = []
        for item in tools[:8]:
            if isinstance(item, dict) and item.get("name"):
                preview_names.append(str(item.get("name")))
        for key_tool in (
            "runtime.scene.snapshot",
            "runtime.environment.import_components",
            "runtime.actor.import_batch",
            "runtime.layout.apply_delta",
            "runtime.actor.mark_deleted",
        ):
            if key_tool in preview_names:
                continue
            if any(isinstance(item, dict) and item.get("name") == key_tool for item in tools):
                preview_names.append(key_tool)
        preview = ", ".join(preview_names) or "none"
        return (
            "【Runtime Tool 能力清单】\n"
            f"- tool_count: {int(summary.get('tool_count') or len(tools))}\n"
            f"- categories: {category_text}\n"
            f"- preview: {preview}"
        )

    @staticmethod
    def _is_runtime_tool_manifest_query(text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return False
        manifest_markers = (
            "tool manifest",
            "tool capabilities",
            "runtime tools",
            "runtime tool",
            "工具清单",
            "工具能力",
            "可用工具",
            "能力清单",
        )
        runtime_markers = ("runtime", "agentruntime", "agent runtime", "工具", "tool")
        return any(marker in normalized for marker in manifest_markers) and any(
            marker in normalized for marker in runtime_markers
        )

    def _handle_agent_runtime_operation_replay_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if not self._is_runtime_operation_replay_query(text):
            return None
        room_id = str(trigger.get("room_id") or "default")
        external_plan_id = self._active_runtime_external_plan_id(room_id)
        runtime_batch_id = self._runtime_batch_id_from_message(trigger)
        sync_event = {"batch_id": runtime_batch_id} if runtime_batch_id else None
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                action="operation_replay",
                external_plan_id=external_plan_id,
                sync_event=sync_event,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime operation replay query skipped: %s", type(exc).__name__)
            return None
        replay = result.get("operation_replay", {}) if isinstance(result, dict) else {}
        if not isinstance(replay, dict):
            return None
        event_counts = replay.get("event_counts", {}) if isinstance(replay.get("event_counts"), dict) else {}
        review_advisory = (
            replay.get("review_advisory_summary", {})
            if isinstance(replay.get("review_advisory_summary"), dict)
            else {}
        )
        final_adjustment_confirmation = (
            replay.get("final_adjustment_confirmation_replay_summary", {})
            if isinstance(replay.get("final_adjustment_confirmation_replay_summary"), dict)
            else {}
        )
        message_delivery = (
            replay.get("message_delivery_summary", {})
            if isinstance(replay.get("message_delivery_summary"), dict)
            else {}
        )
        runtime_commands = (
            replay.get("runtime_command_summary", {})
            if isinstance(replay.get("runtime_command_summary"), dict)
            else {}
        )
        tool_execution = (
            replay.get("tool_execution_summary", {})
            if isinstance(replay.get("tool_execution_summary"), dict)
            else {}
        )
        tool_queue = (
            replay.get("tool_graph_queue_summary", {})
            if isinstance(replay.get("tool_graph_queue_summary"), dict)
            else {}
        )
        state_patch = (
            replay.get("state_patch_summary", {})
            if isinstance(replay.get("state_patch_summary"), dict)
            else {}
        )
        runtime_guard = (
            replay.get("runtime_guard_replay_summary", {})
            if isinstance(replay.get("runtime_guard_replay_summary"), dict)
            else {}
        )
        plan_lifecycle = (
            replay.get("scene_plan_lifecycle_summary", {})
            if isinstance(replay.get("scene_plan_lifecycle_summary"), dict)
            else {}
        )
        intervention_batch = (
            replay.get("intervention_batch_replay_summary", {})
            if isinstance(replay.get("intervention_batch_replay_summary"), dict)
            else {}
        )
        geometry_replay = (
            replay.get("geometry_fact_replay_summary", {})
            if isinstance(replay.get("geometry_fact_replay_summary"), dict)
            else {}
        )
        runtime_events = (
            replay.get("runtime_event_replay_summary", {})
            if isinstance(replay.get("runtime_event_replay_summary"), dict)
            else {}
        )
        failure_strategy = (
            replay.get("tool_failure_strategy_summary", {})
            if isinstance(replay.get("tool_failure_strategy_summary"), dict)
            else {}
        )
        layout_adjustment = (
            replay.get("layout_adjustment_summary", {})
            if isinstance(replay.get("layout_adjustment_summary"), dict)
            else {}
        )
        vlm_checkpoint = (
            replay.get("vlm_checkpoint_summary", {})
            if isinstance(replay.get("vlm_checkpoint_summary"), dict)
            else {}
        )
        environment_component = (
            replay.get("environment_component_summary", {})
            if isinstance(replay.get("environment_component_summary"), dict)
            else {}
        )
        resource_readiness = (
            replay.get("resource_readiness_replay_summary", {})
            if isinstance(replay.get("resource_readiness_replay_summary"), dict)
            else {}
        )
        sync_replay = (
            replay.get("sync_summary", {})
            if isinstance(replay.get("sync_summary"), dict)
            else {}
        )
        asset_transfer_replay = (
            replay.get("asset_transfer_replay_summary", {})
            if isinstance(replay.get("asset_transfer_replay_summary"), dict)
            else {}
        )
        worker_drain_replay = (
            replay.get("worker_drain_replay_summary", {})
            if isinstance(replay.get("worker_drain_replay_summary"), dict)
            else {}
        )
        peer_sync_replay = (
            replay.get("peer_sync_replay_summary", {})
            if isinstance(replay.get("peer_sync_replay_summary"), dict)
            else {}
        )
        engine_write = (
            replay.get("engine_write_summary", {})
            if isinstance(replay.get("engine_write_summary"), dict)
            else {}
        )
        engine_write_boundary = (
            replay.get("engine_write_boundary_summary", {})
            if isinstance(replay.get("engine_write_boundary_summary"), dict)
            else {}
        )
        batch_resource_lifecycle = (
            replay.get("batch_resource_lifecycle_summary", {})
            if isinstance(replay.get("batch_resource_lifecycle_summary"), dict)
            else {}
        )
        planning_context = (
            replay.get("planning_context_summary", {})
            if isinstance(replay.get("planning_context_summary"), dict)
            else {}
        )
        entries = replay.get("entries", []) if isinstance(replay.get("entries"), list) else []
        def _safe_replay_event_name(value: Any) -> str:
            event = str(value or "")
            if not event:
                return ""
            safe = event
            for marker in ("provider", "prompt", "url", "raw"):
                safe = re.sub(marker, "runtime", safe, flags=re.IGNORECASE)
            return safe

        count_text = ", ".join(
            f"{_safe_replay_event_name(key)}:{value}"
            for key, value in sorted(event_counts.items())
            if str(key)
        ) or "none"
        recent_events: list[str] = []
        for entry in entries[-5:]:
            if not isinstance(entry, dict):
                continue
            event = _safe_replay_event_name(entry.get("event"))
            if event:
                recent_events.append(event)
        recent_text = ", ".join(recent_events) or "none"
        review_advisory_text = self._format_agent_runtime_replay_review_advisory_report(review_advisory)
        final_adjustment_text = self._format_agent_runtime_replay_final_adjustment_report(
            final_adjustment_confirmation
        )
        message_delivery_text = self._format_agent_runtime_message_delivery_report(message_delivery)
        command_text = self._format_agent_runtime_replay_command_report(runtime_commands)
        tool_execution_text = self._format_agent_runtime_replay_tool_execution_report(tool_execution)
        tool_queue_text = self._format_agent_runtime_replay_tool_queue_report(tool_queue)
        state_patch_text = self._format_agent_runtime_replay_state_patch_report(state_patch)
        runtime_guard_text = self._format_agent_runtime_replay_guard_report(runtime_guard)
        plan_lifecycle_text = self._format_agent_runtime_replay_plan_lifecycle_report(plan_lifecycle)
        intervention_batch_text = self._format_agent_runtime_replay_intervention_report(intervention_batch)
        geometry_replay_text = self._format_agent_runtime_replay_geometry_report(geometry_replay)
        runtime_event_text = self._format_agent_runtime_replay_runtime_event_report(runtime_events)
        failure_strategy_text = self._format_agent_runtime_replay_failure_strategy_report(failure_strategy)
        layout_adjustment_text = self._format_agent_runtime_replay_layout_report(layout_adjustment)
        vlm_checkpoint_text = self._format_agent_runtime_replay_vlm_report(vlm_checkpoint)
        environment_component_text = self._format_agent_runtime_replay_environment_report(environment_component)
        resource_readiness_text = self._format_agent_runtime_replay_resource_readiness_report(resource_readiness)
        sync_replay_text = self._format_agent_runtime_sync_replay_report(sync_replay)
        asset_transfer_replay_text = self._format_agent_runtime_replay_asset_transfer_report(asset_transfer_replay)
        worker_drain_replay_text = self._format_agent_runtime_worker_drain_replay_report(worker_drain_replay)
        peer_sync_replay_text = self._format_agent_runtime_replay_peer_sync_report(peer_sync_replay)
        engine_write_text = self._format_agent_runtime_engine_write_report(engine_write)
        engine_write_boundary_text = self._format_agent_runtime_engine_write_boundary_report(engine_write_boundary)
        batch_resource_lifecycle_text = self._format_agent_runtime_batch_resource_lifecycle_report(
            batch_resource_lifecycle
        )
        planning_context_text = self._format_agent_runtime_context_report(planning_context)
        return (
            "【Runtime Operation Replay】\n"
            f"- entry_count: {int(replay.get('entry_count') or 0)}\n"
            f"- event_counts: {count_text}\n"
            f"- context: {planning_context_text}\n"
            f"- batch_resources: {batch_resource_lifecycle_text}\n"
            f"- commands: {command_text}\n"
            f"- tools: {tool_execution_text}\n"
            f"- queue: {tool_queue_text}\n"
            f"- state_patch: {state_patch_text}\n"
            f"- guard: {runtime_guard_text}\n"
            f"- plan_lifecycle: {plan_lifecycle_text}\n"
            f"- interventions: {intervention_batch_text}\n"
            f"- geometry: {geometry_replay_text}\n"
            f"- runtime_events: {runtime_event_text}\n"
            f"- failure_strategy: {failure_strategy_text}\n"
            f"- layout: {layout_adjustment_text}\n"
            f"- vlm: {vlm_checkpoint_text}\n"
            f"- environment: {environment_component_text}\n"
            f"- resource_readiness: {resource_readiness_text}\n"
            f"- sync: {sync_replay_text}\n"
            f"- asset_transfer: {asset_transfer_replay_text}\n"
            f"- worker_drain: {worker_drain_replay_text}\n"
            f"- peer_sync: {peer_sync_replay_text}\n"
            f"- review_advisory: {review_advisory_text}\n"
            f"- final_adjustment: {final_adjustment_text}\n"
            f"- engine_write: {engine_write_text}\n"
            f"- engine_write_boundary: {engine_write_boundary_text}\n"
            f"- message_delivery: {message_delivery_text}\n"
            f"- recent: {recent_text}"
        )

    @staticmethod
    def _is_runtime_operation_replay_query(text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return False
        replay_markers = (
            "operation replay",
            "operation log",
            "runtime replay",
            "runtime operation",
            "鎵ц鍥炴斁",
            "鎿嶄綔鍥炴斁",
            "鎿嶄綔鏃ュ織",
            "澶嶇洏鏃ュ織",
            "杩愯鏃ュ織",
        )
        runtime_markers = ("runtime", "agentruntime", "agent runtime", "鍥炴斁", "鏃ュ織", "澶嶇洏")
        return any(marker in normalized for marker in replay_markers) and any(
            marker in normalized for marker in runtime_markers
        )

    def _handle_agent_runtime_report_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if not self._is_runtime_report_query(text):
            return None
        room_id = str(trigger.get("room_id") or "default")
        external_plan_id = self._active_runtime_external_plan_id(room_id)
        runtime_batch_id = self._runtime_batch_id_from_message(trigger)
        sync_event = {"batch_id": runtime_batch_id} if runtime_batch_id else None
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                action="runtime_report",
                external_plan_id=external_plan_id,
                sync_event=sync_event,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime report query skipped: %s", type(exc).__name__)
            return None
        if isinstance(result, dict) and not result.get("recorded", True):
            return str(result.get("message") or "AgentRuntime report is unavailable for this room.")
        report = result.get("report", {}) if isinstance(result, dict) else {}
        if not isinstance(report, dict):
            return None
        plan_summary = report.get("plan_summary", {}) if isinstance(report.get("plan_summary"), dict) else {}
        classification = report.get("classification_summary", {}) if isinstance(report.get("classification_summary"), dict) else {}
        scene_registry = report.get("scene_entity_registry", {}) if isinstance(report.get("scene_entity_registry"), dict) else {}
        scene_design_contract = report.get("scene_design_contract_summary", {}) if isinstance(report.get("scene_design_contract_summary"), dict) else {}
        semantic_arbitration = report.get("semantic_arbitration_summary", {}) if isinstance(report.get("semantic_arbitration_summary"), dict) else {}
        scene_snapshot = report.get("scene_snapshot_summary", {}) if isinstance(report.get("scene_snapshot_summary"), dict) else {}
        environment = report.get("environment_component_summary", {}) if isinstance(report.get("environment_component_summary"), dict) else {}
        runtime_resources = report.get("resource_summary", {}) if isinstance(report.get("resource_summary"), dict) else {}
        report_health = (
            report.get("report_health_summary", {})
            if isinstance(report.get("report_health_summary"), dict)
            else {}
        )
        review_summary = report.get("review_summary", {}) if isinstance(report.get("review_summary"), dict) else {}
        geometry_summary = report.get("geometry_fact_summary", {}) if isinstance(report.get("geometry_fact_summary"), dict) else {}
        review_proposals = report.get("review_advisory_proposal_summary", {}) if isinstance(report.get("review_advisory_proposal_summary"), dict) else {}
        review_confirmations = report.get("review_advisory_confirmation_summary", {}) if isinstance(report.get("review_advisory_confirmation_summary"), dict) else {}
        layout_summary = report.get("layout_adjustment_summary", {}) if isinstance(report.get("layout_adjustment_summary"), dict) else {}
        final_adjustment_confirmations = report.get("final_adjustment_confirmation_summary", {}) if isinstance(report.get("final_adjustment_confirmation_summary"), dict) else {}
        runtime_commands = report.get("runtime_command_summary", {}) if isinstance(report.get("runtime_command_summary"), dict) else {}
        intervention_summary = report.get("intervention_summary", {}) if isinstance(report.get("intervention_summary"), dict) else {}
        batch_summary = report.get("batch_summary", {}) if isinstance(report.get("batch_summary"), dict) else {}
        import_summary = report.get("import_summary", {}) if isinstance(report.get("import_summary"), dict) else {}
        batch_tooling = report.get("batch_tooling_summary", {}) if isinstance(report.get("batch_tooling_summary"), dict) else {}
        state_patch = report.get("state_patch_summary", {}) if isinstance(report.get("state_patch_summary"), dict) else {}
        graph_summary = report.get("tool_graph_summary", {}) if isinstance(report.get("tool_graph_summary"), dict) else {}
        tool_execution = report.get("tool_execution_digest", {}) if isinstance(report.get("tool_execution_digest"), dict) else {}
        tool_queue_health = report.get("tool_queue_health_summary", {}) if isinstance(report.get("tool_queue_health_summary"), dict) else {}
        sync_summary = report.get("sync_summary", {}) if isinstance(report.get("sync_summary"), dict) else {}
        asset_transfer_summary = report.get("asset_transfer_summary", {}) if isinstance(report.get("asset_transfer_summary"), dict) else {}
        provider_summary = report.get("provider_summary", {}) if isinstance(report.get("provider_summary"), dict) else {}
        provider_readiness = report.get("provider_readiness_summary", {}) if isinstance(report.get("provider_readiness_summary"), dict) else {}
        engine_write_readiness = (
            report.get("engine_write_readiness_summary", {})
            if isinstance(report.get("engine_write_readiness_summary"), dict)
            else {}
        )
        replay_summary = report.get("operation_replay_summary", {}) if isinstance(report.get("operation_replay_summary"), dict) else {}
        runtime_guard = (
            report.get("runtime_guard_replay_summary", {})
            if isinstance(report.get("runtime_guard_replay_summary"), dict)
            else replay_summary.get("runtime_guard_replay_summary", {})
            if isinstance(replay_summary.get("runtime_guard_replay_summary"), dict)
            else {}
        )
        plan_lifecycle = (
            report.get("scene_plan_lifecycle_summary", {})
            if isinstance(report.get("scene_plan_lifecycle_summary"), dict)
            else replay_summary.get("scene_plan_lifecycle_summary", {})
            if isinstance(replay_summary.get("scene_plan_lifecycle_summary"), dict)
            else {}
        )
        vlm_checkpoint = (
            report.get("vlm_checkpoint_summary", {})
            if isinstance(report.get("vlm_checkpoint_summary"), dict)
            else replay_summary.get("vlm_checkpoint_summary", {})
            if isinstance(replay_summary.get("vlm_checkpoint_summary"), dict)
            else {}
        )
        review_advisory_replay = (
            report.get("review_advisory_replay_summary", {})
            if isinstance(report.get("review_advisory_replay_summary"), dict)
            else replay_summary.get("review_advisory_summary", {})
            if isinstance(replay_summary.get("review_advisory_summary"), dict)
            else {}
        )
        final_adjustment_replay = (
            replay_summary.get("final_adjustment_confirmation_replay_summary", {})
            if isinstance(replay_summary.get("final_adjustment_confirmation_replay_summary"), dict)
            else {}
        )
        message_delivery = replay_summary.get("message_delivery_summary", {}) if isinstance(replay_summary.get("message_delivery_summary"), dict) else {}
        engine_write = replay_summary.get("engine_write_summary", {}) if isinstance(replay_summary.get("engine_write_summary"), dict) else {}
        engine_write_boundary = (
            report.get("engine_write_boundary_summary", {})
            if isinstance(report.get("engine_write_boundary_summary"), dict)
            else replay_summary.get("engine_write_boundary_summary", {})
            if isinstance(replay_summary.get("engine_write_boundary_summary"), dict)
            else {}
        )
        planning_context = replay_summary.get("planning_context_summary", {}) if isinstance(replay_summary.get("planning_context_summary"), dict) else {}
        sync_replay = replay_summary.get("sync_replay_summary", {}) if isinstance(replay_summary.get("sync_replay_summary"), dict) else {}
        asset_transfer_replay = (
            replay_summary.get("asset_transfer_replay_summary", {})
            if isinstance(replay_summary.get("asset_transfer_replay_summary"), dict)
            else {}
        )
        worker_drain_replay = (
            report.get("worker_drain_replay_summary", {})
            if isinstance(report.get("worker_drain_replay_summary"), dict)
            else replay_summary.get("worker_drain_replay_summary", {})
            if isinstance(replay_summary.get("worker_drain_replay_summary"), dict)
            else {}
        )
        peer_sync_replay = (
            replay_summary.get("peer_sync_replay_summary", {})
            if isinstance(replay_summary.get("peer_sync_replay_summary"), dict)
            else {}
        )
        failure_strategy = (
            replay_summary.get("tool_failure_strategy_summary", {})
            if isinstance(replay_summary.get("tool_failure_strategy_summary"), dict)
            else {}
        )
        accepted = intervention_summary.get("accepted", []) if isinstance(intervention_summary.get("accepted"), list) else []
        deferred = intervention_summary.get("deferred", []) if isinstance(intervention_summary.get("deferred"), list) else []
        pending = intervention_summary.get("pending", []) if isinstance(intervention_summary.get("pending"), list) else []
        model_items = self._format_agent_runtime_short_list(classification.get("model_items"), fallback="none")
        substrate_items = self._format_agent_runtime_short_list(classification.get("substrate_items"), fallback="none")
        guarded_items = self._format_agent_runtime_short_list(classification.get("guarded_items"), fallback="none")
        raw_model_items = classification.get("model_items") if isinstance(classification.get("model_items"), list) else []
        raw_substrate_items = (
            classification.get("substrate_items") if isinstance(classification.get("substrate_items"), list) else []
        )
        classification_counts_text = (
            f"model/substrate "
            f"{len(raw_model_items)}/"
            f"{len(raw_substrate_items)}"
        )
        scene_registry_text = self._format_agent_runtime_scene_registry_report(scene_registry)
        scene_contract_text = self._format_agent_runtime_scene_contract_report(scene_design_contract)
        semantic_arbitration_text = self._format_agent_runtime_semantic_arbitration_report(semantic_arbitration)
        scene_snapshot_text = self._format_agent_runtime_scene_snapshot_report(scene_snapshot)
        runtime_resource_text = self._format_agent_runtime_resource_stage_report(runtime_resources)
        report_health_text = self._format_agent_runtime_report_health_report(report_health)
        fact_source_text = self._format_agent_runtime_fact_source_boundary_report(
            report.get("fact_source_boundary_summary")
        )
        closure_text = self._format_agent_runtime_closure_report(
            report.get("fact_source_boundary_summary"),
            state_patch,
            operation_count=report.get("operation_count"),
            operation_total_count=report.get("operation_total_count"),
        )
        import_text = self._format_agent_runtime_import_stage_report(import_summary)
        actor_import_text = self._format_agent_runtime_actor_import_boundary_report(
            import_summary,
            scene_registry,
            engine_write_boundary,
        )
        environment_text = self._format_agent_runtime_environment_report(environment)
        review_text = self._format_agent_runtime_review_report(review_summary)
        geometry_text = self._format_agent_runtime_geometry_fact_report(geometry_summary)
        review_proposal_text = self._format_agent_runtime_review_proposal_report(review_proposals)
        review_confirmation_text = self._format_agent_runtime_review_confirmation_report(review_confirmations)
        layout_text = self._format_agent_runtime_layout_report(layout_summary, final_adjustment_confirmations)
        command_text = self._format_agent_runtime_command_report(runtime_commands)
        sync_text = self._format_agent_runtime_sync_report(sync_summary)
        asset_transfer_text = self._format_agent_runtime_asset_transfer_report(asset_transfer_summary)
        sync_replay_text = self._format_agent_runtime_sync_replay_report(sync_replay)
        asset_transfer_replay_text = self._format_agent_runtime_replay_asset_transfer_report(asset_transfer_replay)
        worker_drain_replay_text = self._format_agent_runtime_worker_drain_replay_report(worker_drain_replay)
        peer_sync_replay_text = self._format_agent_runtime_replay_peer_sync_report(peer_sync_replay)
        batch_tooling_text = self._format_agent_runtime_batch_tooling_report(batch_tooling)
        state_patch_text = self._format_agent_runtime_replay_state_patch_report(state_patch)
        tool_execution_text = self._format_agent_runtime_tool_execution_digest_report(tool_execution)
        failure_strategy_text = self._format_agent_runtime_replay_failure_strategy_report(failure_strategy)
        runtime_guard_text = self._format_agent_runtime_replay_guard_report(runtime_guard)
        plan_lifecycle_text = self._format_agent_runtime_replay_plan_lifecycle_report(plan_lifecycle)
        vlm_checkpoint_text = self._format_agent_runtime_replay_vlm_report(vlm_checkpoint)
        review_advisory_replay_text = self._format_agent_runtime_replay_review_advisory_report(review_advisory_replay)
        final_adjustment_replay_text = self._format_agent_runtime_replay_final_adjustment_report(
            final_adjustment_replay
        )
        tool_queue_health_text = self._format_agent_runtime_tool_queue_health_report(tool_queue_health)
        resource_text = self._format_agent_runtime_resource_report(provider_summary)
        resource_readiness_text = self._format_agent_runtime_resource_readiness_report(provider_readiness)
        engine_write_readiness_text = self._format_agent_runtime_engine_write_readiness_report(
            engine_write_readiness
        )
        replay_text = self._format_agent_runtime_replay_report(replay_summary)
        message_delivery_text = self._format_agent_runtime_message_delivery_report(message_delivery)
        engine_write_text = self._format_agent_runtime_engine_write_report(engine_write)
        engine_write_boundary_text = self._format_agent_runtime_engine_write_boundary_report(engine_write_boundary)
        planning_context_text = self._format_agent_runtime_context_report(planning_context)
        return (
            "[Runtime Report]\n"
            f"- plan: {str(plan_summary.get('title') or report.get('plan_id') or 'unknown')}\n"
            f"- status: {str(plan_summary.get('status') or 'unknown')}\n"
            f"- objects: {len(plan_summary.get('concrete_object_items') or [])}\n"
            f"- classification: {classification_counts_text}\n"
            f"- models: {model_items}\n"
            f"- substrate: {substrate_items}\n"
            f"- scene registry: {scene_registry_text}\n"
            f"- scene contract: {scene_contract_text}\n"
            f"- semantic arbitration: {semantic_arbitration_text}\n"
            f"- scene snapshot: {scene_snapshot_text}\n"
            f"- fact source: {fact_source_text}\n"
            f"- closure: {closure_text}\n"
            f"- environment: {environment_text}\n"
            f"- runtime resources: {runtime_resource_text}\n"
            f"- report health: {report_health_text}\n"
            f"- import: {import_text}\n"
            f"- actor import: {actor_import_text}\n"
            f"- review: {review_text}\n"
            f"- geometry facts: {geometry_text}\n"
            f"- review proposals: {review_proposal_text}\n"
            f"- review confirmations: {review_confirmation_text}\n"
            f"- layout: {layout_text}\n"
            f"- commands: {command_text}\n"
            f"- guarded: {guarded_items}\n"
            f"- batches: {int(batch_summary.get('batch_count') or 0)}\n"
            f"- batch tooling: {batch_tooling_text}\n"
            f"- state patch: {state_patch_text}\n"
            f"- failure strategy: {failure_strategy_text}\n"
            f"- guard: {runtime_guard_text}\n"
            f"- plan lifecycle: {plan_lifecycle_text}\n"
            f"- vlm replay: {vlm_checkpoint_text}\n"
            f"- review advisory replay: {review_advisory_replay_text}\n"
            f"- final adjustment replay: {final_adjustment_replay_text}\n"
                f"- graphs: {int(graph_summary.get('graph_count') or 0)}\n"
                f"- tool execution: {tool_execution_text}\n"
                f"- runtime queue: {tool_queue_health_text}\n"
            f"- sync: {sync_text}\n"
            f"- asset transfer: {asset_transfer_text}\n"
            f"- sync replay: {sync_replay_text}\n"
            f"- asset transfer replay: {asset_transfer_replay_text}\n"
            f"- worker drain replay: {worker_drain_replay_text}\n"
            f"- peer sync replay: {peer_sync_replay_text}\n"
            f"- resources: {resource_text}\n"
            f"- resource readiness: {resource_readiness_text}\n"
            f"- engine write readiness: {engine_write_readiness_text}\n"
            f"- engine write: {engine_write_text}\n"
            f"- engine write boundary: {engine_write_boundary_text}\n"
            f"- context: {planning_context_text}\n"
            f"- message delivery: {message_delivery_text}\n"
            f"- replay: {replay_text}\n"
            f"- interventions: pending {len(pending)}, accepted {len(accepted)}, deferred {len(deferred)}"
        )

    @staticmethod
    def _format_agent_runtime_short_list(value: Any, *, fallback: str = "none", limit: int = 6) -> str:
        if not isinstance(value, list):
            return fallback
        items = [str(item).strip() for item in value if str(item).strip()]
        if not items:
            return fallback
        preview = "、".join(items[:max(1, int(limit or 1))])
        if len(items) > max(1, int(limit or 1)):
            preview += f" 等 {len(items)} 项"
        return preview

    @staticmethod
    def _format_agent_runtime_scene_registry_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "none"
        entity_type_counts = dict(summary.get("entity_type_counts") or {})
        entity_count = int(summary.get("entity_count") or 0)
        actor_count = int(summary.get("actor_count") or entity_type_counts.get("actor") or 0)
        terrain_count = int(summary.get("terrain_count") or entity_type_counts.get("terrain") or 0)
        skybox_count = int(summary.get("skybox_count") or entity_type_counts.get("skybox") or 0)
        entities = summary.get("entities") if isinstance(summary.get("entities"), list) else []
        roles: list[str] = []
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            role = str(entity.get("semantic_role") or entity.get("name") or "").strip()
            if role and role not in roles:
                roles.append(role)
            if len(roles) >= 4:
                break
        if entity_count <= 0 and actor_count <= 0 and terrain_count <= 0 and skybox_count <= 0:
            return "none"
        parts = [
            f"entities {entity_count}",
            f"actor {actor_count}",
            f"terrain {terrain_count}",
            f"skybox {skybox_count}",
        ]
        if roles:
            parts.append("roles " + "、".join(roles))
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_environment_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "none"
        count = int(summary.get("component_count") or 0)
        requested = int(summary.get("requested_count") or 0)
        ready = int(summary.get("ready_count") or count or 0)
        failed = int(summary.get("failed_count") or 0)
        imported = int(summary.get("imported_count") or 0)
        import_failed = int(summary.get("import_failed_count") or 0)
        event_count = int(summary.get("event_count") or 0)
        if count <= 0 and requested <= 0 and failed <= 0 and imported <= 0 and import_failed <= 0 and event_count <= 0:
            return "none"
        type_counts = summary.get("type_counts") if isinstance(summary.get("type_counts"), dict) else {}
        parts = [
            f"{str(key).replace('_', '-')}: {int(value or 0)}"
            for key, value in sorted(type_counts.items())
            if int(value or 0) > 0
        ]
        detail = "、".join(parts[:4]) if parts else "components tracked"
        counters = [f"{count} component(s)", f"ready {ready}"]
        if imported:
            counters.append(f"imported {imported}")
        if requested:
            counters.append(f"requested {requested}")
        if failed:
            counters.append(f"failed {failed}")
        if import_failed:
            counters.append(f"import-failed {import_failed}")
        return f"{'；'.join(counters)}, {detail}"

    @staticmethod
    def _format_agent_runtime_scene_contract_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary or not summary.get("available"):
            return "none"

        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in ("prompt", "provider", "url", "raw", "token", "api-key", "path"):
                text = re.sub(marker, "resource", text, flags=re.IGNORECASE)
            return text[:80]

        scene_type = safe_label(summary.get("scene_type")) or "unknown-scene"
        environment_type = safe_label(summary.get("environment_type")) or "unknown-env"
        terrain_type = safe_label(summary.get("terrain_type")) or "unknown-terrain"
        boundary_type = safe_label(summary.get("boundary_type")) or "unknown-boundary"
        mood = LANChatAgentWorker._format_agent_runtime_short_list(
            summary.get("mood"),
            fallback="none",
            limit=3,
        )
        style = LANChatAgentWorker._format_agent_runtime_short_list(
            summary.get("style_keywords"),
            fallback="none",
            limit=3,
        )
        avoid = LANChatAgentWorker._format_agent_runtime_short_list(
            summary.get("avoid_keywords"),
            fallback="none",
            limit=3,
        )
        version = int(summary.get("version") or 0)
        return (
            f"{scene_type}/{environment_type}, terrain {terrain_type}, boundary {boundary_type}, "
            f"mood {mood}, style {style}, avoid {avoid}, v{version}"
        )

    @staticmethod
    def _format_agent_runtime_semantic_arbitration_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary or not summary.get("available"):
            return "none"

        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in ("prompt", "provider", "url", "raw", "token", "api-key", "path"):
                text = re.sub(marker, "resource", text, flags=re.IGNORECASE)
            return text[:80]

        state = safe_label(summary.get("arbitration_state")) or "unknown"
        readiness = safe_label(summary.get("execution_readiness")) or "unknown"
        owner = safe_label(summary.get("owner_agent")) or "none"
        agents = LANChatAgentWorker._format_agent_runtime_short_list(
            summary.get("contributing_agents"),
            fallback="none",
            limit=4,
        )
        flags = LANChatAgentWorker._format_agent_runtime_short_list(
            summary.get("risk_flags"),
            fallback="none",
            limit=4,
        )
        confirm = "yes" if bool(summary.get("requires_host_confirmation")) else "no"
        clarify = "yes" if bool(summary.get("needs_clarification")) else "no"
        multi_agent = "yes" if bool(summary.get("multi_agent_discussion")) else "no"
        return (
            f"{state}, readiness {readiness}, owner {owner}, agents {agents}, "
            f"multi-agent {multi_agent}, confirm {confirm}, clarify {clarify}, flags {flags}"
        )

    @staticmethod
    def _format_agent_runtime_tool_execution_digest_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary or not summary.get("available"):
            return "none"

        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in (
                "prompt",
                "provider",
                "url",
                "raw",
                "token",
                "api-key",
                "path",
                "tool-call",
                "tool-name",
            ):
                text = re.sub(marker, "resource", text, flags=re.IGNORECASE)
            return text[:80]

        graph_count = int(summary.get("graph_count") or 0)
        queue_count = int(summary.get("queue_count") or 0)
        node_count = int(summary.get("node_count") or 0)
        succeeded = int(summary.get("succeeded_count") or 0)
        failed = int(summary.get("failed_count") or 0)
        blocked = int(summary.get("blocked_count") or 0)
        skipped = int(summary.get("skipped_count") or 0)
        running = int(summary.get("running_count") or 0)
        planned = int(summary.get("planned_count") or 0)
        ready = int(summary.get("ready_count") or 0)
        attention = "yes" if bool(summary.get("attention_required")) else "no"
        reasons = LANChatAgentWorker._format_agent_runtime_short_list(
            summary.get("attention_reasons"),
            fallback="none",
            limit=4,
        )
        latest = summary.get("latest_attention") if isinstance(summary.get("latest_attention"), dict) else {}
        latest_status = safe_label(latest.get("status"))
        latest_reason = safe_label(latest.get("reason")) if latest_status else ""
        parts = [
            f"graphs {graph_count}",
            f"queue {queue_count}",
            f"nodes {node_count}",
            f"ok {succeeded}",
            f"failed {failed}",
            f"blocked {blocked}",
            f"skipped {skipped}",
        ]
        if running or planned or ready:
            parts.append(f"active r/p/ready {running}/{planned}/{ready}")
        parts.append(f"attention {attention}")
        if reasons != "none":
            parts.append(f"reasons {reasons}")
        if latest_status:
            parts.append(f"latest {latest_status}" + (f": {latest_reason}" if latest_reason else ""))
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_review_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "none"
        review_count = int(summary.get("review_count") or 0)
        if review_count <= 0:
            return "none"
        issue_count = int(summary.get("issue_count") or 0)
        advisory_count = int(summary.get("advisory_count") or 0)
        status_counts = summary.get("status_counts") if isinstance(summary.get("status_counts"), dict) else {}
        checkpoint_counts = summary.get("checkpoint_counts") if isinstance(summary.get("checkpoint_counts"), dict) else {}
        statuses = ",".join(
            f"{str(key).replace('_', '-')}:{int(value or 0)}"
            for key, value in sorted(status_counts.items())
            if int(value or 0) > 0
        )
        checkpoints = ",".join(
            f"{str(key).replace('_', '-')}:{int(value or 0)}"
            for key, value in sorted(checkpoint_counts.items())
            if int(value or 0) > 0
        )
        parts = [f"{review_count} review(s)", f"issues {issue_count}", f"advisory {advisory_count}"]
        if statuses:
            parts.append(f"status {statuses}")
        if checkpoints:
            parts.append(f"checkpoint {checkpoints}")
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_geometry_fact_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "none"
        fact_count = int(summary.get("fact_count") or 0)
        aabb_count = int(summary.get("aabb_actor_count") or 0)
        skipped_count = int(summary.get("aabb_skipped_count") or 0)
        overlap_count = int(summary.get("overlap_issue_count") or 0)
        if fact_count <= 0 and aabb_count <= 0 and skipped_count <= 0 and overlap_count <= 0:
            return "none"
        status_counts = summary.get("status_counts") if isinstance(summary.get("status_counts"), dict) else {}
        fact_type_counts = summary.get("fact_type_counts") if isinstance(summary.get("fact_type_counts"), dict) else {}
        statuses = ",".join(
            f"{str(key).replace('_', '-')}:{int(value or 0)}"
            for key, value in sorted(status_counts.items())
            if int(value or 0) > 0
        )
        fact_types = ",".join(
            f"{str(key).replace('_', '-')}:{int(value or 0)}"
            for key, value in sorted(fact_type_counts.items())
            if int(value or 0) > 0
        )
        parts = [
            f"{fact_count} fact(s)",
            f"AABB actors {aabb_count}",
            f"overlap issues {overlap_count}",
        ]
        if skipped_count:
            parts.append(f"skipped {skipped_count}")
        if statuses:
            parts.append(f"status {statuses}")
        if fact_types:
            parts.append(f"type {fact_types}")
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_review_proposal_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "none"
        proposal_count = int(summary.get("proposal_count") or 0)
        if proposal_count <= 0:
            return "none"
        item_count = int(summary.get("item_count") or 0)
        status_counts = summary.get("status_counts") if isinstance(summary.get("status_counts"), dict) else {}
        statuses = ",".join(
            f"{str(key).replace('_', '-')}:{int(value or 0)}"
            for key, value in sorted(status_counts.items())
            if int(value or 0) > 0
        )
        pending_count = int(status_counts.get("proposed") or 0)
        confirmed_count = int(status_counts.get("confirmed") or 0)
        rejected_count = int(status_counts.get("rejected") or 0)
        if pending_count > 0:
            decision_state = "waiting host confirmation"
        elif confirmed_count > 0 or rejected_count > 0:
            decision_state = "host decision recorded"
        else:
            decision_state = "decision state unknown"
        parts = [f"{proposal_count} proposal(s)", f"items {item_count}", decision_state]
        if statuses:
            parts.append(f"status {statuses}")
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_review_confirmation_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "none"
        confirmation_count = int(summary.get("confirmation_count") or 0)
        if confirmation_count <= 0:
            return "none"
        decision_counts = summary.get("decision_counts") if isinstance(summary.get("decision_counts"), dict) else {}
        decisions = ",".join(
            f"{str(key).replace('_', '-')}:{int(value or 0)}"
            for key, value in sorted(decision_counts.items())
            if int(value or 0) > 0
        )
        return f"{confirmation_count} confirmation(s)" + (f"；decision {decisions}" if decisions else "")

    @staticmethod
    def _format_agent_runtime_layout_report(summary: Any, confirmation_summary: Any = None) -> str:
        if not isinstance(summary, dict) or not summary:
            proposal_count = 0
            proposals: list[Any] = []
        else:
            proposal_count = int(summary.get("proposal_count") or 0)
            proposals = summary.get("proposals") if isinstance(summary.get("proposals"), list) else []
        confirmation_count = 0
        if isinstance(confirmation_summary, dict):
            confirmation_count = int(confirmation_summary.get("confirmation_count") or 0)
        if proposal_count <= 0 and confirmation_count <= 0:
            return "none"
        status_counts: dict[str, int] = {}
        delta_count = 0
        applied_delta_count = int(summary.get("applied_delta_count") or 0) if isinstance(summary, dict) else 0
        skipped_delta_count = int(summary.get("skipped_delta_count") or 0) if isinstance(summary, dict) else 0
        transform_result_count = int(summary.get("transform_result_count") or 0) if isinstance(summary, dict) else 0
        ground_snapped_count = int(summary.get("ground_snapped_count") or 0) if isinstance(summary, dict) else 0
        overlap_resolved_count = int(summary.get("overlap_resolved_count") or 0) if isinstance(summary, dict) else 0
        transform_failure_code_counts = (
            summary.get("layout_transform_failure_code_counts")
            if isinstance(summary, dict) and isinstance(summary.get("layout_transform_failure_code_counts"), dict)
            else {}
        )
        risk_levels: list[str] = []
        for proposal in proposals:
            if not isinstance(proposal, dict):
                continue
            status = str(proposal.get("status") or "").strip()
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
            delta_count += int(proposal.get("delta_count") or 0)
            risk = str(proposal.get("risk_level") or "").strip().replace("_", "-")
            if risk and risk not in risk_levels:
                risk_levels.append(risk)
        parts = [f"{proposal_count} proposal(s)", f"deltas {delta_count}"]
        parts.append(f"applied {applied_delta_count}")
        parts.append(f"skipped {skipped_delta_count}")
        parts.append(f"transforms {transform_result_count}")
        if ground_snapped_count:
            parts.append(f"ground-snapped {ground_snapped_count}")
        if overlap_resolved_count:
            parts.append(f"overlap-resolved {overlap_resolved_count}")
        if transform_failure_code_counts:
            def _safe_layout_failure_label(value: Any) -> str:
                label = str(value or "").strip().lower().replace("_", "-").replace(" ", "-")
                blocked = ("provider", "url", "http", "prompt", "raw", "api-key", "apikey", "secret", "token")
                if any(marker in label for marker in blocked):
                    return "redacted"
                return label[:64] or "unknown"

            failure_items = ",".join(
                f"{_safe_layout_failure_label(key)}:{int(value or 0)}"
                for key, value in sorted(transform_failure_code_counts.items())
                if int(value or 0) > 0
            )
            if failure_items:
                parts.append(f"transform-failures {failure_items}")
        if confirmation_count:
            parts.append(f"confirmations {confirmation_count}")
        if risk_levels:
            parts.append("risk " + ",".join(risk_levels[:3]))
        if status_counts:
            statuses = ",".join(
                f"{str(key).replace('_', '-')}:{int(value or 0)}"
                for key, value in sorted(status_counts.items())
                if int(value or 0) > 0
            )
            if statuses:
                parts.append(f"status {statuses}")
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_command_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "none"
        command_count = int(summary.get("command_count") or 0)
        commands = summary.get("latest_commands") if isinstance(summary.get("latest_commands"), list) else []
        if command_count <= 0 and not commands:
            return "none"

        def safe_text(value: Any) -> str:
            text = str(value or "").strip()
            for marker in ("provider", "prompt", "url", "raw", "token", "api_key"):
                text = re.sub(marker, "runtime", text, flags=re.IGNORECASE)
            return text.replace("_", "-")[:80]

        latest_parts: list[str] = []
        for item in commands[-3:]:
            if not isinstance(item, dict):
                continue
            command = safe_text(item.get("command"))
            old_status = safe_text(item.get("old_status"))
            new_status = safe_text(item.get("new_status"))
            if not command:
                continue
            if old_status or new_status:
                latest_parts.append(f"{command}:{old_status or '?'}->{new_status or '?'}")
            else:
                latest_parts.append(command)
        parts = [f"{command_count} command(s)"]
        if latest_parts:
            parts.append("latest " + ",".join(latest_parts))
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_command_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "none"
        command_count = int(summary.get("command_count") or 0)
        if command_count <= 0:
            return "none"

        def safe_text(value: Any) -> str:
            text = str(value or "").strip()
            for marker in ("provider", "prompt", "url", "raw", "token", "api_key"):
                text = re.sub(marker, "runtime", text, flags=re.IGNORECASE)
            return text.replace("_", "-")[:80]

        cancelled_batches = int(summary.get("cancelled_batch_total") or 0)
        cancelled_graphs = int(summary.get("cancelled_graph_total") or 0)
        resumed_graphs = int(summary.get("resumed_graph_total") or 0)
        retried_graphs = int(summary.get("retried_graph_total") or 0)
        parts = [f"{command_count} command(s)"]
        if cancelled_batches or cancelled_graphs:
            parts.append(f"cancelled batch/graph {cancelled_batches}/{cancelled_graphs}")
        if resumed_graphs:
            parts.append(f"resumed graphs {resumed_graphs}")
        if retried_graphs:
            parts.append(f"retried graphs {retried_graphs}")
        latest = summary.get("latest_command") if isinstance(summary.get("latest_command"), dict) else {}
        command = safe_text(latest.get("command"))
        old_status = safe_text(latest.get("old_status"))
        new_status = safe_text(latest.get("new_status"))
        if command:
            if old_status or new_status:
                parts.append(f"latest {command}:{old_status or '?'}->{new_status or '?'}")
            else:
                parts.append(f"latest {command}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_tool_execution_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "started 0, succeeded 0, failed 0"
        started = int(summary.get("started_count") or 0)
        succeeded = int(summary.get("succeeded_count") or 0)
        failed = int(summary.get("failed_count") or 0)
        blocked = int(summary.get("blocked_count") or 0)
        retry_scheduled = int(summary.get("retry_scheduled_count") or 0)
        skipped = int(summary.get("skipped_count") or 0)
        parts = [
            f"started {started}",
            f"succeeded {succeeded}",
            f"failed {failed}",
            f"blocked {blocked}",
        ]
        if retry_scheduled:
            parts.append(f"retry {retry_scheduled}")
        if skipped:
            parts.append(f"skipped {skipped}")
        latest = summary.get("latest_tool_event") if isinstance(summary.get("latest_tool_event"), dict) else {}
        event = str(latest.get("event") or "").strip().replace("_", "-")
        status = str(latest.get("status") or "").strip().replace("_", "-")
        if event:
            parts.append(f"latest {event}:{status or 'unknown'}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_tool_queue_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "queued 0, dequeued 0, completed 0"
        queued = int(summary.get("queued_count") or 0)
        dequeued = int(summary.get("dequeued_count") or 0)
        completed = int(summary.get("completed_count") or 0)
        rejected = int(summary.get("rejected_count") or 0)
        empty = int(summary.get("empty_count") or 0)
        blocked = int(summary.get("blocked_count") or 0)
        missing_graph = int(summary.get("missing_graph_count") or 0)
        parts = [
            f"queued {queued}",
            f"dequeued {dequeued}",
            f"completed {completed}",
        ]
        if rejected:
            parts.append(f"rejected {rejected}")
        if empty:
            parts.append(f"empty {empty}")
        if blocked:
            parts.append(f"blocked {blocked}")
        if missing_graph:
            parts.append(f"missing {missing_graph}")
        latest = summary.get("latest_queue_event") if isinstance(summary.get("latest_queue_event"), dict) else {}
        event = str(latest.get("event") or "").strip().replace("_", "-")
        status = str(latest.get("status") or "").strip().replace("_", "-")
        if event:
            parts.append(f"latest {event}:{status or 'unknown'}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_state_patch_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "applied 0, conflict 0, invalid 0"
        version_stamped = int(summary.get("version_stamped") or 0)
        applied = int(summary.get("applied") or 0)
        conflict = int(summary.get("conflict") or 0)
        invalid = int(summary.get("invalid") or 0)
        reconciled = int(summary.get("reconciled") or 0)
        reconcile_failed = int(summary.get("reconcile_failed") or 0)
        parts = [
            f"versioned {version_stamped}",
            f"applied {applied}",
            f"conflict {conflict}",
            f"invalid {invalid}",
        ]
        if reconciled:
            parts.append(f"reconciled {reconciled}")
        if reconcile_failed:
            parts.append(f"reconcile-failed {reconcile_failed}")
        latest_events = summary.get("latest_events") if isinstance(summary.get("latest_events"), list) else []
        latest = latest_events[-1] if latest_events and isinstance(latest_events[-1], dict) else {}
        event = str(latest.get("event") or "").strip().replace("_", "-")
        applied_version = latest.get("applied_version")
        if event:
            suffix = f":v{applied_version}" if isinstance(applied_version, int) else ""
            parts.append(f"latest {event}{suffix}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_guard_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "blocked 0"
        blocked = int(summary.get("blocked_count") or 0)
        high_risk = int(summary.get("high_risk_confirmation_required_count") or 0)
        write_confirm = int(summary.get("write_confirmation_required_count") or 0)
        system_actor = int(summary.get("system_actor_write_blocked_count") or 0)
        visible_blocked = int(summary.get("user_visible_blocked_event_count") or 0)
        requires_write = int(summary.get("requires_write_blocked_count") or 0)
        unconfirmed = int(summary.get("unconfirmed_blocked_count") or 0)
        confirmed = int(summary.get("confirmed_blocked_count") or 0)
        risk_counts = summary.get("risk_level_counts") if isinstance(summary.get("risk_level_counts"), dict) else {}

        def format_risk_counts() -> str:
            parts: list[str] = []
            for risk in ("high", "medium", "low", "unknown"):
                try:
                    count = int(risk_counts.get(risk) or 0)
                except (TypeError, ValueError):
                    count = 0
                if count:
                    parts.append(f"{risk}:{count}")
            return "/".join(parts)
        parts = [f"blocked {blocked}"]
        if high_risk:
            parts.append(f"high-risk-confirm {high_risk}")
        if write_confirm:
            parts.append(f"write-confirm {write_confirm}")
        if system_actor:
            parts.append(f"system-actor {system_actor}")
        if visible_blocked:
            parts.append(f"visible-blocked {visible_blocked}")
        if requires_write:
            parts.append(f"write-blocked {requires_write}")
        if unconfirmed:
            parts.append(f"unconfirmed {unconfirmed}")
        if confirmed:
            parts.append(f"confirmed-blocked {confirmed}")
        risk_text = format_risk_counts()
        if risk_text:
            parts.append(f"risk {risk_text}")
        latest = summary.get("latest_block") if isinstance(summary.get("latest_block"), dict) else {}
        reason = str(latest.get("reason") or "").strip().replace("_", "-")
        if reason:
            latest_risk = str(latest.get("risk_level") or "").strip().replace("_", "-")
            latest_requires_write = bool(latest.get("requires_write"))
            latest_confirmed = bool(latest.get("confirmed"))
            latest_suffix = []
            if latest_risk:
                latest_suffix.append(f"risk:{latest_risk}")
            if latest_requires_write:
                latest_suffix.append("write")
            latest_suffix.append("confirmed" if latest_confirmed else "unconfirmed")
            suffix = " " + "/".join(latest_suffix) if latest_suffix else ""
            parts.append(f"latest {reason}{suffix}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_plan_lifecycle_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "created 0, confirmed 0"
        created = int(summary.get("created_count") or 0)
        confirmed = int(summary.get("confirmed_count") or 0)
        state_persisted = int(summary.get("state_persisted_count") or 0)
        state_failed = int(summary.get("state_persist_failed_count") or 0)
        status_persisted = int(summary.get("status_persisted_count") or 0)
        status_failed = int(summary.get("status_persist_failed_count") or 0)
        extracted = int(summary.get("extracted_count") or 0)
        parts = [
            f"created {created}",
            f"confirmed {confirmed}",
            f"state {state_persisted}/{state_failed}",
            f"status {status_persisted}/{status_failed}",
        ]
        if extracted:
            parts.append(f"extracted {extracted}")
        latest = summary.get("latest_plan_event") if isinstance(summary.get("latest_plan_event"), dict) else {}
        event = str(latest.get("event") or "").strip().replace("_", "-")
        status = str(latest.get("status") or "").strip().replace("_", "-")
        if event:
            parts.append(f"latest {event}:{status or 'unknown'}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_intervention_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "routed 0, queued 0, absorbed 0"
        routed = int(summary.get("routed_count") or 0)
        queued = int(summary.get("queued_count") or 0)
        persisted = int(summary.get("persisted_count") or 0)
        persist_failed = int(summary.get("persist_failed_count") or 0)
        skipped = int(summary.get("skipped_count") or 0)
        enqueue_failed = int(summary.get("enqueue_failed_count") or 0)
        absorbed = int(summary.get("absorbed_count") or 0)
        route_absorbable = int(summary.get("route_absorbable_count") or 0)
        route_non_absorbable = int(summary.get("route_non_absorbable_count") or 0)
        route_requested_items = int(summary.get("route_requested_item_count") or 0)
        merge_events = int(summary.get("merge_event_count") or 0)
        merged_items = int(summary.get("merged_item_count") or 0)
        merge_absorbed = int(summary.get("merge_absorbed_count") or 0)
        parts = [
            f"routed {routed}",
            f"queued {queued}",
            f"persisted {persisted}/{persist_failed}",
            f"absorbed {absorbed}",
        ]
        if route_absorbable or route_non_absorbable or route_requested_items:
            parts.append(
                f"route {route_absorbable}/{route_non_absorbable} items {route_requested_items}"
            )
        if merge_events or merged_items or merge_absorbed:
            parts.append(f"merge {merge_events} items {merged_items} absorbed {merge_absorbed}")
        if skipped:
            parts.append(f"skipped {skipped}")
        if enqueue_failed:
            parts.append(f"enqueue-failed {enqueue_failed}")
        latest = (
            summary.get("latest_intervention_batch")
            if isinstance(summary.get("latest_intervention_batch"), dict)
            else {}
        )
        event = str(latest.get("event") or "").strip().replace("_", "-")
        status = str(latest.get("status") or "").strip().replace("_", "-")
        item_count = int(latest.get("item_count") or 0)
        if event:
            parts.append(f"latest {event}:{status or 'unknown'} items {item_count}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_geometry_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "facts 0, overlap 0"
        patch_events = int(summary.get("patch_event_count") or 0)
        fact_count = int(summary.get("fact_count") or 0)
        aabb_actor_count = int(summary.get("aabb_actor_count") or 0)
        aabb_skipped_count = int(summary.get("aabb_skipped_count") or 0)
        overlap_issue_count = int(summary.get("overlap_issue_count") or 0)
        parts = [
            f"patches {patch_events}",
            f"facts {fact_count}",
            f"aabb {aabb_actor_count}/{aabb_skipped_count}",
            f"overlap {overlap_issue_count}",
        ]
        status_counts = summary.get("status_counts") if isinstance(summary.get("status_counts"), dict) else {}
        if status_counts:
            status_text = ", ".join(
                f"{str(status).strip().replace('_', '-')}:{int(count or 0)}"
                for status, count in sorted(status_counts.items())
                if str(status).strip()
            )
            if status_text:
                parts.append(f"status {status_text}")
        fact_type_counts = (
            summary.get("fact_type_counts")
            if isinstance(summary.get("fact_type_counts"), dict)
            else {}
        )
        if fact_type_counts:
            type_text = ", ".join(
                f"{str(fact_type).strip().replace('_', '-')}:{int(count or 0)}"
                for fact_type, count in sorted(fact_type_counts.items())
                if str(fact_type).strip()
            )
            if type_text:
                parts.append(f"types {type_text}")
        latest = (
            summary.get("latest_geometry_event")
            if isinstance(summary.get("latest_geometry_event"), dict)
            else {}
        )
        latest_type = str(latest.get("fact_type") or "").strip().replace("_", "-")
        latest_status = str(latest.get("status") or "").strip().replace("_", "-")
        latest_actor_count = int(latest.get("actor_count") or 0)
        latest_issue_count = int(latest.get("issue_count") or 0)
        latest_skipped_count = int(latest.get("skipped_count") or 0)
        if latest_type:
            parts.append(
                f"latest {latest_type}:{latest_status or 'unknown'} "
                f"actors {latest_actor_count} issues {latest_issue_count} skipped {latest_skipped_count}"
            )
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_runtime_event_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "emitted 0, failed 0"
        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in ("provider", "prompt", "url", "raw", "token", "api-key"):
                text = re.sub(marker, "resource", text, flags=re.IGNORECASE)
            return text[:80]

        emitted = int(summary.get("emitted_count") or 0)
        failed = int(summary.get("emit_failed_count") or 0)
        skipped_count = int(summary.get("disclosure_skipped_count") or 0)
        parts = [f"emitted {emitted}", f"failed {failed}"]
        if skipped_count > 0:
            parts.append(f"skipped {skipped_count}")
        type_counts = summary.get("event_type_counts") if isinstance(summary.get("event_type_counts"), dict) else {}
        top_types = [
            f"{safe_label(key)}:{int(value or 0)}"
            for key, value in sorted(type_counts.items())[:4]
            if str(key).strip() and int(value or 0) > 0
        ]
        if top_types:
            parts.append("types " + ",".join(top_types))
        report_ready = int(summary.get("report_ready_count") or 0)
        report_attention = int(summary.get("report_attention_count") or 0)
        if report_ready > 0:
            report_part = f"report-ready {report_ready}"
            if report_attention > 0:
                report_part += f"/attention {report_attention}"
            status_counts = (
                summary.get("report_health_status_counts")
                if isinstance(summary.get("report_health_status_counts"), dict)
                else {}
            )
            status_parts = [
                f"{safe_label(key)}:{int(value or 0)}"
                for key, value in sorted(status_counts.items())[:3]
                if str(key).strip() and int(value or 0) > 0
            ]
            if status_parts:
                report_part += " " + ",".join(status_parts)
            parts.append(report_part)
        latest = summary.get("latest_runtime_event") if isinstance(summary.get("latest_runtime_event"), dict) else {}
        event_type = safe_label(latest.get("event_type"))
        status = safe_label(latest.get("status"))
        if event_type:
            parts.append(f"latest {event_type}:{status or 'unknown'}")
        latest_report = summary.get("latest_report_ready") if isinstance(summary.get("latest_report_ready"), dict) else {}
        report_status = safe_label(latest_report.get("status"))
        if report_status:
            parts.append(f"latest-report {report_status}")
        environment_import_failure_code_counts = (
            latest_report.get("environment_import_failure_code_counts")
            if isinstance(latest_report.get("environment_import_failure_code_counts"), dict)
            else {}
        )
        environment_failure_parts = [
            f"{safe_label(key)}:{int(value or 0)}"
            for key, value in sorted(environment_import_failure_code_counts.items())[:3]
            if str(key).strip() and int(value or 0) > 0
        ]
        if environment_failure_parts:
            parts.append("env-import-failures " + ",".join(environment_failure_parts))
        engine_write_bridge_failed_count = int(
            latest_report.get("engine_write_bridge_failed_count") or 0
        )
        engine_write_bridge_error_code_counts = (
            latest_report.get("engine_write_bridge_error_code_counts")
            if isinstance(latest_report.get("engine_write_bridge_error_code_counts"), dict)
            else {}
        )
        engine_write_failure_parts = [
            f"{safe_label(key)}:{int(value or 0)}"
            for key, value in sorted(engine_write_bridge_error_code_counts.items())[:3]
            if str(key).strip() and int(value or 0) > 0
        ]
        if engine_write_failure_parts:
            parts.append("engine-write-failures " + ",".join(engine_write_failure_parts))
        elif engine_write_bridge_failed_count > 0:
            parts.append(f"engine-write-failures {engine_write_bridge_failed_count}")
        engine_write_readiness_mismatch_count = int(
            latest_report.get("engine_write_readiness_mismatch_count") or 0
        )
        engine_write_readiness_mismatch_channels = (
            latest_report.get("engine_write_readiness_mismatch_channels")
            if isinstance(latest_report.get("engine_write_readiness_mismatch_channels"), list)
            else []
        )
        engine_write_mismatch_parts = [
            safe_label(item)
            for item in engine_write_readiness_mismatch_channels[:4]
            if safe_label(item)
        ]
        if engine_write_readiness_mismatch_count:
            if engine_write_mismatch_parts:
                parts.append(
                    "engine-write-mismatch "
                    f"{engine_write_readiness_mismatch_count}(" + "/".join(engine_write_mismatch_parts) + ")"
                )
            else:
                parts.append(f"engine-write-mismatch {engine_write_readiness_mismatch_count}")
        latest_skip = summary.get("latest_disclosure_skip") if isinstance(summary.get("latest_disclosure_skip"), dict) else {}
        skip_type = safe_label(latest_skip.get("event_type"))
        skip_audience = safe_label(latest_skip.get("audience"))
        if skip_type:
            parts.append(f"latest-skip {skip_type}:{skip_audience or 'unknown'}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_failure_strategy_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "retry 0, skipped 0, abandoned 0"
        retry = int(summary.get("retry_scheduled_count") or 0)
        skipped = int(summary.get("dependency_skipped_count") or 0)
        abandoned = int(summary.get("abandoned_late_result_count") or 0)
        handler_failed = int(summary.get("handler_failed_count") or 0)
        invalid_result = int(summary.get("invalid_result_count") or 0)
        invalid_patch = int(summary.get("invalid_state_patch_count") or 0)
        state_conflict = int(summary.get("state_patch_conflict_count") or 0)
        stopped = int(summary.get("stopped_by_runtime_command_count") or 0)
        parts = [
            f"retry {retry}",
            f"skipped {skipped}",
            f"abandoned {abandoned}",
        ]
        if handler_failed:
            parts.append(f"handler-failed {handler_failed}")
        if invalid_result:
            parts.append(f"invalid-result {invalid_result}")
        if invalid_patch:
            parts.append(f"invalid-patch {invalid_patch}")
        if state_conflict:
            parts.append(f"state-conflict {state_conflict}")
        if stopped:
            parts.append(f"stopped {stopped}")
        latest = summary.get("latest_strategy_event") if isinstance(summary.get("latest_strategy_event"), dict) else {}
        strategy = str(latest.get("strategy") or "").strip().replace("_", "-")
        status = str(latest.get("status") or "").strip().replace("_", "-")
        if strategy:
            parts.append(f"latest {strategy}:{status or 'unknown'}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_layout_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "requests 0, confirmations 0, applied 0"
        request_count = int(summary.get("request_count") or 0)
        request_failed = int(summary.get("request_failed_count") or 0)
        confirmation_count = int(summary.get("confirmation_count") or 0)
        confirmation_failed = int(summary.get("confirmation_failed_count") or 0)
        applied = int(summary.get("applied_count") or 0)
        skipped = int(summary.get("skipped_count") or 0)
        transform_success = int(summary.get("transform_success_count") or 0)
        transform_failed = int(summary.get("transform_failed_count") or 0)
        ground_snapped = int(summary.get("ground_snapped_count") or 0)
        overlap_resolved = int(summary.get("overlap_resolved_count") or 0)
        delta_count = int(summary.get("delta_count") or 0)
        parts = [
            f"requests {request_count}/{request_failed}",
            f"confirmations {confirmation_count}/{confirmation_failed}",
            f"applied {applied}",
            f"transforms {transform_success}/{transform_failed}",
        ]
        if skipped:
            parts.append(f"skipped {skipped}")
        if ground_snapped:
            parts.append(f"ground {ground_snapped}")
        if overlap_resolved:
            parts.append(f"overlap {overlap_resolved}")
        if delta_count:
            parts.append(f"deltas {delta_count}")
        latest_status = str(summary.get("latest_graph_status") or "").strip().replace("_", "-")
        if latest_status:
            parts.append(f"latest {latest_status}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_vlm_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "checkpoints 0, advisory 0"
        checkpoint_count = int(summary.get("checkpoint_count") or 0)
        advisory_count = int(summary.get("advisory_count") or 0)
        parts = [f"checkpoints {checkpoint_count}", f"advisory {advisory_count}"]
        status_counts = summary.get("status_counts") if isinstance(summary.get("status_counts"), dict) else {}
        status_text = ",".join(
            f"{str(key).strip().replace('_', '-')}:{int(value or 0)}"
            for key, value in sorted(status_counts.items())[:4]
            if str(key).strip() and int(value or 0) > 0
        )
        if status_text:
            parts.append(f"status {status_text}")
        checkpoint_counts = (
            summary.get("checkpoint_counts") if isinstance(summary.get("checkpoint_counts"), dict) else {}
        )
        checkpoint_text = ",".join(
            f"{str(key).strip().replace('_', '-')}:{int(value or 0)}"
            for key, value in sorted(checkpoint_counts.items())[:4]
            if str(key).strip() and int(value or 0) > 0
        )
        if checkpoint_text:
            parts.append(f"types {checkpoint_text}")
        latest = summary.get("latest_checkpoints") if isinstance(summary.get("latest_checkpoints"), list) else []
        latest_item = latest[-1] if latest and isinstance(latest[-1], dict) else {}
        checkpoint_type = str(latest_item.get("checkpoint_type") or "").strip().replace("_", "-")
        status = str(latest_item.get("status") or "").strip().replace("_", "-")
        if checkpoint_type:
            parts.append(f"latest {checkpoint_type}:{status or 'unknown'}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_review_advisory_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "proposals 0, confirmations 0"
        proposals = int(summary.get("proposal_created_count") or 0)
        confirmations = int(summary.get("confirmation_count") or 0)
        pending = int(summary.get("pending_proposal_count") or 0)
        confirmed = int(summary.get("confirmed_proposal_count") or 0)
        rejected = int(summary.get("rejected_proposal_count") or 0)
        advisory_items = int(summary.get("advisory_item_count") or 0)
        parts = [
            f"proposals {proposals}",
            f"confirmations {confirmations}",
        ]
        status_parts: list[str] = []
        if pending:
            status_parts.append(f"pending:{pending}")
        if confirmed:
            status_parts.append(f"confirmed:{confirmed}")
        if rejected:
            status_parts.append(f"rejected:{rejected}")
        if status_parts:
            parts.append("status " + ",".join(status_parts))
        if advisory_items:
            parts.append(f"items {advisory_items}")
        latest_decision = str(summary.get("latest_decision") or "").strip().replace("_", "-")
        if latest_decision:
            parts.append(f"latest {latest_decision}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_final_adjustment_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "confirmations 0"
        confirmations = int(summary.get("confirmation_count") or 0)
        failed = int(summary.get("confirmation_failed_count") or 0)
        skipped = int(summary.get("confirmation_skipped_count") or 0)
        parts = [f"confirmations {confirmations}"]
        if failed:
            parts.append(f"failed {failed}")
        if skipped:
            parts.append(f"skipped {skipped}")
        decision_counts = summary.get("decision_counts") if isinstance(summary.get("decision_counts"), dict) else {}
        decision_text = ",".join(
            f"{str(key).strip().replace('_', '-')}:{int(value or 0)}"
            for key, value in sorted(decision_counts.items())[:4]
            if str(key).strip() and int(value or 0) > 0
        )
        if decision_text:
            parts.append(f"decisions {decision_text}")
        latest = summary.get("latest_confirmation") if isinstance(summary.get("latest_confirmation"), dict) else {}
        latest_decision = str(latest.get("decision") or "").strip().replace("_", "-")
        latest_proposal = str(latest.get("proposal_id") or "").strip()
        conflict_count = int(latest.get("conflict_item_count") or 0)
        if latest_decision:
            latest_text = f"latest {latest_decision}"
            if latest_proposal:
                latest_text += f" {latest_proposal[:48]}"
            if conflict_count:
                latest_text += f" conflicts {conflict_count}"
            parts.append(latest_text)
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_environment_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "ready 0, import 0"
        ready = int(summary.get("ready_event_count") or 0)
        failed = int(summary.get("failed_event_count") or 0)
        imported = int(summary.get("import_event_count") or 0)
        import_failed = int(summary.get("import_failed_event_count") or 0)
        parts = [
            f"ready {ready}/{failed}",
            f"import {imported}/{import_failed}",
        ]
        event_counts = summary.get("event_type_counts") if isinstance(summary.get("event_type_counts"), dict) else {}
        event_text = ",".join(
            f"{str(key).strip().replace('_', '-')}:{int(value or 0)}"
            for key, value in sorted(event_counts.items())[:4]
            if str(key).strip() and int(value or 0) > 0
        )
        if event_text:
            parts.append(f"types {event_text}")
        latest = str(summary.get("latest_event_type") or "").strip().replace("_", "-")
        if latest:
            parts.append(f"latest {latest}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_resource_readiness_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "queries 0, published 0, events 0"
        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in ("prompt", "provider", "url", "raw", "token", "api-key", "path", "session", "job"):
                text = re.sub(marker, "resource", text, flags=re.IGNORECASE)
            return text[:60]

        queries = int(summary.get("status_query_count") or 0)
        published = int(summary.get("published_count") or 0)
        publish_failed = int(summary.get("publish_failed_count") or 0)
        readiness_events = int(summary.get("readiness_event_count") or 0)
        parts = [
            f"queries {queries}",
            f"published {published}/{publish_failed}",
            f"events {readiness_events}",
        ]
        publish_requested = int(summary.get("publish_requested_total") or 0)
        publish_enabled = int(summary.get("publish_enabled_total") or 0)
        publish_unavailable = int(summary.get("publish_unavailable_total") or 0)
        if publish_requested or publish_enabled or publish_unavailable:
            parts.append(
                f"publish-ready requested/enabled/unavailable {publish_requested}/{publish_enabled}/{publish_unavailable}"
            )
        publish_status_counts = (
            summary.get("publish_status_counts")
            if isinstance(summary.get("publish_status_counts"), dict)
            else {}
        )
        publish_status_text = ",".join(
            f"{safe_label(key)}:{int(value or 0)}"
            for key, value in sorted(publish_status_counts.items())[:4]
            if safe_label(key) and int(value or 0) > 0
        )
        if publish_status_text:
            parts.append(f"publish-status {publish_status_text}")
        requested_total = int(summary.get("status_query_requested_total") or 0)
        enabled_total = int(summary.get("status_query_enabled_total") or 0)
        unavailable_total = int(summary.get("status_query_unavailable_total") or 0)
        if requested_total or enabled_total or unavailable_total:
            parts.append(f"query-ready requested/enabled/unavailable {requested_total}/{enabled_total}/{unavailable_total}")
        query_status_counts = (
            summary.get("status_query_status_counts")
            if isinstance(summary.get("status_query_status_counts"), dict)
            else {}
        )
        query_status_text = ",".join(
            f"{safe_label(key)}:{int(value or 0)}"
            for key, value in sorted(query_status_counts.items())[:4]
            if safe_label(key) and int(value or 0) > 0
        )
        if query_status_text:
            parts.append(f"query-status {query_status_text}")
        status_counts = summary.get("status_counts") if isinstance(summary.get("status_counts"), dict) else {}
        status_text = ",".join(
            f"{safe_label(key)}:{int(value or 0)}"
            for key, value in sorted(status_counts.items())[:4]
            if safe_label(key) and int(value or 0) > 0
        )
        if status_text:
            parts.append(f"status {status_text}")
        latest = (
            summary.get("latest_readiness_event")
            if isinstance(summary.get("latest_readiness_event"), dict)
            else {}
        )
        latest_status = safe_label(latest.get("status"))
        if latest_status:
            parts.append(f"latest {latest_status}")
        return ", ".join(parts)

    def _format_agent_runtime_sync_report(self, summary: Any) -> str:
        if not isinstance(summary, dict):
            return "events 0, actors 0, assets 0"
        event_count = int(summary.get("event_count") or 0)
        actor_count = int(summary.get("actor_event_count") or 0)
        asset_count = int(summary.get("asset_event_count") or 0)
        latest_actors = summary.get("latest_actors")
        actor_preview = self._format_agent_runtime_sync_actor_rows(latest_actors if isinstance(latest_actors, list) else [])
        latest_assets = summary.get("latest_assets")
        asset_preview = self._format_agent_runtime_sync_asset_rows(latest_assets if isinstance(latest_assets, list) else [])
        parts = [f"events {event_count}", f"actors {actor_count}", f"assets {asset_count}"]
        if actor_preview != "none":
            parts.append(f"latest actors {actor_preview}")
        if asset_preview != "none":
            parts.append(f"latest assets {asset_preview}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_resource_flow_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "batches 0"
        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in ("prompt", "provider", "url", "raw", "token", "api-key", "path", "session", "job"):
                text = re.sub(marker, "resource", text, flags=re.IGNORECASE)
            return text[:60]

        batch_count = int(summary.get("batch_count") or 0)
        completed_count = int(summary.get("completed_count") or 0)
        partial_count = int(summary.get("partial_count") or 0)
        failed_count = int(summary.get("failed_count") or 0)
        waiting_count = int(summary.get("waiting_count") or 0)
        parts = [
            f"batches {batch_count}",
            f"completed {completed_count}",
            f"partial {partial_count}",
            f"failed {failed_count}",
            f"waiting {waiting_count}",
        ]
        latest = summary.get("latest_batch") if isinstance(summary.get("latest_batch"), dict) else {}
        latest_status = str(latest.get("status") or "").strip()
        latest_index = int(latest.get("batch_index") or 0)
        latest_total = int(latest.get("total_batches") or 0)
        requested_count = int(latest.get("requested_count") or 0)
        image_ready_count = int(latest.get("image_ready_count") or 0)
        model_ready_count = int(latest.get("model_ready_count") or 0)
        import_ready_count = int(latest.get("import_ready_count") or 0)
        import_failure_code_counts = (
            latest.get("import_failure_code_counts")
            if isinstance(latest.get("import_failure_code_counts"), dict)
            else {}
        )
        review_status = str(latest.get("review_status") or "").strip()
        if latest_status or latest_index or requested_count:
            batch_label = (
                f"{latest_index}/{latest_total}"
                if latest_index and latest_total
                else str(latest_index or "?")
            )
            parts.append(
                "latest "
                f"{batch_label}:{latest_status or 'unknown'} "
                f"img/model/import {image_ready_count}/{model_ready_count}/{import_ready_count}"
                f" of {requested_count}"
            )
        if review_status:
            parts.append(f"review {review_status.replace('_', '-')[:40]}")
        import_failure_codes = ",".join(
            f"{safe_label(code)}:{int(count or 0)}"
            for code, count in sorted(import_failure_code_counts.items())[:4]
            if safe_label(code) and int(count or 0) > 0
        )
        if import_failure_codes:
            parts.append(f"import-failures {import_failure_codes}")
        needs_attention = [
            str(item).strip().replace("_", "-")[:40]
            for item in list(summary.get("needs_attention") or [])[:4]
            if str(item).strip()
        ]
        if needs_attention:
            parts.append("needs " + ",".join(needs_attention))
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_scene_snapshot_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "snapshots 0, observed 0"
        snapshot_count = int(summary.get("scoped_snapshot_count") or summary.get("snapshot_count") or 0)
        observed_count = int(summary.get("observed_actor_count") or 0)
        observed_total = int(summary.get("observed_actor_total_count") or observed_count or 0)
        latest_source = str(summary.get("latest_source") or "").strip().replace("_", "-")[:40]
        parts = [
            f"snapshots {snapshot_count}",
            f"observed {observed_count}/{observed_total}",
        ]
        if latest_source:
            parts.append(f"source {latest_source}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_resource_stage_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "events 0"
        by_phase = summary.get("by_phase") if isinstance(summary.get("by_phase"), dict) else {}
        parts = [f"events {int(summary.get('event_count') or 0)}"]
        ordered_phases = ["image", "model", "import", "review"]
        extra_phases = [
            str(phase)
            for phase in by_phase.keys()
            if str(phase) not in set(ordered_phases)
        ]
        for phase in ordered_phases + sorted(extra_phases):
            row = by_phase.get(phase) if isinstance(by_phase.get(phase), dict) else {}
            if not row:
                if phase in {"image", "model"}:
                    parts.append(f"{phase} 0/0 failed 0")
                continue
            parts.append(
                f"{phase} {int(row.get('item_count') or 0)}/"
                f"{int(row.get('requested_count') or 0)} failed {int(row.get('failed_count') or 0)}"
            )
        latest = summary.get("latest_events") if isinstance(summary.get("latest_events"), list) else []
        latest_row = latest[-1] if latest and isinstance(latest[-1], dict) else {}
        latest_phase = str(latest_row.get("phase") or "").strip()
        latest_status = str(latest_row.get("status") or "").strip().replace("_", "-")
        if latest_phase or latest_status:
            parts.append(f"latest {latest_phase or 'resource'}:{latest_status or 'unknown'}")
        needs_attention = [
            str(item).strip().replace("_", "-")[:40]
            for item in list(summary.get("needs_attention") or [])[:4]
            if str(item).strip()
        ]
        if needs_attention:
            parts.append("needs " + ",".join(needs_attention))
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_report_health_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "unknown"

        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in ("prompt", "provider", "url", "raw", "token", "api-key", "path", "session", "job"):
                text = re.sub(marker, "resource", text, flags=re.IGNORECASE)
            return text[:60]

        status = safe_label(summary.get("status")) or "unknown"
        attention = "yes" if bool(summary.get("attention_required")) else "no"
        batch_failed = int(summary.get("batch_failed_count") or 0)
        batch_partial = int(summary.get("batch_partial_count") or 0)
        batch_waiting = int(summary.get("batch_waiting_count") or 0)
        import_failed = int(summary.get("import_failed_count") or 0)
        resource_failed = int(summary.get("resource_phase_failed_count") or 0)
        resource_partial = int(summary.get("resource_phase_partial_count") or 0)
        resource_waiting = int(summary.get("resource_phase_waiting_count") or 0)
        asset_failed = int(summary.get("asset_failed_count") or 0)
        asset_incomplete = int(summary.get("asset_incomplete_count") or 0)
        sync_health = safe_label(summary.get("sync_health_status")) or "unknown"
        import_failure_code_counts = (
            summary.get("import_failure_code_counts")
            if isinstance(summary.get("import_failure_code_counts"), dict)
            else {}
        )
        import_failure_codes = ", ".join(
            safe_label(code)
            for code, count in sorted(import_failure_code_counts.items())
            if int(count or 0) > 0 and safe_label(code)
        ) or "none"
        sync_failure_code_counts = (
            summary.get("sync_failure_code_counts")
            if isinstance(summary.get("sync_failure_code_counts"), dict)
            else {}
        )
        sync_failure_codes = ", ".join(
            safe_label(code)
            for code, count in sorted(sync_failure_code_counts.items())
            if int(count or 0) > 0 and safe_label(code)
        ) or "none"
        latest_sync_failure_code = safe_label(summary.get("latest_sync_failure_code"))
        engine_write_readiness_mismatch_count = int(
            summary.get("engine_write_readiness_mismatch_count") or 0
        )
        raw_engine_write_readiness_mismatch_channels = (
            summary.get("engine_write_readiness_mismatch_channels")
            if isinstance(summary.get("engine_write_readiness_mismatch_channels"), list)
            else []
        )
        engine_write_readiness_mismatch_channels = "/".join(
            safe_label(item)
            for item in raw_engine_write_readiness_mismatch_channels[:4]
            if safe_label(item)
        )
        engine_write_runtime_state_only_count = int(
            summary.get("engine_write_runtime_state_only_count") or 0
        )
        raw_engine_write_runtime_state_only_channels = (
            summary.get("engine_write_runtime_state_only_channels")
            if isinstance(summary.get("engine_write_runtime_state_only_channels"), list)
            else []
        )
        engine_write_runtime_state_only_channels = "/".join(
            safe_label(item)
            for item in raw_engine_write_runtime_state_only_channels[:4]
            if safe_label(item)
        )
        worker_drain_failed = int(summary.get("worker_drain_failed_count") or 0)
        worker_drain_exception = int(summary.get("worker_drain_exception_count") or 0)
        worker_drain_status_failed = int(summary.get("worker_drain_status_failed_count") or 0)
        worker_drain_plan_resolve_failed = int(
            summary.get("worker_drain_plan_resolve_failed_count") or 0
        )
        raw_reasons = summary.get("reasons") if isinstance(summary.get("reasons"), list) else []
        reasons = ", ".join(
            safe_label(reason)
            for reason in raw_reasons[:5]
            if safe_label(reason)
        ) or "none"
        parts = [
            status,
            f"attention {attention}",
            f"batch failed/partial/waiting {batch_failed}/{batch_partial}/{batch_waiting}",
            f"import failed {import_failed}",
            f"resource phase failed/partial/waiting {resource_failed}/{resource_partial}/{resource_waiting}",
            f"asset failed/incomplete {asset_failed}/{asset_incomplete}",
            f"sync {sync_health}",
        ]
        if import_failure_codes != "none":
            parts.append(f"import failures {import_failure_codes}")
        if sync_failure_codes != "none":
            parts.append(f"sync failures {sync_failure_codes}")
        if latest_sync_failure_code:
            parts.append(f"latest sync failure {latest_sync_failure_code}")
        if engine_write_readiness_mismatch_count:
            if engine_write_readiness_mismatch_channels:
                parts.append(
                    f"engine-write mismatch {engine_write_readiness_mismatch_count}"
                    f"({engine_write_readiness_mismatch_channels})"
                )
            else:
                parts.append(f"engine-write mismatch {engine_write_readiness_mismatch_count}")
        if engine_write_runtime_state_only_count:
            if engine_write_runtime_state_only_channels:
                parts.append(
                    f"engine-write runtime-state-only {engine_write_runtime_state_only_count}"
                    f"({engine_write_runtime_state_only_channels})"
                )
            else:
                parts.append(f"engine-write runtime-state-only {engine_write_runtime_state_only_count}")
        if (
            worker_drain_failed
            or worker_drain_exception
            or worker_drain_status_failed
            or worker_drain_plan_resolve_failed
        ):
            parts.append(
                "worker-drain failed/status-failed/exception/plan-resolve "
                f"{worker_drain_failed}/{worker_drain_status_failed}/"
                f"{worker_drain_exception}/{worker_drain_plan_resolve_failed}"
            )
        if reasons != "none":
            parts.append(f"reasons {reasons}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_fact_source_boundary_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "runtime 0, external 0, external unavailable"
        runtime_count = int(summary.get("runtime_business_fact_count") or 0)
        external_count = int(summary.get("mirrored_external_fact_count") or 0)
        plan_count = int(summary.get("runtime_plan_fact_count") or 0)
        batch_count = int(summary.get("runtime_batch_fact_count") or 0)
        resource_count = int(summary.get("runtime_resource_event_count") or 0)
        import_count = int(summary.get("runtime_import_event_count") or 0)
        sync_count = int(summary.get("sync_event_count") or 0)
        engine_write_count = int(summary.get("engine_write_result_count") or 0)
        engine_write_boundary_count = int(summary.get("engine_write_boundary_fact_count") or 0)
        snapshot_count = int(summary.get("scene_snapshot_count") or 0)
        external_available = bool(summary.get("external_authoritative_available"))
        parts = [
            f"runtime {runtime_count}",
            f"external {external_count}",
            f"plan/batch {plan_count}/{batch_count}",
            f"resource/import {resource_count}/{import_count}",
            f"sync/write/snapshot {sync_count}/{engine_write_count}/{snapshot_count}",
            f"write-boundary {engine_write_boundary_count}",
        ]
        parts.append("external available" if external_available else "external unavailable")
        notes = [
            str(item).strip().replace("_", "-")[:48]
            for item in list(summary.get("boundary_notes") or [])[:3]
            if str(item).strip()
        ]
        if notes:
            parts.append("notes " + ",".join(notes))
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_closure_report(
        fact_source: Any,
        state_patch: Any,
        *,
        operation_count: Any = 0,
        operation_total_count: Any = 0,
    ) -> str:
        fact_data = fact_source if isinstance(fact_source, dict) else {}
        patch_data = state_patch if isinstance(state_patch, dict) else {}
        source = str(fact_data.get("runtime_state_source") or "unknown").strip() or "unknown"
        write_boundary = int(fact_data.get("engine_write_boundary_fact_count") or 0)
        try:
            operations = int(operation_count or 0)
        except (TypeError, ValueError):
            operations = 0
        try:
            operation_total = int(operation_total_count or 0)
        except (TypeError, ValueError):
            operation_total = 0
        return (
            f"state {source}, operation {operations}/{operation_total}, "
            f"patch applied/conflict/invalid "
            f"{int(patch_data.get('applied') or 0)}/"
            f"{int(patch_data.get('conflict') or 0)}/"
            f"{int(patch_data.get('invalid') or 0)}, "
            f"write-boundary {write_boundary}"
        )

    @staticmethod
    def _format_agent_runtime_import_stage_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "events 0, imported 0/0, failed 0"
        parts = [
            f"events {int(summary.get('event_count') or 0)}",
            f"imported {int(summary.get('imported_count') or 0)}/"
            f"{int(summary.get('requested_count') or 0)}",
            f"failed {int(summary.get('failed_count') or 0)}",
        ]
        latest = summary.get("latest_events") if isinstance(summary.get("latest_events"), list) else []
        latest_row = latest[-1] if latest and isinstance(latest[-1], dict) else {}
        latest_status = str(latest_row.get("status") or "").strip().replace("_", "-")
        if latest_status:
            parts.append(f"latest {latest_status}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_actor_import_boundary_report(
        import_summary: Any,
        scene_registry: Any,
        engine_write_boundary: Any,
    ) -> str:
        import_data = import_summary if isinstance(import_summary, dict) else {}
        registry_data = scene_registry if isinstance(scene_registry, dict) else {}
        boundary_data = engine_write_boundary if isinstance(engine_write_boundary, dict) else {}
        entity_type_counts = dict(registry_data.get("entity_type_counts") or {})
        requested = int(import_data.get("requested_count") or 0)
        imported = int(import_data.get("imported_count") or 0)
        failed = int(import_data.get("failed_count") or 0)
        actor_count = int(registry_data.get("actor_count") or entity_type_counts.get("actor") or 0)
        bridge_calls = int(boundary_data.get("bridge_call_count") or 0)
        bridge_success = int(boundary_data.get("bridge_success_count") or 0)
        bridge_failed = int(boundary_data.get("bridge_failed_count") or 0)
        status_counts = boundary_data.get("status_counts") if isinstance(boundary_data.get("status_counts"), dict) else {}
        runtime_state_only = int(status_counts.get("runtime_state_only") or 0)
        if bridge_calls > 0:
            native_state = f"bridge {bridge_success}/{bridge_calls}"
            if bridge_failed:
                native_state += f", failed {bridge_failed}"
        elif runtime_state_only > 0:
            native_state = f"RuntimeState-only {runtime_state_only}, native pending F5"
        else:
            native_state = "native not-observed"
        return (
            f"requested/imported/failed {requested}/{imported}/{failed}, "
            f"registered actor {actor_count}, {native_state}"
        )

    @staticmethod
    def _format_agent_runtime_tool_queue_health_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "queue 0, active 0, blocked 0, pressure 0%"
        queue_count = int(summary.get("queue_count") or 0)
        queued_count = int(summary.get("queued_count") or 0)
        running_count = int(summary.get("running_count") or 0)
        blocked_count = int(summary.get("blocked_count") or 0)
        terminal_count = int(summary.get("terminal_count") or 0)
        active_count = int(summary.get("active_count") or 0)
        queue_pressure = float(summary.get("queue_pressure") or 0.0)
        queue_pressure = max(0.0, min(1.0, queue_pressure))
        return (
            f"queue {queue_count}, active {active_count}, "
            f"queued/running {queued_count}/{running_count}, "
            f"blocked {blocked_count}, terminal {terminal_count}, "
            f"pressure {int(queue_pressure * 100)}%"
        )

    @staticmethod
    def _format_agent_runtime_batch_tooling_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "facts 0, created-batches 0, priorities 0, merged 0, absorbed 0"
        fact_count = int(summary.get("fact_count") or 0)
        created_batch_fact_count = int(summary.get("created_batch_fact_count") or 0)
        created_batch_count = int(summary.get("created_batch_count") or 0)
        prioritized_item_count = int(summary.get("prioritized_item_count") or 0)
        merged_intervention_fact_count = int(summary.get("merged_intervention_fact_count") or 0)
        merged_intervention_item_count = int(summary.get("merged_intervention_item_count") or 0)
        absorbed_intervention_count = int(summary.get("absorbed_intervention_count") or 0)
        latest_types = [
            str(item).strip().replace("_", "-")[:40]
            for item in list(summary.get("latest_fact_types") or [])[:5]
            if str(item).strip()
        ]
        parts = [
            f"facts {fact_count}",
            f"created-batches {created_batch_count}/{created_batch_fact_count}",
            f"priorities {prioritized_item_count}",
            f"merged {merged_intervention_item_count}/{merged_intervention_fact_count}",
            f"absorbed {absorbed_intervention_count}",
        ]
        if latest_types:
            parts.append("latest " + ",".join(latest_types))
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_batch_resource_lifecycle_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "events 0"
        resource_event_count = int(summary.get("resource_event_count") or 0)
        image_ready_count = int(summary.get("image_ready_count") or 0)
        image_failed_count = int(summary.get("image_failed_count") or 0)
        model_ready_count = int(summary.get("model_ready_count") or 0)
        model_failed_count = int(summary.get("model_failed_count") or 0)
        import_ready_count = int(summary.get("import_ready_count") or 0)
        import_failed_count = int(summary.get("import_failed_count") or 0)
        environment_ready_count = int(summary.get("environment_ready_count") or 0)
        environment_failed_count = int(summary.get("environment_failed_count") or 0)
        emit_failed_count = int(summary.get("emit_failed_count") or 0)
        parts = [
            f"events {resource_event_count}",
            f"image {image_ready_count}/{image_failed_count}",
            f"model {model_ready_count}/{model_failed_count}",
            f"import {import_ready_count}/{import_failed_count}",
            f"env {environment_ready_count}/{environment_failed_count}",
        ]
        if emit_failed_count:
            parts.append(f"emit-failed {emit_failed_count}")
        latest = (
            summary.get("latest_resource_event")
            if isinstance(summary.get("latest_resource_event"), dict)
            else {}
        )
        latest_stage = str(latest.get("stage") or "").strip().replace("_", "-")
        latest_status = "persisted" if bool(latest.get("persisted")) else "not-persisted"
        if latest_stage:
            parts.append(f"latest {latest_stage}:{latest_status}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_sync_health_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "unknown"
        status = str(summary.get("status") or "unknown").strip() or "unknown"
        needs_attention = [
            str(item).strip().replace("_", "-")
            for item in list(summary.get("needs_attention") or [])[:4]
            if str(item).strip()
        ]
        actor_create_count = int(summary.get("actor_create_count") or 0)
        actor_transform_count = int(summary.get("actor_transform_count") or 0)
        actor_delete_count = int(summary.get("actor_delete_count") or 0)
        active_actor_count = int(summary.get("latest_active_actor_count") or 0)
        peer_join_count = int(summary.get("peer_join_count") or 0)
        peer_leave_count = int(summary.get("peer_leave_count") or 0)
        room_close_count = int(summary.get("room_close_count") or 0)
        parts = [
            status,
            f"attention {len(needs_attention)}",
            f"actors create/transform/delete {actor_create_count}/{actor_transform_count}/{actor_delete_count}",
            f"active {active_actor_count}",
        ]
        if peer_join_count or peer_leave_count:
            parts.append(f"peers join/leave {peer_join_count}/{peer_leave_count}")
        if room_close_count:
            parts.append(f"room-close {room_close_count}")
        if needs_attention:
            parts.append("needs " + ",".join(needs_attention))
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_asset_transfer_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "none"
        asset_count = int(summary.get("asset_count") or 0)
        if asset_count <= 0:
            return "none"
        ready_count = int(summary.get("ready_count") or 0)
        failed_count = int(summary.get("failed_count") or 0)
        transferring_count = int(summary.get("transferring_count") or 0)
        completed_count = int(summary.get("completed_count") or 0)
        progress = int(summary.get("overall_progress") or 0)
        bytes_transferred = int(summary.get("bytes_transferred") or 0)
        total_bytes = int(summary.get("total_bytes") or 0)
        parts = [
            f"assets {asset_count}",
            f"ready {ready_count}",
            f"completed {completed_count}",
            f"transferring {transferring_count}",
            f"failed {failed_count}",
        ]
        if progress:
            parts.append(f"progress {max(0, min(100, progress))}%")
        if total_bytes > 0:
            parts.append(f"bytes {bytes_transferred}/{total_bytes}")
        latest_assets = summary.get("latest_assets")
        if isinstance(latest_assets, list) and latest_assets:
            latest = latest_assets[-1] if isinstance(latest_assets[-1], dict) else {}
            asset_id = str(latest.get("asset_id") or "").strip()
            status = str(latest.get("transfer_status") or "").strip()
            if asset_id or status:
                parts.append(f"latest {asset_id or 'asset'}:{status or 'unknown'}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_sync_replay_report(summary: Any) -> str:
        if not isinstance(summary, dict):
            return "recorded 0, failed 0"
        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in ("prompt", "provider", "url", "raw", "token", "api-key", "path", "session", "job"):
                text = re.sub(marker, "resource", text, flags=re.IGNORECASE)
            return text[:60]

        recorded_count = int(summary.get("recorded_count") or 0)
        failed_count = int(summary.get("failed_count") or 0)
        actor_transform_count = int(summary.get("actor_transform_count") or 0)
        actor_delete_count = int(summary.get("actor_delete_count") or 0)
        peer_join_count = int(summary.get("peer_join_count") or 0)
        peer_leave_count = int(summary.get("peer_leave_count") or 0)
        transfer_failed_count = int(summary.get("transfer_failed_count") or 0)
        transfer_progress_count = int(summary.get("transfer_progress_count") or 0)
        latest_transfer_progress = int(summary.get("latest_transfer_progress") or 0)
        latest_chunk_index = int(summary.get("latest_chunk_index") or 0)
        latest_chunk_count = int(summary.get("latest_chunk_count") or 0)
        latest_bytes_transferred = int(summary.get("latest_bytes_transferred") or 0)
        latest_total_bytes = int(summary.get("latest_total_bytes") or 0)
        latest_event_type = str(summary.get("latest_event_type") or "").strip().replace("_", "-")
        failure_code_counts = (
            summary.get("failure_code_counts")
            if isinstance(summary.get("failure_code_counts"), dict)
            else {}
        )
        failure_codes = ", ".join(
            f"{safe_label(code)}:{int(count or 0)}"
            for code, count in sorted(failure_code_counts.items())[:5]
            if int(count or 0) > 0 and safe_label(code)
        )
        latest_failure_code = safe_label(summary.get("latest_failure_code"))
        parts = [f"recorded {recorded_count}", f"failed {failed_count}"]
        if actor_transform_count:
            parts.append(f"actor-transform {actor_transform_count}")
        if actor_delete_count:
            parts.append(f"actor-delete {actor_delete_count}")
        if peer_join_count:
            parts.append(f"peer-join {peer_join_count}")
        if peer_leave_count:
            parts.append(f"peer-leave {peer_leave_count}")
        if transfer_failed_count:
            parts.append(f"transfer-failed {transfer_failed_count}")
        if transfer_progress_count:
            transfer_parts = [f"transfer-progress {transfer_progress_count}"]
            progress_bits: list[str] = []
            if latest_transfer_progress:
                progress_bits.append(f"{max(0, min(100, latest_transfer_progress))}%")
            if latest_chunk_index and latest_chunk_count:
                progress_bits.append(f"chunk {latest_chunk_index}/{latest_chunk_count}")
            byte_text = LANChatAgentWorker._format_runtime_transfer_bytes(
                latest_bytes_transferred,
                latest_total_bytes,
            )
            if byte_text:
                progress_bits.append(byte_text.strip())
            if progress_bits:
                transfer_parts.append("latest " + " ".join(progress_bits))
            parts.append(" ".join(transfer_parts))
        if latest_event_type:
            parts.append(f"latest {latest_event_type[:48]}")
        if failure_codes:
            parts.append(f"failure codes {failure_codes}")
        if latest_failure_code:
            parts.append(f"latest failure {latest_failure_code}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_asset_transfer_report(summary: Any) -> str:
        if not isinstance(summary, dict):
            return "events 0, started 0, progress 0, completed 0, failed 0"
        event_count = int(summary.get("asset_event_count") or 0)
        started_count = int(summary.get("asset_transfer_started_count") or 0)
        progress_count = int(summary.get("asset_transfer_progress_count") or 0)
        completed_count = int(summary.get("asset_transfer_completed_count") or 0)
        failed_count = int(summary.get("asset_transfer_failed_count") or 0)
        peer_ready_count = int(summary.get("peer_asset_ready_count") or 0)
        latest_progress = int(summary.get("latest_transfer_progress") or 0)
        latest_chunk_index = int(summary.get("latest_chunk_index") or 0)
        latest_chunk_count = int(summary.get("latest_chunk_count") or 0)
        latest_bytes_transferred = int(summary.get("latest_bytes_transferred") or 0)
        latest_total_bytes = int(summary.get("latest_total_bytes") or 0)
        latest_status = str(summary.get("latest_transfer_status") or "").strip().replace("_", "-")
        parts = [
            f"events {event_count}",
            f"started {started_count}",
            f"progress {progress_count}",
            f"completed {completed_count}",
            f"failed {failed_count}",
        ]
        if peer_ready_count:
            parts.append(f"peer-ready {peer_ready_count}")
        latest_bits: list[str] = []
        if latest_progress:
            latest_bits.append(f"{max(0, min(100, latest_progress))}%")
        if latest_chunk_index and latest_chunk_count:
            latest_bits.append(f"chunk {latest_chunk_index}/{latest_chunk_count}")
        byte_text = LANChatAgentWorker._format_runtime_transfer_bytes(
            latest_bytes_transferred,
            latest_total_bytes,
        )
        if byte_text:
            latest_bits.append(byte_text.strip())
        if latest_status:
            latest_bits.append(latest_status[:24])
        if latest_bits:
            parts.append("latest " + " ".join(latest_bits))
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_peer_sync_report(summary: Any) -> str:
        if not isinstance(summary, dict):
            return "events 0, join 0, leave 0, room-close 0, reconcile 0/0, state 0/0"
        event_count = int(summary.get("peer_event_count") or 0)
        join_count = int(summary.get("peer_join_count") or 0)
        leave_count = int(summary.get("peer_leave_count") or 0)
        room_close_count = int(summary.get("room_close_count") or 0)
        sync_reconcile_count = int(summary.get("sync_reconcile_count") or 0)
        sync_reconcile_failed_count = int(summary.get("sync_reconcile_failed_count") or 0)
        state_reconcile_count = int(summary.get("state_reconcile_count") or 0)
        state_reconcile_failed_count = int(summary.get("state_reconcile_failed_count") or 0)
        latest_peer_event_type = str(summary.get("latest_peer_event_type") or "").strip().replace("_", "-")
        latest_room_status = str(summary.get("latest_room_status") or "").strip().replace("_", "-")
        latest_reconcile_event = (
            summary.get("latest_reconcile_event")
            if isinstance(summary.get("latest_reconcile_event"), dict)
            else {}
        )
        latest_reconcile_status = str(
            latest_reconcile_event.get("status") if isinstance(latest_reconcile_event, dict) else ""
        ).strip().replace("_", "-")
        parts = [
            f"events {event_count}",
            f"join {join_count}",
            f"leave {leave_count}",
            f"room-close {room_close_count}",
            f"reconcile {sync_reconcile_count}/{sync_reconcile_failed_count}",
            f"state {state_reconcile_count}/{state_reconcile_failed_count}",
        ]
        if latest_peer_event_type:
            parts.append(f"latest-peer {latest_peer_event_type[:32]}")
        if latest_room_status:
            parts.append(f"room {latest_room_status[:24]}")
        if latest_reconcile_status:
            parts.append(f"latest-reconcile {latest_reconcile_status[:24]}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_replay_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "entries 0"
        entry_count = int(summary.get("entry_count") or 0)
        event_counts = summary.get("event_counts") if isinstance(summary.get("event_counts"), dict) else {}
        latest_events = summary.get("latest_events") if isinstance(summary.get("latest_events"), list) else []
        environment_replay = (
            summary.get("environment_component_replay_summary")
            if isinstance(summary.get("environment_component_replay_summary"), dict)
            else {}
        )
        runtime_event_replay = (
            summary.get("runtime_event_replay_summary")
            if isinstance(summary.get("runtime_event_replay_summary"), dict)
            else {}
        )
        worker_drain_replay = (
            summary.get("worker_drain_replay_summary")
            if isinstance(summary.get("worker_drain_replay_summary"), dict)
            else {}
        )
        engine_write_boundary = (
            summary.get("engine_write_boundary_summary")
            if isinstance(summary.get("engine_write_boundary_summary"), dict)
            else {}
        )

        def safe_event(value: Any) -> str:
            event = str(value or "").strip()
            if not event:
                return ""
            for marker in ("provider", "prompt", "url", "raw"):
                event = re.sub(marker, "runtime", event, flags=re.IGNORECASE)
            return event.replace("_", "-")[:80]

        priority_events = [
            "scene_plan_created",
            "scene_plan_confirmed",
            "batch_plan_created",
            "tool_graph_queued",
            "tool_graph_completed",
            "user_report_generated",
        ]
        count_parts: list[str] = []
        for key in priority_events:
            value = int(event_counts.get(key) or 0)
            if value > 0:
                count_parts.append(f"{safe_event(key)}:{value}")
        if not count_parts:
            for key, value in sorted(event_counts.items())[:4]:
                if int(value or 0) > 0:
                    count_parts.append(f"{safe_event(key)}:{int(value or 0)}")
        recent: list[str] = []
        for item in latest_events[-3:]:
            if isinstance(item, dict):
                event = safe_event(item.get("event"))
            else:
                event = safe_event(item)
            if event:
                recent.append(event)
        parts = [f"entries {entry_count}"]
        if count_parts:
            parts.append("events " + ",".join(count_parts[:4]))
        env_import_count = int(environment_replay.get("import_event_count") or 0)
        env_import_failed = int(environment_replay.get("import_failed_event_count") or 0)
        if env_import_count or env_import_failed:
            env_bits = []
            if env_import_count:
                env_bits.append(f"env-import:{env_import_count}")
            if env_import_failed:
                env_bits.append(f"env-import-failed:{env_import_failed}")
            parts.append("environment " + ",".join(env_bits))
        if int(runtime_event_replay.get("disclosure_skipped_count") or 0) > 0:
            parts.append(
                "runtime-events "
                + LANChatAgentWorker._format_agent_runtime_replay_runtime_event_report(runtime_event_replay)
            )
        drain_failed = int(worker_drain_replay.get("failed_count") or event_counts.get("runtime_worker_drain_failed") or 0)
        drain_exception = int(worker_drain_replay.get("exception_count") or event_counts.get("runtime_worker_drain_exception") or 0)
        drain_status_failed = int(
            worker_drain_replay.get("status_failed_count")
            or event_counts.get("runtime_worker_drain_status_failed")
            or 0
        )
        if drain_failed or drain_exception or drain_status_failed:
            parts.append(
                "worker-drain "
                + LANChatAgentWorker._format_agent_runtime_worker_drain_replay_report(worker_drain_replay or {
                    "failed_count": drain_failed,
                    "exception_count": drain_exception,
                    "status_failed_count": drain_status_failed,
                })
            )
        if int(engine_write_boundary.get("boundary_fact_count") or 0) > 0:
            parts.append(
                "engine_write_boundary "
                + LANChatAgentWorker._format_agent_runtime_engine_write_boundary_report(engine_write_boundary)
            )
        if recent:
            parts.append("recent " + ",".join(recent[:3]))
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_worker_drain_replay_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "requested 0, drained 0, failed 0, exception 0"
        requested = int(summary.get("requested_count") or 0)
        drained_messages = int(summary.get("message_drained_count") or 0)
        failed = int(summary.get("failed_count") or 0)
        exception = int(summary.get("exception_count") or 0)
        status_failed = int(summary.get("status_failed_count") or 0)
        plan_resolve_failed = int(summary.get("plan_resolve_failed_count") or 0)
        drained_graph_total = int(summary.get("drained_graph_total") or 0)
        parts = [
            f"requested {requested}",
            f"drained {drained_messages}/{drained_graph_total}",
            f"failed {failed}",
            f"exception {exception}",
        ]
        if status_failed:
            parts.append(f"status-failed {status_failed}")
        if plan_resolve_failed:
            parts.append(f"plan-resolve-failed {plan_resolve_failed}")
        latest = summary.get("latest_drain_event") if isinstance(summary.get("latest_drain_event"), dict) else {}
        latest_event = str(latest.get("event") or "").strip().replace("_", "-")
        if latest_event:
            parts.append(f"latest {latest_event[:48]}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_context_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "0 context(s)"
        context_count = int(summary.get("context_count") or 0)
        context_type_counts = (
            summary.get("context_type_counts")
            if isinstance(summary.get("context_type_counts"), dict)
            else {}
        )
        speaker_type_counts = (
            summary.get("speaker_type_counts")
            if isinstance(summary.get("speaker_type_counts"), dict)
            else {}
        )
        latest_context = summary.get("latest_context") if isinstance(summary.get("latest_context"), list) else []

        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in ("provider", "prompt", "url", "raw", "metadata", "message-id"):
                text = re.sub(marker, "runtime", text, flags=re.IGNORECASE)
            return text[:48]

        type_rows = [
            f"{safe_label(key)}:{int(value or 0)}"
            for key, value in sorted(context_type_counts.items())
            if int(value or 0) > 0
        ]
        speaker_rows = [
            f"{safe_label(key)}:{int(value or 0)}"
            for key, value in sorted(speaker_type_counts.items())
            if int(value or 0) > 0
        ]
        latest_preview = ""
        if latest_context:
            latest = latest_context[-1] if isinstance(latest_context[-1], dict) else {}
            latest_type = safe_label(latest.get("context_type"))
            latest_speaker = safe_label(latest.get("speaker_type"))
            latest_message = safe_label(latest.get("message") or latest.get("text_preview"))
            if latest_message:
                latest_preview = f"{latest_type or 'context'}/{latest_speaker or 'speaker'}:{latest_message}"
            elif latest_type or latest_speaker:
                latest_preview = f"{latest_type or 'context'}/{latest_speaker or 'speaker'}"
        parts = [f"{context_count} context(s)"]
        if type_rows:
            parts.append("types " + ",".join(type_rows[:4]))
        if speaker_rows:
            parts.append("speakers " + ",".join(speaker_rows[:4]))
        if latest_preview:
            parts.append("latest " + latest_preview)
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_engine_write_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "import 0, transform 0, env-import 0, actor-delete 0"
        import_count = int(summary.get("import_result_count") or 0)
        transform_count = int(summary.get("transform_result_count") or 0)
        environment_import_count = int(summary.get("environment_import_result_count") or 0)
        delete_count = int(summary.get("delete_result_count") or 0)
        import_status_counts = (
            summary.get("import_status_counts")
            if isinstance(summary.get("import_status_counts"), dict)
            else {}
        )
        transform_status_counts = (
            summary.get("transform_status_counts")
            if isinstance(summary.get("transform_status_counts"), dict)
            else {}
        )
        environment_import_status_counts = (
            summary.get("environment_import_status_counts")
            if isinstance(summary.get("environment_import_status_counts"), dict)
            else {}
        )
        delete_status_counts = (
            summary.get("delete_status_counts")
            if isinstance(summary.get("delete_status_counts"), dict)
            else {}
        )
        status_export_count = int(summary.get("status_export_count") or 0)
        latest_status_export = (
            summary.get("latest_status_export")
            if isinstance(summary.get("latest_status_export"), dict)
            else {}
        )

        def status_text(counts: Any) -> str:
            if not isinstance(counts, dict) or not counts:
                return ""
            rows = [
                f"{str(key).replace('_', '-')}:{int(value or 0)}"
                for key, value in sorted(counts.items())
                if int(value or 0) > 0
            ]
            return "(" + ",".join(rows[:4]) + ")" if rows else ""

        parts = [
            f"import {import_count}{status_text(import_status_counts)}",
            f"transform {transform_count}{status_text(transform_status_counts)}",
            f"env-import {environment_import_count}{status_text(environment_import_status_counts)}",
            f"actor-delete {delete_count}{status_text(delete_status_counts)}",
        ]
        mismatch_count = int(summary.get("readiness_mismatch_count") or 0)
        mismatch_channels = summary.get("readiness_mismatch_channels")
        if mismatch_count and isinstance(mismatch_channels, list):
            names = [
                str(item or "").replace("_", "-")[:32]
                for item in mismatch_channels[:4]
                if str(item or "").strip()
                and "provider" not in str(item).lower()
                and "secret" not in str(item).lower()
            ]
            if names:
                parts.append(f"readiness-mismatch {mismatch_count}(" + "/".join(names) + ")")
        if status_export_count > 0:
            export_bits = ["recorded" if latest_status_export.get("recorded") else "not-recorded"]
            bridge_failed = int(latest_status_export.get("engine_write_bridge_failed_count") or 0)
            if bridge_failed:
                export_bits.append(f"bridge-failed:{bridge_failed}")
            readiness_bits = []
            for label, key in (
                ("native", "engine_write_readiness_native_enabled_count"),
                ("runtime-state", "engine_write_readiness_runtime_state_only_count"),
                ("fallback", "engine_write_readiness_fallback_count"),
                ("disabled", "engine_write_readiness_disabled_count"),
                ("unavailable", "engine_write_readiness_unavailable_count"),
            ):
                value = int(latest_status_export.get(key) or 0)
                if value:
                    readiness_bits.append(f"{label}:{value}")
            if readiness_bits:
                export_bits.append("readiness " + ",".join(readiness_bits[:5]))
            channel_bits = []
            for label, key in (
                ("native", "engine_write_readiness_native_enabled_channels"),
                ("runtime-state", "engine_write_readiness_runtime_state_only_channels"),
                ("fallback", "engine_write_readiness_fallback_channels"),
                ("disabled", "engine_write_readiness_disabled_channels"),
                ("unavailable", "engine_write_readiness_unavailable_channels"),
            ):
                values = latest_status_export.get(key)
                if not isinstance(values, list) or not values:
                    continue
                names = [
                    str(item or "").replace("_", "-")[:32]
                    for item in values[:3]
                    if str(item or "").strip()
                    and "provider" not in str(item).lower()
                    and "secret" not in str(item).lower()
                ]
                if names:
                    channel_bits.append(f"{label} " + "/".join(names))
            if channel_bits:
                export_bits.append("channels " + "; ".join(channel_bits[:5]))
            error_counts = latest_status_export.get("engine_write_bridge_error_code_counts")
            if isinstance(error_counts, dict) and error_counts:
                safe_errors = [
                    f"{str(key).replace('_', '-')}:{int(value or 0)}"
                    for key, value in sorted(error_counts.items())
                    if int(value or 0) > 0
                    and "provider" not in str(key).lower()
                    and "secret" not in str(key).lower()
                ]
                if safe_errors:
                    export_bits.append("errors " + ",".join(safe_errors[:3]))
            parts.append(f"status-export {status_export_count}(" + ", ".join(export_bits) + ")")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_engine_write_boundary_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "boundary 0, import/transform/delete 0/0/0"
        boundary_count = int(summary.get("boundary_fact_count") or 0)
        import_count = int(summary.get("import_boundary_count") or 0)
        transform_count = int(summary.get("transform_boundary_count") or 0)
        delete_count = int(summary.get("delete_boundary_count") or 0)

        def safe_label(value: Any) -> str:
            text = str(value or "").strip().lower()
            if not text:
                return ""
            text = re.sub(r"provider|prompt|raw|url|api[_-]?key|token", "runtime", text)
            text = re.sub(r"[^a-z0-9_.:-]+", "-", text)
            return text[:48].strip("-")

        def count_rows(value: Any) -> str:
            if not isinstance(value, dict) or not value:
                return "none"
            rows: list[str] = []
            for key, count in sorted(value.items()):
                label = safe_label(key)
                if not label:
                    continue
                try:
                    numeric_count = int(count or 0)
                except (TypeError, ValueError):
                    continue
                if numeric_count > 0:
                    rows.append(f"{label}:{numeric_count}")
            return ",".join(rows[:4]) if rows else "none"

        source_text = count_rows(summary.get("write_source_counts"))
        status_text = count_rows(summary.get("status_counts"))
        bridge_calls = int(summary.get("bridge_call_count") or 0)
        bridge_success = int(summary.get("bridge_success_count") or 0)
        bridge_failed = int(summary.get("bridge_failed_count") or 0)
        bridge_error_text = count_rows(summary.get("bridge_error_code_counts"))
        raw_status_counts = summary.get("status_counts") if isinstance(summary.get("status_counts"), dict) else {}
        runtime_state_only_count = int(raw_status_counts.get("runtime_state_only") or 0)
        if bridge_calls > 0:
            native_text = "native verified" if bridge_success > 0 and bridge_failed <= 0 else "native needs-attention"
        elif runtime_state_only_count > 0:
            native_text = "native pending F5"
        else:
            native_text = "native not-observed"
        return (
            f"boundary {boundary_count}, "
            f"import/transform/delete {import_count}/{transform_count}/{delete_count}, "
            f"sources {source_text}, statuses {status_text}, "
            f"bridge {bridge_calls}/{bridge_success}/{bridge_failed}, errors {bridge_error_text}, "
            f"{native_text}"
        )

    @staticmethod
    def _format_agent_runtime_resource_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "default runtime adapters"
        parts: list[str] = []
        def safe_value(value: Any) -> str:
            text = str(value or "").strip()[:80]
            return text.replace("provider", "adapter").replace("_", "-")
        for key in ("scene_snapshot", "image_resource", "model_resource", "actor_import", "environment_component", "environment_import", "review", "layout_transform"):
            value = summary.get(key)
            if not isinstance(value, dict):
                continue
            status = safe_value(value.get("status") or value.get("mode") or "")
            reason = safe_value(value.get("reason") or "")
            if not status:
                continue
            label = key.replace("_", "-")
            if reason and status != "enabled":
                parts.append(f"{label}:{status}({reason[:40]})")
            else:
                parts.append(f"{label}:{status}")
        return "、".join(parts[:7]) if parts else "default runtime adapters"

    @staticmethod
    def _format_agent_runtime_resource_readiness_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "channels 0, enabled 0, unavailable 0"
        channel_count = int(summary.get("channel_count") or 0)
        requested_count = int(summary.get("requested_count") or 0)
        enabled_count = int(summary.get("enabled_count") or 0)
        unavailable_count = int(summary.get("unavailable_count") or 0)
        unavailable = summary.get("unavailable_channels")
        unavailable_text = ""
        if isinstance(unavailable, list) and unavailable:
            names = [
                str(item or "").replace("_", "-")[:32]
                for item in unavailable[:3]
                if str(item or "").strip()
            ]
            if names:
                unavailable_text = ", unavailable " + "、".join(names)
        return (
            f"channels {channel_count}, requested {requested_count}, "
            f"enabled {enabled_count}, unavailable {unavailable_count}{unavailable_text}"
        )

    @staticmethod
    def _format_agent_runtime_engine_write_readiness_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "channels 0, native 0, runtime-state 0, fallback 0, disabled 0"

        def count(name: str) -> int:
            try:
                return max(0, int(summary.get(name) or 0))
            except (TypeError, ValueError):
                return 0

        def channel_list(name: str) -> str:
            values = summary.get(name)
            if not isinstance(values, list) or not values:
                return ""
            names = [
                str(item or "").replace("_", "-")[:32]
                for item in values[:3]
                if str(item or "").strip()
            ]
            return "(" + "?".join(names) + ")" if names else ""

        parts = [
            f"channels {count('channel_count')}",
            f"native {count('native_enabled_count')}{channel_list('native_enabled_channels')}",
            f"runtime-state {count('runtime_state_only_count')}{channel_list('runtime_state_only_channels')}",
            f"fallback {count('fallback_count')}{channel_list('fallback_channels')}",
            f"disabled {count('disabled_count')}{channel_list('disabled_channels')}",
        ]
        unavailable_count = count("unavailable_count")
        if unavailable_count:
            parts.append(f"unavailable {unavailable_count}{channel_list('unavailable_channels')}")
        return ", ".join(parts)

    @staticmethod
    def _is_runtime_report_query(text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return False
        report_markers = (
            "runtime report",
            "runtime final report",
            "agent runtime report",
            "final report",
            "generate report",
            "show report",
            "report summary",
            "最终报告",
            "鐢熸垚鎶ュ憡",
            "鎶ュ憡鎽樿",
            "鏌ョ湅鎶ュ憡",
            "杩愯鎶ュ憡",
            "runtime 鎶ュ憡",
        )
        runtime_markers = ("runtime", "agentruntime", "agent runtime", "鎶ュ憡", "report")
        return any(marker in normalized for marker in report_markers) and any(
            marker in normalized for marker in runtime_markers
        )

    def _handle_agent_runtime_sync_status_query(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if not self._is_runtime_sync_status_query(text):
            return None
        room_id = str(trigger.get("room_id") or "default")
        runtime_batch_id = self._runtime_batch_id_from_message(trigger)
        sync_event = {"batch_id": runtime_batch_id} if runtime_batch_id else None
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                action="sync_status",
                external_plan_id=self._active_runtime_external_plan_id(room_id),
                sync_event=sync_event,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime sync status query skipped: %s", type(exc).__name__)
            return None
        sync_status = result.get("sync_status", {}) if isinstance(result, dict) else {}
        if not isinstance(sync_status, dict):
            return None
        sync_replay = result.get("sync_replay", {}) if isinstance(result.get("sync_replay"), dict) else {}
        message_delivery = result.get("message_delivery_summary", {}) if isinstance(result.get("message_delivery_summary"), dict) else {}
        latest_actors = sync_status.get("latest_actors", []) if isinstance(sync_status.get("latest_actors"), list) else []
        latest_assets = sync_status.get("latest_assets", []) if isinstance(sync_status.get("latest_assets"), list) else []
        sync_replay_text = self._format_agent_runtime_sync_replay_report(sync_replay)
        message_delivery_text = self._format_agent_runtime_message_delivery_report(message_delivery)
        latest_actor_text = self._format_agent_runtime_sync_actor_rows(latest_actors)
        latest_asset_text = self._format_agent_runtime_sync_asset_rows(latest_assets)
        return (
            "【Runtime Sync 状态】\n"
            f"- room_status: {str(sync_status.get('room_status') or 'unknown')}\n"
            f"- event_count: {int(sync_status.get('event_count') or 0)}\n"
            f"- actor_events: {int(sync_status.get('actor_event_count') or 0)}\n"
            f"- asset_events: {int(sync_status.get('asset_event_count') or 0)}\n"
            f"- sync_replay: {sync_replay_text}\n"
            f"- message_delivery: {message_delivery_text}\n"
            f"- latest_actors: {latest_actor_text}\n"
            f"- latest_assets: {latest_asset_text}"
        )

    @staticmethod
    def _format_agent_runtime_sync_actor_rows(rows: Any) -> str:
        if not isinstance(rows, list) or not rows:
            return "none"
        formatted: list[str] = []
        for item in rows[:5]:
            if not isinstance(item, dict):
                continue
            actor = str(item.get("actor_name") or item.get("actor_id") or "actor")
            event_type = str(item.get("event_type") or "")
            lifecycle = str(item.get("lifecycle_status") or "")
            status = lifecycle or event_type or "updated"
            formatted.append(f"{actor}:{status}")
        return ", ".join(formatted) or "none"

    @staticmethod
    def _format_agent_runtime_sync_asset_rows(rows: Any) -> str:
        if not isinstance(rows, list) or not rows:
            return "none"
        formatted: list[str] = []
        for item in rows[:5]:
            if not isinstance(item, dict):
                continue
            asset = str(item.get("asset_id") or "asset")
            transfer_status = str(item.get("transfer_status") or item.get("status") or item.get("event_type") or "unknown")
            progress = int(item.get("progress") or 0)
            chunk_index = int(item.get("chunk_index") or 0)
            chunk_count = int(item.get("chunk_count") or 0)
            bytes_transferred = int(item.get("bytes_transferred") or 0)
            total_bytes = int(item.get("total_bytes") or 0)
            progress_text = f" {progress}%" if progress else ""
            chunk_text = f" chunk {chunk_index}/{chunk_count}" if chunk_index and chunk_count else ""
            byte_text = LANChatAgentWorker._format_runtime_transfer_bytes(bytes_transferred, total_bytes)
            formatted.append(f"{asset}:{transfer_status}{progress_text}{chunk_text}{byte_text}")
        return ", ".join(formatted) or "none"

    @staticmethod
    def _format_runtime_transfer_bytes(bytes_transferred: int, total_bytes: int) -> str:
        def human(value: int) -> str:
            amount = max(0, int(value or 0))
            if amount >= 1024 * 1024:
                return f"{amount / (1024 * 1024):.1f}MB"
            if amount >= 1024:
                return f"{amount // 1024}KB"
            return f"{amount}B"

        transferred = max(0, int(bytes_transferred or 0))
        total = max(0, int(total_bytes or 0))
        if transferred and total:
            return f" {human(transferred)}/{human(total)}"
        if transferred:
            return f" {human(transferred)}"
        return ""

    def _handle_active_runtime_plan_context_update(self, message: dict[str, Any], text: str) -> str | None:
        value = str(text or "").strip()
        if not value:
            return None
        message_kind = str((message or {}).get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if self._is_generation_start_text(value) or self._is_runtime_status_query_text(value):
            return None
        try:
            from .intent_understanding import IntentUnderstandingService

            decision = IntentUnderstandingService().classify(
                value,
                allow_llm=False,
                generation_active=False,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime active plan update intent skipped: %s", type(exc).__name__)
            return None
        contextual_update = self._is_contextual_plan_update_text(value)
        if decision.intent not in {"plan_drafting", "plan_revision"} and not contextual_update:
            return None
        if decision.intent == "plan_drafting" and not contextual_update:
            return None
        room_id = str((message or {}).get("room_id") or "default")
        external_plan_id = self._active_runtime_external_plan_id(room_id)
        if not external_plan_id:
            return None
        metadata = self._metadata_from_trigger(message or {})
        source_context_agent = (
            str(metadata.get("source_context_agent") or "").strip()
            or self._source_context_agent_from_text(value)
        )
        target_agent = (
            str(metadata.get("target_agent_name") or "").strip()
            or str((message or {}).get("target_agent_name") or "").strip()
            or str((message or {}).get("agent_name") or "").strip()
            or str(decision.target_agent or "").strip()
        )
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                external_plan_id=external_plan_id,
                text=value,
                sender_id=str((message or {}).get("sender_id") or (message or {}).get("from") or ""),
                sender_name=str((message or {}).get("sender_name") or (message or {}).get("from") or ""),
                owner_agent=target_agent,
                source_context_agents=[source_context_agent] if source_context_agent else [],
                action="plan_supplement",
                reply_to=str((message or {}).get("message_id") or ""),
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime active plan update failed: %s", type(exc).__name__)
            return "内部执行异常已记录，当前 Runtime 执行未完成。"
        plan_result = result.get("plan", {}) if isinstance(result, dict) else {}
        if not isinstance(result, dict) or not isinstance(plan_result, dict) or not plan_result.get("plan_id"):
            return None
        status_reply = self._agent_runtime_status_reply(
            room_id=room_id,
            external_plan_id=external_plan_id,
            batch_id=self._runtime_batch_id_from_message(message or {}),
        )
        if status_reply:
            return f"已更新当前 Runtime 方案。\n{status_reply}"
        return "已更新当前 Runtime 方案。"

    @staticmethod
    def _is_contextual_plan_update_text(text: str) -> bool:
        value = str(text or "").strip()
        if not value:
            return False
        contextual_markers = (
            "整理", "总结", "汇总", "梳理", "继续", "展开", "细化",
            "运行时",
            "基础上", "基于", "进一步", "改进", "完善", "补充方案",
        )
        return any(marker in value for marker in contextual_markers)

    def _record_active_runtime_busy_intervention(
        self,
        trigger: dict[str, Any],
        *,
        note_kind: str,
    ) -> bool:
        value = str((trigger or {}).get("text") or "").strip()
        if not value:
            return False
        room_id = str((trigger or {}).get("room_id") or "default")
        external_plan_id = self._active_runtime_external_plan_id(room_id)
        if not external_plan_id:
            return False
        patch_action = "intervention_modify" if str(note_kind or "") in {"edit_existing", "layout_constraint"} else "intervention_add"
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                external_plan_id=external_plan_id,
                text=value,
                sender_id=str((trigger or {}).get("sender_id") or (trigger or {}).get("from") or ""),
                sender_name=str((trigger or {}).get("sender_name") or (trigger or {}).get("from") or ""),
                owner_agent=str((trigger or {}).get("agent_name") or (trigger or {}).get("target_agent_name") or ""),
                action=patch_action,
                reply_to=str((trigger or {}).get("message_id") or ""),
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime busy intervention mirror failed: %s", type(exc).__name__)
            return False
        return bool(isinstance(result, dict) and result.get("recorded"))

    @staticmethod
    def _is_runtime_sync_status_query(text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return False
        sync_markers = (
            "sync status",
            "runtime sync",
            "sync summary",
            "运行时",
            "鍚屾鎽樿",
            "澶氫汉鍚屾",
            "鑱旀満鍚屾",
            "actor鍚屾",
            "actor 鍚屾",
            "璧勬簮鍚屾",
        )
        runtime_markers = ("runtime", "agentruntime", "agent runtime", "鍚屾", "sync")
        return any(marker in normalized for marker in sync_markers) and any(
            marker in normalized for marker in runtime_markers
        )

    @staticmethod
    def _runtime_batch_id_from_message(message: dict[str, Any]) -> str:
        if not isinstance(message, dict):
            return ""
        raw_metadata = LANChatAgentWorker._metadata_from_trigger(message)
        for key in ("batch_id", "runtime_batch_id", "target_batch_id"):
            value = message.get(key)
            if value is None or value == "":
                value = raw_metadata.get(key)
            if value is not None and value != "":
                return str(value)
        return ""

    def _agent_runtime_status_reply(
        self,
        *,
        room_id: str,
        external_plan_id: str = "",
        batch_id: str = "",
    ) -> str:
        try:
            sync_event = {"batch_id": str(batch_id or "")} if str(batch_id or "").strip() else None
            result = self._agent_runtime.handle_message(
                room_id=str(room_id or "default"),
                text="status",
                action="status_query",
                external_plan_id=str(external_plan_id or ""),
                sync_event=sync_event,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime status summary skipped: %s", type(exc).__name__)
            return ""
        status = result.get("status", {}) if isinstance(result, dict) else {}
        if not isinstance(status, dict) or not status.get("available"):
            return ""
        plan = status.get("plan_summary", {}) if isinstance(status.get("plan_summary"), dict) else {}
        batch = status.get("batch_summary", {}) if isinstance(status.get("batch_summary"), dict) else {}
        batch_tooling = status.get("batch_tooling_summary", {}) if isinstance(status.get("batch_tooling_summary"), dict) else {}
        state_patch = status.get("state_patch_summary", {}) if isinstance(status.get("state_patch_summary"), dict) else {}
        failure_strategy = (
            status.get("tool_failure_strategy_summary", {})
            if isinstance(status.get("tool_failure_strategy_summary"), dict)
            else {}
        )
        intervention_batches = (
            status.get("intervention_batch_summary", {})
            if isinstance(status.get("intervention_batch_summary"), dict)
            else {}
        )
        graphs = status.get("tool_graph_summary", {}) if isinstance(status.get("tool_graph_summary"), dict) else {}
        tool_execution = status.get("tool_execution_digest", {}) if isinstance(status.get("tool_execution_digest"), dict) else {}
        tool_queue_health = status.get("tool_queue_health_summary", {}) if isinstance(status.get("tool_queue_health_summary"), dict) else {}
        context = status.get("planning_context_summary", {}) if isinstance(status.get("planning_context_summary"), dict) else {}
        interventions = status.get("intervention_summary", {}) if isinstance(status.get("intervention_summary"), dict) else {}
        classification = status.get("classification_summary", {}) if isinstance(status.get("classification_summary"), dict) else {}
        scene_registry = status.get("scene_entity_registry", {}) if isinstance(status.get("scene_entity_registry"), dict) else {}
        scene_design_contract = status.get("scene_design_contract_summary", {}) if isinstance(status.get("scene_design_contract_summary"), dict) else {}
        semantic_arbitration = status.get("semantic_arbitration_summary", {}) if isinstance(status.get("semantic_arbitration_summary"), dict) else {}
        scene_snapshot = status.get("scene_snapshot_summary", {}) if isinstance(status.get("scene_snapshot_summary"), dict) else {}
        environment = status.get("environment_component_summary", {}) if isinstance(status.get("environment_component_summary"), dict) else {}
        runtime_resources = status.get("resource_summary", {}) if isinstance(status.get("resource_summary"), dict) else {}
        review_summary = status.get("review_summary", {}) if isinstance(status.get("review_summary"), dict) else {}
        geometry_summary = status.get("geometry_fact_summary", {}) if isinstance(status.get("geometry_fact_summary"), dict) else {}
        review_proposals = status.get("review_advisory_proposal_summary", {}) if isinstance(status.get("review_advisory_proposal_summary"), dict) else {}
        review_confirmations = status.get("review_advisory_confirmation_summary", {}) if isinstance(status.get("review_advisory_confirmation_summary"), dict) else {}
        layout_summary = status.get("layout_adjustment_summary", {}) if isinstance(status.get("layout_adjustment_summary"), dict) else {}
        final_adjustment_confirmations = status.get("final_adjustment_confirmation_summary", {}) if isinstance(status.get("final_adjustment_confirmation_summary"), dict) else {}
        runtime_commands = status.get("runtime_command_summary", {}) if isinstance(status.get("runtime_command_summary"), dict) else {}
        import_summary = status.get("import_summary", {}) if isinstance(status.get("import_summary"), dict) else {}
        provider = status.get("provider_summary", {}) if isinstance(status.get("provider_summary"), dict) else {}
        provider_readiness = status.get("provider_readiness_summary", {}) if isinstance(status.get("provider_readiness_summary"), dict) else {}
        engine_write_readiness = (
            status.get("engine_write_readiness_summary", {})
            if isinstance(status.get("engine_write_readiness_summary"), dict)
            else {}
        )
        report_health = (
            status.get("report_health_summary", {})
            if isinstance(status.get("report_health_summary"), dict)
            else {}
        )
        sync_summary = status.get("sync_summary", {}) if isinstance(status.get("sync_summary"), dict) else {}
        sync_health = status.get("sync_health_digest", {}) if isinstance(status.get("sync_health_digest"), dict) else {}
        asset_transfer_summary = status.get("asset_transfer_summary", {}) if isinstance(status.get("asset_transfer_summary"), dict) else {}
        sync_replay = status.get("sync_replay_summary", {}) if isinstance(status.get("sync_replay_summary"), dict) else {}
        asset_transfer_replay = (
            status.get("asset_transfer_replay_summary", {})
            if isinstance(status.get("asset_transfer_replay_summary"), dict)
            else {}
        )
        peer_sync_replay = (
            status.get("peer_sync_replay_summary", {})
            if isinstance(status.get("peer_sync_replay_summary"), dict)
            else {}
        )
        runtime_event_replay = (
            status.get("runtime_event_replay_summary", {})
            if isinstance(status.get("runtime_event_replay_summary"), dict)
            else {}
        )
        gm_summary_replay = (
            status.get("gm_summary_replay_summary", {})
            if isinstance(status.get("gm_summary_replay_summary"), dict)
            else {}
        )
        batch_execution_replay = (
            status.get("batch_execution_replay_summary", {})
            if isinstance(status.get("batch_execution_replay_summary"), dict)
            else {}
        )
        tool_graph_queue_replay = (
            status.get("tool_graph_queue_replay_summary", {})
            if isinstance(status.get("tool_graph_queue_replay_summary"), dict)
            else {}
        )
        worker_drain_replay = (
            status.get("worker_drain_replay_summary", {})
            if isinstance(status.get("worker_drain_replay_summary"), dict)
            else {}
        )
        runtime_guard = (
            status.get("runtime_guard_replay_summary", {})
            if isinstance(status.get("runtime_guard_replay_summary"), dict)
            else {}
        )
        plan_lifecycle = (
            status.get("scene_plan_lifecycle_summary", {})
            if isinstance(status.get("scene_plan_lifecycle_summary"), dict)
            else {}
        )
        vlm_checkpoint = (
            status.get("vlm_checkpoint_summary", {})
            if isinstance(status.get("vlm_checkpoint_summary"), dict)
            else {}
        )
        review_advisory_replay = (
            status.get("review_advisory_replay_summary", {})
            if isinstance(status.get("review_advisory_replay_summary"), dict)
            else {}
        )
        engine_write = status.get("engine_write_summary", {}) if isinstance(status.get("engine_write_summary"), dict) else {}
        engine_write_boundary = (
            status.get("engine_write_boundary_summary", {})
            if isinstance(status.get("engine_write_boundary_summary"), dict)
            else {}
        )
        message_delivery = status.get("message_delivery_summary", {}) if isinstance(status.get("message_delivery_summary"), dict) else {}
        batch_resource_flow = (
            status.get("batch_resource_flow_summary", {})
            if isinstance(status.get("batch_resource_flow_summary"), dict)
            else {}
        )
        status_batch_id = str(status.get("batch_id") or "").strip()
        batch_model_items = (
            classification.get("model_items")
            if isinstance(classification.get("model_items"), list)
            else []
        )
        items = (
            [str(item) for item in batch_model_items if str(item)]
            if status_batch_id and batch_model_items
            else [str(item) for item in (plan.get("concrete_object_items") or []) if str(item)]
        )
        item_text = "、".join(items[:8]) if items else "暂无模型清单"
        if len(items) > 8:
            item_text += f" 等 {len(items)} 项"
        substrate_items = [str(item) for item in (classification.get("substrate_items") or []) if str(item)]
        substrate_text = "、".join(substrate_items[:8]) if substrate_items else "暂无"
        if len(substrate_items) > 8:
            substrate_text += f" 等 {len(substrate_items)} 项"
        guarded_items = [str(item) for item in (classification.get("guarded_items") or []) if str(item)]
        guarded_text = "、".join(guarded_items[:5]) if guarded_items else "暂无"
        if len(guarded_items) > 5:
            guarded_text += f" 等 {len(guarded_items)} 项"
        classification_model_count = (
            len(batch_model_items)
            if batch_model_items
            else len([str(item) for item in (classification.get("model_items") or []) if str(item)])
        )
        classification_counts_text = f"model/substrate {classification_model_count}/{len(substrate_items)}"
        batch_status = batch.get("status_counts", {}) if isinstance(batch.get("status_counts"), dict) else {}
        graph_status = graphs.get("status_counts", {}) if isinstance(graphs.get("status_counts"), dict) else {}
        scene_registry_text = self._format_agent_runtime_scene_registry_report(scene_registry)
        scene_contract_text = self._format_agent_runtime_scene_contract_report(scene_design_contract)
        semantic_arbitration_text = self._format_agent_runtime_semantic_arbitration_report(semantic_arbitration)
        scene_snapshot_text = self._format_agent_runtime_scene_snapshot_report(scene_snapshot)
        runtime_resource_text = self._format_agent_runtime_resource_stage_report(runtime_resources)
        fact_source_text = self._format_agent_runtime_fact_source_boundary_report(
            status.get("fact_source_boundary_summary")
        )
        closure_text = self._format_agent_runtime_closure_report(
            status.get("fact_source_boundary_summary"),
            state_patch,
            operation_count=status.get("operation_count"),
            operation_total_count=status.get("operation_total_count"),
        )
        import_text = self._format_agent_runtime_import_stage_report(import_summary)
        actor_import_text = self._format_agent_runtime_actor_import_boundary_report(
            import_summary,
            scene_registry,
            engine_write_boundary,
        )
        report_health_text = self._format_agent_runtime_report_health_report(report_health)
        resource_text = self._format_agent_runtime_resource_report(provider)
        resource_readiness_text = self._format_agent_runtime_resource_readiness_report(provider_readiness)
        engine_write_readiness_text = self._format_agent_runtime_engine_write_readiness_report(
            engine_write_readiness
        )
        environment_text = self._format_agent_runtime_environment_report(environment)
        review_text = self._format_agent_runtime_review_report(review_summary)
        geometry_text = self._format_agent_runtime_geometry_fact_report(geometry_summary)
        review_proposal_text = self._format_agent_runtime_review_proposal_report(review_proposals)
        review_confirmation_text = self._format_agent_runtime_review_confirmation_report(review_confirmations)
        layout_text = self._format_agent_runtime_layout_report(layout_summary, final_adjustment_confirmations)
        command_text = self._format_agent_runtime_command_report(runtime_commands)
        sync_text = self._format_agent_runtime_sync_report(sync_summary)
        sync_health_text = self._format_agent_runtime_sync_health_report(sync_health)
        asset_transfer_text = self._format_agent_runtime_asset_transfer_report(asset_transfer_summary)
        sync_replay_text = self._format_agent_runtime_sync_replay_report(sync_replay)
        asset_transfer_replay_text = self._format_agent_runtime_replay_asset_transfer_report(asset_transfer_replay)
        peer_sync_replay_text = self._format_agent_runtime_replay_peer_sync_report(peer_sync_replay)
        runtime_event_replay_text = self._format_agent_runtime_replay_runtime_event_report(runtime_event_replay)
        gm_summary_replay_text = self._format_agent_runtime_gm_summary_replay_report(gm_summary_replay)
        tool_graph_replay_text = self._format_agent_runtime_tool_graph_replay_report(
            batch_execution_replay,
            tool_graph_queue_replay,
        )
        worker_drain_replay_text = self._format_agent_runtime_worker_drain_replay_report(worker_drain_replay)
        engine_write_text = self._format_agent_runtime_engine_write_report(engine_write)
        engine_write_boundary_text = self._format_agent_runtime_engine_write_boundary_report(engine_write_boundary)
        message_delivery_text = self._format_agent_runtime_message_delivery_report(message_delivery)
        resource_flow_text = self._format_agent_runtime_resource_flow_report(batch_resource_flow)
        batch_tooling_text = self._format_agent_runtime_batch_tooling_report(batch_tooling)
        state_patch_text = self._format_agent_runtime_replay_state_patch_report(state_patch)
        tool_execution_text = self._format_agent_runtime_tool_execution_digest_report(tool_execution)
        failure_strategy_text = self._format_agent_runtime_replay_failure_strategy_report(failure_strategy)
        runtime_guard_text = self._format_agent_runtime_replay_guard_report(runtime_guard)
        plan_lifecycle_text = self._format_agent_runtime_replay_plan_lifecycle_report(plan_lifecycle)
        vlm_checkpoint_text = self._format_agent_runtime_replay_vlm_report(vlm_checkpoint)
        review_advisory_replay_text = self._format_agent_runtime_replay_review_advisory_report(review_advisory_replay)
        tool_queue_health_text = self._format_agent_runtime_tool_queue_health_report(tool_queue_health)
        event_lines = self._format_agent_runtime_event_lines(status.get("latest_runtime_events"))
        context_items = context.get("latest_context") if isinstance(context.get("latest_context"), list) else []
        latest_context = context_items[-1] if context_items and isinstance(context_items[-1], dict) else {}
        context_text = str(latest_context.get("text_preview") or "").strip()
        if len(context_text) > 80:
            context_text = context_text[:80] + "..."
        brief_text = str(plan.get("design_brief_preview") or "").strip()
        if len(brief_text) > 100:
            brief_text = brief_text[:100] + "..."
        context_count = int(context.get("context_count") or 0)
        intervention_line = self._format_agent_runtime_intervention_summary(interventions)
        intervention_batch_line = self._format_agent_runtime_intervention_batch_summary(intervention_batches)
        current_plan_line = (
            f"- 当前方案：{str(status.get('plan_id') or '').strip()}"
            if str(status.get("plan_id") or "").strip()
            else "- 当前方案：尚未形成 ScenePlan"
        )
        reply_lines = [
            "【Runtime 状态】",
            current_plan_line,
        ]
        if brief_text:
            reply_lines.append(f"- 方案摘要：{brief_text}")
        reply_lines.extend([
            f"- 介入：{intervention_line}",
            f"- 分类计数：{classification_counts_text}",
            f"- 主要模型：{item_text}",
            f"- 环境/地形：{substrate_text}",
            f"- 场景实体：{scene_registry_text}",
            f"- 场景契约：{scene_contract_text}",
            f"- 语义仲裁：{semantic_arbitration_text}",
            f"- 场景快照：{scene_snapshot_text}",
            f"- 事实来源：{fact_source_text}",
            f"- Closure：{closure_text}",
            f"- 环境组件：{environment_text}",
            f"- Runtime 资源：{runtime_resource_text}",
            f"- 导入：{import_text}",
            f"- ActorImport：{actor_import_text}",
            f"- 报告健康：{report_health_text}",
            f"- 审查：{review_text}",
            f"- 几何事实：{geometry_text}",
            f"- 审查建议：{review_proposal_text}",
            f"- 审查确认：{review_confirmation_text}",
            f"- 布局调整：{layout_text}",
            f"- Runtime 命令：{command_text}",
            f"- 多人同步：{sync_text}；健康 {sync_health_text}；复盘 {sync_replay_text}",
            f"- 模型同传：{asset_transfer_text}",
            f"- 同传复盘：{asset_transfer_replay_text}",
            f"- Peer 复盘：{peer_sync_replay_text}",
            f"- 引擎写入：{engine_write_text}",
            f"- 写入边界：{engine_write_boundary_text}",
            f"- 消息送达：{message_delivery_text}",
            f"- 高风险资源：{guarded_text}",
            f"- 批次：{batch.get('batch_count', 0)} 个，状态 {batch_status or '暂无'}",
            f"- 资源批次：{resource_flow_text}",
            f"- Batch tooling: {batch_tooling_text}",
            f"- StatePatch: {state_patch_text}",
            f"- Failure strategy: {failure_strategy_text}",
            f"- RuntimeGuard: {runtime_guard_text}",
            f"- Plan lifecycle: {plan_lifecycle_text}",
            f"- VLM replay: {vlm_checkpoint_text}",
            f"- Review advisory replay: {review_advisory_replay_text}",
            f"- GM replay: {gm_summary_replay_text}",
            f"- ToolGraph replay: {tool_graph_replay_text}",
            f"- Worker drain replay: {worker_drain_replay_text}",
            f"- 介入批次：{intervention_batch_line}",
            f"- ToolCallGraph：{graphs.get('graph_count', 0)} 个，状态 {graph_status or '暂无'}",
            f"- Tool execution：{tool_execution_text}",
            f"- Runtime queue: {tool_queue_health_text}",
            f"- 资源通道：{resource_text}",
            f"- 资源可用性：{resource_readiness_text}",
            f"- Engine write readiness: {engine_write_readiness_text}",
        ])
        reply_lines.insert(-8, f"- RuntimeEvent replay: {runtime_event_replay_text}")
        reply = "\n".join(reply_lines)
        if event_lines:
            reply += "\n- 最近状态：" + "；".join(event_lines)
        return reply

    @staticmethod
    def _format_agent_runtime_tool_graph_replay_report(
        batch_summary: Any,
        queue_summary: Any,
    ) -> str:
        if not isinstance(batch_summary, dict):
            batch_summary = {}
        if not isinstance(queue_summary, dict):
            queue_summary = {}

        def count(source: dict[str, Any], name: str) -> int:
            try:
                return max(0, int(source.get(name) or 0))
            except (TypeError, ValueError):
                return 0

        return (
            "batch start/done/final "
            f"{count(batch_summary, 'started_count')}/"
            f"{count(batch_summary, 'completed_count')}/"
            f"{count(batch_summary, 'finalized_count')}, "
            "queue queued/dequeued/rejected/blocked "
            f"{count(queue_summary, 'queued_count')}/"
            f"{count(queue_summary, 'dequeued_count')}/"
            f"{count(queue_summary, 'rejected_count')}/"
            f"{count(queue_summary, 'blocked_count')}"
        )

    @staticmethod
    def _format_agent_runtime_gm_summary_replay_report(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary:
            return "exported 0, failed 0, readiness publish/query 0/0"

        def count(name: str) -> int:
            try:
                return max(0, int(summary.get(name) or 0))
            except (TypeError, ValueError):
                return 0

        exported = count("exported_count")
        failed = count("failed_count")
        available = count("available_count")
        scene_plan = count("scene_plan_count")
        readiness_publish = count("resource_readiness_publish_total")
        readiness_query = count("resource_readiness_query_total")
        return (
            f"exported {exported}, failed {failed}, available {available}, "
            f"scene-plan {scene_plan}, readiness publish/query {readiness_publish}/{readiness_query}"
        )

    def _agent_runtime_gm_summary_reply(
        self,
        *,
        room_id: str,
        external_plan_id: str = "",
        batch_id: str = "",
    ) -> str:
        try:
            result = self._agent_runtime.handle_message(
                room_id=str(room_id or "default"),
                text="gm summary",
                action="runtime_gm_summary",
                external_plan_id=str(external_plan_id or ""),
                sync_event={"batch_id": str(batch_id or "")} if str(batch_id or "").strip() else None,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime GM summary skipped: %s", type(exc).__name__)
            return ""
        summary = result.get("gm_summary", {}) if isinstance(result, dict) else {}
        if not isinstance(summary, dict) or not summary.get("available"):
            return ""
        current_plan = summary.get("current_plan", {}) if isinstance(summary.get("current_plan"), dict) else {}
        context_digest = summary.get("context_digest", {}) if isinstance(summary.get("context_digest"), dict) else {}
        speaker_counts = summary.get("speaker_type_counts", {}) if isinstance(summary.get("speaker_type_counts"), dict) else {}
        sync_health = summary.get("sync_health_digest", {}) if isinstance(summary.get("sync_health_digest"), dict) else {}
        asset_transfer_digest = (
            summary.get("asset_transfer_digest", {})
            if isinstance(summary.get("asset_transfer_digest"), dict)
            else {}
        )
        sync_replay_digest = (
            summary.get("sync_replay_digest", {})
            if isinstance(summary.get("sync_replay_digest"), dict)
            else {}
        )
        intervention_digest = (
            summary.get("intervention_digest", {})
            if isinstance(summary.get("intervention_digest"), dict)
            else {}
        )
        batch_tooling_digest = (
            summary.get("batch_tooling_digest", {})
            if isinstance(summary.get("batch_tooling_digest"), dict)
            else {}
        )
        resource_flow_digest = (
            summary.get("resource_flow_digest", {})
            if isinstance(summary.get("resource_flow_digest"), dict)
            else {}
        )
        tool_queue_health_digest = (
            summary.get("tool_queue_health_digest", {})
            if isinstance(summary.get("tool_queue_health_digest"), dict)
            else {}
        )
        tool_execution_digest = (
            summary.get("tool_execution_digest", {})
            if isinstance(summary.get("tool_execution_digest"), dict)
            else {}
        )
        state_patch_digest = (
            summary.get("state_patch_digest", {})
            if isinstance(summary.get("state_patch_digest"), dict)
            else {}
        )
        failure_strategy_digest = (
            summary.get("tool_failure_strategy_digest", {})
            if isinstance(summary.get("tool_failure_strategy_digest"), dict)
            else {}
        )
        runtime_guard_digest = (
            summary.get("runtime_guard_digest", {})
            if isinstance(summary.get("runtime_guard_digest"), dict)
            else {}
        )
        plan_lifecycle_digest = (
            summary.get("scene_plan_lifecycle_digest", {})
            if isinstance(summary.get("scene_plan_lifecycle_digest"), dict)
            else {}
        )
        engine_write_digest = (
            summary.get("engine_write_digest", {})
            if isinstance(summary.get("engine_write_digest"), dict)
            else {}
        )
        engine_write_readiness_digest = (
            summary.get("engine_write_readiness_digest", {})
            if isinstance(summary.get("engine_write_readiness_digest"), dict)
            else {}
        )
        engine_write_boundary_digest = (
            summary.get("engine_write_boundary_digest", {})
            if isinstance(summary.get("engine_write_boundary_digest"), dict)
            else {}
        )
        message_delivery_digest = (
            summary.get("message_delivery_digest", {})
            if isinstance(summary.get("message_delivery_digest"), dict)
            else {}
        )
        runtime_event_replay_digest = (
            summary.get("runtime_event_replay_digest", {})
            if isinstance(summary.get("runtime_event_replay_digest"), dict)
            else {}
        )
        resource_readiness_replay_digest = (
            summary.get("resource_readiness_replay_digest", {})
            if isinstance(summary.get("resource_readiness_replay_digest"), dict)
            else {}
        )
        vlm_checkpoint_digest = (
            summary.get("vlm_checkpoint_digest", {})
            if isinstance(summary.get("vlm_checkpoint_digest"), dict)
            else {}
        )
        review_advisory_replay_digest = (
            summary.get("review_advisory_replay_digest", {})
            if isinstance(summary.get("review_advisory_replay_digest"), dict)
            else {}
        )
        scene_design_contract_digest = (
            summary.get("scene_design_contract_digest", {})
            if isinstance(summary.get("scene_design_contract_digest"), dict)
            else {}
        )
        semantic_arbitration_digest = (
            summary.get("semantic_arbitration_digest", {})
            if isinstance(summary.get("semantic_arbitration_digest"), dict)
            else {}
        )
        scene_snapshot_digest = (
            summary.get("scene_snapshot_digest", {})
            if isinstance(summary.get("scene_snapshot_digest"), dict)
            else {}
        )
        fact_source_boundary_digest = (
            summary.get("fact_source_boundary_digest", {})
            if isinstance(summary.get("fact_source_boundary_digest"), dict)
            else {}
        )
        resource_stage_digest = (
            summary.get("resource_stage_digest", {})
            if isinstance(summary.get("resource_stage_digest"), dict)
            else {}
        )
        report_health_digest = (
            summary.get("report_health_digest", {})
            if isinstance(summary.get("report_health_digest"), dict)
            else {}
        )
        import_stage_digest = (
            summary.get("import_stage_digest", {})
            if isinstance(summary.get("import_stage_digest"), dict)
            else {}
        )
        geometry_fact_digest = (
            summary.get("geometry_fact_digest", {})
            if isinstance(summary.get("geometry_fact_digest"), dict)
            else {}
        )
        model_items = [
            str(item)
            for item in list(summary.get("model_items") or summary.get("candidate_model_items") or [])
            if str(item).strip()
        ]
        substrate_items = [str(item) for item in list(summary.get("substrate_items") or []) if str(item).strip()]
        agent_contributions = (
            context_digest.get("agent_contributions")
            if isinstance(context_digest.get("agent_contributions"), list)
            else []
        )
        contribution_names = [
            str(item.get("agent_name") or "").strip()
            for item in agent_contributions
            if isinstance(item, dict) and str(item.get("agent_name") or "").strip()
        ]
        latest_user_points = [
            str(item).strip()
            for item in list(context_digest.get("latest_user_points") or [])[:3]
            if str(item).strip()
        ]
        model_text = "、".join(model_items[:8]) if model_items else "暂无模型清单"
        if len(model_items) > 8:
            model_text += f" 等 {len(model_items)} 项"
        substrate_text = "、".join(substrate_items[:8]) if substrate_items else "暂无"
        if len(substrate_items) > 8:
            substrate_text += f" 等 {len(substrate_items)} 项"
        intervention_text = self._format_agent_runtime_intervention_digest(intervention_digest)
        batch_tooling_text = self._format_agent_runtime_batch_tooling_report(batch_tooling_digest)
        state_patch_text = self._format_agent_runtime_replay_state_patch_report(state_patch_digest)
        failure_strategy_text = self._format_agent_runtime_replay_failure_strategy_report(failure_strategy_digest)
        runtime_guard_text = self._format_agent_runtime_replay_guard_report(runtime_guard_digest)
        plan_lifecycle_text = self._format_agent_runtime_replay_plan_lifecycle_report(plan_lifecycle_digest)
        vlm_checkpoint_text = self._format_agent_runtime_replay_vlm_report(vlm_checkpoint_digest)
        review_advisory_replay_text = self._format_agent_runtime_replay_review_advisory_report(
            review_advisory_replay_digest
        )
        engine_write_text = self._format_agent_runtime_engine_write_report(engine_write_digest)
        engine_write_readiness_text = self._format_agent_runtime_engine_write_readiness_report(
            engine_write_readiness_digest
        )
        engine_write_boundary_text = self._format_agent_runtime_engine_write_boundary_report(
            engine_write_boundary_digest
        )
        message_delivery_text = self._format_agent_runtime_message_delivery_report(
            message_delivery_digest,
            redact_agent_reply=True,
        )
        runtime_event_replay_text = self._format_agent_runtime_gm_runtime_event_replay_digest(
            runtime_event_replay_digest
        )
        resource_readiness_replay_text = self._format_agent_runtime_replay_resource_readiness_report(
            resource_readiness_replay_digest
        )
        scene_contract_text = self._format_agent_runtime_scene_contract_report(scene_design_contract_digest)
        semantic_arbitration_text = self._format_agent_runtime_semantic_arbitration_report(semantic_arbitration_digest)
        scene_snapshot_text = self._format_agent_runtime_scene_snapshot_report(scene_snapshot_digest)
        fact_source_text = self._format_agent_runtime_fact_source_boundary_report(fact_source_boundary_digest)
        runtime_resource_text = self._format_agent_runtime_resource_stage_report(resource_stage_digest)
        import_text = self._format_agent_runtime_import_stage_report(import_stage_digest)
        report_health_text = self._format_agent_runtime_report_health_report(report_health_digest)
        geometry_text = self._format_agent_runtime_geometry_fact_report(geometry_fact_digest)
        asset_transfer_text = self._format_agent_runtime_asset_transfer_report(asset_transfer_digest)
        tool_queue_health_text = self._format_agent_runtime_tool_queue_health_report(tool_queue_health_digest)
        tool_execution_text = self._format_agent_runtime_tool_execution_digest_report(tool_execution_digest)
        contribution_text = "、".join(dict.fromkeys(contribution_names[:6])) if contribution_names else "暂无"
        user_points_text = "；".join(latest_user_points) if latest_user_points else "暂无"
        has_scene_plan = bool(summary.get("has_scene_plan"))
        title = str(current_plan.get("title") or "未命名方案")
        status = str(current_plan.get("status") or "unknown")
        brief = str(current_plan.get("design_brief_preview") or "").strip()
        if len(brief) > 120:
            brief = brief[:120] + "..."
        reply_lines = [
            "【GM Runtime 总结】",
            (
                f"- 当前方案：{title}（{status}）"
                if has_scene_plan
                else "- 当前方案：尚未形成 ScenePlan"
            ),
            f"- 上下文：{int(summary.get('context_count') or 0)} 条，用户 {int(speaker_counts.get('user') or 0)} / Agent {int(speaker_counts.get('agent') or 0)}",
        ]
        if brief:
            reply_lines.append(f"- 方案摘要：{brief}")
        reply_lines.extend([
            f"- Agent 贡献：{contribution_text}",
            f"- 最近用户要点：{user_points_text}",
            f"- 介入摘要：{intervention_text}",
            f"- 主要模型：{model_text}",
            f"- 环境/地形：{substrate_text}",
            f"- Scene contract: {scene_contract_text}",
            f"- Semantic arbitration: {semantic_arbitration_text}",
            f"- Scene snapshot: {scene_snapshot_text}",
            f"- Fact source: {fact_source_text}",
            f"- Runtime resources: {runtime_resource_text}",
            f"- Import: {import_text}",
            f"- Report health: {report_health_text}",
            f"- Geometry facts: {geometry_text}",
            f"- Batch tooling: {batch_tooling_text}",
            f"- StatePatch: {state_patch_text}",
            f"- Failure strategy: {failure_strategy_text}",
            f"- RuntimeGuard: {runtime_guard_text}",
            f"- Plan lifecycle: {plan_lifecycle_text}",
            f"- VLM replay: {vlm_checkpoint_text}",
            f"- Review advisory replay: {review_advisory_replay_text}",
            f"- Engine write: {engine_write_text}",
            f"- Engine write readiness: {engine_write_readiness_text}",
            f"- Engine write boundary: {engine_write_boundary_text}",
            f"- Message delivery: {message_delivery_text}",
            f"- 模型同传：{asset_transfer_text}",
            f"- 资源批次：{self._format_agent_runtime_resource_flow_report(resource_flow_digest)}",
            f"- Tool execution: {tool_execution_text}",
            f"- Runtime queue: {tool_queue_health_text}",
            f"- 多人同步健康：{self._format_agent_runtime_sync_health_report(sync_health)}",
            f"- 同步复盘：{self._format_agent_runtime_gm_sync_replay_digest(sync_replay_digest)}",
        ])
        reply_lines.append(f"- 资源通道复盘：{resource_readiness_replay_text}")
        reply_lines.append(f"- RuntimeEvent replay: {runtime_event_replay_text}")
        return "\n".join(reply_lines)

    @staticmethod
    def _format_agent_runtime_gm_runtime_event_replay_digest(digest: Any) -> str:
        if not isinstance(digest, dict) or not digest:
            return "emitted 0, failed 0, skipped 0"
        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in ("provider", "prompt", "url", "raw", "token", "api-key"):
                text = re.sub(marker, "resource", text, flags=re.IGNORECASE)
            return text[:60]

        emitted = int(digest.get("emitted_count") or 0)
        failed = int(digest.get("emit_failed_count") or 0)
        skipped = int(digest.get("disclosure_skipped_count") or 0)
        parts = [f"emitted {emitted}", f"failed {failed}", f"skipped {skipped}"]
        report_ready = int(digest.get("report_ready_count") or 0)
        report_attention = int(digest.get("report_attention_count") or 0)
        if report_ready > 0:
            report_part = f"report-ready {report_ready}"
            if report_attention > 0:
                report_part += f"/attention {report_attention}"
            status_counts = (
                digest.get("report_health_status_counts")
                if isinstance(digest.get("report_health_status_counts"), dict)
                else {}
            )
            status_parts = [
                f"{safe_label(key)}:{int(value or 0)}"
                for key, value in sorted(status_counts.items())[:3]
                if str(key).strip() and int(value or 0) > 0
            ]
            if status_parts:
                report_part += " " + ",".join(status_parts)
            parts.append(report_part)
        latest_report = digest.get("latest_report_ready") if isinstance(digest.get("latest_report_ready"), dict) else {}
        environment_import_failure_code_counts = (
            latest_report.get("environment_import_failure_code_counts")
            if isinstance(latest_report.get("environment_import_failure_code_counts"), dict)
            else {}
        )
        environment_failure_parts = [
            f"{safe_label(key)}:{int(value or 0)}"
            for key, value in sorted(environment_import_failure_code_counts.items())[:3]
            if str(key).strip() and int(value or 0) > 0
        ]
        if environment_failure_parts:
            parts.append("env-import-failures " + ",".join(environment_failure_parts))
        engine_write_bridge_failed_count = int(
            latest_report.get("engine_write_bridge_failed_count") or 0
        )
        engine_write_bridge_error_code_counts = (
            latest_report.get("engine_write_bridge_error_code_counts")
            if isinstance(latest_report.get("engine_write_bridge_error_code_counts"), dict)
            else {}
        )
        engine_write_failure_parts = [
            f"{safe_label(key)}:{int(value or 0)}"
            for key, value in sorted(engine_write_bridge_error_code_counts.items())[:3]
            if str(key).strip() and int(value or 0) > 0
        ]
        if engine_write_failure_parts:
            parts.append("engine-write-failures " + ",".join(engine_write_failure_parts))
        elif engine_write_bridge_failed_count > 0:
            parts.append(f"engine-write-failures {engine_write_bridge_failed_count}")
        engine_write_readiness_mismatch_count = int(
            latest_report.get("engine_write_readiness_mismatch_count") or 0
        )
        engine_write_readiness_mismatch_channels = (
            latest_report.get("engine_write_readiness_mismatch_channels")
            if isinstance(latest_report.get("engine_write_readiness_mismatch_channels"), list)
            else []
        )
        engine_write_mismatch_parts = [
            safe_label(item)
            for item in engine_write_readiness_mismatch_channels[:4]
            if safe_label(item)
        ]
        if engine_write_readiness_mismatch_count:
            if engine_write_mismatch_parts:
                parts.append(
                    "engine-write-mismatch "
                    f"{engine_write_readiness_mismatch_count}(" + "/".join(engine_write_mismatch_parts) + ")"
                )
            else:
                parts.append(f"engine-write-mismatch {engine_write_readiness_mismatch_count}")
        latest_skip = digest.get("latest_disclosure_skip") if isinstance(digest.get("latest_disclosure_skip"), dict) else {}
        skip_type = safe_label(latest_skip.get("event_type"))
        skip_audience = safe_label(latest_skip.get("audience"))
        if skip_type:
            parts.append(f"latest-skip {skip_type}:{skip_audience or 'unknown'}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_gm_sync_replay_digest(digest: Any) -> str:
        if not isinstance(digest, dict) or not digest:
            return "recorded 0, asset progress 0, peer join/leave 0/0, reconcile 0/0"
        def safe_label(value: Any) -> str:
            text = str(value or "").strip().replace("_", "-")
            for marker in ("prompt", "provider", "url", "raw", "token", "api-key", "path", "session", "job"):
                text = re.sub(marker, "resource", text, flags=re.IGNORECASE)
            return text[:60]

        recorded_count = int(digest.get("recorded_count") or 0)
        failed_count = int(digest.get("failed_count") or 0)
        actor_transform_count = int(digest.get("actor_transform_count") or 0)
        actor_delete_count = int(digest.get("actor_delete_count") or 0)
        asset_progress_count = int(digest.get("asset_transfer_progress_count") or 0)
        asset_completed_count = int(digest.get("asset_transfer_completed_count") or 0)
        asset_failed_count = int(digest.get("asset_transfer_failed_count") or 0)
        peer_ready_count = int(digest.get("peer_asset_ready_count") or 0)
        peer_join_count = int(digest.get("peer_join_count") or 0)
        peer_leave_count = int(digest.get("peer_leave_count") or 0)
        sync_reconcile_count = int(digest.get("sync_reconcile_count") or 0)
        sync_reconcile_failed_count = int(digest.get("sync_reconcile_failed_count") or 0)
        failure_code_counts = (
            digest.get("failure_code_counts")
            if isinstance(digest.get("failure_code_counts"), dict)
            else {}
        )
        failure_codes = ", ".join(
            f"{safe_label(code)}:{int(count or 0)}"
            for code, count in sorted(failure_code_counts.items())[:5]
            if int(count or 0) > 0 and safe_label(code)
        )
        latest_failure_code = safe_label(digest.get("latest_failure_code"))
        parts = [
            f"recorded {recorded_count}/{failed_count}",
            f"actor transform/delete {actor_transform_count}/{actor_delete_count}",
            f"asset progress {asset_progress_count}",
            f"asset completed/failed {asset_completed_count}/{asset_failed_count}",
            f"peer-ready {peer_ready_count}",
            f"peer join/leave {peer_join_count}/{peer_leave_count}",
            f"reconcile {sync_reconcile_count}/{sync_reconcile_failed_count}",
            *([f"failure codes {failure_codes}"] if failure_codes else []),
            *([f"latest failure {latest_failure_code}"] if latest_failure_code else []),
        ]
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_intervention_digest(digest: Any) -> str:
        if not isinstance(digest, dict) or not digest:
            return "pending 0, accepted 0, deferred 0"
        pending_count = int(digest.get("pending_count") or 0)
        accepted_count = int(digest.get("accepted_count") or 0)
        deferred_count = int(digest.get("deferred_count") or 0)
        absorbable_count = int(digest.get("absorbable_pending_count") or 0)
        non_absorbable_count = int(digest.get("non_absorbable_pending_count") or 0)
        parts = [
            f"pending {pending_count}",
            f"accepted {accepted_count}",
            f"deferred {deferred_count}",
        ]
        if absorbable_count or non_absorbable_count:
            parts.append(f"absorbable {absorbable_count}")
            parts.append(f"needs-confirmation {non_absorbable_count}")
        return ", ".join(parts)

    @staticmethod
    def _format_agent_runtime_intervention_summary(interventions: Any) -> str:
        if not isinstance(interventions, dict):
            return "鏆傛棤"
        pending_count = int(interventions.get("pending_count") or 0)
        accepted_count = int(interventions.get("accepted_count") or 0)
        deferred_count = int(interventions.get("deferred_count") or 0)
        parts = [
            f"寰呭鐞?{pending_count}",
            f"宸插惛鏀?{accepted_count}",
            f"寤跺悗 {deferred_count}",
        ]
        latest_pending = interventions.get("latest_pending")
        if isinstance(latest_pending, list) and latest_pending:
            latest = latest_pending[-1] if isinstance(latest_pending[-1], dict) else {}
            items = [str(item) for item in (latest.get("items") or []) if str(item)]
            preview = "、".join(items[:3]) if items else str(latest.get("text") or "").strip()
            if len(preview) > 48:
                preview = preview[:48] + "..."
            if preview:
                parts.append(f"最近待处理：{preview}")
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_intervention_batch_summary(summary: Any) -> str:
        if not isinstance(summary, dict):
            return "暂无"
        batch_count = int(summary.get("batch_count") or 0)
        status_counts = summary.get("status_counts") if isinstance(summary.get("status_counts"), dict) else {}
        parts = [f"{batch_count} batch(es)"]
        if status_counts:
            parts.append(f"鐘舵€?{status_counts}")
        latest = summary.get("latest_batches")
        if isinstance(latest, list) and latest:
            batch = latest[-1] if isinstance(latest[-1], dict) else {}
            items = [str(item) for item in (batch.get("requested_items") or []) if str(item)]
            preview = "、".join(items[:3])
            if len(items) > 3:
                preview += f" 等 {len(items)} 项"
            if preview:
                parts.append(
                    f"鏈€杩戠 {batch.get('batch_index') or 0}/{batch.get('total_batches') or 0} 鎵癸細{preview}"
                )
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_message_delivery_report(summary: Any, *, redact_agent_reply: bool = False) -> str:
        if not isinstance(summary, dict):
            return "暂无"
        def safe_delivery_label(value: Any) -> str:
            label = str(value or "").strip()
            if not label:
                return ""
            if not redact_agent_reply:
                return label
            replacements = {
                "agent_reply": "reply",
                "provider": "adapter",
                "prompt": "detail",
                "url": "link",
                "raw": "payload",
                "token": "credential",
                "api-key": "credential",
            }
            for marker, replacement in replacements.items():
                label = re.sub(marker, replacement, label, flags=re.IGNORECASE)
            return label[:80]

        def safe_failure_label(value: Any) -> str:
            return safe_delivery_label(value).replace("_", "-")

        requested = int(summary.get("requested_count") or 0)
        succeeded = int(summary.get("succeeded_count") or 0)
        failed = int(summary.get("failed_count") or 0)
        parts = [
            f"璇锋眰 {requested}",
            f"鎴愬姛 {succeeded}",
            f"澶辫触 {failed}",
        ]
        message_kind_counts = summary.get("message_kind_counts") if isinstance(summary.get("message_kind_counts"), dict) else {}
        channel_counts = summary.get("channel_counts") if isinstance(summary.get("channel_counts"), dict) else {}
        latest_kind = str(summary.get("latest_message_kind") or "").strip()
        latest_channel = str(summary.get("latest_channel") or "").strip()
        latest_stage = str(summary.get("latest_stage") or "").strip()
        latest_progress = summary.get("latest_progress")
        failure_code_counts = (
            summary.get("failure_code_counts")
            if isinstance(summary.get("failure_code_counts"), dict)
            else {}
        )
        failure_codes = ", ".join(
            f"{safe_failure_label(code)}:{int(count or 0)}"
            for code, count in sorted(failure_code_counts.items())[:5]
            if int(count or 0) > 0 and safe_failure_label(code)
        )
        latest_failure_code = safe_failure_label(summary.get("latest_failure_code"))
        if message_kind_counts:
            safe_kinds = {
                safe_delivery_label(key): int(value or 0)
                for key, value in message_kind_counts.items()
                if safe_delivery_label(key)
            }
            parts.append(f"绫诲瀷 {safe_kinds}")
        if channel_counts:
            safe_channels = {
                safe_delivery_label(key): int(value or 0)
                for key, value in channel_counts.items()
                if safe_delivery_label(key)
            }
            parts.append(f"鍑哄彛 {safe_channels}")
        if failure_codes:
            parts.append(f"failure codes {failure_codes}")
        if latest_failure_code:
            parts.append(f"latest failure {latest_failure_code}")
        if latest_kind or latest_channel or latest_stage:
            latest = safe_delivery_label(latest_kind) or "unknown"
            if latest_channel:
                latest += f"/{safe_delivery_label(latest_channel)}"
            if latest_stage:
                latest += f"@{safe_delivery_label(latest_stage)}"
            if isinstance(latest_progress, (int, float)):
                latest += f" {max(0, min(100, int(latest_progress)))}%"
            parts.append(f"鏈€杩?{latest}")
        return "；".join(parts)

    @staticmethod
    def _format_agent_runtime_event_lines(events: Any) -> list[str]:
        return [line for line, _event in LANChatAgentWorker._format_agent_runtime_event_rows(events)]

    @staticmethod
    def _format_agent_runtime_event_rows(events: Any) -> list[tuple[str, dict[str, Any]]]:
        if not isinstance(events, list):
            return []
        rows: list[tuple[str, dict[str, Any]]] = []
        for event in events[-3:]:
            if not isinstance(event, dict):
                continue
            title = str(event.get("title") or "").strip()
            message = str(event.get("message") or "").strip()
            if not title and not message:
                continue
            progress = event.get("progress")
            prefix = f"{title}" if title else "状态更新"
            if isinstance(progress, int):
                prefix = f"{prefix} {max(0, min(100, progress))}%"
            if message:
                rows.append((f"{prefix}: {message}", event))
            else:
                rows.append((prefix, event))
        return rows

    @classmethod
    def _is_runtime_gm_summary_query(cls, trigger: dict[str, Any]) -> bool:
        text = str((trigger or {}).get("text") or "").strip()
        if not text:
            return False
        is_gm_target = cls._is_gm_target_trigger(trigger) or text.startswith("@GM")
        if not is_gm_target:
            return False
        summary_tokens = ("总结", "整理", "汇总", "当前方案", "当前共识", "复盘", "gm summary", "runtime summary")
        status_only_tokens = ("进度", "到哪", "到哪里", "什么情况", "现在情况", "生成到哪里")
        return any(word in text for word in summary_tokens) and not any(
            word in text for word in status_only_tokens
        )

    @classmethod
    def _is_runtime_status_summary_query(cls, trigger: dict[str, Any]) -> bool:
        text = str((trigger or {}).get("text") or "").strip()
        if not text:
            return False
        is_gm_target = cls._is_gm_target_trigger(trigger) or text.startswith("@GM")
        if not is_gm_target:
            return False
        return any(word in text for word in (
            "运行时",
            "进度", "到哪", "到哪里", "什么情况", "现在情况",
        ))

    @staticmethod
    def _is_runtime_status_query_text(text: str) -> bool:
        value = str(text or "").strip()
        if not value:
            return False
        try:
            from .intent_understanding import IntentUnderstandingService

            decision = IntentUnderstandingService().classify(
                value,
                allow_llm=False,
                generation_active=False,
            )
            return decision.intent == "status_query"
        except Exception:  # noqa: BLE001
            return any(word in value for word in (
                "到哪步", "到哪一步", "到哪里", "生成到哪里", "生成情况", "查看生成情况",
                "运行时",
                "运行时",
                "了解现在的生成方案", "我们开始生成了吗", "现在情况", "什么情况",
                "情况是什么", "生成计划是什么", "为什么执行生成计划", "现在生成到哪里",
            ))

    @staticmethod
    def _is_gm_target_trigger(trigger: dict[str, Any]) -> bool:
        agent_id = str((trigger or {}).get("agent_id") or (trigger or {}).get("target_agent_id") or "").strip().lower()
        agent_name = str((trigger or {}).get("agent_name") or (trigger or {}).get("target_agent_name") or "").strip().lower()
        return agent_id == "gm" or agent_name in {"gm", "主持人", "裁判", "game master"}

    def _handle_coordinator_generation_start(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        if not self._is_generation_start_text(text):
            return None
        room_id = str(trigger.get("room_id") or "default")
        host_id = str(trigger.get("sender_id") or trigger.get("from") or "")
        runtime_reply = self._execute_active_runtime_plan_generation(
            trigger,
            room_id=room_id,
            host_id=host_id,
        )
        if runtime_reply is not None:
            self._logger.info(
                "[LANChatGenerationTrace] phase=trigger_generation_start_runtime_first room=%s sender=%s/%s text=%s",
                room_id,
                trigger.get("sender_id") or trigger.get("from") or "",
                trigger.get("sender_name") or trigger.get("from") or "",
                _trace_preview(text),
            )
            return runtime_reply
        try:
            coordinator = self._get_interaction_coordinator()
            plan = coordinator.active_plan_for_room(room_id)
            self._logger.info(
                "[LANChatGenerationTrace] phase=trigger_generation_start room=%s sender=%s/%s plan=%s status=%s text=%s",
                room_id,
                trigger.get("sender_id") or trigger.get("from") or "",
                trigger.get("sender_name") or trigger.get("from") or "",
                str(getattr(plan, "plan_id", "") or ""),
                str(getattr(getattr(plan, "status", ""), "value", getattr(plan, "status", "")) or ""),
                _trace_preview(text),
            )
            if plan is None:
                return self._execute_active_runtime_plan_generation(
                    trigger,
                    room_id=room_id,
                    host_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                )
            if plan.status == SeedPlanStatus.CONFIRMED:
                return self._start_active_coordinator_generation(
                    coordinator,
                    room_id=room_id,
                    host_id=host_id,
                )
            if plan.status == SeedPlanStatus.EXECUTING:
                latest_status = coordinator._latest_generation_job_status(plan.plan_id)
                return coordinator._status_query_message(plan, "", latest_status)
            return None
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Coordinator generation start skipped: %s", type(exc).__name__)
            return None

    def _start_active_coordinator_generation(
        self,
        coordinator: InteractionCoordinator,
        *,
        room_id: str,
        host_id: str,
    ) -> str | None:
        if not self._can_execute_generation_locally():
            self._logger.info(
                "[LANChatGenerationTrace] phase=blocked_non_host room=%s host=%s",
                room_id,
                host_id,
            )
            return None
        plan = coordinator.active_plan_for_room(room_id)
        if plan is None:
            self._logger.info(
                "[LANChatGenerationTrace] phase=start_request_no_plan room=%s host=%s",
                room_id,
                host_id,
            )
            return None
        self._logger.info(
            "[LANChatGenerationTrace] phase=start_request room=%s host=%s plan=%s status=%s design_len=%s summary=%s",
            room_id,
            host_id,
            plan.plan_id,
            str(getattr(plan.status, "value", plan.status)),
            len(str(getattr(plan, "design_brief", "") or "")),
            _trace_preview(getattr(plan, "intent_summary", "") or "", 100),
        )
        if plan.status == SeedPlanStatus.EXECUTING:
            latest_status = coordinator._latest_generation_job_status(plan.plan_id)
            return coordinator._status_query_message(plan, "", latest_status)
        if plan.status != SeedPlanStatus.CONFIRMED:
            if plan.status not in {SeedPlanStatus.DRAFT, SeedPlanStatus.CLARIFYING, SeedPlanStatus.PROPOSED}:
                return None
            disclosure_start = len(coordinator.disclosure_events)
            confirmed = coordinator.confirm_seed_plan(plan.plan_id, str(host_id or ""))
            self._logger.info(
                "[LANChatGenerationTrace] phase=confirm_result room=%s host=%s plan=%s ok=%s message=%s payload_plan=%s design_len=%s",
                room_id,
                host_id,
                plan.plan_id,
                bool(getattr(confirmed, "ok", False)),
                _trace_preview(getattr(confirmed, "message", "") or ""),
                str((getattr(confirmed, "payload", {}) or {}).get("plan_id") or ""),
                len(str(getattr(plan, "design_brief", "") or "")),
            )
            emitted = self._emit_new_disclosure_events(coordinator, disclosure_start)
            self._start_coordinator_disclosure_watch(coordinator, disclosure_start + emitted)
            if not getattr(confirmed, "ok", False):
                return str(getattr(event, "message", "") or "当前状态暂不可用，请稍后再试。")
            plan = coordinator.active_plan_for_room(room_id) or plan
        if plan.status == SeedPlanStatus.CONFIRMED:
            if not self._agent_runtime_flags.can_call_legacy_main_workflow():
                self._logger.info(
                    "[LANChatGenerationTrace] phase=blocked_legacy_main_workflow room=%s plan=%s runtime_enabled=%s adapter_allowed=%s",
                    room_id,
                    plan.plan_id,
                    self._agent_runtime_flags.agent_runtime_enabled,
                    self._agent_runtime_flags.allow_legacy_function_adapter,
                )
                return self._execute_confirmed_plan_via_agent_runtime(
                    plan,
                    room_id=room_id,
                    host_id=host_id,
                )
            disclosure_start = len(coordinator.disclosure_events)
            self._logger.info(
                "[LANChatGenerationTrace] phase=execute_confirmed room=%s plan=%s design_len=%s",
                room_id,
                plan.plan_id,
                len(str(getattr(plan, "design_brief", "") or "")),
            )
            ref = coordinator.execute_confirmed_plan(plan.plan_id)
            self._logger.info(
                "[LANChatGenerationTrace] phase=execute_result room=%s plan=%s job=%s status=%s",
                room_id,
                plan.plan_id,
                getattr(ref, "job_id", ""),
                getattr(ref, "status", ""),
            )
            emitted = self._emit_new_disclosure_events(coordinator, disclosure_start)
            self._start_coordinator_disclosure_watch(coordinator, disclosure_start + emitted)
            self._emit_generation_scheduler_disclosure()
            return f"【执行结果】SeedPlan {plan.plan_id} 已进入生成队列：{ref.job_id} ({ref.status})"
        return None

    def _execute_confirmed_plan_via_agent_runtime(self, plan: Any, *, room_id: str, host_id: str) -> str:
        try:
            text = str(
                getattr(plan, "design_brief", "")
                or getattr(plan, "intent_summary", "")
                or getattr(plan, "title", "")
                or ""
            )
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=str(host_id or ""),
                sender_name=str(host_id or ""),
                owner_agent=str(getattr(plan, "owner_agent_name", "") or getattr(plan, "owner_agent_id", "") or ""),
                source_context_agents=list(getattr(plan, "source_context_agents", []) or []),
                action="confirm_and_execute",
                external_plan_id=str(getattr(plan, "plan_id", "") or ""),
                scene_name=self._runtime_scene_name_from_plan(plan),
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "[LANChatGenerationTrace] phase=agent_runtime_execute_failed room=%s plan=%s exc_type=%s",
                room_id,
                getattr(plan, "plan_id", ""),
                type(exc).__name__,
            )
            return "内部执行异常已记录，当前 Runtime 执行未完成。"

        runtime_plan = result.get("plan", {}) if isinstance(result, dict) else {}
        runtime_plan_id = str(runtime_plan.get("plan_id") or "")
        batches = self._agent_runtime_batches_from_result(result) if isinstance(result, dict) else []
        graphs = self._agent_runtime_graphs_from_result(result)
        graph_statuses = [str(graph.get("status") or "") for graph in graphs if isinstance(graph, dict)]
        if graphs:
            self._remember_room_id(room_id)
        self._logger.info(
            "[LANChatGenerationTrace] phase=agent_runtime_execute_result room=%s external_plan=%s runtime_plan=%s batches=%s graph_statuses=%s",
            room_id,
            getattr(plan, "plan_id", ""),
            runtime_plan_id,
            len(batches),
            ",".join(graph_statuses),
        )
        self._log_agent_runtime_evidence(
            phase="agent_runtime_execute_result",
            room_id=room_id,
            runtime_plan_id=runtime_plan_id,
            result=result,
        )
        return self._format_agent_runtime_execution_reply(result)

    def _execute_active_runtime_plan_generation(
        self,
        trigger: dict[str, Any],
        *,
        room_id: str,
        host_id: str,
    ) -> str | None:
        if not self._can_execute_generation_locally():
            self._logger.info(
                "[LANChatGenerationTrace] phase=runtime_active_plan_execute_skipped room=%s reason=not_authoritative",
                room_id,
            )
            return None
        external_plan_id = self._active_runtime_external_plan_id(room_id)
        if not external_plan_id:
            self._logger.info(
                "[LANChatGenerationTrace] phase=runtime_active_plan_execute_no_active_plan room=%s",
                room_id,
            )
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=str(trigger.get("text") or ""),
                sender_id=str(host_id or ""),
                sender_name=str(trigger.get("sender_name") or host_id or ""),
                owner_agent=str(trigger.get("agent_name") or ""),
                source_context_agents=[],
                action="confirm_and_execute",
                external_plan_id=external_plan_id,
                scene_name=self._runtime_scene_name_from_trigger(trigger),
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "[LANChatGenerationTrace] phase=runtime_active_plan_execute_failed room=%s exc_type=%s",
                room_id,
                type(exc).__name__,
            )
            return "内部执行异常已记录，当前 Runtime 执行未完成。"

        runtime_plan = result.get("plan", {}) if isinstance(result, dict) else {}
        if not runtime_plan:
            action = str(result.get("action") or "") if isinstance(result, dict) else ""
            handled = bool(result.get("handled")) if isinstance(result, dict) else False
            self._logger.info(
                "[LANChatGenerationTrace] phase=runtime_active_plan_execute_no_plan room=%s action=%s handled=%s external_plan=%s",
                room_id,
                action,
                handled,
                external_plan_id,
            )
            return None
        runtime_plan_id = str(runtime_plan.get("plan_id") or "")
        batches = self._agent_runtime_batches_from_result(result) if isinstance(result, dict) else []
        graphs = self._agent_runtime_graphs_from_result(result)
        graph_statuses = [str(graph.get("status") or "") for graph in graphs if isinstance(graph, dict)]
        if graphs:
            self._remember_room_id(room_id)
        self._logger.info(
            "[LANChatGenerationTrace] phase=runtime_active_plan_execute_result room=%s runtime_plan=%s batches=%s graph_statuses=%s",
            room_id,
            runtime_plan_id,
            len(batches),
            ",".join(graph_statuses),
        )
        self._log_agent_runtime_evidence(
            phase="runtime_active_plan_execute_result",
            room_id=room_id,
            runtime_plan_id=runtime_plan_id,
            result=result,
        )
        return self._format_agent_runtime_execution_reply(result)

    def _execute_structured_host_action_via_agent_runtime(self, payload: dict[str, Any]) -> str:
        data = dict(payload or {})
        seed_plan = data.get("seed_plan") if isinstance(data.get("seed_plan"), dict) else {}
        plan_id = str(
            data.get("plan_id")
            or data.get("external_plan_id")
            or data.get("seed_plan_id")
            or data.get("runtime_plan_id")
            or data.get("resolved_from_plan_id")
            or seed_plan.get("plan_id")
            or seed_plan.get("external_plan_id")
            or seed_plan.get("seed_plan_id")
            or ""
        )
        room_id = str(data.get("room_id") or seed_plan.get("room_id") or "default")
        action_type = str(data.get("action_type") or "").strip()
        text = str(
            data.get("resolved_intent_text")
            or data.get("intent_text")
            or seed_plan.get("design_brief")
            or seed_plan.get("intent_summary")
            or seed_plan.get("title")
            or ""
        )
        host_id = str(data.get("source_user_id") or data.get("host_id") or "host")
        owner_agent = str(
            data.get("target_agent_name")
            or data.get("source_agent_name")
            or dict(seed_plan.get("review_policy") or {}).get("owner_agent_name")
            or ""
        )
        source_context_agents = list(
            data.get("source_context_agents")
            or dict(seed_plan.get("review_policy") or {}).get("source_context_agents")
            or []
        )
        scene_name = str(data.get("scene_name") or seed_plan.get("scene_name") or "Scene/鍦烘櫙1.scene")
        if action_type == "post_generation_add":
            runtime_action = "post_generation_add"
        else:
            runtime_action = "confirm_and_execute"
        try:
            result = self._agent_runtime.handle_message(
                room_id=room_id,
                text=text,
                sender_id=host_id,
                sender_name=host_id,
                owner_agent=owner_agent,
                source_context_agents=source_context_agents,
                action=runtime_action,
                external_plan_id=plan_id,
                scene_name=scene_name,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "[LANChatHostActionTrace] phase=agent_runtime_structured_action_failed room=%s plan=%s action=%s exc_type=%s",
                room_id,
                plan_id,
                action_type,
                type(exc).__name__,
            )
            return "内部执行异常已记录，当前 Runtime 执行未完成。"
        if runtime_action == "post_generation_add":
            return self._format_agent_runtime_intervention_reply(result if isinstance(result, dict) else {})
        runtime_plan = result.get("plan", {}) if isinstance(result, dict) else {}
        runtime_plan_id = str(runtime_plan.get("plan_id") or plan_id or "")
        batches = self._agent_runtime_batches_from_result(result) if isinstance(result, dict) else []
        graphs = self._agent_runtime_graphs_from_result(result)
        graph_statuses = [str(graph.get("status") or "") for graph in graphs if isinstance(graph, dict)]
        if graphs:
            self._remember_room_id(room_id)
        self._logger.info(
            "[LANChatHostActionTrace] phase=agent_runtime_structured_action_result room=%s runtime_plan=%s batches=%s graph_statuses=%s",
            room_id,
            runtime_plan_id,
            len(batches),
            ",".join(graph_statuses),
        )
        self._log_agent_runtime_evidence(
            phase="agent_runtime_structured_action_result",
            room_id=room_id,
            runtime_plan_id=runtime_plan_id,
            result=result if isinstance(result, dict) else {},
        )
        runtime_plan = result.get("plan", {}) if isinstance(result, dict) else {}
        if not runtime_plan:
            return self._format_agent_runtime_execution_reply(result if isinstance(result, dict) else {})
        return self._format_agent_runtime_execution_reply(result)

    @staticmethod
    def _runtime_scene_name_from_plan(plan: Any) -> str:
        metadata = getattr(plan, "metadata", None)
        metadata = metadata if isinstance(metadata, dict) else {}
        for value in (
            metadata.get("scene_name"),
            metadata.get("scene_path"),
            getattr(plan, "scene_name", ""),
            getattr(plan, "scene_path", ""),
        ):
            text = str(value or "").strip()
            if text:
                return text
        return ""

    def _send_coordinator_sync_system_reply(self, message: dict[str, Any], text: str) -> bool:
        safe_text = self._safe_control_text(text)
        room_id = str(message.get("room_id") or "default")
        reply_to = str(message.get("message_id") or "")
        metadata = {
            "reply_to": reply_to,
            "phase": "generation_start",
        }
        self._record_coordinator_system_reply_send_in_agent_runtime(
            phase="coordinator_system_reply_send_requested",
            room_id=room_id,
            reply_to=reply_to,
            message=safe_text,
            message_kind="action_status",
        )
        if self._corona_engine is None:
            self._record_coordinator_system_reply_send_in_agent_runtime(
                phase="coordinator_system_reply_send_failed",
                room_id=room_id,
                reply_to=reply_to,
                message=safe_text,
                message_kind="action_status",
                sent=False,
            )
            return False
        try:
            if hasattr(self._corona_engine, "network_send_system_message_ex"):
                sent = bool(self._corona_engine.network_send_system_message_ex(
                    "system",
                    "绯荤粺",
                    safe_text,
                    "action_status",
                    reply_to,
                    json.dumps(metadata, ensure_ascii=False),
                ))
                self._record_coordinator_system_reply_send_in_agent_runtime(
                    phase="coordinator_system_reply_send_succeeded" if sent else "coordinator_system_reply_send_failed",
                    room_id=room_id,
                    reply_to=reply_to,
                    message=safe_text,
                    message_kind="action_status",
                    sent=sent,
                )
                return sent
            if hasattr(self._corona_engine, "network_send_system_message"):
                sent = bool(self._corona_engine.network_send_system_message("system", "绯荤粺", safe_text))
                self._record_coordinator_system_reply_send_in_agent_runtime(
                    phase="coordinator_system_reply_send_succeeded" if sent else "coordinator_system_reply_send_failed",
                    room_id=room_id,
                    reply_to=reply_to,
                    message=safe_text,
                    message_kind="action_status",
                    sent=sent,
                )
                return sent
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to send Coordinator sync system reply: %s", type(exc).__name__)
            self._record_coordinator_system_reply_send_in_agent_runtime(
                phase="coordinator_system_reply_send_failed",
                room_id=room_id,
                reply_to=reply_to,
                message=safe_text,
                message_kind="action_status",
                sent=False,
            )
            return False
        self._record_coordinator_system_reply_send_in_agent_runtime(
            phase="coordinator_system_reply_send_failed",
            room_id=room_id,
            reply_to=reply_to,
            message=safe_text,
            message_kind="action_status",
            sent=False,
        )
        return False

    def _record_coordinator_system_reply_send_in_agent_runtime(
        self,
        *,
        phase: str,
        room_id: str,
        reply_to: str,
        message: str,
        message_kind: str,
        sent: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "message_kind": str(message_kind or "action_status"),
            "phase": "coordinator_sync",
            "reply_to": str(reply_to or ""),
        }
        if sent is not None:
            payload["sent"] = bool(sent)
        room = str(room_id or "default")
        external_plan_id = self._active_runtime_external_plan_id(room)
        return self._record_runtime_audit_event(
            event=phase,
            room_id=room,
            message=str(message or ""),
            payload=payload,
            external_plan_id=external_plan_id,
        )

    @staticmethod
    def _is_generation_start_text(text: str) -> bool:
        raw = str(text or "")
        return any(word in raw for word in (
            "运行时",
            "确认生成", "确认开始", "开始生成", "直接生成", "执行生成",
            "按照方案执行生成", "按方案执行生成", "就按方案生成", "按这个方案生成",
            "按照方案生成", "就按照这个方案生成", "就按照方案生成", "开始搭建", "开始布置",
        ))

    def _handle_coordinator_completed_intervention(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        try:
            coordinator = self._get_interaction_coordinator()
            room_id = str(trigger.get("room_id") or "default")
            plan = coordinator.active_plan_for_room(room_id)
            if plan is None or plan.status != SeedPlanStatus.COMPLETED:
                return None
            if self._is_generation_start_text(text):
                return "当前状态暂不可用，请稍后再试。"
            is_status_query = getattr(coordinator, "_is_status_query", None)
            if callable(is_status_query) and is_status_query(text):
                return None
            is_post_adjustment = getattr(coordinator, "_is_post_generation_adjustment", None)
            intent_type = coordinator._intent_type(text)
            if intent_type != "add" and (not callable(is_post_adjustment) or not is_post_adjustment(text)):
                return None
            disclosure_start = len(coordinator.disclosure_events)
            event = coordinator.ingest_message(ChatMessage(
                room_id=room_id,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                text=text,
                is_host=self._message_sender_is_host(
                    trigger,
                    sender_type=str(trigger.get("sender_type") or ""),
                ),
                agent_id=str(trigger.get("agent_id") or ""),
                agent_name=str(trigger.get("agent_name") or ""),
                metadata=self._coordinator_sync_metadata(trigger, source="lanchat_agent_completed_intervention"),
            ))
            self._emit_new_disclosure_events(coordinator, disclosure_start)
            if getattr(event, "event_type", "") in {
                "post_generation_add_routed",
                "final_adjustment_routed",
                "layout_reflow_proposal_created",
                "layout_reflow_confirmed",
                "layout_reflow_rejected",
                "layout_reflow_confirmation_failed",
            }:
                runtime_adjustment_result = self._record_completed_adjustment_in_agent_runtime(
                    room_id=room_id,
                    text=text,
                    trigger=trigger,
                    plan=plan,
                    event=event,
                )
                if getattr(event, "event_type", "") == "layout_reflow_proposal_created":
                    return str(getattr(event, "message", "") or "当前状态暂不可用，请稍后再试。")
                if getattr(event, "event_type", "") == "layout_reflow_confirmed":
                    payload = getattr(event, "payload", {}) or {}
                    if self._agent_runtime_flags.can_call_legacy_main_workflow():
                        executed = self._execute_layout_reflow_confirmation(payload)
                    else:
                        executed = self._confirm_layout_reflow_via_agent_runtime(
                            room_id=room_id,
                            plan=plan,
                            payload=payload,
                        )
                    base = str(getattr(event, "message", "") or "已记录调整。").strip()
                    return f"{base}\n{executed}" if executed else base
                if getattr(event, "event_type", "") == "layout_reflow_rejected":
                    return str(getattr(event, "message", "") or "当前状态暂不可用，请稍后再试。")
                if getattr(event, "event_type", "") == "layout_reflow_confirmation_failed":
                    return str(getattr(event, "message", "") or "当前状态暂不可用，请稍后再试。")
                if self._agent_runtime_flags.can_call_legacy_main_workflow():
                    executed = self._try_execute_completed_final_adjustment(event, trigger)
                else:
                    executed = self._completed_final_adjustment_runtime_reply(
                        room_id=room_id,
                        plan=plan,
                        event=event,
                        runtime_result=runtime_adjustment_result,
                    )
                if executed:
                    base = str(getattr(event, "message", "") or "已记录调整。").strip()
                    return f"{base}\n{executed}" if base else executed
                return str(getattr(event, "message", "") or "当前状态暂不可用，请稍后再试。")
            return None
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Coordinator completed intervention skipped: %s", type(exc).__name__)
            return None

    def _handle_coordinator_executing_intervention(self, trigger: dict[str, Any]) -> str | None:
        text = str(trigger.get("text") or "").strip()
        if not text:
            return None
        message_kind = str(trigger.get("message_kind") or "chat").strip().lower()
        if message_kind not in {"", "chat"}:
            return None
        runtime_reply = self._handle_runtime_executing_intervention(trigger)
        if runtime_reply is not None:
            return runtime_reply
        try:
            coordinator = self._get_interaction_coordinator()
            room_id = str(trigger.get("room_id") or "default")
            plan = coordinator.active_plan_for_room(room_id)
            if plan is None or plan.status != SeedPlanStatus.EXECUTING:
                return None
            if self._is_generation_start_text(text):
                return None
            is_status_query = getattr(coordinator, "_is_status_query", None)
            if callable(is_status_query) and is_status_query(text):
                return None
            intent_type = ""
            intent_fn = getattr(coordinator, "_intent_type", None)
            if callable(intent_fn):
                intent_type = str(intent_fn(text) or "").strip()
            is_post_adjustment = getattr(coordinator, "_is_post_generation_adjustment", None)
            if intent_type not in {"add", "modify", "delete"} and (
                not callable(is_post_adjustment) or not is_post_adjustment(text)
            ):
                return None
            disclosure_start = len(coordinator.disclosure_events)
            event = coordinator.ingest_message(ChatMessage(
                room_id=room_id,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                text=text,
                is_host=self._message_sender_is_host(
                    trigger,
                    sender_type=str(trigger.get("sender_type") or ""),
                ),
                agent_id=str(trigger.get("agent_id") or ""),
                agent_name=str(trigger.get("agent_name") or ""),
                metadata=self._coordinator_sync_metadata(trigger, source="lanchat_agent_executing_intervention"),
            ))
            self._emit_new_disclosure_events(coordinator, disclosure_start)
            if getattr(event, "event_type", "") in {
                "intervention_routed",
                "post_generation_add_routed",
                "final_adjustment_routed",
            }:
                self._record_completed_adjustment_in_agent_runtime(
                    room_id=room_id,
                    text=text,
                    trigger=trigger,
                    plan=plan,
                    event=event,
                )
                return str(getattr(event, "message", "") or "当前状态暂不可用，请稍后再试。")
            return None
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Coordinator executing intervention skipped: %s", type(exc).__name__)
            return None

    def _handle_runtime_executing_intervention(self, trigger: dict[str, Any]) -> str | None:
        if not self._agent_runtime_flags.agent_runtime_enabled:
            return None
        text = str(trigger.get("text") or "").strip()
        if not text or self._is_generation_start_text(text):
            return None
        room_id = str(trigger.get("room_id") or "default")
        external_plan_id = self._active_runtime_external_plan_id(room_id)
        if not external_plan_id:
            return None
        status_result = self._agent_runtime.handle_message(
            room_id=room_id,
            text="",
            sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
            sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
            action="runtime_status",
            external_plan_id=external_plan_id,
        )
        status = status_result.get("status", {}) if isinstance(status_result, dict) else {}
        if not isinstance(status, dict):
            return None
        plan_summary = status.get("plan_summary", {})
        if not isinstance(plan_summary, dict):
            return None
        plan_status = str(plan_summary.get("status") or "")
        if plan_status != "executing":
            return None

        decision = get_intent_understanding_service().classify(
            text,
            allow_llm=False,
            generation_active=True,
        )
        action_map = {
            "intervention_add": "intervention_add",
            "post_generation_add": "intervention_add",
            "intervention_modify": "intervention_modify",
            "intervention_delete": "intervention_delete",
        }
        action = action_map.get(decision.intent)
        if action is None:
            return None
        result = self._agent_runtime.handle_message(
            room_id=room_id,
            text=text,
            sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
            sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
            owner_agent=str(trigger.get("agent_name") or trigger.get("agent_id") or plan_summary.get("owner_agent") or ""),
            action=action,
            external_plan_id=external_plan_id,
        )
        queued = self._agent_runtime.handle_message(
            room_id=room_id,
            text=text,
            sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
            sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
            owner_agent=str(trigger.get("agent_name") or trigger.get("agent_id") or plan_summary.get("owner_agent") or ""),
            action="enqueue_pending_interventions",
            external_plan_id=external_plan_id,
            scene_name=self._runtime_scene_name_from_trigger(trigger),
        )
        patch = result.get("patch", {}) if isinstance(result, dict) else {}
        items = patch.get("items", []) if isinstance(patch, dict) else []
        item_preview = "、".join(str(item) for item in list(items)[:3] if str(item).strip())
        if isinstance(queued, dict) and queued.get("recorded"):
            batch = queued.get("batch", {})
            batch_index = batch.get("batch_index") if isinstance(batch, dict) else ""
            total_batches = batch.get("total_batches") if isinstance(batch, dict) else ""
            batch_suffix = ""
            if batch_index or total_batches:
                batch_suffix = f"已排入第 {batch_index or '?'}"
                if total_batches:
                    batch_suffix += f"/{total_batches}"
                batch_suffix += " 批。"
            if item_preview:
                return f"已记录该介入：{item_preview}。{batch_suffix}"
            return f"已记录该介入。{batch_suffix}"
        if item_preview:
            return f"已记录该介入：{item_preview}。等待下一批吸收。"
        return "已记录该介入，等待下一批吸收。"

    def _record_completed_adjustment_in_agent_runtime(
        self,
        *,
        room_id: str,
        text: str,
        trigger: dict[str, Any],
        plan: Any,
        event: Any,
    ) -> dict[str, Any] | None:
        if not self._agent_runtime_flags.agent_runtime_enabled:
            return None
        external_plan_id = str(getattr(plan, "plan_id", "") or "").strip()
        if not external_plan_id:
            return None
        event_type = str(getattr(event, "event_type", "") or "")
        if event_type in {"layout_reflow_rejected", "layout_reflow_confirmation_failed"}:
            return None
        try:
            plan_text = str(
                getattr(plan, "design_brief", "")
                or getattr(plan, "intent_summary", "")
                or getattr(plan, "title", "")
                or text
                or ""
            )
            self._agent_runtime.handle_message(
                room_id=str(room_id or "default"),
                text=plan_text,
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                owner_agent=str(getattr(plan, "owner_agent_name", "") or getattr(plan, "owner_agent_id", "") or ""),
                source_context_agents=list(getattr(plan, "source_context_agents", []) or []),
                action="plan",
                external_plan_id=external_plan_id,
            )
            action = "final_adjustment_request"
            event_payload = getattr(event, "payload", None)
            event_payload = event_payload if isinstance(event_payload, dict) else {}
            intervention_payload = event_payload.get("intervention")
            if not isinstance(intervention_payload, dict):
                intervention_payload = event_payload
            intent_type = str(intervention_payload.get("intent_type") or "").strip()
            if event_type == "intervention_routed":
                action = "intervention_add" if intent_type == "add" else "intervention_modify"
            elif event_type == "post_generation_add_routed":
                action = "post_generation_add"
            elif event_type == "layout_reflow_confirmed":
                action = "layout_adjustment"
            return self._agent_runtime.handle_message(
                room_id=str(room_id or "default"),
                text=str(text or ""),
                sender_id=str(trigger.get("sender_id") or trigger.get("from") or ""),
                sender_name=str(trigger.get("sender_name") or trigger.get("from") or ""),
                owner_agent=str(getattr(plan, "owner_agent_name", "") or getattr(plan, "owner_agent_id", "") or ""),
                source_context_agents=list(getattr(plan, "source_context_agents", []) or []),
                action=action,
                external_plan_id=external_plan_id,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime completed adjustment mirror skipped: %s", type(exc).__name__)
            return None

    def _completed_final_adjustment_runtime_reply(
        self,
        *,
        room_id: str,
        plan: Any,
        event: Any,
        runtime_result: dict[str, Any] | None = None,
    ) -> str:
        if not self._agent_runtime_flags.agent_runtime_enabled:
            return "AgentRuntime 未启用，最终调整未进入 Runtime。"
        external_plan_id = str(getattr(plan, "plan_id", "") or "").strip()
        if not external_plan_id:
            return "AgentRuntime 未找到关联方案，最终调整暂未记录。"
        try:
            result = runtime_result if isinstance(runtime_result, dict) else {}
            proposal = result.get("proposal", {}) if isinstance(result, dict) else {}
            proposal = proposal if isinstance(proposal, dict) else {}
            if proposal:
                proposal_id = str(proposal.get("proposal_id") or proposal.get("id") or "").strip()
                suffix = f"：{proposal_id}" if proposal_id else ""
                return f"AgentRuntime 已记录最终调整建议{suffix}，等待房主确认。"
            if result and not result.get("recorded"):
                return "AgentRuntime 未能记录最终调整，请稍后重试。"
            return "AgentRuntime 已记录最终调整，等待后续确认。"
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime final adjustment reply skipped: %s", type(exc).__name__)
            return "AgentRuntime 最终调整记录异常已记录。"

    def _confirm_layout_reflow_via_agent_runtime(
        self,
        *,
        room_id: str,
        plan: Any,
        payload: dict[str, Any],
    ) -> str:
        if not self._agent_runtime_flags.agent_runtime_enabled:
            return "AgentRuntime 未启用，布局调整未执行。"
        if not isinstance(payload, dict) or str(payload.get("status") or "") != "confirmed":
            return ""
        external_plan_id = str(getattr(plan, "plan_id", "") or "").strip()
        if not external_plan_id:
            return "AgentRuntime 未找到关联方案，布局调整未执行。"
        try:
            room_key = str(room_id or "default")
            result = self._agent_runtime.handle_message(
                room_id=room_key,
                text="确认布局调整",
                sender_id=str(payload.get("sender_id") or ""),
                sender_name=str(payload.get("sender_name") or ""),
                action="confirm_layout_adjustment",
                external_plan_id=external_plan_id,
            )
            if isinstance(result, dict) and not result.get("recorded") and not result.get("proposal"):
                return "AgentRuntime 未能记录布局调整确认。"
            return self._format_agent_runtime_layout_confirmation_reply(result if isinstance(result, dict) else {})
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime layout reflow confirmation skipped: %s", type(exc).__name__)
            return "内部异常已记录，AgentRuntime 布局调整未完成。"

    def _try_execute_completed_final_adjustment(self, event: Any, trigger: dict[str, Any]) -> str:
        if getattr(event, "event_type", "") != "final_adjustment_routed":
            return ""
        text = str(trigger.get("text") or "").strip()
        if not text:
            return ""
        payload = getattr(event, "payload", None)
        payload = payload if isinstance(payload, dict) else {}
        target_hint = str(
            payload.get("actor_id")
            or payload.get("target_actor_id")
            or payload.get("target_hint")
            or ""
        ).strip()
        actor = self._pick_completed_adjustment_actor(text, target_hint)
        if actor is not None:
            changes = self._apply_completed_adjustment_to_actor(actor, text)
            if changes:
                name = str(getattr(actor, "name", "") or target_hint or "鐩爣鐗╀綋")
                return f"已执行低风险最终调整：{name}：{'；'.join(changes)}。"
        review_changes = self._apply_completed_review_adjustments(event, trigger, text)
        if review_changes:
            return f"已执行低风险最终调整：{'；'.join(review_changes)}。"
        if self._looks_like_review_result_application(text):
            return "当前状态暂不可用，请稍后再试。"
        return ""

    def _pick_completed_adjustment_actor(self, text: str, target_hint: str = "") -> Any | None:
        actors = self._current_scene_actors()
        if not actors:
            return None
        try:
            from .terrain_component_resolver import canonical_actor_id
        except Exception:  # noqa: BLE001
            canonical_actor_id = lambda value: str(value or "").strip()  # type: ignore
        text_value = str(text or "")
        canonical_target = str(canonical_actor_id(target_hint) or "").strip()
        if canonical_target == "__terrain_boundary" or self._looks_like_boundary_adjustment(text_value):
            for actor in actors:
                name = str(getattr(actor, "name", "") or "")
                if str(canonical_actor_id(name) or "") == "__terrain_boundary":
                    return actor
        target_values = {target_hint, canonical_target}
        target_values = {str(item).strip() for item in target_values if str(item or "").strip()}
        for actor in actors:
            name = str(getattr(actor, "name", "") or "")
            display = self._completed_adjustment_display_name(name)
            canonical = str(canonical_actor_id(name) or "").strip()
            candidates = {name, display, canonical}
            if target_values & {item for item in candidates if item}:
                return actor
            if any(item and item in text_value for item in candidates):
                return actor
        return None

    def _current_scene_actors(self) -> list[Any]:
        try:
            from plugins.AITool.cai_extensions.mcp.tools.native_scene_state import native_actor_views
        except Exception:  # noqa: BLE001
            try:
                from ..cai_extensions.mcp.tools.native_scene_state import native_actor_views  # type: ignore
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Failed to import native scene actor helper: %s", type(exc).__name__)
                return []
        try:
            return list(native_actor_views(""))
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to read native scene actors: %s", type(exc).__name__)
            return []

    def _execute_layout_reflow_confirmation(self, payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict) or str(payload.get("status") or "") != "confirmed":
            return ""
        actors = [actor for actor in self._current_scene_actors() if self._is_layout_reflow_actor(actor)]
        if not actors:
            return "当前状态暂不可用，请稍后再试。"
        applied: list[str] = []
        grounded: list[str] = []
        skipped_ground: list[str] = []
        max_targets = min(len(actors), 8)
        for index, actor in enumerate(actors[:max_targets]):
            name = str(getattr(actor, "name", "") or f"鐗╀綋{index + 1}")
            try:
                current = [float(value) for value in actor.get_position()]
                while len(current) < 3:
                    current.append(0.0)
                side = -1.0 if index % 2 == 0 else 1.0
                row = index // 2
                if index == max_targets - 1 and max_targets >= 4:
                    target = [0.0, current[1], round(2.2 + 0.35 * row, 3)]
                    label = "后方焦点区"
                else:
                    target = [
                        round(side * (1.8 + 0.25 * row), 3),
                        current[1],
                        round(-1.2 + 0.7 * row, 3),
                    ]
                    label = "渚ц竟鍒嗗尯"
                target = self._clamp_layout_reflow_to_room(target, actor)
                if [round(v, 3) for v in current[:3]] != target:
                    actor.set_position(target)
                snapped, reason = self._selective_ground_actor_if_floor_supported(actor)
                if snapped:
                    grounded.append(name)
                elif reason:
                    skipped_ground.append(f"{name}: {reason}")
                final_pos = [round(float(value), 3) for value in actor.get_position()[:3]]
                if [round(v, 3) for v in current[:3]] != final_pos:
                    applied.append(f"{name} -> {label} {final_pos}")
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Layout reflow actor move skipped for %s: %s", name, type(exc).__name__)
        if not applied:
            return "当前状态暂不可用，请稍后再试。"
        suffix = ""
        if grounded:
            suffix = f" 并已贴地修正地面物体：{'、'.join(grounded[:8])}。"
        elif skipped_ground:
            suffix = " 未发现需要自动贴地的地面物体。"
        return "布局调整完成：" + "；".join(applied[:8]) + "。" + suffix

    def _ground_layout_reflow_position(self, actor: Any, target: list[float]) -> list[float]:
        grounded = [float(value) for value in target[:3]]
        while len(grounded) < 3:
            grounded.append(0.0)
        aabb = self._safe_actor_aabb(actor)
        if aabb and len(aabb) >= 6:
            try:
                current = [float(value) for value in actor.get_position()]
            except Exception:
                current = [grounded[0], grounded[1], grounded[2]]
            while len(current) < 3:
                current.append(0.0)
            min_y = float(aabb[1])
            max_y = float(aabb[4])
            is_world_aabb = min_y - 1e-4 <= current[1] <= max_y + 1e-4
            grounded[1] = current[1] - min_y if is_world_aabb else -min_y
        else:
            grounded[1] = max(0.0, grounded[1])
        grounded[1] = max(0.0, grounded[1])
        return [round(value, 3) for value in grounded[:3]]

    def _clamp_layout_reflow_to_room(self, target: list[float], actor: Any) -> list[float]:
        room_size = self._current_room_box_size()
        if len(room_size) < 3:
            return [round(float(value), 3) for value in target[:3]]
        aabb = self._safe_actor_aabb(actor)
        if aabb and len(aabb) >= 6:
            half_x = max(0.0, (float(aabb[3]) - float(aabb[0])) / 2.0)
            half_z = max(0.0, (float(aabb[5]) - float(aabb[2])) / 2.0)
        else:
            half_x = half_z = 0.25
        margin = 0.18
        width, depth = float(room_size[0]), float(room_size[1])
        min_x = -width / 2.0 + margin + half_x
        max_x = width / 2.0 - margin - half_x
        min_z = -depth / 2.0 + margin + half_z
        max_z = depth / 2.0 - margin - half_z
        out = [float(value) for value in target[:3]]
        if min_x <= max_x:
            out[0] = min(max(out[0], min_x), max_x)
        if min_z <= max_z:
            out[2] = min(max(out[2], min_z), max_z)
        return [round(value, 3) for value in out[:3]]

    def _selective_ground_actor_if_floor_supported(self, actor: Any) -> tuple[bool, str]:
        support_type = self._layout_support_type(actor)
        if support_type == "floor_supported":
            return self._snap_actor_bottom_to_ground(actor)
        if support_type in {"system", "wall_mounted", "ceiling_hung"}:
            return False, f"璺宠繃{support_type}"
        return False, "鏈煡鏀拺绫诲瀷锛屾湭鑷姩璐村湴"

    def _snap_actor_bottom_to_ground(
        self,
        actor: Any,
        *,
        ground_y: float = 0.0,
        epsilon: float = 0.03,
    ) -> tuple[bool, str]:
        aabb = self._safe_actor_aabb(actor)
        if not aabb or len(aabb) < 6:
            return False, "AABB 不可读"
        try:
            current = [float(value) for value in actor.get_position()]
        except Exception:
            return False, "位置不可读"
        while len(current) < 3:
            current.append(0.0)
        bottom_y = float(aabb[1])
        delta = bottom_y - float(ground_y)
        if abs(delta) <= float(epsilon):
            return False, "已贴地"
        current[1] = current[1] - delta
        actor.set_position([round(value, 3) for value in current[:3]])
        return True, "已贴地"

    @staticmethod
    def _layout_support_type(actor: Any) -> str:
        name = str(getattr(actor, "name", "") or "").strip()
        lowered = name.lower()
        if not name:
            return "unknown"
        if (
            lowered.startswith("__room")
            or lowered.startswith("__terrain")
            or lowered.startswith("_terrain")
            or lowered in {"terrain", "ground", "sky", "room_box", "__room_box", "__room_terrain"}
            or any(term in name for term in ("地形", "天空", "边界"))
        ):
            return "system"

        ceiling_terms = ("吊灯", "吊旗", "吊笼", "悬挂", "铁链", "天花", "ceiling", "chandelier", "hanging")
        if any(term in lowered or term in name for term in ceiling_terms):
            return "ceiling_hung"

        wall_terms = (
            "火把", "壁灯", "墙灯", "墙饰", "地图", "旗帜", "窗", "门", "招牌", "武器架",
            "torch", "sconce", "wall", "map", "flag", "window", "door", "sign", "weapon rack",
        )
        if any(term in lowered or term in name for term in wall_terms):
            return "wall_mounted"

        floor_terms = (
            "桌", "椅", "箱", "宝箱", "金币", "木桶", "酒桶", "麻袋", "床", "柜", "地毯",
            "雕像", "动物", "长椅", "沙发",
            "table", "chair", "box", "chest", "coin", "barrel", "sack", "bed", "cabinet",
            "rug", "carpet", "statue", "animal", "bench", "sofa",
        )
        if any(term in lowered or term in name for term in floor_terms):
            return "floor_supported"
        return "unknown"

    def _current_room_box_size(self) -> list[float]:
        for actor in self._current_scene_actors():
            name = str(getattr(actor, "name", "") or "").lower()
            if name not in {"__room_box", "room_box"}:
                continue
            try:
                scale = [float(value) for value in actor.get_scale()]
                if len(scale) >= 3:
                    return [abs(scale[0]), abs(scale[2]), abs(scale[1])]
            except Exception:
                pass
        return []

    @staticmethod
    def _safe_actor_aabb(actor: Any) -> list[float]:
        getter = getattr(actor, "get_aabb", None)
        if not callable(getter):
            getter = getattr(actor, "get_bounding_box", None)
        if not callable(getter):
            return []
        try:
            raw = getter()
        except Exception:
            return []
        if isinstance(raw, dict):
            values = raw.get("aabb") or raw.get("bounds") or raw.get("box")
        else:
            values = raw
        if not isinstance(values, (list, tuple)) or len(values) < 6:
            return []
        try:
            return [float(value) for value in values[:6]]
        except Exception:
            return []

    @staticmethod
    def _is_layout_reflow_actor(actor: Any) -> bool:
        name = str(getattr(actor, "name", "") or "")
        if not name:
            return False
        lowered = name.lower()
        if lowered.startswith("__room") or lowered.startswith("__terrain") or lowered.startswith("_terrain"):
            return False
        if lowered in {"terrain", "ground", "sky", "room_box"}:
            return False
        return callable(getattr(actor, "get_position", None)) and callable(getattr(actor, "set_position", None))

    def _apply_completed_review_adjustments(
        self,
        event: Any,
        trigger: dict[str, Any],
        text: str,
    ) -> list[str]:
        if not self._looks_like_review_result_application(text):
            return []
        payload = getattr(event, "payload", None)
        payload = payload if isinstance(payload, dict) else {}
        plan_id = str(payload.get("plan_id") or "").strip()
        try:
            coordinator = self._get_interaction_coordinator()
            if not plan_id:
                room_id = str(trigger.get("room_id") or payload.get("room_id") or "default")
                plan = coordinator.active_plan_for_room(room_id)
                plan_id = str(getattr(plan, "plan_id", "") or "").strip()
            if not plan_id:
                return []
            pending = list(coordinator.pending_interventions(plan_id))
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Completed review adjustment lookup failed: %s", type(exc).__name__)
            return []
        changes: list[str] = []
        for intervention in reversed(pending):
            details = getattr(intervention, "finding_details", None)
            if not isinstance(details, list) or not details:
                continue
            route = str(getattr(intervention, "apply_policy", "") or "")
            intent = str(getattr(intervention, "intent_type", "") or "")
            if route != "final_adjustment" and "review" not in intent:
                continue
            for detail in details[:8]:
                if not isinstance(detail, dict):
                    continue
                actor_hint = self._review_detail_actor_hint(detail)
                advice_text = self._review_detail_adjustment_text(detail)
                if not actor_hint and not advice_text:
                    continue
                actor = self._pick_completed_adjustment_actor(advice_text or text, actor_hint)
                if actor is None:
                    continue
                actor_changes = self._apply_completed_review_detail_to_actor(actor, detail, advice_text)
                if actor_changes:
                    name = str(getattr(actor, "name", "") or actor_hint or "鐩爣鐗╀綋")
                    changes.append(f"{name}：{'、'.join(actor_changes)}")
            if changes:
                break
        return changes

    @staticmethod
    def _looks_like_review_result_application(text: str) -> bool:
        raw = str(text or "")
        review_words = ("审查", "检查", "外观", "VLM", "vlm", "建议", "结果", "参考", "参照")
        action_words = ("按", "根据", "应用", "执行", "处理", "调整", "摆放", "修正", "优化")
        if any(word in raw for word in review_words) and any(word in raw for word in action_words):
            return True
        return (
            any(word in raw for word in ("摆放", "布局", "大小", "尺寸", "比例"))
            and any(word in raw for word in ("问题", "不对", "不合理", "有问题"))
        )

    @staticmethod
    def _review_detail_actor_hint(detail: dict[str, Any]) -> str:
        for key in ("actor_id", "target_actor_id", "object_id", "target_object_id", "target", "target_hint"):
            value = detail.get(key)
            if value:
                return str(value).strip()
        return ""

    @staticmethod
    def _review_detail_adjustment_text(detail: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in ("fix_suggestion", "suggestion", "message", "overall"):
            value = str(detail.get(key) or "").strip()
            if value:
                parts.append(value)
        issues = detail.get("issues")
        if isinstance(issues, list):
            parts.extend(str(item or "").strip() for item in issues if str(item or "").strip())
        return "；".join(parts)

    def _apply_completed_review_detail_to_actor(
        self,
        actor: Any,
        detail: dict[str, Any],
        advice_text: str,
    ) -> list[str]:
        changes: list[str] = []
        scale_vector = detail.get("scale_correction")
        if isinstance(scale_vector, list) and len(scale_vector) >= 3:
            try:
                factors = [float(value) for value in scale_vector[:3]]
                if any(abs(value - 1.0) > 1e-3 for value in factors):
                    current = [float(v) for v in actor.get_scale()]
                    while len(current) < 3:
                        current.append(1.0)
                    new_scale = [
                        round(max(0.02, min(20.0, current[index] * factors[index])), 4)
                        for index in range(3)
                    ]
                    actor.set_scale(new_scale)
                    changes.append(f"缂╂斁璋冩暣涓?{new_scale}")
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Completed VLM review scale vector adjustment failed: %s", type(exc).__name__)
        text_changes = self._apply_completed_adjustment_to_actor(actor, advice_text)
        for item in text_changes:
            if item not in changes:
                changes.append(item)
        return changes

    @staticmethod
    def _completed_adjustment_display_name(name: str) -> str:
        display = str(name or "")
        for prefix in ("__shell_", "__asset_"):
            if display.startswith(prefix):
                return display[len(prefix):]
        return display

    @staticmethod
    def _looks_like_boundary_adjustment(text: str) -> bool:
        return any(token in str(text or "") for token in (
            "_terrain_boundary",
            "__terrain_boundary",
            "terrain_boundary",
            "鍦板舰杈圭晫",
            "鍦哄湴杈圭晫",
            "杈圭晫",
            "鏍呮爮",
            "鍥存爮",
        ))

    def _apply_completed_adjustment_to_actor(self, actor: Any, text: str) -> list[str]:
        try:
            from .terrain_component_resolver import canonical_actor_id
        except Exception:  # noqa: BLE001
            canonical_actor_id = lambda value: str(value or "").strip()  # type: ignore
        name = str(getattr(actor, "name", "") or "")
        canonical = str(canonical_actor_id(name) or "").strip()
        changes: list[str] = []
        raw = str(text or "")
        if canonical == "__terrain_boundary":
            changes.extend(self._apply_completed_boundary_adjustment(actor, raw))
        scale_factor = self._completed_adjustment_scale_factor(raw)
        if scale_factor is not None and canonical != "__terrain_boundary":
            try:
                current = [float(v) for v in actor.get_scale()]
                while len(current) < 3:
                    current.append(1.0)
                new_scale = [round(max(0.02, value * scale_factor), 4) for value in current[:3]]
                actor.set_scale(new_scale)
                changes.append(f"缩放调整为 {new_scale}")
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Completed final adjustment scale failed: %s", type(exc).__name__)
        if any(word in raw for word in ("贴地", "落地", "悬空", "浮空", "飘起", "飘起来", "离地", "没贴地", "穿模", "接地")):
            try:
                current = [float(v) for v in actor.get_position()]
                while len(current) < 3:
                    current.append(0.0)
                grounded = self._ground_layout_reflow_position(actor, current)
                if [round(v, 3) for v in current[:3]] != grounded:
                    actor.set_position(grounded)
                    changes.append("已校正贴地高度")
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Completed final adjustment grounding failed: %s", type(exc).__name__)
        return changes

    def _apply_completed_boundary_adjustment(self, actor: Any, text: str) -> list[str]:
        changes: list[str] = []
        if any(word in text for word in ("低矮", "矮一点", "太高", "别太高", "奇怪", "不自然", "藤蔓", "木栏", "围栏", "栅栏")):
            try:
                current = [float(v) for v in actor.get_scale()]
                while len(current) < 3:
                    current.append(1.0)
                new_scale = [
                    round(max(0.02, current[0]), 4),
                    round(min(max(0.02, current[1]), 0.55), 4),
                    round(max(0.02, current[2]), 4),
                ]
                actor.set_scale(new_scale)
                changes.append(f"边界高度调整为 {new_scale}")
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Completed boundary scale adjustment failed: %s", type(exc).__name__)
        if any(word in text for word in ("藤蔓", "木栏", "木质", "温暖", "自然")):
            rgb = [0.34, 0.45, 0.18] if "藤蔓" in text else [0.42, 0.25, 0.12]
            if self._try_completed_actor_color(actor, rgb):
                changes.append("边界颜色调整为自然木藤色")
        return changes

    @staticmethod
    def _completed_adjustment_scale_factor(text: str) -> float | None:
        numeric = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*倍", str(text or ""))
        if numeric and any(word in text for word in ("放大", "变大", "扩大")):
            return max(0.05, float(numeric.group(1)))
        if numeric and any(word in text for word in ("缩小", "变小")):
            return max(0.05, 1.0 / max(0.05, float(numeric.group(1))))
        if "一半" in text and any(word in text for word in ("缩小", "变小")):
            return 0.5
        if any(word in text for word in ("太大", "过大", "偏大", "尺寸大", "比例大")):
            return 0.8
        if any(word in text for word in ("太小", "过小", "偏小", "尺寸小", "比例小")):
            return 1.2
        if any(word in text for word in ("大一点", "变大", "放大")):
            return 1.35
        if any(word in text for word in ("小一点", "变小", "缩小")):
            return 0.75
        return None

    @staticmethod
    def _try_completed_actor_color(actor: Any, rgb: list[float]) -> bool:
        candidates = [
            getattr(actor, "set_color", None),
            getattr(actor, "set_diffuse", None),
        ]
        optics = getattr(actor, "_optics", None)
        if optics is not None:
            candidates.extend([
                getattr(optics, "set_color", None),
                getattr(optics, "set_diffuse", None),
                getattr(optics, "set_base_color", None),
            ])
        for setter in candidates:
            if not callable(setter):
                continue
            try:
                setter(rgb)
                return True
            except TypeError:
                try:
                    setter(float(rgb[0]), float(rgb[1]), float(rgb[2]))
                    return True
                except Exception:
                    continue
            except Exception:
                continue
        return False

    @staticmethod
    def _gm_pace_action_from_trigger(trigger: dict[str, Any]) -> str:
        agent_id = str(trigger.get("agent_id") or trigger.get("target_agent_id") or "").lower()
        agent_name = str(trigger.get("agent_name") or "").lower()
        text = str(trigger.get("text") or "").strip()
        if not (agent_id == "gm" or agent_name in {"gm", "主持人", "裁判", "game master"} or text.startswith("@GM")):
            return ""
        if re.search(r"\b(?:gm-\d+|fa-[\w.-]+|cr-[\w.-]+)\b", text, flags=re.I):
            return ""
        if any(word in text for word in ("暂停", "先停", "等一下")):
            return "pause"
        if any(word in text for word in ("继续", "恢复")):
            return "resume"
        if False:
            return "discuss"
        return ""

    @staticmethod
    def _gm_clarification_question_from_trigger(trigger: dict[str, Any]) -> str:
        agent_id = str(trigger.get("agent_id") or trigger.get("target_agent_id") or "").lower()
        agent_name = str(trigger.get("agent_name") or "").lower()
        text = str(trigger.get("text") or "").strip()
        if not (agent_id == "gm" or agent_name in {"gm", "主持人", "裁判", "game master"} or text.startswith("@GM")):
            return ""
        if re.search(r"\b(?:gm-\d+|fa-[\w.-]+|cr-[\w.-]+)\b", text, flags=re.I):
            return ""
        if False:
            return ""
        question = re.sub(r"^@GM\s*", "", text, flags=re.I).strip()
        # syntax-repaired damaged text line

    @classmethod
    def _trusted_host_control(cls, trigger: dict[str, Any]) -> bool | None:
        metadata = cls._metadata_from_trigger(trigger)
        view = {**metadata, **(trigger or {})}
        for key in ("sender_role", "room_role", "role"):
            if key not in view:
                continue
            role = str(view.get(key) or "").strip().lower()
            if role:
                return role in {"host", "owner", "room_host", "鎴夸富"}
        for key in ("is_host", "is_room_host", "sender_is_host"):
            if key in view:
                return bool(view.get(key))
        return None

    @staticmethod
    def _metadata_from_trigger(trigger: dict[str, Any]) -> dict[str, Any]:
        metadata = (trigger or {}).get("metadata")
        if isinstance(metadata, dict):
            return metadata
        raw = (trigger or {}).get("metadata_json")
        if not raw:
            return {}
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(str(raw))
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _coordinator_sync_metadata(self, message: dict[str, Any], *, source: str) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "message_id": str(message.get("message_id") or ""),
            "source": source,
        }
        raw_metadata = self._metadata_from_trigger(message)
        for key in (
            "actor_id",
            "target_actor_id",
            "object_id",
            "target_object_id",
            "actor_version",
            "target_hint",
            "workspace_mode",
            "draft_action",
            "target_agent_id",
            "target_agent_name",
            "target_agent_ids",
            "target_agent_names",
            "target_plan_id",
            "batch_id",
            "runtime_batch_id",
            "target_batch_id",
            "target_scope",
        ):
            value = raw_metadata.get(key)
            if value is not None and value != "":
                metadata[key] = value
        for key in ("source_user_id", "correlation_id"):
            value = message.get(key)
            if value:
                metadata[key] = str(value)
        return metadata

    def _normalize_coordinator_target_metadata(
        self,
        message: dict[str, Any],
        text: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(metadata or {})
        mention = self._explicit_agent_mention(text)
        if mention:
            agent_id, agent_name = self._resolve_lanchat_agent_mention(mention)
            normalized["target_scope"] = "agent"
            normalized["target_agent_name"] = agent_name or mention
            normalized["target_agent_id"] = agent_id or str(message.get("target_agent_id") or message.get("agent_id") or agent_name or mention)
        elif str(message.get("target_agent_id") or "").strip() or str(message.get("target_agent_name") or "").strip():
            normalized.setdefault("target_scope", "agent")
            normalized["target_agent_id"] = str(message.get("target_agent_id") or "").strip()
            normalized["target_agent_name"] = str(message.get("target_agent_name") or "").strip()
        source_context = self._source_context_agent_from_text(text)
        if source_context and source_context != str(normalized.get("target_agent_name") or ""):
            normalized["source_context_agent"] = source_context
        return normalized

    @staticmethod
    def _explicit_agent_mention(text: str) -> str:
        match = re.search(r"@([^\s锛?銆傦紱;锛?]+)", str(text or ""))
        return match.group(1).strip() if match else ""

    @staticmethod
    def _source_context_agent_from_text(text: str) -> str:
        raw = str(text or "")
        match = re.search(
            r"(?:在|基于|按照|参考)\s*@?([^，。；;、\s@]+?)\s*(?:的)?(?:方案|设计|想法|基础)?(?:基础上)?(?:继续|进行|进一步|来|再|调整|修改|改进|整理|生成|$)",
            raw,
        )
        if match:
            return match.group(1).strip()
        match = re.search(
            r"@?([^，。；;、\s@]+?)\s*(?:方案|设计|想法)?基础上",
            raw,
        )
        return match.group(1).strip() if match else ""

    def _resolve_lanchat_agent_mention(self, mention: str) -> tuple[str, str]:
        wanted = str(mention or "").strip()
        if not wanted:
            return "", ""
        roster = []
        getter = getattr(self._corona_engine, "network_lanchat_agents_snapshot", None)
        if callable(getter):
            try:
                roster = list(getter() or [])
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Failed to read LANChat agent roster: %s", type(exc).__name__)
        for item in roster:
            if not isinstance(item, dict):
                continue
            agent_id = str(item.get("agent_id") or item.get("id") or "").strip()
            agent_name = str(item.get("name") or item.get("agent_name") or "").strip()
            if wanted in {agent_id, agent_name}:
                return agent_id, agent_name
        return "", wanted

    def _apply_generation_options_from_message(self, message: dict[str, Any]) -> None:
        metadata = self._metadata_from_trigger(message)
        options = metadata.get("generation_options") if isinstance(metadata, dict) else None
        if not isinstance(options, dict):
            return
        is_host = bool(
            self._message_sender_is_host(
                message,
                sender_type=str(message.get("sender_type") or metadata.get("sender_role") or ""),
            )
            or metadata.get("is_host")
        )
        if not is_host:
            return
        enabled = bool(options.get("vlm_enabled"))
        raw_targets = options.get("vlm_max_targets", 1 if enabled else 0)
        try:
            targets = int(raw_targets)
        except Exception:
            targets = 1 if enabled else 0
        targets = max(0, min(4, targets))
        if enabled and targets <= 0:
            targets = 1
        os.environ["PROGRESSIVE_VLM_MAX_TARGETS"] = str(targets if enabled else 0)
        self._logger.info(
            "LANChat generation option updated: PROGRESSIVE_VLM_MAX_TARGETS=%s",
            os.environ["PROGRESSIVE_VLM_MAX_TARGETS"],
        )

    @staticmethod
    def _coordinator_sync_dedupe_key(message: dict[str, Any], *, source: str) -> str:
        message_id = str(message.get("message_id") or "").strip()
        if message_id:
            return f"id:{message_id}"
        text = str(message.get("text") or "").strip()
        if not text:
            return ""
        parts = (
            "fallback",
            str(source or "lanchat_direct").strip(),
            str(message.get("room_id") or "default").strip(),
            str(message.get("sender_id") or message.get("from") or "").strip(),
            str(message.get("sender_type") or "user").strip().lower(),
            str(message.get("message_kind") or "chat").strip().lower(),
            text,
        )
        return "|".join(parts)

    def _set_runtime_mode_for_pace(self, action: str, *, trigger: dict[str, Any] | None = None) -> None:
        mode = {"pause": "PAUSED", "resume": "EXECUTING", "discuss": "DISCUSSING"}.get(action)
        if not mode:
            return
        runtime_action = {"pause": "pause_generation", "resume": "resume_generation"}.get(action)
        if runtime_action:
            message = trigger or {}
            room_id = str(message.get("room_id") or "default")
            external_plan_id = self._active_runtime_external_plan_id(room_id)
            try:
                if runtime_action == "pause_generation":
                    self._agent_runtime.handle_message(
                        room_id=room_id,
                        text=str(message.get("text") or action),
                        sender_id=str(message.get("sender_id") or message.get("from") or ""),
                        sender_name=str(message.get("sender_name") or message.get("from") or ""),
                        action="pause_generation",
                        external_plan_id=external_plan_id,
                    )
                elif runtime_action == "resume_generation":
                    self._agent_runtime.handle_message(
                        room_id=room_id,
                        text=str(message.get("text") or action),
                        sender_id=str(message.get("sender_id") or message.get("from") or ""),
                        sender_name=str(message.get("sender_name") or message.get("from") or ""),
                        action="resume_generation",
                        external_plan_id=external_plan_id,
                    )
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("AgentRuntime pace command mirror skipped: %s", type(exc).__name__)
        try:
            from .lanchat_scene_runtime import get_lanchat_scene_runtime
            get_lanchat_scene_runtime().set_mode(mode)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("LANChat scene runtime pace update skipped: %s", type(exc).__name__)

    def _sync_trigger_history_to_coordinator(self, trigger: dict[str, Any]) -> None:
        history = trigger.get("history") or []
        if not isinstance(history, list):
            return
        room_id = str(trigger.get("room_id") or "default")
        self._remember_room_id(room_id)
        current_message_id = str(trigger.get("message_id") or "")
        for item in history:
            if not isinstance(item, dict):
                continue
            message_id = str(item.get("message_id") or "")
            if not message_id or message_id == current_message_id:
                continue
            if message_id in self._coordinator_seen_message_ids:
                continue
            payload = dict(item)
            payload["room_id"] = str(payload.get("room_id") or room_id)
            self.sync_chat_message_to_coordinator(
                payload,
                source="lanchat_history_snapshot",
                emit_disclosure=False,
            )

    def _broadcast_confirmed_action(self, payload: dict[str, Any] | None) -> None:
        if not payload:
            return
        if str(payload.get("action_type") or "") == "final_adjustment_confirmation":
            self._record_final_adjustment_confirmation(payload)
            return
        if str(payload.get("action_type") or "") == "conflict_resolution_confirmation":
            self._record_conflict_resolution_confirmation(payload)
            return
        if payload.get("status") != "confirmed":
            return
        if str(payload.get("action_type") or "") == "discussion_only":
            return
        if not self._is_confirmed_action_payload_runtime_approved(payload):
            self._record_unapproved_confirmed_action_block(payload, phase="broadcast")
            self._logger.warning(
                "Blocked unapproved confirmed action payload from LANChat agent: action=%s execution=%s plan_id=%s",
                str(payload.get("action_type") or ""),
                str(payload.get("execution") or ""),
                str(payload.get("plan_id") or ""),
            )
            return
        if hasattr(self._corona_engine, "network_broadcast_intent"):
            source_user_id = str(payload.get("source_user_id") or "unknown")
            tooltip = self._safe_control_text(payload.get("intent_text") or payload.get("proposal_id") or "")
            try:
                self._corona_engine.network_broadcast_intent(
                    source_user_id,
                    tooltip,
                    [0.0, 0.0, 0.0],
                    "confirmed_gm_action",
                )
            except Exception as exc:
                self._logger.debug("Failed to broadcast confirmed GM action: %s", type(exc).__name__)

        self._execute_confirmed_action(payload)

    def _filter_confirmed_action_payload_for_runtime(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if self._is_confirmed_action_payload_runtime_approved(payload):
            return payload
        self._record_unapproved_confirmed_action_block(payload, phase="reply_metadata")
        self._logger.warning(
            "Dropped unapproved confirmed action payload before reply metadata: action=%s execution=%s plan_id=%s",
            str((payload or {}).get("action_type") or ""),
            str((payload or {}).get("execution") or ""),
            str((payload or {}).get("plan_id") or ""),
        )
        return None

    def _is_confirmed_action_payload_runtime_approved(self, payload: dict[str, Any] | None) -> bool:
        if not payload:
            return True
        action_type = str(payload.get("action_type") or "")
        if action_type in {"final_adjustment_confirmation", "conflict_resolution_confirmation"}:
            return True
        if payload.get("status") != "confirmed":
            return True
        if action_type == "discussion_only":
            return True
        if self._agent_runtime_flags.can_call_legacy_main_workflow():
            return True
        execution = str(payload.get("execution") or "")
        if execution not in {"agent_runtime_structured", "coordinator_structured"}:
            return False
        return bool(payload.get("runtime_payload_prepared_by_worker"))

    def _record_unapproved_confirmed_action_block(
        self,
        payload: dict[str, Any] | None,
        *,
        phase: str,
    ) -> None:
        data = dict(payload or {})
        safe_payload = {
            "phase": str(phase or ""),
            "action_type": str(data.get("action_type") or ""),
            "execution": str(data.get("execution") or ""),
            "plan_id": str(data.get("plan_id") or ""),
            "room_id": str(data.get("room_id") or ""),
            "source_user_id": str(data.get("source_user_id") or ""),
            "status": str(data.get("status") or ""),
            "runtime_payload_prepared_by_worker": bool(data.get("runtime_payload_prepared_by_worker")),
        }
        result = self._record_runtime_audit_event(
            event="unapproved_confirmed_action_blocked",
            room_id=str(data.get("room_id") or "default"),
            message="Blocked confirmed action payload that was not prepared by AgentRuntime.",
            payload=safe_payload,
        )
        if not result.get("recorded"):
            self._logger.debug("AgentRuntime unapproved action audit skipped: %s", result.get("reason") or "unknown")

    @classmethod
    def _sanitize_control_payload(cls, value: Any) -> Any:
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                normalized = str(key or "").lower()
                if any(marker in normalized for marker in _SENSITIVE_WORKER_PAYLOAD_KEYS):
                    continue
                sanitized[key] = cls._sanitize_control_payload(item)
            return sanitized
        if isinstance(value, list):
            return [cls._sanitize_control_payload(item) for item in value]
        if isinstance(value, tuple):
            return [cls._sanitize_control_payload(item) for item in value]
        if isinstance(value, str):
            return cls._safe_control_text(value)
        return value

    @staticmethod
    def _safe_control_text(value: Any) -> str:
        text = str(value or "")
        lower = text.lower()
        cut_points = [
            lower.find(marker)
            for marker in _SENSITIVE_WORKER_TEXT_MARKERS
            if lower.find(marker) >= 0
        ]
        if not cut_points:
            return text
        first = min(cut_points)
        keep = text[:first].strip(" \t\r\n,;；。")
        return keep or text

    def _record_final_adjustment_confirmation(self, payload: dict[str, Any]) -> None:
        coordinator = self._interaction_coordinator
        if coordinator is None:
            return
        proposal_id = str(payload.get("proposal_id") or "").strip()
        decision = str(payload.get("decision") or "confirm").strip().lower()
        host_id = str(payload.get("source_user_id") or payload.get("confirmed_by") or "").strip()
        disclosure_start = len(coordinator.disclosure_events)
        confirm = getattr(coordinator, "confirm_final_adjustment_conflict", None)
        if not callable(confirm):
            return
        try:
            result = confirm(proposal_id, host_id, decision=decision)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to record final adjustment confirmation: %s", type(exc).__name__)
            return
        self._record_final_adjustment_confirmation_in_agent_runtime(result, payload)
        emitted = self._emit_new_disclosure_events(coordinator, disclosure_start)
        self._start_coordinator_disclosure_watch(coordinator, disclosure_start + emitted)

    def _record_final_adjustment_confirmation_in_agent_runtime(
        self,
        result: Any,
        payload: dict[str, Any],
    ) -> None:
        if not self._agent_runtime_flags.agent_runtime_enabled:
            return
        result_payload = getattr(result, "payload", None)
        result_payload = result_payload if isinstance(result_payload, dict) else {}
        proposal = result_payload.get("proposal")
        proposal = proposal if isinstance(proposal, dict) else {}
        if not proposal:
            return
        room_id = str(proposal.get("room_id") or payload.get("room_id") or "default")
        external_plan_id = str(proposal.get("plan_id") or payload.get("plan_id") or "").strip()
        try:
            runtime_payload = dict(proposal)
            runtime_payload.update(
                {
                    "proposal": proposal,
                    "proposal_id": str(proposal.get("proposal_id") or payload.get("proposal_id") or ""),
                    "decision": str(proposal.get("status") or payload.get("decision") or ""),
                }
            )
            self._agent_runtime.handle_message(
                room_id=room_id,
                text="最终调整确认",
                sender_id=str(payload.get("source_user_id") or payload.get("confirmed_by") or ""),
                sender_name=str(proposal.get("confirmed_by") or payload.get("source_user_id") or payload.get("confirmed_by") or ""),
                action="final_adjustment_confirmation",
                external_plan_id=external_plan_id,
                sync_event=runtime_payload,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("AgentRuntime final adjustment confirmation mirror skipped: %s", type(exc).__name__)

    def _record_conflict_resolution_confirmation(self, payload: dict[str, Any]) -> None:
        coordinator = self._interaction_coordinator
        if coordinator is None:
            return
        proposal_id = str(payload.get("proposal_id") or "").strip()
        decision = str(payload.get("decision") or "confirm").strip().lower()
        host_id = str(payload.get("source_user_id") or payload.get("confirmed_by") or "").strip()
        disclosure_start = len(coordinator.disclosure_events)
        handler_name = "reject_conflict_resolution" if decision in {"reject", "rejected", "no", "cancel"} else "confirm_conflict_resolution"
        handler = getattr(coordinator, handler_name, None)
        if not callable(handler):
            return
        try:
            handler(proposal_id, host_id)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to record conflict resolution confirmation: %s", type(exc).__name__)
            return
        emitted = self._emit_new_disclosure_events(coordinator, disclosure_start)
        self._start_coordinator_disclosure_watch(coordinator, disclosure_start + emitted)

    def _execute_confirmed_action(self, payload: dict[str, Any]) -> None:
        if (
            str(payload.get("execution") or "") == "agent_runtime_structured"
            and str(payload.get("action_type") or "") in {"start_generation", "post_generation_add"}
        ):
            reply = self._execute_structured_host_action_via_agent_runtime(payload)
            self._send_runtime_structured_action_reply(payload, reply)
            return
        executor = self._get_host_action_executor()
        if executor is None or not hasattr(executor, "enqueue_and_process"):
            return
        coordinator = self._interaction_coordinator
        disclosure_start = len(coordinator.disclosure_events) if coordinator is not None else 0
        try:
            executor.enqueue_and_process(payload)
        except Exception as exc:
            self._logger.debug("Failed to execute confirmed GM action: %s", type(exc).__name__)
        finally:
            if coordinator is not None:
                emitted = self._emit_new_disclosure_events(coordinator, disclosure_start)
                self._start_coordinator_disclosure_watch(coordinator, disclosure_start + emitted)
            self._emit_generation_scheduler_disclosure()

    def _send_runtime_structured_action_reply(self, payload: dict[str, Any], text: str | None) -> bool:
        if self._corona_engine is None:
            return False
        safe_text = self._safe_control_text(text or "")
        if not safe_text:
            return False
        metadata = {
            "action_type": str(payload.get("action_type") or ""),
            "execution": "agent_runtime_structured",
            "plan_id": str(payload.get("plan_id") or ""),
            "room_id": str(payload.get("room_id") or "default"),
            "phase": "agent_runtime_execution_result",
        }
        correlation_id = str(payload.get("proposal_id") or payload.get("plan_id") or "")
        try:
            if hasattr(self._corona_engine, "network_send_system_message_ex"):
                return bool(self._corona_engine.network_send_system_message_ex(
                    "gm-system",
                    "GM",
                    safe_text,
                    "action_status",
                    correlation_id,
                    json.dumps(metadata, ensure_ascii=False),
                ))
            if hasattr(self._corona_engine, "network_send_system_message"):
                return bool(self._corona_engine.network_send_system_message("gm-system", "GM", safe_text))
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to send AgentRuntime structured action reply: %s", type(exc).__name__)
        return False

    def _emit_new_disclosure_events(self, coordinator: InteractionCoordinator, start_index: int) -> int:
        if self._corona_engine is None:
            return 0
        if hasattr(coordinator, "disclosure_events_since"):
            events, cursor_advance = coordinator.disclosure_events_since(start_index)
        else:
            events = coordinator.disclosure_events[start_index:]
            cursor_advance = len(events)
        if not events:
            return cursor_advance
        for event in events:
            if getattr(event, "audience", "") not in {"participant", "host"}:
                continue
            payload = event.as_dict()
            text = self._broadcast_text_for_disclosure(payload)
            if not text:
                continue
            if self._try_send_targeted_host_disclosure(payload, text):
                continue
            metadata_payload = payload
            metadata_envelope = {"disclosure": metadata_payload}
            if str(payload.get("audience") or "") == "host":
                metadata_payload = self._host_disclosure_broadcast_payload(payload, text)
                metadata_envelope = {
                    "disclosure": metadata_payload,
                    "host_disclosure": self._host_disclosure_fallback_payload(payload, text),
                }
            metadata = json.dumps(metadata_envelope, ensure_ascii=False)
            try:
                if hasattr(self._corona_engine, "network_send_system_message_ex"):
                    self._record_disclosure_event_send_in_agent_runtime(
                        phase="disclosure_event_send_requested",
                        payload=payload,
                        message=text,
                        message_kind="action_status",
                        channel="broadcast_ex",
                    )
                    sent = bool(self._corona_engine.network_send_system_message_ex(
                        "system",
                        "绯荤粺",
                        text,
                        "action_status",
                        str(payload.get("event_id") or ""),
                        metadata,
                    ))
                    self._record_disclosure_event_send_in_agent_runtime(
                        phase="disclosure_event_send_succeeded" if sent else "disclosure_event_send_failed",
                        payload=payload,
                        message=text,
                        message_kind="action_status",
                        channel="broadcast_ex",
                        sent=sent,
                    )
                elif hasattr(self._corona_engine, "network_send_system_message"):
                    self._record_disclosure_event_send_in_agent_runtime(
                        phase="disclosure_event_send_requested",
                        payload=payload,
                        message=text,
                        message_kind="action_status",
                        channel="broadcast",
                    )
                    sent = bool(self._corona_engine.network_send_system_message("system", "绯荤粺", text))
                    self._record_disclosure_event_send_in_agent_runtime(
                        phase="disclosure_event_send_succeeded" if sent else "disclosure_event_send_failed",
                        payload=payload,
                        message=text,
                        message_kind="action_status",
                        channel="broadcast",
                        sent=sent,
                    )
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Failed to emit LANChat disclosure event: %s", type(exc).__name__)
                self._record_disclosure_event_send_in_agent_runtime(
                    phase="disclosure_event_send_failed",
                    payload=payload,
                    message=text,
                    message_kind="action_status",
                    channel="broadcast",
                    sent=False,
                )
        return cursor_advance

    def _try_send_targeted_host_disclosure(self, payload: dict[str, Any], text: str) -> bool:
        if str(payload.get("audience") or "") != "host":
            return False
        target_sender_id = str(
            payload.get("target_user_id")
            or (payload.get("metadata") or {}).get("target_user_id")
            or "host"
        )
        metadata = json.dumps({"disclosure": payload}, ensure_ascii=False)
        for method_name in (
            "network_send_system_message_to_host_ex",
            "network_send_system_message_to_user_ex",
        ):
            sender = getattr(self._corona_engine, method_name, None)
            if not callable(sender):
                continue
            try:
                self._record_disclosure_event_send_in_agent_runtime(
                    phase="disclosure_event_send_requested",
                    payload=payload,
                    message=text,
                    message_kind="action_status",
                    channel=method_name,
                )
                if method_name.endswith("_to_user_ex"):
                    sent = bool(sender(
                        target_sender_id,
                        "system",
                        "绯荤粺",
                        text,
                        "action_status",
                        str(payload.get("event_id") or ""),
                        metadata,
                    ))
                else:
                    sent = bool(sender(
                        "system",
                        "绯荤粺",
                        text,
                        "action_status",
                        str(payload.get("event_id") or ""),
                        metadata,
                    ))
                self._record_disclosure_event_send_in_agent_runtime(
                    phase="disclosure_event_send_succeeded" if sent else "disclosure_event_send_failed",
                    payload=payload,
                    message=text,
                    message_kind="action_status",
                    channel=method_name,
                    sent=sent,
                )
                if sent:
                    return True
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Failed to emit targeted host disclosure via %s: %s", method_name, type(exc).__name__)
                self._record_disclosure_event_send_in_agent_runtime(
                    phase="disclosure_event_send_failed",
                    payload=payload,
                    message=text,
                    message_kind="action_status",
                    channel=method_name,
                    sent=False,
                )
        return False

    def _record_disclosure_event_send_in_agent_runtime(
        self,
        *,
        phase: str,
        payload: dict[str, Any],
        message: str,
        message_kind: str,
        channel: str,
        sent: bool | None = None,
    ) -> dict[str, Any]:
        room_id = str(payload.get("room_id") or "default")
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        external_plan_id = str(
            payload.get("external_plan_id")
            or payload.get("plan_id")
            or metadata.get("plan_id")
            or ""
        )
        if not external_plan_id:
            external_plan_id = self._active_runtime_external_plan_id(room_id)
        safe_payload: dict[str, Any] = {
            "event_id": str(payload.get("event_id") or ""),
            "audience": str(payload.get("audience") or ""),
            "stage": str(payload.get("stage") or ""),
            "progress": int(payload.get("progress") or 0),
            "message_kind": str(message_kind or "action_status"),
            "channel": str(channel or ""),
            "external_plan_id": external_plan_id,
        }
        if sent is not None:
            safe_payload["sent"] = bool(sent)
        return self._record_runtime_audit_event(
            event=phase,
            room_id=room_id,
            message=str(message or ""),
            payload=safe_payload,
            external_plan_id=external_plan_id,
        )

    @staticmethod
    def _host_disclosure_broadcast_payload(payload: dict[str, Any], text: str) -> dict[str, Any]:
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        safe_metadata = {
            key: metadata.get(key)
            for key in ("proposal_id", "requires_conflict_resolution", "requires_confirmation")
            if key in metadata
        }
        return {
            "event_id": payload.get("event_id"),
            "room_id": payload.get("room_id"),
            "audience": "participant",
            "stage": payload.get("stage"),
            "progress": payload.get("progress"),
            "public_message": text,
            "available_actions": [],
            "requires_confirmation": False,
            "metadata": safe_metadata,
        }

    @staticmethod
    def _host_disclosure_fallback_payload(payload: dict[str, Any], text: str) -> dict[str, Any]:
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        intervention = metadata.get("intervention") if isinstance(metadata.get("intervention"), dict) else {}
        proposal_id = (
            payload.get("proposal_id")
            or metadata.get("proposal_id")
            or intervention.get("proposal_id")
            or ""
        )
        safe_metadata = {
            key: metadata.get(key)
            for key in ("proposal_id", "requires_conflict_resolution", "requires_confirmation", "apply_policy")
            if key in metadata
        }
        if intervention:
            safe_metadata["intervention"] = {
                key: intervention.get(key)
                for key in ("proposal_id", "requires_conflict_resolution", "apply_policy", "intent_type")
                if key in intervention
            }
        available_actions = payload.get("available_actions")
        return {
            "event_id": payload.get("event_id"),
            "room_id": payload.get("room_id"),
            "audience": "host",
            "stage": payload.get("stage"),
            "progress": payload.get("progress"),
            "public_message": payload.get("public_message") or text,
            "available_actions": list(available_actions) if isinstance(available_actions, list) else [],
            "requires_confirmation": bool(payload.get("requires_confirmation")),
            "requires_conflict_resolution": bool(
                payload.get("requires_conflict_resolution")
                or metadata.get("requires_conflict_resolution")
                or intervention.get("requires_conflict_resolution")
            ),
            "proposal_id": proposal_id,
            "metadata": safe_metadata,
            "created_at": payload.get("created_at"),
        }

    def _start_coordinator_disclosure_watch(
        self,
        coordinator: InteractionCoordinator,
        start_index: int,
        *,
        duration_seconds: float = 30.0,
        interval_seconds: float = 0.05,
    ) -> None:
        if self._corona_engine is None:
            return

        def _watch() -> None:
            cursor = int(start_index)
            deadline = time.time() + max(0.1, float(duration_seconds))
            while not self._stop_event.is_set() and time.time() < deadline:
                emitted = self._emit_new_disclosure_events(coordinator, cursor)
                if emitted:
                    cursor += emitted
                time.sleep(max(0.01, float(interval_seconds)))

        threading.Thread(
            target=_watch,
            name="LANChatDisclosureWatch",
            daemon=True,
        ).start()

    @staticmethod
    def _broadcast_text_for_disclosure(payload: dict[str, Any]) -> str:
        """Return text safe for a room-wide system message."""
        audience = str(payload.get("audience") or "")
        if audience == "host":
            if payload.get("requires_confirmation"):
                return "有一项需要房主确认的事项。"
            return "当前状态暂不可用，请稍后再试。"
        return str(payload.get("public_message") or "")

    def _emit_generation_scheduler_disclosure(self) -> None:
        if self._corona_engine is None:
            return
        room_ids = sorted(self._active_room_ids)
        snapshots: list[tuple[str, dict[str, Any]]] = []
        if room_ids:
            for room_id in room_ids:
                snapshot = self.generation_scheduler_session_snapshot(room_id)
                if snapshot.get("available"):
                    snapshots.append((room_id, snapshot))
        else:
            snapshot = self.generation_scheduler_snapshot()
            if snapshot.get("available"):
                snapshots.append(("", snapshot))
        for room_id, snapshot in snapshots:
            self._emit_generation_scheduler_snapshot_disclosure(room_id, snapshot)

    def _emit_generation_scheduler_snapshot_disclosure(self, room_id: str, snapshot: dict[str, Any]) -> None:
        queued_count = int(snapshot.get("queued_count") or 0)
        total_jobs = int(snapshot.get("total_jobs") or 0)
        active_count = int(snapshot.get("active_count") or len(snapshot.get("active_jobs") or []))
        paused_sessions = list(snapshot.get("paused_sessions") or [])
        paused_session_count = int(snapshot.get("paused_session_count") or len(paused_sessions))
        queue_pressure = float(snapshot.get("queue_pressure") or 0.0)
        diagnosis = snapshot.get("diagnosis") if isinstance(snapshot.get("diagnosis"), dict) else {}
        if queued_count <= 0 and active_count <= 0 and paused_session_count <= 0:
            return
        progress = max(0, min(100, int(round(queue_pressure * 100))))
        if paused_session_count > 0:
            public_message = "生成任务正在执行，当前阶段会持续更新。"
            available_actions = ["continue_generation", "add_note"]
        elif queue_pressure >= 1.0:
            public_message = "生成任务正在执行，当前阶段会持续更新。"
            available_actions = ["pause_after_batch", "add_note"]
        elif queued_count > 0:
            public_message = "生成任务正在执行，当前阶段会持续更新。"
            available_actions = ["add_note", "pause_after_batch"]
        else:
            public_message = "生成任务正在执行，当前阶段会持续更新。"
            available_actions = ["add_note"]
        metadata = {
            "disclosure": {
                "event_id": f"scheduler-{room_id or 'global'}-{int(time.time() * 1000)}",
                "room_id": room_id,
                "audience": "participant",
                "stage": "璧勬簮璋冨害",
                "progress": progress,
                "public_message": public_message,
                "available_actions": available_actions,
                "requires_confirmation": False,
                "metadata": {
                    "queue_pressure": queue_pressure,
                    "queued_count": queued_count,
                    "active_count": active_count,
                    "paused_session_count": paused_session_count,
                    "total_jobs": total_jobs,
                    "diagnosis": {
                        "state": str(diagnosis.get("state") or ""),
                        "reasons": [
                            str(item) for item in list(diagnosis.get("reasons") or [])[:6]
                            if str(item)
                        ],
                        "recommended_actions": [
                            str(item) for item in list(diagnosis.get("recommended_actions") or [])[:6]
                            if str(item)
                        ],
                    },
                    "recent_event_types": [
                        str(event.get("event_type") or "")
                        for event in (snapshot.get("recent_events") or [])[-5:]
                        if isinstance(event, dict)
                    ],
                },
            },
        }
        text = public_message
        disclosure_payload = metadata["disclosure"]
        try:
            if hasattr(self._corona_engine, "network_send_system_message_ex"):
                self._record_disclosure_event_send_in_agent_runtime(
                    phase="disclosure_event_send_requested",
                    payload=disclosure_payload,
                    message=text,
                    message_kind="action_status",
                    channel="scheduler_broadcast_ex",
                )
                sent = bool(self._corona_engine.network_send_system_message_ex(
                    "system",
                    "绯荤粺",
                    text,
                    "action_status",
                    disclosure_payload["event_id"],
                    json.dumps(metadata, ensure_ascii=False),
                ))
                self._record_disclosure_event_send_in_agent_runtime(
                    phase="disclosure_event_send_succeeded" if sent else "disclosure_event_send_failed",
                    payload=disclosure_payload,
                    message=text,
                    message_kind="action_status",
                    channel="scheduler_broadcast_ex",
                    sent=sent,
                )
            elif hasattr(self._corona_engine, "network_send_system_message"):
                self._record_disclosure_event_send_in_agent_runtime(
                    phase="disclosure_event_send_requested",
                    payload=disclosure_payload,
                    message=text,
                    message_kind="action_status",
                    channel="scheduler_broadcast",
                )
                sent = bool(self._corona_engine.network_send_system_message("system", "绯荤粺", text))
                self._record_disclosure_event_send_in_agent_runtime(
                    phase="disclosure_event_send_succeeded" if sent else "disclosure_event_send_failed",
                    payload=disclosure_payload,
                    message=text,
                    message_kind="action_status",
                    channel="scheduler_broadcast",
                    sent=sent,
                )
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to emit generation scheduler disclosure: %s", type(exc).__name__)
            self._record_disclosure_event_send_in_agent_runtime(
                phase="disclosure_event_send_failed",
                payload=disclosure_payload,
                message=text,
                message_kind="action_status",
                channel="scheduler_broadcast",
                sent=False,
            )

    def _get_host_action_executor(self) -> Any:
        if self._host_action_executor is None:
            structured_action_handler = (
                self._get_interaction_coordinator().execute_action_payload
                if self._agent_runtime_flags.can_call_legacy_main_workflow()
                else self._execute_structured_host_action_via_agent_runtime
            )
            self._host_action_executor = LanChatHostActionExecutor(
                corona_engine=self._corona_engine,
                agent_factory=self._agent_factory or self._default_agent_factory,
                structured_action_handler=structured_action_handler,
                send_audit_callback=self._record_host_action_message_send_in_agent_runtime,
                allow_legacy_agent_fallback=self._agent_runtime_flags.can_call_legacy_main_workflow(),
            )
        return self._host_action_executor

    def _record_host_action_message_send_in_agent_runtime(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = dict(payload or {})
        phase = str(data.get("phase") or "").strip()
        suffix = "requested" if phase == "requested" else "succeeded" if phase == "succeeded" else "failed"
        event_name = f"host_action_message_send_{suffix}"
        room_id = str(data.get("room_id") or "default")
        external_plan_id = str(
            data.get("external_plan_id")
            or data.get("seed_plan_id")
            or data.get("plan_id")
            or data.get("runtime_plan_id")
            or ""
        )
        if not external_plan_id:
            external_plan_id = self._active_runtime_external_plan_id(room_id)
        safe_payload: dict[str, Any] = {
            "status": str(data.get("status") or ""),
            "message_kind": str(data.get("message_kind") or "action_status"),
            "channel": str(data.get("channel") or ""),
            "proposal_id": str(data.get("proposal_id") or ""),
            "external_plan_id": str(data.get("external_plan_id") or ""),
            "seed_plan_id": str(data.get("seed_plan_id") or ""),
            "plan_id": str(data.get("plan_id") or ""),
            "runtime_plan_id": str(data.get("runtime_plan_id") or ""),
            "batch_id": str(data.get("batch_id") or ""),
            "source_user_id": str(data.get("source_user_id") or ""),
        }
        if "sent" in data:
            safe_payload["sent"] = bool(data.get("sent"))
        return self._record_runtime_audit_event(
            event=event_name,
            room_id=room_id,
            message=str(data.get("message") or ""),
            payload=safe_payload,
            external_plan_id=external_plan_id,
            batch_id=str(data.get("batch_id") or ""),
        )

    def _get_interaction_coordinator(self) -> InteractionCoordinator:
        if self._interaction_coordinator is None:
            self._interaction_coordinator = InteractionCoordinator(
                scheduler=self._get_generation_scheduler(),
            )
        return self._interaction_coordinator

    def _get_generation_scheduler(self) -> Any:
        if not self._agent_runtime_flags.can_call_legacy_main_workflow():
            return None
        if self._generation_scheduler is None:
            from .generation_scheduler import GenerationScheduler

            if self._composer_factory is not None:
                from .generation_composer_adapter import SceneComposerJobRunner

                runner = SceneComposerJobRunner(
                    self._composer_factory,
                    agent_runtime_flags=self._agent_runtime_flags,
                )
                self._generation_scheduler = GenerationScheduler(
                    stage_handlers=runner.stage_handlers(),
                    stage_order=("compose",),
                )
            else:
                self._generation_scheduler = GenerationScheduler()
            self._install_generation_scheduler_hooks(self._generation_scheduler)
        return self._generation_scheduler

    def _install_generation_scheduler_hooks(self, scheduler: Any) -> None:
        self._install_deferred_download_scheduler(scheduler)
        self._install_media_task_scheduler(scheduler)
        self._install_generation_scheduler_runtime_audit(scheduler)
        self._install_progress_disclosure_scheduler(scheduler)

    def _clear_generation_scheduler_hooks(self, scheduler: Any) -> None:
        self._clear_deferred_download_scheduler(scheduler)
        self._clear_media_task_scheduler(scheduler)
        self._clear_generation_scheduler_runtime_audit(scheduler)
        self._clear_progress_disclosure_scheduler(scheduler)

    def _install_generation_scheduler_runtime_audit(self, scheduler: Any) -> None:
        record_event = getattr(scheduler, "_record_event_locked", None)
        if not callable(record_event):
            return
        if getattr(scheduler, "_lanchat_runtime_audit_installed", False):
            return
        worker = self

        def record_event_with_runtime_audit(event_type: str, **payload: Any) -> Any:
            result = record_event(event_type, **payload)
            worker._record_generation_scheduler_event_in_agent_runtime(
                event_type=str(event_type or ""),
                payload=dict(payload or {}),
            )
            return result

        try:
            setattr(scheduler, "_lanchat_runtime_audit_original_record_event", record_event)
            setattr(scheduler, "_lanchat_runtime_audit_installed", True)
            setattr(scheduler, "_record_event_locked", record_event_with_runtime_audit)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to install generation scheduler Runtime audit hook: %s", type(exc).__name__)

    def _clear_generation_scheduler_runtime_audit(self, scheduler: Any) -> None:
        if not getattr(scheduler, "_lanchat_runtime_audit_installed", False):
            return
        original = getattr(scheduler, "_lanchat_runtime_audit_original_record_event", None)
        try:
            if callable(original):
                setattr(scheduler, "_record_event_locked", original)
            setattr(scheduler, "_lanchat_runtime_audit_installed", False)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to clear generation scheduler Runtime audit hook: %s", type(exc).__name__)

    def _record_generation_scheduler_event_in_agent_runtime(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        room_id = str(payload.get("room_id") or payload.get("session_id") or "default")
        external_plan_id = str(payload.get("plan_id") or "")
        safe_payload: dict[str, Any] = {
            "event_type": str(event_type or ""),
            "status": str(payload.get("status") or ""),
            "current_stage": str(payload.get("current_stage") or ""),
            "priority": int(payload.get("priority") or 0),
            "cancelled_count": int(payload.get("cancelled_count") or 0),
            "pruned_count": int(payload.get("pruned_count") or 0),
        }
        if payload.get("batch_id"):
            safe_payload["batch_id"] = str(payload.get("batch_id") or "")
        return self._record_runtime_audit_event(
            event=f"generation_scheduler_{event_type or 'event'}",
            room_id=room_id,
            message=str(event_type or ""),
            payload=safe_payload,
            external_plan_id=external_plan_id,
            batch_id=str(payload.get("batch_id") or ""),
        )

    def _install_progress_disclosure_scheduler(self, scheduler: Any) -> None:
        submit = getattr(scheduler, "submit", None)
        if not callable(submit):
            return
        if getattr(scheduler, "_lanchat_progress_disclosure_installed", False):
            return
        worker = self

        def submit_with_progress(payload: dict[str, Any]) -> Any:
            job_payload = dict(payload or {})
            job_type = str(job_payload.get("job_type") or "")
            if job_type.startswith("scene_generation"):
                runtime_context = dict(job_payload.get("_runtime_context") or {})
                if not callable(runtime_context.get("progress_sink")):
                    runtime_context["progress_sink"] = worker._make_generation_progress_sink(
                        room_id=str(job_payload.get("room_id") or job_payload.get("session_id") or ""),
                        plan_id=str(job_payload.get("plan_id") or ""),
                    )
                if not callable(runtime_context.get("runtime_status_provider")):
                    runtime_context["runtime_status_provider"] = worker._make_generation_runtime_status_provider(
                        room_id=str(job_payload.get("room_id") or job_payload.get("session_id") or ""),
                        plan_id=str(job_payload.get("plan_id") or ""),
                    )
                job_payload["_runtime_context"] = runtime_context
            return submit(job_payload)

        try:
            setattr(scheduler, "_lanchat_progress_disclosure_original_submit", submit)
            setattr(scheduler, "_lanchat_progress_disclosure_installed", True)
            setattr(scheduler, "submit", submit_with_progress)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to install LANChat progress disclosure scheduler hook: %s", type(exc).__name__)

    def _clear_progress_disclosure_scheduler(self, scheduler: Any) -> None:
        if not getattr(scheduler, "_lanchat_progress_disclosure_installed", False):
            return
        original = getattr(scheduler, "_lanchat_progress_disclosure_original_submit", None)
        try:
            if callable(original):
                setattr(scheduler, "submit", original)
            setattr(scheduler, "_lanchat_progress_disclosure_installed", False)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to clear LANChat progress disclosure scheduler hook: %s", type(exc).__name__)

    def _make_generation_progress_sink(self, *, room_id: str, plan_id: str) -> Callable[[str], None]:
        def sink(message: str) -> None:
            self._emit_generation_progress_disclosure(
                message,
                room_id=room_id,
                plan_id=plan_id,
            )
        return sink

    def _make_generation_runtime_status_provider(self, *, room_id: str, plan_id: str) -> Callable[[], dict[str, Any]]:
        def provider() -> dict[str, Any]:
            runtime = self._agent_runtime
            if runtime is None:
                return {}
            try:
                status = runtime.handle_message(
                    room_id=room_id or "default",
                    external_plan_id=plan_id,
                    text="runtime status for progressive workflow",
                    sender_id="system",
                    sender_name="system",
                    action="runtime_status",
                )
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Failed to read AgentRuntime generation status: %s", type(exc).__name__)
                return {}
            if isinstance(status, dict):
                return status
            return {}
        return provider

    def _emit_generation_progress_disclosure(self, message: str, *, room_id: str, plan_id: str) -> None:
        text = self._safe_control_text(str(message or "").strip())
        if not text or self._corona_engine is None:
            return
        room = str(room_id or "default")
        now = time.time()
        with self._progress_disclosure_lock:
            last_text, last_at = self._progress_disclosure_last_by_room.get(room, ("", 0.0))
            if text == last_text and now - float(last_at or 0.0) < 1.0:
                return
            self._progress_disclosure_last_by_room[room] = (text, now)
        stage, progress = self._generation_progress_stage_and_percent(text)
        event_id = f"generation-progress-{room}-{int(now * 1000)}"
        disclosure = {
            "event_id": event_id,
            "room_id": room,
            "audience": "participant",
            "stage": stage,
            "progress": progress,
            "public_message": text,
            "available_actions": ["add_note", "pause_after_batch"],
            "requires_confirmation": False,
            "metadata": {
                "plan_id": str(plan_id or ""),
                "source": "generation_progress_sink",
            },
        }
        metadata = json.dumps({"disclosure": disclosure}, ensure_ascii=False)
        try:
            if hasattr(self._corona_engine, "network_send_system_message_ex"):
                self._corona_engine.network_send_system_message_ex(
                    "system",
                    "绯荤粺",
                    text,
                    "action_status",
                    event_id,
                    metadata,
                )
            elif hasattr(self._corona_engine, "network_send_system_message"):
                self._corona_engine.network_send_system_message("system", "绯荤粺", text)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to emit generation progress disclosure: %s", type(exc).__name__)

    @staticmethod
    def _generation_progress_stage_and_percent(text: str) -> tuple[str, int]:
        progress = 0
        match = re.search(r"鐢熸垚杩涘害\s*(\d{1,3})\s*%", str(text or ""))
        if match:
            progress = max(0, min(100, int(match.group(1))))
        if "排队" in text or "鎺掗槦" in text:
            return "排队中", progress
        if "准备所需模型" in text or "图片" in text or "模型" in text:
            return "资源准备", progress
        if "开始组装" in text or "导入" in text or "放入" in text or "摆放" in text:
            return "分批组装", progress
        if "自动检查" in text or "检查" in text:
            return "最终检查", progress
        if "完成空间" in text or "理解场景" in text:
            return "理解方案", progress
        return "生成中", progress

    def _install_deferred_download_scheduler(self, scheduler: Any) -> None:
        try:
            from plugins.AITool.Quasar.ai_modules.three_d_generate.tools import model_tools
        except Exception:
            return
        setter = getattr(model_tools, "set_deferred_download_scheduler", None)
        if callable(setter):
            try:
                setter(scheduler)
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Failed to install deferred download scheduler: %s", type(exc).__name__)

    def _clear_deferred_download_scheduler(self, scheduler: Any) -> None:
        try:
            from plugins.AITool.Quasar.ai_modules.three_d_generate.tools import model_tools
        except Exception:
            return
        getter = getattr(model_tools, "get_deferred_download_scheduler", None)
        setter = getattr(model_tools, "set_deferred_download_scheduler", None)
        if not callable(getter) or not callable(setter):
            return
        try:
            if getter() is scheduler:
                setter(None)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to clear deferred download scheduler: %s", type(exc).__name__)

    def _install_media_task_scheduler(self, scheduler: Any) -> None:
        try:
            from plugins.AITool.Quasar.ai_media_resource import registry
        except Exception:
            return
        setter = getattr(registry, "set_media_task_scheduler", None)
        if callable(setter):
            try:
                setter(scheduler)
            except Exception as exc:  # noqa: BLE001
                self._logger.debug("Failed to install media task scheduler: %s", type(exc).__name__)

    def _clear_media_task_scheduler(self, scheduler: Any) -> None:
        try:
            from plugins.AITool.Quasar.ai_media_resource import registry
        except Exception:
            return
        getter = getattr(registry, "get_media_task_scheduler", None)
        setter = getattr(registry, "set_media_task_scheduler", None)
        if not callable(getter) or not callable(setter):
            return
        try:
            if getter() is scheduler:
                setter(None)
        except Exception as exc:  # noqa: BLE001
            self._logger.debug("Failed to clear media task scheduler: %s", type(exc).__name__)

    def _prepare_confirmed_action_payload(
        self,
        payload: dict[str, Any] | None,
        trigger: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not payload or payload.get("status") != "confirmed":
            return payload
        if str(payload.get("action_type") or "") != "start_generation":
            return payload
        if payload.get("seed_plan") and payload.get("plan_id"):
            return payload

        room_id = str(trigger.get("room_id") or payload.get("room_id") or "default")
        host_id = str(trigger.get("sender_id") or payload.get("source_user_id") or "host")
        intent_text = str(
            payload.get("resolved_intent_text")
            or payload.get("intent_text")
            or trigger.get("text")
            or ""
        )
        if not self._agent_runtime_flags.can_call_legacy_main_workflow():
            structured = dict(payload)
            plan_id = str(
                payload.get("plan_id")
                or payload.get("resolved_from_plan_id")
                or self._runtime_planning_external_id(
                    trigger,
                    str(trigger.get("agent_name") or payload.get("source_agent_name") or ""),
                )
                or ""
            )
            structured.update({
                "action_type": "start_generation",
                "execution": "agent_runtime_structured",
                "plan_id": plan_id,
                "room_id": room_id,
                "source_user_id": host_id,
                "intent_text": intent_text,
                "resolved_intent_text": str(payload.get("resolved_intent_text") or intent_text),
                "requires_host_confirm": False,
                "status": "confirmed",
                "scene_name": self._runtime_scene_name_from_trigger(trigger),
                "runtime_payload_prepared_by_worker": True,
            })
            structured.setdefault("target_agent_name", str(trigger.get("agent_name") or ""))
            structured.setdefault("target_agent_id", str(trigger.get("agent_id") or ""))
            return structured
        coordinator = self._get_interaction_coordinator()
        plan = coordinator.create_or_update_seed_plan(ChatMessage(
            room_id=room_id,
            sender_id=host_id,
            sender_name=str(trigger.get("sender_name") or ""),
            text=intent_text,
            is_host=True,
            agent_id=str(trigger.get("agent_id") or ""),
            agent_name=str(trigger.get("agent_name") or ""),
        ))
        if plan.status.value == "draft":
            plan.propose()
        confirmed = coordinator.confirm_seed_plan(plan.plan_id, host_id)
        confirmed_payload = confirmed.payload if isinstance(getattr(confirmed, "payload", None), dict) else {}
        seed_plan = confirmed_payload.get("seed_plan")
        if not getattr(confirmed, "ok", False) or not confirmed_payload.get("plan_id") or not seed_plan:
            structured = dict(payload)
            structured.update({
                "action_type": "discussion_only",
                "execution": "coordinator_confirmation_blocked",
                "room_id": room_id,
                "plan_id": plan.plan_id,
                "requires_host_confirm": False,
                "status": "confirmed",
                "coordinator_blocked": True,
                "reason": str(getattr(confirmed, "message", "") or "SeedPlan 暂不能确认执行。"),
                "seed_plan_status": str(getattr(plan.status, "value", plan.status)),
            })
            structured.setdefault("intent_text", intent_text)
            return structured
        structured = dict(payload)
        structured.update({
            "action_type": "start_generation",
            "execution": "coordinator_structured",
            "plan_id": confirmed_payload["plan_id"],
            "plan_version": confirmed_payload["plan_version"],
            "room_id": room_id,
            "seed_plan": seed_plan,
            "requires_host_confirm": False,
            "status": "confirmed",
            "runtime_payload_prepared_by_worker": True,
        })
        structured.setdefault("intent_text", intent_text)
        return structured

    @staticmethod
    def _correlation_id(trigger: dict[str, Any]) -> str:
        return str(trigger.get("correlation_id") or trigger.get("message_id") or "")

    @staticmethod
    def _should_send_fast_ack(trigger: dict[str, Any]) -> bool:
        kind = str(trigger.get("message_kind") or "chat").lower()
        if kind and kind != "chat":
            return False
        text = str(trigger.get("text") or "")
        if not text.strip():
            return False
        keywords = (
            "生成", "设计", "场景", "房间", "卧室", "广场", "教堂",
            "添加", "放大", "缩小", "移动", "移", "删", "删除", "调整",
            "运行时",
            "generate", "create", "move", "scale", "delete", "adjust",
        )
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _messages_from_trigger(trigger: dict[str, Any]) -> list[str]:
        messages: list[str] = []
        history = trigger.get("history") or []
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                sender = str(item.get("from") or item.get("sender_name") or "")
                text = str(item.get("text") or "")
                if text:
                    messages.append(f"{sender}: {text}" if sender else text)

        text = str(trigger.get("text") or "")
        if text and text not in messages:
            messages.append(text)
        return messages

    @staticmethod
    def _default_agent_factory() -> Any:
        from plugins.AITool.cai_extensions.agent.agent_adapter import create_master_agent

        return create_master_agent()
