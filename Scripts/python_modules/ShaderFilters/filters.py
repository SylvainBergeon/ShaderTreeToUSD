import lx

# NOT CURRENTLY USED ANYWHERE. Not imported by ShaderTree.py or any normalize/*.py pass - grep the repo
# to confirm before trusting this comment if it's been a while. _JSON_get_channels's docstring still
# references a "preFilterChannels" flag that would have consulted this table to only export channels
# relevant to an item's type, but no such flag exists in the code today - every channel gets exported
# unconditionally instead (see _JSON_get_channels/_XML_get_channels).
#
# Kept as-is (not deleted) pending a decision: either revive the filtering behavior described above, or
# remove this table for good.
filters = {}

filters[lx.symbol.sITYPE_ADVANCEDMATERIAL] = [
    "useRefIdx",  # Important
    "brdfType",   # Important
    "specRefIdx", # boolean toggle refIndex/specAmount ?
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
    "normal",
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
    "submask",
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
    "textureValue",
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
    "playback",
]

filters[lx.symbol.sITYPE_TEXTURELOC] = [
    "projType",
    # ------------------------------------------------------ UV Projection
    "uvMap", "useUDIM", "uvRotation", "wrapU", "wrapV", "tileU", "tileV",
    # ------------------------------------------------------ Solid, Planar, spherical, Cylindrical ...
    "world", "worldMatrix", "worldXfrm", "wposMatrix", "wrotMatrix", "wsclMatrix",
    # ------------------------------------------------------ Triplanar
    "triplanarBlending",
]

filters[lx.symbol.sITYPE_DEFAULTSHADER] = []
filters[lx.symbol.sITYPE_RENDEROUTPUT] = []
filters[lx.symbol.sITYPE_CONSTANT] = []
