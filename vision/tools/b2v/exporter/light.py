import bpy
import os
import json
import math
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from .. import utils
from mathutils import Matrix, Vector
import numpy as np
from . import shadernode


def _find_active_light_output(light):
    if not light.use_nodes or light.node_tree is None:
        return None
    for node in light.node_tree.nodes:
        if node.type == "OUTPUT_LIGHT" and getattr(node, "is_active_output", True):
            return node
    for node in light.node_tree.nodes:
        if node.type == "OUTPUT_LIGHT":
            return node
    return None


def _extract_cycles_spot_color(exporter, light, node_tab):
    output = _find_active_light_output(light)
    if output is None or not output.inputs["Surface"].is_linked:
        return None, 1.0, 1.0

    surface_node = output.inputs["Surface"].links[0].from_node
    if surface_node.type != "EMISSION":
        return None, 1.0, 1.0

    strength = surface_node.inputs["Strength"].default_value
    color_socket = surface_node.inputs["Color"]
    if not color_socket.is_linked:
        return None, float(light.get("vision_spot_ratio", 1.0)), strength

    ratio = float(light.get("vision_spot_ratio", 1.0))

    image_node = color_socket.links[0].from_node
    if image_node.type == "TEX_IMAGE" and image_node.image is not None:
        width, height = image_node.image.size
        ratio = float(width) / float(height) if height else 1.0

    color_slot = shadernode.parse_node(exporter, color_socket, 3, node_tab)
    if color_slot is None:
        return None, ratio, strength

    return color_slot, ratio, strength


def export_area(exporter, object, node_tab):
    light = object.data
    width = 1
    height = 1
    if light.shape == "SQUARE":
        width = light.size * object.scale.x
        height = light.size * object.scale.y
    elif light.shape == "RECTANGLE":
        width = light.size * object.scale.x
        height = light.size_y * object.scale.y

    mat = exporter.correct_matrix(object.matrix_world)
    mat_list = utils.matrix_to_list(utils.vision_area_export_matrix(mat))

    ret = {
        "type": "area",
        "param": {
            "color": {"channels": "xyz", "node": list(light.color)},
            "scale": light.energy,
            "width": width,
            "height": height,
            "o2w": {"type": "matrix4x4", "param": {"matrix4x4": mat_list}},
        },
    }
    return ret


def export_point(exporter, object, node_tab):
    light = object.data
    pos = object.location
    p = exporter.correct_matrix(pos)
    value = light.energy / (4 * np.pi)
    ret = {
        "type": "point",
        "param": {
            "color": {"channels": "xyz", "node": list(light.color)},
            "scale": value,
            "strength" :{
                "channels":"x",
                "node" : {
                    "type" : "number",
                    "param" : {
                        "min" : 0,
                        "max" : 1000,
                        "value" : value,
                    }
                }
            },
            "position": list(p),
        },
    }
    return ret


def export_spot(exporter, object, node_tab):
    light = object.data
    angle = math.degrees(light.spot_size / 2.0)
    b = light.spot_blend
    falloff = angle * b
    mat = exporter.correct_matrix(object.matrix_world)
    mat_list = utils.matrix_to_list(utils.vision_spot_export_matrix(mat))

    color_slot, ratio, emission_strength = _extract_cycles_spot_color(exporter, light, node_tab)
    value = light.energy * emission_strength / (4 * np.pi)
    color_param = {"channels": "xyz", "node": list(light.color)}
    if color_slot is not None:
        color_param = color_slot
    vision_light_type = getattr(light, "vision_light_type", None) or light.get("vision_light_type", "spot")
    ret = {
        "type": vision_light_type,
        "param": {
            "color": color_param,
            "scale": value,
            "angle": angle,
            "falloff": falloff,
            "o2w": {"type": "matrix4x4", "param": {"matrix4x4": mat_list}},
            "strength" :{
                "channels":"x",
                "node" : {
                    "type" : "number",
                    "param" : {
                        "min" : 0,
                        "max" : 1000,
                        "value" : value,
                    }
                }
            },
        },
    }
    if color_slot is not None or abs(ratio - 1.0) > 1e-6:
        ret["param"]["ratio"] = ratio
    return ret


func_tab = {
    "AREA": export_area,
    "POINT": export_point,
    "SPOT": export_spot,
}


def export(exporter, object, node_tab=None):
    node_tab = {} if node_tab is None else node_tab
    ret = func_tab[object.data.type](exporter, object, node_tab)
    ret["node_tab"] = node_tab
    return ret

def export_environment(exporter):
    scene = bpy.context.scene
    if scene.world and scene.world.use_nodes:
        node_tab = {}
        world_nodes = scene.world.node_tree.nodes
        output = world_nodes["World Output"]
        env_surface = output.inputs["Surface"].links[0].from_node
        color = env_surface.inputs["Color"]
        scale = env_surface.inputs["Strength"].default_value
        if scale == 0:
            return None
        ret = {
            "type" : "spherical",
            "param" : {
                "color" : shadernode.parse_node(exporter, color, 3, node_tab),
                "scale" : scale,
                "o2w" : {
                    "type":"Euler",
                    "param": {
                        "yaw" :180
                    }
                },
            },
            "node_tab" : node_tab,
        }
        # ret["node_tab"] = node_tab
        return ret