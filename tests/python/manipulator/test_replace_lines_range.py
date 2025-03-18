
# test_replace_lines_range.py
import pytest

from manipulator.factory import get_code_manipulator


@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_replace_lines_range_simple(python_manipulator):
    original_code = """
line 1
line 2
line 3
line 4
line 5
"""
    new_content = """
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
    result = python_manipulator.replace_lines_range(original_code, 2, 3, new_content)
    assert result.strip() == expected.strip()

def test_replace_lines_range_preserve_formatting(python_manipulator):
    original_code = """
line 1
line 2
line 3
line 4
line 5
"""
    new_content = """
new line 2
new line 3"""  # No trailing newline
    expected = """
line 1
new line 2
new line 3line 4
line 5
"""
    result = python_manipulator.replace_lines_range(original_code, 2, 3, new_content, preserve_formatting=True)
    assert result.strip() == expected.strip()

def test_replace_lines_range_empty_original(python_manipulator):
    original_code = ""
    new_content = "new content"
    result = python_manipulator.replace_lines_range(original_code, 1, 1, new_content)
    assert result == new_content

def test_replace_lines_range_out_of_bounds(python_manipulator):
    original_code = """
line 1
line 2
line 3
"""
    new_content = "new content"
    # Should adjust start and end lines to be within bounds
    result = python_manipulator.replace_lines_range(original_code, 0, 10, new_content)
    assert "new content" in result

    # Should adjust to start at line 1
    result = python_manipulator.replace_lines_range(original_code, -5, 2, new_content)
    assert result.startswith("new content")

# test_fix_special_characters.py
import pytest

@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_fix_special_characters_in_content(python_manipulator):
    content = """
def *special_function*(param):
    return param
"""
    xpath = "normal_function"
    expected_content = """
def special_function(param):
    return param
"""
    fixed_content, fixed_xpath = python_manipulator.fix_special_characters(content, xpath)
    assert fixed_content.strip() == expected_content.strip()
    assert fixed_xpath == xpath

def test_fix_special_characters_in_xpath(python_manipulator):
    content = "def normal_function():\n    pass"
    xpath = "Class.*special_method*"
    expected_xpath = "Class.special_method"
    fixed_content, fixed_xpath = python_manipulator.fix_special_characters(content, xpath)
    assert fixed_content == content
    assert fixed_xpath == expected_xpath

def test_fix_special_characters_in_standalone_xpath(python_manipulator):
    content = "def normal_function():\n    pass"
    xpath = "*special_function*"
    expected_xpath = "special_function"
    fixed_content, fixed_xpath = python_manipulator.fix_special_characters(content, xpath)
    assert fixed_content == content
    assert fixed_xpath == expected_xpath

def test_fix_special_characters_no_changes(python_manipulator):
    content = "def normal_function():\n    pass"
    xpath = "normal_function"
    fixed_content, fixed_xpath = python_manipulator.fix_special_characters(content, xpath)
    assert fixed_content == content
    assert fixed_xpath == xpath
