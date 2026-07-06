import pathlib
import re
import unittest


class NativeSceneToolsRpcTests(unittest.TestCase):
    def _repo_root(self):
        return pathlib.Path(__file__).resolve().parents[4]

    def _handler_source(self):
        repo_root = self._repo_root()
        handler_path = repo_root / "src" / "systems" / "ui" / "cef" / "cef_editor_native_api_handlers.cpp"
        return handler_path.read_text(encoding="utf-8")

    def _editor_api_header(self):
        api_path = (
            self._repo_root()
            / "src"
            / "systems"
            / "ui"
            / "cef"
            / "cef_editor_api.h"
        )
        return api_path.read_text(encoding="utf-8")

    def _editor_api_source(self):
        api_path = (
            self._repo_root()
            / "src"
            / "systems"
            / "ui"
            / "cef"
            / "cef_editor_api.cpp"
        )
        return api_path.read_text(encoding="utf-8")

    def _native_api_header(self):
        return (
            self._repo_root()
            / "src"
            / "systems"
            / "ui"
            / "cef"
            / "cef_editor_native_api_registry.h"
        ).read_text(encoding="utf-8")

    def _query_bridge_source(self):
        return (
            self._repo_root()
            / "src"
            / "systems"
            / "ui"
            / "cef"
            / "cef_query_bridge.cpp"
        ).read_text(encoding="utf-8")

    def _frontend_bridge_source(self):
        return (
            self._repo_root() / "editor" / "Frontend" / "src" / "utils" / "bridge.js"
        ).read_text(encoding="utf-8")

    def _frontend_rpc_calls(self):
        bridge_source = self._frontend_bridge_source()
        return set(
            re.findall(
                r"Bridge\.callCEF\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]",
                bridge_source,
                re.S,
            )
        )

    def _native_rpc_methods(self):
        source = self._handler_source()
        module_map = {
            "project_launcher": "ProjectLauncher",
            "main_view": "MainView",
            "project_settings": "ProjectSettings",
            "scene_datas": "SceneDatas",
            "scene_tools": "SceneTools",
            "network": "Network",
            "lanchat": "LANChat",
        }
        methods = set()
        for register_name, module_name in module_map.items():
            match = re.search(
                rf"void register_{register_name}_api_handlers\(NativeApiRegistry& registry\) "
                rf"\{{(.*?)registry\.register_module\(\"{re.escape(module_name)}\"",
                source,
                re.S,
            )
            self.assertIsNotNone(match, module_name)
            for method in re.findall(r'\{"([A-Za-z0-9_]+)",\s*\[', match.group(1)):
                methods.add((module_name, method))
        return methods

    def _editor_api_methods(self):
        source = self._editor_api_source()
        return set(
            re.findall(
                r"EDITOR_API_METHOD(?:[A-Z0-9_]*)?\(([A-Za-z0-9_]+),\s*([A-Za-z0-9_]+)",
                source,
            )
        )

    def _frontend_editor_api_calls(self):
        bridge_source = self._frontend_bridge_source()
        return set(
            re.findall(
                r"editorApi\.invoke\(\s*['\"]([^'\"]+)['\"]",
                bridge_source,
                re.S,
            )
        )

    def test_rpc_contract_contains_all_frontend_calls(self):
        frontend_calls = self._frontend_rpc_calls()
        self.assertEqual(frontend_calls, set())

    def test_native_rpc_methods_are_all_in_contract(self):
        native_methods = self._native_rpc_methods()
        api_methods = self._editor_api_methods()
        missing = sorted(native_methods - api_methods)
        self.assertEqual(missing, [])

    def test_editor_api_has_no_python_backend(self):
        api_source = self._editor_api_source()
        api_header = self._editor_api_header()

        native_rpc_source = (
            self._repo_root() / "src" / "systems" / "ui" / "cef" / "cef_editor_native_api_registry.cpp"
        ).read_text(encoding="utf-8")
        editor_source = (
            self._repo_root() / "editor" / "CoronaCore" / "core" / "corona_editor.py"
        ).read_text(encoding="utf-8")
        bind_source = (
            self._repo_root() / "src" / "systems" / "ui" / "cef" / "cef_py_bind.cpp"
        ).read_text(encoding="utf-8")
        for text in (api_source, api_header, bind_source, editor_source):
            with self.subTest(source=text[:24]):
                self.assertNotIn("EditorApiBackend::Python", text)
                self.assertNotIn("register_editor_api_python_dispatcher", text)
                self.assertNotIn("unregister_editor_api_python_dispatcher", text)
                self.assertNotIn("dispatch_editor_api_from_cpp", text)
                self.assertNotIn("Python backend", text)
        self.assertNotIn("is_python_fallback_allowed", native_rpc_source)
        self.assertNotIn("_PYTHON_ROUTE_METHOD_ALLOWLIST", editor_source)
        self.assertNotIn("deal_func_from_js", editor_source)
        self.assertIn("register_python_script_dispatcher", bind_source)
        self.assertIn("dispatch_script_request_from_cpp", editor_source)

    def test_unknown_rpc_is_rejected_before_python(self):
        query_source = self._query_bridge_source()
        self.assertIn("EditorApiRegistry::instance().find", query_source)
        self.assertIn("unsupported_editor_api_route_json", query_source)
        self.assertNotIn("find_editor_rpc_spec", query_source)
        self.assertNotIn("parse_native_request", query_source)
        self.assertNotIn("native_unhandled", query_source)

    def test_cef_query_bridge_has_no_python_fallback(self):
        query_source = self._query_bridge_source()
        self.assertNotIn("deal_func_from_js", query_source)
        self.assertNotIn("is_python_fallback_allowed", query_source)
        self.assertNotIn("CEF RPC python fallback", query_source)
        self.assertNotIn("CefEditorRpcInterface", query_source)
        self.assertNotIn("PythonEditorRpcInterface", query_source)
        self.assertNotIn("PyImport_Import", query_source)
        self.assertNotIn("dispatch_from_cpp", query_source)
        self.assertNotIn("initialize_python", query_source)
        self.assertNotIn("pFunc_", query_source)
        self.assertNotIn("EditorApiBackend::Python", query_source)

    def test_editor_api_core_declares_cpp_defined_endpoint_contract(self):
        header = self._editor_api_header()
        source = self._editor_api_source()
        cmake = (
            self._repo_root() / "src" / "systems" / "ui" / "CMakeLists.txt"
        ).read_text(encoding="utf-8")

        for symbol in (
            "EditorApiRegistry",
            "EditorApiMethodSpec",
            "EditorApiEndpointBase",
            "CefEditorApiEndpoint",
            "PythonEditorApiEndpoint",
            "register_python_script_dispatcher",
            "unregister_python_script_dispatcher",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, header)

        self.assertNotIn("CefEditorApiEndpoint(PyObject*", header)
        self.assertIn("Python script dispatcher is not registered", source)
        self.assertIn("EDITOR_API_METHOD0(ProjectLauncher, get_app_version", source)
        self.assertIn("EDITOR_API_METHOD1(SceneTools, list_actor_tree", source)
        self.assertIn(
            "EDITOR_API_METHOD_SCHEMA(MainView, scene_save, kSceneNameParam, EditorApiValueType::Object)",
            source,
        )
        self.assertIn("cef/cef_editor_api.cpp", cmake)
        self.assertNotIn("cef/cef_editor_rpc_contract.cpp", cmake)

    def test_editor_api_registry_covers_all_native_handlers(self):
        api_methods = self._editor_api_methods()
        missing = []
        for module, method in sorted(self._native_rpc_methods()):
            if (module, method) not in api_methods:
                missing.append(f"{module}.{method}")
        self.assertEqual(missing, [])

    def test_frontend_native_backed_services_use_editor_api(self):
        bridge_source = self._frontend_bridge_source()
        native_methods = self._native_rpc_methods()
        legacy_native_calls = sorted(
            (module, method)
            for module, method in self._frontend_rpc_calls()
            if (module, method) in native_methods
        )
        self.assertEqual(legacy_native_calls, [])

    def test_frontend_services_no_longer_use_public_callcef(self):
        bridge_source = self._frontend_bridge_source()
        self.assertNotRegex(bridge_source, r"Bridge\.callCEF\(")

    def test_editor_api_registry_covers_all_frontend_editor_api_calls(self):
        api_methods = self._editor_api_methods()
        missing = []
        for api_name in sorted(self._frontend_editor_api_calls()):
            module, method = api_name.split(".", 1)
            if (module, method) not in api_methods:
                missing.append(api_name)
        self.assertEqual(missing, [])

    def test_editor_api_registry_includes_script_facade_methods_as_native_api(self):
        source = self._editor_api_source()
        expected = {
            "AITool.ai_rpc": "kObjectPayloadParam",
            "ScratchTool.execute_python_code": "kScratchExecutePythonCodeParams",
        }
        for api_name, params_name in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, EditorApiValueType::Any)",
                    source,
                )
        self.assertNotIn("EditorApiBackend::Python", source)

    def test_cef_query_accepts_editor_api_requests_before_legacy_rpc(self):
        query_source = self._query_bridge_source()
        self.assertIn("CefEditorApiEndpoint", query_source)
        self.assertIn("parse_editor_api_request(request_payload", query_source)
        self.assertNotIn("find_editor_rpc_spec", query_source)
        self.assertNotIn("parse_native_request", query_source)
        self.assertNotIn('request_payload.find("module")', query_source)

    def test_old_public_rpc_contract_is_removed(self):
        repo_root = self._repo_root()
        self.assertFalse(
            (repo_root / "src" / "systems" / "ui" / "cef" / "cef_editor_rpc_contract.cpp").exists()
        )
        native_header = self._native_api_header()
        for symbol in (
            "EditorRpcId",
            "EditorRpcBackend",
            "EditorRpcSpec",
            "find_editor_rpc_spec",
            "EditorRpcInterfaceBase",
            "CefEditorRpcInterface",
            "PythonEditorRpcInterface",
        ):
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, native_header)

    def test_frontend_sample_methods_use_editor_api_not_public_rpc(self):
        bridge_source = self._frontend_bridge_source()
        self.assertIn("export const editorApi", bridge_source)
        self.assertIn("callEditorApi", bridge_source)
        for snippet in (
            "getAppVersion: () => editorApi.project.getAppVersion()",
            "listActorTree: (sceneName) => editorApi.scene.listActorTree(sceneName)",
            "sceneSave: (sceneName) => editorApi.main.sceneSave(sceneName)",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_python_editor_api_wrapper_consumes_cpp_defined_methods(self):
        api_source = (
            self._repo_root()
            / "editor"
            / "CoronaCore"
            / "core"
            / "editor_api.py"
        ).read_text(encoding="utf-8")
        self.assertIn("class CoronaEditorApi", api_source)
        self.assertIn("invoke_cpp_api", api_source)
        self.assertIn("ProjectLauncher.get_app_version", api_source)
        self.assertIn("SceneTools.list_actor_tree", api_source)
        self.assertIn("MainView.scene_save", api_source)

    def test_python_script_dispatcher_is_registered_explicitly(self):
        repo_root = self._repo_root()
        bind_source = (
            repo_root / "src" / "systems" / "ui" / "cef" / "cef_py_bind.cpp"
        ).read_text(encoding="utf-8")
        main_source = (repo_root / "editor" / "main.py").read_text(encoding="utf-8")
        editor_source = (
            repo_root / "editor" / "CoronaCore" / "core" / "corona_editor.py"
        ).read_text(encoding="utf-8")

        self.assertIn("register_python_script_dispatcher", bind_source)
        self.assertIn("unregister_python_script_dispatcher", bind_source)
        self.assertIn("editor.register_script_dispatcher()", main_source)
        self.assertIn("dispatch_script_request_from_cpp", editor_source)
        self.assertNotIn("register_editor_api_python_dispatcher", bind_source)
        self.assertNotIn("dispatch_editor_api_from_cpp", editor_source)
        self.assertIn("if 'api' in request", editor_source)
        self.assertIn("Editor API payload is not accepted by Python script dispatcher", editor_source)
        self.assertIn("request.get('module'", editor_source)
        self.assertIn("request.get('function'", editor_source)

    def test_editor_api_spec_defines_real_schema_and_events(self):
        header = self._editor_api_header()
        source = self._editor_api_source()

        for symbol in (
            "enum class EditorApiValueType",
            "struct EditorApiParamSpec",
            "struct EditorApiReturnSpec",
            "struct EditorApiEventSpec",
            "class EditorApiCallbackRegistry",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, header)

        for snippet in (
            'EDITOR_API_METHOD0(ProjectLauncher, get_app_version, EditorApiValueType::String)',
            'EDITOR_API_METHOD1(SceneTools, list_actor_tree, "scene_name", EditorApiValueType::String, EditorApiValueType::Array)',
            "EDITOR_API_METHOD_SCHEMA(MainView, scene_save, kSceneNameParam, EditorApiValueType::Object)",
            '"SceneTools.actorChanged"',
            '"ProjectLauncher.projectOpened"',
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, source)

        self.assertNotIn('"json[]"', source)

    def test_editor_api_validates_arguments_and_results(self):
        source = self._editor_api_source()

        self.assertIn("validate_editor_api_args", source)
        self.assertIn("validate_editor_api_result", source)
        self.assertIn("invalid Editor API arguments", source)
        self.assertIn("invalid Editor API result", source)

        invoke_start = source.find("NativeResult EditorApiRegistry::invoke")
        self.assertGreaterEqual(invoke_start, 0)
        invoke_end = source.find("std::optional<EditorApiRequest> parse_editor_api_request", invoke_start)
        self.assertGreater(invoke_end, invoke_start)
        invoke_body = source[invoke_start:invoke_end]
        args_pos = invoke_body.find("validate_editor_api_args(")
        native_pos = invoke_body.find("invoke_native_api_method(")
        result_pos = invoke_body.find("validate_editor_api_result(")
        self.assertGreaterEqual(args_pos, 0)
        self.assertGreater(native_pos, args_pos)
        self.assertGreater(result_pos, native_pos)

    def test_editor_api_registry_has_no_unspecified_method_entries(self):
        source = self._editor_api_source()

        registry_start = source.find("constexpr std::array<EditorApiMethodSpec")
        self.assertGreaterEqual(registry_start, 0)
        registry_end = source.find("}};", registry_start)
        self.assertGreater(registry_end, registry_start)
        registry_body = source[registry_start:registry_end]
        self.assertNotIn("EDITOR_API_METHOD(", registry_body)
        self.assertIn(
            "EDITOR_API_METHOD_SCHEMA(ScratchTool, execute_python_code, kScratchExecutePythonCodeParams, EditorApiValueType::Any)",
            source,
        )
        validation_start = source.find("NativeResult validate_editor_api_args")
        self.assertGreaterEqual(validation_start, 0)
        validation_end = source.find("NativeResult validate_editor_api_result", validation_start)
        self.assertGreater(validation_end, validation_start)
        validation_body = source[validation_start:validation_end]
        self.assertIn("spec.params == nullptr", validation_body)
        self.assertIn("Unspecified Editor API schema", validation_body)

    def test_scene_tools_common_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "SceneTools.create_actor": "kSceneToolsCreateActorParams",
            "SceneTools.remove_actor": "kSceneActorParams",
            "SceneTools.rename_actor": "kSceneToolsRenameActorParams",
            "SceneTools.open_actor": "kSceneActorParams",
            "SceneTools.focus_actor": "kSceneToolsFocusActorParams",
            "SceneTools.set_render_backend": "kSceneToolsSetRenderBackendParams",
            "SceneTools.get_render_backend": "kSceneToolsCameraOptionalParams",
            "SceneTools.set_vision_render_mode": "kSceneToolsSetVisionRenderModeParams",
            "SceneTools.get_vision_render_mode": "kSceneToolsCameraOptionalParams",
        }
        for api_name, params_name in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, EditorApiValueType::Object)",
                    source,
                )

        self.assertIn("value.is_null() && param_spec.optional", source)

    def test_editor_api_callback_registry_replaces_placeholder_tokens(self):
        header = self._editor_api_header()
        source = self._editor_api_source()

        for symbol in (
            "register_cef_callback",
            "register_python_script_callback",
            "emit_editor_api_event",
            "emit_python_script_event",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, header + source)

        self.assertNotIn("return g_next_callback_token.fetch_add(1);", source)
        self.assertNotIn("return callback_token != 0;", source)
        self.assertIn("EditorApiCallbackRegistry::instance()", source)

    def test_frontend_bridge_exposes_event_subscription_helpers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "on: (eventName, callback)",
            "off: (callbackToken)",
            "__coronaEditorApiDispatch",
            "register_editor_api_callback",
            "unregister_editor_api_callback",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_scene_tools_schema_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "sceneTools: {",
            "createActor: (sceneName, objPath, actorType = 'model', actorData = null)",
            "removeActor: (sceneName, actorName)",
            "renameActor: (sceneName, actorName, name)",
            "focusActor: (sceneName, actorName, cameraName)",
            "setRenderBackend: (mode, sceneName = null, cameraId = null)",
            "getRenderBackend: (sceneName = null, cameraId = null)",
            "setVisionRenderMode: (sceneName, cameraId = null, mode = 'path_tracing')",
            "getVisionRenderMode: (sceneName, cameraId = null)",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_scene_tools_scene_camera_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "SceneTools.create_scene": ("kSceneNameParam", "EditorApiValueType::Object"),
            "SceneTools.list_scene_tree": ("kSceneNameParam", "EditorApiValueType::Object"),
            "SceneTools.reload_scene": ("kSceneToolsReloadSceneParams", "EditorApiValueType::Object"),
            "SceneTools.create_camera_view": ("kSceneToolsCreateCameraViewParams", "EditorApiValueType::Object"),
            "SceneTools.open_camera_view": ("kSceneCameraParams", "EditorApiValueType::Object"),
            "SceneTools.close_camera_view": ("kSceneCameraParams", "EditorApiValueType::Object"),
            "SceneTools.rename_camera_view": ("kSceneToolsRenameCameraViewParams", "EditorApiValueType::Object"),
            "SceneTools.list_camera_views": ("kSceneNameParam", "EditorApiValueType::Object"),
            "SceneTools.update_camera_view": ("kSceneToolsUpdateCameraViewParams", "EditorApiValueType::Object"),
            "SceneTools.delete_camera": ("kSceneCameraParams", "EditorApiValueType::Object"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_scene_tools_camera_lifecycle_apis_are_native_handlers(self):
        source = self._handler_source()
        for method in (
            "create_camera_view",
            "open_camera_view",
            "close_camera_view",
            "rename_camera_view",
            "update_camera_view",
            "delete_camera",
        ):
            with self.subTest(method=method):
                self.assertNotIn(f'{{"{method}", script_method}}', source)
                self.assertIn(f'{{"{method}", [](const NativeRequest& request', source)

    def test_scene_tools_scene_camera_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "createScene: (sceneName) =>\n    editorApi.sceneTools.createScene",
            "createCameraView: (sceneName, name = null) =>\n    editorApi.sceneTools.createCameraView",
            "openCameraView: (sceneName, cameraId) =>\n    editorApi.sceneTools.openCameraView",
            "closeCameraView: (sceneName, cameraId) =>\n    editorApi.sceneTools.closeCameraView",
            "renameCameraView: (sceneName, cameraId, name) =>\n    editorApi.sceneTools.renameCameraView",
            "listCameraViews: (sceneName) =>\n    editorApi.sceneTools.listCameraViews",
            "updateCameraView: (sceneName, cameraId, state) =>\n    editorApi.sceneTools.updateCameraView",
            "deleteCamera: (sceneName, cameraId) =>\n    editorApi.sceneTools.deleteCamera",
            "reloadScene: (sceneName, projectPath = '') =>\n    editorApi.sceneTools.reloadScene",
            "listSceneTree: (sceneName) => editorApi.sceneTools.listSceneTree(sceneName)",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

        for snippet in (
            "createActor: (sceneName, objPath, actorType = 'model', actorData = null) =>\n    editorApi.sceneTools.createActor",
            "removeActor: (sceneName, actorName) =>\n    editorApi.sceneTools.removeActor",
            "renameActor: (sceneName, actorName, name) =>\n    editorApi.sceneTools.renameActor",
            "focusActor: (sceneName, actorName, cameraName) =>\n    editorApi.sceneTools.focusActor",
            "setRenderBackend: (mode, sceneName = null, cameraId = null) =>\n    editorApi.sceneTools.setRenderBackend",
            "getRenderBackend: (sceneName = null, cameraId = null) =>\n    editorApi.sceneTools.getRenderBackend",
            "setVisionRenderMode: (sceneName, cameraId = null, mode = 'path_tracing') =>\n    editorApi.sceneTools.setVisionRenderMode",
            "getVisionRenderMode: (sceneName, cameraId = null) =>\n    editorApi.sceneTools.getVisionRenderMode",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_scene_tools_environment_render_audio_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "SceneTools.sun_direction": ("kSceneToolsSunDirectionParams", "EditorApiValueType::Object"),
            "SceneTools.floor_grid": ("kSceneToolsFloorGridParams", "EditorApiValueType::Object"),
            "SceneTools.set_physics_params": ("kSceneToolsSetPhysicsParams", "EditorApiValueType::Object"),
            "SceneTools.get_physics_params": ("kSceneNameParam", "EditorApiValueType::Object"),
            "SceneTools.select_screenshot_path": ("kSceneToolsCameraOptionalParams", "EditorApiValueType::Object"),
            "SceneTools.save_screenshot": ("kSceneToolsSaveScreenshotParams", "EditorApiValueType::Object"),
            "SceneTools.set_output_mode": ("kSceneToolsSetOutputModeParams", "EditorApiValueType::Object"),
            "SceneTools.get_output_mode": ("kSceneToolsCameraOptionalParams", "EditorApiValueType::Object"),
            "SceneTools.set_shadow_cascade_debug": ("kSceneToolsSetCameraBoolParams", "EditorApiValueType::Object"),
            "SceneTools.get_shadow_cascade_debug": ("kSceneToolsCameraOptionalParams", "EditorApiValueType::Object"),
            "SceneTools.set_ssao_enabled": ("kSceneToolsSetCameraBoolParams", "EditorApiValueType::Object"),
            "SceneTools.get_ssao_enabled": ("kSceneToolsCameraOptionalParams", "EditorApiValueType::Object"),
            "SceneTools.is_vision_available": ("kNoParams", "EditorApiValueType::Object"),
            "SceneTools.load_vision_scene": ("kPathParam", "EditorApiValueType::Object"),
            "SceneTools.pick_actor_at_pixel": ("kSceneToolsPickActorParams", "EditorApiValueType::Object"),
            "SceneTools.play_audio": ("kSceneToolsPlayAudioParams", "EditorApiValueType::Object"),
            "SceneTools.stop_audio": ("kResourceIdParam", "EditorApiValueType::Object"),
            "SceneTools.actor_play_audio": ("kSceneToolsActorPlayAudioParams", "EditorApiValueType::Object"),
            "SceneTools.actor_stop_audio": ("kActorNameParam", "EditorApiValueType::Object"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_scene_tools_environment_render_audio_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "sunDirection: (sceneName, enable, direction) =>\n    editorApi.sceneTools.sunDirection",
            "floorGrid: (sceneName, enabled) =>\n    editorApi.sceneTools.floorGrid",
            "setPhysicsParams: (sceneName, params) =>\n    editorApi.sceneTools.setPhysicsParams",
            "getPhysicsParams: (sceneName) => editorApi.sceneTools.getPhysicsParams(sceneName)",
            "selectScreenshotPath: (sceneName, cameraName) =>\n    editorApi.sceneTools.selectScreenshotPath",
            "saveScreenshot: (sceneName, path, cameraName) =>\n    editorApi.sceneTools.saveScreenshot",
            "setOutputMode: (sceneName, cameraName, mode) =>\n    editorApi.sceneTools.setOutputMode",
            "getOutputMode: (sceneName, cameraName) =>\n    editorApi.sceneTools.getOutputMode",
            "setShadowCascadeDebug: (sceneName, cameraName, enabled) =>\n    editorApi.sceneTools.setShadowCascadeDebug",
            "getShadowCascadeDebug: (sceneName, cameraName) =>\n    editorApi.sceneTools.getShadowCascadeDebug",
            "setSsaoEnabled: (sceneName, cameraName, enabled) =>\n    editorApi.sceneTools.setSsaoEnabled",
            "getSsaoEnabled: (sceneName, cameraName) =>\n    editorApi.sceneTools.getSsaoEnabled",
            "isVisionAvailable: () => editorApi.sceneTools.isVisionAvailable()",
            "loadVisionScene: (path) => editorApi.sceneTools.loadVisionScene(path)",
            "pickActor: (sceneName, x, y, vpWidth, vpHeight) =>\n    editorApi.sceneTools.pickActor",
            "playAudio: (resourceId, loop) =>\n    editorApi.sceneTools.playAudio",
            "stopAudio: (resourceId) =>\n    editorApi.sceneTools.stopAudio",
            "actorPlayAudio: (actorName, loop = false) =>\n    editorApi.sceneTools.actorPlayAudio",
            "actorStopAudio: (actorName) =>\n    editorApi.sceneTools.actorStopAudio",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_scene_datas_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "SceneDatas.get_scene": ("kSceneNameOptionalParam", "EditorApiValueType::Object"),
            "SceneDatas.get_actor": ("kSceneActorParams", "EditorApiValueType::Object"),
            "SceneDatas.actor_operation": ("kSceneDatasActorOperationParams", "EditorApiValueType::Object"),
            "SceneDatas.save_actor": ("kSceneActorParams", "EditorApiValueType::Object"),
            "SceneDatas.select_model_file": ("kSceneDatasSelectModelFileParams", "EditorApiValueType::String"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_scene_datas_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "sceneDatas: {",
            "getScene: (sceneId) => Bridge.callEditorApi('SceneDatas.get_scene', [sceneId])",
            "getActor: (sceneId, actorId) => Bridge.callEditorApi('SceneDatas.get_actor', [sceneId, actorId])",
            "actorOperation: (sceneName, actorName, operation, vector) =>",
            "saveActor: (sceneName, actorName) =>",
            "selectModelFile: (sceneId, actorId, fileType) =>",
            "getScene: (sceneId) => editorApi.sceneDatas.getScene(sceneId)",
            "getActor: (sceneId, actorId) => editorApi.sceneDatas.getActor(sceneId, actorId)",
            "actorOperation: (scene_name, actor_name, operation, vector) =>\n    editorApi.sceneDatas.actorOperation",
            "saveActor: (sceneName, actorName) =>\n    editorApi.sceneDatas.saveActor",
            "selectModelFileDialog: (sceneId, actorId, fileType) =>\n    editorApi.sceneDatas.selectModelFile",
            "setCameraLock: (sceneName, actorName, enabled) =>\n    editorApi.sceneDatas.actorOperation",
            "setCameraLockOffset: (sceneName, actorName, offset) =>\n    editorApi.sceneDatas.actorOperation",
            "setCameraLockRotation: (sceneName, actorName, rotation) =>\n    editorApi.sceneDatas.actorOperation",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_scene_tree_and_property_handlers_respect_scene_route_args(self):
        source = self._handler_source()

        self.assertIn("NativeEditorScene* scene_for_request_route", source)
        expected = (
            '{"get_scene", [](const NativeRequest& request',
            '{"get_actor", [](const NativeRequest& request',
            '{"actor_operation", [](const NativeRequest& request',
            '{"save_actor", [](const NativeRequest& request',
            '{"list_scene_tree", [](const NativeRequest& request',
            '{"list_actor_tree", [](const NativeRequest& request',
            '{"rename_actor", [](const NativeRequest& request',
            '{"list_camera_views", [](const NativeRequest& request',
        )
        for snippet in expected:
            with self.subTest(snippet=snippet):
                start = source.find(snippet)
                self.assertGreaterEqual(start, 0)
                body = source[start:source.find("}},", start)]
                self.assertIn("scene_for_request_route(request)", body)

    def test_project_launcher_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "ProjectLauncher.browse_folder": ("kPathOptionalParam", "EditorApiValueType::String"),
            "ProjectLauncher.create_multiplayer_project": ("kObjectPayloadParam", "EditorApiValueType::Object"),
            "ProjectLauncher.create_project": ("kObjectPayloadParam", "EditorApiValueType::String"),
            "ProjectLauncher.create_world_project": ("kObjectPayloadParam", "EditorApiValueType::Object"),
            "ProjectLauncher.get_default_project_path": ("kNoParams", "EditorApiValueType::String"),
            "ProjectLauncher.get_recent_projects": ("kNoParams", "EditorApiValueType::Array"),
            "ProjectLauncher.open_project": ("kPathParam", "EditorApiValueType::Object"),
            "ProjectLauncher.open_project_file": ("kNoParams", "EditorApiValueType::Object"),
            "ProjectLauncher.set_project_mode": ("kObjectPayloadParam", "EditorApiValueType::Boolean"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_project_launcher_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "getDefaultProjectPath: () => editorApi.project.getDefaultProjectPath()",
            "browseFolder: (default_path) =>\n    editorApi.project.browseFolder",
            "openProjectFile: () => editorApi.project.openProjectFile()",
            "createProject: (projectData) =>\n    editorApi.project.createProject",
            "createWorldProject: (worldData) =>\n    editorApi.project.createWorldProject",
            "createMultiplayerProject: (projectData) =>\n    editorApi.project.createMultiplayerProject",
            "openProject: (projectPath) =>\n    editorApi.project.openProject",
            "setProjectMode: (mode, settings) =>\n    editorApi.project.setProjectMode",
            "getRecentProjects: () => editorApi.project.getRecentProjects()",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_project_settings_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "ProjectSettings.browse_scene_file": ("kNoParams", "EditorApiValueType::Object"),
            "ProjectSettings.get_active_project_info": ("kNoParams", "EditorApiValueType::Object"),
            "ProjectSettings.save_active_project_info": ("kObjectPayloadParam", "EditorApiValueType::Object"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_project_settings_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "projectSettings: {",
            "getActiveProjectInfo: () => Bridge.callEditorApi('ProjectSettings.get_active_project_info', [])",
            "saveActiveProjectInfo: (settings) =>",
            "browseSceneFile: () => Bridge.callEditorApi('ProjectSettings.browse_scene_file', [])",
            "getActiveProjectInfo: () => editorApi.projectSettings.getActiveProjectInfo()",
            "saveActiveProjectInfo: (settings) =>\n    editorApi.projectSettings.saveActiveProjectInfo",
            "browseSceneFile: () => editorApi.projectSettings.browseSceneFile()",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_corona_editor_app_api_has_explicit_schema_and_wrapper(self):
        source = self._editor_api_source()
        bridge_source = self._frontend_bridge_source()

        self.assertIn(
            "EDITOR_API_METHOD_SCHEMA(CoronaEditor, close_process, kNoParams, EditorApiValueType::Null)",
            source,
        )
        for snippet in (
            "app: {",
            "closeProcess: () => Bridge.callEditorApi('CoronaEditor.close_process', [])",
            "closeProcess: () => editorApi.app.closeProcess()",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_file_manager_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "FileManager.create_file": ("kFileManagerCreateFileParams", "EditorApiValueType::Boolean"),
            "FileManager.create_folder": ("kFileManagerCreateFolderParams", "EditorApiValueType::Boolean"),
            "FileManager.delete_item": ("kPathParam", "EditorApiValueType::Boolean"),
            "FileManager.get_file_tree": ("kPathOptionalParam", "EditorApiValueType::Object"),
            "FileManager.get_files": ("kPathOptionalParam", "EditorApiValueType::Array"),
            "FileManager.get_project_info": ("kNoParams", "EditorApiValueType::Object"),
            "FileManager.open_file": ("kFileManagerOpenFileParams", "EditorApiValueType::Boolean"),
            "FileManager.rename_item": ("kFileManagerRenameItemParams", "EditorApiValueType::Boolean"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_file_manager_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "files: {",
            "getProjectInfo: () => Bridge.callEditorApi('FileManager.get_project_info', [])",
            "getFiles: (relPath = '') =>",
            "getFileTree: (relPath = '') =>",
            "createFolder: (path, folderName) =>",
            "createFile: (path, fileName, type) =>",
            "deleteItem: (path) => Bridge.callEditorApi('FileManager.delete_item', [path])",
            "renameItem: (oldPath, newName) =>",
            "openFile: (filePath, fileType) =>",
            "getProjectInfo: () => editorApi.files.getProjectInfo()",
            "getFiles: (relPath) => editorApi.files.getFiles(relPath)",
            "getFileTree: (relPath) => editorApi.files.getFileTree(relPath)",
            "createFolder: (path, folderName) =>\n    editorApi.files.createFolder",
            "createFile: (path, fileName, type) =>\n    editorApi.files.createFile",
            "deleteItem: (path) => editorApi.files.deleteItem(path)",
            "renameItem: (oldPath, newName) =>\n    editorApi.files.renameItem",
            "openFile: (filePath, fileType) =>\n    editorApi.files.openFile",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_resource_search_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "ResourceSearch.focus_actor": ("kResourceSearchFocusActorParams", "EditorApiValueType::Object"),
            "ResourceSearch.fuzzy_search": ("kResourceSearchFuzzySearchParams", "EditorApiValueType::Object"),
            "ResourceSearch.get_stats": ("kCallerParam", "EditorApiValueType::Object"),
            "ResourceSearch.image_search": ("kResourceSearchImageSearchParams", "EditorApiValueType::Object"),
            "ResourceSearch.list_types": ("kCallerParam", "EditorApiValueType::Object"),
            "ResourceSearch.mark_index_dirty": ("kResourceSearchMarkIndexDirtyParams", "EditorApiValueType::Object"),
            "ResourceSearch.prepare_index": ("kCallerParam", "EditorApiValueType::Object"),
            "ResourceSearch.rebuild_index": ("kCallerParam", "EditorApiValueType::Object"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_resource_search_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "resourceSearch: {",
            "prepareIndex: (caller = CURRENT_CALLER) =>",
            "fuzzySearch: (query, topK = 20, typeFilter = null, caller = CURRENT_CALLER) =>",
            "imageSearch: (imageB64, topK = 20, threshold = 10, caller = CURRENT_CALLER) =>",
            "listTypes: (caller = CURRENT_CALLER) =>",
            "rebuildIndex: (caller = CURRENT_CALLER) =>",
            "getStats: (caller = CURRENT_CALLER) =>",
            "markIndexDirty: (reason = 'frontend', caller = CURRENT_CALLER) =>",
            "focusActor: (sceneName, actorName, caller = CURRENT_CALLER) =>",
            "? editorApi.resourceSearch.prepareIndex()",
            "? editorApi.resourceSearch.fuzzySearch(query, topK, typeFilter)",
            "? editorApi.resourceSearch.imageSearch(imageB64, topK, threshold)",
            "? editorApi.resourceSearch.listTypes()",
            "? editorApi.resourceSearch.rebuildIndex()",
            "? editorApi.resourceSearch.getStats()",
            "? editorApi.resourceSearch.markIndexDirty(reason)",
            "? editorApi.resourceSearch.focusActor(sceneName, actorName)",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_network_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "Network.broadcast_actor_create": ("kNetworkBroadcastActorCreateParams", "EditorApiValueType::Object"),
            "Network.broadcast_actor_delete": ("kNetworkBroadcastActorDeleteParams", "EditorApiValueType::Object"),
            "Network.broadcast_actor_scene_snapshot": ("kNetworkBroadcastSceneSnapshotParams", "EditorApiValueType::Object"),
            "Network.broadcast_actor_state_update": ("kNetworkActorStateUpdateParams", "EditorApiValueType::Object"),
            "Network.broadcast_actor_transform": ("kNetworkActorStateUpdateParams", "EditorApiValueType::Object"),
            "Network.claim_actor_ownership": ("kActorGuidParam", "EditorApiValueType::Object"),
            "Network.connect_to_peer": ("kNetworkConnectToPeerParams", "EditorApiValueType::Object"),
            "Network.get_peer_count": ("kNoParams", "EditorApiValueType::Object"),
            "Network.get_session_info": ("kNoParams", "EditorApiValueType::Object"),
            "Network.poll_pending_actor_create": ("kNoParams", "EditorApiValueType::Object"),
            "Network.poll_pending_actor_delete": ("kNoParams", "EditorApiValueType::Object"),
            "Network.poll_pending_actor_scene_snapshot": ("kNoParams", "EditorApiValueType::Object"),
            "Network.poll_pending_actor_scene_snapshot_request": ("kNoParams", "EditorApiValueType::Object"),
            "Network.poll_pending_actor_state_update": ("kNoParams", "EditorApiValueType::Object"),
            "Network.poll_pending_actor_transform": ("kNoParams", "EditorApiValueType::Object"),
            "Network.register_actor_identity": ("kNetworkRegisterActorIdentityParams", "EditorApiValueType::Object"),
            "Network.request_actor_scene_snapshot": ("kSceneNameParam", "EditorApiValueType::Object"),
            "Network.set_project_root": ("kProjectRootParam", "EditorApiValueType::Object"),
            "Network.set_sync_paused": ("kPausedParam", "EditorApiValueType::Object"),
            "Network.start_session": ("kNetworkStartSessionParams", "EditorApiValueType::Object"),
            "Network.stop_session": ("kNoParams", "EditorApiValueType::Object"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_network_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "network: {",
            "startSession: (instanceName, projectId, port = 27960, role = 'host') =>",
            "stopSession: () => Bridge.callEditorApi('Network.stop_session', [])",
            "getPeerCount: () => Bridge.callEditorApi('Network.get_peer_count', [])",
            "getSessionInfo: () => Bridge.callEditorApi('Network.get_session_info', [])",
            "connectToPeer: (ip, port, peerName) =>",
            "setProjectRoot: (projectRoot) =>",
            "broadcastActorCreate: (actorGuid, sceneName, modelPath, actorData) =>",
            "broadcastActorTransform: (actorGuid, sceneName, actorData) =>",
            "broadcastActorDelete: (actorGuid, sceneName, actorName) =>",
            "requestSceneSnapshot: (sceneName) =>",
            "broadcastSceneSnapshot: (sceneName, snapshot) =>",
            "broadcastActorStateUpdate: (actorGuid, sceneName, actorData) =>",
            "pollPendingActorCreate: () => Bridge.callEditorApi('Network.poll_pending_actor_create', [])",
            "pollPendingActorTransform: () => Bridge.callEditorApi('Network.poll_pending_actor_transform', [])",
            "pollPendingActorDelete: () => Bridge.callEditorApi('Network.poll_pending_actor_delete', [])",
            "pollPendingSceneSnapshotRequest: () =>",
            "pollPendingSceneSnapshot: () => Bridge.callEditorApi('Network.poll_pending_actor_scene_snapshot', [])",
            "pollPendingActorStateUpdate: () => Bridge.callEditorApi('Network.poll_pending_actor_state_update', [])",
            "setSyncPaused: (paused) => Bridge.callEditorApi('Network.set_sync_paused', [!!paused])",
            "registerActorIdentity: (actorGuid, actorHandle, locallyOwned = true) =>",
            "claimActorOwnership: (actorGuid) =>",
            "startSession: (instanceName, projectId, port = 27960, role = 'host') =>\n    editorApi.network.startSession",
            "stopSession: () => editorApi.network.stopSession().then(_unwrap)",
            "getPeerCount: () => editorApi.network.getPeerCount().then(_unwrap)",
            "getSessionInfo: () => editorApi.network.getSessionInfo().then(_unwrap)",
            "connectToPeer: (ip, port, peerName) =>\n    editorApi.network.connectToPeer",
            "setProjectRoot: (projectRoot) =>\n    editorApi.network.setProjectRoot",
            "broadcastActorCreate: (actorGuid, sceneName, modelPath, actorData) =>\n    editorApi.network.broadcastActorCreate",
            "registerActorIdentity: (actorGuid, actorHandle, locallyOwned = true) =>\n    editorApi.network.registerActorIdentity",
            "claimActorOwnership: (actorGuid) =>\n    editorApi.network.claimActorOwnership",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_lanchat_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "LANChat.add_agent": ("kObjectPayloadParam", "EditorApiValueType::Object"),
            "LANChat.get_history": ("kNoParams", "EditorApiValueType::Object"),
            "LANChat.get_local_ip": ("kNoParams", "EditorApiValueType::Object"),
            "LANChat.join_room": ("kObjectPayloadParam", "EditorApiValueType::Object"),
            "LANChat.leave_room": ("kNoParams", "EditorApiValueType::Object"),
            "LANChat.list_agents": ("kNoParams", "EditorApiValueType::Object"),
            "LANChat.list_history_rooms": ("kNoParams", "EditorApiValueType::Object"),
            "LANChat.load_history_room": ("kObjectPayloadParam", "EditorApiValueType::Object"),
            "LANChat.remove_agent": ("kObjectPayloadParam", "EditorApiValueType::Object"),
            "LANChat.send_message": ("kObjectPayloadParam", "EditorApiValueType::Object"),
            "LANChat.start_local_room": ("kObjectPayloadParam", "EditorApiValueType::Object"),
            "LANChat.start_room": ("kObjectPayloadParam", "EditorApiValueType::Object"),
            "LANChat.stop_local_room": ("kNoParams", "EditorApiValueType::Object"),
            "LANChat.stop_room": ("kNoParams", "EditorApiValueType::Object"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_lanchat_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "lanChat: {",
            "startRoom: (payload) => Bridge.callEditorApi('LANChat.start_room', [payload || {}])",
            "startLocalRoom: (payload) => Bridge.callEditorApi('LANChat.start_local_room', [payload || {}])",
            "stopRoom: () => Bridge.callEditorApi('LANChat.stop_room', [])",
            "stopLocalRoom: () => Bridge.callEditorApi('LANChat.stop_local_room', [])",
            "joinRoom: (payload) => Bridge.callEditorApi('LANChat.join_room', [payload || {}])",
            "getHistory: () => Bridge.callEditorApi('LANChat.get_history', [])",
            "listHistoryRooms: () => Bridge.callEditorApi('LANChat.list_history_rooms', [])",
            "loadHistoryRoom: (room) => Bridge.callEditorApi('LANChat.load_history_room', [{ room }])",
            "leaveRoom: () => Bridge.callEditorApi('LANChat.leave_room', [])",
            "sendMessage: (text, options = {}) =>",
            "getLocalIp: () => Bridge.callEditorApi('LANChat.get_local_ip', [])",
            "addAgent: (payload) => Bridge.callEditorApi('LANChat.add_agent', [payload || {}])",
            "removeAgent: (agentId) => Bridge.callEditorApi('LANChat.remove_agent', [{ agent_id: agentId }])",
            "listAgents: () => Bridge.callEditorApi('LANChat.list_agents', [])",
            "startRoom: (payload) => editorApi.lanChat.startRoom(payload).then(_unwrap)",
            "startLocalRoom: (payload) => editorApi.lanChat.startLocalRoom(payload).then(_unwrap)",
            "stopRoom: () => editorApi.lanChat.stopRoom().then(_unwrap)",
            "stopLocalRoom: () => editorApi.lanChat.stopLocalRoom().then(_unwrap)",
            "joinRoom: (payload) => editorApi.lanChat.joinRoom(payload).then(_unwrap)",
            "getHistory: () => editorApi.lanChat.getHistory().then(_unwrap)",
            "listHistoryRooms: () => editorApi.lanChat.listHistoryRooms().then(_unwrap)",
            "loadHistoryRoom: (room) => editorApi.lanChat.loadHistoryRoom(room).then(_unwrap)",
            "leaveRoom: () => editorApi.lanChat.leaveRoom().then(_unwrap)",
            "sendMessage: (text, options = {}) =>\n    editorApi.lanChat.sendMessage",
            "getLocalIp: () => editorApi.lanChat.getLocalIp().then(_unwrap)",
            "addAgent: (payload) => editorApi.lanChat.addAgent(payload).then(_unwrap)",
            "removeAgent: (agentId) => editorApi.lanChat.removeAgent(agentId).then(_unwrap)",
            "listAgents: () => editorApi.lanChat.listAgents().then(_unwrap)",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_script_facade_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "AITool.ai_rpc": ("kObjectPayloadParam", "EditorApiValueType::Any"),
            "AITool.generate_hint": ("kAiToolGenerateHintParams", "EditorApiValueType::Any"),
            "AITool.read_local_file_as_base64": ("kPathParam", "EditorApiValueType::Any"),
            "AITool.send_message_to_ai_stream": ("kAnyPayloadParam", "EditorApiValueType::Any"),
            "ScratchTool.execute_python_code": ("kScratchExecutePythonCodeParams", "EditorApiValueType::Any"),
            "ScratchTool.get_game_preview_status": ("kNoParams", "EditorApiValueType::Any"),
            "ScratchTool.get_script_status": ("kNoParams", "EditorApiValueType::Any"),
            "ScratchTool.key_event": ("kScratchKeyEventParams", "EditorApiValueType::Any"),
            "ScratchTool.key_release": ("kScratchKeyReleaseParams", "EditorApiValueType::Any"),
            "ScratchTool.load_blockly_target": ("kObjectPayloadParam", "EditorApiValueType::Any"),
            "ScratchTool.mouse_event": ("kScratchMouseEventParams", "EditorApiValueType::Any"),
            "ScratchTool.save_blockly_target": ("kObjectPayloadParam", "EditorApiValueType::Any"),
            "ScratchTool.start_game_preview": ("kObjectPayloadParam", "EditorApiValueType::Any"),
            "ScratchTool.stop_game_preview": ("kNoParams", "EditorApiValueType::Any"),
            "ScratchTool.stop_script_execution": ("kNoParams", "EditorApiValueType::Any"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_script_facade_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "ai: {",
            "sendMessageToAIStream: (payload) => Bridge.callEditorApi('AITool.send_message_to_ai_stream', [payload])",
            "readLocalFileAsBase64: (filePath) => Bridge.callEditorApi('AITool.read_local_file_as_base64', [filePath])",
            "generateHint: (elementType, context = {}) =>",
            "chatStream: (request) => Bridge.callEditorApi('AITool.ai_rpc', [request || {}])",
            "cancelRequest: (requestId) =>",
            "getRequestStatus: (requestId) =>",
            "scratch: {",
            "executePythonCode: (code, mode, sceneName, actorName, targetType = 'actor') =>",
            "saveBlocklyTarget: (payload) => Bridge.callEditorApi('ScratchTool.save_blockly_target', [payload || {}])",
            "loadBlocklyTarget: (payload) => Bridge.callEditorApi('ScratchTool.load_blockly_target', [payload || {}])",
            "startGamePreview: (payload = { scope: 'project' }) =>",
            "stopGamePreview: () => Bridge.callEditorApi('ScratchTool.stop_game_preview', [])",
            "getGamePreviewStatus: () => Bridge.callEditorApi('ScratchTool.get_game_preview_status', [])",
            "stopScriptExecution: () => Bridge.callEditorApi('ScratchTool.stop_script_execution', [])",
            "getScriptStatus: () => Bridge.callEditorApi('ScratchTool.get_script_status', [])",
            "sendKeyEvent: (key, modifiers, displayKey) =>",
            "sendKeyUpEvent: (key, displayKey) =>",
            "sendMouseEvent: (eventType, button, x, y) =>",
            "sendMessageToAIStream: (payload) => editorApi.ai.sendMessageToAIStream(payload)",
            "readLocalFileAsBase64: (filePath) => editorApi.ai.readLocalFileAsBase64(filePath)",
            "generateHint: (elementType, context = {}) => editorApi.ai.generateHint(elementType, context)",
            "chatStream: (request) => editorApi.ai.chatStream(request)",
            "executePythonCode: (code, mode, sceneName, actorName, targetType = 'actor') =>\n    editorApi.scratch.executePythonCode",
            "saveBlocklyTarget: (payload) => editorApi.scratch.saveBlocklyTarget(payload)",
            "startGamePreview: (payload = { scope: 'project' }) => editorApi.scratch.startGamePreview(payload)",
            "sendKeyEvent: (key, modifiers, displayKey) =>\n    editorApi.scratch.sendKeyEvent",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_main_view_editor_apis_have_explicit_schema(self):
        source = self._editor_api_source()

        expected = {
            "MainView.get_menu_data": ("kNoParams", "EditorApiValueType::Object"),
            "MainView.import_resource_file": ("kMainViewImportResourceFileParams", "EditorApiValueType::Object"),
            "MainView.on_init": ("kPathOptionalParam", "EditorApiValueType::Object"),
            "MainView.run_project": ("kPathOptionalParam", "EditorApiValueType::Object"),
            "MainView.scene_save": ("kSceneNameParam", "EditorApiValueType::Object"),
            "MainView.update_view_tool_state": ("kMainViewUpdateViewToolStateParams", "EditorApiValueType::Object"),
        }
        for api_name, (params_name, return_type) in expected.items():
            module, method = api_name.split(".", 1)
            with self.subTest(api_name=api_name):
                self.assertIn(
                    f"EDITOR_API_METHOD_SCHEMA({module}, {method}, {params_name}, {return_type})",
                    source,
                )

    def test_main_view_apis_use_frontend_typed_wrappers(self):
        bridge_source = self._frontend_bridge_source()

        for snippet in (
            "main: {",
            "getMenuData: () => Bridge.callEditorApi('MainView.get_menu_data', [])",
            "importResourceFile: (sceneName, fileType) =>",
            "onInit: (projectPath = '') =>",
            "runProject: (scenePath = '') =>",
            "sceneSave: (sceneName) => Bridge.callEditorApi('MainView.scene_save', [sceneName])",
            "updateViewToolState: (toolId, enabled) =>",
            "OnInit: (projectPath = window.localStorage?.getItem('corona.activeProjectPath') || '') =>\n    editorApi.main.onInit",
            "importResourceFileByDialog: (sceneName, fileType) =>\n    editorApi.main.importResourceFile",
            "getMenuData: () => editorApi.main.getMenuData()",
            "updateViewToolState: (toolId, enabled) =>\n    editorApi.main.updateViewToolState",
            "runProject: (scenePath) =>\n    editorApi.main.runProject",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

    def test_editor_api_events_validate_payload_and_cleanup_cef_callbacks(self):
        source = self._editor_api_source()
        cef_client_source = (
            self._repo_root() / "src" / "systems" / "ui" / "cef" / "cef_client.cpp"
        ).read_text(encoding="utf-8")

        for snippet in (
            "validate_editor_api_event_payload",
            "invalid Editor API event payload",
            "event_caller_allowed",
            "emit_callbacks(event_name, payload, false)",
            "emit_callbacks(event_name, payload, true)",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, source)

        self.assertIn('#include "cef_editor_api.h"', cef_client_source)
        self.assertIn(
            "EditorApiCallbackRegistry::instance().clear_cef_callbacks_for_browser",
            cef_client_source,
        )

    def test_scene_tools_registers_native_camera_handlers(self):
        source = self._handler_source()

        match = re.search(
            r"void register_scene_tools_api_handlers\(NativeApiRegistry& registry\).*?"
            r"registry\.register_module\(\"SceneTools\"",
            source,
            re.S,
        )
        self.assertIsNotNone(match)
        scene_tools_handlers = match.group(0)
        for method in (
            "save_screenshot",
            "set_render_backend",
            "get_render_backend",
            "set_vision_render_mode",
            "get_vision_render_mode",
        ):
            with self.subTest(method=method):
                self.assertIn(f'{{"{method}"', scene_tools_handlers)

    def test_native_scene_save_preserves_embedded_vision_document(self):
        source = self._handler_source()
        self.assertIn("persist_native_scene_common", source)
        self.assertIn("persist_native_scene_vision_metadata", source)
        self.assertIn("storage == \"embedded\"", source)
        self.assertIn("storage = embedded", source)
        self.assertIn("persist_native_scene_vision_document", source)
        start = source.find("void persist_native_scene_common")
        end = source.find("void apply_native_scene_environment", start)
        self.assertGreaterEqual(start, 0)
        self.assertGreater(end, start)
        persist_body = source[start:end]
        self.assertNotIn('remove_ini_section(scene_file, "vision_document")', persist_body)

        match = re.search(
            r'\{"scene_save", \[\]\(const NativeRequest& request, const NativeContext&\).*?'
            r"return native_success",
            source,
            re.S,
        )
        self.assertIsNotNone(match)
        self.assertIn("persist_native_scene_common(*scene)", match.group(0))

    def test_vision_project_open_embeds_document_without_scene_source_path(self):
        source = self._handler_source()

        self.assertIn("create_embedded_vision_document", source)
        self.assertIn("VISION_DOCUMENT_ENCODING", source)
        self.assertIn('"storage", "embedded"', source)
        self.assertIn('"import_mode", "external"', source)
        self.assertIn('"vision_document"', source)

        start = source.find("std::filesystem::path create_vision_project_native")
        end = source.find("std::filesystem::path copy_existing_project_to_data_native", start)
        self.assertGreaterEqual(start, 0)
        self.assertGreater(end, start)
        create_body = source[start:end]
        self.assertIn("create_embedded_vision_document", create_body)
        self.assertIn("persist_vision_proxy_actors_from_document", create_body)
        self.assertIn("replace_ini_section_from_map", create_body)
        self.assertNotIn('"source_path"', create_body)

    def test_embedded_vision_source_loads_from_memory_without_runtime_json(self):
        source = self._handler_source()
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        scene_tools_source = (
            repo_root / "editor" / "plugins" / "SceneTools" / "main.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("write_embedded_vision_runtime_scene", source)
        self.assertNotIn("vision_runtime", source)
        self.assertNotIn("vision_runtime", scene_tools_source)
        self.assertIn('scene.vision_storage == "embedded"', source)
        self.assertIn("decode_vision_document_data(scene.vision_document_data)", source)
        self.assertIn("Corona::API::load_vision_scene_from_json", source)
        self.assertIn('CFW_LOG_ERROR("Vision embedded scene missing', source)

    def test_project_sidecar_vision_source_remains_compatible(self):
        source = self._handler_source()

        self.assertIn("resolve_project_sidecar_vision_json", source)
        self.assertIn('scene.vision_storage == "project_sidecar"', source)
        self.assertIn('Corona::API::load_vision_scene(path_to_utf8(sidecar_json))', source)
        self.assertIn('CFW_LOG_ERROR("Vision sidecar scene missing', source)
        self.assertIn("migrate_project_sidecar_scene_to_embedded", source)
        self.assertIn("create_embedded_vision_document(scene.project_root, sidecar_json, document)", source)
        self.assertIn("scene_ini = read_ini_file(scene_file)", source)

    def test_vision_scene_load_event_supports_embedded_json_payload(self):
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        event_source = (
            repo_root / "include" / "corona" / "events" / "optics_system_events.h"
        ).read_text(encoding="utf-8")
        api_header = (
            repo_root / "include" / "corona" / "systems" / "script" / "corona_engine_api.h"
        ).read_text(encoding="utf-8")
        api_source = (
            repo_root / "src" / "systems" / "script" / "python" / "corona_engine_api.cpp"
        ).read_text(encoding="utf-8")
        optics_header = (
            repo_root / "include" / "corona" / "systems" / "optics" / "optics_system.h"
        ).read_text(encoding="utf-8")
        optics_source = (
            repo_root / "src" / "systems" / "optics" / "optics_system.cpp"
        ).read_text(encoding="utf-8")
        scene_resource_header = (
            repo_root
            / "include"
            / "corona"
            / "systems"
            / "optics"
            / "vision_scene_resource.h"
        ).read_text(encoding="utf-8")

        for snippet in (
            "std::string scene_json",
            "std::string base_dir",
            "std::string scene_key",
            "bool external_live",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, event_source)
        self.assertIn("load_vision_scene_from_json", api_header)
        self.assertIn("load_vision_scene_from_json", api_source)
        self.assertIn("event_bus->publish<Events::VisionSceneLoadEvent>", api_source)
        self.assertIn("VisionSceneLoadRequest", optics_header)
        self.assertIn("std::optional<VisionSceneLoadRequest> pending_vision_scene_load_", optics_header)
        self.assertIn("import_vision_scene_from_data", optics_source)
        self.assertIn("DataWrap::parse(request.scene_json)", optics_source)
        self.assertIn("vision::Global::instance().set_scene_path(base_dir)", optics_source)
        self.assertIn("request.external_live", optics_source)
        self.assertIn("VisionPipelineSource::ExternalLive", optics_source)
        self.assertIn("binding->visible", optics_source)

    def test_python_corona_engine_loader_has_no_fallback_module(self):
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        loader_source = (
            repo_root / "editor" / "CoronaCore" / "core" / "corona_engine.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("corona_engine_fallback", loader_source)
        self.assertFalse(
            (repo_root / "editor" / "CoronaCore" / "utils" / "corona_engine_fallback.py").exists()
        )

    def test_embedded_vision_registers_synthetic_external_live_bindings(self):
        source = self._handler_source()

        for snippet in (
            "embedded_vision_scene_key",
            "register_embedded_vision_actor_bindings",
            "clear_embedded_vision_actor_bindings",
            "set_external_vision_binding(",
            "clear_external_vision_binding()",
            "const auto shape_guid = vision_shape_guid(shape, index)",
            "scene_key,",
            "static_cast<int>(index)",
            "Corona::API::load_vision_scene_from_json(render_document.dump()",
            "true);",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, source)

        load_body = re.search(
            r"void apply_native_scene_vision_source\(.*?\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(load_body)
        self.assertIn("register_embedded_vision_actor_bindings", load_body.group(0))
        self.assertIn("register_embedded_vision_actor_bindings(scene, render_document, scene_key)", load_body.group(0))

    def test_embedded_vision_visibility_uses_live_transform_without_scene_reload(self):
        source = self._handler_source()
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        optics_source = (
            repo_root / "src" / "systems" / "optics" / "optics_system.cpp"
        ).read_text(encoding="utf-8")
        scene_resource_header = (
            repo_root
            / "include"
            / "corona"
            / "systems"
            / "optics"
            / "vision_scene_resource.h"
        ).read_text(encoding="utf-8")

        render_body = re.search(
            r"nlohmann::json vision_document_for_render\(.*?\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(render_body)
        self.assertNotIn("remove_if", render_body.group(0))
        self.assertNotIn("vision_shape_visible(shape)", render_body.group(0))

        sync_start = source.find(
            "bool sync_native_actor_to_embedded_vision_document(NativeEditorScene& scene,\n"
            "                                                   const NativeEditorActor& actor,\n"
            "                                                   bool create_if_missing,\n"
            "                                                   bool sync_transform) {"
        )
        sync_end = source.find("bool remove_native_actor_from_embedded_vision_document", sync_start)
        self.assertGreaterEqual(sync_start, 0)
        self.assertGreater(sync_end, sync_start)
        sync_body = source[sync_start:sync_end]
        self.assertIn("persisted && created_shape", sync_body)
        self.assertNotIn("previous_visible != next_visible", sync_body)

        remove_body = re.search(
            r"auto remove_actor_shape = .*?\n    \};",
            optics_source,
            re.S,
        )
        self.assertIsNotNone(remove_body)
        self.assertIn("!record->dynamically_added", remove_body.group(0))
        self.assertIn("scene_resource->erase_external_live_shape(actor_handle)", remove_body.group(0))

        transform_body = re.search(
            r"void OpticsSystem::sync_external_live_vision_transforms\(.*?\n\}",
            optics_source,
            re.S,
        )
        self.assertIsNotNone(transform_body)
        self.assertIn("hidden_bound_actors", transform_body.group(0))
        self.assertIn("hidden_external_live_o2w()", transform_body.group(0))
        self.assertIn("external_live_hidden_transform_signature", transform_body.group(0))
        self.assertIn("!binding->visible", transform_body.group(0))
        self.assertNotIn("!actor_has_visible_optics(actor_handle)", transform_body.group(0))
        self.assertIn("cache_external_live_original_instance", transform_body.group(0))
        self.assertIn("external_live_original_transform_signatures", transform_body.group(0))
        self.assertIn("restore_external_live_original_instances", transform_body.group(0))
        self.assertIn("continue;", transform_body.group(0))

        self.assertIn("external_live_original_instances", scene_resource_header)
        self.assertIn("external_live_original_transform_signatures", scene_resource_header)
        self.assertIn("cache_external_live_original_instance", scene_resource_header)
        self.assertIn("restore_external_live_original_instances", scene_resource_header)

    def test_embedded_vision_visibility_does_not_rewrite_transform_schema(self):
        source = self._handler_source()

        for snippet in (
            "write_actor_visibility_to_vision_shape",
            "write_actor_state_to_vision_shape(actor, *shape, sync_transform)",
            "operation == \"SetVisible\"",
            "operation != \"SetVisible\"",
            "cleanup_editor_trs_overrides_for_non_trs_transform",
            "cleanup_vision_document_editor_transform_overrides",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, source)

    def test_embedded_vision_rewrites_and_copies_common_vision_assets(self):
        source = self._handler_source()

        for snippet in (
            "rewrite_vision_resource_paths_for_project_archive",
            "copy_vision_archive_asset",
            "copy_obj_dependencies",
            "copy_mtl_texture_dependencies",
            "copy_gltf_dependencies",
            'std::filesystem::path("Resource")',
            '"vision_imports"',
            'key == "fn"',
            'key == "texture"',
            'copy_uri_array("buffers")',
            'copy_uri_array("images")',
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, source)

    def test_native_actor_save_load_preserves_common_optics_fields(self):
        source = self._handler_source()
        for snippet in (
            '".optics.diffuse = "',
            '".optics.metallic = "',
            '".optics.roughness = "',
            '".optics.emission = "',
            '".material.texture = "',
            'item.optics->set_diffuse',
            'item.optics->set_metallic',
            'item.optics->set_roughness',
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, source)

    def test_embedded_vision_actor_operations_update_document_without_reload(self):
        source = self._handler_source()

        for snippet in (
            "sync_native_actor_to_embedded_vision_document",
            "remove_native_actor_from_embedded_vision_document",
            "persist_embedded_vision_document",
            "vision_document_for_render",
            "ensure_vision_shape_guids",
            "scene.vision_document_data = encode_vision_document_data(document)",
            "Corona::API::load_vision_scene_from_json(",
            '"visible"',
            '".optics.visible = "',
            'actor.optics->set_visible',
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, source)

        sync_body = re.search(
            r"bool sync_native_actor_to_embedded_vision_document\(.*?\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(sync_body)
        self.assertNotIn("load_vision_scene_from_json", sync_body.group(0))

        transform_body = re.search(
            r"NativeResult set_native_editor_actor_transform\(.*?\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(transform_body)
        self.assertIn("sync_native_actor_to_embedded_vision_document(*scene, *actor)", transform_body.group(0))

        operation_body = re.search(
            r"NativeResult apply_actor_operation\(.*?\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(operation_body)
        self.assertIn("sync_native_actor_to_embedded_vision_document(", operation_body.group(0))
        self.assertIn('operation != "SetVisible"', operation_body.group(0))

        remove_body = re.search(
            r"NativeResult remove_native_editor_actor\(.*?\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(remove_body)
        self.assertIn("remove_native_actor_from_embedded_vision_document(*scene, removed_guid)", remove_body.group(0))

    def test_native_camera_save_load_preserves_vision_render_settings(self):
        source = self._handler_source()
        for snippet in (
            '".vision_spp = "',
            '".vision_max_depth = "',
            '".vision_denoise = "',
            'section_value("vision_spp"',
            'section_value("vision_max_depth"',
            'section_value("vision_denoise"',
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, source)

    def test_project_launcher_business_logic_is_native(self):
        source = self._handler_source()
        for snippet in (
            "void register_project_launcher_api_handlers",
            '"create_project"',
            '"create_world_project"',
            '"create_multiplayer_project"',
            '"open_project"',
            "create_vision_project_native",
            "create_embedded_vision_document",
            "copy_existing_project_to_data_native",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, source)

        rpc_source = (
            pathlib.Path(__file__).resolve().parents[4]
            / "src" / "systems" / "ui" / "cef" / "cef_editor_native_api_registry.cpp"
        ).read_text(encoding="utf-8")
        self.assertIn("register_project_launcher_api_handlers(registry)", rpc_source)
        api_source = self._editor_api_source()
        self.assertIn(
            "EDITOR_API_METHOD_SCHEMA(ProjectLauncher, browse_folder, kPathOptionalParam, EditorApiValueType::String)",
            api_source,
        )
        self.assertIn(
            "EDITOR_API_METHOD_SCHEMA(ProjectLauncher, open_project_file, kNoParams, EditorApiValueType::Object)",
            api_source,
        )
        self.assertIn(
            "EDITOR_API_METHOD_SCHEMA(ProjectLauncher, open_project, kPathParam, EditorApiValueType::Object)",
            api_source,
        )
        self.assertIn(
            "EDITOR_API_METHOD_SCHEMA(ProjectLauncher, create_project, kObjectPayloadParam, EditorApiValueType::String)",
            api_source,
        )

    def test_native_project_template_prefers_corona_core_demo_project(self):
        source = self._handler_source()
        match = re.search(
            r"std::filesystem::path project_template_path\(\) \{(?P<body>.*?)\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn('"CoronaCore" / "demo" / "project"', body)
        self.assertIn('"plugins" / "ProjectLauncher" / "demo" / "project"', body)

    def test_vision_project_open_updates_recent_only_after_successful_open(self):
        source = self._handler_source()

        match = re.search(
            r"std::filesystem::path create_project_from_template_native\(.*?\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(match)
        self.assertNotIn("add_recent_project_native", match.group(0))

        match = re.search(
            r"std::filesystem::path open_project_native\(.*?\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(match)
        self.assertIn("add_recent_project_native(project_dir)", match.group(0))

    def test_vision_import_uses_type_safe_json_accessors(self):
        source = self._handler_source()
        fragile_snippets = (
            'output["denoise"].get<bool>()',
            'shape.value("type"',
            'shape.value("shape_type"',
            'shape.value("name"',
            'shape.value("fn"',
            'shape.value("path"',
            'params.value("fn"',
            'params.value("path"',
            'params.value("position"',
            'params.value("direction"',
            'params.value("up"',
            'transform_params.value("t"',
            'transform_params.value("s"',
        )
        for snippet in fragile_snippets:
            with self.subTest(snippet=snippet):
                self.assertNotIn(snippet, source)
        self.assertIn('json_bool_value(output, "denoise", false)', source)
        self.assertIn("shapes.is_object()", source)

    def test_project_launcher_open_project_returns_resolved_project_path(self):
        source = self._handler_source()
        self.assertIn("std::filesystem::path open_project_native", source)
        self.assertIn("return project_dir;", source)

        start = source.find('{"open_project", [](const NativeRequest& request, const NativeContext&)')
        end = source.find('{"set_project_mode"', start)
        self.assertGreaterEqual(start, 0)
        self.assertGreater(end, start)
        handler = source[start:end]
        self.assertIn("const auto opened = open_project_native", handler)
        self.assertIn('{"path", path_to_utf8(opened)}', handler)

    def test_project_launcher_frontend_caches_resolved_project_path(self):
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        bridge_path = repo_root / "editor" / "Frontend" / "src" / "utils" / "bridge.js"
        source = bridge_path.read_text(encoding="utf-8")
        self.assertIn("const activeProjectPath = success?.path || projectPath;", source)
        self.assertIn("setItem('corona.activeProjectPath', activeProjectPath)", source)

    def test_project_launcher_canonicalizes_settings_project_paths(self):
        source = self._handler_source()
        self.assertIn("canonical_project_dir_for_settings", source)

        for function_name in (
            "read_last_project_from_editor_ini",
            "resolve_active_project_path",
            "add_recent_project_native",
            "recent_projects_native",
            "open_project_native",
        ):
            with self.subTest(function=function_name):
                match = re.search(
                    rf"{function_name}\(.*?\n\}}",
                    source,
                    re.S,
                )
                self.assertIsNotNone(match)
                self.assertIn("canonical_project_dir_for_settings", match.group(0))

    def test_project_launcher_open_path_is_logged_at_rpc_boundaries(self):
        source = self._handler_source()
        for snippet in (
            "[ProjectLauncher] open_project request path='{}'",
            "[ProjectLauncher] open_project opened path='{}'",
            "[ProjectLauncher] open_project failed: {}",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, source)

        bridge_source = self._query_bridge_source()
        for snippet in (
            "parse_editor_api_request(request_payload",
            "CefEditorApiEndpoint editor_api",
            "editor_api.invoke(editor_api_request->api_name",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)
        self.assertNotIn("CEF RPC request", bridge_source)
        self.assertNotIn("CEF RPC success", bridge_source)
        self.assertNotIn("CEF RPC failure", bridge_source)
        self.assertNotIn("CEF RPC python fallback", bridge_source)

    def test_python_scene_save_preserves_embedded_vision_document(self):
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        source = (repo_root / "editor" / "CoronaCore" / "core" / "entities" / "scene.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("self.vision_storage", source)
        self.assertIn("self.vision_document", source)
        self.assertIn("_encode_vision_document(vision_document)", source)
        self.assertIn("zlib.compressobj(level=0)", source)
        self.assertIn("self.file_data['vision']['storage'] = 'embedded'", source)
        self.assertIn("self.file_data['vision_document']['data']", source)
        self.assertIn("if vision_storage == 'project_sidecar' and vision_source_id:", source)
        self.assertIn("self.file_data['vision']['source_id']", source)
        self.assertNotIn("self.file_data['vision']['source_path']", source)

    def test_recent_games_import_awaits_open_project_and_catches_errors(self):
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        source = (
            repo_root / "editor" / "Frontend" / "src" / "views" / "layout" / "RecentGames.vue"
        ).read_text(encoding="utf-8")
        start = source.find("const handleImport = async () => {")
        end = source.find("\n};", start)
        self.assertGreaterEqual(start, 0)
        self.assertGreater(end, start)
        body = source[start:end]
        self.assertIn("try {", body)
        self.assertIn("await handleOpenProject(result.data.path)", body)
        self.assertIn("console.error('打开现有项目失败:'", body)

    def test_native_scene_load_keeps_expensive_mesh_processing_opt_in(self):
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        engine_source = (repo_root / "src" / "engine.cpp").read_text(encoding="utf-8")
        parse_common_source = (
            repo_root
            / "modules"
            / "corona_resource"
            / "src"
            / "resource"
            / "types"
            / "parse_common.h"
        ).read_text(encoding="utf-8")

        self.assertIn("assimp_options.simplify_mesh = false", engine_source)
        self.assertIn("assimp_options.lod_options.enabled = false", engine_source)
        self.assertNotIn("lod.enabled     = true", engine_source)

        self.assertNotIn("bool /*simplify_mesh*/", parse_common_source)
        self.assertIn("if (!simplify_mesh)", parse_common_source)

    def test_python_settings_hydrates_native_last_project(self):
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        settings_source = (repo_root / "editor" / "utils" / "settings.py").read_text(encoding="utf-8")

        self.assertIn("def _hydrate_active_project_from_last_project", settings_source)
        self.assertIn("self.config.get('General', 'last_project'", settings_source)
        self.assertIn("self._active_project_path = project_path", settings_source)
        self.assertIn("self.active_project_config = proj_cfg", settings_source)


if __name__ == "__main__":
    unittest.main()
