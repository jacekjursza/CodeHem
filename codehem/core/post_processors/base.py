"""
Language-specific post-processor base class.

This module provides the abstract base class for language-specific post-processors,
which transform raw extraction data into structured CodeElement objects with proper relationships.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from codehem.core.components.interfaces import IPostProcessor
from codehem.models.enums import CodeElementType

if TYPE_CHECKING:
    from codehem.models.code_element import CodeElement, CodeElementsResult

logger = logging.getLogger(__name__)

class LanguagePostProcessor(IPostProcessor, ABC):
    """
    Abstract base class for language-specific post-processors.
    
    Transforms raw extraction dictionaries into structured CodeElement objects with proper 
    relationships. Provides common functionality while allowing language-specific implementations
    to handle unique features of each programming language.
    """
    
    def __init__(self, language_code: str):
        """
        Initialize the post-processor with a language code.
        
        Args:
            language_code: The language code this post-processor is for
        """
        self._language_code = language_code
    
    @property
    def language_code(self) -> str:
        """Get the language code this post-processor is for."""
        return self._language_code
    
    @abstractmethod
    def process_imports(self, raw_imports: List[Dict]) -> List['CodeElement']:
        """
        Process raw import data into CodeElement objects.
        
        Args:
            raw_imports: List of raw import dictionaries
            
        Returns:
            List of CodeElement objects representing imports
        """
        pass
    
    @abstractmethod
    def process_functions(self, raw_functions: List[Dict], 
                        all_decorators: Optional[List[Dict]]=None) -> List['CodeElement']:
        """
        Process raw function data into CodeElement objects.
        
        Args:
            raw_functions: List of raw function dictionaries
            all_decorators: Optional list of all decorators found in the file
            
        Returns:
            List of CodeElement objects representing functions
        """
        pass
    
    @abstractmethod
    def process_classes(self, raw_classes: List[Dict], members: List[Dict], 
                      static_props: List[Dict], properties: Optional[List[Dict]]=None,
                      all_decorators: Optional[List[Dict]]=None) -> List['CodeElement']:
        """
        Process raw class data into CodeElement objects.
        
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
    
    def process_all(self, raw_elements: Dict[str, List[Dict]]) -> 'CodeElementsResult':
        """
        Process all raw element data into a CodeElementsResult.
        
        Default implementation that calls individual processing methods and combines the results.
        Subclasses may override for more specific processing.
        
        Args:
            raw_elements: Dictionary of element type to list of raw element dictionaries
            
        Returns:
            CodeElementsResult containing processed elements
        """
        from codehem.models.code_element import CodeElementsResult
        
        logger.info(f'Starting post-processing of all elements for {self.language_code}')
        result = CodeElementsResult()
        
        # Extract decorators to use for contextual enrichment
        all_decorators = raw_elements.get('decorators', [])
        
        # Process imports
        imports = self.process_imports(raw_elements.get('imports', []))
        result.elements.extend(imports)
        logger.debug(f'Post-processed {len(imports)} import elements')
        
        # Process functions
        functions = self.process_functions(
            raw_elements.get('functions', []), 
            all_decorators
        )
        result.elements.extend(functions)
        logger.debug(f'Post-processed {len(functions)} function elements')
        
        # Process classes and their members
        classes = self.process_classes(
            raw_elements.get('classes', []),
            raw_elements.get('members', []),
            raw_elements.get('static_properties', []),
            raw_elements.get('properties', []),
            all_decorators
        )
        result.elements.extend(classes)
        logger.debug(f'Post-processed {len(classes)} class elements')
        
        # Process additional language-specific elements
        for element_type in ['interfaces', 'enums', 'type_aliases', 'namespaces']:
            elements_method = getattr(self, f'process_{element_type}', None)
            if elements_method and callable(elements_method):
                raw_list = raw_elements.get(element_type, [])
                if raw_list:
                    processed = elements_method(raw_list, all_decorators)
                    result.elements.extend(processed)
                    logger.debug(f'Post-processed {len(processed)} {element_type} elements')
        
        logger.info(f'Completed post-processing for {self.language_code}')
        return result
    
    def _build_lookup(self, items: List[Dict], key_field: str) -> Dict[str, List[Dict]]:
        """
        Build a lookup dictionary for items based on a key field.
        
        Args:
            items: List of dictionaries containing the items
            key_field: The field to use as key in the lookup dictionary
            
        Returns:
            Dictionary mapping key field values to lists of items
        """
        result = {}
        if not items:
            return result
            
        for item in items:
            if not isinstance(item, dict):
                continue
                
            key = item.get(key_field)
            if not key:
                continue
                
            if key not in result:
                result[key] = []
                
            result[key].append(item)
            
        return result
