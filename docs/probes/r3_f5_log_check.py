"""Read-only R3 evidence probe for Corona F5 logs.

Usage:
    python docs/probes/r3_f5_log_check.py [path/to/*_corona.log]
    python docs/probes/r3_f5_log_check.py --json [path/to/*_corona.log]

The probe consumes structured ``R3GateTrace`` and ``LANChatRuntimeEvidence``
lines. It never imports AgentRuntime and never mutates Runtime or Engine state.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_DIR = REPO_ROOT / "build" / "examples" / "engine" / "RelWithDebInfo" / "logs"

R3_DIMENSIONS = (
    "snapshot_integrity",
    "environment_readiness",
    "entity_readiness",
    "finalizer_completeness",
    "business_graph_consistency",
    "multiplayer_consistency",
    "runtime_write_safety",
)
KEY_VALUE_RE = re.compile(r"(?P<key>[a-zA-Z_]+)=(?P<value>[^\s]+)")
BATCH_RE = re.compile(r"batches=total:(\d+),active:(\d+),terminal:(\d+)")
GRAPH_RE = re.compile(r"graphs=business:(\d+),internal:(\d+),active:(\d+),terminal:(\d+)")
DRAIN_RE = re.compile(r"drain=status:([^,\s]+),drained:(\d+)")
RATIO_RE = re.compile(r"^(\d+)/(\d+)$")


@dataclass(frozen=True)
class Check:
    level: str
    name: str
    detail: str


@dataclass(frozen=True)
class RuntimeEvidence:
    plan_id: str
    batch_total: int
    batch_active: int
    batch_terminal: int
    business_graphs: int
    internal_graphs: int
    graph_active: int
    graph_terminal: int
    drain_status: str
    drained_count: int

    @property
    def terminal(self) -> bool:
        return (
            self.batch_total > 0
            and self.batch_active == 0
            and self.batch_terminal == self.batch_total
            and self.graph_active == 0
            and self.graph_terminal == self.business_graphs
        )


def _latest_log() -> Path:
    candidates = sorted(DEFAULT_LOG_DIR.glob("*_corona.log"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"no *_corona.log found under {DEFAULT_LOG_DIR}")
    return candidates[-1]


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def _fields(line: str) -> dict[str, str]:
    return {match.group("key"): match.group("value") for match in KEY_VALUE_RE.finditer(line)}


def _parse_dimensions(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in str(raw or "").split(","):
        name, separator, status = item.partition(":")
        if separator and name in R3_DIMENSIONS and status in {"red", "yellow", "green"}:
            result[name] = status
    return result


def _parse_ratio(raw: str) -> tuple[int, int]:
    match = RATIO_RE.match(str(raw or ""))
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def _runtime_evidence(line: str) -> RuntimeEvidence | None:
    if "[LANChatRuntimeEvidence]" not in line or "phase=runtime_queue_drain_result" not in line:
        return None
    batches = BATCH_RE.search(line)
    graphs = GRAPH_RE.search(line)
    drain = DRAIN_RE.search(line)
    if not batches or not graphs:
        return None
    fields = _fields(line)
    return RuntimeEvidence(
        plan_id=fields.get("runtime_plan", ""),
        batch_total=int(batches.group(1)),
        batch_active=int(batches.group(2)),
        batch_terminal=int(batches.group(3)),
        business_graphs=int(graphs.group(1)),
        internal_graphs=int(graphs.group(2)),
        graph_active=int(graphs.group(3)),
        graph_terminal=int(graphs.group(4)),
        drain_status=drain.group(1) if drain else "",
        drained_count=int(drain.group(2)) if drain else 0,
    )


def _dimension_checks(fields: dict[str, str]) -> list[Check]:
    dimensions = _parse_dimensions(fields.get("dimensions", ""))
    checks: list[Check] = []
    for name in R3_DIMENSIONS:
        status = dimensions.get(name)
        if not status:
            checks.append(Check("FAIL", name, "dimension missing from latest R3GateTrace"))
        elif status == "green":
            checks.append(Check("PASS", name, "green"))
        elif status == "yellow":
            checks.append(Check("WARN", name, "yellow"))
        else:
            checks.append(Check("FAIL", name, "red"))
    return checks


def _business_graph_check(evidence: list[RuntimeEvidence]) -> Check:
    if not evidence:
        return Check("FAIL", "business-graph-evidence", "no runtime queue-drain evidence")
    latest = evidence[-1]
    if latest.batch_total != latest.business_graphs:
        return Check(
            "FAIL",
            "business-graph-evidence",
            f"business batches={latest.batch_total}, business graphs={latest.business_graphs}",
        )
    if latest.batch_terminal != latest.graph_terminal:
        return Check(
            "FAIL",
            "business-graph-evidence",
            f"terminal batches={latest.batch_terminal}, terminal graphs={latest.graph_terminal}",
        )
    return Check(
        "PASS",
        "business-graph-evidence",
        f"business batches/graphs={latest.batch_total}/{latest.business_graphs}, "
        f"terminal={latest.batch_terminal}/{latest.graph_terminal}",
    )


def _internal_graph_growth_check(evidence: list[RuntimeEvidence], lines: Iterable[str]) -> Check:
    terminal = [item for item in evidence if item.terminal]
    if len(terminal) < 2:
        return Check("WARN", "terminal-internal-graph-growth", "fewer than two terminal drain samples")
    growth = terminal[-1].internal_graphs - terminal[0].internal_graphs
    exhausted = sum("runtime_finalizer_retry_exhausted" in line for line in lines)
    if growth > 25:
        return Check(
            "FAIL",
            "terminal-internal-graph-growth",
            f"internal graphs grew by {growth} after business terminal; retry_exhausted={exhausted}",
        )
    return Check(
        "PASS",
        "terminal-internal-graph-growth",
        f"internal graph growth after terminal={growth}; retry_exhausted={exhausted}",
    )


def _render_check(fields: dict[str, str]) -> Check:
    ready, total = _parse_ratio(fields.get("render", ""))
    observed, observed_total = _parse_ratio(fields.get("render_observed", ""))
    denominator = max(total, observed_total)
    if denominator <= 0:
        return Check("WARN", "render-readiness", "latest R3GateTrace has no render denominator")
    if observed == observed_total and ready == total:
        return Check("PASS", "render-readiness", f"ready={ready}/{total}, observed={observed}/{observed_total}")
    if observed == 0:
        return Check("FAIL", "render-readiness", f"ready={ready}/{total}, observed={observed}/{observed_total}")
    return Check("WARN", "render-readiness", f"ready={ready}/{total}, observed={observed}/{observed_total}")


def run(path: Path) -> tuple[list[Check], dict[str, object]]:
    lines = _read_lines(path)
    gate_lines = [line for line in lines if "[R3GateTrace]" in line]
    evidence = [item for line in lines if (item := _runtime_evidence(line)) is not None]
    if not gate_lines:
        checks = [Check("FAIL", "r3-gate-trace", "no R3GateTrace found")]
        return checks, {"log": str(path), "gate_trace_count": 0, "runtime_evidence_count": len(evidence)}

    latest_fields = _fields(gate_lines[-1])
    overall = latest_fields.get("overall", "")
    overall_level = {"green": "PASS", "yellow": "WARN", "red": "FAIL"}.get(overall, "FAIL")
    checks = [Check(overall_level, "r3-gate-trace", f"overall={overall or 'missing'}")]
    checks.extend(_dimension_checks(latest_fields))
    checks.append(_business_graph_check(evidence))
    checks.append(_internal_graph_growth_check(evidence, lines))
    checks.append(_render_check(latest_fields))
    latest_evidence = asdict(evidence[-1]) if evidence else {}
    metadata = {
        "log": str(path),
        "gate_trace_count": len(gate_lines),
        "runtime_evidence_count": len(evidence),
        "plan_id": latest_fields.get("plan", ""),
        "scene_version": int(latest_fields.get("scene_version", "0") or 0),
        "overall": overall,
        "game_ready": latest_fields.get("game_ready", ""),
        "render": latest_fields.get("render", ""),
        "render_observed": latest_fields.get("render_observed", ""),
        "latest_runtime_evidence": latest_evidence,
    }
    return checks, metadata


def summarize(checks: list[Check]) -> str:
    counts = Counter(check.level for check in checks)
    status = "R3_F5_BLOCKED" if counts["FAIL"] else "R3_F5_WARN" if counts["WARN"] else "R3_F5_READY"
    return f"{status}: PASS={counts['PASS']} WARN={counts['WARN']} FAIL={counts['FAIL']}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", nargs="?", type=Path, help="Path to *_corona.log; defaults to latest")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report")
    args = parser.parse_args(argv)
    path = args.log or _latest_log()
    if not path.exists():
        print(f"[FAIL] log not found: {path}", file=sys.stderr)
        return 2
    checks, metadata = run(path)
    if args.json:
        print(json.dumps({"metadata": metadata, "checks": [asdict(item) for item in checks], "summary": summarize(checks)}, ensure_ascii=False, indent=2))
    else:
        print(f"[INFO] log={path}")
        for check in checks:
            print(f"[{check.level}] {check.name}: {check.detail}")
        print(f"[SUMMARY] {summarize(checks)}")
    return 1 if any(check.level == "FAIL" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
