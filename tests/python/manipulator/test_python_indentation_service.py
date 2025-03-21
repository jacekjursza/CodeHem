import unittest

from codehem.core.services.python_indentation_service import PythonIndentationService

class TestPythonIndentationService(unittest.TestCase):
    """Test suite for PythonIndentationService."""
    
    def setUp(self):
        self.service = PythonIndentationService()
    
    def test_calculate_class_indentation(self):
        """Test calculating indentation for classes."""
        code_lines = [
            "class OuterClass:",
            "    def method1(self):",
            "    class NestedClass:",
            "        def method2(self):"
        ]
        
        # Test simple class
        indent = self.service.calculate_class_indentation(code_lines, "OuterClass")
        self.assertEqual(indent, "    ")
        
        # Test nested class
        indent = self.service.calculate_class_indentation(code_lines, "OuterClass.NestedClass")
        self.assertEqual(indent, "        ")


    def test_format_method_with_nested_conditionals(self):
        """Test formatting a method with nested conditionals."""
        method_content = """
def nested_conditionals(self, x, y):
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x - y
    else:
        return 0
"""
        expected = """    def nested_conditionals(self, x, y):
        if x > 0:
            if y > 0:
                return x + y
            else:
                return x - y
        else:
            return 0"""
        
        formatted = self.service.format_method_content(method_content, "    ")
        self.assertEqual(formatted, expected)

if __name__ == "__main__":
    unittest.main()