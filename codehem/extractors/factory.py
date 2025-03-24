"""
Factory for creating appropriate extractors based on type and language.
"""
import logging
from typing import Optional
from codehem.extractors.base import BaseExtractor
from codehem.languages.registry import registry

logger = logging.getLogger(__name__)

class ExtractorFactory:
    """Factory for creating extractors."""

    def create_extractor(self, element_type: str, language_code: str) -> Optional[BaseExtractor]:
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
        handler = registry.get_handler(language_code, element_type)
        if not handler:
            logger.debug(f'No handler found for {language_code}/{element_type}')
            return None
        extractor_class = registry.get_extractor(element_type)
        if extractor_class:
            extractor = extractor_class()
            if extractor.supports_language(language_code):
                return extractor
        from .generic_extractor import GenericExtractor
        generic = GenericExtractor(element_type)
        if generic.supports_language(language_code):
            return generic
        logger.debug(f'No extractor found for {element_type} / {language_code}')
        return None
