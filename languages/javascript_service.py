"""
JavaScript-specific language service implementation.
"""
from typing import Dict, List, Optional, Tuple, Any
import re

from languages.service import LanguageService
from core.models import CodeElementType

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
        
        # Class definition
        if re.match(r'class\s+\w+', code):
            return CodeElementType.CLASS.value
            
        # Function
        if re.match(r'function\s+\w+', code):
            return CodeElementType.FUNCTION.value
            
        # Method definition within a class
        if re.match(r'(?:async\s+)?(?:static\s+)?(?:\w+\s*\([^)]*\))', code):
            return CodeElementType.METHOD.value
            
        # Arrow function
        if re.search(r'=>', code):
            return CodeElementType.FUNCTION.value
            
        # Import statement
        if re.match(r'import\s+', code):
            return CodeElementType.IMPORT.value
            
        return CodeElementType.UNKNOWN.value
    
    def upsert_element(self, original_code: str, element_type: str, name: str, 
                     new_code: str, parent_name: Optional[str]=None) -> str:
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
        # Similar to PythonLanguageService but with JavaScript syntax
        # This is a simplified implementation
        
        if element_type == CodeElementType.FUNCTION.value:
            # Try to find the function
            pattern = r'function\s+' + re.escape(name) + r'\s*\(.*?\)\s*{.*?}(?=\n|$)'
            match = re.search(pattern, original_code, re.DOTALL)
            
            if match:
                # Replace existing function
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                # Add new function at the end
                return original_code + '\n\n' + new_code
                
        elif element_type == CodeElementType.CLASS.value:
            # Try to find the class
            pattern = r'class\s+' + re.escape(name) + r'.*?{.*?}(?=\n|$)'
            match = re.search(pattern, original_code, re.DOTALL)
            
            if match:
                # Replace existing class
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                # Add new class at the end
                return original_code + '\n\n' + new_code
        
        # If we couldn't handle it, return the original code
        return original_code