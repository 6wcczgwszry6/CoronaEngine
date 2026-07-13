from __future__ import annotations

from copy import deepcopy
import unittest

from editor.plugins.AITool.services.agent_runtime import (
    AgentRuntime,
    R3_DIMENSION_NAMES,
    R3GateReportValidator,
    evaluate_r3_gate,
)
from editor.plugins.AITool.services.agent_runtime.scene_world_consistency import (
    audit_scene_world_consistency,
    scene_world_fingerprint,
)


def _entity(index: int, *, game_ready: bool, environment: bool = False) -> dict:
    entity_id = f"entity-{index:02d}"
    actor_id = f"actor-{index:02d}"
    component_type = "room_box" if index == 0 else "room_floor" if index == 1 else ""
    row = {
        "entity_id": entity_id,
        "actor_id": actor_id,
        "asset_id": f"asset-{index:02d}",
        "model_ref": f"model-{index:02d}",
        "version": 1,
        "entity_type": "environment" if environment else "furniture",
        "semantic_role": component_type or f"prop-{index:02d}",
        "component_type": component_type,
        "transform": {
            "position": [float(index), 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
        },
        "world_aabb": {
            "min": [float(index), 0.0, 0.0],
            "max": [float(index + 1), 1.0, 1.0],
        },
        "bounds_source": "engine_actual",
        "grounding_status": "enclosure" if component_type == "room_box" else "grounded",
        "sync_status": "synced",
        "engine_write_verification_status": "engine_verified",
        "game_ready": bool(game_ready),
        "readiness_missing_fields": [] if game_ready else ["support_classification"],
    }
    return row


def _gate_facts(*, game_ready_count: int) -> dict:
    entities = [
        _entity(index, game_ready=index < game_ready_count, environment=index < 2)
        for index in range(14)
    ]
    environment_entities = entities[:2]
    actor_entities = entities[2:]
    plan_id = "plan-bedroom"
    scene_version = 3
    fingerprint = scene_world_fingerprint(
        entities,
        plan_id=plan_id,
        scene_version=scene_version,
    )
    snapshot = {
        "room_id": "room-1",
        "plan_id": plan_id,
        "scene_version": scene_version,
        "world_readiness": "needs_review",
        "snapshot_authority": "local_runtime",
        "environment_entities": environment_entities,
        "actor_entities": actor_entities,
        "readiness_summary": {
            "entity_count": 14,
            "game_ready_entity_count": game_ready_count,
        },
        "world_fingerprint": fingerprint,
        "operation_cursor": "op:7",
    }
    engine_snapshot = {
        "snapshot_id": "engine-snapshot-3",
        "plan_id": plan_id,
        "scene_version": scene_version,
        "actors": [dict(entity) for entity in entities],
    }
    consistency = audit_scene_world_consistency(
        world_snapshot=snapshot,
        engine_snapshot=engine_snapshot,
    )
    consistency["engine_snapshot_available"] = True
    operation_entries = [
        {
            "event": event,
            "timestamp": float(index + 1),
            "payload": {"scene_version": scene_version},
        }
        for index, event in enumerate(
            (
                "finalizer_started",
                "tool_graph_queue_empty",
                "scene_plan_finalized",
                "scene_entity_registry_ready",
                "runtime_scene_world_consistency_audited",
                "scene_world_snapshot_ready",
            )
        )
    ]
    batches = [
        {
            "batch_id": f"batch-{index}",
            "plan_id": plan_id,
            "status": "completed",
            "tool_graph_id": f"graph-{index}",
        }
        for index in range(1, 4)
    ]
    graphs = [
        {
            "graph_id": f"graph-{index}",
            "batch_id": f"batch-{index}",
            "plan_id": plan_id,
            "graph_role": "business_batch",
            "status": "completed",
            "nodes": {},
        }
        for index in range(1, 4)
    ]
    registry = {
        "entity_count": 14,
        "game_ready_entity_count": game_ready_count,
        "engine_write_verified_count": 14,
        "readiness_missing_field_counts": {
            "support_classification": 14 - game_ready_count,
        },
        "entities": entities,
    }
    return {
        "room_id": "room-1",
        "plan_id": plan_id,
        "scene_version": scene_version,
        "snapshot_result": {
            "found": True,
            "plan_id": plan_id,
            "scene_version": scene_version,
            "snapshot_authority": "local_runtime",
            "snapshot_stability": "immutable",
            "world_fingerprint": fingerprint,
            "snapshot": snapshot,
        },
        "consistency_audit": consistency,
        "scene_entity_registry": registry,
        "required_environment_components": ["room_box", "room_floor"],
        "batch_plans": batches,
        "tool_graphs": graphs,
        "operation_entries": operation_entries,
        "runtime_events": [
            {
                "event_type": "report_ready",
                "timestamp": 7.0,
                "payload": {"scene_version": scene_version},
            }
        ],
        "engine_write_summary": {
            "boundary_fact_count": 3,
            "bridge_call_count": 14,
            "bridge_success_count": 14,
            "bridge_failed_count": 0,
        },
        "multiplayer_evidence": {
            "applicable": True,
            "peer_count": 1,
            "entity_count": 14,
            "verified_entity_count": 14,
            "partial_entity_count": 0,
            "identity_drift_count": 0,
            "version_drift_count": 0,
            "missing_fields_explicit": True,
        },
        "state_version": 9,
        "benchmark_profile": "bedroom_14",
        "expected_entity_count": 14,
        "evaluated_at": 7.0,
    }


class R3ReadinessGateTests(unittest.TestCase):
    def test_eight_of_fourteen_with_all_hard_conditions_is_green(self) -> None:
        report = evaluate_r3_gate(**_gate_facts(game_ready_count=8))

        self.assertEqual(report.overall, "green")
        self.assertEqual(tuple(report.dimensions), R3_DIMENSION_NAMES)
        self.assertEqual(report.dimensions["entity_readiness"].status, "green")
        R3GateReportValidator.validate(report)

    def test_five_of_fourteen_is_yellow(self) -> None:
        report = evaluate_r3_gate(**_gate_facts(game_ready_count=5))

        self.assertEqual(report.overall, "yellow")
        self.assertEqual(report.dimensions["entity_readiness"].status, "yellow")
        metrics = report.dimensions["entity_readiness"].metrics
        self.assertEqual(metrics["entity_diagnostics_total_count"], 9)
        self.assertEqual(metrics["entity_diagnostics_truncated_count"], 0)
        self.assertEqual(
            [item["entity_ref"] for item in metrics["entity_diagnostics"]],
            [f"entity-{index:02d}" for index in range(5, 14)],
        )
        self.assertTrue(
            all(
                item["readiness_missing_fields"] == ["support_classification"]
                for item in metrics["entity_diagnostics"]
            )
        )
        self.assertIn("readonly_snapshot_analysis", report.capability_unlocks)
        self.assertNotIn("action_proposal", report.capability_unlocks)

    def test_finalizer_events_from_different_scene_versions_do_not_form_green_chain(self) -> None:
        facts = _gate_facts(game_ready_count=8)
        facts["operation_entries"] = deepcopy(facts["operation_entries"])
        registry_event = next(
            entry
            for entry in facts["operation_entries"]
            if entry["event"] == "scene_entity_registry_ready"
        )
        registry_event["payload"]["scene_version"] = 2

        report = evaluate_r3_gate(**facts)

        dimension = report.dimensions["finalizer_completeness"]
        self.assertEqual(dimension.status, "red")
        self.assertIn("scene_entity_registry_ready", dimension.missing)
        self.assertIn("finalizer_scene_version_mismatch", dimension.contradictions)

    def test_entity_diagnostics_include_identity_failures_without_trusting_game_ready(self) -> None:
        facts = _gate_facts(game_ready_count=8)
        registry = deepcopy(facts["scene_entity_registry"])
        registry["entities"][0]["asset_id"] = ""
        registry["entities"][0]["model_ref"] = ""
        facts["scene_entity_registry"] = registry

        report = evaluate_r3_gate(**facts)

        dimension = report.dimensions["entity_readiness"]
        self.assertEqual(dimension.status, "red")
        diagnostics = dimension.metrics["entity_diagnostics"]
        entity = next(item for item in diagnostics if item["entity_ref"] == "entity-00")
        self.assertTrue(entity["game_ready"])
        self.assertEqual(entity["readiness_missing_fields"], ["asset_identity"])
        self.assertIn("entity-00:asset_identity", dimension.missing)

    def test_environment_fingerprint_and_identity_failures_are_red(self) -> None:
        missing_environment = _gate_facts(game_ready_count=8)
        missing_environment["required_environment_components"] = ["room_box", "room_floor", "ceiling"]
        environment_report = evaluate_r3_gate(**missing_environment)
        self.assertEqual(environment_report.overall, "red")
        self.assertIn(
            "environment_readiness:ceiling",
            environment_report.blockers,
        )

        bad_fingerprint = _gate_facts(game_ready_count=8)
        bad_fingerprint["snapshot_result"] = dict(bad_fingerprint["snapshot_result"])
        bad_fingerprint["snapshot_result"]["world_fingerprint"] = "0" * 64
        bad_fingerprint["snapshot_result"]["snapshot"] = dict(
            bad_fingerprint["snapshot_result"]["snapshot"]
        )
        bad_fingerprint["snapshot_result"]["snapshot"]["world_fingerprint"] = "0" * 64
        fingerprint_report = evaluate_r3_gate(**bad_fingerprint)
        self.assertEqual(fingerprint_report.dimensions["snapshot_integrity"].status, "red")

        identity_drift = _gate_facts(game_ready_count=8)
        registry = deepcopy(identity_drift["scene_entity_registry"])
        registry["entities"][1]["entity_id"] = registry["entities"][0]["entity_id"]
        identity_drift["scene_entity_registry"] = registry
        identity_report = evaluate_r3_gate(**identity_drift)
        self.assertEqual(identity_report.dimensions["entity_readiness"].status, "red")
        self.assertTrue(
            any("duplicate_entity_id" in item for item in identity_report.blockers)
        )

    def test_report_is_deterministic_for_identical_facts(self) -> None:
        facts = _gate_facts(game_ready_count=8)
        first = evaluate_r3_gate(**facts).as_dict()
        second = evaluate_r3_gate(**deepcopy(facts)).as_dict()

        self.assertEqual(first, second)
        self.assertEqual(first["gate_report_id"], second["gate_report_id"])

    def test_public_runtime_action_is_read_only_and_does_not_create_room(self) -> None:
        runtime = AgentRuntime()
        before_rooms = deepcopy(runtime.state.rooms)
        before_version = runtime.state.version
        before_log = [entry.as_dict() for entry in runtime.operation_log.entries()]

        first = runtime.handle_message(
            room_id="room-missing",
            text="",
            action="runtime.r3_readiness.evaluate",
        )
        second = runtime.handle_message(
            room_id="room-missing",
            text="",
            action="runtime.r3_readiness.evaluate",
        )

        self.assertTrue(first["handled"])
        self.assertFalse(first["recorded"])
        self.assertEqual(first["gate_report"]["overall"], "red")
        self.assertEqual(first["gate_report"], second["gate_report"])
        self.assertEqual(runtime.state.rooms, before_rooms)
        self.assertEqual(runtime.state.version, before_version)
        self.assertEqual(
            [entry.as_dict() for entry in runtime.operation_log.entries()],
            before_log,
        )
        policy = runtime.message_action_policy("runtime.r3_readiness.evaluate")
        self.assertTrue(policy["read_only"])
        self.assertFalse(policy["may_create_plan"])

    def test_public_runtime_action_does_not_mutate_existing_room(self) -> None:
        runtime = AgentRuntime()
        room = runtime.state.room("room-existing")
        room["latest_completed_plan_id"] = "plan-existing"
        room["scene_plans"] = {
            "plan-existing": {
                "plan_id": "plan-existing",
                "room_id": "room-existing",
                "title": "bedroom",
                "status": "completed",
                "version": 1,
            }
        }
        before_room = deepcopy(room)
        before_version = runtime.state.version
        before_log = [entry.as_dict() for entry in runtime.operation_log.entries()]

        result = runtime.handle_message(
            room_id="room-existing",
            text="",
            action="runtime.r3_readiness.evaluate",
        )

        self.assertTrue(result["found"])
        self.assertEqual(result["gate_report"]["overall"], "red")
        self.assertEqual(runtime.state.rooms["room-existing"], before_room)
        self.assertEqual(runtime.state.version, before_version)
        self.assertEqual(
            [entry.as_dict() for entry in runtime.operation_log.entries()],
            before_log,
        )


if __name__ == "__main__":
    unittest.main()
