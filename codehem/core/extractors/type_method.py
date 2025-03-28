"""
Method extractor that uses language-specific handlers.
"""
from typing import Dict, List, Optional, Any
import re
import logging

from codehem.core.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class MethodExtractor(BaseExtractor):
    """Method extractor using language-specific handlers."""
    ELEMENT_TYPE = CodeElementType.METHOD

    @property
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""
        return self.ELEMENT_TYPE

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Extract methods from the provided code.
        
        Args:
            code: The source code to extract from
            context: Optional context information for the extraction
            
        Returns:
            List of extracted methods as dictionaries
        """
        context = context or {}
        methods = super().extract(code, context)
        return methods

    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract using TreeSitter first, fall back to regex if needed."""
        if handler.tree_sitter_query:
            methods = self._extract_with_tree_sitter(code, handler, context)
            if methods:
                return methods
        if handler.regexp_pattern:
            return self._extract_with_regex(code, handler, context)
        return []

    def _extract_with_tree_sitter(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract methods using TreeSitter."""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            return []
        try:
            root, code_bytes = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
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
                    parent = node.parent
                    if parent and parent.type == 'decorated_definition':
                        def_node = ast_handler.find_child_by_field_name(parent, 'definition')
                        if def_node and def_node.type == 'function_definition':
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
                                        elif child.type == 'attribute':
                                            # Handle property.setter style decorators
                                            obj_node = ast_handler.find_child_by_field_name(child, 'object')
                                            attr_node = ast_handler.find_child_by_field_name(child, 'attribute')
                                            if obj_node and attr_node:
                                                obj_name = ast_handler.get_node_text(obj_node, code_bytes)
                                                attr_name = ast_handler.get_node_text(attr_node, code_bytes)
                                                decorator_name = f"{obj_name}.{attr_name}"
                                                break
                                decorator_nodes[method_name].append({'name': decorator_name, 'content': decorator_content})
                elif capture_name == 'method_name':
                    method_name = ast_handler.get_node_text(node, code_bytes)
                    parent = node.parent
                    if parent and parent.type == 'function_definition':
                        grand_parent = parent.parent
                        if grand_parent and grand_parent.type == 'decorated_definition':
                            decorated_methods[method_name] = grand_parent
                        else:
                            method_nodes[method_name] = parent
            for method_name, method_node in method_nodes.items():
                content = ast_handler.get_node_text(method_node, code_bytes)
                class_name = None
                if context.get('class_name'):
                    class_name = context.get('class_name')
                else:
                    class_node = ast_handler.find_parent_of_type(method_node, 'class_definition')
                    if class_node:
                        class_name_node = ast_handler.find_child_by_field_name(class_node, 'name')
                        if class_name_node:
                            class_name = ast_handler.get_node_text(class_name_node, code_bytes)
                parameters = []
                params_node = ast_handler.find_child_by_field_name(method_node, 'parameters')
                if params_node:
                    for i in range(params_node.named_child_count):
                        param_node = params_node.named_child(i)
                        if i == 0 and ast_handler.get_node_text(param_node, code_bytes) == 'self':
                            continue
                        param_info = self._extract_parameter(param_node, code_bytes, ast_handler)
                        if param_info:
                            parameters.append(param_info)
                return_type = None
                return_type_node = ast_handler.find_child_by_field_name(method_node, 'return_type')
                if return_type_node:
                    return_type = ast_handler.get_node_text(return_type_node, code_bytes)
                return_values = []
                body_node = ast_handler.find_child_by_field_name(method_node, 'body')
                if body_node:
                    try:
                        return_query = '(return_statement) @return_stmt'
                        return_results = ast_handler.execute_query(return_query, body_node, code_bytes)
                        for return_node, _ in return_results:
                            stmt_text = ast_handler.get_node_text(return_node, code_bytes)
                            if stmt_text.startswith('return '):
                                return_values.append(stmt_text[7:].strip())
                    except Exception:
                        pass
                decorators = decorator_nodes.get(method_name, [])
                method_info = {'type': 'method', 'name': method_name, 'content': content, 'class_name': class_name, 'range': {'start': {'line': method_node.start_point[0] + 1, 'column': method_node.start_point[1]}, 'end': {'line': method_node.end_point[0] + 1, 'column': method_node.end_point[1]}}, 'decorators': decorators, 'parameters': parameters, 'return_info': {'return_type': return_type, 'return_values': return_values}}
                methods.append(method_info)
            for method_name, decorated_node in decorated_methods.items():
                def_node = ast_handler.find_child_by_field_name(decorated_node, 'definition')
                if not def_node:
                    continue
                content = ast_handler.get_node_text(decorated_node, code_bytes)
                class_name = None
                if context.get('class_name'):
                    class_name = context.get('class_name')
                else:
                    class_node = ast_handler.find_parent_of_type(decorated_node, 'class_definition')
                    if class_node:
                        class_name_node = ast_handler.find_child_by_field_name(class_node, 'name')
                        if class_name_node:
                            class_name = ast_handler.get_node_text(class_name_node, code_bytes)
                parameters = []
                params_node = ast_handler.find_child_by_field_name(def_node, 'parameters')
                if params_node:
                    for i in range(params_node.named_child_count):
                        param_node = params_node.named_child(i)
                        if i == 0 and ast_handler.get_node_text(param_node, code_bytes) == 'self':
                            continue
                        param_info = self._extract_parameter(param_node, code_bytes, ast_handler)
                        if param_info:
                            parameters.append(param_info)
                return_type = None
                return_type_node = ast_handler.find_child_by_field_name(def_node, 'return_type')
                if return_type_node:
                    return_type = ast_handler.get_node_text(return_type_node, code_bytes)
                return_values = []
                body_node = ast_handler.find_child_by_field_name(def_node, 'body')
                if body_node:
                    try:
                        return_query = '(return_statement) @return_stmt'
                        return_results = ast_handler.execute_query(return_query, body_node, code_bytes)
                        for return_node, _ in return_results:
                            stmt_text = ast_handler.get_node_text(return_node, code_bytes)
                            if stmt_text.startswith('return '):
                                return_values.append(stmt_text[7:].strip())
                    except Exception:
                        pass
                decorators = decorator_nodes.get(method_name, [])
                if not decorators:
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
                                    elif sub_child.type == 'attribute':
                                        # Handle property.setter style decorators
                                        obj_node = ast_handler.find_child_by_field_name(sub_child, 'object')
                                        attr_node = ast_handler.find_child_by_field_name(sub_child, 'attribute')
                                        if obj_node and attr_node:
                                            obj_name = ast_handler.get_node_text(obj_node, code_bytes)
                                            attr_name = ast_handler.get_node_text(attr_node, code_bytes)
                                            decorator_name = f"{obj_name}.{attr_name}"
                                            break
                            decorators.append({'name': decorator_name, 'content': decorator_content})

                # Detect property getter and setter methods
                method_type = 'method'
                for decorator in decorators:
                    dec_name = decorator.get('name', '')
                    if dec_name == 'property':
                        method_type = 'property_getter'
                        break
                    elif dec_name and '.' in dec_name and dec_name.endswith('.setter'):
                        method_type = 'property_setter'
                        break

                method_info = {'type': method_type, 'name': method_name, 'content': content, 'class_name': class_name, 'range': {'start': {'line': decorated_node.start_point[0] + 1, 'column': decorated_node.start_point[1]}, 'end': {'line': decorated_node.end_point[0] + 1, 'column': decorated_node.end_point[1]}}, 'decorators': decorators, 'parameters': parameters, 'return_info': {'return_type': return_type, 'return_values': return_values}}
                methods.append(method_info)
            return methods
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {str(e)}')
            return []

    def _extract_decorators(self, method_node, code_bytes, ast_handler) -> List[Dict]:
        """
        Extract decorators from a method node.
        
        Args:
            method_node: Method node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            List of decorator dictionaries
        """
        decorators = []
        parent_node = method_node.parent
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

    def _extract_parameters(self, method_node, code_bytes, ast_handler) -> List[Dict]:
        """
        Extract detailed parameter information from a method.
        
        Args:
            method_node: Method node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            List of parameter dictionaries with name, type, and default value
        """
        parameters = []
        params_node = None
        for child_idx in range(method_node.named_child_count):
            child = method_node.named_child(child_idx)
            if child.type == 'parameters':
                params_node = child
                break
        if not params_node:
            return parameters
        for child_idx in range(params_node.named_child_count):
            child = params_node.named_child(child_idx)
            if child.type == 'identifier':
                name = ast_handler.get_node_text(child, code_bytes)
                if name != 'self':
                    parameters.append({'name': name, 'type': None})
            elif child.type == 'typed_parameter':
                name_node = child.child_by_field_name('name')
                type_node = child.child_by_field_name('type')
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    if name != 'self':
                        param_dict = {'name': name, 'type': None}
                        if type_node:
                            param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                        parameters.append(param_dict)
            elif child.type == 'default_parameter':
                name_node = child.child_by_field_name('name')
                value_node = child.child_by_field_name('value')
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    if name != 'self':
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
                    if name != 'self':
                        param_dict = {'name': name, 'type': None, 'optional': True}
                        if type_node:
                            param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                        if value_node:
                            param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                        parameters.append(param_dict)
        return parameters

    def _extract_return_info(self, method_node, code_bytes, ast_handler) -> Dict:
        """
        Extract return type information from a method.
        
        Args:
            method_node: Method node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            Dictionary with return_type and return_values
        """
        return_type = None
        return_values = []
        return_type_node = method_node.child_by_field_name('return_type')
        if return_type_node:
            return_type = ast_handler.get_node_text(return_type_node, code_bytes)
        body_node = method_node.child_by_field_name('body')
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
                    method_text = ast_handler.get_node_text(method_node, code_bytes)
                    return_regex = 'return\\s+(.+?)(?:\\n|$)'
                    for match in re.finditer(return_regex, method_text):
                        return_values.append(match.group(1).strip())
        return {'return_type': return_type, 'return_values': return_values}

    def _extract_parameter(self, param_node, code_bytes, ast_handler) -> Optional[Dict]:
        """
        Extract information about a parameter.
        
        Args:
            param_node: Parameter node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            Parameter information or None
        """
        if param_node.type == 'identifier':
            name = ast_handler.get_node_text(param_node, code_bytes)
            return {'name': name, 'type': None}
        elif param_node.type == 'typed_parameter':
            name_node = param_node.child_by_field_name('name')
            type_node = param_node.child_by_field_name('type')
            if name_node:
                name = ast_handler.get_node_text(name_node, code_bytes)
                param_dict = {'name': name, 'type': None}
                if type_node:
                    param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                return param_dict
        elif param_node.type == 'default_parameter':
            name_node = param_node.child_by_field_name('name')
            value_node = param_node.child_by_field_name('value')
            if name_node:
                name = ast_handler.get_node_text(name_node, code_bytes)
                param_dict = {'name': name, 'type': None, 'optional': True}
                if value_node:
                    param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                return param_dict
        elif param_node.type == 'typed_default_parameter':
            name_node = param_node.child_by_field_name('name')
            type_node = param_node.child_by_field_name('type')
            value_node = param_node.child_by_field_name('value')
            if name_node:
                name = ast_handler.get_node_text(name_node, code_bytes)
                param_dict = {'name': name, 'type': None, 'optional': True}
                if type_node:
                    param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                if value_node:
                    param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                return param_dict
        return None

    def _extract_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract methods using regex."""
        class_name = context.get('class_name')
        if class_name:
            class_pattern = 'class\\s+' + re.escape(class_name) + '(?:\\s*\\([^)]*\\))?\\s*:(.*?)(?=\\n(?:class|def\\s+\\w+\\s*\\([^s]|$))'
            class_match = re.search(class_pattern, code, re.DOTALL)
            if not class_match:
                return []
            code_to_search = class_match.group(1)
            base_indent = ' ' * 4
        else:
            code_to_search = code
            base_indent = ''
        try:
            if class_name:
                pattern = f'{re.escape(base_indent)}' + handler.regexp_pattern
            else:
                pattern = handler.regexp_pattern
            matches = re.finditer(pattern, code_to_search, re.DOTALL)
            methods = []
            for match in matches:
                name = match.group(1)
                signature = match.group(0)
                if class_name:
                    start_pos = class_match.start(1) + match.start()
                    sig_end_pos = class_match.start(1) + match.end()
                else:
                    start_pos = match.start()
                    sig_end_pos = match.end()

                # Get the indentation level of the method definition
                code_lines = code.splitlines()
                method_line_num = code[:start_pos].count('\n')
                method_indent = self.get_indentation(signature) if signature.startswith(' ') else ''

                # Parse the method body based on indentation
                content_lines = [signature]

                # Find the end of the method by analyzing indentation
                method_end_line = method_line_num
                for i, line in enumerate(code_lines[method_line_num + 1:], method_line_num + 1):
                    if i >= len(code_lines):
                        break

                    line_indent = self.get_indentation(line)
                    # Skip empty lines
                    if not line.strip():
                        content_lines.append(line)
                        continue

                    # If indentation is less than or equal to method indentation and not an empty line,
                    # we've exited the method
                    if len(line_indent) <= len(method_indent):
                        break

                    # Still in the method body
                    content_lines.append(line)
                    method_end_line = i

                # Combine the method signature and body
                content = '\n'.join(content_lines)

                # Calculate start line (1-indexed)
                start_line = method_line_num + 1

                # Calculate end line (1-indexed)
                end_line = method_end_line + 1

                # Get column positions
                last_newline = code[:start_pos].rfind('\n')
                start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
                end_column = len(code_lines[method_end_line]) if method_end_line < len(code_lines) else 0

                # Extract decorators
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

                is_property = False
                is_property_setter = False
                property_name = None
                for decorator in decorators:
                    if decorator.get('name') == 'property':
                        is_property = True
                    elif decorator.get('name', '').endswith('.setter'):
                        is_property_setter = True
                        property_name = decorator.get('name').split('.')[0]

                element_type = 'method'
                if is_property:
                    element_type = 'property_getter'
                elif is_property_setter:
                    element_type = 'property_setter'

                param_pattern = 'def\\s+\\w+\\s*\\((.*?)\\)'
                param_match = re.search(param_pattern, content)
                parameters = []
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

                # Extract return information correctly from the method body only
                return_info = {'return_type': None, 'return_values': []}
                return_type_pattern = 'def\\s+\\w+\\s*\\([^)]*\\)\\s*->\\s*([^:]+):'
                return_type_match = re.search(return_type_pattern, content)
                if return_type_match:
                    return_info['return_type'] = return_type_match.group(1).strip()

                return_pattern = 'return\\s+([^\\n;]+)'
                return_matches = re.finditer(return_pattern, content)
                for return_match in return_matches:
                    return_info['return_values'].append(return_match.group(1).strip())

                methods.append({
                    'type': element_type, 
                    'name': name, 
                    'content': content, 
                    'class_name': class_name, 
                    'range': {
                        'start': {'line': start_line, 'column': start_column}, 
                        'end': {'line': end_line, 'column': end_column}
                    }, 
                    'decorators': decorators, 
                    'parameters': parameters, 
                    'return_info': return_info, 
                    'property_name': property_name
                })
            return methods
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []
