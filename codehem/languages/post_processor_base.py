# NEW FILE: Base class for post-processors, moved from core
from abc import ABC, abstractmethod
from typing import List, Dict, Any, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from codehem.models.code_element import CodeElement

class BaseExtractionPostProcessor(ABC):
    """
    Abstract base class for language-specific extraction post-processors.
    Responsible for transforming raw extraction dicts into structured CodeElement objects.
    """

    @abstractmethod
    def process_imports(self, raw_imports: List[Dict]) -> List[Any]:
        """
        Processes raw import data.
        
        Args:
            raw_imports: List of raw import dictionaries
            
        Returns:
            List of CodeElement objects representing imports
        """
        pass

    @abstractmethod
    def process_functions(self, raw_functions: List[Dict], all_decorators: List[Dict] = None) -> List[Any]:
        """
        Processes raw standalone function data.
        Optionally receives all decorators found in the file.
        
        Args:
            raw_functions: List of raw function dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing functions
        """
        pass

    @abstractmethod
    def process_classes(self, raw_classes: List[Dict], members: List[Dict], static_props: List[Dict], properties: List[Dict] = None, all_decorators: List[Dict] = None) -> List[Any]:
        """
        Processes raw class/interface data, associating members and properties.
        Optionally receives all decorators found in the file.
        
        Args:
            raw_classes: List of raw class dictionaries
            members: List of raw member dictionaries (methods, getters, setters)
            static_props: List of raw static property dictionaries
            properties: Optional list of raw property dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing classes with their members
        """
        pass
