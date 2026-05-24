import bpy
import os
import json
import math
from mathutils import Matrix
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
import numpy as np

def rotate_x(theta):
    theta = math.radians(theta)
    sinTheta = math.sin(theta)
    cosTheta = math.cos(theta)
    mat = [
        [1, 0,        0,         0],
        [0, cosTheta, sinTheta, 0],
        [0, -sinTheta, cosTheta,  0],
        [0, 0,        0,         1]
    ]
    return np.array(mat)

def scale(s):
    mat = [
        [s[0], 0, 0, 0],
        [0, s[1], 0, 0],
        [0, 0, s[2], 0],
        [0, 0, 0,     1]
    ]
    return np.array(mat)

def to_mat(matrix4x4):
    items = []
    for col in matrix4x4.col:
        items.extend(col)
    mat = np.array(items).reshape(4, 4)
    return mat

def to_luminous():
    r = rotate_x(0)
    s = scale([1, 1, -1])
    t = np.matmul(s, r)
    return t

def matrix_to_list(matrix):
    matrix = matrix.transposed()
    return [
        list(matrix[0]),
        list(matrix[1]),
        list(matrix[2]),
        list(matrix[3]),
    ]


def vision_area_export_matrix(corrected_world_matrix):
    """Convert a Blender area-light world matrix into Vision's local light frame.

    Blender area lights emit along local -Z. Vision's area light expects the
    quad normal to point along local +Y. A local -90 degree X rotation remaps
    the Blender emission frame into Vision's area-light convention before the
    matrix is serialized as o2w.
    """
    local_fix = Matrix.Rotation(math.radians(-90), 4, "X")
    return corrected_world_matrix @ local_fix


def vision_spot_export_matrix(corrected_world_matrix):
    """Convert a Blender spot-light world matrix into Vision's local light frame.

    Blender spot lights emit along local -Z. Vision spot/projector lights use
    local +Z as the forward axis. A local 180 degree Y rotation flips the
    forward axis while preserving the rest of the transform, so exported o2w
    matches the C++ side's transform_vector(..., +Z) convention.
    """
    local_fix = Matrix.Rotation(math.radians(180), 4, "Y")
    return corrected_world_matrix @ local_fix
