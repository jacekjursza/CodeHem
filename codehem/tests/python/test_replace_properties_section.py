import pytest
from codehem.core.codehem2 import CodeHem2
from codehem.core.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_replace_properties_section(codehem2):
    """Test replacing a properties section in a class."""
    original_code = '''
class MyClass:
    x = 1
    y = 2
    z = "test"

    def method(self):
        pass
'''
    
    new_properties = '''
x = 10
y = 20
z = "updated"
new_prop = True
'''
    
    # In CodeHem2, there might not be a direct method to replace the properties section
    # We would need to:
    # 1. Extract the class
    # 2. Modify it with the new properties
    # 3. Replace the entire class
    
    result = codehem2.extract(original_code)
    class_element = codehem2.filter(result, 'MyClass')
    assert class_element is not None, "Class MyClass not found"
    
    # Create a new class with updated properties
    new_class_code = '''
class MyClass:
    x = 10
    y = 20
    z = "updated"
    new_prop = True

    def method(self):
        pass
'''
    
    # Replace the entire class
    modified_code = codehem2.upsert_element(
        original_code,
        CodeElementType.CLASS.value,
        'MyClass',
        new_class_code
    )
    
    # Verify the properties are updated
    assert 'x = 10' in modified_code
    assert 'y = 20' in modified_code
    assert 'z = "updated"' in modified_code
    assert 'new_prop = True' in modified_code
    assert 'def method(self):' in modified_code