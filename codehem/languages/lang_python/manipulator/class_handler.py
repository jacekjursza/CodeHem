"""
Python class manipulator implementation.
"""
import logging
from typing import Optional, Tuple

from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.languages.lang_python.manipulator.base import PythonManipulatorBase

logger = logging.getLogger(__name__)

@manipulator
class PythonClassManipulator(PythonManipulatorBase):
    """Manipulator for Python classes."""
    ELEMENT_TYPE = CodeElementType.CLASS

    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add a class to Python code."""
        # Classes don't need parent context, always top-level
        formatted_class = self.format_element(new_element, indent_level=0)

        # Append with appropriate spacing
        if original_code:
            if original_code.endswith('\n\n'):
                return original_code + formatted_class + '\n'
            elif original_code.endswith('\n'):
                return original_code + '\n' + formatted_class + '\n'
            else:
                return original_code + '\n\n' + formatted_class + '\n'
        else:
            return formatted_class + '\n'