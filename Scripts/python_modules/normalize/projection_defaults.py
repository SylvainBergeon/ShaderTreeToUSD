import copy

# Ported from ShaderTree.py's USD_create_texture_output (now _USD_create_texture_output), which silently
# falls back to a UV projection whenever txtrLocator/channels/projType isn't "uv" or "triplanar". This pass
# resolves that fallback up front and writes the result as a usdProjType attribute, alongside the untouched
# raw Modo value (so a future diagnostic pass can still report what the original, unsupported value was).

SUPPORTED_PROJECTION_TYPES = {'uv', 'triplanar'}
DEFAULT_PROJECTION_TYPE = 'uv'


def normalize_projection_defaults(xml):
    """Resolves every txtrLocator/channels/projType to a supported projection type, defaulting to uv for
    anything else. Pure transformation, XML -> XML: returns a new tree, the input is left untouched."""
    xml = copy.deepcopy(xml)
    for projTypeEl in xml.iter('projType'):
        _normalize_proj_type(projTypeEl)
    return xml


def _normalize_proj_type(projTypeEl):
    projType = projTypeEl.get('value')
    usdProjType = projType if projType in SUPPORTED_PROJECTION_TYPES else DEFAULT_PROJECTION_TYPE
    projTypeEl.set('usdProjType', usdProjType)
