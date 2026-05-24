#!/usr/bin/env python3
"""
Run all scene transformation phases on vision_scene.json files.

Phases:
  1. Canonicalize all material params to {channels, node} format
  2. Upgrade principled_bsdf to Blender 4.x standard fields
  3. Canonicalize emission params (color→canonical, scale kept, strength added)
  4. Canonicalize light params (color→canonical, scale kept, strength added)

Usage:
    python -m scene_transform.run_all [--dry-run] [--phase N] [target_dir]
    python tools/scene_transform/run_all.py [--dry-run] [target_dir]

Options:
    --dry-run       Preview changes without writing files
    --phase N       Run only phase N (1-4), can repeat: --phase 1 --phase 3
    --no-backup     Skip creating .json.bak backups
"""

import json
import sys
from pathlib import Path

from .common import (
    load_scene_json, save_scene_json, resolve_scene_dir, find_scene_files,
)
from .transform_materials import transform_material, upgrade_principled_materials
from .transform_emissions import canonicalize_emissions
from .transform_lights import canonicalize_lights


def process_file(filepath: Path, phases: set, dry_run: bool, no_backup: bool) -> dict:
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{prefix}{filepath.parent.name}/{filepath.name}")

    data = load_scene_json(filepath)
    stats = {}

    # Phase 1 & 2: Materials
    if (1 in phases or 2 in phases) and "materials" in data:
        mat_count = len(data["materials"])

        if 1 in phases:
            data["materials"] = [transform_material(m) for m in data["materials"]]
            stats["materials"] = mat_count

        if 2 in phases:
            upgraded = upgrade_principled_materials(data["materials"])
            if upgraded:
                stats["principled_upgraded"] = upgraded

    # Phase 3: Emissions
    if 3 in phases and "shapes" in data:
        em_count = canonicalize_emissions(data["shapes"])
        if em_count:
            stats["emissions"] = em_count

    # Phase 4: Lights
    if 4 in phases:
        light_count = canonicalize_lights(data)
        if light_count:
            stats["lights"] = light_count

    if not stats:
        print("  (no changes)")
        return stats

    if not dry_run:
        save_scene_json(filepath, data, backup=not no_backup)

    parts = []
    if "materials" in stats:
        parts.append(f"{stats['materials']} materials")
    if "principled_upgraded" in stats:
        names = ', '.join(stats['principled_upgraded'])
        parts.append(f"{len(stats['principled_upgraded'])} principled ({names})")
    if "emissions" in stats:
        parts.append(f"{stats['emissions']} emissions")
    if "lights" in stats:
        parts.append(f"{stats['lights']} lights")
    print(f"  {'Would process' if dry_run else 'OK'}: {', '.join(parts)}")

    return stats


def main():
    dry_run = "--dry-run" in sys.argv
    no_backup = "--no-backup" in sys.argv
    all_json = "--all" in sys.argv

    # Parse --phase arguments
    phases = set()
    argv = sys.argv[1:]
    i = 0
    positional = []
    while i < len(argv):
        if argv[i] == "--phase" and i + 1 < len(argv):
            phases.add(int(argv[i + 1]))
            i += 2
        elif argv[i].startswith("--"):
            i += 1
        else:
            positional.append(argv[i])
            i += 1

    if not phases:
        phases = {1, 2, 3, 4}

    base = resolve_scene_dir(positional[0] if positional else None)

    if not base.is_dir():
        print(f"ERROR: Target directory not found: {base}")
        sys.exit(1)

    pattern = "*.json" if all_json else "vision_scene.json"
    files = find_scene_files(base, pattern)
    phase_str = ", ".join(str(p) for p in sorted(phases))
    print(f"Target:  {base}")
    print(f"Phases:  {phase_str}")
    print(f"Files:   {len(files)}")
    print(f"Dry-run: {dry_run}")
    print()

    total_stats = {"materials": 0, "principled": 0, "emissions": 0, "lights": 0}
    ok = 0
    for f in files:
        stats = process_file(f, phases, dry_run, no_backup)
        if stats:
            ok += 1
            total_stats["materials"] += stats.get("materials", 0)
            total_stats["principled"] += len(stats.get("principled_upgraded", []))
            total_stats["emissions"] += stats.get("emissions", 0)
            total_stats["lights"] += stats.get("lights", 0)

    print(f"\n{'Summary':=^60}")
    print(f"  Files processed:       {ok}/{len(files)}")
    print(f"  Materials canonicalized: {total_stats['materials']}")
    print(f"  Principled upgraded:     {total_stats['principled']}")
    print(f"  Emissions transformed:   {total_stats['emissions']}")
    print(f"  Lights transformed:      {total_stats['lights']}")


if __name__ == "__main__":
    main()
