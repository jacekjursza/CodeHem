import pytest
from codehem.core import get_code_manipulator

@pytest.fixture
def typescript_manipulator():
    return get_code_manipulator('typescript')

def test_add_method_to_class_simple(typescript_manipulator):
    original_code = '\nclass MyClass {\n    existingMethod() {\n        console.log("Existing");\n    }\n}\n'
    method_code = '\nnewMethod() {\n    console.log("New method");\n}\n'
    expected = '\nclass MyClass {\n    existingMethod() {\n        console.log("Existing");\n    }\n\n    newMethod() {\n        console.log("New method");\n    }\n}\n'
    result = typescript_manipulator.add_method_to_class(original_code, 'MyClass', method_code)
    assert result.strip() == expected.strip()

def test_add_method_to_empty_class(typescript_manipulator):
    original_code = '\nclass EmptyClass {\n}\n'
    method_code = '\nmethod() {\n    console.log("Method in empty class");\n}\n'
    expected = '\nclass EmptyClass {\n    method() {\n        console.log("Method in empty class");\n    }\n}\n'
    result = typescript_manipulator.add_method_to_class(original_code, 'EmptyClass', method_code)
    assert result.strip() == expected.strip()

def test_add_method_with_modifiers(typescript_manipulator):
    original_code = '\nclass MyClass {\n    method1() {}\n}\n'
    method_code = '\nprivate method2() {\n    this.method1();\n}\n'
    expected = '\nclass MyClass {\n    method1() {}\n\n    private method2() {\n        this.method1();\n    }\n}\n'
    result = typescript_manipulator.add_method_to_class(original_code, 'MyClass', method_code)
    assert result.strip() == expected.strip()

def test_add_static_method(typescript_manipulator):
    original_code = '\nclass MyClass {\n    instanceMethod() {}\n}\n'
    method_code = '\nstatic staticMethod() {\n    console.log("Static method");\n}\n'
    expected = '\nclass MyClass {\n    instanceMethod() {}\n\n    static staticMethod() {\n        console.log("Static method");\n    }\n}\n'
    result = typescript_manipulator.add_method_to_class(original_code, 'MyClass', method_code)
    assert result.strip() == expected.strip()

def test_add_async_method(typescript_manipulator):
    original_code = '\nclass MyClass {\n    method1() {}\n}\n'
    method_code = '\nasync asyncMethod() {\n    return await Promise.resolve("result");\n}\n'
    expected = '\nclass MyClass {\n    method1() {}\n\n    async asyncMethod() {\n        return await Promise.resolve("result");\n    }\n}\n'
    result = typescript_manipulator.add_method_to_class(original_code, 'MyClass', method_code)
    assert result.strip() == expected.strip()

def test_add_method_to_nonexistent_class(typescript_manipulator):
    original_code = '\nclass ExistingClass {\n    method() {}\n}\n'
    method_code = '\nnewMethod() {}\n'
    result = typescript_manipulator.add_method_to_class(original_code, 'NonExistentClass', method_code)
    assert result.strip() == original_code.strip()