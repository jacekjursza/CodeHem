import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_property_setter_before_getter(python_finder):
    """Test finding a property when the setter is defined before the getter."""
    example = TestHelper.load_example("property_setter_before_getter.py", category="property")
    
    (start_line, end_line) = python_finder.find_property(
        example.content,
        example.class_name,
        example.property_name,
        include_extra=example.include_extra
    )
    
    assert start_line == example.expected_start_line, f'Expected property start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected property end at line {example.expected_end_line}, got {end_line}'

def test_find_property_among_other_decorators(python_finder):
    """Test finding a property that has multiple decorators."""
    example = TestHelper.load_example("property_among_other_decorators.py", category="property")
    
    (start_line, end_line) = python_finder.find_property(
        example.content,
        example.class_name,
        example.property_name,
        include_extra=example.include_extra
    )
    
    assert start_line == example.expected_start_line, f'Expected property start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected property end at line {example.expected_end_line}, got {end_line}'