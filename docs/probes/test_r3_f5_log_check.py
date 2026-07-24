from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from docs.probes.r3_f5_log_check import run, run_control_plane, run_scene_runtime, summarize


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
CONTROL_LOG = FIXTURE_DIR / "2026-07-19_b5_control_plane_corona.log"
CONTROL_HISTORY = FIXTURE_DIR / "2026-07-19_b5_control_plane_history.jsonl"


GREEN_TRACE = (
    "[R3GateTrace] room=room-1 plan=plan-1 scene_version=2 overall=green "
    "dimensions=snapshot_integrity:green,environment_readiness:green,entity_readiness:green,"
    "finalizer_completeness:green,business_graph_consistency:green,"
    "multiplayer_consistency:green,runtime_write_safety:green "
    "game_ready=8/14 render=10/10 render_observed=10/10"
)


def evidence(internal: int, *, active: int = 0, terminal: int = 3) -> str:
    return (
        "[LANChatRuntimeEvidence] phase=runtime_queue_drain_result room=room-1 "
        "runtime_plan=plan-1 batches=total:3,active:0,terminal:3 "
        f"graphs=business:3,internal:{internal},active:{active},terminal:{terminal} "
        "drain=status:drained,drained:0"
    )


class R3F5LogCheckTests(unittest.TestCase):
    def _run(self, lines: list[str]):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture_corona.log"
            path.write_text("\n".join(lines), encoding="utf-8")
            return run(path)

    def test_green_trace_and_bounded_terminal_growth_are_ready(self) -> None:
        checks, metadata = self._run([GREEN_TRACE, evidence(40), evidence(48)])

        self.assertEqual(summarize(checks), "R3_F5_READY: PASS=11 WARN=0 FAIL=0")
        self.assertEqual(metadata["overall"], "green")
        self.assertEqual(metadata["game_ready"], "8/14")

    def test_old_failure_shape_reports_gate_and_internal_graph_explosion(self) -> None:
        red_trace = GREEN_TRACE.replace("overall=green", "overall=red").replace(
            "finalizer_completeness:green",
            "finalizer_completeness:red",
        ).replace("game_ready=8/14", "game_ready=0/14").replace(
            "render=10/10 render_observed=10/10",
            "render=0/2 render_observed=0/2",
        )
        checks, _ = self._run([red_trace, evidence(85), evidence(352)])
        by_name = {check.name: check for check in checks}

        self.assertEqual(by_name["r3-gate-trace"].level, "FAIL")
        self.assertEqual(by_name["finalizer_completeness"].level, "FAIL")
        self.assertEqual(by_name["terminal-internal-graph-growth"].level, "FAIL")
        self.assertEqual(by_name["render-readiness"].level, "FAIL")
        self.assertTrue(summarize(checks).startswith("R3_F5_BLOCKED"))

    def test_missing_gate_trace_is_blocked_without_guessing(self) -> None:
        checks, metadata = self._run([evidence(10)])

        self.assertEqual(checks[0].name, "r3-gate-trace")
        self.assertEqual(checks[0].level, "FAIL")
        self.assertEqual(metadata["gate_trace_count"], 0)

    def test_b5_control_plane_fixture_reproduces_known_f5_failures(self) -> None:
        checks, metadata = run(CONTROL_LOG, CONTROL_HISTORY)
        control = metadata["control_plane"]
        turns = {turn["message_id"]: turn for turn in control["turns"]}
        session = control["session"]

        bedroom_turn = turns["local-single-player:1784447857297:5"]
        self.assertEqual(bedroom_turn["final_reply_count"], 1)
        self.assertEqual(bedroom_turn["progress_count"], 1)
        self.assertEqual(bedroom_turn["action_status_count"], 1)
        self.assertIn("runtime_reply_contradiction", bedroom_turn["diagnostics"])

        elder_turn = turns["local-single-player:1784447977239:11"]
        self.assertEqual(elder_turn["expected_target_name"], "长者")
        self.assertEqual(elder_turn["final_reply_count"], 2)
        self.assertEqual(elder_turn["actual_reply_senders"], ("小女孩", "长者"))
        self.assertEqual(elder_turn["processing_owners"], ())
        self.assertEqual(
            elder_turn["model_call_purposes"],
            ("inferred:plan_context/plan_drafting",),
        )
        self.assertIn("reply_target_mismatch", elder_turn["diagnostics"])
        self.assertIn("formal_processing_owner_missing", elder_turn["diagnostics"])
        self.assertIn("command_fragment_used_as_entity", elder_turn["diagnostics"])
        self.assertIn("duplicate_template_reply", elder_turn["diagnostics"])

        confirmation = turns["local-single-player:1784448276902:14"]
        self.assertIn("plan_owner_mismatch", confirmation["diagnostics"])
        self.assertIn("plan-d37bebb0578d", confirmation["plan_refs"])

        self.assertEqual(session["duplicate_heartbeat_count"], 20)
        self.assertEqual(session["invalid_entity_fragments"], ("请你给出一个方案",))
        self.assertTrue(session["finalizer_disclosure_order_violation"])
        self.assertEqual(session["quasar_import_roots"], ("Quasar", "plugins.AITool.Quasar"))
        self.assertEqual(session["explicit_model_purpose_count"], 0)
        self.assertEqual(session["inferred_model_purpose_count"], 2)
        self.assertTrue(session["plan_owner_mismatches"])

        by_name = {check.name: check for check in checks}
        self.assertEqual(by_name["control-single-final-reply"].level, "FAIL")
        self.assertEqual(by_name["control-target-authority"].level, "FAIL")
        self.assertEqual(by_name["control-single-processing-owner"].level, "FAIL")
        self.assertEqual(by_name["control-native-defer-zero-mutation"].level, "PASS")
        self.assertEqual(by_name["control-heartbeat-deduplication"].level, "FAIL")
        self.assertEqual(by_name["control-finalizer-disclosure-order"].level, "FAIL")
        self.assertEqual(by_name["control-quasar-import-root"].level, "FAIL")
        self.assertEqual(by_name["control-model-purpose-observability"].level, "WARN")
        self.assertTrue(summarize(checks).startswith("R3_F5_BLOCKED"))

    def test_b7_1_profile_requires_all_fixed_turns_and_isolated_control_contract(self) -> None:
        checks, metadata = run_control_plane(CONTROL_LOG, CONTROL_HISTORY)
        by_name = {check.name: check for check in checks}

        self.assertEqual(metadata["profile"], "control-plane")
        self.assertEqual(by_name["b7.1-fixed-turn-coverage"].level, "FAIL")
        self.assertIn("@小女孩 围绕迪士尼乐园主题讨论一下", by_name["b7.1-fixed-turn-coverage"].detail)
        self.assertEqual(by_name["b7.1-turn-contract"].level, "FAIL")
        self.assertTrue(summarize(checks, profile="control-plane").startswith("B7_1_CONTROL_BLOCKED"))

    def test_b7_1_profile_accepts_versioned_six_turn_contract(self) -> None:
        proposal_purposes = (
            "planning_artifact_reasoning",
            "program_artifact_reasoning",
            "art_artifact_reasoning",
            "collaboration_proposal_narration",
        )
        turn_specs = (
            ("m1", "@小女孩 围绕迪士尼乐园主题讨论一下", "girl", "小女孩", "agent_trigger", 1, ("agent_visible_reasoning",), "discussion_reply", "discussion", "", "你好，我们可以围绕迪士尼乐园主题聊聊。"),
            ("m2", "@小女孩  按照迪士尼风格的卧室来设计呢", "girl", "小女孩", "agent_trigger", 4, proposal_purposes, "planning_proposal", "plan_drafting", "legacy-plan:proposal-room-001@1", "已形成针对迪士尼卧室的待确认方案。"),
            ("m3", "@GM 确认生成", "gm", "GM", "native_queue", 0, (), "runtime_write_blocked", "generation_start", "legacy-plan:proposal-room-001@1", "方案引用已核对，当前 Red Gate 不执行写入。"),
            ("m4", "@长者 请你给出一个方案", "elder", "长者", "agent_trigger", 4, proposal_purposes, "planning_proposal", "plan_drafting", "legacy-plan:proposal-room-001@2", "已形成针对当前目标的第二版待确认方案。"),
            ("m5", "@长者 确认开始", "elder", "长者", "agent_trigger", 0, (), "runtime_write_blocked", "generation_start", "legacy-plan:proposal-room-001@2", "方案引用已核对，当前 Red Gate 不执行写入。"),
            ("m6", "@小女孩 你好", "girl", "小女孩", "agent_trigger", 1, ("agent_visible_reasoning",), "discussion_reply", "discussion", "", "你好，我在的。"),
        )
        history: list[str] = []
        log_lines = ["[Python] Quasar.ai_service.entrance initialized"]
        seq = 1
        proposal_metadata = {
            "legacy-plan:proposal-room-001@1": {
                "proposal_id": "proposal-room-001",
                "proposal_version": 1,
                "proposal_hash": "sha256:girl",
                "artifact_refs": ["artifact:brief@1", "artifact:level@1"],
            },
            "legacy-plan:proposal-room-001@2": {
                "proposal_id": "proposal-room-001",
                "proposal_version": 2,
                "proposal_hash": "sha256:elder",
                "artifact_refs": ["artifact:brief@2", "artifact:level@2"],
            },
        }
        for message_id, text, target_id, target_name, owner, calls, purposes, contract, intent, artifact_ref, reply_text in turn_specs:
            user_metadata = {
                "target_agent_id": target_id,
                "target_agent_name": target_name,
            }
            history.append(json.dumps({
                "message_id": message_id,
                "sender_id": "host",
                "sender_name": "房主",
                "room_id": "room-b7-ready",
                "text": text,
                "seq": seq,
                "timestamp_ms": seq,
                "sender_type": "user",
                "message_kind": "chat",
                "correlation_id": message_id,
                "metadata_json": json.dumps(user_metadata, ensure_ascii=False),
            }, ensure_ascii=False))
            seq += 1
            reply_metadata = {
                "reply_to": message_id,
                "reply_contract": contract,
                "resolved_intent": intent,
            }
            if artifact_ref:
                proposal_values = proposal_metadata[artifact_ref]
                reply_metadata.update({
                    "artifact_ref": "legacy-plan:proposal-room-001",
                    "agent_plan_id": proposal_values["proposal_id"],
                    **proposal_values,
                })
            message_kind = "gm_proposal" if contract == "planning_proposal" else "agent_reply"
            authoritative_gm = contract in {
                "planning_proposal",
                "generation_confirmation",
                "runtime_write_blocked",
            }
            if message_kind == "gm_proposal":
                reply_metadata.update({
                    "origin_message_id": message_id,
                    "origin_correlation_id": message_id,
                })
            history.append(json.dumps({
                "message_id": f"r-{message_id}",
                "sender_id": "gm" if authoritative_gm else target_id,
                "sender_name": "GM" if authoritative_gm else target_name,
                "room_id": "room-b7-ready",
                "text": reply_text,
                "seq": seq,
                "timestamp_ms": seq,
                "sender_type": "agent",
                "message_kind": message_kind,
                "correlation_id": message_id,
                "metadata_json": json.dumps(reply_metadata, ensure_ascii=False),
            }, ensure_ascii=False))
            seq += 1
            log_lines.append(
                f"[LANChatDispatchLedger] phase=execution_claimed owner={owner} "
                f"route=agent_chat room=room-b7-ready message_id={message_id}"
            )
            log_lines.append(
                f"[LANChatModelCallSummary] message_id={message_id} correlation={message_id} "
                f"room=room-b7-ready calls={calls} purposes={','.join(purposes)}"
            )
            for purpose in purposes:
                log_lines.append(
                    f"[LANChatModelCall] message_id={message_id} correlation={message_id} "
                    f"room=room-b7-ready purpose={purpose} provider=quasar model=test"
                )
                log_lines.append(
                    f"[LANChatModelCallResult] message_id={message_id} correlation={message_id} "
                    f"room=room-b7-ready purpose={purpose} provider=quasar model=test "
                    "elapsed_ms=1000 result=completed error_code="
                )
        history.extend([
            json.dumps({
                "message_id": "status-snapshot",
                "sender_id": "system",
                "sender_name": "系统",
                "room_id": "room-b7-ready",
                "text": "场景快照已刷新",
                "seq": seq,
                "timestamp_ms": seq,
                "sender_type": "system",
                "message_kind": "runtime_status",
                "correlation_id": "",
                "metadata_json": "{}",
            }, ensure_ascii=False),
            json.dumps({
                "message_id": "status-report",
                "sender_id": "system",
                "sender_name": "系统",
                "room_id": "room-b7-ready",
                "text": "最终报告已写入",
                "seq": seq + 1,
                "timestamp_ms": seq + 1,
                "sender_type": "system",
                "message_kind": "runtime_status",
                "correlation_id": "",
                "metadata_json": "{}",
            }, ensure_ascii=False),
        ])
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "fixture_corona.log"
            history_path = Path(directory) / "fixture_history.jsonl"
            log_path.write_text("\n".join(log_lines), encoding="utf-8")
            history_path.write_text("\n".join(history), encoding="utf-8")

            checks, _ = run_control_plane(log_path, history_path)

        self.assertEqual(
            summarize(checks, profile="control-plane"),
            f"B7_1_CONTROL_READY: PASS={len(checks)} WARN=0 FAIL=0",
        )

    def test_b7_2_profile_requires_exact_real_media_lineage_and_engine_actor(self) -> None:
        trace = {
            "phase": "actor_import_ready",
            "plan_id": "plan-media-1",
            "batch_id": "batch-media-1",
            "asset_id": "key",
            "image_mode": "text_to_image",
            "image_ref": "image-resource-1",
            "image_hash": "sha256:image",
            "image_source": "image_resource",
            "model_mode": "image_to_3d",
            "source_image_ref": "image-resource-1",
            "source_image_hash": "sha256:image",
            "model_ref": "model-resource-1",
            "actor_id": "actor-key-1",
            "actor_source": "engine_actor_import",
            "actor_status": "bounds_ready",
        }
        runtime = (
            "[LANChatRuntimeEvidence] phase=runtime_queue_drain_result room=room-media "
            "runtime_plan=plan-media-1 engine_imports=1 resources=image:1/0,model:1/0"
        )
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "fixture_corona.log"
            log_path.write_text(
                "\n".join((
                    f"[R3MediaLineageTrace] {json.dumps(trace, ensure_ascii=False, separators=(',', ':'))}",
                    runtime,
                )),
                encoding="utf-8",
            )

            checks, metadata = run_scene_runtime(log_path)

        self.assertEqual(metadata["profile"], "scene-runtime")
        self.assertEqual(
            summarize(checks, profile="scene-runtime"),
            f"B7_2_SCENE_READY: PASS={len(checks)} WARN=0 FAIL=0",
        )

    def test_b7_2_profile_rejects_mock_or_text_to_3d_fallback(self) -> None:
        trace = {
            "phase": "actor_import_ready",
            "plan_id": "plan-media-1",
            "batch_id": "batch-media-1",
            "asset_id": "key",
            "image_mode": "mock_reference",
            "image_ref": "mock-image",
            "image_hash": "sha256:mock",
            "image_source": "mock_reference",
            "model_mode": "text_to_3d",
            "source_image_ref": "",
            "source_image_hash": "",
            "model_ref": "model-resource-1",
            "actor_id": "actor-key-1",
            "actor_source": "runtime_default_import",
            "actor_status": "ready",
        }
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "fixture_corona.log"
            log_path.write_text(
                f"[R3MediaLineageTrace] {json.dumps(trace, separators=(',', ':'))}\n"
                "generation_mode=text_to_3d mock_reference",
                encoding="utf-8",
            )

            checks, _ = run_scene_runtime(log_path)

        by_name = {check.name: check for check in checks}
        self.assertEqual(by_name["b7.2-real-text-to-image"].level, "FAIL")
        self.assertEqual(by_name["b7.2-strict-image-to-model"].level, "FAIL")
        self.assertEqual(by_name["b7.2-engine-actor-import"].level, "FAIL")
        self.assertEqual(by_name["b7.2-no-media-fallback"].level, "FAIL")

    def test_b7_2_profile_reports_specific_image_failure_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "fixture_corona.log"
            log_path.write_text(
                "[LANChatRuntimeEvidence] phase=runtime_queue_drain_result "
                "image_failures={'image_resource_timeout':1} engine_imports=0",
                encoding="utf-8",
            )

            checks, metadata = run_scene_runtime(log_path)

        by_name = {check.name: check for check in checks}
        self.assertIn(
            "image_resource_timeout",
            by_name["b7.2-media-lineage-evidence"].detail,
        )
        self.assertEqual(metadata["image_failure_codes"], ["image_resource_timeout"])

    def test_model_call_summary_exposes_explicit_zero_call_budget(self) -> None:
        history_line = (
            '{"message_id":"message-1","sender_id":"host","sender_name":"房主",'
            '"room_id":"room-1","text":"@GM 确认生成","seq":1,"timestamp_ms":1,'
            '"sender_type":"user","message_kind":"chat","correlation_id":"message-1",'
            '"metadata_json":"{\\"target_agent_id\\":\\"gm\\",\\"target_agent_name\\":\\"GM\\"}"}'
        )
        reply_line = (
            '{"message_id":"reply-1","sender_id":"gm","sender_name":"GM",'
            '"room_id":"room-1","text":"plan-demo-001 artifact-plan-001",'
            '"seq":2,"timestamp_ms":2,"sender_type":"agent","message_kind":"agent_reply",'
            '"correlation_id":"message-1","metadata_json":"{\\"reply_to\\":\\"message-1\\"}"}'
        )
        log_line = (
            "[LANChatModelCallSummary] message_id=message-1 correlation=message-1 "
            "room=room-1 calls=0 purposes="
        )
        process_line = "[LANChatAgentTrace] phase=process_start message_id=message-1 room=room-1"
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "fixture_corona.log"
            history_path = Path(directory) / "fixture_history.jsonl"
            log_path.write_text("\n".join((process_line, log_line)), encoding="utf-8")
            history_path.write_text("\n".join((history_line, reply_line)), encoding="utf-8")

            _, metadata = run_control_plane(log_path, history_path)

        turn = metadata["control_plane"]["turns"][0]
        self.assertEqual(turn["model_call_count"], 0)
        self.assertEqual(turn["model_call_observability"], "explicit")

    def test_control_probe_rejects_runtime_mutation_and_late_model_result(self) -> None:
        history = [
            {
                "message_id": "message-control-only",
                "sender_id": "host",
                "sender_name": "host",
                "room_id": "room-control-only",
                "text": "@GM status",
                "seq": 1,
                "timestamp_ms": 1,
                "sender_type": "user",
                "message_kind": "chat",
                "correlation_id": "message-control-only",
                "metadata_json": json.dumps({"target_agent_id": "gm", "target_agent_name": "GM"}),
            },
            {
                "message_id": "reply-control-only",
                "sender_id": "gm",
                "sender_name": "GM",
                "room_id": "room-control-only",
                "text": "status reply",
                "seq": 2,
                "timestamp_ms": 2,
                "sender_type": "agent",
                "message_kind": "agent_reply",
                "correlation_id": "message-control-only",
                "metadata_json": json.dumps({
                    "reply_to": "message-control-only",
                    "reply_contract": "discussion_reply",
                    "resolved_intent": "status_query",
                }),
            },
        ]
        log_lines = (
            "[Python] Quasar.ai_service.entrance initialized",
            "[LANChatDispatchLedger] phase=execution_claimed owner=native_queue route=gm_control "
            "room=room-control-only message_id=message-control-only",
            "[LANChatModelCallSummary] message_id=message-control-only correlation=message-control-only "
            "room=room-control-only calls=1 purposes=program_artifact_reasoning",
            "[LANChatModelCallResult] message_id=message-control-only correlation=message-control-only "
            "room=room-control-only purpose=program_artifact_reasoning elapsed_ms=90001 "
            "result=failed error_code=collaboration_stage_timeout",
            "[LANChatRuntimeTrace] phase=agent_reply_context_recorded "
            "message_id=message-control-only room=room-control-only",
            "[LANChatModelCallLateResult] message_id=message-control-only "
            "room=room-control-only purpose=program_artifact_reasoning stage_token=late-1 result=discarded",
        )
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "fixture_corona.log"
            history_path = Path(directory) / "fixture_history.jsonl"
            log_path.write_text("\n".join(log_lines), encoding="utf-8")
            history_path.write_text(
                "\n".join(json.dumps(item, ensure_ascii=False) for item in history),
                encoding="utf-8",
            )
            checks, metadata = run_control_plane(log_path, history_path)

        by_name = {check.name: check for check in checks}
        self.assertEqual(by_name["control-collaboration-runtime-zero-mutation"].level, "FAIL")
        self.assertEqual(by_name["control-collaboration-late-model-result"].level, "FAIL")
        self.assertIn(
            "control_plane_runtime_mutation",
            metadata["control_plane"]["turns"][0]["diagnostics"],
        )


if __name__ == "__main__":
    unittest.main()
