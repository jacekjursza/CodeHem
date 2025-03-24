"""
Base language service interface for CodeHem language modules.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from ..models import CodeElementType
from ... import CodeElementsResult


class BaseLanguageService(ABC):
    """
    Base class for language-specific services.
    Defines the interface for language-specific operations and combines finder, formatter, and manipulator.
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
        Check if this language service can handle the given code.
        
        Args:
            code: Source code as string
            
        Returns:
            True if this language service can handle the code, False otherwise
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
    def extract(self, code: str) -> CodeElementsResult:
        """
        Extract code elements from the source code.
        
        Args:
            code: Source code as string
            
        Returns:
            CodeElementsResult containing extracted elements
        """
        pass
    
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
    def resolve_xpath(self, xpath: str) -> Tuple[str, Optional[str]]:
        """
        Resolve an XPath expression to element name and parent name.
        
        Args:
            xpath: XPath expression (e.g., 'ClassName.method_name')
            
        Returns:
            Tuple of (name, parent_name)
        """
        pass