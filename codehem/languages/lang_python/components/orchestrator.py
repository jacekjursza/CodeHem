"""
Python-specific extraction orchestrator implementation.

This module provides Python-specific implementation of the IExtractionOrchestrator
interface, coordinating the extraction process using Python-specific components.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from codehem.core.components.base_implementations import BaseExtractionOrchestrator
from codehem.languages.lang_python.components.parser import PythonCodeParser
from codehem.languages.lang_python.components.navigator import PythonSyntaxTreeNavigator
from codehem.languages.lang_python.components.extractor import PythonElementExtractor
from codehem.core.error_handling import handle_extraction_errors
from codehem.models.code_element import CodeElementsResult

logger = logging.getLogger(__name__)

class PythonExtractionOrchestrator(BaseExtractionOrchestrator):
    """
    Python-specific implementation of the extraction orchestrator.
    
    Coordinates the extraction process using Python-specific components.
    """
    
    def __init__(self, post_processor):
        """
        Initialize the Python extraction orchestrator.
        
        Args:
            post_processor: The post processor to use for transforming raw extraction data
        """
        # Create Python-specific components
        parser = PythonCodeParser()
        navigator = PythonSyntaxTreeNavigator()
        extractor = PythonElementExtractor(navigator)
        
        # Initialize base orchestrator with components
        super().__init__('python', parser, extractor, post_processor)
        
        # Store navigator for find_element operations
        self.navigator = navigator
    
    @handle_extraction_errors
    def find_element(self, code: str, element_type: str, 
                   element_name: Optional[str]=None, 
                   parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the Python code based on type, name, and parent.
        
        Args:
            code: Source code as string
            element_type: Type of element to find (e.g., 'function', 'class', 'method')
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        logger.debug(f"PythonExtractionOrchestrator: Finding element type='{element_type}', name='{element_name}', parent='{parent_name}'")
        try:
            # Parse the code
            tree, code_bytes = self.parser.parse(code)
            
            # Find the element using the navigator
            return self.navigator.find_element(tree, code_bytes, element_type, element_name, parent_name)
        except Exception as e:
            logger.error(f'Error during find_element for Python: {e}', exc_info=True)
            return (0, 0)
