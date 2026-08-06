from python_modules.normalize.node_registry import NODE_DEFS
from python_modules.normalize.blend_operators import USD_BLEND_OPERATOR


def test_registry_entries_have_the_expected_shape():
    assert len(NODE_DEFS) > 0
    for node_id, info in NODE_DEFS.items():
        assert set(info.keys()) == {'inputs', 'output'}
        assert isinstance(info['output'], str) and info['output']
        for input_name, input_type in info['inputs']:
            assert isinstance(input_name, str) and input_name
            assert isinstance(input_type, str) and input_type


def test_every_supported_blend_operator_has_a_float_variant_registered():
    supported_operators = {op for op in USD_BLEND_OPERATOR.values() if op}

    for operator in supported_operators:
        assert operator + "_float" in NODE_DEFS


def test_multiply_and_divide_use_in1_in2_with_no_mix_input():
    for op in ("ND_multiply_float", "ND_divide_float"):
        input_names = [name for name, _ in NODE_DEFS[op]['inputs']]
        assert input_names == ['in1', 'in2']


def test_other_supported_blend_operators_use_fg_bg_mix():
    single_pattern_ops = {
        op + "_float" for op in USD_BLEND_OPERATOR.values()
        if op and op not in ("ND_multiply", "ND_divide")
    }
    for op in single_pattern_ops:
        input_names = [name for name, _ in NODE_DEFS[op]['inputs']]
        assert input_names == ['fg', 'bg', 'mix']
