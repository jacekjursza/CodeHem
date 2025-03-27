"""
Integration tests for CodeHem2 main class.
"""
import unittest
import os
import tempfile

from codehem import CodeHem, CodeElementType
from ..helpers.code_examples import TestHelper

class CodeHem2Tests(unittest.TestCase):
    """Integration tests for CodeHem2."""

    def setUp(self):
        """Set up test environment."""
        self.codehem = CodeHem('python')
        self.sample_code = TestHelper.load_example('sample_class_with_properties', 'general').content

    def test_detect_element_type(self):
        """Test element type detection."""
        class_code = TestHelper.load_example('simple_class', 'general').content
        element_type = self.codehem.detect_element_type(class_code)
        self.assertEqual(CodeElementType.CLASS.value, element_type)
        
        method_code = TestHelper.load_example('simple_method', 'general').content
        element_type = self.codehem.detect_element_type(method_code)
        self.assertEqual(CodeElementType.METHOD.value, element_type)

    def test_extract(self):
        """Test extracting code elements."""
        result = self.codehem.extract(self.sample_code)
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, 'elements'))
        self.assertTrue(len(result.elements) > 0)
        class_found = False
        for element in result.elements:
            if element.type == CodeElementType.CLASS and element.name == 'ExampleClass':
                class_found = True
                self.assertTrue(len(element.children) > 0)
                break
        self.assertTrue(class_found)
        function_found = False
        for element in result.elements:
            if element.type == CodeElementType.FUNCTION and element.name == 'standalone_function':
                function_found = True
                break
        self.assertTrue(function_found)

    def test_upsert_element(self):
        """Test adding/replacing an element."""
        new_method = TestHelper.load_example('new_method', 'general').content
        modified_code = self.codehem.upsert_element(self.sample_code, CodeElementType.METHOD.value, 'new_method', new_method, 'ExampleClass')
        self.assertIsNotNone(modified_code)
        self.assertIn('def new_method(self, param: str) -> str:', modified_code)
        self.assertIn('return f"Method called with {param}"', modified_code)

    def test_upsert_element_by_xpath(self):
        """Test adding/replacing an element using XPath."""
        new_calculate = TestHelper.load_example('new_calculate_method', 'general').content
        modified_code = self.codehem.upsert_element_by_xpath(self.sample_code, 'ExampleClass.calculate', new_calculate)
        self.assertIsNotNone(modified_code)
        self.assertIn('def calculate(self, multiplier: int, offset: int = 0) -> int:', modified_code)
        self.assertIn('return self._value * multiplier + offset', modified_code)

    def test_filter(self):
        """Test filtering code elements."""
        result = self.codehem.extract(self.sample_code)
        element = self.codehem.filter(result, 'ExampleClass')
        self.assertIsNotNone(element)
        self.assertEqual(CodeElementType.CLASS, element.type)
        self.assertEqual('ExampleClass', element.name)
        element = self.codehem.filter(result, 'ExampleClass.calculate')
        self.assertIsNotNone(element)
        self.assertEqual(CodeElementType.METHOD, element.type)
        self.assertEqual('calculate', element.name)
        self.assertEqual('ExampleClass', element.parent_name)
        element = self.codehem.filter(result, 'standalone_function')
        self.assertIsNotNone(element)
        self.assertEqual(CodeElementType.FUNCTION, element.type)
        self.assertEqual('standalone_function', element.name)

    def test_file_operations(self):
        """Test file operations."""
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(self.sample_code.encode())
        try:
            code = CodeHem.load_file(temp_file.name)
            self.assertEqual(self.sample_code, code)
            codehem = CodeHem.from_file_path(temp_file.name)
            self.assertEqual('python', codehem.language_service.language_code)
            result = codehem.extract(code)
            self.assertTrue(len(result.elements) > 0)
        finally:
            os.unlink(temp_file.name)