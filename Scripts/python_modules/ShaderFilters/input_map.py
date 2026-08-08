# NOT CURRENTLY USED ANYWHERE. Not imported by ShaderTree.py - grep the repo to confirm before trusting
# this comment if it's been a while. Both tables below have already been superseded by a normalize/ pass
# that duplicates the same data and resolves it ahead of time onto the normalized XML instead:
#   "uvTile"    -> Scripts/python_modules/normalize/uv_wrap_modes.py     (USD_WRAP_MODE_BY_TILE)
#   "effect_gl" -> Scripts/python_modules/normalize/effect_channel_names.py (USD_PREVIEW_INPUT_NAME_BY_EFFECT)
#
# "blend" and "effect" used to live here too, superseded the same way by normalize_blend_operators.py /
# normalize_effect_channel_names.py - those two were already removed once construction stopped reading
# them (see CLAUDE.md). uvTile/effect_gl were left behind at the time and are being kept here now, same
# as filters.py, pending a decision: delete for good, or is there still a reason to keep a copy of this
# data outside normalize/?
usdInputMap = {
    "uvTile": {
        "reset": "black",
        "repeat": "periodic",
        "edge": "clamp",
        "mirror": "mirror",
    },
    "effect_gl": {
        "diffColor": "diffuseColor",
        "lumiColor": "emissiveColor",
        "specColor": "specularColor",
        "metallic": "metallic",
        "lumiAmount": "emissive",
        "rough": "roughness",
        "normal": "normal",
        "displace": "displacement",
    },
}
