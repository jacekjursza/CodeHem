"""
Base extractor interface that all extractors must implement.
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from codehem.core.engine.ast_handler import ASTHandler
from codehem.core.engine.languages import LANGUAGES, get_parser
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType
logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """Abstract base class for all extractors."""
    ELEMENT_TYPE: CodeElementType

    def __init__(self, language_code: str, language_type_descriptor: ElementTypeLanguageDescriptor):
        self.language_code = language_code.lower()
        self.descriptor = language_type_descriptor
        self.ast_handler = None

    def _get_ast_handler(self) -> Optional[ASTHandler]:
        """Get or create an AST handler for the language."""
        if not self.ast_handler:
            parser = get_parser(self.language_code)
            language = LANGUAGES.get(self.language_code)
            self.ast_handler = ASTHandler(self.language_code, parser, language)
        return self.ast_handler
    
    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match(r'^(\s*)', line)
        return match.group(1) if match else ''

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> Union[List[Dict], Dict]:
        """
        Extract decorators from the provided code and filter results based on context.

        Args:
            code: The source code to extract from
            context: Optional context information for the extraction

        Returns:
            Filtered list of extracted decorators as dictionaries
        """
        context = context or {}
        if self.descriptor.custom_extract:
            result = self.descriptor.extract(code, context)
        else:
            result = self._extract_with_patterns(code, self.descriptor, context)
        if context:
            result = [item for item in result if all((item.get(k) == v for k, v in context.items()))]
        return result

    @abstractmethod
    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        pass