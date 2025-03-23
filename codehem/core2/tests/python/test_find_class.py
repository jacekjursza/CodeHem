import pytest
from codehem.core2.codehem2 import CodeHem2
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_find_class_simple(codehem2):
    """Test finding a simple class."""
    example = TestHelper.load_example('class_simple.py', category='class')
    
    # Use extract + filter instead of direct find_class
    result = codehem2.extract(example.content)
    class_element = codehem2.filter(result, example.class_name)
    
    assert class_element is not None, f"Class {example.class_name} not found"
    assert class_element.range.start_line == example.expected_start_line, \
        f'Expected class start at line {example.expected_start_line}, got {class_element.range.start_line}'
    assert class_element.range.end_line == example.expected_end_line, \
        f'Expected class end at line {example.expected_end_line}, got {class_element.range.end_line}'

def test_find_class_missing(codehem2):
    """Test finding a non-existent class."""
    example = TestHelper.load_example('class_missing.py', category='class')
    
    # Use extract + filter instead of direct find_class
    result = codehem2.extract(example.content)
    class_element = codehem2.filter(result, example.class_name)
    
    assert class_element is None, 'Expected None for a non-existent class'