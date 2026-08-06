import copy

# Ported from ShaderTree.py's USD_connect_operator (now _USD_connect_operator), which resolves the same
# Modo blend value -> USD node id lookup at construction time, once per connection. This pass resolves it
# once, up front, and writes the result back into the XML as new attributes on the <blend> channel element,
# so stage 3 no longer needs to know which Modo blend values exist or which ones are supported.
#
# The literal strings below mirror lx.symbol.sICVAL_TEXTURELAYER_BLEND_* (queried from a live Modo instance,
# 2026-08-06), duplicated here instead of imported so this pass has zero dependency on lx/modo/fnpxr - unlike
# ShaderFilters.usdInputMap["blend"], which is keyed by those same lx.symbol constants directly and can only
# be imported inside Modo.
BLEND_MULTIPLY = 'multiply'
BLEND_DIVIDE = 'divide'
BLEND_NORMAL = 'normal'
BLEND_ADD = 'add'
BLEND_SUBTRACT = 'subtract'
BLEND_SCREEN = 'screen'
BLEND_COLORBURN = 'colorburn'
BLEND_COLORDODGE = 'colordodge'
BLEND_DIFFERENCE = 'difference'
BLEND_OVERLAY = 'overlay'
BLEND_DARKEN = 'darken'
BLEND_HARDLIGHT = 'hardlight'
BLEND_LIGHTEN = 'lighten'
BLEND_NORMALMULT = 'normalmult'
BLEND_SOFTLIGHT = 'softlight'

# Modo blend value -> USD (MaterialX) node id. Empty string means "known Modo blend mode, no USD
# equivalent wired up yet" - same meaning as a value missing from this table entirely.
USD_BLEND_OPERATOR = {
    BLEND_MULTIPLY: "ND_multiply",
    BLEND_DIVIDE: "ND_divide",
    BLEND_NORMAL: "ND_mix",
    BLEND_ADD: "ND_plus",
    BLEND_SUBTRACT: "ND_minus",
    BLEND_SCREEN: "ND_screen",
    BLEND_COLORBURN: "ND_burn",
    BLEND_COLORDODGE: "ND_dodge",
    BLEND_DIFFERENCE: "ND_difference",
    BLEND_OVERLAY: "ND_overlay",
    BLEND_DARKEN: "",
    BLEND_HARDLIGHT: "",
    BLEND_LIGHTEN: "",
    BLEND_NORMALMULT: "",
    BLEND_SOFTLIGHT: "",
}

# Multiply/Divide connect through two USD nodes (the op node on in1/in2, then a separate ND_mix using
# opacity); every other supported blend connects through a single node taking fg/bg + mix directly.
# See _USD_connect_operator.
DUAL_NODE_BLENDS = {BLEND_MULTIPLY, BLEND_DIVIDE}


def normalize_blend_operators(xml):
    """Resolves every effect layer's <blend value="..."/> channel into its USD operator node id and
    connection pattern, written as usdOperator/usdMixPattern attributes on that same element (empty
    usdOperator means unsupported). Pure transformation, XML -> XML: returns a new tree, the input is
    left untouched."""
    xml = copy.deepcopy(xml)
    for blendEl in xml.iter('blend'):
        _normalize_blend_channel(blendEl)
    return xml


def _normalize_blend_channel(blendEl):
    blend = blendEl.get('value')
    usdOperator = USD_BLEND_OPERATOR.get(blend, "")
    blendEl.set('usdOperator', usdOperator)
    blendEl.set('usdMixPattern', 'dual' if blend in DUAL_NODE_BLENDS else 'single')
