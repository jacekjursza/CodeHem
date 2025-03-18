import pytest
from manipulator.factory import get_code_manipulator

@pytest.fixture
def typescript_manipulator():
    return get_code_manipulator('typescript')

def test_replace_method_simple(typescript_manipulator):
    original_code = '\nclass MyClass {\n    myMethod() {\n        console.log("Hello");\n    }\n}\n'
    new_method = '\nmyMethod() {\n    console.log("Hello, World!");\n}\n'
    expected = '\nclass MyClass {\n    myMethod() {\n        console.log("Hello, World!");\n    }\n}\n'
    result = typescript_manipulator.replace_method(original_code, 'MyClass', 'myMethod', new_method)
    assert result.strip() == expected.strip()

def test_replace_method_missing(typescript_manipulator):
    original_code = '\nclass MyClass {\n    anotherMethod() {\n        console.log("Hello");\n    }\n}\n'
    new_method = '\nmyMethod() {\n    console.log("Hello, World!");\n}\n'
    result = typescript_manipulator.replace_method(original_code, 'MyClass', 'myMethod', new_method)
    assert result.strip() == original_code.strip()

def test_replace_method_with_modifiers(typescript_manipulator):
    original_code = '\nclass MyClass {\n    private myMethod() {\n        console.log("Private method");\n    }\n}\n'
    new_method = '\npublic myMethod() {\n    console.log("Public method now");\n}\n'
    expected = '\nclass MyClass {\n    public myMethod() {\n        console.log("Public method now");\n    }\n}\n'
    result = typescript_manipulator.replace_method(original_code, 'MyClass', 'myMethod', new_method)
    assert result.strip() == expected.strip()

def test_replace_method_with_types(typescript_manipulator):
    original_code = '\nclass MyClass {\n    calculate(a: number, b: number): number {\n        return a + b;\n    }\n}\n'
    new_method = '\ncalculate(a: number, b: number, c: number = 0): number {\n    return a + b + c;\n}\n'
    expected = '\nclass MyClass {\n    calculate(a: number, b: number, c: number = 0): number {\n        return a + b + c;\n    }\n}\n'
    result = typescript_manipulator.replace_method(original_code, 'MyClass', 'calculate', new_method)
    assert result.strip() == expected.strip()

def test_replace_async_method(typescript_manipulator):
    original_code = '\nclass ApiClient {\n    async fetchData() {\n        return await fetch("api/data");\n    }\n}\n'
    new_method = '\nasync fetchData() {\n    const response = await fetch("api/data");\n    return await response.json();\n}\n'
    expected = '\nclass ApiClient {\n    async fetchData() {\n        const response = await fetch("api/data");\n        return await response.json();\n    }\n}\n'
    result = typescript_manipulator.replace_method(original_code, 'ApiClient', 'fetchData', new_method)
    assert result.strip() == expected.strip()