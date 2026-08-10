import copy

# Native UsdUVTexture.wrapS/wrapT tokens (black/clamp/repeat/mirror - verified against usd-core's
# shaderDefs.usda). Used by the glPreview texture-reading network (_USD_create_preview_UV_texture), which
# reads UsdUVTexture directly.
USD_NATIVE_WRAP_MODE_BY_TILE = {
    "reset": "black",
    "repeat": "repeat",
    "edge": "clamp",
    "mirror": "mirror",
}

# MaterialX ND_image's uaddressmode/vaddressmode enum (constant/clamp/periodic/mirror - verified against
# the real MaterialX standard library, see node_registry.py). Used by the mtlx render path
# (_USD_create_UV_texture): "reset" maps to "constant", not the native table's "black" - that's a
# UsdUVTexture-specific token, not a valid value in ND_image's enum. "repeat" maps to "periodic", the
# MaterialX name for the same behavior.
USD_WRAP_MODE_BY_TILE = {
    "reset": "constant",
    "repeat": "periodic",
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
    tileEl.set('usdNativeWrapMode', USD_NATIVE_WRAP_MODE_BY_TILE.get(tile, ""))
    tileEl.set('usdWrapMode', USD_WRAP_MODE_BY_TILE.get(tile, ""))
