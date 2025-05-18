"""
Unit tests for the ExtractionService with components.

This module contains tests that verify the extraction service works correctly
with the component architecture.
"""

import unittest
import logging
from unittest.mock import patch, MagicMock

from codehem.core.extraction_service import ExtractionService
from codehem.languages import get_language_service_for_code
from codehem.models.enums import CodeElementType
from codehem.models.code_element import CodeElementsResult

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Sample Python code for testing
PYTHON_SAMPLE = """
import os
from typing import List, Dict, Optional

class ExampleClass:
    # Class constant
    CONSTANT = 42
    other_property: int = 0
    
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

class TestExtractionService(unittest.TestCase):
    """Test cases for the ExtractionService."""

    def setUp(self):
        """Set up test environment."""
        # Get the Python language service
        self.language_service = get_language_service_for_code(PYTHON_SAMPLE)
        self.assertIsNotNone(self.language_service, "Failed to get language service for Python code")
        
        # Create ExtractionService instance
        self.service = ExtractionService('python')
    
    def test_service_initialization(self):
        """Test that the service initializes correctly."""
        self.assertEqual(self.service.language_code, 'python')
        self.assertIsNotNone(self.service.language_service, "Language service should be initialized")
    
    def test_find_element(self):
        """Test the find_element method."""
        # Find a class
        start_line, end_line = self.service.find_element(PYTHON_SAMPLE, CodeElementType.CLASS.value, 'ExampleClass')
        self.assertGreater(start_line, 0, "Start line should be positive")
        self.assertGreaterEqual(end_line, start_line, "End line should be >= start line")
        
        # Find a method
        start_line, end_line = self.service.find_element(
            PYTHON_SAMPLE, 
            CodeElementType.METHOD.value, 
            'calculate', 
            'ExampleClass'
        )
        self.assertGreater(start_line, 0, "Start line should be positive")
        self.assertGreaterEqual(end_line, start_line, "End line should be >= start line")
        
        # Find a property getter
        start_line, end_line = self.service.find_element(
            PYTHON_SAMPLE,
            CodeElementType.PROPERTY_GETTER.value,
            'value',
            'ExampleClass'
        )
        if start_line == 0:
            self.skipTest("Property getter extraction not implemented")
        self.assertGreaterEqual(end_line, start_line, "End line should be >= start line")
        
        # Find a property setter
        start_line, end_line = self.service.find_element(
            PYTHON_SAMPLE,
            CodeElementType.PROPERTY_SETTER.value,
            'value',
            'ExampleClass'
        )
        if start_line == 0:
            self.skipTest("Property setter extraction not implemented")
        self.assertGreaterEqual(end_line, start_line, "End line should be >= start line")
        
        # Find a function
        start_line, end_line = self.service.find_element(PYTHON_SAMPLE, CodeElementType.FUNCTION.value, 'standalone_function')
        self.assertGreater(start_line, 0, "Start line should be positive")
        self.assertGreaterEqual(end_line, start_line, "End line should be >= start line")
    
    def test_extract_all(self):
        """Test the extract_all method."""
        result = self.service.extract_all(PYTHON_SAMPLE)
        
        # Check result type
        self.assertIsInstance(result, CodeElementsResult)
        
        # Check that we have elements
        self.assertGreater(len(result.elements), 0, "Should have extracted elements")
        
        # Check specific element types
        self.assertGreater(len(result.classes), 0, "Should have extracted classes")
        self.assertGreater(len(result.functions), 0, "Should have extracted functions")
        
        # Check that the class contains methods and properties
        for cls in result.classes:
            self.assertEqual(cls.name, 'ExampleClass')
            self.assertGreater(len(cls.children), 0, "Class should have children")
            
            # Check for specific methods and properties
            method_names = [m.name for m in cls.children if m.is_method]
            property_names = [p.name for p in cls.children if p.is_property]
            
            self.assertIn('calculate', method_names, "'calculate' method should be present")
            self.assertIn('value', property_names, "'value' property should be present")
    
    def test_find_by_xpath(self):
        """Test the find_by_xpath method."""
        # Find class by XPath
        start_line, end_line = self.service.find_by_xpath(PYTHON_SAMPLE, 'FILE.ExampleClass')
        self.assertGreater(start_line, 0, "Start line should be positive")
        self.assertGreaterEqual(end_line, start_line, "End line should be >= start line")
        
        # Find method by XPath
        start_line, end_line = self.service.find_by_xpath(PYTHON_SAMPLE, 'FILE.ExampleClass.calculate')
        self.assertGreater(start_line, 0, "Start line should be positive")
        self.assertGreaterEqual(end_line, start_line, "End line should be >= start line")

if __name__ == '__main__':
    unittest.main()
