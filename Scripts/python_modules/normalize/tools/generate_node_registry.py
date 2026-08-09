"""
Dev-only tool, not part of the kit. Queries the real MaterialX standard library (via the standalone
`MaterialX` PyPI package - `pip install MaterialX` into .venv) for the exact input names/types and output
type of every USD/MaterialX node id referenced in ShaderTree.py, and prints a Python literal table ready to
paste into normalize/node_registry.py.

Run from the repo root: .venv/bin/python3 Scripts/python_modules/normalize/tools/generate_node_registry.py

Re-run and diff whenever a new CreateIdAttr(...) call is added to ShaderTree.py, to keep node_registry.py
in sync with what the codebase actually uses.
"""
import MaterialX as mx

# Every node id passed to CreateIdAttr(...) in ShaderTree.py, as of the 2026-08-06 refactor. Families with
# a dynamic _UTIL_get_node_type_prefix() suffix are expanded across the type suffixes that helper can
# produce (_float / _color3 / _color4); fixed ids are listed as-is.
DYNAMIC_FAMILIES = [
    # blend operators (_USD_connect_operator / normalize_blend_operators' USD_BLEND_OPERATOR)
    "ND_multiply", "ND_divide", "ND_mix", "ND_plus", "ND_minus",
    "ND_screen", "ND_burn", "ND_dodge", "ND_difference", "ND_overlay",
    # texture adjust nodegraph / stencil
    "ND_invert", "ND_constant", "ND_triplanarprojection", "ND_image", "ND_tiledimage", "ND_remap", "ND_contrast",
]
TYPE_SUFFIXES = ["_float", "_color3", "_color4"] # matches _UTIL_get_node_type_prefix's only 3 outputs

FIXED_IDS = [
    "ND_round_float", "ND_bump_vector3", "ND_displacement_float",
    "ND_unifiednoise3d_float", "ND_normal_vector3", "ND_separate4_color4",
    "ND_position_vector3", "ND_multiply_vector3", "ND_rotate3d_vector3", "ND_add_vector3",
    "ND_standard_surface_surfaceshader", "ND_geompropvalue_vector2",
    # ShaderTree.py:867 uses the bare id "ND_normalmap", which does NOT exist in the MaterialX standard
    # library (only ND_normalmap_float and ND_normalmap_vector2 do) - looks like a real bug. The scale
    # input is set as a plain float there, so ND_normalmap_float is very likely the intended id.
    "ND_normalmap_float",
    # Not MaterialX nodes - included to document that they're a different mechanism entirely:
    "UsdPreviewSurface", "UsdTransform2d",
]


def main():
    doc = mx.createDocument()
    search_path = mx.getDefaultDataSearchPath()
    mx.loadLibraries(mx.getDefaultDataLibraryFolders(), search_path, doc)

    candidate_ids = FIXED_IDS + [family + suffix for family in DYNAMIC_FAMILIES for suffix in TYPE_SUFFIXES]

    found = {}
    not_found = []
    for node_id in candidate_ids:
        nodedef = doc.getNodeDef(node_id)
        if nodedef is None:
            not_found.append(node_id)
            continue
        inputs = tuple((i.getName(), i.getType()) for i in nodedef.getActiveInputs())
        found[node_id] = {"inputs": inputs, "output": nodedef.getType()}

    print("NODE_DEFS = {")
    for node_id, info in sorted(found.items()):
        print(f"    {node_id!r}: {{'inputs': {info['inputs']!r}, 'output': {info['output']!r}}},")
    print("}")
    print()
    print(f"# {len(found)} resolved, {len(not_found)} not found in the MaterialX standard library:")
    for node_id in not_found:
        print(f"#   {node_id}")


if __name__ == "__main__":
    main()
