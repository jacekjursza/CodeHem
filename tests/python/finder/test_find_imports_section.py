import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_imports_section_simple(python_finder):
    example = TestHelper.load_example('imports_simple.py', category='import')
    (start_line, end_line) = python_finder.find_imports_section(example.content)
    assert start_line == example.expected_start_line, f'Expected imports section start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected imports section end at line {example.expected_end_line}, got {end_line}'

def test_find_imports_section_none(python_finder):
    example = TestHelper.load_example('imports_none.py', category='import')
    (start_line, end_line) = python_finder.find_imports_section(example.content)
    assert start_line == example.expected_start_line and end_line == example.expected_end_line, 'Expected no imports section when no imports'