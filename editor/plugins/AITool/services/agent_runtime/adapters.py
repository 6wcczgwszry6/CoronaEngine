"""Low-risk adapters from existing capabilities into AgentRuntime providers.

These adapters are intentionally narrower than the legacy workflows they touch.
They expose function-sized resource providers to ToolCallGraph execution without
letting old SceneComposer/ProgressiveWorkflow regain control of the runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .tools import ResourceProvider


@dataclass(frozen=True)
class RuntimeCppBridgeResult:
    """Normalized result for a single C++/engine binding call."""

    success: bool
    payload: dict[str, Any]
    error_code: str = ""
    message: str = ""


class RuntimeCppBridge:
    """Narrow Runtime boundary for C++/engine writes.

    The bridge does not know about SceneComposer, Scheduler, or progressive
    workflow.  It only invokes an already selected low-level binding through
    EngineWriteGate and normalizes the binding result into a Runtime-safe shape.
    """

    def __init__(
        self,
        *,
        engine_gate: Any,
        parse_result: Callable[[Any], dict[str, Any]] | None = None,
    ) -> None:
        if engine_gate is None:
            raise ValueError("engine_gate is required")
        self._engine_gate = engine_gate
        self._parse_result = parse_result

    def invoke_tool(
        self,
        tool: Any,
        payload: dict[str, Any],
        *,
        error_code: str = "cpp_tool_failed",
    ) -> RuntimeCppBridgeResult:
        if tool is None:
            return RuntimeCppBridgeResult(False, {}, error_code="cpp_tool_missing", message="C++ tool is missing")
        invoke_tool = getattr(self._engine_gate, "invoke_tool", None)
        if not callable(invoke_tool):
            return RuntimeCppBridgeResult(
                False,
                {},
                error_code="cpp_gate_method_missing",
                message="C++ engine write gate method is missing",
            )
        try:
            raw = invoke_tool(tool, payload)
            return self._normalize(raw, error_code=error_code)
        except Exception:  # noqa: BLE001
            return RuntimeCppBridgeResult(False, {}, error_code=error_code, message="C++ tool failed")

    def set_transform(
        self,
        tool: Any,
        payload: dict[str, Any],
        *,
        error_code: str = "cpp_transform_failed",
    ) -> RuntimeCppBridgeResult:
        if tool is None:
            return RuntimeCppBridgeResult(False, {}, error_code="cpp_tool_missing", message="C++ transform tool is missing")
        set_transform = getattr(self._engine_gate, "set_transform", None)
        if not callable(set_transform):
            return RuntimeCppBridgeResult(
                False,
                {},
                error_code="cpp_gate_method_missing",
                message="C++ engine write gate method is missing",
            )
        try:
            raw = set_transform(tool, payload)
            return self._normalize(raw, error_code=error_code)
        except Exception:  # noqa: BLE001
            return RuntimeCppBridgeResult(False, {}, error_code=error_code, message="C++ transform failed")

    def remove_actor(
        self,
        tool: Any,
        payload: dict[str, Any],
        *,
        error_code: str = "cpp_actor_delete_failed",
    ) -> RuntimeCppBridgeResult:
        if tool is None:
            return RuntimeCppBridgeResult(False, {}, error_code="cpp_tool_missing", message="C++ delete tool is missing")
        remove_actor = getattr(self._engine_gate, "remove_actor", None)
        if not callable(remove_actor):
            return RuntimeCppBridgeResult(
                False,
                {},
                error_code="cpp_gate_method_missing",
                message="C++ engine write gate method is missing",
            )
        try:
            raw = remove_actor(tool, payload)
            return self._normalize(raw, error_code=error_code)
        except Exception:  # noqa: BLE001
            return RuntimeCppBridgeResult(False, {}, error_code=error_code, message="C++ actor delete failed")

    def _normalize(self, raw: Any, *, error_code: str) -> RuntimeCppBridgeResult:
        parsed = self._parse_result(raw) if self._parse_result is not None else _parse_tool_result(raw)
        if _is_unstructured_raw_result(parsed):
            return RuntimeCppBridgeResult(
                False,
                {},
                error_code=error_code,
                message="C++ binding returned invalid result",
            )
        status_text = str(parsed.get("status") or parsed.get("status_info") or "").strip().lower()
        type_text = str(parsed.get("type") or parsed.get("event_type") or "").strip().lower()
        success_value = parsed.get("success")
        explicit_failure = (
            (isinstance(success_value, bool) and not success_value)
            or (
                isinstance(success_value, (int, float))
                and not isinstance(success_value, bool)
                and float(success_value) == 0.0
            )
            or (
                isinstance(success_value, str)
                and success_value.strip().lower() in {"0", "false", "no", "off", "failed", "failure", "error"}
            )
        )
        native_error_code = parsed.get("error_code")
        native_error_text = str(native_error_code or "").strip()
        has_native_error_code = bool(native_error_text) and native_error_text.lower() not in {
            "0",
            "ok",
            "success",
        }
        if (
            explicit_failure
            or status_text in {"error", "failed", "failure", "fail"}
            or type_text in {"error", "failed", "failure", "fail"}
            or parsed.get("error")
            or (
                has_native_error_code and status_text not in {"ok", "success"}
            )
        ):
            message = _safe_cpp_error_message(
                parsed.get("message")
                or parsed.get("error")
                or parsed.get("status_info")
                or native_error_text
            )
            if isinstance(native_error_code, str):
                normalized_error_code = native_error_code.strip()
                if normalized_error_code and not normalized_error_code.isdigit():
                    error_code = normalized_error_code
            return RuntimeCppBridgeResult(
                False,
                {"status": "error", "error": message, "error_code": error_code},
                error_code=error_code,
                message=message,
            )
        return RuntimeCppBridgeResult(True, _safe_cpp_success_payload(parsed))


def make_image_resource_provider(
    *,
    image_tool: Any,
    parse_result: Callable[[Any], dict[str, Any]] | None = None,
    resolution: str = "1:1",
) -> ResourceProvider:
    """Create a Runtime image-resource provider from a function-sized image tool.

    The adapter normalizes reference-image facts for RuntimeState.  It does not
    call SceneComposer, start a model workflow, import actors, or mutate engine
    state.  The injected image_tool may expose ``invoke(payload)`` or be a plain
    callable that accepts the same payload.
    """

    if image_tool is None:
        raise ValueError("image_tool is required")

    def _provider(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        batch_id = str(payload.get("batch_id") or "")
        model_items = [str(item) for item in (payload.get("model_items") or []) if str(item or "")]
        resources: dict[str, dict[str, Any]] = {}
        for index, name in enumerate(model_items, start=1):
            prompt = str(_item_value(payload, name, "image_prompt") or _image_prompt_for_item(name))
            tool_payload = {
                "prompt": prompt,
                "object_name": name,
                "object_id": f"{batch_id}-img-{index:02d}" if batch_id else f"runtime-img-{index:02d}",
                "resolution": resolution,
            }
            try:
                raw = _invoke_image_tool(image_tool, tool_payload)
                parsed = parse_result(raw) if parse_result is not None else _parse_tool_result(raw)
                resources[name] = _normalize_image_result(
                    parsed,
                    name=name,
                    batch_id=batch_id,
                    index=index,
                    prompt=prompt,
                )
            except Exception:  # noqa: BLE001
                resources[name] = _failed_image_resource(
                    name=name,
                    batch_id=batch_id,
                    index=index,
                )
        return resources

    return _provider


def make_model_resource_provider(
    *,
    model_tool: Any,
    parse_result: Callable[[Any], dict[str, Any]] | None = None,
) -> ResourceProvider:
    """Create a Runtime model-resource provider from a function-sized model tool.

    The adapter prepares model resource facts only.  It does not call
    SceneComposer, ProgressiveWorkflow, GenerationScheduler, or import actors.
    The injected model_tool may expose ``invoke(payload)`` or be a plain
    callable accepting the same payload.
    """

    if model_tool is None:
        raise ValueError("model_tool is required")

    def _provider(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        batch_id = str(payload.get("batch_id") or "")
        model_items = [str(item) for item in (payload.get("model_items") or []) if str(item or "")]
        resources: dict[str, dict[str, Any]] = {}
        for index, name in enumerate(model_items, start=1):
            tool_payload = {
                "object_name": name,
                "object_id": f"{batch_id}-model-{index:02d}" if batch_id else f"runtime-model-{index:02d}",
                "image_url": str(_item_value(payload, name, "image_url") or _image_resource_value(payload, name) or ""),
                "prompt_text": str(_item_value(payload, name, "prompt_text") or name),
            }
            try:
                raw = _invoke_tool_safely(model_tool, tool_payload, fallback="model resource failed")
                parsed = parse_result(raw) if parse_result is not None else _parse_tool_result(raw)
                resources[name] = _normalize_model_tool_result(
                    parsed,
                    name=name,
                    batch_id=batch_id,
                    index=index,
                )
            except Exception:  # noqa: BLE001
                resources[name] = _failed_model_resource(
                    name=name,
                    batch_id=batch_id,
                    index=index,
                    source="model_resource",
                )
        return resources

    return _provider


def make_scene_snapshot_provider(
    *,
    snapshot_tool: Any,
    scene_name: str = "",
    wait_for_bounds: bool = True,
    parse_result: Callable[[Any], dict[str, Any]] | None = None,
) -> Callable[[str], dict[str, Any]]:
    """Create a Runtime scene-snapshot provider from a function-sized scene tool.

    The provider only reads native scene facts and normalizes them for
    RuntimeState.  It does not import actors, mutate transforms, or call any
    legacy compose/progressive workflow path.
    """

    if snapshot_tool is None:
        raise ValueError("snapshot_tool is required")

    def _provider(request: Any) -> dict[str, Any]:
        if isinstance(request, dict):
            room_id = str(request.get("room_id") or "")
            effective_scene_name = str(request.get("scene_name") or scene_name or "")
        else:
            room_id = str(request or "")
            effective_scene_name = scene_name
        payload = {
            "scene_name": effective_scene_name,
            "wait_for_bounds": bool(wait_for_bounds),
        }
        raw = _invoke_tool_safely(snapshot_tool, payload, fallback="scene snapshot failed")
        parsed = parse_result(raw) if parse_result is not None else _parse_tool_result(raw)
        return _normalize_scene_snapshot_result(
            parsed,
            room_id=str(room_id or ""),
            scene_name=effective_scene_name,
        )

    return _provider


def make_scene_review_provider(
    *,
    review_tool: Any,
    output_dir_provider: Callable[[dict[str, Any]], str] | None = None,
    max_images: int = 12,
    parse_result: Callable[[Any], dict[str, Any]] | None = None,
) -> ResourceProvider:
    """Create a Runtime review provider from a function-sized scene review tool.

    The provider produces advisory review facts only.  If no screenshot directory
    is available it returns a skipped review instead of blocking generation or
    pretending VLM succeeded.
    """

    if review_tool is None:
        raise ValueError("review_tool is required")

    def _provider(payload: dict[str, Any]) -> dict[str, Any]:
        output_dir = str(output_dir_provider(payload) if output_dir_provider else payload.get("review_output_dir") or "")
        if not output_dir:
            return {
                "plan_id": str(payload.get("plan_id") or ""),
                "batch_id": str(payload.get("batch_id") or ""),
                "contract_version": int(payload.get("contract_version") or 0),
                "checkpoint_type": str(payload.get("checkpoint_type") or "geometry_review"),
                "reviewed_targets": [
                    str(item or "").strip()
                    for item in (payload.get("reviewed_targets") or [])
                    if str(item or "").strip()
                ],
                "status": "skipped",
                "overall": "SKIPPED",
                "score": -1,
                "issues": [],
                "advisory_items": [
                    {"type": "review_skipped", "reason": "missing screenshot directory"},
                ],
                "source": "scene_review_provider",
            }
        tool_payload = {
            "output_dir": output_dir,
            "scene_description": str(payload.get("scene_description") or payload.get("scene_name") or ""),
            "max_images": int(max_images),
        }
        raw = _invoke_tool_safely(review_tool, tool_payload, fallback="scene review failed")
        parsed = parse_result(raw) if parse_result is not None else _parse_tool_result(raw)
        return _normalize_scene_review_result(parsed, payload=payload)

    return _provider


def make_environment_component_provider(
    *,
    environment_tool: Any,
    parse_result: Callable[[Any], dict[str, Any]] | None = None,
) -> ResourceProvider:
    """Create a Runtime environment-component provider from a function tool.

    The adapter returns terrain / skybox / boundary component facts for
    RuntimeState only.  Real engine writes must be implemented as dedicated
    engine providers through RuntimeCppBridge / EngineWriteGate, not hidden
    behind this fact provider.
    """

    if environment_tool is None:
        raise ValueError("environment_tool is required")

    def _provider(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        batch_id = str(payload.get("batch_id") or "")
        components: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(payload.get("substrate_resolutions") or [], start=1):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            component_type = str(item.get("component_type") or "environment").strip() or "environment"
            tool_payload = {
                "room_id": str(payload.get("room_id") or ""),
                "plan_id": str(payload.get("plan_id") or ""),
                "batch_id": batch_id,
                "scene_name": str(payload.get("scene_name") or ""),
                "name": name,
                "component_type": component_type,
                "handler": str(item.get("handler") or ""),
                "object_id": f"{batch_id}-env-{index:02d}" if batch_id else f"runtime-env-{index:02d}",
                "requires_engine_write": _coerce_adapter_bool(item.get("requires_engine_write"), default=False),
            }
            raw = _invoke_tool_safely(environment_tool, tool_payload, fallback="environment component failed")
            parsed = parse_result(raw) if parse_result is not None else _parse_tool_result(raw)
            component = _normalize_environment_component_result(
                parsed,
                fallback=tool_payload,
                index=index,
            )
            if component.get("requires_engine_write"):
                raise RuntimeError("environment component requires dedicated engine bridge")
            components[component["component_id"]] = component
        return components

    return _provider


def make_engine_environment_component_import_provider(
    *,
    environment_import_tool: Any,
    engine_gate: Any,
    scene_name: str = "",
    parse_result: Callable[[Any], dict[str, Any]] | None = None,
) -> ResourceProvider:
    """Create a Runtime environment-component import provider.

    This is the dedicated engine-write bridge for future terrain / boundary /
    room-framework actor creation.  It is intentionally separate from
    make_environment_component_provider(), which only produces Runtime facts.
    """

    if environment_import_tool is None:
        raise ValueError("environment_import_tool is required")
    if engine_gate is None:
        raise ValueError("engine_gate is required")
    bridge = RuntimeCppBridge(engine_gate=engine_gate, parse_result=parse_result)

    def _provider(payload: dict[str, Any]) -> dict[str, Any]:
        batch_id = str(payload.get("batch_id") or "")
        plan_id = str(payload.get("plan_id") or "")
        effective_scene_name = str(payload.get("scene_name") or scene_name or "")
        requested = _environment_components_from_payload(payload)
        component_updates: dict[str, dict[str, Any]] = {}
        import_results: list[dict[str, Any]] = []
        for index, component in enumerate(requested, start=1):
            component_id = _safe_component_token(
                component.get("component_id"),
                fallback=(f"{batch_id}-env-import-{index:02d}" if batch_id else f"runtime-env-import-{index:02d}"),
            )
            name = _safe_component_text(component.get("name"), fallback=component_id)
            component_type = _safe_component_token(
                component.get("component_type"),
                fallback="environment",
            )
            import_payload = {
                "component_id": component_id,
                "name": name,
                "component_type": component_type,
                "handler": _safe_component_token(component.get("handler"), fallback="", allow_empty=True),
                "object_id": component_id,
                "scene_name": str(component.get("scene_name") or effective_scene_name),
            }
            if plan_id:
                import_payload["plan_id"] = plan_id
            if batch_id:
                import_payload["batch_id"] = batch_id
            bridge_result = bridge.invoke_tool(
                environment_import_tool,
                import_payload,
                error_code="cpp_environment_component_import_failed",
            )
            if not bridge_result.success:
                import_results.append({
                    "component_id": component_id,
                    "name": name,
                    "component_type": component_type,
                    "status": "failed",
                    "reason": _safe_adapter_error_message(
                        {"message": bridge_result.message},
                        fallback="environment component import failed",
                    ),
                })
                continue
            update = _normalize_environment_component_import_result(
                bridge_result.payload,
                fallback=import_payload,
            )
            component_updates[update["component_id"]] = update
            import_results.append({
                "component_id": update["component_id"],
                "name": update["name"],
                "component_type": update["component_type"],
                "status": "success",
            })
        return {
            "environment_components": component_updates,
            "environment_import_results": import_results,
        }

    return _provider


def make_legacy_model_resource_provider(
    model_provider_factory: Callable[[], Any] | None = None,
) -> ResourceProvider:
    """Create a Runtime model-resource provider backed by legacy ModelProvider.

    The returned provider only acquires and normalizes model resource facts.  It
    does not import actors, mutate the engine scene, or call the old scene
    composition workflow.  Per-item acquisition failures are persisted as failed
    resource facts so later Runtime stages can report partial progress without
    creating fake actors for unavailable models.
    """

    provider_instance: Any | None = None

    def _provider(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        nonlocal provider_instance
        if provider_instance is None:
            provider_instance = _create_model_provider(model_provider_factory)

        batch_id = str(payload.get("batch_id") or "")
        model_items = [str(item) for item in (payload.get("model_items") or []) if str(item or "")]
        resources: dict[str, dict[str, Any]] = {}
        for index, name in enumerate(model_items, start=1):
            object_id = f"{batch_id}-{index:02d}" if batch_id else f"runtime-{index:02d}"
            try:
                result = provider_instance.acquire(
                    name,
                    image_url=str(_item_value(payload, name, "image_url") or _image_resource_value(payload, name) or ""),
                    prompt_text=str(_item_value(payload, name, "prompt_text") or name),
                    object_id=object_id,
                )
            except Exception as exc:  # noqa: BLE001
                resources[name] = _failed_model_resource(name=name, batch_id=batch_id, index=index)
                continue
            try:
                resources[name] = _normalize_acquire_result(result, name=name, batch_id=batch_id, index=index)
            except RuntimeError:
                resources[name] = _failed_model_resource(name=name, batch_id=batch_id, index=index)
        return resources

    return _provider


def _normalize_environment_component_result(
    parsed: dict[str, Any],
    *,
    fallback: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    if str(parsed.get("status") or "").lower() == "error" or parsed.get("error"):
        raise RuntimeError(_safe_adapter_error_message(parsed, fallback="environment component failed"))
    fallback_component_id = str(fallback.get("object_id") or f"runtime-env-{index:02d}")
    component_id = _safe_component_token(
        _first_present(parsed.get("component_id"), parsed.get("actor_id"), parsed.get("object_id")),
        fallback=fallback_component_id,
    )
    component_type = _safe_component_token(
        _first_present(
            fallback.get("component_type"),
            parsed.get("component_type"),
            parsed.get("type"),
            "environment",
        ),
        fallback=str(fallback.get("component_type") or "environment"),
    )
    name = _safe_component_text(
        _first_present(fallback.get("name"), parsed.get("name"), parsed.get("actor_name")),
        fallback=str(fallback.get("name") or component_id),
    )
    handler = _safe_component_token(
        _first_present(fallback.get("handler"), parsed.get("handler")),
        fallback=str(fallback.get("handler") or ""),
        allow_empty=True,
    )
    status = _safe_component_token(parsed.get("status"), fallback="created")
    scene_name = _safe_component_text(
        _first_present(fallback.get("scene_name"), parsed.get("scene_name")),
        fallback=str(fallback.get("scene_name") or ""),
        allow_empty=True,
    )
    return {
        "component_id": component_id,
        "name": name,
        "component_type": component_type,
        "handler": handler,
        "status": status,
        "source": "environment_component",
        "scene_name": scene_name,
        "requires_engine_write": _coerce_adapter_bool(
            parsed.get("requires_engine_write") if "requires_engine_write" in parsed else fallback.get("requires_engine_write"),
            default=False,
        ),
    }


def _environment_components_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("environment_components")
    if isinstance(raw, dict):
        return [dict(value) for value in raw.values() if isinstance(value, dict)]
    if isinstance(raw, list):
        return [dict(value) for value in raw if isinstance(value, dict)]
    raw = payload.get("substrate_resolutions")
    if isinstance(raw, list):
        return [dict(value) for value in raw if isinstance(value, dict)]
    return []


def _normalize_environment_component_import_result(
    parsed: dict[str, Any],
    *,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    component_id = _safe_component_token(
        _first_present(parsed.get("component_id"), parsed.get("object_id"), fallback.get("component_id")),
        fallback=str(fallback.get("component_id") or fallback.get("object_id") or "runtime-env-import"),
    )
    name = _safe_component_text(
        _first_present(fallback.get("name"), parsed.get("name"), parsed.get("actor_name")),
        fallback=component_id,
    )
    component_type = _safe_component_token(
        _first_present(fallback.get("component_type"), parsed.get("component_type"), parsed.get("type")),
        fallback=str(fallback.get("component_type") or "environment"),
    )
    handler = _safe_component_token(
        _first_present(fallback.get("handler"), parsed.get("handler")),
        fallback="",
        allow_empty=True,
    )
    scene_name = _safe_component_text(
        _first_present(fallback.get("scene_name"), parsed.get("scene_name")),
        fallback="",
        allow_empty=True,
    )
    actor_id = _safe_component_token(
        _first_present(parsed.get("actor_id"), parsed.get("actor_guid"), parsed.get("guid")),
        fallback="",
        allow_empty=True,
    )
    update = {
        "component_id": component_id,
        "name": name,
        "component_type": component_type,
        "handler": handler,
        "status": "imported",
        "source": "engine_environment_import",
        "scene_name": scene_name,
        "requires_engine_write": False,
    }
    if actor_id:
        update["actor_id"] = actor_id
    return update


def _safe_component_token(raw: Any, *, fallback: str, allow_empty: bool = False) -> str:
    fallback_text = str(fallback or "").strip()
    text = str(raw or "").strip()
    if not text:
        return "" if allow_empty else fallback_text
    if _adapter_text_has_unsafe_token(text):
        return "" if allow_empty and not fallback_text else fallback_text
    if len(text) > 80 or any(ch.isspace() for ch in text) or "/" in text or "\\" in text or ":" in text:
        return "" if allow_empty and not fallback_text else fallback_text
    return text


def _safe_component_text(raw: Any, *, fallback: str, allow_empty: bool = False) -> str:
    fallback_text = str(fallback or "").strip()
    text = str(raw or "").strip()
    if not text:
        return "" if allow_empty else fallback_text
    if _adapter_text_has_unsafe_token(text):
        return "" if allow_empty and not fallback_text else fallback_text
    return text[:160]


def _coerce_adapter_bool(raw: Any, *, default: bool = False) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    text = str(raw or "").strip().lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if text in {"0", "false", "no", "n", "off", "disabled", "none", "null"}:
        return False
    return default


def _invoke_image_tool(image_tool: Any, payload: dict[str, Any]) -> Any:
    return _invoke_tool_safely(image_tool, payload, fallback="image resource failed")


def _invoke_tool(tool: Any, payload: dict[str, Any]) -> Any:
    invoke = getattr(tool, "invoke", None)
    if callable(invoke):
        return invoke(payload)
    if callable(tool):
        return tool(payload)
    raise TypeError("tool must be callable or expose invoke(payload)")


def _invoke_tool_safely(tool: Any, payload: dict[str, Any], *, fallback: str) -> Any:
    try:
        return _invoke_tool(tool, payload)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(fallback) from exc


def _normalize_scene_snapshot_result(parsed: dict[str, Any], *, room_id: str, scene_name: str) -> dict[str, Any]:
    status = str(parsed.get("status") or "").strip().lower()
    success = _coerce_adapter_bool(parsed.get("success"), default=True)
    if status in {"error", "failed", "failure", "fail"} or not success or parsed.get("error"):
        raise RuntimeError(_safe_adapter_error_message(parsed, fallback="scene snapshot failed"))
    actors = parsed.get("actors")
    if not isinstance(actors, list):
        actors = []
    safe_actors = [
        actor
        for actor in (
            _normalize_snapshot_actor(item, scene_name=scene_name, index=index)
            for index, item in enumerate(actors, start=1)
        )
        if actor
    ]
    return {
        "room_id": room_id,
        "scene_name": str(_first_present(scene_name, parsed.get("scene_name"), parsed.get("scene"), room_id)),
        "actor_count": len(safe_actors),
        "actors": safe_actors,
        "source": "scene_snapshot_tool",
    }


def _normalize_snapshot_actor(actor: Any, *, scene_name: str, index: int = 0) -> dict[str, Any]:
    if not isinstance(actor, dict):
        return {}
    raw_actor_id = str(
        _first_present(
            actor.get("actor_id"),
            actor.get("actor_guid"),
            actor.get("guid"),
            actor.get("name"),
        )
        or ""
    ).strip()
    raw_actor_name = str(_first_present(actor.get("name"), actor.get("actor_name"), raw_actor_id) or "").strip()
    if not raw_actor_id and not raw_actor_name:
        return {}
    fallback_id = f"snapshot-actor-{max(int(index or 0), 1):02d}"
    actor_id = _safe_component_token(raw_actor_id, fallback=fallback_id)
    actor_name = _safe_component_text(raw_actor_name, fallback=actor_id)
    geometry = actor.get("geometry") if isinstance(actor.get("geometry"), dict) else {}
    safe: dict[str, Any] = {
        "actor_id": actor_id,
        "name": actor_name,
        "source": "scene_snapshot",
    }
    effective_scene_name = _safe_component_text(
        _first_present(scene_name, actor.get("scene_name"), actor.get("scene")),
        fallback="",
        allow_empty=True,
    )
    if effective_scene_name:
        safe["scene_name"] = effective_scene_name
    for field in ("position", "rotation", "scale", "aabb"):
        value = _first_present(actor.get(field), geometry.get(field))
        if value is not None:
            safe[field] = value
    if "version" in actor and isinstance(actor.get("version"), int):
        safe["version"] = actor.get("version")
    return safe


def _normalize_scene_review_result(parsed: dict[str, Any], *, payload: dict[str, Any]) -> dict[str, Any]:
    status = str(parsed.get("status") or "").strip().lower()
    success = _coerce_adapter_bool(parsed.get("success"), default=True)
    if status in {"error", "failed", "failure", "fail"} or not success or parsed.get("error"):
        raise RuntimeError(_safe_adapter_error_message(parsed, fallback="scene review failed"))
    raw_issues = parsed.get("issues") or []
    issues: list[dict[str, Any]] = []
    for item in raw_issues:
        issue = _normalize_review_issue(item)
        if issue:
            issues.append(issue)
    overall = _safe_component_text(parsed.get("overall"), fallback=("WARN" if issues else "PASS")).upper()
    status = _safe_component_text(parsed.get("status"), fallback="", allow_empty=True).lower()
    if not status:
        status = "needs_adjustment" if issues and overall not in {"PASS", "SKIPPED"} else overall.lower()
    advisory_items = [
        item
        for item in (_normalize_review_advisory(item) for item in (parsed.get("advisory_items") or []))
        if item
    ]
    return {
        "plan_id": str(payload.get("plan_id") or parsed.get("plan_id") or ""),
        "batch_id": str(payload.get("batch_id") or parsed.get("batch_id") or ""),
        "contract_version": int(payload.get("contract_version") or parsed.get("contract_version") or 0),
        "checkpoint_type": _safe_component_text(
            payload.get("checkpoint_type") or parsed.get("checkpoint_type"),
            fallback="geometry_review",
        ),
        "reviewed_targets": [
            _safe_component_text(item, fallback=f"target-{index:02d}")
            for index, item in enumerate(
                (payload.get("reviewed_targets") or parsed.get("reviewed_targets") or []),
                start=1,
            )
            if str(item or "").strip()
        ],
        "status": status,
        "overall": overall,
        "score": parsed.get("score") if isinstance(parsed.get("score"), (int, float)) else None,
        "issue_count": len(issues),
        "issues": issues,
        "advisory_items": advisory_items,
        "source": "scene_review",
    }


_REVIEW_TEXT_FIELDS = {
    "actor_name",
    "message",
    "name",
    "reason",
    "severity",
    "target_hint",
    "type",
}
_REVIEW_ADVISORY_TEXT_FIELDS = {
    "actor_name",
    "message",
    "reason",
    "summary",
    "target_hint",
    "type",
}
_REVIEW_TOKEN_FIELDS = {"actor_id"}
_REVIEW_ADVISORY_TOKEN_FIELDS = {"actor_id", "batch_id", "checkpoint_type"}
_REVIEW_NUMERIC_FIELDS = {"confidence", "current_y", "suggested_y"}
_REVIEW_VECTOR_FIELDS = {"bounds", "current_position", "suggested_position"}
_REVIEW_ADVISORY_BOOL_FIELDS = {"requires_confirmation"}
_REVIEW_ISSUE_ALLOWED_FIELDS = (
    _REVIEW_TEXT_FIELDS
    | _REVIEW_TOKEN_FIELDS
    | _REVIEW_NUMERIC_FIELDS
    | _REVIEW_VECTOR_FIELDS
)
_REVIEW_ADVISORY_ALLOWED_FIELDS = (
    _REVIEW_ADVISORY_TEXT_FIELDS
    | _REVIEW_ADVISORY_TOKEN_FIELDS
    | {"confidence", "requires_confirmation"}
)


def _normalize_review_issue(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        message = _safe_component_text(item, fallback="内部细节已隐藏")
        return {"type": "advisory", "message": message, "severity": "low"}
    if not isinstance(item, dict):
        return {}
    safe: dict[str, Any] = {}
    for field, value in item.items():
        key = str(field or "").strip()
        if key not in _REVIEW_ISSUE_ALLOWED_FIELDS:
            continue
        normalized = _normalize_review_field(key, value, advisory=False)
        if normalized is not None:
            safe[key] = normalized
    safe["type"] = _safe_component_text(safe.get("type"), fallback="advisory")
    if "severity" in safe:
        safe["severity"] = _safe_component_text(safe.get("severity"), fallback="low")
    if not any(str(safe.get(field) or "").strip() for field in ("message", "reason", "target_hint")):
        safe["message"] = "内部细节已隐藏"
    return safe


def _normalize_review_advisory(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    safe: dict[str, Any] = {}
    for field, value in item.items():
        key = str(field or "").strip()
        if key not in _REVIEW_ADVISORY_ALLOWED_FIELDS:
            continue
        normalized = _normalize_review_field(key, value, advisory=True)
        if normalized is not None:
            safe[key] = normalized
    if not any(str(safe.get(field) or "").strip() for field in ("message", "reason", "summary")):
        safe["summary"] = "内部细节已隐藏"
    return safe


def _normalize_review_field(field: str, value: Any, *, advisory: bool) -> Any:
    token_fields = _REVIEW_ADVISORY_TOKEN_FIELDS if advisory else _REVIEW_TOKEN_FIELDS
    text_fields = _REVIEW_ADVISORY_TEXT_FIELDS if advisory else _REVIEW_TEXT_FIELDS
    if field in token_fields:
        return _safe_component_token(value, fallback="", allow_empty=True)
    if field in text_fields:
        fallback = "advisory" if field == "type" else ("low" if field == "severity" else "内部细节已隐藏")
        return _safe_component_text(value, fallback=fallback)
    if field in _REVIEW_NUMERIC_FIELDS:
        return value if isinstance(value, (int, float)) else None
    if field in _REVIEW_VECTOR_FIELDS:
        if isinstance(value, list) and all(isinstance(number, (int, float)) for number in value):
            return list(value)
        return None
    if field in _REVIEW_ADVISORY_BOOL_FIELDS:
        return bool(value) if isinstance(value, bool) else None
    return None


def make_engine_actor_import_provider(
    *,
    import_tool: Any,
    engine_gate: Any,
    scene_name: str = "",
    parse_result: Callable[[Any], dict[str, Any]] | None = None,
) -> ResourceProvider:
    """Create a Runtime actor-import provider backed by EngineWriteGate.

    This is the narrow C++/engine bridge boundary for Runtime.  It imports only
    the batch items whose model resources are already ready in RuntimeState-like
    payload data, and returns actor facts for StatePatch.  It does not create a
    SceneLayout, run progressive workflow, or clear existing scene actors.
    """

    if import_tool is None:
        raise ValueError("import_tool is required")
    if engine_gate is None:
        raise ValueError("engine_gate is required")
    bridge = RuntimeCppBridge(engine_gate=engine_gate, parse_result=parse_result)

    def _provider(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        batch_id = str(payload.get("batch_id") or "")
        plan_id = str(payload.get("plan_id") or "")
        model_items = [str(item) for item in (payload.get("model_items") or []) if str(item or "")]
        placements = dict(payload.get("placements") or {})
        model_resources = _model_resources_from_payload(payload)
        actors: dict[str, dict[str, Any]] = {}
        import_results: list[dict[str, Any]] = []
        for index, name in enumerate(model_items, start=1):
            resource = model_resources.get(name)
            model_path = str(_resource_model_path(resource) or "")
            if not model_path:
                import_results.append({
                    "actor_name": name,
                    "status": "failed",
                    "reason": "missing ready model resource",
                })
                continue
            placement = dict(placements.get(name) or {})
            import_payload = {
                "model_path": model_path,
                "actor_name": name,
                "model_name": name,
                "object_id": f"{batch_id}-{index:02d}" if batch_id else f"runtime-{index:02d}",
                "target": name,
                "position": list(placement.get("position") or [0.0, 0.0, 0.0]),
                "rotation": list(placement.get("rotation") or [0.0, 0.0, 0.0]),
                "scale": list(placement.get("scale") or [1.0, 1.0, 1.0]),
            }
            if plan_id:
                import_payload["plan_id"] = plan_id
            if batch_id:
                import_payload["batch_id"] = batch_id
            effective_scene_name = str(payload.get("scene_name") or scene_name or "")
            if effective_scene_name:
                import_payload["scene_name"] = effective_scene_name
            bridge_result = bridge.invoke_tool(import_tool, import_payload, error_code="cpp_actor_import_failed")
            if not bridge_result.success:
                import_results.append({
                    "actor_name": name,
                    "status": "failed",
                    "reason": (
                        _safe_adapter_error_message(
                            {"message": bridge_result.message},
                            fallback="actor import failed",
                        )
                    ),
                })
                continue
            parsed = bridge_result.payload
            try:
                actor = _normalize_import_result(
                    parsed,
                    fallback_name=name,
                    model_path=model_path,
                    batch_id=batch_id,
                    plan_id=plan_id,
                    scene_name=effective_scene_name,
                    placement=placement,
                )
            except Exception as exc:  # noqa: BLE001
                import_results.append({
                    "actor_name": name,
                    "status": "failed",
                    "reason": _safe_adapter_error_message(exc, fallback="actor import failed"),
                })
                continue
            actors[actor["actor_id"]] = actor
            import_results.append({
                "actor_id": actor["actor_id"],
                "actor_name": actor["name"],
                "status": "success",
            })
        return {"actors": actors, "import_results": import_results}

    return _provider


def make_engine_layout_transform_provider(
    *,
    transform_tool: Any,
    engine_gate: Any,
    scene_name: str = "",
    parse_result: Callable[[Any], dict[str, Any]] | None = None,
) -> ResourceProvider:
    """Create a Runtime layout-transform provider backed by EngineWriteGate.

    The provider applies already-confirmed low-risk Runtime deltas to the engine
    through the narrow set_actor_transform tool.  It does not create new deltas,
    does not call legacy workflows, and returns only observed transform facts for
    RuntimeState reconciliation.
    """

    if transform_tool is None:
        raise ValueError("transform_tool is required")
    if engine_gate is None:
        raise ValueError("engine_gate is required")
    bridge = RuntimeCppBridge(engine_gate=engine_gate, parse_result=parse_result)

    def _provider(payload: dict[str, Any]) -> dict[str, Any]:
        plan_id = str(payload.get("plan_id") or "")
        batch_id = str(payload.get("batch_id") or "")
        applied = [dict(item) for item in (payload.get("applied_deltas") or []) if isinstance(item, dict)]
        actors = {str(key): dict(value) for key, value in (payload.get("actors") or {}).items() if isinstance(value, dict)}
        actor_updates: dict[str, dict[str, Any]] = {}
        transform_results: list[dict[str, Any]] = []
        for item in applied:
            actor_id = str(item.get("actor_id") or "")
            actor = dict(actors.get(actor_id) or {})
            actor_name = str(actor.get("name") or item.get("actor_name") or actor_id)
            position = item.get("position")
            if not actor_id or not actor_name or not isinstance(position, list) or len(position) < 3:
                transform_results.append({
                    "actor_id": actor_id,
                    "actor_name": actor_name,
                    "status": "skipped",
                    "reason": "missing actor or position",
                })
                continue
            transform_payload = {
                "actor_id": actor_id,
                "actor_name": actor_name,
                "position": tuple(float(value) for value in position[:3]),
                "snap_to_ground": False,
            }
            if plan_id:
                transform_payload["plan_id"] = plan_id
            if batch_id:
                transform_payload["batch_id"] = batch_id
            effective_scene_name = str(actor.get("scene_name") or payload.get("scene_name") or scene_name or "")
            if effective_scene_name:
                transform_payload["scene_name"] = effective_scene_name
            bridge_result = bridge.set_transform(transform_tool, transform_payload, error_code="cpp_actor_transform_failed")
            if not bridge_result.success:
                transform_results.append({
                    "actor_id": actor_id,
                    "actor_name": actor_name,
                    "status": "failed",
                    "reason": (
                        _safe_transform_skip_reason(bridge_result.message)
                        or "actor transform failed"
                    ),
                })
                continue
            parsed = bridge_result.payload
            update = _normalize_transform_result(
                parsed,
                actor_id=actor_id,
                fallback_name=actor_name,
                fallback_position=position,
                scene_name=effective_scene_name,
            )
            engine_result = dict(update.get("engine_transform_result") or {})
            update.pop("engine_transform_result", None)
            actor_updates[actor_id] = update
            transform_results.append({
                "actor_id": actor_id,
                "actor_name": actor_name,
                "status": "success",
                "position": list(update.get("position") or position),
                "observed_position": bool(engine_result.get("observed_position")),
            })
        return {"actor_updates": actor_updates, "transform_results": transform_results}

    return _provider


def make_engine_actor_delete_provider(
    *,
    delete_tool: Any,
    engine_gate: Any,
    scene_name: str = "",
    parse_result: Callable[[Any], dict[str, Any]] | None = None,
) -> ResourceProvider:
    """Create a Runtime actor-delete provider backed by EngineWriteGate.

    The provider executes only already-confirmed Runtime delete targets. It does
    not decide whether deletion is safe, and it never receives prompt/provider
    raw context. Failed deletes are returned as per-actor results so RuntimeState
    can preserve the advisory decision without pretending the engine changed.
    """

    if delete_tool is None:
        raise ValueError("delete_tool is required")
    if engine_gate is None:
        raise ValueError("engine_gate is required")
    bridge = RuntimeCppBridge(engine_gate=engine_gate, parse_result=parse_result)

    def _provider(payload: dict[str, Any]) -> dict[str, Any]:
        plan_id = str(payload.get("plan_id") or "")
        proposal_id = str(payload.get("proposal_id") or "")
        actors = {
            str(key): dict(value)
            for key, value in (payload.get("actors") or {}).items()
            if isinstance(value, dict)
        }
        requested = [
            dict(item)
            for item in (payload.get("marked_deleted_actors") or payload.get("target_actors") or [])
            if isinstance(item, dict)
        ]
        actor_updates: dict[str, dict[str, Any]] = {}
        delete_results: list[dict[str, Any]] = []
        for item in requested:
            actor_id = str(item.get("actor_id") or "").strip()
            actor = dict(actors.get(actor_id) or {})
            actor_name = str(actor.get("name") or item.get("actor_name") or actor_id)
            if not actor_id or not actor_name:
                delete_results.append({
                    "actor_id": actor_id,
                    "actor_name": actor_name,
                    "status": "skipped",
                    "reason": "missing actor",
                })
                continue
            delete_payload = {
                "actor_id": actor_id,
                "actor_name": actor_name,
                "target_actor_id": actor_id,
                "target_actor_name": actor_name,
            }
            if plan_id:
                delete_payload["plan_id"] = plan_id
            if proposal_id:
                delete_payload["proposal_id"] = proposal_id
            effective_scene_name = str(actor.get("scene_name") or payload.get("scene_name") or scene_name or "")
            if effective_scene_name:
                delete_payload["scene_name"] = effective_scene_name
            bridge_result = bridge.remove_actor(delete_tool, delete_payload, error_code="cpp_actor_delete_failed")
            if not bridge_result.success:
                delete_results.append({
                    "actor_id": actor_id,
                    "actor_name": actor_name,
                    "status": "failed",
                    "reason": _safe_adapter_error_message({"message": bridge_result.message}, fallback="actor delete failed"),
                })
                continue
            parsed = bridge_result.payload
            actor_updates[actor_id] = {
                **actor,
                "actor_id": actor_id,
                "name": actor_name,
                "deleted": True,
                "sync_lifecycle_status": "deleted",
                "last_sync_event": "runtime_engine_delete",
                "last_sync_status": "deleted",
            }
            if effective_scene_name:
                actor_updates[actor_id]["scene_name"] = effective_scene_name
            delete_results.append({
                "actor_id": actor_id,
                "actor_name": actor_name,
                "status": "success",
                "observed_deleted": bool(
                    parsed.get("deleted")
                    or str(parsed.get("status") or "").strip().lower() in {"ok", "success", "deleted", "removed"}
                    or str(parsed.get("event_type") or "").strip().lower() in {"actor_deleted", "actor_removed"}
                ),
            })
        return {"actor_updates": actor_updates, "delete_results": delete_results}

    return _provider


def _create_model_provider(model_provider_factory: Callable[[], Any] | None) -> Any:
    if model_provider_factory is not None:
        return model_provider_factory()

    from plugins.AITool.cai_extensions.agent.model_provider import ModelProvider

    return ModelProvider()


def _model_resources_from_payload(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    resources = payload.get("model_resources")
    if isinstance(resources, dict):
        return {str(key): dict(value) for key, value in resources.items() if isinstance(value, dict)}
    plans = payload.get("model_resource_plans")
    batch_id = str(payload.get("batch_id") or "")
    if isinstance(plans, dict):
        if batch_id and isinstance(plans.get(batch_id), dict):
            return {str(key): dict(value) for key, value in plans[batch_id].items() if isinstance(value, dict)}
        return {str(key): dict(value) for key, value in plans.items() if isinstance(value, dict)}
    return {}


def _resource_model_path(resource: dict[str, Any] | None) -> str:
    if not resource:
        return ""
    if str(resource.get("status") or "").lower() not in {"ready", "prepared", "provider-model"}:
        return ""
    return str(
        _first_present(
            resource.get("local_path"),
            resource.get("model_path"),
            resource.get("path"),
        )
        or ""
    )


def _parse_tool_result(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return _unwrap_tool_envelope(raw)
    if isinstance(raw, str):
        import json

        try:
            parsed = json.loads(raw)
            return _unwrap_tool_envelope(parsed) if isinstance(parsed, dict) else {"raw": raw}
        except Exception:  # noqa: BLE001
            return {"raw": raw}
    return {"raw": raw}


def _is_unstructured_raw_result(parsed: dict[str, Any]) -> bool:
    return set(parsed.keys()) == {"raw"}


def _safe_cpp_error_message(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return "C++ binding failed"
    lowered = text.lower()
    blocked = (
        "api_key",
        "asset_path",
        "authorization",
        "bearer ",
        "c:\\",
        "metadata",
        "model_path",
        "prompt",
        "provider",
        "raw",
        "token",
        "url",
        "://",
    )
    if any(token in lowered for token in blocked):
        return "C++ binding failed"
    return text


def _safe_cpp_success_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "actor",
        "actor_data",
        "actor_guid",
        "actor_id",
        "actor_name",
        "event_type",
        "geometry",
        "ground_snapped",
        "guid",
        "name",
        "observed_position",
        "overlap_resolved",
        "position",
        "rotation",
        "scale",
        "scene_name",
        "skipped_reason",
        "status",
        "status_info",
        "success",
        "type",
    }
    return {
        str(key): safe_value
        for key, value in parsed.items()
        if (key_text := str(key or "").strip())
        and key_text in allowed_keys
        and not _adapter_text_has_unsafe_token(key_text)
        and (safe_value := _safe_cpp_success_value(value)) is not None
    }


def _safe_cpp_success_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        if _adapter_text_has_unsafe_token(value):
            return None
        return value
    if isinstance(value, list):
        safe_items = [_safe_cpp_success_value(item) for item in value[:16]]
        return [item for item in safe_items if item is not None]
    if isinstance(value, dict):
        return _safe_cpp_success_payload(value)
    return None


def _adapter_text_has_unsafe_token(raw: Any) -> bool:
    lowered = str(raw or "").strip().lower()
    if not lowered:
        return False
    blocked = (
        "api_key",
        "asset_path",
        "authorization",
        "bearer ",
        "metadata",
        "model_path",
        "prompt",
        "provider",
        "raw",
        "token",
        "url",
        "://",
        ":\\",
    )
    return any(token in lowered for token in blocked)


def _safe_adapter_error_message(parsed: dict[str, Any], *, fallback: str) -> str:
    message = _safe_cpp_error_message(parsed.get("message") or parsed.get("error"))
    if message == "C++ binding failed":
        return fallback
    return message or fallback


def _unwrap_tool_envelope(parsed: dict[str, Any]) -> dict[str, Any]:
    error_code = _tool_error_code(parsed.get("error_code"))
    if error_code:
        return {
            "status": "error",
            "error": str(parsed.get("status_info") or f"tool error {error_code}"),
            "error_code": error_code,
        }
    llm_content = parsed.get("llm_content")
    if isinstance(llm_content, list):
        for message in llm_content:
            if not isinstance(message, dict):
                continue
            parts = message.get("part")
            if not isinstance(parts, list):
                continue
            for part in parts:
                if not isinstance(part, dict):
                    continue
                content_text = part.get("content_text")
                if isinstance(content_text, str) and content_text.strip():
                    import json

                    try:
                        payload = json.loads(content_text)
                        if isinstance(payload, dict):
                            return payload
                    except Exception:  # noqa: BLE001
                        continue
    return parsed


def _tool_error_code(raw: Any) -> str:
    if raw is None or raw is False:
        return ""
    if isinstance(raw, (int, float)):
        return "" if int(raw) == 0 else str(int(raw))
    text = str(raw).strip()
    if not text or text in {"0", "0.0"}:
        return ""
    return text


def _normalize_import_result(
    parsed: dict[str, Any],
    *,
    fallback_name: str,
    model_path: str,
    batch_id: str,
    plan_id: str,
    scene_name: str,
    placement: dict[str, Any],
) -> dict[str, Any]:
    status = str(parsed.get("status") or "").strip().lower()
    success = _coerce_adapter_bool(parsed.get("success"), default=True)
    if status in {"error", "failed", "failure", "fail"} or not success or parsed.get("error"):
        raise RuntimeError(_safe_adapter_error_message(parsed, fallback="actor import failed"))
    actor = parsed.get("actor") if isinstance(parsed.get("actor"), dict) else {}
    actor_name = _safe_component_text(
        _first_present(
            fallback_name,
            actor.get("name") if isinstance(actor, dict) else None,
            parsed.get("actor_name"),
            parsed.get("actor_id"),
            parsed.get("name"),
        ),
        fallback=fallback_name,
    )
    actor_id = str(
        _first_present(
            actor.get("actor_guid") if isinstance(actor, dict) else None,
            actor.get("guid") if isinstance(actor, dict) else None,
            actor.get("actor_id") if isinstance(actor, dict) else None,
            actor.get("name") if isinstance(actor, dict) else None,
            parsed.get("actor_guid"),
            parsed.get("actor_id"),
            parsed.get("actor_name"),
        )
        or ""
    )
    if not actor_id.strip():
        raise RuntimeError(f"{fallback_name}: actor import returned no actor id")
    geometry = actor.get("geometry") if isinstance(actor.get("geometry"), dict) else {}
    return {
        "actor_id": actor_id,
        "name": actor_name,
        "plan_id": plan_id,
        "batch_id": batch_id,
        "scene_name": str(scene_name or ""),
        "model_path": str(model_path),
        "source": "engine_import",
        "position": list(geometry.get("position") or placement.get("position") or [0.0, 0.0, 0.0]),
        "rotation": list(geometry.get("rotation") or placement.get("rotation") or [0.0, 0.0, 0.0]),
        "scale": list(geometry.get("scale") or placement.get("scale") or [1.0, 1.0, 1.0]),
    }


def _normalize_transform_result(
    parsed: dict[str, Any],
    *,
    actor_id: str,
    fallback_name: str,
    fallback_position: list[Any],
    scene_name: str,
) -> dict[str, Any]:
    status = str(parsed.get("status") or "").strip().lower()
    success = _coerce_adapter_bool(parsed.get("success"), default=True)
    if status in {"error", "failed", "failure", "fail"} or not success or parsed.get("error"):
        raise RuntimeError(_safe_adapter_error_message(parsed, fallback="actor transform failed"))
    actor_data = parsed.get("actor_data") if isinstance(parsed.get("actor_data"), dict) else {}
    observed_position = parsed.get("position") is not None or (
        isinstance(actor_data, dict) and actor_data.get("position") is not None
    )
    position = _first_present(
        parsed.get("position"),
        actor_data.get("position") if isinstance(actor_data, dict) else None,
        fallback_position,
    )
    rotation = _first_present(
        parsed.get("rotation"),
        actor_data.get("rotation") if isinstance(actor_data, dict) else None,
    )
    scale = _first_present(
        parsed.get("scale"),
        actor_data.get("scale") if isinstance(actor_data, dict) else None,
    )
    update: dict[str, Any] = {
        "actor_id": actor_id,
        "name": _safe_component_text(
            _first_present(
                fallback_name,
                parsed.get("actor"),
                actor_data.get("name") if isinstance(actor_data, dict) else None,
            ),
            fallback=fallback_name,
        ),
        "scene_name": str(scene_name or ""),
        "position": list(position or fallback_position),
        "source": "engine_transform",
        "engine_transform_result": {
            "ground_snapped": bool(parsed.get("ground_snapped")),
            "overlap_resolved": bool(parsed.get("overlap_resolved")),
            "observed_position": bool(observed_position),
            "skipped_reason": _safe_transform_skip_reason(parsed.get("skipped_reason")),
        },
    }
    if rotation is not None:
        update["rotation"] = list(rotation)
    if scale is not None:
        update["scale"] = list(scale)
    return update


def _safe_transform_skip_reason(raw: Any) -> str:
    if raw is None:
        return ""
    message = _safe_cpp_error_message(raw)
    if message == "C++ binding failed":
        return ""
    return message[:160]


def _normalize_image_result(
    parsed: dict[str, Any],
    *,
    name: str,
    batch_id: str,
    index: int,
    prompt: str,
) -> dict[str, Any]:
    status = str(parsed.get("status") or "").strip().lower()
    success = _coerce_adapter_bool(parsed.get("success"), default=True)
    if status in {"error", "failed", "failure", "fail"} or not success or parsed.get("error"):
        raise RuntimeError(_safe_adapter_error_message(parsed, fallback="image resource failed"))
    image_url = str(
        _first_present(
            parsed.get("image_url"),
            parsed.get("url"),
            parsed.get("content_url"),
            parsed.get("local_path"),
            parsed.get("path"),
        )
        or ""
    )
    image_paths = parsed.get("image_paths") or parsed.get("images") or []
    if not image_url and isinstance(image_paths, list) and image_paths:
        image_url = str(image_paths[0] or "")
    if not image_url:
        raise RuntimeError(f"{name}: image provider returned no image url/path")
    return {
        "image_request_id": f"image-resource-{batch_id}-{index:02d}" if batch_id else f"image-resource-{index:02d}",
        "name": name,
        "status": "ready",
        "image_url": image_url,
        "source": "image_resource",
    }


def _failed_image_resource(*, name: str, batch_id: str, index: int) -> dict[str, Any]:
    return {
        "image_request_id": f"image-resource-{batch_id}-{index:02d}" if batch_id else f"image-resource-{index:02d}",
        "name": name,
        "status": "failed",
        "source": "image_resource",
    }


def _normalize_acquire_result(result: Any, *, name: str, batch_id: str, index: int) -> dict[str, Any]:
    success = _coerce_adapter_bool(_result_value(result, "success", default=True), default=True)
    if not success:
        raise RuntimeError(f"{name}: model acquire failed")

    local_path = str(
        _first_present(
            _result_value(result, "local_path"),
            _result_value(result, "model_path"),
            _result_value(result, "path"),
        )
        or ""
    )
    if not local_path:
        raise RuntimeError(f"{name}: model provider returned no local_path")

    source = _safe_model_resource_source(_result_value(result, "source", default="legacy_model_provider"))
    preview_images = [
        str(item)
        for item in (_result_value(result, "preview_images", default=[]) or [])
        if isinstance(item, str) and item
    ]
    return {
        "model_request_id": f"legacy-model-{batch_id}-{index:02d}" if batch_id else f"legacy-model-{index:02d}",
        "name": name,
        "status": "ready",
        "local_path": local_path,
        "source": source,
        "preview_images": preview_images,
    }


def _normalize_model_tool_result(
    parsed: dict[str, Any],
    *,
    name: str,
    batch_id: str,
    index: int,
) -> dict[str, Any]:
    status = str(parsed.get("status") or "").strip().lower()
    success = _coerce_adapter_bool(parsed.get("success"), default=True)
    if status in {"error", "failed", "failure", "fail"} or not success or parsed.get("error"):
        raise RuntimeError(_safe_adapter_error_message(parsed, fallback="model resource failed"))
    local_path = str(
        _first_present(
            parsed.get("local_path"),
            parsed.get("model_path"),
            parsed.get("path"),
        )
        or ""
    )
    if not local_path:
        raise RuntimeError(f"{name}: model tool returned no local_path")
    preview_images = [
        str(item)
        for item in (parsed.get("preview_images") or parsed.get("images") or [])
        if isinstance(item, str) and item
    ]
    return {
        "model_request_id": f"model-resource-{batch_id}-{index:02d}" if batch_id else f"model-resource-{index:02d}",
        "name": name,
        "status": "ready",
        "local_path": local_path,
        "source": _safe_model_resource_source(parsed.get("source") or "generation"),
        "preview_images": preview_images,
    }


def _failed_model_resource(
    *,
    name: str,
    batch_id: str,
    index: int,
    source: str = "legacy_model",
) -> dict[str, Any]:
    return {
        "model_request_id": (
            f"{source}-{batch_id}-{index:02d}" if batch_id else f"{source}-{index:02d}"
        ),
        "name": name,
        "status": "failed",
        "source": _safe_model_resource_source(source),
    }


def _item_value(payload: dict[str, Any], name: str, key: str) -> Any:
    keyed = payload.get(key)
    if isinstance(keyed, dict):
        return keyed.get(name)
    item_metadata = payload.get("item_metadata")
    if isinstance(item_metadata, dict):
        metadata = item_metadata.get(name)
        if isinstance(metadata, dict):
            return metadata.get(key)
    return None


def _safe_model_resource_source(value: Any) -> str:
    source = str(value or "").strip().lower().replace("-", "_")
    allowed = {
        "generation",
        "generated",
        "generated_model",
        "retrieval",
        "retrieved",
        "cache",
        "local",
        "local_asset",
        "legacy_model",
        "model_resource",
    }
    if source in allowed:
        return source
    return "legacy_model"


def _image_resource_value(payload: dict[str, Any], name: str) -> Any:
    image_resources = payload.get("image_resources")
    if not isinstance(image_resources, dict):
        return None
    resource = image_resources.get(name)
    if not isinstance(resource, dict):
        return None
    if str(resource.get("status") or "").strip().lower() in {"failed", "failure", "error", "missing"}:
        return None
    return _first_present(
        resource.get("image_url"),
        resource.get("url"),
        resource.get("local_path"),
        resource.get("path"),
    )


def _result_value(result: Any, key: str, default: Any = None) -> Any:
    if isinstance(result, dict):
        return result.get(key, default)
    return getattr(result, key, default)


def _first_present(*values: Any) -> Any:
    for value in values:
        if value:
            return value
    return None


def _image_prompt_for_item(name: str) -> str:
    return (
        f"single standalone physical 3D object reference image of {name}, "
        "centered full object, plain white background, visible thickness and depth, "
        "no text, no labels, no watermark, not a flat poster, not a texture sheet"
    )
