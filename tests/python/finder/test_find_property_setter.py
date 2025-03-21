import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_property_setter_simple(python_finder):
    example = TestHelper.load_example("property_setter_simple.py", category="property")
    
    (start_line, end_line) = python_finder.find_property_setter(
        example.content,
        example.class_name,
        example.property_name,
        include_extra=example.include_extra
    )
    
    assert start_line == example.expected_start_line, f'Expected setter start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected setter end at line {example.expected_end_line}, got {end_line}'

def test_find_property_setter_missing(python_finder):
    example = TestHelper.load_example("property_setter_missing.py", category="property")
    
    (start_line, end_line) = python_finder.find_property_setter(
        example.content,
        example.class_name,
        example.property_name
    )
    
    assert start_line == 0 and end_line == 0, 'Expected no lines when setter does not exist'