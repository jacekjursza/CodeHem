"""
Python-specific syntax tree navigator implementation.

This module provides Python-specific implementation of the ISyntaxTreeNavigator interface.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from tree_sitter import Query, Node, QueryError

from codehem.core.components.base_implementations import BaseSyntaxTreeNavigator
from codehem.models.enums import CodeElementType
from codehem.core.engine.languages import PY_LANGUAGE

logger = logging.getLogger(__name__)

class PythonSyntaxTreeNavigator(BaseSyntaxTreeNavigator):
    """
    Python-specific implementation of the syntax tree navigator.
    
    Provides functionality for navigating and querying Python syntax trees.
    """
    
    def __init__(self):
        """Initialize the Python syntax tree navigator."""
        super().__init__('python')
    
    def find_element(self, tree: Node, code_bytes: bytes, element_type: str, 
                   element_name: Optional[str]=None, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the Python syntax tree based on type, name, and parent.
        
        Args:
            tree: The syntax tree to search
            code_bytes: The original code as bytes
            element_type: Type of element to find (e.g., 'function', 'class', 'method')
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        logger.debug(f"Finding Python element: type='{element_type}', name='{element_name}', parent='{parent_name}'")
        
        # Check if this is a member search (method or property of a class)
        is_member_search = element_type in [
            CodeElementType.METHOD.value,
            CodeElementType.PROPERTY.value,
            CodeElementType.PROPERTY_GETTER.value,
            CodeElementType.PROPERTY_SETTER.value,
            CodeElementType.STATIC_PROPERTY.value
        ]
        
        try:
            # Build query based on element type
            query_string = self._build_query_for_element_type(element_type, element_name, parent_name)
            if not query_string:
                logger.warning(f"Could not build query for element type '{element_type}'")
                return (0, 0)
            
            # Execute query
            matches = self.execute_query(tree, code_bytes, query_string)
            if not matches:
                logger.debug(f"No matches found for element type '{element_type}', name '{element_name}'")
                return (0, 0)
            
            # Filter results based on name and parent if needed
            filtered_matches = []
            for node, capture_name in matches:
                # Check if node matches our criteria
                current_name = self._get_node_name(node, code_bytes)
                current_parent = None
                
                if is_member_search:
                    # Find parent class for methods and properties
                    current_parent = self._get_node_parent_class(node, code_bytes)
                
                name_match = (element_name is None) or (current_name == element_name)
                parent_match = (not is_member_search) or (parent_name is None) or (current_parent == parent_name)
                
                if name_match and parent_match:
                    filtered_matches.append((node, capture_name))
            
            if not filtered_matches:
                logger.debug(f"No filtered matches found for element")
                return (0, 0)
            
            # Get range for first match
            best_node = filtered_matches[0][0]
            start_line, end_line = self.get_node_range(best_node)
            logger.debug(f"Found element at lines {start_line}-{end_line}")
            return (start_line, end_line)
            
        except QueryError as e:
            logger.error(f"Query error when finding element: {e}")
            return (0, 0)
        except Exception as e:
            logger.error(f"Error when finding element: {e}", exc_info=True)
            return (0, 0)
    
    def execute_query(self, tree: Node, code_bytes: bytes, query_string: str) -> List[Tuple[Node, str]]:
        """
        Execute a tree-sitter query on the Python syntax tree.
        
        Args:
            tree: The syntax tree to query
            code_bytes: The original code as bytes
            query_string: The query to execute
            
        Returns:
            List of tuples (node, capture_name) matching the query
        """
        try:
            query = Query(PY_LANGUAGE, query_string)
            # Tree-sitter changed API - now requires a callback function
            results = []
            
            def capture_callback(match, capture_index, node):
                # Create a match record
                capture_name = query.capture_names[capture_index]
                results.append((node, capture_name))
                return True  # Continue matching
            
            # Execute the query with the callback
            query.matches(tree, capture_callback)
            
            return results
        except QueryError as e:
            logger.error(f"Query error: {e}, query: {query_string}")
            raise
        except Exception as e:
            logger.error(f"Error executing query: {e}", exc_info=True)
            return []
    
    def get_node_text(self, node: Node, code_bytes: bytes) -> str:
        """
        Get the text for a node in the Python syntax tree.
        
        Args:
            node: The node to get text for
            code_bytes: The original code as bytes
            
        Returns:
            The text of the node
        """
        if node is None:
            return ""
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')
    
    def get_node_range(self, node: Node) -> Tuple[int, int]:
        """
        Get the line range for a node in the Python syntax tree.
        
        Args:
            node: The node to get range for
            
        Returns:
            Tuple of (start_line, end_line)
        """
        if node is None:
            return (0, 0)
        return (node.start_point[0] + 1, node.end_point[0] + 1)
    
    def _build_query_for_element_type(self, element_type: str, element_name: Optional[str]=None, 
                                    parent_name: Optional[str]=None) -> str:
        """
        Build a tree-sitter query for a specific element type.
        
        Args:
            element_type: Type of element to find
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element
            
        Returns:
            The query string or None if not supported
        """
        if element_type == CodeElementType.FUNCTION.value:
            name_constraint = f' name: (identifier) @name  (#eq? @name "{element_name}")' if element_name else ''
            return f'(function_definition{name_constraint}) @function_def'
        
        elif element_type == CodeElementType.CLASS.value:
            name_constraint = f' name: (identifier) @name  (#eq? @name "{element_name}")' if element_name else ''
            return f'(class_definition{name_constraint}) @class_def'
        
        elif element_type == CodeElementType.METHOD.value:
            if not parent_name:
                # Method must have a parent class
                return None
            
            # Find method within a specific class
            name_constraint = f' name: (identifier) @name  (#eq? @name "{element_name}")' if element_name else ''
            parent_constraint = f' (#eq? @class_name "{parent_name}")'
            
            return f'''
            (class_definition
                name: (identifier) @class_name {parent_constraint}
                body: (block
                    (function_definition{name_constraint}) @method_def
                )
            )
            '''
        
        elif element_type in [CodeElementType.PROPERTY_GETTER.value, CodeElementType.PROPERTY_SETTER.value]:
            # This is more complex as we need to look for decorated methods
            # We'll implement a simplified version here
            if not parent_name:
                # Property must have a parent class
                return None
            
            decorator_type = 'property' if element_type == CodeElementType.PROPERTY_GETTER.value else f'{element_name}.setter'
            
            return f'''
            (class_definition
                name: (identifier) @class_name  (#eq? @class_name "{parent_name}")
                body: (block
                    (decorated_definition
                        (decorator
                            name: (identifier) @dec_name  (#eq? @dec_name "{decorator_type}")
                        )
                        (function_definition
                            name: (identifier) @method_name  (#eq? @method_name "{element_name}")
                        ) @property_def
                    )
                )
            )
            '''
        
        elif element_type == CodeElementType.STATIC_PROPERTY.value:
            if not parent_name:
                # Static property must have a parent class
                return None
            
            name_constraint = f'(identifier) @name  (#eq? @name "{element_name}")' if element_name else '(identifier) @name'
            
            return f'''
            (class_definition
                name: (identifier) @class_name  (#eq? @class_name "{parent_name}")
                body: (block
                    (expression_statement
                        (assignment
                            left: {name_constraint}
                        )
                    ) @static_prop
                )
            )
            '''
        
        elif element_type == CodeElementType.IMPORT.value:
            # Note: This might not work perfectly for finding specific imports
            # as import extraction usually combines all imports
            return f'''
            (import_statement) @import_stmt
            (import_from_statement) @import_from_stmt
            '''
        
        else:
            logger.warning(f"Unsupported element type for query building: {element_type}")
            return None
    
    def _get_node_name(self, node: Node, code_bytes: bytes) -> Optional[str]:
        """Get the name of a node if available."""
        # Check if there's a direct name field
        name_node = node.child_by_field_name('name')
        if name_node:
            return self.get_node_text(name_node, code_bytes)
        
        # If not, try to infer from node type and content
        if node.type == 'function_definition':
            for child in node.children:
                if child.type == 'identifier':
                    return self.get_node_text(child, code_bytes)
        
        return None
    
    def _get_node_parent_class(self, node: Node, code_bytes: bytes) -> Optional[str]:
        """Get the parent class name of a node if available."""
        # Look for parent class_definition
        current = node
        while current and current.type != 'class_definition':
            current = current.parent
        
        if current and current.type == 'class_definition':
            name_node = current.child_by_field_name('name')
            if name_node:
                return self.get_node_text(name_node, code_bytes)
        
        return None
    
    def find_child_by_field_name(self, node: Node, field_name: str) -> Optional[Node]:
        """Find a child node by field name."""
        if node is None:
            return None
        return node.child_by_field_name(field_name)
    
    def find_parent_of_type(self, node: Node, parent_type: Union[str, List[str]]) -> Optional[Node]:
        """Find a parent node of the specified type."""
        if node is None:
            return None
        
        if isinstance(parent_type, str):
            target_types = {parent_type}
        elif isinstance(parent_type, list):
            target_types = set(parent_type)
        else:
            logger.error(f"Invalid parent_type: {parent_type}")
            return None
        
        current = node.parent
        while current is not None:
            if current.type in target_types:
                return current
            current = current.parent
        
        return None
