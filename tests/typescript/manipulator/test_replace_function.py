import pytest
from codehem.core import get_code_manipulator

@pytest.fixture
def typescript_manipulator():
    return get_code_manipulator('typescript')

def test_replace_function_simple(typescript_manipulator):
    original_code = '\nfunction myFunction() {\n    console.log("Hello");\n}\n'
    new_function = '\nfunction myFunction() {\n    console.log("Hello, World!");\n}\n'
    expected = '\nfunction myFunction() {\n    console.log("Hello, World!");\n}\n'
    result = typescript_manipulator.replace_function(original_code, 'myFunction', new_function)
    assert result.strip() == expected.strip()

def test_replace_function_with_comments(typescript_manipulator):
    original_code = '\n/**\n * Original function documentation\n */\nfunction myFunction() {\n    console.log("Hello");\n}\n'
    new_function = '\n/**\n * Updated function documentation\n */\nfunction myFunction() {\n    console.log("Hello, World!");\n}\n'
    expected = '\n/**\n * Updated function documentation\n */\nfunction myFunction() {\n    console.log("Hello, World!");\n}\n'
    result = typescript_manipulator.replace_function(original_code, 'myFunction', new_function)
    assert result.strip() == expected.strip()

def test_replace_function_missing(typescript_manipulator):
    original_code = '\nfunction anotherFunction() {\n    console.log("Hello");\n}\n'
    new_function = '\nfunction myFunction() {\n    console.log("Hello, World!");\n}\n'
    result = typescript_manipulator.replace_function(original_code, 'myFunction', new_function)
    assert result.strip() == original_code.strip()

def test_replace_function_with_types(typescript_manipulator):
    original_code = '\nfunction calculateSum(a: number, b: number): number {\n    return a + b;\n}\n'
    new_function = '\nfunction calculateSum(a: number, b: number, c: number = 0): number {\n    return a + b + c;\n}\n'
    expected = '\nfunction calculateSum(a: number, b: number, c: number = 0): number {\n    return a + b + c;\n}\n'
    result = typescript_manipulator.replace_function(original_code, 'calculateSum', new_function)
    assert result.strip() == expected.strip()

def test_replace_async_function(typescript_manipulator):
    original_code = '\nasync function fetchData() {\n    return await fetch("api/data");\n}\n'
    new_function = '\nasync function fetchData() {\n    const response = await fetch("api/data");\n    return await response.json();\n}\n'
    expected = '\nasync function fetchData() {\n    const response = await fetch("api/data");\n    return await response.json();\n}\n'
    result = typescript_manipulator.replace_function(original_code, 'fetchData', new_function)
    assert result.strip() == expected.strip()