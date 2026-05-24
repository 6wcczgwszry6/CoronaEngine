"""Import Vision JSON camera into Blender."""
import bpy
import math
from .geometry import _extract_camera_transform


def import_camera(cam_desc):
    """Create a Blender camera from a Vision JSON camera descriptor.
    
    Returns the created camera object.
    """
    param = cam_desc.get("param", {})
    
    # Create camera data
    cam_data = bpy.data.cameras.new(name=param.get("name", "Camera"))
    cam_data.type = "PERSP"
    
    # FOV: exporter multiplied angle_y by 1.5
    fov_y = param.get("fov_y", 60)
    cam_data.angle_y = math.radians(fov_y / 1.5)
    
    # Lens type
    cam_type = cam_desc.get("type", "thin_lens")
    if cam_type == "thin_lens":
        lens_radius = param.get("lens_radius", 0)
        focal_distance = param.get("focal_distance", 10)
        if lens_radius > 0:
            cam_data.dof.use_dof = True
            cam_data.dof.focus_distance = focal_distance
            cam_data.dof.aperture_fstop = 1.0 / (2.0 * lens_radius) if lens_radius > 0 else 1.4
    
    # Create camera object
    cam_obj = bpy.data.objects.new(name=param.get("name", "Camera"), object_data=cam_data)
    bpy.context.collection.objects.link(cam_obj)
    
    # Apply transform
    transform = param.get("transform")
    if transform:
        mat = _extract_camera_transform(transform)
        cam_obj.matrix_world = mat
    
    # Set as active camera
    bpy.context.scene.camera = cam_obj
    
    # Set render resolution from pipeline/framebuffer if available
    filter_desc = param.get("filter")
    # Resolution is set at the ui.py level from pipeline data
    
    return cam_obj
