#!/usr/bin/env python3
"""Shared utilities for scene transformation scripts.

Provides JSON loading (with comment stripping), path resolution,
and common canonical-format helpers.
"""

import json
import re
from pathlib import Path
from collections import OrderedDict


# ---------------------------------------------------------------------------
# JSON pre-processing (strip comments, trailing commas)
# ---------------------------------------------------------------------------

def strip_json_comments(text: str) -> str:
    """Remove // and /* */ comments from JSON text."""
    result = []
    i = 0
    n = len(text)
    in_string = False

    while i < n:
        c = text[i]
        if in_string:
            result.append(c)
            if c == '\\' and i + 1 < n:
                result.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            result.append(c)
            i += 1
            continue
        if c == '/' and i + 1 < n:
            if text[i + 1] == '/':
                i += 2
                while i < n and text[i] != '\n':
                    i += 1
                continue
            elif text[i + 1] == '*':
                i += 2
                while i < n - 1 and not (text[i] == '*' and text[i + 1] == '/'):
                    i += 1
                i += 2
                continue
        result.append(c)
        i += 1
    return ''.join(result)


def fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ]."""
    return re.sub(r',(\s*[}\]])', r'\1', text)


def load_scene_json(filepath: Path) -> dict:
    """Load a vision_scene.json file, handling comments and trailing commas."""
    text = filepath.read_text(encoding='utf-8')
    clean = fix_trailing_commas(strip_json_comments(text))
    return json.loads(clean)


def save_scene_json(filepath: Path, data: dict, backup: bool = True):
    """Write scene data back to JSON with optional .bak backup."""
    import shutil
    if backup:
        bak = filepath.with_suffix('.json.bak')
        shutil.copy2(filepath, bak)
    filepath.write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding='utf-8'
    )


# ---------------------------------------------------------------------------
# Default target directory resolution
# ---------------------------------------------------------------------------

def resolve_scene_dir(explicit_path: str = None) -> Path:
    """Resolve the CoronaTestScenes render_scene directory.

    Args:
        explicit_path: If given, use this path directly.

    Returns:
        Resolved Path to the render_scene directory.
    """
    if explicit_path:
        return Path(explicit_path).resolve()
    # Default: ../../../CoronaTestScenes/test_vision/render_scene
    # (relative to this file: tools/scene_transform/common.py)
    return (Path(__file__).resolve().parent / ".." / ".." / ".."
            / "CoronaTestScenes" / "test_vision" / "render_scene").resolve()


def find_scene_files(base: Path, pattern: str = "vision_scene.json") -> list:
    """Find scene JSON files under base directory.

    Args:
        pattern: Glob pattern. Use "vision_scene.json" for main files only,
                 or "*.json" for all JSON files.
    """
    EXCLUDE = {"tungsten_scene.json", "golden_timing.json", "test_image_timing.json"}
    results = []
    for f in sorted(base.rglob(pattern)):
        if f.suffix == ".bak":
            continue
        if f.name in EXCLUDE:
            continue
        results.append(f)
    return results


# ---------------------------------------------------------------------------
# Canonical format helpers
# ---------------------------------------------------------------------------

def determine_channels(value) -> str:
    if isinstance(value, (int, float)):
        return "x"
    if isinstance(value, list):
        return {1: "x", 2: "xy", 3: "xyz", 4: "xyzw"}.get(len(value), "x")
    return "x"


def make_number_node(value):
    return {"type": "number", "param": {"value": value}}


def make_slot(channels: str, value):
    """Create a canonical slot: {channels, node: {type: "number", param: {value: ...}}}."""
    return {"channels": channels, "node": make_number_node(value)}
