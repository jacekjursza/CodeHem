from abc import ABC, abstractmethod
from typing import Tuple, Any, List, Optional
from ast_handler import ASTHandler
from query_builder import QueryBuilder
from rich.console import Console
from tree_sitter import Node

from languages import get_parser


class CodeFinder(ABC):
    language = 'python'

    def __init__(self):
        super().__init__()
        self.ast_handler = ASTHandler(self.language)
        self.query_builder = QueryBuilder(self.language)
        self.parser = get_parser(self.language)

    @abstractmethod
    def find_function(self, code: str, function_name: str) -> Tuple[int, int]:
        pass

    @abstractmethod
    def find_class(self, code: str, class_name: str) -> Tuple[int, int]:
        pass

    @abstractmethod
    def find_method(self, code: str, class_name: str, method_name: str) -> Tuple[int, int]:
        pass

    @abstractmethod
    def find_property(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        pass

    def find_property_setter(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        return (0, 0)

    def find_property_and_setter(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        return (0, 0)

    def get_class_with_updated_property(self, code: str, class_name: str, property_name: str, new_property_code: str) -> str:
        return code

    @abstractmethod
    def find_imports_section(self, code: str) -> Tuple[int, int]:
        pass

    @abstractmethod
    def find_properties_section(self, code: str, class_name: str) -> Tuple[int, int]:
        pass

    @abstractmethod
    def get_classes_from_code(self, code: str) -> List[Tuple[str, Node]]:
        pass

    @abstractmethod
    def get_methods_from_code(self, code: str) -> List[Tuple[str, Node]]:
        pass

    @abstractmethod
    def get_methods_from_class(self, code: str, class_name: str) -> List[Tuple[str, Node]]:
        pass

    @abstractmethod
    def has_class_method_indicator(self, method_node: Node, code_bytes: bytes) -> bool:
        pass

    def get_decorators(self, code: str, name: str, class_name: Optional[str]=None) -> List[str]:
        """
        Get decorators for a function or method.
        
        Args:
            code: Source code as string
            name: Function or method name
            class_name: Class name if searching for method decorators, None for standalone functions
            
        Returns:
            List of decorator strings
        """
        (root, code_bytes) = self.ast_handler.parse(code)
        
        if class_name:
            # Look for method decorators
            query_string = f"""
            (class_definition
              name: (identifier) @class_name (#eq? @class_name "{class_name}")
              body: (_) @class_body)
            """
            
            captures = self.ast_handler.execute_query(query_string, root, code_bytes)
            class_body = None
            
            for node, capture_name in captures:
                if capture_name == 'class_body':
                    class_body = node
            
            if not class_body:
                return []
                
            # Find the method and its decorators
            method_query = f"""
            (function_definition
              name: (identifier) @method_name (#eq? @method_name "{name}"))
            """
            
            method_captures = self.ast_handler.execute_query(method_query, class_body, code_bytes)
            method_node = None
            
            for node, capture_name in method_captures:
                if capture_name == 'method_name':
                    method_node = self.ast_handler.find_parent_of_type(node, "function_definition")
            
            if not method_node:
                return []
                
            # Check if the method is decorated
            decorators = []
            
            if method_node.parent and method_node.parent.type == 'decorated_definition':
                for child in method_node.parent.children:
                    if child.type == 'decorator':
                        decorators.append(self.ast_handler.get_node_text(child, code_bytes))
            
            return decorators
        else:
            # Look for function decorators
            query_string = f"""
            (function_definition
              name: (identifier) @func_name (#eq? @func_name "{name}"))
            """
            
            captures = self.ast_handler.execute_query(query_string, root, code_bytes)
            func_node = None
            
            for node, capture_name in captures:
                if capture_name == 'func_name':
                    func_node = self.ast_handler.find_parent_of_type(node, "function_definition")
            
            if not func_node:
                return []
                
            # Check if the function is decorated
            decorators = []
            
            if func_node.parent and func_node.parent.type == 'decorated_definition':
                for child in func_node.parent.children:
                    if child.type == 'decorator':
                        decorators.append(self.ast_handler.get_node_text(child, code_bytes))
            
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
        (root, code_bytes) = self.ast_handler.parse(code)
        
        query_string = f"""
        (class_definition
          name: (identifier) @class_name (#eq? @class_name "{class_name}"))
        """
        
        captures = self.ast_handler.execute_query(query_string, root, code_bytes)
        class_node = None
        
        for node, capture_name in captures:
            if capture_name == 'class_name':
                class_node = self.ast_handler.find_parent_of_type(node, "class_definition")
        
        if not class_node:
            return []
            
        # Check if the class is decorated
        decorators = []
        
        if class_node.parent and class_node.parent.type == 'decorated_definition':
            for child in class_node.parent.children:
                if child.type == 'decorator':
                    decorators.append(self.ast_handler.get_node_text(child, code_bytes))
        
        return decorators

    def is_correct_syntax(self, plain_text: str) -> bool:
        try:
            self.ast_handler.parse(plain_text)
            return True
        except Exception:
            return False

    def is_class_method(self, method_node: Node, code_bytes: bytes) -> bool:
        return self.has_class_method_indicator(method_node, code_bytes)

    def find_class_for_method(self, method_name: str, code: str) -> Optional[str]:
        classes = self.get_classes_from_code(code)
        for (class_name, class_node) in classes:
            methods = self.get_methods_from_class(code, class_name)
            for (method_name_found, _) in methods:
                if method_name_found == method_name:
                    return class_name
        return None

    def _get_tree(self, code: str) -> Tuple[Node, bytes]:
        return self.ast_handler.parse(code)

    def _get_node_text(self, node: Node, code_bytes: bytes) -> str:
        return self.ast_handler.get_node_text(node, code_bytes)

    def get_node_content(self, node: Node, code_bytes: bytes) -> str:
        return self._get_node_text(node, code_bytes)

    def get_node_range(self, node: Node) -> Tuple[int, int]:
        return self.ast_handler.get_node_range(node)

    def _process_captures(self, captures: Any) -> list:
        return self.ast_handler._process_captures(captures)

    def content_looks_like_class_definition(self, content: str) -> bool:
        if not content or not content.strip():
            return False
        content_lines = content.strip().splitlines()
        if not content_lines:
            return False
        try:
            classes = self.get_classes_from_code(content)
            if classes and len(classes) > 0:
                return True
        except Exception:
            pass
        return False