"""
Function extractor that uses language-specific handlers.
"""
from typing import Dict, List, Optional, Any
import re
import logging
from codehem.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler
from codehem.languages.registry import extractor

logger = logging.getLogger(__name__)

@extractor
class FunctionExtractor(BaseExtractor):
    """Function extractor using language-specific handlers."""

    @property
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""
        return CodeElementType.FUNCTION

    def supports_language(self, language_code: str) -> bool:
        """Check if this extractor supports the given language."""
        return language_code.lower() in self.handlers

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Extract functions from the provided code.
        
        Args:
            code: The source code to extract from
            context: Optional context information for the extraction
            
        Returns:
            List of extracted functions as dictionaries
        """
        context = context or {}
        language_code = context.get('language_code', 'python').lower()
        if not self.supports_language(language_code):
            return []
        handler = self.handlers[language_code]
        if handler.custom_extract:
            return handler.extract(code, context)
        return self._extract_with_patterns(code, handler, context)

    def _extract_with_patterns(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract using TreeSitter first, fall back to regex if needed."""
        if handler.tree_sitter_query:
            functions = self._extract_with_tree_sitter(code, handler, context)
            if functions:
                return functions
        if handler.regexp_pattern:
            return self._extract_with_regex(code, handler, context)
        return []

    def _extract_with_tree_sitter(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract functions using TreeSitter."""
        ast_handler = self._get_ast_handler(handler.language_code)
        if not ast_handler:
            return []
        try:
            (tree, code_bytes) = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, tree, code_bytes)
            functions = []
            for match in query_results:
                function_def = None
                function_name = None
                for (node, node_type) in match:
                    if node_type == 'function_def':
                        function_def = node
                    elif node_type == 'function_name':
                        function_name = node
                if function_def and function_name:
                    name = ast_handler.get_node_text(function_name, code_bytes)
                    content = ast_handler.get_node_text(function_def, code_bytes)
                    functions.append({'type': 'function', 'name': name, 'content': content, 'range': {'start': {'line': function_def.start_point[0], 'column': function_def.start_point[1]}, 'end': {'line': function_def.end_point[0], 'column': function_def.end_point[1]}}})
            return functions
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {e}')
            return []

    def _extract_with_regex(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract functions using regex."""
        try:
            pattern = handler.regexp_pattern
            matches = re.finditer(pattern, code, re.DOTALL)
            functions = []
            for match in matches:
                name = match.group(1)
                content = match.group(0)
                start_pos = match.start()
                end_pos = match.end()
                lines_before = code[:start_pos].count('\n')
                last_newline = code[:start_pos].rfind('\n')
                start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
                lines_total = code[:end_pos].count('\n')
                last_newline_end = code[:end_pos].rfind('\n')
                end_column = end_pos - last_newline_end - 1 if last_newline_end >= 0 else end_pos
                functions.append({'type': 'function', 'name': name, 'content': content, 'range': {'start': {'line': lines_before, 'column': start_column}, 'end': {'line': lines_total, 'column': end_column}}})
            return functions
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []