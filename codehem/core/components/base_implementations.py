"""
Base implementations of component interfaces.

This module provides base implementations of the component interfaces defined in
the interfaces module. These implementations can be extended by language-specific
subclasses to provide concrete functionality.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from abc import ABC, abstractmethod

import rich

from codehem.core.components.interfaces import (
    ICodeParser, ISyntaxTreeNavigator, IElementExtractor, IPostProcessor, IExtractionOrchestrator
)
from codehem.core.error_handling import handle_extraction_errors
from codehem.models.enums import CodeElementType

if TYPE_CHECKING:
    from codehem.models.code_element import CodeElement, CodeElementsResult

logger = logging.getLogger(__name__)

class BaseCodeParser(ICodeParser, ABC):
    """
    Base implementation of the ICodeParser interface.
    
    Provides common functionality for language-specific parser implementations.
    """
    
    def __init__(self, language_code: str):
        """
        Initialize the parser with a language code.
        
        Args:
            language_code: The language code this parser is for
        """
        self._language_code = language_code
    
    @property
    def language_code(self) -> str:
        """Get the language code this parser is for."""
        return self._language_code

class BaseSyntaxTreeNavigator(ISyntaxTreeNavigator, ABC):
    """
    Base implementation of the ISyntaxTreeNavigator interface.
    
    Provides common functionality for language-specific syntax tree navigator implementations.
    """
    
    def __init__(self, language_code: str):
        """
        Initialize the navigator with a language code.
        
        Args:
            language_code: The language code this navigator is for
        """
        self._language_code = language_code
    
    @property
    def language_code(self) -> str:
        """Get the language code this navigator is for."""
        return self._language_code

class BaseElementExtractor(IElementExtractor, ABC):
    """
    Base implementation of the IElementExtractor interface.
    
    Provides common functionality for language-specific element extractor implementations.
    """
    
    def __init__(self, language_code: str, navigator: ISyntaxTreeNavigator):
        """
        Initialize the extractor with a language code and navigator.
        
        Args:
            language_code: The language code this extractor is for
            navigator: The syntax tree navigator to use
        """
        self._language_code = language_code
        self.navigator = navigator
    
    @property
    def language_code(self) -> str:
        """Get the language code this extractor is for."""
        return self._language_code
    
    @handle_extraction_errors
    def extract_all(self, tree: Any, code_bytes: bytes) -> Dict[str, List[Dict]]:
        """
        Extract all supported code elements from the provided syntax tree.
        
        Default implementation that combines results from individual extraction methods.
        Subclasses may override for more efficient or specialized extraction.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            Dictionary of element type to list of element data dictionaries
        """
        logger.info(f'Starting raw extraction of all elements for {self.language_code}')
        results = {'imports': self.extract_imports(tree, code_bytes)}
        logger.debug(f"Raw extracted {len(results.get('imports', []))} import elements.")
        
        # Extract standalone functions
        results['functions'] = self.extract_functions(tree, code_bytes)
        logger.debug(f"Raw extracted {len(results.get('functions', []))} functions.")
        
        # Extract classes
        results['classes'] = self.extract_classes(tree, code_bytes)
        logger.debug(f"Raw extracted {len(results.get('classes', []))} classes.")
        
        # Extract methods
        all_members = self.extract_methods(tree, code_bytes)
        results['members'] = all_members
        logger.debug(f'Raw extracted {len(all_members)} potential class members (methods/getters/setters).')
        
        # Extract properties
        results['properties'] = self.extract_properties(tree, code_bytes)
        logger.debug(f'Raw extracted {len(results.get("properties", []))} regular properties.')
        
        # Extract static properties
        static_props = self.extract_static_properties(tree, code_bytes)
        results['static_properties'] = static_props
        logger.debug(f'Raw extracted {len(static_props)} static properties.')
        
        # Extract decorators
        decorators = self.extract_decorators(tree, code_bytes)
        results['decorators'] = decorators
        logger.debug(f'Raw extracted {len(decorators)} decorators.')
        
        # Extract interfaces, enums, type aliases, namespaces if supported
        for element_type in ['interfaces', 'enums', 'type_aliases', 'namespaces']:
            extract_method = getattr(self, f'extract_{element_type}', None)
            if extract_method:
                results[element_type] = extract_method(tree, code_bytes)
                logger.debug(f"Raw extracted {len(results.get(element_type, []))} {element_type}.")
        
        logger.info(f'Completed raw extraction for {self.language_code}. Collected types: {list(results.keys())}')
        return results
    
    @abstractmethod
    def extract_imports(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract imports from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of import data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_properties(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract properties from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of property data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_static_properties(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract static properties from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of static property data dictionaries
        """
        pass
    
    @abstractmethod
    def extract_decorators(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract decorators from the provided syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of decorator data dictionaries
        """
        pass

class BaseExtractionOrchestrator(IExtractionOrchestrator):
    """
    Base implementation of the IExtractionOrchestrator interface.
    
    Coordinates the extraction process using the provided components.
    """
    
    def __init__(self, language_code: str, parser: ICodeParser, 
                 extractor: IElementExtractor, post_processor: IPostProcessor):
        """
        Initialize the orchestrator with components.
        
        Args:
            language_code: The language code this orchestrator is for
            parser: The code parser to use
            extractor: The element extractor to use
            post_processor: The post processor to use
        """
        self.language_code = language_code
        self.parser = parser
        self.extractor = extractor
        self.post_processor = post_processor
    
    @handle_extraction_errors
    def extract_all(self, code: str) -> 'CodeElementsResult':
        """
        Extract all code elements from the provided code.
        
        Args:
            code: Source code as string
            
        Returns:
            CodeElementsResult containing extracted elements
        """
        from codehem.models.code_element import CodeElementsResult
        
        logger.info(f'ExtractionOrchestrator: Starting extraction for {self.language_code}')
        try:
            # Parse the code
            tree, code_bytes = self.parser.parse(code)
            
            # Extract raw elements
            raw_elements = self.extractor.extract_all(tree, code_bytes)
            
            # Post-process elements
            result = self.post_processor.process_all(raw_elements)
            
            logger.info(f'ExtractionOrchestrator: Completed extraction for {self.language_code}')
            return result
        except Exception as e:
            logger.error(f'Error during extract_all for {self.language_code}: {e}', exc_info=True)
            # Return empty result on error
            return CodeElementsResult(elements=[])
    
    @handle_extraction_errors
    def find_element(self, code: str, element_type: str, 
                   element_name: Optional[str]=None, 
                   parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element in the code based on type, name, and parent.
        
        Args:
            code: Source code as string
            element_type: Type of element to find (e.g., 'function', 'class', 'method')
            element_name: Optional name of the element to find
            parent_name: Optional name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        logger.debug(f"==> find_element: type='{element_type}', name='{element_name}', parent='{parent_name}'")
        try:
            # Parse the code
            tree, code_bytes = self.parser.parse(code)
            
            # Find the element
            return self.navigator.find_element(tree, code_bytes, element_type, element_name, parent_name)
        except Exception as e:
            logger.error(f'Error during find_element for {self.language_code}: {e}', exc_info=True)
            return (0, 0)
