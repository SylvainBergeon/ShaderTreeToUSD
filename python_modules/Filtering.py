#python

import lx

filters = {}
filters [lx.symbol.sITYPE_ADVANCEDMATERIAL] = [
    "useRefIdx", # Important
    "brdfType", #Important
    "diffAmt",
    "diffCol",
    "specAmt",
    "specCol",
    "specRefIdx",
    "aniso",
    "rough",
    "specFres",
    "specTint",
    "coatAmt",
    "coatRough",
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
    "opacity",
    "disperse",
    "metallic",
    "tranAmt",
    "tranCol",
    "tranDist",
    "tranAmt",
    "tranRough"
    ]

filters[lx.symbol.sITYPE_MASK] = ["blend", "effect", "enable", "filter", "invert", "opacity", "ptag", "ptyp", "render", "submask"]
filters[lx.symbol.sITYPE_CONSTANT] = []
filters[lx.symbol.sITYPE_DEFAULTSHADER] = []
filters[lx.symbol.sITYPE_RENDEROUTPUT] = []