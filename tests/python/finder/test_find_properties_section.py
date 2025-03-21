import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_properties_section_simple(python_finder):
    example = TestHelper.load_example('properties_section_simple.py', category='property_section')
    (start_line, end_line) = python_finder.find_properties_section(example.content, example.class_name)
    assert start_line == example.expected_start_line, f'Expected properties section start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected properties section end at line {example.expected_end_line}, got {end_line}'

def test_find_properties_section_none(python_finder):
    example = TestHelper.load_example('properties_section_none.py', category='property_section')
    (start_line, end_line) = python_finder.find_properties_section(example.content, example.class_name)
    assert start_line == example.expected_start_line and end_line == example.expected_end_line, 'Expected no properties section when no properties'