import copy

# Ported from ShaderTree.py's _USD_create_UV_texture, which looked up
# ShaderFilters.usdInputMap['uvTile'][...] for both tileU and tileV at construction time. This pass
# resolves it once, up front, and writes the result as a usdWrapMode attribute alongside the untouched
# raw Modo value. These are the real MaterialX ND_image uaddressmode/vaddressmode enum tokens
# (constant/clamp/periodic/mirror - verified against the standalone MaterialX standard library), NOT
# UsdUVTexture's native wrapS/wrapT tokens (black/clamp/repeat/mirror - see USD_NATIVE_WRAP_MODE_BY_TILE
# below). "reset" used to map to "black" here, a native-only token that doesn't exist in ND_image's
# enum - combined with ShaderTree.py authoring it under the wrong input names entirely (wrapS/wrapT
# instead of uaddressmode/vaddressmode), Modo's wrap mode never actually reached the mtlx render output.
USD_WRAP_MODE_BY_TILE = {
    "reset": "constant",
    "repeat": "periodic",
    "edge": "clamp",
    "mirror": "mirror",
}

# Native UsdUVTexture.wrapS/wrapT use "repeat", not MaterialX's "periodic" - every other token
# coincides. Used by the glPreview texture-reading network (_USD_create_preview_UV_texture), which
# reads UsdUVTexture directly rather than going through an ND_image_* MaterialX node.
USD_NATIVE_WRAP_MODE_BY_TILE = {
    "reset": "black",
    "repeat": "repeat",
    "edge": "clamp",
    "mirror": "mirror",
}


def normalize_uv_wrap_modes(xml):
    """Resolves every txtrLocator/channels/tileU and tileV to its USD wrap mode. Pure transformation,
    XML -> XML: returns a new tree, the input is left untouched."""
    xml = copy.deepcopy(xml)
    for tag in ('tileU', 'tileV'):
        for tileEl in xml.iter(tag):
            _normalize_tile_channel(tileEl)
    return xml


def _normalize_tile_channel(tileEl):
    tile = tileEl.get('value')
    tileEl.set('usdWrapMode', USD_WRAP_MODE_BY_TILE.get(tile, ""))
    tileEl.set('usdNativeWrapMode', USD_NATIVE_WRAP_MODE_BY_TILE.get(tile, ""))
