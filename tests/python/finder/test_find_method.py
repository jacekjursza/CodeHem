import pytest
from codehem.core.finder import get_code_finder
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_method_simple(python_finder):
    example = TestHelper.load_example('method_simple.py', category='method')
    (start_line, end_line) = python_finder.find_method(example.content, example.class_name, example.method_name)
    assert start_line == example.expected_start_line, f'Expected method start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected method end at line {example.expected_end_line}, got {end_line}'

def test_find_method_missing(python_finder):
    example = TestHelper.load_example('method_missing.py', category='method')
    (start_line, end_line) = python_finder.find_method(example.content, example.class_name, example.method_name)
    assert start_line == 0 and end_line == 0, 'Expected no lines for a non-existent method'

def test_find_method_with_single_decorator(python_finder):
    example = TestHelper.load_example('method_with_single_decorator.py', category='method')
    (start_line, end_line) = python_finder.find_method(example.content, example.class_name, example.method_name)
    assert start_line == example.expected_start_line, f'Expected method start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected method end at line {example.expected_end_line}, got {end_line}'
    
    # Test with include_extra parameter
    include_extra_start = example.metadata.get('include_extra_start_line')
    include_extra_end = example.metadata.get('include_extra_end_line')
    (start_line, end_line) = python_finder.find_method(example.content, example.class_name, example.method_name, include_extra=True)
    assert start_line == include_extra_start, f'Expected start line with include_extra {include_extra_start}, got {start_line}'
    assert end_line == include_extra_end, f'Expected end line with include_extra {include_extra_end}, got {end_line}'

def test_find_method_with_multiple_decorators(python_finder):
    example = TestHelper.load_example('method_with_multiple_decorators.py', category='method')
    (start_line, end_line) = python_finder.find_method(example.content, example.class_name, example.method_name)
    assert start_line == example.expected_start_line, f'Expected method start at line {example.expected_start_line}, got {start_line}'
    assert end_line == example.expected_end_line, f'Expected method end at line {example.expected_end_line}, got {end_line}'
    
    # Test with include_extra parameter
    include_extra_start = example.metadata.get('include_extra_start_line')
    include_extra_end = example.metadata.get('include_extra_end_line')
    (start_line, end_line) = python_finder.find_method(example.content, example.class_name, example.method_name, include_extra=True)
    assert start_line == include_extra_start, f'Expected start line with include_extra {include_extra_start}, got {start_line}'
    assert end_line == include_extra_end, f'Expected end line with include_extra {include_extra_end}, got {end_line}'