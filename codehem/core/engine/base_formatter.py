"""
Base formatter interface for CodeHem language modules.
"""
from abc import ABC, abstractmethod

class BaseFormatter(ABC):
    """
    Base class for language-specific code formatters.
    Defines the interface for formatting code elements.
    """
    
    def __init__(self, indent_size: int = 4):
        """
        Initialize the formatter.
        
        Args:
            indent_size: Number of spaces per indentation level
        """
        self.indent_size = indent_size
        self.indent_string = ' ' * indent_size
    
    @abstractmethod
    def format_element(self, element_type: str, code: str) -> str:
        """
        Format a code element of the specified type.
        
        Args:
            element_type: Type of the element to format
            code: Code to format
            
        Returns:
            Formatted code
        """
        pass
    
    @abstractmethod
    def apply_indentation(self, code: str, base_indent: str) -> str:
        """
        Apply indentation to the code.
        
        Args:
            code: Code to indent
            base_indent: Base indentation to apply
            
        Returns:
            Indented code
        """
        pass
    
    @abstractmethod
    def get_indentation(self, line: str) -> str:
        """
        Get the indentation from a line.
        
        Args:
            line: Line to analyze
            
        Returns:
            Indentation string
        """
        pass