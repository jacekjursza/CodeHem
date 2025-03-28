"""
TypeScript method manipulator implementation.
"""
import logging
import re
from typing import Optional
from codehem.models.enums import CodeElementType
from codehem.core.registry import manipulator
from codehem.core.manipulators.template_method_manipulator import TemplateMethodManipulator
from codehem.languages.lang_typescript.manipulator.base import TypeScriptManipulatorBase

logger = logging.getLogger(__name__)

@manipulator
class TypeScriptMethodManipulator(TypeScriptManipulatorBase, TemplateMethodManipulator):
    """Manipulator for TypeScript methods."""
    ELEMENT_TYPE = CodeElementType.METHOD
    
    def add_element(self, original_code: str, new_element: str, parent_name: Optional[str]=None) -> str:
        """Add a method to a TypeScript class."""
        if not parent_name:
            logger.error("Cannot add method without parent class name.")
            return original_code
            
        try:
            # Find the parent class
            class_pattern = rf'class\s+{re.escape(parent_name)}\s*{{[^}}]*}}'
            class_match = re.search(class_pattern, original_code, re.DOTALL)
            if not class_match:
                logger.error(f"Parent class '{parent_name}' not found.")
                return original_code
                
            class_content = class_match.group(0)
            class_start_pos = class_match.start()
            class_end_pos = class_match.end()
            
            # Find the insertion point inside the class (before the closing brace)
            closing_brace_pos = class_content.rfind('}')
            if closing_brace_pos == -1:
                logger.error(f"Malformed class '{parent_name}', no closing brace found.")
                return original_code
                
            # Calculate the proper indentation
            lines = class_content.splitlines()
            if len(lines) <= 1:
                indent = "    "  # Default indentation
            else:
                # Find the first non-empty line after the class declaration
                for i in range(1, len(lines)):
                    line = lines[i]
                    if line.strip():
                        indent = re.match(r'^(\s*)', line).group(1)
                        break
                else:
                    indent = "    "  # Default indentation
            
            # Format the method with proper indentation
            formatted_method = self.format_element(new_element, indent_level=1)
            
            # Insert the method
            insertion_pos = class_start_pos + closing_brace_pos
            result = original_code[:insertion_pos]
            
            # Add a newline before the method if needed
            if not result.endswith('\n'):
                result += '\n'
                
            result += f"{indent}{formatted_method.lstrip()}\n{' ' * (len(indent) - 2)}}}".rstrip() + original_code[class_end_pos:]
            
            return result
            
        except Exception as e:
            logger.error(f"Error adding method to class: {e}")
            return original_code