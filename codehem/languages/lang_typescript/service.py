"""
TypeScript language service implementation.
"""
import re
import logging
from typing import List, Optional, Dict, Union, Any
from codehem import CodeElementType, CodeElementXPathNode
from codehem.core.service import LanguageService
from codehem.core.registry import language_service
from codehem.models.code_element import CodeElementsResult, CodeElement
from codehem.core.engine.xpath_parser import XPathParser

logger = logging.getLogger(__name__)

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
        if not xpath_nodes:
            return None
            
        from codehem import CodeHem
        element_name = xpath_nodes[-1].name
        element_type = xpath_nodes[-1].type
        parent_name = xpath_nodes[-2].name if len(xpath_nodes) > 1 else None
        
        include_all = False
        if element_type == 'all':
            include_all = True
            element_type = None
            
        elements_result = self.extract(code)
        code_lines = code.splitlines()
        
        def extract_text(element: CodeElement, code_lines: List[str]) -> Optional[str]:
            """Extract text content from code based on element range."""
            if element and element.range:
                start = element.range.start_line
                end = element.range.end_line
                if 1 <= start <= len(code_lines) and 1 <= end <= len(code_lines) and start <= end:
                    return '\n'.join(code_lines[start - 1:end])
            return None
            
        # Handle special case for interfaces
        if len(xpath_nodes) == 1 and element_type == CodeElementType.INTERFACE.value:
            # Find interface using regex as a fallback
            pattern = rf'interface\s+{re.escape(element_name)}\s*{{[^}}]*}}'
            match = re.search(pattern, code, re.DOTALL)
            if match:
                return match.group(0)
                
        # Try using the filter method
        filtered_element = CodeHem.filter(elements_result, XPathParser.to_string(xpath_nodes))
        if filtered_element:
            text = extract_text(filtered_element, code_lines)
            if include_all:
                # Include decorators if present
                decorators_text = '\n'.join([child.content for child in filtered_element.children 
                                          if child.type == CodeElementType.DECORATOR])
                return f'{text}\n{decorators_text}' if decorators_text else text
            return text
            
        # Try finding by regex as a last resort
        if element_name:
            if element_type == CodeElementType.CLASS.value:
                pattern = rf'class\s+{re.escape(element_name)}\s*{{[^}}]*}}'
                match = re.search(pattern, code, re.DOTALL)
                if match:
                    return match.group(0)
            elif element_type == CodeElementType.FUNCTION.value:
                pattern = rf'function\s+{re.escape(element_name)}\s*\([^)]*\)\s*{{[^}}]*}}'
                match = re.search(pattern, code, re.DOTALL)
                if match:
                    return match.group(0)
                    
                # Check for arrow function
                pattern = rf'const\s+{re.escape(element_name)}\s*=\s*\([^)]*\)\s*=>\s*{{[^}}]*}}'
                match = re.search(pattern, code, re.DOTALL)
                if match:
                    return match.group(0)
                
        return None

    def extract_language_specific(self, code: str, current_result: CodeElementsResult) -> CodeElementsResult:
        """Extract TypeScript-specific elements like interfaces and type aliases."""
        # This method could be expanded to handle more TypeScript-specific elements
        return current_result