"""
Python-specific extraction service implementation.
"""
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from tree_sitter import Node
from ...engine.base_extraction_service import BaseExtractionService
from ...models import CodeElementsResult, CodeElement, CodeElementType, CodeRange
from .template import TEMPLATES, ADDITIONAL_QUERIES

class PythonExtractionService(BaseExtractionService):
    """
    Python-specific implementation of the extraction service.
    """

    def __init__(self, analyzer, strategy):
        """
        Initialize the extraction service.
        
        Args:
            analyzer: Python analyzer
            strategy: Used for backward compatibility, now replaced by analyzer
        """
        super().__init__(analyzer, strategy)
        self.analyzer = analyzer

    def extract_code_elements(self, code: str) -> CodeElementsResult:
        """
        Extract code elements from source code.
        
        Args:
            code: Source code as string
            
        Returns:
            CodeElementsResult containing extracted elements
        """
        result = CodeElementsResult()
        code_bytes = code.encode('utf8')
        self.extract_imports(code, result)
        self.extract_classes(code, code_bytes, result)
        self.extract_functions(code, code_bytes, result)
        return result

    def extract_imports(self, code: str, result: CodeElementsResult) -> None:
        """
        Extract imports from code and add to result.
        
        Args:
            code: Source code as string
            result: CodeElementsResult to add imports to
        """
        imports_info = self.analyzer.get_imports(code)
        if imports_info:
            import_element = CodeElement(type=CodeElementType.IMPORT, name='imports', content=imports_info['content'], range=CodeRange(start_line=imports_info['start_line'], end_line=imports_info['end_line'], node=None), additional_data={'import_statements': imports_info.get('statements', imports_info.get('lines', []))})
            result.elements.append(import_element)

    def extract_classes(self, code: str, code_bytes: bytes, result: CodeElementsResult) -> None:
        """
        Extract classes from code and add to result.

        Args:
            code: Source code as string
            code_bytes: Source code as bytes
            result: CodeElementsResult to add classes to
        """
        try:
            (root, _) = self.analyzer.ast_handler.parse(code)
            class_query = TEMPLATES[CodeElementType.CLASS.value]['find_all']
            class_results = self.analyzer.ast_handler.execute_query(class_query, root, code_bytes)
            
            # Extract decorated classes
            decorated_class_query = ADDITIONAL_QUERIES['decorated_class'].format(class_name="")
            decorated_results = self.analyzer.ast_handler.execute_query(decorated_class_query, root, code_bytes)
            
            for (node, capture_name) in class_results:
                if capture_name == 'class_name':
                    class_name = self.analyzer.get_node_content(node, code_bytes)
                    class_node = self.analyzer.ast_handler.find_parent_of_type(node, 'class_definition')
                    if class_node:
                        (start_line, end_line) = self.analyzer.get_node_range(class_node)
                        class_content = self.analyzer.get_node_content(class_node, code_bytes)
                        class_decorators = self.analyzer.get_class_decorators(code, class_name)
                        class_element = CodeElement(type=CodeElementType.CLASS, name=class_name, content=class_content, range=CodeRange(start_line=start_line, end_line=end_line, node=class_node), additional_data={'decorators': class_decorators})
                        for decorator in class_decorators:
                            decorator_name = self._extract_decorator_name(decorator)
                            meta_element = CodeElement(type=CodeElementType.DECORATOR, name=decorator_name, content=decorator, parent_name=class_name, additional_data={'target_type': 'class', 'target_name': class_name})
                            class_element.children.append(meta_element)
                        self._extract_class_members(code, code_bytes, class_name, class_element)
                        result.elements.append(class_element)
            
            for (node, capture_name) in decorated_results:
                if capture_name == 'class_name':
                    class_name = self.analyzer.get_node_content(node, code_bytes)
                    decorated_def_node = self.analyzer.ast_handler.find_parent_of_type(node, 'decorated_definition')
                    if decorated_def_node:
                        (start_line, end_line) = self.analyzer.get_node_range(decorated_def_node)
                        class_content = self.analyzer.get_node_content(decorated_def_node, code_bytes)
                        decorator_nodes = []
                        for child_idx in range(decorated_def_node.named_child_count):
                            child = decorated_def_node.named_child(child_idx)
                            if child.type == 'decorator':
                                decorator_nodes.append(child)
                        class_decorators = [self.analyzer.get_node_content(node, code_bytes) for node in decorator_nodes]
                        class_element = CodeElement(type=CodeElementType.CLASS, name=class_name, content=class_content, range=CodeRange(start_line=start_line, end_line=end_line, node=decorated_def_node), additional_data={'decorators': class_decorators})
                        for decorator in class_decorators:
                            decorator_name = self._extract_decorator_name(decorator)
                            meta_element = CodeElement(type=CodeElementType.DECORATOR, name=decorator_name, content=decorator, parent_name=class_name, additional_data={'target_type': 'class', 'target_name': class_name})
                            class_element.children.append(meta_element)
                        self._extract_class_members(code, code_bytes, class_name, class_element)
                        result.elements.append(class_element)
        except Exception as e:
            class_pattern = re.compile('class\\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)
            for match in class_pattern.finditer(code):
                class_name = match.group(1)
                (start_line, end_line) = self.finder.find_element(code, CodeElementType.CLASS.value, class_name)
                if start_line <= 0 or end_line <= 0:
                    continue
                lines = code.splitlines()
                class_content = '\n'.join(lines[start_line - 1:end_line])
                class_element = self._create_class_element(code, code_bytes, class_name, start_line, end_line, class_content)
                self._extract_class_members(code, code_bytes, class_name, class_element)
                result.elements.append(class_element)

    def extract_functions(self, code: str, code_bytes: bytes, result: CodeElementsResult) -> None:
        """
        Extract standalone functions from code and add to result.

        Args:
            code: Source code as string
            code_bytes: Source code as bytes
            result: CodeElementsResult to add functions to
        """
        try:
            (root, _) = self.analyzer.ast_handler.parse(code)
            function_query = TEMPLATES[CodeElementType.FUNCTION.value]['find_all']
            function_results = self.analyzer.ast_handler.execute_query(function_query, root, code_bytes)
            
            decorated_function_query = ADDITIONAL_QUERIES['decorated_method'].format(method_name="")
            decorated_results = self.analyzer.ast_handler.execute_query(decorated_function_query, root, code_bytes)
            
            classes = self._get_class_names(code)
            for (node, capture_name) in function_results:
                if capture_name == 'func_name':
                    func_name = self.analyzer.get_node_content(node, code_bytes)
                    if self._is_class_method(code, func_name, classes):
                        continue
                    function_node = self.analyzer.ast_handler.find_parent_of_type(node, 'function_definition')
                    if function_node:
                        (start_line, end_line) = self.analyzer.get_node_range(function_node)
                        func_content = self.analyzer.get_node_content(function_node, code_bytes)
                        decorators = self.finder.get_decorators(code, func_name) or []
                        element_type_str = self.strategy.determine_element_type(decorators, is_method=False)
                        element_type = getattr(CodeElementType, element_type_str.upper())
                        func_element = CodeElement(type=element_type, name=func_name, content=func_content, range=CodeRange(start_line=start_line, end_line=end_line, node=function_node), additional_data={'decorators': decorators})
                        self._add_decorator_meta_elements(parent_element=func_element, decorators=decorators, parent_name=func_name, target_type='function', target_name=func_name)
                        parameters = self.finder.get_function_parameters(func_content, func_name)
                        for param in parameters:
                            param_element = CodeElement(type=CodeElementType.PARAMETER, name=param['name'], content=param['name'], parent_name=func_name, value_type=param.get('type'), additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                            func_element.children.append(param_element)
                        return_info = self.finder.get_function_return_info(func_content, func_name)
                        if return_info['return_type'] or return_info['return_values']:
                            return_element = CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{func_name}_return', content=return_info['return_type'] if return_info['return_type'] else '', parent_name=func_name, value_type=return_info['return_type'], additional_data={'values': return_info['return_values']})
                            func_element.children.append(return_element)
                        result.elements.append(func_element)
            
            for (node, capture_name) in decorated_results:
                if capture_name == 'method_name':
                    func_name = self.analyzer.get_node_content(node, code_bytes)
                    if self._is_class_method(code, func_name, classes):
                        continue
                    decorated_def_node = self.analyzer.ast_handler.find_parent_of_type(node, 'decorated_definition')
                    if decorated_def_node:
                        (start_line, end_line) = self.analyzer.get_node_range(decorated_def_node)
                        func_content = self.analyzer.get_node_content(decorated_def_node, code_bytes)
                        decorator_nodes = []
                        for child_idx in range(decorated_def_node.named_child_count):
                            child = decorated_def_node.named_child(child_idx)
                            if child.type == 'decorator':
                                decorator_nodes.append(child)
                        decorators = [self.analyzer.get_node_content(node, code_bytes) for node in decorator_nodes]
                        element_type_str = self.strategy.determine_element_type(decorators, is_method=False)
                        element_type = getattr(CodeElementType, element_type_str.upper())
                        func_element = CodeElement(type=element_type, name=func_name, content=func_content, range=CodeRange(start_line=start_line, end_line=end_line, node=decorated_def_node), additional_data={'decorators': decorators})
                        self._add_decorator_meta_elements(parent_element=func_element, decorators=decorators, parent_name=func_name, target_type='function', target_name=func_name)
                        function_node = None
                        for child_idx in range(decorated_def_node.named_child_count):
                            child = decorated_def_node.named_child(child_idx)
                            if child.type == 'function_definition':
                                function_node = child
                                break
                        if function_node:
                            function_content = self.analyzer.get_node_content(function_node, code_bytes)
                            parameters = self.finder.get_function_parameters(function_content, func_name)
                            for param in parameters:
                                param_element = CodeElement(type=CodeElementType.PARAMETER, name=param['name'], content=param['name'], parent_name=func_name, value_type=param.get('type'), additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                                func_element.children.append(param_element)
                            return_info = self.finder.get_function_return_info(function_content, func_name)
                            if return_info['return_type'] or return_info['return_values']:
                                return_element = CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{func_name}_return', content=return_info['return_type'] if return_info['return_type'] else '', parent_name=func_name, value_type=return_info['return_type'], additional_data={'values': return_info['return_values']})
                                func_element.children.append(return_element)
                        result.elements.append(func_element)
        except Exception as e:
            function_pattern = re.compile('def\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(', re.MULTILINE)
            classes = self._get_class_names(code)
            for match in function_pattern.finditer(code):
                func_name = match.group(1)
                if self._is_class_method(code, func_name, classes):
                    continue
                (start_line, end_line) = self.finder.find_element(code, CodeElementType.FUNCTION.value, func_name)
                if start_line <= 0 or end_line <= 0:
                    continue
                lines = code.splitlines()
                func_content = '\n'.join(lines[start_line - 1:end_line])
                decorators = self.finder.get_decorators(code, func_name) or []
                element_type_str = self.strategy.determine_element_type(decorators, is_method=False)
                element_type = getattr(CodeElementType, element_type_str.upper())
                func_element = CodeElement(type=element_type, name=func_name, content=func_content, range=CodeRange(start_line=start_line, end_line=end_line, node=None), additional_data={'decorators': decorators})
                self._add_decorator_meta_elements(parent_element=func_element, decorators=decorators, parent_name=func_name, target_type='function', target_name=func_name)
                parameters = self.finder.get_function_parameters(func_content, func_name)
                for param in parameters:
                    param_element = CodeElement(type=CodeElementType.PARAMETER, name=param['name'], content=param['name'], parent_name=func_name, value_type=param.get('type'), additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                    func_element.children.append(param_element)
                return_info = self.finder.get_function_return_info(func_content, func_name)
                if return_info['return_type'] or return_info['return_values']:
                    return_element = CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{func_name}_return', content=return_info['return_type'] if return_info['return_type'] else '', parent_name=func_name, value_type=return_info['return_type'], additional_data={'values': return_info['return_values']})
                    func_element.children.append(return_element)
                result.elements.append(func_element)

    def _get_class_names(self, code: str) -> List[str]:
        """
        Get all class names from code.

        Args:
            code: Source code as string

        Returns:
            List of class names
        """
        class_pattern = re.compile('class\\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)
        return [match.group(1) for match in class_pattern.finditer(code)]

    def _create_class_element(self, code: str, code_bytes: bytes, class_name: str, start_line: int, end_line: int, class_content: str) -> CodeElement:
        """
        Create a class element with decorators.

        Args:
        code: Source code as string
        code_bytes: Source code as bytes
        class_name: Name of the class
        start_line: Start line of the class
        end_line: End line of the class
        class_content: Content of the class

        Returns:
        CodeElement for the class
        """
        class_decorators = self.finder.get_class_decorators(code, class_name)
        class_element = CodeElement(type=CodeElementType.CLASS, name=class_name, content=class_content, range=CodeRange(start_line=start_line, end_line=end_line, node=None), additional_data={'decorators': class_decorators})
        for decorator in class_decorators:
            decorator_name = self._extract_decorator_name(decorator)
            meta_element = CodeElement(type=CodeElementType.DECORATOR, name=decorator_name, content=decorator, parent_name=class_name, additional_data={'target_type': 'class', 'target_name': class_name})
            class_element.children.append(meta_element)
        return class_element

    def _extract_decorator_name(self, decorator: str) -> str:
        """
        Extract decorator name from decorator string.
        
        Args:
            decorator: Decorator string (e.g., '@property', '@staticmethod')
            
        Returns:
            Decorator name without '@' prefix
        """
        if not decorator:
            return ''
        name = decorator.strip()
        if name.startswith('@'):
            name = name[1:]
        name = name.split('(')[0].strip()
        if '.' in name:
            return name.split('.')[1].strip()
        return name.strip()

    def _extract_class_members(self, code: str, code_bytes: bytes, class_name: str, class_element: CodeElement) -> None:
        """
        Extract members from a class (methods, properties, etc.).

        Args:
            code: Source code as string
            code_bytes: Source code as bytes
            class_name: Name of the class
            class_element: CodeElement for the class
        """
        (start_line, end_line) = self.finder.find_element(code, CodeElementType.CLASS.value, class_name)
        if start_line == 0 or end_line == 0:
            return
        lines = code.splitlines()
        class_code = '\n'.join(lines[start_line - 1:end_line])
        self._extract_methods(code, code_bytes, class_name, class_element)
        property_names = set()
        self._scan_for_properties(class_code, code, class_name, class_element, property_names)
        self._extract_static_properties(class_code, code, class_name, class_element)

    def _extract_methods(self, code: str, code_bytes: bytes, class_name: str, class_element: CodeElement) -> None:
        """
        Extract methods from a class.

        Args:
            code: Source code as string
            code_bytes: Source code as bytes
            class_name: Name of the class
            class_element: CodeElement for the class
        """
        try:
            (root, _) = self.analyzer.ast_handler.parse(code)
            class_query = TEMPLATES[CodeElementType.CLASS.value]['find_one'].format(class_name=class_name)
            class_captures = self.analyzer.ast_handler.execute_query(class_query, root, code_bytes)
            class_node = None
            for (node, capture_name) in class_captures:
                if capture_name == 'class_name':
                    class_node = self.analyzer.ast_handler.find_parent_of_type(node, 'class_definition')
                    break
            if not class_node:
                return
            
            method_query = TEMPLATES[CodeElementType.METHOD.value]['find_all']
            method_captures = self.analyzer.ast_handler.execute_query(method_query, class_node, code_bytes)
            for (node, capture_name) in method_captures:
                if capture_name == 'method_name':
                    method_name = self.analyzer.get_node_content(node, code_bytes)
                    method_node = self.analyzer.ast_handler.find_parent_of_type(node, 'function_definition')
                    if method_node:
                        (start_line, end_line) = self.analyzer.get_node_range(method_node)
                        method_content = self.analyzer.get_node_content(method_node, code_bytes)
                        method_decorators = self._find_decorators_for_method(code, method_name, class_name)
                        element_type_str = self.strategy.determine_element_type(method_decorators, is_method=True)
                        element_type = getattr(CodeElementType, element_type_str.upper())
                        method_element = CodeElement(type=element_type, name=method_name, content=method_content, range=CodeRange(start_line=start_line, end_line=end_line, node=method_node), parent_name=class_name, additional_data={'decorators': method_decorators})
                        for decorator in method_decorators:
                            decorator_name = self._extract_decorator_name(decorator)
                            decorator_element = CodeElement(type=CodeElementType.DECORATOR, name=decorator_name, content=decorator, parent_name=f'{class_name}.{method_name}', additional_data={'target_type': element_type.value, 'target_name': method_name, 'class_name': class_name})
                            method_element.children.append(decorator_element)
                        parameters = self.finder.get_function_parameters(method_content, method_name, class_name)
                        for param in parameters:
                            param_element = CodeElement(type=CodeElementType.PARAMETER, name=param['name'], content=param['name'], parent_name=f'{class_name}.{method_name}', value_type=param.get('type'), additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                            method_element.children.append(param_element)
                        return_info = self.finder.get_function_return_info(method_content, method_name, class_name)
                        if return_info['return_type'] or return_info['return_values']:
                            return_element = CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{method_name}_return', content=return_info['return_type'] if return_info['return_type'] else '', parent_name=f'{class_name}.{method_name}', value_type=return_info['return_type'], additional_data={'values': return_info['return_values']})
                            method_element.children.append(return_element)
                        class_element.children.append(method_element)
            
            decorated_method_query = ADDITIONAL_QUERIES['decorated_method'].format(method_name="")
            decorated_captures = self.analyzer.ast_handler.execute_query(decorated_method_query, class_node, code_bytes)
            for (node, capture_name) in decorated_captures:
                if capture_name == 'method_name':
                    method_name = self.analyzer.get_node_content(node, code_bytes)
                    decorated_def_node = self.analyzer.ast_handler.find_parent_of_type(node, 'decorated_definition')
                    if decorated_def_node:
                        (start_line, end_line) = self.analyzer.get_node_range(decorated_def_node)
                        method_content = self.analyzer.get_node_content(decorated_def_node, code_bytes)
                        decorator_nodes = []
                        for child_idx in range(decorated_def_node.named_child_count):
                            child = decorated_def_node.named_child(child_idx)
                            if child.type == 'decorator':
                                decorator_nodes.append(child)
                        method_decorators = [self.analyzer.get_node_content(node, code_bytes) for node in decorator_nodes]
                        element_type_str = self.strategy.determine_element_type(method_decorators, is_method=True)
                        element_type = getattr(CodeElementType, element_type_str.upper())
                        method_element = CodeElement(type=element_type, name=method_name, content=method_content, range=CodeRange(start_line=start_line, end_line=end_line, node=decorated_def_node), parent_name=class_name, additional_data={'decorators': method_decorators})
                        for decorator in method_decorators:
                            decorator_name = self._extract_decorator_name(decorator)
                            decorator_element = CodeElement(type=CodeElementType.DECORATOR, name=decorator_name, content=decorator, parent_name=f'{class_name}.{method_name}', additional_data={'target_type': element_type.value, 'target_name': method_name, 'class_name': class_name})
                            method_element.children.append(decorator_element)
                        function_node = None
                        for child_idx in range(decorated_def_node.named_child_count):
                            child = decorated_def_node.named_child(child_idx)
                            if child.type == 'function_definition':
                                function_node = child
                                break
                        if function_node:
                            function_content = self.analyzer.get_node_content(function_node, code_bytes)
                            parameters = self.finder.get_function_parameters(function_content, method_name, class_name)
                            for param in parameters:
                                param_element = CodeElement(type=CodeElementType.PARAMETER, name=param['name'], content=param['name'], parent_name=f'{class_name}.{method_name}', value_type=param.get('type'), additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                                method_element.children.append(param_element)
                            return_info = self.finder.get_function_return_info(function_content, method_name, class_name)
                            if return_info['return_type'] or return_info['return_values']:
                                return_element = CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{method_name}_return', content=return_info['return_type'] if return_info['return_type'] else '', parent_name=f'{class_name}.{method_name}', value_type=return_info['return_type'], additional_data={'values': return_info['return_values']})
                                method_element.children.append(return_element)
                        class_element.children.append(method_element)
        except Exception as e:
            (start_line, end_line) = self.finder.find_element(code, CodeElementType.CLASS.value, class_name)
            if start_line <= 0 or end_line <= 0:
                return
            lines = code.splitlines()
            class_code = '\n'.join(lines[start_line - 1:end_line])
            method_pattern = re.compile('def\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(', re.MULTILINE)
            for match in method_pattern.finditer(class_code):
                method_name = match.group(1)
                (start_line, end_line) = self.finder.find_element(code, CodeElementType.METHOD.value, method_name, class_name)
                if start_line <= 0 or end_line <= 0:
                    continue
                method_content = '\n'.join(lines[start_line - 1:end_line])
                method_decorators = self._find_decorators_for_method(code, method_name, class_name)
                element_type_str = self.strategy.determine_element_type(method_decorators, is_method=True)
                element_type = getattr(CodeElementType, element_type_str.upper())
                method_element = CodeElement(type=element_type, name=method_name, content=method_content, range=CodeRange(start_line=start_line, end_line=end_line, node=None), parent_name=class_name, additional_data={'decorators': method_decorators})
                for decorator in method_decorators:
                    decorator_name = self._extract_decorator_name(decorator)
                    decorator_element = CodeElement(type=CodeElementType.DECORATOR, name=decorator_name, content=decorator, parent_name=f'{class_name}.{method_name}', additional_data={'target_type': element_type.value, 'target_name': method_name, 'class_name': class_name})
                    method_element.children.append(decorator_element)
                parameters = self.finder.get_function_parameters(method_content, method_name, class_name)
                for param in parameters:
                    param_element = CodeElement(type=CodeElementType.PARAMETER, name=param['name'], content=param['name'], parent_name=f'{class_name}.{method_name}', value_type=param.get('type'), additional_data={'optional': param.get('optional', False), 'default': param.get('default')})
                    method_element.children.append(param_element)
                return_info = self.finder.get_function_return_info(method_content, method_name, class_name)
                if return_info['return_type'] or return_info['return_values']:
                    return_element = CodeElement(type=CodeElementType.RETURN_VALUE, name=f'{method_name}_return', content=return_info['return_type'] if return_info['return_type'] else '', parent_name=f'{class_name}.{method_name}', value_type=return_info['return_type'], additional_data={'values': return_info['return_values']})
                    method_element.children.append(return_element)
                class_element.children.append(method_element)

    def _find_decorators_for_method(self, code: str, method_name: str, class_name: str) -> List[str]:
        """
        Find decorators for a method using regex pattern matching.
        
        Args:
            code: Source code
            method_name: Method name
            class_name: Class name
            
        Returns:
            List of decorator strings
        """
        try:
            decorators = self.finder.get_decorators(code, method_name, class_name)
            if decorators:
                return decorators
        except Exception:
            pass
        lines = code.splitlines()
        method_pattern = re.compile(f'(\\s+)def\\s+{re.escape(method_name)}\\s*\\(', re.MULTILINE)
        for (i, line) in enumerate(lines):
            match = method_pattern.search(line)
            if match:
                indentation = match.group(1)
                decorators = []
                j = i - 1
                while j >= 0:
                    line_j = lines[j]
                    if line_j.strip() and line_j.startswith(indentation + '@'):
                        decorators.insert(0, line_j.strip())
                    elif not line_j.strip() or not line_j.startswith(indentation):
                        break
                    j -= 1
                return decorators
        return []

    def _scan_for_properties(self, class_code: str, full_code: str, class_name: str, class_element: CodeElement, property_names: Set[str]) -> None:
        """
        Scan the class code directly for property decorators.

        Args:
            class_code: Code of the class
            full_code: Full source code
            class_name: Name of the class
            class_element: CodeElement for the class
            property_names: Set to track already extracted property names
        """
        try:
            (root, code_bytes) = self.analyzer.ast_handler.parse(full_code)
            class_query = TEMPLATES[CodeElementType.CLASS.value]['find_one'].format(class_name=class_name)
            class_captures = self.analyzer.ast_handler.execute_query(class_query, root, code_bytes)
            class_node = None
            for (node, capture_name) in class_captures:
                if capture_name == 'class_name':
                    class_node = self.analyzer.ast_handler.find_parent_of_type(node, 'class_definition')
                    break
            if not class_node:
                return
            
            property_getter_query = TEMPLATES[CodeElementType.PROPERTY_GETTER.value]['find_all']
            property_getter_captures = self.analyzer.ast_handler.execute_query(property_getter_query, class_node, code_bytes)
            for (node, capture_name) in property_getter_captures:
                if capture_name == 'property_name':
                    property_name = self.analyzer.get_node_content(node, code_bytes)
                    if property_name in property_names:
                        continue
                    property_names.add(property_name)
                    decorated_def_node = self.analyzer.ast_handler.find_parent_of_type(node, 'decorated_definition')
                    if decorated_def_node:
                        (start_line, end_line) = self.analyzer.get_node_range(decorated_def_node)
                        content = self.analyzer.get_node_content(decorated_def_node, code_bytes)
                        decorators = ['@property']
                        property_element = CodeElement(type=CodeElementType.PROPERTY_GETTER, name=property_name, content=content, range=CodeRange(start_line=start_line, end_line=end_line, node=decorated_def_node), parent_name=class_name, additional_data={'decorators': decorators})
                        self._add_decorator_meta_elements(parent_element=property_element, decorators=decorators, parent_name=f'{class_name}.{property_name}', target_type='property', target_name=property_name, class_name=class_name)
                        class_element.children.append(property_element)
            
            property_setter_query = TEMPLATES[CodeElementType.PROPERTY_SETTER.value]['find_all']
            property_setter_captures = self.analyzer.ast_handler.execute_query(property_setter_query, class_node, code_bytes)
            for (node, capture_name) in property_setter_captures:
                if capture_name == 'property_name':
                    property_name = self.analyzer.get_node_content(node, code_bytes)
                    property_names.add(property_name)
                    decorated_def_node = self.analyzer.ast_handler.find_parent_of_type(node, 'decorated_definition')
                    if decorated_def_node:
                        (start_line, end_line) = self.analyzer.get_node_range(decorated_def_node)
                        content = self.analyzer.get_node_content(decorated_def_node, code_bytes)
                        prop_obj_node = None
                        for (capture_node, capture_name) in property_setter_captures:
                            if capture_name == 'prop_obj':
                                prop_obj_node = capture_node
                                break
                        prop_obj_name = ''
                        if prop_obj_node:
                            prop_obj_name = self.analyzer.get_node_content(prop_obj_node, code_bytes)
                        decorators = [f'@{prop_obj_name}.setter']
                        property_element = CodeElement(type=CodeElementType.PROPERTY_SETTER, name=property_name, content=content, range=CodeRange(start_line=start_line, end_line=end_line, node=decorated_def_node), parent_name=class_name, additional_data={'decorators': decorators, 'property_obj': prop_obj_name})
                        self._add_decorator_meta_elements(parent_element=property_element, decorators=decorators, parent_name=f'{class_name}.{property_name}', target_type='property_setter', target_name=property_name, class_name=class_name)
                        class_element.children.append(property_element)
        except Exception as e:
            property_pattern = re.compile('(?:^|\\n)\\s*@property\\s*\\n\\s*def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(', re.MULTILINE)
            property_matches = property_pattern.finditer(class_code)
            for match in property_matches:
                property_name = match.group(1)
                if property_name in property_names:
                    continue
                property_names.add(property_name)
                (start_line, end_line) = self.finder.find_element(full_code, CodeElementType.PROPERTY_GETTER.value, property_name, class_name)
                if start_line > 0 and end_line > 0:
                    content = '\n'.join(full_code.splitlines()[start_line - 1:end_line])
                    decorators = ['@property']
                    property_element = CodeElement(type=CodeElementType.PROPERTY_GETTER, name=property_name, content=content, range=CodeRange(start_line=start_line, end_line=end_line, node=None), parent_name=class_name, additional_data={'decorators': decorators})
                    self._add_decorator_meta_elements(parent_element=property_element, decorators=decorators, parent_name=f'{class_name}.{property_name}', target_type='property', target_name=property_name, class_name=class_name)
                    class_element.children.append(property_element)

    def _extract_static_properties(self, class_code: str, full_code: str, class_name: str, class_element: CodeElement) -> None:
        """
        Extract static properties (class variables) from the class.

        Args:
            class_code: Code of the class
            full_code: Full source code
            class_name: Name of the class
            class_element: CodeElement for the class
        """
        try:
            (root, code_bytes) = self.analyzer.ast_handler.parse(full_code)
            class_query = TEMPLATES[CodeElementType.CLASS.value]['find_one'].format(class_name=class_name)
            class_captures = self.analyzer.ast_handler.execute_query(class_query, root, code_bytes)
            class_node = None
            for (node, capture_name) in class_captures:
                if capture_name == 'class_name':
                    class_node = self.analyzer.ast_handler.find_parent_of_type(node, 'class_definition')
                    break
            if not class_node:
                return
            
            static_prop_query = TEMPLATES[CodeElementType.STATIC_PROPERTY.value]['find_all']
            static_prop_captures = self.analyzer.ast_handler.execute_query(static_prop_query, class_node, code_bytes)
            for (node, capture_name) in static_prop_captures:
                if capture_name == 'prop_name':
                    property_name = self.analyzer.get_node_content(node, code_bytes)
                    if property_name.startswith('__') or (property_name.startswith('_') and (not property_name.startswith('_' + class_name.lower()))):
                        continue
                    assignment_node = self.analyzer.ast_handler.find_parent_of_type(node, 'assignment')
                    if assignment_node:
                        expr_node = self.analyzer.ast_handler.find_parent_of_type(assignment_node, 'expression_statement')
                        if expr_node:
                            (start_line, end_line) = self.analyzer.get_node_range(expr_node)
                            content = self.analyzer.get_node_content(expr_node, code_bytes)
                            property_value = ''
                            value_node = None
                            for value_node in assignment_node.children:
                                if value_node.type != 'identifier':
                                    property_value = self.analyzer.get_node_content(value_node, code_bytes)
                                    break
                            property_element = CodeElement(type=CodeElementType.STATIC_PROPERTY, name=property_name, content=content, range=CodeRange(start_line=start_line, end_line=end_line, node=expr_node), parent_name=class_name, additional_data={'value': property_value, 'is_static': True})
                            class_element.children.append(property_element)
        except Exception as e:
            property_pattern = re.compile('(?:^|\\n)\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*=\\s*([^()\\n]+)(?:\\n|$)', re.MULTILINE)
            property_matches = property_pattern.finditer(class_code)
            for match in property_matches:
                property_name = match.group(1)
                property_value = match.group(2).strip()
                if property_name.startswith('__') or (property_name.startswith('_') and (not property_name.startswith('_' + class_name.lower()))):
                    continue
                start_pos = match.start()
                line_count = class_code[:start_pos].count('\n') + 1
                (class_start_line, _) = self.finder.find_element(full_code, CodeElementType.CLASS.value, class_name)
                start_line = class_start_line + line_count - 1
                content = match.group(0).strip()
                property_element = CodeElement(type=CodeElementType.STATIC_PROPERTY, name=property_name, content=content, range=CodeRange(start_line=start_line, end_line=start_line, node=None), parent_name=class_name, additional_data={'value': property_value, 'is_static': True})
                class_element.children.append(property_element)

    def _is_class_method(self, code: str, func_name: str, classes: List[str]) -> bool:
        """
        Check if a function is a method of any class.

        Args:
            code: Source code as string
            func_name: Name of the function
            classes: List of class names

        Returns:
            True if the function is a method of a class, False otherwise
        """
        for class_name in classes:
            (start_line, end_line) = self.finder.find_element(code, CodeElementType.METHOD.value, func_name, class_name)
            if start_line > 0 and end_line > 0:
                return True
        return False

    def _add_decorator_meta_elements(self, parent_element: CodeElement, decorators: List[str], parent_name: str, target_type: str, target_name: str, class_name: Optional[str]=None) -> None:
        """
        Add decorator meta-elements to a parent element.

        Args:
            parent_element: Parent element to add decorators to
            decorators: List of decorator strings
            parent_name: Name of the parent element
            target_type: Type of the target element
            target_name: Name of the target element
            class_name: Optional name of the class
        """
        for decorator in decorators:
            if isinstance(decorator, str):
                decorator_name = self._extract_decorator_name(decorator)
                meta_data = {'target_type': target_type, 'target_name': target_name}
                if class_name:
                    meta_data['class_name'] = class_name
                meta_element = CodeElement(type=CodeElementType.DECORATOR, name=decorator_name, content=decorator, parent_name=parent_name, additional_data=meta_data)
                parent_element.children.append(meta_element)