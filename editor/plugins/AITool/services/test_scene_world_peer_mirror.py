from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
EDITOR_ROOT = REPO_ROOT / "editor"
if str(EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(EDITOR_ROOT))

from plugins.AITool.services.agent_runtime import AgentRuntime  # noqa: E402


class SceneWorldPeerMirrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = AgentRuntime()

    def _record(self, event: dict) -> dict:
        return self.runtime.record_sync_event(room_id="room-peer", event=event)

    def test_remote_host_facts_create_read_only_peer_snapshot_without_scene_plan(self) -> None:
        base = {
            "room_id": "room-peer",
            "plan_id": "plan-host-scene",
            "scene_version": 4,
            "authority": "remote_host",
            "actor_id": "actor-cupid",
            "entity_id": "entity-cupid",
            "actor_version": 4,
            "asset_id": "asset-cupid",
            "model_ref": "model-cupid",
            "entity_type": "decoration",
            "semantic_role": "statue",
            "grounding_status": "grounded",
            "position": [1.0, 0.0, 2.0],
            "rotation": [0.0, 45.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
        }
        self.assertTrue(self._record({**base, "event": "actor_create_received", "status": "received"})["recorded"])
        self.assertTrue(self._record({
            "room_id": "room-peer",
            "event": "actor_imported",
            "authority": "remote_host",
            "actor_id": "actor-cupid",
            "status": "engine_imported",
        })["recorded"])
        self.assertTrue(self._record({
            **base,
            "event": "actor_updated",
            "status": "ready",
            "world_aabb": {"min": [0.5, 0.0, 1.5], "max": [1.5, 2.0, 2.5]},
        })["recorded"])

        room = self.runtime.query_state("room-peer")["room"]
        self.assertEqual(room["peer_mirror_plan_id"], "plan-host-scene")
        self.assertEqual(room["peer_mirror_scene_versions"]["plan-host-scene"], 4)
        self.assertEqual(room["scene_plans"], {})
        self.assertEqual(room["tool_graph_queue"], {})

        snapshot_result = self.runtime.get_scene_world_snapshot(room_id="room-peer")
        self.assertTrue(snapshot_result["found"])
        self.assertFalse(snapshot_result["recorded"])
        self.assertEqual(snapshot_result["snapshot_authority"], "peer_mirror")
        self.assertEqual(snapshot_result["snapshot_stability"], "peer_mirror")
        self.assertEqual(snapshot_result["scene_version"], 4)
        self.assertEqual(snapshot_result["world_readiness"], "game_ready")
        self.assertEqual(len(snapshot_result["snapshot"]["actor_entities"]), 1)
        entity = snapshot_result["snapshot"]["actor_entities"][0]
        self.assertEqual(entity["entity_id"], "entity-cupid")
        self.assertEqual(entity["actor_id"], "actor-cupid")
        self.assertEqual(entity["bounds_source"], "engine_actual")
        self.assertEqual(entity["sync_status"], "synced")
        self.assertEqual(self.runtime.query_state("room-peer")["room"]["scene_plans"], {})

        status = self.runtime.status_summary("room-peer")
        self.assertTrue(status["available"])
        self.assertEqual(status["plan_id"], "plan-host-scene")
        self.assertEqual(status["peer_mirror_plan_id"], "plan-host-scene")
        self.assertEqual(status["snapshot_authority"], "peer_mirror")
        self.assertEqual(status["scene_entity_registry"]["actor_count"], 1)

        stale = self._record({
            **base,
            "event": "actor_updated",
            "actor_version": 3,
            "position": [99.0, 99.0, 99.0],
            "world_aabb": {"min": [98.0, 98.0, 98.0], "max": [100.0, 100.0, 100.0]},
        })
        self.assertFalse(stale["recorded"])
        self.assertEqual(stale["reason"], "stale actor version")
        after_stale = self.runtime.get_scene_world_snapshot(room_id="room-peer")
        stable_entity = after_stale["snapshot"]["actor_entities"][0]
        self.assertEqual(stable_entity["transform"]["position"], [1.0, 0.0, 2.0])
        self.assertEqual(stable_entity["world_aabb"]["min"], [0.5, 0.0, 1.5])
        self.assertEqual(after_stale["world_fingerprint"], snapshot_result["world_fingerprint"])

    def test_unknown_local_plan_sync_fact_is_rejected(self) -> None:
        result = self._record({
            "room_id": "room-peer",
            "event": "actor_updated",
            "plan_id": "plan-untrusted",
            "authority": "local",
            "actor_id": "actor-untrusted",
        })
        self.assertFalse(result["recorded"])
        room = self.runtime.query_state("room-peer")["room"]
        self.assertEqual(room["peer_mirror_plan_id"], "")
        self.assertNotIn("actor-untrusted", room["actors"])


if __name__ == "__main__":
    unittest.main()
