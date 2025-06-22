"""
TypeScript code parser component.

This module provides the TypeScript implementation of the ICodeParser interface,
responsible for parsing TypeScript/JavaScript code into a syntax tree using Tree-sitter.
"""

import logging
from typing import Any, Tuple

from codehem.core.components.interfaces import ICodeParser
from codehem.core.components.base_implementations import BaseCodeParser
from codehem.core.engine.languages import get_parser, LANGUAGES

logger = logging.getLogger(__name__)


class TypeScriptCodeParser(BaseCodeParser):
    """
    TypeScript implementation of the ICodeParser interface.
    
    Parses TypeScript/JavaScript code into a syntax tree using the Tree-sitter parser.
    """
    
    def __init__(self):
        """Initialize the TypeScript code parser."""
        super().__init__('typescript')
        self.parser = get_parser('typescript')
        self.language = LANGUAGES['typescript']
        # Set the language for the parser - use language property
        self.parser.language = self.language
    
    def parse(self, code: str) -> Tuple[Any, bytes]:
        """
        Parse TypeScript code into a syntax tree.
        
        Args:
            code: The TypeScript/JavaScript code to parse
            
        Returns:
            A tuple containing the parsed syntax tree and the code as bytes
        """
        logger.debug("Parsing TypeScript code")
        
        try:
            code_bytes = code.encode('utf-8')
            tree = self.parser.parse(code_bytes)
            logger.debug("Successfully parsed TypeScript code")
            return tree, code_bytes
        except Exception as e:
            logger.error(f"Error parsing TypeScript code: {e}", exc_info=True)
            raise
