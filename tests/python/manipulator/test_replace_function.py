import pytest
from manipulator.factory import get_code_manipulator

@pytest.fixture
def python_manipulator():
    return get_code_manipulator('python')

def test_replace_function_simple(python_manipulator):
    original_code = """
def my_function():
    print("Hello")
"""
    new_function = """
def my_function():
    print("Hello, World!")
"""
    expected = """
def my_function():
    print("Hello, World!")
"""
    result = python_manipulator.replace_function(original_code, 'my_function', new_function)
    assert result.strip() == expected.strip()

def test_replace_function_with_docstring(python_manipulator):
    original_code = """
def my_function():
    \"\"\"Original docstring.\"\"\"
    print("Hello")
"""
    new_function = """
def my_function():
    \"\"\"Updated docstring.\"\"\"
    print("Hello, World!")
"""
    expected = """
def my_function():
    \"\"\"Updated docstring.\"\"\"
    print("Hello, World!")
"""
    result = python_manipulator.replace_function(original_code, 'my_function', new_function)
    assert result.strip() == expected.strip()

def test_replace_function_missing(python_manipulator):
    original_code = """
def another_function():
    print("Hello")
"""
    new_function = """
def my_function():
    print("Hello, World!")
"""
    # Should not change if function not found
    result = python_manipulator.replace_function(original_code, 'my_function', new_function)
    assert result.strip() == original_code.strip()

def test_replace_function_with_decorator(python_manipulator):
    original_code = """
@decorator
def my_function():
    print("Hello")
"""
    new_function = """
@new_decorator
def my_function():
    print("Hello, World!")
"""
    expected = """
@new_decorator
def my_function():
    print("Hello, World!")
"""
    result = python_manipulator.replace_function(original_code, 'my_function', new_function)
    assert result.strip() == expected.strip()
