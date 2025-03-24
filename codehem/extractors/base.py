"""
Base extractor interface that all extractors must implement.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from codehem.core.engine.ast_handler import ASTHandler
from codehem.core.engine.languages import LANGUAGES, get_parser
from codehem.core.registry import registry
from codehem.models.enums import CodeElementType
logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """Abstract base class for all extractors."""

    @property
    @abstractmethod
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""
        pass

    def __init__(self):
        self.handlers = {}
        self.ast_handlers = {}
        self._load_handlers()

    def _load_handlers(self):
        """Load all language-specific handlers using the language registry."""
        for language_code in registry.get_supported_languages():
            handler = registry.get_handler(language_code, self.element_type.value)
            if handler:
                self.handlers[language_code] = handler
                logger.debug(f'Registered {language_code} {self.element_type} handler from registry')

    def _get_ast_handler(self, language_code: str) -> Optional[ASTHandler]:
        """Get or create an AST handler for the language."""
        language_code = language_code.lower()
        if language_code not in self.ast_handlers:
            try:
                if language_code in LANGUAGES:
                    parser = get_parser(language_code)
                    language = LANGUAGES.get(language_code)
                    if parser and language:
                        self.ast_handlers[language_code] = ASTHandler(language_code, parser, language)
            except Exception as e:
                logger.error(f"Error creating AST handler for {language_code}: {str(e)}")
        return self.ast_handlers.get(language_code)

    @abstractmethod
    def supports_language(self, language_code: str) -> bool:
        """Check if this extractor supports the given language."""
        pass

    @abstractmethod
    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Extract elements from code.
        
        Args:
            code: The source code to extract from
            context: Optional context information for the extraction
            
        Returns:
            List of extracted elements as dictionaries
        """
        pass