#!/usr/bin/env python3
"""
Phase 4: Transform light params in vision_scene.json.

Rules:
  - color: convert to canonical {channels:"xyz", node:{type:"number", param:{value:[r,g,b]}}}
  - scale: keep as bare number (unchanged)
  - strength: NEW field, value = scale's value, canonical {channels:"x", node:...}
  - Other attributes (position, direction, angle, etc.): keep as-is

Usage:
    python -m scene_transform.transform_lights [--dry-run] [target_dir]
"""

import json
import sys
from pathlib import Path

from .common import (
    load_scene_json, save_scene_json, resolve_scene_dir, find_scene_files,
)
from .transform_materials import transform_param_value


# ---------------------------------------------------------------------------
# Light transformation
# ---------------------------------------------------------------------------

def canonicalize_lights(data):
    """Walk light_sampler.param.lights and canonicalize color + add strength."""
    lights = data.get("light_sampler", {}).get("param", {}).get("lights", [])
    count = 0
    for light in lights:
        param = light.get("param", {})
        changed = False
        if "color" in param:
            param["color"] = transform_param_value(param["color"])
            changed = True
        if "scale" in param:
            scale_val = param["scale"]
            param["strength"] = transform_param_value(scale_val)
            changed = True
        if changed:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Process a single file
# ---------------------------------------------------------------------------

def process_file(filepath, dry_run=False):
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{prefix}Processing: {filepath}")

    data = load_scene_json(filepath)

    count = canonicalize_lights(data)
    if count == 0:
        print("  SKIP: No lights found")
        return {"skipped": True}

    if not dry_run:
        save_scene_json(filepath, data)

    print(f"  OK: {count} lights canonicalized")
    return {"lights": count}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    from pathlib import Path

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
        total += result.get("lights", 0)
        print()

    print(f"Total lights processed: {total}")


if __name__ == "__main__":
    main()
