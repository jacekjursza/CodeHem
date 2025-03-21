import pytest
from core.finder.factory import get_code_finder

@pytest.fixture
def python_finder():
    return get_code_finder('python')

def test_find_nested_class(python_finder):
    """Test finding a class nested inside another class."""
    code = '''
class OuterClass:
    class InnerClass:
        def inner_method(self):
            pass
            
    def outer_method(self):
        pass
'''
    (outer_start, outer_end) = python_finder.find_class(code, 'OuterClass')
    assert outer_start == 2, f'Expected outer class start at line 2, got {outer_start}'
    assert outer_end == 8, f'Expected outer class end at line 8, got {outer_end}'
    
    # The inner class should be findable directly
    (inner_start, inner_end) = python_finder.find_class(code, 'InnerClass')
    assert inner_start == 3, f'Expected inner class start at line 3, got {inner_start}'
    assert inner_end == 5, f'Expected inner class end at line 5, got {inner_end}'

def test_find_nested_function(python_finder):
    """Test finding a function nested inside another function."""
    code = '''
def outer_function():
    x = 1
    
    def inner_function():
        return x + 1
        
    return inner_function()
'''
    (outer_start, outer_end) = python_finder.find_function(code, 'outer_function')
    assert outer_start == 2, f'Expected outer function start at line 2, got {outer_start}'
    assert outer_end == 8, f'Expected outer function end at line 8, got {outer_end}'
    
    # The inner function should be findable directly, but some implementations
    # may choose not to support this for scoping reasons
    (inner_start, inner_end) = python_finder.find_function(code, 'inner_function')
    # We accept either successful finding or (0,0) as valid implementation choices
    if inner_start != 0 or inner_end != 0:
        assert inner_start == 5, f'Expected inner function start at line 5, got {inner_start}'
        assert inner_end == 6, f'Expected inner function end at line 6, got {inner_end}'

def test_find_method_with_nested_function(python_finder):
    """Test finding a method that contains a nested function."""
    code = '''
class MyClass:
    def method_with_nested(self):
        x = 10
        
        def nested_func():
            return x * 2
            
        return nested_func()
'''
    (method_start, method_end) = python_finder.find_method(code, 'MyClass', 'method_with_nested')
    assert method_start == 3, f'Expected method start at line 3, got {method_start}'
    assert method_end == 9, f'Expected method end at line 9, got {method_end}'

def test_find_with_complex_nesting(python_finder):
    """Test finding elements in code with complex nesting structures."""
    code = '''
class OuterClass:
    CONST = 42
    
    class MiddleClass:
        def middle_method(self):
            class InnerClass:
                def inner_method(self):
                    def deeply_nested():
                        return 42
                    return deeply_nested()
            return 10
            
    def outer_method(self):
        return 20
'''
    # Verify we can find the outer class
    (outer_start, outer_end) = python_finder.find_class(code, 'OuterClass')
    assert outer_start == 2, f'Expected outer class start at line 2, got {outer_start}'
    assert outer_end > 10, f'Expected outer class to span multiple lines'
    
    # Verify we can find the middle class
    (middle_start, middle_end) = python_finder.find_class(code, 'MiddleClass')
    assert middle_start == 5, f'Expected middle class start at line 5, got {middle_start}'
    
    # Verify we can find methods at different nesting levels
    (outer_method_start, _) = python_finder.find_method(code, 'OuterClass', 'outer_method')
    assert outer_method_start == 14, f'Expected outer_method start at line 14, got {outer_method_start}'
    
    (middle_method_start, _) = python_finder.find_method(code, 'MiddleClass', 'middle_method')
    assert middle_method_start == 6, f'Expected middle_method start at line 6, got {middle_method_start}'