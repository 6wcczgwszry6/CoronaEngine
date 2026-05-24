"""Import Vision JSON shapes into Blender."""
import bpy
import os
import math
from mathutils import Matrix, Vector
from bpy_extras.io_utils import axis_conversion


# --- Coordinate system helpers ---
# Vision: Y-up, -Z forward (column-major, column-vector, same layout as Blender)
# Blender: Z-up, -Y forward
# Point conversion: Vision (x,y,z) -> Blender (x, -z, y)

_axis_c = None
_axis_c_inv = None


def _get_axis_matrices():
    """Get cached axis conversion matrices (Blender->Vision, Vision->Blender)."""
    global _axis_c, _axis_c_inv
    if _axis_c is None:
        _axis_c = axis_conversion(to_forward="-Z", to_up="Y").to_4x4()
        _axis_c_inv = _axis_c.inverted()
    return _axis_c, _axis_c_inv


def _v2b(v):
    """Convert a 3D point/vector from Vision (Y-up) to Blender (Z-up)."""
    return Vector((v[0], -v[2], v[1]))


def list_to_matrix(mat_list):
    """Convert a 4x4 nested list from Vision JSON to Blender Matrix.

    Vision JSON stores column-major data as nested arrays where each
    sub-array is one column: json[col][row]. Matrix(mat_list) treats
    each sub-array as a ROW, so transposing gives us the correct
    column-major Blender Matrix matching the C++ internal layout.
    """
    m = Matrix(mat_list)
    return m.transposed()


def import_model(shape, base_dir, materials_dict):
    """Import a model shape using an importer that matches its file extension."""
    param = shape.get("param", {})
    fn = param.get("fn", "")
    mat_name = param.get("material", "")
    
    filepath = os.path.join(base_dir, fn)
    if not os.path.exists(filepath):
        print(f"Warning: Model file not found: {filepath}")
        return None
    
    # Remember existing objects to find the newly imported ones
    before = set(bpy.data.objects)

    ext = os.path.splitext(filepath)[1].lower()
    if ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=filepath)
    else:
        print(f"Warning: Unsupported model format '{ext}' for file: {filepath}")
        return None
    
    after = set(bpy.data.objects)
    new_objects = after - before
    
    # Apply transform if present.
    # Current b2v exports keep the model file at the origin and store the real
    # world transform in JSON. We still compose with the imported matrix to
    # preserve any importer-introduced basis correction on the glTF side.
    transform = param.get("transform")
    if transform:
        mat = _parse_transform(transform)
        for obj in new_objects:
            if obj.type == "MESH":
                obj.matrix_world = mat @ obj.matrix_world
    
    # Assign material
    if mat_name and mat_name in materials_dict:
        bl_mat = materials_dict[mat_name]
        for obj in new_objects:
            if obj.type == "MESH":
                obj.data.materials.clear()
                obj.data.materials.append(bl_mat)
    
    # Set shape name
    shape_name = shape.get("names") or shape.get("name", "")
    for obj in new_objects:
        if obj.type == "MESH" and shape_name:
            obj.name = shape_name
    
    return list(new_objects)


def import_quad(shape, materials_dict):
    """Import a quad shape as a Blender plane."""
    param = shape.get("param", {})
    mat_name = param.get("material", "")
    width = param.get("width", 1.0)
    height = param.get("height", 1.0)
    
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    obj = bpy.context.active_object
    
    shape_name = shape.get("names") or shape.get("name", "Quad")
    obj.name = shape_name
    
    # Apply transform
    transform = param.get("transform")
    if transform:
        mat = _parse_transform(transform)
        obj.matrix_world = mat
    
    # Assign material
    if mat_name and mat_name in materials_dict:
        obj.data.materials.clear()
        obj.data.materials.append(materials_dict[mat_name])
    
    return [obj]


def import_cube(shape, materials_dict):
    """Import a cube shape as a Blender cube."""
    param = shape.get("param", {})
    mat_name = param.get("material", "")
    
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    
    shape_name = shape.get("names") or shape.get("name", "Cube")
    obj.name = shape_name
    
    # Apply transform
    transform = param.get("transform")
    if transform:
        mat = _parse_transform(transform)
        obj.matrix_world = mat
    
    # Assign material
    if mat_name and mat_name in materials_dict:
        obj.data.materials.clear()
        obj.data.materials.append(materials_dict[mat_name])
    
    return [obj]


def _build_vision_matrix(transform):
    """Build a 4x4 Matrix in Vision's coordinate space from a transform descriptor.

    This matches how the C++ TransformDesc::init interprets the JSON data.
    Both Vision and Blender use column-major, column-vector convention, so
    the matrix operations are identical.
    """
    ttype = transform.get("type", "matrix4x4")
    param = transform.get("param", {})

    if ttype == "matrix4x4":
        return list_to_matrix(param.get("matrix4x4",
                              [[1, 0, 0, 0], [0, 1, 0, 0],
                               [0, 0, 1, 0], [0, 0, 0, 1]]))

    elif ttype == "look_at":
        # C++ look_at: columns = right, up, fwd(unnegated), position
        pos = Vector(param.get("position", [0, 0, 0]))
        target = Vector(param.get("target_pos", [0, 0, 1]))
        up = Vector(param.get("up", [0, 1, 0]))
        fwd = (target - pos).normalized()
        right = fwd.cross(up).normalized()
        up = right.cross(fwd).normalized()
        mat = Matrix.Identity(4)
        mat[0][0], mat[1][0], mat[2][0] = right
        mat[0][1], mat[1][1], mat[2][1] = up
        mat[0][2], mat[1][2], mat[2][2] = fwd  # unnegated, Vision looks +Z
        mat[0][3], mat[1][3], mat[2][3] = pos
        return mat

    elif ttype == "trs":
        # C++ TRS: mat = T * R * S (axis-angle rotation)
        t = Vector(param.get("t", [0, 0, 0]))
        r = param.get("r", [1, 0, 0, 0])  # [axis_x, axis_y, axis_z, angle_deg]
        s = param.get("s", [1, 1, 1])
        T = Matrix.Translation(t)
        axis = Vector(r[:3])
        angle = math.radians(r[3]) if len(r) > 3 else 0
        R = Matrix.Rotation(angle, 4, axis) if axis.length > 0 else Matrix.Identity(4)
        S = Matrix.Diagonal((*s, 1)).to_4x4()
        return T @ R @ S

    elif ttype == "Euler":
        # C++ Euler: mat = T * R_pitch_x * R_roll_z * R_yaw_y
        yaw = param.get("yaw", 0)
        pitch = param.get("pitch", 0)
        roll = param.get("roll", 0)
        pos = param.get("position", [0, 0, 0])
        T = Matrix.Translation(Vector(pos))
        R_yaw = Matrix.Rotation(math.radians(yaw), 4, 'Y')
        R_pitch = Matrix.Rotation(math.radians(pitch), 4, 'X')
        R_roll = Matrix.Rotation(math.radians(roll), 4, 'Z')
        return T @ R_pitch @ R_roll @ R_yaw

    return Matrix.Identity(4)


def _parse_transform(transform):
    """Parse a Vision JSON transform for geometry objects.

    Converts from Vision (Y-up) to Blender (Z-up) using the similarity
    transform: M_blender = C_inv @ M_vision @ C.  This correctly converts
    both the world-space position and the local-space orientation for objects
    whose local geometry is also converted (e.g. glTF import does Y-up->Z-up).

    Unlike lights and cameras, ordinary shapes do not need an extra local-axis
    correction here. Their local frame is carried directly by the object/mesh
    transform, so the world-axis conversion is the only mandatory step.
    """
    vision_mat = _build_vision_matrix(transform)
    C, C_inv = _get_axis_matrices()
    return C_inv @ vision_mat @ C


def _extract_camera_transform(transform):
    """Parse a Vision JSON transform for camera objects.

    Extracts yaw/pitch/position from the Vision matrix (matching the C++
    Sensor::update_mat decomposition) and converts to Blender Euler angles.

    The C++ camera_to_world applies scale(1,1,-1) internally, so the Vision
    camera effectively looks along -Z after reconstruction. The +90 pitch
    offset compensates for the Y/Z axis swap between coordinate systems.

    So cameras do have a coordinate conversion similar in spirit to lights, but
    the reason is slightly different: shapes only need a world-axis remap,
    while cameras also need a camera-frame forward/pitch correction to match
    Blender's camera convention after the Vision transform is decoded.
    """
    vision_mat = _build_vision_matrix(transform)
    # Extract yaw/pitch/position matching C++ update_mat:
    #   pitch = degrees(atan2(m[col1][row2], m[col1][row1]))
    #   yaw   = degrees(atan2(m[col2][row0], m[col0][row0]))
    #   pos   = m[col3]
    # In Blender Matrix M[row][col], so m_cpp[col][row] = M[row][col]:
    pitch_v = math.degrees(math.atan2(vision_mat[2][1], vision_mat[1][1]))
    yaw_v = math.degrees(math.atan2(vision_mat[0][2], vision_mat[0][0]))
    pos_v = (vision_mat[0][3], vision_mat[1][3], vision_mat[2][3])

    # Convert to Blender: swap Y/Z for position, offset pitch by 90 for axis change
    from mathutils import Euler as EulerMath
    euler = EulerMath((math.radians(pitch_v + 90), 0, math.radians(-yaw_v)), 'XYZ')
    mat = euler.to_matrix().to_4x4()
    mat.translation = _v2b(pos_v)
    return mat


def import_shape(shape, base_dir, materials_dict):
    """Import a single shape from Vision JSON."""
    stype = shape.get("type", "")
    
    if stype == "model":
        return import_model(shape, base_dir, materials_dict)
    elif stype == "quad":
        return import_quad(shape, materials_dict)
    elif stype == "cube":
        return import_cube(shape, materials_dict)
    else:
        print(f"Warning: Unsupported shape type '{stype}'")
        return None
