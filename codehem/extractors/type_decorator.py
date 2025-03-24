"""
Decorator extractor that uses language-specific handlers.
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
class DecoratorExtractor(BaseExtractor):
    """Decorator extractor using language-specific handlers."""

    @property
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""
        return CodeElementType.DECORATOR

    def supports_language(self, language_code: str) -> bool:
        """Check if this extractor supports the given language."""
        return language_code.lower() in self.handlers

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Extract decorators from the provided code.
        
        Args:
            code: The source code to extract from
            context: Optional context information for the extraction
            
        Returns:
            List of extracted decorators as dictionaries
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
            decorators = self._extract_with_tree_sitter(code, handler, context)
            if decorators:
                return decorators
        if handler.regexp_pattern:
            return self._extract_with_regex(code, handler, context)
        return []

    def _extract_with_tree_sitter(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract decorators using TreeSitter."""
        ast_handler = self._get_ast_handler(handler.language_code)
        if not ast_handler:
            return []
        try:
            (tree, code_bytes) = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, tree, code_bytes)
            decorators = []

            for match in query_results:
                decorator_def = None
                decorator_name = None
                dec_func_def = None
                dec_def_name = None
                func_name = None

                for (node, node_type) in match:
                    if node_type == 'decorator_def':
                        decorator_def = node
                    elif node_type == 'decorator_name':
                        decorator_name = node
                    elif node_type == 'dec_func_def':
                        dec_func_def = node
                    elif node_type == 'dec_def_name':
                        dec_def_name = node
                    elif node_type == 'func_name':
                        func_name = node

                # Handle standalone decorator (class-level)
                if decorator_def and decorator_name:
                    name = ast_handler.get_node_text(decorator_name, code_bytes)
                    content = ast_handler.get_node_text(decorator_def, code_bytes)
                    parent_element = None
                    parent_name = None

                    # Try to find what the decorator decorates
                    parent_node = ast_handler.find_parent_of_type(decorator_def, 'decorated_definition')
                    if parent_node:
                        definition_node = ast_handler.find_child_by_field_name(parent_node, 'definition')
                        if definition_node:
                            if definition_node.type == 'function_definition':
                                # It's a function/method decorator
                                name_node = ast_handler.find_child_by_field_name(definition_node, 'name')
                                if name_node:
                                    parent_name = ast_handler.get_node_text(name_node, code_bytes)
                            elif definition_node.type == 'class_definition':
                                # It's a class decorator
                                name_node = ast_handler.find_child_by_field_name(definition_node, 'name')
                                if name_node:
                                    parent_name = ast_handler.get_node_text(name_node, code_bytes)

                    decorators.append({
                        'type': 'decorator', 
                        'name': name, 
                        'content': content, 
                        'parent_name': parent_name, 
                        'range': {
                            'start': {'line': decorator_def.start_point[0], 'column': decorator_def.start_point[1]}, 
                            'end': {'line': decorator_def.end_point[0], 'column': decorator_def.end_point[1]}
                        }
                    })

                # Handle decorator within decorated_definition
                if dec_func_def and dec_def_name and func_name:
                    name = ast_handler.get_node_text(dec_def_name, code_bytes)
                    parent_name = ast_handler.get_node_text(func_name, code_bytes)
                    decorator_node = ast_handler.find_child_by_field_name(dec_func_def, 'decorator')
                    if decorator_node:
                        content = ast_handler.get_node_text(decorator_node, code_bytes)
                        decorators.append({
                            'type': 'decorator', 
                            'name': name, 
                            'content': content, 
                            'parent_name': parent_name, 
                            'range': {
                                'start': {'line': decorator_node.start_point[0], 'column': decorator_node.start_point[1]}, 
                                'end': {'line': decorator_node.end_point[0], 'column': decorator_node.end_point[1]}
                            }
                        })

            return decorators
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {e}')
            return []

    def _extract_with_regex(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract decorators using regex."""
        try:
            pattern = handler.regexp_pattern
            matches = re.finditer(pattern, code, re.DOTALL)
            decorators = []

            for match in matches:
                name = match.group(1)
                content = match.group(0)

                # Look at what follows the decorator to find the target
                start_pos = match.start()
                end_pos = match.end()

                # Extract text following the decorator to detect what it decorates
                following_text = code[end_pos:].lstrip()

                # Determine parent element by checking what follows the decorator
                parent_name = None
                if following_text.startswith('def '):
                    # It's a function/method decorator
                    func_match = re.match(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', following_text)
                    if func_match:
                        parent_name = func_match.group(1)
                elif following_text.startswith('class '):
                    # It's a class decorator
                    class_match = re.match(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', following_text)
                    if class_match:
                        parent_name = class_match.group(1)

                # Record line positions for the decorator
                lines_before = code[:start_pos].count('\n')
                last_newline = code[:start_pos].rfind('\n')
                start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
                lines_total = code[:end_pos].count('\n')
                last_newline_end = code[:end_pos].rfind('\n')
                end_column = end_pos - last_newline_end - 1 if last_newline_end >= 0 else end_pos

                # Create the decorator entry with the correct parent name
                decorators.append({
                    'type': 'decorator', 
                    'name': name, 
                    'content': content, 
                    'parent_name': parent_name,  # This will correctly identify the decorated element
                    'range': {
                        'start': {'line': lines_before, 'column': start_column}, 
                        'end': {'line': lines_total, 'column': end_column}
                    }
                })

            return decorators
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []
