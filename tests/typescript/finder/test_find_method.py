import pytest
from core.finder import get_code_finder

@pytest.fixture
def typescript_finder():
    return get_code_finder('typescript')

def test_find_method_simple(typescript_finder):
    code = '\nclass MyClass {\n    myMethod() {\n        return 42;\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_method(code, 'MyClass', 'myMethod')
    assert start_line == 3, f'Expected method start at line 3, got {start_line}'
    assert end_line == 5, f'Expected method end at line 5, got {end_line}'

def test_find_method_missing(typescript_finder):
    code = '\nclass MyClass {\n    anotherMethod() {\n        return 42;\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_method(code, 'MyClass', 'myMethod')
    assert start_line == 0 and end_line == 0, 'Expected no lines for a non-existent method'

def test_find_method_with_modifiers(typescript_finder):
    code = '\nclass MyClass {\n    private myPrivateMethod() {\n        return "private";\n    }\n\n    public myPublicMethod() {\n        return "public";\n    }\n\n    protected myProtectedMethod() {\n        return "protected";\n    }\n}\n'
    
    (start_line, end_line) = typescript_finder.find_method(code, 'MyClass', 'myPrivateMethod')
    assert start_line == 3, f'Expected private method start at line 3, got {start_line}'
    assert end_line == 5, f'Expected private method end at line 5, got {end_line}'
    
    (start_line, end_line) = typescript_finder.find_method(code, 'MyClass', 'myPublicMethod')
    assert start_line == 7, f'Expected public method start at line 7, got {start_line}'
    assert end_line == 9, f'Expected public method end at line 9, got {end_line}'
    
    (start_line, end_line) = typescript_finder.find_method(code, 'MyClass', 'myProtectedMethod')
    assert start_line == 11, f'Expected protected method start at line 11, got {start_line}'
    assert end_line == 13, f'Expected protected method end at line 13, got {end_line}'

def test_find_static_method(typescript_finder):
    code = '\nclass MyClass {\n    static staticMethod() {\n        return "static";\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_method(code, 'MyClass', 'staticMethod')
    assert start_line == 3, f'Expected static method start at line 3, got {start_line}'
    assert end_line == 5, f'Expected static method end at line 5, got {end_line}'

def test_find_async_method(typescript_finder):
    code = '\nclass MyClass {\n    async asyncMethod() {\n        return await Promise.resolve("async");\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_method(code, 'MyClass', 'asyncMethod')
    assert start_line == 3, f'Expected async method start at line 3, got {start_line}'
    assert end_line == 5, f'Expected async method end at line 5, got {end_line}'

def test_find_getter_setter(typescript_finder):
    code = '\nclass MyClass {\n    private _value: string;\n\n    get value() {\n        return this._value;\n    }\n\n    set value(val: string) {\n        this._value = val;\n    }\n}\n'
    
    (start_line, end_line) = typescript_finder.find_method(code, 'MyClass', 'value')
    assert start_line in [5, 9], f'Expected getter or setter method to be found'