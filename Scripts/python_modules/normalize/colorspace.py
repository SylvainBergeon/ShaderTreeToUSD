import copy

# Ported from ShaderTree.py's texture-creation functions (_USD_create_UV_texture/_USD_create_preview_UV_
# texture), which will read Modo's videoStill/channels/colorspace value at construction time. This pass
# resolves it once, up front, and writes the result as a usdColorSpace attribute alongside the untouched
# raw Modo value.
#
# Modo's "(default)" sentinel does NOT mean "no colorspace transformation" - it resolves to one of 4
# Preferences > Color Management settings depending on the image's own bit depth (confirmed live by the
# author: 8bit/16bit/numeric -> sRGB, float -> linear, on one real installation - scene/installation-wide,
# not a small fixed enum, so not something this pass can hardcode). Resolving it needs those 4 live values
# - queried in Stage 1 (ShaderTree.py's _initialize_colormanagement_defaults, the one part of this that
# genuinely can't move here: it's an lx.eval() call, and this pass has zero lx/modo/fnpxr dependency like
# every other one in normalize/) - passed into this pass as colorspaceDefaultByCategory rather than
# queried by it, so the pass itself stays a plain, pytest-testable function of its arguments.
#
# Any value other than "(default)" is an explicit override, already a real colorspace name chosen from
# whatever OCIO config is registered in the scene's color management preferences (queried live from Modo:
# several configs can be registered on the same scene at once - aces, foundry-v1, Foundry-WideGamut,
# nuke-default, spi-anim, spi-vfx observed - with no small fixed enum of names to map from the way wrap
# modes or blend operators have, so those are passed through as-is rather than translated.
MODO_DEFAULT_COLORSPACE = "(default)"
USD_RAW_COLORSPACE = "raw"

# Modo doesn't expose an image's actual bit depth in the channels extracted in Stage 1, so this
# approximates it from the videoStill's own "format" channel instead. Not airtight (e.g. PNG/TIFF can be
# 8 or 16-bit) but covers the common cases - falls back to "8bit" (the most common case for ordinary
# color textures) for anything not listed here.
MODO_FORMAT_COLORSPACE_CATEGORY = {
    "PNG": "8bit", "JPG": "8bit", "JPEG": "8bit", "TGA": "8bit", "BMP": "8bit", "GIF": "8bit",
    "TIFF": "16bit", "TIF": "16bit", "PSD": "16bit", "DPX": "16bit", "CIN": "16bit",
    "EXR": "float", "HDR": "float", "RADIANCE": "float", "PFM": "float",
}


def normalize_colorspace(xml, colorspaceDefaultByCategory=None):
    """Resolves every videoStill/channels/colorspace to its USD colorspace value: for Modo's "(default)"
    sentinel, looks up colorspaceDefaultByCategory (Stage 1's 4 live-queried color management
    preferences, category approximated from the videoStill's own "format" channel), falling back to
    "raw" if that dict is missing/incomplete; passed through unchanged otherwise. Pure transformation,
    XML -> XML: returns a new tree, the input is left untouched."""
    xml = copy.deepcopy(xml)
    colorspaceDefaultByCategory = colorspaceDefaultByCategory or {}
    for videoStillEl in xml.iter('videoStill'):
        _normalize_video_still_colorspace(videoStillEl, colorspaceDefaultByCategory)
    return xml


def _normalize_video_still_colorspace(videoStillEl, colorspaceDefaultByCategory):
    colorspaceEl = videoStillEl.find('channels/colorspace')
    if colorspaceEl is None:
        return

    colorspace = colorspaceEl.get('value')
    if colorspace == MODO_DEFAULT_COLORSPACE:
        formatEl = videoStillEl.find('channels/format')
        formatValue = formatEl.get('value') if formatEl is not None else ""
        category = MODO_FORMAT_COLORSPACE_CATEGORY.get(formatValue.upper(), "8bit")
        usdColorSpace = colorspaceDefaultByCategory.get(category) or USD_RAW_COLORSPACE
    else:
        usdColorSpace = colorspace

    colorspaceEl.set('usdColorSpace', usdColorSpace)
