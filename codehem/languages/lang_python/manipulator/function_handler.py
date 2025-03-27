"""
Python function manipulator implementation.
"""
import logging
from typing import Optional, Tuple

from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.languages.lang_python.manipulator.base import PythonManipulatorBase

logger = logging.getLogger(__name__)

@manipulator
class PythonFunctionManipulator(PythonManipulatorBase):
    """Manipulator for Python functions."""
    ELEMENT_TYPE = CodeElementType.FUNCTION

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add a function to Python code."""
        # Top-level functions don't need parent context
        formatted_function = self.format_element(new_element, indent_level=0)

        # Append with appropriate spacing
        if original_code:
            if original_code.endswith('\n\n'):
                return original_code + formatted_function
            elif original_code.endswith('\n'):
                return original_code + '\n' + formatted_function
            else:
                return original_code + '\n\n' + formatted_function
        else:
            return formatted_function