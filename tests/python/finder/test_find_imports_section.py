import pytest

from core.finder.factory import get_code_finder


@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_imports_section_simple(python_finder):
    code = '''
import os
import sys

def foo():
    pass
'''
    start_line, end_line = python_finder.find_imports_section(code)
    assert start_line == 2, f"Expected imports section start at line 2, got {start_line}"
    assert end_line == 3, f"Expected imports section end at line 3, got {end_line}"

def test_find_imports_section_none(python_finder):
    code = '''
def foo():
    pass
'''
    start_line, end_line = python_finder.find_imports_section(code)
    assert start_line == 0 and end_line == 0, "Expected no imports section when no imports"