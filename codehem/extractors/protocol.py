"""
Extraction protocol definitions for standardizing extractor interfaces.
"""
from typing import Dict, List, Optional, Protocol, runtime_checkable, Any

@runtime_checkable
class ExtractionProtocol(Protocol):
    """Protocol defining the interface for extraction operations."""
    
    def extract(self, code: str, context: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Extract elements from code."""
        ...
    
    def supports_language(self, language_code: str) -> bool:
        """Check if this extractor supports the given language."""
        ...

@runtime_checkable
class FunctionExtractionProtocol(ExtractionProtocol):
    """Protocol for function extraction."""
    
    def extract_function_by_name(self, code: str, function_name: str) -> Optional[Dict]:
        """Extract a specific function by name."""
        ...

@runtime_checkable
class ClassExtractionProtocol(ExtractionProtocol):
    """Protocol for class extraction."""
    
    def extract_class_by_name(self, code: str, class_name: str) -> Optional[Dict]:
        """Extract a specific class by name."""
        ...

@runtime_checkable
class MethodExtractionProtocol(ExtractionProtocol):
    """Protocol for method extraction."""
    
    def extract_method_by_name(self, code: str, class_name: str, method_name: str) -> Optional[Dict]:
        """Extract a specific method by name."""
        ...