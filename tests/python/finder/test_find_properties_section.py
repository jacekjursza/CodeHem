import pytest
from finder.factory import get_code_finder

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_properties_section_simple(python_finder):
    code = '''
class MyClass:
    x = 1
    y = 2
    z = "test"
    
    def method(self):
        pass
'''
    (start_line, end_line) = python_finder.find_properties_section(code, 'MyClass')
    assert start_line == 3, f'Expected properties section start at line 3, got {start_line}'
    assert end_line == 5, f'Expected properties section end at line 5, got {end_line}'

def test_find_properties_section_none(python_finder):
    code = '''
class MyClass:
    def method(self):
        pass
'''
    (start_line, end_line) = python_finder.find_properties_section(code, 'MyClass')
    assert start_line == 0 and end_line == 0, 'Expected no properties section when no properties'