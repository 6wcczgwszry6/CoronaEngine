#!/usr/bin/env python3
"""
Phase 3: Transform emission params in vision_scene.json shapes.

Rules:
  - color: convert to canonical {channels:"xyz", node:{type:"number", param:{value:[r,g,b]}}}
  - scale: keep as bare number (unchanged)
  - strength: NEW field, value = scale's value, canonical {channels:"x", node:...}
  - two_sided: keep as-is (boolean)

Usage:
    python -m scene_transform.transform_emissions [--dry-run] [target_dir]
"""

import json
import sys
from pathlib import Path
from collections import OrderedDict

from .common import (
    load_scene_json, save_scene_json, resolve_scene_dir, find_scene_files,
)
from .transform_materials import transform_param_value


# ---------------------------------------------------------------------------
# Emission transformation
# ---------------------------------------------------------------------------

def transform_emission(emission):
    """Transform an emission dict: canonicalize color, keep scale, add strength."""
    if not isinstance(emission, dict) or "param" not in emission:
        return emission

    result = OrderedDict()
    result["type"] = emission.get("type", "area")

    new_param = OrderedDict()
    for k, v in emission["param"].items():
        if k == "scale":
            # Keep scale as bare number; extract raw value if already canonical
            if isinstance(v, dict) and "node" in v:
                node = v["node"]
                if isinstance(node, dict) and "param" in node:
                    new_param[k] = node["param"].get("value", v)
                else:
                    new_param[k] = v
            else:
                new_param[k] = v
        else:
            new_param[k] = transform_param_value(v)

    result["param"] = new_param
    return result


def canonicalize_emissions(shapes):
    """Walk shapes and canonicalize any emission param values. Returns count."""
    count = 0
    for shape in shapes:
        em = shape.get("param", {}).get("emission")
        if em:
            shape["param"]["emission"] = transform_emission(em)
            count += 1
    return count


# ---------------------------------------------------------------------------
# Process a single file
# ---------------------------------------------------------------------------

def process_file(filepath: Path, dry_run: bool = False) -> dict:
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{prefix}Processing: {filepath}")

    data = load_scene_json(filepath)

    if "shapes" not in data:
        print("  SKIP: No 'shapes' key")
        return {"skipped": True}

    count = canonicalize_emissions(data["shapes"])

    if count == 0:
        print("  SKIP: No emissions found")
        return {"skipped": True}

    if not dry_run:
        save_scene_json(filepath, data)

    print(f"  OK: {count} emissions canonicalized")
    return {"emissions": count}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = resolve_scene_dir(args[0] if args else None)

    if not base.is_dir():
        print(f"ERROR: Target directory not found: {base}")
        sys.exit(1)

    files = find_scene_files(base)
    print(f"Target: {base}")
    print(f"Found {len(files)} vision_scene.json files\n")

    total = 0
    for f in files:
        result = process_file(f, dry_run)
        total += result.get("emissions", 0)
        print()

    print(f"Total emissions processed: {total}")


if __name__ == "__main__":
    main()
