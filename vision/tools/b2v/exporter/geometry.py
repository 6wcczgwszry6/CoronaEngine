import bpy
import os
import json
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from . import material
from ..import utils
from mathutils import Matrix


def _vision_shape_transform(exporter, object):
    axis_mat = exporter.correct_matrix()
    return axis_mat @ object.matrix_world @ axis_mat.inverted()


def _export_origin_glb(exporter, object):
    scene = exporter.context.scene
    temp_object = object.copy()
    temp_object.parent = None
    temp_object.matrix_world = Matrix.Identity(4)
    scene.collection.objects.link(temp_object)

    previous_active = bpy.context.view_layer.objects.active
    previous_active_name = previous_active.name if previous_active else None
    previous_selected_names = [selected_object.name for selected_object in bpy.context.selected_objects]

    try:
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = temp_object
        temp_object.select_set(True)
        bpy.ops.export_scene.gltf(
            filepath=exporter.mesh_path(object.name),
            export_materials="PLACEHOLDER",
            use_selection=True,
        )
    finally:
        bpy.ops.object.select_all(action="DESELECT")
        bpy.data.objects.remove(temp_object, do_unlink=True)
        for selected_name in previous_selected_names:
            selected_object = bpy.data.objects.get(selected_name)
            if selected_object is not None:
                selected_object.select_set(True)
        if previous_active_name:
            active_object = bpy.data.objects.get(previous_active_name)
            if active_object is not None:
                bpy.context.view_layer.objects.active = active_object


def export_mesh(exporter, object, materials):
    exporter.try_make_mesh_dir()
    vision_transform = _vision_shape_transform(exporter, object)

    if object.type == "MESH":
        b_mesh = object.data
    else:
        b_mesh = object.to_mesh()
    print(object.name, "--------------------------------")
    mat = b_mesh.materials[0]
    mat_data = material.export(exporter, mat, materials)
    ret = {
        "type": "model",
        "names": object.name,
        "param": {
            "fn": exporter.mesh_dir + "/" + object.name + ".glb",
            "smooth": True,
            "material": mat.name,
            "transform": {
                "type": "matrix4x4",
                "param": {
                    "matrix4x4": utils.matrix_to_list(vision_transform)
                },
            },
        },
    }
    
    if mat_data is None:
        print("wocaonima   ", object.name)
    
    if mat_data["type"] == "add":
        ret["param"]["emission"] = mat_data["param"]["emission"]

    _export_origin_glb(exporter, object)
    return ret


def export(exporter, object, materials):
    bpy.context.view_layer.objects.active = object
    object.select_set(True)
    ret = export_mesh(exporter, object, materials)
    object.select_set(False)
    return ret
