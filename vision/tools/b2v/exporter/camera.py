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


def export(exporter, object):
    camera = object.data
    res_x = exporter.context.scene.render.resolution_x
    res_y = exporter.context.scene.render.resolution_y
    ret = exporter.get_params("camera")
    
    mat = utils.to_mat(object.matrix_world)
    pos = mat[3][0:3]
    euler = object.rotation_euler
    # Camera export does not use exporter.correct_matrix() directly because the
    # Vision camera schema stores yaw/pitch/position rather than a generic o2w
    # matrix. We therefore remap the decomposed Blender camera pose into the
    # convention expected by Sensor::update_mat: position becomes (x, z, -y),
    # and the pitch is offset by 90 degrees to account for the Blender/Vision
    # camera forward-axis mismatch.
    pitch = math.degrees(euler.x) - 90
    yaw = -math.degrees(euler.z)
    
    param = {
        "fov_y": math.degrees(camera.angle_y) * 1.5,
        "name": object.name,
        "filter": exporter.get_params("filter"),
        "transform": {
            "type": "Euler",
            "param": {
                "yaw": yaw,
                "pitch": pitch,
                "position": [pos[0], pos[2], -pos[1]]
            }
        }
    }
    ret["param"].update(param)
    return ret
