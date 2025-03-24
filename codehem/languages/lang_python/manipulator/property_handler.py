import re
from typing import Optional, Tuple

from codehem.models.enums import CodeElementType
from codehem.core.registry import handler
from codehem.languages.lang_python.manipulator.base import PythonBaseHandler
from codehem.core.finder.factory import get_code_finder

@handler
class PythonPropertyHandler(PythonBaseHandler):
    language_code = 'python'
    element_type = CodeElementType.PROPERTY
    
    def __init__(self):
        self.finder = get_code_finder('python')
    
    def format_element(self, element_code: str, indent_level: int = 0) -> str:
        """Format a Python property definition"""
        indent = ' ' * (4 * indent_level)
        lines = element_code.strip().splitlines()
        if not lines:
            return ''
            
        result = []
        
        # Determine if this is a standard property or property decorator
        is_property_decorator = False
        for line in lines:
            if line.strip().startswith('@property'):
                is_property_decorator = True
                break
                
        if is_property_decorator:
            # Format as method with decorators
            decorator_lines = []
            method_line_idx = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith('@'):
                    decorator_lines.append(i)
                elif line.strip().startswith('def '):
                    method_line_idx = i
                    break
                    
            # Add decorators
            for i in decorator_lines:
                result.append(f"{indent}{lines[i].strip()}")
                
            # Add the method definition
            if method_line_idx >= 0:
                result.append(f"{indent}{lines[method_line_idx].strip()}")
                
                # Add method body with additional indentation
                method_indent = indent + '    '
                for i in range(method_line_idx + 1, len(lines)):
                    line = lines[i].strip()
                    if not line:
                        result.append('')
                        continue
                        
                    result.append(f"{method_indent}{line}")
        else:
            # Format as standard assignment property
            for line in lines:
                result.append(f"{indent}{line.strip()}")
                
        return '\n'.join(result)
    
    def find_element(self, code: str, property_name: str, 
                    parent_name: Optional[str] = None) -> Tuple[int, int]:
        """Find a property in Python code"""
        if not parent_name:
            return 0, 0
            
        # Check if this is a property getter/setter or a regular class attribute
        # First try to find it as a property decorator
        start_line, end_line = self.finder.find_property(code, parent_name, property_name)
        if start_line > 0:
            return start_line, end_line
            
        # If not found as a property decorator, look for it as a class attribute
        class_start, class_end = self.finder.find_class(code, parent_name)
        if class_start == 0:
            return 0, 0
            
        lines = code.splitlines()
        for i in range(class_start, class_end):
            if i >= len(lines):
                break
                
            # Look for self.property_name = ...
            if re.search(r'self\.' + re.escape(property_name) + r'\s*=', lines[i]):
                return i + 1, i + 1
                
        return 0, 0
    
    def replace_element(self, original_code: str, property_name: str, 
                       new_element: str, parent_name: Optional[str] = None) -> str:
        """Replace a property in Python code"""
        # Get the line range for the property
        start_line, end_line = self.find_element(original_code, property_name, parent_name)
        if start_line == 0 and end_line == 0:
            if parent_name:
                return self.add_element(original_code, new_element, parent_name)
            return original_code
            
        # Handle decorators for property methods
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
        # For properties, we need to match the class indentation + 1 level
        class_line = 0
        if parent_name:
            class_start, _ = self.finder.find_class(original_code, parent_name)
            if class_start > 0:
                class_line = class_start - 1
        
        class_indent = ''
        if class_line < len(lines):
            class_indent = self.get_indentation(lines[class_line])
        
        property_indent_level = (len(class_indent) // 4) + 1
        
        # Format the new property definition
        formatted_property = self.format_element(new_element, property_indent_level)
        
        # Replace the property in the original code
        return self.replace_lines(original_code, adjusted_start, end_line, formatted_property)
        
    def add_element(self, original_code: str, new_element: str,
                   parent_name: Optional[str] = None) -> str:
        """Add a property to a Python class"""
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
            
        property_indent_level = (len(class_indent) // 4) + 1
        formatted_property = self.format_element(new_element, property_indent_level)
        
        # Determine where to insert the property
        # For standard properties: after class definition, before first method
        # For property decorators: add at the end of the class like methods
        is_property_decorator = '@property' in new_element
        
        if is_property_decorator:
            # Add property decorator like methods, near the end of the class
            insertion_point = class_end
            if insertion_point > len(lines):
                insertion_point = len(lines)
                
            # Make sure there's a blank line between the last method and this one
            result_lines = lines[:insertion_point]
            if result_lines and result_lines[-1].strip():
                result_lines.append('')
                
            result_lines.append(formatted_property)
            result_lines.extend(lines[insertion_point:])
            
        else:
            # Add standard property after class definition, before first method
            # Find the first method or the end of the class
            found_init = False
            method_line = class_end
            
            for i in range(class_start, class_end):
                if i >= len(lines):
                    break
                    
                line = lines[i].strip()
                if line.startswith('def __init__'):
                    found_init = True
                elif found_init and line.startswith('self.'):
                    # This is inside __init__, skip
                    continue
                elif line.startswith('def '):
                    method_line = i
                    break
            
            # Insert before the first method or at the end of the class
            result_lines = lines[:method_line]
            
            # Add a blank line if needed
            if result_lines and result_lines[-1].strip() and result_lines[-1].strip() != ':':
                result_lines.append('')
                
            result_lines.append(formatted_property)
            
            # Add a blank line after the property if inserting before a method
            if method_line < class_end:
                result_lines.append('')
                
            result_lines.extend(lines[method_line:])
            
        return '\n'.join(result_lines)
        
    def remove_element(self, original_code: str, property_name: str,
                      parent_name: Optional[str] = None) -> str:
        """Remove a property from a Python class"""
        start_line, end_line = self.find_element(original_code, property_name, parent_name)
        if start_line == 0 and end_line == 0:
            return original_code
            
        # Handle decorators for property methods
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