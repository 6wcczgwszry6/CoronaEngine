from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from docs.probes.r3_f5_log_check import run, summarize


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


if __name__ == "__main__":
    unittest.main()
