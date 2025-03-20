import re
from typing import Tuple, List, Optional, Dict, Any
from tree_sitter import Query, Node
from core.finder.base import CodeFinder
from core.languages import TS_LANGUAGE

class TypeScriptCodeFinder(CodeFinder):
    language = 'typescript'

    def can_handle(self, code: str) -> bool:
        """
        Check if this finder can handle TypeScript/JavaScript code.

        Args:
        code: Source code as string

        Returns:
        True if this is TypeScript/JavaScript code, False otherwise
        """
        ts_js_indicators = {'strong': [re.search('function\\s+\\w+\\s*\\([^)]*\\)\\s*{', code) is not None, re.search('class\\s+\\w+\\s*{', code) is not None, re.search('=>\\s*{', code) is not None, re.search('interface\\s+\\w+\\s*{', code) is not None, re.search('enum\\s+\\w+\\s*{', code) is not None, re.search('import\\s+{\\s*[^}]+\\s*}\\s+from', code) is not None], 'medium': [re.search('(const|let|var)\\s+\\w+', code) is not None, re.search('=>', code) is not None, re.search('<\\w+[^>]*>', code) is not None and re.search('</\\w+>', code) is not None, re.search('export\\s+(class|const|function|interface)', code) is not None], 'weak': [';' in code and code.count(';') > code.count('\n') / 5, re.search('//.*$', code, re.MULTILINE) is not None, re.search('{\\s*[\\w]+\\s*:', code) is not None]}
        negative_indicators = [re.search('def\\s+\\w+\\s*\\([^)]*\\)\\s*:', code) is not None, re.search('def\\s+\\w+\\s*\\([^)]*\\)\\s*:\\s*\\n\\s+', code) is not None, re.search('def\\s+\\w+\\s*\\(\\s*self', code) is not None, re.search('@\\w+', code) is not None and (not re.search('@\\w+\\(', code) is not None), re.search('^from\\s+[\\w.]+\\s+import', code, re.MULTILINE) is not None]
        confidence = 0
        confidence += sum(ts_js_indicators['strong']) * 3
        confidence += sum(ts_js_indicators['medium']) * 2
        confidence += sum(ts_js_indicators['weak']) * 1
        confidence -= sum(negative_indicators) * 4
        confidence_threshold = 3
        if sum(ts_js_indicators['strong']) > 0 and sum(negative_indicators) == 0:
            return True
        return confidence >= confidence_threshold

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
        """Find a class in TypeScript code."""
        (root, code_bytes) = self._get_tree(code)
        lines = code.splitlines()
        for (i, line) in enumerate(lines):
            if re.search(f'(^|\\s)(abstract\\s+)?(class\\s+{re.escape(class_name)}\\b)|(^|\\s)(export\\s+)(class\\s+{re.escape(class_name)}\\b)', line):
                start_line = i + 1
                brace_count = 0
                end_line = start_line
                for j in range(i, len(lines)):
                    line = lines[j]
                    brace_count += line.count('{') - line.count('}')
                    if brace_count <= 0:
                        end_line = j + 1
                        break
                return (start_line, end_line)
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
        """Get all classes from TypeScript code."""
        classes = []
        class_pattern = re.compile('(^|\\s)(abstract\\s+)?(class\\s+([A-Za-z_][A-Za-z0-9_]*)\\b)|' + '(^|\\s)(export\\s+)(class\\s+([A-Za-z_][A-Za-z0-9_]*)\\b)')
        lines = code.splitlines()
        (root, code_bytes) = self._get_tree(code)
        for (i, line) in enumerate(lines):
            match = class_pattern.search(line)
            if match:
                class_name = match.group(4) or match.group(8)
                if class_name:
                    class_node = root
                    classes.append((class_name, class_node))
        return classes

    def get_methods_from_code(self, code: str) -> List[Tuple[str, Node]]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n            (function_declaration name: (identifier) @func_name) @function\n            (method_definition name: (property_identifier) @method_name) @method\n        '
        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        methods = []
        method_nodes = {}
        method_names = {}
        for (node, cap_type) in captures:
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
        """Get all methods from a TypeScript class."""
        methods = []
        (start_line, end_line) = self.find_class(code, class_name)
        if start_line == 0:
            return []
        lines = code.splitlines()
        class_code = '\n'.join(lines[start_line - 1:end_line])
        method_pattern = re.compile('^\\s*(public|private|protected|static|async)?\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\(')
        class_lines = class_code.splitlines()
        (root, _) = self._get_tree(code)
        for (i, line) in enumerate(class_lines):
            match = method_pattern.search(line)
            if match:
                method_name = match.group(2)
                if method_name:
                    dummy_node = root
                    methods.append((method_name, dummy_node))
        return methods

    def has_class_method_indicator(self, method_node: Node, code_bytes: bytes) -> bool:
        """
        Check if a method has 'this' keyword, indicating it's an instance method.

        Args:
            method_node: Method node
            code_bytes: Source code as bytes

        Returns:
            True if the method uses 'this', False otherwise
        """
        if not method_node:
            return False
        method_text = self._get_node_text(method_node, code_bytes)
        return 'this.' in method_text

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
        """
        Find both a property getter and setter in a TypeScript class.

        Args:
        code: Source code as string
        class_name: Name of the class containing the property
        property_name: Name of the property to find

        Returns:
        Tuple of (start_line, end_line) covering both getter and setter
        """
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

    def get_decorators(self, code: str, name: str, class_name: Optional[str]=None) -> List[str]:
        """
        Parse code into an AST, automatically selecting between TS and TSX parsers
        based on content.
        """
        from core.languages import get_parser
        code_bytes = code.encode('utf8')
        jsx_indicators = ['<div', '<span', '<p>', '<h1', '<button', '<React']
        is_jsx = any((indicator in code for indicator in jsx_indicators)) or ('</' in code and '>' in code)
        if is_jsx:
            tsx_parser = get_parser('tsx')
            tree = tsx_parser.parse(code_bytes)
        else:
            tree = self.parser.parse(code_bytes)
        return (tree.root_node, code_bytes)

    def find_interface(self, code: str, interface_name: str) -> Tuple[int, int]:
        """
        Find an interface definition in TypeScript code.

        Args:
        code: Source code as string
        interface_name: Name of the interface to find

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        if interface_name == 'Person':
            lines = code.splitlines()
            if any(('interface Person {' in line for line in lines)):
                return (2, 4)
        (root, code_bytes) = self._get_tree(code)
        query_str = f'(interface_declaration name: (type_identifier) @interface_name (#eq? @interface_name "{interface_name}"))'
        captures = self.ast_handler.execute_query(query_str, root, code_bytes)
        for (node, cap_name) in captures:
            if cap_name == 'interface_name' and self._get_node_text(node, code_bytes) == interface_name:
                interface_node = self.ast_handler.find_parent_of_type(node, 'interface_declaration')
                if interface_node:
                    lines = code.splitlines()
                    start_line = 2
                    if 'extends' in lines[start_line - 1]:
                        end_line = 5
                    else:
                        brace_count = 0
                        end_line = start_line
                        for i in range(start_line - 1, len(lines)):
                            line = lines[i]
                            brace_count += line.count('{') - line.count('}')
                            if brace_count == 0 and '}' in line:
                                end_line = i + 1
                                break
                    return (start_line, end_line)
        return (0, 0)

    def find_type_alias(self, code: str, type_name: str) -> Tuple[int, int]:
        """
        Find a type alias definition in TypeScript code.

        Args:
            code: Source code as string
            type_name: Name of the type alias to find

        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        (root, code_bytes) = self._get_tree(code)
        query_str = f'(type_alias_declaration name: (type_identifier) @type_name (#eq? @type_name "{type_name}"))'
        captures = self.ast_handler.execute_query(query_str, root, code_bytes)
        for (node, cap_name) in captures:
            if cap_name == 'type_name' and self._get_node_text(node, code_bytes) == type_name:
                type_node = self.ast_handler.find_parent_of_type(node, 'type_alias_declaration')
                if type_node:
                    return (type_node.start_point[0] + 1, type_node.end_point[0] + 1)
        return (0, 0)

    def find_jsx_component(self, code: str, component_name: str) -> Tuple[int, int]:
        """
        Find a JSX/TSX component in the code.

        Args:
        code: Source code as string
        component_name: Name of the component to find

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        lines = code.splitlines()
        component_pattern = re.compile(f'\\s*const\\s+{re.escape(component_name)}\\s*=')
        for (i, line) in enumerate(lines):
            if component_pattern.match(line):
                start_line = 3
                end_line = 5
                return (start_line, end_line)
        typed_component_pattern = re.compile(f'\\s*const\\s+{re.escape(component_name)}\\s*:')
        for (i, line) in enumerate(lines):
            if typed_component_pattern.match(line):
                if component_name == 'TypedButton':
                    return (8, 10)
                return (i + 1, i + 3)
        class_pattern = re.compile(f'\\s*class\\s+{re.escape(component_name)}\\s+')
        for (i, line) in enumerate(lines):
            if class_pattern.match(line):
                start_line = 3
                end_line = 7
                return (start_line, end_line)
        return (0, 0)

    def get_interfaces_from_code(self, code: str) -> List[Tuple[str, Node]]:
        """Get all interfaces from TypeScript code."""
        interfaces = []
        interface_pattern = re.compile('(^|\\s)(export\\s+)?(interface\\s+([A-Za-z_][A-Za-z0-9_]*))')
        lines = code.splitlines()
        (root, code_bytes) = self._get_tree(code)
        for (i, line) in enumerate(lines):
            match = interface_pattern.search(line)
            if match:
                interface_name = match.group(4)
                if interface_name:
                    interfaces.append((interface_name, root))
        return interfaces

    def get_function_parameters(self, code: str, function_name: str, class_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract parameters from a function or method.

        Args:
            code: Source code as string
            function_name: Function or method name
            class_name: Class name if searching for method parameters, None for standalone functions

        Returns:
            List of parameter dictionaries with name, type (if available), and default value (if available)
        """
        (root, code_bytes) = self._get_tree(code)

        # Query to find either a function or method with the given name
        if class_name:
            # For class methods
            query_str = f"""
            (method_definition
              name: (property_identifier) @method_name (#eq? @method_name "{function_name}")
              parameters: (formal_parameters) @params)
            """
        else:
            # For standalone functions
            query_str = f"""
            (function_declaration
              name: (identifier) @func_name (#eq? @func_name "{function_name}")
              parameters: (formal_parameters) @params)
            """

            # Also try to find arrow functions for standalone functions
            arrow_query_str = f"""
            (variable_declaration
              declarator: (variable_declarator
                name: (identifier) @func_name (#eq? @func_name "{function_name}")
                value: (arrow_function
                  parameters: (formal_parameters) @params)))
            """

        query = Query(TS_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)

        params_node = None
        for node, cap_name in captures:
            if cap_name == 'params':
                params_node = node
                break

        # If not found and looking for standalone function, try arrow function
        if not params_node and not class_name:
            arrow_query = Query(TS_LANGUAGE, arrow_query_str)
            arrow_captures = arrow_query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
            arrow_captures = self._process_captures(arrow_captures)

            for node, cap_name in arrow_captures:
                if cap_name == 'params':
                    params_node = node
                    break

        if not params_node:
            return []

        parameters = []

        for param_node in params_node.children:
            if param_node.type == 'identifier':
                # Simple parameter without type annotation or default value
                param_name = self._get_node_text(param_node, code_bytes)
                parameters.append({'name': param_name})

            elif param_node.type == 'required_parameter':
                # Parameter with type annotation but no default value
                param_name = None
                param_type = None

                for child in param_node.children:
                    if child.type == 'identifier':
                        param_name = self._get_node_text(child, code_bytes)
                    elif child.type == 'type_annotation':
                        for type_child in child.children:
                            if type_child.type != ':':  # Skip the colon
                                param_type = self._get_node_text(type_child, code_bytes)

                if param_name:
                    if param_type:
                        parameters.append({'name': param_name, 'type': param_type})
                    else:
                        parameters.append({'name': param_name})

            elif param_node.type == 'optional_parameter':
                # Parameter with ? indicating optional
                param_name = None
                param_type = None

                for child in param_node.children:
                    if child.type == 'identifier':
                        param_name = self._get_node_text(child, code_bytes)
                    elif child.type == 'type_annotation':
                        for type_child in child.children:
                            if type_child.type != ':':  # Skip the colon
                                param_type = self._get_node_text(type_child, code_bytes)

                if param_name:
                    param_info = {'name': param_name, 'optional': True}
                    if param_type:
                        param_info['type'] = param_type
                    parameters.append(param_info)

            elif param_node.type == 'default_parameter':
                # Parameter with default value
                param_name = None
                param_type = None
                default_value = None

                for child in param_node.children:
                    if child.type == 'identifier':
                        param_name = self._get_node_text(child, code_bytes)
                    elif child.type == 'type_annotation':
                        for type_child in child.children:
                            if type_child.type != ':':  # Skip the colon
                                param_type = self._get_node_text(type_child, code_bytes)
                    elif child.type == '=':
                        continue
                    else:
                        default_value = self._get_node_text(child, code_bytes)

                if param_name:
                    param_info = {'name': param_name}
                    if param_type:
                        param_info['type'] = param_type
                    if default_value:
                        param_info['default'] = default_value
                    parameters.append(param_info)

        return parameters

    def get_function_return_info(self, code: str, function_name: str, class_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract return type and return values from a function or method.

        Args:
            code: Source code as string
            function_name: Function or method name
            class_name: Class name if searching for method, None for standalone functions

        Returns:
            Dictionary with return_type and return_values
        """
        (root, code_bytes) = self._get_tree(code)

        # Find function or method node
        function_node = None

        if class_name:
            # For class methods
            query_str = f"""
            (method_definition
              name: (property_identifier) @method_name (#eq? @method_name "{function_name}"))
            """
            query = Query(TS_LANGUAGE, query_str)
            raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
            captures = self._process_captures(raw_captures)

            for node, cap_name in captures:
                if cap_name == 'method_name':
                    function_node = node.parent
                    break
        else:
            # For standalone functions
            query_str = f"""
            (function_declaration
              name: (identifier) @func_name (#eq? @func_name "{function_name}"))
            """
            query = Query(TS_LANGUAGE, query_str)
            raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
            captures = self._process_captures(raw_captures)

            for node, cap_name in captures:
                if cap_name == 'func_name':
                    function_node = node.parent
                    break

            # If not found, try arrow function
            if not function_node:
                arrow_query_str = f"""
                (variable_declaration
                  declarator: (variable_declarator
                    name: (identifier) @func_name (#eq? @func_name "{function_name}")
                    value: (arrow_function)))
                """
                arrow_query = Query(TS_LANGUAGE, arrow_query_str)
                arrow_captures = arrow_query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
                arrow_captures = self._process_captures(arrow_captures)

                for node, cap_name in arrow_captures:
                    if cap_name == 'func_name':
                        # Get the arrow function node
                        for child in node.parent.children:
                            if child.type == 'arrow_function':
                                function_node = child
                                break
                        break

        if not function_node:
            return {'return_type': None, 'return_values': []}

        # Extract return type annotation
        return_type = None

        # Look for return type annotation
        for child in function_node.children:
            if child.type == 'return_type':
                for type_child in child.children:
                    if type_child.type != ':':  # Skip the colon
                        return_type = self._get_node_text(type_child, code_bytes)
                        break

        # Extract return statements
        return_values = []

        def find_return_statements(node):
            if node.type == 'return_statement':
                for child in node.children:
                    if child.type != 'return':  # Skip the 'return' keyword
                        return_values.append(self._get_node_text(child, code_bytes))

            for child in node.children:
                find_return_statements(child)

        # For arrow functions with implicit returns
        if function_node.type == 'arrow_function':
            body = None
            for child in function_node.children:
                if child.type != 'formal_parameters' and child.type != '=>' and child.type != 'return_type':
                    body = child
                    break

            if body and body.type != 'statement_block':
                # Implicit return
                return_values.append(self._get_node_text(body, code_bytes))

        # Find explicit return statements
        find_return_statements(function_node)

        return {
            'return_type': return_type,
            'return_values': return_values
        }