"""
Template implementation for method extractor.
"""
import logging
import re
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class TemplateMethodExtractor(TemplateExtractor):
    """Template implementation for method extraction."""
    ELEMENT_TYPE = CodeElementType.METHOD

    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results for methods."""
        methods = []
        method_nodes = {}
        decorated_methods = {}
        decorator_nodes = {}
        for node, capture_name in query_results:
            if capture_name == 'method_def':
                name_node = ast_handler.find_child_by_field_name(node, 'name')
                if name_node:
                    method_name = ast_handler.get_node_text(name_node, code_bytes)
                    method_nodes[method_name] = node
            elif capture_name == 'decorated_method_def':
                def_node = ast_handler.find_child_by_field_name(node, 'definition')
                if def_node:
                    name_node = ast_handler.find_child_by_field_name(def_node, 'name')
                    if name_node:
                        method_name = ast_handler.get_node_text(name_node, code_bytes)
                        decorated_methods[method_name] = node
            elif capture_name == 'decorator':
                self._process_decorator(node, decorator_nodes, ast_handler, code_bytes)
            elif capture_name == 'method_name':
                method_name = ast_handler.get_node_text(node, code_bytes)
                parent = node.parent
                if parent and parent.type in ['function_definition', 'method_definition']:
                    grand_parent = parent.parent
                    if grand_parent and grand_parent.type == 'decorated_definition':
                        decorated_methods[method_name] = grand_parent
                    else:
                        method_nodes[method_name] = parent
        self._process_regular_methods(method_nodes, methods, code_bytes, ast_handler, context, decorator_nodes)
        self._process_decorated_methods(decorated_methods, methods, code_bytes, ast_handler, context, decorator_nodes)
        return methods

    def _process_decorator(self, node, decorator_nodes, ast_handler, code_bytes):
        """Process a decorator node and add to dictionary."""
        parent = node.parent
        if parent and parent.type == 'decorated_definition':
            def_node = ast_handler.find_child_by_field_name(parent, 'definition')
            if def_node and def_node.type in ['function_definition', 'method_definition']:
                name_node = ast_handler.find_child_by_field_name(def_node, 'name')
                if name_node:
                    method_name = ast_handler.get_node_text(name_node, code_bytes)
                    if method_name not in decorator_nodes:
                        decorator_nodes[method_name] = []
                    decorator_content = ast_handler.get_node_text(node, code_bytes)
                    decorator_name = None
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        decorator_name = ast_handler.get_node_text(name_node, code_bytes)
                    elif node.named_child_count > 0:
                        for i in range(node.named_child_count):
                            child = node.named_child(i)
                            if child.type == 'identifier':
                                decorator_name = ast_handler.get_node_text(child, code_bytes)
                                break
                    decorator_nodes[method_name].append({'name': decorator_name, 'content': decorator_content})

    def _process_regular_methods(self, method_nodes, methods, code_bytes, ast_handler, context, decorator_nodes):
        """Process regular (non-decorated) methods."""
        for method_name, method_node in method_nodes.items():
            content = ast_handler.get_node_text(method_node, code_bytes)
            class_name = self._get_class_name(method_node, context, ast_handler, code_bytes)
            parameters = ExtractorHelpers.extract_parameters(ast_handler, method_node, code_bytes)
            return_info = ExtractorHelpers.extract_return_info(ast_handler, method_node, code_bytes)
            decorators = decorator_nodes.get(method_name, [])
            method_info = {'type': 'method', 'name': method_name, 'content': content, 'class_name': class_name, 'range': {'start': {'line': method_node.start_point[0] + 1, 'column': method_node.start_point[1]}, 'end': {'line': method_node.end_point[0] + 1, 'column': method_node.end_point[1]}}, 'decorators': decorators, 'parameters': parameters, 'return_info': return_info}
            methods.append(method_info)

    def _process_decorated_methods(self, decorated_methods, methods, code_bytes, ast_handler, context, decorator_nodes):
        """Process decorated methods."""
        for method_name, decorated_node in decorated_methods.items():
            def_node = ast_handler.find_child_by_field_name(decorated_node, 'definition')
            if not def_node:
                continue
            content = ast_handler.get_node_text(decorated_node, code_bytes)
            class_name = self._get_class_name(decorated_node, context, ast_handler, code_bytes)
            parameters = ExtractorHelpers.extract_parameters(ast_handler, def_node, code_bytes)
            return_info = ExtractorHelpers.extract_return_info(ast_handler, def_node, code_bytes)
            decorators = decorator_nodes.get(method_name, [])
            if not decorators:
                decorators = self._extract_decorators_from_node(decorated_node, ast_handler, code_bytes)
            method_info = {'type': 'method', 'name': method_name, 'content': content, 'class_name': class_name, 'range': {'start': {'line': decorated_node.start_point[0] + 1, 'column': decorated_node.start_point[1]}, 'end': {'line': decorated_node.end_point[0] + 1, 'column': decorated_node.end_point[1]}}, 'decorators': decorators, 'parameters': parameters, 'return_info': return_info}
            methods.append(method_info)

    def _extract_decorators_from_node(self, decorated_node, ast_handler, code_bytes):
        """Extract decorators directly from a decorated definition node."""
        decorators = []
        for i in range(decorated_node.named_child_count):
            child = decorated_node.named_child(i)
            if child.type == 'decorator':
                decorator_content = ast_handler.get_node_text(child, code_bytes)
                decorator_name = None
                name_node = child.child_by_field_name('name')
                if name_node:
                    decorator_name = ast_handler.get_node_text(name_node, code_bytes)
                elif child.named_child_count > 0:
                    for j in range(child.named_child_count):
                        sub_child = child.named_child(j)
                        if sub_child.type == 'identifier':
                            decorator_name = ast_handler.get_node_text(sub_child, code_bytes)
                            break
                decorators.append({'name': decorator_name, 'content': decorator_content})
        return decorators

    def _get_class_name(self, node, context, ast_handler, code_bytes):
        """Get class name for a method node."""
        class_name = None
        if context.get('class_name'):
            class_name = context.get('class_name')
        else:
            class_node = ast_handler.find_parent_of_type(node, 'class_definition')
            if not class_node:
                class_node = ast_handler.find_parent_of_type(node, 'class_declaration')
            if class_node:
                class_name_node = ast_handler.find_child_by_field_name(class_node, 'name')
                if class_name_node:
                    class_name = ast_handler.get_node_text(class_name_node, code_bytes)
        return class_name

    def _process_regex_results(self, matches, code, context):
        """Process regex match results for methods."""
        methods = []
        class_name = context.get('class_name')
        class_content = code
        class_offset = 0
        if class_name:
            class_pattern = f'class\\s+{re.escape(class_name)}(?:\\s*\\([^)]*\\))?\\s*:(.*?)(?=\\n(?:class|def\\s+\\w+\\s*\\([^s]|$))'
            class_match = re.search(class_pattern, code, re.DOTALL)
            if class_match:
                class_content = class_match.group(1)
                class_offset = class_match.start(1)
        base_indent = ' ' * 4 if class_name else ''
        pattern = f'{re.escape(base_indent)}' + self.descriptor.regexp_pattern if class_name else self.descriptor.regexp_pattern
        for match in matches:
            name = match.group(1)
            signature = match.group(0)
            start_pos = match.start() + class_offset if class_name else match.start()
            sig_end_pos = match.end() + class_offset if class_name else match.end()
            code_lines = code.splitlines()
            method_line_num = code[:start_pos].count('\n')
            method_indent = self.get_indentation(signature) if signature.startswith(' ') else ''
            content_lines = [signature]
            method_end_line = method_line_num
            for i, line in enumerate(code_lines[method_line_num + 1:], method_line_num + 1):
                if i >= len(code_lines):
                    break
                line_indent = self.get_indentation(line)
                if not line.strip():
                    content_lines.append(line)
                    continue
                if len(line_indent) <= len(method_indent):
                    break
                content_lines.append(line)
                method_end_line = i
            content = '\n'.join(content_lines)
            start_line = method_line_num + 1
            end_line = method_end_line + 1
            last_newline = code[:start_pos].rfind('\n')
            start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
            end_column = len(code_lines[method_end_line]) if method_end_line < len(code_lines) else 0
            decorator_lines = []
            for i, line in enumerate(content.splitlines()):
                if line.strip().startswith('@'):
                    decorator_lines.append(line.strip())
                elif line.strip().startswith('def '):
                    break
            decorators = []
            for decorator in decorator_lines:
                name = decorator[1:].split('(')[0] if '(' in decorator else decorator[1:]
                decorators.append({'name': name, 'content': decorator})
            element_type = 'method'
            is_property = False
            is_property_setter = False
            property_name = None
            for decorator in decorators:
                if decorator.get('name') == 'property':
                    is_property = True
                elif decorator.get('name', '').endswith('.setter'):
                    is_property_setter = True
                    property_name = decorator.get('name').split('.')[0]
            if is_property:
                element_type = 'property_getter'
            elif is_property_setter:
                element_type = 'property_setter'
            parameters = self._extract_parameters_regex(content)
            return_info = self._extract_return_info_regex(content)
            method_info = {'type': element_type, 'name': name, 'content': content, 'class_name': class_name, 'range': {'start': {'line': start_line, 'column': start_column}, 'end': {'line': end_line, 'column': end_column}}, 'decorators': decorators, 'parameters': parameters, 'return_info': return_info, 'property_name': property_name}
            methods.append(method_info)
        return methods

    def _extract_parameters_regex(self, content):
        """Extract parameters using regex."""
        parameters = []
        param_pattern = 'def\\s+\\w+\\s*\\((.*?)\\)'
        param_match = re.search(param_pattern, content)
        if param_match:
            params_str = param_match.group(1)
            param_list = [p.strip() for p in params_str.split(',') if p.strip()]
            for param in param_list:
                if param == 'self':
                    continue
                param_dict = {'name': param, 'type': None}
                if ':' in param:
                    name_part, type_part = param.split(':', 1)
                    param_dict['name'] = name_part.strip()
                    param_dict['type'] = type_part.strip()
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
        return_type_pattern = 'def\\s+\\w+\\s*\\([^)]*\\)\\s*->\\s*([^:]+):'
        return_type_match = re.search(return_type_pattern, content)
        if return_type_match:
            return_info['return_type'] = return_type_match.group(1).strip()
        return_pattern = 'return\\s+([^\\n;]+)'
        return_matches = re.finditer(return_pattern, content)
        for return_match in return_matches:
            return_info['return_values'].append(return_match.group(1).strip())
        return return_info

    def get_indentation(self, line: str) -> str:
        """Extract indentation from a line."""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''