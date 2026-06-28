from __future__ import annotations

import json
from pathlib import Path
import sys

EDITOR_DIR = Path(__file__).resolve().parents[5]
AITOOL_DIR = EDITOR_DIR / "plugins" / "AITool"
for candidate in (EDITOR_DIR, AITOOL_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from plugins.AITool.cai_extensions.agent.scene_session import FinalReviewReport, SceneSession
from plugins.AITool.cai_extensions.data_model.layout import LayoutInstance, SceneLayout
from plugins.AITool.cai_extensions.mcp.tools import native_scene_state


class FakeEngine:
    def __init__(self) -> None:
        self.transform_calls = []
        self.snapshot = {
            "status": "success",
            "scene": "Scene/default.scene",
            "scene_name": "default",
            "actors": [
                {
                    "name": "储物道具",
                    "actor_guid": "guid-storage",
                    "route": "models/storagecrateprop/base.glb",
                    "actor_type": "model",
                    "geometry": {"position": [1.0, 0.0, 1.0], "rotation": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0]},
                    "local_aabb": [-0.4, -0.5, -0.4, 0.4, 0.6, 0.4],
                    "world_aabb": [0.6, -0.5, 0.6, 1.4, 0.6, 1.4],
                    "bounds_ready": True,
                    "size": [0.8, 1.1, 0.8],
                }
            ],
            "scene_aabb": [0.6, -0.5, 0.6, 1.4, 0.6, 1.4],
            "bounds_ready": True,
        }

    def get_editor_scene_snapshot(self, scene_name: str) -> str:
        return json.dumps(self.snapshot)

    def set_editor_actor_transform(self, scene_name: str, actor_name: str, transform_json: str) -> str:
        transform = json.loads(transform_json)
        self.transform_calls.append((scene_name, actor_name, transform))
        actor = self.snapshot["actors"][0]
        actor["geometry"].update(transform["geometry"])
        pos = actor["geometry"]["position"]
        actor["world_aabb"] = [0.6, pos[1] - 0.5, 0.6, 1.4, pos[1] + 0.6, 1.4]
        return json.dumps({"status": "success", "scene": scene_name, "actor": actor})


def setup_function() -> None:
    native_scene_state.CORONA_ENGINE_OVERRIDE = FakeEngine()


def teardown_function() -> None:
    native_scene_state.CORONA_ENGINE_OVERRIDE = None


def test_ground_fit_final_adjustment_snaps_native_actor_to_ground() -> None:
    layout = SceneLayout()
    layout.add(LayoutInstance(
        instance_id="储物道具",
        asset_id="储物道具",
        zone_id="default",
        transform={"pos": [1.0, 0.0, 1.0], "rot": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0]},
        provenance="AGENT",
    ))
    session = SceneSession(layout, scene_name="Scene/default.scene")
    report = FinalReviewReport(final_adjustments=[{
        "actor_id": "储物道具",
        "content": "模型下半身被地面遮挡，存在明显穿模，需要贴地。",
    }])

    applied = session.apply_final_adjustments(report)

    engine = native_scene_state.CORONA_ENGINE_OVERRIDE
    assert applied[0]["actions"] == ["ground_fit"]
    assert engine.transform_calls
    position = engine.transform_calls[0][2]["geometry"]["position"]
    assert position == [1.0, 0.52, 1.0]
    assert layout.get("储物道具").transform["pos"] == [1.0, 0.52, 1.0]
