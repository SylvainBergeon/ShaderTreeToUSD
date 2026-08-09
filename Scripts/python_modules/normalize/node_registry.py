# Static catalogue of every USD/MaterialX node id referenced in ShaderTree.py (CreateIdAttr(...) calls),
# generated from the real MaterialX standard library - see tools/generate_node_registry.py, which queries
# it via the standalone `MaterialX` PyPI package (`pip install MaterialX`; not available through fnpxr/
# usd-core). Re-run that generator whenever a new CreateIdAttr(...) call is added to ShaderTree.py.
#
# For each node id: its active input names + types, and its output type, exactly as MaterialX defines them
# - not guessed or hand-classified. This lets a future generic connection step ask "what are node X's real
# inputs?" instead of hardcoding per-node shapes like the current dual/single split in normalize_blend_
# operators does for exactly the 10 blend operators it knows about.
#
# Not currently used anywhere - infrastructure for whatever comes after the 4 normalization passes.
#
# Two ids used in ShaderTree.py are deliberately absent: UsdPreviewSurface and UsdTransform2d are not
# MaterialX nodes at all (no ND_ prefix) - they come from USD's own Sdr/UsdShaders shader registry, a
# different mechanism this table doesn't cover.
NODE_DEFS = {
    'ND_add_vector3': {'inputs': (('in1', 'vector3'), ('in2', 'vector3')), 'output': 'vector3'},
    'ND_bump_vector3': {'inputs': (('height', 'float'), ('scale', 'float'), ('normal', 'vector3'), ('tangent', 'vector3'), ('bitangent', 'vector3')), 'output': 'vector3'},
    'ND_burn_color3': {'inputs': (('fg', 'color3'), ('bg', 'color3'), ('mix', 'float')), 'output': 'color3'},
    'ND_burn_color4': {'inputs': (('fg', 'color4'), ('bg', 'color4'), ('mix', 'float')), 'output': 'color4'},
    'ND_burn_float': {'inputs': (('fg', 'float'), ('bg', 'float'), ('mix', 'float')), 'output': 'float'},
    'ND_constant_color3': {'inputs': (('value', 'color3'),), 'output': 'color3'},
    'ND_constant_color4': {'inputs': (('value', 'color4'),), 'output': 'color4'},
    'ND_constant_float': {'inputs': (('value', 'float'),), 'output': 'float'},
    'ND_contrast_color3': {'inputs': (('in', 'color3'), ('amount', 'color3'), ('pivot', 'color3')), 'output': 'color3'},
    'ND_contrast_color4': {'inputs': (('in', 'color4'), ('amount', 'color4'), ('pivot', 'color4')), 'output': 'color4'},
    'ND_contrast_float': {'inputs': (('in', 'float'), ('amount', 'float'), ('pivot', 'float')), 'output': 'float'},
    'ND_difference_color3': {'inputs': (('fg', 'color3'), ('bg', 'color3'), ('mix', 'float')), 'output': 'color3'},
    'ND_difference_color4': {'inputs': (('fg', 'color4'), ('bg', 'color4'), ('mix', 'float')), 'output': 'color4'},
    'ND_difference_float': {'inputs': (('fg', 'float'), ('bg', 'float'), ('mix', 'float')), 'output': 'float'},
    'ND_displacement_float': {'inputs': (('displacement', 'float'), ('scale', 'float')), 'output': 'displacementshader'},
    'ND_divide_color3': {'inputs': (('in1', 'color3'), ('in2', 'color3')), 'output': 'color3'},
    'ND_divide_color4': {'inputs': (('in1', 'color4'), ('in2', 'color4')), 'output': 'color4'},
    'ND_divide_float': {'inputs': (('in1', 'float'), ('in2', 'float')), 'output': 'float'},
    'ND_dodge_color3': {'inputs': (('fg', 'color3'), ('bg', 'color3'), ('mix', 'float')), 'output': 'color3'},
    'ND_dodge_color4': {'inputs': (('fg', 'color4'), ('bg', 'color4'), ('mix', 'float')), 'output': 'color4'},
    'ND_dodge_float': {'inputs': (('fg', 'float'), ('bg', 'float'), ('mix', 'float')), 'output': 'float'},
    'ND_geompropvalue_vector2': {'inputs': (('geomprop', 'string'), ('default', 'vector2')), 'output': 'vector2'},
    'ND_image_color3': {'inputs': (('file', 'filename'), ('layer', 'string'), ('default', 'color3'), ('texcoord', 'vector2'), ('uaddressmode', 'string'), ('vaddressmode', 'string'), ('filtertype', 'string'), ('framerange', 'string'), ('frameoffset', 'integer'), ('frameendaction', 'string')), 'output': 'color3'},
    'ND_image_color4': {'inputs': (('file', 'filename'), ('layer', 'string'), ('default', 'color4'), ('texcoord', 'vector2'), ('uaddressmode', 'string'), ('vaddressmode', 'string'), ('filtertype', 'string'), ('framerange', 'string'), ('frameoffset', 'integer'), ('frameendaction', 'string')), 'output': 'color4'},
    'ND_image_float': {'inputs': (('file', 'filename'), ('layer', 'string'), ('default', 'float'), ('texcoord', 'vector2'), ('uaddressmode', 'string'), ('vaddressmode', 'string'), ('filtertype', 'string'), ('framerange', 'string'), ('frameoffset', 'integer'), ('frameendaction', 'string')), 'output': 'float'},
    'ND_invert_color3': {'inputs': (('in', 'color3'), ('amount', 'color3')), 'output': 'color3'},
    'ND_invert_color4': {'inputs': (('in', 'color4'), ('amount', 'color4')), 'output': 'color4'},
    'ND_invert_float': {'inputs': (('in', 'float'), ('amount', 'float')), 'output': 'float'},
    'ND_minus_color3': {'inputs': (('fg', 'color3'), ('bg', 'color3'), ('mix', 'float')), 'output': 'color3'},
    'ND_minus_color4': {'inputs': (('fg', 'color4'), ('bg', 'color4'), ('mix', 'float')), 'output': 'color4'},
    'ND_minus_float': {'inputs': (('fg', 'float'), ('bg', 'float'), ('mix', 'float')), 'output': 'float'},
    'ND_mix_color3': {'inputs': (('fg', 'color3'), ('bg', 'color3'), ('mix', 'float')), 'output': 'color3'},
    'ND_mix_color4': {'inputs': (('fg', 'color4'), ('bg', 'color4'), ('mix', 'float')), 'output': 'color4'},
    'ND_mix_float': {'inputs': (('fg', 'float'), ('bg', 'float'), ('mix', 'float')), 'output': 'float'},
    'ND_multiply_color3': {'inputs': (('in1', 'color3'), ('in2', 'color3')), 'output': 'color3'},
    'ND_multiply_color4': {'inputs': (('in1', 'color4'), ('in2', 'color4')), 'output': 'color4'},
    'ND_multiply_float': {'inputs': (('in1', 'float'), ('in2', 'float')), 'output': 'float'},
    'ND_multiply_vector3': {'inputs': (('in1', 'vector3'), ('in2', 'vector3')), 'output': 'vector3'},
    'ND_normal_vector3': {'inputs': (('space', 'string'),), 'output': 'vector3'},
    'ND_normalmap_float': {'inputs': (('in', 'vector3'), ('scale', 'float'), ('normal', 'vector3'), ('tangent', 'vector3'), ('bitangent', 'vector3')), 'output': 'vector3'},
    'ND_overlay_color3': {'inputs': (('fg', 'color3'), ('bg', 'color3'), ('mix', 'float')), 'output': 'color3'},
    'ND_overlay_color4': {'inputs': (('fg', 'color4'), ('bg', 'color4'), ('mix', 'float')), 'output': 'color4'},
    'ND_overlay_float': {'inputs': (('fg', 'float'), ('bg', 'float'), ('mix', 'float')), 'output': 'float'},
    'ND_plus_color3': {'inputs': (('fg', 'color3'), ('bg', 'color3'), ('mix', 'float')), 'output': 'color3'},
    'ND_plus_color4': {'inputs': (('fg', 'color4'), ('bg', 'color4'), ('mix', 'float')), 'output': 'color4'},
    'ND_plus_float': {'inputs': (('fg', 'float'), ('bg', 'float'), ('mix', 'float')), 'output': 'float'},
    'ND_position_vector3': {'inputs': (('space', 'string'),), 'output': 'vector3'},
    'ND_remap_color3': {'inputs': (('in', 'color3'), ('inlow', 'color3'), ('inhigh', 'color3'), ('outlow', 'color3'), ('outhigh', 'color3')), 'output': 'color3'},
    'ND_remap_color4': {'inputs': (('in', 'color4'), ('inlow', 'color4'), ('inhigh', 'color4'), ('outlow', 'color4'), ('outhigh', 'color4')), 'output': 'color4'},
    'ND_remap_float': {'inputs': (('in', 'float'), ('inlow', 'float'), ('inhigh', 'float'), ('outlow', 'float'), ('outhigh', 'float')), 'output': 'float'},
    'ND_rotate3d_vector3': {'inputs': (('in', 'vector3'), ('amount', 'float'), ('axis', 'vector3')), 'output': 'vector3'},
    'ND_round_float': {'inputs': (('in', 'float'),), 'output': 'float'},
    'ND_screen_color3': {'inputs': (('fg', 'color3'), ('bg', 'color3'), ('mix', 'float')), 'output': 'color3'},
    'ND_screen_color4': {'inputs': (('fg', 'color4'), ('bg', 'color4'), ('mix', 'float')), 'output': 'color4'},
    'ND_screen_float': {'inputs': (('fg', 'float'), ('bg', 'float'), ('mix', 'float')), 'output': 'float'},
    'ND_separate4_color4': {'inputs': (('in', 'color4'),), 'output': 'multioutput'},
    'ND_standard_surface_surfaceshader': {'inputs': (('base', 'float'), ('base_color', 'color3'), ('diffuse_roughness', 'float'), ('metalness', 'float'), ('specular', 'float'), ('specular_color', 'color3'), ('specular_roughness', 'float'), ('specular_IOR', 'float'), ('specular_anisotropy', 'float'), ('specular_rotation', 'float'), ('transmission', 'float'), ('transmission_color', 'color3'), ('transmission_depth', 'float'), ('transmission_scatter', 'color3'), ('transmission_scatter_anisotropy', 'float'), ('transmission_dispersion', 'float'), ('transmission_extra_roughness', 'float'), ('subsurface', 'float'), ('subsurface_color', 'color3'), ('subsurface_radius', 'color3'), ('subsurface_scale', 'float'), ('subsurface_anisotropy', 'float'), ('sheen', 'float'), ('sheen_color', 'color3'), ('sheen_roughness', 'float'), ('coat', 'float'), ('coat_color', 'color3'), ('coat_roughness', 'float'), ('coat_anisotropy', 'float'), ('coat_rotation', 'float'), ('coat_IOR', 'float'), ('coat_normal', 'vector3'), ('coat_affect_color', 'float'), ('coat_affect_roughness', 'float'), ('thin_film_thickness', 'float'), ('thin_film_IOR', 'float'), ('emission', 'float'), ('emission_color', 'color3'), ('opacity', 'color3'), ('thin_walled', 'boolean'), ('normal', 'vector3'), ('tangent', 'vector3')), 'output': 'surfaceshader'},
    'ND_tiledimage_color3': {'inputs': (('file', 'filename'), ('default', 'color3'), ('texcoord', 'vector2'), ('uvtiling', 'vector2'), ('uvoffset', 'vector2'), ('realworldimagesize', 'vector2'), ('realworldtilesize', 'vector2'), ('filtertype', 'string'), ('framerange', 'string'), ('frameoffset', 'integer'), ('frameendaction', 'string')), 'output': 'color3'},
    'ND_tiledimage_color4': {'inputs': (('file', 'filename'), ('default', 'color4'), ('texcoord', 'vector2'), ('uvtiling', 'vector2'), ('uvoffset', 'vector2'), ('realworldimagesize', 'vector2'), ('realworldtilesize', 'vector2'), ('filtertype', 'string'), ('framerange', 'string'), ('frameoffset', 'integer'), ('frameendaction', 'string')), 'output': 'color4'},
    'ND_tiledimage_float': {'inputs': (('file', 'filename'), ('default', 'float'), ('texcoord', 'vector2'), ('uvtiling', 'vector2'), ('uvoffset', 'vector2'), ('realworldimagesize', 'vector2'), ('realworldtilesize', 'vector2'), ('filtertype', 'string'), ('framerange', 'string'), ('frameoffset', 'integer'), ('frameendaction', 'string')), 'output': 'float'},
    'ND_triplanarprojection_color3': {'inputs': (('filex', 'filename'), ('filey', 'filename'), ('filez', 'filename'), ('layerx', 'string'), ('layery', 'string'), ('layerz', 'string'), ('default', 'color3'), ('position', 'vector3'), ('normal', 'vector3'), ('upaxis', 'integer'), ('blend', 'float'), ('filtertype', 'string'), ('framerange', 'string'), ('frameoffset', 'integer'), ('frameendaction', 'string')), 'output': 'color3'},
    'ND_triplanarprojection_color4': {'inputs': (('filex', 'filename'), ('filey', 'filename'), ('filez', 'filename'), ('layerx', 'string'), ('layery', 'string'), ('layerz', 'string'), ('default', 'color4'), ('position', 'vector3'), ('normal', 'vector3'), ('upaxis', 'integer'), ('blend', 'float'), ('filtertype', 'string'), ('framerange', 'string'), ('frameoffset', 'integer'), ('frameendaction', 'string')), 'output': 'color4'},
    'ND_triplanarprojection_float': {'inputs': (('filex', 'filename'), ('filey', 'filename'), ('filez', 'filename'), ('layerx', 'string'), ('layery', 'string'), ('layerz', 'string'), ('default', 'float'), ('position', 'vector3'), ('normal', 'vector3'), ('upaxis', 'integer'), ('blend', 'float'), ('filtertype', 'string'), ('framerange', 'string'), ('frameoffset', 'integer'), ('frameendaction', 'string')), 'output': 'float'},
    'ND_unifiednoise3d_float': {'inputs': (('position', 'vector3'), ('freq', 'vector3'), ('offset', 'vector3'), ('jitter', 'float'), ('outmin', 'float'), ('outmax', 'float'), ('clampoutput', 'boolean'), ('octaves', 'integer'), ('lacunarity', 'float'), ('diminish', 'float'), ('type', 'integer'), ('style', 'integer')), 'output': 'float'},
}
