"""
Template implementation for method manipulator.
"""
import logging
from typing import Optional
from codehem.core.template_manipulator import TemplateManipulator
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

class TemplateMethodManipulator(TemplateManipulator):
    """Template implementation for method manipulation."""
    ELEMENT_TYPE = CodeElementType.METHOD
    
    def _find_insertion_point(self, code: str, parent_name: Optional[str]=None) -> int:
        """Methods require a parent class."""
        if not parent_name:
            logger.error("Cannot add method without parent class name.")
            return len(code.splitlines())
        
        try:
            class_start, class_end = self.extraction_service.find_element(
                code, CodeElementType.CLASS.value, parent_name)
            
            if class_start == 0:
                logger.error(f"Parent class '{parent_name}' not found.")
                return len(code.splitlines())
                
            return class_end
        except Exception as e:
            logger.error(f"Error finding parent class '{parent_name}': {e}")
            return len(code.splitlines())
            
    def _determine_indent_level_for_addition(self, code: str, parent_name: Optional[str]=None) -> int:
        """Method indentation level is derived from the parent class."""
        if not parent_name:
            return 0
            
        try:
            class_start, _ = self.extraction_service.find_element(
                code, CodeElementType.CLASS.value, parent_name)
                
            if class_start > 0:
                # Method should be indented one level deeper than the class
                return self.get_element_indent_level(code, class_start) + 1
        except Exception as e:
            logger.error(f"Error determining method indent level: {e}")
            
        return 1  # Default method indent