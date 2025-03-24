"""
Registry for language services and detectors.
"""
import logging
import os
from typing import List, Optional, Any, Dict
from .base import BaseLanguageDetector, BaseLanguageService
logger = logging.getLogger(__name__)

class LanguageRegistry:
    """
    Registry for language services and detectors.
    Implements the Singleton pattern.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LanguageRegistry, cls).__new__(cls)
            cls._instance._services = {}
            cls._instance._detectors = {}
            cls._instance._handlers = {}
            cls._instance._initialized = False
            # Initialize automatically when instance is created
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """Initialize the registry by discovering language modules."""
        if self._initialized:
            return
        self._services = {}
        self._detectors = {}
        self._handlers = {}  # Initialize handlers dict
        self._discover_languages()
        self._initialized = True

    def _discover_languages(self):
        """Discover and load all available language modules."""
        from . import lang_javascript, lang_python, lang_typescript
        languages_to_load = [lang_python, lang_javascript, lang_typescript]
        for lang_module in languages_to_load:
            try:
                if hasattr(lang_module, 'register'):
                    lang_module.register(self)
                    logger.debug(f'Registered language module: {lang_module.__name__}')
            except Exception as e:
                logger.error(f'Error loading language module {lang_module.__name__}: {str(e)}')

    def register_service(self, service: BaseLanguageService):
        """
        Register a language service.
        
        Args:
            service: The service to register
        """
        self._services[service.language_code.lower()] = service
        logger.debug(f'Registered service for language: {service.language_code}')

    def register_detector(self, detector: BaseLanguageDetector):
        """
        Register a language detector.
        
        Args:
            detector: The detector to register
        """
        self._detectors[detector.language_code.lower()] = detector
        logger.debug(f'Registered detector for language: {detector.language_code}')

    def register_handler(self, handler):
        """Register a handler for a specific language and element type."""
        language_code = handler.language_code.lower()
        element_type = handler.element_type.value.lower()
        if language_code not in self._handlers:
            self._handlers[language_code] = {}
        self._handlers[language_code][element_type] = handler
        logger.debug(f'Registered handler for {language_code}/{element_type}')
    
    def get_handler(self, language_code: str, element_type: str) -> Optional[Any]:
        """Get a handler for a specific language and element type."""
        language_code = language_code.lower()
        element_type = element_type.lower()
        return self._handlers.get(language_code, {}).get(element_type)
    
    def get_handlers(self, language_code: str) -> List[Any]:
        """Get all handlers for a specific language."""
        language_code = language_code.lower()
        return list(self._handlers.get(language_code, {}).values())

    def get_service(self, language_code: str) -> Optional[BaseLanguageService]:
        """
        Get a language service by code.
        
        Args:
            language_code: The language code to get a service for
            
        Returns:
            Language service or None if not found
        """
        return self._services.get(language_code.lower())

    def get_detector(self, language_code: str) -> Optional[BaseLanguageDetector]:
        """
        Get a language detector by code.
        
        Args:
            language_code: The language code to get a detector for
            
        Returns:
            Language detector or None if not found
        """
        return self._detectors.get(language_code.lower())

    def get_all_detectors(self) -> List[BaseLanguageDetector]:
        """Get all registered language detectors."""
        return list(self._detectors.values())

    def get_supported_languages(self) -> List[str]:
        """Get a list of all supported language codes."""
        return list(self._services.keys())

    def get_service_for_file(self, file_path: str) -> Optional[BaseLanguageService]:
        """
        Get language service for the specified file based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language service or None if not supported
        """
        (_, ext) = os.path.splitext(file_path)
        ext = ext.lower()
        for service in self._services.values():
            if ext in service.file_extensions:
                return service
        return None

    def get_service_for_code(self, code: str) -> Optional[BaseLanguageService]:
        """
        Attempt to detect language from code content.
        
        Args:
            code: Source code as string
            
        Returns:
            Language service or None if not detected
        """
        if not code.strip():
            return None
        results = []
        for detector in self._detectors.values():
            confidence = detector.detect_confidence(code)
            if confidence > 0:
                results.append((detector.language_code, confidence))
        if not results:
            return None
        results.sort(key=lambda x: x[1], reverse=True)
        if results[0][1] > 0.5:
            return self.get_service(results[0][0])
        return None
registry = LanguageRegistry()