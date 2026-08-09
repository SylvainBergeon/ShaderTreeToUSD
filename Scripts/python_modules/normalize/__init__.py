# Stage 2 of the export pipeline: XML brut (Scripts/lxserv/ExportShaderTree.py) -> XML canonique (here) -> Stage USD.
#
# Each pass below is a pure Element -> Element transform (no lx/modo/fnpxr dependency), responsible for
# exactly one case-particulier that used to live inline in ShaderTree.py's USD construction code. Passes
# never mutate their input: they return a modified copy, writing resolved usd* attributes/values
# alongside (never over) the raw Modo ones.
#
# Wired into ShaderTree.py's construction path: _USD_write_file/_USD_export_shadertree only work with
# normalize(xml_shadertree) - see CLAUDE.md for the full picture.

from .specular_ior import normalize_specular_ior
from .blend_operators import normalize_blend_operators
from .projection_defaults import normalize_projection_defaults
from .effect_channel_names import normalize_effect_channel_names
from .uv_wrap_modes import normalize_uv_wrap_modes
from .colorspace import normalize_colorspace

NORMALIZATION_PASSES = [
    normalize_specular_ior,
    normalize_blend_operators,
    normalize_projection_defaults,
    normalize_effect_channel_names,
    normalize_uv_wrap_modes,
]


def normalize(xml, colorspaceDefaultByCategory=None):
    """colorspaceDefaultByCategory: Stage 1's 4 live-queried color management preferences (see
    ShaderTree.py's _initialize_colormanagement_defaults) - normalize_colorspace needs it as a parameter
    rather than querying lx itself, so it's called separately here instead of living in
    NORMALIZATION_PASSES with the other (argument-less) passes."""
    for normalization_pass in NORMALIZATION_PASSES:
        xml = normalization_pass(xml)
    return normalize_colorspace(xml, colorspaceDefaultByCategory)
