import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_class_simple(python_finder):
    example = TestHelper.load_example('class_simple.py', category='class')
    (start_line, end_line) = python_finder.find_class(example.content, example.class_name)
    assert start_line == example.expected_start_line, f'Expected class start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected class end at line {example.expected_end_line}, got {end_line}'

def test_find_class_missing(python_finder):
    example = TestHelper.load_example('class_missing.py', category='class')
    (start_line, end_line) = python_finder.find_class(example.content, example.class_name)
    assert start_line == 0 and end_line == 0, 'Expected no lines for a non-existent class'