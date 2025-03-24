from abc import ABC, abstractmethod
from typing import Optional

from codehem.models.enums import CodeElementType

class AbstractManipulator(ABC):
    @property
    @abstractmethod
    def element_type(self) -> CodeElementType:
        """Get the element type this manipulator handles."""
        pass
        
    @abstractmethod
    def replace_element(self, original_code: str, element_name: str, 
                       new_element: str, language_code: str, 
                       parent_name: Optional[str] = None) -> str:
        """Replace element in code"""
        pass
        
    @abstractmethod
    def add_element(self, original_code: str, new_element: str, 
                   language_code: str, parent_name: Optional[str] = None) -> str:
        """Add element to code"""
        pass
        
    @abstractmethod
    def remove_element(self, original_code: str, element_name: str,
                      language_code: str, parent_name: Optional[str] = None) -> str:
        """Remove element from code"""
        pass