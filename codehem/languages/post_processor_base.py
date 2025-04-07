# NEW FILE: Base class for post-processors, moved from core
from abc import ABC, abstractmethod
from typing import List, Dict
from codehem.models.code_element import CodeElement

class BaseExtractionPostProcessor(ABC):
    """
    Abstract base class for language-specific extraction post-processors.
    Responsible for transforming raw extraction dicts into structured CodeElement objects.
    """

    @abstractmethod
    def process_imports(self, raw_imports: List[Dict]) -> List[CodeElement]:
        pass

    @abstractmethod
    @abstractmethod
    def process_functions(self, raw_functions: List[Dict], all_decorators: List[Dict] = None) -> List[CodeElement]:
        """
        Processes raw standalone function data.
        Optionally receives all decorators found in the file.
        """
        pass

    @abstractmethod
    @abstractmethod
    def process_classes(self, raw_classes: List[Dict], members: List[Dict], static_props: List[Dict], properties: List[Dict] = None, all_decorators: List[Dict] = None) -> List[CodeElement]:
        """
        Processes raw class/interface data, associating members and properties.
        Optionally receives all decorators found in the file.
        """
        pass
