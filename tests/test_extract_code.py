import unittest
from core.models import CodeElementsResult, CodeElementType, MetaElementType
from main import CodeHem

class TestExtractCodeElements(unittest.TestCase):
    """Test suite for the CodeHem extract_code_elements method."""

    def setUp(self):
        """Set up test fixtures."""
        self.python_hem = CodeHem('python')
        self.typescript_hem = CodeHem('typescript')

    def test_extract_empty_code(self):
        """Test extraction from empty code."""
        result = self.python_hem.extract_code_elements("")
        self.assertIsInstance(result, CodeElementsResult)
        self.assertEqual(len(result.elements), 0)

    def test_extract_imports(self):
        """Test extraction of import statements."""
        code = """
import os
import sys
from datetime import datetime
from typing import List, Dict

def main():
    pass
"""
        result = self.python_hem.extract_code_elements(code)
        self.assertIsInstance(result, CodeElementsResult)

        # Find imports element
        imports_element = None
        for element in result.elements:
            if element.type == CodeElementType.IMPORT:
                imports_element = element
                break

        self.assertIsNotNone(imports_element)
        self.assertEqual(imports_element.name, 'imports')
        self.assertIn('import statements', imports_element.additional_data)
        import_statements = imports_element.additional_data['import_statements']
        self.assertEqual(len(import_statements), 4)
        self.assertIn('import os', import_statements)
        self.assertIn('import sys', import_statements)
        self.assertIn('from datetime import datetime', import_statements)
        self.assertIn('from typing import List, Dict', import_statements)

    def test_extract_class_with_methods(self):
        """Test extraction of a class with methods."""
        code = """
class TestClass:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def set_value(self, new_value):
        self.value = new_value
"""
        result = self.python_hem.extract_code_elements(code)

        # Find class element
        class_element = None
        for element in result.elements:
            if element.type == CodeElementType.CLASS and element.name == 'TestClass':
                class_element = element
                break

        self.assertIsNotNone(class_element)
        self.assertEqual(len(class_element.children), 3)

        # Check methods
        method_names = [child.name for child in class_element.children]
        self.assertIn('__init__', method_names)
        self.assertIn('get_value', method_names)
        self.assertIn('set_value', method_names)

        # Check method content
        for child in class_element.children:
            if child.name == 'get_value':
                self.assertIn('return self.value', child.content)

    def test_extract_class_with_properties(self):
        """Test extraction of a class with properties."""
        code = """
class Person:
    def __init__(self, name, age):
        self._name = name
        self._age = age

    @property
    def name(self):
        return self._name

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        if value < 0:
            raise ValueError("Age cannot be negative")
        self._age = value
"""
        result = self.python_hem.extract_code_elements(code)

        # Find class element
        class_element = None
        for element in result.elements:
            if element.type == CodeElementType.CLASS and element.name == 'Person':
                class_element = element
                break

        self.assertIsNotNone(class_element)

        # Check properties
        property_elements = [child for child in class_element.children if child.type == CodeElementType.PROPERTY]
        self.assertEqual(len(property_elements), 2)

        property_names = [prop.name for prop in property_elements]
        self.assertIn('name', property_names)
        self.assertIn('age', property_names)

        # Check property decorators
        for prop in property_elements:
            if prop.name == 'age':
                # Check if we have metadata about decorators
                self.assertIn('decorators', prop.additional_data)
                decorators = prop.additional_data['decorators']
                self.assertIn('@property', decorators)

    def test_extract_functions(self):
        """Test extraction of standalone functions."""
        code = """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

@decorator
def decorated_function():
    print("I am decorated")
"""
        result = self.python_hem.extract_code_elements(code)

        # Find function elements
        function_elements = [element for element in result.elements
                             if element.type == CodeElementType.FUNCTION]

        self.assertEqual(len(function_elements), 3)

        function_names = [func.name for func in function_elements]
        self.assertIn('add', function_names)
        self.assertIn('multiply', function_names)
        self.assertIn('decorated_function', function_names)

        # Check decorator for decorated_function
        for func in function_elements:
            if func.name == 'decorated_function':
                self.assertIn('decorators', func.additional_data)
                decorators = func.additional_data['decorators']
                self.assertIn('@decorator', decorators)

                # Check meta elements
                meta_elements = [child for child in func.children
                                 if child.type == CodeElementType.META_ELEMENT]
                self.assertEqual(len(meta_elements), 1)

                meta = meta_elements[0]
                self.assertEqual(meta.name, 'decorator')
                self.assertEqual(meta.additional_data['meta_type'], MetaElementType.DECORATOR)
                self.assertEqual(meta.additional_data['target_type'], 'function')
                self.assertEqual(meta.additional_data['target_name'], 'decorated_function')

    def test_extract_multiple_classes(self):
        """Test extraction of multiple classes."""
        code = """
class BaseClass:
    def base_method(self):
        pass

class ChildClass(BaseClass):
    def child_method(self):
        pass
"""
        result = self.python_hem.extract_code_elements(code)

        class_elements = [element for element in result.elements
                          if element.type == CodeElementType.CLASS]

        self.assertEqual(len(class_elements), 2)

        class_names = [cls.name for cls in class_elements]
        self.assertIn('BaseClass', class_names)
        self.assertIn('ChildClass', class_names)

        # Get methods for each class
        for cls in class_elements:
            if cls.name == 'BaseClass':
                self.assertEqual(len(cls.children), 1)
                self.assertEqual(cls.children[0].name, 'base_method')
            elif cls.name == 'ChildClass':
                self.assertEqual(len(cls.children), 1)
                self.assertEqual(cls.children[0].name, 'child_method')

    def test_extract_nested_structures(self):
        """Test extraction of nested structures like classes inside functions."""
        code = """
def outer_function():
    class InnerClass:
        def inner_method(self):
            pass

    return InnerClass()
"""
        result = self.python_hem.extract_code_elements(code)

        # We should have one function
        function_elements = [element for element in result.elements
                             if element.type == CodeElementType.FUNCTION]
        self.assertEqual(len(function_elements), 1)
        self.assertEqual(function_elements[0].name, 'outer_function')

        # Currently, the extraction doesn't capture nested classes inside functions
        # This is a limitation of the current implementation
        class_elements = [element for element in result.elements
                          if element.type == CodeElementType.CLASS]
        self.assertEqual(len(class_elements), 0)

    def test_typescript_extraction(self):
        """Test extraction from TypeScript code."""
        code = """
import { Component } from 'react';

class MyComponent extends Component {
    private count: number = 0;

    constructor() {
        super();
    }

    render() {
        return <div>{this.count}</div>;
    }

    increment() {
        this.count++;
    }
}

function calculateSum(a: number, b: number): number {
    return a + b;
}
"""
        result = self.typescript_hem.extract_code_elements(code)

        # Check imports
        imports_element = None
        for element in result.elements:
            if element.type == CodeElementType.IMPORT:
                imports_element = element
                break

        self.assertIsNotNone(imports_element)

        # Check class
        class_element = None
        for element in result.elements:
            if element.type == CodeElementType.CLASS and element.name == 'MyComponent':
                class_element = element
                break

        self.assertIsNotNone(class_element)

        # Check methods
        method_names = [child.name for child in class_element.children]
        self.assertIn('constructor', method_names)
        self.assertIn('render', method_names)
        self.assertIn('increment', method_names)

        # Check function
        function_elements = [element for element in result.elements
                             if element.type == CodeElementType.FUNCTION]
        self.assertEqual(len(function_elements), 1)
        self.assertEqual(function_elements[0].name, 'calculateSum')

    def test_complex_class_hierarchy(self):
        """Test extraction of complex class hierarchy with inheritance and decorators."""
        code = """
@dataclass
class BaseEntity:
    id: int
    created_at: datetime

    def get_id(self):
        return self.id

@dataclass
class User(BaseEntity):
    name: str
    email: str
    _password: str

    @property
    def password(self):
        return "********"

    @password.setter
    def password(self, new_password):
        self._password = hash_password(new_password)

    @staticmethod
    def validate_email(email):
        return '@' in email
"""
        result = self.python_hem.extract_code_elements(code)

        # Check classes
        class_elements = [element for element in result.elements
                          if element.type == CodeElementType.CLASS]
        self.assertEqual(len(class_elements), 2)

        # Find User class
        user_class = None
        for cls in class_elements:
            if cls.name == 'User':
                user_class = cls
                break

        self.assertIsNotNone(user_class)

        # Check class decorators
        self.assertIn('decorators', user_class.additional_data)
        self.assertIn('@dataclass', user_class.additional_data['decorators'])

        # Check methods and properties
        method_count = 0
        property_count = 0
        static_method_count = 0

        for child in user_class.children:
            if child.type == CodeElementType.METHOD:
                method_count += 1
            elif child.type == CodeElementType.PROPERTY:
                property_count += 1

            # Check for static method
            if 'decorators' in child.additional_data:
                decorators = child.additional_data['decorators']
                if '@staticmethod' in decorators:
                    static_method_count += 1

        self.assertGreaterEqual(method_count, 1)  # At least password setter and validate_email
        self.assertEqual(property_count, 1)       # password property
        self.assertEqual(static_method_count, 1)  # validate_email

if __name__ == '__main__':
    unittest.main()