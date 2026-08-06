import xml.etree.ElementTree as ET

import pytest

from python_modules.normalize.projection_defaults import normalize_projection_defaults


def make_locator(projType):
    imageMap = ET.Element('imageMap', {'name': 'Tex1'})
    txtrLocator = ET.SubElement(imageMap, 'txtrLocator')
    channels = ET.SubElement(txtrLocator, 'channels')
    ET.SubElement(channels, 'projType', {'value': projType})
    return imageMap


def proj_type_el(imageMap):
    return imageMap.find('.//projType')


@pytest.mark.parametrize("projType", ["uv", "triplanar"])
def test_supported_projection_types_are_kept_as_is(projType):
    imageMap = make_locator(projType)

    result = normalize_projection_defaults(imageMap)

    assert proj_type_el(result).get('usdProjType') == projType
    assert proj_type_el(result).get('value') == projType # raw value untouched


@pytest.mark.parametrize("projType", ["cylindrical", "spherical", "planar", ""])
def test_unsupported_projection_types_fall_back_to_uv(projType):
    imageMap = make_locator(projType)

    result = normalize_projection_defaults(imageMap)

    assert proj_type_el(result).get('usdProjType') == "uv"
    assert proj_type_el(result).get('value') == projType # raw value kept for diagnostics


def test_input_tree_is_never_mutated():
    imageMap = make_locator("cylindrical")

    normalize_projection_defaults(imageMap)

    assert proj_type_el(imageMap).get('usdProjType') is None


def test_proj_types_nested_anywhere_in_the_tree_are_normalized():
    root = ET.Element('mask')
    root.append(make_locator("triplanar"))

    result = normalize_projection_defaults(root)

    assert result.find('.//projType').get('usdProjType') == "triplanar"


def test_elements_without_a_proj_type_are_left_alone():
    root = ET.Element('mask')
    ET.SubElement(root, 'noise', {'name': 'Noise1'})

    result = normalize_projection_defaults(root) # must not raise

    assert result.find('noise') is not None
