import pytest
from codehem.core.codehem2 import CodeHem2
from codehem.core.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_replace_method_simple(codehem2):
    """Test replacing a simple method in a class."""
    original_code = '\nclass MyClass:\n    def my_method(self):\n        print("Hello")\n'
    new_method = '\ndef my_method(self):\n    print("Hello, World!")\n'
    
    # Use upsert_element instead of replace_method
    result = codehem2.upsert_element(
        original_code, 
        CodeElementType.METHOD.value, 
        'my_method', 
        new_method, 
        'MyClass'
    )
    
    assert 'def my_method(self):' in result
    assert 'print("Hello, World!")' in result
    assert 'class MyClass:' in result

def test_add_method_to_class(codehem2):
    """Test adding a new method to a class."""
    original_code = '\nclass MyClass:\n    def existing_method(self):\n        print("Hello")\n'
    new_method = '\ndef new_method(self):\n    print("New Method")\n'
    
    # Use upsert_element to add a method
    result = codehem2.upsert_element(
        original_code, 
        CodeElementType.METHOD.value, 
        'new_method', 
        new_method, 
        'MyClass'
    )
    
    assert 'def existing_method(self):' in result
    assert 'def new_method(self):' in result
    assert 'print("New Method")' in result
    assert 'class MyClass:' in result

def test_replace_method_with_decorator(codehem2):
    """Test replacing a method that has a decorator."""
    original_code = '\nclass MyClass:\n    @decorator\n    def my_method(self):\n        print("Hello")\n'
    new_method = '\n@new_decorator\ndef my_method(self):\n    print("Hello, World!")\n'
    
    # Use upsert_element instead of replace_method
    result = codehem2.upsert_element(
        original_code, 
        CodeElementType.METHOD.value, 
        'my_method', 
        new_method, 
        'MyClass'
    )
    
    assert '@new_decorator' in result
    assert 'def my_method(self):' in result
    assert 'print("Hello, World!")' in result
    assert 'class MyClass:' in result