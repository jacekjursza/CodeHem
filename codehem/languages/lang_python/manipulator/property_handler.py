"""
Python property manipulator implementation.
"""
import re
import logging
from typing import Optional, Tuple

from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.languages.lang_python.manipulator.base import PythonManipulatorBase

logger = logging.getLogger(__name__)

@manipulator
class PythonPropertyManipulator(PythonManipulatorBase):
    """Manipulator for Python properties."""
    ELEMENT_TYPE = CodeElementType.PROPERTY

    def format_element(self, element_code: str, indent_level: int=0) -> str:
        """Format a Python property, handling different property types."""
        # Determine if it's a decorated property or assignment property
        is_property_decorator = '@property' in element_code

        if is_property_decorator:
            return super().format_element(element_code, indent_level)
        else:
            # Simple property assignment formatting
            indent = ' ' * (self.formatter.indent_size if hasattr(self.formatter, 'indent_size') else 4) * indent_level
            return self.apply_indentation(element_code.strip(), indent)

    def find_element(self, code: str, property_name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """Find a property in Python code (handles multiple property types)."""
        if not parent_name:
            return (0, 0)
            
        es = self.extraction_service

        # Try different property types in order
        for prop_type in [
            CodeElementType.PROPERTY_GETTER, 
            CodeElementType.PROPERTY_SETTER,
            CodeElementType.STATIC_PROPERTY
        ]:
            start, end = es.find_element(code, prop_type.value, property_name, parent_name)
            if start > 0:
                return (start, end)

        # Fallback: Look for assignments in __init__
        class_start, class_end = es.find_element(code, CodeElementType.CLASS.value, parent_name)
        if class_start == 0:
            return (0, 0)

        lines = code.splitlines()
        in_init = False
        init_indent = ""
        
        for i in range(class_start-1, min(class_end, len(lines))):
            line = lines[i]
            line_indent = self.get_indentation(line)
            
            # Find __init__ method
            if line.strip().startswith("def __init__"):
                in_init = True
                init_indent = line_indent
                continue
                
            # Look for property assignment in __init__
            if (in_init and 
                line_indent > init_indent and 
                f"self.{property_name}" in line and 
                "=" in line):
                return (i+1, i+1)
                
            # Exit __init__ if we hit another method
            if (in_init and 
                line_indent == init_indent and 
                line.strip().startswith("def ")):
                in_init = False

        return (0, 0)

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add a property to a Python class."""
        if not parent_name:
            logger.error("Cannot add property without parent class name.")
            return original_code

        try:
            class_start, class_end = self.extraction_service.find_element(
                original_code, CodeElementType.CLASS.value, parent_name
            )
        except Exception as e:
            logger.error(f"Error finding parent class '{parent_name}': {e}")
            return original_code

        if class_start == 0:
            logger.error(f"Parent class '{parent_name}' not found.")
            return original_code

        # Format the property with appropriate indentation
        property_indent_level = self.get_element_indent_level(original_code, class_start, parent_name)
        formatted_property = self.format_element(new_element, property_indent_level)
        
        # Decide where to insert the property
        lines = original_code.splitlines()
        is_property_decorator = '@property' in new_element
        
        if is_property_decorator:
            # Add decorated properties at the end of the class
            insertion_point = class_end
        else:
            # Add regular properties near the top, after class definition and docstring
            insertion_point = class_start
            in_docstring = False
            docstring_marker = None
            
            # Check for docstring after class definition
            if class_start < len(lines):
                first_line = lines[class_start].strip()
                if first_line.startswith(('"""', "'''")):
                    in_docstring = True
                    docstring_marker = first_line[:3]
            
            # Look for appropriate insertion point
            for i in range(class_start, min(class_end, len(lines))):
                line = lines[i].strip()
                
                # Skip docstring lines
                if in_docstring:
                    if docstring_marker in line and i > class_start:
                        in_docstring = False
                    continue
                
                # Insert before first method or non-property line
                if line and not line.startswith('#'):
                    if line.startswith('def ') or not ('=' in line and line.split('=')[0].strip().isidentifier()):
                        insertion_point = i
                        break

        # Insert the property with appropriate spacing
        result_lines = lines[:insertion_point]
        if result_lines and result_lines[-1].strip():
            result_lines.append('')  # Add blank line before property if needed
            
        result_lines.extend(formatted_property.splitlines())
        
        if insertion_point < min(class_end, len(lines)) and lines[insertion_point].strip():
            result_lines.append('')  # Add blank line after property if needed
            
        result_lines.extend(lines[insertion_point:])
        
        return '\n'.join(result_lines)