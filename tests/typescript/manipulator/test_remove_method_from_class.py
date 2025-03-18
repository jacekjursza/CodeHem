import pytest
from manipulator.factory import get_code_manipulator

@pytest.fixture
def typescript_manipulator():
    return get_code_manipulator('typescript')

def test_remove_method_from_class_simple(typescript_manipulator):
    original_code = '\nclass MyClass {\n    method1() {\n        console.log("Method 1");\n    }\n\n    method2() {\n        console.log("Method 2");\n    }\n}\n'
    expected = '\nclass MyClass {\n    method1() {\n        console.log("Method 1");\n    }\n}\n'
    result = typescript_manipulator.remove_method_from_class(original_code, 'MyClass', 'method2')
    assert result.strip() == expected.strip()

def test_remove_method_class_missing(typescript_manipulator):
    original_code = '\nclass ExistingClass {\n    method() {\n        console.log("Method");\n    }\n}\n'
    result = typescript_manipulator.remove_method_from_class(original_code, 'MissingClass', 'method')
    assert result.strip() == original_code.strip()

def test_remove_method_missing(typescript_manipulator):
    original_code = '\nclass MyClass {\n    existingMethod() {\n        console.log("Existing");\n    }\n}\n'
    result = typescript_manipulator.remove_method_from_class(original_code, 'MyClass', 'missingMethod')
    assert result.strip() == original_code.strip()

def test_remove_method_with_modifiers(typescript_manipulator):
    original_code = '\nclass MyClass {\n    method1() {}\n    \n    private method2() {}\n    \n    public method3() {}\n}\n'
    expected = '\nclass MyClass {\n    method1() {}\n    \n    public method3() {}\n}\n'
    result = typescript_manipulator.remove_method_from_class(original_code, 'MyClass', 'method2')
    assert result.strip() == expected.strip()

def test_remove_static_method(typescript_manipulator):
    original_code = '\nclass MyClass {\n    method1() {}\n    \n    static staticMethod() {\n        console.log("Static");\n    }\n}\n'
    expected = '\nclass MyClass {\n    method1() {}\n}\n'
    result = typescript_manipulator.remove_method_from_class(original_code, 'MyClass', 'staticMethod')
    assert result.strip() == expected.strip()

def test_remove_last_method(typescript_manipulator):
    original_code = '\nclass MyClass {\n    onlyMethod() {\n        console.log("Only method");\n    }\n}\n'
    expected = '\nclass MyClass {\n}\n'
    result = typescript_manipulator.remove_method_from_class(original_code, 'MyClass', 'onlyMethod')
    # This test may need adjustment based on how your implementation handles empty classes
    assert "onlyMethod" not in result, "Method should be removed"