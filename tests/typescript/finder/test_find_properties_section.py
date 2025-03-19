import pytest
from core.finder import get_code_finder

@pytest.fixture
def typescript_finder():
    return get_code_finder('typescript')

def test_find_properties_section_simple(typescript_finder):
    code = '\nclass MyClass {\n    x = 1;\n    y = 2;\n    z = "test";\n    \n    method() {\n        console.log(this.x, this.y, this.z);\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_properties_section(code, 'MyClass')
    assert start_line == 3, f'Expected properties section start at line 3, got {start_line}'
    assert end_line == 5, f'Expected properties section end at line 5, got {end_line}'

def test_find_properties_section_none(typescript_finder):
    code = '\nclass MyClass {\n    method() {\n        console.log("No properties");\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_properties_section(code, 'MyClass')
    assert start_line == 0 and end_line == 0, 'Expected no properties section when no properties'

def test_find_properties_section_with_types(typescript_finder):
    code = '\nclass MyClass {\n    x: number = 1;\n    y: number = 2;\n    z: string = "test";\n    \n    method() {\n        console.log(this.x, this.y, this.z);\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_properties_section(code, 'MyClass')
    assert start_line == 3, f'Expected properties section start at line 3, got {start_line}'
    assert end_line == 5, f'Expected properties section end at line 5, got {end_line}'

def test_find_properties_section_with_modifiers(typescript_finder):
    code = '\nclass MyClass {\n    private x: number = 1;\n    public y: number = 2;\n    protected z: string = "test";\n    \n    method() {\n        console.log(this.x, this.y, this.z);\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_properties_section(code, 'MyClass')
    assert start_line == 3, f'Expected properties section start at line 3, got {start_line}'
    assert end_line == 5, f'Expected properties section end at line 5, got {end_line}'

def test_find_properties_section_with_static(typescript_finder):
    code = '\nclass MyClass {\n    static readonly VERSION = "1.0.0";\n    private static instance: MyClass;\n    \n    getInstance(): MyClass {\n        return MyClass.instance;\n    }\n}\n'
    (start_line, end_line) = typescript_finder.find_properties_section(code, 'MyClass')
    assert start_line == 3, f'Expected properties section start at line 3, got {start_line}'
    assert end_line == 4, f'Expected properties section end at line 4, got {end_line}'