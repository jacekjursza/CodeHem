"""
TypeScript language service implementation.
"""
import re
from typing import List, Optional
from codehem import CodeElementType, CodeElementXPathNode
from codehem.core.service import LanguageService
from codehem.core.registry import language_service
from codehem.models.code_element import CodeElementsResult

@language_service
class TypeScriptLanguageService(LanguageService):
    """TypeScript language service implementation."""
    LANGUAGE_CODE = 'typescript'

    @property
    def file_extensions(self) -> List[str]:
        return ['.ts', '.tsx']

    @property
    def supported_element_types(self) -> List[str]:
        return [
            CodeElementType.CLASS.value,
            CodeElementType.FUNCTION.value, 
            CodeElementType.METHOD.value,
            CodeElementType.IMPORT.value,
            CodeElementType.INTERFACE.value,
            CodeElementType.TYPE_ALIAS.value,
            CodeElementType.PROPERTY.value
        ]

    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of TypeScript code element.
        Args:
            code: The code to analyze
        Returns:
            Element type string (from CodeElementType)
        """
        code = code.strip()
        
        if re.match(r'^\s*class\s+\w+', code):
            return CodeElementType.CLASS.value
            
        if re.match(r'^\s*interface\s+\w+', code):
            return CodeElementType.INTERFACE.value
            
        if re.match(r'^\s*type\s+\w+\s*=', code):
            return CodeElementType.TYPE_ALIAS.value
            
        if re.search(r'(public|private|protected|readonly)?\s*\w+\s*\(.*?\)\s*[{:]', code):
            return CodeElementType.METHOD.value
            
        if re.match(r'^\s*function\s+\w+', code) or re.match(r'^\s*const\s+\w+\s*=\s*\(.*?\)\s*=>', code):
            return CodeElementType.FUNCTION.value
            
        if re.match(r'^\s*(import|export)', code):
            return CodeElementType.IMPORT.value
            
        if re.match(r'^\s*(public|private|protected|readonly)?\s*\w+\s*:\s*\w+', code):
            return CodeElementType.PROPERTY.value
            
        return CodeElementType.UNKNOWN.value

    def get_text_by_xpath_internal(self, code: str, xpath_nodes: List['CodeElementXPathNode']) -> Optional[str]:
        """
        Internal method to retrieve text content based on parsed XPath nodes for TypeScript.
        """
        # This is a placeholder implementation
        # For a complete implementation, we would need to handle TypeScript-specific patterns
        return None
        
    def extract_language_specific(self, code: str, current_result: CodeElementsResult) -> CodeElementsResult:
        """Extract TypeScript-specific elements like interfaces and type aliases."""
        # This would be implemented for TypeScript-specific element extraction
        return current_result