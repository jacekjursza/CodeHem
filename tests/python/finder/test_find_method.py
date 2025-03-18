import pytest
from finder.factory import get_code_finder

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_method_simple(python_finder):
    code = '\nclass MyClass:\n    def my_method(self):\n        return 42\n'
    (start_line, end_line) = python_finder.find_method(code, 'MyClass', 'my_method')
    assert start_line == 3, f'Expected method start at line 3, got {start_line}'
    assert end_line == 4, f'Expected method end at line 4, got {end_line}'

def test_find_method_missing(python_finder):
    code = '\nclass MyClass:\n    def another_method(self):\n        return 42\n'
    (start_line, end_line) = python_finder.find_method(code, 'MyClass', 'my_method')
    assert start_line == 0 and end_line == 0, 'Expected no lines for a non-existent method'

def test_find_method_with_single_decorator(python_finder):
    code = '\nclass MyClass:\n    @decorator\n    def my_method(self):\n        return 42\n'
    (start_line, end_line) = python_finder.find_method(code, 'MyClass', 'my_method')
    assert start_line == 4, f'Expected method start at line 4, got {start_line}'
    assert end_line == 5, f'Expected method end at line 5, got {end_line}'

def test_find_method_with_multiple_decorators(python_finder):
    code = '\nclass MyClass:\n    @decorator1\n    @decorator2\n    @decorator3\n    def my_method(self):\n        return 42\n'
    (start_line, end_line) = python_finder.find_method(code, 'MyClass', 'my_method')
    assert start_line == 6, f'Expected method start at line 6, got {start_line}'
    assert end_line == 7, f'Expected method end at line 7, got {end_line}'