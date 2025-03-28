"""
Base extraction logic for standardizing extraction across languages.
"""
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from codehem.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
logger = logging.getLogger(__name__)

class ExtractorHelpers:
    """Common utilities for extraction."""

    @staticmethod
    def extract_parameters(ast_handler, node, code_bytes, is_self_or_this=True):
        """Extract parameters from a function/method node."""
        parameters = []
        params_node = ast_handler.find_child_by_field_name(node, 'parameters')
        if not params_node:
            return parameters
        for i in range(params_node.named_child_count):
            param_node = params_node.named_child(i)
            if i == 0 and is_self_or_this:
                first_param_text = ast_handler.get_node_text(param_node, code_bytes)
                if first_param_text in ['self', 'this']:
                    continue
            param_info = ExtractorHelpers.extract_parameter(ast_handler, param_node, code_bytes)
            if param_info:
                parameters.append(param_info)
        return parameters

    @staticmethod
    def extract_parameter(ast_handler, param_node, code_bytes):
        """Extract information about a parameter."""
        if param_node.type == 'identifier':
            name = ast_handler.get_node_text(param_node, code_bytes)
            return {'name': name, 'type': None}
        return None

    @staticmethod
    def extract_return_info(ast_handler, function_node, code_bytes):
        """Extract return type information."""
        return_type = None
        return_values = []
        return_type_node = ast_handler.find_child_by_field_name(function_node, 'return_type')
        if return_type_node:
            return_type = ast_handler.get_node_text(return_type_node, code_bytes)
        body_node = ast_handler.find_child_by_field_name(function_node, 'body')
        if body_node:
            try:
                return_query = '(return_statement) @return_stmt'
                return_results = ast_handler.execute_query(return_query, body_node, code_bytes)
                for node, node_type in return_results:
                    if node_type == 'return_stmt':
                        stmt_text = ast_handler.get_node_text(node, code_bytes)
                        if stmt_text.startswith('return '):
                            return_values.append(stmt_text[7:].strip())
            except Exception:
                function_text = ast_handler.get_node_text(function_node, code_bytes)
                return_regex = 'return\\s+(.+?)(?:\\n|$)'
                for match in re.finditer(return_regex, function_text):
                    return_values.append(match.group(1).strip())
        return {'return_type': return_type, 'return_values': return_values}

    @staticmethod
    def extract_decorators(ast_handler, node, code_bytes):
        """Extract decorators from a node."""
        decorators = []
        parent_node = node.parent
        if parent_node and parent_node.type == 'decorated_definition':
            for child_idx in range(parent_node.named_child_count):
                child = parent_node.named_child(child_idx)
                if child.type == 'decorator':
                    name_node = child.child_by_field_name('name')
                    if name_node:
                        decorator_name = ast_handler.get_node_text(name_node, code_bytes)
                        decorator_content = ast_handler.get_node_text(child, code_bytes)
                        decorators.append({'name': decorator_name, 'content': decorator_content})
        return decorators

class TemplateExtractor(BaseExtractor):
    """Template method pattern for extractors."""

    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract using TreeSitter first, fall back to regex if needed."""
        if handler.tree_sitter_query:
            elements = self._extract_with_tree_sitter(code, handler, context)
            if elements:
                return elements
        if handler.regexp_pattern:
            return self._extract_with_regex(code, handler, context)
        return []

    def _extract_with_tree_sitter(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract elements using TreeSitter."""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            return []
        try:
            root, code_bytes = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
            return self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {str(e)}')
            return []

    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results."""
        return []

    def _extract_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract elements using regex."""
        try:
            pattern = handler.regexp_pattern
            matches = re.finditer(pattern, code, re.DOTALL)
            return self._process_regex_results(matches, code, context)
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []

    def _process_regex_results(self, matches, code, context):
        """Process regex match results."""
        return []