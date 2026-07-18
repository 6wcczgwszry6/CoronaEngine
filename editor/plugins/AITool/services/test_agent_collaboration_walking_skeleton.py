from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import unittest

import editor.plugins.AITool.services.agent_collaboration.walking_skeleton as walking_skeleton_module
from editor.plugins.AITool.services._test_import_guard import assert_module_has_no_forbidden_imports
from editor.plugins.AITool.services.agent_collaboration import (
    ArtifactEnvelope,
    GameDesignBrief,
    NonExecutableArtifactError,
    assert_executable,
)
from editor.plugins.AITool.services.agent_collaboration.walking_skeleton import (
    SKELETON_NODE_ORDER,
    DemoScenarioRunner,
    UnavailableEngineCapabilityPort,
    build_skeleton_manifest,
    default_user_command_fixture,
)


class WalkingSkeletonTests(unittest.TestCase):
    @staticmethod
    def _runner() -> DemoScenarioRunner:
        return DemoScenarioRunner(
            engine_capabilities=UnavailableEngineCapabilityPort(),
            clock=lambda: datetime(2026, 7, 18, tzinfo=timezone.utc),
        )

    def test_fixture_runs_complete_non_executable_five_artifact_skeleton(self) -> None:
        result = self._runner().run(default_user_command_fixture())

        self.assertFalse(result.preflight.executable)
        self.assertEqual(result.preflight.status, "completed")
        self.assertTrue(all(check.status == "passed" for check in result.preflight.checks))
        self.assertEqual(len(result.demo_result.artifact_refs), 5)
        self.assertFalse(result.demo_result.executable)
        self.assertEqual(result.demo_result.status, "pending_runtime_verification")
        self.assertEqual(result.progress_event.status, "pending_runtime_verification")
        self.assertEqual(result.demo_result.blocked_results, result.progress_event.blocked_results)

    def test_baseline_node_order_status_and_engine_diagnostics_are_exact(self) -> None:
        result = self._runner().run(default_user_command_fixture())
        nodes = result.demo_result.skeleton_report.nodes

        self.assertEqual(tuple(node.node_id for node in nodes), SKELETON_NODE_ORDER)
        expected_status = {
            node_id: "pending_runtime_verification" if node_id == "engine_capability_port" else "completed"
            for node_id in SKELETON_NODE_ORDER
        }
        self.assertEqual({node.node_id: node.status for node in nodes}, expected_status)
        engine = next(node for node in nodes if node.node_id == "engine_capability_port")
        self.assertEqual(engine.blocker_code, "engine_capability_manifest_unavailable")
        self.assertEqual(engine.owner_domain, "engine")
        blocked = result.demo_result.blocked_results[0]
        self.assertEqual(blocked.owner_domain, "engine")
        self.assertEqual(blocked.missing_requirements[0].requirement_id, "engine.capability_manifest")
        self.assertTrue(blocked.next_action)

    def test_same_fixture_and_clock_produce_same_manifest_report_and_hash(self) -> None:
        first = self._runner().run(default_user_command_fixture())
        second = self._runner().run(default_user_command_fixture())

        self.assertEqual(first.manifest, second.manifest)
        self.assertEqual(first.manifest.contract_hash(), second.manifest.contract_hash())
        self.assertEqual(first.demo_result.skeleton_report, second.demo_result.skeleton_report)
        self.assertEqual(first.demo_result, second.demo_result)

    def test_contract_manifest_contains_fixed_nodes_edges_and_versions(self) -> None:
        manifest = build_skeleton_manifest()
        self.assertEqual(tuple(node_id for node_id, _ in manifest.skeleton_nodes), SKELETON_NODE_ORDER)
        self.assertEqual(
            manifest.skeleton_edges,
            tuple(zip(SKELETON_NODE_ORDER, SKELETON_NODE_ORDER[1:])),
        )
        self.assertTrue(manifest.contract_hash().startswith("sha256:"))
        self.assertEqual(len(dict(manifest.schema_versions)), 6)

    def test_collaboration_skeleton_has_no_runtime_frontend_or_cpp_import(self) -> None:
        assert_module_has_no_forbidden_imports(
            self,
            walking_skeleton_module,
            (
                "editor.plugins.AITool.services.agent_runtime",
                "editor.plugins.AITool.services.lanchat",
                "editor.plugins.AITool.services.schema_versions",
                "editor.Frontend",
                "src.systems",
            ),
        )
        source = Path(walking_skeleton_module.__file__).read_text(encoding="utf-8")
        for forbidden_symbol in (
            "ActionProposal",
            "EntityBindingPlan",
            "PlanPatch",
            "ToolCallGraph",
            "RuntimeCppBridge",
            "EngineWriteGate",
        ):
            self.assertNotIn(forbidden_symbol, source)

    def test_fixture_artifacts_cannot_cross_execution_boundary(self) -> None:
        result = self._runner().run(default_user_command_fixture())
        self.assertFalse(result.demo_result.executable)
        mock_artifact = ArtifactEnvelope(
            artifact_id="planning.mock-brief",
            artifact_type="GameDesignBrief",
            version=1,
            producer_role="planning",
            source_task_id="task.mock-planning",
            base_project_version=1,
            base_world_version=1,
            snapshot_source="mock",
            non_executable=True,
            status="validated",
            payload=GameDesignBrief(
                project_goal="Mock goal",
                player_experience=("inspect",),
                core_rules=("do not execute",),
                acceptance_criteria=("mock stays blocked",),
            ),
        )
        with self.assertRaises(NonExecutableArtifactError):
            assert_executable(mock_artifact)


if __name__ == "__main__":
    unittest.main()
