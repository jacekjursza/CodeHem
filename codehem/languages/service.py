"""
Base language service implementation.
"""
from typing import Dict

from codehem.extractor import Extractor
from codehem.models import CodeElement, CodeElementsResult
from codehem.models.code_element import CodeElement
from codehem.models.enums import CodeElementType
from codehem.models.range import CodeRange


class LanguageService:
    """Base class for language-specific services."""

    def __init__(self, language_code: str):
        self.language_code = language_code
        self.extractor = Extractor(language_code)

    def extract(self, code: str) -> CodeElementsResult:
        """
        Extract code elements from the provided code.
        
        Args:
            code: The source code
            
        Returns:
            CodeElementsResult containing extracted elements
        """
        raw_elements = self.extractor.extract_all(code)
        result = CodeElementsResult()
        for func in raw_elements.get('functions', []):
            element = self._convert_to_code_element(func)
            result.elements.append(element)
        for cls in raw_elements.get('classes', []):
            class_element = self._convert_to_code_element(cls)
            methods = self.extractor.extract_methods(code, cls.get('name'))
            for method in methods:
                method_element = self._convert_to_code_element(method)
                class_element.children.append(method_element)
            result.elements.append(class_element)
        for imp in raw_elements.get('imports', []):
            import_element = self._convert_to_code_element(imp)
            result.elements.append(import_element)
        return result

    def _convert_to_code_element(self, raw_element: Dict) -> 'CodeElement':
        """Convert raw extractor output to CodeElement."""
        element_type = raw_element.get('type', 'unknown')
        name = raw_element.get('name', '')
        content = raw_element.get('content', '')
        element_type_enum = None
        if element_type == 'function':
            element_type_enum = CodeElementType.FUNCTION
        elif element_type == 'class':
            element_type_enum = CodeElementType.CLASS
        elif element_type == 'method':
            element_type_enum = CodeElementType.METHOD
        elif element_type == 'import':
            element_type_enum = CodeElementType.IMPORT
        else:
            element_type_enum = CodeElementType.UNKNOWN
        range_data = raw_element.get('range')
        code_range = None
        if range_data:
            code_range = CodeRange(start_line=range_data['start']['line'], start_column=range_data['start']['column'], end_line=range_data['end']['line'], end_column=range_data['end']['column'])
        return CodeElement(type=element_type_enum, name=name, content=content, range=code_range, parent_name=raw_element.get('class_name'), children=[])

    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of code element.
        
        Args:
            code: The code to analyze
            
        Returns:
            Element type string (from CodeElementType)
        """
        code = code.strip()
        if code.startswith('class '):
            return CodeElementType.CLASS.value
        elif code.startswith('def '):
            lines = code.splitlines()
            method_indicators = ['self', 'cls']
            params = lines[0].split('(')[1].split(')')[0] if '(' in lines[0] else ''
            for indicator in method_indicators:
                if indicator in params.split(','):
                    return CodeElementType.METHOD.value
            return CodeElementType.FUNCTION.value
        elif code.startswith('import ') or code.startswith('from '):
            return CodeElementType.IMPORT.value
        return CodeElementType.UNKNOWN.value