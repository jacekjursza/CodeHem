import pytest
from codehem.core.codehem2 import CodeHem2
from tests.helpers.code_examples import TestHelper
from codehem.core.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_find_property_setter_before_getter(codehem2):
    """Test finding a property when the setter is defined before the getter."""
    example = TestHelper.load_example('property_setter_before_getter.py', category='property')
    
    # Use extract + filter instead of direct find_property
    result = codehem2.extract(example.content)
    
    # Get the class first
    class_element = codehem2.filter(result, example.class_name)
    assert class_element is not None, f"Class {example.class_name} not found"
    
    # Find property getter and setter
    getter = None
    setter = None
    for child in class_element.children:
        if child.name == example.property_name:
            if child.type == CodeElementType.PROPERTY_GETTER:
                getter = child
            elif child.type == CodeElementType.PROPERTY_SETTER:
                setter = child
    
    assert getter is not None, f"Property getter for {example.property_name} not found"
    assert setter is not None, f"Property setter for {example.property_name} not found"
    
    # Verify the element can be accessed through the xpath
    property_element = codehem2.filter(result, f"{example.class_name}.{example.property_name}")
    assert property_element is not None, f"Property {example.class_name}.{example.property_name} not found via xpath"

def test_find_property_among_other_decorators(codehem2):
    """Test finding a property that has multiple decorators."""
    example = TestHelper.load_example('property_among_other_decorators.py', category='property')
    
    # Use extract + filter
    result = codehem2.extract(example.content)
    property_element = codehem2.filter(result, f"{example.class_name}.{example.property_name}")
    
    assert property_element is not None, f"Property {example.class_name}.{example.property_name} not found"
    assert property_element.type == CodeElementType.PROPERTY_GETTER, f"Expected property getter type, got {property_element.type}"
    assert property_element.range.start_line <= example.expected_start_line, \
        f'Expected property start at line {example.expected_start_line} or before, got {property_element.range.start_line}'
    assert property_element.range.end_line >= example.expected_end_line, \
        f'Expected property end at line {example.expected_end_line} or after, got {property_element.range.end_line}'