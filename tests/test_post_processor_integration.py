"""
Integration tests for the new PostProcessorFactory and TypeScriptPostProcessor implementation.

This module provides tests to verify the correct integration of post-processors
with the ExtractionService, ensuring that language-specific processing
works as expected.
"""

import unittest
import os
from typing import Dict, List

from codehem.main import CodeHem
from codehem.core.post_processors.factory import PostProcessorFactory
from codehem.core.post_processors.python import PythonPostProcessor
from codehem.core.post_processors.typescript import TypeScriptPostProcessor
from codehem.models.enums import CodeElementType


class PostProcessorIntegrationTest(unittest.TestCase):
    """Test the integration of PostProcessorFactory and language-specific post-processors."""

    def test_post_processor_factory_registration(self):
        """Test that post-processors are correctly registered in the factory."""
        # Check that Python and TypeScript are registered
        supported = PostProcessorFactory.get_supported_languages()
        self.assertIn('python', supported)
        self.assertIn('typescript', supported)
        
        # Check that JavaScript maps to TypeScript
        js_processor = PostProcessorFactory.get_post_processor('javascript')
        self.assertIsInstance(js_processor, TypeScriptPostProcessor)
    
    def test_post_processor_instantiation(self):
        """Test that post-processors can be instantiated correctly."""
        python_processor = PostProcessorFactory.get_post_processor('python')
        ts_processor = PostProcessorFactory.get_post_processor('typescript')
        
        self.assertIsInstance(python_processor, PythonPostProcessor)
        self.assertIsInstance(ts_processor, TypeScriptPostProcessor)
        
        # Check language codes
        self.assertEqual(python_processor.language_code, 'python')
        self.assertEqual(ts_processor.language_code, 'typescript')
    
    def test_python_code_extraction(self):
        """Test extraction of Python code using the post-processor."""
        python_code = """
class ExampleClass:
    def method1(self):
        return "Hello"
        
    def method2(self, param):
        return f"Hello, {param}"

def standalone_function():
    return "standalone"
"""
        # Create a CodeHem instance for Python
        hem = CodeHem('python')
        
        # Extract code elements
        result = hem.extract(python_code)
        
        # Verify class extraction
        class_element = hem.filter(result, 'ExampleClass')
        self.assertIsNotNone(class_element)
        self.assertEqual(class_element.type, CodeElementType.CLASS)
        self.assertEqual(len(class_element.children), 2)  # Two methods
        
        # Verify method extraction
        method1 = hem.filter(result, 'ExampleClass.method1')
        self.assertIsNotNone(method1)
        self.assertEqual(method1.type, CodeElementType.METHOD)
        
        # Verify function extraction
        function = hem.filter(result, 'standalone_function')
        self.assertIsNotNone(function)
        self.assertEqual(function.type, CodeElementType.FUNCTION)
    
    def test_typescript_code_extraction(self):
        """Test extraction of TypeScript code using the post-processor."""
        typescript_code = """
class Person {
    private name: string;
    private age: number;
    
    constructor(name: string, age: number) {
        this.name = name;
        this.age = age;
    }
    
    public getName(): string {
        return this.name;
    }
    
    public getAge(): number {
        return this.age;
    }
}

interface Shape {
    area(): number;
}

function calculateArea(shape: Shape): number {
    return shape.area();
}
"""
        # Create a CodeHem instance for TypeScript
        hem = CodeHem('typescript')
        
        # Extract code elements
        result = hem.extract(typescript_code)
        
        # Verify class extraction
        class_element = hem.filter(result, 'Person')
        self.assertIsNotNone(class_element)
        self.assertEqual(class_element.type, CodeElementType.CLASS)
        
        # Verify method extraction
        getName = hem.filter(result, 'Person.getName')
        self.assertIsNotNone(getName)
        self.assertEqual(getName.type, CodeElementType.METHOD)
        
        # Verify function extraction
        function = hem.filter(result, 'calculateArea')
        self.assertIsNotNone(function)
        self.assertEqual(function.type, CodeElementType.FUNCTION)
        
        # Verify interface extraction if supported
        interface = next((e for e in result.elements if e.type == CodeElementType.INTERFACE), None)
        if interface:
            self.assertEqual(interface.name, 'Shape')


if __name__ == '__main__':
    unittest.main()
