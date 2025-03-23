"""
Tests for element type detection functionality.
"""
import unittest
from ...codehem2 import CodeHem2
from ...models import CodeElementType
from ..helpers.code_examples import TestHelper

class ElementDetectionTests(unittest.TestCase):
    """Tests for element type detection."""

    def setUp(self):
        """Set up test environment."""
        self.codehem = CodeHem2('python')

    def test_class_detection(self):
        """Test class detection."""
        example = TestHelper.load_example("class_simple", category="class")
        element_type = self.codehem.detect_element_type(example.content)
        self.assertEqual(CodeElementType.CLASS.value, element_type)

    def test_method_detection(self):
        """Test method detection."""
        method_code = '\ndef method_name(self, param):\n    return param * 2\n'
        element_type = self.codehem.detect_element_type(method_code)
        self.assertEqual(CodeElementType.METHOD.value, element_type)

    def test_function_detection(self):
        """Test function detection."""
        example = TestHelper.load_example("function_simple", category="function")
        element_type = self.codehem.detect_element_type(example.content)
        self.assertEqual(CodeElementType.FUNCTION.value, element_type)

    def test_property_getter_detection(self):
        """Test property getter detection."""
        example = TestHelper.load_example("property_getter", category="property")
        element_type = self.codehem.detect_element_type(example.content)
        self.assertEqual(CodeElementType.PROPERTY_GETTER.value, element_type)

    def test_property_setter_detection(self):
        """Test property setter detection."""
        property_setter_code = '\n@property_name.setter\ndef property_name(self, value):\n    self._property_name = value\n'
        element_type = self.codehem.detect_element_type(property_setter_code)
        self.assertEqual(CodeElementType.PROPERTY_SETTER.value, element_type)

    def test_static_property_detection(self):
        """Test static property detection."""
        static_property_code = '\nCONSTANT = 42\n'
        element_type = self.codehem.detect_element_type(static_property_code)
        self.assertEqual(CodeElementType.STATIC_PROPERTY.value, element_type)
        
    def test_property_detection(self):
        """Test instance property detection."""
        property_code = 'self._value = value'
        element_type = self.codehem.detect_element_type(property_code)
        self.assertEqual(CodeElementType.PROPERTY.value, element_type)

    def test_import_detection(self):
        """Test import detection."""
        import_code = '\nimport os\nfrom typing import List, Dict\n'
        element_type = self.codehem.detect_element_type(import_code)
        self.assertEqual(CodeElementType.IMPORT.value, element_type)