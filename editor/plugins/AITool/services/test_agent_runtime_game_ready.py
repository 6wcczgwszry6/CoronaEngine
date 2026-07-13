from __future__ import annotations

import unittest
from unittest.mock import patch

from editor.plugins.AITool.services.agent_runtime import (
    AgentRuntime,
    BatchPlan,
    BatchPlanStatus,
    ScenePlan,
    ScenePlanStatus,
    StatePatch,
    ToolCall,
    ToolCallGraph,
    ToolCallGraphValidator,
    make_scene_snapshot_provider,
)
from editor.plugins.AITool.services.agent_runtime.scene_world_consistency import (
    audit_scene_world_consistency,
)
from editor.plugins.AITool.services.lanchat_agent_worker import LANChatAgentWorker
from editor.plugins.AITool.services.runtime_action_intent import RuntimeActionIntent


class _DispatchTrackingWorker(LANChatAgentWorker):
    def __init__(self, *, agent_runtime: AgentRuntime) -> None:
        super().__init__(agent_runtime=agent_runtime)
        self.authoritative_replies: list[str] = []

    def _send_coordinator_sync_system_reply(self, _message: dict, text: str) -> bool:
        self.authoritative_replies.append(str(text))
        return True

    def _send_final_reply(self, _agent_id: str, _agent_name: str, text: str, *_args, **_kwargs) -> bool:
        self.authoritative_replies.append(str(text))
        return True


class _ClientDispatchTrackingWorker(_DispatchTrackingWorker):
    def _can_execute_generation_locally(self) -> bool:
        return False


class _RuntimeIdentitySnapshotTool:
    def invoke(self, _payload: dict) -> dict:
        return {
            "status": "success",
            "actors": [
                {
                    "actor_guid": "actor-runtime-1",
                    "name": "desk",
                    "entity_id": "entity-runtime-1",
                    "asset_id": "asset-desk",
                    "model_ref": "asset-desk",
                    "entity_type": "furniture",
                    "semantic_role": "desk",
                    "source_plan_id": "plan-runtime-1",
                    "source_batch_id": "batch-runtime-1",
                    "actor_version": 4,
                    "bounds_ready": True,
                    "world_aabb": [-1.0, 0.0, -0.5, 1.0, 1.2, 0.5],
                    "geometry": {
                        "position": [0.0, 0.0, 0.0],
                        "rotation": [0.0, 0.0, 0.0],
                        "scale": [1.0, 1.0, 1.0],
                    },
                }
            ],
        }


def _room_fact(*, game_ready: bool) -> dict:
    actor = {
        "plan_id": "plan-1",
        "batch_id": "batch-1",
        "name": "丘比特雕像",
        "requested_name": "丘比特雕像",
        "asset_id": "asset-cupid",
        "model_ref": "cupid.obj",
        "position": [0.0, 0.0, 0.0],
        "rotation": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
        "aabb": {"min": [-0.5, 0.0, -0.5], "max": [0.5, 1.8, 0.5]},
        "bounds_source": "engine_actual" if game_ready else "estimated",
        "bounds_ready": True,
        "engine_lifecycle_status": "bounds_ready",
        "sync_status": "engine_created",
        "grounding_status": "grounded",
        "source": "engine_actor_import",
        "status": "success",
    }
    return {
        "active_execution_plan_id": "",
        "latest_completed_plan_id": "plan-1",
        "scene_plans": {
            "plan-1": {
                "plan_id": "plan-1",
                "room_id": "room-1",
                "title": "test",
                "status": "completed",
                "version": 2,
                "concrete_object_items": ["丘比特雕像"],
            }
        },
        "batch_plans": {
            "batch-1": {
                "batch_id": "batch-1",
                "plan_id": "plan-1",
                "room_id": "room-1",
                "status": "completed",
                "tool_graph_id": "graph-business",
            }
        },
        "actors": {"actor-cupid": actor},
        "observed_actors": {"actor-cupid": actor},
    }


class AgentRuntimeGameReadyTests(unittest.TestCase):
    def test_engine_snapshot_preserves_runtime_identity_and_actual_bounds(self) -> None:
        provider = make_scene_snapshot_provider(
            snapshot_tool=_RuntimeIdentitySnapshotTool(),
            scene_name="Scene/runtime-identity.scene",
        )

        snapshot = provider({"room_id": "room-runtime-identity"})
        self.assertEqual(snapshot["actor_count"], 1)
        actor = snapshot["actors"][0]
        self.assertEqual(actor["actor_id"], "actor-runtime-1")
        self.assertEqual(actor["entity_id"], "entity-runtime-1")
        self.assertEqual(actor["asset_id"], "asset-desk")
        self.assertEqual(actor["model_ref"], "asset-desk")
        self.assertEqual(actor["plan_id"], "plan-runtime-1")
        self.assertEqual(actor["batch_id"], "batch-runtime-1")
        self.assertEqual(actor["actor_version"], 4)
        self.assertEqual(actor["entity_version"], 4)
        self.assertEqual(actor["version"], 4)
        self.assertEqual(actor["bounds_source"], "engine_actual")
        self.assertEqual(actor["engine_lifecycle_status"], "bounds_ready")
        self.assertEqual(actor["sync_status"], "engine_imported")

    def test_non_authoritative_client_does_not_execute_completed_scene_write(self) -> None:
        runtime = AgentRuntime()
        applied, _ = runtime.state.apply_patch(StatePatch(room_id="room-1", changes=_room_fact(game_ready=True)))
        self.assertTrue(applied)
        worker = _ClientDispatchTrackingWorker(agent_runtime=runtime)
        intent = RuntimeActionIntent(
            message_id="msg-client-write",
            room_id="room-1",
            route="runtime_write",
            operation="add",
            modality="command",
            confidence=0.99,
            target_plan_id="plan-1",
        )
        message = {
            "room_id": "room-1",
            "message_id": "msg-client-write",
            "text": "add a table",
            "sender_id": "member-1",
            "sender_name": "member",
            "sender_type": "user",
            "message_kind": "chat",
        }

        with patch.object(worker, "_runtime_action_intent_for_trigger", return_value=intent):
            handled = worker.sync_chat_message_to_coordinator(message, source="lanchat_native_queue")

        self.assertTrue(handled)
        self.assertEqual(runtime.state.room("room-1").get("pending_interventions", {}), {})
        self.assertEqual(worker.authoritative_replies, [])

    def test_native_and_agent_trigger_share_one_authoritative_query_reply(self) -> None:
        runtime = AgentRuntime()
        applied, _ = runtime.state.apply_patch(StatePatch(room_id="room-1", changes=_room_fact(game_ready=True)))
        self.assertTrue(applied)
        worker = _DispatchTrackingWorker(agent_runtime=runtime)
        message = {
            "room_id": "room-1",
            "message_id": "msg-shared-query",
            "text": "@GM 丘比特雕像已经加入了吗",
            "sender_id": "host-1",
            "sender_name": "房主",
            "sender_type": "host",
            "message_kind": "chat",
            "agent_id": "gm",
            "agent_name": "GM",
            "is_host": True,
        }

        self.assertTrue(worker.sync_chat_message_to_coordinator(dict(message), source="lanchat_native_queue"))
        self.assertTrue(worker._process_trigger(dict(message)))

        self.assertEqual(len(worker.authoritative_replies), 1)
        ledger = worker._message_dispatch_ledger.entry("room-1", "msg-shared-query")
        self.assertEqual(ledger.get("owner"), "native_queue")
        self.assertEqual(ledger.get("state"), "replied")

    def test_worker_entity_question_is_read_only_end_to_end(self) -> None:
        runtime = AgentRuntime()
        applied, _ = runtime.state.apply_patch(StatePatch(room_id="room-1", changes=_room_fact(game_ready=True)))
        self.assertTrue(applied)
        worker = LANChatAgentWorker(agent_runtime=runtime)
        before = runtime.state.room("room-1")

        reply = worker._handle_runtime_entity_status_query({
            "room_id": "room-1",
            "message_id": "msg-query",
            "text": "@GM 丘比特雕像已经加入了吗",
        })

        after = runtime.state.room("room-1")
        self.assertIn("丘比特雕像", reply or "")
        self.assertEqual(before.get("tool_graphs", {}), after.get("tool_graphs", {}))
        self.assertEqual(before.get("pending_interventions", {}), after.get("pending_interventions", {}))

    def test_worker_typo_add_returns_clarification_without_patch(self) -> None:
        runtime = AgentRuntime()
        applied, _ = runtime.state.apply_patch(StatePatch(room_id="room-1", changes=_room_fact(game_ready=True)))
        self.assertTrue(applied)
        worker = LANChatAgentWorker(agent_runtime=runtime)

        reply = worker._handle_runtime_completed_increment({
            "room_id": "room-1",
            "message_id": "msg-typo",
            "text": "再加入一个切比特雕像",
        })

        self.assertIn("丘比特雕像", reply or "")
        self.assertEqual(runtime.state.room("room-1").get("pending_interventions", {}), {})

    def test_entity_status_query_does_not_create_graph_or_patch(self) -> None:
        runtime = AgentRuntime()
        applied, _ = runtime.state.apply_patch(StatePatch(room_id="room-1", changes=_room_fact(game_ready=True)))
        self.assertTrue(applied)
        before = runtime.state.room("room-1")

        result = runtime.handle_message(
            room_id="room-1",
            plan_id="plan-1",
            text="",
            action="runtime.entity_status",
            sync_event={"entity_names": ["丘比特雕像"]},
        )

        after = runtime.state.room("room-1")
        self.assertFalse(result["recorded"])
        self.assertEqual(len(result["entity_status"]["丘比特雕像"]), 1)
        self.assertEqual(before.get("tool_graphs", {}), after.get("tool_graphs", {}))
        self.assertEqual(before.get("pending_interventions", {}), after.get("pending_interventions", {}))

    def test_snapshot_distinguishes_partial_world_from_pipeline_completion(self) -> None:
        room = _room_fact(game_ready=False)
        registry = AgentRuntime._scene_entity_registry_for_plan(room, "plan-1")
        snapshot = AgentRuntime._scene_world_snapshot_for_plan(
            room,
            "plan-1",
            room_id="room-1",
            scene_entity_registry=registry,
            operation_cursor="op:10",
        )

        self.assertEqual(snapshot["scene_version"], 2)
        self.assertEqual(snapshot["world_readiness"], "needs_review")
        self.assertEqual(len(snapshot["world_fingerprint"]), 64)
        self.assertIn("engine_actual_aabb", snapshot["actor_entities"][0]["readiness_missing_fields"])

    def test_partial_sync_status_blocks_game_ready_snapshot(self) -> None:
        room = _room_fact(game_ready=True)
        room["actors"]["actor-cupid"]["sync_status"] = "partial"
        room["observed_actors"]["actor-cupid"]["sync_status"] = "partial"

        registry = AgentRuntime._scene_entity_registry_for_plan(room, "plan-1")
        snapshot = AgentRuntime._scene_world_snapshot_for_plan(
            room,
            "plan-1",
            room_id="room-1",
            scene_entity_registry=registry,
            operation_cursor="op:11",
        )

        self.assertEqual(registry["game_ready_entity_count"], 0)
        self.assertEqual(snapshot["world_readiness"], "needs_review")
        self.assertEqual(snapshot["actor_entities"][0]["sync_status"], "partial")
        self.assertIn(
            "sync_status_ready",
            snapshot["actor_entities"][0]["readiness_missing_fields"],
        )

    def test_registry_entities_carry_stable_versions_and_source_identity(self) -> None:
        room = _room_fact(game_ready=True)
        actor = room["actors"]["actor-cupid"]
        actor["actor_request_id"] = "actor-request-cupid"
        actor["actor_version"] = 7
        room["element_routes"] = {
            "batch-1": [
                {
                    "name": "grass",
                    "target_pipeline": "environment",
                }
            ]
        }

        first = AgentRuntime._scene_entity_registry_for_plan(room, "plan-1")
        first_actor = next(entity for entity in first["entities"] if entity.get("actor_id") == "actor-cupid")
        substrate = next(entity for entity in first["entities"] if entity.get("entity_type") == "substrate")
        first_entity_id = first_actor["entity_id"]

        room["actors"]["actor-cupid-reloaded"] = room["actors"].pop("actor-cupid")
        second = AgentRuntime._scene_entity_registry_for_plan(room, "plan-1")
        second_actor = next(
            entity for entity in second["entities"] if entity.get("actor_id") == "actor-cupid-reloaded"
        )

        self.assertEqual(first_actor["version"], 7)
        self.assertEqual(first_actor["version_source"], "engine_actual")
        self.assertEqual(first_actor["entity_id_source"], "request_identity")
        self.assertEqual(first_entity_id, second_actor["entity_id"])
        self.assertEqual(first_actor["source_plan_id"], "plan-1")
        self.assertEqual(first_actor["source_batch_id"], "batch-1")
        self.assertEqual(substrate["version"], 2)
        self.assertEqual(substrate["version_source"], "scene_version")

    def test_public_snapshot_api_is_read_only_and_uses_latest_completed_plan(self) -> None:
        runtime = AgentRuntime()
        applied, _ = runtime.state.apply_patch(StatePatch(room_id="room-1", changes=_room_fact(game_ready=True)))
        self.assertTrue(applied)
        before = runtime.state.room("room-1")

        result = runtime.handle_message(
            room_id="room-1",
            text="",
            action="runtime.scene_world_snapshot.get",
        )

        after = runtime.state.room("room-1")
        self.assertTrue(result["found"])
        self.assertEqual(result["plan_id"], "plan-1")
        self.assertEqual(result["scene_version"], 2)
        self.assertEqual(result["snapshot_stability"], "provisional")
        self.assertEqual(before.get("tool_graphs", {}), after.get("tool_graphs", {}))
        self.assertEqual(before.get("pending_interventions", {}), after.get("pending_interventions", {}))

    def test_public_snapshot_api_rejects_unavailable_minimum_version(self) -> None:
        runtime = AgentRuntime()
        applied, _ = runtime.state.apply_patch(StatePatch(room_id="room-1", changes=_room_fact(game_ready=True)))
        self.assertTrue(applied)

        result = runtime.handle_message(
            room_id="room-1",
            text="",
            action="runtime.scene_world_snapshot.get",
            sync_event={"min_version": 3},
        )

        self.assertFalse(result["found"])
        self.assertEqual(result["scene_version"], 2)
        self.assertEqual(result["reason"], "minimum_scene_version_not_available")

    def test_world_consistency_audit_matches_runtime_and_engine_identity(self) -> None:
        room = _room_fact(game_ready=True)
        registry = AgentRuntime._scene_entity_registry_for_plan(room, "plan-1")
        entity = next(row for row in registry["entities"] if row.get("actor_id") == "actor-cupid")
        room["engine_scene_snapshots"] = {
            "snapshot-runtime-1": {
                "snapshot_id": "snapshot-runtime-1",
                "room_id": "room-1",
                "scene_name": "Scene/runtime.scene",
                "plan_id": "plan-1",
                "actor_count": 1,
                "source": "scene_snapshot_tool",
                "timestamp": 10.0,
                "actors": [
                    {
                        "actor_id": entity["actor_id"],
                        "entity_id": entity["entity_id"],
                        "asset_id": entity["asset_id"],
                        "model_ref": entity["model_ref"],
                        "name": entity["name"],
                        "source": "scene_snapshot",
                        "status": "success",
                        "version": entity["version"],
                        "entity_version": entity["version"],
                        "bounds_ready": True,
                        "bounds_source": "engine_actual",
                        "engine_lifecycle_status": "bounds_ready",
                        "sync_status": "engine_imported",
                        "aabb": [-0.5, 0, -0.5, 0.5, 1.8, 0.5],
                        "position": [0, 0, 0],
                        "rotation": entity["transform"]["rotation"],
                        "scale": entity["transform"]["scale"],
                    }
                ],
            }
        }
        runtime = AgentRuntime()
        applied, _ = runtime.state.apply_patch(StatePatch(room_id="room-1", changes=room))
        self.assertTrue(applied)
        before = runtime.state.room("room-1")

        result = runtime.handle_message(
            room_id="room-1",
            text="",
            action="runtime.scene_world_consistency.audit",
        )

        after = runtime.state.room("room-1")
        self.assertTrue(result["found"])
        self.assertEqual(result["audit"]["status"], "consistent")
        self.assertEqual(result["audit"]["matched_entity_count"], 1)
        self.assertEqual(result["audit"]["issue_count"], 0)
        self.assertTrue(result["audit"]["fingerprints_match"])
        self.assertEqual(
            result["audit"]["world_fingerprint"],
            result["audit"]["engine_fingerprint"],
        )
        self.assertEqual(before.get("tool_graphs", {}), after.get("tool_graphs", {}))
        self.assertEqual(before.get("pending_interventions", {}), after.get("pending_interventions", {}))
        policy = AgentRuntime.message_action_policy("runtime.scene_world_consistency.audit")
        self.assertEqual(policy["category"], "read_only")

    def test_world_consistency_audit_reports_identity_and_version_drift(self) -> None:
        room = _room_fact(game_ready=True)
        registry = AgentRuntime._scene_entity_registry_for_plan(room, "plan-1")
        entity = next(row for row in registry["entities"] if row.get("actor_id") == "actor-cupid")
        room["engine_scene_snapshots"] = {
            "snapshot-drift": {
                "snapshot_id": "snapshot-drift",
                "room_id": "room-1",
                "scene_name": "Scene/runtime.scene",
                "plan_id": "plan-1",
                "actor_count": 2,
                "source": "scene_snapshot_tool",
                "timestamp": 20.0,
                "actors": [
                    {
                        "actor_id": entity["actor_id"],
                        "entity_id": entity["entity_id"],
                        "asset_id": "asset-wrong",
                        "name": entity["name"],
                        "source": "scene_snapshot",
                        "version": entity["version"] + 1,
                    },
                    {
                        "actor_id": "actor-without-runtime-identity",
                        "name": "manual actor",
                        "source": "scene_snapshot",
                        "version": 1,
                    },
                ],
            }
        }
        runtime = AgentRuntime()
        applied, _ = runtime.state.apply_patch(StatePatch(room_id="room-1", changes=room))
        self.assertTrue(applied)

        result = runtime.handle_message(
            room_id="room-1",
            text="",
            action="runtime.scene_world_consistency.audit",
        )

        audit = result["audit"]
        self.assertEqual(audit["status"], "needs_review")
        self.assertEqual(audit["unidentified_engine_actor_ids"], ["actor-without-runtime-identity"])
        self.assertEqual(audit["asset_id_mismatches"][0]["entity_id"], entity["entity_id"])
        self.assertEqual(audit["version_mismatches"][0]["actual"], entity["version"] + 1)
        self.assertEqual(audit["transform_mismatches"][0]["entity_id"], entity["entity_id"])
        self.assertEqual(audit["world_aabb_mismatches"][0]["entity_id"], entity["entity_id"])
        self.assertFalse(audit["fingerprints_match"])

    def test_world_consistency_audit_rejects_non_materialized_runtime_entity(self) -> None:
        materialized = {
            "entity_id": "entity-desk",
            "actor_id": "actor-desk",
            "asset_id": "asset-desk",
            "model_ref": "desk.obj",
            "version": 1,
            "transform": {
                "position": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
            },
            "world_aabb": {"min": [-0.5, 0.0, -0.5], "max": [0.5, 1.0, 0.5]},
        }
        planned_only = {
            "entity_id": "entity-terrain",
            "actor_id": "",
            "asset_id": "asset-terrain",
            "model_ref": "terrain.obj",
            "version": 1,
            "transform": {},
            "world_aabb": {},
        }

        audit = audit_scene_world_consistency(
            world_snapshot={
                "plan_id": "plan-1",
                "scene_version": 1,
                "environment_entities": [planned_only],
                "actor_entities": [materialized],
            },
            engine_snapshot={
                "snapshot_id": "snapshot-partial-world",
                "plan_id": "plan-1",
                "actors": [materialized],
            },
        )

        self.assertEqual(audit["status"], "needs_review")
        self.assertEqual(audit["non_materialized_entity_count"], 1)
        self.assertGreaterEqual(audit["issue_count"], 1)
        self.assertFalse(audit["fingerprints_match"])

    def test_environment_support_semantics_are_game_ready_specific(self) -> None:
        room = _room_fact(game_ready=True)
        room["environment_components"] = {
            "batch-1": {
                "floor": {
                    "component_id": "floor",
                    "component_type": "room_floor",
                    "actor_id": "actor-floor",
                    "asset_id": "asset-floor",
                    "model_ref": "room_floor.obj",
                    "position": [0.0, 0.0, 0.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0],
                    "aabb": {"min": [-3.0, 0.0, -3.0], "max": [3.0, 0.1, 3.0]},
                    "bounds_source": "engine_actual",
                    "bounds_ready": True,
                    "engine_lifecycle_status": "bounds_ready",
                    "sync_status": "engine_created",
                    "source": "engine_environment_import",
                    "status": "success",
                },
                "shell": {
                    "component_id": "shell",
                    "component_type": "room_box",
                    "actor_id": "actor-shell",
                    "asset_id": "asset-shell",
                    "model_ref": "room_box.obj",
                    "position": [0.0, 0.0, 0.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0],
                    "aabb": {"min": [-3.0, 0.0, -3.0], "max": [3.0, 3.0, 3.0]},
                    "bounds_source": "engine_actual",
                    "bounds_ready": True,
                    "engine_lifecycle_status": "bounds_ready",
                    "sync_status": "engine_created",
                    "source": "engine_environment_import",
                    "status": "success",
                },
            }
        }

        registry = AgentRuntime._scene_entity_registry_for_plan(room, "plan-1")
        support_by_component = {
            entity["component_type"]: entity["grounding_status"]
            for entity in registry["entities"]
            if entity.get("entity_type") == "environment"
        }

        self.assertEqual(support_by_component["room_floor"], "grounded")
        self.assertEqual(support_by_component["room_box"], "enclosure")

    def test_business_graph_role_is_persisted_and_validated(self) -> None:
        graph = ToolCallGraph(
            graph_id="graph-business",
            plan_id="plan-1",
            batch_id="batch-1",
            graph_role="business_batch",
        )
        graph.add(ToolCall(tool_call_id="tool-1", tool_name="mock.echo"))
        fact = ToolCallGraphValidator.safe_graph_fact(graph)

        ToolCallGraphValidator.validate_graph_fact(fact)
        self.assertEqual(fact["graph_role"], "business_batch")

    def test_report_separates_business_batches_from_internal_graphs(self) -> None:
        runtime = AgentRuntime()
        plan = runtime.propose_scene_plan(
            room_id="room-graph-domains",
            text="simple bedroom with bed and desk",
            owner_agent="tester",
        )
        runtime.confirm_scene_plan(plan.plan_id, confirmed_by="host")
        queued = runtime.enqueue_planned_batches(plan.plan_id, max_items_per_batch=1)

        report = runtime.generate_report("room-graph-domains", plan_id=plan.plan_id)
        domains = report["tool_graph_domain_summary"]

        self.assertEqual(domains["business_batch_count"], len(queued["batches"]))
        self.assertGreater(domains["internal_graph_count"], 0)
        self.assertEqual(
            domains["total_graph_count"],
            domains["business_batch_count"] + domains["internal_graph_count"],
        )
        self.assertEqual(report["completion_status"]["pipeline_status"], "running")
        self.assertNotEqual(report["completion_status"]["world_readiness"], "game_ready")

    def test_finalizer_records_registry_and_snapshot_before_report_ready(self) -> None:
        runtime = AgentRuntime()
        plan = ScenePlan(
            plan_id="plan-finalizer-order",
            room_id="room-finalizer-order",
            title="order",
            design_brief="order",
            status=ScenePlanStatus.COMPLETED,
        )
        batch = BatchPlan(
            batch_id="batch-finalizer-order",
            plan_id=plan.plan_id,
            room_id=plan.room_id,
            requested_items=["table"],
            status=BatchPlanStatus.COMPLETED,
        )
        registry = {"entity_count": 1, "game_ready_entity_count": 0, "entities": [{}]}
        snapshot = {
            "scene_version": 1,
            "world_readiness": "needs_review",
            "environment_entities": [],
            "actor_entities": [{}],
            "operation_cursor": "op:1",
        }
        report = {"scene_entity_registry": registry, "scene_world_snapshot": snapshot}

        def generate_report(*_args, **_kwargs):
            runtime.operation_log.append("report_ready", room_id=plan.room_id, plan_id=plan.plan_id)
            return report

        with (
            patch.object(runtime, "_runtime_plan_by_id_from_state", return_value=plan),
            patch.object(runtime, "_planned_batches_for_plan", return_value=[batch]),
            patch.object(runtime, "_reconcile_partial_engine_readiness", return_value={}),
            patch.object(runtime, "_scene_entity_registry_for_plan", return_value=registry),
            patch.object(runtime, "_scene_world_snapshot_for_plan", return_value=snapshot),
            patch.object(runtime, "_latest_persisted_report_for_plan", side_effect=[{}, report]),
            patch.object(runtime, "generate_report", side_effect=generate_report),
            patch.object(runtime, "_persist_plan_identity_changes", return_value=True),
        ):
            result = runtime._finalize_plan_after_queue_drain(
                room_id=plan.room_id,
                plan_id=plan.plan_id,
            )

        self.assertTrue(result["report_ready"])
        events = runtime.operation_log.events()
        self.assertLess(events.index("scene_entity_registry_ready"), events.index("scene_world_snapshot_ready"))
        self.assertLess(
            events.index("scene_world_snapshot_ready"),
            events.index("runtime_scene_world_consistency_audited"),
        )
        self.assertLess(
            events.index("runtime_scene_world_consistency_audited"),
            events.index("report_ready"),
        )
        self.assertLess(events.index("scene_world_snapshot_ready"), events.index("report_ready"))
        self.assertLess(events.index("report_ready"), events.index("latest_completed_plan_set"))


if __name__ == "__main__":
    unittest.main()
