import pytest
from codehem.core2.codehem2 import CodeHem2
from tests.helpers.code_examples import TestHelper
from codehem.core2.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_find_property_simple(codehem2):
    """Test finding a simple property in a class."""
    example = TestHelper.load_example('property_simple.py', category='property')
    
    # Use extract + filter instead of direct find_property
    result = codehem2.extract(example.content)
    property_element = codehem2.filter(result, f"{example.class_name}.{example.property_name}")
    
    assert property_element is not None, f"Property {example.class_name}.{example.property_name} not found"
    assert property_element.type == CodeElementType.PROPERTY_GETTER, \
        f"Expected property getter type, got {property_element.type}"
    assert property_element.range.start_line == example.expected_start_line, \
        f'Expected property start at line {example.expected_start_line}, got {property_element.range.start_line}'
    assert property_element.range.end_line == example.expected_end_line, \
        f'Expected property end at line {example.expected_end_line}, got {property_element.range.end_line}'

def test_find_property_missing(codehem2):
    """Test finding a non-existent property."""
    example = TestHelper.load_example('property_missing.py', category='property')
    
    # Use extract + filter instead of direct find_property
    result = codehem2.extract(example.content)
    property_element = codehem2.filter(result, f"{example.class_name}.{example.property_name}")
    
    assert property_element is None, "Expected None when property doesn't exist"

def test_find_property_setter(codehem2):
    """Test finding a property setter."""
    example = TestHelper.load_example('property_setter_simple.py', category='property')
    
    # Use extract to get all elements
    result = codehem2.extract(example.content)
    
    # Find class first
    class_element = codehem2.filter(result, example.class_name)
    assert class_element is not None, f"Class {example.class_name} not found"
    
    # Look for property setter among children
    setter_found = False
    for child in class_element.children:
        if child.name == example.property_name and child.type == CodeElementType.PROPERTY_SETTER:
            setter_found = True
            break
    
    assert setter_found, f"Property setter for {example.property_name} not found"