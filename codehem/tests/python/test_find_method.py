import pytest
from codehem.core.codehem2 import CodeHem2
from tests.helpers.code_examples import TestHelper
from codehem.core.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_find_method_simple(codehem2):
    """Test finding a simple method in a class."""
    example = TestHelper.load_example('method_simple.py', category='method')
    
    # Use extract + filter instead of direct find_method
    result = codehem2.extract(example.content)
    method_element = codehem2.filter(result, f"{example.class_name}.{example.method_name}")
    
    assert method_element is not None, f"Method {example.class_name}.{example.method_name} not found"
    assert method_element.type == CodeElementType.METHOD, f"Expected method type, got {method_element.type}"
    assert method_element.range.start_line == example.expected_start_line, \
        f'Expected method start at line {example.expected_start_line}, got {method_element.range.start_line}'
    assert method_element.range.end_line == example.expected_end_line, \
        f'Expected method end at line {example.expected_end_line}, got {method_element.range.end_line}'

def test_find_method_missing(codehem2):
    """Test finding a non-existent method."""
    example = TestHelper.load_example('method_missing.py', category='method')
    
    # Use extract + filter instead of direct find_method
    result = codehem2.extract(example.content)
    method_element = codehem2.filter(result, f"{example.class_name}.{example.method_name}")
    
    assert method_element is None, 'Expected None for a non-existent method'

def test_find_method_with_decorator(codehem2):
    """Test finding a method with a decorator."""
    example = TestHelper.load_example('method_with_single_decorator.py', category='method')
    
    # Use extract + filter instead of direct find_method
    result = codehem2.extract(example.content)
    method_element = codehem2.filter(result, f"{example.class_name}.{example.method_name}")
    
    assert method_element is not None, f"Method {example.class_name}.{example.method_name} not found"
    assert method_element.range.start_line == example.expected_start_line, \
        f'Expected method start at line {example.expected_start_line}, got {method_element.range.start_line}'
    assert method_element.range.end_line == example.expected_end_line, \
        f'Expected method end at line {example.expected_end_line}, got {method_element.range.end_line}'