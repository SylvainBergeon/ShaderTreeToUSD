import xml.etree.ElementTree as ET

import pytest

from python_modules.normalize.effect_channel_names import normalize_effect_channel_names


def make_layer(effect, tag='imageMap', name='Tex1'):
    layer = ET.Element(tag, {'name': name})
    channels = ET.SubElement(layer, 'channels')
    ET.SubElement(channels, 'effect', {'value': effect})
    return layer


def effect_el(layer):
    return layer.find('channels/effect')


@pytest.mark.parametrize("effect,expected_input_name", [
    ("diffColor", "base_color"),
    ("diffAmount", "base"),
    ("rough", "specular_roughness"),
    ("normal", "normal"),
    ("objectNormal", "in"),
    ("bump", "normal"),
    ("stencil", "opacity"),
    ("specAmount", "specular"),
    ("reflFresnel", "specular"),
    ("specFresnel", "specular"),
    ("tranAmount", "transmission"),
    ("lumiAmount", "emission"),
    ("lumiColor", "emission_color"),
    ("specColor", "specular_color"),
    ("metallic", "metalness"),
    ("sheen", "sheen"),
    ("sheenTint", "sheen_color"),
    ("flatness", "sheen_roughness"),
    ("displace", "displacement"),
])
def test_known_effects_resolve_to_their_usd_input_name(effect, expected_input_name):
    layer = make_layer(effect)

    result = normalize_effect_channel_names(layer)

    assert effect_el(result).get('usdInputName') == expected_input_name
    assert effect_el(result).get('value') == effect # raw value untouched


def test_unknown_effect_is_marked_unresolved_rather_than_raising():
    layer = make_layer("some_future_modo_effect")

    result = normalize_effect_channel_names(layer) # must not raise

    assert effect_el(result).get('usdInputName') == ""


def test_input_tree_is_never_mutated():
    layer = make_layer("diffColor")

    normalize_effect_channel_names(layer)

    assert effect_el(layer).get('usdInputName') is None


def test_effect_channels_nested_anywhere_in_the_tree_are_normalized():
    root = ET.Element('mask')
    root.append(make_layer("rough", tag='noise', name='Noise1'))

    result = normalize_effect_channel_names(root)

    assert result.find('.//effect').get('usdInputName') == "specular_roughness"


def test_layers_without_an_effect_channel_are_left_alone():
    root = ET.Element('mask')
    ET.SubElement(root, 'imageMap', {'name': 'Tex1'})

    result = normalize_effect_channel_names(root) # must not raise

    assert result.find('imageMap') is not None
