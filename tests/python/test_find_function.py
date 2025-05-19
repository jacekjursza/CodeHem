import pytest
import rich

from codehem import CodeHem
from codehem.models.code_element import CodeElementType
from tests.helpers.code_examples import TestHelper


@pytest.fixture
def codehem():
    return CodeHem('python')

def test_find_function_simple(codehem):
    """Test finding a simple function."""
    example = TestHelper.load_example('simple_function', category='general')
    result = codehem.extract(example.content)
    function_element = codehem.filter(result, 'test_function')

    assert function_element is not None, f"Function {example.metadata['function_name']} not found"
    assert function_element.type == CodeElementType.FUNCTION, f"Expected function type, got {function_element.type}"
    assert function_element.range.start_line == example.expected_start_line, \
        f'Expected function start at line {example.expected_start_line}, got {function_element.range.start_line}'
    assert function_element.range.end_line == example.expected_end_line, \
        f'Expected function end at line {example.expected_end_line}, got {function_element.range.end_line}'
