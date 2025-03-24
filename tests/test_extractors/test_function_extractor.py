"""
Tests for function extractors.
"""
import unittest
from unittest.mock import patch, MagicMock

from extractors.function.main import TreeSitterFunctionExtractor
from extractors.function.fallback import RegexFunctionExtractor

class TestTreeSitterFunctionExtractor(unittest.TestCase):
    
    def setUp(self):
        self.extractor = TreeSitterFunctionExtractor()
        
    def test_supports_language(self):
        """Test language support detection."""
        self.assertTrue(self.extractor.supports_language('python'))
        self.assertTrue(self.extractor.supports_language('javascript'))
        self.assertTrue(self.extractor.supports_language('typescript'))
        self.assertFalse(self.extractor.supports_language('unsupported'))
        
    @patch('core.ast_handler.ASTHandler')
    def test_extract_python_function(self, mock_handler):
        """Test extraction of Python functions."""
        # Setup mock
        mock_instance = MagicMock()
        mock_handler.return_value = mock_instance
        
        mock_tree = MagicMock()
        mock_code_bytes = b"def test_function():\n    return 'test'"
        mock_instance.parse.return_value = (mock_tree, mock_code_bytes)
        
        # Mock query results
        mock_func_def = MagicMock()
        mock_func_def.start_byte = 0
        mock_func_def.end_byte = len(mock_code_bytes)
        mock_func_def.start_point = (0, 0)
        mock_func_def.end_point = (1, 15)
        
        mock_func_name = MagicMock()
        mock_func_name.start_byte = 4
        mock_func_name.end_byte = 17
        
        mock_instance.execute_query.return_value = [[(mock_func_def, 'function_def'), (mock_func_name, 'function_name')]]
        
        # Test extraction
        result = self.extractor.extract(mock_code_bytes.decode('utf-8'), {'language_code': 'python'})
        
        # Verify results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'function')
        self.assertEqual(result[0]['content'], mock_code_bytes.decode('utf-8'))

class TestRegexFunctionExtractor(unittest.TestCase):
    
    def setUp(self):
        self.extractor = RegexFunctionExtractor()
        
    def test_supports_language(self):
        """Test language support detection."""
        self.assertTrue(self.extractor.supports_language('python'))
        self.assertTrue(self.extractor.supports_language('javascript'))
        self.assertTrue(self.extractor.supports_language('typescript'))
        self.assertFalse(self.extractor.supports_language('unsupported'))
        
    def test_extract_python_function(self):
        """Test extraction of Python functions with regex."""
        code = """
def test_function():
    return 'test'
        
def another_function(param1, param2):
    # This is a comment
    result = param1 + param2
    return result
"""
        
        result = self.extractor.extract(code, {'language_code': 'python'})
        
        # Verify results
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'test_function')
        self.assertEqual(result[1]['name'], 'another_function')

if __name__ == '__main__':
    unittest.main()