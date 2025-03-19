import re
from typing import Tuple, List, Optional

from rich.console import Console
from tree_sitter import Query, Node
from core.finder.base import CodeFinder
from core.languages import PY_LANGUAGE

class PythonCodeFinder(CodeFinder):
    language = "python"

    def can_handle(self, code: str) -> bool:
        """
        Check if this finder can handle Python code.

        Args:
        code: Source code as string

        Returns:
        True if this is Python code, False otherwise
        """
        # Check for distinctive Python syntax
        python_indicators = {
            # Strong Python indicators (highly distinctive)
            'strong': [
                # Python-style function definitions with colon and indented body
                re.search(r'def\s+\w+\s*\([^)]*\)\s*:', code) is not None,
                # Class definitions with colon
                re.search(r'class\s+\w+(\s*\([^)]*\))?\s*:', code) is not None,
                # Python-style indentation (function body indented without braces)
                re.search(r'def\s+\w+\s*\([^)]*\)\s*:\s*\n\s+', code) is not None,
                # Python's self parameter in methods
                re.search(r'def\s+\w+\s*\(\s*self', code) is not None,
            ],
            # Medium strength indicators (characteristic but not exclusive)
            'medium': [
                # Python-style imports
                re.search(r'^import\s+\w+', code, re.MULTILINE) is not None,
                re.search(r'^from\s+[\w.]+\s+import', code, re.MULTILINE) is not None,
                # Python decorators
                re.search(r'@\w+', code) is not None,
                # Python-style return type annotations
                re.search(r'def\s+\w+\s*\([^)]*\)\s*->\s*\w+', code) is not None,
            ],
            # Weak indicators (supportive but common across languages)
            'weak': [
                # Significant whitespace/indentation patterns
                re.search(r'\n\s+\S', code) is not None,
                # Python-style comments
                re.search(r'#.*$', code, re.MULTILINE) is not None,
                # Python-style type hints in variables
                re.search(r':\s*\w+(\s*\[\w+\])?\s*=', code) is not None,
            ]
        }

        # Negative indicators (strong evidence against Python)
        negative_indicators = [
            # JavaScript/TypeScript-style blocks with braces
            re.search(r'function\s+\w+\s*\([^)]*\)\s*{', code) is not None,
            # Heavy use of semicolons (rare in Python)
            code.count(';') > code.count('\n') / 2,
            # JavaScript/TypeScript variable declarations
            re.search(r'(const|let|var)\s+\w+\s*=', code) is not None,
            # TypeScript-style interfaces
            re.search(r'interface\s+\w+\s*{', code) is not None,
            # JavaScript-style imports
            re.search(r'import\s+{\s*[^}]+\s*}\s+from', code) is not None,
        ]

        # Calculate confidence score for Python
        confidence = 0
        # Strong indicators carry more weight
        confidence += sum(python_indicators['strong']) * 3
        confidence += sum(python_indicators['medium']) * 2
        confidence += sum(python_indicators['weak']) * 1
        # Negative indicators reduce confidence significantly
        confidence -= sum(negative_indicators) * 4

        # Threshold for Python detection (tuned value)
        confidence_threshold = 2

        # Highly confident if we have any strong indicators and no negative indicators
        if sum(python_indicators['strong']) > 0 and sum(negative_indicators) == 0:
            return True

        # Otherwise, use confidence threshold
        return confidence >= confidence_threshold

    def find_function(self, code: str, function_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n        (\n            function_definition\n            name: (identifier) @func_name\n        )\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            if cap_name == 'func_name' and self._get_node_text(node, code_bytes) == function_name:
                func_node = node
                while func_node is not None and func_node.type != 'function_definition':
                    func_node = func_node.parent
                if func_node is not None:
                    return (func_node.start_point[0] + 1, func_node.end_point[0] + 1)
        return (0, 0)

    def find_class(self, code: str, class_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n        (\n            class_definition\n            name: (identifier) @class_name\n        )\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            if cap_name == 'class_name' and self._get_node_text(node, code_bytes) == class_name:
                class_node = node
                while class_node is not None and class_node.type != 'class_definition':
                    class_node = class_node.parent
                if class_node is not None:
                    return (class_node.start_point[0] + 1, class_node.end_point[0] + 1)
        return (0, 0)

    def find_method(self, code: str, class_name: str, method_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n        (\n            function_definition\n            name: (identifier) @method_name\n        )\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            if cap_name == 'method_name' and self._get_node_text(node, code_bytes) == method_name:
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_definition':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    curr = curr.parent
                if inside:
                    method_node = node
                    while method_node is not None and method_node.type != 'function_definition':
                        method_node = method_node.parent
                    if method_node:
                        return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
        return (0, 0)

    def find_imports_section(self, code: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n        (import_statement) @import\n        (import_from_statement) @import\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        nodes = [node for (node, _) in captures]
        if not nodes:
            return (0, 0)
        nodes.sort(key=lambda node: node.start_point[0])
        return (nodes[0].start_point[0] + 1, nodes[-1].end_point[0] + 1)

    def get_class_with_updated_property(self, code: str, class_name: str, property_name: str, new_property_code: str) -> str:
        (class_start, class_end) = self.find_class(code, class_name)
        if class_start == 0 or class_end == 0:
            return code
        lines = code.splitlines()
        class_code = '\n'.join(lines[class_start - 1:class_end])
        methods = self.get_methods_from_class(code, class_name)
        getter_found = False
        setter_found = False
        getter_range = (0, 0)
        setter_range = (0, 0)
        for (method_name, method_node) in methods:
            if method_name == property_name:
                is_property = False
                current = method_node
                while current and (not is_property):
                    for child in current.children:
                        if child.type == 'decorator':
                            decorator_text = self._get_node_text(child, code.encode('utf8'))
                            if '@property' in decorator_text:
                                is_property = True
                                break
                    if is_property:
                        break
                    current = current.parent
                if is_property:
                    getter_found = True
                    getter_range = self.get_node_range(method_node)
            if method_name == property_name:
                is_setter = False
                current = method_node
                while current and (not is_setter):
                    for child in current.children:
                        if child.type == 'decorator':
                            decorator_text = self._get_node_text(child, code.encode('utf8'))
                            if f'@{property_name}.setter' in decorator_text:
                                is_setter = True
                                break
                    if is_setter:
                        break
                    current = current.parent
                if is_setter:
                    setter_found = True
                    setter_range = self.get_node_range(method_node)
        if getter_found and setter_found:
            if getter_range[0] < setter_range[0]:
                start_line = getter_range[0]
                end_line = setter_range[1]
            else:
                start_line = setter_range[0]
                end_line = getter_range[1]
            new_class_lines = []
            for i in range(class_start - 1, start_line - 1):
                new_class_lines.append(lines[i])
            class_indent = self._get_indentation(lines[class_start - 1])
            method_indent = class_indent + '    '
            for property_line in new_property_code.splitlines():
                if property_line.strip():
                    new_class_lines.append(method_indent + property_line.strip())
                else:
                    new_class_lines.append('')
            for i in range(end_line, class_end):
                new_class_lines.append(lines[i])
            return '\n'.join(new_class_lines)
        elif getter_found:
            start_line = getter_range[0]
            end_line = getter_range[1]
            new_class_lines = []
            for i in range(class_start - 1, start_line - 1):
                new_class_lines.append(lines[i])
            class_indent = self._get_indentation(lines[class_start - 1])
            method_indent = class_indent + '    '
            for property_line in new_property_code.splitlines():
                if property_line.strip():
                    new_class_lines.append(method_indent + property_line.strip())
                else:
                    new_class_lines.append('')
            for i in range(end_line, class_end):
                new_class_lines.append(lines[i])
            return '\n'.join(new_class_lines)
        elif setter_found:
            start_line = setter_range[0]
            end_line = setter_range[1]
            new_class_lines = []
            for i in range(class_start - 1, start_line - 1):
                new_class_lines.append(lines[i])
            class_indent = self._get_indentation(lines[class_start - 1])
            method_indent = class_indent + '    '
            for property_line in new_property_code.splitlines():
                if property_line.strip():
                    new_class_lines.append(method_indent + property_line.strip())
                else:
                    new_class_lines.append('')
            for i in range(end_line, class_end):
                new_class_lines.append(lines[i])
            return '\n'.join(new_class_lines)
        else:
            class_indent = self._get_indentation(lines[class_start - 1])
            method_indent = class_indent + '    '
            indented_property = []
            for line in new_property_code.splitlines():
                if line.strip():
                    indented_property.append(method_indent + line.strip())
                else:
                    indented_property.append('')
            new_property_text = '\n'.join(indented_property)
            new_class_code = class_code.rstrip()
            if not new_class_code.endswith('\n'):
                new_class_code += '\n'
            new_class_code += '\n' + new_property_text + '\n'
            return new_class_code

    def _get_indentation(self, line: str) -> str:
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    def find_property(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n        (\n            function_definition\n            name: (identifier) @prop_name\n        )\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            if cap_name == 'prop_name' and self._get_node_text(node, code_bytes) == property_name:
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_definition':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    curr = curr.parent
                if inside:
                    func_node = node
                    while func_node is not None and func_node.type != 'function_definition':
                        func_node = func_node.parent
                    if func_node is not None:
                        has_property_decorator = False
                        if func_node.parent and func_node.parent.type == 'decorated_definition':
                            for child in func_node.parent.children:
                                if child.type == 'decorator' and '@property' in self._get_node_text(child, code_bytes):
                                    has_property_decorator = True
                                    break
                        if not has_property_decorator:
                            for child in func_node.children:
                                if child.type == 'decorator' and '@property' in self._get_node_text(child, code_bytes):
                                    has_property_decorator = True
                                    break
                        if has_property_decorator:
                            if func_node.parent and func_node.parent.type == 'decorated_definition':
                                return (func_node.parent.start_point[0] + 1, func_node.end_point[0] + 1)
                            else:
                                return (func_node.start_point[0] + 1, func_node.end_point[0] + 1)
        return (0, 0)

    def find_property_setter(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n        (\n            function_definition\n            name: (identifier) @prop_name\n        )\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_name) in captures:
            if cap_name == 'prop_name' and self._get_node_text(node, code_bytes) == property_name:
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_definition':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    curr = curr.parent
                if inside:
                    func_node = node
                    while func_node is not None and func_node.type != 'function_definition':
                        func_node = func_node.parent
                    if func_node is not None:
                        setter_decorator_pattern = f'@{property_name}.setter'
                        if func_node.parent and func_node.parent.type == 'decorated_definition':
                            for child in func_node.parent.children:
                                if child.type == 'decorator' and setter_decorator_pattern in self._get_node_text(child, code_bytes):
                                    return (func_node.parent.start_point[0] + 1, func_node.end_point[0] + 1)
                        for child in func_node.children:
                            if child.type == 'decorator' and setter_decorator_pattern in self._get_node_text(child, code_bytes):
                                return (func_node.start_point[0] + 1, func_node.end_point[0] + 1)
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

    def find_properties_section(self, code: str, class_name: str) -> Tuple[int, int]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n        (assignment\n           left: (identifier) @prop\n        )\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        property_nodes = []
        for (node, _) in captures:
            curr = node
            inside_class = False
            while curr is not None:
                if curr.type == 'class_definition':
                    class_name_node = curr.child_by_field_name('name')
                    if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                        inside_class = True
                    break
                elif curr.type == 'function_definition':
                    break
                curr = curr.parent
            if inside_class:
                property_nodes.append(node)
        if not property_nodes:
            return (0, 0)
        property_nodes.sort(key=lambda node: node.start_point[0])
        return (property_nodes[0].start_point[0] + 1, property_nodes[-1].end_point[0] + 1)

    def get_classes_from_code(self, code: str) -> List[Tuple[str, Node]]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n        (\n            class_definition\n            name: (identifier) @class_name\n        ) @class\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        classes = []
        class_nodes = {}
        class_names = {}
        for (node, cap_type) in captures:
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
        query_str = '\n        (\n            function_definition\n            name: (identifier) @func_name\n        ) @function\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        methods = []
        func_nodes = {}
        func_names = {}
        for (node, cap_type) in captures:
            if cap_type == 'function':
                func_nodes[node.id] = node
            elif cap_type == 'func_name':
                func_name = self._get_node_text(node, code_bytes)
                func_names[node.parent.id] = func_name
        for (node_id, node) in func_nodes.items():
            if node_id in func_names:
                methods.append((func_names[node_id], node))
        return methods

    def get_methods_from_class(self, code: str, class_name: str) -> List[Tuple[str, Node]]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n        (\n            class_definition\n            name: (identifier) @class_name\n        ) @class\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        class_node = None
        for (node, cap_type) in captures:
            if cap_type == 'class_name' and self._get_node_text(node, code_bytes) == class_name:
                class_node = node.parent
                break
        if not class_node:
            return []
        query_str = '\n        (\n            function_definition\n            name: (identifier) @method_name\n        ) @method\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(class_node, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        methods = []
        method_nodes = {}
        method_names = {}
        for (node, cap_type) in captures:
            if cap_type == 'method':
                method_nodes[node.id] = node
            elif cap_type == 'method_name':
                method_name = self._get_node_text(node, code_bytes)
                method_names[node.parent.id] = method_name
        for (node_id, node) in method_nodes.items():
            if node_id in method_names:
                methods.append((method_names[node_id], node))
        return methods

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
        (root, code_bytes) = self._get_tree(code)

        if class_name:
            # Get method decorators
            method_node = None
            methods = self.get_methods_from_class(code, class_name)
            for method_name, node in methods:
                if method_name == name:
                    method_node = node
                    break

            if not method_node:
                return []

            # Check if the function has decorators
            decorators = []

            # First check if the function is inside a decorated_definition
            if method_node.parent and method_node.parent.type == 'decorated_definition':
                for child in method_node.parent.children:
                    if child.type == 'decorator':
                        decorators.append(self._get_node_text(child, code_bytes))

            # Also check for decorators directly under the function (some tree-sitter parsers structure it this way)
            for child in method_node.children:
                if child.type == 'decorator':
                    decorator_text = self._get_node_text(child, code_bytes)
                    if decorator_text not in decorators:
                        decorators.append(decorator_text)

            return decorators
        else:
            # Get function decorators
            query_str = '(function_definition name: (identifier) @func_name)'
            query = Query(PY_LANGUAGE, query_str)
            raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
            captures = self._process_captures(raw_captures)

            func_node = None
            for node, cap_name in captures:
                if cap_name == 'func_name' and self._get_node_text(node, code_bytes) == name:
                    func_node = node
                    while func_node is not None and func_node.type != 'function_definition':
                        func_node = func_node.parent
                    break

            if not func_node:
                return []

            # Check for decorators
            decorators = []

            # Check if function is inside a decorated_definition
            decorated_parent = func_node.parent
            if decorated_parent and decorated_parent.type == 'decorated_definition':
                for child in decorated_parent.children:
                    if child.type == 'decorator':
                        decorators.append(self._get_node_text(child, code_bytes))

            # Also check for decorators directly under the function
            for child in func_node.children:
                if child.type == 'decorator':
                    decorator_text = self._get_node_text(child, code_bytes)
                    if decorator_text not in decorators:
                        decorators.append(decorator_text)

            return decorators

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
        
        # Find the class node
        class_node = None
        classes = self.get_classes_from_code(code)
        for cls_name, node in classes:
            if cls_name == class_name:
                class_node = node
                break
                
        if not class_node:
            return []
            
        # Check for decorators
        decorators = []
        
        # First check if the class is inside a decorated_definition
        if class_node.parent and class_node.parent.type == 'decorated_definition':
            for child in class_node.parent.children:
                if child.type == 'decorator':
                    decorators.append(self._get_node_text(child, code_bytes))
        
        # Also check for decorators directly under the class
        for child in class_node.children:
            if child.type == 'decorator':
                decorator_text = self._get_node_text(child, code_bytes)
                if decorator_text not in decorators:
                    decorators.append(decorator_text)
                    
        return decorators

    def has_class_method_indicator(self, method_node: Node, code_bytes: bytes) -> bool:
        params_node = None
        for child in method_node.children:
            if child.type == 'parameters':
                params_node = child
                break
        if not params_node:
            return False
        for child in params_node.children:
            if child.type == 'identifier':
                param_name = self._get_node_text(child, code_bytes)
                return param_name == 'self'
        return False

    def is_correct_syntax(self, plain_text: str) -> bool:
        try:
            self._get_tree(plain_text)
            import ast
            ast.parse(plain_text)
            return True
        except Exception:
            return False

    def find_class_for_method(self, method_name: str, code: str) -> Optional[str]:
        try:
            (root, code_bytes) = self._get_tree(code)
            query_str = f'\n            (function_definition\n              name: (identifier) @func_name (#eq? @func_name "{method_name}"))\n            '
            query = Query(PY_LANGUAGE, query_str)
            raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
            captures = self._process_captures(raw_captures)
            for item in captures:
                if not isinstance(item, tuple) or len(item) < 2:
                    continue
                (node, cap_type) = (item[0], item[1])
                if cap_type != 'func_name':
                    continue
                func_node = node.parent
                if not func_node or func_node.type != 'function_definition':
                    continue
                if not self.has_class_method_indicator(func_node, code_bytes):
                    continue
                current = func_node.parent
                while current and current.type != 'class_definition':
                    current = current.parent
                if current and current.type == 'class_definition':
                    class_name_node = current.child_by_field_name('name')
                    if class_name_node:
                        return self._get_node_text(class_name_node, code_bytes)
                    for child in current.children:
                        if child.type == 'identifier':
                            return self._get_node_text(child, code_bytes)
            return None
        except Exception as e:
            console = Console()
            console.print(f'[yellow]Error in find_class_for_method: {e}[/yellow]')
            import traceback
            console.print(f'[dim]{traceback.format_exc()}[/dim]')
            return None

    def content_looks_like_class_definition(self, content: str) -> bool:
        if not content or not content.strip():
            return False
        content_lines = content.strip().splitlines()
        if not content_lines:
            return False
        first_line = content_lines[0].strip()
        if first_line.startswith('class ') and (':' in first_line or '(' in first_line):
            return True
        return super().content_looks_like_class_definition(content)

    def find_parent_classes(self, code: str, class_name: str) -> List[str]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '\n        (\n            class_definition\n            name: (identifier) @class_name\n            superclasses: (argument_list) @parents\n        )\n        '
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        class_nodes = {}
        class_names = {}
        parent_nodes = {}
        for (node, cap_type) in captures:
            if cap_type == 'class_name':
                name = self._get_node_text(node, code_bytes)
                class_names[node.parent.id] = name
                class_nodes[node.parent.id] = node.parent
            elif cap_type == 'parents':
                parent_nodes[node.parent.id] = node
        for (node_id, name) in class_names.items():
            if name == class_name and node_id in parent_nodes:
                parents_node = parent_nodes[node_id]
                parents = []
                for child in parents_node.children:
                    if child.type == 'identifier':
                        parents.append(self._get_node_text(child, code_bytes))
                    elif child.type == 'attribute':
                        parents.append(self._get_node_text(child, code_bytes))
                return parents
        return []

    def find_module_for_class(self, code: str, class_name: str) -> Optional[str]:
        (root, code_bytes) = self._get_tree(code)
        query_str = '(import_from_statement module_name: (_) @module name: (dotted_name) @imported_name)'
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        modules = {}
        imported_names = {}
        for (node, cap_type) in captures:
            if cap_type == 'module':
                module_name = self._get_node_text(node, code_bytes)
                modules[node.parent.id] = module_name
            elif cap_type == 'imported_name':
                name = self._get_node_text(node, code_bytes)
                if name == class_name:
                    imported_names[node.parent.id] = name
        for (node_id, name) in imported_names.items():
            if node_id in modules:
                return modules[node_id]
        query_str = '(import_from_statement module_name: (_) @module aliased_import name: (dotted_name) @orig_name alias: (identifier) @alias_name)'
        try:
            query = Query(PY_LANGUAGE, query_str)
            raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
            captures = self._process_captures(raw_captures)
            modules = {}
            aliases = {}
            orig_names = {}
            for (node, cap_type) in captures:
                if cap_type == 'module':
                    module_name = self._get_node_text(node, code_bytes)
                    modules[node.parent.id] = module_name
                elif cap_type == 'alias_name':
                    alias = self._get_node_text(node, code_bytes)
                    if alias == class_name:
                        aliases[node.parent.id] = alias
                elif cap_type == 'orig_name':
                    orig_name = self._get_node_text(node, code_bytes)
                    orig_names[node.parent.id] = orig_name
            for (node_id, _) in aliases.items():
                if node_id in modules:
                    orig_name = orig_names.get(node_id, '')
                    if orig_name:
                        return f'{modules[node_id]}.{orig_name}'
                    else:
                        return modules[node_id]
        except Exception:
            pass
        
        # Handle aliased imports - using a regex approach as a fallback
        try:
            import re
            aliased_pattern = re.compile(r'from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_]+)\s+as\s+([a-zA-Z0-9_]+)')
            for match in aliased_pattern.finditer(code):
                module, orig_class, alias = match.groups()
                if alias == class_name:
                    return f"{module}.{orig_class}"
        except Exception:
            pass
            
        query_str = '(import_statement name: (_) @module)'
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for (node, cap_type) in captures:
            if cap_type == 'module':
                module_name = self._get_node_text(node, code_bytes)
                if f'{module_name}.{class_name}'.encode('utf8') in code_bytes:
                    return module_name
        query_str = '(attribute object: (_) @module attribute: (identifier) @attr)'
        try:
            query = Query(PY_LANGUAGE, query_str)
            raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
            captures = self._process_captures(raw_captures)
            for (node, cap_type) in captures:
                if cap_type == 'attr' and self._get_node_text(node, code_bytes) == class_name:
                    parent_node = node.parent.child_by_field_name('object')
                    if parent_node:
                        return self._get_node_text(parent_node, code_bytes)
        except Exception:
            pass
        return None