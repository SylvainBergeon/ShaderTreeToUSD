import copy

# Ported from ShaderTree.py's _USD_create_UV_texture, which looked up
# ShaderFilters.usdInputMap['uvTile'][...] for both tileU and tileV at construction time. This pass
# resolves it once, up front, and writes the result as a usdWrapMode attribute alongside the untouched
# raw Modo value. The table below mirrors usdInputMap['uvTile'] (plain string keys, no lx.symbol
# involved), duplicated here so this pass has zero dependency on lx/modo/fnpxr.
USD_WRAP_MODE_BY_TILE = {
    "reset": "black",
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
    tileEl.set('usdWrapMode', USD_WRAP_MODE_BY_TILE.get(tile, ""))
