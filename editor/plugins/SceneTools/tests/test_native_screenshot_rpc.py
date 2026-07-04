import pathlib
import re
import unittest


class NativeSceneToolsRpcTests(unittest.TestCase):
    def _handler_source(self):
        repo_root = pathlib.Path(__file__).resolve().parents[4]
        handler_path = repo_root / "src" / "systems" / "ui" / "cef" / "cef_native_rpc_handlers.cpp"
        return handler_path.read_text(encoding="utf-8")

    def test_scene_tools_registers_native_camera_handlers(self):
        source = self._handler_source()

        match = re.search(
            r"void register_scene_tools_rpc_handlers\(NativeRpcRegistry& registry\).*?"
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
        fallback_source = (
            repo_root / "editor" / "CoronaCore" / "utils" / "corona_engine_fallback.py"
        ).read_text(encoding="utf-8")

        for snippet in (
            "std::string scene_json",
            "std::string base_dir",
            "std::string scene_key",
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
        self.assertIn("load_vision_scene_from_json", fallback_source)

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
            "void register_project_launcher_rpc_handlers",
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
            / "src" / "systems" / "ui" / "cef" / "cef_native_rpc.cpp"
        ).read_text(encoding="utf-8")
        self.assertIn("register_project_launcher_rpc_handlers(registry)", rpc_source)
        project_allowlist = re.search(
            r'\{"ProjectLauncher", \{(?P<body>.*?)\}\}',
            rpc_source,
            re.S,
        )
        self.assertIsNotNone(project_allowlist)
        body = project_allowlist.group("body")
        self.assertIn('"open_project_file"', body)
        self.assertIn('"browse_folder"', body)
        self.assertNotIn('"open_project"', body)
        self.assertNotIn('"create_project"', body)

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

        repo_root = pathlib.Path(__file__).resolve().parents[4]
        bridge_source = (
            repo_root / "src" / "systems" / "ui" / "cef" / "cef_query_bridge.cpp"
        ).read_text(encoding="utf-8")
        for snippet in (
            "should_log_rpc_route",
            "CEF RPC request {}.{} args={}",
            "CEF RPC native success {}.{} route={}",
            "CEF RPC python fallback {}.{}",
            "CEF RPC native failure {}.{} route={} error={}",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, bridge_source)

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
