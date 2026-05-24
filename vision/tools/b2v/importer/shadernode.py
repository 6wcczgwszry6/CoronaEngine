"""Reconstruct Blender shader node graphs from Vision JSON."""
import bpy
import os


def resolve_slot(slot, node_tab):
    """Resolve a slot to (node_desc, output_key).
    
    Handles both DAG format (node is a string referencing node_tab)
    and inline format (node is a dict with type/param).
    """
    if slot is None:
        return None, None
    if isinstance(slot, (list, tuple)):
        return {"type": "number", "param": {"value": list(slot)}}, None
    if isinstance(slot, (int, float, bool)):
        return {"type": "number", "param": {"value": slot}}, None
    if not isinstance(slot, dict):
        return None, None
    node = slot.get("node")
    if node is None:
        return None, None
    if isinstance(node, str):
        # DAG format: node is a key into node_tab
        node_desc = node_tab.get(node)
        output_key = slot.get("output_key")
        return node_desc, output_key
    elif isinstance(node, dict):
        # Inline format: node is the descriptor itself
        return node, slot.get("output_key")
    elif isinstance(node, list):
        # Bare color array like [1, 0.5, 0.2] — legacy light format
        return {"type": "number", "param": {"value": node}}, None
    else:
        return None, None


def get_slot_value(slot, node_tab):
    """Extract a numeric value from a slot, returning None if it's a complex node."""
    if slot is None:
        return None
    node_desc, _ = resolve_slot(slot, node_tab)
    if node_desc is None:
        return None
    if node_desc.get("type") == "number":
        return node_desc["param"]["value"]
    return None


def set_socket_value(socket, value):
    """Set a socket's default_value from a JSON value."""
    if value is None:
        return
    if isinstance(value, list):
        if len(value) == 3 and hasattr(socket, "default_value") and len(socket.default_value) == 4:
            socket.default_value = (*value, 1.0)
        elif len(value) == 3 and hasattr(socket, "default_value") and len(socket.default_value) == 3:
            socket.default_value = tuple(value)
        elif len(value) == 2:
            # Some sockets (roughness xy) — use first value
            socket.default_value = value[0]
        else:
            try:
                socket.default_value = value[0] if len(value) == 1 else tuple(value)
            except (TypeError, ValueError):
                pass
    else:
        try:
            socket.default_value = value
        except (TypeError, ValueError):
            pass


def create_image_node(node_tree, desc, base_dir):
    """Create an Image Texture node."""
    node = node_tree.nodes.new("ShaderNodeTexImage")
    param = desc.get("param", {})
    fn = param.get("fn", "")
    
    # Resolve path relative to scene file directory
    img_path = os.path.join(base_dir, fn)
    if os.path.exists(img_path):
        img = bpy.data.images.load(img_path, check_existing=True)
        node.image = img
        cs = param.get("color_space", "srgb")
        if cs == "linear":
            node.image.colorspace_settings.name = "Non-Color"
        else:
            node.image.colorspace_settings.name = "sRGB"
    else:
        print(f"Warning: Texture not found: {img_path}")
    
    return node


def create_converter_node(node_tree, desc, base_dir, node_tab, created):
    """Create a converter-type node (mapping, fresnel, normal_map, math, etc.)."""
    construct = desc.get("construct_name", "")
    param = desc.get("param", {})
    
    if construct == "vector_mapping":
        node = node_tree.nodes.new("ShaderNodeMapping")
        vtype = param.get("type", "POINT")
        node.vector_type = vtype
        connect_slot(node_tree, param.get("vector"), node.inputs["Vector"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("scale"), node.inputs["Scale"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("rotation"), node.inputs["Rotation"], base_dir, node_tab, created)
        if "Location" in node.inputs and param.get("location"):
            connect_slot(node_tree, param.get("location"), node.inputs["Location"], base_dir, node_tab, created)
        return node
    
    elif construct == "fresnel":
        node = node_tree.nodes.new("ShaderNodeFresnel")
        connect_slot(node_tree, param.get("ior"), node.inputs["IOR"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("normal"), node.inputs["Normal"], base_dir, node_tab, created)
        return node
    
    elif construct == "normal_map":
        node = node_tree.nodes.new("ShaderNodeNormalMap")
        connect_slot(node_tree, param.get("color"), node.inputs["Color"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("strength"), node.inputs["Strength"], base_dir, node_tab, created)
        return node
    
    elif construct == "math":
        node = node_tree.nodes.new("ShaderNodeMath")
        node.operation = param.get("operation", "ADD")
        node.use_clamp = param.get("use_clamp", False)
        connect_slot(node_tree, param.get("value0"), node.inputs[0], base_dir, node_tab, created)
        if param.get("value1") is not None:
            connect_slot(node_tree, param.get("value1"), node.inputs[1], base_dir, node_tab, created)
        if param.get("value2") is not None and len(node.inputs) > 2:
            connect_slot(node_tree, param.get("value2"), node.inputs[2], base_dir, node_tab, created)
        return node
    
    elif construct == "gamma":
        node = node_tree.nodes.new("ShaderNodeGamma")
        connect_slot(node_tree, param.get("color"), node.inputs["Color"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("gamma"), node.inputs["Gamma"], base_dir, node_tab, created)
        return node
    
    elif construct == "clamp":
        node = node_tree.nodes.new("ShaderNodeClamp")
        connect_slot(node_tree, param.get("value"), node.inputs["Value"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("min"), node.inputs["Min"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("max"), node.inputs["Max"], base_dir, node_tab, created)
        return node
    
    elif construct == "combine_color":
        node = node_tree.nodes.new("ShaderNodeCombineColor")
        connect_slot(node_tree, param.get("channel0"), node.inputs["Red"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("channel1"), node.inputs["Green"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("channel2"), node.inputs["Blue"], base_dir, node_tab, created)
        return node
    
    elif construct == "combine_xyz":
        node = node_tree.nodes.new("ShaderNodeCombineXYZ")
        connect_slot(node_tree, param.get("x"), node.inputs["X"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("y"), node.inputs["Y"], base_dir, node_tab, created)
        connect_slot(node_tree, param.get("z"), node.inputs["Z"], base_dir, node_tab, created)
        return node
    
    print(f"Warning: Unknown converter construct '{construct}'")
    return None


def create_src_node(node_tree, desc):
    """Create a source node (tex_coord, geometry, camera)."""
    construct = desc.get("construct_name", "")
    
    if construct == "tex_coord":
        return node_tree.nodes.new("ShaderNodeTexCoord")
    elif construct == "geometry":
        return node_tree.nodes.new("ShaderNodeNewGeometry")
    elif construct == "camera":
        return node_tree.nodes.new("ShaderNodeCameraData")
    
    print(f"Warning: Unknown src_node construct '{construct}'")
    return None


def get_output_socket(node, output_key):
    """Get the output socket of a node by name or index."""
    if output_key and output_key in node.outputs:
        return node.outputs[output_key]
    # Default: first output
    if len(node.outputs) > 0:
        return node.outputs[0]
    return None


def ensure_node(node_tree, name, desc, base_dir, node_tab, created):
    """Ensure a node_tab entry is created as a Blender node, returning the node."""
    if name in created:
        return created[name]
    
    ntype = desc.get("type", "")
    node = None
    
    if ntype == "image":
        node = create_image_node(node_tree, desc, base_dir)
    elif ntype == "src_node":
        node = create_src_node(node_tree, desc)
    elif ntype == "converter":
        node = create_converter_node(node_tree, desc, base_dir, node_tab, created)
    elif ntype == "number":
        # Pure number nodes don't create Blender nodes — value set directly on socket
        node = None
    elif ntype == "separate_color":
        node = node_tree.nodes.new("ShaderNodeSeparateColor")
        connect_slot(node_tree, desc.get("param", {}).get("value"), node.inputs["Color"], base_dir, node_tab, created)
    elif ntype == "separate_xyz":
        node = node_tree.nodes.new("ShaderNodeSeparateXYZ")
        connect_slot(node_tree, desc.get("param", {}).get("value"), node.inputs["Vector"], base_dir, node_tab, created)
    
    if node is not None:
        node.name = name
        node.label = name
    
    created[name] = node
    return node


def connect_slot(node_tree, slot, target_socket, base_dir, node_tab, created):
    """Connect a Vision JSON slot to a Blender node socket.
    
    If the slot is a simple number, sets default_value.
    If it references a node, creates/finds the node and connects it.
    """
    if slot is None:
        return
    
    node_desc, output_key = resolve_slot(slot, node_tab)
    if node_desc is None:
        return
    
    ntype = node_desc.get("type", "")
    
    if ntype == "number":
        # Just set the default value, no node connection
        value = node_desc.get("param", {}).get("value")
        set_socket_value(target_socket, value)
        return
    
    # It's a real node — need to create and connect
    if not isinstance(slot, dict):
        return
    node_ref = slot.get("node")
    if isinstance(node_ref, str):
        # DAG format — use the name as key
        bl_node = ensure_node(node_tree, node_ref, node_desc, base_dir, node_tab, created)
    else:
        # Inline format — generate a unique name
        import hashlib
        key = hashlib.md5(str(node_desc).encode()).hexdigest()[:8]
        name = f"inline_{ntype}_{key}"
        bl_node = ensure_node(node_tree, name, node_desc, base_dir, node_tab, created)
    
    if bl_node is None:
        return
    
    out_socket = get_output_socket(bl_node, output_key)
    if out_socket and target_socket:
        node_tree.links.new(out_socket, target_socket)
