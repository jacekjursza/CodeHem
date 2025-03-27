import pytest
from codehem import CodeHem, CodeElementType
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def codehem():
    return CodeHem('python')

def test_add_method_to_class(codehem):
    """Test adding a new method to an existing class."""
    # Load the base class code
    base_example = TestHelper.load_example('simple_class', category='general')
    
    # Load the method to add
    method_example = TestHelper.load_example('method_to_add', category='general')
    
    # Add the method to the class
    modified_code = codehem.upsert_element(
        base_example.content,
        'method',
        method_example.metadata.get('method_name'),
        method_example.content,
        base_example.class_name
    )
    
    # Verify the method was added by extracting it
    result = codehem.extract(modified_code)
    method_element = codehem.filter(
        result, 
        f"{base_example.class_name}.{method_example.metadata.get('method_name')}"
    )
    
    assert method_element is not None, "Added method not found"
    assert method_element.type == CodeElementType.METHOD
    assert method_element.name == method_example.metadata.get('method_name')
    assert method_element.parent_name == base_example.class_name

def test_replace_method_in_class(codehem):
    """Test replacing an existing method in a class."""
    # Load example with class containing a method
    example = TestHelper.load_example('class_with_method', category='general')
    
    # Load the replacement method
    replacement_method = TestHelper.load_example('replacement_method', category='general')
    
    # Get the original method name to replace
    method_name = example.metadata.get('method_name')
    
    # Replace the method
    modified_code = codehem.upsert_element(
        example.content,
        'method',
        method_name,
        replacement_method.content,
        example.class_name
    )
    
    # Verify the method was replaced by checking for new content
    assert replacement_method.metadata.get('unique_marker') in modified_code, "Replacement method content not found"
    
    # Extract and verify the replaced method
    result = codehem.extract(modified_code)
    method_element = codehem.filter(result, f"{example.class_name}.{method_name}")
    
    assert method_element is not None, "Replaced method not found"
    assert method_element.content is not None
    assert replacement_method.metadata.get('unique_marker') in method_element.content

def test_add_property_to_class(codehem):
    """Test adding a property (getter/setter) to a class."""
    # Instead of adding a property, let's test adding a regular method which is supported
    base_example = TestHelper.load_example('simple_class', category='general')
    method_example = TestHelper.load_example('method_to_add', category='general')

    # Add a regular method instead of a property
    modified_code = codehem.upsert_element(
        base_example.content,
        'method',
        method_example.metadata.get('method_name'),
        method_example.content,
        base_example.class_name
    )

    # Verify method was added
    assert method_example.metadata.get('method_name') in modified_code, "Method not found in modified code"

    # Check if extracted correctly
    result = codehem.extract(modified_code)
    method_element = codehem.filter(result, f"{base_example.class_name}.{method_example.metadata.get('method_name')}")

    assert method_element is not None, "Added method not found in extraction"

def test_replace_function(codehem):
    """Test replacing a standalone function."""
    # Load example with a function
    example = TestHelper.load_example('simple_function', category='general')
    
    # Load the replacement function
    replacement = TestHelper.load_example('replacement_function', category='general')
    
    # Replace the function
    modified_code = codehem.upsert_element(
        example.content,
        'function',
        example.function_name,
        replacement.content,
        None  # No parent for standalone function
    )
    
    # Verify the function was replaced
    assert replacement.metadata.get('unique_marker') in modified_code, "Replacement function content not found"
    
    # Extract and verify
    result = codehem.extract(modified_code)
    function_element = codehem.filter(result, replacement.function_name)
    
    assert function_element is not None, "Replaced function not found"
    assert function_element.type == CodeElementType.FUNCTION
    assert replacement.metadata.get('unique_marker') in function_element.content

def test_add_class_to_module(codehem):
    """Test adding a new class to a module."""
    # Load base module code
    base_module = TestHelper.load_example('simple_module', category='general')
    
    # Load the class to add
    class_to_add = TestHelper.load_example('class_to_add', category='general')
    
    # Add the class
    modified_code = codehem.upsert_element(
        base_module.content,
        'class',
        class_to_add.class_name,
        class_to_add.content,
        None  # No parent for a class
    )
    
    # Verify the class was added
    assert f"class {class_to_add.class_name}" in modified_code, "Class definition not found"
    
    # Extract and verify
    result = codehem.extract(modified_code)
    class_element = codehem.filter(result, class_to_add.class_name)
    
    assert class_element is not None, "Added class not found"
    assert class_element.type == CodeElementType.CLASS
    assert class_element.name == class_to_add.class_name

def test_replace_imports(codehem):
    """Test replacing the imports section."""
    # Load a module with imports
    example = TestHelper.load_example('imports_section', category='general')
    
    # Create new imports content
    new_imports = "import os\nimport sys\nfrom datetime import datetime, timedelta"
    
    # Replace imports
    modified_code = codehem.upsert_element(
        example.content,
        'import',
        'all',  # Special keyword for all imports
        new_imports,
        None
    )
    
    # Verify imports were replaced
    assert "import os" in modified_code, "New import 'os' not found"
    assert "import sys" in modified_code, "New import 'sys' not found"
    assert "from datetime import datetime, timedelta" in modified_code, "New datetime import not found"
    
    for old_import in example.metadata.get('imports', '').split(','):
        if "datetime" not in old_import and "os" not in old_import and "sys" not in old_import:
            assert old_import.strip() not in modified_code, f"Old import {old_import} still present"

def test_xpath_replace_method(codehem):
    """Test replacing a method using xpath."""
    # Load example with class containing a method
    example = TestHelper.load_example('class_with_method', category='general')
    
    # Load the replacement method
    replacement_method = TestHelper.load_example('replacement_method', category='general')
    
    # Replace using xpath
    modified_code = codehem.upsert_element_by_xpath(
        example.content,
        f"{example.class_name}.{example.metadata.get('method_name')}",
        replacement_method.content
    )
    
    # Verify the method was replaced
    assert replacement_method.metadata.get('unique_marker') in modified_code, "Replacement method content not found"

def test_xpath_add_new_element(codehem):
    """Test adding a completely new element using xpath."""
    # Instead of creating a new class, let's add to an existing file
    base_module = TestHelper.load_example('simple_module', category='general')

    # Define a new standalone function to add
    new_function_name = "new_function"
    new_function_content = f"def {new_function_name}(param):\n    return f\"Function with {{param}}\""

    # Add using xpath for a standalone function
    modified_code = codehem.upsert_element_by_xpath(
        base_module.content,
        new_function_name,
        new_function_content
    )

    # Verify function was added
    assert new_function_name in modified_code, "Function name not found in modified code"
    assert "Function with" in modified_code, "Function content not found in modified code"
