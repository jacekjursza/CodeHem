"""
Interfaces for CodeHem component architecture.

This module defines the core interfaces for the refactored component architecture
of CodeHem. These interfaces provide a contract for implementation classes to follow,
enabling cleaner separation of concerns and better modularity.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from codehem.models.code_element import CodeElement, CodeElementsResult

class ICodeParser(ABC):
    """
    Interface for code parsing components.
    
    Responsible for parsing source code into language-specific syntax trees or other
    intermediate representations that can be used for code analysis and manipulation.
    """
    
    @abstractmethod
    def parse(self, code: str) -> Tuple[Any, bytes]:
        """
        Parse source code into a syntax tree.
        
        Args:
            code: Source code as string
            
        Returns:
            Tuple of (syntax_tree, code_bytes) where syntax_tree is the parsed tree
            and code_bytes is the source code as bytes
        """
        pass
    
    @property
    @abstractmethod
    def language_code(self) -> str:
        """Get the language code this parser is for."""
        pass

class ISyntaxTreeNavigator(ABC):
    """
    Interface for syntax tree navigation components.
    
    Responsible for navigating and querying syntax trees to find specific elements
    or patterns within the code.
    """
    
    @abstractmethod
    def find_element(self, tree: Any, code_bytes: bytes, element_type: str, 
                   element_name: Optional[str]=None, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the syntax tree based on type, name, and parent.
        
        Args:
            tree: The syntax tree to search
            code_bytes: The original code as bytes
            element_type: Type of element to find (e.g., 'function', 'class', 'method')
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        pass
    
    @abstractmethod
    def execute_query(self, tree: Any, code_bytes: bytes, query_string: str) -> List[Tuple[Any, str]]:
        """
        Execute a tree-specific query on the syntax tree.
        
        Args:
            tree: The syntax tree to query
            code_bytes: The original code as bytes
            query_string: The query to execute
            
        Returns:
            List of tuples (node, capture_name) matching the query
        """
        pass
    
    @abstractmethod
    def get_node_text(self, node: Any, code_bytes: bytes) -> str:
        """
        Get the text for a node in the syntax tree.
        
        Args:
            node: The node to get text for
            code_bytes: The original code as bytes
            
        Returns:
            The text of the node
        """
        pass
    
    @abstractmethod
    def get_node_range(self, node: Any) -> Tuple[int, int]:
        """
        Get the line range for a node in the syntax tree.
        
        Args:
            node: The node to get range for
            
        Returns:
            Tuple of (start_line, end_line)
        """
        pass

class IElementExtractor(ABC):
    """
    Interface for code element extraction components.
    
    Responsible for extracting specific code elements (functions, classes, etc.)
    from syntax trees or raw code.
    """
    
    @abstractmethod
    def extract_functions(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract functions from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of function data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_classes(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract classes from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of class data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_methods(self, tree: Any, code_bytes: bytes, 
                      class_name: Optional[str]=None) -> List[Dict]:
        """
        Extract methods from the provided syntax tree, optionally filtering by class.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            class_name: Optional class name to filter by
            
        Returns:
            List of method data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_all(self, tree: Any, code_bytes: bytes) -> Dict[str, List[Dict]]:
        """
        Extract all supported code elements from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            Dictionary of element type to list of element data dictionaries
        """
        pass

class IPostProcessor(ABC):
    """
    Interface for post-processing components.
    
    Responsible for transforming raw extraction dictionaries into structured
    CodeElement objects with proper relationships.
    """
    
    @abstractmethod
    def process_imports(self, raw_imports: List[Dict]) -> List['CodeElement']:
        """
        Process raw import data into CodeElement objects.
        
        Args:
            raw_imports: List of raw import dictionaries
            
        Returns:
            List of CodeElement objects representing imports
        """
        pass
    
    @abstractmethod
    def process_functions(self, raw_functions: List[Dict], 
                        all_decorators: Optional[List[Dict]]=None) -> List['CodeElement']:
        """
        Process raw function data into CodeElement objects.
        
        Args:
            raw_functions: List of raw function dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing functions
        """
        pass
    
    @abstractmethod
    def process_classes(self, raw_classes: List[Dict], members: List[Dict], 
                      static_props: List[Dict], properties: Optional[List[Dict]]=None,
                      all_decorators: Optional[List[Dict]]=None) -> List['CodeElement']:
        """
        Process raw class data into CodeElement objects.
        
        Args:
            raw_classes: List of raw class dictionaries
            members: List of raw member dictionaries (methods, getters, setters)
            static_props: List of raw static property dictionaries
            properties: Optional list of raw property dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing classes with their members
        """
        pass
    
    @abstractmethod
    def process_all(self, raw_elements: Dict[str, List[Dict]]) -> 'CodeElementsResult':
        """
        Process all raw element data into a CodeElementsResult.
        
        Args:
            raw_elements: Dictionary of element type to list of raw element dictionaries
            
        Returns:
            CodeElementsResult containing processed elements
        """
        pass

class IExtractionOrchestrator(ABC):
    """
    Interface for extraction orchestration components.
    
    Responsible for coordinating the extraction process across multiple components.
    """
    
    @abstractmethod
    def extract_all(self, code: str) -> 'CodeElementsResult':
        """
        Extract all code elements from the provided code.
        
        Args:
            code: Source code as string
            
        Returns:
            CodeElementsResult containing extracted elements
        """
        pass
    
    @abstractmethod
    def find_element(self, code: str, element_type: str, 
                   element_name: Optional[str]=None, 
                   parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the code based on type, name, and parent.
        
        Args:
            code: Source code as string
            element_type: Type of element to find (e.g., 'function', 'class', 'method')
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        pass
