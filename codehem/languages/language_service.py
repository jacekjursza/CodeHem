"""
Base interfaces for language implementations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from codehem import CodeElementType

from codehem.extractor import Extractor
from codehem.models import CodeRange
from codehem.models.code_element import CodeElementsResult, CodeElement
from codehem.languages.registry import registry


class BaseLanguageService(ABC):
    """
    Base class for language-specific services.
    Defines the interface for language-specific operations and combines finder, formatter, and manipulator.
    """

    @property
    @abstractmethod
    def language_code(self) -> str:
        """Get the language code (e.g., 'python', 'typescript')."""
        pass

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Get file extensions supported by this language."""
        pass

    @property
    @abstractmethod
    def supported_element_types(self) -> List[str]:
        """Get element types supported by this language."""
        pass

    @abstractmethod
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of element in the code.

        Args:
            code: Code to analyze

        Returns:
            Element type string
        """
        pass

    def extract(self, code: str) -> CodeElementsResult:
        """Extract code elements from source code."""
        return self._base_extract(code)

    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add or replace a code element.

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
        handlers = registry.get_handlers(self.language_code)
        for h in handlers:
            if h.element_type.value == element_type:
                handler = h
                break
        if handler:
            return handler.upsert_element(original_code, name, new_code, parent_name)
        return original_code

    def resolve_xpath(self, xpath: str) -> Tuple[str, Optional[str]]:
        """Resolve an XPath expression to element name and parent name."""
        parts = xpath.split('.')
        if len(parts) == 1:
            return parts[0], None
        return parts[-1], parts[-2]

    @staticmethod
    def _convert_to_code_element(raw_element: dict) -> CodeElement:
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
            code_range = CodeRange(
                start_line=range_data['start']['line'],
                start_column=range_data.get('start', {}).get('column', 0),
                end_line=range_data['end']['line'],
                end_column=range_data.get('end', {}).get('column', 0)
            )
        return CodeElement(
            type=element_type,
            name=name,
            content=content,
            range=code_range,
            parent_name=raw_element.get('class_name'),
            children=[]
        )

    def _base_extract(self, code: str) -> CodeElementsResult:
        """
        Base implementation for extract() that language services can call.
        This is a helper method that implements common extraction behavior.

        Args:
            code: Source code as string

        Returns:
            CodeElementsResult containing extracted elements
        """

        extractor = Extractor(self.language_code)
        raw_elements = extractor.extract_all(code)
        result = CodeElementsResult()

        # Process functions and extract their decorators
        for func in raw_elements.get("functions", []):
            element = self._convert_to_code_element(func)
            self._extract_and_attach_decorators(code, element, extractor)
            result.elements.append(element)

        # Process classes, their methods, and extract decorators
        for cls in raw_elements.get("classes", []):
            class_element = self._convert_to_code_element(cls)
            self._extract_and_attach_decorators(code, class_element, extractor)

            # Extract methods for this class
            methods = extractor.extract_methods(code, cls.get("name"))
            for method in methods:
                method_element = self._convert_to_code_element(method)
                method_element.parent_name = cls.get("name")
                self._extract_and_attach_decorators(code, method_element, extractor)
                class_element.children.append(method_element)

            result.elements.append(class_element)

        # Process imports
        for imp in raw_elements.get("imports", []):
            import_element = self._convert_to_code_element(imp)
            result.elements.append(import_element)

        return result

    def _extract_and_attach_decorators(self, code: str, element, extractor) -> None:
        """
        Helper method to extract decorators and attach them as children.
        Language-specific services should override this for customized behavior.

        Args:
            code: Source code as string
            element: CodeElement to attach decorators to
            extractor: Extractor instance to use
        """
        pass