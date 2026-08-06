import copy
import math

# Ported from ShaderTree.py's USD_apply_overrides (now _USD_apply_overrides), which computes the same
# values on the fly, once per channel, during USD construction. This pass resolves them once, up front,
# and writes them back into the XML so stage 3 no longer needs to know about gtr/principled specifics.
# _USD_apply_overrides itself is left untouched for now (progressive migration - see CLAUDE.md).

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


def normalize_specular_ior(xml):
    """Rewrites specAmt/refIndex/disperse/tranRough/specCol/sheenTint to USD-ready values on every
    advancedMaterial node, according to its brdfType (gtr/principled). Pure transformation, XML -> XML:
    returns a new tree, the input is left untouched."""
    xml = copy.deepcopy(xml)
    for material in xml.iter('advancedMaterial'):
        _normalize_material(material)
    return xml


def _normalize_material(material):
    channels = material.find('channels')
    if channels is None:
        return
    brdfTypeEl = channels.find('brdfType')
    if brdfTypeEl is None:
        return
    brdfType = brdfTypeEl.get('value')

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

    for name, value in updates.items():
        el = channels.find(name)
        if el is not None:
            el.set('value', str(value))
