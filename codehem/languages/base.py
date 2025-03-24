"""
Base interfaces for language implementations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple

from codehem.models.code_element import CodeElementsResult


class BaseLanguageDetector(ABC):
    """Base class for language detection."""
    
    @property
    @abstractmethod
    def language_code(self) -> str:
        """Get the language code this detector is for."""
        pass
    
    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Get file extensions associated with this language."""
        pass
    
    @abstractmethod
    def detect_confidence(self, code: str) -> float:
        """
        Calculate confidence level that the code is written in this language.
        
        Args:
            code: Source code to analyze
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        pass

class BaseLanguageService(ABC):
    """Base interface for language services."""

    @property
    @abstractmethod
    def language_code(self) -> str:
        """Get the language code this service is for."""
        pass

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Get file extensions associated with this language."""
        pass

    @property
    def finder(self):
        """Get the finder for this language service."""
        # This will be implemented by concrete classes
        pass

    @abstractmethod
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of code element.

        Args:
        code: The code to analyze

        Returns:
        Element type string
        """
        pass

    @abstractmethod
    def extract(self, code: str) -> 'CodeElementsResult':
        """
        Extract code elements from the source code.

        Args:
        code: Source code as string

        Returns:
        CodeElementsResult containing extracted elements
        """
        pass

    @abstractmethod
    def upsert_element(self, original_code: str, element_type: str, name: str,
        new_code: str, parent_name: Optional[str]=None) -> str:
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
    def extract(self, code: str) -> 'CodeElementsResult':
        """
        Extract code elements from the source code.

        Args:
        code: Source code as string

        Returns:
        CodeElementsResult containing extracted elements
        """
        pass

    @abstractmethod
    def upsert_element(self, original_code: str, element_type: str, name: str,
        new_code: str, parent_name: Optional[str]=None) -> str:
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
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of code element.

        Args:
        code: The code to analyze

        Returns:
        Element type string
        """
        pass

    @abstractmethod
    def extract(self, code: str) -> 'CodeElementsResult':
        """
        Extract code elements from the source code.

        Args:
        code: Source code as string

        Returns:
        CodeElementsResult containing extracted elements
        """
        pass

    @abstractmethod
    def upsert_element(self, original_code: str, element_type: str, name: str,
        new_code: str, parent_name: Optional[str]=None) -> str:
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

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Get file extensions associated with this language."""
        pass

    @property
    def finder(self):
        """Get the finder for this language service."""
        # This will be implemented by concrete classes
        pass

    @abstractmethod
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of code element.

        Args:
        code: The code to analyze

        Returns:
        Element type string
        """
        pass

    @abstractmethod
    def extract(self, code: str) -> 'CodeElementsResult':
        """
        Extract code elements from the source code.

        Args:
        code: Source code as string

        Returns:
        CodeElementsResult containing extracted elements
        """
        pass

    @abstractmethod
    def upsert_element(self, original_code: str, element_type: str, name: str,
        new_code: str, parent_name: Optional[str]=None) -> str:
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

    @property
    def finder(self):
        """Get the finder for this language service."""
        # This will be implemented by concrete classes
        pass

    @abstractmethod
    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of code element.

        Args:
        code: The code to analyze

        Returns:
        Element type string
        """
        pass

    @abstractmethod
    def extract(self, code: str) -> 'CodeElementsResult':
        """
        Extract code elements from the source code.

        Args:
        code: Source code as string

        Returns:
        CodeElementsResult containing extracted elements
        """
        pass

    @abstractmethod
    def upsert_element(self, original_code: str, element_type: str, name: str,
        new_code: str, parent_name: Optional[str]=None) -> str:
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
