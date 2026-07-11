from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import types
import unittest
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[7]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
EDITOR_ROOT = PROJECT_ROOT / "editor"
if str(EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(EDITOR_ROOT))
AI_TOOL_ROOT = PROJECT_ROOT / "editor" / "plugins" / "AITool"
if str(AI_TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_TOOL_ROOT))

from editor.plugins.AITool.cai_extensions.mcp.tools.model_import_tools import (
    _actor_identity_from_native_result,
    _build_import_environment_component_tool,
    _create_native_editor_actor,
    _pick_model_file,
)
from editor.plugins.AITool.services.agent_runtime.environment_primitives import (
    build_environment_primitive,
)


class ModelImportToolsTests(unittest.TestCase):
    def test_room_environment_primitives_are_visible_model_assets(self) -> None:
        room_box = build_environment_primitive(
            component_type="room_box",
            component_id="room-box-test",
            scale=[7.0, 3.2, 6.5],
        )
        room_floor = build_environment_primitive(
            component_type="room_floor",
            component_id="room-floor-test",
            scale=[7.0, 0.05, 6.5],
        )

        self.assertTrue(Path(room_box.model_path).is_file())
        self.assertTrue(Path(room_floor.model_path).is_file())
        self.assertEqual(room_box.position, [0.0, 1.6, 0.0])
        self.assertEqual(room_floor.position, [0.0, 0.025, 0.0])
        self.assertEqual(room_box.semantic_role, "indoor_enclosure")
        self.assertEqual(room_floor.semantic_role, "walkable_floor")
        self.assertIn("usemtl wall", Path(room_box.model_path).read_text(encoding="utf-8"))
        self.assertIn("usemtl floor", Path(room_floor.model_path).read_text(encoding="utf-8"))

        terrain = build_environment_primitive(
            component_type="terrain",
            component_id="terrain-test",
            scale=[14.0, 0.05, 12.0],
        )
        boundary = build_environment_primitive(
            component_type="boundary",
            component_id="boundary-test",
            scale=[14.0, 0.8, 12.0],
        )
        self.assertTrue(Path(terrain.model_path).is_file())
        self.assertTrue(Path(boundary.model_path).is_file())
        self.assertEqual(terrain.semantic_role, "walkable_terrain")
        self.assertEqual(boundary.semantic_role, "scene_boundary")

    def test_room_environment_import_never_uses_audio_actor_type(self) -> None:
        calls = []
        fake_editor_module = types.ModuleType("CoronaCore.core.corona_editor")
        fake_editor_module.CoronaEditor = types.SimpleNamespace(
            CoronaEngine=types.SimpleNamespace()
        )
        tool = _build_import_environment_component_tool(scene_manager=None)

        def fake_create(**kwargs):
            calls.append(kwargs)
            actor_data = kwargs["actor_data"]
            return {
                "status": "success",
                "scene": kwargs["scene_name"],
                "actor": {
                    "actor_guid": "room-native-guid",
                    "name": actor_data["name"],
                    "geometry": actor_data["geometry"],
                },
            }

        with mock.patch.dict(
            "sys.modules",
            {"CoronaCore.core.corona_editor": fake_editor_module},
        ), mock.patch(
            "editor.plugins.AITool.cai_extensions.mcp.tools.model_import_tools._create_native_editor_actor",
            side_effect=fake_create,
        ):
            tool.func(
                component_id="component-room-box",
                name="room_box",
                component_type="room_box",
                scale=[6.5, 3.0, 6.0],
                scene_name="Scene/test.scene",
            )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["actor_type"], "model")
        self.assertTrue(calls[0]["source_path"].endswith("room_box.obj"))
        self.assertEqual(calls[0]["actor_data"]["entity_type"], "environment")
        self.assertEqual(calls[0]["actor_data"]["semantic_role"], "indoor_enclosure")

    def test_pick_model_file_finds_nested_mesh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hunyuan_model"
            nested = root / "mesh" / "export"
            nested.mkdir(parents=True)
            mesh = nested / "base.glb"
            mesh.write_bytes(b"glb")

            self.assertEqual(_pick_model_file(str(root)), str(mesh))

    def test_actor_identity_from_native_result_accepts_supported_fields(self) -> None:
        self.assertEqual(
            _actor_identity_from_native_result({"actor": {"actor_guid": "guid-1"}}),
            "guid-1",
        )
        self.assertEqual(
            _actor_identity_from_native_result({"actor_data": {"native_actor_id": "native-2"}}),
            "native-2",
        )
        self.assertEqual(
            _actor_identity_from_native_result({"entity_id": "entity-3"}),
            "entity-3",
        )

    def test_actor_identity_from_native_result_rejects_missing_identity(self) -> None:
        self.assertEqual(
            _actor_identity_from_native_result({"status": "success", "actor": {"name": "box"}}),
            "",
        )

    def test_create_native_editor_actor_prefers_manifest_api(self) -> None:
        manifest_calls = []

        class FakeSceneTools:
            @staticmethod
            def create_actor(scene_name, source_path, actor_type, actor_data):
                manifest_calls.append((scene_name, source_path, actor_type, actor_data))
                return {
                    "status": "success",
                    "actor": {"actor_guid": "manifest-guid"},
                }

        fake_corona_engine_module = types.ModuleType("CoronaEngine")
        fake_corona_engine_module._invoke_cpp_editor_api = lambda *_args: None
        fake_editor_api_module = types.ModuleType("CoronaCore.core.editor_api")
        fake_editor_api_module.CoronaEditorApi = types.SimpleNamespace(
            scene_tools=FakeSceneTools()
        )
        fake_editor_api_module._find_cpp_api_method_by_python_wrapper = (
            lambda wrapper: {"api": "SceneTools.create_actor"}
            if wrapper == "scene_tools.create_actor"
            else None
        )

        class LegacyEngine:
            @staticmethod
            def create_editor_actor(*_args):
                raise AssertionError("legacy actor API must not be called")

        actor_data = {"position": [1.0, 2.0, 3.0]}
        with mock.patch.dict(
            "sys.modules",
            {
                "CoronaEngine": fake_corona_engine_module,
                "CoronaCore.core.editor_api": fake_editor_api_module,
            },
        ):
            result = _create_native_editor_actor(
                scene_name="Scene/test.scene",
                source_path="models/chest.glb",
                actor_type="model",
                actor_data=actor_data,
                legacy_engine=LegacyEngine,
            )

        self.assertEqual(result["actor"]["actor_guid"], "manifest-guid")
        self.assertEqual(len(manifest_calls), 1)
        self.assertIs(manifest_calls[0][3], actor_data)

    def test_create_native_editor_actor_falls_back_when_manifest_method_is_missing(self) -> None:
        fake_corona_engine_module = types.ModuleType("CoronaEngine")
        fake_corona_engine_module._invoke_cpp_editor_api = lambda *_args: None
        fake_editor_api_module = types.ModuleType("CoronaCore.core.editor_api")
        fake_editor_api_module.CoronaEditorApi = types.SimpleNamespace()
        fake_editor_api_module._find_cpp_api_method_by_python_wrapper = lambda _wrapper: None
        legacy_calls = []

        class LegacyEngine:
            @staticmethod
            def create_editor_actor(scene_name, source_path, actor_type, actor_data_json):
                legacy_calls.append((scene_name, source_path, actor_type, actor_data_json))
                return {"status": "success", "actor": {"actor_guid": "old-build-guid"}}

        with mock.patch.dict(
            "sys.modules",
            {
                "CoronaEngine": fake_corona_engine_module,
                "CoronaCore.core.editor_api": fake_editor_api_module,
            },
        ):
            result = _create_native_editor_actor(
                scene_name="Scene/test.scene",
                source_path="models/chest.glb",
                actor_type="model",
                actor_data={"position": [0.0, 0.0, 0.0]},
                legacy_engine=LegacyEngine,
            )

        self.assertEqual(result["actor"]["actor_guid"], "old-build-guid")
        self.assertEqual(len(legacy_calls), 1)

    def test_create_native_editor_actor_falls_back_for_old_engine(self) -> None:
        legacy_calls = []
        fake_corona_engine_module = types.ModuleType("CoronaEngine")

        class LegacyEngine:
            @staticmethod
            def create_editor_actor(scene_name, source_path, actor_type, actor_data_json):
                legacy_calls.append(
                    (scene_name, source_path, actor_type, json.loads(actor_data_json))
                )
                return json.dumps(
                    {"status": "success", "actor": {"actor_guid": "legacy-guid"}}
                )

        with mock.patch.dict(
            "sys.modules", {"CoronaEngine": fake_corona_engine_module}
        ):
            result = _create_native_editor_actor(
                scene_name="Scene/test.scene",
                source_path="models/chest.glb",
                actor_type="model",
                actor_data={"scale": [1.2, 1.2, 1.2]},
                legacy_engine=LegacyEngine,
            )

        self.assertEqual(result["actor"]["actor_guid"], "legacy-guid")
        self.assertEqual(legacy_calls[0][3]["scale"], [1.2, 1.2, 1.2])


if __name__ == "__main__":
    unittest.main()
