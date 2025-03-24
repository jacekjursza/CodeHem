"""
TypeScript language module for CodeHem.
"""
from typing import List, Optional
import re
from ..language_service import BaseLanguageService
from ..language_detector import BaseLanguageDetector
from ..lang_javascript import JavaScriptLanguageService
from ...models.code_element import CodeElementsResult, CodeElement
from ...models.range import CodeRange
from ...models.enums import CodeElementType

class TypeScriptLanguageDetector(BaseLanguageDetector):
    """TypeScript-specific language detector."""

    @property
    def language_code(self) -> str:
        return 'typescript'

    @property
    def file_extensions(self) -> List[str]:
        return ['.ts', '.tsx']

    def detect_confidence(self, code: str) -> float:
        """Calculate confidence that the code is TypeScript."""
        if not code.strip():
            return 0.0
        js_patterns = ['function\\s+\\w+\\s*\\(', 'const\\s+\\w+\\s*=', 'let\\s+\\w+\\s*=', 'var\\s+\\w+\\s*=', 'class\\s+\\w+\\s*{', '\\w+\\s*=\\s*function', '\\(.*?\\)\\s*=>', 'export\\s+', 'import\\s+.*?from']
        ts_patterns = [':\\s*\\w+', 'interface\\s+\\w+', '<\\w+>', 'type\\s+\\w+\\s*=', 'enum\\s+\\w+', 'namespace\\s+\\w+', 'as\\s+\\w+', 'readonly\\s+', 'public\\s+|private\\s+|protected\\s+']
        score = 0
        max_score = (len(js_patterns) + len(ts_patterns)) * 10
        for pattern in js_patterns:
            if re.search(pattern, code, re.DOTALL):
                score += 5
        for pattern in ts_patterns:
            if re.search(pattern, code, re.DOTALL):
                score += 15
        non_ts = ['def\\s+\\w+\\s*\\(', 'from\\s+\\w+\\s+import', ':\\s*\\n']
        for pattern in non_ts:
            if re.search(pattern, code):
                score -= 15
        normalized = max(0.0, min(1.0, score / max_score))
        return normalized

class TypeScriptLanguageService(JavaScriptLanguageService):
    """TypeScript language service implementation that extends JavaScript service."""

    @property
    def language_code(self) -> str:
        return 'typescript'

    @property
    def file_extensions(self) -> List[str]:
        return ['.ts', '.tsx']

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
            return CodeElementType.TYPE_ALIAS.value
        if re.match('enum\\s+\\w+', code):
            return CodeElementType.ENUM.value
        return super().detect_element_type(code)

    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add or replace a TypeScript code element.
        
        Args:
            original_code: Original source code
            element_type: Type of element to add/replace
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
        elif element_type == 'type_alias':
            pattern = 'type\\s+' + re.escape(name) + '\\s*=.*?;(?=\\n|$)'
            match = re.search(pattern, original_code, re.DOTALL)
            if match:
                return original_code[:match.start()] + new_code + original_code[match.end():]
            else:
                return original_code + '\n\n' + new_code
        return super().upsert_element(original_code, element_type, name, new_code, parent_name)
detector = TypeScriptLanguageDetector()
service = TypeScriptLanguageService()

def register(registry):
    """Register TypeScript language components with the registry."""
    registry.register_detector(detector)
    registry.register_service(service)
    
    # Register TypeScript-specific handlers
    # Similar to the JavaScript module, we would add handler registrations here
    # For now, this is left empty since there are no TypeScript-specific handlers in the code dump