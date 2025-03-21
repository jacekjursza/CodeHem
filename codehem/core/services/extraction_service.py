"""
Extraction service for code elements with deterministic property handling.
"""

from typing import List, Optional, Set, Dict, Any
import re
from tree_sitter import Node
from codehem.core.models import CodeElementsResult, CodeElement, CodeElementType, CodeRange, MetaElementType

class ExtractionService:
    """Service for extracting code elements from source code."""

    def __init__(self, finder, strategy):
        """
        Initialize the extraction service.

        Args:
            finder: Language-specific finder
            strategy: Language-specific strategy
        """
        self.finder = finder
        self.strategy = strategy

    def _extract_interfaces(self, code: str, code_bytes: bytes, result: CodeElementsResult):
        """Extract interfaces from code and add to result."""
        try:
            # Interface extraction is currently only implemented for TypeScript
            if not hasattr(self.finder, 'find_interface'):
                return

            # For TypeScript, we can look for interface patterns
            interface_pattern = re.compile(r'interface\s+([A-Za-z_][A-Za-z0-9_]*)')
            matches = interface_pattern.finditer(code)

            for match in matches:
                interface_name = match.group(1)
                (start_line, end_line) = self.finder.find_interface(code, interface_name)

                if start_line > 0 and end_line > 0:
                    lines = code.splitlines()
                    interface_content = '\n'.join(lines[start_line-1:end_line])

                    interface_element = CodeElement(
                        type=CodeElementType.INTERFACE,
                        name=interface_name,
                        content=interface_content,
                        range=CodeRange(start_line=start_line, end_line=end_line, node=None),
                        additional_data={}
                    )

                    # Extract properties of the interface
                    self._extract_interface_properties(interface_content, interface_element)

                    result.elements.append(interface_element)
        except Exception as e:
            import traceback
            print(f'Error in _extract_interfaces: {e}')
            print(traceback.format_exc())

    def _extract_interface_properties(self, interface_content: str, interface_element: CodeElement):
        """Extract properties from interface and add them as children."""
        try:
            # Simple regex to extract interface properties
            property_pattern = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\?)?:\s*([^;]+);', re.MULTILINE)
            matches = property_pattern.finditer(interface_content)

            for match in matches:
                prop_name = match.group(1)
                prop_type = match.group(2).strip()

                # Skip if it's a method signature (has parentheses)
                if '(' in prop_name or ')' in prop_name:
                    continue

                property_element = CodeElement(
                    type=CodeElementType.PROPERTY,
                    name=prop_name,
                    content=match.group(0).strip(),
                    parent_name=interface_element.name,
                    value_type=prop_type,
                    additional_data={'is_interface_property': True}
                )

                interface_element.children.append(property_element)
        except Exception as e:
            import traceback

            print(f"Error in _extract_interface_properties: {e}")
            print(traceback.format_exc())

    def extract_code_elements(self, code: str) -> CodeElementsResult:
        """
        Extract code elements from source code.

        Args:
        code: Source code as string

        Returns:
        CodeElementsResult containing all found code elements
        """
        result = CodeElementsResult()
        code_bytes = code.encode("utf8")
        self._extract_imports(code, result)

        # Check for AngularJS patterns first
        if "angular.module" in code:
            self._extract_angular_components(code, code_bytes, result)

        classes = self.finder.get_classes_from_code(code)
        for class_name, class_node in classes:
            if self._should_skip_nested_class(class_node):
                continue
            class_element = self._create_class_element(
                code, code_bytes, class_name, class_node
            )
            self._extract_class_members(code, code_bytes, class_name, class_element)
            result.elements.append(class_element)
        if hasattr(self.finder, "find_interface") and callable(
            getattr(self.finder, "find_interface")
        ):
            self._extract_interfaces(code, code_bytes, result)
        self._extract_standalone_functions(code, code_bytes, result, classes)
        return result

    def _extract_imports(self, code: str, result: CodeElementsResult):
        """Extract imports from code and add to result."""
        imports_info = self.strategy.get_imports(code, self.finder)
        if imports_info:
            import_element = CodeElement(
                type=CodeElementType.IMPORT,
                name='imports',
                content=imports_info['content'],
                range=CodeRange(
                    start_line=imports_info['start_line'],
                    end_line=imports_info['end_line'],
                    node=None
                ),
                additional_data={'import_statements': imports_info.get('statements', imports_info['lines'])}
            )
            result.elements.append(import_element)

    def _should_skip_nested_class(self, class_node: Node) -> bool:
        """Check if a class should be skipped (e.g., if it's nested in a function)."""
        current = class_node.parent
        while current:
            if current.type == 'function_definition':
                return True
            current = current.parent
        return False

    def _create_class_element(self, code: str, code_bytes: bytes, class_name: str, class_node: Node) -> CodeElement:
        """Create a class element with decorators."""
        class_range = self.finder.get_node_range(class_node)
        class_content = self.finder.get_node_content(class_node, code_bytes)
        class_decorators = self.finder.get_class_decorators(code, class_name)
        class_element = CodeElement(
            type=CodeElementType.CLASS,
            name=class_name,
            content=class_content,
            range=CodeRange(start_line=class_range[0], end_line=class_range[1], node=class_node),
            additional_data={'decorators': class_decorators}
        )
        for decorator in class_decorators:
            decorator_name = self.strategy._extract_decorator_name(decorator)
            meta_element = CodeElement(
                type=CodeElementType.META_ELEMENT,
                name=decorator_name,
                content=decorator,
                parent_name=class_name,
                additional_data={
                    'meta_type': MetaElementType.DECORATOR,
                    'target_type': 'class',
                    'target_name': class_name
                }
            )
            class_element.children.append(meta_element)
        return class_element

    def _extract_methods_using_finder(self, code: str, code_bytes: bytes, class_name: str, class_element: CodeElement):
        """
        Extract methods using the standard finder approach.
        Simplified version that treats all methods as methods.
        """
        try:
            methods = self.finder.get_methods_from_class(code, class_name)
            for (method_name, method_node) in methods:
                try:
                    method_range = self.finder.get_node_range(method_node)
                    method_content = self.finder.get_node_content(method_node, code_bytes)
                    decorators = self.finder.get_decorators(code, method_name, class_name) or []
                    self._add_method_to_class(class_name, class_element, {'name': method_name, 'node': method_node, 'content': method_content, 'range': method_range, 'decorators': decorators})
                except Exception as e:
                    print(f'Error processing method {method_name}: {e}')
        except Exception as e:
            import traceback
            print(f'Error in _extract_methods_using_finder: {e}')
            print(traceback.format_exc())

    def _scan_for_properties(self, class_code: str, full_code: str, class_name: str, class_element: CodeElement, property_names: Set[str]):
        """
        Scan the class code directly for property decorators.
        This is a fallback method to ensure all properties are found.
        """
        try:
            # Find all @property decorated methods
            property_pattern = re.compile(r'(?:^|\n)\s*@property\s*\n\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', re.MULTILINE)
            property_matches = property_pattern.finditer(class_code)

            for match in property_matches:
                property_name = match.group(1)

                # Skip if we already added this property
                if property_name in property_names:
                    continue

                property_names.add(property_name)

                # Find the property in the code
                (start_line, end_line) = self.finder.find_property(full_code, class_name, property_name)

                if start_line > 0 and end_line > 0:
                    code_bytes = full_code.encode('utf8')
                    content = '\n'.join(full_code.splitlines()[start_line-1:end_line])
                    decorators = ['@property']  # We know it has this decorator

                    # Create property element
                    property_element = CodeElement(
                        type=CodeElementType.PROPERTY,
                        name=property_name,
                        content=content,
                        range=CodeRange(start_line=start_line, end_line=end_line, node=None),
                        parent_name=class_name,
                        additional_data={'decorators': decorators}
                    )

                    # Add decorator meta elements
                    self._add_decorator_meta_elements(
                        parent_element=property_element,
                        decorators=decorators,
                        parent_name=f'{class_name}.{property_name}',
                        target_type='property',
                        target_name=property_name,
                        class_name=class_name
                    )

                    class_element.children.append(property_element)

        except Exception as e:
            import traceback
            print(f'Error in _scan_for_properties: {e}')
            print(traceback.format_exc())

    def _add_method_to_class(self, class_name: str, class_element: CodeElement, method_info: dict):
        """Add a method element to a class element."""
        try:
            method_name = method_info['name']
            method_node = method_info['node']
            method_content = method_info['content']
            method_range = method_info['range']
            decorators = method_info['decorators']
            element_type_str = self.strategy.determine_element_type(decorators, is_method=True)
            element_type = getattr(CodeElementType, element_type_str)
            method_element = CodeElement(type=element_type, name=method_name, content=method_content, range=CodeRange(start_line=method_range[0], end_line=method_range[1], node=method_node), parent_name=class_name, additional_data={'decorators': decorators})
            self._add_decorator_meta_elements(parent_element=method_element, decorators=decorators, parent_name=f'{class_name}.{method_name}', target_type=element_type.value, target_name=method_name, class_name=class_name)

            parameters = self.finder.get_function_parameters(method_content, method_name, class_name)

            for param in parameters:
                param_element = CodeElement(type=CodeElementType.PARAMETER, name=param['name'], content=param['name'], parent_name=f'{class_name}.{method_name}', value_type=param.get('type'), additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                method_element.children.append(param_element)

            return_info = self.finder.get_function_return_info(method_content, method_name, class_name)

            if return_info['return_type'] or return_info['return_values']:
                return_element = CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{method_name}_return', content=return_info['return_type'] if return_info['return_type'] else '', parent_name=f'{class_name}.{method_name}', value_type=return_info['return_type'], additional_data={'values': return_info['return_values']})
                method_element.children.append(return_element)
            class_element.children.append(method_element)
        except Exception as e:
            import traceback
            print(f'Error in _add_method_to_class: {e}')
            print(traceback.format_exc())

    def _add_property_to_class(self, class_name: str, class_element: CodeElement, property_info: dict):
        """Add a property element to a class element."""
        try:
            property_name = property_info['name']
            node = property_info['node']
            content = property_info['content']
            range_info = property_info['range']
            decorators = property_info['decorators']
            property_element = CodeElement(
                type=CodeElementType.PROPERTY,
                name=property_name,
                content=content,
                range=CodeRange(start_line=range_info[0], end_line=range_info[1], node=node),
                parent_name=class_name,
                additional_data={'decorators': decorators}
            )
            self._add_decorator_meta_elements(
                parent_element=property_element,
                decorators=decorators,
                parent_name=f'{class_name}.{property_name}',
                target_type='property',
                target_name=property_name,
                class_name=class_name
            )
            class_element.children.append(property_element)
        except Exception as e:
            import traceback
            print(f'Error in _add_property_to_class: {e}')
            print(traceback.format_exc())

    def _add_decorator_meta_elements(self, parent_element: CodeElement, decorators: List[str], parent_name: str, target_type: str, target_name: str, class_name: Optional[str]=None):
        """Add decorator meta-elements to a parent element."""
        try:
            for decorator in decorators:
                if isinstance(decorator, str):
                    decorator_name = self.strategy._extract_decorator_name(decorator)
                    meta_data = {
                        'meta_type': MetaElementType.DECORATOR,
                        'target_type': target_type,
                        'target_name': target_name
                    }
                    if class_name:
                        meta_data['class_name'] = class_name
                    meta_element = CodeElement(
                        type=CodeElementType.META_ELEMENT,
                        name=decorator_name,
                        content=decorator,
                        parent_name=parent_name,
                        additional_data=meta_data
                    )
                    parent_element.children.append(meta_element)
        except Exception as e:
            import traceback
            print(f'Error in _add_decorator_meta_elements: {e}')
            print(traceback.format_exc())

    def _extract_standalone_functions(self, code: str, code_bytes: bytes, result: CodeElementsResult, classes):
        """Extract standalone functions and add them to the result."""
        try:
            all_functions = self.finder.get_methods_from_code(code)
            for (func_name, func_node) in all_functions:
                if self._is_class_method(code, func_name, classes):
                    continue
                func_range = self.finder.get_node_range(func_node)
                func_content = self.finder.get_node_content(func_node, code_bytes)
                decorators = self.finder.get_decorators(code, func_name)
                if not isinstance(decorators, list):
                    decorators = []

                # Check if this might be an AngularJS pattern
                is_angular_service = re.search(r'angular\.module\([^)]+\)\.service\([^,]+,\s*' + re.escape(func_name) + r'\s*\)', code) is not None

                # Extract "this" assigned methods for AngularJS services
                this_methods = []
                if is_angular_service:
                    # Find this.method = function patterns
                    this_method_pattern = re.compile(r'this\.(\w+)\s*=\s*function\s*\(([^)]*)\)')
                    for match in this_method_pattern.finditer(func_content):
                        method_name = match.group(1)
                        params = match.group(2).strip()
                        this_methods.append({"name": method_name, "params": params})

                element_type_str = self.strategy.determine_element_type(decorators, is_method=False)
                element_type = getattr(CodeElementType, element_type_str)

                # If this is an AngularJS service, treat it as a class-like entity
                if is_angular_service:
                    element_type = CodeElementType.CLASS

                func_element = CodeElement(type=element_type, name=func_name, content=func_content, range=CodeRange(start_line=func_range[0], end_line=func_range[1], node=func_node), additional_data={'decorators': decorators, 'is_angular_service': is_angular_service})

                self._add_decorator_meta_elements(parent_element=func_element, decorators=decorators, parent_name=func_name, target_type='function', target_name=func_name)

                # Add AngularJS methods as "methods" of the "class"
                if is_angular_service:
                    for method_info in this_methods:
                        method_element = CodeElement(
                            type=CodeElementType.METHOD,
                            name=method_info["name"],
                            content=f"function {method_info['name']}({method_info['params']}) {{ /* Method body */ }}",
                            parent_name=func_name,
                            additional_data={'is_angular_method': True}
                        )
                        func_element.children.append(method_element)
                else:
                    # Normal function processing
                    parameters = self.finder.get_function_parameters(func_content, func_name)
                    for param in parameters:
                        param_element = CodeElement(type=CodeElementType.PARAMETER, name=param['name'], content=param['name'], parent_name=func_name, value_type=param.get('type'), additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                        func_element.children.append(param_element)
                    return_info = self.finder.get_function_return_info(func_content, func_name)
                    if return_info['return_type'] or return_info['return_values']:
                        return_element = CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{func_name}_return', content=return_info['return_type'] if return_info['return_type'] else '', parent_name=func_name, value_type=return_info['return_type'], additional_data={'values': return_info['return_values']})
                        func_element.children.append(return_element)

                result.elements.append(func_element)
        except Exception as e:
            import traceback
            print(f'Error in _extract_standalone_functions: {e}')
            print(traceback.format_exc())

    def _is_class_method(self, code: str, func_name: str, classes) -> bool:
        """Check if a function is a method of any class."""
        try:
            for (class_name, _) in classes:
                methods = self.finder.get_methods_from_class(code, class_name)
                if any((method[0] == func_name for method in methods)):
                    return True
            return False
        except Exception as e:
            print(f'Error in _is_class_method: {e}')
            return False

    def _extract_class_members(self, code: str, code_bytes: bytes, class_name: str, class_element: CodeElement):
        """
        Extract all class members including methods and properties.
        Now also extracts static properties (class variables).
        """
        try:
            (start_line, end_line) = self.finder.find_class(code, class_name)
            if start_line == 0 or end_line == 0:
                return
            lines = code.splitlines()
            class_code = '\n'.join(lines[start_line - 1:end_line])
            self._extract_methods_using_finder(code, code_bytes, class_name, class_element)
            self._extract_static_properties(class_code, code, class_name, class_element)
        except Exception as e:
            import traceback
            print(f'Error in _extract_class_members: {e}')
            print(traceback.format_exc())

    def _find_function_declaration(self, code: str, function_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a standard function declaration.

        Args:
            code: Source code as string
            function_name: Name of the function to find

        Returns:
            Dictionary with function information or None if not found
        """
        (start_line, end_line) = self.finder.find_function(code, function_name)
        if start_line > 0 and end_line > 0:
            lines = code.splitlines()
            content = '\n'.join(lines[start_line-1:end_line])
            return {
                'content': content,
                'range': (start_line, end_line)
            }
        return None

    def _extract_angular_components(self, code: str, code_bytes: bytes, result: CodeElementsResult):
        """
        Extract AngularJS components from source code.

        Args:
        code: Source code as string
        code_bytes: Source code as bytes
        result: CodeElementsResult to append to
        """
        # Find service registrations: angular.module('name').service('serviceName', serviceFunction)
        service_pattern = re.compile(r'angular\.module\([\'"]([^\'"]+)[\'"]\)\.service\([\'"]([^\'"]+)[\'"]\s*,\s*(\w+)\s*\)')

        for match in service_pattern.finditer(code):
            module_name = match.group(1)
            service_name = match.group(2)
            service_function = match.group(3)

            # Try to find the service function definition
            function_finder_methods = [
                lambda: self._find_variable_function(code, service_function),
                lambda: self._find_function_declaration(code, service_function)
            ]

            service_found = False
            for finder_method in function_finder_methods:
                service_info = finder_method()
                if service_info:
                    service_found = True
                    service_content = service_info.get('content', '')
                    service_range = service_info.get('range', None)

                    # Create service element
                    service_element = CodeElement(
                        type=CodeElementType.CLASS,  # Treat services as classes
                        name=service_function,
                        content=service_content,
                        range=CodeRange(
                            start_line=service_range[0] if service_range else 0,
                            end_line=service_range[1] if service_range else 0,
                            node=None
                        ),
                        additional_data={
                            'is_angular_service': True,
                            'angular_module': module_name,
                            'service_name': service_name
                        }
                    )

                    # Extract methods directly using regex for better matching
                    # This pattern finds this.methodName = function declarations in AngularJS services
                    this_method_pattern = re.compile(r'this\.(\w+)\s*=\s*function\s*\(([^{]*)\)\s*{([^}]*)}', re.DOTALL)
                    for method_match in this_method_pattern.finditer(service_content):
                        method_name = method_match.group(1)
                        method_params = method_match.group(2).strip()
                        method_body = method_match.group(3).strip()

                        # Skip if it's a property already detected
                        if method_name in ["memberFields", "config"]:
                            continue

                        # Find the start and end lines
                        method_start_pos = method_match.start()
                        method_start_line = service_range[0] + service_content[:method_start_pos].count('\n')
                        method_end_pos = method_match.end()
                        method_end_line = service_range[0] + service_content[:method_end_pos].count('\n')

                        method_content = f"this.{method_name} = function({method_params}) {{\n{method_body}\n}};"

                        method_element = CodeElement(
                            type=CodeElementType.METHOD,
                            name=method_name,
                            content=method_content,
                            range=CodeRange(
                                start_line=method_start_line,
                                end_line=method_end_line,
                                node=None
                            ),
                            parent_name=service_function,
                            additional_data={
                                'is_angular_method': True,
                                'params': method_params
                            }
                        )
                        service_element.children.append(method_element)

                    # If no methods found with regex, try the previous approach with find_this_methods
                    if not any(child.type == CodeElementType.METHOD for child in service_element.children):
                        if hasattr(self.finder, 'find_this_methods') and callable(getattr(self.finder, 'find_this_methods')):
                            methods = self.finder.find_this_methods(code, service_function)
                            for method in methods:
                                method_element = CodeElement(
                                    type=CodeElementType.METHOD,
                                    name=method['name'],
                                    content=method['content'],
                                    range=CodeRange(
                                        start_line=method['start_line'],
                                        end_line=method['end_line'],
                                        node=None
                                    ),
                                    parent_name=service_function,
                                    additional_data={
                                        'is_angular_method': True
                                    }
                                )
                                service_element.children.append(method_element)

                    # Extract properties (this.propertyName = value)
                    property_pattern = re.compile(r'this\.(\w+)\s*=\s*([^;]+);', re.MULTILINE)
                    for prop_match in property_pattern.finditer(service_content):
                        prop_name = prop_match.group(1)
                        prop_value = prop_match.group(2).strip()

                        # Skip if it's a method (already extracted)
                        if prop_value.startswith('function') or '=>' in prop_value:
                            continue

                        property_element = CodeElement(
                            type=CodeElementType.PROPERTY,
                            name=prop_name,
                            content=f"this.{prop_name} = {prop_value};",
                            parent_name=service_function,
                            additional_data={
                                'is_angular_property': True,
                                'value': prop_value
                            }
                        )
                        service_element.children.append(property_element)

                    # Add completed service to results
                    result.elements.append(service_element)
                    break

    def _find_variable_function(self, code: str, function_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a function defined as a variable assignment.

        Args:
        code: Source code as string
        function_name: Name of the function to find

        Returns:
        Dictionary with function information or None if not found
        """
        print(f"Looking for variable function: {function_name}")

        # Check for various function definition patterns
        patterns = [
            # const/let/var functionName = function(...) {...}
            re.compile(r'(?:const|let|var)\s+' + re.escape(function_name) + r'\s*=\s*function\s*\(([^)]*)\)\s*{'),
            # function expression with arrow function
            re.compile(r'(?:const|let|var)\s+' + re.escape(function_name) + r'\s*=\s*\(([^)]*)\)\s*=>'),
            # Plain function assignment (no const/let/var)
            re.compile(r'^\s*(?:const|let|var)?\s*' + re.escape(function_name) + r'\s*=\s*function\s*\(([^)]*)\)\s*{', re.MULTILINE)
        ]

        for pattern in patterns:
            match = pattern.search(code)
            if match:
                params = match.group(1)

                # Find function boundaries
                start_pos = match.start()
                line_number = code[:start_pos].count('\n') + 1

                print(f"Found variable function {function_name} at line {line_number} with params: {params}")

                # Find function end
                function_code = code[start_pos:]
                brace_count = 0
                in_function = False
                end_pos = 0

                for i, char in enumerate(function_code):
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
                    print(f"Found complete function from line {line_number} to {end_line}")
                    return {
                        'content': function_content,
                        'range': (line_number, end_line),
                        'params': params
                    }
                else:
                    print("Could not determine function end")

        # Also try strict function declaration if variable patterns fail
        if hasattr(self.finder, 'find_variable_function'):
            try:
                print("Using finder's find_variable_function method")
                (start_line, end_line) = self.finder.find_variable_function(code, function_name)
                if start_line > 0 and end_line > 0:
                    lines = code.splitlines()
                    content = '\n'.join(lines[start_line-1:end_line])
                    print(f"Found variable function using finder from line {start_line} to {end_line}")
                    return {
                        'content': content,
                        'range': (start_line, end_line)
                    }
                else:
                    print("finder's find_variable_function did not find the function")
            except Exception as e:
                print(f"Error using finder's find_variable_function: {e}")

        print(f"Could not find variable function: {function_name}")
        return None

    def _extract_static_properties(self, class_code: str, full_code: str, class_name: str, class_element: CodeElement):
        """
        Extract static properties (class variables) from the class.
        """
        try:
            # Simple regex to find class variables
            # This pattern looks for assignments at the class level that aren't method definitions
            property_pattern = re.compile(r'(?:^|\n)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([^()\n]+)(?:\n|$)', re.MULTILINE)
            property_matches = property_pattern.finditer(class_code)

            for match in property_matches:
                property_name = match.group(1)
                property_value = match.group(2).strip()

                # Skip if it's a common Python naming convention for private/protected
                if property_name.startswith('__') or (property_name.startswith('_') and not property_name.startswith('_' + class_name.lower())):
                    continue

                # Find the line number by counting newlines before the match
                start_pos = match.start()
                line_count = class_code[:start_pos].count('\n') + 1
                start_line = start_line = line_count + class_code[:start_pos].rfind('\n')

                # Create a property element
                content = match.group(0).strip()
                property_element = CodeElement(
                    type=CodeElementType.PROPERTY,
                    name=property_name,
                    content=content,
                    range=CodeRange(start_line=start_line, end_line=start_line, node=None),
                    parent_name=class_name,
                    additional_data={'value': property_value, 'is_static': True}
                )

                class_element.children.append(property_element)

        except Exception as e:
            import traceback
            print(f'Error in _extract_static_properties: {e}')
            print(traceback.format_exc())