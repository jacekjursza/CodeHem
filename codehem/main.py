import os
import logging
from typing import List, Optional, Tuple

from .core.engine.xpath_parser import XPathParser
from .core.extraction_service import ExtractionService
from .core.manipulation_service import ManipulationService
from .languages import (
    get_language_service,
    get_language_service_for_code,
    get_language_service_for_file,
    get_supported_languages,
)
from .models.code_element import CodeElement, CodeElementsResult
from .models.enums import CodeElementType
from .models.xpath import CodeElementXPathNode

logger = logging.getLogger(__name__)

class CodeHem:
    """
    Main entry point for CodeHem.
    Provides language-agnostic interface for code manipulation.
    """

    def __init__(self, language_code: str):
        """
        Initialize CodeHem for a specific language.

        Args:
            language_code: Language code (e.g., 'python', 'typescript')

        Raises:
            ValueError: If the language is not supported
        """
        self.language_service = get_language_service(language_code)
        if not self.language_service:
            raise ValueError(f"Unsupported language: {language_code}")

        # Initialize services lazily or ensure they are created correctly
        # Assuming services are now initialized within LanguageService or needed here
        try:
            self.extraction = ExtractionService(language_code)
            self.manipulation = ManipulationService(language_code)
        except ValueError as e:
             # Handle cases where services might fail initialization if LanguageService failed
             logger.error(f"Failed to initialize services for {language_code}: {e}")
             raise # Re-raise the error

    @classmethod
    def from_file_path(cls, file_path: str) -> "CodeHem":
        """
        Create a CodeHem instance based on file extension.

        Args:
            file_path: Path to the file

        Returns:
            CodeHem instance

        Raises:
            ValueError: If the file extension is not supported
        """
        language_service = get_language_service_for_file(file_path)
        if not language_service:
            raise ValueError(
                f"Unsupported file extension: {os.path.splitext(file_path)[1]}"
            )
        return cls(language_service.language_code)

    @classmethod
    def from_raw_code(cls, code: str) -> "CodeHem":
        """
        Create a CodeHem instance by detecting language from code.

        Args:
            code: Source code as string

        Returns:
            CodeHem instance

        Raises:
            ValueError: If the language could not be detected
        """
        language_service = get_language_service_for_code(code)
        if not language_service:
            # Raise error instead of defaulting to Python
            raise ValueError("Could not detect language from code")
            # return cls('python') # Old behavior
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
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            # Try UTF-8 first
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            logger.warning(f"Could not decode {file_path} as UTF-8, trying default encoding.")
            # Fallback to default encoding if UTF-8 fails
            with open(file_path, "r") as f:
                return f.read()
        except IOError as e:
             logger.error(f"IOError reading file {file_path}: {e}")
             raise

    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of element in the code.

        Args:
            code: Code to analyze

        Returns:
            Element type string (from CodeElementType)
        """
        if not self.language_service:
             raise RuntimeError("Language service not initialized.")
        return self.language_service.detect_element_type(code)

    def upsert_element(
        self,
        original_code: str,
        element_type: str,
        name: str,
        new_code: str,
        parent_name: Optional[str] = None,
    ) -> str:
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
        if not self.manipulation:
             raise RuntimeError("Manipulation service not initialized.")
        return self.manipulation.upsert_element(
            original_code, element_type, name, new_code, parent_name
        )

    def _ensure_file_prefix(self, xpath: str) -> str:
        """Internal helper to ensure XPath starts with FILE."""
        root_prefix = XPathParser.ROOT_ELEMENT + "."
        if not xpath.startswith(root_prefix) and not xpath.startswith("["): # Avoid prefixing special selectors like [import]
            logger.debug(f"XPath '{xpath}' does not start with '{root_prefix}'. Prepending it.")
            xpath = root_prefix + xpath
        return xpath

    def upsert_element_by_xpath(
        self, original_code: str, xpath: str, new_code: str
    ) -> str:
        """
        Add or replace an element in the code using XPath expression.
        Automatically prepends "FILE." if missing.

        Args:
            original_code: Original source code
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')
            new_code: New content for the element

        Returns:
            Modified code
        """
        if not self.manipulation:
            raise RuntimeError("Manipulation service not initialized.")
        # Ensure xpath starts with FILE. before passing to manipulation service
        processed_xpath = self._ensure_file_prefix(xpath)
        return self.manipulation.upsert_element_by_xpath(
            original_code, processed_xpath, new_code
        )

    # --- ZMIANA: Wykorzystanie _ensure_file_prefix ---
    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        """
        Find an element's location using an XPath expression.
        Automatically prepends "FILE." if missing.

        Args:
            code: Source code as string
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')

        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        if not self.extraction:
             raise RuntimeError("Extraction service not initialized.")
        processed_xpath = self._ensure_file_prefix(xpath)
        return self.extraction.find_by_xpath(code, processed_xpath)

    # --- ZMIANA: Wykorzystanie _ensure_file_prefix ---
    def get_text_by_xpath(self, code: str, xpath: str) -> Optional[str]:
        """
        Get the text content of an element using an XPath expression.
        Automatically prepends "FILE." if missing.
        Handles property getters/setters and parts like [def], [body].

        Args:
            code: Source code as string
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName.value[property_getter]')

        Returns:
            Text content of the element, or None if not found
        """
        if not self.language_service:
            raise RuntimeError("Language service not initialized.")
        # Ensure xpath starts with FILE. before parsing
        processed_xpath = self._ensure_file_prefix(xpath)
        try:
            # Parse the potentially modified xpath
            xpath_nodes = XPathParser.parse(processed_xpath)
            if not xpath_nodes:
                 logger.warning(f"Could not parse XPath: '{processed_xpath}'")
                 return None
            # Call internal method with parsed nodes
            return self.language_service.get_text_by_xpath_internal(code, xpath_nodes)
        except Exception as e:
             logger.error(f"Error getting text by XPath '{xpath}' (processed: '{processed_xpath}'): {e}", exc_info=True)
             return None

    def extract(self, code: str) -> CodeElementsResult:
        """
        Extract code elements from the source code.

        Args:
            code: Source code as string

        Returns:
            CodeElementsResult containing extracted elements
        """
        if not self.extraction:
             raise RuntimeError("Extraction service not initialized.")
        return self.extraction.extract_all(code)

    @staticmethod
    def _ensure_file_prefix_static(xpath: str) -> str:
        """Static helper to ensure XPath starts with FILE."""
        root_prefix = XPathParser.ROOT_ELEMENT + "."
        if not xpath.startswith(root_prefix) and not xpath.startswith("["):
            # Note: Static method doesn't have logger instance easily
            # print(f"DEBUG: XPath '{xpath}' does not start with '{root_prefix}'. Prepending it.")
            xpath = root_prefix + xpath
        return xpath

    @staticmethod
    def filter(elements: CodeElementsResult, xpath: str = "") -> Optional[CodeElement]:
        """
        Filter code elements based on XPath expression.
        Automatically prepends "FILE." if missing.

        Args:
            elements: CodeElementsResult containing elements
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')

        Returns:
            Matching CodeElement or None if not found
        """
        if not xpath or not elements or not hasattr(elements, 'elements') or not elements.elements:
            return None

        # Ensure xpath starts with FILE. before parsing
        processed_xpath = CodeHem._ensure_file_prefix_static(xpath)

        try:
            # Parse the potentially modified xpath
            element_name, parent_name, element_type = XPathParser.get_element_info(processed_xpath)

            if processed_xpath.lower().endswith(".[import]") or processed_xpath.lower() == "[import]":
                 target_type = CodeElementType.IMPORT.value
                 target_name = "imports" # Assuming collective import element name
                 parent_name = None # Imports are top-level
                 logger.debug(f"Filter: Special handling for import XPath '{processed_xpath}'")
            elif xpath.lower() == 'imports': # Handle simple "imports" case
                 target_type = CodeElementType.IMPORT.value
                 target_name = "imports"
                 parent_name = None
                 logger.debug(f"Filter: Special handling for simple 'imports' XPath")
            else:
                 # Use parsed info, note element_type might be None
                 target_name = element_name
                 target_type = element_type # Can be None

            logger.debug(f"Filter: Searching for name='{target_name}', type='{target_type}', parent='{parent_name}'")

            # --- Search Logic ---
            if parent_name:
                # Find parent first
                parent_match = None
                for el in elements.elements:
                    # Parent must be a CLASS or INTERFACE (or other container types)
                    if el.type in [CodeElementType.CLASS, CodeElementType.INTERFACE] and el.name == parent_name:
                         parent_match = el
                         break
                if not parent_match:
                     logger.debug(f"Filter: Parent '{parent_name}' not found.")
                     return None

                # Search within parent's children
                for child in parent_match.children:
                    name_match = hasattr(child, 'name') and child.name == target_name
                    # Type match: ignore if target_type is None, otherwise compare values
                    type_match = (target_type is None) or (hasattr(child, 'type') and child.type.value == target_type)

                    if name_match and type_match:
                        logger.debug(f"Filter: Found child match: {child.name} ({child.type.value})")
                        return child
                logger.debug(f"Filter: Child '{target_name}' (type: {target_type}) not found in parent '{parent_name}'.")
                return None
            else:
                # Search top-level elements
                for element in elements.elements:
                    name_match = hasattr(element, 'name') and element.name == target_name
                    type_match = (target_type is None) or (hasattr(element, 'type') and element.type.value == target_type)
                    # Ensure it's truly top-level (no parent_name assigned during extraction)
                    is_top_level = not hasattr(element, 'parent_name') or not element.parent_name

                    if name_match and type_match and is_top_level:
                         logger.debug(f"Filter: Found top-level match: {element.name} ({element.type.value})")
                         return element
                logger.debug(f"Filter: Top-level element '{target_name}' (type: {target_type}) not found.")
                return None

        except Exception as e:
             logger.error(f"Error during filtering with XPath '{xpath}': {e}", exc_info=True)
             return None

    @staticmethod
    def parse_xpath(xpath: str) -> List[CodeElementXPathNode]:
        """
        Parse an XPath expression into component nodes.
        Does NOT automatically prepend "FILE.".

        Args:
            xpath: XPath expression (e.g., 'FILE.ClassName.method_name', 'ClassName[interface].method_name[property_getter]')

        Returns:
            List of CodeElementXPathNode objects representing the path
        """
        # This method specifically should NOT add FILE automatically,
        # as its purpose is purely parsing the given string.
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

    # _get_text_for_top_level_element remains private helper, no change needed
    def _get_text_for_top_level_element(
        self, code: str, xpath: str
    ) -> Optional[str]:
        """Helper function to get text for top-level elements (classes, functions)."""
        # This uses find_by_xpath, which now includes the FILE prefix logic
        start_line, end_line = self.find_by_xpath(code, xpath)
        if start_line == 0 and end_line == 0:
            return None

        lines = code.splitlines()
        # Adjust validation if start_line can be > end_line temporarily? No, find_by_xpath should return valid range.
        if start_line > len(lines) or end_line > len(lines) or start_line <= 0 or end_line < start_line:
            logger.warning(f'Invalid line range returned by find_by_xpath for "{xpath}": ({start_line}, {end_line})')
            return None

        def extract_text(start, end, code_lines):
            # Ensure indices are within bounds for slicing
            start_idx = max(0, start - 1)
            end_idx = min(len(code_lines), end)
            if start_idx >= end_idx:
                 logger.warning(f'Adjusted invalid line range for extraction: start_idx={start_idx}, end_idx={end_idx}')
                 return None
            return "\n".join(code_lines[start_idx:end_idx])

        return extract_text(start_line, end_line, lines)