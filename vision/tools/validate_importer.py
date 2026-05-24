"""
Validate the b2v importer logic against actual Vision scene JSON files.

This script simulates the importer's parsing logic *without* Blender,
checking that every field in every scene can be correctly interpreted
by the importer code paths.

Usage:
    python tools/validate_importer.py
"""

import json
import re
import os
import sys
import traceback
from collections import defaultdict

# ── Scene directories ────────────────────────────────────────────────
RENDER_SCENE_BASE = r"D:\work\corona\CoronaTestScenes\test_vision\render_scene"
BLENDER_SCENE_BASE = r"D:\work\corona\CoronaTestScenes\test_vision\blender_scene"


# ── JSON loader (mirrors importer/ui.py _load_json_with_comments) ────
def load_json(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return json.loads(text)


# ── Collect all scenes ───────────────────────────────────────────────
def collect_scenes():
    scenes = []
    for d in sorted(os.listdir(RENDER_SCENE_BASE)):
        fp = os.path.join(RENDER_SCENE_BASE, d, "vision_scene.json")
        if os.path.isfile(fp):
            scenes.append((d, fp))
    if os.path.isdir(BLENDER_SCENE_BASE):
        for d in sorted(os.listdir(BLENDER_SCENE_BASE)):
            for jf in ["vision_scene.json", "cbox.json"]:
                fp = os.path.join(BLENDER_SCENE_BASE, d, jf)
                if os.path.isfile(fp):
                    scenes.append((d + "(blender)", fp))
    return scenes


# ── Slot value extraction (mirrors importer/shadernode.py logic) ─────
def validate_slot(slot_data, node_tab, dim, path_ctx):
    """Validate that a slot value can be parsed by the importer."""
    errors = []

    if slot_data is None:
        return errors  # None is valid (skip)

    # Direct scalar
    if isinstance(slot_data, (int, float)):
        return errors

    # Direct list
    if isinstance(slot_data, list):
        if dim == 1 and len(slot_data) < 1:
            errors.append("%s: list too short for dim=1" % path_ctx)
        elif dim == 3 and len(slot_data) < 3:
            # dim=3 with <3 elements: importer may fail
            errors.append("%s: list len=%d < dim=3" % (path_ctx, len(slot_data)))
        return errors

    if not isinstance(slot_data, dict):
        errors.append("%s: unexpected slot type %s" % (path_ctx, type(slot_data).__name__))
        return errors

    node_ref = slot_data.get("node")

    # String reference to node_tab
    if isinstance(node_ref, str):
        if node_tab and node_ref in node_tab:
            node_def = node_tab[node_ref]
            errors.extend(validate_node(node_def, slot_data, node_tab, dim, path_ctx + "->ref"))
        else:
            errors.append("%s: node_tab ref '%s' not found" % (path_ctx, node_ref[:60]))
        return errors

    # Inline node dict
    if isinstance(node_ref, dict):
        errors.extend(validate_node(node_ref, slot_data, node_tab, dim, path_ctx + "->inline"))
        return errors

    # Inline number list
    if isinstance(node_ref, list):
        return errors  # valid

    # Inline scalar
    if isinstance(node_ref, (int, float)):
        return errors  # valid

    if node_ref is None:
        # {"channels":"xyz"} with no node - unusual but maybe OK
        return errors

    errors.append("%s: unexpected node type %s" % (path_ctx, type(node_ref).__name__))
    return errors


def validate_node(node_def, slot_data, node_tab, dim, path_ctx):
    """Validate a resolved node definition."""
    errors = []
    if not isinstance(node_def, dict):
        errors.append("%s: node_def not a dict" % path_ctx)
        return errors

    node_type = node_def.get("type", "")
    param = node_def.get("param", {})

    KNOWN_TYPES = {
        "number", "image", "converter", "src_node", "separate_color", "separate_xyz"
    }

    if node_type == "number":
        val = param.get("value")
        if val is None:
            errors.append("%s: number node missing 'value'" % path_ctx)
        # value can be scalar or list - both fine

    elif node_type == "image":
        fn = param.get("fn", "")
        if not fn:
            errors.append("%s: image node missing 'fn'" % path_ctx)
        # vector sub-slot can be None or a slot
        vec = param.get("vector")
        if vec is not None:
            errors.extend(validate_slot(vec, node_tab, 3, path_ctx + ".vector"))

    elif node_type == "converter":
        construct = node_def.get("construct_name", "")
        KNOWN_CONVERTERS = {
            "normal_map", "math", "gamma", "clamp",
            "combine_color", "combine_xyz", "fresnel", "vector_mapping"
        }
        if construct not in KNOWN_CONVERTERS:
            errors.append("%s: unknown converter '%s'" % (path_ctx, construct))
        else:
            # Validate sub-slots per converter type
            if construct == "normal_map":
                errors.extend(validate_slot(param.get("color"), node_tab, 3, path_ctx + ".color"))
                errors.extend(validate_slot(param.get("strength"), node_tab, 1, path_ctx + ".strength"))
            elif construct == "math":
                errors.extend(validate_slot(param.get("value0"), node_tab, 1, path_ctx + ".value0"))
                errors.extend(validate_slot(param.get("value1"), node_tab, 1, path_ctx + ".value1"))
                # value2 is optional
            elif construct == "gamma":
                errors.extend(validate_slot(param.get("color"), node_tab, 3, path_ctx + ".color"))
                errors.extend(validate_slot(param.get("gamma"), node_tab, 1, path_ctx + ".gamma"))
            elif construct == "clamp":
                errors.extend(validate_slot(param.get("value"), node_tab, 1, path_ctx + ".value"))
                errors.extend(validate_slot(param.get("min"), node_tab, 1, path_ctx + ".min"))
                errors.extend(validate_slot(param.get("max"), node_tab, 1, path_ctx + ".max"))
            elif construct == "combine_color":
                for ch in ["channel0", "channel1", "channel2"]:
                    errors.extend(validate_slot(param.get(ch), node_tab, 1, path_ctx + "." + ch))
            elif construct == "combine_xyz":
                for ch in ["x", "y", "z"]:
                    errors.extend(validate_slot(param.get(ch), node_tab, 1, path_ctx + "." + ch))
            elif construct == "fresnel":
                errors.extend(validate_slot(param.get("ior"), node_tab, 1, path_ctx + ".ior"))
            elif construct == "vector_mapping":
                errors.extend(validate_slot(param.get("vector"), node_tab, 3, path_ctx + ".vector"))
                errors.extend(validate_slot(param.get("scale"), node_tab, 3, path_ctx + ".scale"))
                errors.extend(validate_slot(param.get("rotation"), node_tab, 3, path_ctx + ".rotation"))

    elif node_type == "src_node":
        construct = node_def.get("construct_name", "")
        KNOWN_SRC = {"tex_coord", "geometry", "camera"}
        if construct not in KNOWN_SRC:
            errors.append("%s: unknown src_node '%s'" % (path_ctx, construct))

    elif node_type == "separate_color":
        errors.extend(validate_slot(param.get("value"), node_tab, 3, path_ctx + ".value"))

    elif node_type == "separate_xyz":
        # Importer doesn't handle separate_xyz! This is an issue.
        errors.append("%s: IMPORTER_MISSING separate_xyz handler" % path_ctx)

    elif node_type not in KNOWN_TYPES:
        errors.append("%s: unknown node type '%s'" % (path_ctx, node_type))

    return errors


# ── Material validation ──────────────────────────────────────────────
MATERIAL_SLOT_MAP = {
    "principled_bsdf": {
        "color": 3, "roughness": 1, "ior": 1, "metallic": 1,
        "spec_tint": 3, "anisotropic": 1, "normal": 3,
        "sheen_weight": 1, "sheen_roughness": 1, "sheen_tint": 3,
        "coat_weight": 1, "coat_roughness": 1, "coat_ior": 1, "coat_tint": 3,
        "subsurface_weight": 1, "subsurface_radius": 3, "subsurface_scale": 1,
        "transmission_weight": 1,
    },
    "diffuse": {"color": 3, "roughness": 1},
    "glass": {"color": 3, "roughness": 1, "ior": 1},
    "mirror": {"color": 3, "roughness": 1},
    "metal": {"color": 3, "roughness": 1},
    "substrate": {"color": 3, "roughness": 1, "spec": 3, "specular": 3, "ior": 1},
    "mix": {},  # handled separately
}

KNOWN_MATERIAL_TYPES = set(MATERIAL_SLOT_MAP.keys())


def validate_material(mat_def, scene_name):
    errors = []
    mat_type = mat_def.get("type", "")
    mat_name = mat_def.get("name", "?")
    param = mat_def.get("param", {})
    node_tab = mat_def.get("node_tab", {})
    ctx = "scene=%s mat=%s(%s)" % (scene_name, mat_name, mat_type)

    if mat_type not in KNOWN_MATERIAL_TYPES:
        errors.append("%s: UNKNOWN material type '%s'" % (ctx, mat_type))
        return errors

    if mat_type == "mix":
        # Check frac OR scale (importer reads both)
        if "frac" not in param and "scale" not in param:
            errors.append("%s: mix has neither 'frac' nor 'scale'" % ctx)

        for sub_key in ["mat0", "mat1"]:
            sub = param.get(sub_key, {})
            if sub:
                errors.extend(validate_sub_material(sub, node_tab, ctx + ".%s" % sub_key))
        return errors

    # Standard materials - validate slots
    slot_map = MATERIAL_SLOT_MAP.get(mat_type, {})
    for slot_name, dim in slot_map.items():
        slot_val = param.get(slot_name)
        if slot_val is not None:
            errors.extend(validate_slot(slot_val, node_tab, dim, ctx + ".%s" % slot_name))

    # Check for unknown parameter keys that might be important
    known_keys = set(slot_map.keys()) | {"material_name", "name"}
    unknown = set(param.keys()) - known_keys
    # Filter out keys the importer ignores (handled by renderer, not material)
    important_unknown = unknown - {
        "two_sided", "eta", "k", "remapping_roughness",
        # Extra Disney/Principled params sometimes exported on diffuse
        "flatness", "spec_trans", "metallic", "sheen_tint", "ior",
        "anisotropic", "scatter_distance", "sheen", "diff_trans",
        "clearcoat_alpha", "clearcoat", "spec_tint",
        # Extra params on glass/mirror
        "bump_scale",
    }
    if important_unknown:
        errors.append("%s: UNHANDLED params %s" % (ctx, important_unknown))

    return errors


def validate_sub_material(mat_data, parent_node_tab, ctx):
    """Validate inline sub-material in a mix shader."""
    errors = []
    mat_type = mat_data.get("type", "")
    param = mat_data.get("param", {})
    node_tab = mat_data.get("node_tab", parent_node_tab)

    KNOWN_SUB_TYPES = {"diffuse", "glass", "mirror", "glossy", "principled_bsdf", "metal", "substrate"}
    if mat_type not in KNOWN_SUB_TYPES:
        errors.append("%s: IMPORTER_BUG unknown sub-material type '%s' in _create_bsdf_node" % (ctx, mat_type))
        return errors

    # Validate known slots based on type
    sub_slots = {
        "diffuse": {"color": 3, "roughness": 1},
        "glass": {"color": 3, "roughness": 1, "ior": 1},
        "mirror": {"color": 3, "roughness": 1},
        "glossy": {"color": 3, "roughness": 1},
        "principled_bsdf": {"color": 3, "roughness": 1, "metallic": 1, "ior": 1},
        "metal": {"color": 3, "roughness": 1},
        "substrate": {"color": 3, "roughness": 1, "spec": 3},
    }
    for slot_name, dim in sub_slots.get(mat_type, {}).items():
        slot_val = param.get(slot_name)
        if slot_val is not None:
            errors.extend(validate_slot(slot_val, node_tab, dim, ctx + ".%s" % slot_name))

    return errors


# ── Shape validation ─────────────────────────────────────────────────
KNOWN_SHAPE_TYPES = {"quad", "cube", "sphere", "model"}


def validate_shape(shape, material_names, scene_dir, scene_name):
    errors = []
    shape_type = shape.get("type", "")
    name = shape.get("name", "?")
    param = shape.get("param", {})
    ctx = "scene=%s shape=%s(%s)" % (scene_name, name, shape_type)

    if shape_type not in KNOWN_SHAPE_TYPES:
        errors.append("%s: unknown shape type '%s'" % (ctx, shape_type))

    # Validate transform
    transform = param.get("transform", {})
    t_type = transform.get("type", "")
    if t_type:
        KNOWN_TRANSFORMS = {"matrix4x4", "TRS", "look_at", "Euler"}
        if t_type not in KNOWN_TRANSFORMS:
            errors.append("%s: unknown transform type '%s'" % (ctx, t_type))

        if t_type == "matrix4x4":
            mat = transform.get("param", {}).get("matrix4x4")
            if mat is None:
                errors.append("%s: matrix4x4 transform missing matrix4x4 param" % ctx)
            elif not isinstance(mat, list) or len(mat) != 4:
                errors.append("%s: matrix4x4 should be 4x4 list, got %s" % (ctx, type(mat).__name__))
            else:
                for i, row in enumerate(mat):
                    if not isinstance(row, list) or len(row) != 4:
                        errors.append("%s: matrix4x4 row %d invalid" % (ctx, i))

    # Validate material reference
    mat_ref = param.get("material", "")
    if mat_ref and mat_ref not in material_names:
        errors.append("%s: material '%s' not found in scene materials" % (ctx, mat_ref))

    # Validate model file reference
    if shape_type == "model":
        fn = param.get("fn", "")
        if fn:
            filepath = os.path.join(scene_dir, fn)
            if not os.path.isfile(filepath):
                # Just a warning, not an error (model files may be missing)
                errors.append("%s: WARNING model file not found: %s" % (ctx, fn))

    # Check emission field (from add shader) - importer creates co-located light
    if "emission" in param:
        em = param["emission"]
        if not isinstance(em, dict):
            errors.append("%s: emission field is not a dict" % ctx)

    return errors


# ── Light validation ─────────────────────────────────────────────────
KNOWN_LIGHT_TYPES = {"area", "point", "spot", "spherical", "projector"}


def validate_light(light, scene_dir, scene_name):
    errors = []
    light_type = light.get("type", "")
    param = light.get("param", {})
    node_tab = light.get("node_tab", {})
    ctx = "scene=%s light(%s)" % (scene_name, light_type)

    if light_type not in KNOWN_LIGHT_TYPES:
        errors.append("%s: unknown light type '%s'" % (ctx, light_type))
        return errors

    if light_type == "area":
        errors.extend(validate_slot(param.get("color"), node_tab, 3, ctx + ".color"))
        if "o2w" not in param:
            errors.append("%s: area light missing 'o2w' transform" % ctx)

    elif light_type == "point":
        errors.extend(validate_slot(param.get("color"), node_tab, 3, ctx + ".color"))
        if "position" not in param:
            errors.append("%s: point light missing 'position'" % ctx)

    elif light_type == "spot":
        errors.extend(validate_slot(param.get("color"), node_tab, 3, ctx + ".color"))
        if "o2w" not in param and "position" not in param:
            errors.append("%s: spot light missing 'o2w' transform (or legacy 'position')" % ctx)

    elif light_type == "spherical":
        color = param.get("color", {})
        errors.extend(validate_slot(color, node_tab, 3, ctx + ".color"))
        # Check for environment map image
        if isinstance(color, dict):
            node = color.get("node")
            if isinstance(node, dict) and node.get("type") == "image":
                fn = node.get("param", {}).get("fn", "")
                filepath = os.path.join(scene_dir, fn)
                if fn and not os.path.isfile(filepath):
                    errors.append("%s: WARNING env map not found: %s" % (ctx, fn))
            elif isinstance(node, str):
                # node_tab reference
                node_def = node_tab.get(node)
                if node_def and node_def.get("type") == "image":
                    fn = node_def.get("param", {}).get("fn", "")
                    filepath = os.path.join(scene_dir, fn)
                    if fn and not os.path.isfile(filepath):
                        errors.append("%s: WARNING env map not found: %s" % (ctx, fn))

    elif light_type == "projector":
        # Importer maps projector -> spot as approximation
        pass

    return errors


# ── Camera validation ────────────────────────────────────────────────
def validate_camera(cam_data, scene_name):
    errors = []
    if not cam_data:
        errors.append("scene=%s: no camera data" % scene_name)
        return errors

    param = cam_data.get("param", {})
    ctx = "scene=%s camera" % scene_name

    # FOV
    fov_y = param.get("fov_y")
    if fov_y is None:
        errors.append("%s: missing fov_y" % ctx)

    # Transform
    transform = param.get("transform", {})
    t_type = transform.get("type", "")
    t_param = transform.get("param", {})

    KNOWN_CAM_TRANSFORMS = {"look_at", "Euler", "TRS", "matrix4x4"}
    if t_type and t_type not in KNOWN_CAM_TRANSFORMS:
        errors.append("%s: unknown camera transform type '%s'" % (ctx, t_type))

    if t_type == "look_at":
        for key in ["position", "target_pos"]:
            if key not in t_param:
                errors.append("%s: look_at missing '%s'" % (ctx, key))

    elif t_type == "Euler":
        # Should have yaw, pitch, position
        if "position" not in t_param:
            errors.append("%s: Euler missing 'position'" % ctx)

    return errors


# ── Main validation ──────────────────────────────────────────────────
def main():
    scenes = collect_scenes()
    print("=" * 70)
    print("Importer Validation: %d scenes found" % len(scenes))
    print("=" * 70)

    total_errors = 0
    total_warnings = 0
    error_categories = defaultdict(int)

    for scene_name, scene_path in scenes:
        scene_dir = os.path.dirname(scene_path)
        try:
            data = load_json(scene_path)
        except Exception as e:
            print("\nERROR loading %s: %s" % (scene_name, e))
            total_errors += 1
            continue

        scene_errors = []

        # Validate materials
        material_names = set()
        for mat in data.get("materials", []):
            mat_name = mat.get("name", "")
            param_name = mat.get("param", {}).get("material_name", "")
            # Importer uses param.material_name if present, else name
            effective_name = param_name if param_name else mat_name
            material_names.add(effective_name)
            # Also add the top-level 'name' since shapes reference it
            material_names.add(mat_name)
            scene_errors.extend(validate_material(mat, scene_name))

        # Validate shapes
        for shape in data.get("shapes", []):
            scene_errors.extend(validate_shape(shape, material_names, scene_dir, scene_name))

        # Validate lights
        ls = data.get("light_sampler", {})
        for light in ls.get("param", {}).get("lights", []):
            scene_errors.extend(validate_light(light, scene_dir, scene_name))

        # Validate camera
        scene_errors.extend(validate_camera(data.get("camera"), scene_name))

        # Classify and count
        bugs = [e for e in scene_errors if "IMPORTER_BUG" in e or "IMPORTER_MISSING" in e]
        warnings = [e for e in scene_errors if "WARNING" in e]
        others = [e for e in scene_errors if "IMPORTER_BUG" not in e and "IMPORTER_MISSING" not in e and "WARNING" not in e]

        if bugs or warnings or others:
            print("\n--- %s (%s) ---" % (scene_name, os.path.basename(scene_path)))
            for e in bugs:
                print("  [BUG]  %s" % e)
                # Categorize
                if "IMPORTER_BUG" in e:
                    cat = e.split("IMPORTER_BUG")[1].strip().split(" ")[0]
                elif "IMPORTER_MISSING" in e:
                    cat = e.split("IMPORTER_MISSING")[1].strip().split(" ")[0]
                else:
                    cat = "other"
                error_categories[cat] += 1
            for e in others:
                print("  [ERR]  %s" % e)
                error_categories["parse_error"] += 1
            for e in warnings:
                print("  [WARN] %s" % e)
                total_warnings += 1

        total_errors += len(bugs) + len(others)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("  Scenes validated: %d" % len(scenes))
    print("  Errors:   %d" % total_errors)
    print("  Warnings: %d" % total_warnings)

    if error_categories:
        print("\n  Error categories:")
        for cat, cnt in sorted(error_categories.items(), key=lambda x: -x[1]):
            print("    %s: %d" % (cat, cnt))

    if total_errors > 0:
        print("\n  IMPORTER ISSUES DETECTED — see details above")
        return 1
    else:
        print("\n  All scenes pass validation!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
