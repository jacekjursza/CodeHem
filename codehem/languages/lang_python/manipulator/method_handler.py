"""
Python method manipulator implementation.
"""
import logging
from typing import Optional, Tuple

from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.languages.lang_python.manipulator.base import PythonManipulatorBase

logger = logging.getLogger(__name__)

@manipulator
class PythonMethodManipulator(PythonManipulatorBase):
    """Manipulator for Python methods."""
    ELEMENT_TYPE = CodeElementType.METHOD

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add a method to a Python class."""
        if not parent_name:
            logger.error("Cannot add method without parent class name.")
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

        # Calculate indentation based on parent class
        method_indent_level = self.get_element_indent_level(original_code, class_start, parent_name)
        formatted_method = self.format_element(new_element, method_indent_level)

        # Determine insertion point (typically end of class)
        lines = original_code.splitlines()
        insertion_point = class_end
        if insertion_point > len(lines):
            insertion_point = len(lines)

        # Insert method with appropriate spacing
        result_lines = lines[:insertion_point]
        if result_lines and result_lines[-1].strip():
            result_lines.append('')  # Add blank line before method if needed
        result_lines.append(formatted_method)
        result_lines.extend(lines[insertion_point:])

        return '\n'.join(result_lines)