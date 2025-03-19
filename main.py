"""
Language handler for PatchCommander.
Provides a unified interface for language-specific operations.
"""

from typing import Optional, Dict, List, Any

from core.ast_handler import ASTHandler
from core.finder.factory import get_code_finder
from core.formatting import get_formatter
from core.strategies import get_strategy
from core.manipulator.factory import get_code_manipulator
from core.utils.logs import logger
from core.languages import get_language_for_file, FILE_EXTENSIONS, LANGUAGES


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
    def from_raw_code(cls, text: str) -> Optional['CodeHem']:
        """
        Try to determine the language from raw code.
        Iterates through registered finders and checks syntax.

        Args:
            text: Source code text

        Returns:
            LanguageHandler if language detected, None otherwise
        """
        language_codes = list(LANGUAGES.keys())
        for lang in language_codes:
            try:
                finder = get_code_finder(lang)
                if finder.is_correct_syntax(text):
                    logger.debug(f'[blue]Detected language: {lang}[/blue]')
                    return cls(lang)
            except Exception as e:
                logger.debug(f'[dim]Error checking syntax for {lang}: {e}[/dim]')
                continue
        logger.debug('[yellow]Could not determine language from code[/yellow]')
        return None

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
            
        # Use the strategy if available
        if self.strategy:
            lines = content.strip().splitlines()
            # Check the first non-empty line
            for line in lines:
                if line.strip():
                    return self.strategy.is_class_definition(line)
        
        # Fall back to the finder if strategy not available
        return self.finder.content_looks_like_class_definition(content)

    def extract_code_elements(self, code: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract code elements (classes, methods, functions) from code.
        
        Args:
            code: Source code to analyze
            
        Returns:
            Dictionary with 'classes', 'methods', and 'functions' keys,
            each containing a list of dictionaries with element information
        """
        if not self.strategy:
            return {'classes': [], 'methods': [], 'functions': []}
            
        lines = code.splitlines()
        classes = []
        methods = []
        functions = []
        
        for i, line in enumerate(lines):
            if self.strategy.is_class_definition(line):
                class_name = self.strategy.extract_class_name(line)
                if class_name:
                    classes.append({
                        'name': class_name,
                        'line': i + 1,
                        'content': line
                    })
            elif self.strategy.is_method_definition(line):
                method_name = self.strategy.extract_method_name(line)
                if method_name:
                    methods.append({
                        'name': method_name,
                        'line': i + 1,
                        'content': line
                    })
            elif self.strategy.is_function_definition(line):
                function_name = self.strategy.extract_function_name(line)
                if function_name:
                    functions.append({
                        'name': function_name,
                        'line': i + 1,
                        'content': line
                    })
                    
        return {
            'classes': classes,
            'methods': methods,
            'functions': functions
        }