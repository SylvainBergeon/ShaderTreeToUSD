#python

import lx

channelTypeMap = {
    lx.symbol.iCHANTYPE_EVAL:       "eval",
    lx.symbol.iCHANTYPE_FLOAT:      "float",
    lx.symbol.iCHANTYPE_INTEGER:    "integer",
    lx.symbol.iCHANTYPE_GRADIENT:   "gradient",
    lx.symbol.iCHANTYPE_STORAGE:    "string",
    lx.symbol.iCHANTYPE_NONE:       "none"
}

channelMap = {}
channelMap [lx.symbol.sITYPE_ADVANCEDMATERIAL] = {
    "principled": { #----------------------------------- Mapping used for Principled shading mode
        "diffAmt":      "base",
        "diffCol":      "base_color",
        "specAmt":      "specular",
        "specCol":      "specular_color",
        "rough":        "specular_roughness",
        "specRefIdx":   "specular_IOR",
        "aniso":        "specular_anisotroy",
        "specFres":     "",
        "specTint":     "",
        "coatAmt":      "coat",
        "coatRough":    "coat_roughness",
        "luminousAmt":  "emission",
        "luminousCol":  "emission_color",
        "metallic":     "metalness",
        "tranAmt":      "transmission",
        "aniso":        "specular_anisotropy",
        "rough":        "diffuse_roughness",
        "scatterAmt":   "transmission_scatter",
        "disperse":     "transmission_dispersion",
        "tranRough":    "transmission_extra_roughness",
        "subsAmt":      "subsurface",
        "subsCol":      "subsurface_color",
        "subsDepth":    "subsurface_radius",
        "subsDist":     "subsurface_scale",
        "sheen":        "sheen",
        "sheenTint":    "sheen_color",
        "opacity":      "opacity",
        "disperse":     "dispersion",
        "metallic":     "metalness",
        "tranCol":      "transmission_color",
        "tranDist":     "transmission_depth",
        "tranAmt":      "transmission",
        "tranRough":    "transmission_roughness"
        },
    "gtr": { #----------------------------------- Mapping used for PBR shading mode
        "diffAmt":      "base",
        "diffCol":      "base_color",
        "specAmt":      "specular",
        "specCol":      "specular_color",
        "rough":        "specular_roughness",
        "specRefIdx":   "specular_IOR",
        "aniso":        "specular_anisotroy",
        "specFres":     "",
        "specTint":     "",
        "coatAmt":      "coat",
        "coatRough":    "coat_roughness",
        "luminousAmt":  "emission",
        "luminousCol":  "emission_color",
        "metallic":     "metalness",
        "tranAmt":      "transmission",
        "aniso":        "specular_anisotropy",
        "rough":        "diffuse_roughness",
        "scatterAmt":   "transmission_scatter",
        "disperse":     "transmission_dispersion",
        "tranRough":    "transmission_extra_roughness",
        "subsAmt":      "subsurface",
        "subsCol":      "subsurface_color",
        "subsDepth":    "subsurface_radius",
        "subsDist":     "subsurface_scale",
        "sheen":        "sheen",
        "sheenTint":    "sheen_color",
        "opacity":      "opacity",
        "disperse":     "dispersion",
        "metallic":     "metalness",
        "tranCol":      "transmission_color",
        "tranDist":     "transmission_depth",
        "tranAmt":      "transmission",
        "tranRough":    "transmission_roughness"
        }
    }

channelMap[lx.symbol.sITYPE_MASK] = {
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
channelMap[lx.symbol.sITYPE_CONSTANT] = {}
channelMap[lx.symbol.sITYPE_DEFAULTSHADER] = {}
channelMap[lx.symbol.sITYPE_RENDEROUTPUT] = {}