"""
Base manipulator interface for CodeHem language modules.
"""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Optional


class BaseManipulator(ABC):
    """
    Base class for language-specific code manipulators.
    Defines the interface for manipulating code elements.
    """
    
    @abstractmethod
    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str] = None) -> str:
        """
        Add or replace an element in the code.
        
        Args:
            original_code: Original source code
            element_type: Type of element to add/replace
            name: Name of the element
            new_code: New content for the element
            parent_name: Name of parent element (e.g., class name for methods)
            
        Returns:
            Modified code
        """
        pass
    
    @abstractmethod
    def remove_element(self, original_code: str, element_type: str, name: str, parent_name: Optional[str] = None) -> str:
        """
        Remove an element from the code.
        
        Args:
            original_code: Original source code
            element_type: Type of element to remove
            name: Name of the element to remove
            parent_name: Name of parent element (e.g., class name for methods)
            
        Returns:
            Modified code
        """
        pass
    
    @abstractmethod
    def replace_lines(self, original_code: str, start_line: int, end_line: int, new_content: str) -> str:
        """
        Replace specific lines in the code.
        
        Args:
            original_code: Original source code
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)
            new_content: New content to replace the lines with
            
        Returns:
            Modified code
        """
        pass
    
    @abstractmethod
    def fix_special_characters(self, content: str, xpath: str) -> Tuple[str, str]:
        """
        Fix special characters in content and xpath.
        
        Args:
            content: Code content
            xpath: XPath expression
            
        Returns:
            Tuple of (fixed_content, fixed_xpath)
        """
        pass