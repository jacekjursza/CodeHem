import re
from typing import Optional, Tuple

from codehem.models.enums import CodeElementType
from codehem.core.registry import handler
from codehem.languages.lang_python.manipulator.base import PythonBaseManipulator
from codehem.core.finder.factory import get_code_finder

@handler
class PythonMethodManipulator(PythonBaseManipulator):
    language_code = 'python'
    element_type = CodeElementType.METHOD
    
    def __init__(self):
        self.finder = get_code_finder('python')
    
    def format_element(self, element_code: str, indent_level: int = 0) -> str:
        """Format a Python method definition"""
        # Methods in Python classes are indented one level inside the class
        indent = ' ' * (4 * indent_level)
        lines = element_code.strip().splitlines()
        if not lines:
            return ''
            
        result = []
        method_line_idx = next((i for i, line in enumerate(lines) 
                              if line.strip().startswith('def ')), 0)
        
        # Add any lines before the method definition (like decorators)
        for i in range(method_line_idx):
            result.append(f"{indent}{lines[i].strip()}")
            
        # Add the method definition line
        result.append(f"{indent}{lines[method_line_idx].strip()}")
        
        method_indent = indent + '    '  # 4 spaces for method body
        
        # Process the method body with proper indentation
        for i in range(method_line_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                result.append('')
                continue
                
            result.append(f"{method_indent}{line}")
            
        return '\n'.join(result)
    
    def find_element(self, code: str, method_name: str, 
                    parent_name: Optional[str] = None) -> Tuple[int, int]:
        """Find a method in Python code"""
        if not parent_name:
            # Try to determine the parent class from the code
            parent_name = self.finder.find_class_for_method(method_name, code)
            if not parent_name:
                return 0, 0
        
        return self.finder.find_method(code, parent_name, method_name)
    
    def replace_element(self, original_code: str, method_name: str, 
                       new_element: str, parent_name: Optional[str] = None) -> str:
        """Replace a method in Python code"""
        # Get the line range for the method
        start_line, end_line = self.find_element(original_code, method_name, parent_name)
        if start_line == 0 and end_line == 0:
            if parent_name:
                return self.add_element(original_code, new_element, parent_name)
            return original_code
            
        # Handle decorators
        lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and not line.startswith('#'):
                break
        
        # Calculate proper indentation
        # For methods, we need to match the class indentation + 1 level
        class_line = 0
        if parent_name:
            class_start, _ = self.finder.find_class(original_code, parent_name)
            if class_start > 0:
                class_line = class_start - 1
        
        class_indent = ''
        if class_line < len(lines):
            class_indent = self.get_indentation(lines[class_line])
        
        method_indent_level = (len(class_indent) // 4) + 1
        
        # Format the new method definition
        formatted_method = self.format_element(new_element, method_indent_level)
        
        # Replace the method in the original code
        return self.replace_lines(original_code, adjusted_start, end_line, formatted_method)
        
    def add_element(self, original_code: str, new_element: str,
                   parent_name: Optional[str] = None) -> str:
        """Add a method to a Python class"""
        if not parent_name:
            return original_code
            
        # Find the class
        class_start, class_end = self.finder.find_class(original_code, parent_name)
        if class_start == 0:
            return original_code
            
        lines = original_code.splitlines()
        class_indent = ''
        if class_start - 1 < len(lines):
            class_indent = self.get_indentation(lines[class_start - 1])
            
        method_indent_level = (len(class_indent) // 4) + 1
        formatted_method = self.format_element(new_element, method_indent_level)
        
        # Determine where to insert the method in the class
        # Usually at the end of the class, but before the end of the file
        insertion_point = class_end
        if insertion_point > len(lines):
            insertion_point = len(lines)
            
        # Make sure there's a blank line between the last method and this one
        result_lines = lines[:insertion_point]
        if result_lines and result_lines[-1].strip():
            result_lines.append('')
            
        result_lines.append(formatted_method)
        result_lines.extend(lines[insertion_point:])
        
        return '\n'.join(result_lines)
        
    def remove_element(self, original_code: str, method_name: str,
                      parent_name: Optional[str] = None) -> str:
        """Remove a method from a Python class"""
        start_line, end_line = self.find_element(original_code, method_name, parent_name)
        if start_line == 0 and end_line == 0:
            return original_code
            
        # Handle decorators
        lines = original_code.splitlines()
        adjusted_start = start_line
        for i in range(start_line - 2, -1, -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if line.startswith('@'):
                adjusted_start = i + 1
            elif line and not line.startswith('#'):
                break
                
        return self.replace_lines(original_code, adjusted_start, end_line, '')