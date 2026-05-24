#!/usr/bin/env python3
"""
Phase 1 & 2: Transform vision_scene.json materials.

Phase 1 — Canonicalize all material params to {channels, node} format.
Phase 2 — Rewrite principled_bsdf materials to Blender 4.x standard fields.

Usage:
    python -m scene_transform.transform_materials [--dry-run] [target_dir]
    python tools/scene_transform/transform_materials.py [--dry-run] [target_dir]
"""

import json
import sys
from pathlib import Path
from collections import OrderedDict

from .common import (
    load_scene_json, save_scene_json, resolve_scene_dir, find_scene_files,
    determine_channels, make_number_node, make_slot,
)


# ---------------------------------------------------------------------------
# Material type set
# ---------------------------------------------------------------------------

MATERIAL_TYPES = {
    "diffuse", "glass", "metal", "mirror", "substrate", "mix",
    "principled_bsdf", "disney", "matte", "plastic", "uber",
    "subsurface", "translucent",
}


# ---------------------------------------------------------------------------
# Phase 1 — Canonicalize param values to {channels, node} format
# ---------------------------------------------------------------------------

def is_material_like(value):
    return isinstance(value, dict) and value.get("type") in MATERIAL_TYPES and "param" in value


def infer_channels_from_node(node):
    if isinstance(node, dict):
        if node.get("type") == "number":
            return determine_channels(node.get("param", {}).get("value"))
        if node.get("type") == "image":
            return "xyz"
    return "xyz"


def transform_node(node):
    if isinstance(node, (int, float)):
        return make_number_node(node)
    if isinstance(node, list) and all(isinstance(v, (int, float)) for v in node):
        return make_number_node(node)
    if not isinstance(node, dict):
        return node

    if "fn" in node and "type" not in node:
        return {"type": "image", "param": dict(node)}

    if "type" in node and "param" in node:
        new_node = {"type": node["type"]}
        param = node.get("param", {})
        if isinstance(param, dict):
            new_param = {}
            for k, v in param.items():
                if k in ("min", "max"):
                    continue
                if k == "value":
                    new_param[k] = v
                elif isinstance(v, dict) and ("channels" in v or "node" in v):
                    new_param[k] = transform_param_value(v)
                else:
                    new_param[k] = v
            new_node["param"] = new_param
        else:
            new_node["param"] = param
        for k in node:
            if k not in ("type", "param"):
                new_node[k] = node[k]
        return new_node

    return node


def transform_param_value(value):
    if isinstance(value, bool) or isinstance(value, str) or value is None:
        return value
    if isinstance(value, (int, float)):
        return {"channels": "x", "node": make_number_node(value)}
    if isinstance(value, list):
        if all(isinstance(v, (int, float)) for v in value):
            return {"channels": determine_channels(value), "node": make_number_node(value)}
        return value
    if isinstance(value, dict):
        if "channels" in value and "node" in value:
            result = {"channels": value["channels"]}
            if "output_key" in value:
                result["output_key"] = value["output_key"]
            result["node"] = transform_node(value["node"])
            return result
        if is_material_like(value):
            return transform_material(value)
        if "type" in value and "param" in value:
            return {"channels": infer_channels_from_node(value), "node": transform_node(value)}
        if "fn" in value and "type" not in value:
            return {"channels": "xyz", "node": {"type": "image", "param": dict(value)}}
        return value
    return value


def transform_material(mat):
    result = OrderedDict()
    result["type"] = mat.get("type", "unknown")
    if "name" in mat:
        result["name"] = mat["name"]
    if "param" in mat:
        new_param = OrderedDict()
        for k, v in mat["param"].items():
            if k == "material_name":
                new_param[k] = v
            elif k in ("mat0", "mat1") and isinstance(v, dict):
                new_param[k] = transform_material(v)
            else:
                new_param[k] = transform_param_value(v)
        result["param"] = new_param
    result["node_tab"] = mat.get("node_tab", {})
    for k, v in mat.items():
        if k not in ("type", "name", "param", "node_tab"):
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# Phase 2 — Rewrite principled_bsdf to Blender 4.x standard fields
# ---------------------------------------------------------------------------

def make_blender_principled(name, color_slot):
    """Build a Blender 4.x principled_bsdf with the given color slot preserved."""
    _n = make_slot
    return OrderedDict([
        ("type", "principled_bsdf"),
        ("name", name),
        ("param", OrderedDict([
            ("color",              color_slot),
            ("roughness",          _n("x", 0.5)),
            ("ior",                _n("x", 1.45)),
            ("metallic",           _n("x", 0.0)),
            ("spec_tint",          _n("xyz", [1.0, 1.0, 1.0])),
            ("anisotropic",        _n("x", 0.0)),
            ("sheen_weight",       _n("x", 0.0)),
            ("sheen_roughness",    _n("x", 0.5)),
            ("sheen_tint",         _n("xyz", [1.0, 1.0, 1.0])),
            ("coat_weight",        _n("x", 0.0)),
            ("coat_roughness",     _n("x", 0.03)),
            ("coat_ior",           _n("x", 1.5)),
            ("coat_tint",          _n("xyz", [1.0, 1.0, 1.0])),
            ("subsurface_weight",  _n("x", 0.0)),
            ("subsurface_radius",  _n("xyz", [1.0, 0.2, 0.1])),
            ("subsurface_scale",   _n("x", 0.05)),
            ("transmission_weight", _n("x", 0.0)),
        ])),
        ("node_tab", {}),
    ])


def upgrade_principled_materials(materials):
    upgraded = []
    for i, m in enumerate(materials):
        if m.get("type") != "principled_bsdf":
            continue
        name = m.get("name", "unnamed")
        color_slot = m["param"]["color"]  # Already canonicalized by Phase 1
        materials[i] = make_blender_principled(name, color_slot)
        upgraded.append(name)
    return upgraded


# ---------------------------------------------------------------------------
# Process a single file
# ---------------------------------------------------------------------------

def process_file(filepath: Path, dry_run: bool = False) -> dict:
    """Process one vision_scene.json file. Returns stats dict."""
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{prefix}Processing: {filepath}")

    data = load_scene_json(filepath)

    if "materials" not in data:
        print("  SKIP: No 'materials' key")
        return {"skipped": True}

    mat_count = len(data["materials"])

    # Phase 1: canonicalize all material params
    data["materials"] = [transform_material(m) for m in data["materials"]]

    # Phase 2: rewrite principled_bsdf to Blender standard
    upgraded = upgrade_principled_materials(data["materials"])

    if not dry_run:
        save_scene_json(filepath, data)

    msg = f"  OK: {mat_count} materials canonicalized"
    if upgraded:
        msg += f", {len(upgraded)} principled_bsdf upgraded ({', '.join(upgraded)})"
    print(msg)

    return {"materials": mat_count, "principled_upgraded": upgraded}


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

    ok = 0
    for f in files:
        result = process_file(f, dry_run)
        if not result.get("skipped"):
            ok += 1
        print()

    action = "Would transform" if dry_run else "Transformed"
    print(f"{action}: {ok}/{len(files)} files")


if __name__ == "__main__":
    main()
