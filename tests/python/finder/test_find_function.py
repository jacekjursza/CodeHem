import pytest

from core.finder.factory import get_code_finder


@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_function_simple(python_finder):
    code = '\ndef my_function():\n    print("Hello")\n'
    (start_line, end_line) = python_finder.find_function(code, 'my_function')
    assert start_line == 2, f'Expected start line 2, got {start_line}'
    assert end_line == 3, f'Expected end line 3, got {end_line}'

def test_find_function_missing(python_finder):
    code = '\ndef another_function():\n    print("Still hello")\n'
    (start_line, end_line) = python_finder.find_function(code, 'my_function')
    assert start_line == 0 and end_line == 0, 'Expected no lines when function does not exist'

def test_find_function_with_single_decorator(python_finder):
    code = '\n@decorator\ndef my_function():\n    print("Hello")\n'
    (start_line, end_line) = python_finder.find_function(code, 'my_function')
    assert start_line == 3, f'Expected start line 3, got {start_line}'
    assert end_line == 4, f'Expected end line 4, got {end_line}'

def test_find_function_with_multiple_decorators(python_finder):
    code = '\n@decorator1\n@decorator2\n@decorator3\ndef my_function():\n    print("Hello")\n'
    (start_line, end_line) = python_finder.find_function(code, 'my_function')
    assert start_line == 5, f'Expected start line 5, got {start_line}'
    assert end_line == 6, f'Expected end line 6, got {end_line}'