import pytest

from core.manipulator.factory import get_code_manipulator


@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_replace_method_simple(python_manipulator):
    original_code = """
class MyClass:
    def my_method(self):
        print("Hello")
"""
    new_method = """
def my_method(self):
    print("Hello, World!")
"""
    expected = """
class MyClass:
    def my_method(self):
        print("Hello, World!")
"""
    result = python_manipulator.replace_method(original_code, 'MyClass', 'my_method', new_method)
    assert result.strip() == expected.strip()

def test_replace_method_missing(python_manipulator):
    original_code = """
class MyClass:
    def another_method(self):
        print("Hello")
"""
    new_method = """
def my_method(self):
    print("Hello, World!")
"""
    result = python_manipulator.replace_method(original_code, 'MyClass', 'my_method', new_method)
    assert result.strip() == original_code.strip()

def test_replace_method_with_decorator(python_manipulator):
    original_code = """
class MyClass:
    @decorator
    def my_method(self):
        print("Hello")
"""
    new_method = """
@new_decorator
def my_method(self):
    print("Hello, World!")
"""
    expected = """
class MyClass:
    @new_decorator
    def my_method(self):
        print("Hello, World!")
"""
    result = python_manipulator.replace_method(original_code, 'MyClass', 'my_method', new_method)
    assert result.strip() == expected.strip()

def test_replace_method_indentation(python_manipulator):
    original_code = """
class MyClass:
    def my_method(self):
        if True:
            print("Hello")
"""
    new_method = """
def my_method(self):
    if True:
        print("Hello, World!")
"""
    expected = """
class MyClass:
    def my_method(self):
        if True:
            print("Hello, World!")
"""
    result = python_manipulator.replace_method(original_code, 'MyClass', 'my_method', new_method)
    assert result.strip() == expected.strip()