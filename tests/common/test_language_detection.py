"""
Tests for language detection functionality.
"""
import unittest

from codehem import CodeHem
from codehem.languages import get_language_service_for_code
from ..helpers.code_examples import TestHelper

class LanguageDetectionTests(unittest.TestCase):
    """Tests for language detection functionality."""

    def test_python_detection(self):
        """Test Python language detection."""
        example = TestHelper.load_example("sample_class_with_properties", "general")
        language_service = get_language_service_for_code(example.content)
        self.assertIsNotNone(language_service)
        self.assertEqual("python", language_service.language_code)
        codehem = CodeHem.from_raw_code(example.content)
        self.assertEqual("python", codehem.language_service.language_code)

    def test_edge_case_detection(self):
        """Test detection with minimal code."""
        minimal_python = 'def foo(): pass'
        language_service = get_language_service_for_code(minimal_python)
        self.assertIsNotNone(language_service)
        self.assertEqual("python", language_service.language_code)

    def test_comments_only(self):
        """Test detection with only comments."""
        python_comments = '# This is a Python comment\n# Another comment'
        javascript_comments = '// This is a JavaScript comment\n// Another comment'
        py_service = get_language_service_for_code(python_comments)
        if py_service:
            self.assertEqual("python", py_service.language_code)
        js_service = get_language_service_for_code(javascript_comments)
        self.assertIsNone(js_service)

    def test_empty_code(self):
        """Test detection with empty or whitespace-only code."""
        empty_code = ''
        whitespace_code = '   \n  \t  '
        self.assertIsNone(get_language_service_for_code(empty_code))
        self.assertIsNone(get_language_service_for_code(whitespace_code))