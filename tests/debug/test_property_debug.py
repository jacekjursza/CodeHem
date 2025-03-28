import pytest
from codehem import CodeHem, CodeElementType
from codehem.core.engine.xpath_parser import XPathParser

def test_debug_property_extraction():
    """Debug test to trace property extraction process."""
    # Simple class with property for testing
    test_code = """
class TestClass:
    
    def __init__(self, value=0):
        self._value = value
        
    @property
    def value(self):
        return self._value
        
    @value.setter
    def value(self, new_value):
        self._value = new_value
"""
    
    codehem = CodeHem('python')
    
    # Step 1: Skip the low-level AST parsing for now
    print("\n---- Property Extraction Debug ----")
    
    # Step 2: Debug method extraction (including properties)
    print("\n---- Method Extraction Debug ----")
    methods = codehem.extraction.extract_methods(test_code, "TestClass")
    print(f"Found {len(methods)} methods in TestClass:")
    for method in methods:
        print(f"  - Type: {method.get('type')}, Name: {method.get('name')}")
        print(f"    Decorators: {[d.get('name') for d in method.get('decorators', [])]}")
    
    # Step 3: Debug full element extraction and classification
    print("\n---- Element Extraction Debug ----")
    result = codehem.extract(test_code)
    print("All extracted elements:")
    for element in result.elements:
        print(f"  - {element.type}: {element.name}")
        if element.type == CodeElementType.CLASS:
            print(f"    Children: {len(element.children)}")
            for child in element.children:
                print(f"      - {child.type}: {child.name}")
                if hasattr(child, 'decorators') and child.decorators:
                    print(f"        Decorators: {[d.name for d in child.decorators]}")
    
    # Step 4: Debug XPath resolution
    print("\n---- XPath Resolution Debug ----")
    # Try various XPath expressions
    paths = [
        "TestClass",
        "TestClass.value",
        "TestClass.value[property_getter]",
        "TestClass.value[property_setter]",
    ]
    for path in paths:
        text = codehem.get_text_by_xpath(test_code, path)
        if text:
            print(f"XPath '{path}': Found - {len(text.split(chr(10)))} lines")
            print(f"  Content preview: {text[:50]}...")
        else:
            print(f"XPath '{path}': Not found")
        
        # Debug filter
        element = CodeHem.filter(result, path)
        print(f"  Filter '{path}': {element.type if element else 'Not found'}")
    
    # Step 5: Debug XPath finding mechanism directly
    print("\n---- XPath Finding Debug ----")
    for path in paths:
        start_line, end_line = codehem.find_by_xpath(test_code, path)
        print(f"find_by_xpath for '{path}': lines {start_line}-{end_line}")

def test_debug_sample_class_with_properties():
    """Debug test for the specific test case that's failing."""
    from tests.common.test_codehem2 import CodeHem2Tests
    
    # Create the test instance
    test_instance = CodeHem2Tests("test_get_property_methods_by_xpath")
    test_instance.setUp()
    
    # Extract the sample code used in the test
    sample_code = test_instance.sample_code
    codehem = test_instance.codehem
    
    print("\n---- Sample Code Analysis ----")
    print(f"Sample code length: {len(sample_code.split(chr(10)))} lines")
    print(f"Sample code preview:\n{sample_code[:300]}...")
    
    # Step 1: Check method extraction directly
    print("\n---- Direct Method Extraction ----")
    methods = codehem.extraction.extract_methods(sample_code, "ExampleClass")
    print(f"Found {len(methods)} methods in ExampleClass:")
    for method in methods:
        print(f"  - Type: {method.get('type')}, Name: {method.get('name')}")
        print(f"    Decorators: {[d.get('name') for d in method.get('decorators', [])]}")
    
    # Step 2: Check the full element extraction
    result = codehem.extract(sample_code)
    class_element = CodeHem.filter(result, "ExampleClass")
    if class_element:
        print(f"Found class ExampleClass with {len(class_element.children)} children")
        for child in class_element.children:
            print(f"  - {child.type}: {child.name}")
            if hasattr(child, 'decorators') and child.decorators:
                print(f"    Decorators: {[d.name for d in child.decorators]}")
    
    # Step 3: Direct XPath finding
    print("\n---- XPath Finding Debug ----")
    paths = [
        "ExampleClass", 
        "ExampleClass.value",
        "ExampleClass.value[property_getter]",
        "ExampleClass.value[property_setter]",
        "ExampleClass.calculate"
    ]
    for path in paths:
        start_line, end_line = codehem.find_by_xpath(sample_code, path)
        print(f"find_by_xpath for '{path}': lines {start_line}-{end_line}")
    
    # Step 4: Check XPath text retrieval directly
    print("\n---- XPath Text Retrieval Debug ----")
    for path in paths:
        text = codehem.get_text_by_xpath(sample_code, path)
        if text:
            print(f"XPath '{path}': Found - {len(text.split(chr(10)))} lines")
            print(f"  Content preview: {text[:50]}...")
        else:
            print(f"XPath '{path}': Not found")
    
    # Step 5: Debug if property decorator is correctly detected
    print("\n---- Property Pattern Detection ----")
    print("Is '@property' in code:", '@property' in sample_code)
    print("Is '@value.setter' in code:", '@value.setter' in sample_code)
    
    # Step 6: Check how the PythonLanguageService handles XPath
    print("\n---- Language Service XPath Testing ----")
    for path in paths:
        xpath_nodes = XPathParser.parse(path)
        print(f"XPath '{path}' parsed into {len(xpath_nodes)} nodes:")
        for i, node in enumerate(xpath_nodes):
            print(f"  Node {i+1}: name='{node.name}', type='{node.type}'")
        
        # Try to get text directly using the language service
        result = codehem.language_service.get_text_by_xpath_internal(sample_code, xpath_nodes)
        print(f"  Result: {'Found' if result else 'Not found'}")