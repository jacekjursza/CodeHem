import re
from typing import Tuple, List, Optional, Dict, Any, Callable

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
        python_indicators = {
            "strong": [
                re.search("def\\s+\\w+\\s*\\([^)]*\\)\\s*:", code) is not None,
                re.search("class\\s+\\w+(\\s*\\([^)]*\\))?\\s*:", code) is not None,
                re.search("def\\s+\\w+\\s*\\([^)]*\\)\\s*:\\s*\\n\\s+", code)
                is not None,
                re.search("def\\s+\\w+\\s*\\(\\s*self", code) is not None,
            ],
            "medium": [
                re.search("^import\\s+\\w+", code, re.MULTILINE) is not None,
                re.search("^from\\s+[\\w.]+\\s+import", code, re.MULTILINE) is not None,
                re.search("@\\w+", code) is not None,
                re.search("def\\s+\\w+\\s*\\([^)]*\\)\\s*->\\s*\\w+", code) is not None,
            ],
            "weak": [
                re.search("\\n\\s+\\S", code) is not None,
                re.search("#.*$", code, re.MULTILINE) is not None,
                re.search(":\\s*\\w+(\\s*\\[\\w+\\])?\\s*=", code) is not None,
            ],
        }
        negative_indicators = [
            re.search("function\\s+\\w+\\s*\\([^)]*\\)\\s*{", code) is not None,
            code.count(";") > code.count("\n") / 2,
            re.search("(const|let|var)\\s+\\w+\\s*=", code) is not None,
            re.search("interface\\s+\\w+\\s*{", code) is not None,
            re.search("import\\s+{\\s*[^}]+\\s*}\\s+from", code) is not None,
        ]

        # Give more weight to Python comments
        has_python_comments = re.search("#.*$", code, re.MULTILINE) is not None

        confidence = 0
        confidence += sum(python_indicators["strong"]) * 3
        confidence += sum(python_indicators["medium"]) * 2
        confidence += sum(python_indicators["weak"]) * 1
        confidence -= sum(negative_indicators) * 4

        # Boost confidence if file contains Python comments
        if has_python_comments:
            confidence += 2

        confidence_threshold = 2
        if sum(python_indicators["strong"]) > 0 and sum(negative_indicators) == 0:
            return True
        return confidence >= confidence_threshold

    # --- Core Helper Methods ---

    def _execute_query(
        self, query_str: str, root_node: Node, code_bytes: bytes
    ) -> List[Tuple[Node, str]]:
        """
        Execute a tree-sitter query and process the captures.

        Args:
            query_str: Query string in tree-sitter format
            root_node: Root node to query against
            code_bytes: Source code as bytes

        Returns:
            List of processed captures (node, capture_name)
        """
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(
            root_node, lambda n: code_bytes[n.start_byte : n.end_byte].decode("utf8")
        )
        return self._process_captures(raw_captures)

    def _find_element_by_query(
        self, code: str, query_str: str, match_conditions: Dict[str, Any] = None
    ) -> Optional[Node]:
        """
        Find an element using a tree-sitter query with optional match conditions.

        Args:
            code: Source code
            query_str: Query string in tree-sitter format
            match_conditions: Dictionary of {capture_name: expected_value}

        Returns:
            Matching node or None if not found
        """
        root, code_bytes = self._get_tree(code)
        captures = self._execute_query(query_str, root, code_bytes)

        if not match_conditions:
            return captures[0][0] if captures else None

        capture_dict = {}
        for node, capture_name in captures:
            if capture_name not in capture_dict:
                capture_dict[capture_name] = []
            capture_dict[capture_name].append(
                (node, self._get_node_text(node, code_bytes))
            )

        # Check if all conditions are satisfied
        matched_nodes = {}
        for capture_name, expected_value in match_conditions.items():
            if capture_name not in capture_dict:
                return None

            for node, value in capture_dict[capture_name]:
                if value == expected_value:
                    matched_nodes[capture_name] = node
                    break

            if capture_name not in matched_nodes:
                return None

        # Return the parent node of our match
        for capture_name in match_conditions:
            node = matched_nodes[capture_name]
            parent_type = match_conditions.get("parent_type")

            current = node
            while current and (not parent_type or current.type != parent_type):
                current = current.parent

            if current:
                return current

        return None

    def _get_decorated_range(
        self, node: Node, code: str, include_extra: bool = False
    ) -> Tuple[int, int]:
        """
        Get the line range for a node, optionally including decorators.

        Args:
            node: The node to get the range for
            code: Source code string
            include_extra: Whether to include decorators

        Returns:
            Tuple of (start_line, end_line)
        """
        # Base range without decorators
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1

        if not include_extra:
            return start_line, end_line

        return self._adjust_range_for_decorators(start_line, end_line, node, code)

    def _adjust_range_for_decorators(
        self, start_line: int, end_line: int, node: Node, code: str
    ) -> Tuple[int, int]:
        """
        Adjust a line range to include decorators if present.

        Args:
            start_line: Starting line number (1-indexed)
            end_line: Ending line number
            node: The node to check for decorators
            code: Source code string

        Returns:
            Adjusted tuple of (start_line, end_line)
        """
        # Check if node is inside a decorated_definition
        if node.parent and node.parent.type == "decorated_definition":
            return node.parent.start_point[0] + 1, end_line

        # Look for decorators manually by scanning previous lines
        lines = code.splitlines()
        i = start_line - 2  # Start from the line before

        while i >= 0:
            if i < len(lines):
                line = lines[i].strip()
                if line.startswith("@"):
                    start_line = i + 1
                    i -= 1
                elif line and not line.startswith("#"):
                    break
                else:
                    i -= 1
            else:
                break

        return start_line, end_line

    def _get_element_range_with_content(
        self, element_start: int, code: str, content_check: Callable[[str], bool]
    ) -> Tuple[int, int]:
        """
        Find the end of an element based on content indentation.

        Args:
            element_start: Starting line number (1-indexed)
            code: Source code string
            content_check: Function to determine if a line is still part of the element

        Returns:
            Tuple of (start_line, end_line)
        """
        lines = code.splitlines()

        # Find element indentation level
        if element_start - 1 >= len(lines):
            return element_start, element_start

        base_indent = len(lines[element_start - 1]) - len(
            lines[element_start - 1].lstrip()
        )
        element_end = element_start

        # Scan for end of element
        for i in range(element_start, len(lines)):
            line = lines[i]
            if not line.strip() or line.strip().startswith("#"):
                element_end = i + 1
                continue

            # If indentation is less than or equal to base, we've reached the end
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent and not content_check(line):
                break

            element_end = i + 1

        return element_start, element_end

    def _filter_class_elements(
        self, nodes: List[Tuple[Node, str]], class_node: Node
    ) -> List[Tuple[Node, str]]:
        """
        Filter nodes to only those that are children of the given class node.

        Args:
            nodes: List of (node, capture_name) tuples
            class_node: Class node to filter by

        Returns:
            Filtered list of (node, capture_name) tuples
        """
        result = []
        for node, capture_name in nodes:
            current = node
            while current and current != class_node:
                current = current.parent

            if current == class_node:
                result.append((node, capture_name))

        return result

    # --- Public Methods ---

    def find_function(
        self, code: str, function_name: str, include_extra: bool = False
    ) -> Tuple[int, int]:
        """Find a standalone function in Python code.

        Args:
        code: Source code as string
        function_name: Name of the function to find
        include_extra: Whether to include decorators in the returned range

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        root, code_bytes = self._get_tree(code)
        query_str = """
        (
            function_definition
            name: (identifier) @func_name
        )
        """
        captures = self._execute_query(query_str, root, code_bytes)

        for node, cap_name in captures:
            if (
                cap_name == "func_name"
                and self._get_node_text(node, code_bytes) == function_name
            ):
                func_node = node
                while func_node is not None and func_node.type != "function_definition":
                    func_node = func_node.parent

                if func_node is not None:
                    parent = func_node.parent
                    if parent and parent.type == "class_definition":
                        continue  # Skip class methods

                    return self._get_decorated_range(func_node, code, include_extra)

        return (0, 0)

    def find_class(
        self, code: str, class_name: str, include_extra: bool = False
    ) -> Tuple[int, int]:
        """Find a class in Python code.

        Args:
        code: Source code as string
        class_name: Name of the class to find
        include_extra: Whether to include decorators in the returned range

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        root, code_bytes = self._get_tree(code)
        query_str = """
        (
            class_definition
            name: (identifier) @class_name
        )
        """
        captures = self._execute_query(query_str, root, code_bytes)

        for node, cap_name in captures:
            if (
                cap_name == "class_name"
                and self._get_node_text(node, code_bytes) == class_name
            ):
                class_node = node
                while class_node is not None and class_node.type != "class_definition":
                    class_node = class_node.parent

                if class_node is not None:
                    return self._get_decorated_range(class_node, code, include_extra)

        return (0, 0)

    def find_method(
        self, code: str, class_name: str, method_name: str, include_extra: bool = False
    ) -> Tuple[int, int]:
        """Find a method in a class.

        Args:
        code: Source code as string
        class_name: Name of the class containing the method
        method_name: Name of the method to find
        include_extra: Whether to include decorators in the returned range

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        methods = self.get_methods_from_class(code, class_name)
        for name, node in methods:
            if name == method_name:
                method_node = node
                return self._get_decorated_range(method_node, code, include_extra)

        return (0, 0)

    def find_imports_section(self, code: str) -> Tuple[int, int]:
        """Find the imports section in Python code.

        Args:
        code: Source code as string

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        root, code_bytes = self._get_tree(code)
        query_str = """
        (import_statement) @import
        (import_from_statement) @import
        """
        captures = self._execute_query(query_str, root, code_bytes)
        nodes = [node for node, _ in captures]

        if not nodes:
            return (0, 0)

        nodes.sort(key=lambda node: node.start_point[0])
        return (nodes[0].start_point[0] + 1, nodes[-1].end_point[0] + 1)

    def _find_property_elements(
        self, code: str, class_name: str, property_name: str
    ) -> Dict[str, Tuple[Node, Tuple[int, int]]]:
        """
        Find property getter and setter elements.

        Args:
            code: Source code string
            class_name: Name of the class
            property_name: Name of the property

        Returns:
            Dictionary with 'getter' and 'setter' keys mapping to (node, range) tuples
        """
        class_start, class_end = self.find_class(code, class_name)
        if class_start == 0:
            return {"getter": None, "setter": None}

        methods = self.get_methods_from_class(code, class_name)
        result = {"getter": None, "setter": None}

        # Look for property getter and setter with the given name
        for method_name, method_node in methods:
            if method_name != property_name:
                continue

            # Use the dedicated method to get decorators
            decorators = self._get_method_decorators(method_node, code)

            for decorator in decorators:
                # Get basic node range
                start_line = method_node.start_point[0] + 1
                end_line = method_node.end_point[0] + 1
                node_range = (start_line, end_line)

                # Check for property type
                if decorator == "@property":
                    result["getter"] = (method_node, node_range)
                elif decorator == f"@{property_name}.setter":
                    result["setter"] = (method_node, node_range)

        return result

    def _get_node_decorators(self, node: Node, code: str) -> List[str]:
        """
        Get all decorators for a given node (method or class).

        Args:
            node: The node to get decorators for
            code: Source code string

        Returns:
            List of decorator strings
        """
        decorators = []
        code_bytes = code.encode("utf8") if isinstance(code, str) else code

        # Check if node is part of a decorated_definition
        if node.parent and node.parent.type == "decorated_definition":
            for child in node.parent.children:
                if child.type == "decorator":
                    decorators.append(self._get_node_text(child, code_bytes))

        # Check direct decorators on the node
        for child in node.children:
            if child.type == "decorator":
                decorators.append(self._get_node_text(child, code_bytes))

        # Look for decorators in source code if none found yet
        if not decorators:
            lines = (
                code.splitlines()
                if isinstance(code, str)
                else code.decode("utf8").splitlines()
            )
            start_line = node.start_point[0] + 1
            i = start_line - 2

            while i >= 0:
                if i < len(lines) and lines[i].strip().startswith("@"):
                    decorators.append(lines[i].strip())
                    i -= 1
                elif (
                    i < len(lines)
                    and lines[i].strip()
                    and not lines[i].strip().startswith("#")
                ):
                    break
                else:
                    i -= 1

        return decorators

    def _get_method_decorators(self, method_node: Node, code: str) -> List[str]:
        """Get decorators for a method node (alias for _get_node_decorators)."""
        return self._get_node_decorators(method_node, code)

    def get_class_with_updated_property(
        self, code: str, class_name: str, property_name: str, new_property_code: str
    ) -> str:
        """Update a property in a class.

        Args:
        code: Source code as string
        class_name: Name of the class
        property_name: Name of the property to update
        new_property_code: New property code

        Returns:
        Updated class code
        """
        class_start, class_end = self.find_class(code, class_name)
        if class_start == 0 or class_end == 0:
            return code

        lines = code.splitlines()
        class_code = "\n".join(lines[class_start - 1 : class_end])

        property_elements = self._find_property_elements(
            code, class_name, property_name
        )
        getter = property_elements["getter"]
        setter = property_elements["setter"]

        if getter and setter:
            # Replace both getter and setter
            getter_range = getter[1]
            setter_range = setter[1]

            if getter_range[0] < setter_range[0]:
                start_line = getter_range[0]
                end_line = setter_range[1]
            else:
                start_line = setter_range[0]
                end_line = getter_range[1]

        elif getter:
            # Replace just the getter
            start_line, end_line = getter[1]

        elif setter:
            # Replace just the setter
            start_line, end_line = setter[1]

        else:
            # No existing property, add to end of class
            class_indent = self._get_indentation(lines[class_start - 1])
            method_indent = class_indent + "    "
            indented_property = []

            for line in new_property_code.splitlines():
                if line.strip():
                    indented_property.append(method_indent + line.strip())
                else:
                    indented_property.append("")

            new_property_text = "\n".join(indented_property)
            new_class_code = class_code.rstrip()

            if not new_class_code.endswith("\n"):
                new_class_code += "\n"

            new_class_code += "\n" + new_property_text + "\n"
            return new_class_code

        # Rebuild the class with the new property
        new_class_lines = []

        # Add lines before the property
        for i in range(class_start - 1, start_line - 1):
            new_class_lines.append(lines[i])

        # Add the new property code with proper indentation
        class_indent = self._get_indentation(lines[class_start - 1])
        method_indent = class_indent + "    "

        for property_line in new_property_code.splitlines():
            if property_line.strip():
                new_class_lines.append(method_indent + property_line.strip())
            else:
                new_class_lines.append("")

        # Add lines after the property
        for i in range(end_line, class_end):
            new_class_lines.append(lines[i])

        return "\n".join(new_class_lines)

    def _get_indentation(self, line: str) -> str:
        """Get the indentation from a line."""
        match = re.match("^(\\s*)", line)
        return match.group(1) if match else ""

    def find_property(
        self,
        code: str,
        class_name: str,
        property_name: str,
        include_extra: bool = False,
    ) -> Tuple[int, int]:
        """Find a property getter in a Python class.

        Args:
        code: Source code as string
        class_name: Name of the class containing the property
        property_name: Name of the property to find
        include_extra: Whether to include decorators in the returned range

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        property_elements = self._find_property_elements(
            code, class_name, property_name
        )
        getter = property_elements["getter"]

        if not getter:
            return (0, 0)

        method_node, (start_line, end_line) = getter

        if include_extra:
            start_line, end_line = self._adjust_range_for_decorators(
                start_line, end_line, method_node, code
            )

        return (start_line, end_line)

    def find_property_setter(
        self,
        code: str,
        class_name: str,
        property_name: str,
        include_extra: bool = False,
    ) -> Tuple[int, int]:
        """Find a property setter in a Python class.

        Args:
        code: Source code as string
        class_name: Name of the class containing the property
        property_name: Name of the property to find
        include_extra: Whether to include decorators in the returned range

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        property_elements = self._find_property_elements(
            code, class_name, property_name
        )
        setter = property_elements["setter"]

        if not setter:
            return (0, 0)

        method_node, (start_line, end_line) = setter

        if include_extra:
            start_line, end_line = self._adjust_range_for_decorators(
                start_line, end_line, method_node, code
            )

        return (start_line, end_line)

    def find_property_and_setter(
        self,
        code: str,
        class_name: str,
        property_name: str,
        include_extra: bool = False,
    ) -> Tuple[int, int]:
        """Find both a property getter and its setter in a Python class.

        Args:
        code: Source code as string
        class_name: Name of the class containing the property
        property_name: Name of the property to find
        include_extra: Whether to include decorators in the returned range

        Returns:
        Tuple of (start_line, end_line) covering both getter and setter, or (0, 0) if not found
        """
        getter_start, getter_end = self.find_property(
            code, class_name, property_name, include_extra
        )
        setter_start, setter_end = self.find_property_setter(
            code, class_name, property_name, include_extra
        )

        # Handle cases where one or both are not found
        if getter_start == 0 and setter_start == 0:
            return (0, 0)
        elif getter_start == 0:
            return (setter_start, setter_end)
        elif setter_start == 0:
            return (getter_start, getter_end)

        # Both found - return range covering both
        start = min(getter_start, setter_start)
        end = max(getter_end, setter_end)
        return (start, end)

    def find_properties_section(self, code: str, class_name: str) -> Tuple[int, int]:
        """Find the properties section in a class.

        Args:
        code: Source code as string
        class_name: Name of the class

        Returns:
        Tuple of (start_line, end_line) or (0, 0) if not found
        """
        root, code_bytes = self._get_tree(code)
        query_str = """
        (assignment
           left: (identifier) @prop
        )
        """
        captures = self._execute_query(query_str, root, code_bytes)
        property_nodes = []

        for node, _ in captures:
            curr = node
            inside_class = False

            while curr is not None:
                if curr.type == "class_definition":
                    class_name_node = curr.child_by_field_name("name")
                    if (
                        class_name_node
                        and self._get_node_text(class_name_node, code_bytes)
                        == class_name
                    ):
                        inside_class = True
                    break
                elif curr.type == "function_definition":
                    break
                curr = curr.parent

            if inside_class:
                property_nodes.append(node)

        if not property_nodes:
            return (0, 0)

        property_nodes.sort(key=lambda node: node.start_point[0])
        return (
            property_nodes[0].start_point[0] + 1,
            property_nodes[-1].end_point[0] + 1,
        )

    def get_classes_from_code(self, code: str) -> List[Tuple[str, Node]]:
        """Get all classes from Python code.

        Args:
        code: Source code as string

        Returns:
        List of tuples with (class_name, class_node)
        """
        root, code_bytes = self._get_tree(code)
        query_str = """
        (
            class_definition
            name: (identifier) @class_name
        ) @class
        """
        captures = self._execute_query(query_str, root, code_bytes)

        classes = []
        class_nodes = {}
        class_names = {}

        for node, cap_type in captures:
            if cap_type == "class":
                class_nodes[node.id] = node
            elif cap_type == "class_name":
                class_name = self._get_node_text(node, code_bytes)
                class_names[node.parent.id] = class_name

        for node_id, node in class_nodes.items():
            if node_id in class_names:
                classes.append((class_names[node_id], node))

        return classes

    def get_methods_from_code(self, code: str) -> List[Tuple[str, Node]]:
        """Get all methods from Python code.

        Args:
        code: Source code as string

        Returns:
        List of tuples with (method_name, method_node)
        """
        root, code_bytes = self._get_tree(code)
        query_str = """
        (
            function_definition
            name: (identifier) @func_name
        ) @function
        """
        captures = self._execute_query(query_str, root, code_bytes)

        methods = []
        func_nodes = {}
        func_names = {}

        for node, cap_type in captures:
            if cap_type == "function":
                func_nodes[node.id] = node
            elif cap_type == "func_name":
                func_name = self._get_node_text(node, code_bytes)
                func_names[node.parent.id] = func_name

        for node_id, node in func_nodes.items():
            if node_id in func_names:
                methods.append((func_names[node_id], node))

        return methods

    def get_methods_from_class(
        self, code: str, class_name: str
    ) -> List[Tuple[str, Node]]:
        """Get all methods from a Python class.

        Args:
        code: Source code as string
        class_name: Name of the class

        Returns:
        List of tuples with (method_name, method_node)
        """
        if not class_name:
            return []  # Return empty list if class_name is None

        root, code_bytes = self._get_tree(code)

        # Handle nested classes (Class1.Class2.method)
        if "." in class_name:
            class_parts = class_name.split(".")
            current_node = root

            for class_part in class_parts:
                query_str = f'''
                (
                    class_definition
                    name: (identifier) @class_name (#eq? @class_name "{class_part}")
                ) @class
                '''
                query = Query(PY_LANGUAGE, query_str)
                raw_captures = query.captures(
                    current_node,
                    lambda n: code_bytes[n.start_byte : n.end_byte].decode("utf8"),
                )
                captures = self._process_captures(raw_captures)
                class_node = None

                for node, cap_type in captures:
                    if (
                        cap_type == "class_name"
                        and self._get_node_text(node, code_bytes) == class_part
                    ):
                        class_node = node.parent
                        break

                if not class_node:
                    return []

                current_node = class_node

            query_str = """
            (
                function_definition
                name: (identifier) @method_name
            ) @method
            """
            captures = self._execute_query(query_str, current_node, code_bytes)

            methods = []
            method_nodes = {}
            method_names = {}

            for node, cap_type in captures:
                if cap_type == "method":
                    method_nodes[node.id] = node
                elif cap_type == "method_name":
                    method_name = self._get_node_text(node, code_bytes)
                    method_names[node.parent.id] = method_name

            for node_id, node in method_nodes.items():
                if node_id in method_names:
                    methods.append((method_names[node_id], node))

            return methods

        # Handle regular classes
        class_node = None
        classes = self.get_classes_from_code(code)
        for cls_name, node in classes:
            if cls_name == class_name:
                class_node = node
                break

        if not class_node:
            return []

        query_str = """
        (
            function_definition
            name: (identifier) @method_name
        ) @method
        """
        captures = self._execute_query(query_str, class_node, code_bytes)

        methods = []
        method_nodes = {}
        method_names = {}

        for node, cap_type in captures:
            if cap_type == "method":
                method_nodes[node.id] = node
            elif cap_type == "method_name":
                method_name = self._get_node_text(node, code_bytes)
                method_names[node.parent.id] = method_name

        for node_id, node in method_nodes.items():
            if node_id in method_names:
                methods.append((method_names[node_id], node))

        return methods

    def get_decorators(
        self, code: str, name: str, class_name: Optional[str] = None
    ) -> List[str]:
        """
        Get decorators for a function or method.

        Args:
        code: Source code as string
        name: Function or method name
        class_name: Class name if searching for method decorators, None for standalone functions

        Returns:
        List of decorator strings
        """
        node = self._find_callable_node(code, name, class_name)
        if not node:
            return []

        return self._get_node_decorators(node, code)

    def _find_callable_node(
        self, code: str, name: str, class_name: Optional[str] = None
    ) -> Optional[Node]:
        """
        Find a function or method node by name.

        Args:
            code: Source code as string
            name: Function or method name
            class_name: Optional class name to search within

        Returns:
            Function/method node or None if not found
        """
        if class_name:
            # Find method in class
            methods = self.get_methods_from_class(code, class_name)
            for method_name, node in methods:
                if method_name == name:
                    return node
        else:
            # Find standalone function
            root, code_bytes = self._get_tree(code)
            query_str = "(function_definition name: (identifier) @func_name)"
            captures = self._execute_query(query_str, root, code_bytes)

            for node, cap_name in captures:
                if (
                    cap_name == "func_name"
                    and self._get_node_text(node, code_bytes) == name
                ):
                    func_node = node
                    while (
                        func_node is not None
                        and func_node.type != "function_definition"
                    ):
                        func_node = func_node.parent

                    # Check if function is inside a class (skip if it is)
                    current = func_node
                    is_method = False
                    while current:
                        if current.type == "class_definition":
                            is_method = True
                            break
                        current = current.parent

                    if not is_method:
                        return func_node

        return None

    def get_class_decorators(self, code: str, class_name: str) -> List[str]:
        """
        Get decorators for a class.

        Args:
            code: Source code as string
            class_name: Class name

        Returns:
            List of decorator strings
        """
        classes = self.get_classes_from_code(code)
        class_node = None

        for cls_name, node in classes:
            if cls_name == class_name:
                class_node = node
                break

        if not class_node:
            return []

        return self._get_node_decorators(class_node, code)

    def has_class_method_indicator(self, method_node: Node, code_bytes: bytes) -> bool:
        """Check if a method has 'self' as its first parameter."""
        params_node = None

        for child in method_node.children:
            if child.type == "parameters":
                params_node = child
                break

        if not params_node:
            return False

        for child in params_node.children:
            if child.type == "identifier":
                param_name = self._get_node_text(child, code_bytes)
                return param_name == "self"

        return False

    def is_correct_syntax(self, plain_text: str) -> bool:
        """Check if Python code has correct syntax."""
        try:
            self._get_tree(plain_text)
            import ast

            ast.parse(plain_text)
            return True
        except Exception:
            return False

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
            root, code_bytes = self._get_tree(code)
            query_str = f'''
            (function_definition
              name: (identifier) @func_name (#eq? @func_name "{method_name}"))
            '''
            captures = self._execute_query(query_str, root, code_bytes)

            for node, cap_type in captures:
                if cap_type != "func_name":
                    continue

                func_node = node.parent
                if not func_node or func_node.type != "function_definition":
                    continue

                if not self.has_class_method_indicator(func_node, code_bytes):
                    continue

                current = func_node.parent
                while current and current.type != "class_definition":
                    current = current.parent

                if current and current.type == "class_definition":
                    class_name_node = current.child_by_field_name("name")
                    if class_name_node:
                        return self._get_node_text(class_name_node, code_bytes)

                    for child in current.children:
                        if child.type == "identifier":
                            return self._get_node_text(child, code_bytes)

            return None

        except Exception as e:
            console = Console()
            console.print(f"[yellow]Error in find_class_for_method: {e}[/yellow]")
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return None

    def content_looks_like_class_definition(self, content: str) -> bool:
        """Check if content looks like a class definition."""
        if not content or not content.strip():
            return False

        content_lines = content.strip().splitlines()
        if not content_lines:
            return False

        first_line = content_lines[0].strip()
        if first_line.startswith("class ") and (":" in first_line or "(" in first_line):
            return True

        return super().content_looks_like_class_definition(content)

    def find_parent_classes(self, code: str, class_name: str) -> List[str]:
        """
        Find parent classes for a given class.

        Args:
            code: Source code string
            class_name: Name of the class

        Returns:
            List of parent class names
        """
        root, code_bytes = self._get_tree(code)
        query_str = """
        (
            class_definition
            name: (identifier) @class_name
            superclasses: (argument_list) @parents
        )
        """
        captures = self._execute_query(query_str, root, code_bytes)

        class_nodes = {}
        class_names = {}
        parent_nodes = {}

        for node, cap_type in captures:
            if cap_type == "class_name":
                name = self._get_node_text(node, code_bytes)
                class_names[node.parent.id] = name
                class_nodes[node.parent.id] = node.parent
            elif cap_type == "parents":
                parent_nodes[node.parent.id] = node

        for node_id, name in class_names.items():
            if name == class_name and node_id in parent_nodes:
                parents_node = parent_nodes[node_id]
                parents = []

                for child in parents_node.children:
                    if child.type == "identifier":
                        parents.append(self._get_node_text(child, code_bytes))
                    elif child.type == "attribute":
                        parents.append(self._get_node_text(child, code_bytes))

                return parents

        return []

    def find_module_for_class(self, code: str, class_name: str) -> Optional[str]:
        """
        Find which module a class was imported from.

        Args:
            code: Source code string
            class_name: Name of the class

        Returns:
            Module name or None if not found
        """
        root, code_bytes = self._get_tree(code)

        # Check direct imports
        query_str = "(import_from_statement module_name: (_) @module name: (dotted_name) @imported_name)"
        captures = self._execute_query(query_str, root, code_bytes)

        modules = {}
        imported_names = {}

        for node, cap_type in captures:
            if cap_type == "module":
                module_name = self._get_node_text(node, code_bytes)
                modules[node.parent.id] = module_name
            elif cap_type == "imported_name":
                name = self._get_node_text(node, code_bytes)
                if name == class_name:
                    imported_names[node.parent.id] = name

        for node_id, name in imported_names.items():
            if node_id in modules:
                return modules[node_id]

        # Check aliased imports
        try:
            query_str = "(import_from_statement module_name: (_) @module aliased_import name: (dotted_name) @orig_name alias: (identifier) @alias_name)"
            captures = self._execute_query(query_str, root, code_bytes)

            modules = {}
            aliases = {}
            orig_names = {}

            for node, cap_type in captures:
                if cap_type == "module":
                    module_name = self._get_node_text(node, code_bytes)
                    modules[node.parent.id] = module_name
                elif cap_type == "alias_name":
                    alias = self._get_node_text(node, code_bytes)
                    if alias == class_name:
                        aliases[node.parent.id] = alias
                elif cap_type == "orig_name":
                    orig_name = self._get_node_text(node, code_bytes)
                    orig_names[node.parent.id] = orig_name

            for node_id, _ in aliases.items():
                if node_id in modules:
                    orig_name = orig_names.get(node_id, "")
                    if orig_name:
                        return f"{modules[node_id]}.{orig_name}"
                    else:
                        return modules[node_id]
        except Exception:
            pass

        # Use regex as fallback for aliased imports
        try:
            import re

            aliased_pattern = re.compile(
                "from\\s+([a-zA-Z0-9_.]+)\\s+import\\s+([a-zA-Z0-9_]+)\\s+as\\s+([a-zA-Z0-9_]+)"
            )

            for match in aliased_pattern.finditer(code):
                module, orig_class, alias = match.groups()
                if alias == class_name:
                    return f"{module}.{orig_class}"
        except Exception:
            pass

        # Check for module.Class usage pattern
        query_str = "(import_statement name: (_) @module)"
        captures = self._execute_query(query_str, root, code_bytes)

        for node, cap_type in captures:
            if cap_type == "module":
                module_name = self._get_node_text(node, code_bytes)
                if f"{module_name}.{class_name}".encode("utf8") in code_bytes:
                    return module_name

        # Check attribute access for potential module
        query_str = "(attribute object: (_) @module attribute: (identifier) @attr)"

        try:
            captures = self._execute_query(query_str, root, code_bytes)

            for node, cap_type in captures:
                if (
                    cap_type == "attr"
                    and self._get_node_text(node, code_bytes) == class_name
                ):
                    parent_node = node.parent.child_by_field_name("object")
                    if parent_node:
                        return self._get_node_text(parent_node, code_bytes)
        except Exception:
            pass

        return None

    def get_function_parameters(
        self, code: str, function_name: str, class_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract parameters from a function or method.

        Args:
        code: Source code as string
        function_name: Function or method name
        class_name: Class name if searching for method parameters, None for standalone functions

        Returns:
        List of parameter dictionaries with name, type (if available), and default value (if available)
        """
        # Find the function node using the helper method
        func_node = self._find_callable_node(code, function_name, class_name)
        if not func_node:
            return []

        # Get the code bytes for text extraction
        _, code_bytes = self._get_tree(code)

        # Find parameters node
        params_node = None
        for child in func_node.children:
            if child.type == "parameters":
                params_node = child
                break

        if not params_node:
            return []

        # Process parameters based on their type
        return self._extract_parameters_from_node(params_node, code_bytes)

    def _extract_parameters_from_node(
        self, params_node: Node, code_bytes: bytes
    ) -> List[Dict[str, Any]]:
        """
        Extract parameter information from a parameters node.

        Args:
            params_node: Node containing parameters
            code_bytes: Source code as bytes

        Returns:
            List of parameter dictionaries
        """
        parameters = []
        param_handlers = {
            "identifier": self._handle_simple_parameter,
            "typed_parameter": self._handle_typed_parameter,
            "default_parameter": self._handle_default_parameter,
            "typed_default_parameter": self._handle_typed_default_parameter,
        }

        for param_node in params_node.children:
            if param_node.type in param_handlers:
                param_info = param_handlers[param_node.type](param_node, code_bytes)
                if param_info:
                    parameters.append(param_info)

        return parameters

    def _handle_simple_parameter(
        self, node: Node, code_bytes: bytes
    ) -> Optional[Dict[str, str]]:
        """Handle a simple parameter (identifier only)."""
        param_name = self._get_node_text(node, code_bytes)
        if param_name in ("self", "cls"):
            return None
        return {"name": param_name}

    def _handle_typed_parameter(
        self, node: Node, code_bytes: bytes
    ) -> Optional[Dict[str, str]]:
        """Handle a typed parameter (name: type)."""
        param_name = None
        param_type = None

        for child in node.children:
            if child.type == "identifier":
                param_name = self._get_node_text(child, code_bytes)
            elif child.type == "type":
                param_type = self._get_node_text(child, code_bytes)

        if param_name in ("self", "cls"):
            return None

        return {"name": param_name, "type": param_type} if param_name else None

    def _handle_default_parameter(
        self, node: Node, code_bytes: bytes
    ) -> Optional[Dict[str, str]]:
        """Handle a parameter with default value (name=default)."""
        param_name = None
        default_value = None

        for child in node.children:
            if child.type == "identifier":
                param_name = self._get_node_text(child, code_bytes)
            elif child.type not in ("=", "type"):
                default_value = self._get_node_text(child, code_bytes)

        if param_name in ("self", "cls"):
            return None

        return {"name": param_name, "default": default_value} if param_name else None

    def _handle_typed_default_parameter(
        self, node: Node, code_bytes: bytes
    ) -> Optional[Dict[str, str]]:
        """Handle a typed parameter with default value (name: type = default)."""
        param_name = None
        param_type = None
        default_value = None

        for child in node.children:
            if child.type == "identifier":
                param_name = self._get_node_text(child, code_bytes)
            elif child.type == "type":
                param_type = self._get_node_text(child, code_bytes)
            elif child.type not in ("=", "type", "identifier"):
                default_value = self._get_node_text(child, code_bytes)

        if param_name in ("self", "cls"):
            return None

        if param_name:
            result = {"name": param_name}
            if param_type:
                result["type"] = param_type
            if default_value:
                result["default"] = default_value
            return result

        return None

    def get_function_return_info(
        self, code: str, function_name: str, class_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract return type and return values from a function or method.

        Args:
        code: Source code as string
        function_name: Function or method name
        class_name: Class name if searching for method, None for standalone functions

        Returns:
        Dictionary with return_type and return_values
        """
        # Find the function node using the helper method
        func_node = self._find_callable_node(code, function_name, class_name)
        if not func_node:
            return {"return_type": None, "return_values": []}

        # Get the code bytes for text extraction
        _, code_bytes = self._get_tree(code)

        # Extract return type and return values
        return_type = self._extract_return_type(func_node, code_bytes)
        return_values = self._extract_return_values(func_node, code_bytes)

        return {"return_type": return_type, "return_values": return_values}

    def _extract_return_type(self, func_node: Node, code_bytes: bytes) -> Optional[str]:
        """
        Extract the return type annotation from a function node.

        Args:
            func_node: Function or method node
            code_bytes: Source code as bytes

        Returns:
            Return type string or None if not found
        """
        for i, child in enumerate(func_node.children):
            if child.type == '->':
                # The type node should be the next child after '->'
                if i + 1 < len(func_node.children) and func_node.children[i + 1].type == 'type':
                    type_node = func_node.children[i + 1]
                    return self._get_node_text(type_node, code_bytes)

        return None

    def _extract_return_values(self, func_node: Node, code_bytes: bytes) -> List[str]:
        """
        Extract return values from return statements in a function.

        Args:
            func_node: Function or method node
            code_bytes: Source code as bytes

        Returns:
            List of return value strings
        """
        return_values = []

        def find_return_statements(node):
            if node.type == 'return_statement':
                for child in node.children:
                    if child.type != 'return':
                        return_val = self._get_node_text(child, code_bytes)
                        return_values.append(return_val)

            for child in node.children:
                find_return_statements(child)

        find_return_statements(func_node)
        return return_values