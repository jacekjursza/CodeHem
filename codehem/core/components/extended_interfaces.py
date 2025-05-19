"""
Extended interfaces for CodeHem component architecture.

This module defines additional interfaces for the language component architecture
of CodeHem, extending the core interfaces defined in the interfaces module.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

from codehem.core.components.interfaces import (
    ICodeParser, ISyntaxTreeNavigator, IElementExtractor, 
    IPostProcessor, IExtractionOrchestrator
)
from codehem.models.enums import CodeElementType

if TYPE_CHECKING:
    from codehem.models.code_element import CodeElement, CodeElementsResult
    from codehem.core.formatting.formatter import BaseFormatter


class IManipulator(ABC):
    """
    Interface for code manipulation components.
    
    Responsible for modifying source code by adding, removing, or replacing
    specific code elements while preserving syntax and formatting.
    """
    
    @abstractmethod
    def add_element(self, original_code: str, new_element: str, 
                  parent_name: Optional[str]=None) -> str:
        """
        Add a new element to the code.
        
        Args:
            original_code: The original source code
            new_element: The code for the new element to add
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            The modified source code with the new element added
        """
        pass
    
    @abstractmethod
    def find_element(self, code: str, element_name: str, 
                   parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the code by name and optional parent.
        
        Args:
            code: The source code to search
            element_name: Name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        pass
    
    @abstractmethod
    def replace_element(self, original_code: str, element_name: str, 
                       new_element: str, parent_name: Optional[str]=None) -> str:
        """
        Replace an existing element with a new implementation.
        
        Args:
            original_code: The original source code
            element_name: Name of the element to replace
            new_element: The new code for the element
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            The modified source code with the element replaced
        """
        pass
    
    @abstractmethod
    def remove_element(self, original_code: str, element_name: str, 
                      parent_name: Optional[str]=None) -> str:
        """
        Remove an element from the code.
        
        Args:
            original_code: The original source code
            element_name: Name of the element to remove
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            The modified source code with the element removed
        """
        pass
    
    @abstractmethod
    def format_element(self, element_code: str, indent_level: int=0) -> str:
        """
        Format an element's code using the appropriate formatter and indentation.
        
        Args:
            element_code: The code of the element to format
            indent_level: The indentation level to apply
            
        Returns:
            The formatted element code
        """
        pass


class IFormatter(ABC):
    """
    Interface for code formatting components.
    
    Responsible for formatting code elements according to language-specific
    style guidelines and indentation rules.
    """
    
    @abstractmethod
    def format_code(self, code: str) -> str:
        """
        Format general code according to language-specific rules.
        
        Args:
            code: The code to format
            
        Returns:
            The formatted code
        """
        pass
    
    @abstractmethod
    def format_element(self, element_type: str, code: str) -> str:
        """
        Format a specific code element based on its type.
        
        Args:
            element_type: The type of the element (e.g., 'class', 'method', 'function')
            code: The code to format
            
        Returns:
            The formatted code
        """
        pass
    
    @abstractmethod
    def apply_indentation(self, code: str, base_indent: str) -> str:
        """
        Apply a base indentation level to all lines in the code.
        
        Args:
            code: The code to indent
            base_indent: The base indentation to apply (e.g., '    ', '\t')
            
        Returns:
            The indented code
        """
        pass
    
    @abstractmethod
    def get_indentation(self, line: str) -> str:
        """
        Extract the indentation from a line of code.
        
        Args:
            line: The line to extract indentation from
            
        Returns:
            The indentation string
        """
        pass
    
    @abstractmethod
    def normalize_indentation(self, code: str, target_indent: str='') -> str:
        """
        Normalize indentation by reducing all lines to a common baseline,
        then applying the target indentation.
        
        Args:
            code: The code to normalize
            target_indent: The target indentation to apply
            
        Returns:
            The code with normalized indentation
        """
        pass


class ILanguageService(ABC):
    """
    Interface for language-specific service components.
    
    Responsible for providing a unified interface to all language-specific
    functionality and coordinating the use of various components.
    """
    
    @abstractmethod
    def get_parser(self) -> ICodeParser:
        """
        Get the language-specific parser.
        
        Returns:
            The parser component for this language
        """
        pass
    
    @abstractmethod
    def get_navigator(self) -> ISyntaxTreeNavigator:
        """
        Get the language-specific syntax tree navigator.
        
        Returns:
            The navigator component for this language
        """
        pass
    
    @abstractmethod
    def get_extractor(self) -> IElementExtractor:
        """
        Get the language-specific element extractor.
        
        Returns:
            The extractor component for this language
        """
        pass
    
    @abstractmethod
    def get_post_processor(self) -> IPostProcessor:
        """
        Get the language-specific post-processor.
        
        Returns:
            The post-processor component for this language
        """
        pass
    
    @abstractmethod
    def get_orchestrator(self) -> IExtractionOrchestrator:
        """
        Get the language-specific extraction orchestrator.
        
        Returns:
            The orchestrator component for this language
        """
        pass
    
    @abstractmethod
    def get_manipulator(self, element_type: Union[str, CodeElementType]) -> IManipulator:
        """
        Get the language-specific manipulator for a given element type.
        
        Args:
            element_type: The type of element to get a manipulator for
            
        Returns:
            The manipulator component for this language and element type
        """
        pass
    
    @abstractmethod
    def get_formatter(self) -> IFormatter:
        """
        Get the language-specific formatter.
        
        Returns:
            The formatter component for this language
        """
        pass
    
    @abstractmethod
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of the primary element in a code snippet.
        
        Args:
            code: The code snippet to analyze
            
        Returns:
            The detected element type
        """
        pass
    
    @abstractmethod
    def extract(self, code: str) -> 'CodeElementsResult':
        """
        Extract all code elements from the provided code.
        
        Args:
            code: The source code to extract from
            
        Returns:
            A CodeElementsResult containing all extracted elements
        """
        pass
    
    @abstractmethod
    def find_element(self, code: str, element_type: str, 
                   element_name: Optional[str]=None, 
                   parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the code based on type, name, and parent.
        
        Args:
            code: The source code to search
            element_type: The type of element to find
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        pass
    
    @abstractmethod
    def get_text_by_xpath(self, code: str, xpath: str) -> str:
        """
        Get the text of an element identified by an XPath expression.
        
        Args:
            code: The source code to search
            xpath: The XPath expression identifying the element
            
        Returns:
            The text of the element
        """
        pass
    
    @property
    @abstractmethod
    def language_code(self) -> str:
        """
        Get the language code for this service.
        
        Returns:
            The language code (e.g., 'python', 'typescript')
        """
        pass
    
    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """
        Get the file extensions associated with this language.
        
        Returns:
            List of file extensions (e.g., ['.py'], ['.ts', '.tsx'])
        """
        pass
    
    @property
    @abstractmethod
    def supported_element_types(self) -> List[str]:
        """
        Get the element types supported by this language.
        
        Returns:
            List of supported element type strings
        """
        pass


class ILanguageDetector(ABC):
    """
    Interface for language detection components.
    
    Responsible for detecting the programming language of a code snippet
    based on its syntax and structure.
    """
    
    @abstractmethod
    def detect_confidence(self, code: str) -> float:
        """
        Calculate a confidence score for the code being in this language.
        
        Args:
            code: The code snippet to analyze
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass


class IBaseManipulator(ABC):
    """
    Interface for base manipulator components.
    
    Provides common functionality for all manipulators, regardless of element type.
    """
    
    @property
    @abstractmethod
    def element_type(self) -> CodeElementType:
        """
        Get the element type this manipulator handles.
        
        Returns:
            The CodeElementType enum value
        """
        pass
    
    @property
    @abstractmethod
    def formatter(self) -> 'BaseFormatter':
        """
        Get the formatter used by this manipulator.
        
        Returns:
            The formatter instance
        """
        pass
    
    @abstractmethod
    def get_indentation(self, line: str) -> str:
        """
        Extract the indentation from a line of code.
        
        Args:
            line: The line to extract indentation from
            
        Returns:
            The indentation string
        """
        pass
    
    @abstractmethod
    def apply_indentation(self, content: str, indent: str) -> str:
        """
        Apply indentation to a block of code.
        
        Args:
            content: The content to indent
            indent: The indentation to apply
            
        Returns:
            The indented content
        """
        pass
    
    @abstractmethod
    def replace_lines(self, original_code: str, start_line: int, 
                     end_line: int, new_content: str) -> str:
        """
        Replace a range of lines in the original code with new content.
        
        Args:
            original_code: The original code
            start_line: The start line index (1-based)
            end_line: The end line index (1-based)
            new_content: The new content to insert
            
        Returns:
            The modified code
        """
        pass
