"""
Python language service implementation.
"""
from typing import List, Optional, Tuple
import tree_sitter_python
from codehem import CodeElementsResult
from tree_sitter import Language
from codehem.core.engine.languages import get_parser

from .finder import PythonFinder
from .formatter import PythonFormatter
from .manipulator import PythonManipulator
from .extraction_service import PythonExtractionService
from codehem.core.engine.ast_handler import ASTHandler
from codehem.core.engine.base_language_service import BaseLanguageService

PY_LANGUAGE = Language(tree_sitter_python.language())


class PythonLanguageService(BaseLanguageService):
    """
    Python language service implementation.
    """

    def __init__(self):
        """Initialize the Python language service."""

        parser = get_parser("python")

        self.ast_handler = ASTHandler('python', parser, PY_LANGUAGE)
        self.finder = PythonFinder(self.ast_handler)
        self.extraction_service = PythonExtractionService(self.finder, self.finder)
        self.formatter = PythonFormatter()
        self.manipulator = PythonManipulator(self.finder, self.formatter)

    @property
    def language_code(self) -> str:
        """Get the language code."""
        return 'python'

    @property
    def file_extensions(self) -> List[str]:
        """Get file extensions supported by this language."""
        return ['.py']

    @property
    def supported_element_types(self) -> List[str]:
        """Get element types supported by this language."""
        return self.finder.supported_element_types

    def can_handle(self, code: str) -> bool:
        """
        Check if this language service can handle the given code.
        
        Args:
            code: Source code as string
            
        Returns:
            True if this language service can handle the code, False otherwise
        """
        return self.finder.can_handle(code)

    def get_confidence_score(self, code: str) -> float:
        """
        Calculate a confidence score for how likely the code is Python.
        
        Args:
            code: Source code as string
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        return self.finder.get_confidence_score(code)

    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of element in the code.

        Args:
            code: Code to analyze

        Returns:
            Element type string
        """
        return self.finder.detect_element_type(code)

    def extract(self, code: str) -> CodeElementsResult:
        """
        Extract code elements from the source code.
        
        Args:
            code: Source code as string
            
        Returns:
            CodeElementsResult containing extracted elements
        """
        return self.extraction_service.extract_code_elements(code)

    def upsert_element(self, original_code: str, element_type: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
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
        return self.manipulator.upsert_element(original_code, element_type, name, new_code, parent_name)

    def resolve_xpath(self, xpath: str) -> Tuple[str, Optional[str]]:
        """
        Resolve an XPath expression to element name and parent name.
        
        Args:
            xpath: XPath expression (e.g., 'ClassName.method_name')
            
        Returns:
            Tuple of (name, parent_name)
        """
        if '.' in xpath:
            (parent_name, name) = xpath.split('.', 1)
            return (name, parent_name)
        else:
            return (xpath, None)