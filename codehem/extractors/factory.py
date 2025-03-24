"""
Factory for creating appropriate extractors based on type and language.
"""
import importlib
import os
from typing import Dict, List, Optional, Type
from codehem.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.languages.registry import registry
import logging
logger = logging.getLogger(__name__)

class ExtractorFactory:
    """Factory for creating extractors."""

    def __init__(self):
        self._extractors = {}
        self._load_extractors()

    def _load_extractors(self):
        """Dynamically load all available extractors."""
        extractors_dir = os.path.dirname(os.path.abspath(__file__))
        for file_name in os.listdir(extractors_dir):
            if file_name.startswith('type_') and file_name.endswith('.py'):
                element_type = file_name[5:-3]
                try:
                    module = importlib.import_module(f'codehem.extractors.{file_name[:-3]}')
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BaseExtractor) and (attr is not BaseExtractor):
                            self._extractors[element_type] = attr
                            logger.debug(f'Registered extractor: {attr_name} for {element_type}')
                            break
                except (ImportError, AttributeError) as e:
                    logger.warning(f'Could not load extractor {file_name}: {e}')

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
        extractor_class = self._extractors.get(element_type)

        print(self._extractors)

        if extractor_class:
            extractor = extractor_class()
            if extractor.supports_language(language_code):
                return extractor

        # Add debug message for missing extractor
        logger.debug(f"No extractor found for {element_type} / {language_code}")
        return None
