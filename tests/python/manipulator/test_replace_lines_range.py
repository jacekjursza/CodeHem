import pytest
from manipulator.factory import get_code_manipulator

@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_replace_lines_range_simple(python_manipulator):
    original_code = "line 1\nline 2\nline 3\nline 4\nline 5"
    new_content = "new line 2\nnew line 3"
    expected = "line 1\nnew line 2\nnew line 3\nline 4\nline 5"
    result = python_manipulator.replace_lines_range(original_code, 2, 3, new_content)
    assert result.strip() == expected.strip()

def test_replace_lines_range_preserve_formatting(python_manipulator):
    original_code = "line 1\nline 2\nline 3\nline 4\nline 5"
    new_content = "new line 2\nnew line 3" # No trailing newline
    expected = "line 1\nnew line 2\nnew line 3line 4\nline 5"
    result = python_manipulator.replace_lines_range(original_code, 2, 3, new_content, preserve_formatting=True)
    assert result.strip() == expected.strip()

def test_replace_lines_range_empty_original(python_manipulator):
    original_code = ""
    new_content = "new content"
    result = python_manipulator.replace_lines_range(original_code, 1, 1, new_content)
    assert result == new_content

def test_replace_lines_range_out_of_bounds(python_manipulator):
    original_code = "line 1\nline 2\nline 3"
    new_content = "new line"
    result = python_manipulator.replace_lines_range(original_code, 0, 10, new_content)
    assert "new line" in result
    result = python_manipulator.replace_lines_range(original_code, -5, 2, new_content)
    assert result.startswith("new line")

def test_fix_special_characters_in_content(python_manipulator):
    content = "def *special_function*(param):\n    return param"
    xpath = "normal_function"
    expected_content = "def special_function(param):\n    return param"
    (fixed_content, fixed_xpath) = python_manipulator.fix_special_characters(content, xpath)
    assert fixed_content.strip() == expected_content.strip()
    assert fixed_xpath == xpath

def test_fix_special_characters_in_xpath(python_manipulator):
    content = "def normal_function():\n    pass"
    xpath = "Class.*special_method*"
    expected_xpath = "Class.special_method"
    (fixed_content, fixed_xpath) = python_manipulator.fix_special_characters(content, xpath)
    assert fixed_content == content
    assert fixed_xpath == expected_xpath

def test_fix_special_characters_in_standalone_xpath(python_manipulator):
    content = "def normal_function():\n    pass"
    xpath = "*special_function*"
    expected_xpath = "special_function"
    (fixed_content, fixed_xpath) = python_manipulator.fix_special_characters(content, xpath)
    assert fixed_content == content
    assert fixed_xpath == expected_xpath

def test_fix_special_characters_no_changes(python_manipulator):
    content = "def normal_function():\n    pass"
    xpath = "normal_function"
    (fixed_content, fixed_xpath) = python_manipulator.fix_special_characters(content, xpath)
    assert fixed_content == content
    assert fixed_xpath == xpath