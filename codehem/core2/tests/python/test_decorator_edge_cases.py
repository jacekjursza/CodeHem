import pytest
from codehem.core2.codehem2 import CodeHem2
from codehem.core2.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_parameterized_decorators(codehem2):
    """Test handling functions with parameterized decorators."""
    original_code = '''
@decorator_with_args("arg1", "arg2", keyword=True)
def decorated_function(x, y):
    return x + y
'''
    
    # Extract the function
    result = codehem2.extract(original_code)
    function = codehem2.filter(result, 'decorated_function')
    
    assert function is not None, "Function decorated_function not found"
    assert function.type == CodeElementType.FUNCTION
    assert '@decorator_with_args(' in function.content
    
    # Replace with new function with different decorator params
    new_function = '''
@decorator_with_args("new_arg1", "new_arg2", keyword=False, extra=123)
def decorated_function(x, y, z=0):
    return x + y + z
'''
    
    modified_code = codehem2.upsert_element(
        original_code,
        CodeElementType.FUNCTION.value,
        'decorated_function',
        new_function
    )
    
    assert '@decorator_with_args("new_arg1", "new_arg2", keyword=False, extra=123)' in modified_code
    assert 'def decorated_function(x, y, z=0):' in modified_code
    assert 'return x + y + z' in modified_code

def test_multiple_stacked_decorators(codehem2):
    """Test handling functions with multiple stacked decorators."""
    original_code = '''
@decorator1
@decorator2
@decorator3
def decorated_function(x):
    return x * 2
'''
    
    # Extract the function
    result = codehem2.extract(original_code)
    function = codehem2.filter(result, 'decorated_function')
    
    assert function is not None, "Function decorated_function not found"
    assert function.type == CodeElementType.FUNCTION
    
    # Replace with new function with different decorators
    new_function = '''
@decorator1
@new_decorator
@decorator3
def decorated_function(x, y=1):
    return x * y
'''
    
    modified_code = codehem2.upsert_element(
        original_code,
        CodeElementType.FUNCTION.value,
        'decorated_function',
        new_function
    )
    
    assert '@decorator1' in modified_code
    assert '@new_decorator' in modified_code
    assert '@decorator3' in modified_code
    assert '@decorator2' not in modified_code
    assert 'def decorated_function(x, y=1):' in modified_code
    assert 'return x * y' in modified_code