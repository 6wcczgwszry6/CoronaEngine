#!/usr/bin/env python3
"""Inspect scene JSON files: list materials, emissions, lights and their structure.

Usage:
    python -m scene_transform.inspect [--blender] [target_dir]

    --blender   Also show Blender-exported cbox.json for comparison.
"""

import json
import sys
from pathlib import Path

from .common import load_scene_json, resolve_scene_dir, find_scene_files


def find_emissions(shapes):
    for s in shapes:
        em = s.get("param", {}).get("emission")
        if em:
            name = s.get("names", s.get("name", "?"))
            yield name, em


def find_lights(data):
    return data.get("light_sampler", {}).get("param", {}).get("lights", [])


def inspect_file(filepath: Path):
    data = load_scene_json(filepath)
    scene = filepath.parent.name
    mats = data.get("materials", [])
    shapes = data.get("shapes", [])
    emissions = list(find_emissions(shapes))
    lights = find_lights(data)

    print(f"{'=' * 60}")
    print(f"  {scene}/vision_scene.json")
    print(f"{'=' * 60}")

    # Materials summary
    mat_types = {}
    for m in mats:
        t = m.get("type", "?")
        mat_types[t] = mat_types.get(t, 0) + 1
    print(f"  Materials ({len(mats)}): {dict(mat_types)}")

    has_node_tab = [m.get("name", "?") for m in mats if m.get("node_tab", {}) != {}]
    if has_node_tab:
        print(f"  With node_tab: {has_node_tab}")

    # Emissions
    if emissions:
        print(f"  Emissions ({len(emissions)}):")
        for name, em in emissions:
            print(f"    {name}: {json.dumps(em, indent=6)[:200]}")

    # Lights
    if lights:
        print(f"  Lights ({len(lights)}):")
        for light in lights:
            ltype = light.get("type", "?")
            lname = light.get("name", "?")
            print(f"    {lname} ({ltype}): params={list(light.get('param', {}).keys())}")

    print()


def inspect_blender_cbox():
    """Show Blender-exported cbox.json for comparison."""
    scene_dir = resolve_scene_dir()
    bf = scene_dir.parent.parent / "blender_scene" / "cbox" / "cbox.json"
    if not bf.exists():
        # Try alternate location
        bf = scene_dir.parent / "blender_scene" / "cbox" / "cbox.json"
    if not bf.exists():
        print(f"Blender cbox.json not found")
        return

    data = load_scene_json(bf)
    mats = data.get("materials", [])

    print(f"{'=' * 60}")
    print(f"  BLENDER cbox.json (reference)")
    print(f"{'=' * 60}")
    print(f"  Materials ({len(mats)}):")
    for m in mats:
        name = m.get("name", "?")
        mtype = m.get("type", "?")
        nt = m.get("node_tab", {})
        print(f"    {name} ({mtype}), node_tab entries: {len(nt)}")
    print()

    emissions = list(find_emissions(data.get("shapes", [])))
    if emissions:
        print(f"  Emissions ({len(emissions)}):")
        for name, em in emissions:
            print(f"    {name}: {json.dumps(em, indent=6)[:200]}")
        print()


def main():
    show_blender = "--blender" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = resolve_scene_dir(args[0] if args else None)

    if not base.is_dir():
        print(f"ERROR: Directory not found: {base}")
        sys.exit(1)

    if show_blender:
        inspect_blender_cbox()

    files = find_scene_files(base)
    print(f"Inspecting {len(files)} scene files under: {base}\n")
    for f in files:
        inspect_file(f)


if __name__ == "__main__":
    main()
