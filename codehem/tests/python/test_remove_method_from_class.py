import pytest
from codehem.core.codehem2 import CodeHem2
from codehem.core.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_remove_method_from_class(codehem2):
    """Test removing a method from a class."""
    original_code = '''
class MyClass:
    def method1(self):
        print("Hello")

    def method2(self):
        print("World")
'''
    
    # Extract the code to get the current structure
    result = codehem2.extract(original_code)
    
    # Check that both methods exist initially
    class_element = codehem2.filter(result, 'MyClass')
    assert class_element is not None, "Class MyClass not found"
    
    method_count = 0
    for child in class_element.children:
        if child.type == CodeElementType.METHOD:
            method_count += 1
    
    assert method_count == 2, f"Expected 2 methods initially, got {method_count}"
    
    # For CodeHem2, we don't have a direct remove_method function, but we could:
    # 1. Extract all except the method to remove
    # 2. Create a new class with only the methods we want to keep
    
    # The implementation would be something like:
    method1 = codehem2.filter(result, 'MyClass.method1')
    assert method1 is not None, "Method method1 not found"
    
    # Create a new class with just method1
    new_class_code = '''
class MyClass:
    def method1(self):
        print("Hello")
'''
    
    # Replace the entire class
    modified_code = codehem2.upsert_element(
        original_code,
        CodeElementType.CLASS.value,
        'MyClass',
        new_class_code
    )
    
    # Verify method2 is gone
    assert 'def method1(self):' in modified_code
    assert 'print("Hello")' in modified_code
    assert 'def method2(self):' not in modified_code
    assert 'print("World")' not in modified_code