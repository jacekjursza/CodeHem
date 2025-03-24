"""
Base language finder interface for CodeHem language modules.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from tree_sitter import Node
from ..models import CodeElementType
from .xpath_parser import XPathParser

class BaseLanguageFinder(ABC):
    """
    Base class for language-specific code finders.
    Combines element finding and code analysis capabilities.
    """

    @property
    @abstractmethod
    def language_code(self) -> str:
        """Get the language code (e.g., 'python', 'typescript')."""
        pass

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Get file extensions supported by this language."""
        pass

    @property
    @abstractmethod
    def supported_element_types(self) -> List[str]:
        """Get element types supported by this language."""
        pass

    @abstractmethod
    def can_handle(self, code: str) -> bool:
        """
        Check if this finder can handle the given code.
        
        Args:
            code: Source code as string
            
        Returns:
            True if this finder can handle the code, False otherwise
        """
        pass

    @abstractmethod
    def get_confidence_score(self, code: str) -> float:
        """
        Calculate a confidence score for how likely the code is of this language type.
        
        Args:
            code: Source code as string
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        pass

    @abstractmethod
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of element in the code.
        
        Args:
            code: Code to analyze
            
        Returns:
            Element type string
        """
        pass

    @abstractmethod
    def find_element(self, code: str, element_type: str, name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
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
        pass
        
    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        """
        Find an element in the code using an XPath-like expression.
        
        Args:
            code: Source code as string
            xpath: XPath-like expression (e.g., 'ClassName.method_name')
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        # Parse the XPath expression
        element_name, parent_name, element_type = XPathParser.get_element_info(xpath)
        
        # If we couldn't extract necessary info, return not found
        if not element_name and not element_type:
            return (0, 0)
            
        # Handle special cases
        if element_type == CodeElementType.IMPORT.value and not element_name:
            return self.find_element(code, element_type, "", None)
            
        # If we have both name and type, use them
        if element_name and element_type:
            return self.find_element(code, element_type, element_name, parent_name)
            
        # If we have only a name but no type, we need to try different element types
        if element_name and not element_type:
            # Try different element types based on context
            if parent_name:
                # If we have a parent, try class member types
                element_types = [
                    CodeElementType.METHOD.value,
                    CodeElementType.PROPERTY.value,
                    CodeElementType.PROPERTY_GETTER.value,
                    CodeElementType.PROPERTY_SETTER.value,
                    CodeElementType.STATIC_PROPERTY.value
                ]
            else:
                # If no parent, try top-level types
                element_types = [
                    CodeElementType.CLASS.value,
                    CodeElementType.FUNCTION.value,
                    CodeElementType.INTERFACE.value
                ]
                
            # Try each element type until we find a match
            for type_to_try in element_types:
                result = self.find_element(code, type_to_try, element_name, parent_name)
                if result[0] > 0:
                    return result
                    
        # Not found
        return (0, 0)

    @abstractmethod
    def get_elements_by_type(self, code: str, element_type: str) -> List[Dict[str, Any]]:
        """
        Get all elements of the specified type from the code.
        
        Args:
            code: Source code as string
            element_type: Type of elements to find
            
        Returns:
            List of dictionaries with element information
        """
        pass

    @abstractmethod
    def get_node_content(self, node: Node, code_bytes: bytes) -> str:
        """
        Get the content of a node.
        
        Args:
            node: Tree-sitter node
            code_bytes: Source code as bytes
            
        Returns:
            Content of the node as string
        """
        pass

    @abstractmethod
    def get_node_range(self, node: Node) -> Tuple[int, int]:
        """
        Get the line range of a node.
        
        Args:
            node: Tree-sitter node
            
        Returns:
            Tuple of (start_line, end_line)
        """
        pass

    @abstractmethod
    def is_class_definition(self, node: Optional[Node], code_bytes: bytes) -> bool:
        """
        Check if a node is a class definition.
        
        Args:
            node: Tree-sitter node
            code_bytes: Source code as bytes
            
        Returns:
            True if the node is a class definition, False otherwise
        """
        pass

    @abstractmethod
    def is_function_definition(self, node: Optional[Node], code_bytes: bytes) -> bool:
        """
        Check if a node is a function definition.
        
        Args:
            node: Tree-sitter node
            code_bytes: Source code as bytes
            
        Returns:
            True if the node is a function definition, False otherwise
        """
        pass

    @abstractmethod
    def is_method_definition(self, node: Optional[Node], code_bytes: bytes) -> bool:
        """
        Check if a node is a method definition.
        
        Args:
            node: Tree-sitter node
            code_bytes: Source code as bytes
            
        Returns:
            True if the node is a method definition, False otherwise
        """
        pass

    @abstractmethod
    def determine_element_type(self, node: Node, code_bytes: bytes) -> str:
        """
        Determine the element type from a node.
        
        Args:
            node: Tree-sitter node
            code_bytes: Source code as bytes
            
        Returns:
            Element type string from CodeElementType
        """
        pass

    @abstractmethod
    def get_imports(self, code: str) -> Dict[str, Any]:
        """
        Get imports from code.
        
        Args:
            code: Source code as string
            
        Returns:
            Dictionary with import information
        """
        pass