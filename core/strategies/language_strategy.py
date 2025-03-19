"""
Strategy pattern for language-specific operations.
"""
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Any, Optional
from tree_sitter import Node

class LanguageStrategy(ABC):
    """
    Abstract strategy for language-specific operations.
    Concrete implementations should be created for each supported language.
    """
    
    @property
    @abstractmethod
    def language_code(self) -> str:
        """Return the language code (e.g., 'python', 'typescript')."""
        pass
    
    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Return the file extensions for this language (e.g., ['.py'], ['.ts', '.tsx'])."""
        pass
    
    @abstractmethod
    def is_class_definition(self, line: str) -> bool:
        """
        Check if a line of code is a class definition.
        
        Args:
            line: Line of code to check
            
        Returns:
            True if the line is a class definition, False otherwise
        """
        pass
    
    @abstractmethod
    def is_function_definition(self, line: str) -> bool:
        """
        Check if a line of code is a function definition.
        
        Args:
            line: Line of code to check
            
        Returns:
            True if the line is a function definition, False otherwise
        """
        pass
    
    @abstractmethod
    def is_method_definition(self, line: str) -> bool:
        """
        Check if a line of code is a method definition.
        
        Args:
            line: Line of code to check
            
        Returns:
            True if the line is a method definition, False otherwise
        """
        pass
    
    @abstractmethod
    def extract_method_name(self, method_line: str) -> Optional[str]:
        """
        Extract the method name from a method definition line.
        
        Args:
            method_line: Method definition line
            
        Returns:
            Method name or None if not found
        """
        pass
    
    @abstractmethod
    def extract_class_name(self, class_line: str) -> Optional[str]:
        """
        Extract the class name from a class definition line.
        
        Args:
            class_line: Class definition line
            
        Returns:
            Class name or None if not found
        """
        pass
    
    @abstractmethod
    def extract_function_name(self, function_line: str) -> Optional[str]:
        """
        Extract the function name from a function definition line.
        
        Args:
            function_line: Function definition line
            
        Returns:
            Function name or None if not found
        """
        pass
    
    @abstractmethod
    def fix_special_characters(self, content: str, xpath: str) -> Tuple[str, str]:
        """
        Fix special characters in method names and xpaths.
        
        Args:
            content: Code content
            xpath: XPath string
            
        Returns:
            Tuple of (updated_content, updated_xpath)
        """
        pass
    
    @abstractmethod
    def adjust_indentation(self, code: str, indent_level: int) -> str:
        """
        Adjust the indentation of code to the specified level.
        
        Args:
            code: Code to adjust
            indent_level: Target indentation level
            
        Returns:
            Code with adjusted indentation
        """
        pass
    
    @abstractmethod
    def get_default_indentation(self) -> str:
        """
        Get the default indentation string for this language.
        
        Returns:
            Default indentation string
        """
        pass
    
    @abstractmethod
    def is_method_of_class(self, method_node: Node, class_name: str, code_bytes: bytes) -> bool:
        """
        Check if a method belongs to a specific class.
        
        Args:
            method_node: Method node
            class_name: Class name to check
            code_bytes: Source code as bytes
            
        Returns:
            True if the method belongs to the class, False otherwise
        """
        pass