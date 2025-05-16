"""
Example implementation showing how to use the input validation framework in CodeHem.

This module demonstrates practical applications of the validation framework
across different components of the CodeHem codebase.
"""
from typing import Dict, List, Optional, Union, Any, cast

from codehem.core.error_handling import ValidationError
from codehem.core.error_context import error_context, with_error_context
from codehem.core.input_validation import (
    validate_params,
    validate_return,
    validate_type,
    validate_not_empty,
    validate_dict_schema,
    create_schema_validator
)
from codehem.models.code_element import CodeElement, CodeElementsResult
from codehem.models.enums import CodeElementType


# Example 1: Using validate_params decorator for a public API function
@validate_params(
    code={"type": str, "not_empty": True},
    element_type={"type": str, "one_of": [e.value for e in CodeElementType]},
    element_name={"type": str, "optional": True},
    parent_name={"type": str, "optional": True}
)
def find_element(code: str, element_type: str, 
                element_name: Optional[str] = None, 
                parent_name: Optional[str] = None) -> tuple:
    """
    Find the line range of a code element.
    
    Args:
        code: The source code to search
        element_type: The type of element to find
        element_name: Optional name of the element to find
        parent_name: Optional name of the parent element
        
    Returns:
        A tuple containing the start and end line numbers
    """
    # Implementation would go here
    # For this example, we'll return a dummy result
    return (10, 20)


# Example 2: Using validate_params with context-aware error handling
@with_error_context('extraction', component='Python', operation='extract_class')
@validate_params(
    code={"type": str, "not_empty": True},
    class_name={"type": str, "optional": True},
    include_members={"type": bool, "optional": True}
)
def extract_class(code: str, class_name: Optional[str] = None, 
                 include_members: bool = True) -> Dict[str, Any]:
    """
    Extract a class definition from Python code.
    
    Args:
        code: The Python source code
        class_name: Optional name of the class to extract (extracts first class if None)
        include_members: Whether to include class members in the result
        
    Returns:
        A dictionary containing the extracted class information
    """
    with error_context('parsing', code_snippet=code[:100]):
        # Implementation would go here
        # For this example, we'll return a dummy result
        result = {
            "type": "class",
            "name": class_name or "ExampleClass",
            "line_range": (1, 20),
            "members": [] if include_members else None
        }
        
        return result


# Example 3: Using schema validation for complex data structures
element_schema = {
    "type": {"type": str, "required": True, "one_of": [e.value for e in CodeElementType]},
    "name": {"type": str, "required": True, "not_empty": True},
    "content": {"type": str, "required": True},
    "range": {"type": dict, "required": True, "schema": {
        "start_line": {"type": int, "required": True, "min_value": 1},
        "end_line": {"type": int, "required": True, "min_value": 1},
        "start_column": {"type": int, "required": False, "min_value": 0},
        "end_column": {"type": int, "required": False, "min_value": 0}
    }},
    "parent_name": {"type": str, "required": False},
    "children": {"type": list, "required": False, "item_validator": {
        "type": dict,  # This would be a recursive reference to the same schema,
                       # but we simplify here for the example
    }}
}

element_validator = create_schema_validator(element_schema)


def process_element(element: Dict[str, Any]) -> CodeElement:
    """
    Process a dictionary containing element data into a CodeElement.
    
    Args:
        element: Dictionary of element data
        
    Returns:
        A CodeElement instance
    """
    # Validate the element structure
    element_validator(element, "element")
    
    # Process the validated element
    # Implementation would convert the dictionary to a CodeElement
    # For this example, we'll use a simple construction
    return CodeElement(
        type=element["type"],
        name=element["name"],
        content=element["content"],
        range=element["range"],
        parent_name=element.get("parent_name"),
        children=[]  # Simplified for example
    )


# Example 4: Integrating validation with error context for better debugging
@with_error_context('manipulation', component='ManipulationService', operation='add_element')
@validate_params(
    original_code={"type": str, "not_empty": True},
    element_type={"type": str, "one_of": [e.value for e in CodeElementType]},
    new_code={"type": str, "not_empty": True},
    parent_name={"type": str, "optional": True},
    options={"type": dict, "optional": True, "schema": {
        "insert_blank_line_before": {"type": bool, "optional": True},
        "insert_blank_line_after": {"type": bool, "optional": True},
        "keep_indentation": {"type": bool, "optional": True}
    }}
)
def add_element(original_code: str, element_type: str, new_code: str,
               parent_name: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> str:
    """
    Add a new element to existing code.
    
    Args:
        original_code: The original source code
        element_type: The type of element to add
        new_code: The code for the new element
        parent_name: Optional name of the parent element
        options: Optional dictionary of additional options
        
    Returns:
        The modified source code
    """
    with error_context('preparation', code_sample=original_code[:100], new_element=new_code[:100]):
        # Preparation steps...
        pass
    
    with error_context('insertion', element_type=element_type, parent=parent_name):
        # Insertion steps...
        # For this example, we'll simply append the new code
        result = original_code
        
        if parent_name:
            # If we have a parent, we'd find it and insert the code in the right place
            # Simplified for example:
            result += f"\n\n# New {element_type} added to {parent_name}\n{new_code}"
        else:
            # Otherwise add at the end
            result += f"\n\n# New {element_type} added\n{new_code}"
        
        return result


# Example 5: Using validation for return values
@validate_return({
    "type": CodeElementsResult,
    "custom_validator": lambda result, _: (
        validate_not_empty(result.elements, "result.elements") 
        if hasattr(result, 'elements') else None
    )
})
def extract_all_elements(code: str) -> CodeElementsResult:
    """
    Extract all code elements from source code.
    
    Args:
        code: The source code to analyze
        
    Returns:
        A CodeElementsResult containing all extracted elements
    """
    # Implementation would go here
    # For this example, we'll return a dummy result
    return CodeElementsResult(elements=[
        CodeElement(
            type=CodeElementType.CLASS.value,
            name="ExampleClass",
            content="class ExampleClass:\n    pass",
            range={"start_line": 1, "end_line": 2}
        )
    ])


# Example 6: Direct validation in a function
def parse_xpath(xpath: str) -> List[Dict[str, str]]:
    """
    Parse an XPath-like expression into a list of node descriptors.
    
    Args:
        xpath: The XPath-like expression
        
    Returns:
        A list of dictionaries representing the path nodes
    """
    # Input validation
    validate_type(xpath, str, "xpath")
    validate_not_empty(xpath, "xpath")
    
    # Implementation would go here
    # For this example, we'll return a dummy result
    if '.' in xpath:
        parts = xpath.split('.')
        return [{"name": part, "type": "generic"} for part in parts if part]
    else:
        return [{"name": xpath, "type": "generic"}]


# Example of handling validation errors
def example_error_handling():
    """Example showing how to handle validation errors."""
    try:
        # This will raise a validation error
        result = find_element("", "invalid_type")
    except ValidationError as e:
        print(f"Validation error: {e}")
        print(f"Parameter: {e.parameter}")
        print(f"Value: {e.value}")
        print(f"Expected: {e.expected}")
        
        # We can also check specific error types
        from codehem.core.error_handling import (
            InvalidParameterError,
            InvalidTypeError,
            MissingParameterError
        )
        
        if isinstance(e, InvalidParameterError):
            print("The parameter's value is invalid")
        elif isinstance(e, InvalidTypeError):
            print("The parameter's type is incorrect")
        elif isinstance(e, MissingParameterError):
            print("A required parameter is missing")
