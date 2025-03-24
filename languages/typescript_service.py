"""
TypeScript-specific language service implementation.
"""
from typing import Dict, List, Optional, Tuple, Any
import re

from languages.javascript_service import JavaScriptLanguageService
from core.models import CodeElementType

class TypeScriptLanguageService(JavaScriptLanguageService):
    """TypeScript language service implementation."""
    
    def __init__(self):
        # Initialize with the TypeScript language code
        super().__init__()
        self.language_code = 'typescript'
        # Reinitialize the extractor with the correct language code
        self.extractor = Extractor('typescript')
    
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of TypeScript code element.
        
        Args:
            code: The code to analyze
            
        Returns:
            Element type string (from CodeElementType)
        """
        code = code.strip()
        
        # Interface definition
        if re.match(r'interface\s+\w+', code):
            return CodeElementType.INTERFACE.value
            
        # Type definition
        if re.match(r'type\s+\w+\s*=', code):
            return CodeElementType.TYPE.value
            
        # Enum definition
        if re.match(r'enum\s+\w+', code):
            return CodeElementType.ENUM.value
            
        # For standard elements, use the JavaScript detection
        return super().detect_element_type(code)
    
    def upsert_element(self, original_code: str, element_type: str, name: str, 
                     new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add or replace a TypeScript code element.
        
        Args:
            original_code: Original source code
            element_type: Type of element to add/replace (from CodeElementType)
            name: Name of the element
            new_code: New content for the element
            parent_name: Name of parent element (e.g., class name for methods)
            
        Returns:
            Modified code
        """
        # Handle TypeScript-specific elements
        if element_type == CodeElementType.INTERFACE.value:
            # Try to find the interface
            pattern = r'interface\s+' + re.escape(name) + r'.*?{.*?}(?=\n|$)'
            match = re.search(pattern, original_code, re.DOTALL)
            
            if match:
                # Replace existing interface
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                # Add new interface at the end
                return original_code + '\n\n' + new_code
                
        elif element_type == CodeElementType.TYPE.value:
            # Try to find the type
            pattern = r'type\s+' + re.escape(name) + r'\s*=.*?;(?=\n|$)'
            match = re.search(pattern, original_code, re.DOTALL)
            
            if match:
                # Replace existing type
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                # Add new type at the end
                return original_code + '\n\n' + new_code
                
        # For standard elements, use the JavaScript implementation
        return super().upsert_element(original_code, element_type, name, new_code, parent_name)