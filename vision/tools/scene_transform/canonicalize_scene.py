#!/usr/bin/env python3
"""Canonicalize vision_scene.json files to strict slot format.

A whitelist-based approach: only known slot properties are canonicalized,
non-slot properties are left untouched.

Canonical forms:
  3D vector: {"channels": "xyz", "node": {"type": "number", "param": {"value": [r, g, b]}}}
  2D vector: {"channels": "xy",  "node": {"type": "number", "param": {"value": [u, v]}}}
  1D scalar: {"channels": "x",   "node": {"type": "number", "param": {"value": [v]}}}
  image:     {"channels": "xyz", "node": {"type": "image",  "param": {"fn": ..., "color_space": ...}}}

Usage:
    python -m scene_transform.canonicalize_scene [--dry-run] [--scenes name1 name2 ...]
    python tools/scene_transform/canonicalize_scene.py [--dry-run]
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

from .common import resolve_scene_dir

# ---------------------------------------------------------------------------
# Slot white-lists  (property names that ARE shader-node slots)
# ---------------------------------------------------------------------------

MATERIAL_SLOTS = {
    "diffuse":         {"color", "sigma"},
    "glass":           {"color", "roughness", "ior", "anisotropic"},
    "metal":           {"eta", "k", "roughness", "anisotropic"},
    "metallic":        {"color", "edge_tint", "roughness", "anisotropic"},
    "mirror":          {"color", "roughness", "anisotropic"},
    "substrate":       {"color", "spec", "specular", "roughness", "ior", "anisotropic"},
    "plastic":         {"color", "spec", "specular", "roughness", "ior", "anisotropic"},
    "principled_bsdf": {
        "color", "metallic", "ior", "roughness", "spec_tint", "anisotropic",
        "sheen", "sheen_tint", "sheen_weight", "sheen_roughness",
        "clearcoat", "clearcoat_alpha", "coat_weight", "coat_roughness",
        "coat_ior", "coat_tint",
        "spec_trans", "transmission_weight",
        "flatness", "scatter_distance", "subsurface_weight",
        "subsurface_radius", "subsurface_scale",
        "diff_trans", "opacity",
    },
    "subsurface":      {"color", "roughness", "ior", "sigma_a", "sigma_s"},
    "mix":             {"frac", "scale"},
}

LIGHT_SLOTS = {"color", "strength"}
EMISSION_SLOTS = {"color", "strength"}

NON_SLOT_KEYS = {
    "material_name", "remapping_roughness", "two_sided", "thin",
    "alpha_threshold", "sigma_scale", "bump_scale",
    "mat0", "mat1",
    "name", "type",
    "angle", "falloff", "direction", "position", "o2w", "ratio", "flip_u",
}

SCALAR_SLOTS = {
    "ior", "metallic", "spec_tint", "anisotropic",
    "sheen", "sheen_tint", "sheen_weight", "sheen_roughness",
    "clearcoat", "clearcoat_alpha", "coat_weight", "coat_roughness",
    "coat_ior", "spec_trans", "transmission_weight",
    "flatness", "subsurface_weight", "subsurface_scale",
    "diff_trans", "opacity", "frac", "scale",
    "sigma", "strength",
}


# ---------------------------------------------------------------------------
# Slot canonicalization helpers
# ---------------------------------------------------------------------------

def _dim_of_value(val):
    if isinstance(val, (int, float)):
        return 1
    if isinstance(val, list):
        return len(val)
    return None


def _is_already_canonical(val):
    return isinstance(val, dict) and "channels" in val


def _is_image_shorthand(val):
    return (isinstance(val, dict) and "fn" in val
            and "channels" not in val and "type" not in val)


def _is_number_node_shorthand(val):
    return (isinstance(val, dict) and val.get("type") == "number"
            and "channels" not in val)


def _ensure_value_array(val):
    if isinstance(val, (int, float)):
        return [val]
    return val


def _slot_image_channels(key):
    if key == "roughness":
        return "xy"
    if key in SCALAR_SLOTS:
        return "x"
    return "xyz"


def _canonicalize_slot(key, val):
    if _is_already_canonical(val):
        val = dict(val)
        node = val.get("node")
        if isinstance(node, list) and all(isinstance(v, (int, float)) for v in node):
            val["node"] = {"type": "number", "param": {"value": node}}
            return val
        if _is_image_shorthand(node):
            val["node"] = {"type": "image", "param": {
                "fn": node["fn"], "color_space": node.get("color_space", "linear")
            }}
            return val
        if isinstance(node, dict) and node.get("type") == "number":
            param = node.get("param", {})
            if "value" in param:
                param["value"] = _ensure_value_array(param["value"])
        return val

    if _is_image_shorthand(val):
        return {"channels": _slot_image_channels(key), "node": {"type": "image", "param": {
            "fn": val["fn"], "color_space": val.get("color_space", "linear")
        }}}

    if _is_number_node_shorthand(val):
        inner = val.get("param", {})
        raw_val = inner.get("value", 0)
        dim = _dim_of_value(raw_val)
        if dim is None:
            return val
        ch = {1: "x", 2: "xy", 3: "xyz", 4: "xyzw"}.get(dim, "xyz")
        new_param = {"value": _ensure_value_array(raw_val)}
        if "min" in inner:
            new_param["min"] = inner["min"]
        if "max" in inner:
            new_param["max"] = inner["max"]
        return {"channels": ch, "node": {"type": "number", "param": new_param}}

    if isinstance(val, (int, float)):
        return {"channels": "x", "node": {"type": "number", "param": {"value": [val]}}}

    if isinstance(val, list) and all(isinstance(v, (int, float)) for v in val):
        dim = len(val)
        ch = {1: "x", 2: "xy", 3: "xyz", 4: "xyzw"}.get(dim, "xyz")
        return {"channels": ch, "node": {"type": "number", "param": {"value": val}}}

    if isinstance(val, dict) and "type" in val and "param" in val:
        return {"channels": "xyz", "node": val}

    return val


def _get_slot_whitelist(mat_type):
    if mat_type in MATERIAL_SLOTS:
        return MATERIAL_SLOTS[mat_type]
    combined = set()
    for s in MATERIAL_SLOTS.values():
        combined |= s
    return combined


# ---------------------------------------------------------------------------
# Top-level canonicalization
# ---------------------------------------------------------------------------

def canonicalize_material(mat):
    mat_type = mat.get("type", "")
    param = mat.get("param")
    if not isinstance(param, dict):
        return
    slots = _get_slot_whitelist(mat_type)
    if mat_type in ("mix", "add"):
        for sub_key in ("mat0", "mat1"):
            sub = param.get(sub_key)
            if isinstance(sub, dict):
                canonicalize_material(sub)
    for key in list(param.keys()):
        if key not in slots:
            continue
        param[key] = _canonicalize_slot(key, param[key])


def canonicalize_light(light):
    param = light.get("param")
    if not isinstance(param, dict):
        return
    for key in list(param.keys()):
        if key not in LIGHT_SLOTS:
            continue
        param[key] = _canonicalize_slot(key, param[key])


def canonicalize_emission(emission):
    param = emission.get("param")
    if not isinstance(param, dict):
        return
    for key in list(param.keys()):
        if key not in EMISSION_SLOTS:
            continue
        param[key] = _canonicalize_slot(key, param[key])


def canonicalize_scene(data):
    for mat in data.get("materials", []):
        canonicalize_material(mat)
    for shape in data.get("shapes", []):
        em = shape.get("emission")
        if isinstance(em, dict):
            canonicalize_emission(em)
    ls = data.get("light_sampler", {})
    for light in ls.get("param", {}).get("lights", []):
        canonicalize_light(light)
    return data


def load_json_with_comments(path):
    text = open(path, encoding="utf-8").read()
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Canonicalize vision scene JSON files (whitelist-based)")
    parser.add_argument(
        "--scenes-dir",
        default=str(resolve_scene_dir()),
        help="Root directory containing scene folders",
    )
    parser.add_argument("--scenes", nargs="*", help="Specific scene names (default: all)")
    parser.add_argument("--backup", default="", help="Backup suffix (e.g. '_backup.json')")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    args = parser.parse_args()

    scenes_dir = args.scenes_dir
    if args.scenes:
        scene_dirs = [os.path.join(scenes_dir, s) for s in args.scenes]
    else:
        scene_dirs = sorted(
            os.path.join(scenes_dir, d)
            for d in os.listdir(scenes_dir)
            if os.path.isdir(os.path.join(scenes_dir, d))
        )

    processed = 0
    for sd in scene_dirs:
        scene_file = os.path.join(sd, "vision_scene.json")
        if not os.path.isfile(scene_file):
            continue

        scene_name = os.path.basename(sd)
        data = load_json_with_comments(scene_file)
        canonicalize_scene(data)

        output = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False)

        if args.dry_run:
            print("=== %s ===" % scene_name)
            print(output[:2000])
            print("...\n")
        else:
            if args.backup:
                backup_path = scene_file.replace(".json", args.backup)
                if not os.path.exists(backup_path):
                    shutil.copy2(scene_file, backup_path)
                    print("  backup -> %s" % backup_path)
            with open(scene_file, "w", encoding="utf-8") as f:
                f.write(output + "\n")
            print("[OK] %s" % scene_name)
            processed += 1

    print("\nProcessed %d scene(s)." % processed)


if __name__ == "__main__":
    main()
