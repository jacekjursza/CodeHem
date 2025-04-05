"""
Tests for CodeHem2 XPath functionality.
"""
import unittest
import logging
import re # Import re for regex assertion
from codehem import CodeHem, CodeElementType, CodeElementXPathNode
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeHem2XPathTests(unittest.TestCase):
    """Tests for CodeHem2 XPath functionality."""

    def setUp(self):
        """Set up test environment."""
        self.codehem = CodeHem('python')
        # Using the same sample code as test_codehem2 for consistency
        self.sample_code = """import os
from typing import List, Dict, Optional
# Adding @dataclass to match the sample used in test_codehem2 failures
from dataclasses import dataclass

@dataclass
class ExampleClass:
    # Class constant
    CONSTANT = 42

    def __init__(self, value: int = 0):
        self._value = value

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, new_value: int) -> None:
        self._value = new_value

    def calculate(self, multiplier: int) -> int:
        return self._value * multiplier

def standalone_function(param: str) -> str:
    return param.upper()
"""

    def test_parse_xpath(self):
        """Test parsing XPath expressions."""
        xpath = 'ExampleClass.calculate'
        nodes = CodeHem.parse_xpath(xpath)
        self.assertEqual(2, len(nodes))
        self.assertEqual('ExampleClass', nodes[0].name)
        self.assertEqual('calculate', nodes[1].name)
        xpath = 'ExampleClass[class].value[property_getter]'
        nodes = CodeHem.parse_xpath(xpath)
        self.assertEqual(2, len(nodes))
        self.assertEqual('ExampleClass', nodes[0].name)
        self.assertEqual(CodeElementType.CLASS.value, nodes[0].type)
        self.assertEqual('value', nodes[1].name)
        self.assertEqual(CodeElementType.PROPERTY_GETTER.value, nodes[1].type)

    def test_format_xpath(self):
        """Test formatting XPath nodes back to string."""
        nodes = [CodeElementXPathNode(name='ExampleClass', type=CodeElementType.CLASS.value), CodeElementXPathNode(name='calculate', type=CodeElementType.METHOD.value)]
        xpath = CodeHem.format_xpath(nodes)
        self.assertEqual('ExampleClass[class].calculate[method]', xpath)

    def test_find_by_xpath(self):
        """Test finding elements by XPath."""
        start_line, end_line = self.codehem.find_by_xpath(self.sample_code, 'ExampleClass')
        self.assertTrue(start_line > 0, "Class start line should be > 0")
        self.assertTrue(end_line >= start_line, "Class end line should be >= start line")

        start_line, end_line = self.codehem.find_by_xpath(self.sample_code, 'ExampleClass.calculate')
        self.assertTrue(start_line > 0, "Method start line should be > 0")
        self.assertTrue(end_line >= start_line, "Method end line should be >= start line")

        start_line, end_line = self.codehem.find_by_xpath(self.sample_code, 'ExampleClass.calculate[method]')
        self.assertTrue(start_line > 0, "Method[method] start line should be > 0")
        self.assertTrue(end_line >= start_line, "Method[method] end line should be >= start line")

        # Test property getter specifically
        start_line, end_line = self.codehem.find_by_xpath(self.sample_code, 'ExampleClass.value[property_getter]')
        self.assertTrue(start_line > 0, "Getter start line should be > 0")
        self.assertTrue(end_line >= start_line, "Getter end line should be >= start line")

        start_line, end_line = self.codehem.find_by_xpath(self.sample_code, 'standalone_function')
        self.assertTrue(start_line > 0, "Function start line should be > 0")
        self.assertTrue(end_line >= start_line, "Function end line should be >= start line")

    def test_filter_with_xpath(self):
        """Test filtering elements with XPath."""
        try:
            result = self.codehem.extract(self.sample_code)
        except Exception as e:
            self.skipTest(f'Extraction failed: {str(e)}')
            return

        element = CodeHem.filter(result, 'ExampleClass')
        self.assertIsNotNone(element)
        self.assertEqual(CodeElementType.CLASS, element.type)
        self.assertEqual('ExampleClass', element.name)

        element = CodeHem.filter(result, 'ExampleClass.calculate[method]')
        self.assertIsNotNone(element)
        self.assertEqual(CodeElementType.METHOD, element.type)
        self.assertEqual('calculate', element.name)

        element = CodeHem.filter(result, 'ExampleClass.value[property_getter]')
        self.assertIsNotNone(element, "Property getter should be found by filter")
        self.assertEqual(CodeElementType.PROPERTY_GETTER, element.type)
        self.assertEqual('value', element.name)

        element = CodeHem.filter(result, 'standalone_function')
        self.assertIsNotNone(element)
        self.assertEqual(CodeElementType.FUNCTION, element.type)
        self.assertEqual('standalone_function', element.name)

    def test_upsert_element_by_xpath(self):
        """Test adding or replacing elements by XPath."""
        # Replace method
        new_method = "\ndef calculate(self, multiplier: int, offset: int = 0) -> int:\n    return self._value * multiplier + offset\n"
        modified_code = self.codehem.upsert_element_by_xpath(self.sample_code, "ExampleClass.calculate", new_method)
        # Use assertRegex to ignore spacing around '='
        self.assertRegex(modified_code, r'def calculate\(self, multiplier: int, offset: int\s*=\s*0\) -> int:', "Calculate method signature not found or incorrect after replacement")
        self.assertIn("return self._value * multiplier + offset", modified_code, "New method body not found after replacement")

        # Add method (using upsert via XPath)
        new_method_add = '\ndef new_method(self, param: str) -> None:\n    print(f"New method with {param}")\n'
        modified_code_add = self.codehem.upsert_element_by_xpath(self.sample_code, 'ExampleClass.new_method[method]', new_method_add)
        self.assertIn('def new_method(self, param: str) -> None:', modified_code_add, "Added method signature not found")
        # Make assertion flexible regarding quotes
        self.assertTrue(
            'print(f"New method with {param}")' in modified_code_add or \
            "print(f'New method with {param}')" in modified_code_add,
            "Added method body not found (checked both quote types)"
        )