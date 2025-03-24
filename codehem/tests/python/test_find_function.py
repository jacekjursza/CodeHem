import pytest
from codehem.core.codehem2 import CodeHem2
from tests.helpers.code_examples import TestHelper
from codehem.core.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_find_function_simple(codehem2):
    """Test finding a simple function."""
    example = TestHelper.load_example('function_simple.py', category='function')
    
    # Use extract + filter instead of direct find_function
    result = codehem2.extract(example.content)
    function_element = codehem2.filter(result, example.function_name)
    
    assert function_element is not None, f"Function {example.function_name} not found"
    assert function_element.type == CodeElementType.FUNCTION, f"Expected function type, got {function_element.type}"
    assert function_element.range.start_line == example.expected_start_line, \
        f'Expected function start at line {example.expected_start_line}, got {function_element.range.start_line}'
    assert function_element.range.end_line == example.expected_end_line, \
        f'Expected function end at line {example.expected_end_line}, got {function_element.range.end_line}'

def test_find_function_missing(codehem2):
    """Test finding a non-existent function."""
    example = TestHelper.load_example('function_missing.py', category='function')
    
    # Use extract + filter instead of direct find_function
    result = codehem2.extract(example.content)
    function_element = codehem2.filter(result, example.function_name)
    
    assert function_element is None, 'Expected None when function does not exist'

def test_find_function_with_decorator(codehem2):
    """Test finding a function with a decorator."""
    example = TestHelper.load_example('function_with_single_decorator.py', category='function')
    
    # Use extract + filter instead of direct find_function
    result = codehem2.extract(example.content)
    function_element = codehem2.filter(result, example.function_name)
    
    assert function_element is not None, f"Function {example.function_name} not found"
    assert function_element.range.start_line == example.expected_start_line, \
        f'Expected function start at line {example.expected_start_line}, got {function_element.range.start_line}'
    assert function_element.range.end_line == example.expected_end_line, \
        f'Expected function end at line {example.expected_end_line}, got {function_element.range.end_line}'