"""
Definition of the extraction protocol for language-agnostic extraction capabilities.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Protocol, runtime_checkable

@runtime_checkable
class ExtractionProtocol(Protocol):
    """
    Protocol defining the interface for extraction operations.
    Any class that implements these methods is considered to satisfy the protocol.
    """
    
    def extract_functions(self, code: str) -> List[Dict]:
        """Extract functions from the provided code."""
        ...
    
    def extract_classes(self, code: str) -> List[Dict]:
        """Extract classes from the provided code."""
        ...
    
    def extract_methods(self, code: str, class_name: Optional[str] = None) -> List[Dict]:
        """Extract methods from the provided code, optionally filtering by class."""
        ...
    
    def extract_imports(self, code: str) -> List[Dict]:
        """Extract imports from the provided code."""
        ...
    
    def extract_all(self, code: str) -> Dict[str, List[Dict]]:
        """Extract all code elements from the provided code."""
        ...