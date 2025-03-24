"""
JavaScript language module for CodeHem.
"""
from typing import List, Optional
import re
from ..base import BaseLanguageDetector, BaseLanguageService
from ...models.code_element import CodeElementsResult, CodeElement
from ...models.range import CodeRange
from ...models.enums import CodeElementType

class JavaScriptLanguageDetector(BaseLanguageDetector):
    """JavaScript-specific language detector."""

    @property
    def language_code(self) -> str:
        return 'javascript'

    @property
    def file_extensions(self) -> List[str]:
        return ['.js', '.jsx']

    def detect_confidence(self, code: str) -> float:
        """Calculate confidence that the code is JavaScript."""
        if not code.strip():
            return 0.0
        patterns = ['function\\s+\\w+\\s*\\(', 'const\\s+\\w+\\s*=', 'let\\s+\\w+\\s*=', 'var\\s+\\w+\\s*=', 'class\\s+\\w+\\s*{', '\\w+\\s*=\\s*function', '\\(.*?\\)\\s*=>', 'export\\s+', 'import\\s+.*?from', '/[/*].*?[*/]/']
        score = 0
        max_score = len(patterns) * 10
        for pattern in patterns:
            if re.search(pattern, code, re.DOTALL):
                score += 10
        non_js = ['def\\s+\\w+\\s*\\(', 'from\\s+\\w+\\s+import', ':\\s*\\n', '@staticmethod']
        for pattern in non_js:
            if re.search(pattern, code):
                score -= 15
        if re.search(':\\s*\\w+', code) or re.search('<\\w+>', code):
            score -= 5
        normalized = max(0.0, min(1.0, score / max_score))
        return normalized

class JavaScriptLanguageService(BaseLanguageService):
    """JavaScript language service implementation."""

    @property
    def language_code(self) -> str:
        return 'javascript'

    @property
    def file_extensions(self) -> List[str]:
        return ['.js', '.jsx']

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

    def extract(self, code: str) -> CodeElementsResult:
        """Extract code elements from JavaScript source code."""
        from ...extractor import Extractor
        extractor = Extractor('javascript')
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
        Add or replace a JavaScript code element.
        
        Args:
            original_code: Original source code
            element_type: Type of element to add/replace
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
        elif element_type == CodeElementType.METHOD.value and parent_name:
            class_pattern = 'class\\s+' + re.escape(parent_name) + '.*?{'
            class_match = re.search(class_pattern, original_code)
            if class_match:
                class_content_start = class_match.end()
                class_content_end = self._find_closing_brace(original_code, class_content_start)
                if class_content_end == -1:
                    return original_code
                method_pattern = '(?:async\\s+)?(?:static\\s+)?\\s*' + re.escape(name) + '\\s*\\(.*?\\)\\s*{.*?}(?=\\n|$)'
                class_content = original_code[class_content_start:class_content_end]
                method_match = re.search(method_pattern, class_content, re.DOTALL)
                if method_match:
                    method_start = class_content_start + method_match.start()
                    method_end = class_content_start + method_match.end()
                    return original_code[:method_start] + new_code + original_code[method_end:]
                else:
                    return original_code[:class_content_end] + '\n  ' + new_code + '\n' + original_code[class_content_end:]
        return original_code

    def _find_closing_brace(self, code: str, start_pos: int) -> int:
        """Find the position of the closing brace that matches the opening brace."""
        stack = []
        for i in range(start_pos, len(code)):
            if code[i] == '{':
                stack.append('{')
            elif code[i] == '}':
                if not stack:
                    return i
                stack.pop()
                if not stack:
                    return i
        return -1
detector = JavaScriptLanguageDetector()
service = JavaScriptLanguageService()

def register(registry):
    """Register JavaScript language components with the registry."""
    registry.register_detector(detector)
    registry.register_service(service)
    
    # Register handlers
    from .type_class import JavaScriptClassHandler
    
    registry.register_handler(JavaScriptClassHandler())
    # Add more JavaScript handler registrations as needed