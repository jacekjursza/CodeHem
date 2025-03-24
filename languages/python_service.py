"""
Python-specific language service implementation.
"""
from typing import Dict, List, Optional, Tuple, Any
import re

from languages.service import LanguageService
from core.models import CodeElementType

class PythonLanguageService(LanguageService):
    """Python language service implementation."""
    
    def __init__(self):
        super().__init__('python')
        
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of Python code element.
        
        Args:
            code: The code to analyze
            
        Returns:
            Element type string (from CodeElementType)
        """
        code = code.strip()
        
        # Class definition
        if re.match(r'class\s+\w+', code):
            return CodeElementType.CLASS.value
            
        # Method or function
        if re.match(r'def\s+\w+', code):
            # Check for self or cls parameter
            if re.search(r'def\s+\w+\s*\(\s*(?:self|cls)[\s,)]', code):
                return CodeElementType.METHOD.value
            return CodeElementType.FUNCTION.value
            
        # Import statement
        if re.match(r'(?:import|from)\s+\w+', code):
            return CodeElementType.IMPORT.value
            
        # Property
        if re.search(r'@property', code):
            return CodeElementType.PROPERTY.value
            
        return CodeElementType.UNKNOWN.value
    
    def upsert_element(self, original_code: str, element_type: str, name: str, 
                     new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add or replace a Python code element.
        
        Args:
            original_code: Original source code
            element_type: Type of element to add/replace (from CodeElementType)
            name: Name of the element
            new_code: New content for the element
            parent_name: Name of parent element (e.g., class name for methods)
            
        Returns:
            Modified code
        """
        # For now, this is a simplified implementation
        # In a real implementation, we would use our manipulator classes
        
        if element_type == CodeElementType.FUNCTION.value:
            # Try to find the function
            pattern = r'def\s+' + re.escape(name) + r'\s*\(.*?\).*?(?=\n(?:def|class)|\Z)'
            match = re.search(pattern, original_code, re.DOTALL)
            
            if match:
                # Replace existing function
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                # Add new function at the end
                return original_code + '\n\n' + new_code
                
        elif element_type == CodeElementType.CLASS.value:
            # Try to find the class
            pattern = r'class\s+' + re.escape(name) + r'.*?(?=\n(?:def|class)|\Z)'
            match = re.search(pattern, original_code, re.DOTALL)
            
            if match:
                # Replace existing class
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                # Add new class at the end
                return original_code + '\n\n' + new_code
                
        elif element_type == CodeElementType.METHOD.value and parent_name:
            # Try to find the class
            class_pattern = r'class\s+' + re.escape(parent_name) + r'.*?:'
            class_match = re.search(class_pattern, original_code)
            
            if class_match:
                # Find the class body end
                class_content_start = class_match.end()
                
                # Indentation level of the method
                base_indent = '    '  # Assume 4 spaces for Python
                
                # Indent the new method
                indented_code = '\n'.join(base_indent + line for line in new_code.split('\n'))
                
                # Try to find the method within the class
                method_pattern = base_indent + r'def\s+' + re.escape(name) + r'\s*\(.*?\).*?(?=\n' + base_indent + r'def|\Z)'
                method_match = re.search(method_pattern, original_code[class_content_start:], re.DOTALL)
                
                if method_match:
                    # Replace existing method
                    method_start = class_content_start + method_match.start()
                    method_end = class_content_start + method_match.end()
                    return original_code[:method_start] + indented_code + original_code[method_end:]
                else:
                    # Add new method at the end of the class
                    # Find the next class or function, or the end of the file
                    next_elem = re.search(r'\n(?:def|class)', original_code[class_content_start:])
                    if next_elem:
                        insert_point = class_content_start + next_elem.start()
                        return original_code[:insert_point] + '\n' + indented_code + original_code[insert_point:]
                    else:
                        # Add at the end of the file
                        return original_code + '\n' + indented_code
        
        # If we couldn't handle it, return the original code
        return original_code