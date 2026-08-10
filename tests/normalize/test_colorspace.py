import xml.etree.ElementTree as ET

import pytest

from python_modules.normalize.colorspace import normalize_colorspace


def make_video_still(colorspace=None):
    imageMap = ET.Element('imageMap', {'name': 'Tex1'})
    videoStill = ET.SubElement(imageMap, 'videoStill')
    channels = ET.SubElement(videoStill, 'channels')
    if colorspace is not None:
        ET.SubElement(channels, 'colorspace', {'value': colorspace})
    return imageMap


def colorspace_el(imageMap):
    return imageMap.find('.//colorspace')


def test_modo_default_sentinel_resolves_to_empty_string():
    # "(default)" no longer resolves through Modo's Preferences > Color Management settings (Round 7,
    # reversed in Round 19) - it now means "don't set colorSpace at all", left for mtlx/the renderer.
    imageMap = make_video_still(colorspace="(default)")

    result = normalize_colorspace(imageMap)

    assert colorspace_el(result).get('usdColorSpace') == ""
    assert colorspace_el(result).get('value') == "(default)" # raw value untouched


@pytest.mark.parametrize("colorspace,expected", [
    ("linear", "lin_rec709"),
    ("sRGB", "srgb_texture"),
    ("sRGBf", "srgb_texture"),
    ("rec709", "rec709_display"),
    ("Gamma1.8", "g18_rec709"),
    ("Gamma2.2", "g22_rec709"),
    ("AdobeRGB", "adobergb"),
    ("raw", "raw"),
])
def test_known_explicit_colorspace_is_translated_to_its_mtlx_cms_equivalent(colorspace, expected):
    imageMap = make_video_still(colorspace=colorspace)

    result = normalize_colorspace(imageMap)

    assert colorspace_el(result).get('usdColorSpace') == expected


@pytest.mark.parametrize("colorspace", [
    "ProPhoto", "Cineon", "AlexaV3LogC", "PLogLin", "SLog", # foundry-v1 colorspaces with no mtlx CMS equivalent
    "Rec 709", "aces", "Foundry-WideGamut - ACES2065-1", # not yet in the table at all
])
def test_colorspace_not_in_the_table_resolves_to_empty_string(colorspace):
    # A name mtlx doesn't recognize is no better than no metadata at all - same fallback as "(default)".
    # ShaderTree.py is responsible for telling the two apart and diagnosing this one - not this pass's
    # job, it can't call _DEBUG_diag itself.
    imageMap = make_video_still(colorspace=colorspace)

    result = normalize_colorspace(imageMap)

    assert colorspace_el(result).get('usdColorSpace') == ""


@pytest.mark.parametrize("colorspace,expected", [
    ("nuke-default:sRGB", "srgb_texture"),
    ("foundry-v1:linear", "lin_rec709"),
    ("aces:raw", "raw"), # even an unrelated config's prefix is stripped - the config name itself isn't checked
])
def test_explicit_colorspace_is_stripped_of_its_ocio_config_prefix_before_lookup(colorspace, expected):
    imageMap = make_video_still(colorspace=colorspace)

    result = normalize_colorspace(imageMap)

    assert colorspace_el(result).get('usdColorSpace') == expected
    assert colorspace_el(result).get('value') == colorspace # raw value (with its prefix) untouched


@pytest.mark.parametrize("colorspace", ["(default)", "(none)", "auto"])
def test_sentinel_values_have_no_colon_and_are_used_as_is(colorspace):
    # None of Modo's sentinel values (as opposed to explicit OCIO choices) carry a config prefix - only
    # "(default)" is currently mapped (to ""); "(none)"/"auto" fall through to the same "" default.
    imageMap = make_video_still(colorspace=colorspace)

    result = normalize_colorspace(imageMap)

    assert colorspace_el(result).get('usdColorSpace') == ""


def test_input_tree_is_never_mutated():
    imageMap = make_video_still(colorspace="(default)")

    normalize_colorspace(imageMap)

    assert colorspace_el(imageMap).get('usdColorSpace') is None


def test_colorspace_channels_nested_anywhere_in_the_tree_are_normalized():
    root = ET.Element('mask')
    root.append(make_video_still(colorspace="linear"))

    result = normalize_colorspace(root)

    assert result.find('.//colorspace').get('usdColorSpace') == "lin_rec709"


def test_video_still_without_a_colorspace_channel_is_left_alone():
    imageMap = ET.Element('imageMap', {'name': 'Tex1'})
    ET.SubElement(imageMap, 'videoStill') # no channels at all

    result = normalize_colorspace(imageMap) # must not raise

    assert result.find('videoStill') is not None


def test_layers_without_a_video_still_are_left_alone():
    root = ET.Element('mask')
    ET.SubElement(root, 'noise', {'name': 'Noise1'})

    result = normalize_colorspace(root) # must not raise

    assert result.find('noise') is not None
