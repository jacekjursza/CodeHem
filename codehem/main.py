"""
CodeHem2 main class for language-agnostic code manipulation.
"""
import os
from typing import List, Optional, Tuple

import logging # Import the logging module
from .core.engine.xpath_parser import XPathParser
from .core.extraction import ExtractionService
from .core.manipulation import ManipulationService
from .languages import get_language_service, get_language_service_for_code, get_language_service_for_file, get_supported_languages
from .models.code_element import CodeElement, CodeElementsResult
from .models.enums import CodeElementType
from .models.xpath import CodeElementXPathNode


logger = logging.getLogger(__name__) # Define the logger at the module level

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
        if not self.language_service:
            raise ValueError(f'Unsupported language: {language_code}')
        self.extraction = ExtractionService(language_code)
        self.manipulation = ManipulationService(language_code)

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
        return self.manipulation.upsert_element(original_code, element_type, name, new_code, parent_name)

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
        return self.manipulation.upsert_element_by_xpath(original_code, xpath, new_code)

    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        """
        Find an element's location using an XPath expression.

        Args:
            code: Source code as string
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')

        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        return self.extraction.find_by_xpath(code, xpath)

    def get_text_by_xpath(self, code: str, xpath: str) -> Optional[str]:
        """
        Get the text content of an element using an XPath expression.
        Handles unqualified property XPaths by returning the last defined method (getter or setter).
        Handles explicit property getter/setter types like [property_getter].

        Args:
        code: Source code as string
        xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName.value', 'ClassName.value[property_getter]')

        Returns:
        Text content of the element, or None if not found
        """
        element_name, parent_name, xpath_element_type = XPathParser.get_element_info(xpath)
        logger.debug(f"get_text_by_xpath: Parsed XPath '{xpath}' -> name={element_name}, parent={parent_name}, type={xpath_element_type}")

        # Helper to extract lines to avoid code duplication and add validation
        def extract_text(start, end, code_lines):
            # Added validation for line range
            if start > len(code_lines) or end > len(code_lines) or start <= 0 or end < start:
                logger.warning(f"Invalid line range for extraction: start={start}, end={end}")
                return None
            return '\n'.join(code_lines[start - 1:end])

        lines = code.splitlines()

        # Handle top-level elements or elements without a parent in XPath
        if not parent_name:
            # Try find_by_xpath first for top-level resolution
            start_line, end_line = self.find_by_xpath(code, xpath)
            if start_line > 0:
                 return extract_text(start_line, end_line, lines)
            else:
                 # Fallback using filter (handles imports etc.)
                 elements = self.extraction.extract_all(code)
                 element = CodeHem.filter(elements, xpath)
                 if element and hasattr(element, 'range') and element.range: # Check if element and range exist
                     return extract_text(element.range.start_line, element.range.end_line, lines)
                 logger.debug(f"Could not find top-level element for XPath: {xpath}")
                 return None

        # Handle nested elements (like methods/properties within a class)
        elements = self.extraction.extract_all(code)
        parent_element = CodeHem.filter(elements, parent_name)

        if parent_element and hasattr(parent_element, 'children') and parent_element.children: # Check if parent and children exist
            candidates = []
            # Determine if the type was explicitly specified in the original XPath string
            is_type_explicit_in_xpath = '[' in xpath and ']' in xpath # Simple heuristic

            logger.debug(f"Searching children of '{parent_name}' for '{element_name}'. Explicit type in XPath: {is_type_explicit_in_xpath}")

            for child in parent_element.children:
                # Ensure child has necessary attributes before checking
                if not (hasattr(child, 'name') and hasattr(child, 'type') and hasattr(child, 'range') and child.range):
                    logger.debug(f"  Skipping child due to missing attributes: {getattr(child, 'name', 'N/A')}")
                    continue # Skip child if essential attributes are missing

                if child.name == element_name:
                    if is_type_explicit_in_xpath:
                        # --- BEGIN CHANGE FOR EXPLICIT TYPE ---
                        # If type was explicit in XPath, match it strictly and return immediately if found.
                        if xpath_element_type and child.type == xpath_element_type:
                             logger.debug(f"  Exact match found (explicit type): {child.name} [{child.type}]")
                             text = extract_text(child.range.start_line, child.range.end_line, lines)
                             if text:
                                 # Return the first and only match for explicit type
                                 return text
                             else:
                                 logger.warning(f"Could not extract text for matched explicit child: {child.name} range: {child.range}")
                                 # If text extraction fails for the specific element requested, return None
                                 return None
                        # --- END CHANGE FOR EXPLICIT TYPE ---
                    else:
                        # If type was NOT explicit in XPath, just match by name and add to candidates.
                        # The logic later returns the last match found.
                        logger.debug(f"  Potential match found (implicit type): {child.name} [{child.type}]")
                        text = extract_text(child.range.start_line, child.range.end_line, lines)
                        if text:
                            candidates.append(text)
                        else:
                            logger.warning(f"Could not extract text for implicitly matched child: {child.name} range: {child.range}")

            # This part is now only reached if the type was NOT explicit in the XPath,
            # OR if the explicit type requested was not found among the children.
            if candidates:
                # Return the last match found for implicit type request
                logger.debug(f"Found {len(candidates)} candidates for implicit '{xpath}'. Returning the last one.")
                return candidates[-1]
            else:
                 logger.debug(f"No candidates found matching '{xpath}' within '{parent_name}'.")

        logger.debug(f"Element not found using primary logic for XPath: {xpath}")
        return None # Return None if nothing found

    def extract(self, code: str) -> CodeElementsResult:
        """
        Extract code elements from
        the source code.

        Args:
            code: Source code as string

        Returns:
            CodeElementsResult containing extracted elements
        """
        return self.extraction.extract_all(code)

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
        element_name, parent_name, element_type = XPathParser.get_element_info(xpath)
        if xpath.lower() == 'imports' or (element_type == CodeElementType.IMPORT.value and (not element_name)):
            for element in elements.elements:
                if element.type == CodeElementType.IMPORT:
                    return element
        if parent_name:
            for element in elements.elements:
                if element.type == CodeElementType.CLASS and element.name == parent_name:
                    for child in element.children:
                        # Ensure child has name and type attributes before comparing
                        if hasattr(child, 'name') and child.name == element_name:
                            if element_type and hasattr(child, 'type') and child.type != element_type:
                                continue
                            return child
            return None
        for element in elements.elements:
            # Ensure element has name and type attributes before comparing
            if hasattr(element, 'name') and element.name == element_name:
                if element_type and hasattr(element, 'type') and element.type != element_type:
                    continue
                # Ensure element has parent_name attribute before checking it
                if not hasattr(element, 'parent_name') or not element.parent_name:
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

    def _get_text_for_top_level_element(self, code: str, xpath: str) -> Optional[str]:
        """Helper function to get text for top-level elements (classes, functions)."""
        start_line, end_line = self.find_by_xpath(code, xpath)
        if start_line == 0 and end_line == 0:
            return None
        lines = code.splitlines()
        if start_line > len(lines) or end_line > len(lines):
            return None
        # Re-use the helper function defined in the modified get_text_by_xpath
        def extract_text(start, end, code_lines):
            if start > len(code_lines) or end > len(code_lines) or start <= 0 or end < start:
                logger.warning(f"Invalid line range for extraction: start={start}, end={end}")
                return None
            return '\n'.join(code_lines[start - 1:end])
        return extract_text(start_line, end_line, lines)