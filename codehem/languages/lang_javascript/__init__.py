"""
JavaScript language module for CodeHem.
"""

from typing import List, Optional, Tuple
import re
from ..language_service import BaseLanguageService
from ..language_detector import BaseLanguageDetector
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

    @property
    def supported_element_types(self) -> List[str]:
        return [
            CodeElementType.CLASS.value,
            CodeElementType.FUNCTION.value,
            CodeElementType.METHOD.value,
            CodeElementType.IMPORT.value
        ]

    def can_handle(self, code: str) -> bool:
        """Check if this service can handle the given code."""
        return self.get_confidence_score(code) > 0.5

    def get_confidence_score(self, code: str) -> float:
        """Calculate confidence score for JavaScript code."""
        detector = JavaScriptLanguageDetector()
        return detector.detect_confidence(code)

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
        return self._base_extract(code)


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

    def resolve_xpath(self, xpath: str) -> Tuple[str, Optional[str]]:
        """Resolve an XPath expression to element name and parent name."""
        parts = xpath.split('.')
        if len(parts) == 1:
            return parts[0], None
        return parts[-1], parts[-2]

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