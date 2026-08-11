from fnpxr import Sdf

# USD input name -> Sdf.ValueTypeNames, consulted throughout USD construction (stage 3) whenever a shader
# input is created (_USD_create_shader_input and friends). Covers both the mtlx standard_surface inputs
# and the glPreview/UsdPreviewSurface ones - the two shaders share this one type table since a handful of
# names (e.g. "specular", "normal") mean the same type in both.
usdTypeMap = {
    # ----------------------------------------- mtlx standard
    "base": Sdf.ValueTypeNames.Float,
    "base_color": Sdf.ValueTypeNames.Color3f,
    "opacity": Sdf.ValueTypeNames.Float,
    "metalness": Sdf.ValueTypeNames.Float,
    "diffuse_roughness": Sdf.ValueTypeNames.Float,
    "specular": Sdf.ValueTypeNames.Float,
    "specular_color": Sdf.ValueTypeNames.Color3f,
    "specular_IOR": Sdf.ValueTypeNames.Float,
    "specular_anisotropy": Sdf.ValueTypeNames.Float,
    "specular_roughness": Sdf.ValueTypeNames.Float,
    "sheen": Sdf.ValueTypeNames.Float,
    "sheen_color": Sdf.ValueTypeNames.Color3f,  # beware: original Modo value (sheenTint) is Float, this override changes its type
    "sheen_roughness": Sdf.ValueTypeNames.Float,
    "coat": Sdf.ValueTypeNames.Float,
    "coat_roughness": Sdf.ValueTypeNames.Float,
    "emission": Sdf.ValueTypeNames.Float,
    "emission_color": Sdf.ValueTypeNames.Color3f,
    "transmission": Sdf.ValueTypeNames.Float,
    "transmission_scatter": Sdf.ValueTypeNames.Float,
    "transmission_dispersion": Sdf.ValueTypeNames.Float,
    "transmission_extra_roughness": Sdf.ValueTypeNames.Float,
    "transmission_color": Sdf.ValueTypeNames.Color3f,
    "transmission_depth": Sdf.ValueTypeNames.Float,
    "transmission_roughness": Sdf.ValueTypeNames.Float,
    "subsurface": Sdf.ValueTypeNames.Float,
    "subsurface_color": Sdf.ValueTypeNames.Color3f,
    "subsurface_radius": Sdf.ValueTypeNames.Float,
    "subsurface_scale": Sdf.ValueTypeNames.Float,
    "subsurface_anisotropy": Sdf.ValueTypeNames.Float,
    "thin_film_thickness": Sdf.ValueTypeNames.Float,
    "thin_film_IOR": Sdf.ValueTypeNames.Float,
    "thin_walled": Sdf.ValueTypeNames.Int,
    "normal": Sdf.ValueTypeNames.Vector3f,
    "in": Sdf.ValueTypeNames.Vector3f,
    "displacement": Sdf.ValueTypeNames.Float,
    "vectorDisplacement": Sdf.ValueTypeNames.Vector3f,

    # ----------------------------------------- glPreview
    "diffuseColor": Sdf.ValueTypeNames.Color3f,
    "emissive": Sdf.ValueTypeNames.Float,
    "emissiveColor": Sdf.ValueTypeNames.Color3f,
    "specularColor": Sdf.ValueTypeNames.Color3f,
    "metallic": Sdf.ValueTypeNames.Float,
    "roughness": Sdf.ValueTypeNames.Float,
    "clearcoat": Sdf.ValueTypeNames.Float,
    "clearcoatRoughness": Sdf.ValueTypeNames.Float,
    "ior": Sdf.ValueTypeNames.Float,
    "occlusion": Sdf.ValueTypeNames.Float,
    "opacityThreshold": Sdf.ValueTypeNames.Float,
}
