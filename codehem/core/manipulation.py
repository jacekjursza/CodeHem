"""
Main entry point for code manipulation functionality.
Acts as a facade for the various manipulation strategies.
"""
import logging
from typing import Optional

from codehem import CodeElementType
from codehem.core.engine.xpath_parser import XPathParser
from codehem.core.registry import registry
from codehem.core.service import LanguageService
from codehem.languages import (
    get_language_service_for_code,
    get_language_service_for_file,
)

logger = logging.getLogger(__name__)

class ManipulationService:
    """
    Main manipulation class that delegates to language-specific manipulators.
    Provides a unified API for code manipulation operations.
    """

    def __init__(self, language_code: str):
        """
        Initialize the manipulation service for a specific language.
        
        Args:
            language_code: Language code (e.g., 'python', 'typescript')
        """
        self.language_code = language_code
        self.language_service: LanguageService = registry.get_language_service(language_code)
        if not self.language_service:
            raise ValueError(f'Unsupported language: {language_code}')
        logger.debug(f'Created manipulation service for language: {language_code}')

    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add or replace a code element.

        Args:
        original_code: Original source code
        element_type: Type of element to add/replace (from CodeElementType)
        name: Name of the element
        new_code: New content for the element
        parent_name: Name of parent element (e.g., class name for methods)

        Returns:
        Modified code
        """
        logger.debug(f"Upserting element of type '{element_type}', name '{name}', parent '{parent_name}'")
        manipulator = self.language_service.get_manipulator(element_type)

        if manipulator:
            logger.debug(f"Found manipulator: {manipulator.__class__.__name__}")
            if hasattr(manipulator, 'replace_element'):
                return manipulator.replace_element(original_code, name, new_code, parent_name)
            logger.warning(f'Manipulator for {element_type} does not implement replace_element method')
        else:
            logger.error(f'No manipulator found for element type: {element_type} in {self.language_code}')
            # Try to debug why manipulator is not found
            all_manipulators = getattr(self.language_service, 'manipulators', {})
            logger.error(f'Available manipulators: {list(all_manipulators.keys())}')

        return original_code

    def upsert_element_by_xpath(self, original_code: str, xpath: str, new_code: str) -> str:
        """
        Add or replace an element in the code using XPath expression.
        
        Args:
            original_code: Original source code
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')
            new_code: New content for the element
            
        Returns:
            Modified code
        """
        (element_name, parent_name, element_type) = XPathParser.get_element_info(xpath)
        if not element_type:
            element_type = self.language_service.detect_element_type(new_code)
        return self.upsert_element(original_code, element_type, element_name, new_code, parent_name)

    def add_element(self, original_code: str, element_type: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add a new code element.
        
        Args:
            original_code: Original source code
            element_type: Type of element to add (from CodeElementType)
            new_code: Content for the new element
            parent_name: Name of parent element (e.g., class name for methods)
            
        Returns:
            Modified code
        """
        logger.debug(f"Adding element of type '{element_type}', parent '{parent_name}'")
        manipulator = self.language_service.get_manipulator(element_type)
        if manipulator:
            if hasattr(manipulator, 'add_element'):
                return manipulator.add_element(original_code, new_code, parent_name)
            logger.warning(f"Manipulator for {element_type} does not implement add_element method")
        else:
            logger.warning(f"No manipulator found for element type: {element_type}")
        return original_code

    def remove_element(self, original_code: str, element_type: str, element_name: str, parent_name: Optional[str]=None) -> str:
        """
        Remove a code element.
        
        Args:
            original_code: Original source code
            element_type: Type of element to remove (from CodeElementType)
            element_name: Name of the element to remove
            parent_name: Name of parent element (e.g., class name for methods)
            
        Returns:
            Modified code
        """
        logger.debug(f"Removing element of type '{element_type}', name '{element_name}', parent '{parent_name}'")
        manipulator = self.language_service.get_manipulator(element_type)
        if manipulator:
            if hasattr(manipulator, 'remove_element'):
                return manipulator.remove_element(original_code, element_name, parent_name)
            logger.warning(f"Manipulator for {element_type} does not implement remove_element method")
        else:
            logger.warning(f"No manipulator found for element type: {element_type}")
        return original_code

    def remove_element_by_xpath(self, original_code: str, xpath: str) -> str:
        """
        Remove an element from the code using XPath expression.

        Args:
        original_code: Original source code
        xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')

        Returns:
        Modified code
        """
        (element_name, parent_name, element_type) = XPathParser.get_element_info(xpath)
        if not element_type:
            # We need to find the element to determine its type
            from codehem.core.extraction import ExtractionService
            extraction_service = ExtractionService(self.language_code)
            elements = extraction_service.extract_all(original_code)

            # Filter elements based on xpath
            if not xpath or not elements or (not hasattr(elements, 'elements')):
                return original_code

            if parent_name:
                for element in elements.elements:
                    if element.type == CodeElementType.CLASS and element.name == parent_name:
                        for child in element.children:
                            if hasattr(child, 'name') and child.name == element_name:
                                element_type = child.type.value
                                break
            else:
                for element in elements.elements:
                    if hasattr(element, 'name') and element.name == element_name:
                        if not element.parent_name:
                            element_type = element.type.value
                            break

            if not element_type:
                logger.warning(f"Could not find element with xpath: {xpath}")
                return original_code

        return self.remove_element(original_code, element_type, element_name, parent_name)

    @classmethod
    def from_file_path(cls, file_path: str) -> 'ManipulationService':
        """Create a manipulation service for a file based on its extension."""
        service = get_language_service_for_file(file_path)
        if not service:
            import os
            (_, ext) = os.path.splitext(file_path)
            raise ValueError(f'Unsupported file extension: {ext}')
        return cls(service.language_code)

    @classmethod
    def from_raw_code(cls, code: str) -> 'ManipulationService':
        """Create a manipulation service by attempting to detect the language from code."""
        service = get_language_service_for_code(code)
        if service:
            return cls(service.language_code)
        return cls('python')  # Default to Python if no language detected