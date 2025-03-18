import pytest
import os
import tempfile

from manipulator.factory import get_code_manipulator


@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_fix_class_method_xpath_method_definition(python_manipulator):
    content = """
def method_name(self):
    return "Hello"
"""
    xpath = "ClassName"
    expected_xpath = "ClassName.method_name"
    fixed_xpath, attributes = python_manipulator.fix_class_method_xpath(content, xpath)
    assert fixed_xpath == expected_xpath
    assert attributes['target_type'] == 'method'
    assert attributes['class_name'] == 'ClassName'
    assert attributes['method_name'] == 'method_name'

def test_fix_class_method_xpath_decorated_method(python_manipulator):
    content = """
@decorator
def method_name(self):
    return "Hello"
"""
    xpath = "ClassName"
    expected_xpath = "ClassName.method_name"
    fixed_xpath, attributes = python_manipulator.fix_class_method_xpath(content, xpath)
    assert fixed_xpath == expected_xpath
    assert attributes['method_name'] == 'method_name'

def test_fix_class_method_xpath_already_has_class(python_manipulator):
    content = """
def method_name(self):
    return "Hello"
"""
    xpath = "ClassName.method_name"
    fixed_xpath, attributes = python_manipulator.fix_class_method_xpath(content, xpath)
    assert fixed_xpath == xpath
    assert attributes == {}

def test_fix_class_method_xpath_not_a_method(python_manipulator):
    content = """
def function_name(param):
    return param
"""
    xpath = "function_name"
    fixed_xpath, attributes = python_manipulator.fix_class_method_xpath(content, xpath)
    assert fixed_xpath == xpath
    assert attributes == {}

def test_fix_class_method_xpath_with_file(python_manipulator):
    content = """
def method_name(self):
    return "Hello"
"""
    xpath = "ClassName"

    # Create a temporary file with a class definition
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        temp_file.write("""
class ClassName:
    pass
""")
        temp_file_path = temp_file.name

    try:
        fixed_xpath, attributes = python_manipulator.fix_class_method_xpath(content, xpath, temp_file_path)
        assert fixed_xpath == "ClassName.method_name"
        assert attributes['target_type'] == 'method'
    finally:
        os.unlink(temp_file_path)