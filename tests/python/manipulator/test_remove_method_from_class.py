
# test_remove_method_from_class.py
import pytest

from manipulator.factory import get_code_manipulator


@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_remove_method_from_class_simple(python_manipulator):
    original_code = """
class MyClass:
    def method1(self):
        print("Hello")

    def method2(self):
        print("World")
"""
    expected = """
class MyClass:
    def method1(self):
        print("Hello")
"""
    result = python_manipulator.remove_method_from_class(original_code, 'MyClass', 'method2')
    assert result.strip() == expected.strip()

def test_remove_method_from_class_with_decorator(python_manipulator):
    original_code = """
class MyClass:
    def method1(self):
        print("Hello")

    @decorator
    def method2(self):
        print("World")
"""
    expected = """
class MyClass:
    def method1(self):
        print("Hello")
"""
    result = python_manipulator.remove_method_from_class(original_code, 'MyClass', 'method2')
    assert result.strip() == expected.strip()

def test_remove_method_class_missing(python_manipulator):
    original_code = """
class ExistingClass:
    def method(self):
        print("Hello")
"""
    # Should not change if class not found
    result = python_manipulator.remove_method_from_class(original_code, 'MissingClass', 'method')
    assert result.strip() == original_code.strip()

def test_remove_method_missing(python_manipulator):
    original_code = """
class MyClass:
    def existing_method(self):
        print("Hello")
"""
    # Should not change if method not found
    result = python_manipulator.remove_method_from_class(original_code, 'MyClass', 'missing_method')
    assert result.strip() == original_code.strip()
