"""
Language handler for PatchCommander.
Provides a unified interface for language-specific operations.
"""
import re
from typing import Optional

from core.ast_handler import ASTHandler
from core.formatting import get_formatter
from core.languages import get_language_for_file, FILE_EXTENSIONS
from core.manipulator.factory import get_code_manipulator
from core.models import CodeElementsResult, CodeElement, CodeElementType, CodeRange, MetaElementType
from core.services.extraction_service import ExtractionService
from core.strategies import get_strategy
from core.finder.factory import get_code_finder
from core.utils.logs import logger

class CodeHem:
    """
    Central handler for language-specific operations.
    Provides access to appropriate finder and manipulator for a given language.
    """

    def __init__(self, language_code: str):
        """
        Initialize a language handler for a specific language.

        Args:
            language_code: Code of the language (e.g., 'python', 'javascript')
        """
        self.language_code = language_code
        self.finder = get_code_finder(language_code)
        self.manipulator = get_code_manipulator(language_code)
        self.ast_handler = ASTHandler(language_code)
        self.formatter = get_formatter(language_code)
        self.strategy = get_strategy(language_code)

    @classmethod
    def from_file_path(cls, file_path: str) -> 'CodeHem':
        """
        Create a language handler based on file path.

        Args:
            file_path: Path to the file

        Returns:
            LanguageHandler for the detected language
        """
        language_code = get_language_for_file(file_path)
        return cls(language_code)

    @classmethod
    def from_file_extension(cls, file_ext: str) -> 'CodeHem':
        """
        Create a language handler based on file extension.

        Args:
            file_ext: File extension (with or without leading dot)

        Returns:
            LanguageHandler for the detected language

        Raises:
            ValueError: If the extension is not supported
        """
        file_ext = file_ext.lower()
        if not file_ext.startswith('.'):
            file_ext = '.' + file_ext
        for (ext, lang) in FILE_EXTENSIONS.items():
            if ext == file_ext:
                return cls(lang)
        raise ValueError(f'Unsupported file extension: {file_ext}')

    @classmethod
    def from_raw_code(cls, code: str) -> 'CodeHem':
        """
        Create a CodeHem instance from raw code string with language auto-detection.

        Args:
        code: Raw code string

        Returns:
        CodeHem instance with appropriate language settings
        """
        finders = {'python': get_code_finder('python'), 'typescript': get_code_finder('typescript')}
        matching_languages = []
        language_confidences = {}
        for (lang, finder) in finders.items():
            try:
                if finder.can_handle(code):
                    matching_languages.append(lang)
                    if hasattr(finder, 'get_confidence_score'):
                        language_confidences[lang] = finder.get_confidence_score(code)
            except Exception as e:
                logger.warning(f'Error in language detector for {lang}: {str(e)}')
        if len(matching_languages) == 1:
            return cls(matching_languages[0])
        if len(matching_languages) > 1:
            logger.warning(f'Multiple language handlers claim they can handle this code: {matching_languages}.')
            if language_confidences:
                max_score = max(language_confidences.values())
                best_languages = [lang for (lang, score) in language_confidences.items() if score == max_score]
                if len(best_languages) > 1:
                    logger.warning(f'Multiple languages have the same confidence score ({max_score}): {best_languages}. Using the first one.')
                return cls(best_languages[0])
            logger.warning("Couldn't determine best language based on confidence. Using first match.")
            return cls(matching_languages[0])
        logger.warning('No language handler matched the code. Defaulting to Python.')
        return cls('python')

    def content_looks_like_class_definition(self, content: str) -> bool:
        """
        Check if the provided content appears to be a class definition.
        Delegates to the language-specific strategy.

        Args:
            content: The code content to check

        Returns:
            bool: True if content looks like a class definition, False otherwise
        """
        if not content or not content.strip():
            return False
        if self.strategy:
            lines = content.strip().splitlines()
            for line in lines:
                if line.strip():
                    return self.strategy.is_class_definition(line)
        return self.finder.content_looks_like_class_definition(content)

    def extract(self, code: str) -> "CodeElementsResult":
        """
        Extract code elements from source code and return them as Pydantic models.

        Args:
        code: Source code as string

        Returns:
        CodeElementsResult containing all found code elements
        """

        service = ExtractionService(self.finder, self.strategy)
        return service.extract_code_elements(code)

    @staticmethod
    def filter(elements: CodeElementsResult, xpath: str = "") -> Optional[CodeElement]:
        """
        Filter code elements based on xpath expression.

        Args:
        elements: CodeElementsResult containing code elements
        xpath: XPath-like expression for filtering (e.g., "ClassName.method_name", "function_name")

        Returns:
        Matching CodeElement or None if not found
        """
        if not xpath or not elements or not hasattr(elements, 'elements'):
            return None

        # Special case for imports
        if xpath.lower() == "imports":
            for element in elements.elements:
                if element.type == CodeElementType.IMPORT:
                    return element

        # Handle class.method pattern
        if "." in xpath:
            parts = xpath.split(".", 1)
            if len(parts) == 2:
                class_name, member_name = parts

                # Find the class element
                for element in elements.elements:
                    if element.type == CodeElementType.CLASS and element.name == class_name:
                        # Search for method/property within the class's children
                        for child in element.children:
                            if hasattr(child, 'name') and child.name == member_name:
                                return child
            return None

        # Handle standalone classes and functions
        for element in elements.elements:
            if hasattr(element, 'name') and element.name == xpath:
                if element.parent_name is None or element.parent_name == "":  # Ensure it's not a child element
                    return element

        return None
