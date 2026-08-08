import copy

# Ported from ShaderTree.py's _USD_connect_texture_output_to_shader_input / _USD_connect_effect_stack,
# which both look up channels/effect's value in ShaderFilters.usdInputMap['effect'] at construction time.
# This pass resolves it once, up front, and writes the result as a usdInputName attribute (mtlx shader)
# and a usdPreviewInputName attribute (glPreview/UsdPreviewSurface shader), alongside the untouched raw
# Modo effect name.
#
# The tables below mirror ShaderFilters.usdInputMap['effect'] and ['effect_gl'] (plain string keys, no
# lx.symbol involved - unlike usdInputMap['blend']), duplicated here so this pass has zero dependency on
# lx/modo/fnpxr: importing ShaderFilters directly would still pull in `import lx` at module level for its
# other, lx-keyed tables. usdInputMap['effect_gl'] was dead code in ShaderFilters/input_map.py (defined,
# never consulted anywhere) - the glPreview shader was only ever connected for the bump/normal effects,
# hardcoded inline in _USD_connect_texture_output_to_shader_input; every other texture-driven effect
# (diffuse color, roughness, specular color, metallic, emission) never reached the preview shader at all.
#
# Deliberately out of scope for now: _USD_connect_effect_stack also does a *reverse* lookup, from the
# resolved usdInputName back into stdMatChannelMap[...]['principled'] (~30 entries), to read the
# advancedMaterial's own default value as a fallback when no texture is connected. That table is bigger,
# also lives in ShaderFilters/std_mat_channel_map.py, and duplicating it here risks drifting from the
# source of truth - left for when CLAUDE.md's "where do ShaderFilters tables live" decision is settled.
USD_INPUT_NAME_BY_EFFECT = {
    "diffColor": "base_color",
    "diffAmount": "base",
    "rough": "specular_roughness",
    "normal": "normal",
    "objectNormal": "in",
    "bump": "normal",
    "stencil": "opacity",
    "specAmount": "specular",
    "reflFresnel": "specular",
    "specFresnel": "specular",
    "tranAmount": "transmission",
    "lumiAmount": "emission",
    "lumiColor": "emission_color",
    "specColor": "specular_color",
    "metallic": "metalness",
    "sheen": "sheen",
    "sheenTint": "sheen_color",
    "flatness": "sheen_roughness",
    "displace": "displacement",
}

USD_PREVIEW_INPUT_NAME_BY_EFFECT = {
    "diffColor": "diffuseColor",
    "lumiColor": "emissiveColor",
    "specColor": "specularColor",
    "metallic": "metallic",
    "lumiAmount": "emissive",
    "rough": "roughness",
    "normal": "normal",
    "displace": "displacement",
}


def normalize_effect_channel_names(xml):
    """Resolves every channels/effect to its mtlx input name (usdInputName) and its glPreview/
    UsdPreviewSurface input name (usdPreviewInputName, empty if this effect has no preview equivalent).
    Pure transformation, XML -> XML: returns a new tree, the input is left untouched."""
    xml = copy.deepcopy(xml)
    for effectEl in xml.iter('effect'):
        _normalize_effect_channel(effectEl)
    return xml


def _normalize_effect_channel(effectEl):
    effect = effectEl.get('value')
    effectEl.set('usdInputName', USD_INPUT_NAME_BY_EFFECT.get(effect, ""))
    effectEl.set('usdPreviewInputName', USD_PREVIEW_INPUT_NAME_BY_EFFECT.get(effect, ""))
