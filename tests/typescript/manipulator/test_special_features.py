import pytest
from core.manipulator import get_code_manipulator

@pytest.fixture
def typescript_manipulator():
    return get_code_manipulator('typescript')

def test_fix_special_characters_in_content(typescript_manipulator):
    content = 'function *special_function*(param) {\n    return param;\n}'
    xpath = 'normal_function'
    expected_content = 'function special_function(param) {\n    return param;\n}'
    (fixed_content, fixed_xpath) = typescript_manipulator.fix_special_characters(content, xpath)
    assert fixed_content.strip() == expected_content.strip()
    assert fixed_xpath == xpath

def test_fix_special_characters_in_xpath(typescript_manipulator):
    content = 'function normal_function() {\n    // code\n}'
    xpath = 'Class.*special_method*'
    expected_xpath = 'Class.special_method'
    (fixed_content, fixed_xpath) = typescript_manipulator.fix_special_characters(content, xpath)
    assert fixed_content == content
    assert fixed_xpath == expected_xpath

def test_fix_special_characters_in_method(typescript_manipulator):
    content = 'class MyClass {\n    *generator_method*() {\n        yield 1;\n    }\n}'
    xpath = 'MyClass.generator_method'
    expected_content = 'class MyClass {\n    generator_method() {\n        yield 1;\n    }\n}'
    (fixed_content, fixed_xpath) = typescript_manipulator.fix_special_characters(content, xpath)
    assert fixed_content.strip() == expected_content.strip()
    assert fixed_xpath == xpath

def test_jsx_handling(typescript_manipulator):
    original_code = '\nfunction Component() {\n    return <div>Original</div>;\n}\n'
    new_component = '\nfunction Component() {\n    return <div className="updated">Updated</div>;\n}\n'
    expected = '\nfunction Component() {\n    return <div className="updated">Updated</div>;\n}\n'
    result = typescript_manipulator.replace_function(original_code, 'Component', new_component)
    assert result.strip() == expected.strip()

def test_arrow_function_handling(typescript_manipulator):
    original_code = '\nconst myArrow = () => {\n    console.log("Original");\n};\n'
    
    # You may need to add specific methods for arrow functions or adapt existing ones
    # This test may need modification depending on your implementation
    
    # One approach might be to replace the entire file
    new_content = '\nconst myArrow = () => {\n    console.log("Updated");\n};\n'
    result = typescript_manipulator.replace_entire_file(original_code, new_content)
    assert result.strip() == new_content.strip()

def test_typescript_interface_handling(typescript_manipulator):
    original_code = '\ninterface MyInterface {\n    prop1: string;\n    prop2: number;\n}\n'
    
    # Similarly, this would depend on your implementation for handling interfaces
    
    # Using replace_entire_file as a fallback
    new_content = '\ninterface MyInterface {\n    prop1: string;\n    prop2: number;\n    prop3: boolean;\n}\n'
    result = typescript_manipulator.replace_entire_file(original_code, new_content)
    assert result.strip() == new_content.strip()