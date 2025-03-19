import pytest
from core.finder import get_code_finder

@pytest.fixture
def typescript_finder():
    return get_code_finder('typescript')

def test_find_property_simple(typescript_finder):
    code = '\nclass MyClass {\n    myProperty = "value";\n\n    method() {\n        console.log(this.myProperty);\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_property(code, 'MyClass', 'myProperty')
    assert start_line == 3, f'Expected property start at line 3, got {start_line}'
    assert end_line == 3, f'Expected property end at line 3, got {end_line}'

def test_find_property_with_type(typescript_finder):
    code = '\nclass MyClass {\n    myProperty: string = "value";\n}\n'
    (start_line, end_line) = typescript_finder.find_property(code, 'MyClass', 'myProperty')
    assert start_line == 3, f'Expected property start at line 3, got {start_line}'
    assert end_line == 3, f'Expected property end at line 3, got {end_line}'

def test_find_property_with_access_modifiers(typescript_finder):
    code = '\nclass MyClass {\n    private privateProperty = "private";\n    public publicProperty = "public";\n    protected protectedProperty = "protected";\n}\n'
    
    (start_line, end_line) = typescript_finder.find_property(code, 'MyClass', 'privateProperty')
    assert start_line == 3, f'Expected private property start at line 3, got {start_line}'
    assert end_line == 3, f'Expected private property end at line 3, got {end_line}'
    
    (start_line, end_line) = typescript_finder.find_property(code, 'MyClass', 'publicProperty')
    assert start_line == 4, f'Expected public property start at line 4, got {start_line}'
    assert end_line == 4, f'Expected public property end at line 4, got {end_line}'
    
    (start_line, end_line) = typescript_finder.find_property(code, 'MyClass', 'protectedProperty')
    assert start_line == 5, f'Expected protected property start at line 5, got {start_line}'
    assert end_line == 5, f'Expected protected property end at line 5, got {end_line}'

def test_find_property_missing(typescript_finder):
    code = '\nclass MyClass {\n    existingProperty = "exists";\n}\n'
    (start_line, end_line) = typescript_finder.find_property(code, 'MyClass', 'missingProperty')
    assert start_line == 0 and end_line == 0, "Expected no lines when property doesn't exist"

def test_find_static_property(typescript_finder):
    code = '\nclass MyClass {\n    static staticProperty = "static value";\n}\n'
    (start_line, end_line) = typescript_finder.find_property(code, 'MyClass', 'staticProperty')
    assert start_line == 3, f'Expected static property start at line 3, got {start_line}'
    assert end_line == 3, f'Expected static property end at line 3, got {end_line}'

def test_find_readonly_property(typescript_finder):
    code = '\nclass MyClass {\n    readonly readonlyProperty: string = "readonly";\n}\n'
    (start_line, end_line) = typescript_finder.find_property(code, 'MyClass', 'readonlyProperty')
    assert start_line == 3, f'Expected readonly property start at line 3, got {start_line}'
    assert end_line == 3, f'Expected readonly property end at line 3, got {end_line}'