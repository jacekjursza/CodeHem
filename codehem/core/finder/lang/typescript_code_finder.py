import re
from typing import Tuple, List, Optional, Dict, Any
from tree_sitter import Query, Node
from codehem.core.finder.base import CodeFinder
from codehem.core.languages import TS_LANGUAGE
from rich.console import Console

class TypeScriptCodeFinder(CodeFinder):
    language = 'typescript'

    def __init__(self):
        super().__init__()
        self.console = Console()

    def can_handle(self, code: str) -> bool:
        """
        Check if this finder can handle TypeScript/JavaScript code.

        Args:
        code: Source code as string

        Returns:
        True if this is TypeScript/JavaScript code, False otherwise
        """
        ts_js_indicators = {
            'strong': [
                re.search('function\\s+\\w+\\s*\\([^)]*\\)\\s*{', code) is not None,
                re.search('class\\s+\\w+\\s*{', code) is not None,
                re.search('=>\\s*{', code) is not None,
                re.search('interface\\s+\\w+\\s*{', code) is not None,
                re.search('enum\\s+\\w+\\s*{', code) is not None,
                re.search('import\\s+{\\s*[^}]+\\s*}\\s+from', code) is not None,
                re.search('const\\s+\\w+\\s*=\\s*function', code) is not None,
                re.search('var\\s+\\w+\\s*=\\s*function', code) is not None,
                re.search('let\\s+\\w+\\s*=\\s*function', code) is not None,
                re.search('angular\\.module', code) is not None,
                re.search('\\.controller\\(', code) is not None,
                re.search('\\.directive\\(', code) is not None,
                re.search('\\.service\\(', code) is not None,
                re.search('\\.factory\\(', code) is not None,
                re.search('\\.provider\\(', code) is not None,
                re.search('\\.config\\(', code) is not None,
                re.search('\\.run\\(', code) is not None,
                re.search('this\\.\\w+\\s*=\\s*function', code) is not None,
                re.search("'use strict';", code) is not None,
                re.search('"use strict";', code) is not None
            ],
            'medium': [
                re.search('(const|let|var)\\s+\\w+', code) is not None,
                re.search('=>', code) is not None,
                re.search('<\\w+[^>]*>', code) is not None and re.search('</\\w+>', code) is not None,
                re.search('export\\s+(class|const|function|interface)', code) is not None,
                re.search('this\\.\\w+\\s*=', code) is not None,
                re.search('\\$scope', code) is not None,
                re.search('\\$http', code) is not None,
                re.search('\\$q', code) is not None,
                re.search('\\$rootScope', code) is not None
            ],
            'weak': [
                ';' in code and code.count(';') > code.count('\n') / 5,
                re.search('//.*$', code, re.MULTILINE) is not None,
                re.search('{\\s*[\\w]+\\s*:', code) is not None,
                re.search('function\\(', code) is not None
            ]
        }
        
        negative_indicators = [
            re.search('def\\s+\\w+\\s*\\([^)]*\\)\\s*:', code) is not None,
            re.search('def\\s+\\w+\\s*\\([^)]*\\)\\s*:\\s*\\n\\s+', code) is not None,
            re.search('def\\s+\\w+\\s*\\(\\s*self', code) is not None,
            re.search('@\\w+', code) is not None and (not re.search('@\\w+\\(', code) is not None),
            re.search('^from\\s+[\\w.]+\\s+import', code, re.MULTILINE) is not None
        ]
        
        has_only_comments = re.search('//.*$', code, re.MULTILINE) is not None and (not any((
            re.search(pattern, code) is not None 
            for pattern in ['function', 'class', 'var', 'let', 'const', '{', '}', '=', '=>']
        )))
        
        # Fast path for common Angular patterns
        if 'angular.module' in code or '.controller(' in code or '.service(' in code or \
           ('.directive(' in code) or ('.factory(' in code) or ('.provider(' in code):
            return True
            
        # Calculate confidence score
        confidence = 0
        confidence += sum(ts_js_indicators['strong']) * 3
        confidence += sum(ts_js_indicators['medium']) * 2
        confidence += sum(ts_js_indicators['weak']) * 1
        confidence -= sum(negative_indicators) * 4
        
        if has_only_comments:
            confidence -= 2
            
        confidence_threshold = 3
        
        # Strong indicators with no negative indicators is a definite match
        if sum(ts_js_indicators['strong']) > 0 and sum(negative_indicators) == 0:
            return True
            
        return confidence >= confidence_threshold

    def _execute_query(self, query_str: str, root_node: Node, code_bytes: bytes) -> List[Tuple[Node, str]]:
        """
        Execute a tree-sitter query and process the captures with error handling.

        Args:
            query_str: Query string in tree-sitter format
            root_node: Root node to query against
            code_bytes: Source code as bytes

        Returns:
            List of processed captures (node, capture_name)
        """
        try:
            query = Query(TS_LANGUAGE, query_str)
            raw_captures = query.captures(root_node, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
            return self._process_captures(raw_captures)
        except Exception as e:
            self.console.print(f"[yellow]Error executing query: {e}[/yellow]")
            return []

    def _find_node_by_query(self, code: str, query_str: str, match_conditions: Optional[Dict[str, str]]=None) -> Optional[Node]:
        """
        Find a node using a tree-sitter query with optional match conditions.

        Args:
            code: Source code
            query_str: Query string in tree-sitter format
            match_conditions: Dictionary of {capture_name: expected_value}

        Returns:
            Matching node or None if not found
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            captures = self._execute_query(query_str, root, code_bytes)
            
            if not match_conditions:
                return captures[0][0] if captures else None
                
            capture_dict = {}
            for (node, capture_name) in captures:
                if capture_name not in capture_dict:
                    capture_dict[capture_name] = []
                capture_dict[capture_name].append((node, self._get_node_text(node, code_bytes)))
                
            matched_nodes = {}
            for (capture_name, expected_value) in match_conditions.items():
                if capture_name not in capture_dict:
                    return None
                    
                for (node, value) in capture_dict[capture_name]:
                    if value == expected_value:
                        matched_nodes[capture_name] = node
                        break
                        
                if capture_name not in matched_nodes:
                    return None
                    
            for capture_name in match_conditions:
                node = matched_nodes[capture_name]
                parent_type = match_conditions.get('parent_type')
                current = node
                
                while current and (not parent_type or current.type != parent_type):
                    current = current.parent
                    
                if current:
                    return current
                    
            return None
        except Exception as e:
            self.console.print(f"[yellow]Error in _find_node_by_query: {e}[/yellow]")
            return None

    def _is_node_inside_class(self, node: Node, class_name: str, code_bytes: bytes) -> bool:
        """
        Check if a node is inside a class with the given name.

        Args:
            node: Node to check
            class_name: Expected class name
            code_bytes: Source code as bytes

        Returns:
            True if the node is inside the specified class
        """
        try:
            current = node
            while current is not None:
                if current.type == 'class_declaration':
                    class_name_node = current.child_by_field_name('name')
                    if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                        return True
                    break
                current = current.parent
            return False
        except Exception as e:
            self.console.print(f"[yellow]Error in _is_node_inside_class: {e}[/yellow]")
            return False

    def find_function(self, code: str, function_name: str) -> Tuple[int, int]:
        """
        Find a function declaration in TypeScript code.

        Args:
        code: Source code as string
        function_name: Name of the function to find

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            query_str = '(function_declaration name: (identifier) @func_name)'
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                if cap_name == 'func_name' and self._get_node_text(node, code_bytes) == function_name:
                    func_node = node
                    while func_node is not None and func_node.type != 'function_declaration':
                        func_node = func_node.parent
                    if func_node is not None:
                        return (func_node.start_point[0] + 1, func_node.end_point[0] + 1)
                        
            # If no function declaration is found, try to find a variable function
            return self.find_variable_function(code, function_name)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_function: {e}[/yellow]")
            return (0, 0)

    def find_class(self, code: str, class_name: str) -> Tuple[int, int]:
        """
        Find a class in TypeScript code.

        Args:
        code: Source code as string
        class_name: Name of the class to find

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            lines = code.splitlines()
            
            # First, try regex-based approach
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
                    
            # If regex approach fails, try with AST
            (root, code_bytes) = self._get_tree(code)
            query_str = f'(class_declaration name: (identifier) @class_name (#eq? @class_name "{class_name}"))'
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                if cap_name == 'class_name' and self._get_node_text(node, code_bytes) == class_name:
                    class_node = self.ast_handler.find_parent_of_type(node, 'class_declaration')
                    if class_node:
                        return (class_node.start_point[0] + 1, class_node.end_point[0] + 1)
                        
            return (0, 0)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_class: {e}[/yellow]")
            return (0, 0)

    def find_method(self, code: str, class_name: str, method_name: str) -> Tuple[int, int]:
        """
        Find a method in a TypeScript class.

        Args:
        code: Source code as string
        class_name: Name of the class containing the method
        method_name: Name of the method to find

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            query_str = '(method_definition name: (property_identifier) @method_name)'
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                if cap_name == 'method_name' and self._get_node_text(node, code_bytes) == method_name:
                    if self._is_node_inside_class(node, class_name, code_bytes):
                        method_node = node
                        while method_node is not None and method_node.type != 'method_definition':
                            method_node = method_node.parent
                        if method_node:
                            return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
                            
            return (0, 0)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_method: {e}[/yellow]")
            return (0, 0)

    def find_imports_section(self, code: str) -> Tuple[int, int]:
        """
        Find the imports section in TypeScript code.

        Args:
        code: Source code as string

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            query_str = '(import_statement) @import'
            captures = self._execute_query(query_str, root, code_bytes)
            
            nodes = [node for (node, _) in captures]
            if not nodes:
                return (0, 0)
                
            nodes.sort(key=lambda node: node.start_point[0])
            return (nodes[0].start_point[0] + 1, nodes[-1].end_point[0] + 1)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_imports_section: {e}[/yellow]")
            return (0, 0)

    def find_properties_section(self, code: str, class_name: str) -> Tuple[int, int]:
        """
        Find the properties section in a TypeScript class.

        Args:
        code: Source code as string
        class_name: Name of the class

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            query_str = '(public_field_definition name: (property_identifier) @prop)'
            captures = self._execute_query(query_str, root, code_bytes)
            
            property_nodes = []
            for (node, _) in captures:
                if self._is_node_inside_class(node, class_name, code_bytes):
                    property_nodes.append(node)
                    
            if not property_nodes:
                return (0, 0)
                
            property_nodes.sort(key=lambda node: node.start_point[0])
            return (property_nodes[0].start_point[0] + 1, property_nodes[-1].end_point[0] + 1)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_properties_section: {e}[/yellow]")
            return (0, 0)

    def get_classes_from_code(self, code: str) -> List[Tuple[str, Node]]:
        """
        Get all classes from TypeScript code.

        Args:
        code: Source code as string

        Returns:
        List of tuples with (class_name, class_node)
        """
        try:
            classes = []
            class_pattern = re.compile('(^|\\s)(abstract\\s+)?(class\\s+([A-Za-z_][A-Za-z0-9_]*)\\b)|' + 
                                      '(^|\\s)(export\\s+)(class\\s+([A-Za-z_][A-Za-z0-9_]*)\\b)')
            lines = code.splitlines()
            (root, code_bytes) = self._get_tree(code)
            
            for (i, line) in enumerate(lines):
                match = class_pattern.search(line)
                if match:
                    class_name = match.group(4) or match.group(8)
                    if class_name:
                        classes.append((class_name, root))
                        
            return classes
        except Exception as e:
            self.console.print(f"[yellow]Error in get_classes_from_code: {e}[/yellow]")
            return []

    def get_methods_from_code(self, code: str) -> List[Tuple[str, Node]]:
        """
        Get all methods and functions from TypeScript code.

        Args:
        code: Source code as string

        Returns:
        List of tuples with (method_name, method_node)
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            methods = []
            
            # First, find function declarations
            query_str = '(function_declaration name: (identifier) @func_name)'
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                if cap_name == 'func_name':
                    func_name = self._get_node_text(node, code_bytes)
                    func_node = self.ast_handler.find_parent_of_type(node, 'function_declaration')
                    if func_node:
                        methods.append((func_name, func_node))
            
            # Then, find method definitions
            query_str = '(method_definition name: (property_identifier) @method_name)'
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                if cap_name == 'method_name':
                    method_name = self._get_node_text(node, code_bytes)
                    method_node = self.ast_handler.find_parent_of_type(node, 'method_definition')
                    if method_node:
                        methods.append((method_name, method_node))
                        
            return methods
        except Exception as e:
            self.console.print(f"[yellow]Error in get_methods_from_code: {e}[/yellow]")
            return []

    def get_methods_from_class(self, code: str, class_name: str) -> List[Tuple[str, Node]]:
        """
        Get all methods from a TypeScript class.

        Args:
        code: Source code as string
        class_name: Name of the class

        Returns:
        List of tuples with (method_name, method_node)
        """
        try:
            methods = []
            method_pattern = re.compile('^\\s*(public|private|protected|static|async)?\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\(')
            
            # Find the class first
            (class_start, class_end) = self.find_class(code, class_name)
            if class_start == 0:
                return []
                
            lines = code.splitlines()
            class_code = '\n'.join(lines[class_start - 1:class_end])
            class_lines = class_code.splitlines()
            
            (root, _) = self._get_tree(code)
            
            for (i, line) in enumerate(class_lines):
                match = method_pattern.search(line)
                if match:
                    method_name = match.group(2)
                    if method_name:
                        methods.append((method_name, root))
                        
            return methods
        except Exception as e:
            self.console.print(f"[yellow]Error in get_methods_from_class: {e}[/yellow]")
            return []

    def has_class_method_indicator(self, method_node: Node, code_bytes: bytes) -> bool:
        """
        Check if a method has 'this' keyword, indicating it's an instance method.

        Args:
            method_node: Method node
            code_bytes: Source code as bytes

        Returns:
            True if the method uses 'this', False otherwise
        """
        try:
            if not method_node:
                return False
                
            method_text = self._get_node_text(method_node, code_bytes)
            return 'this.' in method_text
        except Exception as e:
            self.console.print(f"[yellow]Error in has_class_method_indicator: {e}[/yellow]")
            return False

    def find_property(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        """
        Find a property in a TypeScript class.

        Args:
        code: Source code as string
        class_name: Name of the class containing the property
        property_name: Name of the property to find

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            
            # Try to find a public field definition (property)
            query_str = '(public_field_definition name: (property_identifier) @prop)'
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                if cap_name == 'prop' and self._get_node_text(node, code_bytes) == property_name:
                    if self._is_node_inside_class(node, class_name, code_bytes):
                        prop_node = node
                        while prop_node is not None and prop_node.type != 'public_field_definition':
                            prop_node = prop_node.parent
                        if prop_node:
                            return (prop_node.start_point[0] + 1, prop_node.end_point[0] + 1)
            
            # Try to find a getter method with get_ prefix or getPropertyName pattern
            query_str = '(method_definition name: (property_identifier) @getter)'
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                getter_name = self._get_node_text(node, code_bytes)
                if cap_name == 'getter' and (getter_name == 'get_' + property_name or 
                                           getter_name == 'get' + property_name.capitalize()):
                    if self._is_node_inside_class(node, class_name, code_bytes):
                        method_node = node
                        while method_node is not None and method_node.type != 'method_definition':
                            method_node = method_node.parent
                        if method_node:
                            return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
            
            # Try to find a getter property
            query_str = '(method_definition name: (property_identifier) @prop)'
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                if cap_name == 'prop' and self._get_node_text(node, code_bytes) == property_name:
                    # Check if it's a getter
                    is_getter = False
                    parent_node = node.parent
                    if parent_node:
                        for child in parent_node.children:
                            if child.type == 'get':
                                is_getter = True
                                break
                    
                    if not is_getter:
                        continue
                        
                    if self._is_node_inside_class(node, class_name, code_bytes):
                        method_node = node.parent
                        return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
                        
            return (0, 0)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_property: {e}[/yellow]")
            return (0, 0)

    def find_property_setter(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        """
        Find a property setter in a TypeScript class.

        Args:
        code: Source code as string
        class_name: Name of the class containing the property
        property_name: Name of the property to find

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            
            # Try to find a setter method with set_ prefix or setPropertyName pattern
            query_str = '(method_definition name: (property_identifier) @setter)'
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                setter_name = self._get_node_text(node, code_bytes)
                if cap_name == 'setter' and (setter_name == 'set_' + property_name or 
                                           setter_name == 'set' + property_name.capitalize()):
                    if self._is_node_inside_class(node, class_name, code_bytes):
                        method_node = node
                        while method_node is not None and method_node.type != 'method_definition':
                            method_node = method_node.parent
                        if method_node:
                            return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
            
            # Try to find a setter property
            query_str = '(method_definition name: (property_identifier) @prop)'
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                if cap_name == 'prop' and self._get_node_text(node, code_bytes) == property_name:
                    # Check if it's a setter
                    is_setter = False
                    parent_node = node.parent
                    if parent_node:
                        for child in parent_node.children:
                            if child.type == 'set':
                                is_setter = True
                                break
                    
                    if not is_setter:
                        continue
                        
                    if self._is_node_inside_class(node, class_name, code_bytes):
                        method_node = node.parent
                        return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
                        
            return (0, 0)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_property_setter: {e}[/yellow]")
            return (0, 0)

    def find_property_and_setter(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        """
        Find both a property getter and its setter in a TypeScript class.

        Args:
        code: Source code as string
        class_name: Name of the class containing the property
        property_name: Name of the property to find

        Returns:
        Tuple of (start_line, end_line) covering both getter and setter, or (0, 0) if not found
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
        """
        Update a property in a class and return the updated class code.

        Args:
        code: Source code as string
        class_name: Name of the class
        property_name: Name of the property to update
        new_property_code: New property code

        Returns:
        Updated class code
        """
        try:
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
        except Exception as e:
            self.console.print(f"[yellow]Error in get_class_with_updated_property: {e}[/yellow]")
            return code

    def _get_indentation(self, line: str) -> str:
        """Extract the whitespace indentation from a line."""
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''

    def find_class_for_method(self, method_name: str, code: str) -> Optional[str]:
        """
        Find which class a method belongs to.

        Args:
            method_name: Method name
            code: Source code string

        Returns:
            Class name or None if not found
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            query_str = '(method_definition name: (property_identifier) @method_name)'
            
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                if cap_name == 'method_name' and self._get_node_text(node, code_bytes) == method_name:
                    current = node.parent
                    while current and current.type != 'class_declaration':
                        current = current.parent
                        
                    if current and current.type == 'class_declaration':
                        for child in current.children:
                            if child.type == 'identifier':
                                return self._get_node_text(child, code_bytes)
                            
            query_str = '(public_field_definition name: (property_identifier) @field_name value: (arrow_function))'
            
            captures = self._execute_query(query_str, root, code_bytes)
            
            for (node, cap_name) in captures:
                if cap_name == 'field_name' and self._get_node_text(node, code_bytes) == method_name:
                    current = node.parent
                    while current and current.type != 'class_declaration':
                        current = current.parent
                        
                    if current and current.type == 'class_declaration':
                        for child in current.children:
                            if child.type == 'identifier':
                                return self._get_node_text(child, code_bytes)
                            
            return None
        except Exception as e:
            self.console.print(f"[yellow]Error in find_class_for_method: {e}[/yellow]")
            return None

    def content_looks_like_class_definition(self, content: str) -> bool:
        """Check if content looks like a class definition."""
        if not content or not content.strip():
            return False
            
        content_lines = content.strip().splitlines()
        if not content_lines:
            return False
            
        first_line = content_lines[0].strip()
        if first_line.startswith('class ') and ('{' in first_line or (len(content_lines) > 1 and '{' in content_lines[1].strip())):
            return True
            
        return super().content_looks_like_class_definition(content)

    def find_variable_function(self, code: str, function_name: str) -> Tuple[int, int]:
        """
        Find a function defined as a variable assignment.

        Args:
        code: Source code as string
        function_name: Name of the function to find

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            # First, try regex patterns for common function declaration patterns
            patterns = [
                re.compile('(?:const|let|var)\\s+' + re.escape(function_name) + '\\s*=\\s*function\\s*\\(([^)]*)\\)\\s*{'),
                re.compile('(?:const|let|var)\\s+' + re.escape(function_name) + '\\s*=\\s*\\(([^)]*)\\)\\s*=>'),
                re.compile('^' + re.escape(function_name) + '\\s*=\\s*function\\s*\\(([^)]*)\\)\\s*{', re.MULTILINE)
            ]
            
            for pattern in patterns:
                match = pattern.search(code)
                if match:
                    start_pos = match.start()
                    line_number = code[:start_pos].count('\n') + 1
                    function_code = code[start_pos:]
                    brace_count = 0
                    in_function = False
                    end_pos = 0
                    
                    for (i, char) in enumerate(function_code):
                        if char == '{':
                            brace_count += 1
                            in_function = True
                        elif char == '}':
                            brace_count -= 1
                            if in_function and brace_count == 0:
                                end_pos = i + 1
                                break
                                
                    if end_pos > 0:
                        function_content = function_code[:end_pos]
                        end_line = line_number + function_content.count('\n')
                        return (line_number, end_line)
            
            # If regex approach fails, try with AST
            (root, code_bytes) = self._get_tree(code)
            
            # Try to find lexical declarations (const, let)
            query_str = '(lexical_declaration (variable_declarator name: (identifier) @var_name))'
            
            try:
                captures = self._execute_query(query_str, root, code_bytes)
                
                for (node, cap_name) in captures:
                    if cap_name == 'var_name' and self._get_node_text(node, code_bytes) == function_name:
                        var_func_node = node.parent.parent
                        if var_func_node is not None:
                            return (var_func_node.start_point[0] + 1, var_func_node.end_point[0] + 1)
            except Exception:
                pass
                
            return (0, 0)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_variable_function: {e}[/yellow]")
            return (0, 0)

    def get_function_parameters(self, code: str, function_name: str, class_name: Optional[str]=None) -> List[Dict[str, Any]]:
        """
        Extract parameters from a function or method.

        Args:
            code: Source code as string
            function_name: Function or method name
            class_name: Class name if searching for method parameters, None for standalone functions

        Returns:
            List of parameter dictionaries with name, type (if available), and default value (if available)
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            
            if class_name:
                query_str = '(method_definition name: (property_identifier) @method_name)'
                captures = self._execute_query(query_str, root, code_bytes)
                
                method_node = None
                for (node, cap_name) in captures:
                    if cap_name == 'method_name' and self._get_node_text(node, code_bytes) == function_name:
                        if self._is_node_inside_class(node, class_name, code_bytes):
                            method_node = self.ast_handler.find_parent_of_type(node, 'method_definition')
                            break
                
                if not method_node:
                    return []
                    
                params_node = None
                for child in method_node.children:
                    if child.type == 'formal_parameters':
                        params_node = child
                        break
            else:
                query_str = '(function_declaration name: (identifier) @func_name)'
                captures = self._execute_query(query_str, root, code_bytes)
                
                func_node = None
                for (node, cap_name) in captures:
                    if cap_name == 'func_name' and self._get_node_text(node, code_bytes) == function_name:
                        func_node = self.ast_handler.find_parent_of_type(node, 'function_declaration')
                        break
                
                if not func_node:
                    # Try arrow function
                    query_str = '(variable_declaration (variable_declarator name: (identifier) @var_name))'
                    captures = self._execute_query(query_str, root, code_bytes)
                    
                    for (node, cap_name) in captures:
                        if cap_name == 'var_name' and self._get_node_text(node, code_bytes) == function_name:
                            var_node = node.parent
                            for child in var_node.children:
                                if child.type == 'arrow_function':
                                    func_node = child
                                    break
                            break
                
                if not func_node:
                    return []
                    
                params_node = None
                for child in func_node.children:
                    if child.type == 'formal_parameters':
                        params_node = child
                        break
                        
            if not params_node:
                return []
                
            parameters = []
            for param_node in params_node.children:
                if param_node.type == 'identifier':
                    param_name = self._get_node_text(param_node, code_bytes)
                    parameters.append({'name': param_name})
                    
                elif param_node.type == 'required_parameter':
                    param_name = None
                    param_type = None
                    
                    for child in param_node.children:
                        if child.type == 'identifier':
                            param_name = self._get_node_text(child, code_bytes)
                        elif child.type == 'type_annotation':
                            for type_child in child.children:
                                if type_child.type != ':':
                                    param_type = self._get_node_text(type_child, code_bytes)
                                    
                    if param_name:
                        if param_type:
                            parameters.append({'name': param_name, 'type': param_type})
                        else:
                            parameters.append({'name': param_name})
                            
                elif param_node.type == 'optional_parameter':
                    param_name = None
                    param_type = None
                    
                    for child in param_node.children:
                        if child.type == 'identifier':
                            param_name = self._get_node_text(child, code_bytes)
                        elif child.type == 'type_annotation':
                            for type_child in child.children:
                                if type_child.type != ':':
                                    param_type = self._get_node_text(type_child, code_bytes)
                                    
                    if param_name:
                        param_info = {'name': param_name, 'optional': True}
                        if param_type:
                            param_info['type'] = param_type
                        parameters.append(param_info)
                        
                elif param_node.type == 'default_parameter':
                    param_name = None
                    param_type = None
                    default_value = None
                    
                    for child in param_node.children:
                        if child.type == 'identifier':
                            param_name = self._get_node_text(child, code_bytes)
                        elif child.type == 'type_annotation':
                            for type_child in child.children:
                                if type_child.type != ':':
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
        except Exception as e:
            self.console.print(f"[yellow]Error in get_function_parameters: {e}[/yellow]")
            return []

    def get_function_return_info(self, code: str, function_name: str, class_name: Optional[str]=None) -> Dict[str, Any]:
        """
        Extract return type and return values from a function or method.

        Args:
            code: Source code as string
            function_name: Function or method name
            class_name: Class name if searching for method, None for standalone functions

        Returns:
            Dictionary with return_type and return_values
        """
        try:
            (root, code_bytes) = self._get_tree(code)
            function_node = None
            
            if class_name:
                query_str = '(method_definition name: (property_identifier) @method_name)'
                captures = self._execute_query(query_str, root, code_bytes)
                
                for (node, cap_name) in captures:
                    if cap_name == 'method_name' and self._get_node_text(node, code_bytes) == function_name:
                        if self._is_node_inside_class(node, class_name, code_bytes):
                            function_node = self.ast_handler.find_parent_of_type(node, 'method_definition')
                            break
            else:
                query_str = '(function_declaration name: (identifier) @func_name)'
                captures = self._execute_query(query_str, root, code_bytes)
                
                for (node, cap_name) in captures:
                    if cap_name == 'func_name' and self._get_node_text(node, code_bytes) == function_name:
                        function_node = self.ast_handler.find_parent_of_type(node, 'function_declaration')
                        break
                        
                if not function_node:
                    # Try arrow function
                    query_str = '(variable_declaration (variable_declarator name: (identifier) @var_name))'
                    captures = self._execute_query(query_str, root, code_bytes)
                    
                    for (node, cap_name) in captures:
                        if cap_name == 'var_name' and self._get_node_text(node, code_bytes) == function_name:
                            var_node = node.parent
                            for child in var_node.children:
                                if child.type == 'arrow_function':
                                    function_node = child
                                    break
                            break
                            
            if not function_node:
                return {'return_type': None, 'return_values': []}
                
            return_type = None
            for child in function_node.children:
                if child.type == 'return_type':
                    for type_child in child.children:
                        if type_child.type != ':':
                            return_type = self._get_node_text(type_child, code_bytes)
                            break
                            
            return_values = []

            def find_return_statements(node):
                if node.type == 'return_statement':
                    for child in node.children:
                        if child.type != 'return':
                            return_values.append(self._get_node_text(child, code_bytes))
                for child in node.children:
                    find_return_statements(child)
                    
            if function_node.type == 'arrow_function':
                body = None
                for child in function_node.children:
                    if child.type != 'formal_parameters' and child.type != '=>' and (child.type != 'return_type'):
                        body = child
                        break
                        
                if body and body.type != 'statement_block':
                    return_values.append(self._get_node_text(body, code_bytes))
                    
            find_return_statements(function_node)
            
            return {'return_type': return_type, 'return_values': return_values}
        except Exception as e:
            self.console.print(f"[yellow]Error in get_function_return_info: {e}[/yellow]")
            return {'return_type': None, 'return_values': []}

    def find_this_methods(self, code: str, function_name: str) -> List[Dict[str, Any]]:
        """
        Find methods defined as this.methodName = function() within a constructor function.
        Common pattern in AngularJS services.

        Args:
        code: Source code as string
        function_name: Name of the parent function/service

        Returns:
        List of dictionaries with method information
        """
        result = []
        
        try:
            (start_line, end_line) = self.find_function(code, function_name)
            if start_line == 0 or end_line == 0:
                (start_line, end_line) = self.find_variable_function(code, function_name)
                if start_line == 0 or end_line == 0:
                    return result
                    
            lines = code.splitlines()
            function_code = '\n'.join(lines[start_line - 1:end_line])
            
            # Find this.method = function() patterns
            this_method_pattern = re.compile('this\\.(\\w+)\\s*=\\s*function\\s*\\(([^{]*)\\)\\s*{', re.DOTALL)
            for match in this_method_pattern.finditer(function_code):
                method_name = match.group(1)
                params = match.group(2).strip()
                start_pos = match.start()
                line_count = function_code[:start_pos].count('\n')
                method_start_line = start_line + line_count
                
                open_pos = function_code.find('{', match.end())
                if open_pos == -1:
                    continue
                    
                brace_count = 1
                end_pos = open_pos + 1
                
                while brace_count > 0 and end_pos < len(function_code):
                    if function_code[end_pos] == '{':
                        brace_count += 1
                    elif function_code[end_pos] == '}':
                        brace_count -= 1
                    end_pos += 1
                    
                if brace_count > 0:
                    continue
                    
                method_content = function_code[match.start():end_pos]
                method_end_line = method_start_line + method_content.count('\n')
                
                if any((m['name'] == method_name for m in result)):
                    continue
                    
                result.append({
                    'name': method_name,
                    'params': params,
                    'start_line': method_start_line,
                    'end_line': method_end_line,
                    'content': method_content
                })
                
            # Find this.method = () => patterns
            arrow_method_pattern = re.compile('this\\.(\\w+)\\s*=\\s*\\(([^)]*)\\)\\s*=>', re.DOTALL)
            for match in arrow_method_pattern.finditer(function_code):
                method_name = match.group(1)
                params = match.group(2).strip()
                
                if any((m['name'] == method_name for m in result)):
                    continue
                    
                start_pos = match.start()
                line_count = function_code[:start_pos].count('\n')
                method_start_line = start_line + line_count
                arrow_pos = function_code.find('=>', match.end())
                
                if arrow_pos == -1:
                    continue
                    
                block_start = function_code.find('{', arrow_pos)
                if block_start != -1 and (not re.search('[;\\n]', function_code[arrow_pos:block_start])):
                    brace_count = 1
                    end_pos = block_start + 1
                    
                    while brace_count > 0 and end_pos < len(function_code):
                        if function_code[end_pos] == '{':
                            brace_count += 1
                        elif function_code[end_pos] == '}':
                            brace_count -= 1
                        end_pos += 1
                        
                    if brace_count > 0:
                        continue
                else:
                    end_pos = function_code.find(';', arrow_pos)
                    if end_pos == -1:
                        newline_pos = function_code.find('\n', arrow_pos)
                        if newline_pos == -1:
                            end_pos = len(function_code)
                        else:
                            end_pos = newline_pos
                            
                method_content = function_code[start_pos:end_pos]
                method_end_line = method_start_line + method_content.count('\n')
                
                result.append({
                    'name': method_name,
                    'params': params,
                    'start_line': method_start_line,
                    'end_line': method_end_line,
                    'content': method_content
                })
                
            return result
        except Exception as e:
            self.console.print(f"[yellow]Error in find_this_methods: {e}[/yellow]")
            return []

    def find_interface(self, code: str, interface_name: str) -> Tuple[int, int]:
        """
        Find an interface definition in TypeScript code.

        Args:
        code: Source code as string
        interface_name: Name of the interface to find

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            # First, try regex-based approach
            interface_pattern = re.compile(f'(^|\\s)(export\\s+)?(interface\\s+{re.escape(interface_name)}\\b)')
            lines = code.splitlines()

            for (i, line) in enumerate(lines):
                match = interface_pattern.search(line)
                if match:
                    start_line = i + 1
                    brace_count = 0
                    has_opening_brace = False
                    end_line = start_line

                    # Find opening brace and count until closing brace
                    for j in range(i, len(lines)):
                        line = lines[j]

                        # Count braces in this line
                        opening_braces = line.count('{')
                        closing_braces = line.count('}')

                        # Update brace counter
                        brace_count += opening_braces - closing_braces

                        # Mark that we've seen the opening brace
                        if opening_braces > 0 and not has_opening_brace:
                            has_opening_brace = True

                        # If we've seen the opening brace and reached the matching closing brace
                        if has_opening_brace and brace_count == 0 and closing_braces > 0:
                            end_line = j + 1
                            break

                    return (start_line, end_line)

            # If regex fails, try using AST
            (root, code_bytes) = self._get_tree(code)
            query_str = '(interface_declaration name: (type_identifier) @interface_name)'
            captures = self._execute_query(query_str, root, code_bytes)

            for (node, cap_name) in captures:
                if cap_name == 'interface_name' and self._get_node_text(node, code_bytes) == interface_name:
                    interface_node = self.ast_handler.find_parent_of_type(node, 'interface_declaration')
                    if interface_node:
                        return (interface_node.start_point[0] + 1, interface_node.end_point[0] + 1)

            return (0, 0)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_interface: {e}[/yellow]")
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
        try:
            # First, try regex-based approach
            type_pattern = re.compile(f'(^|\\s)(export\\s+)?(type\\s+{re.escape(type_name)}\\b)')
            lines = code.splitlines()

            for (i, line) in enumerate(lines):
                match = type_pattern.search(line)
                if match:
                    start_line = i + 1
                    end_line = start_line

                    # Check if type alias is defined with braces (object type)
                    has_braces = '{' in line
                    brace_count = line.count('{') - line.count('}')

                    # Continue looking for the end of the type definition
                    j = i
                    while j < len(lines):
                        # If we're looking at a different line than the match line
                        if j != i:
                            current_line = lines[j]
                            if has_braces:
                                brace_count += current_line.count('{') - current_line.count('}')

                            # If we've found a semicolon and all braces are closed,
                            # or if all braces are closed and we had braces
                            if (';' in current_line and (not has_braces or brace_count <= 0)) or \
                                    (has_braces and brace_count <= 0 and '}' in current_line):
                                end_line = j + 1
                                break

                        j += 1
                        end_line = j  # Default to current line if we don't break

                    return (start_line, end_line)

            # If regex fails, try using AST
            (root, code_bytes) = self._get_tree(code)
            query_str = '(type_alias_declaration name: (type_identifier) @type_name)'
            captures = self._execute_query(query_str, root, code_bytes)

            for (node, cap_name) in captures:
                if cap_name == 'type_name' and self._get_node_text(node, code_bytes) == type_name:
                    type_node = self.ast_handler.find_parent_of_type(node, 'type_alias_declaration')
                    if type_node:
                        return (type_node.start_point[0] + 1, type_node.end_point[0] + 1)

            return (0, 0)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_type_alias: {e}[/yellow]")
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
        try:
            # Look for functional components or class components
            lines = code.splitlines()

            # Functional component pattern (arrow function)
            func_component_pattern = re.compile(f'(const|let|var)\\s+{re.escape(component_name)}\\s*=')
            for (i, line) in enumerate(lines):
                match = func_component_pattern.search(line)
                if match:
                    # JSX components start at the line with the declaration
                    # In our test cases, the line numbers are 1-indexed
                    start_line = i + 1

                    # Arrow function check
                    has_arrow = '=>' in line or any('=>' in lines[j] for j in range(i+1, min(i+3, len(lines))))
                    if not has_arrow and not 'React.FC' in line and not 'React.Component' in line:
                        continue

                    # Determine where component ends
                    end_line = start_line
                    brace_count = line.count('{') - line.count('}')
                    paren_count = line.count('(') - line.count(')')

                    for j in range(i+1, len(lines)):
                        current_line = lines[j]
                        brace_count += current_line.count('{') - current_line.count('}')
                        paren_count += current_line.count('(') - current_line.count(')')

                        # Check for semicolon at the end of expression
                        if ';' in current_line and brace_count <= 0 and paren_count <= 0:
                            end_line = j + 1
                            break

                        # If we reach balanced braces and parentheses
                        if brace_count <= 0 and paren_count <= 0 and ('}' in current_line or ')' in current_line):
                            end_line = j + 1
                            break

                        end_line = j + 1

                    return (start_line, end_line)

            # Typed functional component pattern
            typed_component_pattern = re.compile(f'(const|let|var)\\s+{re.escape(component_name)}\\s*:\\s*React')
            for (i, line) in enumerate(lines):
                match = typed_component_pattern.search(line)
                if match:
                    start_line = i + 1

                    # Find end of component
                    end_line = start_line
                    brace_count = line.count('{') - line.count('}')
                    paren_count = line.count('(') - line.count(')')

                    for j in range(i+1, len(lines)):
                        current_line = lines[j]
                        brace_count += current_line.count('{') - current_line.count('}')
                        paren_count += current_line.count('(') - current_line.count(')')

                        # Check for semicolon at the end of expression
                        if ';' in current_line and brace_count <= 0 and paren_count <= 0:
                            end_line = j + 1
                            break

                        # If we reach balanced braces and parentheses
                        if brace_count <= 0 and paren_count <= 0 and ('}' in current_line or ')' in current_line):
                            end_line = j + 1
                            break

                        end_line = j + 1

                    return (start_line, end_line)

            # Class component pattern
            class_component_pattern = re.compile(f'class\\s+{re.escape(component_name)}\\s+extends')
            for (i, line) in enumerate(lines):
                match = class_component_pattern.search(line)
                if match:
                    start_line = i + 1

                    # Find end of class
                    end_line = start_line
                    brace_count = line.count('{') - line.count('}')

                    for j in range(i+1, len(lines)):
                        current_line = lines[j]
                        brace_count += current_line.count('{') - current_line.count('}')

                        # If we reach balanced braces
                        if brace_count <= 0 and '}' in current_line:
                            end_line = j + 1
                            break

                        end_line = j + 1

                    return (start_line, end_line)

            return (0, 0)
        except Exception as e:
            self.console.print(f"[yellow]Error in find_jsx_component: {e}[/yellow]")
            return (0, 0)
