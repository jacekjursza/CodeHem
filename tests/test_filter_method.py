import unittest
from core.models import CodeElementsResult, CodeElement, CodeElementType, CodeRange, MetaElementType
from main import CodeHem

class TestCodeHemFilter(unittest.TestCase):
    """Test cases for the CodeHem filter method."""

    def setUp(self):
        """Set up test fixtures."""
        self.hem = CodeHem('python')
        
        # Create a sample code elements structure for testing
        self.elements = CodeElementsResult()
        
        # Add an import element
        import_element = CodeElement(
            type=CodeElementType.IMPORT,
            name='imports',
            content='import os\nimport sys\n',
            range=CodeRange(start_line=1, end_line=2, node=None),
            additional_data={'import_statements': ['import os', 'import sys']}
        )
        self.elements.elements.append(import_element)
        
        # Add a class element
        class_element = CodeElement(
            type=CodeElementType.CLASS,
            name='TestClass',
            content='class TestClass:\n    def method1(self):\n        pass\n',
            range=CodeRange(start_line=4, end_line=6, node=None),
            additional_data={'decorators': []}
        )
        
        # Add methods to the class
        method1 = CodeElement(
            type=CodeElementType.METHOD,
            name='method1',
            content='def method1(self):\n    pass\n',
            range=CodeRange(start_line=5, end_line=6, node=None),
            parent_name='TestClass',
            additional_data={'decorators': []}
        )
        class_element.children.append(method1)
        
        property1 = CodeElement(
            type=CodeElementType.PROPERTY,
            name='property1',
            content='@property\ndef property1(self):\n    return self._property1\n',
            range=CodeRange(start_line=7, end_line=9, node=None),
            parent_name='TestClass',
            additional_data={'decorators': ['@property']}
        )
        class_element.children.append(property1)
        
        self.elements.elements.append(class_element)
        
        # Add a standalone function
        function_element = CodeElement(
            type=CodeElementType.FUNCTION,
            name='standalone_function',
            content='def standalone_function():\n    return 42\n',
            range=CodeRange(start_line=11, end_line=12, node=None),
            additional_data={'decorators': []}
        )
        self.elements.elements.append(function_element)

    def test_filter_class(self):
        """Test filtering by class name."""
        result = self.hem.filter(self.elements, "TestClass")
        self.assertIsNotNone(result)
        self.assertEqual(result.type, CodeElementType.CLASS)
        self.assertEqual(result.name, "TestClass")

    def test_filter_method(self):
        """Test filtering by method within a class."""
        result = self.hem.filter(self.elements, "TestClass.method1")
        self.assertIsNotNone(result)
        self.assertEqual(result.type, CodeElementType.METHOD)
        self.assertEqual(result.name, "method1")
        self.assertEqual(result.parent_name, "TestClass")

    def test_filter_property(self):
        """Test filtering by property within a class."""
        result = self.hem.filter(self.elements, "TestClass.property1")
        self.assertIsNotNone(result)
        self.assertEqual(result.type, CodeElementType.PROPERTY)
        self.assertEqual(result.name, "property1")
        self.assertEqual(result.parent_name, "TestClass")

    def test_filter_function(self):
        """Test filtering by standalone function name."""
        result = self.hem.filter(self.elements, "standalone_function")
        self.assertIsNotNone(result)
        self.assertEqual(result.type, CodeElementType.FUNCTION)
        self.assertEqual(result.name, "standalone_function")
        self.assertIsNone(result.parent_name)

    def test_filter_imports(self):
        """Test filtering for imports section."""
        result = self.hem.filter(self.elements, "imports")
        self.assertIsNotNone(result)
        self.assertEqual(result.type, CodeElementType.IMPORT)
        self.assertEqual(result.name, "imports")

    def test_filter_nonexistent_class(self):
        """Test filtering for a class that doesn't exist."""
        result = self.hem.filter(self.elements, "NonExistentClass")
        self.assertIsNone(result)

    def test_filter_nonexistent_method(self):
        """Test filtering for a method that doesn't exist."""
        result = self.hem.filter(self.elements, "TestClass.nonexistent_method")
        self.assertIsNone(result)

    def test_filter_nonexistent_function(self):
        """Test filtering for a function that doesn't exist."""
        result = self.hem.filter(self.elements, "nonexistent_function")
        self.assertIsNone(result)

    def test_filter_empty_xpath(self):
        """Test filtering with an empty xpath."""
        result = self.hem.filter(self.elements, "")
        self.assertIsNone(result)

    def test_filter_with_real_code(self):
        """Test filtering with actual code extraction."""
        code = """
import os
import sys

class SampleClass:
    def method1(self):
        return "Hello from method1"
    
    @property
    def prop1(self):
        return self._prop1
    
def standalone_func():
    return 42
"""
        elements = self.hem.extract_code_elements(code)
        
        # Test class filter
        class_element = self.hem.filter(elements, "SampleClass")
        self.assertIsNotNone(class_element)
        self.assertEqual(class_element.type, CodeElementType.CLASS)
        self.assertEqual(class_element.name, "SampleClass")
        
        # Test method filter
        method_element = self.hem.filter(elements, "SampleClass.method1")
        self.assertIsNotNone(method_element)
        self.assertEqual(method_element.type, CodeElementType.METHOD)
        self.assertEqual(method_element.name, "method1")
        
        # Test property filter
        prop_element = self.hem.filter(elements, "SampleClass.prop1")
        self.assertIsNotNone(prop_element)
        self.assertEqual(prop_element.type, CodeElementType.PROPERTY)
        self.assertEqual(prop_element.name, "prop1")
        
        # Test function filter
        func_element = self.hem.filter(elements, "standalone_func")
        self.assertIsNotNone(func_element)
        self.assertEqual(func_element.type, CodeElementType.FUNCTION)
        self.assertEqual(func_element.name, "standalone_func")
        
        # Test imports filter
        import_element = self.hem.filter(elements, "imports")
        self.assertIsNotNone(import_element)
        self.assertEqual(import_element.type, CodeElementType.IMPORT)

if __name__ == '__main__':
    unittest.main()