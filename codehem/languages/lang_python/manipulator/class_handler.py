"""
Python class manipulator implementation.
"""
import logging
from typing import Optional
from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.core.manipulators.template_class_manipulator import TemplateClassManipulator

logger = logging.getLogger(__name__)

@manipulator
class PythonClassManipulator(TemplateClassManipulator):
    """Manipulator for Python classes."""
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.CLASS
    COMMENT_MARKERS = ['#']
    DECORATOR_MARKERS = ['@']
    
    def _perform_insertion(self, code: str, formatted_element: str, insertion_point: int, 
                          parent_name: Optional[str]=None) -> str:
        """Add a class to Python code with appropriate spacing."""
        if not code:
            return formatted_element + '\n'
            
        result = super()._perform_insertion(code, formatted_element, insertion_point, parent_name)
        
        # Ensure proper spacing and newline at end
        if not result.endswith('\n'):
            result += '\n'
            
        return result