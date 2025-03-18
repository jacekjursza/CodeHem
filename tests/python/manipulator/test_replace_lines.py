
# test_replace_lines.py
import pytest

from manipulator.factory import get_code_manipulator


@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_replace_lines_simple(python_manipulator):
    original_code = """
line 1
line 2
line 3
line 4
line 5
"""
    new_lines = """
new line 2
new line 3
"""
    expected = """
line 1
new line 2
new line 3
line 4
line 5
"""
    result = python_manipulator.replace_lines(original_code, 2, 3, new_lines)
    assert result.strip() == expected.strip()

def test_replace_lines_at_beginning(python_manipulator):
    original_code = """
line 1
line 2
line 3
"""
    new_lines = """
new line 1
"""
    expected = """
new line 1
line 2
line 3
"""
    result = python_manipulator.replace_lines(original_code, 1, 1, new_lines)
    assert result.strip() == expected.strip()

def test_replace_lines_at_end(python_manipulator):
    original_code = """
line 1
line 2
line 3
"""
    new_lines = """
new line 3
"""
    expected = """
line 1
line 2
new line 3
"""
    result = python_manipulator.replace_lines(original_code, 3, 3, new_lines)
    assert result.strip() == expected.strip()

def test_replace_lines_out_of_range(python_manipulator):
    original_code = """
line 1
line 2
line 3
"""
    new_lines = """
new line
"""
    # Should not change if line numbers are out of range
    result = python_manipulator.replace_lines(original_code, 0, 0, new_lines)
    assert result.strip() == original_code.strip()

    result = python_manipulator.replace_lines(original_code, 4, 5, new_lines)
    assert result.strip() == original_code.strip()
