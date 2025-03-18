import pytest
from manipulator.factory import get_code_manipulator

@pytest.fixture
def typescript_manipulator():
    return get_code_manipulator('typescript')

def test_replace_property_simple(typescript_manipulator):
    original_code = '\nclass MyClass {\n    myProperty = "original value";\n}\n'
    new_property = 'myProperty = "new value";'
    expected = '\nclass MyClass {\n    myProperty = "new value";\n}\n'
    result = typescript_manipulator.replace_property(original_code, 'MyClass', 'myProperty', new_property)
    assert result.strip() == expected.strip()

def test_replace_property_with_type(typescript_manipulator):
    original_code = '\nclass MyClass {\n    myProperty: string = "original";\n}\n'
    new_property = 'myProperty: string | null = null;'
    expected = '\nclass MyClass {\n    myProperty: string | null = null;\n}\n'
    result = typescript_manipulator.replace_property(original_code, 'MyClass', 'myProperty', new_property)
    assert result.strip() == expected.strip()

def test_replace_property_with_modifier(typescript_manipulator):
    original_code = '\nclass MyClass {\n    private myProperty = "private";\n}\n'
    new_property = 'public myProperty = "public now";'
    expected = '\nclass MyClass {\n    public myProperty = "public now";\n}\n'
    result = typescript_manipulator.replace_property(original_code, 'MyClass', 'myProperty', new_property)
    assert result.strip() == expected.strip()

def test_replace_property_missing(typescript_manipulator):
    original_code = '\nclass MyClass {\n    existingProperty = true;\n}\n'
    new_property = 'missingProperty = "won\'t be added";'
    result = typescript_manipulator.replace_property(original_code, 'MyClass', 'missingProperty', new_property)
    assert result.strip() == original_code.strip()

def test_replace_property_static(typescript_manipulator):
    original_code = '\nclass MyClass {\n    static VERSION = "1.0.0";\n}\n'
    new_property = 'static VERSION = "2.0.0";'
    expected = '\nclass MyClass {\n    static VERSION = "2.0.0";\n}\n'
    result = typescript_manipulator.replace_property(original_code, 'MyClass', 'VERSION', new_property)
    assert result.strip() == expected.strip()

def test_replace_property_readonly(typescript_manipulator):
    original_code = '\nclass MyClass {\n    readonly ID = "original-id";\n}\n'
    new_property = 'readonly ID = "new-id";'
    expected = '\nclass MyClass {\n    readonly ID = "new-id";\n}\n'
    result = typescript_manipulator.replace_property(original_code, 'MyClass', 'ID', new_property)
    assert result.strip() == expected.strip()