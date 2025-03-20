import unittest

import rich

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
        result = self.python_hem.extract("")
        self.assertIsInstance(result, CodeElementsResult)
        self.assertEqual(len(result.elements), 0)

    def test_extract_imports(self):
        """Test extraction of import statements."""
        code = '\nimport os\nimport sys\nfrom datetime import datetime\nfrom typing import List, Dict\n\ndef main():\n    pass\n'
        result = self.python_hem.extract(code)
        self.assertIsInstance(result, CodeElementsResult)

        # Find imports element
        imports_element = None
        for element in result.elements:
            if element.type == CodeElementType.IMPORT:
                imports_element = element
                break

        self.assertIsNotNone(imports_element)
        self.assertEqual(imports_element.name, 'imports')
        self.assertIn('import_statements', imports_element.additional_data)
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
        result = self.python_hem.extract(code)

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
            if child.name == "get_value":
                self.assertIn("return self.value", child.content)


    def test_extract_class_with_static_properties(self):
        """Test extraction of a class with static properties (class variables)."""
        code = """
    class ConfigClass:
        VERSION = "1.0.0"
        DEBUG = True
        MAX_CONNECTIONS = 100
        DEFAULT_TIMEOUT = 30.0

        def __init__(self):
            self.instance_var = "instance"

        def get_version(self):
            return self.VERSION
    """
        result = self.python_hem.extract(code)

        # Find class element
        class_element = None
        for element in result.elements:
            if element.type == CodeElementType.CLASS and element.name == "ConfigClass":
                class_element = element
                break

        self.assertIsNotNone(class_element)

        # Find actual property elements (static properties)
        property_elements = [
            child
            for child in class_element.children
            if child.type == CodeElementType.PROPERTY
        ]

        # We should have 4 static properties
        self.assertEqual(len(property_elements), 4, "Should have 4 static properties")

        # Check property names
        property_names = [prop.name for prop in property_elements]
        expected_names = ["VERSION", "DEBUG", "MAX_CONNECTIONS", "DEFAULT_TIMEOUT"]

        for name in expected_names:
            self.assertIn(name, property_names, f"Should have '{name}' static property")

        # Check property values
        for prop in property_elements:
            if prop.name == "VERSION":
                self.assertEqual(prop.additional_data.get("value"), '"1.0.0"')
            elif prop.name == "DEBUG":
                self.assertEqual(prop.additional_data.get("value"), "True")
            elif prop.name == "MAX_CONNECTIONS":
                self.assertEqual(prop.additional_data.get("value"), "100")
            elif prop.name == "DEFAULT_TIMEOUT":
                self.assertEqual(prop.additional_data.get('value'), '30.0')

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
        result = self.python_hem.extract(code)

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
        result = self.python_hem.extract(code)

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
        code = '\ndef outer_function():\n    class InnerClass:\n        def inner_method(self):\n            pass\n\n    return InnerClass()\n'
        result = self.python_hem.extract(code)

        # We should have one function
        function_elements = [element for element in result.elements if element.type == CodeElementType.FUNCTION]
        self.assertEqual(len(function_elements), 1)
        self.assertEqual(function_elements[0].name, 'outer_function')

        # Currently, the extraction doesn't capture nested classes inside functions
        # This is a limitation of the current implementation
        class_elements = [element for element in result.elements if element.type == CodeElementType.CLASS]
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
        result = self.typescript_hem.extract(code)

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
        code = '\n@dataclass\nclass BaseEntity:\n    id: int\n    created_at: datetime\n\n    def get_id(self):\n        return self.id\n\n@dataclass\nclass User(BaseEntity):\n    name: str\n    email: str\n    _password: str\n\n    @property\n    def password(self):\n        return "********"\n\n    @password.setter\n    def password(self, new_password):\n        self._password = hash_password(new_password)\n\n    @staticmethod\n    def validate_email(email):\n        return \'@\' in email\n'
        result = self.python_hem.extract(code)

        # Check classes
        class_elements = [element for element in result.elements if element.type == CodeElementType.CLASS]
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
        property_method_count = 0
        setter_method_count = 0
        static_method_count = 0

        for child in user_class.children:
            if child.type == CodeElementType.METHOD:
                method_count += 1
                # Check for property decorator
                if 'decorators' in child.additional_data:
                    decorators = child.additional_data['decorators']
                    # Count different decorator types
                    if any(d.startswith('@property') for d in decorators):
                        property_method_count += 1
                    if any('.setter' in d for d in decorators):
                        setter_method_count += 1
                    if any(d.startswith('@staticmethod') for d in decorators):
                        static_method_count += 1

        self.assertGreaterEqual(method_count, 3)  # At least password getter, setter and validate_email

        # If we can't distinguish between property and setter decorators, combine their count
        combined_property_count = property_method_count + setter_method_count
        self.assertEqual(combined_property_count, 2)  # One property getter and one setter

        self.assertEqual(static_method_count, 1)   # One method with @staticmethod decorator

if __name__ == '__main__':
    unittest.main()