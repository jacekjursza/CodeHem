"""
TypeScript-specific language service implementation.
"""
from typing import Dict, List, Optional, Tuple, Any
import re
from codehem.models.enums import CodeElementType
from .javascript_service import JavaScriptLanguageService
from codehem.extractor import Extractor

class TypeScriptLanguageService(JavaScriptLanguageService):
    """TypeScript language service implementation."""

    def __init__(self):
        super().__init__()
        self.language_code = 'typescript'
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
        if re.match('interface\\s+\\w+', code):
            return CodeElementType.INTERFACE.value
        if re.match('type\\s+\\w+\\s*=', code):
            return CodeElementType.TYPE.value
        if re.match('enum\\s+\\w+', code):
            return CodeElementType.ENUM.value
        return super().detect_element_type(code)

    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
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
        if element_type == CodeElementType.INTERFACE.value:
            pattern = 'interface\\s+' + re.escape(name) + '.*?{.*?}(?=\\n|$)'
            match = re.search(pattern, original_code, re.DOTALL)
            if match:
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                return original_code + '\n\n' + new_code
        elif element_type == CodeElementType.TYPE.value:
            pattern = 'type\\s+' + re.escape(name) + '\\s*=.*?;(?=\\n|$)'
            match = re.search(pattern, original_code, re.DOTALL)
            if match:
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                return original_code + '\n\n' + new_code
        return super().upsert_element(original_code, element_type, name, new_code, parent_name)