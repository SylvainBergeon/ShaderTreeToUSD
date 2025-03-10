import lx
from pxr import Sdf

filters = {}
filters [lx.symbol.sITYPE_ADVANCEDMATERIAL] = [
    "useRefIdx", # Important
    "brdfType",  #Important
    "specRefIdx",#boolean toggle refIndex/specAmount ?
    "diffAmt",
    "diffCol",
    "specAmt",
    "specCol",
    "refIndex",
    "aniso",
    "rough",
    "specFres",
    "specTint",
    "coatAmt",
    "coatRough",
    "radiance",
    "luminousAmt",
    "luminousCol",
    "metallic",
    "specCol",
    "scatterAmt",
    "disperse",
    "tranRough",
    "subsAmt",
    "subsCol",
    "subsDepth",
    "subsDist",
    "sheen",
    "sheenTint",
    "flatness",
    "opacity",
    "disperse",
    "metallic",
    "tranAmt",
    "tranCol",
    "tranDist",
    "tranAmt",
    "tranRough",
    "normal"
    ]
filters[lx.symbol.sITYPE_MASK] = [
    "blend",
    "effect",
    "enable",
    "filter",
    "invert",
    "opacity",
    "ptag",
    "ptyp",
    "render",
    "submask"
    ]
filters[lx.symbol.sITYPE_IMAGEMAP] = [
    "aa",
    "aaVal",
    "alpha",
    "blend",
    "blueInv",
    "brightness",
    "clamp",
    "contrast",
    "effect",
    "enable",
    "filter",
    "gamma",
    "greenInv",
    "ignSclGrp",
    "invert",
    "max",
    "min",
    "minSpot",
    "opacity",
    "pixBlend",
    "rawTextureAlpha",
    "rawTextureColor",
    "rawTextureValue",
    "redInv",
    "render",
    "rgba",
    "sourceHigh",
    "sourceLow",
    "swizzling",
    "textureAlpha",
    "textureColor",
    "textureValue"
    ]
filters[lx.symbol.sITYPE_VIDEOSTILL] = [
    "enable",
    "blend",
    "opacity",
    "filename",
    "format",
    "udim",
    "alphaMode",
    "colorRange",
    "colorspace",
    "fps",
    "imageStack",
    "interlace",
    "playback"
    ]
filters[lx.symbol.sITYPE_TEXTURELOC] = [
    "projType",
    #------------------------------------------------------ UV Projection
    "uvMap", "useUDIM",  "uvRotation", "wrapU", "wrapV", "tileU", "tileV",
    #------------------------------------------------------ Solid, Planar, spherical, Cylindrical ...
    "world", "worldMatrix", "worldXfrm", "wposMatrix", "wrotMatrix", "wsclMatrix",
    #------------------------------------------------------ Triplanar
    "triplanarBlending", 
    
]

filters[lx.symbol.sITYPE_DEFAULTSHADER] = []
filters[lx.symbol.sITYPE_RENDEROUTPUT] = []
filters[lx.symbol.sITYPE_CONSTANT] = []

channelTypeMap = {
    lx.symbol.iCHANTYPE_EVAL:       "eval",
    lx.symbol.iCHANTYPE_FLOAT:      "float",
    lx.symbol.iCHANTYPE_INTEGER:    "integer",
    lx.symbol.iCHANTYPE_GRADIENT:   "gradient",
    lx.symbol.iCHANTYPE_STORAGE:    "string",
    lx.symbol.iCHANTYPE_NONE:       "none"
}
usdInputMap = {
    "uvTile":{
        "reset":"black",
        "repeat":"periodic",
        "edge":"clamp",
        "mirror":"mirror"
    },
    "effect":{
        "diffColor":"base_color",
        "diffAmount":"base",
        "rough":"specular_roughness",
        "normal":"in",
        "objectNormal":"in",
        "bump":"normal",
        "stencil":"in",
        "specAmount":"specular",
        "reflFresnel":"specular",
        "specFresnel":"specular",
        "tranAmount":"transmission",
        "lumiAmount":"emission",
        "lumiColor":"emission_color",
        "specColor":"specular_color",
        "metallic":"metalness",
        "sheen":"sheen",
        "sheenTint":"sheen_color",
        "flatness":"sheen_roughness",
        "displace":"displacement"
    },
    "effect_gl":{
        "diffColor":"diffuseColor",
        "lumiColor":"emissiveColor",
        "specColor":"specularColor",
        "metallic":"metallic",
        "lumiAmount":"emissive",
        "rough":"roughness",
        "normal":"normal",
        "displace":"displacement"
    },
    "blend":{
        #--------------------------------------------------- Maths
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_MULTIPLY:"ND_multiply",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_DIVIDE:"ND_divide",
        #--------------------------------------------------- Maths
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_NORMAL:"ND_mix",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_ADD:"ND_plus",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_SUBTRACT:"ND_minus",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_SCREEN:"ND_screen",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_COLORBURN:"ND_burn",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_COLORDODGE:"ND_dodge",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_DIFFERENCE:"ND_difference",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_OVERLAY:"ND_overlay",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_DARKEN:"",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_HARDLIGHT:"",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_LIGHTEN:"",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_NORMALMULT:"",
        lx.symbol.sICVAL_TEXTURELAYER_BLEND_SOFTLIGHT:""
    }
}
usdTypeMap = {
    # ----------------------------------------- mtlx standard
    "base":Sdf.ValueTypeNames.Float,
    "base_color":Sdf.ValueTypeNames.Color3f,
    "opacity":Sdf.ValueTypeNames.Float,
    "metalness":Sdf.ValueTypeNames.Float,
    "diffuse_roughness":Sdf.ValueTypeNames.Float,
    "specular":Sdf.ValueTypeNames.Float,
    "specular_color":Sdf.ValueTypeNames.Color3f,
    "specular_IOR":Sdf.ValueTypeNames.Float,
    "specular_anisotropy":Sdf.ValueTypeNames.Float,
    "specular_roughness":Sdf.ValueTypeNames.Float,
    "sheen":Sdf.ValueTypeNames.Float,
    "sheen_color":Sdf.ValueTypeNames.Color3f, #----------- beware of this, original modo value (sheenTint) is Float, sheen_color override changes its type
    "sheen_roughness":Sdf.ValueTypeNames.Float,
    "coat":Sdf.ValueTypeNames.Float,
    "coat_roughness":Sdf.ValueTypeNames.Float,
    "emission":Sdf.ValueTypeNames.Float,
    "emission_color":Sdf.ValueTypeNames.Color3f,
    "transmission":Sdf.ValueTypeNames.Float,
    "transmission_scatter":Sdf.ValueTypeNames.Float,
    "transmission_dispersion":Sdf.ValueTypeNames.Float,
    "transmission_extra_roughness":Sdf.ValueTypeNames.Float,
    "transmission_color":Sdf.ValueTypeNames.Color3f,
    "transmission_depth":Sdf.ValueTypeNames.Float,
    "transmission_roughness":Sdf.ValueTypeNames.Float,
    "subsurface":Sdf.ValueTypeNames.Float,
    "subsurface_color":Sdf.ValueTypeNames.Color3f,
    "subsurface_radius":Sdf.ValueTypeNames.Float,
    "subsurface_scale":Sdf.ValueTypeNames.Float,
    "subsurface_anisotropy":Sdf.ValueTypeNames.Float,
    "thin_film_thickness":Sdf.ValueTypeNames.Float,
    "thin_film_IOR":Sdf.ValueTypeNames.Float,
    "thin_walled":Sdf.ValueTypeNames.Int,
    "normal":Sdf.ValueTypeNames.Vector3f,
    "in":Sdf.ValueTypeNames.Vector3f,
    "displacement":Sdf.ValueTypeNames.Float,
    # ----------------------------------------- glPreview
    "diffuseColor":Sdf.ValueTypeNames.Color3f,
    "emissive":Sdf.ValueTypeNames.Float,
    "emissiveColor":Sdf.ValueTypeNames.Color3f,
    "specularColor":Sdf.ValueTypeNames.Color3f,
    "metallic":Sdf.ValueTypeNames.Float,
    "roughness":Sdf.ValueTypeNames.Float,
    "clearcoat":Sdf.ValueTypeNames.Float,
    "clearcoatRoughness":Sdf.ValueTypeNames.Float,
    "ior":Sdf.ValueTypeNames.Float,
    "occlusion":Sdf.ValueTypeNames.Float,
}

stdMatChannelMap = {}
stdMatChannelMap[lx.symbol.sITYPE_ADVANCEDMATERIAL] = {
    "glPreview": { #----------------------------------- Mapping used for Principled shading mode
        #"useRefIdx":   "useSpecularWorkflow", # boolean toggle refIndex/specAmount ?
        "specCol":      "specularColor",
        "specTint":     "metallic",
        
        "diffCol":      "diffuseColor",
        "luminousAmt":  "emissive",
        "luminousCol":  "emissiveColor",
        "specAmt":      "specular", # (if useRefIdx = 0: specAmt)
        "rough":        "roughness",
        "refIndex":     "ior", # (if useRefIdx = 1 & specRefIdx = 1):refIndex or (if useRefIdx = 1 & specRefIdx = 0):1+specAmt
        "coatAmt":      "clearcoat",
        "coatRough":    "clearcoatRoughness",
        "opacity":      "opacity",
        "stencil":      "opacityThreshold",
        
        "normal":         "normal",
        "disp":         "displacement",
        "occ":          "occlusion"
        },

    "principled": { #----------------------------------- Mapping used for Principled shading mode
        "specRefIdx":   "", # boolean toggle refIndex/specAmount ?
        
        # =============================================== BASE
        "diffAmt":      "base",
        "diffCol":      "base_color",
        "opacity":      "opacity",
        "metallic":     "metalness",
        
        # =============================================== SPECULAR REFLECTIONS
        "specAmt":      "specular", # (if useRefIdx = 0: specAmt)
        "specCol":      "specular_color",
        "refIndex":     "specular_IOR", # (if useRefIdx = 1 & specRefIdx = 1):refIndex or (if useRefIdx = 1 & specRefIdx = 0):1+specAmt
        "aniso":        "specular_anisotropy",
        "rough":        "specular_roughness",
        
        # =============================================== COAT
        "coatAmt":      "coat",
        "coatRough":    "coat_roughness",
        
        # =============================================== EMISSION
        "luminousAmt":  "emission",
        "luminousCol":  "emission_color",
        
        # =============================================== SHEEN
        "sheen":"sheen",
        "sheenTint":"sheen_color",
        "flatness":"sheen_roughness",
        
        # =============================================== TRANSMISSION
        "tranAmt":      "transmission",
        "scatterAmt":   "transmission_scatter",
        "disperse":     "transmission_dispersion",
        "tranRough":    "transmission_extra_roughness",
        "tranCol":      "transmission_color",
        "tranDist":     "transmission_depth",
        "tranRough":    "transmission_roughness",
        "stencil":      "opacity",
        
        # =============================================== SSS
        "subsAmt":      "subsurface",
        "subsCol":      "subsurface_color",
        "subsDepth":    "subsurface_radius",
        "subsDist":     "subsurface_scale",
        # # =============================================== surface
        "normal":       "normal",
        "disp":         "displacement"
        },
    
    "gtr": { #----------------------------------- Mapping used for PBR shading mode
        "opacity":      "opacity",
        # =============================================== BASE
        "diffAmt":      "base",
        "diffCol":      "base_color",
        #"diffRough":    "diffuse_roughness", (diffRough is not available in modo pbr, only in modo energy conserving)
        #"metallic":     "metalness", (metallic is not supported in Modo PBR but is in mtlxStandardSurface !!)
        # =============================================== SPECULAR REFLECTIONS
        "specAmt":      "specular",
        "specCol":      "specular_color",
        "rough":        "specular_roughness",
        "refIndex":     "specular_IOR",
        "aniso":        "specular_anisotropy",
        #"aniso":        "specular_rotation", (specular rotation only exist in modo pbr through uv map ?)
        #"specTint":     "", (specTint is not available in modo pbr)
        
        # =============================================== COAT
        "coatAmt":      "coat",
        "coatRough":    "coat_roughness",
        
        # # =============================================== TRANSMISSION
        "tranAmt":      "transmission",
        "tranCol":      "transmission_color",
        "tranDist":     "transmission_depth",
        "scatterAmt":   "transmission_scatter",
        "disperse":     "transmission_dispersion",
        "tranRough":    "transmission_extra_roughness",
        "stencil":      "opacity",
        
        # # =============================================== EMISSION
        "radiance":     "emission",
        "luminousCol":  "emission_color",
        
        # # =============================================== SSS
        "subsAmt":      "subsurface",
        "subsCol":      "subsurface_color",
        "subsDepth":    "subsurface_radius",
        "subsDist":     "subsurface_scale",
        
        # # =============================================== surface
        "normal":       "normal",
        "disp":         "displacement",
        }
    }
stdMatChannelMap[lx.symbol.sITYPE_MASK] = {
    "blend":        "",
    "effect":       "",
    "enable":       "",
    "filter":       "",
    "invert":       "",
    "opacity":      "",
    "ptag":         "",
    "ptyp":         "",
    "render":       "",
    "submask":      ""
    }
stdMatChannelMap[lx.symbol.sITYPE_TEXTURELOC] = {
    "uvMap":        "",
    "useUDIM":      "",
    "uvRotation":   "",
    "wrapU":        "",
    "wrapV":        "",
    "tileU":        "Wraps",
    "tileV":        "Wrapt"
}

stdMatChannelMap[lx.symbol.sITYPE_CONSTANT] = {}
stdMatChannelMap[lx.symbol.sITYPE_DEFAULTSHADER] = {}
stdMatChannelMap[lx.symbol.sITYPE_RENDEROUTPUT] = {}