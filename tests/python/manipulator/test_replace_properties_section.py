
# test_replace_properties_section.py
import pytest

from codehem.core.manipulator.factory import get_code_manipulator


@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_replace_properties_section_simple(python_manipulator):
    original_code = """
class MyClass:
    x = 1
    y = 2
    z = "test"

    def method(self):
        pass
"""
    new_properties = """
x = 10
y = 20
z = "updated"
"""
    expected = """
class MyClass:
    x = 10
    y = 20
    z = "updated"

    def method(self):
        pass
"""
    result = python_manipulator.replace_properties_section(original_code, 'MyClass', new_properties)
    assert result.strip() == expected.strip()

def test_replace_properties_section_no_properties(python_manipulator):
    original_code = """
class MyClass:
    def method(self):
        pass
"""
    new_properties = """
x = 10
y = 20
"""
    expected = """
class MyClass:
    x = 10
    y = 20

    def method(self):
        pass
"""
    result = python_manipulator.replace_properties_section(original_code, 'MyClass', new_properties)
    assert result.strip() == expected.strip()

def test_replace_properties_section_class_missing(python_manipulator):
    original_code = """
class ExistingClass:
    x = 1
"""
    new_properties = """
x = 10
"""
    # Should not change if class not found
    result = python_manipulator.replace_properties_section(original_code, 'MissingClass', new_properties)
    assert result.strip() == original_code.strip()
