import pytest
from core.manipulator import get_code_manipulator

@pytest.fixture
def typescript_manipulator():
    return get_code_manipulator('typescript')

def test_replace_class_simple(typescript_manipulator):
    original_code = '\nclass MyClass {\n    method() {\n        console.log("Hello");\n    }\n}\n'
    new_class = '\nclass MyClass {\n    method() {\n        console.log("Hello, World!");\n    }\n}\n'
    expected = '\nclass MyClass {\n    method() {\n        console.log("Hello, World!");\n    }\n}\n'
    result = typescript_manipulator.replace_class(original_code, 'MyClass', new_class)
    assert result.strip() == expected.strip()

def test_replace_class_missing(typescript_manipulator):
    original_code = '\nclass AnotherClass {\n    method() {\n        console.log("Hello");\n    }\n}\n'
    new_class = '\nclass MyClass {\n    method() {\n        console.log("Hello, World!");\n    }\n}\n'
    result = typescript_manipulator.replace_class(original_code, 'MyClass', new_class)
    assert result.strip() == original_code.strip()

def test_replace_class_with_inheritance(typescript_manipulator):
    original_code = '\nclass MyClass extends BaseClass {\n    method() {\n        super.method();\n        console.log("Extended");\n    }\n}\n'
    new_class = '\nclass MyClass extends NewBaseClass {\n    method() {\n        super.method();\n        console.log("New implementation");\n    }\n}\n'
    expected = '\nclass MyClass extends NewBaseClass {\n    method() {\n        super.method();\n        console.log("New implementation");\n    }\n}\n'
    result = typescript_manipulator.replace_class(original_code, 'MyClass', new_class)
    assert result.strip() == expected.strip()

def test_replace_class_with_decorators(typescript_manipulator):
    original_code = '\n@Component({\n    selector: "app-component"\n})\nclass MyComponent {\n    constructor() {}\n}\n'
    new_class = '\n@Component({\n    selector: "app-new-component"\n})\nclass MyComponent {\n    constructor() {}\n    ngOnInit() {}\n}\n'
    expected = '\n@Component({\n    selector: "app-new-component"\n})\nclass MyComponent {\n    constructor() {}\n    ngOnInit() {}\n}\n'
    result = typescript_manipulator.replace_class(original_code, 'MyComponent', new_class)
    assert result.strip() == expected.strip()

def test_replace_exported_class(typescript_manipulator):
    original_code = '\nexport class ExportedClass {\n    method() {}\n}\n'
    new_class = '\nexport class ExportedClass {\n    method() {}\n    newMethod() {}\n}\n'
    expected = '\nexport class ExportedClass {\n    method() {}\n    newMethod() {}\n}\n'
    result = typescript_manipulator.replace_class(original_code, 'ExportedClass', new_class)
    assert result.strip() == expected.strip()