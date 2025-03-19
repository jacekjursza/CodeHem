import pytest

from core.finder.factory import get_code_finder


@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_class_simple(python_finder):
    code = '''
class MyClass:
    def method(self):
        pass
'''
    start_line, end_line = python_finder.find_class(code, 'MyClass')
    assert start_line == 2, f"Expected class start at line 2, got {start_line}"
    assert end_line == 4, f"Expected class end at line 4, got {end_line}"

def test_find_class_missing(python_finder):
    code = '''
class AnotherClass:
    pass
'''
    start_line, end_line = python_finder.find_class(code, 'NoSuchClass')
    assert start_line == 0 and end_line == 0, "Expected no lines for a non-existent class"