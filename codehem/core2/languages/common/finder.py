"""
Common finder implementation shared across language modules.
"""
from typing import Tuple, List, Optional, Dict, Any
from tree_sitter import Node

from ...engine.base_finder import BaseFinder
from ...engine.ast_handler import ASTHandler

class CommonFinder(BaseFinder):
    """
    Common implementation of the code finder with shared functionality.
    Language-specific finders should extend this class.
    """
    
    def __init__(self, ast_handler: ASTHandler, templates: Dict[str, Dict[str, str]]):
        """
        Initialize the common finder.
        
        Args:
            ast_handler: AST handler instance
            templates: Dictionary of query templates
        """
        self.ast_handler = ast_handler
        self.templates = templates
    
    def find_element(self, code: str, element_type: str, name: str, parent_name: Optional[str] = None) -> Tuple[int, int]:
        """
        Find an element of the specified type in the code.
        
        Args:
            code: Source code as string
            element_type: Type of element to find
            name: Name of the element to find
            parent_name: Name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        handler = self._get_element_handler(element_type)
        if handler:
            return handler(code, name, parent_name)
        
        # Default implementation for simple elements
        if element_type not in self.templates:
            return (0, 0)
            
        template = self.templates[element_type]['find_one']
        
        # For other elements, use the template directly
        param_name = f"{element_type.lower()}_name"
        template = template.format(**{param_name: name})
        return self._find_element_by_query(code, template)
    
    def _get_element_handler(self, element_type: str) -> Optional[callable]:
        """
        Get the handler function for the specified element type.
        Override this in language-specific finders.
        
        Args:
            element_type: Element type
            
        Returns:
            Handler function or None if no specific handler
        """
        return None
    
    def _find_element_by_query(self, code: str, query: str) -> Tuple[int, int]:
        """
        Find an element using a tree-sitter query.
        
        Args:
            code: Source code as string
            query: Tree-sitter query
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        (root, code_bytes) = self.ast_handler.parse(code)
        captures = self.ast_handler.execute_query(query, root, code_bytes)
        
        element_node = None
        for node, capture_name in captures:
            if capture_name.endswith('_name'):
                element_node = self.ast_handler.find_parent_of_type(node, self._get_parent_node_type(capture_name))
                if element_node:
                    break
            elif capture_name in self._get_element_capture_names():
                element_node = node
                break
                    
        if element_node:
            return self.ast_handler.get_node_range(element_node)
            
        return (0, 0)
    
    def _get_parent_node_type(self, capture_name: str) -> str:
        """
        Get the parent node type for a capture name.
        Override this in language-specific finders.
        
        Args:
            capture_name: Capture name (e.g., 'func_name', 'class_name')
            
        Returns:
            Parent node type (e.g., 'function_definition', 'class_definition')
        """
        return 'module'
    
    def _get_element_capture_names(self) -> List[str]:
        """
        Get the list of element capture names.
        Override this in language-specific finders.
        
        Returns:
            List of element capture names
        """
        return ['class', 'function', 'method', 'property', 'import']
    
    def find_element_in_parent(self, code: str, parent_type: str, parent_name: str, 
                              element_type: str, element_name: str, template_key: str = None) -> Tuple[int, int]:
        """
        Find an element within a parent element.
        
        Args:
            code: Source code as string
            parent_type: Type of parent element
            parent_name: Name of parent element
            element_type: Type of element to find
            element_name: Name of element to find
            template_key: Optional alternate template key
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        # First, find the parent
        parent_template = self.templates[parent_type]['find_one'].format(**{f"{parent_type.lower()}_name": parent_name})
        (root, code_bytes) = self.ast_handler.parse(code)
        parent_captures = self.ast_handler.execute_query(parent_template, root, code_bytes)
        
        parent_node = None
        for node, capture_name in parent_captures:
            if capture_name == parent_type or capture_name == parent_type.lower():
                parent_node = node
                break
                
        if not parent_node:
            return (0, 0)
            
        # Now find the element within the parent
        key = template_key or element_type
        if key not in self.templates or 'find_one' not in self.templates[key]:
            return (0, 0)
            
        element_template = self.templates[key]['find_one'].format(**{f"{element_type.lower()}_name": element_name})
        element_captures = self.ast_handler.execute_query(element_template, parent_node, code_bytes)
        
        for node, capture_name in element_captures:
            if capture_name == element_type or capture_name == key or capture_name == key.lower():
                return self.ast_handler.get_node_range(node)
                
        return (0, 0)
    
    def get_elements_by_type(self, code: str, element_type: str) -> List[Dict[str, Any]]:
        """
        Get all elements of the specified type from the code.
        
        Args:
            code: Source code as string
            element_type: Type of elements to find
            
        Returns:
            List of dictionaries with element information
        """
        if element_type not in self.templates or 'find_all' not in self.templates[element_type]:
            return []
            
        template = self.templates[element_type]['find_all']
        (root, code_bytes) = self.ast_handler.parse(code)
        captures = self.ast_handler.execute_query(template, root, code_bytes)
        
        result = []
        current_element = None
        
        for node, capture_name in captures:
            if capture_name == element_type or capture_name in self._get_element_capture_names():
                if current_element:
                    result.append(current_element)
                current_element = {
                    'node': node,
                    'type': element_type,
                    'range': self.ast_handler.get_node_range(node),
                    'content': self.ast_handler.get_node_text(node, code_bytes)
                }
            elif capture_name.endswith('_name') and current_element:
                current_element['name'] = self.ast_handler.get_node_text(node, code_bytes)
                
        if current_element:
            result.append(current_element)
            
        return result
    
    def get_node_content(self, node: Node, code_bytes: bytes) -> str:
        """
        Get the content of a node.
        
        Args:
            node: Tree-sitter node
            code_bytes: Source code as bytes
            
        Returns:
            Content of the node as string
        """
        return self.ast_handler.get_node_text(node, code_bytes)
    
    def get_node_range(self, node: Node) -> Tuple[int, int]:
        """
        Get the line range of a node.
        
        Args:
            node: Tree-sitter node
            
        Returns:
            Tuple of (start_line, end_line)
        """
        return self.ast_handler.get_node_range(node)