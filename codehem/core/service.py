"""
Base interfaces for language implementations.
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Union, Type
from codehem import CodeElementType
from codehem.core.formatting.formatter import BaseFormatter
from codehem.core.manipulator_base import ManipulatorBase
from codehem.extractors.base import BaseExtractor
from codehem.models.code_element import CodeElement, CodeElementsResult
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
logger = logging.getLogger(__name__)

class LanguageService(ABC):
    """
    Base class for language-specific services.
    Defines the interface for language-specific operations and combines finder, formatter, and manipulator.
    """
    LANGUAGE_CODE: str

    def __init__(self, extractors: Dict[str, Type[BaseExtractor]], manipulators: Dict[str, Type[ManipulatorBase]], element_type_descriptors: Dict[str, Dict[str, ElementTypeLanguageDescriptor]], formatter_class: Optional[Type[BaseFormatter]]=None):
        """
        Initialize the language service with components.

        Args:
            extractors: Mapping of element types to extractor classes
            manipulators: Mapping of element types to manipulator classes
            element_type_descriptors: Language-specific element type descriptors
            formatter_class: Optional formatter class for this language
        """
        self.extractors: Dict[str, BaseExtractor] = {}
        self.manipulators: Dict[str, ManipulatorBase] = {}
        self.element_type_descriptors: Dict[str, ElementTypeLanguageDescriptor] = {}
        self._extraction_service = None
        self.formatter = formatter_class() if formatter_class else BaseFormatter()
        try:
            from codehem.core.extraction import ExtractionService
            self._extraction_service = ExtractionService(self.language_code)
        except Exception as e:
            logger.error(f'Error creating extraction service for {self.language_code}: {e}')
        
        logger.debug(f"Initializing language service for {self.language_code}, registered manipulators: {list(manipulators.keys())}")
        
        for element_type_name, extractor_class in extractors.items():
            descriptor = element_type_descriptors.get(self.language_code, {}).get(element_type_name)
            if descriptor:
                self.element_type_descriptors[element_type_name] = descriptor
                if extractor_class:
                    try:
                        self.extractors[element_type_name] = extractor_class(self.language_code, descriptor)
                    except Exception as e:
                        logger.error(f'Error creating extractor for {element_type_name}: {e}')
        
        # Initialize manipulators separately to ensure proper element_type mapping
        self._init_manipulators(manipulators)

    def _init_manipulators(self, manipulators: Dict[str, Type[ManipulatorBase]]):
        """Initialize all manipulators for this language service."""
        for key, manipulator_class in manipulators.items():
            if key.startswith(f"{self.language_code}_"):
                # Extract element_type_name from the composite key
                element_type_name = key[len(self.language_code) + 1:]
                try:
                    element_type_enum = self._get_element_type_enum(element_type_name)
                    if element_type_enum:
                        logger.debug(f"Creating manipulator for {self.language_code}/{element_type_name}")
                        self.manipulators[element_type_name] = manipulator_class(
                            element_type=element_type_enum,
                            formatter=self.formatter,
                            extraction_service=self._extraction_service
                        )
                except Exception as e:
                    logger.error(f'Error creating manipulator for {element_type_name}: {e}')

    def _get_element_type_enum(self, element_type_name: str) -> Optional[CodeElementType]:
        """Convert element type name to enum value."""
        try:
            # First try direct attribute lookup
            return getattr(CodeElementType, element_type_name.upper(), None)
        except (AttributeError, ValueError):
            # Then try to match by value
            for elem_type in CodeElementType:
                if elem_type.value.lower() == element_type_name.lower():
                    return elem_type
            return None

    @property
    def language_code(self) -> str:
        return self.LANGUAGE_CODE

    def get_element_descriptor(self, element_type: Union[str, CodeElementType]) -> Optional[ElementTypeLanguageDescriptor]:
        """Get an extractor class by element type."""
        if hasattr(element_type, 'value'):
            element_type = element_type.value
        return self.element_type_descriptors.get(element_type.lower())

    def get_manipulator(self, element_type: str):
        """Get all handlers for a specific language."""
        element_type = element_type.lower()
        manipulator = self.manipulators.get(element_type)
        if not manipulator:
            logger.debug(f"No manipulator found for '{element_type}' in {self.language_code}. Available manipulators: {list(self.manipulators.keys())}")
        return manipulator

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
        result = self.extract_language_specific(code, result)
        logger.debug(f'Completed extraction with {len(result.elements)} elements')
        return result

    def extract_language_specific(self, code: str, current_result: CodeElementsResult) -> CodeElementsResult:
        return current_result

    def resolve_xpath(self, xpath: str) -> Tuple[str, Optional[str]]:
        """Resolve an XPath expression to element name and parent name."""
        parts = xpath.split('.')
        if len(parts) == 1:
            return (parts[0], None)
        return (parts[-1], parts[-2])