"""
JavaScript-specific language service implementation.
"""
from typing import Dict, List, Optional, Tuple, Any
import re
from codehem.models.enums import CodeElementType
from .service import LanguageService

class JavaScriptLanguageService(LanguageService):
    """JavaScript language service implementation."""

    def __init__(self):
        super().__init__('javascript')

    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of JavaScript code element.
        
        Args:
            code: The code to analyze
            
        Returns:
            Element type string (from CodeElementType)
        """
        code = code.strip()
        if re.match('class\\s+\\w+', code):
            return CodeElementType.CLASS.value
        if re.match('function\\s+\\w+', code):
            return CodeElementType.FUNCTION.value
        if re.match('(?:async\\s+)?(?:static\\s+)?(?:\\w+\\s*\\([^)]*\\))', code):
            return CodeElementType.METHOD.value
        if re.search('=>', code):
            return CodeElementType.FUNCTION.value
        if re.match('import\\s+', code):
            return CodeElementType.IMPORT.value
        return CodeElementType.UNKNOWN.value

    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add or replace a JavaScript code element.
        
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
            pattern = 'function\\s+' + re.escape(name) + '\\s*\\(.*?\\)\\s*{.*?}(?=\\n|$)'
            match = re.search(pattern, original_code, re.DOTALL)
            if match:
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                return original_code + '\n\n' + new_code
        elif element_type == CodeElementType.CLASS.value:
            pattern = 'class\\s+' + re.escape(name) + '.*?{.*?}(?=\\n|$)'
            match = re.search(pattern, original_code, re.DOTALL)
            if match:
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                return original_code + '\n\n' + new_code
        return original_code