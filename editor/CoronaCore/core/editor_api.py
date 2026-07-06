import json


def invoke_cpp_api(api_name, args=None):
    """Invoke a C++ defined editor API method through the CoronaEngine binding."""
    import CoronaEngine

    payload = json.dumps(args or [], ensure_ascii=False)
    response_text = CoronaEngine.invoke_cpp_api(api_name, payload)
    try:
        response = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid C++ Editor API response: {response_text}") from exc
    if not response.get("success", False):
        raise RuntimeError(response.get("error") or f"C++ Editor API failed: {api_name}")
    return response.get("data")


class _ProjectApi:
    @staticmethod
    def get_app_version():
        return invoke_cpp_api("ProjectLauncher.get_app_version", [])


class _SceneApi:
    @staticmethod
    def list_actor_tree(scene_name):
        return invoke_cpp_api("SceneTools.list_actor_tree", [scene_name])


class _MainApi:
    @staticmethod
    def scene_save(scene_name):
        return invoke_cpp_api("MainView.scene_save", [scene_name])


class CoronaEditorApi:
    invoke = staticmethod(invoke_cpp_api)
    project = _ProjectApi()
    scene = _SceneApi()
    main = _MainApi()
