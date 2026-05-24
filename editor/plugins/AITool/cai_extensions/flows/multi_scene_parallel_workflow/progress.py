"""
ParallelProgressTracker — 线程安全的子场景进度聚合器

MVP 粒度：只追踪场景级完成/失败，不追踪内部节点细节。
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List


class ParallelProgressTracker:
    """线程安全的并行任务进度追踪器。"""

    def __init__(self, total_scenes: int):
        self._lock = threading.Lock()
        self.total = total_scenes
        self.completed = 0
        self.failed = 0
        self._scenes: Dict[str, Dict[str, Any]] = {}
        self._start_time = time.time()

    def mark_started(self, scene_name: str) -> None:
        with self._lock:
            self._scenes[scene_name] = {
                "status": "running",
                "started_at": time.time(),
            }

    def mark_completed(self, scene_name: str) -> None:
        with self._lock:
            self.completed += 1
            entry = self._scenes.get(scene_name, {})
            entry["status"] = "success"
            entry["elapsed"] = time.time() - entry.get("started_at", self._start_time)
            self._scenes[scene_name] = entry

    def mark_failed(self, scene_name: str, error: str) -> None:
        with self._lock:
            self.completed += 1
            self.failed += 1
            entry = self._scenes.get(scene_name, {})
            entry["status"] = "failed"
            entry["error"] = error
            entry["elapsed"] = time.time() - entry.get("started_at", self._start_time)
            self._scenes[scene_name] = entry

    @property
    def overall_progress(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total": self.total,
                "completed": self.completed,
                "failed": self.failed,
                "pending": self.total - self.completed,
                "elapsed": time.time() - self._start_time,
                "scenes": dict(self._scenes),
            }

    def summary(self) -> str:
        p = self.overall_progress
        succeeded = [n for n, s in p["scenes"].items() if s["status"] == "success"]
        failed = [(n, s.get("error", "unknown"))
                   for n, s in p["scenes"].items() if s["status"] == "failed"]
        parts: List[str] = [f"完成 {p['completed']}/{p['total']}"]
        if succeeded:
            parts.append("成功: " + ", ".join(succeeded))
        if failed:
            parts.append("失败: " + ", ".join(f"{n}({e})" for n, e in failed))
        parts.append(f"耗时 {p['elapsed']:.0f}s")
        return " | ".join(parts)
