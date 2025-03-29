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
        """Process tree-sitter query results for methods.
        MODIFIED: Adds definition start location for deduplication.
        """
        methods = []
        method_nodes = {}
        decorated_method_nodes = {}
        processed_def_node_ids = set()
        temp_decorators = {}

        # First pass - collect all decorators
        for node, capture_name in query_results:
            if capture_name == 'decorator':
                parent = node.parent
                if parent and parent.type == 'decorated_definition':
                    def_node = ast_handler.find_child_by_field_name(parent, 'definition')
                    if def_node:
                        name_node = ast_handler.find_child_by_field_name(def_node, 'name')
                        if name_node:
                            method_name = ast_handler.get_node_text(name_node, code_bytes)
                            decorator_content = ast_handler.get_node_text(node, code_bytes)
                            decorator_name = None
                            name_node = node.child_by_field_name('name')
                            if name_node:
                                decorator_name = ast_handler.get_node_text(name_node, code_bytes)
                            elif node.named_child_count > 0:
                                for j in range(node.named_child_count):
                                    sub_child = node.named_child(j)
                                    if sub_child.type == 'identifier':
                                        decorator_name = ast_handler.get_node_text(sub_child, code_bytes)
                                        break
                                    elif sub_child.type == 'attribute':
                                        obj_node = ast_handler.find_child_by_field_name(sub_child, 'object')
                                        attr_node = ast_handler.find_child_by_field_name(sub_child, 'attribute')
                                        if obj_node and attr_node:
                                            obj_name = ast_handler.get_node_text(obj_node, code_bytes)
                                            attr_name = ast_handler.get_node_text(attr_node, code_bytes)
                                            decorator_name = f'{obj_name}.{attr_name}'
                                            break

                            # Use function node ID as the key
                            node_id = def_node.id
                            if node_id not in temp_decorators:
                                temp_decorators[node_id] = []

                            dec_range_data = {'start': {'line': node.start_point[0] + 1, 'column': node.start_point[1]}, 
                                              'end': {'line': node.end_point[0] + 1, 'column': node.end_point[1]}}

                            temp_decorators[node_id].append({
                                'name': decorator_name, 
                                'content': decorator_content, 
                                'range': dec_range_data
                            })

        for node, capture_name in query_results:
            if capture_name == 'decorated_method_def':
                definition_node = ast_handler.find_child_by_field_name(node, 'definition')
                if definition_node and definition_node.type in ['function_definition', 'method_definition']:
                    if definition_node.id not in processed_def_node_ids:
                        decorated_method_nodes[definition_node.id] = node
                        processed_def_node_ids.add(definition_node.id)

            elif capture_name == 'method_def':
                definition_node = node
                if definition_node.type in ['function_definition', 'method_definition']:
                    if definition_node.id not in processed_def_node_ids:
                        is_likely_property = False

                        # Check if we have collected decorators for this node and if any is a property decorator
                        if definition_node.id in temp_decorators:
                            for dec in temp_decorators[definition_node.id]:
                                if dec['name'] == 'property' or (isinstance(dec['name'], str) and '.setter' in dec['name']):
                                    is_likely_property = True
                                    break

                        # If parent is decorated definition, also check directly
                        if definition_node.parent and definition_node.parent.type == 'decorated_definition':
                            for i in range(definition_node.parent.named_child_count):
                                child = definition_node.parent.named_child(i)
                                if child.type == 'decorator':
                                    dec_name_node = ast_handler.find_child_by_field_name(child, 'name')
                                    dec_name = ast_handler.get_node_text(dec_name_node, code_bytes) if dec_name_node else None
                                    if dec_name == 'property' or (isinstance(dec_name, str) and '.setter' in dec_name):
                                        is_likely_property = True
                                        break

                        if not is_likely_property:
                            method_nodes[definition_node.id] = definition_node
                            processed_def_node_ids.add(definition_node.id)

        for def_node_id, definition_node in method_nodes.items():
            name_node = ast_handler.find_child_by_field_name(definition_node, 'name')
            if not name_node:
                continue
            method_name = ast_handler.get_node_text(name_node, code_bytes)
            definition_start_line = definition_node.start_point[0] + 1
            definition_start_col = definition_node.start_point[1]
            content = ast_handler.get_node_text(definition_node, code_bytes)
            full_range_data = {'start': {'line': definition_start_line, 'column': definition_start_col}, 
                              'end': {'line': definition_node.end_point[0] + 1, 'column': definition_node.end_point[1]}}
            class_name = self._get_class_name(definition_node, context, ast_handler, code_bytes)
            parameters = ExtractorHelpers.extract_parameters(ast_handler, definition_node, code_bytes)
            return_info = ExtractorHelpers.extract_return_info(ast_handler, definition_node, code_bytes)

            # Get decorators for this method if any were collected
            decorators = temp_decorators.get(def_node_id, [])

            method_info = {
                'type': 'method', 
                'name': method_name, 
                'content': content, 
                'class_name': class_name, 
                'range': full_range_data, 
                'decorators': decorators, 
                'parameters': parameters, 
                'return_info': return_info, 
                'definition_start_line': definition_start_line, 
                'definition_start_col': definition_start_col
            }
            methods.append(method_info)

        for def_node_id, decorated_node in decorated_method_nodes.items():
            definition_node = ast_handler.find_child_by_field_name(decorated_node, 'definition')
            if not definition_node:
                continue
            name_node = ast_handler.find_child_by_field_name(definition_node, 'name')
            if not name_node:
                continue
            method_name = ast_handler.get_node_text(name_node, code_bytes)

            # Get decorators for this method if any were collected
            decorators = temp_decorators.get(def_node_id, [])

            # If we didn't collect decorators earlier, try to extract them now
            if not decorators:
                decorators = self._extract_decorators_from_node(decorated_node, ast_handler, code_bytes)

            is_likely_property = False
            for dec in decorators:
                dec_name = dec.get('name')
                if dec_name == 'property' or (isinstance(dec_name, str) and '.setter' in dec_name):
                    is_likely_property = True
                    break

            # If it's a property, don't treat it as a method - let the property extractors handle it
            if is_likely_property:
                logger.debug(f"Method extractor skipping '{method_name}' as it's likely a property.")
                continue

            definition_start_line = definition_node.start_point[0] + 1
            definition_start_col = definition_node.start_point[1]
            content = ast_handler.get_node_text(decorated_node, code_bytes)
            full_range_data = {'start': {'line': decorated_node.start_point[0] + 1, 'column': decorated_node.start_point[1]}, 
                              'end': {'line': decorated_node.end_point[0] + 1, 'column': decorated_node.end_point[1]}}
            class_name = self._get_class_name(decorated_node, context, ast_handler, code_bytes)
            parameters = ExtractorHelpers.extract_parameters(ast_handler, definition_node, code_bytes)
            return_info = ExtractorHelpers.extract_return_info(ast_handler, definition_node, code_bytes)

            method_info = {
                'type': 'method', 
                'name': method_name, 
                'content': content, 
                'class_name': class_name, 
                'range': full_range_data, 
                'decorators': decorators, 
                'parameters': parameters, 
                'return_info': return_info, 
                'definition_start_line': definition_start_line, 
                'definition_start_col': definition_start_col
            }
            methods.append(method_info)

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