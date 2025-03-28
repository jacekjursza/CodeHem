"""
Template implementation for function manipulator.
"""
import logging
from typing import Optional
from codehem.core.template_manipulator import TemplateManipulator
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

class TemplateFunctionManipulator(TemplateManipulator):
    """Template implementation for function manipulation."""
    ELEMENT_TYPE = CodeElementType.FUNCTION
    
    def _find_insertion_point(self, code: str, parent_name: Optional[str]=None) -> int:
        """Functions typically go after imports and classes."""
        lines = code.splitlines()
        
        # Find the last class or import
        last_class_line = 0
        last_import_line = 0
        
        in_class = False
        class_indent = ""
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            indent = self.get_indentation(line)
            
            if stripped.startswith(('import ', 'from ')):
                last_import_line = i
            
            if stripped.startswith('class '):
                in_class = True
                class_indent = indent
                last_class_line = i
            
            # Check if we're outside a class definition
            if in_class and indent <= class_indent and stripped and not stripped.startswith(('#', '@')):
                in_class = False
                last_class_line = i
        
        # Insert after the last class or import
        insertion_point = max(last_class_line, last_import_line)
        if insertion_point > 0:
            # Skip to the end of the last entity
            while insertion_point < len(lines):
                if not lines[insertion_point].strip():
                    break
                insertion_point += 1
                
            return insertion_point
        
        # Default: append to file
        return len(lines)