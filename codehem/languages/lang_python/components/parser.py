"""
Python-specific code parser implementation.

This module provides Python-specific implementation of the ICodeParser interface.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from tree_sitter import Parser, Language

from codehem.core.components.base_implementations import BaseCodeParser
from codehem.core.engine.languages import get_parser, PY_LANGUAGE

logger = logging.getLogger(__name__)

class PythonCodeParser(BaseCodeParser):
    """
    Python-specific implementation of the code parser.
    
    Uses tree-sitter to parse Python code into syntax trees.
    """
    
    def __init__(self):
        """Initialize the Python code parser."""
        super().__init__('python')
        self._parser = get_parser('python')
        self._language = PY_LANGUAGE
    
    def parse(self, code: str) -> Tuple[Any, bytes]:
        """
        Parse Python code into a syntax tree.
        
        Args:
            code: Python source code as string
            
        Returns:
            Tuple of (syntax_tree, code_bytes) where syntax_tree is the parsed tree
            and code_bytes is the source code as bytes
        """
        logger.debug('Parsing Python code with tree-sitter')
        code_bytes = code.encode('utf8')
        tree = self._parser.parse(code_bytes)
        return (tree.root_node, code_bytes)
