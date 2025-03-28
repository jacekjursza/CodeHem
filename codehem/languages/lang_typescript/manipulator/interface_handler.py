"""
TypeScript interface manipulator implementation.
"""
import logging
import re
from typing import Optional
from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.core.template_manipulator import TemplateManipulator
from codehem.languages.lang_typescript.manipulator.base import TypeScriptManipulatorBase

logger = logging.getLogger(__name__)

@manipulator
class TypeScriptInterfaceManipulator(TypeScriptManipulatorBase):
    """Manipulator for TypeScript interfaces."""
    ELEMENT_TYPE = CodeElementType.INTERFACE
    
    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add an interface to TypeScript code."""
        # Interfaces go after imports but before classes
        lines = original_code.splitlines()
        
        # Find the last import statement
        last_import_line = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'import{', 'import {')):
                last_import_line = i
        
        # Format the interface
        formatted_interface = self.format_element(new_element)
        
        # If we found imports, insert after them with a blank line
        if last_import_line > 0:
            insertion_point = last_import_line + 1
            result_lines = lines[:insertion_point]
            if insertion_point < len(lines) and lines[insertion_point].strip():
                # Ensure blank line after imports
                result_lines.append('')
            result_lines.append('')  # Blank line before interface
            result_lines.extend(formatted_interface.splitlines())
            result_lines.append('')  # Blank line after interface
            result_lines.extend(lines[insertion_point:])
            return '\n'.join(result_lines)
        
        # If no imports, check where to insert the interface
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('class '):
                # Insert before the first class with blank lines
                result_lines = lines[:i]
                if result_lines and result_lines[-1].strip():
                    result_lines.append('')
                result_lines.extend(formatted_interface.splitlines())
                result_lines.append('')
                result_lines.extend(lines[i:])
                return '\n'.join(result_lines)
                
        # Otherwise just append to the end
        if original_code:
            if original_code.endswith('\n\n'):
                return original_code + formatted_interface
            elif original_code.endswith('\n'):
                return original_code + '\n' + formatted_interface
            else:
                return original_code + '\n\n' + formatted_interface
        else:
            return formatted_interface
            
    def find_element(self, code: str, element_name: str, parent_name: Optional[str]=None) -> tuple:
        """Find an interface by name."""
        # Try standard extraction first
        try:
            start_line, end_line = super().find_element(code, element_name, parent_name)
            if start_line > 0:
                return start_line, end_line
        except Exception as e:
            logger.debug(f"Error finding interface: {e}")
        
        # If not found, try regex search
        pattern = rf'interface\s+{re.escape(element_name)}\s*{{[^}}]*}}'
        match = re.search(pattern, code, re.DOTALL)
        if match:
            start_pos = match.start()
            end_pos = match.end()
            start_line = code[:start_pos].count('\n') + 1
            end_line = code[:end_pos].count('\n') + 1
            return start_line, end_line
            
        return 0, 0