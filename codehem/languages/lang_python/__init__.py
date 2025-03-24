"""
Python language module for CodeHem.
"""
from typing import List, Optional
import re
from ..base import BaseLanguageDetector, BaseLanguageService
from ...models.code_element import CodeElementsResult, CodeElement
from ...models.range import CodeRange
from ...models.enums import CodeElementType

class PythonLanguageDetector(BaseLanguageDetector):
    """Python-specific language detector."""

    @property
    def language_code(self) -> str:
        return 'python'

    @property
    def file_extensions(self) -> List[str]:
        return ['.py']

    def detect_confidence(self, code: str) -> float:
        """Calculate confidence that the code is Python."""
        if not code.strip():
            return 0.0
        patterns = ['def\\s+\\w+\\s*\\(', 'class\\s+\\w+\\s*:', 'import\\s+\\w+', 'from\\s+\\w+\\s+import', ':\\s*\\n', '__\\w+__', '#.*?\\n', '""".*?"""', '@\\w+']
        score = 0
        max_score = len(patterns) * 10
        for pattern in patterns:
            if re.search(pattern, code, re.DOTALL):
                score += 10
        non_python = ['{\\s*\\n', 'function\\s+\\w+\\s*\\(', 'var\\s+\\w+\\s*=', 'let\\s+\\w+\\s*=', 'const\\s+\\w+\\s*=']
        for pattern in non_python:
            if re.search(pattern, code):
                score -= 15
        normalized = max(0.0, min(1.0, score / max_score))
        return normalized

class PythonLanguageService(BaseLanguageService):
    """Python language service implementation."""

    @property
    def language_code(self) -> str:
        return 'python'

    @property
    def file_extensions(self) -> List[str]:
        return ['.py']

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
        if re.search('@property', code):
            return CodeElementType.PROPERTY_GETTER.value
        if re.search('@\\w+\\.setter', code):
            return CodeElementType.PROPERTY_SETTER.value
        if re.match('def\\s+\\w+', code):
            if re.search('def\\s+\\w+\\s*\\(\\s*(?:self|cls)[\\s,)]', code):
                return CodeElementType.METHOD.value
            return CodeElementType.FUNCTION.value
        if re.match('(?:import|from)\\s+\\w+', code):
            return CodeElementType.IMPORT.value
        if re.match('[A-Z][A-Z0-9_]*\\s*=', code):
            return CodeElementType.STATIC_PROPERTY.value
        if re.match('self\\.\\w+\\s*=', code):
            return CodeElementType.PROPERTY.value
        return CodeElementType.UNKNOWN.value

    def extract(self, code: str) -> CodeElementsResult:
        """Extract code elements from Python source code."""
        from ...extractor import Extractor
        extractor = Extractor('python')
        raw_elements = extractor.extract_all(code)
        result = CodeElementsResult()
        for func in raw_elements.get('functions', []):
            element = self._convert_to_code_element(func)
            result.elements.append(element)
        for cls in raw_elements.get('classes', []):
            class_element = self._convert_to_code_element(cls)
            methods = extractor.extract_methods(code, cls.get('name'))
            for method in methods:
                method_element = self._convert_to_code_element(method)
                method_element.parent_name = cls.get('name')
                class_element.children.append(method_element)
            result.elements.append(class_element)
        for imp in raw_elements.get('imports', []):
            import_element = self._convert_to_code_element(imp)
            result.elements.append(import_element)
        return result

    def _convert_to_code_element(self, raw_element: dict) -> CodeElement:
        """Convert raw extractor output to CodeElement."""
        element_type_str = raw_element.get('type', 'unknown')
        name = raw_element.get('name', '')
        content = raw_element.get('content', '')
        element_type = CodeElementType.UNKNOWN
        if element_type_str == 'function':
            element_type = CodeElementType.FUNCTION
        elif element_type_str == 'class':
            element_type = CodeElementType.CLASS
        elif element_type_str == 'method':
            element_type = CodeElementType.METHOD
        elif element_type_str == 'import':
            element_type = CodeElementType.IMPORT
        range_data = raw_element.get('range')
        code_range = None
        if range_data:
            code_range = CodeRange(start_line=range_data['start']['line'], start_column=range_data.get('start', {}).get('column', 0), end_line=range_data['end']['line'], end_column=range_data.get('end', {}).get('column', 0))
        return CodeElement(type=element_type, name=name, content=content, range=code_range, parent_name=raw_element.get('class_name'), children=[])

    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add or replace a Python code element.

        Args:
            original_code: Original source code
            element_type: Type of element to add/replace
            name: Name of the element
            new_code: New content for the element
            parent_name: Name of parent element (e.g., class name for methods)

        Returns:
            Modified code
        """
        handler = None
        from ..registry import registry
        handlers = registry.get_handlers(self.language_code)
        for h in handlers:
            if h.element_type.value == element_type:
                handler = h
                break
        if handler:
            return handler.upsert_element(original_code, name, new_code, parent_name)
        return original_code
detector = PythonLanguageDetector()
service = PythonLanguageService()

def register(registry):
    """Register Python language components with the registry."""
    registry.register_detector(detector)
    registry.register_service(service)
    
    # Register handlers
    from .type_class import PythonClassHandler
    from .type_function import PythonFunctionHandler
    from .type_method import PythonMethodHandler
    from .type_import import PythonImportHandler
    from .type_property_getter import PythonPropertyGetterHandler
    from .type_property_setter import PythonPropertySetterHandler
    from .type_static_property import PythonStaticPropertyHandler
    
    registry.register_handler(PythonClassHandler())
    registry.register_handler(PythonFunctionHandler())
    registry.register_handler(PythonMethodHandler())
    registry.register_handler(PythonImportHandler())
    registry.register_handler(PythonPropertyGetterHandler())
    registry.register_handler(PythonPropertySetterHandler())
    registry.register_handler(PythonStaticPropertyHandler())