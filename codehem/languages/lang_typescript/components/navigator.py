"""
TypeScript syntax tree navigator component.

This module provides the TypeScript implementation of the ISyntaxTreeNavigator interface,
responsible for navigating and executing queries on TypeScript syntax trees.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from codehem.core.components.interfaces import ISyntaxTreeNavigator
from codehem.core.components.base_implementations import BaseSyntaxTreeNavigator
from codehem.core.engine.languages import LANGUAGES

logger = logging.getLogger(__name__)


class TypeScriptSyntaxTreeNavigator(BaseSyntaxTreeNavigator):
    """
    TypeScript implementation of the ISyntaxTreeNavigator interface.
    
    Provides methods for navigating TypeScript/JavaScript syntax trees,
    executing queries, and retrieving node content and range information.
    """
    
    def __init__(self):
        """Initialize the TypeScript syntax tree navigator."""
        super().__init__('typescript')
        self.language = LANGUAGES['typescript']
    
    def find_element(
        self, 
        tree: Any, 
        code_bytes: bytes, 
        element_type: str, 
        element_name: Optional[str] = None, 
        parent_name: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Find a specific element in the TypeScript syntax tree.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            element_type: Type of the element to find (function, class, method, etc.)
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for a method)
            
        Returns:
            Tuple of (start_line, end_line) for the found element
        """
        logger.debug(f"find_element: Finding TypeScript element type={element_type}, name={element_name}, parent={parent_name}")
        
        # Build a query based on the element type, name, and parent
        query_string = self._build_query_for_element_type(element_type, element_name, parent_name)
        
        try:
            # Execute the query on the tree
            query_results = self.execute_query(tree, code_bytes, query_string)
            
            for match in query_results:
                # Check if the match has the target element we're looking for
                target_node = None
                
                # Each element type has a different structure in the query
                if element_type.lower() in ['function', 'func']:
                    if 'func_decl' in match:
                        target_node = match['func_decl']
                elif element_type.lower() in ['class']:
                    if 'class_decl' in match:
                        target_node = match['class_decl']
                elif element_type.lower() in ['method', 'member']:
                    if 'method_def' in match:
                        target_node = match['method_def']
                elif element_type.lower() in ['property', 'prop']:
                    if 'property_def' in match:
                        target_node = match['property_def']
                elif element_type.lower() in ['interface']:
                    if 'interface_decl' in match:
                        target_node = match['interface_decl']
                elif element_type.lower() in ['import']:
                    if 'import' in match:
                        target_node = match['import']
                elif element_type.lower() in ['enum']:
                    if 'enum_decl' in match:
                        target_node = match['enum_decl']
                elif element_type.lower() in ['type', 'type_alias']:
                    if 'type_alias' in match:
                        target_node = match['type_alias']
                
                # If we found a matching node, return its line range
                if target_node:
                    start_line, end_line = self.get_node_range(target_node)
                    logger.debug(f"find_element: Found TypeScript element at lines {start_line}-{end_line}")
                    return start_line, end_line
            
            # If no matching node was found, return 0, 0
            logger.warning(f"find_element: No matching TypeScript element found: type={element_type}, name={element_name}, parent={parent_name}")
            return 0, 0
            
        except Exception as e:
            logger.error(f"find_element: Error finding TypeScript element: {e}", exc_info=True)
            return 0, 0
    
    def execute_query(self, tree: Any, code_bytes: bytes, query_string: str) -> List[Dict[str, Any]]:
        """
        Execute a tree-sitter query on the TypeScript syntax tree.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            query_string: The tree-sitter query string
            
        Returns:
            List of dictionaries mapping capture names to nodes
        """
        logger.debug(f"execute_query: Executing TypeScript query: {query_string[:100]}...")
        
        try:
            # Create a tree-sitter query
            query = self.language.query(query_string)
            
            # Execute the query and get matches
            # Handle both tree objects and node objects
            if hasattr(tree, 'root_node'):
                # It's a tree object
                captures = query.captures(tree.root_node)
            else:
                # It's a node object
                captures = query.captures(tree)
            
            # Process captures into structured format  
            result = []
            if captures:
                # Determine if this is a "flat" query (single capture type with multiple nodes)
                # vs "hierarchical" query (multiple capture types that should be grouped)
                is_flat_query = len(captures) == 1 and any(len(nodes) > 1 for nodes in captures.values())
                
                if is_flat_query:
                    # Flat query: create one match per node
                    for capture_name, nodes in captures.items():
                        for node in nodes:
                            result.append({capture_name: node})
                else:
                    # Hierarchical query: check if multiple captures have multiple nodes
                    # If so, we need to create multiple matches with corresponding nodes
                    max_nodes = max(len(nodes) for nodes in captures.values())
                    multi_capture_multi_node = max_nodes > 1 and len(captures) > 1
                    
                    if multi_capture_multi_node:
                        # Sort all capture nodes by their start position to ensure correct pairing
                        sorted_captures = {}
                        for capture_name, nodes in captures.items():
                            sorted_captures[capture_name] = sorted(nodes, key=lambda n: n.start_point)
                        
                        # Create multiple matches with corresponding nodes (now correctly sorted)
                        for i in range(max_nodes):
                            match_dict = {}
                            for capture_name, nodes in sorted_captures.items():
                                if i < len(nodes):
                                    match_dict[capture_name] = nodes[i]
                            
                            if match_dict:
                                result.append(match_dict)
                    else:
                        # Simple hierarchical query: group all captures together
                        match_dict = {}
                        for capture_name, nodes in captures.items():
                            # Take the first node for each capture name
                            if nodes:
                                match_dict[capture_name] = nodes[0]
                        
                        if match_dict:
                            result.append(match_dict)
            
            logger.debug(f"execute_query: Found {len(result)} matches")
            return result
            
        except Exception as e:
            logger.error(f"execute_query: Error executing TypeScript query: {e}", exc_info=True)
            return []
    
    def get_node_text(self, node: Any, code_bytes: bytes) -> bytes:
        """
        Get the text content of a syntax tree node.
        
        Args:
            node: The syntax tree node
            code_bytes: The original code bytes
            
        Returns:
            The text content of the node as bytes
        """
        try:
            start_byte = node.start_byte
            end_byte = node.end_byte
            return code_bytes[start_byte:end_byte]
        except Exception as e:
            logger.error(f"get_node_text: Error getting node text: {e}", exc_info=True)
            return b""
    
    def get_node_range(self, node: Any) -> Tuple[int, int]:
        """
        Get the line range of a syntax tree node.
        
        Args:
            node: The syntax tree node
            
        Returns:
            Tuple of (start_line, end_line) where lines are 1-based
        """
        try:
            # Add 1 to convert from 0-based (tree-sitter) to 1-based
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            return start_line, end_line
        except Exception as e:
            logger.error(f"get_node_range: Error getting node range: {e}", exc_info=True)
            return 0, 0
    
    def find_child_by_field_name(self, node: Any, field_name: str) -> Optional[Any]:
        """
        Find a direct child node by its field name in the AST.
        
        Args:
            node: The parent node
            field_name: The field name to look for
            
        Returns:
            The child node or None if not found
        """
        try:
            return node.child_by_field_name(field_name)
        except Exception as e:
            logger.error(f"find_child_by_field_name: Error finding child by field name '{field_name}': {e}", exc_info=True)
            return None
    
    def find_parent_of_type(self, node: Any, parent_type: Union[str, List[str]]) -> Optional[Any]:
        """
        Find the nearest ancestor node of a specified type.
        
        Args:
            node: The starting node
            parent_type: The type(s) of parent to find (str or list of strings)
            
        Returns:
            The parent node or None if not found
        """
        try:
            # Convert single string to list for uniform handling
            parent_types = [parent_type] if isinstance(parent_type, str) else parent_type
            
            current = node.parent
            while current:
                if current.type in parent_types:
                    return current
                current = current.parent
            
            return None
            
        except Exception as e:
            logger.error(f"find_parent_of_type: Error finding parent of type '{parent_type}': {e}", exc_info=True)
            return None
    
    def _build_query_for_element_type(
        self, 
        element_type: str, 
        element_name: Optional[str] = None, 
        parent_name: Optional[str] = None
    ) -> str:
        """
        Build a tree-sitter query string for finding a specific element type.
        
        Args:
            element_type: The type of element to find
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element
            
        Returns:
            A tree-sitter query string
        """
        # Start with a query template based on the element type
        query_template = ""
        
        if element_type.lower() in ['function', 'func']:
            if element_name:
                query_template = """
                (function_declaration
                  name: (identifier) @func_name
                  (#eq? @func_name "{name}")
                  parameters: (formal_parameters) @params
                  body: (statement_block) @body) @func_decl
                
                (lexical_declaration
                  (variable_declarator
                    name: (identifier) @func_name
                    (#eq? @func_name "{name}")
                    value: (arrow_function
                      parameters: (formal_parameters) @params
                      body: (_) @body)) @func_expr) @func_decl
                """
            else:
                query_template = """
                (function_declaration
                  name: (identifier) @func_name
                  parameters: (formal_parameters) @params
                  body: (statement_block) @body) @func_decl
                
                (lexical_declaration
                  (variable_declarator
                    name: (identifier) @func_name
                    value: (arrow_function
                      parameters: (formal_parameters) @params
                      body: (_) @body)) @func_expr) @func_decl
                """
        
        elif element_type.lower() in ['class']:
            if element_name:
                query_template = """
                (class_declaration
                  name: (type_identifier) @class_name
                  (#eq? @class_name "{name}")
                  body: (class_body) @body) @class_decl
                """
            else:
                query_template = """
                (class_declaration
                  name: (type_identifier) @class_name
                  body: (class_body) @body) @class_decl
                """
        
        elif element_type.lower() in ['method', 'member']:
            if parent_name and element_name:
                query_template = """
                (class_declaration
                  name: (type_identifier) @class_name
                  (#eq? @class_name "{parent}")
                  body: (class_body
                    (method_definition
                      name: (property_identifier) @method_name
                      (#eq? @method_name "{name}")
                      parameters: (formal_parameters) @params
                      body: (statement_block) @body))) @method_def
                """
            elif element_name:
                query_template = """
                (class_declaration
                  name: (type_identifier) @class_name
                  body: (class_body
                    (method_definition
                      name: (property_identifier) @method_name
                      (#eq? @method_name "{name}")
                      parameters: (formal_parameters) @params
                      body: (statement_block) @body))) @method_def
                """
            elif parent_name:
                query_template = """
                (class_declaration
                  name: (type_identifier) @class_name
                  (#eq? @class_name "{parent}")
                  body: (class_body
                    (method_definition
                      name: (property_identifier) @method_name
                      parameters: (formal_parameters) @params
                      body: (statement_block) @body))) @method_def
                """
            else:
                query_template = """
                (class_declaration
                  name: (type_identifier) @class_name
                  body: (class_body
                    (method_definition
                      name: (property_identifier) @method_name
                      parameters: (formal_parameters) @params
                      body: (statement_block) @body))) @method_def
                """
        
        elif element_type.lower() in ['property', 'prop']:
            if parent_name and element_name:
                query_template = """
                (class_declaration
                  name: (type_identifier) @class_name
                  (#eq? @class_name "{parent}")
                  body: (class_body
                    (public_field_definition
                      name: (property_identifier) @property_name
                      (#eq? @property_name "{name}")))) @property_def
                """
            elif element_name:
                query_template = """
                (class_declaration
                  name: (type_identifier) @class_name
                  body: (class_body
                    (public_field_definition
                      name: (property_identifier) @property_name
                      (#eq? @property_name "{name}")))) @property_def
                """
            elif parent_name:
                query_template = """
                (class_declaration
                  name: (type_identifier) @class_name
                  (#eq? @class_name "{parent}")
                  body: (class_body
                    (public_field_definition
                      name: (property_identifier) @property_name))) @property_def
                """
            else:
                query_template = """
                (class_declaration
                  name: (type_identifier) @class_name
                  body: (class_body
                    (public_field_definition
                      name: (property_identifier) @property_name))) @property_def
                """
        
        elif element_type.lower() in ['interface']:
            if element_name:
                query_template = """
                (interface_declaration
                  name: (type_identifier) @interface_name
                  (#eq? @interface_name "{name}")
                  body: (object_type) @body) @interface_decl
                """
            else:
                query_template = """
                (interface_declaration
                  name: (type_identifier) @interface_name
                  body: (object_type) @body) @interface_decl
                """
        
        elif element_type.lower() in ['import']:
            query_template = """
            (import_statement) @import
            """
        
        elif element_type.lower() in ['enum']:
            if element_name:
                query_template = """
                (enum_declaration
                  name: (type_identifier) @enum_name
                  (#eq? @enum_name "{name}")
                  body: (enum_body) @body) @enum_decl
                """
            else:
                query_template = """
                (enum_declaration
                  name: (type_identifier) @enum_name
                  body: (enum_body) @body) @enum_decl
                """
        
        elif element_type.lower() in ['type', 'type_alias']:
            if element_name:
                query_template = """
                (type_alias_declaration
                  name: (type_identifier) @type_name
                  (#eq? @type_name "{name}")
                  value: (_) @value) @type_alias
                """
            else:
                query_template = """
                (type_alias_declaration
                  name: (type_identifier) @type_name
                  value: (_) @value) @type_alias
                """
        
        # Format the query template with element_name and parent_name if provided
        format_args = {}
        if element_name:
            format_args['name'] = element_name
        if parent_name:
            format_args['parent'] = parent_name
        
        # Format the query string with the provided names
        query_string = query_template.format(**format_args) if format_args else query_template
        
        return query_string
