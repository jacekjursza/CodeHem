import pytest
from finder.factory import get_code_finder

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_property_simple(python_finder):
        code = '''
    class MyClass:
        @property
        def my_value(self):
            return 123
    '''
        (start_line, end_line) = python_finder.find_property(code, 'MyClass', 'my_value')
        assert start_line == 3, f'Expected property start at line 3, got {start_line}'
        assert end_line == 5, f'Expected property end at line 5, got {end_line}'

def test_find_property_missing(python_finder):
    code = '''
class MyClass:
    @property
    def another_value(self):
        return 123
'''
    start_line, end_line = python_finder.find_property(code, 'MyClass', 'no_such_property')
    assert start_line == 0 and end_line == 0, "Expected no lines when property doesn't exist"