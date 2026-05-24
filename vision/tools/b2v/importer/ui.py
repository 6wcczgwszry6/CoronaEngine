import os
import bpy
from pathlib import Path
from bpy.props import (
    StringProperty,
    BoolProperty,
)
from bpy_extras.io_utils import ImportHelper, orientation_helper, axis_conversion
import json
import traceback
import time
from . import geometry
from . import material
from . import camera
from . import light


@orientation_helper(axis_forward="-Z", axis_up="Y")
class VisionImporter(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.vision"
    bl_label = "Vision Importer"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    override_scene: BoolProperty(
        name="Override Current Scene",
        description="Override the current scene with the imported scene. "
        "Otherwise, creates a new scene.",
        default=True,
    )

    import_materials: BoolProperty(
        name="Import Materials",
        description="Import materials and shader node graphs",
        default=True,
    )

    import_lights: BoolProperty(
        name="Import Lights",
        description="Import lights including environment",
        default=True,
    )

    import_camera: BoolProperty(
        name="Import Camera",
        description="Import camera",
        default=True,
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.base_dir = ""

    def execute(self, context):
        try:
            return self._do_import(context)
        except Exception as e:
            traceback.print_exc()
            self.report({"ERROR"}, f"Import failed: {e}")
            return {"CANCELLED"}

    def _do_import(self, context):
        # Determine base directory (the folder containing the JSON)
        json_path = self.filepath
        # Vision exports create a directory with the same name as the JSON
        # e.g. cbox/cbox.json with cbox/meshes/ and cbox/textures/
        self.base_dir = os.path.dirname(json_path)

        # Load JSON
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if self.override_scene:
            # Clear existing scene
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.object.delete(use_global=False)

        window_manager = context.window_manager

        # --- Import materials ---
        materials_dict = {}  # name → bpy.types.Material
        if self.import_materials:
            mat_list = data.get("materials", [])
            for mat_desc in mat_list:
                name = mat_desc.get("name", "Material")
                try:
                    bl_mat = material.import_material(mat_desc, self.base_dir)
                    materials_dict[name] = bl_mat
                except Exception as e:
                    print(f"Warning: Failed to import material '{name}': {e}")
                    traceback.print_exc()

        # --- Import shapes ---
        shapes = data.get("shapes", [])
        window_manager.progress_begin(0, len(shapes))
        for i, shape in enumerate(shapes):
            try:
                geometry.import_shape(shape, self.base_dir, materials_dict)
            except Exception as e:
                sname = shape.get("names") or shape.get("name", f"shape_{i}")
                print(f"Warning: Failed to import shape '{sname}': {e}")
                traceback.print_exc()
            window_manager.progress_update(i)
        window_manager.progress_end()

        # --- Import camera ---
        if self.import_camera:
            cam_data = data.get("camera")
            if cam_data:
                try:
                    cam_obj = camera.import_camera(cam_data)
                    # Set resolution from pipeline
                    pipeline = data.get("pipeline", {})
                    fb = pipeline.get("param", {}).get("frame_buffer", {})
                    resolution = fb.get("param", {}).get("resolution")
                    if resolution and len(resolution) == 2:
                        context.scene.render.resolution_x = resolution[0]
                        context.scene.render.resolution_y = resolution[1]
                except Exception as e:
                    print(f"Warning: Failed to import camera: {e}")
                    traceback.print_exc()

        # --- Import lights ---
        if self.import_lights:
            ls_data = data.get("light_sampler", {})
            lights = ls_data.get("param", {}).get("lights", [])
            for light_desc in lights:
                try:
                    light.import_light(light_desc, self.base_dir)
                except Exception as e:
                    ltype = light_desc.get("type", "unknown")
                    print(f"Warning: Failed to import light '{ltype}': {e}")
                    traceback.print_exc()

        self.report({"INFO"}, f"Scene imported: {len(shapes)} shapes, "
                    f"{len(materials_dict)} materials")
        return {"FINISHED"}


def menu_import_func(self, context):
    self.layout.operator(VisionImporter.bl_idname, text="vision (.json)")


def register():
    bpy.types.TOPBAR_MT_file_import.append(menu_import_func)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import_func)
