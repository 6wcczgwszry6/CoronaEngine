#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
One-click build script (Windows friendly):
1) Ensure Python dependencies in requirements.txt are installed (install missing ones automatically).
2) Use the bundled Node/npm under Env\node-v22.19.0-win-x64 to run `npm install` and `npm run build` in Frontend.

Run:
        python build.py

Notes:
- Auto-detects `uv` and uses it for Python dependency management when available.
- USE_UV_PIP = None (default): auto-detect uv; True: force uv; False: force standard pip.
- Uses the local npm at Env\node-v22.19.0-win-x64\npm.cmd and sets PATH accordingly.
"""

from __future__ import annotations

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

# ============================================================
# Configuration: Choose pip tool
# ============================================================
# None  = auto-detect: use 'uv' if found in PATH, otherwise fall back to standard pip
# True  = force 'uv pip'
# False = force standard 'python -m pip'
USE_UV_PIP: Optional[bool] = None

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"
FRONTEND_DIR = ROOT / "Frontend"

if sys.platform == "win32":
    NODE_DIR = ROOT / "Env" / "node-v22.19.0-win-x64"
    NPM_CMD = NODE_DIR / "npm.cmd"
else:
    NODE_DIR = ROOT / "Env" / "node-v20.19.0-linux-x64"
    NPM_CMD = NODE_DIR / "bin" / "npm"


def _is_uv_available() -> bool:
    """Return True if the `uv` executable is reachable in PATH."""
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _print_header(title: str) -> None:
    line = "=" * 60
    print(f"\n{line}\n{title}\n{line}")


def _run(cmd: List[str], cwd: Optional[Path] = None, env: Optional[dict] = None) -> int:
    """Run a command and stream output. Returns process return code."""
    print(f"$ {' '.join([str(c) for c in cmd])}")
    if cwd:
        print(f"  (cwd: {cwd})")
    try:
        proc = subprocess.run(
            [str(c) for c in cmd],
            cwd=str(cwd) if cwd else None,
            env=env,
            check=False,
        )
        return proc.returncode
    except FileNotFoundError as e:
        print(f"ERROR: Command not found: {cmd[0]} -> {e}")
        return 127


def _parse_requirement_name(req_line: str) -> Optional[str]:
    """Extract base package name from a requirement line for `pip show` check.

    - Keeps extras (in install), but `pip show` should be given the base name without extras/version.
    - Handles comments and whitespace. Returns None if the line is ignorable.
    """
    line = req_line.strip()
    if not line or line.startswith("#"):
        return None
    # Remove inline comments: e.g., "package # comment"
    if " #" in line:
        line = line.split(" #", 1)[0].strip()
    # PEP 508 direct URLs, editable installs, or local paths are out of scope – just install directly later
    if any(line.startswith(prefix) for prefix in ("-e ", "git+", "http://", "https://", "file:")):
        # return a best-effort name for `pip show` (None forces install)
        return None
    # Strip extras and version specifiers for show-check: name[extras]==1.2.3 -> name
    # Name can contain hyphens/underscores and dots; stop at first of these spec chars: [<>=!~@;,
    m = re.match(r"^[A-Za-z0-9_.\-]+", line)
    return m.group(0) if m else None


def ensure_python_requirements(requirements_file: Path = REQUIREMENTS) -> None:
    _print_header("Step 1: Ensuring Python requirements are installed")

    # Determine pip command: respect explicit override, or auto-detect uv
    use_uv: bool
    if USE_UV_PIP is None:
        use_uv = _is_uv_available()
        if use_uv:
            print("Auto-detected uv. Using pip tool: uv")
        else:
            print("uv not found. Using pip tool: standard pip")
    elif USE_UV_PIP:
        use_uv = True
        print("Using pip tool: uv (forced by USE_UV_PIP)")
    else:
        use_uv = False
        print("Using pip tool: standard pip (forced by USE_UV_PIP)")

    if use_uv:
        pip_cmd_base = ["uv", "pip"]
    else:
        pip_cmd_base = [sys.executable, "-m", "pip"]

    if not requirements_file.exists():
        print(f"WARNING: {requirements_file} not found. Skipping Python dependency installation.")
        return

    lines = requirements_file.read_text(encoding="utf-8").splitlines()
    missing: List[str] = []
    for raw in lines:
        base_name = _parse_requirement_name(raw)
        if base_name is None:
            # Can't reliably `pip show`; defer to install step
            # Keep original line for install to preserve extras/specifiers
            if raw.strip() and not raw.strip().startswith("#"):
                missing.append(raw.strip())
            continue
        # Check if installed
        rc = _run(pip_cmd_base + ["show", base_name])
        if rc != 0:
            missing.append(raw.strip())

    if not missing:
        print("All Python requirements appear to be installed.")
        return

    print("Missing or unverified packages detected. Installing:")
    for req in missing:
        print(f"  - {req}")

    # Install missing individually to keep progress visible; if this is too slow, fallback to -r file
    for req in missing:
        rc = _run(pip_cmd_base + ["install", req])
        if rc != 0:
            print(
                f"ERROR: Failed to install '{req}'. You may retry or run: \
{' '.join(pip_cmd_base)} install -r {requirements_file}"
            )
            sys.exit(rc)


def clone_inner_agent_workflow(repo_url: str, target_dir: Path) -> None:
    """Clone the InnerAgent workflow repository if InnerAgentWorkFlow is enabled."""
    _print_header("Step 1.5: Cloning InnerAgent Workflow Repository")

    # Check if git is available
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print("ERROR: git is not installed or not in PATH. Please install git first.")
            sys.exit(1)
    except FileNotFoundError:
        print("ERROR: git is not installed or not in PATH. Please install git first.")
        sys.exit(1)

    # Check if target directory already exists
    if target_dir.exists():
        print(f"Target directory already exists: {target_dir}")
        # Check if it's a git repository
        if (target_dir / ".git").exists():
            print("Directory is already a git repository. Pulling latest changes...")
            rc = _run(["git", "pull"], cwd=target_dir)
            if rc != 0:
                print("WARNING: 'git pull' failed. Continuing anyway...")
            else:
                print("Successfully updated repository.")
        else:
            print("WARNING: Directory exists but is not a git repository. Skipping clone.")
        return

    # Create parent directory if needed
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    # Clone the repository
    print(f"Cloning from {repo_url} to {target_dir}...")
    rc = _run(["git", "clone", repo_url, str(target_dir)])
    if rc != 0:
        print(f"ERROR: Failed to clone repository from {repo_url}")
        sys.exit(rc)

    print(f"Successfully cloned InnerAgent workflow to {target_dir}")


def build_frontend(
    frontend_dir: Path = FRONTEND_DIR, node_dir: Path = NODE_DIR, npm_cmd: Path = NPM_CMD
) -> None:
    _print_header("Step 2: Installing and building Frontend with bundled Node/npm")
    if not frontend_dir.exists():
        print(f"ERROR: Frontend directory not found: {frontend_dir}")
        sys.exit(1)

    if os.name == "nt":
        # Prefer the local npm.cmd
        if not npm_cmd.exists():
            print(f"ERROR: npm not found at {npm_cmd}. Ensure Node is present under {node_dir}.")
            sys.exit(1)
        npm = str(npm_cmd)
    else:
        # Non-Windows (just in case): try local npm first
        npm = str(npm_cmd) if npm_cmd.exists() else "npm"

    env = os.environ.copy()
    # Prepend node_dir (or bin) to PATH to ensure the bundled node executable is used
    if sys.platform == "win32":
        node_bin = node_dir
    else:
        node_bin = node_dir / "bin"

    env["PATH"] = str(node_bin) + os.pathsep + env.get("PATH", "")

    # npm install
    rc = _run([npm, "install"], cwd=frontend_dir, env=env)
    if rc != 0:
        print("ERROR: 'npm install' failed.")
        sys.exit(rc)

    # npm run build (use script defined in package.json)
    rc = _run([npm, "run", "build"], cwd=frontend_dir, env=env)
    if rc != 0:
        print("ERROR: 'npm run build' failed.")
        sys.exit(rc)

    print("Frontend build completed successfully.")


def main() -> None:
    # Step 1: Ensure Python requirements
    ensure_python_requirements(REQUIREMENTS)

    # Step 2: Build frontend
    build_frontend(FRONTEND_DIR, NODE_DIR, NPM_CMD)

    _print_header("Done")
    print("All steps finished successfully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Aborted by user.")
        sys.exit(130)
