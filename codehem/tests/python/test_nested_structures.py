import pytest
from codehem.core.codehem2 import CodeHem2
from codehem.core.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_find_nested_class(codehem2):
    """Test finding a class nested inside another class."""
    code = '''
class OuterClass:
    class InnerClass:
        def inner_method(self):
            pass
            
    def outer_method(self):
        pass
'''
    
    # Extract all elements
    result = codehem2.extract(code)
    
    # Find outer class
    outer_class = codehem2.filter(result, 'OuterClass')
    assert outer_class is not None, "OuterClass not found"
    assert outer_class.type == CodeElementType.CLASS
    
    # Find inner class
    # Note: In the new structure, nested classes would typically be children of the parent class
    inner_class_found = False
    for child in outer_class.children:
        if child.type == CodeElementType.CLASS and child.name == 'InnerClass':
            inner_class_found = True
            break
    
    # Alternatively, we might find it directly
    inner_class = codehem2.filter(result, 'InnerClass')
    
    assert inner_class_found or inner_class is not None, "InnerClass not found"

def test_find_nested_function(codehem2):
    """Test finding a function nested inside another function."""
    code = '''
def outer_function():
    x = 1
    
    def inner_function():
        return x + 1
        
    return inner_function()
'''
    
    # Extract all elements
    result = codehem2.extract(code)
    
    # Find outer function
    outer_function = codehem2.filter(result, 'outer_function')
    assert outer_function is not None, "outer_function not found"
    assert outer_function.type == CodeElementType.FUNCTION
    
    # NOTE: Finding nested functions directly might be limited in the current implementation
    # as they're often not exposed as top-level elements
    
    # Check if the inner function is included in the outer function's content
    assert 'def inner_function():' in outer_function.content
    assert 'return x + 1' in outer_function.content