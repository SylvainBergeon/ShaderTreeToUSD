# Stage 2 of the export pipeline: XML brut (Scripts/lxserv/ExportShaderTree.py) -> XML canonique (here) -> Stage USD.
#
# Each pass below is a pure Element -> Element transform (no lx/modo/fnpxr dependency), responsible for
# exactly one case-particulier that today lives inline in ShaderTree.py's USD construction code. Passes never
# mutate their input: they return a modified copy, so a caller can still read the untouched raw XML afterwards
# (needed e.g. because the glPreview shader is built from the same XML as the mtlx shader, but must keep the
# raw Modo channel values instead of the gtr/principled-specific overrides).
#
# Not yet wired into ShaderTree.py's construction path (USD_export_shadertree still reads the raw XML directly) -
# see CLAUDE.md for the migration plan. Passes are added here one at a time as they're built and tested.

from .specular_ior import normalize_specular_ior
from .blend_operators import normalize_blend_operators

NORMALIZATION_PASSES = [
    normalize_specular_ior,
    normalize_blend_operators,
]


def normalize(xml):
    for normalization_pass in NORMALIZATION_PASSES:
        xml = normalization_pass(xml)
    return xml
