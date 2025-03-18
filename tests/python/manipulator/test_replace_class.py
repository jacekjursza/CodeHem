
# test_replace_class.py
import pytest

from manipulator.factory import get_code_manipulator


@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_replace_class_simple(python_manipulator):
    original_code = """
class MyClass:
    def method(self):
        print("Hello")
"""
    new_class = """
class MyClass:
    def method(self):
        print("Hello, World!")
"""
    expected = """
class MyClass:
    def method(self):
        print("Hello, World!")
"""
    result = python_manipulator.replace_class(original_code, 'MyClass', new_class)
    assert result.strip() == expected.strip()

def test_replace_class_missing(python_manipulator):
    original_code = """
class AnotherClass:
    def method(self):
        print("Hello")
"""
    new_class = """
class MyClass:
    def method(self):
        print("Hello, World!")
"""
    # Should not change if class not found
    result = python_manipulator.replace_class(original_code, 'MyClass', new_class)
    assert result.strip() == original_code.strip()

def test_replace_class_with_decorator(python_manipulator):
    original_code = """
@decorator
class MyClass:
    def method(self):
        print("Hello")
"""
    new_class = """
@new_decorator
class MyClass:
    def method(self):
        print("Hello, World!")
"""
    expected = """
@new_decorator
class MyClass:
    def method(self):
        print("Hello, World!")
"""
    result = python_manipulator.replace_class(original_code, 'MyClass', new_class)
    assert result.strip() == expected.strip()

def test_replace_class_with_inheritance(python_manipulator):
    original_code = """
class MyClass(BaseClass):
    def method(self):
        print("Hello")
"""
    new_class = """
class MyClass(NewBaseClass):
    def method(self):
        print("Hello, World!")
"""
    expected = """
class MyClass(NewBaseClass):
    def method(self):
        print("Hello, World!")
"""
    result = python_manipulator.replace_class(original_code, 'MyClass', new_class)
    assert result.strip() == expected.strip()
