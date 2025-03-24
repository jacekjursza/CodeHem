import pytest
from codehem.core.codehem2 import CodeHem2
from codehem.core.models import CodeElementType

@pytest.fixture
def codehem2():
    return CodeHem2('python')

def test_element_type_detection(codehem2):
    """Test detecting element types from code snippets."""
    # Test class detection
    class_code = '\nclass TestClass:\n    def method(self):\n        pass\n'
    element_type = codehem2.detect_element_type(class_code)
    assert element_type == CodeElementType.CLASS.value, f"Expected CLASS, got {element_type}"
    
    # Test method detection
    method_code = '\ndef test_method(self, param):\n    return param\n'
    element_type = codehem2.detect_element_type(method_code)
    assert element_type == CodeElementType.METHOD.value, f"Expected METHOD, got {element_type}"
    
    # Test function detection
    function_code = '\ndef standalone_function(param):\n    return param\n'
    element_type = codehem2.detect_element_type(function_code)
    assert element_type == CodeElementType.FUNCTION.value, f"Expected FUNCTION, got {element_type}"
    
    # Test property getter detection
    property_code = '\n@property\ndef my_property(self):\n    return self._value\n'
    element_type = codehem2.detect_element_type(property_code)
    assert element_type == CodeElementType.PROPERTY_GETTER.value, f"Expected PROPERTY_GETTER, got {element_type}"
    
    # Test property setter detection
    setter_code = '\n@my_property.setter\ndef my_property(self, value):\n    self._value = value\n'
    element_type = codehem2.detect_element_type(setter_code)
    assert element_type == CodeElementType.PROPERTY_SETTER.value, f"Expected PROPERTY_SETTER, got {element_type}"