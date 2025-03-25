"""
Base interfaces for language implementations.
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Union, Type
from codehem import CodeElementType
from codehem.extractors.base import BaseExtractor
from codehem.core.manipulator import BaseManipulator
from codehem.models.code_element import CodeElement, CodeElementsResult
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
logger = logging.getLogger(__name__)

class LanguageService(ABC):
    """
    Base class for language-specific services.
    Defines the interface for language-specific operations and combines finder, formatter, and manipulator.
    """
    LANGUAGE_CODE: str

    def __init__(self, extractors: Dict[str, Type[BaseExtractor]], manipulators: Dict[str, Type[BaseManipulator]], element_type_descriptors: Dict[str, Dict[str, ElementTypeLanguageDescriptor]]):
        self.extractors: Dict[str, BaseExtractor] = {}
        self.manipulators: Dict[str, BaseManipulator] = {}
        self.element_type_descriptors: Dict[str, ElementTypeLanguageDescriptor] = {}
        for (element_type_name, extractor_class) in extractors.items():
            descriptor = element_type_descriptors[self.language_code].get(element_type_name)
            if descriptor:
                self.element_type_descriptors[element_type_name] = descriptor
                if extractor_class:
                    self.extractors[element_type_name] = extractor_class(self.language_code, descriptor)
                manipulator_class = manipulators.get(f'{self.language_code}_{element_type_name}')
                if manipulator_class and extractor_class:
                    self.manipulators[element_type_name] = manipulator_class(self.extractors[element_type_name])

    @property
    def language_code(self) -> str:
        return self.LANGUAGE_CODE

    def get_element_descriptor(self, element_type: Union[str, CodeElementType]) -> Optional[ElementTypeLanguageDescriptor]:
        """Get an extractor class by element type."""
        if hasattr(element_type, 'value'):
            element_type = element_type.value
        return self.element_type_descriptors.get(element_type.lower())

    def get_manipulator(self, element_type: str) -> BaseManipulator:
        """Get all handlers for a specific language."""
        return self.manipulators.get(element_type.lower())

    def get_extractor(self, element_type: str) -> BaseExtractor:
        return self.extractors.get(element_type.lower())

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
        logger.debug(f'Starting extraction for {self.language_code}')
        from codehem.core.extraction import ExtractionService
        extractor = ExtractionService(self.language_code)
        result = extractor.extract_elements(code)
        # Apply any language-specific extraction
        result = self.extract_language_specific(code, result)
        logger.debug(f'Completed extraction with {len(result.elements)} elements')
        return result

    def extract_language_specific(self, code: str, current_result: CodeElementsResult) -> CodeElementsResult:
        return current_result

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
        handlers = self.get_manipulator(self.language_code)
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
            return (parts[0], None)
        return (parts[-1], parts[-2])