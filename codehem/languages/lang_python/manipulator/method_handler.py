"""
Python method manipulator implementation.
"""
import logging
from typing import Optional
from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.core.manipulators.template_method_manipulator import TemplateMethodManipulator

logger = logging.getLogger(__name__)

# @manipulator # Disabled: Using PythonASTManipulator via __init__.py registration
class PythonMethodManipulator(TemplateMethodManipulator):
    """Manipulator for Python methods."""
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.METHOD
    COMMENT_MARKERS = ['#']
    DECORATOR_MARKERS = ['@']
    
    def _determine_indent_level_for_addition(self, code: str, parent_name: Optional[str]=None) -> int:
        """Python methods are indented one level inside their parent class."""
        if not parent_name:
            return 0
            
        try:
            class_start, _ = self.extraction_service.find_element(
                code, CodeElementType.CLASS.value, parent_name)
                
            if class_start > 0:
                lines = code.splitlines()
                if class_start <= len(lines):
                    class_line = lines[class_start - 1]
                    class_indent = self.get_indentation(class_line)
                    indent_size = getattr(self.formatter, 'indent_size', 4)
                    return len(class_indent) // indent_size + 1
        except Exception as e:
            logger.debug(f"Error finding method indent level: {e}")
            
        return 1  # Default Python method indent