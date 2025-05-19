"""
AST Handler for CodeHem providing a unified interface for tree-sitter operations.
"""
import logging
import traceback
from functools import lru_cache
from typing import Tuple, List, Any, Optional, Dict, Callable

from codehem.core.utils.hashing import sha1_code


from tree_sitter import Node, Query

logger = logging.getLogger(__name__)

class ASTHandler:
    """
    Handles Abstract Syntax Tree operations using tree-sitter.
    Provides a unified interface for querying and navigating syntax trees.
    """

    def __init__(self, language_code: str, parser, language):
        """
        Initialize the AST handler.
        
        Args:
            language_code: Language code (e.g., 'python', 'typescript')
            parser: Tree-sitter parser for the language
            language: Tree-sitter language object
        """
        self.language_code = language_code
        self.parser = parser
        self.language = language

    @lru_cache(maxsize=128)
    def _parse_cached(self, code_hash: str, code: str) -> Tuple[Node, bytes]:
        """Internal cached parse implementation."""
        code_bytes = code.encode("utf8")
        tree = self.parser.parse(code_bytes)
        return (tree.root_node, code_bytes)

    def parse(self, code: str) -> Tuple[Node, bytes]:
        """
        Parse source code into an AST. Results are cached using an LRU cache
        keyed by the SHA1 hash of ``code``.

        Args:
            code: Source code as string

        Returns:
            Tuple of (root_node, code_bytes)
        """
        code_hash = sha1_code(code)
        return self._parse_cached(code_hash, code)

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
            query = Query(self.language, query_string)
            raw_captures = query.captures(root, lambda n: self.get_node_text(n, code_bytes))
            return self.process_captures(raw_captures)
        except Exception as e:
            logger.error(
                "Error executing query: %s\nquery_string: %s\n%s",
                e,
                query_string,
                traceback.format_exc(),
            )
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(root)
            return []

    @staticmethod
    def process_captures(captures: Any) -> List[Tuple[Node, str]]:
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
                logger.error("Unexpected captures type: %s", type(captures))
        except Exception as e:
            logger.error("Error processing captures: %s", e)
        return result

    def find_parent_of_type(self, node: Node, parent_type: str) -> Optional[Node]:
        """
        Find the nearest parent node matching the specified type or one of the specified types.
        Args:
            node: Starting node
            parent_types: A single type string or a list of type strings to find.

        Returns:
            Parent node or None if not found
        """
        if not node:
            return None

        if isinstance(parent_type, str):
            target_types = {parent_type}
        elif isinstance(parent_type, list):
            target_types = set(parent_type)
        else:
            logger.error(
                "Invalid parent_types format in find_parent_of_type: %s. Expected str or List[str].",
                type(parent_type),
            )
            return None

        current = node.parent
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