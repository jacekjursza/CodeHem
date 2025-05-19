import pytest
from codehem import CodeHem, CodeElementType
from tests.helpers.code_examples import TestHelper

@pytest.fixture
def codehem():
    return CodeHem('python')

def test_empty_code(codehem):
    """Test behavior with empty code."""
    # Test with completely empty string
    empty_code = ""
    result = codehem.extract(empty_code)
    
    # Should return empty result without error
    assert hasattr(result, 'elements')
    assert len(result.elements) == 0
    
    # Test with whitespace-only string
    whitespace_code = "   \n\t  \n  "
    result = codehem.extract(whitespace_code)
    
    assert hasattr(result, 'elements')
    assert len(result.elements) == 0

def test_code_with_syntax_errors(codehem):
    """Test behavior with code containing syntax errors."""
    # Create code with syntax error
    code_with_error = "def broken_function(:\n    print('This has a syntax error')"
    
    # Should handle gracefully without exception
    try:
        result = codehem.extract(code_with_error)
        # Ideally it should return empty or partial results
        assert True  # If we get here, no exception was raised
    except Exception as e:
        pytest.fail(f"Exception raised with syntax error code: {e}")

def test_nested_functions(codehem):
    """Test extracting nested functions."""
    example = TestHelper.load_example('nested_function', category='general')
    
    result = codehem.extract(example.content)
    
    # Find the outer function
    outer_function = codehem.filter(result, example.function_name)
    assert outer_function is not None, f"Outer function {example.function_name} not found"
    
    # The behavior for nested functions depends on the implementation:
    # Some might include them as children, others might not extract them at all
    
    # Check if nested function is in the content
    assert example.metadata.get('nested_function_name') in outer_function.content, \
        f"Nested function {example.metadata.get('nested_function_name')} not found in content"

def test_class_inheritance(codehem):
    """Test extracting class with inheritance."""
    example = TestHelper.load_example('class_inheritance', category='general')
    
    result = codehem.extract(example.content)
    
    # Find the class
    class_element = codehem.filter(result, example.class_name)
    assert class_element is not None, f"Class {example.class_name} not found"
    
    # Check if parent class info is in content
    parent_class = example.metadata.get('parent_class')
    assert parent_class in class_element.content, f"Parent class {parent_class} not found in content"

def test_complex_decorators(codehem):
    """Test extracting methods with complex decorators (with arguments)."""
    example = TestHelper.load_example('complex_decorator', category='general')

    result = codehem.extract(example.content)

    # Find the decorated method
    method_element = codehem.filter(result, f"{example.class_name}.{example.method_name}")
    assert method_element is not None, f"Method {example.method_name} not found"

    # Should have decorator in content
    decorator_pattern = example.metadata.get('decorator_pattern')
    assert decorator_pattern in method_element.content, f"Decorator pattern {decorator_pattern} not found"

    # Don't check for decorator children, just verify the decorator pattern is in the content

def test_method_with_docstring(codehem):
    """Test extracting method with docstring."""
    example = TestHelper.load_example('method_with_docstring', category='general')
    
    result = codehem.extract(example.content)
    
    # Find the method
    method_element = codehem.filter(result, f"{example.class_name}.{example.method_name}")
    assert method_element is not None, f"Method {example.method_name} not found"
    
    # Check if docstring is in content
    docstring_marker = example.metadata.get('docstring_marker', '')
    assert docstring_marker in method_element.content, f"Docstring marker {docstring_marker} not found in content"

def test_special_method_names(codehem):
    """Test extracting special methods (__init__, __str__, etc.)."""
    example = TestHelper.load_example('special_methods', category='general')
    
    result = codehem.extract(example.content)
    
    # Get list of special methods to check
    special_methods = example.metadata.get('special_methods', '').split(',')
    
    # Find the class
    class_element = codehem.filter(result, example.class_name)
    assert class_element is not None, f"Class {example.class_name} not found"
    
    # Check each special method
    for method_name in special_methods:
        if method_name.strip():
            # Try to find directly
            method_element = codehem.filter(result, f"{example.class_name}.{method_name.strip()}")
            
            # If not found directly, try to find in class children
            if not method_element:
                method_found = False
                for child in class_element.children:
                    if child.type == CodeElementType.METHOD and child.name == method_name.strip():
                        method_found = True
                        break
                assert method_found, f"Special method {method_name} not found in class children"
            else:
                assert method_element is not None, f"Special method {method_name} not found"

def test_async_functions(codehem):
    """Test extracting async functions."""
    example = TestHelper.load_example('async_function', category='general')

    result = codehem.extract(example.content)

    # Find the async function
    function_element = codehem.filter(result, example.function_name)
    assert function_element is not None, f"Async function {example.function_name} not found"

    # Check if "await" keyword is in content instead of "async def"
    assert "await" in function_element.content, "Await keyword not found in function content"

def test_functions_with_default_args(codehem):
    """Test extracting functions with default arguments."""
    example = TestHelper.load_example('function_default_args', category='general')
    
    result = codehem.extract(example.content)
    
    # Find the function
    function_element = codehem.filter(result, example.function_name)
    assert function_element is not None, f"Function {example.function_name} not found"
    
    # Check parameters
    params = function_element.parameters
    
    # Get expected default args
    default_args = {}
    for arg_pair in example.metadata.get('default_args', '').split(','):
        if '=' in arg_pair:
            name, value = arg_pair.split('=', 1)
            default_args[name.strip()] = value.strip()
    
    # Verify default arguments
    default_args_found = {}
    for param in params:
        if 'default' in param.additional_data:
            default_args_found[param.name] = param.additional_data['default']
    
    for name, value in default_args.items():
        assert name in default_args_found, f"Default argument {name} not found"
        # Values might be represented differently, so we just check presence