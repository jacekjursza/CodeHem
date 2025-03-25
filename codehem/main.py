"""
CodeHem2 main class for language-agnostic code manipulation.
"""
import os
from typing import List, Optional, Tuple

from .core.engine.xpath_parser import XPathParser
from .core.extraction import ExtractionService
from .languages import (
    get_language_service,
    get_language_service_for_code,
    get_language_service_for_file,
    get_supported_languages,
)
from .models.code_element import CodeElement, CodeElementsResult
from .models.enums import CodeElementType
from .models.xpath import CodeElementXPathNode


class CodeHem:
    """
    Main entry point for CodeHem2.
    Provides language-agnostic interface for code manipulation.
    """

    def __init__(self, language_code: str):
        """
        Initialize CodeHem2 for a specific language.
        
        Args:
            language_code: Language code (e.g., 'python', 'typescript')
            
        Raises:
            ValueError: If the language is not supported
        """
        self.language_service = get_language_service(language_code)
        self.extraction_service = ExtractionService(language_code)
        if not self.language_service:
            raise ValueError(f'Unsupported language: {language_code}')

    @classmethod
    def from_file_path(cls, file_path: str) -> 'CodeHem':
        """
        Create a CodeHem2 instance based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            CodeHem2 instance
            
        Raises:
            ValueError: If the file extension is not supported
        """
        language_service = get_language_service_for_file(file_path)
        if not language_service:
            raise ValueError(f'Unsupported file extension: {os.path.splitext(file_path)[1]}')
        return cls(language_service.language_code)

    @classmethod
    def from_raw_code(cls, code: str) -> 'CodeHem':
        """
        Create a CodeHem2 instance by detecting language from code.
        
        Args:
            code: Source code as string
            
        Returns:
            CodeHem2 instance
            
        Raises:
            ValueError: If the language could not be detected
        """
        language_service = get_language_service_for_code(code)
        if not language_service:
            raise ValueError('Could not detect language from code')
        return cls(language_service.language_code)

    @staticmethod
    def supported_languages() -> List[str]:
        """
        Get a list of supported language codes.
        
        Returns:
            List of supported language codes
        """
        return get_supported_languages()

    @staticmethod
    def load_file(file_path: str) -> str:
        """
        Load content from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Content of the file as string
            
        Raises:
            FileNotFoundError: If the file does not exist
            IOError: If the file cannot be read
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'File not found: {file_path}')
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r') as f:
                return f.read()

    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of element in the code.
        
        Args:
            code: Code to analyze
            
        Returns:
            Element type string (from CodeElementType)
        """
        return self.language_service.detect_element_type(code)

    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        """
        Add or replace an element in the code.
        
        Args:
            original_code: Original source code
            element_type: Type of element to add/replace (from CodeElementType)
            name: Name of the element
            new_code: New content for the element
            parent_name: Name of parent element (e.g., class name for methods)
            
        Returns:
            Modified code
        """
        return self.language_service.upsert_element(original_code, element_type, name, new_code, parent_name)

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
            element_type = self.detect_element_type(new_code)
        return self.upsert_element(original_code, element_type, element_name, new_code, parent_name)

    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        """
        Find an element's location using an XPath expression.
        
        Args:
            code: Source code as string
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        return self.extraction_service.find_by_xpath(code, xpath)

    def extract(self, code: str) -> CodeElementsResult:
        """
        Extract code elements from the source code.
        
        Args:
            code: Source code as string
            
        Returns:
            CodeElementsResult containing extracted elements
        """
        return self.extraction_service.extract_file(code)

    @staticmethod
    def filter(elements: CodeElementsResult, xpath: str='') -> Optional[CodeElement]:
        """
        Filter code elements based on XPath expression.
        
        Args:
            elements: CodeElementsResult containing elements
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')
            
        Returns:
            Matching element or None if not found
        """
        if not xpath or not elements or (not hasattr(elements, 'elements')):
            return None
        (element_name, parent_name, element_type) = XPathParser.get_element_info(xpath)
        if xpath.lower() == 'imports' or (element_type == CodeElementType.IMPORT.value and (not element_name)):
            for element in elements.elements:
                if element.type == CodeElementType.IMPORT:
                    return element
        if parent_name:
            for element in elements.elements:
                if element.type == CodeElementType.CLASS and element.name == parent_name:
                    for child in element.children:
                        if hasattr(child, 'name') and child.name == element_name:
                            if element_type and child.type != element_type:
                                continue
                            return child
            return None
        for element in elements.elements:
            if hasattr(element, 'name') and element.name == element_name:
                if element_type and element.type != element_type:
                    continue
                if not element.parent_name:
                    return element
        return None

    @staticmethod
    def parse_xpath(xpath: str) -> List[CodeElementXPathNode]:
        """
        Parse an XPath expression into component nodes.
        
        Args:
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')
            
        Returns:
            List of CodeElementXPathNode objects representing the path
        """
        return XPathParser.parse(xpath)

    @staticmethod
    def format_xpath(nodes: List[CodeElementXPathNode]) -> str:
        """
        Format XPath nodes back into an XPath expression string.
        
        Args:
            nodes: List of CodeElementXPathNode objects
            
        Returns:
            XPath expression string
        """
        return XPathParser.to_string(nodes)

