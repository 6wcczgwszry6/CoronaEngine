from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from workflow import CommandError, run_command, safe_remove


COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class HorizonLock:
    schema_version: int
    url: str
    ref: str
    commit: str


def load_lock(lock_file: Path) -> HorizonLock:
    try:
        data = json.loads(lock_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read Horizon lock file '{lock_file}': {error}") from error
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid Horizon lock data: {lock_file}")
    lock = HorizonLock(
        schema_version=data.get("schema_version"),
        url=data.get("url", ""),
        ref=data.get("ref", ""),
        commit=data.get("commit", "").lower(),
    )
    if lock.schema_version != 1:
        raise RuntimeError(f"Unsupported Horizon lock schema: {lock.schema_version}")
    if not lock.url or not lock.ref or not COMMIT_PATTERN.fullmatch(lock.commit):
        raise RuntimeError(f"Invalid Horizon lock data: {lock_file}")
    return lock


def _git(worktree: Path, *arguments: str, capture: bool = False) -> str:
    result = run_command(("git", "-C", worktree, *arguments), cwd=worktree.parent, capture_output=capture)
    return result.stdout.strip() if capture else ""


def is_dirty(worktree: Path) -> bool:
    return bool(_git(worktree, "status", "--porcelain", capture=True))


def current_commit(worktree: Path) -> str:
    return _git(worktree, "rev-parse", "HEAD", capture=True).lower()


def _normalized_url(value: str) -> str:
    return value.rstrip("/").removesuffix(".git").lower()


def ensure_workspace(repo_root: Path) -> HorizonLock:
    lock_file = repo_root / ".workspace" / "horizon.lock.json"
    worktree = repo_root / ".workspace" / "Horizon"
    lock = load_lock(lock_file)
    created = False
    if not worktree.exists():
        worktree.parent.mkdir(parents=True, exist_ok=True)
        created = True
        try:
            run_command(("git", "clone", "--no-checkout", lock.url, worktree), cwd=repo_root)
            _git(worktree, "fetch", "--tags", "origin", lock.ref)
            _git(worktree, "cat-file", "-e", f"{lock.commit}^{{commit}}")
            _git(worktree, "checkout", "--detach", lock.commit)
        except Exception:
            if worktree.exists():
                safe_remove(repo_root, worktree)
            raise

    if not (worktree / ".git").exists():
        raise RuntimeError(f"Horizon workspace is not a Git checkout: {worktree}")
    remote_url = _git(worktree, "remote", "get-url", "origin", capture=True)
    if _normalized_url(remote_url) != _normalized_url(lock.url):
        raise RuntimeError(f"Horizon origin is '{remote_url}', expected '{lock.url}'.")
    head = current_commit(worktree)
    if head != lock.commit:
        raise RuntimeError(
            f"Horizon HEAD is {head}, but the lock requires {lock.commit}. "
            "The workflow will not reset local work; restore the locked commit or update the lock explicitly."
        )
    if created:
        print(f"[INFO] Horizon workspace created at {worktree}")
    return lock


def update_workspace(repo_root: Path) -> HorizonLock:
    old_lock = ensure_workspace(repo_root)
    lock_file = repo_root / ".workspace" / "horizon.lock.json"
    worktree = repo_root / ".workspace" / "Horizon"
    if is_dirty(worktree):
        raise RuntimeError("Horizon workspace has local changes; update was refused.")

    _git(worktree, "fetch", "--tags", "origin", old_lock.ref)
    new_commit = _git(worktree, "rev-parse", "FETCH_HEAD", capture=True).lower()
    if new_commit == old_lock.commit:
        print(f"[INFO] Horizon is already locked at {new_commit}")
        return old_lock

    temporary_lock = lock_file.with_suffix(".json.tmp")
    data = {
        "schema_version": 1,
        "url": old_lock.url,
        "ref": old_lock.ref,
        "commit": new_commit,
    }
    temporary_lock.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        _git(worktree, "checkout", "--detach", new_commit)
        temporary_lock.replace(lock_file)
    except Exception:
        if temporary_lock.exists():
            temporary_lock.unlink()
        try:
            _git(worktree, "checkout", "--detach", old_lock.commit)
        except CommandError:
            pass
        raise
    print(f"[INFO] Horizon lock updated: {old_lock.commit} -> {new_commit}")
    return load_lock(lock_file)
