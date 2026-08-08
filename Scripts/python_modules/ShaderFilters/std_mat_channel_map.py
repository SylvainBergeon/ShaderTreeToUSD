import lx

# Modo channel name -> USD input name, per item type and (for advancedMaterial) per brdfType. Consulted
# by _UTIL_get_mapped_channel (stage 3, during shader construction) to decide which USD shader input a
# given Modo channel feeds, and by _USD_connect_effect_stack's reverse lookup (Modo channel name from a
# resolved USD input name) for the no-texture-connected fallback - see CLAUDE.md's still-open "decision 4"
# about that reverse lookup reading raw values instead of the gtr/principled-overridden ones.
stdMatChannelMap = {}

stdMatChannelMap[lx.symbol.sITYPE_ADVANCEDMATERIAL] = {
    "glPreview": {  # ----------------------------------- Mapping used for the UsdPreviewSurface shader
        # "useRefIdx":  "useSpecularWorkflow", # boolean toggle refIndex/specAmount ?
        # specAmt/luminousAmt have no direct UsdPreviewSurface input (no standalone specular/emissive
        # intensity, only specularColor/emissiveColor) - normalize_specular_ior folds them into
        # specCol/luminousCol's usdPreviewValue instead (specularColor = specCol * specAmt, etc.).
        "specCol":    "specularColor",
        "specTint":   "metallic",

        "diffCol":    "diffuseColor",
        "luminousCol": "emissiveColor",
        "rough":      "roughness",
        "refIndex":   "ior",  # (if useRefIdx = 1 & specRefIdx = 1): refIndex, or (if useRefIdx = 1 & specRefIdx = 0): 1+specAmt
        "coatAmt":    "clearcoat",
        "coatRough":  "clearcoatRoughness",
        "opacity":    "opacity",
        "stencil":    "opacityThreshold",

        "normal":     "normal",
        "disp":       "displacement",
        "occ":        "occlusion",
    },

    "principled": {  # ----------------------------------- Mapping used for Principled shading mode
        "specRefIdx": "",  # boolean toggle refIndex/specAmount ?

        # =============================================== BASE
        "diffAmt":    "base",
        "diffCol":    "base_color",
        "opacity":    "opacity",
        "metallic":   "metalness",

        # =============================================== SPECULAR REFLECTIONS
        "specAmt":    "specular",  # (if useRefIdx = 0: specAmt)
        "specCol":    "specular_color",
        "refIndex":   "specular_IOR",  # (if useRefIdx = 1 & specRefIdx = 1): refIndex, or (if useRefIdx = 1 & specRefIdx = 0): 1+specAmt
        "aniso":      "specular_anisotropy",
        "rough":      "specular_roughness",

        # =============================================== COAT
        "coatAmt":    "coat",
        "coatRough":  "coat_roughness",

        # =============================================== EMISSION
        "luminousAmt": "emission",
        "luminousCol": "emission_color",

        # =============================================== SHEEN
        "sheen":      "sheen",
        "sheenTint":  "sheen_color",
        "flatness":   "sheen_roughness",

        # =============================================== TRANSMISSION
        "tranAmt":    "transmission",
        "scatterAmt": "transmission_scatter",
        "disperse":   "transmission_dispersion",
        "tranRough":  "transmission_roughness",  # the dict literal used to also set "tranRough" to
                                                  # "transmission_extra_roughness" a few lines above this
                                                  # one - a dead duplicate key, silently shadowed by this
                                                  # one in the original code (last write wins)
        "tranCol":    "transmission_color",
        "tranDist":   "transmission_depth",

        # =============================================== SSS
        "subsAmt":    "subsurface",
        "subsCol":    "subsurface_color",
        "subsDepth":  "subsurface_radius",
        "subsDist":   "subsurface_scale",

        # =============================================== SURFACE
        "stencil":    "opacity",
        "normal":     "normal",
        "disp":       "displacement",
    },

    "gtr": {  # ----------------------------------- Mapping used for PBR shading mode
        # =============================================== BASE
        "diffAmt":    "base",
        "diffCol":    "base_color",
        # "diffRough": "diffuse_roughness", (diffRough is not available in modo pbr, only in modo energy conserving)
        # "metallic":  "metalness", (metallic is not supported in Modo PBR but is in mtlxStandardSurface !!)

        # =============================================== SPECULAR REFLECTIONS
        "specAmt":    "specular",
        "specCol":    "specular_color",
        "rough":      "specular_roughness",
        "refIndex":   "specular_IOR",
        "aniso":      "specular_anisotropy",
        # "aniso":     "specular_rotation", (specular rotation only exists in modo pbr through a uv map ?)
        # "specTint":  "", (specTint is not available in modo pbr)

        # =============================================== COAT
        "coatAmt":    "coat",
        "coatRough":  "coat_roughness",

        # =============================================== TRANSMISSION
        "tranAmt":    "transmission",
        "tranCol":    "transmission_color",
        "tranDist":   "transmission_depth",
        "scatterAmt": "transmission_scatter",
        "disperse":   "transmission_dispersion",
        "tranRough":  "transmission_extra_roughness",
        "stencil":    "opacity",

        # =============================================== EMISSION
        "radiance":   "emission",
        "luminousCol": "emission_color",

        # =============================================== SSS
        "subsAmt":    "subsurface",
        "subsCol":    "subsurface_color",
        "subsDepth":  "subsurface_radius",
        "subsDist":   "subsurface_scale",

        # =============================================== SURFACE
        "normal":     "normal",
        "disp":       "displacement",
    },
}

stdMatChannelMap[lx.symbol.sITYPE_MASK] = {
    "blend":   "",
    "effect":  "",
    "enable":  "",
    "filter":  "",
    "invert":  "",
    "opacity": "",
    "ptag":    "",
    "ptyp":    "",
    "render":  "",
    "submask": "",
}

stdMatChannelMap[lx.symbol.sITYPE_TEXTURELOC] = {
    "uvMap":      "",
    "useUDIM":    "",
    "uvRotation": "",
    "wrapU":      "",
    "wrapV":      "",
    "tileU":      "Wraps",
    "tileV":      "Wrapt",
}

stdMatChannelMap[lx.symbol.sITYPE_CONSTANT] = {}
stdMatChannelMap[lx.symbol.sITYPE_DEFAULTSHADER] = {}
stdMatChannelMap[lx.symbol.sITYPE_RENDEROUTPUT] = {}
