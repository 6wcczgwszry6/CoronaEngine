"""Import Vision JSON materials into Blender."""
import bpy
from . import shadernode


def import_diffuse(node_tree, param, base_dir, node_tab, created):
    """Create a Diffuse BSDF node."""
    bsdf = node_tree.nodes.new("ShaderNodeBsdfDiffuse")
    shadernode.connect_slot(node_tree, param.get("color"), bsdf.inputs["Color"],
                            base_dir, node_tab, created)
    shadernode.connect_slot(node_tree, param.get("roughness"), bsdf.inputs["Roughness"],
                            base_dir, node_tab, created)
    return bsdf


def import_principled(node_tree, param, base_dir, node_tab, created):
    """Create a Principled BSDF node with all supported parameters."""
    bsdf = node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    
    mapping = {
        "color": "Base Color",
        "roughness": "Roughness",
        "ior": "IOR",
        "metallic": "Metallic",
        "spec_tint": "Specular Tint",
        "anisotropic": "Anisotropic",
        "normal": "Normal",
        "sheen_weight": "Sheen Weight",
        "sheen_roughness": "Sheen Roughness",
        "sheen_tint": "Sheen Tint",
        "coat_weight": "Coat Weight",
        "coat_roughness": "Coat Roughness",
        "coat_ior": "Coat IOR",
        "coat_tint": "Coat Tint",
        "subsurface_weight": "Subsurface Weight",
        "subsurface_radius": "Subsurface Radius",
        "subsurface_scale": "Subsurface Scale",
        "transmission_weight": "Transmission Weight",
    }
    
    for json_key, socket_name in mapping.items():
        slot = param.get(json_key)
        if slot is not None and socket_name in bsdf.inputs:
            shadernode.connect_slot(node_tree, slot, bsdf.inputs[socket_name],
                                    base_dir, node_tab, created)
    return bsdf


def import_substrate(node_tree, param, base_dir, node_tab, created):
    """Map Vision substrate to a Principled BSDF using substrate color."""
    bsdf = node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    shadernode.connect_slot(node_tree, param.get("color"), bsdf.inputs["Base Color"],
                            base_dir, node_tab, created)
    shadernode.connect_slot(node_tree, param.get("roughness"), bsdf.inputs["Roughness"],
                            base_dir, node_tab, created)
    return bsdf


def import_glass(node_tree, param, base_dir, node_tab, created):
    """Create a Glass BSDF node."""
    bsdf = node_tree.nodes.new("ShaderNodeBsdfGlass")
    shadernode.connect_slot(node_tree, param.get("color"), bsdf.inputs["Color"],
                            base_dir, node_tab, created)
    shadernode.connect_slot(node_tree, param.get("roughness"), bsdf.inputs["Roughness"],
                            base_dir, node_tab, created)
    shadernode.connect_slot(node_tree, param.get("ior"), bsdf.inputs["IOR"],
                            base_dir, node_tab, created)
    return bsdf


def import_mirror(node_tree, param, base_dir, node_tab, created):
    """Create a Glossy BSDF node (mirror)."""
    bsdf = node_tree.nodes.new("ShaderNodeBsdfGlossy")
    shadernode.connect_slot(node_tree, param.get("color"), bsdf.inputs["Color"],
                            base_dir, node_tab, created)
    shadernode.connect_slot(node_tree, param.get("roughness"), bsdf.inputs["Roughness"],
                            base_dir, node_tab, created)
    if "Anisotropy" in bsdf.inputs:
        shadernode.connect_slot(node_tree, param.get("anisotropic"), bsdf.inputs["Anisotropy"],
                                base_dir, node_tab, created)
    return bsdf


def import_mix(node_tree, param, base_dir, node_tab, created):
    """Create a Mix Shader node with two sub-materials."""
    mix = node_tree.nodes.new("ShaderNodeMixShader")
    shadernode.connect_slot(node_tree, param.get("frac"), mix.inputs[0],
                            base_dir, node_tab, created)
    # Import the two sub-materials
    mat0_desc = param.get("mat0")
    mat1_desc = param.get("mat1")
    if mat0_desc:
        bsdf0 = import_material_desc(node_tree, mat0_desc, base_dir, node_tab, created)
        if bsdf0:
            node_tree.links.new(bsdf0.outputs[0], mix.inputs[1])
    if mat1_desc:
        bsdf1 = import_material_desc(node_tree, mat1_desc, base_dir, node_tab, created)
        if bsdf1:
            node_tree.links.new(bsdf1.outputs[0], mix.inputs[2])
    return mix


def import_emission(node_tree, param, base_dir, node_tab, created):
    """Create an Emission node."""
    emission = node_tree.nodes.new("ShaderNodeEmission")
    shadernode.connect_slot(node_tree, param.get("color"), emission.inputs["Color"],
                            base_dir, node_tab, created)
    scale = param.get("scale", 1.0)
    if isinstance(scale, (int, float)):
        emission.inputs["Strength"].default_value = scale
    return emission


func_tab = {
    "diffuse": import_diffuse,
    "principled_bsdf": import_principled,
    "substrate": import_substrate,
    "glass": import_glass,
    "mirror": import_mirror,
    "mix": import_mix,
}


def import_material_desc(node_tree, desc, base_dir, node_tab, created):
    """Import a material descriptor (can be top-level or nested in mix)."""
    mat_type = desc.get("type", "diffuse")
    param = desc.get("param", {})
    # Merge material-level node_tab with top-level
    mat_node_tab = desc.get("node_tab", {})
    merged_tab = {**node_tab, **mat_node_tab}
    
    if mat_type in func_tab:
        return func_tab[mat_type](node_tree, param, base_dir, merged_tab, created)
    else:
        print(f"Warning: Unsupported material type '{mat_type}', using diffuse fallback")
        return import_diffuse(node_tree, param, base_dir, merged_tab, created)


def import_material(mat_desc, base_dir):
    """Create a Blender material from a Vision JSON material descriptor.
    
    Returns the created bpy.types.Material.
    """
    name = mat_desc.get("name", "Material")
    mat_type = mat_desc.get("type", "diffuse")
    param = mat_desc.get("param", {})
    node_tab = mat_desc.get("node_tab", {})
    created = {}  # Track created Blender nodes by name
    
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    node_tree = mat.node_tree
    
    # Clear default nodes
    for node in node_tree.nodes:
        node_tree.nodes.remove(node)
    
    # Create the output node
    output = node_tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (300, 0)
    
    # Handle "add" type (material + emission → Add Shader)
    if mat_type == "add":
        add_shader = node_tree.nodes.new("ShaderNodeAddShader")
        add_shader.location = (100, 0)
        node_tree.links.new(add_shader.outputs[0], output.inputs["Surface"])
        
        mat_inner = param.get("material", {})
        emission_desc = param.get("emission", {})
        
        bsdf = import_material_desc(node_tree, mat_inner, base_dir, node_tab, created)
        if bsdf:
            bsdf.location = (-200, 100)
            node_tree.links.new(bsdf.outputs[0], add_shader.inputs[0])
        
        emission = import_emission(node_tree, emission_desc.get("param", emission_desc),
                                   base_dir, node_tab, created)
        if emission:
            emission.location = (-200, -100)
            node_tree.links.new(emission.outputs[0], add_shader.inputs[1])
    else:
        bsdf = import_material_desc(node_tree, mat_desc, base_dir, node_tab, created)
        if bsdf:
            bsdf.location = (-200, 0)
            node_tree.links.new(bsdf.outputs[0], output.inputs["Surface"])
    
    return mat
