"""
Python-specific language service implementation.
"""
from typing import Dict, List, Optional, Tuple, Any
import re
from codehem import CodeElementType
from .service import LanguageService

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
        if re.match('class\\s+\\w+', code):
            return CodeElementType.CLASS.value
        if re.match('def\\s+\\w+', code):
            if re.search('def\\s+\\w+\\s*\\(\\s*(?:self|cls)[\\s,)]', code):
                return CodeElementType.METHOD.value
            return CodeElementType.FUNCTION.value
        if re.match('(?:import|from)\\s+\\w+', code):
            return CodeElementType.IMPORT.value
        if re.search('@property', code):
            return CodeElementType.PROPERTY.value
        return CodeElementType.UNKNOWN.value

    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
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
        if element_type == CodeElementType.FUNCTION.value:
            pattern = 'def\\s+' + re.escape(name) + '\\s*\\(.*?\\).*?(?=\\n(?:def|class)|\\Z)'
            match = re.search(pattern, original_code, re.DOTALL)
            if match:
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                return original_code + '\n\n' + new_code
        elif element_type == CodeElementType.CLASS.value:
            pattern = 'class\\s+' + re.escape(name) + '.*?(?=\\n(?:def|class)|\\Z)'
            match = re.search(pattern, original_code, re.DOTALL)
            if match:
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                return original_code + '\n\n' + new_code
        elif element_type == CodeElementType.METHOD.value and parent_name:
            class_pattern = 'class\\s+' + re.escape(parent_name) + '.*?:'
            class_match = re.search(class_pattern, original_code)
            if class_match:
                class_content_start = class_match.end()
                base_indent = '    '
                indented_code = '\n'.join((base_indent + line for line in new_code.split('\n')))
                method_pattern = base_indent + 'def\\s+' + re.escape(name) + '\\s*\\(.*?\\).*?(?=\\n' + base_indent + 'def|\\Z)'
                method_match = re.search(method_pattern, original_code[class_content_start:], re.DOTALL)
                if method_match:
                    method_start = class_content_start + method_match.start()
                    method_end = class_content_start + method_match.end()
                    return original_code[:method_start] + indented_code + original_code[method_end:]
                else:
                    next_elem = re.search('\\n(?:def|class)', original_code[class_content_start:])
                    if next_elem:
                        insert_point = class_content_start + next_elem.start()
                        return original_code[:insert_point] + '\n' + indented_code + original_code[insert_point:]
                    else:
                        return original_code + '\n' + indented_code
        return original_code