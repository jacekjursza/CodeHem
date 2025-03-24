"""
Base extraction service interface for CodeHem language modules.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ... import CodeElementsResult


class BaseExtractionService(ABC):
    """
    Base class for language-specific extraction services.
    Defines the interface for extracting code elements from source code.
    """

    def __init__(self, finder, strategy):
        """
        Initialize the extraction service.
        
        Args:
            finder: Language-specific finder
            strategy: Language-specific strategy
        """
        self.finder = finder
        self.strategy = strategy

    @abstractmethod
    def extract_code_elements(self, code: str) -> CodeElementsResult:
        """
        Extract code elements from source code.
        
        Args:
            code: Source code as string
            
        Returns:
            CodeElementsResult containing extracted elements
        """
        pass

    @abstractmethod
    def extract_imports(self, code: str, result: CodeElementsResult) -> None:
        """
        Extract imports from code and add to result.
        
        Args:
            code: Source code as string
            result: CodeElementsResult to add imports to
        """
        pass

    @abstractmethod
    def extract_classes(self, code: str, code_bytes: bytes, result: CodeElementsResult) -> None:
        """
        Extract classes from code and add to result.
        
        Args:
            code: Source code as string
            code_bytes: Source code as bytes
            result: CodeElementsResult to add classes to
        """
        pass

    @abstractmethod
    def extract_functions(self, code: str, code_bytes: bytes, result: CodeElementsResult) -> None:
        """
        Extract standalone functions from code and add to result.
        
        Args:
            code: Source code as string
            code_bytes: Source code as bytes
            result: CodeElementsResult to add functions to
        """
        pass