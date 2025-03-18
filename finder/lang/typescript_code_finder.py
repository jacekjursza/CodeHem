from typing import Tuple, List, Optional
from tree_sitter import Query, Node
from finder.base import CodeFinder
from languages import TS_LANGUAGE


class TypeScriptCodeFinder(CodeFinder):
    language = 'typescript'

    def find_function(self, code: str, function_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '(function_declaration name: (identifier) @func_name)'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            if cap_name == 'func_name' and self._get_node_text(node, code_bytes) == function_name:
                func_node = node
                while func_node is not None and func_node.type != 'function_declaration':
                    func_node = func_node.parent
                if func_node is not None:
                    return (func_node.start_point[0] + 1, func_node.end_point[0] + 1)
        return (0, 0)

    def find_class(self, code: str, class_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '((class_declaration) @class)'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, _) in captures:
            class_name_node = None
            for child in node.children:
                if child.type == 'identifier':
                    if self._get_node_text(child, code_bytes) == class_name:
                        class_name_node = child
                        break
            if class_name_node:
                return (node.start_point[0] + 1, node.end_point[0] + 1)
        return (0, 0)

    def find_method(self, code: str, class_name: str, method_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '(method_definition name: (property_identifier) @method_name)'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            if cap_name == 'method_name' and self._get_node_text(node, code_bytes) == method_name:
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_declaration':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    curr = curr.parent
                if inside:
                    method_node = node
                    while method_node is not None and method_node.type != 'method_definition':
                        method_node = method_node.parent
                    if method_node:
                        return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
        return (0, 0)

    def find_imports_section(self, code: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '(import_statement) @import (import_clause) @import'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        nodes = [node for (node, _) in captures]
        if not nodes:
            return (0, 0)
        nodes.sort(key=lambda node: node.start_point[0])
        return (nodes[0].start_point[0] + 1, nodes[-1].end_point[0] + 1)

    def find_properties_section(self, code: str, class_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '(public_field_definition name: (property_identifier) @prop)'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        property_nodes = []
        for (node, _) in captures:
            curr = node
            inside = False
            while curr is not None:
                if curr.type == 'class_declaration':
                    class_name_node = curr.child_by_field_name('name')
                    if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                        inside = True
                    break
                elif curr.type == 'method_definition':
                    break
                curr = curr.parent
            if inside:
                property_nodes.append(node)
        if not property_nodes:
            return (0, 0)
        property_nodes.sort(key=lambda node: node.start_point[0])
        return (property_nodes[0].start_point[0] + 1, property_nodes[-1].end_point[0] + 1)

    def get_classes_from_code(self, code: str) -> List[Tuple[str, Node]]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '(class_declaration name: (identifier) @class_name) @class'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        classes = []
        class_nodes = {}
        class_names = {}
        for (node, cap_type) in raw_captures:
            if cap_type == 'class':
                class_nodes[node.id] = node
            elif cap_type == 'class_name':
                class_name = self._get_node_text(node, code_bytes)
                class_names[node.parent.id] = class_name
        for (node_id, node) in class_nodes.items():
            if node_id in class_names:
                classes.append((class_names[node_id], node))
        return classes

    def get_methods_from_code(self, code: str) -> List[Tuple[str, Node]]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n            (function_declaration name: (identifier) @func_name) @function\n            (method_definition name: (property_identifier) @method_name) @method\n        '
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        methods = []
        method_nodes = {}
        method_names = {}
        for (node, cap_type) in raw_captures:
            if cap_type in ['function', 'method']:
                method_nodes[node.id] = node
            elif cap_type in ['func_name', 'method_name']:
                method_name = self._get_node_text(node, code_bytes)
                method_names[node.parent.id] = method_name
        for (node_id, node) in method_nodes.items():
            if node_id in method_names:
                methods.append((method_names[node_id], node))
        return methods

    def get_methods_from_class(self, code: str, class_name: str) -> List[Tuple[str, Node]]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '(class_declaration name: (identifier) @class_name) @class'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        class_node = None
        for (node, cap_type) in raw_captures:
            if cap_type == 'class_name' and self._get_node_text(node, code_bytes) == class_name:
                class_node = node.parent
                break
        if not class_node:
            return []
        query_str = '(method_definition name: (property_identifier) @method_name) @method'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(class_node, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        methods = []
        method_nodes = {}
        method_names = {}
        for (node, cap_type) in raw_captures:
            if cap_type == 'method':
                method_nodes[node.id] = node
            elif cap_type == 'method_name':
                method_name = self._get_node_text(node, code_bytes)
                method_names[node.parent.id] = method_name
        for (node_id, node) in method_nodes.items():
            if node_id in method_names:
                methods.append((method_names[node_id], node))
        return methods

    def has_class_method_indicator(self, method_node: Node, code_bytes: bytes) -> bool:
        method_body = None
        for child in method_node.children:
            if child.type == 'statement_block':
                method_body = child
                break
        if not method_body:
            return False
        query_str = '(this) @this_ref'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(method_body, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        return len(raw_captures) > 0

    def is_correct_syntax(self, plain_text: str) -> bool:
        try:
            self._get_tree(plain_text)
            return True
        except Exception:
            return False

    def find_class_for_method(self, method_name: str, code: str) -> Optional[str]:
        (root, code_bytes) = self._get_tree(code)
        query_str = f'\n        (method_definition\n          name: (property_identifier) @method_name (#eq? @method_name "{method_name}"))\n        '
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        for (node, _) in raw_captures:
            current = node.parent
            while current and current.type != 'class_declaration':
                current = current.parent
            if current and current.type == 'class_declaration':
                for child in current.children:
                    if child.type == 'identifier':
                        return self._get_node_text(child, code_bytes)
        query_str = f'\n        (public_field_definition\n          name: (property_identifier) @field_name (#eq? @field_name "{method_name}")\n          value: (arrow_function))\n        '
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        for (node, _) in raw_captures:
            current = node.parent
            while current and current.type != 'class_declaration':
                current = current.parent
            if current and current.type == 'class_declaration':
                for child in current.children:
                    if child.type == 'identifier':
                        return self._get_node_text(child, code_bytes)
        return None

    def content_looks_like_class_definition(self, content: str) -> bool:
        if not content or not content.strip():
            return False
        content_lines = content.strip().splitlines()
        if not content_lines:
            return False
        first_line = content_lines[0].strip()
        if first_line.startswith('class ') and ('{' in first_line or (len(content_lines) > 1 and '{' in content_lines[1].strip())):
            return True
        return super().content_looks_like_class_definition(content)

    def find_property(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '(public_field_definition name: (property_identifier) @prop)'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            if cap_name == 'prop' and self._get_node_text(node, code_bytes) == property_name:
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_declaration':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    curr = curr.parent
                if inside:
                    prop_node = node
                    while prop_node is not None and prop_node.type != 'public_field_definition':
                        prop_node = prop_node.parent
                    if prop_node:
                        return (prop_node.start_point[0] + 1, prop_node.end_point[0] + 1)
        query_str = '(method_definition name: (property_identifier) @getter (#match? @getter "^get_.*|^get[A-Z].*"))'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            getter_name = self._get_node_text(node, code_bytes)
            if cap_name == 'getter' and (getter_name == 'get_' + property_name or getter_name == 'get' + property_name.capitalize()):
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_declaration':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    curr = curr.parent
                if inside:
                    method_node = node
                    while method_node is not None and method_node.type != 'method_definition':
                        method_node = method_node.parent
                    if method_node:
                        return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
        query_str = '(method_definition name: (property_identifier) @prop)'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            if cap_name == 'prop' and self._get_node_text(node, code_bytes) == property_name:
                is_getter = False
                for child in node.parent.children:
                    if child.type == 'get':
                        is_getter = True
                        break
                if not is_getter:
                    continue
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_declaration':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    curr = curr.parent
                if inside:
                    method_node = node.parent
                    return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
        return (0, 0)

    def find_property_setter(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '(method_definition name: (property_identifier) @setter (#match? @setter "^set_.*|^set[A-Z].*"))'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            setter_name = self._get_node_text(node, code_bytes)
            if cap_name == 'setter' and (setter_name == 'set_' + property_name or setter_name == 'set' + property_name.capitalize()):
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_declaration':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    curr = curr.parent
                if inside:
                    method_node = node
                    while method_node is not None and method_node.type != 'method_definition':
                        method_node = method_node.parent
                    if method_node:
                        return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
        query_str = '(method_definition name: (property_identifier) @prop)'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            if cap_name == 'prop' and self._get_node_text(node, code_bytes) == property_name:
                is_setter = False
                for child in node.parent.children:
                    if child.type == 'set':
                        is_setter = True
                        break
                if not is_setter:
                    continue
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_declaration':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    curr = curr.parent
                if inside:
                    method_node = node.parent
                    return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
        return (0, 0)

    def find_property_and_setter(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        (getter_start, getter_end) = self.find_property(code, class_name, property_name)
        (setter_start, setter_end) = self.find_property_setter(code, class_name, property_name)
        if getter_start == 0 or getter_end == 0:
            if setter_start == 0 or setter_end == 0:
                return (0, 0)
            return (setter_start, setter_end)
        if setter_start == 0 or setter_end == 0:
            return (getter_start, getter_end)
        start = min(getter_start, setter_start)
        end = max(getter_end, setter_end)
        return (start, end)

    def get_class_with_updated_property(self, code: str, class_name: str, property_name: str, new_property_code: str) -> str:
        (class_start, class_end) = self.find_class(code, class_name)
        if class_start == 0 or class_end == 0:
            return code
        (prop_start, prop_end) = self.find_property_and_setter(code, class_name, property_name)
        lines = code.splitlines()
        class_indent = self._get_indentation(lines[class_start - 1]) if class_start <= len(lines) else ''
        prop_indent = class_indent + '  '
        if prop_start > 0 and prop_end > 0:
            new_lines = []
            new_lines.extend(lines[:prop_start - 1])
            for line in new_property_code.splitlines():
                if line.strip():
                    new_lines.append(prop_indent + line.strip())
                else:
                    new_lines.append('')
            new_lines.extend(lines[prop_end:])
            return '\n'.join(new_lines)
        else:
            new_class_lines = []
            last_member_line = class_start
            for i in range(class_start, class_end):
                line = lines[i].strip() if i < len(lines) else ''
                if line and line != '{' and (line != '}'):
                    last_member_line = i
            new_class_lines.extend(lines[class_start - 1:last_member_line + 1])
            new_class_lines.append('')
            for line in new_property_code.splitlines():
                if line.strip():
                    new_class_lines.append(prop_indent + line.strip())
                else:
                    new_class_lines.append('')
            new_class_lines.extend(lines[last_member_line + 1:class_end])
            return '\n'.join(new_class_lines)
            
    def _get_indentation(self, line: str) -> str:
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''
        
    def get_decorators(self, code: str, name: str, class_name: Optional[str] = None) -> List[str]:
        """
        Get decorators for a function or method.
        
        Args:
            code: Source code as string
            name: Function or method name
            class_name: Class name if searching for method decorators, None for standalone functions
            
        Returns:
            List of decorator strings
        """
        # TypeScript doesn't have built-in decorators like Python, but it does have
        # a decorator pattern using the @ symbol that's similar to Python
        (root, code_bytes) = self._get_tree(code)
        
        if class_name:
            # For class methods
            query_str = f'(method_definition name: (property_identifier) @method_name (#eq? @method_name "{name}"))'
            query = Query(TS_LANGUAGE, query_str)
            raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
            
            for node, _ in raw_captures:
                method_node = node.parent
                
                # Check if this method is in the specified class
                current = method_node
                in_target_class = False
                while current:
                    if current.type == 'class_declaration':
                        for child in current.children:
                            if child.type == 'identifier' and self._get_node_text(child, code_bytes) == class_name:
                                in_target_class = True
                                break
                        break
                    current = current.parent
                
                if in_target_class:
                    # Find decorators - TypeScript/JavaScript decorators are indicated with @ symbol
                    decorators = []
                    for child in method_node.children:
                        if child.type == 'decorator':
                            decorators.append(self._get_node_text(child, code_bytes))
                    
                    return decorators
            
            return []
        else:
            # For standalone functions
            query_str = f'(function_declaration name: (identifier) @func_name (#eq? @func_name "{name}"))'
            query = Query(TS_LANGUAGE, query_str)
            raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
            
            for node, _ in raw_captures:
                func_node = node.parent
                
                # Find decorators
                decorators = []
                for child in func_node.children:
                    if child.type == 'decorator':
                        decorators.append(self._get_node_text(child, code_bytes))
                
                return decorators
            
            return []

    def get_class_decorators(self, code: str, class_name: str) -> List[str]:
        """
        Get decorators for a class.
        
        Args:
            code: Source code as string
            class_name: Class name
            
        Returns:
            List of decorator strings
        """
        (root, code_bytes) = self._get_tree(code)
        
        query_str = f'(class_declaration name: (identifier) @class_name (#eq? @class_name "{class_name}"))'
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        
        for node, _ in raw_captures:
            class_node = node.parent
            
            # Find decorators
            decorators = []
            for child in class_node.children:
                if child.type == 'decorator':
                    decorators.append(self._get_node_text(child, code_bytes))
            
            return decorators
        
        return []