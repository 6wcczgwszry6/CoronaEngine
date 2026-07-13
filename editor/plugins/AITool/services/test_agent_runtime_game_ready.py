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
)
from editor.plugins.AITool.services.lanchat_agent_worker import LANChatAgentWorker


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
        self.assertIn("engine_actual_aabb", snapshot["actor_entities"][0]["readiness_missing_fields"])

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
        self.assertLess(events.index("scene_world_snapshot_ready"), events.index("report_ready"))
        self.assertLess(events.index("report_ready"), events.index("latest_completed_plan_set"))


if __name__ == "__main__":
    unittest.main()
