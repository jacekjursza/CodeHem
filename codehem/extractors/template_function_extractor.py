"""
Template implementation for function extractor.
"""
import logging
import re
from typing import Dict, List, Optional, Any
from codehem.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class TemplateFunctionExtractor(TemplateExtractor):
    """Template implementation for function extraction."""
    ELEMENT_TYPE = CodeElementType.FUNCTION

    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results for functions."""
        functions = []
        for node, capture_name in query_results:
            if capture_name == 'function_def':
                function_def = node
                name_node = ast_handler.find_child_by_field_name(function_def, 'name')
                if name_node:
                    function_name = ast_handler.get_node_text(name_node, code_bytes)
                    content = ast_handler.get_node_text(function_def, code_bytes)
                    parameters = ExtractorHelpers.extract_parameters(ast_handler, function_def, code_bytes, is_self_or_this=False)
                    return_info = ExtractorHelpers.extract_return_info(ast_handler, function_def, code_bytes)
                    function_info = {'type': 'function', 'name': function_name, 'content': content, 'range': {'start': {'line': function_def.start_point[0] + 1, 'column': function_def.start_point[1]}, 'end': {'line': function_def.end_point[0] + 1, 'column': function_def.end_point[1]}}, 'parameters': parameters, 'return_info': return_info}
                    functions.append(function_info)
            elif capture_name == 'function_name':
                function_name = ast_handler.get_node_text(node, code_bytes)
                function_node = ast_handler.find_parent_of_type(node, 'function_definition')
                if not function_node:
                    function_node = ast_handler.find_parent_of_type(node, 'function_declaration')
                if function_node:
                    content = ast_handler.get_node_text(function_node, code_bytes)
                    parameters = ExtractorHelpers.extract_parameters(ast_handler, function_node, code_bytes, is_self_or_this=False)
                    return_info = ExtractorHelpers.extract_return_info(ast_handler, function_node, code_bytes)
                    function_info = {'type': 'function', 'name': function_name, 'content': content, 'range': {'start': {'line': function_node.start_point[0] + 1, 'column': function_node.start_point[1]}, 'end': {'line': function_node.end_point[0] + 1, 'column': function_node.end_point[1]}}, 'parameters': parameters, 'return_info': return_info}
                    functions.append(function_info)
        return functions

    def _process_regex_results(self, matches, code, context):
        """Process regex match results for functions."""
        functions = []
        for match in matches:
            name = match.group(1)
            signature = match.group(0)
            start_pos = match.start()
            sig_end_pos = match.end()
            code_lines = code.splitlines()
            func_line_num = code[:start_pos].count('\n')
            func_indent = self.get_indentation(signature) if signature.startswith(' ') else ''
            content_lines = [signature]
            function_end_line = func_line_num
            for i, line in enumerate(code_lines[func_line_num + 1:], func_line_num + 1):
                if i >= len(code_lines):
                    break
                line_indent = self.get_indentation(line)
                if not line.strip():
                    content_lines.append(line)
                    continue
                if len(line_indent) <= len(func_indent):
                    break
                content_lines.append(line)
                function_end_line = i
            content = '\n'.join(content_lines)
            start_line = func_line_num + 1
            end_line = function_end_line + 1
            last_newline = code[:start_pos].rfind('\n')
            start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
            end_column = len(code_lines[function_end_line]) if function_end_line < len(code_lines) else 0
            parameters = self._extract_parameters_regex(content)
            return_info = self._extract_return_info_regex(content)
            function_info = {'type': 'function', 'name': name, 'content': content, 'range': {'start': {'line': start_line, 'column': start_column}, 'end': {'line': end_line, 'column': end_column}}, 'parameters': parameters, 'return_info': return_info}
            functions.append(function_info)
        return functions

    def _extract_parameters_regex(self, content):
        """Extract parameters using regex."""
        parameters = []
        param_pattern = '(?:function|def)\\s+\\w+\\s*\\((.*?)\\)'
        param_match = re.search(param_pattern, content)
        if param_match:
            params_str = param_match.group(1)
            param_list = [p.strip() for p in params_str.split(',') if p.strip()]
            for param in param_list:
                param_dict = {'name': param, 'type': None}
                if ':' in param:
                    name_part, type_part = param.split(':', 1)
                    param_dict['name'] = name_part.strip()
                    param_dict['type'] = type_part.strip()
                if param.startswith('...'):
                    param_dict['name'] = param.strip()
                    param_dict['is_rest'] = True
                if '=' in param_dict['name']:
                    name_part, value_part = param_dict['name'].split('=', 1)
                    param_dict['name'] = name_part.strip()
                    param_dict['default'] = value_part.strip()
                    param_dict['optional'] = True
                parameters.append(param_dict)
        return parameters

    def _extract_return_info_regex(self, content):
        """Extract return type information using regex."""
        return_info = {'return_type': None, 'return_values': []}
        return_type_pattern = '(?:def|function)\\s+\\w+\\s*\\([^)]*\\)\\s*->\\s*([^:]+):'
        return_type_match = re.search(return_type_pattern, content)
        if return_type_match:
            return_info['return_type'] = return_type_match.group(1).strip()
        if not return_info['return_type']:
            ts_return_type_pattern = 'function\\s+\\w+\\s*\\([^)]*\\)\\s*:\\s*([^{;]+)'
            ts_return_match = re.search(ts_return_type_pattern, content)
            if ts_return_match:
                return_info['return_type'] = ts_return_match.group(1).strip()
        return_pattern = 'return\\s+([^\\n;]+)'
        return_matches = re.finditer(return_pattern, content)
        for return_match in return_matches:
            return_info['return_values'].append(return_match.group(1).strip())
        return return_info

    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''