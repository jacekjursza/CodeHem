import pytest

from core.finder.factory import get_code_finder


@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_property_setter_simple(python_finder):
    code = '''
class MyClass:
    @property
    def my_value(self):
        return self._value
        
    @my_value.setter
    def my_value(self, value):
        self._value = value
'''
    (start_line, end_line) = python_finder.find_property_setter(code, 'MyClass', 'my_value')
    assert start_line == 7, f'Expected setter start at line 7, got {start_line}'
    assert end_line == 9, f'Expected setter end at line 9, got {end_line}'

def test_find_property_setter_missing(python_finder):
    code = '''
class MyClass:
    @property
    def my_value(self):
        return self._value
'''
    (start_line, end_line) = python_finder.find_property_setter(code, 'MyClass', 'my_value')
    assert start_line == 0 and end_line == 0, 'Expected no lines when setter does not exist'