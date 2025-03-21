import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_property_with_helper(python_finder):
    # Load code example
    example = TestHelper.load_example(
        "simple_property.py", 
        category="property"
    )
    
    # Run test
    (start_line, end_line) = python_finder.find_property(
        example.content, 
        example.class_name, 
        example.property_name,
        include_extra=example.include_extra
    )
    
    # Check results
    assert start_line == example.expected_start_line, \
        f"Expected property start at line {example.expected_start_line}, got {start_line}"
    assert end_line == example.expected_end_line, \
        f"Expected property end at line {example.expected_end_line}, got {end_line}"

@pytest.mark.parametrize("example_name", [
    "simple_property.py",
])
def test_parametrized_property_examples(python_finder, example_name):
    example = TestHelper.load_example(
        example_name, 
        category="property"
    )
    
    (start_line, end_line) = python_finder.find_property(
        example.content, 
        example.class_name, 
        example.property_name,
        include_extra=example.include_extra
    )
    
    assert start_line == example.expected_start_line, \
        f"Expected property start at line {example.expected_start_line}, got {start_line}"
    assert end_line == example.expected_end_line, \
        f"Expected property end at line {example.expected_end_line}, got {end_line}"