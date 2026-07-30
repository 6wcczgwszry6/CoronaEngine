import json


_CPP_EDITOR_API_METHODS = None
_CPP_EDITOR_API_EVENTS = None
_CPP_EDITOR_API_CALLER_PYTHON_SCRIPT = 2


def _validate_cpp_api_caller(name, spec, caller_mask, caller_name):
    allowed_callers = spec.get("allowed_callers", 0) if isinstance(spec, dict) else 0
    if (int(allowed_callers) & caller_mask) == 0:
        raise RuntimeError(
            f"Editor API caller is not allowed by C++ manifest: {caller_name} cannot call {name}"
        )


def _ensure_cpp_api_methods():
    global _CPP_EDITOR_API_METHODS
    if _CPP_EDITOR_API_METHODS is None:
        manifest = _invoke_cpp_api("EditorApi.list_methods", [], validate_method=False)
        methods = manifest.get("methods", []) if isinstance(manifest, dict) else []
        _CPP_EDITOR_API_METHODS = {
            method.get("api"): method
            for method in methods
            if isinstance(method, dict) and isinstance(method.get("api"), str)
        }
    return _CPP_EDITOR_API_METHODS


def _ensure_cpp_api_method(api_name):
    methods = _ensure_cpp_api_methods()
    if api_name not in _CPP_EDITOR_API_METHODS:
        raise RuntimeError(f"Editor API method is not defined by C++ manifest: {api_name}")
    return methods[api_name]


def _ensure_cpp_api_events():
    global _CPP_EDITOR_API_EVENTS
    if _CPP_EDITOR_API_EVENTS is None:
        manifest = _invoke_cpp_api("EditorApi.list_events", [], validate_method=False)
        events = manifest.get("events", []) if isinstance(manifest, dict) else []
        _CPP_EDITOR_API_EVENTS = {
            event.get("event"): event
            for event in events
            if isinstance(event, dict) and isinstance(event.get("event"), str)
        }
    return _CPP_EDITOR_API_EVENTS


def _ensure_cpp_api_event(event_name):
    events = _ensure_cpp_api_events()
    if event_name not in events:
        raise RuntimeError(f"Editor API event is not defined by C++ manifest: {event_name}")
    event_spec = events[event_name]
    _validate_cpp_api_caller(event_name, event_spec, _CPP_EDITOR_API_CALLER_PYTHON_SCRIPT, "PythonScript")
    return event_spec


def _find_cpp_api_method_by_python_wrapper(wrapper_path):
    for spec in _ensure_cpp_api_methods().values():
        if spec.get("python_wrapper") == wrapper_path:
            return spec
    return None


def _find_cpp_api_event_by_python_wrapper(wrapper_path):
    for event_spec in _ensure_cpp_api_events().values():
        if event_spec.get("python_wrapper") == wrapper_path:
            return event_spec
    return None


def _cpp_value_matches_type(value, value_type):
    if value_type == "any":
        return True
    if value_type == "null":
        return value is None
    if value_type == "boolean":
        return isinstance(value, bool)
    if value_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if value_type == "number":
        return (isinstance(value, (int, float)) and not isinstance(value, bool))
    if value_type == "string":
        return isinstance(value, str)
    if value_type == "object":
        return isinstance(value, dict)
    if value_type == "array":
        return isinstance(value, list)
    return False


def _validate_cpp_api_args(api_name, args):
    spec = _ensure_cpp_api_method(api_name)
    if spec is None:
        return None
    _validate_cpp_api_caller(api_name, spec, _CPP_EDITOR_API_CALLER_PYTHON_SCRIPT, "PythonScript")
    if not isinstance(args, list):
        raise RuntimeError(f"Editor API argument schema mismatch for {api_name}: args must be an array")
    params = spec.get("params", []) if isinstance(spec, dict) else []
    if len(args) > len(params):
        raise RuntimeError(f"Editor API argument schema mismatch for {api_name}: too many arguments")
    for index, param in enumerate(params):
        value_missing = index >= len(args)
        value = None if value_missing else args[index]
        if value_missing or value is None:
            if param.get("optional"):
                continue
            raise RuntimeError(
                f"Editor API argument schema mismatch for {api_name}: missing {param.get('name', index)}"
            )
        if not _cpp_value_matches_type(value, param.get("type")):
            raise RuntimeError(
                f"Editor API argument schema mismatch for {api_name}: "
                f"{param.get('name', index)} must be {param.get('type')}"
            )
    return spec


def _validate_cpp_api_return(api_name, data, spec):
    if not isinstance(spec, dict):
        return
    return_type = spec.get("return", "any")
    if not _cpp_value_matches_type(data, return_type):
        raise RuntimeError(
            f"Editor API return schema mismatch for {api_name}: data must be {return_type}"
        )


def _validate_cpp_api_event_payload(event_name, payload, event_spec):
    if not isinstance(event_spec, dict):
        return
    payload_type = event_spec.get("payload", "any")
    if not _cpp_value_matches_type(payload, payload_type):
        raise RuntimeError(
            f"Editor API event payload schema mismatch for {event_name}: payload must be {payload_type}"
        )


def _invoke_cpp_api(api_name, args=None, validate_method=True):
    """Invoke a C++ defined editor API method through the CoronaEngine binding."""
    normalized_args = args or []
    spec = None
    if validate_method:
        spec = _validate_cpp_api_args(api_name, normalized_args)
    import CoronaEngine

    payload = json.dumps(normalized_args, ensure_ascii=False)
    response_text = CoronaEngine._invoke_cpp_editor_api(api_name, payload)
    try:
        response = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid C++ Editor API response: {response_text}") from exc
    if not response.get("success", False):
        raise RuntimeError(response.get("error") or f"C++ Editor API failed: {api_name}")
    data = response.get("data")
    _validate_cpp_api_return(api_name, data, spec)
    return data


def _invoke_typed_cpp_api(api_name, wrapper_path, args=None):
    spec = _ensure_cpp_api_method(api_name)
    if spec.get("python_wrapper") != wrapper_path:
        raise RuntimeError(f"Python wrapper path is not defined by C++ manifest: {wrapper_path}")
    return _invoke_cpp_api(api_name, args)


def _invoke_manifest_cpp_api(wrapper_path, args=None):
    spec = _find_cpp_api_method_by_python_wrapper(wrapper_path)
    if spec is None:
        raise RuntimeError(f"Python wrapper path is not defined by C++ manifest: {wrapper_path}")
    return _invoke_typed_cpp_api(spec.get("api"), wrapper_path, args or [])


def _register_editor_api_event_callback(event_name, wrapper_name, callback):
    event_spec = _ensure_cpp_api_event(event_name)
    if event_spec.get("python_wrapper") != wrapper_name:
        raise RuntimeError(f"Editor API event wrapper is not defined by C++ manifest: {wrapper_name}")
    import CoronaEngine

    def _dispatch(payload_json, event):
        payload = json.loads(payload_json) if isinstance(payload_json, str) else payload_json
        _validate_cpp_api_event_payload(event_name, payload, event_spec)
        return callback(payload, event)

    return CoronaEngine.register_python_script_callback(event_name, _dispatch)


def _register_manifest_editor_api_event_callback(wrapper_name, callback):
    event_spec = _find_cpp_api_event_by_python_wrapper(wrapper_name)
    if event_spec is None:
        raise RuntimeError(f"Editor API event wrapper is not defined by C++ manifest: {wrapper_name}")
    return _register_editor_api_event_callback(event_spec.get("event"), wrapper_name, callback)


def _emit_cpp_editor_api_event(event_name, payload):
    event_spec = _ensure_cpp_api_event(event_name)
    _validate_cpp_api_event_payload(event_name, payload, event_spec)
    import CoronaEngine

    return CoronaEngine.emit_editor_api_event(event_name, json.dumps(payload))


def _emit_manifest_cpp_editor_api_event(wrapper_name, payload):
    event_spec = _find_cpp_api_event_by_python_wrapper(wrapper_name)
    if event_spec is None:
        raise RuntimeError(f"Editor API event wrapper is not defined by C++ manifest: {wrapper_name}")
    return _emit_cpp_editor_api_event(event_spec.get("event"), payload)


class _DynamicApiNamespace:
    def __init__(self, wrapper_path):
        self._wrapper_path = wrapper_path

    def __getattr__(self, name):
        wrapper_path = f"{self._wrapper_path}.{name}"
        method_spec = _find_cpp_api_method_by_python_wrapper(wrapper_path)
        if method_spec is not None:
            def _method(*args):
                return _invoke_manifest_cpp_api(wrapper_path, list(args))

            setattr(self, name, _method)
            return _method

        event_spec = _find_cpp_api_event_by_python_wrapper(wrapper_path)
        if event_spec is not None:
            def _on_event(callback):
                return _register_manifest_editor_api_event_callback(wrapper_path, callback)

            setattr(self, name, _on_event)
            return _on_event

        namespace = _DynamicApiNamespace(wrapper_path)
        setattr(self, name, namespace)
        return namespace


class _CoronaEditorApiMeta(type):
    def __getattr__(cls, name):
        return _DynamicApiNamespace(name)


class _ProjectApi(_DynamicApiNamespace):
    def __init__(self):
        super().__init__("project")

    @staticmethod
    def get_app_version():
        return _invoke_manifest_cpp_api("project.get_app_version", [])


class _EditorApi(_DynamicApiNamespace):
    def __init__(self):
        super().__init__("editor")

    @staticmethod
    def list_methods():
        return _invoke_typed_cpp_api("EditorApi.list_methods", "editor.list_methods", [])

    @staticmethod
    def list_events():
        return _invoke_typed_cpp_api("EditorApi.list_events", "editor.list_events", [])

    @staticmethod
    def off(callback_token):
        return _invoke_typed_cpp_api("EditorApi.unregister_callback", "editor.unregister_callback", [callback_token])


class _EventsApi(_DynamicApiNamespace):
    def __init__(self):
        super().__init__("events")

    @staticmethod
    def on_ai_chunk(callback):
        return _register_manifest_editor_api_event_callback("events.on_ai_chunk", callback)

    @staticmethod
    def on_log_batch(callback):
        return _register_manifest_editor_api_event_callback("events.on_log_batch", callback)

    @staticmethod
    def on_actor_changed(callback):
        return _register_manifest_editor_api_event_callback("events.on_actor_changed", callback)

    @staticmethod
    def on_actor_selection_changed(callback):
        return _register_manifest_editor_api_event_callback("events.on_actor_selection_changed", callback)

    @staticmethod
    def on_actor_transform_updated(callback):
        return _register_manifest_editor_api_event_callback("events.on_actor_transform_updated", callback)

    @staticmethod
    def on_actor_pick_result(callback):
        return _register_manifest_editor_api_event_callback("events.on_actor_pick_result", callback)

    @staticmethod
    def on_focus_pose_result(callback):
        return _register_manifest_editor_api_event_callback("events.on_focus_pose_result", callback)

    @staticmethod
    def on_scene_added(callback):
        return _register_manifest_editor_api_event_callback("events.on_scene_added", callback)

    @staticmethod
    def on_scene_renamed(callback):
        return _register_manifest_editor_api_event_callback("events.on_scene_renamed", callback)

    @staticmethod
    def on_project_opened(callback):
        return _register_manifest_editor_api_event_callback("events.on_project_opened", callback)

    @staticmethod
    def on_lan_chat_event(callback):
        return _register_manifest_editor_api_event_callback("events.on_lan_chat_event", callback)

    @staticmethod
    def on_network_actor_ownership_claimed(callback):
        return _register_manifest_editor_api_event_callback("events.on_network_actor_ownership_claimed", callback)

    @staticmethod
    def on_network_actor_delete_sync_broadcast_requested(callback):
        return _register_manifest_editor_api_event_callback("events.on_network_actor_delete_sync_broadcast_requested", callback)

    @staticmethod
    def on_network_actor_state_sync_broadcast_requested(callback):
        return _register_manifest_editor_api_event_callback("events.on_network_actor_state_sync_broadcast_requested", callback)

    @staticmethod
    def on_network_actor_sync_broadcast_requested(callback):
        return _register_manifest_editor_api_event_callback("events.on_network_actor_sync_broadcast_requested", callback)

    @staticmethod
    def on_network_actor_transform_sync_broadcast_requested(callback):
        return _register_manifest_editor_api_event_callback("events.on_network_actor_transform_sync_broadcast_requested", callback)

    @staticmethod
    def on_network_asset_import_completed(callback):
        return _register_manifest_editor_api_event_callback("events.on_network_asset_import_completed", callback)

    @staticmethod
    def on_network_file_sync_status_changed(callback):
        return _register_manifest_editor_api_event_callback("events.on_network_file_sync_status_changed", callback)

    @staticmethod
    def on_network_sync_pause_requested(callback):
        return _register_manifest_editor_api_event_callback("events.on_network_sync_pause_requested", callback)


class _SceneApi(_DynamicApiNamespace):
    def __init__(self):
        super().__init__("scene")

    @staticmethod
    def list_actor_tree(scene_name):
        return _invoke_manifest_cpp_api("scene.list_actor_tree", [scene_name])

    @staticmethod
    def select_actor(scene_name, actor_type, actor_name):
        return _invoke_manifest_cpp_api("scene.select_actor", [scene_name, actor_type, actor_name])


class _MainApi(_DynamicApiNamespace):
    def __init__(self):
        super().__init__("main")

    @staticmethod
    def scene_save(scene_name, snapshot=None):
        args = [scene_name]
        if snapshot is not None:
            args.append(snapshot)
        return _invoke_manifest_cpp_api("main.scene_save", args)


class CoronaEditorApi(metaclass=_CoronaEditorApiMeta):
    editor = _EditorApi()
    events = _EventsApi()
    project = _ProjectApi()
    scene = _SceneApi()
    main = _MainApi()
