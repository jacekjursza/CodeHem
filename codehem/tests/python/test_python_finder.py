"""
Tests for Python finder functionality using the CodeHem2 API.
"""
import unittest
from ...codehem2 import CodeHem2
from ...models import CodeElementType
from ..helpers.code_examples import TestHelper

class PythonFinderTests(unittest.TestCase):
    """Tests for Python finder functionality using CodeHem2."""

    def setUp(self):
        """Set up test environment."""
        self.codehem = CodeHem2('python')
        self.sample_code = TestHelper.load_example("sample_class_with_properties").content

    def test_find_class(self):
        """Test finding a class."""
        result = self.codehem.extract(self.sample_code)
        class_element = self.codehem.filter(result, 'ExampleClass')
        self.assertIsNotNone(class_element)
        self.assertEqual(CodeElementType.CLASS, class_element.type)
        self.assertEqual('ExampleClass', class_element.name)
        self.assertIn('def __init__(self, value: int = 0):', class_element.content)
        self.assertIn('def calculate(self, multiplier: int) -> int:', class_element.content)

    def test_find_method(self):
        """Test finding a method in a class."""
        result = self.codehem.extract(self.sample_code)
        method_element = self.codehem.filter(result, 'ExampleClass.calculate')
        self.assertIsNotNone(method_element)
        self.assertEqual(CodeElementType.METHOD, method_element.type)
        self.assertEqual('calculate', method_element.name)
        self.assertEqual('ExampleClass', method_element.parent_name)
        self.assertIn('return self._value * multiplier', method_element.content)

    def test_find_property_getter(self):
        """Test finding a property getter."""
        result = self.codehem.extract(self.sample_code)
        property_element = self.codehem.filter(result, 'ExampleClass.value')
        self.assertIsNotNone(property_element)
        self.assertEqual(CodeElementType.PROPERTY_GETTER, property_element.type)
        self.assertEqual('value', property_element.name)
        self.assertEqual('ExampleClass', property_element.parent_name)
        self.assertIn('@property', property_element.content)
        self.assertIn('return self._value', property_element.content)

    def test_find_property_setter(self):
        """Test finding a property setter."""
        result = self.codehem.extract(self.sample_code)
        class_element = self.codehem.filter(result, 'ExampleClass')
        self.assertIsNotNone(class_element)
        setter_found = False
        for child in class_element.children:
            if child.name == 'value' and '@value.setter' in child.content:
                setter_found = True
                break
        self.assertTrue(setter_found, "Property setter for 'value' not found")

    def test_find_static_property(self):
        """Test finding a static property."""
        result = self.codehem.extract(self.sample_code)
        class_element = self.codehem.filter(result, 'ExampleClass')
        self.assertIsNotNone(class_element)
        static_prop = None
        for child in class_element.children:
            if child.name == 'CONSTANT':
                static_prop = child
                break
        self.assertIsNotNone(static_prop)
        self.assertEqual('CONSTANT', static_prop.name)
        self.assertTrue(hasattr(static_prop, 'is_static_property') or 
                       static_prop.type == CodeElementType.STATIC_PROPERTY)

    def test_find_function(self):
        """Test finding a standalone function."""
        result = self.codehem.extract(self.sample_code)
        function_element = self.codehem.filter(result, 'standalone_function')
        self.assertIsNotNone(function_element)
        self.assertEqual(CodeElementType.FUNCTION, function_element.type)
        self.assertEqual('standalone_function', function_element.name)
        self.assertIn('return param.upper()', function_element.content)

    def test_get_elements_by_type(self):
        """Test getting all elements of a specific type."""
        result = self.codehem.extract(self.sample_code)
        classes = [e for e in result.elements if e.type == CodeElementType.CLASS]
        self.assertTrue(len(classes) > 0)
        self.assertEqual('ExampleClass', classes[0].name)
        functions = [e for e in result.elements if e.type == CodeElementType.FUNCTION]
        self.assertTrue(len(functions) > 0)
        self.assertEqual('standalone_function', functions[0].name)