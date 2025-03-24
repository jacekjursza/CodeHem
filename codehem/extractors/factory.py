"""
Factory for creating appropriate extractors based on type and language.
"""
import logging
from typing import Optional
from codehem.extractors.base import BaseExtractor
from codehem.core.registry import registry
logger = logging.getLogger(__name__)

class ExtractorFactory:
    """Factory for creating extractors."""

    @staticmethod
    def create_extractor(element_type: str, language_code: str) -> Optional[BaseExtractor]:
        """
        Create an extractor of the specified type for the given language.

        Args:
        element_type: The type of extractor (class, function, etc.)
        language_code: The language code (python, typescript, etc.)

        Returns:
        An appropriate extractor instance or None if not supported
        """
        if hasattr(element_type, 'value'):
            element_type = element_type.value
        element_type = element_type.lower()
        
        # First check if handler exists for this language/element type
        handler = registry.get_handler(language_code, element_type)
        if not handler:
            logger.debug(f'No handler found for {language_code}/{element_type}')
            return None
        
        # Get extractor class from registry
        extractor_class = registry.get_extractor(element_type)
        if not extractor_class:
            logger.debug(f'No extractor found for {element_type}')
            return None
        
        # Create extractor instance
        try:
            extractor = extractor_class()
            if extractor.supports_language(language_code):
                logger.debug(f'Created extractor for {language_code}/{element_type}')
                return extractor
            else:
                logger.debug(f'Extractor does not support language: {language_code}/{element_type}')
        except Exception as e:
            logger.error(f'Error creating extractor: {str(e)}')
        
        return None