"""
Template implementation for class manipulator.
"""
import logging
from typing import Optional

from codehem.core.manipulators.template_manipulator import TemplateManipulator
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

class TemplateClassManipulator(TemplateManipulator):
    """Template implementation for class manipulation."""
    ELEMENT_TYPE = CodeElementType.CLASS
    
    def _perform_insertion(self, code: str, formatted_element: str, insertion_point: int, 
                          parent_name: Optional[str]=None) -> str:
        """Classes are typically added to the end of imports or at the file level."""
        lines = code.splitlines()
        
        # Find the last import statement
        last_import_line = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')):
                last_import_line = i
        
        # If we have imports, add after them with a blank line
        if last_import_line > 0:
            insertion_point = last_import_line + 1
            result_lines = lines[:insertion_point]
            if insertion_point < len(lines) and lines[insertion_point].strip():
                result_lines.append('')
            result_lines.append('')  # Extra blank line after imports
            result_lines.extend(formatted_element.splitlines())
            if insertion_point < len(lines):
                result_lines.append('')  # Blank line before next content
                result_lines.extend(lines[insertion_point:])
            return '\n'.join(result_lines)
        
        # Default behavior: append to end of file
        return super()._perform_insertion(code, formatted_element, insertion_point, parent_name)