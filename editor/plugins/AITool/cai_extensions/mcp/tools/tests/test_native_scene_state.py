from __future__ import annotations

import json
from pathlib import Path
import sys

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import native_scene_state as state


class FakeEngine:
    def __init__(self) -> None:
        self.transform_calls = []
        self.snapshot = {
            "status": "success",
            "scene": "Scene/default.scene",
            "scene_name": "default",
            "actors": [
                {
                    "name": "Bed",
                    "actor_guid": "guid-bed",
                    "route": "Models/bed.glb",
                    "actor_type": "model",
                    "geometry": {"position": [10, 0, 2], "rotation": [0, 0, 0], "scale": [2, 1, 3]},
                    "local_aabb": [-1, 0, -1, 1, 2, 1],
                    "world_aabb": [8, 0, -1, 12, 2, 5],
                    "bounds_ready": True,
                    "size": [4, 2, 6],
                },
                {
                    "name": "Loading",
                    "actor_guid": "guid-loading",
                    "route": "Models/loading.glb",
                    "actor_type": "model",
                    "geometry": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                    "local_aabb": None,
                    "world_aabb": None,
                    "bounds_ready": False,
                    "size": [0, 0, 0],
                },
            ],
            "scene_aabb": [8, 0, -1, 12, 2, 5],
            "bounds_ready": True,
        }

    def get_editor_scene_snapshot(self, scene_name: str) -> str:
        return json.dumps(self.snapshot)

    def set_editor_actor_transform(self, scene_name: str, actor_name: str, transform_json: str) -> str:
        self.transform_calls.append((scene_name, actor_name, json.loads(transform_json)))
        actor = self.snapshot["actors"][0]
        actor["geometry"].update(json.loads(transform_json)["geometry"])
        return json.dumps({"status": "success", "scene": scene_name, "actor": actor})


def setup_function() -> None:
    state.CORONA_ENGINE_OVERRIDE = FakeEngine()


def teardown_function() -> None:
    state.CORONA_ENGINE_OVERRIDE = None


def test_snapshot_returns_native_actors_when_python_actor_list_is_empty() -> None:
    snapshot = state.get_native_scene_snapshot("")
    assert snapshot["actors"][0]["name"] == "Bed"
    assert len(state.native_actor_views("")) == 2


def test_actor_view_exposes_world_aabb_and_bounds_ready() -> None:
    bed = state.find_native_actor("", "Bed")
    loading = state.find_native_actor("", "Loading")
    assert bed is not None
    assert loading is not None
    assert bed.bounds_ready is True
    assert bed.get_world_aabb() == [8, 0, -1, 12, 2, 5]
    assert loading.bounds_ready is False


def test_set_native_actor_transform_calls_native_api() -> None:
    result = state.set_native_actor_transform("Scene/default.scene", "Bed", position=[1, 2, 3])
    assert result["actor"]["geometry"]["position"] == [1.0, 2.0, 3.0]
    engine = state.CORONA_ENGINE_OVERRIDE
    assert engine.transform_calls[0][1] == "Bed"
    assert engine.transform_calls[0][2]["geometry"]["position"] == [1.0, 2.0, 3.0]
