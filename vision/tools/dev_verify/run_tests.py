"""Discover and run test-* executables from the build directory.

Usage:
    python run_tests.py                         # run all test-* executables
    python run_tests.py --filter bxdf half      # only matching tests
    python run_tests.py --exclude gui vulkan    # skip tests containing these words
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Tests that require a GPU/window and should be excluded by default in headless mode
DEFAULT_EXCLUDE = ["gui", "vulkan"]


def _find_vcvarsall() -> str | None:
    """Auto-detect vcvarsall.bat via vswhere, fall back to common paths."""
    vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / \
              "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if vswhere.exists():
        result = subprocess.run(
            [str(vswhere), "-latest", "-products", "*",
             "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
             "-property", "installationPath"],
            capture_output=True, text=True
        )
        vs_path = result.stdout.strip()
        if vs_path:
            candidate = Path(vs_path) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
            if candidate.exists():
                return str(candidate)
    for edition in ("Community", "Professional", "Enterprise"):
        for year in ("2022", "2019"):
            candidate = Path(rf"C:\Program Files\Microsoft Visual Studio\{year}\{edition}"
                             r"\VC\Auxiliary\Build\vcvarsall.bat")
            if candidate.exists():
                return str(candidate)
    return None


def ensure_targets_built(build_dir: Path, targets: list[str]) -> None:
    """Build required test targets before discovery/execution."""
    if not targets:
        return

    vcvarsall = _find_vcvarsall()
    if not vcvarsall:
        sys.exit("ERROR: vcvarsall.bat not found. Install Visual Studio with C++ workload.")

    build_dir = build_dir.resolve()
    cmd = f'call "{vcvarsall}" x64 >nul 2>&1 && ninja -C "{build_dir}" ' + " ".join(targets)
    print(f"Ensuring test targets are built: {' '.join(targets)}")
    result = subprocess.run(cmd, cwd=find_project_root(), shell=True)
    if result.returncode != 0:
        sys.exit(f"ERROR: failed to build required test targets: {' '.join(targets)}")
    print()


def find_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "CMakeLists.txt").exists() and (parent / "src").is_dir():
            return parent
    sys.exit("ERROR: cannot locate Vision project root")


def discover_tests(bin_dir: Path, filter_words: list[str] | None,
                   exclude_words: list[str] | None,
                   exact_tests: list[str] | None) -> list[Path]:
    """Find test-*.exe in bin_dir, applying optional filters."""
    tests = []
    exact_set = set(exact_tests or [])
    for f in sorted(bin_dir.glob("test-*.exe")):
        name = f.stem  # e.g. "test-bxdf"
        if exact_set and name not in exact_set:
            continue
        if filter_words and not any(w in name for w in filter_words):
            continue
        if exclude_words and any(w in name for w in exclude_words):
            continue
        tests.append(f)
    return tests


def run_test(exe: Path, timeout: int) -> tuple[bool, str]:
    """Run a single test executable. Returns (passed, detail)."""
    try:
        env = os.environ.copy()
        env["PATH"] = str(exe.parent) + os.pathsep + env.get("PATH", "")
        result = subprocess.run(
            [str(exe)],
            capture_output=True, text=True, timeout=timeout,
            cwd=exe.parent, env=env,
        )
        if result.returncode == 0:
            return True, "OK"
        else:
            last_lines = result.stdout.strip().split("\n")[-3:]
            stderr_lines = result.stderr.strip().split("\n")[-3:]
            detail = "\n".join(last_lines + stderr_lines).strip()
            return False, f"exit code {result.returncode}: {detail}"
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT ({timeout}s)"
    except OSError as e:
        return False, f"OS error: {e}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run unit tests")
    parser.add_argument("--build-dir", type=str, default=None,
                        help="Build directory (default: cmake-build-release)")
    parser.add_argument("--filter", nargs="*", default=None,
                        help="Only run tests containing these words")
    parser.add_argument("--exclude", nargs="*", default=None,
                        help=f"Exclude tests containing these words (default: {DEFAULT_EXCLUDE})")
    parser.add_argument("--tests", nargs="*", default=None,
                        help="Run only these exact test executable stem names")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Per-test timeout in seconds (default: 120)")
    parser.add_argument("--include-gpu", action="store_true",
                        help="Include GPU/GUI tests (normally excluded)")
    parser.add_argument("--ensure-targets", nargs="*", default=None,
                        help="Build these targets before discovering/running tests")
    args = parser.parse_args()

    project_root = find_project_root()
    build_dir = Path(args.build_dir) if args.build_dir else project_root / "cmake-build-release"
    bin_dir = build_dir / "bin"

    if not bin_dir.is_dir():
        sys.exit(f"ERROR: bin directory not found: {bin_dir}")

    ensure_targets_built(build_dir, args.ensure_targets or [])

    exclude = args.exclude if args.exclude is not None else ([] if args.include_gpu else DEFAULT_EXCLUDE)
    tests = discover_tests(bin_dir, args.filter, exclude, args.tests)

    if not tests:
        sys.exit("ERROR: no matching tests found")

    print(f"Running {len(tests)} test(s) from {bin_dir}")
    if exclude:
        print(f"  excluding: {exclude}")
    print()

    passed = 0
    failed = []
    for exe in tests:
        ok, detail = run_test(exe, args.timeout)
        tag = "PASS" if ok else "FAIL"
        print(f"  {tag}  {exe.stem:<30s}  {detail if not ok else ''}")
        if ok:
            passed += 1
        else:
            failed.append((exe.stem, detail))

    print()
    print(f"Results: {passed} passed, {len(failed)} failed out of {len(tests)}")

    # Write report
    report_path = Path(__file__).resolve().parent / "report_unit_tests.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Unit Test Report\n\n")
        f.write(f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Build Dir**: {build_dir}\n")
        f.write(f"- **Total**: {len(tests)}, **Passed**: {passed}, **Failed**: {len(failed)}\n\n")
        f.write(f"| Test | Result | Detail |\n")
        f.write(f"|------|--------|--------|\n")
        for exe_path in tests:
            fail_entry = next((d for n, d in failed if n == exe_path.stem), None)
            status = "FAIL" if fail_entry else "PASS"
            detail = fail_entry or ""
            f.write(f"| {exe_path.stem} | {status} | {detail} |\n")
        f.write(f"\n**Summary**: {passed} passed, {len(failed)} failed out of {len(tests)}\n")
    print(f"Report: {report_path}")

    if failed:
        print("\nFailed tests:")
        for name, detail in failed:
            print(f"  {name}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
