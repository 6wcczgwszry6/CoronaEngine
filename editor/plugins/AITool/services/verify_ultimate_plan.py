"""Run the current non-native verification suite for the Agent-native plan.

This runner intentionally avoids C++/Ninja/CEF/F5/native build steps. It is the
repeatable gate for the Python, protocol, and static checks that can be
validated in this workstream. Keep this list aligned with files that exist in
the current Agent-native branch; missing listed files are treated as failures.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import tokenize
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
PYCACHE_PREFIX = REPO_ROOT / ".tmp" / "ultimate_plan_pycache"


PYTHON_TESTS = [
    "editor/plugins/AITool/services/test_agent_runtime_phase1.py",
    "editor/plugins/AITool/services/test_lanchat_runtime_guard.py",
    "docs/probes/test_v3_f5_log_check.py",
    "docs/probes/test_v3_f5_quick_gate.py",
]

NODE_TESTS: list[str] = []

PY_COMPILE_TARGETS = [
    "editor/plugins/AITool/services/agent_runtime/__init__.py",
    "editor/plugins/AITool/services/agent_runtime/adapters.py",
    "editor/plugins/AITool/services/agent_runtime/core.py",
    "editor/plugins/AITool/services/agent_runtime/flags.py",
    "editor/plugins/AITool/services/agent_runtime/tools.py",
    "editor/plugins/AITool/services/generation_composer_adapter.py",
    "editor/plugins/AITool/services/generation_scheduler.py",
    "editor/plugins/AITool/services/interaction_coordinator.py",
    "editor/plugins/AITool/services/intent_understanding.py",
    "editor/plugins/AITool/services/lanchat_agent_worker.py",
    "editor/plugins/AITool/services/lanchat_host_action_executor.py",
    "editor/plugins/AITool/services/lanchat_scene_runtime.py",
    "editor/plugins/AITool/services/seed_plan.py",
    "editor/plugins/AITool/services/workflow_command_policy.py",
    "editor/plugins/AITool/services/test_agent_runtime_phase1.py",
    "editor/plugins/AITool/services/test_lanchat_runtime_guard.py",
    "editor/plugins/AITool/cai_extensions/register.py",
    "editor/plugins/AITool/cai_extensions/agent/agent_adapter.py",
    "editor/plugins/AITool/cai_extensions/agent/engine_write_gate.py",
    "editor/plugins/AITool/cai_extensions/agent/scene_composer_progressive.py",
    "editor/plugins/AITool/cai_extensions/agent/scene_element_classifier.py",
    "docs/probes/v3_f5_log_check.py",
    "docs/probes/v3_f5_quick_gate.py",
]

DIRECT_SCENE_COMPOSE_SCAN_ROOTS = [
    "editor/plugins/AITool/services",
    "editor/plugins/AITool/cai_extensions/agent",
    "editor/plugins/AITool/main.py",
]

DIRECT_SCENE_COMPOSE_ALLOWED_FILES = {
    "editor/plugins/AITool/main.py",
    "editor/plugins/AITool/cai_extensions/agent/agent_adapter.py",
    "editor/plugins/AITool/services/generation_composer_adapter.py",
}

DIRECT_SCENE_COMPOSE_GUARDS = {
    "editor/plugins/AITool/cai_extensions/agent/agent_adapter.py": (
        "_legacy_main_workflow_allowed",
        "AGENT_RUNTIME_REQUIRED_MESSAGE",
    ),
    "editor/plugins/AITool/services/generation_composer_adapter.py": (
        "can_call_legacy_main_workflow",
        "legacy SceneComposer main workflow is disabled",
    ),
}

DIRECT_SCENE_COMPOSE_ALLOWED_LINE_PATTERNS = {
    "editor/plugins/AITool/main.py": (
        'return SceneComposer(scene_name="Scene/default.scene")',
    ),
    "editor/plugins/AITool/cai_extensions/agent/agent_adapter.py": (
        "composer = SceneComposer(",
        "result = composer.compose(",
    ),
    "editor/plugins/AITool/services/generation_composer_adapter.py": (
        "SceneComposer.compose().",
        "result = composer.compose(",
    ),
}

DIRECT_SCENE_COMPOSE_GUARDED_CALLS = {
    "editor/plugins/AITool/cai_extensions/agent/agent_adapter.py": [
        ("def _handle_scene_compose(", "composer = SceneComposer("),
        ("def _handle_scene_compose(", "result = composer.compose("),
    ],
    "editor/plugins/AITool/services/generation_composer_adapter.py": [
        ("def compose(", "result = composer.compose("),
    ],
}

DIRECT_ENGINE_WRITE_SCAN_ROOTS = [
    "editor/plugins/AITool/cai_extensions/agent/agent_adapter.py",
]

DIRECT_ENGINE_WRITE_GUARDED_CALLS = {
    "editor/plugins/AITool/cai_extensions/agent/agent_adapter.py": [
        ("def _handle_direct_import(", 'get_tool("import_model")'),
        ("def _handle_edit(", "scene_manager.get"),
    ],
}

DIRECT_PROGRESSIVE_WORKFLOW_SCAN_ROOTS = [
    "editor/plugins/AITool/services",
    "editor/plugins/AITool/cai_extensions/agent",
    "editor/plugins/AITool/main.py",
]

DIRECT_GENERATION_SCHEDULER_SCAN_ROOTS = [
    "editor/plugins/AITool/services",
    "editor/plugins/AITool/cai_extensions/agent",
    "editor/plugins/AITool/main.py",
]

DIRECT_HOST_ACTION_EXECUTOR_SCAN_ROOTS = [
    "editor/plugins/AITool/services",
    "editor/plugins/AITool/cai_extensions/agent",
    "editor/plugins/AITool/main.py",
]

DIRECT_PROGRESSIVE_WORKFLOW_ALLOWED_FILES = {
    "editor/plugins/AITool/cai_extensions/agent/scene_composer.py",
    "editor/plugins/AITool/cai_extensions/agent/scene_composer_progressive.py",
    "editor/plugins/AITool/cai_extensions/agent/scene_session.py",
}

DIRECT_PROGRESSIVE_WORKFLOW_ALLOWED_LINE_PATTERNS = {
    "editor/plugins/AITool/cai_extensions/agent/scene_composer.py": (
        "from .scene_composer_progressive import run_progressive_workflow",
        "result = run_progressive_workflow(",
    ),
    "editor/plugins/AITool/cai_extensions/agent/scene_composer_progressive.py": (
        "本模块提供 `_run_progressive_workflow`",
        "def run_progressive_workflow(",
        "prog_result = session.progressive_compose(",
        '__all__ = ["run_progressive_workflow"]',
    ),
    "editor/plugins/AITool/cai_extensions/agent/scene_session.py": (
        "progressive_compose() 是主循环",
        "def progressive_compose(",
    ),
}

DIRECT_PROGRESSIVE_WORKFLOW_CONTAINED_CALLS = {
    "editor/plugins/AITool/cai_extensions/agent/scene_composer.py": [
        ("    def compose(", "from .scene_composer_progressive import run_progressive_workflow"),
        ("    def compose(", "result = run_progressive_workflow("),
    ],
    "editor/plugins/AITool/cai_extensions/agent/scene_composer_progressive.py": [
        ("def run_progressive_workflow(", "prog_result = session.progressive_compose("),
    ],
}

DIRECT_PROGRESSIVE_WORKFLOW_REQUIRED_SCOPE_TOKENS = {
    "editor/plugins/AITool/cai_extensions/agent/scene_composer_progressive.py": [
        (
            "def run_progressive_workflow(",
            (
                "from .engine_write_gate import get_engine_write_gate",
                "engine_gate = get_engine_write_gate()",
                "def importer(",
                "incremental_import(",
                "import_tool=import_tool,\n            scene_layout=scene_layout,\n            engine_gate=engine_gate",
                "session.progressive_compose(",
            ),
        ),
    ],
}

DIRECT_GENERATION_SCHEDULER_ALLOWED_FILES = {
    "editor/plugins/AITool/services/interaction_coordinator.py",
    "editor/plugins/AITool/services/lanchat_agent_worker.py",
}

DIRECT_GENERATION_SCHEDULER_ALLOWED_LINE_PATTERNS = {
    "editor/plugins/AITool/services/interaction_coordinator.py": (
        "submitted = self._scheduler.submit(payload)",
        "submitted = self._scheduler.submit(job_payload)",
    ),
    "editor/plugins/AITool/services/lanchat_agent_worker.py": (
        "self._generation_scheduler = GenerationScheduler(",
        "ref = coordinator.execute_confirmed_plan(plan.plan_id)",
    ),
}

DIRECT_GENERATION_SCHEDULER_CONTAINED_CALLS = {
    "editor/plugins/AITool/services/interaction_coordinator.py": [
        ("    def execute_confirmed_plan(", "submitted = self._scheduler.submit(payload)"),
        ("    def execute_post_generation_add(", "submitted = self._scheduler.submit(job_payload)"),
    ],
    "editor/plugins/AITool/services/lanchat_agent_worker.py": [
        ("    def _start_active_coordinator_generation(", "ref = coordinator.execute_confirmed_plan(plan.plan_id)"),
    ],
}

DIRECT_GENERATION_SCHEDULER_REQUIRED_SCOPE_TOKENS = {
    "editor/plugins/AITool/services/lanchat_agent_worker.py": [
        (
            "    def _get_generation_scheduler(",
            (
                "can_call_legacy_main_workflow()",
                "from .generation_scheduler import GenerationScheduler",
                "self._generation_scheduler = GenerationScheduler(",
                "self._install_generation_scheduler_hooks(self._generation_scheduler)",
            ),
        ),
        (
            "    def _start_active_coordinator_generation(",
            (
                "if not self._agent_runtime_flags.can_call_legacy_main_workflow():",
                "return self._execute_confirmed_plan_via_agent_runtime(",
                "ref = coordinator.execute_confirmed_plan(plan.plan_id)",
            ),
        ),
    ],
}

DIRECT_HOST_ACTION_EXECUTOR_ALLOWED_FILES = {
    "editor/plugins/AITool/services/lanchat_agent_worker.py",
}

DIRECT_HOST_ACTION_EXECUTOR_ALLOWED_LINE_PATTERNS = {
    "editor/plugins/AITool/services/lanchat_agent_worker.py": (
        "self._execute_confirmed_action(payload)",
        "executor.enqueue_and_process(payload)",
    ),
}

DIRECT_HOST_ACTION_EXECUTOR_REQUIRED_SCOPE_TOKENS = {
    "editor/plugins/AITool/services/lanchat_agent_worker.py": [
        (
            "    def _broadcast_confirmed_action(",
            (
                "def _broadcast_confirmed_action(",
                "if not self._is_confirmed_action_payload_runtime_approved(payload):",
                "self._record_unapproved_confirmed_action_block(payload, phase=\"broadcast\")",
                "Blocked unapproved confirmed action payload",
                "self._execute_confirmed_action(payload)",
            ),
        ),
        (
            "    def _broadcast_confirmed_action(",
            (
                "if not self._is_confirmed_action_payload_runtime_approved(payload):",
                "return\n        if hasattr(self._corona_engine, \"network_broadcast_intent\"):",
                "self._execute_confirmed_action(payload)",
            ),
        ),
        (
            "    def _execute_confirmed_action(",
            (
                "def _execute_confirmed_action(",
                "executor = self._get_host_action_executor()",
                "executor.enqueue_and_process(payload)",
                "self._emit_generation_scheduler_disclosure()",
            ),
        ),
    ],
}

REQUIRED_DEPRECATED_WORKFLOW_COMMANDS = {
    "/scene_agent",
    "/sc_agent",
    "/scene_composition",
    "/scene_composition_v2",
    "/sc_v2",
    "/full_pipeline",
    "/pipeline",
    "/full_pipeline_v2",
    "/fp_v2",
    "/multi_scene",
    "/parallel_generate",
    "/parallel_generate_v2",
    "/pg_v2",
}

REQUIRED_INTERNAL_WORKFLOW_COMMANDS = {
    "/model_retrieval",
    "/terrain_generate",
    "/terrain",
}

WORKFLOW_COMMAND_SCAN_ROOTS = [
    "editor/plugins/AITool/cai_extensions/agent/__init__.py",
    "editor/plugins/AITool/cai_extensions/flows",
]

AGENT_RUNTIME_CORE = "editor/plugins/AITool/services/agent_runtime/core.py"
AGENT_RUNTIME_TOOLS = "editor/plugins/AITool/services/agent_runtime/tools.py"
AGENT_RUNTIME_FLAGS = "editor/plugins/AITool/services/agent_runtime/flags.py"
GENERATION_COMPOSER_ADAPTER = "editor/plugins/AITool/services/generation_composer_adapter.py"
LANCHAT_AGENT_WORKER = "editor/plugins/AITool/services/lanchat_agent_worker.py"
LANCHAT_HOST_ACTION_EXECUTOR = "editor/plugins/AITool/services/lanchat_host_action_executor.py"
AGENT_RUNTIME_PHASE1_TESTS = "editor/plugins/AITool/services/test_agent_runtime_phase1.py"
LANCHAT_RUNTIME_GUARD_TESTS = "editor/plugins/AITool/services/test_lanchat_runtime_guard.py"

REQUIRED_RUNTIME_VALIDATORS = {
    "ScenePlanValidator",
    "BatchPlanValidator",
    "PlanPatchValidator",
    "StatePatchValidator",
    "ToolCallValidator",
    "ToolResultValidator",
    "ToolCallGraphValidator",
    "AdjustmentProposalValidator",
    "ReviewAdvisoryProposalValidator",
    "ReportRecordValidator",
}

REQUIRED_STATE_PATCH_CONFLICT_TESTS = (
    "test_executor_preserves_explicit_state_patch_expected_version_conflict",
    "test_state_patch_conflict_is_visible_as_reconcile_fact_in_status_and_report",
    "test_state_patch_conflict_reconcile_action_records_decision_without_replaying_patch",
    "test_state_patch_conflict_does_not_emit_result_when_failed_state_persist_fails",
    "test_state_patch_validator_rejects_invalid_operations_schema",
    "test_state_patch_validator_protects_runtime_owned_control_slots",
)

REQUIRED_PHASE6_GEOMETRY_TOOL_TESTS = (
    "test_phase6_geometry_compute_aabb_tool_records_safe_actor_facts",
    "test_phase6_geometry_check_overlap_tool_records_safe_review_fact_without_actor_write",
)

ALLOWED_RUNTIME_STATE_APPLY_PATCH_FUNCTIONS = {
    "execute",
    "_emit_tool_started_runtime_event",
    "_emit_tool_result_runtime_event",
    "_emit_tool_blocked_runtime_event",
    "_emit_graph_stopped_runtime_event",
    "_persist_graph",
}


def _run(label: str, command: list[str]) -> bool:
    print(f"[RUN] {label}")
    env = os.environ.copy()
    if command and Path(command[0]).name.lower().startswith("python"):
        PYCACHE_PREFIX.mkdir(parents=True, exist_ok=True)
        env["PYTHONPYCACHEPREFIX"] = str(PYCACHE_PREFIX)
    completed = subprocess.run(command, cwd=REPO_ROOT, env=env)
    if completed.returncode == 0:
        print(f"[OK]  {label}")
        return True
    print(f"[FAIL] {label} (exit={completed.returncode})")
    return False


def _syntax_check(paths: list[str]) -> bool:
    print("[RUN] syntax compile current Agent-native modules")
    for path in paths:
        source_path = REPO_ROOT / path
        try:
            with tokenize.open(source_path) as handle:
                source = handle.read()
            compile(source, str(source_path), "exec")
        except Exception as exc:
            print(f"[FAIL] syntax compile current Agent-native modules: {path}: {exc}")
            return False
    print("[OK]  syntax compile current Agent-native modules")
    return True


def _to_repo_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _should_skip_direct_scene_compose_scan(path: Path) -> bool:
    parts = set(path.relative_to(REPO_ROOT).parts)
    if "Quasar" in parts or "__pycache__" in parts or ".tmp" in parts:
        return True
    if path.name == "verify_ultimate_plan.py":
        return True
    if "tests" in parts or path.name.startswith("test_"):
        return True
    if path.name == "scene_composer.py":
        return True
    return path.suffix != ".py"


def _iter_direct_scene_compose_scan_files() -> list[Path]:
    files: list[Path] = []
    for root in DIRECT_SCENE_COMPOSE_SCAN_ROOTS:
        root_path = REPO_ROOT / root
        if root_path.is_file():
            if not _should_skip_direct_scene_compose_scan(root_path):
                files.append(root_path)
            continue
        if root_path.is_dir():
            for path in root_path.rglob("*.py"):
                if not _should_skip_direct_scene_compose_scan(path):
                    files.append(path)
    return sorted(set(files))


def _direct_scene_compose_entry_gate() -> bool:
    print("[RUN] static direct SceneComposer entry gate")
    violations: list[str] = []
    for path in _iter_direct_scene_compose_scan_files():
        rel = _to_repo_path(path)
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = path.read_text(encoding="utf-8-sig")
        interesting_lines = []
        for lineno, line in enumerate(source.splitlines(), start=1):
            if "SceneComposer(" in line or "composer.compose(" in line:
                interesting_lines.append((lineno, line.strip()))
        if not interesting_lines:
            continue
        if rel not in DIRECT_SCENE_COMPOSE_ALLOWED_FILES:
            for lineno, line in interesting_lines:
                violations.append(f"{rel}:{lineno}: unexpected direct SceneComposer entry: {line}")
            continue
        allowed_patterns = DIRECT_SCENE_COMPOSE_ALLOWED_LINE_PATTERNS.get(rel, ())
        for lineno, line in interesting_lines:
            if not any(pattern in line for pattern in allowed_patterns):
                violations.append(f"{rel}:{lineno}: unexpected direct SceneComposer entry: {line}")
        guard_tokens = DIRECT_SCENE_COMPOSE_GUARDS.get(rel, ())
        if guard_tokens and not all(token in source for token in guard_tokens):
            violations.append(
                f"{rel}: allowed legacy SceneComposer entry is missing Runtime guard tokens: "
                + ", ".join(guard_tokens)
            )
        for entry_marker, compose_marker in DIRECT_SCENE_COMPOSE_GUARDED_CALLS.get(rel, []):
            try:
                entry_index = source.index(entry_marker)
            except ValueError:
                violations.append(f"{rel}: missing guarded SceneComposer entry marker {entry_marker!r}")
                continue
            try:
                compose_index = source.index(compose_marker, entry_index)
            except ValueError:
                violations.append(f"{rel}: missing SceneComposer call marker {compose_marker!r}")
                continue
            guarded_prefix = source[entry_index:compose_index]
            for token in guard_tokens:
                if token not in guarded_prefix:
                    violations.append(
                        f"{rel}: {entry_marker} reaches {compose_marker!r} without guard token {token!r}"
                    )
    if violations:
        print("[FAIL] static direct SceneComposer entry gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static direct SceneComposer entry gate")
    return True


def _direct_engine_write_entry_gate() -> bool:
    print("[RUN] static direct engine-write entry gate")
    violations: list[str] = []
    for rel in DIRECT_ENGINE_WRITE_SCAN_ROOTS:
        path = REPO_ROOT / rel
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = path.read_text(encoding="utf-8-sig")
        for entry_marker, write_marker in DIRECT_ENGINE_WRITE_GUARDED_CALLS.get(rel, []):
            try:
                entry_index = source.index(entry_marker)
            except ValueError:
                violations.append(f"{rel}: missing guarded entry marker {entry_marker!r}")
                continue
            try:
                write_index = source.index(write_marker, entry_index)
            except ValueError:
                violations.append(f"{rel}: missing direct write marker {write_marker!r}")
                continue
            guarded_prefix = source[entry_index:write_index]
            if "_legacy_main_workflow_allowed()" not in guarded_prefix:
                violations.append(f"{rel}: {entry_marker} reaches {write_marker!r} without legacy-main guard")
            if "AGENT_RUNTIME_REQUIRED_MESSAGE" not in guarded_prefix:
                violations.append(f"{rel}: {entry_marker} reaches {write_marker!r} without Runtime-required reply")
    if violations:
        print("[FAIL] static direct engine-write entry gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static direct engine-write entry gate")
    return True


def _should_skip_direct_progressive_workflow_scan(path: Path) -> bool:
    parts = set(path.relative_to(REPO_ROOT).parts)
    if "Quasar" in parts or "__pycache__" in parts or ".tmp" in parts:
        return True
    if path.name == "verify_ultimate_plan.py":
        return True
    if "tests" in parts or path.name.startswith("test_"):
        return True
    return path.suffix != ".py"


def _iter_direct_progressive_workflow_scan_files() -> list[Path]:
    files: list[Path] = []
    for root in DIRECT_PROGRESSIVE_WORKFLOW_SCAN_ROOTS:
        root_path = REPO_ROOT / root
        if root_path.is_file():
            if not _should_skip_direct_progressive_workflow_scan(root_path):
                files.append(root_path)
            continue
        if root_path.is_dir():
            for path in root_path.rglob("*.py"):
                if not _should_skip_direct_progressive_workflow_scan(path):
                    files.append(path)
    return sorted(set(files))


def _function_scope(source: str, entry_marker: str) -> tuple[str, list[str]]:
    try:
        entry_index = source.index(entry_marker)
    except ValueError:
        return "", [f"missing entry marker {entry_marker!r}"]
    line_start = source.rfind("\n", 0, entry_index) + 1
    entry_line = source[line_start:source.find("\n", line_start)]
    indent = len(entry_line) - len(entry_line.lstrip())
    sibling_marker = "\n" + (" " * indent) + "def "
    scope_end = source.find(sibling_marker, entry_index + len(entry_marker))
    if scope_end < 0:
        scope_end = len(source)
    return source[entry_index:scope_end], []


def _direct_progressive_workflow_entry_gate() -> bool:
    print("[RUN] static direct ProgressiveWorkflow entry gate")
    violations: list[str] = []
    markers = (
        "run_progressive_workflow",
        "progressive_compose(",
    )
    for path in _iter_direct_progressive_workflow_scan_files():
        rel = _to_repo_path(path)
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = path.read_text(encoding="utf-8-sig")
        interesting_lines = []
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith(("\"", "'")):
                continue
            if any(marker in stripped for marker in markers):
                interesting_lines.append((lineno, stripped))
        if not interesting_lines:
            continue
        for lineno, line in interesting_lines:
            allowed_patterns = DIRECT_PROGRESSIVE_WORKFLOW_ALLOWED_LINE_PATTERNS.get(rel, ())
            if rel in DIRECT_PROGRESSIVE_WORKFLOW_ALLOWED_FILES and any(
                pattern in line for pattern in allowed_patterns
            ):
                continue
            violations.append(f"{rel}:{lineno}: unexpected direct ProgressiveWorkflow entry: {line}")
        for entry_marker, workflow_marker in DIRECT_PROGRESSIVE_WORKFLOW_CONTAINED_CALLS.get(rel, []):
            scope, scope_errors = _function_scope(source, entry_marker)
            if scope_errors:
                violations.extend(f"{rel}: {item}" for item in scope_errors)
                continue
            try:
                workflow_index = scope.index(workflow_marker)
            except ValueError:
                violations.append(f"{rel}: missing ProgressiveWorkflow call marker {workflow_marker!r}")
                continue
            if workflow_index < 0:
                violations.append(f"{rel}: {workflow_marker!r} is not contained in expected entry {entry_marker!r}")
        for entry_marker, required_tokens in DIRECT_PROGRESSIVE_WORKFLOW_REQUIRED_SCOPE_TOKENS.get(rel, []):
            scope, scope_errors = _function_scope(source, entry_marker)
            if scope_errors:
                violations.extend(f"{rel}: {item}" for item in scope_errors)
                continue
            last_index = -1
            for token in required_tokens:
                token_index = scope.find(token)
                if token_index < 0:
                    violations.append(f"{rel}: {entry_marker} scope missing required token {token!r}")
                    continue
                if token_index < last_index:
                    violations.append(
                        f"{rel}: {entry_marker} scope has required token {token!r} out of execution order"
                    )
                last_index = token_index
    if violations:
        print("[FAIL] static direct ProgressiveWorkflow entry gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static direct ProgressiveWorkflow entry gate")
    return True


def _should_skip_direct_generation_scheduler_scan(path: Path) -> bool:
    parts = set(path.relative_to(REPO_ROOT).parts)
    if "Quasar" in parts or "__pycache__" in parts or ".tmp" in parts:
        return True
    if path.name in {"verify_ultimate_plan.py", "generation_scheduler.py"}:
        return True
    if "tests" in parts or path.name.startswith("test_"):
        return True
    return path.suffix != ".py"


def _iter_direct_generation_scheduler_scan_files() -> list[Path]:
    files: list[Path] = []
    for root in DIRECT_GENERATION_SCHEDULER_SCAN_ROOTS:
        root_path = REPO_ROOT / root
        if root_path.is_file():
            if not _should_skip_direct_generation_scheduler_scan(root_path):
                files.append(root_path)
            continue
        if root_path.is_dir():
            for path in root_path.rglob("*.py"):
                if not _should_skip_direct_generation_scheduler_scan(path):
                    files.append(path)
    return sorted(set(files))


def _direct_generation_scheduler_entry_gate() -> bool:
    print("[RUN] static direct GenerationScheduler entry gate")
    violations: list[str] = []
    markers = (
        "GenerationScheduler(",
        "_scheduler.submit(",
    )
    for path in _iter_direct_generation_scheduler_scan_files():
        rel = _to_repo_path(path)
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = path.read_text(encoding="utf-8-sig")
        interesting_lines = []
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith(("\"", "'")):
                continue
            if stripped.startswith("def "):
                continue
            if any(marker in stripped for marker in markers):
                interesting_lines.append((lineno, stripped))
        if not interesting_lines:
            continue
        allowed_patterns = DIRECT_GENERATION_SCHEDULER_ALLOWED_LINE_PATTERNS.get(rel, ())
        for lineno, line in interesting_lines:
            if rel in DIRECT_GENERATION_SCHEDULER_ALLOWED_FILES and any(
                pattern in line for pattern in allowed_patterns
            ):
                continue
            violations.append(f"{rel}:{lineno}: unexpected direct GenerationScheduler entry: {line}")
        for entry_marker, submit_marker in DIRECT_GENERATION_SCHEDULER_CONTAINED_CALLS.get(rel, []):
            scope, scope_errors = _function_scope(source, entry_marker)
            if scope_errors:
                violations.extend(f"{rel}: {item}" for item in scope_errors)
                continue
            if submit_marker not in scope:
                violations.append(
                    f"{rel}: {submit_marker!r} is not contained in expected entry {entry_marker!r}"
                )
        for entry_marker, required_tokens in DIRECT_GENERATION_SCHEDULER_REQUIRED_SCOPE_TOKENS.get(rel, []):
            scope, scope_errors = _function_scope(source, entry_marker)
            if scope_errors:
                violations.extend(f"{rel}: {item}" for item in scope_errors)
                continue
            last_index = -1
            for token in required_tokens:
                token_index = scope.find(token)
                if token_index < 0:
                    violations.append(f"{rel}: {entry_marker} scope missing required token {token!r}")
                    continue
                if token_index < last_index:
                    violations.append(
                        f"{rel}: {entry_marker} scope has required token {token!r} out of execution order"
                    )
                last_index = token_index
    if violations:
        print("[FAIL] static direct GenerationScheduler entry gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static direct GenerationScheduler entry gate")
    return True


def _should_skip_direct_host_action_executor_scan(path: Path) -> bool:
    parts = set(path.relative_to(REPO_ROOT).parts)
    if "Quasar" in parts or "__pycache__" in parts or ".tmp" in parts:
        return True
    if path.name in {"verify_ultimate_plan.py", "lanchat_host_action_executor.py"}:
        return True
    if "tests" in parts or path.name.startswith("test_"):
        return True
    return path.suffix != ".py"


def _iter_direct_host_action_executor_scan_files() -> list[Path]:
    files: list[Path] = []
    for root in DIRECT_HOST_ACTION_EXECUTOR_SCAN_ROOTS:
        root_path = REPO_ROOT / root
        if root_path.is_file():
            if not _should_skip_direct_host_action_executor_scan(root_path):
                files.append(root_path)
            continue
        if root_path.is_dir():
            for path in root_path.rglob("*.py"):
                if not _should_skip_direct_host_action_executor_scan(path):
                    files.append(path)
    return sorted(set(files))


def _direct_host_action_executor_entry_gate() -> bool:
    print("[RUN] static direct host action executor entry gate")
    violations: list[str] = []
    markers = (
        "_execute_confirmed_action(",
        "enqueue_and_process(",
    )
    for path in _iter_direct_host_action_executor_scan_files():
        rel = _to_repo_path(path)
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = path.read_text(encoding="utf-8-sig")
        interesting_lines = []
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith(("\"", "'")):
                continue
            if stripped.startswith("def "):
                continue
            if any(marker in stripped for marker in markers):
                interesting_lines.append((lineno, stripped))
        if not interesting_lines:
            continue
        allowed_patterns = DIRECT_HOST_ACTION_EXECUTOR_ALLOWED_LINE_PATTERNS.get(rel, ())
        for lineno, line in interesting_lines:
            if rel in DIRECT_HOST_ACTION_EXECUTOR_ALLOWED_FILES and any(
                pattern in line for pattern in allowed_patterns
            ):
                continue
            violations.append(f"{rel}:{lineno}: unexpected direct host action execution entry: {line}")
        for entry_marker, required_tokens in DIRECT_HOST_ACTION_EXECUTOR_REQUIRED_SCOPE_TOKENS.get(rel, []):
            scope, scope_errors = _function_scope(source, entry_marker)
            if scope_errors:
                violations.extend(f"{rel}: {item}" for item in scope_errors)
                continue
            last_index = -1
            for token in required_tokens:
                token_index = scope.find(token)
                if token_index < 0:
                    violations.append(f"{rel}: {entry_marker} scope missing required token {token!r}")
                    continue
                if token_index < last_index:
                    violations.append(
                        f"{rel}: {entry_marker} scope has required token {token!r} out of execution order"
                    )
                last_index = token_index
    if violations:
        print("[FAIL] static direct host action executor entry gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static direct host action executor entry gate")
    return True


def _host_action_executor_policy_gate() -> bool:
    print("[RUN] static host action executor policy gate")
    path = REPO_ROOT / LANCHAT_HOST_ACTION_EXECUTOR
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = path.read_text(encoding="utf-8-sig")
    violations: list[str] = []
    init_source = _function_source(source, "__init__")
    execute_payload = _function_source(source, "_execute_payload")
    structured_action = _function_source(source, "_is_structured_seed_plan_action")

    if not init_source:
        violations.append("LanChatHostActionExecutor.__init__ not found")
    else:
        for token in (
            "structured_action_handler: Callable[[dict[str, Any]], str] | None = None",
            "allow_legacy_agent_fallback: bool = False",
            "self._structured_action_handler = structured_action_handler",
            "self._allow_legacy_agent_fallback = bool(allow_legacy_agent_fallback)",
        ):
            if token not in init_source:
                violations.append(f"LanChatHostActionExecutor.__init__ missing policy token: {token}")

    if not execute_payload:
        violations.append("LanChatHostActionExecutor._execute_payload not found")
    else:
        required_order = (
            "if self._is_structured_seed_plan_payload(payload):",
            "if not self._is_structured_seed_plan_action(payload):",
            "if self._structured_action_handler is None:",
            "return str(self._structured_action_handler(dict(payload)))",
            "if not self._allow_legacy_agent_fallback:",
            "旧 Agent 执行回退已关闭",
            "agent = self._get_agent()",
        )
        last_index = -1
        for token in required_order:
            token_index = execute_payload.find(token)
            if token_index < 0:
                violations.append(f"LanChatHostActionExecutor._execute_payload missing policy token: {token}")
                continue
            if token_index < last_index:
                violations.append(
                    f"LanChatHostActionExecutor._execute_payload policy token out of order: {token}"
                )
            last_index = token_index

    if not structured_action:
        violations.append("LanChatHostActionExecutor._is_structured_seed_plan_action not found")
    else:
        for token in ('"start_generation"', '"execute_seed_plan"', '"post_generation_add"'):
            if token not in structured_action:
                violations.append(
                    f"LanChatHostActionExecutor._is_structured_seed_plan_action missing allowed action: {token}"
                )

    if violations:
        print("[FAIL] static host action executor policy gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static host action executor policy gate")
    return True


def _agent_runtime_flag_boundary_gate() -> bool:
    print("[RUN] static AgentRuntime flag boundary gate")
    flags_path = REPO_ROOT / AGENT_RUNTIME_FLAGS
    adapter_path = REPO_ROOT / GENERATION_COMPOSER_ADAPTER
    worker_path = REPO_ROOT / LANCHAT_AGENT_WORKER
    core_path = REPO_ROOT / AGENT_RUNTIME_CORE
    try:
        flags_source = flags_path.read_text(encoding="utf-8")
        adapter_source = adapter_path.read_text(encoding="utf-8")
        worker_source = worker_path.read_text(encoding="utf-8")
        core_source = core_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        flags_source = flags_path.read_text(encoding="utf-8-sig")
        adapter_source = adapter_path.read_text(encoding="utf-8-sig")
        worker_source = worker_path.read_text(encoding="utf-8-sig")
        core_source = core_path.read_text(encoding="utf-8-sig")

    violations: list[str] = []

    required_flag_defaults = (
        "agent_runtime_enabled: bool = True",
        "old_workflow_direct_entry_disabled: bool = True",
        "allow_legacy_function_adapter: bool = True",
        "allow_legacy_main_workflow: bool = False",
        "use_scene_snapshot_provider: bool = False",
        "use_scene_review_provider: bool = False",
        "use_image_resource_provider: bool = False",
        "use_model_resource_provider: bool = False",
        "use_legacy_model_resource_provider: bool = False",
        "use_environment_component_provider: bool = False",
        "use_engine_environment_import_provider: bool = False",
        "use_engine_actor_import_provider: bool = False",
        "use_engine_actor_delete_provider: bool = False",
        "use_engine_layout_transform_provider: bool = False",
        'agent_runtime_enabled=_env_bool(values, "AGENT_RUNTIME_ENABLED", True)',
        'old_workflow_direct_entry_disabled=_env_bool(values, "OLD_WORKFLOW_DIRECT_ENTRY_DISABLED", True)',
        'allow_legacy_function_adapter=_env_bool(values, "ALLOW_LEGACY_FUNCTION_ADAPTER", True)',
        'allow_legacy_main_workflow=_env_bool(values, "ALLOW_LEGACY_MAIN_WORKFLOW", False)',
        'use_scene_snapshot_provider=_env_bool(values, "AGENT_RUNTIME_USE_SCENE_SNAPSHOT_PROVIDER", False)',
        'use_scene_review_provider=_env_bool(values, "AGENT_RUNTIME_USE_SCENE_REVIEW_PROVIDER", False)',
        'use_image_resource_provider=_env_bool(values, "AGENT_RUNTIME_USE_IMAGE_PROVIDER", False)',
        'use_model_resource_provider=_env_bool(values, "AGENT_RUNTIME_USE_MODEL_PROVIDER", False)',
        'use_legacy_model_resource_provider=_env_bool(values, "AGENT_RUNTIME_USE_LEGACY_MODEL_PROVIDER", False)',
        'use_environment_component_provider=_env_bool(values, "AGENT_RUNTIME_USE_ENVIRONMENT_PROVIDER", False)',
        'use_engine_environment_import_provider=_env_bool(values, "AGENT_RUNTIME_USE_ENGINE_ENVIRONMENT_IMPORT_PROVIDER", False)',
        'use_engine_actor_import_provider=_env_bool(values, "AGENT_RUNTIME_USE_ENGINE_IMPORT_PROVIDER", False)',
        'use_engine_actor_delete_provider=_env_bool(values, "AGENT_RUNTIME_USE_ENGINE_DELETE_PROVIDER", False)',
        'use_engine_layout_transform_provider=_env_bool(values, "AGENT_RUNTIME_USE_ENGINE_TRANSFORM_PROVIDER", False)',
    )
    for token in required_flag_defaults:
        if token not in flags_source:
            violations.append(f"AgentRuntimeFlags missing required default/env token: {token}")

    can_call_legacy = _function_source(flags_source, "can_call_legacy_main_workflow")
    if not can_call_legacy:
        violations.append("AgentRuntimeFlags.can_call_legacy_main_workflow not found")
    else:
        for token in (
            "self.agent_runtime_enabled",
            "self.allow_legacy_main_workflow",
            "not self.old_workflow_direct_entry_disabled",
        ):
            if token not in can_call_legacy:
                violations.append(f"can_call_legacy_main_workflow missing hard boundary token: {token}")

    assert_blocked = _function_source(flags_source, "assert_legacy_main_workflow_blocked")
    if "if self.can_call_legacy_main_workflow():" not in assert_blocked:
        violations.append("AgentRuntimeFlags.assert_legacy_main_workflow_blocked must fail if legacy main workflow is enabled")

    for method_name, flag_name in (
        ("can_use_scene_snapshot_provider", "use_scene_snapshot_provider"),
        ("can_use_scene_review_provider", "use_scene_review_provider"),
        ("can_use_image_resource_provider", "use_image_resource_provider"),
        ("can_use_model_resource_provider", "use_model_resource_provider"),
        ("can_use_legacy_model_resource_provider", "use_legacy_model_resource_provider"),
        ("can_use_environment_component_provider", "use_environment_component_provider"),
        ("can_use_engine_environment_import_provider", "use_engine_environment_import_provider"),
        ("can_use_engine_actor_import_provider", "use_engine_actor_import_provider"),
        ("can_use_engine_actor_delete_provider", "use_engine_actor_delete_provider"),
        ("can_use_engine_layout_transform_provider", "use_engine_layout_transform_provider"),
    ):
        method_source = _function_source(flags_source, method_name)
        if not method_source:
            violations.append(f"AgentRuntimeFlags.{method_name} not found")
            continue
        for token in ("self.can_call_legacy_function_adapter()", f"self.{flag_name}"):
            if token not in method_source:
                violations.append(f"AgentRuntimeFlags.{method_name} missing provider boundary token: {token}")

    compose = _function_source(adapter_source, "compose")
    if not compose:
        violations.append("SceneComposerJobRunner.compose not found")
    else:
        required_order = (
            "if not self._agent_runtime_flags.can_call_legacy_main_workflow():",
            "legacy SceneComposer main workflow is disabled by AgentRuntimeFlags",
            "composer = self._composer_factory()",
            "result = composer.compose(",
        )
        last_index = -1
        for token in required_order:
            token_index = compose.find(token)
            if token_index < 0:
                violations.append(f"SceneComposerJobRunner.compose missing legacy-main boundary token: {token}")
                continue
            if token_index < last_index:
                violations.append(f"SceneComposerJobRunner.compose legacy-main boundary token out of order: {token}")
            last_index = token_index

    get_scheduler = _function_source(worker_source, "_get_generation_scheduler")
    if not get_scheduler:
        violations.append("LANChatAgentWorker._get_generation_scheduler not found")
    else:
        required_order = (
            "if not self._agent_runtime_flags.can_call_legacy_main_workflow():",
            "return None",
            "from .generation_scheduler import GenerationScheduler",
            "self._generation_scheduler = GenerationScheduler(",
            "self._install_generation_scheduler_hooks(self._generation_scheduler)",
        )
        last_index = -1
        for token in required_order:
            token_index = get_scheduler.find(token)
            if token_index < 0:
                violations.append(f"LANChatAgentWorker._get_generation_scheduler missing legacy-main boundary token: {token}")
                continue
            if token_index < last_index:
                violations.append(f"LANChatAgentWorker._get_generation_scheduler legacy-main boundary token out of order: {token}")
            last_index = token_index

    create_runtime = _function_source(worker_source, "_create_agent_runtime")
    if not create_runtime:
        violations.append("LANChatAgentWorker._create_agent_runtime not found")
    else:
        for guard_token, factory_token in (
            ("can_use_scene_snapshot_provider()", "make_scene_snapshot_provider"),
            ("can_use_image_resource_provider()", "make_image_resource_provider"),
            ("can_use_scene_review_provider()", "make_scene_review_provider"),
            ("can_use_environment_component_provider()", "make_environment_component_provider"),
            ("can_use_engine_environment_import_provider()", "make_engine_environment_component_import_provider"),
            ("can_use_model_resource_provider()", "make_model_resource_provider"),
            ("can_use_legacy_model_resource_provider()", "make_legacy_model_resource_provider"),
            ("can_use_engine_actor_import_provider()", "make_engine_actor_import_provider"),
            ("can_use_engine_actor_delete_provider()", "make_engine_actor_delete_provider"),
            ("can_use_engine_layout_transform_provider()", "make_engine_layout_transform_provider"),
        ):
            guard_index = create_runtime.find(guard_token)
            factory_index = create_runtime.find(factory_token)
            if factory_index < 0:
                violations.append(f"LANChatAgentWorker._create_agent_runtime missing provider factory token: {factory_token}")
                continue
            if guard_index < 0:
                violations.append(f"LANChatAgentWorker._create_agent_runtime missing provider guard token: {guard_token}")
                continue
            if guard_index > factory_index:
                violations.append(
                    "LANChatAgentWorker._create_agent_runtime provider factory appears before its flag guard: "
                    f"{factory_token}"
                )

    runtime_status_reply = _function_source(worker_source, "_agent_runtime_status_reply")
    gm_summary_reply = _function_source(worker_source, "_agent_runtime_gm_summary_reply")
    runtime_report_reply = _function_source(worker_source, "_handle_agent_runtime_report_query")
    operation_replay_reply = _function_source(worker_source, "_handle_agent_runtime_operation_replay_query")
    runtime_system_event_sender = _function_source(worker_source, "_send_agent_runtime_system_event")
    runtime_event_emitter = _function_source(worker_source, "_emit_agent_runtime_events_since")
    runtime_event_metadata_helper = _function_source(worker_source, "_safe_runtime_event_metadata")
    runtime_event_disclosure_guard = _function_source(worker_source, "_should_auto_disclose_agent_runtime_event")
    runtime_event_disclosure_skip = _function_source(worker_source, "_record_skipped_agent_runtime_event_disclosure")
    runtime_audit_recorder = _function_source(worker_source, "_record_runtime_audit_event")
    lanchat_sync_bridge = _function_source(worker_source, "_record_lanchat_sync_event_in_agent_runtime")
    lanchat_sync_bridge_reason = _function_source(worker_source, "_safe_lanchat_sync_bridge_reason")
    resource_flow_formatter = _function_source(worker_source, "_format_agent_runtime_resource_flow_report")
    scene_snapshot_formatter = _function_source(worker_source, "_format_agent_runtime_scene_snapshot_report")
    resource_stage_formatter = _function_source(worker_source, "_format_agent_runtime_resource_stage_report")
    import_stage_formatter = _function_source(worker_source, "_format_agent_runtime_import_stage_report")
    geometry_fact_formatter = _function_source(worker_source, "_format_agent_runtime_geometry_fact_report")
    tool_queue_health_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_tool_queue_health_report",
    )
    batch_tooling_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_batch_tooling_report",
    )
    batch_resource_lifecycle_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_batch_resource_lifecycle_report",
    )
    replay_command_formatter = _function_source(worker_source, "_format_agent_runtime_replay_command_report")
    replay_tool_formatter = _function_source(worker_source, "_format_agent_runtime_replay_tool_execution_report")
    replay_queue_formatter = _function_source(worker_source, "_format_agent_runtime_replay_tool_queue_report")
    replay_state_patch_formatter = _function_source(worker_source, "_format_agent_runtime_replay_state_patch_report")
    replay_guard_formatter = _function_source(worker_source, "_format_agent_runtime_replay_guard_report")
    replay_plan_lifecycle_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_replay_plan_lifecycle_report",
    )
    replay_intervention_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_replay_intervention_report",
    )
    replay_geometry_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_replay_geometry_report",
    )
    replay_runtime_event_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_replay_runtime_event_report",
    )
    replay_report_formatter = _function_source(worker_source, "_format_agent_runtime_replay_report")
    runtime_event_replay_summary = _function_source(
        core_source,
        "_runtime_event_replay_summary",
    )
    replay_failure_strategy_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_replay_failure_strategy_report",
    )
    replay_layout_formatter = _function_source(worker_source, "_format_agent_runtime_replay_layout_report")
    replay_vlm_formatter = _function_source(worker_source, "_format_agent_runtime_replay_vlm_report")
    replay_environment_formatter = _function_source(worker_source, "_format_agent_runtime_replay_environment_report")
    replay_readiness_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_replay_resource_readiness_report",
    )
    replay_sync_formatter = _function_source(worker_source, "_format_agent_runtime_sync_replay_report")
    replay_asset_transfer_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_replay_asset_transfer_report",
    )
    replay_peer_sync_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_replay_peer_sync_report",
    )
    gm_runtime_event_replay_formatter = _function_source(
        worker_source,
        "_format_agent_runtime_gm_runtime_event_replay_digest",
    )
    if not resource_flow_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_resource_flow_report not found")
    else:
        for token in (
            '"batches {batch_count}"',
            '"completed {completed_count}"',
            '"failed {failed_count}"',
            "image_ready_count",
            "model_ready_count",
            "import_ready_count",
        ):
            if token not in resource_flow_formatter:
                violations.append(f"LANChatAgentWorker resource flow formatter missing token: {token}")
    if not lanchat_sync_bridge:
        violations.append("LANChatAgentWorker._record_lanchat_sync_event_in_agent_runtime not found")
    else:
        for token in (
            'action="runtime_sync_event"',
            "_safe_lanchat_sync_bridge_reason",
            '"event": dict(result.get("sync_event") or {})',
            '"sync_state": dict(result.get("sync_status") or {})',
        ):
            if token not in lanchat_sync_bridge:
                violations.append(f"LANChatAgentWorker sync bridge missing safe Runtime token: {token}")
        if 'str(result.get("message")' in lanchat_sync_bridge:
            violations.append("LANChatAgentWorker sync bridge must not expose raw Runtime message as reason")
    if not lanchat_sync_bridge_reason:
        violations.append("LANChatAgentWorker._safe_lanchat_sync_bridge_reason not found")
    else:
        for token in (
            "runtime_sync_rejected",
            "provider",
            "prompt",
            "api_key",
            "https://",
            ".glb",
        ):
            if token not in lanchat_sync_bridge_reason:
                violations.append(f"LANChatAgentWorker sync bridge reason sanitizer missing token: {token}")
    if not scene_snapshot_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_scene_snapshot_report not found")
    else:
        for token in (
            "snapshot_count",
            "observed_actor_count",
            "observed_actor_total_count",
            "latest_source",
            "snapshots",
            "observed",
        ):
            if token not in scene_snapshot_formatter:
                violations.append(f"LANChatAgentWorker scene snapshot formatter missing token: {token}")
    if not resource_stage_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_resource_stage_report not found")
    else:
        for token in (
            "event_count",
            "by_phase",
            "requested_count",
            "failed_count",
            "latest_events",
            "image",
            "model",
        ):
            if token not in resource_stage_formatter:
                violations.append(f"LANChatAgentWorker resource stage formatter missing token: {token}")
    if not import_stage_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_import_stage_report not found")
    else:
        for token in (
            "event_count",
            "requested_count",
            "imported_count",
            "failed_count",
            "latest_events",
            "imported",
        ):
            if token not in import_stage_formatter:
                violations.append(f"LANChatAgentWorker import stage formatter missing token: {token}")
    if not geometry_fact_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_geometry_fact_report not found")
    else:
        for token in (
            "fact_count",
            "aabb_actor_count",
            "aabb_skipped_count",
            "overlap_issue_count",
            "fact_type_counts",
            "status_counts",
            "AABB actors",
            "overlap issues",
        ):
            if token not in geometry_fact_formatter:
                violations.append(f"LANChatAgentWorker geometry fact formatter missing token: {token}")
    if not tool_queue_health_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_tool_queue_health_report not found")
    else:
        for token in (
            "queue_count",
            "queued_count",
            "running_count",
            "blocked_count",
            "terminal_count",
            "active_count",
            "queue_pressure",
            "pressure",
        ):
            if token not in tool_queue_health_formatter:
                violations.append(f"LANChatAgentWorker tool queue health formatter missing token: {token}")
    if not batch_tooling_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_batch_tooling_report not found")
    else:
        for token in (
            "fact_count",
            "created_batch_fact_count",
            "created_batch_count",
            "prioritized_item_count",
            "merged_intervention_fact_count",
            "merged_intervention_item_count",
            "absorbed_intervention_count",
            "latest_fact_types",
        ):
            if token not in batch_tooling_formatter:
                violations.append(f"LANChatAgentWorker batch tooling formatter missing token: {token}")
    if not batch_resource_lifecycle_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_batch_resource_lifecycle_report not found")
    else:
        for token in (
            '"events {resource_event_count}"',
            '"image {image_ready_count}/{image_failed_count}"',
            '"model {model_ready_count}/{model_failed_count}"',
            '"import {import_ready_count}/{import_failed_count}"',
            '"env {environment_ready_count}/{environment_failed_count}"',
        ):
            if token not in batch_resource_lifecycle_formatter:
                violations.append(
                    "LANChatAgentWorker batch resource lifecycle formatter missing token: "
                    f"{token}"
                )
    if not operation_replay_reply:
        violations.append("LANChatAgentWorker._handle_agent_runtime_operation_replay_query not found")
    else:
        for token in (
            "batch_resource_lifecycle_summary",
            "_format_agent_runtime_batch_resource_lifecycle_report",
            "runtime_command_summary",
            "_format_agent_runtime_replay_command_report",
            "tool_execution_summary",
            "_format_agent_runtime_replay_tool_execution_report",
            "tool_graph_queue_summary",
            "_format_agent_runtime_replay_tool_queue_report",
            "state_patch_summary",
            "_format_agent_runtime_replay_state_patch_report",
            "runtime_guard_replay_summary",
            "_format_agent_runtime_replay_guard_report",
            "scene_plan_lifecycle_summary",
            "_format_agent_runtime_replay_plan_lifecycle_report",
            "intervention_batch_replay_summary",
            "_format_agent_runtime_replay_intervention_report",
            "geometry_fact_replay_summary",
            "_format_agent_runtime_replay_geometry_report",
            "runtime_event_replay_summary",
            "_format_agent_runtime_replay_runtime_event_report",
            "tool_failure_strategy_summary",
            "_format_agent_runtime_replay_failure_strategy_report",
            "layout_adjustment_summary",
            "_format_agent_runtime_replay_layout_report",
            "vlm_checkpoint_summary",
            "_format_agent_runtime_replay_vlm_report",
            "environment_component_summary",
            "_format_agent_runtime_replay_environment_report",
            "resource_readiness_replay_summary",
            "_format_agent_runtime_replay_resource_readiness_report",
            "sync_summary",
            "_format_agent_runtime_sync_replay_report",
            "asset_transfer_replay_summary",
            "_format_agent_runtime_replay_asset_transfer_report",
            "peer_sync_replay_summary",
            "_format_agent_runtime_replay_peer_sync_report",
            "batch_resources",
            "commands",
            "tools",
            "queue",
            "state_patch",
            "guard",
            "plan_lifecycle",
            "interventions",
            "geometry",
            "runtime_events",
            "failure_strategy",
            "layout",
            "vlm",
            "environment",
            "resource_readiness",
            "sync",
            "asset_transfer",
            "peer_sync",
        ):
            if token not in operation_replay_reply:
                violations.append(f"LANChatAgentWorker operation replay reply missing token: {token}")
    if not runtime_report_reply:
        violations.append("LANChatAgentWorker._handle_agent_runtime_report_query not found")
    else:
        for token in (
            "operation_replay_summary",
            "sync_replay_summary",
            "_format_agent_runtime_sync_replay_report",
            "asset_transfer_replay_summary",
            "_format_agent_runtime_replay_asset_transfer_report",
            "peer_sync_replay_summary",
            "_format_agent_runtime_replay_peer_sync_report",
            "sync replay",
            "asset transfer replay",
            "peer sync replay",
        ):
            if token not in runtime_report_reply:
                violations.append(f"LANChatAgentWorker runtime report reply missing replay token: {token}")
        for token in (
            "batch_tooling_summary",
            "batch_tooling_text",
            "_format_agent_runtime_batch_tooling_report",
            "batch tooling",
        ):
            if token not in runtime_report_reply:
                violations.append(f"LANChatAgentWorker runtime report reply missing batch tooling token: {token}")
        for token in (
            "state_patch_summary",
            "state_patch_text",
            "_format_agent_runtime_replay_state_patch_report",
            "state patch",
            "tool_failure_strategy_summary",
            "failure_strategy_text",
            "_format_agent_runtime_replay_failure_strategy_report",
            "failure strategy",
            "runtime_guard_replay_summary",
            "runtime_guard_text",
            "_format_agent_runtime_replay_guard_report",
            "guard:",
            "scene_plan_lifecycle_summary",
            "plan_lifecycle_text",
            "_format_agent_runtime_replay_plan_lifecycle_report",
            "plan lifecycle",
        ):
            if token not in runtime_report_reply:
                violations.append(f"LANChatAgentWorker runtime report reply missing state/failure token: {token}")
        for token in (
            "tool_queue_health_summary",
            "tool_queue_health_text",
            "_format_agent_runtime_tool_queue_health_report",
            "runtime queue",
        ):
            if token not in runtime_report_reply:
                violations.append(f"LANChatAgentWorker runtime report reply missing queue health token: {token}")
        for token in (
            "tool_execution_digest",
            "tool_execution_text",
            "_format_agent_runtime_tool_execution_digest_report",
            "tool execution",
        ):
            if token not in runtime_report_reply:
                violations.append(f"LANChatAgentWorker runtime report reply missing tool execution token: {token}")
        for token in (
            "vlm_checkpoint_summary",
            "vlm_checkpoint_text",
            "_format_agent_runtime_replay_vlm_report",
            "vlm replay",
            "review_advisory_replay_summary",
            "review_advisory_replay_text",
            "_format_agent_runtime_replay_review_advisory_report",
            "review advisory replay",
        ):
            if token not in runtime_report_reply:
                violations.append(f"LANChatAgentWorker runtime report reply missing VLM/review replay token: {token}")
        for token in (
            "scene_design_contract_summary",
            "scene_contract_text",
            "_format_agent_runtime_scene_contract_report",
            "scene contract",
        ):
            if token not in runtime_report_reply:
                violations.append(f"LANChatAgentWorker runtime report reply missing scene contract token: {token}")
        for token in (
            "semantic_arbitration_summary",
            "semantic_arbitration_text",
            "_format_agent_runtime_semantic_arbitration_report",
            "semantic arbitration",
        ):
            if token not in runtime_report_reply:
                violations.append(f"LANChatAgentWorker runtime report reply missing semantic arbitration token: {token}")
        for token in (
            "scene_snapshot_summary",
            "scene_snapshot_text",
            "_format_agent_runtime_scene_snapshot_report",
            "scene snapshot",
            "resource_summary",
            "runtime_resource_text",
            "_format_agent_runtime_resource_stage_report",
            "runtime resources",
            "import_summary",
            "import_text",
            "_format_agent_runtime_import_stage_report",
            "import:",
        ):
            if token not in runtime_report_reply:
                violations.append(f"LANChatAgentWorker runtime report reply missing scene/resource/import token: {token}")
        for token in (
            "geometry_fact_summary",
            "geometry_text",
            "_format_agent_runtime_geometry_fact_report",
            "geometry facts",
        ):
            if token not in runtime_report_reply:
                violations.append(f"LANChatAgentWorker runtime report reply missing geometry fact token: {token}")
    if not replay_report_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_report not found")
    else:
        for token in (
            "runtime_event_replay_summary",
            "disclosure_skipped_count",
            "_format_agent_runtime_replay_runtime_event_report",
        ):
            if token not in replay_report_formatter:
                violations.append(f"LANChatAgentWorker replay report formatter missing runtime-event token: {token}")
    if not runtime_system_event_sender:
        violations.append("LANChatAgentWorker._send_agent_runtime_system_event not found")
    else:
        for token in (
            "runtime_event",
            "runtime_event_metadata",
            "json.dumps(metadata",
        ):
            if token not in runtime_system_event_sender:
                violations.append(f"LANChatAgentWorker runtime event sender missing metadata token: {token}")
    if not runtime_event_emitter:
        violations.append("LANChatAgentWorker._emit_agent_runtime_events_since not found")
    else:
        for token in (
            "disclose_events",
            "MAX_AGENT_RUNTIME_DISCLOSURE_EVENT_LOOKBACK",
            "_should_auto_disclose_agent_runtime_event",
            "_format_agent_runtime_event_rows(disclose_events)",
            "_record_skipped_agent_runtime_event_disclosure",
        ):
            if token not in runtime_event_emitter:
                violations.append(f"LANChatAgentWorker runtime event emitter missing disclosure filter token: {token}")
    if not runtime_event_metadata_helper:
        violations.append("LANChatAgentWorker._safe_runtime_event_metadata not found")
    else:
        for token in (
            "runtime_event_id",
            "runtime_event_type",
            "runtime_plan_id",
            "runtime_batch_id",
            "runtime_stage",
            "runtime_audience",
            "runtime_level",
            "runtime_progress",
        ):
            if token not in runtime_event_metadata_helper:
                violations.append(f"LANChatAgentWorker runtime event metadata helper missing token: {token}")
    if not runtime_event_disclosure_guard:
        violations.append("LANChatAgentWorker._should_auto_disclose_agent_runtime_event not found")
    else:
        for token in ("host", "participants", "all"):
            if token not in runtime_event_disclosure_guard:
                violations.append(f"LANChatAgentWorker runtime event disclosure guard missing audience token: {token}")
    if not runtime_event_disclosure_skip:
        violations.append("LANChatAgentWorker._record_skipped_agent_runtime_event_disclosure not found")
    elif "runtime_system_event_disclosure_skipped" not in runtime_event_disclosure_skip:
        violations.append("LANChatAgentWorker runtime event disclosure skip audit missing event token")
    else:
        for token in ("runtime_plan_id", "batch_id"):
            if token not in runtime_event_disclosure_skip:
                violations.append(f"LANChatAgentWorker runtime event disclosure skip audit missing scope token: {token}")
    if not runtime_audit_recorder:
        violations.append("LANChatAgentWorker._record_runtime_audit_event not found")
    elif "runtime_plan_id" not in runtime_audit_recorder:
        violations.append("LANChatAgentWorker runtime audit recorder missing runtime_plan_id scope token")
    if not replay_command_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_command_report not found")
    else:
        for token in (
            "cancelled_batch_total",
            "cancelled_graph_total",
            "resumed_graph_total",
            "retried_graph_total",
            "latest_command",
        ):
            if token not in replay_command_formatter:
                violations.append(f"LANChatAgentWorker replay command formatter missing token: {token}")
    if not replay_tool_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_tool_execution_report not found")
    else:
        for token in (
            "started_count",
            "succeeded_count",
            "failed_count",
            "blocked_count",
            "retry_scheduled_count",
            "skipped_count",
            "latest_tool_event",
        ):
            if token not in replay_tool_formatter:
                violations.append(f"LANChatAgentWorker replay tool formatter missing token: {token}")
    if not replay_queue_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_tool_queue_report not found")
    else:
        for token in (
            "queued_count",
            "dequeued_count",
            "completed_count",
            "rejected_count",
            "blocked_count",
            "missing_graph_count",
            "latest_queue_event",
        ):
            if token not in replay_queue_formatter:
                violations.append(f"LANChatAgentWorker replay queue formatter missing token: {token}")
    if not replay_state_patch_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_state_patch_report not found")
    else:
        for token in (
            "version_stamped",
            "applied",
            "conflict",
            "invalid",
            "reconciled",
            "reconcile_failed",
            "latest_events",
        ):
            if token not in replay_state_patch_formatter:
                violations.append(f"LANChatAgentWorker replay state patch formatter missing token: {token}")
    if not replay_guard_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_guard_report not found")
    else:
        for token in (
            "blocked_count",
            "high_risk_confirmation_required_count",
            "write_confirmation_required_count",
            "system_actor_write_blocked_count",
            "user_visible_blocked_event_count",
            "latest_block",
        ):
            if token not in replay_guard_formatter:
                violations.append(f"LANChatAgentWorker replay guard formatter missing token: {token}")
    if not replay_plan_lifecycle_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_plan_lifecycle_report not found")
    else:
        for token in (
            "created_count",
            "confirmed_count",
            "state_persisted_count",
            "state_persist_failed_count",
            "status_persisted_count",
            "status_persist_failed_count",
            "extracted_count",
            "latest_plan_event",
        ):
            if token not in replay_plan_lifecycle_formatter:
                violations.append(f"LANChatAgentWorker replay plan lifecycle formatter missing token: {token}")
    if not replay_intervention_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_intervention_report not found")
    else:
        for token in (
            "routed_count",
            "queued_count",
            "persisted_count",
            "persist_failed_count",
            "skipped_count",
            "enqueue_failed_count",
            "absorbed_count",
            "route_absorbable_count",
            "route_non_absorbable_count",
            "route_requested_item_count",
            "merge_event_count",
            "merged_item_count",
            "merge_absorbed_count",
            "latest_intervention_batch",
        ):
            if token not in replay_intervention_formatter:
                violations.append(f"LANChatAgentWorker replay intervention formatter missing token: {token}")
    if not replay_geometry_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_geometry_report not found")
    else:
        for token in (
            "patch_event_count",
            "fact_count",
            "aabb_actor_count",
            "aabb_skipped_count",
            "overlap_issue_count",
            "status_counts",
            "fact_type_counts",
            "latest_geometry_event",
        ):
            if token not in replay_geometry_formatter:
                violations.append(f"LANChatAgentWorker replay geometry formatter missing token: {token}")
    if not replay_runtime_event_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_runtime_event_report not found")
    else:
        for token in (
            "emitted_count",
            "emit_failed_count",
            "disclosure_skipped_count",
            "event_type_counts",
            "latest_runtime_event",
            "latest_disclosure_skip",
            "skipped {skipped_count}",
        ):
            if token not in replay_runtime_event_formatter:
                violations.append(f"LANChatAgentWorker replay runtime event formatter missing token: {token}")
    if not runtime_event_replay_summary:
        violations.append("AgentRuntime._runtime_event_replay_summary not found")
    else:
        for token in (
            "runtime_system_event_disclosure_skipped",
            "disclosure_skipped_count",
            "latest_disclosure_skip",
        ):
            if token not in runtime_event_replay_summary:
                violations.append(f"AgentRuntime runtime event replay summary missing token: {token}")
    if not replay_failure_strategy_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_failure_strategy_report not found")
    else:
        for token in (
            "retry_scheduled_count",
            "dependency_skipped_count",
            "abandoned_late_result_count",
            "handler_failed_count",
            "invalid_result_count",
            "invalid_state_patch_count",
            "state_patch_conflict_count",
            "stopped_by_runtime_command_count",
            "latest_strategy_event",
        ):
            if token not in replay_failure_strategy_formatter:
                violations.append(f"LANChatAgentWorker replay failure strategy formatter missing token: {token}")
    if not replay_layout_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_layout_report not found")
    else:
        for token in (
            "request_count",
            "request_failed_count",
            "confirmation_count",
            "confirmation_failed_count",
            "applied_count",
            "transform_success_count",
            "transform_failed_count",
            "ground_snapped_count",
            "overlap_resolved_count",
            "delta_count",
            "latest_graph_status",
        ):
            if token not in replay_layout_formatter:
                violations.append(f"LANChatAgentWorker replay layout formatter missing token: {token}")
    if not replay_vlm_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_vlm_report not found")
    else:
        for token in (
            "checkpoint_count",
            "advisory_count",
            "status_counts",
            "checkpoint_counts",
            "latest_checkpoints",
        ):
            if token not in replay_vlm_formatter:
                violations.append(f"LANChatAgentWorker replay VLM formatter missing token: {token}")
    if not replay_environment_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_environment_report not found")
    else:
        for token in (
            "ready_event_count",
            "failed_event_count",
            "import_event_count",
            "import_failed_event_count",
            "event_type_counts",
            "latest_event_type",
        ):
            if token not in replay_environment_formatter:
                violations.append(f"LANChatAgentWorker replay environment formatter missing token: {token}")
    if not replay_readiness_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_resource_readiness_report not found")
    else:
        for token in (
            "status_query_count",
            "published_count",
            "publish_failed_count",
            "readiness_event_count",
            "status_counts",
            "latest_readiness_event",
        ):
            if token not in replay_readiness_formatter:
                violations.append(f"LANChatAgentWorker replay resource readiness formatter missing token: {token}")
    if not replay_sync_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_sync_replay_report not found")
    else:
        for token in (
            "recorded_count",
            "failed_count",
            "actor_transform_count",
            "transfer_progress_count",
            "latest_transfer_progress",
        ):
            if token not in replay_sync_formatter:
                violations.append(f"LANChatAgentWorker sync replay formatter missing token: {token}")
    if not replay_asset_transfer_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_asset_transfer_report not found")
    else:
        for token in (
            "asset_event_count",
            "asset_transfer_started_count",
            "asset_transfer_progress_count",
            "asset_transfer_completed_count",
            "asset_transfer_failed_count",
            "peer_asset_ready_count",
            "latest_transfer_progress",
        ):
            if token not in replay_asset_transfer_formatter:
                violations.append(f"LANChatAgentWorker asset transfer replay formatter missing token: {token}")
        for forbidden in ("latest_asset_id", "latest_peer_id", "asset_path", "provider", "prompt", "url", "raw"):
            if forbidden in replay_asset_transfer_formatter:
                violations.append(
                    "LANChatAgentWorker asset transfer replay formatter must not expose internal token: "
                    f"{forbidden}"
                )
    if not replay_peer_sync_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_replay_peer_sync_report not found")
    else:
        for token in (
            "peer_event_count",
            "peer_join_count",
            "peer_leave_count",
            "room_close_count",
            "sync_reconcile_count",
            "sync_reconcile_failed_count",
            "state_reconcile_count",
            "state_reconcile_failed_count",
        ):
            if token not in replay_peer_sync_formatter:
                violations.append(f"LANChatAgentWorker peer sync replay formatter missing token: {token}")
        for forbidden in ("latest_peer_id", "peer_id", "message_id", "provider", "prompt", "url", "raw"):
            if forbidden in replay_peer_sync_formatter:
                violations.append(
                    "LANChatAgentWorker peer sync replay formatter must not expose internal token: "
                    f"{forbidden}"
                )
    if not gm_summary_reply:
        violations.append("LANChatAgentWorker._agent_runtime_gm_summary_reply not found")
    else:
        for token in (
            "resource_flow_digest",
            "_format_agent_runtime_resource_flow_report",
            "资源批次",
            "sync_replay_digest",
            "_format_agent_runtime_gm_sync_replay_digest",
            "runtime_event_replay_digest",
            "_format_agent_runtime_gm_runtime_event_replay_digest",
            "RuntimeEvent replay",
            "同步复盘",
        ):
            if token not in gm_summary_reply:
                violations.append(f"LANChatAgentWorker GM summary reply missing Runtime digest token: {token}")
        for token in (
            "batch_tooling_digest",
            "_format_agent_runtime_batch_tooling_report",
            "Batch tooling",
        ):
            if token not in gm_summary_reply:
                violations.append(f"LANChatAgentWorker GM summary reply missing batch tooling token: {token}")
        for token in (
            "state_patch_digest",
            "_format_agent_runtime_replay_state_patch_report",
            "StatePatch",
            "tool_failure_strategy_digest",
            "_format_agent_runtime_replay_failure_strategy_report",
            "Failure strategy",
            "runtime_guard_digest",
            "_format_agent_runtime_replay_guard_report",
            "RuntimeGuard",
            "scene_plan_lifecycle_digest",
            "_format_agent_runtime_replay_plan_lifecycle_report",
            "Plan lifecycle",
            "engine_write_digest",
            "_format_agent_runtime_engine_write_report",
            "Engine write",
            "message_delivery_digest",
            "_format_agent_runtime_message_delivery_report",
            "Message delivery",
        ):
            if token not in gm_summary_reply:
                violations.append(f"LANChatAgentWorker GM summary reply missing runtime health token: {token}")
        for token in (
            "tool_queue_health_digest",
            "_format_agent_runtime_tool_queue_health_report",
            "Runtime queue",
        ):
            if token not in gm_summary_reply:
                violations.append(f"LANChatAgentWorker GM summary reply missing queue health token: {token}")
        for token in (
            "tool_execution_digest",
            "tool_execution_text",
            "_format_agent_runtime_tool_execution_digest_report",
            "Tool execution",
        ):
            if token not in gm_summary_reply:
                violations.append(f"LANChatAgentWorker GM summary reply missing tool execution token: {token}")
        for token in (
            "vlm_checkpoint_digest",
            "review_advisory_replay_digest",
            "_format_agent_runtime_replay_vlm_report",
            "_format_agent_runtime_replay_review_advisory_report",
            "VLM replay",
            "Review advisory replay",
        ):
            if token not in gm_summary_reply:
                violations.append(f"LANChatAgentWorker GM summary reply missing VLM/review replay token: {token}")
        for token in (
            "scene_design_contract_digest",
            "scene_contract_text",
            "_format_agent_runtime_scene_contract_report",
            "Scene contract",
        ):
            if token not in gm_summary_reply:
                violations.append(f"LANChatAgentWorker GM summary reply missing scene contract token: {token}")
        for token in (
            "semantic_arbitration_digest",
            "semantic_arbitration_text",
            "_format_agent_runtime_semantic_arbitration_report",
            "Semantic arbitration",
        ):
            if token not in gm_summary_reply:
                violations.append(f"LANChatAgentWorker GM summary reply missing semantic arbitration token: {token}")
        for token in (
            "scene_snapshot_digest",
            "scene_snapshot_text",
            "_format_agent_runtime_scene_snapshot_report",
            "Scene snapshot",
            "resource_stage_digest",
            "runtime_resource_text",
            "_format_agent_runtime_resource_stage_report",
            "Runtime resources",
            "import_stage_digest",
            "import_text",
            "_format_agent_runtime_import_stage_report",
            "Import",
        ):
            if token not in gm_summary_reply:
                violations.append(f"LANChatAgentWorker GM summary reply missing scene/resource/import token: {token}")
        for token in (
            "geometry_fact_digest",
            "geometry_text",
            "_format_agent_runtime_geometry_fact_report",
            "Geometry facts",
        ):
            if token not in gm_summary_reply:
                violations.append(f"LANChatAgentWorker GM summary reply missing geometry fact token: {token}")
    if not gm_runtime_event_replay_formatter:
        violations.append("LANChatAgentWorker._format_agent_runtime_gm_runtime_event_replay_digest not found")
    else:
        for token in (
            "emitted_count",
            "emit_failed_count",
            "disclosure_skipped_count",
            "latest_disclosure_skip",
            "latest-skip",
        ):
            if token not in gm_runtime_event_replay_formatter:
                violations.append(f"LANChatAgentWorker GM runtime event replay formatter missing token: {token}")
    if not runtime_status_reply:
        violations.append("LANChatAgentWorker._agent_runtime_status_reply not found")
    else:
        for token in (
            "batch_resource_flow_summary",
            "resource_flow_text",
            "_format_agent_runtime_resource_flow_report",
            "asset_transfer_replay_summary",
            "_format_agent_runtime_replay_asset_transfer_report",
            "peer_sync_replay_summary",
            "_format_agent_runtime_replay_peer_sync_report",
            "runtime_event_replay_summary",
            "_format_agent_runtime_replay_runtime_event_report",
            "RuntimeEvent replay",
            "同传复盘",
            "Peer 复盘",
        ):
            if token not in runtime_status_reply:
                violations.append(f"LANChatAgentWorker Runtime status reply missing resource flow token: {token}")
        for token in (
            "batch_tooling_summary",
            "batch_tooling_text",
            "_format_agent_runtime_batch_tooling_report",
            "Batch tooling",
        ):
            if token not in runtime_status_reply:
                violations.append(f"LANChatAgentWorker Runtime status reply missing batch tooling token: {token}")
        for token in (
            "state_patch_summary",
            "state_patch_text",
            "_format_agent_runtime_replay_state_patch_report",
            "StatePatch",
            "tool_failure_strategy_summary",
            "failure_strategy_text",
            "_format_agent_runtime_replay_failure_strategy_report",
            "Failure strategy",
            "runtime_guard_replay_summary",
            "runtime_guard_text",
            "_format_agent_runtime_replay_guard_report",
            "RuntimeGuard",
            "scene_plan_lifecycle_summary",
            "plan_lifecycle_text",
            "_format_agent_runtime_replay_plan_lifecycle_report",
            "Plan lifecycle",
        ):
            if token not in runtime_status_reply:
                violations.append(f"LANChatAgentWorker Runtime status reply missing state/failure token: {token}")
        for token in (
            "tool_queue_health_summary",
            "tool_queue_health_text",
            "_format_agent_runtime_tool_queue_health_report",
            "Runtime queue",
        ):
            if token not in runtime_status_reply:
                violations.append(f"LANChatAgentWorker Runtime status reply missing queue health token: {token}")
        for token in (
            "tool_execution_digest",
            "tool_execution_text",
            "_format_agent_runtime_tool_execution_digest_report",
            "Tool execution",
        ):
            if token not in runtime_status_reply:
                violations.append(f"LANChatAgentWorker Runtime status reply missing tool execution token: {token}")
        for token in (
            "vlm_checkpoint_summary",
            "vlm_checkpoint_text",
            "_format_agent_runtime_replay_vlm_report",
            "VLM replay",
            "review_advisory_replay_summary",
            "review_advisory_replay_text",
            "_format_agent_runtime_replay_review_advisory_report",
            "Review advisory replay",
        ):
            if token not in runtime_status_reply:
                violations.append(f"LANChatAgentWorker Runtime status reply missing VLM/review replay token: {token}")
        for token in (
            "scene_design_contract_summary",
            "scene_contract_text",
            "_format_agent_runtime_scene_contract_report",
            "场景契约",
        ):
            if token not in runtime_status_reply:
                violations.append(f"LANChatAgentWorker Runtime status reply missing scene contract token: {token}")
        for token in (
            "semantic_arbitration_summary",
            "semantic_arbitration_text",
            "_format_agent_runtime_semantic_arbitration_report",
            "语义仲裁",
        ):
            if token not in runtime_status_reply:
                violations.append(f"LANChatAgentWorker Runtime status reply missing semantic arbitration token: {token}")
        for token in (
            "scene_snapshot_summary",
            "scene_snapshot_text",
            "_format_agent_runtime_scene_snapshot_report",
            "场景快照",
            "resource_summary",
            "runtime_resource_text",
            "_format_agent_runtime_resource_stage_report",
            "Runtime 资源",
            "import_summary",
            "import_text",
            "_format_agent_runtime_import_stage_report",
            "导入",
        ):
            if token not in runtime_status_reply:
                violations.append(f"LANChatAgentWorker Runtime status reply missing scene/resource/import token: {token}")
        for token in (
            "geometry_fact_summary",
            "geometry_text",
            "_format_agent_runtime_geometry_fact_report",
            "几何事实",
        ):
            if token not in runtime_status_reply:
                violations.append(f"LANChatAgentWorker Runtime status reply missing geometry fact token: {token}")

    if violations:
        print("[FAIL] static AgentRuntime flag boundary gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static AgentRuntime flag boundary gate")
    return True


def _runtime_state_apply_patch_boundary_gate() -> bool:
    print("[RUN] static RuntimeState apply_patch boundary gate")
    core_path = REPO_ROOT / AGENT_RUNTIME_CORE
    try:
        with tokenize.open(core_path) as handle:
            source = handle.read()
    except Exception as exc:
        print(f"[FAIL] static RuntimeState apply_patch boundary gate: cannot read {AGENT_RUNTIME_CORE}: {exc}")
        return False
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    def enclosing_function(node: ast.AST) -> str:
        current = parents.get(node)
        while current is not None:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return current.name
            current = parents.get(current)
        return "<module>"

    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "apply_patch":
            continue
        owner = enclosing_function(node)
        if owner not in ALLOWED_RUNTIME_STATE_APPLY_PATCH_FUNCTIONS:
            violations.append(
                f"{AGENT_RUNTIME_CORE}:{getattr(node, 'lineno', '?')}: "
                f"RuntimeState.apply_patch call outside allowed executor boundary: {owner}"
            )
    if violations:
        print("[FAIL] static RuntimeState apply_patch boundary gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static RuntimeState apply_patch boundary gate")
    return True


def _extract_policy_command_set(source: str, name: str) -> set[str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        value = node.value
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "frozenset":
            if not value.args:
                return set()
            value = value.args[0]
        if isinstance(value, (ast.Set, ast.List, ast.Tuple)):
            return {
                str(item.value).strip().lower()
                for item in value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            }
    return set()


def _extract_workflow_commands(path: Path) -> set[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    commands: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "WORKFLOW_COMMANDS" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key in node.value.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                value = key.value.strip().lower()
                if value:
                    commands.add(value if value.startswith("/") else f"/{value}")
    return commands


def _iter_workflow_command_files() -> list[Path]:
    files: list[Path] = []
    for root in WORKFLOW_COMMAND_SCAN_ROOTS:
        root_path = REPO_ROOT / root
        if root_path.is_file():
            files.append(root_path)
            continue
        if root_path.is_dir():
            for path in root_path.rglob("*.py"):
                rel_parts = path.relative_to(REPO_ROOT).parts
                if "tests" in rel_parts or path.name.startswith("test_"):
                    continue
                files.append(path)
    return sorted(set(files))


def _workflow_command_exposure_gate() -> bool:
    print("[RUN] static workflow command exposure gate")
    policy_path = REPO_ROOT / "editor/plugins/AITool/services/workflow_command_policy.py"
    register_path = REPO_ROOT / "editor/plugins/AITool/cai_extensions/register.py"
    try:
        policy_source = policy_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        policy_source = policy_path.read_text(encoding="utf-8-sig")
    try:
        register_source = register_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        register_source = register_path.read_text(encoding="utf-8-sig")
    deprecated = _extract_policy_command_set(policy_source, "DEPRECATED_USER_WORKFLOW_COMMANDS")
    internal = _extract_policy_command_set(policy_source, "INTERNAL_DEBUG_WORKFLOW_COMMANDS")

    violations: list[str] = []
    missing_deprecated = sorted(REQUIRED_DEPRECATED_WORKFLOW_COMMANDS - deprecated)
    if missing_deprecated:
        violations.append(
            "workflow_command_policy.py missing deprecated commands: " + ", ".join(missing_deprecated)
        )
    missing_internal = sorted(REQUIRED_INTERNAL_WORKFLOW_COMMANDS - internal)
    if missing_internal:
        violations.append(
            "workflow_command_policy.py missing internal/debug commands: " + ", ".join(missing_internal)
        )

    for path in _iter_workflow_command_files():
        commands = _extract_workflow_commands(path)
        if not commands:
            continue
        rel = _to_repo_path(path)
        for command in sorted(commands & REQUIRED_DEPRECATED_WORKFLOW_COMMANDS):
            if command not in deprecated:
                violations.append(f"{rel}: {command} appears in WORKFLOW_COMMANDS but is not deprecated")
        for command in sorted(commands & REQUIRED_INTERNAL_WORKFLOW_COMMANDS):
            if command not in internal:
                violations.append(f"{rel}: {command} appears in WORKFLOW_COMMANDS but is not internal/debug")

    required_policy_tokens = (
        'if exposure == "deprecated":',
        "return False",
        "should_execute_workflow_function",
        "install_workflow_function_policy",
        "get_with_policy",
        "has_with_policy",
        "list_function_ids_with_policy",
    )
    if not all(token in policy_source for token in required_policy_tokens):
        violations.append("workflow_command_policy.py is missing hidden workflow function execution guards")

    workflow_plugin_source = register_source[
        register_source.find("class CabbageWorkflowPlugin:"):
        register_source.find("class CabbageWorkflowSyncPlugin:")
    ]
    register_function = _function_source(workflow_plugin_source, "register")
    if not register_function:
        violations.append("cai_extensions/register.py CabbageExtension.register not found")
    else:
        required_order = (
            "registry = runtime.get_registry(\"workflow\")",
            "command_registry = runtime.get_registry(\"workflow_command\")",
            "install_workflow_command_policy(command_registry)",
            "install_workflow_function_policy(registry, command_registry)",
            "for module_name in self.flow_modules:",
            "registry.register(function_id, graph, overwrite=True)",
            "record_workflow_function_exposure(command_registry, command, function_id)",
            "if not should_register_workflow_command(command):",
            "command_registry.register(command, function_id, overwrite=True)",
        )
        last_index = -1
        for token in required_order:
            token_index = register_function.find(token)
            if token_index < 0:
                violations.append(f"cai_extensions/register.py register missing workflow policy token: {token}")
                continue
            if token_index < last_index:
                violations.append(f"cai_extensions/register.py register policy token out of order: {token}")
            last_index = token_index

    if violations:
        print("[FAIL] static workflow command exposure gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static workflow command exposure gate")
    return True


def _function_source(source: str, function_name: str) -> str:
    marker = f"    def {function_name}("
    start = source.find(marker)
    if start < 0:
        return ""
    next_start = source.find("\n    def ", start + len(marker))
    if next_start < 0:
        next_start = source.find("\n    @", start + len(marker))
    return source[start:] if next_start < 0 else source[start:next_start]


def _runtime_report_fact_source_gate() -> bool:
    print("[RUN] static Runtime report fact-source gate")
    core_path = REPO_ROOT / AGENT_RUNTIME_CORE
    try:
        source = core_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = core_path.read_text(encoding="utf-8-sig")
    generate_report = _function_source(source, "generate_report")
    operation_replay = _function_source(source, "operation_replay")
    compose_operation_replay = _function_source(source, "_compose_operation_replay")
    operation_replay_snapshot = _function_source(source, "_operation_replay_snapshot_via_tool_graph")
    operation_replay_summary_for_report = _function_source(source, "_operation_replay_summary_for_report")
    tool_manifest = _function_source(source, "tool_manifest")
    provider_status = _function_source(source, "provider_status")
    provider_status_snapshot = _function_source(source, "_provider_status_snapshot_via_tool_graph")
    gm_summary = _function_source(source, "gm_summary")
    gm_summary_snapshot = _function_source(source, "_gm_summary_snapshot_via_tool_graph")
    runtime_events_snapshot = _function_source(source, "_runtime_events_snapshot_via_tool_graph")
    sync_status_snapshot = _function_source(source, "_sync_status_snapshot_via_tool_graph")
    execute_scene_plan = _function_source(source, "execute_scene_plan")
    enqueue_scene_plan = _function_source(source, "enqueue_scene_plan")
    enqueue_planned_batches = _function_source(source, "enqueue_planned_batches")
    enqueue_pending_intervention_batch = _function_source(source, "enqueue_pending_intervention_batch")
    build_batch_execution_graph = _function_source(source, "_build_batch_execution_graph")
    handle_message = _function_source(source, "handle_message")
    status_summary = _function_source(source, "status_summary")
    status_summary_snapshot = _function_source(source, "_status_summary_snapshot_via_tool_graph")
    batch_resource_lifecycle_replay = _function_source(source, "_batch_resource_lifecycle_replay_summary")
    intervention_batch_replay = _function_source(source, "_intervention_batch_replay_summary")
    violations: list[str] = []

    if not generate_report:
        violations.append("AgentRuntime.generate_report not found")
    else:
        required_order = [
            "_operation_replay_summary_via_tool_graph",
            "_classification_summary_for_plan",
            '"operation_replay_summary": operation_replay_summary',
            '"user_report_generated"',
            "_persist_user_report",
            'event_type="report_ready"',
        ]
        positions: list[int] = []
        for token in required_order:
            pos = generate_report.find(token)
            if pos < 0:
                violations.append(f"AgentRuntime.generate_report missing required fact/report token: {token}")
            positions.append(pos)
        if all(pos >= 0 for pos in positions) and positions != sorted(positions):
            violations.append(
                "AgentRuntime.generate_report must derive OperationLog/RuntimeState summaries "
                "before logging, persisting, and emitting the user report"
            )
        if "_operation_replay_summary_for_report(" in generate_report:
            violations.append(
                "AgentRuntime.generate_report must use runtime.report.operation_replay_summary "
                "ToolCallGraph instead of directly composing OperationLog replay facts"
            )
        if "intervention_digest = self._intervention_digest_for_report" not in generate_report:
            violations.append("AgentRuntime.generate_report missing Runtime intervention digest token")
        if '"sync_health_digest": sync_health_digest' not in generate_report:
            violations.append("AgentRuntime.generate_report missing Runtime sync health digest token")
        if "_sync_health_digest_for_report(" not in generate_report:
            violations.append("AgentRuntime.generate_report must derive sync health from Runtime sync summaries")
        if '"runtime_guard_replay_summary": dict(operation_replay_summary.get("runtime_guard_replay_summary") or {})' not in generate_report:
            violations.append("AgentRuntime.generate_report missing RuntimeGuard replay summary token")
        if '"scene_plan_lifecycle_summary": dict(operation_replay_summary.get("scene_plan_lifecycle_summary") or {})' not in generate_report:
            violations.append("AgentRuntime.generate_report missing ScenePlan lifecycle summary token")
        if '"vlm_checkpoint_summary": dict(operation_replay_summary.get("vlm_checkpoint_summary") or {})' not in generate_report:
            violations.append("AgentRuntime.generate_report missing VLM checkpoint replay summary token")
        if '"review_advisory_replay_summary": dict(operation_replay_summary.get("review_advisory_summary") or {})' not in generate_report:
            violations.append("AgentRuntime.generate_report missing review advisory replay summary token")
        for required in (
            "scene_design_contract_summary = self._scene_design_contract_summary_for_plan",
            '"scene_design_contract_summary": scene_design_contract_summary',
            "semantic_arbitration_summary = self._semantic_arbitration_digest_for_report",
            '"semantic_arbitration_summary": semantic_arbitration_summary',
            "scene_snapshot_summary = self._scene_snapshot_summary_for_plan",
            '"scene_snapshot_summary": scene_snapshot_summary',
            "geometry_fact_summary = self._geometry_fact_summary_for_plan",
            '"geometry_fact_summary": geometry_fact_summary',
            "resource_summary = self._resource_summary_for_plan",
            '"resource_summary": resource_summary',
            "import_summary = self._import_summary_for_plan",
            '"import_summary": import_summary',
            "tool_execution_digest = self._tool_execution_digest_for_report",
            '"tool_execution_digest": tool_execution_digest',
        ):
            if required not in generate_report:
                violations.append(f"AgentRuntime.generate_report missing runtime report token: {required}")
        sync_health_tool = _function_source(source, "_sync_health_digest_for_report")
        for required in (
            '"peer_join_count": peer_join_count',
            '"peer_leave_count": peer_leave_count',
            '"room_close_count": room_close_count',
            '"latest_peer_id": latest_peer_id',
            '"latest_peer_event_type": latest_peer_event_type',
            '"latest_room_status": latest_room_status',
            '"actor_create_count": actor_create_count',
            '"actor_transform_count": actor_transform_count',
            '"actor_delete_count": actor_delete_count',
            '"latest_active_actor_count": latest_active_actor_count',
            '"latest_deleted_actor_count": latest_deleted_actor_count',
        ):
            if required not in sync_health_tool:
                violations.append(f"AgentRuntime sync health digest missing actor sync token: {required}")
        report_summary_tool = _function_source(source, "_operation_replay_summary_via_tool_graph")
        if "runtime.report.operation_replay_summary" not in report_summary_tool:
            violations.append(
                "AgentRuntime._operation_replay_summary_via_tool_graph must execute "
                "runtime.report.operation_replay_summary"
            )

    if not tool_manifest:
        violations.append("AgentRuntime.tool_manifest not found")
    else:
        for required in (
            "runtime.tool_manifest.snapshot",
            "custom_report_facts",
            '"runtime_tool_manifest_queried"',
        ):
            if required not in tool_manifest:
                violations.append(f"AgentRuntime.tool_manifest missing Runtime manifest fact token: {required}")
        if "self.registry.manifest(" in tool_manifest or "self.registry.capability_summary(" in tool_manifest:
            violations.append(
                "AgentRuntime.tool_manifest must read ToolRegistry facts through "
                "runtime.tool_manifest.snapshot instead of direct registry access"
            )

    if not operation_replay:
        violations.append("AgentRuntime.operation_replay not found")
    else:
        for required in (
            "runtime_operation_replay_requested",
            "runtime_operation_replay_queried",
            "_operation_replay_snapshot_via_tool_graph",
        ):
            if required not in operation_replay:
                violations.append(f"AgentRuntime.operation_replay missing Runtime replay fact token: {required}")
        if not operation_replay_snapshot or "runtime.operation_replay.snapshot" not in operation_replay_snapshot:
            violations.append(
                "AgentRuntime._operation_replay_snapshot_via_tool_graph must execute "
                "runtime.operation_replay.snapshot"
            )
        if not operation_replay_summary_for_report or "gm_summary_replay_summary" not in operation_replay_summary_for_report:
            violations.append(
                "AgentRuntime._operation_replay_summary_for_report must include gm_summary_replay_summary"
            )
        if '"geometry_fact_replay_summary": self._geometry_fact_replay_summary' not in operation_replay_summary_for_report:
            violations.append(
                "AgentRuntime._operation_replay_summary_for_report must include geometry_fact_replay_summary"
            )
        runtime_command_replay = _function_source(source, "_runtime_command_replay_summary")
        for required in (
            '"cancelled_batch_total": cancelled_batch_total',
            '"cancelled_graph_total": cancelled_graph_total',
            '"resumed_graph_total": resumed_graph_total',
            '"retried_graph_total": retried_graph_total',
            '"status_transition_counts": dict(sorted(status_transition_counts.items()))',
        ):
            if required not in runtime_command_replay:
                violations.append(f"AgentRuntime runtime command replay missing queue-impact token: {required}")
        review_advisory_replay = _function_source(source, "_review_advisory_replay_summary")
        for required in (
            '"proposal_status_counts": dict(sorted(proposal_status_counts.items()))',
            '"pending_proposal_count": int(proposal_status_counts.get("proposed") or 0)',
            '"confirmed_proposal_count": int(proposal_status_counts.get("confirmed") or 0)',
            '"rejected_proposal_count": int(proposal_status_counts.get("rejected") or 0)',
            '"advisory_item_count": advisory_item_count',
        ):
            if required not in review_advisory_replay:
                violations.append(f"AgentRuntime review advisory replay missing proposal-status token: {required}")
        layout_adjustment_replay = _function_source(source, "_layout_adjustment_replay_summary")
        for required in (
            '"proposal_status_counts": dict(sorted(proposal_status_counts.items()))',
            '"pending_proposal_count": int(proposal_status_counts.get("proposed") or 0)',
            '"confirmed_proposal_count": int(proposal_status_counts.get("confirmed") or 0)',
            '"failed_proposal_count": int(proposal_status_counts.get("failed") or 0)',
            '"delta_count": delta_count',
        ):
            if required not in layout_adjustment_replay:
                violations.append(f"AgentRuntime layout adjustment replay missing proposal-status token: {required}")
        asset_transfer_replay = _function_source(source, "_asset_transfer_replay_summary")
        for required in (
            '"asset_transfer_started_count": started_count',
            '"asset_transfer_progress_count": progress_count',
            '"asset_transfer_completed_count": completed_count',
            '"asset_transfer_failed_count": failed_count',
            '"peer_asset_ready_count": peer_ready_count',
            '"transfer_status_counts": dict(sorted(transfer_status_counts.items()))',
        ):
            if required not in asset_transfer_replay:
                violations.append(f"AgentRuntime asset transfer replay missing lifecycle token: {required}")
        if '"asset_transfer_replay_summary": asset_transfer_replay_summary' not in operation_replay_summary_for_report:
            violations.append(
                "AgentRuntime._operation_replay_summary_for_report must include asset_transfer_replay_summary"
            )
        peer_sync_replay = _function_source(source, "_peer_sync_replay_summary")
        for required in (
            '"peer_event_count": peer_event_count',
            '"peer_join_count": peer_join_count',
            '"peer_leave_count": peer_leave_count',
            '"sync_reconcile_count": sync_reconcile_count',
            '"sync_reconcile_failed_count": sync_reconcile_failed_count',
            '"state_reconcile_count": state_reconcile_count',
            '"state_reconcile_failed_count": state_reconcile_failed_count',
            '"latest_reconcile_event": latest_reconcile_event',
        ):
            if required not in peer_sync_replay:
                violations.append(f"AgentRuntime peer sync replay missing lifecycle/reconcile token: {required}")
        if '"peer_sync_replay_summary": self._peer_sync_replay_summary' not in operation_replay_summary_for_report:
            violations.append(
                "AgentRuntime._operation_replay_summary_for_report must include peer_sync_replay_summary"
            )
        if '"runtime_event_replay_summary": self._runtime_event_replay_summary' not in operation_replay_summary_for_report:
            violations.append(
                "AgentRuntime._operation_replay_summary_for_report must include runtime_event_replay_summary"
            )
        for required in (
            '"batch_resource_lifecycle_summary": self._batch_resource_lifecycle_replay_summary',
            '"batch_execution_summary": self._batch_execution_replay_summary',
        ):
            if required not in operation_replay_summary_for_report:
                violations.append(
                    f"AgentRuntime._operation_replay_summary_for_report missing batch lifecycle token: {required}"
                )
    if not batch_resource_lifecycle_replay:
        violations.append("AgentRuntime._batch_resource_lifecycle_replay_summary not found")
    else:
        for required in (
            '"image_ready_count": 0',
            '"model_ready_count": 0',
            '"import_ready_count": 0',
            '"environment_ready_count": 0',
            '"emit_failed_count": 0',
            '"batch_event_counts": {}',
            '"latest_resource_event": {}',
            '"image_resources_ready": ("image_ready_count", "image")',
            '"actors_imported": ("import_ready_count", "import")',
        ):
            if required not in batch_resource_lifecycle_replay:
                violations.append(f"AgentRuntime batch resource lifecycle replay missing token: {required}")
    if not intervention_batch_replay:
        violations.append("AgentRuntime._intervention_batch_replay_summary not found")
    else:
        for required in (
            '"route_absorbable_count": route_absorbable_count',
            '"route_non_absorbable_count": route_non_absorbable_count',
            '"route_requested_item_count": route_requested_item_count',
            '"merge_event_count": merge_event_count',
            '"merged_item_count": merged_item_count',
            '"merge_absorbed_count": merge_absorbed_count',
            'event == "batch_interventions_merged_via_tool_graph"',
        ):
            if required not in intervention_batch_replay:
                violations.append(f"AgentRuntime intervention batch replay missing route/merge token: {required}")
    if compose_operation_replay and (
        '"batch_resource_lifecycle_summary"] = self._batch_resource_lifecycle_replay_summary'
        not in compose_operation_replay
    ):
        violations.append("AgentRuntime._compose_operation_replay must expose batch_resource_lifecycle_summary")
    if compose_operation_replay and (
        '"geometry_fact_replay_summary"] = self._geometry_fact_replay_summary'
        not in compose_operation_replay
    ):
        violations.append("AgentRuntime._compose_operation_replay must expose geometry_fact_replay_summary")

    if not status_summary:
        violations.append("AgentRuntime.status_summary not found")
    else:
        for forbidden in ('"user_report_generated"', "_persist_user_report", 'event_type="report_ready"'):
            if forbidden in status_summary:
                violations.append(f"AgentRuntime.status_summary must stay read-only for reports: found {forbidden}")
        for required in (
            "runtime_status_queried",
            "_operation_log_snapshot_from_entries",
            "_status_summary_snapshot_via_tool_graph",
            "intervention_digest = self._intervention_digest_for_report",
            '"intervention_digest": intervention_digest',
            '"sync_health_digest": sync_health_digest',
            "_sync_health_digest_for_report(",
            "_batch_tooling_summary_for_plan(",
            '"batch_tooling_summary": batch_tooling_summary',
            "_tool_queue_health_summary_for_plan(",
            '"tool_queue_health_summary": tool_queue_health_summary',
            "_batch_resource_flow_summary_for_plan(",
            '"batch_resource_flow_summary": batch_resource_flow_summary',
            "runtime_event_replay_summary = self._runtime_event_replay_summary",
            '"runtime_event_replay_summary": runtime_event_replay_summary',
            "runtime_guard_replay_summary = self._runtime_guard_replay_summary",
            '"runtime_guard_replay_summary": runtime_guard_replay_summary',
            "scene_plan_lifecycle_summary = self._scene_plan_lifecycle_replay_summary",
            '"scene_plan_lifecycle_summary": scene_plan_lifecycle_summary',
            "vlm_checkpoint_summary = self._vlm_checkpoint_replay_summary",
            '"vlm_checkpoint_summary": vlm_checkpoint_summary',
            "review_advisory_replay_summary = self._review_advisory_replay_summary",
            '"review_advisory_replay_summary": review_advisory_replay_summary',
            "scene_design_contract_summary = self._scene_design_contract_summary_for_plan",
            '"scene_design_contract_summary": scene_design_contract_summary',
		            "semantic_arbitration_summary = self._semantic_arbitration_digest_for_report",
		            '"semantic_arbitration_summary": semantic_arbitration_summary',
            "scene_snapshot_summary = self._scene_snapshot_summary_for_plan",
            '"scene_snapshot_summary": scene_snapshot_summary',
            "geometry_fact_summary = self._geometry_fact_summary_for_plan",
            '"geometry_fact_summary": geometry_fact_summary',
            "resource_summary = self._resource_summary_for_plan",
            '"resource_summary": resource_summary',
            "import_summary = self._import_summary_for_plan",
            '"import_summary": import_summary',
		            "tool_execution_digest = self._tool_execution_digest_for_report",
		            '"tool_execution_digest": tool_execution_digest',
		        ):
            if required not in status_summary:
                violations.append(f"AgentRuntime.status_summary missing audit/read-summary token: {required}")
        if "self.registry.capability_summary(" in status_summary:
            violations.append(
                "AgentRuntime.status_summary must read ToolRegistry summary through "
                "runtime.tool_manifest.snapshot instead of direct registry access"
            )
        if not status_summary_snapshot or "runtime.status_summary.snapshot" not in status_summary_snapshot:
            violations.append(
                "AgentRuntime._status_summary_snapshot_via_tool_graph must execute "
                "runtime.status_summary.snapshot"
            )

    if not provider_status:
        violations.append("AgentRuntime.provider_status not found")
    else:
        for forbidden in ('"user_report_generated"', "_persist_user_report", 'event_type="report_ready"'):
            if forbidden in provider_status:
                violations.append(f"AgentRuntime.provider_status must stay read-only for reports: found {forbidden}")
        for required in (
            "runtime_provider_status_queried",
            "_provider_status_snapshot_via_tool_graph",
        ):
            if required not in provider_status:
                violations.append(f"AgentRuntime.provider_status missing Runtime provider fact token: {required}")
        if not provider_status_snapshot or "runtime.resource_status.snapshot" not in provider_status_snapshot:
            violations.append(
                "AgentRuntime._provider_status_snapshot_via_tool_graph must execute "
                "runtime.resource_status.snapshot"
            )

    if not gm_summary:
        violations.append("AgentRuntime.gm_summary not found")
    else:
        for forbidden in ('"user_report_generated"', "_persist_user_report", 'event_type="report_ready"'):
            if forbidden in gm_summary:
                violations.append(f"AgentRuntime.gm_summary must stay read-only for reports: found {forbidden}")
        for required in (
            "status_summary(",
            "_gm_summary_snapshot_via_tool_graph",
	            "runtime_gm_summary_exported",
	            "context_digest",
	            "agent_contributions",
	            "intervention_digest",
	            "intervention_pending_count",
            "intervention_accepted_count",
            "intervention_deferred_count",
            "batch_tooling_summary",
            "batch_tooling_digest",
            "created_batch_count",
            "prioritized_item_count",
            "merged_intervention_item_count",
            "absorbed_intervention_count",
            "batch_resource_flow_summary",
            "resource_flow_digest",
            "resource_batch_count",
            "resource_failed_count",
            "resource_waiting_count",
            "tool_queue_health_summary",
            "tool_queue_health_digest",
            "queue_pressure",
            "active_count",
            "blocked_count",
            "state_patch_summary",
            "state_patch_digest",
            "reconcile_pending_count",
            "tool_failure_strategy_summary",
            "tool_failure_strategy_digest",
            "retry_scheduled_count",
            "abandoned_late_result_count",
            "stopped_by_runtime_command_count",
            "runtime_guard_replay_summary",
            "runtime_guard_digest",
            "high_risk_confirmation_required_count",
            "write_confirmation_required_count",
            "system_actor_write_blocked_count",
            "user_visible_blocked_event_count",
            "scene_plan_lifecycle_summary",
            "scene_plan_lifecycle_digest",
            "created_count",
            "confirmed_count",
            "state_persist_failed_count",
            "status_persist_failed_count",
            "vlm_checkpoint_summary",
            "vlm_checkpoint_digest",
            "checkpoint_count",
            "checkpoint_counts",
            "review_advisory_replay_summary",
            "review_advisory_replay_digest",
            "proposal_created_count",
            "confirmation_count",
            "advisory_item_count",
            "scene_design_contract_summary",
            "scene_design_contract_digest",
            "scene_design_contract_available",
            "scene_design_contract_scene_type",
            "scene_design_contract_environment_type",
            "scene_type",
            "environment_type",
            "terrain_type",
            "boundary_type",
            "semantic_arbitration_summary",
            "semantic_arbitration_digest",
		            "semantic_arbitration_state",
		            "semantic_arbitration_requires_host_confirmation",
		            "arbitration_state",
		            "execution_readiness",
		            "requires_host_confirmation",
		            "needs_clarification",
            "scene_snapshot_summary",
            "scene_snapshot_digest",
            "scene_snapshot_count",
            "scene_observed_actor_count",
            "resource_summary",
            "resource_stage_digest",
            "resource_event_count",
            "import_summary",
            "import_stage_digest",
            "imported_actor_count",
            "import_failed_count",
            "geometry_fact_summary",
            "geometry_fact_digest",
            "geometry_fact_count",
            "geometry_overlap_issue_count",
            "aabb_actor_count",
            "overlap_issue_count",
		            "tool_execution_summary",
		            "tool_execution_digest",
		            "tool_execution_attention_required",
	            "tool_execution_failed_count",
	            "tool_execution_blocked_count",
	            "attention_required",
	            "attention_reasons",
	            "engine_write_summary",
            "engine_write_digest",
            "import_result_count",
            "transform_result_count",
            "message_delivery_summary",
            "message_delivery_digest",
            "requested_count",
            "succeeded_count",
            "failed_count",
            "sync_health_digest",
            "sync_health_status",
            "sync_replay_summary",
            "asset_transfer_replay_summary",
            "peer_sync_replay_summary",
            "runtime_event_replay_summary",
            "sync_replay_digest",
            "runtime_event_replay_digest",
            "disclosure_skipped_count",
            "asset_transfer_progress_count",
            "peer_asset_ready_count",
            "sync_reconcile_count",
        ):
            if required not in gm_summary:
                violations.append(f"AgentRuntime.gm_summary missing Runtime GM summary token: {required}")
        if not gm_summary_snapshot or "runtime.gm_summary.snapshot" not in gm_summary_snapshot:
            violations.append(
                "AgentRuntime._gm_summary_snapshot_via_tool_graph must execute "
                "runtime.gm_summary.snapshot"
            )

    if not handle_message:
        violations.append("AgentRuntime.handle_message not found")
    else:
        if "_runtime_events_snapshot_via_tool_graph" not in handle_message:
            violations.append(
                "AgentRuntime.handle_message runtime_events action must snapshot "
                "user-visible event feed before returning it"
            )
        if not runtime_events_snapshot or "runtime.events.snapshot" not in runtime_events_snapshot:
            violations.append(
                "AgentRuntime._runtime_events_snapshot_via_tool_graph must execute "
                "runtime.events.snapshot"
            )
        if "_sync_status_snapshot_via_tool_graph" not in handle_message:
            violations.append(
                "AgentRuntime.handle_message sync_status action must snapshot "
                "sync status before returning it"
            )
        for required in (
            'engine_write_summary = dict(provider_status.get("engine_write_summary") or {})',
            '"engine_write_summary": engine_write_summary',
        ):
            if required not in handle_message:
                violations.append(f"AgentRuntime.handle_message engine_write_status missing replay token: {required}")
        for required in (
            '"asset_transfer_replay_summary": asset_transfer_replay',
            '"asset_transfer_started_count": int(asset_transfer_replay.get("asset_transfer_started_count") or 0)',
            '"asset_transfer_progress_count": int(asset_transfer_replay.get("asset_transfer_progress_count") or 0)',
            '"asset_transfer_completed_count": int(asset_transfer_replay.get("asset_transfer_completed_count") or 0)',
            '"asset_transfer_failed_count": int(asset_transfer_replay.get("asset_transfer_failed_count") or 0)',
            '"peer_asset_ready_count": int(asset_transfer_replay.get("peer_asset_ready_count") or 0)',
            '"peer_sync_replay_summary": peer_sync_replay',
            '"peer_event_count": int(peer_sync_replay.get("peer_event_count") or 0)',
            '"sync_reconcile_count": int(peer_sync_replay.get("sync_reconcile_count") or 0)',
            '"state_reconcile_count": int(peer_sync_replay.get("state_reconcile_count") or 0)',
        ):
            if required not in handle_message:
                violations.append(f"AgentRuntime.handle_message sync_status missing transfer/peer token: {required}")
        if not sync_status_snapshot or "runtime.sync_status.snapshot" not in sync_status_snapshot:
            violations.append(
                "AgentRuntime._sync_status_snapshot_via_tool_graph must execute "
                "runtime.sync_status.snapshot"
            )
        for required in (
            'asset_transfer_replay = dict(status.get("asset_transfer_replay_summary") or {})',
            '"asset_transfer_started_count": int(',
            '"asset_transfer_progress_count": int(',
            '"asset_transfer_completed_count": int(',
            '"asset_transfer_failed_count": int(',
            '"peer_asset_ready_count": int(asset_transfer_replay.get("peer_asset_ready_count") or 0)',
            'peer_sync_replay = dict(status.get("peer_sync_replay_summary") or {})',
            '"peer_event_count": int(peer_sync_replay.get("peer_event_count") or 0)',
            '"sync_reconcile_count": int(peer_sync_replay.get("sync_reconcile_count") or 0)',
            '"state_reconcile_count": int(peer_sync_replay.get("state_reconcile_count") or 0)',
        ):
            if required not in sync_status_snapshot:
                violations.append(f"AgentRuntime sync status snapshot missing transfer/peer token: {required}")
        for required in (
            "safe_snapshot = {",
            "_safe_graph_summary_for_user",
            "_safe_graphs_for_user",
            "_safe_queue_result_for_user",
            "_safe_drain_result_for_user",
            '"graph": {"status": graph_status}',
            '"snapshot": safe_snapshot',
            '"graph": {"status": graph_status}',
            '"graph": {"status": ""}',
        ):
            if required not in handle_message:
                violations.append(f"AgentRuntime.handle_message missing user-safe graph return token: {required}")
        forbidden_handle_returns = (
            '"snapshot": snapshot',
            '"graph": graph',
            '"graph": adjustment.get("graph"',
            '"graph": result.get("graph"',
            '"drain": drain_result',
            '"queued": queued',
            '"graphs": queued["graphs"]',
            '"graphs": execution["graphs"]',
        )
        for forbidden in forbidden_handle_returns:
            if forbidden in handle_message:
                violations.append(f"AgentRuntime.handle_message must not return raw graph payloads: found {forbidden}")

    if not execute_scene_plan:
        violations.append("AgentRuntime.execute_scene_plan not found")
    else:
        for required in (
            "include_debug_graph_nodes: bool = False",
            "graph_result = {",
            '"node_count": len(graph.nodes) if graph else 0',
            "if include_debug_graph_nodes:",
            'graph_result["nodes"] = {key: call.as_dict() for key, call in graph.nodes.items()} if graph else {}',
            '"queued": self._safe_queue_result_for_user(queued)',
            '"drain": self._safe_drain_result_for_user(drain_result)',
        ):
            if required not in execute_scene_plan:
                violations.append(f"AgentRuntime.execute_scene_plan missing safe graph return token: {required}")
        if execute_scene_plan.find("if include_debug_graph_nodes:") > execute_scene_plan.find('graph_result["nodes"] = {key: call.as_dict()'):
            violations.append(
                "AgentRuntime.execute_scene_plan must only return graph nodes after include_debug_graph_nodes guard"
            )
    for name, body in (
        ("enqueue_scene_plan", enqueue_scene_plan),
        ("enqueue_planned_batches", enqueue_planned_batches),
        ("enqueue_pending_intervention_batch", enqueue_pending_intervention_batch),
    ):
        if not body:
            violations.append(f"AgentRuntime.{name} not found")
            continue
        if "_build_batch_execution_graph(" not in body:
            violations.append(f"AgentRuntime.{name} must build formal batch execution graphs")
        if "_build_mock_graph(" in body:
            violations.append(f"AgentRuntime.{name} must not call legacy mock graph builder")
    if "def _build_mock_graph(" in source:
        violations.append("AgentRuntime must not keep legacy _build_mock_graph compatibility wrapper")
    if not build_batch_execution_graph:
        violations.append("AgentRuntime._build_batch_execution_graph not found")
    for forbidden in (
        "def _register_default_mock_tools(",
        "def _mock_import_actor(",
        '"mock.import_actor"',
        "'mock.import_actor'",
    ):
        if forbidden in source:
            violations.append(f"AgentRuntime default Runtime tool path must not expose mock import token: {forbidden}")

    if violations:
        print("[FAIL] static Runtime report fact-source gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static Runtime report fact-source gate")
    return True


def _runtime_validator_contract_gate() -> bool:
    print("[RUN] static Runtime validator contract gate")
    core_path = REPO_ROOT / AGENT_RUNTIME_CORE
    try:
        source = core_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = core_path.read_text(encoding="utf-8-sig")
    tools_path = REPO_ROOT / AGENT_RUNTIME_TOOLS
    try:
        tools_source = tools_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        tools_source = tools_path.read_text(encoding="utf-8-sig")
    test_path = REPO_ROOT / LANCHAT_RUNTIME_GUARD_TESTS
    try:
        test_source = test_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        test_source = test_path.read_text(encoding="utf-8-sig")
    phase1_test_path = REPO_ROOT / AGENT_RUNTIME_PHASE1_TESTS
    try:
        phase1_test_source = phase1_test_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        phase1_test_source = phase1_test_path.read_text(encoding="utf-8-sig")
    violations: list[str] = []

    for validator in sorted(REQUIRED_RUNTIME_VALIDATORS):
        if f"class {validator}" not in source:
            violations.append(f"missing required Runtime schema validator: {validator}")

    execute = _function_source(source, "execute")
    apply_patch = _function_source(source, "apply_patch")
    generate_report = _function_source(source, "generate_report")
    persist_graph = _function_source(source, "_persist_graph")
    persist_user_report = _function_source(source, "_persist_user_report")
    persist_user_report_tool = _function_source(source, "_persist_user_report_tool")
    apply_layout_delta_tool = _function_source(source, "_apply_layout_delta_tool")

    required_execute_tokens = (
        "ToolCallGraphValidator.validate(graph, self.registry)",
        "self.guard.authorize(call, definition)",
        "ToolCallValidator._validate_runtime_fact_arg_tree",
        "ToolResultValidator.validate_for_tool",
    )
    for token in required_execute_tokens:
        if token not in execute:
            violations.append(f"ToolCallGraphExecutor.execute missing validation/guard token: {token}")
    if "ToolCallGraphValidator.safe_graph_fact" not in persist_graph:
        violations.append("ToolCallGraphExecutor._persist_graph must persist only safe ToolCallGraph facts")

    required_apply_patch_tokens = (
        "StatePatchValidator.validate",
        "ScenePlanValidator.validate_plans",
        "BatchPlanValidator.validate_plans",
        "ToolCallGraphValidator.validate_graph_facts",
        "ToolCallGraphValidator.validate_queue_items",
        "AdjustmentProposalValidator.validate",
        "ReviewAdvisoryProposalValidator.validate",
        "ReportRecordValidator.validate_reports",
    )
    for token in required_apply_patch_tokens:
        if token not in apply_patch and token not in source:
            violations.append(f"RuntimeState.apply_patch path missing validator token: {token}")

    if "_persist_user_report(" not in generate_report:
        violations.append("AgentRuntime.generate_report must persist reports through the Runtime tool path")
    for required in (
        "_batch_tooling_summary_for_plan(",
        '"batch_tooling_summary": batch_tooling_summary',
        "_tool_queue_health_summary_for_plan(",
        '"tool_queue_health_summary": tool_queue_health_summary',
        "_batch_resource_flow_summary_for_plan(",
        '"batch_resource_flow_summary": batch_resource_flow_summary',
        "_geometry_fact_summary_for_plan(",
        '"geometry_fact_summary": geometry_fact_summary',
        '"geometry_fact_replay_summary": dict(',
    ):
        if required not in generate_report:
            violations.append(f"AgentRuntime.generate_report missing Runtime queue/batch summary token: {required}")
    batch_resource_flow_summary = _function_source(source, "_batch_resource_flow_summary_for_plan")
    if '"ready_count" in import_fact' not in batch_resource_flow_summary:
        violations.append("AgentRuntime batch resource flow must preserve explicit import ready_count=0")
    if 'import_fact.get("ready_count") or import_fact.get("actor_count")' in batch_resource_flow_summary:
        violations.append("AgentRuntime batch resource flow must not coerce ready_count=0 to actor_count")
    if "runtime.user_report.persist" not in persist_user_report or "executor.execute(graph" not in persist_user_report:
        violations.append("AgentRuntime._persist_user_report must use ToolCallGraphExecutor")
    if "ReportRecordValidator.validate(report)" not in persist_user_report_tool:
        violations.append("runtime.user_report.persist must validate ReportRecord before StatePatch persistence")
    for token in (
        "_layout_support_type(actor)",
        "_shift_actor_aabb(",
        "_snap_actor_bottom_to_ground_if_supported(",
    ):
        if token not in apply_layout_delta_tool:
            violations.append(f"runtime.layout.apply_delta missing selective grounding token: {token}")
    for helper in (
        "def _batch_tooling_summary_for_plan(",
        "def _batch_resource_flow_summary_for_plan(",
        "def _tool_queue_health_summary_for_plan(",
        "def _geometry_fact_summary_for_plan(",
        "def _geometry_fact_replay_summary(",
        "def _summarize_geometry_facts_for_replay(",
        "def _layout_support_type(",
        "def _shift_actor_aabb(",
        "def _snap_actor_bottom_to_ground_if_supported(",
    ):
        if helper not in source:
            violations.append(f"AgentRuntime missing Agent-native Runtime helper: {helper}")
    for test_name in (
        "test_runtime_cpp_bridge_success_payload_is_narrow_and_sanitized",
        "test_runtime_cpp_bridge_failure_message_is_sanitized",
        "test_runtime_cpp_bridge_missing_gate_method_is_stable",
        "test_runtime_tool_manifest_exposes_engine_plane_tools_without_internals",
    ):
        if test_name not in test_source:
            violations.append(f"RuntimeCppBridge boundary missing regression test: {test_name}")
    for required_tool in (
        "runtime.environment.import_components",
        "runtime.actor.import_batch",
        "runtime.layout.apply_delta",
        "runtime.actor.mark_deleted",
    ):
        if required_tool not in test_source:
            violations.append(f"Runtime tool manifest regression missing engine-plane tool: {required_tool}")
    for test_name in (
        "test_runtime_guard_blocks_unconfirmed_high_risk_tool",
        "test_runtime_guard_blocks_unconfirmed_low_risk_write_tool",
        "test_runtime_guard_uses_tool_definition_requires_write_even_when_call_omits_it",
        "test_runtime_guard_blocks_confirmed_system_actor_write_by_actor_id",
        "test_runtime_guard_blocks_nested_system_actor_write_reference",
        "test_runtime_guard_system_actor_ref_matches_room_and_terrain_without_false_sky_prefix",
        "test_tool_definition_default_high_risk_requires_confirmation",
    ):
        if test_name not in phase1_test_source:
            violations.append(f"RuntimeGuard boundary missing regression test: {test_name}")
    for test_name in REQUIRED_STATE_PATCH_CONFLICT_TESTS:
        if test_name not in phase1_test_source:
            violations.append(f"RuntimeState StatePatch conflict/reconcile missing regression test: {test_name}")
    for tool_name in (
        "runtime.queue.plan_enqueue_items",
        "runtime.geometry.compute_aabb",
        "runtime.geometry.check_overlap",
    ):
        if tool_name not in tools_source:
            violations.append(f"AgentRuntime required Runtime tool missing: {tool_name}")
    for token in (
        "def _failed_resource_entries(",
        "image_resource_unavailable",
        "model_resource_unavailable",
        'plan_status = "failed"',
        'plan_status = "partial"',
        '"runtime.actor.import_batch"',
        'produces_state=("actors", "custom_import_facts")',
        "def _actor_import_result_fact(",
        "actor import skipped and failed resource fact recorded",
        "actor import failed and result fact recorded",
        "runtime_actor_import_result",
        ':actor_import_result',
    ):
        if token not in tools_source:
            violations.append(f"AgentRuntime resource provider result handling missing token: {token}")
    if "without calling providers" in tools_source:
        violations.append("AgentRuntime resource tool manifest must not claim providers are never called")
    for token in (
        "def _plan_queue_items_via_tool_graph(",
        "runtime.queue.plan_enqueue_items",
        "queue_item_plan_tool_failed",
    ):
        if token not in source:
            violations.append(f"AgentRuntime enqueue_planned_batches missing queue planning token: {token}")
    forbidden_runtime_tool_manifest_tokens = (
        "legacy.scene_compose",
        "legacy.progressive_compose",
        "legacy.workflow_orchestrator",
        "SceneComposer.compose",
        "ProgressiveWorkflow",
        "run_progressive_workflow",
    )
    forbidden_runtime_tool_manifest_phrases = (
        "mock.import_actor",
        "mock actor import",
        "mock import",
    )
    try:
        tools_tree = ast.parse(tools_source)
    except SyntaxError as exc:
        violations.append(f"agent_runtime/tools.py could not be parsed for manifest safety: {exc}")
        tools_tree = None
    if tools_tree is not None:
        for node in ast.walk(tools_tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "register":
                continue
            tool_name = ""
            if node.args and isinstance(node.args[0], ast.Constant):
                tool_name = str(node.args[0].value or "")
            description = ""
            for keyword in node.keywords:
                if keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                    description = str(keyword.value.value or "")
                    break
            manifest_text = f"{tool_name} {description}"
            for token in forbidden_runtime_tool_manifest_tokens:
                if token in manifest_text:
                    violations.append(
                        "AgentRuntime tool registry exposes legacy main-control token "
                        f"{token!r} in manifest entry {tool_name!r}"
                    )
            lowered_manifest_text = manifest_text.lower()
            for phrase in forbidden_runtime_tool_manifest_phrases:
                if phrase in lowered_manifest_text:
                    violations.append(
                        "AgentRuntime tool registry exposes mock import phrase "
                        f"{phrase!r} in manifest entry {tool_name!r}"
                    )
    for test_name in (
        "test_queue_enqueue_item_planning_tool_records_safe_drafts_without_persisting_queue",
        "test_tool_definition_rejects_legacy_workflow_main_control_tools",
        "test_tool_registry_manifest_does_not_expose_legacy_workflow_main_control_tools",
        "test_empty_resource_provider_result_records_failed_resource_facts",
        "test_empty_model_resource_provider_result_records_failed_resource_facts",
    ):
        if test_name not in phase1_test_source:
            violations.append(f"legacy main-control manifest boundary missing regression test: {test_name}")
    for test_name in REQUIRED_PHASE6_GEOMETRY_TOOL_TESTS:
        if test_name not in phase1_test_source:
            violations.append(f"Phase 6 geometry tool missing regression test: {test_name}")

    if violations:
        print("[FAIL] static Runtime validator contract gate")
        for item in violations:
            print(f"       {item}")
        return False
    print("[OK]  static Runtime validator contract gate")
    return True


def main() -> int:
    checks: list[tuple[str, list[str]]] = []

    for path in PYTHON_TESTS:
        checks.append((path, [sys.executable, path]))

    for path in NODE_TESTS:
        checks.append((path, ["node", path]))

    failed = 0
    for label, command in checks:
        if not _run(label, command):
            failed += 1

    if not _syntax_check(PY_COMPILE_TARGETS):
        failed += 1

    if not _direct_scene_compose_entry_gate():
        failed += 1

    if not _direct_engine_write_entry_gate():
        failed += 1

    if not _direct_progressive_workflow_entry_gate():
        failed += 1

    if not _direct_generation_scheduler_entry_gate():
        failed += 1

    if not _direct_host_action_executor_entry_gate():
        failed += 1

    if not _host_action_executor_policy_gate():
        failed += 1

    if not _agent_runtime_flag_boundary_gate():
        failed += 1

    if not _runtime_state_apply_patch_boundary_gate():
        failed += 1

    if not _workflow_command_exposure_gate():
        failed += 1

    if not _runtime_report_fact_source_gate():
        failed += 1

    if not _runtime_validator_contract_gate():
        failed += 1

    if failed:
        print(f"[SUMMARY] {failed} non-native check(s) failed.")
        return 1

    print("[SUMMARY] All current Agent-native non-native checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
