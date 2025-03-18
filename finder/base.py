from abc import ABC, abstractmethod
from typing import Tuple, Any, List, Optional

from rich.console import Console
from tree_sitter import Node

from languages import get_parser


class CodeFinder(ABC):
    language = 'python'

    def __init__(self):
        super().__init__()
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
        return []

    def is_correct_syntax(self, plain_text: str) -> bool:
        try:
            self._get_tree(plain_text)
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
        code_bytes = code.encode('utf8')
        tree = self.parser.parse(code_bytes)
        return (tree.root_node, code_bytes)

    def _get_node_text(self, node: Node, code_bytes: bytes) -> str:
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')

    def get_node_content(self, node: Node, code_bytes: bytes) -> str:
        return self._get_node_text(node, code_bytes)

    def get_node_range(self, node: Node) -> Tuple[int, int]:
        return (node.start_point[0] + 1, node.end_point[0] + 1)

    def _process_captures(self, captures: Any) -> list:
        result = []
        try:
            if isinstance(captures, dict):
                for (cap_name, nodes) in captures.items():
                    if isinstance(nodes, list):
                        for node in nodes:
                            result.append((node, cap_name))
                    else:
                        result.append((nodes, cap_name))
            elif isinstance(captures, list):
                result = captures
            else:
                Console().print(f'[yellow]Unexpected captures type: {type(captures)}[/yellow]')
        except Exception as e:
            Console().print(f'[yellow]Error processing captures: {e}[/yellow]')
            import traceback
            Console().print(f'[dim]{traceback.format_exc()}[/dim]')
        return result

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