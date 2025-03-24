import re
from typing import List

from codehem import CodeElementType
from codehem.core.service import LanguageService
from codehem.core.registry import language_service


@language_service
class PythonLanguageService(LanguageService):
    """Python language service implementation."""

    @property
    def language_code(self) -> str:
        return 'python'

    @property
    def file_extensions(self) -> List[str]:
        return ['.py']

    @property
    def supported_element_types(self) -> List[str]:
        return [
            CodeElementType.CLASS.value,
            CodeElementType.FUNCTION.value,
            CodeElementType.METHOD.value,
            CodeElementType.IMPORT.value,
            CodeElementType.DECORATOR.value,
            CodeElementType.PROPERTY.value,
            CodeElementType.PROPERTY_GETTER.value,
            CodeElementType.PROPERTY_SETTER.value,
            CodeElementType.STATIC_PROPERTY.value
        ]

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

    def _extract_and_attach_decorators(self, code: str, element, extractor) -> None:
        """
        Extract decorators and attach them as children to the element.

        Args:
        code: Source code as string
        element: CodeElement to attach decorators to
        extractor: Extractor instance to use
        """
        if element.type not in [CodeElementType.CLASS, CodeElementType.METHOD, CodeElementType.FUNCTION]:
            return
        if not element.content:
            return
        decorator_extractor = extractor.get_extractor('decorator')
        if not decorator_extractor:
            return
        decorators = decorator_extractor.extract(element.content, {'language_code': self.language_code})
        for dec in decorators:
            if dec.get('parent_name') == element.name:
                decorator_element = self._convert_to_code_element(dec)
                decorator_element.type = CodeElementType.DECORATOR
                decorator_element.parent_name = element.name
                element.children.append(decorator_element)
        if element.type == CodeElementType.METHOD and element.parent_name:
            class_elements = extractor.extract_classes(code)
            for class_elem in class_elements:
                if class_elem.get('name') == element.parent_name:
                    class_decorators = decorator_extractor.extract(class_elem.get('content', ''), {'language_code': self.language_code})
                    for dec in class_decorators:
                        if dec.get('parent_name') == element.name:
                            decorator_element = self._convert_to_code_element(dec)
                            decorator_element.type = CodeElementType.DECORATOR
                            decorator_element.parent_name = element.name
                            element.children.append(decorator_element)
                    break
