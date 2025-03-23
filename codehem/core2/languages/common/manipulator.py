"""
Common manipulator implementation shared across language modules.
"""
import re
from typing import Optional, Tuple, Callable
from ...engine.base_manipulator import BaseManipulator

class CommonManipulator(BaseManipulator):
    """
    Common implementation of code manipulator with shared functionality.
    Language-specific manipulators should extend this class.
    """

    def __init__(self, analyzer, formatter):
        """
        Initialize the common manipulator.
        
        Args:
            analyzer: Analyzer instance for the language
            formatter: Formatter instance for the language
        """
        self.analyzer = analyzer
        self.formatter = formatter

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
        (start_line, end_line) = self.analyzer.find_element(original_code, element_type, name, parent_name)
        formatted_code = self.formatter.format_element(element_type, new_code)
        if start_line > 0 and end_line > 0:
            return self.replace_lines(original_code, start_line, end_line, formatted_code)
        else:
            handler = self._get_add_handler(element_type)
            if handler:
                return handler(original_code, name, formatted_code, parent_name)
            else:
                return original_code.rstrip() + '\n\n' + formatted_code

    # Other method implementations remain the same, 
    # but replace all occurrences of "self.finder" with "self.analyzer"