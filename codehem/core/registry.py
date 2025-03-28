"""
Central registration system for CodeHem components.
Uses decorator-based self-registration for automatic component discovery.
"""
import importlib
import logging
import os
import traceback
from typing import Any, List, Optional, Type

import rich

from codehem.core.service import LanguageService
from codehem.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)

class Registry:
    """
    Central registry for all CodeHem components.
    Components register themselves using decorators.
    """
    _instance = None

    def __init__(self):
        self._initialized = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Registry, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize empty registries for different component types."""
        self.language_detectors = {}
        self.language_services = {}
        self.all_descriptors = {}
        self.all_extractors = {}
        self.all_manipulators = {}
        self.discovered_modules = set()
        self.language_service_instances = {}
        self._initialized = False

    def register_language_detector(self, cls):
        """Register a language detector class."""
        instance = cls()
        language_code = instance.language_code.lower()
        self.language_detectors[language_code] = instance
        rich.print(f'Registered language detector: {cls.__name__} for {language_code}')
        return cls

    def register_language_service(self, cls: Type[LanguageService]):
        """Register a language service class."""
        self.language_services[cls.LANGUAGE_CODE] = cls
        rich.print(f'Registered language service: {cls.__name__} for {cls.LANGUAGE_CODE}')
        return cls

    def register_extractor(self, cls: Type[BaseExtractor]):
        """Register an extractor class - extractor is language agnostic and needs descriptor for specific language"""

        if cls.ELEMENT_TYPE in self.all_extractors:
            print(f"Warning: Extractor for {cls.ELEMENT_TYPE} already registered {self.all_extractors[cls.ELEMENT_TYPE].__name__}.")
            return cls

        self.all_extractors[cls.ELEMENT_TYPE] = cls
        rich.print(f'Registered extractor: {cls.__name__} for {cls.ELEMENT_TYPE}')
        return cls

    def register_manipulator(self, cls):
        """Register a language-specific handler."""
        key = f'{cls.LANGUAGE_CODE}_{cls.ELEMENT_TYPE.value.lower()}'
        self.all_manipulators[key] = cls
        rich.print(f'Registered manipulator: {cls.__name__} for {cls.ELEMENT_TYPE}')
        return cls

    def register_element_type_descriptor(self, cls):
        """Register a language-specific handler."""
        instance = cls()
        language_code = instance.language_code.lower()
        element_type = instance.element_type.value.lower()
        if language_code not in self.all_descriptors:
            self.all_descriptors[language_code] = {}
        self.all_descriptors[language_code][element_type] = instance
        rich.print(f'Registered descriptor: {cls.__name__} for {language_code}/{element_type}')
        return cls

    def get_language_detector(self, language_code: str) -> Optional[Any]:
        """Get a language detector by code."""
        return self.language_detectors.get(language_code.lower())

    def get_language_service(self, language_code) -> Optional[Any]:
        """Get a language service by code, injecting dependencies."""
        if not isinstance(language_code, str):
            logger.error(f'Invalid language_code type: {type(language_code)}')
            return None

        language_code = language_code.lower()

        if language_code not in self.language_service_instances:
            language_service_cls = self.language_services.get(language_code)

            if language_service_cls:
                try:
                    # Get formatter class for this language
                    formatter_class = None
                    if language_code == 'python':
                        from codehem.languages.lang_python.formatting.python_formatter import (
                            PythonFormatter,
                        )
                        formatter_class = PythonFormatter
                    # Add other language formatters as needed

                    # Initialize language service with components
                    self.language_service_instances[language_code] = language_service_cls(
                        extractors=self.all_extractors,
                        manipulators=self.all_manipulators,
                        element_type_descriptors=self.all_descriptors,
                        formatter_class=formatter_class
                    )
                except Exception as e:
                    logger.error(f'Error initializing language service for {language_code}: {e}')
                    return None
            else:
                return None

        return self.language_service_instances.get(language_code)

    def get_supported_languages(self) -> List[str]:
        """Get a list of all supported language codes."""
        return list(self.language_services.keys())

    def discover_modules(self, package_name='codehem', recursive=True):
        """
        Discover and import all modules in a package to trigger registrations.
        """
        rich.print(f'Discovering modules in package: {package_name}')
        try:
            package = importlib.import_module(package_name)
            package_dir = os.path.dirname(package.__file__)
            for item in os.listdir(package_dir):
                if item.startswith('__') or item.startswith('.'):
                    continue
                full_path = os.path.join(package_dir, item)
                if item.endswith('.py'):
                    module_name = f'{package_name}.{item[:-3]}'
                    if module_name not in self.discovered_modules:
                        try:
                            importlib.import_module(module_name)
                            self.discovered_modules.add(module_name)
                            rich.print(f'Imported module: {module_name}')
                        except Exception as e:
                            logger.warning(f'Error importing module {module_name}: {e}')
                            print(traceback.format_exc())
                elif os.path.isdir(full_path) and recursive:
                    subpackage = f'{package_name}.{item}'
                    if os.path.exists(os.path.join(full_path, '__init__.py')):
                        self.discover_modules(subpackage, recursive)
        except Exception as e:
            logger.error(f'Error discovering modules in {package_name}: {e}')

    def initialize_components(self):
        """
        Discover and initialize all components.
        This should be called once at application startup.
        """
        if self._initialized:
            return
        self.discover_modules()
        self._initialized = True
        rich.print(f'Components initialized: {len(self.language_detectors)} detectors, {len(self.language_services)} services, {len(self.all_extractors)} extractors, {len(self.all_manipulators)} languages with handlers')
registry = Registry()

def language_detector(cls):
    """Decorator to register a language detector."""
    return registry.register_language_detector(cls)

def language_service(cls):
    """Decorator to register a language service."""
    return registry.register_language_service(cls)

def extractor(cls):
    """Decorator to register an extractor."""
    return registry.register_extractor(cls)

def manipulator(cls):
    """Decorator to register a manipulator."""
    return registry.register_manipulator(cls)

def element_type_descriptor(cls):
    """Decorator to register a language handler."""
    return registry.register_element_type_descriptor(cls)