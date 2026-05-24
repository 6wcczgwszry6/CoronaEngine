"""Import Vision JSON lights into Blender."""
import bpy
import os
import math
import numpy as np
from mathutils import Matrix, Vector
from .geometry import list_to_matrix, _build_vision_matrix, _get_axis_matrices, _v2b
from . import shadernode


def _get_color(light_param, node_tab):
    """Extract RGB color from a light's color slot."""
    color_slot = light_param.get("color")
    if color_slot is None:
        return (1.0, 1.0, 1.0)
    
    val = shadernode.get_slot_value(color_slot, node_tab)
    if val is not None:
        if isinstance(val, list) and len(val) >= 3:
            return tuple(val[:3])
        elif isinstance(val, (int, float)):
            return (val, val, val)
    
    # Check for bare list in node field (legacy format)
    node = color_slot.get("node")
    if isinstance(node, list) and len(node) >= 3:
        return tuple(node[:3])
    
    return (1.0, 1.0, 1.0)


def _vision_light_matrix_to_blender_world(o2w, local_fix):
    """Convert a Vision light o2w transform into Blender object space.

    Both systems store 4x4 transforms in column-major form, but their world-up
    axes differ, so we first map Vision's Y-up frame into Blender's Z-up frame.
    On top of that, each light type may need a local-axis fix because Blender
    and Vision do not use the same emission/forward axis in the light's own
    local frame.
    """
    vision_mat = _build_vision_matrix(o2w)
    _C, C_inv = _get_axis_matrices()
    return C_inv @ vision_mat @ local_fix


def _area_light_blender_world_from_vision(o2w):
    """Map Vision area-light o2w to Blender area-light world transform.

    Vision area lights emit along local +Y. Blender area lights emit along
    local -Z. A local +90 degree X rotation converts the Vision frame back to
    Blender's area-light convention during import.
    """
    return _vision_light_matrix_to_blender_world(o2w, Matrix.Rotation(math.radians(90), 4, "X"))


def _spot_light_blender_world_from_vision(o2w):
    """Map Vision spot/projector-style o2w to Blender spot-light world transform.

    Vision spot/projector lights use local +Z as forward. Blender spot lights
    use local -Z. A local 180 degree Y rotation converts the imported Vision
    frame back into Blender's spot-light convention.
    """
    return _vision_light_matrix_to_blender_world(o2w, Matrix.Rotation(math.radians(180), 4, "Y"))


def _apply_legacy_spot_transform(light_obj, param):
    """Apply backward-compatible spot placement from explicit position/direction.

    Older Vision JSON stored spot lights as a world-space position plus a world-
    space direction vector. Blender spot lights also use a position + local -Z
    emission model, so we can reconstruct a matching object transform directly
    from those legacy fields when o2w is absent.
    """
    pos = param.get("position", [0, 0, 0])
    light_obj.location = _v2b(pos)

    direction = param.get("direction", [0, -1, 0])
    direction_blender = _v2b(direction)
    if direction_blender.length > 0:
        direction_blender.normalize()
        rotation = direction_blender.to_track_quat('-Z', 'Y')
        light_obj.rotation_euler = rotation.to_euler()


def _create_cycles_spot_nodes(light_data, color_slot, base_dir, node_tab):
    light_data.use_nodes = True
    node_tree = light_data.node_tree

    for node in list(node_tree.nodes):
        node_tree.nodes.remove(node)

    output = node_tree.nodes.new("ShaderNodeOutputLight")
    output.location = (300, 0)

    emission = node_tree.nodes.new("ShaderNodeEmission")
    emission.location = (0, 0)
    emission.inputs["Strength"].default_value = 1.0
    node_tree.links.new(emission.outputs[0], output.inputs["Surface"])

    created = {}
    shadernode.connect_slot(node_tree, color_slot, emission.inputs["Color"],
                            base_dir, node_tab, created)


def import_area(light_desc, node_tab, base_dir=None):
    """Import an area light."""
    param = light_desc.get("param", {})
    
    light_data = bpy.data.lights.new(name="AreaLight", type="AREA")
    light_data.shape = "RECTANGLE"
    light_data.size = param.get("width", 1.0)
    light_data.size_y = param.get("height", 1.0)
    light_data.energy = param.get("scale", 1.0)
    light_data.color = _get_color(param, node_tab)
    
    light_obj = bpy.data.objects.new(name="AreaLight", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    
    # Apply transform
    o2w = param.get("o2w")
    if o2w:
        light_obj.matrix_world = _area_light_blender_world_from_vision(o2w)
    
    return light_obj


def import_point(light_desc, node_tab, base_dir=None):
    """Import a point light."""
    param = light_desc.get("param", {})
    
    light_data = bpy.data.lights.new(name="PointLight", type="POINT")
    # Exporter does: value = energy / (4*pi), so reverse it
    scale = param.get("scale", 1.0)
    light_data.energy = scale * 4 * math.pi
    light_data.color = _get_color(param, node_tab)
    
    light_obj = bpy.data.objects.new(name="PointLight", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    
    pos = param.get("position", [0, 0, 0])
    light_obj.location = _v2b(pos)
    
    return light_obj


def import_spot(light_desc, node_tab, base_dir=None, light_name="SpotLight"):
    """Import a spot light."""
    param = light_desc.get("param", {})
    
    light_data = bpy.data.lights.new(name=light_name, type="SPOT")
    scale = param.get("scale", 1.0)
    light_data.energy = scale * 4 * math.pi
    light_data.color = _get_color(param, node_tab)
    
    angle = param.get("angle", 45)
    light_data.spot_size = math.radians(angle * 2)
    # Blender spot lights are circular only. Preserve Vision's ellipse ratio as
    # custom data so scenes can round-trip even when Blender cannot display the
    # exact cone shape in its native light UI.
    light_data["vision_spot_ratio"] = float(param.get("ratio", 1.0))
    light_data["vision_light_type"] = "spot"
    if hasattr(light_data, "vision_light_type"):
        light_data.vision_light_type = "spot"
    
    falloff = param.get("falloff", 0)
    if angle > 0:
        light_data.spot_blend = falloff / angle
    
    light_obj = bpy.data.objects.new(name=light_name, object_data=light_data)
    bpy.context.collection.objects.link(light_obj)

    color_slot = param.get("color")
    merged_tab = {**node_tab, **light_desc.get("node_tab", {})}
    if color_slot is not None and shadernode.get_slot_value(color_slot, merged_tab) is None:
        _create_cycles_spot_nodes(light_data, color_slot, base_dir or bpy.path.abspath("//"), merged_tab)

    o2w = param.get("o2w")
    if o2w:
        light_obj.matrix_world = _spot_light_blender_world_from_vision(o2w)
    else:
        _apply_legacy_spot_transform(light_obj, param)
    
    return light_obj


def import_projector(light_desc, node_tab, base_dir=None):
    """Import a Vision projector as a Blender spot light.

    Blender has no native projector light type. Vision projector and spot share
    the same local +Z forward convention on the Vision side, and the existing
    spot importer already reconstructs the closest Blender representation,
    including o2w conversion and optional color-node wiring.
    """
    light_obj = import_spot(light_desc, node_tab, base_dir, light_name="ProjectorLight")
    light_obj.data["vision_light_type"] = "projector"
    if hasattr(light_obj.data, "vision_light_type"):
        light_obj.data.vision_light_type = "projector"
    return light_obj


def import_spherical(light_desc, base_dir, node_tab):
    """Import a spherical (environment) light as World."""
    param = light_desc.get("param", {})
    
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    
    world.use_nodes = True
    node_tree = world.node_tree
    
    # Clear existing
    for node in node_tree.nodes:
        node_tree.nodes.remove(node)
    
    output = node_tree.nodes.new("ShaderNodeOutputWorld")
    output.location = (300, 0)
    
    background = node_tree.nodes.new("ShaderNodeBackground")
    background.location = (0, 0)
    node_tree.links.new(background.outputs[0], output.inputs["Surface"])
    
    scale = param.get("scale", 1.0)
    background.inputs["Strength"].default_value = scale
    
    # Handle color (could be HDRI image or constant)
    color_slot = param.get("color")
    if color_slot:
        created = {}
        merged_tab = {**node_tab, **light_desc.get("node_tab", {})}
        shadernode.connect_slot(node_tree, color_slot, background.inputs["Color"],
                                base_dir, merged_tab, created)
    
    return world


func_tab = {
    "area": import_area,
    "point": import_point,
    "spot": import_spot,
    "projector": import_projector,
}


def import_light(light_desc, base_dir):
    """Import a single light from Vision JSON."""
    ltype = light_desc.get("type", "")
    node_tab = light_desc.get("node_tab", {})
    
    if ltype == "spherical":
        return import_spherical(light_desc, base_dir, node_tab)
    
    if ltype in func_tab:
        return func_tab[ltype](light_desc, node_tab, base_dir)
    
    print(f"Warning: Unsupported light type '{ltype}'")
    return None
