import os
import logging
from typing import List, Optional, Tuple

from .core.engine.xpath_parser import XPathParser
from .core.extraction_service import ExtractionService
from .core.manipulation_service import ManipulationService
from .core.post_processors.factory import PostProcessorFactory
from .languages import (
    get_language_service,
    get_language_service_for_code,
    get_language_service_for_file,
    get_supported_languages,
)
from .models.code_element import CodeElement, CodeElementsResult
from .models.enums import CodeElementType
from .models.xpath import CodeElementXPathNode
from .builder import build_class, build_function, build_method

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
        try:
            # Initialize extraction service
            logger.debug(f"Using ExtractionService for {language_code}")
            self.extraction = ExtractionService(language_code)

            # Initialize manipulation service
            self.manipulation = ManipulationService(language_code)
        except ValueError as e:
            # Handle cases where services might fail initialization if LanguageService failed
            logger.error(f"Failed to initialize services for {language_code}: {e}")
            raise  # Re-raise the error

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
    def supported_post_processors() -> List[str]:
        """
        Get a list of language codes with post-processor support.

        Returns:
            List of languages with post-processor support
        """
        return PostProcessorFactory.get_supported_languages()

    @staticmethod
    def open_workspace(repo_root: str) -> "Workspace":
        """Open a workspace rooted at ``repo_root`` and build its index."""
        from codehem.core.workspace import Workspace

        return Workspace.open(repo_root)

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
            logger.warning(
                f"Could not decode {file_path} as UTF-8, trying default encoding."
            )
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
        if not xpath.startswith(root_prefix) and not xpath.startswith(
            "["
        ):  # Avoid prefixing special selectors like [import]
            logger.debug(
                f"XPath '{xpath}' does not start with '{root_prefix}'. Prepending it."
            )
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

    def find_by_xpath(self, code: str, xpath: str) -> Optional[Tuple[int, int]]:
        """
        Find an element's location using an XPath expression.
        Automatically prepends "FILE." if missing.

        Args:
            code: Source code as string
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')

        Returns:
            Tuple of (start_line, end_line) or None if not found
        """
        if not self.extraction:
            raise RuntimeError("Extraction service not initialized.")
        processed_xpath = self._ensure_file_prefix(xpath)
        return self.extraction.find_by_xpath(code, processed_xpath)

    def get_text_by_xpath(
        self, code: str, xpath: str, return_hash: bool = False
    ) -> Optional[str]:
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
            text = self.language_service.get_text_by_xpath_internal(code, xpath_nodes)
            if text is None:
                return None
            if return_hash:
                from codehem.core.utils.hashing import sha256_code

                return text, sha256_code(text)
            return text
        except Exception as e:
            logger.error(
                f"Error getting text by XPath '{xpath}' (processed: '{processed_xpath}'): {e}",
                exc_info=True,
            )
            return None

    def extract(self, code: str) -> CodeElementsResult:
        """
        Extract code elements from the source code.

        Args:
            code: Source code as string

        Returns:
            CodeElementsResult containing extracted elements
        """
        # Special handling to use component-based orchestrators where available
        if self.language_service and self.language_service.language_code in ['typescript', 'javascript', 'python']:
            lang = self.language_service.language_code
            logger.debug(f'CodeHem: Using {lang.capitalize()} orchestrator for extraction')
            try:
                if lang in ['typescript', 'javascript']:
                    from codehem.languages.lang_typescript.components.orchestrator import TypeScriptExtractionOrchestrator
                    from codehem.languages.lang_typescript.components.post_processor import TypeScriptPostProcessor

                    post_processor = TypeScriptPostProcessor()
                    orchestrator = TypeScriptExtractionOrchestrator(post_processor)
                else:  # python
                    from codehem.languages.lang_python.components.orchestrator import PythonExtractionOrchestrator
                    from codehem.languages.lang_python.components.post_processor import PythonPostProcessor

                    post_processor = PythonPostProcessor()
                    orchestrator = PythonExtractionOrchestrator(post_processor)

                result = orchestrator.extract_all(code)
                logger.debug(f'CodeHem: {lang.capitalize()} orchestrator found {len(result.elements)} elements')
                return result
            except Exception as e:
                logger.error(f'CodeHem: Error with {lang.capitalize()} orchestrator, falling back to extraction service: {e}', exc_info=True)
                # Fall back to regular extraction service
        
        # Default behavior for other languages
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
        Delegates to the ElementFilter utility class.

        Args:
            elements: CodeElementsResult containing elements
            xpath: XPath expression (e.g., 'ClassName.method_name', 'ClassName[interface].method_name[property_getter]')

        Returns:
            Matching CodeElement or None if not found
        """
        # Use ElementFilter utility to avoid duplicating filtering logic
        from codehem.models.element_filter import ElementFilter

        # Process the xpath first to ensure FILE. prefix (for compatibility)
        if (
            xpath
            and not xpath.startswith(XPathParser.ROOT_ELEMENT + ".")
            and not xpath.startswith("[")
        ):
            processed_xpath = CodeHem._ensure_file_prefix_static(xpath)
        else:
            processed_xpath = xpath

        return ElementFilter.filter(elements, processed_xpath)

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
    def _get_text_for_top_level_element(self, code: str, xpath: str) -> Optional[str]:
        """Helper function to get text for top-level elements (classes, functions)."""
        # This uses find_by_xpath, which now includes the FILE prefix logic
        line_range = self.find_by_xpath(code, xpath)
        if not line_range:
            return None
        start_line, end_line = line_range

        lines = code.splitlines()
        # Adjust validation if start_line can be > end_line temporarily? No, find_by_xpath should return valid range.
        if (
            start_line > len(lines)
            or end_line > len(lines)
            or start_line <= 0
            or end_line < start_line
        ):
            logger.warning(
                f'Invalid line range returned by find_by_xpath for "{xpath}": ({start_line}, {end_line})'
            )
            return None

        def extract_text(start, end, code_lines):
            # Ensure indices are within bounds for slicing
            start_idx = max(0, start - 1)
            end_idx = min(len(code_lines), end)
            if start_idx >= end_idx:
                logger.warning(
                    f"Adjusted invalid line range for extraction: start_idx={start_idx}, end_idx={end_idx}"
                )
                return None
            return "\n".join(code_lines[start_idx:end_idx])

        return extract_text(start_line, end_line, lines)

    def get_element_hash(self, code: str, xpath: str) -> Optional[str]:
        """Return SHA256 hash of the code fragment specified by XPath."""
        text = self.get_text_by_xpath(code, xpath)
        if text is None:
            return None
        from codehem.core.utils.hashing import sha256_code

        return sha256_code(text)

    def apply_patch(
        self,
        original_code: str,
        xpath: str,
        new_code: str,
        mode: str = "replace",
        original_hash: Optional[str] = None,
        dry_run: bool = False,
        return_format: str = "json",
    ) -> object:
        """Apply a patch to the code fragment selected by XPath."""
        location = self.find_by_xpath(original_code, xpath)
        if not location:
            from codehem.core.error_handling import ElementNotFoundError

            raise ElementNotFoundError("xpath", xpath)
        start_line, end_line = location
        lines = original_code.splitlines()
        old_fragment = "\n".join(lines[start_line - 1 : end_line])
        from codehem.core.utils.hashing import sha256_code

        current_hash = sha256_code(old_fragment)
        if original_hash is not None and original_hash != current_hash:
            from codehem.core.error_handling import WriteConflictError

            raise WriteConflictError(
                expected_hash=original_hash,
                actual_hash=current_hash,
            )
        if mode == "replace":
            new_fragment_lines = new_code.splitlines()
        elif mode == "append":
            new_fragment_lines = (
                lines[start_line - 1 : end_line] + new_code.splitlines()
            )
        elif mode == "prepend":
            new_fragment_lines = (
                new_code.splitlines() + lines[start_line - 1 : end_line]
            )
        else:
            from codehem.core.error_handling import InvalidManipulationError

            raise InvalidManipulationError("apply_patch", f"Unknown mode: {mode}")
        patched_lines = lines[: start_line - 1] + new_fragment_lines + lines[end_line:]
        patched_code = "\n".join(patched_lines)
        from difflib import unified_diff

        diff_lines = list(
            unified_diff(
                original_code.splitlines(True),
                patched_code.splitlines(True),
                fromfile="original",
                tofile="patched",
            )
        )
        if dry_run:
            return "".join(diff_lines)

        lines_added = sum(
            1
            for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        lines_removed = sum(
            1
            for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )
        result = {
            "status": "ok",
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "new_hash": sha256_code("\n".join(new_fragment_lines)),
            "code": patched_code,
        }
        if return_format == "text":
            return patched_code
        return result

    def new_function(
        self,
        original_code: str,
        name: str,
        args: Optional[List[str]] = None,
        body: Optional[List[str]] = None,
        decorators: Optional[List[str]] = None,
        return_format: str = "text",
    ) -> object:
        """Create and insert a new top-level function."""
        snippet = build_function(name, args, body, decorators)
        patched = self.upsert_element(
            original_code, CodeElementType.FUNCTION.value, name, snippet
        )
        if return_format == "json":
            return {"status": "ok", "code": patched}
        return patched

    def new_class(
        self,
        original_code: str,
        name: str,
        body: Optional[List[str]] = None,
        decorators: Optional[List[str]] = None,
        return_format: str = "text",
    ) -> object:
        """Create and insert a new class."""
        snippet = build_class(name, body, decorators)
        patched = self.upsert_element(
            original_code, CodeElementType.CLASS.value, name, snippet
        )
        if return_format == "json":
            return {"status": "ok", "code": patched}
        return patched

    def new_method(
        self,
        original_code: str,
        parent: str,
        name: str,
        args: Optional[List[str]] = None,
        body: Optional[List[str]] = None,
        decorators: Optional[List[str]] = None,
        return_format: str = "text",
    ) -> object:
        """Create and insert a new method inside a parent class."""
        snippet = build_method(name, args, body, decorators)
        patched = self.upsert_element(
            original_code,
            CodeElementType.METHOD.value,
            name,
            snippet,
            parent_name=parent,
        )
        if return_format == "json":
            return {"status": "ok", "code": patched}
        return patched

    def short_xpath(self, elements: CodeElementsResult, element: CodeElement) -> str:
        """Return the shortest unique XPath for ``element``."""

        def find_path(
            current: CodeElement, path: List[CodeElement]
        ) -> List[CodeElement]:
            if current is element:
                return path + [current]
            for child in getattr(current, "children", []):
                result = find_path(child, path + [current])
                if result:
                    return result
            return []

        path_elements: List[CodeElement] = []
        for top in elements.elements:
            path_elements = find_path(top, [])
            if path_elements:
                break
        if not path_elements:
            return ""

        nodes = [CodeElementXPathNode(type=CodeElementType.FILE.value)]
        for el in path_elements:
            nodes.append(CodeElementXPathNode(name=el.name, type=el.type.value))
        full_nodes = nodes[:]
        for i in range(len(nodes)):
            candidate = XPathParser.to_string(nodes[i:])
            found = CodeHem.filter(elements, candidate)
            if found is element:
                return candidate
        return XPathParser.to_string(full_nodes)
