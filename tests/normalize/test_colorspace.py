import xml.etree.ElementTree as ET

import pytest

from python_modules.normalize.colorspace import normalize_colorspace


def make_video_still(colorspace=None, format=None):
    imageMap = ET.Element('imageMap', {'name': 'Tex1'})
    videoStill = ET.SubElement(imageMap, 'videoStill')
    channels = ET.SubElement(videoStill, 'channels')
    if colorspace is not None:
        ET.SubElement(channels, 'colorspace', {'value': colorspace})
    if format is not None:
        ET.SubElement(channels, 'format', {'value': format})
    return imageMap


def colorspace_el(imageMap):
    return imageMap.find('.//colorspace')


def test_modo_default_sentinel_resolves_via_the_bit_depth_category_preference():
    # "(default)" does NOT mean "raw" in general - it depends on the image's bit depth (approximated
    # here from its "format" channel) and the scene's color management preferences.
    imageMap = make_video_still(colorspace="(default)", format="PNG")

    result = normalize_colorspace(imageMap, {"8bit": "sRGB", "float": "linear"})

    assert colorspace_el(result).get('usdColorSpace') == "sRGB"
    assert colorspace_el(result).get('value') == "(default)" # raw value untouched


def test_float_formats_use_the_float_category():
    imageMap = make_video_still(colorspace="(default)", format="EXR")

    result = normalize_colorspace(imageMap, {"8bit": "sRGB", "float": "linear"})

    assert colorspace_el(result).get('usdColorSpace') == "linear"


def test_unrecognized_format_falls_back_to_the_8bit_category():
    imageMap = make_video_still(colorspace="(default)", format="some_future_modo_format")

    result = normalize_colorspace(imageMap, {"8bit": "sRGB"})

    assert colorspace_el(result).get('usdColorSpace') == "sRGB"


def test_modo_default_sentinel_falls_back_to_raw_without_preferences():
    imageMap = make_video_still(colorspace="(default)", format="PNG")

    result = normalize_colorspace(imageMap) # no colorspaceDefaultByCategory at all

    assert colorspace_el(result).get('usdColorSpace') == "raw"


@pytest.mark.parametrize("colorspace", ["sRGB", "linear", "aces", "Foundry-WideGamut - ACES2065-1"])
def test_explicit_override_is_passed_through_unchanged(colorspace):
    imageMap = make_video_still(colorspace=colorspace)

    result = normalize_colorspace(imageMap, {"8bit": "sRGB"})

    assert colorspace_el(result).get('usdColorSpace') == colorspace


def test_input_tree_is_never_mutated():
    imageMap = make_video_still(colorspace="(default)", format="PNG")

    normalize_colorspace(imageMap, {"8bit": "sRGB"})

    assert colorspace_el(imageMap).get('usdColorSpace') is None


def test_colorspace_channels_nested_anywhere_in_the_tree_are_normalized():
    root = ET.Element('mask')
    root.append(make_video_still(colorspace="(default)", format="PNG"))

    result = normalize_colorspace(root, {"8bit": "sRGB"})

    assert result.find('.//colorspace').get('usdColorSpace') == "sRGB"


def test_video_still_without_a_colorspace_channel_is_left_alone():
    imageMap = ET.Element('imageMap', {'name': 'Tex1'})
    ET.SubElement(imageMap, 'videoStill') # no channels at all

    result = normalize_colorspace(imageMap, {"8bit": "sRGB"}) # must not raise

    assert result.find('videoStill') is not None


def test_layers_without_a_video_still_are_left_alone():
    root = ET.Element('mask')
    ET.SubElement(root, 'noise', {'name': 'Noise1'})

    result = normalize_colorspace(root, {"8bit": "sRGB"}) # must not raise

    assert result.find('noise') is not None
