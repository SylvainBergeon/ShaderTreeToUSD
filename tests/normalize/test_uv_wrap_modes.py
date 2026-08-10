import xml.etree.ElementTree as ET

import pytest

from python_modules.normalize.uv_wrap_modes import normalize_uv_wrap_modes


def make_locator(tileU=None, tileV=None):
    imageMap = ET.Element('imageMap', {'name': 'Tex1'})
    txtrLocator = ET.SubElement(imageMap, 'txtrLocator')
    channels = ET.SubElement(txtrLocator, 'channels')
    if tileU is not None:
        ET.SubElement(channels, 'tileU', {'value': tileU})
    if tileV is not None:
        ET.SubElement(channels, 'tileV', {'value': tileV})
    return imageMap


def tile_el(imageMap, tag):
    return imageMap.find(f'.//{tag}')


@pytest.mark.parametrize("tile,expectedNative,expectedMtlx", [
    ("reset", "black", "constant"),
    ("repeat", "repeat", "periodic"),
    ("edge", "clamp", "clamp"),
    ("mirror", "mirror", "mirror"),
])
def test_known_tile_modes_resolve_to_their_usd_native_and_mtlx_wrap_mode(tile, expectedNative, expectedMtlx):
    locator = make_locator(tileU=tile, tileV=tile)

    result = normalize_uv_wrap_modes(locator)

    assert tile_el(result, 'tileU').get('usdNativeWrapMode') == expectedNative
    assert tile_el(result, 'tileV').get('usdNativeWrapMode') == expectedNative
    assert tile_el(result, 'tileU').get('usdWrapMode') == expectedMtlx
    assert tile_el(result, 'tileV').get('usdWrapMode') == expectedMtlx
    assert tile_el(result, 'tileU').get('value') == tile # raw value untouched


def test_tileu_and_tilev_are_resolved_independently():
    locator = make_locator(tileU="reset", tileV="mirror")

    result = normalize_uv_wrap_modes(locator)

    assert tile_el(result, 'tileU').get('usdNativeWrapMode') == "black"
    assert tile_el(result, 'tileV').get('usdNativeWrapMode') == "mirror"
    assert tile_el(result, 'tileU').get('usdWrapMode') == "constant"
    assert tile_el(result, 'tileV').get('usdWrapMode') == "mirror"


def test_unknown_tile_mode_is_marked_unresolved_rather_than_raising():
    locator = make_locator(tileU="some_future_modo_mode", tileV="reset")

    result = normalize_uv_wrap_modes(locator) # must not raise

    assert tile_el(result, 'tileU').get('usdNativeWrapMode') == ""
    assert tile_el(result, 'tileU').get('usdWrapMode') == ""


def test_input_tree_is_never_mutated():
    locator = make_locator(tileU="reset", tileV="reset")

    normalize_uv_wrap_modes(locator)

    assert tile_el(locator, 'tileU').get('usdNativeWrapMode') is None


def test_tiles_nested_anywhere_in_the_tree_are_normalized():
    root = ET.Element('mask')
    root.append(make_locator(tileU="edge", tileV="edge"))

    result = normalize_uv_wrap_modes(root)

    assert result.find('.//tileU').get('usdNativeWrapMode') == "clamp"


def test_layers_without_tile_channels_are_left_alone():
    root = ET.Element('mask')
    ET.SubElement(root, 'noise', {'name': 'Noise1'})

    result = normalize_uv_wrap_modes(root) # must not raise

    assert result.find('noise') is not None
