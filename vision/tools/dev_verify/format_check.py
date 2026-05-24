"""Incremental clang-format check on files modified in git diff.

Usage:
    python format_check.py                  # check uncommitted changes
    python format_check.py --base HEAD~3    # check against specific base
    python format_check.py --fix            # auto-fix formatting in place
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CPP_EXTENSIONS = {".cpp", ".h", ".hpp", ".cxx", ".cc", ".hxx", ".inl"}


def find_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "CMakeLists.txt").exists() and (parent / "src").is_dir():
            return parent
    sys.exit("ERROR: cannot locate Vision project root")


def get_changed_files(project_root: Path, base: str) -> list[Path]:
    """Get C++ files changed relative to base ref."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACM", base, "--"],
        capture_output=True, text=True, cwd=project_root,
    )
    if result.returncode != 0:
        # Try without base (unstaged changes)
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, cwd=project_root,
        )

    # Also include staged changes
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, cwd=project_root,
    )

    files = set()
    for line in (result.stdout + "\n" + staged.stdout).strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        p = project_root / line
        if p.suffix in CPP_EXTENSIONS and p.exists():
            files.add(p)

    return sorted(files)


def check_format(file: Path, project_root: Path) -> tuple[bool, str]:
    """Check if a file is properly formatted. Returns (ok, diff_output)."""
    result = subprocess.run(
        ["clang-format", "--style=file", "--dry-run", "--Werror", str(file)],
        capture_output=True, text=True, cwd=project_root,
    )
    if result.returncode == 0:
        return True, ""

    # Get the actual diff for display
    diff_result = subprocess.run(
        ["clang-format", "--style=file", str(file)],
        capture_output=True, text=True, cwd=project_root,
    )
    original = file.read_text(encoding="utf-8", errors="replace")
    if diff_result.stdout == original:
        return True, ""

    return False, result.stderr


def fix_format(file: Path, project_root: Path) -> bool:
    """Apply clang-format in-place."""
    result = subprocess.run(
        ["clang-format", "--style=file", "-i", str(file)],
        capture_output=True, text=True, cwd=project_root,
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Incremental clang-format check")
    parser.add_argument("--base", type=str, default="HEAD",
                        help="Git ref to diff against (default: HEAD)")
    parser.add_argument("--fix", action="store_true",
                        help="Auto-fix formatting in place")
    parser.add_argument("--all", action="store_true",
                        help="Check all C++ files under src/, not just changed ones")
    args = parser.parse_args()

    project_root = find_project_root()

    if args.all:
        src_dir = project_root / "src"
        files = sorted(f for f in src_dir.rglob("*") if f.suffix in CPP_EXTENSIONS)
    else:
        files = get_changed_files(project_root, args.base)

    if not files:
        print("No C++ files to check.")
        return

    print(f"Checking {len(files)} file(s)...")
    print()

    bad_files = []
    for f in files:
        rel = f.relative_to(project_root)
        if args.fix:
            fix_format(f, project_root)
            print(f"  FIXED  {rel}")
        else:
            ok, detail = check_format(f, project_root)
            if ok:
                print(f"  OK     {rel}")
            else:
                print(f"  BAD    {rel}")
                bad_files.append(rel)

    print()
    if args.fix:
        print(f"Fixed {len(files)} file(s).")
    # Write report
    report_path = Path(__file__).resolve().parent / "report_format.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Format Check Report\n\n")
        f.write(f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Files Checked**: {len(files)}\n")
        f.write(f"- **Mode**: {'fix' if args.fix else 'check'}\n\n")
        if args.fix:
            f.write(f"Fixed {len(files)} file(s).\n")
        else:
            f.write(f"| File | Status |\n")
            f.write(f"|------|--------|\n")
            for checked_f in files:
                rel = checked_f.relative_to(project_root)
                status = "BAD" if rel in bad_files else "OK"
                f.write(f"| {rel} | {status} |\n")
            f.write(f"\n**Summary**: {len(files) - len(bad_files)} OK, {len(bad_files)} violations\n")
    print(f"Report: {report_path}")

    if not args.fix and bad_files:
        print(f"Format violations in {len(bad_files)} file(s):")
        for f in bad_files:
            print(f"  {f}")
        print("\nRun with --fix to auto-format.")
        sys.exit(1)
    elif not args.fix:
        print(f"All {len(files)} file(s) properly formatted.")


if __name__ == "__main__":
    main()
