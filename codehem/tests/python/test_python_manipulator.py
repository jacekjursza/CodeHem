"""
Tests for Python manipulator functionality using the CodeHem2 API.
"""
import unittest
from ...codehem2 import CodeHem2
from ...models import CodeElementType
from ..helpers.code_examples import TestHelper

class PythonManipulatorTests(unittest.TestCase):
    """Tests for Python manipulator functionality using CodeHem2."""

    def setUp(self):
        """Set up test environment."""
        self.codehem = CodeHem2('python')
        self.sample_code = TestHelper.load_example("sample_class_with_properties", "general").content

    def test_replace_method(self):
        """Test replacing a method."""
        new_method = '\ndef calculate(self, multiplier: int, offset: int = 0) -> int:\n    return self._value * multiplier + offset\n'
        modified_code = self.codehem.upsert_element(self.sample_code, CodeElementType.METHOD.value, 'calculate', new_method, 'ExampleClass')
        self.assertIsNotNone(modified_code)
        self.assertIn('def calculate(self, multiplier: int, offset: int = 0) -> int:', modified_code)
        self.assertIn('return self._value * multiplier + offset', modified_code)
        self.assertIn('class ExampleClass:', modified_code)
        self.assertIn('@property', modified_code)
        self.assertIn('def standalone_function(param: str) -> str:', modified_code)

    def test_add_method(self):
        """Test adding a new method."""
        new_method = '\ndef new_method(self, param: str) -> None:\n    print(f"New method with {param}")\n'
        modified_code = self.codehem.upsert_element(self.sample_code, CodeElementType.METHOD.value, 'new_method', new_method, 'ExampleClass')
        self.assertIsNotNone(modified_code)
        self.assertIn('def new_method(self, param: str) -> None:', modified_code)
        self.assertIn('print(f"New method with {param}")', modified_code)
        self.assertIn('def calculate(self, multiplier: int) -> int:', modified_code)

    def test_add_class(self):
        """Test adding a new class."""
        new_class = '\nclass NewClass:\n    def __init__(self):\n        self.name = "New"\n        \n    def get_name(self) -> str:\n        return self.name\n'
        modified_code = self.codehem.upsert_element(self.sample_code, CodeElementType.CLASS.value, 'NewClass', new_class)
        self.assertIsNotNone(modified_code)
        self.assertIn('class NewClass:', modified_code)
        self.assertIn('def get_name(self) -> str:', modified_code)
        self.assertIn('class ExampleClass:', modified_code)

    def test_replace_property(self):
        """Test replacing a property."""
        new_property = '\n@property\ndef value(self) -> int:\n    print("Getting value")\n    return self._value\n'
        modified_code = self.codehem.upsert_element(self.sample_code, CodeElementType.PROPERTY_GETTER.value, 'value', new_property, 'ExampleClass')
        self.assertIsNotNone(modified_code)
        self.assertIn('print("Getting value")', modified_code)
        self.assertIn('@value.setter', modified_code)

    def test_add_import(self):
        """Test adding imports."""
        new_imports = '\nimport sys\nfrom datetime import datetime\n'
        modified_code = self.codehem.upsert_element(self.sample_code, CodeElementType.IMPORT.value, '', new_imports)
        self.assertIsNotNone(modified_code)
        print("MODIFIED CODE:")
        print(modified_code)
        print('-----------------------')
        self.assertIn('import sys', modified_code)
        self.assertIn('from datetime import datetime', modified_code)
        self.assertIn('import os', modified_code)
        self.assertIn('from typing import List, Dict, Optional', modified_code)

    def test_upsert_element_by_xpath(self):
        """Test using upsert_element_by_xpath method."""
        new_method = '\ndef calculate(self, multiplier: int, offset: int = 0) -> int:\n    """Calculate with multiplier and offset."""\n    return self._value * multiplier + offset\n'
        modified_code = self.codehem.upsert_element_by_xpath(self.sample_code, 'ExampleClass.calculate', new_method)
        self.assertIsNotNone(modified_code)
        self.assertIn('def calculate(self, multiplier: int, offset: int = 0) -> int:', modified_code)
        self.assertIn('"""Calculate with multiplier and offset."""', modified_code)
        self.assertIn('return self._value * multiplier + offset', modified_code)