"""
Function extractor that uses language-specific handlers.
"""
from typing import Dict, List, Optional, Any
import re
import logging
from codehem.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class FunctionExtractor(BaseExtractor):
    """Function extractor using language-specific handlers."""
    ELEMENT_TYPE = CodeElementType.FUNCTION

    @property
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""
        return self.ELEMENT_TYPE

    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract using TreeSitter first, fall back to regex if needed."""
        if handler.tree_sitter_query:
            functions = self._extract_with_tree_sitter(code, handler, context)
            if functions:
                return functions
        if handler.regexp_pattern:
            return self._extract_with_regex(code, handler, context)
        return []

    def _extract_with_tree_sitter(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract functions using TreeSitter."""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            return []
        try:
            (root, code_bytes) = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
            functions = []
            for (node, capture_name) in query_results:
                if capture_name == 'function_def':
                    function_def = node
                elif capture_name == 'func_name':
                    func_name = ast_handler.get_node_text(node, code_bytes)
                    function_node = ast_handler.find_parent_of_type(node, 'function_definition')
                    if function_node:
                        (start_line, end_line) = ast_handler.get_node_range(function_node)
                        content = ast_handler.get_node_text(function_node, code_bytes)
                        parameters = self._extract_parameters(function_node, code_bytes, ast_handler)
                        return_info = self._extract_return_info(function_node, code_bytes, ast_handler)
                        functions.append({'type': 'function', 'name': func_name, 'content': content, 'range': {'start': {'line': start_line, 'column': function_node.start_point[1]}, 'end': {'line': end_line, 'column': function_node.end_point[1]}}, 'parameters': parameters, 'return_info': return_info})
            return functions
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {str(e)}')
            return []

    def _extract_parameters(self, function_node, code_bytes, ast_handler) -> List[Dict]:
        """
        Extract detailed parameter information from a function.
        
        Args:
            function_node: Function node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            List of parameter dictionaries with name, type, and default value
        """
        parameters = []
        params_node = None
        for child_idx in range(function_node.named_child_count):
            child = function_node.named_child(child_idx)
            if child.type == 'parameters':
                params_node = child
                break
        if not params_node:
            return parameters
        for child_idx in range(params_node.named_child_count):
            child = params_node.named_child(child_idx)
            if child.type == 'identifier':
                name = ast_handler.get_node_text(child, code_bytes)
                parameters.append({'name': name, 'type': None})
            elif child.type == 'typed_parameter':
                name_node = child.child_by_field_name('name')
                type_node = child.child_by_field_name('type')
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    param_dict = {'name': name, 'type': None}
                    if type_node:
                        param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                    parameters.append(param_dict)
            elif child.type == 'default_parameter':
                name_node = child.child_by_field_name('name')
                value_node = child.child_by_field_name('value')
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    param_dict = {'name': name, 'type': None, 'optional': True}
                    if value_node:
                        param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                    parameters.append(param_dict)
            elif child.type == 'typed_default_parameter':
                name_node = child.child_by_field_name('name')
                type_node = child.child_by_field_name('type')
                value_node = child.child_by_field_name('value')
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    param_dict = {'name': name, 'type': None, 'optional': True}
                    if type_node:
                        param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                    if value_node:
                        param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                    parameters.append(param_dict)
        return parameters

    def _extract_return_info(self, function_node, code_bytes, ast_handler) -> Dict:
        """
        Extract return type information from a function.
        
        Args:
            function_node: Function node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            Dictionary with return_type and return_values
        """
        return_type = None
        return_values = []
        return_type_node = function_node.child_by_field_name('return_type')
        if return_type_node:
            return_type = ast_handler.get_node_text(return_type_node, code_bytes)
        body_node = function_node.child_by_field_name('body')
        if body_node:
            try:
                return_query = '(return_statement (_) @return_value)'
                return_results = ast_handler.execute_query(return_query, body_node, code_bytes)
                for (node, capture_name) in return_results:
                    if capture_name == 'return_value':
                        return_values.append(ast_handler.get_node_text(node, code_bytes))
            except Exception as e:
                try:
                    alt_query = '(return_statement) @return_stmt'
                    return_stmts = ast_handler.execute_query(alt_query, body_node, code_bytes)
                    for (node, capture_name) in return_stmts:
                        if capture_name == 'return_stmt':
                            stmt_text = ast_handler.get_node_text(node, code_bytes)
                            if stmt_text.startswith('return '):
                                return_values.append(stmt_text[7:].strip())
                except Exception:
                    function_text = ast_handler.get_node_text(function_node, code_bytes)
                    return_regex = 'return\\s+(.+?)(?:\\n|$)'
                    for match in re.finditer(return_regex, function_text):
                        return_values.append(match.group(1).strip())
        return {'return_type': return_type, 'return_values': return_values}

    def _extract_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
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
                param_pattern = 'def\\s+\\w+\\s*\\((.*?)\\)'
                param_match = re.search(param_pattern, content)
                parameters = []
                if param_match:
                    params_str = param_match.group(1)
                    param_list = [p.strip() for p in params_str.split(',') if p.strip()]
                    for param in param_list:
                        param_dict = {'name': param, 'type': None}
                        if ':' in param:
                            (name_part, type_part) = param.split(':', 1)
                            param_dict['name'] = name_part.strip()
                            param_dict['type'] = type_part.strip()
                        if '=' in param_dict['name']:
                            (name_part, value_part) = param_dict['name'].split('=', 1)
                            param_dict['name'] = name_part.strip()
                            param_dict['default'] = value_part.strip()
                            param_dict['optional'] = True
                        parameters.append(param_dict)
                return_info = {'return_type': None, 'return_values': []}
                return_type_pattern = 'def\\s+\\w+\\s*\\([^)]*\\)\\s*->\\s*([^:]+):'
                return_type_match = re.search(return_type_pattern, content)
                if return_type_match:
                    return_info['return_type'] = return_type_match.group(1).strip()
                return_pattern = 'return\\s+([^;]+)'
                return_matches = re.finditer(return_pattern, content)
                for return_match in return_matches:
                    return_info['return_values'].append(return_match.group(1).strip())
                functions.append({'type': 'function', 'name': name, 'content': content, 'range': {'start': {'line': lines_before, 'column': start_column}, 'end': {'line': lines_total, 'column': end_column}}, 'parameters': parameters, 'return_info': return_info})
            return functions
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []