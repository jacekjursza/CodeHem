import pytest
from codehem.core.finder import get_code_finder

@pytest.fixture
def typescript_finder():
    return get_code_finder('typescript')

def test_find_class_simple(typescript_finder):
    code = '\nclass MyClass {\n    method() {\n        console.log("Hello");\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_class(code, 'MyClass')
    assert start_line == 2, f'Expected class start at line 2, got {start_line}'
    assert end_line == 6, f'Expected class end at line 6, got {end_line}'

def test_find_class_missing(typescript_finder):
    code = '\nclass AnotherClass {\n    method() {\n        console.log("Hello");\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_class(code, 'NoSuchClass')
    assert start_line == 0 and end_line == 0, 'Expected no lines for a non-existent class'

def test_find_class_with_inheritance(typescript_finder):
    code = '\nclass ChildClass extends ParentClass {\n    method() {\n        super.method();\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_class(code, 'ChildClass')
    assert start_line == 2, f'Expected class start at line 2, got {start_line}'
    assert end_line == 6, f'Expected class end at line 6, got {end_line}'

def test_find_class_with_implements(typescript_finder):
    code = '\nclass MyClass implements MyInterface {\n    prop: string;\n    method() {\n        console.log(this.prop);\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_class(code, 'MyClass')
    assert start_line == 2, f'Expected class start at line 2, got {start_line}'
    assert end_line == 7, f'Expected class end at line 7, got {end_line}'

def test_find_exported_class(typescript_finder):
    code = '\nexport class ExportedClass {\n    constructor() {}\n}\n'
    (start_line, end_line) = typescript_finder.find_class(code, 'ExportedClass')
    assert start_line == 2, f'Expected class start at line 2, got {start_line}'
    assert end_line == 4, f'Expected class end at line 4, got {end_line}'

def test_find_abstract_class(typescript_finder):
    code = '\nabstract class AbstractClass {\n    abstract method(): void;\n}\n'
    (start_line, end_line) = typescript_finder.find_class(code, 'AbstractClass')
    assert start_line == 2, f'Expected class start at line 2, got {start_line}'
    assert end_line == 4, f'Expected class end at line 4, got {end_line}'

def test_find_class_with_generic_types(typescript_finder):
    code = '\nclass GenericClass<T> {\n    item: T;\n    constructor(item: T) {\n        this.item = item;\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_class(code, 'GenericClass')
    assert start_line == 2, f'Expected class start at line 2, got {start_line}'
    assert end_line == 7, f'Expected class end at line 7, got {end_line}'