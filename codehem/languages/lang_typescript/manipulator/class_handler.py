"""
TypeScript class manipulator implementation.
"""
import logging
from typing import Optional
from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.core.manipulators.template_class_manipulator import TemplateClassManipulator
from codehem.languages.lang_typescript.manipulator.base import TypeScriptManipulatorBase

logger = logging.getLogger(__name__)

@manipulator
class TypeScriptClassManipulator(TypeScriptManipulatorBase, TemplateClassManipulator):
    """Manipulator for TypeScript classes."""
    ELEMENT_TYPE = CodeElementType.CLASS
    
    def _perform_insertion(self, code: str, formatted_element: str, insertion_point: int, 
                          parent_name: Optional[str]=None) -> str:
        """Add a class to TypeScript code with appropriate spacing."""
        if not code:
            return formatted_element
            
        # Process class insertion with TypeScript-specific spacing and export handling
        lines = code.splitlines()
        result_lines = lines[:insertion_point]
        
        # Make sure there's a blank line before the class unless it's at the start
        if result_lines and result_lines[-1].strip():
            result_lines.append('')
            
        # Add the class
        result_lines.extend(formatted_element.splitlines())
        
        # Add the rest of the code with proper spacing
        if insertion_point < len(lines):
            if not lines[insertion_point].strip():
                # Skip blank line if already present
                insertion_point += 1
            result_lines.append('')  # Ensure blank line after class
            result_lines.extend(lines[insertion_point:])
            
        return '\n'.join(result_lines)