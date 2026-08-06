import math
import xml.etree.ElementTree as ET

import pytest

from python_modules.normalize.specular_ior import normalize_specular_ior


def make_material(name="Mat1", **channel_values):
    material = ET.Element('advancedMaterial', {'name': name, 'type': 'advancedMaterial'})
    channels = ET.SubElement(material, 'channels')
    for chName, value in channel_values.items():
        ET.SubElement(channels, chName, {'value': value})
    return material


def channel(material, name):
    return material.find(f'channels/{name}').get('value')


def ior_from_spec_amt(specAmt, saturation=.99999):
    return 2 / (1 - math.sqrt(specAmt * saturation)) - 1


def saturating_curve(x, k):
    return 1 - (1 / (k * (x - 1) + 1))


class TestGtr:
    def test_use_ref_idx_forces_full_specular_and_leaves_ref_index_alone(self):
        material = make_material(brdfType="gtr", useRefIdx="1", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5")

        result = normalize_specular_ior(material)

        assert channel(result, 'specAmt') == "1.0"
        assert channel(result, 'refIndex') == "1.5" # untouched: only used when useRefIdx is off

    def test_no_ref_idx_derives_ref_index_from_original_spec_amt(self):
        material = make_material(brdfType="gtr", useRefIdx="0", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5")

        result = normalize_specular_ior(material)

        assert channel(result, 'specAmt') == "1.0"
        assert float(channel(result, 'refIndex')) == pytest.approx(ior_from_spec_amt(0.4))

    def test_disperse_and_tran_rough(self):
        material = make_material(brdfType="gtr", useRefIdx="1", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5",
                                  disperse="0.2", tranRough="0.3")

        result = normalize_specular_ior(material)

        assert float(channel(result, 'disperse')) == pytest.approx(abs(.1 / 0.2))
        assert float(channel(result, 'tranRough')) == pytest.approx(0.3 * 2)

    def test_disperse_zero_is_left_alone_to_avoid_division_by_zero(self):
        material = make_material(brdfType="gtr", useRefIdx="1", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5", disperse="0")

        result = normalize_specular_ior(material)

        assert channel(result, 'disperse') == "0"


class TestPrincipled:
    def test_use_ref_idx_with_spec_ref_idx(self):
        material = make_material(brdfType="principled", useRefIdx="1", specRefIdx="1",
                                  specAmt="0.4", refIndex="1.5", diffCol="(0.5,0.5,0.5)", specTint="0")

        result = normalize_specular_ior(material)

        x = ior_from_spec_amt(0.4, .8)
        assert float(channel(result, 'specAmt')) == pytest.approx(saturating_curve(x, 100))
        assert float(channel(result, 'refIndex')) == pytest.approx(x)

    def test_use_ref_idx_without_spec_ref_idx_keys_off_ref_idx_directly(self):
        material = make_material(brdfType="principled", useRefIdx="1", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5", diffCol="(0.5,0.5,0.5)", specTint="0")

        result = normalize_specular_ior(material)

        assert float(channel(result, 'specAmt')) == pytest.approx(saturating_curve(1.5, 20))
        assert float(channel(result, 'refIndex')) == pytest.approx(1.5)

    def test_no_ref_idx_forces_full_specular_and_derives_ref_index(self):
        material = make_material(brdfType="principled", useRefIdx="0", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5", diffCol="(0.5,0.5,0.5)", specTint="0")

        result = normalize_specular_ior(material)

        assert channel(result, 'specAmt') == "1.0"
        assert float(channel(result, 'refIndex')) == pytest.approx(ior_from_spec_amt(0.4))

    def test_spec_col_is_tinted_towards_diffuse_color(self):
        material = make_material(brdfType="principled", useRefIdx="0", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5", specCol="(1,1,1)",
                                  diffCol="(0.8, 0.2, 0.1)", specTint="0.5")

        result = normalize_specular_ior(material)

        r, g, b = eval(channel(result, 'specCol'))
        assert r == pytest.approx(1.0) # brightest channel of diffCol stays saturated at 1
        assert 0 < b < g < r

    def test_spec_col_on_pure_black_diffuse_does_not_crash(self):
        material = make_material(brdfType="principled", useRefIdx="0", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5", specCol="(1,1,1)",
                                  diffCol="(0, 0, 0)", specTint="0.5")

        result = normalize_specular_ior(material)

        assert eval(channel(result, 'specCol')) == (1.0, 1.0, 1.0)

    def test_sheen_tint_is_expanded_to_a_grey_triplet(self):
        material = make_material(brdfType="principled", useRefIdx="0", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5",
                                  diffCol="(0.5,0.5,0.5)", specTint="0", sheenTint="0.3")

        result = normalize_specular_ior(material)

        assert eval(channel(result, 'sheenTint')) == (0.3, 0.3, 0.3)


class TestStructural:
    def test_input_tree_is_never_mutated(self):
        material = make_material(brdfType="gtr", useRefIdx="0", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5")

        normalize_specular_ior(material)

        assert channel(material, 'specAmt') == "0.4"
        assert channel(material, 'refIndex') == "1.5"

    def test_materials_nested_anywhere_in_the_tree_are_normalized(self):
        root = ET.Element('polyRender')
        mask = ET.SubElement(root, 'mask')
        material = make_material(brdfType="gtr", useRefIdx="0", specRefIdx="0",
                                  specAmt="0.4", refIndex="1.5")
        mask.append(material)

        result = normalize_specular_ior(root)

        found = result.find('.//advancedMaterial')
        assert channel(found, 'specAmt') == "1.0"

    def test_material_without_brdf_type_is_left_alone(self):
        material = ET.Element('advancedMaterial', {'name': 'NoBrdf'})
        ET.SubElement(material, 'channels')

        result = normalize_specular_ior(material) # must not raise

        assert result.find('channels/brdfType') is None

    def test_non_material_elements_are_ignored(self):
        root = ET.Element('polyRender')
        ET.SubElement(root, 'imageMap', {'name': 'Tex1'})

        result = normalize_specular_ior(root) # must not raise

        assert result.find('imageMap') is not None
