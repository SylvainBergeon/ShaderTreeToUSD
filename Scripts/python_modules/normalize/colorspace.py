import copy

# Ported from ShaderTree.py's texture-creation functions (_USD_create_UV_texture/_USD_create_preview_UV_
# texture), which read Modo's videoStill/channels/colorspace value at construction time. This pass
# resolves it once, up front, and writes the result as a usdColorSpace attribute alongside the untouched
# raw Modo value.
#
# Maps Modo's own per-texture colorspace choice (the literal value of videoStill/channels/colorspace,
# whatever the user picked in Modo's dropdown - "(default)", "linear", "sRGB", "sRGBf", "Rec 709", ...)
# to a value that will actually mean something as mtlx "colorSpace" metadata (UsdAttribute.SetColorSpace()
# on ND_image's "file" input) - see CLAUDE.md Round 19/20. "(default)" maps to "" (no colorSpace metadata
# set at all, left for the consuming renderer/mtlx to decide) rather than being resolved through Modo's
# own Preferences > Color Management settings, reversing the Round 7 decision to do the latter.
#
# The rest is keyed on colorspace names Modo's "foundry-v1" OCIO config offers (Contents/Resources/
# ocio_configs/foundry-v1/config.ocio), mapped to MaterialX's own DefaultColorManagementSystem vocabulary
# - verified directly against the real standard library's cmlib (cmlib_defs.mtlx, shipped with the
# standalone MaterialX PyPI package): only acescg/adobergb/g18_rec709/g22_ap1/g22_rec709/lin_adobergb/
# lin_displayp3/lin_rec709/rec709_display/srgb_texture/srgb_displayp3 have a real ND_..._to_lin_rec709
# conversion node, so those are the only names mtlx's CMS actually recognizes. "raw" isn't a CMS
# transform at all - it's the standard "skip color management" token, passed through as itself.
#
# Any value not in this table (a Modo colorspace with no known mtlx equivalent - e.g. the log-curve
# formats and ProPhoto foundry-v1 also offers, or an unmapped value from one of Modo's other 5 OCIO
# configs) resolves to "" too, same as "(default)" - a name mtlx doesn't recognize is no better than no
# metadata at all. ShaderTree.py is responsible for telling the two "" cases apart and diagnosing the
# fallback one - this pass can't call _DEBUG_diag itself without pulling in ShaderTree.py's lx/modo
# dependency, breaking every normalize/ pass's pytest-testability.
MODO_COLORSPACE_TO_USD = {
    "(default)": "",
    "linear": "lin_rec709",
    "sRGB": "srgb_texture",
    "sRGBf": "srgb_texture",
    "rec709": "rec709_display",
    "Gamma1.8": "g18_rec709",
    "Gamma2.2": "g22_rec709",
    "AdobeRGB": "adobergb",
    "raw": "raw",
}


def normalize_colorspace(xml):
    """Resolves every videoStill/channels/colorspace to its USD colorspace value via
    MODO_COLORSPACE_TO_USD (falls back to "" for anything not in that table). Pure transformation,
    XML -> XML: returns a new tree, the input is left untouched."""
    xml = copy.deepcopy(xml)
    for colorspaceEl in xml.iter('colorspace'):
        _normalize_colorspace_channel(colorspaceEl)
    return xml


def _normalize_colorspace_channel(colorspaceEl):
    colorspace = colorspaceEl.get('value') or ""
    # An explicit colorspace choice (as opposed to a sentinel like "(default)"/"(none)"/"auto") comes back
    # from Modo prefixed with its OCIO config name, e.g. "nuke-default:sRGB" - same "<config>:<colorspace>"
    # shape already seen in Round 7's preference queries. MODO_COLORSPACE_TO_USD is keyed on the bare
    # colorspace name, so the prefix (whatever config it names) is discarded here rather than threaded
    # through as a parameter - the config name itself isn't needed to strip it, only to know a prefix is
    # there at all, and any colon marks that unambiguously.
    if ":" in colorspace:
        colorspace = colorspace.split(":", 1)[1]
    usdColorSpace = MODO_COLORSPACE_TO_USD.get(colorspace, "")
    colorspaceEl.set('usdColorSpace', usdColorSpace)
