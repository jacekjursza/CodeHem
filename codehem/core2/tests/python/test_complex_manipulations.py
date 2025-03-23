import pytest
from codehem.core2.codehem2 import CodeHem2
from codehem.core2.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_method_to_standalone_function(codehem2):
    """Test converting a method to a standalone function."""
    original_code = '''
class MyClass:
    def method(self, param):
        return f"Result: {param}"
'''
    
    # Extract method from class
    result = codehem2.extract(original_code)
    method = codehem2.filter(result, 'MyClass.method')
    assert method is not None
    
    # Convert method to function (remove self parameter)
    function_content = method.content.replace('def method(self, param)', 'def standalone_method(param)')
    
    # Add function to code
    modified_code = codehem2.upsert_element(
        original_code, 
        CodeElementType.FUNCTION.value, 
        'standalone_method', 
        function_content
    )
    
    # Verify the result
    assert 'class MyClass:' in modified_code
    assert 'def method(self, param):' in modified_code
    assert 'def standalone_method(param):' in modified_code
    assert 'return f"Result: {param}"' in modified_code
    
    # Extract and check the new structure
    new_result = codehem2.extract(modified_code)
    function_element = codehem2.filter(new_result, 'standalone_method')
    assert function_element is not None
    assert function_element.type == CodeElementType.FUNCTION