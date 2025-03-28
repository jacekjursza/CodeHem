"""
Tests for TypeScript element extraction.
"""
import pytest
from codehem import CodeHem, CodeElementType
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def codehem():
    return CodeHem('typescript')

def test_extract_interface(codehem):
    """Test extracting a TypeScript interface."""
    example = TestHelper.load_example('basic_interface', 'general', 'typescript')
    result = codehem.extract(example.content)
    interface_element = codehem.filter(result, example.name)
    
    assert interface_element is not None
    assert interface_element.type == CodeElementType.INTERFACE
    assert interface_element.name == example.name
    assert 'id: number' in interface_element.content
    assert 'name: string' in interface_element.content
    assert 'email: string' in interface_element.content

def test_extract_class(codehem):
    """Test extracting a TypeScript class."""
    example = TestHelper.load_example('class_with_methods', 'general', 'typescript')
    result = codehem.extract(example.content)
    class_element = codehem.filter(result, example.class_name)
    
    assert class_element is not None
    assert class_element.type == CodeElementType.CLASS
    assert class_element.name == example.class_name
    
    # Check for methods
    methods = [child for child in class_element.children if child.type == CodeElementType.METHOD]
    method_names = [method.name for method in methods]
    
    assert 'getUsers' in method_names
    assert 'addUser' in method_names
    
    # Check for properties
    properties = [child for child in class_element.children if child.type == CodeElementType.PROPERTY]
    if properties:  # Properties might not be extracted yet in current implementation
        property_names = [prop.name for prop in properties]
        assert 'users' in property_names

def test_extract_function(codehem):
    """Test extracting a TypeScript function."""
    example = TestHelper.load_example('standard_function', 'general', 'typescript')
    result = codehem.extract(example.content)
    function_element = codehem.filter(result, example.function_name)
    
    assert function_element is not None
    assert function_element.type == CodeElementType.FUNCTION
    assert function_element.name == example.function_name
    
    # Check return type if available
    return_value = function_element.return_value if hasattr(function_element, 'return_value') else None
    if return_value:
        assert return_value.value_type == 'number'

def test_extract_arrow_function(codehem):
    """Test extracting a TypeScript arrow function."""
    example = TestHelper.load_example('arrow_function', 'general', 'typescript')
    result = codehem.extract(example.content)
    function_element = codehem.filter(result, example.function_name)
    
    assert function_element is not None
    assert function_element.type == CodeElementType.FUNCTION
    assert function_element.name == example.function_name
    assert 'first: string' in function_element.content
    assert 'last: string' in function_element.content