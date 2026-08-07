import copy
import math

# Ported from ShaderTree.py's former USD_apply_overrides, which computed the same values on the fly,
# once per channel, during USD construction (that function and its helpers were removed once this pass
# was wired in - see _USD_export_shadertree/_USD_create_mtlx_standard_surface_shader).
#
# Every channel under an advancedMaterial's <channels> gets a `usdValue` attribute, alongside its raw
# Modo `value`: the gtr/principled-overridden value where one applies, a straight copy of `value`
# otherwise. Both the mtlx shader and the glPreview shader (UsdPreviewSurface) read `usdValue` -
# construction code never needs to know which channels are override-eligible.
#
# specCol and luminousCol additionally get a `usdPreviewValue`: UsdPreviewSurface has no standalone
# specular/emissive intensity input, only specularColor/emissiveColor, so the glPreview shader needs
# those colors pre-weighted by specAmt/luminousAmt instead - a value the mtlx shader does NOT want
# (it has its own specular/emission intensity inputs). Construction reads usdPreviewValue for the
# glPreview shader when present, falling back to usdValue everywhere else.

# IOR approximation from specular amount; saturation<1 keeps the sqrt argument <1 (avoids div-by-zero at specAmt==1)
def _ior_from_spec_amt(specAmt, saturation=.99999):
    return 2 / (1 - math.sqrt(specAmt * saturation)) - 1

# Maps x toward 1 as x grows past 1; k controls how fast it saturates. Approximation based on observation.
def _saturating_curve(x, k):
    return 1 - (1 / (k * (x - 1) + 1))

# Blends white toward diffCol by specTint, normalized so the brightest channel stays at/below 1
def _tinted_spec_color(diffCol, specTint):
    dr, dg, db = diffCol
    m = max(dr, dg, db)
    if m == 0:
        return (1.0, 1.0, 1.0)
    sr = 1 + (dr / m) * specTint
    sg = 1 + (dg / m) * specTint
    sb = 1 + (db / m) * specTint
    m = max(sr, sg, sb) - 1
    return (sr - m, sg - m, sb - m)

# UsdPreviewSurface has no standalone specular/emissive intensity input (only specularColor/
# emissiveColor) - scale the color by the Modo intensity channel instead, so specAmt/luminousAmt still
# have a visible effect in the preview.
def _weighted_color(col, amount):
    r, g, b = col
    return (r * amount, g * amount, b * amount)


def normalize_specular_ior(xml):
    """Adds a usdValue attribute to every channel of every advancedMaterial node: specAmt/refIndex/
    disperse/tranRough/specCol/sheenTint get their gtr/principled-overridden value (per brdfType), every
    other channel gets a plain copy of its raw value. Pure transformation, XML -> XML: returns a new
    tree, the input is left untouched."""
    xml = copy.deepcopy(xml)
    for material in xml.iter('advancedMaterial'):
        _normalize_material(material)
    return xml


def _normalize_material(material):
    # Every channel always gets a usdValue, even if there's no channels/brdfType to compute overrides
    # from (missing channels element, or no brdfType - shouldn't normally happen, but construction code
    # unconditionally reads usdValue, so it must never be left unset).
    channels = material.find('channels')
    if channels is None:
        return

    brdfTypeEl = channels.find('brdfType')
    updates = _compute_overrides(brdfTypeEl.get('value'), channels) if brdfTypeEl is not None else {}
    previewUpdates = _compute_preview_overrides(channels)

    for channel in channels:
        channel.set('usdValue', str(updates.get(channel.tag, channel.get('value'))))
        if channel.tag in previewUpdates:
            channel.set('usdPreviewValue', str(previewUpdates[channel.tag]))


# glPreview-only: specularColor/emissiveColor weighted by their Modo intensity channel. Independent of
# brdfType - the glPreview shader is built for every advancedMaterial regardless of gtr/principled, and
# specCol/specAmt/luminousCol/luminousAmt exist on all of them. Construction falls back to usdValue for
# any channel with no usdPreviewValue (i.e. everywhere the mtlx and glPreview values are the same).
def _compute_preview_overrides(channels):
    def raw(name):
        el = channels.find(name)
        return el.get('value') if el is not None else None

    specCol = raw('specCol')
    specAmt = raw('specAmt')
    luminousCol = raw('luminousCol')
    luminousAmt = raw('luminousAmt')

    previewUpdates = {}
    if specCol is not None and specAmt is not None:
        previewUpdates['specCol'] = _weighted_color(eval(specCol), float(specAmt))
    if luminousCol is not None and luminousAmt is not None:
        previewUpdates['luminousCol'] = _weighted_color(eval(luminousCol), float(luminousAmt))
    return previewUpdates


def _compute_overrides(brdfType, channels):
    def raw(name):
        el = channels.find(name)
        return el.get('value') if el is not None else None

    # Snapshot every raw value up front: overrides below are computed independently of each other,
    # exactly like the per-channel calls in _USD_apply_overrides, which never see each other's output.
    useRefIdx = raw('useRefIdx') == "1"
    specRefIdx = raw('specRefIdx') == "1"
    disperse = raw('disperse')
    tranRough = raw('tranRough')
    specAmt = raw('specAmt')
    refIndex = raw('refIndex')
    specTint = raw('specTint')
    diffCol = raw('diffCol')
    sheenTint = raw('sheenTint')

    updates = {}

    if brdfType == "gtr":
        if disperse is not None:
            disperseValue = float(disperse)
            if disperseValue != 0:
                updates['disperse'] = abs(.1 / disperseValue)

        if tranRough is not None:
            updates['tranRough'] = float(tranRough) * 2

        if specAmt is not None:
            updates['specAmt'] = "1.0"

        if not useRefIdx and refIndex is not None and specAmt is not None:
            updates['refIndex'] = _ior_from_spec_amt(float(specAmt))

    elif brdfType == "principled":
        if useRefIdx:
            specAmnt = float(specAmt)
            refIdx = float(refIndex)
            if specRefIdx:
                x = _ior_from_spec_amt(specAmnt, .8) # avoid division by zero
                k = 100 # magic number, determine how fast the value reaches 1 when refIdx > 1
                updates['specAmt'] = _saturating_curve(x, k)
                updates['refIndex'] = x
            else:
                x = refIdx
                k = 20 # magic number, determine how fast the value reaches 1 when refIdx > 1
                updates['specAmt'] = _saturating_curve(x, k)
                updates['refIndex'] = refIdx
        else:
            specAmnt = float(specAmt)
            updates['specAmt'] = 1.0
            updates['refIndex'] = _ior_from_spec_amt(specAmnt)
            if specTint is not None:
                updates['specTint'] = specTint

        if diffCol is not None and specTint is not None:
            updates['specCol'] = str(_tinted_spec_color(eval(diffCol), float(specTint)))

        if sheenTint is not None:
            st = float(sheenTint)
            updates['sheenTint'] = str((st, st, st))

    return updates
