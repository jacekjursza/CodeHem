"""
Python function manipulator implementation.
"""
import logging
from typing import Optional
from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.core.manipulators.template_function_manipulator import TemplateFunctionManipulator

logger = logging.getLogger(__name__)

@manipulator
class PythonFunctionManipulator(TemplateFunctionManipulator):
    """Manipulator for Python functions."""
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.FUNCTION
    COMMENT_MARKERS = ['#']
    DECORATOR_MARKERS = ['@']
    
    def _perform_insertion(self, code: str, formatted_element: str, insertion_point: int, 
                          parent_name: Optional[str]=None) -> str:
        """Add a function to Python code with proper spacing."""
        if not code:
            return formatted_element
            
        lines = code.splitlines()
        if insertion_point >= len(lines):
            # Appending to the end
            if code.endswith('\n\n'):
                return code + formatted_element
            elif code.endswith('\n'):
                return code + '\n' + formatted_element
            else:
                return code + '\n\n' + formatted_element
        else:
            # Inserting in the middle
            result_lines = lines[:insertion_point]
            if result_lines and result_lines[-1].strip():
                result_lines.append('')
            result_lines.append('')  # Extra blank line before function
            result_lines.extend(formatted_element.splitlines())
            result_lines.extend(lines[insertion_point:])
            return '\n'.join(result_lines)