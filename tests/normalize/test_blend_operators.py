import xml.etree.ElementTree as ET

import pytest

from python_modules.normalize.blend_operators import normalize_blend_operators


def make_layer(tag='imageMap', name='Tex1', **channel_values):
    layer = ET.Element(tag, {'name': name})
    channels = ET.SubElement(layer, 'channels')
    for chName, value in channel_values.items():
        ET.SubElement(channels, chName, {'value': value})
    return layer


def blend_el(layer):
    return layer.find('channels/blend')


@pytest.mark.parametrize("blend,expected_operator", [
    ("multiply", "ND_multiply"),
    ("divide", "ND_divide"),
    ("normal", "ND_mix"),
    ("add", "ND_plus"),
    ("subtract", "ND_minus"),
    ("screen", "ND_screen"),
    ("colorburn", "ND_burn"),
    ("colordodge", "ND_dodge"),
    ("difference", "ND_difference"),
    ("overlay", "ND_overlay"),
])
def test_supported_blends_resolve_to_their_usd_operator(blend, expected_operator):
    layer = make_layer(blend=blend, opacity="1.0")

    result = normalize_blend_operators(layer)

    assert blend_el(result).get('usdOperator') == expected_operator


@pytest.mark.parametrize("blend", [
    "darken", "hardlight", "lighten", "normalmult", "softlight",
])
def test_known_but_unimplemented_blends_are_marked_unsupported(blend):
    layer = make_layer(blend=blend, opacity="1.0")

    result = normalize_blend_operators(layer)

    assert blend_el(result).get('usdOperator') == ""


def test_unknown_blend_value_is_marked_unsupported_rather_than_raising():
    layer = make_layer(blend="some_future_modo_blend_mode", opacity="1.0")

    result = normalize_blend_operators(layer) # must not raise

    assert blend_el(result).get('usdOperator') == ""


def test_input_tree_is_never_mutated():
    layer = make_layer(blend="multiply", opacity="1.0")

    normalize_blend_operators(layer)

    assert blend_el(layer).get('usdOperator') is None


def test_blend_channels_nested_anywhere_in_the_tree_are_normalized():
    root = ET.Element('mask')
    layer = make_layer(blend="screen", opacity="0.5")
    root.append(layer)

    result = normalize_blend_operators(root)

    found = result.find('.//blend')
    assert found.get('usdOperator') == "ND_screen"


def test_layers_without_a_blend_channel_are_left_alone():
    root = ET.Element('mask')
    ET.SubElement(root, 'imageMap', {'name': 'Tex1'})

    result = normalize_blend_operators(root) # must not raise

    assert result.find('imageMap') is not None
