"""
AST Handler for CodeHem providing a unified interface for tree-sitter operations.
"""
from typing import Tuple, List, Any, Optional, Dict

from rich.console import Console
from tree_sitter import Node, Query

from core.caching import cached
from core.languages import get_parser, LANGUAGES


class ASTHandler:
    """
    Handles Abstract Syntax Tree operations using tree-sitter.
    Provides a unified interface for querying and navigating syntax trees.
    """
    
    def __init__(self, language: str):
        self.language = language
        self.parser = get_parser(language)
        self.console = Console()
    
    @cached
    def parse(self, code: str) -> Tuple[Node, bytes]:
        """
        Parse source code into an AST.
        
        Args:
            code: Source code as string
            
        Returns:
            Tuple of (root_node, code_bytes)
        """
        code_bytes = code.encode('utf8')
        tree = self.parser.parse(code_bytes)
        return (tree.root_node, code_bytes)
    
    def get_node_text(self, node: Node, code_bytes: bytes) -> str:
        """
        Get the text content of a node.
        
        Args:
            node: Tree-sitter node
            code_bytes: Source code as bytes
            
        Returns:
            String content of the node
        """
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')
    
    def get_node_range(self, node: Node) -> Tuple[int, int]:
        """
        Get the line range of a node.
        
        Args:
            node: Tree-sitter node
            
        Returns:
            Tuple of (start_line, end_line) in 1-indexed form
        """
        return (node.start_point[0] + 1, node.end_point[0] + 1)
    
    @cached
    def execute_query(self, query_string: str, root: Node, code_bytes: bytes) -> List[Tuple[Node, str]]:
        """
        Execute a tree-sitter query and process the results.
        
        Args:
            query_string: Tree-sitter query string
            root: Root node to query from
            code_bytes: Source code as bytes
            
        Returns:
            List of (node, capture_name) tuples
        """

        try:
            query = Query(LANGUAGES[self.language], query_string)
            raw_captures = query.captures(root, lambda n: self.get_node_text(n, code_bytes))
            return self._process_captures(raw_captures)
        except Exception as e:
            self.console.print(f"[yellow]Error executing query: {e}[/yellow]")
            return []
    
    def _process_captures(self, captures: Any) -> List[Tuple[Node, str]]:
        """
        Process tree-sitter query captures into a normalized format.
        
        Args:
            captures: Raw captures from tree-sitter query
            
        Returns:
            List of (node, capture_name) tuples
        """
        result = []
        try:
            if isinstance(captures, dict):
                for cap_name, nodes in captures.items():
                    if isinstance(nodes, list):
                        for node in nodes:
                            result.append((node, cap_name))
                    else:
                        result.append((nodes, cap_name))
            elif isinstance(captures, list):
                result = captures
            else:
                self.console.print(f'[yellow]Unexpected captures type: {type(captures)}[/yellow]')
        except Exception as e:
            self.console.print(f'[yellow]Error processing captures: {e}[/yellow]')
            import traceback
            self.console.print(f'[dim]{traceback.format_exc()}[/dim]')
        return result
    
    def find_parent_of_type(self, node: Node, parent_type: str) -> Optional[Node]:
        """
        Find the nearest parent node of a specified type.
        
        Args:
            node: Starting node
            parent_type: Type of parent to find
            
        Returns:
            Parent node or None if not found
        """
        current = node
        while current is not None:
            if current.type == parent_type:
                return current
            current = current.parent
        return None
    
    def find_child_by_field_name(self, node: Node, field_name: str) -> Optional[Node]:
        """
        Find a child node by field name.
        
        Args:
            node: Parent node
            field_name: Field name to find
            
        Returns:
            Child node or None if not found
        """
        if node is None:
            return None
        return node.child_by_field_name(field_name)
    
    def find_first_child_of_type(self, node: Node, child_type: str) -> Optional[Node]:
        """
        Find the first child node of a specified type.
        
        Args:
            node: Parent node
            child_type: Type of child to find
            
        Returns:
            Child node or None if not found
        """
        if node is None:
            return None
            
        for child in node.children:
            if child.type == child_type:
                return child
        return None
    
    def is_node_of_type(self, node: Node, node_type: str) -> bool:
        """
        Check if a node is of a specified type.
        
        Args:
            node: Node to check
            node_type: Type to check for
            
        Returns:
            True if node is of specified type, False otherwise
        """
        return node is not None and node.type == node_type
    
    def get_indentation(self, line: str) -> str:
        """
        Extract the whitespace indentation from the beginning of a line.
        
        Args:
            line: The line to extract indentation from
            
        Returns:
            The indentation string (spaces, tabs, etc.)
        """
        import re
        match = re.match('^(\\s*)', line)
        return match.group(1) if match else ''
    
    def apply_indentation(self, content: str, base_indent: str) -> str:
        """
        Apply consistent indentation to a block of content.
        
        Args:
            content: The content to indent
            base_indent: The base indentation to apply
            
        Returns:
            The indented content
        """
        lines = content.splitlines()
        result = []
        for line in lines:
            if line.strip():
                result.append(base_indent + line.lstrip())
            else:
                result.append('')
        return '\n'.join(result)

    @cached
    def find_by_query(self, code: str, query_string: str) -> List[Dict[str, Any]]:
        """
        Find nodes matching a query and return structured results.
        
        Args:
            code: Source code to search
            query_string: Tree-sitter query string
            
        Returns:
            List of dictionaries with captured nodes and metadata
        """
        (root, code_bytes) = self.parse(code)
        captures = self.execute_query(query_string, root, code_bytes)
        
        # Group captures by unique patterns
        results = []
        current_match = {}
        current_id = None
        
        for node, capture_name in captures:
            # Use node.id as a way to group related captures
            parent = self.find_parent_of_type(node, "function_definition") or \
                    self.find_parent_of_type(node, "class_definition") or \
                    self.find_parent_of_type(node, "method_definition")
            
            match_id = parent.id if parent else node.id
            
            if current_id is None:
                current_id = match_id
                
            if match_id != current_id:
                # We've started a new match
                if current_match:
                    results.append(current_match.copy())
                current_match = {}
                current_id = match_id
            
            # Add this capture to the current match
            current_match[capture_name] = {
                'node': node,
                'text': self.get_node_text(node, code_bytes),
                'range': self.get_node_range(node)
            }
        
        # Add the last match if there is one
        if current_match:
            results.append(current_match)
            
        return results