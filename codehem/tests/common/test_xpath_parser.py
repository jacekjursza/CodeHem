"""
Tests for the XPath parser.
"""
import unittest

from ... import CodeElementType
from ...engine.xpath_parser import XPathParser


class XPathParserTests(unittest.TestCase):
    """Tests for XPath parser functionality."""

    def test_simple_class_xpath(self):
        """Test parsing a simple class XPath."""
        xpath = "MyClass"
        nodes = XPathParser.parse(xpath)
        self.assertEqual(1, len(nodes))
        self.assertEqual("MyClass", nodes[0].name)
        self.assertEqual(CodeElementType.CLASS.value, nodes[0].type)

    def test_class_with_explicit_type(self):
        """Test parsing class with explicit type."""
        xpath = "MyClass[class]"
        nodes = XPathParser.parse(xpath)
        self.assertEqual(1, len(nodes))
        self.assertEqual("MyClass", nodes[0].name)
        self.assertEqual(CodeElementType.CLASS.value, nodes[0].type)

    def test_class_method_xpath(self):
        """Test parsing class.method XPath."""
        xpath = "MyClass.my_method"
        nodes = XPathParser.parse(xpath)
        self.assertEqual(2, len(nodes))
        self.assertEqual("MyClass", nodes[0].name)
        self.assertEqual(CodeElementType.CLASS.value, nodes[0].type)
        self.assertEqual("my_method", nodes[1].name)
        self.assertEqual(CodeElementType.METHOD.value, nodes[1].type)

    def test_property_getter_xpath(self):
        """Test parsing property getter with explicit type."""
        xpath = "MyClass.my_property[property_getter]"
        nodes = XPathParser.parse(xpath)
        self.assertEqual(2, len(nodes))
        self.assertEqual("MyClass", nodes[0].name)
        self.assertEqual("my_property", nodes[1].name)
        self.assertEqual(CodeElementType.PROPERTY_GETTER.value, nodes[1].type)

    def test_property_setter_xpath(self):
        """Test parsing property setter with explicit type."""
        xpath = "MyClass.my_property[property_setter]"
        nodes = XPathParser.parse(xpath)
        self.assertEqual(2, len(nodes))
        self.assertEqual("MyClass", nodes[0].name)
        self.assertEqual("my_property", nodes[1].name)
        self.assertEqual(CodeElementType.PROPERTY_SETTER.value, nodes[1].type)

    def test_interface_xpath(self):
        """Test parsing with interface type."""
        xpath = "MyClass[interface].my_method"
        nodes = XPathParser.parse(xpath)
        self.assertEqual(2, len(nodes))
        self.assertEqual("MyClass", nodes[0].name)
        self.assertEqual(CodeElementType.INTERFACE.value, nodes[0].type)
        self.assertEqual("my_method", nodes[1].name)
        self.assertEqual(CodeElementType.METHOD.value, nodes[1].type)

    def test_standalone_function_xpath(self):
        """Test parsing standalone function."""
        xpath = "my_function"
        nodes = XPathParser.parse(xpath)
        self.assertEqual(1, len(nodes))
        self.assertEqual("my_function", nodes[0].name)
        self.assertEqual(CodeElementType.FUNCTION.value, nodes[0].type)

    def test_with_root_element(self):
        """Test parsing with FILE root element."""
        xpath = "FILE.MyClass.my_method"
        nodes = XPathParser.parse(xpath)
        self.assertEqual(3, len(nodes))
        self.assertEqual(None, nodes[0].name)
        self.assertEqual(CodeElementType.FILE.value, nodes[0].type)
        self.assertEqual("MyClass", nodes[1].name)
        self.assertEqual("my_method", nodes[2].name)

    def test_type_only_xpath(self):
        """Test parsing type-only XPath."""
        xpath = "[import]"
        nodes = XPathParser.parse(xpath)
        self.assertEqual(1, len(nodes))
        self.assertEqual(None, nodes[0].name)
        self.assertEqual(CodeElementType.IMPORT.value, nodes[0].type)

    def test_nameless_node_in_path(self):
        """Test parsing path with nameless node."""
        xpath = "FILE.[import]"
        nodes = XPathParser.parse(xpath)
        self.assertEqual(2, len(nodes))
        self.assertEqual(None, nodes[0].name)
        self.assertEqual(CodeElementType.FILE.value, nodes[0].type)
        self.assertEqual(None, nodes[1].name)
        self.assertEqual(CodeElementType.IMPORT.value, nodes[1].type)

    def test_to_string(self):
        """Test converting nodes back to string."""
        original = "MyClass[interface].my_property[property_getter]"
        nodes = XPathParser.parse(original)
        result = XPathParser.to_string(nodes)
        self.assertEqual(original, result)

    def test_get_element_info(self):
        """Test extracting element info from XPath."""
        xpath = "MyClass.my_property[property_getter]"
        element_name, parent_name, element_type = XPathParser.get_element_info(xpath)
        self.assertEqual("my_property", element_name)
        self.assertEqual("MyClass", parent_name)
        self.assertEqual(CodeElementType.PROPERTY_GETTER.value, element_type)
        
        xpath = "my_function"
        element_name, parent_name, element_type = XPathParser.get_element_info(xpath)
        self.assertEqual("my_function", element_name)
        self.assertEqual(None, parent_name)
        self.assertEqual(CodeElementType.FUNCTION.value, element_type)