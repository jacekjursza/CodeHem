"""
TypeScript extraction orchestrator component.

This module provides the TypeScript implementation of the IExtractionOrchestrator interface,
coordinating the extraction of code elements from TypeScript/JavaScript files.
"""

import logging
from typing import Dict, List, Optional, Tuple

from codehem.core.components.interfaces import IExtractionOrchestrator, IPostProcessor
from codehem.core.components.base_implementations import BaseExtractionOrchestrator
from codehem.core.error_handling import handle_extraction_errors
from codehem.models.code_element import CodeElementsResult

from .parser import TypeScriptCodeParser
from .navigator import TypeScriptSyntaxTreeNavigator
from .extractor import TypeScriptElementExtractor

logger = logging.getLogger(__name__)


class TypeScriptExtractionOrchestrator(BaseExtractionOrchestrator):
    """
    TypeScript implementation of the IExtractionOrchestrator interface.
    
    Coordinates the extraction process for TypeScript/JavaScript code:
    1. Parses code into a syntax tree
    2. Extracts raw code elements using the TypeScript element extractor
    3. Processes raw elements into structured CodeElement objects
    """
    
    def __init__(self, post_processor: IPostProcessor):
        """
        Initialize the TypeScript extraction orchestrator.
        
        Args:
            post_processor: The TypeScript post-processor component
        """
        # Initialize with TypeScript-specific components
        parser = TypeScriptCodeParser()
        navigator = TypeScriptSyntaxTreeNavigator()
        extractor = TypeScriptElementExtractor(navigator)
        
        super().__init__('typescript', parser, extractor, post_processor)
    
    @handle_extraction_errors
    def extract_all(self, code: str) -> CodeElementsResult:
        """
        Perform complete extraction of all code elements from TypeScript code.
        
        Args:
            code: The TypeScript code to extract elements from
            
        Returns:
            A CodeElementsResult containing all extracted CodeElement objects
        """
        logger.debug("Extracting all TypeScript code elements")
        
        # Parse the code
        tree, code_bytes = self.parser.parse(code)
        
        # Extract raw data for all elements
        raw_data = self.extractor.extract_all(tree, code_bytes)
        
        # Process raw data into CodeElement objects
        elements = self.post_processor.process_all(raw_data)
        
        logger.debug(f"Extracted {len(elements.elements)} TypeScript code elements")
        return elements
    
    @handle_extraction_errors
    def find_element(
        self, 
        code: str, 
        element_type: str, 
        element_name: Optional[str] = None, 
        parent_name: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Find a specific element in TypeScript code.
        
        Args:
            code: The TypeScript code to search in
            element_type: The type of element to find
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element
            
        Returns:
            A tuple containing the start and end line numbers of the element
        """
        logger.debug(f"Finding TypeScript element: type={element_type}, name={element_name}, parent={parent_name}")
        
        # Parse the code
        tree, code_bytes = self.parser.parse(code)
        
        # Use the navigator to find the specific element
        start_line, end_line = self.extractor._navigator.find_element(
            tree, code_bytes, element_type, element_name, parent_name
        )
        
        logger.debug(f"Found TypeScript element at lines {start_line}-{end_line}")
        return start_line, end_line
