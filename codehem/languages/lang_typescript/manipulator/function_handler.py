"""
TypeScript function manipulator implementation.
"""
import logging
import re
from typing import Optional
from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.core.manipulators.template_function_manipulator import TemplateFunctionManipulator
from codehem.languages.lang_typescript.manipulator.base import TypeScriptManipulatorBase

logger = logging.getLogger(__name__)

@manipulator
class TypeScriptFunctionManipulator(TypeScriptManipulatorBase, TemplateFunctionManipulator):
    """Manipulator for TypeScript functions."""
    ELEMENT_TYPE = CodeElementType.FUNCTION
    
    def find_element(self, code: str, element_name: str, parent_name: Optional[str]=None) -> tuple:
        """Find a function by name - handle both standard and arrow functions."""
        try:
            # Try standard extraction first
            start_line, end_line = super().find_element(code, element_name, parent_name)
            if start_line > 0:
                return start_line, end_line
        except Exception as e:
            logger.debug(f"Error finding function: {e}")
        
        # Try finding standard function via regex
        pattern = rf'function\s+{re.escape(element_name)}\s*\([^)]*\)[^{{]*{{[^}}]*}}'
        match = re.search(pattern, code, re.DOTALL)
        if match:
            start_pos = match.start()
            end_pos = match.end()
            start_line = code[:start_pos].count('\n') + 1
            end_line = code[:end_pos].count('\n') + 1
            return start_line, end_line
            
        # Try finding arrow function via regex
        pattern = rf'const\s+{re.escape(element_name)}\s*=\s*\([^)]*\)[^=]*=>\s*{{[^}}]*}}'
        match = re.search(pattern, code, re.DOTALL)
        if match:
            start_pos = match.start()
            end_pos = match.end()
            start_line = code[:start_pos].count('\n') + 1
            end_line = code[:end_pos].count('\n') + 1
            return start_line, end_line
            
        return 0, 0
        
    def replace_element(self, original_code: str, element_name: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Replace a function with a new version."""
        start_line, end_line = self.find_element(original_code, element_name, parent_name)
        if start_line == 0 and end_line == 0:
            # If the function isn't found, add it
            return self.add_element(original_code, new_element, parent_name)
            
        formatted_element = self.format_element(new_element)
        return self.replace_lines(original_code, start_line, end_line, formatted_element)