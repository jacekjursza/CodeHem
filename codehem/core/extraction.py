"""
Main entry point for code extraction functionality.
Acts as a facade for the various extraction strategies.
"""
import re
from typing import Dict, List, Optional, Any, Tuple, Union
import os
import logging

from codehem import CodeElementType
from codehem.core.engine.xpath_parser import XPathParser

from codehem.core.registry import registry
from codehem.core.error_handling import handle_extraction_errors
from codehem.core.service import LanguageService
from codehem.languages import get_language_service_for_file, get_language_service_for_code
logger = logging.getLogger(__name__)

class ExtractionService:
    """Main extractor class that delegates to specific extractors based on language."""

    def __init__(self, language_code: str):
        self.language_code = language_code
        self.language_service: LanguageService = registry.get_language_service(language_code)
        logger.debug(f"Created extractor for language: {language_code}")

    def find_element(
        self,
        code: str,
        element_type: str,
        element_name: Optional[str] = None,
        parent_name: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        Find a specific element in the code based on type, name, and parent.

        Args:
            code: Source code as string
            element_type: Type of element to find (e.g., 'function', 'class', 'method')
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)

        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        logger.debug(
            f"Finding element of type '{element_type}', name '{element_name}', parent '{parent_name}'"
        )

        # If only code + type => extract_<type>
        if element_name is None and parent_name is None:
            elements = self.extract_any(code, element_type)
            if elements and len(elements) > 0:
                first_element = elements[0]
                return (
                    first_element.get("start_line", 0),
                    first_element.get("end_line", 0),
                )
            return (0, 0)

        # If name / parent_name => extract_file + filter
        if element_type == CodeElementType.METHOD.value and parent_name:
            methods = self.extract_methods(code, parent_name)
            for method in methods:
                if method.get("name") == element_name:
                    return (method.get("start_line", 0), method.get("end_line", 0))

        elif element_type == CodeElementType.FUNCTION.value:
            functions = self.extract_functions(code)
            for func in functions:
                if func.get("name") == element_name:
                    return (func.get("start_line", 0), func.get("end_line", 0))

        elif element_type == CodeElementType.CLASS.value:
            classes = self.extract_classes(code)
            for cls in classes:
                if cls.get("name") == element_name:
                    return (cls.get("start_line", 0), cls.get("end_line", 0))

        elif element_type == CodeElementType.IMPORT.value:
            imports = self.extract_imports(code)
            for imp in imports:
                if imp.get("name") == element_name:
                    return (imp.get("start_line", 0), imp.get("end_line", 0))

        elif (
            element_type
            in [
                CodeElementType.PROPERTY.value,
                CodeElementType.PROPERTY_GETTER.value,
                CodeElementType.PROPERTY_SETTER.value,
                CodeElementType.STATIC_PROPERTY.value,
            ]
            and parent_name
        ):
            # Extract all elements and filter for properties
            all_elements = self.extract_file(code)
            for cls in all_elements.get("classes", []):
                if cls.get("name") == parent_name:
                    for prop in cls.get(
                        "methods", []
                    ):  # Properties might be in methods list
                        if (
                            prop.get("name") == element_name
                            and prop.get("type") == element_type
                        ):
                            return (prop.get("start_line", 0), prop.get("end_line", 0))

        # Element not found
        return (0, 0)

    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        """
        Find an element in the code using an XPath-like expression.

        Args:
            code: Source code as string
            xpath: XPath-like expression (e.g., 'ClassName.method_name')

        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        (element_name, parent_name, element_type) = XPathParser.get_element_info(xpath)
        if not element_name and (not element_type):
            return (0, 0)
        if element_type == CodeElementType.IMPORT.value and (not element_name):
            return self.extract_any(code, element_type)
        if element_name and element_type:
            return self.extract_any(code, element_type, element_name, parent_name)
        if element_name and (not element_type):
            if parent_name:
                element_types = [
                    CodeElementType.METHOD.value,
                    CodeElementType.PROPERTY.value,
                    CodeElementType.PROPERTY_GETTER.value,
                    CodeElementType.PROPERTY_SETTER.value,
                    CodeElementType.STATIC_PROPERTY.value,
                ]
            else:
                element_types = [
                    CodeElementType.CLASS.value,
                    CodeElementType.FUNCTION.value,
                    CodeElementType.INTERFACE.value,
                ]
            for type_to_try in element_types:
                result = self.find_element(code, type_to_try, element_name, parent_name)
                if result[0] > 0:
                    return result
        return (0, 0)

    @classmethod
    def from_file_path(cls, file_path: str) -> 'ExtractionService':
        """Create an extractor for a file based on its extension."""
        service = get_language_service_for_file(file_path)
        if not service:
            (_, ext) = os.path.splitext(file_path)
            raise ValueError(f'Unsupported file extension: {ext}')
        return cls(service.language_code)

    @classmethod
    def from_raw_code(cls, code: str, language_hints: List[str]=None) -> 'ExtractionService':
        """Create an extractor by attempting to detect the language from code."""
        if language_hints:
            for lang in language_hints:
                temp_extractor = cls(lang)
                if temp_extractor.extract_functions(code) or temp_extractor.extract_classes(code):
                    return temp_extractor
        service = get_language_service_for_code(code)
        if service:
            return cls(service.language_code)
        return cls('python')

    def get_descriptor(self, element_type_descriptor: Union[str, CodeElementType]) -> Optional[Any]:
        """Get the appropriate extractor for the given type and language."""
        descriptor = self.language_service.get_element_descriptor(element_type_descriptor)
        return descriptor

    @handle_extraction_errors
    def extract_functions(self, code: str) -> List[Dict]:
        """Extract functions from the provided code."""
        extractor = self.get_descriptor('function')
        if not extractor:
            logger.warning(f'Could not find extractor for extract_functions / {self.language_code}')
            return []
        
        logger.debug(f"Extracting functions using {extractor.__class__.__name__}")
        results = extractor.extract(code, {'language_code': self.language_code})
        logger.debug(f"Extracted {len(results)} functions")
        return results

    @handle_extraction_errors
    def extract_classes(self, code: str) -> List[Dict]:
        """Extract classes from the provided code."""
        extractor = self.get_descriptor('class')
        if not extractor:
            logger.warning(f'Could not find extractor for extract_classes / {self.language_code}')
            return []
        
        logger.debug(f"Extracting classes using {extractor.__class__.__name__}")
        results = extractor.extract(code, {'language_code': self.language_code})
        logger.debug(f"Extracted {len(results)} classes")
        return results

    @handle_extraction_errors
    def extract_methods(self, code: str, class_name: Optional[str]=None) -> List[Dict]:
        """Extract methods from the provided code, optionally filtering by class."""
        extractor = self.get_descriptor('method')
        if not extractor:
            logger.warning(f'Could not find extractor for extract_methods / {self.language_code}')
            return []
        
        logger.debug(f"Extracting methods for class '{class_name}' using {extractor.__class__.__name__}")
        results = extractor.extract(code, {'language_code': self.language_code, 'class_name': class_name})
        logger.debug(f"Extracted {len(results)} methods")
        return results

    @handle_extraction_errors
    def extract_imports(self, code: str) -> List[Dict]:
        """Extract imports from the provided code."""
        extractor = self.get_descriptor('import')
        if not extractor:
            logger.warning(f'Could not find extractor for extract_imports / {self.language_code}')
            return []
        
        logger.debug(f"Extracting imports using {extractor.__class__.__name__}")
        results = extractor.extract(code, {'language_code': self.language_code})
        logger.debug(f"Extracted {len(results)} imports")
        return results

    @handle_extraction_errors
    def extract_any(self, code, element_type: str) -> List[Dict]:
        """Extract any code element from the provided code."""
        extractor = self.get_descriptor(element_type)
        if not extractor:
            logger.warning(f'Could not find extractor for {element_type} / {self.language_code}')
            return []
        return extractor.extract(code, {'language_code': self.language_code})

    def extract_file(self, code: str) -> Dict[str, List[Dict]]:
        """Extract all code elements from the provided code."""
        logger.debug(f"Starting extraction for all elements")
        
        # Extract imports, classes, and functions
        imports = self.extract_imports(code)
        classes = self.extract_classes(code)
        functions = self.extract_functions(code)
        
        results = {
            'imports': imports,
            'classes': classes,
            'functions': functions
        }
        
        # For each class, extract methods
        for cls in classes:
            class_name = cls.get('name')
            if class_name:
                methods = self.extract_methods(code, class_name)
                cls['methods'] = methods
                logger.debug(f"Added {len(methods)} methods to class '{class_name}'")
        
        logger.debug(f"Completed extraction: {len(imports)} imports, {len(classes)} classes, {len(functions)} functions")
        return results